# -*- coding: utf-8 -*-
"""临时自检：预览改动后的前后端一致性。"""
import py_compile
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = r"D:\Aicomfyui\短剧工作台"
VUE = ROOT + r"\frontend\src\views\Script.vue"
PY = ROOT + r"\backend\app\routers\scripts.py"

t = open(VUE, encoding="utf-8").read()
print("previewText.value 残留:", t.count("previewText.value"))
print("previewData 出现次数:", t.count("previewData"))
print("computed 是否已导入:", bool(re.search(r"import\s*\{[^}]*computed", t)))
print("dialog 里有 radio-group:", "el-radio-group" in t)
print("instruction 传参存在:", "instruction" in t)

py_compile.compile(PY, doraise=True)
print("scripts.py 语法 OK")

b = open(PY, encoding="utf-8").read()
print("preview 返回 generate:", '"generate"' in b)
print("preview 返回 revise:", '"revise"' in b)
print("ReviseIn.instruction:", "instruction: str | None = None" in b)
