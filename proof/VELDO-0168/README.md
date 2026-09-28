# VELDO-0168 proof

The suite `86_veldo_0168_text` reports 26 rows, once each, through the signed inbox, framing,
presentation, report and intake writers, a loopback Bot API stand-in and a signed SQLite authority.
Only generated fixtures and loopback networking are used. The renderer probes start from real writer
snapshots. Unsupported choice text is supplied at renderer and waiting-reader seams; the refusal and
hint rows still record and deliver through the production writers. The compose row substitutes a
corrupted copy of a real receipt at its reader, then calls production compose.

| Criterion | Rows and what they establish |
| --- | --- |
| AC1 | `lines/decision`, `lines/inbox`, `lines/report`, `lines/prompt`, `lines/edges`: line breaks and spaces survive the real send renderers, including Telegram's trimmed message ends. `replies/refused`, `replies/hint`, `intake/delivery`: refusal and hint sends render choices, request ids and merged question text once. `inventory/sends-and-assets`: every engine Python module's send and private send call is counted against explicit lists, and the Presenter send callers' text producers are traced. |
| AC2 | `escape/zero-width`, `escape/direction`, `escape/whitespace`, `escape/literal`, `escape/categories`, `escape/fields`: distinct values remain distinct across the four renderers. `escape/markers`: a typed cut marker escapes its opener. `escape/field-crlf`: scope, choice and subject CRs remain visible while free text normalizes CRLF. |
| AC3 | `cuts/long-token`, `cuts/words`: hard cuts carry both markers within the limit, soft cuts preserve spaces. `cuts/escape-boundary`: 600 zero-width characters remain 600 whole escapes across delivered parts. |
| AC4 | `receipts/earlier`, `receipts/new`, `receipts/unknown`: old and new versions recheck their own bytes with distinct unknown-version errors. `receipts/compose-recheck`: an otherwise current receipt failing recheck is refused during compose, with the correct reason. `receipts/version-type`: bool and float versions are refused. |

`observability/counters` checks renderer versions, escaped categories, hard cuts and part numbers on
real observations and metrics. The inventory also found the service's delegation renewal notice;
its text now uses the renderer. This required the documented two-file footprint addition.

## Renderer 1 fixtures

`renderer-1-receipt.json` and `renderer-1-parts-receipt.json` were recorded by the earlier renderer from
an unchanged archive of ad91698948dd1d894c0f6af4702b8a4b93c9694e. Neither names a renderer version.
The earlier-receipt row requires both to recheck under renderer 1 while current rendering differs.

## Red record

The current proof driver run against ad916989 makes all 26 rows red by assertion, with no setup or
section exception (`red-at-ad916989.json`). Against b0dca892, the merge commit immediately before
these fixes, seven rows are red by assertion (`red-at-b0dca892.json`): the inventory, refusal reply,
hint, escape boundary, literal markers, field CRLF and version type. The compose behavior already
worked at that baseline; its new row is green there and red at the original baseline.

## Mutations and checks

`mutations.json` lists 44 finding 168 mutations, their exact diffs, source digests and named rows.
It explicitly records that the revised mutations were not run: the owner reserves that execution,
including the older companion mutations, for the reviewer. The old 32-mutation run is preserved as
`mutations-before-review.json`; it is historical evidence, not a result for the revised code.
Every mutation name from both merge parents is retained. The anchor check reports zero bad anchors
and no duplicate names. Both new send mutants target the inventory: one adds an edge send outside
the original four modules, the other adds a raw Presenter private send caller. Additional mutations
cover both missed renderers, the renewal sender, merged intake text, escape boundaries, typed markers, both field CRLF
renderers, both compose refusal reasons and renderer version types.

The own suite passes normally and under the gate's clean environment: 26 specification rows and
26 shared preamble assertions, zero failures in each run. The scoped runner intentionally exits 2 on success, reserving exit 0 for
a full verification. `review-checks.json` records the checks.
Requires were regenerated unchanged after the merge. The footprint check reports nothing outside;
validation passes; engine and repository copies are byte-identical. These are scoped checks, not a
gate or landing claim. The full suite and mutation runners were not run in this job.

Splitting inbox items, reports and intake prompts exceeding 4096 after escaping remains the explicit
History follow-up, outside this job.
