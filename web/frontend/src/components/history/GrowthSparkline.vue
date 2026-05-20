<script setup lang="ts">
// GrowthSparkline.vue — SVG polyline showing total_lines trend.
// Stroke colour: emerald if growing, rose if shrinking, slate if flat/insufficient data.

const props = withDefaults(defineProps<{
  values: number[]
  width?: number
  height?: number
}>(), {
  width: 110,
  height: 32,
})

interface SparkPoint {
  x: number
  y: number
}

function computePoints(): SparkPoint[] {
  const { values, width, height } = props
  if (values.length < 2) return []
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = Math.max(1, max - min)
  const stepX = width / (values.length - 1)
  return values.map((v, i) => ({
    x: i * stepX,
    y: height - ((v - min) / range) * (height - 4) - 2,
  }))
}

function pointsString(pts: SparkPoint[]): string {
  return pts.map(p => `${p.x},${p.y}`).join(' ')
}

function areaPath(pts: SparkPoint[]): string {
  if (!pts.length) return ''
  const { width, height } = props
  const line = pts.map((p, i) => (i === 0 ? `M${p.x},${p.y}` : `L${p.x},${p.y}`)).join(' ')
  return `${line} L${width},${height} L0,${height} Z`
}

// Derive colour from last vs first
const trend = (() => {
  const v = props.values
  if (v.length < 2) return 'slate'
  const first = v[0]
  const last = v[v.length - 1]
  if (last > first) return 'emerald'
  if (last < first) return 'rose'
  return 'slate'
})()

const COLORS = {
  emerald: { stroke: '#6ee7b7', fill: 'rgba(16,185,129,0.18)' },
  rose:    { stroke: '#fda4af', fill: 'rgba(244,63,94,0.18)' },
  slate:   { stroke: '#94a3b8', fill: 'rgba(148,163,184,0.15)' },
} as const

const color = COLORS[trend as keyof typeof COLORS]
const pts = computePoints()
const last = pts[pts.length - 1]
</script>

<template>
  <svg
    v-if="pts.length >= 2"
    :viewBox="`0 0 ${width} ${height}`"
    :width="width"
    :height="height"
    class="overflow-visible"
  >
    <path :d="areaPath(pts)" :fill="color.fill" />
    <polyline
      :points="pointsString(pts)"
      fill="none"
      :stroke="color.stroke"
      stroke-width="1.5"
      stroke-linejoin="round"
      stroke-linecap="round"
    />
    <circle
      v-if="last"
      :cx="last.x"
      :cy="last.y"
      r="2"
      :fill="color.stroke"
    />
  </svg>
</template>
