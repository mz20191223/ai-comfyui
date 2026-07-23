# 桃子 AI 视频 · 云端开源管线执行手册（路径 B + 多角度参考）

> 状态：**已准备完毕，待用户开机 HAI 并给 ComfyUI 地址后执行。**
> 本手册是"开箱即跑"的 runbook；所有脚本/提示词资产已在 `D:\Aicomfyui\cloud\` 备齐。

---

## 0. 目标与验收标准

- **基线**：今天已出的 p1 成片（桃子 s01–s05，4 段首尾帧过渡，16s 竖屏，角色一致）。
- **必须修掉的已知问题**：
  - 问题①：s01→s02 草堆被推进飞走、像切场景。
  - 问题②：角色横移/跑动，而非原地探头扒草。
- **硬约束**：视频反复改 → 走云端开源 ComfyUI，迭代零边际成本（不抽卡）。
- **本次新增**：云端生成 2–4 张桃子多角度参考图（正面/侧/背/表情），增强 MSR 与 Qwen-Edit 稳定性，**全程保持与 `peach_role_v6` 一致**。

---

## 1. 最终架构（路径 B）

```
桃子锚图 peach_role_v6.png
        │  (云端 Qwen-Image-Edit-2511 GGUF，保持一致性)
        ▼
  多角度参考图 ref_front / ref_side / ref_back / ref_expr_happy
        │
        ├─► 云端 Qwen-Image-Edit-2511 重出 p1 关键帧 s01–s05（同机位同位置，修问题②源头）
        │       并生成草地背景参考 bg_meadow.png（修问题①源头）
        │
        └─► 云端 LTX 2.3 MSR（角色参考 + 背景参考 + 连续性 prompt）
                逐段生成 s01→s02 / s02→s03 / s03→s04 / s04→s05 视频
                （prompt 强制 固定机位/原地/背景一致 → 修问题①②）
                        │
                        ▼
                ffmpeg 统一 720×1280 竖屏拼接 → p1_scene_cloud.mp4
```

模型对照（两方案）：
| 需求 | 今天（百炼付费） | 本方案（云端开源） |
|---|---|---|
| 角色定稿 | peach_role_v6（资产） | 同左 |
| 多角度参考 | 无 | **Qwen-Image-Edit-2511 云端生成**（本手册新增） |
| 关键帧出图 | wan2.7-image | Qwen-Image-Edit-2511（多参考锁一致） |
| 首尾帧视频 | wan2.7-i2v | **LTX 2.3 MSR**（Apache 2.0 开源） |
| 修问题① | 未修 | 同构图重出 s01 + 背景参考 + 固定机位 prompt |
| 修问题② | 未修 | 同机位关键帧 + 原地 prompt + 多图参考锁身份 |
| 拼接 | ffmpeg | ffmpeg（同） |
| 成本 | 按量付费 | 本地 GPU 免费 |

---

## 2. 已有资产（无需再生成）

| 资产 | 路径 |
|---|---|
| 角色锚图 | `D:\Aicomfyui\peach_role_v6.png` |
| 分镜脚本 | `D:\Aicomfyui\storyboard_25grid.json` |
| p1 关键帧（旧/对照） | `D:\Aicomfyui\grid\s01.png` … `s05.png` |
| 旧成片（对照验收） | `D:\Aicomfyui\p1_scene.mp4` |
| 旧提交脚本（参考） | `D:\Aicomfyui\run_comfy.py`、`comfy_discover.py` |

---

## 3. 云端需安装的节点 / 权重（开机后第一步核对）

运行 `python check_cloud_nodes.py --host <地址>` 自动核对。缺失项按提示装：

| 类别 | 节点/权重 | 来源 | 备注 |
|---|---|---|---|
| 视频模型 | `ComfyUI-LTXVideo`（或 Kijai 版） | GitHub | 需 ComfyUI v0.16+ |
| MSR 多参考 | `ComfyUI-Licon-MSR` + **MSR IC-LoRA V2** 权重 | GitHub / HuggingFace | 多图参考灵魂 |
| 图像编辑 | `ComfyUI-Qwen-Image-Edit`（GGUF 加载） | GitHub | 出关键帧 + 多角度参考 |
| 文本编码器 | Gemma-3-12B（GGUF/FP4） | HuggingFace | LTX 2.3 文本编码 |
| VAE | `taeltx2_3` VAE | HuggingFace | LTX 视频解码 |
| 拼接 | `ComfyUI-VideoHelperSuite` | GitHub | 视频输出节点 |
| 通用 | `SaveImage` / `LoadImage` | 内置 | — |

**权重下载（国内用 hf-mirror）**：LTX 2.3 GGUF/FP8、Qwen-Image-Edit-2511 GGUF(Q4_K_M ~13GB)、Gemma-3-12B GGUF、MSR IC-LoRA V2、taeltx2_3 VAE。

> ⚠️ T4 显存 15.6G + 32G 内存：Qwen-Edit(~13G) 与 LTX(~12G) **不要同时载**，分段提交、上一段完全结束再跑下一段（顺序 offload 到内存）。

---

## 4. 执行步骤（开机后严格按顺序）

### 步骤 A · 连通 + 节点核对
```bash
python check_cloud_nodes.py --host http://<HOST>:6889
```
缺失即装 + 重启 ComfyUI，重跑直到全 OK。

### 步骤 B · 生成多角度参考图（Qwen-Image-Edit-2511，保持一致性）★本次重点
- 提示词资产：`peach_refs_prompts.json`（4 个角度 + 一致性锚定）。
- 把 `peach_role_v6.png` 作为参考图，依次生成 `ref_front / ref_side / ref_back / ref_expr_happy`。
- 生成后肉眼比对一致性，不达标的重生成或丢弃。
- 输出落 `D:\Aicomfyui\cloud\refs\`。
- **🔍 评审闸门**：4 张角度图生成后发你预览，确认与 `peach_role_v6` 配色/体型/五官一致，再进步骤 C。
- 客户端用法（先上传锚图，再提交 Qwen-Edit 工作流）：
  ```bash
  python cloud_pipeline.py go --host http://<HOST>:6889 \
      --workflow qwen_ref_front.json --images ../peach_role_v6.png \
      --map "6:peach_role_v6.png" --out refs --timeout 1200
  ```
  （`qwen_ref_*.json` 工作流在步骤 A 后、依据真实节点名从模板组装。）

### 步骤 C · 从头生成 p1 分镜图（★关键：不复用旧百炼图）
> **决策（2026-07-23 用户定）**：旧百炼 p1 关键帧（s01–s05）本身埋了问题（s01 大全景空镜会被推飞、相邻镜角色屏幕位置漂移 → 视频模型误读为位移）。**必须从头在云端重新生成分镜图**，才能暴露并修掉这些构图问题，而不是在旧图上贴视频。

- 用 Qwen-Image-Edit-2511 多参考（anchor + 4 张角度图）**从零生成 s01–s05**，**强制同机位、同角色屏幕位置、只变探出量**（修问题②源头）。
- 单独生成 `bg_meadow.png`：干净草地背景（无角色），用于 MSR 背景参考（修问题①）。
- 落 `D:\Aicomfyui\cloud\p1_keys\`。
- **🔍 评审闸门（本阶段核心）**：生成后**逐张发你预览**，你来看"构图连续不连续 / 角色位置飘没飘 / 草堆在不在"——这就是"从头开始才能发现问题"的环节。发现问题当场改 prompt 或重出，确认 OK 才进视频。

> 范围：先以 **p1（s01–s05，5 张）作为验证切片**（T4 上快、便于迭代找问题）；p1 视频端到端验证通过后，用同一套"图像生成配方"复制到其余 4 个 plot → 产出完整 25 宫格。如你要求一开机就直接生成全 25 张，说一声我改成整批循环。

### 步骤 D · LTX 2.3 MSR 视频（修问题①②）
- 提示词资产：`ltx_p1_prompts.json`（4 段 + global_rules 强制固定机位/原地/背景一致）。
- 每段：首帧(s0X.png) i2v 锚定 + 角色参考(anchor+角度) + 背景参考(bg_meadow) + 段 prompt。
- 逐段提交（串行），每段超时放宽到 ~30 分钟。
  ```bash
  python cloud_pipeline.py go --host http://<HOST>:6889 \
      --workflow ltx_s01_s02.json \
      --images ../peach_role_v6.png refs/ref_front.png refs/ref_side.png refs/ref_back.png refs/ref_expr_happy.png p1_keys/bg_meadow.png p1_keys/s01.png p1_keys/s02.png \
      --map "6:peach_role_v6.png,9:ref_front.png,..." --out p1_clips --timeout 1800
  ```
- 产出 `p1_clips/s01_s02.mp4` … `s04_s05.mp4`。

### 步骤 E · 拼接 + 验收
```bash
ffmpeg -f concat -i <filelist.txt> -vf "scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2" -c:v libx264 -pix_fmt yuv420p p1_scene_cloud.mp4
```
对照 `p1_scene.mp4` 验收：效果达标 + 问题①②消失。

---

## 5. 两个问题在手册里的具体落点

- **问题①（草堆被推飞）**：
  1. 步骤 C 重出 s01 与 s02 **同构图**（去掉会被推飞的大全景空镜）；
  2. 步骤 C 生成 `bg_meadow.png` 作为 MSR 背景参考，锁死草地；
  3. `ltx_p1_prompts.json` 的 `global_rules` 强制"背景一致且留在画面内、固定机位不推"。
- **问题②（横移跑动）**：
  1. 步骤 C 关键帧**同机位同屏幕位置**（只变探出量），消除"构图差被读成位移"；
  2. `global_rules` 强制"原地、勿横移跑动"；
  3. MSR 多图参考（anchor+4 角度）锁身份；
  4. （可选）叠 depth ControlNet 锁首帧结构。

---

## 6. 验证清单（成片后逐条核对）

- [ ] 4 段视频均生成、时长合计 ~16s、720×1280 竖屏、可播放
- [ ] 问题①消失：草地草堆全程在画面内、无"推飞/切场景"
- [ ] 问题②消失：桃子原地探头/扒草/伸懒腰，无横移跑动
- [ ] 角色一致性：跨 4 段桃子与 `peach_role_v6` 及 4 张参考图一致
- [ ] 多角度参考图本身与锚图一致（步骤 B 已比对）

---

## 7. 风险与回退

| 风险 | 表现 | 回退 |
|---|---|---|
| T4 跑 LTX 2.3 慢 | 单段 >10min | 接受慢；或升 24G(4090)/32G(V100) 跑 FP8/bf16 |
| Qwen-Edit 非人类一致性漂移 | 角度图崩 | 丢弃重生成；仍可用 anchor 单图兜底 |
| MSR 节点名与手册不符 | 工作流提交失败 | 步骤 A 后按真实 `object_info` 重组装 JSON |
| 1.3B/量化运动观感弱 | 不如今天 wan2.7 丝滑 | 升 GPU 跑 14B/bf16；结构问题已修，仅观感差异 |

---

## 8. 文件清单（本目录已备齐）

| 文件 | 作用 |
|---|---|
| `cloud_pipeline.py` | 通用客户端：上传图 / 提交 / 轮询 / 下载图+视频 |
| `check_cloud_nodes.py` | 开机节点核对 |
| `peach_refs_prompts.json` | 多角度参考图生成提示词（4 角度 + 一致性锚） |
| `ltx_p1_prompts.json` | p1 四段视频提示词（含修问题①②的全局规则） |
| `CLOUD_PIPELINE.md` | 本手册 |
| `qwen_ref_*.json` / `ltx_s0X_s0Y.json` | 工作流（步骤 A 后按真实节点名组装） |

---

## 9. 故障排查：我这边访问不了 HAI 时，你在实例内跑的命令

> 场景：你开了机、把 HAI 给的 ComfyUI 地址发我，但我从沙箱 `curl` 连不通（HAI 反代需登录态 / 网段隔离 / 沙箱出口受限）。
> 解决：**你在 HAI 实例的 Jupyter Terminal 或 SSH 里执行下面命令，把输出贴回给我**。我据此判断缺什么、给你装插件的命令，全程无需我直连。

### 9.1 确认 ComfyUI 在跑 + 监听端口
```bash
# 看 python 监听的端口（通常 6889 或 8188）
ss -ltnp 2>/dev/null | grep -i python || netstat -ltnp 2>/dev/null | grep -i python
```

### 9.2 拉取节点清单（存成文件，方便核对）
```bash
# 端口按 9.1 实测改（下面以 6889 为例）
PORT=6889
curl -s http://127.0.0.1:$PORT/object_info -o /root/object_info.json
echo "保存完毕，大小："; ls -l /root/object_info.json
# 顺带做个健康检查
curl -s http://127.0.0.1:$PORT/system_stats | head -c 300
```

### 9.3 关键节点一键核对（不依赖 jq，系统 python3 即可）
```bash
python3 - <<'PY'
import json
try:
    info = json.load(open('/root/object_info.json'))
except Exception as e:
    print("读不到 object_info.json：", e); raise SystemExit
names = list(info.keys())
cands = {
 "LTX2.3视频":      ["LTX","LTXVideo"],
 "LiconMSR多参考":  ["MSR","LiconMSR","MultiSubject","ReferenceVideo"],
 "Qwen-Image-Edit": ["Qwen","QwenImageEdit","QwenImage"],
 "Gemma文本编码":   ["Gemma"],
 "VAELoader":       ["VAELoader"],
 "VideoHelperSuite":["VHS","VideoHelper"],
 "SaveImage":       ["SaveImage"],
}
for k, subs in cands.items():
    hit = [n for n in names if any(s.lower() in n.lower() for s in subs)]
    print(f"{k:16} -> {'OK: ' + ', '.join(hit[:4]) if hit else 'MISSING（需装）'}")
print("节点总数:", len(names))
PY
```
把上面输出整段贴给我即可。**MISSING 的项我会给你对应的 `git clone` 安装命令 + 重启 ComfyUI 命令。**

### 9.4 装缺失插件（仅在 MISSING 时由我给的具体命令，示例占位）
```bash
# 进入 ComfyUI 自定义节点目录（路径按你实例实际改）
cd /root/ComfyUI/custom_nodes
# 示例（实际以我给的为准）：
# git clone https://github.com/Lightricks/ComfyUI-LTXVideo
# git clone https://github.com/.../ComfyUI-Licon-MSR
# 重启 ComfyUI 后重新执行 9.2 + 9.3
```

### 9.5 把参考图/工作流传进实例
- HAI 控制台通常有"文件上传"或 Jupyter 上传功能；或用 `scp` 从你本地传到实例。
- 我生成的 `qwen_ref_*.json` / `ltx_s0X_s0Y.json` 工作流，会让你下载后上传到实例 `ComfyUI/user/default/workflows/` 或直接 `/root/` 下，再在实例内用 `curl` 提交（命令由我提供）。

> 最顺的方式仍是**给我实例的 SSH 或 Jupyter Terminal 入口**——那样我可以直接在实例里操作、自己跑 9.1–9.4，不用你来回贴。如果只能网页控制台，就按上面 9.2–9.3 贴 `object_info.json` 的内容给我也行。
