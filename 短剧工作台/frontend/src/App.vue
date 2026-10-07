<template>
  <div class="app-wrapper">
    <!-- ============ 侧边栏 ============ -->
    <aside class="sidebar-container" :class="{ collapsed: isCollapse }">
      <div class="logo">
        <span v-if="!isCollapse">短剧生产工作台</span>
        <span v-else>ST</span>
      </div>

      <el-menu
        :default-active="activePath"
        :collapse="isCollapse"
        :collapse-transition="false"
        unique-opened
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
        @select="onSelect"
      >
        <el-menu-item index="/">
          <el-icon><Menu /></el-icon>
          <template #title>项目列表</template>
        </el-menu-item>
        <el-menu-item index="/tasks">
          <el-icon><List /></el-icon>
          <template #title>任务中心</template>
        </el-menu-item>
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <template #title>接口与设置</template>
        </el-menu-item>
      </el-menu>

    </aside>

    <!-- ============ 主区域 ============ -->
    <section class="main-container">
      <header class="navbar">
        <div class="navbar-left">
          <el-icon class="collapse-btn" @click="toggleCollapse">
            <Fold v-if="!isCollapse" />
            <Expand v-else />
          </el-icon>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">项目列表</el-breadcrumb-item>
            <el-breadcrumb-item
              v-if="pid && project"
              :to="{ path: `/p/${pid}/board?ep=1` }"
            >{{ project.name }}</el-breadcrumb-item>
            <el-breadcrumb-item v-if="title !== '项目列表'">{{ title }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <div class="navbar-right">
          <RunningTasks />
          <el-dropdown trigger="click" @command="setFs">
            <el-button size="small" text title="调整全站字号">
              <span style="font-weight: 600">Aa</span>
              <span style="margin-left: 6px">{{ fsLabel }}</span>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item v-for="o in FS_OPTIONS" :key="o.key" :command="o.key">
                  <div class="fs-pick">
                    <span class="t">{{ o.label }}{{ fsKey === o.key ? ' ·当前' : '' }}</span>
                    <span class="h">正文 {{ o.size }}</span>
                  </div>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <el-button size="small" text title="刷新" @click="refresh">
            <el-icon><Refresh /></el-icon>
          </el-button>
        </div>
      </header>

      <div class="app-main" :class="{ flush: $route.name === 'shot' }">
        <router-view :key="$route.fullPath" />
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from './api'
import RunningTasks from './components/RunningTasks.vue'

const route = useRoute()
const router = useRouter()
const projects = ref([])
const refreshKey = ref(0)

// ---------------- 侧边栏折叠 ----------------
const isCollapse = ref(localStorage.getItem('studio.sidebar') === 'collapsed')
function toggleCollapse() {
  isCollapse.value = !isCollapse.value
  try {
    localStorage.setItem('studio.sidebar', isCollapse.value ? 'collapsed' : 'open')
  } catch (e) { /* 隐私模式忽略 */ }
}

// ---------------- 字号档位 ----------------
// 字号本身由 styles.css 的 --fs-* 变量控制，这里只负责切档与记忆。
const FS_OPTIONS = [
  { key: 'compact', label: '紧凑', size: '13px' },
  { key: 'normal', label: '标准', size: '15px' },
  { key: 'large', label: '大', size: '16.5px' },
  { key: 'xlarge', label: '特大', size: '18px' },
]
const fsKey = ref(document.documentElement.dataset.fs || 'large')
const fsLabel = computed(
  () => FS_OPTIONS.find((o) => o.key === fsKey.value)?.label || '大',
)
function setFs(k) {
  fsKey.value = k
  document.documentElement.dataset.fs = k
  try { localStorage.setItem('studio.fontScale', k) } catch (e) { /* 隐私模式忽略 */ }
}

const pid = computed(() => {
  const v = route.params.pid
  return v ? Number(v) : null
})
const project = computed(() => projects.value.find((p) => p.id === pid.value) || null)

// 侧边栏高亮：分镜详情页归到「镜头看板」下
const activePath = computed(() => {
  if (!pid.value) return route.path
  if (['board', 'shot'].includes(route.name)) return `/p/${pid.value}/board`
  return route.path
})

// 标题只认路由 meta.title（router/index.js 里统一维护）
const title = computed(() => route.meta?.title || '短剧生产工作台')

function onSelect(index) {
  if (index !== route.path) router.push(index)
}

async function loadProjects() {
  projects.value = await api.projects()
}

async function refresh() {
  refreshKey.value++
  await loadProjects()
  window.dispatchEvent(new CustomEvent('studio-refresh'))
}

onMounted(loadProjects)
watch(() => route.params.pid, loadProjects)
</script>
