---
schema: veldo.spec/v1
id: VELDO-0274
title: The VELDO-0127 factory fixture removes every systemd slice it creates, on success, failure and interruption, for every suite that starts it
status: ready
risk: standard
owner: dmitry
human_approval: not_required
lane: standalone
depends_on: [VELDO-0127]
placement: [enforcement]
protected_paths: []
footprint:
  - "proof/VELDO-0127/factory.py"
  - "scripts/suites/86_veldo_0127_agent_configuration.py"
  - "scripts/suites/88_veldo_0127_feature_defaults.py"
  - "scripts/suites/89_veldo_0127_feature_listing.py"
  - "scripts/suites/90_veldo_0127_feature_profile.py"
  - "scripts/suites/*_veldo_0274_*.py"
  - "scripts/suites/manifest.json"
  - "specs/VELDO-0274-suites-that-start-the-0127-factory-remove-every-systemd-slice-they-create.md"
  - "specs/index.md"
  - "proof/VELDO-0274/**"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
behavior_bearing: true
observability:
  logs: >
    The factory prints one line when it stops a slice left by an earlier run whose process is gone,
    naming the slice; nothing on the ordinary path.
  metrics: >
    None added.
  traces: >
    None added.
  error_taxonomy: >
    None added. A slice that cannot be stopped at teardown is a red row naming it, never silence.
acceptance_criteria:
  - id: AC1
    text: >
      proof/VELDO-0127/factory.py owns the lifetime of the slice it names (veldo0127-<pid>.slice): the
      factory is a context manager whose exit stops the slice with systemctl --user stop and confirms it
      is no longer loaded, whatever the body did, and suites 86, 88, 89 and 90, every suite that starts the
      factory today, use it that way. The stop calls in suite 86's finally block go; no suite stops the
      slice itself.
    falsified_by: >
      A new suite starts the factory in a child process, launches one fake engine into the slice, and then
      (a) returns, (b) raises: in both cases systemctl --user list-units --all shows no unit named by that
      child's slice afterwards. Registered mutation from a green baseline: the context manager's exit skips
      the stop: both rows go red.
  - id: AC2
    text: >
      Interruption does not leak a slice. While the factory is open it handles SIGTERM, SIGINT and SIGHUP
      by stopping its slice and then re-raising the signal's default action, and on entry it stops every
      veldo0127-<pid>.slice whose pid is not a live process, which covers a run killed by SIGKILL or a
      gate timeout. A slice of a live process is never touched.
    falsified_by: >
      The suite sends SIGTERM to a child inside the factory: no slice of that child remains. It plants a
      slice named for a dead pid and one for a live sleeper, enters the factory, and requires the first
      gone and the second still loaded. Registered mutations: (1) the signal handler is not installed: the
      SIGTERM row goes red; (2) the entry sweep ignores pid liveness: the live-slice row goes red.
  - id: AC3
    text: >
      A leak is caught by the gate. After the unit stage's last suite runs, a row requires that no
      veldo0127-* slice whose pid belongs to this run remains loaded in the user manager.
    falsified_by: >
      Registered mutation: suite 88 is changed to start the factory without the context manager: the
      end-of-run row goes red naming the leaked slice.
required_evidence: [unit]
rollback: Revert the commit; the suites go back to their own teardown and slices may leak again.
---

## Intent

Fix the defect in the weight audit's item L: veldo0127-* slices left in the owner's systemd user manager
(39 found on 2026-11-07).

## Context

Verified on main at afa292f0, and where the audit's fact differs:

- The slice is created by proof/VELDO-0127/factory.py (slice_name = 'veldo0127-' + pid + '.slice'),
  not by suite 86 alone. Four suites start that factory: 86 (agent configuration), 88 (feature
  defaults), 89 (feature listing) and 90 (feature profile).
- Only suite 86 stops the slice, in a finally block, so it leaks only when the run is killed. Suites 88,
  89 and 90 never stop it: their finally blocks close store connections only. So every run of 88 to 90
  leaks one slice; the audit attributes the leak to suite 86.
- On 2026-11-06 no veldo0127-* unit was loaded on the host (systemctl --user list-units --all), so the
  39 had been cleaned by then; the defect stands in the code.

## Out of scope

Other fixtures' slices; the containment profile in .veldo/control_containment.py.

## What the reviewer judges

- Normal use: the unit stage and a developer running one suite.
- Every exit path of every factory user stops the slice; the sweep never touches a live run's slice.
- Out of review scope: per the template.

## History

2026-11-07: drafted by the lead under the owner's narrowed approval scope (Telegram 39708, 39710). A
draft.

2026-11-07: ready by the lead under the owner's narrowed approval scope (Telegram 39708): test machinery and cleanup, no money, security, schema or infrastructure decision.

2026-11-07: footprint gains the suite registration files (scripts/suites/manifest.json, requires.json and scripts/check_teeth_mutations.py where missing), by the lead under Telegram 39708 (mechanical, ACs unchanged): selftest refuses a suite file the manifest does not enumerate, so a ticket that adds a suite must register it (VELDO-0272 build stopped on this, proof/VELDO-0272/README.md).
