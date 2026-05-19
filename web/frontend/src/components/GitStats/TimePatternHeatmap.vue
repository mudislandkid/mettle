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
  GridComponent,
  VisualMapComponent,
} from 'echarts/components'
import type { TimePatterns } from '@/types'

// Register ECharts components
use([
  CanvasRenderer,
  HeatmapChart,
  TitleComponent,
  TooltipComponent,
  GridComponent,
  VisualMapComponent,
])

const { theme } = useTheme()

const props = defineProps<{
  timePatterns: TimePatterns
}>()

const option = computed(() => {
  const hours = Array.from({ length: 24 }, (_, i) => `${i.toString().padStart(2, '0')}:00`)
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

  // Calculate max for color scale
  const maxCommits = Math.max(...props.timePatterns.heatmap.map(d => d[2]), 1)

  return {
    title: {
      text: 'Commit Activity by Day and Hour',
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 600,
      },
    },
    tooltip: {
      position: 'top',
      formatter: (params: any) => {
        const day = days[params.value[1]]
        const hour = hours[params.value[0]]
        const count = params.value[2]
        return `
          <div style="font-weight: 600; margin-bottom: 4px;">${day} ${hour}</div>
          <div>${count} commit${count !== 1 ? 's' : ''}</div>
        `
      },
    },
    grid: {
      left: '10%',
      right: '10%',
      bottom: '15%',
      top: '15%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: hours,
      splitArea: {
        show: true,
      },
      axisLabel: {
        interval: 2,
        rotate: 45,
        fontSize: 11,
      },
      name: 'Hour of Day',
      nameLocation: 'middle',
      nameGap: 40,
      nameTextStyle: {
        fontSize: 13,
        fontWeight: 600,
      },
    },
    yAxis: {
      type: 'category',
      data: days,
      splitArea: {
        show: true,
      },
      axisLabel: {
        fontSize: 12,
      },
      name: 'Day of Week',
      nameLocation: 'middle',
      nameGap: 50,
      nameTextStyle: {
        fontSize: 13,
        fontWeight: 600,
      },
    },
    visualMap: {
      min: 0,
      max: maxCommits,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: '5%',
      inRange: {
        color: ['#ebedf0', '#c6e48b', '#7bc96f', '#239a3b', '#196127'],
      },
      text: ['High', 'Low'],
      textStyle: {
        fontSize: 12,
      },
    },
    series: [
      {
        name: 'Commits',
        type: 'heatmap',
        data: props.timePatterns.heatmap.map(([day, hour, count]) => [hour, day, count]),
        label: {
          show: false,
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowColor: 'rgba(0, 0, 0, 0.5)',
          },
        },
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
  height: 400px;
  width: 100%;
  min-height: 400px;
}

@media (max-width: 768px) {
  .chart {
    height: 350px;
    min-height: 350px;
  }
}
</style>
