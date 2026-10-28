/**
 * Style sheets made through the CSS object model instead of <style> elements. The API's content security
 * policy has no style-src, so a <style> element a library writes at run time is refused (and reported);
 * a constructed sheet adopted by the document is not governed by that policy and carries only CSS text.
 * PrimeVue's useStyle and Monaco's domStylesheets are both routed here at build time (vite.config.ts).
 */

/** One constructed sheet in the shape a library expects of a <style> element: text, sheet and remove. */
export class AdoptedSheet {
  readonly sheet: CSSStyleSheet
  media = ''
  type = 'text/css'
  private text = ''
  private adopted = false

  constructor() {
    this.sheet = new CSSStyleSheet()
    this.attach()
  }

  get textContent(): string {
    return this.text
  }

  set textContent(value: string | null) {
    this.text = value ?? ''
    try {
      this.sheet.replaceSync(this.text)
    } catch {
      /* a rule the browser cannot parse is skipped, as in a style element */
    }
  }

  get isConnected(): boolean {
    return this.adopted
  }

  attach() {
    if (this.adopted || typeof document === 'undefined') return
    document.adoptedStyleSheets = [...document.adoptedStyleSheets, this.sheet]
    this.adopted = true
  }

  remove() {
    if (!this.adopted) return
    document.adoptedStyleSheets = document.adoptedStyleSheets.filter((s) => s !== this.sheet)
    this.adopted = false
  }

  setAttribute() {}
  getAttribute() {
    return null
  }
}
