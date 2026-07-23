# 桃子 AI 视频 · 云端 ComfyUI 项目状态（2026-07-23 续接手册）

> 本文件是给「另一台电脑 / 下一次会话」的续接入口。实例 IP、密码等运行时信息以用户最新消息为准。

## 目标
端到端：桃子角色参考图 `peach_role_v6.png` + 分镜提示词 → 出「跨镜头角色一致」的皮克斯风短视频。
验收标准：达到本地 p1 效果 **且** 修复两个已知问题——
1. s01→s02 草堆被推飞像切场景（根因：camera 运镜字段未进视频提示词 + 关键帧构图不连续）
2. 角色横移跑动而非原地探头扒草（应原地完成动作）

## 当前架构（路径乙，2026-07-23 定稿）
- **图像前端 = Qwen-Image-Edit-2511（GGUF，云端 ComfyUI）**：出多角度参考图(B) + 从头重出 p1 分镜图(C)。
  - 关键事实：**LTX 2.3 节点包只能出视频、无文生静止图节点**，"出分镜图"必须有独立图像生成器 → 故恢复 Qwen-Edit（此前因磁盘紧张曾放弃，后拍板恢复）。
  - 权重：unet=`qwen-image-edit-2511-Q4_K_M.gguf` + clip=`Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf` + `mmproj-BF16.gguf` + `qwen_image_vae.safetensors`
- **视频引擎 = LTX 2.3（云端 ComfyUI）**：吃参考图+提示词出视频，原生修两个已知问题（固定机位/背景留画面/原地勿横移）。
- **多参考锚定（待装）= Licon-MSR**：ComfyUI-Licon-MSR 插件 + MSR IC-LoRA V2，把参考图合成参考视频锚定身份，绕开 IP-Adapter 对非人类角色锁不住的坑。
- 已弃用：Agnes 图生视频路线、AnimateDiff+IPAdapter 路线、Phantom/Wan 路线（T4 显存/一致性不符）。

## 实例状态（HAI T4 16G；当前 IP 43.155.234.34 —— 重启会变，以用户最新发的为准）
- 已装插件：`ComfyUI-LTXVideo`（解压自 `cloud/_ltx_mirror.tar.gz`）、`ComfyUI-GGUF`（解压自 `cloud/_gguf_mirror.tar.gz`）
- 未装：`ComfyUI_Qwen_Image_Edit`（本机 `cloud/_qwen_mirror.tar.gz` 待传）、`Licon-MSR`
- 权重下载（实例上 `/root/dl_qwen.sh`，`setsid` 后台，`wget -c` 续传）：
  - 已完成：mmproj-BF16.gguf(1.35G)、qwen_image_vae.safetensors(0.25G)
  - 进行中（2026-07-23 傍晚）：unet(~1.1G↑)、clip(~2.1G↑)；约 4.5MB/s
  - 完成标志：`/root/dl.log` 出现 `ALL_DONE`
- 桃子锚图：已传 `/root/ComfyUI/input/peach_role_v6.png`
- 入口：SSH `root` / 密码见对话历史（**不入库**）；ComfyUI `:6889`

## 另一台电脑续接步骤（从 GitHub clone 后）
1. `git clone https://github.com/mz20191223/ai-comfyui.git`（main 分支）
2. 用户在 HAI 控制台开/重启实例 → 发新 IP + SSH 密码
3. 传插件镜像（本机 `cloud/` 已有 tar.gz，用 `cloud/sftp_upload.py`）：
   ```
   python sftp_upload.py <ip> 22 root cloud/_ltx_mirror.tar.gz  /root/ComfyUI/custom_nodes/_ltx_mirror.tar.gz
   python sftp_upload.py <ip> 22 root cloud/_gguf_mirror.tar.gz /root/ComfyUI/custom_nodes/_gguf_mirror.tar.gz
   python sftp_upload.py <ip> 22 root cloud/_qwen_mirror.tar.gz /root/ComfyUI/custom_nodes/_qwen_mirror.tar.gz
   ```
   SSH 解压：`cd /root/ComfyUI/custom_nodes && tar xzf _ltx_mirror.tar.gz && mv _ltx_mirror ComfyUI-LTXVideo && tar xzf _gguf_mirror.tar.gz && mv _gguf_mirror ComfyUI-GGUF && tar xzf _qwen_mirror.tar.gz && mv _qwen_mirror ComfyUI_Qwen_Image_Edit`
   （若 `_qwen_mirror.tar.gz` 缺失：本机 `git clone --depth 1 https://ghproxy.net/https://github.com/QwenLM/ComfyUI_Qwen_Image_Edit` 再打包）
4. 续传权重：SSH 进实例 `setsid bash /root/dl_qwen.sh > /root/dl.log 2>&1 &`（wget -c 续传）
5. HAI 控制台『重启 ComfyUI』加载插件
6. 拉 `object_info` 验证节点齐：LTXVideo 系列 / `UnetLoaderGGUF` / `QwenImageEdit` 系列
7. 出分镜图：组装 `cloud/qwen_ref_*.json`(B 多角度) 与 p1(C) → 提交 → 发用户预览做**评审闸门**（用户强调"从头生成才能发现问题"）

## 关键坑（务必记）
- 实例出网白名单仅 HF/ModelScope/baidu；**GitHub 全系被墙** → 插件代码必须本机 `ghproxy.net` 镜像再 SFTP。
- 实例侧 **HF 直连可用**（权重从 huggingface.co 直接 wget）；本机 HF 被墙（历史用 hf-mirror）。
- SFTP 上传：`msys` 版 Python 不翻译 `/d/...` 绝对前缀，用相对路径 `../` 或真实 Windows 路径。
- SSH 密码敏感，**不写库**；开机后用户重发。
- 磁盘：实例系统盘 49G，清旧模型后约 15–19G 可用；纯 LTX+Qwen 分段顺序加载即可，不冲突。
- 本机 `ssh_run.py`/`sftp_upload.py` 密码从环境变量 `SSH_PASS` 读，不落盘；依赖系统 `python3` + `paramiko`（托管 Python 需 `pip install paramiko`）。

## 文件清单（cloud/ 为本项目工作目录）
| 文件 | 作用 |
|------|------|
| `CLOUD_PIPELINE.md` | 执行手册（A节点核对→B多角度参考图→C从头分镜图→D LTX视频→E拼接验收） |
| `cloud_pipeline.py` | 通用云端客户端（上传参考图→提交→轮询→下载图+视频） |
| `check_cloud_nodes.py` | 节点核对（curl object_info） |
| `ssh_run.py` / `sftp_upload.py` | 实例 SSH exec / SFTP 上传（密码走 SSH_PASS 环境变量） |
| `peach_refs_prompts.json` | 多角度参考图提示词（正面/侧/背/表情+一致性锚定，中英双语） |
| `ltx_p1_prompts.json` | p1 四段视频提示词，强制"固定机位/背景留在画面内/原地勿横移" |
| `dl_qwen_weights.sh` | 实例侧权重下载/续传脚本（wget -c） |
| `_ltx_mirror.tar.gz` (52M) | LTXVideo 插件代码镜像 |
| `_gguf_mirror.tar.gz` (80K) | ComfyUI-GGUF 插件镜像 |
| `_qwen_mirror.tar.gz` | Qwen-Image-Edit 插件镜像（克隆中/或已就绪） |
| `../peach_role_v6.png` | 桃子锚图（一致性基准，已传实例 input/） |
