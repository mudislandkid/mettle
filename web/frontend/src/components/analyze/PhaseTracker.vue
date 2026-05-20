<script setup lang="ts">
defineProps<{
  phase: string
}>()

const PHASES = [
  { id: 'discovering', label: 'Discover',  sub: 'Find project roots'       },
  { id: 'counting',    label: 'Count',     sub: 'Lines · files · langs'    },
  { id: 'analyzing',   label: 'Analyze',   sub: 'Complexity · TODOs'       },
  { id: 'finalizing',  label: 'Finalize',  sub: 'Health · secrets'         },
]

function phaseState(id: string, phase: string): 'done' | 'active' | 'todo' {
  const idx = PHASES.findIndex(p => p.id === phase)
  const i   = PHASES.findIndex(p => p.id === id)
  if (i < idx)  return 'done'
  if (i === idx) return 'active'
  return 'todo'
}
</script>

<template>
  <ol class="grid grid-cols-2 sm:grid-cols-4 gap-2">
    <li
      v-for="(p, i) in PHASES"
      :key="p.id"
      :class="[
        'relative rounded-lg ring-1 ring-inset px-3 py-2.5',
        phaseState(p.id, phase) === 'active' ? 'ring-indigo-500/40 bg-indigo-500/10'
          : phaseState(p.id, phase) === 'done'   ? 'ring-emerald-500/30 bg-emerald-500/5'
          : 'ring-slate-800 bg-slate-900/40'
      ]"
    >
      <div class="flex items-center gap-2">
        <!-- Step badge -->
        <span
          :class="[
            'shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold',
            phaseState(p.id, phase) === 'active' ? 'bg-indigo-500 text-slate-950'
              : phaseState(p.id, phase) === 'done'   ? 'bg-emerald-500 text-slate-950'
              : 'bg-slate-800 text-slate-500'
          ]"
        >
          <svg v-if="phaseState(p.id, phase) === 'done'" width="10" height="10" viewBox="0 0 16 16" fill="none">
            <path d="M3 8l3 3 7-7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <template v-else>{{ i + 1 }}</template>
        </span>

        <!-- Label -->
        <span
          :class="[
            'text-[12px] font-semibold',
            phaseState(p.id, phase) === 'todo' ? 'text-slate-500' : 'text-slate-100'
          ]"
        >{{ p.label }}</span>

        <!-- Active pulse bars -->
        <span
          v-if="phaseState(p.id, phase) === 'active'"
          class="ml-auto inline-flex gap-0.5 items-end h-3"
        >
          <span class="block w-[3px] bg-indigo-300 rounded-sm animate-phase-bar1" style="height:30%" />
          <span class="block w-[3px] bg-indigo-300 rounded-sm animate-phase-bar2" style="height:70%" />
          <span class="block w-[3px] bg-indigo-300 rounded-sm animate-phase-bar3" style="height:100%" />
        </span>
      </div>

      <div class="text-[10.5px] text-slate-500 mt-0.5 pl-7">{{ p.sub }}</div>
    </li>
  </ol>
</template>

<style scoped>
@keyframes phasePulse {
  0%, 100% { opacity: 0.4; transform: scaleY(0.6); }
  50%       { opacity: 1;   transform: scaleY(1);   }
}
.animate-phase-bar1 { animation: phasePulse 1s ease-in-out infinite; animation-delay: 0ms;   }
.animate-phase-bar2 { animation: phasePulse 1s ease-in-out infinite; animation-delay: 150ms; }
.animate-phase-bar3 { animation: phasePulse 1s ease-in-out infinite; animation-delay: 300ms; }
</style>
