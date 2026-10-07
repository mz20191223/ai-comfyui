#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_sample.py —— 开机后一键跑「刺猬 3 场景小样」验证 Phantom 架构。

流程：
  1. 探测 HAI 环境（Phantom 节点 + 模型是否就绪；缺则提示先跑 hai_phantom_setup.sh）
  2. 按 sample_shots.json 逐镜调用 gen_phantom_clip.py 出片 → clips/<id>.mp4
  3. 调 stitch_video.py 把各镜拼成 final.mp4（xfade 转场）

用法：
  python run_sample.py --host http://<HAI_IP>:6889
  python run_sample.py --host http://<HAI_IP>:6889 --dry-run     # 只核对，不出片
  python run_sample.py --host http://<HAI_IP>:6889 --plan sample_shots.json --out hedgehog_sample.mp4
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="http://43.155.214.240:6889")
    ap.add_argument("--plan", default=os.path.join(HERE, "sample_shots.json"))
    ap.add_argument("--out", default="hedgehog_sample.mp4")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    with open(a.plan, "r", encoding="utf-8") as f:
        plan = json.load(f)

    g = plan.get("global", {})
    shots = plan.get("shots", [])
    if not shots:
        print("!! plan 里没有 shots")
        sys.exit(1)

    clips = []
    for shot in shots:
        sid = shot["id"]
        refs = [r if os.path.isabs(r) else os.path.join(HERE, r) for r in shot["refs"]]
        out_mp4 = os.path.join(HERE, "clips", f"{sid}.mp4")
        os.makedirs(os.path.dirname(out_mp4), exist_ok=True)
        cmd = [
            sys.executable, os.path.join(HERE, "gen_phantom_clip.py"),
            "--host", a.host,
            "--refs", *refs,
            "--prompt", shot["prompt"],
            "--neg", shot.get("neg", ""),
            "--out", out_mp4,
            "--width", str(shot.get("width", g.get("width", 832))),
            "--height", str(shot.get("height", g.get("height", 480))),
            "--frames", str(shot.get("frames", g.get("frames", 33))),
            "--fps", str(shot.get("fps", g.get("fps", 16))),
            "--steps", str(shot.get("steps", g.get("steps", 30))),
            "--cfg", str(shot.get("cfg", g.get("cfg", 5.0))),
            "--phantom-cfg", str(shot.get("phantom_cfg", g.get("phantom_cfg", 5.0))),
        ]
        if a.dry_run:
            cmd.append("--dry-run")
        print(f"\n===== 镜头 {sid}（{shot.get('scene','')}）=====")
        rc = subprocess.run(cmd)
        if rc.returncode != 0:
            print(f"!! 镜头 {sid} 失败，停止")
            sys.exit(rc.returncode)
        if not a.dry_run:
            clips.append(out_mp4)

    if a.dry_run:
        print("\n[DRY-RUN] 各镜工作流已打印，未出片。去掉 --dry-run 真跑。")
        return

    # 拼接成片
    print("\n===== 拼接成片 =====")
    stitch = [
        sys.executable, os.path.join(HERE, "stitch_video.py"),
        "--clips", *clips,
        "--out", os.path.join(HERE, a.out),
        "--transition", "0.5",
    ]
    rc = subprocess.run(stitch)
    if rc.returncode == 0:
        print(f"\n✅ 小样成片: {os.path.join(HERE, a.out)}")
    else:
        print("!! 拼接失败（可能本机无 ffmpeg；可把 clips/ 拷到有线 ffmpeg 的环境拼）")


if __name__ == "__main__":
    main()
