<script setup lang="ts">
import { computed, onMounted, ref, shallowRef } from 'vue'
import { readEvents, type JournalEvent } from '@/api/events'
import { readSpend } from '@/api/reads'
import ScreenHeader from '@/components/ScreenHeader.vue'
import StatePanel from '@/components/StatePanel.vue'
import VButton from '@/components/VButton.vue'
import { useDesktop } from '@/composables/useMedia'
import { useLiveRead } from '@/composables/useLiveRead'
import { useNow } from '@/composables/useNow'
import LiveMeta from '@/features/factory/LiveMeta.vue'
import UsageChart from '@/features/usage/UsageChart.vue'
import { accountsOf, amount, breakdown, invocationsOf, noAccountUntil, seriesOf, timesOf, UNITS, type BreakdownKey, type UsageUnit } from '@/features/usage/usage'
import '@/styles/factory.css'

/** Subscription usage over time (VELDO-0131): the spend read's invocations in the units the CLI reports
 * (invocations, wall seconds, tokens, messages), bucketed by the journal time each was committed, with the
 * breakdown by provider, account, project and run, each account's rate-limit windows, reset times and active runs, and
 * "no account until" the earliest reset when every account is out. Unknown usage is shown as unknown, never as
 * zero, and no price is ever computed. */
const events = shallowRef<JournalEvent[]>([])
const live = useLiveRead(
  async (signal) => {
    const spend = await readSpend(signal)
    const all: JournalEvent[] = []
    let after = 0
    for (let page = 0; page < 200; page += 1) {
      const answer = await readEvents(after, signal)
      all.push(...answer.events)
      const next = answer.cursor ?? answer.events[answer.events.length - 1]?.seq ?? after
      if (next <= after || next >= answer.watermark.seq) break
      after = next
    }
    events.value = all
    return spend
  },
  (spend) => spend.watermark,
  (spend) => (spend.items.subscription_reservation ?? []).length === 0,
)
const desktop = useDesktop()
const now = useNow(30_000)
const unit = ref<UsageUnit>('tokens')
const by = ref<BreakdownKey>('account')
const BY_WORDS: Record<BreakdownKey, string> = { provider: 'Provider', account: 'Account', project: 'Project', dispatch: 'Run' }
const selected = ref<number | null>(null)
const invocations = computed(() => invocationsOf(live.data.value))
const series = computed(() => seriesOf(invocations.value, timesOf(events.value), unit.value))
const accounts = computed(() => accountsOf(live.data.value, now.value / 1000))
const until = computed(() => noAccountUntil(accounts.value))
const rows = computed(() => breakdown(invocations.value, unit.value, by.value))
const picked = computed(() => series.value.buckets.find((b) => b.start === selected.value) ?? null)
const range = computed(() => {
  const b = series.value.buckets
  if (!b.length) return 'No timed usage yet'
  return `${when(b[0]!.start)} to ${when(b[b.length - 1]!.start + 3600)}`
})
const when = (seconds: number) => new Date(seconds * 1000).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', timeZoneName: 'short' })
const words = (u: string) => u.replace('_', ' ')
onMounted(() => void live.start())
</script>

<template>
  <section class="screen screen-wide">
    <ScreenHeader title="Usage">
      <template #aside>
        <VButton label="Refresh" variant="secondary" size="small" :pending="live.state.value === 'loading'" pending-label="Refreshing" @click="live.refresh()" />
      </template>
    </ScreenHeader>
    <LiveMeta :live="live.live.value" :seq="live.data.value?.watermark.seq ?? null" :freshness="live.data.value?.freshness ?? null" :read-at="live.readAt.value" />
    <StatePanel
      :state="live.state.value"
      :refusal="live.refusal.value"
      empty-title="No usage recorded yet"
      empty-body="Usage appears here once a worker's calls are reserved against an account."
      loading-label="Loading usage"
      @retry="live.refresh()"
    >
      <div class="factory-grid" data-testid="usage">
        <p v-if="until" class="factory-gap" role="status" data-testid="no-account-until">No account until {{ when(until) }}: every account's window has run out.</p>
        <section class="panel" aria-labelledby="usage-time-title">
          <h2 id="usage-time-title" class="panel-title">Over time</h2>
          <div class="factory-body">
            <div class="factory-grid factory-split-even">
              <div class="factory-search">
                <label for="usage-unit" class="field-label">Unit</label>
                <select id="usage-unit" v-model="unit" class="factory-select" data-testid="usage-unit">
                  <option v-for="u in UNITS" :key="u" :value="u">{{ words(u) }}</option>
                </select>
              </div>
              <p class="factory-meta" data-testid="usage-range">{{ range }}<template v-if="series.untimed">; {{ series.untimed }} invocation{{ series.untimed === 1 ? '' : 's' }} with no journal time</template></p>
            </div>
            <UsageChart :buckets="series.buckets" :unit="unit" :selected="selected" :label="`Usage in ${words(unit)} per hour, ${range}`" @select="selected = $event" />
            <ol class="factory-list" aria-label="Hours">
              <li v-for="b in series.buckets" :key="b.start">
                <button type="button" class="factory-card factory-card-button" :aria-pressed="selected === b.start" :data-bucket="b.start" data-testid="usage-bucket" @click="selected = b.start">
                  <span class="factory-card-title">{{ when(b.start) }}</span>
                  <span>{{ amount(b.known, b.unknown, unit) }}</span>
                </button>
              </li>
            </ol>
            <div v-if="picked" class="factory-card" role="status" data-testid="usage-selected">
              <span class="factory-card-title">{{ when(picked.start) }}: {{ amount(picked.known, picked.unknown, unit) }}</span>
              <span v-for="inv in picked.invocations" :key="inv.id" class="factory-meta">{{ inv.account }}, {{ inv.project }}, {{ inv.dispatch }}: {{ inv.unknown.includes(unit) || inv.charge[unit] == null ? 'unknown' : `${inv.charge[unit]} ${words(unit)}` }}</span>
            </div>
          </div>
        </section>
        <div class="factory-grid factory-split-even">
          <section class="panel" aria-labelledby="usage-accounts-title" data-testid="usage-accounts">
            <h2 id="usage-accounts-title" class="panel-title">Accounts <span class="panel-count">{{ accounts.length }}</span></h2>
            <ul class="factory-body factory-list">
              <li v-for="a in accounts" :key="a.account" class="factory-card" :data-account="a.account">
                <span class="factory-card-title">{{ a.account }}
                  <span class="factory-tag" :class="a.blockedUntil ? 'is-stop' : 'is-done'">{{ a.blockedUntil ? `Out until ${when(a.blockedUntil)}` : 'Available' }}</span>
                </span>
                <dl class="factory-facts">
                  <dt>Provider</dt><dd data-testid="account-provider">{{ a.provider || 'no account record' }}</dd>
                  <dt>Label</dt><dd>{{ a.label || 'no account record' }}</dd>
                  <dt>Status</dt><dd>{{ a.status || 'no account record' }}</dd>
                  <dt>Active runs</dt><dd>{{ a.activeRuns.length ? a.activeRuns.join(', ') : 'none' }}</dd>
                  <dt>{{ words(unit) }}</dt><dd>{{ amount(a.totals[unit] ?? 0, a.unknown[unit] ?? 0, unit) }}</dd>
                </dl>
                <ul class="factory-list" :aria-label="`Rate-limit windows of ${a.account}`">
                  <li v-for="w in a.windows" :key="w.id" class="factory-meta" :data-window="w.id">
                    Window {{ w.id }}: {{ w.remaining == null ? 'remaining unknown' : `${w.remaining} ${w.unit} left` }}, resets {{ w.resetAt ? when(w.resetAt) : 'at an unknown time' }}
                  </li>
                  <li v-if="!a.windows.length" class="factory-meta">No window observed yet: exposure unknown</li>
                </ul>
              </li>
            </ul>
          </section>
          <section class="panel" aria-labelledby="usage-breakdown-title" data-testid="usage-breakdown">
            <h2 id="usage-breakdown-title" class="panel-title">Breakdown</h2>
            <div class="factory-body">
              <div class="factory-search">
                <label for="usage-by" class="field-label">By</label>
                <select id="usage-by" v-model="by" class="factory-select" data-testid="usage-by">
                  <option value="provider">Provider</option>
                  <option value="account">Account</option>
                  <option value="project">Project</option>
                  <option value="dispatch">Run</option>
                </select>
              </div>
              <div v-if="desktop" class="factory-table-wrap">
                <table class="factory-table" aria-label="Usage breakdown">
                  <thead><tr><th scope="col">{{ BY_WORDS[by] }}</th><th scope="col">Invocations</th><th scope="col">{{ words(unit) }}</th></tr></thead>
                  <tbody>
                    <tr v-for="row in rows" :key="row.key" :data-key="row.key"><td class="factory-mono">{{ row.key }}</td><td>{{ row.count }}</td><td>{{ amount(row.known, row.unknown, unit) }}</td></tr>
                  </tbody>
                </table>
              </div>
              <ul v-else class="factory-list" aria-label="Usage breakdown">
                <li v-for="row in rows" :key="row.key" class="factory-card" :data-key="row.key">
                  <span class="factory-mono">{{ row.key }}</span>
                  <span>{{ row.count }} invocations, {{ amount(row.known, row.unknown, unit) }}</span>
                </li>
              </ul>
            </div>
          </section>
        </div>
      </div>
    </StatePanel>
  </section>
</template>
