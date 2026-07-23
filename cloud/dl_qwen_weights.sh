#!/usr/bin/env bash
# 实例侧 Qwen-Image-Edit-2511 权重下载/续传脚本（wget -c 断点续传）
# 用法： setsid bash /root/dl_qwen.sh > /root/dl.log 2>&1 &
cd /root/ComfyUI/models
mkdir -p unet text_encoders vae loras
wget -c -L --tries=0 --timeout=60 -O unet/qwen-image-edit-2511-Q4_K_M.gguf \
  "https://huggingface.co/unsloth/Qwen-Image-Edit-2511-GGUF/resolve/main/qwen-image-edit-2511-Q4_K_M.gguf" &
wget -c -L --tries=0 --timeout=60 -O text_encoders/Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf \
  "https://huggingface.co/unsloth/Qwen2.5-VL-7B-Instruct-GGUF/resolve/main/Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf" &
wget -c -L --tries=0 --timeout=60 -O text_encoders/mmproj-BF16.gguf \
  "https://huggingface.co/unsloth/Qwen2.5-VL-7B-Instruct-GGUF/resolve/main/mmproj-BF16.gguf" &
wget -c -L --tries=0 --timeout=60 -O vae/qwen_image_vae.safetensors \
  "https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/vae/qwen_image_vae.safetensors" &
wait
echo ALL_DONE >> /root/dl.log
