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

/** Light or dark, following the system until the person picks one. Only the choice itself is stored. */
export function useTheme() {
  if (!started && typeof document !== 'undefined') {
    started = true
    watchEffect(() => document.documentElement.setAttribute('data-theme', theme.value))
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
