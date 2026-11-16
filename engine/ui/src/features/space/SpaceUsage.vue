<script setup lang="ts">
import { computed } from 'vue'
import { useDesktop } from '@/composables/useMedia'
import { bytesText, countText, usageRows, type UsageAnswer } from './space'

/** Usage (design 10): bytes and item counts by project, plain repository or no project, then ticket, then kind,
 * with the event each kind's sizes were measured at. A table on a desktop, the same rows as a list on a phone.
 * The figures are the API's sums of the ledger's item records; nothing is added up here. */
const props = defineProps<{ usage: UsageAnswer }>()
const desktop = useDesktop()
const rows = computed(() => usageRows(props.usage))
</script>

<template>
  <section class="panel" aria-labelledby="space-usage-title" data-testid="space-usage">
    <h2 id="space-usage-title" class="panel-title">Usage <span class="panel-count">{{ bytesText(props.usage.total.bytes) }} in {{ countText(props.usage.total) }}</span></h2>
    <div class="factory-body">
      <p v-if="!rows.length" class="space-note" data-testid="space-usage-none">The ledger holds no item that is still there.</p>
      <div v-else-if="desktop" class="factory-table-wrap">
        <table class="factory-table" aria-label="Space used by project, ticket and kind">
          <thead>
            <tr><th scope="col">Project, ticket, kind</th><th scope="col" class="space-num">Size</th><th scope="col" class="space-num">Items</th></tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.key" :class="`space-level-${row.level}`" :data-usage="row.key" :data-level="row.level">
              <td>{{ row.label }}<span class="space-detail">{{ row.detail }}</span></td>
              <td class="space-num" data-testid="usage-bytes" :data-bytes="row.bytes">{{ bytesText(row.bytes) }}</td>
              <td class="space-num" data-testid="usage-items" :data-items="row.items">{{ countText(row) }}</td>
            </tr>
          </tbody>
          <tfoot>
            <tr class="space-total" data-usage="total">
              <th scope="row">Total</th>
              <td class="space-num" data-testid="usage-bytes" :data-bytes="props.usage.total.bytes">{{ bytesText(props.usage.total.bytes) }}</td>
              <td class="space-num" data-testid="usage-items" :data-items="props.usage.total.items">{{ countText(props.usage.total) }}</td>
            </tr>
          </tfoot>
        </table>
      </div>
      <ul v-else class="space-tree" aria-label="Space used by project, ticket and kind">
        <li v-for="row in rows" :key="row.key" class="space-tree-row" :class="`space-level-${row.level}`" :data-usage="row.key" :data-level="row.level">
          <span class="space-tree-label">{{ row.label }}<span class="space-detail">{{ row.detail }}; {{ countText(row) }}</span></span>
          <span class="space-num" data-testid="usage-bytes" :data-bytes="row.bytes" :data-items="row.items">{{ bytesText(row.bytes) }}</span>
        </li>
        <li class="space-tree-row space-level-0" data-usage="total">
          <span class="space-tree-label">Total<span class="space-detail">{{ countText(props.usage.total) }}</span></span>
          <span class="space-num" data-testid="usage-bytes" :data-bytes="props.usage.total.bytes" :data-items="props.usage.total.items">{{ bytesText(props.usage.total.bytes) }}</span>
        </li>
      </ul>
    </div>
  </section>
</template>
