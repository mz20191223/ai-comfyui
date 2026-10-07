"""不花钱的端到端验证：临时项目 → 落库分集+镜头 → 回填双份提示词 → 校验槽位与 Image N 编号。

全程走真实 HTTP 接口（不起 LLM），无论成败最后都删掉临时项目，不碰用户真实项目。
"""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8770/api"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

fails: list[str] = []


def call(method: str, path: str, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req, timeout=60)
        raw = r.read().decode("utf-8")
        return r.status, (json.loads(raw) if raw.strip() else None)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")[:700]


def show(tag, code, data):
    ok = code < 300
    print(f"[{'OK ' if ok else 'ERR'}] {tag} -> {code}")
    if not ok:
        print("     ", data)
    return ok


def check(cond, msg):
    print(("   [PASS] " if cond else "   [FAIL] ") + msg)
    if not cond:
        fails.append(msg)


pid = None
try:
    code, proj = call("POST", "/projects", {"name": "ZZ_临时验证_镜头清单", "genre": "软科幻", "aspect_ratio": "9:16"})
    assert show("建项目", code, proj), proj
    pid = proj["id"]

    for t, n in (("character", "阿吉"), ("scene", "车间")):
        c, a = call("POST", f"/projects/{pid}/assets", {"asset_type": t, "name": n})
        show(f"建资产 {n}", c, a)

    outline = {
        "title": "临时验证剧", "logline": "一句话梗概",
        "episodes": [{
            "number": 1, "title": "第1集 试机", "synopsis": "梗概一",
            "script": "场景：车间/夜\n阿吉：这台机器坏了。",
            "shots": [
                {"shot_code": "1", "title": "阿吉站在机器前",
                 "summary": "阿吉站在车间机器前，抬头看指示灯",
                 "assets": ["阿吉", "车间"], "dialog": [], "shot_size": "中景", "duration": 4},
                {"shot_code": "2", "title": "指示灯变红",
                 "summary": "机器指示灯由绿转红，红光打在阿吉脸上",
                 "assets": ["阿吉", "车间", "不存在的资产"],
                 "dialog": [{"role": "阿吉", "text": "这台机器坏了。"}],
                 "shot_size": "特写", "duration": 5},
            ],
        }],
    }
    code, res = call("POST", f"/projects/{pid}/scripts/apply-outline",
                     {"outline": outline, "replace_shots": False})
    assert show("落库分集+镜头", code, res), res
    print("     ", {k: v for k, v in res.items() if k != "unmatched_assets"},
          "未匹配资产:", res["unmatched_assets"])
    check(res["unmatched_assets"] == ["不存在的资产"], "编造的资产名被识别为未匹配（不落库）")

    code, eps = call("GET", f"/projects/{pid}/episodes")
    eid = eps[0]["id"]

    code, sl = call("GET", f"/episodes/{eid}/shot-list")
    assert show("读镜头清单", code, sl), sl
    for s in sl["shots"]:
        vs = sorted(l["slot_index"] for l in s["links"] if l["target_side"] == "video")
        ins = sorted(l["slot_index"] for l in s["links"] if l["target_side"] == "image")
        print(f"     镜{s['shot_code']} 视频槽位={vs} 图片槽位={ins}")
        check(vs == list(range(0, len(vs))), f"镜{s['shot_code']} 视频槽位从 0 连续无空档")
        check(ins == list(range(1, len(ins) + 1)), f"镜{s['shot_code']} 图片槽位从 1 连续无空档")

    items = [
        {"shot_code": "1",
         "image_body": "阿吉站在车间机器前，抬头看指示灯。中景，主体居中。写实摄影，冷白日光。",
         "video_body": "机位：平视视角；运镜：固定机位。\n画面主体：\n[Shot 1] Live-action，cinematic，"
                       "竖屏 9:16 构图。阿吉站在机器前抬头。\n\n"
                       "画面任务指令（严格按时序，画面与声音同步生成）：\n0.0–2.0秒：阿吉站着不动。\n"
                       "2.0–4.0秒：指示灯闪一下。"},
        {"shot_code": "2",
         "image_body": "参考图1（阿吉）锁定的脸；机器指示灯由绿转红，红光打在脸上。特写。写实摄影。",
         "video_body": "素材关系声明：\nImage 1：xxx.jpg\n机位：过肩机位；运镜：推近。\n画面主体：\n"
                       "[Shot 1] Live-action，cinematic，竖屏 9:16 构图。指示灯转红。\n\n"
                       "画面任务指令（严格按时序，画面与声音同步生成）：\n0.0–2.5秒：绿灯。\n"
                       "2.5–5.0秒：转成红灯。\n阿吉：\"这台机器坏了。\""},
    ]
    code, ap = call("POST", f"/episodes/{eid}/shot-prompts/apply", {"items": items})
    assert show("回填提示词", code, ap), ap

    code, sl2 = call("GET", f"/episodes/{eid}/shot-list")
    print("\n" + "=" * 74)
    for s in sl2["shots"]:
        print(f"##### 镜 {s['shot_code']} #####")
        print("--- image_prompt ---\n" + str(s["image_prompt"]))
        print("--- video_prompt ---\n" + str(s["video_prompt"]))
        print("--- prefix ---\n" + str(s["video_prompt_prefix"]))
        print("-" * 74)

    s1, s2 = sl2["shots"][0], sl2["shots"][1]
    check(bool(s1["image_prompt"]), "镜1 分镜图提示词已写入")
    check(bool(s2["image_prompt"]), "镜2 分镜图提示词已写入（模型写了参考图前缀也不该被清空）")
    check("参考图1（阿吉）严格锁定" in s1["image_prompt"], "镜1 图片侧声明自动拼为「参考图1（阿吉）…」")
    check("参考图1（阿吉）" not in s2["image_prompt"].split("竖屏9:16构图")[0][:20]
          or s2["image_prompt"].count("参考图1（阿吉）") == 1,
          "镜2 模型自写的「参考图N（…）」前缀没被重复堆叠")
    check(s2["image_prompt"].startswith("参考图1（阿吉）"), "镜2 图片侧声明由工作台拼在最前")
    check("竖屏9:16构图。" in s1["image_prompt"], "分镜图提示词带构图锚点")
    check(bool(s1["video_prompt_prefix"].startswith("For the target video")), "视频首行 I2VA 声明已写入")

    for s in sl2["shots"]:
        vp = s["video_prompt"]
        check("素材关系声明：" in vp, f"镜{s['shot_code']} 视频提示词含素材关系声明")
        check("Image 1（= Picture 1）" in vp and "0101.jpg" in vp.replace("0102.jpg", "0101.jpg")
              or "Image 1（= Picture 1）" in vp, f"镜{s['shot_code']} Image 1 = 首帧分镜图")
        # 声明里的 Image N 必须与真实视频槽位一致：Image N ↔ slot N-1
        want = {l["slot_index"] + 1: l["file_name"] for l in s["links"] if l["target_side"] == "video"}
        got = {}
        for m in re.finditer(r"^Image\s+(\d+)[^：]*：([^\n—]+)", vp, re.M):
            got[int(m.group(1))] = m.group(2).strip()
        check(got == {k: (v or "").strip() for k, v in want.items()},
              f"镜{s['shot_code']} Image N 编号与真实视频槽位逐项一致 → {got}")
        check("机位：" in vp and "画面任务指令" in vp, f"镜{s['shot_code']} 视频正文含机位与任务指令")
        check("黑场" not in vp or "严禁黑场" in vp, f"镜{s['shot_code']} 无违规转场描述")
        if s["shot_code"] == "2":
            check(vp.count("素材关系声明") == 1, "模型误写的素材声明已被剥掉，只剩工作台拼的那份")
            check("Audio 1：阿吉音色参考" in vp, "有台词的镜头自动补 Audio 1")
    check("参考图" not in s2["video_prompt"].split("\n\n", 1)[1], "视频正文里没有图片侧措辞串味")
finally:
    if pid:
        print("\n清理临时项目:", call("DELETE", f"/projects/{pid}"))

print("\n" + ("全部断言通过 ✓" if not fails else f"失败 {len(fails)} 项：\n  - " + "\n  - ".join(fails)))
sys.exit(1 if fails else 0)
