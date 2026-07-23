# 桃子 AI 视频项目 · 云端 ComfyUI 衔接手册

> 最后更新：2026-07-23 晚（HAI 已关机，用户离开；本机继续预研）
> 本文件是「另一台电脑 / 重开 HAI 后」无缝续接的唯一权威手册。

---

## 0. 一句话现状
- **HAI 实例已关机**（约 18:41 起不可达）。重开后会换 IP，需重新发我 `IP + SSH 密码`。
- **已推 GitHub**：`ai-comfyui` 仓库 `main` 分支 = 本手册 + `cloud/` 全套脚本/镜像/提示词（孤儿分支，干净快照）。
- **当前最大卡点（今晚新发现，见第 2 节）**：Qwen-Image-Edit 出分镜图所需的**节点包在本实例上装不上**，需要换获取路径。

---

## 1. 目标与验收
- 桃子（Pixar 风小兽）短视频：关键文字 + 角色参考图 → 自动出「角色一致」短视频。
- 架构（用户 2026-07-23 拍板）：**Qwen-Image-Edit-2511 出分镜图（图像前端）+ LTX 2.3 出视频（视频引擎）**。
- 验收 = 达到本地旧片效果 + 修复两个已知问题：
  1. s01→s02 草堆被推飞像切场景（camera/构图不连续）
  2. 角色横移跑动而非原地（运镜未进视频提示词）

---

## 2. ?? 今晚核实的关键修正（之前手册写的，部分已过时）

### 2.1 实例侧出网白名单（实测）
| 可达 | 不可达 |
|---|---|
| huggingface.co（含官方权重） | github.com（git clone 被重置） |
| modelscope.cn | raw.githubusercontent.com |
| baidu | 一切 GitHub 镜像（ghproxy/kgithub/gitproxy 全死） |

→ **实例上装任何 ComfyUI 节点包，不能走 GitHub，必须走 HF 或 ModelScope。**

### 2.2 Qwen-Image-Edit 节点包 = 真正的卡点
- 实例预装 ComfyUI 版本**偏旧**（17:09 拉取的 object_info 里**没有任何 qwen 节点**）。Qwen-Image 是 2025 年才进 ComfyUI 原生支持的，本实例没有。
- `Comfy-Org/Qwen-Image_ComfyUI` 和 `Comfy-Org/Qwen-Image-Edit_ComfyUI` 在 HF 上**只有权重（.safetensors），没有任何节点代码**——它俩不是节点包。
- 候选节点包核查结果：
  - `QwenLM/ComfyUI_Qwen_Image_Edit` → **不存在**
  - `kijai/ComfyUI-Qwen-Image` → **不存在**
  - `HM-RunningHub/ComfyUI_RH_Qwen-Image` → 存在，但**基于 diffusers**（requirements 依赖 `git+https://github.com/huggingface/diffusers`），**不走 ComfyUI 原生 MODEL/CLIP，与我们的 GGUF 方案不兼容**，装了也喂不进 GGUF unet。
  - ComfyUI 官方 `comfy_extras/nodes_qwenimage.py` → **404（当前 master 也没有这个路径）**，原生节点文件位置未定位。
- **结论**：GGUF 兼容的 Qwen-Image 节点包，没有现成可靠仓库可一键装。需要重开 HAI 后在实例上从 **ModelScope / HF** 现找现装（见第 5 节步骤 A）。

### 2.3 本机（这台电脑）出网也受限
- 可达：github.com（HTTP/API）、GitHub API（search/contents/base64 取文件）。
- 不可达：git clone github（连接被重置）、raw.githubusercontent.com（000）、huggingface.co（000）。
- → 本机**无法**把节点包源码抓下来 SFTP 给实例（git clone 被墙、HF 不通）。节点包只能**在实例侧从 HF/ModelScope 获取**。

### 2.4 已确认可用的部分（不用重做）
- ? **ComfyUI-GGUF** 已装实例（GGUF unet / text_encoder 加载器都在）。
- ? **LTXVideo 插件**已解压安装（出视频用）。
- ? 桃子锚图 `peach_role_v6.png` 已传实例 `input/`。
- ? Qwen-Edit **权重下载已在进行**（实例后台 wget -c，约下完 4.2G/总 ~13G，关机不丢）。

---

## 3. 实例文件落点（重开后仍在该系统盘）
- `custom_nodes/ComfyUI-LTXVideo/` ?
- `custom_nodes/ComfyUI-GGUF/` ?
- `input/peach_role_v6.png` ?
- `models/unet/qwen-image-edit-2511-Q4_K_M.gguf` ? 下载中（续传）
- `models/text_encoders/Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf` ?
- `models/text_encoders/mmproj-BF16.gguf` ?
- `models/vae/qwen_image_vae.safetensors` ?（已下完 253M）

---

## 4. cloud/ 目录（已推 GitHub，另一台电脑 clone 即得）
| 文件 | 作用 |
|---|---|
| `ssh_run.py` | paramiko SSH 执行（密码走 `SSH_PASS` 环境变量，不落盘） |
| `sftp_upload.py` | paramiko SFTP 上传 |
| `cloud_pipeline.py` | 通用云端客户端（上传→提交→轮询→下载） |
| `check_cloud_nodes.py` | 节点核对（--host） |
| `dl_qwen_weights.sh` | Qwen-Edit 权重续传脚本（wget -c） |
| `CLOUD_PIPELINE.md` | 完整执行手册 |
| `ltx_p1_prompts.json` | p1 四段视频提示词（强制固定机位/原地） |
| `peach_refs_prompts.json` | 多角度参考图提示词（B 步） |
| `object_info.json` | 17:09 实例节点快照（已无 qwen 节点，见 2.2） |
| `_gguf_mirror.tar.gz` | ComfyUI-GGUF 镜像（实例已装，备用） |
| `_ltx_mirror.tar.gz` | LTXVideo 镜像（实例已装，备用） |

---

## 5. 重开 HAI 后的执行步骤（按顺序）

### A. 拿到节点包（解决 2.2 卡点）—— 本步最不确定，优先做
1. 重开实例，SSH 进去。
2. **先在实例上找 GGUF 兼容的 Qwen-Image 节点包**（实例能连 ModelScope/HF）：
   ```bash
   # 试 ModelScope（实例侧可达）
   git clone https://www.modelscope.cn/models/<owner>/ComfyUI-Qwen-Image.git custom_nodes/ComfyUI-Qwen-Image
   # 或 HF 上搜 Qwen-Image ComfyUI 节点（实例侧可达 huggingface.co）
   git clone https://huggingface.co/<org>/ComfyUI-Qwen-Image custom_nodes/ComfyUI-Qwen-Image
   ```
   - 判断标准：节点文件里出现 `NODE_CLASS_MAPPINGS` 且加载的是 ComfyUI `MODEL` 对象（能接 `UnetLoaderGGUF` 的输出），**不是** diffusers pipeline。
   - 若找不到 GGUF 兼容包 → 退路：下载官方 **fp8** 权重（`Comfy-Org/Qwen-Image-Edit_ComfyUI` 的 `qwen_image_edit_2509_fp8_*.safetensors` 等，实例能直连 HF）并**更新 ComfyUI 到带原生 Qwen 节点的版本**（同样需从 HF 获取 ComfyUI 源码），代价是 T4 16G 显存更吃紧。
3. 装依赖（实例侧能 pip / 从 HF 镜像装的都行，避开 GitHub）。

### B. 续传权重（若关机期间没下完）
```bash
setsid bash /root/dl_qwen.sh > /root/dl.log 2>&1 &
# dl_qwen.sh 用 wget -c，已下的 4.2G 不丢
```

### C. 重启 ComfyUI 并验证节点
- 重启命令见 `CLOUD_PIPELINE.md` 第 9 节（实例内 kill + main.py --listen --port=6889）。
- 拉 `object_info`，确认出现 Qwen-Image 相关节点 + GGUF 节点。

### D. 出 B 多角度参考图（评审闸门）
- 用 `peach_role_v6.png` 作参考，按 `peach_refs_prompts.json` 出 正面/侧/背/表情 4 张，发用户预览，确认一致性。

### E. 出 C p1 分镜图（评审闸门，从头重出）
- 按 `ltx_p1_prompts.json` / `peach_refs_prompts.json` 重出 s01–s05，逐张发用户评审（用户强调「从头开始才能发现问题」）。

### F. LTX 出视频 + 拼接验收
- 吃分镜图 + 提示词出视频，修复第 1 节两个已知问题，ffmpeg 拼接。

---

## 6. 另一台电脑衔接步骤
1. `git clone https://github.com/mz20191223/ai-comfyui.git`
2. 打开本 `STATE.md` 照第 5 节走。
3. 开 HAI → 发 `新 IP + SSH 密码` 给我。
4. 我执行 A→F。

---

## 7. 待用户决策的开放问题
- **图像生成器是否坚持 Qwen-Image-Edit？** 若节点包实在装不上，可退到「官方 fp8 权重 + 更新 ComfyUI」或换一个实例原生可跑的图像模型（风格会偏移，需你拍板）。
- T4 16G 显存对 Qwen-Image（无论 GGUF Q4 还是 fp8）都偏紧，实测 OOM 时需降分辨率/启 offload。
