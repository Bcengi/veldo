# VELDO-0294 implementation trace

The build follows revision 4 of docs/design/VELDO-0294-design.md. The spec's
acceptance criteria and footprint remain unchanged.

Runtime.build owns phase order and the dispatch budget. Runtime._run owns the
clone until its finally block calls Runner.wait. Capped clone reads and object
imports must finish inside that try block. The floor still reads the newest
build dispatch and its bound artifact.

Receiver._reap meters each output chunk before choosing a stop cause. The first
cause stays latched while output drains. Ledger limits take precedence when a
chunk reaches both limits. Engine meters count steps independently of the
ledger's message count. Codex usage comes only from completed turns.

Metering.settle classifies the outcome before choosing final usage. Only
phase_cap with outcome cancelled uses observed usage and a settlement mark.
Reservations.report validates that mark and stores it without changing admission
or the existing settlement rule. Reports without a mark retain their old shape.
Run token files use the committed invocation charge after a sequence read-back.
The reporter reads journal records, so a missing token file cannot silence it.

The spec's cancelled dispatch wording maps to an exited dispatch whose bound
engine artifact names phase_cap. Cancelled is the ledger outcome. State notes
need tree mode and blob size checks before the authority reads their bytes;
P.blob alone cannot distinguish a symlink. Refusal details retain the design's
existing code names. Suite selectors in this tree require their full names.

Apply the review's Final check (760b300d) correction in the refusal fixtures:
keep usage below the allowance until phase_cap is latched. Exhaust the cap or
window with valid usage during a deterministic termination drain. Assert the
phase_cap artifact and settled marked invocation before attempting continuation.
For Codex, complete the open turn during the drain, include both completed turns
in the expected charge, and open another turn if asserting in_flight equal to 1.
Do not weaken usage_cap precedence.

After each production edit, sync the matching .veldo copy before any baseline
or mutant. Run the old ledger rows after the ledger edit and again after the
receiver edit. New baselines precede mutation evidence. Qualification precedes
live captures, which bind the final receiver and engine bytes.
