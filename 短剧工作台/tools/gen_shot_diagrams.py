# -*- coding: utf-8 -*-
"""批量生成镜头设置向导的示意图（景别 7 + 视角 8）。
用 Agnes image-2.1-flash（免费），竖屏 9:16，固定角色与画风模板保证一致性。
"""
import sys
import time
import urllib.request
import urllib.error
import json
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

API_KEY = os.environ.get("AGNES_API_KEY", """")
BASE_URL = "https://apihub.agnes-ai.com/v1/images/generations"
MODEL = "agnes-image-2.1-flash"
SIZE = "1024x1792"
OUT_DIR = Path(r"D:/Aicomfyui/短剧工作台/assets-src/shot-diagrams")  # 原图放这儿，不进发布目录

CHARS = (
    "只画一个人物：一位日式动漫风格的青年男性角色，黑色短发、额前有碎发、"
    "五官清秀、穿纯白色圆领短袖T恤和深色长裤。"
)
STYLE = (
    "画面为黑白漫画线稿示意图：人物只用干净利落的黑色单线勾勒轮廓，"
    "不做阴影、不做网点、不做渐变填充，背景为纯白色完全留白。"
)
BAN = (
    "画面中不要出现任何文字、汉字、字母、数字、符号、标注、箭头、"
    "参考线、网格线、边框、水印。"
)
FRAME = "整体为严格的竖向 9:16 竖构图。"

BODY_FULL = "构图：全景，人物全身完整入画，从头顶到脚底都清晰可见。"

ITEMS = [
    ("size_ELS", "构图：极远景。人物站在画面正中央，整个人物身高只占画面高度的八分之一左右，显得非常渺小，人物四周都是大面积的空白空间。"),
    ("size_LS",  BODY_FULL + "人物身高占画面高度的三分之二左右，头顶上方和脚底下方各留出一段空白。"),
    ("size_MLS", "构图：中全景。人物从膝盖以上入画，画面的下边缘正好切在人物的膝盖位置。"),
    ("size_MS",  "构图：中景。人物从腰部以上入画，画面的下边缘正好切在人物的腰胯位置。"),
    ("size_MCU", "构图：中近景。人物从胸部以上入画，画面的下边缘正好切在人物的胸口位置。"),
    ("size_CU",  "构图：特写。人物从肩膀以上入画，面部占据画面主体，头顶接近画面的上边缘。"),
    ("size_ECU", "构图：大特写。只画人物的一双眼睛和眉毛区域，双眼占据画面中央绝大部分面积，画面的上下左右都被面部皮肤切割。"),

    ("angle_EYE_LEVEL", BODY_FULL + "视角：平视机位，摄影机与人物视线同高，正面对着人物平拍。"),
    ("angle_HIGH_ANGLE", BODY_FULL + "视角：高机位俯拍，摄影机位于人物头顶上方斜向下拍摄，人物显得矮小，可看到头顶与双肩，画面中地面占比明显增多。"),
    ("angle_LOW_ANGLE", BODY_FULL + "视角：低机位仰拍，摄影机位于人物腰部以下向上拍摄，人物显得高大挺拔，可以清楚看到下巴底面与鼻底，画面上方留白明显增多。"),
    ("angle_BIRD_EYE", BODY_FULL + "视角：垂直鸟瞰，摄影机位于人物正上方垂直向下拍摄，画面中只看到人物的头顶、双肩以及脚下的地面，人物呈明显的俯视缩短透视。"),
    ("angle_DUTCH", BODY_FULL + "视角：荷兰角倾斜构图，摄影机保持平视，但整个画面向左倾斜约二十度，画框是斜的，人物在画面中依然笔直站立。"),
    ("angle_OVER_SHOULDER", BODY_FULL + "视角：过肩镜头，画面右侧前景出现另一人的肩膀和后脑勺的纯黑剪影，主体人物位于画面左中部。"),
    ("angle_POV", "视角：第一人称主观镜头，画面下方出现这个人自己向前伸出的双臂与双手，朝向画面正前方，完全看不到人物本人的脸。"),
    ("angle_BEHIND", "视角：背面机位，只能看到人物的后背和后脑勺，完全看不到五官和正脸。"),
]


def gen(name: str, framing: str, retries: int = 3) -> tuple:
    prompt = f"{CHARS}{framing}{STYLE}{BAN}{FRAME}"
    out = OUT_DIR / f"{name}.png"
    payload = {"model": MODEL, "prompt": prompt, "size": SIZE, "n": 1}
    last_err = ""
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                BASE_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Authorization": f"Bearer {API_KEY}",
                         "Content-Type": "application/json; charset=UTF-8"},
                method="POST",
            )
            op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with op.open(req, timeout=180) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            url = result["data"][0]["url"]
            op2 = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with op2.open(url, timeout=180) as r:
                data = r.read()
            # 一次性写入最终文件名（绿盾规则：创建后不再改名/覆盖）
            with open(out, "wb") as f:
                f.write(data)
            return (name, True, f"{len(data)/1024:.0f} KB")
        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code}: {e.read().decode('utf-8', 'ignore')[:160]}"
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
        time.sleep(4 * attempt)
    return (name, False, last_err)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    ok = 0
    with ThreadPoolExecutor(max_workers=3) as pool:
        futs = {pool.submit(gen, n, f): n for n, f in ITEMS}
        for fut in as_completed(futs):
            name, success, msg = fut.result()
            print(f"[{'OK ' if success else 'FAIL'}] {name:22s} {msg}", flush=True)
            ok += int(success)
    print(f"\n完成 {ok}/{len(ITEMS)}，耗时 {time.time()-t0:.0f}s")


if __name__ == "__main__":
    sys.exit(main())
