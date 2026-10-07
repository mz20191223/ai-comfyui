# 桃子项目对话记录（2026-08-05 ~ 2026-08-14 + 长期记忆）

> 由项目记忆每日日志（`.workbuddy/memory/YYYY-MM-DD.md`）合并整理，按日期归档，便于在资料库检索与通读。本篇涵盖：2026-08-05 ~ 2026-08-14 + 长期记忆。

## 2026-08-05
### 2026-08-05 工作日志

## MiniMax H3 × 阿里云 24G：AI 短视频工厂（新支线，与桃子漫剧/CloudBase 并行）

### 背景
- 用户 8/5 提到阿里云新 GPU 实例，想装 ComfyUI 跑"AI 短视频"工作流；参考微信公众号文章《MiniMax H3 开源视频模型来了》（8/3 开源）。
- 本日纯讨论（用户明确"先聊，不动手"），未做部署。

### 硬件（用户确认）
- **阿里云 `ecs.gn7i-c8g1.2xlarge`**：8 vCPU / 30 GiB 内存 / **NVIDIA A10 24G ×1**。实例未开，等方案聊透再开。

### 用户需求（复述确认版）：一句话→完整短视频流水线
```
输入一句话（如"一只皮克斯风格的兔子"）
→ ① LLM 扩写成英文提示词
→ ② 文生图出角色设定图
→ ③ 以角色图为参考出多角度/多表情图（锁定角色）
→ ④ 输入剧情，LLM 生成分镜表（每镜提示词+时长）
→ ⑤ 以角色图为参考按分镜提示词生成分镜图（长相一致）
→ ⑥ 分镜图做首帧/参考，H3 生成带声音视频段
→ ⑦ 多段拼接成片
```
- 输出规格：768p 可接受，先跑通。
- 工作流形态：**官方三套模板起步**（T2V/I2V/R2V），不搞超级大工作流；4 个独立工作流 + 文件夹衔接。

### 选型（本轮敲定）
| 环节 | 方案 | 备注 |
|---|---|---|
| ①④ LLM | **本地 Qwen2.5-14B-Instruct GGUF Q4_K_M**（用户选定） | 跑 A10 显存（comfyui-sg-llama-cpp + llama-cpp CUDA），免费离线，复用 DSW 安装经验 |
| ② 角色图 | Flux.1 dev GGUF（Q4_K_S 6.7G 起步） | DualCLIPLoader(t5xxl_fp8+clip_l)+ae，全复用 7-29 已验证栈 |
| ③⑤ 角度/分镜图 | **Qwen-Image-Edit-2511** GGUF(12.3G) + Multiple-Angles LoRA | `<sks>` + 方位格式已验证；参考图锁角色替代 IP-Adapter |
| ⑥ 视频 | **H3** FL2VA(I2V 分镜首帧) + Ref2VA(R2V 多参考锁身份) | 官方模板改文件名接入 |

### H3 部署事实（8/5 调研核实，官方模型卡+模板源码+社区 GGUF）
- ComfyUI **≥0.30.0** 原生支持（8/3 发布），模板库搜 MiniMaxH3；官方模板直链：
  - T2V `templates/video_minimax_h3_t2v.json`、I2V `video_minimax_h3_i2v.json`、R2V `video_minimax_h3_r2v.json`（Comfy-Org/workflow_templates 仓库）
  - 三套已下载到 `D:\Aicomfyui\aliyun_h3\workflows\`（T2V 42K / I2V 44K / R2V 27K 字节，curl 重试成功）
- 官方推荐文件（Comfy-Org/MiniMax-H3）：`minimax_h3_{fl2va|ref2va}_pruned_int8_convrot.safetensors`(20.97G) + `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors`(15.69G) + 视频VAE fp16(5.21G) + 音频VAE fp32(0.61G)。FL2VA 一套 ≈42.5G 下载；含 Ref2VA ≈63.5G。
- 模板接线（已核实）：UNETLoader→BasicGuider/BasicScheduler；CLIPLoader→MiniMaxH3XxxToVideo；双VAELoader→生成节点/VAEDecode/VAEDecodeAudio；RandomNoise+KSamplerSelect(res_multistep)+SamplerCustomAdvanced；VAEDecode+VAEDecodeAudio→CreateVideo(24fps)→SaveVideo。参数：1344×768、steps20、调度 simple、帧数 17n+5 网格（5秒=124帧）、隐式引导无显式CFG、prompt 须含 Audio 描述。
- 国内下载：modelscope `MiniMax/MiniMax-H3` 官方镜像（Day0 适配）；备选 hf-mirror `Comfy-Org/MiniMax-H3`。
- ⚠️ **nvfp4_awq 是 Blackwell 特性，A10(Ampere) 无原生 FP4**——若 ComfyUI 软件解量化不兼容，文本编码器换 `int8_convrot`(27.14G)，待实例上实测。
- 社区 GGUF 备选：joeygambino/MiniMax-H3-GGUF（fl2va Q5_1 25.9G 适合24-32G卡 / Q4_0 19.9G 16G卡；无 K-quants 因 hidden width 2688）；文本编码器另仓 `joeygambino/MiniMax-H3-encoder-GGUF`（Qwen3-VL-32B Q4_K_M 19.8G + 必须带 mmproj）；节点包 ComfyUI-H3-Multishot+ComfyUI-GGUF+一行架构 patch。

### 磁盘/显存核算
- 模型总量：Flux组~10G + Qwen-Edit组~13G + H3全套~63G ≈ **90G**；建议**数据盘 200G**（系统盘 40G 不够）。
- 显存：Flux段~10G / Qwen-Edit段~13G / H3段 24G 内动态卸载，三段分时加载不冲突。
- 内存 30GiB 够 LLM GPU 版。

### 交付物现状（本目录）
- `D:\Aicomfyui\aliyun_h3\workflows\`：官方 T2V/I2V/R2V 三模板 ✓
- `D:\Aicomfyui\aliyun_h3\README.md`：方案文档**写了开头被截断，未完成**（待续：安装步骤/下载清单/工作流说明/待验证点）。
- 待交付（用户开实例后）：① 一键安装脚本（ComfyUI0.30+节点+4组模型，国内源+aria2/curl 看门狗复用）；② 4 个工作流（扩写/角色图/分镜图/视频）；③ 验证清单。

### 待办（挂起，等用户开实例）
- 用户开 `ecs.gn7i-c8g1.2xlarge` → 告诉我 IP/登录方式。
- 补完 README 方案文档。
- 写安装脚本 + 4 工作流文件。
- 验证链：H3 T2V 首跑 → I2V 兔子分镜 → R2V 锁身份；再串 Flux/Qwen-Edit 前段。

## 上午执行进展（10:0x）

### 实例确认 + 磁盘结构
- 用户实例实为 **阿里云 PAI-DSW**（非 ECS）：`dsw-bat131d8834b7fggc`，镜像 modelScope1.38.0.1 / PyTorch2.10 / CUDA12.8 / py3.12 / Ubuntu22.04；A10 24G、8vCPU、30GiB 内存；系统盘 100G 已用 91G（无独立数据盘）。
- 访问方式定 **路线 B**：Web IDE（JupyterLab）跑脚本，不配公网 SSH（避免 NAT/EIP 持续计费）。
- 磁盘大头：`/root/ComfyUI` 46G + `/mnt/workspace/ai-comfyui` 41G（其 pai/ 子目录占满，用户确认可整删）。
- **关键发现：盘上无 LTX-2**（当时没下成）；Flux 完整模型也不在（只有 .part 残片）；Qwen2.5-VL-7B 编码器在 clip/ 和 text_encoders/ 重复两份（删 text_encoders 那份留 clip/）。
- 删留清单已给用户（删 ai-comfyui 41G + checkpoints/zero123 8G + text_encoders 5.7G + 残片 3.1G + 3 旧节点包 320M ≈ 释放 58G；保留 qwen-edit 13G / 14B LLM 8.6G / clip 编码器 5.7G / LoRA / VAE；新下 H3 42.8G + Flux 9.7G，核算余 ~10G）。

### 模型源探测结论（沙箱实测，脚本已固化）
- **H3**：modelscope `Comfy-Org/MiniMax-H3`（resolve/master/ 子目录 200 ✅）+ hf-mirror 同仓（302 ✅）；**路径含子目录** diffusion_models/ text_encoders/ vae/（根路径会 404）。
- **Flux GGUF**：modelscope `AI-ModelScope/FLUX.1-dev-gguf`（200 ✅）回退 hf-mirror city96/FLUX.1-dev-gguf（302 ✅）。
- **t5xxl_fp8/clip_l**：modelscope `AI-ModelScope/flux_text_encoders`（200 ✅）。
- **ae.safetensors**：modelscope `AI-ModelScope/flux1` **不存在**（record not found）；改用 `AI-ModelScope/FLUX.1-schnell`（200 ✅，官方同款 VAE）；hf-mirror black-forest-labs 403 不可用。
- ComfyUI 0.30 内置模板库自带 MiniMaxH3 三模板（T2V/I2V/R2V），**无需自己部署模板**，模型文件名与官方模板一致（pruned_int8_convrot + nvfp4_awq + 双 VAE）。

### 交付物
- `D:\Aicomfyui\aliyun_h3\setup_h3_pai.sh`（122 行，bash -n 通过）：6 步（环境检查→ComfyUI git pull 升级→8 模型下载[modelscope 并行分片/hf-mirror 回退/已存在跳过]→复用检查→校验→启动 0.0.0.0:8188）。下载器：get_size 用 -r 0-0 + content-range 双兜底；dl_parallel 分片 .part.N 原子合并（吸取 7-29 空洞教训）。
- 模板三套已在 `D:\Aicomfyui\aliyun_h3\workflows\`（备用，实际用 ComfyUI 内置模板库）。
- 待用户：删旧（命令已给）→ df -h 确认 → 粘脚本跑 → 贴日志。
- LLM 暂用现有 CPU 版 llama-cpp（14B 慢但能跑）；CUDA wheel 加速列为后续优化，避免脚本失败点。

## 安装执行（10:2x-11:0x，踩坑记录）
- 用户 PAI 上跑脚本，连续踩 4 个 bash 坑（同族）：`local a=.. b=$(cmd $a)` 在 set -u 下，local 同一行命令替换/算数展开引用未赋值变量会报「未绑定变量」。已全部拆成独立 local 赋值修复。**教训：set -u 脚本里禁止 `local x=$((引用同行的变量))` 或 `local w=$(cmd $same_line_var)`**。
- v6 最终版（本地 `aliyun_h3/setup_h3_pai.sh`）：16 线程分片下载（dp 带分片级重试 3 次 + 已下分片续传）、大小走 modelscope API（`repo/files` 接口 Data.Files[].Size；**CDN resolve 不返回 Content-Range，-r 0-0 只给 content-length:1**）、ComfyUI 升级用 `git fetch origin master && git reset --hard FETCH_HEAD`（浅克隆 pull 会"无法快进"）、[3.5] H3 四件套下完立即启动 ComfyUI（Flux 组后台续下）。
- **速度现实**：PAI 上 modelscope/hf-mirror 单连接均 ~1.2MB/s（测速确认，换源无用）；v4(8线程)实测 3.3MB/s；16 线程可能 1.2-6MB/s 视 CDN 状态。**无官方加速通道**（EAS 模型缓存=推理内存缓存非下载加速；OSS 内网仅限自有 bucket）。接受现实或停实例错峰。
- 模型大小（modelscope API 实测）：fl2va_pruned_int8 20,970,379,616B / nvfp4_awq 15,687,142,551B / video_vae 5,207,808,496B / audio_vae 605,254,808B。

## 4 个工作流已生成（11:0x，`D:\Aicomfyui\aliyun_h3\workflows\`，全部 JSON 合法）
- `wf_01_llm_expand.json`：扩写流。String Literal → LlamaCPPModelLoader(Qwen2.5-14B,qwen2) + LlamaCPPOptions(-1层GPU/4096ctx) + LlamaCPPEngine(system=扩写指令,max400,temp0.7) + LlamaCPPMemoryCleanup + ShowText。节点字段照抄 7-29 已验证 t2i_qwenllm_e2e.json。
- `wf_02_flux_char.json`：角色图流。String Literal(英文提示词) → UnetLoaderGGUF(flux1-dev-Q4_K_S) + DualCLIPLoader(t5xxl_fp8+clip_l,flux) + VAELoader(ae) + EmptyLatentImage(1024²) + CLIPTextEncode×2 + KSampler(25/3.5/euler/simple/1.0) + VAEDecode + SaveImage(char_role)。
- `wf_03_qwen_edit_storyboard.json`：分镜图流（参考锁角色）。UnetLoaderGGUF(qwen-image-edit-2511-Q4_K_M) + **CLIPLoaderGGUF(Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf, type=qwen_image)** + VAELoader(qwen_image_vae) + **ModelSamplingAuraFlow(shift=1.73)** + LoraLoader(multiple-angles,0.9/0) + LoadImage(参考) + TextEncodeQwenImageEditPlus(`<sks>`+方位+identity保持) + VAEEncode(参考图入潜) + KSampler(35/7.5/dpmpp_2m/karras/denoise0.8) + VAEDecode + SaveImage(storyboard)。接线=7-28 已验证 peach_bible_v4（API 格式）转 UI 格式。
- `wf_04a/b/c_h3_*.json`：官方 ComfyUI H3 视频模板（T2V/I2V/R2V）直接复用，模型文件名与我们下载一致。
- 衔接：①扩写→②角色图→③(参考图+分镜词)→分镜图→④I2V(分镜图做首帧)→视频。
- 生成器 `aliyun_h3/gen_workflows.py` 可复用。

## 12:04 止损停实例（CDN 限速 + pip 报错）
- 用户在 12:04 停掉 PAI-DSW 实例（`dsw-bat131d8834b7fggc`）。原因：下载卡死（CDN 限速到 0.25MB/s、part.4/part.6 缺失、mtime 冻结 12:02:58）+ ComfyUI `pip install` 报 `comfyui-frontend-package==1.48.6` 不在 PyPI（超前 pin）。
- 已写恢复清单：`D:\Aicomfyui\aliyun_h3\resume_notes.md`（低峰时段恢复步骤）。
- 待办：深夜/清晨低峰重开实例 → 直接续跑已内置 pip 修复+8 线程的脚本 → 上传 6 工作流 → 验证链。
- 教训固化：① PAI 下载 **8 线程最优(3.3MB/s)**，16 线程负优化(0.4MB/s)；② set -u 下禁止 `local x=$(cmd $同行变量)` / `local x=$((ref 同行变量))`；③ CDN 速度随时段波动大，必须错峰。
- 脚本 v7（本地待写/已规划）：pip pin 自修复 sed + 下载改 8 线程 + 分片按线程数命名(`$o.part.$n.$i`)避免串扰。

## 评估「船长AI视界」技能（12:1x，用户发仓库链接要求学习+分析使用条件）
- 仓库 `zhangxiansheng-888/chuanzhangAIshijie`（MIT）：中文 AI 影视创作方法论 + 5 个 **Codex 技能**（纯提示词/工作流规则，不调 API、不跑代码）。
- 固定 01→02→03→04：故事创作→真人感人像提示词→静态图像提示词→分镜+情绪融合。核心理念：风格母版锁全片、真人感锁身份、情绪写进每镜"表情"字段。
- **关键事实**：技能只产出**文本提示词**，不生成图/视频；分镜技能输出的是 **Seedance（字节）视频提示词格式**，不是 H3。
- 使用条件三档：A 按原意需 OpenAI **Codex 付费订阅**（装 ~/.codex/skills/）；B 贴合现有栈——clone 读 SKILL.md 当提示词模板在 WorkBuddy 用，喂进现有 ComfyUI（Flux/Qwen-Edit/H3），视频提示词需 Seedance→H3 适配（**推荐，零新增成本**）；C self-hosted 网站需 Node22.13+ + ChatGPT Sites + 自带 OpenAI Key。
- 与本项目关系：它是流水线 **①④ 文本侧的高质量增强**（补用户之前 IP-Adapter 锁不住非人类角色、一致性/表情僵硬的坑），**不替代** ②Flux/③Qwen-Edit/⑥H3。
- 待用户拍板：是否把 4 技能转成 WorkBuddy 技能 + 分镜视频提示词改 H3 适配。分析笔记已存 `Downloads/chuanzhang_skill_analysis.md`。
- **12:43 验证转向真人**：用户要求把验证主题从「皮克斯兔子」换成**真人**（主题：江屿，28岁被裁程序员，搬家前最后一夜）。关键变化：换真人后 **02 真人感人像技能可用**（含九宫格多角度锁脸），不再用 03 替代身份控制。全套可粘贴提示词已写 `Downloads/chuanzhang_realperson_prompts.md`（01故事/02单人+九宫格/03角色图三视图/04三镜带表情微表演）。结论仍成立：技能只产文本提示词，不绑模型、不绑 Seedance/Codex，Hy3 即可跑。

## 12:2x 确认 Codex 非必需 + cc-switch 性质澄清
- 用户问"是否一定要用 Codex，要用就用 cc-switch 做中转"。核实结论：**用船长AI视界技能不强制 Codex**——SKILL.md 是纯 LLM 指令文档（无代码/无 API 调用），可移植到任意能遵循指令的 LLM（WorkBuddy/ChatGPT/Claude）。
- cc-switch 实测是 Tauri 桌面应用，统一管理 ClaudeCode/Codex/Gemini 等 CLI 的 **API 中转站 + Skills 一键安装(~/.codex/skills/) + MCP/Prompts 配置**；**不替代 Codex 运行时**，只把 Codex 的 API 请求中继到便宜中转站(DeepSeek/GLM/Qwen/MiniMax)，并支持装 GitHub Skills。用户已有 cc-switch。
- 三条路：A 移植 WorkBuddy(推荐,零新增) / B cc-switch+Codex 中转(用户有 cc-switch 时顺手) / C 纯提示词模板。共同摩擦：04 分镜输出 Seedance 视频提示词格式≠H3，需适配。待用户选路径。
- **12:22 追加确认**：用户截图里的模型列表（Claude/GPT/GLM/Gemini/DeepSeek/Qwen）均可跑这些技能。技能方法论不绑定 Codex，只要求 LLM 能遵循长指令。用作者推荐的“大模型”写提示词 ≠ 必须用 Codex。

## 12:47 已装 WorkBuddy 技能 + 用户自验
- 把船长AI视界 4 生产技能合并为单个 WorkBuddy 技能 `chuanzhang-ai-shijie`，装到 `~/.workbuddy/skills/chuanzhang-ai-shijie/SKILL.md`（frontmatter 含 `agent_created:true`）。内容含 01→04 全流程 + 02真人 + 03中英双语 + 04 六字段(画面动作概述/构图/机位/动作/表情/音效)带表情微表演 + 视频提示词通用平台/H3 适配格式（默认内联表情微表演，附 Seedance 四段原生格式说明）。
- 本地 clone 在 `D:\Aicomfyui\aliyun_h3\chuanzhangAIshijie`（沙箱直连 github 慢，靠 WebFetch 抓原文 + 本地转 LF 校验）；源文件 UTF-8+CRLF，Read 判二进制，已 tr -d '\r' 转存 `Downloads/cz_skill_src/` 供核对。
- 12:48 用 Skill 工具验证加载成功并实跑江屿真人主题产出样稿（02单人+九宫格/03三视图/04三镜）。用户 12:49 起**自行触发技能产出、贴图片/视频平台验证**（不再由我手动跑）。
- 触发语：「用船长AI视界帮我把 XX 写成故事分镜」「船长方法论」。完整流程闭环=技能(Hy3 出文本)→贴平台出图/视频（未来接自己 ComfyUI+H3）。

## 14:27 用户铁律：技能产出不人为限镜数
- 用户要求用「视频制作流」触发时，按故事情节点**完整展开分镜**（如陈默黑客题材约 8–9 镜），**不得人为砍成 3 镜演示版**。
- 镜头数由 01 结构大纲情节点密度决定；单镜 ≤15s 是上限非目标；时长档位按内容类型（闪现1-3s / 简单动作4-8s / 无台词反应5-10s / 完整情绪弧8-15s）。
- 之前给的 3 镜是演示精简，非技能限制。以后默认出完整镜数。

## 14:37 技能补全（关掉 3 镜逃生口 + 嵌入真实镜头数算法）
- 用户要求"把技能搞完整"，并明确：**下次换剧本，不要记住陈默**（每次触发=全新剧本）。
- 已改 `~/.workbuddy/skills/chuanzhang-ai-shijie/SKILL.md` 五处：
  1. 最高规则#2：默认一次性出完整 01→04，**严禁为演示砍成固定 3 镜**（仅用户显式要"样稿"才可精简并标注）。
  2. 最高规则#5（新增）：技能不含任何角色/剧本预设，每次触发从当次输入出发，**不沿用上一次角色/故事（如陈默）**，不保留跨次记忆。
  3. 04「镜头数如何确定」：嵌入源仓库**合并优先**规则（连续地/人/情绪/摄影逻辑→合并；超15s/焦点变/地点硬切/角色进出/关键道具/情绪大转折→拆）+ 时长档位 + 数量估算(≤10s≈1条/10-25s≈2-3条/25-45s≈3-5条) + 少而准。
  4. 04「六道 Gate」改为"时间划分与镜头数"：默认直接出完整分镜，去掉"概念片可简化给样稿"这个被滥用的口子；仅用户要"先给时间划分方案"才先出表。
  5. 02 示例措辞泛化（去掉绑定江屿的"灰卫衣+青影"写为通用"深色卫衣+眼下青影"）。
- 校验：grep 确认"样稿/3 镜/合并优先/不沿用上一次/少而准/真实镜头数"均到位，无跨次角色残留。
- 结论：下次用「视频制作流：新剧本」触发，必出完整真实镜头数，且不会带出陈默。

## 14:51 用户确认文案够用 + DSW 落地映射（实测节点）
- 用户确认「船长技能产出的 01→04 文案够用」，下一步要在 DSW 上用 ComfyUI 出图出视频。已读 `workflows/wf_02_flux_char.json` 与 `wf_04b_h3_i2v.json` 确认节点映射：
- **wf_02（Flux 出角色图）**：节点1 `String Literal`（标题"英文提示词(来自扩写流)"）= 填 02/03 英文提示词；节点6 `CLIPTextEncode` 正提示词接节点1；节点11 `SaveImage` 文件名 `char_role`。双人需跑两次（周野/黎舟各一次），分别改节点1 提示词 + SaveImage 文件名。
- **wf_04b（H3 图生视频）**：`LoadImage`(节点114) 首帧图换成 03 角色图；subgraph 内 `MiniMaxH3ImageToVideo` 的 `prompt` 字段（widgets_values 首段长文本）须填 **H3 英文描述**；`PrimitiveFloat (duration)`(节点111) 设秒数（=2 示例，上限~15s）。
- ⚠️ **04 中文六字段 → H3 英文 prompt 是必须转化**（唯一摩擦点）：H3 的 qwen3vl 文本编码器官方全英文 prompt，且不吃"表情：内部压力5/5"标签——须把六字段压成一段英文画面+动作描述，微表演译成可见动作、音效译成 `Audio:`。转化示例（镜2告警炸开）已给。
- ⚠️ **H3 单条上限≈15s**：04 完整 10 镜不能一次出，须分段（每镜或合并到≤15s 一段）生成后再拼接成片。
- 前置仍待用户重开 DSW + 跑 v7 续下模型（H3 42.8G+Flux 9.7G）+ 上传 6 工作流。v7 脚本在 `Downloads/setup_h3_pai_v7.sh`（已修 pip pin+8线程+分片隔离）。

### 14:5x 技能补强 + 下载成本担忧（用户提问）
- **用户确认 04 分镜原本只有中文六字段、无英文** → 已在技能 `chuanzhang-ai-shijie/SKILL.md` 新增「块 B 英文 H3 Prompt」：每镜双语输出（中文六字段 + 英文 H3 Prompt），翻译铁律（表情三轴→可见动作、音效→`Audio:`、单镜≤15s、双人写各自动作）。以后「视频制作流」触发自动出英文，免手动翻译工序。
- 已把「周野&黎舟」10 镜英文 H3 Prompt 转出存 `Downloads/h3_prompts_zhouye_lizhou.md`（含 03 角色图英文三视图），即升级后技能会自动给的内容。
- **用户担忧重开 DSW 又要重新下载、慢=烧钱**：澄清「停止≠释放」——停止实例保留磁盘，重开是**续下**（v7 跳过已完整文件，只补未完成分片），非从头下。成本缓解待议：① 错峰（深夜/清晨 CDN 最快 3.3MB/s）；② v7 已 8 线程最优；③ 可选先只下 H3(42.8G) 跳过 Flux(9.7G)，图在外平台做、DSW 只跑视频，省 ~9.7G；④ 探究 ModelScope `modelscope` SDK/CLI 是否走阿里内网更快（PAI 与 ModelScope 同属阿里云）。待用户拍板是否改脚本。
- 用户要"写个 json 导入 ComfyUI"：6 个 wf_*.json 已就绪（wf_02 Flux 出图 / wf_04b H3 图生视频为最核心），UI 格式可直接 Load。提示词填法见上条节点映射。

### 15:0x v8 下载脚本改 ModelScope 内网（已落地）
- 用户拍板：**先做 ModelScope 内网下载**。已写 `Downloads/setup_h3_pai_v8.sh`（语法 `bash -n` 通过）。核心改动：下载通道从 v7「公网 CDN 分片 curl」改为「modelscope SDK `snapshot_download`」——PAI-DSW 与 ModelScope 同属阿里云，SDK 自动走 OSS 内网加速，直击 v7 卡速(0.25MB/s)烧钱根因。
- v8 机制：① `pip install -U modelscope` 升级；② `allow_patterns`+`local_dir` 精确落 ComfyUI 对应子目录（diffusion_models/text_encoders/vae/unet）；③ 天然断点续传（已完整文件自动跳过）；④ 保留 pip pin 自修复；⑤ `SKIP_FLUX=1` 环境变量可跳过 Flux 组(省~9.7G)；⑥ H3 四件套下完先启 ComfyUI 再下 Flux；⑦ 清理 v7 公网 `.part` 残留。
- **官方依据**：阿里云 PAI-DSW 文档明确 `snapshot_download`「代码自动选择适当下载地址」，内网 pip 镜像实测 100+MB/s（文档样例），OSS 内网同理应大幅快于公网 CDN。
- 上机步骤：重开实例(勿释放) → 粘 v8 到 `/mnt/workspace/setup.sh` → `SKIP_FLUX=1 bash /mnt/workspace/setup.sh`（建议先只下 H3 验证速率）→ 上传 6 个 wf_*.json 到 `/root/ComfyUI/user/default/workflows/`。
- **首跑必验**：看日志下载速率是否达内网水平（应远快于公网 0.25MB/s）；若仍慢，查实例 region 与 OSS region、或 `MODELSCOPE_ENDPOINT`。
- A10 FP4 提示：H3 文本编码器默认 `nvfp4_awq` 在 A10 可能报错，预案换同仓库 `int8_convrot` 版（更大但软件可解量化）。脚本末尾已注释。

### 15:2x 用户重开 DSW，开始续下
- 用户说「dsw开了」。下一步：把 v8 全文粘到 `/mnt/workspace/setup.sh` → `SKIP_FLUX=1 bash /mnt/workspace/setup.sh` 后台跑、先只下 H3 验证内网速率（省~9.7G、更快出视频结果）。H3 下完脚本自动启 ComfyUI。
- 监控：`tail -f /tmp/setup_h3_pai.log`；速率看 modelscope 进度。若仍 K/s 级，停、查 `MODELSCOPE_ENDPOINT`/region 同区。
- 等 H3 就绪后传 6 个 wf_*.json 到 `/root/ComfyUI/user/default/workflows/`，用 `wf_04b_h3_i2v.json` + `Downloads/h3_prompts_zhouye_lizhou.md` 的英文块出视频。

### 15:36 用户跑 v8 后 tail 报「没有那个文件或目录」
- 非脚本崩溃，是**时序竞态**：日志 `/tmp/setup_h3_pai.log` 在第 12 行 `exec > >(tee -a "$LOG")` 才创建，而用户把 `nohup … &` 与 `tail -f` 写在同一行，tail 跑太早文件尚未生成就报错退出。
- 诊断命令：`ps aux | grep -E 'setup_h3|msdl.py|main.py'`（看进程在否）+ `ls -la /tmp/setup_h3_pai.log`（看日志现在在否）+ `tail -n 40 /tmp/setup_h3_pai.log`。
- 经验固化：**v8 的 tail 不要与 nohup 同行**，分两行或先 `sleep 3`；进程在+日志已生成就 `tail -f` 接着看，重点盯 `[dl] Comfy-Org/MiniMax-H3` 速率。

### 15:41 真因：磁盘 100% 写满（非 tail 竞态）
- 用户再贴完整日志，根因是 **`overlay 98G 98G 0 100% /` 磁盘满**：`git fetch` 写 shallow.lock 报「设备上没有空间」、`sed` flush 失败、`[dl] Comfy-Org/MiniMax-H3` 下载因无空间中断、ComfyUI 最终 `curl 000` 没起来。H3 未下成（fl2va 仅 250M 残缺、text_encoders 空、无 H3 vae）。复用模型（qwen-edit/LLM/clip/LoRA）均 `[ok]` 存活。
- **隐藏坑（致命）**：v8 `msdl.py` 原 `local_dir_use_symlink=False` → modelscope 先下缓存再**复制**到 ComfyUI，H3 峰值需 2×42.8G≈85G；清完盘也只有 ~49G，必装不下。已改本地 `Downloads/setup_h3_pai_v8.sh` 为 `local_dir_use_symlink=True`（1 倍空间），并给 DSW 上传版同 sed 补丁。
- **清理方案（用户先前确认的删留清单）**：`rm -rf /mnt/workspace/ai-comfyui`(41G) + `rm -rf /root/ComfyUI/models/checkpoints/zero123`(8G) + 删 250M 残缺 fl2va + 清 .part/.tmp + 删 `.git/shallow.lock`。释放 ~49G，symlink 模式够装 H3(42.8G) 留 ~6G。
- 待用户跑清理后贴 `df -h /`；若空闲 <45G 则临时删 qwen-edit(13G)/LLM(8.6G)（仅图片侧用，H3 视频暂不需要，后可同脚本重下）。删完重跑 `SKIP_FLUX=1 bash setup_h3_pai_v8.sh`。
- 教训：PAI-DSW 系统盘 98G 极易写满（旧下载残留+ComfyUI 46G+ai-comfyui 41G）；**任何下载/升级脚本前必须先 df 确认余量**，且 modelscope 落地务必用 symlink 避免 2 倍放大。

### 15:54 du 诊断：H3 已下半截，fl2va 完整但在错路径
- `du -sh /root/ComfyUI/models/*` 揭示真实占用：**fl2va 20G（≈完整20.97GB）躺在 `/root/ComfyUI/models/` 顶层错路径**（v6/v7 curl 残留，ComfyUI 默认去 diffusion_models/ 找）；text_encoder `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` 仅 6.9G 残缺也在顶层错路径；vae/ 只有 qwen_image_vae，H3 的 video_vae+audio_vae 未下。`ai-comfyui` 已不在（早清过）。盘满=H3 半截+旧模型(qwen-edit13G/LLM8.4G/clip5.7G)堆满。
- 结论：fl2va 不用重下（搬对位置复用），只差 text_encoder 补全15.7G+两vae5.8G≈21.5G。需腾≥22G。
- 清理方案（用户已确认图片侧可删）：`mv` 顶层20G fl2va→diffusion_models/（先删该目录250M残缺）；`rm -f` 顶层6.9G残缺text_encoder；`rm -rf unet`(13G)+`rm -rf LLM`(8.4G)；清 `.git/shallow.lock`+`.part/.tmp`。保留 clip/loras/qwen_image_vae。**预期释放 ~28G，塞进21.5G H3剩余+~6G余量**。
- 验证前置：`stat -c %s` fl2va 应=20970379616（完整则 v8 skip 重下）；`df -h /` 释放后空闲需≥24G 才重跑 `SKIP_FLUX=1 bash setup_h3_pai_v8.sh`。
- ⚠️ **A10 FP4 硬伤**：nvfp4_awq 文本编码器 A10(Ampere) 无原生 FP4，需软件解量化；若报错，备选 int8_convrot(27G) 在本98G盘与 fl2va+vae 共存放不下→须换大盘或再腾空间。本次先验证 nvfp4 能否在 A10 加载。
- modelscope 缓存 `~/.cache/modelscope` 当前为空（du 无输出），说明下载直写 local_dir，symlink 补丁更稳（避免缓存+local 双份）。

### 16:11 文生图侧空间账（用户问占用）
- 文生图三环节模型大小：① 扩写 Qwen2.5-14B Q4_K_M ≈8.4G；② Flux 角色图 flux1-dev Q4_K_S(6.7)+t5xxl_fp8(2.5)+clip_l(0.24)+ae(0.3)≈9.7G；③ Qwen-Edit qwen-image-edit-2511 Q4_K_M unet(13)+Qwen2.5-VL-7B clip(5.7)+qwen_image_vae(0.24)+LoRA(0.3)≈19.2G。
- 完整文生图总占用 ≈37G；**当前缺≈31G**（clip/vae/LoRA 壳已留，只需补 LLM8.4+Flux9.7+Qwen-Edit unet13）。
- 盘现实：98G 盘下完 H3(42.5G) 后仅剩 ~6.8G 空闲 → 文生图(31G)与 H3 互斥，本机只能二选一或换 200G 大盘。印证「DSW 只跑视频、文生图放外平台」是被盘容量逼的，非单纯偏好。

### 16:14 用户最终拍板：DSW 只做图生视频（I2V），文生图走外平台
- 用户明确："那就这样吧，只实现视频生成，图生视频"。**最终定位确认**：DSW 纯 I2V/R2V 视频工厂，角色图/分镜图由外平台（CloudBase 生图等）产出后传 DSW 当 H3 首帧。文生图三环节（Flux 角色图 / Qwen-Edit 分镜图 / 14B 扩写）全部放弃本机部署。
- 推论：删 `unet`(qwen-edit 13G) + `LLM`(14B 8.4G) 是**最终决定、不再重下**（clip/loras/qwen_image_vae 这几个壳留着无害，仅占几 G，留待将来扩盘恢复）。Flux 组也永不再下（SKIP_FLUX=1 永久）。
- 落地动作（待用户执行）：A) sed 给 v8 打 `local_dir_use_symlink=True` 补丁（防 2 倍空间）；B) `stat` 校验 fl2va 字节=20970379616（完整则 v8 skip 重下）；C) `mv` 顶层20G fl2va→diffusion_models/；D) rm 顶层6.9G 残缺 text_encoder；E) rm -rf unet+LLM；F) 清 .git/shallow.lock+.part/.tmp；最后 `df -h /` 确认空闲≥24G。
- 重跑：`cd /mnt/workspace && SKIP_FLUX=1 nohup bash setup_h3_pai_v8.sh >/dev/null 2>&1 & sleep 3; tail -f /tmp/setup_h3_pai.log`。核心验收：**nvfp4_awq 文本编码器能否在 A10 加载**（不能则换 int8_convrot 27G，但本盘放不下→须换大盘）。
- 视频链路闭环后：外平台出图 → DSW 上传 `wf_04b_h3_i2v.json` + 填英文 prompt（来自 `Downloads/h3_prompts_zhouye_lizhou.md`）→ H3 出≤15s 视频段 → 拼接。

### 16:18 用户决定：开 2 个 DSW 实例，文生图与图生视频分离
- 用户发截图确认 PAI-DSW **可同时启动多个实例**，资源包按账户级时长+规格累加抵扣，不因实例数量被禁。
- **最终架构调整**：
  - **实例 A（当前 `dsw-823428`）**：纯 H3 图生视频工厂，彻底放弃本机文生图，大胆删 `unet`/`LLM` 腾空间给 H3。
  - **实例 B（新实例）**：纯文生图工厂（Flux 角色图 + Qwen-Edit 分镜图 + 14B 扩写），独立 100G 系统盘，无需考虑 H3 占用。
- 优势：避免 98G 单盘二选一；当前实例已下到半截的 H3（fl2va 20G 完整）可复用；新实例文生图栈 ~37G 单独放得下。
- 成本：两实例同时运行按各自运行时长累加扣资源包，用完即停最省。
- 待交付：当前实例继续执行 A-F 清理→重跑 v8；新实例等开好后，写一个文生图专用安装脚本（不下 H3，只下 LLM+Flux+Qwen-Edit 三件套）。
- **硬件规格（用户 16:20 补充）**：
  - 图生视频实例 = **A10 24G**（当前 dsw-823428，H3 路线不变）。
  - 文生图实例 = **24G 显存**（用户 16:35 更正：之前说的 16G 有误，实际也是 24G，与视频实例同规格）。
  - **24G 文生图选型（用户 16:35 更正后）**：显存足够，原完整方案直接跑，无需 Flux+IP-Adapter 妥协——Flux 角色图(~10G) + Qwen-Edit qwen-image-edit-2511 Q4_K_M(13G)+VL-7B clip(5.7G)=18.7G(<24G ✅) + 14B 扩写(CPU)。文生图栈 ~37G，24G 实例 100G 盘容得下。实例 B 脚本按完整方案写（下 LLM+Flux+Qwen-Edit 三件套）。

### 16:48 视频实例 H3 未完整 + 根因（v8 modelscope 路径 bug）
- 用户贴 [3.5] DONE，但 [5/6] 清单暴露：diffusion_models 仅 fl2va 20G；`text_encoders` 空（仅占位）；`vae` 仅 qwen_image_vae（无 H3 双 vae）；overlay 100% 满。ComfyUI 起了但 H3 缺 text_encoder+双vae，**跑视频必报错**。`[3.5] H3 四件套完成` 是误判（脚本未校验文件实际落地大小）。
- **根因（du 诊断）**：`/root/ComfyUI/models/` 顶层有**两份错路径文件**——`minimax_h3_fl2va...safetensors` 20G（重复，diffusion_models 已有完整版）+ `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` 8.3G（残缺，应 15.7G）。v8 的 `snapshot_download` `allow_patterns` 未带仓库子目录前缀 + `local_dir=/root/ComfyUI/models`，导致文件落 local_dir 根而非 `text_encoders/`/`vae/`，且 fl2va 重复下（本地 diffusion_models 已有实体但 modelscope 不认，重下到根）。98G 被双份 fl2va+残缺 text_encoder 吃满。
- **修复（手动绕过 v8 bug）**：① 删顶层 20G 重复 fl2va + 8.3G 残缺 text_encoder + clip(5.7G)+loras(0.28G)+qwen_image_vae(0.24G) 壳 → 腾 ~34G；② 手动 `snapshot_download` 带子目录前缀（`text_encoders/...`、`vae/...`）下到正确子目录；③ 验证三目录齐全；④ 手动起 ComfyUI。
- **v8 脚本 bug 待修**：msdl.py 的 allow_patterns 必须含 `diffusion_models/`/`text_encoders/`/`vae/` 前缀且 local_dir=/root/ComfyUI/models，且需校验文件大小≠占位才标完成。本地 `Downloads/setup_h3_pai_v8.sh` 待改供新视频实例用。
- 教训：modelscope `allow_patterns` 不含子目录前缀→文件落 local_dir 根；脚本必须校验落地大小，不能只看"下载完成"日志。

### 16:26 实例 A 清理执行结果（关键坑）
- 用户跑 A-F：fl2va `stat`=**20970379616 完整**✓（免重下那 20G）；清理生效，系统盘 `overlay 98G 71G 28G 72%`（空闲 28G，够装 H3 剩余 21.5G）。
- **sed 补丁失败**：`sed: 无法将 89 个项目写入 /mnt/workspace/sedidVldS：设备上没有空间` → `/mnt/workspace` 是**独立挂载盘且已满**，sed 临时文件写那失败；grep 第 65 行仍 `local_dir_use_symlink=False`（未改成功）。
- **修复**：用 `TMPDIR=/tmp sed -i ...`（临时文件改落系统盘 /tmp，有 28G）；再 `grep` 确认变 True。若不灵改用 python 改写或把脚本 cp 到 /tmp 再改。
- 风险：若 symlink 不改成 True，modelscope 下缓存+复制 2 倍 → H3 需 43G > 28G 装不下。必须修。
- 下载目标 `/root/ComfyUI/models`（系统盘）有 28G ✓；/mnt/workspace 满只影响脚本临时写，不影响模型落地。

### 16:5x 致命坑：PAI-DSW 的 modelscope 版本过旧，`local_dir_use_symlink` 参数根本不存在
- 用户跑手动补全脚本 `snapshot_download(..., local_dir_use_symlink=True)` 直接报 `TypeError: got an unexpected keyword argument 'local_dir_use_symlink'` → **当前实例 modelscope 版本太旧，不支持该参数**（v8 之前"能下"是靠 `False` 默认值，sed 补丁改 `True` 反而踩雷）。
- **通用 workaround（兼容任意版本）**：不用 symlink 参数，改为「先下到 modelscope 缓存 → 再 `shutil.move` 到正确子目录」。move 在同文件系统(/root 下)是 rename，不占双份空间；峰值仅=下载量(21.5G)，28G 空闲装得下。
  - 脚本：`snapshot_download(repo, allow_patterns=[文件列表], revision="master")` 返回缓存路径 → `os.walk` 找文件 → `shutil.move(缓存路径, /root/ComfyUI/models/<子目录>/)`。
  - 注意：allow_patterns 必须带 `text_encoders/` `vae/` 子目录前缀，否则落 local_dir 根（v8 的 bug 根因）。
- **v8 脚本必须改两点才能复用于新视频实例**：① allow_patterns 加子目录前缀 + local_dir=/root/ComfyUI/models；② 把 `local_dir_use_symlink=True` 整行删掉（旧版本不支持）；③ 下载后校验文件字节≠占位(0 字节)再标完成。本地 `Downloads/setup_h3_pai_v8.sh` 待改。
- 当前进度：用户正在跑 move 法补全 text_encoder(15.7G)+双vae(5.8G)；跑完验证 `text_encoders/`+`vae/`+`diffusion_models/` 三件套齐全 + 手动起 ComfyUI(curl 8188=200) 即 H3 就绪。

## 2026-08-06
### 2026-08-06 工作日志（续 H3 视频实例排障）

## 视频实例（dsw-823428）ComfyUI 起不来的真因：numpy 被升到 2.x
- 用户贴 `/tmp/comfy_run.log` 诊断：进程 `main.py` 在（PID 5665），但 `curl 8188` 返回 000。
- **根因**：`AttributeError: _ARRAY_API not found` + `ImportError: numpy.core.multiarray failed to import`。日志自述「A module that was compiled using NumPy 1.x cannot be run in NumPy 2」「downgrade to 'numpy<2'」。
- **触发链**：v8 脚本里 `pip install -U modelscope`（或 pip 修复步骤）把 `numpy` 顶到 **2.x**，而 ComfyUI 的 `cv2`(OpenCV) 及 `ComfyUI-GGUF`/`ComfyUI-Easy-Use`/`KJNodes` 等编译节点按 numpy 1.x 编，导入 cv2 即崩 → 节点 IMPORT FAILED → 服务起不稳（curl 000）。
- **修复（已给命令，待用户执行）**：
  ```bash
  pkill -f main.py; sleep 3
  pip install "numpy<2" --root-user-action=ignore
  python3 -c "import cv2, numpy; print(cv2.__version__, numpy.__version__)"  # 须 numpy 1.x
  cd /root/ComfyUI && nohup python3 main.py --port 8188 --listen 0.0.0.0 >/tmp/comfy_run.log 2>&1 &
  sleep 25; curl -s -o /dev/null -w "HTTP: %{http_code}\n" http://localhost:8188   # 期望 200
  ```
- **H3 文件状态已确认 100% 完整**（无需再下）：fl2va 20,970,379,616B（diffusion_models/）、text_encoder 15,687,142,551B（text_encoders/）、video_vae 5,207,808,496B + audio_vae 605,254,808B（vae/）。之前误判"缺件/下到错路径"是磁盘 100% 时 `du` 看花眼，实际早已落对目录。
- **关键复用经验**：v8 脚本必须锁 `numpy<2`（在 install 段加 `pip install "numpy<2"` 或 pin），否则重跑必再触发 cv2 崩溃。 modelscope 升级不应带 numpy 升级。
- A10 FP4：nvfp4_awq 文本编码器能否在 A10 加载待 ComfyUI 起来后实测（目前日志未到模型加载，先过 numpy 关）。

## 下一步（视频实例）
- **✅ 已修复验证通过**（09:58）：`numpy 1.26.4` + `cv2 4.9.0` 正常，`curl 8188 → 200`，`grep -c "IMPORT FAILED" /tmp/comfy_run.log = 0`。**视频工厂正式就绪。**
- 下一步：上传 `wf_04*.json`（来自 `D:\Aicomfyui\aliyun_h3\workflows\`）到 `/root/ComfyUI/user/default/workflows/`；**建议先传 wf_04a (T2V) 用 `h3_prompts_zhouye_lizhou.md` 某镜头英文 prompt 验证 H3 在 A10 能否出视频**（重点看 nvfp4 文本编码器是否加载成功、有无 FP4 不兼容报错），确认链路通后再用 wf_04b (I2V) 配合文生图实例首帧出"周野&黎舟"10 镜。
- 文生图实例（实例 B，24G）待开，需另写 `setup_img_pai.sh`（只下 LLM+Flux+Qwen-Edit，绝不下 H3，且锁 numpy<2）。

## 视频实例 T2V 验证已启动（~10:40）
- 用户已在 ComfyUI 网页 Load `wf_04a_h3_t2v.json`，`MiniMaxH3ImageToVideo` 节点填入 Shot1 英文 prompt（两个亚洲男安全工程师 SOC 室），`Float(duration)`=6，点 Queue Prompt；队列 1 运行 2 排队。该工作流 first_frame/last_frame 无图输入 → 实为纯 T2V（不需传图）。
- **目的**：验证 A10 对 nvfp4_awq 文本编码器的 FP4 兼容性。跑完出视频=链路通；报 FP4 不兼容=需换 int8_convrot（27G 本盘放不下，需腾空间/换大盘）。等用户贴结果。

## 生图实例（实例 B，24G）脚本已就绪
- `setup_img_pai.sh` 已生成存 `C:\Users\Administrator\Downloads\setup_img_pai.sh`：锁 numpy<2（避坑）、modelscope 内网 OSS 下生图三件套（Flux 组用 v8 已验证的 AI-ModelScope 三仓库；Qwen2.5-14B/ Qwen-Image-Edit/ VL/ LoRA 用推测 repo + 容错）、起 ComfyUI。
- 生图实例开好后的流程：① 上传跑 `setup_img_pai.sh`；② 传 `wf_01`(扩写)/`wf_02`(Flux角色图)/`wf_03`(Qwen-Edit角度) 工作流；③ 用 `Downloads/h3_prompts_zhouye_lizhou.md` 末尾「03 角色图英文提示词」让 Flux 出周野/黎舟首帧 → 传回视频实例当 wf_04b 首帧出视频。
- 风险点：Flux 源已验证；Qwen 系列 repo 为推测，若 [WARN] 失败需看日志改路径重下该项。

## T2V 验证结果更新（~11:07）
- 工作流已成功传到正确目录：`/root/ComfyUI/user/default/workflows/` 含 `wf_04a_h3_t2v.json` + `wf_04b_h3_i2v.json`（外加旧 `t2i_qwenllm_e2e.json`）。
- **✅ A10 FP4 隐患已排除**：日志显示 `Native ops: convrot_w4a4, int8_tensorwise , emulated ops: mxfp8, float8_e4m3fn, float8_e5m2, nvfp4` → nvfp4 走 **emulated（软件模拟）** 加载，A10 无原生 FP4 但能跑。采样 `100%|20/20 [11:44]` 完成无崩溃。
- ⚠️ 完整出视频文件未确认：`output/` 无新 mp4/webm。原因：采样 100% 后进入 VAE decode（AudioVAE/VideoVAE 加载），**尚未保存时被用户 `pkill`+`^C` 中断**（用户重跑修复命令把进程杀了）。另：用户点了 3 次 Queue（队列堆 3 个），下次只点 1 次。
- 下一步：重启 ComfyUI → 重连 → 重新 Load wf_04a → 填 Shot1 prompt + duration=6 → 只点 1 次 Queue → 等完整跑完（含 VAE decode+保存）看 output 出新视频。生图实例 setup_img_pai.sh 仍在跑（~37G 下载中），别动。
- 结论：**H3 在 A10 上模型加载+采样均通过，仅待一次完整出片确认保存**。不用换 int8_convrot。

## 首产物复盘：423K/5s、双人画面，H3 T2V 链路已完全跑通（~11:31–11:45 确认）
- 用户贴诊断：`find /root/ComfyUI -mmin -15` 命中 `/root/ComfyUI/output/video/MiniMax_H3_00001_.mp4` → **视频真实落点确认 = output/video/ 子目录**（不是 output 根）。之前"全盘 find 没找到"是用户粘贴命令时混入 `$` 符号导致第一个 find 语法错乱静默失败，非未生成。
- 文件大小：DSW 上 423K，下载到本地 432,675 bytes；ComfyUI 预览显示 `0:00/0:05`、762.8K（预览缓冲大小）。能完整播放 5 秒且有清晰画面，**排除完全截断**；423K 偏小的主因是 **wf_04a 分辨率选择器档位太低**（左下角表格 0.2→608×352、0.3→768×416、0.4→960×544、0.5→1280×?），若当前选 0.2/0.3 则文件小合理。
- ✅ **用户确认画面是两人并排**（之前基于截图误判为"单人"，实为 ComfyUI 预览只显示了左边视频区域，右边人没显示出来）。→ **H3 T2V 对多主体/构图遵循正常，prompt 完全生效**。
- **里程碑达成：H3 在 A10 上模型加载+采样+保存全链路跑通**（nvfp4 emulated 兼容 + 采样 20/20 + VAE 解码出可播放双人 mp4）。FP4 不兼容顾虑已排除，无需换 int8_convrot。
- 后续路线：
  1. **提分辨率再抽 T2V**：把分辨率选择器提到 0.4/0.5 让画质/文件大小正常，换 seed 多抽即可（双人遵循已验证 OK）；
  2. **角色一致性考虑 I2V**：T2V 每次长相随机，若"周野&黎舟"需固定长相，等生图实例跑通后用 Flux 出明确双人首帧，传回视频实例用 `wf_04b_h3_i2v.json` 做图生视频锁定角色。
- **生图实例 setup_img_pai.sh 已跑（~11:59 验收，实例 dsw-831216）**：
  - ✅ numpy 1.26.4 | cv2 4.12.0（锁成功）；DSW 默认 python3.11，未踩 3.8 set[str] 坑。
  - ✅ Flux 全套到位：unet/flux1-dev-Q4_K_S.gguf(6.4G) + text_encoders/t5xxl_fp8_e4m3fn(4.6G)+clip_l(235M) + vae/ae.safetensors(320M)。
  - ✅ Qwen2.5-14B 扩写(LLM/) 8.4G 三片到位。
  - ⚠️ city96/Qwen-Image-Edit-2511-GGUF → **404 不存在**（modelscope 上该 repo 猜错路径）；且脚本回退逻辑 bug（except TypeError 内再抛 NotExistError 未捕获）致 imgdl.py 崩，**后续 Qwen2.5-VL-7B 与 Multiple-Angles-LoRA 未下**。
  - ⚠️ ComfyUI HTTP: 000（首次加载 Flux 大模型，15s 明显不足）；IMPORT FAILED 数=0 不可靠（日志未打印完）。需 sleep 后再 curl + tail /tmp/comfy_run.log 确认。
  - **结论：出双人首帧所需 Flux 全齐，核心生图能力已就绪**；Qwen-Image-Edit 仅 wf_03 角度图用，当前出首帧不需要。待 ComfyUI 起来即可传 wf_02 出图。
  - ❌ **ComfyUI HTTP 000 真因**：`python3: can't open file '/root/ComfyUI/main.py': No such file` → **生图实例上根本没有 ComfyUI 代码**！setup_img_pai.sh 只下载了模型（mkdir 创建了 /root/ComfyUI/models/），但**遗漏了克隆 ComfyUI 本身**。两实例文件系统独立，视频实例的 ComfyUI 不会自动带过来。这是脚本遗漏（缺 git clone ComfyUI 步骤）。
  - **补装方案**：① `cd /root && git clone https://github.com/comfyanonymous/ComfyUI.git`（github 慢则换 gitee 镜像 `https://gitee.com/mirrors/ComfyUI.git`）；② `pip install -r requirements.txt --root-user-action=ignore` + 锁 numpy<2；③ `custom_nodes` 下 `git clone https://github.com/city96/ComfyUI-GGUF.git`（Flux GGUF 必需）+ 装其 requirements；④ 起服务看 IMPORT FAILED 补其他节点（wf_01 扩写需 comfyui-sg-llama-cpp 等 LLM 节点）。
  - 待办：① 克隆 ComfyUI 补装后重起确认 200；② 修 setup_img_pai.sh（加克隆 ComfyUI+节点步骤）供未来复用；③ 修 Qwen-Image-Edit 正确 repo + 脚本回退 bug（若后续要 wf_03 角度图）。
  - **用户已把工作流传到 /mnt/workspace/**：`wf_01_llm_expand.json`(扩写)、`wf_02_flux_char.json`(Flux角色图)、`wf_03_qwen_edit_storyboard.json`(角度图) 都在，无需再传。ComfyUI 起后需 `cp /mnt/workspace/wf_*.json /root/ComfyUI/user/default/workflows/`（或网页直接 Load 该路径）。
  - **克隆被挡（~12:11）**：用户直接 `git clone .../ComfyUI.git /root` 报 `fatal: 目标路径 'ComfyUI' 已经存在，并且不是一个空目录` → 因 setup_img_pai.sh 的 `mkdir -p /root/ComfyUI/models/...` 已建出**只有 models/ 的空壳目录**，挡住了 git clone。正确修复：① `mv /root/ComfyUI /root/ComfyUI_data`（保留 37G 模型）；② `git clone .../ComfyUI.git /root/ComfyUI`；③ `rm -rf /root/ComfyUI/models && mv /root/ComfyUI_data/models /root/ComfyUI/models`（同盘 mv 瞬时）；④ `[ -d /root/ComfyUI_data/user ] && cp -rn /root/ComfyUI_data/user/. /root/ComfyUI/user/`；⑤ `ls /root/ComfyUI/main.py` 确认源码就位。待用户执行贴结果。
  - **官方确认（~12:13）**：阿里云官方客服确认 **PAI-DSW 实例默认不预装 ComfyUI**，建议"PAI-EAS ComfyUI 预置镜像"或"手动安装"。我评估后结论：EAS 镜像路线需重挂/重下已就位的 37G 模型，多此一举；**当前实例手动 `git clone` 源码 + 装依赖最省事、零重下**，与官方"手动安装"建议一致，路线正确无需改。可写进 setup_img_pai.sh 复用（脚本须补 `git clone ComfyUI` + 节点安装步骤，避免下次再踩空壳目录挡 clone）。
  - **✅ 克隆成功（~12:15）**：`mv 空壳→ComfyUI_data` + `git clone .../ComfyUI.git /root/ComfyUI`(85MB, 1.15MB/s) + `mv 模型回来` 全部完成，`ls /root/ComfyUI/main.py` 显示 25K 源码就位。下一步：装 requirements + 锁 numpy<2 + 装 ComfyUI-GGUF 节点 + 起服务看 200。待用户跑依赖段落贴结果。
  - **新阻塞（~12:28）：ComfyUI 起服务崩溃，`AttributeError: module 'torch.library' has no attribute 'custom_op'`**。调用链：`comfy/quant_ops.py` → `comfy_kitchen` → `backends/eager/adaln.py` 第 28 行 `@torch.library.custom_op(...)`。`torch.library.custom_op` 是 PyTorch 2.4+ 才引入的 API，说明生图实例 DSW 镜像预装的 torch 版本过低，与最新 ComfyUI 不兼容。需确认 torch/cuda 版本后升级 torch（或用兼容旧 torch 的 ComfyUI commit）。HTTP 000 即因此崩溃，不是模型没加载完。
  - **✅ 版本确认（~12:30）**：`torch: 2.3.1+cu121`，`cuda: 12.1`（驱动 550.163.01 支持 12.4，A10 24G）。→ 需升级到 **torch 2.4.1+cu121** 才有 `torch.library.custom_op`。升级后须重 `pip install "numpy<2"`（防 torch 把 numpy 带上 2.x）再起服务。旧进程 PID 114145 已崩死，升级后直接重起 main.py 即可。
  - **升级踩坑（~13:37）**：官方 `--index-url https://download.pytorch.org/whl/cu121` 在 DSW 仅 ~100KB/s 且 **哈希校验失败**（`Expected sha256 ≠ Got`，R2 CDN 给出损坏包）。**改用阿里云内网镜像 find-links**：`pip install torch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1 -f https://mirrors.aliyun.com/pytorch-wheels/cu121/ --no-cache-dir --root-user-action=ignore`（用 `-f` 非 `--index-url`；`--no-cache-dir` 清掉损坏缓存碎片）。numpy 仍 1.26.4 满足。待跑升级+重起验证 200。
  - **✅ 生图实例 ComfyUI 正式就绪（~14:08）**：`pip install torch==2.4.1+cu121`（阿里云镜像成功）→ `nohup python3 main.py --listen 0.0.0.0 --port 8188` → `ComfyUI HTTP: 200`。日志干净：`ComfyUI-GGUF` 加载成功、`[INFO] Starting server`、`To see the GUI go to: http://0.0.0.0:8188`，**无 IMPORT FAILED**。torch 2.4.1+cu121 / numpy 1.26.4 / cuda 12.1。→ 生图实例可正式出图。下一步：复制 `wf_02_flux_char.json` 到 `user/default/workflows/` 或直接网页 Load `/mnt/workspace/wf_02_flux_char.json`，用角色图英文提示词出"周野&黎舟"双人首帧。
  - **wf_02 加载报缺节点（~14:29）**：网页提示"请安装缺失的包以使用此工作流"。**根因**：wf_02 用了 `String Literal` 节点（节点1/7 填正/负提示词），该节点由 **ComfyUI-Manager** 提供，当前未装。修复：clone ComfyUI-Manager 到 custom_nodes + 重启 ComfyUI（默认已启用 manager；如需显式可加 `--enable-manager`）。装 manager 后网页可一键安装后续 wf_01(LLM节点)/wf_03(Qwen-Edit) 的缺失节点。
  - **String Literal 缺失的彻底解决（~14:56）**：装 ComfyUI-Manager + git pull 升级 + ComfyUI-Custom-Scripts 后，**Manager 仍报 String Literal 缺失**（4.2.1 版本校验仍不过）。最优解=**改工作流去依赖**：本地 `D:\Aicomfyui\aliyun_h3\workflows\wf_02_flux_char.json` 已重写——删除节点1/7(String Literal 正/负提示词)、把文本直接写进节点6/8(CLIPTextEncode 的 widgets_values)、断开 link 1/8。重传实例后 Load 不再报缺失。
  - **wf_02 Queue Prompt 报错（~15:08）**：KSampler 提示"输入超出范围 / 无效输入"，截图显示 `steps=NaN / cfg=0`。根因=原文件 `widgets_values` 顺序写错：`[25, 3.5, 0, "euler", "simple", 1.0]` 把 steps 填成 3.5、cfg 填成 0。已修正为 `[25, "fixed", 20, 3.5, "euler", "simple", 1.0]`（seed=25, control_after_generate=fixed, steps=20, cfg=3.5, sampler=euler, scheduler=simple, denoise=1.0）。重新上传实例后再 Queue 即可。
  - ✅ **经验**：ComfyUI 新版 KSampler 有 7 个参数（seed / control_after_generate / steps / cfg / sampler_name / scheduler / denoise），旧 6 值模板会因字段错位导致 steps/cfg 变 NaN。工作流模板需要按当前 ComfyUI 版本调整 widgets_values 长度；String Literal 节点可替换为"直接在 CLIPTextEncode 文本框输入"。后续 wf_01/wf_03 若也用 String Literal，同样手法去依赖即可。
  - **首帧图偏卡通插画风（~15:40）**：wf_02 第三次出图人物明显迪士尼/插画化（皮肤光滑、眼睛超超大、笑容商业化）。根因① 采样截图显示 **cfg=3.5, steps=20**——实例上跑的仍是 KSampler 6→7 参数版（[25, fixed, 20, 3.5, euler, simple, 1.0]），cfg=1.0/steps=25 的最新版没上传；② 之前船长AI视界版 prompt 含 **big eyes / eyes sparkling / adorable** 这类亚洲动漫化词，Flux 见到直接往插画风靠。已修正 wf_02 文件（本地）：prompt 改成纪录片电影感 `Cinematic still from a documentary-style film, candid photojournalistic composition, shot on 35mm film with Kodak Portra 400 color grade`，去掉 big eyes/sparkling/bucktooth smile，加 `natural proportional eyes / natural proportional almond eyes / candid natural expressions`；负提示词加 `cartoon, anime, illustration, drawing, doll, kawaii, chibi, 3d render, CGI, plastic skin, stylized, oversaturated, exaggerated eyes, glitter, sparkles`；KSampler 保持 steps=25, cfg=1.0。让用户重传文件刷新加载。**注意**：用户很可能在 ComfyUI 网页里手动改了节点文本（绕过文件上传），导致文件与实例不一致——以后改 wf_02 需提醒用户"文件改了，DSW 文件浏览器删旧传新+网页 F5+重 Load"，不能只在网页上点节点改。
  - **换剧情（~15:34）**：用户放弃 SOC 双人场景，改用 **`chuanzhang-ai-shijie`（船长AI视界）技能**做新故事《两个小朋友去买冰淇淋，顺便拯救世界》。角色：阿乐(8岁男孩,黄T恤背带裤)+果果(7岁半,齐刘海圆眼镜蓝裙)；8 镜 90s 概念片（冰淇淋店=银河甜品护卫队前哨、老彭被焦糖光卷走、银河搅拌勺修好融化射线）。产出 01故事→02真人写真→03中英双语图像提示词→04分镜+英文H3 Prompt。03 双人同框首帧图供 Flux(wf_02) 出图、04 块 B 英文 prompt 直接贴 H3 MiniMaxH3ImageToVideo。文本产物见会话回复。
  - **✅ 首帧出图成功（~15:44）**：用户反馈"这张看着还行"——电影感 prompt + 防卡通负面词 + cfg=1.0/steps=25 组合生效，Flux 出写实双小孩图。**Flux 写实出图配方定型**：纪录片电影感 prompt（candid/35mm/Kodak Portra 400）+ 负面词压 cartoon/anime + KSampler cfg=1.0 steps=25。下一步：把该首帧图从生图实例传到视频实例，用 `wf_04b_h3_i2v.json` 做图生视频（I2V）。
  - **首帧图规划（~15:46）**：8 镜无纯单人镜头，**双人同框首帧已够覆盖全部镜头**。补充可选：①老彭单人柜台后（镜2/镜7 开场用，prompt 已给）；②阿乐单人、③果果单人（暂缓，非必需）。跑法：ComfyUI 画布上只替换正提示词节点文本（参数节点 cfg=1.0/steps=25 不动）→ Queue，无需重传文件。
  - **单人定妆图已出（~15:50）**：阿乐/果果单人照已生成，Qwen-Image-Edit 四件套下载中（VAE 242M 走 hf-mirror→AWS CDN 302 正常）。**Flux 固定 seed 坑（用户疑问）**：wf_02 KSampler 是 `seed=25, control_after_generate=fixed`——同 prompt 下重复 Queue 输出**同一张图**，想出新变体必须①点 seed 框旁骰子🎲随机，或②手动改 seed 数字，或③把 control_after_generate 改 randomize。改 prompt 会出图变化是因为 prompt 本身就是条件输入（seed 相同也会因条件不同结果不同）。
  - **✅ Qwen-Image-Edit 四件套下载完成 + wf_03 改造为双人合成版（~16:05）**：`unsloth/Qwen-Image-Edit-2511-GGUF` 四件套齐（UNet 13G + Qwen2.5-VL Q4_K_M 4.4G + mmproj-BF16 1.3G + VAE 243M，均 `models/` 对应子目录，mmproj 与主模型前缀一致 `Qwen2.5-VL-7B-Instruct-`）。**官方确认（Unsloth Qwen-Image-2512 教程 + ComfyUI docs）**：① mmproj 前缀与文本编码器一致即自动配对，CLIPLoaderGGUF 无需 mmproj 参数；② Qwen-Image-Edit-2511 原生支持多参考图（prompt 用 "image 1"/"image 2" 锚定）；③ 负面词宜自然语言短句勿堆关键词；④ Qwen-Image 是 flow matching，cfg=1.0。wf_03 本地已改：LoraLoader(multiple-angles) **bypass**(mode=4，转视角 LoRA 生图实例未下载且合成双人不需要)、LoadImage×2(ale_00001_.png/guoguo_00001_.png→image1/image2)、prompt=双人合成、负提示词自然语言、KSampler 7参 [12345,fixed,35,1.0,dpmpp_2m,karras,1.0]。待用户：传单人图到 `/root/ComfyUI/input/` + 重传 wf_03 + Load Queue。⚠️ LoadImage 需图在 ComfyUI input 目录。
  - **✅ wf_03 拆成两个版本（~16:10）**：用户提出"应先出单角色角度图再合成双人"（判断正确，专业流程=定妆→角度图→合成→I2V）。已备份 `wf_03b_qwen_edit_duo.json`（双人合成版：LoRA bypass、image1阿乐+image2果果、prompt 用 image1/image2 锚定、denoise 1.0）；`wf_03_qwen_edit_storyboard.json` 恢复为**角度图版**（LoRA mode=0 启用、prompt=`<sks> 方位角 仰角 距离` 转视角模板、denoise 0.8、无 image2）。**Multiple-Angles LoRA 官方源（~16:07 查到）**：`fal/Qwen-Image-Edit-2511-Multiple-Angles-LoRA`（HF，295MB，文件 `qwen-image-edit-2511-multiple-angles-lora.safetensors`，官方自带 ComfyUI 工作流 comfyui-workflow-multiple-angles.json + 可选节点 jtydhr88/ComfyUI-qwenmultiangle 3D 视角控制）；提示词公式=`<sks> [方位角] [仰角] [距离]`：方位角8(front view/front-right quarter/right side/back-right quarter/back view/back-left quarter/left side/front-left quarter)、仰角4(low-angle -30°/eye-level 0°/elevated 30°/high-angle 60°)、距离3(close-up/medium shot/wide shot)。hf-mirror 直链：`https://hf-mirror.com/fal/Qwen-Image-Edit-2511-Multiple-Angles-LoRA/resolve/main/qwen-image-edit-2511-multiple-angles-lora.safetensors` → `/root/ComfyUI/models/loras/`（与 wf_03 LoraLoader widgets 同名）。**老彭单人 prompt 补齐**（镜2/镜7 用，见会话）。
  - **新阻塞（~16:27）：Qwen-Image-Edit 跑 wf_03 时 `scaled_dot_product_attention() got an unexpected keyword argument 'enable_gqa'`**——`enable_gqa` 是 PyTorch **2.5+** 才支持的 GQA（Grouped Query Attention）参数，当前 torch=2.4.1+cu121 不够。须升级到 **torch 2.5.0+cu121**（同步 torchvision 0.20.0 + torchaudio 2.5.0）。优先阿里云内网 PyTorch 镜像 `-f https://mirrors.aliyun.com/pytorch-wheels/cu121/`，若无 2.5 wheels 则走官方 `--index-url https://download.pytorch.org/whl/cu121`（之前该源有 100KB/s + 哈希校验失败历史，必要时 `--no-cache-dir` 清缓存重试）。升级后**必须重装 `numpy<2`**（防 torch 升级顺带升 numpy）。升级完重起 ComfyUI 验证 200 + IMPORT FAILED 0 再跑 wf_03。
  - **✅ torch 2.5.0 升级成功（~17:07）**：`pip install torch==2.5.0 -f https://mirrors.aliyun.com/pytorch-wheels/cu121/ --no-cache-dir`（阿里云镜像有 2.5 wheels，无需走官方）+ `pip install "numpy<2"` → `torch: 2.5.0+cu121 | numpy: 1.26.4` + `ComfyUI HTTP: 200` + 无 IMPORT FAILED。依赖冲突警告（torchvision 0.19.1 要 torch==2.4.1、lmdeploy/pai-easycv 旧包）均为 DSW 预装环境遗留，**不影响 ComfyUI**，忽略。enable_gqa 解决，可重跑 wf_03 角度图。
  - **⚠️ 角度图 LoRA 不生效根因（~18:05，重要）**：`LoraLoader`（普通）加载 Qwen-Image-Edit LoRA **静默跳过**（它同时处理 CLIP，key 转换对 Qwen 不匹配→LoRA 没应用，输出=输入）。**官方工作流 `comfyui-workflow-multiple-angles.json`（fal 仓库自带，已下载到本地 `D:\Aicomfyui\aliyun_h3\workflows\official_multiangle.json`）证实必须用 `LoraLoaderModelOnly`**（只 patch MODEL，widgets 只有 [lora, strength_model]）；官方 prompt 就是**纯 `<sks> [方位角] [仰角] [距离]`** 一行，无任何附加描述；官方 KSampler `denoise=1.0`（还用了 Lightning-4steps LoRA 加速，steps=4，可选）。已按官方结构修正 wf_03 角度图版：node5 → `LoraLoaderModelOnly`（[lora, 1.0]）、prompt 纯 `<sks> front-right quarter view eye-level shot medium shot`、denoise 1.0、删 link3（CLIP→LoRA）、保留 link4/5。**通用经验**：Qwen/Flux 等 DiT 模型 LoRA 一律用 `LoraLoaderModelOnly`（除非官方明确用 LoraLoader）；官方工作流永远是最佳参照（铁律"优先官方示例作底"再次验证）。
  - **待补（非阻塞）**：① 修 `setup_img_pai.sh` 加 `git clone ComfyUI`+节点安装步骤（避免新实例再踩空壳挡 clone）；② 修 Qwen-Image-Edit 正确 repo + 脚本回退 bug（若后续要 wf_03 角度图）；③ wf_01 扩写需装 `comfyui-sg-llama-cpp` LLM 节点（当前未装，先别跑 wf_01）。

## 2026-08-07
### 2026-08-07

## 今日进展
- 用户启动生图实例 `dsw-831216` ComfyUI（端口 8188，DSW 网关 `proxy/8188`）。
- 用已修正的 `wf_03_qwen_edit_storyboard.json`（LoraLoaderModelOnly + 纯 `<sks>` prompt + denoise=1.0）跑阿乐角度图。
- **结果异常**：输出图角度与参考图几乎一致，脸部崩坏（表情从笑变抿嘴、肤色脏）。
- 已修正长期记忆：生图实例 dsw-831216 端口为 **8188**（非 6889）。

## 待诊断根因
1. LoRA 节点是否真正串进 Qwen Image Edit 的 **MODEL 路径**（截图待核）。
2. LoRA 参数是否生效（`lora_name` 是否选对、`strength` 是否为 1.0）。
3. Prompt 是否严格为 `<sks> 方位 仰角 距离` 且无额外描述。
4. LoRA 文件完整性（`qwen-image-edit-2511-multiple-angles-lora.safetensors`，约 282M）。
5. 终端日志是否有 LoRA key 不匹配或静默跳过警告。
6. 是否需对照 fal 官方 `official_multiangle.json` 工作流逐项核对节点接线。

## 根因定位与修复
- 对照 `official_multiangle.json`（fal 官方 Multiple-Angles LoRA 工作流）发现：
  1. **模型接线顺序反了**：官方是 `UNET → 角度LoRA → LightningLoRA → ModelSamplingAuraFlow → CFGNorm → KSampler`，AuraFlow/CFGNorm 在 LoRA **之后**；而 `wf_03` 是 `UNET → ModelSamplingAuraFlow → 角度LoRA → KSampler`，AuraFlow 在 LoRA **之前**。
  2. **ModelSamplingAuraFlow shift 值错误**：官方用 `3.1`，`wf_03` 用 `1.73`。
  3. **负提示词混用 CLIP**：官方负提示词是空的 `TextEncodeQwenImageEditPlus`，`wf_03` 用 `CLIPTextEncode` 接长串负面词，可能和 Qwen 正条件冲突导致脸崩。
  4. 官方工作流因缺少 bf16 主模型、fp8 text_encoder、Lightning LoRA 而无法直接运行，但节点结构可作为正确接线模板。
- 已修改 `D:\Aicomfyui\aliyun_h3\workflows\wf_03_qwen_edit_storyboard.json`：
  - `UNET → LoraLoaderModelOnly → ModelSamplingAuraFlow → KSampler`
  - `ModelSamplingAuraFlow` shift `1.73 → 3.1`
  - 负提示词清空（暂用空字符串）

## 第二轮测试与修正
- 用户加载旧版 `wf_03`（仍含孤立节点「角色参考图2(果果单人)」），继续报角度没变+脸崩。
- 本人误判：把画面上残留的孤立节点当成已连到 image2，实际该节点无输出 link，未接入工作流。
- 已清理 `wf_03`：删除孤立节点，补回缺失的 model link 1/2，调整节点位置使视觉顺序与逻辑顺序一致（`UNET → LoRA → AuraFlow → KSampler`）。
- 当前待验证：用户重新上传最新版 `wf_03`，Queue 跑阿乐 front-right quarter view，观察角度是否真正改变；若仍不变，再考虑下载 bf16/safetensors 主模型或 Lightning LoRA。

## 2026-08-11
### 2026-08-11 角度图：按 fal 官方参数重写 wf_03

## 背景
连续多轮调参（denoise 1.0 / 0.93 / 0.85 / 0.97，LoRA 1.0 / 1.3 / 1.5，cfg 一直 1.0）角度都转不动或脸糊。
用户拿来一份"官方回复"（实为 AI 生成总结），逐条与 fal 官方对照后判定**大部分错误**，仅"GGUF 量化损失视角控制精度"一条成立。

## fal 官方权威来源（已核实）
- 模型卡：https://huggingface.co/fal/Qwen-Image-Edit-2511-Multiple-Angles-LoRA
- 官方 ComfyUI 工作流：`comfyui-workflow-multiple-angles.json`（同仓库）
- 在线体验：https://fal.ai/models/fal-ai/qwen-image-edit-2511-multiple-angles

## 官方 vs 那份"官方回复" 对照结论
| 回复主张 | fal 官方实际 | 判定 |
|---|---|---|
| 移除 `<sks>` | README 明确 trigger 必需 | ❌ 错 |
| 改用标准 LoraLoader | 官方用 `LoraLoaderModelOnly` | ❌ 错 |
| denoise 降到 0.7 | 官方 denoise 1.0 / steps 40 | ❌ 错 |
| 删 ModelSamplingAuraFlow | 官方工作流自带 | ❌ 错 |
| GGUF 量化损精度 | 官方 base 是 safetensors 原版 | ✅ 对 |

## 关键新发现（此前一直漏掉的变量）
**官方 Diffusers 示例 `true_cfg_scale=4.0`，对应 ComfyUI 的 KSampler `cfg`。我们一直用 cfg=1.0 → 条件引导几乎为零，LoRA 的角度指令根本没被"执行"。**
这很可能才是角度转不动的真根因（此前把 cfg=1.0 当成 Qwen 甜点参数照搬自 Flux，属误用）。
另：cfg=1.0 时负提示词完全无效，这也是之前填负面词没反应的原因。

## 已改文件
`D:\Aicomfyui\aliyun_h3\workflows\wf_03_qwen_edit_storyboard.json` 全量重写（官方参数版）：
- KSampler：`[20260811, "fixed", 40, 4.0, "euler", "simple", 1.0]`（steps 40 / **cfg 4.0** / euler+simple / denoise 1.0）
- LoRA strength：1.0 → **0.9**（官方推荐 0.8~1.0，此前 1.3/1.5 超范围）
- AuraFlow shift：保留 3.1；LoraLoaderModelOnly 保留；`<sks>` 保留
- prompt：`<sks> right side view eye-level shot medium shot`（90° 侧最易肉眼验证是否生效）
- 负提示词填入：`blurry, smudged face, distorted face, deformed, extra limbs, low quality, watermark, text`（cfg 4.0 后才生效）
- 参考图改为白底正脸 `ale_ref_front_00001_.png`
- SaveImage 前缀改 `angle_official`（与旧 storyboard_ 区分）
- **修掉 links 数组重复项**（link id 1、2 各出现两次，历次 Edit 遗留）
- 采样器由 dpmpp_2m/karras 改 **euler/simple**（flow-matching 模型官方口径）

## 待验证
上传新 wf_03 → Queue → 看 `angle_official_00001_.png` 角度是否真转 90°。
- 角度转了脸略糊 → GGUF 量化所致，可微降 cfg 到 3.0 或提 steps
- 角度仍不转 → 基本确认 GGUF 量化路线不可行，转 Flux+IPAdapter 或 fal 官方 API

## 验证结果（2026-08-11 13:15）
阿乐 right side view 角度图成功：从白底正脸参考图稳定转出标准右侧面 90°，身份特征（黄 T 恤、牛仔背带裤、帽子、发型、五官）完整保留，无糊脸/涂抹/背景崩坏。截图文件名 `Clipboard_Screenshot.png` 已保存。核心原因确认：**cfg=4.0 生效**，此前 cfg=1.0 导致条件引导几乎为零，LoRA 角度指令不被执行。

## 教训
- **cfg 不能跨模型照搬**：Flux 甜点 cfg=1.0，但 Qwen-Image-Edit + LoRA 官方要 4.0。参数迁移前必须查该模型官方示例。
- 反复微调单一参数无效时，应回头核对**是否有整类参数被错误固定**（此处 cfg 被当常量从未动过）。
- 非官方来源的"诊断报告"要逐条对官方文档核验，不可照单全收。

## 批量出图脚本 + 角度集定稿（13:3x 补充）
- **结论：单工作流单次只能 1 个角度**（LoRA 机制：1 参考图 + 1 `<sks>` 方位词 = 1 角度），不能一次出多图；但可用 ComfyUI API 批量脚本一次提交所有组合，后台自动排队。
- 批量脚本：`D:\Aicomfyui\aliyun_h3\scripts\batch_angle_gen.py`
  - 标准库 urllib 实现，无 pip 依赖；在 DSW 生图实例内部 `python3 batch_angle_gen.py` 运行（连 127.0.0.1:8188）。
  - 自动 UI→API 格式转换（拉 `/object_info` 映射 widget），循环替换 LoadImage.image / TextEncodeQwenImageEditPlus.prompt / KSampler.seed / SaveImage.filename_prefix，提交角色×角度全部任务并等完成。
  - 依赖参考图就位：`ale_ref_front_00001_.png` / `guoguo_ref_front_00001_.png` / `laopeng_ref_front_00001_.png`（果果、老彭尚未出白底正脸）。
- **角度集定稿 = 4 个**（正面用已有白底参考图、左前 front-left 弃用）：
  1. `front-right quarter view`（fr45）
  2. `right side view`（right）
  3. `back-right quarter view`（br45）
  4. `back view`（back）
  - 三角色 × 4 = **12 张**。左侧角度靠镜像 right side 图补足，不做生成。
- **新发现：front-left quarter view 与 right 系列输出雷同** —— fal 该 LoRA 训练数据是「正面→右侧→背面」连续视频，左侧角度覆盖弱，生成会退化到右前/右侧解。故正式集去掉 front-left。

## 左前角度决策（2026-08-11 14:1x 用户拍板）
- **左前在本路线下彻底无解，两种补法都否**：
  1. LoRA 硬出 front-left → 实测=假左前（与右前雷同），不可信；
  2. 镜像 right side 当左前 → 用户明确否掉（帽子歪向/背带扣等不对称元素翻转后会反，不能当真）。
- **角色圣经采用 fal 官方 4 词角度（终版，2026-08-11 14:3x 用户拍板）**：
  fal 官方示例只有 front / front-right / right / back 四个离散视角，back-right/front-left 非官方词、LoRA 会退化成 right side（14:28 实测 back-right 出成正侧面，用户确认有问题）。故最终角度集 = 正面0°(已有ale_ref_front白底参考图,不生成) + 右前45°(front-right quarter view) + 正侧90°(right side view) + 背面180°(back view)。
  每角色实际用 LoRA 生成 3 张，三角色 = 9 张。批量脚本 `batch_angle_gen.py` 的 ANGLES 已同步改为这 3 个（去掉 br45）。
- 左前/右后作为中间角不可靠，分镜临时需要时用邻近角度翻转/转场补足，不写进角色圣经成稿。

## 路线失败确认 + GPU 封顶（2026-08-11 15:0x）
- **用户实测三张图，确认当前 GGUF 量化路线做角色转面图彻底失败**：
  - `back view` → 输出正侧面（back 端点没学好）
  - `right side view` → 输出正侧面（✅ 唯一稳定可用的角度）
  - `front-right quarter view` → 输出正侧面（45° 中间角退化成 side）
- **修正此前记录**："阿乐右前 45° 成功"判定不可靠——当前 LoRA 在 GGUF 版上只能稳定产出 `right side view` 一种角度，front/back/quarter 均退化成 side。之前那张"右前成功图"很可能也是 `right side view` 出的（prompt 混淆）或 seed 偏 side。
- **GPU 规格确认**：用户确认 DSW 生图实例（dsw-831216）GPU 最高 A10 24G，**无法升级到 40G（需付费）**。故 bf16/safetensors 原版 Qwen-Image-Edit（28G 显存）路线彻底放弃。
- **24G 卡上可行方向（待用户定）**：
  1. **Flux + IP-Adapter 多角度**（推荐）：Flux Q4_K_S 6.7G + IP-Adapter 锁身份，角度由 prompt 直接控制，不依赖视角 LoRA 训练数据缺陷，A10 24G 吃得下。需新搭工作流。
  2. **fal.ai 在线 API**：官方完整权重出角度最稳，按次付费，不占本地显存，需传图到云端。
  3. **接受现状**：只用 `right side view` 一张侧面 + 正面参考图做分镜，放弃多角度。

## 调研 guojijun/ComfyUI_GJJ_Nodes（2026-08-11 15:1x 用户提案）
- 用户提案：节点 https://github.com/guojijun/ComfyUI_GJJ_Nodes + 模型夸克网盘 + 安装后点📁打开工作流，问可行不。
- **调研结论：不推荐安装**。理由：
  1. 该仓库是 328 节点大合集（图像/视频/音频/3D），主打**视频生成**（Wan/LTX/HunyuanVideo 等 75+ 视频节点），不是静态角色转面图专用工具。
  2. "📷多角度相机控制"节点是给**视频相机路径**用的（输出多角度提示词+相机信息），非从单张参考图生成静态转面图；"👤Character Multi View Studio"技术细节不明，大概率视频/3D 向。
  3. 模型全在夸克网盘，README 无显存占用数据，A10 24G 风险高；328 节点注入现有干净 ComfyUI（torch2.5+GGUF 环境）易冲突、维护成本高。
  4. 未解决根因：若仍靠 prompt 控角度，GGUF 量化下同样会退化（同当前 fal LoRA 失败原因）。
- **按用户铁律(2026-07-28)**：官方 README 无"从单张参考图稳定出角色多角度转面图"的明确用法说明 → 不得动手安装。
- 仍推荐 **Flux + IP-Adapter + ControlNet(OpenPose)** 路线（24G 可跑，角度由 pose 图精确控制，IP-Adapter 锁身份）。

## 调研 B站视频"人物资产四视图直出 int4_convrot"（2026-08-11 15:1x 用户提案）
- 视频 https://www.bilibili.com/video/BV11m3K69Ec1/（2026-07-25 发），对比 Krea2/Qwen/Flux/Firered/Boogu，标题含 "ComfyUI int4_convrot"。B站页面 WebFetch 只返回"正在缓冲"，抓不到正文，以下从标题+关联搜索还原。
- **int4_convrot 是什么**：ConvRot = "Rotation-Based Plug-and-Play 4-bit Quantization for Diffusion Transformers"（arXiv 2512.03673，2025-12）。对权重做 group-256 Hadamard 旋转 + INT4 打包，敏感层(int8 回退)保真。比 GGUF Q4_K_M 视角更保真。
  - HugFace 模型 `LAXMAYDAY/Qwen-Image-Edit-2511-int4-tensorwise-mixed`：14.9GB，PSNR 26.58dB（bf16 40GB 为基线，int8 30.05dB）。
  - ⚠️ **Runtime 未合入主干**：需要 `int4_tensorwise` runtime（comfy-kitchen PR #63 + ComfyUI loader 特殊分支），正式版 ComfyUI 会报 "format not available"。用户现有核心 `0cb84e7e` 大概率不支持。
- **关键转折——"四视图直出"的成熟方案不是 `<sks>` LoRA，而是自然语言角度 prompt + INT4 量化模型 + Lightning LoRA**：
  - RunningHub 现成工作流（已验证可出多视图）：`NunchakuQwenImageDiTLoader` 加载 `svdq-int4_r32-qwen-image-edit-2509-lightningv2.0-4steps.safetensors`（Nunchaku/SVDQuant W4A4），配 `Qwen-Image-Lightning` LoRA + `ModelSamplingAuraFlow` + `CFGNorm`；`TextEncodeQwenImageEditPlus` 的 prompt 写**自然语言角度**（"Shows the back-side of the man" / "Shows the side view of the man, facing to the left."），**三个 KSampler 并行**一次出背/左/右三视图；euler/simple、8步、denoise=1。
  - 这正是 Qwen-Image-Edit 官方能力（图生图 + 自然语言指令改视角），**根本不需要 fal 的 Multiple-Angles LoRA 和 `<sks>` 触发词**。
- **我们此前死循环的根因确认**：走错技术栈——用 `GGUF Q4_K_M + fal <sks> Multiple-Angles LoRA`，而该 LoRA 训练数据只覆盖 4 个离散视角且 GGUF 量化压坏视角精度；应改用 **Nunchaku INT4 (svdq) 或 convrot + Lightning + 自然语言角度 prompt**。
- **两条 24G 可行路线对比**：
  1. **Nunchaku svdq-int4**（推荐，runtime 已合入 ComfyUI v0.28.0 附近的 int4 支持）：需装 `ComfyUI-Nunchaku` 节点包 + 下 `svdq-int4_r32-...-2509-lightning-4steps.safetensors`(~20G内) + `qwen_2.5_vl_7b_fp8_scaled.safetensors` 文本编码器 + Lightning LoRA。模型 2509 版（非2511，但同系列）。
  2. **convrot int4**（视频作者可能用的）：保真更高，但需特殊 ComfyUI 分支，未合入主干，落地成本高。
- **下一步（待用户定）**：若走 Nunchaku，需先查官方 GitHub 文档确认安装 + 拿 RunningHub 工作流 JSON 作底，再搭 `wf_04_nunchaku_multiview.json`。按用户铁律(2026-07-28)动手前必须先查官方文档。

## Nunchaku 官方文档核实（2026-08-11 15:2x 完成）
- **正确仓库**：`mit-han-lab/ComfyUI-nunchaku`（非 chengzeyi）。官方文档 https://nunchaku.tech/docs/ComfyUI-nunchaku/ 。
- **模型版本 = 2509**（不是现有 2511）：HF 组织 `nunchaku-ai` / `nunchaku-tech`，仓库 `nunchaku-qwen-image-edit-2509`。
- **Lightning 4steps fused 模型（已融合 LoRA，无需单独加载 Lightning LoRA 节点）**：
  - `svdq-int4_r32-qwen-image-edit-2509-lightning-4steps-251115.safetensors`（~11.5G，推荐，显存友好）
  - 或 v2.0：`svdq-int4_r128-qwen-image-edit-2509-lightningv2.0-4steps.safetensors`（~12.7G，精度更高）
  - 下载：`https://huggingface.co/nunchaku-ai/nunchaku-qwen-image-edit-2509/resolve/main/<文件名>`
- **文本编码器**：`qwen_2.5_vl_7b_fp8_scaled.safetensors`（~9.28G 磁盘，fp8）。放 `models/text_encoders/`（**不是 clip/**）。来源：`https://huggingface.co/Qwen/Qwen-Image-Edit-2509/resolve/main/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors` 或 Comfy-Org 镜像。
- **VAE**：`qwen_image_vae.safetensors`（~254M），放 `models/vae/`。
- **ComfyUI 版本门槛**：官方明确 lightning 工作流需 **ComfyUI ≥ 0.3.60**。现有核心 `0cb84e7e` 需 git pull 升级确认。
- **安装方式**：git clone `ComfyUI-nunchaku` 到 `custom_nodes/` + 安装 `nunchaku` wheel（按 torch 版本选 whl，或用 `NunchakuWheelInstaller` 节点自动装）。需匹配 torch/cuda 版本。
- **节点/工作流（以官方 lightning.json 为蓝本）**：`NunchakuQwenImageDiTLoader`(model_path=fused 模型) + 文本编码器/VAE 加载节点 + `ModelSamplingAuraFlow` + `CFGNorm` + `TextEncodeQwenImageEditPlus`(自然语言角度 prompt) + `KSampler`(euler/simple, 4步, denoise=1.0)。多视图=复制 3 套 KSampler+prompt（背/左/右自然语言），共用同一参考图，一次 Queue 出三视图。
- **显存评估（A10 24G）**：DiT int4 ~11.5G + 文本编码器 fp8 ~9G ≈ 20.5G，逼近 24G 上限；需开 `cpu_offload` 或 Nunchaku 异步 offload（Transformer VRAM 可压到 ~3G），否则可能 OOM。建议用 r32(11.5G) 而非 r128(12.7G)。
- **重大风险（环境冲突）**：现有生图实例为 GGUF 路线装了 **torch 2.5.0+cu121**；Nunchaku wheel 按 torch 版本编译，最新版可能需 torch 2.6/2.7。就地升级 torch 可能破坏现有 GGUF/Flux 文生图。
- **部署策略（2026-08-11 用户拍板：单 ComfyUI）**：用户明确该生图实例专职文生图（白底参考图+多角度图+剧情分镜图全在一台出），**只用一台 ComfyUI**，不再开第二台/独立目录。方案改为把 Nunchaku 节点直接装进现有 `/root/ComfyUI`（端口仍 8188），与 GGUF/Flux 共存。脚本 `dsw_setup_nunchaku.sh` 已改单环境版：`git pull` 升级核心到 ≥0.3.60 + 确保 torch≥2.5 + clone ComfyUI-nunchaku 到 custom_nodes + 装 nunchaku wheel + 下模型到现有 models/{diffusion_models,text_encoders,vae}。⚠️ 升级核心/torch 后**必须验证现有 Flux(wf_02)/GGUF-QwenEdit(wf_03) 工作流仍可加载**，若被破坏再回退或隔离。
- **用户已确认走 Nunchaku 方案**（2026-08-11 15:2x）。下一步：用户在 DSW 实例执行 `dsw_setup_nunchaku.sh`，验证官方 lightning 工作流出图，再改造成三视图并行 `wf_04_nunchaku_multiview.json`。

## 清理脚本 + 单实例视频可行性（2026-08-11 17:1x 用户追问）
- **已把"废弃模型清理"写进 `dsw_setup_nunchaku.sh` 第 0 步**（与 Nunchaku 安装同脚本一次执行）。删除清单（释放 ~16G）：
  1. `models/unet/qwen-image-edit-2511-Q4_K_M.gguf`（13.24G，失败路线主模型）
  2. `models/clip/Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf`（失败路线 CLIP）
  3. `models/clip/Qwen2.5-VL-7B-Instruct-mmproj-BF16.gguf`（=mmproj-F16，失败路线视觉投影）
  4. `models/loras/*Multiple-Angles*`（fal LoRA）
  - **保留**：Flux(wf_02 白底参考图)、Qwen2.5-14B(sg-llama-cpp 文生图扩写)、`qwen_image_vae.safetensors`(Nunchaku 也用)、**ComfyUI-GGUF 节点(被 LTX-2 视频路线复用，绝不能删)**。
  - rm -f 容错（文件不在也不报错）；脚本前后各打一次 `df -h /root` 看释放量。
- **单实例生视频可行性结论：可以，但必须串行，不能并发。**
  - Nunchaku 2509 显存极轻：官方称最低 4GB、<15GB 自动 offload，deepwiki 写"supports 3GB operation"。24G 上跑完图后还剩大量余量。
  - LTX-2 Q4_K_M(Kijai GGUF) ~12.7G，社区报告 24G 卡(4090/3090)跑得舒服，峰值含文本编码器+VAE 约 16–20G。
  - 两栈不能同驻 24G：流程=先用 Nunchaku 出齐图 → 卸载 → 再用 LTX-2 图转视频。同一台 dsw-831216、同一 ComfyUI、端口 8188。
  - **磁盘**：Nunchaku 2509(~21G) + LTX-2 栈(Q4_K_M 12.7 + gemma fp8 ~8 + VAE ~2.7 + embeddings connector ~2.8 ≈ 26G) + 保留的 Flux(~9.5G)+LLM(~8G) ≈ 65G+。清理失败路线后若实例盘 ≥100G 可容纳；**执行前先 `df -h` 确认**。
  - **节点共存性**：Nunchaku(mit-han-lab) 与 LTX-2(Kijai GGUF+KJNodes) 可同处一个 custom_nodes；ComfyUI 核心 ≥0.3.60 同时满足两者。
  - 权衡：无并行提速（A10 跑视频本就慢）；开发/迭代阶段完全够用，生产吞吐建议仍分实例。
  - 待用户决定：是否把 LTX-2 安装也并入同一脚本（需先核实下载 URL + 确认磁盘余量）。本地 `D:\Aicomfyui\pai\dsw_setup_ltx2_qwentts.sh` 已有 LTX-2 安装逻辑可借鉴。

## LTX-2 并入一站式脚本（2026-08-11 17:4x 用户确认）
- 用户确认"单实例串行跑图+视频"，要求把 LTX-2 安装并入 `dsw_setup_nunchaku.sh` 做成图+视频一站式。
- **已核实 LTX-2 官方下载源(Kijai/LTXV2_comfy 文件树确认)**：主模型 `ltx-2-19b-dev_Q4_K_M.gguf`(12.7G，确实存在；另一份指南写的 `ltx2-19b-Q4_K_M.gguf` 是 QuantStack 仓库命名，不用)；connector 仓库已改名 `ltx-2-19b-embeddings_connector_distill_bf16.safetensors`(原 `_bf16` 被重命名)；Gemma 用 `unsloth/gemma-3-12b-it-GGUF` 的 Q4_K_M GGUF(能被 DualCLIPLoaderGGUF 直接加载，作者引用 fp8 曾缺失)；VAE `LTX2_video_vae_bf16`+`LTX2_audio_vae_bf16`。
- **脚本改动**：第 8 步新增 LTX-2 视频栈——装 `ComfyUI-KJNodes`(确保 `ComfyUI-GGUF` 在场)、下模型到 `models/{unet,text_encoders,vae,upscale_models,loras}`、下 HerrDehy `LTX2_I2V_GGUF v0.3.json` 到 `models/workflows/`；开头加 `df -BG` 磁盘余量检查(<30G 警告)。`bash -n` 语法校验通过。
- **用法提示(写进脚本结尾 echo)**：视频工作流里把 UnetLoaderGGUF 改为 `LTX-2-dev-Q4_K_M.gguf`、DualCLIPLoaderGGUF 的 gemma 改为 `gemma-3-12b-it-Q4_K_M.gguf`、connector 改为 `ltx-2-19b-embeddings_connector_bf16.safetensors`；OOM 降 480p 或关 upscaler。
- 待用户开实例传脚本执行：跑完先 Load Nunchaku lightning 验证出图，再 Load LTX2_I2V 验证视频；并回归验证 Flux(wf_02)/GGUF-QwenEdit(wf_03) 工作流仍可加载(核心/torch 已升级)。

## 2026-08-12
### 2026-08-12 生图实例 Nunchaku 安装脚本 URL 修正

## 事件
- 用户在 dsw-831216 首次执行 `dsw_setup_nunchaku.sh`，跑到 6a 主模型下载即 **404 中断**（`set -e` 导致后续 6b/6c/7/8 全未跑）。
- pip install nunchaku 0.16.1 把 numpy 顶到 **2.4.6**、scipy 1.17.1，控制台报一堆 DSW 自带包（tensorflow/lmdeploy/outlines/spacy）`numpy<2.0` 冲突告警——但这些不是 ComfyUI 依赖，启动时再验证 ComfyUI 是否受影响。

## 根因（两处 URL 写错 + 两处脚本 bug）
1. **6a 主模型 404**：原写 `svdq-int4_r32-qwen-image-edit-2509-lightning-4steps-251115.safetensors`（带日期子目录名）。官方 `nunchaku-ai/nunchaku-qwen-image-edit-2509` 仓库里该文件名只在 `lightning-251115/` 子目录，根目录只有 `svdq-int4_r128-qwen-image-edit-2509-lightningv2.0-4steps.safetensors`。**官方 lightning 工作流引用的是根目录 r128 版**（非 r32）。→ 改为 `svdq-int4_r128-qwen-image-edit-2509-lightningv2.0-4steps.safetensors`。
2. **6b 文本编码器 404**：原写 `Qwen/Qwen-Image-Edit-2509/.../text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors`——该仓库只有 bf16 分片，无 fp8 文件。正确来源 `Comfy-Org/Qwen-Image_ComfyUI` 的 `split_files/text_encoders/`。→ 改源。
3. **step0 清理 cd 路径 bug**：清理 rm 在 `cd "$BASE"` 之前执行，相对 `models/...` 打到 launch 目录（/mnt/workspace），等于没清理（失败路线 16G 仍在）。→ 全部加 `$BASE/` 前缀。
4. **step7 工作流下载错镜像**：从 `hf-mirror.com/mit-han-lab/...` 下 GitHub 文件必 404（hf-mirror 只代理 HF，不代理 GitHub）。→ 改为从已克隆的 `custom_nodes/ComfyUI-nunchaku/example_workflows/` 直接复制。

## 核实结果（全部已查官方仓库文件树）
- Nunchaku DiT：根目录 `svdq-int4_r128-qwen-image-edit-2509-lightningv2.0-4steps.safetensors`（r128 版，lightningv2.0）✓
- 文本编码器：`Comfy-Org/Qwen-Image_ComfyUI/split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors` ✓
- VAE：`Comfy-Org/Qwen-Image_ComfyUI/split_files/vae/qwen_image_vae.safetensors` ✓
- **LTX-2 全部 URL 经复查均正确**（Kijai/LTXV2_comfy 主模型/connector/VAE、unsloth/gemma-3-12b-it-Q4_K_M、Lightricks 的 spatial-upscaler）— 无需改。

## 脚本改动（已写回 dsw_setup_nunchaku.sh，bash -n 通过）
- 6a/6b URL 修正 + wget 加 `--tries=3 -T 60` 重试
- step0 清理加 `$BASE/` 前缀 + 清理上一次误留的 r32 错误空文件
- step7 改复制节点目录（非致命）
- step8.3 wget 改非致命（`|| echo`）

## 待办
- 用户**重传修正后的脚本覆盖实例旧文件**，再 `bash dsw_setup_nunchaku.sh` 重跑（6a/6b/6c/7/8 未跑过，会重新下；LTX-2 栈 ~26G 一并下）。
- 跑完启动 ComfyUI，先 Load `nunchaku-qwen-image-edit-2509-lightning.json` 验证出图；再回归验证 Flux(wf_02)/GGUF-QwenEdit(wf_03) 是否因 numpy 2.4.6 升级而异常。

## 第二次修正（续传安全，用户问"换时段下载/有无续传"后）
- 用户重跑修正版，[0]清理生效（释放 18G：68G→50G）、[1]git pull 已最新、[2]torch 升到 2.5.0（CUDA12.4 依赖从 tuna 下，速度 **1.1~1.2 MB/s** 确认带宽瓶颈）、[6a]主模型开始下。
- **[6a]实测**：`svdq-int4_r128-qwen-image-edit-2509-lightningv2.0-4steps.safetensors` = **12,654,443,144 字节 ≈ 12.6GB**；hf-mirror 302 跳转到 `us.aws.cdn.hf.co`（美国 XET CDN），国内拉美国源可能偏慢。
- **发现续传坑**：原脚本模型下载用 `if [ ! -f 文件 ]; then wget; fi`——中途 Ctrl-C/停实例会留半成品，重跑时误判"已存在"直接跳过 → 模型残缺。用户问"换时段/续传"时定位此坑。
- **修复**：6a/6b/6c 改为**始终 `wget -c`**（去 `if` 判断，完整秒跳过/残缺续传/缺失下载）；dl() 改为先下 `.part` 完成才改名（重跑安全续传）。两脚本 `bash -n` 通过。
- 另拆出**图-only 脚本** `dsw_setup_nunchaku_img.sh`（awk 抽主脚本 0–7 阶段 + 尾部提示，不含 LTX-2 那 26G），用于先验证出图、视频栈后装；同样已修续传安全。
- 结论给用户：下载跑在 DSW 云端，关浏览器不影响；不必刻意换时段（带宽恒定、美国 CDN 未必更快）；真要停实例隔天续，用**修复后脚本**重跑即可（续传走 hf-mirror 源会重新签发 CDN 链接，不受旧签名过期影响）。

## 第三次修正（国内源 ModelScope，用户问"只能美国源？国内没有？"后）
- **根因确认**：hf-mirror 现在对所有大文件 302 跳 `us.aws.cdn.hf.co`（HF 新 XET 美国存储 CDN），国内拉美国源慢。用户 [6a] 卡在 9% 慢速。
- **国内源核实（全部查到真实文件）**：
  - 6a 主模型：`modelscope.cn/models/nunchaku-tech/nunchaku-qwen-image-edit-2509`（org 是 `nunchaku-tech` 不是 `nunchaku-ai`）→ `resolve/master/svdq-int4_r128-qwen-image-edit-2509-lightningv2.0-4steps.safetensors`，302 跳 `cdn-lfs-cn-1.modelscope.cn`（国内 CDN）✓ 与 HF 文件字节一致。
  - 6b 文本编码器 + 6c VAE：`modelscope.cn/models/Comfy-Org/Qwen-Image_ComfyUI`（搜索确认 `modelscope download --model Comfy-Org/Qwen-Image_ComfyUI split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors` 可用）→ `resolve/master/split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors` 与 `.../split_files/vae/qwen_image_vae.safetensors` ✓
  - **LTX-2（Kijai/LTXV2_comfy）ModelScope 无干净镜像**（只有 unsloth/LTX-2-GGUF 303G 大杂烩，不确定含 dev_Q4_K_M）→ 暂留 hf-mirror（可能也卡美国 CDN，等用户真下视频时若慢再单独找镜像）。
- **脚本改动**：新增 `dl_ms()`（ModelScope 国内源 + .part 续传安全 + 完成跳过）替代 6a/6b/6c 的 wget；两脚本 `bash -n` 通过。torch/节点克隆已有守卫（重跑安全、不重复装）。
- **给用户即时操作**：Ctrl-C 当前慢下载 → 用 `wget -c -L <modelscope URL> -O <同文件名>` 从国内源**续传** 6a（接着 9%）→ 再重跑更新后脚本（6a 已完整则跳过、6b/6c 走国内源、做 7/8）。
- ⚠️ 注意：更新后脚本的 dl_ms 用 `if [ -s ]` 跳过完整文件——若 6a 在中途残留下**不完整** partial 就重跑，会被误判"已存在"跳过 → 所以必须先手动 wget -c 把 6a 续传完整，再重跑脚本。

## 第四次修正（LTX-2 也全改国内源，用户说"全部改成国内源"后）
- **LTX-2 国内源核实（curl 探活 HTTP 状态码确认）**：
  - `unsloth/LTX-2-GGUF` **没有 Q4_K_M**（404），它用别的命名 → 弃用。
  - **主模型**改用 `chatpig/ltx2-gguf` `ltx2-19b-dev-iq4_xs.gguf`（10.5G，Q4 级，302 跳 `cdn-lfs-cn` 国内 CDN 确认）✓ 重命名为 `LTX-2-dev-Q4_K_M.gguf` 供工作流 Load。
  - **Gemma** `unsloth/gemma-3-12b-it-GGUF` `gemma-3-12b-it-Q4_K_M.gguf`（302 确认）✓
  - **connector** `chatpig/ltx2-gguf` `ltx2-19b-embeddings_connector_dev_fp8_e4m3fn.safetensors`（302 确认）✓ 重命名 `ltx-2-19b-embeddings_connector_dev_bf16.safetensors`。**修正旧 bug：dev 主模型须配 dev connector（非 distill）**。
  - **video VAE** `chatpig/ltx2-gguf` `ltx2_video_vae_fp8_e4m3fn.safetensors`（302 确认）✓ 重命名 `LTX2_video_vae_bf16.safetensors`
  - **audio VAE** `chatpig/ltx2-gguf` `ltx2_audio_checkpoint_vae_bf16.safetensors`（200 确认）✓ 重命名 `LTX2_audio_vae_bf16.safetensors`
  - **spatial upscaler** `Lightricks/LTX-2` `ltx-2-spatial-upscaler-x2-1.0.safetensors`（302 确认）✓
  - 删去旧 `ltx-2-19b-distilled-lora_...`（dev 模型不配 distill lora）。
- **脚本改动**：删除 step8 内的 `dl()`(hf-mirror 版)，LTX-2 全部改用 `dl_ms()`(ModelScope 国内源)；删除旧 `dl` 下载的旧 `ltx-2-19b-distilled-lora` 行；结尾提示 connector 改为 dev 版、注明主模型实为 iq4_xs。
- **新增体积防御（防旧 wget 残缺文件被误判完成）**：step6 前加 `if [ -f "$NM" ] && size<13G → rm -f`，避免旧脚本中断残留的 12.6G partial 被 dl_ms 跳过。
- 两脚本（主 + 图-only）`bash -n` 通过。至此 **6a/6b/6c/8 全部走 ModelScope 国内源**，无美国 CDN 瓶颈。
- **给用户操作**：Ctrl-C 停掉当前跑的旧版（hf-mirror 慢）脚本 → 重传最新脚本 → `bash dsw_setup_nunchaku.sh`（或先用图-only `dsw_setup_nunchaku_img.sh` 先验证出图，省 LTX-2 那 ~26G 等待）。脚本会自动清残缺文件并从国内源拉齐。

## 验证阶段（用户 Load 工作流出图）
- **关键坑**：本机 ComfyUI（≥0.3.60，Nodes 2.0 中文界面，`图形 ▼ → 文件 → 打开`）**弹的是系统原生本地文件对话框（上传本机文件）**，不是浏览云端硬盘。用户本机当然找不到云端 `models/workflows/` 的 json。
- **解决**：本机沙箱直连 `raw.githubusercontent.com` 被重置（Exit 35），改用 `https://ghproxy.net/https://raw.githubusercontent.com/...` 代理拉到 **本机 `C:\Users\Administrator\Downloads\nunchaku-qwen-image-edit-2509-lightning.json`（23KB）**，用户在原生对话框里选这个本地文件上传即可。
- **核对**：该工作流引用的三个模型名 `svdq-int4_r128-qwen-image-edit-2509-lightningv2.0-4steps.safetensors` / `qwen_2.5_vl_7b_fp8_scaled.safetensors` / `qwen_image_vae.safetensors` 与 6a/6b/6c 下载的完全一致，Load 后无需改模型名。
- **下一步**：用户 Load 后在画布点 Queue Prompt 出图验证 Nunchaku 在 24G(A10) 上跑通；同时第 8 步 LTX-2 仍在后台下载（独立进程，互不干扰）。

## 工作文件落地更正（用户 2026-08-12 14:4x 纠正）
- **用户纠正**：工作文件不能放 C 盘 Downloads，必须放本地工作文件夹（D 盘项目目录）。
- **处理**：JSON 已从 `C:\Users\Administrator\Downloads\` 复制到 `D:\Aicomfyui\aliyun_h3\workflows\nunchaku-qwen-image-edit-2509-lightning.json`（23.7KB，内容核对一致），并清理 Downloads 副本。代理拉取不稳定时，优先从云端/已有副本 cp 到 D 盘目标，避免依赖网络。
- **已固化约定**：在 MEMORY.md 新增「本机工作文件落地约定」段——普通工作文件（脚本/工作流/文档）一律放对应项目 D 盘目录，不放 C 盘 Downloads；仅绿盾要求的"生成测试文件"才落 Downloads。用户铁律段也补了这条。

## 环境故障排查（2026-08-12 15:0x）
- **症状**：用户重跑主脚本后，Load 官方 lightning 工作流报 5 错：①缺失节点包 ComfyUI-nunchaku ②缺失模型 qwen_2_5_vl_7b_fp8_scaled ③缺 Image 输入等。
- **根因定位**：第 6 步（Nunchaku 主模型 6a + 文本编码器 6b + VAE 6c）下载**未落地**——`find` 确认 `models/diffusion_models/` 空、`models/text_encoders/` 只有 Flux 的 clip_l/t5xxl；而第 8 步 LTX-2（chatpig）`.part` 在下载中（说明 [8] 跑了、[6] 没成功）。VAE 之前就有（qwen_image_vae 253MB 8/6）。
- **链接已本机验证正确**：`nunchaku-tech/nunchaku-qwen-image-edit-2509`(主模型) 与 `Comfy-Org/Qwen-Image_ComfyUI/split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled`(文本编码器) 均 HTTP 200 可下（不走 CDN 跳转，直接 200）。→ 链接没错，是 `dl_ms()` 在 DSW 上对这两仓库下载失败（chatpig 成功，疑似 `-C -` 续传 + 直接 200 的组合坑，或 DSW 对该仓库网络偶发）。
- **临时解决（已给用户）**：Ctrl-C 停 LTX-2 → 另开终端用最简 `curl -L --retry 5 -o` 手动下上述两文件（绕过脚本 dl_ms）→ 下完重启 ComfyUI 看启动日志（确认 nunchaku 节点 import 是否成功，目录在但报"缺失节点包"多半是 pip 包未 import）。
- **待修脚本 bug**：`dl_ms()` 的 `-C -` 续传逻辑需排查（或 nunchaku-tech/Comfy-Org 两仓库在 DSW 下载不稳定）；待用户验证手动 curl 是否成功后再定是改 dl_ms 还是换源。
- ⚠️ 用户铁律重申：工作文件落地 D 盘，已遵守。

## 手动 curl 补下进度（2026-08-12 15:19）
- 用户已执行最简 `curl -L --retry 5 -o` 手动下 6a/6b（绕 dl_ms）。输出确认：首行 `100 418` 是 ModelScope 302 跳转响应页（curl -L 跟随，非错误），第二行 `0 11.7G ... 1184k` 为真文件下载（已下 25MB，速度 **~1.18 MB/s**）。
- **重要实测结论**：ModelScope 从这台 DSW 也只有 ~1.18 MB/s，**跟之前美国 CDN 速度一样** → 瓶颈是 **DSW 实例出口带宽（约 1.2MB/s 封顶）**，不是 CDN 地域问题。国内源只是避免美国 CDN 偶发更慢/断流，但不能突破带宽上限。
- 时间估算：主模型 11.7G≈2.7h，文本编码器 9G≈2h，单终端串行约 5h。建议开第二终端并行下文本编码器（若出口是总带宽封顶则各自变慢、总时长不亏）。
- 下完收尾：关 ComfyUI 重启 → 贴启动日志前 40 行确认 nunchaku 节点无 ImportError → Load 官方 lightning 工作流接参考图出图验证。

## 停实例 + 续传方案（2026-08-12 17:02 用户问"现在停实例可以吧"）
- **结论：可以停**。下载写进 DSW 云盘 `/root/ComfyUI/models/`，停实例杀 curl 进程但不丢文件：主模型已落盘 ~2.14GB(17%)、文本编码器 256MB(2%)，均残缺可续传。
- **重启后必须用 `-C -` 续传**（curl 从断点接），绝不能用普通 `-o`（会 0 覆盖）。推荐命令（已含 `--retry-all-errors` 兜 SSL 超时）：
  - 主模型：`curl -L --retry 10 --retry-all-errors --retry-delay 10 --connect-timeout 60 -C - -o /root/ComfyUI/models/diffusion_models/svdq-int4_r128-qwen-image-edit-2509-lightningv2.0-4steps.safetensors "https://modelscope.cn/models/nunchaku-tech/nunchaku-qwen-image-edit-2509/resolve/master/svdq-int4_r128-qwen-image-edit-2509-lightningv2.0-4steps.safetensors"`
  - 文本编码器：`curl -L --retry 10 --retry-all-errors --retry-delay 10 --connect-timeout 60 -C - -o /root/ComfyUI/models/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors "https://modelscope.cn/models/Comfy-Org/Qwen-Image_ComfyUI/resolve/master/split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors"`
- **建议串行**：主模型先续完（优先、进度多），再续编码器，避免两路抢 1.2MB/s 出口带宽导致 SSL 超时（已实测并行会掉到 350KB/s 并触发 errno 110 超时）。
- **重启注意**：实例 dsw-831216 重启后 **IP 变、ComfyUI 端口链接失效**，需重新拉起 ComfyUI 才恢复推理；模型文件在云盘持久保留，不影响续传。

## 2026-08-14
### 2026-08-14 续传 Nunchaku 模型

- 用户 08-12 17:02 问"停实例可以吧"后，实际下载继续跑到 **~18:05** 才真正停（文件时间戳佐证）。今日(08-14)重启实例后 `ls` 确认残缺文件仍在且比预估大：
  - 主模型 `svdq-int4_r128-qwen-image-edit-2509-lightningv2.0-4steps.safetensors` = **5.8G / 11.7G（约 50%）**
  - 文本编码器 `qwen_2.5_vl_7b_fp8_scaled.safetensors` = **4.9G / 8.9G（约 55%）**
- 续传方案：`curl -L --retry 10 --retry-all-errors --retry-delay 10 --connect-timeout 60 -C -` + nohup 后台 + 日志（关浏览器不杀进程）。**建议串行**：主模型先续完再续编码器，避免两路抢 1.2MB/s 出口带宽掉速触发 SSL 超时。
- 剩余量：主 5.9G + 编码器 4.0G ≈ 9.9G，满带宽约 2.3h。
- 已给用户完整命令（dl_main.log / dl_enc.log）。待两份齐后：重启 ComfyUI → 贴启动日志前 40 行确认 nunchaku 节点无 ImportError → Load 官方 lightning 工作流出图验证。
- ⚠️ 用户铁律遵守：本机工作文件仍在 D 盘项目目录。

## 续传已启动（2026-08-14 09:35）
- 用户已跑主模型 nohup 续传：`[1] 12191`，日志 `/root/dl_main.log`。后台跑、输出不进终端（正常现象，非卡死）。
- 验证方式（给用户）：`tail -f /root/dl_main.log`（看进度，Ctrl-C 退出 tail 不杀 curl）、`ls -l --block-size=M /root/ComfyUI/models/diffusion_models/*.safetensors`（看大小爬升）、`ps aux | grep curl | grep -v grep`（确认进程在）。
- 预期：从 5.8G 续，速度 ~1.18MB/s，ETA ~1.4h 主模型齐；齐后起编码器续传（同法，日志 /root/dl_enc.log）。

## MEMORY.md（长期项目记忆）
### 项目长期记忆：桃子角色 自动视频生成

## 核心定位
- 目标：桃子单角色带情节视频 → 多角色视频 → 漫剧。按每日调研调整技术选型。
- 当前路线（2026-08-12 定稿）：Nunchaku INT4 出图 + LTX-2 视频，单 ComfyUI 串行（实例 dsw-831216，端口 8188）。

## 本机工作文件落地约定（用户 2026-08-12 重申）
- 所有工作文件（脚本/工作流/文档）放对应项目 D 盘目录（如 `D:\Aicomfyui\aliyun_h3\...`），**不要创建在 C 盘 Downloads**。
- 例外：仅"绿盾要求的生成测试文件"才直接落 Downloads（安全目录）；普通工作文件一律 D 盘项目目录。

## 技术路线（Nunchaku 出图 + LTX-2 视频）
### Nunchaku 出图（24G 卡多角度最终方案）
- 节点 `mit-han-lab/ComfyUI-nunchaku`（需 ComfyUI ≥0.3.60）。
- **安装坑（2026-08-14 实战）**：真正量化库是 `nunchaku>=1.0.1`（nunchaku-tech/nunchaku，版本带 `+torch2.x` 后缀，如 `1.0.1+torch2.7`）。PyPI 默认 `nunchaku` 0.16.1 是同名**统计包**（依赖 matplotlib/scipy），装错会让节点加载失败（`pip show nunchaku` 看 Requires 即可分辨）。正确 wheel 不在 PyPI 默认源，而从官方 flat 索引装：`pip install "nunchaku==1.0.1+torch2.7" -f https://raw.githubusercontent.com/nunchaku-tech/ComfyUI-nunchaku/refs/heads/dev/pypi/nunchaku_index.html`；该 raw.github 国内可能慢，备选用 ComfyUI 内置 NunchakuWheelInstaller 节点（`install_wheel.json`）自动匹配 torch+CUDA。torch 须 ≥2.6（comfy_kitchen 0.2.30 的 `list[int]` 在 2.5.0 的 `infer_schema` 不认），已升 2.7.1+cu124。
- DiT = `svdq-int4_r128-qwen-image-edit-2509-lightningv2.0-4steps.safetensors`（nunchaku-ai 仓库根目录；官方 lightning 工作流即引用此 r128 名；r32 带日期旧名已 404）。
- 文本编码器 = `qwen_2.5_vl_7b_fp8_scaled.safetensors`（来自 `Comfy-Org/Qwen-Image_ComfyUI` 的 `split_files/text_encoders/`；不在 `Qwen/Qwen-Image-Edit-2509` 仓库，后者只有 bf16 分片）。
- VAE = `qwen_image_vae.safetensors`（同仓库 `split_files/vae/`）。
- Qwen-Image-Edit 原生支持自然语言改视角（"Shows the back-side of the boy" 等），不依赖 fal `<sks>` LoRA。三 KSampler 并行一次出背/左/右三视图。
- 参考工作流（官方 lightning）：本机已存 `D:\Aicomfyui\aliyun_h3\workflows\nunchaku-qwen-image-edit-2509-lightning.json`，云端 `models/workflows/`。注意本机 ComfyUI 的「打开」是上传本地文件模式，需本机有该 json 才能选。

### Flux 白底参考图（wf_02，仍用）
- 出角色白底正脸参考图。文生图端到端：`Qwen2.5-14B-Instruct` GGUF Q4_K_M 扩写 → `Flux.1 dev` GGUF Q4_K_S(~6.7G)。
- 文本编码器在 `comfyanonymous/flux_text_encoders`：`t5xxl_fp8_e4m3fn(~2.5G)` + `clip_l.safetensors`，须 DualCLIPLoader 双加载。t5xxl_fp16 实为~9.8G，叠 Flux 必 OOM。

### LTX-2 视频（全国内源，2026-08-12 核实）
- 主模型 `chatpig/ltx2-gguf` 的 `ltx2-19b-dev-iq4_xs.gguf`(10.5G) → 重命名 `LTX-2-dev-Q4_K_M.gguf`
- Gemma `unsloth/gemma-3-12b-it-GGUF` 的 `gemma-3-12b-it-Q4_K_M.gguf`
- connector `chatpig/ltx2-gguf` 的 `ltx2-19b-embeddings_connector_dev_fp8_e4m3fn.safetensors` → 重命名 `ltx-2-19b-embeddings_connector_dev_bf16.safetensors`（dev 主模型须配 dev connector，非 distill）
- 视频 VAE `chatpig/ltx2-gguf` 的 `ltx2_video_vae_fp8_e4m3fn.safetensors` → `LTX2_video_vae_bf16`
- 音频 VAE `chatpig/ltx2-gguf` 的 `ltx2_audio_checkpoint_vae_bf16.safetensors` → `LTX2_audio_vae_bf16`
- 空间上采样 `Lightricks/LTX-2` 的 `ltx-2-spatial-upscaler-x2-1.0.safetensors`
- 节点 `ComfyUI-KJNodes` + `ComfyUI-GGUF`（GGUF 必须保留，LTX-2 的 UnetLoaderGGUF/DualCLIPLoaderGGUF 依赖它；Nunchaku 不用）
- A10 24G：LTX-2 须 Q4 级（iq4_xs 10.5G），勿用 Q8(20.4G)；显存临界→关 upscaler/降分辨率。
- 弃用源：`unsloth/LTX-2-GGUF` 无 Q4_K_M(404)、`Kijai/LTXV2_comfy` 在 ModelScope 无干净镜像。

## 实例信息
- HAI 实例：IP 每次变；SSH:22 root；ComfyUI:6889；python 须 `/root/miniforge3/bin/python3`。
- dsw-831216（生图实例/当前）：端口 **8188**；启动 `cd /root/ComfyUI && python3 main.py --port 8188 --listen 0.0.0.0`；python 实测为 **/usr/local/bin/python3**（torch 2.7.1+cu124，非 miniforge3——之前误用 miniforge3 路径导致启动 127）；代理 `https://dsw-gateway-cn-shanghai.data.aliyuncs.com/dsw-831216/proxy/8188/`；实例关机后进程停、链接失效，重启并拉起 ComfyUI 即恢复。
- dsw-823428（视频实例）：端口 6889。
- 一键脚本：`D:\Aicomfyui\aliyun_h3\scripts\dsw_setup_nunchaku.sh`（图+视频一站式：清理废弃 GGUF 路线 + 国内源装 Nunchaku+LTX-2）；图-only 版 `dsw_setup_nunchaku_img.sh`。

## 已弃用路线（仅留根因备忘）
- fal Multiple-Angles LoRA + GGUF Q4_K_M：仅 right side view 可出，余全退化成 side view（LoRA 仅 4 离散视角 + GGUF 量化压坏精度）。cfg=1.0 导致角度不生效（需 4.0），但整体路线已证伪→改用 Nunchaku 自然语言改视角。
- 旧 9宫格（Agnes+SDXL+MV-Adapter）、IP-Adapter（锁不住非人类角色）已弃用。
- Qwen-Image-Edit 非跨对象变换工具（桃子→蘑菇必失败）。

## CloudBase 生图项目（2026-07-31 起，独立）
- 输入短描述→扩写→CloudBase 生图。uni-app(Vue3+Vite)+Node.js(@cloudbase/node-sdk)，云托管同源托管 H5。
- 工程 `D:\Aicomfyui\cbimg-cloudrun\`；GitHub 私有 `mz20191223/cbimg-cloudrun` main；CloudBase 拉仓库 Git 部署。
- 环境 `mz0708` / `mz0708-d6grh8a1xcfa9b963`；免费额度 Token 包 1亿+生图 10万张，至 2027-01-04。
- 根因：免费 AI 额度仅认官方 SDK（node-sdk），裸 HTTP 调 AI 网关报 AI_CHANNEL_NOT_ALLOWED；v2 改 @cloudbase/node-sdk 自动鉴权（commit d5c50a2）。详细见 2026-07-31.md。

## 用户铁律
- 工具/模型/工作流动手前必查官方教程确认，无官方说明不动手。
- 后续优先用社区/RunningHub 成品工作流反向学习，不现推节点。
- 账密同步腾讯文档【相关平台和账密】。
- 本机工作文件落地 D 盘项目目录，不放 C 盘 Downloads（见上"本机工作文件落地约定"）。

## 每日日志索引
- `2026-07-28.md`：角色圣经根因(LoRA+`<sks>`)、官方确认铁律、LTX-2 事实、社区工作流验证方式转变。
- `2026-07-29.md`：16G 转向文生图端到端(Qwen2.5-14B扩写→Flux.1 dev)，节点包/文件名经官方核实。
- `2026-07-31.md`：CloudBase 生图转 Node.js+@cloudbase/node-sdk 自动鉴权（d5c50a2）；官方额度/SDK约束；Git 部署。
