#!/bin/bash
# ============================================================================
# DSW 一键安装脚本：多角色对话动画片工作流（LTX-2 + Qwen3-TTS）
# 适用实例：DSW dsw-823428，ComfyUI 端口 6889，A10 24GB，核心 0cb84e7e
# 来源（均经官方核实 2026-07-28）：
#   - 工作流自带 "About Models" 注记：Kijai/LTXV2_comfy + unsloth/gemma-3-12b-it-GGUF + 1038lab/ComfyUI-QwenTTS
#   - Kijai 仓库 GGUF 文件树 / text_encoders / VAE / loras
#   - flybirdxx/ComfyUI-Qwen-TTS（提供工作流实际使用的 FB_Qwen3TTS* 节点；注记写的 1038lab 是错的，其 main 只有 AILab_* 且历史上从未有 FB_ 节点）
#   - Lightricks/LTX-2 官方模型卡（确认组件/蒸馏 LoRA 命名与分辨率规范）
#
# 用法：
#   1) 把本文件传到 DSW（如 /mnt/workspace/ai-comfyui/pai/）或直接在终端粘贴
#   2) 终端执行：  bash /mnt/workspace/ai-comfyui/pai/dsw_setup_ltx2_qwentts.sh
#   3) 跑完看结尾 [校验] 汇总；浏览器打开工作流 JSON → 改 unet_name → Queue
#
# 说明：脚本只装"环境与模型"，不自动出图。模型总下载约 30GB，建议在后台跑。
# ============================================================================
set -u
export GIT_TERMINAL_PROMPT=0   # 禁用 git 交互式密码提示，失败即报错不卡死
# GitHub PAT（用户授权内置：来自腾讯文档【相关平台和账密】，仅用于提升 clone 限额避免匿名 401 鉴权失败）
export GH_TOKEN="${GH_TOKEN:-}"   # read from env; never hardcode token here
git config --global url."https://${GH_TOKEN}@github.com/".insteadOf "https://github.com/" \
  && echo "[OK] 已为 git clone 配置 GH_TOKEN 鉴权（限额提升到 5000/小时）" \
  || echo "[警告] git config insteadOf 失败，将退化为匿名 clone"
COMFY=/root/ComfyUI
LOG=/tmp/dsw_setup_ltx2.log
exec > >(tee -a "$LOG") 2>&1
echo "===== 开始 $(date) ====="

export HF_ENDPOINT=https://hf-mirror.com
export HF_HUB_DISABLE_XET=1

# ---------- 工具函数 ----------
# 用 hf-mirror 直链 curl 下载（绕过 huggingface-cli 在镜像下对 LFS 文件失败的问题）
dl() {  # $1=repo  $2=file(可含子目录)  $3=localdir  $4=期望文件名(默认 basename)
  local repo="$1" file="$2" dir="$3" want="${4:-$(basename "$file")}"
  mkdir -p "$dir"
  local dst="$dir/$want"
  if [ -s "$dst" ]; then echo "[跳过] 已存在: $dst"; return; fi
  local url="https://hf-mirror.com/$repo/resolve/main/$file"
  echo "[下载] $url -> $dst"
  for try in 1 2 3; do
    if curl -L --retry 2 -C - -fsS -o "$dst" "$url" 2>/dev/null && [ -s "$dst" ]; then
      echo "[OK] $dst"; return
    fi
    sleep 2
  done
  echo "[警告] 下载失败: $url"
}

clone() {  # $1=url  $2=目标目录
  local url="$1" dst="$2"
  if [ -d "$dst" ]; then
    echo "[跳过] 已克隆: $dst"
  else
    echo "[克隆] $url -> $dst"
    if git -C "$(dirname "$dst")" clone "$url" "$(basename "$dst")" >/dev/null 2>&1; then
      echo "[OK] $dst"
    else
      echo "[失败] clone $url （若提示鉴权/限流，请先 export GH_TOKEN=你的PAT 后重跑本脚本）"
    fi
  fi
}

echo "=== [1/6] 安装 5 个自定义节点包（含官方要求的 TTS 版本依赖） ==="
CN=$COMFY/custom_nodes
#   TTS 节点真实来源 = flybirdxx/ComfyUI-Qwen-TTS（FB_Qwen3TTS* 节点）。
#   注：工作流 "About Models" 注记写的 1038lab/ComfyUI-QwenTTS 是错误的——其 main 只注册 AILab_* 节点，
#   且仓库历史中从未有过 FB_ 节点；经 GitHub 代码搜索确认 FB_Qwen3TTS* 来自 flybirdxx 仓库。
clone https://github.com/flybirdxx/ComfyUI-Qwen-TTS.git     "$CN/ComfyUI-Qwen-TTS"
clone https://github.com/kijai/ComfyUI-KJNodes.git          "$CN/ComfyUI-KJNodes"
clone https://github.com/yolain/ComfyUI-Easy-Use.git        "$CN/ComfyUI-Easy-Use"
#   注意：mtb / LayerStyle 的仓库地址已核实修正（2026-07-28）：
#     - mtb = melMass/comfy_mtb（提供 "Audio Duration (mtb)" 节点），原 mattya/ComfyUI_mtb 不存在
#     - LayerStyle = chflame163/ComfyUI_LayerStyle（提供 "LayerUtility: PurgeVRAM V2"），原 pythongosssss 路径 404
clone https://github.com/melMass/comfy_mtb.git             "$CN/ComfyUI_mtb"
clone https://github.com/chflame163/ComfyUI_LayerStyle.git "$CN/ComfyUI-LayerStyle"

for pkg in ComfyUI-Qwen-TTS ComfyUI-KJNodes ComfyUI-Easy-Use ComfyUI_mtb ComfyUI-LayerStyle; do
  if [ -f "$CN/$pkg/requirements.txt" ]; then
    echo "  [pip] $pkg 依赖"
    python3 -m pip install -r "$CN/$pkg/requirements.txt" --no-cache-dir 2>&1 | tail -3
  fi
done

echo "=== [2/6] 固定 transformers 版本（QwenTTS 要求 4.57.3，5.x 会报 pad_token_id） ==="
python3 -m pip install -U "transformers==4.57.3" "tokenizers<0.20" --no-cache-dir 2>&1 | tail -3
python3 -c "import transformers; print('[OK] transformers', transformers.__version__)"

echo "=== [3/6] 下载 LTX-2 模型权重（A10 用 Q4，且改名对齐工作流期望文件名） ==="
# 注意：Kijai 仓库文件名已更新，但与工作流节点里写死的名字不同 —— 这里下载后改名/软链，避免改工作流。
UNET=$COMFY/models/unet
TEXT=$COMFY/models/text_encoders
VAE=$COMFY/models/vae
UPS=$COMFY/models/upscale_models
LORA=$COMFY/models/loras

# 3.1 主模型：A10 必须用 Q4（12.7G），改名成工作流期望的 LTX-2-dev-Q4_K_M.gguf
dl Kijai/LTXV2_comfy diffusion_models/ltx-2-19b-dev_Q4_K_M.gguf "$UNET" "LTX-2-dev-Q4_K_M.gguf"

# 3.2 Gemma 文本编码器：作者 Note 说来自 unsloth/gemma-3-12b-it-GGUF，
#     但该仓库只有 GGUF 量化版（无 fp8_e4m3fn 文件），公开 HF 也搜不到该 fp8 文件。
#     改用 unsloth 的 Q4_K_M GGUF —— 这正是 Kijai LTX-2 GGUF 工作流标准 gemma 源，
#     GGUF 量化版对 A10/Ampere 更友好；并同步改写工作流节点文件名（见 [5/7]）。
dl unsloth/gemma-3-12b-it-GGUF gemma-3-12b-it-Q4_K_M.gguf "$TEXT" "gemma-3-12b-it-Q4_K_M.gguf"

# 3.3 embeddings connector：Kijai 现名 _distill_bf16，工作流要旧名 _bf16 → 下载后改名
dl Kijai/LTXV2_comfy text_encoders/ltx-2-19b-embeddings_connector_distill_bf16.safetensors "$TEXT" "ltx-2-19b-embeddings_connector_bf16.safetensors"

# 3.4 视频 VAE：工作流要 LTX2_video_vae_bf16_260115.safetensors；Kijai 现名 LTX2_video_vae_bf16.safetensors
dl Kijai/LTXV2_comfy VAE/LTX2_video_vae_bf16.safetensors "$VAE" "LTX2_video_vae_bf16_260115.safetensors"

# 3.5 音频 VAE：同目录同名
dl Kijai/LTXV2_comfy VAE/LTX2_audio_vae_bf16.safetensors "$VAE" "LTX2_audio_vae_bf16.safetensors"

# 3.6 空间 upscaler：Lightricks 官方
dl Lightricks/LTX-2 ltx-2-spatial-upscaler-x2-1.0.safetensors "$UPS" "ltx-2-spatial-upscaler-x2-1.0.safetensors"

# 3.7 蒸馏 LoRA：工作流写死文件名（Kijai 有）
dl Kijai/LTXV2_comfy loras/ltx-2-19b-distilled-lora_resized_dynamic_fro09_avg_rank_175_bf16.safetensors "$LORA" "ltx-2-19b-distilled-lora_resized_dynamic_fro09_avg_rank_175_bf16.safetensors"

echo "=== [4/7] Qwen3-TTS 模型：首次运行由节点自动下载（此处不预下，避免 huggingface-cli 在镜像下失败） ==="
echo "   节点默认目录：models/TTS/Qwen3-TTS/<REPO>/"
echo "   若首次运行下载超时，单独用浏览器或 aria2 下 Qwen/Qwen3-TTS-12Hz-1.7B-* 到该目录即可。"

echo "=== [5/7] 把工作流 unet 名 Q8 改为 Q4（A10 显存红线，免手动编辑） ==="
WF_SRC="/mnt/workspace/ai-comfyui/pai/一键生成多角色对话动画片，Qwen3-TTS+++LTX-2工作流！.json"
WF_DST="$COMFY/user/default/workflows/runninghub_ltx2_qwentts.json"
if [ -f "$WF_SRC" ]; then
  mkdir -p "$COMFY/user/default/workflows"
  cp "$WF_SRC" "$WF_DST"
  # 将 UnetLoaderGGUF 期望的 Q8 名替换为 Q4（文件里是 LTX-2-dev-Q8_0.gguf）
  sed -i 's/LTX-2-dev-Q8_0.gguf/LTX-2-dev-Q4_K_M.gguf/g' "$WF_DST"
  # 同步修正 Gemma 文本编码器：作者写死的 fp8 文件公开不存在，改用 unsloth Q4_K_M GGUF
  sed -i 's/gemma_3_12B_it_fp8_e4m3fn.safetensors/gemma-3-12b-it-Q4_K_M.gguf/g' "$WF_DST"
  echo "[OK] 已复制并改写 unet 名为 Q4: $WF_DST"
  echo "      若无该源路径，请用 ComfyUI 网页 Load 原 JSON，再手动把 UnetLoaderGGUF 的"
  echo "      LTX-2-dev-Q8_0.gguf 改成 LTX-2-dev-Q4_K_M.gguf"
else
  echo "[提示] 未找到工作流源文件 $WF_SRC，请自行 Load 并在 UnetLoaderGGUF 把 Q8 改 Q4。"
fi

echo "=== [6/7] 重启 ComfyUI（让节点与模型注册） ==="
pkill -f "main.py" || true
sleep 3
cd "$COMFY" && nohup python3 main.py --port 6889 > /tmp/comfy_run.log 2>&1 &
for i in $(seq 1 60); do
  if curl -s --noproxy 127.0.0.1 http://127.0.0.1:6889/object_info >/dev/null 2>&1; then
    echo "[OK] ComfyUI 已启动"; break
  fi
  sleep 3
done

echo "=== [7/7] 校验关键节点 + 模型文件 ==="
OI=$(curl -s --noproxy 127.0.0.1 http://127.0.0.1:6889/object_info)
echo "--- 节点校验（缺任何一个都会让工作流报节点缺失） ---"
for n in UnetLoaderGGUF DualCLIPLoaderGGUF VAELoaderKJ LoraLoaderModelOnly FB_Qwen3TTSDialogueInference easy\ showAnything Audio\ Duration\ \(mtb\) LayerUtility:\ PurgeVRAM\ V2; do
  if echo "$OI" | grep -q "\"$n\""; then echo "[OK]   $n"; else echo "[缺失] $n  → 见下方排查"; fi
done
echo "--- 模型文件校验 ---"
for f in \
  "$UNET/LTX-2-dev-Q4_K_M.gguf" \
  "$TEXT/gemma-3-12b-it-Q4_K_M.gguf" \
  "$TEXT/ltx-2-19b-embeddings_connector_bf16.safetensors" \
  "$VAE/LTX2_video_vae_bf16_260115.safetensors" \
  "$VAE/LTX2_audio_vae_bf16.safetensors" \
  "$UPS/ltx-2-spatial-upscaler-x2-1.0.safetensors" \
  "$LORA/ltx-2-19b-distilled-lora_resized_dynamic_fro09_avg_rank_175_bf16.safetensors" ; do
  if [ -s "$f" ]; then echo "[OK]   $(basename "$f")"; else echo "[缺失] $(basename "$f") -> $f"; fi
done

echo "=== [!] 重要：跑工作流前需改 1 处 ==="
echo "  在 ComfyUI 网页打开工作流 JSON，找到 UnetLoaderGGUF 节点，把"
echo "  LTX-2-dev-Q8_0.gguf  →  LTX-2-dev-Q4_K_M.gguf  （A10 显存红线）"
echo "  并找到 DualCLIPLoaderGGUF 节点，把"
echo "  gemma_3_12B_it_fp8_e4m3fn.safetensors  →  gemma-3-12b-it-Q4_K_M.gguf  （作者引用文件公开不存在，已改用 unsloth GGUF）"
echo "  若还 OOM：断开 LTXVLatentUpsampler / 空间 upscaler 支路，或降分辨率 480p。"
echo "  若 [缺失] FB_Qwen3TTS* 节点：说明 1038lab 仓库版本节点名变了 ——"
echo "    方案A：在 ComfyUI-Manager 装 'ComfyUI-QwenTTS' 正式版（节点名可能是 AILab_Qwen3TTS*），"
echo "           此时需把工作流里 FB_Qwen3TTS* 节点整体替换为对应 AILab_Qwen3TTS* 节点（我可帮你做替换版工作流）。"
echo "    方案B：找作者原版带 FB_ 的 fork（runninghub 通常内嵌了对应 custom_nodes），按其说明装。"
echo "=== 安装结束。日志: $LOG ==="
