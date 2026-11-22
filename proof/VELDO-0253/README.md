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
- Static checks: 1,259 Python files and 40 shell files; 333 template pairs; zero personal-setup findings.
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
