"""首次初始化：建库 + 种子数据 + 建项目 + 导入现有分镜文档。

用法（在 backend 目录下）：
    python scripts/bootstrap.py                 # 全量导入
    python scripts/bootstrap.py --rebuild       # 重建镜头（清空后重导）
    python scripts/bootstrap.py --episode 1     # 只导第 1 集
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_BACKEND))

from app.config import DEFAULT_DOC_DIR, DEFAULT_WORKSPACE  # noqa: E402
from app.core.db import init_db  # noqa: E402
from app.parsers import importer  # noqa: E402
from app.routers.projects import _derive_dirs, _discover_docs  # noqa: E402
from app.services.seed import seed_all  # noqa: E402
from app.core import db  # noqa: E402

PROJECT_NAME = "凌晨两点，Bug 成精了"
PROJECT_CODE = "bug-2026"


def ensure_project() -> int:
    row = db.query_one("SELECT id FROM projects WHERE code=?", (PROJECT_CODE,))
    if row:
        print(f"  项目已存在 id={row['id']}")
        return row["id"]
    dirs = _derive_dirs(str(DEFAULT_WORKSPACE), str(DEFAULT_DOC_DIR))
    pid = db.execute(
        """INSERT INTO projects(name, code, kind, visual_style, genre, aspect_ratio, fps, resolution,
               workspace_dir, doc_dir, ref_dir, keyframe_dir, video_dir, tail_dir, audio_dir)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            PROJECT_NAME, PROJECT_CODE, "micro_drama", "live_action", "软科幻·神话",
            "9:16", 24, "768x1344",
            dirs["workspace_dir"], dirs["doc_dir"], dirs["ref_dir"], dirs["keyframe_dir"],
            dirs["video_dir"], dirs["tail_dir"], dirs["audio_dir"],
        ),
    )
    print(f"  已建项目 id={pid}：{PROJECT_NAME}")
    return pid


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true", help="清空镜头后重建")
    ap.add_argument("--episode", type=int, default=None, help="只导入指定集")
    args = ap.parse_args()

    print("[1/4] 初始化数据库…")
    init_db()
    stats = seed_all()
    print(f"  种子数据：{stats}")

    pid = ensure_project()

    print("[2/4] 发现文档…")
    doc_dir = Path(DEFAULT_DOC_DIR)
    found = _discover_docs(doc_dir)
    if not found:
        print(f"  未在 {doc_dir} 发现「第N集」文档")
        return
    for n, v in sorted(found.items()):
        print(f"  第{n}集：核对版={'有' if v.get('video_doc') else '无'}  分镜图={'有' if v.get('storyboard_doc') else '无'}")

    print("[3/4] 导入…")
    for num, v in sorted(found.items()):
        if args.episode and num != args.episode:
            continue
        if not v.get("video_doc"):
            print(f"  第{num}集：跳过（缺核对版）")
            continue
        try:
            r = importer.import_episode(
                pid, num, v["video_doc"], v.get("storyboard_doc"), rebuild=args.rebuild
            )
            print(
                f"  第{num}集 OK：镜头 {r.shots_total}（新建 {r.shots_created} / 更新 {r.shots_updated}）"
                f" 资产新建 {r.assets_created} 引用槽 {r.links_created} 尾帧挂载 {r.frames_linked}"
                f" 问题 {len(r.issues)}"
            )
        except Exception as e:  # noqa: BLE001
            import traceback

            print(f"  第{num}集 失败：{e}")
            traceback.print_exc()

    print("[4/4] 统计…")
    counts = {
        "镜头": db.query_one("SELECT COUNT(*) AS c FROM shots")["c"],
        "资产": db.query_one("SELECT COUNT(*) AS c FROM assets")["c"],
        "参考图": db.query_one("SELECT COUNT(*) AS c FROM asset_images")["c"],
        "引用槽": db.query_one("SELECT COUNT(*) AS c FROM shot_asset_links")["c"],
        "台词": db.query_one("SELECT COUNT(*) AS c FROM shot_dialog_lines")["c"],
        "尾帧": db.query_one("SELECT COUNT(*) AS c FROM shot_frames")["c"],
        "健康问题": db.query_one("SELECT COUNT(*) AS c FROM health_issues")["c"],
    }
    for k, v in counts.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
