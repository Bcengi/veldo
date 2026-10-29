import { onScopeDispose, ref } from 'vue'

/** The current time in milliseconds, updated every `every` milliseconds while the caller's scope lives. */
export function useNow(every = 1000) {
  const now = ref(Date.now())
  const timer = setInterval(() => (now.value = Date.now()), every)
  onScopeDispose(() => clearInterval(timer))
  return now
}
