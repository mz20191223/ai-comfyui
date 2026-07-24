#!/bin/bash
# ============================================================
# 阿里云 PAI-DSW (A10 24G 免费额度) 一键部署 Qwen-Image-Edit + ComfyUI
# 用途：把 HAI 上验证过的「Qwen 出桃子参考图」流程原样搬到 DSW，
#       利用 A10 的 24G 显存整张装下模型、不 CPU 卸载，比 T4 快 5~10 倍。
#
# 用法（把本 pai 文件夹整体上传到 DSW 实例后，在 Terminal 里）：
#   cd <你上传的目录>/pai
#   bash setup_pai.sh
#
# 全程约 20~40 分钟（主要是下载 ~17G 权重）。跑完会后台启动 ComfyUI。
# ⚠️ 跑此脚本期间实例在运行、消耗免费计算时；跑完记得手动停止实例。
# ============================================================
set -e

echo "==> [1/6] 检查 Python 环境（需 >= 3.10）"
python -V
PYV=$(python -c "import sys; print('%d.%d'%sys.version_info[:2])")
if [ "$(printf '%s\n' '3.10' "$PYV" | sort -V | head -1)" != "3.10" ]; then
  echo "⚠️  Python 需 >= 3.10，当前 $PYV。"
  echo "    请用 DSW 预置的 conda(torch) 环境，例如先执行: conda activate <torch_env>"
  exit 1
fi

echo "==> [2/6] 克隆 ComfyUI（最新版，原生支持 Qwen-Image）"
cd ~
if [ ! -d ComfyUI ]; then
  git clone https://github.com/Comfy-Org/ComfyUI.git
fi
cd ComfyUI

echo "==> [3/6] 安装 ComfyUI 依赖（含 sqlalchemy 等新版必需的包）"
pip install -r requirements.txt
# 校验 torch 仍是 CUDA 版（被改坏则重装 cu124）
if ! python -c "import torch; assert torch.cuda.is_available()" 2>/dev/null; then
  echo "    ⚠️ torch CUDA 不可用，重装 CUDA 版..."
  pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124 \
    -i https://mirrors.aliyun.com/pypi/simple
fi

echo "==> [4/6] 安装 ComfyUI-GGUF 节点（UnetLoaderGGUF / CLIPLoaderGGUF 来源）"
cd custom_nodes
if [ ! -d ComfyUI-GGUF ]; then
  git clone https://github.com/city96/ComfyUI-GGUF.git
fi
cd ComfyUI-GGUF
pip install -r requirements.txt
cd ../..

echo "==> [5/6] 下载 Qwen-Image-Edit 权重（hf-mirror 国内镜像，断点续传）"
HF="https://hf-mirror.com"
cd models
mkdir -p unet clip text_encoders vae input
# Unet 12.34G（与 HAI 同文件）
curl -L -C - -o unet/qwen-image-edit-2511-Q4_K_M.gguf \
  "$HF/unsloth/Qwen-Image-Edit-2511-GGUF/resolve/main/qwen-image-edit-2511-Q4_K_M.gguf"
# Text Encoder (Qwen2.5-VL) 4.68G —— 放 text_encoders，并 cp 一份到 clip 兼容新旧目录
curl -L -C - -o text_encoders/Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf \
  "$HF/rexionmars/Qwen2.5-VL-7B-Instruct-Q4_K_M-GGUF/resolve/main/Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf"
cp text_encoders/Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf clip/ 2>/dev/null || true
# VAE 0.3G
curl -L -C - -o vae/qwen_image_vae.safetensors \
  "$HF/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/vae/qwen_image_vae.safetensors"
cd ..

echo "==> [6/6] 放置 anchor 图 + 后台启动 ComfyUI"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/peach_role_v6.png" ]; then
  cp "$SCRIPT_DIR/peach_role_v6.png" input/peach_role_v6.png
  echo "    已放置 anchor -> input/peach_role_v6.png"
else
  echo "    ⚠️ 未找到 peach_role_v6.png，请手动上传到 $(pwd)/input/peach_role_v6.png"
fi

# 后台启动 ComfyUI（监听 6889；日志 /tmp/comfy.log）
nohup python main.py --listen 0.0.0.0 --port 6889 > /tmp/comfy.log 2>&1 &
echo "    ComfyUI 后台启动 (PID $!)，日志: /tmp/comfy.log"
echo "    等 ~60s 后验证:  curl http://127.0.0.1:6889/system_stats"
echo ""
echo "DONE. 下一步（仍在 Terminal）:"
echo "  cd <pai目录> && python gen_refs_pai.py test     # 先验证链路"
echo "  python gen_refs_pai.py full                     # 出 4 张参考图 -> ./out/"
