#!/usr/bin/env bash
# ============================================================
# DSW 一键安装：文生图端到端（LLM扩写 → Flux.1 dev 出图）
# 目标：16G 显存（A10 等）。LLM 扩写与出图【分时】运行。
# 流程：用户输入短词 → Qwen2.5-14B 扩写成英文提示词 → 释放LLM显存 → Flux.1 dev Q4 出图
# 铁律：所有文件名/节点名均经官方核实（2026-07-29）
# ============================================================
set -u
export GIT_TERMINAL_PROMPT=0   # 禁用 git 交互式密码提示，失败即报错不卡死
# GitHub PAT（用户授权硬编码，仅用于提升 clone 限额）
export GH_TOKEN="${GH_TOKEN:-}"   # read from env; never hardcode token here
git config --global url."https://${GH_TOKEN}@github.com/".insteadOf "https://github.com/" 2>/dev/null \
  && echo "[OK] 已为 git clone 配置 GH_TOKEN 鉴权" || echo "[警告] git config insteadOf 失败"

COMFY=/root/ComfyUI
CN=$COMFY/custom_nodes
LLM=$COMFY/models/LLM
UNET=$COMFY/models/unet
CLIP=$COMFY/models/clip
VAE=$COMFY/models/vae
LOG=/tmp/dsw_setup_t2i.log
: > "$LOG"
exec > >(tee -a "$LOG") 2>&1
echo "===== 开始 $(date '+%F %T') ====="

clone() {  # $1=url  $2=目标目录
  local url="$1" dst="$2"
  if [ -d "$dst" ]; then echo "[跳过] 已克隆: $dst"; return; fi
  git -C "$(dirname "$dst")" clone "$url" "$(basename "$dst")" 2>&1 | tail -2 \
    && echo "[OK] $dst" || echo "[警告] 克隆失败: $url"
}

# ---------- [1/6] 安装自定义节点包 ----------
echo "=== [1/6] 安装自定义节点包 ==="
clone https://github.com/scruffynerf/comfyui-sg-llama-cpp.git "$CN/comfyui-sg-llama-cpp"   # 本地LLM(GGUF)推理+内存清理
clone https://github.com/city96/ComfyUI-GGUF.git             "$CN/ComfyUI-GGUF"             # UnetLoaderGGUF 加载 Flux GGUF

echo "--- 安装依赖 ---"
# llama-cpp-python：装 PyPI 的 CPU 版（直连快，绕过 GitHub 慢下载；LLM 退回 CPU 推理，Flux 出图不受影响，16G 下更省显存）
pip install --upgrade pip >/dev/null 2>&1
echo "[安装] llama-cpp-python (PyPI CPU 版，直连快)"
pip install --force-reinstall --no-cache-dir llama-cpp-python 2>&1 | tail -5 \
  && echo "[OK] llama-cpp-python(CPU 版)" \
  || echo "[警告] llama-cpp-python 安装失败，把日志发我"

# ---------- [2/6] 下载模型 ----------
echo "=== [2/6] 下载模型（优先 modelscope 并行分片加速；hf-mirror 兜底；写死确切文件名） ==="
# 铁律背景(2026-07-29核实)：
#  - huggingface.co 在本 DSW(国内区域)被墙，连接即失败
#  - 下载改用「并行分片」(dl_parallel)：大文件切 8 片并发下载再合并，突破 modelscope/hf-mirror 单连接限速(实测单连接仅~1.3MB/s，并行可达数倍)
#  - modelscope 是阿里自家镜像，DSW(阿里云PAI)同骨干飞快；已探活 Qwen3分片/Flux Q4_K_S/ae 可达(200)
#  - 文本编码器正确仓库=comfyanonymous/flux_text_encoders（modelscope 镜像 AI-ModelScope/flux_text_encoders 已验证200）；
#    用 fp8 版 t5xxl(~4.9G) 适配 16G（fp16 实为~9.8G，叠加 Flux 必 OOM）；Flux 需 DualCLIPLoader 同时加载 t5xxl+clip_l。
#  - city96/FLUX.1-dev-gguf 无 Q4_K_M(仅 Q4_0/Q4_1/Q4_K_S)，已改 Q4_K_S
ensure_aria2() {
  if command -v aria2c >/dev/null 2>&1; then echo "[OK] aria2c 已就绪"; return 0; fi
  echo "[安装] aria2c (多线程下载，破解 hf-mirror 单连接限速)"
  apt-get update -qq >/dev/null 2>&1
  if apt-get install -y aria2 >/dev/null 2>&1 && command -v aria2c >/dev/null 2>&1; then
    echo "[OK] aria2c 安装成功"; return 0
  fi
  echo "[警告] aria2c 安装失败，将退回 curl 单线程(会慢，建议手动 apt-get install aria2)"
  return 1
}
# 并行分片下载：大文件切 N 片并发下载再合并，突破单连接限速（实测 modelscope/hf-mirror 单连接仅~1.3MB/s）
# $1=url $2=out $3=线程数(默认8) $4=分片阈值字节(默认300M，小于此走单连接续传)
dl_parallel() {
  local url="$1" out="$2" nthr="${3:-4}" minsz="${4:-314572800}"
  # 取总大小：HEAD 的 content-length 优先；拿不到则试 Range GET 的 content-range
  #   （modelscope 的 OSS 对 HEAD 不返回 content-length，只在 GET/Range 时返回，必须兜底）
  local total=""
  total=$(curl -sIL -L --max-time 30 "$url" 2>/dev/null | grep -i "^content-length:" | tail -1 | tr -d '\r' | awk '{print $2}')
  if [ -z "$total" ]; then
    total=$(curl -s -L -r 0-0 -o /dev/null -D - --max-time 30 "$url" 2>/dev/null | grep -iE "^content-range:" | tail -1 | tr -d '\r' | awk -F'/' '{print $2}')
  fi
  [ -z "$total" ] && { echo "    [dl_parallel] 取不到文件大小，放弃"; return 1; }
  local have=$(stat -c%s "$out" 2>/dev/null || echo 0)
  if [ "$have" = "$total" ]; then echo "    [dl_parallel] 已完整，跳过"; return 0; fi
  # 小文件：单连接续传（可靠路径，00003 即由此完成）
  if [ "$total" -lt "$minsz" ]; then
    curl -L -C - --retry 8 --retry-delay 3 --speed-time 60 --speed-limit 500 "$url" -o "$out" 2>/dev/null && [ -s "$out" ] && return 0
    return 1
  fi
  # 大文件：并行分片下载到临时 part，【全部精确校验】通过后才整体原子组装；
  #   ⚠️ 绝不一边下一边追加到 $out（旧版因此产生空洞+来回跳），任何分片失败都干净回退单连接。
  local from=0
  if [ "$have" -gt 0 ] && [ "$have" -lt "$total" ]; then
    echo "    [dl_parallel] 已有 $have/$total 字节，并行下载剩余部分 [from=$have]"
    from=$have
  elif [ "$have" -ge "$total" ]; then
    rm -f "$out"; from=0   # 大小不符(或已损坏)，删掉重下
  fi
  local part="$out.part" chunk=$(( (total - from + nthr - 1) / nthr )) i=0 pids=""
  rm -f "$part".*
  while [ $i -lt $nthr ]; do
    local start=$(( from + i * chunk )); local end=$(( start + chunk - 1 ))
    [ $end -ge $total ] && end=$(( total - 1 ))
    [ $start -ge $total ] && { i=$((i+1)); continue; }
    local exp=$(( end - start + 1 ))
    ( curl -s -L -r "${start}-${end}" --retry 5 --retry-delay 2 --speed-time 30 --speed-limit 300 "$url" -o "${part}.$i"; \
      sz=$(stat -c%s "${part}.$i" 2>/dev/null || echo 0); \
      [ "$sz" -eq "$exp" ] || exit 1 ) &
    pids="$pids $!"
    i=$((i+1))
  done
  local fail=0
  for p in $pids; do wait $p || fail=1; done
  if [ $fail -ne 0 ]; then
    echo "    [dl_parallel] 分片失败(服务端不支持Range/并发限流)，干净回退单连接续传"
    rm -f "$part".*
    # 单连接从 from 续传（保留原前缀，绝不污染）；这才是可靠的兜底
    curl -L -C - --retry 10 --retry-delay 3 --speed-time 60 --speed-limit 500 "$url" -o "$out" 2>/dev/null \
      && [ "$(stat -c%s "$out" 2>/dev/null || echo 0)" = "$total" ] && return 0
    return 1
  fi
  # 全部成功：先拼到临时文件，再【整体追加】到原文件（保证顺序+原子性，无空洞）
  local tmp="$out.tmpmerge"
  : > "$tmp"; i=0
  while [ $i -lt $nthr ]; do cat "${part}.$i" >> "$tmp"; i=$((i+1)); done
  rm -f "$part".*
  cat "$tmp" >> "$out"; rm -f "$tmp"
  local sz=$(stat -c%s "$out" 2>/dev/null || echo 0)
  if [ "$sz" = "$total" ]; then echo "    [dl_parallel] 合并完成($sz 字节)"; return 0; fi
  echo "    [dl_parallel] 合并大小不符($sz!=$total)，回退单连接重下"
  rm -f "$out"
  curl -L -C - --retry 10 --retry-delay 3 --speed-time 60 --speed-limit 500 "$url" -o "$out" 2>/dev/null \
    && [ "$(stat -c%s "$out" 2>/dev/null || echo 0)" = "$total" ] && return 0
  return 1
}
dl_file() {  # $1=hf-mirror repo  $2=文件名  $3=localdir  $4=modelscope完整URL(可选)
  local repo="$1" f="$2" dir="$3" msurl="${4:-}"
  mkdir -p "$dir"
  local out="$dir/$f"
  echo "[下载] $repo/$f"
  # 已完整则秒跳过（优先比 modelscope 大小，回退 hf-mirror；避免对已完整文件反复重下/覆盖）
  local rsize=""
  if [ -n "$msurl" ]; then
    rsize=$(curl -sIL --max-time 25 "$msurl" 2>/dev/null | grep -i "^content-length:" | tail -1 | tr -d '\r' | awk '{print $2}')
  fi
  if [ -z "$rsize" ]; then
    rsize=$(curl -sIL --max-time 25 "https://hf-mirror.com/$repo/resolve/main/$f" 2>/dev/null | grep -i "^content-length:" | tail -1 | tr -d '\r' | awk '{print $2}')
  fi
  local lsize=$(stat -c%s "$out" 2>/dev/null || echo 0)
  if [ -n "$rsize" ] && [ "$lsize" = "$rsize" ]; then
    echo "[OK]   $out 已完整(本地=$rsize 字节), 跳过"; return 0
  fi
  # 优先 modelscope（DSW 在阿里云同骨干；大文件自动并行分片，突破单连接限速）
  if [ -n "$msurl" ]; then
    echo "  -> 优先 modelscope (并行分片加速)"
    if dl_parallel "$msurl" "$out"; then echo "[OK]   $out (modelscope 并行)"; return 0; fi
    echo "  -> modelscope 失败，回退 hf-mirror"
  fi
  # 回退 hf-mirror（并行分片；若分片失败再单连接兜底）
  if dl_parallel "https://hf-mirror.com/$repo/resolve/main/$f" "$out"; then echo "[OK]   $out (hf-mirror 并行)"; return 0; fi
  if curl -L -C - --retry 5 --retry-delay 2 --speed-time 60 --speed-limit 1000 "https://hf-mirror.com/$repo/resolve/main/$f" -o "$out" 2>/dev/null && [ -s "$out" ]; then
    echo "[OK]   $out (hf-mirror curl)"; return 0
  fi
  if curl -L -C - "https://huggingface.co/$repo/resolve/main/$f" -o "$out" 2>/dev/null && [ -s "$out" ]; then
    echo "[OK]   $out (huggingface.co curl)"; return 0
  fi
  echo "[警告] 下载失败: $repo/$f"; return 1
}
ensure_aria2

# 清理上轮可能残留的 .part 分片（避免旧分片干扰续传/合并）
find "$LLM" "$UNET" "$CLIP" "$VAE" -name '*.part*' -delete 2>/dev/null
echo "[清理] 已删除残留 .part 分片"

# 2.1 LLM：Qwen2.5-14B-Instruct GGUF Q4_K_M（3 个分片，逐片下；llama.cpp 自动读后续片）
#     优先 modelscope（DSW 同骨干飞快）
dl_file Qwen/Qwen2.5-14B-Instruct-GGUF "qwen2.5-14b-instruct-q4_k_m-00001-of-00003.gguf" "$LLM" "https://modelscope.cn/models/Qwen/Qwen2.5-14B-Instruct-GGUF/resolve/master/qwen2.5-14b-instruct-q4_k_m-00001-of-00003.gguf"
dl_file Qwen/Qwen2.5-14B-Instruct-GGUF "qwen2.5-14b-instruct-q4_k_m-00002-of-00003.gguf" "$LLM" "https://modelscope.cn/models/Qwen/Qwen2.5-14B-Instruct-GGUF/resolve/master/qwen2.5-14b-instruct-q4_k_m-00002-of-00003.gguf"
dl_file Qwen/Qwen2.5-14B-Instruct-GGUF "qwen2.5-14b-instruct-q4_k_m-00003-of-00003.gguf" "$LLM" "https://modelscope.cn/models/Qwen/Qwen2.5-14B-Instruct-GGUF/resolve/master/qwen2.5-14b-instruct-q4_k_m-00003-of-00003.gguf"

# 2.2 Flux unet GGUF（city96/FLUX.1-dev-gguf，已核实仓库无 Q4_K_M，用真实存在的 Q4_K_S ~6.7G，16G 可装）
#     优先 modelscope
dl_file city96/FLUX.1-dev-gguf "flux1-dev-Q4_K_S.gguf" "$UNET" "https://modelscope.cn/models/city96/FLUX.1-dev-gguf/resolve/master/flux1-dev-Q4_K_S.gguf"

# 清理上版误下的 t5xxl_fp16 残留（旧仓库 404 可能留下空/错误文件，干扰校验）
rm -f "$CLIP/t5xxl_fp16.safetensors"

# 2.3 文本编码器（Flux 双编码器：t5xxl + clip_l，来自 comfyanonymous/flux_text_encoders 仓库）
#     ⚠️ 关键修正(2026-07-29)：
#       - 之前下错仓库(comfyanonymous/flux1 在 hf-mirror/modelscope 均 404/无)；
#         正确仓库 comfyanonymous/flux_text_encoders（modelscope 镜像 AI-ModelScope/flux_text_encoders 已验证 200）。
#       - t5xxl_fp16 实为 ~9.8G，与 Flux Q4_K_S(6.7G) 叠加超 16G 必 OOM；
#         改用 t5xxl_fp8_e4m3fn(~4.9G)，显存峰值降到 ~12G，16G 稳装。
#       - Flux 官方用 DualCLIPLoader 同时加载 t5xxl 与 clip_l，缺一不可。
dl_file comfyanonymous/flux_text_encoders "t5xxl_fp8_e4m3fn.safetensors" "$CLIP" "https://modelscope.cn/models/AI-ModelScope/flux_text_encoders/resolve/master/t5xxl_fp8_e4m3fn.safetensors"
dl_file comfyanonymous/flux_text_encoders "clip_l.safetensors" "$CLIP" "https://modelscope.cn/models/AI-ModelScope/flux_text_encoders/resolve/master/clip_l.safetensors"

# 2.4 VAE（同包）→ 优先 modelscope(black-forest-labs/FLUX.1-dev 已探活200)
dl_file comfyanonymous/flux1 "ae.safetensors" "$VAE" "https://modelscope.cn/models/black-forest-labs/FLUX.1-dev/resolve/master/ae.safetensors"

# ---------- [3/6] 配置 comfyui-sg-llama-cpp 模型文件夹 ----------
echo "=== [3/6] 写 comfyui-sg-llama-cpp config.json（指向 models/LLM） ==="
cat > "$CN/comfyui-sg-llama-cpp/config.json" <<EOF
{
  "model_folders": [
    "/root/ComfyUI/models/LLM"
  ]
}
EOF
echo "[OK] config.json 写入"

# ---------- [4/6] 部署端到端工作流 JSON ----------
echo "=== [4/6] 部署端到端工作流 JSON ==="
WF_SRC="/mnt/workspace/ai-comfyui/pai/workflows/t2i_qwenllm_e2e.json"
WF_DST="$COMFY/user/default/workflows/t2i_qwenllm_e2e.json"
mkdir -p "$(dirname "$WF_DST")"
if [ -f "$WF_SRC" ]; then
  cp "$WF_SRC" "$WF_DST" && echo "[OK] 工作流已部署到 $WF_DST"
else
  echo "[提示] 未找到 $WF_SRC，请在网页手动 Load 该 JSON"
fi

# ---------- [5/6] 重启 ComfyUI ----------
echo "=== [5/6] 重启 ComfyUI（注册节点与模型） ==="
pkill -f "main.py --port 6889" 2>/dev/null; sleep 3
cd "$COMFY"
nohup python3 main.py --port 6889 --listen 0.0.0.0 > /tmp/comfy_run.log 2>&1 &
for i in $(seq 1 40); do curl -s --noproxy 127.0.0.1 http://127.0.0.1:6889/object_info >/dev/null 2>&1 && break; sleep 3; done
curl -s --noproxy 127.0.0.1 http://127.0.0.1:6889/object_info >/dev/null && echo "[OK] ComfyUI 已启动" || echo "[警告] ComfyUI 未启动"

# ---------- [6/6] 校验 ----------
echo "=== [6/6] 校验关键节点 + 模型文件 ==="
echo "--- 节点校验 ---"
for cls in LlamaCPPModelLoader LlamaCPPOptions LlamaCPPEngine LlamaCPPMemoryCleanup UnetLoaderGGUF DualCLIPLoader VAELoader EmptyLatentImage KSampler CLIPTextEncode VAEDecode SaveImage "String Literal"; do
  if curl -s --noproxy 127.0.0.1 http://127.0.0.1:6889/object_info | grep -q "\"$cls\""; then
    echo "[OK]   $cls"
  else
    echo "[缺失] $cls"
  fi
done
echo "--- 模型文件校验 ---"
check_model() { local dir="$1" pat="$2"; local f=$(ls "$dir" 2>/dev/null | grep "$pat" | head -1); [ -n "$f" ] && [ -s "$dir/$f" ] && echo "[OK]   $dir/$f" || echo "[缺失] $dir/$pat"; }
check_model "$LLM" "q4_k_m"
check_model "$UNET" "flux1-dev-Q4_K_S"
check_model "$CLIP" "t5xxl"
check_model "$CLIP" "clip_l"
check_model "$VAE" "ae.safetensors"
echo "=== 安装结束。日志: $LOG ==="
