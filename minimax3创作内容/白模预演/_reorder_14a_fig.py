# -*- coding: utf-8 -*-
p = r"D:\Aicomfyui\minimax3创作内容\deepseek分镜\第1集_分镜图提示词_GPT-Img2.md"
lines = open(p, encoding="utf-8").read().split("\n")

i_a = next(i for i, l in enumerate(lines) if l.startswith("**A. 出 0114a.jpg"))
i_b = next(i for i, l in enumerate(lines) if l.startswith("**B. 出 0114a_end.jpg"))
i_p1 = next(i for i, l in enumerate(lines) if l.startswith("**分镜图提示词（0114a.jpg"))
i_p2 = next(i for i, l in enumerate(lines) if l.startswith("**分镜图提示词（0114a_end.jpg"))
i_end = next(i for i, l in enumerate(lines) if l.startswith("**衔接说明"))
print("A=%d B=%d P1=%d P2=%d end=%d" % (i_a, i_b, i_p1, i_p2, i_end))

A = lines[i_a:i_b]
B = lines[i_b:i_p1]
P1 = lines[i_p1:i_p2]
P2 = lines[i_p2:i_end]


def strip_trailing_blank(seg):
    out = list(seg)
    while out and out[-1].strip() == "":
        out.pop()
    return out


A, B, P1, P2 = map(strip_trailing_blank, (A, B, P1, P2))
new = lines[:i_a] + A + [""] + P1 + [""] + B + [""] + P2 + [""] + lines[i_end:]
open(p, "w", encoding="utf-8").write("\n".join(new))
print("reordered OK")
