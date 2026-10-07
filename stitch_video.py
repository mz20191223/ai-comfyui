#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Step4 · 分镜拼接成片

把多段短视频拼成最终 MP4：
- ffmpeg filter_complex 做 xfade 转场（默认 fade，0.5s）
- 可选叠加字幕(srt) 与 旁白音轨(mp3/wav)

用法:
  python stitch_video.py --clips c1.mp4 c2.mp4 c3.mp4 --out final.mp4
  python stitch_video.py --clips c1.mp4 c2.mp4 --subs storyboard.srt --audio voice.mp3 --out final.mp4

依赖: ffmpeg / ffprobe 在 PATH
"""
import argparse
import json
import subprocess
import sys


def probe_duration(path: str) -> float:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", path]
    )
    return float(out.strip())


def build(clips, subs, audio, out, transition=0.5):
    n = len(clips)
    if n == 0:
        raise SystemExit("没有片段可拼")

    durations = [probe_duration(c) for c in clips]

    cmd = ["ffmpeg", "-y"]
    for c in clips:
        cmd += ["-i", c]
    if audio:
        cmd += ["-i", audio]

    # 视频滤镜链：逐对 xfade
    vfilters = []
    offset = durations[0]
    last = "[0:v]"
    for i in range(1, n):
        outlabel = f"[v{i}]" if i < n - 1 else "[vcat]"
        vfilters.append(
            f"{last}[{i}:v]xfade=transition=fade:duration={transition:.3f}:offset={offset:.3f}{outlabel}"
        )
        last = outlabel
        offset += durations[i] - transition

    vid_chain = ";".join(vfilters)

    if subs:
        vid_chain += f";[vcat]subtitles='{subs}'[vsub]"
        vmap = "[vsub]"
    else:
        vmap = "[vcat]"

    cmd += ["-filter_complex", vid_chain]
    cmd += ["-map", vmap]
    if audio:
        cmd += ["-map", f"{n}:a"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", out]

    print("▶ 运行:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    print(f"✅ 成片已写入 {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clips", nargs="+", required=True, help="各镜短片 mp4")
    ap.add_argument("--subs", default="", help="字幕 srt 路径（可选）")
    ap.add_argument("--audio", default="", help="旁白音轨（可选）")
    ap.add_argument("--out", default="final.mp4")
    ap.add_argument("--transition", type=float, default=0.5)
    a = ap.parse_args()
    build(a.clips, a.subs or None, a.audio or None, a.out, a.transition)


if __name__ == "__main__":
    main()
