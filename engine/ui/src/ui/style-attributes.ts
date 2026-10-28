/**
 * The API's policy refuses style attributes parsed from markup (style-src-attr falls back to default-src
 * 'self'), but not styles set through the CSS object model. Monaco renders its lines as HTML strings with
 * style attributes, through its trusted-types policy hook. `styleSafePolicy` wraps that hook so each
 * ` style="..."` becomes ` data-veldo-style="..."`, and `applyMovedStyles` moves the value into
 * `element.style.cssText` (the CSS object model) as the markup lands. `setAttribute('style', ...)` is
 * routed the same way. Only declarations move; nothing is evaluated.
 */
export const MOVED = 'data-veldo-style'
const STYLE_ATTRIBUTE = /(<[^>]*?\s)style="([^"]*)"/g

export function moveStyleAttributes(html: string): string {
  return html.replace(STYLE_ATTRIBUTE, (_m, head: string, value: string) => `${head}${MOVED}="${value}"`)
}

function apply(root: ParentNode | Element) {
  if (root instanceof Element && root.hasAttribute(MOVED)) {
    ;(root as HTMLElement).style.cssText = root.getAttribute(MOVED) ?? ''
    root.removeAttribute(MOVED)
  }
  for (const element of Array.from(root.querySelectorAll?.(`[${MOVED}]`) ?? [])) {
    ;(element as HTMLElement).style.cssText = element.getAttribute(MOVED) ?? ''
    element.removeAttribute(MOVED)
  }
}

let observer: MutationObserver | null = null

/** Watch the document for moved style values and apply them through the CSS object model. */
export function applyMovedStyles() {
  if (observer || typeof MutationObserver === 'undefined') return
  observer = new MutationObserver((records) => {
    for (const record of records) {
      if (record.type === 'attributes') apply(record.target as Element)
      for (const node of Array.from(record.addedNodes)) if (node instanceof Element) apply(node)
    }
  })
  observer.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: [MOVED] })
  const setAttribute = Element.prototype.setAttribute
  Element.prototype.setAttribute = function (this: Element, name: string, value: string) {
    if (name.toLowerCase() === 'style' && this instanceof HTMLElement) {
      this.style.cssText = value
      return
    }
    return setAttribute.call(this, name, value)
  }
}

interface PolicyOptions {
  createHTML?: (input: string, ...args: unknown[]) => string
  createScript?: (input: string, ...args: unknown[]) => string
  createScriptURL?: (input: string, ...args: unknown[]) => string
}

/** MonacoEnvironment.createTrustedTypesPolicy: Monaco's own policy, with style attributes moved. */
export function styleSafePolicy(name: string, options: PolicyOptions) {
  const policy: PolicyOptions & { name: string } = { name }
  if (options.createHTML) {
    const create = options.createHTML
    policy.createHTML = (input, ...args) => moveStyleAttributes(create(input, ...args))
  }
  if (options.createScript) policy.createScript = options.createScript
  if (options.createScriptURL) policy.createScriptURL = options.createScriptURL
  return policy
}
