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
   Suite 129_veldo_0254_canary_launch needs the systemd user manager, as 85_veldo_0158 does, so it needs the same
   leg: `{"suite": "129_veldo_0254_canary_launch", "reason": "real launches in transient systemd scopes under the
   owner's user manager, as 85_veldo_0158"}`. Until then the teeth case delivery254-keystore-into-launch-canary
   stops at the driver's confined baseline (PermissionError on the runtime directory); its red was shown by hand.

## Depends on tickets not built here

2. AC1 canary row: built in fix round 1 as suite 129_veldo_0254_canary_launch (ruling (c) item 2). With canaries
   `fixture-mail` and `fixture-tracker` in the existing keystore (control_credential_keystore through a fake
   `secret-tool`) and no catalog server selected, real launches through the Runner, the receiver process and the
   trusted wrapper: an engine run and a conversation turn on each of claude_code and codex, a workflow step (the PM
   cycle's coordination dispatch, the same Runner.submit path) and a project process (the repository
   provisioner). Each dumps its environment, command line and every file it can read under its workspace and
   scratch, and none holds a canary, by substring and by the one scan entry holding them. With the AC1 falsifier
   applied by hand, ac1/canary-keystore, ac1/canary-engine-run, ac1/canary-conversation and
   ac1/canary-workflow-step go red (falsifier-ac1-canary.txt). Not covered: the LangGraph graph runner, which
   starts with a fixed environment and runs no engine, and the engine's temporary directory (the shared /tmp,
   since the wrapper strips TMPDIR). The declared fixture services of VELDO-0253 are not on this branch.
3. AC1 static row: it names exactly one site today, `control_launch.py:Receiver._spawn`, the VELDO-0158 keystore
   resolution for selected catalog servers. Removing it is VELDO-0257 (Out of scope here). Suite 127 accepts that
   one site only while it exists (PENDING_0257) and fails on any other. Until VELDO-0257 lands, AC1's claim does
   not hold for runs that select a credentialed catalog server. The launch-time scan of fix round 1 (ruling (a))
   likewise passes the values that path delivered itself (`Receiver.delivered`), as it passes the engine's own
   subscription token; every other credential in a run's final environment or command line refuses the launch.
4. AC2 exact match against the credentials held for the gate: `secret_scan.scan(held=...)` digests the values in
   process and never writes them, and the rows pass with fixture values. No production caller passes held
   values yet, because the gate's keystore (VELDO-0251, VELDO-0253) does not exist; the run-end, landing,
   setup and command triggers detect by format only until then.
5. AC2 owner notice through Veldo's own channel: closed in fix round 1. The lead widened the footprint to the one
   call site that sends it (review-2026-11-05.md, ruling (c)): `.veldo/control_service_channel.py` and its engine
   copy `engine/.veldo/control_service_channel.py`, where `Channel.tick` now also runs `Channel.tell_secrets`,
   which reads the installation's scan logs (`secret_scan.store_logs`) and tells the owner's enrolled chat once per
   scan that found a credential or failed (`secret_scan.notices`, masked findings only). The one new send makes
   `scripts/suites/86_veldo_0168_text.py`'s send inventory name it (one line, `Channel.tell_secrets`, and its
   `V.TEXT.message` route); that suite is outside the footprint and the line is the only change to it, listed here
   for the lead.

## Gaps of this build (no other ticket owns them)

6. Closed in fix round 1 (finding 1): the formats are `secret_scan.FORMATS` inside the module, the data file is gone,
   and suite 127's ac2/installed runs the owner's command, the run-end scan and the landing scan from the
   installed service layout (`control_service.closure` and its runtime assets). A run-end, landing or setup scan
   that fails is logged as `secret_scan_failed` to the owner's scan log and told to the owner (ac2/failure-visible).
7. Closed in fix round 1 (finding 2): a risky engine run's confined runner gets the dispatch's clone work tree, as
   `_engine_cwd` computes it, and the engine's client (`--client claude` or `--client codex`); suite 127's
   ac3/risky-spawn drives `Receiver._spawn` for a risky launch on each engine and for a conversation turn. The
   runner's self-test is taken once per receiver (finding 6, ac3/selftest-cached).
8. Project processes (the repository provisioner started by control_service_projects) are not runs the
   receiver accepts; they are not routed through the runner decision. The static row covers
   control_service_projects as a launch module.
9. The full gate was not run (instruction). Suites run are listed in the proof manifest and
   fix-round-1-suites.txt.
10. Fix round 1, finding 4: the run-end scan reads only the files the run added or changed in its clone's work tree
   and scratch and its conversation directory (a stat snapshot taken at the spawn), once its end is recorded and
   before the end is reported. The run's own directory is no longer read: it is removed before the end is
   recorded, so nothing in it outlives the run.
11. Fix round 1, a consequence of item 6: a setup scan that finds nothing no longer writes to the state root, so a
   re-run of setup still changes nothing (85_veldo_0171 rerun/changes-nothing). A setup scan with findings, or one
   that fails, is logged in full.
