"""创作层：从 0 建剧 —— 创意 → 剧本 → 拆镜 → 资产 → 双份提示词

设计目标：下部剧不用改代码，只要新建项目 + 建资产 + 贴剧本，就能长出镜头与提示词槽位。
"""
from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..core import db
from ..core.db import jdumps, jloads
from ..services import file_store

router = APIRouter(prefix="/api/creation", tags=["creation"])

SCRIPT_SHOT_RE = re.compile(r"^#{2,4}\s*镜头\s*(?P<code>[0-9]+[A-Za-z]?(?:-\d+)?)\s*(?P<rest>.*)$")
SUB_HEAD_RE = re.compile(r"^#{3,5}\s*(?P<title>.+?)\s*$")
QUOTE_RE = re.compile(r"^>\s?(?P<content>.*)$")


# ---------------- 创意 ----------------

@router.get("/ideas")
def list_ideas(project_id: int | None = None) -> list[dict]:
    if project_id:
        return db.query("SELECT * FROM creative_ideas WHERE project_id=? ORDER BY id DESC", (project_id,))
    return db.query("SELECT * FROM creative_ideas ORDER BY id DESC")


class IdeaIn(BaseModel):
    project_id: int | None = None
    title: str | None = None
    one_liner: str | None = None
    story_text: str | None = None
    beats: list[dict] | None = None
    characters_json: list[dict] | None = None
    scenes_json: list[dict] | None = None
    status: str | None = "idea"


@router.post("/ideas")
def create_idea(body: IdeaIn) -> dict:
    iid = db.execute(
        """INSERT INTO creative_ideas(project_id, title, one_liner, story_text, beats,
               characters_json, scenes_json, status)
           VALUES(?,?,?,?,?,?,?,?)""",
        (body.project_id, body.title, body.one_liner, body.story_text,
         jdumps(body.beats), jdumps(body.characters_json), jdumps(body.scenes_json), body.status),
    )
    return db.query_one("SELECT * FROM creative_ideas WHERE id=?", (iid,))


@router.patch("/ideas/{idea_id}")
def patch_idea(idea_id: int, body: dict) -> dict:
    allowed = {"title", "one_liner", "story_text", "beats", "characters_json", "scenes_json", "status", "project_id"}
    vals = {}
    for k, v in body.items():
        if k not in allowed:
            continue
        vals[k] = jdumps(v) if k in ("beats", "characters_json", "scenes_json") and not isinstance(v, str) else v
    if not vals:
        raise HTTPException(400, "无可更新字段")
    cols = ", ".join(f"{k}=?" for k in vals)
    db.execute(
        f"UPDATE creative_ideas SET {cols}, updated_at=datetime('now','localtime') WHERE id=?",
        list(vals.values()) + [idea_id],
    )
    return db.query_one("SELECT * FROM creative_ideas WHERE id=?", (idea_id,))


@router.delete("/ideas/{idea_id}")
def delete_idea(idea_id: int) -> dict:
    db.execute("DELETE FROM creative_ideas WHERE id=?", (idea_id,))
    return {"ok": True}


# ---------------- 剧本解析：拆镜 ----------------

def parse_script(text: str) -> list[dict]:
    """把剧本 md 拆成镜头草稿。

    兼容两种写法：
    A) ## 镜头14d  +  ### 分镜图提示词 / ### 分镜视频提示词
    B) ## 镜头6a   +  正文直接是提示词
    """
    lines = text.splitlines()
    shots: list[dict] = []
    cur: dict | None = None
    section = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal buf, section
        if cur is not None and section and buf:
            body = _clean_quote(buf)
            if section == "image":
                cur["image_prompt"] = (cur.get("image_prompt") or "") + ("\n\n" if cur.get("image_prompt") else "") + body
            elif section == "video":
                cur["video_prompt"] = (cur.get("video_prompt") or "") + ("\n\n" if cur.get("video_prompt") else "") + body
            elif section == "video_en":
                cur["video_prompt_en"] = (cur.get("video_prompt_en") or "") + ("\n\n" if cur.get("video_prompt_en") else "") + body
            elif section == "body":
                cur["script_excerpt"] = (cur.get("script_excerpt") or "") + ("\n" if cur.get("script_excerpt") else "") + body
        buf = []

    for ln in lines:
        m = SCRIPT_SHOT_RE.match(ln)
        if m:
            flush()
            if cur:
                shots.append(cur)
            code = m.group("code")
            cur = {
                "shot_code": code,
                "title": (m.group("rest") or "").strip("｜| "),
                "image_prompt": None,
                "video_prompt": None,
                "video_prompt_en": None,
                "script_excerpt": None,
                "gen_mode": None,
                "duration_sec": None,
            }
            section = None
            continue
        if cur is None:
            continue
        sub = SUB_HEAD_RE.match(ln)
        if sub:
            flush()
            t = sub.group("title")
            if "分镜图" in t:
                section = "image"
            elif "视频提示词" in t and ("英文" in t or "English" in t):
                section = "video_en"
            elif "视频提示词" in t or "分镜视频" in t:
                section = "video"
                cur["gen_mode"] = _mode_from_text(t) or cur["gen_mode"]
                dur = re.search(r"(\d+(?:\.\d+)?)\s*秒", t)
                if dur:
                    cur["duration_sec"] = float(dur.group(1))
            else:
                section = "body"
            continue
        if section:
            buf.append(ln)

    flush()
    if cur:
        shots.append(cur)
    return [s for s in shots if s["shot_code"]]


def _clean_quote(lines: list[str]) -> str:
    out = []
    for ln in lines:
        s = ln.rstrip()
        q = QUOTE_RE.match(s)
        if q:
            out.append(q.group("content"))
        elif s.strip() == "" and out and out[-1] == "":
            continue
        else:
            out.append(s)
    return "\n".join(out).strip()


def _mode_from_text(t: str) -> str | None:
    for m in ("FL2VA", "I2VA", "REF2VA", "T2V", "I2V"):
        if m.lower() in t.lower():
            return m
    return None


class SplitIn(BaseModel):
    script_text: str | None = None
    script_path: str | None = None
    replace: bool = False
    create_assets: bool = True


@router.post("/episodes/{episode_id}/split")
def split_script(episode_id: int, body: SplitIn) -> dict:
    ep = db.query_one("SELECT * FROM episodes WHERE id=?", (episode_id,))
    if not ep:
        raise HTTPException(404, "集不存在")
    text = body.script_text
    if not text and body.script_path:
        p = Path(body.script_path)
        if not p.exists():
            raise HTTPException(404, f"剧本文件不存在：{p}")
        text = p.read_text(encoding="utf-8", errors="ignore")
        db.execute("UPDATE episodes SET script_text=? WHERE id=?", (text, episode_id))
    if not text:
        text = ep.get("script_text")
    if not text:
        raise HTTPException(400, "请提供剧本内容或剧本文件路径")

    drafts = parse_script(text)
    if not drafts:
        raise HTTPException(400, "未能从剧本里识别出镜头（需形如「## 镜头1」的标题）")

    if body.replace:
        db.execute("DELETE FROM shots WHERE episode_id=?", (episode_id,))

    created, updated = 0, 0
    for i, d in enumerate(drafts):
        code = d["shot_code"]
        exists = db.query_one("SELECT id FROM shots WHERE episode_id=? AND shot_code=?", (episode_id, code))
        vals = dict(
            video_prompt=d.get("video_prompt"),
            image_prompt=d.get("image_prompt"),
            gen_mode=d.get("gen_mode"),
            duration_sec=d.get("duration_sec"),
        )
        if exists:
            sid = exists["id"]
            db.execute("UPDATE shots SET title=?, sort_order=?, script_excerpt=? WHERE id=?",
                       (d.get("title") or None, i, d.get("script_excerpt"), sid))
            cols = ", ".join(f"{k}=?" for k in vals)
            db.execute(f"UPDATE shot_details SET {cols}, updated_at=datetime('now','localtime') WHERE shot_id=?",
                       list(vals.values()) + [sid])
            updated += 1
        else:
            sid = db.execute(
                """INSERT INTO shots(episode_id, shot_code, title, sort_order, script_excerpt)
                   VALUES(?,?,?,?,?)""",
                (episode_id, code, d.get("title") or None, i, d.get("script_excerpt")),
            )
            cols = ", ".join(vals.keys())
            ph = ", ".join("?" for _ in vals)
            db.execute(f"INSERT INTO shot_details(shot_id, {cols}) VALUES(?, {ph})",
                       [sid] + list(vals.values()))
            created += 1
        # 参考图槽位：从提示词里自动抽取「参考图N（xxx）」
        _auto_refs(ep["project_id"], sid, d)

    assets_created = 0
    if body.create_assets:
        assets_created = _assets_from_script(ep["project_id"], text)

    return {
        "ok": True,
        "shots_total": len(drafts),
        "created": created,
        "updated": updated,
        "assets_created": assets_created,
        "shots": [d["shot_code"] for d in drafts],
    }


REF_MENTION_RE = re.compile(r"参考图\s*(\d+)\s*[（(](?P<name>[^）)]+)[）)]")


def _auto_refs(project_id: int, shot_id: int, draft: dict) -> None:
    text = "\n".join(filter(None, [draft.get("image_prompt"), draft.get("video_prompt")]))
    found: list[tuple[int, str]] = []
    for m in REF_MENTION_RE.finditer(text):
        found.append((int(m.group(1)), m.group("name").strip()))
    if not found:
        return
    db.execute("DELETE FROM shot_asset_links WHERE shot_id=? AND target_side='image'", (shot_id,))
    project = db.query_one("SELECT * FROM projects WHERE id=?", (project_id,))
    for idx, name in sorted(found):
        asset = _match_asset(project_id, name)
        fname = None
        if asset:
            img = db.query_one(
                "SELECT * FROM asset_images WHERE asset_id=? ORDER BY is_primary DESC, id LIMIT 1",
                (asset["id"],),
            )
            fname = img["file_name"] if img else None
        if not fname:
            fname = _guess_ref_file(name)
        real = file_store.resolve(fname, project) if fname else None
        db.execute(
            """INSERT OR REPLACE INTO shot_asset_links(shot_id, asset_id, role, slot_index,
                   target_side, ref_version, take_note, file_name, raw_text)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (shot_id, asset["id"] if asset else None, "参考图", idx, "image",
             "concept" if asset else None, name, fname, f"参考图{idx}（{name}）"),
        )


def _match_asset(project_id: int, name: str) -> dict | None:
    rows = db.query("SELECT * FROM assets WHERE project_id=?", (project_id,))
    n = name.strip().lower()
    for a in rows:
        aliases = [a["name"].lower()] + [x.lower() for x in (jloads(a.get("alias"), []) or [])]
        if any(n == x or n in x or x in n for x in aliases if x):
            return a
    return None


def _guess_ref_file(name: str) -> str | None:
    base = re.sub(r"[_\-]?参考图.*$", "", name).strip()
    if "场景" in name:
        return f"{base}_场景参考图.jpg"
    if "道具" in name:
        return f"{base}_道具参考图.jpg"
    return f"{base}_角色参考图.jpg"


def _assets_from_script(project_id: int, text: str) -> int:
    rows = db.query("SELECT name, alias FROM assets WHERE project_id=?", (project_id,))
    known = {}
    for r in rows:
        known[r["name"]] = True
        for a in (jloads(r.get("alias"), []) or []):
            known[a] = True
    # 从「XXX："台词"」里抓角色名
    created = 0
    for m in re.finditer(r"[\*【\[]?([\u4e00-\u9fffA-Za-z]{1,10})[\*】\]]?\s*[：:]\s*[\"“]", text):
        name = m.group(1).strip()
        if name in known or len(name) < 2 or name in ("角色", "音色", "台词", "语气", "旁白", "时间", "地点", "镜头"):
            continue
        db.execute(
            "INSERT INTO assets(project_id, asset_type, name) VALUES(?,?,?) "
            "ON CONFLICT(project_id, asset_type, name) DO NOTHING",
            (project_id, "character", name),
        )
        known[name] = True
        created += 1
    return created


# ---------------- 用模板生成提示词 ----------------

class ApplyTemplateIn(BaseModel):
    template_id: int
    shot_ids: list[int] | None = None
    stage: str = "image"           # image / video
    variables: dict | None = None


@router.post("/episodes/{episode_id}/apply-template")
def apply_template(episode_id: int, body: ApplyTemplateIn) -> dict:
    from ..executors import provider_engine as PE

    tpl = db.query_one("SELECT * FROM prompt_templates WHERE id=?", (body.template_id,))
    if not tpl:
        raise HTTPException(404, "模板不存在")
    shots = (
        db.query("SELECT * FROM shots WHERE id IN (%s)" % ",".join("?" * len(body.shot_ids)), body.shot_ids)
        if body.shot_ids
        else db.query("SELECT * FROM shots WHERE episode_id=? ORDER BY sort_order", (episode_id,))
    )
    ep = db.query_one("SELECT * FROM episodes WHERE id=?", (episode_id,))
    project = db.query_one("SELECT * FROM projects WHERE id=?", (ep["project_id"],)) if ep else None

    done = []
    for s in shots:
        d = db.query_one("SELECT * FROM shot_details WHERE shot_id=?", (s["id"],)) or {}
        refs = []
        for r in db.query(
            """SELECT l.*, a.name AS asset_name FROM shot_asset_links l
               LEFT JOIN assets a ON a.id=l.asset_id
               WHERE l.shot_id=? AND l.target_side=? ORDER BY l.slot_index""",
            (s["id"], "image" if body.stage == "image" else "video"),
        ):
            refs.append({
                "name": r.get("asset_name") or r.get("file_name"),
                "file_name": r.get("file_name"),
                "take_note": r.get("take_note") or "",
            })
        ctx = {
            "shot_code": s["shot_code"],
            "title": s.get("title"),
            "subject": d.get("summary") or "",
            "camera_note": d.get("camera_note") or "",
            "shot_size": d.get("camera_shot") or "",
            "ratio_phrase": f"竖屏{project.get('aspect_ratio', '9:16')}构图" if project else "竖屏9:16构图",
            "style_tail": "写实摄影，电影质感。",
            "refs": refs,
            "duration": d.get("duration_sec") or 5,
            "beats": jloads(d.get("action_beats"), []) or [],
            "image_refs": refs,
            "audio_refs": [
                {"role": ln["role_name"], "text": ln["text"]}
                for ln in db.query("SELECT * FROM shot_dialog_lines WHERE shot_id=?", (s["id"],))
            ],
            **(body.variables or {}),
        }
        try:
            out = PE.render_text(tpl["content"], ctx)
        except Exception as e:  # noqa: BLE001
            done.append({"shot_id": s["id"], "shot_code": s["shot_code"], "error": str(e)})
            continue
        col = "image_prompt" if body.stage == "image" else "video_prompt"
        db.execute(f"UPDATE shot_details SET {col}=?, updated_at=datetime('now','localtime') WHERE shot_id=?",
                   (out, s["id"]))
        db.execute(
            "INSERT INTO prompt_revisions(target_kind, target_id, content, note, source) VALUES(?,?,?,?,?)",
            (f"shot_{body.stage}", s["id"], out, f"模板 {tpl['name']}", "template"),
        )
        done.append({"shot_id": s["id"], "shot_code": s["shot_code"], "preview": out[:200]})
    return {"ok": True, "applied": len([d for d in done if "error" not in d]), "results": done}


# ---------------- 流水线状态 ----------------

@router.get("/projects/{project_id}/pipeline")
def pipeline(project_id: int) -> dict:
    eps = db.query("SELECT * FROM episodes WHERE project_id=? ORDER BY number", (project_id,))
    assets = db.query("SELECT asset_type, COUNT(*) AS c FROM assets WHERE project_id=? GROUP BY asset_type", (project_id,))
    steps = {
        "1_project": {"done": True, "label": "建项目"},
        "2_assets": {
            "done": any(a["c"] > 0 for a in assets),
            "label": "建资产（角色/场景/道具）",
            "detail": {a["asset_type"]: a["c"] for a in assets},
        },
        "3_episodes": {"done": len(eps) > 0, "label": "建集与剧本", "detail": len(eps)},
        "4_split": {
            "done": any(
                db.query_one("SELECT COUNT(*) AS c FROM shots WHERE episode_id=?", (e["id"],))["c"] > 0
                for e in eps
            ),
            "label": "拆解分镜",
            "detail": sum(
                db.query_one("SELECT COUNT(*) AS c FROM shots WHERE episode_id=?", (e["id"],))["c"] for e in eps
            ),
        },
        "5_prompts": {"done": False, "label": "生成双份提示词"},
        "6_keyframes": {"done": False, "label": "生成分镜图"},
        "7_videos": {"done": False, "label": "生成视频"},
        "8_compose": {"done": False, "label": "合成成片"},
    }
    prompt_cnt = db.query_one(
        """SELECT COUNT(*) AS c FROM shot_details d JOIN shots s ON s.id=d.shot_id
           JOIN episodes e ON e.id=s.episode_id
           WHERE e.project_id=? AND (d.video_prompt IS NOT NULL AND d.video_prompt <> '')""",
        (project_id,),
    )["c"]
    steps["5_prompts"]["done"] = prompt_cnt > 0
    steps["5_prompts"]["detail"] = prompt_cnt
    kf = db.query_one(
        """SELECT COUNT(DISTINCT s.id) AS c FROM shots s JOIN episodes e ON e.id=s.episode_id
           LEFT JOIN shot_frames f ON f.shot_id=s.id AND f.frame_type='first'
           WHERE e.project_id=? AND f.id IS NOT NULL""",
        (project_id,),
    )["c"]
    steps["6_keyframes"]["done"] = kf > 0
    steps["6_keyframes"]["detail"] = kf
    vid = db.query_one(
        """SELECT COUNT(DISTINCT s.id) AS c FROM shots s JOIN episodes e ON e.id=s.episode_id
           JOIN task_links l ON l.target_kind='shot' AND l.target_id=s.id
           JOIN generation_tasks t ON t.id=l.task_id AND t.task_kind='video_generation' AND t.status='succeeded'
           WHERE e.project_id=?""",
        (project_id,),
    )["c"]
    steps["7_videos"]["done"] = vid > 0
    steps["7_videos"]["detail"] = vid
    steps["8_compose"]["done"] = db.query_one(
        "SELECT COUNT(*) AS c FROM timeline_clips WHERE episode_id IN "
        "(SELECT id FROM episodes WHERE project_id=?) AND enabled=1",
        (project_id,),
    )["c"] > 0
    return {"steps": steps, "episodes": len(eps)}
