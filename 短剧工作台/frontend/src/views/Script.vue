<template>
  <div>
    <!-- ============ ① 剧本 ============ -->
    <div class="card">
      <h3>
        <span>剧本</span>
        <span class="spacer"></span>
        <span class="tiny muted" v-if="latest">
          当前第 {{ latest.version }} 版 · {{ latest.chars }} 字
          <template v-if="latest.created_at"> · {{ latest.created_at }}</template>
        </span>
        <el-button size="small" text :disabled="!versions.length" @click="showHistory = true">
          版本历史（{{ versions.length }}）
        </el-button>
      </h3>

      <el-input
        v-model="form.requirement"
        type="textarea"
        :rows="2"
        placeholder="写下创作要求，例如：3 集竖屏微短剧，软科幻，讲一个程序员加班到凌晨两点，发现 Bug 成精了…"
      />

      <div class="req-row">
        <span class="tiny muted">可选参数</span>
        <el-input-number v-model="form.episodes" :min="1" :max="120" size="small"
          controls-position="right" style="width: 96px" placeholder="集数" />
        <span class="tiny muted">集</span>
        <el-input-number v-model="form.minutes_per_episode" :min="0.5" :max="20" :step="0.5" size="small"
          controls-position="right" style="width: 110px" placeholder="时长" />
        <span class="tiny muted">分钟/集</span>
        <el-select v-model="form.genre" size="small" style="width: 152px" placeholder="题材"
          filterable allow-create default-first-option clearable>
          <el-option v-for="g in genreOptions(form.genre)" :key="g" :label="g" :value="g" />
        </el-select>
        <el-select v-model="form.visual_style" size="small" style="width: 118px">
          <el-option label="写实真人" value="live_action" />
          <el-option label="动漫" value="anime" />
          <el-option label="3D" value="3d" />
        </el-select>
        <span class="spacer"></span>
        <el-button size="small" :loading="busy.preview" @click="doPreview">预览提示词</el-button>
        <el-button size="small" :disabled="!hasContent" :loading="busy.revise" @click="showRevise = true">
          按意见重写
        </el-button>
        <el-button size="small" type="primary" :loading="busy.gen" @click="doGenerate">
          {{ latest ? '调用 DeepSeek 重新生成' : '调用 DeepSeek 生成' }}
        </el-button>
      </div>

      <div v-if="job" class="job">
        <el-progress :percentage="job.pct" :stroke-width="6"
          :status="job.state === 'success' ? 'success' : undefined" />
        <span class="tiny muted">{{ job.text }}</span>
      </div>

      <textarea
        v-model="content"
        class="script-edit"
        placeholder="剧本正文会出现在这里；也可以直接手写或粘贴，再点「保存为新版本」。"
      ></textarea>
      <div class="row mt8">
        <span class="tiny muted">{{ content.length }} 字</span>
        <span v-if="dirty" class="pill warn">有未保存的修改</span>
        <span class="spacer"></span>
        <el-button size="small" :disabled="!hasContent" :loading="busy.save" @click="doSave">
          保存为新版本
        </el-button>
      </div>
    </div>

    <!-- ============ ② 剧本确认后：一键生成分集并落库 → 看板 ============ -->
    <div class="card">
      <div class="row">
        <span class="tiny muted">剧本确认后点这里：AI 生成分集 + 镜头清单并落库，自动进「镜头看板」；集与镜头统一在看板管理。</span>
        <span class="spacer"></span>
        <el-button size="small" :loading="busy.previewOutline" @click="doPreviewOutline">预览提示词</el-button>
        <el-button size="small" type="primary" :disabled="!(form.requirement || hasContent)"
          :loading="busy.outlineApply" @click="doOutlineAndApply">
          生成并落库 → 看板
        </el-button>
      </div>
      <!-- 进度条：② 操作卡内也可见 -->
      <div v-if="job" class="job mt8">
        <el-progress :percentage="job.pct" :stroke-width="6"
          :status="job.state === 'success' ? 'success' : undefined" />
        <span class="tiny muted">{{ job.text }}</span>
      </div>
    </div>

    <!-- ============ 弹窗 ============ -->
    <el-dialog v-model="showHistory" title="剧本版本历史" width="760px" append-to-body>
      <el-table :data="versions" size="small" border stripe>
        <el-table-column label="版本" width="70"><template #default="{ row }">v{{ row.version }}</template></el-table-column>
        <el-table-column label="标题" width="170"><template #default="{ row }"><span class="tiny">{{ row.title || '—' }}</span></template></el-table-column>
        <el-table-column label="来源" width="96">
          <template #default="{ row }">
            <span class="pill" :class="row.source === 'ai' ? 'brand' : 'gray'">
              {{ row.source === 'ai' ? 'AI 生成' : '人工保存' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="字数" width="76" prop="chars" />
        <el-table-column label="时间" width="150"><template #default="{ row }"><span class="tiny muted">{{ row.created_at }}</span></template></el-table-column>
        <el-table-column class-name="op-col" label-class-name="op-col" label="操作" width="130">
          <template #default="{ row }">
            <el-button size="small" text @click="loadVersion(row)">载入</el-button>
            <el-button size="small" text type="danger" @click="removeVersion(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <el-dialog v-model="showRevise" title="按意见重写" width="580px" append-to-body>
      <el-input v-model="reviseText" type="textarea" :rows="5"
        placeholder="例如：把第 2 集结尾的钩子换成过客发现异常日志；整体再紧凑一些，对白更短。" />
      <div class="tiny muted mt8">会把当前正文和这条意见一起发给 DeepSeek，结果存成新版本（原版本保留）。</div>
      <template #footer>
        <el-button @click="showRevise = false">取消</el-button>
        <el-button type="primary" :loading="busy.revise" @click="doRevise">提交给 DeepSeek</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showPreview" title="提示词预览（未发送，不消耗额度）" width="800px" append-to-body>
      <div class="row mb8">
        <el-radio-group v-model="previewMode" size="small">
          <el-radio-button value="generate">生成会发的内容</el-radio-button>
          <el-radio-button value="revise" :disabled="!previewData?.revise">按意见重写</el-radio-button>
        </el-radio-group>
        <span class="spacer"></span>
        <span class="tiny muted">{{ previewChars }} 字 · {{ previewMsgs.length }} 条消息</span>
      </div>
      <pre class="preview">{{ previewText }}</pre>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api'
import { genreOptions } from '../constants'

const route = useRoute()
const router = useRouter()
const pid = Number(route.params.pid)

const project = ref(null)
const versions = ref([])
const latest = ref(null)
const content = ref('')

const form = ref({
  requirement: '',
  episodes: null,
  minutes_per_episode: null,
  genre: '',
  visual_style: '',
})

const busy = ref({
  gen: false, revise: false, save: false, preview: false,
  outlineApply: false, previewOutline: false,
})
const job = ref(null)
const showHistory = ref(false)
const showRevise = ref(false)
const showPreview = ref(false)
const reviseText = ref('')
const previewData = ref(null)
const previewMode = ref('generate')

/** 预览内容：generate = 「调用 DeepSeek 生成」会发的；revise = 「按意见重写」会发的 */
const previewPack = computed(() => {
  const d = previewData.value
  if (!d) return null
  return (previewMode.value === 'revise' ? d.revise : d.generate) || d.generate
})
const previewMsgs = computed(() => previewPack.value?.messages || [])
const previewChars = computed(() => previewPack.value?.chars || 0)
const previewText = computed(() =>
  previewMsgs.value.map((m) => `【${m.role}】\n${m.content}`).join('\n\n────────────────\n\n'),
)

let disposed = false
const savedContent = ref('')

const hasContent = computed(() => !!content.value.trim())
const dirty = computed(() => hasContent.value && content.value !== savedContent.value)

function err(e) {
  if (!e?.response) ElMessage.error(e?.message || '操作失败')
}

async function load() {
  const [p, s] = await Promise.all([api.project(pid), api.scripts(pid)])
  project.value = p
  versions.value = s.items || []
  latest.value = s.latest || null
  if (!form.value.genre) form.value.genre = p.genre || ''
  if (!form.value.visual_style) form.value.visual_style = p.visual_style || 'live_action'
}

/** 生成完成后刷新版本列表，并把正文切到最新版本（同时更新「已保存」基线） */
async function reloadScript(keepEditor = false) {
  const s = await api.scripts(pid)
  versions.value = s.items || []
  latest.value = s.latest || null
  if (!keepEditor) {
    content.value = latest.value?.content || ''
    savedContent.value = content.value
  }
}

function reqPayload() {
  return {
    requirement: form.value.requirement || '',
    episodes: form.value.episodes || null,
    minutes_per_episode: form.value.minutes_per_episode || null,
    genre: form.value.genre || null,
    visual_style: form.value.visual_style || null,
  }
}

/** 轮询任务到终态；返回任务结果对象 */
function waitTask(tid, label) {
  return new Promise((resolve, reject) => {
    job.value = { pct: 0, text: label + '…', state: null }
    const tick = async () => {
      if (disposed) return
      let t
      try {
        t = await api.task(tid)
      } catch (e) {
        job.value = null
        return reject(e)
      }
      const note = (t.result_json && t.result_json.note) || ''
      job.value = { pct: Number(t.progress || 0), text: note || label + '…', state: null }
      if (t.status === 'succeeded') {
        job.value = { pct: 100, text: '完成', state: 'success' }
        setTimeout(() => { if (!disposed) job.value = null }, 1500)
        return resolve(t.result_json || {})
      }
      if (t.status === 'failed') {
        job.value = null
        return reject(new Error((t.fail_message || '生成失败') + (t.error ? '：' + t.error : '')))
      }
      if (t.status === 'cancelled') {
        job.value = null
        return reject(new Error('任务已取消'))
      }
      setTimeout(tick, 2000)
    }
    tick()
  })
}

async function withBusy(key, fn) {
  busy.value[key] = true
  try {
    return await fn()
  } catch (e) {
    err(e)
  } finally {
    busy.value[key] = false
  }
}

// ---------------- ① 剧本 ----------------
async function doGenerate() {
  await withBusy('gen', async () => {
    const r = await api.generateScript(pid, reqPayload())
    const res = await waitTask(r.task_id, 'DeepSeek 正在写剧本')
    await reloadScript()
    ElMessage.success(`已生成第 ${latest.value?.version ?? '?'} 版（${res.chars || 0} 字）`)
  })
}

async function doRevise() {
  await withBusy('revise', async () => {
    if (!reviseText.value.trim()) return ElMessage.warning('请先写修改意见')
    const r = await api.reviseScript(pid, { ...reqPayload(), instruction: reviseText.value, content: content.value })
    const res = await waitTask(r.task_id, 'DeepSeek 正在按意见重写')
    showRevise.value = false
    reviseText.value = ''
    await reloadScript()
    ElMessage.success(`已重写为新版本（${res.chars || 0} 字）`)
  })
}

async function doSave() {
  await withBusy('save', async () => {
    await api.saveScript(pid, { content: content.value })
    await reloadScript()
    ElMessage.success('已保存为新版本')
  })
}

async function doPreview() {
  await withBusy('preview', async () => {
    const r = await api.previewScript(pid, { ...reqPayload(), content: content.value || null })
    previewData.value = r
    previewMode.value = 'generate'
    showPreview.value = true
  })
}

async function loadVersion(row) {
  const full = await api.script(row.id)
  content.value = full.content || ''
  savedContent.value = content.value
  showHistory.value = false
  ElMessage.success(`已载入 v${row.version}（还没保存为新版本，改动前请先「保存为新版本」）`)
}

async function removeVersion(row) {
  try {
    await ElMessageBox.confirm(`删除剧本 v${row.version}？此操作不可撤销。`, '删除版本', { type: 'warning' })
  } catch {
    return
  }
  await api.deleteScript(row.id)
  await reloadScript(true)
  ElMessage.success('已删除')
}

// ---------------- ② 一键生成分集并落库 ----------------
/** 一键：生成集结构+镜头清单 → 自动落库 → 跳看板第 1 集 */
async function doOutlineAndApply() {
  await withBusy('outlineApply', async () => {
    const r = await api.generateOutline(pid, reqPayload())
    const res = await waitTask(r.task_id, 'DeepSeek 正在生成集结构 + 镜头清单')
    if (!res.outline) throw new Error('没有返回分集结构')
    const apply = await api.applyOutline(pid, { outline: res.outline, replace_shots: false })
    let msg = `落库完成：新建 ${apply.episodes_created} 集 / 更新 ${apply.episodes_updated} 集；` +
      `镜头 +${apply.shots_created} ~${apply.shots_updated}`
    ElMessage.success(msg)
    router.push(`/p/${pid}/board?ep=1`)
  })
}

async function doPreviewOutline() {
  await withBusy('previewOutline', async () => {
    const r = await api.previewOutline(pid, reqPayload())
    previewData.value = { generate: { messages: r.messages, chars: r.chars } }
    previewMode.value = 'generate'
    showPreview.value = true
  })
}

onMounted(async () => {
  try {
    await load()
    content.value = latest.value?.content || ''
    savedContent.value = content.value
  } catch (e) {
    err(e)
  }
})

onBeforeUnmount(() => {
  disposed = true
})
</script>

<style scoped>
h3 {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--fs-base);
  margin-bottom: 10px;
}
.spacer { flex: 1; }
.ml8 { margin-left: 8px; }
.mb4 { margin-bottom: 4px; }
.mb8 { margin-bottom: 8px; }
.mt6 { margin-top: 6px; }
.mt8 { margin-top: 8px; }

.req-row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 8px;
}

.job {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 10px;
}
.job :deep(.el-progress) { flex: 1; }

.script-edit {
  width: 100%;
  min-height: 42vh;
  margin-top: 10px;
  padding: 10px 12px;
  box-sizing: border-box;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--panel);
  color: var(--text);
  font-size: var(--fs-base);
  line-height: 1.85;
  font-family: inherit;
  resize: vertical;
  outline: none;
}
.script-edit:focus { border-color: var(--brand); }

.row { display: flex; align-items: center; gap: 8px; }

.prompt-edit :deep(.el-textarea) { margin-bottom: 2px; }

.preview {
  max-height: 60vh;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: var(--fs-sm);
  line-height: 1.7;
  margin: 0;
}

</style>
