import { defineConfig, type DefaultTheme } from 'vitepress'

const normalizeBasePath = (value: string): string => {
  const trimmed = value.trim()
  if (!trimmed) {
    return '/'
  }
  const withLeadingSlash = trimmed.startsWith('/') ? trimmed : `/${trimmed}`
  return withLeadingSlash.endsWith('/') ? withLeadingSlash : `${withLeadingSlash}/`
}

const resolveGitHubRepoLink = (): string => {
  const fallbackRepo = 'Reuben-Sun/OpenKnowForge'
  const rawValue =
    process.env.VITEPRESS_GITHUB_REPO?.trim() ||
    process.env.GITHUB_REPOSITORY?.trim() ||
    fallbackRepo
  const normalized = rawValue.replace(/\/+$/, '')
  if (/^https?:\/\//i.test(normalized)) {
    return normalized
  }
  return `https://github.com/${normalized.replace(/^\/+/, '')}`
}

const repoName = process.env.GITHUB_REPOSITORY?.split('/')[1]?.trim()
const explicitBase = process.env.VITEPRESS_BASE?.trim()
const isGitHubActions = process.env.GITHUB_ACTIONS === 'true'
const isUserOrOrgSiteRepo = Boolean(repoName && repoName.toLowerCase().endsWith('.github.io'))
const githubRepoLink = resolveGitHubRepoLink()
const base = explicitBase
  ? normalizeBasePath(explicitBase)
  : isGitHubActions && repoName && !isUserOrOrgSiteRepo
    ? normalizeBasePath(repoName)
    : '/'

const sharedSocialLinks: DefaultTheme.SocialLink[] = [
  { icon: 'github', link: githubRepoLink }
]

const zhGuideSidebar: DefaultTheme.SidebarItem[] = [
  {
    text: '指南',
    items: [
      { text: '快速开始', link: '/guide/quick-start' },
      { text: 'API', link: '/guide/api' },
      { text: '结构', link: '/guide/structure' }
    ]
  }
]

const enGuideSidebar: DefaultTheme.SidebarItem[] = [
  {
    text: 'Guide',
    items: [
      { text: 'Quick Start', link: '/en/guide/quick-start' },
      { text: 'API', link: '/en/guide/api' },
      { text: 'Structure', link: '/en/guide/structure' }
    ]
  }
]

const zhThemeConfig: DefaultTheme.Config = {
  langMenuLabel: '语言',
  outline: {
    label: '本页目录',
    level: [2, 6]
  },
  nav: [
    { text: '首页', link: '/' },
    { text: '笔记', link: '/notes/' },
    { text: '探索', link: '/notes/explorer' },
    { text: '指南', link: '/guide/quick-start' }
  ],
  sidebar: {
    '/guide': zhGuideSidebar,
    '/guide/': zhGuideSidebar
  },
  socialLinks: sharedSocialLinks,
  search: {
    provider: 'local'
  }
}

const enThemeConfig: DefaultTheme.Config = {
  langMenuLabel: 'Language',
  outline: {
    label: 'On this page',
    level: [2, 6]
  },
  nav: [
    { text: 'Home', link: '/en/' },
    { text: 'Notes', link: '/en/notes/' },
    { text: 'Explore', link: '/en/notes/explorer' },
    { text: 'Guide', link: '/en/guide/quick-start' }
  ],
  sidebar: {
    '/en/guide': enGuideSidebar,
    '/en/guide/': enGuideSidebar
  },
  socialLinks: sharedSocialLinks,
  search: {
    provider: 'local'
  }
}

export default defineConfig({
  title: 'OpenKnowForge',
  description: 'API-driven, git-backed knowledge base',
  base,
  cleanUrls: true,
  rewrites: (id) => {
    if (id.startsWith('ui/zh/')) {
      return id.slice('ui/zh/'.length)
    }
    if (id.startsWith('ui/en/')) {
      return `en/${id.slice('ui/en/'.length)}`
    }
    if (id.startsWith('project/entries/')) {
      return `notes/entries/${id.slice('project/entries/'.length)}`
    }
    return id
  },
  markdown: {
    math: true
  },
  locales: {
    root: {
      label: '简体中文',
      lang: 'zh-CN',
      title: 'OpenKnowForge',
      description: 'API 驱动、Git 记录的知识库',
      themeConfig: zhThemeConfig
    },
    en: {
      label: 'English',
      lang: 'en-US',
      title: 'OpenKnowForge',
      description: 'API-driven, git-backed knowledge base',
      themeConfig: enThemeConfig
    }
  }
})
