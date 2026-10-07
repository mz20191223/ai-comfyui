#!/bin/bash
# DSW 一键安装 Qwen-Image-Edit 环境（只装环境，不自动出图）
# 用法：把本文件传到 DSW（如 /mnt/workspace/ai-comfyui/pai/），终端执行：
#   bash /mnt/workspace/ai-comfyui/pai/dsw_setup_qwen.sh
# 跑完后在 ComfyUI 网页 Load 工作流 JSON（mushroom_from_peach_ui.json），
# 在 LoadImage 节点上传 peach_role_v6.png，点 Queue Prompt。
set -u
COMFY=/root/ComfyUI
PAI=/mnt/workspace/ai-comfyui/pai
LOG=/tmp/dsw_setup_qwen.log
exec > >(tee -a "$LOG") 2>&1
echo "===== 开始 $(date) ====="

echo "=== [1/5] 安装 ComfyUI-GGUF 节点 ==="
if [ ! -d "$COMFY/custom_nodes/ComfyUI-GGUF" ]; then
  git -C "$COMFY/custom_nodes" clone https://github.com/city96/ComfyUI-GGUF.git
fi
pip install -q -r "$COMFY/custom_nodes/ComfyUI-GGUF/requirements.txt" 2>&1 | tail -3
echo "[OK] ComfyUI-GGUF 就绪"

echo "=== [2/5] 升级 ComfyUI 核心（原生支持 QwenImageSampler） ==="
cd "$COMFY"
git stash 2>/dev/null || true
git pull 2>&1 | tail -5
pip install -q -r requirements.txt 2>&1 | tail -3
echo "[OK] ComfyUI 已更新: $(git log --oneline -1)"

echo "=== [3/5] 下载 Qwen 权重 (hf-mirror) ==="
export HF_ENDPOINT=https://hf-mirror.com
export HF_HUB_DISABLE_XET=1
DL() {
  local f="$3/$2"
  [ -f "$f" ] && { echo "[跳过] 已存在: $f"; return; }
  mkdir -p "$3"
  for try in 1 2 3; do
    echo "[下载#$try] $1/$2 -> $3"
    huggingface-cli download "$1" "$2" --local-dir "$3" --local-dir-use-symlinks False && return
    sleep 2
  done
  echo "[警告] $2 下载失败"
}
DL city96/qwen-image-edit-gguf qwen-image-edit-2511-Q4_K_M.gguf "$COMFY/models/unet"
DL city96/Qwen2.5-VL-7B-Instruct-GGUF Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf "$COMFY/models/text_encoders"
if [ ! -f "$COMFY/models/vae/qwen_image_vae.safetensors" ]; then
  mkdir -p "$COMFY/models/vae"
  curl -L -C - -o "$COMFY/models/vae/qwen_image_vae.safetensors" \
    https://hf-mirror.com/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/vae/qwen_image_vae.safetensors
fi
echo "[OK] 权重清单:"
ls -lh "$COMFY/models/unet/"*.gguf "$COMFY/models/text_encoders/"*.gguf "$COMFY/models/vae/"*.safetensors 2>/dev/null

echo "=== [4/5] 重启 ComfyUI (6889) ==="
pkill -f "main.py" || true
sleep 3
cd "$COMFY" && nohup python3 main.py --port 6889 > /tmp/comfy_run.log 2>&1 &
for i in $(seq 1 60); do
  if curl -s --noproxy 127.0.0.1 http://127.0.0.1:6889/object_info >/dev/null 2>&1; then
    echo "[OK] ComfyUI 已启动"; break
  fi
  sleep 3
done

echo "=== [5/5] 验证 Qwen 节点 ==="
OI=$(curl -s --noproxy 127.0.0.1 http://127.0.0.1:6889/object_info)
for n in UnetLoaderGGUF CLIPLoaderGGUF QwenImageSampler QwenImageEmptyLatentImage; do
  if echo "$OI" | grep -q "\"$n\""; then echo "[OK] $n"; else echo "[缺失] $n -> 请检查日志 $LOG"; fi
done
echo "=== [+] 放置可视化工作流（需你已把 mushroom_from_peach_ui.json 传到 $PAI/workflows/） ==="
if [ -f "$PAI/workflows/mushroom_from_peach_ui.json" ]; then
  mkdir -p "$COMFY/user/default/workflows"
  cp "$PAI/workflows/mushroom_from_peach_ui.json" "$COMFY/user/default/workflows/"
  echo "[OK] 工作流已复制到 ComfyUI 用户目录，可在网页菜单/侧边栏直接打开"
else
  echo "[提示] 未找到 $PAI/workflows/mushroom_from_peach_ui.json —— 请在 ComfyUI 网页用 Load 手动导入该文件"
fi
echo "=== 环境就绪。下一步：ComfyUI 网页打开工作流，LoadImage 上传 peach_role_v6.png，Queue Prompt ==="
echo "日志: $LOG"
