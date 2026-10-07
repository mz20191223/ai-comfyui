"""run_bailian_sample.py — 编排某行(默认 r1)的相邻格→wan2.7-i2v 视频段→ffmpeg 拼接成连续镜头。

这是"选项2"的主验证脚本：25 宫格相邻两格当首尾帧 → 生成过渡视频段 → 拼接。
依赖 gen_bailian_clip.py（导入其上传/提交/轮询/下载函数）。

用法:
  python run_bailian_sample.py --key "sk-xxx" --row r1 --duration 4
  python run_bailian_sample.py --key "sk-xxx" --row all   # 全部 5 行

输出:
  clips/{row}_c1_c2.mp4 ... 各段
  {row}_scene.mp4            该行拼接后的连续镜头
"""
import argparse, json, os, sys, subprocess, shutil
import gen_bailian_clip as C

# 与 gen_bailian_storyboard.py 保持一致的风格锚
ANCHOR = "皮克斯3D动画电影风格，明亮饱和色彩，干净构图，体积光，柔和阴影，迪士尼质感，可爱圆润造型，电影级光影"


def get_ffmpeg():
    s = shutil.which("ffmpeg")
    if s:
        return s
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def gen_clip(key, first, last, prompt, duration, out):
    if os.path.exists(out) and os.path.getsize(out) > 0:
        print(f"  跳过已存在 {out}")
        return True
    fu = C.upload_image(key, first)
    lu = C.upload_image(key, last)
    tid = C.submit(key, fu, lu, prompt, duration)
    vurl = C.wait_task(key, tid)
    C.download(vurl, out)
    return True


def concat_ffmpeg(clips, out, tw=720, th=1280):
    """用 filter_complex 把各段统一缩放到竖屏(默认720x1280)后拼接；比 concat 解复用器更稳，且避开 ffmpeg 非 UTF-8 输出解码坑。"""
    ff = get_ffmpeg()
    if not ff:
        print("WARN: 找不到 ffmpeg，无法拼接"); return False
    if not clips:
        return False
    n = len(clips)
    ins = []
    for c in clips:
        ins += ["-i", c]
    filt = []
    for i in range(n):
        filt.append(f"[{i}:v]scale={tw}:{th}:force_original_aspect_ratio=decrease,"
                    f"pad={tw}:{th}:(ow-iw)/2:(oh-ih)/2,setsar=1[v{i}]")
    concat_part = "".join(f"[v{i}]" for i in range(n))
    filt.append(f"{concat_part}concat=n={n}:v=1[v]")
    fc = ";".join(filt)
    cmd = [ff, "-y"] + ins + ["-filter_complex", fc, "-map", "[v]",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", out]
    r = subprocess.run(cmd, capture_output=True)  # 不指定 text，避免 ffmpeg 非 UTF-8 输出解码报错
    if r.returncode != 0:
        print("WARN: concat 失败")
        return False
    return True


def process_row(key, row_key, duration, grid, clips_dir):
    cfg = json.load(open("storyboard_25grid.json", encoding="utf-8"))
    rows = {r["key"]: r for r in cfg["rows"]}
    cols = cfg["cols"]
    row = rows[row_key]
    scene = row["scene"]
    os.makedirs(clips_dir, exist_ok=True)
    clips = []
    for i in range(len(cols) - 1):
        c0, c1 = cols[i], cols[i + 1]
        first = f"{grid}/{row_key}_{c0['key']}.png"
        last = f"{grid}/{row_key}_{c1['key']}.png"
        out = f"{clips_dir}/{row_key}_{c0['key']}_{c1['key']}.mp4"
        prompt = (f"{ANCHOR}。{scene}。"
                  f"{c0['shot']} 平滑运动过渡到 {c1['shot']}，"
                  f"保持角色一致、皮克斯3D动画电影质感、明亮饱和色彩。")
        print(f"[clip] {row_key}: {c0['key']} -> {c1['key']}")
        gen_clip(key, first, last, prompt, duration, out)
        clips.append(out)
    out_scene = f"{row_key}_scene.mp4"
    print(f"[concat] {' + '.join(clips)} -> {out_scene}")
    if concat_ffmpeg(clips, out_scene):
        print(f"DONE {out_scene}")
    else:
        print(f"WARN: ffmpeg 拼接失败，各段在 {clips_dir}/")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default=os.environ.get("DASHSCOPE_API_KEY", ""))
    ap.add_argument("--row", default="r1", help="r1..r5 或 all")
    ap.add_argument("--duration", type=int, default=4)
    ap.add_argument("--grid", default="grid")
    ap.add_argument("--clips-dir", default="clips")
    a = ap.parse_args()
    if not a.key:
        print("ERROR: 需 --key 或环境变量 DASHSCOPE_API_KEY"); sys.exit(1)

    cfg = json.load(open("storyboard_25grid.json", encoding="utf-8"))
    if a.row == "all":
        for r in cfg["rows"]:
            process_row(a.key, r["key"], a.duration, a.grid, a.clips_dir)
    else:
        process_row(a.key, a.row, a.duration, a.grid, a.clips_dir)


if __name__ == "__main__":
    main()
