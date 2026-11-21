# Brief E: items for the lead

1. Suite 106 is not in the proven set yet, through files no brief owns. It reuses suite 85's installed-host
   fixture (proof/VELDO-0185/fixture.py runs scripts/suites/85_veldo_0171_setup_api.py) and so opens
   scripts/suites/85_veldo_0171_setup_api.py (21 sites), scripts/suites/support/v73_authority.py (8),
   scripts/suites/support/setup_runtime.py (5) and proof/VELDO-0172/compare_formats.py (4). None is in the
   specification's footprint or in any brief's files, so they were not touched (brief rule: stop and report).
   Suite 106's own file has no site. Converting them is a footprint decision (wave 2, or this specification).
   Suite 78 opens proof/VELDO-0172/compare_formats.py too (the mutation observer's record; selftest's own record
   did not list it), so its 36 cases are kill_by unproven as well. Suites 62 and 63 open only themselves and the
   support modules.

2. Census gap (brief B's tool): R3 reads shared.wait_for's bound only as a number, and its bound is the tuple
   (seconds, origin), so `wait_for(cond, (10.0, '...'), what)` is not a site. Since brief A the tuple bounds
   nothing (it is kept in the report as data), so no wait is shortened by it, but AC10's falsifier "restore the
   ten second bound of marker_for" had to be written as the clock-bounded poll it once was.

3. waits.Stamp has no epoch accessor. A suite that hands the product a wall time as data (`now=`, a deadline
   an hour away) reads it as `datetime.fromisoformat(WAITS.stamp().iso()...)`. A `Stamp.wall()` in brief A's
   module would say the same in one call.

4. The service's own start record (control_service, brief F) is not written by this brief; suite 106's
   service process therefore runs its own timers at production values while its receivers run under the
   profile (their configuration). Brief F's start record and profile would close it for 106.

5. RECEIVER_EXIT_SECONDS keeps its production value of 2 s as a table entry; the wait for the receiver is now
   its pidfd and the kill comes only after the bound. Design 4.8 lists the event with the wait hang bound as the
   bound; the specification's falsifier (timers358-literal-kept) reads it from the table. The production value
   is the owner's choice; under every suite's profile it is the wait hang bound.

6. The receiver now also waits for its own exit after its last report (`exited`, `unknown`) before the kill,
   where it was killed at once unless its output had already ended. Its end (closing the store, removing its
   run directory) is therefore no longer cut short by the runner.

7. Suite 63's cpu-cap fixture ('burn') still loops on the clock inside fixture text: it is the subject of the
   cpu-cap row (usage against wall time) and the census does not read clocks in strings.

8. Release acts this change needs (any change to control_launch or the engine modules does): proof/VELDO-0127's
   qualify resource fixtures (suite 126, qualify/reproduces) and its live captures (suite 86_veldo_0127,
   live/claude and live/codex) are bound to these modules' digests. Precedents: fe9eb598 (rerun qualify on the
   recorded engines) and f5055400 (live recapture, owner approval). Both suites are green at the base.

9. The scaffold change (a48602c9) is in engine/.veldo/init_scaffold.py, which no brief lists: the engine modules
   now load timers.py, so an adopter's installation must lay it down (suites 66_veldo_0047 and 82_veldo_0129).

10. Suite 62 dispatch/owner-stop was red once in 50 at slowdown 7.9 (runs.md, red-62-owner-stop.txt). Cause not
    established; open.
