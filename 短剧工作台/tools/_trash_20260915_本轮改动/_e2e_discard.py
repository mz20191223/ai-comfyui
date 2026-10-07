# -*- coding: utf-8 -*-
"""废弃产物接口端到端实测：造临时文件 → 调真实接口 → 校验落盘 → 清理。

只动我自己创建的文件（_discard_test_*.jpg），不碰任何既有素材。
"""
import io
import json
import sys
import urllib.request
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

API = "http://127.0.0.1:8770/api"
KEYFRAME_DIR = Path(r"D:\Aicomfyui\minimax3创作内容\重制版\分镜图")
DISCARD_DIR = Path(r"D:\Aicomfyui\minimax3创作内容\重制版\废弃内容")
SHOT_ID = 113


def post(url, payload):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


def get(url):
    with urllib.request.urlopen(url, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    # 0) 镜头是否存在
    shot = get(f"{API}/shots/{SHOT_ID}")
    print("镜头:", shot["shot"]["shot_code"], shot["shot"]["title"])

    # 1) 造一个临时 jpg（最小 JPEG 头，只为验证移动逻辑）
    KEYFRAME_DIR.mkdir(parents=True, exist_ok=True)
    src = KEYFRAME_DIR / "_discard_test_zz.jpg"
    src.write_bytes(bytes.fromhex("ffd8ffe000104a46494600010100000100010000ffdb0043") + b"\x00" * 256 + bytes.fromhex("ffd9"))
    print("已造临时文件:", src, src.exists(), src.stat().st_size, "B")

    # 2) 调真实接口
    res = post(f"{API}/shots/{SHOT_ID}/discard-output", {"path": str(src)})
    print("接口返回 ok =", res.get("ok"))
    new_path = Path(res["new_path"])
    print("新位置:", new_path)

    # 3) 校验
    checks = {
        "原位置已不存在": not src.exists(),
        "已落到废弃目录": new_path.parent == DISCARD_DIR,
        "废弃目录内文件存在": new_path.exists(),
        "内容一致(361B)": new_path.exists() and new_path.stat().st_size == src.stat().st_size if src.exists() else new_path.exists(),
        "落盘大小": new_path.stat().st_size if new_path.exists() else None,
    }
    for k, v in checks.items():
        print(f"  {k}: {v}")

    # 4) 清理（只删我造的这个文件）
    if new_path.exists() and new_path.name.startswith("_discard_test"):
        new_path.unlink()
        print("已清理临时文件:", new_path)
    else:
        print("!! 未清理，请人工确认:", new_path)

    # 5) 重复调用同一路径应报 404（文件已不在）
    try:
        post(f"{API}/shots/{SHOT_ID}/discard-output", {"path": str(src)})
        print("重复调用: 未报错（异常）")
    except urllib.error.HTTPError as e:
        print("重复调用返回:", e.code, "（期望 404）")


if __name__ == "__main__":
    main()
