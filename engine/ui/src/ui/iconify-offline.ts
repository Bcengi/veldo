/**
 * Veldo's adapter for @iconify/vue, which vite.config.ts substitutes for every import of that package. It
 * re-exports Iconify's offline build, which has no API client, so an icon missing from the bundle renders
 * nothing instead of being fetched from api.iconify.design (the content security policy allows this origin
 * only). The offline build lacks iconLoaded, which Nuxt UI's icon asks; it is answered from the icons added.
 */
import { Icon, addCollection as addOfflineCollection, addIcon as addOfflineIcon } from '@iconify/vue/offline'

type IconData = Parameters<typeof addOfflineIcon>[1]
type Collection = Parameters<typeof addOfflineCollection>[0]
const loaded = new Set<string>()

export function addIcon(name: string, data: IconData) {
  loaded.add(name)
  addOfflineIcon(name, data)
  return true
}

export function addCollection(collection: Collection, prefix?: string | boolean) {
  const at = typeof prefix === 'string' ? prefix : collection.prefix
  for (const name of Object.keys(collection.icons ?? {})) loaded.add(`${at}:${name}`)
  addOfflineCollection(collection, prefix)
  return true
}

export function iconLoaded(name: string) {
  return loaded.has(name)
}

export { Icon }
