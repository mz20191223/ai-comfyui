"""一次性补丁：任务态枚举改造 + 失败归因落库 + 启动时僵尸回收。"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(r"D:/Aicomfyui/短剧工作台/backend")


def patch(rel: str, pairs: list[tuple[str, str]]) -> bool:
    p = ROOT / rel
    t = p.read_text(encoding="utf-8")
    ok = True
    for old, new in pairs:
        n = t.count(old)
        if n != 1:
            print(f"  ✗ 命中 {n} 次（应为 1）：{old.strip().splitlines()[0][:72]}")
            ok = False
            continue
        t = t.replace(old, new, 1)
        print(f"  ✓ {old.strip().splitlines()[0][:72]}")
    if ok:
        p.write_text(t, encoding="utf-8")
    else:
        print("  !! 未写回")
    return ok


RUNNER = [
    # 1) 建单即「已提交」
    (
        '        (task_kind, mode, "pending", 0, priority, provider_id, model_id, jdumps(payload or {}), max_attempts),',
        '        (task_kind, mode, "submitted", 0, priority, provider_id, model_id, jdumps(payload or {}), max_attempts),',
    ),
    # 2) _progress 支持「接口回执 → 转进行中」
    (
        'def _progress(task_id: int, pct: int, note: str = "") -> None:\n'
        "    _set(task_id, progress=max(0, min(100, int(pct))))\n",
        'def _progress(task_id: int, pct: int, note: str = "", mark_running: bool = False) -> None:\n'
        '    """回写进度。mark_running=True 表示这是接口回执，可把「已提交」推进到「进行中」。"""\n'
        "    kw: dict = {\"progress\": max(0, min(100, int(pct)))}\n"
        "    if mark_running:\n"
        '        cur = db.query_one("SELECT status FROM generation_tasks WHERE id=?", (task_id,))\n'
        '        if cur and cur["status"] == "submitted":\n'
        '            kw["status"] = "running"\n'
        "    _set(task_id, **kw)\n",
    ),
    # 3) 新增失败归因与僵尸回收（挂在 _cancelled 之后）
    (
        "def _cancelled(task_id: int) -> bool:\n"
        '    row = db.query_one("SELECT cancel_requested FROM generation_tasks WHERE id=?", (task_id,))\n'
        '    return bool(row and row["cancel_requested"])\n',
        "def _cancelled(task_id: int) -> bool:\n"
        '    row = db.query_one("SELECT cancel_requested FROM generation_tasks WHERE id=?", (task_id,))\n'
        '    return bool(row and row["cancel_requested"])\n'
        "\n"
        "\n"
        "# ---------------- 失败归因 / 僵尸回收 ----------------\n"
        "\n"
        "# provider_engine.detect_quota 给出的 kind → 任务态的失败原因\n"
        "_QUOTA_TO_FAIL = {\n"
        '    "exhausted": "insufficient_balance",   # 额度耗尽：余额不足 / 欠费\n'
        '    "cooling": "rate_limit",               # 限流冷却：稍后再试或换号\n'
        '    "invalid": "auth",                     # Key 无效 / 无权限\n'
        "}\n"
        "\n"
        "FAIL_TEXT = {\n"
        '    "insufficient_balance": "余额不足",\n'
        '    "rate_limit": "接口限流",\n'
        '    "auth": "密钥无效",\n'
        '    "api_error": "接口错误",\n'
        '    "interrupted": "进程中断",\n'
        "}\n"
        "\n"
        "\n"
        "def classify_failure(e: Exception) -> str:\n"
        '    """把异常归因到失败原因。额度类看 QuotaExceeded 带的 kind，其余都算接口问题。"""\n'
        '    qk = getattr(e, "kind", None)\n'
        "    if qk in _QUOTA_TO_FAIL:\n"
        "        return _QUOTA_TO_FAIL[qk]\n"
        '    return "api_error"\n'
        "\n"
        "\n"
        "def recover_zombies() -> int:\n"
        '    """进程启动时清理上次遗留的未终态任务。\n'
        "\n"
        "    任务跑在线程池里、纯内存。进程一重启，库里那些 submitted/running 就再也没人\n"
        "    更新了 —— 不打扫的话界面会永远显示「进行中」，只能手改数据库。\n"
        '    """\n'
        '    rows = db.query("SELECT id FROM generation_tasks WHERE status IN (\'submitted\',\'running\')")\n'
        "    if not rows:\n"
        "        return 0\n"
        '    ids = [r["id"] for r in rows]\n'
        '    ph = ",".join("?" * len(ids))\n'
        "    db.execute(\n"
        '        f"""UPDATE generation_tasks\n'
        "            SET status='failed', fail_kind='interrupted',\n"
        "                fail_message='进程重启导致中断',\n"
        "                error='进程重启导致中断（该次生成未完成）',\n"
        "                finished_at=datetime('now','localtime'),\n"
        "                updated_at=datetime('now','localtime')\n"
        "            WHERE id IN ({ph})\"\"\",\n"
        "        ids,\n"
        "    )\n"
        "    return len(ids)\n",
    ),
    # 4) 开工时按 mode 决定「已提交」还是「进行中」
    (
        '    _set(task_id, status="running", started_at=_now(), attempts=(row["attempts"] or 0) + 1)\n',
        "    # 本地任务（抽帧/合成/Lint/转码）没有「接口回执」这回事，直接算进行中；\n"
        "    # 走接口的任务先停在「已提交」，等第一次轮询回执再转「进行中」。\n"
        "    _set(\n"
        "        task_id,\n"
        '        status=("running" if row["mode"] == "local" else "submitted"),\n'
        "        started_at=_now(),\n"
        '        attempts=(row["attempts"] or 0) + 1,\n'
        "    )\n",
    ),
    # 5) 失败时把归因写进结构化字段
    (
        "def _fail(task_id: int, e: Exception) -> None:\n"
        "    msg = str(e)\n"
        '    detail = getattr(e, "detail", None)\n'
        '    stage = getattr(e, "stage", "")\n'
        "    tb = traceback.format_exc(limit=3)\n"
        "    _set(\n"
        '        task_id, status="failed", finished_at=_now(),\n'
        '        error=(f"[{stage}] " if stage else "") + msg,\n'
        '        result=jdumps({"detail": detail, "traceback": tb.splitlines()[-3:]}),\n'
        "    )\n",
        "def _fail(task_id: int, e: Exception) -> None:\n"
        "    msg = str(e)\n"
        '    detail = getattr(e, "detail", None)\n'
        '    stage = getattr(e, "stage", "")\n'
        "    tb = traceback.format_exc(limit=3)\n"
        "    fk = classify_failure(e)\n"
        "    _set(\n"
        '        task_id, status="failed", finished_at=_now(),\n'
        '        error=(f"[{stage}] " if stage else "") + msg,\n'
        '        fail_kind=fk, fail_message=FAIL_TEXT.get(fk, "生成失败"),\n'
        '        result=jdumps({"detail": detail, "traceback": tb.splitlines()[-3:]}),\n'
        "    )\n",
    ),
    # 6) 取消：pending 改名 submitted
    (
        '    if row["status"] == "pending":\n'
        '        _set(task_id, status="cancelled", finished_at=_now(), error="用户取消")\n',
        '    if row["status"] == "submitted":\n'
        "        # 还没真正开跑，直接掐掉；已在跑的只能打标记，等执行器自查（协作式取消）\n"
        '        _set(task_id, status="cancelled", finished_at=_now(), error="用户取消")\n',
    ),
    # 7) 两处接口调用：进度回执可推进状态
    (
        "    res = PE.execute(bundle, {**payload, \"model_id\": None}, progress=lambda p, n: _progress(task_id, p, n))\n",
        "    res = PE.execute(bundle, {**payload, \"model_id\": None},\n"
        "                     progress=lambda p, n: _progress(task_id, p, n, mark_running=True))\n",
    ),
    (
        "    res = PE.execute(bundle, payload, progress=lambda p, n: _progress(task_id, p, n))\n",
        "    res = PE.execute(bundle, payload, progress=lambda p, n: _progress(task_id, p, n, mark_running=True))\n",
    ),
]

MAIN = [
    (
        "from app.core.db import init_db  # noqa: E402\n",
        "from app.core.db import init_db  # noqa: E402\n"
        "from app.executors import task_runner  # noqa: E402\n",
    ),
    (
        "    init_db()\n    seed_all()\n    yield\n",
        "    init_db()\n"
        "    seed_all()\n"
        "    # 上次进程留下的 submitted/running 已经没人更新了，扫一遍判为中断\n"
        "    leftover = task_runner.recover_zombies()\n"
        "    if leftover:\n"
        '        print(f"[startup] 回收僵尸任务 {leftover} 条（上次进程中断）")\n'
        "    yield\n",
    ),
]


def main() -> None:
    ok = True
    print("app/executors/task_runner.py")
    ok &= patch("app/executors/task_runner.py", RUNNER)
    print("app/main.py")
    ok &= patch("app/main.py", MAIN)
    print()
    print("全部通过" if ok else "!! 有未命中项")


if __name__ == "__main__":
    main()
