---
schema: veldo.spec/v1
id: VELDO-0264
title: A call step runs another stored workflow revision as a unit of reuse, an each step fans out one bounded branch per item of a list and a Join waits for all of them, and no call, item or branch can go around the owner's approval
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0057, VELDO-0068, VELDO-0132, VELDO-0141, VELDO-0154, VELDO-0241, VELDO-0247, VELDO-0253, VELDO-0262, VELDO-0263]
placement: [contracts, engine, loop]
protected_paths: []
footprint:
  - ".veldo/control_workflow*.py"
  - "engine/.veldo/control_workflow*.py"
  - "packs/*/.veldo/control_workflow*.py"
  - ".veldo/control_graph_steps.py"
  - "engine/.veldo/control_graph_steps.py"
  - "packs/*/.veldo/control_graph_steps.py"
  - ".veldo/control_service.py"
  - "engine/.veldo/control_service.py"
  - ".veldo/control_store*.py"
  - "engine/.veldo/control_store*.py"
  - ".veldo/control_event_vocabulary.py"
  - "engine/.veldo/control_event_vocabulary.py"
  - ".veldo/init_scaffold.py"
  - "engine/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0264_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0264-a-step-calls-a-stored-workflow-and-a-step-fans-out-over-a-list.md"
  - "specs/index.md"
  - "proof/VELDO-0264/**"
behavior_bearing: true
observability:
  logs: >
    A refused save records every named problem with the caller's node, the called workflow id and
    version and, for a problem found inside the called revision, the path of call nodes leading to it.
    Every call records the unit, the caller's revision {id, version, digest}, the call node, the called
    revision {id, version, digest}, the child cycle it started, the inputs it passed by field name (a
    private field as its digest), and the named results it took back. Every each step records the list
    field, the item count, the declared most, the concurrency, each item's index and digest, the child
    cycle of each item, each item's outcome, and the join's completion with the outcome of every item.
  metrics: >
    Counted from the journal, never kept as a second record: calls per called revision, child cycles
    per each step, item count distribution, items failed per each step, and how long a join waited
    after its first item finished. VELDO-0265 reads these from the same events.
  traces: >
    A child cycle joins to its parent cycle, the call or each node, the item index where there is one,
    and both revisions, so a unit's trace shows each called workflow and each item as a child of the
    step that started it, to any depth the ceiling allows.
  error_taxonomy: >
    New save problems, each with the node and the call path named: call_target_unknown,
    call_target_not_accepted, call_inputs_invalid, call_outputs_invalid, call_recursion,
    call_depth_exceeded, each_invalid, each_most_out_of_bounds, each_concurrency_out_of_bounds,
    each_body_not_allowed, and VELDO-0241's and VELDO-0247's approval and block problems reported with
    the call path. New run failures: list_too_long (more items than the declared most; nothing is cut),
    list_item_invalid, call_failed and items_failed, each classified invalid_input or
    unavailable_service as stated in the Notes, so no caller's classification moves.
acceptance_criteria:
  - id: AC1
    text: >
      A call step is closed data and the save check sees through it. A `call` node's config is exactly
      {workflow, version, inputs, outputs}: workflow and version name an accepted revision exactly (no
      head, no latest, no range); inputs map each input the called revision declares (a new optional
      `inputs` section of a definition, typed like VELDO-0247's fields) to a field the caller declares,
      types equal, every required input mapped; outputs map named results the called revision declares
      to names in the caller, which the caller's checks may then read as node results. The save check
      composes the caller with every revision it calls, to any depth up to CALL_DEPTH_CEILING (declared
      beside STEP_CEILING), into one composed graph whose node ids carry the call path, and runs
      VELDO-0241's approval walk and VELDO-0247's block rules on that composed graph, so an outward step
      inside a called revision needs the owner's approval on every path through the pair, and a
      subject-changing step in the caller after that approval is refused as it would be inline. A call
      that leads back to any revision on its own call path, directly or through others, is refused.
      Saving a new revision of a called workflow changes no caller: a caller names its version. Rows: a
      call to an unknown or unaccepted revision, a missing required input, a type mismatch, an output
      the callee does not declare, a self call, a call cycle of three, a chain one deeper than the
      ceiling, a caller whose build follows a callee's approval and precedes the callee's land, and a
      callee land reachable with no approval anywhere in the pair are each refused with the named
      problem and the call path, and no revision is written; the same definitions within the rules are
      accepted.
    falsified_by: >
      Two registered mutations, each with a green baseline: (1) the approval walk treats a call node as
      an opaque step that changes nothing: the callee-land-without-approval row goes red; (2) recursion
      is checked only for a direct self call: the call-cycle-of-three row goes red.
  - id: AC2
    text: >
      A call runs the called revision as a child cycle of the same unit, pinned like every revision.
      When a unit first reaches a call node, the called revision's {id, version, digest} is recorded in
      the unit's record under the call path and every later step reads that record (VELDO-0241 AC3); a
      new revision saved or bound mid-unit changes neither the caller nor the callee for that unit. The
      child cycle runs on the step runner (VELDO-0262) with its own step budget from the called
      revision, so a caller's budget counts the call as one step and a deep call cannot exhaust it;
      the composed graph's digest is recorded with the unit so a replay runs exactly what ran. The
      child receives only the mapped inputs and returns only the declared outputs; anything else it
      produces stays in its own record. The child's steps are journaled as the child's, linked to the
      parent cycle and call node, and the canvas run view (VELDO-0246 AC4) opens the child from the
      call node. A child that fails fails the call node with call_failed naming the child's failed
      step, and VELDO-0263's policy and failed port of the call node decide what follows; a retry of a
      call whose child recorded an outside write is refused as VELDO-0263 AC2 refuses it. Rows: the
      pinned callee survives a mid-unit save of a newer callee; an unmapped child result is not visible
      to the caller's check; a child failure reaches the call node's failed port; a replay from the
      recorded composed digest gives the same step sequence.
    falsified_by: >
      Two registered mutations, each with a green baseline: (1) the child reads the callee's head: the
      mid-unit callee row goes red; (2) every child result is merged into the caller: the
      unmapped-result row goes red.
  - id: AC3
    text: >
      An each step fans out one branch per item of a list known only at run time, bounded, and a Join
      waits for all of them (the variant VELDO-0247 set aside). VELDO-0247's field types gain `list`,
      a list of one scalar type with a declared most. An `each` node's config is exactly {over, most,
      concurrency, body}: over a declared list field; most an integer from 1 to EACH_CEILING; concurrency
      from 1 to FAN_OUT_CEILING, the most item branches dispatched at once; body a call config (AC1)
      whose called revision receives the item as a declared input. EACH_CEILING is a declared bound
      sized for the work, not today's load, and the save check refuses a most above it. The each node's
      `done` port leads to exactly one join that names it, as VELDO-0247's join does for a fan-out. At
      run, a list longer than most fails the step with list_too_long and runs no item (nothing is
      silently cut); an empty list completes the join at once with no items; each item runs as a child
      cycle in list order, identified by its index and the digest of its value, at most `concurrency`
      at a time, the next starting as one finishes; the join completes only when every item has a
      final outcome, and then once. An item's failure is decided by the body's own failure policy; an
      item that still fails makes the each step fail with items_failed naming every failed index after
      all items finish, and VELDO-0263 decides what follows. Rows: a list of 5 with concurrency 2
      dispatches two items, then the third only when one finishes; the join has not run with four
      items done and runs once with five; a list of most plus one fails with list_too_long and
      dispatches nothing; an empty list passes the join; one failed item of five gives items_failed
      naming that index after the other four finish; the same list in the same order gives the same
      item identities and child cycle order.
    falsified_by: >
      Three registered mutations, each with a green baseline: (1) the join completes on the first item
      to finish: the join-waits-for-all row goes red; (2) a list longer than most is cut to most: the
      list-too-long row goes red; (3) the concurrency bound is ignored: the dispatch-order row goes red.
  - id: AC4
    text: >
      No call, item or branch can go around the owner's approval. The body of an each step, composed
      to its full depth, may contain no owner_approval and no node of a kind marked outward or
      writes_outside (VELDO-0263); such a body is refused at save with each_body_not_allowed, so an
      approval sits before the each with no subject-changing step in any item, or after the join over
      the combined subject, exactly as VELDO-0247 AC4 rules for branches. An each inside a parallel
      branch or inside another each body is refused, as nested fan-outs are in VELDO-0247. At run,
      control_workflow_cycle re-judges every step a child cycle reports against the child's pinned
      revision and the composed graph, so a forged runner answer that leads an item or a callee to an
      outward step, to a node of another revision, or out of its child cycle is refused before anything
      follows. An approval inside a called revision binds to the exact subject that reaches it
      (VELDO-0057) and settles only through the owner's ordinary decision (VELDO-0068); no caller, item
      or child result can grant it. Rows: a body that lands, a body that calls a revision whose
      approval precedes its publish, a land after the join reached with no approval after the join,
      an each nested in an each, and an each inside a parallel branch are each refused at save; a
      forged child answer naming the caller's land node is refused at run; the same definitions with
      the approval after the join are accepted and run.
    falsified_by: >
      Two registered mutations, each with a green baseline: (1) the body check composes only one call
      level: the body-calls-a-publishing-revision row goes red; (2) the cycle accepts a child's
      reported step without checking it against the child's pinned revision: the forged-child-answer
      row goes red. VELDO-0247's branch-around-approval falsifier still reds its row.
required_evidence: [unit, integration]
rollback: >
  Revert the commits. call, each and the list field type are unregistered, so a stored revision that
  uses them no longer validates and a unit bound to it stops at its next station with missing_workflow
  and is put to the owner; a running child cycle is stopped through the existing stop path and its unit
  is put to the owner. Stored revisions, unit records, child cycle records and journal entries stay as
  written. No automatic rollback, retry or recovery is authorized.
---

## Intent

Default definitions for code, document, media, deploy and social post repeat the same pieces: the
review loop with its bounded re-review, render then review then approve, the spend checklist before a
paid step. When the owner improves one, every copy has to change. Separately, a social post for five
channels, a document in four locales or an upgrade across six repositories needs one branch per item
of a list known only when the unit runs. This adds a call step that runs another stored workflow
revision as a unit of reuse, and an each step that fans out one bounded branch per list item with a
Join that waits for all of them, and keeps the owner's approval impossible to route around in any call,
item or branch.

## Context

Owner, Telegram 39631 to 39633 (2026-11-07): on the comparison of Veldo with n8n, asked for tickets for
step failure policy, sub-workflows and fan-out, and run insights first. This is the second; it is gap 4
of research/veldo-n8n-gaps-2026-11-07.md in the owner's research folder.

What is there today. VELDO-0132 stores revisions as closed data; VELDO-0241 binds a unit to one pinned
revision and walks every path for the approval; VELDO-0247 adds checks, a fixed fan-out of at most
FAN_OUT_CEILING (8) branches and a Join, and its Out of scope names "fan-out over a list known only at
run time (one branch per item ... with a variable width)" as a later spec on its shape. VELDO-0253 makes
every saved revision a commit in the installation repository, so a called revision is as durable and
reviewable as its caller. VELDO-0262 replaces LangGraph with Veldo's own step runner; this spec is
written against it.

Design decisions.
- A call names an exact accepted version. A caller never follows a callee's head, so improving a shared
  piece is a deliberate new caller revision, visible in history, and every unit can be replayed.
- A call runs as a child cycle with its own budget, not inlined into the caller's cycle. The save check
  composes the graphs for the approval walk; the runner runs each revision separately. That keeps
  STEP_CEILING meaningful per revision, keeps the runner's one exchange per cycle, and gives each child
  its own record and trace.
- Each item is a child cycle of the each step's body, which is a call. Reuse and fan-out share one
  mechanism, and an item's own failure policy (VELDO-0263) is the body's.
- Width is bounded twice: by `most`, declared per step under EACH_CEILING and checked against the real
  list (too long fails the step, nothing is cut), and by `concurrency` under FAN_OUT_CEILING, so a long
  list queues rather than exhausting workers or accounts. Dispatch still goes through the Line and the
  reservations, so the factory's account limits govern how many run at once.
- No approval or outward step inside an item, as VELDO-0247 rules for branches. The owner approves the
  combined result after the join, or approves the subject before the each when no item changes it.

Dependency on landing-b, VELDO-0262 and VELDO-0263. VELDO-0241 and VELDO-0247 as built are in the
landing-b batch, not on main at afa292f0; VELDO-0262 is ready and built after landing-b lands; this spec
uses VELDO-0263's failed port, policy and writes_outside mark and is built after it.

## Out of scope

A called workflow given to a model as a tool. Fan-out over a list inside another fan-out, and an each
inside a parallel branch (refused here, a later spec if needed). A join that completes on the first or
on some items. Lists of records rather than scalars, and fields computed from other fields. A called
revision from another installation. Canvas drawing of call and each nodes and of child runs, which
belongs to VELDO-0246 and reads this spec's records and named problems.

## What the reviewer judges

- Normal use: the owner builds "review loop" once and calls it from code, document and social post;
  builds "post to one channel" and runs it with each over the five channels the subject lists, two at a
  time, then approves the five drafts together after the join.
- Threat model: a callee that publishes with no approval anywhere in the pair; a caller that changes
  the subject after a callee's approval; recursion through several revisions; a callee head swapped
  under a running unit; a list longer than declared, silently cut or allowed to exhaust workers; a join
  that fires early; an item that approves, lands or publishes; a forged child answer that steps into
  the caller or another revision.
- The composed approval walk is VELDO-0241's and VELDO-0247's walk, reused on a composed graph, not a
  second walk.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962).

## Notes

Classification of the new run failures: list_too_long, list_item_invalid and call_failed caused by an
input or output that does not match its declaration are invalid_input; call_failed and items_failed
caused by a child's own failure take the child's class.

## History

2026-11-07: drafted under owner Telegram 39631 to 39633 (the n8n comparison and its recommendation:
tickets for step failure policy, sub-workflows and fan-out, and run insights first), from main at
afa292f0, VELDO-0241 and VELDO-0247 as written in the landing-b batch, and VELDO-0262 as ready. Built
after landing-b lands, after VELDO-0262 and after VELDO-0263. Standalone; no plan work item.
