"""启动脚本：python run.py"""
from __future__ import annotations

import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent
sys.path.insert(0, str(_BACKEND))

import uvicorn  # noqa: E402

from app.config import HOST, PORT  # noqa: E402


def main() -> None:
    print(f"短剧生产工作台启动中…  http://{HOST}:{PORT}")
    print(f"API 文档：            http://{HOST}:{PORT}/docs")
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=False, log_level="info")


if __name__ == "__main__":
    main()
