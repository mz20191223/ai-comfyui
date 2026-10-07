# 给旧版 model_management 加 flash_attention_enabled()，让新版 attention.py 能 import。
# 旧版无 flash attention 开关，默认返回 False（走标准 attention，T4 上 flash 本就不可用）。
p = "/root/ComfyUI/comfy/model_management.py"
s = open(p, encoding="utf-8").read()
if "def flash_attention_enabled" not in s:
    s += (
        "\n\n"
        "def flash_attention_enabled():\n"
        "    # 旧版无 flash attention 开关；默认关闭，走标准 attention（兼容新版 text_encoders）\n"
        "    return False\n"
    )
    open(p, "w", encoding="utf-8").write(s)
    print("MM_PATCH_OK")
else:
    print("ALREADY_PATCHED")
