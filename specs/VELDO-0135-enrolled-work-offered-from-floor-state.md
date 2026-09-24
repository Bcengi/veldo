---
schema: veldo.spec/v1
id: VELDO-0135
title: Enrolled work is offered from its authoritative floor state, not the spec status line
status: ready
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W98
plan_revision: 3
depends_on: [VELDO-0049, VELDO-0052]
placement: [loop, contracts]
protected_paths: []
footprint:
  - "plans/PLAN-0019-dark-factory.md"
  - "engine/.veldo/frontier.py"
  - ".veldo/frontier.py"
  - "packs/*/.veldo/frontier.py"
  - "engine/.veldo/work.py"
  - ".veldo/work.py"
  - "packs/*/.veldo/work.py"
  - "engine/.veldo/dispatch.py"
  - ".veldo/dispatch.py"
  - "scripts/suites/*_veldo_0135_*.py"
  - "scripts/suites/63_veldo_0049_floor.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0135-enrolled-work-offered-from-floor-state.md"
  - "specs/index.md"
  - "proof/VELDO-0135/*"
behavior_bearing: true
observability:
  logs: >
    Record, for each offered or withheld unit of enrolled work, the unit, the station offered, the
    floor record version it was read from, and a named reason when nothing is offered.
  metrics: >
    Count units offered per station from floor state, and units withheld with each named reason.
  traces: >
    Join each offer to the floor record version and the dispatch it led to, by identity.
  error_taxonomy: >
    Distinguish missing authority, stale subject, unavailable service and invalid input; an unreadable
    floor record never becomes an offer.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: For an enrolled repository the frontier offers each unit the station its floor record
      is in (build when ready or returned, review when an accepted build awaits review), and never the
      station the spec file's status line names. Set and completeness: every floor state of VELDO-0049's
      transition table, over a real enrolled repository whose spec file still says ready. Falsifier:
      read the lane status from the spec file for an enrolled unit; the floor-state offer check must
      fail.
    falsified_by: >
      Read the lane status from the spec file for an enrolled unit; the floor-state offer check must fail.
  - id: AC2
    text: >
      Claim: The work loop's claimability check for enrolled work reads the same floor record, so a
      unit handed off, landed or waiting on an open finding is not claimed again. Set and completeness:
      handoff, landed, returned with an open finding, and review awaiting a second reviewer. Falsifier:
      treat a handed-off unit as claimable; the no-reclaim check must fail.
    falsified_by: >
      Treat a handed-off unit as claimable; the no-reclaim check must fail.
  - id: AC3
    text: >
      Claim: The full enrolled floor runs end to end through the ordinary loop: build, accepted build,
      review offered to a separate reviewer, handoff and landing, with no direct call. Non-enrolled
      repositories keep today's status-line behavior unchanged. Set and completeness: one enrolled unit
      driven by the real work loop, plus the existing non-enrolled loop suites. Falsifier: offer an
      enrolled unit as build again after its build is accepted; the end-to-end floor check must fail.
    falsified_by: >
      Offer an enrolled unit as build again after its build is accepted; the end-to-end floor check must fail.
required_evidence: [unit, integration]
rollback: >
  Disable floor-state offers for enrolled repositories; enrolled work then stops being offered, which
  is refused by name, never offered from the status line.
---

## Intent

Enrolled work must move through the factory's own loop. VELDO-0049 made the authority's floor record
the only source of an enrolled unit's state and stopped the dispatcher writing the spec file's status
line, but the frontier and the work loop still read that line, so after a build is accepted no review
is ever offered and the enrolled journey stops.

## Context

W98 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 1. Found by the
scoped review of VELDO-0049 on 2026-09-24: `.veldo/frontier.py` offers a review unit only when the
lane status is review, which it reads from the spec file, and `.veldo/work.py` checks claimability the
same way. Both files are in VELDO-0052's footprint, which does not depend on VELDO-0049, so this item
is ordered after both.

## Out of scope

Recovery of an interrupted transition (Release 2). Intake of a finding disposition from Telegram or the
API (VELDO-0126 and its dependants). Any change to the floor record's schema or transitions.

## What the reviewer judges

- Normal use: the ordinary work loop running an enrolled repository through build, review, handoff and
  landing, and a non-enrolled repository running as it does today.
- Threat model: a unit offered at the wrong station, a finished unit claimed again, and a status line
  that disagrees with the floor record. The owner's account, the store and the gate are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962), crash recovery
  between transitions (Release 2), forged rows in our own store.

## Notes

Read the floor record through the authority's read path, never by opening the store for writing.

## History

2026-09-24: new draft, from the scoped review of VELDO-0049 (the enrolled journey stalls after build
acceptance because the frontier and work loop read the spec status line).

2026-09-24: the owner marked this specification ready (Telegram 29041).

2026-09-24: built on branch build-veldo-0135 from 5ba4a02, finishing a work in progress cut off by a usage
limit. The frontier and the work loop read each enrolled unit's floor record through the authority's read
path; a returned unit is offered to build (its disposition binds to the rebuilt commit), a unit with the
review count met and a finding open waits, and a claim client's stop about one unadmitted unit is withheld
by name. Suite 67_veldo_0135_offers (4 assertion rows) is red by assertion at 5ba4a02 and green here; 13
registered mutations; proof in proof/VELDO-0135/.

2026-09-24: the scoped review of e5b4dad found that after the owner resolves the last open finding the
unit reaches handoff only through a new review the review policy does not require: the frontier offers the
review station when the handoff rule passes, but the dispatcher's review station assigned and launched a
reviewer before it ever asked for the handoff. dispatch.py (both copies) joins this footprint for that
reason: the review station now asks the authority's handoff rule first (FloorAuthority.handoff_refusals, the
same question the frontier asks) and hands off without a reviewer when it passes; only when it does not is a
review assigned and launched. The work loop's failed set is keyed by unit and station, so a unit whose
review failed is still rebuilt in the same run. New row offers/finding-path (suite 67 now 5 assertion rows),
red by assertion at e5b4dad; 16 registered mutations.

2026-09-24: suite 63_veldo_0049_floor joins this footprint because its floor/finding-not-erased row asserted
the defect above: after the owner resolved the finding it required a third reviewer, reviewer-d, in the
handoff. The row now requires the handoff on the two passing reviews that stand, with no reviewer launched.
