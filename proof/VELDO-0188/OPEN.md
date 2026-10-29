# VELDO-0188 round 2 open points

The owner requested removal of section 2 exceptions and repair of suites 83, 92, 93 and 110.
The specification footprint is unchanged. Files outside it required by that request:

- scripts/suites/83_veldo_0154_factory_loop.py
- scripts/suites/92_veldo_0088_pm_cycles.py
- scripts/suites/93_veldo_0152_intake_routes.py
- scripts/suites/110_veldo_0143_new_project.py
- proof/VELDO-0152/fixture.py (install before declaring store owners, so the process and setup use installed modules)

Owner approval of this footprint extension remains a landing requirement. The requested local repairs proceed.

Round 2 progress and evidence are recorded under round2. AC1 now runs the installed service as its own process,
with real provisioning and adoption. Suite 113 passes all 25 rows. Changed suites pass: 83 has 13 rows, 92 has 33, 93 has 24 and 110 has 109. Consumer falsifier
runs remain unexecuted: their blocking flock waited behind another host gate and was terminated before
spawning any test when handing back the approval blocker (round2/pending-verification.json). Suite 113 mutation verification awaits the protected
declaration approval described below. No waiver is claimed. The pinned capability reference and factory-only project cycles retain the
review's accepted interpretation. Testing follows owner rule 37191: ticket suite, changed suites and falsifiers.

The installed-process mutation controls require the host user manager. Suite 113 is absent from the protected
`scripts/gate_unconfined.json` declaration, while suites 92, 93 and 110 already have entries. The exact proposed
addition is in round2/proposed-gate-entry.patch. This is a sixth file outside the footprint, pending explicit
owner approval before changing its confinement declaration. The failed confined controls are retained; they
are not accepted mutation evidence.

## Round 3 (2026-10-28)

The owner approved the gate declaration (Telegram 37451 and 37452). scripts/gate_unconfined.json lists
116_veldo_0188_project_lines whole, and the specification's footprint and protected paths name that file.
The coordinator receipt for all nine registered cases passed (falsifiers-receipt.json). Suite 92 was changed
again: one variant now reports line/store-staffing, so its falsifier names a single row. The footprint extension
to suites 83, 92, 93 and 110 and to proof/VELDO-0152/fixture.py was accepted in the round 2 fix-check. Nothing
in this ticket is open; landing still needs independent review and the batch gate.
