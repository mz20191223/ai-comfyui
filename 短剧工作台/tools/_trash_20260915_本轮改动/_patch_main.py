# -*- coding: utf-8 -*-
"""把 scripts 路由注册进 main.py（CRLF 文件，字节级替换 + 唯一断言）。"""
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

P = r"D:\Aicomfyui\短剧工作台\backend\app\main.py"
src = open(P, encoding="utf-8", newline="").read()
orig = src
CRLF = "\r\n"


def sub(old, new, tag):
    global src
    hit = src.count(old)
    print(f"[{tag}] 命中 {hit} 处")
    if hit != 1:
        print(f"  !! 中止：期望 1 处，实际 {hit} 处")
        sys.exit(1)
    src = src.replace(old, new)


sub(
    "    prompts," + CRLF + "    shots,",
    "    prompts," + CRLF + "    scripts," + CRLF + "    shots,",
    "import",
)
sub(
    "app.include_router(shots.router)",
    "app.include_router(scripts.router)" + CRLF + "app.include_router(shots.router)",
    "include_router",
)

if src == orig:
    print("未发生任何修改")
    sys.exit(1)
open(P, "w", encoding="utf-8", newline="").write(src)
print("已写入 main.py")
ast.parse(open(P, encoding="utf-8").read())
print("语法检查通过")

# 顺带把新模块都过一遍语法
for p in (
    r"D:\Aicomfyui\短剧工作台\backend\app\routers\scripts.py",
    r"D:\Aicomfyui\短剧工作台\backend\app\services\script_service.py",
    r"D:\Aicomfyui\短剧工作台\backend\app\executors\task_runner.py",
):
    ast.parse(open(p, encoding="utf-8").read())
    print("语法 OK", p.rsplit("\\", 1)[-1])
