---
schema: veldo.spec/v1
id: VELDO-0227
title: Factory setup tells the installed API where the factory UI is, so no one edits its configuration by hand
status: ready
risk: standard
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0145, VELDO-0171]
placement: [engine, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_factory_setup*.py"
  - ".veldo/control_factory_setup*.py"
  - "packs/*/.veldo/control_factory_setup*.py"
  - "scripts/suites/*_veldo_0227_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0227-factory-setup-tells-the-api-where-the-ui-is.md"
  - "specs/index.md"
  - "proof/VELDO-0227/*"
behavior_bearing: true
observability:
  logs: >
    Setup's report names the UI directory it wrote into the API process configuration and whether a
    built UI is there now; it never prints a key or a token.
  metrics: >
    None beyond setup's existing report: a one-shot host command.
  traces: >
    The API process configuration file itself is the record of what setup wrote.
  error_taxonomy: >
    Distinguish a UI directory that is named and built, named but not yet built (the API answers
    missing_evidence:ui_not_built until init_scaffold --ui lays it), and an existing configuration that
    differs from what setup would write in anything other than the `ui` key (refused, as today).
acceptance_criteria:
  - id: AC1
    text: >
      Claim: On a host set up by `veldo factory setup`, the installed API serves the factory UI laid by
      `init_scaffold.py --ui <workspace>` with no manual edit of its configuration. Set and completeness:
      the API process configuration (control_factory_setup_api.process_config, the veldo.api_process/v1
      file) is the only place the installed API learns its UI directory (control_api_ui.directory reads
      `api.ui`, else a directory beside the installed module in bin/, which setup never fills); setup
      writes `api.ui` as `<workspace>/.veldo/ui` on a fresh host and on a host set up before this change
      (whose configuration lacks the key: setup adds it and nothing else), and a second run changes
      nothing. Measured on a scratch host root with the setup suite's user manager stand-in: fresh setup,
      `init_scaffold.py --ui`, then GET / on the installed API's listener answers the laid index.html under
      the API's content security policy; and a configuration written by the pre-change setup is upgraded
      in place with only `api.ui` added.
    falsified_by: >
      process_config omits the `ui` key; the fresh-host row's GET / answers missing_evidence:ui_not_built.
  - id: AC2
    text: >
      Claim: setup says where the UI goes and whether it is there. Set: its report on every run names the
      UI directory and one of "built UI present" or "no UI laid yet: run init_scaffold.py --ui <workspace>
      from a Veldo source checkout after npm ci && npm run build in engine/ui". Completeness: the two
      states are the only ones (the directory holds an index.html or it does not).
    falsified_by: >
      The report always says "built UI present"; the row with no laid UI goes red.
required_evidence: [unit]
rollback: >
  Revert the setup change; an installed configuration that carries `api.ui` still works with the
  pre-change API (it reads the key since VELDO-0145), and the manual step in proof/VELDO-0145/OPEN.md
  applies again.
---

## Intent

VELDO-0145 built the factory UI and taught the API to serve it from a named directory, and its scaffold
lays the built UI at `<workspace>/.veldo/ui` on request (`init_scaffold.py --ui`). But `veldo factory
setup` installs the API from a copy of the modules in the installation's `bin/`, which carries no UI, and
writes the API process configuration without a `ui` key, so on a real host the API answers
`missing_evidence:ui_not_built` until someone edits that file by hand and restarts the unit
(proof/VELDO-0145/OPEN.md, item 1 step 2). This spec removes that hand edit: setup names the UI directory.

## Context

- control_factory_setup_api.process_config builds the veldo.api_process/v1 file; control_client_api.open_api
  passes its `api` object to control_api.ControlApi, which keeps `ui` (VELDO-0145).
- Setup refuses an existing file that differs from what it would write (file_state). A host set up before
  this change has a configuration without `ui`; AC1 requires that exact difference to be upgraded, not
  refused, and every other difference to stay refused.
- The UI is built and laid separately (npm in engine/ui, then init_scaffold --ui), because a composed pack
  carries no UI source. Setup does not build or copy it; it only names where it is.

## Out of scope

Building the UI during setup, copying the build into `bin/`, Tailscale Serve changes, and the phone
sign-in leg (VELDO-0145 AC1, run by the owner).

## What the reviewer judges

- Normal use: the owner runs `veldo factory setup` on the factory host, before or after laying the UI.
- Threat model: the same account as VELDO-0171; files planted in the owner's workspace are not an attacker.
- Out of review scope: a workspace path that changes after setup (setup is re-run), and hosts whose
  configuration was edited by hand beyond the `ui` key.

## Notes

Drafted in VELDO-0145 round 3 at the reviewer's request (fix-check 2026-10-28, F1 and OPEN item 2). Not
implemented; the owner approves it before it is claimed.

## History

2026-10-29: marked ready by the owner (Telegram 37476 and 37477, "Ok to build").
