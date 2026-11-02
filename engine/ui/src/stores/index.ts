import { useDecisionsStore } from './decisions'
import { useRunsStore } from './runs'
import { useSessionStore } from './session'

/** When a session ends, every store drops what it held, so nothing from it stays on screen. */
export function wireSessionEnd() {
  const session = useSessionStore()
  const decisions = useDecisionsStore()
  const runs = useRunsStore()
  session.onEnd(() => {
    decisions.reset()
    runs.reset()
  })
}
