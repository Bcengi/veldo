---
schema: veldo.spec/v1
id: VELDO-0258
title: Veldo's own outside calls (tracker, repository provisioner, landing push, the owner's channel and its doorbell) are made by the service outside the gate and never from a run, with credentials only from the keystore and settings only from the installation repository
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0144, VELDO-0253, VELDO-0254]
placement: [contracts, engine, distribution]
protected_paths: [".veldo/secretref.py", "engine/.veldo/secretref.py"]
footprint:
  - ".veldo/tracker*.py"
  - "engine/.veldo/tracker*.py"
  - ".veldo/trackers.json"
  - "engine/.veldo/trackers.json"
  - ".veldo/request_doorbell.py"
  - "engine/.veldo/request_doorbell.py"
  - ".veldo/control_repository_provisioner.py"
  - "engine/.veldo/control_repository_provisioner.py"
  - ".veldo/control_landing_station.py"
  - "engine/.veldo/control_landing_station.py"
  - ".veldo/control_service_channel.py"
  - "engine/.veldo/control_service_channel.py"
  - ".veldo/control_plane_calls.json"
  - "engine/.veldo/control_plane_calls.json"
  - "engine/.veldo/installation_schema/**"
  - ".veldo/installation_schema/**"
  - "engine/.veldo/installation_template/**"
  - ".veldo/installation_template/**"
  - "docs/outside-services.md"
  - "scripts/suites/*_veldo_0258_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0258-veldo-own-outside-calls-take-credentials-from-the-keystore-and-settings-from-the-installation.md"
  - "specs/index.md"
  - "proof/VELDO-0258/**"
  - ".veldo/control_channel_activation.py"
  - ".veldo/control_channel_ingress.py"
  - ".veldo/control_channel_projection.py"
  - ".veldo/control_effect_executor.py"
  - ".veldo/control_effect_executor_adoption.py"
  - ".veldo/control_effect_executor_creation.py"
  - ".veldo/control_factory_setup.py"
  - ".veldo/control_git_identity_transport.py"
  - ".veldo/control_installation_schema.py"
  - ".veldo/control_plane_calls.py"
  - ".veldo/control_plane_scan.py"
  - ".veldo/control_repository_creation.py"
  - ".veldo/control_service.py"
  - ".veldo/control_tracker_service.py"
  - ".veldo/git_process.py"
  - ".veldo/init_scaffold.py"
  - ".veldo/installation.py"
  - "engine/.veldo/control_channel_activation.py"
  - "engine/.veldo/control_channel_ingress.py"
  - "engine/.veldo/control_channel_projection.py"
  - "engine/.veldo/control_effect_executor.py"
  - "engine/.veldo/control_effect_executor_adoption.py"
  - "engine/.veldo/control_effect_executor_creation.py"
  - "engine/.veldo/control_factory_setup.py"
  - "engine/.veldo/control_git_identity_transport.py"
  - "engine/.veldo/control_installation_schema.py"
  - "engine/.veldo/control_plane_calls.py"
  - "engine/.veldo/control_plane_scan.py"
  - "engine/.veldo/control_repository_creation.py"
  - "engine/.veldo/control_service.py"
  - "engine/.veldo/control_tracker_service.py"
  - "engine/.veldo/git_process.py"
  - "engine/.veldo/init_scaffold.py"
  - "engine/.veldo/installation.py"
  - "scripts/suites/05_tracker_routing_resolver_veldo.py"
  - "scripts/suites/06_capabilities_manifest_honesty_veldo.py"
  - "scripts/suites/09_action_whitelist_warp_1205.py"
  - "scripts/suites/103_veldo_0142_git_identities.py"
  - "scripts/suites/105_veldo_0182_memory.py"
  - "scripts/suites/106_veldo_0185_dispatch_setup.py"
  - "scripts/suites/107_veldo_0153_identity_push.py"
  - "scripts/suites/108_veldo_0153_executor_profile.py"
  - "scripts/suites/109_veldo_0161_adoption.py"
  - "scripts/suites/10_warp_0613_anti_vacuity.py"
  - "scripts/suites/110_veldo_0143_new_project.py"
  - "scripts/suites/117_veldo_0227_ui_location.py"
  - "scripts/suites/123_veldo_0174_conversations.py"
  - "scripts/suites/127_veldo_0234_https_port.py"
  - "scripts/suites/127_veldo_0259_installation.py"
  - "scripts/suites/129_veldo_0254_canary_launch.py"
  - "scripts/suites/13_warp_0623_codified_live.py"
  - "scripts/suites/58_veldo_0028_effects.py"
  - "scripts/suites/60_veldo_0064_inbox.py"
  - "scripts/suites/62_veldo_0065_presentations.py"
  - "scripts/suites/63_veldo_0066_attribution.py"
  - "scripts/suites/70_veldo_0073_activation.py"
  - "scripts/suites/71_veldo_0130_api.py"
  - "scripts/suites/71_veldo_0138_channel_service.py"
  - "scripts/suites/72_veldo_0075_andon.py"
  - "scripts/suites/72_veldo_0128_reports.py"
  - "scripts/suites/73_veldo_0139_factory_setup.py"
  - "scripts/suites/74_veldo_0140_standing_delegation.py"
  - "scripts/suites/82_veldo_0144_mcp_catalog.py"
  - "scripts/suites/84_veldo_0169_project_handouts.py"
  - "scripts/suites/85_veldo_0171_setup_api.py"
  - "scripts/suites/86_veldo_0168_text.py"
  - "scripts/suites/86_veldo_0186_setup_assets.py"
  - "scripts/suites/86_veldo_0189_engine_upgrade.py"
  - "scripts/suites/87_veldo_0170_receiver_trust.py"
  - "scripts/suites/support/outside_fixture.py"
  - "scripts/suites/support/v73_authority.py"
behavior_bearing: true
observability:
  logs: >
    Each control-plane caller writes one line per outside call: caller, destination host, operation, result
    and latency, never a credential value or body. A refused credential reference is logged with the
    caller and the reference's scheme and name.
  metrics: >
    Control-plane calls by caller and result; credential references refused by scheme.
  traces: >
    Each call carries the accepted installation commit whose settings were in force and, where it serves a
    unit, the unit or dispatch id.
  error_taxonomy: >
    invalid_input:control_plane_credential:<caller>:<scheme> (a credential reference that is not a keystore
    reference), installation_invalid for a tracker or doorbell setting that fails its kind (VELDO-0253),
    control_plane_call_unregistered:<module> (an outside call from a module the register does not list,
    found by the static row).
acceptance_criteria:
  - id: AC1
    text: >
      Claim: every outside credential Veldo's own service uses is a keystore reference, and no other source
      is read. Set: the tracker mirror, the tracker's init command, the doorbell, the repository provisioner
      and the owner's channel resolve their credentials through secretref's keychain scheme only; an env:,
      file: or literal reference for any of them is refused at load as
      invalid_input:control_plane_credential:<caller>:<scheme>, and a token present in the process
      environment is never read. Rows: each caller authenticates to a fixture service with a keystore canary;
      each refuses an env: reference by name with the variable set; a scan of the service's logs and records
      finds no canary.
    falsified_by: >
      Keep the tracker's environment resolver; the env-reference row authenticates with the variable's
      value and fails.
  - id: AC2
    text: >
      Claim: tracker routing and the doorbell's settings are installation configuration, and the product
      ships none. Set: the tracker file's routing (sites, projects, repository mapping, credential reference
      by name) and the doorbell's target are kinds added to VELDO-0253's schema, read only through the
      installation loader; the product's trackers.json becomes the template's example with no site; a value
      in the state root is never a source. Rows: a tracker site added by an installation commit is used after
      the loader accepts the commit; a commit with a malformed site is refused whole and the previous routing
      stays live; the shipped template names no site.
    falsified_by: >
      Read the tracker file from the product tree; the added-site row keeps the old routing and fails.
  - id: AC3
    text: >
      Claim: the control plane's outside calls are listed once, are made only by the service, and are outside
      the gate, so no run can make them. Set: one register (control_plane_calls.json) names each module that
      makes an outside call for the control plane (tracker, provisioner, landing push, the owner's channel,
      the doorbell) with its destination kind; a static row fails on an outside call from any other engine
      module as control_plane_call_unregistered:<module>; each listed module runs only in the service
      process, never in a run, and messages and files Veldo sends the owner through its own
      channel need no per-call approval. Rows: the static row passes on the register and fails on a planted
      call in another module; a run's files, environment and command line hold no canary for any listed
      module's credential (VELDO-0254 AC1); a landing
      push from the control plane reaches a fixture remote with no gate call.
    falsified_by: >
      Drop the static row's scan of unregistered modules; the planted-call row passes where it must fail.
required_evidence: [unit, integration]
rollback: >
  Revert the change. The tracker and doorbell read their env: references and the product tracker file again,
  and the register is no longer checked. Keystore items and installation commits stay, inert. No automatic
  rollback, retry or recovery is authorized.
---

## Intent

The gate covers calls from runs and project code. Veldo's own service also calls outside: the tracker
mirror, the repository provisioner, the landing push, the owner's channel and its doorbell. These stay
outside the gate because the control plane makes them, not a run, but today some read tokens from the
process environment and their settings from product files. This ticket puts their credentials in the
keystore, their settings in the installation repository, and lists them once so a new one cannot appear
unnoticed.

## Context

- The tracker resolver reads a token named by an env: reference from the process environment, and the
  doorbell reuses it for its own token.
- The product ships trackers.json with routing an installation fills in.
- VELDO-0253 declares the installation schema; every spec adds its kinds there.
- Runs hold no credential for these destinations (VELDO-0254); they are not fenced from the network.

## Design

Keystore references only, refusal of every other scheme by caller, tracker and doorbell kinds in the
installation schema, and one register with a static row.

## Out of scope

- Which tracker or channel an installation uses.
- The tracker code's own behaviour beyond where its credentials and settings come from.
- Calls from runs and project code (VELDO-0251).

## What the reviewer judges

- Normal use: an installation declares its tracker in its repository, stores the token in the keystore,
  and the mirror works; the owner's channel and doorbell work as before.
- Threat model: a token in the environment silently used, routing read from a product file, a new outside
  call added to an unlisted module, a control-plane credential found in a run.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962).

## History

2026-11-04: new draft, Telegram 39145, from research/veldo-plan-consistency-review-2026-11-04.md (C15, A9)
and the lead's rulings research/veldo-plan-rulings-2026-11-04.md (R6: the control plane is outside the
gate; R1: tracker and doorbell kinds join VELDO-0253's schema). It decides only where the tracker's
credentials and settings come from, not whether the unreviewed tracker code on another branch (review D10)
lands. Standalone; no plan work item.

2026-11-05: Telegram 39154 and 39155, revised rulings R5, R7 and R14 (no mandatory sandbox): AC3 no longer
says a run finds no route to a control-plane destination; it checks instead that no run holds a credential
for one (VELDO-0254 AC1), and the Context and threat model say the same.

2026-11-05: the review amendments and new tickets approved by the owner, Telegram 39157 ("Yes", to 39156). Status ready.
