"""解析「第N集_中文视频提示词_核对版.md」

产出结构化的镜头记录：提示词各段、参考素材声明、API 参数、音频块、时序拍点、硬约束。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict

from . import md_common as C
from ..services.file_store import clean_name, is_placeholder

# 段落起始识别
_SECTIONS: list[tuple[str, tuple[str, ...]]] = [
    ("api_prompt", ("**API prompt", "**API prompt（", "API prompt")),
    ("declarations", ("素材关系声明", "**素材关系声明")),
    ("summary", ("画面主体",)),
    ("beats", ("画面任务指令",)),
    ("constraints", ("硬约束",)),
    ("api_params", ("**API参数", "API参数")),
    ("audio", ("**音频", "音频：")),
    ("post_audio", ("**后期音轨", "后期音轨")),
]


@dataclass
class VideoRef:
    image_index: int
    file_name: str
    description: str
    is_placeholder: bool = False
    from_api_param: bool = False


@dataclass
class AudioRef:
    index: int
    role: str
    description: str


@dataclass
class ParsedVideoShot:
    shot_code: str
    title: str
    raw_title: str
    gen_mode: str | None = None
    api_style: str | None = None
    duration_sec: float | None = None
    duration_note: str | None = None
    resolution: str | None = None
    seed: str | None = None
    prefix: str | None = None                      # 接口A首行
    declarations: str | None = None
    summary: str | None = None
    beats_text: str | None = None
    beats: list[dict] = field(default_factory=list)
    constraints_text: str | None = None
    constraints: list[str] = field(default_factory=list)
    audio_block: str | None = None
    post_audio_block: str | None = None
    video_prompt: str | None = None                # 喂模型的正文（声明+主体+时序）
    image_refs: list[VideoRef] = field(default_factory=list)
    image_param_refs: list[VideoRef] = field(default_factory=list)
    audio_decl_refs: list[AudioRef] = field(default_factory=list)
    audio_file: str | None = None
    audio_measured_sec: float | None = None
    audio_role: str | None = None
    audio_voice: str | None = None
    audio_voice_rate: str | None = None
    audio_voice_pitch: str | None = None
    audio_text: str | None = None
    audio_tone: str | None = None
    line_start_sec: float | None = None
    line_end_sec: float | None = None
    start_line: int = 0
    end_line: int = 0
    raw: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["image_refs"] = [asdict(x) for x in self.image_refs]
        d["image_param_refs"] = [asdict(x) for x in self.image_param_refs]
        d["audio_decl_refs"] = [asdict(x) for x in self.audio_decl_refs]
        return d


def _match_section(line: str) -> str | None:
    s = line.strip()
    if not s:
        return None
    for key, prefixes in _SECTIONS:
        for p in prefixes:
            if s.startswith(p):
                # 排除误命中：「音频：」出现在正文里的情况（要求行首是 **音频 或 音频：后无内容）
                if key == "audio" and s.startswith("音频：") and len(s) > 3:
                    continue
                return key
    return None


def parse_video_doc(text: str) -> list[ParsedVideoShot]:
    blocks = C.split_shot_blocks(text)
    return [_parse_block(b) for b in blocks]


def _parse_block(block: C.ShotBlock) -> ParsedVideoShot:
    lines = block.lines
    shot = ParsedVideoShot(
        shot_code=block.code,
        title=block.title,
        raw_title=block.raw_title,
        start_line=block.start_line,
        end_line=block.end_line,
        raw=block.text,
    )
    head = block.raw_title
    shot.gen_mode = C.parse_gen_mode(head)
    shot.duration_sec = C.parse_duration_from_title(head)
    if "多图" in head or "接口A" in head:
        shot.api_style = "接口A多图"
    elif "首尾帧" in head or "接口B" in head:
        shot.api_style = "接口B首尾帧"

    # ---- 切段 ----
    marks: list[tuple[int, str]] = []
    for i, ln in enumerate(lines):
        key = _match_section(ln)
        if key:
            marks.append((i, key))
    # 去重：同一 key 只取第一次
    seen_k = set()
    uniq: list[tuple[int, str]] = []
    for i, k in marks:
        if k in seen_k:
            continue
        seen_k.add(k)
        uniq.append((i, k))
    marks = uniq

    segs: dict[str, list[str]] = {}
    for idx, (i, key) in enumerate(marks):
        end = marks[idx + 1][0] if idx + 1 < len(marks) else len(lines)
        # 有些段的内容就写在标记行本身（如「硬约束：① … ② …」「画面主体：xxx」）
        head_rest = _section_rest(lines[i])
        segs[key] = ([head_rest] if head_rest else []) + lines[i + 1: end]

    for key, body_lines in segs.items():
        body = C.strip_md("\n".join(body_lines)).strip()
        body = body.rstrip("-—").strip()
        if key == "api_prompt":
            shot.prefix = _extract_prefix(segs.get("api_prompt", []))
            shot.api_style = shot.api_style or (
                "接口A多图" if shot.prefix and "the target video" in shot.prefix.lower() else None
            )
            body_only = "\n".join(
                ln for ln in segs.get("api_prompt", []) if ln.strip() and ln.strip() != shot.prefix
            ).strip()
            shot.api_prompt_body = body_only or None
        elif key == "declarations":
            shot.declarations = body
            shot.image_refs, shot.audio_decl_refs = _parse_declarations(segs["declarations"])
        elif key == "summary":
            shot.summary = body
        elif key == "beats":
            shot.beats_text = body
            shot.beats = C.parse_beats(body_lines)
        elif key == "constraints":
            shot.constraints_text = body
            shot.constraints = _parse_constraints(body_lines)
        elif key == "api_params":
            _parse_api_params(segs["api_params"], shot)
        elif key == "audio":
            shot.audio_block = body
            _parse_audio_block(segs["audio"], shot)
        elif key == "post_audio":
            shot.post_audio_block = body

    # 正文 = 声明 + 主体 + 时序（不含硬约束/参数/音频）
    parts = []
    if shot.declarations:
        parts.append("素材关系声明：\n" + shot.declarations)
    if shot.summary:
        parts.append("画面主体：\n" + shot.summary)
    if shot.beats_text:
        parts.append("画面任务指令（严格按时序，画面与声音同步生成）：\n" + shot.beats_text)
    if not parts and shot.api_prompt_body:
        # 早期镜头（如镜头1）没有分段结构，整段 API prompt 就是正文
        parts.append(shot.api_prompt_body)
    shot.video_prompt = "\n\n".join(parts) if parts else None

    # 台词语音窗（从拍点里定位）
    _locate_line_window(shot)
    return shot


def _extract_prefix(seg_lines: list[str]) -> str | None:
    """接口A首行：For the target video, ... / How the reference pictures align..."""
    for ln in seg_lines:
        s = ln.strip()
        if not s:
            continue
        low = s.lower()
        if low.startswith("for the target video") or low.startswith("how the reference pictures"):
            return s
    # 兜底：有的镜头首行是纯英文声明（不含中文）。
    # 必须卡 isascii——早期格式的正文常以「ref_image_0是上一镜头…」这种中文行开头，
    # 一旦被误判成首行，下面剔首行时会把整段正文全部剔掉，正文就空了。
    for ln in seg_lines:
        s = ln.strip()
        if s and re.match(r"^[A-Za-z<]", s) and len(s) > 20 and s.isascii():
            return s
    return None


def _parse_declarations(seg_lines: list[str]) -> tuple[list[VideoRef], list[AudioRef]]:
    imgs: list[VideoRef] = []
    auds: list[AudioRef] = []
    for ln in seg_lines:
        s = ln.strip()
        if not s:
            continue
        m = C.ASSET_DECL_RE.match(s)
        if not m:
            # 续行并入上一个声明
            if imgs and s and not s.startswith(("Image", "Audio")):
                imgs[-1].description = (imgs[-1].description + " " + C.strip_md(s)).strip()
            continue
        kind = m.group("kind")
        idx = int(m.group("idx"))
        rest = C.strip_md(m.group("rest"))
        if kind == "Image":
            name = clean_name(rest)
            is_ph = is_placeholder(name) or not re.search(r"\.(jpg|jpeg|png|webp|mp4|mov)$", name, re.I)
            imgs.append(
                VideoRef(
                    image_index=idx,
                    file_name=name,
                    description=rest,
                    is_placeholder=is_ph and is_placeholder(name),
                )
            )
        else:
            role = rest.split("，")[0].split("——")[0].strip()
            auds.append(AudioRef(index=idx, role=role, description=rest))
    # 同名续行已在循环里处理（简化：只保留首行描述）
    return imgs, auds


def _parse_constraints(lines: list[str]) -> list[str]:
    text = " ".join(x.strip() for x in lines if x.strip())
    return C.extract_numbered_items(C.strip_md(text))


def _parse_api_params(lines: list[str], shot: ParsedVideoShot) -> None:
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        m = C.API_PARAM_RE.match(s)
        if not m:
            continue
        key, val = m.group("key"), C.strip_md(m.group("val"))
        if key.startswith("ref_image_"):
            idx = int(key.rsplit("_", 1)[1])
            name = clean_name(val)
            note = val[len(name):].strip("（）() ——-") if name else val
            shot.image_param_refs.append(
                VideoRef(
                    image_index=idx,
                    file_name=name,
                    description=val,
                    is_placeholder=is_placeholder(name),
                    from_api_param=True,
                )
            )
        elif key.startswith("ref_audio_"):
            shot.audio_file = clean_name(val) or shot.audio_file
        elif key == "duration":
            num = re.match(r"(\d+(?:\.\d+)?)", val)
            if num:
                shot.duration_sec = float(num.group(1))
            if "（" in val:
                shot.duration_note = val[val.find("（") + 1: val.rfind("）")] if "）" in val else val
        elif key == "resolution":
            shot.resolution = val
        elif key == "seed":
            shot.seed = val


def _parse_audio_block(lines: list[str], shot: ParsedVideoShot) -> None:
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        m = C.AUDIO_FIELD_RE.match(s)
        if not m:
            continue
        key, val = m.group("key"), C.strip_md(m.group("val"))
        if key == "角色":
            shot.audio_role = val
        elif key == "音色":
            shot.audio_voice = val
            rate = re.search(r"语速\s*(?P<v>[+\-]?\d+%[^|｜）)]*)", val)
            pitch = re.search(r"音调\s*(?P<v>[+\-]?\d+%[^|｜）)]*)", val)
            shot.audio_voice_rate = rate.group("v").strip() if rate else None
            shot.audio_voice_pitch = pitch.group("v").strip() if pitch else None
        elif key == "台词":
            shot.audio_text = C.extract_quoted(val) or val
        elif key == "语气":
            shot.audio_tone = val
        elif key == "ref_audio_0":
            shot.audio_file = clean_name(val) or shot.audio_file
            got = re.search(r"实测\s*\*{0,2}\s*(\d+(?:\.\d+)?)\s*s", val)
            if got:
                shot.audio_measured_sec = float(got.group(1))
    if not shot.audio_measured_sec and shot.audio_block:
        got = re.search(r"实测\s*\*{0,2}\s*(\d+(?:\.\d+)?)\s*s", shot.audio_block)
        if got:
            shot.audio_measured_sec = float(got.group(1))


def _section_rest(line: str) -> str:
    """取标记行冒号后面的内容（有些段的内容写在标记行本身）。"""
    s = line.strip()
    for ch in ("：", ":"):
        i = s.find(ch)
        if i >= 0:
            return s[i + 1:].strip().strip("*").strip()
    return ""


def _locate_line_window(shot: ParsedVideoShot) -> None:
    """从拍点里定位台词的起始时间窗；有实测时长则用它校正收尾时间。"""
    if not shot.beats:
        return
    needle = (shot.audio_text or "").strip()
    core = needle[:4] if len(needle) >= 4 else needle
    start = end = None
    if core:
        for b in shot.beats:
            if core and core in b["text"]:
                start, end = b["start"], b["end"]
                break
    if start is None:
        for b in shot.beats:
            if "台词" in b["text"]:
                start, end = b["start"], b["end"]
                break
    if start is None:
        return
    # 台词可能跨多个拍点（如 14d 的「…如何啊？」+「出来吧~」），用实测时长校正收尾
    if shot.audio_measured_sec:
        end = max(float(end), round(start + float(shot.audio_measured_sec), 3))
    shot.line_start_sec, shot.line_end_sec = start, end
