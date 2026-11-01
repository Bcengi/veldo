# Workers

Route `/workers`. Reads `reads.workers` and `reads.spend` (the account records), live, and `reads.contract` once.

The machines the API derives from the recorded dispatches, grouped Linux then Mac, each with its host label
and how many runs it is running, and each worker run as a card: unit (opening its run), state, station,
project, capability (the dispatch contract's adapter, configuration role and revision, servers and tools),
account, process and record. The read's gaps (the machine registry, VELDO-0125) are named above.

Stop asks for an inline confirmation; confirming sends `workers.stop` (`src/api/actions.ts`) with the dispatch
and the version the card shows: the owner's stop request, control_dispatch's command (VELDO-0131), which the
authority records on the dispatch with its state unchanged. The card then shows the stop only as the record holds
it ("Requested by ...; waiting for the runner to ask its receiver", then whether the receiver was asked) and offers
Stop no more. The runner that holds the run's receiver asks it to stop on its next sweep; the run's end is
recorded as every end is. A stop recovers, retries or restarts nothing. A refusal is named beside the card with
its name in `data-refusal`: `stale_version` when the record moved after the screen read it,
`unauthorized:not_authorized:role` or `:scope` for a member who does not own the run's project.

Run caps by account lists every account record of the spend read with its run cap, record version and changes.
Save cap sends `workers.cap` (control_accounts' cap, VELDO-0131) with the account, the version shown and a whole
number from 1 to 16; the result is the API's, beside the control ("Cap saved" with the record's new version, or
"Not saved" with the refusal name: `stale_version`, `unauthorized:missing_authority:scope` for a member whose scope
is not the whole factory). A machine's own cap waits on the machine registry (VELDO-0125), and the screen says so.

A dispatch is linked by its entity id: inside the data the API's secret scanner may redact the dispatch id's
random suffix.
