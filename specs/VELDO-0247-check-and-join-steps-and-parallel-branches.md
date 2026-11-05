---
schema: veldo.spec/v1
id: VELDO-0247
title: A Check step routes the work by a plain rule over declared fields with a required otherwise path, parallel branches from one step run at the same time and a Join step waits for all of them, every fan-out is bounded, and no branch can go around the owner's approval
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0132, VELDO-0241]
placement: [contracts, engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_workflow*.py"
  - ".veldo/control_workflow*.py"
  - "packs/*/.veldo/control_workflow*.py"
  - "engine/.veldo/control_graph_langgraph.py"
  - ".veldo/control_graph_langgraph.py"
  - "packs/*/.veldo/control_graph_langgraph.py"
  - "engine/.veldo/control_service.py"
  - ".veldo/control_service.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0247_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0247-check-and-join-steps-and-parallel-branches.md"
  - "specs/index.md"
  - "proof/VELDO-0247/*"
behavior_bearing: true
observability:
  logs: >
    A refused save records every named problem, among them the check node, the field and the rule at fault.
    Every check a run passes records the unit, the workflow id, version and digest, the node, the branch
    taken, the rule that matched (or otherwise), and for each condition of that rule and of every earlier
    rule the field, the comparison, the literal value and the observed value. Every fan-out records the
    node, the branches started with their first nodes and the LangGraph step they started in; every join
    records each input's arrival and the moment it completed. No secret is logged; an observed value is
    logged only when its declared field is not marked private, otherwise its digest.
  metrics: >
    Count saves refused by problem name, checks run by node and branch (otherwise counted on its own),
    fan-outs by width, branches running at once, joins waiting and their wait time, and branch-decision
    mismatches refused by the cycle.
  traces: >
    Join each check decision and each branch's dispatches, gate observations and results to the unit's one
    recorded revision (VELDO-0241 AC3) and to the fan-out that started the branch and the join that ended it.
  error_taxonomy: >
    Keep VELDO-0132's and VELDO-0241's names. At save: unsupported_configuration:check_without_otherwise:<node>,
    unsupported_configuration:undeclared_field:<node>:<field>, unsupported_configuration:unknown_comparison:<node>:<name>,
    unsupported_configuration:code_like_value:<node>:<rule>, unsupported_configuration:value_type:<node>:<rule>,
    unsupported_configuration:fan_out_too_wide:<node>, unsupported_configuration:join_inputs:<node>,
    unsupported_configuration:branch_escapes_join:<node>, and VELDO-0241's
    invalid_input:missing_owner_approval:<node> and invalid_input:approval_not_last:<node>, which also name
    approval_in_branch:<node> and outward_in_branch:<node>. At run: a declared field with no value or the wrong
    type is invalid_input:field_unsupplied:<field>, never the otherwise path; a branch reported by the runner
    that differs from the cycle's own evaluation is unsupported_workflow:branch_mismatch. None is a completion.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: a Check node's configuration is closed and is checked by definition_problems at save. Set: the
      definition gains an optional `fields` section, each field a name with a type (text, number, yes or no,
      or one of a listed set of choices) and a source (the subject, or a named result of a node that lies on
      every path from the entry to the check); a check's config is exactly an ordered list of named branches,
      each a list of conditions all of which must hold, each condition exactly {field, comparison, value}, and
      a required `otherwise` branch. The field is a declared one; the comparison is one of a fixed set (is, is
      not, less than, at most, more than, at least, contains, is one of), allowed only for the field's type;
      the value is a literal of the field's type (a choice from its list, a number, yes or no, or plain text of
      at most 200 characters made of letters, digits, spaces and . , - _ / : @). The check's ports are its
      branch names plus otherwise, each with exactly one transition. Nothing is ever evaluated, interpolated or
      run: a value is compared as data. Rows: a check without otherwise, a condition on a field the workflow
      does not declare, an unknown comparison, a comparison the field's type does not allow, a value of the
      wrong type, any extra key (expression, code, script, shell, template), and a text value carrying code-like
      characters (a brace, backtick, dollar sign, quote, bracket, parenthesis, semicolon, pipe, angle bracket or
      equals sign) are each refused with the named problem and no revision is written.
    falsified_by: >
      Accept a check whose config has no otherwise branch, or whose value is the text "$(rm -rf .)"; the
      check-configuration refusal row must fail.
  - id: AC2
    text: >
      Claim: a run takes exactly one branch of a check and records which and why. Set: the branches are tried
      in their listed order and the first whose conditions all hold is taken, otherwise is taken when none
      does; a declared field with no supplied value or the wrong type fails the step by name and takes no
      branch. The runner reports the branch with the matched rule and the observed values; control_workflow_cycle
      re-evaluates the same rule on the same supplied values against the unit's recorded revision and refuses
      any difference before anything follows, so the runner never chooses the route. The unit's record and the
      log hold the node, branch, rule and every condition with its observed value, and the canvas run view
      (VELDO-0246) reads that record. Rows: on fixtures covering each branch, otherwise, a missing field and a
      wrong type, exactly one branch's next node is offered and the recorded reason names the deciding rule.
    falsified_by: >
      Let the cycle accept the branch the runner reports without re-evaluating the rule; the forged-branch row,
      whose runner names a branch the rule does not match, must fail.
  - id: AC3
    text: >
      Claim: a fan-out runs its branches at the same time on the real pinned LangGraph runtime and a Join
      completes only when all its inputs have, within a bound on width. Set: a port may lead to several
      transitions, which makes that step a fan-out of at most FAN_OUT_CEILING (8) branches; every branch
      reaches the one Join node that names exactly those branches as its inputs, no path leaves a branch except
      through that join, a bounded loop stays inside one branch, and fan-outs inside a branch are refused in
      this spec. The production runner (control_graph_langgraph.py) starts the branches through LangGraph's
      parallel edges or Send in one superstep, keeps each branch's position and results in its own state with
      reducers so no branch overwrites another, and the join node runs only when every input has arrived; the
      Line dispatches the branches' workers without waiting for one another, and the cycle's step budget
      counts every node of every branch. Rows: in a real LangGraph run two assignment branches are dispatched
      before either result returns and their first nodes share one superstep; with one result in, the join
      has not run and the cycle stays suspended; with both in, it runs once; a fan-out of 9 is refused at save.
    falsified_by: >
      Make the join run when its first input arrives; the join-waits-for-all row must fail.
  - id: AC4
    text: >
      Claim: VELDO-0241's approval rule holds on every path through checks, branches and joins and is checked
      at save. Set: the save check walks every path from the entry, taking each branch of every check
      including otherwise; a fan-out and its join count as one block whose steps all precede the join, so a
      subject-changing step in any branch is before whatever follows the join. An owner_approval or an outward
      step (land, deliver, publish, deploy) inside a parallel branch is refused, so the approval sits before
      the fan-out, with no subject-changing step in any branch, or after the join. A check may sit after the
      approval because it changes nothing, but every one of its branches is held to the same rule. Rows: a
      check branch that reaches land around the approval, a check after the approval whose otherwise branch
      leads to a build then land, an approval inside one parallel branch with a build in the other, and a
      land inside a branch are each refused with VELDO-0241's named problem and no revision is written; the
      same definitions with the approval moved after the join or the check are accepted.
    falsified_by: >
      Accept a definition whose check routes its otherwise branch straight to land while its named branch
      passes the owner_approval; the branch-around-approval refusal row must fail.
required_evidence: [unit, integration]
rollback: >
  Revert the change; check and join are unregistered and a port may again lead to one transition only, so a
  definition that uses them no longer validates and a unit bound to it stops at its next station with
  missing_workflow and is put to the owner. Definitions stay in the installation repository, and recorded
  revisions and decisions stay in the store; a later installation commit that still holds a definition
  using check or join is refused as a whole (VELDO-0253 AC1) until that file is changed. No automatic
  rollback, retry or recovery is authorized.
---

## Intent

Today a workflow branches only on a step's named outcome (approved, declined, done). The owner asked what
happens when steps are conditional, not just next, next. This adds two step kinds and one shape: a Check
step that routes the work by a rule written in plain words over fields the workflow declares, parallel
branches that start from one step and run at the same time, and a Join step that waits for all of them.
Every loop and fan-out stays bounded, and the owner's approval before anything leaves the factory still
cannot be routed around.

## Context

The owner (2026-11-04), on the canvas design (VELDO-0246): "what if steps are conditional, not
just next next?" Answered and agreed the same day: branching on a named outcome already exists; a Check step
routes the work by a rule set in plain words over declared fields (field, comparison, value; named branches
plus a required otherwise path; never code, shell or expressions); parallel branches from one step run at
the same time and a Join step waits for all of them; every loop and fan-out is bounded.

VELDO-0132 stores definitions as plain data with registered step kinds (STEP_KINDS in
.veldo/control_workflow.py), one transition per port, bounded loops through `max`, and runs one pinned
revision per cycle on LangGraph through control_workflow_langgraph.py spliced into the production runner
control_graph_langgraph.py, one step per exchange. VELDO-0241 makes a unit's process such a revision and
adds the save-time approval rule (its AC2). Veldo's pinned LangGraph runtime has conditional edges,
parallel fan-out with a join that waits for all its inputs, and Send; this spec uses them rather than
building a scheduler of its own.

## Out of scope

Fan-out over a list known only at run time (one branch per item through Send with a variable width), and
fan-outs nested inside a branch; both are later specs on this shape. A join that completes on the first or
on some of its inputs. Fields computed from other fields. Any field source other than the subject and a
node's named result. The canvas palette entries, inspector and drawing of checks, branches and joins belong
to VELDO-0246, which reads the named problems and the recorded decisions this spec produces.

## What the reviewer judges

- Normal use: the owner adds a Check after review, "if the change touches more than 20 files, send it to a
  second reviewer, otherwise go on", picks the field from a list, the comparison from a list and types the
  number; or splits a document into a copy branch and an image branch that run at the same time and meet at
  a Join before review and the owner's approval. The run view shows which branch a check took and the rule that
  decided it, and which branches are still running.
- Threat model: a check whose value smuggles code, a template or a shell line; a field that is not declared
  or comes from a step that may not have run; a check with no otherwise, so a run can fall through with no
  route; a runner that names a branch the rule does not pick; branches that run one after another while
  claiming to be parallel; a join that fires before every branch is done; a fan-out wide enough to exhaust
  workers; and any check branch, parallel branch or join that reaches an outward step without the owner's
  approval or with a subject-changing step after it.
- Out of review scope (filed, not blocking): unlikely edge cases (the owner's standing ruling); recovery of a fan-out
  after a crash between two branch steps beyond what the store records (Release 2 checkpointing).

## Notes

The comparison set and the value pattern are closed lists in STEP_KINDS' neighbour tables, so the canvas
offers exactly them and nothing else; a new comparison is a spec change, not a definition change. A
condition's value is never a field name, so no rule compares two fields; that keeps every rule readable as
one plain sentence ("review score is at least 4").

Branch state: each branch carries its own position and results under its branch name, merged by reducers in
the runner's State, and the cycle's resume value becomes a set of positions keyed by branch. The one step
per exchange rule of VELDO-0132 becomes one superstep per exchange: every branch with what it needs runs in
the same superstep, and the domain side still sees and may refuse every transition before the next runs.
FAN_OUT_CEILING (8) sits beside STEP_CEILING (64); the step budget counts every branch's nodes, so a wide
fan-out cannot run past the cycle budget.

The approval walk of VELDO-0241 is reused, not copied: it gains two rules (each check branch is a path; a
fan-out to its join is one block) and the two in-branch refusals, so later outward kinds inherit the rule.

## History

2026-11-04: new draft under owner Telegram 39079 (conditional steps, parallel branches and a join, every
loop and fan-out bounded; agreed), on the canvas design of VELDO-0246 and the process-as-workflow drafts
VELDO-0241 to VELDO-0245 (Telegram 39069 to 39071). Standalone; no plan work item.

2026-11-04: approved by the owner, Telegram 39096 ("Yes covers both", to 39089-39092 asking approval of VELDO-0236 to VELDO-0249, the PLAN-0019 amendment and the connectors plan). Status ready.

2026-11-04: amended under the plan consistency review (owner Telegram 39145; research/veldo-plan-consistency-review-2026-11-04.md, findings A23, E4, E7) and the lead's rulings (research/veldo-plan-rulings-2026-11-04.md, R1): the rollback keeps definitions in the installation repository and says a later commit holding check or join is refused until changed; the LangGraph version is the pinned runtime. Status stays ready.

2026-11-05: the review amendments and new tickets approved by the owner, Telegram 39157 ("Yes", to 39156).
