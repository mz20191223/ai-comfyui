"""run_storyboard_video.py — 按情节生成连续叙事视频（带断点续传）。

取某情节(默认 p1)的全部镜(按 beat 排序)，相邻两镜当首尾帧 → wan2.7-i2v 生成过渡视频段
→ ffmpeg 统一缩放竖屏后拼接成一段连续镜头。

断点续传：每段提交后把【完整 task_id】写到 {plot}_tasks.json；若进程中途退出，
重跑时先轮询已有任务(不重复扣费)，成功则直接下载，失败/未知才重提。一次只串行提交
一段，避免重复进程挤爆队列。

用法:
  python run_storyboard_video.py --key "sk-xxx" --plot p1 --duration 4
  python run_storyboard_video.py --key "sk-xxx" --plot p1 --duration 4 --out p1_scene.mp4

输出:
  clips/{s0}_{s1}.mp4  各过渡段
  {plot}_scene.mp4     该情节拼接后的连续镜头
"""
import argparse, json, os, sys, shutil, subprocess, atexit
import gen_bailian_clip as C


def is_pid_alive(pid):
    """Windows 下用 os.kill(pid,0) 探测进程是否存活。"""
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except Exception:
        return True  # 其他错误(如权限)保守认为存活


def acquire_lock(plot):
    """单实例锁：同一 plot 只允许一个进程跑，重复拉起自动退出，避免双倍扣费。
    锁文件残留(进程被强杀)时，若其中 PID 已死则视为陈旧锁并清除。"""
    lock = f"{plot}.lock"
    if os.path.exists(lock):
        try:
            with open(lock) as f:
                oldpid = int(f.read().strip() or 0)
            if oldpid and is_pid_alive(oldpid):
                print(f"ERROR: 另一实例(plot={plot}, pid={oldpid})正在运行，"
                      f"本次退出以避免重复提交/扣费")
                sys.exit(1)
            else:
                os.remove(lock)  # 陈旧锁
        except Exception:
            try:
                os.remove(lock)
            except Exception:
                pass
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        print(f"ERROR: 锁文件 {lock} 已存在，另一实例运行中，退出")
        sys.exit(1)
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    mypid = os.getpid()

    def _release():
        # 仅当锁中记录的 PID 仍是自己时才删除，避免重复进程退出时误删正主的锁
        try:
            if os.path.exists(lock):
                with open(lock) as f:
                    if int(f.read().strip() or 0) == mypid:
                        os.remove(lock)
        except Exception:
            pass

    atexit.register(_release)
    return lock

POLL_TIMEOUT = 1800   # 单段最长轮询 30 分钟
POLL_INTERVAL = 15


def get_ffmpeg():
    s = shutil.which("ffmpeg")
    if s:
        return s
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def concat_ffmpeg(clips, out, tw=720, th=1280):
    """filter_complex 单遍拼接：先统一缩放pad到竖屏720x1280，再 concat。"""
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
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        print("WARN: concat 失败")
        return False
    return True


def resume_existing(key, tid):
    """轮询已落盘的任务；成功返回 video_url，否则返回 None。"""
    try:
        return C.wait_task(key, tid, timeout=POLL_TIMEOUT, interval=POLL_INTERVAL)
    except Exception as e:
        print(f"  [resume] 任务 {tid[:8]} 轮询失败: {e}")
        return None


def gen_one(key, first, last, prompt, duration, out, state, pair_key, state_file):
    if os.path.exists(out) and os.path.getsize(out) > 0:
        print(f"  跳过已存在 {out}"); return True
    # 断点续传：先尝试已有任务
    tid = state.get(pair_key)
    if tid:
        print(f"  [resume] 复用任务 {tid[:8]} for {pair_key}")
        vurl = resume_existing(key, tid)
        if vurl:
            C.download(vurl, out)
            state.pop(pair_key, None)
            json.dump(state, open(state_file, "w", encoding="utf-8"))
            return True
        state.pop(pair_key, None)  # 失败/未知 → 清掉下面重提
    # 新提交（一次一段，串行）
    fu = C.upload_image(key, first)
    lu = C.upload_image(key, last)
    tid = C.submit(key, fu, lu, prompt, duration)
    state[pair_key] = tid
    json.dump(state, open(state_file, "w", encoding="utf-8"))  # 提交即落盘
    print(f"  [submit] {pair_key} task={tid}")
    vurl = C.wait_task(key, tid, timeout=POLL_TIMEOUT, interval=POLL_INTERVAL)
    C.download(vurl, out)
    state.pop(pair_key, None)
    json.dump(state, open(state_file, "w", encoding="utf-8"))
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default=os.environ.get("DASHSCOPE_API_KEY", ""))
    ap.add_argument("--plot", default="p1", help="情节 key，如 p1")
    ap.add_argument("--duration", type=int, default=4)
    ap.add_argument("--grid", default="grid")
    ap.add_argument("--clips-dir", default="clips")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if not a.key:
        print("ERROR: 需 --key 或环境变量 DASHSCOPE_API_KEY"); sys.exit(1)

    acquire_lock(a.plot)  # 单实例：重复拉起自动退出

    cfg = json.load(open("storyboard_25grid.json", encoding="utf-8"))
    shots = [s for s in cfg["shots"] if s["plot"] == a.plot]
    shots.sort(key=lambda s: s["beat"])
    os.makedirs(a.clips_dir, exist_ok=True)

    state_file = f"{a.plot}_tasks.json"
    state = {}
    if os.path.exists(state_file):
        try:
            state = json.load(open(state_file, encoding="utf-8"))
        except Exception:
            state = {}

    clips = []
    for i in range(len(shots) - 1):
        s0, s1 = shots[i], shots[i + 1]
        first = f"{a.grid}/{s0['id']}.png"
        last = f"{a.grid}/{s1['id']}.png"
        out = f"{a.clips_dir}/{s0['id']}_{s1['id']}.mp4"
        prompt = (f"{s0['prompt']} 镜头平滑运镜过渡到：{s1['prompt']}。"
                  f"保持角色一致、皮克斯3D动画电影质感、明亮饱和色彩、连贯动作。")
        pair_key = f"{s0['id']}_{s1['id']}"
        print(f"[clip {i+1}/{len(shots)-1}] {s0['id']} -> {s1['id']} (duration={a.duration}s)")
        gen_one(a.key, first, last, prompt, a.duration, out, state, pair_key, state_file)
        clips.append(out)

    out_scene = a.out or f"{a.plot}_scene.mp4"
    print(f"[concat] {' + '.join(clips)} -> {out_scene}")
    if concat_ffmpeg(clips, out_scene):
        print(f"DONE {out_scene}")
    else:
        print("WARN: ffmpeg 拼接失败，各段在 clips/")


if __name__ == "__main__":
    main()
