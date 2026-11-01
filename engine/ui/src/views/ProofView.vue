<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { readProof } from '@/api/reads'
import CopyId from '@/components/CopyId.vue'
import ScreenHeader from '@/components/ScreenHeader.vue'
import StatePanel from '@/components/StatePanel.vue'
import VButton from '@/components/VButton.vue'
import { useDesktop } from '@/composables/useMedia'
import { useLiveRead } from '@/composables/useLiveRead'
import { landedUnits } from '@/features/backlog/completion'
import LiveMeta from '@/features/factory/LiveMeta.vue'
import { bundlesOf, findingsOf, observationsOf } from '@/features/proof/proof'
import SourceDiff from '@/features/proof/SourceDiff.vue'
import '@/styles/factory.css'

/** Gate and review results (VELDO-0131): each proof bundle's checks and artifacts, the findings (checks that did
 * not pass, gates that were not green), and the gate output and manifest as read-only Monaco panes, with the
 * changes between any two gate observations. On a phone the checks are cards and the code pane wraps and shows
 * old, new or the changes, one at a time. */
const live = useLiveRead(readProof, (a) => a.watermark, (a) => Object.values(a.items).every((list) => list.length === 0))
const desktop = useDesktop()
const bundles = computed(() => bundlesOf(live.data.value))
const observations = computed(() => observationsOf(live.data.value))
const findings = computed(() => findingsOf(bundles.value, observations.value))
const landed = computed(() => landedUnits(live.data.value))
const oldId = ref<string>('')
const newId = ref<string>('')
watch(observations, (list) => {
  if (!list.find((o) => o.id === newId.value)) newId.value = list[list.length - 1]?.id ?? ''
  if (!list.find((o) => o.id === oldId.value)) oldId.value = list[list.length - 2]?.id ?? list[0]?.id ?? ''
}, { immediate: true })
const older = computed(() => observations.value.find((o) => o.id === oldId.value) ?? null)
const newer = computed(() => observations.value.find((o) => o.id === newId.value) ?? null)
const pane = ref<'changes' | 'old' | 'new'>('changes')
const wrap = ref(true)
const manifestOf = ref<string>('')
const manifest = computed(() => bundles.value.find((b) => b.id === manifestOf.value) ?? null)
const when = (seconds: number | null) => (seconds ? new Date(seconds * 1000).toLocaleString() : 'not recorded')
onMounted(() => void live.start())
</script>

<template>
  <section class="screen screen-wide">
    <ScreenHeader title="Gate and review">
      <template #aside>
        <VButton label="Refresh" variant="quiet" size="small" :pending="live.state.value === 'loading'" pending-label="Refreshing" @click="live.refresh()" />
      </template>
    </ScreenHeader>
    <LiveMeta :live="live.live.value" :seq="live.data.value?.watermark.seq ?? null" :freshness="live.data.value?.freshness ?? null" :read-at="live.readAt.value" />
    <StatePanel
      :state="live.state.value"
      :refusal="live.refusal.value"
      empty-title="No gate or review result yet"
      empty-body="Results appear here once a unit's gate runs and its proof is accepted."
      loading-label="Loading gate and review results"
      @retry="live.refresh()"
    >
      <div class="factory-grid" data-testid="proof">
        <section class="panel" aria-labelledby="findings-title" data-testid="findings">
          <h2 id="findings-title" class="panel-title">Findings <span class="panel-count">{{ findings.length }}</span></h2>
          <ul class="factory-body factory-list">
            <li v-for="finding in findings" :key="finding.id" class="factory-card" :data-finding="finding.id">
              <span class="factory-tag is-stop">Needs a look</span>
              <span class="factory-card-title">{{ finding.title }}</span>
              <span class="factory-meta">{{ finding.detail }}</span>
            </li>
            <li v-if="!findings.length" class="factory-meta">No finding: every check passed and every gate was green.</li>
          </ul>
        </section>

        <section v-for="bundle in bundles" :key="bundle.id" class="panel" :aria-labelledby="`bundle-${bundle.id}`" :data-bundle="bundle.id">
          <h2 :id="`bundle-${bundle.id}`" class="panel-title">
            {{ bundle.unit }}
            <span class="factory-tag" :class="landed.has(bundle.unit) ? 'is-done' : 'is-waiting'">{{ landed.has(bundle.unit) ? 'Landed' : 'Landing not confirmed' }}</span>
          </h2>
          <div class="factory-body">
            <dl class="factory-facts">
              <dt>Specification</dt><dd>{{ bundle.spec }}<template v-if="bundle.revision != null"> revision {{ bundle.revision }}</template></dd>
              <dt>Criteria</dt><dd>{{ bundle.criteria.join(', ') || 'none' }}</dd>
              <dt>Commit</dt><dd><CopyId :value="bundle.commit" label="commit" /></dd>
              <dt>Accepted by</dt><dd>{{ bundle.accepted || 'not recorded' }}</dd>
            </dl>
            <div v-if="desktop" class="factory-table-wrap">
              <table class="factory-table" :aria-label="`Checks of ${bundle.unit}`">
                <thead><tr><th scope="col">Check</th><th scope="col">Status</th><th scope="col">Command</th><th scope="col">Observation</th></tr></thead>
                <tbody>
                  <tr v-for="check in bundle.checks" :key="check.name" :data-check="check.name">
                    <td>{{ check.name }}</td>
                    <td><span class="factory-tag" :class="check.status === 'passed' ? 'is-done' : 'is-stop'">{{ check.status }}</span></td>
                    <td class="factory-mono">{{ check.command }}</td>
                    <td class="factory-mono">{{ check.observation }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <ul v-else class="factory-list" :aria-label="`Checks of ${bundle.unit}`">
              <li v-for="check in bundle.checks" :key="check.name" class="factory-card" :data-check="check.name">
                <span class="factory-card-title">{{ check.name }} <span class="factory-tag" :class="check.status === 'passed' ? 'is-done' : 'is-stop'">{{ check.status }}</span></span>
                <span class="factory-mono">{{ check.command }}</span>
              </li>
            </ul>
            <h3 class="panel-title">Proof</h3>
            <ul class="factory-list" :aria-label="`Proof of ${bundle.unit}`">
              <li v-for="artifact in bundle.artifacts" :key="artifact.path" class="factory-card" :data-artifact="artifact.path">
                <span class="factory-card-title">{{ artifact.criterion }}: {{ artifact.type }}</span>
                <span class="factory-mono">{{ artifact.path }}</span>
              </li>
            </ul>
            <div class="factory-actions">
              <VButton
                :label="manifestOf === bundle.id ? 'Hide the manifest' : 'Show the manifest'"
                variant="secondary"
                size="small"
                :aria-expanded="manifestOf === bundle.id"
                data-testid="manifest-toggle"
                @click="manifestOf = manifestOf === bundle.id ? '' : bundle.id"
              />
            </div>
            <SourceDiff v-if="manifest && manifestOf === bundle.id" :path="manifest.manifestPath" before="" :after="manifest.manifestBody" pane="new" :wrap="wrap" :label="`Manifest ${manifest.manifestPath}`" />
          </div>
        </section>

        <section v-if="observations.length" class="panel" aria-labelledby="gate-output-title" data-testid="gate-output">
          <h2 id="gate-output-title" class="panel-title">Gate output <span class="panel-count">{{ observations.length }}</span></h2>
          <div class="factory-body">
            <div class="factory-grid factory-split-even">
              <div class="factory-search">
                <label for="gate-old" class="field-label">Old</label>
                <select id="gate-old" v-model="oldId" class="factory-select" data-testid="gate-old">
                  <option v-for="o in observations" :key="o.id" :value="o.id">{{ o.commit.slice(0, 7) }} {{ o.green ? 'green' : 'red' }}, {{ when(o.finishedAt) }}</option>
                </select>
              </div>
              <div class="factory-search">
                <label for="gate-new" class="field-label">New</label>
                <select id="gate-new" v-model="newId" class="factory-select" data-testid="gate-new">
                  <option v-for="o in observations" :key="o.id" :value="o.id">{{ o.commit.slice(0, 7) }} {{ o.green ? 'green' : 'red' }}, {{ when(o.finishedAt) }}</option>
                </select>
              </div>
            </div>
            <div class="factory-actions" role="group" aria-label="Pane">
              <VButton label="Changes" size="small" :variant="pane === 'changes' ? 'primary' : 'secondary'" :aria-pressed="pane === 'changes'" data-testid="pane-changes" @click="pane = 'changes'" />
              <VButton label="Old only" size="small" :variant="pane === 'old' ? 'primary' : 'secondary'" :aria-pressed="pane === 'old'" data-testid="pane-old" @click="pane = 'old'" />
              <VButton label="New only" size="small" :variant="pane === 'new' ? 'primary' : 'secondary'" :aria-pressed="pane === 'new'" data-testid="pane-new" @click="pane = 'new'" />
              <VButton :label="wrap ? 'Wrap lines: on' : 'Wrap lines: off'" size="small" variant="secondary" :aria-pressed="wrap" data-testid="wrap" @click="wrap = !wrap" />
            </div>
            <p v-if="older && newer" class="factory-meta">{{ older.command }}: {{ older.terminal || `exit ${older.exit}` }} then {{ newer.terminal || `exit ${newer.exit}` }}</p>
            <SourceDiff
              v-if="older && newer"
              path="gate-output.txt"
              :before="older.output"
              :after="newer.output"
              :pane="pane"
              :wrap="wrap"
              :label="`Gate output, ${pane}`"
            />
          </div>
        </section>
      </div>
    </StatePanel>
  </section>
</template>
