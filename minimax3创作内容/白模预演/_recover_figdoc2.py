# -*- coding: utf-8 -*-
import re

src = r"D:\Aicomfyui\minimax3创作内容\deepseek分镜\_corrupted_20260909.md"
dst = r"D:\Aicomfyui\minimax3创作内容\deepseek分镜\_recovered2_20260909.md"

new = open(src, encoding="utf-8").read().split("\n")
anchor = "**衔接说明：** 无（全片首帧）"
idx = [i for i, l in enumerate(new) if l == anchor]
print("anchor at:", idx)

second = idx[-1]
rec = new[:27] + new[second:]
s = "\n".join(rec)
open(dst, "w", encoding="utf-8").write(s)

print("recovered lines:", len(rec), "chars:", len(s))
print("镜头标题:", len(re.findall(r"^## 镜头", s, re.M)))
print("衔接说明:", len(re.findall(r"^\*\*衔接说明", s, re.M)))
print("A./B.块:", len(re.findall(r"^\*\*[AB]\. 出 0114", s, re.M)))
print("14a 提示词块:", len(re.findall(r"^\*\*分镜图提示词（0114", s, re.M)))
print("0114a_end 出现次数:", s.count("0114a_end"))
print("\n--- 行 25-30 ---")
for i in range(25, 31):
    print(i + 1, rec[i][:60])
print("\n--- 14a 段前 6 行 ---")
i14 = next(i for i, l in enumerate(rec) if l.startswith("## 镜头14a"))
for j in range(i14, i14 + 6):
    print(j + 1, rec[j][:70])
