---
schema: veldo.spec/v1
id: VELDO-0122
title: Observe transient and out-of-directory writes during unavailable calls
status: draft
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0109, VELDO-0111, VELDO-0112, VELDO-0115, VELDO-0116]
placement: [contracts, fleet, runners]
protected_paths: []
footprint:
  - "scripts/fixtures/filesystem_census.py"
  - "scripts/suites/49_veldo_0109_unavailable.py"
  - "scripts/suites/*_veldo_0122_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - ".veldo/control_client.py"
  - "engine/.veldo/control_client.py"
  - ".veldo/claim.py"
  - "engine/.veldo/claim.py"
  - ".veldo/dispatch.py"
  - "engine/.veldo/dispatch.py"
  - "specs/VELDO-0122-unavailable-calls-have-no-transient-writes.md"
  - "specs/index.md"
  - "proof/VELDO-0122/*"
behavior_bearing: true
observability:
  logs: >
    Record process birth identity, filesystem object identity, operation, path/alias and observation interval, excluding diagnostic pipe bytes.
  metrics: >
    Count observed filesystem mutations, escaped path targets and incomplete capture results.
  traces: >
    Bind every result to the input identity, implementation digest and fixture version.
  error_taxonomy: >
    Distinguish forbidden_write, forbidden_metadata_change and filesystem_observation_incomplete.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: A filesystem observation extension records successful durable-object mutation operations during the whole client interval, including writes subsequently reversed.
      Set: VELDO-0111's measured process scope and all writable filesystem objects it can reach, including existing descriptors, renamed/unlinked files, links and paths outside both state directories; ordinary writes, truncation, creation/deletion, renaming, metadata updates, shared writable mappings and asynchronous I/O.
      Completeness: Qualify an operation inventory against the kernel mutation interfaces using independent acknowledged probes, including write-and-restore, create-and-unlink, mmap and descriptor-relative operations. Observe object identities and descendants rather than path-prefix snapshots; inability to observe any reachable mutation mechanism makes the result incomplete.
      Refutation: filesystem/transient-and-escaped-writes-are-seen is false if any acknowledged mutation is missing after the final filesystem snapshot has returned to baseline.
    falsified_by: >
      Discard events for objects outside the two state-directory path prefixes; filesystem/transient-and-escaped-writes-are-seen must turn red.
  - id: AC2
    text: >
      Claim: An unavailable mutating call writes no durable object even if it restores the original contents before returning.
      Set: The VELDO-0112 client inventory crossed with absent authority, SIGKILLed authority and relay killed before forwarding while the authority lives, using VELDO-0115/0116 lifecycle controls and fresh command identities.
      Completeness: Arm after fixture setup and the last successful watermark write, before client invocation; require zero observed mutation operations through return and descendant drain for every inventory cell. Retain recursive snapshots as a complementary check, not the event oracle. A warm read-only runtime setup disables incidental bytecode/cache creation.
      Refutation: unavailable/no-transient-write is false on any successful filesystem mutation by the refusing client even if all final bytes match.
    falsified_by: >
      Write one byte to last_seen.json and restore its original bytes before returning authority_unavailable; unavailable/no-transient-write must turn red.
  - id: AC3
    text: >
      Claim: No writable path can escape the refusal check by lying outside the enrolled clone or configured authority directory.
      Set: The same refusal product with cwd, temporary directory, home directory and a pre-opened descriptor aimed at independent writable canary locations outside both state directories in an isolated filesystem view.
      Completeness: The observer uses the inherited process scope and object identities across the complete writable mount inventory. Canary destinations are set up by the fixture before arming; exclude only the explicitly registered stdout/stderr pipes and observer-owned sinks outside the scope, never general tmp/home prefixes.
      Refutation: unavailable/no-out-of-directory-write is false if a refusing client changes an outside canary or creates and deletes a fallback ledger there.
    falsified_by: >
      Create and unlink a fallback ledger in the configured temporary directory on connection failure; unavailable/no-out-of-directory-write must turn red.
  - id: AC4
    text: >
      Claim: A missing or interrupted filesystem observer cannot be reported as proof of no side effects.
      Set: All refusal cases with normal capture, denied observation privileges, dropped events, observer death and failure to drain.
      Completeness: Each matrix result requires its complete loss-free filesystem receipt, sharing VELDO-0111's process interval and observer isolation. Every failure state must yield an incomplete qualification result and zero claims of observed absence.
      Refutation: unavailable/no-write-needs-complete-observation is false if a failed collector falls back to equal final snapshots.
    falsified_by: >
      Accept unchanged final snapshots when the filesystem collector reports event loss; unavailable/no-write-needs-complete-observation must turn red.
required_evidence: [unit, integration]
rollback: >
  Revert this capability and its consumer wiring together; retain the evidence gap as open rather than reporting coverage from the earlier weaker rows.
---

## Intent

Track the remaining write-side-effect gap that final snapshots cannot observe.

## Context

proof/VELDO-0109/README.md:58-67 and proof/prose-20260922/README.md:30 explicitly leave transient reverted writes and other paths unproven. This is separate from process creation and listener absence.

## Out of scope

Tracing arbitrary unrelated host processes, counting fixture setup writes, authority-side already-committed transactions after ambiguous relay loss, and a second process/listener census.

## Notes

Use the VELDO-0111 scope and barrier lifecycle rather than rebuilding it. The new filesystem adapter adds only mutation observation. Establish an isolated disposable writable view before arming so negative controls cannot change the developer's actual home or repository; the original call runs inside it with real enrollment and stores. Kernel-generated read atime changes and writes to the registered output pipes are not client-issued durable mutations; explicit metadata updates are. The observer and event sink remain outside what is measured.

This is planned work, not implementation evidence. All named rows below this contract are obligations for a future ready implementation. For each declared falsifier, retain the applied diff, require the named row to become false in an otherwise completed run, and revert the mutation. A crash, missing row or timeout is an invalid drive, not a detected falsifier.

