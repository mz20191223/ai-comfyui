import imageio_ffmpeg
import subprocess, os, json

exe = imageio_ffmpeg.get_ffmpeg_exe()
src = r"D:\Aicomfyui\minimax3创作内容\重制版\废弃内容\0114b废弃.mp4"
outdir = r"D:\Aicomfyui\minimax3创作内容\重制版\废弃内容\_0114b_frames"
os.makedirs(outdir, exist_ok=True)

# get metadata
probe = subprocess.run([exe, "-i", src], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
info = probe.stderr.decode("utf-8", "ignore")
print("=== METADATA ===")
# extract duration / resolution / fps lines
for line in info.splitlines():
    if any(k in line for k in ["Duration", "Stream", "Video:", "resolution"]):
        print(line.strip())

# extract N evenly spaced frames
N = 10
# use fps filter to grab frames at timestamps; simpler: use -vf fps
# First detect total duration
import re
m = re.search(r"Duration: (\d+):(\d+):(\d+)\.(\d+)", info)
if m:
    h, mi, s, f = map(int, m.groups())
    total = h*3600 + mi*60 + s + f/100.0
else:
    total = 5.0
print("TOTAL_SECONDS:", total)

# grab frames at evenly spaced timestamps
for i in range(N):
    t = total * (i + 0.5) / N
    out = os.path.join(outdir, f"frame_{i:02d}_t{t:.2f}.jpg")
    cmd = [exe, "-ss", f"{t:.3f}", "-i", src, "-frames:v", "1", "-q:v", "2", out]
    subprocess.run(cmd, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    print("saved", out)
print("DONE")
