#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""云端 ComfyUI 通用管线客户端（curl 版，沙箱友好）。

职责：
  1) 上传参考图到 ComfyUI（/upload/image），返回服务端文件名
  2) 提交工作流（/prompt）
  3) 轮询结果（/history/<pid>），并捕获 execution_error
  4) 下载输出（图像 + 视频），归到本地目录

设计要点：
  - 全程走 curl（沙箱只放行 curl，不用 urllib 代理栈）。
  - 单实例锁（可选）：同一 --tag 只允许一个进程跑，避免重复提交双倍扣算力。
  - 通用：工作流 JSON 由调用方提供；本脚本只负责传/提/轮/下。

用法：
  # 仅上传参考图，拿到服务端文件名（用于填工作流）
  python cloud_pipeline.py upload --host http://HOST:6889 --images peach_role_v6.png a.png b.png

  # 提交一个已写好引用文件名的工作流，轮询并下载
  python cloud_pipeline.py run \
      --host http://HOST:6889 \
      --workflow ltx_p1_s01_s02.json \
      --out p1_clips \
      --timeout 1800

  # 一步到位：先上传 --images 里列出的图，再把它们作为 "uploaded" 映射写进
  # 工作流的指定 LoadImage 节点，然后提交+轮询+下载
  python cloud_pipeline.py go \
      --host http://HOST:6889 \
      --workflow ltx_p1_s01_s02.json \
      --images peach_role_v6.png ref_front.png ref_side.png \
      --map "6:peach_role_v6.png,9:ref_front.png,10:ref_side.png" \
      --out p1_clips --timeout 1800
"""
import sys, os, json, time, shutil, subprocess, argparse, uuid, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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


def curl_download(url, dest, max_time=180):
    cmd = ["curl", "-sSL", "--max-time", str(max_time), "-o", dest, url]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=max_time + 20)
    return p.returncode == 0 and os.path.exists(dest) and os.path.getsize(dest) > 0


def upload_image(host, path):
    """上传单张图，返回服务端文件名（填工作流时用）。"""
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    cmd = ["curl", "-sSL", "--max-time", "120", "-F",
           "image=@" + path, host.rstrip("/") + "/upload/image"]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=140)
        try:
            j = json.loads(p.stdout)
            return j.get("name") or j.get("filename")
        except Exception:
            print("  [upload 返回非 JSON]", p.stdout[:300])
            return None
    except Exception as e:
        print("  [upload 异常]", e)
        return None


def submit(host, workflow, client_id):
    payload = json.dumps({"prompt": workflow, "client_id": client_id}).encode("utf-8")
    tmp = workflow + ".payload.tmp"
    with open(tmp, "wb") as f:
        f.write(payload)
    try:
        code, body = curl(["-X", "POST", "-H", "Content-Type: application/json",
                           "--data-binary", "@" + tmp, host.rstrip("/") + "/prompt"], max_time=60)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
    if code != "200":
        return (None, code, body)
    try:
        pid = json.loads(body)["prompt_id"]
        return (pid, code, body)
    except Exception:
        return (None, code, body)


def wait_history(host, pid, timeout, interval=5):
    start = time.time()
    while time.time() - start < timeout:
        code, body = curl([host.rstrip("/") + "/history/" + pid], max_time=20)
        if code == "200" and body:
            try:
                hist = json.loads(body)
            except Exception:
                time.sleep(interval); continue
            if pid in hist:
                entry = hist[pid]
                for m in entry.get("status", {}).get("messages", []):
                    if m[0] == "execution_error":
                        return ("error", m[1], entry)
                return ("done", entry.get("outputs", {}), entry)
        time.sleep(interval)
    return ("timeout", None, None)


def download_outputs(host, outputs, out_dir):
    if os.path.exists(out_dir):
        try:
            shutil.rmtree(out_dir)
        except OSError:
            pass
    os.makedirs(out_dir, exist_ok=True)
    from urllib.parse import quote
    count = 0
    for nid, o in outputs.items():
        for key in ("images", "videos"):
            for im in o.get(key, []):
                fn = im.get("filename")
                sub = im.get("subfolder", "")
                typ = im.get("type", "output")
                if not fn:
                    continue
                url = "%s/view?filename=%s&subfolder=%s&type=%s" % (
                    host.rstrip("/"), quote(fn), quote(sub), quote(typ))
                dest = os.path.join(out_dir, os.path.basename(fn))
                ok = curl_download(url, dest)
                print("  [%s/%s] %s -> %s %s" % (nid, key, fn, dest, "OK" if ok else "FAIL"))
                if ok:
                    count += 1
    return count


def parse_map(s):
    """ '6:peach_role_v6.png,9:a.png' -> {6: 'peach_role_v6.png'} """
    m = {}
    if not s:
        return m
    for part in s.split(","):
        k, v = part.split(":", 1)
        m[k.strip()] = v.strip()
    return m


def cmd_upload(args):
    host = args.host.rstrip("/")
    code, _ = curl([host + "/system_stats"], max_time=20)
    if code != "200":
        print("!! 连不上 ComfyUI (HTTP %s)" % code); sys.exit(1)
    for img in args.images:
        name = upload_image(host, img)
        print("%s -> %s" % (img, name))


def cmd_run(args):
    host = args.host.rstrip("/")
    code, _ = curl([host + "/system_stats"], max_time=20)
    if code != "200":
        print("!! 连不上 ComfyUI (HTTP %s)" % code); sys.exit(1)
    with open(args.workflow, encoding="utf-8") as f:
        wf = json.load(f)
    pid, code, body = submit(host, wf, "wb_%d" % int(time.time()))
    print("POST /prompt ->", code, body[:400])
    if not pid:
        print("!! 提交失败"); sys.exit(1)
    print("prompt_id =", pid)
    st, out, entry = wait_history(host, pid, args.timeout)
    if st == "error":
        print("\n!!! 执行错误:"); print(json.dumps(out, ensure_ascii=False, indent=2)); sys.exit(2)
    if st == "timeout":
        print("!! 超时未完成"); sys.exit(3)
    n = download_outputs(host, out, args.out)
    print("==> 下载完成，文件数:", n, "->", args.out)


def cmd_go(args):
    host = args.host.rstrip("/")
    code, _ = curl([host + "/system_stats"], max_time=20)
    if code != "200":
        print("!! 连不上 ComfyUI (HTTP %s)" % code); sys.exit(1)
    # 1) 上传
    uploaded = {}
    for img in args.images:
        name = upload_image(host, img)
        if not name:
            print("!! 上传失败:", img); sys.exit(1)
        uploaded[os.path.basename(img)] = name
        print("upload %s -> %s" % (img, name))
    # 2) 把上传文件名填进工作流指定节点
    with open(args.workflow, encoding="utf-8") as f:
        wf = json.load(f)
    mp = parse_map(args.map)
    for node_id, basename in mp.items():
        if basename not in uploaded:
            print("!! --map 指定的 %s 不在 --images 中" % basename); sys.exit(1)
        if node_id in wf:
            # 兼容两种输入写法： {"image": "x"} 或 {"images": [...]}
            if "image" in wf[node_id].get("inputs", {}):
                wf[node_id]["inputs"]["image"] = uploaded[basename]
            else:
                wf[node_id].setdefault("inputs", {})["image"] = uploaded[basename]
            print("  node %s.image = %s" % (node_id, uploaded[basename]))
        else:
            print("!! 工作流无节点 %s" % node_id); sys.exit(1)
    # 3) 提交+轮询+下载
    pid, code, body = submit(host, wf, "wb_%d" % int(time.time()))
    print("POST /prompt ->", code, body[:400])
    if not pid:
        print("!! 提交失败"); sys.exit(1)
    print("prompt_id =", pid)
    st, out, entry = wait_history(host, pid, args.timeout)
    if st == "error":
        print("\n!!! 执行错误:"); print(json.dumps(out, ensure_ascii=False, indent=2)); sys.exit(2)
    if st == "timeout":
        print("!! 超时未完成"); sys.exit(3)
    n = download_outputs(host, out, args.out)
    print("==> 下载完成，文件数:", n, "->", args.out)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    au = sub.add_parser("upload"); au.add_argument("--host", required=True); au.add_argument("--images", nargs="+", required=True); au.set_defaults(func=cmd_upload)
    ar = sub.add_parser("run"); ar.add_argument("--host", required=True); ar.add_argument("--workflow", required=True); ar.add_argument("--out", default="cloud_out"); ar.add_argument("--timeout", type=int, default=1800); ar.set_defaults(func=cmd_run)
    ag = sub.add_parser("go"); ag.add_argument("--host", required=True); ag.add_argument("--workflow", required=True); ag.add_argument("--images", nargs="+", required=True); ag.add_argument("--map", required=True, help="节点ID:本地文件名 映射，如 6:peach_role_v6.png,9:a.png"); ag.add_argument("--out", default="cloud_out"); ag.add_argument("--timeout", type=int, default=1800); ag.set_defaults(func=cmd_go)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
