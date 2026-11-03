import { ref } from 'vue'

/** The desktop sidebar's width (VELDO-0229, Telegram 38255): a narrow icon rail by default, expanded to the
 * labeled sidebar by the panel toggle in each screen's top bar. Kept for the page's lifetime, across navigation;
 * not stored. */
const expanded = ref(false)

export function useRail() {
  return { expanded, toggle: () => (expanded.value = !expanded.value) }
}
