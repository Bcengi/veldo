import { ref, watchEffect } from 'vue'

export type Theme = 'light' | 'dark'
const KEY = 'veldo.theme'

function systemTheme(): Theme {
  return typeof matchMedia === 'function' && matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function stored(): Theme | null {
  try {
    const value = localStorage.getItem(KEY)
    return value === 'light' || value === 'dark' ? value : null
  } catch {
    return null
  }
}

const theme = ref<Theme>(stored() ?? systemTheme())
let started = false

/** Put the theme on the document: Veldo's data-theme attribute and Nuxt UI's dark and light classes, together. */
export function applyTheme(root: HTMLElement, value: Theme) {
  root.setAttribute('data-theme', value)
  root.classList.toggle('dark', value === 'dark')
  root.classList.toggle('light', value === 'light')
}

/** Light or dark, following the system until the person picks one. Only the choice itself is stored. The one
 * preference drives both Veldo's tokens (data-theme) and Nuxt UI's components (the dark class); the sidebar's
 * appearance switch and the account screen's switch both read and set it here (VELDO-0229). */
export function useTheme() {
  if (!started && typeof document !== 'undefined') {
    started = true
    watchEffect(() => applyTheme(document.documentElement, theme.value))
  }
  function set(next: Theme) {
    theme.value = next
    try {
      localStorage.setItem(KEY, next)
    } catch {
      /* private mode: the choice lasts for this page */
    }
  }
  return { theme, set, toggle: () => set(theme.value === 'dark' ? 'light' : 'dark') }
}
