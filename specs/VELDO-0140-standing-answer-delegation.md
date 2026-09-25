---
schema: veldo.spec/v1
id: VELDO-0140
title: A standing answer delegation the owner renews, and no silent refusal of his answers
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0025, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0073, VELDO-0138]
placement: [engine, contracts, tracker]
protected_paths: []
footprint:
  - "engine/.veldo/control_signer_answers*.py"
  - ".veldo/control_signer_answers*.py"
  - "packs/*/.veldo/control_signer_answers*.py"
  - "engine/.veldo/control_channel_activation*.py"
  - ".veldo/control_channel_activation*.py"
  - "packs/*/.veldo/control_channel_activation*.py"
  - "engine/.veldo/control_channel_ingress*.py"
  - ".veldo/control_channel_ingress*.py"
  - "packs/*/.veldo/control_channel_ingress*.py"
  - "engine/.veldo/control_service_channel*.py"
  - ".veldo/control_service_channel*.py"
  - "packs/*/.veldo/control_service_channel*.py"
  - "bin/veldo"
  - "engine/bin/veldo"
  - "scripts/suites/*_veldo_0140_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0140-standing-answer-delegation.md"
  - "specs/index.md"
  - "proof/VELDO-0140/*"
behavior_bearing: true
acceptance_criteria:
  - id: AC1
    text: >
      Claim: One standing delegation from the owner to the Telegram edge signs his answers to any
      current request version and presentation, while each signed assertion stays bound to its exact
      request, presentation and canonical evidence. Set and completeness: Under one delegation, answer
      a request at version 1, the same request revised to version 2, and a request presented a second
      time; each settles. Then an answer bound to a superseded version or presentation, to another
      channel, actor, scope or edge key, or after expiry, is refused by name with no signature.
      Falsifier: Pin the delegation to request version 1 again; the revised-request row must fail.
    falsified_by: >
      Pin the delegation to request version 1 again; the revised-request row must fail.
  - id: AC2
    text: >
      Claim: The owner renews or replaces the delegation with his own signed command before it
      expires, and nobody else can. Set and completeness: Drive veldo channel delegate signed by the
      owner, then by another member, an agent_run or service principal, and unsigned; only the owner's
      is accepted and the prior delegation is superseded, not deleted. Falsifier: Accept a delegation
      signed by a member who is not the owner; the owner-only row must fail.
    falsified_by: >
      Accept a delegation signed by a member who is not the owner; the owner-only row must fail.
  - id: AC3
    text: >
      Claim: An owner answer the signer cannot sign is never refused silently: he is told in his chat
      why, and before the delegation expires he is told to renew it. Set and completeness: Drive an
      answer with an expired delegation, with none, and with one about to expire; observe one reply in
      his chat naming the reason or the renewal, sent through the activated edge, and no settlement.
      Falsifier: Refuse an unsignable answer without telling the owner; the told-why row must fail.
    falsified_by: >
      Refuse an unsignable answer without telling the owner; the told-why row must fail.
required_evidence: [unit, integration]
rollback: >
  Revert to per-version delegations; answers to revised or re-presented requests are then refused
  again, which fails closed.
---

## Intent

The answer delegation that lets the Telegram edge sign the owner's answers is matched on request
version and presentation version, so a delegation covers exactly one version of one request. The
only production grant (VELDO-0139's setup) is one delegation at version 1 lasting 90 days: every
revised or re-presented request, and every request after 90 days, has its answer refused with
nothing sent back to the owner. This makes the delegation a standing, renewable grant and makes
every refusal of his answer visible to him.

## Context

Found by VELDO-0139's first critical review (2026-09-25). The per-version binding moves from the
delegation to the assertion, which already binds the exact request, presentation and canonical
VELDO-0066 evidence it answers.

## Out of scope

More than one owner or channel; delegation to agents or services; restart recovery (Release 2).

## What the reviewer judges

- Normal use: the owner holds one current delegation to the Telegram edge for answers in his scope.
  It signs his answer to whatever request version and presentation is current, each assertion still
  bound to that exact request, presentation and evidence. He renews it with veldo channel delegate
  before it expires; he is told in his chat before expiry, and told why whenever an answer of his
  cannot be signed.
- Threat model: an answer bound to a superseded version or presentation, another channel, actor,
  scope or edge key, or after expiry, getting a signature; a delegation granted or renewed by anyone
  but the owner; an answer refused with the owner never told. The owner's account, the store, the
  protected signer and the edge are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); the items in
  Out of scope above; forged rows in our own store and files planted in the installed directory.

## Notes

Keep VELDO-0067's purpose, channel, actor, edge key, scope and expiry dimensions on the delegation;
move request and presentation version to the assertion check the signer already performs.

## History

2026-09-25: written by the lead from VELDO-0139's first critical review. Draft; the owner decides
readiness.
