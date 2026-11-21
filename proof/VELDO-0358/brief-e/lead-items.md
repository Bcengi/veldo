# Brief E: items for the lead

1. Closed in round 2 (lead decision: brief E converts them). The files suites 78 and 106 open with sites,
   scripts/suites/85_veldo_0171_setup_api.py, support/setup_runtime.py, support/v73_authority.py and
   proof/VELDO-0172/compare_formats.py, wait on events (190c4e90); their 38 baseline sites are lowered. The 42
   suites that open them were run (runs.md, round 2); suite 86_veldo_0168, which froze v73_authority's clock by
   patching its time module, now patches its one wall-time reader (481bd6fc).

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

10. Closed in round 2: a product race in Runner.honor_stops (a stop result refused stale_version by the
    receiver's own exit commit), fixed in 69961820 with the row dispatch/owner-stop-ends-first (runs.md, round 2).

11. The same order exists in control_api_authority (not brief E's file): the API's stop_worker asks the receiver
    (self.stop) and then calls dispatches.stop_result with the version read at that moment, so a receiver that
    records the worker's end in between makes the result stale_version, which the API returns as a refusal of an
    owner's stop that was in fact asked. The fix is the same as Runner._stop_result; no row reaches it today.

12. Brief F's lead item 6b is fixed here (69961820, d1b18d13); suite 83 with both briefs: 10 of 10 idle, 49 of 50
    loaded with no hang. Its one loaded red is loop/reset-timer-wake, brief F's row (runs.md, round 2).

13. Every proof run of round 2 is local: pc2's Python has no os.pidfd_open and its runs have no systemd user
    manager, so these suites cannot run there (runs.md, round 2).
