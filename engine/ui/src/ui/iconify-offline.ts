/**
 * Veldo's adapter for @iconify/vue, which vite.config.ts substitutes for every import of that package. It
 * re-exports Iconify's offline build, which has no API client, so an icon missing from the bundle renders
 * nothing instead of being fetched from api.iconify.design (the content security policy allows this origin
 * only). The offline build lacks iconLoaded, which Nuxt UI's icon asks; it is answered from the icons added.
 * addCollection registers only the colon form; Nuxt UI's bundle adds icons one by one through addIcon.
 */
import { Icon, addCollection as addOfflineCollection, addIcon as addOfflineIcon } from '@iconify/vue/offline'

type IconData = Parameters<typeof addOfflineIcon>[1]
type Collection = Parameters<typeof addOfflineCollection>[0]
const loaded = new Set<string>()

/** Nuxt UI asks for `lucide-x` (its `i-lucide-x` without the `i-`) while its bundle adds `lucide:x`. The online
 * build parses both forms; the offline build looks names up as given, so each icon is added under both. */
export function addIcon(name: string, data: IconData) {
  for (const form of new Set([name, name.replace(':', '-')])) {
    loaded.add(form)
    addOfflineIcon(form, data)
  }
  return true
}

export function addCollection(collection: Collection, prefix?: string | boolean) {
  const at = typeof prefix === 'string' ? prefix : collection.prefix
  for (const name of Object.keys(collection.icons ?? {})) {
    loaded.add(`${at}:${name}`)
    loaded.add(`${at}-${name}`)
  }
  addOfflineCollection(collection, prefix)
  return true
}

export function iconLoaded(name: string) {
  return loaded.has(name)
}

export { Icon }
