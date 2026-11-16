# Space-management integration: assembly record

Lead's assembly, not a landing. Branch veldo-space-integration, from veldo-space-0304 at 98e08944
(VELDO-0302, 0324, 0333, 0304). STATUS (fix round after the independent review, below): all seven
picks in, lead decisions (a) and (b) applied, the integration defects fixed, the review's five findings
fixed, suites run, and teeth passed. Nothing
was pushed; verify.sh and policy_check.py were not run (lead's instruction).

## Picks (git cherry-pick 8ef46604..TIP, in order)

1. veldo-space-0328 (7cf06b02): clean.
2. veldo-space-0341 (efca30b3): no conflict, with one change to VELDO-0328's code that is declared
   here (the review of the assembly, finding 4). The 0341 fix commit d50ab560 renames 0328's
   Adapter._image(engine, name) (added by 28f89a22: read one image by name, refuse an unread one) to
   _named_image, in control_space_docker.py and its engine copy, and gives the name _image to its own
   new method (engine, shown, relations: judge one image the engine showed, by itself or by a
   protected container made from it). Why: both methods are on the one Adapter, so without the rename
   0341's _image would replace 0328's and its two callers, built and pulled, would call the wrong
   method with the wrong arguments. With it, built and pulled call _named_image and keep 0328's
   checks unchanged, and the image_tag removal probe applies 0341's related protection
   (control_space_probe.py, the image_tag and network branch). The rename changes no behaviour of
   0328.
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

## Resume 1 checks (superseded below)

At bd4b848b: stopped before teeth on the CLI event contract between 0314 and 0323/0335 (0314's CLI
sent released {paths, creator} and session subjects with working_folder; the Ledger takes released
{paths} and session {session, cwd, pid, started}).

## Resume 2: lead decisions and fixes (one commit each)

- fba90748 VELDO-0314, decision (a): the spool's subjects are the Ledger's (session: cwd; released:
  paths alone, the --creator option gone, who released is the emitter's). The CLI sends released to
  the Ledger with its {verb, host} emitter; its session and ref_changed events are refused there by
  0335's emitter rule (kept), so session events reach the Ledger only from the spool through 0323's
  consumer. 153_0314 rows adjusted: the waiting row simulates a Ledger with no event command (0323
  installed it, so the real Ledger no longer makes an entry wait); the wired CLI rows expect the
  Ledger's answers. History line in the spec as dictated.
- 6917c232 VELDO-0324, decision (b): the nine rows now expect 0304's standalone removal with no
  ledger (unique commit kept in main by the keep step, clone removed; an untracked only copy defers
  it; the observation folder stays as evidence, space_deferred:kept). History line in the spec.
- 45c38f49 VELDO-0302: lander.gate uses setdefault('space_items') (KeyError in 113_0220).
- 77027ee5 VELDO-0304: 113_0220 and 114_0220 fixtures stub scripts/check_space_boundary.py, which
  0304 added to verify.sh's CHECK_extra (host-lock/held-not-started, host-scope/own-scope).
- 78285554 VELDO-0304: its proof manifest gains checks, rollback and unit evidence, from its own
  round4-checks.json and teeth-receipt.json only; status stays pending_lead_validation (27_0010 AC1).
- c7fe5048 VELDO-0304: 53_0123's isolated gate stubs check_space_boundary.py (2 coordinator rows).
- 09c1328c VELDO-0337: the fixture lifecycle tables of 132_0297, 133_0326 and 134_0331 list the
  review run kinds (found in this run: the pick-3 decision added them to KINDS, and those suites
  were not in resume 1's list; 31 and 29 rows red, every Ledger refused invalid_input:lifecycle).
- d6e2b3d9 VELDO-0337: suite 153_0337 carries the control_space_kinds.py production-copy anchor the
  re-pointed teeth case needs (finding 337 had executed nothing: anchor moved).

## Resume 2 checks

validate.py all: 0 problems. Not run: verify.sh, policy_check.py.

Suites (selftest --suite, nice 10): 45 suites, the ones the twelve tickets' manifests and tests.json
name (0304: round4-checks.json) plus 135_0298, 113/114_0220, 53_0123, 27_0010, 86_0127; and
132_0297, 133_0326 (fixed above), 134_0331, 153_0337 rerun after their fixes. All green except:
- 151_0313: 18 rows, ac3/event-types PASSES. The red rows are the host-bound ones (cgroup, process
  group and kernel reads; the space admission rows wait 75 on this host's free disk: 25 GB free
  against a 20 GB floor with 4 GB held); known, they fail at the ticket tip on this host too.
- 101_0208: sandbox/unavailable-refuses-before-exec, sandbox/old-abi-refuses-before-exec and
  unconfined-leg/fixture-sharers-are-listed (133_0326 shares with 85_0171); known.
- 86_0127: live/claude, live/codex (stale live captures; recapture before landing); known.

Teeth (python3 scripts/check_teeth_mutations.py --finding N, nice 10, nothing written meanwhile),
all passed with every case rejected: 302 12/12, 304 44/44, 309 20/20, 314 21/21, 323 16/16,
324 20/20, 328 14/14, 333 6/6, 335 13/13, 336 11/11, 337 18/18 (rerun at d6e2b3d9, after the
anchor fix), 341 15/15. 302-336 and 341 ran at 09c1328c; d6e2b3d9 touches only suite 153_0337,
which none of those findings run.

## Fix round after the independent review (verdict FIX, five findings; one commit each)

Review: review-veldo-space-integration.md, at 9b5ca496.

- 5d419069 VELDO-0335, finding 1, decision (a) finished (design 6.9: the CLI event verb is for
  released). The verb takes released alone: session_started, session_ended and ref_changed are refused
  by name (space_event_hook_only:<type>) before anything is spooled or sent, with a ledger and with
  none; its session and ref branches are removed. The Ledger refuses the emitter hook "event" for every
  kind but released, so the spool route cannot bypass 0335's rule. The client hooks and the git hooks
  spool directly as before. This supersedes the line of fba90748 above that the Ledger refuses the
  CLI's session and ref events: the verb now refuses them itself. Rows: 154_0335
  safety/spool-emitter-released-only (new), 151_0313 ac3/event-types, 153_0314 ac4/cli-spools,
  fix5/cli-session-path-said, round2/cli-invalid-refused and round2/cli-unsafe-folder (the last two
  now plant a release), 153_0323 compatibility/cli-envelope-refused. Teeth registry: new
  space335-spool-emitter-any-kind; space314-cli-hook-type-taken replaces
  space314-cli-folder-unresolved and space314-cli-session-path-silent, whose code is gone; the
  anchors of space314-cli-raw-paths, space314-cli-unresolved and space335-cli-forges-hook follow the
  code. proof/VELDO-0314/falsifiers.json still names the two replaced cases: that bundle is not
  edited here. Suite registry sentence and 0335 History line updated.
- 0063dff3 VELDO-0337, finding 2: row safety/review-scratch-in-use (a review_run_scratch whose
  borrowed login is not settled under the borrow root is deferred at verdict_recorded, rule in_use,
  and removed by the same event once settled) and teeth case space337-review-scratch-in-use-skipped;
  suite 153_0337 names control_space_signal.py among its production copies.
- c2de998d VELDO-0337, finding 3: row ac1/build-root-passes-between-kinds (a review run after a
  build run on the same worktree, and a build run after a review run, are given the same build root)
  and teeth cases space337-build-root-own-kind-only and space337-build-root-plain-kind-only.
- 8cffa5be VELDO-0341, finding 4: pick 2 above declares the rename of 0328's Adapter._image.
- 042705db VELDO-0337, finding 5: design VELDO-0295 amended (a review's scratch and build root end on
  verdict_recorded, ticket_ended and project_ended; twelve kinds), with a dated note.

Checks at 8cffa5be. Not run: verify.sh, policy_check.py. validate.py all exit 0, check_generated.sh
and check_docs.sh pass (run during the round).

Suites (selftest --suite, nice 10), green: 153_0314 54/0, 153_0323 66/0, 154_0335 58/0, 153_0337
47/0, 153_0302 68/0, 153_0309 50/0, 153_0328 43/0, 153_0333 39/0, 153_0336 47/0, 153_0341 47/0,
154_0324 55/0, 148_0311 57/0, 132_0297 57/0, 149_0312 67/0. Red, known rows only: 151_0313 42/12
(the host-bound rows, a subset of the 18 above; ac3/event-types PASSES), 86_0127 52/2 (live/claude,
live/codex).

Teeth (check_teeth_mutations.py --finding N, nice 10, run last, nothing written meanwhile), all
passed with every case rejected: 314 20/20, 335 14/14, 337 21/21. The other nine findings were not
rerun: of their modules this round changed only control_space.py's emitter check and bin/veldo's
event verb.

## Open

- Landing still needs the lead's gate (verify.sh), policy_check, independent review and the 0304
  proof bundle's lead validation; 86_0127 live captures are to be recaptured.
