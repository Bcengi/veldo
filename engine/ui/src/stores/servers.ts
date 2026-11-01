import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useSessionStore } from './session'

/** What the form shows of a credential: its label, when and by whom it was last set, replaced or deleted, and the
 * reference and version the credential route answered. Never its value: this store has no field for one. */
export interface CredentialMeta {
  id: string
  label: string
  setAt: number
  setBy: string
  reference: string
  version: number
  deleted: boolean
}

/** The credentials written from the form in this session, in memory only. The API refuses every read-back of a
 * credential (unauthorized:credential_read_back), so the form knows a credential's record from the answers to its
 * own writes; nothing here is put in storage, the URL or the DOM beyond the label, set at and set by. */
export const useServersStore = defineStore('servers', () => {
  const credentials = ref<Record<string, CredentialMeta>>({})

  function recordCredential(meta: CredentialMeta) {
    credentials.value = { ...credentials.value, [meta.id]: meta }
  }

  function reset() {
    credentials.value = {}
  }

  useSessionStore().onEnd(reset)
  return { credentials, recordCredential, reset }
})
