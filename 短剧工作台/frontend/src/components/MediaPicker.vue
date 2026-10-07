<template>
  <el-dialog
    :model-value="modelValue"
    title="选择素材"
    width="880px"
    top="6vh"
    append-to-body
    @update:model-value="(v) => emit('update:modelValue', v)"
  >
    <div class="row mb8">
      <el-input v-model="dir" size="small" placeholder="素材目录" style="flex:1" @keyup.enter="browse" />
      <el-button size="small" @click="browse">浏览</el-button>
      <el-select v-model="quickDir" size="small" placeholder="快捷目录" style="width:200px" @change="useQuick">
        <el-option v-for="r in roots" :key="r.path" :label="r.name" :value="r.path" />
      </el-select>
    </div>
    <div class="row mb8">
      <el-input v-model="searchName" size="small" placeholder="按文件名搜索（支持模糊）" style="flex:1" @keyup.enter="doSearch" />
      <el-button size="small" @click="doSearch">搜索</el-button>
      <el-radio-group v-model="kindFilter" size="small" @change="reload">
        <el-radio-button value="image">图片</el-radio-button>
        <el-radio-button value="video">视频</el-radio-button>
        <el-radio-button value="audio">音频</el-radio-button>
        <el-radio-button value="">全部</el-radio-button>
      </el-radio-group>
    </div>
    <div class="thumb-grid" style="max-height:460px;overflow:auto">
      <div
        v-for="f in files"
        :key="f.path"
        class="thumb"
        :class="{ sel: picked === f.path }"
        @click="picked = f.path"
        @dblclick="confirm(f)"
      >
        <img v-if="f.kind === 'image'" :src="thumbUrl(f.path, 160)" loading="lazy" />
        <div v-else class="file-ph">{{ f.kind }}</div>
        <div class="cap ellipsis" :title="f.name">{{ f.name }}</div>
      </div>
      <div v-if="!files.length" class="empty" style="width:100%">该目录下没有符合条件的文件</div>
    </div>
    <div class="tiny muted mt8">
      双击直接选中；也可单击后在下方确认。<span v-if="hint">{{ hint }}</span>
    </div>
    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :disabled="!picked" @click="confirm(null)">使用选中文件</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { api, thumbUrl } from '../api'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  projectId: { type: Number, default: null },
  kind: { type: String, default: 'image' },
})
const emit = defineEmits(['update:modelValue', 'picked'])

const roots = ref([])
const dir = ref('')
const quickDir = ref('')
const files = ref([])
const picked = ref(null)
const kindFilter = ref(props.kind)
const searchName = ref('')
const hint = ref('')

async function loadRoots() {
  roots.value = await api.mediaRoots(props.projectId)
  if (!dir.value && roots.value.length) {
    // 首屏落到与类型匹配的目录：音频 → 音频目录，其余 → 分镜图目录
    const want = props.kind === 'audio' ? /音频$/ : /分镜图$/
    const kf = roots.value.find((r) => want.test(r.name)) || roots.value[0]
    dir.value = kf.path
    quickDir.value = kf.path
    await browse()
  }
}
async function useQuick(p) {
  dir.value = p
  await browse()
}
async function browse() {
  if (!dir.value) return
  searchName.value = ''
  const r = await api.browse(dir.value, kindFilter.value || undefined)
  files.value = r.items.filter((x) => !x.is_dir)
}
async function doSearch() {
  if (!searchName.value.trim()) return browse()
  files.value = await api.searchMedia(searchName.value, kindFilter.value || undefined)
}
function reload() {
  if (searchName.value.trim()) doSearch()
  else browse()
}
async function confirm(f) {
  const p = f ? f.path : picked.value
  if (!p) return
  hint.value = ''
  try {
    const c = await api.classify(p)
    hint.value = `识别为：${c.guess_asset_type} / ${c.guess_asset_name}${c.shot_code_guess ? ` · 镜号 ${c.shot_code_guess}` : ''}`
  } catch (e) { /* ignore */ }
  emit('picked', p)
  emit('update:modelValue', false)
}

onMounted(() => { if (props.modelValue) loadRoots() })
watch(() => props.modelValue, (v) => { if (v && !roots.value.length) loadRoots() })
</script>

<style scoped>
.file-ph { height: 78px; display: flex; align-items: center; justify-content: center; background: #f2f3f5; color: #8a93a8; font-size: var(--fs-mini); }
</style>
