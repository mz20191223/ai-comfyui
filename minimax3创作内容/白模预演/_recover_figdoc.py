# -*- coding: utf-8 -*-
import re

src = r"D:\Aicomfyui\minimax3创作内容\deepseek分镜\_corrupted_20260909.md"
dst = r"D:\Aicomfyui\minimax3创作内容\deepseek分镜\_recovered_20260909.md"

new = open(src, encoding="utf-8").read().split("\n")
print("corrupted lines:", len(new))

# 反推：new = L[0:359] + [""] + L[365:368] + [""] + L[359:365] + [""] + [] + [""] + L[27:N]
rec = new[0:359] + new[364:370] + new[360:363] + new[713:]

# 校验拼接处
print("--- join check ---")
print("L[358]:", rec[358][:60])
print("L[359]:", rec[359][:60])
print("L[364]:", rec[364][:60])
print("L[365]:", rec[365][:60])
print("L[367]:", rec[367][:60])
print("L[368]:", rec[368][:60])

s = "\n".join(rec)
open(dst, "w", encoding="utf-8").write(s)
print("\nrecovered lines:", len(rec), "chars:", len(s))
print("镜头标题:", len(re.findall(r"^## 镜头", s, re.M)))
print("衔接说明:", len(re.findall(r"^\*\*衔接说明", s, re.M)))
print("A./B.块:", len(re.findall(r"^\*\*[AB]\. 出 0114", s, re.M)))
print("14a 提示词块:", len(re.findall(r"^\*\*分镜图提示词（0114", s, re.M)))
