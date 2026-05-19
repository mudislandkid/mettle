<script setup lang="ts">
import { computed } from 'vue'
import { useTheme } from '@/composables/useTheme'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
} from 'echarts/components'
import type { AuthorStats } from '@/types'

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent, LegendComponent, TitleComponent])

const { theme } = useTheme()

const props = defineProps<{
  authors: AuthorStats[]
}>()

const option = computed(() => {
  // Stacked horizontal bar: lines added (positive) + lines deleted (also positive),
  // displayed as two series so users can see proportion at a glance.
  const names = props.authors.map((a) => a.author)
  const added = props.authors.map((a) => a.lines_added)
  const deleted = props.authors.map((a) => a.lines_deleted)
  const commits = props.authors.map((a) => a.commits)

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: unknown) => {
        const arr = params as Array<{ seriesName: string; value: number; dataIndex: number }>
        if (!arr.length) return ''
        const idx = arr[0].dataIndex
        const a = props.authors[idx]
        return `<div style="font-weight:600;margin-bottom:4px">${a.author}</div>` +
          `Commits: <b>${a.commits.toLocaleString()}</b><br/>` +
          `+${a.lines_added.toLocaleString()} / -${a.lines_deleted.toLocaleString()}<br/>` +
          `Net: ${a.net_lines.toLocaleString()}<br/>` +
          `<span style="color:#94a3b8">First: ${new Date(a.first_commit_date).toLocaleDateString()}</span><br/>` +
          `<span style="color:#94a3b8">Last: ${new Date(a.last_commit_date).toLocaleDateString()}</span>`
      },
    },
    legend: { data: ['Lines added', 'Lines deleted', 'Commits'], top: 0 },
    grid: { left: 120, right: 60, top: 40, bottom: 30, containLabel: true },
    xAxis: { type: 'value' },
    yAxis: {
      type: 'category',
      data: names,
      inverse: true,
      axisLabel: { fontFamily: 'inherit' },
    },
    series: [
      {
        name: 'Lines added',
        type: 'bar',
        stack: 'churn',
        data: added,
        itemStyle: { color: '#10b981' },
      },
      {
        name: 'Lines deleted',
        type: 'bar',
        stack: 'churn',
        data: deleted,
        itemStyle: { color: '#ef4444' },
      },
      {
        name: 'Commits',
        type: 'bar',
        data: commits,
        itemStyle: { color: '#6366f1' },
        xAxisIndex: 0,
        // Render commits on a secondary, smaller-scale axis so a 200x churn
        // value doesn't squash the commit bars to invisibility.
        yAxisIndex: 0,
        barGap: '20%',
      },
    ],
  }
})
</script>

<template>
  <div class="bg-white rounded-lg border border-slate-200 p-4 dark:bg-slate-900 dark:border-slate-700">
    <div class="flex items-baseline justify-between mb-2">
      <h3 class="text-sm font-semibold text-slate-900 dark:text-slate-100">Top contributors</h3>
      <span class="text-xs text-slate-500 dark:text-slate-400">{{ authors.length }} authors shown</span>
    </div>
    <div v-if="authors.length === 0" class="text-sm text-slate-500 py-8 text-center dark:text-slate-400">
      No author data available.
    </div>
    <v-chart :theme="theme === 'dark' ? 'dark' : ''" v-else :option="option" :autoresize="true" class="chart" />
  </div>
</template>

<style scoped>
.chart {
  height: 380px;
}
</style>
