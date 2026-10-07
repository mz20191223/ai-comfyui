# -*- coding: utf-8 -*-
"""回填第1集 14c→23 的景别/视角/运镜/主体位置。

判定依据 = 各镜自己的分镜图提示词 + 视频提示词原文（见 tools/dump_shots.py 输出）。
**只写镜头语言字段，不改 image_prompt / video_prompt**——这些镜头的提示词已定稿。

来源标记：
  [原文] 提示词里直接写了景别/机位/运镜
  [推断] 提示词没写景别，按画面内容判断
"""
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, r"D:/Aicomfyui/短剧工作台/backend")
from app.services.wizard_service import compose_image_note  # noqa: E402

BASE = "http://127.0.0.1:8770/api"
OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))

# id: (景别, 视角, 运镜, 主体位置, 依据, 来源)
PLAN = {
    113: ("MCU", "EYE_LEVEL", "DOLLY_IN", "中心·近",
          "分镜图写「中近景·正对着过客拍摄」；视频写「极缓慢推近约0.2米」", "原文"),
    114: ("MS", "EYE_LEVEL", "DOLLY_OUT", "上中·中",
          "分镜图写「中景…魅影位于画面中央偏上」；视频写「缓慢后拉约0.4米」", "原文"),
    115: ("LS", "EYE_LEVEL", "DOLLY_IN", "下中·中",
          "分镜图写「全景构图…过客位于画面中心偏下」；视频运镜写「固定中景、轻微推近」"
          "（景别以分镜图的「全景」为准，视频句里的「中景」与分镜图不一致，已记入报告）", "原文"),
    116: ("MS", "EYE_LEVEL", "DOLLY_OUT", "中心·中",
          "分镜图写「过客中景，从腰部以上入镜」；视频写「快速后拉 + 全屏震动」", "原文"),
    117: ("ECU", "HIGH_ANGLE", "STATIC", "中心·近",
          "分镜图写「双手在键盘上快速飞舞的极近景特写，双手占据画面大部分」；"
          "视频写「固定微特写」；机位判为俯拍（分镜图「显示器红光从上方照下来」）", "原文"),
    118: ("CU", "EYE_LEVEL", "DOLLY_IN", "下中·近",
          "分镜图为屏幕与人物叠化，「画面下方为过客的面部反应特写」→ 特写；"
          "视频写「缓推面板」", "原文"),
    119: ("LS", "EYE_LEVEL", "DOLLY_OUT", "下中·中",
          "分镜图写「全景画面，过客位于画面中心偏下，被三魔同时攻击」；"
          "视频写「快速后拉 + 全屏震动」", "原文"),
    120: ("MS", "EYE_LEVEL", "DOLLY_IN", "中心·中",
          "分镜图未写景别，按「过客坐在地上、面前显示器」判为中景；视频写「缓推靠近屏幕」", "推断"),
    121: ("MS", "EYE_LEVEL", "TILT", "中心·中",
          "分镜图未写景别，按「过客半起身、右手伸向屏幕」判为中景；视频写「尾端轻微上摇」", "推断"),
}


def patch(sid: int, detail: dict) -> dict:
    req = urllib.request.Request(
        f"{BASE}/shots/{sid}", data=json.dumps({"detail": detail}).encode("utf-8"),
        method="PATCH", headers={"Content-Type": "application/json"})
    with OP.open(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    before = {}
    for sid in PLAN:
        with OP.open(f"{BASE}/shots/{sid}", timeout=30) as r:
            d = json.loads(r.read().decode("utf-8"))
        det = d.get("detail") or {}
        before[sid] = {k: det.get(k) for k in
                       ("image_prompt", "video_prompt", "camera_shot", "angle", "movement")}
        print(f"[{sid}] {(d.get('shot') or {}).get('shot_code')}  原值: 景别={det.get('camera_shot') or '-'} "
              f"视角={det.get('angle') or '-'} 运镜={det.get('movement') or '-'}")

    print("\n开始回填 ...")
    for sid, (size, angle, mv, pos, why, src) in PLAN.items():
        note = compose_image_note(size, angle, pos)
        r = patch(sid, {
            "camera_shot": size, "angle": angle, "movement": mv,
            "subject_position": pos, "camera_note": note,
        })
        det = r.get("detail") or {}
        code = (r.get("shot") or {}).get("shot_code")
        ok = (det.get("camera_shot") == size and det.get("angle") == angle
              and det.get("movement") == mv)
        print(f" {'OK ' if ok else 'FAIL'} [{sid}] {str(code):<6} "
              f"{size}/{angle}/{mv}/{pos}  [{src}]  {note}")

    print("\n校验：提示词有没有被改动 ...")
    bad = 0
    for sid, old in before.items():
        with OP.open(f"{BASE}/shots/{sid}", timeout=30) as r:
            d = json.loads(r.read().decode("utf-8"))
        det = d.get("detail") or {}
        same = (det.get("image_prompt") == old["image_prompt"]
                and det.get("video_prompt") == old["video_prompt"])
        if not same:
            bad += 1
            print(f"  !! [{sid}] 提示词被改动了")
    print("  提示词全部保持原样" if bad == 0 else f"  {bad} 个镜头提示词被改动，需回滚")


if __name__ == "__main__":
    main()
