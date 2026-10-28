<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useTheme } from '@/composables/useTheme'
import { useDesktop } from '@/composables/useMedia'

/** One edit as a read-only Monaco diff. Monaco loads only once an edit scrolls into view; until then, and
 * as the text alternative for assistive technology, the old and new text are in the DOM as text. */
const props = defineProps<{ path: string; before: string; after: string }>()
const root = ref<HTMLElement | null>(null)
const host = ref<HTMLElement | null>(null)
const mounting = ref(false)
const ready = ref(false)
const failed = ref(false)
const { theme } = useTheme()
const desktop = useDesktop()
let dispose: (() => void) | null = null
let observer: IntersectionObserver | null = null

const lines = props.before.split('\n').length + props.after.split('\n').length
const height = ref(Math.min(Math.max(lines * 19 + 16, 72), 480))

async function mount() {
  if (dispose || mounting.value) return
  mounting.value = true
  await nextTick()
  if (!host.value) return
  try {
    // The environment first, in its own chunk: Monaco's modules read it as they evaluate.
    await import('./monaco-env')
    const { monaco, defineThemes, languageOf } = await import('./monaco')
    defineThemes()
    const language = languageOf(props.path)
    const original = monaco.editor.createModel(props.before, language)
    const modified = monaco.editor.createModel(props.after, language)
    const editor = monaco.editor.createDiffEditor(host.value, {
      readOnly: true,
      originalEditable: false,
      domReadOnly: true,
      automaticLayout: true,
      renderSideBySide: desktop.value,
      useInlineViewWhenSpaceIsLimited: true,
      renderOverviewRuler: false,
      scrollBeyondLastLine: false,
      minimap: { enabled: false },
      lineNumbersMinChars: 3,
      fontFamily: 'Atkinson Hyperlegible Mono Variable, ui-monospace, monospace',
      fontSize: 13,
      wordWrap: 'on',
      diffWordWrap: 'on',
      theme: theme.value === 'dark' ? 'veldo-dark' : 'veldo-light',
      scrollbar: { alwaysConsumeMouseWheel: false },
      ariaLabel: `Changes to ${props.path}`,
    })
    editor.setModel({ original, modified })
    // Size the box to the diff as Monaco lays it out (inline diffs are taller than either side).
    const fit = () => {
      const content = Math.max(editor.getOriginalEditor().getContentHeight(), editor.getModifiedEditor().getContentHeight())
      height.value = Math.min(Math.max(content + 8, 72), 480)
    }
    editor.onDidUpdateDiff(fit)
    editor.getModifiedEditor().onDidContentSizeChange(fit)
    const stopTheme = watch(theme, (t) => monaco.editor.setTheme(t === 'dark' ? 'veldo-dark' : 'veldo-light'))
    const stopSide = watch(desktop, (d) => editor.updateOptions({ renderSideBySide: d }))
    dispose = () => {
      stopTheme()
      stopSide()
      editor.dispose()
      original.dispose()
      modified.dispose()
    }
    ready.value = true
  } catch {
    failed.value = true
  }
}

onMounted(() => {
  if (typeof IntersectionObserver === 'undefined') return
  observer = new IntersectionObserver((entries) => {
    if (entries.some((e) => e.isIntersecting)) {
      observer?.disconnect()
      void mount()
    }
  }, { rootMargin: '200px' })
  if (root.value) observer.observe(root.value)
})
onBeforeUnmount(() => {
  observer?.disconnect()
  dispose?.()
})
</script>

<template>
  <div ref="root" class="diff" :data-ready="ready ? 'true' : 'false'">
    <div v-if="mounting && !failed" ref="host" class="diff-editor" :style="{ height: `${height}px` }" :aria-hidden="ready ? undefined : 'true'" />
    <div class="diff-text" :class="{ 'is-hidden': ready && !failed }" data-testid="diff-text">
      <pre v-if="props.before" class="diff-before"><span class="sr-only">Removed: </span>{{ props.before }}</pre>
      <pre class="diff-after"><span class="sr-only">Added: </span>{{ props.after }}</pre>
    </div>
  </div>
</template>
