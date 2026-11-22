# VELDO-0253 implementation handoff

The owner-approved criteria and amendment remain unchanged. The manifest keeps every criterion pending:
this bundle is not an independent review, an aggregate unit pass, a gate pass, or a landing approval.

## Implementation

`installation.py` owns Git tree/object/ref operations and the OS reference subscription. The shipped
`installation_schema/schema.json` declares paths, closed kinds, and widening fields. The loader validates
all files and cross references before one store transaction records the accepted configuration, provenance,
resolved bindings, workflow content copies, revisions and layouts. Invalid trees retain the last good record. Every settings reader in the service uses the accepted
snapshot, including when the original commit has been pruned; working files cannot replace it.

`control_installation_decision.py` uses ordinary signed VELDO-0068 terms, presentation and settlement for
an exact commit and widening digest. The Git author is provenance only. Metadata-only edits and authority reductions do not request
approval; changing the declared remote does, since it changes where the private configuration is sent. A superseding commit cancels the
old decision. A signed owner-save packet verifies the exact proposed commit and settles that same request.

Canvas saves validate the whole proposed tree, create Git objects without touching the working copy/index,
and compare-and-swap the branch against the accepted parent. Waiting saves keep the draft. Layout-only
commits retain the definition version. Installation bindings override the shipped code default; configured
stores refuse the old workflow and binding writers, including on a separately opened connection.

Setup creates a private repository and imports live workflow heads, old revision content copies, project
bindings, role revisions, teams/default team, memory, accounts and supplied settings. Existing account
settings survive the import, including binary paths from setup's qualified engine record. It records the
service environment and sends accepted commits to the declared remote without force. A remote refusal is
reported while the accepted local configuration remains live.

## Falsifiers

Finding 253 has exactly four registered cases in `scripts/check_teeth_mutations.py`:

| Criterion | Mutation | Required red row |
| --- | --- | --- |
| AC1 | install253-partial-commit | ac1/whole-commit |
| AC2 | install253-tool-not-widening | ac2/widening-waits |
| AC3 | install253-store-save | ac3/one-source |
| AC4 | install253-pin-from-git | ac4/pinned-survives |

`mutations-initial.json` is the selected confined-driver receipt from implementation commit e223d668413.
It records four registered/executed/rejected cases, zero invalid results, and green baseline/no-op legs.
The corresponding target row is false for each mutant; dependent later rows may also fail. This receipt
is historical, not a claim that a later tree has been gated. A current host recheck is queued.

`registered-workers.json` records current production bytes at commit 0f486f8dc697. The portable
`registered_workers.py` invokes the existing registry materializer and worker CLI on pc2, with a separate
process for each baseline, no-op and mutant. Every baseline/no-op has 52 true observations; all four
mutants turn their specified row false. This confirms current anchors and red/green behavior. It is
explicitly a worker diagnostic, not a substitute receipt for the confined coordinator or a gate pass.

## Diagnostics and limits

All runs used committed snapshots. Compute runs named pc2 explicitly. Host-only checks use the owner's
external host-heavy wrapper. No timing assertions or sleeps were added: notification tests synchronize
on an OS descriptor, and new subprocess/event hang detectors allow at least 120 seconds.

The `.txt` transcripts retain the partial-run warning and exit code 2 where applicable. They are debugging
records, not unit verification evidence. `diagnostic-sources.json` records each node run and raw log hash;
home roots are redacted and remote cleanup messages after command exit are omitted.

- Ticket diagnostic: 26 ticket rows and 24 existing workflow-binding rows, zero failed (plus 26 shared validator rows).
- Workflow binding diagnostic: 24 existing VELDO-0241 rows and 25 ticket rows, zero failed.
- Setup diagnostic: 30 existing space/setup rows and 25 ticket rows, zero failed.
- Static checks: 1,260 Python files and 40 shell files; 333 template pairs; zero personal-setup findings.
- UI: locked dependencies installed on pc2 and `npm run typecheck` exited zero. Node emitted dependency
  engine-version warnings; no dependency or lockfile changed.

The following pc2 reds were compared with the pre-implementation parent c1cbb7c3 on pc2:

| Suites | Candidate / parent result | Limitation |
| --- | --- | --- |
| 65 workflow | same six failed rows | qualified runtime graph unavailable |
| 71 API | same setup exception | unavailable_service:profile:user_manager |
| 73 factory setup, 85 setup API | same 31 failed rows | unavailable user manager |
| 127 installation reader | same one failed row | home-as-tilde fixture and remote HOME |

The paired transcripts are retained. These are not waived product failures or counted passes. The host
recheck is still queued; its completion and the lead's full gate/independent review remain outstanding.
The canonical verification command was not run, as instructed. No approval is asserted.

The queued host request is recorded in `host-request.json`; it leaves its immutable checkout and raw
results under the named temporary output pattern. Those future results are not claimed by this bundle.

## Fix round 1 (review FIX, F1-F9)

The criteria and the amendment are unchanged. Each finding has a row in suite 157 and a registered
falsifier for finding 253; the twelve new cases join the four criterion cases.

| Finding | Fix | Row | Falsifier |
| --- | --- | --- | --- |
| F1 | A removed `changed` field widens; deleting a project file with bindings, or an override of a product default, widens | ac2/binding-removed, ac2/connector-removal | install253-removal-not-widening, install253-deleted-binding-narrows |
| F1 | Narrowing still applies directly (the spec's allowed list) | ac2/narrowing-direct | install253-deletion-widens |
| F2 | Memory servers, stores, sink and manifest are classified | ac2/memory-server | install253-memory-unclassified |
| F2, F3 | Memory, schedule and deploy target references are checked; the last good configuration stays | ac1/cross-references | install253-memory-references, install253-schedule-references, install253-deploy-references |
| F4 | A project's remote, landing destination, repository and trunk widen (owner ruling requested in the spec History) | ac2/project-remote | install253-project-remote |
| probe | Bot token reference, trackers, raised inbound file cap and body limit widen | ac2/other-widening | install253-bot-not-widening |
| F5 | A plain value under a credential-named key is refused and never stored or told | ac1/plain-credential | install253-plain-credential |
| F6 | Setup's import refuses a credential in an unread file before committing or sending | ac1/unread-secret-import | install253-unread-import |
| F7 | A clean checkout follows a save; a dirty one is untouched | ac3/working-copy-follows | install253-checkout-left-behind |

Which is which: docs/installation.md lists every change that waits for the owner and every change
that applies directly. Only narrowing (removing a tool, adding a never rule, removing a port and the
like, lowering a limit, deleting a file whose removal only takes authority away) and metadata apply
without a decision.

F8 is recorded in the spec History for the owner (the footprint widening and the F4 classification).
F9: the original sequential fixture is unchanged; every new row runs on its own installation and
store, and an exception in one new row fails only that row.

Fix-round transcripts: `fix-ticket-pc2.txt`, `fix-bindings-pc2.txt`, `fix-workers-pc2.txt`
(registered worker diagnostic for all sixteen cases), and `fix-host.txt` for the host-only suites and
the confined coordinator, recorded only once they have run.

Fix-round pc2 results at 0d3adb5ac9b5 (diagnostics, not a gate pass): suite 157 has 36 rows passed and
0 failed. Suites 127_0241 and 157 have 86 passed and 0 failed. The registered worker diagnostic passes
all sixteen cases: baselines and no-ops are green at 62 observations, and each mutant turns its target
row false. Each of the twelve new mutants fails only its own row. The host-only suites and the
confined coordinator were queued behind full builder slots when this was recorded; no host result is claimed.
