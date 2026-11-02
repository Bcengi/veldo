<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { readObjectives } from '@/api/reads'
import ScreenHeader from '@/components/ScreenHeader.vue'
import StatePanel from '@/components/StatePanel.vue'
import VButton from '@/components/VButton.vue'
import { useDesktop } from '@/composables/useMedia'
import { useLiveRead } from '@/composables/useLiveRead'
import FactorySheet from '@/features/factory/FactorySheet.vue'
import LiveMeta from '@/features/factory/LiveMeta.vue'
import MessageBox from '@/features/projects/MessageBox.vue'
import { intakeOf, projectsOf, searchProjects } from '@/features/projects/projects'
import '@/styles/factory.css'

/** Objectives and projects (VELDO-0131): a searchable list of projects, the selected project's objectives with
 * their evidence and status, and the message box to the factory beside them (a sheet on a phone, opened from a
 * message button that stays on screen). */
const route = useRoute()
const router = useRouter()
const desktop = useDesktop()
const live = useLiveRead(readObjectives, (a) => a.watermark, (a) => (a.items.project ?? []).length === 0)
const query = ref('')
const projects = computed(() => projectsOf(live.data.value))
const shown = computed(() => searchProjects(projects.value, query.value))
const selectedName = computed(() => (typeof route.params.project === 'string' ? route.params.project : null))
const selected = computed(() => projects.value.find((p) => p.name === selectedName.value) ?? (desktop.value ? shown.value[0] ?? null : null))
const intake = computed(() => intakeOf(live.data.value))
const chat = ref(false)
const STATE_TONE: Record<string, string> = { ACTIVE: '', SATISFIED: 'is-done', ACCEPTED: '', PROPOSED: 'is-waiting', BLOCKED: 'is-stop', PAUSED: 'is-waiting', CANCELED: 'is-stop', REJECTED: 'is-stop', COMPLETED: 'is-done' }
const open = (name: string) => router.push({ name: 'project', params: { project: name } })
onMounted(() => void live.start())
</script>

<template>
  <section class="screen screen-wide">
    <ScreenHeader :title="selected && !desktop ? selected.name : 'Projects'" :back="selected && !desktop ? { to: { name: 'projects' }, label: 'Projects' } : undefined">
      <template #aside>
        <VButton label="Refresh" variant="quiet" size="small" :pending="live.state.value === 'loading'" pending-label="Refreshing" @click="live.refresh()" />
      </template>
    </ScreenHeader>
    <LiveMeta :live="live.live.value" :seq="live.data.value?.watermark.seq ?? null" :freshness="live.data.value?.freshness ?? null" :read-at="live.readAt.value" />
    <StatePanel
      :state="live.state.value"
      :refusal="live.refusal.value"
      empty-title="No project yet"
      empty-body="Projects appear here once one is activated. Send a message to the factory to propose one."
      loading-label="Loading projects"
      @retry="live.refresh()"
    >
      <div class="factory-grid factory-split">
        <div class="factory-grid">
          <section v-if="desktop || !selected" class="panel" aria-labelledby="projects-title" data-testid="projects">
            <h2 id="projects-title" class="panel-title">Projects <span class="panel-count">{{ shown.length }}</span></h2>
            <div class="factory-body">
              <div class="factory-search">
                <label for="projects-search" class="field-label">Search projects and objectives</label>
                <input id="projects-search" v-model="query" type="search" autocomplete="off" data-testid="projects-search" />
              </div>
              <ul class="factory-list">
                <li v-for="project in shown" :key="project.name" class="factory-card" :aria-current="selected?.name === project.name ? 'true' : undefined" :data-project="project.name">
                  <button type="button" class="factory-card-button" @click="open(project.name)">
                    <span class="factory-card-title">{{ project.name }}</span>
                    <span class="factory-meta">
                      <span class="factory-tag" :class="STATE_TONE[project.state]">{{ project.state }}</span>
                      <span>{{ project.objectives.length }} objective{{ project.objectives.length === 1 ? '' : 's' }}</span>
                      <span v-if="project.owner">Owner {{ project.owner }}</span>
                    </span>
                    <span v-if="project.purpose">{{ project.purpose }}</span>
                  </button>
                </li>
                <li v-if="!shown.length" class="factory-meta">No project matches.</li>
              </ul>
            </div>
          </section>
          <section v-if="selected" class="panel" aria-labelledby="project-detail" data-testid="project-detail" :data-project="selected.name">
            <h2 id="project-detail" class="panel-title">{{ selected.name }} <span class="factory-tag" :class="STATE_TONE[selected.state]">{{ selected.state }}</span></h2>
            <div class="factory-body">
              <p v-if="selected.purpose">{{ selected.purpose }}</p>
              <h3 class="panel-title">Objectives <span class="panel-count">{{ selected.objectives.length }}</span></h3>
              <ul class="factory-list">
                <li v-for="objective in selected.objectives" :key="objective.id" class="factory-card" :data-objective="objective.id" :data-state="objective.state">
                  <span class="factory-card-title">{{ objective.outcome }}</span>
                  <span class="factory-meta">
                    <span class="factory-tag" :class="STATE_TONE[objective.state]">{{ objective.state }}</span>
                    <span>{{ objective.features }} feature{{ objective.features === 1 ? '' : 's' }}</span>
                    <span v-if="objective.assessment">Assessment: {{ objective.assessment }}</span>
                  </span>
                  <dl class="factory-facts">
                    <dt>Scope</dt><dd>{{ objective.scope.join(', ') || 'none' }}</dd>
                    <dt>Evidence</dt><dd>{{ objective.evidence.map((e) => `${e.id} (${e.kind})`).join(', ') || 'none required' }}</dd>
                    <dt>Version</dt><dd>{{ objective.version }}</dd>
                  </dl>
                </li>
                <li v-if="!selected.objectives.length" class="factory-meta">No objective yet.</li>
              </ul>
            </div>
          </section>
        </div>
        <section v-if="desktop" class="panel" aria-labelledby="chat-title">
          <h2 id="chat-title" class="panel-title">Message the factory</h2>
          <div class="factory-body"><MessageBox :entries="intake" :project="selected?.name ?? null" id-prefix="desk" @sent="live.refresh()" /></div>
        </section>
      </div>
    </StatePanel>
    <VButton v-if="!desktop && !chat" class="factory-fab" label="Message" data-testid="message-open" @click="chat = true" />
    <FactorySheet v-if="!desktop && chat" id="chat-sheet" title="Message the factory" @close="chat = false">
      <MessageBox :entries="intake" :project="selected?.name ?? null" id-prefix="phone" @sent="live.refresh()" />
    </FactorySheet>
  </section>
</template>
