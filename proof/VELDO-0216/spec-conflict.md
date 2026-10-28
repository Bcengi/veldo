# AC4 conflict for owner decision, round two

The specification is unchanged. This is a proposed amendment, not an approval.

The recorded 2026-10-25 leg durations, replayed through the production ledger on
20 CPU cores, 15 GiB available memory after the 1 GiB scope reserve, and 16 manager
slots, project **6932.501 seconds (115.54 minutes)** for graph execution. This
exceeds AC4's 6000 seconds by 932.501 seconds, before gate shell overhead,
contention, newer suites or attribution overhead. The old cold scheduler replay is
10726.032 seconds. The recorded full gate was 10718.80284181796 seconds; replay
uses the upper end of each short stage's recorded interval, so its serial sum is
not expected to equal the measured full gate.

Basis: serial-baseline.json, bound to the canonical source receipt digests;
round2/simulate.py calls the actual Ledger and node_claim methods. Its ordered
launch policy, dependencies, resource admission and mutation floor match run().
round2/schedule-red.json and round2/schedule-green.json record every interval,
claim, grant, refusal, release and peak. No actual gate was executed.

The remaining chain is mutation 5207.101 s, unit.unconfined 891.6 s, and
integration.unconfined 833.8 s. Both legs include suites 63 and 66, whose manifest
requires exclusive systemd_user_manager use. The current mutation coordinator
also runs their cases and controls. Before per-case admission is connected to the
gate ledger it must hold that aggregate manager exclusion for its entire lifetime.
Weakening it to shared would permit the exact disturbance the manifest forbids.
Confined unit and integration, lint and the other independent stages now overlap
mutation wherever summed CPU and memory permit.

The host lock is a different resource. gate_host.py owns it across the entire
gate; all nodes share that inherited ownership. They neither acquire the real
lock again nor claim to be independent gates. Fixture host-lock tests use scratch
locks. The ledger now distinguishes shared and exclusive host-lock use from user
manager slots. This does not remove a real manager conflict.

The authority graph seeds cold CPU rates from recorded CPU seconds / wall seconds,
rounded upward to tenths with a one-core minimum. It seeds memory from recorded
cache-inclusive cgroup peaks rounded upward to GiB. These are labelled startup
estimates, not invented anonymous-memory measurements or hard future upper bounds.
The three stages whose durations were coalesced use their 5.1 s interval ceiling
and one CPU core; they have no measured CPU rate. Runtime receipts still measure
anonymous memory, and fresh source-bound measurements take precedence. The source
change that invalidates a runtime cache no longer forces full-capacity claims.

Proposed owner amendment: retain AC1 through AC3 and require this ticket to show
independent stages admitted concurrently on the qualification host, with a full
fresh gate ceiling of 7500 seconds, subject to canonical measurement. Move the
6000-second qualification to the first stack containing gate-wide per-worker
manager admission (VELDO-0219) and, if required by measurement, narrowed exclusive
shard holds (VELDO-0221). The 7500 figure is a proposal with 567.499 seconds of
headroom above replay, not a measured guarantee. Owner approval and a canonical
force-fresh run remain required. Owner rule 37191 forbids that run in this round.
