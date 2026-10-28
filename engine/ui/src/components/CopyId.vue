<script setup lang="ts">
import { ref } from 'vue'
import Icon from './Icon.vue'

/** An identifier a person copies (a dispatch id, a digest): set in mono, broken anywhere, with a copy
 * button that says when it copied. Only the clipboard is written; nothing is sent anywhere. */
const props = defineProps<{ value: string; label: string; testid?: string }>()
const copied = ref(false)
let timer: ReturnType<typeof setTimeout> | undefined

async function copy() {
  try {
    await navigator.clipboard.writeText(props.value)
    copied.value = true
    clearTimeout(timer)
    timer = setTimeout(() => (copied.value = false), 2000)
  } catch {
    copied.value = false
  }
}
</script>

<template>
  <span class="copyid">
    <code class="copyid-value break" :data-testid="props.testid">{{ props.value }}</code>
    <button type="button" class="copyid-button" :aria-label="copied ? `${props.label} copied` : `Copy ${props.label}`" @click="copy">
      <Icon :name="copied ? 'check' : 'copy'" :size="16" />
      <span>{{ copied ? 'Copied' : 'Copy' }}</span>
    </button>
  </span>
</template>
