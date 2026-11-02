# Gate and review

Route `/proof`. Reads `reads.proof` (proof bundles, gate observations, completion receipts), live.

Findings first (checks that did not pass and gates that were not green). Then each proof bundle: its unit
with Landed or Landing not confirmed, specification, criteria, commit and acceptance; its checks as a table on
a desktop and cards on a phone; its proof artifacts; and its manifest in a read-only Monaco pane.

Gate output: pick an old and a new gate observation; the read-only Monaco pane (`SourceDiff`) shows the
changes (side by side on a desktop, inline on a phone), the old or the new output alone, with line wrapping
switched on or off. Monaco only shows text; nothing is run.
