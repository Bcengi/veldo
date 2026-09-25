---
schema: veldo.spec/v1
id: VELDO-0161
title: A repository the owner names is adopted under one identity on his settled answer and taken on by the running factory without a restart
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W121
plan_revision: 4
depends_on: [VELDO-0028, VELDO-0029, VELDO-0047, VELDO-0068, VELDO-0139, VELDO-0142, VELDO-0153]
placement: [contracts, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_repository*.py"
  - ".veldo/control_repository*.py"
  - "packs/*/.veldo/control_repository*.py"
  - "engine/.veldo/control_effect_executor*.py"
  - ".veldo/control_effect_executor*.py"
  - "packs/*/.veldo/control_effect_executor*.py"
  - "engine/.veldo/control_factory_setup*.py"
  - ".veldo/control_factory_setup*.py"
  - "packs/*/.veldo/control_factory_setup*.py"
  - "engine/.veldo/control_service*.py"
  - ".veldo/control_service*.py"
  - "packs/*/.veldo/control_service*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0161_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0161-repository-adoption-without-restart.md"
  - "specs/index.md"
  - "proof/VELDO-0161/*"
behavior_bearing: true
observability:
  logs: >
    Record each adoption with the repository, identity and settled decision, the scaffold commit when one
    was laid, each adoption signature with the decision it answered, and the service taking the
    repository on, or the named refusal; never a token.
  metrics: >
    Count repositories adopted and refused by reason, adoption signatures issued, and repositories taken
    on by the running service.
  traces: >
    Join the settled decision, the scaffold commit, the adoption signature, the store binding and the
    running service's receiver configuration for the repository.
  error_taxonomy: >
    Distinguish remote owner mismatch, push refused, no settled decision, signature refused and a
    repository the running service did not take on; a repository left `failed` names its reason.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: An existing repository the owner names is adopted under his chosen identity, with the
      scaffold laid as one recorded commit when missing, and signed by the adoption signer only for a
      repository a settled decision names. Set and completeness: Adopt a repository that carries the
      scaffold and one that does not; the provisioner checks its remote owner against the identity
      (VELDO-0153), lays the scaffold as one recorded commit and pushes it where missing, and the proposal
      he answered names that commit. The adoption signer is a service key setup enrolls among the host's
      enrollment signers, whose only use is signing a VELDO-0029 binding for a repository named in a
      settled owner decision; the effect executor checks the settlement before asking for the signature,
      and every signature is journaled. Falsifier: Let the adoption signer sign a binding for a repository
      no settled decision names, and the signer-scope check must fail; lay the missing scaffold in a commit
      the answered proposal does not name, and the scaffold-commit row must fail.
    falsified_by: >
      Let the adoption signer sign a binding for a repository no settled decision names, and the
      signer-scope check must fail; lay the missing scaffold in a commit the answered proposal does not
      name, and the scaffold-commit row must fail.
  - id: AC2
    text: >
      Claim: An adopted repository is taken on by the running authority service without a restart or
      reinstallation. Set and completeness: With the installed authority service running and serving one
      repository, adopt a second; the store binds it, the running service adds its receiver configuration,
      and the repository record becomes `active`, while the service's process identity and start time
      are unchanged and nothing is reinstalled; a packet from the new repository's receiver is then
      accepted by that same running service, and one from a repository no settlement adopted is refused.
      Falsifier: Take the adopted repository on only by restarting the authority service; the
      same-process row must fail.
    falsified_by: >
      Take the adopted repository on only by restarting the authority service; the same-process row must
      fail.
required_evidence: [unit, integration]
rollback: >
  Stop adoption and disable the adoption signer; repositories already adopted stay as they are, with
  their records, for the owner to remove by hand. No automatic rollback is authorized.
---

## Intent

The owner names an existing repository, or asks for a new one that the factory creates and then
adopts, and the running factory takes it on under one identity on his answer, with no separate command,
restart or reinstallation.

## Context

W121 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. Section 5 of the
approved [operating-model design](../docs/design/PLAN-0019-operating-model-design.md) (owner Telegram
29162) designs adoption, the adoption signer and the service taking the repository on without a
restart; its section 12 builds this with VELDO-0143 (item 19). These were VELDO-0143 AC3, split out on
the third review of revision 4 so taking a repository on without a restart has a falsifier of its own,
which would have given VELDO-0143 a fifth criterion; VELDO-0143 keeps the factory project's proposal,
creation and activation, and its creation path ends in this adoption. VELDO-0139 is a standalone built
item, so its edge is kept here and not in the plan graph. This new specification is draft; authoring it
supplies neither implementation proof nor operational activation.

## Out of scope

Creating a repository (VELDO-0143 AC2); moving a repository between identities (refused); Git hosts
other than GitHub; several projects in one repository.

## What the reviewer judges

- Normal use: the owner answers a proposal to adopt a repository, or to create one; the provisioner
  checks the remote owner, lays the scaffold if it is missing, the adoption signer signs its binding, and
  the running service takes it on, all with no restart.
- Threat model: a binding signed without a settled owner answer; the adoption signer used for anything
  other than a repository a settled decision names; a remote under another owner adopted; the service
  restarted or reinstalled to take on the repository; a packet from a repository nobody adopted
  accepted. The owner's account, the keystore, GitHub and the store are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); forged rows in
  our own store and files planted in the installed directory.

## Notes

The adoption signer widens enrollment, so every signature it makes is journaled, and the review should
judge exactly that it signs only for a repository named in a settled owner decision (section 13 of the
design). The scaffold is laid before the lander has anything to judge a unit by, so it is one recorded
commit rather than a first unit.

## History

2026-09-25: split from VELDO-0143 AC3 on the third review of PLAN-0019 revision 4. AC1 is the former AC3's
adoption, scaffold commit and signer scope, with its falsifier unchanged; AC2 is its "taken on by the
running service without a restart", which had no falsifier, now with its own. A draft: only the owner
marks a specification ready.

2026-09-25, PLAN-0019 revision 4, fourth review: AC1's scaffold half, one recorded commit named by the
proposal he answered, gets a falsifier of its own beside the signer-scope one. Criterion meaning
unchanged. A draft.
