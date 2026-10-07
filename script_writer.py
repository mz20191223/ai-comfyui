#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Step2 · 剧本/分镜自动扩写器

把用户的"关键内容"（主题/时长/风格/平台/必含梗/语气）扩写成可直接用于图生视频的分镜表 JSON。

用法:
  python script_writer.py --brief brief.txt --out storyboard.json
  python script_writer.py --brief "主题：刺猬的一天" --out storyboard.json
  python script_writer.py --offline --out storyboard.json   # 不调 API，写模板，便于先跑通后续

剧本扩写后端: agnes_llm.py（Agnes LLM，默认免费；改 AGNES_API_KEY 环境变量可换 key）
"""
import argparse
import datetime
import json
import os
import sys
import urllib.request

SYSTEM = """你是为 AI 漫剧/短视频做角色分镜设计的助手。
用户会给你一段"关键内容"（主题、时长、风格、平台、必含梗、语气）。
请扩写成一份可直接用于图生视频的分镜表。
要求：
- 输出严格 JSON，不要任何解释性文字、不要 markdown 代码块。
- 字段：title(片名), style(风格), duration_sec(总时长), voiceover_tone(旁白语气),
  shots: [ {id, duration_sec, angle(用 9 宫格哪个视角: front/back/left/right/three_quarter/closeup),
            camera(镜头运动: static/pan/zoom_in/zoom_out), action(角色动作),
            scene(场景/背景), mood(情绪), sfx(音效/配乐提示), narration(该镜旁白文案)} ]
- 分镜数按总时长估算，每镜 3-6 秒，所有 shots 的 duration_sec 之和应≈duration_sec。
- angle 必须从给定视角集合选，对应后续 9 宫格设定表的视角（保持一致）。"""


def call_llm(brief: str) -> dict:
    from agnes_llm import agnes_chat
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": brief},
    ]
    return agnes_chat(messages, json_mode=True, temperature=0.8, max_tokens=2048)


def offline_template(brief: str) -> dict:
    return {
        "title": "皮克斯刺猬小剧场（示例模板）",
        "style": "pixar 3d cartoon",
        "duration_sec": 18,
        "voiceover_tone": "轻松可爱",
        "shots": [
            {"id": 1, "duration_sec": 4, "angle": "front", "camera": "static",
             "action": "刺猬挥手打招呼", "scene": "浅蓝纯色背景", "mood": "开心",
             "sfx": "轻快 BGM", "narration": "大家好，我是这只圆滚滚的小刺猬！"},
            {"id": 2, "duration_sec": 4, "angle": "three_quarter", "camera": "zoom_in",
             "action": "刺猬转头微笑", "scene": "浅蓝纯色背景", "mood": "俏皮",
             "sfx": "", "narration": "今天带你们看看我的日常。"},
            {"id": 3, "duration_sec": 5, "angle": "closeup", "camera": "static",
             "action": "刺猬眨眼", "scene": "浅蓝纯色背景", "mood": "可爱",
             "sfx": "", "narration": "别看我满身刺，其实我超软乎的～"},
            {"id": 4, "duration_sec": 5, "angle": "back", "camera": "pan",
             "action": "刺猬背对镜头抖抖背刺", "scene": "浅蓝纯色背景", "mood": "得意",
             "sfx": "", "narration": "背刺可是我的小骄傲！"},
        ],
        "_note": "这是 --offline 模板，未调用 LLM。请填真实关键内容后设 LLM_API_KEY 再跑。",
        "_brief": brief,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brief", required=True, help="关键内容：直接文本，或 @文件路径")
    ap.add_argument("--out", default="storyboard.json")
    ap.add_argument("--offline", action="store_true", help="不调 API，写模板")
    a = ap.parse_args()

    brief = a.brief
    if brief.startswith("@"):
        brief = open(brief[1:], encoding="utf-8").read()

    if a.offline:
        data = offline_template(brief)
    else:
        try:
            data = call_llm(brief)
        except Exception as e:
            print(f"[script_writer] LLM 调用失败({e})，自动降级离线模板")
            data = offline_template(brief)
    data.setdefault("generated_at", datetime.datetime.now().isoformat(timespec="seconds"))
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ 分镜已写入 {a.out}（{len(data.get('shots', []))} 镜）")


if __name__ == "__main__":
    main()
