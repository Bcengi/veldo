---
schema: veldo.spec/v1
id: VELDO-0126
title: One Telegram and API message intake for proposed work
status: ready
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W89
plan_revision: 3
depends_on: [VELDO-0025, VELDO-0035, VELDO-0047]
placement: [contracts, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_intake*.py"
  - ".veldo/control_intake*.py"
  - "packs/*/.veldo/control_intake*.py"
  - "scripts/suites/*_veldo_0126_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0126-message-objective-intake.md"
  - "specs/index.md"
  - "proof/VELDO-0126/*"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/check_teeth_mutations.py"
behavior_bearing: true
observability:
  logs: >
    Record operation, domain/repository, actor or role, input/configuration versions,
    resulting record identity and named refusal; exclude secrets.
  metrics: >
    Count accepted/refused operations and pending work, with bounded run duration and
    charge attribution where this concern uses a worker.
  traces: >
    Correlate input request, configuration/host, dispatched work and resulting authority evidence.
  error_taxonomy: >
    Distinguish unauthenticated, unauthorized, stale version, unsupported configuration,
    unavailable service, missing evidence and unknown outcome; none is successful completion.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Both source adapters submit the same normalized intake command and produce a proposed
      objective or work item. Set and completeness: Enumerate the two allowed source kinds and drive
      one actual Telegram message and one authenticated API call with equivalent text through the
      common service. Retain source identity/message ID or API request ID, exact text, authenticated
      principal and project context. If the project is unresolved, retain an inbox proposal and ask
      rather than invent ownership. Falsifier: Write API messages into a separate work queue; the
      common-command and proposal comparison must fail.
    falsified_by: >
      Write API messages into a separate work queue; the common-command and proposal comparison must
      fail.
  - id: AC2
    text: >
      Claim: Arbitrary message text is retained without requiring a ticket identifier or structured
      command. Set and completeness: Exercise ordinary prose, a Jira link, a follow-up clarification
      and incomplete intent through both sources; inspect original text/provenance and resulting
      proposed work or clarification. A referenced ticket may be fetched only by a configured agent
      tool and is not watched for changes. Falsifier: Require every message to contain a Jira ticket
      ID; the plain-objective intake check must fail.
    falsified_by: >
      Require every message to contain a Jira ticket ID; the plain-objective intake check must fail.
  - id: AC3
    text: >
      Claim: Intake cannot admit or prioritize work and accepts only authenticated allowed sources.
      Set and completeness: Attempt forged Telegram actor text, unauthenticated API calls, an
      unsupported source and a valid message; inspect zero executable units or priority grants from
      intake. Repeat the same source request identity unchanged and require the same proposal, with
      changed content refusing an identity conflict. Falsifier: Create an executable unit directly
      from an accepted message; the no-intake-admission check must fail.
    falsified_by: >
      Create an executable unit directly from an accepted message; the no-intake-admission check
      must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern while preserving accepted records, configuration
  revisions and unresolved work. No automatic rollback, retry or recovery is authorized.
---

## Intent

An owner message creates a proposed objective or work item through one common intake
operation, regardless of whether it arrived on Telegram or the authenticated API.

## Context

W89 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 3.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its 2026-09-22
scope amendments. This new specification is draft; authoring it supplies neither implementation
proof nor operational activation. Implementation still requires readiness and applicable approval.

## Out of scope

Automatic recovery, durability/scale qualification and additional host/channel types beyond
this declared concern. These belong to later releases as assigned by the plan. No existing
specification status, implementation, test, runtime policy or deployed service changes in this draft.

## What the reviewer judges

- Normal use: a message from an authenticated allowed source, a Telegram message acquired through
  VELDO-0066 or an authenticated API call through the intake interface VELDO-0130 will expose, becomes
  one normalized intake command. It records the source identity (message id or API request id), the
  exact text, the authenticated principal and the project context, and produces a proposed objective or
  work item, or an inbox proposal plus a question when the project is unresolved. Arbitrary prose is
  kept as written; a ticket reference is data an agent may fetch with its configured tools, never
  watched. Intake never admits or prioritizes work. The same source request repeated unchanged returns
  the same proposal. AC1's API leg runs through the intake interface the API will call; VELDO-0130
  drives its own leg when it is built.
- Threat model: forged actor text inside a Telegram message; an unauthenticated API call; an
  unsupported source; one source written to a separate queue; a message required to carry a ticket id;
  intake that creates an executable unit or grants priority; a repeated request identity with changed
  content. The owner's account, the store and the authenticated channel edges are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); Jira watchers,
  polling intake and webhook triggers (dropped by the owner, 28857); the API server itself
  (VELDO-0130); recovery (Release 2); forged rows in our own store and files planted in the installed
  directory.

## Notes

Owner Telegram 28857 limits new-work triggers to a Telegram message or authenticated API call;
28859 allows agents to use exactly their configured MCP servers/tools. The UI message box uses
the API. No Jira watcher, polling intake, webhook trigger or special Jira channel is built.
Referenced Jira content is task data retrieved by agents through configured tools; a ticket
does not grant admission.

Use canonical engine assets and synchronize installed copies. Resolve the proposed footprint's
architecture mapping before ready, including the new UI assets where applicable; this draft does
not amend the architecture contract. Inventory every asset the selected journey installs. Compare
executable registrations to each criterion's declared universe, observe the real named interfaces,
and retain the driven negative-control diff and named failed row. Fixtures cannot certify real
platform, engine or host behavior. Required evidence labels describe future implementation proof,
not tests run by this writing revision.

## History

2026-09-22: new draft for PLAN-0019 revision 3, Release 1 stage 3, under the owner's
complete-factory MVP decisions. Simple function and its meaningful refusal checks are in this
release; recovery and robustness are Release 2, governance depth Release 3, broader hosts/channels,
installation, adoption, migration and rollback Release 4.

2026-09-24, implementation: `.veldo/init_scaffold.py` (both copies, and any pack copy) and
`scripts/check_teeth_mutations.py` were added to the footprint before either was changed, so the
scaffold installs the intake module and the registry holds this specification's mutations.

2026-09-24, implementation: `.veldo/control_intake.py` takes a Telegram message kept and attributed by
VELDO-0066 and an API request signed by the API edge principal into one normalized command and one
store command that writes only intake sources, proposals and questions; an unresolved project keeps an
inbox proposal and asks. Suite 68 has 18 rows, finding 126 has 14 mutations, and the rows are red at
d34980f (`proof/VELDO-0126/`). The API leg drives the intake interface; VELDO-0130 drives its own leg.
The criteria, status and risk are unchanged.
