#!/bin/bash
# ============================================================
# Nunchaku(Qwen-Image-Edit-2509) + LTX-2 图/视频一站式安装（云通用版）
# 适用：AutoDL / 腾讯云 GPU / 任意 A10~4090 24G 实例（已踩坑固化）
# 端口：8188（单 ComfyUI，图与视频串行）
#
# 【踩坑固化清单（务必先看）】
#  1) nunchaku 绝不能 `pip install nunchaku`（PyPI 默认是同名统计包 0.16.1，缺 convert_fp16）。
#     必须装 nunchaku-1.2.0+torch2.7 的 wheel（node 1.2.1 需要 convert_fp16，1.0.1/1.1.0 都没有）。
#  2) torch 必须 >=2.6（comfy_kitchen 0.2.30 的 list[int] 在 2.5 不认）。本脚本装 2.7.1+cu126，
#     若 nvidia-smi 显示驱动 CUDA < 12.4，请改 cu124；< 12.1 改 cu121。
#  3) numpy 必须钉 1.26.4（环境默认 2.2.6 与老 tensorflow 2.16 的 numpy1.x ABI 冲突，import 即崩）。
#  4) 黑图疑为 sage attention 在 Qwen-Image-Edit 下产生 NaN，启动加 --disable-sage-attention 规避。
#  5) ComfyUI 官方 lightning 工作流用到 ImageScaleToTotalPixels（在 flash_attn 崩掉的
#     post_processing 模块里）。本机 flash_attn.so 与 torch2.7 ABI 不匹配会拖崩该模块，
#     故请用 D 盘已修好的 fix-v3 工作流：nunchaku-qwen-image-edit-2509-lightning-fix-v3.json
#
# 用法：把本文件 + 工作流 JSON 传到新实例后执行  bash setup_nunchaku_ltx2_cloud.sh
# 可选：BASE=/app/ComfyUI bash setup_nunchaku_ltx2_cloud.sh   （若 ComfyUI 不在 /root/ComfyUI）
# ============================================================
set -e
export HF_ENDPOINT=https://hf-mirror.com   # 国内加速（HF 元数据）

BASE="${BASE:-/root/ComfyUI}"
echo "==> 目标目录: $BASE"

# ---------- 0. 环境探测 ----------
PYVER=$(python3 -c "import sys; print('%d.%d'%sys.version_info[:2])")
echo "==> Python 版本: $PYVER"
# nunchaku 1.2.0 官方 wheel 的 cp 标签；新实例务必选 Python 3.11 镜像（cp311）。
# 若为 3.10，需自行换成 cp310 版 wheel（release 里若有）。
CP="cp3${PYVER#*.}"   # 3.11 -> cp311? 不对，下面显式处理
case "$PYVER" in
  3.11) CP=cp311 ;;
  3.10) CP=cp310 ;;
  3.12) CP=cp312 ;;
  *)    CP=cp311 ; echo "[警告] 未识别的 Python 版本 $PYVER，默认按 cp311 处理" ;;
esac
echo "==> 判定 wheel cp 标签: $CP"

# 驱动 CUDA 版本（决定 torch 的 cu 版本）
CUDA_DRV=$(nvidia-smi 2>/dev/null | grep -oE "CUDA Version: [0-9]+\.[0-9]+" | awk '{print $3}' | cut -d. -f1)
echo "==> 驱动 CUDA 主版本: ${CUDA_DRV:-未知}"
TORCH_CU="cu126"
if [ "${CUDA_DRV:-99}" -lt 12 ]; then TORCH_CU="cu121";
elif [ "${CUDA_DRV:-99}" -lt 13 ] && [ "${CUDA_DRV:-99}" -ge 12 ]; then
  # 12.0~12.4 -> cu126 通常可（cu126 需驱动>=12.4；若 <12.4 用 cu124）
  if [ "${CUDA_DRV}" -lt 4 ] && [ "${CUDA_DRV}" -ge 0 ]; then TORCH_CU="cu124"; fi
fi
echo "==> 选用 torch CUDA 构建: $TORCH_CU"

PIP="python3 -m pip"
MIRROR="-i https://pypi.tuna.tsinghua.edu.cn/simple"

# ---------- 1. 升级 ComfyUI 核心（需 >=0.3.60 支持 Nunchaku/LTX-2） ----------
cd "$BASE"
echo "==> [1] 升级 ComfyUI 核心..."
git pull --ff-only || echo "[1] git pull 失败，若已是 >=0.3.60 可忽略"

# ---------- 2. torch 2.7.1 ----------
echo "==> [2] 安装 torch 2.7.1+$TORCH_CU ..."
$PIP install "torch==2.7.1" "torchvision==0.22.1" --index-url "https://download.pytorch.org/whl/$TORCH_CU" $MIRROR || \
  $PIP install "torch==2.7.1" "torchvision==0.22.1" $MIRROR
# 修复 torchaudio（按 cu 版本重装，避免 libcudart.so.13 之类）
$PIP install "torchaudio==2.7.1" --index-url "https://download.pytorch.org/whl/$TORCH_CU" $MIRROR 2>/dev/null || \
  $PIP install "torchaudio==2.7.1" $MIRROR 2>/dev/null || true

# ---------- 3. ComfyUI 依赖 ----------
echo "==> [3] 安装 ComfyUI 依赖..."
$PIP install -r requirements.txt $MIRROR

# ---------- 4. 克隆节点 ----------
echo "==> [4] 克隆自定义节点..."
CN=custom_nodes
[ -d "$CN/ComfyUI-nunchaku/.git" ] || git clone https://github.com/mit-han-lab/ComfyUI-nunchaku.git "$CN/ComfyUI-nunchaku"
git -C "$CN/ComfyUI-nunchaku" pull --ff-only 2>/dev/null || true
[ -d "$CN/ComfyUI-KJNodes/.git" ] || git clone https://github.com/kijai/ComfyUI-KJNodes.git "$CN/ComfyUI-KJNodes"
[ -d "$CN/ComfyUI-GGUF/.git" ]  || git clone https://github.com/city96/ComfyUI-GGUF.git "$CN/ComfyUI-GGUF"
$PIP install -r "$CN/ComfyUI-nunchaku/requirements.txt" $MIRROR 2>/dev/null || true
$PIP install -r "$CN/ComfyUI-KJNodes/requirements.txt" $MIRROR 2>/dev/null || true

# ---------- 5. 安装 nunchaku 1.2.0 正确 wheel（核心！） ----------
echo "==> [5] 安装 nunchaku-1.2.0+torch2.7 ($CP) 正确 wheel..."
WHEEL="nunchaku-1.2.0+torch2.7-${CP}-${CP}-linux_x86_64.whl"
WHEEL_DIR="/root/whl"; mkdir -p "$WHEEL_DIR"; cd "$WHEEL_DIR"
if [ ! -s "$WHEEL" ]; then
  # 先试 ModelScope（快，但 1.2.0 大概率没有）-> 失败则 aria2 直连 GitHub（多线程突破限速）
  curl -fL --retry 2 -o "$WHEEL" "https://modelscope.cn/models/nunchaku-tech/nunchaku/resolve/master/$WHEEL" 2>/dev/null || true
  if [ ! -s "$WHEEL" ]; then
    command -v aria2c >/dev/null 2>&1 || (apt-get install -y aria2 2>/dev/null || yum install -y aria2 2>/dev/null || true)
    URL="https://github.com/nunchaku-ai/nunchaku/releases/download/v1.2.0/$WHEEL"
    if command -v aria2c >/dev/null 2>&1; then
      aria2c -x 16 -s 16 -o "$WHEEL" "$URL"
    else
      curl -L --retry 5 -C - -o "$WHEEL" "$URL"
    fi
  fi
fi
ls -l --block-size=M "$WHEEL"
# --no-deps 保护已钉的 numpy
$PIP install --no-deps --force-reinstall "$WHEEL_DIR/$WHEEL"
python3 -c "import importlib.metadata as m; from nunchaku.models.transformers.utils import convert_fp16, patch_scale_key; print('nunchaku', m.version('nunchaku'), 'convert_fp16 OK')"

# ---------- 6. 钉 numpy（兼容老 tensorflow 2.16） ----------
echo "==> [6] 钉 numpy==1.26.4 ..."
$PIP install --no-deps "numpy==1.26.4" $MIRROR

# ---------- 7. 模型下载（ModelScope 国内源） ----------
echo "==> [7] 下载模型（国内源，断点续传安全）..."
cd "$BASE"
dl_ms() {
  local repo="$1" file="$2" dir="$3" want="${4:-$(basename "$file")}"
  mkdir -p "$dir"; local dst="$dir/$want" part="$dst.part"
  [ -s "$dst" ] && { echo "[跳过] 已存在: $dst"; return; }
  local url="https://modelscope.cn/models/$repo/resolve/master/$file"
  for try in 1 2 3; do
    if curl -L --retry 2 -C - -fsS -o "$part" "$url" 2>/dev/null && [ -s "$part" ]; then mv -f "$part" "$dst"; echo "[OK] $dst"; return; fi
    sleep 2
  done
  echo "[警告] 下载失败: $url（可手动补下，不阻断后续）"
}
mkdir -p models/diffusion_models models/text_encoders models/vae models/workflows models/unet models/upscale_models
# 图：DiT 主模型 / 文本编码器 / VAE
dl_ms nunchaku-tech/nunchaku-qwen-image-edit-2509 svdq-int4_r128-qwen-image-edit-2509-lightningv2.0-4steps.safetensors models/diffusion_models
dl_ms Comfy-Org/Qwen-Image_ComfyUI split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors models/text_encoders
dl_ms Comfy-Org/Qwen-Image_ComfyUI split_files/vae/qwen_image_vae.safetensors models/vae
# 视频 LTX-2
dl_ms chatpig/ltx2-gguf ltx2-19b-dev-iq4_xs.gguf models/unet "LTX-2-dev-Q4_K_M.gguf"
dl_ms unsloth/gemma-3-12b-it-GGUF gemma-3-12b-it-Q4_K_M.gguf models/text_encoders "gemma-3-12b-it-Q4_K_M.gguf"
dl_ms chatpig/ltx2-gguf ltx2-19b-embeddings_connector_dev_fp8_e4m3fn.safetensors models/text_encoders "ltx-2-19b-embeddings_connector_dev_bf16.safetensors"
dl_ms chatpig/ltx2-gguf ltx2_video_vae_fp8_e4m3fn.safetensors models/vae "LTX2_video_vae_bf16.safetensors"
dl_ms chatpig/ltx2-gguf ltx2_audio_checkpoint_vae_bf16.safetensors models/vae "LTX2_audio_vae_bf16.safetensors"
dl_ms Lightricks/LTX-2 ltx-2-spatial-upscaler-x2-1.0.safetensors models/upscale_models "ltx-2-spatial-upscaler-x2-1.0.safetensors"

# ---------- 8. 工作流 ----------
echo "==> [8] 复制官方 lightning 工作流..."
[ -f models/workflows/nunchaku-qwen-image-edit-2509-lightning.json ] || \
  cp "$CN/ComfyUI-nunchaku/example_workflows/nunchaku-qwen-image-edit-2509-lightning.json" models/workflows/ 2>/dev/null || true
echo "    （黑图规避版在本地 D 盘：nunchaku-qwen-image-edit-2509-lightning-fix-v3.json，请一并传到新实例 Load）"

# ---------- 9. 启动（禁用 sage attention 规避黑图） ----------
echo ""
echo "==> 安装完成。启动命令（已加 --disable-sage-attention）："
echo "    cd $BASE && nohup python3 main.py --port 8188 --listen 0.0.0.0 --disable-sage-attention > /root/comfy_start.log 2>&1 &"
echo "==> 访问：AutoDL 在控制台『快捷工具/外网访问』获取代理 URL；腾讯云用 公网IP:8188（需开安全组）。"
echo "==> 验证出图：Load nunchaku-qwen-image-edit-2509-lightning-fix-v3.json，传 3 张图 + 改 prompt -> Queue Prompt。"
echo "==> 若仍黑图：抓日志 grep nan / invalid value，转 fp32 注意力或排查 VAE。"
