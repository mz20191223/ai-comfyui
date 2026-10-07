<template>
  <div>
    <div class="row wrap">
      <div v-for="c in cards" :key="c.key" class="card stat" :class="{ on: status === c.key }" @click="pick(c.key)">
        <div class="n">{{ c.count }}</div>
        <div class="tiny muted">{{ c.label }}</div>
      </div>
      <div class="card stat" style="flex:1;min-width:190px;cursor:default">
        <div class="row" style="align-items:center;gap:6px">
          <span class="dot" :class="stats.running ? 'run' : 'gray'"></span>
          <span style="font-size: var(--fs-sm)">{{ stats.running ? `${stats.running} 个任务进行中` : '当前无进行中的任务' }}</span>
        </div>
        <div class="tiny muted" style="margin-top:6px">实时推送已{{ live ? '开启' : '关闭' }} · 点左侧卡片可筛选</div>
      </div>
    </div>

    <div class="card">
      <h3>
        <span>任务列表</span>
        <span class="spacer"></span>
        <el-select v-model="kind" size="small" style="width:140px" clearable placeholder="任务类型" @change="load">
          <el-option v-for="k in KINDS" :key="k" :label="kindLabel(k)" :value="k" />
        </el-select>
        <el-select v-model="projectId" size="small" style="width:170px" clearable placeholder="全部项目" @change="load">
          <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
        <el-input v-model="q" size="small" placeholder="搜镜号 / 备注 / 错误" style="width:180px" clearable />
        <el-button size="small" :loading="loading" @click="load">刷新</el-button>
        <el-button size="small" @click="clearFinished">清理已结束</el-button>
      </h3>

      <el-table border stripe :data="filtered" size="small" v-loading="loading" :row-class-name="rowClass">
        <el-table-column prop="id" label="#" width="58" />
        <el-table-column label="类型" width="86">
          <template #default="{ row }">
            <span class="pill gray">{{ kindLabel(row.task_kind) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="项目" width="132">
          <template #default="{ row }">
            <span v-if="row.project_name" class="tiny ellipsis" :title="row.project_name">{{ row.project_name }}</span>
            <span v-else class="muted tiny">—</span>
          </template>
        </el-table-column>
        <el-table-column label="镜头" width="120">
          <template #default="{ row }">
            <a v-if="row.shot" class="link" @click="gotoShot(row.shot)">
              第{{ row.shot.episode_number }}集 {{ row.shot.shot_code }}
            </a>
            <span v-else class="muted tiny">—</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="108">
          <template #default="{ row }">
            <span class="pill" :class="statusClass(row.status)">
              <span v-if="row.status === 'running'" class="dot run"></span>{{ statusLabel(row.status) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="进度" width="130">
          <template #default="{ row }">
            <div class="bar"><i :style="{ width: (row.progress || 0) + '%' }"></i></div>
            <div class="tiny muted">{{ row.progress || 0 }}% · {{ row.note || '—' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="模型 / 供应商" width="150">
          <template #default="{ row }">
            <div class="ellipsis">{{ row.model_name || '—' }}</div>
            <div class="tiny muted ellipsis">{{ row.provider_name || '—' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="产物" width="180">
          <template #default="{ row }">
            <div v-if="row.output_files && row.output_files.length" class="tiny">
              <a class="link" @click="preview(row.output_files[0])">{{ baseName(row.output_files[0]) }}</a>
              <span v-if="row.output_files.length > 1" class="muted"> +{{ row.output_files.length - 1 }}</span>
            </div>
            <span v-else class="muted tiny">—</span>
          </template>
        </el-table-column>
        <el-table-column label="耗时 / 失败原因" min-width="170">
          <template #default="{ row }">
            <span v-if="row.error" class="err-text">「{{ row.error }}」</span>
            <span v-else class="tiny muted">{{ row.finished_at ? `${row.started_at || '—'} → ${row.finished_at}` : (row.started_at || '未开始') }}</span>
          </template>
        </el-table-column>
        <el-table-column class-name="op-col" label-class-name="op-col" label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <div class="op-row">
              <el-button size="small" text @click="openDetail(row)">详情</el-button>
              <el-button v-if="isActive(row)" size="small" text type="warning" @click="doCancel(row)">取消</el-button>
              <el-button v-else size="small" text type="primary" @click="doRetry(row)">重试</el-button>
              <el-button v-if="!isActive(row)" size="small" text type="danger" @click="doDelete(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-drawer v-model="showDetail" title="任务详情" size="620px">
      <div v-if="detail">
        <div class="kv mb8">
          <div class="k">任务</div><div class="v">#{{ detail.id }} · {{ kindLabel(detail.task_kind) }} · {{ statusLabel(detail.status) }}</div>
          <div class="k">模型</div><div class="v">{{ detail.model_name || '—' }} / {{ detail.provider_name || '—' }}</div>
          <div class="k">模式</div><div class="v">{{ detail.mode }}</div>
          <div class="k">创建</div><div class="v">{{ detail.created_at }}</div>
          <div class="k">结束</div><div class="v">{{ detail.finished_at || '—' }}</div>
          <div class="k">重试次数</div><div class="v">{{ detail.attempt || 0 }} / {{ detail.max_attempts || 1 }}</div>
        </div>
        <el-alert v-if="detail.error" type="error" :closable="false" :title="detail.error" class="mb8" />
        <el-tabs v-model="tab">
          <el-tab-pane label="请求参数" name="payload">
            <pre class="prompt">{{ pretty(detail.payload_json) }}</pre>
          </el-tab-pane>
          <el-tab-pane label="返回结果" name="result">
            <pre class="prompt">{{ pretty(detail.result_json) }}</pre>
          </el-tab-pane>
          <el-tab-pane label="视频提示词" name="prompt">
            <pre class="prompt">{{ detail.payload_json?.prompt || '（本任务无提示词）' }}</pre>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-drawer>

    <el-dialog v-model="showPreview" :title="previewName" width="620px">
      <img v-if="isImage(previewPath)" :src="fileUrl(previewPath)" style="max-width:100%;border-radius:6px" />
      <video v-else-if="isVideo(previewPath)" :src="fileUrl(previewPath)" controls style="max-width:100%;border-radius:6px" />
      <audio v-else-if="isAudio(previewPath)" :src="fileUrl(previewPath)" controls style="width:100%" />
      <div v-else class="empty">该文件无法预览，路径：{{ previewPath }}</div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api, fileUrl } from '../api'

const router = useRouter()
const KINDS = ['video_generation', 'image_generation', 'extract_frame', 'compose', 'normalize_8bit', 'lint']
const LABELS = {
  video_generation: '出片', image_generation: '出图',
  extract_frame: '抽尾帧', compose: '合成', normalize_8bit: '转码', lint: 'Lint',
}
const STATUS = { submitted: '已提交', running: '进行中', succeeded: '已完成', failed: '失败', cancelled: '已取消' }

const tasks = ref([])
const stats = ref({ by_status: {}, running: 0 })
const projects = ref([])
const status = ref('')
const kind = ref('')
const projectId = ref(null)
const q = ref('')
const loading = ref(false)
const showDetail = ref(false)
const detail = ref(null)
const tab = ref('payload')
const showPreview = ref(false)
const previewPath = ref('')
const previewName = ref('')
const live = ref(false)

let es = null

const cards = computed(() => [
  { key: 'running', label: '进行中', count: (stats.value.by_status.running || 0) + (stats.value.by_status.submitted || 0) },
  { key: 'succeeded', label: '成功', count: stats.value.by_status.succeeded || 0 },
  { key: 'failed', label: '失败', count: stats.value.by_status.failed || 0 },
  { key: 'cancelled', label: '已取消', count: stats.value.by_status.cancelled || 0 },
])

const filtered = computed(() =>
  tasks.value.filter((t) => {
    if (status.value === 'running' && !['running', 'submitted'].includes(t.status)) return false
    if (status.value && status.value !== 'running' && t.status !== status.value) return false
    if (q.value) {
      const hay = `${t.id} ${t.shot?.shot_code || ''} ${t.note || ''} ${t.error || ''} ${t.model_name || ''}`
      if (!hay.toLowerCase().includes(q.value.toLowerCase())) return false
    }
    return true
  }),
)

function kindLabel(k) { return LABELS[k] || k }
function statusLabel(s) { return STATUS[s] || s }
function statusClass(s) {
  return { succeeded: 'ok', failed: 'err', running: 'run', submitted: 'gray', cancelled: 'gray' }[s] || 'gray'
}
function isActive(row) { return ['submitted', 'running'].includes(row.status) }
function rowClass({ row }) { return row.status === 'failed' ? 'row-err' : '' }
function baseName(p) { return String(p || '').split(/[\\/]/).pop() }
function isImage(p) { return /\.(jpg|jpeg|png|webp|bmp|gif)$/i.test(p || '') }
function isVideo(p) { return /\.(mp4|mov|webm|mkv)$/i.test(p || '') }
function isAudio(p) { return /\.(mp3|wav|m4a|aac|flac|ogg)$/i.test(p || '') }
function pretty(o) { return JSON.stringify(o || {}, null, 2) }
function pick(k) { status.value = status.value === k ? '' : k }

async function load() {
  loading.value = true
  try {
    const [t, s] = await Promise.all([
      api.tasks({ status: '', task_kind: kind.value || undefined, project_id: projectId.value || undefined, limit: 200 }),
      api.taskStats(),
    ])
    tasks.value = t
    stats.value = s
  } finally {
    loading.value = false
  }
}

function gotoShot(shot) {
  router.push(`/p/${shot.project_id}/shot/${shot.id}`)
}
function preview(p) {
  previewPath.value = p
  previewName.value = baseName(p)
  showPreview.value = true
}
async function openDetail(row) {
  detail.value = await api.task(row.id)
  tab.value = 'payload'
  showDetail.value = true
}
async function doCancel(row) {
  await api.cancelTask(row.id, '用户手动取消')
  ElMessage.success('已请求取消')
  load()
}
async function doRetry(row) {
  const r = await api.retryTask(row.id)
  ElMessage.success(`已重试，新任务 #${r.task_id}`)
  load()
}
async function doDelete(row) {
  await ElMessageBox.confirm(`删除任务 #${row.id} 的记录？（不影响已产出的文件）`, '确认', { type: 'warning' })
  await api.deleteTask(row.id)
  load()
}
async function clearFinished() {
  await ElMessageBox.confirm('清理所有「成功」和「已取消」的任务记录？', '确认', { type: 'warning' })
  const r = await api.clearFinished()
  ElMessage.success(`已清理 ${r.deleted} 条`)
  load()
}

function connectLive() {
  const ids = tasks.value.filter(isActive).map((t) => t.id)
  if (es) { es.close(); es = null }
  live.value = false
  if (!ids.length) return
  es = new EventSource(`/api/tasks-stream?ids=${ids.join(',')}`)
  es.onmessage = (ev) => {
    live.value = true
    try {
      const data = JSON.parse(ev.data)
      for (const u of data.tasks || []) {
        const t = tasks.value.find((x) => x.id === u.id)
        if (t) { t.status = u.status; t.progress = u.progress; t.error = u.error; t.note = u.note }
      }
      if ((data.tasks || []).every((x) => !['submitted', 'running'].includes(x.status))) {
        es.close(); es = null; live.value = false; load()
      }
    } catch (e) { /* ignore */ }
  }
  es.onerror = () => { live.value = false }
}

let timer = null
onMounted(async () => {
  projects.value = await api.projects()
  await load()
  connectLive()
  timer = setInterval(() => {
    if (tasks.value.some(isActive)) load().then(connectLive)
  }, 8000)
  window.addEventListener('studio-refresh', load)
})
onUnmounted(() => {
  if (es) es.close()
  if (timer) clearInterval(timer)
  window.removeEventListener('studio-refresh', load)
})
</script>

<style scoped>
.stat { cursor: pointer; min-width: 104px; text-align: center; padding: 10px; }
.stat .n { font-size: var(--fs-xl); font-weight: 600; }
.stat.on { border-color: var(--brand); box-shadow: 0 0 0 2px rgba(74, 92, 240, .12); }
.link { color: var(--brand); cursor: pointer; }
.err-text { color: var(--err); font-size: var(--fs-sm); }
:deep(.row-err) { background: #fffafa; }
</style>
