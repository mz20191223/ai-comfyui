<template>
  <div>
    <div class="table-wrapper">
      <div class="table-header">
        <span class="table-title">我的项目</span>
        <span class="table-tip">素材与文档仍在磁盘原处，工作台只做索引；点行进入镜头看板</span>
        <span class="spacer"></span>
        <el-button size="small" type="primary" @click="openNew">
          <el-icon><Plus /></el-icon> 新建项目
        </el-button>
      </div>
      <div v-if="!projects.length" class="empty">还没有项目。点「新建项目」开始，或直接建一个指向已有素材目录的项目。</div>
      <el-table v-else border stripe :data="projects" size="small" @row-click="openProject" style="cursor: pointer">
        <el-table-column prop="name" label="剧名" min-width="180">
          <template #default="{ row }">
            <b>{{ row.name }}</b>
            <div class="tiny muted">{{ row.genre || '—' }} · {{ row.aspect_ratio }} · {{ row.resolution }}</div>
          </template>
        </el-table-column>
        <el-table-column label="集数 / 镜头" width="110">
          <template #default="{ row }">{{ row.episode_count }} 集 / {{ row.shot_count }} 镜</template>
        </el-table-column>
        <el-table-column label="素材目录" min-width="260">
          <template #default="{ row }">
            <span class="tiny mono muted ellipsis" style="display:block">{{ row.workspace_dir }}</span>
          </template>
        </el-table-column>
        <el-table-column class-name="op-col" label-class-name="op-col" label="操作" width="340">
          <template #default="{ row }">
            <div class="op-row">
              <el-button size="small" type="primary" link @click.stop="openProject(row)">分集</el-button>
              <el-button size="small" type="primary" link @click.stop="openScript(row)">剧本</el-button>
              <el-button size="small" type="primary" link @click.stop="openAssets(row)">资产库</el-button>
              <el-button size="small" type="primary" link @click.stop="openTimeline(row)">合成</el-button>
              <el-button size="small" type="primary" link @click.stop="openEdit(row)">编辑</el-button>
              <el-button size="small" type="danger" link @click.stop="removeProject(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 新建项目 -->
    <el-dialog v-model="showNew" title="新建项目" width="620px">
      <el-form :model="form" label-width="110px" size="small">
        <el-form-item label="剧名" required>
          <el-input v-model="form.name" placeholder="例：凌晨两点，Bug 成精了" />
        </el-form-item>
        <el-form-item label="题材 / 风格">
          <el-select v-model="form.genre" placeholder="选一个题材，或直接输入新的" filterable allow-create
            default-first-option clearable style="width: 200px; margin-right: 8px">
            <el-option v-for="g in genreOptions(form.genre)" :key="g" :label="g" :value="g" />
          </el-select>
          <el-select v-model="form.visual_style" style="width: 160px">
            <el-option label="写实真人" value="live_action" />
            <el-option label="动漫" value="anime" />
            <el-option label="3D" value="3d" />
          </el-select>
        </el-form-item>
        <el-form-item label="规格">
          <el-select v-model="form.aspect_ratio" style="width: 120px; margin-right: 8px">
            <el-option label="竖屏 9:16" value="9:16" />
            <el-option label="横屏 16:9" value="16:9" />
            <el-option label="方形 1:1" value="1:1" />
          </el-select>
          <el-input-number v-model="form.fps" :min="12" :max="60" style="margin-right: 8px" />
          <el-input v-model="form.resolution" style="width: 130px" placeholder="768x1344" />
        </el-form-item>
        <el-form-item label="分镜文档目录">
          <el-input v-model="form.doc_dir" placeholder="留空则用「工作区/deepseek分镜」" />
        </el-form-item>
        <el-form-item label="分镜图目录">
          <el-input v-model="form.keyframe_dir" placeholder="留空则用「工作区/重制版/分镜图」" />
        </el-form-item>
        <el-form-item label="分镜视频目录">
          <el-input v-model="form.video_dir" placeholder="留空则用「工作区/重制版/分镜视频」" />
        </el-form-item>
        <el-form-item label="视频尾帧目录">
          <el-input v-model="form.tail_dir" placeholder="留空则用「工作区/重制版/分镜图/视频尾帧」" />
        </el-form-item>
        <el-form-item label="废弃产物目录">
          <el-input v-model="form.discard_dir" placeholder="留空则用「工作区/重制版/废弃内容」" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showNew = false">取消</el-button>
        <el-button type="primary" @click="doCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- 编辑项目 -->
    <el-dialog v-model="showEdit" title="编辑项目" width="620px">
      <el-form :model="editForm" label-width="110px" size="small">
        <el-form-item label="剧名" required>
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="题材 / 风格">
          <el-select v-model="editForm.genre" placeholder="选一个题材，或直接输入新的" filterable allow-create
            default-first-option clearable style="width: 200px; margin-right: 8px">
            <el-option v-for="g in genreOptions(editForm.genre)" :key="g" :label="g" :value="g" />
          </el-select>
          <el-select v-model="editForm.visual_style" style="width: 160px">
            <el-option label="写实真人" value="live_action" />
            <el-option label="动漫" value="anime" />
            <el-option label="3D" value="3d" />
          </el-select>
        </el-form-item>
        <el-form-item label="规格">
          <el-select v-model="editForm.aspect_ratio" style="width: 120px; margin-right: 8px">
            <el-option label="竖屏 9:16" value="9:16" />
            <el-option label="横屏 16:9" value="16:9" />
            <el-option label="方形 1:1" value="1:1" />
          </el-select>
          <el-input-number v-model="editForm.fps" :min="12" :max="60" style="margin-right: 8px" />
          <el-input v-model="editForm.resolution" style="width: 130px" />
        </el-form-item>
        <el-form-item label="分镜文档目录">
          <el-input v-model="editForm.doc_dir" placeholder="留空则用「工作区/deepseek分镜」" />
        </el-form-item>
        <el-form-item label="分镜图目录">
          <el-input v-model="editForm.keyframe_dir" placeholder="留空则用「工作区/重制版/分镜图」" />
        </el-form-item>
        <el-form-item label="分镜视频目录">
          <el-input v-model="editForm.video_dir" placeholder="留空则用「工作区/重制版/分镜视频」" />
        </el-form-item>
        <el-form-item label="视频尾帧目录">
          <el-input v-model="editForm.tail_dir" placeholder="留空则用「工作区/重制版/分镜图/视频尾帧」" />
        </el-form-item>
        <el-form-item label="废弃产物目录">
          <el-input v-model="editForm.discard_dir" placeholder="留空则用「工作区/重制版/废弃内容」" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEdit = false">取消</el-button>
        <el-button type="primary" @click="doEdit">保存</el-button>
      </template>
    </el-dialog>

  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api'
import { genreOptions } from '../constants'

const router = useRouter()
const projects = ref([])
const showNew = ref(false)

const form = ref({
  name: '',
  genre: '',
  visual_style: 'live_action',
  aspect_ratio: '9:16',
  fps: 24,
  resolution: '768x1344',
  doc_dir: '',
  keyframe_dir: '',
  video_dir: '',
  tail_dir: '',
  discard_dir: '',
})

const showEdit = ref(false)
const editId = ref(null)
const editForm = ref({
  name: '',
  genre: '',
  visual_style: 'live_action',
  aspect_ratio: '9:16',
  fps: 24,
  resolution: '768x1344',
  doc_dir: '',
  keyframe_dir: '',
  video_dir: '',
  tail_dir: '',
  discard_dir: '',
})

function openEdit(row) {
  editId.value = row.id
  editForm.value = {
    name: row.name || '',
    genre: row.genre || '',
    visual_style: row.visual_style || 'live_action',
    aspect_ratio: row.aspect_ratio || '9:16',
    fps: row.fps || 24,
    resolution: row.resolution || '768x1344',
    doc_dir: row.doc_dir || '',
    keyframe_dir: row.keyframe_dir || '',
    video_dir: row.video_dir || '',
    tail_dir: row.tail_dir || '',
    discard_dir: row.discard_dir || '',
  }
  showEdit.value = true
}

async function doEdit() {
  if (!editForm.value.name.trim()) return ElMessage.warning('请填剧名')
  await api.patchProject(editId.value, { ...editForm.value })
  ElMessage.success('项目已更新')
  showEdit.value = false
  await load()
}

async function load() {
  projects.value = await api.projects()
}

function openNew() {
  showNew.value = true
}

async function doCreate() {
  if (!form.value.name.trim()) return ElMessage.warning('请填剧名')
  const p = await api.createProject(form.value)
  ElMessage.success('项目已创建')
  showNew.value = false
  await load()
  openProject(p)
}

function openProject(row) {
  router.push(`/p/${row.id}/board?ep=1`)
}

function openScript(row) {
  router.push(`/p/${row.id}/script`)
}

function openAssets(row) {
  router.push(`/p/${row.id}/assets`)
}

function openTimeline(row) {
  router.push(`/p/${row.id}/timeline`)
}

async function removeProject(row) {
  await ElMessageBox.confirm(
    `删除项目「${row.name}」？只删工作台里的记录，磁盘素材与文档不受影响。`,
    '确认删除',
    { type: 'warning' },
  )
  await api.deleteProject(row.id)
  ElMessage.success('已删除')
  await load()
}

onMounted(load)
</script>
