"""用官方「预估积分」接口确定生图该发哪个 model 字符串。

官方明确该接口「不消耗积分、不调用模型」，因此是零成本探测。
token 从数据库读取，不经过命令行。

用法：python scripts/_probe_image_models.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import httpx  # noqa: E402

from app.core import db  # noqa: E402

BASE = "https://api.marswave.ai/openapi"
ESTIMATE = BASE + "/v1/images/generation/estimate-credits"

CANDIDATES = [
    ("gpt-image-2.5-flare", "网页名 GPT-Image-2.5 Flare（快速出图）"),
    ("gpt-image-2.5-sunburst", "网页名 GPT-Image-2.5 Sunburst（细节更密）"),
    ("gpt-image-2.5", "不带变体后缀"),
    ("gpt-image-2", "官方文档默认值"),
]


def _variants(model: str) -> list[dict]:
    return [
        {
            "provider": "openai",
            "model": model,
            "prompt": "a red circle on white background",
            "imageConfig": {"imageSize": "1K", "aspectRatio": "9:16", "quality": "medium"},
        },
        {
            "provider": "openai",
            "model": model,
            "prompt": "a red circle on white background",
        },
        {
            "model": model,
            "prompt": "a red circle on white background",
        },
    ]


def main() -> None:
    db.init_db()
    row = db.query_one(
        "SELECT pc.api_key FROM provider_credentials pc JOIN providers p ON p.id=pc.provider_id "
        "WHERE p.key=? ORDER BY pc.sort_order, pc.id LIMIT 1", ("listenhub",)
    )
    if not row:
        print("库里没有 listenhub 账号")
        return
    headers = {"Authorization": f"Bearer {row['api_key']}", "Content-Type": "application/json"}

    for model, note in CANDIDATES:
        print(f"\n=== 候选 model: {model}   （{note}）")
        for i, body in enumerate(_variants(model), start=1):
            try:
                r = httpx.post(ESTIMATE, headers=headers, json=body, timeout=30)
            except Exception as e:  # noqa: BLE001
                print(f"  body{i}: 请求异常 {e}")
                continue
            txt = r.text[:300].replace("\n", " ")
            verdict = ""
            try:
                o = json.loads(r.text)
                code = o.get("code")
                if code == 0:
                    verdict = f"✅ 接受（预估积分={o.get('data', {}).get('credits')}）"
                elif code == 29003:
                    verdict = "❌ 参数/模型不被接受"
                elif code is not None:
                    verdict = f"⚠️ code={code} {o.get('message')}"
            except Exception:  # noqa: BLE001
                pass
            print(f"  body{i}: HTTP {r.status_code} {verdict}  {txt}")


if __name__ == "__main__":
    main()
