# -*- coding: utf-8 -*-
"""收尾：归档本轮临时脚本 + 追加项目记忆 + 同步 D 盘。"""
import io
import os
import shutil
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

TOOLS = r"D:\Aicomfyui\短剧工作台\tools"
TRASH = os.path.join(TOOLS, "_trash_20260915_本轮改动")
os.makedirs(TRASH, exist_ok=True)

# 1) 归档临时脚本
moved = []
for n in ["_patch_llm.py", "_patch_main.py"]:
    s = os.path.join(TOOLS, n)
    if os.path.exists(s):
        d = os.path.join(TRASH, n)
        if os.path.exists(d):
            os.remove(d)
        shutil.move(s, d)
        moved.append(n)
print("归档临时脚本:", moved or "无")

# 2) 追加今日日志
LOG = r"C:\Users\Administrator\WorkBuddy\2026-08-27-16-21-46\.workbuddy\memory\2026-09-16.md"
entry = """
## 十、剧本链路打通：剧本 → 智能分集 → 资产图（2026-09-16 下午）

**用户对齐的链路**（原话说成「剧本-资产图-分集」，随即更正为 **剧本-分集-资产图**）：
新建项目 → ①写剧本（DeepSeek，可反复改）→ ②智能分集（DeepSeek）→ ③资产图（角色三视图/道具，gpt）
→ ④确认落库 → 各集拆镜 → 看板出图出片 → ⑤集数管理里再调 DeepSeek 续写新增集。

**四个决策点（用户拍板）**
1. 剧本存储 = **独立表关联项目**（不是项目级字段）→ 建 `scripts` 表，一项目多版本。
2. 剧本入口 = 「能输入后调 DeepSeek 生成」→ 页内第一块就是创作要求输入区。
3. 角色三视图 = **一次出一张三视图合成图**（GPT 一次调用上限 4 张参考图，合并出图省额度且三视图比例一致）。
4. 调用方式 = **走任务中心异步**（有进度/失败原因/可取消/可查历史）。
5. 入口位置（用户补充）= **放在项目的操作按钮里**（项目列表行「打开」旁边），不是左侧导航。

**现状盘点（动手前的缺口）**
- provider/model/密钥配置层早就配好了（`deepseek-script` category=llm mode=synchronous；`_LLM_BODY` 模板；response_spec.text = `$.choices[0].message.content`；model_settings.llm 已指向它），
  `provider_engine.execute()` 也支持文本返回（`ExecResult.text`）——**但此前没有任何接口真的发起过 LLM 调用，整条链是空的**。
- 资产图也只能「登记/上传已有文件」，没有「调 gpt 出图」接口（本轮未做，属批 B）。
- 「拆镜」是本地正则解析（`parse_script`），不是 AI。

**本轮做了（批 A）**
- `scripts` 表：project_id / version(同项目自增) / kind / title / content / source(ai|manual|import) / prompt_used / episode_id / meta。
  **最新版本 = 当前剧本**。schema.sql 一段「一之二、剧本」+ 索引 idx_scripts_project。
- 新任务类型 **`llm_generation`**（task_runner）：`_run` 加分支 + `_run_llm`；payload.save 决定落点
  → `"script"` 存新版本、`"episode"` 写回该集、缺省只把文本塞进任务结果（分集预览走这条）。
- 新服务 `services/script_service.py`：三种提示词构建（整部剧本 / 按意见重写 / 智能分集 / 单集续写）
  + 解析容错（`_json_block` 抠 JSON 容忍 ```json 包裹；退化到「第N集」正则切分；`_renumber` 去重保连续）
  + 落库助手（`save_script` / `apply_episodes`：同集号更新、新集号插入、多余的不动）。
- 新路由 `routers/scripts.py`（12 个接口）：版本列表含 latest 全文、单版本、删除（至少留一版）、
  generate / revise / save / preview(dry-run) / split / parse-episodes / apply-episodes / continue-episode / preview-episode。
  **分集必须人工确认才落库**（split 不写库，apply 才写）。
- 前端新页 `views/Script.vue`（两块：① 剧本 ② 分集与集数管理）+ 路由 `/p/:pid/script`
  + Projects.vue 操作列加「剧本」按钮（列宽 330→380）+ api/index.js 12 个方法。
- 构建通过（vite build exit=0，12.74s）；后端重启后 `scripts` 表已建、`/api/projects/1/scripts` 返回正常。

**⚠️ 遗留：DeepSeek 的 key 还没配**
providers 表里 deepseek(id=3) enabled、base_url 正确，`model_settings.llm=5`，但
**`provider_credentials` 密钥池为空、settings 表也没有 `provider_key:deepseek`** → 现在点「调用 DeepSeek 生成」会 401。
需到「接口与设置」页把 key 填进 DeepSeek 的密钥池（key 见腾讯文档『相关平台和账密』：sk-abaa…0393）。

**批 B（待做）**：资产图出图接口 `POST /assets/{id}/generate-image`（一次一张三视图合成图）+ Assets.vue 出图按钮。
"""
with open(LOG, "a", encoding="utf-8") as f:
    f.write(entry)
print("今日日志已追加，大小", os.path.getsize(LOG))

# 3) 同步 D 盘
DST = r"D:\Aicomfyui\项目记忆与日志"
os.makedirs(DST, exist_ok=True)
n = 0
for f in sorted(os.listdir(os.path.dirname(LOG))):
    if f.endswith(".md"):
        shutil.copy2(os.path.join(os.path.dirname(LOG), f), os.path.join(DST, f))
        n += 1
print("已同步 %d 个 md 到 D 盘（源保留）" % n)
src_size = os.path.getsize(LOG)
dst_size = os.path.getsize(os.path.join(DST, os.path.basename(LOG)))
print("2026-09-16.md 源%d 目标%d %s" % (src_size, dst_size, "OK" if src_size == dst_size else "!! 不一致"))
