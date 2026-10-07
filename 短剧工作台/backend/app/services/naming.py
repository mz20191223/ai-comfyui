"""镜号 ↔ 文件名 的命名推导。

项目既有规律（从现有素材实证）：
    镜头14a-1  →  分镜图 0114a1.jpg   →  尾帧 0114a1_tail.jpg
    镜头12b    →  分镜图 0112b.jpg    →  尾帧 0112b_tail.jpg
    镜头10     →  分镜图 0110.jpg     →  尾帧 0110_tail.jpg

即：`01` + 集内镜号（数字两位补零 + 字母 + 子号，去掉连字符）
"""
from __future__ import annotations

import re
from pathlib import Path

CODE_RE = re.compile(r"^(?P<num>\d+)(?P<letter>[A-Za-z]*)(?:-(?P<sub>\d+))?$")


def code_stem(shot_code: str, episode: int = 1) -> str:
    """镜头号 → 文件名主干。14b-1 → 0114b1"""
    m = CODE_RE.match(shot_code.strip())
    if not m:
        return f"{episode:02d}{shot_code}"
    num = int(m.group("num"))
    letter = m.group("letter")
    sub = m.group("sub") or ""
    return f"{episode:02d}{num:02d}{letter}{sub}"


def tail_names(shot_code: str, episode: int = 1) -> list[str]:
    stem = code_stem(shot_code, episode)
    names = [f"{stem}_tail.jpg", f"{stem}_tail.png", f"{stem}_tail.jpeg"]
    m = CODE_RE.match(shot_code.strip())
    if m and m.group("letter") and not m.group("sub"):
        num = int(m.group("num"))
        names.append(f"{episode:02d}{num:02d}-{m.group('letter')}_tail.jpg")
    return names


def keyframe_names(shot_code: str, episode: int = 1) -> list[str]:
    stem = code_stem(shot_code, episode)
    names = [f"{stem}.jpg", f"{stem}.png", f"{stem}.jpeg"]
    m = CODE_RE.match(shot_code.strip())
    if m:
        num = int(m.group("num"))
        letter = m.group("letter")
        sub = m.group("sub")
        # 兼容带横线写法：6a → 0106-a.jpg ；14b-1 → 0114b-1.jpg
        if letter and not sub:
            names.append(f"{episode:02d}{num:02d}-{letter}.jpg")
            names.append(f"{episode:02d}{num:02d}-{letter}.png")
        if sub:
            names.append(f"{episode:02d}{num:02d}{letter}-{sub}.jpg")
    names += [f"{stem}_a.jpg", f"{stem}_b.jpg"]
    return names


def find_with_names(dirs: list[Path], names: list[str]) -> Path | None:
    for name in names:
        for d in dirs:
            if not d.exists():
                continue
            cand = d / name
            if cand.exists():
                return cand
    return None


def episode_from_filename(name: str) -> int | None:
    m = re.search(r"第\s*(\d+)\s*集", name)
    return int(m.group(1)) if m else None


def shot_sort_key(shot_code: str) -> tuple:
    """镜号排序键：先数字，再字母，再子号。"""
    m = CODE_RE.match(shot_code.strip())
    if not m:
        return (9999, "", 0, shot_code)
    return (int(m.group("num")), m.group("letter").lower(), int(m.group("sub") or 0), "")
