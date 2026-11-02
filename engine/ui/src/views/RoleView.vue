<script setup lang="ts">
import { computed, onMounted, ref, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { latestCatalogServer, type CatalogServer, type LoadMode, type McpSelection } from '@/api/configuration'
import { ApiRefusal } from '@/api/refusal'
import RefusalNotice from '@/components/RefusalNotice.vue'
import ScreenHeader from '@/components/ScreenHeader.vue'
import StatePanel from '@/components/StatePanel.vue'
import VButton from '@/components/VButton.vue'
import VRadio from '@/components/VRadio.vue'
import VTextField from '@/components/VTextField.vue'
import { ENGINES, LOAD_MODES, names } from '@/features/roles/role-draft'
import { useRoleForm } from '@/features/roles/useRoleForm'
import '@/styles/configure.css'

/** A role's capability configuration (VELDO-0163 AC1): engine, native tools, MCP selections from the catalog,
 * skills, instruction files and engine settings, each item with its load mode, saved as a new revision through
 * the configuration route bound to the revision it was edited from. */
const route = useRoute()
const router = useRouter()
const form = useRoleForm()
const roleName = ref('')
const draft = computed(() => form.draft.value)

const serverId = ref('')
const catalog = shallowRef<CatalogServer | null>(null)
const catalogRefusal = shallowRef<ApiRefusal | null>(null)
const catalogBusy = ref(false)
const allTools = ref(true)
const toolList = ref('')
const serverLoad = ref<LoadMode>('always')

const param = computed(() => (typeof route.params.role === 'string' ? route.params.role : ''))

function openRole() {
  const name = roleName.value.trim()
  if (!name) return
  if (name === param.value) void form.open(name)
  else void router.push({ name: 'role', params: { role: name } })
}

watch(
  param,
  (name) => {
    roleName.value = name
    if (name) void form.open(name)
  },
  { immediate: false },
)
onMounted(() => {
  roleName.value = param.value
  if (param.value) void form.open(param.value)
})

async function readCatalog() {
  const id = serverId.value.trim()
  if (!id) return
  catalogBusy.value = true
  catalogRefusal.value = null
  catalog.value = null
  try {
    const found = await latestCatalogServer(id)
    if (!found) catalogRefusal.value = new ApiRefusal(404, 'missing_evidence:mcp_server', 'missing_evidence')
    catalog.value = found
  } catch (error) {
    catalogRefusal.value = error instanceof ApiRefusal ? error : new ApiRefusal(0, 'unavailable:network', 'unavailable')
  } finally {
    catalogBusy.value = false
  }
}

function addServer() {
  const d = draft.value
  const server = catalog.value
  if (!d || !server) return
  const selection: McpSelection = {
    server: server.id,
    revision: server.revision,
    tools: allTools.value ? 'all' : names(toolList.value),
    load: serverLoad.value,
  }
  d.mcp = d.mcp.filter((m) => m.server !== server.id).concat(selection)
  catalog.value = null
  serverId.value = ''
  toolList.value = ''
  allTools.value = true
}

const toolsText = (item: McpSelection) => (item.tools === 'all' ? '' : item.tools.join(', '))
function setAll(item: McpSelection, all: boolean) {
  item.tools = all ? 'all' : []
}
function setTools(item: McpSelection, text: string) {
  item.tools = names(text)
}
function revisionOf(text: string) {
  return /^\d+$/.test(text.trim()) ? Number(text.trim()) : Number.NaN
}
</script>

<template>
  <section class="screen screen-narrow configure">
    <ScreenHeader title="Roles">
      <span class="screen-meta-text">A role's capability configuration. Each save is a new revision.</span>
    </ScreenHeader>

    <form class="panel configure-open" @submit.prevent="openRole">
      <label class="field-label" for="role-name">Role</label>
      <div class="configure-inline">
        <VTextField id="role-name" v-model="roleName" autocomplete="off" spellcheck="false" placeholder="builder_jira" data-testid="role-name" />
        <VButton label="Open" type="submit" variant="secondary" data-testid="role-open" />
      </div>
    </form>

    <StatePanel v-if="param || form.state.value !== 'idle'" :state="form.state.value" :refusal="form.refusal.value" shape="block" loading-label="Reading the role" @retry="openRole">
      <form v-if="draft" class="configure-form" data-testid="role-form" @submit.prevent="form.save()">
        <p class="configure-base" data-testid="role-base" :data-base="draft.editedFrom">
          {{ draft.editedFrom ? `Editing revision ${draft.editedFrom} of ${draft.role}` : `New role ${draft.role}: no revision saved yet` }}
        </p>

        <fieldset class="panel configure-section">
          <legend class="panel-title">Engine</legend>
          <div class="configure-choices">
            <label v-for="engine in ENGINES" :key="engine" class="configure-choice" :for="`engine-${engine}`">
              <VRadio v-model="draft.engine" :value="engine" name="engine" :input-id="`engine-${engine}`" />
              <span>{{ engine }}</span>
            </label>
          </div>
        </fieldset>

        <fieldset class="panel configure-section" data-testid="role-native-tools">
          <legend class="panel-title">Native tools</legend>
          <p v-if="!draft.native_tools.length" class="configure-none">No native tools.</p>
          <div v-for="(item, i) in draft.native_tools" :key="`tool-${i}`" class="configure-row">
            <label class="field-label" :for="`tool-name-${i}`">Tool</label>
            <VTextField :id="`tool-name-${i}`" v-model="item.name" autocomplete="off" spellcheck="false" />
            <label class="field-label" :for="`tool-load-${i}`">Load</label>
            <select :id="`tool-load-${i}`" v-model="item.load" class="vfield"><option v-for="m in LOAD_MODES" :key="m" :value="m">{{ m }}</option></select>
            <VButton label="Remove" variant="quiet" size="small" @click="draft.native_tools.splice(i, 1)" />
          </div>
          <VButton label="Add a native tool" variant="secondary" size="small" data-testid="add-native-tool" @click="draft.native_tools.push({ name: '', load: 'always' })" />
        </fieldset>

        <fieldset class="panel configure-section" data-testid="role-mcp">
          <legend class="panel-title">MCP servers</legend>
          <p v-if="!draft.mcp.length" class="configure-none">No MCP servers.</p>
          <div v-for="(item, i) in draft.mcp" :key="`mcp-${item.server}`" class="configure-row" :data-testid="`mcp-${item.server}`">
            <p class="configure-fact"><strong>{{ item.server }}</strong> revision {{ item.revision }}</p>
            <label class="configure-choice" :for="`mcp-all-${i}`">
              <input :id="`mcp-all-${i}`" type="checkbox" class="configure-check" :checked="item.tools === 'all'" @change="setAll(item, ($event.target as HTMLInputElement).checked)" />
              <span>All its tools</span>
            </label>
            <template v-if="item.tools !== 'all'">
              <label class="field-label" :for="`mcp-tools-${i}`">Tools, separated by commas</label>
              <VTextField :id="`mcp-tools-${i}`" :model-value="toolsText(item)" autocomplete="off" spellcheck="false" @change="setTools(item, ($event.target as HTMLInputElement).value)" />
            </template>
            <label class="field-label" :for="`mcp-load-${i}`">Load</label>
            <select :id="`mcp-load-${i}`" v-model="item.load" class="vfield"><option v-for="m in LOAD_MODES" :key="m" :value="m">{{ m }}</option></select>
            <VButton label="Remove" variant="quiet" size="small" @click="draft.mcp.splice(i, 1)" />
          </div>
          <div class="configure-add">
            <label class="field-label" for="catalog-server">Catalog server</label>
            <div class="configure-inline">
              <VTextField id="catalog-server" v-model="serverId" autocomplete="off" spellcheck="false" placeholder="atlassian" data-testid="catalog-server" @keydown.enter.prevent="readCatalog" />
              <VButton label="Read the catalog" pending-label="Reading" :pending="catalogBusy" variant="secondary" data-testid="catalog-read" @click="readCatalog" />
            </div>
            <RefusalNotice v-if="catalogRefusal" :refusal="catalogRefusal" compact />
            <div v-if="catalog" class="configure-catalog" data-testid="catalog-entry">
              <p class="configure-fact"><strong>{{ catalog.label }}</strong> ({{ catalog.id }}), revision {{ catalog.revision }}, {{ catalog.transport }}</p>
              <p v-if="catalog.read_only_tools.length" class="configure-fact">Read-only tools it lists: {{ catalog.read_only_tools.join(', ') }}</p>
              <label class="configure-choice" for="catalog-all">
                <input id="catalog-all" v-model="allTools" type="checkbox" class="configure-check" data-testid="catalog-all" />
                <span>All its tools</span>
              </label>
              <template v-if="!allTools">
                <label class="field-label" for="catalog-tools">Tools, separated by commas</label>
                <VTextField id="catalog-tools" v-model="toolList" autocomplete="off" spellcheck="false" data-testid="catalog-tools" />
              </template>
              <label class="field-label" for="catalog-load">Load</label>
              <select id="catalog-load" v-model="serverLoad" class="vfield" data-testid="catalog-load"><option v-for="m in LOAD_MODES" :key="m" :value="m">{{ m }}</option></select>
              <VButton label="Add this server" variant="secondary" size="small" data-testid="catalog-add" @click="addServer" />
            </div>
          </div>
        </fieldset>

        <fieldset class="panel configure-section" data-testid="role-skills">
          <legend class="panel-title">Skills</legend>
          <p v-if="!draft.skills.length" class="configure-none">No skills.</p>
          <div v-for="(item, i) in draft.skills" :key="`skill-${i}`" class="configure-row">
            <label class="field-label" :for="`skill-name-${i}`">Skill</label>
            <VTextField :id="`skill-name-${i}`" v-model="item.skill" autocomplete="off" spellcheck="false" />
            <label class="field-label" :for="`skill-revision-${i}`">Revision</label>
            <VTextField :id="`skill-revision-${i}`" :model-value="String(item.revision)" inputmode="numeric" @change="item.revision = revisionOf(($event.target as HTMLInputElement).value)" />
            <label class="field-label" :for="`skill-load-${i}`">Load</label>
            <select :id="`skill-load-${i}`" v-model="item.load" class="vfield"><option v-for="m in LOAD_MODES" :key="m" :value="m">{{ m }}</option></select>
            <VButton label="Remove" variant="quiet" size="small" @click="draft.skills.splice(i, 1)" />
          </div>
          <VButton label="Add a skill" variant="secondary" size="small" data-testid="add-skill" @click="draft.skills.push({ skill: '', revision: 1, load: 'when assigned' })" />
        </fieldset>

        <fieldset class="panel configure-section" data-testid="role-instructions">
          <legend class="panel-title">Instruction files</legend>
          <p v-if="!draft.instructions.length" class="configure-none">No instruction files.</p>
          <div v-for="(item, i) in draft.instructions" :key="`instruction-${i}`" class="configure-row">
            <label class="field-label" :for="`instruction-source-${i}`">From</label>
            <select :id="`instruction-source-${i}`" v-model="item.source" class="vfield"><option value="project">project</option><option value="factory">factory</option></select>
            <label class="field-label" :for="`instruction-path-${i}`">Path</label>
            <VTextField :id="`instruction-path-${i}`" v-model="item.path" autocomplete="off" spellcheck="false" />
            <label class="field-label" :for="`instruction-load-${i}`">Load</label>
            <select :id="`instruction-load-${i}`" v-model="item.load" class="vfield"><option v-for="m in LOAD_MODES" :key="m" :value="m">{{ m }}</option></select>
            <VButton label="Remove" variant="quiet" size="small" @click="draft.instructions.splice(i, 1)" />
          </div>
          <VButton label="Add an instruction file" variant="secondary" size="small" data-testid="add-instruction" @click="draft.instructions.push({ source: 'project', path: '', load: 'always' })" />
        </fieldset>

        <fieldset class="panel configure-section" data-testid="role-settings">
          <legend class="panel-title">Engine settings</legend>
          <p v-if="!draft.settings.length" class="configure-none">No engine settings.</p>
          <div v-for="(item, i) in draft.settings" :key="`setting-${i}`" class="configure-row">
            <label class="field-label" :for="`setting-key-${i}`">Setting</label>
            <VTextField :id="`setting-key-${i}`" v-model="item.key" autocomplete="off" spellcheck="false" />
            <label class="field-label" :for="`setting-value-${i}`">{{ item.json ? 'Value (JSON)' : 'Value' }}</label>
            <VTextField :id="`setting-value-${i}`" v-model="item.value" autocomplete="off" spellcheck="false" />
            <VButton label="Remove" variant="quiet" size="small" @click="draft.settings.splice(i, 1)" />
          </div>
          <VButton label="Add a setting" variant="secondary" size="small" data-testid="add-setting" @click="draft.settings.push({ key: '', value: '', json: false })" />
        </fieldset>

        <div class="configure-save" data-testid="role-save-bar">
          <p v-if="form.problem.value" class="configure-problem" role="alert">{{ form.problem.value }}</p>
          <RefusalNotice v-if="form.saveRefusal.value" :refusal="form.saveRefusal.value" compact />
          <p v-else-if="form.saved.value" class="configure-outcome" role="status" data-testid="role-saved" :data-revision="form.saved.value.revision">
            Saved. Revision {{ form.saved.value.revision }} of {{ form.saved.value.role }} is stored.
          </p>
          <VButton label="Save as a new revision" pending-label="Saving" :pending="form.saving.value" type="submit" data-testid="role-save" />
        </div>
      </form>
    </StatePanel>
  </section>
</template>
