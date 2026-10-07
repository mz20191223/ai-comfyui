# 评估：一键生成多角色对话动画片（Qwen3-TTS + LTX-2）RunningHub 工作流

> 源文件：`D:\Aicomfyui\pai\一键生成多角色对话动画片，Qwen3-TTS+++LTX-2工作流！.json`（124KB，97 节点）
> 评估日期：2026-07-28
> 目标实例：DSW `dsw-823428`，ComfyUI 核心 `0cb84e7e`（2026-07 版），A10 24GB

---

## 1. 这个工作流到底是什么（已拆解节点图确认）

| 模块 | 技术 | 节点证据 |
|---|---|---|
| **视频生成** | **LTX-2**（Kijai Comfy GGUF 版，19B DiT，**原生音画同步**） | `UnetLoaderGGUF: LTX-2-dev-Q8_0.gguf`、`EmptyLTXVLatentVideo`、`LTXVConditioning`、`LTXVScheduler`、`LTXVConcatAVLatent`、`LTXVLatentUpsampler` |
| **对话配音** | **Qwen3-TTS**（ComfyUI-QwenTTS 自定义包） | `FB_Qwen3TTSDialogueInference`、`FB_Qwen3TTSVoiceDesign`、`FB_Qwen3TTSVoiceClonePrompt`、`FB_Qwen3TTSRoleBank` |
| **文本编码器** | Gemma 3 12B（fp8）+ LTX-2 embeddings connector | `DualCLIPLoaderGGUF: gemma_3_12B_it_fp8_e4m3fn.safetensors + ltx-2-19b-embeddings_connector_bf16.safetensors` |
| **VAE** | 视频 VAE + 音频 VAE（分离） | `VAELoader: LTX2_video_vae_bf16` / `VAELoaderKJ: LTX2_audio_vae_bf16` |
| **加速** | 蒸馏 LoRA + 空间 upscaler ×2 | `LoraLoaderModelOnly: ltx-2-19b-distilled-lora...rank_175_bf16 @ 0.6`、`LatentUpscaleModelLoader: ltx-2-spatial-upscaler-x2` |
| **辅助节点包** | easy-use / kjnodes / mtb / LayerStyle | `easy showAnything`、`SimpleCalculatorKJ`、`Audio Duration (mtb)`、`CR Text`、`LayerUtility: PurgeVRAM V2` |

**功能**：输入剧本（如 `Role1: ...\nRole2: ...`）→ Qwen3-TTS 生成多角色对话音频（含声音设计/克隆）→ LTX-2 以 T2V 模式生成匹配视频 → 音画同步合成。是**完整的"对话动画片"流水线**，自带配音，一步到位。

---

## 2. DSW 具备条件评估

### ✅ 已具备
- **ComfyUI 核心含 LTX-2 原生节点**：`0cb84e7e` 是 2026-07 版，晚于 LTX-2 发布（2026-01），`LTXV*` 节点（`cnr_id: comfy-core`）已内置。
- **GGUF 加载器已装**（ComfyUI-GGUF）：`UnetLoaderGGUF` / `DualCLIPLoaderGGUF` / `LoraLoaderModelOnly` 都在。
- **显卡 A10 24GB**：理论可跑（需选对量化）。

### ❌ 不具备，必须补齐

**A. 自定义节点包（5+ 个，工作流缺它们会直接报节点缺失）**
| 包 | 提供的关键节点 | 官方地址（需确认） |
|---|---|---|
| ComfyUI-QwenTTS | `FB_Qwen3TTS*` 全部（工作流配音核心） | `github.com/1038lab/ComfyUI-QwenTTS`（工作流 Note 已给出） |
| ComfyUI-KJNodes | `LTXVLatentUpsampler`/`VAELoaderKJ`/`SimpleCalculatorKJ`/`PurgeVRAM` | `github.com/kijai/ComfyUI-KJNodes` |
| ComfyUI-Easy-Use | `easy showAnything` | `github.com/yolain/ComfyUI-Easy-Use` |
| ComfyUI-M-Toolkit (mtb) | `Audio Duration (mtb)` | `github.com/melmass/comfyui-mtb` |
| ComfyUI_Custom_Nodes_AlekPet（或 Advanced-LayerStyle） | `CR Text` / `LayerUtility: PurgeVRAM V2` | 需确认具体包名 |

> 安装前先确认 DSW 能 `git clone` GitHub（之前 DSW 沙箱连不上本机，但外网访问需验证；不行则走代理或手动传）。

**B. LTX-2 模型权重（6 个文件，总计约 30–40GB）**
| 文件 | 大小 | 说明 |
|---|---|---|
| `LTX-2-dev-Q8_0.gguf` | **20.4GB** | ⚠️ **A10 24GB 装不下**，需换 `LTX-2-dev-Q4_K_M.gguf`(12.7GB) |
| `gemma_3_12B_it_fp8_e4m3fn.safetensors` | ~8GB | 文本编码器 |
| `ltx-2-19b-embeddings_connector_bf16.safetensors` | ~1GB | embedding 连接器 |
| `LTX2_video_vae_bf16.safetensors` | ~1GB | 视频 VAE |
| `LTX2_audio_vae_bf16.safetensors` | ~数百 MB | 音频 VAE |
| `ltx-2-spatial-upscaler-x2-1.0.safetensors` | ~数百 MB | 空间 upscaler |
| `ltx-2-19b-distilled-lora...rank_175_bf16.safetensors` | 工作流指定 | 蒸馏加速 LoRA |

来源（官方）：`huggingface.co/Kijai/LTXV2_comfy`（GGUF 在此 / 其他 safetensors 在子目录）。

### ⚠️ 显存核算（A10 24GB）
- unet Q4_K_M (12.7) + gemma fp8 (8) + embeddings (~1) + 视频/音频 VAE (~2) + 运行时/激活 (~3) ≈ **26GB+ → 临界/可能 OOM**
- **缓解**：关空间 upscaler（省 ~1-2GB，降清晰度）、降分辨率（720p→480p）、用 `PurgeVRAM` 节点（工作流已带）分阶段释放。
- 若仍 OOM，唯一出路是换更大显存实例（如 A100 40/80G）或换 LTX-2.3 FP8（22B，但节点栈不同，见下）。

---

## 3. 与我们当前路线的关系（重要战略提醒）

- **当前阶段目标（用户 2026-07-26 定）**：第一步 = 桃子**单角色**带情节视频。
- **这个工作流**：直接做**多角色对话动画片**（柯基+加菲猫对话示例）→ **跳过了"单角色"阶段，接近最终"漫剧"阶段**。
- **身份一致性冲突**：它是 **T2V 模式**（纯 prompt，无 `LoadImage` 接参考图），**不会锁定桃子身份**——每次生成桃子可能长不一样。这和我们规划的"角色圣经参考图 + I2V 保身份"思路冲突。
  - 若要用于桃子：需把 `LTXVConditioning` 改为接桃子参考图（I2V 模式），或接受 T2V 随机身份。
- **节点栈冲突**：它用 **LTX-2（Kijai 路径：DualCLIPLoaderGGUF + Gemma + embeddings_connector）**；我们之前计划的是 **LTX-2.3（Lightricks 官方：LTXAVTextEncoderLoader + 单独 Gemma + 原生 I2V 节点）**。两者**不是同一套节点，不能混用**。选哪个要先定。

---

## 4. 建议路线（待用户拍板）

- **路线 A（稳健，贴合当前阶段）**：继续我们原计划——先把"桃子单角色 I2V"跑通（选 LTX-2 或 2.3 之一），验证身份保持后，再引入这个工作流的 Qwen3-TTS 做多角色对话配音。
- **路线 B（激进，跳阶段）**：直接研究这个工作流——补 5 个节点包 + 下 Q4 量化 LTX-2 模型，在 DSW 实跑验证"多角色对话动画片"通不通（桃子改 prompt 试），顺便验证 LTX-2 + Qwen3-TTS 整合可行性。
  - 价值：一步到位验证我们最终"漫剧"阶段的核心技术栈；若通，后续单角色阶段可直接复用它的 LTX-2 底座。
  - 风险：显存临界、节点包未装、T2V 不锁身份，需较多调试。

> 官方/来源链接（按铁律核实）：
> - LTX-2 模型与节点要求：`https://huggingface.co/Kijai/LTXV2_comfy`
> - Qwen3-TTS 节点包：`https://github.com/1038lab/ComfyUI-QwenTTS`（工作流 Note 给出）
> - LTX-2.3 vs LTX-2 区别：`https://wan2.video/zh/ltx-2.3` 及 `crepal.ai/blog/?p=5782`
