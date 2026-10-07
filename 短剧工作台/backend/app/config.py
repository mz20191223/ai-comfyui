"""全局路径与运行配置。

设计原则：所有素材目录都在项目配置里可改，代码不写死任何一部剧的路径。
本文件的 WORKSPACE_DEFAULTS 只是「首次导入时的默认值」，导入后以数据库 projects 表为准。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# ---------- 应用自身目录 ----------
# 注意：DATA_DIR / STORAGE_DIR 刻意放在「项目根」而非 backend/ 下，这样备份/迁移项目
# 只需打包一个目录。历史库文件已落在根目录，改动会触发加密软件，所以路径保持不变。
BACKEND_DIR = Path(__file__).resolve().parents[1]      # .../短剧工作台/backend
ROOT_DIR = BACKEND_DIR.parent                          # .../短剧工作台
DATA_DIR = ROOT_DIR / "data"
CONFIG_DIR = ROOT_DIR / "config"
STORAGE_DIR = ROOT_DIR / "storage"
FRONTEND_DIR = ROOT_DIR / "frontend"

# 生成产物的暂存区：视频任务成功后先落这里，用户在页面上看过之后
# 再决定归档进项目「分镜视频」还是扔进「废弃内容」。
# 刻意放在工作台自己的 storage 下 —— 不往用户工作区里塞一个要他手动
# 维护的文件夹；页面上照常能播放（media 路由已把 STORAGE_DIR 列为允许根）。
PENDING_DIR = STORAGE_DIR / "pending"

DATA_DIR.mkdir(parents=True, exist_ok=True)
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
PENDING_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = Path(os.environ.get("STUDIO_DB", DATA_DIR / "studio.db"))
PROVIDER_CONFIG_PATH = CONFIG_DIR / "providers.yaml"

HOST = os.environ.get("STUDIO_HOST", "127.0.0.1")
PORT = int(os.environ.get("STUDIO_PORT", "8770"))

# ---------- 默认素材工作区（仅用于首次导入引导） ----------
DEFAULT_WORKSPACE = Path(r"D:\Aicomfyui\minimax3创作内容")
DEFAULT_DOC_DIR = DEFAULT_WORKSPACE / "deepseek分镜"
DEFAULT_REMAKE_DIR = DEFAULT_WORKSPACE / "重制版"
DEFAULT_DISCARD_DIR = DEFAULT_REMAKE_DIR / "废弃内容"   # 废弃产物统一放这里（2026-09-16 用户指定）

# 素材「按文件名找文件」的搜索路径（有序，先命中先用）
DEFAULT_SEARCH_DIRS = [
    DEFAULT_REMAKE_DIR / "分镜图" / "视频尾帧",
    DEFAULT_REMAKE_DIR / "分镜图",
    DEFAULT_REMAKE_DIR / "音频",
    DEFAULT_REMAKE_DIR / "分镜视频",
    DEFAULT_WORKSPACE / "角色图" / "attachments",
    DEFAULT_WORKSPACE / "角色图",
    DEFAULT_WORKSPACE / "场景道具参考图",
    DEFAULT_WORKSPACE / "辅助图",
    DEFAULT_WORKSPACE / "分镜首尾帧",
    DEFAULT_WORKSPACE / "参考资料",
    DEFAULT_WORKSPACE / "资料类",
    DEFAULT_WORKSPACE / "视频片段",
    DEFAULT_WORKSPACE / "白模预演",
    DEFAULT_REMAKE_DIR / "废弃内容",
]

# 文件名 → 资产类型推断关键词
ASSET_TYPE_HINTS = [
    ("角色参考图", "character"),
    ("场景参考图", "scene"),
    ("道具参考图", "prop"),
    ("服装参考图", "costume"),
]

# 资产名归一化：去掉这些后缀得到资产通用名
ASSET_SUFFIX_PATTERNS = [
    r"[_\-]?角色参考图.*$",
    r"[_\-]?场景参考图.*$",
    r"[_\-]?道具参考图.*$",
]

VIDEO_EXT = {".mp4", ".mov", ".webm", ".mkv", ".avi"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}
DOC_EXT = {".md", ".txt", ".docx", ".pdf", ".json", ".yaml", ".yml"}


def classify_ext(path: str | Path) -> str:
    ext = Path(path).suffix.lower()
    if ext in IMAGE_EXT:
        return "image"
    if ext in VIDEO_EXT:
        return "video"
    if ext in AUDIO_EXT:
        return "audio"
    if ext in DOC_EXT:
        return "doc"
    return "other"


def ffmpeg_exe() -> str:
    """优先用 imageio-ffmpeg 自带的 ffmpeg。"""
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    for cand in ("ffmpeg", "ffmpeg.exe"):
        from shutil import which

        p = which(cand)
        if p:
            return p
    raise RuntimeError("未找到 ffmpeg（请安装 imageio-ffmpeg）")


def python_exe() -> str:
    return sys.executable
