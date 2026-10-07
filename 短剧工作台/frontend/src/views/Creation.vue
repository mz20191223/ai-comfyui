<template>
  <div>
    <div class="card">
      <h3>
        <span>创作流水线</span>
        <span class="spacer"></span>
        <span class="tiny muted">从创意到成片的八步；每一步都能单独补做</span>
        <el-button size="small" @click="load">刷新</el-button>
      </h3>
      <div class="steps">
        <div v-for="(s, k) in pipeline.steps" :key="k" class="step" :class="{ done: s.done }">
          <span class="dot" :class="s.done ? 'ok' : 'gray'"></span>
          <div class="nm">{{ s.label }}</div>
          <div class="tiny muted">{{ fmtDetail(s.detail) }}</div>
        </div>
      </div>
    </div>

    <div class="card">
      <h3>
        <span>剧集与剧本</span>
        <span class="spacer"></span>
        <el-button size="small" type="primary" @click="addEpisode">新建集</el-button>
      </h3>
      <el-table border stripe :data="episodes" size="small">
        <el-table-column label="集" width="66">
          <template #default="{ row }">第 {{ row.number }} 集</template>
        </el-table-column>
        <el-table-column prop="title" label="标题" min-width="150" />
        <el-table-column prop="shot_count" label="镜头" width="70" />
        <el-table-column label="剧本" width="100">
          <template #default="{ row }">
            <span v-if="row.script_text" class="pill ok">{{ row.script_text.length }} 字</span>
            <span v-else class="pill gray">未录入</span>
          </template>
        </el-table-column>
        <el-table-column label="文档" min-width="200">
          <template #default="{ row }">
            <div v-if="row.video_doc_path" class="tiny muted ellipsis" :title="row.video_doc_path">
              提示词：{{ baseName(row.video_doc_path) }}
            </div>
            <div v-if="row.storyboard_doc_path" class="tiny muted ellipsis" :title="row.storyboard_doc_path">
              分镜图：{{ baseName(row.storyboard_doc_path) }}
            </div>
            <span v-if="!row.video_doc_path && !row.storyboard_doc_path" class="muted tiny">—</span>
          </template>
        </el-table-column>
        <el-table-column class-name="op-col" label-class-name="op-col" label="操作" width="400" fixed="right">
          <template #default="{ row }">
            <div class="op-row">
              <el-button size="small" text @click="openScript(row)">剧本/拆镜</el-button>
              <el-button size="small" text @click="openApply(row)">套模板生成提示词</el-button>
              <el-button size="small" text @click="$router.push(`/p/${pid}/board?ep=${row.id}`)">看板</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="card">
      <h3>
        <span>创意库</span>
        <span class="tiny muted">从一句话灵感开始，逐步长成剧本</span>
        <span class="spacer"></span>
        <el-button size="small" type="primary" @click="editIdea(null)">新建创意</el-button>
      </h3>
      <el-table border stripe :data="ideas" size="small">
        <el-table-column label="标题" min-width="170">
          <template #default="{ row }">
            <b>{{ row.title || '（未命名）' }}</b>
            <div class="tiny muted ellipsis">{{ row.one_liner }}</div>
          </template>
        </el-table-column>
        <el-table-column label="故事" min-width="220">
          <template #default="{ row }">
            <span class="tiny ellipsis">{{ (row.story_text || '').slice(0, 120) || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <span class="pill gray">{{ { idea: '创意', script: '已成剧本', shot: '已拆镜' }[row.status] || row.status }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新" width="160" />
        <el-table-column class-name="op-col" label-class-name="op-col" label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <div class="op-row">
              <el-button size="small" text @click="editIdea(row)">编辑</el-button>
              <el-button size="small" text type="danger" @click="removeIdea(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 剧本与拆镜 -->
    <el-dialog v-model="scriptDlg" title="剧本与拆镜" width="900px" top="5vh">
      <el-form label-width="96px" size="small">
        <el-form-item label="从文件读取">
          <el-input v-model="scriptPath" placeholder="粘贴剧本 md 的完整路径，留空则用下面的文本" />
          <el-button size="small" style="margin-left:8px" @click="readScriptFile">读取</el-button>
        </el-form-item>
        <el-form-item label="剧本内容">
          <el-input v-model="scriptText" type="textarea" :rows="16" class="mono" placeholder="用「## 镜头1」作为镜头标题；### 分镜图提示词 / ### 分镜视频提示词 分节" />
        </el-form-item>
        <el-form-item label="拆镜选项">
          <el-checkbox v-model="splitReplace">清空原有镜头后重建（危险）</el-checkbox>
          <el-checkbox v-model="splitCreateAssets">顺带从台词里抽取角色建资产</el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="scriptDlg = false">取消</el-button>
        <el-button @click="saveScript">只保存剧本</el-button>
        <el-button type="primary" :loading="splitting" @click="doSplit">拆解分镜</el-button>
      </template>
    </el-dialog>

    <!-- 套模板 -->
    <el-dialog v-model="applyDlg" title="套模板生成提示词" width="720px">
      <el-alert
        type="info"
        :closable="false"
        class="mb8"
        title="会把模板渲染结果覆盖写入所选镜头的提示词，并自动存一个版本。"
      />
      <el-form label-width="96px" size="small">
        <el-form-item label="生成哪一份">
          <el-radio-group v-model="applyStage">
            <el-radio-button value="image">分镜图提示词</el-radio-button>
            <el-radio-button value="video">视频提示词</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="模板">
          <el-select v-model="applyTpl" style="width:100%" filterable>
            <el-option v-for="t in applyTemplates" :key="t.id" :label="`${t.name}（${catLabel(t.category)}）`" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="作用范围">
          <el-select v-model="applyScope" style="width:200px">
            <el-option label="整集所有镜头" value="all" />
            <el-option label="只处理没提示词的镜头" value="empty" />
          </el-select>
        </el-form-item>
        <el-form-item label="补充变量">
          <el-input v-model="applyVarsText" type="textarea" :rows="3" class="mono" placeholder='{"style_tail":"写实摄影，电影质感。"}' />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="applyDlg = false">取消</el-button>
        <el-button type="primary" :loading="applying" @click="doApply">生成</el-button>
      </template>
    </el-dialog>

    <!-- 创意编辑 -->
    <el-dialog v-model="ideaDlg" :title="ideaForm.id ? '编辑创意' : '新建创意'" width="720px">
      <el-form label-width="88px" size="small">
        <el-form-item label="标题"><el-input v-model="ideaForm.title" /></el-form-item>
        <el-form-item label="一句话">
          <el-input v-model="ideaForm.one_liner" placeholder="用一个钩子把故事说清" />
        </el-form-item>
        <el-form-item label="故事">
          <el-input v-model="ideaForm.story_text" type="textarea" :rows="10" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="ideaForm.status" style="width:150px">
            <el-option label="创意" value="idea" />
            <el-option label="已成剧本" value="script" />
            <el-option label="已拆镜" value="shot" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ideaDlg = false">取消</el-button>
        <el-button type="primary" @click="saveIdea">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api'

const route = useRoute()
const pid = Number(route.params.pid)

const pipeline = ref({ steps: {} })
const episodes = ref([])
const ideas = ref([])

const scriptDlg = ref(false)
const curEp = ref(null)
const scriptText = ref('')
const scriptPath = ref('')
const splitReplace = ref(false)
const splitCreateAssets = ref(true)
const splitting = ref(false)

const applyDlg = ref(false)
const applyStage = ref('image')
const applyTpl = ref(null)
const applyTpls = ref([])
const applyScope = ref('all')
const applyVarsText = ref('')
const applying = ref(false)

const ideaDlg = ref(false)
const ideaForm = ref({})

const applyTemplates = computed(() =>
  applyTpls.value.filter((t) => (applyStage.value === 'image' ? t.category.includes('image') : t.category.includes('video'))),
)

function fmtDetail(d) {
  if (d === undefined || d === null) return ''
  return typeof d === 'object' ? Object.entries(d).map(([k, v]) => `${k}:${v}`).join(' ') : d
}
function baseName(p) { return String(p || '').split(/[\\/]/).pop() }
function catLabel(c) { return { video_prefix: '视频首行', video_body: '视频正文', keyframe_image: '分镜图骨架', character_image: '角色图', scene_image: '场景图', prop_image: '道具图', negative_base: '负向词', tts_script: '台词稿' }[c] || c }

async function load() {
  const [p, e, i] = await Promise.all([api.pipeline(pid), api.episodes(pid), api.ideas(pid)])
  pipeline.value = p
  episodes.value = e
  ideas.value = i
}

async function addEpisode() {
  const { value } = await ElMessageBox.prompt('第几集（数字）', '新建集', {
    inputPattern: /^\d+$/,
    inputErrorMessage: '请输入数字',
  })
  await api.createEpisode(pid, { number: Number(value), title: `第 ${value} 集` })
  ElMessage.success('已新建')
  await load()
}

async function openScript(ep) {
  curEp.value = ep
  const full = await api.episode(ep.id)
  scriptText.value = full.script_text || ''
  scriptPath.value = full.video_doc_path || ''
  splitReplace.value = false
  scriptDlg.value = true
}
async function readScriptFile() {
  if (!scriptPath.value) return ElMessage.warning('请先填文件路径')
  const r = await api.splitScript(curEp.value.id, { script_path: scriptPath.value, replace: false, create_assets: false })
  ElMessage.info(`已读取剧本（识别到 ${r.shots_total} 个镜头标题）`)
  const full = await api.episode(curEp.value.id)
  scriptText.value = full.script_text || ''
}
async function saveScript() {
  await api.patchEpisode(curEp.value.id, { script_text: scriptText.value, video_doc_path: scriptPath.value || null })
  ElMessage.success('剧本已保存')
  await load()
}
async function doSplit() {
  splitting.value = true
  try {
    if (scriptText.value) await api.patchEpisode(curEp.value.id, { script_text: scriptText.value })
    const r = await api.splitScript(curEp.value.id, {
      script_text: scriptText.value || null,
      replace: splitReplace.value,
      create_assets: splitCreateAssets.value,
    })
    ElMessage.success(`识别 ${r.shots_total} 镜：新建 ${r.created} / 更新 ${r.updated}，新增资产 ${r.assets_created}`)
    scriptDlg.value = false
    await load()
  } finally {
    splitting.value = false
  }
}

async function openApply(ep) {
  curEp.value = ep
  applyTpls.value = await api.templates(pid)
  applyStage.value = 'image'
  applyTpl.value = (applyTemplates.value[0] || {}).id || null
  applyScope.value = 'empty'
  applyVarsText.value = ''
  applyDlg.value = true
}
async function doApply() {
  if (!applyTpl.value) return ElMessage.warning('请选模板')
  let vars = {}
  if (applyVarsText.value.trim()) {
    try {
      vars = JSON.parse(applyVarsText.value)
    } catch (e) {
      return ElMessage.error(`补充变量不是合法 JSON：${e.message}`)
    }
  }
  applying.value = true
  try {
    let shotIds = null
    if (applyScope.value === 'empty') {
      const shots = await api.shots(curEp.value.id)
      const has = new Set()
      for (const s of shots) {
        const full = await api.shot(s.id)
        const v = applyStage.value === 'image' ? full.detail.image_prompt : full.detail.video_prompt
        if (v && v.trim()) has.add(s.id)
      }
      shotIds = shots.filter((s) => !has.has(s.id)).map((s) => s.id)
      if (!shotIds.length) {
        ElMessage.info('所有镜头都已有提示词，无需生成')
        return
      }
    }
    const r = await api.applyTemplate(curEp.value.id, {
      template_id: applyTpl.value, stage: applyStage.value, shot_ids: shotIds, variables: vars,
    })
    const errs = (r.results || []).filter((x) => x.error)
    ElMessage.success(`已生成 ${r.applied} 个镜头的提示词${errs.length ? `（${errs.length} 个失败）` : ''}`)
    applyDlg.value = false
    await load()
  } finally {
    applying.value = false
  }
}

function editIdea(row) {
  ideaForm.value = row ? { ...row } : { title: '', one_liner: '', story_text: '', status: 'idea' }
  ideaDlg.value = true
}
async function saveIdea() {
  const f = ideaForm.value
  const body = { project_id: pid, title: f.title, one_liner: f.one_liner, story_text: f.story_text, status: f.status }
  if (f.id) await api.patchIdea(f.id, body)
  else await api.createIdea(body)
  ElMessage.success('已保存')
  ideaDlg.value = false
  await load()
}
async function removeIdea(row) {
  await ElMessageBox.confirm(`删除创意「${row.title || row.id}」？`, '确认', { type: 'warning' })
  await api.deleteIdea(row.id)
  await load()
}

onMounted(load)
</script>

<style scoped>
.steps { display: grid; grid-template-columns: repeat(auto-fill, minmax(196px, 1fr)); gap: 8px; }
.step { border: 1px solid var(--border); border-radius: 5px; padding: 8px 10px; background: #fafbfc; }
.step.done { border-color: #cbe8d6; background: #f6fdf8; }
.step .nm { font-size: var(--fs-sm); font-weight: 600; margin: 4px 0 2px; }
.mono :deep(textarea) { font-family: 'Cascadia Mono', Consolas, monospace; font-size: var(--fs-sm); }
</style>
