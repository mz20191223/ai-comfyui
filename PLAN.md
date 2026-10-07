# 皮克斯角色视频 · 最终方案（Agnes 前端 + ComfyUI 引擎 + MV-Adapter 出 9 宫格）

> 目标：你给「关键内容 + 角色关键词」→ 自动出角色一致的短视频。
> 项目根目录：**D:\Aicomfyui**（已搬离 C 盘）。
> 硬件：HAI T4（15.5G），开机才计费。本协议确保「先探测、后生成、先测试再批量」，绝不盲目烧钱。
>
> ⚠️ 2026-07-22 重大修正：我们实测证明 **IPAdapter(plus-face) 锁不住非人类角色**（weight 0.8/0.95 都失败，9 张形象各异）。
> 因此「9 宫格」改由 **MV-Adapter（i2mv_sdxl）** 生成一致多视角，IPAdapter 只作视频段的弱辅助锁。

## 〇、HAI 真实预装状态（来自官方 SD_ComfyUI_ToolBox.ipynb，已核实）

| 类别 | 预装内容 | 说明 |
|------|----------|------|
| 基座模型 | 仅 `v1-5-pruned-emaonly.safetensors`（SD1.5） | **没有 SDXL / Pixar LoRA**，需下载 |
| 插件 | ComfyUI-Manager / 翻译 / **ComfyUI-AnimateDiff-Evolved** ✅ / comfyui_controlnet_aux / workspace-manager | **缺 MV-Adapter、缺 IPAdapter_plus、缺 VideoHelperSuite** |
| 动画模块 | AnimateDiff 节点在，但 motion 模型文件**没下载**（需 2.2G） | — |

> ⚠️ 之前记忆里"HAI 现成 IPAdapter 模型"是错的——默认预装**没有**该插件/模型。一切以开机后 `comfy_discover.py` 实测为准。

**本机已下好、开机直接传的文件（D:\Aicomfyui）**：
- `models/checkpoints/sd_xl_base_1.0.safetensors`（6.5G，Tier1 下载中）
- `models/loras/Canopus-Pixar-Art.safetensors`（137M，皮克斯 LoRA）
- `models/vae/sdxl_vae_fp16fix.safetensors`（335M，修黑图）
- `models/animatediff/mm_sdxl_v10_beta.ckpt`（2.2G，SDXL 动画模块）
- `models/mvadapter/mvadapter_i2mv_sdxl.safetensors`（MV-Adapter 权重，9 宫格核心）
- `custom_nodes/ComfyUI-VideoHelperSuite/`（视频输出，git clone 中）
- `custom_nodes/ComfyUI-MVAdapter/`（9 宫格插件，已 clone ✅）

**开机后需在 HAI 做的（只耗带宽/时间，不耗 GPU）**：
```bash
# 1) 上传上面 7 个文件到 HAI 对应目录（JupyterLab 拖拽 / scp）
#    checkpoints/ loras/ vae/ animatediff/ mvadapter/ custom_nodes/ 一一对应
# 2) git clone 两个视频相关插件（若本机 clone 没传过去）
cd /root/ComfyUI/custom_nodes
git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite   # 视频输出
git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus           # 视频段弱锁（非必需，先备）
# 3) 重启 ComfyUI 让插件/模型生效
ps -ef | grep -i 'python3 -u main.py' | grep -v 'grep' | awk '{print $2}' | xargs kill -9
cd /root/ComfyUI/ && python3 -u main.py --listen --port=6889 --disable-auto-launch >> /var/log/sd_service.log 2>&1 &
```

## 一、架构（已定，2026-07-22 修正）

```
本地 / 云端（免费，无 GPU）              HAI ComfyUI（GPU，开机才计费）
────────────────────────────           ─────────────────────────────
① script_writer.py → 分镜 JSON  ✅      ③ MV-Adapter(i2mv_sdxl) → 9 宫格（一致多视角）★已下
   (Agnes LLM 扩写)                        上传 hero → 自动出 8~9 张一致角度设定板
② agnes_image.py   → hero 参考图 ✅      ④ 视频：AnimateDiff + IPAdapter(喂 9宫格/hero)
   (Agnes 文生图，皮克斯质量好)   ──▶        逐帧锁角色 → 每段 mp4
⑤ ffmpeg 拼接成片（你接时自动打通）
```

**为什么 9 宫格必须用 MV-Adapter 而不是 IPAdapter**：
- 我们实测：IPAdapter(plus-face) weight 0.8→0.95，9 张形象各异、第一张都不搭 → **对非人类角色锁不住**。
- MV-Adapter 是专为「单图→一致多视角」设计的模块，Liblib 上那种一致 9 宫格就是同类技术，本地用 MV-Adapter 复现。
- 9 宫格是**必需**：既是角色设定板，也是每个视频镜头取参考角的来源。

**为什么视频还要 ComfyUI 而不是 Agnes**：
- Agnes 视频图生视频会把参考图当「动画起点」重绘角色（实测完全两个角色）。
- ComfyUI 用 AnimateDiff 让画面动起来 + IPAdapter(喂 9宫格视图) 逐帧约束角色 → 跨帧/跨镜头一致。

## 二、开机后分步协议（严格按顺序，每步确认再进下一步）

### Step A · 零成本探测（不花 GPU 钱）
```bash
python comfy_discover.py --host <HAI地址>
```
- 只读环境，确认节点/模型：MV-Adapter 节点、SDXL、动画模块、VAE、Pixar LoRA、VHS、IPAdapter_plus。
- 缺什么 → 进 Step A0 补齐。

### Step A0 · 一次性补齐（只耗带宽/时间，不耗 GPU）
- 上传本机已下的 7 个文件到 HAI 对应目录（见〇）。
- git clone VideoHelperSuite + IPAdapter_plus；重启 ComfyUI。
- **重启后再跑一次 Step A 确认全 ✅**。

### Step B · 本地出分镜 + 参考图（免费，已验证）
```bash
python script_writer.py --brief "主题：...；风格：皮克斯3D；时长：8秒；必含梗：..." --out output/storyboard.json
python agnes_image.py   # 出 agnes_test.png，改名 hero.png
```

### Step C1 · 9 宫格测试（MV-Adapter，先验证角色一致性）
- 把 `hero.png` 喂给 MV-Adapter(i2mv_sdxl) 工作流，出 9 宫格。
- **你对比 9 宫格 vs hero**：9 张是否同一只角色、多角度合理？
- 不一致 → 换参考图 / 调 MV-Adapter 参数（seed、视角数），只重跑这步。
- 满意 → Step C2。

### Step C2 · 1 段视频测试片（先验证动作+锁角色，最便宜试错）
```bash
python gen_video_clip.py --host <HAI地址> \
    --ref hero.png --grid output/9grid.png \
    --prompt "小刺猬正面挥手打招呼，皮克斯3D" \
    --out output/test_clip.mp4 --frames 32 --fps 16
```
- AnimateDiff 动起来 + IPAdapter(喂 hero/对应 9宫格视图) 锁角色。
- **你对比 test_clip.mp4 vs hero / 9 宫格**：角色一致吗？动作自然吗？
- 漂移 → 提 IPAdapter 权重 / 用对应 9宫格视图作首帧；只重跑这一段。
- 满意 → Step D。

### Step D · 批量生成全部分镜
- 分镜 JSON + hero + 9宫格喂批量逻辑，逐镜调 gen_video_clip.py，每段 mp4 存 D:\Aicomfyui\output\
- （可选）ffmpeg 拼接：检测到 ffmpeg 即出 final.mp4

## 三、已就绪本地资产（D:\Aicomfyui）

| 文件 | 作用 | 状态 |
|------|------|------|
| `script_writer.py` | 关键内容→分镜 JSON（Agnes LLM） | ✅ 已验证 |
| `agnes_image.py` | 文生参考图（Agnes，皮克斯质量好） | ✅ 已验证 |
| `agnes_llm.py` | LLM 客户端（2.5→2.0 回退，关 thinking） | ✅ 已验证 |
| `comfy_discover.py` | 开机第一步：零成本环境探测 | ✅ 已按真实预装重写 |
| `gen_video_clip.py` | ComfyUI 视频（需补 MV-Adapter/9宫格接入逻辑） | ⚠️ 待 HAI 实测后定稿 |
| `prompt_expand.py` | 文字→英文提示词扩写 | ✅ |
| `make_video.py` | Agnes-only 版（视频部分弃用，保留参考逻辑） | ⚠️ 参考 |
| `custom_nodes/ComfyUI-MVAdapter/` | 9 宫格插件 | ✅ 已 clone |
| `models/mvadapter/mvadapter_i2mv_sdxl.safetensors` | 9 宫格权重 | ⏳ 下载中 |
| `models/checkpoints/sd_xl_base_1.0.safetensors` | SDXL 基座 | ⏳ 下载中 |
| `models/loras/Canopus-Pixar-Art.safetensors` | 皮克斯 LoRA | ⏳ 下载中 |
| `models/vae/sdxl_vae_fp16fix.safetensors` | SDXL VAE(fix) | ⏳ 下载中 |
| `models/animatediff/mm_sdxl_v10_beta.ckpt` | AnimateDiff 动画模块 | ⏳ 下载中 |
| `custom_nodes/ComfyUI-VideoHelperSuite/` | 视频输出插件 | ⏳ clone 中 |

## 四、已确认关键事实（避免重踩坑）

- **IPAdapter(plus-face) 实测锁不住非人类角色** → 9 宫格不能靠它，改用 MV-Adapter(i2mv_sdxl)。
- **MV-Adapter i2mv_sdxl** = 上传参考图 → 一致多视角（9 宫格解法），本地用 hf-mirror 直链 `curl -L` 可下（XET 存储已验证可取字节）。
- **Agnes 视频不锁角色** → 必须用 ComfyUI 出视频。
- **HAI 默认无 MV-Adapter / IPAdapter_plus / VideoHelperSuite** → 需本机传或 git clone + 重启。
- **AnimateDiff 预装但动画模块需下载**（2.2G）→ 已下 `mm_sdxl_v10_beta.ckpt`。
- **基座仅 SD1.5** → 需 SDXL 才能跑 Pixar LoRA（已下）。
- **T4 显存临界**：MV-Adapter 官方测试 3090(24G)，T4 15.6G 需 fp16 VAE + vae_slicing，有 OOM 风险 → 首测若 OOM 立即降级。
- **视频段锁角色**：用 IPAdapter(plus 全身版，非 plus-face) 弱锁 + 对应 9宫格视图作首帧，比纯首帧锚定稳。

## 五、风险与降级

| 风险 | 降级方案 |
|------|----------|
| MV-Adapter OOM（T4 临界） | 降分辨率(1024→768)、开 fp16 VAE + vae_slicing；仍不行 → 降级回 IPAdapter+ControlNet OpenPose 出 9 宫格（需补下 ControlNet 权重） |
| 9 宫格不一致 | 换 hero 参考图 / 调 MV-Adapter seed 与视角数，只重跑 Step C1 |
| 视频段漂移 | 提 IPAdapter(plus 版)权重 0.6~0.85；或每段用对应 9宫格视图作首帧(img2video) |
| AnimateDiff OOM | 降帧数(32→16)、降分辨率、开 fp16 |
| 单段动作僵 | 换 AnimateDiff motion model / 提示词加动作描述 |

## 六、你开机后只需做

1. 开 HAI，把 ComfyUI 地址（http://IP:端口）发我
2. 我跑 Step A 探测（零成本），按结论决定是否 Step A0 补齐（传本机文件 + clone 插件 + 重启）
3. Tier1+MvA 就绪 → 我跑 Step B（免费）+ Step C1（9 宫格测试）
4. 你对比 9 宫格 vs hero，说"一致/不一致"
5. 一致 → Step C2 视频测试片 → 你对比 → 一致才批量
6. 全程先测试再批量，绝不盲目烧 GPU 钱
