<template>
  <svg :width="w" :height="h" viewBox="0 0 90 160" role="img">
    <defs>
      <marker :id="head" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="4.5" markerHeight="4.5"
              orient="auto-start-reverse">
        <path d="M2 1L8 5L2 9" fill="none" stroke="#a86a10" stroke-width="1.8"
              stroke-linecap="round" stroke-linejoin="round" />
      </marker>
    </defs>

    <rect x="0.5" y="0.5" width="89" height="159" rx="4" fill="#fff" stroke="#c8ccd6" />

    <!-- 地面 -->
    <line x1="9" y1="134" x2="81" y2="134" stroke="#c8ccd6" stroke-width="1" />

    <!-- 相机（侧视）：机身 / 镜头 / 三脚架 -->
    <g stroke="#333" stroke-width="1.3" fill="#fff" stroke-linejoin="round">
      <rect x="20" y="96" width="27" height="16" rx="2" />
      <rect x="25" y="90" width="10" height="6" rx="1" />
      <rect x="47" y="101" width="9" height="6" fill="#333" />
    </g>
    <g stroke="#8a93a8" stroke-width="1.2" fill="none" stroke-linecap="round">
      <path d="M34 112 L25 134" />
      <path d="M34 112 L43 134" />
      <path d="M34 112 L34 134" />
    </g>

    <!-- 运镜示意 -->
    <g v-if="mode !== 'static'" stroke="#a86a10" stroke-width="1.7" fill="none" stroke-linecap="round">
      <path v-for="(d, i) in paths" :key="i" :d="d" :marker-end="ends[i] ? `url(#${head})` : null"
            :marker-start="starts[i] ? `url(#${head})` : null" />
    </g>

    <!-- 固定机位：脚架落地标记 -->
    <path v-if="movement === 'STATIC'" d="M34 134 L28 143 L40 143 Z" fill="#8a93a8" />

    <!-- 跟移：轨道 + 滑动块 -->
    <g v-if="movement === 'TRACK'">
      <line x1="8" y1="62" x2="82" y2="62" stroke="#c8ccd6" stroke-width="1" />
      <circle cx="26" cy="62" r="3.6" fill="#333" />
    </g>
  </svg>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  movement: { type: String, default: '' },
  w: { type: Number, default: 20 },
  h: { type: Number, default: 36 },
})

let seq = 0
const head = `mv${++seq}_${Math.random().toString(36).slice(2, 7)}`

// mode: static / move / rotate / zoom / sway
const mode = computed(() => {
  const m = props.movement
  if (!m || m === 'STATIC') return 'static'
  if (m === 'PAN' || m === 'TILT') return 'rotate'
  if (m === 'ZOOM_IN' || m === 'ZOOM_OUT') return 'zoom'
  if (m === 'HANDHELD' || m === 'STEADICAM') return 'sway'
  return 'move'
})

// 每条线的两端是否带箭头
const ends = computed(() => pathsDef.value.map((p) => !!p.e))
const starts = computed(() => pathsDef.value.map((p) => !!p.s))
const paths = computed(() => pathsDef.value.map((p) => p.d))

const pathsDef = computed(() => {
  switch (props.movement) {
    case 'PAN': // 相机不动，左右摇
      return [{ d: 'M4.6 87 A34 34 0 0 1 63.4 87', e: true, s: true }]
    case 'TILT': // 相机不动，上下摇
      return [{ d: 'M76 60 L76 120', e: true, s: true }]
    case 'DOLLY_IN': // 向主体推进
      return [{ d: 'M10 56 L72 56', e: true }]
    case 'DOLLY_OUT': // 远离主体
      return [{ d: 'M78 56 L14 56', e: true }]
    case 'TRACK': // 沿轨道横向跟移
      return [{ d: 'M34 62 L76 62', e: true }]
    case 'CRANE': // 整机升降
      return [{ d: 'M34 86 L34 26', e: true }]
    case 'HANDHELD': // 手持：抖动前进
      return [{ d: 'M10 60 l 11 -7 l 11 13 l 11 -13 l 11 13 l 11 -7', e: true }]
    case 'STEADICAM': // 稳定器：平滑滑行
      return [{ d: 'M8 62 q 13 -17 24 0 q 11 17 24 0 q 10 -13 22 -5', e: true }]
    case 'ZOOM_IN': // 焦距变长，取景锥收窄
      return [{ d: 'M56 84 L84 99' }, { d: 'M56 124 L84 109' }]
    case 'ZOOM_OUT': // 焦距变短，取景锥张开
      return [{ d: 'M56 99 L84 84' }, { d: 'M56 109 L84 124' }]
    default:
      return []
  }
})
</script>
