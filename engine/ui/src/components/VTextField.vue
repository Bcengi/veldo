<script setup lang="ts">
import { ref } from 'vue'

/** A one-line text field: a native input bound with v-model. Every other attribute (id, type, placeholder,
 * maxlength, data-testid) goes to the input itself; its label is the caller's `<label for>`. */
defineOptions({ inheritAttrs: false })
const model = defineModel<string>({ default: '' })
const input = ref<HTMLInputElement | null>(null)
defineExpose({ focus: () => input.value?.focus() })
</script>

<template>
  <input ref="input" v-model="model" class="vfield" v-bind="$attrs" />
</template>
