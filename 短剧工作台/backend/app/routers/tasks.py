"""任务中心：查询 / 取消 / 重试 / 进度流"""
from __future__ import annotations

import json
import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..core import db
from ..core.db import jloads
from ..executors import task_runner

router = APIRouter(prefix="/api", tags=["tasks"])


@router.get("/tasks")
def list_tasks(
    status: str | None = None,
    task_kind: str | None = None,
    project_id: int | None = None,
    limit: int = 100,
) -> list[dict]:
    sql = """SELECT t.*, p.name AS provider_name, m.name AS model_name
             FROM generation_tasks t
             LEFT JOIN providers p ON p.id = t.provider_id
             LEFT JOIN models m ON m.id = t.model_id
             WHERE 1=1"""
    params: list = []
    if status:
        sql += " AND t.status=?"
        params.append(status)
    if task_kind:
        sql += " AND t.task_kind=?"
        params.append(task_kind)
    if project_id:
        sql += """ AND t.id IN (
                    SELECT l.task_id FROM task_links l
                    JOIN shots s ON s.id=l.target_id AND l.target_kind='shot'
                    JOIN episodes e ON e.id=s.episode_id
                    WHERE e.project_id=?)"""
        params.append(project_id)
    sql += " ORDER BY t.id DESC LIMIT ?"
    params.append(limit)
    rows = db.query(sql, params)
    pmap = {p["id"]: p["name"] for p in db.query("SELECT id, name FROM projects")}
    for r in rows:
        links = db.query("SELECT * FROM task_links WHERE task_id=?", (r["id"],))
        r["links"] = links
        shot = next((l for l in links if l["target_kind"] == "shot"), None)
        s = None
        if shot:
            s = db.query_one(
                """SELECT s.shot_code, s.id, e.number AS episode_number, e.id AS episode_id,
                          e.project_id FROM shots s JOIN episodes e ON e.id=s.episode_id WHERE s.id=?""",
                (shot["target_id"],),
            )
            r["shot"] = s
        # 任务归属项目（列表默认跨项目，靠这列才看得出是哪个项目的事）
        r["project_name"] = pmap.get(s["project_id"]) if s else None
        res = jloads(r.get("result"), {}) or {}
        r["note"] = res.get("note")
        r["output_files"] = [f.get("path") for f in (res.get("files") or [])]
    return rows


@router.get("/tasks/stats")
def task_stats() -> dict:
    rows = db.query("SELECT status, COUNT(*) AS c FROM generation_tasks GROUP BY status")
    kinds = db.query("SELECT task_kind, status, COUNT(*) AS c FROM generation_tasks GROUP BY task_kind, status")
    return {
        "by_status": {r["status"]: r["c"] for r in rows},
        "by_kind": [
            {"task_kind": r["task_kind"], "status": r["status"], "count": r["c"]} for r in kinds
        ],
        "running": db.query_one(
            "SELECT COUNT(*) AS c FROM generation_tasks WHERE status IN ('submitted','running')"
        )["c"],
    }


@router.get("/tasks/{task_id}")
def get_task(task_id: int) -> dict:
    t = db.query_one(
        """SELECT t.*, p.name AS provider_name, m.name AS model_name, m.category AS model_category
           FROM generation_tasks t
           LEFT JOIN providers p ON p.id=t.provider_id
           LEFT JOIN models m ON m.id=t.model_id WHERE t.id=?""",
        (task_id,),
    )
    if not t:
        raise HTTPException(404, "任务不存在")
    t["links"] = db.query("SELECT * FROM task_links WHERE task_id=?", (task_id,))
    t["payload_json"] = jloads(t.get("payload"), {}) or {}
    t["result_json"] = jloads(t.get("result"), {}) or {}
    return t


@router.post("/tasks/{task_id}/cancel")
def cancel(task_id: int, body: dict | None = None) -> dict:
    ok = task_runner.cancel_task(task_id, (body or {}).get("reason", ""))
    if not ok:
        raise HTTPException(400, "该任务已结束，无法取消")
    return {"ok": True}


@router.post("/tasks/{task_id}/retry")
def retry(task_id: int) -> dict:
    new_id = task_runner.retry_task(task_id)
    return {"ok": True, "task_id": new_id}


@router.delete("/tasks/{task_id}")
def delete_task(task_id: int) -> dict:
    db.execute("DELETE FROM generation_tasks WHERE id=?", (task_id,))
    return {"ok": True}


@router.post("/tasks/clear-finished")
def clear_finished(body: dict | None = None) -> dict:
    keep = (body or {}).get("statuses") or ["succeeded", "cancelled"]
    ph = ", ".join("?" for _ in keep)
    n = db.execute(f"DELETE FROM generation_tasks WHERE status IN ({ph})", keep)
    return {"ok": True, "deleted": n}


class SubmitIn(BaseModel):
    task_kind: str
    shot_id: int | None = None
    model_id: int | None = None
    overrides: dict | None = None
    payload: dict | None = None


@router.post("/tasks")
def submit_task(body: SubmitIn) -> dict:
    if body.task_kind in ("image_generation", "video_generation") and body.shot_id:
        if body.task_kind == "video_generation":
            params = task_runner.build_video_params(body.shot_id, body.overrides)
        else:
            params = task_runner.build_image_params(body.shot_id, body.overrides)
        params["model_id"] = body.model_id
        role = {"video_generation": "video", "image_generation": "keyframe"}[body.task_kind]
        tid = task_runner.create_task(
            body.task_kind, target_kind="shot", target_id=body.shot_id, role=role,
            payload=params, model_id=body.model_id,
        )
    else:
        tid = task_runner.create_task(
            body.task_kind, payload=body.payload or {}, target_kind="shot", target_id=body.shot_id,
        )
    return {"ok": True, "task_id": tid}


@router.get("/tasks-stream")
def stream(ids: str) -> StreamingResponse:
    """SSE：按任务 id 列表（逗号分隔）持续推送状态。"""
    task_ids = [int(x) for x in ids.split(",") if x.strip().isdigit()]

    def gen():
        deadline = time.time() + 1800
        while time.time() < deadline:
            rows = []
            for tid in task_ids:
                t = db.query_one(
                    "SELECT id, status, progress, error, task_kind, result FROM generation_tasks WHERE id=?",
                    (tid,),
                )
                if t:
                    res = jloads(t.get("result"), {}) or {}
                    rows.append({
                        "id": t["id"], "status": t["status"], "progress": t["progress"],
                        "error": t["error"], "task_kind": t["task_kind"], "note": res.get("note"),
                    })
            yield f"data: {json.dumps({'tasks': rows}, ensure_ascii=False)}\n\n"
            if rows and all(r["status"] in ("succeeded", "failed", "cancelled") for r in rows):
                break
            time.sleep(1.5)

    return StreamingResponse(gen(), media_type="text/event-stream")
