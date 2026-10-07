import os, base64, json, time, subprocess, sys

TOKEN = os.environ.get("GH_TOKEN")
if not TOKEN:
    print("NO_GH_TOKEN"); sys.exit(2)
REPO = "mz20191223/ai-comfyui"
API = f"https://api.github.com/repos/{REPO}"

def api(method, path, data=None, retries=6):
    url = API + path
    for i in range(retries):
        try:
            body = json.dumps(data).encode() if data is not None else None
            req = urllib.request.Request(url, data=body, method=method)
            req.add_header("Authorization", f"Bearer {TOKEN}")
            req.add_header("Accept", "application/vnd.github+json")
            req.add_header("Content-Type", "application/json")
            req.add_header("X-GitHub-Api-Version", "2022-11-28")
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r.read().decode())
        except Exception as e:
            print(f"  [retry {i+1}] {method} {path}: {str(e)[:90]}")
            time.sleep(3)
    raise RuntimeError(f"FAILED after retries: {method} {path}")

# 当前 main 作为 parent
ref = api("GET", "/git/refs/heads/main")
parent = ref["object"]["sha"]
print("parent commit:", parent)

# 本地提交里跟踪的所有文件（已受 .gitignore 约束）
files = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", "HEAD"]).decode().splitlines()
print("待上传文件数:", len(files))

BINARY = {".png", ".mp4", ".jpg", ".jpeg", ".gif", ".zip", ".rar", ".safetensors", ".ckpt", ".pt"}
blobs = []
for idx, f in enumerate(files, 1):
    ext = os.path.splitext(f)[1].lower()
    with open(f, "rb") as fh:
        raw = fh.read()
    if ext in BINARY:
        content, enc = base64.b64encode(raw).decode(), "base64"
    else:
        content, enc = raw.decode("utf-8", errors="replace"), "utf-8"
    r = api("POST", "/git/blobs", {"content": content, "encoding": enc})
    blobs.append({"path": f, "mode": "100644", "type": "blob", "sha": r["sha"]})
    print(f"  blob {idx}/{len(files)}: {f} ({len(raw)}B)")

tree = api("POST", "/git/trees", {"tree": blobs})
print("tree:", tree["sha"])
commit = api("POST", "/git/commits", {
    "message": "C1 九宫格通过 / C2 视频一致性失败：通过 API 逐文件推送当前 MV-Adapter + C2 工作流与证据(clip_00001.mp4)",
    "tree": tree["sha"], "parents": [parent]})
print("commit:", commit["sha"])
api("PATCH", "/git/refs/heads/main", {"sha": commit["sha"]})
print("PUSHED_OK", commit["sha"])
