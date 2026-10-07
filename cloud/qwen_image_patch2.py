# 旧版 SD1Tokenizer.tokenize_with_weights 不接受 disable_weights 参数（新版 qwen_image.py 才用）。
# 去掉该参数，让旧版按默认权重逻辑 tokenize（对 Qwen txt2img/img2img 影响很小）。
p = "/root/ComfyUI/comfy/text_encoders/qwen_image.py"
s = open(p, encoding="utf-8").read()
old = "tokens = super().tokenize_with_weights(llama_text, return_word_ids=return_word_ids, disable_weights=True, **kwargs)"
new = "tokens = super().tokenize_with_weights(llama_text, return_word_ids=return_word_ids, **kwargs)"
assert old in s, "old not found"
s = s.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(s)
print("QWEN_IMAGE_PATCH2_OK")
