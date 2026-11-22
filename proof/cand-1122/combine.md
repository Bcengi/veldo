# Landing candidate cand-1122: the combine record

Base: main 23318512. Each ready branch was brought on with `git cherry-pick` of its own commits
(`git log <base>..<branch>`), in dependency order. Conflicts were resolved keeping both intents.
Not brought (the lead adds them later): VELDO-0147. Round 3 (sections 1.11 to 1.13, 2b) added VELDO-0253,
the VELDO-0111 completion and VELDO-0114; round 4 (sections 1.14 to 1.18, 2c) the VELDO-0111 fix,
VELDO-0113, VELDO-0258, VELDO-0358 wave 1 and VELDO-0359.
`scripts/verify.sh` was not run (the lead queues the gate). Suite and falsifier results: section 3.

## 1. Tickets, commits, conflicts

### 1.1 Bring-up line (line-bringup-1120, 0b767d26..64199803, 43 commits)

Fourteen side-branch tickets (0111 bring-up census, 0117, 0124, 0175, 0176, 0177, 0178, 0179, 0180,
0181, 0183, 0184, 0187, 0231), their fix rounds 1 and 2, and the 0231 live captures. The line's
0111 commits are the census as brought onto the line (from agent/codex/veldo-0111 at 2a7bfcec,
reviewed with the line); the separate veldo-0111-complete branch is not brought.

Conflicts:
- `proof/VELDO-0127/codex-live.json` (fcad71cb) and `proof/VELDO-0127/claude-live.json` (64199803):
  main's VELDO-0127 recapture after gate 12 (f5055400) against the line's 0231 recapture. Each
  capture binds the digests of five production modules; the line's digests are the candidate's
  modules byte for byte (sha256 checked for .veldo/ and engine/.veldo/), main's are not. Taken: the
  line's captures. Main's README section on the gate 12 recapture stays as history.

Added at combine (122d95b5): `proof/VELDO-0231/README.md` no longer describes the old rules. AC1 is
the same-cycle ordering criterion (no 2 s bound, no 5 s after-last-flag window); AC3's probe judges
"immediate" by the event `answered_in: next_request` (no `within_seconds: 5`, no
`IMMEDIATE_SECONDS`), the blocking row is stepped by events (no 15 s deadline), the flood runs on a
frozen service clock; a closing section points to the bring-up evidence and live captures.

### 1.2 VELDO-0316 (0b767d26..8fc4fe86, 8 commits)

Conflicts in the first commit (26484574):
- `.veldo/control_launch.py` and its engine copy, `Runner` dispatch: the line's VELDO-0180 input
  artifacts (`run_inputs`) before the reservation, against 0316 moving the reservation inside the
  `try` that releases the space hold. Kept both: the 0180 block now stands first inside that `try`,
  so a refusal there releases the space hold 0316 prepared; then 0316's reservation. No mutation
  anchor names these lines.
- `scripts/suites/manifest.json`, `requires.json`: both sides appended entries; kept all.

### 1.3 VELDO-0334 (restacked onto 0316 final 8fc4fe86)

The given range 870c43ea..67e858ad leaves out 0334's first three commits (0616b6a2 the
implementation, 794024c5, 870c43ea), which sit on 1f325393. The ticket's own commits are
1f325393..67e858ad (6), all brought. Applied without conflict onto the fixed 0316.

### 1.4 VELDO-0317 (9bbf44d4..b9f2df5a, 15 commits, restacked)

Conflict in 560d46e2, `control_launch.py` (both copies) `Receiver` `take(chunk)`: the line's
VELDO-0231 flag feed against 0317's `space_output.feed`. Kept both, flags first (a flag goes out as
soon as its line is read), then the space observation.

### 1.5 VELDO-0347 (0b767d26..7bf08a96, 11 commits)

Conflicts:
- `control_space_signal.py` (both copies) `signal()`: 0334's per-ending grouping of carried items
  against 0347's new `held` (1ddccef9) and `landing` (43d45aaa) keywords on `_carry`. Kept the
  grouping loop and pass both keywords through it.
- manifest/requires: entries appended on both sides; then the 157 -> 161 renumber of 0347's suite
  applied as 0347's own change.

Combine fix a72dd21e: at 0347's own tip four registered falsifiers of other findings no longer
found their anchors (`mutation anchor moved`, 0): space330-nested-repository-not-looked-for,
space302-agent-form-refused, space324-failed-keep-still-deletes, space324-ledger-drops-ticket-end.
Re-anchored on the rewritten lines with the same defect and rows.

Open (not changed): 0334's admission retry calls `signal('admission_requested', ...)` with the
caller's keywords, so on that path the evidence remover gets no `held` reader and no `landing`;
it then keeps evidence (the safe side). Worth a look in 0347's or 0334's follow-up.

### 1.6 VELDO-0206 (veldo-0206-b, 23318512..0139a9f9, 12 commits)

Conflicts: manifest/requires (both appended); `scripts/check_teeth_mutations.py` (0347's and
0206's case blocks at the same place; kept both).

### 1.7 VELDO-0217 (23318512..ca2b1b82, 6 commits)

Conflicts: manifest/requires only.

### 1.8 VELDO-0224 (7460e9a9..897c8f11, 20 commits, restacked onto 0217 final ca2b1b82)

No conflict.

### 1.9 VELDO-0218 (44b22c72..4b1a8d24, 21 commits, restacked onto 0224 final)

Conflict in 1dabca92, `scripts/check_gate_mutations.py` (both copies), receipt fields: 0224's
`stale_unpersisted`, `reuse_unavailable` and guarded `authority_stale_count` against 0218's audit
counts (it repeated the unguarded `authority_stale_count`). Kept 0224's guarded form and 0218's
audit fields. (The branch's own first commit has `import mathimport os`; its next commit fixes it.)

### 1.10 VELDO-0221 (23318512..2909375d, 43 commits)

Conflicts:
- `scripts/selftest.py` (98671e1b, 1016a3a9): 0206's suite reuse (isolated processes, the
  dispatcher's account lines the authority's settlement reads) against 0221's whole-leg shards,
  which exit before any account line. A plain merge would leave every suite of a gate leg with no
  result in the settlement (RED). Kept both:
  - a sharded leg writes the account: `begin`, one `fresh` result per target with its shard's
    counts, `end` with the leg's exit (also on LegRefused and ShardsStopped);
  - when the gate's plan makes this leg isolate or leave out suites, the leg keeps the ordered run
    with 0206's isolated processes (the form the settlement checks), and says so on one line;
  - the shard's own Landlock layer, target mark and verdict are 0221's, unchanged; 0206's isolated
    child, banner and LEG_RAN_NOTHING rule are unchanged.
  This is a design decision for the review: reuse and shards do not yet compose (a planned
  isolated suite turns its leg ordered). Superseded by ac35f22b (section 2a): reuse operates per
  shard, and the ordered-run fallback is gone.
- manifest/requires; `check_teeth_mutations.py` (0347 and 0221 case blocks; kept both);
  `proof/WARP-0716/crossing-state.md` (generated).

Combine fix 1871c20f: the crossing-state report regenerated from the combined dispatcher; and
space333-read-bound-dropped re-anchored on the resource reader's own age condition, because 0221's
`read_shard_claims` repeats it (anchor found twice, already so at 0221's tip).

### 1.11 VELDO-0253 (199d0b6f, then 199d0b6f..406993c17; 34 commits, round 3)

199d0b6f (the spec, its 0241 amendment note and the index line; not on main 23318512) first, then the
build and its three fix rounds. Conflicts:
- `.veldo/control_service.py` (both copies), in 1d70a6a1 (from e223d668): `hint_after` keeps the
  line's `space_pass()` and 0253's waiting-loader `reconcile()` (at the end of that block since
  9693c8c5, so the anchors of findings 143 and 334 stay whole); in `serve`, 0253 moves
  `space_start()` after its installation loader starts, and the candidate's `authority_for(...)`
  (VELDO-0117 registry) replaces 0253's inline `CC.Authority(...)`, which predates it.
- `.veldo/control_api_assertion.py` (both copies), `shape_problems`: VELDO-0175's optional parameters
  (may be absent) and 0253's `base_commit` and `approval` extras on `save_workflow` in one condition:
  no name outside the spec's parameters (plus the two extras for save_workflow), and every
  non-optional parameter present.
- `.veldo/control_api.py` (both copies), in 3eb33166 (from 82bb10e5): the answer's kept fields are
  the union (the line's `conversation`, `status`, `route`, `routed_to`; 0253's `commit`,
  `configuration_commit`, `reason`, `push_refusal`).
- manifest/requires: both appended.

### 1.12 VELDO-0111 completion (veldo-0111-complete, 805c3082..bb0686b3, 10 commits, round 3)

805c3082 is an ancestor of 64199803, so the line already carries the base. No conflict.
13e5736c records in the spec History the caveat the completion review named: the io_uring
equivalence rests on the descriptor refusal and on Yama ptrace scope 1; process_vm_writev,
process_vm_readv and ptrace are not inspected, so inducing a cooperating outside process belongs to
the consumer tickets (0113, 0114); on a host with Yama scope 0 the io_uring claim covers only rings
whose descriptor the scope could hold.

### 1.13 VELDO-0114 (veldo-0114, bb0686b3..a74ca9b96, 9 commits, round 3)

No conflict. `scripts/gate_unconfined.json` is not edited (the owner decides 0114's and 0111's
entries at landing, section 7).

### 1.14 Round 4: VELDO-0111 fix (veldo-0111-complete, ef330df69 and 06e279291), 4 commits

The fix and its row sit on 3d87f11c3 (close_range accounted) and a41c2095a (its recheck), which
were not on the candidate (round 3 ended the completion at bb0686b3), so those two came with them:
568d3303d (06e279291), 093908ce7 (ef330df69), da612409c (3d87f11c3), 2d49b8313 (a41c2095a).
Conflicts: `scripts/suites/113_veldo_0111_census.py` (ef330df69 before its base: the threaded-exec
row and the close_range rows both kept) and `specs/VELDO-0111-process-and-listener-census.md`
(3d87f11c3: both History entries kept).

### 1.15 Round 4: VELDO-0113 (veldo-0113, a41c2095a..fd99daaf2, 38 commits)

8f60b4778..fb1aa408d. Conflicts: 19942d0e3 in `scripts/check_teeth_mutations.py` (0113's five
autostart113 cases beside the line's registrations) and `scripts/suites/manifest.json` /
`requires.json` (0113's two suites beside the line's). Every suite of the candidate before the round
and of each ticket's tip is in the combined manifest (checked by name).

### 1.16 Round 4: VELDO-0258 (veldo-0258 at 92624b9bf, restacked onto the 0253 on the candidate)

54 commits (336fa3004..fec2c0c12): the 0258 commits of `23318512..92624b9bf`; its 29 VELDO-0253
commits are the 0253 already on the candidate and were not picked again. Conflicts:
- 39e96bb71 and 0927b4c29: `control_service.py` (both copies): the service's command dispatch keeps
  0113's `work` and 0258's `tracker_call` branches; manifest and requires: both.
- 6eb3ec57f, 78554645e: `71_veldo_0138_channel_service.py`, `71_veldo_0130_api.py`: 0258's installation
  assets beside round 3's 58a08f0f copies of `installation_schema/` and `installation_template/`.
- 1b65768a5: `84_veldo_0169_project_handouts.py`, `86_veldo_0168_text.py`: 0258's channel custody and
  shipped service dependencies beside the line's rows (7f8c07e8's owner notice and git send in 0168's
  inventory kept).

### 1.17 Round 4: VELDO-0358 wave 1 (veldo-0358-w1 at 4bb3fefe3, 115 commits)

9c2b7bfbe..4f92fc89c, every commit of `8656888f8..veldo-0358-w1`. Conflicts, each keeping both
intents:
- 0bea09015 (brief A): `check_teeth_mutations.py`, manifest, requires: both; `selftest.py`: 0358's
  wait runtime and residue row inside the candidate's dispatcher (0206 isolation, 0221 shards).
- 52e37e151 (A): `selftest.py`: the candidate's loop (0221 shard target, the REUSED/ISOLATED filter,
  the residue row before PER_SUITE, the counts) under 0358's `WAITS is not None` guards.
- 34187cb5c: `check_space_boundary.py`: the line's 0124/0177/0206 entries and 0358's gate_legs and
  gate_load entries.
- 87a83e258 (brief C): `check_teeth_mutations.py`: 0358 moved and restated the 0214/0215 block; the
  move is taken and the candidate's `deadline215-reused-unaudited-sampled` (e4f142c66) carried into
  the moved block. `check_gate_mutations.py` (both copies): the line's reuse audit (0218/0224) and
  stale-snapshot rerun kept, the stage alarm removed as 0358 does (the rerun's re-arm becomes
  `estimate_seconds`), case receipts carry both `audited`/`reuse_key` and `kill_by`/`kills`.
  `check_first_use.py`: 0358's `heavy_run` under the hang bound, passing 0221's `shard_fds`.
- 5f71c7f23 (the opened-files record taken by the authority): `agent_sandbox.py` (both): 0221's
  `--inherit` channels and 0358's `--keep-fd` ledger both kept; prepared_launch admits a pipe or socket
  above 2, or the append-only ledger (`kept_descriptor_problem`). `gate_legs.py` (both): `_env` drops
  the ledger fd and 0221's shard variables; `confined`/`unconfined` take `keep` beside 0221's
  channels (gate_candidate.py `--keep-fd` with no channels, the launcher's `--keep-fd` with them);
  the leg keeps 0221's ShardClaims/metrics try/finally and hands `handed_env(environment)`.
  `verify.sh`: 0206's suite-state trap also removes `VELDO_OPENED_RECORD`.
- ad63ce183, 9f9dd8b1c: the ledger only when taken (gate_legs), and the line's keyword-only inherit
  call (agent_sandbox), which already passes nothing when there is nothing.
- 6414e4c50: `verify.sh`: all three traps, 0206's included, read `${VELDO_OPENED_RECORD:-}`.
- 5b23bad75 (brief G): `check_teeth_mutations.py`: brief G's cases, then the line's 0253
  init_scaffold companions loop, kept last so it covers every case.
- 2a727affa (brief F): `control_service.py` (both): 0358's apply_timers_profile/tell_passes and the
  line's domain-registry functions before serve's 0258 organ decorator; serve logs 0358's timers
  start record and keeps 0258's control-plane-call observer.
- 3af9ef1b3 (F): suite 110: 0258's outside_fixture run of `_v143_suite`; 0358's removal of the
  wall-clock seconds print.
- 6a23d6c12 (brief E): `control_engine_claude.py`: the line's `_probing()` condition with 0358's
  table-read init deadline; `control_containment.py`: 0221's instance-named slice and 0358's
  SETTLE/TOOL timers registered in the table.
- 59956905e, 0fba128a3 (E): `control_launch.py`: 0231's question stop kept; the deadline comparison
  reads 0358's wall clock (`_wall(self)`).
Every `.veldo/` copy equals its `engine/.veldo/` original (template sync passes).

### 1.18 Round 4: VELDO-0359 (veldo-0359-b2 at d62ee3faf, 29 commits)

e250d5ba3..5a682858c (`git cherry-pick -x`, base 23318512). The real bind-mount cases are deferred
by owner approval (43030) and print as deferred. Conflicts:
- f21f9c2ce (B1): manifest and requires: both. `control_launch.py`: Launch keeps 0231's flags and
  session and adds the query endpoint; Receiver keeps 0231/0176's fields and adds the query server
  and store guard; `launch()` does the line's `receiver_space` set-up first.
- eb7eee007, f6fb69abc (B1): Launch records both 0358's `ended` (last report) and 0359's query
  identity and counts; 0359's falsifiers go before the 0253 companions loop.
- 0e7bdc29c, 647d1f421 (B1 fix 1): 0359's `@_query_ended` launch body with the `receiver_space`
  set-up at its top; query notices taken apart as 0359 does, 0358's `ended` kept; `QUERY_NOTICES`
  beside 0358's `_wall`/`_await_exit` (RECEIVER_EXIT_SECONDS stays in 0358's timers table).
- 034e44f8c (B2): `control_agent_config_handoff.py`: 0359's `codex_store_guard`, `codex` keeps 0231's
  `probe`. `control_launch.py`: the record header carries the store guard and 0178's conversation
  binding; 0184's memory hold and 0359's Codex guard both applied; the wrapper gets 0358's
  `--timers` and 0359's held store guard; the setup acknowledgement keeps 0358's table-read
  `HB.setup()`/`HB.settle()` and uses 0359's `guard_status`.
- 350652220 (B2 fix 2): `control_execution_record.py`, `control_launch.py`: the header carries both
  0359's `guard_header` decision and 0178's binding.

## 2. Combine fixes found by the re-runs (after all ten were picked)

Each is its own commit, each confirmed by the suites and falsifiers named in section 3.

| Commit | Ticket pair | What was red | Fix |
| - | - | - | - |
| 8ce09b1e | 0224 on 0217 r2 | suite 158, 7 rows; finding 224 baselines invalid | the fixture binds its review record's bytes (review_sha256), as suite 100 does |
| c17f120d | 0317 on the bring-up chain | suite 159, 20 rows (AttributeError 'rendering') | the bare receiver gets the chain's __init__ defaults, as the line gave suite 146 |
| 64af93ab | 0334 with 0326 (main) | suite 133 ac1/packet-retry, ac1/packet-resent | a replayed admit/release answers its own hold's state, not the first hold the freed marks wrote (control_space.py, both copies) |
| fe2bd529 | 0206 with 0304 (main) | check_space_boundary, suite 155 (3 rows); already red at 0206's tip | selftest._isolate's one mkdtemp folder declared, pending review with design 6.10 |
| 18f880dc | 0316 with 0323/0047/0129 (main) | suites 153_0323, 66_0047 (1 row each), 82_0129 (25 rows); already so at 0316's tip | init_scaffold installs control_space_admission.py (both copies) |
| f5074f54 (corrects 5b882e51) | 0317 with 0143/0161/0188 (main) | suites 109_0161 (1 row), 116_0188 (3 rows): adopted lines' receivers refused | an unlisted repository runs without the central space wiring; store/domain mismatch still refuses (control_launch.py, both copies) |

5b882e51 named the wrong cause (a missing installation); f5074f54 reverts it and fixes the cause.

## 2a. Combine fixes, round 2 (open items 1, 2 and 4 of the first record)

| Commit | Item | Fix |
| - | - | - |
| ac35f22b | 1: 0206 x 0221 | Lead decision: the shard is the unit of execution and reuse operates per shard (below) |
| c72d7bdc | 2: space324-nested-repository-deleted | The case's row moves to suite 161 ac2/sandbox-scratch; code unchanged (below) |
| f0568050 | 4: three bring-up falsifiers | Each long wait ends on an event that also shows the defect (below) |

**Item 1 (ac35f22b).** In a gate leg cut into shards, a qualified suite runs as its 0221 shard
(own HOME, TMPDIR and runtime directory, its prerequisite closure and nothing else), which is the
isolation 0206 requires, so 0206's per-suite process (`_isolate`) is not started there. A
qualified suite whose key (its whole closure) is unchanged and has an authenticated passing record
is not started at all; every other suite runs fresh as a shard. The leg dispatcher's account names
every suite once: a reused result, a qualified shard as its isolated run (begin, one result per
closure member in order, end: the form the authority settles and publishes), or an ordinary shard
with its target's counts. A shard verdict now carries its closure's per-suite counts and the leg
result each shard's charged failures; a charge against a qualified shard, or an isolation breach
of the leg tied to no shard, counts against it, so it is never published. Authority-only
qualifications, the red rule for an unaccounted suite, 0221's AC1 to AC4 and the AC4 paired ratios
are unchanged; outside a sharded leg (no leg, a selector, no closure table, no launcher) the
ordered run with `_isolate` is unchanged. Suite 157_0206's fixture now carries the real launcher,
so its confined leg really shards under a Landlock layer; a confined shard, whose layer refuses
the fixture's outside trace file, reports its trace on its output, and the listed-leg trace is
compared as the multiset of every shard's closure. New rows
receipts/sharded-leg-runs-qualified-suites-as-shards-and-reuses-unchanged-ones and
receipts/sharded-qualified-shard-failure-is-red-and-not-stored; new falsifiers
suite206-sharded-reused-shard-started, suite206-sharded-qualified-shard-settled-as-shared,
suite206-sharded-shard-failure-published, suite206-sharded-reused-suite-unaccounted. Both specs
record the decision (2026-11-22 notes). Equivalence stated for the review: a record published from
the ordered isolated run can hit in a sharded leg and the reverse; the two differ in that a shard's
runtime directory links the user manager's sockets, which a qualified suite's non_file_inputs
"none" already excludes.

**Item 2 (c72d7bdc): re-anchored, no code hole.** The mutant disables the folder remover's walk
stop on a repository. VELDO-0347 rule 6 now defers a scratch whose repository it can see before
any remover runs, so suite 154's safety/sandbox-repository never reaches the walk (mutant applied:
154 is 55/55 green). The walk is still the only stop where rule 6 cannot see: a folder the
confined run shut in its own scratch (0347's one exception), which the remover opens. Suite 161's
ac2/sandbox-scratch drives that, and with the mutant it is red: the scratch holding an unpushed
clone in a shut folder is removed. Case name, finding, module and defect unchanged; its row is
161 ac2/sandbox-scratch. Evidence: `runs/v0324anchor.txt`.

**Item 4 (f0568050).** Found by running each mutant with the fake engines' hang detector shortened
and a stack printed at each expiry: one wait each. feed178: the owner's live stream waited for a
close the defect hides from him; a frame carries the journal position its stream reached, so each
live wait in 133_0178 AC1/events also ends when its stream passed its command's journal entry.
publish181 and reply181: both waited for the re-run turn, which only a settlement can start; the
wait in 137_0181 now ends when the turn ends, or when the request is unsettled and the loop is
quiet. Mutants now red in 3.3 s, 8.8 s and 11.6 s with the real 120 s detector; in the stage each
was rejected on its rows with full output.

## 2b. Combine fixes, round 3 (found by the full unit leg after 0253, 0111 and 0114)

| Commit | Ticket pair | What was red | Fix |
| - | - | - | - |
| 58a08f0f | 0253 with older service fixtures | 71_0138 (suite stopped, so the leg ended there), 66_0047 (10 rows) | seven fixtures that copy `.veldo/*.py` and `runtime/` also copy `installation_schema/` and `installation_template/`, as 0253's b0112c68 did for 71_0130 (66_0047, 71_0138, 83_0154, 86_0148, 103_0142, 127_0254, 128_0247); no assertion changes |
| 246167d6 | 0253 with 0047 | 66_0047 authority/installed-fixed-and-protected | the row took every bin/ entry but runtime/ for a closure module and every runtime asset to live under runtime/; the asset folders are now the top-level folders the runtime_assets record names (runtime/ always), and the record must still equal exactly the files under them |
| 4a19fa62, corrected by af2f3d2e | 0114 with suite 01 | 01_warp_0101 "suite attr check ANTI-VACUITY", and WARP-0717 AC3 through its --upto run of suite 01 | 113_0114 bound a module-level ROOT in its direct-run block, so ROOT had two bindings and scripts/suite_attr_check.py checked 0 references. 4a19fa62 renamed the uses, which broke the mutation worker's literal `ROOT / ".veldo" / "<module>"` substitution (3 of 0114's 5 cases crashed); af2f3d2e restores the uses and sets ROOT through `globals()` when run directly (5630 references checked again) |
| 7f8c07e8 | 0253 with 0168, 0186, 0162 | 86_0168 inventory/sends-and-assets, 86_0186 runtime/assets, 94_0162 (25 rows) | 0253's owner notice (`control_installation_service` `start.tell`) sent `json.dumps(event)` unrendered; it now goes through `TEXT.message(..., free_text=False)` like `Channel.tell_renewal` (same bytes for its ASCII JSON), and 0168's inventory names it and the installation repository's git `send`; 0186 expects the two new installed assets; 0162's base fixture copies them |
| c18b9188 | 0253 with 0162's helper | 95_0203 (35 rows, "the ingress configuration is absent"), 106_0185 (17 rows) | `proof/VELDO-0162/setup_assets.py`, which stands in for 0186's fixture in those suites, copies the schema and template as 0253's c90ddc9c taught 0186's |
| 7aac081b | 0253 with 0145, 0304, 0315, 0117, 0188 | 113_0145 ui/route-trace, 155_0304 service/unique-work, 156_0315 ac7/serve-order, 113_0117 (1 row), 116_0188 (4 rows) | the UI route table lists workflows.save's optional `base_commit` and `approval` (routes.ts refuses an unlisted body field, so 0253's UI save was refused before it was sent); 0304's replay of serve()'s shutdown block names `installation_watch` None; 0315's serve-order row starts the installation service as with no installation configured (its fixture's installation is a plain folder); 113_0117 and the 0088 and 0152 fixtures copy the schema and template |
| 60e50380 | 0253 with every case on init_scaffold.py | the falsifier stage stopped (driver_error, finding 145's no-op worker) | 0253 made init_scaffold.py load installation.py beside itself at import (and that loads git_process.py); the 46 cases on init_scaffold.py (33 findings) copied it alone and stopped with FileNotFoundError. They carry installation.py, git_process.py and yamlish.py as companions, the registry's pattern for a module that loads a sibling |
| 9693c8c5 | 0253 with 130, 132, 143, 144, 315, 334 | 8 registered cases' anchors no longer found once (none at 4a37d23c) | a scan materializing every case at baseline found them. hint_after's 0253 loader lines move to the end of the block, so newproject143-take-on-not-due and space334-worker-without-space-pass anchor whole again; six cases re-anchored on the lines 0253 rewrote, same defect (workflow-revision-kinds-unowned, workflow-load-returns-head, workflow-load-activates-runtime, save-base-ignored, save-speaker-is-edge, mcp144-locked-success, space315-no-worker-stop). After it the scan finds 0 moved anchors |

7f8c07e8 changes product code of 0253 (one line rendered), 7aac081b the UI's route table and
9693c8c5 the order of hint_after's steps; they need the review's eye.

## 2c. Combine fixes, round 4

| Commit | Ticket pair | What was red | Fix |
| - | - | - | - |
| 786aa07b | 0358 with every other ticket of the line | 0358's wall-clock census (`check_wallclock.py`, a gate stage): RED, 366 wallclock_site (387 sites) and 9 baseline_stale, all in files of the line's other tickets, which 0358's baseline (written at its base) never saw | not fixed here: the baseline grows only by an owner-approved change to the protected `wallclock_baseline.json`. The baseline of what is found at the combined tip is `wallclock-baseline-proposal.json`, the census output `wallclock-at-combine.txt` (section 7). Main has no baseline, so the landing gate's authority judges nothing; the first gate after landing does |
| c3cfee20 | 0359 B2 with the installation closure (0253/0258) | `control_service.closure()` refused `control_launch.py` (`invalid_input:closure:unresolved`, guard_census's runner load), so every suite deriving the closure stopped (seen at 58_0028's baseline in finding 258) | `EXTERNAL_LOADERS = ("guard_census",)` in control_launch.py (both copies), as control_verification declares its policy loader; closure() derives 196 modules again |
| c3cfee20 | 0358 with 0113, 0359 with 0308, the combine's own resolutions with 0358 | anchors no longer found once: autostart113-construction-outside-authority (claim.py's window is now 0358's contract timer; finding 113's control failed), space308-refusal-reported-before-the-space-end (0359's guard refusal record sits between), opened358-tree-drops-ledger and firstuse358-total-budget (the lines as section 1.17 wrote them) | re-anchored, same defects. A static scan of every registered case finds no other moved anchor (fixture-module cases excluded) |

## 3. Suite and falsifier results

Logs: `runs/<run>.txt` (one per run; round 3 in `runs/v1122r3.txt`, row names and counts; pc2 reds were run again on this host,
`rerun` lines). Suites that need no sandbox, pidfd or systemd ran on pc2 (remote_run.sh --share);
pc2's Python has no os.pidfd_open, so every pc2 red was run again through host_heavy at the same
commit. The rest ran through host_heavy. Falsifiers: `scripts/check_gate_mutations.py --finding`.

| Ticket | At | Suites | Falsifiers |
| - | - | - | - |
| Bring-up line | 122d95b5 | 35 suites green on this host (128, 129_0177, 130_0183, 134, 135, 138, 66, 79, 85, 86 54/54 with live rows, 96, 101 on host; the 15 pc2 reds green on host) | 78 registered: 35 rejected, none survived; feed178-conversation-by-scope, reply181-presentation-as-turn and publish181-own-inbox-only run past the 120 s worker deadline (alone, host load 7; open item 4); the rest cancelled by the stage and rejected when run again (bringup2/3/4) |
| 0316 | b7c6eb4c | 157, 146, 134, 150, 62, 83, 136_0180 green | 16/16 |
| 0334 | 636b6385 | 13 suites green (153_0309 and 156_0315 green on host) | 334+316: 31/31 |
| 0317 | 7f892aba, c17f120d, f5074f54 | 159 green after c17f120d (51/51); 151 red as on main (open item 5); 82_0129 fixed by 18f880dc; rest green | 317: 15/15 (after c17f120d and again at f5074f54); 231: 4/4 |
| 0347 | a72dd21e | 36 suites green on host (133_0326 after 64af93ab, 153_0323 after 18f880dc) | 347+330+302+324: 57 of 58; space324-nested-repository-deleted survives (open item 2) |
| 0206 | cf9bff85 | 9 suites green on host | 206: 33/33 |
| 0217 | 091ac91b | 11 suites green on host (155 after fe2bd529) | 217: 14/14 |
| 0224 | 5b4446d6, 8ce09b1e | 158 36/36 after 8ce09b1e; 8 others green | 224: 6/6 after the fix; 217: 14/14 |
| 0218 | 0b0976c1 | 159_0218 and 9 others green (158 as above) | 218+215: 22/22 |
| 0221 | 1871c20f | 157_0221 51/51; 25 others green; 157_0206 5 rows red (open item 1); 151 as on main | 221+333: 24/24; 206: 33 unjudged (157_0206 baseline red) |
| Round 2 (section 2a) | f0568050 | 157_0206 94/94, 157_0221 51/51, 133_0178 42/42, 137_0181 45/45 (`runs/v1122fix.txt`) | 206+221+333: 61/61; 347+330+302+324: 58/58; bring-up 12 findings: 78/78, none by deadline |
| Fix checks | 64af93ab, 18f880dc, f5074f54 | 133_0326 56/56, 157_0316, 158_0334, 132, 139, 153_0323, 155, 66_0047, 109_0161 81/81, 116_0188 53/53, 159, 62, 83, 127, 82_0129, 102_0210 green | 326+334: 34/34; 317: 15/15 |
| 0253 (round 3) | 9f94b4ee | 157_0253 69/69, 127_0241 50/50 (pc2); 65_0132 42/42, 71_0130 71/71, 73_0139 43/43, 85_0171 44/44, 127_0259 46/46 (host) | 253: 19/19 |
| 0111 completion | 13e5736c | 113_0111 48/48 | recheck drive (proof/VELDO-0111/ac2-attempt): baseline and final control 22/22, 13 continuation-2 mutants red, matrices valid, validate.py passed (first attempt stopped at the 2 h background limit, run again) |
| 0114 | 2f385fb3, af2f3d2e | 113_0114 31/31, 48 37/37, 113_0111 48/48; at af2f3d2e 113_0114 31/31, 01 648/648, 14 53/53 | drive.py: 5/5 detected (at 4a19fa62 2/5, the crash af2f3d2e fixes) |
| Round 3 fixes | 58a08f0f, 246167d6, 7f8c07e8, c18b9188 | 71_0138 39/39, 83_0154 40/40, 86_0148 52/52, 103_0142 49/49, 127_0254 48/48, 128_0247 46/46, 66_0047 56/56, 86_0168 52/52, 86_0186 37/37, 94_0162 52/52, 95_0203 62/62, 106_0185 46/46 | 47: 38/38; at c18b9188 253+168+186: 76 of 77, text168-prompt-collapsed survives on intake/delivery, as it already does at 4a37d23c (44 of 45; open item 8) |
| Round 3 after the leg | 7aac081b, 9693c8c5 | at 7aac081b: 113_0117 29/29, 116_0188 53/53, 113_0145 33/33, 155_0304 77/77, 156_0315 61/61, 92_0088 56/56, 93_0152 50/50, 96_0204 46/46, 110_0143 135/135, 132_0175 47/47, 149_0312 67/67, 102_0210 263/263, 120_0131 40/40, 121_0131 28/28, 122_0131 28/28, 124_0131 34/34, 13_0623 exit 2 (pc2); at 9693c8c5: 157_0253 69/69, 110_0143 135/135, 65_0132 42/42, 71_0130 71/71, 82_0144 55/55, 156_0315 61/61, 158_0334 48/48 | at 9693c8c5: 130+132+144+253+304+145+117+188+204: 274/274; 315+334: 39 of 40; 143: 62 of 64. The three not rejected fail the same way at 4a37d23c (open item 10) |
| Round 4 (sections 1.14 to 1.18, 2c) | 786aa07b, c3cfee20 | Logs in `myday research/claude-runs/r4/` (`suite-<name>.txt`, `finding-<n>.txt`, summaries `suites-summary.txt`, `findings-summary.txt`, second pass `findings2-summary.txt`, `suites2-summary.txt`). Finished when this was written: 113_0111 50/50 (host, the threaded-exec row included). The rest of the first pass (114_0113, 115_0113, 158_0258, 71_0138, 71_0130, 84_0169, 86_0168, 110_0143, 157_0358, 158_0358, 160_0358, 62_0039, 63_0040, 83_0154, 157_0359, 158_0359, 156_0315, 62_0065) runs from 15:19 on the tree at c3cfee20 | first pass at 786aa07b: 113, 258, 359 stopped at a control (control_failed): 113 and 258 by the two reds c3cfee20 fixes; 359 by 158_0359_store_guard's baseline, which makes its run directory under /var/lib/veldo and is refused in the confined mutation leg (`Permission denied`): the owner's B2 gate_unconfined entry (section 7a). Second pass (113, 258, 358 at c3cfee20, then 58_0028, 66_0047, 71_0138, 71_0130) is queued detached after the first (chain2.sh). 315, 143, 168 running |

## 4. The full unit leg (once)

`python3 -B scripts/selftest.py` through host_heavy at fe2bd529: 10975 passed, 58 failed
(`unit-leg.txt`). Of the 58: 25 (82_0129), 1 (153_0323), 1 (66_0047) fixed by 18f880dc and 4
(109_0161, 116_0188) by f5074f54, each confirmed green at the tip; 7 (102_0210) green at the tip and
at every checkpoint when run alone; 12 (151_0313) red on main too (6 there); 5 (157_0206) open item 1;
2 (86 live/claude, live/codex) and 1 (126 qualify/reproduces) are stale captures and fixtures (open
item 3).

Again at f0568050 (`unit-leg-2.txt`): 11018 passed, 17 failed. All 17 are items the lead holds:
2 (86 live/claude, live/codex) and 1 (126 qualify/reproduces) open item 3, and 14 (151_0313) open
item 5. 157_0206 is green in the full leg.

Round 3, at c18b9188 (`unit-leg-3.txt`): 11054 passed, 33 failed. 15 are items the lead holds: 2
(86 live/claude, live/codex) and 1 (126 qualify/reproduces) open item 3, 12 (151_0313) open item 5.
7 (102_0210 scratch) and 3 (120 to 124_0131 browser waits) are green when run alone at 7aac081b, as
102_0210 was in round 1. The other 8 were 0253 gaps fixed by 7aac081b (section 2b) and are green
there: 113_0145, 155_0304, 156_0315, 113_0117, 116_0188 (`runs/v1122r3.txt`, fix253d). Two earlier
attempts this round did not finish (one stopped in 71_0138, one at the 2 h background limit); their
reds are listed in `unit-leg-3.txt` and are fixed by 58a08f0f to c18b9188. The full leg was not run
again after 7aac081b.

Round 4: STARTED, not waited for (owner cost rule, 2026-11-22), at 711cebf0b (the record commit after
it changes only this file), as a detached job:
`setsid nohup myday/scripts/host_heavy.sh python3 -B scripts/selftest.py > myday/research/claude-runs/cand-1122-unit-leg-711cebf0b.txt 2>&1 < /dev/null &`
in this worktree (the command round 3 used, `python3 -B scripts/selftest.py` through host_heavy).
Log: myday `research/claude-runs/cand-1122-unit-leg-711cebf0b.txt`. Started while the round 4
suite and finding passes (section 3) were still running beside it under host_heavy's shared slots.

Where this run stopped (turn limit): every ticket is picked and committed, the reds found so far are
fixed (2c), and the record is written; open are the results of the first suite pass, findings 315,
143 and 168 (items 8 and 10), the queued second pass (findings 113, 258, 358; suites 58_0028,
66_0047, 71_0138, 71_0130), and the unit leg. Not run: finding 359 again (its store-guard baseline
needs the owner's unconfined entry, 7a), the full mutation stage, verify.sh.

## 5. Open items for the lead

Items 1, 2 and 4 are closed by round 2 (section 2a); their text below is the first record's.

1. VELDO-0206 x VELDO-0221 do not compose yet. Suite 157_0206's leg rows expect an ordered leg in
   one namespace (trace order, a prerequisite run once); 0221 runs every leg of a tree with a closure
   table as parallel shards, and in 0206's fixture tree (a placeholder agent_sandbox.py) run_shards
   stops at launcher_fds. 5 rows red, and finding 206's 33 cases cannot be judged in the gate until
   they are green. Needs a decision: how a reuse plan and shards combine (section 1.10).
2. space324-nested-repository-deleted survives: since VELDO-0347 rule 6 defers a scratch holding a
   repository before the remover's own walk check runs, so a single-module mutant of the remover
   reddens nothing. Needs a row that drives the remover directly, or a two-module case.
3. Live captures and qualify fixtures are stale on the candidate: control_launch.py changed after the
   0231 captures (0316, 0317, and f5074f54), so suite 86 live/claude and live/codex and suite 126
   qualify/reproduces (four proof/VELDO-0127/resources-*.json) are red. The combine list already
   plans qualify and one owner-approved live recapture on the combined line, after VELDO-0358.
4. Bring-up falsifiers feed178-conversation-by-scope, reply181-presentation-as-turn and
   publish181-own-inbox-only each run past the driver's 120 s worker deadline alone on a quiet host:
   the defect shows only at a hang detector (the pattern 0231 fixed in 3c775bda).
5. Suite 151_0313 is red on main (6 rows) and here (12 to 14 rows); the combine list says it needs
   the gate's confinement.
6. The 0334 admission retry signals with the caller's keywords, so on that path the evidence remover
   has no `held` reader or `landing` (section 1.5); it keeps evidence.
7. Reviews: the selftest integration (1.10, now ac35f22b), the four re-anchored cases (a72dd21e),
   the 333 case (1871c20f), the six fixes of section 2, and the three of section 2a; round 3 adds
   the three conflict resolutions of 1.11 and the six fixes of section 2b (7f8c07e8 changes one line
   of 0253's product code: the owner notice is rendered).
8. Falsifier text168-prompt-collapsed (finding 168) survives on intake/delivery: the row reads the
   question as its request's presentation (VELDO-0181), so the prompt's own rendering no longer
   reaches the chat. Already so at 4a37d23c (44 of 45), not from round 3. The case needs a row that
   reads the prompt's rendering, or re-anchoring.
9. 0253's own runs never ran the full unit leg: seven service fixtures, 66_0047's installed-files
   row, 0168's send inventory, 0186's asset list and 0162's setup helper all lacked its new assets
   or sends (section 2b). The 0258 restack onto 0253 will meet the same.
10. Three falsifiers that fail the same way at 4a37d23c, before round 3: space315-periodic-call
    runs to the 120 s worker deadline (finding 315, 24 of 25 there); newproject143-pick-unmapped and
    newproject143-ambiguous-choices-presented have a no-op control red on eleven VELDO-0065 rows of
    suite 62_0065 (finding 143, the unchanged control_channel_presentation.py copy beside its two
    renderer companions). Each stops a finding's stage; they need their own look.
11. The full unit leg ran at c18b9188, before 7aac081b, 60e50380 and 9693c8c5; those three are
    confirmed by the suites and findings in section 3, not by another full leg.


Round 4 status of items 8 to 11 (where this run stopped: their runs are not finished):
- 8 (text168-prompt-collapsed): the case names `lines/prompt` and `intake/delivery`; since VELDO-0181
  the delivered question reads its presentation, so `intake/delivery` cannot see the prompt's
  rendering. Finding 168 runs at c3cfee20 (`finding-168.txt`); if `lines/prompt` rejects the mutant,
  the case is re-anchored by dropping `intake/delivery` from its rows. Not changed yet.
- 10 (143): the no-op control of newproject143-pick-unmapped and -ambiguous-choices-presented copies
  control_channel_presentation.py beside RENDERER_COMPANIONS (text, v1, plane_calls), but the module
  also loads control_conversation_decisions.py beside itself on first use (VELDO-0181, `_decisions()`),
  the likely cause of the eleven 62_0065 reds. Finding 143 runs (`finding-143.txt`); not changed yet.
- 10 (315): space315-periodic-call ran to the 120 s worker deadline; under 0358 a case ends on
  evidence or at its hang bound, not a worker deadline. Finding 315 runs (`finding-315.txt`).
- 9: the 0258 restack met it (sections 1.16, 2c). 11: superseded by the round 4 unit leg (section 4).

## 6. Protected paths this candidate changes against main 23318512

From .veldo/policy_check.py protected_patterns, with the tickets that change each:

- `.veldo/policy.yaml` (0217), `proof/VELDO-0217/reviews/README.md` (0217)
- `.veldo/reuse_evidence.py`, `engine/.veldo/reuse_evidence.py` (0218)
- `scripts/agent_sandbox.py`, `engine/scripts/agent_sandbox.py` (0221)
- `scripts/case_inputs.py`, `engine/scripts/case_inputs.py` (0217)
- `scripts/case_reuse.py`, `scripts/case_trace.py` and engine copies (0217, 0224)
- `scripts/check_gate_mutations.py`, `engine/scripts/check_gate_mutations.py` (0217, 0218, 0224)
- `scripts/check_first_use.py` (0221)
- `scripts/gate_legs.py`, `scripts/gate_schedule.py` and engine copies (0221)
- `scripts/gate_reuse.py`, `engine/scripts/gate_reuse.py` (0206, 0218)
- `scripts/gate_unconfined.json` (bring-up: 0177, 0179, 0183, 0187)
- `scripts/mutation_case_inputs.json` (bring-up: 0175)
- `scripts/mutation_reuse.py`, `engine/scripts/mutation_reuse.py` (0218, 0224)
- `scripts/propose_case_inputs.py` (0217, 0224)
- `scripts/reuse_stamp.py`, `engine/scripts/reuse_stamp.py` (0218)
- `scripts/run_scope.py` (0206, 0221)
- `scripts/selftest.py` (0206, 0221, and the combine's integration of the two)
- `scripts/verify.sh`, `engine/scripts/verify.sh` (0206)

Round 3 (0253, the 0111 completion, 0114 and the section 2b fixes) adds no protected path: the
same 32 files, recomputed against 23318512 at 9693c8c5 with the policy's patterns.
`scripts/gate_unconfined.json` is unchanged by round 3.

Round 4, recomputed at c3cfee20 against 23318512 with the policy's patterns (`.veldo/policy_check.py`
protected_patterns, the candidate's policy.yaml, which 0358 widens), all of them, 46 files; the round
3 tickets that change each are listed above. 0111, 0113, 0258 and 0359 change no protected path;
0358 adds 14 and changes 13 of the earlier 32; the combine's resolutions (section 1.17) touch
selftest.py, verify.sh, gate_legs.py, agent_sandbox.py, check_gate_mutations.py and
check_first_use.py. `scripts/gate_unconfined.json` is unchanged by round 4 (no diff from 8656888f8).

- `.veldo/policy.yaml` (also 0358 in round 4)
- `.veldo/reuse_evidence.py`
- `engine/.veldo/reuse_evidence.py`
- `engine/scripts/agent_sandbox.py` (also 0358 in round 4)
- `engine/scripts/case_inputs.py`
- `engine/scripts/case_reuse.py`
- `engine/scripts/case_trace.py`
- `engine/scripts/check_gate_mutations.py` (also 0358 in round 4)
- `engine/scripts/check_wallclock.py` (new in round 4: 0358)
- `engine/scripts/gate_candidate.py` (new in round 4: 0358)
- `engine/scripts/gate_host.py` (new in round 4: 0358)
- `engine/scripts/gate_legs.py` (also 0358 in round 4)
- `engine/scripts/gate_load.py` (new in round 4: 0358)
- `engine/scripts/gate_reuse.py`
- `engine/scripts/gate_schedule.py` (also 0358 in round 4)
- `engine/scripts/mutation_observer.py` (new in round 4: 0358)
- `engine/scripts/mutation_reuse.py`
- `engine/scripts/reuse_stamp.py`
- `engine/scripts/verify.sh` (also 0358 in round 4)
- `proof/VELDO-0217/reviews/README.md`
- `scripts/agent_sandbox.py` (also 0358 in round 4)
- `scripts/case_inputs.py`
- `scripts/case_reuse.py`
- `scripts/case_trace.py`
- `scripts/check_first_use.py` (also 0358 in round 4)
- `scripts/check_gate_mutations.py` (also 0358 in round 4)
- `scripts/check_wallclock.py` (new in round 4: 0358)
- `scripts/gate_candidate.py` (new in round 4: 0358)
- `scripts/gate_graph.json` (new in round 4: 0358)
- `scripts/gate_host.py` (new in round 4: 0358)
- `scripts/gate_legs.py` (also 0358 in round 4)
- `scripts/gate_load.py` (new in round 4: 0358)
- `scripts/gate_reuse.py`
- `scripts/gate_schedule.py` (also 0358 in round 4)
- `scripts/gate_unconfined.json`
- `scripts/mutation_case_inputs.json`
- `scripts/mutation_observer.py` (new in round 4: 0358)
- `scripts/mutation_reuse.py`
- `scripts/propose_case_inputs.py`
- `scripts/reuse_stamp.py`
- `scripts/run_scope.py`
- `scripts/selftest.py` (also 0358 in round 4)
- `scripts/suites/shared.py` (new in round 4: 0358)
- `scripts/suites/wallclock.json` (new in round 4: 0358)
- `scripts/suites/wallclock_baseline.json` (new in round 4: 0358)
- `scripts/verify.sh` (also 0358 in round 4)

## 7. Owner items for the landing ask

- Protected-path approval for every path in section 6.
- Bring-up line: gate_unconfined.json (+6 suites across 0177, 0179, 0183, 0187) and
  mutation_case_inputs.json (0175's declarations).
- VELDO-0206: run_scope.py (and selftest.py, verify.sh, gate_reuse.py).
- VELDO-0217: .veldo/policy.yaml (reviews/* pattern) and proof/VELDO-0217/reviews/README.md.
- VELDO-0316: acknowledge the holds_recovered start-record field.
- VELDO-0224: acknowledge the proposer file added to its spec in round 0 (N1).
- VELDO-0221: six UNNAMED suites, suite 151 running alone without its own Landlock layer, two new
  space-boundary entries.
- Space-boundary entries added unreviewed: selftest._isolate (fe2bd529), and the line's
  control_clone.conversation_clone and project_runner_macos Run.release (design 6.10).
- Live recapture: the 0231 captures approved in 42874 are stale on this candidate (open item 3);
  a fresh capture run needs the owner's approval, and whether 42874 also covers the 0127 rows on the
  combined line (combine list).
- VELDO-0358 (round 4): the protected paths of section 6 (its integration-wave1.md section 6), the
  combined wall-clock baseline (section 7a), suites 126 requalify and 86 live recapture before the gate.
- VELDO-0359: spec status to ready; the real bind-mount cases deferred by approval 43030 (follow-up
  spec for a privileged fixture host).
- VELDO-0253 (spec History): the wider footprint (F8, including suite 71 and now the section 2b
  fixtures and suites), and treating project remote, landing destination, repository and trunk
  changes, and the space section's widening changes, as needing an owner decision (F4, fix round 2).
- VELDO-0111 / 0114 / 0113: the entries of the protected scripts/gate_unconfined.json, in one edit,
  since the confined gate leg refuses ptrace: 113_veldo_0114_relay_census whole; 48_veldo_0108_relay
  for rows (census) or whole; 113_veldo_0111_census (and 0113's cases when it comes). Not edited here.
- VELDO-0111: the Yama / process_vm_writev caveat is recorded in its spec History (1.12); it
  states a host assumption (Yama ptrace scope 1) the owner may want named for other hosts.

## 7a. scripts/gate_unconfined.json: the entries for the owner's landing decision

The file is protected and unchanged by this candidate's round 3 and round 4. Every entry the line's
tickets ask for, in one place, for one edit:

1. VELDO-0358 wave 1, suite 157_veldo_0358_suite_runtime, rows waits/no-idle-wake and
   waits/cgroup-gone-is-empty: no child cgroup can be made under the gate's confinement
   (proof/VELDO-0358/integration-wave1.md section 7, item 3). A row-scoped entry, or a grant of the
   gate's delegated cgroup.
2. VELDO-0113, suite 114_veldo_0113_no_autostart: the five ptrace mutation cases
   (autostart113-reaped-fallback, -transient-abstract-listener, -incomplete-counts-as-success,
   -construction-outside-authority, -cli-direct-construction), proof/VELDO-0113/ptrace-mutation-cases.txt:
   the VELDO-0111 observer traces every measured client, and the confined worker denies ptrace.
3. VELDO-0359 B2, suite 158_veldo_0359_store_guard (proof/VELDO-0359/b2-gate-unconfined-proposal.txt):
   "Fixture receiver launches use the systemd user manager, pidfds, Landlock and the namespace helper;
   nested gate confinement cannot exercise this boundary." Its falsifiers stop at the baseline in the
   confined leg (/var/lib/veldo refused, section 3, round 4).
4. The census and 113 rows already listed (section 7): 113_veldo_0114_relay_census whole;
   48_veldo_0108_relay for its census rows, or whole; 113_veldo_0111_census.

## 7b. The wall-clock baseline (VELDO-0358 census) for the owner

`check_wallclock.py` at the combined tip against the candidate's own baseline: RED, 366
wallclock_site and 9 baseline_stale (`wallclock-at-combine.txt`), every one in a file of a ticket
other than 0358 (0111, 0113, 0114, 0124, 0127, 0175 to 0187, 0206, 0217, 0221, 0224, 0231, 0253,
0258, 0316, 0317, 0334, 0347, 0359 and the e2e conversation files). The design lets the baseline
grow only by an owner-approved change; `wallclock-baseline-proposal.json` is the baseline of what
is found (2709 entries, 2829 sites): approving it as `scripts/suites/wallclock_baseline.json` makes
the census green on this line. Not applied here.

