<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { withBase } from 'vitepress'

type NoteItem = {
  title: string
  date: string
  tags: string[]
  link: string
  excerpt?: string
}

const notes = ref<NoteItem[]>([])
const query = ref('')
const activeTag = ref('all')
const loading = ref(true)
const error = ref('')

const availableTags = computed(() => {
  const tagSet = new Set<string>()
  for (const note of notes.value) {
    for (const tag of note.tags || []) {
      tagSet.add(tag)
    }
  }
  return ['all', ...Array.from(tagSet).sort((a, b) => a.localeCompare(b))]
})

const filteredNotes = computed(() => {
  const q = query.value.trim().toLowerCase()

  return notes.value.filter((note) => {
    const matchesTag = activeTag.value === 'all' || (note.tags || []).includes(activeTag.value)
    if (!matchesTag) {
      return false
    }

    if (!q) {
      return true
    }

    const haystack = [note.title, note.excerpt || '', ...(note.tags || [])].join(' ').toLowerCase()
    return haystack.includes(q)
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

onMounted(async () => {
  try {
    const response = await fetch(withBase('/search-index.json'), { cache: 'no-store' })
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }
    const payload = await response.json()
    notes.value = Array.isArray(payload?.notes) ? payload.notes : []
  } catch {
    error.value = 'Failed to load search index. Create notes via POST /note first.'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <section class="note-explorer">
    <div class="note-explorer__controls">
      <input
        v-model="query"
        class="note-explorer__search"
        type="search"
        placeholder="Search title, tags, excerpt..."
      />
      <div class="note-explorer__tags">
        <button
          v-for="tag in availableTags"
          :key="tag"
          class="note-explorer__tag"
          :class="{ 'is-active': tag === activeTag }"
          @click="activeTag = tag"
        >
          {{ tag === 'all' ? 'all tags' : tag }}
        </button>
      </div>
    </div>

    <p v-if="loading" class="note-explorer__meta">Loading notes...</p>
    <p v-else-if="error" class="note-explorer__error">{{ error }}</p>
    <p v-else class="note-explorer__meta">
      {{ filteredNotes.length }} / {{ notes.length }} notes
    </p>

    <ul v-if="!loading && !error" class="note-explorer__list">
      <li v-for="note in filteredNotes" :key="`${note.link}-${note.date}`" class="note-explorer__item">
        <a :href="resolveLink(note.link)" class="note-explorer__title">{{ note.title }}</a>
        <div class="note-explorer__date">{{ note.date || 'unknown date' }}</div>
        <p v-if="note.excerpt" class="note-explorer__excerpt">{{ note.excerpt }}</p>
        <div class="note-explorer__chips">
          <span v-for="tag in note.tags" :key="tag" class="note-explorer__chip">#{{ tag }}</span>
        </div>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.note-explorer {
  border: 1px solid var(--vp-c-divider);
  border-radius: 16px;
  background: linear-gradient(170deg, rgba(255, 255, 255, 0.95), rgba(240, 253, 250, 0.95));
  padding: 18px;
}

.note-explorer__controls {
  display: grid;
  gap: 10px;
}

.note-explorer__search {
  width: 100%;
  border: 1px solid var(--vp-c-divider);
  border-radius: 10px;
  padding: 10px 12px;
  background: #fff;
}

.note-explorer__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.note-explorer__tag {
  border: 1px solid var(--vp-c-divider);
  border-radius: 999px;
  padding: 4px 10px;
  cursor: pointer;
  background: #fff;
  font-size: 13px;
}

.note-explorer__tag.is-active {
  border-color: var(--vp-c-brand-1);
  color: var(--vp-c-brand-1);
  background: rgba(13, 148, 136, 0.08);
}

.note-explorer__meta,
.note-explorer__error {
  margin-top: 12px;
  margin-bottom: 8px;
  font-size: 14px;
}

.note-explorer__error {
  color: #b91c1c;
}

.note-explorer__list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 10px;
}

.note-explorer__item {
  border: 1px solid var(--vp-c-divider);
  border-radius: 12px;
  padding: 12px;
  background: #fff;
}

.note-explorer__title {
  font-weight: 600;
  text-decoration: none;
}

.note-explorer__date {
  margin-top: 4px;
  color: var(--vp-c-text-2);
  font-size: 13px;
}

.note-explorer__excerpt {
  margin: 8px 0;
  color: var(--vp-c-text-2);
  font-size: 14px;
}

.note-explorer__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.note-explorer__chip {
  border-radius: 999px;
  background: #f0fdfa;
  color: #0f766e;
  font-size: 12px;
  padding: 2px 8px;
}

.dark .note-explorer {
  background: linear-gradient(165deg, rgba(12, 18, 31, 0.95), rgba(8, 47, 73, 0.35));
  border-color: rgba(148, 163, 184, 0.28);
}

.dark .note-explorer__search,
.dark .note-explorer__tag,
.dark .note-explorer__item {
  background: rgba(15, 23, 42, 0.8);
  border-color: rgba(148, 163, 184, 0.28);
}

.dark .note-explorer__chip {
  background: rgba(13, 148, 136, 0.2);
  color: #99f6e4;
}

.dark .note-explorer__error {
  color: #fca5a5;
}
</style>
