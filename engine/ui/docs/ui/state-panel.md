# StatePanel

One region's loading, empty, error and ready states; exactly one renders, marked `data-state`.

## Props

| Prop | Type | Default |
|---|---|---|
| `state` | `idle` `loading` `ready` `empty` `error` | required |
| `refusal` | `ApiRefusal` or null | null |
| `emptyTitle`, `emptyBody` | string | generic text; always pass your own |
| `loadingLabel` | string | `Loading` (the status region's name) |
| `rows` | number | 4 skeleton rows |
| `shape` | `rows` `lines` `board` `block` | `rows` |

The loading state is shaped like what is coming: `rows` (a lamp, two text bars and a strip, like a run or
inbox row), `lines` (a gutter and a line, like the record), `board` (the andon board's cells), `block`.

## Emits and slots

`retry`: the person pressed Try again. Try again is offered only when trying again can succeed
(`isRetryable`: the API or the network did not answer); a named refusal such as `out_of_scope` or
`unknown_run` answers the same every time, so it gets none.

Slots: `default` (ready), `empty` (an action for the empty state), `error-actions` (inside the refusal).

## Example

```vue
<StatePanel :state="runs.state" :refusal="runs.refusal" empty-title="No worker has run yet"
  empty-body="Runs appear here as soon as the factory dispatches a unit to a worker." @retry="runs.refresh()">
  <RunList :runs="runs.rows" />
</StatePanel>
```

## Rules

- Empty text says what will make something appear, or what to do; it never just says "No data".
- The error state shows no stale data: the store dropped it when the read failed.
