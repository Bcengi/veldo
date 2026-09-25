---
schema: veldo.spec/v1
id: VELDO-0153
title: Every push the factory makes for a repository authenticates with its Git identity alone, to a remote under that identity's owner
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W113
plan_revision: 4
depends_on: [VELDO-0056, VELDO-0057, VELDO-0142, VELDO-0144]
placement: [contracts, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_git_identity*.py"
  - ".veldo/control_git_identity*.py"
  - "packs/*/.veldo/control_git_identity*.py"
  - "engine/.veldo/git_process.py"
  - ".veldo/git_process.py"
  - "packs/*/.veldo/git_process.py"
  - "engine/.veldo/lander.py"
  - ".veldo/lander.py"
  - "packs/*/.veldo/lander.py"
  - "engine/.veldo/control_effect_executor*.py"
  - ".veldo/control_effect_executor*.py"
  - "packs/*/.veldo/control_effect_executor*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0153_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0153-identity-push-profile-and-remote-owner.md"
  - "specs/index.md"
  - "proof/VELDO-0153/*"
behavior_bearing: true
observability:
  logs: >
    Record each identity-bound push and remote check: repository, identity id, operation (push, remote
    creation, adoption), remote owner checked and named refusal; never a token or key.
  metrics: >
    Count identity-bound pushes and refusals by reason, per identity.
  traces: >
    Join each push to its repository record, its identity and the dispatch or effect that ran it.
  error_taxonomy: >
    Distinguish no identity bound, remote owner mismatch, credential unavailable and push refused by the
    remote; none is reported as a landed push.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Every push the factory performs for a repository uses a third Git process profile,
      `identity`, that supplies only the repository identity's credential. Set and completeness:
      `git_process.py` gains the `identity` profile beside `isolated` and `network`: it strips every
      `GIT_*` variable and `SSH_AUTH_SOCK`, ignores global and system configuration, and authenticates
      with that identity's credential alone, through a credential helper answering from the keystore or
      an SSH command naming that key alone. The lander's push uses it, and VELDO-0143's repository
      provisioner uses the same profile. Plant a global credential helper, a system `insteadOf` rewrite,
      `GIT_SSH_COMMAND` and an SSH agent holding another key, then push through the lander, and through
      the profile directly, to a disposable remote that accepts only the identity's credential; each
      push must use that credential and nothing planted. The `network` profile stays for the operator's
      own pushes, which keep working. Falsifier: Let the identity profile honor the global credential
      helper; the planted-helper row must fail.
    falsified_by: >
      Let the identity profile honor the global credential helper; the planted-helper row must fail.
  - id: AC2
    text: >
      Claim: A remote whose owner is not the identity's owner is refused by name, by one check that every
      push, remote creation and adoption calls. Set and completeness: For each identity, present a remote
      under its own owner (accepted), under the other identity's owner and under a third owner on the
      same host, to the check directly and through a lander push; each mismatch refuses by name before
      any network write and leaves the remote unchanged. VELDO-0143's creation and adoption call the same
      check and drive their own legs. Falsifier: Compare only the remote host, not its owner; the
      other-owner refusal row must fail.
    falsified_by: >
      Compare only the remote host, not its owner; the other-owner refusal row must fail.
required_evidence: [unit, integration]
rollback: >
  An identity-bound push that cannot use its profile refuses rather than falling back to the ambient
  network profile; recorded bindings are kept. No automatic rollback is authorized.
---

## Intent

The credential that pushes and the owner of the remote must come from the one identity the repository
belongs to, never from whatever credential helper, SSH agent or environment override the host happens to
hold.

## Context

W113 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. Section 5 of the
approved [operating-model design](../docs/design/PLAN-0019-operating-model-design.md) (owner Telegram
29162) designs the `identity` profile and the owner check. Today `git_process.py` has the `isolated`
profile and the `network` profile, which for pushes deliberately honors global and system configuration,
credential helpers, `GIT_SSH_COMMAND` and `SSH_AUTH_SOCK`. These were VELDO-0142's AC3 and AC4, split out
on the review of revision 4 so each specification keeps one concern: VELDO-0142 owns the identity and
the author, this specification every push's use of it.

## Out of scope

Git hosts other than GitHub, an identity spanning two remote owners, moving a repository between
identities (refused), and creating or adopting a repository (VELDO-0143).

## What the reviewer judges

- Normal use: the lander and the repository provisioner push with the repository identity's credential
  alone, to a remote under that identity's owner; the operator's own pushes keep the `network` profile.
- Threat model: a push that authenticates with a credential helper, SSH agent key or environment
  override the host happens to have; a push to a remote under another owner, or a check that compares
  only the host; a push that falls back to the ambient profile when the identity's credential is
  unavailable. The owner's account, the keystore and the remote host are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); a worker
  deliberately reading the keystore or the SSH agent through the owner's unconfined keyring daemon (the
  stated MVP boundary, Release 2); forged rows in our own store and files planted in the installed
  directory.

## Notes

"By construction" holds only for the factory's own Git operations: a worker running as the same OS user
can still reach the keystore and the SSH agent deliberately in the MVP (section 3 of the design), and
running tools under separate OS users is Release 2 hardening.

## History

2026-09-25: split from VELDO-0142 (its former AC3 and AC4, criterion text unchanged) on the review of
PLAN-0019 revision 4, so each specification keeps one concern of about three criteria. Draft, as
VELDO-0142 was; the owner decides readiness.
