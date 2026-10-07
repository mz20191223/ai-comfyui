"""镜头设置向导 → 提示词注入。

**分工（沿用项目铁律）**
- 景别 + 视角 + 主体位置 = 静态构图 → 进分镜图提示词（image_prompt）
- 机位 + 运镜           = 动态     → 进视频提示词（video_prompt）
两者不互相污染：运镜句永远不会被写进分镜图。

**视角为什么两边都写**
用户明确要求「视角两边都要有描述」，所以视角写两遍、措辞分开：
- 分镜图里写成**画面事实**（仰拍 → 可见下巴底面与鼻底），符合「分镜图只写图长什么样」
- 视频里写成**机位指令**（机位：低机位仰拍）

**注入位置**
本项目两份提示词的稳定锚点是「竖屏9:16构图。」，构图句插在该句之后。
视频提示词若以「素材关系声明：」开头，则插在整个声明块之后，不破坏声明块。

**防重复堆叠**
shot_details.wiz_image_note / wiz_video_note 记「上次注入进去的原文」；
再次注入时先按原文做一次替换，替换不到（被手改过）才追加，并把实际情况回报给前端。
"""
from __future__ import annotations

ANCHOR = "竖屏9:16构图"
_DECL_HEADS = ("素材关系声明", "素材声明")
_TERMINATORS = ("。", "！", "；", "\n")

# 视角 → 分镜图里的「画面事实」写法（描述图里看得到什么）
# 注意：除过肩/背身/主观这三种本身与人有关的以外，措辞一律不写「人物」——
# 主体可能是手、键盘、屏幕等物件（如镜头19 是双手特写），写死「人物」会说错。
ANGLE_AS_FACT = {
    "EYE_LEVEL": "平视",
    "HIGH_ANGLE": "俯拍视角，从上方俯视主体",
    "LOW_ANGLE": "仰拍视角，从下方仰视主体",
    "BIRD_EYE": "垂直鸟瞰俯视",
    "DUTCH": "画面整体倾斜约20度的斜角构图",
    "OVER_SHOULDER": "过肩构图，前景一侧有另一人的肩部与后脑剪影",
    "POV": "第一人称视角画面，画面中看不到持机者本人",
    "BEHIND": "主体背对镜头，看不到正面",
}

# 视角 → 视频里的「机位指令」写法
ANGLE_AS_CAMERA = {
    "EYE_LEVEL": "平视",
    "HIGH_ANGLE": "高机位俯拍",
    "LOW_ANGLE": "低机位仰拍",
    "BIRD_EYE": "垂直顶机位俯拍",
    "DUTCH": "荷兰角倾斜机位",
    "OVER_SHOULDER": "过肩机位",
    "POV": "第一人称机位",
    "BEHIND": "背面机位",
}

SHOT_SIZE_LABEL = {
    "ECU": "大特写",
    "CU": "特写",
    "MCU": "中近景",
    "MS": "中景",
    "MLS": "中远景",
    "LS": "全景",
    "ELS": "大远景",
}

MOVEMENT_LABEL = {
    "STATIC": "固定机位",
    "PAN": "横摇",
    "TILT": "纵摇",
    "DOLLY_IN": "推近",
    "DOLLY_OUT": "拉远",
    "TRACK": "跟移",
    "CRANE": "升降",
    "HANDHELD": "手持",
    "STEADICAM": "稳定器",
    "ZOOM_IN": "变焦推",
    "ZOOM_OUT": "变焦拉",
}


def compose_image_note(camera_shot: str | None, angle: str | None,
                       subject_position: str | None) -> str:
    """分镜图构图句：景别 + 视角（画面事实）+ 主体位置。运镜绝不进来。"""
    seg: list[str] = []
    size = SHOT_SIZE_LABEL.get((camera_shot or "").strip(), (camera_shot or "").strip())
    if size:
        seg.append(size)
    fact = ANGLE_AS_FACT.get((angle or "").strip())
    if fact:
        seg.append(fact)
    pos = (subject_position or "").strip()
    if pos:
        if "·" in pos:
            where, dist = pos.split("·", 1)
            seg.append(f"主体位于画面{where}，距离{dist}")
        else:
            seg.append(f"主体位于画面{pos}")
    if not seg:
        return ""
    return "，".join(seg) + "。"


def compose_video_note(angle: str | None, movement: str | None) -> str:
    """视频机位+运镜句。不带景别、不带主体位置（那是分镜图的事）。"""
    seg: list[str] = []
    cam = ANGLE_AS_CAMERA.get((angle or "").strip())
    if cam:
        seg.append(f"机位：{cam}视角")
    mv = MOVEMENT_LABEL.get((movement or "").strip(), (movement or "").strip() if movement else "")
    if mv:
        seg.append(f"运镜：{mv}")
    if not seg:
        return ""
    return "；".join(seg) + "。"


def _insert_pos(prompt: str) -> int:
    """返回插入位置：锚点句之后；无锚点则声明块之后；都没有就给 0。"""
    idx = prompt.find(ANCHOR)
    if idx >= 0:
        end = -1
        for ch in _TERMINATORS:
            p = prompt.find(ch, idx + len(ANCHOR))
            if p != -1 and (end == -1 or p < end):
                end = p
        return end + 1 if end != -1 else idx + len(ANCHOR)
    head = prompt.lstrip()
    if head.startswith(_DECL_HEADS):
        # 跳过整个声明块（到第一个空行为止）
        cut = prompt.find("\n\n")
        return cut + 2 if cut != -1 else len(prompt)
    return 0


def _find_movement_segment(prompt: str) -> str:
    """抽出正文里手写的「运镜：……」片段，用于冲突提示（不自动改它）。"""
    idx = prompt.find("运镜：")
    if idx < 0:
        return ""
    rest = prompt[idx:]
    end = -1
    for ch in _TERMINATORS:
        p = rest.find(ch, len("运镜："))
        if p != -1 and (end == -1 or p < end):
            end = p
    return rest[: end + 1] if end != -1 else rest[:80]


def _find_size_mentions(prompt: str) -> list[str]:
    """正文里已经手写的景别词，仅作提醒。"""
    return [w for w in SHOT_SIZE_LABEL.values() if w in (prompt or "")]


def splice(prompt: str | None, old_note: str | None, new_note: str | None) -> tuple[str | None, str]:
    """把 new_note 落到 prompt 里。返回 (新 prompt, 动作)。

    动作取值：unchanged / removed / replaced / inserted
    """
    prompt = prompt or ""
    old_note = (old_note or "").strip()
    new_note = (new_note or "").strip()

    # 先处理「上次注入的原文还在里面」的情况：替换或删除
    if old_note and old_note in prompt:
        if old_note == new_note:
            return prompt, "unchanged"
        if not new_note:
            return prompt.replace(old_note, "", 1), "removed"
        return prompt.replace(old_note, new_note, 1), "replaced"

    if not new_note:
        return prompt, "unchanged"

    if not prompt.strip():
        return new_note, "inserted"

    # 上次原文找不到了（被手改/删过）→ 去重后追加插入
    if new_note in prompt:
        return prompt, "unchanged"
    pos = _insert_pos(prompt)
    return prompt[:pos] + new_note + prompt[pos:], "inserted"


def _strip_note(prompt: str, note: str) -> str:
    """把上次注入的句子摘掉，得到「用户原始正文」。"""
    note = (note or "").strip()
    if note and note in prompt:
        return prompt.replace(note, "", 1)
    return prompt


def apply_to_shot(shot_id: int, *, camera_shot: str | None, angle: str | None,
                  movement: str | None, subject_position: str | None) -> dict:
    """把向导选择写进字段并注入两份提示词。返回注入结果供前端提示。

    **不覆盖手写内容**：
    - 视频正文里若已有手写的「运镜：……」，本次不注入运镜句（只注入机位），
      并把待并入的运镜句回给前端，由用户自己决定怎么合。
    - 分镜图正文里若已有手写景别词，仅回一条提醒，不改正文。
    """
    from ..core import db

    row = db.query_one(
        "SELECT shot_id, image_prompt, video_prompt, wiz_image_note, wiz_video_note "
        "FROM shot_details WHERE shot_id=?", (shot_id,)) or {}

    img_prompt = row.get("image_prompt") or ""
    vid_prompt = row.get("video_prompt") or ""
    # 摘掉上次注入的句子 → 用户正文
    img_base = _strip_note(img_prompt, row.get("wiz_image_note") or "")
    vid_base = _strip_note(vid_prompt, row.get("wiz_video_note") or "")

    img_note = compose_image_note(camera_shot, angle, subject_position)
    pending_movement = ""
    if (movement or "").strip() and "运镜：" in vid_base:
        # 正文已有手写运镜 → 不注入，避免同一份提示词出现两个互相矛盾的运镜
        existing = _find_movement_segment(vid_base)
        pending_movement = compose_video_note(angle, movement)
        vid_note = compose_video_note(angle, None)
    else:
        vid_note = compose_video_note(angle, movement)

    new_img, img_action = splice(img_base, None, img_note)
    new_vid, vid_action = splice(vid_base, None, vid_note)
    # splice 现在总是走「插入」分支；若上一轮注入的句子被摘掉过，对用户来说就是「更新」
    if img_action == "inserted" and img_base != img_prompt:
        img_action = "replaced" if img_note else "removed"
    if vid_action == "inserted" and vid_base != vid_prompt:
        vid_action = "replaced" if vid_note else "removed"
    if new_img == img_prompt:
        img_action = "unchanged"
    if new_vid == vid_prompt:
        vid_action = "unchanged"

    exists = bool(db.query_one("SELECT shot_id FROM shot_details WHERE shot_id=?", (shot_id,)))
    vals = {
        "camera_shot": (camera_shot or "").strip(),
        "angle": (angle or "").strip(),
        "movement": (movement or "").strip(),
        "subject_position": (subject_position or "").strip(),
        "camera_note": img_note,
        "wiz_image_note": img_note,
        "wiz_video_note": vid_note,
        "image_prompt": new_img,
        "video_prompt": new_vid,
    }
    cols = ", ".join(f"{k}=?" for k in vals)
    if exists:
        db.execute(
            f"UPDATE shot_details SET {cols}, updated_at=datetime('now','localtime') WHERE shot_id=?",
            list(vals.values()) + [shot_id])
    else:
        names = ", ".join(vals.keys())
        ph = ", ".join("?" for _ in vals)
        db.execute(f"INSERT INTO shot_details(shot_id, {names}) VALUES(?, {ph})",
                   [shot_id] + list(vals.values()))

    return {
        "image": {
            "note": img_note, "action": img_action, "prompt": new_img,
            "size_mentions": _find_size_mentions(img_base),
        },
        "video": {
            "note": vid_note, "action": vid_action, "prompt": new_vid,
            "pending_movement": pending_movement,
            "existing_movement": _find_movement_segment(vid_base) if pending_movement else "",
        },
    }
