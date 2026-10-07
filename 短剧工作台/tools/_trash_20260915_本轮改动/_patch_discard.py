# -*- coding: utf-8 -*-
"""废弃目录定名「废弃内容」：config 常量 / projects 推导 / shots 回退 / db 回填。"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

def patch(path, old, new, n=1):
    t = open(path, encoding="utf-8", newline="").read()
    c = t.count(old)
    assert c == n, f"{path} 匹配 {c} 次（期望 {n}）：{old[:70]!r}"
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new))
    print("OK", path.split("\\")[-1])

B = r"D:\Aicomfyui\短剧工作台\backend\app"

# 1) config.py：全局废弃目录常量
patch(
    rf"{B}\config.py",
    'DEFAULT_REMAKE_DIR = DEFAULT_WORKSPACE / "重制版"',
    'DEFAULT_REMAKE_DIR = DEFAULT_WORKSPACE / "重制版"\r\n'
    'DEFAULT_DISCARD_DIR = DEFAULT_REMAKE_DIR / "废弃内容"   # 废弃产物统一放这里（2026-09-16 用户指定）',
)

# 2) projects.py：推导目录改用常量
patch(
    rf"{B}\routers\projects.py",
    '"discard_dir": str(remake / "废弃产物"),',
    '"discard_dir": str(DEFAULT_DISCARD_DIR),',
)
patch(
    rf"{B}\routers\projects.py",
    "from ..config import (\r\n    DEFAULT_DOC_DIR,\r\n    DEFAULT_REMAKE_DIR,\r\n    DEFAULT_WORKSPACE,\r\n)",
    "from ..config import (\r\n    DEFAULT_DISCARD_DIR,\r\n    DEFAULT_DOC_DIR,\r\n    DEFAULT_REMAKE_DIR,\r\n    DEFAULT_WORKSPACE,\r\n)",
)

# 3) shots.py：回退路径改用全局常量
patch(
    rf"{B}\routers\shots.py",
    "from ..config import DEFAULT_WORKSPACE",
    "from ..config import DEFAULT_DISCARD_DIR",
)
patch(
    rf"{B}\routers\shots.py",
    '        ws = (project or {}).get("workspace_dir") or DEFAULT_WORKSPACE\r\n        ddir = str(Path(ws) / "重制版" / "废弃产物")',
    '        ddir = str(DEFAULT_DISCARD_DIR)',
)

# 4) db.py：迁移后回填 NULL 的 discard_dir（与 config.DEFAULT_DISCARD_DIR 同值，避免循环导入写死）
patch(
    rf"{B}\core\db.py",
    '    # 任务态枚举改名：pending → submitted（语义不变，只是措辞对齐）\r\n    conn.execute("UPDATE generation_tasks SET status=\'submitted\' WHERE status=\'pending\'")',
    '    # 任务态枚举改名：pending → submitted（语义不变，只是措辞对齐）\r\n'
    '    conn.execute("UPDATE generation_tasks SET status=\'submitted\' WHERE status=\'pending\'")\r\n\r\n'
    '    # 废弃目录回填：与 config.DEFAULT_DISCARD_DIR 同值（db 层不反向 import config）\r\n'
    '    conn.execute(\r\n'
    '        "UPDATE projects SET discard_dir=? WHERE discard_dir IS NULL OR discard_dir=\'\'",\r\n'
    '        (r"D:\\Aicomfyui\\minimax3创作内容\\重制版\\废弃内容",),\r\n'
    '    )',
)

print("all patched")
