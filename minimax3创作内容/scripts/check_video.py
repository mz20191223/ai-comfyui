import imageio.v2 as imageio
import os

video_dir = r"D:\Aicomfyui\minimax3创作内容\重制版\分镜视频"
with open(r"D:\Aicomfyui\minimax3创作内容\scripts\video_duration.txt", "w", encoding="utf-8") as out:
    for f in sorted(os.listdir(video_dir)):
        if f.endswith(".mp4"):
            path = os.path.join(video_dir, f)
            try:
                reader = imageio.get_reader(path)
                out.write(f"{f}: {reader.get_length():.2f}s, FPS: {reader.get_fps()}\n")
                reader.close()
            except Exception as e:
                out.write(f"{f}: ERROR {e}\n")
