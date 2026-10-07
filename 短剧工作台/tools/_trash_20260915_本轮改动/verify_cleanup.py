"""验收：迁移是否生效 + 新接口是否可用（绕开沙箱代理）。"""
from __future__ import annotations

import json
import sqlite3
import time
import urllib.request
from pathlib import Path

DB = r"D:/Aicomfyui/短剧工作台/data/studio.db"
BASE = "http://127.0.0.1:8770/api"
_op = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def req(path: str, method: str = "GET", body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method,
                               headers={"Content-Type": "application/json"})
    with _op.open(r, timeout=30) as resp:
        return json.loads(resp.read().decode())


def wait_up(limit: int = 40) -> bool:
    for _ in range(limit):
        try:
            req("/health")
            return True
        except Exception:
            time.sleep(0.5)
    return False


if not wait_up():
    raise SystemExit("后端没起来")
print("后端已就绪\n")

print("=== 1) schema 迁移结果 ===")
c = sqlite3.connect(DB)
c.row_factory = sqlite3.Row
shot_cols = {r[1] for r in c.execute("PRAGMA table_info(shots)")}
print("  shots.readiness 已删:", "readiness" not in shot_cols)
print("  shots.confirmed_at 已删:", "confirmed_at" not in shot_cols)
task_cols = {r[1] for r in c.execute("PRAGMA table_info(generation_tasks)")}
print("  generation_tasks.fail_kind 已加:", "fail_kind" in task_cols)
print("  generation_tasks.fail_message 已加:", "fail_message" in task_cols)
tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
print("  shot_candidates 已删:", "shot_candidates" not in tables)
print("  shot_dialogue_candidates 已删:", "shot_dialogue_candidates" not in tables)
idx = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='index'")}
print("  idx_shots_ready 已删:", "idx_shots_ready" not in idx)
print("  任务态枚举:", [dict(r) for r in c.execute(
    "SELECT status, COUNT(*) n FROM generation_tasks GROUP BY status")])

print("\n=== 2) 看板接口（含出图/出视频两槽） ===")
shots = req("/episodes/1/shots")
print(f"  第1集 {len(shots)} 个镜头")
s0 = shots[0]
print("  首镜字段里已无 readiness:", "readiness" not in s0)
print("  首镜字段里已无 pending_candidates:", "pending_candidates" not in s0)
ts = s0["task_state"]
print("  task_state 键:", sorted(ts.keys()))
print("  · image 槽:", ts["image"])
print("  · video 槽:", ts["video"])

print("\n=== 3) 镜头详情（不再返回 candidates） ===")
d = req(f"/shots/{s0['id']}")
print("  已无 candidates 字段:", "candidates" not in d)
print("  shot 里已无 confirmed_at:", "confirmed_at" not in d["shot"])
print("  task_state.image:", d["task_state"]["image"])

print("\n=== 4) 已删接口应当 404 ===")
for path, method in (("/shots/1/confirm", "POST"), ("/shots/1/unconfirm", "POST"),
                     ("/shots/1/candidates/1", "POST")):
    try:
        req(path, method, {})
        print(f"  ✗ {method} {path} 竟然还通")
    except urllib.error.HTTPError as e:
        print(f"  ✓ {method} {path} → HTTP {e.code}")

print("\n=== 5) 项目总览（不再有 ready / pending_confirm） ===")
ov = req("/projects/1/overview")
ep0 = ov["episodes"][0]
print("  单集字段:", sorted(ep0.keys()))
print("  已无 ready:", "ready" not in ep0, "｜已无 pending_confirm:", "pending_confirm" not in ep0)

print("\n=== 6) 新建集总览的 ready_count 已去 ===")
eps = req("/projects/1/episodes")
print("  episode 键:", sorted(eps[0].keys()) if eps else "无")
print("  已无 ready_count:", eps and "ready_count" not in eps[0])
