"""把 md 文档导入数据库。

导入期自动产出：
1. 镜头 + 明细（提示词各段、时序拍点、硬约束、时长唯一事实源）
2. 资产库（从参考图文件名反推角色/场景/道具）+ 参考图记录
3. 参考图槽位（shot_asset_links）——提示词「参考图N」由此派生
4. 台词行 + 实测音频时长
5. 幽灵引用候选（解析不到文件的引用）→ 待人工「关联/忽略」
6. 健康问题（缺文件、待生成、作废段落…）
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from ..core import db
from ..services import file_store, naming
from ..core.db import jdumps
from . import md_video_parser as VP
from . import md_storyboard_parser as SP


@dataclass
class ImportResult:
    project_id: int = 0
    episode_id: int = 0
    episode_number: int = 0
    video_doc: str | None = None
    storyboard_doc: str | None = None
    shots_total: int = 0
    shots_created: int = 0
    shots_updated: int = 0
    assets_created: int = 0
    links_created: int = 0
    frames_linked: int = 0
    issues: list[dict] = field(default_factory=list)
    shots: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        d["issues"] = self.issues
        return d


# ---------------- 项目解析辅助 ----------------

DOC_TITLE_RE = re.compile(r"^#\s*(?P<t>.+?)\s*$", re.M)
EP_RE = re.compile(r"第\s*(\d+)\s*集")


def _doc_title(text: str) -> str:
    m = DOC_TITLE_RE.search(text)
    return m.group("t") if m else ""


def _project_meta_from_doc(text: str) -> dict:
    title = _doc_title(text)
    name = title
    m = re.match(r"第\s*\d+\s*集\s*[：:]\s*(?P<n>.+?)(?:\s*——|\s*--|\s*$)", title)
    if m:
        name = m.group("n").strip()
    else:
        name = title.split("——")[0].strip()
    return {"name": name, "doc_title": title}


# ---------------- 主流程 ----------------

def import_episode(
    project_id: int,
    episode_number: int,
    video_doc_path: str | Path,
    storyboard_doc_path: str | Path | None = None,
    rebuild: bool = False,
    script_text: str | None = None,
) -> ImportResult:
    res = ImportResult(project_id=project_id, episode_number=episode_number)
    vpath = Path(video_doc_path)
    if not vpath.exists():
        raise FileNotFoundError(f"核对版文档不存在：{vpath}")
    res.video_doc = str(vpath)
    vtext = vpath.read_text(encoding="utf-8", errors="ignore")

    stext, spath = "", None
    if storyboard_doc_path:
        spath = Path(storyboard_doc_path)
        if spath.exists():
            res.storyboard_doc = str(spath)
            stext = spath.read_text(encoding="utf-8", errors="ignore")

    project = db.query_one("SELECT * FROM projects WHERE id = ?", (project_id,))
    if not project:
        raise ValueError(f"项目不存在：{project_id}")

    # 集
    ep = db.query_one(
        "SELECT * FROM episodes WHERE project_id=? AND number=?", (project_id, episode_number)
    )
    if not ep:
        ep_id = db.execute(
            """INSERT INTO episodes(project_id, number, title, video_doc_path, storyboard_doc_path, script_text)
               VALUES(?,?,?,?,?,?)""",
            (
                project_id,
                episode_number,
                f"第{episode_number}集",
                str(vpath),
                str(spath) if spath else None,
                script_text,
            ),
        )
    else:
        ep_id = ep["id"]
        db.execute(
            """UPDATE episodes SET video_doc_path=?, storyboard_doc_path=?,
                   script_text=COALESCE(?, script_text), updated_at=datetime('now','localtime') WHERE id=?""",
            (str(vpath), str(spath) if spath else None, script_text, ep_id),
        )
    res.episode_id = ep_id

    # 解析
    vshots = VP.parse_video_doc(vtext)
    sshots = {s.shot_code: s for s in SP.parse_storyboard_doc(stext)} if stext else {}
    res.shots_total = len(vshots)
    res.shots = [s.shot_code for s in vshots]

    # 若重建：清掉本集旧数据（保留资产）
    if rebuild:
        db.execute("DELETE FROM shots WHERE episode_id = ?", (ep_id,))

    search_dirs = file_store._candidate_dirs(project)

    for order, vs in enumerate(vshots):
        ss = sshots.get(vs.shot_code)
        shot_id, created = _upsert_shot(project, ep_id, vs, ss, order, search_dirs, res)
        if created:
            res.shots_created += 1
        else:
            res.shots_updated += 1

    _resolve_tail_frames(project, ep_id, vshots, search_dirs, res)
    _scan_health(project, ep_id, res)
    return res


def _upsert_shot(
    project: dict,
    ep_id: int,
    vs: VP.ParsedVideoShot,
    ss: SP.ParsedStoryboardShot | None,
    order: int,
    search_dirs: list[Path],
    res: ImportResult,
) -> tuple[int, bool]:
    ep_number = project.get("_ep_number") or 1
    existing = db.query_one("SELECT id FROM shots WHERE episode_id=? AND shot_code=?", (ep_id, vs.shot_code))
    created = existing is None

    dur = vs.duration_sec
    notes = "\n".join(x for x in [ss.notes if ss else None, ss.lead_notes if ss else None] if x)
    if created:
        shot_id = db.execute(
            """INSERT INTO shots(episode_id, shot_code, title, sort_order, notes, meta)
               VALUES(?,?,?,?,?,?)""",
            (ep_id, vs.shot_code, vs.title or None, order, notes or None, None),
        )
    else:
        shot_id = existing["id"]
        db.execute(
            """UPDATE shots SET title=?, sort_order=?, notes=?, updated_at=datetime('now','localtime')
               WHERE id=?""",
            (vs.title or None, order, notes or None, shot_id),
        )

    # 分镜图目标文件名（优先文档写的，其次按镜号推导）
    target_file = ss.target_file if ss and ss.target_file else None
    if not target_file:
        for nm in naming.keyframe_names(vs.shot_code):
            if file_store.resolve(nm, project):
                target_file = nm
                break

    # details
    row = db.query_one("SELECT shot_id FROM shot_details WHERE shot_id=?", (shot_id,))
    values = dict(
        gen_mode=vs.gen_mode,
        api_style=vs.api_style,
        duration_sec=dur,
        duration_note=vs.duration_note,
        resolution=vs.resolution,
        seed=vs.seed,
        summary=vs.summary,
        action_beats=jdumps(vs.beats),
        beats_text_dummy=None,
        hard_constraints=jdumps(vs.constraints),
        audio_note=vs.audio_block,
        post_audio_note=vs.post_audio_block,
        video_prompt=vs.video_prompt,
        video_prompt_prefix=vs.prefix,
        image_prompt=ss.prompt if ss else None,
        image_target_name=target_file,
        image_refs_note=ss.refs_block if ss else None,
        image_is_optional=1 if (ss and ss.is_optional) else 0,
    )
    values.pop("beats_text_dummy")
    if row:
        cols = ", ".join(f"{k}=?" for k in values)
        db.execute(
            f"UPDATE shot_details SET {cols}, updated_at=datetime('now','localtime') WHERE shot_id=?",
            list(values.values()) + [shot_id],
        )
    else:
        cols = ", ".join(values.keys())
        ph = ", ".join("?" for _ in values)
        db.execute(
            f"INSERT INTO shot_details(shot_id, {cols}) VALUES(?, {ph})",
            [shot_id] + list(values.values()),
        )

    # 提示词版本快照（首次导入留档，内容变化时追加）
    _snapshot_revision(shot_id, "shot_video", vs.video_prompt, "import")
    if ss and ss.prompt:
        _snapshot_revision(shot_id, "shot_image", ss.prompt, "import")

    # 参考素材
    _link_refs(project, ep_id, shot_id, vs, ss, search_dirs, res)

    # 台词
    if vs.audio_text or vs.audio_file:
        au_path = file_store.resolve(vs.audio_file, project) if vs.audio_file else None
        measured = vs.audio_measured_sec or (file_store.audio_duration(au_path) if au_path else None)
        db.execute("DELETE FROM shot_dialog_lines WHERE shot_id=?", (shot_id,))
        db.execute(
            """INSERT INTO shot_dialog_lines(shot_id, line_index, role_name, text, line_mode, tone,
                   audio_file, audio_measured_sec, start_sec, end_sec)
               VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (
                shot_id,
                1,
                vs.audio_role,
                vs.audio_text,
                "dialogue" if vs.audio_text else "sfx",
                vs.audio_tone,
                vs.audio_file,
                measured,
                vs.line_start_sec,
                vs.line_end_sec,
            ),
        )
        if vs.audio_file and not au_path:
            res.issues.append(
                _issue(project, ep_id, shot_id, "audio_missing", "warn",
                       vs.audio_file, f"音频文件未找到：{vs.audio_file}",
                       "确认文件名或在音频目录补齐")
            )
        elif measured and dur and vs.line_start_sec is not None:
            span = dur - vs.line_start_sec
            if span < measured - 0.001:
                res.issues.append(
                    _issue(project, ep_id, shot_id, "duration_short", "error",
                           f"duration={dur}", f"时长不足：{dur}s - 起点{vs.line_start_sec}s = {span:.2f}s < 音频 {measured}s",
                           "加长 duration 或提前台词起点")
                )
    return shot_id, created


def _snapshot_revision(target_id: int, kind: str, content: str | None, source: str) -> None:
    if not content:
        return
    last = db.query_one(
        "SELECT content FROM prompt_revisions WHERE target_kind=? AND target_id=? ORDER BY id DESC LIMIT 1",
        (kind, target_id),
    )
    if last and last["content"] == content:
        return
    db.execute(
        "INSERT INTO prompt_revisions(target_kind, target_id, content, source) VALUES(?,?,?,?)",
        (kind, target_id, content, source),
    )


# ---------------- 参考素材与资产 ----------------

TAIL_RE = re.compile(r"(?P<stem>01\d{2}[a-z]?\d*)_tail\.(jpg|jpeg|png)$", re.I)


def _classify_ref(file_name: str) -> str:
    n = file_name
    if TAIL_RE.search(n):
        return "tail_frame"
    if "角色参考图" in n or "金甲" in n:
        return "asset_character"
    if "场景参考图" in n:
        return "asset_scene"
    if "道具参考图" in n:
        return "asset_prop"
    if re.match(r"^01\d{2}", n):
        return "keyframe"
    return "other"


def _ensure_asset(
    project: dict, file_name: str, real_path: Path | None, res: ImportResult
) -> tuple[int | None, int | None]:
    """确保资产存在，并把这张参考图挂到资产下。返回 (asset_id, asset_image_id)。"""
    asset_type = file_store.guess_asset_type(file_name)
    name = file_store.guess_asset_name(file_name)
    if not name:
        return None, None
    row = db.query_one(
        "SELECT id FROM assets WHERE project_id=? AND asset_type=? AND name=?",
        (project["id"], asset_type, name),
    )
    if row:
        asset_id = row["id"]
    else:
        asset_id = db.execute(
            """INSERT INTO assets(project_id, asset_type, name, alias) VALUES(?,?,?,?)""",
            (project["id"], asset_type, name, jdumps(_aliases_for(name, file_name))),
        )
        res.assets_created += 1

    image_id = None
    if real_path and real_path.exists():
        info = file_store.probe(real_path)
        exists = db.query_one(
            "SELECT id FROM asset_images WHERE asset_id=? AND file_name=? AND usage_kind='reference'",
            (asset_id, real_path.name),
        )
        if exists:
            image_id = exists["id"]
        else:
            image_id = db.execute(
                """INSERT INTO asset_images(asset_id, usage_kind, file_path, file_name, is_primary,
                       width, height, format, size_bytes)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (
                    asset_id,
                    "reference",
                    str(real_path.resolve()),
                    real_path.name,
                    1 if real_path.name == f"{name}_角色参考图.jpg" else 0,
                    info.get("width"),
                    info.get("height"),
                    info.get("format"),
                    info.get("size_bytes"),
                ),
            )
    return asset_id, image_id


def _aliases_for(name: str, file_name: str) -> list[str]:
    out = {name, Path(file_name).stem}
    known = {
        "权限魅影": ["魅影", "权限魅影", "灰黑雾气人形"],
        "过客": ["过客", "他", "男主角"],
        "死循环妖": ["死循环妖", "绿眼妖"],
        "内存黑洞王": ["内存黑洞王", "黑洞王"],
        "林岚": ["林岚"],
    }
    return sorted(out | set(known.get(name, [])))


def _link_refs(
    project: dict,
    ep_id: int,
    shot_id: int,
    vs: VP.ParsedVideoShot,
    ss: SP.ParsedStoryboardShot | None,
    search_dirs: list[Path],
    res: ImportResult,
) -> None:
    # 视频侧：ref_image_0..N（有 API 参数就用参数，否则用声明）
    video_items = vs.image_param_refs or vs.image_refs
    db.execute("DELETE FROM shot_asset_links WHERE shot_id=? AND target_side='video'", (shot_id,))
    for it in video_items:
        fname = it.file_name
        real = file_store.resolve(fname, project) if fname else None
        asset_id = image_id = None
        kind = _classify_ref(fname) if fname else "other"
        if kind.startswith("asset_") and not file_store.is_placeholder(fname):
            asset_id, image_id = _ensure_asset(project, fname, real, res)
        if not real and fname and not file_store.is_placeholder(fname):
            res.issues.append(
                _issue(project, ep_id, shot_id, "ghost_ref", "warn", fname,
                       f"视频侧引用的文件不存在：{fname}", "补齐文件或修正引用名")
            )
        db.execute(
            """INSERT OR REPLACE INTO shot_asset_links(shot_id, asset_id, asset_image_id, role, slot_index,
                   target_side, ref_version, take_note, file_name, raw_text)
               VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (
                shot_id,
                asset_id,
                image_id,
                _role_from_desc(it.description),
                it.image_index,
                "video",
                "render_frame" if kind == "tail_frame" else ("concept" if kind.startswith("asset_") else None),
                it.description,
                fname,
                it.description,
            ),
        )
        res.links_created += 1

    # 分镜图侧：上传参考图 1..N
    if ss and ss.ref_items:
        db.execute("DELETE FROM shot_asset_links WHERE shot_id=? AND target_side='image'", (shot_id,))
        for it in ss.ref_items:
            fname = it.file_name
            real = file_store.resolve(fname, project) if fname else None
            asset_id = image_id = None
            kind = _classify_ref(fname) if fname else "other"
            if kind.startswith("asset_") and not file_store.is_placeholder(fname):
                asset_id, image_id = _ensure_asset(project, fname, real, res)
            db.execute(
                """INSERT OR REPLACE INTO shot_asset_links(shot_id, asset_id, asset_image_id, role, slot_index,
                       target_side, ref_version, take_note, file_name, raw_text)
                   VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (
                    shot_id,
                    asset_id,
                    image_id,
                    _role_from_desc(it.note),
                    it.index,
                    "image",
                    "render_frame" if kind == "tail_frame" else ("concept" if kind.startswith("asset_") else None),
                    it.note,
                    fname,
                    it.note,
                ),
            )
            res.links_created += 1


def _role_from_desc(desc: str | None) -> str | None:
    if not desc:
        return None
    for kw in (
        "首帧锚点", "尾帧锚点", "构图锚点", "机位锚点", "形态锚点", "人形形态锚点",
        "视频首帧", "落幅构图锚点", "仅取色调", "仅取形态", "环境参考", "音色参考",
    ):
        if kw in desc:
            return kw
    return None


# ---------------- 尾帧 ↔ 镜头 互链 ----------------

def _resolve_tail_frames(
    project: dict, ep_id: int, vshots: list[VP.ParsedVideoShot], search_dirs: list[Path], res: ImportResult
) -> None:
    """把 0114b2_tail.jpg 这类渲染尾帧挂到对应镜头的 last frame 上。"""
    by_stem: dict[str, str] = {}
    for vs in vshots:
        by_stem[naming.code_stem(vs.shot_code).lower()] = vs.shot_code

    for d in search_dirs:
        if not d.exists() or "尾帧" not in str(d):
            continue
        for f in d.iterdir():
            m = TAIL_RE.match(f.name)
            if not m:
                continue
            stem = m.group("stem").lower()
            code = by_stem.get(stem)
            if not code:
                continue
            shot = db.query_one("SELECT id FROM shots WHERE episode_id=? AND shot_code=?", (ep_id, code))
            if not shot:
                continue
            info = file_store.probe(f)
            db.execute(
                """INSERT OR REPLACE INTO shot_frames(shot_id, frame_type, file_path, file_name, source,
                       width, height, format, size_bytes, note)
                   VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (
                    shot["id"],
                    "last",
                    str(f.resolve()),
                    f.name,
                    "tail_frame",
                    info.get("width"),
                    info.get("height"),
                    info.get("format"),
                    info.get("size_bytes"),
                    f"{code} 视频尾帧",
                ),
            )
            res.frames_linked += 1


# ---------------- 健康巡检 ----------------

def _issue(project: dict, ep_id: int | None, shot_id: int | None, itype: str, sev: str,
           target: str, message: str, suggestion: str) -> dict:
    db.execute(
        """INSERT INTO health_issues(project_id, episode_id, shot_id, issue_type, severity,
               target, message, suggestion) VALUES(?,?,?,?,?,?,?,?)""",
        (project["id"], ep_id, shot_id, itype, sev, target, message, suggestion),
    )
    return {"type": itype, "severity": sev, "target": target, "message": message, "shot_id": shot_id}


def _scan_health(project: dict, ep_id: int, res: ImportResult) -> None:
    db.execute("DELETE FROM health_issues WHERE episode_id=? AND resolved=0", (ep_id,))
    shots = db.query("SELECT id, shot_code, thumbnail_path FROM shots WHERE episode_id=?", (ep_id,))
    for s in shots:
        sid = s["id"]
        code = s["shot_code"]
        d = db.query_one("SELECT * FROM shot_details WHERE shot_id=?", (sid,))
        if not d:
            continue
        # 首帧 / 分镜图存在性
        frames = db.query("SELECT frame_type, file_path FROM shot_frames WHERE shot_id=? AND is_active=1", (sid,))
        ftypes = {f["frame_type"] for f in frames}
        links_v = db.query(
            "SELECT file_name, file_path FROM shot_asset_links WHERE shot_id=? AND target_side='video' ORDER BY slot_index",
            (sid,),
        ) if False else db.query(
            """SELECT l.file_name, ai.file_path FROM shot_asset_links l
               LEFT JOIN asset_images ai ON ai.id = l.asset_image_id
               WHERE l.shot_id=? AND l.target_side='video' ORDER BY l.slot_index""",
            (sid,),
        )
        first_ref = links_v[0]["file_name"] if links_v else None
        if first_ref:
            real = file_store.resolve(first_ref, project)
            if not real and not file_store.is_placeholder(first_ref):
                res.issues.append(
                    _issue(project, ep_id, sid, "missing_first_frame", "error", first_ref,
                           f"镜头{code} 首帧缺失：{first_ref}", "生成该分镜图或改用已有尾帧")
                )
        # 分镜图侧提示词缺失
        if not d.get("image_prompt") and not d.get("image_is_optional"):
            res.issues.append(
                _issue(project, ep_id, sid, "no_image_prompt", "info", code,
                       f"镜头{code} 缺分镜图提示词", "补充或标记为不需要分镜图")
            )
        # 视频提示词缺防转场句
        vp = d.get("video_prompt") or ""
        if vp and "严禁黑场" not in vp and "黑场" not in (d.get("hard_constraints") or ""):
            res.issues.append(
                _issue(project, ep_id, sid, "no_transition_guard", "warn", code,
                       f"镜头{code} 未包含防转场句（严禁黑场/淡入淡出）", "补入防转场硬约束")
            )
        # 时长缺失
        if not d.get("duration_sec"):
            res.issues.append(
                _issue(project, ep_id, sid, "no_duration", "warn", code,
                       f"镜头{code} 未设置时长", "补 duration")
            )
        # 台词时长校验：duration - 台词起点 必须 ≥ 音频实测
        line = db.query_one(
            "SELECT audio_measured_sec, start_sec FROM shot_dialog_lines WHERE shot_id=? LIMIT 1", (sid,)
        )
        if (
            line
            and line["audio_measured_sec"]
            and d.get("duration_sec")
            and line["start_sec"] is not None
        ):
            span = d["duration_sec"] - line["start_sec"]
            if span + 1e-6 < line["audio_measured_sec"]:
                res.issues.append(
                    _issue(project, ep_id, sid, "duration_short", "error", code,
                           f"镜头{code} 台词可能被截断：可用 {span:.2f}s < 音频 {line['audio_measured_sec']}s",
                           "加长 duration 或提前台词起点")
                )
