"""素材文件解析与探测。

核心能力（对应项目里反复踩的坑）：
1. resolve()：给一个「提示词里写的名字」，多策略找到真实文件
   - 绝对/相对路径
   - 只给文件名 → 在搜索目录里遍历
   - 缺后缀 → 自动补 .jpg/.png/.mp4/.mp3 …
   - 前缀匹配 → 「过客_角色参考图」能命中「过客_角色参考图_GPT版.jpg」
2. probe()：读宽高/时长（图片 PIL，音视频 mutagen；不依赖 ffprobe）
3. index_file()：登记进 files 表
"""
from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Iterable

from ..config import IMAGE_EXT, AUDIO_EXT, VIDEO_EXT, classify_ext
from ..core import db

# 目录内容缓存（TTL）：resolve 会反复遍历同一批目录，缓存后大幅提速
_DIR_TTL = 30.0
_dir_cache: dict[str, tuple[float, list[Path]]] = {}


def _dir_entries(d: Path) -> list[Path]:
    key = str(d)
    now = time.time()
    hit = _dir_cache.get(key)
    if hit and now - hit[0] < _DIR_TTL:
        return hit[1]
    try:
        entries = [f for f in d.iterdir() if f.is_file()]
    except (OSError, PermissionError):
        entries = []
    _dir_cache[key] = (now, entries)
    return entries


def clear_cache() -> None:
    _dir_cache.clear()

# 这些名字是「占位符」，不是真文件（文档里常见）
PLACEHOLDER_NAMES = {
    "分镜图",
    "首帧",
    "尾帧",
    "待生成",
    "待定",
    "无",
    "none",
    "null",
}
_PLACEHOLDER_MARKERS = ("待生成", "待定", "待补", "占位", "todo", "tbd")


def is_placeholder(name: str | None) -> bool:
    if not name:
        return True
    s = name.strip()
    if not s:
        return True
    if s in PLACEHOLDER_NAMES:
        return True
    low = s.lower()
    return any(m in low for m in _PLACEHOLDER_MARKERS)


def clean_name(raw: str | None) -> str:
    """从提示词里的一行名字里抽出纯文件名。"""
    if not raw:
        return ""
    s = raw.strip()
    # 去掉 markdown 粗体/代码/引号
    s = s.replace("**", "").replace("`", "").replace('"', "").replace("'", "")
    # 去掉常见的尾部说明：「0114b2_tail.jpg（14b-2 视频尾帧）—— xxxx」
    for sep in ("（", "(", "——", "—", " - ", "：", ":"):
        idx = s.find(sep)
        if idx > 0:
            s = s[:idx]
    s = s.strip().strip("、,.。；;")
    return s


def _candidate_dirs(project: dict | None) -> list[Path]:
    dirs: list[Path] = []
    if project:
        for k in (
            "tail_dir",
            "keyframe_dir",
            "audio_dir",
            "video_dir",
            "ref_dir",
            "doc_dir",
            "workspace_dir",
        ):
            v = project.get(k)
            if v:
                dirs.append(Path(v))
    from ..config import DEFAULT_SEARCH_DIRS

    dirs.extend(DEFAULT_SEARCH_DIRS)
    out, seen = [], set()
    for d in dirs:
        key = str(d).lower()
        if key not in seen:
            seen.add(key)
            out.append(d)
    return out


def resolve(name: str | Path | None, project: dict | None = None) -> Path | None:
    """把提示词里的名字解析为真实存在的文件路径。"""
    raw = str(name or "").strip()
    if not raw:
        return None
    raw = clean_name(raw)
    if not raw or is_placeholder(raw):
        return None

    p = Path(raw)
    # 1) 绝对路径
    if p.is_absolute():
        if p.exists():
            return p
        # 绝对路径但不存在，退化为按文件名找
        name_only = p.name
    else:
        name_only = raw

    dirs = _candidate_dirs(project)
    # 2) 相对路径直接拼
    if "/" in name_only or "\\" in name_only:
        for d in dirs:
            cand = d / name_only
            if cand.exists():
                return cand

    base = Path(name_only).name
    stem = Path(base).stem
    ext = Path(base).suffix.lower()

    # 3) 精确文件名
    for d in dirs:
        cand = d / base
        if cand.exists():
            return cand

    # 4) 缺后缀 → 补常见后缀
    if not ext:
        for e in list(IMAGE_EXT) + list(VIDEO_EXT) + list(AUDIO_EXT):
            for d in dirs:
                cand = d / f"{base}{e}"
                if cand.exists():
                    return cand

    # 5) 前缀/包含匹配（「过客_角色参考图」→「过客_角色参考图_GPT版.jpg」）
    want_exts = {ext} if ext else (IMAGE_EXT | VIDEO_EXT | AUDIO_EXT)
    best: tuple[int, Path] | None = None
    for d in dirs:
        if not d.exists():
            continue
        for f in _dir_entries(d):
            if f.suffix.lower() not in want_exts:
                continue
            fs = f.stem.lower()
            ss = stem.lower()
            if fs == ss:
                score = 0
            elif fs.startswith(ss):
                score = 1
            elif ss in fs:
                score = 2
            else:
                continue
            if best is None or score < best[0]:
                best = (score, f)
                if score == 0:
                    break
        if best and best[0] == 0:
            break
    if best:
        return best[1]
    return None


def probe(path: str | Path) -> dict:
    """探测文件元信息：type/size/width/height/duration。"""
    p = Path(path)
    info: dict = {"exists": p.exists()}
    if not p.exists():
        return info
    try:
        info["size_bytes"] = p.stat().st_size
    except OSError:
        pass
    info["file_type"] = classify_ext(p)
    ext = p.suffix.lower()
    if ext in IMAGE_EXT:
        try:
            from PIL import Image

            with Image.open(p) as im:
                info["width"], info["height"] = im.size
                info["format"] = (im.format or "").lower()
        except Exception:
            pass
    elif ext in AUDIO_EXT or ext in VIDEO_EXT:
        try:
            from mutagen import File as MutaFile

            mf = MutaFile(str(p))
            if mf is not None and mf.info is not None:
                info["duration_sec"] = round(float(mf.info.length), 3)
        except Exception:
            pass
        if ext in VIDEO_EXT and "width" not in info:
            try:
                import cv2  # 可选

                cap = cv2.VideoCapture(str(p))
                if cap.isOpened():
                    info["width"] = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    info["height"] = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                cap.release()
            except Exception:
                pass
    return info


def sha1_of(path: str | Path, limit: int = 4 * 1024 * 1024) -> str | None:
    try:
        h = hashlib.sha1()
        with open(path, "rb") as f:
            h.update(f.read(limit))
        return h.hexdigest()
    except OSError:
        return None


def index_file(path: str | Path, note: str | None = None) -> int | None:
    """把文件登记进 files 表（存在则更新）。"""
    p = Path(path)
    if not p.exists():
        return None
    info = probe(p)
    abs_path = str(p.resolve())
    row = db.query_one("SELECT id, sha1 FROM files WHERE path = ?", (abs_path,))
    if row:
        # sha1 一起刷：同一个路径被新内容覆盖（重出图）后，旧 sha1 会一直挂着误导排查。
        # 取不到新值时保留原值，避免把已有 sha1 刷成 NULL。
        db.execute(
            """UPDATE files SET size_bytes=?, width=?, height=?, duration_sec=?, sha1=?,
                   exists_flag=1, last_seen_at=datetime('now','localtime') WHERE id=?""",
            (
                info.get("size_bytes"),
                info.get("width"),
                info.get("height"),
                info.get("duration_sec"),
                sha1_of(p) or row["sha1"],
                row["id"],
            ),
        )
        return row["id"]
    return db.execute(
        """INSERT INTO files(path, file_name, ext, file_type, size_bytes, width, height,
                             duration_sec, sha1, exists_flag, last_seen_at)
           VALUES(?,?,?,?,?,?,?,?,?,1,datetime('now','localtime'))""",
        (
            abs_path,
            p.name,
            p.suffix.lower(),
            info.get("file_type"),
            info.get("size_bytes"),
            info.get("width"),
            info.get("height"),
            info.get("duration_sec"),
            sha1_of(p),
        ),
    )


def audio_duration(path: str | Path) -> float | None:
    """精测音频时长（mutagen，比 Windows 属性更准）。"""
    info = probe(path)
    return info.get("duration_sec")


def guess_asset_name(file_name: str) -> str:
    """从参考图文件名反推资产名：「过客_角色参考图_GPT版.jpg」→「过客」"""
    import re

    stem = Path(clean_name(file_name)).stem
    for pat in (
        r"[_\-]?角色参考图.*$",
        r"[_\-]?场景参考图.*$",
        r"[_\-]?道具参考图.*$",
        r"[_\-]?服装参考图.*$",
    ):
        stem = re.sub(pat, "", stem)
    return stem.strip("_- ") or stem


def guess_asset_type(file_name: str) -> str:
    n = str(file_name)
    if "角色参考图" in n or "金甲" in n:
        return "character"
    if "场景参考图" in n:
        return "scene"
    if "道具参考图" in n:
        return "prop"
    if "服装" in n:
        return "costume"
    return "prop"


def list_dir_files(dir_path: str | Path, kinds: Iterable[str] | None = None) -> list[Path]:
    d = Path(dir_path)
    if not d.exists():
        return []
    out = []
    for f in sorted(d.iterdir()):
        if not f.is_file():
            continue
        if kinds and classify_ext(f) not in kinds:
            continue
        out.append(f)
    return out
