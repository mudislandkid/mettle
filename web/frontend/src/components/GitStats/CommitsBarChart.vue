<script setup lang="ts">
import { ref, computed } from 'vue'
import { useTheme } from '@/composables/useTheme'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  GridComponent,
} from 'echarts/components'

// Register ECharts components
use([
  CanvasRenderer,
  BarChart,
  TitleComponent,
  TooltipComponent,
  GridComponent,
])

const { theme } = useTheme()

const props = defineProps<{
  monthlyCommits: Record<string, number>
  weeklyCommits: Record<string, number>
}>()

const viewMode = ref<'monthly' | 'weekly'>('monthly')

const option = computed(() => {
  const data = viewMode.value === 'monthly' ? props.monthlyCommits : props.weeklyCommits
  const periods = Object.keys(data).sort()
  const values = periods.map(p => data[p])

  if (periods.length === 0) {
    return {}
  }

  return {
    title: {
      text: viewMode.value === 'monthly' ? 'Commits Per Month' : 'Commits Per Week',
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 600,
      },
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow',
      },
      formatter: (params: any) => {
        const period = params[0].axisValue
        const count = params[0].value
        return `
          <div style="font-weight: 600; margin-bottom: 4px;">${period}</div>
          <div>Commits: <strong>${count}</strong></div>
        `
      },
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '10%',
      top: '20%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: periods,
      axisLabel: {
        rotate: 45,
      },
    },
    yAxis: {
      type: 'value',
      name: 'Commits',
    },
    series: [
      {
        name: 'Commits',
        type: 'bar',
        data: values,
        itemStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: '#6366f1' },
              { offset: 1, color: '#8b5cf6' },
            ],
          },
        },
        emphasis: {
          itemStyle: {
            color: '#4f46e5',
          },
        },
      },
    ],
  }
})
</script>

<template>
  <div class="bg-white rounded-lg border border-slate-200 p-4 dark:bg-slate-900 dark:border-slate-700">
    <!-- View toggle -->
    <div class="flex justify-center gap-2 mb-3">
      <button
        @click="viewMode = 'monthly'"
        :class="[
          'px-4 py-1.5 text-sm font-medium rounded-md transition-colors',
          viewMode === 'monthly'
            ? 'bg-indigo-600 text-white'
            : 'bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700'
        ]"
      >
        Monthly
      </button>
      <button
        @click="viewMode = 'weekly'"
        :class="[
          'px-4 py-1.5 text-sm font-medium rounded-md transition-colors',
          viewMode === 'weekly'
            ? 'bg-indigo-600 text-white'
            : 'bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700'
        ]"
      >
        Weekly
      </button>
    </div>

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
  height: 320px;
  width: 100%;
}
</style>
