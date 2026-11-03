import { nextTick } from 'vue'
import { describe, expect, it } from 'vitest'
import { applyTheme, useTheme } from './useTheme'

/** VELDO-0229 AC1: one theme preference drives Veldo's data-theme and Nuxt UI's dark and light classes. */
describe('useTheme', () => {
  it('puts data-theme and the matching class on the document together', () => {
    const root = document.createElement('html')
    applyTheme(root, 'dark')
    expect(root.getAttribute('data-theme')).toBe('dark')
    expect(root.classList.contains('dark')).toBe(true)
    expect(root.classList.contains('light')).toBe(false)
    applyTheme(root, 'light')
    expect(root.getAttribute('data-theme')).toBe('light')
    expect(root.classList.contains('dark')).toBe(false)
    expect(root.classList.contains('light')).toBe(true)
  })

  it('is one preference: every caller sees the same choice, applied to the document and stored', async () => {
    const sidebar = useTheme()
    const account = useTheme()
    sidebar.set('dark')
    await nextTick()
    expect(account.theme.value).toBe('dark')
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(localStorage.getItem('veldo.theme')).toBe('dark')
    account.toggle()
    await nextTick()
    expect(sidebar.theme.value).toBe('light')
    expect(document.documentElement.classList.contains('dark')).toBe(false)
    expect(localStorage.getItem('veldo.theme')).toBe('light')
  })
})
