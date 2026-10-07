# -*- coding: utf-8 -*-
"""给 task_runner.py 接上大模型任务（CRLF 文件，用字节级替换，每处断言唯一）。"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

P = r"D:\Aicomfyui\短剧工作台\backend\app\executors\task_runner.py"
src = open(P, encoding="utf-8", newline="").read()
orig = src
CRLF = "\r\n"


def sub(old, new, tag):
    global src
    hit = src.count(old)
    print(f"[{tag}] 命中 {hit} 处")
    if hit != 1:
        print(f"  !! 中止：期望 1 处，实际 {hit} 处")
        sys.exit(1)
    src = src.replace(old, new)


# 1) import 补 script_service
sub(
    "from ..services import file_store, hooks_service, naming, shot_service",
    "from ..services import file_store, hooks_service, naming, script_service, shot_service",
    "import",
)

# 2) _run 分派加 llm_generation
sub(
    '        elif kind == "image_generation":' + CRLF + "            _run_image(task_id, payload)",
    '        elif kind == "image_generation":' + CRLF
    + "            _run_image(task_id, payload)" + CRLF
    + '        elif kind == "llm_generation":' + CRLF
    + "            _run_llm(task_id, payload)",
    "dispatch",
)

# 3) 在 _numbered 之前插入 _run_llm
anchor = "def _numbered(name: str, i: int) -> str:"
RUN_LLM = '''def _run_llm(task_id: int, payload: dict) -> None:
    """大模型文本生成（剧本 / 智能分集 / 单集续写）。

    payload.save 决定落点：
      "script"  → 新建 scripts 版本（整部剧本），结果带 script_id
      "episode" → 写回指定集（续写单集），结果带 episode_id
      缺省      → 只把文本放进任务结果，等前端人工确认后再落库（分集预览走这条）
    """
    messages = payload.get("messages") or []
    if not messages:
        raise PE.ProviderError("缺少 messages（提示词）", stage="params")
    bundle = PE.load_model_bundle(payload.get("model_id"), "llm")
    params: dict = {"messages": messages}
    if payload.get("temperature") is not None:
        params["temperature"] = payload["temperature"]
    if payload.get("max_tokens"):
        params["max_tokens"] = payload["max_tokens"]

    _progress(task_id, 6, "提交大模型…")
    res = PE.execute(bundle, params, progress=lambda p, n: _progress(task_id, p, n, mark_running=True))
    text = (res.text or "").strip()
    if not res.ok or not text:
        raise PE.ProviderError(res.error or "大模型未返回文本", stage="generate", detail=res.raw)

    model_name = bundle["model"]["name"]
    out: dict = {"text": text, "chars": len(text), "model": model_name, "note": "生成完成"}
    save = payload.get("save")
    project_id = payload.get("project_id")

    if save == "script" and project_id:
        _progress(task_id, 96, "写入剧本版本…")
        doc = script_service.parse_script_doc(text)
        out["script_id"] = script_service.save_script(
            project_id,
            doc["body"],
            title=payload.get("title") or doc["title"] or None,
            prompt_used=payload.get("prompt_used"),
            source="ai",
            meta={"model": model_name, "logline": doc["logline"]},
        )
        out["title"] = doc["title"]
        out["logline"] = doc["logline"]
    elif save == "episode" and payload.get("episode_id"):
        _progress(task_id, 96, "写回该集…")
        ep = script_service.parse_single_episode(text)
        eid = payload["episode_id"]
        db.execute(
            """UPDATE episodes SET
                   title=COALESCE(NULLIF(?,''), title),
                   synopsis=COALESCE(NULLIF(?,''), synopsis),
                   script_text=?, updated_at=datetime('now','localtime')
               WHERE id=?""",
            (ep["title"], ep["synopsis"], ep["script"], eid),
        )
        out["episode_id"] = eid
        out["title"] = ep["title"]
    _ok(task_id, out)


'''
sub(anchor, RUN_LLM.replace("\n", CRLF) + anchor, "insert _run_llm")

if src == orig:
    print("未发生任何修改")
    sys.exit(1)
open(P, "w", encoding="utf-8", newline="").write(src)
print("已写入，新增 %d 字节" % (len(src) - len(orig)))

import ast

ast.parse(open(P, encoding="utf-8").read())
print("语法检查通过")
