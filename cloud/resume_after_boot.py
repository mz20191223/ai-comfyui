#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HAI 开机续跑（本机侧）。

背景: run_after_boot.py 的 [2] 步骤因 ssh 读超时"假失败"退出,
但实例上 swap_weights.sh(PID286)+curl(PID287) 仍在后台下载完整 13.2G 权重,
.part 已约 36%。本脚本只"读状态 + 等完成", 不重新触发下载(避免与正在跑的
curl 抢同一个 .part)。swap_weights.sh 会在 curl 下完后自动 校验->替换->杀
ComfyUI(supervisor 自动重启)。本脚本等其完成后接管 验证+出图。

兜底: 若轮询发现 swap_weights 进程消失但正式文件不存在(脚本中途失败),
则用 setsid 在实例后台重触发(脱离 ssh, 不会被通道断开杀死, -C - 断点续传)。

用法(由 agent 执行, 后台跑):
  SSH_PASS='<pwd>' COMFY_HOST='43.155.217.119' python resume_after_boot.py
"""
import os, sys, subprocess, time

HOST = os.environ.get("COMFY_HOST", "43.155.217.119")
SSH_PORT = 22
USER = "root"
COMFY_PORT = 6889
HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
UNET = "qwen-image-edit-2511-Q4_K_M.gguf"
NEW = f"/root/ComfyUI/models/unet/{UNET}"

Q = "Q4_K_M"  # 当前目标量化


def _env():
    e = dict(os.environ)
    if "SSH_PASS" not in e:
        print("ERROR: 请先设置 SSH_PASS"); sys.exit(2)
    return e


def ssh(cmd, timeout=40):
    r = subprocess.run(
        [PY, os.path.join(HERE, "ssh_run.py"),
         "--host", HOST, "--port", str(SSH_PORT), "--user", USER,
         "--cmd", cmd, "--timeout", str(timeout)],
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
    import re
    s2 = re.sub(r'UNET = "qwen-image-edit-2511-[A-Z0-9_]+\.gguf"',
                f'UNET = "qwen-image-edit-2511-{q}.gguf"', s)
    open(p, "w", encoding="utf-8").write(s2)
    print(f"  gen_refs.py UNET 常量 -> {q}")


def wait_swap_done(tries=160, gap=15):
    """轮询直到 swap_weights 进程消失 且 正式文件存在(下载完成)。
    返回 'done' / 'failed' / 'timeout'。"""
    for i in range(1, tries + 1):
        out = ssh(
            f"n=$(ps aux | grep '[s]wap_weights' | wc -l); "
            f"f=$(stat -c%s {NEW} 2>/dev/null || echo 0); "
            f"p=$(stat -c%s {NEW}.part 2>/dev/null || echo 0); "
            f"echo SWAP_N=$n FILE=$f PART=$p", timeout=40)
        n = f = p = 0
        for line in out.splitlines():
            if line.startswith("SWAP_N="): n = int(line.split("=")[1] or 0)
            elif line.startswith("FILE="): f = int(line.split("=")[1] or 0)
            elif line.startswith("PART="): p = int(line.split("=")[1] or 0)
        if n == 0 and f >= 13_000_000_000:
            print(f"  [轮询 {i}] swap 进程结束, 正式文件就绪 ({f/1e9:.2f}G)"); return "done"
        if n == 0 and f == 0:
            print(f"  [轮询 {i}] swap 进程结束但正式文件缺失 -> failed"); return "failed"
        print(f"  [轮询 {i}] 下载中: .part={p/1e9:.2f}G  正式={f/1e9:.2f}G  swap_alive={n}")
        time.sleep(gap)
    return "timeout"


def main():
    print("==[R0]== 确认当前下载/替换状态")
    st = wait_swap_done()
    if st == "timeout":
        print("  超时仍在下载, 继续等下一轮"); st = wait_swap_done()
    if st == "failed":
        print("==[R1]== swap_weights 中途失败 -> setsid 后台重触发(脱离 ssh, 断点续传)")
        ssh(f"setsid bash /root/swap_weights.sh {Q} > /root/swap_weights.log 2>&1 < /dev/null &")
        st = wait_swap_done()
        if st != "done":
            print("  ERROR: 重触发后仍未能完成权重替换"); sys.exit(3)
    elif st == "done":
        print("  权重已就绪(可能由原 swap_weights.sh 自动完成)")

    print("==[R2]== 等 ComfyUI 重启就绪(带新权重)")
    if not wait_comfy():
        print("  ERROR: ComfyUI 未就绪"); sys.exit(3)
    print("  ComfyUI 就绪")

    print("==[R3]== txt2img 链路验证 (gen_refs.py test)")
    ok, out = gen_refs("test")
    if not ok:
        if ("out of memory" in out.lower()) or ("cuda out of memory" in out.lower()):
            print("  检测到 OOM -> 自动回退 Q3_K_M 重跑")
            patch_unet("Q3_K_M")
            ssh(f"setsid bash /root/swap_weights.sh Q3_K_M > /root/swap_weights.log 2>&1 < /dev/null &")
            if wait_swap_done() != "done":
                print("  ERROR: Q3 回退未完成"); sys.exit(3)
            if not wait_comfy():
                print("  ERROR: Q3 回退后 ComfyUI 未就绪"); sys.exit(3)
            ok, out = gen_refs("test")
        if not ok:
            print("  ERROR: txt2img 验证仍失败, 见上方输出"); sys.exit(4)
    print("  txt2img 链路 OK")

    print("==[R4]== 出 4 张多角度参考图 (gen_refs.py full)")
    ok, out = gen_refs("full")
    if not ok:
        print("  ERROR: 出图失败, 见上方输出"); sys.exit(5)
    print("=== 完成 ===")
    print("4 张参考图已生成于:", os.path.join(HERE, "out"))


if __name__ == "__main__":
    main()
