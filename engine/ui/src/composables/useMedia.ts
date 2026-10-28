import { onScopeDispose, ref } from 'vue'

/** Whether a media query matches, kept current. */
export function useMedia(query: string) {
  const list = typeof matchMedia === 'function' ? matchMedia(query) : null
  const matches = ref(list?.matches ?? false)
  const update = (event: MediaQueryListEvent) => (matches.value = event.matches)
  list?.addEventListener('change', update)
  onScopeDispose(() => list?.removeEventListener('change', update))
  return matches
}

export const useDesktop = () => useMedia('(min-width: 768px)')
