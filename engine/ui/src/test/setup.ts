// jsdom has no ResizeObserver; components that size themselves (the auto-growing text area, the
// decision's pinned answer bar) get a quiet one.
class QuietResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
if (typeof globalThis.ResizeObserver === 'undefined') globalThis.ResizeObserver = QuietResizeObserver as unknown as typeof ResizeObserver
