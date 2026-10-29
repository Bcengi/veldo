import { DisposableStore, toDisposable } from 'monaco-editor/base/common/lifecycle.js'
import 'monaco-editor/base/common/observableInternal/index.js'
import { autorun } from 'monaco-editor/base/common/observableInternal/reactions/autorun.js'
import { AdoptedSheet } from './sheets'

/**
 * Monaco's base/browser/domStylesheets with the same exports, writing every sheet through the CSS object
 * model (sheets.ts) instead of a <style> element, which the API's policy refuses. Monaco keeps its theme
 * and decoration rules in these sheets; the editor's own CSS file is a built asset of this origin.
 */
type Disposables = { add<T extends { dispose(): void }>(value: T): T }

export function createStyleSheet(
  _container?: unknown,
  beforeAppend?: (style: AdoptedSheet) => void,
  disposableStore?: Disposables,
): AdoptedSheet {
  const style = new AdoptedSheet()
  beforeAppend?.(style)
  disposableStore?.add(toDisposable(() => style.remove()))
  return style
}

let shared: AdoptedSheet | null = null

function sharedSheet(): AdoptedSheet {
  if (!shared) shared = createStyleSheet()
  return shared
}

export function createCSSRule(selector: string, cssText: string, style: AdoptedSheet = sharedSheet()) {
  if (!style || !cssText) return
  try {
    style.sheet.insertRule(`${selector} {${cssText}}`, 0)
  } catch {
    /* an unparseable rule is skipped */
  }
}

export function removeCSSRulesContainingSelector(ruleName: string, style: AdoptedSheet = sharedSheet()) {
  if (!style) return
  const rules = style.sheet.cssRules
  for (let i = rules.length - 1; i >= 0; i -= 1) {
    const rule = rules[i] as CSSStyleRule
    if (typeof rule.selectorText === 'string' && rule.selectorText.includes(ruleName)) style.sheet.deleteRule(i)
  }
}

export function createStyleSheetFromObservable(css: { read(reader: unknown): string }) {
  const store = new DisposableStore()
  const style = createStyleSheet()
  store.add(toDisposable(() => style.remove()))
  store.add(autorun((reader: unknown) => {
    style.textContent = css.read(reader)
  }))
  return store
}
