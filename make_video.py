#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_video.py —— Agnes-only 一键成片流水线（无需 ComfyUI / GPU）。

关键内容(文字) → ① 分镜 JSON → ② 角色参考图 → ③ 每段视频(图生视频)
               → ④ 可选 ffmpeg 拼接成片。

依赖（同目录）: agnes_llm.py / agnes_image.py / agnes_video.py / script_writer.py
本地硬依赖    : 仅 ffmpeg（可选，用于第④步拼接；没装则只产出分段 mp4 + manifest）

用法:
  # 最常用：一段关键内容直接出片
  python make_video.py --brief "主题：刺猬的早餐冒险；风格：皮克斯3D；时长：12秒；必含梗：被咖啡烫到跳起来"

  # 关键内容写在文件里
  python make_video.py --brief brief.txt --subject "皮克斯风格小刺猬" --out out/

  # 只生成分段，不拼接（ffmpeg 之后你自己接）
  python make_video.py --brief "..." --no-stitch

  # 不调 LLM，用分镜模板先跑通（仍会调 image/video 真实生成）
  python make_video.py --brief "主题：小刺猬挥手" --offline

说明:
  - 每段视频默认 81 帧 / 24fps ≈ 3.4s；会根据分镜里该镜 duration_sec 自动选最接近的合法帧数
    （合法: 81/121/161/241/281/321/361/401/441，必须 8n+1 且 ≤441）
  - 角色一致性靠「图生视频」：每段都把同一张 hero 参考图喂进去，无需 9 宫格 / 无需训练 LoRA
  - 单条视频上限约 18s（441 帧）。更长成片 = 多段拼接（第④步）
"""
import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import time

from agnes_image import generate_image, download_image
from agnes_video import generate_video, download_video
from script_writer import call_llm, offline_template

# 视频帧数约束: 8n+1 且 ≤ 441
VALID_FRAMES = [81, 121, 161, 201, 241, 281, 321, 361, 401, 441]


def frames_for_duration(dur_sec, fps):
    """按该镜时长挑最接近的合法帧数。"""
    if not dur_sec:
        return 81
    target = int(round(dur_sec * fps))
    best = min(VALID_FRAMES, key=lambda f: abs(f - target))
    return best


def infer_subject(brief, storyboard):
    """没给 --subject 时，从关键内容里猜角色词。"""
    keywords = ["刺猬", "兔子", "小猫", "猫咪", "猫", "小狗", "狗", "小熊", "熊",
                "狐狸", "老虎", "狮子", "企鹅", "熊猫", "女孩", "男孩", "少年",
                "少女", "机器人", "小恐龙", "恐龙"]
    for k in keywords:
        if k in brief:
            return f"皮克斯风格{k}"
    style = storyboard.get("style") or "皮克斯3D"
    return f"一只{style}风格的可爱主角角色"


def build_video_prompt(subject, shot, style):
    parts = [subject]
    if shot.get("action"):
        parts.append(shot["action"])
    if shot.get("angle"):
        parts.append(f"{shot['angle']}视角")
    if shot.get("scene"):
        parts.append(shot["scene"])
    parts.append(f"{style}动画风格")
    parts.append("流畅动作，高清，皮克斯3D质感，角色一致")
    return "，".join(p for p in parts if p)


def gen_with_retry(prompt, image, num_frames, frame_rate, attempts=4):
    last = None
    for i in range(1, attempts + 1):
        try:
            return generate_video(prompt, image=image,
                                  num_frames=num_frames, frame_rate=frame_rate)
        except Exception as e:
            last = e
            print(f"    [重试 {i}/{attempts}] 视频创建失败: {e}")
            time.sleep(10)
    raise last


def ffmpeg_concat(clip_paths, out_path):
    """用 ffmpeg 把分段按顺序拼成一条（统一 1088x832 / 24fps，兼容各段尺寸）。"""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False, "未检测到 ffmpeg，跳过拼接"
    list_file = os.path.join(os.path.dirname(out_path) or ".", "_concat_list.txt")
    with open(list_file, "w", encoding="utf-8") as f:
        for p in clip_paths:
            f.write(f"file '{os.path.abspath(p)}'\n")
    cmd = [
        ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", list_file,
        "-vf", "fps=24,scale=1088:832:force_original_aspect_ratio=decrease,"
               "pad=1088:832:(ow-iw)/2:(oh-ih)/2",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        out_path,
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True,
                       timeout=300)
        os.remove(list_file)
        return True, out_path
    except Exception as e:
        return False, f"ffmpeg 拼接失败: {e}"


def main():
    ap = argparse.ArgumentParser(description="Agnes-only 一键成片")
    ap.add_argument("--brief", required=True, help="关键内容：直接文本，或 @文件路径")
    ap.add_argument("--subject", default=None,
                    help="角色描述（如 '皮克斯风格小刺猬'）；不填则自动从 brief 推断")
    ap.add_argument("--out", default="output", help="输出目录（默认 ./output）")
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--no-stitch", action="store_true", help="不拼接，只产出分段 mp4")
    ap.add_argument("--offline", action="store_true",
                    help="分镜用模板（不调 LLM）；image/video 仍真实生成")
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)

    # ① 关键内容 → 分镜 JSON
    brief = a.brief
    if brief.startswith("@"):
        brief = open(brief[1:], encoding="utf-8").read()
    print("① 扩写分镜 ...")
    if a.offline:
        storyboard = offline_template(brief)
    else:
        try:
            storyboard = call_llm(brief)
        except Exception as e:
            print(f"   LLM 失败({e})，降级离线模板")
            storyboard = offline_template(brief)
    storyboard.setdefault("generated_at",
                          datetime.datetime.now().isoformat(timespec="seconds"))
    sb_path = os.path.join(a.out, "storyboard.json")
    with open(sb_path, "w", encoding="utf-8") as f:
        json.dump(storyboard, f, ensure_ascii=False, indent=2)
    style = storyboard.get("style") or "皮克斯3D"
    shots = storyboard.get("shots", [])
    print(f"   ✅ 分镜 {sb_path}（{len(shots)} 镜，风格：{style}）")

    # ② 角色参考图（hero）
    subject = a.subject or infer_subject(brief, storyboard)
    print(f"② 生成角色参考图（{subject}）...")
    hero_prompt = f"{subject}，正面全身，纯色背景，{style}动画风格，高质量，3D渲染"
    hero = generate_image(hero_prompt, size="1024x1024")
    hero_path = os.path.join(a.out, "hero.png")
    hero_url = hero.get("url")
    if hero_url:
        download_image(hero_url, hero_path)
        print(f"   ✅ 参考图 {hero_path}")
    else:
        print("   ⚠️ 参考图未返回 URL，视频将退化为纯文生视频")
        hero_path = None

    # ③ 每段视频（图生视频，喂 hero 参考图锁角色）
    print("③ 生成各分镜视频（图生视频）...")
    clips = []
    for shot in shots:
        sid = shot.get("id", len(clips) + 1)
        nframes = frames_for_duration(shot.get("duration_sec"), a.fps)
        vprompt = build_video_prompt(subject, shot, style)
        clip_path = os.path.join(a.out, f"clip_{sid:02d}.mp4")
        print(f"   - 镜头 {sid}: {nframes}帧 | {vprompt[:50]}...")
        try:
            res = gen_with_retry(vprompt, hero_url, nframes, a.fps)
        except Exception as e:
            print(f"     ❌ 镜头 {sid} 多次重试失败: {e}")
            clips.append({"id": sid, "path": None, "status": "failed",
                          "error": str(e)})
            continue
        if res.get("status") == "completed" and res.get("url"):
            download_video(res["url"], clip_path)
            clips.append({"id": sid, "path": clip_path, "status": "completed",
                          "seconds": res.get("seconds"), "size": res.get("size")})
            print(f"     ✅ {clip_path}")
        else:
            print(f"     ❌ 镜头 {sid} 状态异常: {res.get('status')}")
            clips.append({"id": sid, "path": None, "status": res.get("status"),
                          "error": res.get("error")})

    # manifest
    manifest = {
        "brief": brief,
        "subject": subject,
        "style": style,
        "hero_image": hero_path,
        "storyboard": sb_path,
        "clips": clips,
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    man_path = os.path.join(a.out, "manifest.json")
    with open(man_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # ④ 拼接（可选）
    ok_clips = [c["path"] for c in clips if c.get("path")]
    if not a.no_stitch and ok_clips:
        final_path = os.path.join(a.out, "final.mp4")
        ok, msg = ffmpeg_concat(ok_clips, final_path)
        if ok:
            print(f"④ ✅ 已拼接成片 {final_path}")
        else:
            print(f"④ {msg}（分段 mp4 已就绪，等你装 ffmpeg 再拼）")
    else:
        print(f"④ 跳过拼接：输出 {len(ok_clips)} 段 mp4 + manifest.json，"
              f"待你接 ffmpeg 后用 manifest 里的 clips 顺序拼接")

    print("\n🎬 完成。输出目录:", os.path.abspath(a.out))


if __name__ == "__main__":
    main()
