# VELDO-0143 round 3: rebased onto VELDO-0161 round 9

Before: agent/claude/veldo-0143 at 06658f1e, twelve commits on VELDO-0161 round 5 (8f749423).
After: the same twelve commits replayed onto 928918a5 (VELDO-0161 round 9: rounds 6 and 7 make an upgraded host
lay the adoption signer down, round 8 owes the service a restart for it, round 9 is suite 86's evidence). Only
agent/claude/veldo-0143 was rewritten (`git rebase --onto 928918a5 8f749423 agent/claude/veldo-0143`).

| Old | New | Commit |
| --- | --- | --- |
| f993e8d7 | e38db1bd | a new project from chat, created or adopted and activated on the owner's one answer |
| 4689067d | 57f8ac38 | footprint and history; finding 143's mutations; suite 106 |
| bc81c1b8 | 14ccfa05 | the owner told by a VELDO-0128 report |
| dfeb0eca | dac16825 | the provisioner configuration setup lays in the state root |
| e2fe2e8e | d4fabcbd | proof bundle of round 1 |
| d859b3db | 07a1d304 | the adaptation to VELDO-0161 round 5 |
| a07ad991 | 124b84ef | the first rebase's proof |
| 1b2fb86b | 648601b0 | round 2: pm/new-project-run's colliding name |
| e2e2bc1e | d0413423 | round 2: no ssh-keygen reaches an SSH agent |
| 6d2880b2 | 486881fd | round 2: the scaffold lays init_scaffold.py |
| c1bf6dec | 493157b6 | round 2: finding 143's two new mutations, the falsifier driver |
| 06658f1e | bf6c44ac | round 2: proof |

## Textual conflicts

None. Every commit applied cleanly. Three files are changed on both sides, in disjoint regions:

1. `control_factory_setup.py` (engine and .veldo). 0161 rounds 6 and 7 add `lay_adoption_signer` and its call from
   the engine upgrade (a laid adoption signer, its line in the host's enrollment signers and the installation's
   copy, and the step-log debt of a restart); 0143 adds step 12 (the provisioner configuration), the factory
   project's own repository and `factory=` to `store_steps`. Git merged them; the merged file holds both, and
   its `.veldo/` copy equals the engine file.
2. `scripts/check_teeth_mutations.py`. 0161 registers `upgrade161-adoption-signer-not-laid` and
   `upgrade161-adoption-restart-not-owed` after its round-5 cases; 0143's finding-143 block follows them, unchanged.

The pseudo-refs the rebase leaves (AUTO_MERGE, CHERRY_PICK_HEAD) were removed from this worktree's own git
directory by hand, as in the first rebase: the sandbox refuses `packed-refs.lock` in the shared git directory.

## What 0161 rounds 6 to 9 change for 0143

- The upgrade path (control_factory_setup_upgrade, suite 86) now lays the adoption signer, so a new project's
  creation on an upgraded host is no longer refused `signature_refused:not_enrolled` for want of it. 0143's
  provisioner uses the signer exactly as 0161's adoption effect does; nothing in 0143 changes for it.
- The upgrade does not lay 0143's `host/provisioner.json` (step 12 of a fresh setup). An upgraded host is
  therefore an installation without a provisioner configuration: finding F6 of the review. Round 3's fix for F6
  (no proposal presented or settled that the installation cannot carry out, and the owner told why) covers it;
  laying the configuration on upgrade is not in 0143's specification (DECISIONS 5: a factory set up before this
  change keeps what it has).
- Suites 85 and 86 compare a fresh setup with an upgraded one (proof/VELDO-0189/fresh-equivalence.json), and a
  fresh setup on this branch lays one file more (`.veldo/init_scaffold.py`, round 2) and writes
  `host/provisioner.json`. Neither suite runs in this sandbox (systemd user manager); both are on the host run list.

## Checked here after the rebase

- Every `.veldo/` copy 0143 changes equals its engine file.
- Suite 110 at the rebased head bf6c44ac with the graph stage and the recording agent stood in
  (`round2/sandbox_run.py --stage --agent`): 50 passed, red only service/hand-off (AF_UNIX), as at 06658f1e
  (`110-rebased.json`).
