"""验证 list_shots 批量版与旧逐镜版结果**完全一致**（临时验收脚本）。

旧实现按「每镜一次查询」写死在下面（照抄改动前 shot_service.list_shots 的逻辑），
新版走批量。两者 JSON 序列化后必须逐字节相同，否则报差异。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"D:/Aicomfyui/短剧工作台/backend")

from app.core import db  # noqa: E402
from app.services import shot_service  # noqa: E402


def old_list_shots(episode_id: int) -> list[dict]:
    """改动前的实现（原样照抄，作为黄金参照）。"""
    shots = db.query("SELECT * FROM shots WHERE episode_id=? ORDER BY sort_order, id", (episode_id,))
    out = []
    for s in shots:
        d = db.query_one("SELECT * FROM shot_details WHERE shot_id=?", (s["id"],)) or {}
        links_v = db.query(
            "SELECT * FROM shot_asset_links WHERE shot_id=? AND target_side='video' ORDER BY slot_index",
            (s["id"],))
        links_i = db.query(
            "SELECT * FROM shot_asset_links WHERE shot_id=? AND target_side='image' ORDER BY slot_index",
            (s["id"],))
        line = db.query_one("SELECT * FROM shot_dialog_lines WHERE shot_id=? LIMIT 1", (s["id"],))
        pending_cand = db.query_one(
            "SELECT COUNT(*) AS c FROM shot_candidates WHERE shot_id=? AND candidate_status='pending'",
            (s["id"],))["c"]
        issues = db.query(
            "SELECT severity, issue_type, message FROM health_issues WHERE shot_id=?", (s["id"],))
        out.append({
            "id": s["id"], "shot_code": s["shot_code"], "title": s["title"],
            "readiness": s["readiness"], "sort_order": s["sort_order"],
            "duration_sec": d.get("duration_sec"), "gen_mode": d.get("gen_mode"),
            "api_style": d.get("api_style"), "image_target_name": d.get("image_target_name"),
            "image_is_optional": d.get("image_is_optional"), "resolution": d.get("resolution"),
            "video_ref_count": len(links_v), "image_ref_count": len(links_i),
            "first_ref": (links_v[0]["file_name"] if links_v else None),
            "audio_file": line["audio_file"] if line else None,
            "audio_measured_sec": line["audio_measured_sec"] if line else None,
            "line_text": line["text"] if line else None,
            "role_name": line["role_name"] if line else None,
            "line_start_sec": line["start_sec"] if line else None,
            "pending_candidates": pending_cand,
            "task_state": shot_service.aggregate_task_state(s["id"]),
            "status": shot_service._shot_status_summary(s["id"]),
            "issues": issues,
            "error_count": sum(1 for i in issues if i["severity"] == "error"),
            "warn_count": sum(1 for i in issues if i["severity"] == "warn"),
            "summary": (d.get("summary") or "")[:120],
        })
    return out


def diff(a: dict, b: dict, path: str = "") -> list[str]:
    """递归找差异，返回人类可读的差异列表。"""
    msgs = []
    for k in sorted(set(a) | set(b)):
        p = f"{path}.{k}" if path else k
        if k not in a:
            msgs.append(f"  仅新版有: {p}")
        elif k not in b:
            msgs.append(f"  仅旧版有: {p}")
        elif isinstance(a[k], dict) and isinstance(b[k], dict):
            msgs.extend(diff(a[k], b[k], p))
        elif a[k] != b[k]:
            msgs.append(f"  {p}: 旧={a[k]!r}  新={b[k]!r}")
    return msgs


print("=" * 78)
print("list_shots 批量版 vs 逐镜版 —— 逐字段一致性校验")
print("=" * 78)

all_ok = True
for ep in (1, 2, 3):
    import time
    t0 = time.perf_counter()
    new = shot_service.list_shots(ep)
    t_new = (time.perf_counter() - t0) * 1000
    t0 = time.perf_counter()
    old = old_list_shots(ep)
    t_old = (time.perf_counter() - t0) * 1000

    same = json.dumps(old, sort_keys=True, ensure_ascii=False) == \
        json.dumps(new, sort_keys=True, ensure_ascii=False)
    print(f"\n第{ep}集：{len(new)} 镜   旧 {t_old:8.1f} ms  →  新 {t_new:7.1f} ms"
          f"   提速 {t_old/max(t_new,0.01):.0f}×   {'✅ 完全一致' if same else '❌ 有差异'}")
    if not same:
        all_ok = False
        if len(old) != len(new):
            print(f"  镜头数不同: 旧 {len(old)} / 新 {len(new)}")
        for i, (o, n) in enumerate(zip(old, new)):
            msgs = diff(o, n, f"[{i}]{n.get('shot_code')}")
            if msgs:
                print("\n".join(msgs[:20]))
                break

print("\n" + "=" * 78)
print("结论:", "✅ 全部一致，可以替换" if all_ok else "❌ 存在差异，需排查")
print("=" * 78)
db.close_conn()
sys.exit(0 if all_ok else 1)
