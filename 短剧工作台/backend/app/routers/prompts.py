"""提示词中心：模板 / 片段 / 版本历史 / Lint 规则"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..core import db
from ..core.db import jdumps, jloads
from ..executors import provider_engine as PE

router = APIRouter(prefix="/api", tags=["prompts"])

TEMPLATE_CATEGORIES = [
    {"value": "video_prefix", "label": "视频首行（模式声明）"},
    {"value": "video_body", "label": "视频正文骨架"},
    {"value": "keyframe_image", "label": "分镜图提示词骨架"},
    {"value": "character_image", "label": "角色参考图提示词"},
    {"value": "scene_image", "label": "场景参考图提示词"},
    {"value": "prop_image", "label": "道具参考图提示词"},
    {"value": "negative_base", "label": "通用负向词"},
    {"value": "tts_script", "label": "配音文本处理"},
]


def _scope(project_id: int | None) -> tuple[str, list]:
    if project_id:
        return "(project_id IS NULL OR project_id=?)", [project_id]
    return "project_id IS NULL", []


@router.get("/templates")
def list_templates(project_id: int | None = None, category: str | None = None) -> list[dict]:
    where, params = _scope(project_id)
    sql = f"SELECT * FROM prompt_templates WHERE {where}"
    if category:
        sql += " AND category=?"
        params.append(category)
    sql += " ORDER BY category, sort_order, id"
    rows = db.query(sql, params)
    for r in rows:
        r["var_list"] = jloads(r.get("variables"), []) or []
    return rows


@router.get("/template-categories")
def template_categories() -> list[dict]:
    return TEMPLATE_CATEGORIES


class TemplateIn(BaseModel):
    project_id: int | None = None
    category: str
    name: str
    description: str | None = None
    content: str
    variables: list[dict] | None = None
    is_default: bool = False


@router.post("/templates")
def create_template(body: TemplateIn) -> dict:
    tid = db.execute(
        """INSERT INTO prompt_templates(project_id, category, name, description, content, variables, is_default)
           VALUES(?,?,?,?,?,?,?)""",
        (body.project_id, body.category, body.name, body.description, body.content,
         jdumps(body.variables or []), 1 if body.is_default else 0),
    )
    return db.query_one("SELECT * FROM prompt_templates WHERE id=?", (tid,))


@router.patch("/templates/{template_id}")
def patch_template(template_id: int, body: dict) -> dict:
    allowed = {"name", "description", "content", "variables", "is_default", "is_system", "sort_order", "category"}
    vals = {}
    for k, v in body.items():
        if k not in allowed:
            continue
        vals[k] = jdumps(v) if k == "variables" and not isinstance(v, str) else v
    if not vals:
        raise HTTPException(400, "无可更新字段")
    cols = ", ".join(f"{k}=?" for k in vals)
    db.execute(
        f"UPDATE prompt_templates SET {cols}, updated_at=datetime('now','localtime') WHERE id=?",
        list(vals.values()) + [template_id],
    )
    return db.query_one("SELECT * FROM prompt_templates WHERE id=?", (template_id,))


@router.post("/templates/{template_id}/duplicate")
def duplicate_template(template_id: int) -> dict:
    t = db.query_one("SELECT * FROM prompt_templates WHERE id=?", (template_id,))
    if not t:
        raise HTTPException(404, "模板不存在")
    tid = db.execute(
        """INSERT INTO prompt_templates(project_id, category, name, description, content, variables)
           VALUES(?,?,?,?,?,?)""",
        (t["project_id"], t["category"], f"{t['name']} 副本", t["description"], t["content"], t["variables"]),
    )
    return db.query_one("SELECT * FROM prompt_templates WHERE id=?", (tid,))


@router.delete("/templates/{template_id}")
def delete_template(template_id: int) -> dict:
    t = db.query_one("SELECT * FROM prompt_templates WHERE id=?", (template_id,))
    if t and t["is_system"]:
        raise HTTPException(400, "系统模板不可删除，可复制后修改")
    db.execute("DELETE FROM prompt_templates WHERE id=?", (template_id,))
    return {"ok": True}


class RenderIn(BaseModel):
    variables: dict


@router.post("/templates/{template_id}/render")
def render_template(template_id: int, body: RenderIn) -> dict:
    t = db.query_one("SELECT * FROM prompt_templates WHERE id=?", (template_id,))
    if not t:
        raise HTTPException(404, "模板不存在")
    try:
        out = PE.render_text(t["content"], body.variables)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, f"模板渲染失败：{e}") from e
    return {"output": out}


# ---------------- 片段 ----------------

@router.get("/snippets")
def list_snippets(project_id: int | None = None) -> list[dict]:
    where, params = _scope(project_id)
    rows = db.query(f"SELECT * FROM prompt_snippets WHERE {where} ORDER BY sort_order, id", params)
    for r in rows:
        r["auto"] = jloads(r.get("auto_apply"), {}) or {}
    return rows


class SnippetIn(BaseModel):
    project_id: int | None = None
    key: str
    label: str
    content: str
    category: str | None = "guard"
    auto_apply: dict | None = None


@router.post("/snippets")
def create_snippet(body: SnippetIn) -> dict:
    sid = db.execute(
        """INSERT INTO prompt_snippets(project_id, key, label, content, category, auto_apply)
           VALUES(?,?,?,?,?,?)""",
        (body.project_id, body.key, body.label, body.content, body.category,
         jdumps(body.auto_apply) if body.auto_apply else None),
    )
    return db.query_one("SELECT * FROM prompt_snippets WHERE id=?", (sid,))


@router.patch("/snippets/{snippet_id}")
def patch_snippet(snippet_id: int, body: dict) -> dict:
    allowed = {"label", "content", "category", "auto_apply", "sort_order"}
    vals = {}
    for k, v in body.items():
        if k not in allowed:
            continue
        vals[k] = jdumps(v) if k == "auto_apply" and not isinstance(v, str) else v
    if not vals:
        raise HTTPException(400, "无可更新字段")
    cols = ", ".join(f"{k}=?" for k in vals)
    db.execute(f"UPDATE prompt_snippets SET {cols} WHERE id=?", list(vals.values()) + [snippet_id])
    return db.query_one("SELECT * FROM prompt_snippets WHERE id=?", (snippet_id,))


@router.delete("/snippets/{snippet_id}")
def delete_snippet(snippet_id: int) -> dict:
    db.execute("DELETE FROM prompt_snippets WHERE id=?", (snippet_id,))
    return {"ok": True}


# ---------------- 版本历史 ----------------

@router.get("/revisions")
def list_revisions(target_kind: str, target_id: int, limit: int = 50) -> list[dict]:
    return db.query(
        """SELECT id, target_kind, target_id, note, source, created_at, length(content) AS size
           FROM prompt_revisions WHERE target_kind=? AND target_id=? ORDER BY id DESC LIMIT ?""",
        (target_kind, target_id, limit),
    )


@router.get("/revisions/{revision_id}")
def get_revision(revision_id: int) -> dict:
    r = db.query_one("SELECT * FROM prompt_revisions WHERE id=?", (revision_id,))
    if not r:
        raise HTTPException(404, "版本不存在")
    return r


@router.post("/revisions/{revision_id}/restore")
def restore_revision(revision_id: int) -> dict:
    r = db.query_one("SELECT * FROM prompt_revisions WHERE id=?", (revision_id,))
    if not r:
        raise HTTPException(404, "版本不存在")
    kind, tid, content = r["target_kind"], r["target_id"], r["content"]
    if kind == "shot_video":
        db.execute("UPDATE shot_details SET video_prompt=? WHERE shot_id=?", (content, tid))
    elif kind == "shot_image":
        db.execute("UPDATE shot_details SET image_prompt=? WHERE shot_id=?", (content, tid))
    elif kind == "template":
        db.execute("UPDATE prompt_templates SET content=? WHERE id=?", (content, tid))
    else:
        raise HTTPException(400, f"该类型暂不支持回滚：{kind}")
    db.execute(
        "INSERT INTO prompt_revisions(target_kind, target_id, content, note, source) VALUES(?,?,?,?,?)",
        (kind, tid, content, f"回滚自版本 {revision_id}", "restore"),
    )
    return {"ok": True, "restored": revision_id}


# ---------------- Lint 规则 ----------------

@router.get("/lint-rules")
def list_rules(project_id: int | None = None) -> list[dict]:
    where, params = _scope(project_id)
    rows = db.query(f"SELECT * FROM lint_rules WHERE {where} ORDER BY sort_order, id", params)
    for r in rows:
        r["cfg"] = jloads(r.get("config"), {}) or {}
    return rows


@router.patch("/lint-rules/{rule_id}")
def patch_rule(rule_id: int, body: dict) -> dict:
    allowed = {"label", "description", "stage", "severity", "config", "enabled", "sort_order"}
    vals = {}
    for k, v in body.items():
        if k not in allowed:
            continue
        vals[k] = jdumps(v) if k == "config" and not isinstance(v, str) else v
    if not vals:
        raise HTTPException(400, "无可更新字段")
    cols = ", ".join(f"{k}=?" for k in vals)
    db.execute(f"UPDATE lint_rules SET {cols} WHERE id=?", list(vals.values()) + [rule_id])
    return db.query_one("SELECT * FROM lint_rules WHERE id=?", (rule_id,))


@router.post("/lint-rules")
def create_rule(body: dict) -> dict:
    rid = db.execute(
        """INSERT INTO lint_rules(project_id, key, label, description, stage, severity, checker, config, enabled)
           VALUES(?,?,?,?,?,?,?,?,?)""",
        (body.get("project_id"), body.get("key"), body.get("label"), body.get("description"),
         body.get("stage", "video"), body.get("severity", "warn"), body.get("checker", "keyword_blacklist"),
         jdumps(body.get("config") or {}), body.get("enabled", 1)),
    )
    return db.query_one("SELECT * FROM lint_rules WHERE id=?", (rid,))


@router.get("/lint-checkers")
def lint_checkers() -> list[dict]:
    return [
        {"value": "keyword_blacklist", "label": "关键词黑名单"},
        {"value": "require_phrase", "label": "必需语句"},
        {"value": "dialogue_format", "label": "台词格式"},
        {"value": "ref_blacklist", "label": "参考素材黑名单"},
        {"value": "duration_check", "label": "时长校验"},
        {"value": "subject_scope", "label": "主体越界"},
        {"value": "file_exists", "label": "文件存在性"},
        {"value": "internal_code", "label": "内部代号"},
        {"value": "decl_consistency", "label": "声明与参数一致"},
        {"value": "placeholder_ref", "label": "占位引用"},
    ]
