#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, imageio.v2 as imageio

SRC = r"C:\Users\Administrator\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a66b45ddd1ea2518b75e708\peach_video.mp4"
OUT = r"D:\Aicomfyui\trae_seedance_test\frames"
os.makedirs(OUT, exist_ok=True)

reader = imageio.get_reader(SRC)
meta = reader.get_meta_data()
nframes = reader.count_frames()
fps = meta.get("fps")
duration = None
if fps and nframes:
    duration = nframes / fps
print("fps=%.3f nframes=%d duration=%.2fs size=%s" % (fps or 0, nframes, duration or 0, meta.get("size")))

N = 6
idxs = [int(round(i * (nframes - 1) / (N - 1))) for i in range(N)]
print("sample frame indices:", idxs)
for i, idx in enumerate(idxs):
    frame = reader.get_data(idx)
    p = os.path.join(OUT, "frame_%02d.png" % i)
    imageio.imwrite(p, frame)
    print("wrote", p, frame.shape)
reader.close()
