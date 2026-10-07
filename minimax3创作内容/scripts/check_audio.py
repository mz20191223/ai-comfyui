import mutagen, os

audio_dir = r"D:\Aicomfyui\minimax3创作内容\重制版\音频"
with open(r"D:\Aicomfyui\minimax3创作内容\scripts\audio_duration.txt", "w", encoding="utf-8") as out:
    for f in sorted(os.listdir(audio_dir)):
        if "镜头10" in f or "镜头11" in f:
            path = os.path.join(audio_dir, f)
            m = mutagen.File(path)
            out.write(f"{f}: {m.info.length:.2f}s\n")
