<script setup lang="ts">
/** One radio of a group: a native radio input (keyboard, form and screen reader behavior are the browser's)
 * drawn as Veldo's ring. Wrap it in the `<label>` that names it. */
const props = defineProps<{ value: string; name: string; inputId: string }>()
const model = defineModel<string | null>({ default: null })
</script>

<template>
  <span class="vradio">
    <input :id="props.inputId" v-model="model" type="radio" class="vradio-input" :name="props.name" :value="props.value" />
    <span class="vradio-box" aria-hidden="true"><span class="vradio-dot" /></span>
  </span>
</template>
