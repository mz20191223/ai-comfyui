# -*- coding: utf-8 -*-
import re

p = r"D:\Aicomfyui\minimax3创作内容\deepseek分镜\第1集_分镜图提示词_GPT-Img2.md"
rec = r"D:\Aicomfyui\minimax3创作内容\deepseek分镜\_recovered2_20260909.md"

# 1) 用恢复版覆盖损坏的原文件
s = open(rec, encoding="utf-8").read()
open(p, "w", encoding="utf-8").write(s)
print("restored ->", p, "chars:", len(s))

# 2) 在 14a 段内重排：A清单+首帧提示词 / B清单+落幅提示词
lines = s.split("\n")
i14 = next(i for i, l in enumerate(lines) if l.startswith("## 镜头14a"))
i_next = next(i for i, l in enumerate(lines)
              if i > i14 and (l.startswith("## 镜头") or l.startswith("## ")))
seg = lines[i14:i_next]
print("14a seg:", i14, "-", i_next, len(seg), "lines")


def find(pred):
    return next(i for i, l in enumerate(seg) if pred(l))


ia = find(lambda l: l.startswith("**A. 出 0114a.jpg"))
ib = find(lambda l: l.startswith("**B. 出 0114a_end.jpg"))
ip1 = find(lambda l: l.startswith("**分镜图提示词（0114a.jpg"))
ip2 = find(lambda l: l.startswith("**分镜图提示词（0114a_end.jpg"))
ix = find(lambda l: l.startswith("**衔接说明"))
print("sub idx: A=%d B=%d P1=%d P2=%d X=%d" % (ia, ib, ip1, ip2, ix))

A, B, P1, P2, X = seg[ia:ib], seg[ib:ip1], seg[ip1:ip2], seg[ip2:ix], seg[ix:]


def trim(x):
    o = list(x)
    while o and o[-1].strip() == "":
        o.pop()
    return o


A, B, P1, P2 = map(trim, (A, B, P1, P2))
newseg = seg[:ia] + A + [""] + P1 + [""] + B + [""] + P2 + [""] + X
lines = lines[:i14] + newseg + lines[i_next:]
out = "\n".join(lines)
open(p, "w", encoding="utf-8").write(out)
print("reordered, chars:", len(out))

# 3) 校验
print("\n--- 14a 段结构 ---")
for l in lines[i14:i14 + len(newseg)]:
    t = l.strip()
    if not t:
        continue
    print("  " + t[:66])
