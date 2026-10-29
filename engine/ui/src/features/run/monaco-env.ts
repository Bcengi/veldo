import EditorWorker from 'monaco-editor/editor/editor.worker.js?worker'
import { applyMovedStyles, styleSafePolicy } from '@/ui/style-attributes'

/**
 * Monaco's environment, set before any Monaco module evaluates (its modules create their trusted-types
 * policies as they load, so this module is imported first by monaco.ts). Only the base editor worker is
 * used. Monaco's rendered markup carries style attributes, which the API's policy refuses; they are moved
 * into the CSS object model instead (src/ui/style-attributes.ts).
 */
applyMovedStyles()
;(self as unknown as { MonacoEnvironment: unknown }).MonacoEnvironment = {
  getWorker: () => new EditorWorker(),
  createTrustedTypesPolicy: styleSafePolicy,
}
