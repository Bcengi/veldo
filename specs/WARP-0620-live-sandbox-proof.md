---
schema: veldo.spec/v1
id: WARP-0620
title: The live-sandbox proof of the inbound edge - execute the codified path against a real board for
  the first time, with the owner present, and find out what the offline fake could not tell us: the real
  changelog shape, real actor attribution, and whether the agent's withheld scopes actually stop it from
  approving its own work (W7 of PLAN-0016, the activation gate the reviews required)
status: blocked
risk: high - this is the FIRST REAL EXECUTION of the inbound edge, the path that turns a human's tracker
  decision into an authorized settlement in the repository, and the reviews made a live-sandbox proof the
  precondition for ever trusting it. It is HIGH and not critical because every property is exercised on a
  THROWAWAY board with seeded records: no real decision settles, no record on the production board is
  read or written, and nothing this item runs can authorize a build action. It touches no protected path
  and edits no safety core. The reason it needs the owner present is not risk approval, it is that only a
  real human account can produce a real attributed transition, and the agent structurally must not be able
  to produce one
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0016
work: W7
plan_revision: 1
depends_on: [WARP-0619, WARP-0623]
placement: [tracker]
footprint:
  - proof/WARP-0620/**
  - specs/WARP-0620-live-sandbox-proof.md
  - specs/index.md
  - .veldo/capabilities.yaml
  - engine/.veldo/capabilities.yaml
  - packs/*/.veldo/capabilities.yaml
  - scripts/selftest.py
  - docs/design/held-back/README.md
protected_paths: []
behavior_bearing: false
acceptance_criteria:
  - id: AC1
    text: >
      THE CODIFIED PATH RUNS, END TO END, AGAINST A REAL BOARD, and the run is EVIDENCE rather than a
      demonstration. On a throwaway project, not the production board, the codified bootstrap provisions
      the board (statuses, the Decision issue type, the guarded transition table, and the two fence
      groups), the outbound projection creates a Decision ticket from a SEEDED request record, and the
      doorbell sends its notice. Every step runs through the SHIPPED entry points with no hand-editing of
      the board, no monkeypatch and no local modification: if a step cannot run through the codified path,
      that is the finding and it is recorded as such rather than worked around. The captured evidence
      includes the exact commands, their real output, and the resulting issue keys.
  - id: AC2
    text: >
      THE REAL CHANGELOG SHAPE IS CAPTURED AND COMPARED AGAINST WHAT THE OFFLINE FAKE ASSUMED. After the
      owner fires ONE real transition, the raw ordered attributed changelog is fetched through the
      authenticated pull and recorded verbatim in the evidence (redacted of anything secret). Each field
      the reconcile depends on is checked against the FakeTracker's assumption and any divergence is
      recorded FIELD BY FIELD: the entry ordering, the actor attribution shape, the from-state and
      to-state representation, the entry identity used for idempotence, and the timestamp format. A
      divergence is a FINDING that becomes its own specification, never a quiet adjustment to make this
      run pass.
  - id: AC3
    text: >
      THE ACTOR IS DERIVED CORRECTLY FROM THE REAL HISTORY, which is the property the whole design rests
      on. The reconcile is run against the real changelog and must resolve the OPENING actor to the agent
      service account and the TERMINAL actor to the owner's human account, from the attributed history and
      NEVER from the ticket's current status. It must recompute the bound digest from the repository
      itself and match, and it must write the settlement record exactly ONCE through the append-only
      compare-and-swap receipt. Re-running the same reconcile immediately afterwards must be an idempotent
      no-op that writes no second record and emits no second event, proven by comparing the store and the
      event stream before and after.
  - id: AC4
    text: >
      THE FENCE IS PROVEN BY ATTEMPTING TO DEFEAT IT, not by reading configuration. Using the AGENT's own
      credential, an attempt to fire each of the three terminal transitions (Approved, Decided, Rejected)
      on a real ticket is made and each must be REFUSED BY THE BOARD, with the refusal captured verbatim.
      This is the assertion that the withheld scopes are structural: the agent holds a credential that
      cannot approve its own work. The membership facts are recorded alongside as supporting evidence (the
      agent group contains the service account and not the owner, the approver group contains the owner
      and not the service account), but the LOAD-BEARING evidence is the attempted transition being
      refused, because a group listing proves intent while a refused API call proves the mechanism.
  - id: AC5
    text: >
      THE NEGATIVES ARE RUN LIVE, because the refusals are the product (C1) and an offline refusal proves
      only offline behavior. On the real board: a forged rejection submitted as a MACHINE actor is refused
      by name; a transition to a terminal state performed by an account NOT in the approver set does not
      settle the repository record; a replayed changelog entry is idempotent; and a settlement whose bound
      digest no longer matches the repository is refused by name. Each refusal name is captured from the
      real run and matched against the name the offline suite asserts, so a refusal that fires for a
      different reason live than it does offline is caught rather than assumed equivalent.
  - id: AC6
    text: >
      THE OUTCOME IS RECORDED HONESTLY WHATEVER IT IS, and activation is a SEPARATE act. The evidence
      (proof/WARP-0620/) contains the captured commands and output, the verbatim changelog, the
      field-by-field comparison against the fake, the refused terminal-transition attempts, and an
      explicit list of every property the run did NOT establish. capabilities.yaml records the live proof
      as done for exactly the properties proven and NO others, and states plainly that wiring any
      production board or any listener remains a separate, human-approved activation that this item does
      not perform (NG3, and the plan's O3 decision that the ingress is an in-session pull with no standing
      service). If the run FAILS or a divergence blocks it, this specification records the failure as its
      result: the item is not re-run until the finding it produced has been fixed as its own spec, and a
      failed live proof is a successful outcome for the method.
required_evidence: [operational]
rollback: >
  Nothing to roll back in the repository beyond reverting the evidence commit: this item writes a proof
  directory, one capabilities entry and a selftest assertion, and changes no engine module and no
  behavior. On the board side it creates a throwaway project's contents, which are disposable by
  construction and touch no production record. No listener, service, timer or webhook is created, so
  there is nothing left running afterwards and no production board is wired by this item.
---

## Status: BLOCKED on WARP-0625, and the evidence has landed

**The run happened on 2026-07-24 against throwaway project TE1 and its evidence is now in
`proof/WARP-0620/`** - the run record, the verbatim changelog, the approval record and the manifest
draft. It was held in `docs/design/held-back/` for three months because the approval record was
missing two contract fields and the agent that wrote it refused to invent timestamps on a human
approval, which was the right call.

**Those fields were a NAMING mismatch, not missing data.** The record already carried `approved_at`
(recorded live) and an `expiry` of "single-use: this authorization covers the one session it was
given in". `recorded_at` is a verbatim copy of the former; `expires_at` expresses the latter as the
timestamp the contract wants, deliberately IN THE PAST so the record grants no live authority and
cannot authorize a second run.

**AC1, AC2, AC4 and AC6 passed. AC3 and AC5 are PARTIAL**, and the reason is GAP 2 from the run
itself: there is no live changelog reader, so `reconcile_requests` was never driven end to end
against a real board. That gap is `WARP-0625`, still held back pending plan reconciliation.

**So this item is blocked on WARP-0625 and not on any person.** GAP 1 from the same run is closed:
`WARP-0624` shipped 2026-08-02.

## Intent

Everything in the human-decision surface has been proven against a deterministic fake. That was the right
order, and it is also why tonight's first attempt to execute the codified provisioner against a real board
died immediately on a name collision that no offline fixture could reach: the fake defines the same private
names as the real adapter, so the collision was structurally invisible. WARP-0623 fixes it. This item is
what that fix exists for.

The purpose here is not to demonstrate that the surface works. It is to find out what is different when the
board is real, and to find it out on a throwaway project with seeded records rather than on the production
board with a real decision. Three things can only be learned live: the true shape of the ordered attributed
changelog, whether the actor derivation resolves real accounts correctly, and whether the agent's withheld
scopes actually stop it from firing a terminal transition. The first two are assumptions the fake encoded;
the third is a claim about a credential that only an attempted API call can settle.

The one property this item treats as load-bearing above the rest: the agent must TRY to approve and must be
REFUSED. A group membership listing proves someone's intent. A refused API call proves the mechanism. The
whole surface exists so a machine cannot authorize its own work, and until that refusal has been observed
against a real board it is a design, not a guarantee.

## Context

- Why the owner must be present: only a real human account can produce a real attributed terminal
  transition, and the design requires that the agent cannot. So the decisive input of this run is a click
  that the machine is structurally unable to make. The owner's time cost is about two minutes; the rest is
  execution and capture.
- What the reviews required: a live-sandbox proof of the real changelog shape, the real actor attribution
  and the agent's withheld scopes, before the edge is trusted live. This item is that gate, and it is
  deliberately not autonomous.
- What is already verified and therefore NOT re-proven here: the offline logic of the reconcile (WARP-0619,
  independently reviewed, pass_with_notes with zero blocking findings), the authorization engine
  (WARP-0616, inert and fail-closed), the projection (WARP-0617) and the doorbell (WARP-0618). This item
  proves that the same code behaves the same way when the tracker is real.
- The precondition: WARP-0623, because the codified provisioning path currently raises TypeError on every
  call. Running this item before that fix lands would prove nothing except the defect that is already
  known.
- What must NOT happen here: no production board record is read or written, no real decision settles, and
  no listener or webhook is created. The plan's O3 decision stands, the ingress is an in-session pull with
  no standing service.

## Out of scope

- Any production board activity. The production project is not touched by this item.
- Any listener, webhook receiver, daemon or timer. Delivery stays an in-session pull.
- Settling any real decision. Every record in this run is seeded and disposable.
- Fixing whatever the run finds. A divergence in the changelog shape, a wrong endpoint, a missing scope or
  an unexpected refusal reason each become their own specification. This item's deliverable is the finding,
  not the repair.
- Any change to the reconcile, the authorization engine, the projection or the doorbell. If the live run
  shows one of them is wrong, that is a finding, and changing them here would mean proving patched code
  rather than shipped code.

## Notes

- Capture first, interpret second. Record the raw changelog verbatim before comparing it to anything, so
  the evidence survives a wrong interpretation.
- The comparison against the fake is field by field and written down even where it MATCHES, because a
  match is the evidence that the offline suite's assumption was sound.
- Run the negatives even if the positive path looks perfect. A surface that settles the happy case and
  quietly accepts a forged rejection is worse than one that does neither.
- Write down what was NOT established. The temptation after a green live run is to describe the surface as
  proven; the honest artifact enumerates the properties still resting on offline evidence only.
- RULE #1 clean (ASCII hyphen only, no em dash, no en dash, no prose double-hyphen).
