# VELDO-0358 brief F: the service, client and loop path

Scope: revision-notes section 3.3, brief F. Suites 66_veldo_0047_authority, 71_veldo_0138_channel_service,
83_veldo_0154_factory_loop, 86_veldo_0189_engine_upgrade and 110_veldo_0143_new_project, with
proof/VELDO-0152/fixture.py; engine modules control_service, control_client, control_client_api, control_store,
control_factory_setup_upgrade and control_workflow_cycle_pm (canon in engine/.veldo, synced copies in .veldo).
Criteria AC10 and AC15 for these suites. Built on fb7705e1. Nothing here ran scripts/verify.sh.

## What was built

| Part | Where | What it does |
| - | - | - |
| Timers table entries (AC15) | engine modules | control_client SEND_SECONDS (send and inspect default) and SERVE_READ_SECONDS (serve_one's read and reply); control_service REPLY_SECONDS, SYSTEMCTL_SECONDS, KEYGEN_SECONDS, PRINCIPALS_SECONDS, RECONCILE_SECONDS; control_store BUSY_SECONDS; control_client_api HINT_READ_SECONDS, HINT_CLOSE_SECONDS (its authority calls take the client's default); control_factory_setup_upgrade ANSWER_SECONDS, RESTORE_SECONDS. Each is read where it is armed (`timer(name)`); a copy read alone, with no table beside it, keeps its own values |
| Profile in the service | control_service.serve | The configuration's `timers_profile`, else the manager environment's VELDO_TIMERS_PROFILE, applied before anything is armed; the start record (observation `timers`) carries the effective values |
| Events the suites wait on | control_service | `STATUS=... channel passes N` (sd_notify) after each channel pass; `pending_wakes` in the loop status, for the idle answer |
| Role budget by profile | proof/VELDO-0152/fixture.py | `role_seconds` (default 100, unchanged for suites 93 and 116); suite 110 passes the wait hang bound; control_workflow_cycle_pm takes the dispatch deadline from it, unchanged |

## The suites (design 4.2)

| Suite | Converted | New rows |
| - | - | - |
| 71 | no budget and no returning wait: store changes awaited on the authority's write-ahead file, passes on the service's STATUS notification, READY on the notify socket kept open, the stop on the pidfd; every wait impossible when the service process has ended; no 30 s readiness loop, no select 0.2 | timers/profile-applied, wave1/no-sites |
| 66_veldo_0047 | the second instance's refusal awaited on its exit, its READY=1 (on a notify socket of the suite's own) the terminal condition (no 8 s wait); the unexpected exit read when the unit leaves active, woken by the main process's exit and the unit group's removal (no 1.5 s window); client, reader and child bounds at the hang bound; the launch deadline an hour away | timers/profile-applied (in-process tables, the service's start record, and the timeout the client's send armed on its socket), wave1/no-sites |
| 83 | no 100 s budget, no 45 s rows deadline, no 8 s waits: a pass awaited on the pass log, impossible on the service's idle answer or exit; the start absence closed by the first pass; the receiver-death absence closed by a pass the suite causes; the stop row asserts the order (asked, ended before the pass was logged), not 8 s; the reset watch closed by the next pass, its length from the passes' own times; the fake's gates on inotify | timers/profile-applied |
| 86_veldo_0189 | the bridge's listener shut down and its thread joined (residue: green); readiness and exits on the notify socket and pidfd, no kill after a short wait; child bounds at the hang bound; no row timing | timers/profile-applied |
| 110 | the serve-loop loops wait on the socket and the provisioners' pipes (no 120 s deadline, no 5 s select) and end when no pipe is left; the agent thread joined after its socket woke it; the role budget at the hang bound | timers/profile-applied |

Row labels: rows-kept.txt (every suite keeps every base row). Census: the five suites and the fixture have no site;
the engine files keep only the two accept-interval cadences of design 4.8 (lead item 4). By the landing order rule
the 133 baseline entries (138 sites) this change removed are lowered (lower_baseline.py.txt); checks.txt.

## Falsifiers (brief F's block in scripts/check_teeth_mutations.py)

| Mutant | Suite | Row | Verdict (mutants.txt) |
| - | - | - | - |
| timers358-profile-skips-client (the specification's) | 66_veldo_0047 | timers/profile-applied | rejected, assertion |
| timers358-service-profile-ignored | 71 | timers/profile-applied | rejected, unproven (lead item 3) |
| timers358-reply-literal | 71 | wave1/no-sites | rejected, unproven |
| wave358-budget-restored (suite 71's budget back) | 66_veldo_0047 | wave1/no-sites | rejected, assertion |
| wave358-window-restored (suite 66's 1.5 s window back) | 71 | wave1/no-sites | rejected, unproven |

The other 177 registered cases of these suites were not run through the driver here (time on a shared host);
their anchors are untouched by this change except where restated above. That run is the lead's.

## Runs

- suites.txt: each suite alone at 5bc570a0, plus 93 and 116 (the fixture's other users) and 36 (lead item 1b).
- loaded-runs.txt: 250 runs under the generator (slowdown 4.8, every generator alive): 249 with no failed and no
  hung row. The red: suite 83 run 9, loop/reset-timer-wake (the reset pass offered nothing). Likely cause, not
  proven: the first run's account release refused by control_launch's ORPHAN_SECONDS (5 s, brief E's timer, design
  4.8 names suite 83 on its path), leaving the account busy at the reset with no later wake. Brief E's event-based
  release is being run in a scratch copy (lead item 6b). Not fixed by a bound or a retry.
- Full unit leg: see lead item 8.

Items for the lead: lead-items.md.
