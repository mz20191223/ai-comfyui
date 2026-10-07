"""项目 / 集 / 导入 / 健康报告"""
from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import (
    DEFAULT_DISCARD_DIR,
    DEFAULT_DOC_DIR,
    DEFAULT_REMAKE_DIR,
    DEFAULT_WORKSPACE,
)
from ..core import db
from ..core.db import jloads
from ..parsers import importer
from ..services import file_store, naming

router = APIRouter(prefix="/api", tags=["projects"])


class ProjectIn(BaseModel):
    name: str
    code: str | None = None
    kind: str | None = "micro_drama"
    visual_style: str | None = "live_action"
    genre: str | None = None
    logline: str | None = None
    aspect_ratio: str | None = "9:16"
    fps: int | None = 24
    resolution: str | None = "768x1344"
    workspace_dir: str | None = None
    doc_dir: str | None = None
    ref_dir: str | None = None
    keyframe_dir: str | None = None
    video_dir: str | None = None
    tail_dir: str | None = None
    audio_dir: str | None = None
    discard_dir: str | None = None


def _derive_dirs(ws: str | None, doc: str | None) -> dict:
    workspace = Path(ws) if ws else DEFAULT_WORKSPACE
    remake = workspace / "重制版"
    return {
        "workspace_dir": str(workspace),
        "doc_dir": str(Path(doc) if doc else (workspace / "deepseek分镜")),
        "ref_dir": str(workspace / "角色图"),
        "keyframe_dir": str(remake / "分镜图"),
        "video_dir": str(remake / "分镜视频"),
        "tail_dir": str(remake / "分镜图" / "视频尾帧"),
        "audio_dir": str(remake / "音频"),
        "discard_dir": str(DEFAULT_DISCARD_DIR),
    }


@router.get("/projects")
def list_projects() -> list[dict]:
    rows = db.query("SELECT * FROM projects WHERE archived=0 ORDER BY id DESC")
    for p in rows:
        p["episode_count"] = db.query_one(
            "SELECT COUNT(*) AS c FROM episodes WHERE project_id=?", (p["id"],)
        )["c"]
        p["shot_count"] = db.query_one(
            """SELECT COUNT(*) AS c FROM shots s JOIN episodes e ON e.id=s.episode_id
               WHERE e.project_id=?""",
            (p["id"],),
        )["c"]
    return rows


@router.post("/projects")
def create_project(body: ProjectIn) -> dict:
    dirs = _derive_dirs(body.workspace_dir, body.doc_dir)
    data = body.model_dump()
    data.update({k: v for k, v in dirs.items() if not data.get(k)})
    pid = db.execute(
        """INSERT INTO projects(name, code, kind, visual_style, genre, logline, aspect_ratio, fps,
               resolution, workspace_dir, doc_dir, ref_dir, keyframe_dir, video_dir, tail_dir, audio_dir,
               discard_dir)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            data["name"], data.get("code"), data.get("kind"), data.get("visual_style"),
            data.get("genre"), data.get("logline"), data.get("aspect_ratio"), data.get("fps"),
            data.get("resolution"), data["workspace_dir"], data["doc_dir"], data["ref_dir"],
            data["keyframe_dir"], data["video_dir"], data["tail_dir"], data["audio_dir"],
            data["discard_dir"],
        ),
    )
    return db.query_one("SELECT * FROM projects WHERE id=?", (pid,))


@router.get("/projects/{project_id}")
def get_project(project_id: int) -> dict:
    p = db.query_one("SELECT * FROM projects WHERE id=?", (project_id,))
    if not p:
        raise HTTPException(404, "项目不存在")
    p["episodes"] = db.query(
        "SELECT * FROM episodes WHERE project_id=? ORDER BY number", (project_id,)
    )
    for e in p["episodes"]:
        e["shot_count"] = db.query_one(
            "SELECT COUNT(*) AS c FROM shots WHERE episode_id=?", (e["id"],)
        )["c"]
    return p


@router.patch("/projects/{project_id}")
def update_project(project_id: int, body: dict) -> dict:
    allowed = {
        "name", "code", "kind", "visual_style", "genre", "logline", "aspect_ratio", "fps",
        "resolution", "bit_depth", "codec", "workspace_dir", "doc_dir", "ref_dir",
        "keyframe_dir", "video_dir", "tail_dir", "audio_dir", "discard_dir", "archived", "meta",
    }
    vals = {k: v for k, v in body.items() if k in allowed}
    if not vals:
        raise HTTPException(400, "无可更新字段")
    cols = ", ".join(f"{k}=?" for k in vals)
    db.execute(
        f"UPDATE projects SET {cols}, updated_at=datetime('now','localtime') WHERE id=?",
        list(vals.values()) + [project_id],
    )
    return db.query_one("SELECT * FROM projects WHERE id=?", (project_id,))


@router.delete("/projects/{project_id}")
def delete_project(project_id: int) -> dict:
    db.execute("DELETE FROM projects WHERE id=?", (project_id,))
    return {"ok": True}


# ---------------- 集 ----------------

@router.get("/projects/{project_id}/episodes")
def list_episodes(project_id: int) -> list[dict]:
    rows = db.query("SELECT * FROM episodes WHERE project_id=? ORDER BY number", (project_id,))
    for e in rows:
        e["shot_count"] = db.query_one(
            "SELECT COUNT(*) AS c FROM shots WHERE episode_id=?", (e["id"],)
        )["c"]
    return rows


class EpisodeIn(BaseModel):
    number: int
    title: str | None = None
    synopsis: str | None = None
    script_text: str | None = None


@router.post("/projects/{project_id}/episodes")
def create_episode(project_id: int, body: EpisodeIn) -> dict:
    eid = db.execute(
        "INSERT INTO episodes(project_id, number, title, synopsis, script_text) VALUES(?,?,?,?,?)",
        (project_id, body.number, body.title, body.synopsis, body.script_text),
    )
    return db.query_one("SELECT * FROM episodes WHERE id=?", (eid,))


@router.patch("/episodes/{episode_id}")
def update_episode(episode_id: int, body: dict) -> dict:
    allowed = {"number", "title", "synopsis", "script_text", "video_doc_path", "storyboard_doc_path", "status"}
    vals = {k: v for k, v in body.items() if k in allowed}
    if not vals:
        raise HTTPException(400, "无可更新字段")
    cols = ", ".join(f"{k}=?" for k in vals)
    db.execute(
        f"UPDATE episodes SET {cols}, updated_at=datetime('now','localtime') WHERE id=?",
        list(vals.values()) + [episode_id],
    )
    return db.query_one("SELECT * FROM episodes WHERE id=?", (episode_id,))


@router.get("/episodes/{episode_id}")
def get_episode(episode_id: int) -> dict:
    e = db.query_one("SELECT * FROM episodes WHERE id=?", (episode_id,))
    if not e:
        raise HTTPException(404, "集不存在")
    e["project"] = db.query_one("SELECT * FROM projects WHERE id=?", (e["project_id"],))
    return e


# ---------------- 导入 ----------------

EP_DOC_RE = re.compile(r"第\s*(\d+)\s*集")


def _discover_docs(doc_dir: Path) -> dict[int, dict]:
    """在文档目录里发现「第N集」的核对版与分镜图文档。"""
    found: dict[int, dict] = {}
    if not doc_dir.exists():
        return found
    for f in sorted(doc_dir.glob("*.md")):
        m = EP_DOC_RE.search(f.name)
        if not m:
            continue
        num = int(m.group(1))
        item = found.setdefault(num, {})
        if "核对版" in f.name or "中文视频提示词" in f.name:
            item["video_doc"] = f
        elif "分镜图" in f.name:
            item["storyboard_doc"] = f
        else:
            item.setdefault("other", []).append(f)
    return found


@router.get("/projects/{project_id}/discover")
def discover_documents(project_id: int) -> dict:
    p = db.query_one("SELECT * FROM projects WHERE id=?", (project_id,))
    if not p:
        raise HTTPException(404, "项目不存在")
    doc_dir = Path(p.get("doc_dir") or DEFAULT_DOC_DIR)
    found = _discover_docs(doc_dir)
    return {
        "doc_dir": str(doc_dir),
        "exists": doc_dir.exists(),
        "episodes": [
            {
                "number": n,
                "video_doc": str(v.get("video_doc")) if v.get("video_doc") else None,
                "storyboard_doc": str(v.get("storyboard_doc")) if v.get("storyboard_doc") else None,
            }
            for n, v in sorted(found.items())
        ],
    }


class ImportIn(BaseModel):
    episode_number: int | None = None
    video_doc_path: str | None = None
    storyboard_doc_path: str | None = None
    rebuild: bool = False


@router.post("/projects/{project_id}/import")
def import_docs(project_id: int, body: ImportIn) -> dict:
    p = db.query_one("SELECT * FROM projects WHERE id=?", (project_id,))
    if not p:
        raise HTTPException(404, "项目不存在")
    doc_dir = Path(p.get("doc_dir") or DEFAULT_DOC_DIR)
    results = []

    if body.video_doc_path:
        targets = [(body.episode_number or naming.episode_from_filename(Path(body.video_doc_path).name) or 1,
                    Path(body.video_doc_path), Path(body.storyboard_doc_path) if body.storyboard_doc_path else None)]
    else:
        found = _discover_docs(doc_dir)
        if body.episode_number:
            found = {body.episode_number: found.get(body.episode_number, {})}
        targets = [
            (n, v.get("video_doc"), v.get("storyboard_doc")) for n, v in sorted(found.items())
        ]

    if not targets:
        raise HTTPException(400, f"在 {doc_dir} 未发现可导入的文档")

    for num, vdoc, sdoc in targets:
        if not vdoc:
            results.append({"episode": num, "ok": False, "error": "缺核对版文档"})
            continue
        try:
            r = importer.import_episode(
                project_id, num, vdoc, sdoc, rebuild=body.rebuild
            )
            results.append({"episode": num, "ok": True, **r.to_dict()})
        except Exception as e:  # noqa: BLE001
            results.append({"episode": num, "ok": False, "error": str(e)})
    _ensure_project_dirs(p)
    return {"results": results, "count": len(results)}


def _ensure_project_dirs(p: dict) -> None:
    for k in ("keyframe_dir", "video_dir", "tail_dir", "audio_dir", "discard_dir"):
        v = p.get(k)
        if v:
            try:
                Path(v).mkdir(parents=True, exist_ok=True)
            except OSError:
                pass


# ---------------- 健康报告 ----------------

@router.get("/projects/{project_id}/health")
def project_health(project_id: int, resolved: int = 0) -> dict:
    rows = db.query(
        """SELECT h.*, s.shot_code, e.number AS episode_number FROM health_issues h
           LEFT JOIN shots s ON s.id = h.shot_id
           LEFT JOIN episodes e ON e.id = h.episode_id
           WHERE h.project_id=? AND h.resolved=? ORDER BY
             CASE h.severity WHEN 'error' THEN 0 WHEN 'warn' THEN 1 ELSE 2 END, h.id""",
        (project_id, resolved),
    )
    by_type: dict[str, int] = {}
    by_sev: dict[str, int] = {}
    for r in rows:
        by_type[r["issue_type"]] = by_type.get(r["issue_type"], 0) + 1
        by_sev[r["severity"]] = by_sev.get(r["severity"], 0) + 1
    return {"issues": rows, "by_type": by_type, "by_severity": by_sev, "total": len(rows)}


@router.post("/health/{issue_id}/resolve")
def resolve_issue(issue_id: int) -> dict:
    db.execute("UPDATE health_issues SET resolved=1 WHERE id=?", (issue_id,))
    return {"ok": True}


@router.post("/projects/{project_id}/rescan")
def rescan(project_id: int) -> dict:
    """重新解析全部已导入集（不改文档，只刷新库内索引）。"""
    p = db.query_one("SELECT * FROM projects WHERE id=?", (project_id,))
    if not p:
        raise HTTPException(404, "项目不存在")
    eps = db.query("SELECT * FROM episodes WHERE project_id=? ORDER BY number", (project_id,))
    out = []
    for e in eps:
        if not e.get("video_doc_path") or not Path(e["video_doc_path"]).exists():
            out.append({"episode": e["number"], "ok": False, "error": "文档不存在"})
            continue
        try:
            r = importer.import_episode(
                project_id, e["number"], e["video_doc_path"], e.get("storyboard_doc_path"),
                rebuild=True,
            )
            out.append({"episode": e["number"], "ok": True, **r.to_dict()})
        except Exception as ex:  # noqa: BLE001
            out.append({"episode": e["number"], "ok": False, "error": str(ex)})
    return {"results": out}


# ---------------- 概览看板 ----------------

@router.get("/projects/{project_id}/overview")
def overview(project_id: int) -> dict:
    eps = db.query("SELECT * FROM episodes WHERE project_id=? ORDER BY number", (project_id,))
    total_shots = total_dur = 0.0
    ep_stats = []
    for e in eps:
        shots = db.query("SELECT id FROM shots WHERE episode_id=?", (e["id"],))
        dur = db.query_one(
            """SELECT SUM(d.duration_sec) AS s FROM shot_details d
               JOIN shots sh ON sh.id=d.shot_id WHERE sh.episode_id=?""",
            (e["id"],),
        )["s"] or 0
        running = db.query_one(
            """SELECT COUNT(DISTINCT t.id) AS c FROM generation_tasks t
               JOIN task_links l ON l.task_id=t.id
               JOIN shots s ON s.id=l.target_id AND l.target_kind='shot'
               WHERE s.episode_id=? AND t.status IN ('submitted','running')""",
            (e["id"],),
        )["c"]
        produced = db.query_one(
            """SELECT COUNT(DISTINCT s.id) AS c FROM shots s
               JOIN task_links l ON l.target_kind='shot' AND l.target_id=s.id
               JOIN generation_tasks t ON t.id=l.task_id AND t.task_kind='video_generation'
                    AND t.status='succeeded'
               WHERE s.episode_id=?""",
            (e["id"],),
        )["c"]
        ep_stats.append({
            "episode_id": e["id"],
            "number": e["number"],
            "title": e["title"],
            "shots": len(shots),
            "producing": running,
            "produced": produced,
            "duration_sec": round(dur, 2),
        })
        total_shots += len(shots)
        total_dur += dur
    issues = db.query_one(
        "SELECT COUNT(*) AS c FROM health_issues WHERE project_id=? AND resolved=0", (project_id,)
    )["c"]
    return {
        "project_id": project_id,
        "episodes": ep_stats,
        "total_shots": total_shots,
        "total_duration_sec": round(total_dur, 2),
        "open_issues": issues,
    }
