<script setup lang="ts">
/** A text area that grows with what is typed (CSS `field-sizing: content`, no script), bound with v-model.
 * Every other attribute goes to the textarea; its label is the caller's `<label for>`. */
defineOptions({ inheritAttrs: false })
const model = defineModel<string>({ default: '' })
</script>

<template>
  <textarea v-model="model" class="vfield vfield-area" v-bind="$attrs" />
</template>
