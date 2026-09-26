---
schema: veldo.spec/v1
id: VELDO-0079
title: Grooming and admission requests through enrolled decision surfaces
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W64
plan_revision: 4
depends_on: [VELDO-0065, VELDO-0068, VELDO-0069, VELDO-0073, VELDO-0078, VELDO-0150]
placement: [contracts, tracker, engine, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/request.py"
  - ".veldo/request.py"
  - "packs/*/.veldo/request.py"
  - "engine/.veldo/request_projection.py"
  - ".veldo/request_projection.py"
  - "packs/*/.veldo/request_projection.py"
  - "engine/.veldo/request_reconcile.py"
  - ".veldo/request_reconcile.py"
  - "packs/*/.veldo/request_reconcile.py"
  - "engine/.veldo/authorization.py"
  - ".veldo/authorization.py"
  - "packs/*/.veldo/authorization.py"
  - "engine/.veldo/control_grooming*.py"
  - ".veldo/control_grooming*.py"
  - "packs/*/.veldo/control_grooming*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "engine/.veldo/control_backlog.py"
  - ".veldo/control_backlog.py"
  - "packs/*/.veldo/control_backlog.py"
  - "scripts/check_teeth_mutations.py"
  - "scripts/suites/*_veldo_0079_*.py"
  - "scripts/suites/73_veldo_0078_backlog.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0079-grooming-enrolled-decision-surfaces.md"
  - "specs/index.md"
  - "proof/VELDO-0079/*"
behavior_bearing: true
observability:
  logs: >
    Record the operation, domain, repository, unit or request identity, accepted input versions,
    outcome and named refusal without secrets.
  metrics: >
    Count accepted and refused operations and expose current pending work for this specification.
  traces: >
    Join accepted inputs, actual service observations and resulting authority records by identity.
  error_taxonomy: >
    Distinguish invalid input, missing authority, stale subject, unavailable service,
    missing evidence and unknown outcome where applicable; never label unknown as success.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Grooming presents the exact complete authorization material. Set and completeness:
      Compare real Telegram briefs to the request schema: class, outcome, scope/exclusions,
      priority, ceiling, lane, policy/spec revisions, protected paths, release authority,
      expiry/evidence, decomposition, alternatives and questions. Change each bound field and refuse
      the earlier presentation. Falsifier: Omit decomposition digest from presentation binding; the
      changed-decomposition refusal check must fail.
    falsified_by: >
      Omit decomposition digest from presentation binding; the changed-decomposition refusal check
      must fail.
  - id: AC2
    text: >
      Claim: Only current admission and priority authorities may admit or prioritize prepared work;
      the project owner's own message that proposed its objective admits that work at the project's
      default priority, and grooming presents a request only when the PM raises a question or
      proposes a priority other than the default. Set and completeness: Exercise work prepared under
      an objective from the owner's own message with no PM question and the default priority
      (admitted by his message, no request presented), with a PM question, and with a proposed
      non-default priority (each presented as a request), and work under an objective accepted by a
      presented answer (presented). Exercise owner admit/reject/return choices and a PM
      self-admission attempt through actual authenticated assertions; require actor-authored
      reasoning, separate authority predicates, no execution while required questions remain
      unresolved, and the owner's later reprioritization or withdrawal applied. Falsifier: Admit at
      default priority work whose PM proposal raised a question or proposed another priority; the
      ask-when-needed check must fail.
    falsified_by: >
      Admit at default priority work whose PM proposal raised a question or proposed another
      priority; the ask-when-needed check must fail.
  - id: AC3
    text: >
      Claim: The accepted ruling authorizes only its exact operation, target and parameters. Set and
      completeness: Change priority, ceiling and target separately beneath a retained valid signed
      command, and submit an unchanged ordinary duplicate; inspect refusal of changes and one bound
      settlement for the duplicate. Falsifier: Reuse an admission signature after changing priority
      without digest validation; the parameter-binding check must fail.
    falsified_by: >
      Reuse an admission signature after changing priority without digest validation; the parameter-
      binding check must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Grooming and admission requests through enrolled decision surfaces. Deliver the normal function needed by the running factory journey.

## Context

W64 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 4.
Section 4 of the approved [operating-model design](../docs/design/PLAN-0019-operating-model-design.md)
admits work by his own message.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## What the reviewer judges

- Normal use: the PM prepares work under an accepted objective; when the objective came from the owner's own
  message and the PM has no question and proposes the default priority, his message admits it and
  nothing is asked; otherwise grooming presents the exact complete request on Telegram or the UI,
  and the owner's answer admits, rejects or returns it and sets its priority, settling once.
- Threat model: a PM or any role label admitting or prioritizing work; work admitted without a question the PM
  raised being answered; a non-default priority applied without his answer; a presentation that
  omits a bound field, or an earlier presentation answered after a bound field changed; a signed
  ruling reused after its priority, ceiling or target changed. The owner's account, the store and
  the signing edge are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); concurrent and lost-acknowledgement qualification (Release 2); channels other than Telegram and
  the API (Release 4); forged rows in our own store and files planted in the installed directory.

## Notes

Telegram is the first presentation channel; UI/API later consumes the same full request and
settlement contract. No Jira intake, tracker projection or signed-CLI decision channel is
built. Admission and priority remain distinct decisions even when the owner settles them
together.

Implement canonical engine assets with synchronized installed copies where applicable. Register
every asset this journey actually installs. Derive executable check registrations from each
criterion's declared set; retain the actual observations and each driven negative-control diff
and failing row. Real stores, files, processes, Git and signatures are required where named.
Live engine/channel qualification cannot be replaced by model-response or authorization fixtures.
Current authorization, independent engineering review, enforceable pre-call spend caps and exact
tested-tree landing remain mandatory at the boundaries this concern consumes.

## History

2026-09-22, PLAN-0019 revision 3, Release 1 stage 4: the owner narrowed this work under
Telegram 28848 (function now, robustness/recovery later), with Mac retained by 28852 and
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC3
concurrent/lost-ack qualification moved to Release 2; extra-channel coverage moved to Release
4. Jira-specific grooming is dropped. Exact material, owner ruling and distinct
admission/priority remain. The criteria, declared evidence universe, Context and Notes above
now carry only the retained function. No specification status or historical proof was changed.

2026-09-25, PLAN-0019 revision 4: amended on the approved operating-model design
(docs/design/PLAN-0019-operating-model-design.md, owner Telegram 29162), section 4(e). AC2: work
under an objective proposed from the owner's own message is admitted at the default priority by that
message, and grooming presents a request only when the PM raises a question or proposes another
priority; the PM still cannot admit. Its falsifier is now the ask-when-needed check, with PM
self-admission kept in its set. A What the reviewer judges section is added. Status unchanged.

2026-09-25, PLAN-0019 revision 4, third review: depends_on adds VELDO-0150, because AC2 admits work under
an objective the owner's own message accepted, which is VELDO-0150's acceptance path. Criteria and
status unchanged.

2026-09-25, build: `.veldo/control_grooming_request.py` (new) is the admission request contract (R09): the
sixteen fields (class, lane, outcome, scope, exclusions, priority, ceiling, policy, specification
revisions, protected paths, release authority, expiry, evidence, decomposition, alternatives, questions),
the brief that renders every one of them, the binding (the decomposition by its digest) and digest a
ruling names as its target, the live comparison with the item, objective, project and specification
files, and the route: the owner's own message (VELDO-0150's own_message acceptance) admits at the default
priority, rank 3, only when the project manager asks nothing, proposes the default and wrote the revision
himself or the owner did. `.veldo/control_grooming.py` (new) is the grooming service, the one writer of
admission requests (declared owner): the PM proposes, the service routes the revision, presents each
decision as its own VELDO-0064 request on the `admission` or `priority` touchpoint through VELDO-0065,
revises a pending request when a proposed field changes so its new presentation supersedes the one shown,
and applies settled answers through the backlog. The footprint gains `.veldo/control_backlog.py` (and its
engine and pack copies), because the backlog is the one writer of backlog items and AC2 needs two of its
transitions: `admit_message` (AWAITING_GROOMING to PRIORITIZED in one transaction on his message's
evidence) and the owner's own `reprioritize`; its admit and prioritize accept only the admission
request's target and brief once grooming recorded one, refuse a revision that no longer binds the live
records, and require the owner to hold admission_authority to admit and priority_authority to prioritize
when the decision is applied. It also gains `scripts/check_teeth_mutations.py`, for finding 79.
`request.py`, `request_projection.py`, `request_reconcile.py` and `authorization.py` were not changed:
they are the PLAN-0016 file surface, not on the control store path. VELDO-0150's `accept_message` is not
called by this code: the admission reads the objective's recorded acceptance path, and calling it is the
intake-to-objective step, not admission. Suite `76_veldo_0079_grooming`, red at 516afd1 by assertion;
finding 79 (23 mutations) in `proof/VELDO-0079/`. Filed for the lead: an item grooming never recorded a
request for can still be admitted through VELDO-0078's own thinner brief (requiring grooming for every
admission changes that suite's helpers); the default priority is one constant for every project. Status
stays ready.

2026-09-25, build, the lead's decision on the threat model's presentation that omits a bound field: the
thin admission path is closed. The backlog's admit and prioritize now answer only the item's admission
request, so an item grooming made no request for is refused `missing_evidence:admission_request` and
nothing is written; VELDO-0078's own item target and briefs (`decision_target`, `admission_brief`,
`priority_brief`) are removed from `.veldo/control_backlog.py`, since nothing admits through them. The
footprint gains `scripts/suites/73_veldo_0078_backlog.py`: its admission and priority helpers go through
grooming (pm proposes, the grooming service presents on Telegram, olga answers, pm applies), its
workspace gains the specification files of the units it grooms, every row keeps its meaning, and finding
78 still rejects all 29 of its mutations. Suite `76_veldo_0079_grooming` gains the row
`material/ungroomed-thin-brief` and finding 79 the mutation `grooming-thin-path-reopened` (24 mutations);
two mutations are re-anchored on the new code. The default priority stays one constant, rank 3, for every
project. Status stays ready.

2026-09-25, build, review findings B1 and F2. B1: the own-message route read only the current revision,
so the project manager could undo a question he had raised or a ruling the owner had made by proposing
again. `control_grooming_request.py` now reads the item's history from the store (`history`: every
decision request grooming opened for the admission request, by its shared `alias`, and the settled
rulings among them not yet applied), and `route` names `presented` once any request was opened to the
owner, so his message never admits that item again; grooming and the backlog's `admit_message` both
pass it. A new revision recorded while a request is pending revises that request at once, so its new
presentation supersedes the one he saw and an answer to that one is refused. A settled ruling other
than an approval that is not yet applied (`held`) refuses the next proposal and the next grooming
(`stale_subject:settled_ruling`), so his reject or return is applied as he gave it; a settled approval
of an earlier revision authorizes nothing later (its digest binds it). The backlog refuses an answer
already applied as `already_applied` before judging its binding, the precedence VELDO-0078 had. Suite
`76_veldo_0079_grooming` gains `route/presented-then-proposed`, `route/ruling-settled-unapplied` and
`route/returned-then-proposed` (18 rows), red at 11a65a7 by assertion; finding 79 gains six mutations
(30). F2: row `activation/decomposition-growth` of the 0078 suite applies the earlier answer to the grown
decomposition with no proposal between and expects `stale_subject:decomposition`, then keeps the
request-digest refusal as its own later part; finding 78 gains `grown-decomposition-unchecked` (30).
Status stays ready.
