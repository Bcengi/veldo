import { describe, expect, it } from 'vitest'
import { moveStyleAttributes, styleSafePolicy } from './style-attributes'

describe('moveStyleAttributes', () => {
  it('moves each style attribute out of markup so the policy has nothing inline to refuse', () => {
    expect(moveStyleAttributes('<div style="top:19px;height:19px;" class="view-line"><span style="width:4px"></span></div>')).toBe(
      '<div data-veldo-style="top:19px;height:19px;" class="view-line"><span data-veldo-style="width:4px"></span></div>',
    )
  })

  it('leaves text that only mentions style alone', () => {
    expect(moveStyleAttributes('<span>style="x"</span>')).toBe('<span>style="x"</span>')
  })
})

describe('styleSafePolicy', () => {
  it("wraps Monaco's own policy and keeps its other members", () => {
    const policy = styleSafePolicy('editorViewLayer', { createHTML: (v) => v, createScriptURL: (v) => v + '?ok' })
    expect(policy.createHTML!('<i style="a:b"></i>')).toBe('<i data-veldo-style="a:b"></i>')
    expect(policy.createScriptURL!('w.js')).toBe('w.js?ok')
  })
})
