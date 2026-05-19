<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import type { Tag } from '@/types'

const props = defineProps<{
  params: {
    value: Tag[]
    data: { id: number }
    allTags?: Tag[]
    onAddTag?: (projectId: number, tagId: number) => void
    onRemoveTag?: (projectId: number, tagId: number) => void
    onCreateTag?: (name: string) => Promise<Tag | null>
  }
}>()

const showDropdown = ref(false)
const newTagName = ref('')
const containerRef = ref<HTMLElement | null>(null)

function handleClickOutside(event: MouseEvent) {
  if (!showDropdown.value) return
  const target = event.target as Node | null
  if (target && containerRef.value && !containerRef.value.contains(target)) {
    showDropdown.value = false
  }
}

function handleEscape(event: KeyboardEvent) {
  if (event.key === 'Escape') showDropdown.value = false
}

onMounted(() => {
  document.addEventListener('mousedown', handleClickOutside)
  document.addEventListener('keydown', handleEscape)
})

onBeforeUnmount(() => {
  document.removeEventListener('mousedown', handleClickOutside)
  document.removeEventListener('keydown', handleEscape)
})

const currentTags = computed(() => props.params.value || [])
const allTags = computed(() => props.params.allTags || [])

const availableTags = computed(() =>
  allTags.value.filter(t => !currentTags.value.find(ct => ct.id === t.id))
)

function addTag(tag: Tag) {
  if (props.params.onAddTag) {
    props.params.onAddTag(props.params.data.id, tag.id)
  }
}

function removeTag(tagId: number) {
  if (props.params.onRemoveTag) {
    props.params.onRemoveTag(props.params.data.id, tagId)
  }
}

async function createAndAddTag() {
  if (!newTagName.value.trim() || !props.params.onCreateTag || !props.params.onAddTag) return

  const newTag = await props.params.onCreateTag(newTagName.value.trim())
  if (newTag) {
    props.params.onAddTag(props.params.data.id, newTag.id)
    newTagName.value = ''
  }
}
</script>

<template>
  <div ref="containerRef" class="relative h-full flex items-center">
    <!-- Current tags -->
    <div class="flex flex-wrap gap-1">
      <span
        v-for="tag in currentTags"
        :key="tag.id"
        class="px-1.5 py-0.5 text-xs rounded-full text-white flex items-center gap-1"
        :style="{ backgroundColor: tag.color }"
      >
        {{ tag.name }}
        <button
          @click.stop="removeTag(tag.id)"
          class="hover:bg-white/20 rounded-full p-0.5"
        >
          <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </span>
    </div>

    <!-- Add button -->
    <button
      @click="showDropdown = !showDropdown"
      class="ml-1 p-1 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded dark:text-slate-500 dark:text-slate-400 dark:bg-slate-800"
    >
      <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
      </svg>
    </button>

    <!-- Dropdown -->
    <div
      v-if="showDropdown"
      class="absolute top-full left-0 z-50 mt-1 bg-white border border-slate-200 rounded-md shadow-lg min-w-[180px] dark:bg-slate-900 dark:border-slate-700"
    >
      <!-- Existing tags -->
      <ul v-if="availableTags.length" class="py-1 border-b border-slate-100 dark:border-slate-800">
        <li
          v-for="tag in availableTags"
          :key="tag.id"
          @click="addTag(tag)"
          class="px-3 py-1.5 text-sm cursor-pointer hover:bg-slate-100 flex items-center gap-2 dark:bg-slate-800"
        >
          <span
            class="w-3 h-3 rounded-full"
            :style="{ backgroundColor: tag.color }"
          ></span>
          <span>{{ tag.name }}</span>
        </li>
      </ul>

      <!-- Create new tag -->
      <div class="p-2">
        <div class="flex gap-1">
          <input
            v-model="newTagName"
            type="text"
            placeholder="New tag..."
            class="flex-1 px-2 py-1 text-sm border border-slate-200 rounded dark:border-slate-700"
            @keydown.enter="createAndAddTag"
          />
          <button
            @click="createAndAddTag"
            :disabled="!newTagName.trim()"
            class="px-2 py-1 text-sm bg-indigo-600 text-white rounded disabled:bg-slate-300 dark:bg-slate-600"
          >
            +
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
