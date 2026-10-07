"""资产库：角色 / 场景 / 道具 / 服装 + 参考图多视图"""
from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from ..config import STORAGE_DIR
from ..core import db
from ..core.db import jdumps, jloads
from ..services import file_store

router = APIRouter(prefix="/api", tags=["assets"])

ASSET_TYPES = ("character", "scene", "prop", "costume", "style")

# 本机上传的图落到哪里：按资产类型挑项目里对应的素材目录
_TYPE_DIR_HINT = {
    "character": ("ref_dir", "角色图"),
    "costume": ("ref_dir", "角色图"),
    "scene": ("workspace_dir", "场景道具参考图"),
    "prop": ("workspace_dir", "场景道具参考图"),
    "style": ("workspace_dir", "场景道具参考图"),
}
# 参考图命名后缀：与「{角色}_角色参考图.jpg」的项目约定保持一致
_TYPE_SUFFIX = {
    "character": "_角色参考图", "costume": "_服装参考图",
    "scene": "_场景参考图", "prop": "_道具参考图", "style": "_风格参考图",
}
_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}


def _asset_upload_dir(project: dict, asset_type: str, override: str | None = None) -> Path:
    """选上传落点：优先用调用方给的目录，否则按类型落项目素材目录。"""
    if override:
        d = Path(override)
        if d.is_absolute():
            return d
    proj_key, sub = _TYPE_DIR_HINT.get(asset_type, ("workspace_dir", "角色图"))
    base = (project or {}).get(proj_key)
    if base:
        cand = Path(base)
        if cand.name == sub:
            return cand
        if (cand / sub).exists():
            return cand / sub
    for k in ("ref_dir", "workspace_dir"):
        v = (project or {}).get(k)
        if v:
            return Path(v)
    return STORAGE_DIR / "uploads"



@router.get("/projects/{project_id}/assets")
def list_assets(project_id: int, asset_type: str | None = None, with_images: bool = True) -> list[dict]:
    sql = "SELECT * FROM assets WHERE project_id=?"
    params: list = [project_id]
    if asset_type:
        sql += " AND asset_type=?"
        params.append(asset_type)
    sql += " ORDER BY asset_type, sort_order, id"
    rows = db.query(sql, params)
    for a in rows:
        if with_images:
            a["images"] = db.query(
                "SELECT * FROM asset_images WHERE asset_id=? ORDER BY is_primary DESC, sort_order, id",
                (a["id"],),
            )
            for im in a["images"]:
                im["file_exists"] = Path(im["file_path"]).exists() if im.get("file_path") else False
        a["shot_count"] = db.query_one(
            "SELECT COUNT(DISTINCT shot_id) AS c FROM shot_asset_links WHERE asset_id=?", (a["id"],)
        )["c"]
        if a.get("alias"):
            a["aliases"] = jloads(a["alias"], [])
    return rows


class AssetIn(BaseModel):
    asset_type: str
    name: str
    alias: list[str] | None = None
    description: str | None = None
    lock_sentence: str | None = None
    voice_id: str | None = None
    voice_params: dict | None = None
    quality_level: str | None = "MEDIUM"


@router.post("/projects/{project_id}/assets")
def create_asset(project_id: int, body: AssetIn) -> dict:
    if body.asset_type not in ASSET_TYPES:
        raise HTTPException(400, f"资产类型必须是 {ASSET_TYPES}")
    exists = db.query_one(
        "SELECT id FROM assets WHERE project_id=? AND asset_type=? AND name=?",
        (project_id, body.asset_type, body.name),
    )
    if exists:
        raise HTTPException(400, "同名资产已存在")
    aid = db.execute(
        """INSERT INTO assets(project_id, asset_type, name, alias, description, lock_sentence,
               voice_id, voice_params, quality_level)
           VALUES(?,?,?,?,?,?,?,?,?)""",
        (
            project_id, body.asset_type, body.name,
            jdumps(body.alias) if body.alias else None,
            body.description, body.lock_sentence, body.voice_id,
            jdumps(body.voice_params) if body.voice_params else None, body.quality_level,
        ),
    )
    return db.query_one("SELECT * FROM assets WHERE id=?", (aid,))


@router.get("/assets/{asset_id}")
def get_asset(asset_id: int) -> dict:
    a = db.query_one("SELECT * FROM assets WHERE id=?", (asset_id,))
    if not a:
        raise HTTPException(404, "资产不存在")
    proj = db.query_one("SELECT id, name FROM projects WHERE id=?", (a.get("project_id"),))
    a["project_name"] = proj["name"] if proj else None
    a["images"] = db.query(
        "SELECT * FROM asset_images WHERE asset_id=? ORDER BY is_primary DESC, sort_order, id", (asset_id,)
    )
    a["shots"] = db.query(
        """SELECT DISTINCT s.id, s.shot_code, e.number AS episode_number
           FROM shot_asset_links l JOIN shots s ON s.id=l.shot_id
           JOIN episodes e ON e.id=s.episode_id
           WHERE l.asset_id=? ORDER BY e.number, s.sort_order""",
        (asset_id,),
    )
    a["aliases"] = jloads(a.get("alias"), []) or []
    return a


@router.patch("/assets/{asset_id}")
def patch_asset(asset_id: int, body: dict) -> dict:
    allowed = {"name", "alias", "description", "lock_sentence", "voice_id", "voice_params",
               "quality_level", "default_ratio", "sort_order", "asset_type"}
    vals = {}
    for k, v in body.items():
        if k not in allowed:
            continue
        vals[k] = jdumps(v) if k in ("alias", "voice_params") and not isinstance(v, str) else v
    if not vals:
        raise HTTPException(400, "无可更新字段")
    cols = ", ".join(f"{k}=?" for k in vals)
    db.execute(
        f"UPDATE assets SET {cols}, updated_at=datetime('now','localtime') WHERE id=?",
        list(vals.values()) + [asset_id],
    )
    return db.query_one("SELECT * FROM assets WHERE id=?", (asset_id,))


@router.delete("/assets/{asset_id}")
def delete_asset(asset_id: int) -> dict:
    db.execute("DELETE FROM assets WHERE id=?", (asset_id,))
    return {"ok": True}


# ---------------- 参考图 ----------------

class AssetImageIn(BaseModel):
    file_path: str | None = None
    file_name: str | None = None
    usage_kind: str = "reference"
    view_angle: str | None = None
    take_note: str | None = None
    is_primary: bool = False


@router.post("/assets/{asset_id}/images")
def add_image(asset_id: int, body: AssetImageIn) -> dict:
    a = db.query_one("SELECT * FROM assets WHERE id=?", (asset_id,))
    if not a:
        raise HTTPException(404, "资产不存在")
    project = db.query_one("SELECT * FROM projects WHERE id=?", (a["project_id"],))
    real = None
    if body.file_path:
        p = Path(body.file_path)
        real = p if p.exists() else file_store.resolve(body.file_path, project)
    elif body.file_name:
        real = file_store.resolve(body.file_name, project)
    if not real:
        raise HTTPException(400, "找不到文件，请给出存在的路径或素材目录里的文件名")
    info = file_store.probe(real)
    exists = db.query_one(
        "SELECT id FROM asset_images WHERE asset_id=? AND file_name=?", (asset_id, real.name)
    )
    if exists:
        db.execute(
            """UPDATE asset_images SET file_path=?, usage_kind=?, view_angle=?, take_note=?, is_primary=?,
                   width=?, height=?, format=?, size_bytes=? WHERE id=?""",
            (str(real.resolve()), body.usage_kind, body.view_angle, body.take_note,
             1 if body.is_primary else 0, info.get("width"), info.get("height"),
             info.get("format"), info.get("size_bytes"), exists["id"]),
        )
        iid = exists["id"]
    else:
        iid = db.execute(
            """INSERT INTO asset_images(asset_id, usage_kind, view_angle, file_path, file_name,
                   is_primary, take_note, width, height, format, size_bytes)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (asset_id, body.usage_kind, body.view_angle, str(real.resolve()), real.name,
             1 if body.is_primary else 0, body.take_note, info.get("width"), info.get("height"),
             info.get("format"), info.get("size_bytes")),
        )
    file_store.index_file(real)
    return db.query_one("SELECT * FROM asset_images WHERE id=?", (iid,))


@router.post("/assets/{asset_id}/upload-image")
async def upload_image(
    asset_id: int,
    file: UploadFile = File(...),
    save_as: str | None = Form(None),
    dest_dir: str | None = Form(None),
    usage_kind: str = Form("reference"),
    view_angle: str | None = Form(None),
    take_note: str | None = Form(None),
) -> dict:
    """从本机上传一张图，存进项目素材目录，并直接登记为该资产的参考图。

    - 落点按资产类型自动选（角色→项目角色图目录，场景/道具→场景道具参考图目录），可用 dest_dir 覆盖
    - 若目标目录里已有同名且同体积的文件，直接复用，不会产生 _1/_2 副本
    - 该资产还没有图时，这张自动设为主图
    """
    a = db.query_one("SELECT * FROM assets WHERE id=?", (asset_id,))
    if not a:
        raise HTTPException(404, "资产不存在")
    project = db.query_one("SELECT * FROM projects WHERE id=?", (a["project_id"],)) or {}

    raw_name = Path(file.filename or "upload.jpg").name
    ext = Path(raw_name).suffix.lower()
    if ext not in _IMAGE_EXT:
        raise HTTPException(400, f"只支持图片：{'/'.join(sorted(_IMAGE_EXT))}（收到 {ext or '无后缀'}）")

    # 默认按项目约定命名：{资产名}_角色参考图.jpg
    default_name = f"{a['name']}{_TYPE_SUFFIX.get(a['asset_type'], '_参考图')}{ext}"
    name = Path(save_as).name if save_as and save_as.strip() else default_name
    if Path(name).suffix.lower() not in _IMAGE_EXT:
        name = Path(name).stem + ext

    target_dir = _asset_upload_dir(project, a["asset_type"], dest_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    dst = target_dir / name

    reused = False
    if dst.exists():
        incoming = await file.read()
        if len(incoming) == dst.stat().st_size:
            reused = True          # 同名同体积 → 视为同一张，不重复落盘
        else:
            i = 1
            while dst.exists():
                dst = target_dir / f"{Path(name).stem}_{i}{ext}"
                i += 1
            with open(dst, "wb") as f:
                f.write(incoming)
    else:
        with open(dst, "wb") as f:
            shutil.copyfileobj(file.file, f)

    info = file_store.probe(dst)
    if not info.get("width"):
        if not reused:
            dst.unlink(missing_ok=True)
        raise HTTPException(400, "这个文件不是有效图片，已丢弃")

    has_img = db.query_one("SELECT COUNT(*) AS c FROM asset_images WHERE asset_id=?", (asset_id,))["c"]
    exists = db.query_one(
        "SELECT id FROM asset_images WHERE asset_id=? AND file_name=?", (asset_id, dst.name)
    )
    if exists:
        db.execute(
            """UPDATE asset_images SET file_path=?, usage_kind=?, view_angle=?, take_note=?,
                   width=?, height=?, format=?, size_bytes=? WHERE id=?""",
            (str(dst.resolve()), usage_kind, view_angle, take_note,
             info.get("width"), info.get("height"), info.get("format"), info.get("size_bytes"),
             exists["id"]),
        )
        iid = exists["id"]
    else:
        iid = db.execute(
            """INSERT INTO asset_images(asset_id, usage_kind, view_angle, file_path, file_name,
                   is_primary, take_note, width, height, format, size_bytes)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (asset_id, usage_kind, view_angle, str(dst.resolve()), dst.name,
             1 if not has_img else 0, take_note, info.get("width"), info.get("height"),
             info.get("format"), info.get("size_bytes")),
        )
    file_store.index_file(dst)
    return {
        "ok": True, "reused": reused, "path": str(dst.resolve()), "file_name": dst.name,
        "dir": str(target_dir), "size_bytes": info.get("size_bytes"),
        "image": db.query_one("SELECT * FROM asset_images WHERE id=?", (iid,)),
    }


@router.delete("/assets/{asset_id}/images/{image_id}")
def delete_image(asset_id: int, image_id: int) -> dict:
    db.execute("DELETE FROM asset_images WHERE id=? AND asset_id=?", (image_id, asset_id))
    return {"ok": True}


@router.patch("/asset-images/{image_id}")
def patch_image(image_id: int, body: dict) -> dict:
    allowed = {"usage_kind", "view_angle", "take_note", "is_primary", "sort_order"}
    vals = {k: v for k, v in body.items() if k in allowed}
    if not vals:
        raise HTTPException(400, "无可更新字段")
    cols = ", ".join(f"{k}=?" for k in vals)
    db.execute(f"UPDATE asset_images SET {cols} WHERE id=?", list(vals.values()) + [image_id])
    return db.query_one("SELECT * FROM asset_images WHERE id=?", (image_id,))


# ---------------- 目录扫描导入 ----------------

class ScanIn(BaseModel):
    dirs: list[str] | None = None


@router.post("/projects/{project_id}/assets/scan")
def scan_assets(project_id: int, body: ScanIn | None = None) -> dict:
    """扫描素材目录里的 *参考图* 文件，批量建资产。"""
    p = db.query_one("SELECT * FROM projects WHERE id=?", (project_id,))
    if not p:
        raise HTTPException(404, "项目不存在")
    dirs: list[Path] = []
    if body and body.dirs:
        dirs = [Path(d) for d in body.dirs]
    else:
        ws = Path(p.get("workspace_dir") or ".")
        dirs = [d for d in (Path(p.get("ref_dir") or ""), ws / "角色图" / "attachments",
                            ws / "场景道具参考图", ws / "辅助图") if str(d)]
    created, updated, scanned = 0, 0, 0
    seen_names: list[str] = []
    for d in dirs:
        if not d.exists():
            continue
        for f in sorted(d.iterdir()):
            if not f.is_file() or "参考图" not in f.name:
                continue
            if f.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
                continue
            if f.name.endswith("_v1.jpg") or "_高清版" in f.name:
                continue
            scanned += 1
            seen_names.append(f.name)
            atype = file_store.guess_asset_type(f.name)
            name = file_store.guess_asset_name(f.name)
            row = db.query_one(
                "SELECT id FROM assets WHERE project_id=? AND asset_type=? AND name=?",
                (project_id, atype, name),
            )
            if row:
                aid = row["id"]
                updated += 1
            else:
                aid = db.execute(
                    "INSERT INTO assets(project_id, asset_type, name) VALUES(?,?,?)",
                    (project_id, atype, name),
                )
                created += 1
            info = file_store.probe(f)
            img = db.query_one(
                "SELECT id FROM asset_images WHERE asset_id=? AND file_name=?", (aid, f.name)
            )
            if img:
                db.execute(
                    "UPDATE asset_images SET file_path=? WHERE id=?", (str(f.resolve()), img["id"])
                )
            else:
                db.execute(
                    """INSERT INTO asset_images(asset_id, usage_kind, file_path, file_name,
                           width, height, format, size_bytes)
                       VALUES(?,?,?,?,?,?,?,?)""",
                    (aid, "reference", str(f.resolve()), f.name, info.get("width"),
                     info.get("height"), info.get("format"), info.get("size_bytes")),
                )
            file_store.index_file(f)
    return {"scanned": scanned, "assets_created": created, "assets_touched": updated,
            "files": seen_names, "dirs": [str(d) for d in dirs]}


@router.get("/projects/{project_id}/asset-coverage")
def asset_coverage(project_id: int) -> dict:
    """资产覆盖度：哪些角色/场景还没参考图、哪些镜头引用了缺图资产。"""
    rows = db.query("SELECT * FROM assets WHERE project_id=?", (project_id,))
    out = []
    for a in rows:
        imgs = db.query_one("SELECT COUNT(*) AS c FROM asset_images WHERE asset_id=?", (a["id"],))["c"]
        shots = db.query_one(
            "SELECT COUNT(DISTINCT shot_id) AS c FROM shot_asset_links WHERE asset_id=?", (a["id"],)
        )["c"]
        out.append({
            "asset_id": a["id"], "name": a["name"], "asset_type": a["asset_type"],
            "image_count": imgs, "shot_count": shots,
            "quality_level": a.get("quality_level"),
            "needs_image": imgs == 0,
        })
    return {
        "assets": out,
        "missing_images": [x for x in out if x["needs_image"]],
        "total": len(out),
    }
