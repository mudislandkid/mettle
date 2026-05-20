<script setup lang="ts">
withDefaults(defineProps<{
  percent: number
  label?: string
}>(), {
  label: '%',
})
</script>

<template>
  <div class="relative shrink-0 w-32 h-32">
    <svg viewBox="0 0 120 120" class="w-32 h-32">
      <defs>
        <linearGradient id="ring-grad" x1="0" x2="1" y1="0" y2="1">
          <stop offset="0%" stop-color="#818cf8" />
          <stop offset="100%" stop-color="#60a5fa" />
        </linearGradient>
      </defs>
      <!-- Track -->
      <circle cx="60" cy="60" r="52" fill="none" stroke="#1e293b" stroke-width="8" />
      <!-- Progress arc -->
      <circle
        cx="60" cy="60" r="52"
        fill="none"
        stroke="url(#ring-grad)"
        stroke-width="8"
        stroke-linecap="round"
        :stroke-dasharray="`${(percent / 100) * (2 * Math.PI * 52)} ${2 * Math.PI * 52}`"
        transform="rotate(-90 60 60)"
        style="transition: stroke-dasharray 400ms ease-out"
      />
    </svg>
    <!-- Centre label -->
    <div class="absolute inset-0 flex flex-col items-center justify-center">
      <div class="text-[28px] font-semibold tabular-nums text-slate-100 leading-none">
        {{ percent }}<span class="text-slate-500 text-[16px]">{{ label }}</span>
      </div>
      <div class="text-[10px] uppercase tracking-[0.12em] text-slate-500 mt-1">complete</div>
    </div>
  </div>
</template>
