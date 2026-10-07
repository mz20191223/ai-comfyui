<template>
  <div>
    <el-tabs v-model="tab">
      <!-- 模板 -->
      <el-tab-pane label="提示词模板" name="tpl">
        <div class="card">
          <h3>
            <el-select v-model="tplCat" size="small" style="width:200px" clearable placeholder="全部类别" @change="loadTemplates">
              <el-option v-for="c in cats" :key="c.value" :label="c.label" :value="c.value" />
            </el-select>
            <span class="tiny muted">{{ templates.length }} 个模板</span>
            <span class="spacer"></span>
            <el-button size="small" type="primary" @click="editTpl(null)">新建模板</el-button>
          </h3>
          <el-table border stripe :data="templates" size="small">
            <el-table-column label="模板" min-width="230">
              <template #default="{ row }">
                <b>{{ row.name }}</b>
                <span v-if="row.is_system" class="pill gray" style="margin-left:6px">系统</span>
                <span v-if="row.is_default" class="pill brand" style="margin-left:4px">默认</span>
                <div class="tiny muted">{{ row.description }}</div>
              </template>
            </el-table-column>
            <el-table-column label="类别" width="140">
              <template #default="{ row }"><span class="pill gray">{{ catLabel(row.category) }}</span></template>
            </el-table-column>
            <el-table-column label="变量" min-width="180">
              <template #default="{ row }">
                <span v-for="v in row.var_list" :key="v.name" class="pill gray" style="margin-right:4px">
                  {{ v.name }}{{ v.required ? '*' : '' }}
                </span>
                <span v-if="!row.var_list.length" class="muted tiny">—</span>
              </template>
            </el-table-column>
            <el-table-column label="作用域" width="90">
              <template #default="{ row }">
                <span class="tiny muted">{{ row.project_id ? '本项目' : '全局' }}</span>
              </template>
            </el-table-column>
            <el-table-column class-name="op-col" label-class-name="op-col" label="操作" width="260" fixed="right">
              <template #default="{ row }">
                <div class="op-row">
                  <el-button size="small" text @click="viewTpl(row)">查看</el-button>
                  <el-button size="small" text @click="editTpl(row)">编辑</el-button>
                  <el-button size="small" text @click="duplicate(row)">复制</el-button>
                  <el-button size="small" text type="danger" :disabled="!!row.is_system" @click="removeTpl(row)">删除</el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <!-- 片段 -->
      <el-tab-pane label="常用片段" name="snip">
        <div class="card">
          <h3>
            <span>可复用句子片段</span>
            <span class="tiny muted">编辑提示词时可一键插入</span>
            <span class="spacer"></span>
            <el-button size="small" type="primary" @click="editSnip(null)">新建片段</el-button>
          </h3>
          <el-table border stripe :data="snippets" size="small">
            <el-table-column prop="label" label="名称" width="150" />
            <el-table-column prop="category" label="分类" width="100">
              <template #default="{ row }"><span class="pill gray">{{ row.category }}</span></template>
            </el-table-column>
            <el-table-column label="内容" min-width="330">
              <template #default="{ row }"><span class="tiny">{{ row.content }}</span></template>
            </el-table-column>
            <el-table-column label="自动应用" width="120">
              <template #default="{ row }">
                <span v-if="row.auto && row.auto.stage" class="pill brand">{{ row.auto.stage }}</span>
                <span v-else class="muted tiny">手动</span>
              </template>
            </el-table-column>
            <el-table-column class-name="op-col" label-class-name="op-col" label="操作" width="130" fixed="right">
              <template #default="{ row }">
                <div class="op-row">
                  <el-button size="small" text @click="editSnip(row)">编辑</el-button>
                  <el-button size="small" text type="danger" @click="removeSnip(row)">删除</el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <!-- Lint -->
      <el-tab-pane label="Lint 规则" name="lint">
        <div class="card">
          <h3>
            <span>提示词体检规则</span>
            <span class="tiny muted">出图/出片前自动扫描，命中即拦</span>
            <span class="spacer"></span>
            <el-button size="small" @click="loadRules">刷新</el-button>
          </h3>
          <el-table border stripe :data="rules" size="small">
            <el-table-column label="规则" min-width="230">
              <template #default="{ row }">
                <b>{{ row.label }}</b>
                <div class="tiny muted">{{ row.description }}</div>
              </template>
            </el-table-column>
            <el-table-column label="阶段" width="86">
              <template #default="{ row }">
                <span class="pill gray">{{ { video: '视频', image: '图片', both: '通用' }[row.stage] || row.stage }}</span>
              </template>
            </el-table-column>
            <el-table-column label="级别" width="80">
              <template #default="{ row }">
                <span class="pill" :class="{ error: 'err', warn: 'warn', info: 'gray' }[row.severity]">
                  {{ { error: '错误', warn: '警告', info: '提示' }[row.severity] || row.severity }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="checker" label="检查器" width="150" />
            <el-table-column label="配置" min-width="200">
              <template #default="{ row }">
                <span class="tiny muted mono ellipsis">{{ JSON.stringify(row.cfg) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="启用" width="76">
              <template #default="{ row }">
                <el-switch :model-value="!!row.enabled" size="small" @change="(v) => patchRule(row.id, { enabled: v ? 1 : 0 })" />
              </template>
            </el-table-column>
            <el-table-column class-name="op-col" label-class-name="op-col" label="操作" width="90" fixed="right">
              <template #default="{ row }">
                <div class="op-row">
                  <el-button size="small" text @click="editRule(row)">编辑</el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <!-- 版本历史 -->
      <el-tab-pane label="版本回溯" name="rev">
        <div class="card">
          <h3>
            <span>提示词版本历史</span>
            <span class="spacer"></span>
            <el-select v-model="revEp" size="small" style="width:130px" @change="loadRevShots">
              <el-option v-for="e in episodes" :key="e.id" :label="`第 ${e.number} 集`" :value="e.id" />
            </el-select>
            <el-select v-model="revShot" size="small" style="width:140px" filterable placeholder="选镜头" @change="loadRevisions">
              <el-option v-for="s in revShots" :key="s.id" :label="`${s.shot_code} ${s.title || ''}`" :value="s.id" />
            </el-select>
            <el-select v-model="revKind" size="small" style="width:130px" @change="loadRevisions">
              <el-option label="视频提示词" value="shot_video" />
              <el-option label="分镜图提示词" value="shot_image" />
            </el-select>
          </h3>
          <el-table border stripe :data="revisions" size="small" v-if="revShot">
            <el-table-column prop="id" label="#" width="60" />
            <el-table-column prop="source" label="来源" width="100">
              <template #default="{ row }">
                <span class="pill gray">{{ srcLabel(row.source) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="note" label="备注" min-width="180" />
            <el-table-column prop="size" label="字符数" width="90" />
            <el-table-column prop="created_at" label="时间" width="170" />
            <el-table-column class-name="op-col" label-class-name="op-col" label="操作" width="220" fixed="right">
              <template #default="{ row }">
                <div class="op-row">
                  <el-button size="small" text @click="viewRev(row)">对比</el-button>
                  <el-button size="small" text type="primary" @click="restore(row)">回滚到此版</el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
          <div v-else class="empty">先选一个镜头</div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 模板编辑 -->
    <el-dialog v-model="tplDlg" :title="tplForm.id ? '编辑模板' : '新建模板'" width="820px">
      <el-form label-width="96px" size="small">
        <el-form-item label="名称"><el-input v-model="tplForm.name" /></el-form-item>
        <el-form-item label="类别">
          <el-select v-model="tplForm.category" style="width:220px">
            <el-option v-for="c in cats" :key="c.value" :label="c.label" :value="c.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="说明"><el-input v-model="tplForm.description" /></el-form-item>
        <el-form-item label="内容">
          <el-input v-model="tplForm.content" type="textarea" :rows="10" class="mono" />
        </el-form-item>
        <el-form-item label="变量声明">
          <el-input
            v-model="tplForm.variablesText"
            type="textarea"
            :rows="4"
            class="mono"
            placeholder='[{"name":"subject","label":"画面主体","type":"textarea","required":true}]'
          />
        </el-form-item>
        <el-form-item label="默认模板"><el-switch v-model="tplForm.is_default" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="tplDlg = false">取消</el-button>
        <el-button @click="renderTest">渲染测试</el-button>
        <el-button type="primary" @click="saveTpl">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="tplView" title="模板内容" width="720px">
      <pre class="prompt">{{ tplViewRow?.content }}</pre>
      <div class="mt8 tiny muted">变量：{{ (tplViewRow?.var_list || []).map((v) => v.name).join(', ') || '无' }}</div>
    </el-dialog>

    <el-dialog v-model="renderDlg" title="渲染结果（用默认值试跑）" width="720px">
      <pre class="prompt">{{ renderOut }}</pre>
    </el-dialog>

    <!-- 片段编辑 -->
    <el-dialog v-model="snipDlg" :title="snipForm.id ? '编辑片段' : '新建片段'" width="580px">
      <el-form label-width="88px" size="small">
        <el-form-item label="名称"><el-input v-model="snipForm.label" /></el-form-item>
        <el-form-item label="标识 key" v-if="!snipForm.id"><el-input v-model="snipForm.key" /></el-form-item>
        <el-form-item label="分类">
          <el-select v-model="snipForm.category" style="width:150px">
            <el-option label="硬约束 guard" value="guard" />
            <el-option label="负向词 negative" value="negative" />
            <el-option label="锁定句 lock" value="lock" />
            <el-option label="风格 style" value="style" />
          </el-select>
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="snipForm.content" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="自动应用">
          <el-select v-model="snipForm.autoStage" style="width:150px" clearable placeholder="不自动应用">
            <el-option label="视频提示词" value="video" />
            <el-option label="分镜图提示词" value="image" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="snipDlg = false">取消</el-button>
        <el-button type="primary" @click="saveSnip">保存</el-button>
      </template>
    </el-dialog>

    <!-- 规则编辑 -->
    <el-dialog v-model="ruleDlg" title="编辑 Lint 规则" width="620px">
      <el-form label-width="96px" size="small">
        <el-form-item label="名称"><el-input v-model="ruleForm.label" /></el-form-item>
        <el-form-item label="说明"><el-input v-model="ruleForm.description" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="阶段">
          <el-select v-model="ruleForm.stage" style="width:140px">
            <el-option label="视频" value="video" />
            <el-option label="图片" value="image" />
            <el-option label="通用" value="both" />
          </el-select>
        </el-form-item>
        <el-form-item label="级别">
          <el-select v-model="ruleForm.severity" style="width:140px">
            <el-option label="错误" value="error" />
            <el-option label="警告" value="warn" />
            <el-option label="提示" value="info" />
          </el-select>
        </el-form-item>
        <el-form-item label="检查器">
          <el-select v-model="ruleForm.checker" style="width:220px">
            <el-option v-for="c in checkers" :key="c.value" :label="c.label" :value="c.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="配置 JSON">
          <el-input v-model="ruleForm.configText" type="textarea" :rows="4" class="mono" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ruleDlg = false">取消</el-button>
        <el-button type="primary" @click="saveRule">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="revDlg" title="版本内容对比" width="820px">
      <div class="tiny muted mb8">历史版本 vs 当前</div>
      <div class="row">
        <div class="col">
          <div class="tiny muted">历史（#{{ revRow?.id }}）</div>
          <pre class="prompt">{{ revContent }}</pre>
        </div>
        <div class="col">
          <div class="tiny muted">当前</div>
          <pre class="prompt">{{ currentContent }}</pre>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api'

const route = useRoute()
const pid = Number(route.params.pid)

const tab = ref('tpl')
const cats = ref([])
const templates = ref([])
const tplCat = ref('')
const tplDlg = ref(false)
const tplForm = ref({})
const tplView = ref(false)
const tplViewRow = ref(null)
const renderDlg = ref(false)
const renderOut = ref('')

const snippets = ref([])
const snipDlg = ref(false)
const snipForm = ref({})

const rules = ref([])
const checkers = ref([])
const ruleDlg = ref(false)
const ruleForm = ref({})

const episodes = ref([])
const revEp = ref(null)
const revShots = ref([])
const revShot = ref(null)
const revKind = ref('shot_video')
const revisions = ref([])
const revDlg = ref(false)
const revRow = ref(null)
const revContent = ref('')
const currentContent = ref('')

function catLabel(c) { return (cats.value.find((x) => x.value === c) || {}).label || c }
function srcLabel(s) { return { manual: '手动', template: '模板', import: '导入', restore: '回滚' }[s] || s }

async function loadTemplates() {
  templates.value = await api.templates(pid, tplCat.value || undefined)
}
async function loadSnippets() {
  snippets.value = await api.snippets(pid)
}
async function loadRules() {
  rules.value = await api.lintRules(pid)
}

// 模板
function editTpl(row) {
  tplForm.value = row
    ? { ...row, variablesText: JSON.stringify(row.var_list || [], null, 2) }
    : { name: '', category: 'keyframe_image', description: '', content: '', variablesText: '[]', is_default: false }
  tplDlg.value = true
}
function viewTpl(row) {
  tplViewRow.value = row
  tplView.value = true
}
async function saveTpl() {
  const f = tplForm.value
  if (!f.name || !f.content) return ElMessage.warning('名称与内容必填')
  let vars
  try {
    vars = f.variablesText.trim() ? JSON.parse(f.variablesText) : []
  } catch (e) {
    return ElMessage.error(`变量声明不是合法 JSON：${e.message}`)
  }
  const body = {
    name: f.name, category: f.category, description: f.description,
    content: f.content, variables: vars, is_default: f.is_default,
  }
  if (f.id) await api.patchTemplate(f.id, body)
  else await api.createTemplate({ ...body, project_id: pid })
  ElMessage.success('已保存')
  tplDlg.value = false
  await loadTemplates()
}
async function duplicate(row) {
  await api.duplicateTemplate(row.id)
  ElMessage.success('已复制为本项目模板')
  await loadTemplates()
}
async function removeTpl(row) {
  await ElMessageBox.confirm(`删除模板「${row.name}」？`, '确认', { type: 'warning' })
  await api.deleteTemplate(row.id)
  await loadTemplates()
}
async function renderTest() {
  const f = tplForm.value
  const vars = {}
  try {
    for (const v of JSON.parse(f.variablesText || '[]')) {
      if (v.type === 'refs') vars[v.name] = [{ name: '示例角色', take_note: '仅取面部特征' }]
      else vars[v.name] = v.default ?? `[${v.label || v.name}]`
    }
  } catch (e) { /* ignore */ }
  if (!f.id) {
    renderOut.value = `（未保存的模板无法试渲染，先保存再试）\n\n将使用变量：\n${JSON.stringify(vars, null, 2)}`
    renderDlg.value = true
    return
  }
  const r = await api.renderTemplate(f.id, vars)
  renderOut.value = r.output
  renderDlg.value = true
}

// 片段
function editSnip(row) {
  snipForm.value = row
    ? { ...row, autoStage: row.auto?.stage || '' }
    : { key: '', label: '', category: 'guard', content: '', autoStage: '' }
  snipDlg.value = true
}
async function saveSnip() {
  const f = snipForm.value
  if (!f.label || !f.content) return ElMessage.warning('名称与内容必填')
  const auto = f.autoStage ? { stage: f.autoStage } : null
  if (f.id) await api.patchSnippet(f.id, { label: f.label, content: f.content, category: f.category, auto_apply: auto })
  else await api.createSnippet({ project_id: pid, key: f.key, label: f.label, content: f.content, category: f.category, auto_apply: auto })
  ElMessage.success('已保存')
  snipDlg.value = false
  await loadSnippets()
}
async function removeSnip(row) {
  await ElMessageBox.confirm(`删除片段「${row.label}」？`, '确认', { type: 'warning' })
  await api.deleteSnippet(row.id)
  await loadSnippets()
}

// 规则
function editRule(row) {
  ruleForm.value = { ...row, configText: JSON.stringify(row.cfg || {}, null, 2) }
  ruleDlg.value = true
}
async function saveRule() {
  const f = ruleForm.value
  let cfg
  try {
    cfg = f.configText.trim() ? JSON.parse(f.configText) : {}
  } catch (e) {
    return ElMessage.error(`配置不是合法 JSON：${e.message}`)
  }
  await api.patchLintRule(f.id, {
    label: f.label, description: f.description, stage: f.stage, severity: f.severity,
    checker: f.checker, config: cfg,
  })
  ElMessage.success('已保存')
  ruleDlg.value = false
  await loadRules()
}
async function patchRule(id, data) {
  await api.patchLintRule(id, data)
  await loadRules()
}

// 版本
async function loadRevShots() {
  revShot.value = null
  revisions.value = []
  revShots.value = await api.shots(revEp.value)
}
async function loadRevisions() {
  if (!revShot.value) return
  revisions.value = await api.revisions(revKind.value, revShot.value)
}
async function viewRev(row) {
  const r = await api.revision(row.id)
  revContent.value = r.content
  const s = await api.shot(revShot.value)
  currentContent.value = revKind.value === 'shot_video' ? s.detail.video_prompt : s.detail.image_prompt
  revRow.value = row
  revDlg.value = true
}
async function restore(row) {
  await ElMessageBox.confirm(`把提示词回滚到版本 #${row.id}？当前内容会先存为一个新版本。`, '确认', { type: 'warning' })
  await api.restoreRevision(row.id)
  ElMessage.success('已回滚')
  await loadRevisions()
}

onMounted(async () => {
  cats.value = await api.templateCategories()
  checkers.value = await api.lintCheckers()
  await Promise.all([loadTemplates(), loadSnippets(), loadRules()])
  episodes.value = await api.episodes(pid)
  if (episodes.value.length) {
    revEp.value = episodes.value[0].id
    await loadRevShots()
  }
})
</script>

<style scoped>
.mono :deep(textarea) { font-family: 'Cascadia Mono', Consolas, monospace; font-size: var(--fs-sm); }
</style>
