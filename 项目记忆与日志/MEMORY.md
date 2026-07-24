# 项目长期记忆：桃子角色 自动视频生成（Qwen-Image-Edit GGUF 出图 + LTX 视频）

## ⚠️ 每日收尾硬性约定（用户 2026-07-24 起，务必每天执行）
- 每天工作结束前，把本项目 `.workbuddy/memory/*.md` 全部复制到 `<项目D盘根目录>\项目记忆与日志\`（源保留，绝不删源）。
- 本项目目标目录：`D:\Aicomfyui\项目记忆与日志\`。
- Git Bash：`mkdir -p "/d/Aicomfyui/项目记忆与日志" && cp "/c/Users/Administrator/WorkBuddy/2026-07-15-13-21-24/.workbuddy/memory/"*.md "/d/Aicomfyui/项目记忆与日志/"`

## 当前主线（2026-07-24 起）
- **技术路线**：HAI 实例上 **Qwen-Image-Edit（GGUF 权重）锁角色一致性出图** → 本地组装分镜 → **LTX 2.3 出视频**。
- **与旧路线关系**：原「Agnes+SDXL+MV-Adapter+AnimateDiff」9 宫格路线**已暂停**（IP-Adapter 锁不住非人类角色、SDXL 显存临界）。Qwen 出图完成后的视频阶段可能仍复用 ComfyUI。
- **出图分步**：① `gen_refs.py` 出 4 张多角度参考图给用户确认 → ② 组装 p1 分镜（修运镜硬伤）→ ③ LTX 2.3 出视频。

## 项目位置
- 根目录：`D:\Aicomfyui`（脚本/配置/图片/poses 全在此）。记忆仍在 WorkBuddy 会话目录。
- 跨电脑真相源 GitHub：`https://github.com/mz20191223/ai-comfyui.git`（main）。
- 本机出图/SSH 辅助脚本：`D:\Aicomfyui\cloud\`（gen_refs.py / run_after_boot.py / resume_after_boot.py / swap_weights.sh / ssh_run.py / sftp_upload.py）。

## HAI 实例关键事实
- **实例公网 IP 每次开机都变**（已验证 43.166.8.9 → 43.155.217.119 → 43.155.215.130）。脚本读 `COMFY_HOST` 环境变量，不硬编码。`gen_refs.py` 默认兜当前 IP。
- SSH `:22` root / 密码 `Gp3666923ssd*`；ComfyUI HTTP `:6889`。
- Python：`/root/miniforge3/bin/python3`（conda 3.10.11，torch 2.5.1+cu124，T4 15.9G VRAM）。注意：**`/usr/bin/python3` 是 3.8.10（旧的）**；手动 setsid 拉起时 `launch_comfy_ui.sh` 里的 `python3` 会解析成 3.8 → `set[str]` 报"不可下标"。手动启动务必用 `/root/miniforge3/bin/python3` 显式指定。
- **ComfyUI 由 supervisor 托管**（kill 旧 main.py 自动拉起；官方日志 `/var/log/sd_service.log`）。
- **ComfyUI 已升级到 `0cb84e7e`（2026-07-23 最新，原生支持 Qwen-Image）**：原 HEAD `debabcc`(v0.3.14) 不认识 Qwen 架构 → 误判 SD3 → KeyError `pos_embed.proj.weight`。升级方式：旧 CLIP 补丁 `git stash` → `git checkout master` → `git clean -fd -e comfy_orig_bak` → `git pull` → 重启。原版备份在 `/root/ComfyUI/comfy_orig_bak/`（保留）。
- **依赖补齐**：新版 ComfyUI 启动缺 `sqlalchemy` 等 12+ 新包，已用 `pip install -r requirements.txt` 安装（核心依赖 torch/numpy 等已满足，不重下；但 `transformers` 被中断安装导致损坏，已手动清理残留并 `--force-reinstall --no-deps transformers==5.14.1` 修复）。装完 `pip cache purge` 回收约 1GB 缓存。
- **权重真相**：`qwen-image-edit-2511-Q4_K_M.gguf` 真实大小 **12.34 GB**（早先 2.75G 是截断损坏）。已完整下载并 rename 转正，落 `/root/ComfyUI/models/unet/`。

## 关键踩坑（避免重踩）
- **Qwen 权重 reshape 失败**（早期 2.75G 截断文件）→ 换/重下完整权重即可，无需改 comfy 核心。
- **本机下载模型网络**：`huggingface.co` 被墙；用 `hf-mirror.com`。Git Bash 下 curl 写盘用 `D:/Aicomfyui/...` Windows 路径（`/d/...` 报错）。
- **IP-Adapter 对非人类角色锁不住**（旧路线实测，weight 0.8→0.95 都失败）→ 旧 9 宫格路线弃用。
- 后台长任务（run_after_boot/resume）会被系统回收（ssh 读超时假失败）；改短轮询续跑。
- 本机连 ComfyUI 用 curl 比 urllib 稳；删除文件包 try/except OSError。

## Agnes AI 后端（前端/分镜/参考图，已接入）
- Base URL `https://apihub.agnes-ai.com/v1`，免费额度。Key 见用户级 MEMORY.md（或 agnes_llm.py 常量）。
- LLM：`agnes_llm.py`→agnes_chat()，须关 thinking（`enable_thinking=False`）。
- 图片：`agnes_image.py`→generate_image()，模型 `agnes-image-2.1-flash`。
- 视频：`agnes_video.py` 备用，不锁角色。

## 待办（当前）
1. ✅ `gen_refs.py test` 已验证新版 ComfyUI + Qwen 权重加载（生成 `peach_test_00001_.png`）。
2. ⏸️ `gen_refs.py full` 出 4 张参考图（正面全身/左侧/背面/开心表情）发用户确认 → **用户 7/24 末关机，实例已停、IP 失效；此前后台任务 `xV7cVh` 随关机终止，无需手动停。待用户重启发新 IP 后续跑**。
3. 用户确认 → 组装 p1 分镜（修运镜）→ LTX 2.3 出视频（视频阶段方案见 7/24 日志「视频速度答疑」：分阶段解耦 / 换大显存实例 / Agnes API 兜底）。
4. 收尾：复制项目记忆到 `D:\Aicomfyui\项目记忆与日志\`（每日硬性约定）。

## 每日工作日志索引
（目录见会话 `.workbuddy/memory/`；记录技术决策/踩坑/命令/状态，非聊天稿）
- 2026-07-15 ~ 07-22：项目起点、IP-Adapter/Xet 踩坑、SDXL/MV-Adapter 路线定稿（**旧路线，已暂停**）
- 2026-07-23：Qwen CLIP 连锁补丁落实例（后被 `git stash`，因升级到原生支持）
- 2026-07-24：Qwen 出图链路；权重截断根因；换完整权重 + ComfyUI 升级到 0cb84e7e

## 账密 / 跨项目约定（详见用户级 MEMORY.md）
- 账密/密钥同步腾讯文档【相关平台和账密】 https://docs.qq.com/sheet/DU1NXU3JMZGR0Skdv?tab=BB08J2 （出现即更）。
- 上下文恢复后先通读本项目 memory + 源码再执行。
- 每日记忆导出 D 盘。
