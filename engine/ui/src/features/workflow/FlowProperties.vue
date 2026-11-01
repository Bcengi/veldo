<script setup lang="ts">
import { computed } from 'vue'
import VButton from '@/components/VButton.vue'
import { KINDS, connect, nodeIds, setConfig, setEntry, transitionOf, type Draft } from './workflow-doc'

/** The property sheet of the selected step or transition (VELDO-0131): every setting a step has, each a labeled
 * native control, always shown (never on hover) so the keyboard and touch reach it as the pointer does. */
const props = defineProps<{ draft: Draft; selected: { kind: 'node' | 'edge'; id: string }; roles: string[] }>()
const emit = defineEmits<{ change: [next: Draft, words: string]; remove: [] }>()
const node = computed(() => (props.selected.kind === 'node' ? props.draft.definition.nodes[props.selected.id] ?? null : null))
const edge = computed(() => (props.selected.kind === 'edge' ? props.draft.definition.transitions.find((t) => t.id === props.selected.id) ?? null : null))
const ports = computed(() => (node.value ? KINDS[node.value.kind]?.ports ?? [] : []))
const others = computed(() => nodeIds(props.draft))
const value = (event: Event) => (event.target as HTMLSelectElement).value
</script>

<template>
  <div class="flow-props" data-testid="flow-properties">
    <template v-if="node">
      <dl class="factory-facts">
        <dt>Step</dt><dd class="factory-mono">{{ props.selected.id }}</dd>
        <dt>Kind</dt><dd>{{ KINDS[node.kind]?.label ?? node.kind }}</dd>
      </dl>
      <div class="flow-props" data-testid="node-settings">
        <div v-if="node.kind === 'assignment'" class="factory-search">
          <label :for="`role-${props.selected.id}`" class="field-label">Capability configuration (role)</label>
          <select :id="`role-${props.selected.id}`" class="factory-select" :value="String(node.config.role ?? '')" data-testid="node-role" @change="emit('change', setConfig(props.draft, props.selected.id, 'role', value($event)), `Role of ${props.selected.id} set.`)">
            <option value="">Not set</option>
            <option v-for="role in props.roles" :key="role" :value="role">{{ role }}</option>
          </select>
        </div>
        <div v-for="port in ports" :key="port" class="factory-search">
          <label :for="`port-${props.selected.id}-${port}`" class="field-label">When {{ port }}, go to</label>
          <select :id="`port-${props.selected.id}-${port}`" class="factory-select" :value="transitionOf(props.draft, props.selected.id, port)?.to ?? ''" :data-testid="`node-port-${port}`" @change="emit('change', connect(props.draft, props.selected.id, port, value($event)), `${props.selected.id} ${port} connected to ${value($event) || 'nothing'}.`)">
            <option value="">Not connected</option>
            <option v-for="id in others" :key="id" :value="id">{{ id }}</option>
          </select>
        </div>
        <p v-if="!ports.length" class="factory-meta">A result handling step ends the workflow; it has no outgoing transition.</p>
        <div class="factory-actions">
          <VButton
            :label="props.draft.definition.entry === props.selected.id ? 'This is the entry step' : 'Make this the entry step'"
            variant="secondary"
            size="small"
            :disabled="props.draft.definition.entry === props.selected.id"
            data-testid="node-entry"
            @click="emit('change', setEntry(props.draft, props.selected.id), `${props.selected.id} is the entry step.`)"
          />
          <VButton label="Delete step" variant="danger" size="small" data-testid="node-delete" @click="emit('remove')" />
        </div>
      </div>
    </template>
    <template v-else-if="edge">
      <dl class="factory-facts">
        <dt>Transition</dt><dd class="factory-mono">{{ edge.id }}</dd>
        <dt>From</dt><dd>{{ edge.from }}, port {{ edge.port }}</dd>
      </dl>
      <div class="factory-search">
        <label :for="`edge-to-${edge.id}`" class="field-label">Goes to</label>
        <select :id="`edge-to-${edge.id}`" class="factory-select" :value="edge.to" data-testid="edge-to" @change="emit('change', connect(props.draft, edge.from, edge.port, value($event)), `Transition ${edge.id} goes to ${value($event)}.`)">
          <option v-for="id in others" :key="id" :value="id">{{ id }}</option>
        </select>
      </div>
      <VButton label="Delete transition" variant="danger" size="small" data-testid="edge-delete" @click="emit('remove')" />
    </template>
    <p v-else class="factory-meta">The selection is no longer in the workflow.</p>
  </div>
</template>
