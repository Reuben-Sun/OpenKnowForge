import DefaultTheme from 'vitepress/theme'
import type { Theme } from 'vitepress'
import { h } from 'vue'
import NoteExplorer from './components/NoteExplorer.vue'
import NotesCards from './components/NotesCards.vue'
import HomeTagStream from './components/HomeTagStream.vue'
import RelatedNotesSidebar from './components/RelatedNotesSidebar.vue'
import NoteStatsBar from './components/NoteStatsBar.vue'
import './custom.css'

const theme: Theme = {
  extends: DefaultTheme,
  Layout: () =>
    h(DefaultTheme.Layout, null, {
      'sidebar-nav-before': () => h(RelatedNotesSidebar),
      'doc-before': () => h(NoteStatsBar)
    }),
  enhanceApp({ app }) {
    app.component('NoteExplorer', NoteExplorer)
    app.component('NotesCards', NotesCards)
    app.component('HomeTagStream', HomeTagStream)
    app.component('RelatedNotesSidebar', RelatedNotesSidebar)
    app.component('NoteStatsBar', NoteStatsBar)
  }
}

export default theme
