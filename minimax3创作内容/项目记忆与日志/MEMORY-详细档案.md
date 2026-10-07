# 项目长期约定 · 短剧工作台 + 漫剧《凌晨两点，Bug成精了》

两条线并行：**A. 创作工程**（竖屏软科幻微短剧，共 3 集，9:16）；**B. 自建工作台**（`D:\Aicomfyui\短剧工作台\`，通用可复用，下一部剧从 0 也能用）。

---

# A. 创作工程

## A1 链路
角色/场景参考图 → 分镜图提示词(GPT-Img2) + 视频提示词(MiniMax H3) + 配音(Edge TTS，外部做) → 分镜图 → 成片。

## A2 角色与参考图铁律
- **过客锁定句固定**：`严格锁定过客的面部特征、发型、服饰与体型`（全片通用）。禁写细分特征（年龄/身高/单品…）；强调同一人用「与参考图N同一人」。手持物一律左手。
- **参考图红线**：`手机群聊/红色警报/键盘/终端命令行/公司办公室_场景参考图` 是多状态对比**设计规范稿**，只作风格/家具/氛围参考，**严禁还原布局、复制拼贴排版与色值标注**；界面内容文字写死。手机道具参考图（黑色直板无壳）凡手机镜头必传。
- **传不传人物参考图**：看「画面里有没有这个人」——根本无人→不传；有人但远处→传（标准句+同一人+硬约束防画大）；清晰→传。**视频侧同样要传**（易漏）。
- **真实渲染帧优先于概念稿（09-12 定）**：角色已出过片的，后续镜头优先用其**真实渲染帧**作形态锚点，不传 `XX_角色参考图.jpg`（概念稿有风格漂移/拼贴排版污染）。须逐张写死「取什么/不取什么」：
  - `0110_tail.jpg`（内存黑洞王）：只取形态/质感/色调；严禁带入过客与工位背景、尤其其巨大比例（14d 与魅影同框）。
  - `0112b_tail.jpg`（死循环妖完全体）：只取形态/造型/色调；严禁复制窗口海背景与特写景别。
  - `0114b2_tail.jpg`（权限魅影成型）：半透明灰白雾态、身形修长悬浮下身渐隐；**面部偏暗五官不可辨**（已成片事实，保持此暗部形态、不补强）。
  - **⚠️ 权限魅影是唯一例外（09-15 定）**：魅影形态锚点**一律用 `权限魅影_角色参考图.jpg`**（14b-2 指定的「成型终态唯一锚点」；尾帧只是它的渲染结果且面部暗，拿结果锚结果=没锚）。`0114b2_tail.jpg` 只在需要**首帧/机位/景别/暗部光效**时作锚点（如 14d 首帧）。

## A3 文件与目录
- 活跃工作区 `D:\Aicomfyui\minimax3创作内容\重制版\`；镜头命名 0101/0102…；尾帧 `重制版\分镜图\视频尾帧\`。
- 核心文档 `deepseek分镜\`：分镜图提示词_GPT-Img2 / 中文视频提示词_核对版 / 音频准备清单 / 剧本。
- 资料库 space_id=`jD4Xp2KR7EBarspbtiJlPB`，parent_id=`9Idsa8wG0fqUntQmaPX3m9`。

## A4 视频 API（09-08 定）
- **接口A·多图（主力）**：seed/prompt/duration(1-10)/resolution/ref_audio_0~2/ref_image_0~8。**首行决定模式**：I2VA=`For the target video, at 0.00 seconds..., <Picture 1> (from [Shot 1]) is fully referenced.`；FL2VA=`How the reference pictures align... Picture 2 ... aligns with the S.SS-second mark...`（S.SS=duration）。
- **接口B·首尾帧**：first_frame/last_frame 必填，无 ref_audio，最高 768p。精确停靠→B；动态过程（雾涌/回头）→A+I2VA。长距离推进用首尾帧会中段硬切→拆两镜走 A。
- 768p 竖；seed 首跑留空；**上传先音频后图片**；`Image N` = 参数 `ref_image_(N-1)`，正文用 Image N。白模 mp4 永不进 API。
- **成本（09-15 定）**：沿用旧平台 MiniMax H3，**¥0.04/秒**（768P）。秘塔 0.09 / 官方 0.50 / 302.ai 0.52 均更贵 → 用户决定不迁移。

## A5 提示词通则
- **信息边界（09-17 定，铁律；取代旧的枚举式三条）**：提示词里只能出现**本次调用看得见、做得到**的信息。三类越界一律删——
  - **跨镜**：提到别的镜头（「承接上一镜 / 视线落点 / 上镜尾帧 / 与 14b-2 连戏」）→ 衔接靠 `ref_image_0`，不写进提示词。
  - **跨时**：**分镜图（图像侧）禁一切时间信息**——模型只有一帧，"视频 0.00 秒的首帧 / 必须与视频前 3 秒一致 / 起始态"它看不见也用不上；视频侧只许写**本次调用内**的时间轴，禁止「整片第几秒 / 起始态 / 终态」这类跨调用时间锚。
  - **跨层**：工作流黑话与字段——「起手态 / 结果态 / 终态 / 将欲动作」「（= Picture N）」「ref_image_N / duration / 接口A / I2VA」→ 全部移进 `> 📋【工作流注释·非提示词·勿喂模型】` 块。
  - **自检**：**这句话里有没有模型看不见、也用不上的信息？** 有 → 删。
  - 🔑 为什么升级：旧表述是枚举式（只列「运镜/POV」「跨镜交代」「未上传实体」），而「本图是视频 0.00 秒的首帧」**不提镜号、不是运镜、没点名实体 → 三条例外全躲过**，直接导致 14d 首帧画成"召唤完成态"与视频指令打架。枚举必漏，故改为按信息边界判定。
- **一次性工具思维**：每句提示词只放当前图/视频需被执行的元素；参考图没覆盖的元素一律不提（模型会乱画/脑补）；说明/注释不进喂模型的提示词（留文档级 `>` 注释）。
- 未上传参考图的元素不点名（用通用负向词，如「严禁出现任何人物」而非「含过客」）。
- **单角色镜头不描述其他角色**（参考图只取某属性 ≠ 该主体要出现）。
- 四层结构：素材声明 + 不可变项 + 时序指令 + 风格；每图/音频写明用途。**纯净性**：只留可执行描述，剪辑信息放「后期音轨」块。
- **防转场**：必须写「严禁黑场、黑帧、淡入、淡出、溶解、叠化」。
- **台词**：`**角色："台词"**` 独立成句加粗；整句一气呵成不拆 utterance；视频时长 ≥ 音频总时长；**时长用 mutagen 精测**（Windows 属性会四舍五入）。
- **分镜图 vs 视频分离**：分镜图提示词（GPT-Img2）只写「图长什么样」，**严禁 POV/运镜/空间锚点**；空镜分镜图严禁塞人物图作参考。衔接说明块加 `📋【工作流注释·非提示词·勿喂图像模型】` 标注，只留出图指示。

## A6 镜头衔接
- ref_image_0 = 上镜尾帧；分镜图作 ref_image_1。尾帧含本镜禁止元素 → 分镜图作首帧（**硬约束 > 连续性**）。
- 键盘/屏幕镜头相机位置写死防镜像翻转；左右以角色自身为准（镜头在他右后方45°→可见其右侧脸颊）。
- **姿态保持优先于姿态运动**（可选项非铁律）：先保提示词纯净，再决定是否用完成态硬切规避回弹。

## A7 镜头 14 系列（魅影雾气实体化，白灰雾）
| 镜头 | 内容 | 时长 | 音频 |
|---|---|---|---|
| 14a-1 | 雾引路+推进（落幅人~15%） | 4s | 无 |
| 14a-2 | 环绕侧后45°推近15%→70%+雾手搭右肩（已出片，尾帧已导） | 5s | 无 |
| 14b-1 | 雾手湮灭·猛回头：首帧=14a2尾帧（背身+右肩搭雾手），演「雾手原地溃散→单向猛回头到3/4右侧脸→定格」；不切镜不演魅影 | 2s | 无 |
| 14b-2 | POV·魅影凝聚并完整成型：独立空镜，雾团→凝实半透明灰黑雾态人形 | 3s | 无 |
| 14c | 过客质问「你是谁？」全程站立；首帧=重出 `0114c.jpg`（站立·0°正脸完成态）硬切，不再从0114b起身 | 4s | 云希-10%（1.56s） |
| 14d | 纯魅影镜头·过客不入画：魅影招两妖（左死循环妖/右内存黑洞王）。首帧=`0114b2_tail.jpg`（兼机位/景别/暗部锚点）；魅影锚点=`权限魅影_角色参考图`、两妖=真实帧。体量：死循环妖与魅影同级、黑洞王巨型 | 7s | 云健-20%/-10%（待生成） |

- **空间关系（09-12 定）**：权限魅影始终在**过客背后**。14c 过客须**保持面朝身后（魅影方向）**质问；措辞**禁用「转身」**；退后锚定「远离魅影方向」。14c 机位=魅影侧 0° 正对（光轴垂直于面部朝向），正脸直视镜头、魅影在相机后方自然不入画。显示器=他身后的显示器。
- **雾臂设定**：搭肩只是魅影从远处雾里伸出的雾臂（触须），本体在远处；14b=回头同时雾臂**原地湮灭（溃散）非抽离**；14d 勾手用本体雾臂，硬约束禁止任何雾臂贴近过客。
- **成型态一致性**：14b-2 完整成形，14d/17 保持不退化（半透明雾质、禁不透明实体/禁发光眼/禁贴近镜头）。14c 只拍过客，不渲魅影人形。
- 17/21 锚点：死循环妖=`0112b_tail`、黑洞王=`0110_tail`（真实帧），**权限魅影=`权限魅影_角色参考图`**；17 过客「踉跄后退半步」、21「重摔地面」替代旧椅滑/翻倒。

## A8 工程规格与节点（09-10 定）
全片统一 **768x1344 / 8bit / 24fps / h264+aac**。生成节点固定 `minimax_h3_image_audio_to_video_v2`（8-bit）；**弃用** `minimax_h3_zm_u24`（10-bit 伪高清、兼容差）。体检 `白模预演/scan_all_mp4.py`，异常 `白模预演/mp4_to_8bit.py` 转码（不覆盖原文件）。ffmpeg = `imageio_ffmpeg.get_ffmpeg_exe()`。中文路径下 cv2 静默失败 → 存读图用 PIL+numpy。

---

# B. 短剧工作台

## B1 定位与架构
- **通用可复用**（下部剧从 0 也能用），**不写死**任何接口/角色/片名。Vue3+ElementPlus+Vite 前端 / Python FastAPI+SQLite 后端。
- 端口：**后端 8770，前端 5180**（`/api` 代理到 8770）。`D:\Aicomfyui\短剧工作台\`；说明 `README.md`、调研 `docs\01_开源调研与设计方案.md`、模板 `docs\提示词模板\`。
- 素材仍指向 `minimax3创作内容\重制版\`**不搬家**——md 与素材目录是真相源，工作台只做索引 + 写回。
- 视图 11 个：项目列表/任务中心/接口与设置/总览看板/镜头看板/镜头详情/资产库/提示词中心/创作流水线/时间轴与合成/健康报告 + 新增**剧本页**。

## B2 核心机制
- 镜头勾选出场资产 → **参考图槽位与提示词「参考图N / Image N」自动派生**；`Image N` == 参数 `ref_image_(N-1)`（比较时要换算）。
- 三个自动化：**尾帧自动回流下一镜 ref_image_0** / 音频 mutagen 精测校验 `duration ≥ 音频+偏移` / 引用文件存在性校验。
- **提示词 Lint** 10 条可开关规则（含：逐镜时长≤10s、台词装得下、节拍恰好一次·按序·连续、不跨场次、台词必须在 `<d>[Chinese]` 内且标点未改、对齐指令与镜号/秒数对账、运镜词在官方 20 词表内、防转场句、禁跨镜交代、**禁角色名**、风格短语统一、同框≤3人、Picture N 真实存在防幽灵引用）。
- **镜头详情页两个闸门**：①出图确认（改提示词→生成→候选挑一张采纳，写回 `0NNN.jpg`）；②出片确认（确认文案/槽位/时长→生成→采纳成 `final_video_path`）。**采纳才动素材目录**。

## B3 三通道真实参数（真相源：腾讯文档『相关平台和账密』 https://docs.qq.com/sheet/DU1NXU3JMZGR0Skdv?tab=BB08J2 ）
> ⚠️ 早前基于网络搜索写的「DeepSeek 官方 deepseek-v4-flash」「gpt-image-2.5 = flare/sunburst + images/generations」**全部作废**。

**① 剧本 = DeepSeek（官方文档已确认）**：base `https://api.deepseek.com`（兼容 OpenAI，另有 `/anthropic`）；`POST /chat/completions` + `Authorization: Bearer <key>`，取 `choices[0].message.content`。**⚠️ 请求里的 model 必须发 `deepseek-flash`**——旧名 `deepseek-v4-flash` 仍可调但文档原话「对应模型已下线，请求将由 DeepSeek-V4.1-Flash 提供服务并按 Flash 价格计费」；**用户表里写的 `Deepseek-V4.1-Flash` 是服务端展示名，不是请求该发的字符串**。另有 `deepseek-v4-pro`。可选 `thinking:{type:"enabled"}` + `reasoning_effort`。Key `sk-[REDACTED]`。**零成本验证**：`GET /models`（Bearer 鉴权，不耗 token）。

**② 资产图 = gpt-image2.5 → 实为 ListenHub OpenAPI（api.marswave.ai）**：base `https://api.marswave.ai/openapi`；Bearer 鉴权；响应信封 `{code,message,data}`。
- 同步 `POST /v1/images/generation` → **base64**，取值 `candidates[0].content.parts[].inlineData.data`（**无信封**，是模型原始 JSON）。
- 异步（工作台首选）`POST /v1/images/generation/async` → `data.taskId` → 轮询 `GET /v1/images/generation/tasks/{taskId}` → `data.images[].url`；status = pending/generating/success/failed。
- **免费端点（连通性探针，不扣积分）**：`POST /v1/images/generation/estimate-credits`（返 `credits/canGenerate/requiresSubscription`）、`GET /v1/user/subscription`、`GET /v1/speakers/list`。
- 请求体：`provider`（必填 `openai`）+ `model`（文档默认 `gpt-image-2`；用户口称"2.5"→**确切 id 待确认**）+ `prompt` + `referenceImages[]`（每项二选一：`fileData{fileUri,mimeType}` 公共 URL 或 `inlineData{data,mimeType}` **base64 内联 ← 本地素材走这条，无需上传**）+ `imageConfig{imageSize:1K|2K|4K, aspectRatio, quality}`。参考图上限：gpt-image-2 **4 张**、gemini-3-pro-image 14、seedream-5-0-pro 10；支持 9:16；4K/high 需付费订阅。
- **额度判定**：`402` 积分不足；`429` 限流（读 `Retry-After`）；免费通道忙 → `failReason=free_relax_busy|free_relax_timeout` + `retryable=true`。
- 已验证：5 个 key 的第 1 个（`lh_sk_6aa8fa56…`）可用；另 4 个 `lh_sk_6aa8fb11…` / `lh_sk_6aa8fbb7…` / `lh_sk_6a06f6c3…` / `lh_sk_6aa8fc35…`。
- **副产品**：同一套 key 还能出**视频**（`/v1/video-generation/generate`，`model: MiniMax-H3`，768p/2k、4–15s、content 数组支持 first_frame/last_frame/reference_image/reference_audio）、**TTS**（flowspeech）、音乐 → 备用通道。

**③ 视频 = MiniMax H3 @ AutoDL ComfyUI**：base `https://autodl.art`；提交 `POST /api/v1/comfyui/comfyui_workflow/minimax_h3_image_audio_to_video_v2` → `data.task_id`；查询 `GET /api/v1/comfyui/comfyui_workflow/result/{task_id}`。鉴权 `Authorization: <token>`（**裸 token 无 Bearer** → `auth_scheme` 置空串），token `[REDACTED-AutoDL]`（AutoDL 令牌分组选 ComfyUI）。入参同 A4；出参 `{msg,code:"Success",data:{status,results[{url,type,file_type,output_type}],task_id,client_id}}`；status = `QUEUED|RUNNING|SUCCESS|FAILED`。**results 的 URL 有效期极短，拿到必须立刻下载**。⚠️ **硬阻塞**：`ref_image_*`/`ref_audio_*` 只收 **URL**，本地素材如何变 URL 未解（待问用户现有做法；备选 base64 data URI 或 Cloudflare Tunnel）。

- **引擎现状**：`provider_engine.py` 已支持「本地文件 ↔ data URI」双向（`_to_data_uri`/写盘）+ JSON body（`json=`），**不支持 multipart**。上面三条通道**全走 JSON**，引擎现成可用。
- **多账号轮换（09-15 用户要求，出图尤其需要）**：供应商下挂**密钥池**（别名/ key / 启用 / 状态(可用·冷却中·额度耗尽) / 冷却至 / 失败次数 / 上次使用 + 手动禁用）；策略默认 **round-robin 取"可用"里最久未用**；命中**额度类错误**（402 / 429 / free_relax_*）→ 该账号打冷却并**自动换下一个重试**（重试上限 = 池内可用数）；任务里记录本次账号别名便于对账；生图/视频/文本三类通用。
- **⛔ 铁律：任何真实付费调用前必须先问用户**（原话「你别自己一直测，等下消耗我的额度…你先问我」）。只读文档不受限；连通性探测一律优先免费端点。
- **配置全配置化**：请求体 **Jinja2 模板** + 应答 **JSONPath** + 同步/异步双模式 + 按能力分 base_url；换平台只改「接口与设置」页，不改主程序。

## B4 剧本链（批 A，2026-09-16 建成）
- **入口**：项目列表行「剧本」按钮 → `/p/:pid/script`（不放左侧导航）。
- **后端**：新表 `scripts`（project_id / version 自增 / kind / title / content / source / prompt_used / episode_id / meta，**最新版即当前剧本**）；新 `services/script_service.py`（4 种提示词构建 build_script/revise/split/continue_messages + 解析容错：先抠 JSON，失败退化到「第N集」正则切分 + `apply_episodes` 落库助手）；新 `routers/scripts.py` **12 个接口**；新任务类型 `llm_generation` + `task_runner._run_llm`（`save` 决定落点：存版本 / 写回某集 / 不落库只回文本；走 `provider_engine.execute(category=llm)`，模型 `deepseek-script`，取 `_collect_sync` 的 `text`）。
- **前端 `views/Script.vue`** 三块：①剧本（创作要求输入框 + 可选参数 集数/分钟每集/题材/画面风格 + 生成/按意见重写/保存为新版本/预览提示词 + 版本历史）②智能分集（AI 分集 → 可编辑表格 → **确认写入**才落 episodes）③集数管理（集列表 + AI 续写新增一集 / AI 重写某集 / 跳看板）。
- **参数确实会带上**：`build_script_messages` 里 `_project_block` 拼【项目】【题材】【画面风格】【画幅】，集数+时长拼【体量】全剧共 N 集、单集约 M 分钟，自由文本进【创作要求】。空值自动沿用项目上的 genre/visual_style；都不填则只发题目与格式要求。
- **前置条件**：**DeepSeek key 还没填进密钥池**（provider/model/默认模型都启用、base_url 对，但 `provider_credentials` 与 `settings` 都空）→ 点生成会 401，需到「接口与设置」页填。
- **批 B 未做**：资产图出图 `POST /assets/{id}/generate-image`（一次出一张三视图合成图，GPT 一次最多吃 4 张参考图）+ 资产库「出图」按钮。

## B5 配音/音频铁律（09-15 用户定，改架构级别）
- **工作台不做配音生成**（原话「Edge TTS…相当于是本地执行的，我最终是不用它的」）。
- **音频 = 镜头视频配置时挂上的素材**：外部做好 → 镜头页「选择音频文件」→ **mutagen 精测时长** → 校验 `时长 ≥ 音频 + 偏移` → 出片时作 `ref_audio_N`。
- 已落地：配置层**没有 tts 类供应商/模型**（`local-tts`/`tts-edge` 已删，`provider_seed.RETIRED` 清残留 + 删 `model_settings` tts 行）；`task_runner` 无 `_run_tts`，`kind=tts` 报 400；接口 `POST/DELETE /api/shots/{sid}/audio`；`shot_service._dialog_lines()` 补 `audio_resolved_path`/`audio_exists`。**不要因为「免费」把 Edge TTS 加回配置层。**

## B6 资产库
- **上传**（09-15）：`POST /api/assets/{aid}/upload-image`（multipart：`file`/`save_as`/`dest_dir`/`usage_kind`），按类型选落点（character→项目 `ref_dir`；scene/prop→`workspace_dir\场景道具参考图`），默认命名 `{资产名}_角色参考图.ext`，**同名同体积→复用不落副本**，非图片丢弃，原本无图则自动设主图。前端两个入口：「从素材目录选」+「上传图片」。
- **资产重复待决（09-15）**：`终极Bug魔王`(id 3) 与 `终极Bug王`(id 24) 覆盖镜头几乎重合；全项目 md **`终极Bug王` 121 次 vs `终极Bug魔王` 13 次** → **`终极Bug王` 是正式名**。已给 id 24 挂上 `角色图\终极Bug王_角色参考图.jpg`（2560x1440，主图）。**待用户拍板**：是否合并、是否删重复文件。

## B7 状态轨（09-16 用户拍板重做）
- **只留单轨任务态**。原先的 `shot.readiness`（`draft/extracting/pending_confirm/ready` 四枚举 + `confirmed_at` 闸门）与候选表（`shot_candidates`/`shot_dialogue_candidates`）**已彻底删除**（原话「就绪态没啥用吧，我觉得可以删除」「我这个项目不需要候选」）；迁移写在 `db.py` 的 `_DROP_INDEXES`/`_DROP_COLUMNS`/`_DROP_TABLES`。**禁止把"生成中"写进镜头本身**——任务态一律从 `generation_tasks` 聚合。
- 任务态：`submitted`(已提交) → `running`(进行中) → `succeeded` / `failed` / `cancelled`。旧 `pending` 迁移为 `submitted`。提升时机：`submitted`=已提交给接口；`running`=接口回报进行中（本地同步执行直接进 running），由 `_progress(..., mark_running=True)` 提升。
- **看板分「出图」「出视频」两列**，各取该类型**最后一条**任务，聚合 `{image, video, has_running}`（`shot_service._task_state_from`）；组件 `components/TaskPill.vue`（跑着显示 `N%`、失败显示原因、无任务 `—`）。
- **失败原因结构化**：`generation_tasks.fail_kind` ∈ `rate_limit`/`insufficient_balance`/`auth`/`api_error`/`interrupted` + `fail_message`；由 `task_runner.classify_failure()` 从 `QuotaExceeded.kind` 映射。
- **僵尸回收**：开服时 `task_runner.recover_zombies()` 把残留 `submitted`/`running` 标 `failed + interrupted`；`main.py` 启动时调用并记日志。

## B8 数据库与性能铁律
- **每线程一条 SQLite 连接长期复用**（`db.py` 用 `threading.local()`）。`get_conn()` 是**事务边界**——只 commit/rollback，**不 close**。**禁止自己 `sqlite3.connect`**，一律走 `db.conn()`。
- 原因：绿盾过滤驱动让 `sqlite3.connect()` 单次 **10~30ms**，一条查询只要 **0.14ms**（差 180 倍）。原先每次新建连接 → `list_shots`（340 次查询）**55 秒**；改后 **6.8ms**。
- `PRAGMA journal_mode=WAL` 是**库级持久属性**，只在 `init_db()` 设一次（每条连接都设会白抢写锁）。
- `list_shots` 逐镜 N+1 已改按集批量（`_grouped_by_shot` 助手，`_MAX_VARS=900` 防占位符超限）。
- **验收手法（强烈推荐复用）**：把改动前实现原样照抄成「黄金参照」，与新版逐字段比对，`json.dumps(sort_keys=True)` 必须逐字节相同。**本手法当场抓出一处真实差异**（批量版多带出分组用的 `shot_id`）。

## B9 前端规范
- **UI 字号铁律（09-15）**：全站字号**只允许**用 `frontend/src/styles.css` 顶部的 `--fs-mini/sm/base/lg/xl`，**禁止在 .vue 里写死 px**。4 档 `html[data-fs]`：紧凑/标准/**大(默认)**/特大 = 正文 13/15/16.5/18px；联动尺寸用 `--ui-side/top/kv/thumb/ctl*`。EP 侧必须同步 `--el-font-size-*` 与 `--el-component-size-*`；**`--el-font-size-extra-small` 要指向「次要文本档」而非角标档**（它被 `.el-table--small` 使用，指错会出现"正文变大了表格没变"）。`.el-button--small`/`.el-input--small` 内部写死 12px 需单独覆盖（**EP 共 70 处硬编码 12px，本工作台 `size="small"` 有 182 处**）。
- **操作列居中（09-16）**：全站 17 个「操作」列统一加 `class-name="op-col" label-class-name="op-col"`，CSS 在 styles.css 里 `.el-table .op-col .cell{text-align:center}` + `.op-col .cell .op-row{justify-content:center}`。**原因**：操作列较宽时表头文字左对齐会显得悬空。表头中线与按钮中线必须重合（探针裁决）。

## B10 运维与踩坑
- `run.py` 是 `reload=False`，**改后端代码必须重启**；重启用工具的 `run_in_background`，**`nohup … &` 在 Bash 工具里不保活**。
- 停服务：`netstat -ano | grep :8770` 取 PID → `MSYS_NO_PATHCONV=1 taskkill /PID xxx /F`。
- **本机 `ms-playwright` 的 chromium 报 `0xC000007B` 跑不起来**（`agent-browser` 同样起不来）；浏览器自动化用**系统 Chrome** + `@playwright/cli` 自带 `playwright-core`（`PW_CORE` 环境变量或脚本内默认路径）。
- 路径常量：`BACKEND_DIR=parents[1]`，`DATA_DIR`/`STORAGE_DIR` 挂**项目根**（不在 backend 下）；**不移动既有文件**（移动触发绿盾加密）。
- **并行编辑同一个文件会互相覆盖**——Edit 报成功但内容没进去（曾中招：`provider_seed.py`/`task_runner.py`/`shot_service.py`/`Settings.vue`/`Health.vue`）。**同一文件多处改动必须串行，改完立刻 Read 回读校验**。CRLF 文件用 Edit 匹配不上时改用带唯一性断言的补丁脚本。
- **造测试夹具必须继承真实模型参数**：轮换演练"失败"的真因是脚本自造的 `defaults` 缺 `quality` → 坏号好号都返 `400/29003`。**不是代码 bug**。
- 环境：Bash 工具本机 PATH 异常（`dirname/head/ls/tail` 找不到），命令前需 `export PATH="/usr/bin:/bin:/c/Windows/System32:/c/Program Files/nodejs:/c/Users/Administrator/.workbuddy/binaries/PortableGit/versions/1.2.0/usr/bin:$PATH"`；**PowerShell 工具 stdout 不回传**，改用 Bash。node 脚本执行前缀 `NODE_OPTIONS= BASH_ENV=`。
- **浏览器性能坑**：若 DCL 恒定多出约 1.5s，看 `domainLookupStart - fetchStart`——Chrome 的**代理解析/自动探测（WPAD）**会阻塞首请求约 1.6s，`--no-proxy-server` 启动即消失（1852ms→324ms）。**不是应用问题，别优化前端**。

## B11 镜头设置 → 提示词注入（09-15 建成，重要机制）
- **保存时自动注入**（不是按钮/模板变量）；视角**两边都进、措辞分开**（原话「正常要两边都需要这个视角描述的吧」）。
- **分工**：景别+视角+主体位置=静态构图 → 进 `image_prompt`；机位+运镜=动态 → 进 `video_prompt`；**运镜绝不进分镜图**。
- 措辞两套（`wizard_service.ANGLE_AS_FACT`/`ANGLE_AS_CAMERA`）：分镜图写**画面事实**，视频写**机位指令**。⚠️ **除过肩/背身/主观外，措辞里一律不写「人物」**——主体可能是手/键盘/屏幕（镜头19 是双手特写）。
- 注入锚点 = **`竖屏9:16构图`**（两份提示词都稳定有），插在该句 `。` 之后。
- **幂等靠记账**：`shot_details.wiz_image_note`/`wiz_video_note` 存「上次注入的原文」，改选时先摘旧再插新。
- 🔴 **绝不覆盖手写内容**：视频正文已有手写 `运镜：` 时**不注入运镜**（只注机位），前端黄框提示「已有/待并入」。原因：镜3 本有 `运镜：镜头从分镜图构图缓慢向下微推…`，再注 `运镜：横摇` 会自相矛盾。
- 接口 `GET /shots/{id}/wizard-note`（只算不写，前端预览用**它**）、`POST /shots/{id}/apply-wizard`。**措辞唯一事实源是 `wizard_service.py`，前端不自己拼。**
- **「点正文即可编辑」（09-16 端到端验证）**：镜头设置改**弹窗**，两个入口 ①提示词工具栏「镜头设置」②**直接点正文里那句镜头语言**。`PromptEditor.vue` 用 `rendered` computed 把 `wizardNote` 首次出现处包成 `<span class="wiz-link">`，点击 emit `open-wizard`。**这句只在「该镜头的提示词里真的注入过」时才显示**（数据状态，不是 bug）。
- 端到端验证手法（可复用）：备份单条 `shot_details` → 调**真实接口** `apply-wizard` → 系统 Chrome 打开详情页确认 `.wiz-link` 出现且点击弹窗回显 → 逐字还原并断言。**别手改提示词正文造测试数据。**
- 「常用库/片段库」下拉**已从提示词编辑器删除**；详情页**单列竖排**；标题**只读**；「确认本镜」按钮已删。
- **镜头语言字段回填（09-15）**：`tools\audit_camera_fields.py` 盘点 → `dump_shots.py` 导出依据 → `fill_camera_fields.py` 回填（**只写字段、绝不碰提示词**，跑完自动校验提示词未变，幂等）。已回填第1集 113-121（14c→23）；第1集 1→14b-2、第2/3集**仍为空**（待用户定）。

## B12 镜头示意图（09-15 建成；09-16 瘦身）
- 原图在 `assets-src/shot-diagrams/`（PNG，**不进发布目录**）；发布目录 `frontend/public/shot-diagrams/` 只放 320px 的 WebP，前端 `/shot-diagrams/*.webp`。原图 15 张 8.24MB → **瘦身到 0.17MB**（同尺寸 WebP 比 PNG 小约 10 倍）。瘦身脚本 `tools/optimize_diagrams.py`（不带 `--apply` 只试算）。
- **景别（7）= AI 全身底图 + 程序精确裁切**（`tools/fix_shot_diagrams.py`）。AI 对"比中景更近"有强肖像偏好、会把 MCU/CU/ECU 画成同一张胸像 → **构图就是裁切框，裁切比让模型猜准**。按 `fill=画面高/身高`：ECU 0.115 / CU 0.267 / MCU 0.33 / MS 0.43 / MLS 0.76 / LS 1.18，ELS 由 LS 缩 22% 贴白底。
- **视角（8）= AI 生成**；DUTCH 用平视图旋转 20°；POV 已接受「手伸向镜头」那张。
- **运镜（11）= 代码画的侧视机位图** `components/MoveDiagram.vue`。**不做 AI**（靠箭头表方向，AI 必崩）。
- Agnes API 本沙箱可用：`apihub.agnes-ai.com/v1/images/generations`，`agnes-image-2.1-flash`，3 并发 15 张/65 秒，`tools/gen_shot_diagrams.py`。⚠️ 请求 `1024x1792` 实际可能返回 **736x1312**，按实际尺寸算。
- `tools/contact_sheet.py` 把一批图拼成联排图 → **一次 Read 看全，省 context**。

## B13 剧本生成两层方案（09-15 拍板，模板已写）
- ①**戏层**（`llm_script`）= 场次 + 节拍流 + 台词结构化（说话人/语气/台词）+ 时长确定性折算（**台词 4.5 字/秒、动作 2.5 秒/拍、单集 ±15%**），**本层无镜号**；②**镜层**（`llm_storyboard`）= 切镜 + 分镜图提示词 + **视频提示词中英双语各一份**（英文喂 H3、中文供人审，入库 `video_prompt` + `video_prompt_en`）。产物仍是现有 md 格式（`## 镜头N` + 三个 `###` 小节），不推翻现有工作流。模板：`短剧工作台\docs\提示词模板\01-剧本生成-戏层.md`、`02-分镜生成-镜层.md`。

## B14 MiniMax H3 提示词官方写法（09-15 核对，shuohao 内化版）
结构四块 = ①首行对齐指令（I2VA / FL2VA 见 A4）②`integrated_multimodal_description:` + 每镜独立一行 `[Shot k]`（切点时刻开头）③`overall_soundscape:`（环境/动作声，**不复述台词**）④`non_diegetic_music:`（没有写 N/A）。**整条默认英文**，但三样保留原文语言：**台词逐字进 `<d>[Chinese] …</d>`（标点都不许改）**、歌词、画面里可见文字（英文双引号原样引用）。**禁角色名**，用通用身份（an old ferryman / the man in his 30s）。运镜用官方 20 词表，必须落在本镜自己那一行。**声景也是动作指令**——画面动作改了声景要一起改。说话人首次出现给辨识信息并编号 `(S1)(S2)`；画外音用 `says in an off-screen voiceover … while their lips remain completely closed`。人物**此刻位置状态**要与分镜图一致（图文对不上，模型听图的）。中文模式阈值：`参考图与目标视频的对齐——` / `整体视听描述：` / 配乐没有写「无」。

## B15 自检工具（改完必跑）
- `tools\check_opcol.cjs`（**纯静态、零依赖、不用浏览器**，09-16 新增）：扫全站 15 个「操作」列，估算 compact/normal/large/xlarge 四档字号下按钮组所需宽度 vs `el-table-column` 实际 `width`，输出 `ALL_FIT` / `CLIP_FOUND`。**加/删/改操作列按钮后必跑** —— `.op-row` 是 `nowrap`，列宽不足时右侧按钮被静默裁掉（不报错、不换行）。v-if/v-else 互斥分支按分支取最大、不累加；`{{}}` 占位按半角短串估。
- `tools\smoke_pages.cjs`：按 `router/index.js` 逐路由打开全部页面，检查白屏/控制台报错/4xx-5xx（曾 11/11 通过）。
- `tools\probe_oprow.cjs`（操作列按钮单行不换行，4 档字号 × 全页面）、`probe_alignment.cjs`（表头中线 vs 按钮中线）、`probe_font.cjs`（字号档位实测 + 真实点击切档与持久化）、`ui_tour.cjs`（全页面真实浏览器巡检，镜头 id 要动态取）、`probe_board_perf.cjs`（页面级性能）、`probe_shot_audio.cjs`、`probe_asset_upload.cjs`、`probe_wizard_diagrams.cjs`、`probe_wizard_filled.cjs`。
- `backend\scripts\_audit.py`（数据体检）、`_parse_check.py`（解析自检）、`_e2e_tail.py`（回流演练）、`_test_isolation.py`（跨项目隔离回归，临时项目跑完自清）。

## B16 项目隔离铁律（09-15 定，多项目后不许串）
- 供应商/模型/密钥**全局共用**（多剧一套配置）；资产/集/镜/明细/台词/健康/lint 规则/模板/片段**按 project_id 隔离**；任务中心**跨项目**但列表带「项目」列。
- **`POST /shots/{id}/refs` 必须核对资产与镜头同项目，不一致 400**（`_project_id_of_shot()` 已实现）。同一素材给两部剧用 → **各建一条资产记录指向同一文件**，不做跨项目共享资产。

## B17 待办 / 待决
- **待用户**：① DeepSeek key 填进密钥池（否则剧本页 401）；② 看板要删哪几列（镜号/标题摘要/首帧分镜图/出图/出视频/时长/模式/音频/操作）；③ 项目列表「目录」按钮是否删（已被「编辑」覆盖）；④ 终极Bug王/魔王 是否合并；⑤ H3 本地素材 → URL 的做法；⑥ 第2/3集镜头语言字段是否回填。
- **待做**：批 B 资产图出图；九宫格选帧、chip 引用(@图库/#颜色/~片段)、可编程适配器、时间轴调优。

## 文档维护
删段前先全局搜引用；批量改大文档先限定目标段落切片。

## C 09-16 前端收口（导航极简 / 合成页 / 资产库按钮）
- **侧栏最终**：单 el-menu 3 项（项目列表/任务中心/接口与设置）；项目级页一律走「项目列表」行操作列。
- **项目列表操作列最终**＝ 分集 / 剧本 / 资产库 / 合成 / 编辑 / 删除（宽 300）。已删：目录（与编辑重叠）、导入文档（后端接口保留）、时间轴（改名合成）。
- **合成页**（原「时间轴与合成」）：只留 自动建轴/重建/体检/合成整集 + 片段表（序/镜号/文件/时长/状态/预览）。已移除页面上的 入点/出点/转场/启用/调序/转8bit/删段，**后端 timeline.py 全套与 api 方法保留**。
- **资产库/合成按钮曾点了无反应**：模板写了 @click="openAssets(row)"/openTimeline(row) 但脚本段未定义这两个函数（vite build 不报错）。已在 Projects.vue 补 openAssets()/openTimeline()。**教训：加按钮必须同时定义 handler；build 通过≠交互可用。**
- **时间轴/看板/合成页的 ?ep 参数都是集号**，必须按集号在本项目内匹配 —— 禁止把 query 值直接当集 id。

# D. 09-16 晚 镜头详情页 / 前端细则（收口）

## D1 首帧与「传给视频」
- 分镜图候选悬停「传给视频」＝采纳为**视频参考图第 1 张（首帧）**：写 `shot_asset_links`(video, slot 0) + `shot_frames.first`。
- **视频参考图区必须包含 slot 0**，不许再过滤（前端 `videoRefsRest` 已删）。槽位角标 **1-based**（`slot_index+1`），对齐提示词里「参考图N / Image N」的 `loop.index`。
- 首帧瓦片（video 侧 slot 0）**只读**：只留「用途」，不显示「换 / 删」；幽灵引用列表里它也不给「删掉」——改首帧的入口在「换首帧」（D9），否则会与 `shot_frames.first` 失步。

## D2 首帧手动上传（三条路之一）
`POST /api/shots/{id}/first-frame/upload`（multipart 单文件，仅图片后缀、非空、校验镜头存在）→ `hooks_service.save_uploaded_first_frame(shot_id, filename, content)`：存进项目 `keyframe_dir`、source=`uploaded`、同时写 slot 0。
前端入口＝视频参考图标题行的「换首帧」链接 / 第 1 张瓦片悬停的「换首帧」按钮（D9 弹窗内的「从本地上传一张图」）+ `pickFirstFrameLocal()`；api `uploadFirstFrame(sid, formData)` / `mediaUpload()`。
**改首帧只有三条路**：①自己上传（换首帧弹窗）②采纳分镜图（分镜图候选「传给视频」）③选上一镜/项目尾帧（换首帧弹窗）。

## D3 首帧来源判定
读 `shot_frames.first.source`：`storyboard`＝采纳的分镜图 / `tail_frame`＝上一镜尾帧 / `uploaded`＝手动上传。
**禁止读 `shot_asset_links.ref_version`**——概念稿/渲染帧它只区分这个，上述三者都写 `render_frame`，区分不了。
没有记录的老数据回退按 `*_tail` 命名猜，且文案必须带「（按文件名推断）」。「尾帧」角标同理只认 `*_tail.*` 命名。
**新增 source 值前先看 `schema.sql` 里 `shot_frames.source` 注释枚举（`generated / tail_frame / uploaded / storyboard`），别自造 `manual_upload` 这类名字。**

## D4 视频三个参数
`duration` / `resolution` / `seed` 都真进请求体模板（模型 8 body），前端各带标签（时长(秒)/分辨率/seed(可空)）。
`seed` 是裸插值 `"seed": {{ seed }}`，**必须整数**（填字母＝非法 JSON 报错），前端用 `el-input-number` 限定；留空则 `resolution` 落项目默认、`seed` 整条不传。

## D5 字号与操作列
- **字号铁律**：只允许 `--fs-mini/sm/base/lg/xl`，**禁止 .vue 里写死 px**；4 档 `html[data-fs]` 13/15/**16.5(默认)**/18px；EP 侧同步 `--el-font-size-*` 与 `--el-component-size-*`；`--el-font-size-extra-small` 要指次要文本档（被 `.el-table--small` 用）。
- **操作列**：全站表格加 `class-name/label-class-name="op-col"` 后 CSS 居中；`.op-row .el-button.is-text{color:var(--brand)}` 染蓝。
- `.op-row` 是 `nowrap`，**列宽不够时右侧按钮被静默裁掉**（不报错不换行）。加/改按钮后跑 `node tools/check_opcol.cjs`（估算四档字号所需宽 vs 实际列宽），必须 `ALL_FIT`。当前：项目列表 `width=340`（6 按钮，xlarge 需 330）。

## D6 UI 外壳（仿 `D:\python project\dispensing-new`）
- 左深色侧栏 `#304156`（可折叠 64px，`localStorage['studio.sidebar']`）+ 白顶栏（折叠键 + 面包屑；右 RunningTasks/字号/刷新）+ 内容区 `#f0f2f5` padding 16px。
- **侧栏极简**：单 `el-menu` 3 项（项目列表/任务中心/接口与设置），无分组标题、无项目切换、无「当前项目」组；**项目级页面全部从「项目列表」行操作列进**。
- **面包屑唯一来源＝路由 `meta.title`**；App.vue 的 `TITLES` 已删。**新增路由必须写 meta.title**。
- 骨架类 `.table-wrapper/.card/.page-card/.search-form` 视觉一致（白底 4px 圆角 p16）；内部 `.table-header`（`.table-title` + `.table-tip` + `.spacer` + 右侧按钮）、`.pagination-wrapper`；表格统一 `border stripe`；配色对齐 EP（#409eff/#67c23a/#e6a23c/#f56c6c，border #dcdfe6，text #303133 / dim #909399）。

## D7 09-16 注销与简化
- 注销：创作流水线 `/create`、健康报告 `/health`、提示词中心 `/prompts`、项目列表「导入文档」。注销前查证：提示词中心里**只有 Lint 规则真在跑**（默认全开，界面开关没了规则仍生效）、模板仅内置 `video_prefix` 被读、**常用片段全代码库无消费者**、版本回溯与详情页重复。**页面文件留在磁盘可恢复**，api 方法与后端接口均保留。
- 「时间轴与合成」→ 简化为 **「合成」页**：只留 集选择器 + 节拍条 +「自动建轴(补缺)/按镜序重建/合成前体检/合成整集」+ 片段表（序/镜号/文件/时长/状态/预览）；去掉入点/出点/转场/启用/调序/转8bit/删段（**后端 timeline.py 与 api 方法全保留**）。它是**唯一的整集成片入口**（看板「合成」跳这里）。
- 项目列表操作列最终＝**分集 / 剧本 / 资产库 / 合成 / 编辑 / 删除**（宽 **340**，300 时「删除」被裁）。

## D8 记忆文件写入方式（绿盾）
本目录的 md **只能「删除旧文件 + 一次性新建写入」**（Python 或宿主 Write 新建均可）。宿主 Edit 追加＝"修改"→ 被绿盾加密 → 此后宿主 Read 与自动注入只能读到乱码（Python/Bash 仍能读明文）。写完必须用宿主 `Read` 回读验证。

## D9 首帧入口收口为「换首帧」弹窗（09-17）
- **删掉了整块 `.anchor`「首帧锚点」卡片**（当前/来源/上一镜提示 + 取尾帧下拉 + 上传按钮）——用户嫌占地大且换尾帧本来就该点图操作。
- 现在的入口共 3 个，都通向同一个弹窗 `ffDialog`（`fi`：`openFfDialog()`）：
  1. 视频参考图标题行右侧小字后面的「换首帧」文字链接（**兜底入口，永远可见**）；
  2. 视频参考图第 1 张瓦片悬停 → 「换首帧」按钮；
  3. 幽灵引用列表里首帧那一行提示「首帧：点上方『换首帧』重选」。
- 弹窗内容：当前首帧（文件名 + 来源）→「从本地上传一张图」→ 按组列「上一镜尾帧 / 项目全部尾帧」缩略图（点图即设为首帧）。
  数据来自 `GET /prev-tail-candidates`（`tailInfo.{current,prev,candidates,all_tails}`），设置走 `api.usePrevTail(sid,{path,prev_shot_code})`。
- **标题行状态**：`首帧：0114d.jpg（采纳的分镜图）`；文件解析不到时追加红字「⚠ 文件找不到，出片会被拦下」。没设置时显示「未设置（不设则取参考图第 1 张）」。
- `RefSlots.vue` 新增具名插槽 **`#first-ops`**（只在 `isFirstFrame(r)` 分支渲染，默认空），父组件往里塞「换首帧」按钮 —— 首帧瓦片仍然不给「换 / 删」，避免与 `shot_frames.first` 失步。
- CSS：删 `.anchor/.anchor-head/.anchor-cur`，新增 `.ff-head`（标题 + 状态同一行）、`.ff-group`。


## 2026-09-21 · 14d「五次调整」改回有嘴 + 14a-1 误写事故修复

### 14d v4 取证 → 放弃 OS
- 用户重出 0114d_4.mp4 仍乱语；抽帧＋本地 whisper ASR＋语种扫＋initial_prompt 偏置重打分＋变速率扫描四道闸全过：**OS 在画面内无有脸角色时仍乱语**（0114d.jpg 首帧里魅影头部纯黑零五官，OS 无处挂靠）。OS 唯一有效前提=画面内另有有脸角色（镜头5林岚、12b 过客先例）。
- 用户拍板（五次调整）：**放弃 OS，恢复给魅影一张 human-like 嘴**，本人开口、唇部动作与 ref_audio 同步（口型同步锚点）；形态维持雾态人形+紫瞳。**参考图用户自己重出带嘴版，AI 不调图。**

### 14a-1 误写事故与修复
- 首个 apply 脚本用全局 `t.find("**API prompt…")` 定位，命中排在前面的 14a-1 表头，把 14a-1 的块误写成 14d 的 NEW_BLOCK（md 污染；DB 未受影响：14a-1 vp 957 字符完好、14d vp 已是有嘴版）。
- restore_and_fix.py（第一次）断言写错范围：统计整个 `## 镜头14d→17` 区段的 `画外音(OS)` 数（WF/FM 注释合法含历史字样）→ 误报 3 → 在写盘前抛异常中断，md 未写。
- **fix_md_mouth_v3.py 修复成功**：锚定 `## 镜头XX` 标题 + 块内 H→`\n\n**API参数：**` 定位；14a-1 用 DB 原文还原、14d 换 DB 中的有嘴 NEW_BLOCK；断言只查块本身（14d 零 OS/有「魅影开口念出」、14a-1 零签名且==DB 原文）；写盘+同进程回读通过。DB 四字段核对：vp==md 块、hc 18 条含口型×2 零画外音、summary/beats 均有嘴版。
- 备份：`md_before_fix3_20260921.md`（修复前污染态）。
- **教训固化**：①块定位必须锚标题，严禁全局 find 字符串；②断言范围必须等于改动范围，历史注释里的合法词别算进去；③一次只信同进程回读。

### 垫图加嘴方案（用户自己出图，已给建议）
- 用现 `权限魅影_角色参考图.jpg`（无嘴雾态剪影设定图）垫图加嘴：可行。要点：指令式编辑（Qwen-Image-Edit 类）优于高 denoise 重绘（0.35–0.5 起试）；嘴=雾面上一条微亮暗紫唇线、闭合或微张、无牙无舌，**不加鼻耳等新五官**；紫瞳/雾质感/长袍/排版全部锁定不变；格1 HALF BODY 与中央 MAIN FORM 两处脸都要改。
- 出图后文件名不变覆盖内容；**0114d.jpg 首帧分镜图也要重出**（首帧锚点当前是无嘴黑剪影），再重新生成视频验证乱语是否根除。
