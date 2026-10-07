"""把三家真实平台写进「接口与设置」。

配置本体在 backend/app/services/provider_seed.py（同一个来源也让服务启动时自动补齐），
这个脚本只负责手动执行 + 打印明细。

用法：
    python scripts/seed_providers.py            # 写入/更新配置
    python scripts/seed_providers.py --dry      # 只看会做什么，不落库
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core import db  # noqa: E402
from app.services import provider_seed as PS  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="只打印计划，不落库")
    ap.add_argument("--no-credentials", action="store_true", help="不写入账号")
    args = ap.parse_args()

    db.init_db()

    if args.dry:
        for p in PS.PROVIDERS:
            print(f"[dry] 供应商 {p['key']:<12} {p['name']}")
        for m in PS.MODELS:
            print(f"[dry] 模型   {m['key']:<22} → {m['provider_key']}")
        print(f"[dry] 账号   listenhub × {len(PS.LISTENHUB_KEYS)}，"
              + "，".join(f"{k}×1" for k in PS.SINGLE_KEYS))
        return

    st = PS.seed_platforms(with_credentials=not args.no_credentials)
    print(f"清理占位供应商：{st['removed']} 个")
    print(f"新增供应商 {st['providers']} / 模型 {st['models']} / 账号 {st['credentials']}（已存在的不重复计）")
    if st.get("fixed_assign"):
        print(f"修正默认分配：{st['fixed_assign']} 项")

    print("\n== 当前配置 ==")
    for r in db.query("SELECT id, key, name, enabled FROM providers ORDER BY id"):
        n = db.query_one(
            "SELECT COUNT(*) c FROM provider_credentials WHERE provider_id=? AND enabled=1", (r["id"],)
        )["c"]
        print(f"  #{r['id']} {r['key']:<12} {r['name'][:36]:<38} 账号={n}")
    print("\n== 模型 ==")
    for r in db.query(
        "SELECT m.id, m.key, m.category, m.model_name, p.key pk FROM models m "
        "LEFT JOIN providers p ON p.id=m.provider_id ORDER BY m.category, m.id"
    ):
        print(f"  #{r['id']} [{r['category']:<5}] {r['key']:<22} → {r['pk']}")
    print("\n== 默认模型分配 ==")
    for r in db.query(
        "SELECT ms.category, m.key FROM model_settings ms LEFT JOIN models m ON m.id=ms.model_id"
        " ORDER BY ms.category"
    ):
        print(f"  {r['category']:<6} → {r['key']}")


if __name__ == "__main__":
    main()
