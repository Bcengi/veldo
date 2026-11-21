# VELDO-0125 not brought onto the line, 2026-11-20

Source branch: `agent/codex/veldo-0125-b2` at 82074cf3 (2026-10-17), 99 commits not on the line, of
which 87 are the ticket's own (6196b2e5..82074cf3; the first eight are VELDO-0124 as it stood on
2026-10-10 and one is a merge of main at 9763249e). The line is 1142 commits past that base.
Tried on the line at 5bbbbb7d (space-0329b at 0b767d26 with VELDO-0111, VELDO-0117 and VELDO-0124
brought over). Nothing of VELDO-0125 is committed; this file is the only change.

## The conflict

VELDO-0125 and the VELDO-0124 now on the line are two different continuations of the same five
`project_runner_macos*.py` modules, and they disagree about the design, not about lines of text.

- VELDO-0125 was built on VELDO-0124 as of 2026-10-10 (7b70d125). From round 11 on it replaces the
  Mac runner's polling with exit events: profile schema v2 drops `heartbeat_seconds` and
  `heartbeat_window_seconds` from the required settings (`migrate`, "old qualification never binds
  its new digest"), the wrapper waits through `wait_file` and `wait_members` (kqueue), and the
  suites 103 and 104 are rewritten onto its own event fixture (`proof/VELDO-0125/macos_event_fixture.py`).
- VELDO-0124's rounds 2 and 3 (2026-10-28 and 2026-10-29, after VELDO-0125's last commit) were
  built on the heartbeat design. They keep both heartbeat settings as required, add
  `verify_evidence` (a qualification row is a reference to an evidence file under protected
  storage, with its digest), the refused Claude sandbox setting and the wrapper's recheck of it,
  and fifteen falsifiers over those rows.

Each side passes alone. Put together by a three-way port (base 7b70d125 for the Mac modules, base
9763249e for the rest), with every textual conflict resolved by keeping both sides:

| Suite, alone, on the port | Result |
| --- | --- |
| 105_veldo_0125_relay | 17 rows passed |
| 106_veldo_0125_routing | 161 rows passed, 85 failed |
| 104_veldo_0124_control | 1 row passed, 6 failed |
| 103_veldo_0124_macos | 28 rows passed, 2 failed |

Where the failures come from:

1. 78 rows of suite 106, the six of suite 104 and the receiver fixtures: every VELDO-0125 fixture
   builds a qualification whose rows are plain marks. VELDO-0124's `verify_evidence` refuses them
   (`missing_evidence:macos_qualification`). VELDO-0125's tests also change a profile and re-bind
   only `profile_digest`; under VELDO-0124 the evidence document binds the profile digest too, and
   a v1 profile migrated to v2 has a new digest that no retained evidence names. Whether a
   migrated profile needs new native evidence is the open question behind these rows.
2. `AC1/claude-wrapper-recheck` (suite 103): VELDO-0124's row runs the wrapper on Linux; the
   VELDO-0125 wrapper waits on `select.kqueue`, which Linux does not have.
   `AC1/claude-sandbox-refused` fails with it.
3. Which schema is the accepted one. VELDO-0124's amended specification and its native rows of
   2026-10-28 are for the profile with heartbeats. VELDO-0125's specification says heartbeat
   settings "remain accepted profile fields for compatibility" and healthy runs use exit events.
   One of the two has to be amended; that is the owner's decision, not a port.
4. Four rows of suite 106 fail with `'FactoryLoop' object has no attribute 'conversation'`: they
   drive a loop pass on an object the line's constructor did not build, and the line's pass now
   offers conversation turns (VELDO-0174).

## What did fit

Outside the Mac modules the port is mechanical, twelve conflicts, each resolved keeping both:

- `control_store.py`: grouped commands (`atomic`, savepoints) beside the line's `_begin` and
  `write_refusal` (VELDO-0261), so a grouped command still answers `store_busy`.
- `control_launch.py`: `RemoteLaunch` and `invoke_remote` beside the line's `receiver_log`
  (VELDO-0350); `Runner` takes `space` and the three routing arguments.
- `control_service.py`: the worker-receiver restriction ahead of the take-on branch (VELDO-0161);
  `finish_launch` carrying the line's orphan release, not applied to remote runs; a pass woken only
  by remote deadlines skips provisioning, working-tree watches (VELDO-0260) and conversation turns;
  the poll set keeps the space listener and the adoption timer and takes `next_timer`.
- New modules `control_routing.py`, `control_worker.py`, `control_worker_client.py`,
  `control_worker_outbox.py`, `control_worker_service.py` and suite 105 apply unchanged.

`RemoteLaunch` subclasses the line's `Launch`, which has since changed how a run's end is taken
(VELDO-0308, VELDO-0350 and the launch-wait change). Suite 105 passing does not cover that; the
rows that would (suite 106) are among those blocked above.

## Also open on the source branch

The branch has no `proof/VELDO-0125/manifest.json`. Its last round (22) records an unresolved
confined audit investigation. Its proof is 5.1 MB, 3.1 MB of it logs, against the 1 MB a ticket's
proof may take on the line.

## To unblock

Decide the Mac profile's schema (heartbeat settings required, or exit events with v2), then
rebuild VELDO-0125's fixtures on VELDO-0124's evidence references and give the wrapper's waits a
seam its Linux rows can drive. After that the port above can be repeated and suites 103 to 106
rerun. VELDO-0125 depends on VELDO-0124, VELDO-0039, VELDO-0047 and VELDO-0108, all on the line.

Lead decision, 2026-11-21 (bring-up part 2): not part of this run. The lead gives VELDO-0125 a separate port.
