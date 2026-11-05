# VELDO-0247 evidence

Check and join steps and parallel branches. The full gate is not run here; every suite result below is a
single-suite run of scripts/selftest.py with its suite selector, PARTIAL by construction and not a green gate.

## What was built

- `engine/.veldo/control_workflow.py` (and the `.veldo` copy): optional `fields` (type, source, choices, private);
  the `check` kind (closed config: ordered named branches of {field, comparison, value} conditions plus a required
  `otherwise: true`; ports are the branch names plus otherwise, one transition each); the `join` kind ({inputs});
  a port with several transitions is a fan-out of at most FAN_OUT_CEILING (8); `block_problems` (each branch reaches
  the one join naming exactly its fan-out's branch ids, nothing leaves or enters a branch, no nested fan-out);
  `ran_before` (a field from a node's result must come from a node on every path to the check, a block's branches
  all preceding its join); `branch_approval_problems` (approval_in_branch, outward_in_branch, as VELDO-0241's
  names); `evaluate` and `redacted` (the check as data; a private field's observed value as its digest).
- `engine/.veldo/control_graph_langgraph.py`: a fan-out suspends at `veldo_parallel`; the PARALLEL node starts
  every branch that has not reached the join through Send in one superstep, each writing only its own key of a
  reducer-merged `branches` state; COLLECT gathers them and counts one step per branch node that moved; the join
  runs only when every branch has reached it.
- `engine/.veldo/control_workflow_langgraph.py`: the check and join step kinds; a fan-out names its join; a branch
  node reads `<input>@<node>` and stays when its input is not here.
- `engine/.veldo/control_workflow_cycle.py`: supplies a check's field values from the store, re-evaluates every
  check and refuses a difference (unsupported_workflow:branch_mismatch); field_unsupplied fails the step; records
  `decisions`; judges the fan-out, each branch superstep (one shared superstep, every branch transition) and the
  join; dispatches assignment branches without waiting for one another; events check, fan_out, superstep,
  branch_step, arrive and the join step; metrics in `Cycles.metrics`.
- `scripts/check_teeth_mutations.py`: the four declared falsifiers (finding 247).
- `scripts/suites/128_veldo_0247_check_join.py`, registered in manifest.json and requires.json.
- Round 2, the Line part: `engine/.veldo/control_workflow_unit.py` (and the `.veldo` copy): check and join are
  accepted in a unit's process; `walk` starts every branch of a fan-out in the same pass on its own state (`fork`),
  counts every branch node in the step budget and goes on from the join only when every branch has arrived;
  `parallel_problems` refuses parallel_station at binding. `engine/.veldo/control_service.py` (and the copy): `latest`
  also keys records by node; `at` reads by node when a process holds several nodes of one kind (one node per kind
  reads as before); `step_check` evaluates as data over subject fields, records the route in the pass (`checks`) and
  in every later station's payload, refuses field_unsupplied and branch_mismatch; `step_join` merges the branches.
  `scripts/suites/129_veldo_0247_line.py`, registered; two falsifiers in `scripts/check_teeth_mutations.py`.

## Acceptance criteria (suite 128, 45 passed, 0 failed: `suite-128_veldo_0247_check_join.txt`)

- AC1. Rows check/configuration-accepted, check/configuration-refusals (no otherwise, undeclared field, unknown
  comparison, comparison the type does not allow, wrong value types, a field from a step not on every path, the five
  extra keys on condition, branch and config, and eleven code-like values including "$(rm -rf .)", each refused by
  name with nothing written). Falsifier v247-check-without-otherwise-accepted: check/configuration-refusals red.
- AC2. Rows check/one-branch (many, risky, otherwise on the real runtime: exactly one next node waited at, the
  decision naming the rule and every condition with its observed value), check/field-unsupplied (missing field and
  wrong type: invalid_input:field_unsupplied:files, no branch), check/forged-branch (a runner whose rule always holds:
  unsupported_workflow:branch_mismatch), check/observations. Falsifier v247-runner-branch-trusted:
  check/forged-branch red.
- AC3. Rows fanout/dispatched-together (both assignment branches dispatched before either result; both first nodes
  in LangGraph superstep 2; join once; five steps counted), fanout/join-waits-for-all (one result in: the join has
  not run and the cycle waits; both in: it runs once), fanout/bounded-at-save (9 refused fan_out_too_wide, 8
  accepted, join_inputs, branch_escapes_join), fanout/actual-langgraph. Falsifier v247-join-on-first-input:
  fanout/join-waits-for-all red.
- AC4. Rows approval/branch-around-approval, approval/check-after-approval, approval/in-branch,
  approval/land-in-branch, each refused with VELDO-0241's named problem and nothing written; approval/moved-accepted.
  Falsifier v247-otherwise-around-approval: approval/branch-around-approval red.

Red before the implementation: `red-before-128.txt` (15 rows failed). Falsifier runs: `falsifiers.jsonl`, produced
by `falsify.py` through the mutation driver's own materialize and worker; restored green is the suite-128 run.

## The Line part (suite 129, 40 passed, 0 failed: `suite-129_veldo_0247_line.txt`)

Rows line/unit-accepts-check-join, line/check-one-branch, line/check-field-unsupplied, line/check-recorded-mismatch,
line/dispatched-together (both branches' stations offered in one pass before either result), line/join-waits-for-all
(one branch in: nothing offered; both in: the review after the join offered once, on the docs branch's build),
line/budget-counts-branches, line/fan-out-bounded (9 refused, 8 accepted, parallel_station), line/approval-every-path.
Red before: `red-before-129.txt` (9 rows failed on the pre-implementation Line). Falsifiers v247-line-join-on-first-
arrival (line/join-waits-for-all red) and v247-line-branches-in-turn (line/dispatched-together red): `falsifiers.jsonl`.

## Existing suites, run single (0 failed each)

65 workflow, 127 unit workflows, 59 graph, 62 runtime, 92 PM cycles, 66 authority, 71 API, 93 intake routes,
73 backlog, 82 decomposition, 96 reservation policies, 110 new project, 113 UI, 86 engine upgrade, 83 factory loop,
86 re-land, 116 project lines. Round 2, after the Line part, each again: 129, 128, 127, 65, 59, 116, 70 landing,
86 re-land, 83, 62, 92, 96, 66, 71, 93, 73, 82, 110, 113, 86 engine upgrade, 53 mutations, 0 failed each; 101 landing
reuse fails as it does at 56d8860e (OPEN.md item 8). Suite 73 failed one row (priority/missing-priority) on the first build, which drives
Cycles._assign with a stand-in object; fixed by calling the shared checks through the class, then green.
Template sync: pass. The VELDO-0132 and VELDO-0241 mutation anchors in the changed files are each still unique.

## Open

See OPEN.md.
