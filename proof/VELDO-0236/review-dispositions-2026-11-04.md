# Review dispositions, parity cluster, 2026-11-04

Owner request Telegram 39145. Sources: veldo-plan-consistency-review-2026-11-04.md (95 findings) and the lead's
rulings veldo-plan-rulings-2026-11-04.md (R1 to R14). Specs: VELDO-0236 to VELDO-0240 (veldo-parity-a),
VELDO-0232 (veldo-0232, spec and OPEN.md only), VELDO-0234 and VELDO-0235 (veldo-0234-0235) and VELDO-0248
(veldo-0248), the last three by History note only, naming the follow-up ticket. One line per finding handled.

- A7: applied. 0232 AC4 and L6: no role grants Antigravity until its login files are unreadable to the run's tools (R7); OPEN.md item 6.
- A9: applied. 0232 OPEN.md item 8: the tracker code reads Jira credentials from the environment; it leaves the branch for its own ticket with keystore credentials.
- A11: applied. 0237 Context and AC2: assistant_codex sandbox network off; AC3 capture records the image hosts and the Codex qualification record declares them (R5).
- A12: applied. 0232 AC1 declares model hosts and the proxy reading; AC2 fails closed and waits if the proxy settings are ignored (R5, R13); new error name; OPEN.md item 5.
- A15: applied. 0237 AC2: the grant is a line in the installation repository's assistant_codex role file, a widening commit (R1, R8); rollback and depends_on (VELDO-0253) follow.
- A19: applied by History note on 0234: follow-up VELDO-0253 makes the port installation configuration and replaces the holds_https_port refusal.
- A20: applied by History note on 0235: follow-up VELDO-0253 makes destination, remote and trunk project file keys, drops the signed operation, widening and narrowing as the finding says.
- A21: applied. 0238 AC2 inbound cap and 0239 AC1 renumber hook now name the installation repository (VELDO-0253); VELDO-0253 added to both depends_on.
- A24: applied (0240 part). 0240 AC3: a schedule's approval approves no outside write; each write needs approval of its exact request (R4), else approval_required and the owner is told.
- B1: rejected. VELDO-0250 AC1 names an owner role id but defines no value; choosing one here would make the corpus inconsistent, and VELDO-0250 AC2 rewrites every owner field and index row in one pass.
- B2: applied. Message ids and owner quotes removed from Intent and Context of 0232 and 0236 to 0240; History ids stay (VELDO-0250); for 0234, 0235 and 0248 a History note names VELDO-0250, including 0248 AC2's decision reference.
- B7: applied. 0232 account label, the assistant repository script and path, and the account folder path made generic, the recorded run redacted; shipped binary paths listed in OPEN.md item 7 (code not edited).
- B8: applied by History notes on 0234 and 0235 naming VELDO-0250 for the occupied port and app, project name, remote default, fixture owner and README lines.
- B9: applied. Account labels, "from his phone", project names and the owner's parity report removed from 0236 to 0240; 0237 AC1 cites a decision reference and AC3 uses relative paths and the account label.
- B11: applied by History note on 0248 naming VELDO-0250 to regenerate the records and the closure with decision references.
- C15: applied for 0232 (OPEN.md item 8, control plane calls outside the gate per R6); for 0235 and 0239 no change, the landing push carve-out is stated in VELDO-0251, not here.
- C16: applied (paid-API rule) to 0237 Out of scope: paid services are named per installation with the spend gate flag, each use approved with its cost, none in Veldo's defaults (R11).
- C24: applied. 0240 AC3: a message or file a turn sends the owner through Veldo's own channel is not an outside write (R6).
- D7: rejected for 0248. Landing 0248 before 0241 is batch order, not 0248's spec text; no change needed there.
- D9: applied. 0232, 0237 and 0238 amended now for the outside gate (A7, A11, A12; 0238 AC4 row plants a keystore canary instead of a delivered server credential).
- D10: applied. 0232 OPEN.md item 8 asks the lead to take commit 7c8b0360's tracker files off the branch into a mirror-repair ticket.
- D12: applied for 0232 (OPEN.md item 9, renumber at batch assembly); 0234 and 0235 need no spec change for it.
- D13: applied. 0238 Context: its file delivery is Veldo's one delivery to the owner, which VELDO-0242 calls.
- D14: applied (0240 part). 0240 Context: VELDO-0245's steps may be listed but are timed by their workflow and add no kind; 0245's own Context is not owned here.
- E6: applied. Every sentence added for the agent gateway says "the outside gate"; existing "gate" in 0239 and 0240 means the verification gate.
- E8: applied by History note on 0248 naming the sandboxed launch ticket of R14: build the runtime per host outside the sandbox before any confined gate run.
- E12: applied. 0236 AC2 and error taxonomy refuse any ceiling on a window with no observed utilization (invalid_input:ceiling), with a ceiling/no-utilization row.
- E13 (0234 part): rejected. Review F1 was fixed in fix round 1 (commit cf16ef06, suite 127 green), and the gate_unconfined approval at landing is already in 0234's History.
- E13 (0235 part): applied by History note on 0235: the checked-out working tree issue needs its own follow-up ticket, filed and numbered by the lead before landing.
- E14: applied. 0238 Context: files Veldo sends the owner through its own channel need no per-call approval (R6).

Rulings applied without a finding of their own: R1 (0236 and 0240 Context: pauses, ceilings and schedules are runtime state in the store, per VELDO-0253 AC1, the accounts are installation configuration), R4 (0240 AC3), R8 (0237 AC2), R11 (0237), R13 (0232).

Totals: 27 applied, 3 rejected.
