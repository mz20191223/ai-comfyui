"""提示词 Lint：把项目铁律变成可开关的自动检查。

在「生成」前调用；命中项返回规则名、严重级、证据，前端在提示词旁标红。
"""
from __future__ import annotations

import re

from ..core import db
from ..core.db import jloads
from . import file_store, shot_service

NEGATION_WORDS = ("严禁", "禁止", "不得", "不要", "无", "没有", "不入画", "不出现", "排除", "避免", "切勿", "非")
SENT_SPLIT_RE = re.compile(r"[。！？；\n]+")


def load_rules(project_id: int | None, stage: str) -> list[dict]:
    rows = db.query(
        """SELECT * FROM lint_rules WHERE enabled=1 AND (project_id IS NULL OR project_id=?)
           ORDER BY sort_order""",
        (project_id,),
    )
    # 规则的 stage 为 both 时在任何阶段都要跑。方向是「规则的 stage ∈ {当前阶段, both}」——
    # 写成 `stage in (r["stage"], "both")` 会让 both 规则恒不生效（曾漏跑 4 条规则）。
    return [r for r in rows if r["stage"] in (stage, "both")]


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in SENT_SPLIT_RE.split(text or "") if s.strip()]


def _affirmative_sentences(text: str) -> list[str]:
    return [s for s in _sentences(text) if not any(n in s for n in NEGATION_WORDS)]


NOTE_OPEN = ("【工作流注释", "非提示词")


def strip_workflow_notes(text: str) -> str:
    """剔除明确标注为「工作流注释·非提示词」的块。

    这些块本来就不喂模型（给操作者看的决策记录），却被解析器一并存进了
    image_prompt / video_prompt 字段。若不剔除，黑名单会把注释里提到的
    「首帧」「终态」当成提示词问题报出来——纯误报。
    """
    if not text:
        return ""
    out, skipping = [], False
    for ln in text.splitlines():
        s = ln.strip()
        if any(t in s for t in NOTE_OPEN):
            skipping = True
            continue
        if skipping:
            if s.startswith(">") or not s:      # 注释块 = 连续的引用行
                continue
            skipping = False
        out.append(ln)
    return "\n".join(out)


# ---------------- 各检查器 ----------------

def _ck_keyword_blacklist(b: dict, cfg: dict, rule: dict) -> list[dict]:
    """关键词黑名单。

    cfg["side"] 决定查哪一侧：image / video / both（默认 both）。
    **分镜图与视频是两次独立调用**——图像模型只有一帧、只做这一次出图；视频模型
    有本次调用内的时间轴。所以两侧各自有一份黑名单，不能混着查（视频侧的
    「0.00 秒首帧」是接口协议必需的，图像侧的同类写法则是越界）。
    """
    kws = cfg.get("keywords") or []
    side = (cfg.get("side") or "both").lower()
    fields = {"image": ["image_prompt"],
              "video": ["video_prompt"]}.get(side, ["video_prompt", "image_prompt"])
    hay = strip_workflow_notes(
        "\n".join(filter(None, [b["detail"].get(f) for f in fields]))
    )
    hits = [k for k in kws if k in hay]
    if not hits:
        return []
    ev = []
    for k in hits:
        for s in _sentences(hay):
            if k in s:
                ev.append(s[:160])
                break
    where = {"image": "分镜图", "video": "视频"}.get(side, "提示词")
    hint = cfg.get("hint") or "跨镜交代用语"
    return [{
        "message": f"{where}含{hint}：{'、'.join(hits)}",
        "evidence": " ｜ ".join(ev),
        "suggestion": cfg.get("suggestion") or "跨镜衔接靠 ref_image_0=上镜尾帧，不写进提示词",
    }]


def _ck_require_phrase(b: dict, cfg: dict, rule: dict) -> list[dict]:
    any_of = cfg.get("any_of") or []
    hay = "\n".join(str(b["detail"].get(h) or "") for h in (cfg.get("haystack") or ["video_prompt"]))
    if not hay.strip():
        return []
    if any(ph in hay for ph in any_of):
        return []
    return [{
        "message": f"缺少必需语句：{' / '.join(any_of)}",
        "evidence": "",
        "suggestion": "补入防转场硬约束（黑场、黑帧、淡入、淡出、溶解、叠化）",
    }]


def _ck_dialogue_format(b: dict, cfg: dict, rule: dict) -> list[dict]:
    out = []
    lines = b.get("dialog_lines") or []
    if not lines:
        return out
    vp = b["detail"].get("video_prompt") or ""
    for ln in lines:
        text = (ln.get("text") or "").strip()
        if not text:
            continue
        if text in vp and "**" not in vp:
            out.append({
                "message": "台词未加粗独立成句（应为 **角色：“台词”**）",
                "evidence": text[:80],
                "suggestion": "把台词写成加粗独立成句，整句一气呵成",
            })
            break
        if re.search(r"拆成\s*(多个|两个|几个)\s*utterance|分\s*[2-9]\s*段生成", vp):
            break
    return out


def _ck_ref_blacklist(b: dict, cfg: dict, rule: dict) -> list[dict]:
    kws = cfg.get("keywords") or []
    out = []
    for side in ("video_refs", "image_refs"):
        for r in b.get(side) or []:
            nm = r.get("file_name") or ""
            hit = [k for k in kws if k in nm]
            if hit:
                out.append({
                    "message": f"参考素材命中禁入词（{'、'.join(hit)}）：{nm}",
                    "evidence": f"{side} 第 {r.get('slot_index')} 位",
                    "suggestion": "白模预演片不得进 API，请替换为成片帧",
                })
    return out


def _ck_duration_check(b: dict, cfg: dict, rule: dict) -> list[dict]:
    dur = b["detail"].get("duration_sec")
    lines = b.get("dialog_lines") or []
    if not dur or not lines:
        return []
    ln = lines[0]
    measured = ln.get("audio_measured_sec")
    start = ln.get("start_sec")
    if not measured:
        return []
    if start is None:
        return [{
            "message": f"台词未标注起始时间（音频 {measured}s，总时长 {dur}s）",
            "evidence": (ln.get("text") or "")[:60],
            "suggestion": "在时序拍点里标出台词时间窗",
        }]
    span = dur - start
    tail = float(cfg.get("min_tail_sec") or 0.2)
    if span + 1e-6 < measured + tail:
        return [{
            "message": f"时长可能截断台词：可用 {span:.2f}s ＜ 音频 {measured}s（+{tail}s 余量）",
            "evidence": f"duration={dur}s，台词起点 {start}s",
            "suggestion": f"把 duration 提到 ≥ {start + measured + tail:.1f}s，或提前台词起点",
        }]
    return []


def _ck_subject_scope(b: dict, cfg: dict, rule: dict) -> list[dict]:
    d = b["detail"]
    hay = " ".join(filter(None, [d.get("video_prompt"), d.get("summary")]))
    no_person = any(
        kw in hay for kw in ("严禁出现任何人物", "严禁出现过客", "画面无过客", "纯魅影镜头", "无人入画", "过客不入画")
    )
    if not no_person:
        return []
    words = cfg.get("person_words") or ["过客"]
    bad = [s for s in _affirmative_sentences(hay) if any(w in s for w in words)]
    if not bad:
        return []
    return [{
        "message": "本镜声明为无人镜头，但正文出现了人物描述",
        "evidence": bad[0][:160],
        "suggestion": "删除人物相关内容，或改用通用负向词「严禁出现任何人物」",
    }]


def _ck_file_exists(b: dict, cfg: dict, rule: dict) -> list[dict]:
    out = []
    for side, label in (("video_refs", "视频侧"), ("image_refs", "分镜图侧")):
        for r in b.get(side) or []:
            # 与 placeholder_ref 用同一判定源：老记录的 is_placeholder 字段可能是空的，
            # 但文件名本身（「分镜图」「待生成」）已经能判出是占位符。
            if r.get("is_placeholder") or file_store.is_placeholder(r.get("file_name")):
                continue
            if not r.get("file_exists"):
                out.append({
                    "message": f"{label}引用的文件不存在：{r.get('file_name')}",
                    "evidence": f"第 {r.get('slot_index')} 位",
                    "suggestion": "补齐文件，或改引已有素材",
                })
    return out


ANCHOR_HINTS = ("Image", "参考图", ".jpg", ".jpeg", ".png", ".webp")


def _binds_to_ref(sentence: str) -> bool:
    """句子里是否把该代号绑到了某张具体参考图上。

    项目里大量用「Image 2：0112b_tail.jpg —— 死循环妖形态锚点」这种写法给角色
    绑定**渲染帧**（不是角色参考图），此时代号是有视觉锚点的，不该报。
    """
    return any(h in sentence for h in ANCHOR_HINTS)


def _ck_internal_code(b: dict, cfg: dict, rule: dict) -> list[dict]:
    d = b["detail"]
    codes = cfg.get("codes") or []
    # 保留换行：句子按行切开，才能判断「这一句」有没有绑定参考图
    hay = strip_workflow_notes("\n".join(filter(None, [d.get("image_prompt"), d.get("video_prompt")])))
    # 已上传的资产名集合
    uploaded = set()
    for side in ("video_refs", "image_refs"):
        for r in b.get(side) or []:
            if r.get("asset_name"):
                uploaded.add(r["asset_name"])
    out = []
    for code in codes:
        if code not in hay or code in uploaded:
            continue
        bad = [s for s in _affirmative_sentences(hay) if code in s]
        if not bad:
            continue
        # 代号级豁免：只要该代号**在任一处**绑到了具体参考图，就算它有视觉锚点。
        # （项目惯例是「Image N：xxx_tail.jpg —— 某妖形态锚点」用渲染帧作锚，
        #   别处再顺口提到该代号是正常的，不算「无锚点乱点名」。）
        if any(_binds_to_ref(s) for s in bad):
            continue
        out.append({
            "message": f"正文点名了内部代号「{code}」，但本镜未上传其参考图",
            "evidence": bad[0][:140],
            "suggestion": "改用通用描述或补传该角色参考图",
        })
    return out


def _ck_decl_consistency(b: dict, cfg: dict, rule: dict) -> list[dict]:
    d = b["detail"]
    decl_ids = set()
    for s in _sentences(d.get("declarations") or b.get("_decl_text") or ""):
        for m in re.finditer(r"(?:Image|Picture)\s*(\d+)", s):
            decl_ids.add(int(m.group(1)))
    # 约定：声明里的 Image N 对应参数 ref_image_(N-1)，比较前先统一成 Image 口径，
    # 否则「声明 Image 1..5 / 参数 ref_image_0..4」会被误判成不一致。
    # （老提示词里可能写 `Image 1（= Picture 1）`，这里按 Image 口径归一即可。）
    ref_slots = {r.get("slot_index") for r in (b.get("video_refs") or []) if r.get("slot_index") is not None}
    ref_ids = {s + 1 for s in ref_slots}
    if not decl_ids or not ref_ids:
        return []
    only_decl = sorted(decl_ids - ref_ids)
    only_ref = sorted(ref_ids - decl_ids)
    out = []
    if only_decl:
        out.append({
            "message": f"声明了但参数里没有：Image {only_decl}",
            "evidence": f"声明 {sorted(decl_ids)} / 参数 Image {sorted(ref_ids)}",
            "suggestion": "补齐 ref_image 参数或删除多余声明",
        })
    if only_ref:
        slots = [n - 1 for n in only_ref]
        out.append({
            "message": f"参数里有但声明里没有：Image {only_ref}（即 ref_image_{min(slots)}）",
            "evidence": f"声明 {sorted(decl_ids)} / 参数 Image {sorted(ref_ids)}",
            "suggestion": "在素材关系声明里补上对应 Image N",
        })
    return out


def _ck_placeholder_ref(b: dict, cfg: dict, rule: dict) -> list[dict]:
    out = []
    for side, label in (("video_refs", "视频侧"), ("image_refs", "分镜图侧")):
        for r in b.get(side) or []:
            nm = r.get("file_name")
            if nm and file_store.is_placeholder(nm):
                out.append({
                    "message": f"{label}第 {r.get('slot_index')} 位仍是占位符：{nm}",
                    "evidence": nm,
                    "suggestion": "替换为真实文件名后再生成",
                })
    return out


def _ref_key(s: str | None) -> str:
    """参考图名归一化：去括号说明、去扩展名、去空格。"""
    if not s:
        return ""
    s = re.sub(r"[（(].*?[）)]", "", str(s)).strip().strip("*").strip()
    s = re.sub(r"\.(jpg|jpeg|png|webp)$", "", s, flags=re.I)
    return s.replace(" ", "")


def _slot_of(refs: list[dict], side: str, n: int) -> dict | None:
    """编号 n 对应的槽位记录。image 侧编号==slot_index；video 侧 Image N == slot_index+1。"""
    want = n if side == "image" else n - 1
    for r in refs:
        if r.get("slot_index") == want:
            return r
    return None


def _ck_ref_slot_drift(b: dict, cfg: dict, rule: dict) -> list[dict]:
    """提示词里的参考图编号是否与工作台槽位指向同一张图。

    只判「声明名确实指向本镜某个参考图、但位置对不上」——用描述代替文件名的写法
    （如「Image 1：镜头8视频尾帧」）不判，否则会把正常写法全打成误报。
    """
    side = (cfg or {}).get("side", "image")
    d = b["detail"]
    if side == "image":
        text = strip_workflow_notes(d.get("image_prompt") or "")
        rex = re.compile(r"参考图\s*(\d+)\s*[（(]([^）)]*)[）)]")
        refs = b.get("image_refs") or []
    else:
        text = strip_workflow_notes(d.get("video_prompt") or "")
        rex = re.compile(r"^\s*Image\s*(\d+)\s*[：:]\s*([^\s（(—\-]+)", re.M)
        refs = b.get("video_refs") or []
    if not text or not refs:
        return []

    # 编号口径：image 侧 编号 == slot_index；video 侧 编号 == slot_index + 1
    off = 0 if side == "image" else 1
    names = [_ref_key(r.get("file_name")) for r in refs]
    asset_names = [_ref_key(r.get("asset_name")) for r in refs]

    def tag_of(n: int) -> str:
        return f"参考图{n}" if side == "image" else f"Image {n}"

    out: list[dict] = []
    for ns, declared in rex.findall(text):
        n = int(ns)
        tag = tag_of(n)
        slot = _slot_of(refs, side, n)
        if slot is None:
            # 编号在本镜根本没有对应槽位 —— 与「名字是否写得出来」无关，直接判越界
            out.append({
                "message": f"写了 {tag}，但工作台没有这个槽位（本镜 {side} 侧共 {len(refs)} 张）",
                "evidence": f"{tag}（{declared}）",
                "suggestion": "改成实际存在的编号，或到工作台补上该槽位",
            })
            continue
        key = _ref_key(declared)
        if len(key) < 3:
            continue                       # 编号对得上、名字只是短 → 不判
        where = [i for i, nm in enumerate(names) if nm and (key == nm or key in nm or nm in key)]
        if not where:
            where = [i for i, nm in enumerate(asset_names) if nm and (key == nm or key in nm or nm in key)]
        if not where:
            continue                       # 名字不是本镜任一参考图（写的是描述）→ 不判
        here = _ref_key(slot.get("file_name"))
        if any(here == names[i] or here in names[i] or names[i] in here for i in where):
            continue                       # 指向正确
        moved_slot = refs[where[0]].get("slot_index", where[0]) + off
        out.append({
            "message": (f"{tag} 声明的是「{declared}」，但工作台第 {n} 位实际是"
                        f"「{slot.get('file_name')}」（该名字在第 {moved_slot} 位）"),
            "evidence": (f"{tag}（{declared}）←→ 槽位 #{slot.get('slot_index')} "
                         f"{slot.get('file_name')}"),
            "suggestion": "把提示词里的编号与实际槽位对齐（改编号顺序，或到工作台调整槽位顺序）",
        })
    return out


CHECKERS = {
    "keyword_blacklist": _ck_keyword_blacklist,
    "require_phrase": _ck_require_phrase,
    "dialogue_format": _ck_dialogue_format,
    "ref_blacklist": _ck_ref_blacklist,
    "duration_check": _ck_duration_check,
    "subject_scope": _ck_subject_scope,
    "file_exists": _ck_file_exists,
    "internal_code": _ck_internal_code,
    "decl_consistency": _ck_decl_consistency,
    "placeholder_ref": _ck_placeholder_ref,
    "ref_slot_drift": _ck_ref_slot_drift,
}


# ---------------- 对外入口 ----------------

def lint_shot(shot_id: int, stage: str = "video", project_id: int | None = None, persist: bool = True) -> list[dict]:
    b = shot_service.get_shot(shot_id)
    if not b:
        return []
    if project_id is None:
        project_id = (b.get("project") or {}).get("id")
    rules = load_rules(project_id, stage)
    # decl 检查需要原文声明
    b["_decl_text"] = b["detail"].get("video_prompt") or ""
    results: list[dict] = []
    for rule in rules:
        fn = CHECKERS.get(rule["checker"])
        if not fn:
            continue
        cfg = jloads(rule.get("config"), {}) or {}
        try:
            for hit in fn(b, cfg, rule):
                results.append({
                    "rule_key": rule["key"],
                    "label": rule["label"],
                    "severity": rule["severity"],
                    "stage": stage,
                    **hit,
                })
        except Exception as e:  # noqa: BLE001
            results.append({
                "rule_key": rule["key"], "label": rule["label"], "severity": "info", "stage": stage,
                "message": f"规则执行异常：{e}", "evidence": "", "suggestion": "检查规则配置",
            })
    if persist:
        db.execute("DELETE FROM lint_results WHERE shot_id=? AND stage=?", (shot_id, stage))
        for r in results:
            db.execute(
                """INSERT INTO lint_results(shot_id, stage, rule_key, severity, message, evidence)
                   VALUES(?,?,?,?,?,?)""",
                (shot_id, stage, r["rule_key"], r["severity"], r["message"], r.get("evidence")),
            )
    return results


def lint_episode(episode_id: int, stage: str = "video") -> dict:
    shots = db.query("SELECT id, shot_code FROM shots WHERE episode_id=? ORDER BY sort_order", (episode_id,))
    out = []
    total = {"error": 0, "warn": 0, "info": 0}
    for s in shots:
        hits = lint_shot(s["id"], stage=stage)
        for h in hits:
            total[h["severity"]] = total.get(h["severity"], 0) + 1
        if hits:
            out.append({"shot_id": s["id"], "shot_code": s["shot_code"], "hits": hits})
    return {"episode_id": episode_id, "stage": stage, "totals": total, "shots": out}
