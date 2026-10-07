"""最小验证脚本：用百炼 wan2.7-image 出 1 张图，验证 key / 服务 / 画风。
key 通过 --key 传入（不写死在文件），运行时：
  python bailian_image_one.py --key "sk-xxx" --prompt "..." --out xxx.png
"""
import argparse, urllib.request, json


API = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True)
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="wan2.7-image")
    ap.add_argument("--size", default="1024*1536")
    a = ap.parse_args()

    body = {
        "model": a.model,
        "input": {"messages": [{"role": "user", "content": [{"text": a.prompt}]}]},
        "parameters": {"size": a.size, "n": 1},
    }
    req = urllib.request.Request(
        API,
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {a.key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            data = json.load(r)
        print("STATUS", r.status)
        # 打印精简结构便于排查
        print("RESP_SNIP", json.dumps(data, ensure_ascii=False)[:600])
        url = data["output"]["choices"][0]["message"]["content"][0]["image"]
        with urllib.request.urlopen(url, timeout=60) as r2:
            img = r2.read()
        with open(a.out, "wb") as f:
            f.write(img)
        print("SAVED", a.out, len(img), "bytes")
    except urllib.error.HTTPError as e:
        print("HTTPError", e.code, e.read().decode("utf-8")[:600])
    except Exception as e:
        print("ERR", repr(e))


if __name__ == "__main__":
    main()
