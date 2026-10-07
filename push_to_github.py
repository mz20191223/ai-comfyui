#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 GitHub REST Contents API 把工作流/脚本推送到仓库（绕开被篡改的 git pack）。
走 curl 子进程。GH_PAT 从环境变量读取，不落盘。
"""
import os, sys, json, base64, subprocess

REPO = "mz20191223/ai-comfyui"
API = f"https://api.github.com/repos/{REPO}"
PAT = os.environ.get("GH_PAT")
if not PAT:
    print("!! 缺少 GH_PAT 环境变量"); sys.exit(1)

# (本地路径, 仓库内路径)
FILES = [
    ("hedgehog_9grid_faceidplusv2_v2.json", "hedgehog_9grid_faceidplusv2_v2.json"),
    ("hedgehog_9grid_faceidplusv2_alt.json", "hedgehog_9grid_faceidplusv2_alt.json"),
    ("hedgehog_faceid_v2_test.json", "hedgehog_faceid_v2_test.json"),
    ("hedgehog_faceid_v2_test_alt.json", "hedgehog_faceid_v2_test_alt.json"),
    ("run_comfy.py", "run_comfy.py"),
    ("assemble_grid.py", "assemble_grid.py"),
    ("setup_and_run_hai.sh", "setup_and_run_hai.sh"),
    ("gen_faceid_v2_workflow.py", "gen_faceid_v2_workflow.py"),
    ("gen_faceid_v2_alt.py", "gen_faceid_v2_alt.py"),
    ("README.md", "README.md"),
    ("STATE.md", "STATE.md"),
]

def curl_json(method, url, data=None):
    cmd = ["curl", "-sSL", "--max-time", "60", "-w", "\n%{http_code}",
           "-H", f"Authorization: Bearer {PAT}",
           "-H", "Accept: application/vnd.github+json",
           "-H", "X-GitHub-Api-Version: 2022-11-28",
           "-X", method, url]
    if data is not None:
        tmp = "_api_body.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        cmd += ["-H", "Content-Type: application/json", "--data-binary", "@" + tmp]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    out = p.stdout.rsplit("\n", 1)
    body = out[0]
    code = out[1].strip() if len(out) > 1 else ""
    try:
        j = json.loads(body) if body.strip() else {}
    except Exception:
        j = {"_raw": body[:300]}
    return code, j

def main():
    # 1) 确认仓库 + 默认分支
    code, repo_info = curl_json("GET", API)
    if code != "200":
        print(f"!! 无法访问仓库 {REPO} (HTTP {code}): {repo_info}")
        sys.exit(1)
    branch = repo_info.get("default_branch", "main")
    print(f"==> 仓库 OK，默认分支: {branch}")

    # 2) 逐个上传
    ok = 0
    for local, repo_path in FILES:
        if not os.path.exists(local):
            print(f"  [跳过] 本地缺失: {local}")
            continue
        with open(local, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        # 查现有 sha
        gcode, gj = curl_json("GET", f"{API}/contents/{repo_path}?ref={branch}")
        sha = gj.get("sha") if gcode == "200" else None
        msg = "update " + repo_path if sha else "add " + repo_path
        payload = {"message": msg, "content": b64, "branch": branch}
        if sha:
            payload["sha"] = sha
        pcode, pj = curl_json("PUT", f"{API}/contents/{repo_path}", payload)
        if pcode in ("200", "201"):
            print(f"  [OK] {repo_path} ({'更新' if sha else '新建'})")
            ok += 1
        else:
            print(f"  [FAIL] {repo_path} HTTP {pcode}: {pj}")
    print(f"\n==> 完成: {ok}/{len(FILES)} 个文件已推送")

if __name__ == "__main__":
    main()
