import { describe, expect, it } from 'vitest'
import { NEXT_PATTERN, safeNext } from './index'

describe('the next address after sign-in', () => {
  it('keeps a path of this origin and refuses anything a browser reads as another origin', () => {
    expect(NEXT_PATTERN.source).toBe('^\\/(?![/\\\\])')
    expect(safeNext('/decisions/assignment:r:de1')).toBe('/decisions/assignment:r:de1')
    expect(safeNext('/')).toBe('/')
    for (const foreign of ['//evil.example/x', '/\\evil.example', 'https://evil.example', 'runs', '', undefined, ['/runs']])
      expect(safeNext(foreign)).toBe('/')
  })
})
