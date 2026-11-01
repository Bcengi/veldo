<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { DEFAULT_TEAM } from '@/api/configuration'
import RefusalNotice from '@/components/RefusalNotice.vue'
import ScreenHeader from '@/components/ScreenHeader.vue'
import StatePanel from '@/components/StatePanel.vue'
import VButton from '@/components/VButton.vue'
import VTextField from '@/components/VTextField.vue'
import { KINDS } from '@/features/team/team-draft'
import { useTeamForm } from '@/features/team/useTeamForm'
import '@/styles/configure.css'

/** A project's team roles, or the factory's default team (VELDO-0163 AC2). The team shown current is only
 * what the team route reads back after the authority accepted it; another member's proposal waits on the
 * project owner's answer in the decisions screen. */
const route = useRoute()
const router = useRouter()
const form = useTeamForm()
const projectName = ref('')
const newRole = ref('')
const draft = computed(() => form.draft.value)
const param = computed(() => (typeof route.params.project === 'string' ? route.params.project : ''))
const title = computed(() => (form.isDefault.value ? 'the default team' : `the team of ${form.project.value}`))

function go(name: string) {
  const project = name.trim()
  if (!project) return
  if (project === param.value) void form.open(project)
  else void router.push({ name: 'team', params: { project } })
}
watch(param, (name) => {
  projectName.value = name === DEFAULT_TEAM ? '' : name
  if (name) void form.open(name)
})
onMounted(() => {
  projectName.value = param.value === DEFAULT_TEAM ? '' : param.value
  if (param.value) void form.open(param.value)
})

function add() {
  if (form.addRole(newRole.value)) newRole.value = ''
}

const outcome = computed(() => {
  const answer = form.answer.value
  if (!answer) return null
  if (answer.outcome === 'proposed')
    return `Proposed as revision ${answer.revision}. It becomes current only when the project owner answers it in Decisions.`
  const current = form.current.value
  return current ? `Saved. Revision ${current.revision} is current.` : 'Saved.'
})
const request = computed(() => form.answer.value?.owner_request ?? null)
</script>

<template>
  <section class="screen screen-narrow configure">
    <ScreenHeader title="Team">
      <span class="screen-meta-text">A project's team roles, each naming its capability configuration and kind.</span>
    </ScreenHeader>

    <form class="panel configure-open" @submit.prevent="go(projectName)">
      <label class="field-label" for="team-project">Project</label>
      <div class="configure-inline">
        <VTextField id="team-project" v-model="projectName" autocomplete="off" spellcheck="false" placeholder="project-a" data-testid="team-project" />
        <VButton label="Open" type="submit" variant="secondary" data-testid="team-open" />
      </div>
      <VButton label="Open the default team" variant="quiet" size="small" data-testid="team-open-default" @click="go(DEFAULT_TEAM)" />
    </form>

    <StatePanel v-if="param || form.state.value !== 'idle'" :state="form.state.value" :refusal="form.refusal.value" shape="block" loading-label="Reading the team" @retry="go(param)">
      <div v-if="draft" class="configure-form">
        <section class="panel configure-section" aria-labelledby="team-status">
          <h2 id="team-status" class="panel-title">{{ form.isDefault.value ? 'Default team' : `Team of ${form.project.value}` }}</h2>
          <p class="configure-fact" data-testid="team-current" :data-revision="form.current.value?.revision ?? 0">
            {{ form.current.value ? `Current: revision ${form.current.value.revision}` : `No revision of ${title} is saved yet` }}
          </p>
          <p v-if="form.pending.value" class="configure-pending" data-testid="team-pending" :data-revision="form.pending.value.revision">
            Pending: revision {{ form.pending.value.revision }}{{ form.pending.value.proposed_by ? ` proposed by ${form.pending.value.proposed_by}` : '' }},
            waiting on the project owner's answer. It is not current.
          </p>
          <p class="configure-fact configure-muted" data-testid="team-edited-from" :data-version="draft.editedFrom">
            Editing from {{ form.isDefault.value ? 'revision' : 'team version' }} {{ draft.editedFrom }}
          </p>
          <VButton label="Read again" variant="quiet" size="small" data-testid="team-reload" @click="form.reload()" />
        </section>

        <fieldset v-for="(row, i) in draft.rows" :key="row.name" class="panel configure-section configure-role" :data-testid="`team-role-${row.name}`">
          <legend class="panel-title">{{ row.name }}</legend>
          <div class="configure-grid">
            <div>
              <label class="field-label" :for="`kind-${i}`">Kind</label>
              <select :id="`kind-${i}`" v-model="row.kind" class="vfield" :data-testid="`kind-${row.name}`"><option v-for="k in KINDS" :key="k" :value="k">{{ k }}</option></select>
            </div>
            <div>
              <label class="field-label" :for="`config-role-${i}`">Capability configuration</label>
              <VTextField :id="`config-role-${i}`" v-model="row.configRole" autocomplete="off" spellcheck="false" :data-testid="`config-role-${row.name}`" />
            </div>
            <div>
              <label class="field-label" :for="`config-revision-${i}`">Its revision</label>
              <VTextField :id="`config-revision-${i}`" v-model="row.configRevision" inputmode="numeric" :data-testid="`config-revision-${row.name}`" />
            </div>
            <div>
              <label class="field-label" :for="`workers-${i}`">Workers</label>
              <VTextField :id="`workers-${i}`" v-model="row.workers" autocomplete="off" spellcheck="false" :data-testid="`workers-${row.name}`" />
            </div>
            <div>
              <label class="field-label" :for="`responsibilities-${i}`">Responsibilities</label>
              <VTextField :id="`responsibilities-${i}`" v-model="row.responsibilities" autocomplete="off" :data-testid="`responsibilities-${row.name}`" />
            </div>
            <div>
              <label class="field-label" :for="`expertise-${i}`">Expertise</label>
              <VTextField :id="`expertise-${i}`" v-model="row.expertise" autocomplete="off" :data-testid="`expertise-${row.name}`" />
            </div>
            <div>
              <label class="field-label" :for="`permissions-${i}`">May propose</label>
              <VTextField :id="`permissions-${i}`" v-model="row.permissions" autocomplete="off" spellcheck="false" :data-testid="`permissions-${row.name}`" />
            </div>
            <div>
              <label class="field-label" :for="`engines-${i}`">Engines</label>
              <VTextField :id="`engines-${i}`" v-model="row.engines" autocomplete="off" spellcheck="false" :data-testid="`engines-${row.name}`" />
            </div>
            <div>
              <label class="field-label" :for="`capacity-${i}`">Capacity</label>
              <VTextField :id="`capacity-${i}`" v-model="row.capacity" inputmode="numeric" :data-testid="`capacity-${row.name}`" />
            </div>
            <div>
              <label class="field-label" :for="`invocations-${i}`">Invocations</label>
              <VTextField :id="`invocations-${i}`" v-model="row.invocations" inputmode="numeric" :data-testid="`invocations-${row.name}`" />
            </div>
            <div>
              <label class="field-label" :for="`wall-${i}`">Wall seconds</label>
              <VTextField :id="`wall-${i}`" v-model="row.wallSeconds" inputmode="numeric" :data-testid="`wall-${row.name}`" />
            </div>
            <div>
              <label class="field-label" :for="`distinct-${i}`">Independent of roles</label>
              <VTextField :id="`distinct-${i}`" v-model="row.distinctFrom" autocomplete="off" spellcheck="false" />
            </div>
          </div>
          <VButton :label="`Remove ${row.name}`" variant="danger" size="small" :data-testid="`remove-${row.name}`" @click="form.removeRole(row.name)" />
        </fieldset>
        <p v-if="!draft.rows.length" class="configure-none">No roles yet. Add the four required roles: project_manager, elaboration, implementation and independent_review.</p>

        <form class="panel configure-section configure-add" @submit.prevent="add">
          <label class="field-label" for="new-role">Add a role</label>
          <div class="configure-inline">
            <VTextField id="new-role" v-model="newRole" autocomplete="off" spellcheck="false" placeholder="builder_jira" data-testid="new-role" />
            <VButton label="Add role" type="submit" variant="secondary" data-testid="add-role" />
          </div>
        </form>

        <div class="configure-save" data-testid="team-save-bar">
          <RefusalNotice v-if="form.saveRefusal.value" :refusal="form.saveRefusal.value" compact />
          <p v-else-if="outcome" class="configure-outcome" role="status" data-testid="team-outcome" :data-outcome="form.answer.value?.outcome">
            {{ outcome }}
            <RouterLink v-if="request && form.answer.value?.outcome === 'proposed'" :to="{ name: 'decision', params: { request: request.split('/') } }" class="panel-link">Open the request</RouterLink>
          </p>
          <VButton :label="form.isDefault.value ? 'Save the default team' : 'Save the team'" pending-label="Saving" :pending="form.saving.value" data-testid="team-save" @click="form.save()" />
        </div>
      </div>
    </StatePanel>
  </section>
</template>
