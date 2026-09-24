# VELDO-0132 proof

Versioned workflow definitions consumed by LangGraph, PLAN-0019 revision 3 W95 (Release 1 stage 4).
Branch `build-veldo-0132`, built on 5a5dfcd with origin/main merged (36fd201). The specification
stays **ready**. This is implementation evidence, not independent review, owner approval or a
full-gate result; the lead runs `bash scripts/verify.sh`.

## What landed

**`.veldo/control_workflow.py`** (standard library only). A definition is plain JSON data:
`schema`, `id`, `entry`, `terminal`, `nodes` (`{kind, config}` of a registered step kind:
grooming, owner_wait, assignment, result_handling), `transitions` (`{id, from, port, to, max?}`),
`references` (`roles` and `tools`, each `{id, version, digest}` of an accepted configuration
entity) and `budget` (`{steps}`, at most 64). `definition_problems()` names every problem.
`Workflows.save()` is the store command `save_workflow_revision`, the only writer of workflow
revisions and heads (`control_store.declare_owners`). Its transition judges the editor (an active
person member holding `project_owner` or `technical_authority`, scoped to the repository), requires
`base` to be the current head, resolves every reference in the store, and writes a new immutable
revision beside a separately digested canvas layout. `Workflows.load()` reads a revision back and
checks its entity and definition digests. Neither loads the graph adapter, the runner or any
dispatcher.

**`.veldo/control_workflow_cycle.py`**. `Cycles.start()` commits `record_workflow_cycle`, whose
transition reads the head inside the store transaction and pins that exact revision
(`{id, version, digest, revision, entity_digest}`) with the subject unit and an accepted VELDO-0035
snapshot. Every later record must keep all three. Each exchange runs the production runner with the
step kinds and exactly one registration spliced in: the bound definition's canonical text, never
the layout. It runs on the actual LangGraph through the VELDO-0043 adapter, with the VELDO-0045
runtime activated first. The service runs **one step per exchange** and judges each one before the
next runs:

- the budget and loop bounds;
- the executed digest the runner reports, compared with the binding;
- the step taken, which must be a transition of the bound revision;
- at an assignment, the role configuration (current at its referenced version and digest, its
  principal an active member admitted at `assignment_acceptance`, scoped to the repository), the
  tool references, and the Gate's `selection` decision;
- the worker result, which must be an accepted `proof_bundle` for the unit;
- at the terminal, completion evidence that cites that result and nothing else.

A proposal is recorded as pending for its owning authority. Completion is only ever
`Gate.completion` over stored receipts.

**`.veldo/control_workflow_langgraph.py`** is the step-kind block spliced into the runner. Nothing
imports it. All three have byte-identical `engine/.veldo` copies.

## Rows (suite `65_veldo_0132_workflow`, 15 rows: 10 criterion rows and 5 `ran/` rows, 41 assertions with the preamble)

The suite uses a real SQLite store with OpenSSH journal signatures, a real Git workspace and an
accepted VELDO-0035 snapshot, the eligibility Gate (`workspace=`), and the locked LangGraph 1.2.12
staged into a temporary directory. A row that checks the account's stage confirms it is untouched.

| AC | Row | What it observes |
|---|---|---|
| AC1 | `workflow/validation` | 23 bad documents, each refused through save with its own code: two dangling edges, an unknown step kind, an unknown config field, an unknown port, a missing transition, a duplicate, an undeclared, unresolved, stale or wrong-kind reference, an unused reference, an unbounded cycle, a bound of 0, an unreachable node, a terminal mismatch, an unknown entry, a reserved node id, a budget of 65, a wrong schema, an unknown field, a float, and a layout naming no node. Nothing is written. |
| AC1 | `workflow/authorized-editor` | An unknown principal (`unauthenticated:editor`), and a person without a role, an agent_run, an owner of another repository and a revoked owner (`missing_authority:editor`) write nothing. A technical_authority saves. |
| AC1 | `workflow/revisions-immutable` | Version 2 leaves version 1's entity byte-identical, and version 1 still loads. A stale base is refused `stale_version`, a generic overwrite `entity_owned`. History is [1, 2]. `previous` names version 1. |
| AC3 | `workflow/canvas-round-trip` | Definition and layout load back canonically equal. A layout-only edit is a new revision with the same definition digest. Both runners register exactly the canonical definition text, and no layout value appears in either. |
| AC3 | `workflow/edit-without-execution` | A child process with an audit hook and an in-process signer saves an edge and loads it. It records 0 process launches, 0 network events, no graph, runtime, dispatch or launch module loaded, one journal record (`save_workflow_revision`, revision and head only), and unchanged reservations and effects. |
| AC2 | `workflow/pinned-revision` | Cycle A binds delivery 1 and waits for the owner while delivery 2 is saved. It then completes grooming, owner wait, assignment and result handling. Every step lies in revision 1's transitions and every executed digest equals the stored revision 1 digest. Cycle B, started later, binds revision 2 and runs its new node. |
| AC2 | `workflow/actual-langgraph` | Every step, proposal and cancel of cycles A, B and C is labelled langgraph 1.2.12. Each staged runner starts with the production runner and registers exactly one stored revision, and all six revisions are represented. Cycle C is canceled through the graph. The account stage is unchanged. |
| AC4 | `workflow/ordinary-authorization` | Each case first runs actual graph steps, then is refused by name with no proposal and no pending work: a blocked unit (`blocked:blocker-9604`, the Gate), an intruder role whose principal is a service (`missing_authority:role/intruder`), a spent budget (`budget_exceeded:steps` at 4), a loop past its bound (`budget_exceeded:loop/t-decline`) and an asserted completion (`missing_evidence:completion`). A second visit to an assignment waits for its own worker after a fresh Gate decision. |
| AC4 | `workflow/no-workflow-authority` | Across every cycle, every non-workflow entity is what the suite itself wrote. Every other journal record is a workflow record. No unit is complete or changed state, the spec files, HEAD and working tree are unchanged, and there are no reservations or effects, while cycle A's completion proposal is recorded. |
| (obs.) | `workflow/observations` | Each event carries operation, domain, repository, workflow, actor and snapshot. Each refusal carries its code and one of the seven taxonomy classes. `status()` counts match the events, the pending work is exactly the two waiting cycles, and no key path or key text is present. |

`observations.json` (from `drive.py`) holds one unmutated run.

## Red at the pre-change code

`red.py 5a5dfcd` writes `red-5a5dfcd.json`. At 5a5dfcd none of the three modules exists: a
workflow could only be a generic in-place `upsert_entity`, and a cycle could only run the
unmodified runner, which registers no workflow. The three production anchors point at `prefix/`,
marked stand-ins that give the suite's names exactly that behaviour. Every other installed module
and runtime asset (162 files) is written from `git show 5a5dfcd`. **All 10 criterion rows fail by
assertion, all 5 `ran/` rows pass, and nothing raised.** Observed: all 23 bad documents and all 5
unauthorized editors were accepted, and every cycle answered `unsupported_workflow`.

One defect was found during the build. It was recorded red first (`67ab485`: a second visit to an
assignment reused the earlier worker result and skipped its checks) and then fixed (`b2021c6`).

## Mutations (finding 132, 26 registered in `scripts/check_teeth_mutations.py`)

`mutations.py` drives them and writes `mutations.json`, with each exact edit in `mutations/`. Every
mutation reds its named row by assertion, and **no `ran/` row goes red**. The unmutated control is
green with 41 assertions. Declared falsifiers:

- AC1: `workflow-dangling-edge-accepted`
- AC2: `workflow-cycle-reads-canvas-head`
- AC3: `workflow-save-launches-worker`
- AC4: `workflow-terminal-ships-spec`

| Row | Mutations |
|---|---|
| validation | dangling-edge-accepted, unbounded-cycle-accepted, references-unresolved |
| authorized-editor | editor-unchecked, editor-role-ignored |
| revisions-immutable | revision-kinds-unowned, stale-base-accepted, load-returns-head |
| canvas-round-trip | layout-reaches-runner, layout-dropped |
| edit-without-execution | save-launches-worker, load-activates-runtime |
| pinned-revision | cycle-reads-canvas-head, cycle-binds-first-revision |
| actual-langgraph | runner-unregistered, cancel-without-graph |
| ordinary-authorization | role-unchecked, gate-not-asked, budget-unchecked, loop-bound-unchecked, completion-unvalidated |
| no-workflow-authority | terminal-ships-spec, terminal-writes-unit |
| observations | cycle-refusal-unobserved, save-refusal-unclassified, pending-unlisted |

## Costs

- **Suite 65:** 13.6 to 15.6 s inside selftest at a load average below 3, against the 60 s limit.
  About 15 s of that is roughly 45 LangGraph exchanges at about 0.35 s each; everything else takes
  about 0.3 s.
- **Mutation driver:** finding 132 with `--jobs 4` takes 104 to 118 s for 26 mutations.
- **Gate:** the gate's mutation stage will run these 26 at about 15 s each, roughly 400 worker
  seconds. That stage was not run here.

## Not done here, stated

- **API and editor.** AC3's API and editor legs are VELDO-0130 and VELDO-0131. Here AC3 runs
  through the `save`/`load` interface they call.
- **Scaffold.** The scaffold lays the three modules (the footprint names `init_scaffold.py`). No
  validator loads them.
- **Gate registration.** The cycle's `selection` decision is a proposal-time check, not a
  registered floor entry. `control_eligibility.REGISTRATIONS` is outside this footprint, and the
  dispatcher's registered `build` decision still governs any launch.
- **Role and tool configuration.** Their schema and writer are VELDO-0127's. This spec resolves
  references by `{id, version, digest}` against the kinds `role_configuration` and
  `tool_configuration`, and reads only a role's `principal`.
- **Fixture records.** The suite writes admissions, blockers and the worker's `proof_bundle` with
  the generic command; their services are not re-proved.
- **Step kinds.** They are deterministic routers over plain supplied results. Model-driven
  grooming is VELDO-0088's.
- **Recovery.** A failed exchange refuses the cycle, which is never retried. Checkpoint recovery is
  Release 2.
- **Not run:** `verify.sh` and the Mac.
