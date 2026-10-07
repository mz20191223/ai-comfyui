"""一次性补丁：删除就绪态(readiness/confirmed_at)与候选确认流，并改任务态枚举。

每处替换都断言「精确命中 1 次」，任一处对不上就整体不写回，避免改错。
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(r"D:/Aicomfyui/短剧工作台/backend")


def patch(rel: str, pairs: list[tuple[str, str]]) -> tuple[bool, list[str]]:
    p = ROOT / rel
    t = p.read_text(encoding="utf-8")
    log = []
    ok = True
    for old, new in pairs:
        n = t.count(old)
        if n != 1:
            log.append(f"  ✗ 命中 {n} 次（应为 1）：{old.strip().splitlines()[0][:70]}")
            ok = False
            continue
        t = t.replace(old, new, 1)
        log.append(f"  ✓ {old.strip().splitlines()[0][:70]}")
    if ok:
        p.write_text(t, encoding="utf-8")
    return ok, log


# ---------------- importer.py ----------------
IMPORTER = [
    (
        "    frames_linked: int = 0\n    candidates_created: int = 0\n",
        "    frames_linked: int = 0\n",
    ),
    (
        "    _resolve_tail_frames(project, ep_id, vshots, search_dirs, res)\n"
        "    _recompute_readiness(ep_id)\n"
        "    _scan_health(project, ep_id, res)\n",
        "    _resolve_tail_frames(project, ep_id, vshots, search_dirs, res)\n"
        "    _scan_health(project, ep_id, res)\n",
    ),
    (
        '            """INSERT INTO shots(episode_id, shot_code, title, sort_order, readiness, notes, meta)\n'
        "               VALUES(?,?,?,?,?,?,?)\"\"\",\n"
        '            (ep_id, vs.shot_code, vs.title or None, order, "draft", notes or None, None),\n',
        '            """INSERT INTO shots(episode_id, shot_code, title, sort_order, notes, meta)\n'
        "               VALUES(?,?,?,?,?,?)\"\"\",\n"
        "            (ep_id, vs.shot_code, vs.title or None, order, notes or None, None),\n",
    ),
    (
        "        if not real and fname and not file_store.is_placeholder(fname):\n"
        "            _add_candidate(shot_id, kind, file_store.guess_asset_name(fname) or fname,\n"
        "                           f\"ref_image_{it.image_index}\", {\"file_name\": fname}, res)\n"
        "            res.issues.append(\n",
        "        if not real and fname and not file_store.is_placeholder(fname):\n"
        "            res.issues.append(\n",
    ),
    (
        "            if not real and fname and not file_store.is_placeholder(fname):\n"
        "                _add_candidate(shot_id, kind, file_store.guess_asset_name(fname) or fname,\n"
        "                               f\"上传参考图#{it.index}\", {\"file_name\": fname}, res)\n"
        "            db.execute(\n",
        "            db.execute(\n",
    ),
    (
        "def _add_candidate(shot_id: int, ctype: str, name: str, hint: str, payload: dict, "
        "res: ImportResult) -> None:\n"
        "    t = {\n"
        '        "asset_character": "character",\n'
        '        "asset_scene": "scene",\n'
        '        "asset_prop": "prop",\n'
        '        "tail_frame": "prop",\n'
        '        "keyframe": "prop",\n'
        '    }.get(ctype, "prop")\n'
        "    exists = db.query_one(\n"
        '        "SELECT id FROM shot_candidates WHERE shot_id=? AND candidate_type=? AND candidate_name=?",\n'
        "        (shot_id, t, name),\n"
        "    )\n"
        "    if exists:\n"
        "        return\n"
        "    db.execute(\n"
        '        """INSERT INTO shot_candidates(shot_id, candidate_type, candidate_name, source_hint, payload)\n'
        "           VALUES(?,?,?,?,?)\"\"\",\n"
        "        (shot_id, t, name, hint, jdumps(payload)),\n"
        "    )\n"
        "    res.candidates_created += 1\n"
        "\n"
        "\n"
        "# ---------------- 尾帧 ↔ 镜头 互链 ----------------\n",
        "# ---------------- 尾帧 ↔ 镜头 互链 ----------------\n",
    ),
    (
        "# ---------------- 就绪态重算（双轨之静态轨） ----------------\n"
        "\n"
        "def _recompute_readiness(ep_id: int) -> None:\n"
        '    """就绪态 = 静态轨：有待确认候选 → pending_confirm；否则 ready。"""\n'
        '    shots = db.query("SELECT id FROM shots WHERE episode_id=?", (ep_id,))\n'
        "    for s in shots:\n"
        "        pending = db.query_one(\n"
        '            "SELECT COUNT(*) AS c FROM shot_candidates WHERE shot_id=? AND candidate_status=\'pending\'",\n'
        '            (s["id"],),\n'
        '        )["c"]\n'
        "        pending_dlg = db.query_one(\n"
        '            "SELECT COUNT(*) AS c FROM shot_dialogue_candidates WHERE shot_id=? AND '
        "candidate_status='pending'\",\n"
        '            (s["id"],),\n'
        '        )["c"]\n'
        '        has_detail = db.query_one("SELECT 1 AS x FROM shot_details WHERE shot_id=?", (s["id"],))\n'
        "        if not has_detail:\n"
        '            state = "extracting"\n'
        "        elif pending or pending_dlg:\n"
        '            state = "pending_confirm"\n'
        "        else:\n"
        '            state = "ready"\n'
        '        db.execute("UPDATE shots SET readiness=? WHERE id=?", (state, s["id"]))\n'
        "\n"
        "\n"
        "# ---------------- 健康巡检 ----------------\n",
        "# ---------------- 健康巡检 ----------------\n",
    ),
    (
        '    shots = db.query("SELECT id, shot_code, readiness, thumbnail_path FROM shots WHERE episode_id=?", (ep_id,))\n',
        '    shots = db.query("SELECT id, shot_code, thumbnail_path FROM shots WHERE episode_id=?", (ep_id,))\n',
    ),
]

# ---------------- bootstrap.py ----------------
BOOTSTRAP = [
    (
        '                f" 资产新建 {r.assets_created} 引用槽 {r.links_created} 尾帧挂载 {r.frames_linked}"\n'
        '                f" 候选 {r.candidates_created} 问题 {len(r.issues)}"\n',
        '                f" 资产新建 {r.assets_created} 引用槽 {r.links_created} 尾帧挂载 {r.frames_linked}"\n'
        '                f" 问题 {len(r.issues)}"\n',
    ),
]

# ---------------- creation.py ----------------
CREATION = [
    (
        '                """INSERT INTO shots(episode_id, shot_code, title, sort_order, readiness, script_excerpt)\n'
        '                   VALUES(?,?,?,?,?,?)\"\"\",\n'
        '                (episode_id, code, d.get("title") or None, i, "ready", d.get("script_excerpt")),\n',
        '                """INSERT INTO shots(episode_id, shot_code, title, sort_order, script_excerpt)\n'
        '                   VALUES(?,?,?,?,?)\"\"\",\n'
        '                (episode_id, code, d.get("title") or None, i, d.get("script_excerpt")),\n',
    ),
]

# ---------------- projects.py ----------------
PROJECTS = [
    (
        '        e["ready_count"] = db.query_one(\n'
        '            "SELECT COUNT(*) AS c FROM shots WHERE episode_id=? AND readiness=\'ready\'", (e["id"],)\n'
        '        )["c"]\n',
        "",
    ),
    (
        '        ready = db.query_one(\n'
        '            "SELECT COUNT(*) AS c FROM shots WHERE episode_id=? AND readiness=\'ready\'", (e["id"],)\n'
        '        )["c"]\n'
        "        pending = db.query_one(\n"
        '            "SELECT COUNT(*) AS c FROM shots WHERE episode_id=? AND readiness=\'pending_confirm\'", (e["id"],)\n'
        '        )["c"]\n',
        "",
    ),
    (
        "               WHERE s.episode_id=? AND t.status IN ('pending','running')\"\"\",",
        "               WHERE s.episode_id=? AND t.status IN ('submitted','running')\"\"\",",
    ),
    (
        '            "shots": len(shots),\n'
        '            "ready": ready,\n'
        '            "pending_confirm": pending,\n'
        '            "producing": running,\n',
        '            "shots": len(shots),\n'
        '            "producing": running,\n',
    ),
]


def main() -> None:
    results = [
        ("app/parsers/importer.py", IMPORTER),
        ("scripts/bootstrap.py", BOOTSTRAP),
        ("app/routers/creation.py", CREATION),
        ("app/routers/projects.py", PROJECTS),
    ]
    all_ok = True
    for rel, pairs in results:
        ok, log = patch(rel, pairs)
        all_ok &= ok
        print(f"{'OK ' if ok else 'FAIL'} {rel}")
        for line in log:
            print(line)
    print()
    print("全部通过" if all_ok else "!! 有未命中项，已跳过写回的文件需要人工检查")


if __name__ == "__main__":
    main()
