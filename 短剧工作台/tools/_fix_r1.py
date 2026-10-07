p = r"D:\Aicomfyui\短剧工作台\backend\app\services\script_service.py"
raw = open(p, "rb").read()
text = raw.decode("utf-8")
lines = text.split("\n")
for idx, l in enumerate(lines):
    if "从剧本逻辑里识别、自由写" in l:
        # 原行内部用了 ["过客", "公司办公室"]，双引号把字符串截断 -> 去掉内部引号
        lines[idx] = '        "（从剧本逻辑里识别、自由写，例如 过客、公司办公室）；"'
        print("fixed line %d" % (idx + 1))
        break
else:
    raise SystemExit("r1 sample line not found")
open(p, "wb").write("\n".join(lines).encode("utf-8"))
print("done")
