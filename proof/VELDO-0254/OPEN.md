# VELDO-0254: what this build does not close

Built on agent/claude/veldo-0254 from ad5ba8cb. The dependencies VELDO-0251, VELDO-0252 and VELDO-0253 are not
on this branch (no spec file, no code), so the outside gate, its keystore of gate-held credentials and the
installation's declared services do not exist here. Only this ticket's own part is built; each missing piece is
listed with its owner.

## Blocks a green gate (owner action)

1. Suite 128_veldo_0254_confined_runner needs the gate's unconfined leg. Inside the gate's own confinement the
   namespace helper's root ownership is not visible: measured with the first host check (the helper's ownership,
   since replaced by the runner's own `namespace-selftest`), the teeth driver's confined baseline reported
   `confined_runner_unavailable:helper_untrusted` for this row while it was in suite 127. With the self-test
   check the confined-leg result is expected to be the same and was not measured. Listing the suite
   whole in `scripts/gate_unconfined.json` is a protected change this spec does not list, so it is the owner's:
   `{"suite": "128_veldo_0254_confined_runner", "reason": "nested namespace: starts the confined runner of
   VELDO-0208, whose helper cannot be judged inside the gate's confinement"}`. Suite 127 and all three mutation
   cases pass in the confined leg (teeth-mutations-254.txt).

## Depends on tickets not built here

2. AC1 canary row as the spec states it (canaries in the keystore for each declared fixture service, one launch
   of each kind on each engine, scan of everything the run can read). Declared services are VELDO-0253's and the
   gate is VELDO-0251's. Built: the scan over a fixture run's workspace, scratch, environment and command line
   (row ac1/canary-run), which finds a canary resolved into the environment or the command.
3. AC1 static row: it names exactly one site today, `control_launch.py:Receiver._spawn`, the VELDO-0158 keystore
   resolution for selected catalog servers. Removing it is VELDO-0257 (Out of scope here). Suite 127 accepts that
   one site only while it exists (PENDING_0257) and fails on any other. Until VELDO-0257 lands, AC1's claim does
   not hold for runs that select a credentialed catalog server.
4. AC2 exact match against the credentials held for the gate: `secret_scan.scan(held=...)` digests the values in
   process and never writes them, and the rows pass with fixture values. No production caller passes held
   values yet, because the gate's keystore (VELDO-0251, VELDO-0253) does not exist; the run-end, landing,
   setup and command triggers detect by format only until then.
5. AC2 owner notice through Veldo's own channel: the scan builds one masked notice per scan and calls the
   `notify` sink it is given (row ac2/run-end). The channel's outbound reports are control_telegram_report and
   control_service_channel, outside this footprint, so no production trigger passes a sink yet; the findings and
   the notice's absence are in the scan log.

## Gaps of this build (no other ticket owns them)

6. The installed service layout (control_service.layout, outside this footprint) copies the closure's modules
   and `runtime/` assets only, so `.veldo/secret_scan_patterns.json` does not reach an installed receiver; its
   run-end scan then fails, which is caught and noted on stderr (the run is unaffected). The fix is a layout
   change or the formats file under runtime/, both outside this footprint.
7. AC3 rows run the launcher's decision, refusal and argv (runner_decision, runner_refusal, runner_argv) and
   start the argv for real; they do not drive a whole Receiver launch. The static row ac3/one-decision shows
   Receiver.launch is the one caller and Receiver._spawn applies it. A risky engine run (pinned binary through
   the clone entrance) is wrapped and the wrapper still re-hashes the pinned engine inside the runner's argv,
   but the confined runner's grants for the clone root and the account profile are not exercised by any row.
8. Project processes (the repository provisioner started by control_service_projects) are not runs the
   receiver accepts; they are not routed through the runner decision. The static row covers
   control_service_projects as a launch module.
9. The full gate was not run (instruction). Suites run are listed in the proof manifest.
