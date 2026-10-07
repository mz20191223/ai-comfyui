"""时间轴与合成：把各镜成片按镜序拼成整集。

三个能力：
1. 自动建轴 —— 按镜序扫描已出片视频，落成 timeline_clips（可一键重建）
2. 手工调轴 —— 单条片段的入出点、顺序、启停、转场
3. 合成出片 —— 交给任务中心跑 ffmpeg，不阻塞界面
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..core import db
from ..core.db import jloads
from ..executors import task_runner
from ..services import file_store, naming

router = APIRouter(prefix="/api", tags=["timeline"])


# ---------------- 读 ----------------

def _clip_rows(episode_id: int) -> list[dict]:
    rows = db.query(
        """SELECT c.*, s.shot_code FROM timeline_clips c
           LEFT JOIN shots s ON s.id = c.shot_id
           WHERE c.episode_id=? ORDER BY c.sort_order, c.id""",
        (episode_id,),
    )
    pos = 0.0
    for r in rows:
        r["exists"] = bool(r.get("file_path") and Path(r["file_path"]).exists())
        d = file_store.probe(r["file_path"]).get("duration_sec") if r["exists"] else None
        r["source_duration_sec"] = d
        in_s = r.get("in_sec")
        out_s = r.get("out_sec")
        start = in_s if in_s is not None else 0.0
        end = out_s if out_s is not None else (d or 0.0)
        r["effective_dur"] = max(0.0, round((end or 0) - (start or 0), 3))
        if r.get("enabled"):
            # 供界面预览拼接后的时间轴位置；不等于最终渲染结果
            r["preview_start"] = round(pos, 3)
            r["preview_end"] = round(pos + r["effective_dur"], 3)
            pos += r["effective_dur"]
        else:
            r["preview_start"] = r["preview_end"] = None
    return rows


@router.get("/episodes/{episode_id}/timeline")
def get_timeline(episode_id: int) -> dict:
    ep = db.query_one("SELECT * FROM episodes WHERE id=?", (episode_id,))
    if not ep:
        raise HTTPException(404, "集不存在")
    clips = _clip_rows(episode_id)
    enabled = [c for c in clips if c.get("enabled")]
    return {
        "episode_id": episode_id,
        "episode_number": ep["number"],
        "clips": clips,
        "summary": {
            "clip_count": len(clips),
            "enabled_count": len(enabled),
            "missing_count": sum(1 for c in clips if not c["exists"]),
            "total_duration_sec": round(sum(c["effective_dur"] for c in enabled), 2),
        },
    }


# ---------------- 自动建轴 ----------------

class AutoBuildIn(BaseModel):
    replace: bool = False
    include_missing: bool = False
    reencode_note: str | None = None


VIDEO_EXTS = (".mp4", ".mov", ".webm", ".mkv")


def _shot_video_candidates(shot_id: int) -> list[dict]:
    """本镜的所有成片候选：任务产物 + 「分镜视频」目录里按镜号命名的文件。

    任务侧按 id 倒序（新→旧），过滤掉已废弃标记与非视频后缀（历史上出现过把 mp4
    登记成 .png 的情况，界面上永远显示不出来，也不能拿去合成）；
    目录侧按「规范名优先，其余按 mtime 新→旧」排序，避免多版本时随机取一个。
    """
    out: list[dict] = []
    seen: set[str] = set()

    def push(path: str, source: str, extra: dict | None = None) -> None:
        if not path:
            return
        key = os.path.normcase(os.path.abspath(path))
        if key in seen:
            return
        seen.add(key)
        item = {
            "path": str(path), "name": Path(path).name, "source": source,
            "exists": Path(path).is_file(),
        }
        if extra:
            item.update(extra)
        out.append(item)

    rows = db.query(
        """SELECT t.id, t.result FROM generation_tasks t
           JOIN task_links l ON l.task_id = t.id
           WHERE l.target_kind='shot' AND l.target_id=?
             AND t.task_kind='video_generation' AND t.status='succeeded'
           ORDER BY t.id DESC""",
        (shot_id,),
    )
    for r in rows:
        res = jloads(r.get("result"), {}) or {}
        for f in (res.get("files") or []):
            p = f.get("path")
            if not p or f.get("discarded"):
                continue
            if Path(p).suffix.lower() not in VIDEO_EXTS:
                continue
            push(p, "task", {"task_id": r["id"], "pending": bool(f.get("pending")),
                             "accepted": bool(f.get("accepted"))})

    s = db.query_one(
        """SELECT s.shot_code, e.number AS ep_num, p.video_dir AS video_dir, p.workspace_dir AS ws
           FROM shots s JOIN episodes e ON e.id = s.episode_id
           JOIN projects p ON p.id = e.project_id WHERE s.id=?""",
        (shot_id,),
    )
    if s:
        for nm in naming.keyframe_names(s["shot_code"] or "", s.get("ep_num") or 1):
            stem = Path(nm).stem
            for d in [Path(x) for x in (s.get("video_dir"), s.get("ws")) if x]:
                if not d.is_dir():
                    continue
                cands = [c for c in d.glob(f"{stem}*")
                         if c.is_file() and c.suffix.lower() in VIDEO_EXTS]
                cands.sort(key=lambda c: (0 if c.stem == stem else 1, -c.stat().st_mtime))
                for c in cands:
                    push(str(c.resolve()), "dir")
    return out


def _produced_video_of_shot(shot_id: int) -> str | None:
    """本镜合成该用哪条：① 人工指定的成片 ② 最新任务产物 ③ 目录里按镜号找。

    ① 就是镜头详情页「设为成片」写的 shots.final_video_path —— 以前只写不读、
    合成完全不认它；现在它是最高优先级的显式指定。
    """
    shot = db.query_one("SELECT final_video_path FROM shots WHERE id=?", (shot_id,))
    pinned = ((shot or {}).get("final_video_path") or "").strip()
    if pinned and Path(pinned).is_file():
        return str(Path(pinned))
    for c in _shot_video_candidates(shot_id):
        if c["exists"]:
            return c["path"]
    return None


def _dedupe_clips(episode_id: int) -> int:
    """清掉同一集里完全重复的片段，返回删除条数。

    历史遗留：早期建的无 shot_id 条与 auto-build 补的条同 (file_path, sort_order)
    并存，合成时会把同一镜拼两遍。只删这种成对重复里的多余条（保留带 shot_id 的
    那条），不动任何单独的片段。
    """
    rows = db.query(
        """SELECT * FROM timeline_clips WHERE episode_id=? AND track_type='video'
           ORDER BY id""",
        (episode_id,),
    )
    by_key: dict[tuple, dict] = {}
    drop: list[int] = []
    for r in rows:
        key = (str(r.get("file_path") or "").lower(), r.get("sort_order"))
        prev = by_key.get(key)
        if prev is None:
            by_key[key] = r
            continue
        if r.get("shot_id") and not prev.get("shot_id"):
            keep, kill = r, prev
        else:
            keep, kill = prev, r
        by_key[key] = keep
        drop.append(kill["id"])
    for cid in drop:
        db.execute("DELETE FROM timeline_clips WHERE id=?", (cid,))
    return len(drop)


@router.post("/episodes/{episode_id}/timeline/auto-build")
def auto_build(episode_id: int, body: AutoBuildIn | None = None) -> dict:
    """按镜序扫一遍已出片，落成时间轴。默认只补缺失，不覆盖现有手工调整。"""
    body = body or AutoBuildIn()
    ep = db.query_one("SELECT * FROM episodes WHERE id=?", (episode_id,))
    if not ep:
        raise HTTPException(404, "集不存在")
    shots = db.query("SELECT * FROM shots WHERE episode_id=? ORDER BY sort_order, id", (episode_id,))

    if body.replace:
        db.execute("DELETE FROM timeline_clips WHERE episode_id=? AND track_type='video'", (episode_id,))
        deduped = 0
    else:
        deduped = _dedupe_clips(episode_id)

    # key 只认有 shot_id 的：早期片段 shot_id 为 NULL，若一并塞进 dict 会互相塌缩成
    # 一个 key，导致每个镜头都判定为「不存在」而被重新 INSERT 出一条重复片段。
    existing: dict[int, dict] = {}
    for r in db.query(
        "SELECT * FROM timeline_clips WHERE episode_id=? AND track_type='video' ORDER BY id",
        (episode_id,),
    ):
        sid = r["shot_id"]
        if sid is None:
            continue
        prev = existing.get(sid)
        if prev is None:
            existing[sid] = r
            continue
        if r.get("manual") and not prev.get("manual"):
            existing[sid], kill = r, prev
        else:
            kill = r
        db.execute("DELETE FROM timeline_clips WHERE id=?", (kill["id"],))
        deduped += 1
    order_start = db.query_one(
        "SELECT COALESCE(MAX(sort_order), -1) AS m FROM timeline_clips WHERE episode_id=?",
        (episode_id,),
    )["m"] + 1

    added, updated, missing = 0, 0, []
    for i, s in enumerate(shots):
        path = _produced_video_of_shot(s["id"])
        if not path:
            missing.append(s["shot_code"])
            if not body.include_missing:
                continue
        row = existing.get(s["id"])
        if row:
            db.execute(
                "UPDATE timeline_clips SET file_path=?, sort_order=? WHERE id=?",
                (path, i, row["id"]),
            )
            updated += 1
        else:
            db.execute(
                """INSERT INTO timeline_clips(episode_id, track_type, shot_id, file_path, sort_order,
                       in_sec, out_sec, transition, enabled)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (episode_id, "video", s["id"], path, i, None, None, "cut", 1),
            )
            added += 1

    return {
        "ok": True,
        "added": added,
        "updated": updated,
        "missing": missing,
        "skipped_no_video": len(missing),
        "order_start": order_start,
        "deduped": deduped,
    }


# ---------------- 增删改 ----------------

class ClipIn(BaseModel):
    shot_id: int | None = None
    file_path: str | None = None
    sort_order: int | None = None
    in_sec: float | None = None
    out_sec: float | None = None
    transition: str | None = "cut"
    enabled: bool = True
    note: str | None = None


@router.post("/episodes/{episode_id}/timeline/clips")
def add_clip(episode_id: int, body: ClipIn) -> dict:
    if not db.query_one("SELECT id FROM episodes WHERE id=?", (episode_id,)):
        raise HTTPException(404, "集不存在")
    order = body.sort_order
    if order is None:
        order = db.query_one(
            "SELECT COALESCE(MAX(sort_order), -1) + 1 AS n FROM timeline_clips WHERE episode_id=?",
            (episode_id,),
        )["n"]
    cid = db.execute(
        """INSERT INTO timeline_clips(episode_id, track_type, shot_id, file_path, sort_order,
               in_sec, out_sec, transition, enabled, note)
           VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (episode_id, "video", body.shot_id, body.file_path, order, body.in_sec, body.out_sec,
         body.transition, 1 if body.enabled else 0, body.note),
    )
    return db.query_one("SELECT * FROM timeline_clips WHERE id=?", (cid,))


@router.patch("/timeline/clips/{clip_id}")
def patch_clip(clip_id: int, body: dict) -> dict:
    allowed = {"file_path", "sort_order", "in_sec", "out_sec", "transition", "enabled",
               "note", "shot_id", "manual"}
    vals: dict = {}
    for k, v in body.items():
        if k not in allowed:
            continue
        vals[k] = (1 if v is True else 0 if v is False else v) if k in ("enabled", "manual") else v
    # 手动换了片 → 视为人工指定，合成时优先于自动挑的那条（显式传 manual 以调用方为准）
    if "file_path" in vals and "manual" not in vals:
        vals["manual"] = 1
    if not vals:
        raise HTTPException(400, "无可更新字段")
    cols = ", ".join(f"{k}=?" for k in vals)
    db.execute(f"UPDATE timeline_clips SET {cols} WHERE id=?", list(vals.values()) + [clip_id])
    return db.query_one("SELECT * FROM timeline_clips WHERE id=?", (clip_id,))


@router.delete("/timeline/clips/{clip_id}")
def delete_clip(clip_id: int) -> dict:
    db.execute("DELETE FROM timeline_clips WHERE id=?", (clip_id,))
    return {"ok": True}


@router.post("/episodes/{episode_id}/timeline/reorder")
def reorder(episode_id: int, body: dict) -> dict:
    ids: list[int] = body.get("clip_ids") or []
    for i, cid in enumerate(ids):
        db.execute(
            "UPDATE timeline_clips SET sort_order=? WHERE id=? AND episode_id=?", (i, cid, episode_id)
        )
    return {"ok": True, "count": len(ids)}


# ---------------- 合成 ----------------

class ComposeIn(BaseModel):
    out_path: str | None = None
    reencode: bool = True


@router.post("/episodes/{episode_id}/compose")
def compose(episode_id: int, body: ComposeIn | None = None) -> dict:
    body = body or ComposeIn()
    if not db.query_one("SELECT id FROM episodes WHERE id=?", (episode_id,)):
        raise HTTPException(404, "集不存在")
    enabled = db.query(
        "SELECT id FROM timeline_clips WHERE episode_id=? AND enabled=1 AND track_type='video'",
        (episode_id,),
    )
    if not enabled:
        raise HTTPException(400, "时间轴里没有启用的片段（先点「自动建轴」或手动加片段）")
    tid = task_runner.create_task(
        "compose",
        target_kind="episode",
        target_id=episode_id,
        role="compose",
        payload={"episode_id": episode_id, "out_path": body.out_path, "reencode": body.reencode},
    )
    return {"ok": True, "task_id": tid}


class NormalizeIn(BaseModel):
    path: str


@router.post("/timeline/normalize")
def normalize(body: NormalizeIn) -> dict:
    """把任意规格视频转成全片统一规格（8bit/h264/yuv420p/24fps），不覆盖原文件。"""
    p = Path(body.path)
    if not p.exists():
        raise HTTPException(404, f"文件不存在：{body.path}")
    tid = task_runner.create_task(
        "normalize_8bit", role="normalize", payload={"src": str(p)}
    )
    return {"ok": True, "task_id": tid}


@router.get("/episodes/{episode_id}/compose-candidates")
def compose_candidates(episode_id: int) -> dict:
    """合成前体检：哪些镜有片子、哪些没有，缺的按镜号列出来。"""
    shots = db.query("SELECT * FROM shots WHERE episode_id=? ORDER BY sort_order, id", (episode_id,))
    ok, lack = [], []
    for s in shots:
        path = _produced_video_of_shot(s["id"])
        if path:
            _pv = str(s.get("final_video_path") or "").strip()
            ok.append({"shot_id": s["id"], "shot_code": s["shot_code"], "path": path,
                       "pinned": bool(_pv and os.path.normcase(_pv) == os.path.normcase(path))})
        else:
            lack.append({"shot_id": s["id"], "shot_code": s["shot_code"]})
    # 时间轴里的重复片段会让同一镜被拼多遍，体检必须报出来
    clips = db.query(
        """SELECT id, shot_id, sort_order, file_path FROM timeline_clips
           WHERE episode_id=? AND track_type='video' AND enabled=1
           ORDER BY sort_order, id""",
        (episode_id,),
    )
    seen: dict[tuple, int] = {}
    dupes: list[dict] = []
    for c in clips:
        key = (str(c.get("file_path") or "").lower(), c.get("sort_order"))
        if key in seen:
            dupes.append({"clip_id": c["id"], "keep_clip_id": seen[key],
                          "shot_id": c.get("shot_id"),
                          "name": Path(str(c.get("file_path") or "")).name})
        else:
            seen[key] = c["id"]

    return {"ready": ok, "missing": lack, "ready_count": len(ok), "missing_count": len(lack),
            "clips_count": len(clips), "duplicates": dupes, "duplicate_count": len(dupes)}
