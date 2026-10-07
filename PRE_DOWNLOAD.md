# 本地预下载清单（开机前下好 → 开机直接传 HAI，省 GPU 钱）

> 原则：HAI 开机按秒计费，所有模型在本地提前下好，开机后通过 JupyterLab 上传或 scp，
> 开机第一分钟就能跑探测+测试片，不浪费一分钱。
>
> 总下载量：**Tier1 ≈ 9.4 GB** | Tier1+Tier2 ≈ 12.7 GB
> 存放位置：先全部下到 `D:\Aicomfyui\models\` 子目录，开机后按「目标路径」列复制到 HAI 对应目录。

## ⚠️ 本机实测关键提醒（必读）
- **官方源 `huggingface.co` 在本机被墙/超时连不上**，全部改用国内镜像 **`hf-mirror.com`**（已在本仓库 `download_all_tier1.sh` / `download_tier1.bat` / 下方链接中替换好）。
- **Git Bash 下 curl 必须写 Windows 路径 `D:/Aicomfyui/...`，不能写 `/d/Aicomfyui/...`**（后者会报 `curl: (23) Failed to open the file 系统找不到指定的文件`）。CMD/PowerShell 用 `D:\Aicomfyui\...` 正常。
- 正在跑的一键下载：`bash download_all_tier1.sh`（后台，带断点续传，中断重跑自动续）。
- 实测镜像速度约 **1.3 MB/s**，Tier1 全量约 **1.5~2 小时**，请耐心等后台完成通知。

---

## Tier1 必需（首帧锚定方案，不开 IPAdapter）

| # | 文件名 | 大小 | 用途 | 下载来源 | 本地存放目录 |
|---|--------|------|------|----------|-------------|
| 1 | `sd_xl_base_1.0.safetensors` | **~6.5 GB** | SDXL 基座模型（方案核心） | HuggingFace | `models\checkpoints\` |
| 2 | `Canopus-Pixar-Art.safetensors` | **~137 MB** | 皮克斯风格 LoRA（B站视频推荐） | HuggingFace prithivMLmods | `models\loras\` |
| 3 | `sdxl_vae_fp16fix.safetensors` | **~335 MB** | SDXL VAE（修复黑图，B站视频推荐） | HuggingFace | `models\vae\` |
| 4 | `mm_sdxl_v10_beta.ckpt` | **~2.2 GB** | AnimateDiff 动画模块（SDXL版，视频必需） | HuggingFace | `models\animatediff_models\` |
| 5 | VideoHelperSuite 插件 | **~2 MB**（代码） | 视频合成输出节点（VHS_VideoCombine） | GitHub | `plugins\ComfyUI-VideoHelperSuite\` |

**Tier1 小计：~9.14 GB**

### 下载命令（Windows PowerShell / Git Bash）

```bash
# ====== 1) 创建目录结构 ======
mkdir -p D:/Aicomfyui/models/checkpoints
mkdir -p D:/Aicomfyui/models/loras
mkdir -p D:/Aicomfyui/models/vae
mkdir -p D:/Aicomfyui/models/animatediff_models
mkdir -p D:/Aicomfyui/plugins

# ====== 2) SDXL 基座 (6.5GB, 最大文件，优先下) ======
# HuggingFace: stabilityai/stable-diffusion-xl-base-1.0
curl -L -o D:/Aicomfyui/models/checkpoints/sd_xl_base_1.0.safetensors \
  "https://hf-mirror.com/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors"

# ====== 3) Pixar LoRA (137MB, HuggingFace) ======
# Canopus-Pixar-Art by prithivMLmods（SDXL 皮克斯风格，触发词: Pixar / Pixar-style / Disney Pixar）
curl -L -o D:/Aicomfyui/models/loras/Canopus-Pixar-Art.safetensors \
  "https://hf-mirror.com/prithivMLmods/Canopus-Pixar-Art/resolve/main/Canopus-Pixar-Art.safetensors"

# ====== 4) SDXL VAE 修复 (335MB) ======
# 由 madebyollin 提供，修复 SDXL 黑图问题（B站视频明确推荐）
curl -L -o D:/Aicomfyui/models/vae/sdxl_vae_fp16fix.safetensors \
  "https://hf-mirror.com/madebyollin/sdxl-vae-fp16-fix/resolve/main/sdxl_vae_fp16fix.safetensors"

# ====== 5) AnimateDiff 动画模块 SDXL版 (2.2GB) ======
# guoyww/AnimateDiff 的 SDXL beta 版
curl -L -o D:/Aicomfyui/models/animatediff_models/mm_sdxl_v10_beta.ckpt \
  "https://hf-mirror.com/guoyww/AnimateDiff/resolve/main/mm_sdxl_v10_beta.ckpt"

# ====== 6) VideoHelperSuite 插件 (代码，git clone) ======
cd D:/Aicomfyui/plugins && git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git
```

---

## Tier2 可选（仅当 Tier1 测试片角色仍漂移时才需要）

| # | 文件名 | 大小 | 用途 | 下载来源 | 本地存放目录 |
|---|--------|------|------|----------|-------------|
| 6 | `clip_vision_g.safetensors` | **~2.4 GB** | CLIP Vision 编码器（IPAdapter 配套） | HuggingFace | `models\clip_vision\` |
| 7 | `ip-adapter-plus-face_sdxl_vit-h.safetensors` | **~809 MB** | IPAdapter 权重（非 FaceID 普通版） | HuggingFace | `models\ipadapter\` |
| 8 | ComfyUI-IPAdapter_plus 插件 | **~2 MB**（代码） | IPAdapter 节点（IPAdapterAdvanced 等） | GitHub | `plugins\ComfyUI_IPAdapter_plus\` |

**Tier2 小计：~3.21 GB**

### Tier2 下载命令

```bash
# ====== 7) CLIP Vision (2.4GB) ======
curl -L -o D:/Aicomfyui/models/clip_vision/clip_vision_g.safetensors \
  "https://hf-mirror.com/openai/clip-vit-large-patch14/resolve/main/pytorch_model.bin"
# 注意：ComfyUI 用的是特定格式，也可能需要：
# curl -L -o D:/Aicomfyui/models/clip_vision/clip_vision_g.safetensors \
#   "https://hf-mirror.com/h94/IP-Adapter/resolve/main/models/image_encoder/model.safetensors"

# ====== 8) IPAdapter plus-face SDXL (809MB) ======
curl -L -o D:/Aicomfyui/models/ipadapter/ip-adapter-plus-face_sdxl_vit-h.safetensors \
  "https://hf-mirror.com/h94/IP-Adapter/resolve/main/models/ip-adapter-plus-face_sdxl_vit-h.safetensors"

# ====== 9) IPAdapter 插件 (git clone) ======
cd D:/Aicomfyui/plugins && git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus.git
```

---

## 开机后上传到 HAI 的目标路径

| 本地文件 | HAI 目标路径 | 上传方式 |
|----------|-------------|---------|
| `models/checkpoints/sd_xl_base_1.0.safetensors` | `/root/ComfyUI/models/checkpoints/` | JupyterLab 上传 / scp |
| `models/loras/Canopus-Pixar-Art.safetensors` | `/root/ComfyUI/models/loras/` | JupyterLab 上传 / scp |
| `models/vae/sdxl_vae_fp16fix.safetensors` | `/root/ComfyUI/models/vae/` | JupyterLab 上传 / scp |
| `models/animatediff_models/mm_sdxl_v10_beta.ckpt` | `/root/ComfyUI/models/animatediff_models/` | JupyterLab 上传 / scp |
| `plugins/ComfyUI-VideoHelperSuite/` | `/root/ComfyUI/custom_nodes/ComfyUI-VideoHelperSuite/` | JupyterLab 终端 git clone（推荐，更快）|
| `models/clip_vision/clip_vision_g.safetensors` | `/root/ComfyUI/models/clip_vision/` | 仅 Tier2 |
| `models/ipadapter/ip-adapter-plus-face_sdxl_vit-h.safetensors` | `/root/ComfyUI/models/ipadapter/` | 仅 Tier2 |
| `plugins/ComfyUI_IPAdapter_plus/` | `/root/ComfyUI/custom_nodes/ComfyUI_IPAdapter_plus/` | 仅 Tier2，终端 git clone |

### 推荐上传方式（最快最稳）

**插件用 git clone（代码小，秒完成）：**
```bash
# 在 HAI JupyterLab 终端执行
cd /root/ComfyUI/custom_nodes
git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git
# Tier2 才需要：
git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus.git
```

**模型文件用 JupyterLab 网页上传（拖拽即可）：**
1. 打开 JupyterLab (`http://<HAI-IP>:6888/lab`)
2. 左侧导航进 `ComfyUI/models/checkpoints/`（或对应子目录）
3. 把本地 `D:\Aicomfyui\models\checkpoints\sd_xl_base_1.0.safetensors` 拖进去
4. 等进度条完成，其余同理

**或者用 scp（适合大文件、可断点续传）：**
```bash
# 本地 PowerShell 执行（把 <HAI-IP> 替换成实际 IP）
scp D:/Aicomfyui/models/checkpoints/sd_xl_base_1.0.safetensors root@<HAI-IP>:/root/ComfyUI/models/checkpoints/
scp D:/Aicomfyui/models/loras/Canopus-Pixar-Art.safetensors root@<HAI-IP>:/root/ComfyUI/models/loras/
scp D:/Aicomfyui/models/vae/sdxl_vae_fp16fix.safetensors root@<HAI-IP>:/root/ComfyUI/models/vae/
scp D:/Aicomfyui/models/animatediff_models/mm_sdxl_v10_beta.ckpt root@<HAI-IP>:/root/ComfyUI/models/animatediff_models/
```

---

## 上传完之后（必须做）

1. **重启 ComfyUI**（装了新插件/模型必须重启才生效）：
```bash
ps -ef | grep -i 'python3 -u main.py' | grep -v 'grep' | awk '{print $2}' | xargs kill -9
cd /root/ComfyUI/ && python3 -u main.py --listen --port=6889 --disable-auto-launch >> /var/log/sd_service.log 2>&1 &
```

2. **跑探测确认**：
```bash
python comfy_discover.py --host http://localhost:6889
```
看到结尾 ✅ Tier1 就绪 → 把地址发我，立刻跑测试片。

---

## 已有但不再需要的文件（可清理）

你 D:\Aicomfyui 上有两个 **FaceID 模型**（之前路线废弃后遗留）：

| 文件 | 大小 | 说明 |
|------|------|------|
| `ip-adapter-faceid-plusv2_sdxl.bin` | 1.4 GB | FaceID 权重（SCRFD 只认人类脸，刺猬不可用，已废弃） |
| `ip-adapter-faceid-plusv2_sdxl_lora.safetensors` | 355 MB | FaceID LoRA（同上，已废弃） |

这两个**不需要传 HAI**。如果 D 盘空间紧可以删掉（省 1.75 GB）。Tier2 要用的是不同的 `ip-adapter-plus-face_sdxl_vit-h.safetensors`（普通 IPAdapter 非 FaceID 版）。
