<script setup lang="ts">
import InputText from 'primevue/inputtext'
import { computed, onMounted, ref, shallowRef } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as auth from '@/api/auth'
import { ApiRefusal } from '@/api/refusal'
import RefusalNotice from '@/components/RefusalNotice.vue'
import VButton from '@/components/VButton.vue'
import Wordmark from '@/components/Wordmark.vue'
import { assertPasskey, ceremonyMessage, createPasskey, passkeysAvailable } from '@/features/signin/webauthn'
import { useSessionStore } from '@/stores/session'

/** Sign in with a passkey, or add this device's passkey: the registration and possession ceremonies, then the
 * fingerprint to compare at the host, where a steward approves it. Nothing here signs in until the API does. */
const session = useSessionStore()
const route = useRoute()
const router = useRouter()
const heading = ref<HTMLElement | null>(null)

type Mode = 'start' | 'enroll' | 'pending'
const mode = ref<Mode>('start')
const busy = ref<'sign-in' | 'create' | 'pending-sign-in' | null>(null)
const refusal = shallowRef<ApiRefusal | null>(null)
const problem = ref<string | null>(null)
const label = ref('')
const pending = shallowRef<(auth.PendingRegistration & { credentialId: string; rpId: string }) | null>(null)
const supported = passkeysAvailable()

const next = computed(() => (typeof route.query.next === 'string' && route.query.next.startsWith('/') ? route.query.next : '/runs'))
/** Why sign-in is needed: the session that ended, or a factory screen opened without one. */
const reason = computed<ApiRefusal | null>(() => {
  if (session.endedBy) return session.endedBy
  if (typeof route.query.next === 'string') return new ApiRefusal(401, 'unauthenticated:no_session', 'unauthenticated')
  return null
})
const expires = computed(() => {
  const at = pending.value?.expires_at
  if (typeof at !== 'number') return null
  const d = new Date(at * 1000)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
})
const fingerprintGroups = computed(() => {
  const text = pending.value?.fingerprint ?? ''
  const [scheme, ...groups] = text.split(':')
  return { scheme, groups }
})

onMounted(() => heading.value?.focus({ preventScroll: true }))

function clear() {
  refusal.value = null
  problem.value = null
}

function caught(error: unknown) {
  if (error instanceof ApiRefusal) refusal.value = error
  else problem.value = ceremonyMessage(error)
}

async function signIn() {
  clear()
  busy.value = 'sign-in'
  try {
    await session.signIn()
    await router.replace(next.value)
  } catch (error) {
    caught(error)
  } finally {
    busy.value = null
  }
}

async function create() {
  clear()
  const name = label.value.trim()
  if (!name) {
    problem.value = 'Name this passkey so you can recognize it at the host.'
    return
  }
  busy.value = 'create'
  try {
    const begun = await auth.beginRegistration(name)
    const made = await createPasskey(begun, name)
    const offered = await auth.offerCredential({ registration_id: begun.registration_id, ...made })
    const proof = await assertPasskey(offered.possession_challenge, begun.rp_id, made.credential_id)
    const shown = await auth.provePossession({ registration_id: begun.registration_id, ...proof })
    pending.value = { ...shown, credentialId: made.credential_id, rpId: begun.rp_id }
    mode.value = 'pending'
  } catch (error) {
    caught(error)
  } finally {
    busy.value = null
  }
}

/** Sign in with the passkey just added. The API refuses until the host has approved it. */
async function signInPending() {
  if (!pending.value) return
  clear()
  busy.value = 'pending-sign-in'
  try {
    const issued = await auth.challenge()
    const assertion = await assertPasskey(issued.challenge, issued.rp_id, pending.value.credentialId)
    session.adopt(await auth.signIn(assertion))
    await router.replace(next.value)
  } catch (error) {
    caught(error)
  } finally {
    busy.value = null
  }
}
</script>

<template>
  <main class="signin" id="main">
    <div class="signin-panel">
      <Wordmark size="lg" />
      <h1 ref="heading" tabindex="-1" class="signin-title">
        {{ mode === 'pending' ? 'Approve this passkey at the host' : mode === 'enroll' ? 'Add a passkey on this device' : 'Your factory, from anywhere' }}
      </h1>

      <RefusalNotice v-if="reason && mode === 'start' && !refusal" :refusal="reason" compact />

      <p v-if="!supported" class="signin-note" role="alert">
        This browser cannot use passkeys. Open the factory in a current browser on a device with a screen lock.
      </p>

      <template v-else-if="mode === 'start'">
        <p class="signin-lede">Watch every run as it happens and answer what is waiting on you. Sign in with the passkey you added for this factory.</p>
        <div class="signin-actions">
          <VButton label="Sign in with passkey" pending-label="Waiting for your passkey" :pending="busy === 'sign-in'" block data-testid="sign-in" @click="signIn" />
          <VButton label="Add a passkey on this device" variant="secondary" block data-testid="enroll-start" @click="(mode = 'enroll'), clear()" />
        </div>
      </template>

      <form v-else-if="mode === 'enroll'" class="signin-form" @submit.prevent="create">
        <ol class="signin-steps">
          <li class="is-current">Name it and create it with this device's screen lock.</li>
          <li>Compare its fingerprint at the host and approve it there.</li>
          <li>Sign in with it.</li>
        </ol>
        <label class="field-label" for="passkey-label">Passkey name, as the host will show it</label>
        <InputText id="passkey-label" v-model="label" maxlength="64" autocomplete="off" placeholder="For example: Pixel phone" data-testid="passkey-label" />
        <div class="signin-actions">
          <VButton type="submit" label="Create passkey" pending-label="Creating passkey" :pending="busy === 'create'" block data-testid="enroll-create" />
          <VButton label="Back to sign in" variant="quiet" block @click="(mode = 'start'), clear()" />
        </div>
      </form>

      <section v-else-if="pending" class="signin-pending" data-testid="pending" aria-labelledby="fingerprint-heading">
        <ol class="signin-steps">
          <li class="is-done">Created <strong>{{ pending.label }}</strong> on this device.</li>
          <li class="is-current">
            On the host, run <code>veldo factory passkey</code>. Approve the waiting passkey only if its name and fingerprint match these.
          </li>
          <li>Come back and sign in with it.</li>
        </ol>
        <h2 id="fingerprint-heading" class="fingerprint-heading">Fingerprint</h2>
        <p class="fingerprint" data-testid="fingerprint" :aria-label="`Fingerprint ${pending.fingerprint}`">
          <span class="fingerprint-scheme">{{ fingerprintGroups.scheme }}</span>
          <span v-for="(group, i) in fingerprintGroups.groups" :key="i" class="fingerprint-group">{{ group }}</span>
        </p>
        <dl class="pending-facts">
          <div><dt>Name</dt><dd data-testid="pending-label">{{ pending.label }}</dd></div>
          <div v-if="expires"><dt>Waiting until</dt><dd>{{ expires }}</dd></div>
        </dl>
        <div class="signin-actions">
          <VButton label="Sign in with this passkey" pending-label="Waiting for your passkey" :pending="busy === 'pending-sign-in'" block data-testid="pending-sign-in" @click="signInPending" />
        </div>
      </section>

      <RefusalNotice v-if="refusal" :refusal="refusal" compact />
      <p v-if="problem" class="signin-problem" role="alert" data-testid="ceremony-problem">{{ problem }}</p>
    </div>
    <p class="signin-foot">Only this factory's own origin can use its passkeys. Nothing is shown here until you sign in.</p>
  </main>
</template>
