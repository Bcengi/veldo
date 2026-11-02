import * as monaco from 'monaco-editor/editor/editor.api.js'
import 'monaco-codicons.css'
import 'monaco-editor/languages/definitions/typescript/register.js'
import 'monaco-editor/languages/definitions/javascript/register.js'
import 'monaco-editor/languages/definitions/python/register.js'
import 'monaco-editor/languages/definitions/markdown/register.js'
import 'monaco-editor/languages/definitions/yaml/register.js'
import 'monaco-editor/languages/definitions/shell/register.js'
import 'monaco-editor/languages/definitions/css/register.js'
import 'monaco-editor/languages/definitions/html/register.js'

/** Monaco for read-only diffs: loaded only when an edit is on screen, with only the base editor worker
 * (diffs are computed there) and the tokenizers of the languages a factory mostly edits. */

function token(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

/** Monaco themes that read Veldo's tokens, so a diff matches the page in either theme. */
export function defineThemes() {
  for (const dark of [false, true]) {
    const root = document.documentElement
    const was = root.getAttribute('data-theme')
    root.setAttribute('data-theme', dark ? 'dark' : 'light')
    monaco.editor.defineTheme(dark ? 'veldo-dark' : 'veldo-light', {
      base: dark ? 'vs-dark' : 'vs',
      inherit: true,
      rules: [],
      colors: {
        'editor.background': token('--paper-sunken'),
        'editor.foreground': token('--ink'),
        'editorLineNumber.foreground': token('--ink-muted'),
        'editorGutter.background': token('--paper-sunken'),
        'diffEditor.insertedTextBackground': token('--diff-insert') + '99',
        'diffEditor.removedTextBackground': token('--diff-remove') + '99',
        'diffEditor.insertedLineBackground': token('--diff-insert') + '55',
        'diffEditor.removedLineBackground': token('--diff-remove') + '55',
        'editor.lineHighlightBackground': '#00000000',
        'scrollbarSlider.background': token('--rule') + 'aa',
      },
    })
    if (was) root.setAttribute('data-theme', was)
  }
}

const LANGUAGES: Record<string, string> = {
  ts: 'typescript', tsx: 'typescript', js: 'javascript', mjs: 'javascript', jsx: 'javascript', py: 'python',
  md: 'markdown', yaml: 'yaml', yml: 'yaml', sh: 'shell', bash: 'shell', css: 'css', html: 'html', vue: 'html',
}

export function languageOf(path: string): string {
  const ext = path.split('.').pop()?.toLowerCase() ?? ''
  return LANGUAGES[ext] ?? 'plaintext'
}

export { monaco }
