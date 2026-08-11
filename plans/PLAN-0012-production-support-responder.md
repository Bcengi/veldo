---
schema: veldo.plan/v1
id: PLAN-0012
title: Production support responder - diagnosis from artifacts by an agent that physically cannot write, remediation as a proposal artifact executed only through a whitelisted, laddered, two-key organ, and every incident reconciled back into the loop
kind: mvp
status: released
revision: 2
owner: dmitry
approved_by: dmitry
approved_at: 2026-07-22
risk: standard

outcomes:
  - id: O1
    becomes_true: >
      Privilege separation is physics, not promise. The investigating responder
      runs on credentials that cannot write: read-only roles against read
      replicas and log, metric, and trace stores, never a primary; query rate
      and row limits apply; PII is redacted before anything enters the agent's
      context; and every query it runs lands in a full audit log. The credential
      makes the wrong write impossible; nothing depends on the agent agreeing to
      behave.
    measure: >
      Negative tests on a fake evidence plane: a write attempted through the
      responder's access fails at the credential seam, not at a policy prompt;
      every query issued during a seeded investigation appears in the audit log;
      seeded PII never appears in the responder's context transcript.
  - id: O2
    becomes_true: >
      Diagnosis and execution are separate organs. The responder's output is a
      remediation proposal artifact (diagnosis, evidence with citations,
      proposed action, risk class, reversibility analysis, rollback plan); it
      cannot execute anything because its harness contains no execution
      capability at all. Execution is a separate privileged path that runs only
      pre-vetted, parameterized runbook actions reviewed like code; free-form
      production commands do not exist in the machine path.
    measure: >
      Structural conformance: the responder toolset enumerates no execution
      tool; a proposal missing any required element is invalid at contract
      time; the executor refuses any action not in the whitelist and any
      parameter outside its declared validation, with the refusal named.
  - id: O3
    becomes_true: >
      Autonomy is a ladder with the floor at read-only, and the dangerous rungs
      are multi-key. Every deployment starts at L0 (investigate only); L1
      proposes; L2 executes whitelisted, provably-reversible actions only after
      an explicit human confirmation bound to the proposal; L3, if ever enabled,
      auto-executes the lowest risk class alone, and never enabling it is a
      legitimate configured state. Anything irreversible or data-mutating takes
      two keys: recorded human authorization plus an independent fresh-context
      confirmation that the diagnosis supports the action. A kill switch halts
      the responder and executor instantly; action budgets, timeouts, and
      canary-first execution stand guard on every run.
    measure: >
      Conformance on a fake system: below-floor execution refuses; each missing
      key alone refuses and both keys bound to the proposal digest execute; a
      tripped kill switch refuses everything; an exhausted budget or timeout
      refuses; a canary-declared action demonstrably runs its canary first.
  - id: O4
    becomes_true: >
      Diagnosis comes from artifacts, not memory. The responder queries the
      intent corpus the method already produces - what specification governs
      this behavior, what changed here recently, what did its proof cover, and
      where the affected module sits in the declared shape when an architecture
      contract exists - so a party that never wrote the code reaches a cited
      diagnosis at machine speed.
    measure: >
      A seeded fake incident is diagnosed offline from the corpus alone: the
      diagnosis cites the governing spec, the implicated change, and its proof,
      with no live system access and no source-diving beyond the corpus, and
      degrades gracefully (spec and git level) when no architecture contract is
      present.
  - id: O5
    becomes_true: >
      An incident is intent arriving from production, handled by the compressed
      loop and closed by reconciliation. The diagnosis is validated by a human,
      the fix flows through the emergency lane, the failure mode becomes new
      acceptance and regression criteria drafted for human promotion, every
      executed remediation is reconciled like any other change, and runbook
      actions self-maintain from real incidents as drafts that only a human
      promotes.
    measure: >
      Conformance over a seeded incident lifecycle: the closed incident leaves
      behind regression criteria and a runbook-action draft in draft status;
      re-running the reconciliation creates no duplicates; the recurrence of the
      same failure signature is detected and reported.
  - id: O6
    becomes_true: >
      Diagnosability is gated and support has numbers. Observability (structured
      logs at decision points, metrics, traces, honest error taxonomies) enters
      acceptance criteria for behavior-bearing changes, because every future
      responder is a stranger; and the metrics derive from recorded events:
      time-to-diagnosis and time-to-restore trending, recurrence rate, a
      diagnosability score (share of incidents resolved from artifacts alone),
      and incidents-per-area joining cost-to-change-per-area on one map where
      PLAN-0011 has shipped.
    measure: >
      The elaboration and validator refuse a behavior-bearing spec that declares
      no observability criteria (vocabulary enforced, unmechanizable parts
      honestly review-lane); the metrics derivation renders all four measures
      from the event stream, joining per-area cost data when present and
      standing down without it.

non_goals:
  - id: NG1
    text: >
      No live production access in this plan. Every item is proven offline
      against fake evidence planes and fake systems; wiring the responder or the
      executor to any real production system is a separate, per-system,
      human-approved enablement act with its own risk review, and it is not part
      of this plan.
  - id: NG2
    text: >
      No free-form production execution path, ever, at any autonomy level or
      approval count. Anything outside the whitelist is human-executed by
      definition; this plan never builds a general shell, and no approval flow
      can conjure one.
  - id: NG3
    text: >
      No quiet daemon. This plan creates no standing service: everything ships
      runnable in-session, the deployment posture is an explicit founder
      decision (D1), and any standing mechanism that decision might later
      choose would be a separate, opt-in, off-by-default, visible component
      with its own approval, in the established supervisor posture.
  - id: NG4
    text: >
      No self-authorization and no self-escalation. The responder never
      approves its own proposal, the executor never raises its own autonomy
      level, and no machine edits the ladder configuration, the whitelist, the
      kill switch, or the budgets; those are human-owned controls.
  - id: NG5
    text: >
      No observability platform. This plan builds no log, metric, or trace
      store; the evidence plane reads declared existing sources through thin
      adapters, and improving a system's instrumentation is that system's work,
      driven by the gated criteria.
  - id: NG6
    text: >
      No rebuild of the loop. The compressed incident path extends the shipped
      emergency lane, event stream, review pattern, and metrics derivation; it
      does not redesign them.

constraints:
  - id: C1
    text: >
      Every item is built through VELDO itself: spec, gate, proof, independent
      fresh-context review; and every safety property ships as a negative test
      that proves the refusal (anti-vacuity). In this plan the refusals are the
      product.
  - id: C2
    text: >
      The safety machinery is the enforcement core: specs touching the
      executor, the whitelist, the two-key rule, the kill switch, or the ladder
      configuration carry a high risk floor with recorded human approval, and
      data-mutating execution paths carry the critical tier. Anything may raise
      a risk class; nothing may lower it.
  - id: C3
    text: >
      Fail closed, degrade down. An unknown action, an unresolvable credential,
      an invalid or stale proposal, a missing key, a tripped kill switch, or an
      exhausted budget refuses; on any doubt the system degrades to a lower
      autonomy level, never a higher one.
  - id: C4
    text: >
      Separation is structural. The responder and the executor share no
      credentials and no code path; the responder's harness contains no
      execution capability; the executor accepts only a whitelist action
      reference with validated parameters bound to a proposal digest, never
      command text.
  - id: C5
    text: >
      Credentials and PII: all credentials are secret references resolved at
      the seam (never raw in a file, prompt, proof, or log; sourcing per D4),
      and PII redaction runs before investigation data enters any agent
      context.
  - id: C6
    text: >
      The canon is engine: every contract, module, check, and skill
      lands in the engine, syncs byte-identical to this repository's instances,
      and stays fully generic; all machinery is runnable in-session.
  - id: C7
    text: >
      Cross-plan joins are soft: behavior-to-area attribution and the
      incidents-per-area map join PLAN-0011's architecture contract and
      cost-to-change data where present and stand down honestly where absent;
      no join is ever faked.

feature_tree:
  - id: F1
    title: The evidence plane - read-only physics, redaction, rate limits, and the query audit log
    outcome_refs: [O1]
  - id: F2
    title: Separate organs - the remediation proposal artifact and whitelisted execution
    outcome_refs: [O2]
  - id: F3
    title: The ladder, the two keys, and the standing safeguards
    outcome_refs: [O3]
  - id: F4
    title: Diagnosis from artifacts - the intent corpus queryable at runtime
    outcome_refs: [O4]
  - id: F5
    title: The compressed loop - incident to regression, runbooks self-maintaining
    outcome_refs: [O5]
  - id: F6
    title: Diagnosability gated and the numbers
    outcome_refs: [O6]
  - id: F7
    title: Release - the engine ships it and the docs are true
    outcome_refs: [O2, O6]

work:
  - item: W1
    spec: WARP-1201
    title: >
      The incident and remediation contracts. veldo.incident/v1 (the incident
      record: signal, affected behavior, timeline, status) and veldo.remedy/v1
      (the proposal artifact: diagnosis, evidence with query citations,
      proposed whitelist action and parameters, risk class, reversibility
      analysis, rollback plan, canary shape), validated structurally with
      unknown kinds rejected at contract time; the event vocabulary gains the
      incident lifecycle. A proposal missing any element is invalid, so the
      two-key path downstream has something exact to bind to.
    feature_refs: [F2, F5]
    depends_on: []
    order: 10
  - item: W2
    spec: WARP-1202
    title: >
      The evidence plane - access physics. Declared read-only sources (logs,
      metrics, traces, read replicas, never a primary) behind thin adapters
      authed by secret references the agent never sees raw, with query rate and
      row limits, PII redaction before anything enters agent context, and a
      full audit log of every query. Proven against a fake plane with the
      negative test at the center: a write attempt fails at the credential
      seam, not at a policy prompt.
    feature_refs: [F1]
    depends_on: []
    order: 15
  - item: W3
    spec: WARP-1203
    title: >
      The intent corpus at runtime. A mechanical query surface over what the
      method already records: behavior to governing spec, change to proof and
      verdict, recent changes per path from git and the event stream, and
      module to contract area when a PLAN-0011 architecture contract exists
      (standing down to spec and git level without one). This is total recall
      without authorship, and it reuses recorded data only; no new
      instrumentation.
    feature_refs: [F4]
    depends_on: []
    order: 20
  - item: W4
    spec: WARP-1204
    title: >
      The responder investigation loop (L0 and L1). An in-session agent brief
      and harness: given an incident record, investigate over the evidence
      plane and the intent corpus and produce a cited diagnosis, and at L1 a
      veldo.remedy/v1 proposal. The harness contains no execution capability at
      all - separation is structural, not instructed. Offline conformance over
      seeded fake incidents, including the graceful-degradation path with no
      architecture contract present.
    feature_refs: [F4, F2]
    depends_on: [WARP-1201, WARP-1202, WARP-1203]
    order: 30
  - item: W5
    spec: WARP-1205
    title: >
      The action whitelist - runbook actions as code. veldo.action/v1:
      pre-vetted, parameterized runbook actions (reference trio per D3: restart
      a service, roll back to a deploy, scale a pool - against fake systems),
      each declaring parameter validation, risk class, reversibility, rollback,
      and canary support, each reviewed through the normal VELDO loop like the
      code it is. The store rejects an action without a recorded review, and
      anything not in the whitelist does not exist to the machine path.
    feature_refs: [F2]
    depends_on: [WARP-1201]
    order: 25
  - item: W6
    spec: WARP-1206
    title: >
      The execution organ - separate, privileged, laddered. An executor on its
      own credentials and code path that runs only whitelisted actions with
      validated parameters bound to a proposal digest, governed by the
      per-system autonomy ladder (floor L0/L1: never executes; L2 whitelisted
      reversible with explicit human confirmation; L3 disabled by default and
      lowest class only if ever enabled per D2), with the standing safeguards:
      kill switch that halts instantly, action budgets, timeouts, and
      canary-first where the action declares it. Ships with the full refusal
      suite as negative tests.
    feature_refs: [F3, F2]
    depends_on: [WARP-1205]
    order: 40
  - item: W7
    spec: WARP-1207
    title: >
      The two-key rule. For any action classed irreversible or data-mutating,
      execution requires a recorded human authorization bound to the proposal
      digest PLUS an independent fresh-context confirmation verdict that the
      diagnosis supports the action and the action does only what it claims -
      the independent-review pattern extended to remediation. Either key alone
      refuses; conformance proves each missing-key path and the both-keys path
      on the fake system.
    feature_refs: [F3]
    depends_on: [WARP-1206]
    order: 50
  - item: W8
    spec: WARP-1208
    title: >
      Incident as intent - the compressed loop and reconciliation. The incident
      record flows the emergency lane: human-validated diagnosis, fix through
      the loop, then reconciliation closes it - the failure mode becomes drafted
      acceptance and regression criteria, the executed remediation is reconciled
      like any change (what was done, what it proved, what regression criteria
      it leaves), recurrence of a known signature is detected, and runbook
      actions self-maintain from real incidents as drafts only a human promotes.
      Idempotent under replay.
    feature_refs: [F5]
    depends_on: [WARP-1204, WARP-1206]
    order: 55
  - item: W9
    spec: WARP-1209
    title: >
      Diagnosability gated. Observability becomes acceptance criteria: a
      criteria vocabulary (structured logs at decision points, metrics, traces,
      honest error taxonomy) that elaboration applies to behavior-bearing
      specs and the validator enforces, with the unmechanizable parts honestly
      labeled review-lane guidance; where a PLAN-0011 architecture contract
      exists, a system's observability rules live in it. The stranger question
      - can this be diagnosed from outside without reading the source - becomes
      a gate concern.
    feature_refs: [F6]
    depends_on: []
    order: 35
  - item: W10
    spec: WARP-1210
    title: >
      The numbers. Extend the metrics derivation and dashboard with the support
      measures from the incident event vocabulary: time-to-diagnosis and
      time-to-restore trending, recurrence rate, diagnosability score (share of
      incidents resolved from artifacts alone), and incidents-per-area joined
      with PLAN-0011's cost-to-change-per-area on the same map where that data
      exists, standing down honestly where it does not.
    feature_refs: [F6]
    depends_on: [WARP-1208]
    order: 60
  - item: W11
    spec: WARP-1211
    title: >
      Release. Land the contracts, the evidence-plane and corpus modules, the
      responder brief, the whitelist and executor, and the checks in the
      canonical engine so /veldo:init lays them down and the packs carry them;
      make the docs true (the method and setup documents gain the production
      support organ as shipped behavior, fully generic, with live enablement
      documented as a separate human act); record capabilities honestly; bump
      the plugin version; mark the plan released once the regression is green.
    feature_refs: [F7]
    depends_on: [WARP-1204, WARP-1207, WARP-1208, WARP-1209, WARP-1210]
    order: 80

regression:
  journeys:
    - id: RJ1
      title: >
        A write attempted through the responder's evidence-plane access fails at
        the credential seam; every query of a seeded investigation is in the
        audit log; seeded PII never reaches agent context.
      activation: {when: after:WARP-1202}
      suite: evidence-plane conformance (fake sources)
    - id: RJ2
      title: >
        A seeded incident yields a cited diagnosis and a valid proposal from a
        responder harness that structurally has no execution tool, with the
        citations resolving to real corpus artifacts.
      activation: {when: after:WARP-1204}
      suite: responder conformance (offline corpus and fake plane)
    - id: RJ3
      title: >
        The refusal suite holds: a non-whitelisted action, an invalid parameter,
        a below-floor autonomy level, a tripped kill switch, an exhausted budget,
        and a timeout each refuse with the reason named, and a canary-declared
        action runs its canary first.
      activation: {when: after:WARP-1206}
      suite: executor negative tests (fake system)
    - id: RJ4
      title: >
        An irreversible or data-mutating action refuses with either key missing
        and executes only with the recorded human authorization and the
        independent confirmation verdict, both bound to the proposal digest.
      activation: {when: after:WARP-1207}
      suite: two-key conformance (fake system)
    - id: RJ5
      title: >
        A closed incident leaves behind drafted regression criteria and a
        runbook-action draft that only a human promotes; replaying the incident
        stream creates no duplicates; a recurring failure signature is detected.
      activation: {when: after:WARP-1208}
      suite: incident lifecycle conformance
    - id: RJ6
      title: >
        The existing gate stays green across every item, and a repository that
        never configures the responder is byte-identically unaffected; nothing
        in the plan installs a daemon, timer, or detached process.
      activation: {when: start}
      suite: scripts/verify.sh

release:
  milestone: >
    VELDO production support responder v1 - diagnosis from artifacts by a
    read-only responder that cannot write and cannot execute, remediation as a
    validated proposal artifact, execution only through a whitelisted, laddered,
    two-key organ with kill switch, budgets, and canary-first, incidents
    reconciled into regression criteria and self-maintaining runbooks, and the
    support numbers on the map - all proven offline against fake systems, with
    live enablement a separate human act.
  mode: continuous
  require_all_work_shipped: true
  require_full_regression: true
  rollback: >
    Nothing standing exists to disable: remove or leave absent the responder
    and ladder configuration and every component stands down; git revert the
    plugin version bump; incident records, proposals, and audit logs are inert
    data and keep their history.
  observation:
    duration: >
      Exercise the full lifecycle on a fake production system across the seeded
      incident classes, then a read-only shadow period on a real system under
      whatever posture D1 selects (L0, investigate and propose only, executor
      disabled), reviewed by the founder before any higher rung or any real
      enablement is considered.

open_decisions: []

resolved_decisions:
  - id: D1
    text: >
      The deployment posture: standing service versus on-demand versus hybrid.
    resolution: >
      Everything ships runnable in-session and no standing service or daemon is
      built; the posture decision gates live enablement, not the build. Decided
      by the founder 2026-07-22 via "use recommendations" (start the build).
    resolved_by: founder via 'use recommendations' (start the build), 2026-07-22
    resolved_at: 2026-07-22
  - id: D2
    text: >
      Where the autonomy lines start, per system and per risk class.
    resolution: >
      Start and stay at L0 (investigate) and L1 (propose) until a later,
      explicit founder decision; L3 (autonomous execution) is disabled by
      default and may never be enabled, which is a legitimate permanent state.
      Decided by the founder 2026-07-22 via "use recommendations" (start the
      build).
    resolved_by: founder via 'use recommendations' (start the build), 2026-07-22
    resolved_at: 2026-07-22
  - id: D3
    text: >
      The initial action whitelist contents.
    resolution: >
      The conservative trio against fake systems: restart a service, roll back
      a deploy, scale a pool. Decided by the founder 2026-07-22 via "use
      recommendations" (start the build).
    resolved_by: founder via 'use recommendations' (start the build), 2026-07-22
    resolved_at: 2026-07-22
  - id: D4
    text: >
      Secrets and credential management.
    resolution: >
      Reference-only resolution at the seam (environment variable or OS
      keychain), never a literal secret in a file, prompt, proof, or log; an
      external secrets manager stays an optional per-repo extension, never a
      required dependency. Decided by the founder 2026-07-22 via "use
      recommendations" (start the build).
    resolved_by: founder via 'use recommendations' (start the build), 2026-07-22
    resolved_at: 2026-07-22
  - id: D5
    text: >
      Kill-switch authority: who may trip it and who may reset it.
    resolution: >
      Any human trips it instantly with no ceremony; resetting it requires a
      recorded human approval at the highest tier. Decided by the founder
      2026-07-22 via "use recommendations" (start the build).
    resolved_by: founder via 'use recommendations' (start the build), 2026-07-22
    resolved_at: 2026-07-22
---

## Intent

The method ends at the merge and says nothing about two in the morning. The old
world's five-minute diagnosis was a free byproduct of authorship - the person
who wrote the code knew which log line meant what and what changed on Friday -
and when agents author everything, that byproduct is gone: a production issue
pages a human who is a stranger to the code, and so is everyone else. The honest
reframe: the old model was never good, it was lucky, degrading to "nobody knows
how this works" the moment the author left. Support built on heroes was a
bus-factor illusion; what replaces it has to be built on systems. The method
already produces what the old world never had - every behavior traces to a
specification, every change to its proof, every module to its place in the
declared shape - so the responder does not need to have written the code: the
intent corpus is queryable, and tribal memory becomes a searchable record.

The founder's framing is the design center of this plan, not a section: an
agent with production access can destroy a company by simply doing the wrong
thing there, so its safety cannot be a policy it follows - it has to be an
architecture it cannot escape. Six pillars, each shipped as machinery with the
refusal proven: privilege separation as physics (read-only credentials against
replicas, PII redaction before context, rate and row limits, a full query audit
log - the credential makes the wrong write impossible); diagnosis and execution
as separate organs (the responder emits a remediation proposal artifact and
structurally cannot execute); execution as a whitelist of pre-vetted,
parameterized runbook actions reviewed like code, with free-form production
commands nonexistent in the machine path; an autonomy ladder whose floor is
read-only and whose stopping rung is a human decision per system, where never
enabling auto-execution is legitimate; a two-key rule for anything irreversible
or data-mutating (human authorization plus an independent fresh-context
confirmation - one mind, even a good one, does not touch data alone); and the
standing safeguards - kill switch, action budgets, timeouts, canary-first, and
post-action reconciliation that turns every failure mode into regression
criteria and keeps runbooks true from real incidents. Around that center, the
rest of the design: diagnosability gated as acceptance criteria (every future
responder is a stranger, so the code must explain itself from outside), the
incident handled as intent arriving from production through the compressed
loop, and the numbers - time-to-diagnosis, time-to-restore, recurrence,
diagnosability score, and incidents-per-area joining PLAN-0011's
cost-to-change-per-area so rot and fragility land on the same map.

Three postures bind the plan. First, everything here is proven offline against
fake evidence planes and fake systems; connecting anything to a real production
system is a separate, per-system, human-approved enablement act outside this
plan. Second, no quiet daemon: the plan builds no standing service, everything
ships runnable in-session, and the deployment posture - standing service versus
on-demand session versus hybrid - is named as the founder's decision (D1) with
the trade-offs on the record, gating enablement rather than the build. Third,
this is a receipts plan: the method's companion writing describes this design
under "The Incident" and is honest that it is design-stage; releasing this plan
turns that chapter from design into receipts, and all shipped material stays
fully generic in the engine.

## Data provenance and cross-plan dependencies

Reused as-is, recorded by the loop today (no new instrumentation):

- The intent corpus: specs, proofs, verdicts, and the plans they bind to.
- The event stream (veldo.event/v1) and git history for what changed where and
  when; the metrics derivation and dashboard machinery.
- The emergency lane, the independent-review pattern, and the human-approval
  record shape that the two-key rule extends.

New instrumentation this plan introduces:

- The incident, remediation-proposal, and runbook-action contracts, and the
  incident lifecycle extension of the event vocabulary (W1, W8).
- The evidence-plane adapters with redaction, limits, and the query audit log
  (W2).
- The whitelist store, ladder configuration, kill switch, budgets, and the
  authorization and confirmation records of the execution organ (W5, W6, W7).
- The observability criteria vocabulary (W9).

Cross-plan joins (soft, per C7): behavior-to-area attribution in diagnosis (W3)
and the incidents-per-area map (W10) join the PLAN-0011 architecture contract
and cost-to-change series where present and stand down honestly where absent;
W9's observability rules live in the architecture contract when one exists.
No work item in this plan has a hard dependency on a PLAN-0011 spec.

## Ordered delivery rationale

W1 (contracts), W2 (evidence plane), W3 (intent corpus), and W9 (diagnosability
criteria) are the four roots and start in parallel. W5 (the whitelist) needs
only the contracts. W4 (the responder loop) needs the contracts, the plane, and
the corpus; it is deliberately buildable before any execution machinery exists,
because L0/L1 is the permanent floor. W6 (the executor) consumes the whitelist;
W7 (the two-key rule) hardens the executor. W8 (the compressed loop and
reconciliation) needs the responder and the executor to close an incident end
to end. W10 (the numbers) derives from the events W8 emits. W11 releases once
every lane has shipped and the regression is green. The frontier after approval
is W1, W2, W3, and W9; the widest point is four parallel items.

## Out of scope

Live wiring to any real production system, which is a separate per-system
human-approved act (NG1); any free-form execution path (NG2); any standing
service or daemon, pending D1 and its own approval if ever chosen (NG3);
machine edits to the ladder, whitelist, kill switch, or budgets (NG4); building
log, metric, or trace stores (NG5); redesigning the emergency lane, events,
review, or metrics machinery this plan extends (NG6). The companion book
chapter itself is not work in this repository; this plan only makes its subject
true.

## Revisions

Revision 1 (2026-07-21): drafted at intake from the founder's go and the
method's invention notes ("The Incident"), with the safety architecture as the
design center per the founder's framing (production access as existential
risk): privilege separation as physics, separate diagnosis and execution
organs, whitelist-only execution, the read-only-floor autonomy ladder, the
two-key rule, and the standing safeguards; plus diagnosis from artifacts,
gated diagnosability, incident-as-intent through the compressed loop, and the
support metrics joining PLAN-0011's map. The deployment posture is deliberately
left as founder decision D1 rather than resolved in the plan. Status draft:
authored, not activated; no work starts until the plan leaves draft by a
recorded human approval.

Revision 2 (2026-07-22): the founder gave the go to start the build ("start the
5 plans build") and chose "use recommendations", resolving all five open
decisions to their recommended defaults, each now recorded in
resolved_decisions above: D1 everything runnable in-session with the posture
gating live enablement and not the build, D2 start and stay at L0/L1 with L3
disabled by default and never required, D3 the conservative whitelist trio
(restart a service, roll back a deploy, scale a pool) against fake systems, D4
reference-only secrets resolution at the seam, D5 any human trips the kill
switch instantly and reset takes a recorded highest-tier approval.
open_decisions is now empty. No scope change; recording decisions is not
approval, so status stays draft and leaving draft still requires a separate
recorded human approval.

Approved (2026-07-22): the founder approved the plan to leave draft on the go to
start the build ("start the 5 plans build"); status set to ready, approved_by
dmitry, approved_at 2026-07-22. Per the repo's approve pattern the approval
flips status and records the approver without bumping the revision. The ready
frontier (WARP-1201, WARP-1202, WARP-1203, WARP-1209) is now live for pulling
into specs.
