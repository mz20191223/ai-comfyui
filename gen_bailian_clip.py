"""gen_bailian_clip.py — 百炼 wan2.7-i2v 首尾帧生成视频段。

流程: 上传首帧/尾帧图片到 DashScope 拿到 URL → 提交 i2v 异步任务 → 轮询到完成 → 下载 mp4。

用法:
  python gen_bailian_clip.py --key "sk-xxx" --first grid/r1_c1.png --last grid/r1_c2.png \
      --prompt "镜头从中景推进，小刺猬从草丛窝探出圆脑袋，晨光柔和，皮克斯动画风格" \
      --duration 5 --out clip_r1_c1_c2.mp4

key 也可通过环境变量 DASHSCOPE_API_KEY 传入。
"""
import argparse, json, os, sys, time, urllib.request, urllib.error

BASE = "https://dashscope.aliyuncs.com/api/v1"
SYNTH = f"{BASE}/services/aigc/video-generation/video-synthesis"
FILES = f"{BASE}/files"
MODEL = "wan2.7-i2v"


def _post(url, headers, data=None, binary=None, ctype=None):
    if binary is not None:
        req = urllib.request.Request(url, data=binary, headers=headers, method="POST")
        if ctype:
            req.add_header("Content-Type", ctype)
    else:
        req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"),
                                     headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)


def upload_image(key, path):
    """上传本地图片：先 POST /api/v1/files 拿 file_id，再 GET 取可访问 URL。"""
    with open(path, "rb") as f:
        raw = f.read()
    boundary = "----bailianclipboundary"
    fn = os.path.basename(path)
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{fn}"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode("utf-8") + raw + f"\r\n--{boundary}--\r\n".encode("utf-8")
    hdr = {"Authorization": f"Bearer {key}",
           "Content-Type": f"multipart/form-data; boundary={boundary}"}
    resp = _post(FILES, hdr, binary=body)
    # 上传返回 {"data":{"uploaded_files":[{"name":..,"file_id":..}]}}
    fid = resp["data"]["uploaded_files"][0]["file_id"]
    # 再查询拿到带签名的下载 URL（视频接口需要的是 url 不是 file_id）
    greq = urllib.request.Request(f"{FILES}/{fid}",
                                  headers={"Authorization": f"Bearer {key}"}, method="GET")
    with urllib.request.urlopen(greq, timeout=60) as r:
        g = json.load(r)
    return g["data"]["url"]


def submit(key, first_url, last_url, prompt, duration, resolution="720P",
           prompt_extend=True, watermark=False):
    body = {
        "model": MODEL,
        "input": {
            "prompt": prompt,
            "media": [
                {"type": "first_frame", "url": first_url},
                {"type": "last_frame", "url": last_url},
            ],
        },
        "parameters": {
            "resolution": resolution,
            "duration": duration,
            "prompt_extend": prompt_extend,
            "watermark": watermark,
        },
    }
    hdr = {"Authorization": f"Bearer {key}", "Content-Type": "application/json",
           "X-DashScope-Async": "enable"}
    resp = _post(SYNTH, hdr, data=body)
    out = resp.get("output", {})
    tid = out.get("task_id")
    if not tid:
        raise RuntimeError(f"submit failed: {resp}")
    return tid


def wait_task(key, task_id, timeout=600, interval=10):
    hdr = {"Authorization": f"Bearer {key}"}
    url = f"{BASE}/tasks/{task_id}"
    deadline = time.time() + timeout
    while time.time() < deadline:
        req = urllib.request.Request(url, headers=hdr, method="GET")
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.load(r)
        st = resp["output"]["task_status"]
        print(f"  task {task_id} status={st}")
        if st == "SUCCEEDED":
            return resp["output"]["video_url"]
        if st in ("FAILED", "CANCELED"):
            raise RuntimeError(f"task {st}: {resp}")
        time.sleep(interval)
    raise TimeoutError(f"task {task_id} not done in {timeout}s")


def download(url, out):
    req = urllib.request.Request(url, headers={}, method="GET")
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    with open(out, "wb") as f:
        f.write(data)
    return len(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default=os.environ.get("DASHSCOPE_API_KEY", ""))
    ap.add_argument("--first", required=True)
    ap.add_argument("--last", required=True)
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--duration", type=int, default=5)
    ap.add_argument("--resolution", default="720P")
    ap.add_argument("--out", default="clip.mp4")
    ap.add_argument("--prompt-extend", dest="prompt_extend", action="store_true", default=True)
    ap.add_argument("--watermark", action="store_true", default=False)
    a = ap.parse_args()
    if not a.key:
        print("ERROR: 需 --key 或环境变量 DASHSCOPE_API_KEY"); sys.exit(1)

    print(f"[1/4] 上传首帧 {a.first}")
    fu = upload_image(a.key, a.first)
    print(f"[2/4] 上传尾帧 {a.last}")
    lu = upload_image(a.key, a.last)
    print(f"[3/4] 提交 i2v 任务 (duration={a.duration}s)")
    tid = submit(a.key, fu, lu, a.prompt, a.duration, a.resolution,
                 a.prompt_extend, a.watermark)
    print(f"      task_id={tid}")
    vurl = wait_task(a.key, tid)
    print(f"[4/4] 下载视频 -> {a.out}")
    n = download(vurl, a.out)
    print(f"DONE {a.out} ({n}B)")


if __name__ == "__main__":
    main()
