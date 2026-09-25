---
schema: veldo.spec/v1
id: VELDO-0142
title: Every repository is bound to exactly one Git identity, the only source of its author, remote and push credential
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W102
plan_revision: 4
depends_on: [VELDO-0028, VELDO-0042, VELDO-0056, VELDO-0057, VELDO-0144]
placement: [contracts, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_git_identity*.py"
  - ".veldo/control_git_identity*.py"
  - "packs/*/.veldo/control_git_identity*.py"
  - "engine/.veldo/git_process.py"
  - ".veldo/git_process.py"
  - "packs/*/.veldo/git_process.py"
  - "engine/.veldo/control_clone*.py"
  - ".veldo/control_clone*.py"
  - "packs/*/.veldo/control_clone*.py"
  - "engine/.veldo/lander.py"
  - ".veldo/lander.py"
  - "packs/*/.veldo/lander.py"
  - "engine/.veldo/control_effect_executor*.py"
  - ".veldo/control_effect_executor*.py"
  - "packs/*/.veldo/control_effect_executor*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0142_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0142-git-identities-and-identity-profile.md"
  - "specs/index.md"
  - "proof/VELDO-0142/*"
behavior_bearing: true
observability:
  logs: >
    Record each identity-bound Git operation: repository, identity id, operation (clone author, push,
    remote creation), remote owner checked and named refusal; never a token or key.
  metrics: >
    Count identity-bound pushes and refusals by reason, per identity.
  traces: >
    Join each push and clone to its repository record, its identity and the dispatch or effect that ran it.
  error_taxonomy: >
    Distinguish no identity bound, identity change refused, remote owner mismatch, credential
    unavailable and push refused by the remote; none is reported as a landed push.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Every repository record names exactly one Git identity, set when the repository is created
      or adopted and never changed, and the identity is always recorded, never inferred. Set and
      completeness: Store the two identities of one factory (for example `bcengi` and `personal`), each
      with id, label, author name and email, remote host and owner, an API token reference and a push
      credential (the same token or a path reference to an SSH key) held as keystore references
      (VELDO-0144), a projects root and a default visibility; bind repositories to each; attempt a
      repository record with no identity, with two, and a later change of its identity, and require a
      named refusal for each with nothing written. Falsifier: Allow a repository record's identity to be
      replaced after it is set; the immutable-binding check must fail.
    falsified_by: >
      Allow a repository record's identity to be replaced after it is set; the immutable-binding check
      must fail.
  - id: AC2
    text: >
      Claim: Every worker clone of a repository is written with its identity's author name and email,
      and nothing else sets the author. Set and completeness: Provision worker clones (VELDO-0042) of a
      repository under each identity while the host's global configuration, `GIT_AUTHOR_*` and
      `GIT_COMMITTER_*` name someone else; commit in each clone and read back that every commit's author
      and committer are the clone's identity. Falsifier: Leave the clone's author to the global
      configuration; the clone-author check must fail.
    falsified_by: >
      Leave the clone's author to the global configuration; the clone-author check must fail.
  - id: AC3
    text: >
      Claim: Every push the factory performs for a repository uses a third Git process profile,
      `identity`, that supplies only the repository identity's credential. Set and completeness:
      `git_process.py` gains the `identity` profile beside `isolated` and `network`: it strips every
      `GIT_*` variable and `SSH_AUTH_SOCK`, ignores global and system configuration, and
      authenticates with that identity's credential alone, through a credential helper answering
      from the keystore or an SSH command naming that key alone. The lander's push uses it, and
      VELDO-0143's repository provisioner uses the same profile. Plant a global credential helper, a
      system `insteadOf` rewrite, `GIT_SSH_COMMAND` and an SSH agent holding another key, then push
      through the lander, and through the profile directly, to a disposable remote that accepts only
      the identity's credential; each push must use that credential and nothing planted. The
      `network` profile stays for the operator's own pushes, which keep working. Falsifier: Let the
      identity profile honor the global credential helper; the planted-helper row must fail.
    falsified_by: >
      Let the identity profile honor the global credential helper; the planted-helper row must fail.
  - id: AC4
    text: >
      Claim: A remote whose owner is not the identity's owner is refused by name, by one check that
      every push, remote creation and adoption calls. Set and completeness: For each identity,
      present a remote under its own owner (accepted), under the other identity's owner and under a
      third owner on the same host, to the check directly and through a lander push; each mismatch
      refuses by name before any network write and leaves the remote unchanged. VELDO-0143's
      creation and adoption call the same check and drive their own legs. Falsifier: Compare only
      the remote host, not its owner; the other-owner refusal row must fail.
    falsified_by: >
      Compare only the remote host, not its owner; the other-owner refusal row must fail.
required_evidence: [unit, integration]
rollback: >
  Stop binding new repositories and keep the recorded bindings; an identity-bound push that cannot use
  its profile refuses rather than falling back to the ambient network profile. No automatic rollback
  is authorized.
---

## Intent

The owner keeps personal and Bcengi work under separate Git identities, and they must never mix: the
author written into a commit, the owner of the remote and the credential that pushes all come from the
one identity the repository belongs to, never from whatever the host's global configuration, SSH agent
or environment happens to hold.

## Context

W102 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. Section 5 of the
approved [operating-model design](../docs/design/PLAN-0019-operating-model-design.md) (owner Telegram
29162) designs the identity and the binding rule. Today author, remote owner and push credential are
ambient: `git_process.py` has the `isolated` profile and the `network` profile, which for pushes
deliberately honors global and system configuration, credential helpers, `GIT_SSH_COMMAND` and
`SSH_AUTH_SOCK`, and worker clones have no remote (`control_clone.py`). VELDO-0143 creates and adopts
repositories under an identity; this specification owns the identity and every Git operation's use of
it.

## Out of scope

Git hosts other than GitHub, an identity spanning two remote owners, moving a repository between
identities (refused), and the UI form for identities (VELDO-0131 shows them read-only).

## What the reviewer judges

- Normal use: the owner configures his two identities once, at setup or in the UI; every repository is
  bound to one of them when created or adopted; worker clones author as it, and the lander and the
  repository provisioner push with its credential alone to a remote under its owner.
- Threat model: a commit authored as the other identity or as the host's global user; a push that
  authenticates with a credential helper, SSH agent key or environment override the host happens to
  have; a push to a remote under another owner; a repository whose identity is missing, doubled,
  inferred or changed after binding. The owner's account, the keystore and the remote host are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); a worker
  deliberately reading the keystore or the SSH agent through the owner's unconfined keyring daemon
  (the stated MVP boundary, Release 2); forged rows in our own store and files planted in the
  installed directory.

## Notes

The identity's API token needs permission to create repositories and workflow permission, because the
scaffold writes `.github/workflows/veldo-gate.yml`; the owner creates one token per identity in his
one-time setup. "By construction" holds only for the factory's own Git operations: a worker running as
the same OS user can still reach the keystore and the SSH agent deliberately in the MVP (section 3 of the
design), and running tools under separate OS users is Release 2 hardening.

## History

2026-09-25: written as a draft for PLAN-0019 revision 4 from the approved operating-model design
(Telegram 29162), section 5(e). Draft; the owner decides readiness.
