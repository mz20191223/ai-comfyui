"""解析「第N集_分镜图提示词_GPT-Img2.md」

产出：分镜图提示词正文、上传参考图清单、目标文件名、工作流注释（备注，不入提示词）。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict

from . import md_common as C
from ..services.file_store import clean_name, is_placeholder

TARGET_RE = re.compile(r"分镜图\s*(?P<file>[0-9A-Za-z_\-]+\.(?:jpg|jpeg|png|webp))", re.I)
REF_ITEM_RE = re.compile(r"^\s*\d+[.、)]\s*(?P<rest>.+?)\s*$")
PROMPT_HEAD_RE = re.compile(r"^\s*\*{0,2}分镜图提示词")
REFS_HEAD_RE = re.compile(r"^\s*\*{0,2}上传参考图")
WORKFLOW_NOTE_RE = re.compile(r"📋【工作流注释")
OPTIONAL_MARKERS = ("默认不出分镜图", "仅作备选", "备选", "作废")


@dataclass
class ImageRefItem:
    index: int
    file_name: str
    note: str
    is_placeholder: bool = False


@dataclass
class ParsedStoryboardShot:
    shot_code: str
    title: str
    raw_title: str
    target_file: str | None = None
    is_optional: bool = False
    ref_items: list[ImageRefItem] = field(default_factory=list)
    refs_block: str | None = None
    prompt: str | None = None
    notes: str | None = None          # 工作流注释（非提示词，仅供人看）
    lead_notes: str | None = None     # 标题下的说明行
    start_line: int = 0
    end_line: int = 0
    raw: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["ref_items"] = [asdict(x) for x in self.ref_items]
        return d


def parse_storyboard_doc(text: str) -> list[ParsedStoryboardShot]:
    return [_parse_block(b) for b in C.split_shot_blocks(text)]


def _sections(lines: list[str]) -> list[dict]:
    """把块正文切成若干「参考图清单 + 提示词正文」组，顺序即组号。

    一个块里出现多组的情形：
      · 「## 镜头1」下的「### 图A（首帧）」「### 图B（尾帧）」
      · 「## 镜头14b-1 + 14b-2」下的「分镜图 1/2」「分镜图 2/2」
    提示词只在引用块（> 开头）里，遇到非引用行即视为该段结束——否则
    「**出图命名：**」「**衔接说明：**」会被当成提示词内容一起喂给模型。
    """
    groups: list[dict] = []
    cur: dict | None = None
    for ln in lines:
        s = ln.strip()
        if REFS_HEAD_RE.match(s):
            cur = {"refs": [], "prompt": [], "mode": "refs"}
            groups.append(cur)
            continue
        if PROMPT_HEAD_RE.match(s):
            if cur is None or cur["mode"] == "prompt":
                cur = {"refs": [], "prompt": [], "mode": "prompt"}
                groups.append(cur)
            else:
                cur["mode"] = "prompt"
            continue
        if s.startswith("---"):
            cur = None
            continue
        if cur is None:
            continue
        if cur["mode"] == "refs":
            cur["refs"].append(ln)
        elif cur["mode"] == "prompt":
            if s.startswith(">"):
                cur["prompt"].append(s)
            elif s:
                cur["mode"] = "post"      # 提示词段结束，后面是衔接说明/出图命名等
    return groups


def _parse_block(block: C.ShotBlock) -> ParsedStoryboardShot:
    lines = block.lines
    head = block.raw_title
    out = ParsedStoryboardShot(
        shot_code=block.code,
        title=block.title,
        raw_title=head,
        start_line=block.start_line,
        end_line=block.end_line,
        raw=block.text,
    )

    m = TARGET_RE.search(head)
    if m:
        out.target_file = m.group("file")
    if any(k in head for k in OPTIONAL_MARKERS):
        out.is_optional = True
    # 标题没写但参考图清单头写「备选」时同样视为备选镜头
    if any(REFS_HEAD_RE.match(ln.strip()) and "备选" in ln for ln in lines):
        out.is_optional = True

    groups = _sections(lines)
    grp = groups[block.prompt_ordinal] if block.prompt_ordinal < len(groups) else None

    # --- 参考图清单 ---
    i_refs = next((i for i, ln in enumerate(lines) if REFS_HEAD_RE.match(ln)), -1)
    if grp is not None:
        items: list[ImageRefItem] = []
        ref_kept: list[str] = []
        for ln in grp["refs"]:
            s = ln.strip()
            if not s or WORKFLOW_NOTE_RE.search(s):
                continue
            if s.startswith(">"):
                break
            ref_kept.append(s)
            m2 = REF_ITEM_RE.match(s)
            if not m2:
                continue
            rest = C.strip_md(m2.group("rest"))
            name = clean_name(rest)
            items.append(
                ImageRefItem(
                    index=len(items) + 1,
                    file_name=name,
                    note=rest,
                    is_placeholder=is_placeholder(name),
                )
            )
        out.ref_items = items
        if ref_kept:
            out.refs_block = "\n".join(ref_kept)
    elif i_refs >= 0:
        end = len(lines)
        out.refs_block = "\n".join(x for x in (l.strip() for l in lines[i_refs: end]) if x)

    # --- 提示词正文 ---
    if grp is not None and grp["prompt"]:
        body = "\n".join(grp["prompt"]).strip()
        body = "\n".join(re.sub(r"^>\s?", "", l) for l in body.splitlines()).strip()
        out.prompt = body or None

    # --- 注释（工作流注释 + 标题下列表前的引用行） ---
    notes: list[str] = []
    lead: list[str] = []
    for ln in lines:
        s = ln.strip()
        if not s or not s.startswith(">"):
            continue
        if WORKFLOW_NOTE_RE.search(s):
            notes.append(C.strip_md(re.sub(r"^>\s?", "", s)))
        elif grp is None or s not in grp["prompt"]:
            lead.append(C.strip_md(re.sub(r"^>\s?", "", s)))
    out.notes = "\n".join(notes) or None
    out.lead_notes = "\n".join(lead) or None
    return out
