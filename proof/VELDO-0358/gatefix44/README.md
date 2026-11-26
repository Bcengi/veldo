# Stable load-memory baseline

Gate 22 recorded memory.high 1,738,427,596 and memory.peak 1,760,776,192.
Gate 23 applied 1,056,465,715: floor(60% of that capped peak), then recorded
1,060,237,312. Its four VELDO-0131 UI suites failed with JavaScript heap exhaustion.
The previous writer promoted every passing capped peak into the next pressure input.

The load record now separates the last observed peak from `memory_baseline`.
Only a passing leg whose generator explicitly reports `high: null` and a positive
integer peak can establish that baseline. A capped leg retains the baseline,
regardless of its own peak. Missing provenance is unknown, including every legacy
record on this host; it never supplies a pressure input. Timing observations remain
available for repetition planning.

Bootstrap follows the existing first-run policy: one run of the proven set with
CPU and disk load, without setting memory.high. On success its peak becomes the
baseline. Subsequent runs apply floor(60% of that uncapped peak), retaining all CPU,
disk and memory pressure settings. There is no periodic refresh of an unchanged
set. The baseline is scoped to authority checkout, slot count, and the set of
suite/confinement pairs. A changed suite membership or confinement assignment,
or a different slot count, requires another uncapped bootstrap. Repetitions do
not change set identity. Failed runs, failed load application, and missing peaks
cannot establish a baseline. A failed changed-set run invalidates the old set's
baseline; a failed same-set run retains its valid baseline.

For the next gate on this host, memory.high remains the kernel default `max`
(the leg passes None), because its existing cache record has no uncapped
provenance. After that bootstrap passes, the following gate applies 60% of its
measured peak. Its future numeric value cannot be known without that measurement;
no full leg was run for this fix and no host cache record was edited or removed.

The regression drives real run_load_proof decisions and persistence with a
controlled generator measurement seam. It checks two consecutive passing
pressured legs, matching legacy and explicitly capped records, changed sets and
slot counts, failed suites, missing peaks, and failed load application. On
6a204f341 the pressured requests are 600 then 369, and legacy requests 369 then
231; with the fix they are 600 then 600, and legacy requests None then 600.
The registered teeth restore the ratcheting consumer and the capped-baseline
writer independently. Existing assertions remain unchanged.
