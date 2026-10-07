# -*- coding: utf-8 -*-
"""db.py 迁移后回填 discard_dir（该文件 LF 结尾）。"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

P = r"D:\Aicomfyui\短剧工作台\backend\app\core\db.py"
t = open(P, encoding="utf-8", newline="").read()

old = '    # 任务态枚举改名：pending → submitted（语义不变，只是措辞对齐）\n    conn.execute("UPDATE generation_tasks SET status=\'submitted\' WHERE status=\'pending\'")\n'
new = (
    '    # 任务态枚举改名：pending → submitted（语义不变，只是措辞对齐）\n'
    '    conn.execute("UPDATE generation_tasks SET status=\'submitted\' WHERE status=\'pending\'")\n\n'
    '    # 废弃目录回填：与 config.DEFAULT_DISCARD_DIR 同值（db 层不反向 import config，写死）\n'
    '    conn.execute(\n'
    '        "UPDATE projects SET discard_dir=? WHERE discard_dir IS NULL OR discard_dir=\'\'",\n'
    '        (r"D:\\Aicomfyui\\minimax3创作内容\\重制版\\废弃内容",),\n'
    '    )\n'
)
c = t.count(old)
assert c == 1, f"匹配 {c} 次"
open(P, "w", encoding="utf-8", newline="").write(t.replace(old, new))
print("db.py backfill OK")
