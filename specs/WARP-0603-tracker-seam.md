---
schema: veldo.spec/v1
id: WARP-0603
title: Provider-agnostic tracker adapter seam and a deterministic FakeTracker
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0006
work: W3
plan_revision: 1
depends_on: [WARP-0601]
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: An abstract TrackerAdapter seam declares the vendor-neutral operations intake and the
      mirror need and nothing more - the reads list_intake_items() and read_item(id), and the
      writes comment(id, text), set_status(id, mapped_status), create_or_update_epic(...) and
      create_or_update_child(...) - as the single boundary both tracker edges stand on. The base
      owns the shared logic (input validation by name, the write audit, the fail-loud guard) and
      each surface primitive raises NotImplementedError, so a real adapter supplies only the
      primitives and inherits every guarantee.
  - id: AC2
    text: A deterministic in-memory FakeTracker implements the seam with no network and no
      credentials - an internal dict of items, epics, children, and their statuses, transitions,
      and comments - so intake (list and read items) and the mirror (comment, set status, create
      or update an epic and its children) are exercised end to end offline in the gate.
  - id: AC3
    text: The seam is provider-agnostic - it carries zero dependency on any one tracker (a real
      Jira adapter is the later WARP-0604 item behind this same seam) - and READS are
      side-effect-free while WRITES are explicit: every write goes through a base method that
      appends to a base-owned write audit that no read ever touches, so "reads do not mutate,
      writes are explicit" is provable against the seam and not against one backend.
  - id: AC4
    text: The FakeTracker is deterministic and idempotent where the mirror relies on it, with the
      semantics documented - set_status is idempotent by target state (setting the status an
      object already holds records no transition and returns False, a real move records one
      transition and returns True), comment is append-only but key-idempotent (a comment carrying
      an idempotency key posts at most once so a closing comment survives at-least-once event
      replay, a keyless comment always appends), and create_or_update_epic and
      create_or_update_child are upserts keyed by a stable caller identity (a plan id, a work item
      id) so a re-run updates in place and never forks a second epic.
  - id: AC5
    text: A selftest drives the FakeTracker through the full seam surface and asserts each
      operation's observable effect, and is non-tautological - a comment then a read shows the
      comment (a read reflects a prior write), a status set then a read shows the new status,
      repeating a status set adds no second transition, a keyed comment does not double-post, an
      upsert re-run yields one object not two, a run of reads leaves the write audit unchanged
      while a write grows it, and a write to an object the tracker does not hold fails loud by
      name.
required_evidence: [unit]
rollback: git revert; additive - a new .veldo/tracker_adapter.py, a selftest block, one capability
  entry in both capabilities.yaml copies, and this spec; no protected path; pure stdlib, no network.
---

## Intent

The tracker integration has two edges the method already names: INTAKE (an external report or a
requirements page becomes a routing-resolved VELDO spec draft) and MIRROR (a one-way, effectively
read-only projection of spec and plan status back onto a ticket and an epic). Both edges must
stand on a boundary that knows nothing about any one vendor, so the first tracker (Jira Cloud in
WARP-0604) and a later one (Jira Data Center) are implementations behind the SAME seam, never the
design. This item builds that seam and a deterministic fake so intake and mirror are provable
offline before any line of live-tracker code exists.

## Context

W3 of PLAN-0006, depending on the routing resolver (WARP-0601). The resolver answers WHICH repo a
ticket targets and WHICH tracker and project serves a repo; this seam answers HOW a tracker is
read and written. It sits alongside .veldo/tracker.py and, like it, is pure stdlib with no network
and fails closed by name rather than guessing. The shape deliberately mirrors the environment
provisioning seam in .veldo/env_provision.py (WARP-0406): an abstract base that owns the lifecycle
and the cross-cutting guarantees, a subclass that implements only the surface primitives, and a
deterministic in-memory fake that makes the guarantees gate-testable with no external dependency.

Intake (WARP-0604) and the spec mirror (WARP-0605) both consume this seam; the plan/epic mirror
(WARP-0606) uses create_or_update_epic and create_or_update_child; the conformance selftest
(WARP-0608) drives the whole surface over the FakeTracker.

## Out of scope

No Jira, Confluence, or any live tracker code (that is WARP-0604 onward). No intake pipeline
wiring and no event-driven mirror consumer (WARP-0604, WARP-0605, WARP-0606). No status mapping
config (the mirror maps VELDO status onto the project's statuses; this seam accepts an
already-mapped status string). No auth or secrets handling (capabilities-not-credentials is the
live adapter's concern).

## Notes

The base owns the write audit precisely so "reads are side-effect-free, writes are explicit" is
mechanically true regardless of backend: a subclass cannot route a write around the audit, the
same way env_provision's leak accounting re-observes the real surface rather than trusting
bookkeeping. A write to an object the tracker does not hold raises TrackerItemNotFound and a
malformed argument raises TrackerAdapterError, so a mirror bug surfaces by name instead of a
silent no-op that reads as success.

Idempotency semantics are documented on the seam because the mirror depends on them: set_status
is idempotent by target state and returns whether it changed anything, so a replayed lifecycle
event does not stack duplicate transitions; comment is key-idempotent so a closing comment posts
exactly once under at-least-once delivery; epic and child creation are upserts keyed by a stable
caller identity so re-running a plan mirror updates in place and never forks a second epic. The
FakeTracker derives each object id deterministically from that key.
