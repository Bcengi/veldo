# API layer and state

## Layers

```
view (views/*.vue)            orchestrates; reads stores and composables; no fetch
  store / composable          authoritative state and its loading; no DOM
    api module (api/*.ts)      one function per route; typed bodies and answers
      client (api/client.ts)   the only fetch; headers, token, refusal parsing
```

A component below a view receives data by props and reports intent by emits. Only `src/api/` may
call `fetch` or construct an `EventSource`; a unit test scans the source tree for violations.

## The route table

`src/api/routes.ts` lists every route the UI uses by the **name** the API publishes in
`control_api.ROUTES` (for example `decisions.answer`), with method and path. API modules call
`request(routeName, ...)`; there is no free-form URL anywhere. The Python suite of VELDO-0145 reads
both tables and fails when the UI names a route, method or path the API does not publish, which is
how "every request a screen makes is traced to an API route" stays true.

Routes are domain scoped: `/api/v1/domains/{domain}/...`. The domain comes from the session store,
which reads it from the page's own location (`<meta name="veldo-domain">` is not used, since the API
serves one domain); see `api/domain.ts`.

## The client

`request(route, { params, body, signal })`:

- Sends `credentials: 'same-origin'`, `Accept: application/json`; on a POST also
  `Content-Type: application/json` and `X-Veldo-Token` from the session store's in-memory token.
- Serializes GET parameters as the route's exact query fields and POST bodies as the exact fields.
  Never add a field the route does not list: the API refuses unknown fields and any actor field.
- Returns the parsed JSON on 2xx. On any other status it throws `ApiRefusal` with `status`,
  `refusal` (the full name, for example `stale_version:stale_presentation`), `error` (the class) and
  `ownerRequest` when present. A network failure throws `ApiRefusal` with `error: 'unavailable'`.
- On `unauthenticated` from any route except the sign-in ceremony, it tells the session store, which
  ends the local session and routes to sign-in with the refusal shown there.

## Refusals are data

`api/refusals.ts` maps every refusal the screens can meet to a sentence for a person and a fix:

| Class | Example names | Shown as |
|---|---|---|
| `unauthenticated` | `no_session`, `session_expired`, `credential_not_current`, `unknown_credential` | "You are signed out" and the reason; sign-in |
| `unauthorized` | `out_of_scope`, `not_owner`, `origin`, `token` | "Outside your scope" or the specific check |
| `stale_version` | `stale_presentation`, `request_closed`, `already_answered` | What changed and what to do |
| `invalid_input` | `missing_rationale`, `unmatched_choice` | The field to fix |
| `missing_evidence` | `unknown_run` | What is missing |
| `unavailable_service` | `authority`, `openssl` | Try again; nothing was changed |

The refusal name is always shown too (small, as machine text), so the owner can match it to logs.
Unknown names fall back to their class sentence and still show the name. A refusal is rendered by
`RefusalNotice` beside the action it concerns, never as a toast that disappears.

## State

Stores are Pinia setup stores holding authoritative state only:

- `session`: principal, credential id, anti-forgery token, expiries, status (`unknown`,
  `signed-out`, `signed-in`, `ended`) and the refusal that ended it. Never persisted.
- `decisions`: the last `reads.decisions` answer reduced by `features/decisions/inbox.ts` to the
  pending requests and their current presentation, plus each request's answer state.
- `runs`: the last `reads.workers` and `reads.work` answers reduced to the runs list.

Rules:

1. **Never optimistic.** After an answer is sent the decision shows "Sending" until the API answers,
   then the API's outcome. The inbox is re-read; nothing is removed locally first.
2. **Each read keeps its watermark** (`watermark.seq`) and `freshness`; a screen shows when it was
   read and marks anything not `live` as stale.
3. **Race guard.** A store action that loads keeps a sequence number; an answer that arrives after a
   newer request started is dropped.
4. **On sign-out or session end** every store resets (`resetAll()` in `stores/index.ts`), so no data
   from the ended session stays on screen.

## Screen state

`useAsync(load)` returns `{ state, data, refusal, run }` where `state` is `idle`, `loading`, `ready`,
`empty` or `error`. Views render exactly one `StatePanel` branch per state. An `error` keeps the
`ApiRefusal`, so the panel names it. Empty is decided by the caller (`isEmpty(data)`), because an
empty inbox and an empty record mean different things.

## Live streams

`api/record-stream.ts` follows one run's record:

1. Open `EventSource(runs.record_stream?dispatch=...&after=<cursor>)`. Frames arrive as
   `event: record` with `id` equal to the cursor; the browser resends it as `Last-Event-ID` on
   reconnect, and the API resumes after it.
2. Each frame's lines are applied by `applyFrame(state, frame)` (pure, in `features/run/record.ts`):
   a line is appended only when its `seq` is exactly the next one. A line at or below the cursor is
   dropped (a repeat); a jump past the next sequence is a gap, and the follower reads the missing
   lines with `runs.record` from its cursor before applying the frame.
3. `event: closed` carries the reason. `ended` closes the follower for good and marks the run ended;
   `signed_out`, `session_expired` and `revoked` end the session; `slow_reader` and `disconnected`
   reconnect from the cursor.
4. When the browser drops the connection it reconnects by itself; the follower counts reconnects
   and shows "Reconnecting" in the toolbar until the next frame.

The follower never builds a summary: the terminal renders one row per kept line.
