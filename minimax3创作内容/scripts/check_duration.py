import mutagen, os, imageio.v2 as imageio

audio_dir = r'D:\Aicomfyui\minimax3创作内容\重制版\音频'
video_dir = r'D:\Aicomfyui\minimax3创作内容\重制版\分镜视频'

print("=== 音频时长 ===")
for f in sorted(os.listdir(audio_dir)):
    if '镜头10' in f or '镜头11' in f:
        path = os.path.join(audio_dir, f)
        try:
            m = mutagen.File(path)
            print(f'{f}: {m.info.length:.2f}s')
        except Exception as e:
            print(f'{f}: {e}')

print("\n=== 视频时长 ===")
for f in os.listdir(video_dir):
    if f.endswith('.mp4'):
        path = os.path.join(video_dir, f)
        try:
            reader = imageio.get_reader(path)
            dur = reader.get_length()
            fps = reader.get_fps()
            print(f'{f}: {dur:.2f}s, FPS: {fps}')
            reader.close()
        except Exception as e:
            print(f'{f}: {e}')
