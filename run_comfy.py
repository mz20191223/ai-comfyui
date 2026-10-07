#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""向 HAI 上的 ComfyUI 提交工作流、轮询结果、并自动把输出图下载到本地。
底层走 curl（沙箱只放行 curl），不依赖 urllib 的代理栈。

用法:
  run_comfy.py <workflow.json> [--host http://HOST:PORT] [--timeout 600] [--out DIR]

示例:
  run_comfy.py hedgehog_faceid_v2_test.json --host http://43.133.79.205:6889 --out test_out
  run_comfy.py hedgehog_9grid_faceidplusv2_v2.json --host http://43.133.79.205:6889 --out hedgehog_9grid_out
"""
import sys, os, json, time, shutil, subprocess, argparse

def curl(args, max_time=60, retries=3):
    """用 curl 跑一次请求，返回 (status_code, body_text)。"""
    for attempt in range(1, retries + 1):
        cmd = ["curl", "-sSL", "--max-time", str(max_time), "-w", "\n%{http_code}"]
        cmd += args
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=max_time + 20)
            out = p.stdout
            parts = out.rsplit("\n", 1)
            body = parts[0]
            code = parts[1].strip() if len(parts) > 1 else ""
            return (code, body)
        except subprocess.TimeoutExpired:
            print(f"  [curl 超时, 第{attempt}次]")
        except Exception as e:
            print(f"  [curl 异常 {e}, 第{attempt}次]")
    return ("000", "")

def curl_download(url, dest, max_time=120):
    cmd = ["curl", "-sSL", "--max-time", str(max_time), "-o", dest, url]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=max_time + 20)
    return p.returncode == 0 and os.path.exists(dest) and os.path.getsize(dest) > 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workflow")
    ap.add_argument("--host", default=os.environ.get("COMFY_HOST", "http://43.133.79.205:6889"))
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "hedgehog_9grid_out"))
    args = ap.parse_args()

    HOST = args.host.rstrip("/")
    print("==> ComfyUI:", HOST)
    print("==> 工作流:", args.workflow)

    # 0) 连通性
    code, _ = curl([HOST + "/system_stats"], max_time=20)
    if code not in ("200",):
        print("!! 连不上 ComfyUI (HTTP %s)，确认 HAI 已开且地址正确" % code)
        sys.exit(1)
    print("==> 连通 OK")

    # 1) 读工作流
    with open(args.workflow, encoding="utf-8") as f:
        prompt = json.load(f)

    payload = json.dumps({"prompt": prompt, "client_id": "wb_%d" % int(time.time())}).encode("utf-8")
    # 写临时文件交给 curl，避免命令行超长
    tmp = args.workflow + ".payload.tmp"
    with open(tmp, "wb") as f:
        f.write(payload)

    # 2) 提交
    code, body = curl(["-X", "POST", "-H", "Content-Type: application/json",
                       "--data-binary", "@" + tmp, HOST + "/prompt"], max_time=60)
    try:
        os.remove(tmp)
    except OSError:
        pass  # 沙箱无回收站，安全删除 shim 会抛错，忽略即可
    print("POST /prompt ->", code)
    print(body[:1500])
    if code != "200":
        print("!! 提交失败"); sys.exit(1)
    try:
        pid = json.loads(body)["prompt_id"]
    except Exception:
        print("!! 无法解析 prompt_id"); sys.exit(1)
    print("prompt_id =", pid)

    # 3) 轮询
    start = time.time()
    while time.time() - start < args.timeout:
        code, body = curl([HOST + "/history/" + pid], max_time=20)
        if code == "200" and body:
            try:
                hist = json.loads(body)
            except Exception:
                time.sleep(5); continue
            if pid in hist:
                entry = hist[pid]
                # 异常检测
                for m in entry.get("status", {}).get("messages", []):
                    if m[0] == "execution_error":
                        print("\n!!! 执行错误:")
                        print(json.dumps(m[1], ensure_ascii=False, indent=2))
                        sys.exit(2)
                outs = entry.get("outputs", {})
                imgs = []
                for nid, o in outs.items():
                    for im in o.get("images", []):
                        imgs.append((nid, im.get("filename"), im.get("subfolder", ""), im.get("type", "output")))
                print("\n==> 完成! 生成图像数:", len(imgs))
                if not imgs:
                    print("!! 没有输出图像，可能中间节点未连接 SaveImage")
                    sys.exit(3)
                # 4) 下载
                out_dir = args.out
                if os.path.exists(out_dir):
                    try:
                        shutil.rmtree(out_dir)
                    except OSError:
                        pass  # 沙箱安全删除 shim 可能拦截，忽略；下面 makedirs 仍可建
                os.makedirs(out_dir, exist_ok=True)
                print("==> 下载到:", out_dir)
                for nid, fn, sub, typ in imgs:
                    url = "%s/view?filename=%s&subfolder=%s&type=%s" % (
                        HOST, requests_quote(fn), requests_quote(sub), requests_quote(typ))
                    dest = os.path.join(out_dir, os.path.basename(fn))
                    ok = curl_download(url, dest)
                    print("  [%s] %s -> %s %s" % (nid, fn, dest, "OK" if ok else "FAIL"))
                print("==> 全部完成")
                sys.exit(0)
        time.sleep(5)
    print("!! 超时 (%ds) 未完成" % args.timeout)

def requests_quote(s):
    # 简单 URL 编码（避免引依赖），只处理必要字符
    from urllib.parse import quote
    return quote(s, safe="")

if __name__ == "__main__":
    main()
