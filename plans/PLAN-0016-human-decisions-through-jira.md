---
schema: veldo.plan/v1
id: PLAN-0016
title: Human decisions through Jira - the decision and approval control surface. Every human decision,
  not only approvals, becomes a durable ticket anyone who must weigh in can reach; a human's Jira action
  is only a SUBMITTED ASSERTION and the repository decides, records an append-only receipt, and only then
  projects the terminal state; no decision is ever captured in a terminal prompt and there are no bypasses
kind: mvp
status: ready
revision: 1
owner: dmitry
approved_by: dmitry
approved_at: 2026-07-23
risk: critical

outcomes:
  - id: O1
    becomes_true: >
      EVERY human decision is a ticket on the board, not only approvals. Spec approval, plan approval, a
      choice among options on a foundational question, a review disposition, a risky-action
      authorization, and an escalation each arrive as a durable Jira issue carrying a readable brief, an
      explicit RISK section, what acting vouches for and what it does NOT, the options with their dead
      ends, and links to the artifacts. Anyone who must weigh in can reach it, asynchronously, without
      having been at a keyboard when it arose.
    measure: >
      Every touchpoint kind in the taxonomy projects to a ticket with all required brief fields present,
      and the conformance suite refuses a projection missing the brief, the RISK section, or the
      vouches-for statement. No supported touchpoint reaches a human by any other channel.
  - id: O2
    becomes_true: >
      COMMAND AND RECEIPT, REPOSITORY AUTHORITATIVE. A human's Jira action is a submitted assertion and
      never an authoritative command. The ticket stays pending, the repository verifies and accepts or
      rejects, an append-only receipt is written under compare-and-swap against the request's current
      revision, and only then does the outbound projection set the terminal state. Jira's terminal state
      is a projection of repository acceptance, never an input to it.
    measure: >
      No Jira automation and no Jira status alone can advance a repository record: a seeded terminal
      status with no receipt leaves the record unchanged, and the projection sets a terminal state only
      after an accepted receipt exists. Conflicting history (approved then rejected) resolves by the
      ordered attributed changelog, and a stale approval cannot win.
  - id: O3
    becomes_true: >
      THE INBOUND EDGE IS SAFE BY CONSTRUCTION. A webhook is a DOORBELL with no authority: it triggers
      an authenticated pull of the issue's canonical, ordered, attributed changelog, and the repository
      recovers order, actor and intent from that history. Delivery is durable at-least-once through a
      supervised ingress and a managed queue, never in memory and never a database as a bus. On any
      unprovable gap or conflicting history it BLOCKS and raises a ticket; it never infers approval from
      current status.
    measure: >
      Conformance over replay, a spoofed actor, an automation transition, a bulk transition, downtime
      with gap detection, and a concurrent artifact change: each is refused or blocked by name, and
      idempotence holds under duplicate delivery keyed by the immutable changelog event id.
  - id: O4
    becomes_true: >
      AUTHORIZATION IS REPOSITORY-SIDE AND SEPARATION OF DUTIES IS STRUCTURAL. Every action is
      attributable to a specific account, attribution comes from the verified changelog rather than the
      webhook body, and the approver set, role-incompatibility and quorum matrix live in repository
      policy. The raiser is never the approver, an artifact's author or executor can never satisfy an
      independent-review role, separate keys are distinct human principals, and a model review is NEVER
      a human key. Critical and irreversible actions take two keys.
    measure: >
      Each separation rule refuses by name on a seeded violation; policy.yaml risk_tiers is the single
      source of the required counts; and an approval lacking an actor-authored rationale, an explicit
      disposition of blocking findings, or a recorded risk acceptance is refused (the anti-rubber-stamp
      floor).
  - id: O5
    becomes_true: >
      A RISKY-ACTION AUTHORIZATION BINDS THE WHOLE CONTEXT and cannot be replayed: target, environment,
      parameters, the relevant state digest, an expiry, and a one-time nonce. The executor rechecks
      every precondition and atomically marks the authorization consumed, and a revocation or any
      artifact or parameter change prevents execution and forces a new authorization.
    measure: >
      Conformance on a fake system: a replayed authorization refuses as consumed, an expired one
      refuses, a changed parameter or artifact digest refuses, a revoked one refuses, and the
      consume step is atomic under concurrent attempts.
  - id: O6
    becomes_true: >
      NO BYPASSES EXIST. No decision or approval is ever captured in a terminal prompt, there is no
      manual hand-advancement of a record, and until the live inbound edge exists the loop BLOCKS at
      every human touchpoint rather than falling back to an unaudited path. A phased rollout keeps
      unsupported decision kinds blocked, never bypassed.
    measure: >
      A structural conformance check finds no code path that records a human decision from a terminal
      prompt and no path that advances a request without a receipt; an unsupported touchpoint kind
      blocks with the reason named.

non_goals:
  - id: NG1
    text: >
      No reinvention of the safety core. veldo.approval/v1, two_key.py, decision.py with
      decision_review.py, policy.yaml risk_tiers, and the reconcile lineage in tracker_bridge.py are
      REUSED byte-compatibly. The genuinely new organ is narrow: the command-and-receipt inbound binding,
      the Decision projection, and the board schema.
  - id: NG2
    text: >
      No polling, no database as a bus, no rogue or detached listener process, and no hand-editing of
      the board. Where the ingress runs is a declared, supervised choice, never an ambient background
      process.
  - id: NG3
    text: >
      No live wiring as part of landing a spec. Live inbound wiring and any live board mutation are
      separate, explicit, human-approved activations, proven against a real Jira sandbox first.
  - id: NG4
    text: >
      No terminal carve-out for "non-risky" decisions. That exemption existed in the first draft and was
      REMOVED, because a misclassification would become an unaudited path.
  - id: NG5
    text: >
      No secrets, personal data, or operating metrics leaving the repository. The brief, the RISK
      section, the comments and the notice are redacted before anything is sent, links are preferred
      over payloads, and inbound ticket content is untrusted DATA, never instructions.

constraints:
  - id: C1
    text: >
      Every item is built through the method itself: a specification, a green canonical gate, a proof
      manifest, and an independent fresh-context review. Every safety property ships as a negative test
      that proves the refusal.
  - id: C2
    text: >
      This plan is CRITICAL tier: it is the human-in-the-loop boundary of an autonomous build-and-ship
      system. Items touching the inbound binding, the authorization matrix, the two-key path, or
      policy.yaml carry a critical or high floor with recorded human approval. Nothing may lower a class.
  - id: C3
    text: >
      Fail closed and block on ambiguity. An unprovable gap, a conflicting history, a stale revision, a
      missing rationale, an unverifiable actor, or a superseded artifact refuses or blocks; nothing is
      inferred.
  - id: C4
    text: >
      Any material change to a request creates a NEW REVISION and invalidates prior attestations, so the
      board can never show an approval against a stale artifact.
  - id: C5
    text: >
      The canon is the engine templates: every contract, module, check and skill lands in the engine,
      syncs byte-identical to this repository and every pack, and stays fully generic.

feature_tree:
  - id: F1
    title: The board schema and the Decision issue type
    outcome_refs: [O1]
  - id: F2
    title: The request and decision records, and the outbound projection
    outcome_refs: [O1, O2]
  - id: F3
    title: The inbound command-and-receipt edge
    outcome_refs: [O2, O3]
  - id: F4
    title: Authorization, separation of duties, and the two keys
    outcome_refs: [O4]
  - id: F5
    title: Risky-action authorization bound through execution
    outcome_refs: [O5]
  - id: F6
    title: Conformance, no bypasses, docs and release
    outcome_refs: [O6]

work:
  - item: W1
    spec: WARP-0612
    title: >
      Board schema. The Decision issue type, the full state set, and the guarded transition table in the
      codified bootstrap configuration, provisioned idempotently as an extension of the existing board
      bootstrap. The board is provisioned by code, never by hand.
    feature_refs: [F1]
    depends_on: []
    order: 10
  - item: W2
    spec: WARP-0615
    title: >
      Records and events, by reuse. Adopt veldo.approval/v1 byte-compatibly with both existing readers,
      plus the decision record and the existing event vocabulary, and add only the request fields not
      already present: the canonical request id and hash, the tier, the roles and quorum, the expiry and
      the supersession. The request envelope REFERENCES the settlement records and never extends them, so
      the frozen safety-core readers stay byte-compatible.
    feature_refs: [F2]
    depends_on: [WARP-0612]
    order: 20
  - item: W3
    spec: WARP-0617
    title: >
      The outbound projection. A decisions index and a Decision projection as a sibling of the existing
      spec and plan mirror, carrying the brief, the RISK section, the links, the assignment and the
      watchers, with redaction applied before anything leaves the repository. One-way and idempotent: the
      projection writes the board, never the record.
    feature_refs: [F2]
    depends_on: [WARP-0615]
    order: 30
  - item: W4
    spec: WARP-0618
    title: >
      Notify. The Telegram doorbell: a concise notice with a link, on-channel, idempotent, redacted, and
      signal-only. It tells a human that a decision is waiting and carries no decision content and no
      authority of its own.
    feature_refs: [F2]
    depends_on: [WARP-0615]
    order: 40
  - item: W5
    spec: WARP-0619
    title: >
      The inbound binding, the new safety-critical organ, OFFLINE LOGIC. The command-and-receipt edge: a
      human's tracker transition is a submitted assertion, the repository derives the true actor and
      intent from the ordered attributed changelog and never from current status, validates against the
      frozen safety core with changelog-verified identities, independently recomputes the bound digest,
      and writes the settlement only through an append-only compare-and-swap receipt. Blocks on any gap,
      conflict or ambiguity. Proven entirely offline over a deterministic fake tracker.
    feature_refs: [F3]
    depends_on: [WARP-0615, WARP-0616]
    order: 50
  - item: W6
    spec: WARP-0616
    title: >
      Authorization, by reuse and extension. The repository-side approver set, the role-incompatibility
      and quorum matrix, attribution taken from the verified changelog, the two-key binding reusing the
      shipped two_key module, and the anti-rubber-stamp attestations. Ships INERT: the engine exists and
      fails closed, and switching it on is an edit to policy.yaml, a protected path, which only a
      recorded human approval can authorize. The surface cannot authorize its own activation.
    feature_refs: [F4]
    depends_on: [WARP-0615]
    order: 45
  - item: W7
    spec: WARP-0620
    title: >
      The LIVE-SANDBOX PROOF of the inbound edge, done with the owner present. The real changelog shape,
      real actor attribution, the agent's withheld scopes, and one real decision flowing end to end on
      the real board, before the edge is trusted live. This is the activation gate the reviews required
      and it is deliberately not autonomous: it is the one item that needs the human in the room.
    feature_refs: [F3, F6]
    depends_on: [WARP-0619]
    order: 60
  - item: W8
    spec: WARP-0621
    title: >
      Risky-action execution binding. The authorization binds target, environment, parameters, state
      digest, expiry and a one-time nonce; the executor rechecks every precondition and atomically marks
      the authorization consumed; a revocation or any artifact or parameter change forces a new
      authorization. Extends the shipped executor rather than replacing it.
    feature_refs: [F5]
    depends_on: [WARP-0616]
    order: 70
  - item: W10
    spec: WARP-0625
    title: >
      The live changelog reader. Implement the read-only seam the whole inbound edge assumes: a real
      adapter fetches the ordered attributed changelog through the authenticated pull and normalizes
      Jira's NESTED payload to the flat {actor, actor_kind, from, to} shape the shipped accessors read.
      Declared on TrackerAdapter with a docstring implying it exists; implemented only on FakeTracker,
      so the WARP-0620 live run hand-wrote the fetch. Added as W10 on 2026-08-02 because the plan never
      carried a work item for it - the gap was found BY the live proof, after the plan was written.
    feature_refs: [F5]
    # WARP-0623 (the provisioner collision fix) is a real prerequisite and is named in the
    # SPEC's own depends_on; it is not listed here because a plan work item may only depend
    # on other work items of the same plan, and 0623 is standalone.
    depends_on: [WARP-0619, WARP-0620]
    order: 75
  - item: W9
    spec: WARP-0622
    title: >
      Conformance, no-bypass proof, docs and release. End-to-end conformance over the fake tracker
      covering replay, a spoofed actor, automation transitions, workflow edits, downtime, secret
      rotation, concurrent artifact changes, repository conflicts and revocation; a STRUCTURAL no-bypass
      check proving no code path records a human decision from a terminal prompt and no path advances a
      request without a receipt; honest capability records; made-true documents; and the plan released.
      Live wiring stays a separate human-approved activation.
    feature_refs: [F6]
    depends_on: [WARP-0617, WARP-0618, WARP-0620, WARP-0621]
    order: 80

release:
  milestone: >
    The decision and approval control surface, live: every human decision reaches a durable ticket with a
    readable brief and a RISK section, a human's action is a submitted assertion that the repository
    verifies and settles through an append-only compare-and-swap receipt, the terminal board state is a
    projection of repository acceptance, the inbound edge blocks on any ambiguity, separation of duties
    and the two-key rule are enforced repository-side from policy, a risky-action authorization cannot be
    replayed, and no bypass exists anywhere: no terminal prompt, no hand-advancement, no rogue listener.
  mode: continuous
  require_all_work_shipped: true
  require_full_regression: true

regression:
  journeys:
    - id: RJ1
      title: >
        A seeded terminal Jira status with no receipt leaves the repository record unchanged, and the
        projection sets a terminal state only after an accepted receipt exists.
      activation: {when: after:WARP-0619}
      suite: command-and-receipt conformance (fake tracker)
    - id: RJ2
      title: >
        The inbound edge refuses or blocks by name on replay, a spoofed actor, an automation actor, a
        bulk transition, a detected gap, a stale revision and a conflicting history.
      activation: {when: after:WARP-0619}
      suite: inbound-edge negative suite (fake tracker)
    - id: RJ3
      title: >
        Each separation-of-duties and quorum rule refuses a seeded violation by name, and an approval
        with no actor-authored rationale or no disposition of blocking findings is refused.
      activation: {when: after:WARP-0616}
      suite: authorization conformance
    - id: RJ4
      title: >
        A replayed, expired, revoked, or parameter-changed risky-action authorization each refuse, and
        the consume step is atomic under concurrent attempts.
      activation: {when: after:WARP-0621}
      suite: risky-action binding conformance (fake system)
    - id: RJ5
      title: >
        No bypass exists: a structural check finds no path recording a human decision from a terminal
        prompt and no path advancing a request without a receipt, and an unsupported touchpoint kind
        blocks with the reason named.
      activation: {when: after:WARP-0622}
      suite: no-bypass structural conformance
    - id: RJ6
      title: >
        The existing gate stays green across every item, and the frozen safety-core readers stay
        byte-compatible with the records this surface writes.
      activation: {when: after:WARP-0615}
      suite: full canonical gate plus safety-core compatibility
---

## Intent

This plan was approved on 2026-07-23 in VEL-1 and its design lives in the Confluence document
"Human decisions through Jira - the decision and approval control surface for Veldo" (version 2, hardened
after two independent fresh-context reviews and an external review that returned not-sound on version 1).
This file is that approved design recorded as a plan in the repository, drafted from the document rather
than from anyone's memory of it.

It exists because the points where a human must decide are the entire safety boundary of an autonomous
build-and-ship system, and they were being captured badly: some in a transient terminal prompt, which is
a rubber stamp that is unreadable, unexplained, seen by one person and records nothing, and some in
repository files no non-engineer can reach. The owner's requirement, verbatim: all the decisions that
humans need to make go through tickets, because nobody is going to sit and watch a terminal, and because
different people may be involved in a decision and there is otherwise no way for anyone else to reach it.

## Context

- WHY THIS FILE WAS MISSING AND WHY THAT MATTERED. The plan was approved and its work items were built,
  but the plan itself was never written to disk. Nine specifications carry "PLAN-0016" in their prose and
  the modules reference it in comments, while no plans/PLAN-0016 file existed, so the burn-down could not
  show this thread, the items were tracked as standalone, and the remaining work lived only in
  conversation and in an assistant's memory. That is exactly the failure the method exists to prevent:
  durable knowledge held outside the repository degrades. This file closes it.
- WHAT IS ALREADY SHIPPED against these items: W1 the codified board bootstrap, W2 the request record,
  W3 the outbound Decision projection, W4 the Telegram doorbell, W5 the inbound reconcile offline logic,
  and W6 the authorization engine, shipped INERT and fail-closed. The fenced agent identity that makes
  attribution and withheld scopes real shipped alongside them.
- WHAT REMAINS: W7 the live-sandbox proof, which needs the owner present and is tracked as a Decision on
  the board; W8 the risky-action execution binding; and W9 the conformance, no-bypass proof, docs and
  release. Until W7 activates the edge, every human touchpoint BLOCKS by design (NG4, no bypass), which
  is why a notice is currently written by hand rather than fired by the doorbell: the machinery exists and
  is proven offline, and it is deliberately not yet live.
- THE ORDER IS NOT ARBITRARY. The inbound binding (W5) depends on the authorization engine (W6) because
  the edge validates with changelog-verified identities against that engine; W6 ships inert so that
  switching authorization on is a separate, protected, human-approved act; and W7 gates activation on a
  real-board proof because the offline fake cannot prove the real changelog shape.

## Out of scope

- Any live activation. Live inbound wiring and live board mutation are separate explicit human-approved
  acts, proven against a real sandbox first, never bundled into landing a specification.
- Rebuilding the safety core. The approval record, the two-key rule, the decision record and its review
  gate, the risk tiers and the reconcile lineage are reused, not reimplemented.
- Any decision surface other than the tracker. There is no terminal path, no email path and no chat path
  that records a decision. A chat notice may point at a ticket and carries no authority.

## Notes

- The taxonomy of what becomes a ticket is in section 3 of the controlling document: spec approval, plan
  approval, a decision among options, a review disposition, a risky-action authorization, and an
  escalation or unblock.
- THE OPEN DECISIONS ARE NOW RESOLVED AND RECORDED. O1 (Decision as its own issue type) and O5 (phased
  rollout, approvals and decisions first) were resolved in the controlling document. O2, O3 and O4 were
  required by the external review before approval and had never been recorded anywhere; they were raised
  as VEL-6 and DECIDED by the owner on 2026-07-24, verbatim:
  - O2, the approver set: "Yes just me for now. But in the future we will extend this." So the approver
    matrix is the owner alone, every tier, quorum of one, with two keys required for anything irreversible,
    money-related, or externally visible. The recorded ceiling this implies, stated honestly: with a
    single-human approver set, separation of duties rests on the raiser-is-not-approver rule, and a two-key
    requirement is met by the owner plus an independent fresh-context machine confirmation, never by two
    humans, until the set is extended.
  - O3, where the ingress runs: "Option 2 now, in the future we will consider Option 1." So there is NO
    listener and no standing service: an in-session opt-in pull reconciles the changelog for open requests
    when a session runs. A supervised declared service stays the declared eventual target. The pull path is
    the same code either way, since the doorbell carries no authority; only the trigger differs. The
    accepted cost: a decision made while no session is running is not picked up until the next one, so the
    loop is not truly event-driven yet.
  - O4, the reversibility policy: "confirmed." A single authorized decider is permitted ONLY for a choice
    whose reversal-cost classification has itself passed independent review; money, external commitments
    and anything irreversible default to two keys; and the raiser's own label cannot downgrade scrutiny.
    That last clause is the load-bearing one: without it, anything becomes single-key by being called
    reversible, which is the rubber stamp re-entering through the classification step.
  W6's activation (the policy.yaml edit, a protected path, tracked as VEL-3) and W8 both depend on these
  three, and are now unblocked to be specified.
- RULE #1 clean (ASCII hyphen only, no em dash, no en dash, no prose double-hyphen).
