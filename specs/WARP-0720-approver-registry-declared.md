---
schema: veldo.spec/v1
id: WARP-0720
title: The approval surface cannot recognise anyone - declare the approver registry IN THE REPOSITORY on a
  protected path, make the tracker group a reconciliation check that fails loudly on divergence, and refuse
  rather than degrade when the declaration cannot be read
status: draft
risk: critical - this declares WHO MAY APPROVE. It is the identity half of the authorization surface, and the
  policy block (VEL-3) is inert without it, so together they are the switch that decides who can authorize
  work. Two failure directions, both serious: too permissive (a malformed declaration read as a wider approver
  set) and silently empty (an unreadable declaration treated as zero approvers, which either authorizes nothing
  and looks like a bug, or worse, is conflated with a declared-empty set). It also REGISTERS A NEW PROTECTED
  PATH, which is itself a policy.yaml edit and therefore a protected-path act requiring a commit-bound approval
  record. Critical rather than high because nothing in the repository currently populates this registry at all,
  so this item creates the first thing that can make an approval SUCCEED
owner: dmitry
human_approval: required
approval_record: >
  DIRECTION DECIDED on the board: VEL-11 (https://bcengi.atlassian.net/browse/VEL-11) reached Decided at
  2026-07-26 04:10 EDT, fired by Dmitry, comment verbatim: "Option 1". That settles WHERE the registry lives
  (a declared file in the repository, on a protected path) and rejects deriving it from the tracker group or
  taking it from the caller. THE DIFF ITSELF IS NOT YET APPROVED: this spec still needs its own recorded
  approval before landing, because it registers a new protected path (a policy.yaml edit) and because VEL-11
  was explicitly rated a DECISION about direction rather than a sign-off on code that did not exist.
lane: standalone
depends_on: [WARP-0616, WARP-0719]
placement: [engine]
footprint:
  - .veldo/approvers.yaml
  - .veldo/authorization.py
  - engine/.veldo/authorization.py
  - packs/*/.veldo/authorization.py
  - .veldo/policy.yaml
  - scripts/check_approver_reconcile.sh
  - docs/
  - scripts/selftest.py
  - specs/WARP-0720-approver-registry-declared.md
  - specs/index.md
protected_paths:
  - .veldo/policy.yaml
behavior_bearing: true
observability:
  logs: A refusal names WHICH condition produced it - the declaration absent, unreadable, malformed, or an
    identity absent from it - so an operator can tell "nobody may approve" from "we could not tell who may
    approve" without reading the source. The reconciliation check prints both sets and their symmetric
    difference when they diverge, so the fix is obvious from the failure.
  error_taxonomy: The names stay closed and gain three: REGISTRY_ABSENT (no declaration exists, which is
    distinct from an empty one), REGISTRY_UNREADABLE (a declaration exists but cannot be read or parsed, which
    must never be read as empty), and REGISTRY_RECONCILE_DIVERGED (the declared set and the tracker group
    disagree). The pre-existing UNKNOWN_APPROVER keeps its name and meaning for an identity absent from a
    readable declaration.
acceptance_criteria:
  - id: AC1
    falsified_by: >
      Give .veldo/authorization.py a module-level fallback that loads .veldo/approvers.yaml itself when the
      approver_registry parameter of is_authorized (.veldo/authorization.py:483) arrives empty, and the
      assertion that the core reads the declaration through the EXISTING parameter with no new coupling must
      go red; removing the approvers.yaml entry from policy.yaml protected_paths falsifies the second leg,
      since a change to who may approve would then need no commit-bound path-scoped approval.
    text: >
      THE REPOSITORY IS THE AUTHORITY, AND ITS SHAPE IS THE ONE THE CODE ALREADY EXPECTS. A declaration at
      .veldo/approvers.yaml supplies exactly what is_authorized takes as its approver_registry parameter today
      (authorization.py:439, documented at :453 as {approver_id: {roles, independence, actor}}), so this item
      FILLS AN EXISTING SEAM rather than inventing one, and the core's signature does not change. It is
      registered in policy.yaml's protected_paths at the same floor as policy.yaml itself, so changing who may
      approve requires the same commit-bound, path-scoped approval as changing the policy that uses it. The
      role vocabulary is the one Dmitry decided on VEL-3: `founder`. A selftest asserts the loaded declaration
      satisfies the registry contract and that authorization.py reads it through the existing parameter with no
      new coupling.
  - id: AC2
    falsified_by: >
      Catch the parse failure in the registry loader and return an empty mapping, so a truncated document
      presents as a readable declaration with no approvers, and the assertions that a mode-000 file, a
      directory at that path, a truncated document, a document parsing to a list or a scalar, and non-mapping
      entries each raise REGISTRY_UNREADABLE and authorize NOTHING must go red, together with the assertion
      that the WARP-0719 degradation path is not reached on an unreadable registry.
    text: >
      UNREADABLE IS NEVER EMPTY, AND THAT IS THE WHOLE SAFETY POINT. Three distinct outcomes, each refused or
      permitted by name: an ABSENT declaration raises REGISTRY_ABSENT; a declaration that exists but cannot be
      read or parsed raises REGISTRY_UNREADABLE; and a declaration that is READABLE AND DECLARES NO APPROVERS
      is a legitimate state meaning nobody may approve, which authorizes nothing and says so. Conflating the
      second with the third is the failure this repository has now paid for FOUR times in another module
      (absent versus unreadable), so it is asserted directly: a mode-000 declaration, a directory at that path,
      a truncated document, one that parses to a list or a scalar, and one whose entries are not mappings each
      raise REGISTRY_UNREADABLE and authorize NOTHING. And because WARP-0719 degrades quorum against registry
      SIZE, an unreadable registry must never present as a small one - a selftest asserts the degradation path
      is not reached when the registry is unreadable.
  - id: AC3
    falsified_by: >
      Make the reconciliation stage return a PASS when the network or the credentials are unavailable instead
      of recording a named not-applicable reason in the catalog, and the assertion that unavailability is
      recorded as not-applicable with its reason rather than as agreement must go red; comparing only the two
      set SIZES instead of the symmetric difference falsifies the divergence leg while agreement keeps
      passing.
    text: >
      THE TRACKER GROUP BECOMES A LOUD RECONCILIATION CHECK, NOT A SECOND AUTHORITY. A gate stage compares the
      declared approver set against the membership of the tracker's approver group and FAILS on divergence,
      printing both sets and their symmetric difference. That keeps the repository authoritative while making
      it impossible for the two to disagree quietly - which is the actual risk of a repo-only registry, since
      the live fence keys on the group. THE HONEST BOUNDARY IS DECLARED RATHER THAN GLOSSED: the check needs
      network and credentials, so when either is unavailable it is SKIPPED WITH A NAMED REASON in the catalog's
      not-applicable list, never silently passed and never treated as agreement. A selftest asserts divergence
      fails, agreement passes, and unavailability is recorded as not-applicable with its reason rather than as a
      pass.
  - id: AC4
    falsified_by: >
      Require the `founder` role key inside the loader itself rather than taking the vocabulary from the
      declaration, and the assertion driving the same loader through a one-person, a three-person and an empty
      declaration whose role vocabularies share no words must go red for every vocabulary that does not
      contain that name.
    text: >
      GENERIC, CANON-SYNCED, AND HONEST ABOUT WHAT IT DOES NOT DO. Nothing about Bcengi, its team size or its
      names is in the engine: the behaviour is driven by the declaration and the configured group, asserted by
      driving the loader through a one-person, a three-person and an empty declaration with role vocabularies
      that share no words. The operator guide gains one short generic section on the declaration, the protected
      path, and the reconciliation check. It records plainly what this item does NOT establish: that a declared
      identity is the person it claims to be (that is the tracker's authentication, not ours), and that a human
      approver is not being driven by a script. Engine canon holds across engine and all six packs,
      teeth as a matrix over the three new refusals (exactly diagonal, off-diagonal an EMPTY LIST, targets
      unique, modules sha256-unchanged), the frozen two_key/policy_check/decision core is byte-UNCHANGED, the
      full gate is GREEN, and RULE #1 is clean.
required_evidence: [unit]
rollback: >
  Revert the commit. The change adds a declaration file, its loader and three named refusals, a reconciliation
  gate stage, one protected_paths entry and an operator-guide section, re-synced byte-identical across
  engine and the packs. Reverting returns the registry to unpopulated, which means every approval is
  refused with unknown_approver and the whole human-decision surface is inert again - safe, since it authorizes
  nothing, but useless. So a revert is a loss of capability rather than a return to a good state, and it must
  not be done to unblock anything without replacing the registry. Removing the protected_paths entry is itself
  a protected-path act and needs its own approval.
---

## Intent

Found while rewriting VEL-3 on 2026-07-26, and it is the kind of gap that only surfaces when you stop trusting
the ticket and read the module: **we built a surface that decides WHO MAY APPROVE and never built the place
that says who those people are.** `is_authorized()` takes an `approver_registry` as a runtime parameter and
nothing in the repository populates it. So even with the policy block VEL-3 exists to add, every approval would
be refused with `unknown_approver`, because the mapping from an identity to the roles it holds does not exist
anywhere.

Dmitry decided the direction on VEL-11: **"Option 1"** - the declaration lives in the repository, on a protected
path. That is the only choice consistent with the principle this whole plan rests on, that the repository is
authoritative and a tracker action is merely a submitted assertion. Deriving the registry from the tracker group
was rejected because it makes authorization depend on a live network call AND moves control of the approver set
out of the repository and into Jira administration; taking it from the caller was rejected because the caller
would then decide its own approver set, which defeats the point.

The engineering that matters is not the file. It is the three-way distinction in AC2. An ABSENT declaration, an
UNREADABLE one, and a READABLE ONE DECLARING NOBODY are three different facts, and collapsing the middle into
either of the others is how this becomes dangerous. This repository has been bitten by exactly that conflation
four times in the metrics module, so it is built in from the start here rather than found by a reviewer.

## Context

- Why the reconciliation check exists at all: a repo-only registry can drift from the tracker group that the
  live fence actually keys on, and a silent disagreement between "who the repo says may approve" and "who the
  board will let approve" is the worst of both designs. Failing loudly on divergence keeps one authority and
  still notices reality moving.
- Why the check must be skipped-with-a-reason rather than passed when offline: a network-dependent check that
  quietly passes when it cannot run is a check that reports agreement it never observed. The catalog already
  has a not-applicable mechanism with recorded reasons; use it.
- Why this depends on WARP-0719: that item degrades quorum against the NUMBER of registered approvers, so an
  unreadable registry presenting as a small one would silently weaken the rule. 0719 refuses on an unreadable
  registry; this item is where "unreadable" gets its meaning, so the two must agree and are asserted together.
- What VEL-11 did and did not settle: it settled WHERE the registry lives. It did not approve a diff, because
  none existed. This spec therefore still needs its own recorded approval, and it touches policy.yaml.

## Out of scope

- No change to the policy block itself (VEL-3), to the fence, or to who Dmitry decides may approve.
- No authentication. This item declares WHICH IDENTITIES hold which roles; proving an identity is who it claims
  to be is the tracker's job and is stated as out of scope rather than implied.
- No secret material. The declaration holds identities and roles, never credentials, and WARP-0718 owns
  credential supply.
- No second tracker, no group management, no writing to the tracker. The reconciliation check READS the group.
- No new authorization concept: no roles beyond what policy.yaml declares, no new quorum rule.

## Notes

- Write AC2's five hostile shapes before the loader works. The temptation is to build the happy path and add
  the refusals after, and the refusals are the item.
- Do not let the reconciliation check become a second authority. It compares and fails; it never supplies.
- Prove genericity by loading declarations whose role words share nothing with ours, not by grepping for the
  absence of "Bcengi".
- NO UNBACKED UNIVERSAL: "never read as empty", "authorizes nothing" and "no secret material" each need the
  assertion that enumerates them.
- RULE #1 clean (ASCII hyphen only, no em dash, no en dash, no prose double-hyphen).
