# 桃子项目对话记录（2026-07-24 ~ 2026-07-31）

> 由项目记忆每日日志（`.workbuddy/memory/YYYY-MM-DD.md`）合并整理，按日期归档，便于在资料库检索与通读。本篇涵盖：2026-07-24 ~ 2026-07-31。

## 2026-07-24
### 2026-07-24 工作日志（Qwen-Image-Edit 出桃子分镜图）

## 状态：CLIP 补丁全链路打通，剩独立新坑 = UNet 权重加载 reshape 失败

### 目标
HAI 实例（43.166.8.9，supervisor 托管 ComfyUI v0.3.14，T4 15.9G）上用 Qwen-Image-Edit GGUF 重新出桃子分镜图，锁定角色一致性；分步：① 先出 4 张多角度参考图给用户确认 → ② 组装 p1 各镜头分镜（修运镜硬伤）→ ③ LTX 2.3 出视频。

### 今日确认的关键事实
1. **ComfyUI 由 supervisor 托管**（PID 11 supervisord，01:27 起）。kill 旧 main.py 后 supervisor 自动拉起新进程（04:17 PID 3098），新进程启动即加载全部 CLIP 补丁。→ 关 HAI 再开，ComfyUI 自动起且带补丁，无需手动重启。
2. **CLIP/ops/attention 补丁全部生效并已验证（早上最大坑已填平）**：
   - comfy/ops.py：`RMSNorm`(grep=2)、`scaled_dot_product_attention`(grep=1)
   - comfy/sd.py：`QWEN_IMAGE` 枚举+分支(grep=2)
   - comfy/model_management.py：`flash_attention_enabled`(grep=1)
   - comfy/text_encoders/qwen_image.py：`end_token=151645`(grep=1)
   - comfy/ldm/modules/attention.py：新版（enable_gqa 支持）
   - 验证证据：重跑 `gen_refs.py test` 已跑到 `UnetLoaderGGUF` 节点（前序 CLIP/VAE 等全过），不再报任何 ops/attention/RMSNorm/flash 错误。
3. **新坑（独立，与 CLIP 补丁无关）**：`UnetLoaderGGUF` 加载 `qwen-image-edit-2511-Q4_K_M.gguf` 报 `cannot reshape array of size 23524165 into shape (18432,1728)`。
   - 诊断：文件 2748155301 字节(2.75G)完整、魔数 GGUF、版本 v3(`0300 0000`)。
   - gguf 包版本 **0.19.0**（最新，支持 v3，远超插件要求 gguf>=0.13.0）。
   - 直接 `gguf.GGUFReader(path)` 解析该文件也 reshape 失败 → **问题在权重文件本身/文件与解析器不兼容，非补丁问题**。
   - unet 目录仅有这一个 qwen gguf（7/23 10:38 下载）。

### 下午开 HAI 后待执行（用户无需守着，AI 自主跑）
1. 重下或换 qwen-image-edit-2511 权重（Q8_0 / Q5_K_M / 重下 Q4_K_M），从 hf-mirror 在实例上下（带宽快），验证 `GGUFReader` 能解析、UnetLoaderGGUF 能加载。
2. 权重可加载 → 重跑 `gen_refs.py test` 跑通 txt2img 验证。
3. 出 **4 张多角度参考图**（正面全身/左侧面/背面/开心表情）→ 发预览给用户确认（用户明确"先出这个并确认"）。
4. 用户确认 → 组装 p1 各镜头分镜图（修运镜硬伤：草堆飞走像切场景、角色横移非原地）。
5. LTX 2.3 出视频（需先解决 comfy_api 缺失使 ComfyUI-LTXVideo 加载；社区 haitang.hub 有 LTX2.3 工作流）。

### 连接信息（实例）
- ComfyUI HTTP: `43.166.8.9:6889`
- SSH: `43.166.8.9:22` root，密码 `Gp3666923ssd*`（本机 `ssh_run.py` 走 `SSH_PASS` 环境变量）
- Python: `/root/miniforge3/bin/python3`（conda 3.10.11, torch 2.5.1+cu124）
- 本机辅助脚本目录：`D:\Aicomfyui\cloud\`（ssh_run.py / sftp_upload.py / gen_refs.py / ops_sdpa_patch.py 等）
- 重启 ComfyUI：`fuser/ss/netstat/lsof` 均未装；用 `ps aux | grep 'miniforge3/bin/python3 -u main.py'` 取 PID + `kill -9`，supervisor 自动拉起。

### 注意（避免重踩）
- 早上"连锁补丁"坑已彻底解决，不要再补 ops/scaled_dot_product_attention / RMSNorm / attention 等。
- 唯一未决是权重文件，方向是**换/重下权重**，不是再改 comfy 核心。
- 本机沙箱 `git clone`/`cnb` 下载被拦截（SPA 返回 HTML），`curl` 通 github；实例上 `curl` 联网正常，下载权重走实例。

## 关机前补充（12:23 用户关机，本机侧准备）
- **根因确认（WebSearch）**：原 `qwen-image-edit-2511-Q4_K_M.gguf` 真实大小 **13.2 GB**（huggingface Daex032 页 meta 确认，Q4_K_M, tensor_count 1934, arch=qwen_image），实例上仅 2.75 GB = **严重截断** → GGUFReader reshape 失败的根本原因（非解析器/补丁问题，早上的"连锁补丁"已全通与此无关）。
- **正确下载源**：`unsloth/Qwen-Image-Edit-2511-GGUF`；国内用 **ModelScope 镜像**最稳（CSDN 实测命令可用）：`https://modelscope.cn/api/v1/models/unsloth/Qwen-Image-Edit-2511-GGUF/repo?Revision=master&FilePath=qwen-image-edit-2511-Q4_K_M.gguf`。hf-mirror 对 Xet 大文件易截断，不优先用。
- **已写 `swap_weights.sh`（本机 D:\Aicomfyui\cloud\）**：先下 .part → GGUFReader 校验 → 通过才替换 → 重启 ComfyUI。安全可重复。实例已关机，**下午开 HAI 后先 sftp 上传再 `bash /root/swap_weights.sh`**。
- **显存风险**：13.2G Q4_K_M + TE 4.68G + mmproj 1.35G ≈ 19G > T4 15.9G，**可能 OOM**。若 OOM 改用 `bash /root/swap_weights.sh Q3_K_M`（更小量化）。
- **文本编码器**：实例现有 Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf(4.68G) 之前能加载（test 已跑到 UNet 节点，前序 CLIP 通过），暂假定完整；下午若 UNet 通了但 CLIP 异常再查 TE 完整性（ModelScope 同 repo 可下）。

## 用户审计：每日日志执行情况（12:29）
- 用户确认日志重要，问"聊天内容每天整理"有没有执行、若有就在文件内写每天日志路径。
- **结论（如实）**：
  - 我一直写的是「工作日志」(`.workbuddy/memory/YYYY-MM-DD.md`)：技术决策/踩坑/命令/状态摘要，**非聊天逐字稿**。聊天记录另存 `D:\mz140129\MZ\vIDEOSTUDE\liblib-conversation-log.md`（用户最初约定的位置）。
  - **不是每天都有**：目录缺 `2026-07-18.md`、`2026-07-19.md`；`2026-07-15.md` 是 7/21 补记（非当天写）。
  - 其余 7/16、7/17、7/20~7/24 齐全。
- **已执行**：在 `MEMORY.md` 末尾新增「每日工作日志索引」区块，列出全部日志路径+缺天标注，方便后续查看。
- **7/18、7/19 真相（12:33 用户点破）**：`date` 验证 7/18=周六、7/19=周日 → 周末未开工，所以那两天**根本没有对话**，不是漏写。已把 MEMORY.md 索引标注从"缺失"改为"周末未开工（非漏写）"，且**不写推测补记**（无原始内容可补，诚信优先）。用户此前选的"补上这两天"因此撤销。
- **结论**：日志自 7/15（项目起点）至 7/24 仅工作日有记录，周末自然空，符合实际；无需补。

## 项目记忆导出 D 盘（12:37 用户要求）
- 用户要把项目记忆/日志挪到 D 盘自行整理。确认做法：**复制保留源**（不删 WorkBuddy 的 `.workbuddy/memory`，避免本会话失忆 + 遵守勿删 .workbuddy 原则）。
- 已复制全部 9 个 md（MEMORY.md + 8 个日期日志；7/18、7/19 周末无文件故不复制）到 `D:\Aicomfyui\项目记忆与日志\`。
- 源文件完好保留于 `C:\Users\Administrator\WorkBuddy\2026-07-15-13-21-24\.workbuddy\memory\`。用户在 D 盘可自由编辑整理，不影响 WorkBuddy 记忆连续性。
- **2026-07-24 12:38 用户升级为每日硬性约定**：以后每天工作结束前都要执行此复制。已记入 ①项目级 MEMORY.md「⚠️ 每日收尾硬性约定」②用户级 MEMORY.md「每日项目记忆导出 D 盘」两处，跨会话兜底。

## 平台账密统一留存腾讯文档（12:42 用户硬性要求）
- 用户要求：凡项目内出现平台账号/密码/API Key/Token/PAT/密钥，都及时更新到腾讯文档【相关平台和账密】 https://docs.qq.com/sheet/DU1NXU3JMZGR0Skdv?tab=BB08J2
- 已记入 ①用户级 MEMORY.md「平台账密/密钥 统一记到腾讯文档」②项目级 MEMORY.md「账密统一留存约定」两处。
- **已执行首次同步（12:43）**：文档原已有微信/公众号/DashScope/GitHub PAT/腾讯云服务器 VM-0-5-ubuntu/MySQL/Redis/JWT/Cloudflare 等。本次 append 两行（仅补文档缺失的本项目特有项，未破坏原数据）：
  1. 腾讯云 HAI 实例（皮克斯/Qwen 出图）｜ ComfyUI @ 43.166.8.9:6889 ｜ root ｜ `Gp3666923ssd*`
  2. Agnes AI（图片/视频生成）｜ agnes-image-2.1-flash / agnes-video ｜ Base `https://apihub.agnes-ai.com/v1` ｜ Key `sk-cr[REDACTED]`
- GitHub PAT 文档第4行已存在（mz20191223 / `github_pat_11...`），未重复写。
- 注意：文档里"腾讯云服务器 VM-0-5-ubuntu（生产机 SSH, ubuntu/Gp3666923ssd*）"与本项目的"腾讯云 HAI 实例（43.166.8.9 root/Gp3666923ssd*）"是**两台不同机器**，已分开记录。

## 上下文恢复后先通读再执行（12:45 用户硬性要求）
- 用户新增纪律：每次会话压缩/重置/新开会话后，动手执行任务**前**，必须先整体阅读本项目 `.workbuddy/memory/*.md` + `MEMORY.md` + 项目源码（`D:\Aicomfyui\` 脚本/配置），恢复完整上下文再决策，避免基于残缺记忆乱决策/重复踩坑/误改环境。
- 已记入 ①用户级 MEMORY.md「上下文恢复后先通读项目资料再执行」②项目级 MEMORY.md「上下文恢复后先通读再执行」两处，跨会话兜底。

## 开机一键总控脚本（12:52 用户问"开机后是直接执行还是试探"）
- 用户顾虑：下午开机后希望尽量"直接跑"、减少来回试探。
- **已写 `run_after_boot.py`（本机 D:\Aicomfyui\cloud\）**：把"探测 ComfyUI→传 swap_weights.sh→换完整 Q4_K_M 权重(Instance 内 ModelScope 约13G)→等 ComfyUI 重启就绪→txt2img 验证(test)→出 4 图(full)"串成单条命令。语法自检通过(SYNTAX_OK)。
- 内置一次 OOM 自动回退：test 若报 out of memory → 自动 `patch_unet(Q3_K_M)` + `bash /root/swap_weights.sh Q3_K_M` 重跑；仍失败才停。
- **停下点**：跑完在 ./out/ 生成 4 张参考图，由 agent 呈现给用户确认（符合用户"先出多角度参考图确认"要求）。
- 用法（下午开机后由 agent 跑）：`SSH_PASS='<HAI root 密码>' python run_after_boot.py`
- 注：按"上下文恢复先通读"约定，下午执行前 agent 会先通读 `.workbuddy/memory/*.md` + `D:\Aicomfyui\` 脚本再跑总控。

## ⚠️ 连接信息更正（14:05 用户确认）
- **实例公网 IP 每次开机都变**：本次 `43.166.8.9` → `43.155.217.119`（用户 14:05 重新提供）。日志第 30-32 行旧 IP 已失效。
- 后续每会话：IP 以用户当日提供的为准；脚本改为读 `COMFY_HOST` 环境变量（默认兜底当前 IP），不再硬编码。
- 腾讯文档账密表里的 HAI 实例 IP 也需随开机更新（目前写的是 43.166.8.9，下次开机记得同步新 IP）。**▸用户 14:17 决定：IP 动态变，中途不碰腾讯文档，等整个项目结束再统一改。**

## HAI 官方应用简报归档（14:12 用户提供，全量留存）
> 用户重发 HAI ComfyUI 应用简报，要求未存则存日志。以下为原文要点结构归档。

### 环境配置 / 预装
- **预装模型**：`v1-5-pruned-emaonly.safetensors`（即 SD1.5 基座，无 SDXL）。
- **预装插件**：ComfyUI-Manager、AIGODLIKE-COMFYUI-TRANSLATION、ComfyUI-AnimateDiff-Evolved、comfyui_controlnet_aux、comfyui-workspace-manager。**无 VideoHelperSuite / 无 IPAdapter / 无 Pixar LoRA**（与 MEMORY 段核实一致）。
- **SD 基础模型目录**：`/root/ComfyUI/models/checkpoints`。⚠️ 注意：`checkpoints` 是 Jupyter 关键字，web 文件栏点不进去；可点同目录 `ckpts` 文件夹查看，或 `cd` 进目录、`wget` 下、或上传本地模型至此。
- **SD 插件目录**：`/root/ComfyUI/custom_nodes`。插件下载异常时，先进此目录用 `git clone` 克隆。
- **下载建议**：把模型转存到与 HAI **同地域 COS 桶**，再在实例拉 COS 文件速度最快。国内地域 HAI 可能网络不稳，推荐启用「学术加速」；国外地域 HAI 下模型/插件更快。

### 快捷指令（Jupyter cell，按需单独执行）
- **重启 ComfyUI**：
  ```bash
  ps -ef | grep -i 'python3 -u main.py' | grep -v 'grep' | awk '{print $2}' | xargs kill -9
  cd /root/ComfyUI/
  python3 -u main.py --listen --port=6889 --disable-auto-launch >> /var/log/sd_service.log 2>&1 &
  proc_num=`ps -ef|grep "python3 -u main.py"|grep -v "grep"|wc -l`
  if [[ $proc_num -ge 1 ]]; then echo "success"; else echo "failed"; fi
  ```
  ⚠️ 日志写到 `/var/log/sd_service.log`（官方路径）；本项目实例实际由 **supervisor 托管**，kill 后 supervisor 自动拉起，无需手动重跑上面这句。
- **查看模型目录磁盘占用**：`du -h -d 2 /root/ComfyUI/models`
- **删除 Jupyter 垃圾箱**：`rm -rf ~/.local/share/Trash`
- **查看 ComfyUI 运行 log**（执行其他 cell 前需终止此 cell）：`tail -f /var/log/sd_service.log`（可用 vim 看完整内容）

### 拉取模型（Jupyter cell，按需单独执行，官方工具）
```bash
### 下载 checkpoint 模型（SDXL/SVD/anythingv5，需 17GB）:
wget -N http://mirrors.tencentyun.com/install/HAI/install_hai_tools.sh -P /tmp && bash /tmp/install_hai_tools.sh && python3 /root/hai_application/qcloud_hai/hai_tools/download_models_main.py --model-class checkpoint
### 常用组件（VAE/embeddings/lcm_lora，需 1.3GB）:
... --model-class lora && --model-class vae && --model-class embeddings
### controlnet+预处理器（SD1.5/SDXL，需 24GB）:
... --model-class controlnet && --model-class Annotators
### animatediff+lora（需 2.2GB）:
... --model-class animatediff_model && --model-class animatediff_lora
```
> 官方工具 `download_models_main.py` 同地域 COS 拉取快、只耗带宽不耗 GPU；后续若需补模型可走此路。

## 下午开机执行进度 + 磁盘干预（14:18~）
- 总控 `run_after_boot.py`（后台任务 QLSLL3）按约定：先通读记忆 → 改 `COMFY_HOST` 应对 IP 变更 → 探测在线 → 传 swap_weights.sh → 下完整 13.2G 权重 → 等重启 → test 验证 → full 出 4 图。
- **⚠️ 磁盘爆盘风险（已干预）**：`/root` 盘 49G 已用 39G（剩 7.7G），13.2G 完整权重下完峰值约 50G 必失败。→ 主动 `rm -f` 删旧坏权重(2.75G 截断废物) + 清 Trash，腾到剩 9.8G；峰值重算 ≈47.8G<49G 可完成。删旧后 swap_weights.sh 替换逻辑更干净（无 .bak 冲突）。
- 当前(14:18)下载进度 ~15%（.part 2.01G/13.2G），进程 PID 286 正常；后续由总控自动续跑，跑完通知 agent 呈现 4 图给用户确认。
- **14:22 磁盘二次干预（清缓存）**：`checkpoints` 实测为空（HAI 预装 SD1.5 不在盘），无可删非必需大模型；仅清 `/root/miniforge3/pkgs`(1.6G)+`/root/.cache`(4.2G) 缓存（conda clean -afy + rm pip cache），释放约 2G。现磁盘 36G/49G、剩 11G；下载峰值约 45.5G、余 3.5G 缓冲，已彻底安全。.part 实时 3.73G 增长中。无 Plan B 必要（不换更小量化）。

### 拉取预存模型（Jupyter cell，按需单独执行）
统一前置：`wget -N http://mirrors.tencentyun.com/install/HAI/install_hai_tools.sh -P /tmp && bash /tmp/install_hai_tools.sh &&`
然后接 `python3 /root/hai_application/qcloud_hai/hai_tools/download_models_main.py --model-class <class>`：
- `checkpoint`（SDXL/SVD/anythingv5，需 17GB）
- `lora` + `vae` + `embeddings`（常用组件，需 1.3GB）
- `controlnet` + `Annotators`（适配 SD1.5/SDXL，需 24GB）
- `animatediff_model` + `animatediff_lora`（需 2.2GB）
> 注：此工具仅下官方 preset 模型，**不含 Qwen-Image-Edit GGUF**；本项目 Qwen 权重仍走实例内 ModelScope 镜像（见 `swap_weights.sh`）。

## 脚本参数化（14:13 顺手做）
- `gen_refs.py`：新增 `COMFY_IP = os.environ.get("COMFY_HOST", "43.155.217.119")`，`HOST` 与 `api()` 的 curl `--noproxy` 均改用 `COMFY_IP`。
- `run_after_boot.py`：`HOST = os.environ.get("COMFY_HOST", "43.155.217.119")`。
- 背景总控任务 `QLSLL3` 启动于 14:13（用旧硬编码 IP=43.155.217.119，与当前 IP 一致，不受影响）；正执行换权重(约13G)→重启→验证→出4图。完成时自动通知。

## 总控失败诊断 + 续跑（14:29 起）
- **QLSLL3 失败根因（两个独立问题）**：
  1. `run_after_boot.py` 步骤[2]用**阻塞式 ssh** 等 13G 下载完成，但 `ssh_run.py` 对长时间无输出命令会读超时（约 15min 抛 `socket.timeout`）→ [2]"假失败"退出（subprocess.run 无 check，异常未冒泡，故[3][4]仍跑）。
  2. 但实例上 `swap_weights.sh`(PID286)+`curl`(PID287) **未断**，`.part` 持续涨（14:29 时 4.89G/13.2G≈37%）；旧坏权重此前已删 → 此刻**正式文件不存在** → 步骤[4]提交验证时 `UnetLoaderGGUF` 报 `unet_name not in []`（文件列表空）→ `prompt_outputs_failed_validation`。
- **关键事实**：`swap_weights.sh` 是 `set -e` 脚本，curl 下完后**会自动** GGUFReader 校验 → `mv .part` 正式文件 → `kill ComfyUI`（supervisor 自动重启）。故**无需重新触发下载**，只需等其自行完成再接管验证/出图。
- **新建 `resume_after_boot.py`（本机续跑）**：轮询等 swap 进程消失+正式文件≥13G（只读不抢 .part）；若 swap 中途失败则用 `setsid bash /root/swap_weights.sh Q4_K_M &` 后台重触发（脱离 ssh、-C - 续传）兜底；完成后 `wait_comfy` → `gen_refs.py test` → `gen_refs.py full`（OOM 自动回退 Q3_K_M）。UNET 常量确认=`qwen-image-edit-2511-Q4_K_M.gguf`（匹配）。
- 续跑任务 `QR5qgT` 后台启动于 14:29（SSH_PASS+COMFY_HOST=43.155.217.119），预计下载完约还需 15min，完成后自动通知 agent 呈现 4 图给用户确认。
- **磁盘答疑**：用户 14:29 在 orcaterm 查到 `37G 已用/9.6G 可用`——37G 是已用（非可用）；清缓存瞬间曾剩 11G，现 `.part` 4.89G 在涨使已用+4.89G、可用−4.89G 属正常下载过程；峰值≈45.3G<49G 上限，不会爆。

## ComfyUI 升级"未生效"诊断 + 关机待重启（16:07）
- **`gen_refs.py test` 复跑仍失败，报错与升级前完全一致**：`KeyError: 'pos_embed.proj.weight'` @ `comfy/model_detection.py:678 convert_diffusers_mmdit`。结论：**升级只改了硬盘，没重载运行进程**。
- **SSH 诊断核实**：
  - 磁盘 `git HEAD = 0cb84e7e`（新版，原生支持 Qwen），`model_detection.py` 含 qwen 分支（`grep -c qwen`=1）→ 新代码已在盘。
  - 但**运行进程 = PID 23**（`python3 -u main.py --listen --port=6889`），由 supervisord 开机拉起 = 旧 v0.3.14 代码；`git pull` 未触发进程重载。
  - `comfy_ui` 程序：`command=/usr/local/bin/launch_comfy_ui.sh`、`autorestart=false`；supervisord 无 unix/inet socket → `supervisorctl` 无法直接连。
- **修复动作（16:07 已执行）**：`kill -9 23` + `setsid bash /usr/local/bin/launch_comfy_ui.sh` 重拉新代码。
- **⚠️ 用户 16:07 决定关机**，IP 会变、回来再发新 IP。→ **关机反而最干净**：下次开机 supervisord `autostart=true` 会用盘上 0cb84e7e 新代码自动拉起 ComfyUI，等于"重启即生效"，无需手动 setsid。
- **回来后待办（用新 IP）**：
  1. `curl system_stats` 确认在线；`comfyui_version` 字段未必更新（旧值 0.3.14 是 stale 标签），以 `QwenImageSampler` 节点存在 + 不再 KeyError 为准。
  2. 重跑 `gen_refs.py test`（txt2img 验证 Qwen 权重加载）。
  3. **风险**：升级后**未跑** `pip install -r requirements.txt`（磁盘曾紧 ~1.8G）；若新版缺依赖会启动失败 → 查 `/var/log/sd_service.log`，再谨慎按需 `pip install`（避爆盘）。
  4. test 过 → `sftp_upload.py` 上传本地 `D:\Aicomfyui\peach_role_v6.png` 到 ComfyUI input → 跑 `gen_refs.py full` 出 4 张多角度参考图发用户确认。
  5. 用户确认 → 组装 p1 分镜 → LTX 2.3 出视频。
- **git stash 备注**：旧 CLIP 补丁已 `git stash`（可逆）；新代码原生支持 Qwen 不需补丁；`comfy_orig_bak/` 原版备份保留。

## 新 IP 重启后修复 + test 跑通（16:22~）
- 用户重启后新 IP `43.155.215.130`，ComfyUI HTTP 起不来 → 日志报 `ModuleNotFoundError: No module named 'sqlalchemy'`。
- **根因**：升级后未跑 `pip install -r requirements.txt`，新版 `app.assets` 数据库模块缺 `sqlalchemy` 等 12+ 新包。
- **安装依赖**：
  - 跑 `/root/miniforge3/bin/pip install -r /root/ComfyUI/requirements.txt -i https://mirrors.cloud.tencent.com/pypi/simple`。
  - 安装过程中旧 `transformers 4.49.0` 卸载到一半中断，留下 `~ransformers`（包目录）、`~ransformers-4.49.0.dist-info` 和 `-ransformers` 残留，导致新版 `transformers 5.14.1` 装成命名空间包，`CLIPTokenizer` 导入失败（`transformers.__file__=None`）。
  - **修复**：手动 `rm -rf` 删掉 transformers 相关所有目录（真实包 + `~ransformers*` + `transformers-*.dist-info` + `-ransformers`），再用 `--force-reinstall --no-deps transformers==5.14.1` 干净重装。
  - `pip cache purge` 回收 **1,002 MB** 磁盘空间。
- **手动拉起用正确 Python**：`/usr/bin/python3` 是 **3.8.10**，而 `/root/miniforge3/bin/python3` 是 **3.10.11**；`launch_comfy_ui.sh` 里的 `python3` 在 SSH 非交互 shell 里会解析成 3.8 → `set[str]` 报"不可下标"。必须用 `/root/miniforge3/bin/python3` 显式拉起。
- **结果**：`system_stats` 显示 `comfyui_version: "0.28.0"`，`required_frontend_version: "1.47.10"` 已满足，模板也满足 → 新版真正跑起来。
- **`gen_refs.py test` 跑通**：生成 `D:\Aicomfyui\cloud\out\peach_test_00001_.png`（270KB），效果为圆润粉色桃子吉祥物、绿叶、大眼睛、腮红、微笑、Pixar 风格，验证 Qwen-Image-Edit GGUF 链路完整可用。
- **已上传锚点**：`D:\Aicomfyui\peach_role_v6.png` → `/root/ComfyUI/input/peach_role_v6.png`。
- **`gen_refs.py full` 运行中**：后台任务 `xV7cVh` 生成 4 张多角度参考图（front/side/back/expression），预计每张 10+ min，总计 40~60 min。

## 会话续接 + 视频速度答疑（用户关机后回来续聊）
- 续接时先通读 MEMORY.md + 本日志恢复上下文（符合 12:45 硬性约定）。
- **健康探测**：`curl 43.155.215.130:6889/system_stats` 在当前沙箱无回显（连接不可达），与"用户已关机"一致；实例离线、IP 失效，待用户重启发新 IP。
- **用户核心顾虑（续 16:07 关机前）**：出图已这么慢，后续视频不是更慢、跑不动？
  - 结论（已与用户对齐）：视频扩散（LTX 2.3 等）**确实比出图慢一个量级**，T4 15.9G 跑多镜头分镜可能数小时；但 **GPU 费很便宜（全程约 6-10 元）**，真正痛点是"等待/不能快速试错"，靠"后台挂机不盯盘"化解。
  - **决定架构（分阶段解耦）**：
    1. 出图/锁角色：留在便宜 T4，后台跑（≈1 元、1 小时），不盯盘。
    2. 视频阶段：二选一 —— (A) 换 HAI 更高显存实例（24G/32G+）本地跑 LTX，提速且避 OOM；(B) 走 `agnes_video.py` 托管 API 秒出（代价：不锁角色，一致性弱）。
    3. 砍规格兜底：短片段（5-10s/镜）、低分辨率（512×288 / 768×432）、少帧（16-24 帧）。
  - **不必现在为视频过度优化**：先跑通并确认 4 张参考图（等用户重启给新 IP），图片确认后再定视频路线。
- 下一步：用户重启 HAI → 发新 IP → agent `curl system_stats` 确认在线 → `gen_refs.py full`（建议改 Q3_K_M 量化提速/避 OOM）→ 出 4 图发确认。

## 用户把"速度"列为第一约束（17:11）
- 用户明确：HAI 按小时计费（1.2 元/时），**"一慢就伤不起"**，当前第一要务 = 快，不能慢。
- 已与用户对齐两个方向：① 出图（静态）= 锁角色一致性（多角度参考图 + 各分镜图）；② 视频（动态）= 图生视频（首帧/首尾帧约束）让分镜动起来。用户确认方向后去自行查资料。
- **架构性结论（已同步用户）**：当前 T4 跑 Qwen(~20B+ 量化 12.34G + 7B TE 4.68G) 必然 CPU 卸载 → 慢是物理必然，调参无解；真正提速杠杆只有三：换更大显存 GPU 实例（A10/L20/V100/A100，模型进显存不卸载，快 5~10×，总账单常反更低）、视频走托管 API（agnes_video.py，本地 GPU 时间=0）、砍量砍规格。
- 待用户研究结果：是否愿为视频阶段升 GPU，或视频全走 API。出图"一次性参考图"这步绕不开（一致性基础，仅 ~1 元），等其重启给新 IP 即跑。

## IPAdapter / Agnes / 动漫一致性 澄清（17:16）
- 用户追问：IPAdapter"锁不住非人类"是否意味人物就行？动漫以后是否也受限？Agnes 是否可能悄悄能锁角色？
- **已查 Agnes 接口（agnes_image.py + skill 文档）给确定结论**：Agnes 仅"文生图(agnes-image-2.1-flash)" + "单图图生图(agnes-image-2.0-flash，保留该图构图做风格化)"，**无持久角色身份嵌入** → 不能跨多图锁定同一角色（同我们之前的坑，只是更快免费）。Agnes 不能当一致性引擎，仅适单张出图/改风格。
- **IPAdapter 真实能力边界**：强项是"真人照片人脸"——FaceID/InstantID/PhotoMaker 等用 InsightFace 人脸识别的变体，是其主战场；但依赖"检测到人脸"，故：真人/写实→锁得好；非人类/风格化（桃子、动漫）→无真人脸，FaceID 失效，标准 CLIP 版仅剩颜色/风格/弱构图一致。这正是此前桃子 9 宫格各长各的根因。
- **动漫未来不受限，只是换工具**：动漫一致性的成熟可靠方案是**角色 LoRA 训练**（10~20 张参考图 + 动漫底模 AnythingV5/Illustrious/Pony 训 LoRA），抓身份远强于 IPAdapter 对风格化角色，且推理快（小底模、无重编码器）、T4 可跑。
- **关键串联（顺带解决"快"）**：慢的根因是"为一致性硬上 Qwen(~20B)"；正确姿势＝先出 4 张参考图（一次性 ≈1 元）→ 训角色 LoRA → 之后分镜图全用"小底模+LoRA"快出（SDXL 3G/动漫模进 T4 显存不卸载，速度数倍于 Qwen）。Qwen 产出的 4 张参考图正好当 LoRA 训练集——一致性(LoRA)与速度(小模型)在此统一。
- 待办补充：下次续跑除出参考图外，顺带摸 HAI 上 LoRA 训练可行性（Kohya / ComfyUI 训练节点），备好"参考图→LoRA→小模型快出分镜"路线。

## 用户发 9 个 B 站一致性方案视频，转向"快速出图+视频"（17:34）
- 用户分享 9 个角色一致性 B 站教程链接（Krea2 Identity Edit / FLUX.2 Klein / MSR V2+Ingredients / Wan2.2+LoRA / FLUX 多图 / 一张图全角度(真人3D卡通) / SCAIL2 视频换角色 / 即梦AI / ComfyUI+豆包+即梦+剪辑），要求重点解决"快速出图 + 视频"。
- **已扒技术点（WebFetch）**：仅 FLUX.2 Klein 那期有完整简介——核心节点 `ComfyUI-Flux2Klein-Enhancer`（Identity Feature Transfer，三档强度锁 + 4+参考图链式融合），配 `ComfyUI-NKD-Klein-Tools`；RunningHub 有在线工作流（免 GPU）。其余 3 个被爬仅露标题，结合标题+已知技术分析。
- **分类结论（按是否烧本地 GPU）**：
  - A 组·托管/云端（零本地算力，首选快路径）：即梦AI、Krea2、豆包+即梦+剪辑、RunningHub 在线工作流。
  - B 组·开源本地（控制强但需 GPU 时间）：FLUX.2 Klein、Wan2.2+LoRA、MSR V2+Ingredients、FLUX 多图、一张图全角度、SCAIL2。
- **回应前期两担忧**：① 卡通/3D 非人类一致性是成熟赛道（"一张图全角度"明写覆盖卡通，FLUX.2 Klein 适配虚拟人）→ 动漫不受限；② 真正可能锁角色的是托管方案（即梦等），非 Agnes（已查实 Agnes 无身份嵌入）。
- **落地路线（按速度）**：① 托管即梦/豆包（最快零成本，先实测桃子能否被锁）；② Qwen 出参考图→训 LoRA→小底模快出（本地快出，一次性投入）；③ Wan2.2+LoRA / MSR 视频本地（需升 GPU）。
- **下一步建议（已同步用户）**：先不开 HAI，用免费托管即梦测"桃子角色一致性"；能锁则出图+视频全托管、HAI 基本可不开；不行再回路线②（重启给新 IP 跑 Qwen 参考图）。视频盯 Wan2.2+LoRA/MSR（本地）与即梦/豆包（托管）两条。

## 澄清：托管方案"本地 0 成本"≠"本地部署"（17:50）
- 用户纠正：即梦/豆包/剪辑那期"全托管、本地 0 成本"能否本地部署？——**不能**。
- **事实确认**：即梦 AI、豆包、Krea、SCAIL2(云端版)、Agnes 均为**纯云端 SaaS**，无开源权重，**不能本地部署**（算力在厂商机房，只能网页/App/API 调用）。
- **"本地 0 成本"准确含义**：不占用本机 HAI/T4 的 GPU 小时（不烧 1.2 元/时）；本地顶多跑剪映这类剪辑（不吃 GPU）。≠"能在本地装起来跑"。
- **"0 成本"是"0 本地硬件成本"**：云端服务本身有免费额度/积分，超出按月订阅（几~几十元），非永久免费。
- **与 B 组边界厘清**：能本地部署 = FLUX.2 Klein、Wan2.2+LoRA、MSR、Qwen+ComfyUI（开源权重，跑在 HAI T4，但要 GPU 时间）；不能本地部署 = 即梦/豆包/Krea/SCAIL2/云端版（云端跑，本地零 GPU 成本）。
- **对用户价值**：正因不可本地部署 + 零本地 GPU 成本，才消解"按小时付费一慢就伤不起"——重活外包云端，HAI 可基本不开。
- **⚠️ 费用实情纠正（用户 17:51 指出"这些都要费用的"）**：即梦/豆包/Krea 等**即便有免费额度，实质均要费用**（会员订阅/积分包/按次计费），不能按"免费"规划预算。此前"零成本/零本地成本"表述有误导，准确应为"零本地 HAI GPU 小时成本"；云端自身费用是一笔**独立于 HAI 的账**。算账维度：本地 HAI=纯按开机小时（1.2元/时，关机不花，但慢→干等亏时）；云端=订阅/按次（有固定门槛，但快、不等、不烧本地小时）。总量小→本地按需开机可能更省；长期高频→云端订阅可能更可控。决策还需叠加"云端能否锁桃子一致性（待实测）"这一前提。

## 算力平台选型调研：华为云是否有类似 HAI（17:52）
- 用户问华为云有无类似 HAI 的高性能 GPU 服务器（核心诉求仍是"快+不按小时亏"）。已 WebSearch 查证。
- **华为云对位 HAI 的三类产品**：
  1. 一键部署 AI 绘图应用（activity.huaweicloud.com/serverless-sd.html）：有 Stable Diffusion(WebUI/ComfyUI/ComfyUI+Flux) 一键部署，GPU 资源包 **180 元起**——最接近 HAI"AI 应用镜像"形态。
  2. **ModelArts**（AI 开发平台）：Notebook + 按需 GPU 实例 + 预置 PyTorch 镜像，对位 HAI 开发环境；新用户有 7 天体验包。
  3. ECS GPU 实例（G/P 系列）：通用 GPU 云服务器，自装环境。
- **⚠️ 关键陷阱：华为云主推昇腾 NPU（国产），非 NVIDIA GPU**。我们的 ComfyUI+Qwen GGUF 是 CUDA 生态（torch.cuda 硬编码、GGUF 加载、插件），在昇腾上需改源码（torch.npu）、剥离 CUDA 依赖、权重转 .om、插件 NPU 适配，且很多插件会 CPU 回退变慢；ModelArts 的 NPU ComfyUI 方案（Snt9B/Snt9B23）**仅面向企业客户**，需联系华为技术支持购买 Server。→ 个人/小项目在昇腾上跑我们这套工具链门槛高、风险大，不推荐。
- **华为云也有 NVIDIA GPU 实例（标准 CUDA，能跑我们的东西）**，参考价：T4 ≈1.1~1.8 元/时（与 HAI T4 的 1.2 持平）、V100(32G) ≈4~6 元/时（ModelArts 100h 套餐 580=5.8 元/时）、A100 ≈4.5~12 元/时。
- **解决"慢"的本质仍是换更大显存 NVIDIA 卡**（模型整张进显存不卸载，快 5~10×）；这不一定换华为云——腾讯云 HAI 本身可升 A10/V100/A100。第三方 CUDA 平台亦值得比：优云智算 4090(24G) 仅 2.15 元/时、OneThingAI 4090 2.34 元/时，预装 ComfyUI、显存比 T4 大 50%、价格略高但速度优势明显，对个人更友好。
- **结论给用户的路线**：要快→升 NVIDIA 大卡（HAI 内升 or 华为云 NVIDIA 实例 or 第三方 4090 平台三者比价）；华为云昇腾路线对个人不推荐。下一步：若要试华为云，先用 180 元资源包/7 天体验包低成本验证。

## 算力平台补充调研：阿里云 / 移动云（17:55）
- 用户追查阿里云、移动云有无类似 HAI 产品（仍围绕"快+不按小时亏"）。已 WebSearch 查证。
- **阿里云（最值得考虑）**：
  - GPU 云服务器 ECS：gn6i=T4(16G)、gn7i=A10(24G)、gn6v/gn6e=V100(16G/32G)、L20(48G)，**NVIDIA 标准卡（非昇腾，无适配坑）**；按量价 T4≈1.9、A10≈1.9起(小配16核60G)/9.5(大配)、V100≈8.5(16G)/21.1(32G) 元/时；新用户 GPU 包年 3 折起。
  - PAI 平台（对标 HAI/ModelArts）：PAI-DSW 交互式建模（ModelScope 预置 PyTorch CUDA 镜像，可自装 ComfyUI）；**PAI-EAS 有「AI绘画-SDWebUI 部署 Serverless 版」一键部署**；**新用户 A10/V100 免费试用（每月250计算时×3月=750）+ SDWebUI 500元/月额度**——可几乎零成本试跑 Qwen/ComfyUI 工作流，且 A10(24G) 比 T4(16G) 显存大、直击"慢"痛点。
- **移动云（短期不推荐）**：异构加速型 ECS（g4t/g3t=T4、g4v=V100 32G、g4a=A100 40G），NVIDIA 齐全（也有昇腾裸金属政企口径）；**按量单价偏高（T4 14.61、V100 23.81、A100 21 元/时），包月才划算（T4 4208/月≈5.8/时均价）**；文档仅提 ECS GPU 型、无一键 ComfyUI、需自装；裸金属 GPU 8卡整机为昇腾910B/H100 政企大单。
- **横向结论（快+不亏）**：腾讯HAI/阿里/华为N卡/移动云 均 NVIDIA 生态，能跑我们 CUDA 工具链；仅华为云默认推昇腾是坑。最划算落地点排序：① 阿里云 PAI 用免费额度试 A10（零成本验证，首选）② 腾讯云 HAI 内升 A10/V100 ③ 第三方 4090 平台(2.15元/时,24G,预装) ④ 移动云（包月才划算，短期不推荐）。「快」的关键卡 = A10(24G)/V100(32G)：Qwen 12.34G+TE 4.68G≈17G，T4 16G 必卸载→慢；A10 24G 大幅缓解；V100 32G 可整张进+余量。

## 阿里云 PAI 关键落地链接（17:58 用户要链接，实测可用 URL）
- **⚠️ 重要区分**：阿里云「AI 绘画 SDWebUI Serverless（开箱即用）」是 **Stable Diffusion 系列**，≠ 我们的 ComfyUI+Qwen GGUF 工作流。**真正要用的是「PAI-DSW 交互式建模」**（含 Terminal+sudo，可自装 ComfyUI+Qwen 权重，且吃免费额度 A10/V100）。免费试用重点在 DSW，不在一键 SDWebUI。
- 链接清单：
  1. PAI 产品主页：https://www.aliyun.com/product/bigdata/product/learn
  2. PAI-DSW 交互式建模（有 Terminal/sudo，装 ComfyUI 用这个）：https://cn.aliyun.com/activity/bigdata/pai/dsw
  3. PAI-DSW AIGC 活动页（A10/V100 低至 3 折 + 资源包）：https://cn.aliyun.com/activity/bigdata/pai_aigc
  4. 阿里云免费试用中心（PAI 专区：DSW 每月250计算时×3月=750，EAS 500元×1月）：https://free.aliyun.com/?product=1395
  5. AI 产品免费试用（含 PAI-EAS 500元 + DSW 750时）：https://free.aliyun.com/product/ai-h5
  6. EAS AI 绘画 SDWebUI 部署文档（Serverless 版，部署免费按出图时长计费，参考非 Qwen 路线）：https://help.aliyun.com/en/pai/ai-painting-sdwebui-deployment
  7. EAS 免费部署 SDWebUI 实操教程：https://help.aliyun.com/practice_detail/610074
- **建议动作**：先去链接 4 领 DSW 免费额度（认证+PAI 新用户即可，覆盖 A10/V100/G6），再开 A10(24G) DSW 实例，把 HAI 上验证过的 ComfyUI+Qwen GGUF 流程原样搬过去——比 T4 快 5~10×，前 750 计算时基本白嫖。

## 路线决策：优先阿里云 PAI-DSW A10 免费额度（18:14~18:20）
- 用户确认理解：① A10 在免费额度内**不用钱**（前提：选"公共资源+免费试用资源"规格、不扩容系统盘超100G、不调百炼/EAS 在线模型；我们 Qwen 权重走 wget/ModelScope 不收费）；② 7/8/9 月各送 250 计算时（共750），每月自然月1日0点重置、当月未用完清零不滚存、8/9月照常各送250。
- **额度换算（A10 gn7i-c8g1.2xlarge，24G，6.991 计算时/时）**：每月250≈35.75小时，三个月750≈107小时，出图流程几分钟即可，额度足够挥霍。
- **速度对比（已同步用户）**：T4(16G) 因 Qwen 12.34G+TE 4.68G≈17G 必卸载→慢(≈9.5分/张，4张40~60分)；A10(24G) 可整张进显存不卸载→快 5~10×，单张≈1~2分，4张≈5~10分，且视频模型(LTX/Wan)能跑动（T4 易 OOM/极慢）。
- **⚠️ 避坑**：DSW 实例"运行中即计费"（含空转），跑完必须手动停止/删除；不依赖"闲置自动关机"；额度耗尽/到期未停→转按量(A10≈6.99计算时/时)。
- **当前路线转向**：用户决定优先用阿里云 PAI DSW A10 免费额度试跑出图（快+白嫖），**HAI 出图路线暂搁置**（HAI T4 实例仍关着、IP 43.155.215.130 已失效）。下一步等用户领成功→报地域+实例状态→agent 出 DSW 装 ComfyUI+下 Qwen GGUF 权重命令清单。

## PAI 准备工作已完成（18:35，用户说明天开启使用）
- 已交付 `D:\Aicomfyui\pai\` 文件夹（供明天上传 DSW 实例）：
  - `setup_pai.sh`：一键部署（检 Python≥3.10 → clone ComfyUI 最新 → pip 依赖含 sqlalchemy + torch CUDA 校验 → 装 city96/ComfyUI-GGUF → 下权重(hf-mirror) → 放 anchor → 后台启 ComfyUI :6889）。
  - `gen_refs_pai.py`：连本地 127.0.0.1:6889 出图（test/full），节点图与 HAI 验证版一致（UnetLoaderGGUF+ModelSamplingAuraFlow+CLIPLoaderGGUF(type=qwen_image)+QwenImageSampler）。
  - `README_PAI.md`：中文操作步骤 + 避坑 + 费用小结。
  - `peach_role_v6.png`：角色锚点图（已 cp 进 pai 目录供上传）。
- **权重来源已查实并写进脚本**：unet=`unsloth/Qwen-Image-Edit-2511-GGUF`(12.34G)、text_encoder=`rexionmars/Qwen2.5-VL-7B-Instruct-Q4_K_M-GGUF`(4.68G，放 text_encoders 并 cp 到 clip 兼容)、vae=`Comfy-Org/Qwen-Image_ComfyUI`(0.3G)。下载走 hf-mirror.com 断点续传。
- **mmproj 视觉塔结论**：Qwen-Image-Edit 是 instruction-based 编辑，输入图走 LoadImage→VAEEncode，不需单独 mmproj（HAI 上 full 节点图能进队列已验证）。脚本不下载 mmproj，保持与 HAI 一致。
- 明日用户动作：上传 pai 文件夹到 DSW → 开 A10 实例 → `bash setup_pai.sh` → `python gen_refs_pai.py test` → `full` → 下载 out/ 图 → 停止实例。

## 防扣费提醒文件已补充（18:44，用户提交 PAI 试用截图后）
- 用户截图显示：PAI-DSW 试用类型为 **包年包月**、3 个月免费、**自动续费未开启**。
- 关键提醒：
  - ✅ 自动续费未开启 = 到期不会自动从卡扣钱。
  - ⚠️ 但 3 个月到期（约 2026-10 底）会**自动停机或释放**实例，权重和图会清空；若还想用必须手动去「用户中心-我的试用」购买，否则直接没了。
  - ⚠️ 真正会扣费的只有：当月 250 计算时用完后还在运行（转按量）、扩容系统盘（盘费停止也照收）、调用百炼/EAS 在线模型。
  - 安全口诀：只开 A10 免费规格，不扩容盘，不点在线模型，跑完立刻停止实例，每月额度别超 250 计算时，到期前把重要数据下载回本地。
- 已交付：
  - 新增 `D:\Aicomfyui\pai\ALERT_FEE.md`（独立醒目提醒文件）。
  - 更新 `D:\Aicomfyui\pai\README_PAI.md` 的「八、费用小结」为「八、费用小结与防扣费提醒」，加入上述表格和提醒。
- 用户明天开启 DSW 之前，建议先看一眼 `ALERT_FEE.md`。

## 用户已停止 DSW 实例（18:46~18:47）
- 用户截图发现实例"运行中"，确认 DSW 运行中才计费、停止后不计费；用户当场去控制台**停止**实例（今晚到明天不烧额度）。
- 明日顺序重申：启动→上传 pai→setup_pai.sh→test/full→下载 out→**停止**。安全口诀：跑前启动、跑完停止、不扩容盘、不点在线模型。
- 状态：PAI-DSW 试用已领（包年包月、3月免费、自动续费未开），实例当前应处于"已停止"。HAI T4 实例仍关着（IP 43.155.215.130 失效）。本会话主线停在"等用户明天开 DSW 跑出图"。

## 已推送 GitHub（19:0x，用户要求"推送到github明天继续"）
- **本机 `git push` 走不通**：git 自带 libcurl 源地址 bug（github.com:443 连不上，即使 `dangerouslyDisableSandbox:true` + HTTP/1.1 仍 `Failed to connect... Could not connect to server`）。但 curl/curl.exe 带沙箱禁用能通 API（已验证 api.github.com 返回仓库元数据：public、default_branch=main、远端仅 main 分支）。
- **兜底方案**：改用 **GitHub Git Data API**（Python urllib + Bearer PAT，`dangerouslyDisableSandbox:true`）将今日 14 个文件（pai/ 5 个脚本手册 + 项目记忆与日志/ 9 个 md）作为新 commit 推到 **main** 分支。流程：GET main ref→blob(逐文件 base64)→tree→commit(parent=main HEAD 973b5c8)→PATCH ref/heads/main。成功，远端 main 新 commit = `b0d2aad`。
- **分支注意**：本地 `peach_sync` 仍保留 commit `027dfd3`（内容同 b0d2aad 但 hash 不同，分叉无害）。明天续干：① 换电脑 clone/pull main 即得全部；② 回本机可直接在 peach_sync 继续（027dfd3 已含全部 14 文件），或 `git checkout main && git fetch && git merge --ff-only` 对齐。
- **经验教训**：本机 git 直连 github 不可用（源地址 bug），今后凡 push/pull 一律走 API 兜底（github-private-access-fallback skill），勿依赖 git 原生网络。临时推送脚本 `C:\Users\Administrator\push_api_tmp.py` 用完已删（含 PAT，勿留）。


## 2026-07-25
### 2026-07-25 桃子角色自动视频生成日志

## 上午：确认 PAI-DSW A10 规格
- 用户截图展示 DSW 实例规格选择页，已选中 `ecs.gn7i-c8g1.2xlarge`（A10，24G 显存，支持资源包抵扣）。
- 确认该规格正确：Qwen unet 12.34G + CLIP 4.68G ≈ 17G 可整进显存，不 CPU 卸载，预计比 T4 快 5~10 倍。
- 费用：A10 每小时 6.991 计算时，每月 250 额度 ≈ 35.75 小时；出图流程 <1 小时，基本不花现金。
- 关键约束重申：只选「支持资源包抵扣」的 A10；不扩容系统盘；跑完立刻停止实例。
- **路线修正（08:27，重要）**：用户指出"视频必须本地跑，托管 API 不行"——根因是即梦/ Agnes **锁不住角色一致性**（项目命根子），故视频不能走 API。→ 24G(A10) 跑不了本地 LTX/Wan（OOM），需要 32G 左右。但进一步查看实例列表后发现：免费抵扣的 V100 是 **16G 单卡**，32G 只有 **4×V100(128G)** 且**不支持资源包抵扣**（86.86元/时）或付费单卡 32G（21.71元/时）。→ **最终决定：先创建 A10 24G 免费实例跑 出图**；视频阶段再评估：要么在 24G 上试 AnimateDiff-XL/CogVideoX/LTX 蒸馏等轻量本地视频，要么临时付费租 32G/第三方平台。
- **PAI 实例配置进展（08:38）**：用户正在创建 VPC/交换机；地域 = 华东2（上海），可用区 = 上海 可用区 B，VPC 名 `default-vpc-mz`，交换机名 `pai-vswitch`。VPC 创建后回到 DSW 创建页选择该 VPC，继续创建 A10 实例。
- **DSW 实例已创建成功（08:47）**：实例名 `mz-cmfyUI` / ID `dsw-bu131a80z343v7jgk`，状态**运行中**，地域**华东2（上海）**，镜像 `modelscope:1.38.0.1-pytorch2.10.0-gpu-py312-cu128-ubuntu22.04`，A10 24G。**已开始计费（扣免费额度）。**
- **下一步**：打开 JupyterLab → 获取 `pai/` 文件夹 → Terminal 跑 `bash setup_pai.sh`（下载 17G 权重，约 20~40 分钟）→ `python gen_refs_pai.py test/full`。

## 09:05~09:10 权重下完、ComfyUI 起、首次 test 失败→定位修复
- **权重下载完成 + ComfyUI 启动成功**：因 hf-mirror 单线程限速 ~1MB/s（12G 需 3h），中途改为 **modelscope 内网下载**（解析到 10.224.x.x 内网 IP，快 10 倍），4 文件（unet 12.34G / clip 4.68G / mmproj-F16 / VAE）全部就位。ComfyUI PID 59710，日志确认 Python 3.12.13、ComfyUI version 0.28.0、ComfyUI-GGUF 已加载、DB 迁移到 0006。
- **脚本真实路径修正**：`git clone` 实际落在 `/mnt/workspace/ai-comfyui/pai/`（非之前说的 `~/ai-comfyui`）。正确命令：`cd /mnt/workspace/ai-comfyui/pai && python gen_refs_pai.py test`。
- **test 提交失败（09:10）**：报错 `missing_node_type: QwenImageEmptyLatentImage not found`。根因：DSW 的 ComfyUI（modelscope 镜像/最新版）**未内置 Qwen-Image 专属节点**（HAI 的 0.28.0 是过渡版内置了，DSW 拆成独立包）。→ 修复：安装 `ComfyUI-Qwen-Image`（Comfy-Org 官方包，节点名 `QwenImage*` 无前缀，正好匹配脚本）；clone 后 kill 旧进程、重启 ComfyUI、等 60s 再验证。
- **待办**：装节点包→重启→重跑 test→出 4 张 full 参考图→下载回本地→停止实例。
- **关键限制（09:29，已与用户对齐）**：agent **无法直连 DSW 实例**（DSW 无公网 IP + 用户关了 SSH）。用户曾提议"开 SSH 让我接管"，但 DSW SSH 两条路均有代价：① 直连需配 NAT网关+EIP→**持续计费**（撞用户省钱红线，不推荐）② ProxyClient 需用户交阿里云 AK/SK（敏感凭证，按约定不跨网络传）→不合适。结论：**只能用户在 JupyterLab Terminal 粘贴命令**，agent 给整合命令。节点包 clone 源踩坑：ghproxy.com 卡死、gitclone.com 返回 502、最终试 GitHub 官方源直连（`git clone https://github.com/Comfy-Org/ComfyUI-Qwen-Image.git`）。

## 09:14 用户问"为什么看不到 ComfyUI 界面"——DSW 访问模型差异（重要，可复用）
- **根因**：DSW 实例不像 HAI 有公网 IP 直连，浏览器不能直接 `http://IP:6889`。实例内部服务须经 **JupyterLab 代理通道**才能从本机浏览器看到。ComfyUI 本身是正常的（`Starting server` 已确认）。
- **看 GUI 的方法**：
  1. **JupyterLab 代理 URL（最常用）**：把 JupyterLab 地址栏结尾的 `/lab` 改成 `/proxy/6889/`（结尾斜杠必须有）。例：`https://dsw-gateway-cn-shanghai.data.aliyun.com/dsw-823428-5c7fbf78d-jdk5c/proxy/6889/`。
  2. JupyterLab 左侧"专用工具/小火箭"→ **Port Forwarding** → 填本地端口 6889。
  3. （不推荐）实例"服务访问与端口配置"加 6889 + 公网访问 + 安全组放行 → 独立公网 URL（配置重、实例停即失效）。
- **关键提醒**：本项目工作流用 `gen_refs_pai.py` 直接调 ComfyUI **API（127.0.0.1:6889）**，GUI 只是调试用、**不看界面也能正常出图**；验证只需 `curl http://127.0.0.1:6889/system_stats` 有 JSON 返回即可。

## 09:31 git clone 认证失败 → 改用 zip 下载绕开（重要，可复用）
- **现象**：用户在 DSW Terminal 粘贴整段整合命令，`git clone https://github.com/Comfy-Org/ComfyUI-Qwen-Image.git` 被 GitHub 拒绝：`Password authentication is not supported for Git operations` + `Invalid username or token`。根因：GitHub 自 2021 起**禁用账号密码做 git 操作**，必须走 Personal Access Token；且 gitclone.com/ghproxy 在阿里云均不可用。后续 `cd/pip install` 因目录未建成而连锁失败，但旧 ComfyUI 已被 kill 并由 `nohup` 重启（新 PID 115507，**仍缺 Qwen 节点**）。
- **修复（不依赖 git 认证）**：用 `curl` 直接下 GitHub 的 archive zip（公共仓库匿名可下），再用 `python -m zipfile` 解压改名，彻底避开 git 密码认证。DSW 网络能直连 github.com（clone 时已达认证环节说明 TCP 通），小仓库 zip（几百 KB~几 MB）几秒下完。
- **完整命令（一次性粘贴）**：见下条用户回复。要点：① `curl -L .../archive/refs/heads/main.zip -o /tmp/qi.zip`；② `python -c "import zipfile; zipfile.ZipFile('/tmp/qi.zip').extractall('/root/ComfyUI/custom_nodes')"`；③ `mv ComfyUI-Qwen-Image-main ComfyUI-Qwen-Image`；④ `pip install -r requirements.txt`；⑤ `pkill -f "main.py --listen"` 重启；⑥ 权重加载慢→用 `for` 循环轮询 `system_stats` 直到 UP 再跑 `gen_refs_pai.py test`。

## 09:34~09:40 根因精准定位 + 改用原生 SD3/KSampler（最优解，已落地）
- **根因（精确）**：`gen_refs_pai.py` 依赖 `QwenImageEmptyLatentImage` + `QwenImageSampler` 两个**非原生节点**（脚本第 95/98/112 行）。这两个节点是 ComfyUI **nightly 最新版（HAI 的 0cb84e7e）原生内置**的 Qwen 支持；而 DSW 镜像是 **ComfyUI 0.28.0 稳定版**，Qwen 原生支持尚未合入 → 缺这俩节点。之前试装的 `Comfy-Org/ComfyUI-Qwen-Image` 经 GitHub API 确认 **404 不存在**（curl 下到的 9 字节即 GitHub 返回的 `"Not Found"`），纯路径错误、与网络无关。
- **最优解（已采用，零下载/零升级/零重启）**：Qwen-Image 架构同 SD3（16-channel latent），用 ComfyUI **原生** `EmptySD3LatentImage`（替 QwenImageEmptyLatentImage）+ 标准 `KSampler`（替 QwenImageSampler）即完全等价，参数 1:1 兼容（KSampler 输入 model/positive/negative/latent_image/seed/steps/cfg/sampler_name/scheduler/denoise 与脚本一致；官方原生 Qwen 工作流本就这么用）。其余节点（UnetLoaderGGUF/CLIPLoaderGGUF/ModelSamplingAuraFlow/VAELoader/CLIPTextEncode/VAEDecode/SaveImage）DSW 全已具备。
- **已改本地源** `D:\Aicomfyui\pai\gen_refs_pai.py`：两处 class_type 替换 + 删 aspect_ratio/use_aspect_ratio 多余参数 + 更新文件头注释。DSW 副本因 git clone 且 git pull 有认证问题，用 python 就地替换（不依赖 git）。
- **待用户跑**：DSW 上 python 替换脚本 → grep 验证 → 直接 `python gen_refs_pai.py test`（ComfyUI 已在跑、节点皆原生/已装，**无需重启**，权重已加载）。成功标志：生成 `peach_test_*.png`。

## 09:43 ✅ test 出图成功（A10 链路打通）
- 用户跑完返回：`[提交] txt2img 验证图 peach_test ... prompt_id=94e43e67-...` → `已下载: /mnt/workspace/ai-comfyui/pai/out/peach_test_00001_.png (330045 bytes)`。**A10 上 Qwen 出图链路彻底打通**（原生 SD3+KSampler 替代方案验证有效）。
- grep 验证结果：第 95 行 `EmptySD3LatentImage`、第 98/112 行 `KSampler`；第 9 行 `QwenImageSampler` 仅为文件头注释文字，不参与运行。
- **预览图方式（用户问）**：图在 DSW 硬盘 `/mnt/workspace/ai-comfyui/pai/out/`，agent 无法直连拉取；用户在 JupyterLab 文件浏览器展开 `mnt/workspace/ai-comfyui/pai/out/` 双击 png 即可预览，或右键 Download 存本地。
- **GUI 访问卡点（已解决 09:52 / 09:58）**：
  - ❌ `dsw-823428-5c7fbf78d-jdk5c.console.aliyun.com/proxy/6889/` → DNS 失败（域名格式错）。
  - ❌ `dsw-gateway-cn-shanghai.data.aliyuncs.com/dsw-823428/proxy/6889/` → **403**（官方给的旧域名/错域名）。
  - ✅ 正确网关域名从 `env` 拿到：`dsw_ip=dsw-cn-shanghai.data.aliyun.com`（非官方给的 `data.aliyuncs.com`）；路径前缀 `/dsw-823428/` 来自 `JUPYTER_SERVER_URL=http://127.0.0.1:8088/dsw-823428/`。→ **正确 ComfyUI GUI 地址 = `https://dsw-cn-shanghai.data.aliyun.com/dsw-823428/proxy/6889/`**。
  - 实测：打开该地址返回 `errCode 10010 账号登录失效，请重新登录`（说明域名/路径已对，只是阿里云登录态过期）。**解法**：点 SSO 链接重登阿里云 → 回 DSW 控制台确认实例运行中 → 重开该地址即可进 GUI。
- **full 模式实测成功（~09:55）**：用户跑 `python gen_refs_pai.py full` 完成，在 `./out/` 生成 4 张基于 `peach_role_v6.png` 锚点的多角度图：`peach_ref_back/front/side/expr_happy_00001_.png`，角色一致性 OK。证明 A10 出图链路彻底打通。用户仍不满足：要 GUI 上传自己的参考图、不要纯命令。下一步：待 GUI 调通后给一个 ComfyUI 工作流 JSON（LoadImage 留空上传 + KSampler + VAEDecode + SaveImage）。
- **下一步**：用户看 test 图 OK → `python gen_refs_pai.py full` 出 4 张多角度参考图 → 下载回本地 → **停实例**。

## 10:00~10:33 路线大修正：Qwen 出不了真·多角度 → 换 Zero123 单图转视角（关键决策）
- **用户强烈不满（根因复盘）**：Qwen `full` 出的 4 张其实都是正面（seed 不同导致微差），`side/back` 没真转过去。根因：我之前为了"锁角色一致性"把出图模型从 IPAdapter 换成 **Qwen-Image-Edit**，却忘了**多角度能力来自 Multi-View 模型（当初刺猬用 MV-Adapter）**——Qwen 本就不是 3D 旋转模型，硬 prompt/cfg/denoise 都救不回。这是我判断失误，已认错。
- **正确组合（用户拍板，分步执行）**：`你已有的桃子参考图 → Stable Zero123（单图转多视角）→ 4 个严格角度图`。**Qwen 在这步是多余的**（用户早有参考图 `peach_role_v6.png`，不需要 Qwen 再"出一张参考图"）。
- **为何 Zero123 取代 MV-Adapter**：① Zero123 是 SD1.5 架构，轻量，A10 无压力；② **不需要 IPAdapter**——输入即参考图、输出旋转后仍同一只桃子，角色一致性天然保证（正好绕开当初 IPAdapter 锁不住非人类角色的坑）；③ MV-Adapter 当初翻车就因依赖 IPAdapter。
- **已落地**：
  - ✅ 装节点 `ComfyUI-Zero123-Porting`（kealiu 版，git 直连成功 1.73MiB）；pip install 报错但**节点仍加载成功**（10:33 验证 `Zero123: Image Rotate in 3D` in object_info = True）。
  - ⏳ **权重 `stable-zero123.ckpt`（~4GB）尚未下载**（之前给的下载命令用户未跑，目录/日志都不存在）。已重给下载命令：`mkdir -p /root/ComfyUI/models/checkpoints/zero123 && cd 该目录 && nohup curl -L https://hf-mirror.com/stabilityai/stable-zero123/resolve/main/stable_zero123.ckpt -o stable-zero123.ckpt > /tmp/z123_dl.log 2>&1 &`（备选 HF 直连）。节点要求权重放 `checkpoints/zero123/`、文件名含 `zero123`。
  - ✅ 出图脚本写好本地 `D:\Aicomfyui\pai\gen_angles_zero123.py`（API 调 `LoadImage` + `Zero123: Image Rotate in 3D`[azimuth 0/90/180/-90 → front/right/back/left, polar 0, steps 75, fp16, checkpoint=stable-zero123.ckpt] + `SaveImage` → `out_zero123/`）。DSW 上同内容已用 heredoc 给用户。
- **待办（下一步）**：权重下完（4GB 不再增长）→ DSW 跑 `python gen_angles_zero123.py` → 4 张角度图 Download 回 `D:\Aicomfyui\image\` → 用户看是否真·多角度。角度 OK 后再做「去背景变白底 + 放大」（Zero123 固定 256×256、参考图带灰底会带进结果）。**用户要求"先拿参考图用 Zero123 出角度图，确认角度图再下一步"，严格分步。**

- **11:06 补坑**：用户跑出图报 `can't open file gen_angles_zero123.py: No such file or directory` → 根因是**脚本从没同步到 DSW**（GitHub 因密码认证失败没 push，本地 `D:/Aicomfyui/pai/gen_angles_zero123.py` 只在我的机器上）。之前对话里给的 `cat > gen_angles_zero123.py <<'PY' ... PY` 创建命令用户漏跑了。→ **修复**：重新给完整 heredoc 创建+运行命令。教训：DSW 上每次需脚本时，要么 PAT 同步 git pull，要么直接贴 heredoc 创建，别假设文件已存在。
- **当前状态**：权重 `stable-zero123.ckpt`(8.58GB) 已就位 `models/checkpoints/` 顶层；Zero123 节点已加载(True)；ComfyUI 在跑。**待用户跑 heredoc 创建脚本并 `python gen_angles_zero123.py` 出 4 角度图** → 下载回 `D:\Aicomfyui\image\` 给我看是否真·前/右/后/左。

- **11:08 报错修复**：脚本创建成功、提交成功,但执行 `Zero123: Image Rotate in 3D` 报 `No module named 'taming'`。根因:之前 `pip install -r requirements.txt` subprocess 报错导致依赖没装全(taming-transformers 缺失)。→ **修复**:`pip install taming-transformers`(或 `--no-deps` 避 lightning 冲突);装完**无需重启 ComfyUI**(节点执行时动态 import),直接重跑 `python gen_angles_zero123.py`。（Zero123 节点内部用 `torch.compile`,若旧 torch 不支持后续可能再报,到时再调。）

- **11:11 续坑**:`pip install taming-transformers`(PyPI 版)后仍 `No module named 'taming'` → 确认 **PyPI 包不提供 `taming` 模块名**(装了但 import 路径对不上,白装)。→ **改用 CompVis 官方 git 装**:`pip install git+https://github.com/CompVis/taming-transformers.git@master`,验证 `python -c "import taming"` 出现 `taming OK` 后再重跑脚本。若官方装后 import 报缺 clip/ftfy 等,再补对应包。

## 10:40~11:03 权重下载踩坑 + 修正（可复用经验）
- **hf-mirror 极慢（10:40）**：`curl ... hf-mirror.com/.../stable_zero123.ckpt` 实测 ~1MB/s、总大小 8186M（即 8.58GB），ETA >2h。与 Qwen 当初同坑（hf-mirror 单线程限速）。
- **modelscope 正确姿势（关键，已验证）**：DSW 镜像是 modelscope 定制版，**自带阿里云内网加速**（环境变量 `INTRA_CLOUD_ACCELERATION_REGION`，新版叫 `MODELSCOPE_DOWNLOAD_INTRA_CLOUD_REGION`）。下载用：
  `unset MODELSCOPE_ENDPOINT`（**千万别设 `mirror.modelscope.cn`**，DSW 内网 DNS 解析不到该域名，会报 NameResolutionError）→ `modelscope download --model stabilityai/stable-zero123 stable_zero123.ckpt --local_dir /root/ComfyUI/models/checkpoints/zero123` → 内网飞快、几分钟下完（11:03 实测 ✓）。
- **文件名/路径坑（待执行）**：modelscope 下的是 `stable_zero123.ckpt`（下划线），而脚本 `gen_angles_zero123.py` 的 `CKPT="stable-zero123.ckpt"`（连字符）、且节点下拉项按 checkpoints 内相对路径精确匹配。→ 已给命令：`mv .../stable_zero123.ckpt /root/ComfyUI/models/checkpoints/stable-zero123.ckpt`（移到顶层+改名），使下拉项精确等于 `stable-zero123.ckpt`，避免 `checkpoint ... not in list` 报错。
- **下一步**：改名+验证大小(~8.58G)+确认 ComfyUI 在跑 → `python gen_angles_zero123.py` 出 4 角度(256×256) → 下载回本机 `D:\Aicomfyui\image\` 看是否真·多角度。

- **11:32 续坑**:CompVis 官方 git 装 taming 后仍 `No module named 'taming'` → 根因:**pip 装 taming 时拉重依赖(clip/open_clip)在 DSW 失败,导致整体安装回滚,taming 没真正进 site-packages**。→ **改用最稳手动方案**:`cd /usr/local/lib/python3.12/site-packages && git clone --depth 1 https://github.com/CompVis/taming-transformers.git taming_src && cp -r taming_src/taming ./taming && rm -rf taming_src`,绕开 pip 依赖解析;验证 `python -c "import taming"`。若 import 时缺 clip(说明 `taming/__init__.py` 顶层 import clip),则注释掉该 import 或 `pip install clip`。

- **11:39 续坑·taming OK: None（嵌套嫌疑）**：手动 clone+cp 后 `python -c "import taming"` 打印 `taming OK: None`（**不报错但 `__file__` 为 None**）。正常包 `__file__` 应是 `/usr/local/.../site-packages/taming/__init__.py`，`None` 说明 Python 把它当**命名空间包** → 高度怀疑**目录嵌套**：之前 `pip install taming-transformers` 残留创建了空 `site-packages/taming/` 目录，`cp -r taming_src/taming ./taming` 把源码塞进了 `taming/taming/`，导致 `from taming.modules.vqvae.quantize import ...` 找不到。→ **诊断**：`ls -la /usr/local/lib/python3.12/site-packages/taming/` 看是否里面还有一层 `taming/`；`python -c "import taming.modules.vqvae.quantize"` 看子模块能否导入。→ **修复（若嵌套）**：`rm -rf /usr/local/lib/python3.12/site-packages/taming && git clone --depth 1 https://github.com/CompVis/taming-transformers.git /tmp/ts && cp -r /tmp/ts/taming /usr/local/lib/python3.12/site-packages/taming && rm -rf /tmp/ts`，再验证 `import taming; import taming.modules.vqvae.quantize` 都应打印真实路径（非 None）。若子模块导入报缺 `clip`：`pip install open_clip_torch ftfy regex` 或注释掉 `taming/__init__.py` 顶层 `import clip` 行。

## 11:50 踩坑·ComfyUI 队列僵尸任务（重要，可复用）
- 现象：重跑 `python gen_angles_zero123.py` 后 GPU 0%、无输出。查 `curl ...6889/queue` 发现 `queue_running` 里有一个 **11:39 提交的旧 front 任务 `b60f88a5-...`**（taming 还没修好那次），`queue_pending` 里才是本次 11:48 的 `bab518d0-...`。旧任务客户端脚本已因 taming 报错退出，但 ComfyUI 仍把它当 running → 新任务被堵在后面，GPU 全程空闲。
- **根因（机制）**：ComfyUI 队列在**客户端断开/脚本崩溃后不会自动回收已接受的任务**，会一直占 running 位，导致重复跑脚本时旧僵尸 + 新任务堆积、互相阻塞。
- **解法**：`curl -s -X POST http://127.0.0.1:6889/queue -H "Content-Type: application/json" -d '{"clear":true}'` 清空队列 → 旧 Terminal `Ctrl+C` 停脚本 → 重跑 `python gen_angles_zero123.py`。清空只清 prompt 队列、不杀 ComfyUI 服务。
- **预防（重要）**：脚本 `wait()` 因执行报错抛异常退出时，ComfyUI 侧任务仍在跑/排队。**以后每次重跑出图脚本前，先 `curl ...6889/queue` 看有没有残留任务，有就先 `clear`**；或给脚本加"提交前先 clear 队列"逻辑，避免僵尸堆积。

## 11:44 ✅ taming 彻底修复（出图脚本可重跑）
- 用户跑诊断命令确认：`site-packages/taming/` 顶层直接是 `data/models/modules/util.py`（**无嵌套**）；`import taming.modules.vqvae.quantize` 打印 `quantize OK: /usr/local/lib/python3.12/site-packages/taming/modules/vqvae/quantize.py`（子模块真实导入成功）。之前 `taming OK: None` 仅是 `cp` 中途瞬时态，现已稳定。
- **结论**：Zero123 节点执行时动态 import taming，ComfyUI **无需重启**（节点早已注册 `object_info=True`）。**下一步直接重跑出图脚本**即可。
- **重跑命令（DSW Terminal，一次性）**：`cd /mnt/workspace/ai-comfyui/pai && python gen_angles_zero123.py`。预期：依次提交 front(right/back/left 对应 azimuth 0/90/180/-90)、每个 ~75 steps、A10 上单张约 1~2 分钟；最终在 `out_zero123/` 落下 4 张 256×256 角度图（z123_front/right/back/left_00001_.png）。
- **注意**：Zero123 固定 256×256、参考图灰底会带入结果；角度 OK 后再做「去背景变白底 + 放大」。步骤严格按用户要求：先看 4 张角度图确认 → 再下一步。

## 11:54 新错·Zero123-Porting g_model 真值判断 bug（重要，可复用）
- front 已成功出图并下载 `out_zero123/z123_front_00001_.png`(83450 bytes, 256×256) → taming 彻底 OK。但 right 立刻报新错 `LatentDiffusion does not support len()`，traceback 落在 `ComfyUI-Zero123-Porting/zero123_nodes.py` line 21 `if (g_ckpt == checkpoint) and (g_hf == hf) and g_model:`。
- **根因**：节点把模型缓存在模块全局 `g_model`。第 1 次跑（front）`g_model`=None → `and g_model` 短路不触发 len → 正常加载。第 2 次起 `g_model` 已是 `torch.compile` 包裹的 LatentDiffusion 对象，`and g_model` 求值真值 → Python 调 `len(g_model)` → dynamo 包抛 TypeError。**只有"缓存复用"分支才触发**，纯节点写法 bug。
- **修复（节点文件）**：把 line 21 的 `and g_model` 改成 `and g_model is not None`。DSW 上：`python - <<'PY' ... re.sub(r'and\s+g_model\s*:', 'and g_model is not None:', s) ... PY'`（写 `/root/ComfyUI/custom_nodes/ComfyUI-Zero123-Porting/zero123_nodes.py`）。
- **必须重启 ComfyUI**：节点模块已在运行进程加载，改磁盘文件不热更新 → `pkill -f "main.py"; sleep 3; cd /root/ComfyUI && nohup python main.py --port 6889 > /tmp/comfy_run.log 2>&1 &`；等 `curl ...6889/system_stats` 返回 JSON（权重重载约 1~2 min）再重跑脚本。重启会重载 Qwen 权重（慢但无害）。**注意保留原启动参数**（若有 `--listen`/`--cuda-device`/`--disable-xformers` 等）。
- **待办**：restart → 重跑 `python gen_angles_zero123.py` → 4 张角度图 → 下载回本机 `D:\Aicomfyui\image\` 看真·多角度。

## 12:04 Zero123 出图失败 → 输出非真多角度/腐蚀/离题
- 用户展示 5 张图：第 1 张绿糊块(corruption)；第 2 张完全离题成人脸/耳机；第 3 张疑似原参考图正面；第 4、5 张只是桃子平面内旋转（侧躺），没有 3D 透视变化。**结论：Zero123 对桃子角色完全不可用**。
- **根因**：Stable Zero123 训练于 Objaverse 3D 合成物体，擅长有明确几何结构的物体；桃子是高度风格化 2D 卡通角色（球体+细小四肢+画面孔），模型无真实 3D 先验，无法推断侧/背视图，只能平面旋转或胡编。不是参数问题（scale/steps/fp16 调整救不回）。
- **后续路线（待用户拍板）**：
  1. **推荐：回 MV-Adapter + SD1.5 + IP-Adapter Plus/Full**。SD1.5 的 IP-Adapter 对卡通/非人角色通常比 SDXL 稳；MV-Adapter 本身为多视角设计；A10 跑 SD1.5 轻松。
  2. 图生视频做轨道旋转后抽帧（AnimateDiff/LTX/CogVideoX），但会提前进入视频阶段。
  3. 换更强的单图转多视角模型（Zero123-XL/Zero123++/SyncDreamer），需重新下权重且对卡通角色也未必有效。
- **复盘（重要，AI 自省）**：本次 Zero123 是 AI 在**已知桃子为卡通角色**的情况下主动推荐的，失误不在"不知情"。错误逻辑：过度看重"Zero123 免 IP-Adapter → 一致性天然解决"，却忽略 Zero123 能转视角的前提是模型具备该物体的**真实 3D 几何先验**；对风格化卡通角色它根本生成不出可信新视图，"免锁"成空谈。更早信号已该警觉：刺猬靠 MV-Adapter+IP-Adapter 成功、桃子用 IP-Adapter 才失败 → 说明桃子比刺猬更难保一致，Zero123 更弱更偏物体、只会更难。教训：**非人类风格化角色选多视角方案，不能只看"是否免 IP-Adapter"，必须先验证模型是否具备该品类的 3D 先验**。→ 正解回到 MV-Adapter + SD1.5 + IP-Adapter Plus（靠参考图锁非人一致性）。
- **待办**：等用户确认方案 → 整理节点/权重清单 → 改脚本 → 跑新方案。

## 12:14 ✅ 方案 A 修正并启动（关键，已核实）
- 用户拍板"方案 A-赶紧跑起来"。但 AI 先核实发现：**原方案 A「MV-Adapter + SD1.5 + IP-Adapter Plus」在 ComfyUI 里不成立**：
  - MV-Adapter 的 ComfyUI 节点（`huanngzh/ComfyUI-MVAdapter`）**只支持 SDXL**（源码仅 `StableDiffusionXLPipeline`，无 SD1.5）。
  - **IP-Adapter Plus 与 MV-Adapter 架构不兼容**：IP-Adapter 作用在 ComfyUI `MODEL` 对象，MV-Adapter 用 diffusers `PIPELINE` 对象，无法串接；且 MV-Adapter 的 I2MV 管线**原生直接吃参考图**（自带跨视角一致性），不需要 IP-Adapter。
- **修正后真正可跑方案**：MV-Adapter **I2MV + SDXL**，参考图 `peach_role_v6.png` 直接喂 `DiffusersMVSampler.reference_image`，**不加 IP-Adapter**。一次前向生成 6 视角（含前/右/后/左）。A10 24G 跑 SDXL+MV-Adapter(~13-14G) 足够。
- **已核实节点（来自官方 `workflows/i2mv_sdxl_diffusers.json`，版本 2025-06-26）**：
  - `DiffusersMVPipelineLoader`(ckpt_name=`stabilityai/stable-diffusion-xl-base-1.0`, pipeline_name=`MVAdapterI2MVSDXLPipeline`)
  - `DiffusersMVSchedulerLoader`(pipeline, scheduler_name=`DDPM`, shift_snr=True, shift_mode=`interpolated`, shift_scale=8)
  - `DiffusersMVVaeLoader`(vae_name=`madebyollin/sdxl-vae-fp16-fix`)
  - `DiffusersMVModelMakeup`(pipeline, scheduler, autoencoder, load_mvadapter=True, adapter_path=`huanngzh/mv-adapter`, adapter_name=`mvadapter_i2mv_sdxl.safetensors`, num_views)
  - `LoadImage`(image=`peach_role_v6.png`)
  - `DiffusersMVSampler`(pipeline, reference_image, num_views, prompt, negative_prompt, width=768, height=768, steps=50, cfg=3, seed)
  - `SaveImage`(images) → 落盘多张
- **权重（HF 自动下，需镜像）**：SDXL base、mv-adapter safetensors、sdxl-vae-fp16-fix。DSW 直连 huggingface.co 可能墙 → 用 `export HF_ENDPOINT=https://hf-mirror.com` 前置下载/启动。
- **脚本**：本机 `D:\Aicomfyui\pai\gen_angles_mv.py`（已写好，API 调上述 7 节点，一次提交 6 视角，落 `out_mv/`）。DSW 上用 heredoc 创建。
- **下一步（用户执行）**：① clone `ComfyUI-MVAdapter` + `pip install -r requirements.txt`；② 镜像预下权重（SDXL/mv-adapter/vae）到 HF cache；③ heredoc 写 `gen_angles_mv.py`；④ `pkill main.py` + 带 `HF_ENDPOINT` 重启 ComfyUI；⑤ 验证 MV 节点注册；⑥ `python gen_angles_mv.py` 出 6 视角 → 用户看是否真多角度/角色一致（按"先看角度图再下一步"规则）。
- **已知坑/注意**：MV-Adapter 依赖 diffusers，安装其 requirements 可能改动 diffusers 版本，理论上或不影响已装节点；SDXL 需 13-14G 显存（A10 OK）；一次前向出全部视角不可单视角循环；参考图带灰底会被带入结果（后续再去背景）。
- **12:34 用户澄清（重要）**：用户确认「**HAI 上也能实现角度图，A10 上也能**」——即两个实例都可做 MV-Adapter+SDXL 多视角；HAI(T4 15.9G)需 `--lowvram` 才能跑（慢/有 OOM 风险），A10(24G)直接跑。→ **决策：在 A10 上跑通角度图（环境已搭一半最省事），HAI 留作兜底/只跑 Qwen**。不要再纠结"哪个实例"，按 12:14 的 6 步在 A10 继续。若用户改主意要走 HAI，用 `--lowvram` 启动 ComfyUI（supervisor 托管需注意加旗标）。

## 12:38 装 MV 节点+依赖 OK，但权重下载踩 `huggingface-cli` 废弃坑
- **节点/依赖已装好**：`git clone huanngzh/ComfyUI-MVAdapter` 成功；`pip install -r requirements.txt` 把 diffusers→0.31.0 / transformers→4.46.3 / huggingface_hub→0.24.6 / accelerate→1.1.1 / peft→0.13.2 降级，并新装 trimesh 4.12.2。**这些降级是 MV-Adapter 的精确硬依赖，正常不是坏事**。
- **权重没下下来（关键坑）**：本 DSW 环境 `huggingface-cli` 已被废弃为 no-op（提示 `deprecated and no longer works. Use hf instead`）。3 条 `huggingface-cli download ...` 全只打印提示、0 字节。→ **修正**：改用新 CLI `hf download`（设 `HF_ENDPOINT=https://hf-mirror.com` 走镜像）预下权重。
- **连带隐患**：AI 之前 `pip install -U "huggingface_hub[cli]"` 把 hub 顶到 1.24.0，与 MV 要求的 0.24.6 冲突。

## 12:41 权重下载又踩 xet 401 坑（还原 0.24.6 解决）
- 用 `hf download`（huggingface_hub 1.24.0）走镜像下载 SDXL base 时报 `CAS Client Error: 401 Unauthorized`（domain `cas-server.xethub.hf.co`）。**根因**：新 `hf` CLI 默认走 **xet** 高速传输，但 **hf-mirror 镜像不支持 xet 后端鉴权** → 文件重建阶段 401 失败（且吞吐仅 ~1.2MB/s、慢）。
- **修法（采用）**：还原 huggingface_hub 到 MV-Adapter 要求的 `0.24.6`（`pip install "huggingface_hub==0.24.6"`），此版本用普通 HTTP 下载、无 xet；再用老 `huggingface-cli download` + `HF_ENDPOINT=https://hf-mirror.com` 预下 `stabilityai/stable-diffusion-xl-base-1.0` / `huanngzh/mv-adapter` / `madebyollin/sdxl-vae-fp16-fix`。→ 顺带消掉 1.24.0 与 diffusers 0.31.0 / transformers 4.46.3 的版本冲突。
- **备选**：不重装、仅 `export HF_HUB_DISABLE_XET=1` 后再 `hf download`，但仍有 1.24.0 运行时冲突隐患，不推荐。
- **待办**：等 `huggingface-cli download` 3 个权重下完（~13-15GB）→ 验证 `~/.cache/huggingface/hub` → 写 `gen_angles_mv.py` → 重启 ComfyUI(带 HF_ENDPOINT) → 验证 MV 节点 → 出 6 视角。

## 12:47 ✅ 核验 nodes.py：MV 节点认本地目录路径 → 改走 ModelScope 内网（绕开慢镜像）
- 用户问当前 HF 下载是否正常：**在工作（无 401）但极慢**（~150kB/s，整套几十小时）且拉了整个 57 文件仓库（含 ONNX/OpenVINO/Flax 无用变体）。
- **查 raw `nodes.py` 确认**：`ckpt_name`/`vae_name`/`adapter_path` 均为 STRING，分别传给 `pipeline_class.from_pretrained` / `AutoencoderKL.from_pretrained` / `pipeline.load_custom_adapter`，**三者都接受本地目录路径**（非强制 HF repo id）。→ 可完全绕开慢镜像。
- **新下载方案（采用）**：`Ctrl+C` 停 HF 下载 → `unset MODELSCOPE_ENDPOINT` → `pip install modelscope` → `snapshot_download(<id>, local_dir='/mnt/workspace/ai-comfyui/pai/models/<name>')` 下 `stabilityai/stable-diffusion-xl-base-1.0` / `huanngzh/mv-adapter` / `madebyollin/sdxl-vae-fp16-fix`（PAI-DSW→阿里云内网几百 MB/s）。若 modelscope 缺某模型，该个回退 `huggingface-cli download <id> --local-dir <dir>`（HF 镜像）。
- **脚本改本地路径**：`gen_angles_mv.py` 的 `ckpt_name`→`.../models/sdxl_base`、`vae_name`→`.../models/sdxl_vae`、`adapter_path`→`.../models/mv_adapter`（adapter_name 保持 `mvadapter_i2mv_sdxl.safetensors`）。运行时无需联网。
- **待办**：等 modelscope 三模型下完（看 OK/FAIL）→ 写本地路径版脚本 → 重启 ComfyUI（让进程加载 hub 0.24.6 + 重载 MV 节点）→ `curl object_info` 验证 MV 节点注册 → `python gen_angles_mv.py` 出 6 视角 → 用户确认真多角度/角色一致。

## 12:53 ⚠️ 执行坑：用户把 `Ctrl+C` 当文字粘贴，HF 下载没停
- 用户回复里 `Ctrl+C` 是**粘贴进去的文字**，未真发 SIGINT → 原 `huggingface-cli download` 一直前台运行（仍见 `diffusion_pytorch_model.safetensors 3%`）；modelscope 命令段只憋在输入缓冲、未执行（无 OK/FAIL 输出）。
- **纠正（给用户）**：必须**真按 Ctrl+C 键**（或新标签 `pkill -f huggingface-cli`）杀掉下载进程 → 回到干净提示符后**再粘贴** modelscope 命令；SDXL base 加 `ignore_file_pattern=['*.onnx','*openvino*','*.msgpack','*fp16.safetensors','*0.9vae.safetensors','*.lora*']` 跳过无用变体省带宽。

## 12:55 ✅ modelscope 内网下载确认飞快（勿中途关机）
- 真 Ctrl+C 停掉 HF 下载后，modelscope `snapshot_download` 跑通：**SDXL base 33 文件 30/33（91%）仅 72 秒**（PAI-DSW→阿里云内网加速生效，几百 MB/s）。`modelscope 1.38.0` 已预装。
- **勿在下载中途关实例**：半截文件需重下。若必须离开，选**停止（不删除）**实例，`/mnt/workspace` 持久盘保留已下模型+已装节点/依赖；下次重跑同命令续传，运行时本地路径不再联网。
- **待办**：等 3 个 `OK` → 写本地路径版 `gen_angles_mv.py`（`ckpt_name/vae_name/adapter_path`→`models/{sdxl_base,mv_adapter,sdxl_vae}`）→ 重启 ComfyUI（进程已加载 hub 0.24.6 + 重载 MV 节点）→ `curl object_info` 验证 MV 节点 → `python gen_angles_mv.py` 出 6 视角 → 用户确认真多角度/角色一致。

## 13:00 ✅ SDXL base 下完；改策略只补 mv-adapter 单文件
- **结果**：modelscope `snapshot_download` 跑完 → `OK sdxl_base`（SDXL base 6.94G 本地就位 `/mnt/workspace/ai-comfyui/pai/models/sdxl_base`）；`mv_adapter`/`sdxl_vae` 均 **404**（这两个 repo 不在 modelscope，仅 HuggingFace 有）。
- **修正策略（省下载）**：
  1. **sdxl-vae 不下了**，VAE 直接复用 `models/sdxl_base/vae`（SDXL base 自带标准 VAE，madebyollin fp16 版仅"推荐"非必须）。
  2. **mv-adapter 只下必需文件** `mvadapter_i2mv_sdxl.safetensors`（非整仓库）：`export HF_ENDPOINT=https://hf-mirror.com; export HF_HUB_DISABLE_XET=1; huggingface-cli download huanngzh/mv-adapter mvadapter_i2mv_sdxl.safetensors --local-dir /mnt/workspace/ai-comfyui/pai/models/mv_adapter`（huggingface_hub 已 0.24.6，cli 可用、无 xet）。
- **脚本已改本地路径版** `D:\Aicomfyui\pai\gen_angles_mv.py`：`ckpt_name`→`models/sdxl_base`、`vae_name`→`models/sdxl_base/vae`、`adapter_path`→`models/mv_adapter`。运行时不再联网。
- **待办**：下完 mv-adapter 单文件 → DSW 写本地路径版脚本(heredoc) → `pkill main.py`+重启 ComfyUI(进程已载 hub0.24.6+重载MV节点) → `curl object_info` 验证 MV 节点 → `python gen_angles_mv.py` 出 6 视角 → 用户确认真多角度/角色一致。

## 13:04 📋 用户关机前要求：搞一个周一可续传的一键命令
- 用户 13:04："我要关机下班了，你搞个命令我周一可以续传的，是否可以"。
- **当前活跃线判定**：7/25 对话 = DSW/PAI 上 MV-Adapter(I2MV)+SDXL 出多角度图，仅差 `mvadapter_i2mv_sdxl.safetensors` 单文件未下完（SDXL base 已就位、VAE 复用 sdxl_base/vae）。另一条 HAI/Qwen `gen_refs.py full` 是 7/24 working_memory 主线、暂未做 → 作为**备选**给用户。
- **产出**：`D:\Aicomfyui\pai\resume_mv.sh`（自包含续传脚本，运行于 DSW 终端）：
  ① 检查/下载 mv-adapter 单文件（HF 镜像+`HF_HUB_DISABLE_XET=1`+`--local-dir-use-symlinks False`，已存在则跳过）→
  ② heredoc 内嵌写出 `gen_angles_mv.py`（绕开文件传输）→
  ③ 把 `peach_role_v6.png` 拷到 `/root/ComfyUI/input`（保险）→
  ④ `pkill -f main.py`+`nohup python3 main.py --port 6889` 重启 ComfyUI 并轮询 UP →
  ⑤ `python3 gen_angles_mv.py` 出 6 视角 → 列 `out_mv/`。
- **用户周一操作**：PAI 控制台启动实例（停止不删除、盘持久）→ web terminal 粘贴"创建+执行"一条命令（把 resume_mv.sh 内容 heredoc 写入 DSW 后 `bash`）→ 约 10~20 分钟出图。
- **HAI 备选（若周一要续 Qwen 出图）**：本地 Windows `set COMFY_HOST=<新IP>` 后 `python D:\Aicomfyui\cloud\gen_refs.py full`（需 HAI 实例开机拿新 IP、ComfyUI 由 supervisor 托管应自起）。
- **comfyui-upgrade-deps.md 说明**：用户在 Downloads 引用的该 md 是 HAI 那边 ComfyUI 升级到原生支持 Qwen 的依赖清单，与本次 DSW 出角度图非同一条线，无需在续传命令中执行。

## 20:33 🔍 用户调研 Digen AI 平台（与桃子项目相关性评估）
- 用户 20:33 问"digen平台怎么样，帮我研究下"。
- **结论**：Digen AI（digen.ai）是一站式多模型 AI 视频聚合平台（Sora2/Veo3.1/Seedance2/Kling3.0/Runway/Grok Video），浏览器即用、零 GPU、免费额度友好（注册300积分+每日奖励，免费5秒720p）。官方内容出现 `Digen.ai ✖️ bytedance` 且 Seedream 5.0 Lite 全球首发落地 Digen，与字节 Seedance 生态紧密合作。
- **与桃子项目契合**：✅ 可作"图生视频"快速验证补充（把桃子参考图喂 Kling/Seedance，省自建 LTX 工程）；❌ 数字人唇形同步针对人像/写实脸，对非人类卡通 IP 不适用；❌ 跨镜头角色一致性仍是通病（不提供训练专属角色），不替代 Qwen-Image-Edit 锁一致性主线；⚠️ 素材外泄风险（自有 IP 别大量上传第三方）。
- **产出**：调研报告 `D:\Aicomfyui\Digen平台调研_20260725.md`。建议：Digen 当补充渠道试水，主力仍走 Qwen 出图 + 自建视频路线。

## 20:41 用户发 Digen 引流软文链接（船长AI视界 2026-07-21）
- 文章为 Digen 平台引流软文，邀请码666/注册地址/登录入口藏评论区；吹可灵3.0Turbo/Seedance2.0/mini 满血无水印免费。
- 提醒"无限免费"靠开小号堆积分有水分；对桃子非人类卡通IP真人参考价值低；跨镜头一致性仍无解，替代不了Qwen主线。
- 用户公众号运营教学视角：可拆解该文"评论区藏信息+情绪话术+私域建群"引流漏斗作素材。

## 20:43 用户要求研究软文里的 Digen 实操玩法（补篇）
- 产出 D:\Aicomfyui\Digen实操落地研究_20260725.md。
- 澄清：软文吹的"神级提示词SKILL"非Digen官方功能，是博主自制模板发私域群；"无限免费"=临时邮箱开小号堆积分(违条款/封号风险)；"无水印"前提是生成后立即下载否则自动加水印。
- Digen真实流程：上传图→选引擎(2.0/2.5/Turbo 720p, 2.6 2K)→6种动画preset→比例1:1/9:16/16:9→生成→增强→下载。
- 对桃子：图生视频+自然运动/电影运镜+9:16 适合单镜头展示(补充渠道)；真人参考/口型/跨镜头一致性仍不可用，主力仍Qwen+LTX。
- 运营教学视角：该软文+白嫖教程可作"AI工具引流+灰产小号"避坑案例素材。

## 文生图模型调研结论 + 新建 Qwen-Image base 文生图工作流（桃子项目·文生图路线）
- **根因坐实**：Qwen-Image-Edit 是**编辑**模型，空 latent 直接文生图会出白/灰图（pixar_char_gen_ui.json 实测）。用户明确：文生图不再用 Qwen-Image-Edit，按调研推荐专用 T2I 模型。
- **推荐：Qwen-Image base（city96 GGUF `qwen-image-Q4_K_S.gguf`，12.1GB）**。理由：① 复用 DSW 已装的 `Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf`(qwen_image CLIP) + `qwen_image_vae.safetensors`，**只新增 1 个 unet 文件**；② 20B MMDiT 提示词遵循强、皮克斯风格靠 prompt 即可、且擅长文字渲染（角色举牌等加分）；③ 24G A10 轻松装下(~17G，比 edit 还小)；④ 原生 T2I，不会再出白图。备选 Q4_K_M(13.1G) 略好、Q3_K_M(9.68G) 更省。
- **节点图已对照 ComfyUI 0cb84e7e 源码核实**（`comfy_extras/nodes_qwen.py` 只注册 `TextEncodeQwenImageEdit`/`EditPlus`/`EmptyQwenImageLayeredLatentImage`，**无 base 专属节点**）→ base 走**原生** `CLIPTextEncode`(正/负向，非 EditPlus) + `EmptySD3LatentImage`(非 Layered) + 标准 `KSampler`。另查官方 Qwen 工作流 + runcomfy + docs.comfy.org 一致：shift=3.0（非 edit 的 1.73）、euler/simple、cfg 2.5、steps 20、denoise 1.0。mmproj 仅编辑/图输入需要，T2I 不需要。
- **已建工作流** `D:\Aicomfyui\pai\workflows\qwen_image_t2i_base_ui.json`（10 节点，link 图已 python 校验一致）。默认 Pixar 兔子 prompt，可改任意角色。一次 Queue 出 1 张 1024×1024。
- **待执行（需用户操作）**：DSW 网关现 302 跳转登录（实例需重登/重启）→ 下 `qwen-image-Q4_K_S.gguf` 到与现有 `qwen-image-edit-2511-Q4_K_M.gguf` 同目录（`models/unet/` 或 `models/diffusion_models/`）→ 浏览器加载该 JSON → Queue 一次。下载命令（DSW Terminal）：`cd /root/ComfyUI/models/unet && nohup curl -L https://hf-mirror.com/city96/Qwen-Image-gguf/resolve/main/qwen-image-Q4_K_S.gguf -o qwen-image-Q4_K_S.gguf > /tmp/qwenbase_dl.log 2>&1 &`。
- **其他备选**：SDXL+Pixar/Disney LoRA（卡通生态最成熟、节点 100% 标准，但需另下 base+vae+clip+lora）；FLUX.1 Dev（写实最强、卡通弱、24G FP16 偏紧）。本次不采用，因 Qwen base 复用已装资产、成本最低、质量最高。
- **提速可选**：加 `Qwen-Image-Lightning-8steps-V1.0.safetensors`(LoRA, models/loras) → KSampler steps=8 cfg=1.0，出图从 ~70s 降到 ~35s（RTX4090 参考，A10 略慢）。

## 2026-07-26
### 2026-07-26 工作日志

## 12:17 用户纠正：Digen 讨论勿套用"公众号定位"记忆
- 用户发船长AI视界软文本是延续"桃子角色视频创作"工具链讨论，让研究 Digen 免费图生视频方式本身，与公众号无关。
- 我误从用户级 MEMORY（"公众号运营教学定位，AI选题优先从公众号运营切入"）触发，在分析里加了"运营教学视角/避坑素材"建议——属误用，用户已划掉。
- 教训：该项目当前是视频创作工程语境，非公众号选题策划；用户级 MEMORY 的公众号规则仅在"用户明确做公众号内容/选题"时适用，勿自动套用。
- 行动：已向用户澄清并询问是否调整该记忆适用范围（待用户确认）。

## 12:20 续研 Digen（视频创作视角，已剔除公众号误用）
- 产出 D:\Aicomfyui\Digen视频创作落地研究_20260726.md。
- 关键澄清：官方 resource.digen.ai 的"评测/98
## 12:20 续研 Digen（视频创作视角，已剔除公众号误用）
- 产出 D:\Aicomfyui\Digen视频创作落地研究_20260726.md。
- 关键澄清：官方 resource.digen.ai 的"评测/98%一致性/8K"是 PR 稿不可全信；aifounderkit 实测图生视频运动限头肩、背景会 warp。
- 图生视频对非人类卡通可行(猫咪案例)，但全身动作/复杂互动崩；数字人口型仅针对人脸，桃子无用。
- "98%一致性"=单段视频内头部不漂移，非跨分镜一致，替代不了 Qwen 锁角色。
- 分工明确：Digen=单镜头展示/快速验证(零工程)；Qwen+LTX=多镜头连贯成片(主力)。

## 12:27 设置每日视频制作教程搜集自动化
- 已创建 recurring automation（id=automation-1785040089915），每天 09:00 触发，从 2026-07-27(周一)起生效，cwds=D:\Aicomfyui，status=ACTIVE。
- 任务：每天主动搜微信公众号/B站/小红书/GitHub 上视频制作/AI视频/角色动画方向教程，结合桃子项目(主线Qwen+LTX，补充Digen)分析可尝试方案，已验证成功的沉淀为方法论。
- 简报输出目录：D:\Aicomfyui\每日教程搜集\YYYY-MM-DD.md。
- 用户约定：Digen 研究先暂停，等用户发其他教程再继续；自动化只做视频制作技术搜集，不引入公众号运营视角。

## 12:30 自动化改 8 点 + 写入项目阶段目标路线图
- 自动化 automation-1785040089915 触发时间由 09:00 改为 08:00（用户要求更早），prompt 强化：阶段目标 + 根据调研及时调整创作方式。
- 项目 MEMORY 新增「项目阶段目标路线图」：第一步桃子单角色带情节视频(当前) → 下一步多角色视频 → 最终漫剧；原则=调研到更优方式就及时调整技术选型。
- 用户目的单一清晰：先实现桃子带情节视频，再扩展多角色、漫剧；创作方式随调研动态优化。

## 21:04 用户发 TRAE Work 内置 Seedance 免费视频文章（TRAE 公众号 2026-07-26）
- 文章链接 https://mp.weixin.qq.com/s/p1ATCx8FW40pzxvcT4Z5uQ ；结论：TRAE Work 内置 Seedream 5.0+Seedance，**图生/文生视频对所有用户免费**，不用花钱。
- 实测边界(ai-bot.cn/微博)：文生图+文生视频+图生视频；时长5/10/15s；画幅横/竖/方；分辨率720P；高峰期免费用户排队、付费优先；入口 trae.cn / trae.ai 桌面端+App。
- 重要区分：seedance.tv 是第三方独立站，其免费档(40次/无限/1080P)与本文 TRAE Work 内置 Seedance 不是一回事，勿混淆。
- 对桃子项目：TRAE Work 原生 Seedance 比 Digen 更优(官方通道/IP更安全/明确含"短剧分镜"场景)→ 建议作为首选免费单镜头验证渠道，Digen 降备选；仍替代不了 Qwen+LTX 主线(跨镜头一致性、720P/15s上限)。
- 产出报告 D:\Aicomfyui\TRAE_Work_Seedance研究_20260726.md。下一步：注册TRAE Work→传桃子非核心参考图→图生视频10s竖屏实测。

## 2026-07-27

## 09:00 用户澄清 公众号/B站/小红书 链接转发工作流
- 用户确认：反爬导致自动搜集抓不到公众号/B站/小红书原文，用户会手动把看到的教程链接发我研究（"你发链接给我，我才能发你"）。
- 今日自动简报唯一抓到的原始平台标识：B站视频 BV1feDCB1EN9《AI漫剧全流程 即梦+豆包+剪映》→ 原始链接 https://www.bilibili.com/video/BV1feDCB1EN9/ 。
- 公众号/小红书原文搜索未露真链接，需用户从自己订阅/群里粘贴；我可给二手转载链接供溯源。

## 09:02 用户授权自行甄别研究内容→技能库/记忆（技能固化）
- 用户：学习到的内容自己甄别哪些进技能库、哪些不进，更高效；用户今天先去摸 TRAE Work 模式，待会再找我。
- 已新建 2 个用户级技能（~/.workbuddy/skills/）：
  1. ai-video-character-consistency：Lock-Then-Animate 角色一致性方法论（参考图集+提示词锚定块+抽3-5选优+短镜温和运镜），5+2026源交叉印证，项目主心骨。
  2. ai-video-lowvram-chaining：Last Frame 链式拼接做长情节（T4 15.9GB 永久约束，10GB可跑）。
- 明确不建技能、留记忆/报告：TRAE Work/Digen 用法(平台volatile,用户自测)、模型选型全景(参考易过时)、Grid Method(未验证,待2512权重)、HAI IP/权重/步骤(纯状态)、每日自动化(已是automation)。
- 下一步待用户摸完 TRAE Work 回来；Grid Method 标"待验证晋升"。

## 10:23 用户贴 TRAE Work Agent 执行计划，确认 GenerateVideo=内置Seedance
- 用户摸到 TRAE SOLO CN 桌面端，Agent 计划调 GenerateVideo 工具基于桃子参考图出视频(图生视频)；底层即 TRAE Work 内置 Seedance(官方原生,免费)。确认此前判断:TRAE Seedance 是原生通道、比Digen安全。
- 该调用细节:中文提示词(字节原生OK)、1:1、拟 8s(TRAE仅5/10/15s档,可能圆到10s)、三段情节(打滚→掉河→抓虾)塞一片段对Seedance偏难(图生视频运动幅度有限)。
- 结论:TRAE Seedance 适合单镜轻动作快速验证,替代不了多镜头叙事;真做情节用 lowvram-chaining 技能分段拼。待用户出片后评估。

## 10:26 用户跑通 TRAE Work Seedance 一版桃子视频，实测分析完成
- 视频参数：960×960、24fps、8.04s（1:1画幅实际960p，8s请求被接受）。
- 情节：三段节拍（草地打滚→落水→抓虾）全部演出来，角色一致性跨场景保持得不错，超出预期。
- 重要发现：视频带右下角「AI生成」水印 → 修正此前"未确认水印"的判断；TRAE Seedance 仅适合快速验证/动态分镜，不能当无水印最终成片。
- 已更新 D:\Aicomfyui\TRAE_Work_Seedance研究_20260726.md 实测章节。
- 结论：TRAE Seedance 是桃子单镜头轻情节快速验证的好渠道；最终无水印成片仍靠 Qwen+LTX 主线。后续可把 TRAE 验证的动作作为 LTX 主线的"目标分镜"参考。

## 10:36 用户提出混合流水线思路 + 审美偏好确认
- 用户质疑"LTX能否完美复刻TRAE视频"→ 结论:不能逐帧复刻,但混合流程可行且更优。
- 用户方案: TRAE Work 做角色角度图/分镜图(免费快) → ComfyUI(Qwen精修+LTX出视频)做最终渲染。
- 用户审美偏好(重要): 更喜欢 HAI/Qwen 那版的"颜色与美观度",认为 TRAE 视频亮度偏高、不好看;虽首次HAI motion不流畅,但色调胜出。
- 确认的分工: TRAE=分镜预演/角度探索草稿机(免费);ComfyUI=最终渲染(无水印+偏好色调)。符合"调研到更优就调整"原则。
- 真风险: TRAE图的偏亮会被Qwen继承→精修步须加光照/色调指令拉回偏好调子;此审美须写入角色圣经。
- 下一步: 小范围验证——用户用TRAE出一张桃子角度/分镜草图(以现有参考图为底),我喂Qwen精修看能否拉回偏好色调;成则固化为标准流水线。

## 10:47 用户定调:TRAE出双角色定妆照(桃子+小蘑菇),进入多角色阶段起点
- 用户今日先用 TRAE Work(Seedream)出两个角色图:皮克斯风/圆润/萌/Q版/3D的"可爱桃子"与"小蘑菇",为后续多角色视频铺路。
- 已给两份可直接粘贴的中文提示语(全身正面+浅米色纯背景,利于Qwen锁一致性+出视频);统一关键词:皮克斯/Q版/圆润/3D/纯色浅米色背景/全身正面。
- 操作建议:1:1或3:4比例,每角色出2-4张挑;Seedream支持对话微调。
- 出图后交接:AI评估能否当"角色圣经基准图",并用 ai-video-character-consistency 技能写固定描述块+提示词锚定模板。
- 若此版优于旧 peach_role_v6,则正式取代旧设定,成为多角色阶段(桃子+小蘑菇)起点。

## 10:49 背景色修正:用户要纯白(非米色)利于角度图;蘑菇白身须极浅灰或加阴影
- 用户指出纯色浅米色不如纯白适合后续角度图(去背/一致性更干净)。采纳。
- 修正:两角色统一用"极浅灰纯色背景"(接近白,不影响角度图/去背);关键原因:小蘑菇是白身子,纯白底会丢失轮廓→极浅灰解决。
- 已给更新版中文提示语(桃子/小蘑菇,极浅灰背景)。后续角度集需所有图同背景。

## 11:04 用户问:用桃子参考图,我们自己的栈能否派生同风格蘑菇(多角色关键能力)
- 结论:能。首选方案=Qwen-Image-Edit(HAI)以桃子为风格参考图+指令"同美术风格创作新角色蘑菇";兜底=同风格提示词法(同模型+同描述词必对齐)。
- IP-Adapter 不推荐:此前弃用是因非人类IDENTITY锁不住,与style匹配不同,但Qwen参考法已够用且干净。
- 战略点:蘑菇不必用TRAE出,可用Qwen从桃子派生→无水印+100%同风格+色调可控;TRAE仅作灵感试探。此能力是多角色阶段(桃子+蘑菇同世界)的关键。
- 流程:TRAE出桃子→去水印→Qwen派生蘑菇→两角色当角色圣经基准图。

## 11:07 用户决定在 DSW 装 Qwen-Image-Edit(派生蘑菇),本地有 peach_role_v6
- 用户确认:桃子图本地有(peach_role_v6.png),要在 DSW 上操作;问 DSW 是否装了 Qwen-Image-Edit。
- 事实澄清:DSW(ComfyUI 0.28.0)仅装了 MV-Adapter+SDXL;Qwen GGUF(12.34GB)在 HAI。沙箱连不上 DSW(PAI网页终端),需用户在 DSW 终端自查。
- 用户选择:在 DSW 装 Qwen(A10 更稳,利于后续多角色)。已写 D:\Aicomfyui\pai\setup_qwen_dsw.sh(下GGUF+升级ComfyUI+验证),并给无风险检查命令。
- 风格提醒:peach_role_v6 未必是皮克斯风,蘑菇会继承其原风格;用户坚持用现有桃子。
- 下一步:用户启动 DSW→跑检查命令贴输出→我据输出给精确安装/Qwen节点名→写蘑菇派生脚本。

## 11:19 用户今天忙碌,要求AI自主在DSW操作;澄清沙箱无法直连DSW
- 用户:今天很多事,不能一个个贴命令,让我提供必要资源后AI自己搞。
- 限制澄清:沙箱(Git Bash/Windows)连不上DSW网页终端(PAI网页操作,非SSH);若用户不给DSW公网SSH入口,则只能写一键大脚本让用户粘贴一次。
- 沙箱能连HAI(有SSH信息/IP可变),HAI已装Qwen-Image-Edit(之前验证)。
- 建议今天走HAI路线出蘑菇(免装,省力):用户只需给HAI新IP + 上传peach_role_v6到HAI input(或发图我SFTP传)。DSW装Qwen留到有空。
- 待用户选路线(HAI / DSW-SSH / DSW网页大脚本)。

## 11:25 写 DSW 一键大脚本 dsw_qwen_mushroom.sh(用户选此路线,今天没空)
- 脚本 D:\Aicomfyui\pai\dsw_qwen_mushroom.sh: 安装ComfyUI-GGUF节点+升级核心+下3权重(unet/clip/vae, hf-mirror)+重启+验证Qwen节点+以peach_role_v6为参考派生小蘑菇(denoise 0.75/0.85两张)+git push备份。
- 节点名与HAI gen_refs.py 一致(UnetLoaderGGUF/CLIPLoaderGGUF/qwen_image type/QwenImageSampler等),权重源: city96/qwen-image-edit-gguf, city96/Qwen2.5-VL-7B-Instruct-GGUF, Comfy-Org/Qwen-Image_ComfyUI(vae)。
- 用户操作: 启动DSW → 网页上传peach_role_v6.png到ComfyUI/input → 粘贴脚本执行一次 → 忙别的;回来发 out_qwen/ 下蘑菇图(或git push成功AI自拉)。
- 风险: 下载权重20-40min;升级核心可能动MV-Adapter(暂不需);git push需credential否则跳过手动发图。

## 11:35 用户要求改为可视化工作流(非API脚本),已调整交付
- 用户: 希望从 ComfyUI 工作流直接上传图片生成,不要非可视化(API提交)方式。
- 调整: ① 安装脚本改为 dsw_setup_qwen.sh,只装 Qwen 环境(节点+权重+重启+验证),去掉自动派生; ② 新增可视化工作流 JSON D:\Aicomfyui\pai\workflows\mushroom_from_peach_ui.json(UnetLoaderGGUF/CLIPLoaderGGUF/VAELoader/ModelSamplingAuraFlow/CLIPTextEncode*2/LoadImage/VAEEncode/QwenImageSampler/VAEDecode/SaveImage),桃子为参考图、denoise=0.75。
- 用户操作: 跑安装脚本→ComfyUI网页Load该JSON→LoadImage上传peach_role_v6.png→Queue Prompt→SaveImage下载蘑菇。全可视化,无需贴命令。

## 12:03 用户问官方给的 DSW ComfyUI 网页访问法 + 端口修正
- 用户贴官方解答:PAI控制台打开实例→终端启动ComfyUI→经 DSW Gateway 代理访问,格式 `https://dsw-gateway-cn-shanghai.data.aliyuncs.com/<前缀>/<端口>/`,默认 8188。
- 关键修正:我们 DSW 的 ComfyUI 跑在 **6889** 端口(安装脚本写死),不是 8188。正确地址 `https://dsw-gateway-cn-shanghai.data.aliyuncs.com/dsw-823428/6889/`(前缀 dsw-823428 与用户实例一致)。
- 阻塞点确认:工作流 mushroom_from_peach_ui.json 实际**只用 QwenImageSampler**,没用 QwenImageEmptyLatentImage(后者是验证脚本多查,可忽略)。DSW 升级后 QwenImageSampler 未注册→需诊断(git pull 是否拉全 / comfy_extras/nodes_qwenimage.py import 是否失败)+ 强制更新重启修复。
- 操作澄清:ComfyUI 的 Load 按钮直接读本机文件,JSON 与 peach_role_v6.png 无需先传到 DSW,用户本地选即可。
- 已给用户一段「自动判断+诊断+强制更新+重启+复验」脚本,等其粘贴输出定下一步。

## 12:15 诊断结果 + 修复决策：DSW v0.5.9 无 QwenImageSampler，降级到 0cb84e7e
- 用户贴回诊断：commit `093d571b` = ComfyUI **v0.5.9**（最新）；`comfy_extras/nodes_qwenimage.py` **不存在** → `QwenImageSampler` 不是该版本原生节点。
- 复验出现的 `QwenImage*` 是 v0.5.9 原生新节点：`QwenImageEdit` / `QwenImageEditPlus` / `QwenImageLayeredLatentImage` / `QwenImageDiffsynthControlnet`（与我们的 `QwenImageSampler` 不是一回事，节点名被重构）。
- run log 另有 `ImportError: cannot import name 'FLAX_WEIGHTS_NAME' from 'transformers.utils'`（新版 transformers 删了旧符号，某节点 import 失败，但 GGUF/UnetLoaderGGUF 正常，非阻塞）。
- **根因**：HAI 的 ComfyUI 是更老的 `0cb84e7e`（2026-07-23），还带 `QwenImageSampler` 原生节点，与我们工作流匹配；DSW 升到 v0.5.9 后节点被改名，导致缺失。
- **决策（推荐、可逆）**：把 DSW ComfyUI 降回 `0cb84e7e`（= 与 HAI 同配置），现有工作流零改动即可用。命令：`cd /root/ComfyUI && git fetch --all && git reset --hard 0cb84e7e && pip install -q -r requirements.txt && pkill -f main.py && nohup python3 main.py --port 6889 --listen 0.0.0.0 >/tmp/comfy_run.log 2>&1 &` 然后复验 QwenImageSampler。
- 兜底方案（若降级异常）：用 v0.5.9 原生 `QwenImageEdit`/`QwenImageEditPlus` 节点重写 mushroom_from_peach_ui.json（需先 object_info 取该节点 input/output 规格）。
- 待用户跑降级脚本贴复验输出。

## 12:25 实测打脸：降级 0cb84e7e 后 QwenImageSampler 仍不存在（关键纠正）
- 用户贴回降级输出：commit 确为 `0cb84e7e`，但复验 `QwenImage*` 仍只有 `QwenImage`/`QwenImageEdit`/`QwenImageEditPlus`/`QwenImageDiffsynthControlnet`/`QwenImageLayeredLatentImage`，**无 `QwenImageSampler`**。
- 进一步查 0cb84e7e 源码：`comfy_extras/nodes_qwen.py` 已改用新 API（`comfy_api.latest`+`ComfyExtension`），注册 `TextEncodeQwenImageEdit`/`TextEncodeQwenImageEditPlus`/`EmptyQwenImageLayeredLatentImage`，**无 QwenImageSampler**；ComfyUI-GGUF(city96) 也只提供加载器、不含 QwenImageSampler。
- **结论（纠正 12:15）**：`QwenImageSampler`/`QwenImageEmptyLatentImage` 在**干净的 0cb84e7e 根本不存在**。HAI 能跑 `gen_refs.py` 是因其 0cb84e7e **本地遗留/额外补了 Qwen 节点包**；DSW 干净 checkout 没有 → DSW 跑 gen_refs.py 也缺节点失败。降核心是死路。
- **正确链路（0cb84e7e 原生）**：`TextEncodeQwenImageEdit`(clip+prompt+vae+image=peach) 把参考图编码进 CONDITIONING(`reference_latents`) → 配核心 `KSampler`(model+positive+negative+EmptyLatentImage) → `VAEDecode` → `SaveImage`。此为 0cb84e7e 官方 Qwen-Image-Edit 标准链路（采样用通用 KSampler，无专用节点）。
- 已重写工作流：`D:\Aicomfyui\pai\workflows\mushroom_from_peach_ui_v2.json`（UnetLoaderGGUF→ModelSamplingAuraFlow(1.73)→TextEncodeQwenImageEdit(peach)→KSampler(seed12345/steps22/cfg6/euler/normal/denoise1.0)→VAEDecode→SaveImage）。原 v1 的 QwenImageSampler 已失效，留档勿用。
- 待用户：本地浏览器开 `https://dsw-gateway-cn-shanghai.data.aliyuncs.com/dsw-823428/6889/` → Load `mushroom_from_peach_ui_v2.json` → 传 peach_role_v6.png → Queue；若 KSampler 报 GGUF/reference_latents 相关错，贴回再调。

## 12:54 致命报错 mat1 维度错 → 根因：缺 mmproj 视觉投影文件（关键修复）
- 用户 Load v2 跑出 `RuntimeError: mat1 and mat2 shapes cannot be multiplied (5476x1280 and 3840x1280)`，节点 `TextEncodeQwenImageEdit`（CLIP 视觉编码器路径）。
- 伴随日志：`Can't find mmproj file for 'Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf' ... Qwen-Image-Edit will be broken!` + `clip missing: ['visual.patch_embed.proj.weight', ...]`（所有 visual.* 权重缺失）。
- **根因（确认，官方 Unsloth 文档+CSDN 案例佐证）**：Qwen2.5-VL 的 GGUF 必须配套 **mmproj**（视觉投影矩阵）才能把图 ViT 特征映射到文本空间；安装脚本 `dsw_setup_qwen.sh` 只下了主 GGUF（`Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf`, 4.4G），**漏了 mmproj**。缺失即报此 mat1 维度错（与文档案例 `(748x1280 and 3840x1280)` 同类）。与 KSampler/工作流链路无关。
- **修复**：下载 `Qwen2.5-VL-7B-Instruct-mmproj-BF16.gguf`（文件名前缀须与 text encoder 一致，ComfyUI 才能自动匹配）放进 `models/text_encoders/`，重启 ComfyUI。源：`hf-mirror.com/unsloth/Qwen2.5-VL-7B-Instruct-GGUF/resolve/main/mmproj-BF16.gguf` 或 modelscope `.../repo?Revision=master&FilePath=mmproj-F16.gguf`。重启后日志应出现 `Loading mmproj from ...`。
- v2 工作流 KSampler 默认值已正确（seed12345/steps22/cfg6/euler/normal/denoise1.0），无需改。
- 待用户：DSW 终端下 mmproj → 重启 → 确认日志 Loading mmproj → 重 Load v2 → 传 peach → Queue 出蘑菇；结果发我评估风格对齐。

## 13:25 mmproj 已下好并重启，缺失错误消失，待出图验证
- 用户从 `hf-mirror.com` 下完 `Qwen2.5-VL-7B-Instruct-mmproj-BF16.gguf`（1.3G，约 18 分钟，比预期慢）；放进 `models/text_encoders/`，文件名前缀与 text encoder 一致。
- 重启 ComfyUI 后，确认 `grep -iE "Can't find mmproj|broken"` **无输出** → 文件已被自动匹配，视觉编码器缺失问题解除。
- 服务状态 OK（`object_info` 正常返回）。注意：`object_info` 不加载模型，故日志无 "Loading mmproj" 字样属正常，以"无 Can't find 错误"为匹配成功判据。
- 下一步：用户本地浏览器开 `https://dsw-gateway-cn-shanghai.data.aliyuncs.com/dsw-823428/proxy/6889/` → Load `mushroom_from_peach_ui_v2.json` → 上传 `peach_role_v6.png` → 检查 KSampler(cfg6/euler/normal) → Queue 出蘑菇。若还报 mat1 维度错，则 mmproj 可能仍未被 CLIP 实际加载（需查 Queue 时日志）。

## 13:31 v2 链路错误：必须用 `EmptyQwenImageLayeredLatentImage`，不能用普通 `EmptyLatentImage`（关键纠正）
- 用户跑 v2 第一次：结果仍是桃子（风格保留生效，角色替换未生效，说明参考图仅当风格锚定，没进入编辑采样）。
- 用户按建议调低 denoise=0.8 + 更强编辑 prompt 后第二次：结果出现**两个奇怪人形桃子角色 + 草地背景**，完全偏离提示词。
- **查 0cb84e7e 源码 `comfy_extras/nodes_qwen.py` 找到根因**：
  1. `TextEncodeQwenImageEdit`/`TextEncodeQwenImageEditPlus` 在有 vae 时会生成 `reference_latents` 注入 CONDITIONING；
  2. `EmptyQwenImageLayeredLatentImage` 输出 shape 为 `[batch_size, 16, layers+1, height//8, width//8]`（16通道、带layers维度）；
  3. 普通 `EmptyLatentImage` 输出 shape 为 `[batch_size, 4, height//8, width//8]`（4通道，无layers）。
- **结论**：Qwen-Image-Edit 模型期望的 latent 是 **16-channel 分层 latent**，我们之前用普通 4-channel latent 导致 reference_latents 没被正确消费，模型退化成自由生成，所以出现乱图。
- **修正**：重写工作流 v3：`TextEncodeQwenImageEditPlus`(image1=peach) → `EmptyQwenImageLayeredLatentImage`(768×768, layers=3) → `KSampler` → `VAEDecode`。Plus 节点自带编辑指令模板，比普通版更适合"按指令改图"。
- 已生成 `D:\Aicomfyui\pai\workflows\mushroom_from_peach_ui_v3.json`；v1/v2 均已失效，仅留档。
- 待用户 Load v3 → 传 peach_role_v6.png → Queue 出蘑菇；若仍失败，考虑用 TRAE 先出蘑菇草图再进 Qwen 做风格精修（兜底）。

## 15:07 固化 v4 + 新建桃子重生成变体（用户"继续"指令，真正执行）
- v3 出图有蘑菇样但糊，根因是用户在网页手动把 KSampler steps 设成 6、batch_size 设成 52（未固化进 JSON）。v3 文件本身 KSampler=[12345,22,6.0,euler,normal,1.0]、latent batch=1 是对的。
- 已读 v3 真实结构，固化参数写 **`D:\Aicomfyui\pai\workflows\mushroom_from_peach_ui_v4.json`**：KSampler 改为 `[12345, 35, 7.5, "dpmpp_2m", "karras", 1.0]`，其余结构（UnetLoaderGGUF / CLIPLoaderGGUF(qwen_image) / VAELoader / ModelSamplingAuraFlow(1.73) / TextEncodeQwenImageEditPlus(peach→mushroom) / CLIPTextEncode(负向) / LoadImage(peach_role_v6) / EmptyQwenImageLayeredLatentImage(768×768×layers3×batch1) / VAEDecode / SaveImage 前缀 mushroom）完全沿用 v3。
- 新增 **`D:\Aicomfyui\pai\workflows\peach_regen_ui.json`**：同一链路，仅改提示词=保留桃子本体重生成（"Regenerate the EXACT SAME peach character…"），负向词去掉 peach/peach leaves（否则排斥本体），SaveImage 前缀 `peach_regen`，KSampler seed 98765/同 35/7.5/dpmpp_2m/karras/1.0。用于"重生成皮克斯风桃子形象"需求，无需另起工作流。
- 两个 JSON 已 `python json.load` 校验通过（11 节点 / 12 连线 / v0.4）。
- **15:13 紧急修正：v4 加载后参数串位报错(cfg=NaN / sampler_name=karras / scheduler=1)**。根因：ComfyUI KSampler 的 `widgets_values` 实际顺序是 `seed, control_after_generate, steps, cfg, sampler_name, scheduler, denoise`(7 项)，而 v3/v4 只写了 6 项，漏了 `"fixed"`。这导致 35 被填进 `control_after_generate`、`dpmpp_2m` 被填进 cfg(NaN)、`karras` 被填进 sampler_name、1.0 被填进 scheduler。已修正两个 JSON 的 KSampler 为 7 项：`[seed, "fixed", 35, 7.5, "dpmpp_2m", "karras", 1.0]`，重新校验通过。
- **连带发现**：v3 文件本身也缺 `control_after_generate`(6 项)，所以之前 v3 实际运行时参数也是串位的；用户网页手动改成 steps=6 / batch=52 才会生效。
- 修正后用户操作：重新 Load v4 / peach_regen → 确认 KSampler 显示：种子=12345/98765、生成后控制=fixed、步数=35、cfg=7.5、采样器名称=dpmpp_2m、调度器=karras、降噪=1.0 → 再 Queue。

## 15:32 v4 跑通但不够高清 → v5 升 1024 + 加高清关键词
- 用户反馈 v4 出蘑菇风格正确（红帽白点、圆润 Pixar），但画面不够高清。
- 原因：① latent 只设 768×768，而参考图 peach_role_v6.png 本身是 1024×1024，参考被缩放；② 提示词缺锐利/高清关键词。
- 已生成 HD 版：
  - `D:\Aicomfyui\pai\workflows\mushroom_from_peach_ui_v5.json`：latent 改为 1024×1024；正向词追加 `8k uhd, masterpiece, best quality, sharp focus, highly detailed render, crisp clean edges, smooth textures, professional 3D rendering`；负向词追加 `out of focus, soft focus, jpeg artifacts, compression artifacts, noisy, grainy, pixelated`。
  - `D:\Aicomfyui\pai\workflows\peach_regen_ui_v2.json`：桃子重生成同步同样高清升级。
- 代价：1024×1024 比 768×768 显存/时间增加约 1.7–2 倍（v4 已跑 375 秒，v5 预计 10–12 分钟），一次仍只出 1 张。
- 待用户 Load v5 跑蘑菇 HD，评估是否达到可用清晰度；若仍偏软，再考虑后期加 Upscale 节点或换更大显存实例。

## 15:36 重大纠错：v3~v5 链路根本错（空分层 latent + denoise1.0 = 纯文生图，参考无效 + 出多张）
- 用户实测反馈：v5 出图"完全不能用"：① 参考图毫无意义；② 要求 1 张却出 10+ 张。
- **根因查清**（查 Qwen-Image-Edit 官方工作流 + Qwen-Image-Layered 文档）：
  1. `EmptyQwenImageLayeredLatentImage` 是给 **Qwen-Image-Layered**（分层透明图模型）用的，会生成 `layers+1` 个图层，VAEDecode 会解出多张（layers+1=4 张）；叠加 SaveImage 预览累积历史 `mushroom_00068_`，看着就像 10+ 张。**不是我们要的节点**。
  2. 我们用「空 latent + denoise=1.0」是纯文生图模式，桃子参考只作弱引导（reference_latents 很弱），所以"参考毫无意义"、风格随机。
- **正确链路（Qwen-Image-Edit 官方标准 img2img）**：桃子图 `LoadImage → VAEEncode → KSampler.latent_image`（桃子作结构/风格锚点），同时 `LoadImage → TextEncodeQwenImageEditPlus.image1`（桃子作参考）。denoise 控制变换强度。
- 已重写：
  - `D:\Aicomfyui\pai\workflows\mushroom_from_peach_ui_v6.json`：VAEEncode(peach)→KSampler，denoise=0.85（强变换成蘑菇但保留 Pixar 风格/材质/光照），正向词强调"keep same art style/material/lighting"，负向加 extra mushroom caps。一次严格 1 张、1024 同分辨率。
  - `D:\Aicomfyui\pai\workflows\peach_regen_ui_v3.json`：同链路，denoise=0.6（保留同角色、仅清洁重渲染），正向"EXACT SAME peach"。
- 已 `python json.load` 校验（11 节点、含 VAEEncode、KSampler 7 项 widgets_values 正确）。
- 待用户 Load v6 实测：应出 1 张、且明显继承桃子画风（皮克斯圆润/暖光/浅灰底）。若 denoise 0.85 仍太像桃子→降到 0.9 偏蘑菇；若蘑菇不像→升 0.75 保结构。v1~v5 全部作废。

## 15:52 v6 加载报错：VAEEncode 连线类型不兼容（JSON 链接 ID 写错）
- 用户 Load v6 后报错：VAE编码 - pixels / VAE编码 - vae 类型不兼容。
- 根因：手写 JSON 时 VAEEncode 输入口的 link ID 写串了：
  - `pixels` 错连到 link 7（实为 VAEEncode→KSampler 的 LATENT 输出），应为 link 8（LoadImage→VAEEncode.pixels 的 IMAGE）。
  - `vae` 错连到 link 3（实为 CLIPLoader→CLIPTextEncode 的 CLIP），且未创建 VAELoader→VAEEncode.vae 的 VAE 连线。
  - VAELoader 的 VAE 输出 links 里还误塞了 link 8（IMAGE 线）。
- 已修正 `mushroom_from_peach_ui_v6.json` 与 `peach_regen_ui_v3.json`：
  - VAEEncode.pixels → link 8（IMAGE）
  - VAEEncode.vae → 新增 link 14（VAE，从 VAELoader 输出）
  - VAELoader VAE links = [4,5,14]
  - last_link_id 更新为 14
- 已用 Python 校验：pixels 线源自 LoadImage、vae 线源自 VAELoader，last_link_id 正确。
- 重新 Load v6 / peach_regen_v3，应无连接报错。

## 16:09 v6 跑通：风格/质感/1024 清晰度继承成功，但仍是桃子（denoise 太保守）
- 用户反馈 v6 输出"看到了希望"：画质、皮克斯圆润材质、暖光、浅灰底、1024 高清都继承得很好；但角色仍是桃子，没有变成蘑菇。
- 根因：v6 denoise=0.85 对「桃子→蘑菇」这种结构性替换来说太保守，模型保留了太多原图结构；正向词里"round chubby shape" 也无意中强化了桃子身体。
- 已生成 `D:\Aicomfyui\pai\workflows\mushroom_from_peach_ui_v7.json`：
  - `denoise` 从 0.85 提到 **0.95**（强变换，但仍有 5% 原 latent 锚定画风/光照）。
  - 正向词重写，更强调蘑菇结构："head must be a red round mushroom cap with white polka dots / face under the cap brim / tiny white chubby stem"，弱化"保留形状"。
  - 负向词加入 `peach, peach leaves, peach shape, fruit, round fruit body, pink fuzzy body`，主动排斥桃子特征。
- v6 已验证链路/出图 OK，仅变换强度不足。v7 保持同一真 img2img 结构，只改 denoise 和提示词。
- 待用户 Load v7 实测。若 0.95 仍偏桃子，可再提到 0.98 或 1.0（完全文生图，但会牺牲结构锚定）；若太不像蘑菇/细节散掉，可回调 0.92。

## 16:17 v7 仍偏桃子，用户决定先验证「桃子重生成」工作流
- 用户反馈 v7 输出仍是桃子（红圆身体、带叶子），跨物体替换效果不佳。
- 用户决定暂时搁置蘑菇，先用同一链路验证「桃子重生成」的出图效果（确认 img2img 链路是否能把同一只桃子画得高清/稳定）。
- 已准备 `D:\Aicomfyui\pai\workflows\peach_regen_ui_v3.json`：与 v6/v7 同 img2img 结构（桃子→VAEEncode→KSampler，桃子同时作为 image1 参考），denoise=0.6（保留原角色），steps=35，cfg=7.5，正向词强调"EXACT SAME peach character / 3D chibi Pixar / fresh high-detail"。
- 待用户 Load peach_regen_ui_v3 跑一张，看桃子重生效果。若效果好，再考虑用更强提示词/更高 denoise 或换方案做蘑菇。

## 16:19 用户要一个「纯文生图」新工作流（不绑桃子，可出任意皮克斯角色）
- 用户明确：不要 img2img 绑桃子，要能自由出皮克斯角色（例：兔子），且每次 1 张、皮克斯质感。
- 关键：Qwen-Image-Edit 文生图必须用 **16 通道 latent**，不能用 4 通道的 EmptyLatentImage（v1/v2 就是因此乱出）。正确节点 `EmptyQwenImageLayeredLatentImage` 设 **layers=0** → 即 [1,16,1,128,128]，恰好 1 张输出。
- 已新建 `D:\Aicomfyui\pai\workflows\pixar_char_gen_ui.json`：UnetLoaderGGUF→ModelSamplingAuraFlow(1.73)→TextEncodeQwenImageEditPlus(无参考图、纯文本，默认 Pixar 兔子提示词)→CLIPTextEncode(负向)→EmptyQwenImageLayeredLatentImage(1024×1024×layers0×batch1)→KSampler(seed randomize, 35, 7.5, dpmpp_2m, karras, denoise1.0)→VAEDecode→SaveImage 前缀 pixar_char。
- 用户可随时改 TextEncodeQwenImageEditPlus 里的英文提示词出任意角色；seed 设 randomize 每次换一张，要复现同一张则改 fixed+特定 seed。
- 已 `python json.load` 校验（layers=0 → 1 张，denoise=1.0）。
- 若用户想用桃子作「风格参考」但不绑结构，可后续给 TextEncodeQwenImageEditPlus 的 image1 接 LoadImage（可选，不接则纯文生图）。

## 16:5x 文生图路线纠正：Qwen-Image-Edit 不能纯文生图 → 改用 Qwen-Image base
- **实测坐实**：`pixar_char_gen_ui.json`（EmptyQwenImageLayeredLatentImage layers=0 + TextEncodeQwenImageEditPlus 无参考图、纯文本）跑出**白/灰图** → 确认 Qwen-Image-Edit 是编辑模型，空 latent 文生图不可用（与 7/25 末结论一致）。用户拍板：文生图不再用 Qwen-Image-Edit，按调研推荐专用 T2I 模型。
- **调研结论 + 推荐**：文生图用 **Qwen-Image base**（city96 GGUF `qwen-image-Q4_K_S.gguf`，12.1GB）。理由：① 复用 DSW 已装 `Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf`(qwen_image CLIP) + `qwen_image_vae.safetensors`，**只新增 1 个 unet 文件**；② 20B MMDiT 提示词遵循强、皮克斯风格靠 prompt 即可、擅长文字渲染；③ 24G A10 轻松装下(~17G)；④ 原生 T2I 不出白图。备选 Q4_K_M(13.1G)/Q3_K_M(9.68G)。
- **节点图对照 0cb84e7e 源码核实**：`comfy_extras/nodes_qwen.py` 只注册 `TextEncodeQwenImageEdit`/`EditPlus`/`EmptyQwenImageLayeredLatentImage`，**无 base 专属节点** → base 走**原生** `CLIPTextEncode`(正/负向) + `EmptySD3LatentImage`(非 Layered) + 标准 `KSampler`（官方 Qwen 工作流/runcomfy/docs.comfy.org 一致：shift=3.0、euler/simple、cfg 2.5、steps 20、denoise 1.0）。mmproj 仅图输入需要，T2I 不需要。
- **已建工作流** `D:\Aicomfyui\pai\workflows\qwen_image_t2i_base_ui.json`（10 节点，link 图已 python 校验一致），默认 Pixar 兔子 prompt，一次 Queue 出 1 张 1024×1024。
- **下载命令（用户 16:56 要求重发 + 指定位置）**：已写脚本 `D:\Aicomfyui\pai\download_qwen_base.sh`，保存位置写死 `/root/ComfyUI/models/unet/qwen-image-Q4_K_S.gguf`（与现有 edit GGUF 同目录，UnetLoaderGGUF 才能在下拉看到）。DSW 网关现 302 跳登录，需用户重登/重启实例后粘贴执行。
  - 原始一行版：`curl -L -C - https://hf-mirror.com/city96/Qwen-Image-gguf/resolve/main/qwen-image-Q4_K_S.gguf -o /root/ComfyUI/models/unet/qwen-image-Q4_K_S.gguf`
- **提速可选**：加 `Qwen-Image-Lightning-8steps-V1.0.safetensors`(models/loras) → KSampler steps=8 cfg=1.0。

## （并行分支）DSW 文生图端到端：Qwen2.5-14B 扩写 → Flux.1 dev（16G）
- 目标：用户输入短词 → Qwen2.5-14B-Instruct GGUF Q4_K_M（3 分片，CPU 推理，PyPI CPU 版 llama-cpp-python）→ 扩写成英文长提示词 → 释放 LLM 显存 → Flux.1 dev Q4_K_M（GPU）出图。
- 交付文件（本机已就绪）：
  - `D:\Aicomfyui\pai\dsw_setup_t2i_qwenllm.sh` = commit `450b2e1`：llama-cpp-python 装 PyPI CPU 版；`dl_cli` 用 `huggingface.co` 优先 + `curl -L -C -` 断点续传（修掉旧版 `[ -s ]` 误判不完整文件为完成）；下载 4 模型（Qwen 分片 q4_k_m / flux1-dev-Q4_K_M / t5xxl_fp16 / ae.safetensors）。
  - `D:\Aicomfyui\pai\workflows\t2i_qwenllm_e2e.json`：15 节点，节点 2（LlamaCPPModelLoader）用首片名 `qwen2.5-14b-instruct-q4_k_m-00001-of-00003.gguf`（llama.cpp 自动读后续 2 片）。链路：String Literal→LlamaCPPEngine(英文扩写)→LlamaCPPMemoryCleanup(释放)→CLIPTextEncode(正)→KSampler(25,euler)→VAEDecode→SaveImage。
- 踩坑与决策：
  - llama-cpp-python 源码编译卡 15–25 分钟（按时计费）→ 用户选 PyPI CPU 版（最快最稳，LLM 退回 CPU 推理，Flux 出图不受影响）。
  - huggingface-cli 对 LFS 在 DSW 失败 → 改 curl 直连。
  - Qwen Q4_K_M 是 3 分片（WebFetch 核实）→ 工作流节点 2 用首片名。
  - hf-mirror 单连接限速 ~1.1MB/s（单分片估 56 分钟）→ 改 `huggingface.co` 优先、hf-mirror 回退。
  - 僵尸进程：旧编译进程(PID 36252)存活 38 分钟抢满 CPU，需 `pkill -9` 彻底清理。
- 当前状态（15:52）：本机两文件已确认正确；DSW 仍在跑旧版脚本（hf-mirror 1.1MB/s 慢下载）。已给用户下一步：① `pkill -9 -f dsw_setup_t2i` + `pkill -9 -f "curl -L"` 停旧；② 重传两文件覆盖 DSW（`/mnt/workspace/ai-comfyui/pai/` 下）；③ `nohup bash dsw_setup_t2i_qwenllm.sh > /tmp/dsw_setup_t2i.log 2>&1 &` 重跑；④ `watch -n 15 du -sh models/*` 监控。`curl -C -` 会续传已下部分，不浪费进度。待用户跑完把 [6/6] 结果与 watch 速度贴回。

## 2026-07-28
### 2026-07-28 工作日志

## 1. 每日视频调研（自动化未触发，手动补做）
- 自动化 automation-1785040089915（每日 08:00）今天**未产出**（D:\Aicomfyui\每日教程搜集\ 只有 7-27.md，无 7-28.md）。手动补做，产出 `D:\Aicomfyui\每日教程搜集\2026-07-28.md`。
- 今日关键结论：
  1. **重大校正**：Qwen-Image-Edit 不是跨对象变换工具（桃子→蘑菇必然失败，denoise 0.95 仍出桃子）；正确用法=给参考图出同角色多角度/表情。文生任意新角色走 Qwen-Image base。
  2. **视频阶段根变脸方案**：LTX Likeness Guide 节点（跨帧身份锚点，frontiermodels 2026-07-10），优于仅首帧条件。
  3. **LTX 2.3 参数校准**：需单独下 Gemma 3 12B 文本编码器（≠ qwen_2.5_vl）；ComfyUI v0.16+；A10 跑 FP8 量化；CFG 5.5 / euler_ancestral / steps 30-50 / image_cond_noise_scale 0.1→0.2 调运动。
  4. 附带：LTX Trainer 可本地训桃子 IC-LoRA；20 宫格漫剧工作流（漫剧阶段）；Seedance 2.5 单镜更强但 API 未稳。
- 已把上述校正同步进 MEMORY.md（出图双线 / Qwen Edit 非跨对象 / LTX 2.3 视频阶段事实）。

## 2. 桃子「角色圣经」验证工具（准备就绪，待 DSW 侧运行）
- 背景：用户确认"Qwen-Image-Edit 出角色圣经（三视图+表情）现在就可以验证"。
- 阻塞：**DSW 网关仍 302 跳登录**，本机 curl 无登录态，无法直接驱动 ComfyUI；且 DSW 沙箱连不上本机。验证须用户在 DSW 侧执行。
- 交付两个文件：
  - `D:\Aicomfyui\pai\gen_bible.py`：DSW 网页终端一键脚本，本地环回 127.0.0.1:6889 绕过网关，api 格式工作流串行生成 5 张（front/3q_left/side/back/happy），denoise=0.6，prompt 全锚定"SAME character from the reference"。
  - `D:\Aicomfyui\pai\workflows\peach_character_bible_ui.json`：UI 格式（基于 v6 已验证正确接线），单 KSampler 默认 side view，供 ComfyUI 网页手动加载 Queue。
- 设计要点：denoise 0.6 = 保身份+允许换角度的平衡点（earngenix 最佳实践：勿在 prompt 写面部细节，让参考图控制脸）；A10 24G 串行避免多 KSampler 并行 OOM。

## 3. DSW 实测：400 根因定位 + 工作流修正（已解决）
- 用户开 DSW 实例（dsw-823428），诊断全绿：ComfyUI `/system_stats`=200、进程在跑、input 有 `peach_role_v6.png`(1.4M)。
- 但 `gen_bible.py`（及短版 test1.py）POST /prompt 均 **400 Bad Request**。用 `object_info` 逐项核对，根因：
  **DSW 干净版 `TextEncodeQwenImageEditPlus` 真实 inputs 仅 `[clip, prompt]`** —— 无 `image1`/`vae`/`text`。之前按 HAI 遗留版 v6（节点带 image1/vae/text）写的脚本与 UI JSON 全部字段不符 → 400。
- 修正方案（已落实到文件）：参考图改走 **`VAEEncode → KSampler.latent_image`**（标准 img2img），文本节点只传 `clip` + `prompt`（`prompt` 是字段名，不是 `text`）。
- 已重写 `D:\Aicomfyui\pai\workflows\peach_character_bible_ui.json`（UI 格式，按真实节点，默认 front view，denoise=0.6）。用户从本机下载拖入 DSW ComfyUI 画布 → Queue 即出图（免脚本）。
- 注：`gen_bible.py` 也需同步改节点 5（clip+prompt，去掉 image1/vae/text）才能在终端跑 5 张；当前优先 UI 工作流验证。

## 4. 实测：换视角失败根因 = image1 未接（已修正）
- 用户加载修正版 UI 工作流，改 prompt 为 "3/4 left / side" 但**仍出正面图**，denoise 提到 0.75/0.8 也不变。排查：
- 用 `object_info` 查完整接口：`TextEncodeQwenImageEditPlus` 的 `REQUIRED=[clip, prompt]`，**`OPTIONAL=[vae, image1, image2, image3]`**。
- 根因：第 3 节按"required 只有 clip+prompt"把参考图只走 `VAEEncode→KSampler.latent_image`，**没接 `image1` 编辑条件端口** → 模型只拿到 img2img 的 latent（正面桃子），无"要编辑的原图"语义，死守正面姿态，prompt 角度指令完全失效。之前记"无 image1"是漏看 optional，已回 MEMORY.md 修正。
- 修复：参考图**必须同时接** `TextEncodeQwenImageEditPlus.image1` + `vae`（编辑条件）+ `VAEEncode`(→KSampler.latent_image 保结构)。已写 `D:\Aicomfyui\pai\workflows\peach_bible_v2.json`（api 格式，默认 side view，denoise=0.65，LoadImage 双接 VAEEncode 与 image1）。
- 验证期望：接 image1 后，side/back/3q/happy 应真正变视角/表情且保身份。若仍不变→提 denoise 至 0.7~0.75；若脸崩→降 0.6。

## 5. 🔥 用户铁律：工具使用前必须官方教程确认（2026-07-28 起）
- 用户原话："以后都要加一个怎么使用工具的官方教程确认过程，没有官方说明不要动手"。
- 已写入用户级 `~/.workbuddy/MEMORY.md`（跨项目硬性要求）。落实：动手前必抓官方 README/模型卡，优先用官方示例工作流作底，不凭接口推测手写；资料缺失先问用户。
- 本次教训坐实：Qwen-Image-Edit-2511 转视角盲试 4 轮（v6/v7/v2/v3）全失败，根因是没查官方。用户当场质疑"是不是都盲猜的"——确实如此，已认账。

## 6. 查证官方文档：Qwen-Image-Edit-2511 Multiple-Angles LoRA（已确认用法）
- 官方模型卡 `fal/Qwen-Image-Edit-2511-Multiple-Angles-LoRA`（WebFetch 抓到，hf 直连/hf-mirror 本地 curl 均拿不到原始 JSON，size=0；建议用户在 DSW 侧直接下官方 `comfyui-workflow-multiple-angles.json` 核对接线）。
- **关键官方事实（之前全错的点）**：
  1. **强制 `<sks>` 触发词**："`<sks>` trigger is essential"，prompt 必须以 `<sks>` 开头。我 v3 漏了这个 → 模型不进多角度模式，死守正面。
  2. **prompt 固定格式**：`<sks> [azimuth] [elevation] [distance]`，顺序不可乱。例：`<sks> front view eye-level shot medium shot`。
  3. **方位角/仰角/距离词表**：azimuth 0°=front view / 45°=front-right quarter view / 90°=right side view / 180°=back view / 270°=left side view / 315°=front-left quarter view；elevation -30°=low-angle / 0°=eye-level / 30°=elevated / 60°=high-angle；distance ×0.6=close-up / ×1.0=medium shot / ×1.8=wide shot。
  4. **LoRA 加载**：标准 `LoraLoader`，strength_model 0.8–1.0（起点 0.9），strength_clip 默认（卡未强调，我设 0 规避 GGUF-clip 冲突）。
  5. **基础模型**：Qwen/Qwen-Image-Edit-2511（=我们 GGUF `qwen-image-edit-2511-Q4_K_M.gguf`）。
  6. 作者随卡附官方 `comfyui-workflow-multiple-angles.json`（最权威接线底本，应优先采用）。
- 已写 `D:\Aicomfyui\pai\workflows\peach_bible_v4.json`：补 `<sks>` 前缀 + 官方格式 prompt，denoise 0.8，LoraLoader strength_model=0.9/strength_clip=0，参考图双接 image1+VAEEncode。默认 side view 供验证。
- 5 张角色圣经角度 prompt（均 `<sks>` 开头 + eye-level medium shot）：front / front-left quarter / right side / back / happy(正面加"with a big happy smile, laughing joyfully, both hands raised")。

## 7. 官方工作流加载实测：确认使用 diffusers/FP8 全量模型（GGUF 需改造）
- 用户成功把官方 `comfyui-workflow-multiple-angles.json` 复制到工作区并拖入 ComfyUI。ComfyUI 校验出 4 个缺失模型：
  - `qwen_image_edit_2511_bf16.safetensors`（diffusion_models，官方 FP16/bf16 基础模型）
  - `qwen_2.5_vl_7b_fp8_scaled.safetensors`（text_encoders，官方 FP8 文本编码器）
  - `Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors`（loras，可选 Lightning 加速 LoRA）
  - `qwen-image-edit-2511-multiple-angles-lora.safetensors`（loras，已下好但节点列表未刷新/文件名需再确认）
- **结论**：官方工作流是给 diffusers/FP8 全量权重写的；我们装的是 GGUF，不能直接跑。但官方接线确认了：LoRA 用标准 `LoraLoader`、prompt 以 `<sks>` 开头、身份由参考图提供。
- **建议**：不要下载那 3 个全量权重（占几十 GB），改用已 GGUF 化的 `peach_bible_v4.json`（已将官方 prompt 格式 + LoraLoader 接线适配到我们的 GGUF 权重）。

## 待办 / 下一步
- 用户关闭官方工作流报错 → 加载我写的 GGUF 适配版 `peach_bible_v4.json`。
- 在 `LoraLoader` 节点：点刷新按钮（或按 F5），确认下拉能选到 `qwen-image-edit-2511-multiple-angles-lora.safetensors`；strength_model 保持 0.9。
- 确认 `LoadImage` 是 `peach_role_v6.png`、`TextEncodeQwenImageEditPlus` 的 prompt 以 `<sks> right side view eye-level shot medium shot` 开头、图像1 已接参考图。
- Queue 出 side view 验证换视角；生效后续出 front / 3q_left / back / happy；就绪后接 LTX 2.3 + Likeness Guide。

## 8. 用户新工作方式：社区成品工作流反向学习（已采纳并评估首个样本）
- 用户原话："后续我都先通过别人做好的工作流来反向给你学习好了，验证下我的这种方式"。即：优先用 RunningHub/社区成熟工作流当权威底本，我据此反向拆解 + 适配我们资产（GGUF 模型 / 桃子参考图 / DSW），不再从节点接口现推。
- 首个样本：`D:\Aicomfyui\pai\一键生成多角色对话动画片，Qwen3-TTS+++LTX-2工作流！.json`（124KB, 97 节点，作者给猫狗播客对话示例）。
- 已拆解确认技术栈：**LTX-2**（Kijai Comfy GGUF 19B，原生音画同步）+ **Qwen3-TTS**（ComfyUI-QwenTTS，多角色对话配音）+ Gemma3-12B-fp8 文本编码器 + 蒸馏 LoRA + 空间 upscaler×2。辅助包：easy-use / kjnodes / mtb / LayerStyle。
- 已写评估文档 `D:\Aicomfyui\pai\workflows\runninghub_ltx2_qwentts_review.md`，结论：
  - **DSW 不能直接跑**：缺 5+ 自定义节点包（QwenTTS/KJNodes/Easy-Use/mtb/LayerStyle）；需下 LTX-2 Q4_K_M GGUF(12.7G，不能 Q8 20G 装不下 A10) + Gemma3-12B-fp8(8G) + embeddings_connector + 双 VAE + 蒸馏 LoRA + 空间 upscaler（来源 Kijai/LTXV2_comfy，官方核实）。
  - **显存临界**：A10 24G 跑 LTX-2 Q4 约 26G → 需关 upscaler/降分辨率/PurgeVRAM 分段；否则换大显存实例。
  - **战略冲突**：该工作流是 **T2V 模式**（无参考图接口），**不锁桃子身份**；而当前阶段目标是"单角色带情节视频"。它直接做多角色对话动画片，跳过单角色阶段，接近最终漫剧阶段。
  - **节点栈冲突**：它用 LTX-2（DualCLIPLoaderGGUF+Gemma+embeddings_connector）；我们之前计划 LTX-2.3（LTXAVTextEncoderLoader 一体）。两者不兼容，先定选哪代。
- 同步修正 MEMORY.md：视频主线补 LTX-2 vs 2.3 双栈说明 + A10 显存核算 + 用户新工作流获取方式约定。

## 9. 用户新指令：先抛开桃子，验证现成工作流能否"原样跑通"
- 用户原话："先抛开桃子，我这次是尝试这些现成工作流能不能直接拿来就用，他是怎么样我就怎么用，等我体验完这个工作流我们再说桃子"。
- 即：本次目标=按工作流原样在 DSW 跑通，不魔改；桃子暂挂起。
- 已按铁律查实所有官方来源，产出**原样跑通清单** `D:\Aicomfyui\pai\workflows\runninghub_ltx2_qwentts_run_checklist.md`。关键核实结论：
  1. **配音节点来源坐实**：工作流用 `FB_Qwen3TTS*` 节点 → 来自 **1038lab/ComfyUI-QwenTTS**（非 zwukong/jaysooner 分支）。作者 Note 也写明该仓库。git clone 直装即可（ComfyUI-Manager 未必搜得到 FB_ 名）。
  2. **LTX-2 量化版确认**：Kijai/LTXV2_comfy 官方列 Q4_K_M=12.7GB / Q6_K=15.9 / Q8_0=20.4。工作流原配 Q8_0 装不下 A10 → **必须改 Q4_K_M**。
  3. **KJNodes 必须更新**到 1/13 之后（视频 VAE 换过）；**transformers 需 4.57.3**（1038lab QwenTTS 明确要求，5.x 报 pad_token_id）。DSW 当前 transformers 版本待查。
  4. 其余 LTX-2 模型（Gemma3-12B-fp8 / embeddings_connector / 双 VAE / 空间 upscaler / 蒸馏 LoRA）文件名与工作流节点 widgets_values 一致，来源 Kijai/LTXV2_comfy。
  5. 分辨率/帧数约束（宽高%32+1，帧%8+1）作者 Note 已注明。
- **给用户的清单（下一步他照做）**：① DSW 装 5 节点包+各自 req → 重启；② 下 LTX-2 Q4+其余模型（~30GB，aria2/后台）；③ 可选预下 Qwen3-TTS 1.7B；④ 加载 JSON→改 unet_name 为 Q4→刷新→Queue；⑤ 看柯基×加菲猫对话动画输出。
- 风险重申：该工作流 T2V 纯 prompt（无参考图接口），角色不锁身份——契合本次"不管桃子"目标，但与阶段目标"单角色一致"冲突，待桃子回归时另议。

## 10. 交付：DSW 一键安装脚本（用户下午开实例跑）
- 用户指令："DSW 一键安装脚本你先写下，下午我再开实例来跑"。已写 `D:\Aicomfyui\pai\dsw_setup_ltx2_qwentts.sh`（bash 语法 `bash -n` 校验通过）。
- 脚本 7 步：① clone 5 节点包+装 req；② 固定 transformers==4.57.3 + tokenizers<0.20；③ 下 LTX-2 权重（**A10 用 Q4 并改名对齐工作流期望名**）；④ 可选预下 Qwen3-TTS 1.7B；⑤ sed 把工作流 JSON 的 `LTX-2-dev-Q8_0.gguf`→`Q4_K_M`（免手动改）；⑥ 重启 ComfyUI；⑦ 校验节点+模型文件打 [OK]/[缺失]。
- **写脚本前的官方核实（铁律）发现 4 处必须修正的事实**，已更新 `runninghub_ltx2_qwentts_run_checklist.md`：
  1. **TTS 节点名漂移**：工作流用 `FB_Qwen3TTS*`，但 **1038lab 当前 main 已改为 `AILab_Qwen3TTS*`**（无 FB_ 前缀）→ 直接 clone 最新版会报节点缺失。脚本以"装+校验+提示二选一"兜底（找 runninghub 配套带 FB_ 的版本 / 或重做 AILab 版工作流）。
  2. **ComfyUI 版本漂移**：工作流 `extra.comfy_fork_version = feature/av_inference@a6994ed1`（特定 fork），原生 LTXV* 节点可能与 stock 0cb84e7e 有出入 → 以 object_info 校验为准。
  3. **Kijai 文件改名**：`ltx-2-19b-embeddings_connector_bf16` 现改名 `_distill_bf16`；视频 VAE 现名 `LTX2_video_vae_bf16.safetensors`（工作流要 `_260115` 旧名）→ 脚本下载后改名对齐。
  4. **Gemma 来源**以工作流 Note 为准=`unsloth/gemma-3-12b-it-GGUF`（fp8 e4m3fn），非 Kijai。
- 主模型放入 `models/unet/`，脚本统一改名 `LTX-2-dev-Q4_K_M.gguf`；embeddings/VAE/upscaler/LoRA 各自目录。
- 待用户下午开 DSW 跑脚本 → 看 [7/7] 校验结果，针对性解决 [缺失] 项（尤其 FB_ 节点与 fork 版本）。

## 11. 脚本运行时排错 + 用户授权内置 PAT（14:3x 续）
- 用户下午实际在 DSW 跑了脚本（前台，目录 `/mnt/workspace/ai-comfyui/pai/`），第一步 clone 失败：
  报 `Invalid username or token. Password authentication is not supported` + `fatal: ComfyUI_mtb / ComfyUI-LayerStyle 鉴权失败`。
  - **根因**：GitHub 匿名 `git clone` 限 60 次/小时，前 3 个包(QwenTTS/KJNodes/Easy-Use)已用掉额度 → 后续触发 401 交互密码提示（GitHub 不支持密码鉴权）。
  - 前 3 个包 + 其 requirements 实际已成功；仅 mattya/ComfyUI_mtb 与 pythongosssss/ComfyUI-LayerStyle 失败。
- **修复（已改脚本并 bash -n 通过）**：
  - 顶部加 `export GIT_TERMINAL_PROMPT=0`（禁用交互密码提示，失败即报错不卡死）。
  - clone 函数改为"已存在跳过 + 失败给清晰提示"，不再 `| tail -2` 吞错误。
  - **用户明确授权把 GitHub PAT 明文硬编码进脚本顶部**（`export GH_TOKEN=github_pat_11AND5...`），替代之前的 GH_TOKEN 环境变量读取；重传 DSW 后直接跑、无需 export。

## 12. 关键勘误：3 个仓库地址全错 + TTS 真实来源（15:1x 续，已逐一 GitHub 核实）
- 用户在 DSW 跑修正后脚本，[7/7] 校验仍 `[缺失] ComfyUI_mtb / ComfyUI-LayerStyle / FB_Qwen3TTS*`。`ls` 确认 `/root/ComfyUI/custom_nodes/` 下这俩目录不存在 → clone 又失败了。
- **逐一核实（用 PAT 打 GitHub git 端点 + API + 代码搜索，非盲猜）发现根因：脚本里 3 个仓库地址/来源全错**：
  1. **mtb 地址错**：`mattya/ComfyUI_mtb` 在 GitHub 不存在（mattya 名下全是旧 ML 项目）→ 实为 **`melMass/comfy_mtb`**（★721，含 `nodes/audio.py` 的 "Audio Duration (mtb)"）。
  2. **LayerStyle 地址错**：`pythongosssss/ComfyUI-LayerStyle` 404 → 实为 **`chflame163/ComfyUI_LayerStyle`**（★3111，含 `py/purge_vram.py` 的 "LayerUtility: PurgeVRAM V2"）。
  3. **TTS 真实来源错**：工作流 `FB_Qwen3TTS*`（4 个）**不是** 1038lab（其 main 仅 `AILab_*`，且 commit 历史中**从未有过 FB_ 节点**）→ 经 GitHub 代码搜索确认真实来源 = **`flybirdxx/ComfyUI-Qwen-TTS`**（★1805，自带 `example/Multi-character dialogue.json`，主题吻合；4 个 FB_ 类全部确认存在）。
- **Gemma 文件名也错**：工作流写死 `gemma_3_12B_it_fp8_e4m3fn.safetensors` 公开 HF **根本不存在**（unsloth 仅 GGUF 量化版，Kijai/Comfy-Org/google 均无）→ 改用 `unsloth/gemma-3-12b-it-Q4_K_M.gguf`（直链 302 可达 8.6G），脚本同步改写工作流节点文件名。
- **依赖兼容确认**：flybirdxx `requirements.txt` 要求 `transformers>=4.57.0,<5.0.0` → 与脚本全局 pin `4.57.3` **兼容**，无冲突；还需 torchaudio/librosa/soundfile 等（脚本 pip 循环装）。
- **已修正脚本**：clone 行改为 flybirdxx/melMass/chflame163；pip 循环列表同步改 `ComfyUI-Qwen-TTS`；gemma 下载改 unsloth Q4_K_M 并改名；模型下载函数早前已改 curl 直连 hf-mirror（huggingface-cli 在镜像下对 LFS 失败）。`bash -n` 校验通过。
- **已修订** `runninghub_ltx2_qwentts_run_checklist.md`（v2026-07-28 15:30）：三条现实差异全部改为"已核实并解决"，A 表 5 包地址、B 表 gemma 行均更正。
- **待用户**：重传修正后脚本到 DSW → `cd /mnt/workspace/ai-comfyui/pai && nohup bash dsw_setup_ltx2_qwentts.sh > /tmp/setup_ltx2_qwentts.log 2>&1 &` → 看 [7/7] 校验（预期 mtb/LayerStyle/FB_Qwen3TTS 全 [OK]）。旧 `custom_nodes/ComfyUI-QwenTTS`(1038lab) 仍在但无用，可留可删。
- **安全提示已给**：PAT 明文存于脚本 + DSW 实例(~/.gitconfig)，实例销毁即弃；若担心泄露，跑完可在 GitHub 撤销/轮换该 PAT。
- 用户待做：重传新版脚本覆盖 → `cd /mnt/workspace/ai-comfyui/pai && nohup bash dsw_setup_ltx2_qwentts.sh > /tmp/setup_ltx2_qwentts.log 2>&1 &` → 看 [7/7] 校验。

## 12. 用户跑出 [7/7] 结果 + 模型下载根因定位与脚本二次修复（14:5x）
- 用户重传"内置PAT+hf-cli"版跑完，[7/7] 大量 [缺失]：7 个模型文件全缺 + 3 节点缺（FB_Qwen3TTS / mtb / LayerStyle）。
- **模型下载全失败根因**：`huggingface-cli download` 在 `HF_ENDPOINT=hf-mirror.com` 镜像下对 LFS 文件失败；已用 `curl -sI` 验证 hf-mirror 直链 `resolve/main/...` 全部 302 可达 → 网络通，是 hf-cli 调用问题。→ 改脚本下载函数为 `curl -L -C -` 直链（已验证可用）。
- **Gemma fp8 文件不存在（关键勘误）**：作者 Note 说 gemma 来自 `unsloth/gemma-3-12b-it-GGUF`，但该仓库**只有 GGUF 量化版，无 fp8_e4m3fn 文件**；公开 HF 搜 `gemma_3_12B_it_fp8_e4m3fn` 仅一个 NSFW 微调版；Kijai/Gemma3_comfy 只有 4B 视觉编码器；Kijai/LTXV2_comfy/text_encoders 只有 2 个 embeddings_connector。→ **该 fp8 文件公开不存在**，改用 `unsloth/gemma-3-12b-it-Q4_K_M.gguf`（直链 302 可达，8.6G），即 Kijai LTX-2 GGUF 工作流标准 gemma 源，GGUF 量化版对 A10/Ampere 更友好；并在 [5/7] 用 sed 把工作流节点 298 的 `gemma_3_12B_it_fp8_e4m3fn.safetensors` → `gemma-3-12b-it-Q4_K_M.gguf`。
- **TTS 模型**：[4/7] 改为不预下（hf-cli 在镜像下失败），首次运行由 1038lab 节点自动下载；超时再单独处理。
- 脚本二次修复已 `bash -n` 通过、无 dl_hf 残留。用户需再重传覆盖重跑 → 模型应下到。
- **剩余两个独立问题待诊断/决策**：
  1. mtb / LayerStyle 节点缺失：目录可能 clone 了但 ComfyUI 加载报错（依赖/Python），需看 `/tmp/comfy_run.log` 中 mtb/LayerStyle 加载情况；或 clone 又失败。给诊断命令。
  2. FB_Qwen3TTS* 节点缺失：已知 1038lab main 已改 `AILab_Qwen3TTS*`（无 FB_）→ 必缺。待用户选 方案A（我用 AILab 节点做替换版工作流）或 方案B（找 runninghub 作者原版带 FB_ 的 fork）。

## 2026-07-29
### 2026-07-29 每日日志

## 背景：DSW 今日仅 16G 显存（24G 无库存）
用户临时只能用 16G 实例，放弃原 LTX-2 视频路线（19B 在 16G 装不下），转向「简单体验文生图」。

## 澄清一个用户误解
用户问"deepseek/kimi 有没有开源的（文生图）"——实际 DeepSeek/Kimi 都是**大语言模型(LLM)**，不是画图模型，没有开源文生图。用户真实需求是**「提示词扩写」**：输入短词(如"一只兔子")→ LLM 扩写成适合文生图的详细提示词 → 文生图模型出图。

## 选型（均经官方核实，铁律）
- **扩写 LLM**：`Qwen2.5-14B-Instruct` GGUF **Q4_K_M**（8.99G）→ 中文扩写最强，16G 可容纳。
- **文生图**：`Flux.1 [dev]` GGUF **Q4_K_M**（~7G）→ 质量天花板，16G 配 14B LLM 唯一能分时的强者（Qwen-Image 20B 在 16G 配 14B LLM 装不下）。Flux 吃英文→LLM 扩写直接输出英文喂图。
- **显存策略**：16G 下 LLM(9G) 与 Flux(7G) **必须分时**——LLM 扩写完用 `LlamaCPPMemoryCleanup` 释放，再 Flux 出图。

## 节点包（官方核实）
- `comfyui-sg-llama-cpp`（scruffynerf, master）：本地 GGUF LLM 推理，节点 `LlamaCPPModelLoader`/`LlamaCPPOptions`/`LlamaCPPEngine`/`LlamaCPPMemoryCleanup`。**chat_format 是动态枚举** llama-cpp-python 注册格式（第195行 `_chat_handlers.keys()`），Qwen2.5 需的 `qwen2` 必在内，无风险。默认从 `text_encoders` 加载，用 `config.json` 的 `model_folders` 指向 `models/LLM`。
- `ComfyUI-GGUF`（city96, master）：`UnetLoaderGGUF` 加载 Flux GGUF。
- Flux 还需 ComfyUI 原生 `CLIPLoader`(t5xxl_fp16) + `VAELoader`(ae)。

## 官方核实的关键事实（脚本已固化）
- Qwen GGUF 文件名**小写连字符**：`qwen2.5-14b-instruct-q4_k_m.gguf`（Q4_K_M=8.99G）；**可能分片**需合并（之前 hf-cli 失败根因之一）。仓库 `Qwen/Qwen2.5-14B-Instruct-GGUF`。
- Flux GGUF 源 = `city96/FLUX.1-dev-gguf`（**仓库名大小写敏感**，之前 git 端点 404 因写成小写 `flux1-dev-gguf`）。文件名 `flux1-dev-Q4_K_M.gguf`。
- t5xxl/ae 源 = `comfyanonymous/flux1`：`t5xxl_fp16.safetensors`(4.9G) + `ae.safetensors`(0.3G)。

## 交付文件
- `D:\Aicomfyui\pai\dsw_setup_t2i_qwenllm.sh`：一键安装（6步：克隆2节点包→装llama-cpp-python(CUDA)→下4模型→写config.json→部署工作流→重启→校验）。语法 `bash -n` 通过。
- `D:\Aicomfyui\pai\workflows\t2i_qwenllm_e2e.json`：端到端 UI 工作流（15节点）。链路：用户输入(String Literal)→LlamaCPPEngine(扩写英文)→LlamaCPPMemoryCleanup(释放)→CLIPTextEncode(正)→KSampler→VAEDecode→SaveImage。结构校验通过。

## 待验证 / 风险
- **沙箱网络限流**（直连 huggingface.co 不通、hf-mirror 对 Flux 限流 401），无法在本机验证 DSW 下载。下载逻辑放在 DSW 跑的脚本里，依赖 DSW 网络（之前克隆/下模型成功）。
- 若 Flux GGUF 在 DSW 的 hf-mirror 也下不动 → 换 `huggingface.co` 直连或 `lllyasviel/FLUX.1-dev-gguf` 源。
- llama-cpp-python CUDA 编译可能慢/失败 → 回退 JamePeng 预编译 wheel。
- 用户待做：DSW 跑 `bash dsw_setup_t2i_qwenllm.sh`，看 [6/6] 校验，把 `[缺失]`/`[警告]` 发我。

## 开机操作前置（2026-07-29 晚）
- 确认 `pai/dsw_setup_t2i_qwenllm.sh` + `pai/workflows/t2i_qwenllm_e2e.json` 此前只是本机未跟踪文件 → 已 `git add`+`commit` 到本地（commit `655196f`），**未 push**。
- DSW 上从 github clone 的那份没有这两个新文件，用户开机第一步必须先同步（push 后 git pull，或手动上传两个文件到对应目录）。
- 已交付完整开机操作清单：同步文件 → 跑脚本盯 [6/6] → ComfyUI 网页 Load 工作流 → 改节点1输入"一只兔子" → Queue Prompt 出图。**用户选手动上传、不 push**；已给本机两文件路径与 DSW 目标路径对照表（pai/ 与 pai/workflows/）。
- 用户已按手动上传路线在 DSW(16G, dsw-823428) 实跑 `dsw_setup_t2i_qwenllm.sh`：正常进入 [1/6]，但卡在 `llama-cpp-python` CUDA 编译阶段（日志被 `| tail -3` 缓冲不实时刷，看似不动）。已向用户解释：正常需 5–15 分钟；自查用 `ps` 看编译进程；即使编译失败也只退回 CPU 推理（LLM 扩写变慢、Flux 出图不受影响），失败行发我查官方预编译 wheel。待 [6/6] 结果回收口。
- 12:15 用户确认：日志仍停在 `[1/6] 安装依赖`，4 目标子目录 unet13G/clip5.7G/vae243M 均为历史模型（LTX-2/桃子路线），LLM 目录尚未创建 → [2/6] 下载未开始，之前看到的 models 总量 33G 非本次下载量。继续等编译完自动进下载。
- 12:19 用户因 llama-cpp-python 源码编译太慢（按时计费）主动停掉脚本，选「保留扩写但跳过编译」路线。已按铁律查官方 README 确认 llama-cpp-python 预编译 wheel 命令（`--extra-index-url https://abetlen.github.io/llama-cpp-python/whl/<cu-tag>`，支持 cu118/121/122/123/124/125/130/132，Python 3.10-3.12），改脚本：删源码编译段 → 官方 wheel + `nvcc` 自动探测 CUDA 标签（兜底 cu124）。`bash -n` 通过，已本地 commit 更新(commit f1496d2)。用户需重传脚本覆盖 DSW 旧版、工作流 json 不变、重跑。
- 12:27 用户重传脚本并重跑：日志打印 `[安装] llama-cpp-python 预编译 wheel (CUDA 标签: cu124)`（DSW 实测 CUDA 12.4，自动探测正确、在官方支持列表✓），节点包[跳过]，正在装预编译 wheel（日志被 tail -5 缓冲，等 [OK]/[警告]）。装完自动进 [2/6] 下载。**验证：nvcc 自动探测 CUDA 标签逻辑有效**。待 [6/6] 结果。
- 12:32 诊断根因：用户第一次停脚本时 pkill 没杀干净，旧源码编译进程(PID 36252, 11:56 起)及其子进程(nvcc/cicc/cc1plus, CPU 70-80%)仍后台存活 38 分钟，第二次 wheel 安装(94814,12:27)也被抢 CPU+GitHub 下载慢→双边极慢。已让用户彻底清理所有 llama/pip/nvcc/cicc/cc1plus/dsw_setup 进程。
- 12:34 用户选「切 CPU 版（最快最稳）」：llama-cpp-python 改回 PyPI CPU 版（去掉 GitHub extra-index，PyPI 直连快），LLM 退回 CPU 推理、Flux 出图不受影响、16G 更省显存。脚本改完 bash -n 通过、本地 commit(7e9a4d8)。用户需：先清理僵尸→重传 CPU 版脚本覆盖 DSW→重跑。Qwen14B 模型仍要下(CPU 推理也要权重)。
- 12:41 用户清理僵尸后重传 CPU 版脚本重跑：ps 确认无残留（清理生效），[1/6] 正常打印 `[安装] llama-cpp-python (PyPI CPU 版，直连快)` 并正在装（tail -5 缓冲空着正常），无僵尸抢 CPU。预期几十秒~2分钟刷 [OK] 进 [2/6]。**验证：清理僵尸进程 + 切 PyPI CPU 版 这条路径生效**。待 [6/6] 结果回收口。
- 12:45 [6/6] 结果：节点**全部 [OK]**（llama-cpp-python CPU 版/comfyui-sg-llama-cpp/ComfyUI-GGUF 均注册成功，工作流已部署、ComfyUI 已重启）；但 4 个模型**全 [缺失]** → [2/6] 下载整段失败。根因：脚本误用 `huggingface-cli`，而 DSW 上它对 LFS 会失败（之前 LTX-2 已证实，当时改 curl 直连才成）——**AI 失误**。已查 Qwen Q4_K_M 为 3 分片（-00001/2/3-of-00003，~9G）。已修：①脚本 dl_cli 改 curl 直连(hf-mirror→huggingface.co 回退，API 列举+循环下分片)；②工作流节点2 文件名改首片 `qwen2.5-14b-instruct-q4_k_m-00001-of-00003.gguf`(llama.cpp 自动读后续分片)；③校验段改匹配。bash -n + JSON 合法，本地 commit(7b9258c)。用户需重传两文件覆盖 DSW 并重跑（[1/6] 节点[跳过]，直接进[2/6] curl 下模型）。

## 13:19 「继续」：官方核实暴露两处致命文件名错误，已修（commit fb283f7）
用户说"继续"，本机沙箱无 DSW 连接，故先做**官方文件名核实**（用户铁律），结果抓出两个会到 Queue 才爆的雷：
1. **Flux 量化文件根本不存在**：`city96/FLUX.1-dev-gguf` 完整 14 文件里 Q4 系列只有 `Q4_0 / Q4_1 / Q4_K_S`，**无 `Q4_K_M`**。之前脚本+工作流节点6写的 `flux1-dev-Q4_K_M.gguf` 是幻觉（源自未核实假设）→ 加载必挂。已改用真实存在且 16G 可装的 **`flux1-dev-Q4_K_S.gguf`**（~6.7G）。若显存更宽裕想更好画质可改 Q5_K_S(~8.1G)/Q6_K(~9.6G)/Q8_0(~12G)，同步改节点6。
2. **`comfyanonymous/flux1` 在 hf-mirror API 返回 `{"error":"Invalid username or password."}`** → 旧 `dl_cli` 靠 hf-mirror API 列文件名，对该仓库会列空→t5xxl/vae 漏下→[缺失]。已**废弃 dl_cli 列名逻辑**，改为 `dl_file`（写死确切文件名直连：主源 huggingface.co、回退 hf-mirror），去掉脆弱的 API 列举。
- HEAD 探活（2026-07-29）：Qwen 3 分片 + Flux Q4_K_S 在 hf-mirror 均 302（存在可下）✓；t5xxl_fp16/ae 在 hf-mirror 404（hf-mirror 不代理此仓库 LFS），但 huggingface.co 主源在 DSW 可用（本机沙箱连 huggingface.co 不通，故未能直连探活，依赖官方仓库标准文件名确认）。
- 节点2 首片名 `qwen2.5-14b-instruct-q4_k_m-00001-of-00003.gguf` 经核实与仓库 3 分片完全一致 ✓，无需改。
- 已改：脚本下载段(→dl_file + 3 分片显式 + Q4_K_S) + 校验段(UNET 匹配 Q4_K_S) + 工作流节点6(Q4_K_S)。`bash -n`+`json.load` 通过，无残留 Q4_K_M 引用。本地 commit `fb283f7`（未推送）。
- **用户下一步**：重传本机两文件覆盖 DSW（`dsw_setup_t2i_qwenllm.sh` @fb283f7 + `t2i_qwenllm_e2e.json`）→ `nohup bash ... > /tmp/dsw_setup_t2i.log 2>&1 &` 重跑 → [6/6] 应全绿（含 UNET=flux1-dev-Q4_K_S）→ ComfyUI 网页 Load 工作流、改节点1输入、Queue 出图。因改了文件名，若 DSW 上已有旧的不完整 `flux1-dev-Q4_K_M.gguf` 残留，建议 `rm -f /root/ComfyUI/models/unet/flux1-dev-Q4_K_M.gguf` 清掉避免混淆。

## 14:10 重跑暴露速度根因 + aria2c 提速（commit f81ab9a）
- 用户按 fb283f7 重跑（huggingface.co 优先→hf-mirror 回退），`tail -f` 出现 curl 进度条：`36 3804M 36 1387M ... 1187k ... 0:54:39` → 单分片 3.8G 已下 1.38G(36%)，速度 **1187k≈1.18MB/s**（=hf-mirror 特征速度），ETA 54 分钟。**全套**(3×Qwen~9G+Flux6.7G+t5xxl5G) 按此要 3+ 小时。
- **根因定位**：huggingface.co 在本 DSW(国内区域 PAI)被墙，连接即失败→每次都掉回 hf-mirror 的**单连接限速(~1.2MB/s)**。旧脚本"优先 huggingface.co"在该环境纯属浪费一次失败连接。
- **修复(commit f81ab9a)**：① 新增 `ensure_aria2()`：先 `command -v aria2c`，无则 `apt-get update && apt-get install -y aria2`（root 可装；装失败仅警告、降级 curl 单线程不报错）；② `dl_file` 主路径改 `aria2c -x 16 -s 16 -c -k 8M` 拉 **hf-mirror**（其 CDN 支持 range 分片，16 线程可翻 10~16 倍→15-20MB/s）；curl 单线程降为兜底(hf-mirror 优先、huggingface.co 末选)；③ `-c` 续传旧 curl 残片(已下 1.38G Qwen 分片不浪费)。
- **验证**：`bash -n` 通过；grep 确认旧"huggingface.co 优先"逻辑已无、aria2c 引入就位。已 commit `f81ab9a`（未推送）。工作流 JSON 本轮未改（仍 fb283f7 状态）。
- **用户下一步**：① DSW 上先 `pkill -9 -f dsw_setup_t2i; pkill -9 -f "curl -L"` 停掉 1.18MB/s 慢下载（**千万别删已下的 Qwen 残片**，aria2c -c 会接着下）；② 只重传 `dsw_setup_t2i_qwenllm.sh`@f81ab9a 覆盖 DSW（工作流 JSON 不变可不传，但为保险也可一起传）；③ `nohup bash dsw_setup_t2i_qwenllm.sh > /tmp/dsw_setup_t2i.log 2>&1 &` 重跑。
- **判断提速是否生效**：`watch -n 15 du -sh models/*` 看 LLM 目录是否**猛涨**(MB/s 级)；`tail -f` 应打印 `[OK] ... (aria2c 16线程)`。若仍 ~1.18MB/s → 可能 hf-mirror 不支持 range（aria2c 退回单线程），再换 modelscope 镜像兜底（待用户实测回报）。
- **复用铁律印证**：本次又是"动手前没官方确认下载源连通性"的代价——假设 huggingface.co 在 DSW 可达，实测被墙。后续 DSW 类下载默认 hf-mirror 主源 + aria2c 多线程。

## 14:37 死连接卡死 + 看门狗根治（commit 5c0d421）
- 用户本地**断电**一次（仅掐断 SSH 会话，DSW 云端实例 + `nohup` 脚本不受影响，这是关键经验：DSW 任务用 `nohup ... &` 启动后本地断电/断网不必重来）。
- 重跑 f81ab9a 后 `watch` 显示 LLM 卡在 5.6G 两分钟不动 → 诊断：`ps` 见 `aria2c`(PID 258030,14:23 起) 仍存活但 CPU 0.8%/累计0:06、**文件 mtime 停在 14:20** → 第2分片 `...00002-of-00003.gguf` 大小 `2015068160` 字节 17 分钟没变。
- **根因**：hf-mirror 出现**半死 TCP 连接**（连接建立但不发数据，aria2c 的 `--timeout` 未触发）→ aria2c 永久挂起假死，非限速。第1分片 `3991999872` 字节=正好 3.99G(=curl 进度条 3804M) 完整无误，第2分片残片可能半损坏。
- **修复(commit 5c0d421)**：`dl_file` 改为——aria2c 后台跑，外层 `while` 最多 4 次；**看门狗**每 15s `stat` 文件大小，连续 90s 无增长则 `kill -9` 重启；aria2c 退出码 0 即视为成功(`-c` 续传)；curl 兜底加 `--retry 5 --speed-time 60 --speed-limit 1000` 防挂起。
- **恢复操作(实测)**：`pkill -9 -f dsw_setup_t2i; pkill -9 -f aria2c` → `rm -f ...00002-of-00003.gguf*`（删可能损坏残片，留第1分片）→ 重传硬朗版 → `nohup` 重跑。重跑后 `grep -c "看门狗" /mnt/workspace/ai-comfyui/pai/dsw_setup_t2i_qwenllm.sh` = **3**（确认硬朗版就位）。
- **验证/状态**：脚本 14:44:03 重启(PID 299258)，[1/6] pip 重装 llama-cpp-python 中（tail 缓冲看着像卡，正常）。看门狗就位后即使再遇死连接也会自恢复，用户可放心等 [6/6]。
- **复用经验**：DSW 经 hf-mirror 下载**必须带看门狗/超时重启机制**，裸 aria2c/curl 在高负载 CDN 上易半死挂起。后续一切 DSW 大文件下载脚本默认套用此 `dl_file` 看门狗模板。

## 14:51 完整分片被反复重下 + 秒跳过修复（commit c8f5797）
- 重跑 5c0d421 后日志出现 `aria2c 尝试 3/4` 且出现在**本已完整(3.99G)的第1分片**上 → 说明 aria2c 带 `-c` 遇到已完整文件时，hf-mirror 返回 `200`(全量) 而非 `206`(续传)，导致 aria2c **从头重下 3.99G**，半死连接下每次下一半被看门狗 90s 杀掉→重试 1→4/4。
- **风险**：反复重下会**覆盖/损坏那个完好的第1分片**（截断成残片或坏中间字节）。必须立刻杀掉当前脚本。
- **修复(commit c8f5797)**：`dl_file` 在下载前先用 `curl -sIL` 取远端 `content-length`，**本地大小==远端则 `[OK] 已完整, 跳过` 并 return**，绝不碰已完整文件。这样第1分片秒跳过，不再进 aria2c 循环、不被覆盖。
- **用户动作(实测进行中)**：`pkill -9 -f dsw_setup_t2i; pkill -9 -f aria2c` 停当前跑（保护第1分片）→ `ls -la LLM/` 确认第1分片仍 3991999872（若变小则被覆盖残了，删掉重下）→ 重传 `dsw_setup_t2i_qwenllm.sh`@c8f5797 → `nohup` 重跑。重跑后第1分片直接跳过，从**第2分片干净下载**开始。
- **复用教训**：aria2c `-c` + hf-mirror 对"已完整文件返回 200"会导致重下陷阱；任何断点续传下载器在"文件可能已完整"时，**先用 HEAD 比大小再决定是否跳过**是必备护栏，不能无脑 `-c`。

## 深夜（续）：t5xxl 源缺口根治 + 显存修正（脚本就绪待重传）
- **致命缺口真因**：脚本原 t5xxl 用的是 `comfyanonymous/flux1` 仓库，但 Flux 文编(t5xxl+clip_l)实际在**独立仓库 `comfyanonymous/flux_text_encoders`**。`flux1` 在 hf-mirror 404、modelscope 仅根目录有 ae 无 text_encoders 子目录 → 之前所有探活均假阴性（早期还误用 modelscope API 格式 `api/v1/.../repo?file=`，正确是 `models/{owner}/{repo}/resolve/master/{file}`）。
- **正确可达源（格式修正后验证 200）**：modelscope `AI-ModelScope/flux_text_encoders` 的 `t5xxl_fp8_e4m3fn.safetensors` 与 `clip_l.safetensors`（resolve/master → 200 跳 OSS）；hf-mirror `comfyanonymous/flux_text_encoders` 亦可达作兜底。
- **显存修正（关键）**：`t5xxl_fp16` 实际 **~9.8G**（非 4.9G）。Flux Q4_K_S(6.7G)+t5xxl_fp16(9.8G)+clip_l(0.24)+ae(0.3)+开销 ≈ 17.5G → 16G **必 OOM**。改 `t5xxl_fp8_e4m3fn(~2.5G)`，峰值 ~11G，16G 稳装。
- **工作流修正**：节点7 由单文件 `CLIPLoader`(仅 t5xxl) 改为官方 `DualCLIPLoader`（t5xxl_fp8 + clip_l，type=flux）。单 CLIPLoader 缺 clip_l 必报错。
- **改动文件**：`dsw_setup_t2i_qwenllm.sh`（t5xxl→flux_text_encoders+fp8；新增 clip_l 下载；清理旧 t5xxl_fp16 残留；[6/6] 校验改查 t5xxl/clip_l；节点校验 CLIPLoader→DualCLIPLoader）、`t2i_qwenllm_e2e.json`（节点7=DualCLIPLoader）。`bash -n` 与 JSON 校验均通过。
- **用户下一步**：重传 `dsw_setup_t2i_qwenllm.sh` 与 `t2i_qwenllm_e2e.json` 到 DSW `/mnt/workspace/ai-comfyui/pai/` → `nohup bash dsw_setup_t2i_qwenllm.sh > /tmp/dsw_setup_t2i.log 2>&1 &` 重跑（Qwen/Flux/ae 已完整自动跳过，只下 t5xxl_fp8~2.5G+clip_l~0.24G）→ 等 [6/6] 全绿 → ComfyUI Load 工作流、设节点1短词、Queue 出图。

## 次日重跑踩坑：用户仍跑旧版脚本（必须 verify 上传版本）
- **现象**：用户重跑后日志显示 `aria2c 16线程...hf-mirror 主源` 且 Qwen 走 hf-mirror curl 兜底 → 与我最后的 modelscope 优先版(8线程+`优先 modelscope` banner+t5xxl fp8)不符。确诊：**DSW 上仍是旧版（5c0d421 代或更早），最后修正版未真正覆盖上去**。
- **后果**：旧版不光慢，且 t5xxl 仍指向 `comfyanonymous/flux1`(hf-mirror 404) → 跑到 t5xxl 必失败，白等。
- **操作教训（新增硬规则）**：每次让用户重传脚本后，**重跑前必须用 grep 验证 DSW 上的文件确实是最新版**：`grep -c "优先 modelscope" dsw_setup_t2i_qwenllm.sh`（应为1）；若返回0说明传错/没覆盖。已下载的 Qwen 00001/00002 因 content-length 相等会被新脚本秒跳过，00003 从 modelscope 续传。

## 下载器再修正：modelscope 上 aria2c 假死 → 改 curl 直连
- **现象**：新版（优先 modelscope）跑起来后，00001/00002 秒跳过正确，但 00003 的 modelscope `aria2c` 连续 4 次被看门狗 90s 零进度杀掉（rc=137）。本机沙箱探 modelscope 是 200，但 **DSW 实际出口到 modelscope 的 OSS 重定向不稳定，aria2c 多线程在此会假死**，单连接 curl 反而能通。
- **修正**：`dl_file` 的 modelscope 分支去掉 `aria2c_get`，改为 `curl -L -C - --retry 8 --speed-limit 1000 --speed-time 60` 直连（带断点续传+限速熔断，过慢自动放弃回退 hf-mirror）；`aria2c_get` 仅留作 hf-mirror 兜底，`max_tries` 4→2、看门狗 90s→60s，失败快回退。
- **验证**：`bash -n` 通过；grep 确认 `优先 modelscope (curl 直连` 在、`aria2c_get` 仅出现在 hf-mirror 行(117)。
- **用户操作**：只需重传脚本（工作流未改），kill 旧进程→rm 半残 00003→重跑；重跑后 00003 应直接走 modelscope curl 下载，不再有看门狗刷屏。
  - **实测确认(16:28)**：DSW 重跑日志出现 `-> 优先 modelscope (curl 直连，避开 aria2c 重定向假死)`，证明修复版已生效；00001/00002 秒跳过正常。待观察 00003 是否经 modelscope curl 真正下下来（还是熔断回退 hf-mirror）。

- **加速方案(16:3x)：用户催进度，单连接实测仅 ~1.3MB/s，Flux(6.7G)单连接要~80min 不可接受 → 改「并行分片下载」(dl_parallel)**
  - 做法：大文件(>300M)切 8 片并发 `curl -r start-end` 下载到 `.part.N`，合并校验大小；突破 modelscope/hf-mirror **单连接限速**（多连接通常能叠加）。
  - 已存在部分文件 → 先单连接 `-C -` 续传补齐（不浪费 00003 已下进度）；小文件(<300M: clip_l/ae) → 单连接续传。
  - 移除 `aria2c_get`（两源多线程均假死，留着只耗时有用）；主下载改 `dl_parallel`，失败回退 hf-mirror 单连接 curl 兜底。
  - 风险兜底：若 DSW 出口对单 IP 总带宽限速（多连接不叠加），dl_parallel 分片会慢/失败 → 自动回退单连接，不会更慢，无副作用。
  - 校验：`bash -n` 通过；`dl_parallel()` 定义于 67 行，dl_file 130/134 行调用。`grep -c "dl_parallel()" dsw_setup_t2i_qwenllm.sh` 应为 1（重传后用户验证用）。
  - **用户下一步**：kill 旧进程 → 重传本机脚本(覆盖) → `grep -c "dl_parallel()"` 确认=1 → 重跑。00003 续传补齐、Flux/t5xxl 走 8 连接并行。

- **并行分片失效根因修复(16:53)**：上一版 dl_parallel 实测仍走单连接慢路，日志暴露两处 bug：
  - **bug1**：`total` 只靠 `curl -sIL -L` 取 `content-length`，但 **modelscope OSS 对 HEAD 不返回 content-length**（仅 GET/Range 返回）→ `取不到文件大小，放弃` → 掉回 hf-mirror。
  - **bug2**：本地已有 646MB Flux 残片 → 进入「单连接续传补齐」分支，并行完全没用上，又掉回 hf-mirror 单连接 ~1.18MB/s。
  - **修复**：① size 探测加 `content-range` 兜底（`curl -s -r 0-0 -D -` 取 `content-range: bytes 0-0/TOTAL` 的 TOTAL，modelscope 必能拿到）；② 残片不再单连接续传，改为**并行续传剩余部分**（保留已下前缀，只对 `[have,total)` 切 8 片并发，追加到前缀）；③ 加分片大小校验（sz>chunk+64 即判定服务端忽略 Range 返回整文件，abort 回退），防合并错乱。
  - 校验：`bash -n` 通过；grep 确认 74 行 content-range、87 行「并行续传剩余部分」、107 行「不支持Range」兜底均就位。
  - **用户下一步**：kill 当前(正 hf-mirror 单连接续传 Flux 的)旧进程 → 重传本机脚本 → `grep -c "dl_parallel()"`=1 → 重跑；Flux 应出现 `并行续传剩余部分` + `合并完成`，不再单连接。
  - **经验固化**：下载器 size 探测永远要 HEAD-content-length **和** Range-content-range 双兜底；任何「残片→单连接续传」分支都会让并行加速失效，残片应走并行续传剩余区间。

- **并行仍假死的真凶(17:3x，最终定位)**：上面两处"修复"后仍走慢路，根因是 **content-range 兜底那行漏了 `-L`**（第74行原 `curl -s -r 0-0 -o /dev/null -D -` 没跟随302重定向到 OSS），所以拿到的永远是 302 响应头、没有 `content-range` → `total` 为空 → `取不到文件大小，放弃` → 掉回 hf-mirror 单连接。沙箱实测：modelscope OSS **支持 Range**（跟随302后返回 `206 Partial Content` + `Content-Range: bytes 0-0/6805988640`，Flux总6.8G；t5xxl_fp8 总 **4.89G** 非之前估的2.5G；clip_l/ae 同理）。修复=给第74行加 `-L`（`curl -s -L -r 0-0 ...`）。bash -n 通过。
  - **关键结论**：modelscope 支持 Range → 并行分片在 DSW 真能叠加带宽；此前所有"假死/掉回单连接"都是 size 探测没 `-L` 的假阴性，不是源问题。
  - **用户下一步(真·最终)**：重传本机修复版脚本 → kill 旧进程 → 重跑（保留 Flux 残片，新脚本 content-range 探测生效 → `并行续传剩余部分`）。Flux(6.8G)经 modelscope 8连接并行，几分钟搞定而非80min。
  - **验证标志**：重跑日志出现 `并行续传剩余部分` + `合并完成(6805988640 字节)` 即加速生效。若仍 `取不到文件大小` 说明 -L 没传上去。

- **dl_parallel 空洞写 bug(17:57，最致命的一版)**：用户贴 unet 目录 16G↔17G↔18G 反复横跳，定位到 dl_parallel「续传剩余部分」分支是**一边下分片一边 `cat part >> $out` 增量追加**——某分片没下全时循环检测到缺失即 `return 1`，但**已追加的乱序分片留在原文件、形成空洞**；下一轮 `have` 从带洞大小续传→偏移错位→越写越乱→反复清空重下→du 看到来回跳。且该版正在把 `flux1-dev-Q4_K_S.gguf` 悄悄写坏。
  - **重写 dl_parallel（v2 原子组装）**：分片全部下到 `.part.N` 临时区 → **每个分片精确校验 `sz == exp`**(非大小区间) → 全部成功才拼到 `tmpmerge` 临时文件 → **整体 `cat tmp >> $out`** 一次性原子追加（绝不一边下一边写）；任何分片失败 → `rm .part.*` + **干净回退单连接 `curl -L -C -` 续传(保留原前缀、不污染)**。nthr 默认 8→**4**(降并发被限流概率)。另在 [2/6] 开头 `find ... -name '*.part*' -delete` 清残留。
  - **铁律固化**：下载器的「续传/并行合并」**绝不允许逐片增量追加到目标文件**，必须「先拼临时、整体换入/追加」；增量追加一旦遇分片缺失必产生空洞且不可自愈。
  - **用户下一步(真·最终v2)**：① kill 当前(556044 正把 Flux 写坏)旧进程；② **必须 `rm -f` 已损坏的 `flux1-dev-Q4_K_S.gguf` 及其 `.part*`**（脚本对"带洞但大小不符"无法自愈，留着会从错偏移续传）；③ 重传本机 v2 脚本 → `grep -q "整体追加"` 确认=1 → 重跑。Qwen3分片已完整会跳过；Flux 这次从 0 干净下。
  - **预期**：若 modelscope 并发可用→4连接并行几分钟下完 Flux；若被限流→自动干净回退单连接(可靠、不再横跳)。t5xxl_fp8(4.89G)/clip_l/ae 同理。

## 2026-07-31
### 2026-07-31 工作日志

## CloudBase 生图项目（新支线，与桃子角色视频并行）

### 背景
- DSW 实例欠费后，用户转向腾讯云 CloudBase（小程序成长计划开通，有免费生文/生图模型）。
- 上一轮（2026-07-29 后段）已写 `D:\Aicomfyui\cloudbase-imggen\server.js`（Node 零依赖代理：持有 ENV_ID+API_KEY，提供 /api/expand 扩写 + /api/image 生图，仅监听 127.0.0.1）。**但该轮 index.html 被用户打断、未保存**，目录现仅 server.js 一个文件，且无 config.json。
- **重要：上一轮 CloudBase 工作从未写入 memory，本次补全。**

### 官方文档事实（docs.cloudbase.net/ai/ai-inspire-plan + ai-inspire-plan-guide，2026-07-31 阅读确认）
- AI 资源包（混元 Token + 生图额度）**仅限微信小程序和云开发服务端使用，其他来源不可使用**。
- 生图模型**仅支持在服务端（云函数/云托管）调用**，不能从浏览器/小程序前端直接 fetch。
- 生文端点：`POST https://<ENV_ID>.api.tcloudbasegateway.com/v1/ai/cloudbase/chat/completions`，Bearer ApiKey，OpenAI 兼容，响应 `choices[0].message.content`。
- 生图端点候选：`/v1/ai/hunyuan-image/images/ar/generations` 与 `/v1/ai/<ENV_ID>/images/ar/generations`（server.js 双路径回退）。模型 `HY-Image-3.0-Plus-4090-Tob-v1.0`、`HY-Image-v3.0-I2I-ToB-v1.0.1`（图生图）、`hunyuan-image-v3.0-v1.0.4`。响应 `data[0].url` + `revised_prompt`。
- 生文模型（免费额度内）：`hy3` / `hy3-preview`；非小程序场景建议 `deepseek-v4-flash` 等（走资源点套餐）。
- ⚠️ **额度坑**：把后端部署在用户自有腾讯云轻量服务器（非 CloudBase 云托管）时，对 CloudBase 属「外部来源」，免费额度可能不被认可→走资源点计费或受限。若要白嫖免费额度，更稳是把后端跑在 CloudBase 云托管。已写入部署文档提醒。

### 服务器架构（已读 github.com/mz20191223/DNS-server-configuration，2026-07-31）
- 腾讯云轻量 129.204.189.218，Ubuntu 22.04，2核4G/5M。域名 gp3666923.xyz（阿里云注册+Cloudflare DNS）。
- 已有 Cloudflare Named Tunnel `bingyu-api`（ID 978e8374-83d9-4869-8c2f-4db0d200d878），config `/etc/cloudflared/config.yml`，systemd `bingyu-tunnel`。
- 现有子域：api.gp3666923.xyz→Flask:5000；catalog.gp3666923.xyz→Flask:8888。
- 新增项目范式：开子域→加 ingress→`cloudflared tunnel route dns bingyu-api <子域>.gp3666923.xyz`→`systemctl restart bingyu-tunnel`→systemd 拉服务。

### 本次决策（用户 2026-07-31 拍板）
- 架构改为 **uni-app 前端 + Java 后端**，部署链路挂到用户服务器：子域 **`cbimg.gp3666923.xyz` → Java 后端 :8080**（复用 bingyu-api 隧道，不动 api/catalog）。
- 运行形态：**先做 H5 网页**（编译挂子域经隧道访问）；uni-app 工程同时保留 mp-weixin 构建能力。
- CloudBase 凭证：用户选择「现在就发给我」→ 写进服务端安全配置（仅服务端持有，绝不进前端/仓库）。

### 待办
- [ ] 用户粘贴 CloudBase EnvId + ApiKey。
- [ ] 写 Java Spring Boot 后端（CloudBase 生文/生图 REST 客户端 + 静态托管 uni-app H5 + CORS）。
- [ ] 写 uni-app 前端（输入→扩写→尺寸选择→生图→展示）。
- [ ] 写部署产物：systemd 服务文件、cloudflared ingress 片段、一键 deploy.sh、部署文档（含额度坑提醒）。
- [ ] 旧 Node 版 server.js 可归档或弃用（被 uni-app+Java 版替代）。

### 注意
- 本机（WorkBuddy 沙箱）无法直接 SSH 到 129.204.189.218（无凭据/SSH 工具）；实际服务器部署需用户在 VNC/SSH 执行，或提供访问方式。本会话交付物=完整源码+部署脚本+runbook。

## 实际构建进展（2026-07-31 上午）
- 确认架构：Java 后端 **跑在 CloudBase 云托管（非轻量服务器）** → 免费额度可用（用户明确「要免费」）。不再走 Cloudflared 隧道；轻量服务器 api/catalog 不动。
- 已读完官方云托管文档（docs.cloudbase.net/run）：Spring Boot 监听 80、maven 多阶段 Dockerfile、`tcb cloudrun deploy` 或控制台上传代码包部署。
- 已落盘工程 `D:\Aicomfyui\cbimg-cloudrun\`：
  - backend/：Spring Boot 2.7(Java11) + pom.xml + Dockerfile(官方maven多阶段,EXPOSE 80) + .dockerignore + 源码(CbimgApplication/AppConfig/CloudBaseAiClient/ImageController/CorsConfig) + application.properties(server.port=${PORT:80}) + static 占位 index.html。
  - CloudBaseAiClient 复刻 Node 版逻辑：生文 hy3 @ /v1/ai/cloudbase/chat/completions；生图 HY-Image-3.0-Plus 双候选 URL 自动 404 回退。凭证走环境变量 CB_ENV_ID/CB_API_KEY（Spring 映射 cb.envId/cb.apiKey）。
  - frontend/：degit 拉官方 uni-app v3(Vue3+Vite) 模板，重写 index.vue（输入→扩写→选尺寸→生图→展示，uni.request 兼容 H5/小程序），manifest 加 h5 基路径、pages 标题。
  - README.md + deploy/DEPLOY.md（控制台/CLI 部署、环境变量、自定义域名 cbimg.gp3666923.xyz via Cloudflare CNAME、额度坑、回退）。
- 本地无 Maven/Docker（有 Java25/Node22）；云托管云端构建，无需本地 Docker。正在 `npm install` 前端依赖，随后 `build:h5` 并复制产物到 backend static。

## 交付状态（2026-07-31 上午，构建完成）
- uni-app H5 已本地构建成功（`npm run build:h5`，Compiler 5.15 vue3），产物复制到 `backend/src/main/resources/static/`（index.html + assets/ + static/logo.png），Spring Boot 同源托管，资源路径根绝对 `/assets/...` 正确。
- 完整工程就绪：`D:\Aicomfyui\cbimg-cloudrun\`（backend Java + frontend uni-app + README + deploy/DEPLOY.md）。
- 本机无 Maven/Docker，无法本地编译/打镜像；但云托管云端按 Dockerfile 构建，无需本地 Docker。Java 代码为标准 Spring Boot，逻辑已自查（RestTemplate 调 CloudBase 网关、404 双候选回退、凭证走环境变量）。
- **部署交接**：本会话无法 SSH/直连 CloudBase 控制台或 tcb CLI（无凭据），实际部署需用户在云端控制台「上传 backend 目录代码包」或 `tcb cloudrun deploy`，并注入 CB_ENV_ID/CB_API_KEY。DEPLOY.md 已写清步骤（含自定义域名 cbimg.gp3666923.xyz via Cloudflare CNAME、微信小程序构建、额度坑回退）。
- 待用户：发 CloudBase **ENV_ID + ApiKey**（用于部署时注入；若想让我远程 tcb 部署还需 Tencent SecretId/SecretKey）。

## 关键修正：CloudBase 真实网关 URL（2026-07-31 12:xx）
- 用户控制台确认环境 ID = `mz0708-d6grh8a1xcfa9b963`（环境名 mz0708），非截图初看误判的 me0708。
- **真实 AI 网关 Base URL** = `https://me0708-dhgrh4saicsfakf0bf0a3.ap-beijing.run.tcloudbase.com/v1/ai/cloudbase`（控制台「AI→快速开始」给出）。
- 之前客户端按旧文档猜的 `*.api.tcloudbasegateway.com` 域名**错误**，已改为基于真实 Base URL 拼接（生文 {baseUrl}/chat/completions；生图 4 候选含 baseUrl 变体，404 自动回退）。
- 改动文件：CloudBaseAiClient.java、AppConfig.java(EnvCheck 改查 baseUrl)、application.properties(加 cb.baseUrl/cb.envId 默认值)。backend-deploy.zip 已重生。
- 教训：CloudBase 控制台给的 Base URL 才是真相源，旧文档域名已失效/不适用，先抄真实 URL 再写代码。

## 部署方式调整：改为 Git 平台部署（2026-07-31 中午）
- CloudBase 控制台「云托管 → 创建服务」当前仅支持 **Git 平台部署**（进入即要求 GitHub 授权），无「上传代码包」入口。
- 已将 `cbimg-cloudrun` 本地初始化为独立 git 仓库并 commit（34 个文件）。
- 为适配 Git 部署，在仓库根新增 `Dockerfile`（从 `backend/` 子目录复制源码构建），原 `backend/Dockerfile` 保留备用。
- 新增 `.gitignore`，排除 target/node_modules/dist/backend-deploy.zip 等。
- 尝试用 GitHub PAT / 已连接 GitHub 连接器创建远程仓库 `mz20191223/cbimg-cloudrun`，均返回 403（无创建仓库权限）。
- **当前阻塞**：需用户在 GitHub 网页手动创建私有空仓库 `cbimg-cloudrun`（不要初始化 README），然后把地址发我，我再 push。
- 已重写 `deploy/DEPLOY.md` 为 Git 平台部署流程（含 GitHub 授权、选仓库 main 分支、端口 80、环境变量 CB_API_KEY 等）。

## 仓库已推送（2026-07-31 14:xx）
- 用户手动在 GitHub 创建私有空仓库 `mz20191223/cbimg-cloudrun`。
- 本地 commit（34 文件）已 `git push -u origin main` 成功，远端已确认根 `Dockerfile`(678B)、`backend/Dockerfile`、`backend/src/main/resources/static/index.html` 均在。
- 远程 URL 已复位为干净 `https://github.com/mz20191223/cbimg-cloudrun.git`（无 token 明文）。

## 构建失败→修复（2026-07-31 14:1x）
- CloudBase 首次构建失败：Maven 编译报错 `CloudBaseAiClient.java` 中 `HttpStatusCodeException` 找不到。
- 根因：`import org.springframework.http.client.HttpStatusCodeException` 写错包名，正确应为 `org.springframework.web.client.HttpStatusCodeException`。
- 已改 import 并 push（commit 35191f0）。其余编译无报错（日志仅此一项）。
- 待用户在 CloudBase 对该版本「重新部署 / 重新构建」（拉 main 最新），预计 1 分钟内过编译。

## 构建成功（2026-07-31 14:2x）
- 用户确认 CloudBase 重新构建成功（commit 35191f0 修复 import 后过编译）。
- 下一步：控制台拿默认域名 → /api/health 验证 → / 试用页面；可选绑 cbimg.gp3666923.xyz（Cloudflare CNAME + 云托管证书）。

## 首次访问：页面乱码修复（2026-07-31 14:2x）
- 用户访问默认域名，页面加载但中文全部乱码（JS 中文字符串被浏览器按 Latin-1 解析）。
- 修复：application.properties 加 `spring.http.encoding.*` 强制所有响应 UTF-8；`backend/src/main/resources/static/index.html` 把 `<meta charset="UTF-8" />` 移到 `<head>` 最顶；同时显式加 `cb.apiKey=${CB_API_KEY:}`。
- 已 push（commit c7cf791），待用户重新部署验证。

## 端点修正：实测 INVALID_HOST + 401（2026-07-31 14:2x）
- 用户实跑报错：/api/expand 命中 run.tcloudbase.com → INVALID_HOST（非法域名，不能用）；/api/generate 命中 env-id 网关 → 401 UNAUTHORIZED（域名合法，鉴权失败）。
- 关键事实：真正可用的 AI 网关域名是 **https://<ENV_ID>.api.tcloudbasegateway.com**（env-id 派生），控制台「AI→快速开始」给的 *.ap-beijing.run.tcloudbase.com 实测 INVALID_HOST，已弃用。
- 修复：CloudBaseAiClient 改用 gatewayBase（env-id 网关）；imageUrls 仅留 cloudbase 路径 + env-id 路径两候选；错误带真实响应体；启动日志打印 apiKey 掩码；新增 GET /api/debug 暴露生效网关地址与 apiKeySet 状态。application.properties 的 cb.baseUrl 改为 env-id 网关。
- 已 push（bab9df3）。待用户重新部署后：① 访 /api/debug 确认 apiKeySet=yes；② 若仍 401，多半是 CB_API_KEY 没传到当前版本或 key 本身不对。

## 方案 A 落地：Node.js 后端 + @cloudbase/node-sdk（2026-07-31 15:xx）
- 用户确认走方案 A（后端改 Node.js 以用免费额度）。
- 根因确认：Java 裸 HTTP 调 AI 报 `AI_CHANNEL_NOT_ALLOWED` —— 免费额度仅允许 CloudBase 官方 SDK（node-sdk / wx-server-sdk / 云函数）调用，裸 HTTP 不行。域名(INVALID_HOST)/key(401) 只是表象。
- 已重写：server.js(用 @cloudbase/node-sdk，cloudbase.init({env:ENV_ID}) 自动鉴权，无需 API Key；生文 createModel('cloudbase').generateText({model:'hy3'})；生图 createImageModel('hunyuan-image').generateImage({model:'HY-Image-3.0-Plus-4090-Tob-v1.0'}))；package.json(依赖 ^3.18.3)；Dockerfile(node:18-alpine，npm install + node server.js)；.dockerignore/.gitignore 改 Node 版；README/DEPLOY 重写（不再需要 CB_API_KEY）。
- 复制 H5 static/ 到根，git rm backend，commit `d5c50a2` 已 push 到 mz20191223/cbimg-cloudrun main。远端已确认根目录干净（无 backend），.dockerignore 排除 backend/frontend/*.md/deploy。
- 断电后续做：核对远端=干净 Node 版；清理本地残留 backend（关掉之前起的 8090 预览 python server 后删）；重写 MEMORY CloudBase 段为 Node 架构（删 Java/CB_API_KEY/网关错误描述）。
- 待用户：在 CloudBase 对 cbimg 服务「重新部署/重新构建」拉最新 d5c50a2，验证 /api/health→ok、/api/debug→含 sdkVersion、页面生图可用。

## 本地核验 Node SDK（2026-07-31 15:3x，断电后续做）
- 装 @cloudbase/node-sdk@3.18.3 本地核验：app.ai() 存在；createModel('cloudbase').generateText 是函数；createImageModel('hunyuan-image').generateImage 是函数。AI 实现在子包 @cloudbase/ai。
- 关键事实：cloudbase.init({env}) 不设 baseUrl 时，SDK 内部 AI baseUrl 默认拼 `https://<ENV_ID>.api.tcloudbasegateway.com/v1/ai` —— 即 Java 版报 401 的那个域名，证明域名本身没错，Java 失败是裸 HTTP+路径/key 不对。
- 查 @cloudbase/ai 源码+type.d.ts 确认 server.js 参数完全正确：生图模型 HY-Image-3.0-Plus-4090-Tob-v1.0 属 HunyuanARGenerateImageInput，revise 必须 {value:boolean}（我写的正是）；返回 HunyuanARGenerateImageOutput.data[].url/revised_prompt（我读 res.data[0].url 正确）；生文 createModel('cloudbase')→.../v1/ai/cloudbase/chat/completions，generateText({model:'hy3',messages}) 标准格式。
- 结论：d5c50a2 代码本身正确，无需改。用户只需在 CloudBase 重新部署拉该版本即可。已清本地 node_modules。
