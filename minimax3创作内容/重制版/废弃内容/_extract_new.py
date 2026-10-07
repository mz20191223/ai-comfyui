import subprocess, imageio_ffmpeg, os, sys
from PIL import Image

src = r"D:/Aicomfyui/minimax3创作内容/重制版/废弃内容/废弃0114-new.mp4"
out = r"D:/Aicomfyui/minimax3创作内容/重制版/废弃内容/_new_frames"
os.makedirs(out, exist_ok=True)
ff = imageio_ffmpeg.get_ffmpeg_exe()

# 先 probe 基本信息
p = subprocess.run([ff, "-i", src], stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
print("=== PROBE ===")
print(p.stderr[:1500])

# 抽 10 帧均匀覆盖
dur = 4.5  # 临时，后面用实际
# 用 fps filter 抽 12 帧
vf = "select='not(mod(n\\,ceil(nb_frames/12)))',setpts=N/FRAME_RATE/TB"
cmd = [ff, "-i", src, "-vf", vf, "-vsync", "vfr", os.path.join(out, "f%03d.png")]
# 上面 filter 在某些版本不稳，改用固定 fps 抽帧
cmd2 = [ff, "-i", src, "-vf", "fps=2", os.path.join(out, "f%03d.png")]
r = subprocess.run(cmd2, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
print("=== RUN ===")
print(r.stderr[-800:])
files = sorted(os.listdir(out))
print("frames:", files)
for f in files[:3]:
    im = Image.open(os.path.join(out, f))
    print(f, im.size)
