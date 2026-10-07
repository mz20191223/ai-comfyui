"""剧本与智能分集路由。

链路（2026-09-16 与用户对齐）
    新建项目 → ①写剧本（DeepSeek，可反复迭代）→ ②智能分集（DeepSeek）
      → ③资产图（gpt）→ ④各集拆镜 → 看板出图/出片 → ⑤集数管理再调 DeepSeek 续写

约定
- 剧本按版本存（scripts 表），**最新版本即当前剧本**；每次 AI 生成/人工保存都留一版，可回溯。
- 分集结果**不直接落库**：先生成 → 前端预览可改 → 调 apply 才写 episodes。
- 所有查询按 project_id 隔离。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..core import db
from ..core.db import jloads
from ..executors import task_runner
from ..services import script_service

router = APIRouter(prefix="/api", tags=["scripts"])


# ---------------- 入参模型 ----------------

class ScriptReq(BaseModel):
    """生成/改写剧本的创作参数（requirement 是自由文本主入口，其余可选）。"""

    requirement: str = ""
    episodes: int | None = None
    minutes_per_episode: float | None = None
    genre: str | None = None
    visual_style: str | None = None
    title: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    model_id: int | None = None


class ReviseIn(ScriptReq):
    script_id: int | None = None
    content: str | None = None
    # 「按意见重写」的修改意见；为空时回落到 requirement（兼容旧调用）
    instruction: str | None = None


class SplitIn(ScriptReq):
    script_id: int | None = None
    content: str | None = None


class ApplyEpisodesIn(BaseModel):
    episodes: list[dict] = []


class SaveScriptIn(BaseModel):
    content: str
    title: str | None = None
    note: str | None = None


class ContinueIn(ScriptReq):
    episode_id: int | None = None
    number: int | None = None


# ---------------- 工具 ----------------

def _project(pid: int) -> dict:
    p = db.query_one("SELECT * FROM projects WHERE id=?", (pid,))
    if not p:
        raise HTTPException(404, "项目不存在")
    return p


def _llm_payload(
    messages: list[dict],
    req: ScriptReq,
    *,
    save: str | None = None,
    project_id: int | None = None,
    episode_id: int | None = None,
    title: str | None = None,
    prompt_used: str | None = None,
) -> dict:
    payload: dict[str, Any] = {
        "messages": messages,
        "temperature": req.temperature,
        "max_tokens": req.max_tokens,
        "model_id": req.model_id,
    }
    if save:
        payload["save"] = save
    if project_id:
        payload["project_id"] = project_id
    if episode_id:
        payload["episode_id"] = episode_id
    if title:
        payload["title"] = title
    if prompt_used:
        payload["prompt_used"] = prompt_used
    return {k: v for k, v in payload.items() if v is not None}


def _submit(messages: list[dict], req: ScriptReq, pid: int, **kw) -> dict:
    tid = task_runner.create_task(
        "llm_generation",
        target_kind="project",
        target_id=pid,
        payload=_llm_payload(messages, req, project_id=pid, **kw),
    )
    return {"ok": True, "task_id": tid}


def _latest_script(pid: int) -> dict | None:
    return db.query_one(
        "SELECT * FROM scripts WHERE project_id=? ORDER BY version DESC LIMIT 1", (pid,)
    )


def _chars(messages: list[dict]) -> int:
    return sum(len(m.get("content") or "") for m in messages)


def _script_or_latest(pid: int, script_id: int | None, content: str | None) -> tuple[str, str]:
    """取正文：显式内容 > 指定版本 > 最新版本。返回 (正文, 说明)。"""
    if content and content.strip():
        return content.strip(), "请求传入的正文"
    if script_id:
        row = db.query_one("SELECT * FROM scripts WHERE id=? AND project_id=?", (script_id, pid))
        if not row:
            raise HTTPException(404, "剧本版本不存在（或不属于该项目）")
        return row["content"] or "", f"第 {row['version']} 版"
    row = _latest_script(pid)
    if not row or not (row["content"] or "").strip():
        raise HTTPException(400, "还没有剧本内容，请先生成或录入剧本")
    return row["content"], f"第 {row['version']} 版"


# ---------------- 版本读取 ----------------

@router.get("/projects/{project_id}/scripts")
def list_scripts(project_id: int) -> dict:
    """版本列表（带摘要，不带全文）+ 当前版本（最新版带全文）。"""
    _project(project_id)
    rows = db.query(
        """SELECT id, project_id, version, kind, title, source, episode_id, meta,
                  LENGTH(COALESCE(content,'')) AS chars, created_at, updated_at
           FROM scripts WHERE project_id=? ORDER BY version DESC""",
        (project_id,),
    )
    for r in rows:
        meta = jloads(r.pop("meta", None), {}) or {}
        r["model"] = meta.get("model")
        r["logline"] = meta.get("logline")
    latest = _latest_script(project_id)
    return {"items": rows, "latest": latest}


@router.get("/scripts/{script_id}")
def get_script(script_id: int) -> dict:
    row = db.query_one("SELECT * FROM scripts WHERE id=?", (script_id,))
    if not row:
        raise HTTPException(404, "剧本版本不存在")
    row["meta"] = jloads(row.get("meta"), {}) or {}
    return row


@router.delete("/scripts/{script_id}")
def delete_script(script_id: int) -> dict:
    row = db.query_one("SELECT * FROM scripts WHERE id=?", (script_id,))
    if not row:
        raise HTTPException(404, "剧本版本不存在")
    left = db.query_one(
        "SELECT COUNT(*) AS c FROM scripts WHERE project_id=?", (row["project_id"],)
    )
    if (left or {}).get("c", 0) <= 1:
        raise HTTPException(400, "至少要保留一个剧本版本")
    db.execute("DELETE FROM scripts WHERE id=?", (script_id,))
    return {"ok": True}


# ---------------- ① 写剧本 ----------------

@router.post("/projects/{project_id}/scripts/generate")
def generate_script(project_id: int, body: ScriptReq) -> dict:
    """按创作要求调 DeepSeek 生成整部剧本；完成后自动存为新版本。"""
    p = _project(project_id)
    messages = script_service.build_script_messages(p, body.model_dump())
    return _submit(
        messages, body, project_id,
        save="script",
        prompt_used=body.requirement,
        title=body.title,
    )


@router.post("/projects/{project_id}/scripts/revise")
def revise_script(project_id: int, body: ReviseIn) -> dict:
    """在现有剧本上按修改意见重写（继续调 DeepSeek 迭代）。"""
    p = _project(project_id)
    current, src_note = _script_or_latest(project_id, body.script_id, body.content)
    instruction = body.instruction or body.requirement
    messages = script_service.build_revise_messages(p, current, instruction, body.model_dump())
    return _submit(
        messages, body, project_id,
        save="script",
        prompt_used=instruction,
    )


@router.post("/projects/{project_id}/scripts/save")
def save_script(project_id: int, body: SaveScriptIn) -> dict:
    """人工编辑后保存为新版本（不生成，只落库；保证历史可回溯）。"""
    _project(project_id)
    content = (body.content or "").strip()
    if not content:
        raise HTTPException(400, "内容为空")
    sid = script_service.save_script(
        project_id, content, title=body.title, source="manual",
        meta={"note": body.note} if body.note else None,
    )
    return {"ok": True, "script_id": sid}


@router.post("/projects/{project_id}/scripts/preview")
def preview_script(project_id: int, body: ReviseIn) -> dict:
    """dry-run：只看发出去的提示词（不消耗额度）。

    返回两套草稿：
      generate —— 「调用 DeepSeek 生成」会发的内容（**没有剧本时也能看**，预览本来就是给生成前用的）
      revise   —— 「按意见重写」会发的内容（还没有剧本时为 null）
    """
    p = _project(project_id)
    req = body.model_dump()
    gen = script_service.build_script_messages(p, req)
    out: dict = {
        "generate": {"messages": gen, "chars": _chars(gen)},
        "revise": None,
        "content_note": "",
    }
    try:
        current, note = _script_or_latest(project_id, body.script_id, body.content)
    except HTTPException:
        current, note = "", ""
    if current:
        rv = script_service.build_revise_messages(p, current, body.instruction or body.requirement, req)
        out["revise"] = {"messages": rv, "chars": _chars(rv)}
        out["content_note"] = note
    return out


# ---------------- ② 智能分集 ----------------

@router.post("/projects/{project_id}/scripts/split")
def split_episodes(project_id: int, body: SplitIn) -> dict:
    """调 DeepSeek 把整部剧本切成 N 集。结果只进任务结果，等人工确认后再落库。"""
    p = _project(project_id)
    script_text, _ = _script_or_latest(project_id, body.script_id, body.content)
    messages = script_service.build_split_messages(p, script_text, body.model_dump())
    return _submit(messages, body, project_id)


@router.post("/projects/{project_id}/scripts/parse-episodes")
def parse_episodes(project_id: int, body: dict) -> dict:
    """把（可能被人工编辑过的）分集文本解析成结构化列表，不入库。"""
    _project(project_id)
    text = (body or {}).get("text") or ""
    items = script_service.parse_episodes(text)
    return {"episodes": items, "count": len(items)}


@router.post("/projects/{project_id}/scripts/apply-episodes")
def apply_episodes(project_id: int, body: ApplyEpisodesIn) -> dict:
    """人工确认后写入 episodes（同集号更新、新集号插入）。"""
    _project(project_id)
    if not body.episodes:
        raise HTTPException(400, "没有要写入的分集数据")
    res = script_service.apply_episodes(project_id, body.episodes)
    return {"ok": True, **res}


# ---------------- ⑤ 集数管理：AI 续写 ----------------

@router.post("/projects/{project_id}/scripts/continue-episode")
def continue_episode(project_id: int, body: ContinueIn) -> dict:
    """续写一集：不传 episode_id 就新建下一集再生成；传了就重新生成那一集。"""
    p = _project(project_id)
    latest = _latest_script(project_id)
    script_text = (latest or {}).get("content") or ""

    row = None
    if body.episode_id:
        row = db.query_one(
            "SELECT * FROM episodes WHERE id=? AND project_id=?", (body.episode_id, project_id)
        )
        if not row:
            raise HTTPException(404, "集不存在（或不属于该项目）")
    if not row:
        mx = db.query_one(
            "SELECT COALESCE(MAX(number),0) AS n FROM episodes WHERE project_id=?", (project_id,)
        )
        number = body.number or int((mx or {}).get("n") or 0) + 1
        eid = db.execute(
            """INSERT INTO episodes(project_id, number, title, status, sort_order)
               VALUES(?,?,?,?,?)""",
            (project_id, number, f"第{number}集", "draft", number),
        )
        row = {"id": eid, "number": number}

    existing = db.query(
        "SELECT number, title, synopsis FROM episodes WHERE project_id=? ORDER BY number", (project_id,)
    )
    req = body.model_dump()
    if row.get("number"):
        req["number"] = row["number"]
    messages = script_service.build_continue_messages(p, script_text, existing, req)
    out = _submit(messages, body, project_id, save="episode", episode_id=row["id"])
    out["episode_id"] = row["id"]
    out["number"] = row.get("number")
    return out


@router.post("/projects/{project_id}/scripts/preview-episode")
def preview_episode(project_id: int, body: ContinueIn) -> dict:
    """dry-run：续写一集的提示词预览。"""
    p = _project(project_id)
    latest = _latest_script(project_id)
    existing = db.query(
        "SELECT number, title, synopsis FROM episodes WHERE project_id=? ORDER BY number", (project_id,)
    )
    req = body.model_dump()
    if not req.get("number"):
        mx = max([e["number"] or 0 for e in existing] or [0])
        req["number"] = mx + 1
    msgs = script_service.build_continue_messages(p, (latest or {}).get("content") or "", existing, req)
    return {"messages": msgs}


# ============================================================
# ⑥ 结构化出稿：集结构 + 每集镜头清单（一次调用）
# ============================================================

class OutlineIn(ScriptReq):
    script_id: int | None = None
    content: str | None = None
    shots_per_episode: int | None = None


class ApplyOutlineIn(BaseModel):
    outline: dict
    replace_shots: bool = False


class ShotPromptsIn(ScriptReq):
    shot_codes: list[str] | None = None


def _episode(eid: int) -> tuple[dict, dict]:
    ep = db.query_one("SELECT * FROM episodes WHERE id=?", (eid,))
    if not ep:
        raise HTTPException(404, "集不存在")
    p = db.query_one("SELECT * FROM projects WHERE id=?", (ep["project_id"],))
    if not p:
        raise HTTPException(404, "项目不存在")
    return ep, p


def _shot_list(eid: int) -> list[dict]:
    """该集镜头清单（含槽位与提示词状态），供前端展示与喂给模型。"""
    shots = db.query("SELECT * FROM shots WHERE episode_id=? ORDER BY sort_order, id", (eid,))
    out: list[dict] = []
    for s in shots:
        d = db.query_one("SELECT * FROM shot_details WHERE shot_id=?", (s["id"],)) or {}
        out.append({
            **s,
            "summary": d.get("summary"),
            "duration_sec": d.get("duration_sec"),
            "camera_shot": d.get("camera_shot"),
            "gen_mode": d.get("gen_mode"),
            "image_prompt": d.get("image_prompt"),
            "video_prompt": d.get("video_prompt"),
            "video_prompt_prefix": d.get("video_prompt_prefix"),
            "image_target_name": d.get("image_target_name"),
            "assets_text": d.get("assets_text"),
            "has_image_prompt": bool((d.get("image_prompt") or "").strip()),
            "has_video_prompt": bool((d.get("video_prompt") or "").strip()),
            "links": db.query(
                """SELECT l.slot_index, l.target_side, l.file_name, l.take_note, l.role,
                          a.name AS asset_name, a.asset_type
                   FROM shot_asset_links l LEFT JOIN assets a ON a.id = l.asset_id
                   WHERE l.shot_id=? ORDER BY l.target_side, l.slot_index""",
                (s["id"],),
            ),
            "lines": db.query(
                "SELECT * FROM shot_dialog_lines WHERE shot_id=? ORDER BY line_index, id", (s["id"],)
            ),
        })
    return out


@router.post("/projects/{project_id}/scripts/outline")
def generate_outline(project_id: int, body: OutlineIn) -> dict:
    """一次调 DeepSeek 产出「集结构 + 每集镜头清单」。结果只进任务结果，**不落库**。"""
    p = _project(project_id)
    assets = db.query("SELECT * FROM assets WHERE project_id=?", (project_id,))
    req = body.model_dump()
    if not (req.get("requirement") or "").strip():
        # 没写创作要求时，用当前剧本正文兜底（先写剧本再分镜的用法）
        try:
            current, note = _script_or_latest(project_id, body.script_id, body.content)
            req["requirement"] = current
            req["_from_script"] = note
        except HTTPException:
            pass
    messages = script_service.build_outline_messages(p, req, assets)
    return _submit(messages, body, project_id, save="outline", prompt_used=req.get("requirement"))


@router.post("/projects/{project_id}/scripts/outline/preview")
def preview_outline(project_id: int, body: OutlineIn) -> dict:
    """dry-run：只看发出去的提示词（不消耗额度）。"""
    p = _project(project_id)
    assets = db.query("SELECT * FROM assets WHERE project_id=?", (project_id,))
    req = body.model_dump()
    if not (req.get("requirement") or "").strip():
        try:
            current, _ = _script_or_latest(project_id, body.script_id, body.content)
            req["requirement"] = current
        except HTTPException:
            pass
    msgs = script_service.build_outline_messages(p, req, assets)
    return {"messages": msgs, "chars": _chars(msgs), "assets": len(assets)}


@router.post("/projects/{project_id}/scripts/apply-outline")
def apply_outline(project_id: int, body: ApplyOutlineIn) -> dict:
    """人工确认/编辑后落库：建集、建镜头、按中文名匹配资产写参考图槽位、写台词。"""
    _project(project_id)
    if not (body.outline or {}).get("episodes"):
        raise HTTPException(400, "没有可落库的分集数据")
    res = script_service.apply_outline(project_id, body.outline, replace_shots=body.replace_shots)
    return {"ok": True, **res}


# ============================================================
# ⑦ 按集出双份提示词（一次只处理一集）
# ============================================================

@router.get("/episodes/{episode_id}/shot-list")
def episode_shot_list(episode_id: int) -> dict:
    """该集镜头清单 + 提示词状态（供「分集版块」展示）。"""
    ep, p = _episode(episode_id)
    return {"episode": ep, "project": p, "shots": _shot_list(episode_id)}


def _prompt_targets(eid: int, codes: list[str] | None) -> list[dict]:
    shots = _shot_list(eid)
    if codes:
        want = {str(c).strip() for c in codes}
        shots = [s for s in shots if str(s.get("shot_code")) in want]
    return shots


@router.post("/episodes/{episode_id}/shot-prompts")
def gen_shot_prompts(episode_id: int, body: ShotPromptsIn) -> dict:
    """调 DeepSeek 出本集每镜的【分镜图提示词】+【视频提示词】，自动拼素材声明后回填。"""
    ep, p = _episode(episode_id)
    shots = _prompt_targets(episode_id, body.shot_codes)
    if not shots:
        raise HTTPException(400, "本集还没有镜头，请先落库分集与镜头清单")
    messages = script_service.build_shot_prompts_messages(p, ep, shots, body.model_dump())
    return _submit(messages, body, p["id"], save="shot_prompts", episode_id=episode_id)


@router.post("/episodes/{episode_id}/shot-prompts/preview")
def preview_shot_prompts(episode_id: int, body: ShotPromptsIn) -> dict:
    """dry-run：本集提示词生成的提示词预览。"""
    ep, p = _episode(episode_id)
    shots = _prompt_targets(episode_id, body.shot_codes)
    msgs = script_service.build_shot_prompts_messages(p, ep, shots, body.model_dump())
    return {"messages": msgs, "chars": _chars(msgs), "shots": len(shots)}


@router.post("/episodes/{episode_id}/shot-prompts/apply")
def apply_shot_prompts(episode_id: int, body: dict) -> dict:
    """人工改过提示词后再回填（items: [{shot_code, image_body, video_body}]）。"""
    _episode(episode_id)
    items = (body or {}).get("items") or []
    if not items:
        raise HTTPException(400, "没有要回填的提示词")
    res = script_service.apply_shot_prompts(episode_id, items, model="manual")
    return {"ok": True, **res}
