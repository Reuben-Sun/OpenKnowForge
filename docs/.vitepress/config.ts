import { defineConfig } from 'vitepress'

const repoName = process.env.GITHUB_REPOSITORY?.split('/')[1]
const base = process.env.GITHUB_ACTIONS === 'true' && repoName ? `/${repoName}/` : '/'

export default defineConfig({
  title: 'OpenKnowForge',
  description: 'API-driven, git-backed knowledge base',
  base,
  cleanUrls: true,
  markdown: {
    math: true
  },
  themeConfig: {
    nav: [
      { text: 'Home', link: '/' },
      { text: 'Notes', link: '/notes/' },
      { text: 'Explore', link: '/notes/explorer' },
      { text: 'Guide', link: '/guide/api' }
    ],
    sidebar: {
      '/guide/': [
        {
          text: 'Guide',
          items: [
            { text: 'Guide', link: '/guide' },
            { text: 'API', link: '/guide/api' },
            { text: 'Struture', link: '/guide/structure' }
          ]
        }
      ],
      '/notes/': [
        {
          text: 'Notes',
          items: [
            { text: 'All Notes', link: '/notes/' },
            { text: 'Explore', link: '/notes/explorer' }
          ]
        }
      ]
    },
    socialLinks: [{ icon: 'github', link: 'https://github.com/Reuben-Sun/OpenKnowForge' }],
    search: {
      provider: 'local'
    }
  }
})
