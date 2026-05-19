<script setup lang="ts">
import { computed } from 'vue'
import { useTheme } from '@/composables/useTheme'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { HeatmapChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  CalendarComponent,
  VisualMapComponent,
} from 'echarts/components'

// Register ECharts components
use([
  CanvasRenderer,
  HeatmapChart,
  TitleComponent,
  TooltipComponent,
  CalendarComponent,
  VisualMapComponent,
])

const { theme } = useTheme()

const props = defineProps<{
  heatmapData: [string, number][]
}>()

const option = computed(() => {
  if (!props.heatmapData || props.heatmapData.length === 0) {
    return {}
  }

  // Get actual date range from data
  const dates = props.heatmapData.map(d => d[0]).sort()
  const startDate = dates[0]
  const endDate = dates[dates.length - 1]

  // Calculate max commits for color scale
  const maxCommits = Math.max(...props.heatmapData.map(d => d[1]))

  return {
    title: {
      text: 'Commit Activity',
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 600,
      },
    },
    tooltip: {
      formatter: (params: any) => {
        const date = params.value[0]
        const commits = params.value[1]
        return `
          <div style="font-weight: 600; margin-bottom: 4px;">${date}</div>
          <div>${commits} commit${commits !== 1 ? 's' : ''}</div>
        `
      },
    },
    visualMap: {
      min: 0,
      max: maxCommits,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      top: 40,
      inRange: {
        color: ['#ebedf0', '#9be9a8', '#40c463', '#30a14e', '#216e39'],
      },
      text: ['High', 'Low'],
      textStyle: {
        fontSize: 12,
      },
    },
    calendar: [
      {
        range: [startDate, endDate],
        top: 120,
        left: 40,
        right: 20,
        cellSize: ['auto', 13],
        yearLabel: {
          show: true,
          fontSize: 14,
          fontWeight: 600,
        },
        dayLabel: {
          firstDay: 1,
          nameMap: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
        },
        monthLabel: {
          nameMap: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
          fontSize: 12,
        },
        splitLine: {
          show: true,
          lineStyle: {
            color: '#e5e7eb',
            width: 1,
          },
        },
        itemStyle: {
          borderWidth: 2,
          borderColor: '#fff',
        },
      },
    ],
    series: [
      {
        type: 'heatmap',
        coordinateSystem: 'calendar',
        data: props.heatmapData,
      },
    ],
  }
})
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
  min-height: 350px;
}

@media (max-width: 768px) {
  .chart {
    height: 300px;
    min-height: 300px;
  }
}
</style>
