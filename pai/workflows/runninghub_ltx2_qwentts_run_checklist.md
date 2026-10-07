# 现成工作流「多角色对话动画片 LTX-2 + Qwen3-TTS」DSW 原样跑通清单（已核实修订版 2026-07-28 15:30）

> 目标：按工作流原样跑通，不魔改。本清单所有依赖来源均查自官方/上游仓库（GitHub API + 代码搜索 + HF 文件树），无盲猜。
> 一键安装脚本：`D:\Aicomfyui\pai\dsw_setup_ltx2_qwentts.sh`（已 bash -n 校验通过）

## 0. 跑之前必须知道的三条"现实差异"（已逐一核实并解决）

1. **TTS 节点真实来源 ≠ 工作流注记**：工作流用 `FB_Qwen3TTS*`（4 个：`FB_Qwen3TTSDialogueInference` / `FB_Qwen3TTSVoiceDesign` / `FB_Qwen3TTSVoiceClonePrompt` / `FB_Qwen3TTSRoleBank`）。
   - 工作流内 "About Models" 注记写的 `1038lab/ComfyUI-QwenTTS` 是**错的**：其 main 只有 `AILab_*` 节点，且仓库历史中**从未有过 FB_ 节点**（GitHub 代码搜索 + commit 历史双重确认）。
   - **真实来源 = `flybirdxx/ComfyUI-Qwen-TTS`**（★1805，且自带 `example/Multi-character dialogue.json` 示例，与工作流"多角色对话"主题吻合）。脚本已改用它，4 个 FB_ 节点全部在其仓库中确认存在。
2. **mtb / LayerStyle 地址写错（已修）**：
   - mtb 不是 `mattya/ComfyUI_mtb`（mattya 名下无此仓库）→ 实为 **`melMass/comfy_mtb`**（含 `nodes/audio.py` 的 "Audio Duration (mtb)"）。
   - LayerStyle 不是 `pythongosssss/ComfyUI-LayerStyle`（404）→ 实为 **`chflame163/ComfyUI_LayerStyle`**（★3111，含 `py/purge_vram.py` 的 "LayerUtility: PurgeVRAM V2"）。
3. **ComfyUI 版本漂移**：工作流 `extra.comfy_fork_version = feature/av_inference@a6994ed1`（特定 fork）。DSW 当前 stock `0cb84e7e`（晚于 LTX-2 发布，理论含原生 LTX-2 节点），以 object_info 校验为准。

## 一、必须补齐的两批依赖（脚本已自动化）

### A. 5 个自定义节点包（已逐一核实官方地址）
| 包 | 官方地址 | 提供的关键节点 | 核实方式 |
|---|---|---|---|
| ComfyUI-Qwen-TTS | `github.com/flybirdxx/ComfyUI-Qwen-TTS` | `FB_Qwen3TTS*`（4 个） | 代码搜索确认 4 类全在 |
| ComfyUI-KJNodes | `github.com/kijai/ComfyUI-KJNodes` | VAELoaderKJ / SimpleCalculatorKJ / PurgeVRAM | 已 [OK] |
| ComfyUI-Easy-Use | `github.com/yolain/ComfyUI-Easy-Use` | easy showAnything | 已 [OK] |
| ComfyUI_mtb | `github.com/melMass/comfy_mtb` | Audio Duration (mtb) | 代码搜索确认 nodes/audio.py |
| ComfyUI-LayerStyle | `github.com/chflame163/ComfyUI_LayerStyle` | LayerUtility: PurgeVRAM V2 | 代码搜索确认 py/purge_vram.py |

> flybirdxx 依赖：`transformers>=4.57.0,<5.0.0` + torchaudio + librosa + soundfile 等 → 与脚本全局 pin 的 `transformers==4.57.3` **兼容**，无冲突。
> 每个包装各自 requirements；然后重启 ComfyUI 注册节点。

### B. LTX-2 模型权重（A10 用 Q4，且改名对齐工作流期望名）
| 工作流期望名 | 实际下载源（官方/上游） | 大小 | 备注 |
|---|---|---|---|
| `LTX-2-dev-Q4_K_M.gguf`（必须 Q4，非 Q8） | `Kijai/LTXV2_comfy` → `diffusion_models/ltx-2-19b-dev_Q4_K_M.gguf` | 12.7G | 脚本改名落 `models/unet/` |
| `gemma-3-12b-it-Q4_K_M.gguf` | `unsloth/gemma-3-12b-it-GGUF`（GGUF 量化版） | 8.6G | 工作流原写死 `gemma_3_12B_it_fp8_e4m3fn.safetensors` **该 fp8 文件公开不存在**（unsloth 仅有 GGUF 量化版，Kijai/Comfy-Org/google 均无）→ 改用 Q4_K_M GGUF，脚本同步改写工作流节点文件名 |
| `ltx-2-19b-embeddings_connector_bf16.safetensors` | `Kijai/LTXV2_comfy` → 现已改名 `..._distill_bf16.safetensors` | ~2.9G | 脚本下载后改名，落 `models/text_encoders/` |
| `LTX2_video_vae_bf16_260115.safetensors` | `Kijai/LTXV2_comfy` → `VAE/LTX2_video_vae_bf16.safetensors`（现名） | 2.45G | 脚本改名，落 `models/vae/` |
| `LTX2_audio_vae_bf16.safetensors` | `Kijai/LTXV2_comfy` → `VAE/LTX2_audio_vae_bf16.safetensors` | 218M | 同名，落 `models/vae/` |
| `ltx-2-spatial-upscaler-x2-1.0.safetensors` | `Lightricks/LTX-2` 官方 | 数百 M | 落 `models/upscale_models/` |
| `ltx-2-19b-distilled-lora_resized_dynamic_fro09_avg_rank_175_bf16.safetensors` | `Kijai/LTXV2_comfy` → `loras/...` | 3.58G | 工作流写死此名，落 `models/loras/` |

> 模型下载改用 `curl -L` 直连 hf-mirror（已验证直链 302 可达）；`huggingface-cli` 在镜像下对 LFS 大文件会失败，故弃用。

### C. Qwen3-TTS 1.7B 模型（首次运行由节点自动下，不预下）
落 `models/TTS/Qwen3-TTS/<REPO>/`：`Qwen3-TTS-12Hz-1.7B-CustomVoice` / `-VoiceDesign` / `-Base` / `Qwen3-TTS-Tokenizer-12Hz`。
（flybirdxx 节点首次运行会自动拉，若超时再用浏览器/aria2 手动下到该目录。）

## 二、脚本已自动处理
- transformer 固定 `4.57.3`（flybirdxx 兼容 `>=4.57.0,<5.0.0`）。
- 把工作流 JSON 复制进 `user/default/workflows/` 并 sed：
  - `LTX-2-dev-Q8_0.gguf` → `LTX-2-dev-Q4_K_M.gguf`（A10 显存红线）
  - `gemma_3_12B_it_fp8_e4m3fn.safetensors` → `gemma-3-12b-it-Q4_K_M.gguf`（对应 B 表改名）
- 结尾 [7/7] 校验：节点 + 模型文件逐项打 [OK]/[缺失]。

## 三、加载后必须确认
1. UnetLoaderGGUF 的 unet 名 = `LTX-2-dev-Q4_K_M.gguf`（脚本已改；若手动 Load 原 JSON 需自己改）。
2. DualCLIPLoaderGGUF 的 gemma 名 = `gemma-3-12b-it-Q4_K_M.gguf`（脚本已改；若手动 Load 需自己改）。
3. 若 [缺失] 任何节点：对照上面 A 表的官方地址，多半是 clone 失败（看日志 clone 行）。

## 四、已知坑（官方已注明）
- KJNodes 必须够新（1/13 后），否则视频 VAE 加载错位。
- 分辨率宽高÷32、帧数÷8+1；否则静默取整。
- A10 显存临界（Q4 合计 ~26G）：OOM 时断开 LTXVLatentUpsampler / 空间 upscaler 支路，或降 480p；仍 OOM 换大显存实例。

## 五、风险预判（原样跑的硬伤）
- 工作流是 **T2V 纯 prompt**，无参考图接口 → 角色每次随机，不锁身份（契合"先不管桃子"，但不服务桃子一致性）。
- 模型总下载 ~30GB（Q4 LTX-2 + Gemma + 双 VAE + upscaler + LoRA + TTS），DSW 走 hf-mirror 直链。
- 三大漂移（TTS 节点来源、mtb/LayerStyle 地址、ComfyUI fork 版本）均已核实并修正，其中前两项脚本已用正确仓库，最大剩余不确定项仅剩 ComfyUI fork 版本（以 object_info 校验为准）。
