#!/bin/bash
# ============================================================
# DSW 上安装 Qwen-Image-Edit (GGUF) + 确保 ComfyUI 原生支持
# 用法: 在 DSW 网页终端执行  bash setup_qwen_dsw.sh
# 前置: DSW 实例已启动, ComfyUI 在 /root/ComfyUI
# ============================================================
set -e
COMFY=/root/ComfyUI
cd "$COMFY"

echo "=== [0] 当前 ComfyUI 状态 ==="
git log --oneline -1 2>/dev/null || echo "(git 异常)"
git status --short 2>/dev/null | head

echo "=== [1] 下载 Qwen-Image-Edit GGUF (约 12.34GB, hf-mirror, 禁 xet) ==="
UNET=$COMFY/models/unet
mkdir -p "$UNET"
cd "$UNET"
GGUF=qwen-image-edit-2511-Q4_K_M.gguf
if [ -f "$GGUF" ]; then
  echo "[跳过] 已存在: $(du -h "$GGUF" | cut -f1)"
else
  echo "[下载] city96/qwen-image-edit-gguf :: $GGUF ..."
  HF_ENDPOINT=https://hf-mirror.com HF_HUB_DISABLE_XET=1 \
    python3 -m huggingface_hub.commands.download city96/qwen-image-edit-gguf "$GGUF" \
    --local-dir . --local-dir-use-symlinks False
  echo "[OK] 下载完成: $(du -h "$GGUF" | cut -f1)"
fi

echo "=== [2] 升级 ComfyUI 到原生支持 Qwen 的版本(参考 HAI: 0cb84e7e) ==="
cd "$COMFY"
git stash 2>/dev/null || true
git checkout master 2>/dev/null || true
git pull 2>/dev/null || true
git stash pop 2>/dev/null || true

echo "=== [3] 安装 Qwen 所需依赖(保守: 仅 transformers, 不动 MV-Adapter 的 diffusers) ==="
pip install -q "transformers>=4.49" 2>&1 | tail -3 || echo "[warn] transformers 升级失败, 启动报错再处理"

echo "=== [4] 重启 ComfyUI (端口 6889) ==="
pkill -f "main.py" || true
sleep 3
cd "$COMFY" && nohup python3 main.py --port 6889 > /tmp/comfy_run.log 2>&1 &

echo "=== [5] 等待启动并验证节点 ==="
for i in $(seq 1 40); do
  if curl -s localhost:6889/object_info >/dev/null 2>&1; then echo "[OK] ComfyUI 已启动"; break; fi
  sleep 3
done
echo "--- Qwen 相关节点 ---"
curl -s localhost:6889/object_info | tr ',' '\n' | grep -i qwen | head
echo "--- MV-Adapter 节点是否仍在(确认未破坏) ---"
curl -s localhost:6889/object_info | tr ',' '\n' | grep -i DiffusersMVPipelineLoader | head
echo "=== 完成。若启动异常看日志: tail -f /tmp/comfy_run.log ==="
