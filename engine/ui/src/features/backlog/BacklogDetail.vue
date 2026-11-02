<script setup lang="ts">
import type { BacklogEntry } from './backlog'
import { COMPLETION_WORDS } from './completion'

/** One backlog item's facts, its open and resolved blockers, and its units with their completion. */
const props = defineProps<{ entry: BacklogEntry }>()
</script>

<template>
  <div class="factory-grid">
    <dl class="factory-facts">
      <dt>Project</dt><dd>{{ props.entry.project }}</dd>
      <dt>Objective</dt><dd class="factory-mono">{{ props.entry.objective }}</dd>
      <dt>State</dt><dd>{{ props.entry.state }}</dd>
      <dt>Priority</dt><dd>{{ props.entry.rank == null ? 'No rank' : `Rank ${props.entry.rank}` }}</dd>
      <dt>Version</dt><dd>{{ props.entry.version }}</dd>
    </dl>
    <h3 class="panel-title">Blockers</h3>
    <ul v-if="props.entry.blockers.length" class="factory-list">
      <li v-for="b in props.entry.blockers" :key="b.id" class="factory-card" data-testid="blocker">
        <span class="factory-tag" :class="b.resolved ? 'is-done' : 'is-stop'">{{ b.resolved ? 'Resolved' : 'Open' }}</span>
        <span>{{ b.reason }}</span>
        <span class="factory-meta">{{ b.phase }} by {{ b.by }}</span>
      </li>
    </ul>
    <p v-else class="factory-meta">No blocker</p>
    <h3 class="panel-title">Units</h3>
    <ul v-if="props.entry.units.length" class="factory-list">
      <li v-for="u in props.entry.units" :key="u.id" class="factory-card" :data-unit="u.id" :data-completion="u.completion">
        <span class="factory-card-title">{{ u.id }}</span>
        <span class="factory-meta">{{ u.state }}<template v-if="u.specification">, {{ u.specification }}</template></span>
        <span v-if="COMPLETION_WORDS[u.completion]" class="factory-tag" :class="u.completion === 'landed' ? 'is-done' : 'is-waiting'">{{ COMPLETION_WORDS[u.completion] }}</span>
      </li>
    </ul>
    <p v-else class="factory-meta">No unit taken yet</p>
  </div>
</template>
