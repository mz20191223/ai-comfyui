"""bailian_image_ref.py — 用百炼 wan2.7-image 的图文参考出图。

用法:
  python bailian_image_ref.py --key "sk-xxx" --ref peach_ref.png \
      --prompt "一个可爱的拟人化桃子角色..." --out peach_role.png

key 也可通过环境变量 DASHSCOPE_API_KEY 传入。
"""
import argparse, json, os, sys, urllib.request

API = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
FILES = "https://dashscope.aliyuncs.com/api/v1/files"


def upload_image(key, path):
    with open(path, "rb") as f:
        raw = f.read()
    boundary = "----bailianimgref"
    fn = os.path.basename(path)
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{fn}"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode("utf-8") + raw + f"\r\n--{boundary}--\r\n".encode("utf-8")
    hdr = {"Authorization": f"Bearer {key}",
           "Content-Type": f"multipart/form-data; boundary={boundary}"}
    req = urllib.request.Request(FILES, data=body, headers=hdr, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        resp = json.load(r)
    fid = resp["data"]["uploaded_files"][0]["file_id"]
    greq = urllib.request.Request(f"{FILES}/{fid}",
                                  headers={"Authorization": f"Bearer {key}"}, method="GET")
    with urllib.request.urlopen(greq, timeout=60) as r:
        g = json.load(r)
    return g["data"]["url"]


def gen_with_ref(key, ref_url, prompt, model, size):
    body = {
        "model": model,
        "input": {
            "messages": [
                {"role": "user", "content": [
                    {"text": prompt},
                    {"image": ref_url}
                ]}
            ]
        },
        "parameters": {"size": size, "n": 1},
    }
    req = urllib.request.Request(
        API, data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        data = json.load(r)
    return data["output"]["choices"][0]["message"]["content"][0]["image"]


def gen_one(key, prompt, model, size):
    """纯文字出图（不带参考图），用于 character_lock=false 的空镜（如 s01）。"""
    body = {
        "model": model,
        "input": {
            "messages": [
                {"role": "user", "content": [
                    {"text": prompt}
                ]}
            ]
        },
        "parameters": {"size": size, "n": 1},
    }
    req = urllib.request.Request(
        API, data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        data = json.load(r)
    return data["output"]["choices"][0]["message"]["content"][0]["image"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default=os.environ.get("DASHSCOPE_API_KEY", ""))
    ap.add_argument("--ref", required=True)
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--out", default="peach_role.png")
    ap.add_argument("--model", default="wan2.7-image")
    ap.add_argument("--size", default="1024*1024")
    a = ap.parse_args()
    if not a.key:
        print("ERROR: 需 --key 或环境变量 DASHSCOPE_API_KEY"); sys.exit(1)

    print("[1/2] 上传参考图...")
    ref_url = upload_image(a.key, a.ref)
    print("[2/2] 生成新图...")
    img_url = gen_with_ref(a.key, ref_url, a.prompt, a.model, a.size)
    with urllib.request.urlopen(img_url, timeout=60) as r:
        img = r.read()
    with open(a.out, "wb") as f:
        f.write(img)
    print(f"DONE {a.out} ({len(img)}B)")


if __name__ == "__main__":
    main()
