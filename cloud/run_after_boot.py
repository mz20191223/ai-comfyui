#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HAI 开机后一键总控（本机侧运行）。

流程: 探测 ComfyUI -> 传换权重脚本 -> 换完整 Qwen-Edit 权重(约13G) ->
      等 ComfyUI 重启就绪 -> txt2img 验证 -> 出 4 张多角度参考图。
依赖同目录 ssh_run.py / sftp_upload.py（实例密码从 SSH_PASS 环境变量取）。
若 T4 显存不足 OOM，自动回退 Q3_K_M 并重试一次。

用法（下午开机后，由 agent 执行）:
  SSH_PASS='<HAI root 密码>' python run_after_boot.py

停下点: 跑完会在 ./out/ 生成 4 张参考图，由 agent 呈现给用户确认。
"""
import os, sys, subprocess, time, re

HOST = os.environ.get("COMFY_HOST", "43.155.217.119")  # 实例 IP 每次开机都变，可用环境变量覆盖
SSH_PORT = 22
USER = "root"
COMFY_PORT = 6889
HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable


def _env():
    e = dict(os.environ)
    if "SSH_PASS" not in e:
        print("ERROR: 请先设置 SSH_PASS 环境变量（HAI 实例 root 密码）")
        sys.exit(2)
    return e


def ssh(cmd, timeout=900):
    r = subprocess.run(
        [PY, os.path.join(HERE, "ssh_run.py"),
         "--host", HOST, "--port", str(SSH_PORT), "--user", USER,
         "--cmd", cmd, "--timeout", str(timeout)],
        env=_env(), capture_output=True, text=True)
    return r.stdout + r.stderr


def upload(local, remote):
    r = subprocess.run(
        [PY, os.path.join(HERE, "sftp_upload.py"), HOST, str(SSH_PORT), USER, local, remote],
        env=_env(), capture_output=True, text=True)
    return r.stdout + r.stderr


def curl_comfy(path, timeout=12):
    r = subprocess.run(
        ["curl", "-s", "--noproxy", HOST, "--max-time", str(timeout),
         f"http://{HOST}:{COMFY_PORT}{path}"],
        capture_output=True, text=True)
    return r.stdout


def probe_comfy():
    return "comfyui_version" in curl_comfy("/system_stats")


def wait_comfy(tries=40, gap=5):
    for i in range(1, tries + 1):
        if probe_comfy():
            return True
        print(f"  等 ComfyUI 重启... {i}/{tries}")
        time.sleep(gap)
    return False


def gen_refs(mode):
    r = subprocess.run([PY, os.path.join(HERE, "gen_refs.py"), mode],
                       capture_output=True, text=True, timeout=1200)
    out = r.stdout + r.stderr
    print(out)
    return ("执行出错" not in out) and ("Traceback" not in out), out


def patch_unet(q):
    p = os.path.join(HERE, "gen_refs.py")
    s = open(p, encoding="utf-8").read()
    s2 = re.sub(r'UNET = "qwen-image-edit-2511-[A-Z0-9_]+\.gguf"',
                f'UNET = "qwen-image-edit-2511-{q}.gguf"', s)
    open(p, "w", encoding="utf-8").write(s2)
    print(f"  gen_refs.py UNET 常量 -> {q}")


def main():
    print("==[0]== 探测 ComfyUI 在线状态")
    print("  在线" if probe_comfy() else "  未在线（换权重后会触发 supervisor 重启）")

    print("==[1]== 上传换权重脚本到实例")
    print(upload(os.path.join(HERE, "swap_weights.sh"), "/root/swap_weights.sh").strip())

    print("==[2]== 换完整权重 Q4_K_M (ModelScope 镜像, 约 13G, 可能数分钟)")
    print(ssh("bash /root/swap_weights.sh Q4_K_M", timeout=900).strip())

    print("==[3]== 等 ComfyUI 重启就绪")
    if not wait_comfy():
        print("  ERROR: ComfyUI 未就绪"); sys.exit(3)
    print("  ComfyUI 就绪")

    print("==[4]== txt2img 链路验证 (gen_refs.py test)")
    ok, out = gen_refs("test")
    if not ok:
        if ("out of memory" in out.lower()) or ("cuda out of memory" in out.lower()):
            print("  检测到 OOM -> 自动回退 Q3_K_M 重跑")
            patch_unet("Q3_K_M")
            print(ssh("bash /root/swap_weights.sh Q3_K_M", timeout=900).strip())
            if not wait_comfy():
                print("  ERROR: 回退后 ComfyUI 未就绪"); sys.exit(3)
            ok, out = gen_refs("test")
        if not ok:
            print("  ERROR: txt2img 验证仍失败，详见上方输出"); sys.exit(4)
    print("  txt2img 链路 OK")

    print("==[5]== 出 4 张多角度参考图 (gen_refs.py full)")
    ok, out = gen_refs("full")
    if not ok:
        print("  ERROR: 出图失败，详见上方输出"); sys.exit(5)

    print("=== 完成 ===")
    print("4 张参考图已生成于:", os.path.join(HERE, "out"))


if __name__ == "__main__":
    main()
