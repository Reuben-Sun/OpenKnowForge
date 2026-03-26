<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { withBase } from 'vitepress'

type NoteItem = {
  slug?: string
  title: string
  date?: string
  created_at?: string
  updated_at?: string
  submitted_at?: string
  tags?: string[]
  link: string
}

const notes = ref<NoteItem[]>([])
const loading = ref(true)
const error = ref('')

const POLL_INTERVAL_MS = 2500
let pollTimer: number | undefined

function parseTs(value?: string): number {
  if (!value) {
    return 0
  }
  const parsed = Date.parse(value)
  return Number.isNaN(parsed) ? 0 : parsed
}

const sortedNotes = computed(() => {
  return [...notes.value].sort((a, b) => {
    const aTs = parseTs(a.updated_at || a.date)
    const bTs = parseTs(b.updated_at || b.date)
    return bTs - aTs
  })
})

function resolveLink(link: string): string {
  if (link.startsWith('http://') || link.startsWith('https://')) {
    return link
  }
  if (link.startsWith('/')) {
    return withBase(link)
  }
  return withBase(`/notes/${link.replace(/^\.\//, '')}`)
}

async function loadNotes(isInitial: boolean): Promise<void> {
  const candidates = Array.from(
    new Set([
      withBase('/search-index.json'),
      withBase('/.vitepress/public/search-index.json'),
      '/search-index.json',
      '/.vitepress/public/search-index.json'
    ])
  )

  for (const candidate of candidates) {
    try {
      const response = await fetch(candidate, { cache: 'no-store' })
      if (!response.ok) {
        continue
      }
      const payload = await response.json()
      notes.value = Array.isArray(payload?.notes) ? payload.notes : []
      error.value = ''
      return
    } catch {
      continue
    }
  }

  if (isInitial) {
    error.value = 'Failed to load search index. Check docs/public/search-index.json.'
  }
}

onMounted(async () => {
  await loadNotes(true)
  loading.value = false

  pollTimer = window.setInterval(() => {
    void loadNotes(false)
  }, POLL_INTERVAL_MS)
})

onBeforeUnmount(() => {
  if (pollTimer !== undefined) {
    window.clearInterval(pollTimer)
  }
})
</script>

<template>
  <p v-if="loading">Loading notes...</p>
  <p v-else-if="error" class="note-cards-error">{{ error }}</p>
  <p v-else-if="sortedNotes.length === 0">No notes yet.</p>

  <div v-if="!loading && !error && sortedNotes.length > 0" class="notes-cards">
    <a v-for="note in sortedNotes" :key="`${note.link}-${note.updated_at || note.date}`" class="note-card" :href="resolveLink(note.link)">
      <h3>{{ note.title }}</h3>
      <p class="note-card__time">Last Edited: {{ note.updated_at || note.date || 'unknown' }}</p>
      <p class="note-card__time">Created: {{ note.created_at || 'unknown' }}</p>
      <div class="note-card__tags">
        <span v-for="tag in note.tags || []" :key="`${note.link}-${tag}`" class="note-card__tag">#{{ tag }}</span>
      </div>
    </a>
  </div>
</template>

<style scoped>
.note-cards-error {
  color: #b91c1c;
}

.dark .note-cards-error {
  color: #fca5a5;
}
</style>
