#!/bin/bash
# 下载 Qwen-Image base GGUF（文生图专用，非 edit 模型）到 ComfyUI 的 unet 目录
# 用法：在 DSW Terminal 粘贴本脚本内容后回车执行；下完后在 ComfyUI 加载 qwen_image_t2i_base_ui.json
set -e

# ===== 保存位置（已写死）=====
DEST_DIR="/root/ComfyUI/models/unet"
OUT_FILE="$DEST_DIR/qwen-image-Q4_K_S.gguf"

mkdir -p "$DEST_DIR"

echo "==> 下载目标: $OUT_FILE"
echo "==> 若需断点续传，重复执行本脚本即可（curl -C - 会自动续传）"

# 后台下载，进程 detached；日志写到 /tmp/qwenbase_dl.log
nohup curl -L --retry 3 --retry-delay 5 -C - \
  "https://hf-mirror.com/city96/Qwen-Image-gguf/resolve/main/qwen-image-Q4_K_S.gguf" \
  -o "$OUT_FILE" > /tmp/qwenbase_dl.log 2>&1 &

echo "==> 已在后台启动下载，PID $!"
echo "    查看进度: tail -f /tmp/qwenbase_dl.log"
echo "    查看大小: ls -lh $OUT_FILE"
echo "    预期大小: 约 12.1 GB (Q4_K_S)"
echo ""
echo "==> 下完后在 ComfyUI 加载 D:\\Aicomfyui\\pai\\workflows\\qwen_image_t2i_base_ui.json 即可文生图"
echo "==> 若 UnetLoaderGGUF 下拉里看不到该文件，把它也放一份到 models/diffusion_models/ :"
echo "    cp $OUT_FILE /root/ComfyUI/models/diffusion_models/qwen-image-Q4_K_S.gguf"
