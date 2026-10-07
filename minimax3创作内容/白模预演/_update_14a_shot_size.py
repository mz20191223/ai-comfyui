# -*- coding: utf-8 -*-
p = r"D:\Aicomfyui\minimax3创作内容\deepseek分镜\第1集_中文视频提示词_核对版.md"
s = open(p, encoding="utf-8").read()
lines = s.split("\n")

i_main = next(i for i, l in enumerate(lines) if l.startswith("## 镜头14a"))
i_alt = next(i for i, l in enumerate(lines) if l.startswith("### 【备用】14a"))
i_end = next(i for i, l in enumerate(lines) if l.startswith("## 镜头14b"))
print("main %d-%d, alt %d-%d" % (i_main, i_alt, i_alt, i_end))

common = [
    ("推进约 2.6 米、用时约 4.5 秒", "推进约 4.0 米、用时约 4.5 秒"),
    ("焦距 26mm 缓缓增至 50mm", "焦距 26mm 缓缓增至 80mm"),
    ("（中景、背对镜头、占画面高约 35%、水平居中）",
     "（中近景、背对镜头、占画面高约 70%、水平居中、头顶位于画面上方约 25% 处——与 0114b 同机位同景别）"),
    ("人物高度约占画面高度的 35%、水平居中、头顶位于画面上方约 40% 处",
     "人物高度约占画面高度的 70%、水平居中、头顶位于画面上方约 25% 处"),
]
main_only = [
    ("（26mm→30mm）", "（26mm→34mm）"),
    ("（30mm→38mm）", "（34mm→48mm）"),
    ("（38mm→45mm）", "（48mm→68mm）"),
    ("（45mm→50mm）", "（68mm→80mm）"),
]
alt_only = [
    ("（26mm→30mm）", "（26mm→34mm）"),
    ("（30mm→38mm）", "（34mm→48mm）"),
    ("（38mm→48mm）", "（48mm→74mm）"),
    ("（48mm→50mm）", "（74mm→80mm）"),
]


def rep(seg, pairs, tag):
    n = 0
    for a, b in pairs:
        c = sum(l.count(a) for l in seg)
        seg = [l.replace(a, b) for l in seg]
        n += c
        print("%s: %r -> %d 处" % (tag, a[:22], c))
    return seg


main = rep(lines[i_main:i_alt], common + main_only, "main")
alt = rep(lines[i_alt:i_end], common + alt_only, "alt")
lines = lines[:i_main] + main + alt + lines[i_end:]
open(p, "w", encoding="utf-8").write("\n".join(lines))
print("written")
