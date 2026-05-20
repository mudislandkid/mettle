<script setup lang="ts">
import type { SecretMatch } from '@/types'

defineProps<{
  open: boolean
  projectName: string
  matches: SecretMatch[]
}>()

const emit = defineEmits<{ (e: 'close'): void }>()

const severityClass = (sev: string): string =>
  sev === 'high'
    ? 'text-red-300 bg-red-900/50 border-red-700'
    : 'text-amber-300 bg-amber-900/50 border-amber-700'

const friendlyKind = (kind: string): string => ({
  aws_access_key_id: 'AWS access key',
  aws_secret_access_key: 'AWS secret key',
  github_pat_classic: 'GitHub PAT',
  github_pat_fine: 'GitHub PAT (fine-grained)',
  openai_api_key: 'OpenAI API key',
  anthropic_api_key: 'Anthropic API key',
  jwt: 'JWT',
  rsa_private_key: 'Private key',
  generic_high_entropy: 'High-entropy assignment',
}[kind] ?? kind)
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-40 bg-black/50"
      @click="emit('close')"
    />
    <aside
      v-if="open"
      class="fixed top-0 right-0 z-50 h-full w-full max-w-md overflow-y-auto bg-zinc-900 border-l border-zinc-700 shadow-2xl"
      role="dialog"
      aria-modal="true"
      :aria-label="`Secrets in ${projectName}`"
    >
      <header class="flex items-center justify-between px-5 py-4 border-b border-zinc-800">
        <div>
          <h2 class="text-base font-semibold text-zinc-100">Potential secrets</h2>
          <p class="text-xs text-zinc-400 mt-0.5">{{ projectName }}</p>
        </div>
        <button @click="emit('close')" aria-label="Close" class="text-zinc-500 hover:text-zinc-200 text-xl leading-none">&times;</button>
      </header>

      <div class="px-5 py-3 text-xs text-zinc-400 border-b border-zinc-800/50">
        Regex-based; verify before acting. Snippet content not stored.
      </div>

      <ul class="divide-y divide-zinc-800/50">
        <li v-for="(m, i) in matches" :key="i" class="px-5 py-3">
          <div class="flex items-center gap-2 mb-1">
            <span
              class="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded border"
              :class="severityClass(m.severity)"
            >{{ m.severity }}</span>
            <span class="text-sm text-zinc-200">{{ friendlyKind(m.kind) }}</span>
          </div>
          <div class="font-mono text-xs text-zinc-400 break-all">
            {{ m.file }}<span class="text-zinc-600">:</span>{{ m.line }}
          </div>
          <div class="font-mono text-[10px] text-zinc-600 mt-0.5">
            sha256: {{ m.snippet_hash }}
          </div>
        </li>
      </ul>
    </aside>
  </Teleport>
</template>
