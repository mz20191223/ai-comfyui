<template>
  <div>
    <el-alert
      type="info"
      :closable="false"
      class="mb8"
      title="这里决定「换平台不写代码」：供应商填地址与密钥，模型填请求体模板与响应取值。"
      description="请求体模板用 Jinja2 语法（如 {&quot;model&quot;: &quot;{{ model_name }}&quot;, &quot;prompt&quot;: {{ prompt | tojson }}}），响应取值用 JSONPath（如 $.data.task_id）。改完点「测试」看凭证是否就绪。"
    />

    <div class="card">
      <h3>
        <span>默认模型分配</span>
        <span class="spacer"></span>
        <span class="tiny muted">出图 / 出片 各走哪个模型</span>
      </h3>
      <div class="row wrap">
        <div v-for="ms in modelSettings" :key="ms.category" class="assign">
          <div class="tiny muted">{{ catLabel(ms.category) }}</div>
          <el-select
            :model-value="ms.model_id"
            size="small"
            style="width:200px"
            clearable
            placeholder="未指定"
            @change="(v) => setAssign(ms.category, v)"
          >
            <el-option v-for="o in ms.options" :key="o.id" :label="`${o.name}（${o.model_name}）`" :value="o.id" />
          </el-select>
        </div>
      </div>
      <div class="tiny muted mt8">
        未指定时按任务类型自动挑同类别里第一个启用的模型。
      </div>
    </div>

    <div class="card">
      <h3>
        <span>供应商</span>
        <span class="spacer"></span>
        <el-button size="small" type="primary" @click="editProvider(null)">新增供应商</el-button>
      </h3>
      <el-table border stripe :data="providers" size="small">
        <el-table-column prop="name" label="名称" min-width="150">
          <template #default="{ row }">
            <b>{{ row.name }}</b>
            <div class="tiny muted mono">{{ row.key }}</div>
          </template>
        </el-table-column>
        <el-table-column label="能力" width="140">
          <template #default="{ row }">
            <span v-for="c in row.caps" :key="c" class="pill gray" style="margin-right:4px">{{ c }}</span>
            <span v-if="!row.caps.length" class="muted tiny">—</span>
          </template>
        </el-table-column>
        <el-table-column label="地址" min-width="220">
          <template #default="{ row }">
            <div class="tiny ellipsis">{{ row.base_url || '—' }}</div>
            <div class="tiny muted ellipsis" v-if="row.image_base_url || row.video_base_url">
              图：{{ row.image_base_url || '同主地址' }} · 视：{{ row.video_base_url || '同主地址' }}
            </div>
          </template>
        </el-table-column>
        <el-table-column label="密钥 / 账号池" width="190">
          <template #default="{ row }">
            <span v-if="row.cred_total" :class="row.cred_usable ? 'pill ok' : 'pill err'">
              可用 {{ row.cred_usable }} / {{ row.cred_total }}
            </span>
            <span v-else :class="row.has_key ? 'pill ok' : 'pill warn'">
              {{ row.has_key ? '已配置' : '未配置' }}
            </span>
            <div class="tiny muted mono ellipsis" v-if="row.api_key_ref">{{ row.api_key_ref }}</div>
            <div class="tiny muted" v-else-if="row.cred_total">多账号轮换</div>
          </template>
        </el-table-column>
        <el-table-column label="模型数" width="76">
          <template #default="{ row }">{{ row.models.length }}</template>
        </el-table-column>
        <el-table-column label="启用" width="76">
          <template #default="{ row }">
            <el-switch
              :model-value="!!row.enabled"
              size="small"
              @change="(v) => patchProvider(row.id, { enabled: v })"
            />
          </template>
        </el-table-column>
        <el-table-column class-name="op-col" label-class-name="op-col" label="操作" width="270" fixed="right">
          <template #default="{ row }">
            <div class="op-row">
              <el-button size="small" text @click="openCreds(row)">
                账号{{ row.cred_total ? `(${row.cred_total})` : '' }}
              </el-button>
              <el-button size="small" text @click="testProvider(row)">测试</el-button>
              <el-button size="small" text @click="editProvider(row)">编辑</el-button>
              <el-button size="small" text type="danger" @click="removeProvider(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="card">
      <h3>
        <span>模型</span>
        <span class="spacer"></span>
        <el-select v-model="modelCat" size="small" style="width:130px" clearable placeholder="全部类别" @change="loadModels">
          <el-option v-for="c in CATS" :key="c.value" :label="c.label" :value="c.value" />
        </el-select>
        <el-button size="small" type="primary" @click="editModel(null)">新增模型</el-button>
      </h3>
      <el-table border stripe :data="models" size="small">
        <el-table-column prop="name" label="模型" min-width="170">
          <template #default="{ row }">
            <b>{{ row.name }}</b>
            <div class="tiny muted mono">{{ row.model_name }}</div>
          </template>
        </el-table-column>
        <el-table-column label="类别" width="86">
          <template #default="{ row }"><span class="pill brand">{{ catLabel(row.category) }}</span></template>
        </el-table-column>
        <el-table-column prop="provider_name" label="供应商" width="130" />
        <el-table-column label="调用方式" width="120">
          <template #default="{ row }">
            <span class="pill gray">{{ row.mode }}</span>
            <div class="tiny muted">{{ row.request_kind }}</div>
          </template>
        </el-table-column>
        <el-table-column label="参数映射" min-width="180">
          <template #default="{ row }">
            <span v-if="!Object.keys(row.param_map_obj || {}).length" class="muted tiny">未配置</span>
            <span v-for="(v, k) in row.param_map_obj" :key="k" class="pill gray" style="margin-right:4px">
              {{ k }}→{{ v }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="启用" width="76">
          <template #default="{ row }">
            <el-switch :model-value="!!row.enabled" size="small" @change="(v) => patchModel(row.id, { enabled: v })" />
          </template>
        </el-table-column>
        <el-table-column class-name="op-col" label-class-name="op-col" label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <div class="op-row">
              <el-button size="small" text @click="editModel(row)">编辑</el-button>
              <el-button size="small" text @click="duplicateModel(row)">复制</el-button>
              <el-button size="small" text type="danger" @click="removeModel(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="card">
      <h3>
        <span>系统设置</span>
        <span class="spacer"></span>
        <el-button size="small" :loading="loading" @click="loadSettings">刷新</el-button>
      </h3>
      <el-table border stripe :data="settings" size="small">
        <el-table-column prop="key" label="键" min-width="240">
          <template #default="{ row }">
            <span class="mono">{{ row.key }}</span>
            <span v-if="row.category === 'secrets' || row.key.startsWith('provider_key:')" class="pill warn" style="margin-left:6px">密钥</span>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="分类" width="110" />
        <el-table-column label="值" min-width="260">
          <template #default="{ row }">
            <el-input
              v-if="row.editing"
              v-model="row.draft"
              size="small"
              :placeholder="row.masked ? '输入新值覆盖（留空不改）' : ''"
            />
            <span v-else class="mono ellipsis">{{ row.masked ? row.value : (row.value || '—') }}</span>
          </template>
        </el-table-column>
        <el-table-column class-name="op-col" label-class-name="op-col" label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <div class="op-row">
              <template v-if="row.editing">
                <el-button size="small" text type="primary" @click="saveSetting(row)">保存</el-button>
                <el-button size="small" text @click="row.editing = false">取消</el-button>
              </template>
              <el-button v-else size="small" text @click="row.editing = true; row.draft = ''">修改</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="card">
      <h3>环境变量</h3>
      <div class="tiny muted mb8">
        密钥可以写成 <span class="mono">${ENV:变量名}</span> 放进供应商的「密钥引用」，这样密钥就不落库。
        当前已加载的可用变量：
      </div>
      <div v-if="envKeys.length">
        <span v-for="k in envKeys" :key="k" class="pill gray" style="margin:0 4px 4px 0">{{ k }}</span>
      </div>
      <div v-else class="muted tiny">没有检测到 STUDIO_ / MINIMAX / OPENAI 前缀的环境变量。</div>
    </div>

    <!-- 密钥池 -->
    <el-dialog v-model="cDlg" :title="`账号池 · ${cProvider?.name || ''}`" width="900px">
      <el-alert
        type="info"
        :closable="false"
        class="mb8"
        title="同一供应商可挂多个账号，额度用尽 / 被限流会自动轮到下一个"
        description="轮换策略：取「最久没用过」的可用账号；命中额度类错误（余额不足、限流、Key 失效）会把该账号打冷却并当次换号重试。任务记录里会写明这次用的是哪个账号，方便对账。"
      />

      <div class="row wrap mb8">
        <el-input
          v-model="cBulk"
          type="textarea"
          :rows="3"
          class="mono"
          style="flex:1;min-width:420px"
          placeholder="批量粘贴，每行一个 key；也可写「别名,key」或「别名|key」"
        />
        <div class="col-btns" style="margin-left:8px">
          <el-button size="small" type="primary" :loading="cBusy" @click="addBulk">批量添加</el-button>
          <el-button size="small" :loading="cBusy" @click="probeAll">全部测额度</el-button>
        </div>
      </div>

      <el-table border stripe :data="creds" size="small">
        <el-table-column label="别名" width="120">
          <template #default="{ row }">
            <el-input v-if="row._editAlias" v-model="row._alias" size="small" @blur="saveAlias(row)" @keyup.enter="saveAlias(row)" />
            <span v-else style="cursor:pointer" @click="row._alias = row.alias; row._editAlias = true">{{ row.alias }}</span>
          </template>
        </el-table-column>
        <el-table-column label="Key" min-width="200">
          <template #default="{ row }"><span class="mono tiny">{{ row.key_hint }}</span></template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <span :class="statusPill(row)">{{ statusText(row) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="余额 / 额度" min-width="180">
          <template #default="{ row }">
            <template v-if="row.balance !== null && row.balance !== undefined">
              <span>{{ row.balance }} 积分</span>
            </template>
            <template v-else>
              <span class="muted tiny">未查询</span>
              <div class="tiny muted ellipsis" :title="row.balance_note">{{ (row.balance_note || '').slice(0, 40) }}</div>
            </template>
            <div class="tiny muted">{{ row.balance_checked_at || '' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="最近探测" min-width="150">
          <template #default="{ row }">
            <span v-if="row.probe_ok === 1" class="pill ok">通过</span>
            <span v-else-if="row.probe_ok === 0" class="pill err">失败</span>
            <span v-else class="muted tiny">—</span>
            <div class="tiny muted ellipsis" :title="row.probe_note">{{ row.probe_note || '' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="上次使用 / 失败次数" width="160">
          <template #default="{ row }">
            <div class="tiny">{{ row.last_used_at || '—' }}</div>
            <div class="tiny muted">失败 {{ row.fail_count || 0 }} 次</div>
          </template>
        </el-table-column>
        <el-table-column label="启用" width="70">
          <template #default="{ row }">
            <el-switch :model-value="!!row.enabled" size="small" @change="(v) => patchCred(row, { enabled: v })" />
          </template>
        </el-table-column>
        <el-table-column class-name="op-col" label-class-name="op-col" label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <div class="op-row">
              <el-button size="small" text :loading="row._probing" @click="probeOne(row)">查额度</el-button>
              <el-button size="small" text @click="patchCred(row, { status: 'active' })">恢复</el-button>
              <el-button size="small" text type="danger" @click="removeCred(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
      <div class="tiny muted mt8">
        「恢复」会把冷却、失败计数、错误信息一并清掉，用于手动解冻一个被误判的账号。
      </div>

      <template #footer>
        <el-button @click="cDlg = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 供应商编辑 -->
    <el-dialog v-model="pDlg" :title="pForm.id ? '编辑供应商' : '新增供应商'" width="660px">
      <el-form label-width="112px" size="small">
        <el-form-item label="名称">
          <el-input v-model="pForm.name" />
        </el-form-item>
        <el-form-item label="标识 key" v-if="!pForm.id">
          <el-input v-model="pForm.key" placeholder="如 img-default / vid-oldplat" />
        </el-form-item>
        <el-form-item label="能力">
          <el-checkbox-group v-model="pForm.capabilities">
            <el-checkbox label="image">生图</el-checkbox>
            <el-checkbox label="video">生视频</el-checkbox>
            <el-checkbox label="llm">大模型</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="主地址">
          <el-input v-model="pForm.base_url" placeholder="https://api.example.com" />
        </el-form-item>
        <el-form-item label="生图地址">
          <el-input v-model="pForm.image_base_url" placeholder="留空则用主地址" />
        </el-form-item>
        <el-form-item label="视频地址">
          <el-input v-model="pForm.video_base_url" placeholder="留空则用主地址" />
        </el-form-item>
        <el-form-item label="API Key">
          <el-input v-model="pForm.api_key" type="password" show-password :placeholder="pForm.id ? '留空表示不改' : ''" />
        </el-form-item>
        <el-form-item label="密钥引用">
          <el-input v-model="pForm.api_key_ref" placeholder="${ENV:STUDIO_XXX_KEY}" />
        </el-form-item>
        <el-form-item label="鉴权头">
          <el-input v-model="pForm.auth_header" style="width:180px" />
          <el-input v-model="pForm.auth_scheme" style="width:140px;margin-left:8px" placeholder="Bearer" />
        </el-form-item>
        <el-form-item label="并发 / 超时 / 重试">
          <el-input-number v-model="pForm.concurrency" :min="1" :max="16" size="small" />
          <el-input-number v-model="pForm.timeout_sec" :min="10" :max="3600" size="small" style="margin-left:8px" />
          <el-input-number v-model="pForm.retry" :min="0" :max="5" size="small" style="margin-left:8px" />
        </el-form-item>
        <el-form-item label="代理">
          <el-select v-model="pForm.proxy_mode" size="small" style="width:140px">
            <el-option label="跟随系统" value="system" />
            <el-option label="不用代理" value="none" />
            <el-option label="自定义" value="custom" />
          </el-select>
          <el-input v-if="pForm.proxy_mode === 'custom'" v-model="pForm.proxy_url" style="width:300px;margin-left:8px" placeholder="http://127.0.0.1:7890" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="pForm.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pDlg = false">取消</el-button>
        <el-button type="primary" @click="saveProvider">保存</el-button>
      </template>
    </el-dialog>

    <!-- 模型编辑 -->
    <el-dialog v-model="mDlg" :title="mForm.id ? '编辑模型' : '新增模型'" width="760px">
      <el-form label-width="112px" size="small">
        <el-form-item label="名称">
          <el-input v-model="mForm.name" style="width:240px" />
          <span class="tiny muted" style="margin-left:8px">如：分镜图生图-GPT</span>
        </el-form-item>
        <el-form-item label="标识 key" v-if="!mForm.id">
          <el-input v-model="mForm.key" style="width:240px" placeholder="gpt-image-2" />
        </el-form-item>
        <el-form-item label="供应商">
          <el-select v-model="mForm.provider_id" style="width:240px">
            <el-option v-for="p in providers" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="类别">
          <el-select v-model="mForm.category" style="width:140px">
            <el-option v-for="c in CATS" :key="c.value" :label="c.label" :value="c.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="远端模型名">
          <el-input v-model="mForm.model_name" style="width:240px" placeholder="调用时传给对方的 model 字段" />
        </el-form-item>
        <el-form-item label="调用方式">
          <el-select v-model="mForm.mode" style="width:180px">
            <el-option label="同步返回" value="synchronous" />
            <el-option label="异步轮询" value="asynchronous" />
          </el-select>
        </el-form-item>

        <el-divider content-position="left">请求体模板（Jinja2）</el-divider>
        <el-input
          v-model="mForm.request_spec_text"
          type="textarea"
          :rows="7"
          class="mono"
          placeholder='{"model": "{{ model_name }}", "prompt": {{ prompt | tojson }}, "duration": {{ duration }}}'
        />

        <el-divider content-position="left">响应取值（JSONPath）</el-divider>
        <el-input
          v-model="mForm.response_spec_text"
          type="textarea"
          :rows="5"
          class="mono"
          placeholder='{"task_id": "$.task_id", "files": "$.data.file_urls[*]", "status": "$.status"}'
        />

        <el-divider content-position="left">轮询与参数映射</el-divider>
        <el-input
          v-model="mForm.poll_spec_text"
          type="textarea"
          :rows="5"
          class="mono"
          placeholder='{"enabled": true, "url": "/task/{{ task_id }}", "interval_sec": 5, "status_path": "$.status", "success_values": ["Success"], "fail_values": ["Fail"]}'
        />
        <div class="mt8">
          <el-input
            v-model="mForm.param_map_text"
            type="textarea"
            :rows="4"
            class="mono"
            placeholder='{"duration": "duration", "resolution": "resolution", "seed": "seed", "ref_images": "ref_image"}' 
          />
          <div class="tiny muted mt8">
            左侧是工作台参数名（duration / resolution / seed / ref_images / ref_audios / prompt），
            右侧是发给平台的字段名；参考图会自动按 <span class="mono">ref_image_0…N</span> 展开编号。
          </div>
        </div>
        <el-form-item label="启用" style="margin-top:12px">
          <el-switch v-model="mForm.enabled" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="mForm.notes" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="mDlg = false">取消</el-button>
        <el-button type="primary" @click="saveModel">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api'

const CATS = [
  { value: 'image', label: '生图' },
  { value: 'video', label: '生视频' },
  { value: 'llm', label: '大模型' },
]

const providers = ref([])
const models = ref([])
const modelSettings = ref([])
const settings = ref([])
const envKeys = ref([])
const modelCat = ref('')
const loading = ref(false)

const pDlg = ref(false)
const pForm = ref({})
const mDlg = ref(false)
const mForm = ref({})

function catLabel(c) { return (CATS.find((x) => x.value === c) || {}).label || c }

async function loadAll() {
  providers.value = await api.providers()
  await loadModels()
  modelSettings.value = await api.modelSettings()
  await loadSettings()
  const e = await api.envKeys()
  envKeys.value = e.available_env_keys || []
}
async function loadModels() {
  models.value = await api.models(modelCat.value || undefined)
}
async function loadSettings() {
  loading.value = true
  try {
    settings.value = (await api.settings()).map((s) => ({ ...s, editing: false, draft: '' }))
  } finally {
    loading.value = false
  }
}

async function setAssign(cat, modelId) {
  await api.setModelSetting(cat, modelId)
  ElMessage.success('已更新默认模型')
  modelSettings.value = await api.modelSettings()
}

// ---- 密钥池 ----
const cDlg = ref(false)
const cProvider = ref(null)
const creds = ref([])
const cBulk = ref('')
const cBusy = ref(false)

function statusText(row) {
  if (!row.enabled) return '已禁用'
  const map = { active: '可用', cooling: '冷却中', exhausted: '额度耗尽', invalid: 'Key 失效', disabled: '已禁用' }
  return map[row.status] || row.status
}
function statusPill(row) {
  if (!row.enabled) return 'pill gray'
  return { active: 'pill ok', cooling: 'pill warn', exhausted: 'pill err', invalid: 'pill err' }[row.status] || 'pill gray'
}

async function openCreds(row) {
  cProvider.value = row
  cBulk.value = ''
  await loadCreds()
  cDlg.value = true
}
async function loadCreds() {
  if (!cProvider.value) return
  creds.value = (await api.credentials(cProvider.value.id)).map((c) => ({ ...c, _editAlias: false }))
}
async function addBulk() {
  const text = cBulk.value.trim()
  if (!text) return ElMessage.warning('先粘贴 key')
  cBusy.value = true
  try {
    const r = await api.addCredential(cProvider.value.id, { bulk: text })
    ElMessage.success(`新增 ${r.added} 个账号${r.skipped ? `（跳过重复 ${r.skipped} 个）` : ''}`)
    cBulk.value = ''
    await loadCreds()
    await loadAll()
  } finally { cBusy.value = false }
}
async function probeAll() {
  cBusy.value = true
  try {
    const r = await api.probeAllCredentials(cProvider.value.id)
    const ok = (r.results || []).filter((x) => x.ok).length
    ElMessage.success(`探测完成：${ok} / ${r.count} 个账号可用`)
    await loadCreds()
    await loadAll()
  } finally { cBusy.value = false }
}
async function probeOne(row) {
  row._probing = true
  try {
    const r = await api.probeCredential(row.id)
    if (r.ok) ElMessage.success(`${row.alias}：可用${r.balance !== null && r.balance !== undefined ? `，余额 ${r.balance} 积分` : ''}`)
    else ElMessage.warning(`${row.alias}：${r.message || '探测未通过'}`)
    await loadCreds()
    await loadAll()
  } finally { row._probing = false }
}
async function patchCred(row, data) {
  await api.patchCredential(row.id, data)
  await loadCreds()
  await loadAll()
}
async function saveAlias(row) {
  row._editAlias = false
  if (row._alias && row._alias !== row.alias) await patchCred(row, { alias: row._alias })
}
async function removeCred(row) {
  await ElMessageBox.confirm(`删除账号「${row.alias}」？`, '确认', { type: 'warning' })
  await api.deleteCredential(row.id)
  await loadCreds()
  await loadAll()
}

// ---- 供应商 ----
function editProvider(row) {
  pForm.value = row
    ? { ...row, api_key: '', capabilities: [...(row.caps || [])] }
    : {
        name: '', key: '', capabilities: ['video'], base_url: '', image_base_url: '', video_base_url: '',
        api_key: '', api_key_ref: '', auth_header: 'Authorization', auth_scheme: 'Bearer',
        concurrency: 2, timeout_sec: 600, retry: 1, proxy_mode: 'system', proxy_url: '', enabled: true,
      }
  pDlg.value = true
}
async function saveProvider() {
  const f = pForm.value
  if (!f.name) return ElMessage.warning('请填名称')
  const body = {
    name: f.name,
    capabilities: f.capabilities,
    base_url: f.base_url || null,
    image_base_url: f.image_base_url || null,
    video_base_url: f.video_base_url || null,
    api_key: f.api_key || null,
    api_key_ref: f.api_key_ref || null,
    auth_header: f.auth_header,
    auth_scheme: f.auth_scheme,
    concurrency: f.concurrency,
    timeout_sec: f.timeout_sec,
    retry: f.retry,
    proxy_mode: f.proxy_mode,
    proxy_url: f.proxy_url || null,
    enabled: f.enabled,
  }
  if (f.id) await api.patchProvider(f.id, body)
  else await api.createProvider({ ...body, key: f.key })
  ElMessage.success('已保存')
  pDlg.value = false
  await loadAll()
}
async function patchProvider(id, data) {
  await api.patchProvider(id, data)
  await loadAll()
}
async function removeProvider(row) {
  await ElMessageBox.confirm(`删除供应商「${row.name}」？其下模型也会一并失去来源。`, '确认', { type: 'warning' })
  await api.deleteProvider(row.id)
  await loadAll()
}
async function testProvider(row) {
  const r = await api.testProvider(row.id)
  ElMessageBox.alert(
    `账号池：${r.cred_usable} / ${r.cred_total} 个可用`
      + `\n密钥：${r.has_key ? r.key_hint || '已设置' : '未配置'}`
      + `\n地址：${r.base_url || '未填'}`
      + `\n启用：${r.enabled ? '是' : '否'}`
      + `\n\n${r.advice}`,
    `供应商自检 · ${row.name}`,
    { confirmButtonText: '知道了' },
  )
}

// ---- 模型 ----
function editModel(row) {
  mForm.value = row
    ? {
        ...row,
        request_spec_text: JSON.stringify(row.request || {}, null, 2),
        response_spec_text: JSON.stringify(row.response || {}, null, 2),
        poll_spec_text: JSON.stringify(row.poll || {}, null, 2),
        param_map_text: JSON.stringify(row.param_map_obj || {}, null, 2),
      }
    : {
        name: '', key: '', provider_id: providers.value[0]?.id, category: 'video',
        model_name: '', mode: 'asynchronous',
        request_spec_text: '{\n  "model": "{{ model_name }}",\n  "prompt": {{ prompt | tojson }}\n}',
        response_spec_text: '{\n  "task_id": "$.task_id"\n}',
        poll_spec_text: '{\n  "enabled": true,\n  "url": "/task/{{ task_id }}",\n  "interval_sec": 5,\n  "status_path": "$.status",\n  "success_values": ["Success"],\n  "fail_values": ["Fail"]\n}',
        param_map_text: '{\n  "duration": "duration",\n  "resolution": "resolution",\n  "ref_images": "ref_image",\n  "ref_audios": "ref_audio"\n}',
        enabled: true, notes: '',
      }
  mDlg.value = true
}
function parseOr(obj, text, field) {
  if (!text || !text.trim()) return null
  try {
    return JSON.parse(text)
  } catch (e) {
    ElMessage.error(`${field} 不是合法 JSON：${e.message}`)
    throw e
  }
}
async function saveModel() {
  const f = mForm.value
  if (!f.name || !f.provider_id || !f.model_name) return ElMessage.warning('名称、供应商、远端模型名为必填')
  let req, resp, poll, pmap
  try {
    req = parseOr(null, f.request_spec_text, '请求体模板')
    resp = parseOr(null, f.response_spec_text, '响应取值')
    poll = parseOr(null, f.poll_spec_text, '轮询配置')
    pmap = parseOr(null, f.param_map_text, '参数映射')
  } catch (e) { return }
  const body = {
    provider_id: f.provider_id, name: f.name, category: f.category, model_name: f.model_name,
    mode: f.mode, request_spec: req, response_spec: resp, poll_spec: poll, param_map: pmap,
    enabled: f.enabled, notes: f.notes || null,
  }
  if (f.id) await api.patchModel(f.id, body)
  else await api.createModel({ ...body, key: f.key })
  ElMessage.success('已保存')
  mDlg.value = false
  await loadAll()
}
async function patchModel(id, data) {
  await api.patchModel(id, data)
  await loadModels()
}
async function duplicateModel(row) {
  const body = {
    provider_id: row.provider_id, key: `${row.key}-copy-${Date.now().toString().slice(-4)}`,
    name: `${row.name} 副本`, category: row.category, model_name: row.model_name, mode: row.mode,
    request_kind: row.request_kind, request_spec: row.request, response_spec: row.response,
    poll_spec: row.poll, defaults: row.default_params, param_map: row.param_map_obj,
    enabled: false, notes: row.notes,
  }
  await api.createModel(body)
  ElMessage.success('已复制（默认不启用，改好后手动打开）')
  await loadAll()
}
async function removeModel(row) {
  await ElMessageBox.confirm(`删除模型「${row.name}」？`, '确认', { type: 'warning' })
  await api.deleteModel(row.id)
  await loadAll()
}

// ---- 系统设置 ----
async function saveSetting(row) {
  const v = row.draft
  if (!v && row.masked) { row.editing = false; return }
  await api.setSettings([{ key: row.key, value: v, category: row.category }])
  ElMessage.success('已保存')
  await loadSettings()
}

onMounted(loadAll)
</script>

<style scoped>
.assign { margin-right: 18px; }
.mono :deep(textarea) { font-family: 'Cascadia Mono', Consolas, monospace; font-size: var(--fs-sm); }
.col-btns { display: flex; flex-direction: column; gap: 6px; }
.col-btns :deep(.el-button + .el-button) { margin-left: 0; }
</style>
