<template>
  <div>
    <div class="row wrap">
      <div class="card stat" v-for="s in sevCards" :key="s.key" :class="{ on: sev === s.key }" @click="sev = sev === s.key ? '' : s.key">
        <div class="n">{{ s.count }}</div>
        <div class="tiny muted">{{ s.label }}</div>
      </div>
      <div class="card" style="flex:1;min-width:260px">
        <div class="tiny muted mb8">按类型分布</div>
        <div class="row wrap">
          <span v-for="(c, t) in data.by_type" :key="t" class="pill gray" style="margin:0 6px 6px 0">
            {{ typeLabel(t) }} {{ c }}
          </span>
          <span v-if="!Object.keys(data.by_type || {}).length" class="muted tiny">没有任何问题，很干净。</span>
        </div>
      </div>
    </div>

    <div class="card">
      <h3>
        <span>{{ resolved ? '已解决问题' : '待处理问题' }}</span>
        <span class="spacer"></span>
        <el-select v-model="typeFilter" size="small" style="width:180px" clearable placeholder="按类型筛选">
          <el-option v-for="(c, t) in data.by_type" :key="t" :label="`${typeLabel(t)} (${c})`" :value="t" />
        </el-select>
        <el-select v-model="epFilter" size="small" style="width:130px" clearable placeholder="全部集">
          <el-option v-for="e in episodes" :key="e.id" :label="`第 ${e.number} 集`" :value="e.number" />
        </el-select>
        <el-checkbox v-model="resolved" @change="load">显示已解决</el-checkbox>
        <el-button size="small" :loading="loading" @click="load">刷新</el-button>
        <el-button size="small" :loading="rescanning" @click="rescan">重新解析文档</el-button>
      </h3>

      <el-table border stripe :data="filtered" size="small" v-loading="loading" :row-class-name="rowClass">
        <el-table-column label="级别" width="76">
          <template #default="{ row }">
            <span class="pill" :class="sevClass(row.severity)">{{ sevLabel(row.severity) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="130">
          <template #default="{ row }">
            <span class="tiny">{{ typeLabel(row.issue_type) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="位置" width="120">
          <template #default="{ row }">
            <a v-if="row.shot_id" class="link" @click="goShot(row)">
              第{{ row.episode_number }}集 {{ row.shot_code }}
            </a>
            <span v-else class="muted tiny">{{ row.target || '项目级' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="问题" min-width="260">
          <template #default="{ row }">
            <div>{{ row.message }}</div>
            <div v-if="row.target" class="tiny muted ellipsis" :title="row.target">对象：{{ row.target }}</div>
          </template>
        </el-table-column>
        <el-table-column label="建议" min-width="220">
          <template #default="{ row }">
            <span class="tiny muted">{{ row.suggestion || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column class-name="op-col" label-class-name="op-col" label="操作" width="190" fixed="right">
          <template #default="{ row }">
            <div class="op-row">
              <el-button v-if="row.shot_id" size="small" text @click="goShot(row)">去处理</el-button>
              <el-button v-if="!resolved" size="small" text type="primary" @click="resolve(row)">标记解决</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const route = useRoute()
const router = useRouter()
const pid = Number(route.params.pid)

const TYPE_LABELS = {
  missing_suffix: '文件名缺后缀',
  ghost_ref: '幽灵引用',
  deprecated: '已废弃素材',
  missing_file: '文件找不到',
  duration_short: '时长不足',
  no_audio: '缺音频素材',
  too_many_refs: '参考图超限',
  bad_placeholder: '占位未替换',
  asset_no_image: '资产缺参考图',
  audio_too_long: '音频过长',
  dialogue_format: '台词格式',
  missing_doc: '缺文档',
}

const data = ref({ issues: [], by_type: {}, by_severity: {}, total: 0 })
const episodes = ref([])
const sev = ref('')
const typeFilter = ref('')
const epFilter = ref(null)
const resolved = ref(false)
const loading = ref(false)
const rescanning = ref(false)

const sevCards = computed(() => [
  { key: 'error', label: '错误', count: data.value.by_severity.error || 0 },
  { key: 'warn', label: '警告', count: data.value.by_severity.warn || 0 },
  { key: 'info', label: '提示', count: data.value.by_severity.info || 0 },
])

const filtered = computed(() =>
  data.value.issues.filter((i) => {
    if (sev.value && i.severity !== sev.value) return false
    if (typeFilter.value && i.issue_type !== typeFilter.value) return false
    if (epFilter.value && i.episode_number !== epFilter.value) return false
    return true
  }),
)

function sevLabel(s) { return { error: '错误', warn: '警告', info: '提示' }[s] || s }
function sevClass(s) { return { error: 'err', warn: 'warn', info: 'gray' }[s] || 'gray' }
function typeLabel(t) { return TYPE_LABELS[t] || t }
function rowClass({ row }) { return row.severity === 'error' ? 'row-err' : '' }

async function load() {
  loading.value = true
  try {
    data.value = await api.health(pid, resolved.value ? 1 : 0)
  } finally {
    loading.value = false
  }
}
async function resolve(row) {
  await api.resolveIssue(row.id)
  ElMessage.success('已标记解决')
  await load()
  window.dispatchEvent(new CustomEvent('studio-refresh'))
}
async function rescan() {
  rescanning.value = true
  try {
    const r = await api.rescan(pid)
    const bad = (r.results || []).filter((x) => !x.ok)
    ElMessage.success(bad.length ? `已重解析，${bad.length} 集失败` : '已按现有文档重解析全部集')
    await load()
  } finally {
    rescanning.value = false
  }
}
function goShot(row) {
  router.push(`/p/${pid}/shot/${row.shot_id}`)
}

onMounted(async () => {
  episodes.value = await api.episodes(pid)
  await load()
})
</script>

<style scoped>
.stat { cursor: pointer; min-width: 96px; text-align: center; padding: 10px; }
.stat .n { font-size: var(--fs-xl); font-weight: 600; }
.stat.on { border-color: var(--brand); box-shadow: 0 0 0 2px rgba(74, 92, 240, .12); }
.link { color: var(--brand); cursor: pointer; }
:deep(.row-err) { background: #fffafa; }
</style>
