---
schema: veldo.spec/v1
id: VELDO-0354
title: "Space requests from the You screen, and waiting runs in a group of their own"
status: ready
risk: standard
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0319]
placement: [engine]
protected_paths: ["scripts/gate_unconfined.json"]
footprint:
  - "engine/ui/src/views/YouView.vue"
  - "engine/ui/src/views/RunsView.vue"
  - "engine/ui/src/views/SpaceView.vue"
  - "engine/ui/src/features/run/**"
  - "engine/ui/src/features/space/**"
  - "engine/ui/src/stores/runs.ts"
  - "engine/ui/src/api/reads.ts"
  - "engine/ui/docs/views/runs.md"
  - "engine/ui/docs/views/space.md"
  - "engine/ui/docs/views/shell.md"
  - "engine/ui/docs/ui/run-list.md"
  - "engine/ui/e2e/**"
  - "scripts/suites/*_veldo_0354_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/gate_unconfined.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0354-space-requests-from-the-you-screen-and-waiting-runs-in-a-group-of-their-own.md"
  - "specs/index.md"
  - "proof/VELDO-0354/**"
behavior_bearing: true
observability:
  logs: >
    None. The ticket adds no command and no read model; both screens use the reads VELDO-0319 built.
  error_taxonomy: >
    None of its own. A read that fails shows the screen's error state, as every screen does.
acceptance_criteria:
  - id: AC1
    text: >
      The You screen links to the Space screen among its factory links. When the signed-in owner has
      open space requests, the You screen also says how many wait for an answer, and that line opens the
      Space screen's Pending removal list showing only the items with an open request. A request that
      was answered is not counted. A member who is not the owner sees the link and no count
    falsified_by: >
      Each of these turns a row of its own red. Count every request the item ever had: the row answers
      one of two and still reads two. Open the Space screen unfiltered: the row finds an item with no
      request in the list
  - id: AC2
    text: >
      The runs list has a group "Waiting for space", between Active and Stopped, that holds each run
      waiting on a pool with its one line of need, free, held and floor. A waiting run is no longer
      listed under Stopped, and the header's summary counts it apart. The group is not shown when
      nothing waits
    falsified_by: >
      Leave waiting runs with the stopped ones; the row finds the fixture's waiting run under Stopped
      and fails
  - id: AC3
    text: >
      Both follow the record stream. When a waiting run is admitted it leaves the group and appears
      under Active, and when a request is answered the You screen's count drops, each without a reload
      and with nothing read on a timer
    falsified_by: >
      Read once when the screen opens; the row admits the hold and still finds the run in the waiting
      group
required_evidence: [unit, ui_states]
rollback: >
  Revert the change. The You screen has no Space link, and a waiting run is listed under Stopped, as
  after VELDO-0319.
---

## Intent

Two places where VELDO-0319's screen is hard to reach or says the wrong thing. On a phone the Space
screen has no entry in the bottom bar and no link on the You screen, so an owner with a space request
to answer has to type the address. And a run that waits for space is listed under Stopped, which it is
not.

## Context

Found by the independent review of VELDO-0319 (review-veldo-0319.md): the minor finding M3 ("The
waiting run is listed in the runs screen's Stopped card. It is wrong in meaning, though AC4 is met")
and the not-built list (the You screen link, the waiting-runs group). VELDO-0319's History records why
neither was built: YouView.vue and RunsView.vue were outside its footprint.

## Design

The design is docs/design/VELDO-0295-design.md, section 10 (console): "the runs list shows a waiting
run's reason in one line". The house rules of engine/ui/CLAUDE.md bind this ticket: a page per screen
kept true, and the browser states at four widths in light and dark.

No read and no command is added. The count on the You screen is read from space.pending, the read
VELDO-0319 built, through the same live read the Space screen uses. The requests themselves are
answered on the Decisions screen as today; the Space screen lists each with its worktrees and links
there. The filter is a query on the Space screen's own route, so the router does not change.

A waiting run is a hold with no dispatch (VELDO-0319 AC4), so it has no run to open. Its row in the new
group is the row VELDO-0319 built, moved.

Rows this ticket changes, by name. In engine/ui/e2e/space.spec.ts, the test ac4/runs-list, which is row
ac4/runs-list of scripts/suites/150_veldo_0319_space_ui.py: the waiting run's row is looked for in the
waiting group, under the same title, with its numbers and text unchanged. The suite file itself does not
change, and ui/api-only, which compares its row list with that spec file's titles, stays green. In
engine/ui/src/features/run/runs.spec.ts, "lists a run that waits for space as a row of its own, after the
live runs, with no run to open" (the run now goes to the waiting group) and, in runsSummary, "counts the
rows shown and their distinct projects and hosts, skipping blanks" if the waiting runs are counted apart
there. The teeth case space319-run-row-without-its-hold, anchored in features/run/runs.ts, keeps its
anchor or is re-anchored on the same code with the same target row, and the teeth of finding 319 are
run. The You screen's entry in engine/ui/e2e/layout.spec.ts (no overflow, no overlap, no small target at
the phone widths) stays as written and must stay green with the new link and count.

This ticket's own browser rows live in a spec file of their own, engine/ui/e2e/you-space.spec.ts, run by
this ticket's own UI suite.

Protected path. This ticket's UI suite needs system Chrome, so it needs an entry in
scripts/gate_unconfined.json, which is protected: the owner approves that entry at landing.

Footprint. The two views, the runs list's feature folder and store, the Space screen's filter, the
pages of the three screens and of the runs list component, the browser tests, and the ticket's suite,
proof and spec. No engine module.

## History

- 2026-11-16: drafted from the review of VELDO-0319. Not filed. The number was checked free on every
  ref of the repository.
- 2026-11-16: reviewed. The rows changed are named (the e2e test ac4/runs-list and two vitest cases);
  150_veldo_0319_space_ui.py and the router left the footprint because neither changes; the 319 teeth
  anchor in runs.ts and the You screen's layout row are stated; the browser rows get a spec file of
  their own.
