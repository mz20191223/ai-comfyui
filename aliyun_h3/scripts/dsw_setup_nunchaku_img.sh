#!/bin/bash
# ============================================================
# Nunchaku(Qwen-Image-Edit-2509) + LTX-2 图/视频一站式安装（单 ComfyUI 方案）
# 用途：在 DSW 生图实例 dsw-831216 现有 /root/ComfyUI 上直接安装 Nunchaku 节点 + LTX-2 视频栈，
#       与现有 GGUF/Flux 文生图环境共存于同一台 ComfyUI，端口仍 8188。
#       所有文生图（白底参考图 + 多角度图 + 剧情分镜图）与图生视频（LTX-2）都在这台 ComfyUI 出，串行跑。
# 用法：把本文件传到 DSW 实例后执行  bash dsw_setup_nunchaku.sh
# 端口：8188（与现有 GGUF 实例相同，不另开）
# 注意：会 git pull 升级 ComfyUI 核心(需 >=0.3.60 以支持 Nunchaku 与 LTX-2) 并可能升级 torch；
#       升级后请验证现有 Flux(wf_02)/GGUF-QwenEdit(wf_03) 工作流仍可加载；LTX-2 还需 ~26G 磁盘。
# ============================================================
set -e
export HF_ENDPOINT=https://hf-mirror.com   # 国内加速

BASE=/root/ComfyUI
echo "==> 目标目录: $BASE (现有单 ComfyUI 环境, 端口 8188)"

# --- 辅助下载函数(ModelScope 国内源, 容错重试, 断点续传安全) ---
# 大文件走 modelscope 国内 CDN(cdn-lfs-cn-1), 避免 hf-mirror 把 HF 大文件 302 跳美国 CDN 拖慢
dl_ms() {
  local repo="$1" file="$2" dir="$3" want="${4:-$(basename "$file")}"
  mkdir -p "$dir"
  local dst="$dir/$want"
  local part="$dst.part"
  # 已完成(最终文件存在且非空)则跳过; 否则用 .part 续传, 成功后才改名, 重跑本脚本可安全续传
  if [ -s "$dst" ]; then echo "[跳过] 已存在: $dst"; return; fi
  local url="https://modelscope.cn/models/$repo/resolve/master/$file"
  echo "[下载-国内] $url -> $dst"
  for try in 1 2 3; do
    if curl -L --retry 2 -C - -fsS -o "$part" "$url" 2>/dev/null && [ -s "$part" ]; then
      mv -f "$part" "$dst"
      echo "[OK] $dst"; return
    fi
    sleep 2
  done
  echo "[警告] 下载失败: $url (可手动补下, 不阻断后续)"
}

# ---------- 0. 清理已废弃的 GGUF Qwen-Image-Edit-2511 失败路线(释放 ~16G) ----------
# 背景: gguf Qwen-Edit + fal Multiple-Angles LoRA 经实测只能稳定出 right side view,
#       其余角度全部退化, 已彻底弃用, 改用 Nunchaku 2509。相关模型直接删除, 不保留。
# 重要: 切勿删除 ComfyUI-GGUF 节点(它同时被 LTX-2 视频路线复用)! 这里只删模型文件。
#       也保留 Flux(wf_02 白底参考图) 与 Qwen2.5-14B(sg-llama-cpp 文生图扩写) 不动。
echo "==> [0] 清理废弃的 GGUF Qwen-Edit 路线模型..."
echo "    删除前磁盘:"; df -h /root | tail -1
rm -f "$BASE/models/unet/qwen-image-edit-2511-Q4_K_M.gguf"
rm -f "$BASE/models/clip/Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf"
rm -f "$BASE/models/clip/Qwen2.5-VL-7B-Instruct-mmproj-BF16.gguf"
rm -f "$BASE/models/loras/"*Multiple-Angles* 2>/dev/null
# 清理上一次误下的错误文件名(r32/带日期版, 404 时 wget 可能留了空文件)
rm -f "$BASE/models/diffusion_models/svdq-int4_r32-qwen-image-edit-2509-lightning-4steps-251115.safetensors"
echo "    删除后磁盘:"; df -h /root | tail -1
echo "    [0] 完成 (已删除失败路线的 unet / clip / mmproj / fal-LoRA)"

# ---------- 1. 升级 ComfyUI 核心到最新(需 >=0.3.60 以支持 Nunchaku) ----------
cd "$BASE"
echo "==> [1] 升级 ComfyUI 核心 (当前可能为 0cb84e7e)..."
git pull --ff-only || echo "[1] git pull 失败, 请手动检查; 若已是 >=0.3.60 可忽略"

# ---------- 2. 检查/升级 torch (Nunchaku 需较新 torch, 2.5+ 通常可) ----------
PYVER=$(python3 -c "import torch,sys; print(torch.__version__)" 2>/dev/null || echo "none")
echo "==> [2] 当前 torch: $PYVER"
if python3 -c "import torch,sys; from packaging.version import parse; sys.exit(0 if parse(torch.__version__)>=parse('2.5.0') else 1)" 2>/dev/null; then
  echo "[2] torch 已 >=2.5, 跳过升级"
else
  echo "[2] torch <2.5, 升级到 2.5+cu121 (注意: 升级后需验证 GGUF 工作流)"
  python3 -m pip install torch==2.5.0 torchvision --index-url https://download.pytorch.org/whl/cu121 -i https://pypi.tuna.tsinghua.edu.cn/simple
fi

# ---------- 3. 安装 ComfyUI 依赖 ----------
python3 -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# ---------- 4. 克隆 ComfyUI-nunchaku 节点(mit-han-lab 官方仓库) ----------
if [ ! -d custom_nodes/ComfyUI-nunchaku/.git ]; then
  git clone https://github.com/mit-han-lab/ComfyUI-nunchaku.git custom_nodes/ComfyUI-nunchaku
fi
python3 -m pip install -r custom_nodes/ComfyUI-nunchaku/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple 2>/dev/null || true

# ---------- 5. 安装 nunchaku 推理引擎 wheel(自动匹配当前 torch 版本) ----------
python3 -m pip install nunchaku -i https://pypi.tuna.tsinghua.edu.cn/simple

# ---------- 6. 模型目录(复用现有 models/, 不新建) ----------
# 防御: 旧版脚本用 wget 直接下到最终文件名, 若中途 Ctrl-C 会留下残缺文件; dl_ms 看到"文件存在"会误判已完成而跳过。
#       这里按体积判定: 完整主模型 ~12.6G, 残缺的远小于此, 删除以便重新从国内源下载(完整文件不受影响)。
NM=models/diffusion_models/svdq-int4_r128-qwen-image-edit-2509-lightningv2.0-4steps.safetensors
if [ -f "$NM" ]; then
  SZ=$(stat -c%s "$NM" 2>/dev/null || echo 0)
  if [ "$SZ" -lt 13000000000 ]; then
    echo "    [防御] 发现残缺的 Nunchaku 主模型($SZ 字节 < 13G), 删除以便重新从国内源下载"
    rm -f "$NM"
  fi
fi
mkdir -p models/diffusion_models models/text_encoders models/vae models/workflows

# 6a. DiT 主模型 (官方 lightning 工作流同款: r128 lightningv2.0 INT4)
#     官方 workflow 引用即此 r128 文件名; 来源改 ModelScope 国内源(nunchaku-tech)避免 hf-mirror 跳美国 CDN
dl_ms nunchaku-tech/nunchaku-qwen-image-edit-2509 svdq-int4_r128-qwen-image-edit-2509-lightningv2.0-4steps.safetensors models/diffusion_models

# 6b. 文本编码器 (fp8 ~9.28G, 放 text_encoders/ 不是 clip/)
#     来源 Comfy-Org/Qwen-Image_ComfyUI (Qwen/Qwen-Image-Edit-2509 仓库只有 bf16 分片); 走 ModelScope 国内源
dl_ms Comfy-Org/Qwen-Image_ComfyUI split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors models/text_encoders

# 6c. VAE (现有 qwen_image_vae.safetensors 若已在 models/vae 则跳过); 走 ModelScope 国内源
dl_ms Comfy-Org/Qwen-Image_ComfyUI split_files/vae/qwen_image_vae.safetensors models/vae

# 7. 官方 lightning 工作流作底(后续改造成三视图并行)
#    该 json 已随 ComfyUI-nunchaku 节点克隆到 custom_nodes/, 直接复制即可(无需再走 hf-mirror 下 GitHub 文件)
if [ ! -f models/workflows/nunchaku-qwen-image-edit-2509-lightning.json ]; then
  cp custom_nodes/ComfyUI-nunchaku/example_workflows/nunchaku-qwen-image-edit-2509-lightning.json \
     models/workflows/ 2>/dev/null \
  && echo "[7] 已从节点目录复制官方 lightning 工作流" \
  || echo "[7] 复制失败, 可直接在 ComfyUI 里 Load custom_nodes/ComfyUI-nunchaku/example_workflows/ 下对应 json"
else
  echo "[7] 工作流已存在, 跳过"
fi

echo ""
echo "########## [8] LTX-2 视频栈 (Kijai GGUF) —— 单实例视频生成 ##########"
echo "==> [8] 安装 LTX-2 视频生成所需节点与模型(图用 Nunchaku, 视频用 LTX-2, 同端口 8188 串行)"
# --- 磁盘余量检查(LTX-2 还需 ~26G) ---
AVAIL=$(df -BG /root | awk 'NR==2{print $4}' | tr -d G)
echo "    当前可用磁盘: ${AVAIL}G"
if [ "${AVAIL:-0}" -lt 30 ]; then
  echo "    [警告] 可用空间 < 30G, LTX-2(~26G) 可能装不下! 建议先清理或扩盘后再跑本段。"
fi

# --- 8.1 节点: ComfyUI-KJNodes(提供 LTX2 原生节点+最新 loader) + 确保 ComfyUI-GGUF 在场 ---
CN=custom_nodes
if [ ! -d "$CN/ComfyUI-KJNodes/.git" ]; then
  git clone https://github.com/kijai/ComfyUI-KJNodes.git "$CN/ComfyUI-KJNodes"
fi
python3 -m pip install -r "$CN/ComfyUI-KJNodes/requirements.txt" -i https://pypi.tuna.tsinghua.edu.cn/simple 2>/dev/null || true
# ComfyUI-GGUF 已在原 GGUF 路线装过(UnetLoaderGGUF/DualCLIPLoaderGGUF), 缺失则补装
if [ ! -d "$CN/ComfyUI-GGUF/.git" ]; then
  git clone https://github.com/city96/ComfyUI-GGUF.git "$CN/ComfyUI-GGUF"
fi

# --- 8.2 模型(全部走 ModelScope 国内源, 避免 hf-mirror 把 HF 大文件 302 跳美国 CDN 拖慢) ---
# 说明: Kijai 官方 LTXV2_comfy 在 ModelScope 无干净镜像; 改用 chatpig/ltx2-gguf(unsloth 同款量化, 国内 CDN)
#       与 unsloth 官方镜像。主模型用 chatpig 的 iq4_xs(10.5G, Q4 级, 24G 显存舒适), 重命名为工作流常用名
#       dev_Q4_K_M 以便直接 Load。dev 主模型须配 dev connector(非 distill); 故 connector 取 chatpig 的
#       dev_fp8 版, 重命名为 *_dev_bf16。各文件均已 curl 探活确认在国内 cdn-lfs-cn 存在。
UNET=models/unet
TEXT=models/text_encoders
VAE=models/vae
mkdir -p "$UNET" "$TEXT" "$VAE" models/upscale_models
# 主模型 (dev, iq4_xs) -> 重命名为 dev_Q4_K_M 供工作流引用
dl_ms chatpig/ltx2-gguf ltx2-19b-dev-iq4_xs.gguf "$UNET" "LTX-2-dev-Q4_K_M.gguf"
# Gemma 文本编码器 (unsloth Q4_K_M, 国内源, 已被 DualCLIPLoaderGGUF 直接加载)
dl_ms unsloth/gemma-3-12b-it-GGUF gemma-3-12b-it-Q4_K_M.gguf "$TEXT" "gemma-3-12b-it-Q4_K_M.gguf"
# embeddings connector (dev 版, 配 dev 主模型; 非 distill)
dl_ms chatpig/ltx2-gguf ltx2-19b-embeddings_connector_dev_fp8_e4m3fn.safetensors "$TEXT" "ltx-2-19b-embeddings_connector_dev_bf16.safetensors"
# 视频 / 音频 VAE
dl_ms chatpig/ltx2-gguf ltx2_video_vae_fp8_e4m3fn.safetensors "$VAE" "LTX2_video_vae_bf16.safetensors"
dl_ms chatpig/ltx2-gguf ltx2_audio_checkpoint_vae_bf16.safetensors "$VAE" "LTX2_audio_vae_bf16.safetensors"
# 可选: 空间 upscaler(高清输出), Lightricks/LTX-2 国内源
dl_ms Lightricks/LTX-2 ltx-2-spatial-upscaler-x2-1.0.safetensors models/upscale_models "ltx-2-spatial-upscaler-x2-1.0.safetensors"

# --- 8.3 参考工作流(HerrDehy I2V GGUF) ---
if [ ! -f models/workflows/LTX2_I2V_GGUF.json ]; then
  wget -c --tries=3 -T 60 -O models/workflows/LTX2_I2V_GGUF.json \
    "https://github.com/HerrDehy/SharePublic/raw/main/LTX2_I2V_GGUF%20v0.3.json" \
  || echo "[8.3] I2V 工作流下载失败(不阻断), 可手动从 HerrDehy/SharePublic 获取"
else
  echo "[8.3] I2V 工作流已存在, 跳过"
fi
echo "==> [8] LTX-2 视频栈安装完成"

echo ""
echo "==> 安装完成 (图+视频 一站式, 单 ComfyUI, 端口 8188)。"
echo "==> 启动: cd $BASE && python3 main.py --port 8188 --listen 0.0.0.0"
echo "==> 浏览器: https://dsw-gateway-cn-shanghai.data.aliyuncs.com/dsw-831216/proxy/8188/"
echo "==> 图: 首次启动后 Load models/workflows/nunchaku-qwen-image-edit-2509-lightning.json 验证出图"
echo "==> 视频: Load models/workflows/LTX2_I2V_GGUF.json, 把 UnetLoaderGGUF 模型名改为 LTX-2-dev-Q4_K_M.gguf(已下, 实为 chatpig iq4_xs 量化, 重命名便于 Load),"
echo "        DualCLIPLoaderGGUF 的 gemma 改为 gemma-3-12b-it-Q4_K_M.gguf(已下), connector 改为 ltx-2-19b-embeddings_connector_dev_bf16.safetensors(已下), 参考图接 Image 输入。"
echo "==> 重要: 升级后请在 ComfyUI 里验证现有 Flux(wf_02)/GGUF-QwenEdit(wf_03) 工作流仍正常加载"
echo "==> 显存策略: 图与视频不能同驻 24G, 必须串行(先出齐图 -> 卸载 -> 再图转视频)。若视频 OOM 降分辨率到 480p 或关 upscaler。"
