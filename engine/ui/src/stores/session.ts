import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import * as auth from '@/api/auth'
import { apiContext } from '@/api/context'
import { ApiRefusal } from '@/api/refusal'
import type { SessionView } from '@/api/types'
import { assertPasskey } from '@/features/signin/webauthn'

export type SessionStatus = 'unknown' | 'signed-out' | 'signed-in'

/** The passkey session: who is signed in, the anti-forgery token (memory only) and why a session ended. */
export const useSessionStore = defineStore('session', () => {
  const status = ref<SessionStatus>('unknown')
  const view = ref<Omit<SessionView, 'csrf_token'> | null>(null)
  /** Why the last session ended or sign-in was needed, shown on the sign-in screen. */
  const endedBy = ref<ApiRefusal | null>(null)
  const listeners: (() => void)[] = []

  const principal = computed(() => view.value?.principal ?? null)
  const domain = computed(() => view.value?.domain ?? null)

  function adopt(session: SessionView) {
    const { csrf_token: token, ...rest } = session
    apiContext.token = token
    apiContext.domain = session.domain
    view.value = rest
    status.value = 'signed-in'
    endedBy.value = null
  }

  function end(reason: ApiRefusal | null) {
    apiContext.token = null
    view.value = null
    status.value = 'signed-out'
    endedBy.value = reason
    for (const listener of listeners) listener()
  }

  /** Run `fn` whenever a session ends, so every store drops the data it held. */
  function onEnd(fn: () => void) {
    listeners.push(fn)
  }

  async function restore() {
    try {
      adopt(await auth.readSession())
    } catch (error) {
      if (error instanceof ApiRefusal) end(error.error === 'unauthenticated' ? null : error)
      else throw error
    }
  }

  async function signIn() {
    const issued = await auth.challenge()
    const assertion = await assertPasskey(issued.challenge, issued.rp_id)
    adopt(await auth.signIn(assertion))
  }

  async function signOut(everywhere = false) {
    try {
      if (everywhere) await auth.signOutEverywhere()
      else await auth.signOut()
    } finally {
      end(new ApiRefusal(200, 'unauthenticated:signed_out', 'unauthenticated'))
    }
  }

  apiContext.onUnauthenticated = (refusal) => {
    if (status.value === 'signed-in') end(refusal)
  }

  return { status, view, principal, domain, endedBy, adopt, end, onEnd, restore, signIn, signOut }
})
