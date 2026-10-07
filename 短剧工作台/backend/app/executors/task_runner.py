"""统一任务执行器。

一张 generation_tasks 表承载所有长任务：生图、生视频、TTS、抽帧、合成。
- 任务态与镜头态彻底分离（双轨）
- payload 存参数快照，可原样重跑
- 支持取消、重试、进度
"""
from __future__ import annotations

import json
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ..config import PENDING_DIR, STORAGE_DIR
from ..core import db
from ..core.db import jdumps, jloads
from ..executors import provider_engine as PE
from ..services import file_store, hooks_service, naming, script_service, shot_service

_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="studio-task")
_futures: dict[int, object] = {}
_lock = threading.Lock()


# ---------------- 任务创建 ----------------

def create_task(
    task_kind: str,
    *,
    target_kind: str | None = None,
    target_id: int | None = None,
    role: str | None = None,
    payload: dict | None = None,
    model_id: int | None = None,
    provider_id: int | None = None,
    mode: str | None = None,
    max_attempts: int = 1,
    priority: int = 0,
    submit: bool = True,
) -> int:
    if model_id and not provider_id:
        row = db.query_one("SELECT provider_id, mode FROM models WHERE id=?", (model_id,))
        if row:
            provider_id = row["provider_id"]
            mode = mode or row["mode"]
    mode = mode or ("local" if task_kind in ("extract_frame", "compose", "lint", "normalize_8bit") else "async_polling")
    tid = db.execute(
        """INSERT INTO generation_tasks(task_kind, mode, status, progress, priority, provider_id,
               model_id, payload, max_attempts)
           VALUES(?,?,?,?,?,?,?,?,?)""",
        (task_kind, mode, "submitted", 0, priority, provider_id, model_id, jdumps(payload or {}), max_attempts),
    )
    if target_kind and target_id:
        db.execute(
            "INSERT INTO task_links(task_id, target_kind, target_id, role) VALUES(?,?,?,?)",
            (tid, target_kind, target_id, role),
        )
    if submit:
        submit_task(tid)
    return tid


def submit_task(task_id: int) -> None:
    with _lock:
        fut = _pool.submit(_run, task_id)
        _futures[task_id] = fut


def _set(task_id: int, **kw) -> None:
    if not kw:
        return
    cols = ", ".join(f"{k}=?" for k in kw)
    db.execute(
        f"UPDATE generation_tasks SET {cols}, updated_at=datetime('now','localtime') WHERE id=?",
        list(kw.values()) + [task_id],
    )


def _progress(task_id: int, pct: int, note: str = "", mark_running: bool = False) -> None:
    """回写进度。mark_running=True 表示这是接口回执，可把「已提交」推进到「进行中」。"""
    kw: dict = {"progress": max(0, min(100, int(pct)))}
    if mark_running:
        cur = db.query_one("SELECT status FROM generation_tasks WHERE id=?", (task_id,))
        if cur and cur["status"] == "submitted":
            kw["status"] = "running"
    _set(task_id, **kw)
    if note:
        row = db.query_one("SELECT result FROM generation_tasks WHERE id=?", (task_id,))
        res = jloads(row["result"], {}) if row and row["result"] else {}
        res["note"] = note
        _set(task_id, result=jdumps(res))


def _cancelled(task_id: int) -> bool:
    row = db.query_one("SELECT cancel_requested FROM generation_tasks WHERE id=?", (task_id,))
    return bool(row and row["cancel_requested"])


# ---------------- 失败归因 / 僵尸回收 ----------------

# provider_engine.detect_quota 给出的 kind → 任务态的失败原因
_QUOTA_TO_FAIL = {
    "exhausted": "insufficient_balance",   # 额度耗尽：余额不足 / 欠费
    "cooling": "rate_limit",               # 限流冷却：稍后再试或换号
    "invalid": "auth",                     # Key 无效 / 无权限
}

FAIL_TEXT = {
    "insufficient_balance": "余额不足",
    "rate_limit": "接口限流",
    "auth": "密钥无效",
    "api_error": "接口错误",
    "interrupted": "进程中断",
}


# stage=quota 但异常没带 kind 时的文案兜底（老路径 / 被第三方封装过的异常）
_QUOTA_TEXT_HINTS = (
    ("insufficient_balance", ("余额不足", "积分不足", "欠费", "额度不足", "额度耗尽", "余额", "insufficient", "quota")),
    ("rate_limit", ("限流", "频繁", "rate limit", "too many")),
    ("auth", ("鉴权", "无效", "无权限", "未授权", "401", "403")),
)


def classify_failure(e: Exception) -> str:
    """把异常归因到失败原因。

    依次看：异常自带的 kind → detail 里的 kind → stage=quota 时的文案兜底。
    stage 已经是「额度类」的明确信号，所以兜底至少给 rate_limit，不再吞成 api_error。
    """
    qk = getattr(e, "kind", None)
    if qk not in _QUOTA_TO_FAIL:
        detail = getattr(e, "detail", None)
        if isinstance(detail, dict):
            qk = detail.get("kind") or qk
    if qk in _QUOTA_TO_FAIL:
        return _QUOTA_TO_FAIL[qk]
    if getattr(e, "stage", "") == "quota":
        low = str(e).lower()
        for fk, words in _QUOTA_TEXT_HINTS:
            if any(w in low for w in words):
                return fk
        return "rate_limit"
    return "api_error"


def recover_zombies() -> int:
    """进程启动时清理上次遗留的未终态任务。

    任务跑在线程池里、纯内存。进程一重启，库里那些 submitted/running 就再也没人
    更新了 —— 不打扫的话界面会永远显示「进行中」，只能手改数据库。
    """
    rows = db.query("SELECT id FROM generation_tasks WHERE status IN ('submitted','running')")
    if not rows:
        return 0
    ids = [r["id"] for r in rows]
    ph = ",".join("?" * len(ids))
    db.execute(
        f"""UPDATE generation_tasks
            SET status='failed', fail_kind='interrupted',
                fail_message='进程重启导致中断',
                error='进程重启导致中断（该次生成未完成）',
                finished_at=datetime('now','localtime'),
                updated_at=datetime('now','localtime')
            WHERE id IN ({ph})""",
        ids,
    )
    return len(ids)


# ---------------- 参数组装 ----------------

def build_video_params(shot_id: int, overrides: dict | None = None) -> dict:
    b = shot_service.get_shot(shot_id)
    if not b:
        raise PE.ProviderError(f"镜头不存在：{shot_id}", stage="params")
    d = b["detail"]
    project = b.get("project") or {}
    ep = b.get("episode") or {}

    ref_images: list[str] = []
    ref_names: list[str] = []
    for r in b["video_refs"]:
        nm = r.get("file_name")
        if not nm or r.get("is_placeholder"):
            continue
        p = r.get("resolved_path") or (file_store.resolve(nm, project))
        if p:
            ref_images.append(str(p))
            ref_names.append(Path(str(p)).name)

    # 首帧优先于 ref_image_0 槽位（两者一致时取帧）
    first = next((f for f in b["frames"] if f["frame_type"] == "first"), None)
    if first:
        fp = first["file_path"]
        if ref_images and Path(ref_images[0]).name != Path(fp).name:
            ref_images.insert(0, fp)
            ref_names.insert(0, Path(fp).name)
        elif not ref_images:
            ref_images.append(fp)
            ref_names.append(Path(fp).name)

    ref_audios: list[str] = []
    for ln in b["dialog_lines"]:
        if ln.get("audio_file"):
            p = file_store.resolve(ln["audio_file"], project)
            if p:
                ref_audios.append(str(p))

    prompt = d.get("video_prompt") or ""
    if d.get("image_is_optional") or True:
        pass
    constraints = jloads(d.get("hard_constraints"), []) or []
    if constraints:
        marks = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
        parts = []
        for i, c in enumerate(constraints):
            if i < len(marks):
                parts.append(f"{marks[i]} {c}")
            else:
                parts.append(f"({i + 1}) {c}")
        prompt = (prompt + "\n\n硬约束：" + " ".join(parts)).strip()
    if d.get("video_prompt_prefix"):
        prompt = d["video_prompt_prefix"] + "\n\n" + prompt

    params = {
        "shot_id": shot_id,
        "shot_code": b["shot"]["shot_code"],
        "prompt": prompt,
        "duration": d.get("duration_sec") or 5,
        "resolution": d.get("resolution") or (project.get("resolution") or "768p竖"),
        "seed": d.get("seed"),
        "ref_images": ref_images,
        "ref_names": ref_names,
        "ref_audios": ref_audios,
        "first_frame": first["file_path"] if first else (ref_images[0] if ref_images else None),
        "last_frame": next(
            (f["file_path"] for f in b["frames"] if f["frame_type"] == "last"), None
        ),
        "transport": "auto",
        "episode_number": ep.get("number", 1),
    }
    if overrides:
        params.update(overrides)
    return params


def build_image_params(shot_id: int, overrides: dict | None = None) -> dict:
    b = shot_service.get_shot(shot_id)
    if not b:
        raise PE.ProviderError(f"镜头不存在：{shot_id}", stage="params")
    d = b["detail"]
    project = b.get("project") or {}

    refs = []
    for r in b["image_refs"]:
        nm = r.get("file_name")
        if not nm or r.get("is_placeholder"):
            continue
        p = r.get("resolved_path") or file_store.resolve(nm, project)
        if p:
            refs.append(str(p))
    if not refs:
        # 回退到视频侧参考图（去掉首帧锚点）
        for r in b["video_refs"]:
            nm = r.get("file_name")
            if not nm or r.get("is_placeholder"):
                continue
            p = r.get("resolved_path") or file_store.resolve(nm, project)
            if p:
                refs.append(str(p))

    params = {
        "shot_id": shot_id,
        "shot_code": b["shot"]["shot_code"],
        "prompt": d.get("image_prompt") or "",
        "n": 1,
        "size": overrides.get("size") if overrides and overrides.get("size") else (
            "1024x1536" if str(project.get("aspect_ratio") or "9:16").startswith("9") else "1536x1024"
        ),
        "ref_images": refs,
        "transport": "auto",
        "target_name": d.get("image_target_name")
        or naming.keyframe_names(b["shot"]["shot_code"], (b.get("episode") or {}).get("number", 1))[0],
        "episode_number": (b.get("episode") or {}).get("number", 1),
        "grid": (overrides or {}).get("grid", 1),   # 1 / 4 / 9 宫格
    }
    if overrides:
        params.update(overrides)
    return params


# ---------------- 执行 ----------------

def _run(task_id: int) -> None:
    row = db.query_one("SELECT * FROM generation_tasks WHERE id=?", (task_id,))
    if not row:
        return
    kind = row["task_kind"]
    payload = jloads(row["payload"], {}) or {}
    # 本地任务（抽帧/合成/Lint/转码）没有「接口回执」这回事，直接算进行中；
    # 走接口的任务先停在「已提交」，等第一次轮询回执再转「进行中」。
    _set(
        task_id,
        status=("running" if row["mode"] == "local" else "submitted"),
        started_at=_now(),
        attempts=(row["attempts"] or 0) + 1,
    )
    try:
        if _cancelled(task_id):
            _set(task_id, status="cancelled", finished_at=_now(), progress=0, error="已取消")
            return
        if kind == "video_generation":
            _run_video(task_id, payload)
        elif kind == "image_generation":
            _run_image(task_id, payload)
        elif kind == "llm_generation":
            _run_llm(task_id, payload)
        elif kind == "extract_frame":
            _run_extract(task_id, payload)
        elif kind == "compose":
            _run_compose(task_id, payload)
        elif kind == "lint":
            _run_lint(task_id, payload)
        elif kind == "normalize_8bit":
            _run_normalize(task_id, payload)
        else:
            raise PE.ProviderError(f"未知任务类型：{kind}", stage="dispatch")
    except Exception as e:  # noqa: BLE001
        _fail(task_id, e)
    finally:
        with _lock:
            _futures.pop(task_id, None)


def _fail(task_id: int, e: Exception) -> None:
    msg = str(e)
    detail = getattr(e, "detail", None)
    stage = getattr(e, "stage", "")
    tb = traceback.format_exc(limit=3)
    fk = classify_failure(e)
    _set(
        task_id, status="failed", finished_at=_now(),
        error=(f"[{stage}] " if stage else "") + msg,
        fail_kind=fk, fail_message=FAIL_TEXT.get(fk, "生成失败"),
        result=jdumps({"detail": detail, "traceback": tb.splitlines()[-3:]}),
    )


def _ok(task_id: int, result: dict) -> None:
    _set(task_id, status="succeeded", progress=100, finished_at=_now(), result=jdumps(result))
    # 就绪态重算（静态轨不受任务影响，但候选可能因新文件消解）
    row = db.query_one(
        "SELECT target_id FROM task_links WHERE task_id=? AND target_kind='shot' LIMIT 1", (task_id,)
    )
    if row:
        db.execute("UPDATE shots SET updated_at=datetime('now','localtime') WHERE id=?", (row["target_id"],))


def _now() -> str:
    from datetime import datetime

    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _run_video(task_id: int, payload: dict) -> None:
    model_id = payload.get("model_id")
    bundle = PE.load_model_bundle(model_id, "video")
    _progress(task_id, 3, "校验素材…")
    shot_id = payload.get("shot_id")
    if payload.get("rebuild_params") or not payload.get("prompt"):
        payload = {**build_video_params(shot_id, payload.get("overrides")), **{
            k: v for k, v in payload.items() if k in ("model_id", "overrides")
        }}
        _set(task_id, payload=jdumps(payload))

    if shot_id:
        audit = hooks_service.validate_materials(shot_id)
        if not audit["ok"]:
            errs = [p for p in audit["problems"] if p["type"] in ("ghost_ref", "audio_missing")]
            if errs and not payload.get("force"):
                raise PE.ProviderError(
                    "素材校验未通过：" + "；".join(p["message"] for p in errs), stage="precheck",
                    detail=audit,
                )

    res = PE.execute(bundle, {**payload, "model_id": None},
                     progress=lambda p, n: _progress(task_id, p, n, mark_running=True))
    if _cancelled(task_id):
        _set(task_id, status="cancelled", finished_at=_now(), error="已取消（生成已完成但被丢弃）")
        return
    if not res.ok or not res.files:
        raise PE.ProviderError(res.error or "生成失败", stage="generate", detail=res.raw)

    project = _project_of_shot(shot_id) if shot_id else None
    ep_num = payload.get("episode_number", 1)
    # 产物先进工作台自己的暂存区（storage/pending），不直接落进项目「分镜视频」：
    # 用户在页面上看过之后，自己选「归档到分镜视频」还是「废弃」。
    out_dir = PENDING_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    shot_code = payload.get("shot_code") or f"task{task_id}"
    saved: list[dict] = []

    # 编号按「同类里第几个」算，不按整体下标：一个任务里若混着封面图之类，
    # 按整体下标会把正片挤到 _1 去（0114d_1.mp4），封面反倒占了正名。
    seen_kind: dict[str, int] = {}
    for f in res.files:
        ext = ".mp4" if f["kind"] == "video" else ".png"
        stem = naming.code_stem(shot_code, ep_num) if shot_code and shot_code[0].isdigit() else f"t{task_id}"
        n = seen_kind.get(f["kind"], 0)
        seen_kind[f["kind"]] = n + 1
        suffix = "" if n == 0 else f"_{n}"
        # 同样防撞：同一个镜头重出成片时退让为 _2、_3…，绝不覆盖上一版（成片是花了额度的）
        dst = _free_path(out_dir / f"{stem}{suffix}{ext}")
        try:
            PE.download_result(f["value"], dst, bundle["provider"])
        except Exception as e:  # noqa: BLE001
            raise PE.ProviderError(f"结果下载失败：{e}", stage="download", detail=str(f["value"])[:300]) from e
        info = file_store.probe(dst)
        fid = file_store.index_file(dst)
        if shot_id:
            db.execute(
                """INSERT INTO files(path, file_name, ext, file_type, size_bytes, width, height, duration_sec, exists_flag)
                   SELECT ?,?,?,?,?,?,?,?,1 WHERE NOT EXISTS (SELECT 1 FROM files WHERE path=?)
                   """,
                (str(dst.resolve()), dst.name, dst.suffix.lower(), f["kind"],
                 info.get("size_bytes"), info.get("width"), info.get("height"),
                 info.get("duration_sec"), str(dst.resolve())),
            )
            db.execute(
                """INSERT INTO file_usages(file_id, usage_kind, target_kind, target_id, note)
                   SELECT id, 'shot_video', 'shot', ?, ? FROM files WHERE path=?""",
                (shot_id, f"任务 {task_id}", str(dst.resolve())),
            )
        saved.append({"path": str(dst), "file_id": fid, "kind": f["kind"],
                      "pending": True, **info})

    _progress(task_id, 94, "抽尾帧…")
    hook_out = None
    if shot_id and payload.get("auto_tail", True):
        settings = {r["key"]: r["value"] for r in db.query("SELECT key, value FROM settings")}
        try:
            hook_out = hooks_service.extract_and_register_tail(
                shot_id, saved[0]["path"],
                link_to_next=(settings.get("auto_link_tail_to_next", "1") == "1"),
            )
        except Exception as e:  # noqa: BLE001
            hook_out = {"error": str(e)}

    _ok(task_id, {
        "files": saved,
        "remote_task_id": res.task_id,
        "tail": hook_out,
        "note": "生成完成",
    })


def _run_image(task_id: int, payload: dict) -> None:
    bundle = PE.load_model_bundle(payload.get("model_id"), "image")
    shot_id = payload.get("shot_id")
    if payload.get("rebuild_params") or not payload.get("prompt"):
        payload = {**build_image_params(shot_id, payload.get("overrides")), "model_id": payload.get("model_id")}
        _set(task_id, payload=jdumps(payload))
    _progress(task_id, 5, "提交生图…")
    res = PE.execute(bundle, payload, progress=lambda p, n: _progress(task_id, p, n, mark_running=True))
    if not res.ok or not res.files:
        raise PE.ProviderError(res.error or "生图失败", stage="generate", detail=res.raw)

    project = _project_of_shot(shot_id) if shot_id else None
    out_dir = Path((project or {}).get("keyframe_dir") or (STORAGE_DIR / "keyframes"))
    out_dir.mkdir(parents=True, exist_ok=True)
    target = payload.get("target_name") or f"task{task_id}.png"
    saved = []
    for i, f in enumerate(res.files):
        # 重出图不覆盖旧版：正式名被占用时退让为 _2、_3…（旧版原图保住，候选区多一张）
        dst = _free_path(out_dir / (target if len(res.files) == 1 else _numbered(target, i)))
        PE.download_result(f["value"], dst, bundle["provider"])
        info = file_store.probe(dst)
        saved.append({"path": str(dst), "file_id": file_store.index_file(dst), **info})

    _ok(task_id, {"files": saved, "remote_task_id": res.task_id, "note": "生图完成",
                  "preview_target": payload.get("target_name")})


def _run_llm(task_id: int, payload: dict) -> None:
    """大模型文本生成（剧本 / 智能分集 / 单集续写）。

    payload.save 决定落点：
      "script"       → 新建 scripts 版本（整部剧本），结果带 script_id
      "episode"      → 写回指定集（续写单集），结果带 episode_id
      "outline"      → 只解析「集结构+镜头清单」放进任务结果，等人工确认后调 apply 落库
      "shot_prompts" → 解析该集双份提示词，自动拼素材声明后回填到各镜头
      缺省            → 只把文本放进任务结果，等前端人工确认后再落库（分集预览走这条）
    """
    messages = payload.get("messages") or []
    if not messages:
        raise PE.ProviderError("缺少 messages（提示词）", stage="params")
    bundle = PE.load_model_bundle(payload.get("model_id"), "llm")
    params: dict = {"messages": messages}
    if payload.get("temperature") is not None:
        params["temperature"] = payload["temperature"]
    if payload.get("max_tokens"):
        params["max_tokens"] = payload["max_tokens"]

    _progress(task_id, 6, "提交大模型…")
    res = PE.execute(bundle, params, progress=lambda p, n: _progress(task_id, p, n, mark_running=True))
    text = (res.text or "").strip()
    if not res.ok or not text:
        raise PE.ProviderError(res.error or "大模型未返回文本", stage="generate", detail=res.raw)

    model_name = bundle["model"]["name"]
    out: dict = {"text": text, "chars": len(text), "model": model_name, "note": "生成完成"}
    if (res.raw or {}).get("finish_reason") == "length":
        out["note"] = "生成完成，但输出因 max_tokens 被截断（建议调大 max_tokens 或分集生成）"
    save = payload.get("save")
    project_id = payload.get("project_id")

    if save == "script" and project_id:
        _progress(task_id, 96, "写入剧本版本…")
        doc = script_service.parse_script_doc(text)
        out["script_id"] = script_service.save_script(
            project_id,
            doc["body"],
            title=payload.get("title") or doc["title"] or None,
            prompt_used=payload.get("prompt_used"),
            source="ai",
            meta={"model": model_name, "logline": doc["logline"]},
        )
        out["title"] = doc["title"]
        out["logline"] = doc["logline"]
    elif save == "episode" and payload.get("episode_id"):
        _progress(task_id, 96, "写回该集…")
        ep = script_service.parse_single_episode(text)
        eid = payload["episode_id"]
        db.execute(
            """UPDATE episodes SET
                   title=COALESCE(NULLIF(?,''), title),
                   synopsis=COALESCE(NULLIF(?,''), synopsis),
                   script_text=?, updated_at=datetime('now','localtime')
               WHERE id=?""",
            (ep["title"], ep["synopsis"], ep["script"], eid),
        )
        out["episode_id"] = eid
        out["title"] = ep["title"]
    elif save == "outline" and project_id:
        _progress(task_id, 96, "解析结构化出稿…")
        data = script_service.parse_outline(text)
        eps = data.get("episodes") or []
        out["outline"] = data
        out["parsed"] = bool(data.get("_parsed"))
        if data.get("_parsed"):
            n_shots = sum(len(e.get("shots") or []) for e in eps)
            out["note"] = f"解析出 {len(eps)} 集、{n_shots} 个镜头，等待确认后落库"
        else:
            out["note"] = "模型输出不是合法 JSON，请人工检查（原文已放在 outline._raw）"
    elif save == "shot_prompts" and payload.get("episode_id"):
        _progress(task_id, 96, "回填该集提示词…")
        items = script_service.parse_shot_prompts(text)
        if not items:
            raise PE.ProviderError("模型输出里没有解析到任何镜头提示词",
                                   stage="parse", detail=text[:800])
        out.update(script_service.apply_shot_prompts(
            payload["episode_id"], items, model=model_name))
        out["items"] = items
    _ok(task_id, out)


def _numbered(name: str, i: int) -> str:
    p = Path(name)
    return f"{p.stem}_{i + 1}{p.suffix}"


def _free_path(dst: Path) -> Path:
    """落盘防撞：目标已存在时退让序号（0114d.jpg → 0114d_2.jpg → _3 …），绝不覆盖。

    分镜图正式名（如 0114d.jpg）被下游引用（视频首帧锚点、提示词文档里写的文件名），
    重出图若直接覆盖，会静默换掉下游那张、且旧版彻底丢失。所以新图一律退让，
    由用户在候选区里挑一张再手动「设为分镜图」。
    """
    if not dst.exists():
        return dst
    k = 2
    while True:
        cand = dst.with_name(f"{dst.stem}_{k}{dst.suffix}")
        if not cand.exists():
            return cand
        k += 1


def _run_extract(task_id: int, payload: dict) -> None:
    shot_id = payload.get("shot_id")
    video = payload.get("video_path")
    if not video:
        rows = db.query(
            """SELECT t.result FROM generation_tasks t JOIN task_links l ON l.task_id=t.id
               WHERE l.target_kind='shot' AND l.target_id=? AND t.task_kind='video_generation'
                 AND t.status='succeeded' ORDER BY t.id DESC LIMIT 1""",
            (shot_id,),
        )
        if rows:
            res = jloads(rows[0]["result"], {}) or {}
            files = res.get("files") or []
            video = files[0]["path"] if files else None
    if not video:
        raise PE.ProviderError("找不到可抽帧的视频", stage="params")
    _progress(task_id, 30, "抽帧…")
    out = hooks_service.extract_and_register_tail(shot_id, video, link_to_next=True)
    _ok(task_id, out)


def _run_compose(task_id: int, payload: dict) -> None:
    ep = payload.get("episode_id")
    _progress(task_id, 20, "拼接片段…")
    out = hooks_service.compose_episode(ep, payload.get("out_path"))
    _ok(task_id, out)


def _run_lint(task_id: int, payload: dict) -> None:
    from ..services import lint_service

    # shot_id 通常记在 task_links 里（任务表本身不存目标），payload 里的只是兜底
    shot_id = payload.get("shot_id")
    if not shot_id:
        row = db.query_one(
            "SELECT target_id FROM task_links WHERE task_id=? AND target_kind='shot' LIMIT 1", (task_id,)
        )
        shot_id = row["target_id"] if row else None
    stage = payload.get("stage", "video")
    if not shot_id:
        _ok(task_id, {"hits": [], "count": 0, "note": "任务未关联镜头，跳过"})
        return
    hits = lint_service.lint_shot(shot_id, stage=stage)
    _ok(task_id, {"hits": hits, "count": len(hits)})


def _run_normalize(task_id: int, payload: dict) -> None:
    src = payload.get("src")
    if not src:
        raise PE.ProviderError("缺少源文件路径", stage="params")
    _progress(task_id, 20, "转码为 8bit/h264/24fps…")
    out = hooks_service.normalize_8bit(src, payload.get("dst"))
    _ok(task_id, {"files": [{"path": str(out)}], "note": f"已转码：{Path(out).name}"})


def _project_of_shot(shot_id: int) -> dict | None:
    return db.query_one(
        """SELECT p.*, e.number AS episode_number FROM shots s
           JOIN episodes e ON e.id = s.episode_id
           JOIN projects p ON p.id = e.project_id WHERE s.id=?""",
        (shot_id,),
    )


# ---------------- 取消 / 重试 ----------------

def cancel_task(task_id: int, reason: str = "") -> bool:
    row = db.query_one("SELECT status FROM generation_tasks WHERE id=?", (task_id,))
    if not row:
        return False
    if row["status"] in ("succeeded", "failed", "cancelled"):
        return False
    _set(
        task_id,
        cancel_requested=1,
        cancel_requested_at=_now(),
        cancel_reason=reason or "用户取消",
    )
    if row["status"] == "submitted":
        # 还没真正开跑，直接掐掉；已在跑的只能打标记，等执行器自查（协作式取消）
        _set(task_id, status="cancelled", finished_at=_now(), error="用户取消")
    return True


def retry_task(task_id: int) -> int:
    row = db.query_one("SELECT * FROM generation_tasks WHERE id=?", (task_id,))
    if not row:
        raise PE.ProviderError(f"任务不存在：{task_id}", stage="retry")
    link = db.query_one("SELECT * FROM task_links WHERE task_id=?", (task_id,))
    tid = create_task(
        row["task_kind"],
        target_kind=link["target_kind"] if link else None,
        target_id=link["target_id"] if link else None,
        role=link["role"] if link else None,
        payload=jloads(row["payload"], {}) or {},
        model_id=row["model_id"],
        provider_id=row["provider_id"],
        mode=row["mode"],
        max_attempts=row["max_attempts"] or 1,
    )
    db.execute(
        "INSERT INTO settings(key, value, category) VALUES(?,?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (f"retry_of:{tid}", str(task_id), "tasks"),
    )
    return tid
