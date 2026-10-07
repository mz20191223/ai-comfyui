# -*- coding: utf-8 -*-
"""单独移除 creation.py 里的 production_plan（上一个脚本跑到这里才断言失败，前 4 个文件已改好）。"""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = r"D:\Aicomfyui\短剧工作台\backend\app\routers\creation.py"
with io.open(P, "r", encoding="utf-8", newline="") as f:
    lines = f.readlines()

idx = [i for i, l in enumerate(lines) if "def production_plan(episode_id: int" in l]
assert len(idx) == 1, f"production_plan 定义数 = {len(idx)}"
i = idx[0]
print("=== 定位核对 (0-based %d) ===" % i)
for k in range(i - 4, min(i + 3, len(lines))):
    print("  %4d | %s" % (k + 1, lines[k].rstrip()[:120]))

assert '@router.post("/episodes/{episode_id}/production-plan")' in lines[i - 1], lines[i - 1]
assert "批量生成前的预审" in lines[i + 1], lines[i + 1]
assert lines[i - 3].lstrip().startswith("#"), lines[i - 3]
assert lines[-1].strip() == "}", ("文件末行不是 }，production_plan 可能不是末尾函数", lines[-1])
assert "@router" not in "".join(lines[i:]), "production_plan 之后还有别的路由，需人工确认"

keep = lines[:i - 3]
while keep and keep[-1].strip() == "":
    keep.pop()
if not keep[-1].endswith(("\n", "\r")):
    keep[-1] += "\n"

assert "production_plan" not in "".join(keep), "仍有残留"
with io.open(P, "w", encoding="utf-8", newline="") as f:
    f.writelines(keep)

t = io.open(P, encoding="utf-8", newline="").read()
print("\n=== 删除后 ===")
print("  production_plan 残留:", t.count("production_plan"))
print("  文件行数:", t.count("\n") + 1)
print("  末尾 3 行:")
for l in t.rstrip("\n").splitlines()[-3:]:
    print("   ", l[:110])
print("  file_store 仍被使用:", t.count("file_store"), "次  naming:", t.count("naming"), "次")
