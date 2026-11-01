<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import VButton from '@/components/VButton.vue'

/** A full-width sheet over a phone screen (a dialog): it takes focus when it opens, closes with Escape or its
 * Close button, and gives focus back to what opened it. */
const props = defineProps<{ title: string; id: string }>()
const emit = defineEmits<{ close: [] }>()
const root = ref<HTMLElement | null>(null)
const opener = document.activeElement as HTMLElement | null
function onKey(event: KeyboardEvent) {
  if (event.key === 'Escape') emit('close')
}
onMounted(async () => {
  document.addEventListener('keydown', onKey)
  await nextTick()
  root.value?.querySelector<HTMLElement>('h2')?.focus()
})
onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKey)
  opener?.focus?.()
})
</script>

<template>
  <div ref="root" class="factory-sheet" role="dialog" aria-modal="true" :aria-labelledby="`${props.id}-title`" :data-testid="props.id">
    <div class="factory-sheet-head">
      <h2 :id="`${props.id}-title`" class="panel-title" tabindex="-1">{{ props.title }}</h2>
      <VButton label="Close" variant="secondary" size="small" @click="emit('close')" />
    </div>
    <slot />
  </div>
</template>
