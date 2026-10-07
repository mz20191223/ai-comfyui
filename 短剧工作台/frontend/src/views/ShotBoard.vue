<template>
  <div>
    <div class="card">
      <h3>
        <el-select v-model="epId" size="small" style="width: 160px" placeholder="选择集" @change="load">
          <el-option v-for="e in episodes" :key="e.id" :label="`第 ${e.number} 集`" :value="e.id" />
        </el-select>
        <el-button size="small" @click="addEpisode">新建一集</el-button>
<span class="tiny muted" style="margin-left: 8px">
{{ shots.length }} 镜 · 总 {{ totalDur }}s
</span>
<span v-if="!episodes.length" class="tiny" style="margin-left: 8px; color: var(--el-color-warning)">
本项目还没有分集：点左侧「新建一集」手动建，或到「剧本」页点「生成并落库 → 看板」
</span>
        <span class="tiny muted" v-if="genStat.total" style="margin-left: 8px">
          双份提示词 {{ genStat.have }}/{{ genStat.total }} 镜已生成
        </span>
        <span class="spacer"></span>
        <el-input v-model="q" size="small" placeholder="搜镜号/标题/台词" style="width: 180px" clearable />
        <el-checkbox v-model="onlyIssues" size="small">仅看有问题</el-checkbox>
        <el-button size="small" :disabled="!epId" @click="$router.push(`/p/${pid}/timeline?ep=${epId}`)">合成</el-button>
        <el-button size="small" type="primary" :disabled="!epId" :loading="genBusy" @click="genPrompts">出本集双份提示词</el-button>
        <el-button size="small" type="primary" plain @click="addShot">新建镜头</el-button>
      </h3>

      <el-table
        border
        stripe
        :data="filtered"
        size="small"
        v-loading="loading"
        @row-click="openDetail"
        style="cursor: pointer"
        :row-class-name="rowClass"
      >
        <el-table-column label="镜号" width="72">
          <template #default="{ row }">
            <b class="mono">{{ row.shot_code }}</b>
          </template>
        </el-table-column>
        <el-table-column label="标题 / 摘要" min-width="200">
          <template #default="{ row }">
            <div class="ellipsis">{{ row.title || row.summary || '—' }}</div>
            <div class="tiny muted ellipsis" v-if="row.line_text">「{{ row.line_text }}」</div>
          </template>
        </el-table-column>
        <el-table-column label="首帧 / 分镜图" width="96">
          <template #default="{ row }">
            <div class="mini-thumb" v-if="row.status.first_frame">
              <img
                :src="thumbUrl(row.status.first_frame.path, 120)"
                loading="lazy"
                title="点击看大图"
                @click.stop="openPreview(row.status.first_frame.path)"
              />
            </div>
            <div v-else class="mini-thumb empty-thumb">
              <span class="tiny muted">{{ row.image_target_name ? '待出图' : '—' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="出图" width="96">
          <template #default="{ row }">
            <TaskPill :slot="row.task_state.image" />
          </template>
        </el-table-column>
        <el-table-column label="出视频" width="96">
          <template #default="{ row }">
            <TaskPill :slot="row.task_state.video" />
          </template>
        </el-table-column>
        <el-table-column label="时长" width="66">
          <template #default="{ row }">
            <span :class="{ 'pill warn': durationRisk(row) }">{{ row.duration_sec ?? '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="模式" width="70">
          <template #default="{ row }">
            <span class="pill gray">{{ row.gen_mode || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="音频" width="96">
          <template #default="{ row }">
            <span v-if="row.audio_file" class="tiny">
              {{ row.audio_measured_sec ? row.audio_measured_sec + 's' : '已配' }}
            </span>
            <span v-else class="muted tiny">—</span>
          </template>
        </el-table-column>
        <el-table-column class-name="op-col" label-class-name="op-col" label="操作" width="90" fixed="right">
          <template #default="{ row }">
            <div class="op-row">
              <el-button size="small" text type="primary" @click.stop="openDetail(row)">详情</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 镜头详情：弹窗内嵌，不再跳二级页面 -->
    <el-dialog
      v-model="showDetail"
      :title="detailShot ? `${detailShot.shot_code} · ${detailShot.title || '镜头详情'}` : '镜头详情'"
      width="94%"
      top="4vh"
      :close-on-click-modal="false"
      class="detail-dlg"
      destroy-on-close
      @closed="load"
    >
      <ShotDetail
        v-if="detailShot"
        :key="detailShot.id"
        :shot-id="detailShot.id"
        :project-id="pid"
        embedded
      />
    </el-dialog>

    <ElImageViewer
      v-if="previewPath"
      :url-list="[previewPath]"
      :hide-on-click-modal="true"
      teleported
      @close="previewPath = ''"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox, ElImageViewer } from 'element-plus'
import { api, fileUrl, thumbUrl } from '../api'
import TaskPill from '../components/TaskPill.vue'
import ShotDetail from './ShotDetail.vue'

const route = useRoute()
const pid = Number(route.params.pid)
const episodes = ref([])
const epId = ref(null)
const shots = ref([])
const loading = ref(false)
const q = ref('')
const onlyIssues = ref(false)
const showDetail = ref(false)
const detailShot = ref(null)
const genBusy = ref(false)
const genStat = ref({ total: 0, have: 0 })
// 看板首帧缩略图 → 点开看大图（点行是打开详情，所以图片上要 stop）
const previewPath = ref('')
function openPreview(p) {
  previewPath.value = p ? fileUrl(p) : ''
}
const epNumber = computed(() => {
  const e = episodes.value.find((x) => x.id === epId.value)
  return e ? e.number : '?'
})

function openDetail(row) {
  detailShot.value = row
  showDetail.value = true
}

const totalDur = computed(() =>
  shots.value.reduce((a, s) => a + (Number(s.duration_sec) || 0), 0).toFixed(0),
)

const filtered = computed(() =>
  shots.value.filter((s) => {
    if (onlyIssues.value && !s.error_count && !s.warn_count) return false
    if (q.value) {
      const t = q.value.toLowerCase()
      const hay = `${s.shot_code} ${s.title || ''} ${s.line_text || ''} ${s.summary || ''}`.toLowerCase()
      if (!hay.includes(t)) return false
    }
    return true
  }),
)

function rowClass({ row }) {
  const a = row.task_state.image
  const b = row.task_state.video
  return a?.status === 'failed' || b?.status === 'failed' ? 'row-err' : ''
}
function durationRisk(row) {
  if (!row.audio_measured_sec || !row.duration_sec || row.line_start_sec == null) return false
  return row.duration_sec - row.line_start_sec < row.audio_measured_sec
}

async function load() {
  if (!epId.value) {
    shots.value = []
    genStat.value = { total: 0, have: 0 }
    return
  }
  loading.value = true
  try {
    shots.value = await api.shots(epId.value)
    await refreshGenStat()
  } finally {
    loading.value = false
  }
}

/** 统计本集双份提示词齐备情况（读 shot-list 接口） */
async function refreshGenStat() {
  try {
    const sl = await api.shotList(epId.value)
    const list = sl.shots || []
    genStat.value = {
      total: list.length,
      have: list.filter((s) => s.has_image_prompt && s.has_video_prompt).length,
    }
  } catch {
    genStat.value = { total: shots.value.length, have: 0 }
  }
}

function waitTask(tid) {
  return new Promise((resolve, reject) => {
    const tick = async () => {
      let t
      try {
        t = await api.task(tid)
      } catch (e) {
        return reject(e)
      }
      if (t.status === 'succeeded') return resolve(t.result_json || {})
      if (t.status === 'failed') return reject(new Error(t.fail_message || '生成失败'))
      if (t.status === 'cancelled') return reject(new Error('任务已取消'))
      setTimeout(tick, 2000)
    }
    tick()
  })
}

/** 出本集双份提示词（分镜图 + 视频），素材声明由工作台自动拼 */
async function genPrompts() {
  if (!epId.value) return ElMessage.warning('请先选择一集')
  genBusy.value = true
  try {
    const r = await api.genShotPrompts(epId.value, {})
    await waitTask(r.task_id)
    await load()
    ElMessage.success(`第 ${epNumber.value} 集双份提示词已回填（${genStat.value.have}/${genStat.value.total} 镜齐备）`)
  } catch (e) {
    ElMessage.error(e?.message || '生成失败')
  } finally {
    genBusy.value = false
  }
}


/** 新建一集（集号默认取现有最大集号 +1，可改） */
async function addEpisode() {
  const next = episodes.value.length
    ? Math.max(...episodes.value.map((e) => Number(e.number) || 0)) + 1
    : 1
  let value
  try {
    const r = await ElMessageBox.prompt('新集号', '新建一集', {
      inputValue: String(next),
      inputPattern: /^[0-9]+$/,
      inputErrorMessage: '集号必须是数字',
    })
    value = r.value
  } catch {
    return null
  }
  const created = await api.createEpisode(pid, { number: Number(value) })
  episodes.value = await api.episodes(pid)
  epId.value = created.id
  await load()
  ElMessage.success(`已新建第 ${created.number} 集`)
  return created
}

async function addShot() {
  // 还没有分集时先建集，别直接报错
  if (!epId.value) {
    try {
      await ElMessageBox.confirm('本项目还没有分集，先新建一集？', '还没有分集', { type: 'warning' })
    } catch {
      return
    }
    const created = await addEpisode()
    if (!created) return
  }
  const { value } = await ElMessageBox.prompt('新镜号（如 15、16a）', '新建镜头', {
    inputPattern: /^[0-9]+[A-Za-z]?(-\d+)?$/,
    inputErrorMessage: '格式如 15 / 16a / 16a-1',
  })
  await api.createShot(epId.value, { shot_code: value })
  ElMessage.success('已创建')
  await load()
}

onMounted(async () => {
  episodes.value = await api.episodes(pid)
  const qEp = Number(route.query.ep)
  // 只认「本项目」的集：?ep 按集号匹配，匹配不到就用本项目第一集，绝不回退到别项目的集
  const match = episodes.value.find((e) => e.number === qEp)
  epId.value = (match && match.id) || (episodes.value[0] && episodes.value[0].id) || null
  if (epId.value) await load()
  window.addEventListener('studio-refresh', load)
})
</script>

<style scoped>
.mini-thumb { width: 54px; height: 42px; border-radius: 4px; overflow: hidden; background: #f2f3f5; display: flex; align-items: center; justify-content: center; }
.mini-thumb img { width: 100%; height: 100%; object-fit: cover; }
:deep(.row-warn) { background: #fffdf6; }
/* 镜头详情弹窗：内容较多，让弹窗体自己滚，且给足高度 */
.detail-dlg :deep(.el-dialog__body) { padding: 6px 14px 14px; max-height: 82vh; overflow: auto; }
</style>
