<script setup lang="ts">
import { ref } from 'vue'
import { reconcileSpace } from '@/api/actions'
import { ApiRefusal } from '@/api/refusal'
import VButton from '@/components/VButton.vue'
import { gapSentence, type ActionAvailability } from '@/features/contract/gaps'

/** Reconcile (design 6.6): the owner's signed command that runs a reconcile now, for one project or all, sent to
 * `space.reconcile`. The result is the API's, beside the control; a refusal is named. What the reconcile found
 * reaches the screen as the ledger's records do, through the journal. */
const props = defineProps<{ projects: string[]; action: ActionAvailability }>()
const project = ref('')
const sending = ref(false)
const result = ref<{ text: string; refusal: string | null } | null>(null)

async function run() {
  sending.value = true
  result.value = null
  const scope = project.value || null
  let text: string
  let refusal: string | null = null
  try {
    const sent = await reconcileSpace(scope, props.action.route)
    text = sent.sent
      ? `Reconcile ran for ${scope ?? 'every project'} (${sent.answer.outcome}). What it found is on this screen as the ledger recorded it.`
      : `Not run: the API publishes no route ${sent.route}. ${gapSentence(props.action)}`
    if (!sent.sent) refusal = 'missing_evidence:route'
  } catch (error) {
    refusal = error instanceof ApiRefusal ? error.refusal : 'unavailable_service'
    text = error instanceof ApiRefusal ? `Not run: ${error.refusal}` : `Not run: ${(error as Error).message}`
  } finally {
    sending.value = false
  }
  result.value = { text, refusal }
}
</script>

<template>
  <section class="panel" aria-labelledby="space-reconcile-title" data-testid="space-reconcile">
    <h2 id="space-reconcile-title" class="panel-title">Reconcile</h2>
    <div class="factory-body">
      <p class="space-note">Read what is on disk and in Docker again and bring the ledger in line with it. A reconcile in report mode removes nothing.</p>
      <form class="space-form" @submit.prevent="run">
        <div class="factory-search">
          <label for="space-reconcile-project" class="field-label">For</label>
          <select id="space-reconcile-project" v-model="project" class="factory-select" data-testid="space-reconcile-project">
            <option value="">Every project</option>
            <option v-for="name in props.projects" :key="name" :value="name">{{ name }}</option>
          </select>
        </div>
        <VButton type="submit" label="Reconcile now" :pending="sending" pending-label="Reconciling" data-testid="space-reconcile-run" />
      </form>
      <p v-if="result" class="factory-gap" role="alert" data-testid="space-reconcile-result" :data-refusal="result.refusal ?? undefined">{{ result.text }}</p>
    </div>
  </section>
</template>
