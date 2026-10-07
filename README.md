# AI ComfyUI · 皮克斯刺猬角色一致性 9 宫格

用 ComfyUI（SDXL + Canopus Pixar LoRA + **普通 IPAdapter**（CLIP Vision）+ ControlNet OpenPose）
生成皮克斯风 3D 小刺猬的「角色一致性设定表（9-Grid）」，为后续图生视频准备锁角色 + 锁姿势的资产。

> ⚠️ **FaceID 方案已废弃**：FaceID / FaceID Plus V2 底层用 InsightFace 人脸检测器，
> 只认人类脸，对小刺猬会报 `InsightFace: No face detected.`，锁脸先天失败。
> 改用**普通 IPAdapter**（CLIP Vision 编码整张参考图，不做人脸检测），适合非人类角色的「同一只刺猬摆 9 个姿势」。

## 文件清单

| 文件 | 作用 |
|---|---|
| `hedgehog_9grid_ipadapter.json` | **主用** 9 宫格工作流（普通 IPAdapter 一键 9 路并联） |
| `hedgehog_test_ipadapter.json` | 单图验证版（先跑它确认角色一致性） |
| `make_9grid_ipadapter.py` | 由 `hedgehog_9grid_faceidplusv2_v2.json` 生成普通 IPAdapter 版的脚本（可复现） |
| `run_comfy.py` | 远程提交工作流 + 轮询 + 自动下载出图到本地 |
| `assemble_grid.py` | 把 9 张出图拼成 3×3 设定表 PNG |
| `assemble_grid.py` | 拼图脚本（读 `hedgehog_9grid_out/`，写 `hedgehog_9grid_final.png`） |
| `STATE.md` | 当前进度与交接单（换电脑/换会话必读） |
| `IPAdapterPlus_src.py` | 本地留档的 IPAdapterPlus 节点源码（用于查节点参数签名） |

> 旧的 FaceID 工作流（`hedgehog_9grid_faceidplusv2_v2.json`、`hedgehog_faceid_v2_test.json`
> 等）保留作参考，但**不要再用**——对非人类角色无效。

## 工作流节点接线（普通 IPAdapter，已对照官方插件源码校验）

- `sd_xl_base_1.0.safetensors` → `CheckpointLoaderSimple`（节点 1）
- `Canopus-Pixar-Art.safetensors` → 普通 `LoraLoader`（节点 8，strength 0.8）
- `hedgehog_hero.png` → `LoadImage`（节点 11，IPAdapter 参照图）
- `ip-adapter-plus-face_sdxl_vit-h.safetensors` → `IPAdapterModelLoader`（节点 90）
- `clip_vision_g.safetensors` → `CLIPVisionLoader`（节点 92）
- 节点 10 = **`IPAdapterAdvanced`**，`clip_vision` ← 节点 92，`weight`=0.9，`weight_type`=`linear`，
  `combine_embeds`=`concat`，`embeds_scaling`=`V only`
- `OpenPoseXL2.safetensors` → `ControlNetLoader`（节点 12）+ `ControlNetApplyAdvanced`（节点 41~49）
- 9 路 KSampler（51~59）→ VAEDecode（61~69）→ SaveImage（71~79），`filename_prefix` 对应 01~09

> 注意：简单 `IPAdapter` 节点**不接受** `clip_vision` 形参（会抛 TypeError），
> 因此用 `IPAdapterAdvanced` 显式接 `clip_vision`。`weight_type` 在 Advanced 节点里用 `linear`
> （等价于简单版的 `standard`）。

## 在 HAI 上跑（AI 远程操作）

1. 开 HAI，确认 ComfyUI 在跑，拿到公网地址 `http://HOST:PORT`
2. 确认 HAI 端素材就位（见 `STATE.md` 的清单）
3. 把 `hedgehog_test_ipadapter.json` 交给我，我跑单图验证 → 发你预览
4. 你回 OK → 我跑 9 宫格 → 下载 9 张 → `assemble_grid.py` 拼图发你

本机脚本用法（如需手动）：
```bash
# 提交并下载（host 用环境变量或 --host 指定）
export COMFY_HOST=http://43.155.214.240:6889
python run_comfy.py hedgehog_test_ipadapter.json --out test_out
python run_comfy.py hedgehog_9grid_ipadapter.json --out hedgehog_9grid_out
# 拼图
python assemble_grid.py   # 读 hedgehog_9grid_out/，写 hedgehog_9grid_final.png
```

## 注意

- IPAdapter 权重用 HAI 现成的 `ip-adapter-plus-face_sdxl_vit-h.safetensors`（约 809M），
  CLIP Vision 用 `clip_vision_g.safetensors`（约 2.4G），无需额外下载。
- `antelopev2` 路径若错位需软链修正（详见 `STATE.md`「已知坑」）。
- 参照图 `hedgehog_hero.png` + 9 张姿势骨架必须在 `ComfyUI/input/`（已推 GitHub 仓库）。
