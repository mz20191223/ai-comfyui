"""短剧生产工作台 · 后端入口。"""
from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# 允许以 `python run.py` 直接启动（把 backend 目录加进 sys.path）
_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.config import FRONTEND_DIR, ROOT_DIR  # noqa: E402
from app.core.db import init_db  # noqa: E402
from app.executors import task_runner  # noqa: E402
from app.routers import (  # noqa: E402
    assets,
    config as config_router,
    creation,
    media,
    projects,
    prompts,
    scripts,
    shots,
    tasks,
    timeline,
)
from app.services.seed import seed_all  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_all()
    # 上次进程留下的 submitted/running 已经没人更新了，扫一遍判为中断
    leftover = task_runner.recover_zombies()
    if leftover:
        print(f"[startup] 回收僵尸任务 {leftover} 条（上次进程中断）")
    yield


app = FastAPI(title="短剧生产工作台", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "service": "drama-studio", "version": "1.0.0", "root": str(ROOT_DIR)}


app.include_router(projects.router)
app.include_router(scripts.router)
app.include_router(shots.router)
app.include_router(assets.router)
app.include_router(prompts.router)
app.include_router(tasks.router)
app.include_router(config_router.router)
app.include_router(media.router)
app.include_router(creation.router)
app.include_router(timeline.router)


# 前端构建产物（若已 build）
_DIST = FRONTEND_DIR / "dist"
if _DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        idx = _DIST / "index.html"
        target = _DIST / full_path
        if full_path and target.exists() and target.is_file():
            return FileResponse(str(target))
        return FileResponse(str(idx))


@app.exception_handler(Exception)
async def unhandled(_request, exc: Exception):  # noqa: ANN001
    import traceback

    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "traceback": traceback.format_exc().splitlines()[-6:]},
    )
