---
schema: veldo.spec/v1
id: VELDO-0287
title: A spec lands in a push only when it is new to main, so an edit to a file of a spec already on main is work the pushing ticket's review covers, and a draft renumbered before it reached main is not a lowered approval
status: ready
risk: high
risk_areas: [auth_security]
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0272]
placement: [enforcement]
protected_paths: [".veldo/policy_check.py", "engine/.veldo/policy_check.py"]
footprint:
  - ".veldo/policy_check.py"
  - "engine/.veldo/policy_check.py"
  - "scripts/suites/129_veldo_0272_approval_scope.py"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0287-a-spec-lands-only-when-it-is-new-to-main.md"
  - "specs/index.md"
  - "proof/VELDO-0287/**"
behavior_bearing: true
observability:
  logs: >
    Unchanged refusal lines. A file of a spec already on main that no landing spec covers is named in the
    existing "landing_without_review: no spec covers" line, after the other uncovered files.
  metrics: >
    None.
  traces: >
    None; each check is one synchronous read of files and Git objects.
  error_taxonomy: >
    No new refusal names. landing_without_review, owner approval missing and approval_flag_lowered keep
    their meaning; what changes is which specs they are asked of.
acceptance_criteria:
  - id: AC1
    text: >
      policy_check.landing_specs counts a spec the push carries as landing only when it is not a non-draft
      spec at the push base (the one commit push_range resolves, the protected ref's tip) and is not a
      draft at HEAD. A spec absent, draft or unreadable at the base is not on the base. Only landing specs
      whose proof bundle the push changes (any bundle file other than an approval record) give the
      producer to the protected-path check, the objection override and approval_rule, and need the
      review. A spec already on main that the push builds again (a re-land) is not a landing spec.
    falsified_by: >
      Suite 129 row AC3 landing/slimmed-bundle: a reviewed ticket that rewrites a file in the proof
      bundle of a required spec on main exits 0, with no review or owner approval asked of that spec. Row
      AC3 landing/re-land: a spec on main rebuilt with its own new manifest and review and no new spec
      exits 1. Mutation land287-on-base-lands (a spec on main lands again) reds both.
  - id: AC2
    text: >
      In any push that is not spec-only, a changed spec file or proof bundle file (not an approval record)
      of a spec already on main is work, and the existing N3 rule judges it: the push must carry a landing
      spec it built, which the per-spec loop has reviewed. No new exemption is added. A spec-only push
      (spec files, projections and approval records only) keeps VELDO-0272's spec-only path unchanged, so a
      re-mark of specs on main still lands on the owner's approval.
    falsified_by: >
      Row AC3 landing/slimmed-bundle: the same bundle rewrite with no ticket exits 1 naming
      proof/VELDO-9371/big.json as uncovered. Row AC3 landing/re-land names docs/guide.md as uncovered.
      Mutation land287-on-base-not-work (files of specs on main are not work) reds slimmed-bundle.
  - id: AC3
    text: >
      A landing spec whose proof bundle the push does not change (ready, nothing built) is judged as the
      spec-only path judges it: the owner approval its computed flag requires, with the push's committers
      standing in for the missing producer in the self-approval test, and no review. It covers no work.
    falsified_by: >
      Row AC3 landing/ready-no-work: a ready required spec with nothing built beside a reviewed ticket
      exits 0 with an owner approval naming it, exits 1 owner approval missing with none, exits 1 when the
      approver is the push's committer, and code beside only that spec exits 1 as uncovered. Mutations
      land287-unbuilt-reviewed (it needs a review) and land287-unbuilt-covers-work (it covers work) red it.
  - id: AC4
    text: >
      approval_flag_lowered does not judge a spec id that is absent both at the push base and at HEAD.
      Nothing on main has that id, so nothing on main loses its approval (a draft renumbered before it
      reached main). Every other lowering is judged as before.
    falsified_by: >
      Row AC3 lowered/renumbered-draft: a required draft added and renumbered inside the push exits 0; the
      same renumbering of a required spec on main exits 1 approval_flag_lowered. Mutation
      land287-renumbered-lowered (the filter off) reds it. Every VELDO-0272 row of suite 129 still passes,
      and finding 272's 34 falsifiers are still rejected.
required_evidence: [unit, integration]
rollback: >
  Revert the commit. landing_specs again counts every non-draft spec whose files the push touches, and the
  suite rows and falsifiers go with it. No stored record carries anything this change writes.
---

## Intent

landing-c was refused by the VELDO-0272 landing rule for a reason the rule never meant
(~/projects/myday/research/claude-runs/landing-c-policy-refusal-2026-11-09.md). The rule counted every
non-draft spec whose spec file or proof file the push touched as a spec the push lands. Fifteen of
landing-c's 24 such specs were already on main and were in the push only because another ticket edited
one of their files, and three were ready specs with nothing built. Each was asked for a fresh review and a
proof producer that cannot honestly exist, and their missing producers voided the owner's approval of the
protected paths. A draft renumbered inside the push (VELDO-0271 to VELDO-0272) was refused as a lowered
approval although main never had it.

Owner decision: Dmitry, Telegram 40127 (the question) and 40128 ("Fix."), 2026-11-09. This is his
approval for the spec to be ready; it changes the approval rule he approved on 40124.

## Design

A spec lands when the push brings it to main. A spec already on main lands nothing; an edit to one of its
files belongs to the ticket that made the edit, so it is work that ticket's review must cover. VELDO-0270's
slimming of other specs' proof bundles is covered by 0270's review, and the lead's front matter edits by
the batch's reviewed tickets.

A ready spec with nothing built has no producer and no review to give, which is the spec-only path's
situation, so it is judged the same way. Because it builds nothing, it does not give the producer and does
not cover work: a push whose only landing specs are unbuilt and that changes anything else is refused, as
before.

Re-land (a spec on main whose work is built again) fails closed: its files are work, and another reviewed
landing spec in the push has to cover them.

A spec-only push of files of specs on main (the VELDO-0272 re-mark design) is unchanged: it lands no work,
and it is judged for the owner approval each spec's flag requires and for lowerings.

## Out of scope

Recording manifests, verdicts and per-spec owner approvals for landing-c's tickets; guard 2 of the push
guard; any change to the validator, the executor or the daily summary.

## What the reviewer judges

- No spec already on main can land through this rule, and none of its files escapes the N3 coverage rule
  in a push that is not spec-only.
- An unbuilt ready spec gets no review exemption that lets work through.
- The absent-at-both filter cannot hide a lowering of a spec main has.

## History

2026-11-09: written ready by the lead's builder from the owner's decision, Telegram 40127 and 40128
("Fix."), and the landing-c refusal analysis cited in Intent.
