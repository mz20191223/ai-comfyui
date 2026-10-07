<template>
  <div>
    <input
      ref="fileInput"
      type="file"
      accept="image/*,video/*,audio/*"
      style="display:none"
      @change="onLocalFile"
    />
    <div class="ref-grid">
      <div v-for="r in valid" :key="r.id" class="tile" :title="r.file_name">
        <div class="tile-img">
          <img
            v-if="r.resolved_path && isImage(r.resolved_path)"
            :src="thumbUrl(r.resolved_path, 240)"
            loading="lazy"
            title="点击看大图"
            @click="openPreview(r)"
          />
          <div v-else class="tile-ph">文件</div>
          <span class="badge">{{ slotLabel(r) }}</span>
        </div>
        <div class="tile-name ellipsis">{{ r.file_name }}</div>
        <div class="tile-bar">
          <template v-if="isFirstFrame(r)">
            <slot name="first-ops" />
            <button type="button" title="这张图取什么（这句会写进提示词）" @click.stop="editNote(r)">
              <el-icon><EditPen /></el-icon>
            </button>
          </template>
          <template v-else>
            <button type="button" title="换一张图" @click.stop="pick(r)">
              <el-icon><Switch /></el-icon>
            </button>
            <button type="button" title="这张图取什么（这句会写进提示词）" @click.stop="editNote(r)">
              <el-icon><EditPen /></el-icon>
            </button>
            <button type="button" class="del" title="移除这个参考图槽位" @click.stop="remove(r)">
              <el-icon><Delete /></el-icon>
            </button>
          </template>
        </div>
      </div>
      <div v-if="!atMax" class="tile add-tile" title="添加参考图" @click="pick(null)">＋</div>
    </div>

    <div v-if="invalid.length" class="bad-box">
      <a class="lnk" @click="showBad = !showBad">
        ⚠ {{ invalid.length }} 条引用解析不到文件，出片时会被判为幽灵引用
        {{ showBad ? '▴' : '▾' }}
      </a>
      <div v-if="showBad" class="bad-list">
        <div v-for="r in invalid" :key="r.id" class="bad-row">
          <span class="idx-mini">{{ slotLabel(r) }}</span>
          <span class="mono ellipsis" style="flex:1">{{ r.file_name || '—' }}</span>
          <a v-if="isFirstFrame(r)" class="lnk tiny" @click="emit('pickFirst')">重新选一张</a>
          <el-button v-else size="small" text type="danger" @click="remove(r)">删掉</el-button>
        </div>
        <div class="tiny muted" style="margin-top:6px">
          多半是导入时把说明文字当成了文件名（如「分镜图」「（不传）」）。删掉后重新挂正确的文件。
        </div>
      </div>
    </div>

    <el-dialog v-model="showPicker" title="选择素材" width="860px" top="6vh" append-to-body>
      <div class="row mb8">
        <el-input v-model="dir" size="small" placeholder="素材目录" style="flex:1" @keyup.enter="browse" />
        <el-button size="small" @click="browse">浏览</el-button>
        <el-button size="small" type="primary" plain @click="pickLocal">从本地上传</el-button>
        <el-select v-model="quickDir" size="small" placeholder="快捷目录" style="width: 180px" @change="useQuick">
          <el-option v-for="r in roots" :key="r.path" :label="r.name" :value="r.path" />
        </el-select>
      </div>
      <div class="row mb8">
        <el-input v-model="searchName" size="small" placeholder="按文件名搜索（支持模糊）" style="flex:1" @keyup.enter="doSearch" />
        <el-button size="small" @click="doSearch">搜索</el-button>
        <el-radio-group v-model="kindFilter" size="small" @change="browse">
          <el-radio-button value="image">图片</el-radio-button>
          <el-radio-button value="video">视频</el-radio-button>
          <el-radio-button value="audio">音频</el-radio-button>
          <el-radio-button value="">全部</el-radio-button>
        </el-radio-group>
      </div>
      <div class="thumb-grid" style="max-height: 460px; overflow: auto">
        <div
          v-for="f in files"
          :key="f.path"
          class="thumb"
          :class="{ sel: picked === f.path }"
          @click="picked = f.path"
          @dblclick="confirmPick(f)"
        >
          <img v-if="f.kind === 'image'" :src="thumbUrl(f.path, 160)" loading="lazy" />
          <div v-else class="file-ph">{{ f.kind }}</div>
          <div class="cap ellipsis" :title="f.name">{{ f.name }}</div>
        </div>
      </div>
      <div class="tiny muted mt8">
        双击直接选中。选中后会让你写一句「取什么 / 不取什么」，那句才会进提示词。
        <span v-if="classifyHint" style="margin-left:8px">{{ classifyHint }}</span>
      </div>
      <div class="tiny muted mt8">
        「从本地上传」会把电脑里的文件存进上面「素材目录」指向的文件夹，存好后照常选它。
      </div>
      <template #footer>
        <el-button @click="showPicker = false">取消</el-button>
        <el-button type="primary" :disabled="!picked" @click="confirmPick(null)">使用选中文件</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showNote" title="这张图取什么" width="520px" append-to-body>
      <div class="tiny muted mb8">{{ pendingFile }}</div>
      <el-input
        v-model="takeNote"
        type="textarea"
        :rows="3"
        placeholder="例：仅取死循环妖的完全体形态、造型与色调；严禁其满屏错误窗口海背景"
      />
      <div class="mt8">
        <el-radio-group v-model="role" size="small">
          <el-radio-button v-for="r in roleOptions" :key="r" :value="r" />
        </el-radio-group>
      </div>
      <div class="tiny muted mt8">这句话会原样写进提示词，模型会照着执行。</div>
      <template #footer>
        <el-button @click="showNote = false">取消</el-button>
        <el-button type="primary" @click="doSave">保存</el-button>
      </template>
    </el-dialog>

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
import { ElMessage, ElMessageBox, ElImageViewer } from 'element-plus'
import { Delete, EditPen, Switch } from '@element-plus/icons-vue'
import { api, fileUrl, thumbUrl } from '../api'

const props = defineProps({
  refs: { type: Array, default: () => [] },
  shotId: { type: Number, required: true },
  side: { type: String, default: 'video' },
  projectId: { type: Number, default: null },
})
const emit = defineEmits(['changed', 'pickFirst'])

const showPicker = ref(false)
const showNote = ref(false)
const showBad = ref(false)
const roots = ref([])
const dir = ref('')
const quickDir = ref('')
const files = ref([])
const picked = ref(null)
const kindFilter = ref('image')
const searchName = ref('')
const classifyHint = ref('')
const takeNote = ref('')
const role = ref('')
const pendingFile = ref('')
const editingRef = ref(null)
const fileInput = ref(null)

const valid = computed(() => props.refs.filter((r) => r.file_exists && !r.is_placeholder))
const invalid = computed(() => props.refs.filter((r) => !r.file_exists || r.is_placeholder))

// GPT 生图最多传 4 张，分镜图侧（side=image）限制到 4 个槽位
const IMAGE_MAX = 4
const atMax = computed(() => props.side === 'image' && valid.value.length >= IMAGE_MAX)

const roleOptions = [
  '首帧锚点', '尾帧锚点', '构图锚点', '形态锚点', '人形形态锚点',
  '仅取色调', '仅取形态', '环境参考', '音色参考',
]

function isImage(p) {
  return /\.(jpg|jpeg|png|webp|bmp|gif)$/i.test(p || '')
}

// 点参考图看大图：列表收本组能解析到真文件的图片槽位，弹层里可左右翻看全部
const imgRefs = computed(() => valid.value.filter((r) => r.resolved_path && isImage(r.resolved_path)))
const previewIndex = ref(-1)
const previewList = computed(() => imgRefs.value.map((r) => fileUrl(r.resolved_path)))
function openPreview(r) {
  const i = imgRefs.value.findIndex((x) => x.id === r.id)
  if (i >= 0) previewIndex.value = i
}
// 视频侧第 0 号槽位（ref_image_0 / Image 1）。调用视频模型时它会被当作画面起始参考，
// 但不在这里贴「首帧 / 尾帧」标签：文件名带 _tail 或排在第 1 位都不代表用户想表达首尾帧，
// 自动贴标经常是错的，反而误导。它由 shots 表的首帧状态管理，这里只展示、只让改「用途」；
// 换图的按钮由父组件经 #first-ops 插槽塞进来，免得两处各写一套、和 shot_frames 说不一致。
// 徽标上的编号＝提示词里会写的那一个号。两侧槽位基数不同，不能统一 +1：
// 视频侧 slot 0 起（Image 1 = ref_image_0，模型参数口径），分镜图侧 slot 1 起
// （参考图1 = 上传的第 1 张）。这套基数是导入器/生成器写死的（md_storyboard_parser 用
// len(items)+1、md_video_parser 用 0 起），改这里只影响显示，不动数据。
function slotLabel(r) {
  const n = Number(r.slot_index)
  return String(props.side === 'image' ? n : n + 1)
}

function isFirstFrame(r) {
  return props.side === 'video' && Number(r.slot_index) === 0
}

// 只改「取什么」那句话，不重新挑文件
function editNote(r) {
  editingRef.value = r
  pendingFile.value = r.file_name || ''
  takeNote.value = r.take_note || ''
  role.value = r.role || ''
  classifyHint.value = ''
  showNote.value = true
}

async function loadRoots() {
  roots.value = await api.mediaRoots(props.projectId)
  if (!dir.value && roots.value.length) {
    const kf = roots.value.find((r) => /分镜图$/.test(r.name))
    dir.value = (kf || roots.value[0]).path
    browse()
  }
}

async function useQuick(p) {
  dir.value = p
  await browse()
}

async function browse() {
  if (!dir.value) return
  const r = await api.browse(dir.value, kindFilter.value || undefined)
  files.value = r.items.filter((x) => !x.is_dir)
}

async function doSearch() {
  if (!searchName.value.trim()) return browse()
  files.value = await api.searchMedia(searchName.value, kindFilter.value || undefined)
}

function pick(r) {
  editingRef.value = r
  classifyHint.value = ''
  showPicker.value = true
  if (!roots.value.length) loadRoots()
}

// ---- 从本地上传：存进当前浏览的目录，然后当作刚选中的文件继续走 ----
function pickLocal() {
  if (!dir.value) {
    ElMessage.warning('先在上面选一个「素材目录」，上传的文件会存到那里')
    return
  }
  fileInput.value.value = ''
  fileInput.value.click()
}

async function onLocalFile(e) {
  const f = e.target.files && e.target.files[0]
  if (!f) return
  const fd = new FormData()
  fd.append('file', f, f.name)
  try {
    const r = await api.mediaUpload(fd, { dest_dir: dir.value, project_id: props.projectId })
    ElMessage.success(`已上传到 ${dir.value}，接着写一句「这张图取什么」`)
    await browse()
    picked.value = r.path
    await confirmPick({ path: r.path, name: r.name || f.name })
  } catch (err) {
    /* 已提示 */
  }
}

async function confirmPick(f) {
  const p = f ? f.path : picked.value
  if (!p) return
  showPicker.value = false
  pendingFile.value = p
  if (editingRef.value) {
    takeNote.value = editingRef.value.take_note || ''
    role.value = editingRef.value.role || ''
  } else {
    takeNote.value = ''
    role.value = ''
  }
  try {
    const c = await api.classify(p)
    classifyHint.value = `识别为：${c.guess_asset_type} / ${c.guess_asset_name}`
  } catch (e) { /* ignore */ }
  showNote.value = true
}

async function doSave() {
  const name = pendingFile.value.split(/[\\/]/).pop()
  await api.upsertRef(props.shotId, {
    target_side: props.side,
    slot_index: editingRef.value ? editingRef.value.slot_index : null,
    file_name: name,
    take_note: takeNote.value,
    role: role.value,
  })
  showNote.value = false
  ElMessage.success('已保存参考图槽位')
  emit('changed')
}

async function remove(r) {
  await ElMessageBox.confirm(`移除参考图 ${r.file_name}？`, '确认', { type: 'warning' })
  await api.deleteRef(props.shotId, r.id)
  ElMessage.success('已移除')
  emit('changed')
}

onMounted(() => { if (showPicker.value) loadRoots() })
</script>

<style scoped>
/* 横向排列的缩略图网格：一屏能看完全部参考图 */
.ref-grid { display: flex; flex-wrap: wrap; gap: 8px; }
.tile { width: 88px; }
.tile-img {
  position: relative; width: 88px; height: 64px; border-radius: 5px;
  overflow: hidden; border: 1px solid var(--border); background: #f2f3f5;
}
.tile-img img { width: 100%; height: 100%; object-fit: cover; display: block; cursor: zoom-in; }
.tile-ph {
  width: 100%; height: 100%; display: flex; align-items: center; justify-content: center;
  color: #8a93a8; font-size: var(--fs-mini);
}
.badge {
  position: absolute; left: 3px; top: 3px; min-width: 13px; height: 13px; line-height: 13px;
  padding: 0 3px; border-radius: 3px; background: rgba(0, 0, 0, 0.55); color: #fff;
  font-size: 10px; text-align: center;
}
/* 操作不再靠 hover 遮罩（那会把「点图看大图」吃掉），固定在图片下方一排小图标 */
.tile-bar { display: flex; gap: 4px; margin-top: 4px; }
.tile-bar button {
  display: inline-flex; align-items: center; justify-content: center;
  width: 22px; height: 22px; padding: 0; border-radius: 4px;
  border: 1px solid var(--border); background: #fff; color: #5b6478;
  font-size: 14px; cursor: pointer; line-height: 1;
}
.tile-bar button:hover { border-color: var(--el-color-primary); color: var(--el-color-primary); }
.tile-bar button.del { color: #c0392b; }
.tile-bar button.del:hover { border-color: #c0392b; background: #fdecec; }
/* 父组件经 #first-ops 插槽塞进来的按钮（如「选择上一镜尾帧」）沿用同一套小图标样式 */
.tile-bar :slotted(button) {
  display: inline-flex; align-items: center; justify-content: center;
  width: 22px; height: 22px; padding: 0; border-radius: 4px;
  border: 1px solid var(--border); background: #fff; color: #5b6478;
  font-size: 14px; cursor: pointer; line-height: 1;
}
.tile-bar :slotted(button:hover) { border-color: var(--el-color-primary); color: var(--el-color-primary); }
.tile-name { font-size: var(--fs-mini); margin-top: 3px; color: #5b6478; }

/* 末尾的空槽：直接点它上传，替代原来的「＋ 添加」按钮行 */
.add-tile {
  width: 88px; height: 64px; border-radius: 5px;
  border: 1px dashed #c3cad6; background: #fafbfc;
  display: flex; align-items: center; justify-content: center;
  color: #8a93a8; font-size: 20px; cursor: pointer; margin-top: 3px;
}
.add-tile:hover { border-color: #6b4423; color: #6b4423; background: #fff; }

.bad-box { margin-top: 10px; padding: 6px 8px; border: 1px dashed #e6c9a8; border-radius: 6px; background: #fffaf3; }
.bad-list { margin-top: 6px; }
.bad-row { display: flex; align-items: center; gap: 8px; padding: 2px 0; }
.idx-mini { font-size: var(--fs-mini); color: #8a93a8; width: 16px; }
.lnk { font-size: var(--fs-mini); color: #6b4423; cursor: pointer; }
.lnk:hover { text-decoration: underline; }
.file-ph { height: 78px; display: flex; align-items: center; justify-content: center; background: #f2f3f5; color: #8a93a8; font-size: var(--fs-mini); }
</style>
