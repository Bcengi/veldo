# Revision notes: Veldo store lock, revisions 5 and 6 (run boundary only)

Revision 6 (2026-11-22, small) answers validation-narrow3.md; its section is the last one in this file.
Everything before it is the revision 5 record and is kept as written, except that the switch wording is
restated everywhere as the decided rule: the guard is ON by default, and the PRESENCE of store-guard.off in
the store directory turns it OFF; deleting the file turns the guard back ON.

Revision 5 date: 2026-11-21. Inputs: design.md, spec-draft.md and revision-notes.md revision 4;
validation-narrow2.md (Codex, CHANGES, five findings, reviewed against 23318512); the owner's approval with
its "Scope narrowed" section (research/approvals/2026-11-21-veldo-store-write-lock.md); and the lead
decisions given with this revision. Code re-read in the space-0329b worktree at 23318512. design.md and
spec-draft.md are rewritten in place. D and S below mean design.md and spec-draft.md revision 5.

## Lead decisions applied

| Decision | Where |
|-|-|
| Switch polarity kept: the guard is ON by default; the PRESENCE of store-guard.off in the store directory turns it OFF; deleting it turns the guard back ON (validation-narrow2.md, "Switch direction and owner safety") | D 10, S AC7. No brief instructs deletion to disable; B0 and the owner section say "create it to turn the guard off, delete it to turn the guard on" |
| Narrowed scope kept; no authority.lock capability, writer migration, signer or setup work | D 2; every fix below stays inside the run boundary. The authority socket is not moved and its authentication is not changed (D 1, D 16) |
| Fix the risky-run precondition, the remote Gate contract and the layouts that evade the alias checks or break ordinary engine startup | Findings 1, 2 and 5 below |
| Minimize what can break | Each fix removes a refusal, a mechanism or a claim where it can: the entry check gains one exact exception rather than a looser rule; opportunistic endpoint cleanup is deleted rather than made smarter; the risky floor moves a failure that already happens to an earlier, named point; the census accepts a safe configuration it would have refused |

## Findings of validation-narrow2.md: applied or kept

### Finding 1 (HIGH): the entry policy rejected the running authority's socket

Applied. Evidence confirmed: control_client.py:55 (SOCKET_NAME authority.sock) and 82 to 85
(socket_path_for, beside the binding's store path); control_service.py:1438 (configuration) and 4477 to
4480 (bind and lstat before serving); control_client.py:461 to 474 (bind makes the directory 0700 and the
socket 0600, and unlinks a stale socket first). Revision 4's "directory or regular file only" rule
refused every ordinary factory installation whose authority was running.

| Item in the finding | Revision 5 |
|-|-|
| Exact, narrowly named exception | One exception: the entry named authority.sock directly in the real store directory may be a socket, owned by the account, link count 1 (D 7 "Store entries", S AC3). Any other socket, any socket elsewhere beneath, FIFOs, devices, symlinks and extra hard links still refuse |
| Derive the path from the existing contract | The name is control_client.SOCKET_NAME in the directory socket_path_for derives; no new path or setting |
| Access expectations | Ownership and type are required. Mode is deliberately not required: bind sets 0600 just after creating the socket (control_client.py:471 to 472), so a mode check could refuse a launch racing an authority start, and the mode only governs connect, which is permitted IPC already protected by SO_PEERCRED and member signatures. A stale socket left by a stopped authority is accepted because the next start unlinks it (468 to 469) |
| Inventory of other normal entries | From code: the database, its sidecars, authority.lock, authority.sock. With no state root, the space ledger and conversation state also fall beside the store (control_space_reconcile.py:872; control_service.py:2160), but that is the no-state-root layout already refused. B0 lists the live directory; any further service-owned entry stops B2 until the spec names it (D 7) |
| Connect is not prohibited | Stated in D 3 and D 5: connecting to a pathname socket is not a Landlock filesystem right; binding a new socket needs make, which stays denied; the exception adds no grant |
| Fixtures and mutants | layout/entries: a normal running factory with an actually bound socket and an ordinary receiver launch while the authority serves, a stale socket, an unexpected socket elsewhere and under another name, a FIFO. Mutants store359-socket-exception-removed (fails the normal launch) and store359-special-entries-allowed (accepts the unexpected socket and FIFO). launch/guard-default adds connect to the running socket with its unsigned refusal, and open of authority.sock refused |

### Finding 2 (HIGH): the remote Gate did not preserve its callers and answers

Applied in full. The caller inventory is now in D 4 ("Run-side gate callers, inventoried"), from the
source: plan.py (decide, decision_blockers), frontier.py (decide, observe, coordinates, conn inside
_floor_entry at 183 to 240), work.py (decide, observe, coordinates, 125 to 173), completion_status
(landed, control_eligibility.py:475), work_state.py:336 (completion), runstatus.py:225 to 233,
control_workflow_cycle_pm.py:134 to 175 (SCHEMA by hasattr, _reading, conn), executor.py:582 to 597. No
other hasattr or getattr probe on a run-side gate exists (control_workflow_cycle.py:245 uses getattr on
the coordinates, which are members).

| Gap | Revision 5 |
|-|-|
| completion missing (work_state.py:336; registered consumer control_eligibility.py:172 to 186) | completion(unit) added: exactly the four facts of completion_contract.py:54, all false for a unit with no subject, as Gate.completion does (control_eligibility.py:730 to 740); no receipts, landing id or unit_record. landed is now derived locally from completion, as Gate.landed is (742 to 743), so the protocol has one completion request, not two. query/journey calls completion_view with the remote gate explicitly |
| Coordination rejected by the generic execution-unit check | Scope is per operation (D 9.3): work questions need an existing unit to be an execution unit of the launch repository; coordination needs an existing unit to be a pm_cycle of the launch domain and repository; otherwise coordinate_not_served. A missing cycle gets the direct Gate's own missing_authority:pm_cycle (control_workflow_cycle_pm.py:141 to 142). SCHEMA is a local member so the hasattr probe at 136 keeps its answer. query/journey and query/scope add valid, foreign and missing cycles, an execution unit passed to coordination, and a stale coordination ticket |
| Only Gate._record events preserved | Replaced. Each decide and decision_blockers response carries the events the receiver's Gate emitted for that request, in order: the station decision event (1141 to 1161), decision_dependency (895 to 916) and invalid_record (850 to 860), with a closed field list. The client delivers them to its local observe, so callbacks equal a direct Gate's. The revision 4 approach of synthesizing one event locally is removed. Mutant store359-events-dropped; the differential compares callbacks as well as returns |
| Architecture fields not frozen | Frozen from code: basis, kind, state, required, accepted, artifact (path, type, digest, control_eligibility.py:637 to 642), validator (module, role, path, digest, 604 to 606), refusals, problems or error (1171 to 1206) |
| Coordination shape deferred to B0 | Frozen: inputs team, snapshot, manager, cycle (id and digest only, control_workflow_cycle_pm.py:167 to 168) and project; watermark the journal maximum (172) |
| Floor and replication fields named by function | Floor entry: unit, record, version, state, station, lane, reason, detail, build_dispatch, review_dispatches (frontier.py:195 to 196). Replication: the eleven fields of control_replica.py:427 to 443 |
| Replication described as own-repository | Corrected: the projection is store-wide, including store-wide sequence numbers and pending command identities of every repository; stated in D 9.3 and D 9.4 and accepted, because status shows it today and it contains identities, not bodies |
| Errors | Mapping listed in D 9.3 |
| Workspace, trust, authority inputs | Receiver-bound, never from the client (D 9.3) |
| Forwarding must not authorize dispatch | Stated: dispatch and launch methods unsupported, server connection read-only, query only. A wired orchestrator gate passes through entry_gate unchanged (control_eligibility.py:464 to 465), so no orchestrator's write behavior moves |
| Caller isolation | None added, as the validation allows for this scope; stated in D 9.4 |

### Finding 3 (MEDIUM): descriptor audit after standard descriptors were used

Applied, choosing the validation's first option: one complete audit immediately after parsing the held
configuration. Evidence confirmed: control_launch.py:3842 to 3846 parse, 3847 to 3850 write stdout on a
missing executable, 3857 to 3858 write the identity line, 3859 read release from fd 0.

| Item | Revision 5 |
|-|-|
| Audit before any startup output or release read | D 5 step 2: after parsing, before 3847. One audit, not two, so the skipped-audit mutant is not masked by an independent early check |
| Report only through a validated channel | The failure byte with step audit goes to the setup pipe only when that pipe passed the audit; otherwise a silent exit with a dedicated status; never stdout or stderr (D 5, S AC2). The receiver records enforce_failed with the step or unreported |
| Do not break ordinary startup | The check is by identity and path, never by type, so a log file or terminal on stderr outside the store passes; a row proves it (launch/descriptors-early) |
| Keep fail-closed enumeration, deleted handles, close_fds, post-audit confinement | Kept; inspection failure of one live descriptor and a failed store-directory listing are now named audit failures (D 5) |
| No descriptor can arrive between audit and ruleset | Stated with its reason: the wrapper's only reads before the ruleset are of its pipes with os.read, which accepts no passed descriptor (D 5) |
| Tests | Split into launch/descriptors-early (stdout and stderr writable on the store with unchanged fixture bytes, forbidden stdin never read, setup pipe on the store) and launch/descriptors-leaked (an extra inherited handle the payload actually uses). Mutants store359-fd-check-late and store359-fd-check-skipped each bind to the row that only they can turn red |

### Finding 4 (MEDIUM): stale endpoint cleanup could remove a live endpoint

Applied, choosing the validation's second option, which removes a mechanism: no opportunistic
connection-based cleanup at receiver start (D 9.2). Cleanup has two owners that only act on a finished
owner: the receiver at run end and the Runner after observing the receiver's exit. A leftover endpoint
(both died) is inert, because dispatch ids are never reused, and goes with the runtime directory; it is a
listed residual (D 13). The directory is created exclusively; the serving thread opens its own
connection in that thread and signals ready; acceptance waits for ready within a deadline; failure is a
pre-acceptance refusal. query/lifecycle adds the bind-to-listen barrier case and a leftover-endpoint
case; mutant store359-query-startup-sweep proves no sweep returns. AC6 is amended accordingly.

Timing reconciled (the second half of the finding). D 10 and S AC7 now show pending on the accepted line
of a guarded launch, then applied or enforce_failed on the record; off and preflight refusals at once;
risky shows pending with precondition_checked, then runner_started. The revision 4 owner note claiming
"every new refusal happens before acceptance" was false and is withdrawn: the descriptor audit and the
wrapper's probe, create, add and restrict failures happen after acceptance, before any model code, and are
named as such. The risky ABI floor is no longer one of the late failures (finding 5). The status line is
described as the configuration for later launches, not a statement about running ones.

### Finding 5 (MEDIUM): rows that could not have their stated result

| Item | Revision 5 |
|-|-|
| Symlink inside pointing out in a real launch, refused by AC3 | Removed from the real-launch row. New row ruleset/primitive-symlink-out tests control_clone directly outside the preflight and documents that target resolution governs access; the production expectation is the preflight refusal in layout/entries. The outside symlink pointing in stays a real-launch denial |
| precondition-skipped cannot reach a payload on placement-refused fixtures | End-to-end census fixtures are now only routes on layouts that pass placement: a read root containing the state root, client read_link, configuration file inside the store, general seed, client seed, credential. Each has a companion run of the unchanged runner showing that it really grants or copies that route. Worktree, scratch and Git-ancestor and client-state overlap stay end-to-end placement refusals and get component census tests. No safety check is disabled to make a mutant red |
| Configured roots versus effective grants | Post-exclusion grants chosen, as preferred: the census applies grants_for's rule (agent_sandbox.py:841 to 849) to read items and leaves read-write items unfiltered (865). A broad read root with deny_read on the store is an accepted control; mutant store359-census-prefilter refuses it. Copy sources judged separately without the filter. Parity is normalized by path, rights and exclusions and checked in both directions. Absent-optional semantics kept |
| Mocked ABI 3 cannot make the real runner refuse | Resolved by moving the claim, not by a new seam. With the guard on the receiver refuses a risky launch before acceptance on a non-x86_64 platform or ABI below 6 (D 6, D 7, S AC3), mirroring agent_sandbox.py:68 to 71, which stays unchanged. The claim is now the receiver's, so a probe parameter tests it truthfully; the runner's own floor is not claimed or exercised (this host is ABI 8, and no runner probe seam is added to a protected file). This also removes a post-acceptance failure. Mutant store359-risky-floor-skipped |
| Create-failure injection hitting the version query | The seccomp filters match arguments: create refuses landlock_create_ruleset only with flags 0 and an attribute; probe refuses only the version-query form. The failure byte carries a step code so probe, create, add and restrict are distinguished on the record (D 5, D 15, S AC1) |

All mutants in D 15 and S now name the exact behavior each turns red, and D 15's rules state that a
registered name is not evidence and that an unbuildable facility is NOT RUN.

### Direct-boundary assessment and legacy layouts

Kept as the validation judged, with these clarifications: "one ruleset of several allow rules, not one
kernel rule" (D 1, D 5); mounts tested in the actual enforcement namespace (layout/mounts); no-follow
metadata for the marker (D 10). Legacy layouts: the no-runs-no-state-root refusal is kept because
accepting it breaks engine startup (D 7), with an explicit `runs` outside the store as an accepted control
and the marker-off old path tested (layout/placement). For the conventional Git-directory store, D 7 no
longer calls a move easy: the marker is the immediate recovery, and B0 must name an established
migration procedure or report that none exists. B0's live-layout pass stays an enforcement prerequisite
and now explicitly includes authority.sock, generated run paths and client places.

### ABI refusal versus warning

Kept as refusal (D 11), with the validation's facts: mainline ABI 3 in 6.2, risky ABI 6 in 6.12 and
x86_64, probe not version string, refusal costs an operator step, the marker restores the old path and
old Codex settings, and a successful probe does not guarantee installation (that is enforce_failed).

### Disposition of earlier validations

validation-narrow.md: finding 1 closed (pending versus applied now specified); 2 closed with finding 5's
post-exclusion grants; 3 closed by finding 2 above; 4 closed by finding 1 above, live layout still a B0
prerequisite; 5 closed by findings 3 and 4 above; 6 closed by finding 5 above. Original findings 3, 4 and
6 and R2 R6 stay removed with the capability work, not proven. VELDO-0113's GAP stays a GAP. None of this
is runtime proof; the rows are future required measurements.

## Owner-facing note on risk

The owner's worry is that locking is risky. What revision 5 does to keep the blast radius small:

- No change to how any Veldo process opens the store, to the lock, the authority socket, the signer,
  setup or authority start.
- The kernel rule is applied only to agent runs, after every check has passed; a failure stops that one
  launch before any model code; nothing already running is touched.
- This revision removes two things that could have broken normal use: the entry check no longer refuses
  a running authority's socket, and no receiver can delete another receiver's endpoint at startup. It
  accepts a safe risky configuration it would have refused, and it reports a risky kernel shortfall
  earlier instead of later.
- Most refusals happen before acceptance and name the fix. The two that happen after acceptance (the
  descriptor audit and the ruleset installation in the wrapper) start no engine and are named.
- Creating the marker (store-guard.off in the store directory) turns all of it OFF in one visible step;
  deleting it turns the guard back ON. B0 checks the live installation before any enforcement ships.
- Optional landing path, if the owner prefers it: create store-guard.off before B2 lands, watch OFF in
  status, then delete it to turn the guard on. A choice, not required.

## Build briefs

One specification, VELDO-0359, built as three briefs in order. B1 can land on its own: it changes no
access, only where run-side answers come from, and the marker reverts it.

### B0: measure and inventory, no product change

Scope, in a scratch launch on this host under a real ruleset built with control_clone.rules and confine
on a fixture store directory:
1. Pinned Codex 0.166.0 with danger-full-access runs a native shell command and a child, writes its
   worktree and is refused the fixture store; with workspace-write its shell command fails to start.
2. Pinned Claude Code 2.1.317 with factory settings runs its Bash tool and an ordinary build step; the
   optional-sandbox behavior is recorded.
3. Ruleset construction time against the heartbeat setup deadline.
4. A real risky launch with the shipped runner configuration reaches its payload, and the receiver-side
   post-exclusion census of that launch matches the runner's own grants.
5. A guarded fixture payload connects to a running fixture authority socket in the denied directory and
   gets the unsigned-request refusal.
By reading code and the host: every local contained launch carries the setup pipe; the authority's user
unit has XDG_RUNTIME_DIR and the Runner can observe receiver exit; confirm the run-side gate inventory of
D 4 and the frozen fields of D 9.3 against the code at the build commit; the live receiver configuration's
store path, every entry of the live store directory (expected: database, sidecars, authority.lock,
authority.sock), runs location, generated run paths, placement, and this host's client environment
(CODEX_HOME, CLAUDE_CONFIG_DIR, read_link targets); whether an established migration from the
conventional Git-directory store exists.
Output: proof/VELDO-0359/b0-measurements.md with commands, versions, errnos, timings and inventories.
Exit: both engines' ordinary tools work under the ruleset, the deadline is met, the socket connect works,
and the live layout passes the preflight. If any fails, or the live directory holds an entry the spec
does not name, or the live layout is a refused legacy layout, stop and report the concrete refusal and
recovery before B2.
Do not: change product code; touch the real store; create or delete store-guard.off on the live store;
reopen the Codex sandbox or switch-polarity decisions.

### B1: run-side readers move to the receiver

Scope: control_run_query (new, both trees): the server and the remote gate of D 9.3 (hello exchange,
SCHEMA, decide including coordination, decision_blockers, completion, local landed, floor_entry,
replication_status, per-operation scope, event envelopes, frozen schemas and error mapping); the
receiver creating the endpoint exclusively before acceptance, the serving thread opening its own
connection and signalling ready, acceptance waiting for ready, removal at run end, Runner-side removal on
receiver exit, and no startup sweep; VELDO_RUN_QUERY registered as Veldo's own; entry_gate returning the
remote gate only when no gate is wired; frontier's floor entry behind floor_entry in both modes;
runstatus's override handling and its store guard line; the switch sample as far as the query variable
(marker present: no variable); init_scaffold's module list. Rows query/journey (without the ruleset),
query/scope, query/lifecycle, and the query half of switch/off.
Depends on: B0's inventories. Exit: ./scripts/verify.sh green; differential equal on stable fields and
callbacks; zero direct opens.
Do not: add a generic method, attribute pass-through, connection, SQL, path argument or dispatch method to
the protocol; add a connection-based cleanup sweep; touch how any Veldo process opens the store.

### B2: the guard

Scope, in control_launch (both trees) unless named: the switch sample and its refusal; the preflight in
D 7 order (structured probe in control_clone beside abi, the risky floor, store directory from the
resolved database, recursive entry check with the single authority.sock exception, mounts, runs
location, placement); the post-exclusion risky census with its two-way parity check; the wrapper's single
descriptor audit immediately after parsing, reporting only on a validated setup pipe; the ruleset after
release and before the heartbeat; the failure byte with step code; pending at acceptance and applied only
on the success byte; runner_started recording; owner-visible store_guard fields on lines and records; the
Codex override in control_agent_config_handoff from the sampled decision only. All spec rows, every
registered mutant in check_teeth_mutations.py bound to its row, and the suite entry in
scripts/gate_unconfined.json (protected).
Depends on: B0 exit met, B1 landed. Exit: ./scripts/verify.sh green, each mutant red on its row, the
VELDO-0254 AC3 amendment in the spec, the proof bundle complete; then independent review in a fresh
context and the owner's landing approval for scripts/gate_unconfined.json.
Do not: add a second Landlock layer or a layer before the risky runner; add checks at authority start or
in setup; change open_store, the signer, the lock, the authority socket or control_client; edit
agent_sandbox.py or .json; change control_clone.abi; relocate the runs directory; widen the entry
exception beyond authority.sock; type-check standard streams; make Codex's sandbox off a fallback; create
or delete the marker from launch code.

## Owner-visible behavior changes

While the guard is on, which is the default (none of these while store-guard.off is present in the store
directory):

1. Agent runs cannot read or write anything in the store directory. They can still connect to the
   authority socket, which refuses them without a member signature, as today.
2. Default runs cannot mount: bubblewrap, rootless podman or buildah, unshare with mounts, Codex's own
   sandbox and Claude Code's optional sandbox fail inside them. The docker client still works.
3. Codex runs with its own sandbox off inside guarded runs, over any role setting; Veldo's rule is the
   boundary instead, which protects only the store directory.
4. Default runs cannot create, remove or rename entries directly in the store directory's parent folders
   (for a factory store: /var/lib/veldo, /var/lib, /var, /).
5. Local launches are refused on kernels below Landlock ABI 3 or with Landlock disabled or blocked. Risky
   launches below ABI 6 or off x86_64 are refused before acceptance, where today they fail later inside
   the runner. This host: ABI 8, x86_64, unaffected.
6. Local launches are refused, by name with the fix, when the store directory holds a symlink, a special
   file other than the authority's own authority.sock, or an extra hard link, is mounted a second time,
   contains the runs directory (a configuration with neither `runs` nor `state_root`), or sits under home,
   temporary, runtime, a worktree or a Git directory (including the conventional Git-directory store,
   whose immediate recovery is the marker).
7. A risky launch is refused when its runner would grant, or copy from, anything in the store directory.
   A broad read root that the runner's deny_read already excludes the store from is accepted. The
   shipped configuration is expected to pass; B0 checks it on this host.
8. Planned-run checks, frontier, the completion view and status inside a default run answer through the
   run's receiver; a run can also ask other live runs' receivers for their status answers, and the
   replication part of status covers the whole store.
9. A guarded launch line shows pending at acceptance; its record then shows applied, or enforce_failed
   with the step and no engine started. Off (with the marker's path) and refusals (reason, path, fix) show
   at once; a risky launch shows pending with precondition checked, then runner started. The status
   command shows one store guard line: on, OFF with the marker's path and time, or invalid, meaning what
   later launches will get.
10. To turn the guard off: create a regular file named store-guard.off in the store directory. To turn it
    on: delete it. Each affects launches that start afterwards; end runs started while it was off before
    relying on it again. A marker that is not a regular file (a symlink, a directory) refuses launches
    until it is deleted or replaced.

Not changed: how the authority, setup, maintenance commands, the CLI, the API process or the signer open
the store; where the authority socket is and how it authenticates; anything Veldo does outside agent
runs.

## Revision 6 (2026-11-22, small): validation-narrow3.md

Inputs: design.md, spec-draft.md and revision-notes.md revision 5; validation-narrow3.md (Codex, CHANGES:
one high, three medium, reviewed against 23318512). Code re-read in space-0329b at 23318512:
agent_sandbox.py 818 to 907, 1234 to 1285, 1329 to 1374, 2196 to 2220, 2255 to 2295; control_launch.py
3190 to 3290. Scope is not widened: no lock, writer, signer, setup or protected-runner change.

### Finding 1 (HIGH): switch polarity

Not adopted as a change of rule. The finding came from the lead's validation brief, which still carried
an old wording saying that deleting store-guard.off turns everything off. The decided rule stands: the
guard is ON by default, and the PRESENCE of store-guard.off in the store directory turns it OFF; deleting
it turns the guard back ON. The only work is wording: every place in D, S and these notes, the recovery
instructions included (D 7 refusal text and legacy-layout recoveries, D 10, D 11, D 12, S AC7, S
rollback, S Context, the owner section and the B0 brief here), now says exactly that. No activation step,
no launch-side creation, and nothing else changes for finding 1.

### Finding 2 (MEDIUM): census mixed grants with construction locations

Applied as described. D 6 and S AC4 now keep three sets apart: (a) placement and source-expansion inputs
(client places, used only by client_files to expand sources; the scratch parent, below which a fresh
scratch is made), judged only by AC3's conservative placement checks and never compared as grants; (b)
actual post-preparation grants, modelled on the same prepared configuration including the implicit
exclusions (borrow_root and every client's credential sources added to deny_read, agent_sandbox.py:2263
to 2264), exactly as grants_for, resolver_grants and qualified state_grants emit them; (c) copy sources.
Client state is modelled without calling the mutating preparation: none for an absent home, entries to be
created at the path the runner would create, entries the runner's qualification refuses are not grants.
Scratch has one symbolic identity in both computations. Parity compares only (b). New accepted controls:
an unused place and a place with only disjoint selected sources; new parity fixtures: shipped Claude and
Codex configurations, credential exclusions, absent state home, newly created state entries. New mutant
store359-census-places-as-grants. The broad-read-root-with-exclusion control is kept.

### Finding 3 (MEDIUM): early audit failure had no receiver path

Applied as described. D 5 and S AC2 add an explicit pre-identity handshake: when reading the identity line
fails, and before classifying, the receiver inspects the setup pipe and reaps the wrapper within the
existing bounded identity deadline. A failure byte with step audit records enforce_failed/audit; no byte
plus the dedicated audit exit status records audit, unreported; anything else stays today's generic
containment error. No worker is released without a valid identity, no forbidden child standard stream is
read for a report, containment cleanup is kept, and the post-release success acknowledgement is unchanged.
launch/descriptors-early now asserts the final receiver launch record; new mutant
store359-audit-late-reader-only must show the generic containment error instead.

### Finding 4 (MEDIUM): rows whose fixtures could not produce the required outcome

Applied as described.

- authority.sock: the ordinary read-only open is removed from the trial set (it fails with ENXIO even
  unguarded). Unlink, rename out and link out of the socket stay as name-protection trials; connect and
  the unsigned-request refusal are compatibility assertions in both modes. store359-guard-skipped is
  bound only to trials that succeed unguarded.
- Unresolvable required root: moved from exposure to early-refusal timing. The control refuses before
  acceptance; store359-precondition-skipped is accepted and then fails in the runner with no payload.
  Sentinel exposure is required only on otherwise valid grant or copy fixtures.
- Low ABI: the probe parameter reaches only the receiver's criterion; the wrapper sees the real ABI and
  control_clone.confine and the runner keep their own floors. The mutant is renamed
  store359-low-abi-accepted; its distinguishing failure is acceptance, and on an actual ABI-2 host it is
  accepted and then ends enforce_failed with no payload.

### What changed in this round

1. Switch wording made uniform in D, S and R, recovery instructions included: ON by default, PRESENCE of
   store-guard.off turns it OFF, deleting it turns it back ON. Rule unchanged.
2. D 4, D 6 and S AC4: census split into placement inputs, actual grants and copy sources; parity on
   actual grants only; scratch symbolic; read-only state modelling; new controls, parity fixtures and
   mutant store359-census-places-as-grants.
3. D 5 and S AC2: explicit receiver pre-identity handshake for an audit failure; launch/descriptors-early
   asserts the final record; new mutant store359-audit-late-reader-only.
4. D 15 and S AC1, AC3, AC4: socket open removed from the trial set; unresolvable root moved to
   early-refusal timing; low-ABI mutant renamed store359-low-abi-accepted with its real outcome.
5. D header and S Context and History updated to revision 6.


## Lead correction after round 6 (2026-11-22, validation-narrow4 finding 4, LOW)

Grant-set parity is limited to fixtures on which the runner's grant preparation succeeds (design section 6, row launch/risky-census, spec AC4). The unresolvable required-root fixture is judged by the named pre-acceptance census refusal and, with only the census skipped, acceptance followed by runner failure and no payload. A component fixture whose unchanged runner qualification refuses is judged by its expected refusal outcome. The successful shipped-configuration, credential-exclusion, absent-home and newly-created-state parity fixtures are kept. Applied by the lead exactly as the validator wrote it; findings 1 to 3 of validation-narrow4 passed.


## B0 lead disposition and B1 boundary (2026-11-22)

The lead authorized B1, then B2: both engines' tools work under the ruleset, setup takes at most
3.3 ms against the 5 s deadline, and the authority socket connection receives the designed refusal.
The fourth exit condition has no live layout to inspect on this host. Preflight runs at the first
real installation, with the design's named refusal and marker recovery. No live store is involved
in B1; it uses fixtures and no live engine. The requested suite runs replace running the full
verification script for this brief; no full-verification claim follows from those partial runs.

B0 findings retained, without product changes to address them: Codex workspace-write fails because
AppArmor blocks bwrap on this host, including without the ruleset. Claude Code's optional sandbox
switches itself off because socat is absent. Neither finding is caused by the ruleset.

B1's serving Gate uses the same installed receiver configuration and host/settlement trust as
Receiver._recheck, with its own read-only connection opened on the serving thread. The configured
binding supplies workspace and coordinates; no client can supply them. A conversation receiver
has no repository, so its hello cannot match any enrolled checkout. The client reads only its
local enrollment binding to compare repository identity. No store-opening behavior of an existing
Veldo process is changed.

Cleanup has the two designed owners. The receiver reports the new directory's device/inode before
binding; the supervising Launch drains its reaped receiver's remaining notices and removes only
that reported directory identity. This preserves an existing endpoint on exclusive-creation failure.
No connection-based startup sweep exists. Request logs contain only request name and outcome;
termination counts are collected before or with the receiver's final messages.
