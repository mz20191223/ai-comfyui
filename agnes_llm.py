#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Agnes LLM API 客户端 —— OpenAI 兼容 Chat Completions。

基础地址 : https://apihub.agnes-ai.com/v1
模型     : agnes-2.5-flash（灰度首选） -> agnes-2.0-flash（稳定回退）
费用     : 当前免费（输入/输出均 $0 / 1M tokens），无需银行卡

用法:
  from agnes_llm import agnes_chat
  text = agnes_chat([{"role": "user", "content": "你好"}])
  obj  = agnes_chat(messages, json_mode=True)   # 直接返回解析后的 dict

说明:
  - API Key 默认读取环境变量 AGNES_API_KEY，未设置时回退到下方常量（来自用户共享）。
    ⚠️ 该常量仅为了方便跨机器直接跑通；若要把本项目推到公开仓库，
       请改用环境变量 AGNES_API_KEY，不要把明文 key 提交进 git。
  - json_mode=True 时要求模型返回严格 JSON，本函数会自动剥离 ```json 代码块并容错解析。
  - 灰度模型不可用时自动回退 agnes-2.0-flash。
"""
import json
import os
import urllib.error
import urllib.request

# ⚠️ 明文 key 仅作便利默认；推到公开仓库前请改用环境变量 AGNES_API_KEY 并删掉此常量。
AGNES_API_KEY = os.environ.get(
    "AGNES_API_KEY",
    """",
)
BASE_URL = os.environ.get("AGNES_BASE_URL", "https://apihub.agnes-ai.com/v1").rstrip("/")
CHAT_ENDPOINT = "/chat/completions"
PRIMARY_MODEL = "agnes-2.5-flash"
FALLBACK_MODEL = "agnes-2.0-flash"


def agnes_chat(messages, model=None, temperature=0.7, max_tokens=2048,
               json_mode=False, timeout=120):
    """调用 Agnes Chat Completions。

    messages : [{"role": "system"/"user"/"assistant", "content": ...}]
    返回     : 文本字符串；json_mode=True 时返回解析后的 dict（解析失败抛错）。
    行为     : 不指定 model 时依次尝试 2.5-flash -> 2.0-flash（灰度不可用自动回退）。
    """
    models = [model] if model else [PRIMARY_MODEL, FALLBACK_MODEL]
    last_err = None
    for m in models:
        body = {
            "model": m,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            # 关闭思考链，避免 reasoning token 把 max_tokens 吃光导致 content 为空
            "chat_template_kwargs": {"enable_thinking": False},
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            BASE_URL + CHAT_ENDPOINT,
            data=data,
            headers={
                "Authorization": f"Bearer {AGNES_API_KEY}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                resp = json.loads(r.read().decode("utf-8"))
            content = resp["choices"][0]["message"]["content"]
            return _extract_json(content) if json_mode else content
        except urllib.error.HTTPError as e:
            last_err = e
            detail = ""
            try:
                detail = e.read().decode("utf-8", "ignore")
            except Exception:
                pass
            # 灰度模型 2.5 不可用（400/403/404 报 model 缺失, 或 503 路由不可用）-> 回退 2.0
            if (m != FALLBACK_MODEL and e.code in (400, 403, 404, 503)
                    and ("model" in detail.lower()
                         or "not available" in detail.lower()
                         or "agnes-2.5" in detail.lower()
                         or e.code == 503)):
                print(f"[agnes_llm] {m} 暂不可用（HTTP {e.code}），回退 {FALLBACK_MODEL}")
                continue
            raise
        except Exception as e:  # 网络/解析等其它异常
            last_err = e
            raise
    if last_err:
        raise last_err


def _extract_json(text):
    """从模型回复中解析 JSON：兼容 ```json 代码块包裹，并容错截取首尾大括号。"""
    if not isinstance(text, str):
        return text
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t.lower().startswith("json"):
            t = t[4:]
        t = t.strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        s, e = t.find("{"), t.rfind("}")
        if s != -1 and e != -1 and e > s:
            return json.loads(t[s:e + 1])
        raise


if __name__ == "__main__":
    print(agnes_chat([{"role": "user", "content": "用一句话介绍你自己。"}]))
