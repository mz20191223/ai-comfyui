#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Agnes Image 2.1 Flash —— 文生图 / 图生图（Python 直接调用）。

基础地址 : https://apihub.agnes-ai.com/v1
模型     : agnes-image-2.1-flash（文生图 + 图生图都支持）
费用     : 当前免费（$0 / 张）

重要坑（对照官方文档 + 已验证 skill）:
  - 顶层不要放 response_format / quality / style（会 400）；默认就返回 url。
  - 图生图用 extra_body.image = [图片URL 或 data URI]，不要传 tags。
  - prompt 支持中文，无需翻译成英文。

用法:
  from agnes_image import generate_image, download_image
  r = generate_image("一只皮克斯风格的小刺猬，圆滚滚，大眼睛", size="1024x1024")
  print(r["url"])
  download_image(r["url"], "ref.png")

  # 图生图（把本地图转 data URI 自动上传）
  r = generate_image("改成水彩风格，保留构图", image="ref.png")
"""
import base64
import json
import os
import urllib.request

try:
    from agnes_llm import AGNES_API_KEY, BASE_URL
except Exception:  # 独立运行时回退
    AGNES_API_KEY = os.environ.get(
        "AGNES_API_KEY",
        """",
    )
    BASE_URL = os.environ.get("AGNES_BASE_URL", "https://apihub.agnes-ai.com/v1").rstrip("/")

IMAGE_ENDPOINT = "/images/generations"
MODEL = "agnes-image-2.1-flash"


def generate_image(prompt, size="1024x1024", ratio=None, image=None,
                   return_base64=False, timeout=180):
    """生成一张图。

    prompt        : 中文描述即可。
    size          : 档位 '1K'/'2K'/'3K'/'4K' 或精确值 '1024x1024'（默认 1024x1024）。
    ratio         : 与档位式 size 配合，如 '1:1'/'16:9'/'9:16'（仅 size 为档位时有效）。
    image         : 图生图时的图片——公开 URL 字符串，或本地文件路径（自动转 data URI）。
    return_base64 : True 时文生图以 base64 返回（默认 False，返回 url）。
    返回          : {"url": str|None, "b64_json": str|None, "revised_prompt": str|None}
    """
    body = {"model": MODEL, "prompt": prompt, "size": size}
    if ratio:
        body["ratio"] = ratio
    if return_base64:
        body["return_base64"] = True
    if image:
        if os.path.exists(image):  # 本地文件 -> data URI
            ext = os.path.splitext(image)[1].lstrip(".") or "png"
            with open(image, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
            img_arg = f"data:image/{ext};base64,{b64}"
        else:
            img_arg = image
        # 图生图：用 extra_body.image 传输入图；默认返回 url（不送 response_format 以免 400）
        body["extra_body"] = {"image": [img_arg]}
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL + IMAGE_ENDPOINT,
        data=data,
        headers={
            "Authorization": f"Bearer {AGNES_API_KEY}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        resp = json.loads(r.read().decode("utf-8"))
    item = resp["data"][0]
    return {
        "url": item.get("url"),
        "b64_json": item.get("b64_json"),
        "revised_prompt": item.get("revised_prompt"),
    }


def download_image(url_or_b64, out_path):
    """把图片 URL（或 b64_json 字符串）保存为本地文件。"""
    if url_or_b64.startswith("data:"):
        head, _, payload = url_or_b64.partition(",")
        with open(out_path, "wb") as f:
            f.write(base64.b64decode(payload))
        return out_path
    req = urllib.request.Request(url_or_b64)
    with urllib.request.urlopen(req, timeout=120) as r, open(out_path, "wb") as f:
        f.write(r.read())
    return out_path


if __name__ == "__main__":
    r = generate_image("一只皮克斯风格的小刺猬，圆滚滚，大眼睛，纯色背景", size="1024x1024")
    print("URL:", r["url"])
    if r["url"]:
        download_image(r["url"], "agnes_test.png")
        print("已保存到 agnes_test.png")
