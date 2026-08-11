---
schema: veldo.spec/v1
id: WARP-0613
title: veldo jira snapshot - reconcile the board to the CURRENT repository state (every plan and spec
  projected from its DECLARED file status, standalone specs included), the snapshot half of the
  snapshot-then-subscribe pattern that complements the event-driven mirror
status: shipped
risk: standard - this composes on the released tracker foundation (PLAN-0006 seam/mirror + PLAN-0010
  live edges) and on the just-landed board bootstrap (WARP-0612), and is REPO-ONLY build machinery (it
  lives in the same tracker_jira_init.py / tracker_adapter.py the bootstrap does, inside the single
  tracker architecture area). It touches NO protected path (verify.sh, veldo-guard.sh, policy.yaml,
  policy_check.py and their template twins are untouched) and nothing in the production-support safety
  core (the executor, whitelist, two-key rule, kill switch, or ladder), so per policy.yaml the floor is
  standard. Like the bootstrap it performs live external writes at run time (upserting epics/children
  and setting their status), but that path is REFERENCE-WIRED exactly like the shipped bootstrap and the
  live mirror runner: it is never exercised in the gate (the FakeTracker path is), it fails closed
  without a token, and running it live against a real board is a separate, explicit, human-driven act,
  not part of landing this spec. The mechanical footprint stays inside the single tracker area, so it
  crosses no boundary and the footprint tier floor does not elevate it
owner: dmitry
human_approval: not_required
lane: standalone
placement: [tracker]
footprint:
  - .veldo/tracker_jira_init.py
  - .veldo/tracker_adapter.py
  - .veldo/capabilities.yaml
  - engine/.veldo/capabilities.yaml
  - packs/*/.veldo/capabilities.yaml
  - scripts/selftest.py
  - specs/WARP-0613-jira-snapshot-current-state-reconcile.md
  - specs/index.md
  - proof/WARP-0613/**
protected_paths: []
behavior_bearing: true
observability:
  logs: The snapshot emits a structured report of exactly what reached the board (epics upserted,
    created vs reused; children upserted, created vs reused; standalone specs projected as top-level
    tasks; status transitions made; items left unset because their declared status has no VELDO mapping),
    so a stranger can see what one reconcile pass did from the report alone; the CLI prints that summary
    as JSON. The event-mirror report is unchanged.
  error_taxonomy: A malformed status_map fails loud by name (MirrorError, reused from the mirror, not a
    second validator), an unresolved live token is a fail-closed adapter error, and a repo not wired for
    the tracker (no .veldo/trackers.json) is a clean, honestly-reported no-op. A plan or spec whose
    declared status has no VELDO mapping is NOT an error - it is left unset (never an invented
    transition), which the report counts so a human sees it.
acceptance_criteria:
  - id: AC1
    text: The snapshot is GENERIC and reads every input BY REFERENCE, reusing the shipped mirror's own
      readers rather than reinventing them - build_spec_index and build_plan_index read the repository
      (the single source of truth), resolve_status_map resolves the per-org VELDO-status -> tracker-status
      map, and the tracker connection is read from .veldo/trackers.json. tracker_jira_init.py carries no
      company-specific or board-specific literal (grep-clean for the org/board name and domain), and a
      repo with no tracker config is a clean no-op reported honestly (never an error).
  - id: AC2
    text: It PROJECTS THE DECLARED CURRENT STATE. For every plan (excluding the reserved PLAN-0000
      scaffold, filtered by _is_scaffold_id, never by a company/board value) it upserts the plan's epic
      keyed by plan id - the SAME stable marker the epic mirror uses, so the two converge and never fork
      - and sets the epic's status from the plan's DECLARED file status through FILE_STATUS_TO_VELDO and
      the status_map. For every spec it upserts the spec's child and sets the child's status from the
      spec's DECLARED file status the same way. A plan or spec whose declared status has NO
      FILE_STATUS_TO_VELDO entry (draft, in_progress, proven, closed) leaves the status UNSET - the
      snapshot never invents a transition outside the mapped VELDO set (NG4), the same guarantee the
      event mirror upholds.
  - id: AC3
    text: It COVERS WHAT THE EVENT STREAM STRUCTURALLY CANNOT. FILE_STATUS_TO_VELDO is BUILT FROM the
      mirror's shipped SPEC_STATUS_TO_VELDO (so the two agree byte-for-byte on the shared statuses
      shipped/blocked/ready and the shared constant is copied, never mutated) and EXTENDS it with the two
      current-state statuses no lifecycle event carries: a spec parked in review projects to the VELDO
      status in_review, and a released plan projects its epic to shipped. So a board reconciled by the
      snapshot reflects a spec currently in review and a released plan even when the event stream holds no
      event that would move them, which the event mirror (driven only by spec.ready/blocked/shipped and a
      recorded verdict) cannot do from the stream alone.
  - id: AC4
    text: It places STANDALONE specs correctly and reports created-vs-reused WITHOUT a redundant write. A
      spec that declares no plan (it is in no plan's work list) is projected as a TOP-LEVEL item of the
      child issue type - a Task with no epic parent - via create_or_update_child with epic_key None, so it
      is never forced under a spurious epic and never mapped to a wrong type; its id carries no epic
      segment so it cannot collide with an under-epic child. find_epic and find_child are SIDE-EFFECT-FREE
      reads (the base seam's write audit is byte-unchanged after they run), the read counterparts to the
      upserts keyed the same way, so the snapshot tells a created object from a reused one for its report
      without a second write.
  - id: AC5
    text: It is IDEMPOTENT and ONE-WAY. Re-running the snapshot over the same repository forks no epic or
      child, records no duplicate transition, and leaves the board byte-identical (the upserts are keyed,
      set_status is a no-op when unchanged). It writes ONLY through the provisioner seam (the keyed
      upserts and set_status) and NEVER mutates a spec, a plan, or the in-memory indices it reads - there
      is no code path here that writes back into the repository, so the repository stays the single source
      of truth (C1). Because the snapshot projects the DECLARED file status, when it runs after the event
      mirror it makes the board agree with the file even if an event would have said otherwise - the
      declared repository state wins, which is the source-of-truth invariant, not a conflict.
  - id: AC6
    text: It is wired as ONE command, veldo jira snapshot (a subcommand of the repo-only
      tracker_jira_init.py that bin/veldo already routes 'jira' to, behind the SAME existence guard as veldo
      jira init and veldo mirror; bin/veldo itself is UNCHANGED and stays byte-identical across its copies).
      veldo jira snapshot --dry-run previews the whole reconcile over an in-memory FakeTracker with no
      network and no token; without it it builds the SAME reference live provisioner veldo jira init builds
      and FAILS CLOSED when no token resolves. veldo jira init ALSO runs the snapshot as the FINAL step of
      its one-pass bootstrap (provision, then event-mirror catch-up, then snapshot reconcile), so a single
      init yields a board that reflects the current declared state; both remain idempotent so a re-run of
      either changes nothing. It creates no timer, daemon, or auto-start and spawns nothing detached (NG1).
  - id: AC7
    text: A selftest drives the WHOLE snapshot over the deterministic FakeTracker offline (no network) and
      is NON-TAUTOLOGICAL. A spec whose declared status is review shows the mapped In Review status; a
      released plan's epic shows the mapped Shipped status; a standalone spec (no plan) becomes a
      top-level task with its mapped status and under NO epic; a plan/spec whose declared status has no
      VELDO mapping leaves its status unset (no invented transition); a re-run forks nothing and leaves the
      board byte-identical; and the spec/plan indices are byte-unchanged afterward (one-way). Each load-
      bearing behavior carries an in-memory source-mutation TOOTH that turns its assertion red while the
      on-disk module stays byte-unchanged: neutralizing the review->in_review extension makes the in-review
      spec lose its status; neutralizing the released->shipped extension makes the released epic lose its
      shipped status; neutralizing the epic_key-None top-level branch forces the standalone spec under a
      spurious epic (or collides its id); and neutralizing the keyed-upsert reuse makes a re-run fork or
      duplicate. None of the teeth is vacuous.
required_evidence: [unit]
rollback: git revert; additive - a new snapshot_from_repo projection and a veldo jira snapshot subcommand
  in the repo-only tracker_jira_init.py, two side-effect-free find primitives plus top-level-task support
  on the repo-only tracker_adapter.py seam and its FakeTracker, one extra reconcile step appended to the
  existing bootstrap() (init still provisions and mirrors exactly as before, then reconciles), one new
  tracker_board_snapshot capability entry (all eight capabilities.yaml copies, byte-identical), a selftest
  block, and this spec; no protected path; pure stdlib; the live provisioner is reference-wired and never
  run in the gate. bin/veldo is untouched.
---

## Intent

The board must reflect REALITY the moment it is stood up, not just the replay of an event log. WARP-0612
provisions the board and reuses the event-driven mirror to project lifecycle events onto it - but the
event mirror is driven ONLY by the events that were emitted, and two facts a human reads off the board
have no event of their own: a spec sitting in review right now (there is no recurring "still in review"
event), and a plan that has been released (the epic mirror derives shipped from the work burn-down, not
from the plan's own released status). A board bootstrapped from events alone therefore shows a stale or
missing status for exactly those items. This spec adds the SNAPSHOT: a reconcile that reads the current
declared state of every plan and spec from the repository and projects it onto the board, so the board is
correct on start and after any reconcile.

This is the snapshot half of the correct snapshot-then-subscribe pattern (feedback_right_architecture_no_
shortcuts): snapshot the full current state on start, then let the event mirror keep it current as events
land. It is NOT a poller and NOT a second source of truth - it reads the repository (the source of truth)
and writes only the tracker, one-directionally, idempotently.

## Context

This composes on the RELEASED tracker foundation and the just-landed WARP-0612 board bootstrap, and reuses
them rather than reinventing anything: the provider-agnostic adapter seam and FakeTracker (WARP-0603), the
mirror's repository readers and status projection (build_spec_index / build_plan_index / resolve_status_map
/ SPEC_STATUS_TO_VELDO, WARP-0605/0606), and the bootstrap's config + live provisioner (WARP-0612). It lands
as a STANDALONE tracker-lineage spec (WARP-0613, after WARP-0612), the same convention as the standalone
hardening/extension specs (WARP-0113, WARP-0411, WARP-1212). Like every other tracker module it is
REPO-ONLY build machinery; only .veldo/tracker.py is engine-synced, so the two repo-only modules this
touches are not, and the capability entry (documentation) is synced with its siblings.

## The gap this closes, precisely

The event mirror projects a status ONLY when an event carries it: spec.ready -> ready, spec.blocked ->
blocked, verdict.recorded -> in_review, spec.shipped -> shipped; and the epic mirror derives an epic's
status from whether every work item's spec has shipped. So from the stream alone:
- a spec whose CURRENT front-matter status is review, but whose verdict.recorded event is not in the
  stream being replayed (or predates it), shows no In Review;
- a plan whose CURRENT status is released, but whose work items are not all individually shipped in the
  burn-down, shows an open epic;
- a spec that belongs to no plan is skipped entirely by the mirror ("no plan, so no epic to place the
  child under"), so it never appears on the board at all.
The snapshot fixes all three by projecting the DECLARED current status (through FILE_STATUS_TO_VELDO, which
extends the mirror's projection with review->in_review and released->shipped) and by placing a plan-less
spec as a top-level task. It transitions only within the mapped VELDO set, so a declared status with no
mapping is left unset, never invented (NG4).

## Why standard risk

The change touches no protected path and nothing in the production-support safety core, so the policy floor
is standard. Its live writes are reference-wired exactly like the WARP-0612 bootstrap and the live mirror
runner: never run in the gate, fail closed without a token, and applied live only by an explicit human act.
The mechanical footprint stays inside the single tracker architecture area (the same two repo-only modules
the bootstrap lives in), so it crosses no boundary and the footprint tier floor does not raise it.

## Running it live

Against the live board (once WARP-0612 has stood it up), with the tracker wired in .veldo/trackers.json:
`veldo jira snapshot --dry-run` previews the reconcile offline, then `veldo jira snapshot` applies it live;
or simply `veldo jira init`, which now provisions, mirrors, and reconciles in one pass. The token is
resolved from the environment/secrets store named by token_ref (never a raw credential); it creates
nothing that runs on its own and a re-run reconciles.
