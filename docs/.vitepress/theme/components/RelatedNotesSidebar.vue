<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter, withBase } from 'vitepress'

type NoteItem = {
  slug?: string
  title: string
  date?: string
  updated_at?: string
  tags?: string[]
  link: string
}

type RelatedNote = NoteItem & {
  overlap: number
}

const route = useRoute()
const router = useRouter()
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

function parseTs(value?: string): number {
  if (!value) {
    return 0
  }
  const parsed = Date.parse(value)
  return Number.isNaN(parsed) ? 0 : parsed
}

function normalizeTag(value: string): string {
  return value.trim().toLowerCase()
}

function resolveLink(link: string): string {
  if (link.startsWith('http://') || link.startsWith('https://')) {
    return link
  }
  if (link.startsWith('/')) {
    if (isEn.value && (link === '/notes' || link.startsWith('/notes/'))) {
      return withBase(`/en${link}`)
    }
    return withBase(link)
  }
  const normalized = `/notes/${link.replace(/^\.\//, '')}`
  if (isEn.value) {
    return withBase(`/en${normalized}`)
  }
  return withBase(normalized)
}

function onLinkClick(event: MouseEvent, link: string): void {
  if (
    event.defaultPrevented ||
    event.button !== 0 ||
    event.metaKey ||
    event.ctrlKey ||
    event.shiftKey ||
    event.altKey
  ) {
    return
  }
  event.preventDefault()
  void router.go(resolveLink(link))
}

const enabled = computed(() => isNoteDetailPath(route.path))

const currentPath = computed(() => normalizePath(route.path))

const uiText = computed(() =>
  isEn.value
    ? {
        title: 'Related Notes',
        loading: 'Loading...',
        notIndexed: 'Current note is not indexed yet.',
        noTag: 'Current note has no tags.',
        empty: 'No notes with overlapping tags.'
      }
    : {
        title: '相关笔记',
        loading: '加载中...',
        notIndexed: '当前笔记尚未进入索引。',
        noTag: '当前笔记没有标签。',
        empty: '没有找到标签重叠的笔记。'
      }
)

const currentNote = computed<NoteItem | null>(() => {
  if (!enabled.value) {
    return null
  }
  return notes.value.find((item) => normalizePath(item.link) === currentPath.value) || null
})

const relatedNotes = computed<RelatedNote[]>(() => {
  const current = currentNote.value
  if (!current) {
    return []
  }

  const currentTags = (current.tags || []).map(normalizeTag).filter(Boolean)
  if (currentTags.length === 0) {
    return []
  }
  const tagSet = new Set(currentTags)

  return notes.value
    .filter((item) => normalizePath(item.link) !== currentPath.value)
    .map((item) => {
      const overlap = (item.tags || []).map(normalizeTag).filter((tag) => tagSet.has(tag)).length
      return {
        ...item,
        overlap
      }
    })
    .filter((item) => item.overlap > 0)
    .sort((a, b) => {
      if (b.overlap !== a.overlap) {
        return b.overlap - a.overlap
      }
      const timeDelta = parseTs(b.updated_at || b.date) - parseTs(a.updated_at || a.date)
      if (timeDelta !== 0) {
        return timeDelta
      }
      return a.title.localeCompare(b.title)
    })
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
  () => enabled.value,
  (value) => {
    if (value) {
      void loadNotes()
    } else {
      notes.value = []
    }
  },
  { immediate: true }
)

watch(
  () => route.path,
  () => {
    if (enabled.value) {
      void loadNotes()
    }
  }
)
</script>

<template>
  <section v-if="enabled" class="related-notes-panel">
    <p class="related-notes-panel__title">{{ uiText.title }}</p>
    <p v-if="loading" class="related-notes-panel__meta">{{ uiText.loading }}</p>
    <p v-else-if="!currentNote" class="related-notes-panel__meta">{{ uiText.notIndexed }}</p>
    <p v-else-if="(currentNote.tags || []).length === 0" class="related-notes-panel__meta">{{ uiText.noTag }}</p>
    <ul v-else-if="relatedNotes.length > 0" class="related-notes-panel__list">
      <li v-for="note in relatedNotes" :key="`${note.link}-${note.overlap}`" class="related-notes-panel__item">
        <a
          :href="resolveLink(note.link)"
          class="related-notes-panel__link"
          @click="onLinkClick($event, note.link)"
        >
          {{ note.title }}
        </a>
      </li>
    </ul>
    <p v-else class="related-notes-panel__meta">{{ uiText.empty }}</p>
  </section>
</template>

<style scoped>
.related-notes-panel {
  margin-top: 18px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 14px;
  padding: 14px;
  background: linear-gradient(170deg, rgba(255, 255, 255, 0.88), rgba(240, 253, 250, 0.7));
}

.related-notes-panel__title {
  margin: 0 0 10px;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.02em;
  text-transform: none;
  color: var(--vp-c-text-1);
}

.related-notes-panel__meta {
  margin: 0;
  font-size: 13px;
  color: var(--vp-c-text-2);
}

.related-notes-panel__list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.related-notes-panel__item {
  margin: 0;
}

.related-notes-panel__link {
  display: inline-block;
  font-size: 13px;
  line-height: 1.35;
  color: var(--vp-c-text-2);
  text-decoration: underline;
  text-decoration-thickness: 1px;
  text-underline-offset: 2px;
  cursor: pointer;
}

.related-notes-panel__link:hover {
  color: var(--vp-c-brand-1);
}

.dark .related-notes-panel {
  border-color: rgba(148, 163, 184, 0.3);
  background: linear-gradient(160deg, rgba(15, 23, 42, 0.75), rgba(6, 78, 59, 0.26));
}
</style>
