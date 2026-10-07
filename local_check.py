# -*- coding: utf-8 -*-
"""本地就绪自检：编译脚本 + 校验工作流 JSON + 检查连线完整性 + (可选)解析插件节点签名。"""
import json, sys, subprocess, os

WS = r"C:\Users\Administrator\WorkBuddy\2026-07-15-13-21-24"
PY = sys.executable

print("==== [1] 编译脚本 ====")
for py in ["run_comfy.py", "assemble_grid.py", "gen_faceid_v2_workflow.py"]:
    r = subprocess.run([PY, "-m", "py_compile", os.path.join(WS, py)],
                       capture_output=True, text=True)
    print(("OK " if r.returncode == 0 else "FAIL ") + py + ("" if r.returncode == 0 else " " + r.stderr[:200]))

print("\n==== [2] 校验工作流 JSON + 连线 ====")
WFS = ["hedgehog_9grid_faceidplusv2_v2.json", "hedgehog_faceid_v2_test.json"]
for wf in WFS:
    p = os.path.join(WS, wf)
    try:
        d = json.load(open(p, encoding="utf-8"))
    except Exception as e:
        print(wf, "JSON FAIL:", e); continue
    if "nodes" in d and isinstance(d.get("nodes"), list):
        nodes = {n["id"]: n for n in d["nodes"]}
        bad = []
        for nid, n in nodes.items():
            for inp in n.get("inputs", []):
                if isinstance(inp, dict) and "link" in inp and inp["link"] is not None:
                    if not any(inp["link"] == l[0] for l in d.get("links", [])):
                        bad.append((nid, inp.get("name"), inp["link"]))
        types = sorted({n["type"] for n in d["nodes"]})
        fmt = "UI"
    else:
        ids = set(int(k) for k in d.keys())
        bad = []
        for k, v in d.items():
            if not isinstance(v, dict):
                continue
            for ink, inv in v.get("inputs", {}).items():
                if isinstance(inv, list) and len(inv) >= 1 and isinstance(inv[0], int):
                    if inv[0] not in ids:
                        bad.append((k, ink, inv[0]))
        types = sorted({v.get("class_type") for v in d.values() if isinstance(v, dict)})
        fmt = "API"
    print(f"\n{wf}  [{fmt}格式, {len(d) if fmt=='API' else len(d['nodes'])}节点]")
    print("  悬空连线:", bad if bad else "无")
    print("  使用的节点类型:", types)

print("\n==== [3] (可选) 解析插件源码节点签名 ====")
srcp = os.path.join(WS, "IPAdapterPlus_src.py")
if os.path.exists(srcp):
    src = open(srcp, encoding="utf-8").read()
    for cls in ["IPAdapterModelLoader", "IPAdapterUnifiedLoaderFaceID",
                "IPAdapterInsightFaceLoader", "IPAdapterFaceID"]:
        i = src.find("class " + cls)
        if i < 0:
            print(f"  {cls}: 源码中不存在"); continue
        j = src.find("def INPUT_TYPES", i)
        k = src.find("RETURN_TYPES", i)
        seg = src[j:j+1000] if j >= 0 else ""
        # 抽取 required/optional 的键名
        import re
        req = re.search(r'"required"\s*:\s*\{(.*?)\}', seg, re.S)
        opt = re.search(r'"optional"\s*:\s*\{(.*?)\}', seg, re.S)
        def keys(m):
            return re.findall(r'"\s*([A-Za-z0-9_]+)\s*"\s*:', m.group(1)) if m else []
        rt = src[k:k+160] if k >= 0 else ""
        print(f"  {cls}:")
        print("    REQUIRED:", keys(req))
        print("    OPTIONAL:", keys(opt))
        print("    RETURN:", rt.replace("\n", " ").strip()[:140])
else:
    print("  (IPAdapterPlus_src.py 不存在，跳过; 可在 Bash 下载后重跑)")
