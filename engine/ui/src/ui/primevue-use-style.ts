import { readonly, ref, watch, type Ref } from 'vue'
import { AdoptedSheet } from './sheets'

/**
 * PrimeVue's useStyle (@primevue/core/usestyle) with the same call shape, writing each named sheet through
 * the CSS object model (sheets.ts) instead of a <style> element, which the API's policy refuses.
 */
const byName = new Map<string, AdoptedSheet>()
let serial = 0

interface Options {
  name?: string
  immediate?: boolean
  manual?: boolean
  props?: Record<string, unknown>
  onMounted?: (name: string) => void
  onUpdated?: (name: string) => void
  [option: string]: unknown
}

export function useStyle(css: string, options: Options = {}) {
  const isLoaded = ref(false)
  const cssRef = ref(css)
  const styleRef: Ref<AdoptedSheet | null> = ref(null)
  const name = options.name ?? `style_${++serial}`
  let stop = () => {}

  const load = (next?: string, props: Record<string, unknown> = {}) => {
    if (typeof document === 'undefined') return
    const sheetName = String((props.name as string | undefined) ?? (options.props?.name as string | undefined) ?? name)
    let sheet = byName.get(sheetName)
    if (!sheet) {
      sheet = new AdoptedSheet()
      byName.set(sheetName, sheet)
      options.onMounted?.(sheetName)
    } else if (!sheet.isConnected) sheet.attach()
    styleRef.value = sheet
    if (!isLoaded.value) cssRef.value = next || css
    if (isLoaded.value) return
    stop = watch(
      cssRef,
      (value) => {
        sheet.textContent = value
        options.onUpdated?.(sheetName)
      },
      { immediate: true },
    )
    isLoaded.value = true
  }

  const unload = () => {
    if (!isLoaded.value) return
    stop()
    styleRef.value?.remove()
    isLoaded.value = false
    styleRef.value = null
  }

  if (options.immediate !== false && !options.manual) load()

  return { id: undefined, name, el: styleRef, css: cssRef, unload, load, isLoaded: readonly(isLoaded) }
}
