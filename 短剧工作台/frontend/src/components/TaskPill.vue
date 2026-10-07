<template>
  <span v-if="!slot" class="muted tiny">—</span>
  <span v-else-if="slot.status === 'failed'" class="pill err" :title="slot.message || ''">
    {{ slot.fail_label || '失败' }}
  </span>
  <span v-else class="pill" :class="cls">
    {{ slot.label }}<template v-if="slot.status === 'running'"> {{ slot.progress }}%</template>
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  slot: { type: Object, default: null },
})

const cls = computed(
  () =>
    ({
      succeeded: 'ok',
      failed: 'err',
      running: 'run',
      submitted: 'gray',
      cancelled: 'gray',
    })[props.slot?.status] || 'gray',
)
</script>
