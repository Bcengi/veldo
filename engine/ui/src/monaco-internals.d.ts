/** The two Monaco internals src/ui/monaco-stylesheets.ts uses, typed as it uses them. */
declare module 'monaco-editor/base/common/lifecycle.js' {
  export interface IDisposable {
    dispose(): void
  }
  export class DisposableStore implements IDisposable {
    add<T extends IDisposable>(value: T): T
    dispose(): void
  }
  export function toDisposable(fn: () => void): IDisposable
}
declare module 'monaco-editor/base/common/observableInternal/reactions/autorun.js' {
  export function autorun(fn: (reader: unknown) => void): import('monaco-editor/base/common/lifecycle.js').IDisposable
}
