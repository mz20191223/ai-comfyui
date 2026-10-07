#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Agnes Video V2.0 —— 文生视频 / 图生视频 / 关键帧动画（异步 + 轮询 + 下载）。

API 主机 : https://apihub.agnes-ai.com
创建任务 : POST /v1/videos
轮询结果 : GET  /agnesapi?video_id=<VIDEO_ID>
模型     : agnes-video-v2.0
费用     : 当前免费（$0 / 秒）

帧数约束 : num_frames ≤ 441 且必须 = 8n+1（合法: 81/121/161/201/241/281/321/361/401/441）
时长公式 : seconds = num_frames / frame_rate

重要坑:
  - 视频 URL 在 status=completed 时实测位于顶层 url 字段；
    本模块兼容 metadata.url 与旧字段 remixed_from_video_id 兜底。
  - 轮询用 GET /agnesapi?video_id= （注意不是 /v1/agnesapi）。

用法:
  from agnes_video import generate_video, download_video
  res = generate_video("一只小刺猬在草地上蹦跳，阳光，皮克斯动画风",
                       num_frames=121, frame_rate=24)
  if res["status"] == "completed":
      download_video(res["url"], "clip.mp4")
"""
import json
import os
import time
import urllib.request

try:
    from agnes_llm import AGNES_API_KEY
except Exception:
    AGNES_API_KEY = os.environ.get(
        "AGNES_API_KEY",
        """",
    )

API_HOST = "https://apihub.agnes-ai.com"   # 注意：结果查询端点不带 /v1
VIDEO_ENDPOINT = "/v1/videos"
RESULT_ENDPOINT = "/agnesapi"              # GET ?video_id=
MODEL = "agnes-video-v2.0"


def _headers(extra=None):
    h = {"Authorization": f"Bearer {AGNES_API_KEY}",
         "Content-Type": "application/json"}
    if extra:
        h.update(extra)
    return h


def create_video(prompt, image=None, mode=None, width=1152, height=768,
                 num_frames=121, frame_rate=24, seed=None,
                 negative_prompt=None, extra_images=None, timeout=60):
    """提交一个视频生成任务，返回任务 dict（含 video_id / task_id / status）。"""
    if num_frames > 441 or (num_frames - 1) % 8 != 0:
        raise ValueError("num_frames 必须 ≤ 441 且满足 8n+1，例如 81/121/161/241")
    body = {
        "model": MODEL,
        "prompt": prompt,
        "width": width,
        "height": height,
        "num_frames": num_frames,
        "frame_rate": frame_rate,
    }
    if seed is not None:
        body["seed"] = seed
    if negative_prompt:
        body["negative_prompt"] = negative_prompt
    if image:                      # 图生视频：单图 URL
        body["image"] = image
    if extra_images:               # 关键帧动画：多图
        body["extra_body"] = {"image": extra_images, "mode": "keyframes"}
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        API_HOST + VIDEO_ENDPOINT, data=data, headers=_headers())
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def get_video(video_id, timeout=30):
    """查询任务状态，返回完整结果 dict。"""
    url = f"{API_HOST}{RESULT_ENDPOINT}?video_id={video_id}"
    req = urllib.request.Request(url, headers=_headers())
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def generate_video(prompt, image=None, mode=None, width=1152, height=768,
                   num_frames=121, frame_rate=24, seed=None,
                   negative_prompt=None, extra_images=None,
                   poll_interval=5, max_wait=600, timeout=60):
    """一键生成并轮询，直到完成/失败/超时。

    返回: {"status": "completed"|"failed"|"timeout",
           "url": str|None, "error": ..., "raw": dict}
    """
    task = create_video(prompt, image=image, mode=mode, width=width, height=height,
                        num_frames=num_frames, frame_rate=frame_rate, seed=seed,
                        negative_prompt=negative_prompt, extra_images=extra_images,
                        timeout=timeout)
    vid = task.get("video_id") or task.get("task_id")
    if not vid:
        return {"status": "failed", "url": None,
                "error": "缺少 video_id", "raw": task}
    deadline = time.time() + max_wait
    while time.time() < deadline:
        time.sleep(poll_interval)
        st = get_video(vid, timeout=timeout)
        status = st.get("status")
        if status == "completed":
            # URL 位置兼容：顶层 url（实测）> metadata.url（文档）> 旧字段 remixed_from_video_id
            meta = st.get("metadata") or {}
            url = (st.get("url")
                   or meta.get("url")
                   or st.get("remixed_from_video_id"))
            return {"status": "completed", "url": url,
                    "seconds": st.get("seconds"), "size": st.get("size"),
                    "error": None, "raw": st}
        if status == "failed":
            return {"status": "failed", "url": None,
                    "error": st.get("error"), "raw": st}
        # queued / in_progress -> 继续轮询
    return {"status": "timeout", "url": None, "error": "轮询超时", "raw": task}


def download_video(url, out_path, timeout=180):
    """下载视频到本地。"""
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=timeout) as r, open(out_path, "wb") as f:
        f.write(r.read())
    return out_path


if __name__ == "__main__":
    res = generate_video("一只皮克斯风格的小刺猬在草地上开心蹦跳，阳光明媚，动画风",
                         num_frames=81, frame_rate=24)
    print("status:", res["status"], "| url:", res.get("url"))
    if res["status"] == "completed":
        download_video(res["url"], "agnes_test.mp4")
        print("已保存到 agnes_test.mp4")
