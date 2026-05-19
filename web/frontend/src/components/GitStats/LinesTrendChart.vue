<script setup lang="ts">
import { computed } from 'vue'
import { useTheme } from '@/composables/useTheme'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
} from 'echarts/components'
import type { GitCommitStats } from '@/types'

// Register ECharts components
use([
  CanvasRenderer,
  LineChart,
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
])

const { theme } = useTheme()

const props = defineProps<{
  commits: GitCommitStats[]
}>()

const option = computed(() => {
  if (!props.commits || props.commits.length === 0) {
    return {}
  }

  const dates = props.commits.map(c => c.date)
  const cumulativeLines = props.commits.map(c => c.cumulative_lines)
  const linesAdded = props.commits.map(c => c.lines_added)
  const linesDeleted = props.commits.map(c => c.lines_deleted)

  return {
    title: {
      text: 'Lines of Code Over Time',
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 600,
      },
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const date = params[0].axisValue
        const cumulative = params[0].value?.toLocaleString() || '0'
        const added = linesAdded[params[0].dataIndex]?.toLocaleString() || '0'
        const deleted = linesDeleted[params[0].dataIndex]?.toLocaleString() || '0'

        return `
          <div style="font-weight: 600; margin-bottom: 4px;">${date}</div>
          <div>Total Lines: <strong>${cumulative}</strong></div>
          <div style="color: #10b981;">Lines Added: ${added}</div>
          <div style="color: #ef4444;">Lines Deleted: ${deleted}</div>
        `
      },
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '10%',
      top: '15%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false,
      axisLabel: {
        rotate: 45,
        formatter: (value: string) => {
          // Show month and day for better readability
          const date = new Date(value)
          return `${date.getMonth() + 1}/${date.getDate()}`
        },
      },
    },
    yAxis: {
      type: 'value',
      name: 'Lines of Code',
      axisLabel: {
        formatter: (value: number) => {
          if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`
          if (value >= 1000) return `${(value / 1000).toFixed(1)}K`
          return value.toString()
        },
      },
    },
    series: [
      {
        name: 'Total Lines',
        type: 'line',
        data: cumulativeLines,
        smooth: true,
        showSymbol: false,
        lineStyle: {
          width: 2,
          color: '#6366f1',
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(99, 102, 241, 0.3)' },
              { offset: 1, color: 'rgba(99, 102, 241, 0.05)' },
            ],
          },
        },
      },
    ],
  }
})

// `:autoresize="true"` on <v-chart> already wires resize handling — the manual
// listener that used to live here leaked one handler per chart remount.
</script>

<template>
  <div class="bg-white rounded-lg border border-slate-200 p-4 dark:bg-slate-900 dark:border-slate-700">
    <v-chart
      :theme="theme === 'dark' ? 'dark' : ''"
      :option="option"
      :autoresize="true"
      class="chart"
    />
  </div>
</template>

<style scoped>
.chart {
  height: 350px;
  width: 100%;
}
</style>
