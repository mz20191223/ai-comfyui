"""连接开销基准：验证「每查询新建连接 + 每次 PRAGMA journal_mode=WAL」的代价（临时脚本）"""
import sqlite3
import time
from pathlib import Path

DB = r"D:/Aicomfyui/短剧工作台/data/studio.db"
N = 340


def bench(label, fns):
    t0 = time.perf_counter()
    for _ in range(N):
        for fn in fns:
            fn()
    dt = time.perf_counter() - t0
    print(f"{dt*1000:9.1f} ms  {label}  ({dt/N*1000:.2f} ms/轮)")
    return dt


def open_plain():
    return sqlite3.connect(DB, timeout=30.0, check_same_thread=False)


def open_full():
    c = sqlite3.connect(DB, timeout=30.0, check_same_thread=False)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    c.execute("PRAGMA synchronous=NORMAL")
    return c


def open_no_wal():
    c = sqlite3.connect(DB, timeout=30.0, check_same_thread=False)
    c.execute("PRAGMA foreign_keys=ON")
    c.execute("PRAGMA synchronous=NORMAL")
    return c


def run(fn):
    c = fn()
    try:
        c.execute("SELECT 1").fetchall()
    finally:
        c.close()


print(f"DB = {DB}  ({Path(DB).stat().st_size/1024/1024:.1f} MB)")
print(f"重复 {N} 次（≈ list_shots 的连接次数）\n")
bench("仅 connect+close", [lambda: run(open_plain)])
bench("connect + 3 条 PRAGMA（现状）", [lambda: run(open_full)])
bench("connect + 2 条 PRAGMA（去掉 journal_mode）", [lambda: run(open_no_wal)])

print("\n=== 复用同一连接 ===")
t0 = time.perf_counter()
c = open_full()
for _ in range(N):
    c.execute("SELECT 1").fetchall()
dt = time.perf_counter() - t0
print(f"{dt*1000:9.1f} ms  单连接复用 {N} 次查询")

print("\n=== WAL 状态 ===")
c = sqlite3.connect(DB)
print("journal_mode =", c.execute("PRAGMA journal_mode").fetchone()[0])
for suffix in ("", "-wal", "-shm"):
    p = Path(DB + suffix)
    print(f"  {p.name:<14} {p.stat().st_size/1024:>10.1f} KB" if p.exists() else f"  {p.name:<14} (不存在)")
