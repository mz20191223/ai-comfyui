"""markdown 解析通用工具：标题切块、名字清理、块提取。"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# 镜头标题。注意尾巴不能强制要求以「｜」开头——真实文档里有大量
# 「## 镜头21（分镜图 0121.jpg）」「### 镜头6a 分镜图生成」这种写法，
# 一旦要求竖线就会整块漏掉。
# codes 支持「## 镜头14b-1 + 14b-2｜...」：一个标题下拆成两条镜头。
SHOT_HEADING_RE = re.compile(
    r"^(?P<hashes>#{2,4})\s*镜头\s*"
    r"(?P<codes>[0-9]+[A-Za-z]?(?:-\d+)?(?:\s*\+\s*[0-9]+[A-Za-z]?(?:-\d+)?)*)"
    r"(?P<tail>.*)$"
)

ANY_HEADING_RE = re.compile(r"^#{1,6}\s+\S")

# 容器标题：「## 镜头6（拆为 6a / 6b ...）」「## 镜头11｜拆为 11a / 11b」
CONTAINER_MARKERS = ("拆为", "拆成", "拆分")

# 分镜图文档里标志提示词段开始的字样（用于判断容器正文是否自带提示词）
IMAGE_PROMPT_MARK = "分镜图提示词"

# 时间拍点：0.0–0.6秒：xxx  （兼容 - — ~ 至）
BEAT_RE = re.compile(
    r"^\s*(?P<start>\d+(?:\.\d+)?)\s*[–—\-~至]\s*(?P<end>\d+(?:\.\d+)?)\s*秒\s*[：:]\s*(?P<text>.+?)\s*$"
)

# Image / Audio 声明行
ASSET_DECL_RE = re.compile(
    r"^\s*(?P<kind>Image|Audio)\s*(?P<idx>\d+)\s*"
    r"(?:（[^）]*）)?\s*[：:]\s*(?P<rest>.+?)\s*$"
)

# API 参数行：- ref_image_0: xxx
API_PARAM_RE = re.compile(
    r"^\s*[-*]?\s*(?P<key>ref_image_\d+|ref_audio_\d+|duration|resolution|seed|first_frame|last_frame)\s*[：:]\s*(?P<val>.+?)\s*$"
)

QUOTE_LINE_RE = re.compile(r"^>\s?(?P<content>.*)$")

# 台词：「台词："xxx"」/「台词：xxx」
DIALOG_RE = re.compile(r"^\s*[-*]?\s*台词\s*[：:]\s*(?P<rest>.+?)\s*$")

# 音频块内字段
AUDIO_FIELD_RE = re.compile(
    r"^\s*[-*]?\s*(?P<key>角色|音色|台词|语气|语速|音调|ref_audio_0)\s*[：:]\s*(?P<val>.*?)\s*$"
)

# 引号内文本
QUOTED_RE = re.compile(r"[\"“”'‘’「『](?P<text>[^\"“”'‘’」』]+)[\"“”'‘’」』]")


@dataclass
class ShotBlock:
    code: str
    title: str
    raw_title: str
    heading_level: int
    start_line: int          # 0 基
    end_line: int            # 不含
    lines: list[str] = field(default_factory=list)
    prompt_ordinal: int = 0  # 同一标题下第几条镜头（「14b-1 + 14b-2」时取第 N 组提示词）

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


def split_shot_blocks(text: str) -> list[ShotBlock]:
    """把 md 文本切成镜头块。

    两条规则依据真实文档形态（踩过的坑）：
    1. 块边界是「下一个镜头标题」，而不是任意标题。否则「## 镜头1」会被
       下面的「### 图A（首帧）」切断，提示词就落到父块之外了。
    2. 标题里写「镜头14b-1 + 14b-2」表示一个标题下拆了两条镜头，块内第 N 组
       提示词按顺序分给第 N 个 code。

    「拆为 x/y」的容器标题不单独成块；但若容器正文自带提示词（如镜头11 的 11a
    正文写在「## 镜头11（拆为 11a / 11b）」下面），则归给第一个子镜头。
    """
    lines = text.splitlines()
    heads: list[tuple[int, re.Match, str]] = []
    for i, ln in enumerate(lines):
        m = SHOT_HEADING_RE.match(ln)
        if m:
            heads.append((i, m, ln))
    shot_lines = {h[0] for h in heads}

    def codes_of(m: re.Match) -> list[str]:
        return [c.strip() for c in re.split(r"\s*\+\s*", m.group("codes")) if c.strip()]

    def body_end(i: int) -> int:
        for j in range(i + 1, len(lines)):
            if j in shot_lines:
                return j
        return len(lines)

    blocks: list[ShotBlock] = []
    for pos, (i, m, ln) in enumerate(heads):
        codes = codes_of(m)
        if not codes:
            continue
        tail = (m.group("tail") or "").lstrip("｜|").strip()
        level = len(m.group("hashes"))
        end = body_end(i)
        body = lines[i + 1: end]

        # 容器标题：本身不是镜头，但其正文可能属于第一个子镜头
        if any(mk in ln for mk in CONTAINER_MARKERS):
            head_after = ln.split("拆", 1)[1] if "拆" in ln else ""
            subs = re.findall(r"[0-9]+[A-Za-z]?(?:-\d+)?", head_after)
            if subs and any(IMAGE_PROMPT_MARK in b for b in body):
                blocks.append(
                    ShotBlock(
                        code=subs[0],
                        title=clean_title_tail(tail),
                        raw_title=ln,
                        heading_level=level,
                        start_line=i,
                        end_line=end,
                        lines=body,
                        prompt_ordinal=0,
                    )
                )
            continue

        # 存在同前缀更长的子镜头紧随其后（如「镜头11」后跟「镜头11b」）→ 父标题不成块
        first = codes[0]
        is_container = False
        for j, m2, _ in heads[pos + 1:]:
            if j - i > 80:
                break
            c2 = codes_of(m2)[0]
            if c2.startswith(first) and len(c2) > len(first):
                is_container = True
                break
        if is_container:
            continue

        for k, code in enumerate(codes):
            blocks.append(
                ShotBlock(
                    code=code,
                    title=clean_title_tail(tail),
                    raw_title=ln,
                    heading_level=level,
                    start_line=i,
                    end_line=end,
                    lines=body,
                    prompt_ordinal=k,
                )
            )
    return blocks


def clean_title_tail(tail: str) -> str:
    """从标题尾巴里剥掉 · I2VA · 7秒 这类元信息，留下人读的标题。"""
    if not tail:
        return ""
    s = tail
    # 去括号内的元信息（I2VA · 2秒）
    s = re.sub(r"[（(]\s*(?:I2VA|FL2VA|REF2VA|T2V|I2V|首尾帧|多图)[^）)]*[）)]", "", s)
    # 去 · 分隔的元信息段
    parts = [p.strip() for p in re.split(r"\s*[·•]\s*", s)]
    keep = []
    for p in parts:
        if re.fullmatch(r"[（(]?[^）)]*?(?:I2VA|FL2VA|REF2VA|T2V|I2V)[^）)]*?[）)]?", p):
            continue
        if re.fullmatch(r"\d+(?:\.\d+)?\s*秒", p) or re.fullmatch(r"[（(]?\d+(?:\.\d+)?\s*秒[）)]?", p):
            continue
        if not p:
            continue
        keep.append(p)
    out = " · ".join(keep).strip(" ·")
    return out.strip()


def parse_gen_mode(text: str) -> str | None:
    for mode in ("REF2VA", "FL2VA", "I2VA", "T2V", "I2V"):
        if mode in text or mode.lower() in text.lower():
            return mode
    return None


def parse_duration_from_title(text: str) -> float | None:
    m = re.search(r"(?<![\d.])(\d+(?:\.\d+)?)\s*秒", text)
    return float(m.group(1)) if m else None


def extract_quoted(text: str) -> str | None:
    m = QUOTED_RE.search(text)
    return m.group("text").strip() if m else None


def strip_md(s: str) -> str:
    return s.replace("**", "").replace("`", "").strip()


def parse_beats(lines: list[str]) -> list[dict]:
    out = []
    for ln in lines:
        m = BEAT_RE.match(ln)
        if m:
            out.append(
                {
                    "start": float(m.group("start")),
                    "end": float(m.group("end")),
                    "text": strip_md(m.group("text")),
                }
            )
    return out


def extract_numbered_items(line: str) -> list[str]:
    """把「① xx ② yy ③ zz」拆成列表。"""
    if not line:
        return []
    marks = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
    idxs = [(i, ch) for i, ch in enumerate(line) if ch in marks]
    if not idxs:
        return [strip_md(line)] if strip_md(line) else []
    items = []
    for k, (i, _) in enumerate(idxs):
        end = idxs[k + 1][0] if k + 1 < len(idxs) else len(line)
        seg = line[i + 1: end].strip()
        if seg:
            items.append(strip_md(seg))
    return items


def collect_section(lines: list[str], start_key: str, stop_keys: tuple[str, ...] = ()) -> tuple[str, int, int]:
    """收集以 start_key 打头的段落到下一个 stop_key（或空行后段结束）。返回 (text, start, end)。"""
    start = -1
    for i, ln in enumerate(lines):
        if ln.strip().startswith(start_key):
            start = i
            break
    if start < 0:
        return "", -1, -1
    end = len(lines)
    for j in range(start + 1, len(lines)):
        s = lines[j].strip()
        if stop_keys and any(s.startswith(k) for k in stop_keys):
            end = j
            break
        if re.match(r"^\*\*[^*]+\*\*\s*[：:]?\s*$", s) or re.match(r"^---\s*$", s):
            end = j
            break
    body = "\n".join(lines[start:end]).strip()
    return body, start, end


def join_nonempty(parts: list[str]) -> str:
    return "\n".join(p for p in (x.strip() for x in parts) if p)
