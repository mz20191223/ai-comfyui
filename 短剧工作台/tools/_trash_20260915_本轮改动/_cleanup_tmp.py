# -*- coding: utf-8 -*-
"""把本轮改动用的临时脚本收进 tools/_trash_20260915_本轮改动/（移动，不删除，可随时恢复）。"""
import os, shutil, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

TOOLS = r"D:\Aicomfyui\短剧工作台\tools"
TRASH = os.path.join(TOOLS, "_trash_20260915_本轮改动")

TEMP = [
    # 补丁脚本（改动已生效并验证）
    "_patch_now.py", "_patch_shots.py", "_patch_shotsvc.py", "_patch_fe.py",
    "_patch_task.py", "_patch_tc.py", "_patch_wiz_dlg.py", "_patch_board.py",
    # 验收脚本
    "verify_cleanup.py", "probe_cleanup.cjs",
    # 性能排查（看板卡顿那一轮）
    "_bench_conn.py", "_perf_after.py", "_perf_board.log",
    "_probe_navtiming.cjs", "_probe_proxy.cjs", "_probe_waterfall.cjs",
    "_verify_list_shots.py",
    # 本轮可点句探针 / 端到端
    "_probe_note.py", "_probe_note.log", "_probe_note2.log",
    "_e2e_wizlink.py", "_e2e_wizlink.cjs",
    "_e2e.log", "_e2e2.log", "_e2e3.log", "_e2e4.log",
]

os.makedirs(TRASH, exist_ok=True)
moved, missing = [], []
for n in TEMP:
    src = os.path.join(TOOLS, n)
    if os.path.exists(src):
        dst = os.path.join(TRASH, n)
        if os.path.exists(dst):
            os.remove(dst)
        shutil.move(src, dst)
        moved.append(n)
    else:
        missing.append(n)

# 镜头90 的备份留着当保险（万一之后要再核对）
bak = os.path.join(TOOLS, "_shot90_backup.json")
if os.path.exists(bak):
    shutil.move(bak, os.path.join(TRASH, "_shot90_backup.json"))
    moved.append("_shot90_backup.json（保留，未删）")

print("已收起 %d 个临时文件 → %s" % (len(moved), TRASH))
for n in moved:
    print("   ", n)
if missing:
    print("未找到（可能早前已清）:", missing)

print("\ntools/ 现在剩下的内容:")
for n in sorted(os.listdir(TOOLS)):
    f = os.path.join(TOOLS, n)
    print("   %s%s" % ("[目录] " if os.path.isdir(f) else "       ", n))
