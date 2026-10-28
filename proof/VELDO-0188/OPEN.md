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
with real provisioning and adoption. Suite 113 passes all 25 rows. Changed suites pass: 83 has 13 rows, 92 has 33, 93 has 24 and 110 has 109. Falsifier
runs are in progress under the blocking host gate lock. No waiver is claimed. The pinned capability reference and factory-only project cycles retain the
review's accepted interpretation. Testing follows owner rule 37191: ticket suite, changed suites and falsifiers.
