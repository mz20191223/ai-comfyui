"""离线验证解析器：不写库，只看解析结果是否齐全。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.parsers import md_storyboard_parser as SB  # noqa: E402
from app.parsers import md_video_parser as VD  # noqa: E402

DOCS = Path(r"D:\Aicomfyui\minimax3创作内容\deepseek分镜")

for ep in (1, 2, 3):
    sb_file = DOCS / f"第{ep}集_分镜图提示词_GPT-Img2.md"
    if not sb_file.exists():
        continue
    shots = SB.parse_storyboard_doc(sb_file.read_text(encoding="utf-8"))
    print("=" * 74)
    print(f"第{ep}集 分镜图文档：解析出 {len(shots)} 个镜头块")
    print("=" * 74)
    miss = 0
    for s in shots:
        p = (s.prompt or "").strip()
        if not p:
            miss += 1
        tag = "OK " if p else "缺!"
        print(
            f"  {tag} {s.shot_code:<10} 提示词{len(p):>5}字 参考图{len(s.ref_items):>2}张 "
            f"目标={s.target_file or '-':<18} 可选={int(s.is_optional)} 注释={len(s.notes or '')}字"
        )
        if not p:
            print(f"       标题: {s.raw_title[:90]}")
    print(f"  → 缺提示词 {miss} / {len(shots)}")

print()
print("=" * 74)
print("视频文档解析（第1集）")
print("=" * 74)
vf = DOCS / "第1集_中文视频提示词_核对版.md"
vshots = VD.parse_video_doc(vf.read_text(encoding="utf-8"))
print(f"解析出 {len(vshots)} 个镜头")
for s in vshots:
    d = s.duration_sec
    be = s.beats or []
    hc = s.constraints or []
    vp = (s.video_prompt or "").strip()
    pfx = (s.prefix or "").strip()
    ar = s.image_refs or []
    au = s.audio_file or ""
    print(
        f"  {s.shot_code:<10} 时长{d if d is not None else '-':>5} 拍点{len(be):>2} 硬约束{len(hc):>2} "
        f"参考图{len(ar):>2} 正文{len(vp):>5}字 首行{'有' if pfx else '无'} 音频{'有' if au else '无'}"
    )
    if not vp:
        print(f"       !! 正文为空，标题: {s.raw_title[:80]}")
