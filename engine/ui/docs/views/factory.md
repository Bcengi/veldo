# Factory screens: live reads

VELDO-0131. Every factory screen reads one published read model through `src/api/reads.ts` and keeps it current
with `useLiveRead` (`src/composables/useLiveRead.ts`):

1. Read the model (for example `reads.work`); the answer carries its journal watermark and freshness.
2. Open `events.stream` from that watermark (`src/api/events.ts`). Each frame names committed journal records
   (ids and kinds, never data); a frame with records re-reads the model. Nothing is applied from a frame.
3. A stream closed as `signed_out`, `session_expired` or `revoked` ends the session; any other close (or a
   dropped connection) re-reads and follows again from the new watermark.

`LiveMeta` (`src/features/factory/LiveMeta.vue`) shows, beside the data: Live / Reconnecting / Stopped, the
journal sequence the read was taken at, the freshness the API named (`live`, or stale), and when it was read.

## Actions the API does not carry yet

`reads.contract` publishes the UI action contract (`control_api_models.ACTIONS`). An action whose route is null
(for example `owner_priority`, owned by VELDO-0078, or `worker_stop`, owned by VELDO-0041) is offered as a control
whose result names that gap (`src/features/contract/gaps.ts`); nothing is sent. Once the API publishes the
route, the screen sends it.

## Shared pieces

| Piece | Where | What |
|---|---|---|
| `TreeTable` | `src/features/table/TreeTable.vue` | TanStack Table (`@tanstack/vue-table`) hierarchy: a native table on a desktop, cards on a phone, an expand button per parent row, optional drag and drop of top-level rows (never the only way to move one) |
| `FactorySheet` | `src/features/factory/FactorySheet.vue` | A phone's full-width dialog: takes focus, closes on Escape or Close, gives focus back |
| `LiveMeta` | `src/features/factory/LiveMeta.vue` | The read's source and freshness |
| `factory.css` | `src/styles/factory.css` | Layout of the factory screens, tokens only; every control is a 44 px target on a phone |
