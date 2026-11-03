/**
 * Every icon the UI draws, by Nuxt UI name. The build bundles exactly these (and Nuxt UI's own defaults, such
 * as its loading indicator) from the local @iconify-json/lucide collection, and fails when one is missing, so
 * no icon is ever looked up at run time (VELDO-0229, the content security policy).
 */
export const ICONS = [
  'i-lucide-layout-dashboard',
  'i-lucide-square-terminal',
  'i-lucide-inbox',
  'i-lucide-server',
  'i-lucide-id-card',
  'i-lucide-users',
  'i-lucide-folder-kanban',
  'i-lucide-list-todo',
  'i-lucide-cpu',
  'i-lucide-shield-check',
  'i-lucide-chart-column',
  'i-lucide-settings',
  'i-lucide-library',
  'i-lucide-git-branch',
  'i-lucide-workflow',
  'i-lucide-circle-user',
  'i-lucide-sun',
  'i-lucide-moon',
  'i-lucide-refresh-cw',
  'i-lucide-arrow-right',
  'i-lucide-chevron-left',
  'i-lucide-search',
  'i-lucide-x',
  'i-lucide-copy',
  'i-lucide-check',
  'i-lucide-loader-circle',
  'i-lucide-panel-left',
] as const

export type IconId = (typeof ICONS)[number]
