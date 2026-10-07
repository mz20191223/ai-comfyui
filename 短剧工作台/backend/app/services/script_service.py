"""剧本服务：提示词构建 + 大模型输出解析 + 落库助手。

链路：写剧本（DeepSeek）→ 智能分集（DeepSeek）→ 资产图（gpt）
设计要点
- 模型输出一律「结构化头 + 正文」，解析做两级容错：先抠 JSON，退化到文本标记切分。
- 剧本按版本存（scripts 表，version 同项目自增）；**最新版本即当前剧本**。
- 分集结果**不直接落库**，先回给前端预览，人工确认后才写 episodes。
"""
from __future__ import annotations

import json
import re
from typing import Any

from app.core import db
from app.core.db import jdumps, jloads

from . import naming

SYSTEM_PROMPT = (
    "你是资深竖屏微短剧编剧，擅长强节奏、强钩子的短剧文本。"
    "只输出中文剧本本身，不要解释你的思路，不要用 Markdown 代码块包裹正文。"
)

_CN_DIGITS = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
              "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


# ---------------- 小工具 ----------------

def _norm(s: Any) -> str:
    return str(s).strip() if s is not None else ""


def _as_int(v: Any, default: int = 1) -> int:
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    s = _norm(v)
    if not s:
        return default
    if s.isdigit():
        return int(s)
    return _cn2int(s) or default


def _cn2int(s: str) -> int | None:
    """中文数字转整数，支持 1-99（一 / 十 / 十二 / 二十三）。"""
    s = s.strip()
    if not s:
        return None
    if "十" in s:
        head, _, tail = s.partition("十")
        tens = _CN_DIGITS.get(head, 1) if head else 1
        ones = _CN_DIGITS.get(tail, 0) if tail else 0
        return tens * 10 + ones
    total = 0
    for ch in s:
        if ch not in _CN_DIGITS:
            return None
        total = total * 10 + _CN_DIGITS[ch]
    return total or None


def _json_block(text: str) -> Any:
    """从模型输出里抠出 JSON（容忍 ```json 包裹与前后废话）。"""
    if not text:
        return None
    t = text.strip()
    m = re.search(r"```(?:json)?\s*(.+?)```", t, re.S)
    if m:
        t = m.group(1).strip()
    try:
        return json.loads(t)
    except Exception:
        pass
    for op, cl in (("[", "]"), ("{", "}")):
        i, j = t.find(op), t.rfind(cl)
        if 0 <= i < j:
            try:
                return json.loads(t[i:j + 1])
            except Exception:
                continue
    return None


def _strip_fence(text: str) -> str:
    t = (text or "").strip()
    m = re.fullmatch(r"```[a-zA-Z]*\s*(.+?)```", t, re.S)
    return m.group(1).strip() if m else t


# ---------------- 解析：整部剧本 ----------------

_HEAD_RE = re.compile(r"^\s*(?:#{1,6}\s*)?(标题|剧名|梗概|一句话|正文)\s*[:：]\s*(.*)$", re.M)


def parse_script_doc(text: str) -> dict:
    """把「标题/梗概/正文」结构的输出拆开；没有标记就整段当正文。"""
    body = _strip_fence(text)
    fields: dict[str, str] = {}
    marks = list(_HEAD_RE.finditer(body))
    if not marks:
        return {"title": "", "logline": "", "body": body}
    bm = next((m for m in marks if m.group(1) == "正文"), None)
    for m in marks:
        if m.group(1) == "正文":
            continue
        # 取该标记到下一个标记之间（单行通常）
        nxt = next((x for x in marks if x.start() > m.start()), None)
        seg = body[m.end():(nxt.start() if nxt else len(body))].strip()
        fields[m.group(1)] = seg
    if bm:
        body_text = body[bm.end():].strip()
    else:
        # 没有「正文：」标记 —— 去掉头部若干行
        body_text = body
    title = fields.get("标题") or fields.get("剧名") or ""
    logline = fields.get("梗概") or fields.get("一句话") or ""
    return {"title": title.strip(), "logline": logline.strip(), "body": body_text.strip() or body}


# ---------------- 解析：分集 ----------------

_EP_HEAD_RE = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:第\s*([0-9０-９一二三四五六七八九十]+)\s*集|E(?:P)?\s*([0-9]+))\s*[:：、.．]?\s*(.*)$",
    re.M,
)


def parse_episodes(text: str) -> list[dict]:
    """把模型输出解析成 [{number,title,synopsis,script}]。先试 JSON，再退化到「第N集」标记切分。"""
    data = _json_block(text)
    if isinstance(data, dict):
        data = data.get("episodes") or data.get("list") or data.get("data")
    if isinstance(data, list):
        out: list[dict] = []
        for i, it in enumerate(data):
            if not isinstance(it, dict):
                continue
            out.append({
                "number": _as_int(it.get("number") or it.get("no") or it.get("index"), i + 1),
                "title": _norm(it.get("title") or it.get("name")),
                "synopsis": _norm(it.get("synopsis") or it.get("summary") or it.get("outline")),
                "script": _norm(it.get("script") or it.get("content") or it.get("text")),
            })
        if out:
            return _renumber(out)

    body = _strip_fence(text)
    marks = list(_EP_HEAD_RE.finditer(body))
    if not marks:
        return []
    out = []
    for k, m in enumerate(marks):
        end = marks[k + 1].start() if k + 1 < len(marks) else len(body)
        chunk = body[m.end():end].strip()
        raw_no = m.group(1) or m.group(2) or ""
        title = _norm(m.group(3))
        syn, script = "", chunk
        sm = re.search(r"^\s*(?:梗概|简介|概要)\s*[:：]\s*(.+)$", chunk, re.M)
        if sm:
            syn = sm.group(1).strip()
        bm = re.search(r"^\s*(?:正文|剧本|内容)\s*[:：]\s*", chunk, re.M)
        if bm:
            script = chunk[bm.end():].strip()
        elif sm:
            script = chunk[sm.end():].strip()
        out.append({
            "number": _as_int(raw_no, k + 1),
            "title": title,
            "synopsis": syn,
            "script": script,
        })
    return _renumber(out)


def _renumber(items: list[dict]) -> list[dict]:
    """集号去重并保证从 1 连续递增（模型常给重复或跳号）。"""
    seen: set[int] = set()
    out: list[dict] = []
    nxt = 1
    for it in items:
        n = int(it.get("number") or 0)
        if n <= 0 or n in seen:
            while nxt in seen:
                nxt += 1
            n = nxt
        seen.add(n)
        it["number"] = n
        out.append(it)
    return sorted(out, key=lambda x: x["number"])


# ---------------- 解析：单集续写 ----------------

def parse_single_episode(text: str) -> dict:
    body = _strip_fence(text)
    title = synopsis = ""
    script = body
    tm = re.search(r"^\s*(?:标题|集名)\s*[:：]\s*(.+)$", body, re.M)
    sm = re.search(r"^\s*(?:梗概|简介|概要)\s*[:：]\s*(.+)$", body, re.M)
    bm = re.search(r"^\s*(?:正文|剧本|内容)\s*[:：]\s*", body, re.M)
    if tm:
        title = tm.group(1).strip()
    if sm:
        synopsis = sm.group(1).strip()
    if bm:
        script = body[bm.end():].strip()
    elif sm:
        script = body[sm.end():].strip()
    return {"title": title, "synopsis": synopsis, "script": script}


# ---------------- 提示词构建 ----------------

def _project_block(project: dict, req: dict) -> str:
    lines = [f"【项目】{project.get('name') or '未命名'}"]
    genre = _norm(req.get("genre")) or _norm(project.get("genre"))
    if genre:
        lines.append(f"【题材】{genre}")
    style = _norm(req.get("visual_style")) or _norm(project.get("visual_style"))
    style_cn = {"live_action": "写实真人", "anime": "动漫", "3d": "3D"}.get(style, style)
    if style_cn:
        lines.append(f"【画面风格】{style_cn}")
    ratio = project.get("aspect_ratio") or "9:16"
    if ratio == "9:16":
        lines.append("【画幅】竖屏 9:16（手机竖屏观看）")
    elif ratio:
        lines.append(f"【画幅】{ratio}")
    return "\n".join(lines)


def build_script_messages(project: dict, req: dict) -> list[dict]:
    """① 整部剧本生成：创作要求（自由文本）+ 可选结构化参数。"""
    eps = _as_int(req.get("episodes"), 0) or None
    mins = req.get("minutes_per_episode")
    lines = [
        "请创作一部竖屏微短剧的完整剧本。",
        "",
        _project_block(project, req),
    ]
    if eps:
        lines.append(f"【体量】全剧共 {eps} 集" + (f"，单集约 {mins} 分钟" if mins else ""))
    elif mins:
        lines.append(f"【体量】单集约 {mins} 分钟")
    requirement = _norm(req.get("requirement"))
    if requirement:
        lines += ["", "【创作要求】", requirement]
    lines += [
        "",
        "【输出格式】（严格遵守，不要输出其它内容）",
        "标题：给这部剧起一个标题",
        "梗概：一句话讲清整个故事",
        "正文：",
        "（完整剧本正文。按场景推进，场景之间用「场景：地点/时间」开头；"
        "对白写成「角色：台词」独立成行；动作与画面描述写在括号外，直接叙述。"
        "要求可直接用于后续分镜拆解，画面感强，不写抽象心理描写。）",
    ]
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "\n".join(lines)},
    ]


def build_revise_messages(project: dict, current: str, instruction: str, req: dict | None = None) -> list[dict]:
    """② 在现有剧本上按意见重写（继续调 DeepSeek 迭代）。"""
    req = req or {}
    lines = [
        "下面是一部竖屏微短剧的现有剧本，请按我的修改意见重写。",
        "",
        _project_block(project, req),
        "",
        "【现有剧本】",
        current,
        "",
        "【修改意见】",
        _norm(instruction) or "整体打磨，增强节奏与钩子。",
        "",
        "【要求】保留原有正确的设定与人物名；只输出修改后的完整剧本，"
        "格式与原文一致（标题/梗概/正文 三段），不要输出修改说明。",
    ]
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "\n".join(lines)},
    ]


def build_split_messages(project: dict, script_text: str, req: dict) -> list[dict]:
    """③ 智能分集：把整部剧本切成 N 集，返回 JSON 便于精确落库。"""
    eps = _as_int(req.get("episodes"), 0)
    lines = [
        "下面是一部竖屏微短剧的完整剧本，请把它切分成分集结构。",
        "",
        _project_block(project, req),
    ]
    if eps:
        lines.append(f"【目标集数】{eps} 集（若剧本内容不足以支撑，可少分但不要注水）")
    else:
        lines.append("【目标集数】由你根据剧情自然节奏决定，通常 3-6 集")
    lines += [
        "",
        "【完整剧本】",
        script_text,
        "",
        "【要求】",
        "1. 每集结尾必须留钩子（悬念/反转），保证观众想追下一集；",
        "2. 每集内容按剧本原顺序切分，不要打乱、不要新增剧情；",
        "3. 每集 200-500 字为宜（竖屏微短剧单集时长 1-2 分钟）；",
        "4. 只输出 JSON，不要任何解释文字，不要 Markdown 代码块。",
        "",
        "【输出 JSON 格式】",
        '[{"number":1,"title":"本集标题","synopsis":"一句话梗概","script":"本集剧本正文"}]',
    ]
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "\n".join(lines)},
    ]


def build_continue_messages(project: dict, script_text: str, existing: list[dict], req: dict) -> list[dict]:
    """④ 集数管理：按已有剧情续写下一集。"""
    target = _as_int(req.get("number"), 0) or (len(existing) + 1)
    lines = [
        f"下面是这部剧已写好的部分，请续写第 {target} 集。",
        "",
        _project_block(project, req),
    ]
    if script_text:
        lines += ["", "【全剧剧本】", script_text]
    if existing:
        lines += ["", "【已完成的分集】"]
        for e in existing:
            lines.append(
                f"第{e.get('number')}集 {e.get('title') or ''}"
                + (f" —— {e.get('synopsis')}" if e.get("synopsis") else "")
            )
    requirement = _norm(req.get("requirement"))
    lines += [
        "",
        "【本集要求】",
        requirement or "承接上一集结尾的钩子，推进主线，结尾再留一个新钩子。",
        "",
        "【输出格式】（严格遵守，不要输出其它内容）",
        "标题：本集标题",
        "梗概：一句话梗概",
        "正文：",
        "（本集完整剧本正文，200-500 字，格式与全剧剧本一致）",
    ]
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "\n".join(lines)},
    ]


# ---------------- 落库 ----------------

def next_version(project_id: int) -> int:
    row = db.query_one("SELECT COALESCE(MAX(version),0) AS v FROM scripts WHERE project_id=?", (project_id,))
    return int((row or {}).get("v") or 0) + 1


def save_script(
    project_id: int,
    content: str,
    *,
    title: str | None = None,
    prompt_used: str | None = None,
    source: str = "ai",
    kind: str = "script",
    episode_id: int | None = None,
    meta: dict | None = None,
) -> int:
    """新建一个剧本版本，返回 script_id。"""
    return db.execute(
        """INSERT INTO scripts(project_id, version, kind, title, content, source, prompt_used, episode_id, meta)
           VALUES(?,?,?,?,?,?,?,?,?)""",
        (project_id, next_version(project_id), kind, title, content, source, prompt_used,
         episode_id, jdumps(meta or {})),
    )


def apply_episodes(project_id: int, items: list[dict]) -> dict:
    """把（人工确认后的）分集结果写进 episodes：同集号更新，新集号插入，多余的不动。"""
    created = updated = 0
    for it in items:
        num = _as_int(it.get("number"), 0)
        if num <= 0:
            continue
        title = _norm(it.get("title")) or None
        synopsis = _norm(it.get("synopsis")) or None
        script = _norm(it.get("script")) or ""
        row = db.query_one("SELECT id FROM episodes WHERE project_id=? AND number=?", (project_id, num))
        if row:
            db.execute(
                """UPDATE episodes SET title=COALESCE(?, title), synopsis=COALESCE(?, synopsis),
                       script_text=CASE WHEN ?='' THEN script_text ELSE ? END,
                       updated_at=datetime('now','localtime')
                   WHERE id=?""",
                (title, synopsis, script, script, row["id"]),
            )
            updated += 1
        else:
            db.execute(
                """INSERT INTO episodes(project_id, number, title, synopsis, script_text, status, sort_order)
                   VALUES(?,?,?,?,?,?,?)""",
                (project_id, num, title, synopsis, script, "draft", num),
            )
            created += 1
    return {"created": created, "updated": updated, "total": len(items)}


# ============================================================
# 结构化出稿：集结构 + 每集镜头清单（一次调用）
# ============================================================
# 与「先写整篇剧本 → 再单独分集」的区别：这里一次就把集结构和镜头清单一起产出，
# 落库后可修改；提示词**不在这一步出**，改成按集逐次出（质量稳、漏了只补那一集）。

SYSTEM_OUTLINE = (
    "你是资深竖屏微短剧编剧兼分镜师。你输出的内容会被程序直接解析入库，"
    "所以必须只输出一个严格合法的 JSON 对象：不要任何解释文字，不要 Markdown 代码块，"
    "不要在 JSON 前后加任何字符。JSON 里的字符串必须用双引号，且不能出现未转义的换行。"
)

_TYPE_LABEL = {"character": "角色", "scene": "场景", "prop": "道具", "costume": "服装"}

SHOT_SIZE_CN = ("大特写", "特写", "中近景", "中景", "中远景", "全景", "大远景")


def _num(v: Any, default: float) -> float:
    try:
        f = float(v)
        return f if f > 0 else default
    except Exception:
        return default


def _asset_catalog(assets: list[dict]) -> str:
    """把项目资产整理成「可出场资产清单」给模型看（它只能从中选，不许编造）。"""
    groups: dict[str, list[str]] = {}
    for a in assets:
        nm = _norm(a.get("name"))
        if nm:
            groups.setdefault(a.get("asset_type") or "other", []).append(nm)
    lines: list[str] = []
    for k in ("character", "scene", "prop", "costume"):
        names = groups.get(k) or []
        if names:
            lines.append(f"- {_TYPE_LABEL.get(k, k)}：{'、'.join(names)}")
    if not lines:
        return "（本项目还没有登记资产，所有镜头的 assets 一律给空数组 []）"
    return "\n".join(lines)


def build_outline_messages(project: dict, req: dict, assets: list[dict]) -> list[dict]:
    """① 结构化出稿：一次产出「集结构 + 每集镜头清单」（不含提示词）。"""
    eps = _as_int(req.get("episodes"), 0) or 3
    mins = _num(req.get("minutes_per_episode"), 2.0)
    per_ep = _as_int(req.get("shots_per_episode"), 0) or max(6, min(20, round(mins * 60 / 6)))
    lines = [
        "请创作一部竖屏微短剧，并直接给出「分集结构 + 每集镜头清单」。",
        "",
        _project_block(project, req),
        f"【体量】全剧共 {eps} 集；单集约 {mins:g} 分钟；每集约 {per_ep} 个镜头",
        "",
        "【出场资产（assets）】每个镜头都要写本镜出场的角色 / 场景 / 道具的中文名"
        "（从剧本逻辑里识别、自由写，例如 过客、公司办公室）；"
        "资产图是后续才单独生成并登记进资产库的，这里只登记名字，不要去匹配已有资产。"
    ]
    requirement = _norm(req.get("requirement"))
    if requirement:
        lines += ["", "【创作要求】", requirement]
    lines += [
        "",
        "【分镜要求】",
        "1. 每集结尾必须留钩子（悬念或反转），保证观众想追下一集；",
        "2. shot_code 是集内镜号：从 1 开始连续编号（1、2、3…）；"
        "一个镜头需要拆成前后两拍时用字母后缀（4a、4b），不要用「镜头1」这种写法；",
        f"3. 单镜 3-10 秒，每集各镜 duration 之和约 {mins * 60:.0f} 秒；",
        "4. summary 只写「这一镜画面里能看到什么」：谁在做什么、镜头看到什么。"
        "不写运镜、不写视角术语、不写「承接上一镜/上镜尾帧/视线落点」等跨镜交代；",
        "5. dialog 写这一镜真的说出来的台词原文，一句一条，整句不拆；没有说话就给空数组；",
        "6. shot_size 只能取：" + " / ".join(SHOT_SIZE_CN) + "；",
        "7. script 是本集完整剧本正文：场景用「场景：地点/时间」开头，"
        "对白写成「角色：台词」独立成行，动作与画面直接叙述，不写抽象心理描写。",
        "",
        "【输出 JSON 格式】（严格遵守，只输出这一个 JSON）",
        "{",
        '  "title": "剧名",',
        '  "logline": "一句话讲清整个故事",',
        '  "episodes": [',
        "    {",
        '      "number": 1,',
        '      "title": "本集标题",',
        '      "synopsis": "本集一句话梗概",',
        '      "script": "本集完整剧本正文",',
        '      "shots": [',
        "        {",
        '          "shot_code": "1",',
        '          "title": "镜头摘要（12 字内）",',
        '          "summary": "这一镜拍到什么、谁在做什么",',
        '          "assets": ["过客", "公司办公室"],',
        '          "dialog": [{"role": "过客", "text": "台词原文"}],',
        '          "shot_size": "中近景",',
        '          "duration": 5',
        "        }",
        "      ]",
        "    }",
        "  ]",
        "}",
    ]
    return [
        {"role": "system", "content": SYSTEM_OUTLINE},
        {"role": "user", "content": "\n".join(lines)},
    ]


def parse_outline(text: str) -> dict:
    """解析结构化出稿。JSON 解析失败时 _parsed=False，原文放 _raw 交人工处理。"""
    data = _json_block(text)
    eps_raw = None
    if isinstance(data, dict):
        eps_raw = data.get("episodes") or data.get("list") or data.get("data")
    out_eps: list[dict] = []
    if isinstance(eps_raw, list):
        for i, e in enumerate(eps_raw):
            if not isinstance(e, dict):
                continue
            shots: list[dict] = []
            for s in (e.get("shots") or []):
                if not isinstance(s, dict):
                    continue
                code = _norm(s.get("shot_code") or s.get("code") or s.get("no"))
                if not code:
                    continue
                dialog: list[dict] = []
                for d in (s.get("dialog") or s.get("dialogs") or s.get("lines") or []):
                    if isinstance(d, dict):
                        txt = _norm(d.get("text") or d.get("line"))
                        if txt:
                            dialog.append({"role": _norm(d.get("role") or d.get("name")), "text": txt})
                    elif isinstance(d, str) and d.strip():
                        dialog.append({"role": "", "text": d.strip()})
                shots.append({
                    "shot_code": code,
                    "title": _norm(s.get("title")),
                    "summary": _norm(s.get("summary") or s.get("desc") or s.get("body")),
                    "assets": [_norm(x) for x in (s.get("assets") or []) if _norm(x)],
                    "dialog": dialog,
                    "shot_size": _norm(s.get("shot_size")),
                    "duration": _num(s.get("duration") or s.get("duration_sec"), 5.0),
                })
            out_eps.append({
                "number": _as_int(e.get("number") or e.get("no"), i + 1),
                "title": _norm(e.get("title")),
                "synopsis": _norm(e.get("synopsis") or e.get("summary") or e.get("outline")),
                "script": _norm(e.get("script") or e.get("content") or e.get("text")),
                "shots": shots,
            })
    if not out_eps:
        return {"title": _norm((data or {}).get("title") if isinstance(data, dict) else ""),
                "logline": _norm((data or {}).get("logline") if isinstance(data, dict) else ""),
                "episodes": [], "_parsed": False, "_raw": _strip_fence(text)}
    meta = data if isinstance(data, dict) else {}
    return {
        "title": _norm(meta.get("title")),
        "logline": _norm(meta.get("logline") or meta.get("synopsis")),
        "episodes": _renumber(out_eps),
        "_parsed": True,
    }


# ---------------- 资产匹配与参考图槽位 ----------------

# 槽位约定（沿用本项目既有素材实证，不可改）：
#   图片侧：参考图 1..N = 出场资产（分镜图不需要把自己当参考图）
#   视频侧：Image 1（= ref_image_0）= 本镜首帧分镜图；Image 2..N = 出场资产
_TAKE_NOTE = {
    "character": "严格锁定其面部特征、发型、服饰与体型",
    "scene": "仅作场景环境参考（布局与陈设以本提示词为准）",
    "prop": "道具外观参考，仅取造型与材质",
    "costume": "服装参考，仅取款式与配色",
}

_ROLE_LABEL = {
    "character": "形态锚点",
    "scene": "环境锚点",
    "prop": "道具锚点",
    "costume": "服装锚点",
}


def _asset_rows(project_id: int) -> list[dict]:
    return db.query("SELECT * FROM assets WHERE project_id=?", (project_id,))


def match_asset(project_id: int, name: str, rows: list[dict] | None = None) -> dict | None:
    """按中文名/别名匹配项目资产。先精确、再包含。"""
    nm = _norm(name).lower()
    if not nm:
        return None
    rows = _asset_rows(project_id) if rows is None else rows

    def aliases(a: dict) -> list[str]:
        return [_norm(a.get("name")).lower()] + [str(x).lower() for x in (jloads(a.get("alias"), []) or [])]

    for a in rows:
        if any(nm == x for x in aliases(a) if x):
            return a
    for a in rows:
        if any(x and (nm in x or x in nm) for x in aliases(a)):
            return a
    return None


def _primary_image(asset_id: int) -> dict | None:
    return db.query_one(
        "SELECT id, file_name FROM asset_images WHERE asset_id=? ORDER BY is_primary DESC, id LIMIT 1",
        (asset_id,),
    )


def _write_links(shot_id: int, shot_code: str, ep_number: int, names: list[str],
                 project_id: int, rows: list[dict], unmatched: set[str]) -> int:
    """首帧槽位 + 出场资产槽位（图片侧与视频侧都写）。返回写入条数。

    **视频侧不能留空档**：首帧占 slot 0，出场资产从 slot 1 起连续排（与项目里 I2VA 镜头的
    实测槽位一致：slot0=分镜图、slot1..N=资产）。留空档会让 Image N 与实际 ref_image 错位。
    """
    target = naming.code_stem(shot_code, ep_number) + ".jpg"
    written = 0
    db.execute(
        """INSERT OR REPLACE INTO shot_asset_links
               (shot_id, asset_id, asset_image_id, role, slot_index, target_side,
                ref_version, take_note, file_name, raw_text)
           VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (shot_id, None, None, "首帧分镜图", 0, "video", None,
         "视频首帧锚点（0.00 秒）", target, f"Image 1：{target}"),
    )
    written += 1
    slot = 1
    for name in names:
        a = match_asset(project_id, name, rows)
        if not a:
            unmatched.add(name)
            continue
        img = _primary_image(a["id"]) or {}
        fname = img.get("file_name") or f"{a['name']}_参考图"
        note = _TAKE_NOTE.get(a.get("asset_type"), "参考")
        role = _ROLE_LABEL.get(a.get("asset_type"), "参考")
        db.execute(
            """INSERT OR REPLACE INTO shot_asset_links
                   (shot_id, asset_id, asset_image_id, role, slot_index, target_side,
                    ref_version, take_note, file_name, raw_text)
               VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (shot_id, a["id"], img.get("id"), role, slot, "image", "concept", note, fname,
             f"参考图{slot}（{a['name']}）{note}"),
        )
        db.execute(
            """INSERT OR REPLACE INTO shot_asset_links
                   (shot_id, asset_id, asset_image_id, role, slot_index, target_side,
                    ref_version, take_note, file_name, raw_text)
               VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (shot_id, a["id"], img.get("id"), role, slot, "video", "concept", note, fname,
             f"Image {slot + 1}：{fname}"),
        )
        slot += 1
        written += 2
    return written


def apply_outline(project_id: int, data: dict, *, replace_shots: bool = False) -> dict:
    """把（人工确认/编辑过的）结构化出稿落库。**直接落库、随后可修改**。

    保护性规则（避免污染已有工作成果）：
    - 同镜号已存在 → 只更新标题/摘要/时长，**绝不覆盖已写好的提示词**；
    - 镜头的参考图槽位与台词**只在还没有时写**，不用清单里的值覆盖手工配置；
    - `replace_shots=True` 时才会删除清单里不再出现的镜头（默认不删）。
    """
    rows = _asset_rows(project_id)
    ep_created = ep_updated = sh_created = sh_updated = 0
    links = lines = 0
    unmatched: set[str] = set()

    for ep in data.get("episodes") or []:
        num = _as_int(ep.get("number"), 0)
        if num <= 0:
            continue
        title = _norm(ep.get("title")) or f"第{num}集"
        syn = _norm(ep.get("synopsis")) or None
        script = _norm(ep.get("script"))
        row = db.query_one("SELECT * FROM episodes WHERE project_id=? AND number=?", (project_id, num))
        if row:
            eid = row["id"]
            db.execute(
                """UPDATE episodes SET title=?, synopsis=COALESCE(?, synopsis),
                       script_text=CASE WHEN ?='' THEN script_text ELSE ? END,
                       updated_at=datetime('now','localtime')
                   WHERE id=?""",
                (title, syn, script, script, eid),
            )
            ep_updated += 1
        else:
            eid = db.execute(
                """INSERT INTO episodes(project_id, number, title, synopsis, script_text, status, sort_order)
                   VALUES(?,?,?,?,?,?,?)""",
                (project_id, num, title, syn, script, "draft", num),
            )
            ep_created += 1

        existing = {_norm(s.get("shot_code")): s
                    for s in db.query("SELECT * FROM shots WHERE episode_id=?", (eid,))}
        if replace_shots:
            keep = {_norm(s.get("shot_code")) for s in (ep.get("shots") or [])}
            for code, s in list(existing.items()):
                if code and code not in keep:
                    db.execute("DELETE FROM shots WHERE id=?", (s["id"],))
                    existing.pop(code, None)

        for i, sh in enumerate(ep.get("shots") or []):
            code = _norm(sh.get("shot_code"))
            if not code:
                continue
            dur = _num(sh.get("duration"), 5.0)
            size = _norm(sh.get("shot_size")) or None
            summary = _norm(sh.get("summary")) or None
            srow = existing.get(code)
            if srow:
                sid = srow["id"]
                db.execute(
                    """UPDATE shots SET title=?, sort_order=?, updated_at=datetime('now','localtime')
                       WHERE id=?""",
                    (_norm(sh.get("title")) or None, i, sid),
                )
                if db.query_one("SELECT 1 FROM shot_details WHERE shot_id=?", (sid,)):
                    db.execute(
                        """UPDATE shot_details SET summary=COALESCE(?, summary),
                               duration_sec=COALESCE(?, duration_sec),
                               camera_shot=COALESCE(?, camera_shot),
                               updated_at=datetime('now','localtime')
                           WHERE shot_id=?""",
                        (summary, dur, size, sid),
                    )
                else:
                    db.execute(
                        """INSERT INTO shot_details(shot_id, summary, duration_sec, camera_shot, gen_mode)
                           VALUES(?,?,?,?,?)""",
                        (sid, summary, dur, size, "I2VA"),
                    )
                sh_updated += 1
            else:
                sid = db.execute(
                    "INSERT INTO shots(episode_id, shot_code, title, sort_order) VALUES(?,?,?,?)",
                    (eid, code, _norm(sh.get("title")) or None, i),
                )
                db.execute(
                    """INSERT INTO shot_details(shot_id, summary, duration_sec, camera_shot, gen_mode)
                       VALUES(?,?,?,?,?)""",
                    (sid, summary, dur, size, "I2VA"),
                )
                sh_created += 1
            # 创作期只记录本镜出场资产中文名，不在此处匹配资产库（资产图后续才出）
            db.execute(
                "UPDATE shot_details SET assets_text=? WHERE shot_id=?",
                (json.dumps(sh.get("assets") or [], ensure_ascii=False), sid),
            )

            hl = db.query_one("SELECT COUNT(*) AS c FROM shot_dialog_lines WHERE shot_id=?", (sid,))
            if not ((hl or {}).get("c") or 0):
                for k, d in enumerate(sh.get("dialog") or []):
                    txt = _norm(d.get("text"))
                    if not txt:
                        continue
                    role = _norm(d.get("role"))
                    a = match_asset(project_id, role, rows) if role else None
                    db.execute(
                        """INSERT INTO shot_dialog_lines(shot_id, line_index, role_name, asset_id, text, line_mode)
                           VALUES(?,?,?,?,?,?)""",
                        (sid, k + 1, role or None, (a or {}).get("id"), txt, "dialogue"),
                    )
                    lines += 1

    return {
        "episodes_created": ep_created, "episodes_updated": ep_updated,
        "shots_created": sh_created, "shots_updated": sh_updated,
        "links_written": links, "dialog_written": lines,
        "unmatched_assets": sorted(unmatched),
    }


# ============================================================
# 按集出双份提示词（一次只处理一集）
# ============================================================

SYSTEM_SHOT_PROMPTS = (
    "你是资深竖屏微短剧分镜师兼 AI 视频提示词工程师。你输出的内容会被程序直接解析入库，"
    "必须只输出一个严格合法的 JSON 数组：不要解释、不要 Markdown 代码块。"
)

# 声明行（`Image 1：xxx.jpg` / `Audio 1：…`）必须带冒号才算；否则会把正文行误删
_DECL_LINE_RE = re.compile(r"^\s*(素材关系声明|素材声明)\s*[:：]?\s*$")
_REF_LINE_RE = re.compile(r"^\s*(Image|Audio|Picture)\s*\d+\s*[:：]")
# 模型有时会自己拼「参考图1（资产名）用途；」前缀，整段剥掉（吃到条目结束符为止）
_IMG_DECL_PREFIX_RE = re.compile(r"^\s*(?:参考图\s*\d+\s*[（(][^）)]*[）)][^；;。]*[；;]\s*)+")


def sanitize_body(s: str) -> str:
    """剥掉模型误写的「素材声明 / Image N 行」与自己拼的「参考图N（…）…；」前缀。"""
    keep = [ln for ln in (s or "").splitlines()
            if not (_DECL_LINE_RE.match(ln) or _REF_LINE_RE.match(ln))]
    out = "\n".join(keep).strip()
    out = _IMG_DECL_PREFIX_RE.sub("", out).strip()
    for ch in ("素材关系声明：", "素材关系声明:"):
        if out.startswith(ch):
            out = out[len(ch):].strip()
    return out


def _shot_brief(shot: dict, links: list[dict]) -> list[str]:
    names: list[str] = []
    for r in links:
        nm = _norm(r.get("asset_name"))
        if nm and nm not in names:
            names.append(nm)
    # 链接为空（资产图尚未生成/绑定）时，回退到创作期登记的资产中文名
    if not names:
        raw = shot.get("assets_text")
        if isinstance(raw, str) and raw.strip():
            try:
                arr = json.loads(raw)
            except Exception:
                arr = [raw]
            if isinstance(arr, list):
                for x in arr:
                    nm = _norm(x)
                    if nm and nm not in names:
                        names.append(nm)
    if names:
        out.append("  本镜出场资产：" + "、".join(names))
    if shot.get("lines"):
        out.append("  台词：" + "；".join(f"{l.get('role_name') or ''}：{l.get('text')}" for l in shot["lines"]))
    return out


def build_shot_prompts_messages(project: dict, episode: dict,
                                shots: list[dict], req: dict) -> list[dict]:
    """② 按集出双份提示词：只处理这一集，一次给出每个镜头的分镜图 + 视频提示词。"""
    num = episode.get("number") or 1
    dur_total = sum(float(s.get("duration_sec") or 5) for s in shots)
    lines = [
        f"下面是《{project.get('name') or '未命名'}》第 {num} 集的镜头清单，"
        "请为每一个镜头写出【分镜图提示词】和【视频提示词】。",
        "",
        _project_block(project, req),
        f"【本集】第 {num} 集 {episode.get('title') or ''}".rstrip(),
    ]
    if _norm(episode.get("synopsis")):
        lines.append(f"【本集梗概】{_norm(episode.get('synopsis'))}")
    if _norm(episode.get("script_text")):
        lines += ["", "【本集剧本正文】", _norm(episode.get("script_text"))]
    lines += ["", "【镜头清单】"]
    for s in shots:
        lines += _shot_brief(s, s.get("links") or [])
    lines += [
        "",
        f"【总时长】本集各镜 duration 之和须等于清单里的值（当前合计 {dur_total:g} 秒），不要改镜头数量。",
        "",
        "【image_body 的写法（分镜图提示词正文）】",
        "1. 只写「这张图长什么样」：画面内容、人物姿态与表情、构图落幅、光照、环境陈设、风格尾；",
        "2. 严禁写运镜、镜头运动、机位移动、POV/第一人称说明、时长；",
        "3. 严禁写「参考图1」「Image 1」「素材声明」这类编号与声明——参考素材声明由程序自动拼装；",
        "4. 严禁跨镜交代（不写「承接上一镜」「上镜尾帧」「视线落点」）；",
        "5. 只描述本镜真正出现在画面里的角色；单角色镜头不要提其他角色；",
        "6. 手持物一律写在左手；",
        "7. 结尾带写实风格尾（如「写实人物摄影，电影质感，浅景深」）。",
        "",
        "【video_body 的写法（视频提示词正文）】严格按下面四段拼接，段间用换行分隔：",
        "第 1 段：`机位：<视角>视角；运镜：<运镜>。`"
        "视角只能取：平视 / 高机位俯拍 / 低机位仰拍 / 垂直顶机位俯拍 / 荷兰角倾斜机位 / 过肩机位 / 第一人称机位 / 背面机位；"
        "运镜只能取：固定机位 / 横摇 / 纵摇 / 推近 / 拉远 / 跟移 / 升降 / 手持 / 稳定器 / 变焦推 / 变焦拉。",
        "第 2 段：`画面主体：`换行后以 `[Shot 1] Live-action，cinematic，竖屏 9:16 构图。` 开头，"
        "写这一镜的完整画面与动作过程（可含景别与构图），禁止跨镜交代。",
        "第 3 段：`画面任务指令（严格按时序，画面与声音同步生成）：`换行后逐拍写"
        "`0.0–1.2秒：……`，拍点必须时间连续、首尾覆盖整镜时长，且各拍时长之和等于该镜 duration。",
        "第 4 段：台词必须写成「角色：\"台词\"」，整句一口气说完、不拆不重复；没有台词就不写。",
        "另外：严禁写「素材声明」「Image N」「Audio N」；"
        "严禁黑场、黑帧、淡入、淡出、溶解、叠化；不写字幕、水印。",
        "",
        "【输出 JSON 数组】（严格遵守，只输出这一个数组；shot_code 必须与清单完全一致，不得增删镜头）",
        "[",
        '  {"shot_code": "1",',
        '   "image_body": "分镜图提示词正文",',
        '   "video_body": "机位：平视视角；运镜：推近。\\n画面主体：\\n[Shot 1] Live-action，cinematic，竖屏 9:16 构图。……\\n\\n画面任务指令（严格按时序，画面与声音同步生成）：\\n0.0–2.4秒：……"}',
        "]",
    ]
    return [
        {"role": "system", "content": SYSTEM_SHOT_PROMPTS},
        {"role": "user", "content": "\n".join(lines)},
    ]


def parse_shot_prompts(text: str) -> list[dict]:
    data = _json_block(text)
    if isinstance(data, dict):
        data = data.get("shots") or data.get("items") or data.get("list")
    out: list[dict] = []
    if isinstance(data, list):
        for it in data:
            if not isinstance(it, dict):
                continue
            code = _norm(it.get("shot_code") or it.get("code") or it.get("no"))
            if not code:
                continue
            img = sanitize_body(_norm(it.get("image_body") or it.get("image") or it.get("image_prompt")))
            vid = sanitize_body(_norm(it.get("video_body") or it.get("video") or it.get("video_prompt")))
            if not img and not vid:
                continue
            out.append({"shot_code": code, "image_body": img, "video_body": vid})
    return out


# ---------------- 素材声明自动拼装（编号严格按真实槽位） ----------------

def _side_links(shot_id: int, side: str) -> list[dict]:
    return db.query(
        """SELECT l.*, a.name AS asset_name, a.asset_type AS asset_type
           FROM shot_asset_links l
           LEFT JOIN assets a ON a.id = l.asset_id
           WHERE l.shot_id=? AND l.target_side=? ORDER BY l.slot_index""",
        (shot_id, side),
    )


def compose_image_decl(shot_id: int) -> str:
    """分镜图侧的参考图声明：`参考图1（资产名）用途；参考图2（…）…`

    编号取**真实槽位号**（不是列表位置），所以槽位被手工调整过也不会与上传顺序错位。
    """
    segs: list[str] = []
    for i, r in enumerate(_side_links(shot_id, "image")):
        n = int(r.get("slot_index") if r.get("slot_index") is not None else i + 1)
        name = _norm(r.get("asset_name")) or (_norm(r.get("file_name")).rsplit(".", 1)[0])
        note = _norm(r.get("take_note")) or _TAKE_NOTE.get(r.get("asset_type"), "参考")
        segs.append(f"参考图{n}（{name}）{note}；")
    return "".join(segs)


def compose_video_decl(shot_id: int) -> str:
    """视频侧的素材关系声明：`Image 1` 是本镜首帧，其后是出场资产。

    编号取**真实槽位号 + 1**（因为 `Image N == ref_image_(N-1)`，槽位 0 即 Image 1），
    所以声明里的 Image N 与接口参数 ref_image_(N-1) 永远一致。

    这里只写 `Image N`，不写 `（= Picture N）`：全篇统一一个口径，模型不用去猜两个
    名字是不是同一张；Picture 口径的字样留给接口首行那句英文模板，不混进中文声明。
    """
    lines = ["素材关系声明："]
    for k, d in enumerate(db.query(
            "SELECT * FROM shot_dialog_lines WHERE shot_id=? ORDER BY line_index, id", (shot_id,))):
        role = _norm(d.get("role_name"))
        if role and _norm(d.get("text")):
            lines.append(f'Audio {k + 1}：{role}音色参考，台词"{_norm(d.get("text"))}"')
    for i, r in enumerate(_side_links(shot_id, "video")):
        slot = int(r.get("slot_index") if r.get("slot_index") is not None else i)
        fname = _norm(r.get("file_name")) or "（未指定）"
        if slot == 0:
            lines.append(f"Image 1：{fname} —— 视频首帧锚点（0.00 秒），"
                         "画面起始状态严格以它为准")
            continue
        note = _norm(r.get("take_note")) or _TAKE_NOTE.get(r.get("asset_type"), "参考")
        lines.append(f"Image {slot + 1}：{fname} —— {note}")
    return "\n".join(lines) + "\n\n"


def compose_image_prompt(shot_id: int, body: str) -> str:
    decl = compose_image_decl(shot_id)
    head = f"{decl}" if decl else ""
    return f"{head}竖屏9:16构图。{body}".strip()


def compose_video_prompt(shot_id: int, body: str) -> str:
    return f"{compose_video_decl(shot_id)}{body}".strip()


# ---------------- 回填 ----------------

def i2va_prefix() -> str:
    """取系统里的 I2VA 首行模板（视频侧首行模式声明）。"""
    row = db.query_one(
        """SELECT content FROM prompt_templates
           WHERE category='video_prefix' AND content LIKE '%0.00 seconds%'
           ORDER BY is_default DESC, id LIMIT 1"""
    )
    return (row or {}).get("content") or (
        "For the target video, at 0.00 seconds into the target video, "
        "<Picture 1> (from [Shot 1]) is fully referenced."
    )


def apply_shot_prompts(episode_id: int, items: list[dict], *, model: str | None = None) -> dict:
    """把双份提示词回填到镜头。声明由工作台自动拼，写入正文与首行。"""
    ep = db.query_one("SELECT * FROM episodes WHERE id=?", (episode_id,))
    if not ep:
        raise ValueError("集不存在")
    prefix = i2va_prefix()
    updated = 0
    missing: list[str] = []
    for it in items:
        code = _norm(it.get("shot_code"))
        body_i = sanitize_body(_norm(it.get("image_body")))
        body_v = sanitize_body(_norm(it.get("video_body")))
        row = db.query_one("SELECT * FROM shots WHERE episode_id=? AND shot_code=?", (episode_id, code))
        if not row:
            missing.append(code)
            continue
        sid = row["id"]
        sets: list[str] = []
        vals: list[Any] = []
        if body_i:
            sets += ["image_prompt=?", "image_target_name=?"]
            vals += [compose_image_prompt(sid, body_i), naming.code_stem(code, ep.get("number") or 1) + ".jpg"]
        if body_v:
            sets += ["video_prompt=?", "video_prompt_prefix=COALESCE(NULLIF(video_prompt_prefix,''), ?)"]
            vals += [compose_video_prompt(sid, body_v), prefix]
        if not sets:
            continue
        sets.append("updated_at=datetime('now','localtime')")
        vals.append(sid)
        if db.query_one("SELECT 1 FROM shot_details WHERE shot_id=?", (sid,)):
            db.execute(f"UPDATE shot_details SET {', '.join(sets)} WHERE shot_id=?", vals)
        else:
            cols = [s.split("=")[0] for s in sets if not s.startswith("updated_at")]
            db.execute(
                f"INSERT INTO shot_details(shot_id, {', '.join(cols)}) VALUES(?{', ?' * len(cols)})",
                [sid] + [v for s, v in zip(sets, vals) if not s.startswith("updated_at")],
            )
        updated += 1
    return {"updated": updated, "missing_shots": missing,
            "model": model, "note": f"已回填 {updated} 个镜头"}
