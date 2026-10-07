<template>
  <div class="running" v-if="running.length" @click="$router.push('/tasks')" title="有任务在跑，点击查看任务中心">
    <span class="dot run"></span>
    <span>{{ running.length }} 个任务进行中</span>
  </div>
  <div v-else-if="failed" class="running failed" @click="$router.push('/tasks')" title="有任务失败">
    <span class="dot err"></span>
    <span>{{ failed }} 个失败</span>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { api } from '../api'

const running = ref([])
const failed = ref(0)
let timer = null

async function poll() {
  try {
    const s = await api.taskStats()
    const bs = s.by_status || {}
    running.value = (bs.pending || 0) + (bs.running || 0)
      ? Array((bs.pending || 0) + (bs.running || 0)).fill(1)
      : []
    failed.value = bs.failed || 0
  } catch (e) {
    /* 静默 */
  }
}

onMounted(() => {
  poll()
  timer = setInterval(poll, 4000)
})
onUnmounted(() => timer && clearInterval(timer))
</script>

<style scoped>
.running {
  display: flex; align-items: center; gap: 6px; font-size: var(--fs-sm); color: #2563eb;
  cursor: pointer; padding: 3px 9px; background: #e8effd; border-radius: 11px;
}
.running.failed { color: #dc2626; background: #fdeaea; }
</style>
