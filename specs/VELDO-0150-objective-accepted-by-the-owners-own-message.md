---
schema: veldo.spec/v1
id: VELDO-0150
title: An objective proposed from the project owner's own message is accepted by that message, and any other is still presented
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W110
plan_revision: 4
depends_on: [VELDO-0066, VELDO-0077, VELDO-0126]
placement: [contracts, engine, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_objective*.py"
  - ".veldo/control_objective*.py"
  - "packs/*/.veldo/control_objective*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0150_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0150-objective-accepted-by-the-owners-own-message.md"
  - "specs/index.md"
  - "proof/VELDO-0150/*"
behavior_bearing: true
observability:
  logs: >
    Record each objective's acceptance with the path it came by (his own message, naming the intake
    command and message, or his answer, naming the settlement), or the presentation made instead.
  metrics: >
    Count objectives accepted by the owner's own message, presented for acceptance, and refused.
  traces: >
    Join each acceptance to the intake command, the attributed message or API request and the objective
    revision it accepted.
  error_taxonomy: >
    Distinguish a source that is not the project owner's own, an acceptance evidence that names another
    intake command, and a stale objective revision; none accepts.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: An objective proposed from the project owner's own authenticated message is accepted by
      that message, and any other objective is accepted only by the owner's answer to its presentation.
      Set and completeness: Create an objective in one project through the shared intake (VELDO-0126)
      from the owner's own Telegram message, one from his API request submitted, signed by the API edge,
      through `Intake.receive('api_request', ...)`, the intake interface the authenticated API calls, as
      VELDO-0126 drives it, and one each from a message and an API request by a principal who is not the
      project's owner. The first two are accepted
      with no presentation; the others are presented for current owner acceptance through VELDO-0077,
      and a stale answer after a bound field changes is refused. Acceptance alone admits and prioritizes
      nothing (VELDO-0077 AC1). Falsifier: Accept an objective from a message by a principal who is not
      the project's owner without presenting it; the own-message acceptance check must fail.
    falsified_by: >
      Accept an objective from a message by a principal who is not the project's owner without
      presenting it; the own-message acceptance check must fail.
  - id: AC2
    text: >
      Claim: An acceptance by the owner's own message binds that message's intake command as its
      evidence, with the canonical attribution of the message, and binds the same exact outcome, scope,
      authority and evidence requirements as an acceptance by answer. Set and completeness: For an
      objective accepted by his own message, compare the acceptance record with the intake command it was
      proposed from and the VELDO-0066 attribution (message id, sender, time), and its bound fields with
      those an accepted answer records. Present acceptance evidence naming another intake command, a
      message by the owner in a project he does not own, and a repeat of the same message; each is
      refused by name or returns the same acceptance, with no second record. Falsifier: Accept an
      objective whose acceptance evidence names an intake command other than the one it was proposed
      from; the bound-evidence row must fail.
    falsified_by: >
      Accept an objective whose acceptance evidence names an intake command other than the one it was
      proposed from; the bound-evidence row must fail.
required_evidence: [unit, integration]
rollback: >
  Present every objective for acceptance, as VELDO-0077 did; accepted objectives and their evidence are
  kept. No automatic rollback is authorized.
---

## Intent

Asking the owner to accept work he wrote himself is friction the terminal does not have. His own
authenticated message is his acceptance of the objective it proposes; anyone else's still waits for his
answer.

## Context

W110 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 4. Section 4 of the
approved [operating-model design](../docs/design/PLAN-0019-operating-model-design.md) (owner Telegram
29162) amends VELDO-0077 so an objective proposed from the owner's own message is accepted by that
message. VELDO-0077 has landed with its proof, so this repository's convention puts that amendment in its
own specification that depends on it, and VELDO-0077 keeps its landed text. Admission at the default
priority by the same message is VELDO-0079's revision 4 amendment, built beside this one.

## Out of scope

Admission and priority (VELDO-0079); outcome assessment and cancellation (VELDO-0077); any change to
VELDO-0077's criteria.

## What the reviewer judges

- Normal use: the owner writes "please do BCG-123"; intake proposes an objective in the project, and
  his message accepts it with nothing presented. An objective from another member's message or API call
  is presented to him as before. He can still withdraw at any time.
- Threat model: an objective from someone other than the project's owner accepted without a
  presentation; an acceptance whose evidence is not the message that proposed it; the owner's message
  in a project he does not own treated as its owner's; a repeated message recording a second acceptance;
  acceptance treated as admission or priority. The owner's account, the store and the authenticated
  channel edges are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); VELDO-0079's
  admission; recovery and restart (Release 2); forged rows in our own store and files planted in the
  installed directory.

## Notes

VELDO-0077 records acceptance through the VELDO-0068 settlement of a presented request. This concern
adds the second path, whose evidence is the intake command of the message itself, and leaves the
presented path and every VELDO-0077 check as they are. It is built with VELDO-0079's admission by his
message, in the order of section 12 of the design.

## History

2026-09-25: written for PLAN-0019 revision 4 from the approved operating-model design (Telegram 29162),
section 4(e), whose VELDO-0077 AC1 amendment is carried here whole because VELDO-0077 has landed; its
criterion and falsifier are AC1, and AC2 checks the acceptance evidence that amendment named. A draft: only the owner
marks a specification ready.

2026-09-25, PLAN-0019 revision 4, third review: AC1 drives the API leg through the intake interface
`Intake.receive('api_request', ...)` with a request the API edge signs, as VELDO-0126 does, rather than
an authenticated API call, because the API server (VELDO-0130) is a later stage and drives its own leg.
Criterion meaning and status unchanged.

2026-09-25, build: `.veldo/control_objective.py` gains `accept_message`, the second acceptance path beside
the presented `accept`, which it leaves unchanged. Its evidence is the intake command that first wrote
the one intake source that proposed the objective (`invalid_input:intake_command` for any other); the
source's principal, the proposal's and the bound acceptor must be the project's current owner
(`not_owner:source`, which also refuses his message in a project he does not own); the command names
the current revision and bound digest (`stale_subject:revision`). The acceptance binds the intake
command, the source, the canonical attribution (the kept VELDO-0066 evidence, or the edge-signed API
request) and the same revision, bound digest, principal and ruling an accepted answer binds; the same
command again returns the same acceptance and writes nothing. Suite 75 has 9 rows, red at 0af8dc0 by
assertion; finding 150 has 11 mutations (`proof/VELDO-0150/`). Filed for VELDO-0128: its Telegram
report names an acceptance's settlement, unavailable for one by his own message. The criteria, status
and risk are unchanged.

2026-09-25, review fix: the review showed a plain member could propose and amend the objective of the
owner's message with her own outcome, scope and assessor and then accept it by his message. `accept_message`
now also requires that whoever wrote the bound fields, the proposer and the author of every amendment,
is the project's owner or the project manager of the project's current team (control_team's PM_ROLE
workers of the accepted revision), `not_authorized:author` otherwise, so such an objective is presented
to him through `accept`. The repeat of an accepted message now answers only after the membership, owner
and project-state checks, so a principal outside the project's scope is refused `not_authorized:scope`
and a paused project `project_not_active:PAUSED`, never "repeated". Suite 75 gains 4 rows (13 in all, red
at 0af8dc0 by assertion) and finding 150 gains 4 mutations (15 in all), among them the falsifier that
drops the authorship check. The criteria, status and risk are unchanged.
