# 仓库使用与重建说明（克隆即可用）

本仓库**只保留源码、提示词、配置与项目记录**；已在 `.gitignore` 排除可在其他电脑重新生成的媒体与大文件：模型权重（`*.safetensors/*.ckpt/*.pt`）、图片（`*.png/*.jpg/*.jpeg/*.gif/*.bmp`）、音频（`*.mp3/*.wav`）、视频（`*.mp4`）、前端 `node_modules/`、`dist/`、缓存（`cloud/_*`/`clips/`/`c1_output/`/`grid/`）、运行时数据库（`*.db`、`storage/`）、内嵌图片的生成预览（`*_preview.html`）。

> 保留：`.md` 提示词、`.py/.js/.vue` 源码、`.json` 工作流配置、`.webp/.svg/.ico` 前端 UI 图标、项目每日记录（`项目记忆与日志/`）。
> 图片/视频等 AI 产物不在库中——它们由下面的提示词与脚本重新生成（见第 2、3 节）。

## 1. 短剧工作台（Vue3 + FastAPI）

```bash
# 后端
cd 短剧工作台/backend
pip install -r requirements.txt
python run.py                 # 默认 http://127.0.0.1:8770 ，API 文档 /docs

# 前端
cd 短剧工作台/frontend
npm install
npm run dev                  # 默认 http://localhost:5192
```

- 运行时数据库 `studio.db` 首次启动由后端自动建表，**无需手动准备**。
- 素材/分镜图目录为真相源，后端按文件名索引，克隆后直接可用。

## 2. AI 出图 / 出视频脚本（媒体产物的再生成方式）

| 脚本 | 用途 |
|---|---|
| `agnes_image.py` / `agnes_video.py` | Agnes AI 文生图 / 图生视频（需配置 API Key），按提示词重新生成图片/视频 |
| `aliyun_h3/` | PAI-DSW / AutoDL 上的 ComfyUI + MiniMax H3 工作流与一键安装脚本 `setup_h3_pai.sh` |
| `minimax3创作内容/` | 分镜与视频提示词真相源（`.md`）；参考图/分镜图等图片产物不入库，用本目录提示词重新生成 |

- 模型权重（SDXL / LoRA / IPAdapter / ControlNet / MiniMax 等）体积大，**不入库**；请按各脚本内说明从 HuggingFace / 模型源下载，或运行对应 `setup_*.sh` 自动拉取。
- ComfyUI 节点（`custom_nodes/`）如需可单独 `git clone` 对应插件仓库，或按脚本说明安装。

## 3. API 密钥（环境变量，不入库）

本仓库**不含任何明文密钥**（代码已改为读环境变量，历史记录中的密钥已脱敏）。使用前按需在系统环境变量中设置：

| 变量 | 用途 |
|---|---|
| `AGNES_API_KEY` | Agnes AI 出图/出视频（`agnes_*.py`、`短剧工作台/tools/*.py`） |
| `LISTENHUB_KEYS` | ListenHub 多账号，英文逗号分隔（如 `key1,key2`），短剧工作台 provider 播种用 |
| `DEEPSEEK_KEY` | DeepSeek 剧本通道 |
| `AUTODL_H3_TOKEN` | AutoDL 令牌（MiniMax H3 视频通道） |
| `GH_TOKEN` | `pai/*.sh` 下载脚本用的 GitHub token |

> 各密钥请从你的「相关平台和账密」表获取，本仓库不提供也不保存明文。

## 4. 分镜与提示词（minimax3创作内容）

`deepseek分镜/*.md` 为分镜与视频提示词真相源。参考图（`角色图/`、`场景道具参考图/`、`重制版/分镜图/`）与预演视频为 AI 产物，**不在库中**；需要时用 `deepseek分镜/*.md` 里的提示词 + 对应脚本重新生成。提示词本身（文本）已完整入库，可直接阅读/复用。

## 5. 其他子项目

`hedgehog_poses/`、`workflows/`、`小朋友拯救世界/`、`storyboard/`、`trae_seedance_test/`、`cloudbase-imggen/`、`pai/`、`image/` 等均为独立工具/工作流，按各自目录内的说明或脚本运行；其 Python 依赖参照脚本头部 import 自行 `pip install`，前端依赖参照各目录 `package.json`。
