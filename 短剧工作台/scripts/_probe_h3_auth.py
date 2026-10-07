"""确认 AutoDL 鉴权头格式：裸 token 还是 Bearer。

只发一个「查询不存在任务」的 GET，不提交任何生成任务 → 不产生费用。
token 从数据库读取，不经过命令行，避免明文外泄。

用法：python scripts/_probe_h3_auth.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import httpx  # noqa: E402

from app.core import db  # noqa: E402

FAKE_TASK = "00000000-0000-0000-0000-000000000000"
URL = f"https://autodl.art/api/v1/comfyui/comfyui_workflow/result/{FAKE_TASK}"


def main() -> None:
    db.init_db()
    row = db.query_one(
        "SELECT pc.api_key, p.base_url, p.name FROM provider_credentials pc "
        "JOIN providers p ON p.id = pc.provider_id WHERE p.key = ?", ("autodl-h3",)
    )
    if not row:
        print("库里没有 autodl-h3 的账号")
        return
    token = row["api_key"]
    print(f"账号来源：{row['name']}   token 前缀 {token[:6]}…  长度 {len(token)}")

    variants = [
        ("裸 token（无 scheme）", {"Authorization": token}),
        ("Bearer + token", {"Authorization": f"Bearer {token}"}),
        ("无鉴权头", {}),
    ]
    for label, headers in variants:
        try:
            r = httpx.get(URL, headers=headers, timeout=25, follow_redirects=True)
            body = r.text[:260].replace("\n", " ")
        except Exception as e:  # noqa: BLE001
            print(f"  {label:<20} → 请求异常：{e}")
            continue
        print(f"  {label:<20} → HTTP {r.status_code}  {body}")


if __name__ == "__main__":
    main()
