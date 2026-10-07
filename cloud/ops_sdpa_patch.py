#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给旧版 ComfyUI 的 comfy/ops.py 补上 scaled_dot_product_attention（新版 text_encoders 需要）。

背景：新版 comfy/text_encoders（qwen_image/llama/qwen_vl）在 forward 时，
      attention.py 第 ~544 行调用 comfy.ops.scaled_dot_product_attention，
      旧版 0.3.14 的 ops.py 没有这个函数 -> AttributeError。

本脚本幂等：已存在则跳过；否则在文件尾部追加一个最小 shim，
仅依赖 torch.nn.functional.scaled_dot_product_attention（torch 2.5 已支持
enable_gqa / scale 参数），与调用方签名 (q,k,v, attn_mask=, dropout_p=, is_causal=, **sdpa_extra) 对齐。

实例路径：/root/ComfyUI/comfy/ops.py
"""
import math
import os
import sys

OPS = "/root/ComfyUI/comfy/ops.py"

FUNC = '''

def scaled_dot_product_attention(query, key, value, attn_mask=None, dropout_p=0.0,
                                 is_causal=False, scale=None, **kwargs):
    """Minimal shim matching new ComfyUI text_encoders usage (attention.py ~line 544)."""
    import torch
    if scale is None:
        scale = 1.0 / math.sqrt(query.size(-1))
    return torch.nn.functional.scaled_dot_product_attention(
        query, key, value, attn_mask=attn_mask, dropout_p=dropout_p,
        is_causal=is_causal, scale=scale, **kwargs)
'''


def main():
    if not os.path.exists(OPS):
        print("ERROR: 找不到", OPS)
        sys.exit(2)
    src = open(OPS).read()
    if "def scaled_dot_product_attention" in src:
        print("ALREADY_PRESENT: scaled_dot_product_attention 已存在，无需打补丁")
        sys.exit(0)
    # 保险：确保 math 已导入（shim 内部也会 import math，但顶部加一份更稳）
    if "import math" not in src:
        src = "import math\n" + src
    src = src + FUNC
    open(OPS, "w").write(src)
    # 写后语法自检，避免重启后 import 报错
    import ast
    ast.parse(open(OPS).read())
    print("PATCHED + SYNTAX_OK: 已在", OPS, "追加 scaled_dot_product_attention")


if __name__ == "__main__":
    main()
