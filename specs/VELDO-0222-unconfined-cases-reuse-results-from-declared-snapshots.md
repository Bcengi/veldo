---
schema: veldo.spec/v1
id: VELDO-0222
title: Unconfined mutation cases may reuse results only when a private user manager keeps every read traced
status: draft
risk: high
owner: Dmitry Grinberg
human_approval: required
lane: standalone
depends_on: [VELDO-0208, VELDO-0217, VELDO-0218, VELDO-0219, VELDO-0220, VELDO-0224]
placement: [enforcement]
protected_paths: ["scripts/check_gate_mutations.py", "engine/scripts/check_gate_mutations.py", "scripts/case_reuse.py", "engine/scripts/case_reuse.py", "scripts/case_inputs.py", "engine/scripts/case_inputs.py", "scripts/case_trace.py", "engine/scripts/case_trace.py", "scripts/reuse_worker.py", "engine/scripts/reuse_worker.py", "scripts/propose_case_inputs.py", "scripts/mutation_case_inputs.json"]
footprint:
  - scripts/check_gate_mutations.py
  - engine/scripts/check_gate_mutations.py
  - scripts/case_reuse.py
  - engine/scripts/case_reuse.py
  - scripts/case_inputs.py
  - engine/scripts/case_inputs.py
  - scripts/case_trace.py
  - engine/scripts/case_trace.py
  - scripts/reuse_worker.py
  - engine/scripts/reuse_worker.py
  - scripts/mutation_ownership.py
  - engine/scripts/mutation_ownership.py
  - scripts/propose_case_inputs.py
  - scripts/mutation_case_inputs.json
  - scripts/check_teeth_mutations.py
  - scripts/suites/101_veldo_0208_landing_reuse.py
  - scripts/suites/*_veldo_0222_*.py
  - scripts/suites/manifest.json
  - scripts/suites/requires.json
  - specs/VELDO-0208-single-user-landing-reuse.md
  - specs/VELDO-0222-unconfined-cases-reuse-results-from-declared-snapshots.md
  - specs/index.md
  - proof/VELDO-0222/*
behavior_bearing: true
observability:
  logs: The stage names each unconfined case's qualification decision and reason; for a qualified case, its private manager's start, the units it ran and the trace check result.
  metrics: Unconfined cases declared, able to run under a private manager, reviewed, qualified, reused, audited and fresh per stage.
  traces: An unconfined case's key binds its runtime set, which includes the user manager's binaries by content; its receipt entry carries leg unconfined and manager private.
  error_taxonomy: A case that cannot pass under a private manager stays fresh as VELDO-0208 requires (unconfined_leg); a probe of the real user manager, its bus or its runtime directory is refused mechanically (real_manager_contact) and the case stays fresh; an undeclared read is declaration_stale (VELDO-0224).
acceptance_criteria:
  - id: AC1
    text: >
      Claim: a qualified unconfined case runs in a per-case snapshot holding only its declared
      files (no link to the authority checkout, the candidate or the frozen input tree), with a
      private home, temporary directory, XDG directories and runtime directory, and with its own
      user manager: the authority's worker bootstrap starts a private systemd user manager as a
      child of the worker, inside the coordinator's trace, with its cgroup delegated beneath the
      worker's own (VELDO-0219, VELDO-0220), so every unit the case starts is a descendant of a
      traced process and every read it makes is in the trace. The real user manager, its bus and its
      runtime directory are unreachable: no address for them is in the worker's environment, and
      any probe of them in the trace is real_manager_contact. It still runs unconfined; no
      confinement rule changes. Set: a qualified fixture case that starts a unit which reads a
      declared file, one whose unit reads an undeclared file, and one that connects to the real
      user bus. Completeness: row unconfined-reuse/private-manager-traced requires the first
      published, the second declaration_stale and the third fresh with real_manager_contact, and
      the real manager's unit list unchanged across all three.
    falsified_by: >
      Hand the worker the real XDG_RUNTIME_DIR. Registered mutant unconfined222-real-manager must
      fail unconfined-reuse/private-manager-traced.
  - id: AC2
    text: >
      Claim: the key of a qualified unconfined case is VELDO-0217's key with the runtime set
      defined as every file outside the snapshot that the trace shows the worker, the private
      manager or any unit opening (the interpreter, libraries, shell, Git, locale files, and the
      systemd binaries, generators and library files the manager loads), each bound by content.
      Because the manager is private there is no shared systemd configuration directory to read
      and no live manager state from outside the case, so the declaration's non_file_inputs is
      none and VELDO-0217's AC4 holds. Set: an edit to a systemd library file in a scratch runtime
      root, an edit to the owner's real systemd configuration directory, and a unit started on the
      real manager by another process during the case. Completeness: row
      unconfined-reuse/key-complete requires the first to miss every unconfined case and the other
      two to change no key and no result.
    falsified_by: >
      Leave the manager's binaries out of the runtime set. Registered mutant
      unconfined222-manager-unkeyed must fail unconfined-reuse/key-complete.
  - id: AC3
    text: >
      Claim: a case that cannot be held to AC1 and AC2 stays fresh exactly as VELDO-0208 requires:
      one whose baseline does not pass under a private manager, or passes with an observation that
      differs from its last fresh observation under the real manager; one whose suite is listed
      for some rows (refused as today); one whose inputs include a gate entry; and one whose suite
      runs its own tracer. Reused unconfined results are also audited at 10 percent (VELDO-0218), as
      a second detector, never the only one. Set: one fixture case of each class. Completeness: row
      unconfined-reuse/fresh-when-untraceable requires each fresh with its reason and nothing
      published.
    falsified_by: >
      Qualify a case whose private-manager baseline differs from its real-manager observation.
      Registered mutant unconfined222-differing-baseline must fail
      unconfined-reuse/fresh-when-untraceable.
required_evidence: [unit, integration]
rollback: Restore the unconfined_leg reason for every unconfined case; they run fresh and are never published, as VELDO-0208 shipped.
---

## Intent

982 of the 2,689 cases run in the unconfined leg, and VELDO-0208 made each of them fresh on every
gate: "An unconfined case is neither traced nor confined, so nothing bounds what it read: it is never
reuse-qualified." On 2026-10-25 those cases and their controls were 1,320 of 3,481 workers and
38,472 of 82,740 worker seconds, 46 percent of the mutation stage. Even with every confined case
reused, a landing that changes one suite would still re-run all of them, which puts a typical landing
at about 38 to 45 minutes.

## Owner decision this needs

This amends VELDO-0208's rule for unconfined cases. Under the owner's decision D2 it does so only
where every input is traced or mechanically refused: the reason those cases are untraceable today is
that the shared user manager starts their units outside the worker's process tree. A private manager
started inside the traced tree removes that reason, so nothing a qualified case reads escapes the
trace, and the audit is a second check, not the only one. Where a case cannot run that way, it stays
fresh and VELDO-0208's rule applies unchanged. The confinement does not change: the same suites still
run unconfined.

## Design

The authority's worker bootstrap (scripts/reuse_worker.py, mode unconfined) prepares the private
directories, starts /usr/lib/systemd/systemd in user mode with the private runtime directory, waits
for its private socket, points the case's environment at it, and only then starts the candidate's
suite. The manager needs a delegated cgroup subtree; VELDO-0219 gives each worker a cgroup of its
own beneath the gate's delegated scope (VELDO-0220), and the manager is given a child of it. When the
case ends, the bootstrap stops the manager, which stops its units, and the coordinator checks the
trace as for a confined declared case. Fresh runs of a qualified case use the same setup, so a
published result always comes from the setup it is reused for.

The proposer gains an unconfined probe with the same setup, so proposals record the manager's reads
and the units started, and AC3's comparison with the real-manager observation is made at proposal
time and again whenever the case is re-proposed.

How many unconfined cases can run this way is not known until the first proposal pass; the proof
records it. Expected saving: if most qualify, a typical landing re-runs about 30 to 70 unconfined
cases plus a 10 percent audit of the rest instead of all 982, some 30,000 worker seconds less, about
20 minutes, bringing a typical landing to about 15 to 20 minutes; if few qualify, the landing stays at
about 38 to 45 minutes.

## Out of scope

Which suites are unconfined (scripts/gate_unconfined.json is unchanged); confined cases; changing
the cases or their assertions.

## What the reviewer judges

Normal use: landing gates with authenticated reuse on the owner's host. Threat model: VELDO-0208's
same-account model for the unconfined leg. Out of review scope: deliberate escapes by suite code
running with the owner's authority.

## Notes

VELDO-0208's unconfined-leg section gains a pointer to this specification when it lands; until then
its rule stands.
