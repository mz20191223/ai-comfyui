-- ============================================================
-- 短剧生产工作台 · 数据库 Schema
-- 设计原则：
--   1) 状态只有一条轨：generation_tasks.status（就绪态整轨已于 2026-09-16 废弃）
--   2) 一切可配置：资产/模板/规则/供应商/模型 均不写死任何一部剧
--   3) 文件即真相：md 与素材目录是唯一事实源，本库只做索引与状态
-- ============================================================

PRAGMA foreign_keys = ON;

-- ============================================================
-- 一、项目层
-- ============================================================

CREATE TABLE IF NOT EXISTS projects (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  name            TEXT NOT NULL,
  code            TEXT UNIQUE,
  kind            TEXT DEFAULT 'micro_drama',   -- micro_drama / short_film / ad ...
  visual_style    TEXT DEFAULT 'live_action',   -- live_action(写实) / anime(动漫) / 3d
  genre           TEXT,                          -- 题材：软科幻/神话/悬疑...
  logline         TEXT,                          -- 一句话故事
  aspect_ratio    TEXT DEFAULT '9:16',
  fps             INTEGER DEFAULT 24,
  resolution      TEXT DEFAULT '768x1344',
  bit_depth       TEXT DEFAULT '8bit',
  codec           TEXT DEFAULT 'h264+aac',
  workspace_dir   TEXT,                          -- 素材根目录（绝对路径，不搬家）
  doc_dir         TEXT,                          -- 分镜 md 文档目录
  ref_dir         TEXT,                          -- 角色/场景参考图目录
  keyframe_dir    TEXT,                          -- 分镜图目录
  video_dir       TEXT,                          -- 视频目录
  tail_dir        TEXT,                          -- 视频尾帧目录
  audio_dir       TEXT,                          -- 音频目录
  discard_dir     TEXT,                          -- 废弃产物目录（不要的出图/出片移到这里）
  archived        INTEGER DEFAULT 0,
  meta            TEXT,                          -- JSON 扩展
  created_at      TEXT DEFAULT (datetime('now','localtime')),
  updated_at      TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS episodes (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id          INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  number              INTEGER NOT NULL,
  title               TEXT,
  synopsis            TEXT,
  script_text         TEXT,                      -- 剧本原文（供创作层与拆解参考）
  video_doc_path      TEXT,                      -- 核对版 md 绝对路径
  storyboard_doc_path TEXT,                      -- 分镜图 md 绝对路径
  status              TEXT DEFAULT 'draft',      -- draft/producing/locked/done
  sort_order          INTEGER DEFAULT 0,
  meta                TEXT,
  created_at          TEXT DEFAULT (datetime('now','localtime')),
  updated_at          TEXT DEFAULT (datetime('now','localtime')),
  UNIQUE(project_id, number)
);

-- ============================================================
-- 一之二、剧本（项目级独立表 + 多版本）
--   链路：写剧本（DeepSeek）→ 智能分集（DeepSeek）→ 资产图（gpt）
--   version 同项目内自增；**最新版本即「当前剧本」**
-- ============================================================

CREATE TABLE IF NOT EXISTS scripts (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id    INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  version       INTEGER NOT NULL DEFAULT 1,   -- 同项目内递增
  kind          TEXT DEFAULT 'script',        -- script(整部剧本) / episode(单集) / outline(分集大纲)
  title         TEXT,
  content       TEXT,                          -- 正文
  source        TEXT DEFAULT 'manual',         -- ai(模型生成) / manual(人工保存) / import(导入)
  prompt_used   TEXT,                          -- 生成时用的创作要求（便于复现与继续迭代）
  episode_id    INTEGER,                       -- kind=episode 时指向的集
  meta          TEXT,                          -- JSON：模型名/字数等
  created_at    TEXT DEFAULT (datetime('now','localtime')),
  updated_at    TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_scripts_project ON scripts(project_id, version DESC);

-- ============================================================
-- 二、资产库（角色 / 场景 / 道具 / 服装）——参考图槽位由此派生
-- ============================================================

CREATE TABLE IF NOT EXISTS assets (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id    INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  asset_type    TEXT NOT NULL,                 -- character / scene / prop / costume / style
  name          TEXT NOT NULL,                 -- 通用名，如「过客」「权限魅影」
  alias         TEXT,                          -- JSON 数组：别名/代号，导入时用于匹配
  description   TEXT,
  lock_sentence TEXT,                          -- 锁定句（进提示词的固定句）
  voice_id      TEXT,                          -- TTS 音色（角色用）
  voice_params  TEXT,                          -- JSON：语速/音调
  quality_level TEXT DEFAULT 'MEDIUM',         -- LOW/MEDIUM/HIGH/ULTRA（参考图完善度）
  default_ratio TEXT,
  sort_order    INTEGER DEFAULT 0,
  meta          TEXT,
  created_at    TEXT DEFAULT (datetime('now','localtime')),
  updated_at    TEXT DEFAULT (datetime('now','localtime')),
  UNIQUE(project_id, asset_type, name)
);

CREATE TABLE IF NOT EXISTS asset_images (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  asset_id      INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
  usage_kind    TEXT DEFAULT 'reference',      -- reference / lockup(定妆) / tail_frame(真实渲染帧) / variant
  view_angle    TEXT,                          -- FRONT/LEFT/RIGHT/BACK/THREE_QUARTER/TOP/DETAIL
  file_path     TEXT NOT NULL,                 -- 相对素材根的路径或绝对路径
  file_name     TEXT,                          -- 文件名（提示词里写的就是它）
  is_primary    INTEGER DEFAULT 0,             -- 是否主参考图
  take_note     TEXT,                          -- 「取什么/不取什么」的取用说明
  width         INTEGER, height INTEGER, format TEXT, size_bytes INTEGER,
  sort_order    INTEGER DEFAULT 0,
  meta          TEXT,
  created_at    TEXT DEFAULT (datetime('now','localtime')),
  UNIQUE(asset_id, file_name, usage_kind)
);

-- ============================================================
-- 三、镜头（主表稳定 + 明细表高频变动）
-- ============================================================

CREATE TABLE IF NOT EXISTS shots (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  episode_id      INTEGER NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
  shot_code       TEXT NOT NULL,               -- 镜号 14d / 6a / 14b-1
  title           TEXT,
  sort_order      INTEGER DEFAULT 0,
  skip_extraction INTEGER DEFAULT 0,
  last_extracted_at TEXT,
  script_excerpt  TEXT,                        -- 剧本摘录
  thumbnail_path  TEXT,
  final_video_path TEXT,                       -- 成片（采纳的那条）
  notes           TEXT,                        -- 备注（工作流注释等非提示词内容）
  meta            TEXT,
  created_at      TEXT DEFAULT (datetime('now','localtime')),
  updated_at      TEXT DEFAULT (datetime('now','localtime')),
  UNIQUE(episode_id, shot_code)
);
CREATE INDEX IF NOT EXISTS idx_shots_ep ON shots(episode_id, sort_order);

CREATE TABLE IF NOT EXISTS shot_details (
  shot_id             INTEGER PRIMARY KEY REFERENCES shots(id) ON DELETE CASCADE,
  -- 镜头语言（枚举，供设置向导）
  camera_shot         TEXT,                    -- ECU/CU/MCU/MS/MLS/LS/ELS
  angle               TEXT,                    -- EYE_LEVEL/HIGH_ANGLE/LOW_ANGLE/BIRD_EYE/DUTCH/OVER_SHOULDER
  movement            TEXT,                    -- STATIC/PAN/TILT/DOLLY_IN/DOLLY_OUT/TRACK/CRANE/HANDHELD/STEADICAM/ZOOM_IN/ZOOM_OUT
  subject_position    TEXT,                    -- 主体在画面中的位置描述
  camera_note         TEXT,                    -- 机位自由描述（中文）
  -- 设置向导注入提示词的记账：存「上一次注入进去的原文」，改动时按原文替换，避免重复堆叠
  wiz_image_note      TEXT,                    -- 上次注入分镜图提示词的构图句
  wiz_video_note      TEXT,                    -- 上次注入视频提示词的机位+运镜句
  -- 时长：唯一事实源
  duration_sec        REAL,
  duration_note       TEXT,
  -- 生成模式
  gen_mode            TEXT,                    -- FL2VA / I2VA / REF2VA / T2V / I2V
  api_style           TEXT,                    -- 接口A多图 / 接口B首尾帧
  resolution          TEXT,                    -- 768p竖 ...
  override_ratio      TEXT,                    -- 空=继承项目默认
  seed                TEXT,
  -- 内容
  summary             TEXT,                    -- 画面主体段
  assets_text         TEXT,                    -- 本镜出场资产中文名（创作期记录，不卡资产库）
  action_beats        TEXT,                    -- JSON 数组：[{start,end,text}]
  hard_constraints    TEXT,                    -- JSON 数组（编号条目）
  mood_tags           TEXT,                    -- JSON 数组
  vfx_note            TEXT,
  audio_note          TEXT,                    -- 音频块原文
  post_audio_note     TEXT,                    -- 后期音轨块原文
  -- 提示词
  video_prompt        TEXT,                    -- 给视频模型的完整 prompt 正文
  video_prompt_prefix TEXT,                    -- 接口A首行（I2VA/FL2VA 模式声明）
  image_prompt        TEXT,                    -- 分镜图提示词（GPT-Img2）
  image_negative      TEXT,
  image_target_name   TEXT,                    -- 分镜图目标文件名 0114c.jpg
  image_refs_note     TEXT,                    -- 分镜图侧「上传参考图」清单原文
  image_is_optional   INTEGER DEFAULT 0,       -- 该镜是否默认不出分镜图（14d 备选）
  video_template_id   INTEGER,                 -- 关联模板
  image_template_id   INTEGER,
  created_at          TEXT DEFAULT (datetime('now','localtime')),
  updated_at          TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS shot_frames (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  shot_id         INTEGER NOT NULL REFERENCES shots(id) ON DELETE CASCADE,
  frame_type      TEXT NOT NULL,               -- first / last / key
  file_path       TEXT NOT NULL,
  file_name       TEXT,
  source          TEXT DEFAULT 'generated',    -- generated / tail_frame / uploaded / storyboard
  width INTEGER, height INTEGER, format TEXT, size_bytes INTEGER,
  is_active       INTEGER DEFAULT 1,
  note            TEXT,
  created_at      TEXT DEFAULT (datetime('now','localtime')),
  UNIQUE(shot_id, frame_type)
);

-- 镜头 ↔ 资产 引用：参考图槽位、提示词「参考图N」全部由此派生
CREATE TABLE IF NOT EXISTS shot_asset_links (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  shot_id       INTEGER NOT NULL REFERENCES shots(id) ON DELETE CASCADE,
  asset_id      INTEGER REFERENCES assets(id) ON DELETE SET NULL,
  asset_image_id INTEGER REFERENCES asset_images(id) ON DELETE SET NULL,
  role          TEXT,                          -- 形态锚点 / 仅取色调 / 构图锚点 / 首帧 ...
  slot_index    INTEGER,                       -- 在参考图列表中的序号（1 基，槽位）
  target_side   TEXT DEFAULT 'both',           -- image(分镜图侧) / video(视频侧) / both
  ref_version   TEXT,                          -- 引用的是概念稿还是真实渲染帧：concept / render_frame
  take_note     TEXT,                          -- 「取什么/不取什么」
  file_name     TEXT,                          -- 直接写死的文件名（无资产时）
  raw_text      TEXT,                          -- 原始声明行文本
  created_at    TEXT DEFAULT (datetime('now','localtime')),
  UNIQUE(shot_id, target_side, slot_index)
);

CREATE TABLE IF NOT EXISTS shot_dialog_lines (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  shot_id       INTEGER NOT NULL REFERENCES shots(id) ON DELETE CASCADE,
  line_index    INTEGER DEFAULT 1,
  role_name     TEXT,                          -- 角色名（对应 assets.name）
  asset_id      INTEGER REFERENCES assets(id) ON DELETE SET NULL,
  text          TEXT,                          -- 台词
  line_mode     TEXT DEFAULT 'dialogue',       -- dialogue / voiceover / offscreen / phone / sfx
  tone          TEXT,                          -- 语气
  audio_file    TEXT,                          -- ref_audio_0 文件名
  audio_measured_sec REAL,                     -- mutagen 实测时长
  start_sec     REAL,                          -- 台词时间窗起点
  end_sec       REAL,
  created_at    TEXT DEFAULT (datetime('now','localtime'))
);

-- ============================================================
-- 四、提示词资产：模板（Jinja2）+ 片段 + 版本历史
-- ============================================================

CREATE TABLE IF NOT EXISTS prompt_templates (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id    INTEGER REFERENCES projects(id) ON DELETE CASCADE,  -- NULL = 全局
  category      TEXT NOT NULL,                 -- keyframe_image / video_i2va / video_fl2va / video_ref2va / video_prefix / negative_base / tts_script
  name          TEXT NOT NULL,
  description   TEXT,
  content       TEXT NOT NULL,                 -- Jinja2 模板
  variables     TEXT,                          -- JSON 数组：[{name,label,type,default,required}]
  preview       TEXT,                          -- 预览样例
  is_system     INTEGER DEFAULT 0,
  is_default    INTEGER DEFAULT 0,
  sort_order    INTEGER DEFAULT 0,
  created_at    TEXT DEFAULT (datetime('now','localtime')),
  updated_at    TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS prompt_snippets (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id    INTEGER REFERENCES projects(id) ON DELETE CASCADE,
  key           TEXT NOT NULL,                 -- transition_guard / passenger_lock / white_model_ban
  label         TEXT NOT NULL,                 -- 中文短标签
  content       TEXT NOT NULL,
  category      TEXT DEFAULT 'guard',          -- guard / lock / style / negative
  auto_apply    TEXT,                          -- JSON：自动套用条件（如 stage=video）
  sort_order    INTEGER DEFAULT 0,
  created_at    TEXT DEFAULT (datetime('now','localtime')),
  UNIQUE(project_id, key)
);

CREATE TABLE IF NOT EXISTS prompt_revisions (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  target_kind   TEXT NOT NULL,                 -- shot_video / shot_image / template / asset
  target_id     INTEGER NOT NULL,
  content       TEXT NOT NULL,
  note          TEXT,
  source        TEXT DEFAULT 'manual',         -- manual / import / lint_fix
  created_at    TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_rev_target ON prompt_revisions(target_kind, target_id);

-- ============================================================
-- 五、Lint 规则与结果
-- ============================================================

CREATE TABLE IF NOT EXISTS lint_rules (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id    INTEGER REFERENCES projects(id) ON DELETE CASCADE,
  key           TEXT NOT NULL,
  label         TEXT NOT NULL,
  description   TEXT,
  stage         TEXT DEFAULT 'video',          -- video / image / both
  severity      TEXT DEFAULT 'error',          -- error / warn / info
  checker       TEXT NOT NULL,                 -- 内置检查器名
  config        TEXT,                          -- JSON 参数（关键词表、阈值…）
  enabled       INTEGER DEFAULT 1,
  sort_order    INTEGER DEFAULT 0,
  created_at    TEXT DEFAULT (datetime('now','localtime')),
  UNIQUE(project_id, key)
);

CREATE TABLE IF NOT EXISTS lint_results (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  shot_id       INTEGER NOT NULL REFERENCES shots(id) ON DELETE CASCADE,
  stage         TEXT NOT NULL,
  rule_key      TEXT NOT NULL,
  severity      TEXT,
  message       TEXT,
  evidence      TEXT,
  created_at    TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_lint_shot ON lint_results(shot_id, stage);

-- ============================================================
-- 六、供应商与模型（不写死的核心：请求/响应全配置化）
-- ============================================================

CREATE TABLE IF NOT EXISTS providers (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  key               TEXT NOT NULL UNIQUE,      -- img-default / vid-oldplat
  name              TEXT NOT NULL,
  capabilities      TEXT,                      -- JSON：["image","video","llm"]（不做配音：音频是上传素材）
  base_url          TEXT,
  image_base_url    TEXT,                      -- 可选覆盖（按能力分网关）
  video_base_url    TEXT,
  api_key_ref       TEXT,                      -- ${ENV:XXX} 或引用 settings 表
  auth_header       TEXT DEFAULT 'Authorization',
  auth_scheme       TEXT DEFAULT 'Bearer',
  concurrency       INTEGER DEFAULT 2,
  timeout_sec       INTEGER DEFAULT 600,
  retry             INTEGER DEFAULT 1,
  proxy_mode        TEXT DEFAULT 'system',     -- system / direct / custom
  proxy_url         TEXT,
  enabled           INTEGER DEFAULT 1,
  meta              TEXT,
  created_at        TEXT DEFAULT (datetime('now','localtime')),
  updated_at        TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS models (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  provider_id       INTEGER NOT NULL REFERENCES providers(id) ON DELETE CASCADE,
  key               TEXT NOT NULL UNIQUE,
  name              TEXT NOT NULL,
  category          TEXT NOT NULL,             -- image / video / llm
  model_name        TEXT NOT NULL,             -- 请求体里的 model 字段
  remote_model_name TEXT,                      -- 中转站自定义远端名（为空用 model_name）
  mode              TEXT DEFAULT 'synchronous',-- synchronous / asynchronous / local
  request_kind      TEXT DEFAULT 'http',       -- http / local_command
  -- 以下三块均为 JSON 文本，见 provider_engine
  request_spec      TEXT,                      -- {method,path,headers,body(Jinja2),params_map}
  response_spec     TEXT,                      -- {images:[jsonpath],videos:[jsonpath],task_id,text}
  poll_spec         TEXT,                      -- {path,interval_sec,timeout_sec,status_field,success_values,fail_values,result_video,download_path}
  download_spec     TEXT,                      -- 结果下载方式
  defaults          TEXT,                      -- JSON 默认参数
  param_map         TEXT,                      -- JSON 语义值→字面值映射（768p竖→768P）
  enabled           INTEGER DEFAULT 1,
  notes             TEXT,
  created_at        TEXT DEFAULT (datetime('now','localtime')),
  updated_at        TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS model_settings (
  category      TEXT PRIMARY KEY,              -- image / video / llm
  model_id      INTEGER REFERENCES models(id) ON DELETE SET NULL,
  updated_at    TEXT DEFAULT (datetime('now','localtime'))
);

-- 密钥池：同一供应商可挂多个账号 key，额度用尽自动轮到下一个
CREATE TABLE IF NOT EXISTS provider_credentials (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  provider_id       INTEGER NOT NULL REFERENCES providers(id) ON DELETE CASCADE,
  alias             TEXT NOT NULL,             -- 账号别名：账号A / 主号 / 备用1
  api_key           TEXT NOT NULL,
  status            TEXT DEFAULT 'active',     -- active / cooling / exhausted / invalid / disabled
  cooldown_until    TEXT,                      -- 冷却到期时间（冷却中到点自动恢复）
  fail_count        INTEGER DEFAULT 0,
  last_used_at      TEXT,
  last_error        TEXT,
  balance           REAL,                      -- 最近一次额度查询结果
  balance_note      TEXT,                      -- 额度原文摘要
  balance_checked_at TEXT,
  probe_ok          INTEGER,                   -- 最近一次连通性探测是否通过
  probe_note        TEXT,
  enabled           INTEGER DEFAULT 1,
  sort_order        INTEGER DEFAULT 0,
  created_at        TEXT DEFAULT (datetime('now','localtime')),
  updated_at        TEXT DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_cred_provider ON provider_credentials(provider_id, enabled, status);

-- ============================================================
-- 七、任务中心（图/视频/文本/音频共用）
-- ============================================================

CREATE TABLE IF NOT EXISTS generation_tasks (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  task_kind       TEXT NOT NULL,               -- image_generation / video_generation / lint / compose / extract_frame / normalize_8bit
  mode            TEXT DEFAULT 'async_polling',-- synchronous / async_polling / local
  status          TEXT DEFAULT 'submitted',    -- submitted/running/succeeded/failed/cancelled
  fail_kind       TEXT,                        -- 失败原因：rate_limit/insufficient_balance/auth/api_error/interrupted
  fail_message    TEXT,                        -- 失败原因的人话描述
  progress        INTEGER DEFAULT 0,
  priority        INTEGER DEFAULT 0,
  provider_id     INTEGER REFERENCES providers(id) ON DELETE SET NULL,
  model_id        INTEGER REFERENCES models(id) ON DELETE SET NULL,
  credential_id   INTEGER,                     -- 本次实际使用的密钥池账号（便于对账）
  credential_alias TEXT,
  payload         TEXT,                        -- JSON 请求参数快照（可原样复现）
  result          TEXT,                        -- JSON 结果
  error           TEXT,
  executor_task_id TEXT,                       -- 远端任务 id
  cancel_requested INTEGER DEFAULT 0,
  cancel_requested_at TEXT,
  cancel_reason   TEXT,
  attempts        INTEGER DEFAULT 0,
  max_attempts    INTEGER DEFAULT 1,
  queued_at       TEXT DEFAULT (datetime('now','localtime')),
  started_at      TEXT,
  finished_at     TEXT,
  updated_at      TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_task_status ON generation_tasks(status, updated_at);
CREATE INDEX IF NOT EXISTS idx_task_kind ON generation_tasks(task_kind, status);

CREATE TABLE IF NOT EXISTS task_links (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id       INTEGER NOT NULL REFERENCES generation_tasks(id) ON DELETE CASCADE,
  target_kind   TEXT NOT NULL,                 -- shot / asset / asset_image / timeline / episode
  target_id     INTEGER NOT NULL,
  role          TEXT,                          -- 该任务产出什么：keyframe / video / first_frame / audio / tail_frame
  created_at    TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_tasklink_target ON task_links(target_kind, target_id);

-- ============================================================
-- 八、文件登记
-- ============================================================

CREATE TABLE IF NOT EXISTS files (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  path          TEXT NOT NULL UNIQUE,          -- 绝对路径
  file_name     TEXT,
  ext           TEXT,
  file_type     TEXT,                          -- image / video / audio / doc / other
  size_bytes    INTEGER,
  width INTEGER, height INTEGER, duration_sec REAL,
  sha1          TEXT,
  exists_flag   INTEGER DEFAULT 1,
  indexed_at    TEXT DEFAULT (datetime('now','localtime')),
  last_seen_at  TEXT
);

CREATE TABLE IF NOT EXISTS file_usages (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  file_id       INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
  usage_kind    TEXT NOT NULL,                 -- shot_first_frame / shot_last_frame / shot_video / asset_ref / audio_ref / scene_ref / storyboard / tail_frame
  target_kind   TEXT, target_id INTEGER,
  note          TEXT,
  created_at    TEXT DEFAULT (datetime('now','localtime'))
);

-- ============================================================
-- 九、时间轴与合成
-- ============================================================

CREATE TABLE IF NOT EXISTS timeline_clips (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  episode_id    INTEGER NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
  track_type    TEXT DEFAULT 'video',          -- video / audio / subtitle
  shot_id       INTEGER REFERENCES shots(id) ON DELETE SET NULL,
  file_path     TEXT,
  sort_order    INTEGER DEFAULT 0,
  in_sec        REAL, out_sec REAL,
  timeline_start REAL, timeline_end REAL,
  transition    TEXT,                          -- cut / fade ...
  enabled       INTEGER DEFAULT 1,
  note          TEXT,
  created_at    TEXT DEFAULT (datetime('now','localtime'))
);

-- ============================================================
-- 十、创作层（下部剧从 0 可用）
-- ============================================================

CREATE TABLE IF NOT EXISTS creative_ideas (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id    INTEGER REFERENCES projects(id) ON DELETE CASCADE,
  title         TEXT,
  one_liner     TEXT,                          -- 一句话灵感
  story_text    TEXT,                          -- 扩写故事
  beats         TEXT,                          -- JSON：故事节拍
  characters_json TEXT,                        -- JSON：抽出的角色设定
  scenes_json   TEXT,
  status        TEXT DEFAULT 'idea',           -- idea/story/beats/characters/done
  created_at    TEXT DEFAULT (datetime('now','localtime')),
  updated_at    TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS settings (
  key           TEXT PRIMARY KEY,
  value         TEXT,
  category      TEXT DEFAULT 'general',
  updated_at    TEXT DEFAULT (datetime('now','localtime'))
);

-- ============================================================
-- 十一、健康报告（导入期与巡检期产出）
-- ============================================================

CREATE TABLE IF NOT EXISTS health_issues (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id    INTEGER REFERENCES projects(id) ON DELETE CASCADE,
  episode_id    INTEGER,
  shot_id       INTEGER,
  issue_type    TEXT NOT NULL,                 -- missing_suffix / ghost_ref / deprecated / missing_file / duration_short / no_audio ...
  severity      TEXT DEFAULT 'warn',
  target        TEXT,
  message       TEXT,
  suggestion    TEXT,
  resolved      INTEGER DEFAULT 0,
  created_at    TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_health_proj ON health_issues(project_id, resolved);
