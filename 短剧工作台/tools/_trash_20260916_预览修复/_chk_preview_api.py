# -*- coding: utf-8 -*-
"""临时自检：/preview 在有剧本 / 无剧本两种状态下都必须可用。"""
import json
import sys
import time
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8770/api"


def call(path, body, method="POST"):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        r = urllib.request.urlopen(req, timeout=15)
        return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")


# 等后端起来
for _ in range(20):
    try:
        urllib.request.urlopen(BASE + "/health", timeout=3)
        print("后端已启动")
        break
    except Exception:
        time.sleep(1.5)
else:
    print("后端未起来")
    sys.exit(1)

REQ = {
    "requirement": "帮我输出一个送外卖拯救世界的漫剧",
    "episodes": 3,
    "minutes_per_episode": 3,
    "genre": "软科幻",
    "visual_style": "live_action",
    "content": None,
}

st, d = call("/projects/1/scripts/preview", REQ)
print("--- 无剧本时 preview ---")
print("HTTP", st)
if isinstance(d, dict):
    print("generate.chars =", d["generate"]["chars"], "| revise =", d["revise"])
    print("========== 实际会发给 DeepSeek 的内容 ==========")
    for m in d["generate"]["messages"]:
        print(f"----- {m['role']} -----")
        print(m["content"])
    print("===============================================")
else:
    print(d)
