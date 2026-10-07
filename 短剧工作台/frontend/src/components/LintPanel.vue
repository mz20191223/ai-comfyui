<template>
  <div>
    <div v-if="loading" class="tiny muted">检查中…</div>
    <template v-else>
      <div v-if="!hits.length && !problems.length" class="tiny" style="color:#16a34a">✓ 全部检查通过</div>
      <div v-for="(h, i) in hits" :key="'l' + i" class="lint-item" :class="h.severity">
        <div class="msg"><b>{{ h.label }}</b> · {{ h.message }}</div>
        <div class="ev" v-if="h.evidence">{{ h.evidence }}</div>
        <div class="ev" v-if="h.suggestion">→ {{ h.suggestion }}</div>
      </div>
      <div v-for="(p, i) in problems" :key="'p' + i" class="lint-item warn">
        <div class="msg">{{ p.message }}</div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { api } from '../api'

const props = defineProps({
  shotId: { type: Number, required: true },
  stage: { type: String, default: 'video' },
  auto: { type: Boolean, default: true },
  trigger: { type: Number, default: 0 },
})

const hits = ref([])
const problems = ref([])
const loading = ref(false)

async function run() {
  loading.value = true
  try {
    const r = await api.lintShot(props.shotId, props.stage)
    hits.value = r.hits || []
    try {
      const a = await api.audit(props.shotId)
      problems.value = (a.materials && a.materials.problems) || []
    } catch (e) {
      problems.value = []
    }
  } finally {
    loading.value = false
  }
}

watch(() => [props.shotId, props.trigger], () => { if (props.auto) run() }, { immediate: true })
</script>
