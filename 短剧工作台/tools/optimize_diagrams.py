"""示意图瘦身：原图移到 assets-src（不进发布目录），发布目录只放小尺寸版本。

用法：python tools/optimize_diagrams.py [--apply]
不带 --apply 只试算体积，不动文件。
"""
import shutil
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(r"D:/Aicomfyui/短剧工作台")
PUB = ROOT / "frontend/public/shot-diagrams"
SRC = ROOT / "assets-src/shot-diagrams"
WIDTH = 320  # 预览最大显示约 150px 宽，320 足够 2x 清晰

apply = "--apply" in sys.argv

src_files = sorted(PUB.glob("*.png"))
if not src_files:
    raise SystemExit("发布目录里没有 png，可能已经瘦身过；要重跑请先从 assets-src 恢复")

print(f"源目录 {PUB}")
print(f"{'文件':<26}{'原尺寸':>12}{'原大小':>10}{'→PNG':>10}{'→WebP':>10}")
print("-" * 70)

tot_before = tot_png = tot_webp = 0
plan = []
for p in src_files:
    im = Image.open(p).convert("RGB")
    tot_before += p.stat().st_size
    h = max(1, round(im.height * WIDTH / im.width))
    small = im.resize((WIDTH, h), Image.LANCZOS)

    png = ROOT / "tools" / f"_opt_{p.stem}.png"
    webp = ROOT / "tools" / f"_opt_{p.stem}.webp"
    small.save(png, "PNG", optimize=True)
    small.save(webp, "WEBP", quality=82, method=6)
    sp, sw = png.stat().st_size, webp.stat().st_size
    tot_png += sp
    tot_webp += sw
    print(f"{p.name:<26}{f'{im.width}x{im.height}':>12}{p.stat().st_size/1024:>9.1f}K"
          f"{sp/1024:>9.1f}K{sw/1024:>9.1f}K")
    plan.append((p, png, webp))

print("-" * 70)
print(f"{'合计':<26}{'':>12}{tot_before/1024/1024:>9.2f}M{tot_png/1024/1024:>9.2f}M{tot_webp/1024/1024:>9.2f}M")

if not apply:
    print("\n（试算模式，未改动任何文件。加 --apply 执行）")
    for _, png, webp in plan:
        png.unlink(missing_ok=True)
        webp.unlink(missing_ok=True)
    sys.exit(0)

# 1) 原图搬到 assets-src（保留，不进发布目录）
SRC.mkdir(parents=True, exist_ok=True)
for p, png, webp in plan:
    shutil.move(str(p), str(SRC / p.name))
print(f"\n原图已移到 {SRC}（{len(plan)} 个）")

# 2) WebP 小图落回发布目录（比同尺寸 PNG 小约 10 倍）
for p, png, webp in plan:
    png.unlink(missing_ok=True)
    shutil.move(str(webp), str(PUB / (p.stem + ".webp")))
print(f"WebP 已生成到 {PUB}（宽 {WIDTH}px）")
print(f"发布体积 {tot_before/1024/1024:.2f} MB → {tot_webp/1024/1024:.2f} MB"
      f"（省 {(1-tot_webp/tot_before)*100:.1f}%）")
