# VELDO-0167 main integration

Merge commit: 2370298a4c89d273ebda476a9c56820601c6425e.
Main merged: 298d0fd2. Original seam fixes: e2892514 and 66110bab, superseded
by b32b7d0d after independent review. See review-repair-report.md for the current
design and its scoped checks; the original integration checks below are historical.

Conflict resolutions:

- scripts/check_teeth_mutations.py: retained all 0167 mutations and main's intake
  companion metadata. Both metadata passes follow every registration. Syntax-tree
  comparison found zero missing registration calls from either parent.
- scripts/suites/manifest.json: retained the 0167 suite and main's 0151, 0088 and
  0152 entries, with all other main entries unchanged in the merge.
- scripts/suites/requires.json: regenerated from the merged manifest with run_scope;
  no hand edits. The merged inventory has 146 suites.

Seam audit and fix:

- Read the spec footprint, compared both branches from f1e1abb9, and searched all
  production modules and proof/suite callers for record configuration, recorder,
  hint, service and receiver construction and consumption.
- Factory setup, the API host and installed configuration, record preflight and
  engine upgrade retain the shared directory and additive configuration rules.
  The installed service still multiplexes record hints through its private API
  subscriber registry, with separate record and journal counters.
- Main's PM and intake paths read Line.records through the receiver's directory
  resolver and consume the committed execution record. Main's specialist, tool
  registry, re-land, containment and heartbeat additions keep these interfaces.
  Canonical engine and repository copies of the eleven seam modules match.
- The historical running-host row caught main's 0152 intake declaration adding a
  writer to an immutable existing declaration, preventing the restarted API from
  opening. Independent review rejected the initial intake-record workaround.
  The store now permits a strict command superset for the same owner, module and
  digest, subject to the existing binding check. Upgrade rebinding records the
  previous commands and switch back restores them. Routes execute intake_route;
  the discriminator and compatibility branch are removed. Suite 93 starts with
  the actual pre-route engine's declaration and reattaches it after switch back.
- The 0167 installation fixture already constructs inert CLI bytes with the 0172
  shared fake_formats helper. Its teardown now reports conform_fake through the
  suite's explicit fake/capture row before removing those bytes. These inert
  executables emit no vendor events, so their comparison credits zero events.
- Syntax-tree comparison retained every original check/expect call in suites 91
  (0167), 93 (0152) and 85 (0171). The historical restart check also retains its
  assertion and now reports the API refusal on failure.

Scoped checks:

26 selected suites passed, with 561 suite assertions and 1237 reported
assertions including repeated shared preambles; zero failures in the final runs.
Each suite was invoked individually and serially through selftest with its suite
selector. These are partial runs, not a gate result. Counts below include the
shared preamble; merge-checks.json also records each suite-only count.

- 50_git_environment: 30 passed, 0 failed.
- 62_veldo_0039_dispatch: 47 passed, 0 failed.
- 63_veldo_0040_containment: 80 passed, 0 failed.
- 67_veldo_0041_heartbeat: 49 passed, 0 failed.
- 68_veldo_0126_intake: 44 passed, 0 failed.
- 71_veldo_0130_api: 68 passed, 0 failed.
- 71_veldo_0138_channel_service: 39 passed, 0 failed.
- 72_veldo_0128_reports: 44 passed, 0 failed.
- 73_veldo_0139_factory_setup: 43 passed, 0 failed.
- 74_veldo_0140_standing_delegation: 35 passed, 0 failed.
- 82_veldo_0129_worker_wiring: 55 passed, 0 failed.
- 82_veldo_0141_execution_record: 66 passed, 0 failed.
- 82_veldo_0144_mcp_catalog: 55 passed, 0 failed.
- 82_veldo_0165_launch_hygiene: 49 passed, 0 failed.
- 82_veldo_0172_live_formats: 30 passed, 0 failed.
- 82_veldo_0173_tool_registry: 37 passed, 0 failed.
- 83_veldo_0154_factory_loop: 39 passed, 0 failed.
- 85_veldo_0171_setup_api: 44 passed, 0 failed.
- 86_veldo_0148_re_land: 51 passed, 0 failed.
- 86_veldo_0168_text: 52 passed, 0 failed.
- 86_veldo_0186_setup_assets: 37 passed, 0 failed.
- 86_veldo_0189_engine_upgrade: 58 passed, 0 failed.
- 91_veldo_0151_specialists: 51 passed, 0 failed.
- 91_veldo_0167_setup_records: 35 passed, 0 failed.
- 92_veldo_0088_pm_cycles: 51 passed, 0 failed.
- 93_veldo_0152_intake_routes: 48 passed, 0 failed.

Repository validation (all) and the standalone Git subprocess boundary check both
exit 0. The gate, whole selftest and global mutation executables were not run.
Initial 0167 runs exposed the installed ownership conflict. An intermediate
new regression compared declarations from different fixture stores; that test
setup was corrected. All original route assertions passed throughout that test
iteration. The final 0152, 0167 and historical upgrade suites were rerun after the
production compatibility fix. Existing proof artifacts were retained separately.

Stale VELDO-0127 captures referencing control_launch.py, left unchanged:

- ../VELDO-0127/claude-live.json
- ../VELDO-0127/codex-live.json
- ../VELDO-0127/codex-loopback.json
- ../VELDO-0127/codex-direct-loopback.json
- ../VELDO-0127/resources-gpt-5.5-none.json
- ../VELDO-0127/resources-gpt-5.5-selected.json
- ../VELDO-0127/resources-gpt-6-astra-none.json
- ../VELDO-0127/resources-gpt-6-astra-selected.json
