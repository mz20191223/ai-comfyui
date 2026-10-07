"""供应商 / 模型 / 系统设置 —— 「不写死」的配置面板后端"""
from __future__ import annotations

import json
import os
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..core import db
from ..core.db import jdumps, jloads
from ..executors import provider_engine as PE

router = APIRouter(prefix="/api", tags=["config"])


# ---------------- 供应商 ----------------

@router.get("/providers")
def list_providers() -> list[dict]:
    rows = db.query("SELECT * FROM providers ORDER BY id")
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    for r in rows:
        r["caps"] = jloads(r.get("capabilities"), []) or []
        r["models"] = db.query("SELECT id, name, category, model_name, mode FROM models WHERE provider_id=?", (r["id"],))
        creds = db.query(
            "SELECT id, alias, status, enabled, cooldown_until, fail_count, last_used_at, balance, "
            "balance_note, balance_checked_at, probe_ok, probe_note, last_error, api_key "
            "FROM provider_credentials "
            "WHERE provider_id=? AND enabled=1 ORDER BY sort_order, id", (r["id"],)
        )
        for c in creds:
            c["key_masked"] = _mask_key(c.pop("api_key", "") or "")
        r["credentials"] = creds
        r["cred_total"] = len(creds)
        r["cred_usable"] = sum(
            1 for c in creds
            if c["status"] == "active" or (c["status"] == "cooling" and (c.get("cooldown_until") or "") <= now)
        )
        # 有密钥池的看池子；没有池子的（如本地执行）再看旧的 api_key_ref / settings
        r["has_key"] = bool(r["cred_total"]) or bool(PE.resolve_api_key(r))
        r["meta_obj"] = jloads(r.get("meta"), {}) or {}
    return rows


class ProviderIn(BaseModel):
    key: str
    name: str
    capabilities: list[str] | None = None
    base_url: str | None = None
    image_base_url: str | None = None
    video_base_url: str | None = None
    api_key: str | None = None
    api_key_ref: str | None = None
    auth_header: str | None = "Authorization"
    auth_scheme: str | None = "Bearer"
    concurrency: int | None = 2
    timeout_sec: int | None = 600
    retry: int | None = 1
    proxy_mode: str | None = "system"
    proxy_url: str | None = None
    enabled: bool | None = True


@router.post("/providers")
def create_provider(body: ProviderIn) -> dict:
    if db.query_one("SELECT id FROM providers WHERE key=?", (body.key,)):
        raise HTTPException(400, "key 已存在")
    data = body.model_dump()
    api_key = data.pop("api_key", None)
    caps = data.pop("capabilities", None)
    pid = db.execute(
        """INSERT INTO providers(key, name, capabilities, base_url, image_base_url, video_base_url,
               api_key_ref, auth_header, auth_scheme, concurrency, timeout_sec, retry,
               proxy_mode, proxy_url, enabled)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (data["key"], data["name"], jdumps(caps or []), data["base_url"], data["image_base_url"],
         data["video_base_url"], data.get("api_key_ref"), data["auth_header"], data["auth_scheme"],
         data["concurrency"], data["timeout_sec"], data["retry"], data["proxy_mode"],
         data["proxy_url"], 1 if data["enabled"] else 0),
    )
    if api_key:
        _store_key(body.key, api_key)
    return db.query_one("SELECT * FROM providers WHERE id=?", (pid,))


@router.patch("/providers/{provider_id}")
def patch_provider(provider_id: int, body: dict) -> dict:
    p = db.query_one("SELECT * FROM providers WHERE id=?", (provider_id,))
    if not p:
        raise HTTPException(404, "供应商不存在")
    allowed = {"name", "capabilities", "base_url", "image_base_url", "video_base_url",
               "api_key_ref", "auth_header", "auth_scheme", "concurrency", "timeout_sec",
               "retry", "proxy_mode", "proxy_url", "enabled", "meta"}
    vals = {}
    for k, v in body.items():
        if k not in allowed:
            continue
        vals[k] = jdumps(v) if k in ("capabilities", "meta") and not isinstance(v, str) else (
            1 if k == "enabled" and isinstance(v, bool) else v
        )
    if vals:
        cols = ", ".join(f"{k}=?" for k in vals)
        db.execute(
            f"UPDATE providers SET {cols}, updated_at=datetime('now','localtime') WHERE id=?",
            list(vals.values()) + [provider_id],
        )
    if body.get("api_key"):
        _store_key(p["key"], body["api_key"])
    return db.query_one("SELECT * FROM providers WHERE id=?", (provider_id,))


def _store_key(provider_key: str, api_key: str) -> None:
    db.execute(
        "INSERT INTO settings(key, value, category) VALUES(?,?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=datetime('now','localtime')",
        (f"provider_key:{provider_key}", api_key, "secrets"),
    )
    ref = "${ENV:"
    db.execute(
        "UPDATE providers SET api_key_ref=? WHERE key=? AND (api_key_ref IS NULL OR api_key_ref='')",
        (f"${{ENV:STUDIO_{provider_key.upper().replace('-', '_')}_KEY}}", provider_key),
    )


@router.delete("/providers/{provider_id}")
def delete_provider(provider_id: int) -> dict:
    db.execute("DELETE FROM providers WHERE id=?", (provider_id,))
    return {"ok": True}


@router.post("/providers/{provider_id}/test")
def test_provider(provider_id: int) -> dict:
    p = db.query_one("SELECT * FROM providers WHERE id=?", (provider_id,))
    if not p:
        raise HTTPException(404, "供应商不存在")
    usable = PE.usable_credentials(provider_id)
    key = PE.resolve_api_key(p, usable[0] if usable else None)
    total = len(PE.list_credentials(provider_id, only_enabled=False))
    return {
        "has_key": bool(key),
        "key_hint": _mask_key(key),
        "cred_total": total,
        "cred_usable": len(usable),
        "base_url": p.get("base_url"),
        "enabled": bool(p.get("enabled")),
        "advice": "密钥池里有可用账号即可调用；请求字段结构在下方「模型」里配置。",
    }


# ---------------- 密钥池（一个供应商多个账号，额度用尽自动轮到下一个） ----------------

def _mask_key(k: str | None) -> str:
    k = (k or "").strip()
    if not k:
        return ""
    return f"{k[:8]}…{k[-4:]}" if len(k) > 14 else "已设置"


def _cred_out(row: dict) -> dict:
    r = dict(row)
    r["key_hint"] = _mask_key(r.pop("api_key", None))
    return r


@router.get("/providers/{provider_id}/credentials")
def list_provider_credentials(provider_id: int) -> list[dict]:
    if not db.query_one("SELECT id FROM providers WHERE id=?", (provider_id,)):
        raise HTTPException(404, "供应商不存在")
    return [_cred_out(r) for r in PE.list_credentials(provider_id, only_enabled=False)]


class CredentialIn(BaseModel):
    alias: str | None = None
    api_key: str
    enabled: bool | None = True
    sort_order: int | None = 0


def _parse_bulk(text: str, prefix: str, start: int) -> list[dict]:
    """解析批量粘贴：每行一个 key；也支持「别名,key」「别名|key」「别名<Tab>key」。"""
    items: list[dict] = []
    n = start
    for raw in str(text).splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        alias, key = "", line
        for sep in (",", "|", "\t"):
            if sep in line:
                a, b = line.split(sep, 1)
                if a.strip() and b.strip():
                    alias, key = a.strip(), b.strip()
                break
        key = key.strip().strip('"').strip("'")
        if not key:
            continue
        if not alias:
            n += 1
            alias = f"{prefix}{n}"
        items.append({"alias": alias, "api_key": key, "enabled": 1, "sort_order": 0})
    return items


@router.post("/providers/{provider_id}/credentials")
def add_provider_credentials(provider_id: int, body: dict) -> dict:
    """支持两种形态：{alias, api_key} 单条，或 {bulk:"多行文本"} 批量粘贴。"""
    if not db.query_one("SELECT id FROM providers WHERE id=?", (provider_id,)):
        raise HTTPException(404, "供应商不存在")

    existing = PE.list_credentials(provider_id, only_enabled=False)
    if body.get("bulk"):
        items = _parse_bulk(str(body["bulk"]), body.get("alias_prefix") or "账号", len(existing))
    elif body.get("api_key"):
        items = [{
            "alias": (body.get("alias") or "").strip() or f"账号{len(existing) + 1}",
            "api_key": str(body["api_key"]).strip(),
            "sort_order": int(body.get("sort_order") or 0),
            "enabled": 1 if body.get("enabled", True) else 0,
        }]
    else:
        items = []
    if not items:
        raise HTTPException(400, "没有解析到任何 key")

    added, skipped = 0, 0
    for it in items:
        dup = db.query_one(
            "SELECT id FROM provider_credentials WHERE provider_id=? AND api_key=?", (provider_id, it["api_key"])
        )
        if dup:
            skipped += 1
            continue
        db.execute(
            "INSERT INTO provider_credentials(provider_id, alias, api_key, enabled, sort_order) VALUES(?,?,?,?,?)",
            (provider_id, it["alias"], it["api_key"], it.get("enabled", 1), it.get("sort_order", 0)),
        )
        added += 1
    return {"ok": True, "added": added, "skipped": skipped}


@router.patch("/credentials/{cred_id}")
def patch_credential(cred_id: int, body: dict) -> dict:
    row = db.query_one("SELECT * FROM provider_credentials WHERE id=?", (cred_id,))
    if not row:
        raise HTTPException(404, "账号不存在")
    allowed = {"alias", "api_key", "enabled", "sort_order", "status", "cooldown_until"}
    vals: dict = {}
    for k, v in body.items():
        if k not in allowed:
            continue
        if k == "enabled":
            v = 1 if v else 0
        elif k == "status":
            if v not in ("active", "cooling", "exhausted", "invalid", "disabled"):
                raise HTTPException(400, "status 取值不合法")
            if v == "active":            # 手动恢复：顺带清掉冷却与失败计数
                vals["cooldown_until"] = None
                vals["fail_count"] = 0
                vals["last_error"] = None
        vals[k] = v
    if vals:
        cols = ", ".join(f"{k}=?" for k in vals)
        db.execute(
            f"UPDATE provider_credentials SET {cols}, updated_at=datetime('now','localtime') WHERE id=?",
            list(vals.values()) + [cred_id],
        )
    return _cred_out(db.query_one("SELECT * FROM provider_credentials WHERE id=?", (cred_id,)))


@router.delete("/credentials/{cred_id}")
def delete_credential(cred_id: int) -> dict:
    db.execute("DELETE FROM provider_credentials WHERE id=?", (cred_id,))
    return {"ok": True}


# ---------------- 零成本探测（查余额 / 验鉴权，不触发任何生成） ----------------

def _probe_credential(provider: dict, key: str, cred_id: int | None = None) -> dict:
    """按供应商 meta.probe 的配置发一个只读请求。绝不调用生成接口。"""
    meta = jloads(provider.get("meta"), {}) or {}
    spec = meta.get("probe") or {}
    if not spec.get("path"):
        return {"ok": False, "message": "该供应商未配置探测端点（meta.probe）", "skipped": True}
    base = (provider.get("base_url") or "").rstrip("/")
    path = PE.render_text(spec["path"], {})
    url = base + path if path.startswith("/") else path
    headers = PE.build_headers(provider, spec.get("headers"), key)
    import httpx

    try:
        with httpx.Client(timeout=20, follow_redirects=True) as c:
            r = c.request((spec.get("method") or "GET").upper(), url, headers=headers)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "message": f"请求异常：{e}", "url": url}
    try:
        data = r.json()
    except Exception:  # noqa: BLE001
        data = {"_text": r.text[:400]}

    ok = r.status_code < 400
    message = ""
    flat = json.dumps(data, ensure_ascii=False)[:600]
    for kw in spec.get("fail_keywords") or []:
        if kw.lower() in flat.lower():
            ok, message = False, f"命中失败特征「{kw}」"
            break
    if ok:
        for kw in spec.get("ok_keywords") or []:
            if kw.lower() in flat.lower():
                message = f"命中通过特征「{kw}」"
                break
    code = data.get("code") if isinstance(data, dict) else None
    if code is not None and str(code) not in ("0", "Success", "success", "OK", "ok"):
        # 有些平台用 body code 表达「资源不存在」，若已命中 ok_keywords 则不算失败
        if not (ok and message.startswith("命中通过特征")):
            ok, message = False, f"code={code} {data.get('message') or ''}"

    balance = None
    if spec.get("balance_path"):
        balance = PE.jp_first(data, spec["balance_path"])
    note = PE.jp_first(data, spec.get("note_path")) if spec.get("note_path") else None

    # 备注只留人看得懂的一句，原文别往库里塞
    if not message:
        message = f"HTTP {r.status_code} 正常"
    db.execute(
        "UPDATE provider_credentials SET probe_ok=?, probe_note=?, balance=COALESCE(?, balance), "
        "balance_note=?, balance_checked_at=datetime('now','localtime'), "
        "updated_at=datetime('now','localtime') WHERE id=?",
        (1 if ok else 0, message[:200], balance,
         (json.dumps(note, ensure_ascii=False)[:200] if note is not None else None),
         cred_id if cred_id is not None else -1),
    )
    return {"ok": ok, "status_code": r.status_code, "url": url, "message": message or f"HTTP {r.status_code}",
            "balance": balance, "note": note, "raw": data}


@router.post("/credentials/{cred_id}/probe")
def probe_credential(cred_id: int) -> dict:
    row = db.query_one("SELECT * FROM provider_credentials WHERE id=?", (cred_id,))
    if not row:
        raise HTTPException(404, "账号不存在")
    provider = db.query_one("SELECT * FROM providers WHERE id=?", (row["provider_id"],))
    out = _probe_credential(provider, row["api_key"], cred_id)
    out["alias"] = row["alias"]
    return out


@router.post("/providers/{provider_id}/credentials/probe-all")
def probe_all_credentials(provider_id: int) -> dict:
    provider = db.query_one("SELECT * FROM providers WHERE id=?", (provider_id,))
    if not provider:
        raise HTTPException(404, "供应商不存在")
    rows = PE.list_credentials(provider_id, only_enabled=False)
    results = []
    for r in rows:
        out = _probe_credential(provider, r["api_key"], r["id"])
        out["alias"] = r["alias"]
        out["credential_id"] = r["id"]
        results.append(out)
    return {"ok": True, "count": len(results), "results": results}


# ---------------- 成本预估（走平台免费的预估端点，不产生生成） ----------------

@router.post("/estimate")
def estimate_cost(body: dict) -> dict:
    """预估一次生成会花多少积分。不调用模型、不消耗额度。

    body: {model_id: int, params: {...}}；params 与出片参数同名（image_size / duration / …）。
    """
    mid = body.get("model_id")
    if not mid:
        raise HTTPException(400, "缺少 model_id")
    bundle = PE.load_model_bundle(int(mid))
    if not bundle:
        raise HTTPException(404, "模型不存在")
    out = PE.estimate(bundle, body.get("params") or {})
    out["model"] = bundle["model"]["name"]
    out["provider"] = bundle["provider"]["name"]
    # 顺带带上该供应商当前可用账号数，方便判断「钱够不够、号还剩几个」
    out["cred_usable"] = len(PE.usable_credentials(bundle["provider"]["id"]))
    return out


# ---------------- 模型 ----------------

@router.get("/models")
def list_models(category: str | None = None) -> list[dict]:
    sql = """SELECT m.*, p.name AS provider_name, p.key AS provider_key, p.enabled AS provider_enabled
             FROM models m LEFT JOIN providers p ON p.id=m.provider_id WHERE 1=1"""
    params: list = []
    if category:
        sql += " AND m.category=?"
        params.append(category)
    sql += " ORDER BY m.category, m.id"
    rows = db.query(sql, params)
    for r in rows:
        r["request"] = jloads(r.get("request_spec"), {}) or {}
        r["response"] = jloads(r.get("response_spec"), {}) or {}
        r["poll"] = jloads(r.get("poll_spec"), {}) or {}
        r["default_params"] = jloads(r.get("defaults"), {}) or {}
        r["param_map_obj"] = jloads(r.get("param_map"), {}) or {}
    return rows


@router.get("/models/{model_id}")
def get_model(model_id: int) -> dict:
    m = db.query_one("SELECT * FROM models WHERE id=?", (model_id,))
    if not m:
        raise HTTPException(404, "模型不存在")
    m["request"] = jloads(m.get("request_spec"), {}) or {}
    m["response"] = jloads(m.get("response_spec"), {}) or {}
    m["poll"] = jloads(m.get("poll_spec"), {}) or {}
    m["default_params"] = jloads(m.get("defaults"), {}) or {}
    m["param_map_obj"] = jloads(m.get("param_map"), {}) or {}
    return m


class ModelIn(BaseModel):
    provider_id: int
    key: str
    name: str
    category: str
    model_name: str
    remote_model_name: str | None = None
    mode: str | None = "asynchronous"
    request_kind: str | None = "http"
    request_spec: dict | None = None
    response_spec: dict | None = None
    poll_spec: dict | None = None
    defaults: dict | None = None
    param_map: dict | None = None
    enabled: bool | None = True
    notes: str | None = None


@router.post("/models")
def create_model(body: ModelIn) -> dict:
    if db.query_one("SELECT id FROM models WHERE key=?", (body.key,)):
        raise HTTPException(400, "key 已存在")
    mid = db.execute(
        """INSERT INTO models(provider_id, key, name, category, model_name, remote_model_name, mode,
               request_kind, request_spec, response_spec, poll_spec, defaults, param_map, enabled, notes)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (body.provider_id, body.key, body.name, body.category, body.model_name,
         body.remote_model_name, body.mode, body.request_kind, jdumps(body.request_spec),
         jdumps(body.response_spec), jdumps(body.poll_spec), jdumps(body.defaults),
         jdumps(body.param_map), 1 if body.enabled else 0, body.notes),
    )
    return db.query_one("SELECT * FROM models WHERE id=?", (mid,))


@router.patch("/models/{model_id}")
def patch_model(model_id: int, body: dict) -> dict:
    allowed = {"name", "category", "model_name", "remote_model_name", "mode", "request_kind",
               "request_spec", "response_spec", "poll_spec", "download_spec", "defaults",
               "param_map", "enabled", "notes"}
    vals = {}
    for k, v in body.items():
        if k not in allowed:
            continue
        if k in ("request_spec", "response_spec", "poll_spec", "download_spec", "defaults", "param_map"):
            vals[k] = jdumps(v) if not isinstance(v, str) else v
        elif k == "enabled" and isinstance(v, bool):
            vals[k] = 1 if v else 0
        else:
            vals[k] = v
    if not vals:
        raise HTTPException(400, "无可更新字段")
    cols = ", ".join(f"{k}=?" for k in vals)
    db.execute(
        f"UPDATE models SET {cols}, updated_at=datetime('now','localtime') WHERE id=?",
        list(vals.values()) + [model_id],
    )
    return get_model(model_id)


@router.delete("/models/{model_id}")
def delete_model(model_id: int) -> dict:
    db.execute("DELETE FROM models WHERE id=?", (model_id,))
    return {"ok": True}


@router.get("/model-settings")
def get_model_settings() -> list[dict]:
    out = []
    for cat in ("image", "video", "llm"):
        row = db.query_one("SELECT * FROM model_settings WHERE category=?", (cat,))
        model = db.query_one("SELECT * FROM models WHERE id=?", (row["model_id"],)) if row and row["model_id"] else None
        out.append({
            "category": cat,
            "model_id": model["id"] if model else None,
            "model_name": model["name"] if model else None,
            "options": db.query(
                "SELECT id, name, model_name FROM models WHERE category=? ORDER BY id", (cat,)
            ),
        })
    return out


@router.patch("/model-settings/{category}")
def set_model_setting(category: str, body: dict) -> dict:
    mid = body.get("model_id")
    db.execute(
        "INSERT INTO model_settings(category, model_id) VALUES(?,?) "
        "ON CONFLICT(category) DO UPDATE SET model_id=excluded.model_id, updated_at=datetime('now','localtime')",
        (category, mid),
    )
    return {"ok": True, "category": category, "model_id": mid}


# ---------------- 系统设置 ----------------

@router.get("/settings")
def list_settings(category: str | None = None, hide_secrets: bool = True) -> list[dict]:
    sql = "SELECT * FROM settings"
    params: list = []
    if category:
        sql += " WHERE category=?"
        params.append(category)
    sql += " ORDER BY category, key"
    rows = db.query(sql, params)
    if hide_secrets:
        for r in rows:
            if r["category"] == "secrets" or r["key"].startswith("provider_key:"):
                v = r.get("value") or ""
                r["value"] = (v[:6] + "…" + v[-4:]) if len(v) > 12 else ("已设置" if v else "")
                r["masked"] = True
    return rows


@router.patch("/settings")
def set_settings(body: dict) -> dict:
    """body: {key: value} 或 {items: [{key, value, category}]}"""
    items = body.get("items")
    if not items:
        items = [{"key": k, "value": v} for k, v in body.items() if k != "items"]
    for it in items:
        db.execute(
            "INSERT INTO settings(key, value, category) VALUES(?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=datetime('now','localtime')",
            (it["key"], str(it.get("value", "")), it.get("category", "general")),
        )
    return {"ok": True, "count": len(items)}


@router.get("/env-keys")
def env_keys() -> dict:
    """提示：哪些环境变量可用于注入密钥。"""
    names = [k for k in os.environ if k.startswith(("STUDIO_", "MINIMAX", "OPENAI"))]
    return {"available_env_keys": sorted(names)}
