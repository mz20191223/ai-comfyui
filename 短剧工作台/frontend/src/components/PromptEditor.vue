<template>
  <div>
    <div class="pe-head">
      <slot name="title"></slot>
      <span class="tiny muted">{{ title }}</span>
      <span class="spacer" style="flex: 1"></span>
      <span v-if="dirty" class="pill warn">未保存</span>
      <slot name="tools"></slot>
      <el-button size="small" text @click="emit('reload')">重载</el-button>
      <el-button size="small" text @click="showRev = true">历史版本</el-button>
      <el-button size="small" text @click="copy">复制</el-button>
      <el-button size="small" type="primary" :disabled="!dirty" @click="save">保存</el-button>
    </div>
    <pre
      v-if="!editing"
      class="prompt"
      @dblclick="editing = true"
      @click="onBodyClick"
      v-html="rendered"
    ></pre>
    <textarea v-else class="prompt-edit" v-model="local" @blur="editing = false"></textarea>

    <el-drawer v-model="showRev" title="提示词版本历史" size="560px" append-to-body>
      <el-table border stripe :data="revs" size="small" @row-click="previewRev" style="cursor: pointer">
        <el-table-column prop="created_at" label="时间" width="150" />
        <el-table-column prop="note" label="说明" min-width="130" />
        <el-table-column prop="source" label="来源" width="80" />
        <el-table-column prop="size" label="长度" width="70" />
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button size="small" text type="primary" @click.stop="restore(row)">回滚</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="previewContent" class="mt12">
        <div class="tiny muted mb8">预览：</div>
        <pre class="prompt" style="max-height: 320px">{{ previewContent }}</pre>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api'

const props = defineProps({
  modelValue: { type: String, default: '' },
  title: { type: String, default: '' },
  targetKind: { type: String, required: true },
  targetId: { type: Number, required: true },
  // 镜头语言句（由镜头设置注入的那一段）。给了就在正文里标成可点，点了打开设置面板。
  wizardNote: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue', 'saved', 'reload', 'open-wizard'])

const local = ref(props.modelValue || '')
const dirty = ref(false)
const editing = ref(false)
const showRev = ref(false)
const revs = ref([])
const previewContent = ref('')

function esc(s) {
  return String(s).replace(
    /[&<>"]/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c],
  )
}

// 把镜头语言那句包成可点元素。只包第一处，避免正文里重复出现时到处可点。
const rendered = computed(() => {
  const body = esc(local.value || '（空）')
  const note = (props.wizardNote || '').trim()
  if (!note) return body
  const target = esc(note)
  const i = body.indexOf(target)
  if (i === -1) return body
  return (
    body.slice(0, i) +
    `<span class="wiz-link" title="镜头设置：点击调整景别 / 视角 / 主体位置">${target}</span>` +
    body.slice(i + target.length)
  )
})

function onBodyClick(e) {
  if (e.target && e.target.classList && e.target.classList.contains('wiz-link')) {
    emit('open-wizard')
  }
}

watch(() => props.modelValue, (v) => {
  local.value = v || ''
  dirty.value = false
})
watch(local, () => { dirty.value = true })

async function save() {
  const field = props.targetKind === 'shot_video' ? 'video_prompt' : 'image_prompt'
  await api.patchShot(props.targetId, { detail: { [field]: local.value }, note: '界面编辑' })
  dirty.value = false
  ElMessage.success('已保存（并留了一份版本快照）')
  emit('saved')
}

function copy() {
  navigator.clipboard.writeText(local.value || '')
  ElMessage.success('已复制到剪贴板')
}

async function loadRevs() {
  revs.value = await api.revisions(props.targetKind, props.targetId)
}

async function previewRev(row) {
  const r = await api.revision(row.id)
  previewContent.value = r.content
}

async function restore(row) {
  await ElMessageBox.confirm('用这个版本覆盖当前提示词？', '回滚确认', { type: 'warning' })
  await api.restoreRevision(row.id)
  emit('reload')
  ElMessage.success('已回滚')
  showRev.value = false
}

watch(showRev, (v) => v && loadRevs())

// 给父组件取「编辑器里此刻的文本」用（预览请求体要按你看到的算，含未保存的改动）
defineExpose({
  currentText: () => local.value || '',
  isDirty: () => dirty.value,
})
</script>

<style scoped>
.pe-head { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.prompt :deep(.wiz-link) {
  color: #2f6fd0;
  border-bottom: 1px dashed currentColor;
  cursor: pointer;
}
.prompt :deep(.wiz-link:hover) { background: #eef4fd; }
</style>
