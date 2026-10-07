# -*- coding: utf-8 -*-
"""临时自检：preview 在「已有剧本」时应同时返回 generate 与 revise。

用临时项目跑，跑完自清（不碰真实项目数据）。
"""
import json
import sys
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = "http://127.0.0.1:8770/api"


def call(path, body=None, method="POST"):
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


st, proj = call("/projects", {"name": "_临时预览自检", "genre": "软科幻"})
print("建临时项目:", st, proj if st >= 400 else proj.get("id") or proj)
if st >= 400:
    print(proj)
    sys.exit(1)
pid = proj.get("id") or proj.get("project", {}).get("id")

try:
    st, r = call(f"/projects/{pid}/scripts/save", {"content": "标题：测试\n梗概：一句话\n正文：\n场景：楼道/夜\n过客：你是谁？"})
    print("存一版剧本:", st, r)

    st, d = call(f"/projects/{pid}/scripts/preview", {
        "requirement": "把结尾钩子换成过客发现异常日志",
        "episodes": 3, "minutes_per_episode": 4,
        "genre": "软科幻", "visual_style": "live_action", "content": None,
    })
    print("有剧本时 preview:", st)
    assert isinstance(d, dict), d
    print("generate.chars =", d["generate"]["chars"])
    print("revise 存在 =", d["revise"] is not None, "| chars =", (d["revise"] or {}).get("chars"))
    print("content_note =", d["content_note"])
    print("--- revise 提示词里是否带上「修改意见」 ---")
    rv = "\n".join(m["content"] for m in d["revise"]["messages"])
    print("含修改意见原文:", "把结尾钩子换成过客发现异常日志" in rv)
    print("含现有剧本原文:", "过客：你是谁？" in rv)

    # instruction 优先于 requirement
    st, d2 = call(f"/projects/{pid}/scripts/preview", {
        "requirement": "创作要求不该被当意见",
        "instruction": "意见走正门",
        "content": None,
    })
    rv2 = "\n".join(m["content"] for m in d2["revise"]["messages"])
    print("instruction 优先:", "意见走正门" in rv2, "| requirement 未串入:", "创作要求不该被当意见" not in rv2)
finally:
    st, r = call(f"/projects/{pid}", method="DELETE")
    print("清理临时项目:", st, r)
