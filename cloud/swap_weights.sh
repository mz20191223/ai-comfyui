#!/bin/bash
# ============================================================
# 在 HAI 实例内运行：换 qwen-image-edit GGUF 权重并校验
# 用法: bash /root/swap_weights.sh [量化级别]   默认 Q4_K_M
#
# 根因: 原 unet/qwen-image-edit-2511-Q4_K_M.gguf 仅 2.75G,
#       真实应为 ~13.2G (严重截断) -> GGUFReader reshape 失败。
#       故用 ModelScope 国内镜像下载完整文件。
# 安全策略: 先下载到 .part 临时文件 -> GGUFReader 校验 ->
#           通过才备份旧权重并替换 -> 重启 ComfyUI(supervisor 自动拉起)
#           任何一步失败都不动现有权重、不重启, 可重复执行。
# 注意: 若 13.2G Q4_K_M 在 T4(15.9G) 上 OOM, 改用更小量化重跑:
#       bash /root/swap_weights.sh Q3_K_M
# ============================================================
set -e
Q="${1:-Q4_K_M}"
MS_URL="https://modelscope.cn/api/v1/models/unsloth/Qwen-Image-Edit-2511-GGUF/repo?Revision=master&FilePath=qwen-image-edit-2511-${Q}.gguf"
DST="/root/ComfyUI/models/unet"
OLD="${DST}/qwen-image-edit-2511-Q4_K_M.gguf"
NEW="${DST}/qwen-image-edit-2511-${Q}.gguf"
PART="${NEW}.part"
PY="/root/miniforge3/bin/python3"

cd "$DST"
echo "[1/4] 从 ModelScope 下载 qwen-image-edit-2511-${Q}.gguf (完整, 约 13G, 可能数分钟) -> ${PART}"
curl -L --retry 5 --retry-delay 5 -C - -o "$PART" "$MS_URL"
echo "      大小: $(stat -c%s "$PART" 2>/dev/null || wc -c < "$PART") 字节"

echo "[2/4] GGUFReader 校验 (完整文件应能解析) ..."
"$PY" -c "import gguf; r=gguf.GGUFReader('${PART}'); print('      OK  tensors=%d  arch=%s' % (len(r.tensors), getattr(r,'arch','n/a')))"

echo "[3/4] 替换权重 ..."
if [ -f "$OLD" ] && [ ! -f "${OLD}.bak" ]; then mv "$OLD" "${OLD}.bak"; fi
mv "$PART" "$NEW"

echo "[4/4] 重启 ComfyUI (supervisor 自动拉起) ..."
PID=$(ps aux | grep 'miniforge3/bin/python3 -u main.py' | grep -v grep | awk '{print $2}')
if [ -n "$PID" ]; then kill -9 "$PID"; fi
echo "DONE. supervisor 自动重启后, 在本机运行: cd D:/Aicomfyui/cloud && python gen_refs.py test"
