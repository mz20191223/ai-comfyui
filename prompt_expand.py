#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Step 0 · 提示词自动扩写器（文生图入口的核心）

把用户随手的简短描述（如「皮克斯质感小兔子」「可爱的小猫咪 迪士尼风」）
自动扩写成可直接喂给 ComfyUI 文生图(SDXL)的完整提示词。

两种模式：
- LLM 模式（默认，质量最好）：调 Agnes LLM（agnes-2.5-flash，自动回退 2.0-flash），
  自动把中文翻成英文结构化提示词。Key 内置在 agnes_llm.py，无需额外配置。
- 离线模式（--offline，无需联网）：关键词模板，覆盖常见风格/主体，能跑通后续

输出 JSON: { subject, subject_en, style, style_tag, positive, negative, aspect }

用法:
  python prompt_expand.py "皮克斯质感小兔子"
  python prompt_expand.py "可爱小猫咪 迪士尼风" --offline
  python prompt_expand.py "一只戴帽子的熊猫" --style pixar --out prompt.json
  (也可被其它脚本 import:  from prompt_expand import expand)

LLM 后端: agnes_llm.py（ Agnes API，默认免费；改 AGNES_API_KEY 环境变量可换 key）
"""
import argparse
import json
import os
import sys

# ---------- 离线词表（无需联网也能扩写常见输入）----------
STYLE_MAP = {
    "皮克斯": ("pixar", "pixar style, disney pixar 3d cartoon character"),
    "pixar": ("pixar", "pixar style, disney pixar 3d cartoon character"),
    "迪士尼": ("disney", "disney style 3d cartoon character"),
    "disney": ("disney", "disney style 3d cartoon character"),
    "写实": ("realistic", "photorealistic, real photo, ultra detailed"),
    "照片": ("realistic", "photorealistic, real photo, ultra detailed"),
    "realistic": ("realistic", "photorealistic, real photo, ultra detailed"),
    "动漫": ("anime", "anime style, 2d illustration, cel shaded"),
    "二次元": ("anime", "anime style, 2d illustration, cel shaded"),
    "anime": ("anime", "anime style, 2d illustration, cel shaded"),
    "黏土": ("clay", "claymation, handcrafted clay texture, stop motion"),
    "盲盒": ("blindbox", "blind box toy style, vinyl toy, collectible figure"),
    "泡泡玛特": ("blindbox", "blind box toy style, vinyl toy, collectible figure"),
    "乐高": ("lego", "lego minifigure style, plastic bricks"),
    "水彩": ("watercolor", "watercolor painting, soft brush, paper texture"),
    "油画": ("oil", "oil painting, classical brushwork"),
}

SUBJECT_MAP = {
    "小兔子": "little rabbit", "兔子": "rabbit", "兔": "rabbit",
    "刺猬": "hedgehog",
    "小猫咪": "kitten", "小猫": "kitten", "猫咪": "cat", "猫": "cat",
    "小狗": "puppy", "狗狗": "dog", "狗": "dog",
    "小猪": "piglet", "猪": "pig",
    "小熊": "bear cub", "熊": "bear",
    "龙": "dragon", "狐狸": "fox", "鹿": "deer", "企鹅": "penguin",
    "小鸡": "chick", "鸡": "chick", "老虎": "tiger cub", "狮子": "lion cub",
    "大象": "baby elephant", "熊猫": "panda", "羊": "lamb", "牛": "calf",
    "猴子": "monkey", "老鼠": "mouse", "松鼠": "squirrel", "猫头鹰": "owl",
    "机器人": "cute robot", "外星人": "alien",
    "女孩": "little girl", "男孩": "little boy", "宝宝": "baby",
}

# 风格之外的「特征词」也翻成英文，避免丢细节（如戴帽子 / 红色 / 坐姿）
FEATURE_MAP = {
    "戴帽子": "wearing a hat", "戴眼镜": "wearing glasses",
    "穿": "wearing", "穿着": "wearing", "拿": "holding", "拿着": "holding",
    "举": "raising", "抱": "hugging", "坐": "sitting", "站": "standing",
    "红色": "red", "蓝色": "blue", "粉色": "pink", "黄色": "yellow",
    "绿色": "green", "紫色": "purple", "白色": "white", "黑色": "black",
    "可爱": "cute", "胖": "chubby", "圆": "round", "大": "big", "小": "little",
}
# 主体词 + 特征词合并，按出现顺序拼成英文主体描述
TOKEN_MAP = {}
TOKEN_MAP.update(SUBJECT_MAP)
TOKEN_MAP.update(FEATURE_MAP)

NEGATIVE = ("realistic, photo, lowres, bad anatomy, extra limbs, extra ears, "
            "four ears, deformed, blurry, watermark, text, signature, "
            "multiple animals, duplicate, merged, overlapping, messy, dark, scary, "
            "pig, pig nose, snout, human, person, child")

QUALITY_SUFFIX = ("cute, round plump body, large sparkling glossy eyes, "
                  "smooth clay skin, solid pastel light blue clean background, "
                  "full body shot, centered, soft studio lighting, octane render, "
                  "8k uhd, masterpiece, best quality")


def _detect_style(text):
    for kw, (tag, eng) in STYLE_MAP.items():
        if kw.lower() in text.lower():
            return tag, eng
    return "pixar", "pixar style, disney pixar 3d cartoon character"


def _extract_subject(text):
    # 1) 去掉风格词与「的」
    s = text
    for kw in STYLE_MAP:
        s = s.replace(kw, "")
    s = s.replace("的", "")
    # 2) 按出现顺序匹配已知 token（主体优先置前，长词去重）
    occ = []
    for kw, en in TOKEN_MAP.items():
        idx = s.find(kw)
        if idx >= 0:
            occ.append((idx, kw, en))
    if occ:
        # 长词优先；短词若是已保留长词的子串则丢弃（避免 kitten+cat 重复）
        occ.sort(key=lambda x: len(x[1]), reverse=True)
        kept = []
        for idx, kw, en in occ:
            if any(kw in k2 for _, k2, _ in kept):
                continue
            kept.append((idx, kw, en))
        kept.sort(key=lambda x: x[0])  # 恢复出现顺序
        subj = [en for _, _, en in kept if en in SUBJECT_MAP.values()]
        feat = [en for _, _, en in kept if en not in SUBJECT_MAP.values()]
        parts = (subj + feat) if subj else feat
        subject_en = " ".join(parts)
        return (s.strip() or subject_en, subject_en)
    # 3) 兜底：原文（英文场景直接可用）
    return (s.strip() or "cute character", (s.strip() or "cute character"))


def offline_expand(text, style=None):
    tag, style_eng = _detect_style(text)
    if style:  # 用户强制指定风格
        for kw, (t, e) in STYLE_MAP.items():
            if style.lower() in (kw.lower(), t):
                tag, style_eng = t, e
                break
    subj_cn, subj_en = _extract_subject(text)
    positive = f"{subj_en}, {style_eng}, {QUALITY_SUFFIX}"
    return {
        "subject": subj_cn,
        "subject_en": subj_en,
        "style": tag,
        "style_tag": style_eng,
        "positive": positive,
        "negative": NEGATIVE,
        "aspect": "portrait",
        "_mode": "offline",
    }


SYSTEM = """你是一个把简短中文描述扩写成英文 AI 绘画提示词(Prompt)的助手。
用户会给你一句很随意的话，比如「皮克斯质感小兔子」「戴帽子的小猫 迪士尼风」。
请扩写成用于 SDXL 文生图的高质量英文提示词。

要求：
- 输出严格 JSON（不要 markdown、不要解释）：
  {
    "subject_en": "英文主体描述(含特征如戴帽子/颜色)",
    "style_tag": "英文风格短语(如 'pixar style, disney pixar 3d cartoon character')",
    "positive": "完整正向提示词(把 subject_en + style_tag + 质量词拼好，逗号分隔)",
    "negative": "英文负向提示词",
    "aspect": "portrait 或 square 或 landscape"
  }
- positive 要包含：主体 + 风格 + 可爱圆润身体 + 大眼睛 + 干净纯色背景 + 全身 + 柔光 + 8k + masterpiece。
- 如果用户写了风格词(皮克斯/迪士尼/写实/动漫)，务必体现在 style_tag 与 positive。
- 中文主体要准确翻成英文。"""


def llm_expand(text, style=None):
    from agnes_llm import agnes_chat
    user_msg = text
    if style:
        user_msg += f"\n（指定风格：{style}）"
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user_msg},
    ]
    obj = agnes_chat(messages, json_mode=True, temperature=0.7, max_tokens=2048)
    obj["_mode"] = "llm-agnes"
    obj.setdefault("aspect", "portrait")
    obj.setdefault("negative", NEGATIVE)
    obj.setdefault("subject_en", obj.get("positive", text).split(",")[0])
    obj.setdefault("style_tag", "")
    obj.setdefault("subject", text)
    return obj


def expand(text, style=None, offline=False):
    """统一入口：返回扩写后的 dict。"""
    if offline:
        return offline_expand(text, style)
    try:
        return llm_expand(text, style)
    except SystemExit:
        raise
    except Exception as e:
        print(f"[prompt_expand] LLM 调用失败({e})，自动降级离线模板")
        return offline_expand(text, style)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("text", help="用户的简短描述，如『皮克斯质感小兔子』")
    ap.add_argument("--style", help="强制风格: pixar/disney/realistic/anime/clay/blindbox ...")
    ap.add_argument("--offline", action="store_true", help="不调 API，用模板扩写")
    ap.add_argument("--out", help="把结果写成 JSON 文件")
    a = ap.parse_args()

    obj = expand(a.text, style=a.style, offline=a.offline)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        print(f"✅ 扩写结果已写入 {a.out}")
    else:
        print(json.dumps(obj, ensure_ascii=False, indent=2))
    # 顺手打印可直接复制的正向提示词，方便调试
    print("\n--- 正向提示词(可直接用) ---\n" + obj["positive"])


if __name__ == "__main__":
    main()
