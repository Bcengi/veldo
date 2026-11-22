# Brief E: registered cases

## The mutation stage (mutation-stage.txt)

All 135 registered cases of suites 62, 63, 78 and 106 (brief E's three falsifiers among them), through the
gate's own driver and verdict rule (check_gate_mutations.py --case ...), at 06a092e7: 135 executed, 134
rejected, none hung_not_killed, no control_failed.

| Suite | Cases | kill_by |
| - | - | - |
| 62_veldo_0039_dispatch | 37 | assertion, all (wave358-latency-asserted and timers358-literal-kept among them) |
| 63_veldo_0040_containment | 41 of 42 | assertion (wave358-bound-restored among them) |
| 78_veldo_0060_claude_adapter | 36 | unproven: the suite opens proof/VELDO-0172/compare_formats.py, which has baseline entries (lead-items.md 1) |
| 106_veldo_0185_dispatch_setup | 20 | unproven: the suite opens suite 85's fixture files and compare_formats.py (lead-items.md 1) |

The survivor, containment-runtime-cap-one-second-late, made the cap late only at the old 1.2 s value; the row
judges the real 20 s firing by a lower bound only, so a late cap was not seen. Fixed in the commit after
06a092e7: the row reads RuntimeMaxUSec while the capped scope runs and requires the declared cap, and the
mutant is made at the cap the row uses. Its re-drive (with brief E's three falsifiers and the two restated
suite 62 cases) is in drive.txt when it has run; at the time of writing it was queued behind other builders'
host-heavy runs.

Restated cases (README.md): five anchors moved; dispatch-closed-output-late-deadline anchors the deadline's
judgment; dispatch261-stop-leaves-record-running ends the receiver on the stop instead of sleeping forever;
containment-runtime-cap-one-second-late at the row's cap. Each is rejected by assertion in the stage above
(the last one after its restatement, pending the re-drive).

## Round 2 (mutation-stage-r2.txt)

All 135 registered cases of suites 62, 63, 78 and 106 again through the gate's driver, at d1b18d13: 135 executed,
135 rejected, every one kill_by assertion, none hung_not_killed, no control_failed. The former survivor,
containment-runtime-cap-one-second-late, is rejected by VELDO-0040 containment/runtime-cap. Suites 78 (36 cases)
and 106 (20 cases) are kill_by assertion now that the files they open have no baseline entry (190c4e90).
The new row dispatch/owner-stop-ends-first is falsified by the code before 69961820 (r2-idle-and-falsifier.txt);
it is not a registered case.
