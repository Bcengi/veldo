<script setup lang="ts">
import { computed, onMounted, ref, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { readConfigurationModel } from '@/api/reads'
import { ApiRefusal } from '@/api/refusal'
import { readWorkflow, saveWorkflow, type WorkflowDocument } from '@/api/workflows'
import RefusalNotice from '@/components/RefusalNotice.vue'
import ScreenHeader from '@/components/ScreenHeader.vue'
import StatePanel from '@/components/StatePanel.vue'
import VButton from '@/components/VButton.vue'
import { useAsync } from '@/composables/useAsync'
import { useDesktop } from '@/composables/useMedia'
import { namedRoles } from '@/features/configuration/configuration'
import FactorySheet from '@/features/factory/FactorySheet.vue'
import FlowCanvas from '@/features/workflow/FlowCanvas.vue'
import FlowProperties from '@/features/workflow/FlowProperties.vue'
import LiveMeta from '@/features/factory/LiveMeta.vue'
import {
  KINDS, addNode, connect, moveNode, orderedIds, problems, removeNode, reorder, same, transitionOf, type Draft,
} from '@/features/workflow/workflow-doc'
import '@/styles/factory.css'

/** The workflow/pipeline editor (VELDO-0131) over VELDO-0132's workflow data: a canvas, a palette and the
 * properties of the selected step or transition, with an ordered list of steps and their transitions that does
 * everything the canvas does by keyboard and touch (add, connect, reorder, select). Save sends the definition and
 * layout to workflows.save edited from the version shown; it stores a new version and runs nothing. */
const route = useRoute()
const router = useRouter()
const desktop = useDesktop()
const name = computed(() => (typeof route.params.workflow === 'string' ? route.params.workflow : ''))
const configuration = useAsync(readConfigurationModel)
const workflows = computed(() =>
  (configuration.data.value?.items.workflow_head ?? []).map((i) => String((i.data as { workflow?: unknown }).workflow ?? i.id)).sort(),
)
const roles = computed(() => [...namedRoles(configuration.data.value).keys()].sort())
const doc = shallowRef<WorkflowDocument | null>(null)
const readAt = ref<number | null>(null)
const load = useAsync(
  async (signal) => {
    const answer = await readWorkflow(name.value, undefined, signal)
    doc.value = answer.definition ? answer : null
    readAt.value = Date.now()
    return answer
  },
  (answer) => !answer.definition,
)
const draft = ref<Draft | null>(null)
const stored = computed<Draft | null>(() => (doc.value ? { definition: doc.value.definition, layout: doc.value.layout ?? {} } : null))
watch(stored, (s) => (draft.value = s ? JSON.parse(JSON.stringify(s)) : null))
const edited = computed(() => !!draft.value && !!stored.value && !same(draft.value, stored.value))
const issues = computed(() => (draft.value ? problems(draft.value) : []))
const selected = ref<{ kind: 'node' | 'edge'; id: string } | null>(null)
const sheet = ref(false)
const saving = ref(false)
const saved = ref<number | null>(null)
const refusal = ref<ApiRefusal | null>(null)
const announce = ref('')

const edge = computed(() => (selected.value?.kind === 'edge' && draft.value ? draft.value.definition.transitions.find((t) => t.id === selected.value!.id) ?? null : null))

function apply(next: Draft, words?: string) {
  draft.value = next
  saved.value = null
  if (words) announce.value = words
}
function select(target: { kind: 'node' | 'edge'; id: string }) {
  selected.value = target
  if (!desktop.value) sheet.value = true
}
function add(kind: string) {
  if (!draft.value) return
  const { draft: next, id } = addNode(draft.value, kind)
  apply(next, `Added ${id}.`)
  select({ kind: 'node', id })
}
function remove() {
  if (!draft.value || !selected.value) return
  if (selected.value.kind === 'node') apply(removeNode(draft.value, selected.value.id), `Removed ${selected.value.id}.`)
  else if (edge.value) apply(connect(draft.value, edge.value.from, edge.value.port, ''), `Removed transition ${edge.value.id}.`)
  selected.value = null
  sheet.value = false
}
async function save() {
  if (!draft.value || !doc.value || saving.value) return
  saving.value = true
  refusal.value = null
  try {
    const answer = await saveWorkflow(doc.value.workflow, doc.value.version, draft.value.definition, draft.value.layout)
    saved.value = answer.version
    await load.run()
    saved.value = answer.version
    announce.value = `Saved as version ${answer.version}.`
  } catch (error) {
    refusal.value = error instanceof ApiRefusal ? error : new ApiRefusal(0, 'unavailable:network', 'unavailable')
  } finally {
    saving.value = false
  }
}
async function reload() {
  refusal.value = null
  saved.value = null
  await load.run()
}
watch(name, (n) => {
  selected.value = null
  if (n) void load.run()
})
onMounted(async () => {
  await configuration.run()
  if (!name.value && workflows.value.length) await router.replace({ name: 'workflow', params: { workflow: workflows.value[0] } })
  else if (name.value) await load.run()
})
const label = (id: string) => `${id} (${KINDS[draft.value?.definition.nodes[id]?.kind ?? '']?.label ?? draft.value?.definition.nodes[id]?.kind})`
</script>

<template>
  <section class="screen screen-wide">
    <ScreenHeader :title="name ? `Workflow ${name}` : 'Workflows'" />
    <p class="sr-only" aria-live="polite" data-testid="flow-announce">{{ announce }}</p>
    <LiveMeta v-if="load.data.value" live="idle" :seq="load.data.value.watermark?.seq ?? null" :freshness="load.data.value.freshness ?? null" :read-at="readAt" />
    <div class="factory-actions">
      <div class="factory-search">
        <label for="workflow-pick" class="field-label">Workflow</label>
        <select id="workflow-pick" class="factory-select" :value="name" data-testid="workflow-pick" @change="router.push({ name: 'workflow', params: { workflow: ($event.target as HTMLSelectElement).value } })">
          <option v-for="w in workflows" :key="w" :value="w">{{ w }}</option>
        </select>
      </div>
    </div>
    <StatePanel v-if="configuration.state.value !== 'ready' || !name" :state="!name && configuration.state.value === 'ready' ? 'empty' : configuration.state.value" :refusal="configuration.refusal.value" empty-title="No workflow yet" empty-body="Workflows appear here once one is saved." loading-label="Loading workflows" @retry="configuration.run()" />
    <StatePanel v-else :state="load.state.value" :refusal="load.refusal.value" empty-title="No such workflow in your scope" empty-body="The API serves no workflow by this name to you." loading-label="Loading the workflow" shape="block" @retry="load.run()">
      <div v-if="draft && doc" class="factory-grid factory-split" data-testid="workflow-editor">
        <div class="factory-grid">
          <section class="panel" aria-labelledby="flow-state-title">
            <h2 id="flow-state-title" class="panel-title">
              Version {{ doc.version }}
              <span class="factory-tag" :class="edited ? 'is-waiting' : 'is-done'" data-testid="flow-state" :data-state="saving ? 'saving' : edited ? 'edited' : 'saved'">
                {{ saving ? 'Saving' : edited ? 'Edited, not saved' : saved ? `Saved as version ${saved}` : 'Saved' }}
              </span>
            </h2>
            <div class="factory-body">
              <div class="flow-palette" role="group" aria-label="Add a step">
                <VButton v-for="(kind, key) in KINDS" :key="key" :label="`Add ${kind.label.toLowerCase()}`" size="small" variant="secondary" :data-testid="`add-${key}`" @click="add(key)" />
              </div>
              <FlowCanvas :draft="draft" :selected="selected" @select="select" @move="(id, x, y) => apply(moveNode(draft!, id, x, y))" />
              <ul v-if="issues.length" class="factory-list" aria-label="Not ready to save" data-testid="flow-issues">
                <li v-for="issue in issues" :key="issue" class="factory-meta">{{ issue }}</li>
              </ul>
              <div class="factory-actions">
                <VButton label="Save workflow" pending-label="Saving" :pending="saving" :disabled="!edited" data-testid="flow-save" @click="save" />
                <VButton v-if="edited" label="Discard changes" variant="secondary" @click="draft = JSON.parse(JSON.stringify(stored))" />
              </div>
              <RefusalNotice v-if="refusal" :refusal="refusal" compact>
                <VButton v-if="refusal.error === 'stale_version'" label="Load the current version" variant="secondary" size="small" data-testid="flow-reload" @click="reload" />
              </RefusalNotice>
              <p class="factory-meta">Saving stores a new version of the workflow's data. It runs nothing; work only starts through the factory's own admission.</p>
            </div>
          </section>
          <section class="panel" aria-labelledby="flow-list-title" data-testid="flow-list">
            <h2 id="flow-list-title" class="panel-title">Steps in order <span class="panel-count">{{ orderedIds(draft).length }}</span></h2>
            <ol class="factory-body flow-order">
              <li v-for="(id, index) in orderedIds(draft)" :key="id" :aria-current="selected?.kind === 'node' && selected.id === id ? 'true' : undefined" :data-step="id">
                <VButton :label="label(id)" variant="quiet" size="small" :aria-label="`Select step ${id}`" data-testid="step-select" @click="select({ kind: 'node', id })" />
                <span class="factory-actions">
                  <VButton label="Up" size="small" variant="secondary" :disabled="index === 0" :aria-label="`Move ${id} up`" @click="apply(reorder(draft!, id, -1), `${id} moved up.`)" />
                  <VButton label="Down" size="small" variant="secondary" :disabled="index === orderedIds(draft).length - 1" :aria-label="`Move ${id} down`" @click="apply(reorder(draft!, id, 1), `${id} moved down.`)" />
                </span>
                <ul class="factory-list" :aria-label="`Transitions from ${id}`">
                  <li v-for="port in KINDS[draft.definition.nodes[id]!.kind]?.ports ?? []" :key="port" class="factory-meta" :data-port="`${id}.${port}`">
                    <VButton
                      v-if="transitionOf(draft, id, port)"
                      :label="`${port} to ${transitionOf(draft, id, port)!.to}`"
                      variant="quiet"
                      size="small"
                      :aria-label="`Select transition ${port} from ${id} to ${transitionOf(draft, id, port)!.to}`"
                      @click="select({ kind: 'edge', id: transitionOf(draft, id, port)!.id })"
                    />
                    <span v-else>{{ port }}: not connected</span>
                  </li>
                </ul>
              </li>
            </ol>
          </section>
        </div>
        <section v-if="desktop" class="panel" aria-labelledby="flow-props-title" data-testid="flow-props">
          <h2 id="flow-props-title" class="panel-title">Properties</h2>
          <div class="factory-body">
            <FlowProperties
              v-if="selected"
              :draft="draft"
              :selected="selected"
              :roles="roles"
              @change="(next, words) => apply(next, words)"
              @remove="remove"
            />
            <p v-else class="factory-meta">Select a step or a transition on the canvas or in the list.</p>
          </div>
        </section>
      </div>
      <FactorySheet v-if="!desktop && sheet && selected && draft" id="flow-sheet" :title="selected.kind === 'node' ? `Step ${selected.id}` : `Transition ${selected.id}`" @close="sheet = false">
        <FlowProperties :draft="draft" :selected="selected" :roles="roles" @change="(next, words) => apply(next, words)" @remove="remove" />
      </FactorySheet>
    </StatePanel>
  </section>
</template>

