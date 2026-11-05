# Usage

Route `/usage`. Reads `reads.spend` (reservation policies, workers, invocations and the account records) and
`accounts.pacing` (each account's windows, its pause and ceilings in force, and their history), together and live, and
pages `events.read` for the journal time of each invocation's reservation. A refusal of either read is the screen's
error state, with its name.

A Chart.js bar chart of one unit (invocations, wall seconds, tokens or messages, as the CLI reports them) per
hour, with the invocations whose amount is not known yet drawn apart and never counted as zero; the hours
are also a list of buttons, so a point is selected by touch, click or keyboard, and the selection lists its
invocations. The breakdown is by provider, account, project or run. Each account shows its provider, label and
status from its account record (VELDO-0062), its rate-limit windows
(remaining, reset time), its active runs and whether it is out until a reset; when every account is out,
"No account until" names the earliest reset. No price is ever computed.

## Pacing

The Pacing panel (`src/features/usage/AccountPacing.vue`, VELDO-0236) lists each account with its windows (utilization
in percent or "utilization not reported", and the reset time), a "Paused until" tag naming the window whose reset ends
the pause, and a tag for each ceiling in force with its percent and its end. Per window, "Pause until <window>
resets" sends `accounts.pause` with the account and the window; it is enabled only for a window with a known future
reset. The ceiling field takes a percent (`50`) or a step above the window's utilization (`+10`); Set ceiling sends
`accounts.ceiling` with the account, the window and the value, and is enabled only for a window with reported
utilization and a known future reset. Resume now, shown while a pause or a ceiling is in force, sends
`accounts.resume`. Each action is shown done only with the API's answer, beside the control; a refusal is named
beside the control it concerns (for example `invalid_input:ceiling` for a value that is neither form). After an
answer the screen re-reads. Pauses and ceilings end by themselves at the reset, and each end is in the history.

History lists every pause, ceiling, resume and end from the journal, in journal order; with none it says "No pause or
ceiling recorded yet", and with no account record the panel says "No account is registered yet".

## States

Loading, empty (no reservation recorded: "No usage recorded yet"), error (the named refusal of either read, with
Retry) and populated, at 360, 390, 1280 and 1440 pixels in light and dark; the browser checks render each
(`e2e/factory.spec.ts`, the `usage` screen).
