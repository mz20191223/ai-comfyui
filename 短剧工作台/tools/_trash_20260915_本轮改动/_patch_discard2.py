# -*- coding: utf-8 -*-
"""shots.py 回退段收尾（该块为 LF 结尾）。"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

P = r"D:\Aicomfyui\短剧工作台\backend\app\routers\shots.py"
t = open(P, encoding="utf-8", newline="").read()

old = '        ws = (project or {}).get("workspace_dir") or DEFAULT_WORKSPACE\n        ddir = str(Path(ws) / "重制版" / "废弃产物")\n'
new = '        ddir = str(DEFAULT_DISCARD_DIR)\n'
c = t.count(old)
assert c == 1, f"匹配 {c} 次"
open(P, "w", encoding="utf-8", newline="").write(t.replace(old, new))
print("shots.py fallback OK")
