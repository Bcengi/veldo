# VELDO-0227: factory setup tells the installed API where the factory UI is

## What changed

- `control_factory_setup_api.process_config` writes `api.ui` = `<workspace>/.veldo/ui` (where
  `init_scaffold.py --ui` lays the build) into the 0600 veldo.api_process/v1 file. That file is the only place
  the installed API learns its UI directory (`control_api_ui.directory` reads `api.ui`; setup never puts a UI in
  the installation's `bin/`).
- `process_config_state` / `lacks_only_ui`: on a re-run, an existing configuration that differs from what setup
  writes ONLY by lacking `api.ui` (same owner, mode 0600, every other key equal) is `upgrade`: setup rewrites it
  atomically with that key added and nothing else. Every other difference is still refused
  `invalid_input:state_root:differs:<path>`, as before.
- When the upgrade happens with the authority service and the API unit running, setup restarts the API unit once
  so it reads the new configuration (`api_start` done); a stopped API starts with the authority, as before.
- `api_report` (setup's answer, every run) carries `ui: {directory, state}`, where state is exactly one of
  `built UI present` (the directory holds index.html) or `no UI laid yet: run init_scaffold.py --ui <workspace>
  from a Veldo source checkout after npm ci && npm run build in engine/ui` (the workspace path filled in). No key
  or token is printed.

Files: `engine/.veldo/control_factory_setup.py`, `engine/.veldo/control_factory_setup_api.py` and their synced
copies under `.veldo/`; `scripts/suites/117_veldo_0227_ui_location.py`; `scripts/suites/manifest.json`;
`scripts/suites/requires.json` (regenerated); `scripts/check_teeth_mutations.py` (finding 227);
`proof/VELDO-0227/*`. `specs/index.md` regenerated, unchanged. All inside the declared footprint.

## Proof

Suite `117_veldo_0227_ui_location` (number 117 checked free on every local branch) reuses VELDO-0171's
installed-host fixture (suite 85's setup preamble and cleanup, as VELDO-0185 reuses it): the real setup module
through its command surface into scratch, its user manager stand-in running the installed authority and API units,
its Tailscale stand-in, HTTP to the installed API's loopback listener with the tailnet name as Host.

| Row | Criterion | What it shows |
| --- | --- | --- |
| ui/fresh-config | AC1 | a fresh setup's API configuration names `<workspace>/.veldo/ui`, inside `api` only, 0600, no UI in bin/ |
| ui/served | AC1 | the API answers `missing_evidence:ui_not_built`, then after `init_scaffold --ui` (lay_ui) GET / answers the laid index.html under the API's CSP, and the asset, with no edit |
| ui/report-absent | AC2 | with no UI laid the report names the directory and the exact "no UI laid yet" step |
| ui/report-present | AC2 | after laying, the report says "built UI present" |
| ui/rerun-unchanged | AC1 | a second run leaves the configuration byte for byte (`already_done`) and the UI still served |
| ui/upgrade-pre-change | AC1 | a host laid by the engine of 1aee02d4 (no `ui`): its API cannot find the UI; the re-run upgrades the file in place with only `api.ui` added, restarts the running API, which serves the UI; a further run changes nothing |
| ui/differs-refused | AC1 | a configuration lacking `ui` AND listening elsewhere, and one naming another UI directory, are refused by name and left as they are |

Green: `suite117-green.log` (commit 5dfd559d, 7 of 7 rows, 33 checks, 0 failed; every observation printed).
The first run (the content of e5e7f77b) had `ui/upgrade-pre-change` red for a fixture reason (the pre-change setup
was laid without the fixture's Git identity), fixed in 5dfd559d.

## Falsifiers

| Mutant (finding 227) | Declared falsifier | Target rows |
| --- | --- | --- |
| ui227-config-omits-ui | AC1: process_config omits the `ui` key | ui/fresh-config, ui/served |
| ui227-report-always-present | AC2: the report always says "built UI present" | ui/report-absent |
| ui227-pre-change-refused | AC1: a pre-change configuration is refused, not upgraded | ui/upgrade-pre-change |
| ui227-any-difference-upgraded | AC1: any other difference is overwritten | ui/differs-refused |

The coordinator (`check_gate_mutations.py --finding 227`) refused all four as invalid baselines, because the
confined leg cannot reach the user manager (`coordinator-confined-baseline-refused.log`; OPEN.md item A asks the
owner for the protected unconfined-list entry). The falsifiers are proven instead by the driver's own worker,
unconfined: `falsifiers.py`, receipt `falsifiers.json`, log `falsifiers.log`.

Result at commit 58a8c622 (`falsifiers.json`): 4 of 4 red under the mutant, green restored; each case's
baseline green before and after, the source file never edited (the driver's materialize writes the mutant to a
temporary copy the suite's production anchor is pointed at).

- ui227-config-omits-ui: ui/fresh-config red (the configuration names no UI: `None`), ui/served red (the fresh
  host's GET / answers `404 missing_evidence:ui_not_built`), the declared falsifier. The later rows also fail,
  as consequences: the suite's own differs row then pops a `ui` that is not there (KeyError) and the exercise ends.
- ui227-report-always-present: ui/report-absent red (the report says `built UI present` with no UI laid).
- ui227-pre-change-refused: ui/upgrade-pre-change red (the pre-change configuration refused
  `invalid_input:state_root:differs`).
- ui227-any-difference-upgraded: ui/differs-refused red (a configuration listening elsewhere is overwritten).

## Runs

Only suite 117 and the finding-227 mutants were run, each under `flock .gate.lock systemd-run --user ...
MemoryMax=16G`, never the full gate (owner rule 37191). Open items: `OPEN.md`.
