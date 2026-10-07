import subprocess
import os

FFMPEG = r"C:\Users\Administrator\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\vm\tools\python\lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
CLIP_DIR = r"D:\Aicomfyui\minimax3创作内容\视频片段\第三集"
OUTPUT = os.path.join(CLIP_DIR, "第三集_完整版.mp4")

N = 18

# Build input args
inputs = []
for i in range(1, N + 1):
    inputs.extend(["-i", os.path.join(CLIP_DIR, f"{i:02d}.mp4")])

# Build filter_complex: normalize each clip, then concat
filters = []
for i in range(N):
    filters.append(f"[{i}:v]setsar=1,fps=24,format=yuv420p[v{i}]")
    filters.append(f"[{i}:a]aformat=sample_fmts=fltp:channel_layouts=stereo[a{i}]")

concat_inputs = "".join(f"[v{i}][a{i}]" for i in range(N))
filter_complex = ";".join(filters) + f";{concat_inputs}concat=n={N}:v=1:a=1[vout][aout]"

cmd = [
    FFMPEG, "-y",
    *inputs,
    "-filter_complex", filter_complex,
    "-map", "[vout]", "-map", "[aout]",
    "-c:v", "libx264", "-preset", "medium", "-crf", "18",
    "-r", "24",
    "-vsync", "cfr",
    "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
    "-pix_fmt", "yuv420p",
    "-movflags", "+faststart",
    OUTPUT
]

print(f"Merging {N} clips -> {OUTPUT}")
print("This may take a few minutes...")

result = subprocess.run(cmd, capture_output=True)
if result.returncode == 0:
    size = os.path.getsize(OUTPUT) / (1024 * 1024)
    print(f"SUCCESS: {size:.1f} MB -> {OUTPUT}")
else:
    print(f"FAILED (code {result.returncode})")
    stderr = result.stderr.decode("utf-8", errors="replace")
    print(stderr[-800:])