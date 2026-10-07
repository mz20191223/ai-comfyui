# 旧版 SDTokenizer 对 has_start_token=False + end_token=None 时取 empty[0]，
# 但 Qwen2Tokenizer 对空串返回空列表导致越界。显式传 end_token=151645(<|im_end|>)。
p = "/root/ComfyUI/comfy/text_encoders/qwen_image.py"
s = open(p, encoding="utf-8").read()
old = "min_length=1, pad_token=151643, tokenizer_data=tokenizer_data"
new = "min_length=1, pad_token=151643, end_token=151645, tokenizer_data=tokenizer_data"
assert old in s, "old not found"
s = s.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(s)
print("QWEN_IMAGE_PATCH_OK")
