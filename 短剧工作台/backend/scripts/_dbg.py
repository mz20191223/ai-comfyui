import sys
sys.path.insert(0, r"D:\Aicomfyui\短剧工作台\backend")
from pathlib import Path
from app.parsers import md_video_parser as VP
from app.parsers import md_common as C

doc = Path(r"D:\Aicomfyui\minimax3创作内容\deepseek分镜\第1集_中文视频提示词_核对版.md")
text = doc.read_text(encoding="utf-8", errors="ignore")
shots = VP.parse_video_doc(text)
print("解析镜头数:", len(shots))
v = next((s for s in shots if s.shot_code == "14d"), None)
if v:
    print("title:", v.title)
    print("gen_mode:", v.gen_mode, "dur:", v.duration_sec, "res:", v.resolution)
    print("constraints 条数:", len(v.constraints))
    print("constraints_text:", repr(v.constraints_text)[:300])
    print()
    # 手动复现切段
    blocks = C.split_shot_blocks(text)
    b = next(x for x in blocks if x.code == "14d")
    for i, ln in enumerate(b.lines):
        key = VP._match_section(ln)
        if key:
            print(f"  mark line[{i}] key={key} rest={VP._section_rest(ln)[:60]!r}")
    print()
    print("extract_numbered_items 测试:")
    sample = "① 测试一 ② 测试二 ③ 测试三"
    print(" ->", C.extract_numbered_items(sample))
