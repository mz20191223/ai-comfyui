"""一次性补丁：删除 shots.py 里就绪态与候选确认流。切片法删长段落。"""
from __future__ import annotations

from pathlib import Path

P = Path(r"D:/Aicomfyui/短剧工作台/backend/app/routers/shots.py")
t = P.read_text(encoding="utf-8")
orig_len = len(t)


def expect(old: str, new: str, label: str) -> None:
    global t
    n = t.count(old)
    if n != 1:
        raise SystemExit(f"✗ {label}: 命中 {n} 次（应为 1），未写回")
    t = t.replace(old, new, 1)
    print(f"  ✓ {label}")


# 1) SHOT_FIELDS 去 readiness
expect(
    'SHOT_FIELDS = {"shot_code", "title", "sort_order", "readiness", "script_excerpt", "notes",\n',
    'SHOT_FIELDS = {"shot_code", "title", "sort_order", "script_excerpt", "notes",\n',
    "SHOT_FIELDS",
)

# 2) 切片删掉 confirm / unconfirm / 候选确认流 / _refresh_readiness
start_marker = '@router.post("/shots/{shot_id}/confirm")\n'
end_marker = "# ---------------- 参考图槽位 ----------------\n"
i, j = t.find(start_marker), t.find(end_marker)
if i == -1 or j == -1 or j < i:
    raise SystemExit(f"✗ 候选确认流切片定位失败 start={i} end={j}")
removed = j - i
t = t[:i] + t[j:]
print(f"  ✓ 删除 confirm/unconfirm/候选确认流/_refresh_readiness（{removed} 字符）")

# 3) 新建镜头去掉直写 ready
expect(
    '        "INSERT INTO shots(episode_id, shot_code, title, sort_order, readiness) VALUES(?,?,?,?,?)",\n'
    '        (episode_id, body.shot_code, body.title, order, "ready"),\n',
    '        "INSERT INTO shots(episode_id, shot_code, title, sort_order) VALUES(?,?,?,?)",\n'
    '        (episode_id, body.shot_code, body.title, order),\n',
    "新建镜头 INSERT",
)

# 4) camera-options 去掉 readiness 可选项
expect(
    '        "readiness": [\n'
    '            {"value": "draft", "label": "草稿"},\n'
    '            {"value": "extracting", "label": "解析中"},\n'
    '            {"value": "pending_confirm", "label": "待确认"},\n'
    '            {"value": "ready", "label": "就绪"},\n'
    "        ],\n",
    "",
    "camera-options 的 readiness 选项",
)

P.write_text(t, encoding="utf-8")
print(f"\nshots.py {orig_len} → {len(t)} 字符（省 {orig_len - len(t)}）")

left = [kw for kw in ("readiness", "candidate", "confirmed_at", "_refresh_readiness") if kw in t]
print("残留关键词:", left or "无")
