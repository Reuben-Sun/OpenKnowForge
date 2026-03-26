<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useData, useRoute, withBase } from 'vitepress'

type NoteItem = {
  link: string
  word_count?: number
  image_count?: number
}

const route = useRoute()
const { page } = useData()
const notes = ref<NoteItem[]>([])
const loading = ref(false)
const isEn = computed(() => route.path.startsWith('/en/'))

function stripLocalePrefix(value: string): string {
  if (value === '/en') {
    return '/'
  }
  if (value.startsWith('/en/')) {
    return value.slice(3)
  }
  return value
}

function normalizePath(value?: string): string {
  const raw = String(value || '').trim()
  if (!raw) {
    return '/'
  }
  const next = stripLocalePrefix(raw).replace(/\/+$/, '')
  return next || '/'
}

function isNoteDetailPath(value?: string): boolean {
  const normalized = normalizePath(value)
  return normalized.startsWith('/notes/entries/') && normalized !== '/notes/entries'
}

function toCount(value: unknown): number | undefined {
  const parsed = Number(value)
  if (!Number.isFinite(parsed) || parsed < 0) {
    return undefined
  }
  return Math.floor(parsed)
}

const enabled = computed(() => isNoteDetailPath(route.path))
const currentPath = computed(() => normalizePath(route.path))

const uiText = computed(() =>
  isEn.value
    ? {
        words: 'Words',
        images: 'Images'
      }
    : {
        words: '字数',
        images: '图片'
      }
)

const frontmatterStats = computed(() => {
  const frontmatter = page.value.frontmatter as Record<string, unknown> | undefined
  return {
    words: toCount(frontmatter?.word_count),
    images: toCount(frontmatter?.image_count)
  }
})

const noteFromIndex = computed<NoteItem | null>(() => {
  return notes.value.find((item) => normalizePath(item.link) === currentPath.value) || null
})

const stats = computed(() => {
  const fromIndex = noteFromIndex.value
  return {
    words: toCount(fromIndex?.word_count) ?? frontmatterStats.value.words ?? 0,
    images: toCount(fromIndex?.image_count) ?? frontmatterStats.value.images ?? 0
  }
})

async function loadNotes(): Promise<void> {
  if (!enabled.value) {
    notes.value = []
    return
  }

  loading.value = true
  const candidates = Array.from(
    new Set([
      withBase('/search-index.json'),
      withBase('/.vitepress/public/search-index.json'),
      '/search-index.json',
      '/.vitepress/public/search-index.json'
    ])
  )

  try {
    for (const candidate of candidates) {
      const response = await fetch(candidate, { cache: 'no-store' })
      if (!response.ok) {
        continue
      }
      const payload = await response.json()
      notes.value = Array.isArray(payload?.notes) ? payload.notes : []
      return
    }
    notes.value = []
  } catch {
    notes.value = []
  } finally {
    loading.value = false
  }
}

watch(
  () => route.path,
  () => {
    if (enabled.value) {
      void loadNotes()
    } else {
      notes.value = []
    }
  },
  { immediate: true }
)
</script>

<template>
  <div v-if="enabled" class="note-stats-bar">
    <span class="note-stats-bar__chip">
      <span class="note-stats-bar__label">{{ uiText.words }}</span>
      <strong class="note-stats-bar__value">{{ stats.words }}</strong>
    </span>
    <span class="note-stats-bar__chip">
      <span class="note-stats-bar__label">{{ uiText.images }}</span>
      <strong class="note-stats-bar__value">{{ stats.images }}</strong>
    </span>
    <span v-if="loading" class="note-stats-bar__loading">...</span>
  </div>
</template>

<style scoped>
.note-stats-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin: 0 0 14px;
}

.note-stats-bar__chip {
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
  border-radius: 999px;
  border: 1px solid var(--vp-c-divider);
  background: rgba(20, 184, 166, 0.08);
  padding: 5px 11px;
}

.note-stats-bar__label {
  color: var(--vp-c-text-2);
  font-size: 12px;
}

.note-stats-bar__value {
  color: var(--vp-c-text-1);
  font-size: 14px;
}

.note-stats-bar__loading {
  color: var(--vp-c-text-3);
  font-size: 12px;
}

.dark .note-stats-bar__chip {
  border-color: rgba(148, 163, 184, 0.32);
  background: rgba(15, 23, 42, 0.7);
}
</style>
