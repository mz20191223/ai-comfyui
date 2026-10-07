"""三家真实平台的默认配置（种子数据）。

依据（全部来自官方文档，非猜测）：
- 剧本 → DeepSeek       https://api-docs.deepseek.com/zh-cn/
- 资产图 → ListenHub     https://listenhub.app/docs/zh/openapi/api-reference/image-generation
- 视频 → AutoDL ComfyUI  https://autodl.art/docs/comfyui_api/

配音不在这里：音频是「镜头视频配置时挂上的素材」，随 ref_audio_* 直接交给视频模型，
工作台不承担配音生成，因此没有 tts 类供应商/模型。

幂等：按 key 覆盖更新，重复执行安全；不会覆盖用户在界面上改过的账号（按 api_key 去重）。
"""
from __future__ import annotations
import os


from ..core import db
from ..core.db import jdumps

# 这些是早期的占位配置，用户填了真实平台后就不再需要
PLACEHOLDERS = ("img-default", "vid-oldplat")
# 已废弃：曾把 Edge TTS 当成「本地执行供应商」，现改为一律挂音频素材
RETIRED = ("local-tts",)

PROVIDERS: list[dict] = [
    {
        "key": "deepseek",
        "name": "DeepSeek · 剧本与文本",
        "capabilities": ["llm"],
        "base_url": "https://api.deepseek.com",
        "auth_header": "Authorization",
        "auth_scheme": "Bearer",
        "concurrency": 2,
        "timeout_sec": 600,
        "retry": 1,
        "meta": {
            "vendor": "DeepSeek",
            "doc": "https://api-docs.deepseek.com/zh-cn/",
            "probe": {
                "method": "GET",
                "path": "/models",
                "note_path": "$.data[*].id",
                "ok_keywords": ["deepseek-flash", "deepseek-v4-pro"],
                "fail_keywords": ["invalid api key", "authentication", "insufficient balance"],
            },
            "note": "model 请发 deepseek-flash；DeepSeek-V4.1-Flash 是服务端展示名，不是请求参数。",
            "verified": "2026-09-15 实测：key 有效，可用模型 = deepseek-flash / deepseek-v4-pro。",
        },
    },
    {
        "key": "listenhub",
        "name": "ListenHub · GPT-Image-2.5（多账号轮换）",
        "capabilities": ["image"],
        "base_url": "https://api.marswave.ai/openapi",
        "auth_header": "Authorization",
        "auth_scheme": "Bearer",
        "concurrency": 3,
        "timeout_sec": 900,
        "retry": 1,
        "meta": {
            "vendor": "ListenHub / MarsWave",
            "doc": "https://listenhub.app/docs/zh/openapi/quick-start",
            "probe": {
                "method": "GET",
                "path": "/v1/user/subscription",
                "balance_path": "$.data.totalAvailableCredits",
                "note_path": "$.data",
            },
            "estimate": {
                "method": "POST",
                "path": "/v1/images/generation/estimate-credits",
                "credits_path": "$.data.credits",
                "balance_needed_path": "$.data.canGenerate",
            },
            "note": "HTTP 恒 200，错误看 body code：26004 积分不足 / 29998 限流(3 RPM) / 21007 Key 无效。",
            "quota_codes": [26004, 29998, 21007],
            "verified": "2026-09-15 实测：5 个账号全部有效，余额 65/20/25/21/25 积分。",
        },
    },
    {
        "key": "autodl-h3",
        "name": "AutoDL ComfyUI · MiniMax H3（视频）",
        "capabilities": ["video"],
        "base_url": "https://autodl.art",
        "auth_header": "Authorization",
        "auth_scheme": "",          # 官方示例是裸 token，不带 Bearer
        "concurrency": 2,
        "timeout_sec": 1800,
        "retry": 1,
        "meta": {
            "vendor": "AutoDL ComfyUI",
            "doc": "https://autodl.art/docs/comfyui_api/",
            "probe": {
                "method": "GET",
                "path": "/api/v1/comfyui/comfyui_workflow/result/00000000-0000-0000-0000-000000000000",
                "ok_keywords": ["工作流不可用", "不存在", "not found", "Success"],
                "fail_keywords": ["Invalid authentication", "unauthorized", "鉴权失败", "无效的"],
            },
            "note": "ref_image_* / ref_audio_* 只收公网 URL；本地素材需先变成可访问地址。",
            "verified": "2026-09-15 实测：无鉴权头 → 401；裸 token 与 Bearer token 均通过"
                        "（返回『工作流不可用』= 鉴权已过、假任务不存在）。两种头都可用。",
        },
    },
]

_IMG_BODY = """{
  "provider": "openai",
  "model": "{{ model }}",
  "prompt": {{ prompt | tojson }}{% if ref_images %},
  "referenceImages": [{% for img in ref_images_b64 %}
    {"inlineData": {"data": {{ img.data | tojson }}, "mimeType": "{{ img.mime_type }}"}}{% if not loop.last %},{% endif %}{% endfor %}
  ]{% endif %},
  "imageConfig": {
    "imageSize": "{{ image_size }}",
    "aspectRatio": "{{ aspect_ratio }}",
    "quality": "{{ quality }}"
  }
}"""

_H3_BODY = """{
  "prompt": {{ prompt | tojson }},
  "duration": {{ duration }},
  "resolution": "{{ resolution }}"{% if seed is defined and seed %},
  "seed": {{ seed }}{% endif %}{% for a in ref_audios %},
  "ref_audio_{{ loop.index0 }}": {{ a | tojson }}{% endfor %}{% for i in ref_images %},
  "ref_image_{{ loop.index0 }}": {{ i | tojson }}{% endfor %}
}"""

_LLM_BODY = """{
  "model": "{{ model }}",
  "messages": {{ messages | tojson }},
  "temperature": {{ temperature }},
  "max_tokens": {{ max_tokens }},
  "stream": false
}"""

MODELS: list[dict] = [
    {
        "key": "deepseek-script",
        "provider_key": "deepseek",
        "name": "DeepSeek-V4.1-Flash · 剧本/文本生成",
        "category": "llm",
        "model_name": "deepseek-flash",
        "mode": "synchronous",
        "request_spec": {
            "method": "POST",
            "path": "/chat/completions",
            "headers": {"Content-Type": "application/json"},
            "body": _LLM_BODY,
        },
        "response_spec": {"text": ["$.choices[0].message.content"]},
        "defaults": {"temperature": 0.75, "max_tokens": 8192},
        "notes": "OpenAI 兼容。取 choices[0].message.content。旧名 deepseek-v4-flash 仍可调用，"
                 "但已由 DeepSeek-V4.1-Flash 提供服务。",
    },
    {
        "key": "gpt-image-25-async",
        "provider_key": "listenhub",
        "name": "GPT-Image-2.5 Flare · 异步出图（资产跑量，推荐）",
        "category": "image",
        "model_name": "gpt-image-2.5-flare",
        "mode": "asynchronous",
        "request_spec": {
            "method": "POST",
            "path": "/v1/images/generation/async",
            "headers": {"Content-Type": "application/json"},
            "body": _IMG_BODY,
        },
        "response_spec": {"task_id": "$.data.taskId"},
        "poll_spec": {
            "path": "/v1/images/generation/tasks/{{ task_id }}",
            "interval_sec": 4,
            "timeout_sec": 900,
            "status_field": "$.data.status",
            "success_values": ["success", "succeeded"],
            "fail_values": ["failed", "fail"],
            "result_images": "$.data.images[*].url",
        },
        "defaults": {"image_size": "1K", "aspect_ratio": "9:16", "quality": "medium"},
        "notes": "参考图走 inlineData（base64 内联），本地文件无需上传。"
                 "2026-09-15 实测：模型串被接受；1K 竖屏 4 积分 / 2K 6 积分；quality 参数会被服务端忽略。",
    },
    {
        "key": "gpt-image-25-sunburst",
        "provider_key": "listenhub",
        "name": "GPT-Image-2.5 Sunburst · 异步出图（精修/改脸）",
        "category": "image",
        "model_name": "gpt-image-2.5-sunburst",
        "mode": "asynchronous",
        "request_spec": {
            "method": "POST",
            "path": "/v1/images/generation/async",
            "headers": {"Content-Type": "application/json"},
            "body": _IMG_BODY,
        },
        "response_spec": {"task_id": "$.data.taskId"},
        "poll_spec": {
            "path": "/v1/images/generation/tasks/{{ task_id }}",
            "interval_sec": 4,
            "timeout_sec": 900,
            "status_field": "$.data.status",
            "success_values": ["success", "succeeded"],
            "fail_values": ["failed", "fail"],
            "result_images": "$.data.images[*].url",
        },
        "defaults": {"image_size": "1K", "aspect_ratio": "9:16", "quality": "medium"},
        "notes": "细节更密的变体，用于定妆/改脸等需要精确编辑的场合。"
                 "2026-09-15 实测：模型串被接受，计费与 Flare 相同（1K=4 / 2K=6 积分）。",
    },
    {
        "key": "gpt-image-25-sync",
        "provider_key": "listenhub",
        "name": "GPT-Image-2.5 Flare · 同步出图（直接拿 base64）",
        "category": "image",
        "model_name": "gpt-image-2.5-flare",
        "mode": "synchronous",
        "request_spec": {
            "method": "POST",
            "path": "/v1/images/generation",
            "headers": {"Content-Type": "application/json"},
            "body": _IMG_BODY,
        },
        "response_spec": {"images": ["$.candidates[*].content.parts[*].inlineData.data"]},
        "defaults": {"image_size": "1K", "aspect_ratio": "9:16", "quality": "medium"},
        "notes": "同步返回 base64，无响应信封。异步版更省事，除非需要立刻拿到图。",
    },
    {
        "key": "h3-i2va-multiref",
        "provider_key": "autodl-h3",
        "name": "MiniMax H3 · 多图参考（接口A）",
        "category": "video",
        "model_name": "minimax-h3",
        "mode": "asynchronous",
        "request_spec": {
            "method": "POST",
            "path": "/api/v1/comfyui/comfyui_workflow/minimax_h3_image_audio_to_video_v2",
            "headers": {"Content-Type": "application/json"},
            "body": _H3_BODY,
        },
        "response_spec": {"task_id": "$.data.task_id"},
        "poll_spec": {
            "path": "/api/v1/comfyui/comfyui_workflow/result/{{ task_id }}",
            "interval_sec": 10,
            "timeout_sec": 1800,
            "status_field": "$.data.status",
            "success_values": ["SUCCESS", "completed", "success"],
            "fail_values": ["FAILED", "failed"],
            "result_videos": "$.data.results[*].url",
            "result_images": "$.data.results[*].url",
        },
        "defaults": {"resolution": "768p竖", "duration": 5, "transport": "url"},
        "notes": "接口A：动态过程用（雾涌/回头）。ref_image_0..8 / ref_audio_0..2 必须是公网 URL，"
                 "工作台不会把本地文件传上去。结果 URL 有效期很短，必须立刻下载。",
    },
]

# ListenHub 5 个账号（用户从「相关平台和账密」表提供）
# ListenHub 多账号：读环境变量 LISTENHUB_KEYS（英文逗号分隔），不写明文 key
LISTENHUB_KEYS = [k.strip() for k in os.environ.get("LISTENHUB_KEYS", "").split(",") if k.strip()]

# 单账号 key：读环境变量，缺失即为空；明文 key 切勿入库（见 SETUP.md / 账密表）
SINGLE_KEYS = {
    "deepseek": (os.environ.get("DEEPSEEK_KEY", ""), "主号"),
    "autodl-h3": (os.environ.get("AUTODL_H3_TOKEN", ""), "AutoDL令牌"),
}

DEFAULT_ASSIGN = {
    "llm": "deepseek-script",
    "image": "gpt-image-25-async",
    "video": "h3-i2va-multiref",
}


def _upsert_provider(p: dict) -> int:
    vals = {
        "name": p["name"],
        "capabilities": jdumps(p["capabilities"]),
        "base_url": p["base_url"],
        "auth_header": p["auth_header"],
        "auth_scheme": p["auth_scheme"],
        "concurrency": p["concurrency"],
        "timeout_sec": p["timeout_sec"],
        "retry": p["retry"],
        "meta": jdumps(p["meta"]),
    }
    row = db.query_one("SELECT id FROM providers WHERE key=?", (p["key"],))
    if row:
        cols = ", ".join(f"{k}=?" for k in vals)
        db.execute(
            f"UPDATE providers SET {cols}, enabled=1, updated_at=datetime('now','localtime') WHERE id=?",
            list(vals.values()) + [row["id"]],
        )
        return row["id"]
    keys = ", ".join(vals)
    marks = ", ".join("?" for _ in vals)
    return db.execute(f"INSERT INTO providers(key, {keys}, enabled) VALUES(?, {marks}, 1)",
                      [p["key"], *vals.values()])


def _upsert_model(m: dict, provider_id: int) -> None:
    vals = {
        "provider_id": provider_id,
        "name": m["name"],
        "category": m["category"],
        "model_name": m["model_name"],
        "mode": m["mode"],
        "request_kind": m.get("request_kind", "http"),
        "request_spec": jdumps(m["request_spec"]),
        "response_spec": jdumps(m.get("response_spec")),
        "poll_spec": jdumps(m.get("poll_spec")),
        "defaults": jdumps(m.get("defaults")),
        "param_map": jdumps(m.get("param_map")),
        "enabled": 1,
        "notes": m.get("notes"),
    }
    row = db.query_one("SELECT id FROM models WHERE key=?", (m["key"],))
    if row:
        cols = ", ".join(f"{k}=?" for k in vals)
        db.execute(
            f"UPDATE models SET {cols}, updated_at=datetime('now','localtime') WHERE id=?",
            list(vals.values()) + [row["id"]],
        )
        return
    keys = ", ".join(vals)
    marks = ", ".join("?" for _ in vals)
    db.execute(f"INSERT INTO models(key, {keys}) VALUES(?, {marks})", [m["key"], *vals.values()])


def _add_credential(provider_id: int, alias: str, key: str, order: int) -> bool:
    """新增账号；已存在（同 provider 同 key）则只更新别名与排序，不覆盖用户在界面上的状态。"""
    dup = db.query_one(
        "SELECT id FROM provider_credentials WHERE provider_id=? AND api_key=?", (provider_id, key)
    )
    if dup:
        db.execute(
            "UPDATE provider_credentials SET alias=?, sort_order=?, enabled=1, "
            "updated_at=datetime('now','localtime') WHERE id=?",
            (alias, order, dup["id"]),
        )
        return False
    db.execute(
        "INSERT INTO provider_credentials(provider_id, alias, api_key, sort_order) VALUES(?,?,?,?)",
        (provider_id, alias, key, order),
    )
    return True


def remove_placeholders() -> int:
    """删除早期占位 + 已废弃的供应商（models/credentials 靠外键 CASCADE 一并清掉）。"""
    n = 0
    for k in (*PLACEHOLDERS, *RETIRED):
        row = db.query_one("SELECT id FROM providers WHERE key=?", (k,))
        if row:
            db.execute("DELETE FROM providers WHERE id=?", (row["id"],))
            n += 1
    # 配音不再是生成能力：清掉遗留的 tts 默认分配，避免 UI 指向已删模型
    db.execute("DELETE FROM model_settings WHERE category='tts'")
    return n


def _repair_assignments() -> int:
    """修复指向已不存在模型的默认分配（占位供应商被清理后会留下悬空 model_id）。"""
    n = 0
    for cat, mkey in DEFAULT_ASSIGN.items():
        row = db.query_one("SELECT model_id FROM model_settings WHERE category=?", (cat,))
        target = db.query_one("SELECT id FROM models WHERE key=?", (mkey,))
        if not target:
            continue
        if row and row["model_id"] == target["id"]:
            continue
        if row:   # 悬空或指向老模型 → 修正
            db.execute(
                "UPDATE model_settings SET model_id=?, updated_at=datetime('now','localtime') "
                "WHERE category=?",
                (target["id"], cat),
            )
        else:
            db.execute("INSERT INTO model_settings(category, model_id) VALUES(?,?)", (cat, target["id"]))
        n += 1
    return n


def seed_platforms(with_credentials: bool = True) -> dict:
    """写入三家真实平台 + 默认模型分配（幂等，可反复调用）。"""
    stats = {"providers": 0, "models": 0, "credentials": 0, "removed": 0, "fixed_assign": 0}
    stats["removed"] = remove_placeholders()

    pids: dict[str, int] = {}
    for p in PROVIDERS:
        existed = db.query_one("SELECT id FROM providers WHERE key=?", (p["key"],))
        pids[p["key"]] = _upsert_provider(p)
        if not existed:
            stats["providers"] += 1

    for m in MODELS:
        existed = db.query_one("SELECT id FROM models WHERE key=?", (m["key"],))
        _upsert_model(m, pids[m["provider_key"]])
        if not existed:
            stats["models"] += 1

    if with_credentials:
        for i, k in enumerate(LISTENHUB_KEYS, start=1):
            if _add_credential(pids["listenhub"], f"账号{i}", k, i):
                stats["credentials"] += 1
        for pk, (key, alias) in SINGLE_KEYS.items():
            if _add_credential(pids[pk], alias, key, 0):
                stats["credentials"] += 1

    stats["fixed_assign"] = _repair_assignments()
    return stats
