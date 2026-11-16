# Space-management integration: assembly record

Lead's assembly, not a landing. Branch veldo-space-integration, from veldo-space-0304 at 98e08944
(VELDO-0302, 0324, 0333, 0304). STATUS: STOPPED before the teeth runs, on a genuine contradiction
between accepted tickets (below). Nothing was pushed; verify.sh and policy_check.py were not run.

## Picks (git cherry-pick 8ef46604..TIP, in order)

1. veldo-space-0328 (7cf06b02): clean.
2. veldo-space-0341 (efca30b3): clean.
3. veldo-space-0337 (42995a87): control_space.py pair, declare `ends` vs 0302's `form`. Lead
   decision applied: declare takes no end list; new kinds review_run_scratch and
   review_run_build_output in the kind registry (end on verdict_recorded, ticket_ended,
   project_ended; folder remover; scratch lock rule) and in the Ledger's DISK_KINDS;
   control_launch.space_kind picks them for a review run. 0337 rows ac1/declared-at-creation,
   ac1/adopt-refuses-ends and teeth cases space337-review-kinds-end-at-run-finished,
   space337-adopt-accepts-ends now prove it through the kind; 0298's suite carries the two rows.
   Design note and 0337 History line added.
4. veldo-space-0314 (771c4768): manifest.json, requires.json: both sides kept.
5. veldo-space-0336 (565b3b68): teeth registry, manifest, requires: both sides kept.
6. veldo-space-0309 (9d49c708): teeth registry, manifest, requires: both sides kept; verify.sh: the
   0309 trap with 0304's CHECK_extra line. verify.sh pair, gate_space.py pair and policy.yaml equal
   0309's tip except that one 0304 line.
7. veldo-space-0335b (ce795280): control_space.py COMMAND_PARAMETERS (0323's EVENT and 0302's form);
   control_service.py shutdown (0323's space listener close and owned-list line, 0304's
   close_socket and socket identity); bin/veldo space_event (0314's spool path and arguments with
   0335's --force refusal and released emitter); registries: both sides kept.

Registries were rewritten with json indent 1 (the generator form); check_generated.sh passes.

## Assembly fixes (commit 75f78d5f)

- init_scaffold.py pair installs control_space_docker.py: the probe loads it since 0341, and 0323's
  row compatibility/installed-closure checks the list.
- Suite 155 (0304): its shutdown fixture names 0323's space_listener.

## Checks

validate.py all: 3 problems, all in proof/VELDO-0304/manifest.json (checks, rollback, unit
evidence); the same at 98e08944. check_docs.sh: pass. check_template_sync.sh: pass.

Suites (selftest --suite, nice 10), 42 suites from the proof manifests (0304: its round4 suite
logs) plus 135_veldo_0298: green except:
- 153_0314 (3 rows), 153_0323 compatibility/cli-envelope-refused, 154_0335 (18 rows),
  151_0313 ac3/event-types: CONTRADICTION, below.
- Red at base 98e08944 as well (not from this assembly): 154_0324 (9 rows; 0304's Batch.discard
  with no ledger removes the clone, 0324 keeps it and defers not_in_ledger), 113_0220 (KeyError
  space_items in lander.gate, 0302; and host-lock/held-not-started), 114_0220_gate_scope
  host-scope/own-scope, 53_0123 (2 coordinator rows), 27_0010 AC1 (the 0304 manifest),
  151_0313 (18 rows).
- Red at the ticket tip as well: 86_0127 live/claude, live/codex (stale live captures);
  101_0208 (2 sandbox rows, fixture-sharers 133/85).

Teeth: not run (stopped).

## The contradiction (needs a ticket decision)

0314 bin/veldo space_event sends the Ledger the spool's subject form: released
{paths, creator} (control_space_spool FIELDS 'released': ('paths', 'creator')), session events
{session, working_folder, pid, started}, with the emitter {verb: event}. 0323/0335 Ledger._t_event
requires released subject exactly {paths}, session subject {session, cwd, pid, started}, and
(0335 fix round 2) refuses the CLI emitter for session_ended and ref_changed. Result: the CLI's
released and session events are refused invalid_input:subject / invalid_input:emitter.
