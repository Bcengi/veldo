---
schema: veldo.spec/v1
id: VELDO-0059
title: Installed full factory journey with real workers and enforcement
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W44
plan_revision: 4
depends_on: [VELDO-0037, VELDO-0043, VELDO-0045, VELDO-0047, VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0057, VELDO-0058, VELDO-0060, VELDO-0061, VELDO-0062, VELDO-0069, VELDO-0073, VELDO-0075, VELDO-0076, VELDO-0077, VELDO-0078, VELDO-0079, VELDO-0085, VELDO-0088, VELDO-0089, VELDO-0090, VELDO-0091, VELDO-0108, VELDO-0124, VELDO-0125, VELDO-0126, VELDO-0127, VELDO-0128, VELDO-0129, VELDO-0130, VELDO-0131, VELDO-0132, VELDO-0140, VELDO-0141, VELDO-0142, VELDO-0143, VELDO-0144, VELDO-0145, VELDO-0148]
placement: [distribution, fleet, loop, enforcement, docs]
protected_paths: []
footprint:
  - "engine/.veldo/control_floor_slice*.py"
  - ".veldo/control_floor_slice*.py"
  - "packs/*/.veldo/control_floor_slice*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "engine/.veldo/pack.py"
  - ".veldo/pack.py"
  - "packs/*/.veldo/pack.py"
  - "scripts/check_install_and_run.py"
  - ".veldo/packs.json"
  - "plans/PLAN-0019-dark-factory.md"
  - "scripts/suites/*_veldo_0059_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0059-installed-floor-slice.md"
  - "specs/index.md"
  - "proof/VELDO-0059/*"
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
      Claim: The installed factory carries an owner objective from a Telegram message that points at
      a Jira ticket, and from the authenticated API, through LangGraph grooming, owner admission,
      implementation, independent review, exact landing and completion reporting, on at least two
      subscription accounts, with every run watched live in its execution record. Set and
      completeness: Install the declared reference distribution without source-tree imports. Run a
      real Telegram message that names a Jira ticket of the project's ticket key prefix (for example
      "please do BCG-123") and an API objective using the same intake (including the UI message
      box). The PM run fetches the ticket through the Atlassian catalog server its role lists and
      quotes it with its digest in the published requirements; the actual LangGraph PM asks a
      blocking question answered by the enrolled owner, publishes a prioritized backlog of
      specifications/nested units, and obtains admission and priority by his message or his answer.
      A versioned team and exact configured MCP/tool surface assigns real Claude Code and Codex
      workers across Linux and the Mac, with iOS work only on the Mac via the relay, and the
      journey's runs use at least two subscription accounts. Observe isolated accepted-commit
      clones/C13 attachments with the repository's identity as author, kept proof, the trusted gate
      outside the candidate, fresh independent review, confirmed exact tested-tree landing pushed
      with the repository's identity, stored completion, Telegram/UI progress, stops and completion,
      and every run's execution record followed live in the UI's run terminal. Compare every journey
      step to installed service registrations and correlated receipts. Falsifier: Fall back to a
      source-tree LiveLoop implementation after omitting the installed adapter wiring; the
      installed-provenance journey must fail.
    falsified_by: >
      Fall back to a source-tree LiveLoop implementation after omitting the installed adapter
      wiring; the installed-provenance journey must fail.
  - id: AC2
    text: >
      Claim: A red gate, invalid approval/answer or invalid independent review preserves both trunk
      refs. Set and completeness: For normal, direct build and direct review entry points, run real
      red checks, wrong-subject approval, forged owner identity, stale presentation, self-review and
      unresolved blocking finding followed by a pass. Compare local/remote refs, actual
      policy/review/settlement results and absence of completion. Fixtures prove only these
      consumption checks, not live enrollment. Falsifier: Move trunk before the protected-path
      approval rejects; the unchanged-ref journey must fail.
    falsified_by: >
      Move trunk before the protected-path approval rejects; the unchanged-ref journey must fail.
  - id: AC3
    text: >
      Claim: Current dependency, authority and pre-invocation subscription usage predicates apply through every
      installed station. Set and completeness: Enumerate enabled floor entries from 0052
      registrations; change dependency or authority after selection and before review/publication,
      and exhaust the applicable subscription usage allowance for build, review and PM invocations.
      Also withhold usage so remaining allowance cannot be bounded conservatively under 0036/0062.
      Observe named refusal, zero forbidden launches/publications and retained unknown usage
      reservations. Compare actual entry coverage to RJ3; no resource-exhaustion, checkpoint or recovery
      matrix is required. Falsifier: Cache publication eligibility across a committed authority
      change; the stale-publication journey must fail.
    falsified_by: >
      Cache publication eligibility across a committed authority change; the stale-publication
      journey must fail.
  - id: AC4
    text: >
      Claim: Release 1 completion is evidenced by the complete installed journey and exact immutable
      candidate observations. Set and completeness: Compare RJ1-RJ3 and RJ11-RJ12 declarations to executable
      registrations and actual receipts for the relevant candidate/environment. Remove one required
      journey result, required runtime asset or post-gate tree equality observation; each must
      refuse release acceptance. API/UI and Telegram receipts identify the same authoritative
      request/unit, and build-only output cannot substitute for confirmed landing. Falsifier: Accept
      release readiness with a missing RJ1 result; the complete-journey-evidence check must fail.
    falsified_by: >
      Accept release readiness with a missing RJ1 result; the complete-journey-evidence check must
      fail.
required_evidence: [unit, integration, journeys]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Installed full factory journey with real workers and enforcement. Deliver the normal function needed by the running factory journey.

## Context

W44 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 6.
Section 11 of the approved [operating-model design](../docs/design/PLAN-0019-operating-model-design.md)
walks the journey RJ1 now names.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## What the reviewer judges

- Normal use: the owner writes "please do BCG-123" in Telegram (and, separately, sends an objective through the
  API or the UI message box) to the installed factory on the Linux host with its Mac worker host;
  the journey of the operating-model design's section 11 runs end to end with real engines, real
  channels, the Atlassian catalog server and at least two accounts, and he watches it in Telegram
  and the UI.
- Threat model: a journey that passes only because a source-tree fallback, a fake store, signer, policy or gate
  stood in for the installed integration; a red gate, invalid approval or answer, stale presentation
  or self-review that still moves trunk; a stale dependency, authority or usage cap that a station
  does not recheck; release acceptance with a journey result, runtime asset or post-gate tree
  equality missing. The owner's account, the installed engines, Git and the remote are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); recovery, lost acknowledgements and checkpoints (Release 2); separating the engine login from
  worker tools (Release 2, owner Telegram 29163); forged rows in our own store and files planted in
  the installed directory.

## Notes

Release 1 journey evidence includes an ordinary "fix this bug" message, which runs the default
pipeline like any other work (VELDO-0080 is Release 2 since revision 4): intake, coordination,
admission by his message, build, prove, independently review and land the exact tested tree. No
automatic reproduction service is a prerequisite, and PM proposals take effect one owning command at
a time (VELDO-0092's atomic groups are Release 2).

This is the Release 1 stage 6 full-journey qualification. Declare the reference installed
distribution and both actual host profiles before ready. Real Claude Code/Codex and real
Telegram plus authenticated UI/API are required; deterministic model fixtures may add
repeatable negative controls but cannot certify live behavior. No fake LoopSteps, LandOps,
store, signer, policy or gate substitutes for the installed integration. Register RJ1-RJ3 and RJ11-RJ12 and
retain their actual candidate/environment-bound observations; RJ4 recovery is owned by Release
2/0097.

Implement canonical engine assets with synchronized installed copies where applicable. Register
every asset this journey actually installs. Derive executable check registrations from each
criterion's declared set; retain the actual observations and each driven negative-control diff
and failing row. Real stores, files, processes, Git and signatures are required where named.
Live engine/channel qualification cannot be replaced by model-response or authorization fixtures.
Current authorization, independent engineering review, pre-invocation subscription usage caps and exact
tested-tree landing remain mandatory at the boundaries this concern consumes.

## History

2026-09-22, PLAN-0019 revision 3, Release 1 stage 6: the owner narrowed this work under
Telegram 28848 (function now, robustness/recovery later), with Mac retained by 28852 and
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC4 lost-
ack/checkpoint recovery and AC3 fencing/contention/resource matrices moved to Release 2. AC1
now spans Telegram/API moved to PM moved to owner admission moved to Linux/Mac workers moved
to proof/gate/review moved to exact land moved to Telegram/UI; meaningful AC2 refusals remain.
The criteria, declared evidence universe, Context and Notes above now carry only the retained
function. No specification status or historical proof was changed.

2026-09-25, PLAN-0019 revision 4: amended on the approved operating-model design
(docs/design/PLAN-0019-operating-model-design.md, owner Telegram 29162), section 10(e). depends_on
drops VELDO-0080 and VELDO-0092, which move to Release 2, and adds VELDO-0140 to VELDO-0145. AC1 now
matches the revised RJ1: the journey starts from a Telegram message pointing at a Jira ticket
fetched through the Atlassian catalog server, uses at least two subscription accounts and is watched
in the live run terminal, with the repository's identity as author and pusher. The Notes no longer
route ordinary defects through VELDO-0080, and a What the reviewer judges section is added. Status
unchanged.
