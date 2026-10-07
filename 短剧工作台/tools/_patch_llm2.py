"""给 task_runner._run_llm 增加 outline / shot_prompts 两个落点（带断言）。"""
from __future__ import annotations

import io
import py_compile

P = r"D:\Aicomfyui\短剧工作台\backend\app\executors\task_runner.py"

src = io.open(P, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in src else "\n"
print("换行符:", repr(nl))

# 1) _run_llm 的 docstring 补上新落点说明
old_doc = nl.join([
    '    payload.save 决定落点：',
    '      "script"  → 新建 scripts 版本（整部剧本），结果带 script_id',
    '      "episode" → 写回指定集（续写单集），结果带 episode_id',
    '      缺省      → 只把文本放进任务结果，等前端人工确认后再落库（分集预览走这条）',
]) + nl
new_doc = nl.join([
    '    payload.save 决定落点：',
    '      "script"       → 新建 scripts 版本（整部剧本），结果带 script_id',
    '      "episode"      → 写回指定集（续写单集），结果带 episode_id',
    '      "outline"      → 只解析「集结构+镜头清单」放进任务结果，等人工确认后调 apply 落库',
    '      "shot_prompts" → 解析该集双份提示词，自动拼素材声明后回填到各镜头',
    '      缺省            → 只把文本放进任务结果，等前端人工确认后再落库（分集预览走这条）',
]) + nl
assert src.count(old_doc) == 1, ("docstring 锚点不唯一", src.count(old_doc))
src = src.replace(old_doc, new_doc)

# 2) 在 _run_llm 末尾（save == episode 分支之后）追加两个分支
old_tail = nl.join([
    '        out["episode_id"] = eid',
    '        out["title"] = ep["title"]',
    '    _ok(task_id, out)',
]) + nl
new_tail = nl.join([
    '        out["episode_id"] = eid',
    '        out["title"] = ep["title"]',
    '    elif save == "outline" and project_id:',
    '        _progress(task_id, 96, "解析结构化出稿…")',
    '        data = script_service.parse_outline(text)',
    '        eps = data.get("episodes") or []',
    '        out["outline"] = data',
    '        out["parsed"] = bool(data.get("_parsed"))',
    '        if data.get("_parsed"):',
    '            n_shots = sum(len(e.get("shots") or []) for e in eps)',
    '            out["note"] = f"解析出 {len(eps)} 集、{n_shots} 个镜头，等待确认后落库"',
    '        else:',
    '            out["note"] = "模型输出不是合法 JSON，请人工检查（原文已放在 outline._raw）"',
    '    elif save == "shot_prompts" and payload.get("episode_id"):',
    '        _progress(task_id, 96, "回填该集提示词…")',
    '        items = script_service.parse_shot_prompts(text)',
    '        if not items:',
    '            raise PE.ProviderError("模型输出里没有解析到任何镜头提示词",',
    '                                   stage="parse", detail=text[:800])',
    '        out.update(script_service.apply_shot_prompts(',
    '            payload["episode_id"], items, model=model_name))',
    '        out["items"] = items',
    '    _ok(task_id, out)',
]) + nl
assert src.count(old_tail) == 1, ("末尾锚点不唯一", src.count(old_tail))
src = src.replace(old_tail, new_tail)

io.open(P, "w", encoding="utf-8", newline="").write(src)
py_compile.compile(P, doraise=True)
print("task_runner.py 补丁完成，语法 OK")
print("outline 分支:", io.open(P, encoding="utf-8", newline="").read().count('save == "outline"'))
print("shot_prompts 分支:", io.open(P, encoding="utf-8", newline="").read().count('save == "shot_prompts"'))
