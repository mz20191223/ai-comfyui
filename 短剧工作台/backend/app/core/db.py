"""SQLite 连接与初始化。

要点：
- **每线程一条连接，长期复用**（原先每次查询都新建连接，是本机接口慢的主因）
- row_factory = sqlite3.Row，方便直接转 dict
- WAL 模式：库级持久属性，只在 init_db 设一次

⚠️ 性能约定（2026-09-16 定）
本机装了绿盾过滤驱动，`sqlite3.connect()` 单次约 10~30ms，而一条查询只要约 0.1ms。
原先 `db.query()` 每次新建连接，导致看板页（约 340 次查询）单次要跑 55 秒。
因此：连接一律走 `conn()` 取本线程缓存，**不要自己 `sqlite3.connect`**。
"""
from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable

from ..config import DB_PATH

_SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
_init_lock = threading.Lock()
_initialized = False
_local = threading.local()


def _connect() -> sqlite3.Connection:
    """真正开一条新连接（贵，只在没有缓存时调用）。"""
    conn = sqlite3.connect(str(DB_PATH), timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # journal_mode=WAL 是「库级」持久属性，设一次就写在库头里，后续连接自动继承；
    # 每次连接都设会去抢写锁，白花十几毫秒。这里只保留连接级的两条 PRAGMA。
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def conn() -> sqlite3.Connection:
    """取本线程复用的连接（不存在则建一条）。线程内长期复用，不主动关闭。"""
    c = getattr(_local, "conn", None)
    if c is None:
        c = _connect()
        _local.conn = c
    return c


@contextmanager
def get_conn():
    """事务边界：正常提交、异常回滚。连接由本线程复用，这里**不关闭**。"""
    c = conn()
    try:
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise


def close_conn() -> None:
    """关闭本线程连接。供脚本/测试收尾，避免进程退出时残留 WAL。"""
    c = getattr(_local, "conn", None)
    if c is not None:
        try:
            c.close()
        finally:
            _local.conn = None


def init_db(force: bool = False) -> None:
    global _initialized
    with _init_lock:
        if _initialized and not force:
            return
        schema = _SCHEMA_PATH.read_text(encoding="utf-8")
        with get_conn() as conn:
            conn.execute("PRAGMA journal_mode=WAL")  # 库级属性，设一次即持久
            conn.executescript(schema)
            _migrate(conn)
        _initialized = True


# 轻量迁移：schema.sql 用 IF NOT EXISTS，已存在的表加不了新列，这里补齐
_MIGRATIONS: list[tuple[str, str, str]] = [
    ("generation_tasks", "credential_id", "INTEGER"),
    ("generation_tasks", "credential_alias", "TEXT"),
    ("shot_details", "wiz_image_note", "TEXT"),
    ("shot_details", "wiz_video_note", "TEXT"),
    ("generation_tasks", "fail_kind", "TEXT"),
    ("generation_tasks", "fail_message", "TEXT"),
    ("projects", "discard_dir", "TEXT"),
    ("timeline_clips", "manual", "INTEGER DEFAULT 0"),
]

# 已废弃结构（2026-09-16 定：就绪态整轨 + 候选确认流都不要了）
# 删列前必须先删引用它的索引，否则 SQLite 会拒绝。
_DROP_INDEXES = ("idx_shots_ready",)
_DROP_COLUMNS: list[tuple[str, str]] = [
    ("shots", "readiness"),
    ("shots", "confirmed_at"),
]
_DROP_TABLES = ("shot_candidates", "shot_dialogue_candidates")


def _migrate(conn: sqlite3.Connection) -> None:
    for table, col, decl in _MIGRATIONS:
        info = conn.execute(f"PRAGMA table_info({table})").fetchall()
        if not info:
            continue
        if col not in {r[1] for r in info}:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")

    for idx in _DROP_INDEXES:
        conn.execute(f"DROP INDEX IF EXISTS {idx}")
    for table, col in _DROP_COLUMNS:
        info = conn.execute(f"PRAGMA table_info({table})").fetchall()
        if info and col in {r[1] for r in info}:
            conn.execute(f"ALTER TABLE {table} DROP COLUMN {col}")
    for table in _DROP_TABLES:
        conn.execute(f"DROP TABLE IF EXISTS {table}")

    # 任务态枚举改名：pending → submitted（语义不变，只是措辞对齐）
    conn.execute("UPDATE generation_tasks SET status='submitted' WHERE status='pending'")

    # 废弃目录回填：与 config.DEFAULT_DISCARD_DIR 同值（db 层不反向 import config，写死）
    conn.execute(
        "UPDATE projects SET discard_dir=? WHERE discard_dir IS NULL OR discard_dir=''",
        (r"D:\Aicomfyui\minimax3创作内容\重制版\废弃内容",),
    )


# ---------------- 便捷查询封装 ----------------

def query(sql: str, params: Iterable[Any] = ()) -> list[dict]:
    with get_conn() as conn:
        cur = conn.execute(sql, tuple(params))
        return [dict(r) for r in cur.fetchall()]


def query_one(sql: str, params: Iterable[Any] = ()) -> dict | None:
    rows = query(sql, params)
    return rows[0] if rows else None


def execute(sql: str, params: Iterable[Any] = ()) -> int:
    with get_conn() as conn:
        cur = conn.execute(sql, tuple(params))
        return cur.lastrowid or cur.rowcount


def executemany(sql: str, seq: Iterable[Iterable[Any]]) -> None:
    with get_conn() as conn:
        conn.executemany(sql, [tuple(x) for x in seq])


def update_row(table: str, pk_col: str, pk_val: Any, values: dict) -> None:
    """按主键更新若干列；若表有 updated_at 列则自动带上。"""
    if not values:
        return
    values = dict(values)
    cols_sql = ", ".join(f"{k} = ?" for k in values)
    sql = f"UPDATE {table} SET {cols_sql} WHERE {pk_col} = ?"
    execute(sql, list(values.values()) + [pk_val])


def jloads(text: str | None, default: Any = None) -> Any:
    if not text:
        return default
    try:
        return json.loads(text)
    except Exception:
        return default


def jdumps(obj: Any) -> str | None:
    if obj is None:
        return None
    return json.dumps(obj, ensure_ascii=False)
