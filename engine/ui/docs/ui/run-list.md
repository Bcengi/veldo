# RunList

Worker runs as rows: the run's lamp, its unit, its project, host (mono) and station, the station strip
in miniature (`LineLamps`) and the state as a Nuxt UI `UBadge` with its word (green running, amber
starting or blocked, red failed or refused, neutral done). A row is a link to the run. Used by the runs screen and the
overview.

## Props

`runs`: `RunRow[]` (`features/run/runs.ts`).

## States and words

`runSignal(dispatchState, unitState)` in `features/run/lamps.ts`: a unit off the line wins (Failed and
Canceled in red, Blocked in amber), else the dispatch: Running (green), Starting (amber), Done
(a filled grey lamp), Refused (red). The same words as the andon board.
