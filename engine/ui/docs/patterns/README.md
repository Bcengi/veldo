# Patterns

Solutions that recur. If something is done the same way in two places, it is written down here and,
where it can be, extracted into a composable or a pure module.

| Pattern | Summary | Page |
|---|---|---|
| API layer and state | `client.ts` is the only caller of fetch; routes mirror the API's table; refusals are typed; stores hold authoritative state only | [api-layer.md](api-layer.md) |
| Live streams | EventSource on a record route, resumed by cursor, deduplicated by sequence, closed on a named reason | [api-layer.md#live-streams](api-layer.md#live-streams) |
| Async screen state | `useAsync` gives every screen loading, empty, error and ready states with the refusal kept | [api-layer.md#screen-state](api-layer.md#screen-state) |
| Testing | What each layer's tests must prove, the e2e harness, falsifiers | [testing.md](testing.md) |
| Interactivity | Pending actions, focus, follow mode, keyboard shortcuts | [interactivity.md](interactivity.md) |
| Accessibility | Names, targets, contrast, live regions, reduced motion | [accessibility.md](accessibility.md) |
| Dependencies | How a package is admitted: registry version, license, origin, tier | [dependencies.md](dependencies.md) |
| Routing and navigation | The navigation registry later screens extend | [../views/shell.md](../views/shell.md) |
