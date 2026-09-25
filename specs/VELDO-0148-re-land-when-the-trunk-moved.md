---
schema: veldo.spec/v1
id: VELDO-0148
title: A land refused because another factory moved main is re-landed on the new tip, re-merged and re-gated, and nothing ever forces
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W108
plan_revision: 4
depends_on: [VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0154]
placement: [distribution, fleet, contracts, metrics]
protected_paths: []
footprint:
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "engine/.veldo/lander.py"
  - ".veldo/lander.py"
  - "packs/*/.veldo/lander.py"
  - "engine/.veldo/control_landing*.py"
  - ".veldo/control_landing*.py"
  - "packs/*/.veldo/control_landing*.py"
  - "engine/.veldo/control_effect_executor*.py"
  - ".veldo/control_effect_executor*.py"
  - "packs/*/.veldo/control_effect_executor*.py"
  - "engine/.veldo/control_service*.py"
  - ".veldo/control_service*.py"
  - "packs/*/.veldo/control_service*.py"
  - "scripts/suites/*_veldo_0148_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0148-re-land-when-the-trunk-moved.md"
  - "specs/index.md"
  - "proof/VELDO-0148/*"
behavior_bearing: true
observability:
  logs: >
    Record each refused publication with its watermark, the tip found and the classification, and each
    re-land dispatch with the unit, the original land dispatch it follows and the new watermark; never
    a credential.
  metrics: >
    Count publications refused as stale-subject, lease losses classified refused or unknown, and
    re-land dispatches per unit.
  traces: >
    Join each re-land dispatch to the refused publication it follows, the new candidate, its gate run
    and its compare-and-swap.
  error_taxonomy: >
    Distinguish stale subject at the listing, trunk moved after the listing, unknown publication, a
    re-merge conflict and a missing approval for the re-merged tree; none is recorded as landed.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: A publication refused as `stale-subject` because the trunk moved is followed by exactly one
      new land dispatch that re-merges and re-gates on the new tip, and nothing ever forces. Set and
      completeness: Against a disposable bare remote, land a unit whose trunk another push moves before
      the listing. The effect executor refuses the publication as `stale-subject` and the original land
      dispatch ends refused, with no new attempt under it (VELDO-0057 AC3). The factory loop (VELDO-0154
      AC1) then offers the land station again as a new land dispatch: a new watermark from the new main,
      the same re-merge, the gate run again from the trusted installation on the new candidate and a new
      compare-and-swap, which lands. A clean re-merge keeps review bound to the unchanged evidence
      commit; a real conflict sends the unit back to its builder as a new build dispatch told to merge
      the new main, and that build is reviewed again. No push is ever forced. Falsifier: Leave the land
      failed after a `stale-subject` refusal, offering no new land dispatch; the stale-subject re-land
      row must fail.
    falsified_by: >
      Leave the land failed after a `stale-subject` refusal, offering no new land dispatch; the
      stale-subject re-land row must fail.
  - id: AC2
    text: >
      Claim: A lease lost to another push between the listing and the push is classified as a refused
      publication when the new tip does not contain the candidate, and only a tip that contains it stays
      unknown. Set and completeness: Against a disposable bare remote, move the trunk between the
      listing and the push. The executor fetches the after-state tip into its publication clone; a
      commit that is neither the watermark nor the candidate and does not contain the candidate is a
      refused publication (trunk moved), followed by the re-land of AC1. Separately, make the after-state
      tip contain the candidate: that result stays `unknown`, judged per push URL, and stops under its
      original dispatch with a named stop and no new attempt. Falsifier: Move the remote trunk between
      the listing and the push and record the lease loss as `unknown`; the lease-window row must fail.
    falsified_by: >
      Move the remote trunk between the listing and the push and record the lease loss as `unknown`; the
      lease-window row must fail.
  - id: AC3
    text: >
      Claim: A unit that requires an approval asks once per re-land for a fresh grant bound to the
      re-merged tree, and the old grant never publishes the new candidate. Set and completeness: Re-land
      a unit whose policy requires an approval: observe one request for the re-merged candidate tree and
      no publication until it is granted; answer it, and the new compare-and-swap lands. Present the
      approval granted for the old candidate tree to the re-land's publication and require refusal by
      name with the trunk unchanged. Falsifier: Accept the approval bound to the old candidate tree for
      the re-merged tree; the fresh-grant row must fail.
    falsified_by: >
      Accept the approval bound to the old candidate tree for the re-merged tree; the fresh-grant row must
      fail.
required_evidence: [unit, integration]
rollback: >
  Stop offering re-land dispatches: a publication refused because the trunk moved stops under its
  original dispatch as it did before this concern, and every recorded dispatch, receipt and approval is
  kept. No automatic rollback is authorized.
---

## Intent

Each person runs their own factory, and the factories meet at Git main on the shared remote. A land must
survive another person's factory moving main between the land's start and its publication, without ever
forcing a push.

## Context

W108 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5 (the factory loop it
extends, VELDO-0154, is stage 5). Section 7 of the approved
[operating-model design](../docs/design/PLAN-0019-operating-model-design.md) (owner Telegram 29162) designs the re-land and gives its criterion and falsifier as an amendment of VELDO-0057. VELDO-0057
has landed with its proof, so this repository's convention puts that amendment in its own specification
that depends on it, and VELDO-0057 keeps its landed text.

What the code does today: the lander builds its candidate on a watermark, the trunk tip fetched once, and
merges the build onto it (`lander.py`). Publication is a compare-and-swap of that watermark: the effect
executor lists the destination and refuses with `stale-subject` if the trunk is no longer at the
watermark, and otherwise pushes with a lease on it (`control_effect_executor.py`). After a
`stale-subject` refusal the land is simply failed, and a failed or unknown publication stops under its
original dispatch with no new attempt (`control_landing.py`), so nothing re-lands on the new main; a move
between the listing and the push makes the lease reject the push, which the executor records as
`unknown`.

## Out of scope

A bound or backoff for a trunk that keeps moving under heavy contention (hardening); recovery of a lost or
ambiguous publication (Release 2); any change to VELDO-0057's criteria.

## What the reviewer judges

- Normal use: a colleague's factory lands on main while this factory's land is under way; the publication
  is refused because the trunk moved, and the loop re-lands the unit on the new main as a new land
  dispatch, re-merged and re-gated, and the second compare-and-swap lands. The owner sees each re-land as
  its own dispatch.
- Threat model: a refused land left failed or unknown instead of re-landed; a re-land that skips the
  re-merge or the gate on the new candidate; a forced push, or one that overwrites a trunk that moved; a
  lease loss recorded as unknown when the new tip does not contain the candidate, or as refused when it
  does; a new attempt under the original dispatch; an approval for the old tree used for the re-merged
  one; a conflicting re-merge landed without a new build and review. The owner's account, the store and
  the remote host are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); a trunk that
  keeps moving under heavy contention; recovery of a lost or ambiguous publication (Release 2); forged
  rows in our own store and files planted in the installed directory.

## Notes

The refused publication ends its own land dispatch; the re-land is a new dispatch under a new identity,
so VELDO-0057 AC3 ("an unconfirmed publication cannot establish completion or authorize another attempt")
holds unchanged for the original dispatch and for every unknown result. The factory loop offers the land
station again because the unit's last land ended refused; that offer is the loop's next-station rule in
the authority service (VELDO-0154 AC1), which this concern extends for a refused land. Approvals are bound
to the candidate tree, so the re-merged tree needs its own grant.

## History

2026-09-25: written for PLAN-0019 revision 4 from the approved operating-model design (Telegram 29162),
section 7(e), whose VELDO-0057 amendment is carried here whole because VELDO-0057 has landed. The
criterion text, its falsifier (move the remote trunk between the listing and the push; the re-land row
must fail if the unit is left unknown) and the approval rule are the design's, split into one criterion
each for the stale-subject re-land, the lease window and the fresh grant. A draft: only the owner
marks a specification ready.

2026-09-25, PLAN-0019 revision 4 review: the factory loop this concern extends is VELDO-0154, split
from VELDO-0129 (its former AC4 is VELDO-0154 AC1), so depends_on names VELDO-0154 in place of
VELDO-0129 and the loop references follow. Criterion meaning unchanged.
