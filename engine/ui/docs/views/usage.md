# Usage

Route `/usage`. Reads `reads.spend` (reservation policies, workers and invocations), live, and pages
`events.read` for the journal time of each invocation's reservation.

A Chart.js bar chart of one unit (invocations, wall seconds, tokens or messages, as the CLI reports them) per
hour, with the invocations whose amount is not known yet drawn apart and never counted as zero; the hours
are also a list of buttons, so a point is selected by touch, click or keyboard, and the selection lists its
invocations. The breakdown is by account, project or run. Each account shows its rate-limit windows
(remaining, reset time), its active runs and whether it is out until a reset; when every account is out,
"No account until" names the earliest reset. No price is ever computed; the provider is not in the spend read.
