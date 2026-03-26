<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, withBase } from 'vitepress'

type NoteItem = {
  link?: string
  word_count?: number | string
  image_count?: number | string
}

const loading = ref(true)
const error = ref('')
const allNotes = ref<NoteItem[]>([])
const route = useRoute()

const POLL_INTERVAL_MS = 3000
let pollTimer: number | undefined

const isEn = computed(() => route.path.startsWith('/en/'))

const uiText = computed(() =>
  isEn.value
    ? {
        loading: 'Loading stats...',
        loadError: 'Failed to load stats from search-index.json.',
        notes: 'Total Notes',
        words: 'Total Words',
        images: 'Total Images',
        scope: 'Scope: notes under project/entries'
      }
    : {
        loading: '正在加载统计...',
        loadError: '读取 search-index.json 统计失败。',
        notes: '笔记总数',
        words: '笔记总字数',
        images: '笔记图片总数',
        scope: '统计范围：project/entries 下的笔记'
      }
)

function toSafeNumber(value: unknown): number {
  const num = Number(value)
  if (!Number.isFinite(num) || num < 0) {
    return 0
  }
  return num
}

const projectNotes = computed(() => {
  return allNotes.value.filter((note) => {
    const link = String(note.link || '')
    return link.includes('/notes/entries/')
  })
})

const totalNotes = computed(() => projectNotes.value.length)

const totalWords = computed(() => {
  return projectNotes.value.reduce((sum, note) => sum + toSafeNumber(note.word_count), 0)
})

const totalImages = computed(() => {
  return projectNotes.value.reduce((sum, note) => sum + toSafeNumber(note.image_count), 0)
})

const cards = computed(() => [
  { key: 'notes', label: uiText.value.notes, value: totalNotes.value },
  { key: 'words', label: uiText.value.words, value: totalWords.value },
  { key: 'images', label: uiText.value.images, value: totalImages.value }
])

function formatNumber(value: number): string {
  return new Intl.NumberFormat().format(value)
}

async function loadStats(isInitial: boolean): Promise<void> {
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
      allNotes.value = Array.isArray(payload?.notes) ? (payload.notes as NoteItem[]) : []
      error.value = ''
      return
    } catch {
      continue
    }
  }

  if (isInitial) {
    error.value = uiText.value.loadError
  }
}

onMounted(async () => {
  await loadStats(true)
  loading.value = false

  pollTimer = window.setInterval(() => {
    void loadStats(false)
  }, POLL_INTERVAL_MS)
})

onBeforeUnmount(() => {
  if (pollTimer !== undefined) {
    window.clearInterval(pollTimer)
  }
})
</script>

<template>
  <section class="home-stats-cards">
    <p v-if="loading" class="home-stats-cards__meta">{{ uiText.loading }}</p>
    <p v-else-if="error" class="home-stats-cards__error">{{ error }}</p>

    <div v-if="!loading && !error" class="home-stats-cards__grid">
      <article v-for="card in cards" :key="card.key" class="home-stats-cards__card">
        <p class="home-stats-cards__label">{{ card.label }}</p>
        <p class="home-stats-cards__value">{{ formatNumber(card.value) }}</p>
      </article>
    </div>

    <p v-if="!loading && !error" class="home-stats-cards__scope">{{ uiText.scope }}</p>
  </section>
</template>

<style scoped>
.home-stats-cards {
  margin-top: 20px;
}

.home-stats-cards__meta,
.home-stats-cards__error {
  margin: 0;
  font-size: 14px;
}

.home-stats-cards__error {
  color: #b91c1c;
}

.home-stats-cards__grid {
  display: grid;
  gap: 14px;
  grid-template-columns: repeat(1, minmax(0, 1fr));
}

.home-stats-cards__card {
  border: 1px solid var(--vp-c-divider);
  border-radius: 14px;
  padding: 16px;
  background: linear-gradient(150deg, rgba(255, 255, 255, 0.96), rgba(238, 253, 248, 0.96));
}

.home-stats-cards__label {
  margin: 0;
  font-size: 13px;
  color: var(--vp-c-text-2);
}

.home-stats-cards__value {
  margin: 8px 0 0;
  font-size: 28px;
  line-height: 1.1;
  font-weight: 700;
}

.home-stats-cards__scope {
  margin: 10px 0 0;
  font-size: 12px;
  color: var(--vp-c-text-2);
}

@media (min-width: 720px) {
  .home-stats-cards__grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

.dark .home-stats-cards__card {
  background: linear-gradient(165deg, rgba(12, 18, 31, 0.95), rgba(8, 47, 73, 0.35));
  border-color: rgba(148, 163, 184, 0.28);
}

.dark .home-stats-cards__error {
  color: #fca5a5;
}
</style>
