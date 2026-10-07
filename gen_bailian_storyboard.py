"""gen_bailian_storyboard.py — 用百炼 wan2.7-image 出 25 宫格分镜图（结构 B：25 镜叙事分镜）。

读 storyboard_25grid.json 的 shots（25 个正式分镜脚本），逐张出图存到 grid/。
角色一致性：默认用 JSON 里的 reference_image（peach_role_v6.png）作为参考图锁角色（方案A），
即调用 wan2.7-image 的图文参考出图，避免抽卡/走样（如人类手）。
character_lock=false 的镜（如 s01 角色未入画）不注入参考图，仅文字出图。

用法:
  python gen_bailian_storyboard.py --key "sk-xxx" [--model wan2.7-image] [--size 1024*1024]
  python gen_bailian_storyboard.py --key "sk-xxx" --only s01,s05   # 只补指定镜
key 也可通过环境变量 DASHSCOPE_API_KEY 传入。
"""
import argparse, json, os, sys, urllib.request
import bailian_image_ref as R   # 复用上传/参考图出图逻辑


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default=os.environ.get("DASHSCOPE_API_KEY", ""), required=False)
    ap.add_argument("--json", default="storyboard_25grid.json")
    ap.add_argument("--model", default="wan2.7-image")
    ap.add_argument("--size", default="1024*1024")
    ap.add_argument("--outdir", default="grid")
    ap.add_argument("--ref", default=None,
                    help="角色参考图路径；默认读 JSON 的 reference_image；传 none 关闭锁角色")
    ap.add_argument("--only", default="", help="只生成指定镜，逗号分隔，如 s01,s05")
    a = ap.parse_args()
    if not a.key:
        print("ERROR: 需 --key 或环境变量 DASHSCOPE_API_KEY"); sys.exit(1)

    only = set(x.strip() for x in a.only.split(",") if x.strip()) if a.only else None

    cfg = json.load(open(a.json, "r", encoding="utf-8"))
    shots = cfg["shots"]
    os.makedirs(a.outdir, exist_ok=True)

    # 角色锁：上传参考图一次
    ref_arg = a.ref if a.ref is not None else cfg.get("reference_image")
    ref_url = None
    if ref_arg and ref_arg.lower() != "none":
        print(f"[ref] 上传角色参考图 {ref_arg} ...")
        ref_url = R.upload_image(a.key, ref_arg)
        print(f"[ref] OK {ref_url}")

    n = 0
    for s in shots:
        sid = s["id"]
        if only and sid not in only:
            continue
        prompt = s["prompt"]
        env = cfg.get("env_anchor")
        if env:
            prompt = f"{prompt}。{env}"
        lock = s.get("character_lock", True) and ref_url is not None
        try:
            if lock:
                url = R.gen_with_ref(a.key, ref_url, prompt, a.model, a.size)
            else:
                url = R.gen_one(a.key, prompt, a.model, a.size)
            with urllib.request.urlopen(url, timeout=60) as r2:
                img = r2.read()
            fname = f"{a.outdir}/{sid}.png"
            with open(fname, "wb") as f:
                f.write(img)
            n += 1
            print(f"[{n}/{len(shots)}] {sid} (lock={lock}) {len(img)}B -> {fname}")
        except Exception as e:
            print(f"FAIL {sid}: {e}")
    print(f"DONE {n}/{len(shots)} -> {a.outdir}/")


if __name__ == "__main__":
    main()
