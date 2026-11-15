---
schema: veldo.spec/v1
id: VELDO-0304
title: "The boundary check"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0302, VELDO-0303, VELDO-0324, VELDO-0333]
placement: [enforcement]
protected_paths: ["scripts/verify.sh"]
footprint:
  - "scripts/check_space_boundary.py"
  - "engine/.veldo/control_clone.py"
  - ".veldo/control_clone.py"
  - "engine/.veldo/control_batch.py"
  - ".veldo/control_batch.py"
  - "engine/.veldo/control_repository_provisioner.py"
  - ".veldo/control_repository_provisioner.py"
  - "engine/.veldo/control_space_remove.py"
  - ".veldo/control_space_remove.py"
  - "scripts/verify.sh"
  - "scripts/suites/*_veldo_0304_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0304-the-boundary-check.md"
  - "specs/index.md"
  - "proof/VELDO-0304/**"
behavior_bearing: true
observability:
  logs: >
    The check prints each refusal with the file, the function and the primitive it found, and each
    reviewed-list entry that matches nothing.
  error_taxonomy: >
    The gate is red with the function named, for one of four causes: a creation primitive outside the
    seam's list, a removal primitive outside the removers and the reviewed list, a stale entry of the
    reviewed list, or a delete decided by age.
acceptance_criteria:
  - id: AC1
    text: >
      The check refuses a creation primitive outside the seam's list
    falsified_by: >
      Add a worktree add in a new function not on the list; the check stays green and its mutation row
      fails
  - id: AC2
    text: >
      The check refuses a removal primitive outside the removers and the reviewed list of 6.10. A ref
      delete, a stash drop or clear, a reflog expire and a prune of objects are removal primitives, and
      each is refused everywhere but the owner's kept drop command
    falsified_by: >
      Restore the forced remove in the fleet module; the check stays green and its mutation row fails
  - id: AC3
    text: >
      Every entry of the reviewed list names a function and a reason, and an entry whose function no
      longer holds a removal primitive fails the check
    falsified_by: >
      Accept a list entry that matches nothing; the stale-entry row fails
  - id: AC4
    text: >
      The check refuses any function that deletes a folder, a single file or calls a remover and also
      reads a file's time or compares the clock with a threshold; this rule has no reviewed list
    falsified_by: >
      Restore the 30-day branch in prune_times; the check stays green and its mutation row fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. The gate no longer checks the lists; the seams and the removers are unchanged.
---

## Intent

The lists of creators and removers stay complete only if the gate checks them. This ticket adds a gate
check that refuses a creation primitive outside the seam's list, a removal primitive outside the removers
and the reviewed list, and any function that deletes by a file's age or by the clock.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 6.2 (the boundary check and its rule
for removal by age) and 6.10 (the reviewed list). Section 12 of the design holds the ticket itself; its
acceptance criteria and falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Boundary check. It is called from scripts/verify.sh, a protected path (policy.yaml:83), so
> the owner's recorded approval is required. It lands after 0302, 0303, 0324 and 0333 (see the build
> order).

Build order. It is built after 0302, 0303, 0324 and 0333, on purpose, and before 0315. depends_on holds
the dependencies the design states for this ticket.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

The check is called from scripts/verify.sh, a protected path (policy.yaml:83). The owner's recorded
approval, bound to the commit and the proof, is required.

## History

- 2026-11-15: lead decision, the three engine ref deletes go through a ref remover with the keep step; no exemption
  The footprint now includes those three modules and the removers, each with its synced copy.
  This resolves the scope decision recorded below; the ref remover is not implemented yet.
- 2026-11-15: resumed audit found another AC2 prerequisite conflict. The direct no-ledger removals
  remain in WorktreeProvisioner.remove (fleet.py), Runner.clear_runs and Receiver._remove_run
  (control_launch.py), Runtime.close (control_launch_work.py), GitLandOps.discard (lander.py),
  and Clones._standalone (control_clone.py), in canon and synced copies. Design 6.10 lists these
  under Replaced and says none calls a delete itself. The VELDO-0303 History instead says the
  boundary check must name the no-ledger branches; its review fixes guard them with the standalone
  look and keep step but leave the direct primitives. Treating them as reviewed-list entries
  would therefore require an additional decision about AC2 and 6.10, beyond the three ref deletes.
  Four module pairs are outside the newly expanded footprint: fleet.py, control_launch.py,
  control_launch_work.py and lander.py. The lead must resolve this conflict, preferably by moving
  their removals through the existing removers under an explicit scope extension, while preserving
  their keep checks and the owner's current ledger and signal requirements. No exemption was added,
  no removal implementation was changed, and no new loss is claimed reproduced. This is a boundary
  and scope conflict. Exact calls and source digests are in proof/VELDO-0304/resume-blocker.json.

- 2026-11-15: build blocked after the four required VELDO-0333 dependency commits were applied.
  AC2 and design 6.2 refuse every ref delete outside the owner's kept drop command. The current
  engine still deletes refs in control_clone.py, Clones._release (line 756), control_batch.py,
  Batch._swap (line 929), and control_repository_provisioner.py, remove_scaffold_ref (line 200).
  Each has the same call in its synced .veldo copy. These are pin, staging and scaffold refs,
  respectively; none is the owner's kept drop command. An exemption for these calls would weaken
  AC2, while changing the six implementation files exceeds this ticket's declared footprint.
  The lead must supply a prerequisite that resolves these calls under the owner's rule, or obtain
  an explicit scope and design decision before the boundary check can pass on this branch.
  No boundary-check implementation or removal change was made. Suites 153 for VELDO-0333 and 154
  for VELDO-0324 pass; the gate_legs.py pair is exactly the accepted VELDO-0333 version.
  Evidence and unrun checks are recorded in proof/VELDO-0304/manifest.json.
- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
- 2026-11-13: amended for the owner's rule that no work is ever lost (Telegram 41209), design section 0.
  AC2: a ref delete, a stash drop or clear, a reflog expire and a prune of objects are removal primitives,
  refused everywhere but the owner's kept drop command (VELDO-0346), so no later change can delete a kept
  ref or the commits behind it. The falsifier is unchanged.
