<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useTheme } from '@/composables/useTheme'
import { useDesktop } from '@/composables/useMedia'

/** Gate and review source in Monaco (VELDO-0131), read-only: the changes between two texts (side by side on a
 * desktop, inline on a phone), or one side alone, with line wrapping the owner switches. Monaco never runs what
 * it shows. The texts are in the DOM as text until Monaco is ready and as the alternative for assistive
 * technology. Pane: 'changes', 'old' or 'new'. */
const props = defineProps<{ path: string; before: string; after: string; pane: 'changes' | 'old' | 'new'; wrap: boolean; label: string }>()
const host = ref<HTMLElement | null>(null)
const ready = ref(false)
const failed = ref(false)
const height = ref(240)
const { theme } = useTheme()
const desktop = useDesktop()
let dispose: (() => void) | null = null

async function mount() {
  dispose?.()
  dispose = null
  ready.value = false
  await nextTick()
  if (!host.value) return
  try {
    await import('@/features/run/monaco-env')
    const { monaco, defineThemes, languageOf } = await import('@/features/run/monaco')
    defineThemes()
    const language = languageOf(props.path)
    const common = {
      readOnly: true,
      domReadOnly: true,
      automaticLayout: true,
      scrollBeyondLastLine: false,
      minimap: { enabled: false },
      lineNumbersMinChars: 3,
      fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
      fontSize: 13,
      wordWrap: props.wrap ? ('on' as const) : ('off' as const),
      glyphMargin: false,
      folding: false,
      theme: theme.value === 'dark' ? 'veldo-dark' : 'veldo-light',
      scrollbar: { alwaysConsumeMouseWheel: false, horizontalScrollbarSize: 8 },
      ariaLabel: props.label,
    }
    const models: { dispose(): void }[] = []
    let editor: { dispose(): void }
    if (props.pane === 'changes') {
      const original = monaco.editor.createModel(props.before, language)
      const modified = monaco.editor.createModel(props.after, language)
      models.push(original, modified)
      const diff = monaco.editor.createDiffEditor(host.value, {
        ...common, originalEditable: false, renderSideBySide: desktop.value, useInlineViewWhenSpaceIsLimited: false,
        renderOverviewRuler: false, diffWordWrap: props.wrap ? 'on' : 'off',
      })
      diff.setModel({ original, modified })
      editor = diff
    } else {
      const model = monaco.editor.createModel(props.pane === 'old' ? props.before : props.after, language)
      models.push(model)
      editor = monaco.editor.create(host.value, { ...common, model })
    }
    const stopTheme = watch(theme, (t) => monaco.editor.setTheme(t === 'dark' ? 'veldo-dark' : 'veldo-light'))
    dispose = () => {
      stopTheme()
      editor.dispose()
      for (const m of models) m.dispose()
    }
    ready.value = true
  } catch {
    failed.value = true
  }
}

watch(() => [props.pane, props.wrap, props.before, props.after, desktop.value], () => void mount())
onMounted(() => {
  height.value = Math.min(Math.max((Math.max(props.before.split('\n').length, props.after.split('\n').length) + 2) * 19, 120), 420)
  void mount()
})
onBeforeUnmount(() => dispose?.())
</script>

<template>
  <div class="diff" :data-ready="ready ? 'true' : 'false'" :data-pane="props.pane" :data-wrap="props.wrap ? 'on' : 'off'" data-testid="source-diff">
    <div ref="host" class="diff-editor" :style="{ height: `${height}px` }" :aria-hidden="ready ? undefined : 'true'" />
    <div class="diff-text" :class="{ 'is-hidden': ready && !failed }">
      <pre v-if="props.pane !== 'new'" class="diff-before"><span class="sr-only">Old: </span>{{ props.before }}</pre>
      <pre v-if="props.pane !== 'old'" class="diff-after"><span class="sr-only">New: </span>{{ props.after }}</pre>
    </div>
  </div>
</template>
