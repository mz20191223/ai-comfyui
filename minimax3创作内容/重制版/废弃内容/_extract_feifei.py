import imageio_ffmpeg, subprocess, os
exe = imageio_ffmpeg.get_ffmpeg_exe()
src = r"D:/Aicomfyui/minimax3创作内容/重制版/废弃内容/0114废废弃.mp4"
out = r"D:/Aicomfyui/minimax3创作内容/重制版/废弃内容/_feifei_frames"
os.makedirs(out, exist_ok=True)
# get duration
p = subprocess.run([exe,"-i",src], capture_output=True, text=True)
import re
m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", p.stderr)
print("probe:", m.group(0) if m else "unknown")
dur = float(m.group(3)) + 60*int(m.group(2)) + 3600*int(m.group(1)) if m else 4.5
n = 10
for i in range(n+1):
    t = dur*i/n
    op = os.path.join(out, f"f{i:02d}_t{t:.2f}.jpg")
    subprocess.run([exe,"-ss",f"{t:.2f}","-i",src,"-frames:v","1","-q:v","2",op], capture_output=True)
print("done", os.listdir(out))
