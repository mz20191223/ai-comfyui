#!/usr/bin/env bash
# ============================================================
#  C2 环境补齐脚本（HAI 侧）  —— 依据 2026-07-22 实时节点探测结果
#  已存在(跳过): IPAdapter_plus 插件 / clip_vision_g.safetensors
#  需安装:
#   1) ComfyUI-AnimateDiff-Evolved 插件  (提供 ADE_AnimateDiffLoaderGen1 / RepeatLatentBatch)
#   2) ComfyUI-VideoHelperSuite 插件     (提供 VHS_VideoCombine 视频合成)
#   3) mm_sdxl_v10_beta.ckpt 动画模块     (models/animatediff)
#   4) ip-adapter-plus_sdxl_vit-h 权重    (models/ipadapter, plus 全身版)
#  然后重启 ComfyUI 注册节点
# ============================================================
set -u
COMFY=/root/ComfyUI
cd "$COMFY" || { echo "COMFY_DIR_MISSING"; exit 1; }

echo "==== [0] 磁盘空间 ======"
df -h / | tail -2
RU=$(df --output=pcent / | tail -1 | tr -dc '0-9')
if [ "${RU:-0}" -gt 92 ]; then
  echo "⚠️ 磁盘紧张(${RU}%)，清理 hfcache + 移除 C1 九宫格权重(MV-Adapter, C2 不用)"
  rm -rf /root/.cache/huggingface 2>/dev/null
  rm -f models/mvadapter/mvadapter_i2mv_sdxl.safetensors 2>/dev/null
  echo "清理后:"; df -h / | tail -1
fi

echo "==== [1] clone AnimateDiff-Evolved ======"
if [ -d custom_nodes/ComfyUI-AnimateDiff-Evolved ]; then
  echo "已存在，git pull 更新"; git -C custom_nodes/ComfyUI-AnimateDiff-Evolved pull --ff-only 2>/dev/null || true
else
  git clone https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved custom_nodes/ComfyUI-AnimateDiff-Evolved
fi

echo "==== [2] clone VideoHelperSuite ======"
if [ -d custom_nodes/ComfyUI-VideoHelperSuite ]; then
  echo "已存在，git pull 更新"; git -C custom_nodes/ComfyUI-VideoHelperSuite pull --ff-only 2>/dev/null || true
else
  git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite custom_nodes/ComfyUI-VideoHelperSuite
fi

echo "==== [3] IPAdapter_plus (已装则跳过) ======"
[ -d custom_nodes/ComfyUI-IPAdapter_plus ] && echo "已装，跳过" || \
  git clone https://github.com/cubiq/ComfyUI-IPAdapter_plus custom_nodes/ComfyUI-IPAdapter_plus

echo "==== [4] 下载 AnimateDiff 模块 mm_sdxl_v10_beta.ckpt ======"
mkdir -p models/animatediff
if [ ! -f models/animatediff/mm_sdxl_v10_beta.ckpt ]; then
  curl -L -C - -o models/animatediff/mm_sdxl_v10_beta.ckpt \
    "https://huggingface.co/guoyouyuli/AnimateDiff-XL/resolve/main/mm_sdxl_v10_beta.ckpt" \
    || curl -L -C - -o models/animatediff/mm_sdxl_v10_beta.ckpt \
    "https://hf-mirror.com/guoyouyuli/AnimateDiff-XL/resolve/main/mm_sdxl_v10_beta.ckpt"
else
  echo "已存在，跳过"
fi

echo "==== [5] 下载 ip-adapter-plus_sdxl_vit-h（全身版） ======"
mkdir -p models/ipadapter
if [ ! -f models/ipadapter/ip-adapter-plus_sdxl_vit-h.safetensors ]; then
  curl -L -C - -o models/ipadapter/ip-adapter-plus_sdxl_vit-h.safetensors \
    "https://huggingface.co/h94/IP-Adapter/resolve/main/sdxl_models/ip-adapter-plus_sdxl_vit-h.safetensors" \
    || curl -L -C - -o models/ipadapter/ip-adapter-plus_sdxl_vit-h.safetensors \
    "https://hf-mirror.com/h94/IP-Adapter/resolve/main/sdxl_models/ip-adapter-plus_sdxl_vit-h.safetensors"
else
  echo "已存在，跳过"
fi

echo "==== [6] 检查 ffmpeg（VHS 视频合成需要） ======"
if which ffmpeg >/dev/null 2>&1; then echo "ffmpeg OK"; else
  echo "⚠️ 无 ffmpeg，尝试安装"; apt-get update -qq >/dev/null 2>&1; apt-get install -y ffmpeg 2>/dev/null \
    || echo "⚠️ 自动安装失败，请手动: apt-get install -y ffmpeg"
fi

echo "==== [7] 重启 ComfyUI（注册新插件节点） ======"
pkill -f "main.py --listen" 2>/dev/null || true
sleep 3
cd "$COMFY"
nohup python main.py --listen --port=6889 > /tmp/comfy.log 2>&1 &
echo "重启命令已发，等待启动..."
sleep 25
echo "==== 启动日志尾部 ====="
tail -n 40 /tmp/comfy.log
echo "==== 节点加载检查 ====="
grep -iE "AnimateDiff|VideoHelper|IPAdapter|IMPORT FAILED" /tmp/comfy.log | tail -20 || true
echo "==== 完成：本地脚本会自动检测到节点就绪并提交 C2 测试片 ===="
