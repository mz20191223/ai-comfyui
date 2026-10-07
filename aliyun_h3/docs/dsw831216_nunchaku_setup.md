# Nunchaku + ComfyUI 生图实例部署与排障记录（dsw-831216）

> 整理自 2026-08-11 ~ 08-14 与 AI 的排障对话。目标：把桃子角色生图实例从「失败路线」切到 Nunchaku svdq-int4 路线并跑通出图，同时为后续 LTX-2 视频留出一站式安装脚本。

---

## 一、背景与目标

- 项目：桃子角色单角色带情节视频 → 多角色 → 漫剧。本机工作目录 `D:\Aicomfyui\aliyun_h3`。
- 生图实例 **dsw-831216**（A10 24G，端口 **8188**），单 ComfyUI **串行**出图 → 视频。
- 当前阶段：让官方 `nunchaku-qwen-image-edit-2509-lightning.json` 在 24G 上跑通出图（验证 Nunchaku 路线），之后再改造三视图并行工作流出角度图。

## 二、技术路线

### Nunchaku svdq-int4 出图
- 节点：`mit-han-lab/ComfyUI-nunchaku`（需 ComfyUI ≥ 0.3.60）。
- 主模型：`svdq-int4_r128-qwen-image-edit-2509-lightningv2.0-4steps.safetensors`（12.6G，INT4，官方 lightning 工作流同款，steps=4、cfg=1）。
- 文本编码器：`qwen_2.5_vl_7b_fp8_scaled.safetensors`（来自 `Comfy-Org/Qwen-Image_ComfyUI` 的 `split_files/text_encoders/`，不在 Qwen 官方仓）。
- VAE：`qwen_image_vae.safetensors`（同 Comfy-Org 仓 `split_files/vae/`）。
- Qwen-Image-Edit 原生支持自然语言改视角（"Shows the back-side of the boy" 等），不依赖 fal `<sks>` LoRA。三 KSampler 并行一次出背/左/右三视图。

### LTX-2 视频（后续，已确认国内源）
- 主模型 `chatpig/ltx2-gguf` 的 `ltx2-19b-dev-iq4_xs.gguf`（10.5G）→ 改名 `LTX-2-dev-Q4_K_M.gguf`。
- Gemma `unsloth/gemma-3-12b-it-GGUF` 的 `gemma-3-12b-it-Q4_K_M.gguf`。
- connector / VAE / upscaler：`chatpig/ltx2-gguf` + `Lightricks/LTX-2`。

### VRAM 串行约束
24G 装不下 Nunchaku + LTX-2 同驻显存。方案：先出图 → 卸载（释放显存）→ 另开视频工作流 Load，系统自动把显存让给视频模型（即关闭生图工作流，非删文件）。

## 三、已核实的国内下载源清单（curl 验证 HTTP 200 / 国内 CDN）

| 文件 | 源 |
|---|---|
| Nunchaku 主模型 12.6G | `modelscope.cn/models/nunchaku-tech/nunchaku-qwen-image-edit-2509/resolve/master/svdq-int4_r128-qwen-image-edit-2509-lightningv2.0-4steps.safetensors` |
| 文本编码器 9G | `modelscope.cn/models/Comfy-Org/Qwen-Image_ComfyUI/resolve/master/split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors` |
| VAE | Comfy-Org/Qwen-Image_ComfyUI `split_files/vae/qwen_image_vae.safetensors` |
| LTX-2 主模型 10.5G | chatpig/ltx2-gguf `ltx2-19b-dev-iq4_xs.gguf`（改名 LTX-2-dev-Q4_K_M.gguf） |
| LTX-2 Gemma | unsloth/gemma-3-12b-it-GGUF `gemma-3-12b-it-Q4_K_M.gguf` |
| LTX-2 connector/VAE/upscaler | chatpig/ltx2-gguf + Lightricks/LTX-2 |

> 关键结论：ModelScope 与 chatpig 从这台 DSW 实测也只有 ~1.2 MB/s，跟之前美国 CDN 一样慢。**瓶颈是 DSW 实例出口带宽约 1.2 MB/s 封顶**，不是 CDN 地域问题。国内源的意义是「避开美国 CDN 偶发更慢/断流」，但突破不了带宽上限。

## 四、本机工作文件落地约定（用户铁律）

- 所有工作文件（脚本/工作流/文档）放对应项目 **D 盘目录**（`D:\Aicomfyui\aliyun_h3\...`），**不要创建在 C 盘 Downloads**。
- ComfyUI「打开工作流」是**上传本机文件**模式（原生本地对话框），非浏览云端，故需本机有 json 副本。参考工作流已存 `D:\Aicomfyui\aliyun_h3\workflows\nunchaku-qwen-image-edit-2509-lightning.json`。

## 五、排障时间线（Errors & Fixes）

1. **404（主模型文件名）**：初写 `lightning-4steps-251115` 带日期文件名（仅子目录有），官方要根目录 `r128 lightningv2.0-4steps`；文本编码器源错（Qwen 仓无 fp8），改 Comfy-Org。已修正。
2. **step0 清理没生效**：相对路径打到 `/mnt/workspace`，加 `$BASE/` 前缀修复（实测释放 18G：31G→49G）。
3. **美国 CDN 慢**：hf-mirror 302 跳 `us.aws.cdn.hf.co` ~1.2 MB/s，全改 ModelScope 国内源。
4. **续传坑**：`if [ ! -f ]` 误判半成品为完成，改 `.part` 临时名 + 完成改名。
5. **误放 C 盘**：AI 把工作流下到 Downloads 被纠正，已复制到 D 盘项目目录并删除 C 盘副本。
6. **Load 报 5 错**：①缺失 ComfyUI-nunchaku 节点（目录在，需重启识别）；②缺失 qwen_2_5_vl 模型；③缺输入 Image（lightning 是图生图，必须接参考图）。
7. **dl_ms 第 6 步 bug**：脚本的 `dl_ms` 函数在 DSW 上对 nunchaku-tech / Comfy-Org 两仓下载踩坑，主模型 + 文本编码器根本没落地（`diffusion_models` 空、text_encoders 仅 Flux 的 clip_l/t5xxl）。改用 `curl -L --retry 5 -o` 手动补下。
8. **torch 2.5.0 太旧**：升 torch 后 ComfyUI 核心报 `ValueError: infer_schema(func): Parameter kernel_size has unsupported type list[int]`——`comfy_kitchen 0.2.30` 用了 `list[int]` 新语法，但 torch 2.5.0 的 `infer_schema` 只认 `typing.List[int]`。需 torch ≥ 2.6。
9. **nunchaku 装错包（重大）**：`pip show nunchaku` 显示依赖 `matplotlib, numpy, pandas, scipy, tqdm` —— 这是 PyPI 上同名的**统计包 0.16.1**，不是节点要的**量化库**。量化库是 `nunchaku>=1.0.1`（来自 `nunchaku-tech/nunchaku`，带 `+torch2.x` 后缀），正确 wheel 在官方 GitHub Releases，不在 PyPI 默认源。
10. **miniforge3 路径不存在**：生图实例启动曾误用 `/root/miniforge3/bin/python3`（那是视频实例 dsw-823428 的路径），生图实例 dsw-831216 的 python 是 `/usr/local/bin/python3`（python3.11，nunchaku 装在此环境）。

## 六、当前状态与收尾命令（截至 2026-08-14 12:40）

- ✅ 两份模型已齐：主模型 `12069M`、编码器 `8950M`（均在 `/root/ComfyUI/models/`）。
- 🔄 第 1 批：**升 torch 2.7.1**（从阿里云 PyPI 镜像，~821MB），升完重启 ComfyUI 确认核心能起。
- ⏳ 第 2 批：卸错包 + 装正确量化 nunchaku（wheel 在 GitHub Releases，外国源，慢）。

### 第 1 批（升 torch + 重启，已跑/在跑）
```bash
python3 -m pip install --upgrade "torch==2.7.1" "torchvision==0.22.1"
pkill -f "main.py --port 8188" 2>/dev/null; sleep 3
cd /root/ComfyUI
nohup python3 main.py --port 8188 --listen 0.0.0.0 > /root/comfy_start.log 2>&1 &
sleep 40
head -n 50 /root/comfy_start.log
grep -i -E "nunchaku|ImportError|Traceback|Error" /root/comfy_start.log | head -30
```

### 第 2 批（卸错包 + 装正确量化库，第 1 批确认 ComfyUI 起来后跑）
```bash
# 卸掉装错的同名统计包
python3 -m pip uninstall -y nunchaku

# wheel 下到本地（续传 + 全错误重试，跟模型下载同款）
mkdir -p /root/whl
curl -L --retry 10 --retry-all-errors --retry-delay 10 --connect-timeout 60 -C - \
  -o /root/whl/nunchaku-1.0.1+torch2.7-cp311-cp311-linux_x86_64.whl \
  "https://github.com/nunchaku-tech/nunchaku/releases/download/v1.0.1/nunchaku-1.0.1+torch2.7-cp311-cp311-linux_x86_64.whl"

# GitHub 直连太慢/超时时的社区镜像备选：
#   https://mirror.ghproxy.com/https://github.com/nunchaku-tech/nunchaku/releases/download/v1.0.1/nunchaku-1.0.1+torch2.7-cp311-cp311-linux_x86_64.whl

# 本地安装（不再联网）
python3 -m pip install /root/whl/nunchaku-1.0.1+torch2.7-cp311-cp311-linux_x86_64.whl
```

> wheel 版本说明：已核对官方索引，需 **cp311**（对应 python 3.11.11）+ **torch2.7**（对应刚升的 2.7.1）。

## 七、关键事实速查

| 项 | 值 |
|---|---|
| 生图实例 python | `/usr/local/bin/python3`（python3.11，非 miniforge3） |
| ComfyUI 启动 | `cd /root/ComfyUI && python3 main.py --port 8188 --listen 0.0.0.0` |
| 网关代理 | `https://dsw-gateway-cn-shanghai.data.aliyuncs.com/dsw-831216/proxy/8188/`（IP 变但此路径不变） |
| 实例重启后 | 进程停、链接失效，重启并拉起 ComfyUI 即恢复；模型文件在云盘不丢 |
| 续传命令 | `curl ... -C -`（掉了从断点续，勿用普通 `-o` 覆盖） |
| DSW 带宽 | 出口约 1.2 MB/s 封顶，串行/并行总时长相近 |

## 八、经验教训

- 动手前必查官方文档/模型卡确认包名、版本、源——本次 `nunchaku` 同名统计包 vs 量化库是典型坑。
- 大文件下载一律用 `curl -C - --retry-all-errors`，避开中途 SSL 超时白等。
- DSW 带宽封顶，并行不省时；建议串行（主模型优先）降低抖动超时概率。
- 跨实例别混用 python 路径；先 `which python3` + `import 目标库` 验证环境再拉起服务。
