# VELDO-0241 evidence

A unit's process is a versioned workflow revision; today's code process ships as the default definition `code`;
no definition can reach an outward step without the owner's approval. The full gate is not run here (the lead
runs it under the gate lock); every result below is a single-suite run of scripts/selftest.py with its suite selector,
which is PARTIAL by construction and is not a green gate.

## What was built

- `engine/.veldo/control_workflow.py`: the unit station kinds (build, review, gate, owner_approval, land, end) in
  STEP_KINDS, land marked `outward`, build marked `changes_subject`; `approval_problems`, run by every save:
  `invalid_input:missing_owner_approval:<node>` and `invalid_input:approval_not_last:<node>`; refused saves
  tallied by problem name (`Workflows.refusals`).
- `engine/.veldo/workflows/code.json` and `engine/.veldo/control_workflow_unit.py`: the shipped `code` definition
  (the module carries the same data for an installed service, which receives Python modules only; suite 127 holds
  the two identical), binding resolution, the unit's pin and the walk.
- `engine/.veldo/control_service.py`: the Line's `next` walks the unit's pinned revision (`station_step`,
  `step_build`, `step_review`, `step_land`) instead of `NEXT_STATION` and `after_land`; each offered station
  records `{id, version, digest, node}` in its payload; re-land and grant pass it to the land station.
- `engine/.veldo/control_landing_station.py`: `land(..., workflow=None)` records it on the land dispatch.
- `engine/.veldo/control_project.py`: `bind_workflow`, the project owner's signed command; `workflows` and the
  `workflow_bindings` change log (project, kind of work, old, new, owner, command id) on the project record.
- `engine/.veldo/init_scaffold.py`: lays the new module and `workflows/code.json`.
- `scripts/check_teeth_mutations.py`: the three declared falsifiers (finding 241); the VELDO-0148 loop cases and
  the two VELDO-0088 adapter cases re-anchored on the walk's steps that now carry their behavior.
- `.veldo/` copies synced (template sync: pass).

## Acceptance criteria

- AC1. Rows: default/shipped, default/equivalence (22 unit states, the Line of f6b081a4 read from Git as the
  oracle), default/unbound-runs-code. Falsifier v241-code-review-before-build (review and build swapped in
  code.json): default/equivalence red.
- AC2. Rows: approval/code-saves, approval/removed, approval/side-edge, approval/build-after,
  approval/build-after-land, approval/later-outward-kinds. Falsifier v241-approval-skipped-accepted (the
  reachability refusal disabled): approval/side-edge red.
- AC3. Rows: binding/owner-binds, binding/refusals, binding/kind-of-work, binding/pinned-revision. Falsifier
  v241-station-reads-head (the pinned definition read at the head): binding/pinned-revision red.

Restored green: the unmutated suite 127, 44 passed, 0 failed (`suite-127_veldo_0241_unit_workflows.txt`).
Red before the implementation: `red-before-127.txt` (the module did not exist).
Falsifier runs: `falsifiers.jsonl`, produced by `falsify.py` through the mutation driver's own materialize and
worker; it also holds the re-anchored VELDO-0148 and VELDO-0088 cases, each red on its named row.
Row observations, including every compared old and new station sequence: `observations.json`.

## Existing suites, unchanged files, run single

Green (0 failed): 83 factory loop, 86 re-land, 92 PM cycles, 116 project lines, 59 graph, 32 combined graph,
65 workflow, 70 landing, 71 projects, 123 conversations, 66 authority, 86 setup assets, 103 git identities,
26 install stamp.

101 landing reuse: 214 passed, 2 failed: `sandbox/unavailable-refuses-before-exec` and
`sandbox/old-abi-refuses-before-exec`, which drive scripts/agent_sandbox.py's Landlock checks (a file this
change does not touch) on this host's kernel. Its installed-pack row failed while the new files were uncommitted
(the pack is composed from tracked files) and passes since they are committed.

## Open

- The Notes say setup saves the default definition as an accepted revision; factory setup is outside this
  footprint, so with no binding the Line runs the shipped `code` as version 0 and nothing saves it at setup.
- Assumption: a first land is started by the landing path, as today; the Line waits at gate, approval and land
  until a land dispatch exists.
