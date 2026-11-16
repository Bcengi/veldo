---
schema: veldo.spec/v1
id: VELDO-0324
title: "The batch clone and the sandbox launcher's scratch go through the safety rules"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0302]
placement: [engine, loop]
protected_paths: ["engine/scripts/agent_sandbox.py", "scripts/agent_sandbox.py"]
footprint:
  - "engine/.veldo/control_batch_service.py"
  - ".veldo/control_batch_service.py"
  - "engine/.veldo/control_clone.py"
  - ".veldo/control_clone.py"
  - "engine/.veldo/control_space.py"
  - ".veldo/control_space.py"
  - "specs/VELDO-0302-veldos-own-creators-declare-before-they-create.md"
  - "engine/.veldo/control_batch.py"
  - ".veldo/control_batch.py"
  - "engine/scripts/agent_sandbox.py"
  - "scripts/agent_sandbox.py"
  - "engine/.veldo/control_space_remove.py"
  - ".veldo/control_space_remove.py"
  - "scripts/suites/*_veldo_0324_*.py"
  - "scripts/suites/102_veldo_0210_agent_profile_runtime.py"
  - "scripts/suites/103_veldo_0211_borrowed_login.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0324-the-batch-clone-and-the-sandbox-launchers-scratch-go-through-the-safety-rules.md"
  - "specs/index.md"
  - "proof/VELDO-0324/**"
behavior_bearing: true
observability:
  logs: >
    The batch's and the launcher's removals are outcome records. A refusal is a deferral with the rule's
    name.
  error_taxonomy: >
    A refusal at a batch's discard is a deferral, never an ignored error. A launcher's scratch whose lock
    is held or whose borrowed login is not settled is space_deferred:in_use.
acceptance_criteria:
  - id: AC1
    text: >
      A batch's discard removes its clone through Signal; a refusal is a deferral on the saved batch
      and request records and never an ignored error. Its observation folder is reviewer evidence
      declared to end at verdict_recorded, not at batch end
    falsified_by: >
      Leave the direct delete in place; the row with a process holding an open file in the clone finds the
      folder gone and fails
  - id: AC2
    text: >
      Under a recorded run the sandbox launcher declares its scratch as a child of the run's scratch root
      and deletes nothing itself; the scratch is removed at the run's run finished, including directories
      the confined process left unreadable
    falsified_by: >
      Leave the launcher's own delete in place; the scratch folder is gone while its item is still
      present, and the row fails
  - id: AC3
    text: >
      The stale scratch pass does not exist: a scratch folder two fixture days old whose lock is free
      stays when a launcher starts, with an installation and without one
    falsified_by: >
      Leave the stale pass on where no installation exists; the row without an installation finds the
      two-day-old folder gone and fails
  - id: AC4
    text: >
      With no space environment the launcher otherwise behaves as before the change: it starts its run,
      and it removes its own scratch at its own end
    falsified_by: >
      Require the ledger; the adopter fixture with no installation fails to start its run and the row
      fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. The batch and the launcher delete directly again, and the launcher's stale scratch
  pass removes by age again.
---

## Intent

Two more removal paths go behind the safety rules, and one goes away. A batch's discard removes its clone
and its observation folder through Signal. Under a recorded run the sandbox launcher declares its scratch
and leaves the removal to the run's event. The launcher's pass that deleted scratch older than a day is
deleted in every case: nothing in Veldo removes by age.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 6.10 (the batch row and the two
sandbox rows of the Replaced table), 7 (rule 4) and 13 (the decision that nothing removes by age). Section
12 of the design holds the ticket itself; its acceptance criteria and falsifiers are copied here word for
word.

What section 12 says about this ticket:

> Components: Batch, Sandbox (protected, the owner's recorded approval is required), Removers. Depends on
> 0302.

Build order. It is built after 0301, in any order with the other tickets of that step (0302, 0303, 0305 to
0314, 0323, 0324, 0328, 0329, 0333, 0335, 0336, 0337 and 0341). depends_on holds the dependencies the
design states for this ticket.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

The sandbox (engine/scripts/agent_sandbox.py and its synced copy) is a protected path, policy.yaml:22 and
35. The owner's recorded approval, bound to the commit and the proof, is required.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
- 2026-11-13: from the owner's rule that no work is ever lost (Telegram 41209), design section 0. No
  acceptance criterion changed. A batch clone is a private repository (VELDO-0347 AC3), and a repository
  found beneath a sandbox launcher's scratch holds that scratch unless it is a clean clone (VELDO-0347
  AC2).

- 2026-11-15: built the supplied-ledger seams. Batch observation folders remain evidence as
  VELDO-0302 declares them; Signal keeps that evidence at run finished. The batch lifecycle
  addition belongs to VELDO-0347, so it is a named fixture stand-in, not a production change.
  A batch with no ledger defers rather than deleting work it cannot record or save. Recorded
  sandbox scratch requires the supplied ledger and a present scratch parent matching the run
  label and TMPDIR. No service startup wiring is added. The launcher restores directory access
  while holding its scratch lock, leaving deletion to the existing remover. The two older
  sandbox suites now expect killed launchers' scratch to remain, consistent with AC3; their
  borrowed-login recovery checks remain. Their test paths are added to the footprint above.

- 2026-11-15: fix round after independent review. Discard emits and saves its outcome;
  request records carry outcomes and deferrals after discard, including no-ledger refusals.
  The protected launcher leaves permission recovery to the existing remover. A row refuses
  another run's scratch parent. The lead's VELDO-0302 decision amends AC1: observation
  evidence ends at verdict_recorded. The creator seam passes that explicit event selection
  to the ledger, which validates it against the kind's lifecycle. Footprint includes the
  request writer and this declaration path. The earlier permission-restoration note is superseded.

- 2026-11-15: fix round 2 after the re-review. The ends_on option on the ledger's declare, the
  creator seam and the batch is removed: design 4.1 and 6.1 copy the end list from the kind
  registry, and the chosen list had dropped ticket ended and project ended, so observation
  folders would never have been removed. Lead decision: the folder keeps the evidence kind's
  default end list. Row ac1/observation-end asserts that verdict_recorded, ticket ended and
  project ended are all on it and that the folder survives batch end; row safety/no-end-option
  replaces safety/invalid-end-events. Read AC1's "declared to end at verdict_recorded" as:
  verdict_recorded is on its end list. The design now calls the folder evidence. The ledger and
  creator-seam files are back to their content before the first fix round.
- 2026-11-16: lead decision at assembly, VELDO-0304's decision stands: a batch without its ledger
  removes its clone through the removers' standalone entry after the look and the keep step, and a
  missing ledger is no refusal. The rows safety/batch-no-ledger, ac1/saved-deferral,
  ac1/saved-reassembly and the six ac1/saved-request rows now expect that: the clone's unique work is
  kept in the main repository by the keep step, then the clone is removed; a deferral only when the
  keep step cannot keep or the clone is in use; the observation folder is evidence and stays, kept.
