---
schema: veldo.spec/v1
id: VELDO-0142
title: Every repository is bound to exactly one Git identity, configured at setup, and every commit the factory makes for it is authored as that identity
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W102
plan_revision: 4
depends_on: [VELDO-0028, VELDO-0042, VELDO-0056, VELDO-0057, VELDO-0139, VELDO-0144, VELDO-0148]
placement: [contracts, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_git_identity*.py"
  - ".veldo/control_git_identity*.py"
  - "packs/*/.veldo/control_git_identity*.py"
  - "engine/.veldo/control_clone*.py"
  - ".veldo/control_clone*.py"
  - "packs/*/.veldo/control_clone*.py"
  - "engine/.veldo/lander.py"
  - ".veldo/lander.py"
  - "packs/*/.veldo/lander.py"
  - "engine/.veldo/control_launch*.py"
  - ".veldo/control_launch*.py"
  - "packs/*/.veldo/control_launch*.py"
  - "engine/.veldo/control_factory_setup*.py"
  - ".veldo/control_factory_setup*.py"
  - "packs/*/.veldo/control_factory_setup*.py"
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
    Record each identity configured at setup and each identity-bound commit operation: repository,
    identity id, operation (clone author, lander merge or projection commit) and named refusal; never a
    token or key.
  metrics: >
    Count identity-bound commits and refusals by reason, per identity.
  traces: >
    Join each clone and lander commit to its repository record, its identity and the dispatch or effect
    that ran it.
  error_taxonomy: >
    Distinguish no identity bound, a second identity, identity change refused and an author or committer
    that is not the identity; none is reported as an identity-bound commit.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The owner configures his Git identities once, at setup, and every repository record names
      exactly one of them, set when the repository is created or adopted and never changed; the identity
      is always recorded, never inferred. Set and completeness: Configure the two identities of one
      factory (for example `bcengi` and `personal`) through factory setup (VELDO-0139), each with id,
      label, author name and email, remote host and owner, an API token reference and a push credential
      (the same token or a path reference to an SSH key) held as keystore references (VELDO-0144), a
      projects root and a default visibility; read back the identity records, and run setup again with
      the same identities and require the same records and no duplicate. Bind repositories to each;
      attempt a repository record with no identity, with two, and a later change of its identity, and
      require a named refusal for each with nothing written. Falsifier: Allow a repository record's
      identity to be replaced after it is set; the immutable-binding check must fail.
    falsified_by: >
      Allow a repository record's identity to be replaced after it is set; the immutable-binding check
      must fail.
  - id: AC2
    text: >
      Claim: Every worker clone of a repository is written with its identity's author name and email,
      and the engine environment carries no Git author or committer override. Set and completeness:
      Provision worker clones (VELDO-0042) of a repository under each identity while the host's global
      configuration names someone else and `GIT_AUTHOR_*` and `GIT_COMMITTER_*` are set in the caller's
      environment; read back that the launch receiver removed every `GIT_AUTHOR_*` and
      `GIT_COMMITTER_*` variable from the engine environment, commit in each clone through the engine's
      own tools, and read back that every commit's author and committer are the clone's identity.
      Falsifier: Leave the clone's author to the global configuration; the clone-author check must fail.
    falsified_by: >
      Leave the clone's author to the global configuration; the clone-author check must fail.
  - id: AC3
    text: >
      Claim: Every commit the lander makes for a repository, its candidate's merge and projection commits
      and those of a re-land, is made as that repository's identity and never as the caller repository's
      configured user. Set and completeness: From a caller repository whose `user.name` and `user.email`
      name someone else, land a unit and re-land one after another push moved the trunk (VELDO-0148);
      read back the author and committer of every merge and projection commit on the landed trunk. The
      lander takes the identity from the repository record, and a repository with no identity refuses
      before any commit. Falsifier: Let the lander take `user.name` and `user.email` from the caller
      repository; the lander-author row must fail.
    falsified_by: >
      Let the lander take `user.name` and `user.email` from the caller repository; the lander-author row
      must fail.
required_evidence: [unit, integration]
rollback: >
  Stop binding new repositories and keep the recorded bindings and identities; a commit whose repository
  has no identity refuses rather than falling back to the host's configured user. No automatic rollback
  is authorized.
---

## Intent

The owner keeps personal and Bcengi work under separate Git identities, and they must never mix: the
author written into every commit the factory makes comes from the one identity the repository belongs to,
never from whatever the host's global configuration, the caller repository or the environment happens to
hold. Pushing with that identity alone, to a remote under its owner, is VELDO-0153.

## Context

W102 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. Section 5 of the
approved [operating-model design](../docs/design/PLAN-0019-operating-model-design.md) (owner Telegram
29162) designs the identity and the binding rule. Today the author is ambient: worker clones take it from
the host's configuration or the environment, the lander takes `user.name` and `user.email` from the
caller repository (`lander.py`, its `identity` default), and factory setup (VELDO-0139) configures no
identity. VELDO-0143 creates and adopts repositories under an identity; this specification owns the
identity, its configuration at setup and the author of every commit the factory makes; VELDO-0153 owns
every push's use of it.

## Out of scope

Pushing with the identity's credential and the remote owner check (VELDO-0153); Git hosts other than
GitHub, an identity spanning two remote owners, moving a repository between identities (refused), and
the UI form for identities (VELDO-0131 shows them read-only).

## What the reviewer judges

- Normal use: the owner configures his two identities once, at setup; every repository is bound to one
  of them when created or adopted; worker clones and the lander commit as it.
- Threat model: a commit authored or committed as the other identity, the host's global user, the caller
  repository's configured user or a `GIT_AUTHOR_*` or `GIT_COMMITTER_*` value in the engine
  environment; a lander merge or projection commit, or a re-land's, under anyone but the identity; a
  repository whose identity is missing, doubled, inferred or changed after binding; setup that records
  an identity twice. The owner's account, the keystore and the remote host are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); a worker
  deliberately reading the keystore or the SSH agent through the owner's unconfined keyring daemon (the
  stated MVP boundary, Release 2); forged rows in our own store and files planted in the installed
  directory.

## Notes

The identity's API token needs permission to create repositories and workflow permission, because the
scaffold writes `.github/workflows/veldo-gate.yml`; the owner creates one token per identity in his
one-time setup, and setup records each identity with its token and push credential as keystore
references. "By construction" holds only for the factory's own Git operations: a worker running as the
same OS user can still reach the keystore and the SSH agent deliberately in the MVP (section 3 of the
design), and running tools under separate OS users is Release 2 hardening.

## History

2026-09-25: written as a draft for PLAN-0019 revision 4 from the approved operating-model design
(Telegram 29162), section 5(e). Draft; the owner decides readiness.

2026-09-25, PLAN-0019 revision 4 review: split into two concerns of three and two criteria. This
specification keeps the identity and the author: AC1 adds the identities' configuration at setup (the
footprint adds `control_factory_setup`, and depends_on VELDO-0139), AC2 adds stripping `GIT_AUTHOR_*` and
`GIT_COMMITTER_*` from the engine environment (the footprint adds `control_launch`), and new AC3 covers
the lander's merge and projection commits and a re-land's (depends_on VELDO-0148), which today take the
caller repository's `user.name` and `user.email`. The `identity` push profile and the remote owner check,
formerly AC3 and AC4, are VELDO-0153.

2026-09-25, PLAN-0019 revision 4, third review: the footprint drops `git_process.py`, which VELDO-0153
owns since the `identity` push profile moved there; no criterion of this specification changes it.
Criteria and status unchanged.
