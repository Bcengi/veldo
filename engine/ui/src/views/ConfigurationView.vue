<script setup lang="ts">
import { computed, onMounted, ref, shallowRef } from 'vue'
import { readConfiguration, type ConfigurationRevision } from '@/api/configuration'
import { readConfigurationModel } from '@/api/reads'
import { isRefusal } from '@/api/refusal'
import ScreenHeader from '@/components/ScreenHeader.vue'
import StatePanel from '@/components/StatePanel.vue'
import VButton from '@/components/VButton.vue'
import { useDesktop } from '@/composables/useMedia'
import { useLiveRead } from '@/composables/useLiveRead'
import { namedRoles, roleView, skillsOf, storedRoles, teamsOf, type RoleView } from '@/features/configuration/configuration'
import LiveMeta from '@/features/factory/LiveMeta.vue'
import '@/styles/factory.css'

/** Team and agent/tool/MCP configuration (VELDO-0131): the teams of the configuration read and every stored
 * capability configuration (named by a team or not), each with its revision history and the exact tools, MCP
 * servers and skills of the selected revision, and every stored skill, opening VELDO-0163's role and team forms
 * to edit them. A configuration a team names that the read does not serve is read through configurations.read. */
const roles = shallowRef<RoleView[]>([])
async function revisions(role: string, signal: AbortSignal): Promise<ConfigurationRevision[]> {
  const out: ConfigurationRevision[] = []
  for (let revision = 1; revision < 500; revision += 1) {
    try {
      out.push(await readConfiguration(role, revision, signal))
    } catch (error) {
      if (isRefusal(error) && error.error === 'missing_evidence') break
      throw error
    }
  }
  return out
}
const live = useLiveRead(
  async (signal) => {
    const answer = await readConfigurationModel(signal)
    const named = namedRoles(answer)
    const stored = storedRoles(answer)
    const views: RoleView[] = []
    for (const role of [...new Set([...stored.keys(), ...named.keys()])].sort((a, b) => a.localeCompare(b))) {
      const view = roleView(role, stored.get(role) ?? (await revisions(role, signal)), named.get(role) ?? [])
      if (view) views.push(view)
    }
    roles.value = views
    return answer
  },
  (a) => a.watermark,
  (a) => ['team', 'default_team_revision', 'agent_configuration', 'agent_skill'].every((k) => (a.items[k] ?? []).length === 0),
)
const desktop = useDesktop()
const teams = computed(() => teamsOf(live.data.value))
const skills = computed(() => skillsOf(live.data.value))
const picked = ref<Record<string, number>>({})
const shown = (role: RoleView) => role.history.find((r) => r.revision === picked.value[role.role]) ?? role.current
onMounted(() => void live.start())
</script>

<template>
  <section class="screen screen-wide">
    <ScreenHeader title="Configuration">
      <template #aside>
        <VButton label="Refresh" variant="secondary" size="small" :pending="live.state.value === 'loading'" pending-label="Refreshing" @click="live.refresh()" />
      </template>
    </ScreenHeader>
    <LiveMeta :live="live.live.value" :seq="live.data.value?.watermark.seq ?? null" :freshness="live.data.value?.freshness ?? null" :read-at="live.readAt.value" />
    <StatePanel
      :state="live.state.value"
      :refusal="live.refusal.value"
      empty-title="No configuration yet"
      empty-body="Capability configurations, skills and teams appear here once one is saved."
      loading-label="Loading configuration"
      @retry="live.refresh()"
    >
      <div class="factory-grid" data-testid="configuration">
        <section class="panel" aria-labelledby="roles-title" data-testid="roles-table">
          <h2 id="roles-title" class="panel-title">Roles <span class="panel-count">{{ roles.length }}</span></h2>
          <div class="factory-body">
            <div v-if="desktop" class="factory-table-wrap">
              <table class="factory-table" aria-label="Capability configurations">
                <thead><tr><th scope="col">Configuration</th><th scope="col">Revision</th><th scope="col">Engine</th><th scope="col">Native tools</th><th scope="col">MCP servers</th><th scope="col">Skills</th><th scope="col">Teams</th><th scope="col"><span class="sr-only">Actions</span></th></tr></thead>
                <tbody>
                  <tr v-for="role in roles" :key="role.role" :data-role="role.role" :data-revision="shown(role).revision">
                    <td>{{ role.role }}</td>
                    <td>
                      <label :for="`rev-${role.role}`" class="sr-only">Revision of {{ role.role }}</label>
                      <select :id="`rev-${role.role}`" class="factory-select" :value="shown(role).revision" data-testid="role-revision" @change="picked = { ...picked, [role.role]: Number(($event.target as HTMLSelectElement).value) }">
                        <option v-for="r in role.history" :key="r.revision" :value="r.revision">{{ r.revision }}{{ r.revision === role.current.revision ? ' (current)' : '' }}</option>
                      </select>
                    </td>
                    <td>{{ shown(role).engine }}</td>
                    <td>{{ shown(role).tools.join(', ') || 'none' }}</td>
                    <td>{{ shown(role).servers.join('; ') || 'none' }}</td>
                    <td>{{ shown(role).skills.join(', ') || 'none' }}</td>
                    <td>{{ role.teams.join(', ') || 'no team' }}</td>
                    <td><RouterLink :to="{ name: 'role', params: { role: role.role } }" class="vbtn vbtn-secondary vbtn-small" :aria-label="`Edit ${role.role}`" data-testid="role-edit">Edit</RouterLink></td>
                  </tr>
                </tbody>
              </table>
            </div>
            <ul v-else class="factory-list">
              <li v-for="role in roles" :key="role.role" class="factory-card" :data-role="role.role" :data-revision="shown(role).revision">
                <span class="factory-card-title">{{ role.role }} <span class="factory-tag">revision {{ shown(role).revision }}</span></span>
                <div class="factory-search">
                  <label :for="`rev-p-${role.role}`" class="field-label">Revision</label>
                  <select :id="`rev-p-${role.role}`" class="factory-select" :value="shown(role).revision" data-testid="role-revision" @change="picked = { ...picked, [role.role]: Number(($event.target as HTMLSelectElement).value) }">
                    <option v-for="r in role.history" :key="r.revision" :value="r.revision">{{ r.revision }}{{ r.revision === role.current.revision ? ' (current)' : '' }}</option>
                  </select>
                </div>
                <dl class="factory-facts">
                  <dt>Engine</dt><dd>{{ shown(role).engine }}</dd>
                  <dt>Native tools</dt><dd>{{ shown(role).tools.join(', ') || 'none' }}</dd>
                  <dt>MCP servers</dt><dd>{{ shown(role).servers.join('; ') || 'none' }}</dd>
                  <dt>Skills</dt><dd>{{ shown(role).skills.join(', ') || 'none' }}</dd>
                  <dt>Teams</dt><dd>{{ role.teams.join(', ') || 'no team' }}</dd>
                </dl>
                <RouterLink :to="{ name: 'role', params: { role: role.role } }" class="vbtn vbtn-secondary vbtn-block" :aria-label="`Edit ${role.role}`" data-testid="role-edit">Edit</RouterLink>
              </li>
            </ul>
          </div>
        </section>
        <section class="panel" aria-labelledby="skills-title" data-testid="skills">
          <h2 id="skills-title" class="panel-title">Skills <span class="panel-count">{{ skills.length }}</span></h2>
          <p v-if="!skills.length" class="factory-body factory-meta">No skill is stored yet.</p>
          <ul v-else class="factory-body factory-list">
            <li v-for="skill in skills" :key="`${skill.skill}-${skill.revision}`" class="factory-card" :data-skill="skill.skill">
              <span class="factory-card-title">{{ skill.skill }} <span class="factory-tag">revision {{ skill.revision }}</span></span>
              <span class="factory-meta">{{ skill.source }}: {{ skill.path }}</span>
            </li>
          </ul>
        </section>
        <section class="panel" aria-labelledby="teams-title" data-testid="teams">
          <h2 id="teams-title" class="panel-title">Teams <span class="panel-count">{{ teams.length }}</span></h2>
          <ul class="factory-body factory-list">
            <li v-for="team in teams" :key="team.id" class="factory-card" :data-team="team.project">
              <span class="factory-card-title">{{ team.project === 'default' ? 'Default team' : team.project }}
                <span class="factory-tag">{{ team.project === 'default' ? 'revision' : 'version' }} {{ team.version }}</span>
                <span v-if="team.pending" class="factory-tag is-waiting">Proposal waiting</span>
              </span>
              <span class="factory-meta">{{ team.roles.join(', ') }}</span>
              <RouterLink :to="{ name: 'team', params: { project: team.project } }" class="vbtn vbtn-secondary vbtn-small" :aria-label="`Edit the team of ${team.project}`" data-testid="team-edit">Edit team</RouterLink>
            </li>
          </ul>
        </section>
      </div>
    </StatePanel>
  </section>
</template>
