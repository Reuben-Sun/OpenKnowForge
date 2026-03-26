<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { withBase } from 'vitepress'

type NoteItem = {
  tags?: string[]
}

type TagStat = {
  tag: string
  count: number
  size: number
  color: string
}

const loading = ref(true)
const error = ref('')
const tagStats = ref<TagStat[]>([])

const POLL_INTERVAL_MS = 3000
const ROW_COUNT = 3
const MIN_ROW_ITEMS = 18
const TAG_COLOR_PALETTE = ['#FF669E', '#66E3FF', '#FF8266', '#66FFC7', '#AB857D', '#807377']
let pollTimer: number | undefined

function stableHash(text: string): number {
  let hash = 0
  for (let i = 0; i < text.length; i += 1) {
    hash = (hash * 31 + text.charCodeAt(i)) >>> 0
  }
  return hash
}

function colorForTag(tag: string): string {
  const hash = stableHash(tag)
  return TAG_COLOR_PALETTE[hash % TAG_COLOR_PALETTE.length]
}

function buildTagStats(notes: NoteItem[]): TagStat[] {
  const counts = new Map<string, number>()
  for (const note of notes) {
    for (const rawTag of note.tags || []) {
      const tag = String(rawTag || '').trim()
      if (!tag) {
        continue
      }
      counts.set(tag, (counts.get(tag) || 0) + 1)
    }
  }

  const entries = Array.from(counts.entries())
  if (entries.length === 0) {
    return []
  }

  const maxCount = Math.max(...entries.map(([, count]) => count))
  const minSize = 14
  const maxSize = 34

  return entries
    .map(([tag, count]) => {
      const ratio = maxCount <= 1 ? 1 : count / maxCount
      const size = Math.round(minSize + (maxSize - minSize) * ratio)
      return {
        tag,
        count,
        size,
        color: colorForTag(tag),
      }
    })
    .sort((a, b) => b.count - a.count || a.tag.localeCompare(b.tag))
}

const rollingRows = computed(() => {
  const repeated: TagStat[] = []
  for (const stat of tagStats.value) {
    const repeat = Math.max(1, Math.min(10, stat.count))
    for (let i = 0; i < repeat; i += 1) {
      repeated.push(stat)
    }
  }

  if (repeated.length === 0) {
    return []
  }

  const rows: TagStat[][] = Array.from({ length: ROW_COUNT }, () => [])
  repeated.forEach((item, index) => {
    rows[index % ROW_COUNT].push(item)
  })

  return rows
    .map((row) => {
      if (row.length === 0) {
        return []
      }
      const expanded = [...row]
      let cursor = 0
      while (expanded.length < MIN_ROW_ITEMS) {
        expanded.push(row[cursor % row.length])
        cursor += 1
      }
      return expanded
    })
    .filter((row) => row.length > 0)
})

const doubledRows = computed(() => {
  return rollingRows.value.map((row) => [...row, ...row])
})

function resolveTagLink(tag: string): string {
  return withBase(`/notes/explorer?q=${encodeURIComponent(tag)}`)
}

async function loadTagStats(isInitial: boolean): Promise<void> {
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
      const notes = Array.isArray(payload?.notes) ? (payload.notes as NoteItem[]) : []
      tagStats.value = buildTagStats(notes)
      error.value = ''
      return
    } catch {
      continue
    }
  }

  if (isInitial) {
    error.value = 'Failed to load tags from search-index.json.'
  }
}

onMounted(async () => {
  await loadTagStats(true)
  loading.value = false

  pollTimer = window.setInterval(() => {
    void loadTagStats(false)
  }, POLL_INTERVAL_MS)
})

onBeforeUnmount(() => {
  if (pollTimer !== undefined) {
    window.clearInterval(pollTimer)
  }
})
</script>

<template>
  <section class="home-tag-stream">
    <h2 class="home-tag-stream__title">Notes Tag Stream</h2>
    <p v-if="loading" class="home-tag-stream__meta">Loading tags...</p>
    <p v-else-if="error" class="home-tag-stream__error">{{ error }}</p>
    <p v-else-if="doubledRows.length === 0" class="home-tag-stream__meta">No tags yet.</p>

    <div v-if="!loading && !error && doubledRows.length > 0" class="home-tag-stream__rows">
      <div v-for="(row, rowIndex) in doubledRows" :key="`row-${rowIndex}`" class="home-tag-stream__marquee-row">
        <div class="home-tag-stream__inner">
          <a
            v-for="(item, index) in row"
            :key="`${rowIndex}-${item.tag}-${index}`"
            class="home-tag-stream__tag"
            :href="resolveTagLink(item.tag)"
            :style="{ fontSize: `${item.size}px`, color: item.color }"
          >
            #{{ item.tag }}
          </a>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.home-tag-stream {
  margin-top: 28px;
  border-radius: 18px;
  border: 1px solid var(--vp-c-divider);
  padding: 16px;
  background: linear-gradient(140deg, rgba(255, 255, 255, 0.95), rgba(230, 255, 244, 0.95));
}

.home-tag-stream__title {
  margin: 0 0 12px;
  font-size: 16px;
  letter-spacing: 0.02em;
}

.home-tag-stream__meta,
.home-tag-stream__error {
  margin: 0;
  font-size: 14px;
}

.home-tag-stream__error {
  color: #b91c1c;
}

.home-tag-stream__rows {
  display: grid;
  gap: 10px;
}

.home-tag-stream__marquee-row {
  overflow: hidden;
  mask-image: linear-gradient(to right, transparent, black 8%, black 92%, transparent);
  -webkit-mask-image: linear-gradient(to right, transparent, black 8%, black 92%, transparent);
}

.home-tag-stream__inner {
  width: max-content;
  display: flex;
  align-items: center;
  gap: 16px;
  white-space: nowrap;
  animation: home-tags-scroll 36s linear infinite;
}

.home-tag-stream:hover .home-tag-stream__inner {
  animation-play-state: paused;
}

.home-tag-stream__tag {
  display: inline-block;
  font-weight: 700;
  line-height: 1.1;
  text-decoration: none;
  text-shadow: 0 1px 0 rgba(0, 0, 0, 0.06);
  transition: transform 0.18s ease, opacity 0.18s ease;
}

.home-tag-stream__tag:hover {
  transform: translateY(-1px);
  opacity: 0.86;
}

@keyframes home-tags-scroll {
  from {
    transform: translateX(0);
  }
  to {
    transform: translateX(-50%);
  }
}

.dark .home-tag-stream {
  background: linear-gradient(150deg, rgba(7, 12, 20, 0.96), rgba(7, 35, 31, 0.9));
  border-color: rgba(148, 163, 184, 0.28);
}

.dark .home-tag-stream__error {
  color: #fca5a5;
}
</style>
