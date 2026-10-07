<template>
  <div>
    <div class="proj-bar">
      <span class="pill brand">{{ projectName || '当前项目' }}</span>
      <span class="tiny muted">
        资产库<b>按项目隔离</b>：这里只有本项目的角色 / 场景 / 道具。其他项目的资产不会出现在列表中，
        也不能挂到本项目的镜头里（接口层已拦）。
      </span>
    </div>

    <div class="card">
      <h3>
        <el-radio-group v-model="type" size="small" @change="load">
          <el-radio-button value="">全部 {{ assets.length }}</el-radio-button>
          <el-radio-button v-for="t in TYPES" :key="t.value" :value="t.value">
            {{ t.label }} {{ countOf(t.value) }}
          </el-radio-button>
        </el-radio-group>
        <span class="spacer"></span>
        <el-input v-model="q" size="small" placeholder="搜资产名 / 别名" style="width:180px" clearable />
        <el-checkbox v-model="onlyMissing" size="small">只看缺图</el-checkbox>
        <el-button size="small" @click="showCoverage" :loading="covLoading">覆盖度检查</el-button>
        <el-button size="small" @click="scan" :loading="scanning">扫目录补资产</el-button>
        <el-button size="small" type="primary" @click="editAsset(null)">新建资产</el-button>
      </h3>

      <div class="asset-grid" v-loading="loading">
        <div v-for="a in filtered" :key="a.id" class="asset" :class="{ warn: !a.images.length }" @click="open(a)">
          <div class="cover">
            <img
              v-if="cover(a)"
              :src="thumbUrl(cover(a), 220)"
              loading="lazy"
              title="点击看大图"
              @click.stop="openPreview([fileUrl(cover(a))])"
            />
            <span v-else class="no-img">缺参考图</span>
          </div>
          <div class="info">
            <div class="nm ellipsis" :title="a.name">{{ a.name }}</div>
            <div class="tiny muted">
              {{ typeLabel(a.asset_type) }} · 图 {{ a.images.length }} · 镜 {{ a.shot_count }}
            </div>
            <div v-if="a.voice_id" class="tiny muted ellipsis">音色 {{ a.voice_id }}</div>
          </div>
        </div>
        <div v-if="!filtered.length" class="empty" style="grid-column:1/-1">没有符合条件的资产</div>
      </div>
    </div>

    <!-- 资产详情 -->
    <el-drawer v-model="showDetail" :title="cur ? `${cur.name}（${typeLabel(cur.asset_type)}）` : '资产'" size="720px">
      <div v-if="cur">
        <div class="card">
          <h3>
            <span>参考图</span>
            <span class="spacer"></span>
            <el-button size="small" @click="picker = true">从素材目录选</el-button>
            <el-button size="small" type="primary" @click="pickUpload">上传图片</el-button>
          </h3>
          <input
            ref="fileInput"
            type="file"
            accept="image/*"
            style="display:none"
            @change="doUpload"
          />
          <div class="thumb-grid">
            <div v-for="im in cur.images" :key="im.id" class="thumb" :class="{ sel: im.is_primary }">
              <img
                v-if="isImage(im.file_name)"
                :src="thumbUrl(im.file_path, 200)"
                loading="lazy"
                title="点击看大图"
                @click="openAssetImage(im)"
              />
              <div v-else class="no-img small">非图片</div>
              <div class="cap">
                <div class="ellipsis" :title="im.file_name">{{ im.file_name }}</div>
                <div class="tiny muted">
                  {{ im.usage_kind }}{{ im.view_angle ? ` · ${im.view_angle}` : '' }}
                  <span v-if="im.is_primary" class="pill brand" style="margin-left:4px">主图</span>
                  <span v-if="im.file_exists === false" class="pill err" style="margin-left:4px">文件丢失</span>
                </div>
                <div class="tiny" style="margin-top:4px">
                  <a class="link" @click="setPrimary(im)">设为主图</a>
                  <a class="link danger" style="margin-left:8px" @click="removeImage(im)">删除</a>
                </div>
              </div>
            </div>
            <div v-if="!cur.images.length" class="muted tiny" style="padding:8px 0">
              还没有参考图。可以「上传图片」（从本机选文件），或「从素材目录选」（已在项目文件夹里的）。
              出图/出片前建议先补上，否则该资产只能靠文字描述。
            </div>
          </div>
        </div>

        <div class="card">
          <h3>基本信息</h3>
          <el-form label-width="96px" size="small">
            <el-form-item label="名称">
              <el-input v-model="form.name" />
            </el-form-item>
            <el-form-item label="类型">
              <el-select v-model="form.asset_type" style="width:140px">
                <el-option v-for="t in TYPES" :key="t.value" :label="t.label" :value="t.value" />
              </el-select>
            </el-form-item>
            <el-form-item label="别名">
              <el-input v-model="form.aliasText" placeholder="逗号分隔：如 过客,路人甲" />
            </el-form-item>
            <el-form-item label="锁定句">
              <el-input
                v-model="form.lock_sentence"
                type="textarea"
                :rows="2"
                placeholder="全片通用的面部/发型/服饰锁定句，写一次到处复用"
              />
            </el-form-item>
            <el-form-item label="描述">
              <el-input v-model="form.description" type="textarea" :rows="3" />
            </el-form-item>
            <el-form-item label="音色">
              <el-input v-model="form.voice_id" style="width:180px" placeholder="如 云希 / 云健" />
              <span class="tiny muted" style="margin-left:8px">外部做配音时参照这个音色</span>
            </el-form-item>
            <el-form-item label="画质档">
              <el-select v-model="form.quality_level" style="width:140px">
                <el-option label="高 HIGH" value="HIGH" />
                <el-option label="中 MEDIUM" value="MEDIUM" />
                <el-option label="低 LOW" value="LOW" />
              </el-select>
            </el-form-item>
            <el-form-item label="所属项目">
              <span class="tiny muted">
                {{ cur.project_name || '—' }}
                <span style="margin-left:6px">（资产按项目隔离，只在所属项目内可用）</span>
              </span>
            </el-form-item>
          </el-form>
          <div class="row">
            <el-button size="small" type="primary" @click="saveAsset">保存</el-button>
            <el-button size="small" type="danger" @click="removeAsset">删除资产</el-button>
          </div>
        </div>

        <div class="card">
          <h3>被引用的镜头（{{ (cur.shots || []).length }}）</h3>
          <div v-if="cur.shots && cur.shots.length" class="timeline">
            <span v-for="s in cur.shots" :key="s.id" class="tl-chip">
              <a class="link" @click="goShot(s)">第{{ s.episode_number }}集 {{ s.shot_code }}</a>
            </span>
          </div>
          <div v-else class="muted tiny">还没有镜头引用这个资产。</div>
        </div>
      </div>
    </el-drawer>

    <!-- 新建/编辑 -->
    <el-dialog v-model="showEdit" :title="eForm.id ? '编辑资产' : '新建资产'" width="520px">
      <el-form label-width="88px" size="small">
        <el-form-item label="名称"><el-input v-model="eForm.name" /></el-form-item>
        <el-form-item label="类型">
          <el-select v-model="eForm.asset_type" style="width:150px">
            <el-option v-for="t in TYPES" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="别名">
          <el-input v-model="eForm.aliasText" placeholder="逗号分隔" />
        </el-form-item>
        <el-form-item label="锁定句">
          <el-input v-model="eForm.lock_sentence" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEdit = false">取消</el-button>
        <el-button type="primary" @click="createAsset">保存</el-button>
      </template>
    </el-dialog>

    <!-- 覆盖度 -->
    <el-dialog v-model="showCov" title="资产覆盖度" width="620px">
      <div v-if="cov">
        <div class="mb8">
          <span class="pill gray">共 {{ cov.total }}</span>
          <span class="pill err" v-if="cov.missing_images.length">{{ cov.missing_images.length }} 个缺参考图</span>
          <span class="pill ok" v-else>全部有图</span>
        </div>
        <el-table border stripe :data="cov.assets" size="small" max-height="420">
          <el-table-column prop="name" label="资产" min-width="150" />
          <el-table-column label="类型" width="80">
            <template #default="{ row }">{{ typeLabel(row.asset_type) }}</template>
          </el-table-column>
          <el-table-column prop="image_count" label="参考图" width="76" />
          <el-table-column prop="shot_count" label="引用镜头" width="84" />
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <span :class="row.needs_image ? 'pill err' : 'pill ok'">{{ row.needs_image ? '缺图' : 'OK' }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-dialog>

    <MediaPicker v-model="picker" :project-id="pid" kind="image" @picked="onPicked" />

    <ElImageViewer
      v-if="previewIndex >= 0"
      :url-list="previewList"
      :initial-index="previewIndex"
      :hide-on-click-modal="true"
      teleported
      @close="previewIndex = -1"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, ElImageViewer } from 'element-plus'
import { api, fileUrl, thumbUrl } from '../api'
import MediaPicker from '../components/MediaPicker.vue'

const route = useRoute()
const router = useRouter()
const pid = Number(route.params.pid)

const TYPES = [
  { value: 'character', label: '角色' },
  { value: 'scene', label: '场景' },
  { value: 'prop', label: '道具' },
  { value: 'costume', label: '服装' },
  { value: 'style', label: '风格' },
]

const assets = ref([])
const type = ref('')
const q = ref('')
const onlyMissing = ref(false)
const loading = ref(false)
const scanning = ref(false)
const showDetail = ref(false)
const cur = ref(null)

// 点参考图看大图：详情里整组可左右翻，封面就单张
const previewIndex = ref(-1)
const previewList = ref([])
function openPreview(urls, i = 0) {
  const list = (urls || []).filter(Boolean)
  previewList.value = list
  previewIndex.value = list.length ? Math.max(0, Math.min(i, list.length - 1)) : -1
}
function openAssetImage(im) {
  const list = (cur.value?.images || []).filter((x) => isImage(x.file_name))
  openPreview(list.map((x) => fileUrl(x.file_path)), list.findIndex((x) => x.id === im.id))
}
const form = ref({})
const showEdit = ref(false)
const eForm = ref({})
const showCov = ref(false)
const cov = ref(null)
const covLoading = ref(false)
const picker = ref(false)
const projectName = ref('')

const filtered = computed(() =>
  assets.value.filter((a) => {
    if (type.value && a.asset_type !== type.value) return false
    if (onlyMissing.value && a.images.length) return false
    if (q.value) {
      const hay = `${a.name} ${(a.aliases || []).join(' ')}`
      if (!hay.toLowerCase().includes(q.value.toLowerCase())) return false
    }
    return true
  }),
)

function countOf(t) { return assets.value.filter((a) => a.asset_type === t).length }
function typeLabel(t) { return (TYPES.find((x) => x.value === t) || {}).label || t }
function isImage(n) { return /\.(jpg|jpeg|png|webp|bmp|gif)$/i.test(n || '') }
function cover(a) {
  const p = a.images.find((i) => i.is_primary) || a.images[0]
  return p ? p.file_path : null
}

async function load() {
  loading.value = true
  try {
    assets.value = await api.assets(pid, type.value || undefined)
  } finally {
    loading.value = false
  }
}

async function open(a) {
  cur.value = await api.asset(a.id)
  form.value = {
    name: cur.value.name,
    asset_type: cur.value.asset_type,
    aliasText: (cur.value.aliases || []).join(', '),
    lock_sentence: cur.value.lock_sentence || '',
    description: cur.value.description || '',
    voice_id: cur.value.voice_id || '',
    quality_level: cur.value.quality_level || 'MEDIUM',
  }
  showDetail.value = true
}

async function saveAsset() {
  const aliases = form.value.aliasText.split(/[,，]/).map((s) => s.trim()).filter(Boolean)
  await api.patchAsset(cur.value.id, {
    name: form.value.name,
    asset_type: form.value.asset_type,
    alias: aliases,
    lock_sentence: form.value.lock_sentence || null,
    description: form.value.description || null,
    voice_id: form.value.voice_id || null,
    quality_level: form.value.quality_level,
  })
  ElMessage.success('已保存')
  await load()
  await open({ id: cur.value.id })
}

async function removeAsset() {
  await ElMessageBox.confirm(`删除资产「${cur.value.name}」？已引用它的镜头槽位会失去关联。`, '确认', { type: 'warning' })
  await api.deleteAsset(cur.value.id)
  showDetail.value = false
  ElMessage.success('已删除')
  await load()
}

async function setPrimary(im) {
  await api.addAssetImage(cur.value.asset_id || cur.value.id, {
    file_path: im.file_path,
    file_name: im.file_name,
    usage_kind: im.usage_kind || 'reference',
    view_angle: im.view_angle,
    take_note: im.take_note,
    is_primary: true,
  })
  await open({ id: cur.value.id })
}
async function removeImage(im) {
  await api.deleteAssetImage(cur.value.id, im.id)
  await open({ id: cur.value.id })
}
async function onPicked(path) {
  await api.addAssetImage(cur.value.id, { file_path: path, usage_kind: 'reference' })
  ElMessage.success('已添加参考图')
  await load()
  await open({ id: cur.value.id })
}

// ---- 上传本机图片 ----
const fileInput = ref(null)
const SUFFIX = {
  character: '角色参考图', costume: '服装参考图',
  scene: '场景参考图', prop: '道具参考图', style: '风格参考图',
}

function pickUpload() {
  fileInput.value.value = ''
  fileInput.value.click()
}

async function doUpload(e) {
  const f = e.target.files && e.target.files[0]
  if (!f) return
  const ext = (f.name.match(/\.[^.]+$/) || [''])[0]
  const t = cur.value?.asset_type || 'character'
  const guess = `${cur.value?.name || ''}_${SUFFIX[t] || '参考图'}${ext}`

  let saveAs = guess
  try {
    const r = await ElMessageBox.prompt(
      '存到项目素材目录，文件名按项目约定拼好，可改。',
      '上传参考图', { inputValue: guess, confirmButtonText: '上传', cancelButtonText: '取消' },
    )
    saveAs = (r.value || guess).trim() || guess
  } catch {
    return
  }

  const fd = new FormData()
  fd.append('file', f, f.name)
  fd.append('save_as', saveAs)
  fd.append('usage_kind', 'reference')
  const res = await api.uploadAssetImage(cur.value.id, fd)
  ElMessage.success(res.reused ? `目录里已有一张同样的，直接挂上了：${res.file_name}` : `已上传到 ${res.dir}`)
  await load()
  await open({ id: cur.value.id })
}

function editAsset(a) {
  eForm.value = a
    ? { ...a, aliasText: (a.aliases || []).join(', ') }
    : { name: '', asset_type: 'character', aliasText: '', lock_sentence: '' }
  showEdit.value = true
}
async function createAsset() {
  const f = eForm.value
  if (!f.name) return ElMessage.warning('请填名称')
  const aliases = f.aliasText.split(/[,，]/).map((s) => s.trim()).filter(Boolean)
  await api.createAsset(pid, {
    name: f.name,
    asset_type: f.asset_type,
    alias: aliases.length ? aliases : null,
    lock_sentence: f.lock_sentence || null,
  })
  ElMessage.success('已新建')
  showEdit.value = false
  await load()
}

async function scan() {
  scanning.value = true
  try {
    const r = await api.scanAssets(pid)
    ElMessage.success(`扫到 ${r.scanned} 个参考图，新建资产 ${r.assets_created}，补图 ${r.assets_touched}`)
    await load()
  } finally {
    scanning.value = false
  }
}

async function showCoverage() {
  covLoading.value = true
  try {
    cov.value = await api.assetCoverage(pid)
    showCov.value = true
  } finally {
    covLoading.value = false
  }
}

function goShot(s) {
  showDetail.value = false
  router.push(`/p/${pid}/shot/${s.id}`)
}

async function loadProject() {
  try {
    const p = await api.project(pid)
    projectName.value = p?.name || ''
  } catch {
    projectName.value = ''
  }
}

onMounted(async () => {
  await Promise.all([loadProject(), load()])
})
</script>

<style scoped>
.proj-bar {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  padding: 8px 12px; margin-bottom: 10px;
  background: #f7f8fa; border: 1px solid var(--border); border-radius: 6px;
}
.proj-bar .tiny { line-height: 1.5; }
.asset-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(154px, 1fr)); gap: 10px; }
.asset { border: 1px solid var(--border); border-radius: 6px; overflow: hidden; cursor: pointer; background: #fff; }
.asset:hover { border-color: var(--brand); }
.asset.warn { border-color: #f0cfcf; }
.asset .cover { height: 116px; background: #f2f3f5; display: flex; align-items: center; justify-content: center; }
.asset .cover img { width: 100%; height: 100%; object-fit: cover; }
.no-img { font-size: var(--fs-mini); color: #a8afc0; }
.no-img.small { display: block; height: 78px; display: flex; align-items: center; justify-content: center; }
.asset .info { padding: 6px 8px 8px; }
.asset .nm { font-size: var(--fs-sm); font-weight: 600; }
.link { color: var(--brand); cursor: pointer; }
.link.danger { color: var(--err); }
</style>
