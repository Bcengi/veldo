<script setup lang="ts">
import { computed } from 'vue'
import EditDiff from './EditDiff.vue'
import { clock, type ShownLine } from './record'

/** One kept line of the record: its sequence, receive time and stream, then how it reads. Never merged with
 * another line; in raw view the payload is shown exactly as the record holds it. */
const props = defineProps<{ line: ShownLine; raw: boolean; match: boolean; current: boolean }>()
const time = computed(() => clock(props.line.at))
const pretty = (value: unknown) => (typeof value === 'string' ? value : JSON.stringify(value, null, 2))
</script>

<template>
  <li
    class="tline"
    :class="{ 'is-error': props.line.error, 'is-match': props.match, 'is-current-match': props.current, [`stream-${props.line.stream}`]: true }"
    :data-seq="props.line.seq"
    :data-stream="props.line.stream"
    :data-error="props.line.error ? 'true' : undefined"
    :aria-label="`Line ${props.line.seq}`"
  >
    <div class="tline-gutter" aria-hidden="false">
      <span class="tline-seq">{{ props.line.seq }}</span>
      <time class="tline-time" :datetime="new Date(props.line.at * 1000).toISOString()">{{ time }}</time>
    </div>
    <div class="tline-body">
      <p class="tline-head">
        <span class="tline-kind">{{ props.line.error ? `Error, ${props.line.kind}` : props.line.kind }}</span>
        <span v-if="props.line.stream !== 'engine' && props.line.kind !== props.line.stream" class="tline-stream">{{ props.line.stream }}</span>
        <span v-for="kind in props.line.redacted" :key="kind" class="tline-redacted">Redacted {{ kind }}</span>
      </p>
      <pre v-if="props.raw" class="tline-raw" data-testid="payload">{{ props.line.payload }}</pre>
      <template v-else>
        <template v-for="(block, i) in props.line.blocks" :key="i">
          <p v-if="block.type === 'text'" class="tb-text">{{ block.text }}</p>
          <details v-else-if="block.type === 'thinking'" class="tb-thinking"><summary>Thinking</summary><p>{{ block.text }}</p></details>
          <div v-else-if="block.type === 'tool_call'" class="tb-call">
            <p class="tb-call-head"><span class="tb-tool">{{ block.name }}</span><code class="tb-summary">{{ block.summary }}</code></p>
            <details class="tb-input"><summary>Input</summary><pre>{{ pretty(block.input) }}</pre></details>
          </div>
          <div v-else-if="block.type === 'edit'" class="tb-edit">
            <p class="tb-call-head"><span class="tb-tool">{{ block.name }}</span><code class="tb-summary">{{ block.path }}</code></p>
            <EditDiff v-for="(hunk, h) in block.hunks" :key="h" :path="block.path" :before="hunk.before" :after="hunk.after" />
          </div>
          <div v-else-if="block.type === 'tool_result'" class="tb-result" :class="{ 'is-error': block.isError }">
            <p class="tb-result-head">{{ block.isError ? 'Tool error' : 'Output' }}</p>
            <pre class="tb-output">{{ block.output }}</pre>
          </div>
          <div v-else-if="block.type === 'command'" class="tb-result" :class="{ 'is-error': block.exitCode !== null && block.exitCode !== 0 }">
            <p class="tb-call-head"><span class="tb-tool">Command</span><code class="tb-summary">{{ block.command }}</code></p>
            <pre class="tb-output">{{ block.output }}</pre>
            <p v-if="block.exitCode !== null" class="tb-exit">Exit code {{ block.exitCode }}</p>
          </div>
          <ul v-else-if="block.type === 'file_change'" class="tb-files"><li v-for="p in block.paths" :key="p"><code>{{ p }}</code></li></ul>
          <p v-else-if="block.type === 'system'" class="tb-system"><strong>{{ block.title }}</strong> {{ block.detail }}</p>
          <div v-else-if="block.type === 'result'" class="tb-final" :class="{ 'is-error': block.isError }">
            <p class="tb-result-head">{{ block.isError ? 'Run ended with an error' : 'Run finished' }} ({{ block.title }})</p>
            <p class="tb-text">{{ block.text }}</p>
          </div>
          <p v-else-if="block.type === 'delta'" class="tb-delta">{{ block.text }}</p>
          <p v-else-if="block.type === 'error'" class="tb-error">{{ block.text }}</p>
          <pre v-else-if="block.type === 'raw'" class="tb-rawtext">{{ block.text }}</pre>
          <div v-else class="tb-event"><p class="tb-result-head">{{ block.title }}</p><pre class="tb-output">{{ block.text }}</pre></div>
        </template>
      </template>
    </div>
  </li>
</template>
