from PIL import Image
import os

tail_dir = r"D:\Aicomfyui\minimax3创作内容\重制版\分镜图\视频尾帧"
with open(r"D:\Aicomfyui\minimax3创作内容\scripts\tail_sizes.txt", "w", encoding="utf-8") as out:
    for f in sorted(os.listdir(tail_dir)):
        path = os.path.join(tail_dir, f)
        img = Image.open(path)
        out.write(f"{f}: {img.size}\n")
