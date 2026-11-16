<script setup lang="ts">
import { nextTick, ref } from 'vue'
import { abandonWorktree } from '@/api/actions'
import { ApiRefusal } from '@/api/refusal'
import VButton from '@/components/VButton.vue'
import { gapSentence, type ActionAvailability } from '@/features/contract/gaps'
import { abandonText, bytesText, ownerText, type SpaceWorktree } from './space'

/** The worktrees the owner can give up. Abandon asks for an inline confirmation and sends `space.abandon` with the
 * item and the version shown: the owner's signed command, worktree abandoned for that one worktree. It removes no
 * unique work: what the API answers is shown beside the row, and so is a refusal, by its name. The row itself
 * changes only when the ledger's record does. */
const props = defineProps<{ worktrees: SpaceWorktree[]; action: ActionAvailability }>()
const confirming = ref<string | null>(null)
const sending = ref<string | null>(null)
const result = ref<Record<string, { text: string; refusal: string | null }>>({})

async function ask(tree: SpaceWorktree) {
  confirming.value = tree.id
  await nextTick()
  document.querySelector<HTMLElement>(`[data-confirm="${CSS.escape(tree.id)}"] button`)?.focus()
}
async function abandon(tree: SpaceWorktree) {
  confirming.value = null
  sending.value = tree.id
  let text: string
  let refusal: string | null = null
  try {
    const sent = await abandonWorktree(tree.id, tree.version, props.action.route)
    text = sent.sent ? abandonText(sent.answer) : `Not abandoned: the API publishes no route ${sent.route}. ${gapSentence(props.action)}`
    if (!sent.sent) refusal = 'missing_evidence:route'
  } catch (error) {
    refusal = error instanceof ApiRefusal ? error.refusal : 'unavailable_service'
    text = error instanceof ApiRefusal ? `Not abandoned: ${error.refusal}` : `Not abandoned: ${(error as Error).message}`
  } finally {
    sending.value = null
  }
  result.value = { ...result.value, [tree.id]: { text, refusal } }
}
const stateWords = (tree: SpaceWorktree) => (tree.owner_keep ? 'Kept by you' : tree.state === 'deferred' ? 'Deferred' : tree.state === 'kept' ? 'Kept' : 'Present')
</script>

<template>
  <section class="panel" aria-labelledby="space-worktrees-title" data-testid="space-worktrees">
    <h2 id="space-worktrees-title" class="panel-title">Worktrees <span class="panel-count">{{ props.worktrees.length }}</span></h2>
    <div class="factory-body">
      <p v-if="!props.worktrees.length" class="space-note" data-testid="space-worktrees-none">No worktree is recorded that can be abandoned.</p>
      <ul class="factory-list">
        <li v-for="tree in props.worktrees" :key="tree.id" class="factory-card" :data-worktree="tree.id" :data-version="tree.version" :data-state="tree.state">
          <div class="space-head">
            <span class="space-path">{{ tree.locator }}</span>
            <span class="factory-tag" :class="tree.owner_keep ? 'is-done' : ''">{{ stateWords(tree) }}</span>
          </div>
          <dl class="factory-facts">
            <dt>Owner</dt><dd>{{ ownerText(tree.owner) }}</dd>
            <dt>Branch</dt><dd>{{ tree.branch || 'detached' }}</dd>
            <dt>Size</dt><dd>{{ tree.bytes === null ? 'not measured' : bytesText(tree.bytes) }}</dd>
          </dl>
          <div class="factory-actions">
            <VButton v-if="confirming !== tree.id" label="Abandon" variant="danger" size="small" :pending="sending === tree.id" pending-label="Abandoning" :aria-label="`Abandon the worktree ${tree.locator}`" data-testid="space-abandon" @click="ask(tree)" />
            <div v-else class="factory-actions" :data-confirm="tree.id" role="group" :aria-label="`Confirm abandoning ${tree.locator}`">
              <span class="space-note">Abandon this worktree? Work that is in no other place stays until your Discard.</span>
              <VButton label="Abandon the worktree" variant="danger" size="small" data-testid="space-abandon-confirm" @click="abandon(tree)" />
              <VButton label="Keep it" variant="secondary" size="small" @click="confirming = null" />
            </div>
          </div>
          <p v-if="result[tree.id]" class="factory-gap" role="alert" data-testid="space-abandon-result" :data-refusal="result[tree.id]!.refusal ?? undefined">{{ result[tree.id]!.text }}</p>
        </li>
      </ul>
    </div>
  </section>
</template>
