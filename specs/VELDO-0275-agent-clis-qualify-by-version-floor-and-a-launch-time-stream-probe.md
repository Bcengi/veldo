---
schema: veldo.spec/v1
id: VELDO-0275
title: Claude Code and Codex runs use only the approved engine version pinned by digest with a small qualification summary in place of the per-binary records, and every launch runs a stream probe
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0230]
placement: [fleet]
protected_paths: ["scripts/mutation_case_inputs.json"]
footprint:
  - ".veldo/qualify.py"
  - "engine/.veldo/qualify.py"
  - ".veldo/control_engine_claude.py"
  - "engine/.veldo/control_engine_claude.py"
  - ".veldo/control_engine_codex.py"
  - "engine/.veldo/control_engine_codex.py"
  - ".veldo/control_launch.py"
  - "engine/.veldo/control_launch.py"
  - ".veldo/control_containment.py"
  - "engine/.veldo/control_containment.py"
  - ".veldo/control_factory_setup_engines.py"
  - "engine/.veldo/control_factory_setup_engines.py"
  - ".veldo/init_scaffold.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/control_factory_setup_dispatch.py"
  - "engine/.veldo/control_factory_setup_dispatch.py"
  - ".veldo/control_agent_config.py"
  - "engine/.veldo/control_agent_config.py"
  - ".veldo/control_agent_config_handoff.py"
  - "engine/.veldo/control_agent_config_handoff.py"
  - "scripts/mutation_case_inputs.json"
  - ".veldo/runtime/**"
  - "engine/runtime/**"
  - "scripts/engine_census.py"
  - "scripts/check_teeth_mutations.py"
  - "proof/VELDO-0127/**"
  - "scripts/suites/**"
  - "specs/VELDO-0275-agent-clis-qualify-by-version-floor-and-a-launch-time-stream-probe.md"
  - "specs/index.md"
  - "proof/VELDO-0275/**"
  - "proof/VELDO-0162/setup_assets.py"
  - "proof/VELDO-0167/review_rows.py"
  - "proof/VELDO-0172/compare_formats.py"
  - "proof/VELDO-0182/integration_fixtures.py"
  - "proof/VELDO-0186/fixtures.py"
  - "proof/VELDO-0188/round2/served_scenario.py"
  - "proof/VELDO-0230/fix2_unevaluated.py"
  - "specs/VELDO-0275b-new-agent-cli-versions-qualify-automatically-and-environment-by-named-patterns.md"
behavior_bearing: true
observability:
  logs: >
    Each launch prints one line naming the engine, the resolved binary, its version, the floor it was
    held to and the probe result (parsed, or the first frame that failed to parse). Setup prints the same
    line once per engine.
  metrics: >
    The execution record carries the engine version and the probe result in place of the binary digest.
  traces: >
    A failed probe keeps the raw frames it read (bounded) in the run's evidence.
  error_taxonomy: >
    Added: below_version_floor, stream_probe_failed (with the frame). Removed: stale_subject:engine_digest,
    binding_mismatch:engine_digest and missing_evidence:engine_qualification for a version not in the
    record. Unchanged: every credential and capability refusal.
acceptance_criteria:
  - id: AC1
    text: >
      Runs use only an approved engine version, pinned by digest. runtime/engines.json holds, per engine,
      the approved version, the sha256 of its versioned binary (the copy the installer keeps, as today) and
      the path of its qualification summary. Every launch resolves exactly that binary and refuses with
      engine_not_approved if its digest differs; a newer installed version is never used because it is
      installed, and runs stay on the approved one until a new one is approved (automatically by
      VELDO-0275b AC1 once it lands; until then by the qualify.py run and commit of today). The per-binary
      qualification records (codex-qualification.json, 793 KB; claude-qualification.json, 96 KB) and the
      extractors that only fed them are replaced by small qualification summaries (per check: name,
      outcome, duration; under 1 MB, no raw transcript; the format VELDO-0275b AC1 writes), the approved
      versions' summaries written by qualify.py from the checks it runs today; tables the stream reader still
      needs stay as a small reviewed file in .veldo/runtime.
    falsified_by: >
      A new suite installs a fake engine version above the approved one: launches keep using the approved
      binary. A fake approved binary whose bytes are changed after approval: refused engine_not_approved.
      Registered mutations from a green baseline: (1) the launch picks the newest installed version: the
      stays-on-approved row goes red; (2) the digest check is skipped: the changed-bytes row goes red.
  - id: AC3
    text: >
      Every launch also starts with a stream probe: before the prompt is sent the engine runs the
      zero-turn probe the adapters already run (assistants_before_prompt, num_turns 0), and every frame it
      prints is parsed by the same stream reader the run uses. A frame the reader cannot classify, or a
      missing result frame, refuses the launch as stream_probe_failed with the frame, so even an approved
      version that starts misbehaving never starts a run.
    falsified_by: >
      The suite drives an approved fake engine that prints one frame of an unknown type in the probe:
      refused with that frame; one whose probe matches today's format: accepted. Registered mutation: the
      launch skips the probe for an approved version: the unknown-frame row goes red.
required_evidence: [unit, integration]
rollback: >
  Revert the commit and run python3 .veldo/qualify.py on the installed binaries to rewrite the deleted
  records; launches are held to the digest again.
---

## Intent

Weight audit item 6: stop paying a ticket per CLI upgrade. Claude Code ships often (four versions on this
host); 81 commits on main since 2026-09-01 mention qualification (verified); the 2.1.317 and 0.166.0
upgrade took VELDO-0230 plus three fix rounds.

## Context

Verified on main at afa292f0: .veldo/qualify.py is 696 lines; .veldo/runtime holds
codex-qualification.json (793,287 bytes), claude-qualification.json (96,204) and
capability-decisions.json (27,943), as the audit says. engines.json pins a path, version and sha256 per
engine. Codex is refused on a digest mismatch (stale_subject:engine_digest); Claude Code is keyed by
version entries in its record. capability-decisions.json holds 82 Claude Code entries (19 of them
environment names) and 24 Codex entries, plus seven rules that cite the specs they protect.

Owner approval: required. This changes what reaches an agent process (environment, features, tools),
which is security under the owner's scope (Telegram 39708).

## Out of scope

Credential delivery (VELDO-0158), the role capability lists (VELDO-0127), account pools and usage windows.
Automatic qualification of a new version and the environment and capability rules: VELDO-0275b (former
AC2 and AC4 of this spec).

## What the reviewer judges

- Normal use: factory setup and every launch on this host after an upgrade.
- Only the approved, digest-pinned binary ever runs; a stream format change refuses before the prompt;
  every reader of the deleted records reads the summary or the reviewed tables instead.
- Out of review scope: a new CLI that changes behavior without changing its stream format (the audit's
  accepted risk).

## History

2026-11-07: drafted by the lead from the weight audit's item 6 (Telegram 39708, 39710). A draft; needs
the owner.

2026-11-07: rewritten by the lead on the owner's word (Telegram 39751 to 39753): no version floor; runs stay on the approved, digest-pinned version, and a new version is approved only by an automatic full qualification run that passes every check (AC1, AC2); the launch probe stays (AC3); environment rules unchanged (AC4). Ready on his yes, 39753.

2026-11-08: revised by the lead after the builder stopped on footprint blockers (proof/VELDO-0275/README.md).
Each change and why, facts checked on this branch at bbffb0ce (main 918e7c0e):
(1) Footprint widened to the readers of the two records AC1 deletes that sit outside it: .veldo/init_scaffold.py
498 and 501 install both records; .veldo/control_factory_setup_dispatch.py 155 reads the Codex record by path;
.veldo/control_agent_config.py 97 reads model_catalog from it; .veldo/control_agent_config_handoff.py 237, 270,
377, 414, 431 and 520 read accepted_plugins, engine_plugins, engine_skills, feature_listing, the model catalog
and the tool modes from it; each with its engine/.veldo copy; and scripts/mutation_case_inputs.json 1508 (and
eight more case lists) declares both records as case inputs. That file is protected (floor high), so it is
also listed in protected_paths. The other readers and writers (qualify.py, control_engine_claude.py 400, 1198,
1234, control_engine_codex.py 425, 611, control_factory_setup_engines.py 57, engine_census.py 46, 47,
check_teeth_mutations.py, scripts/suites, engine/runtime) were already in it. scripts/fixtures does not read
the records (its qualification() is the agreement reports' own).
(2) AC2 moved to VELDO-0275b (draft) as its AC1: it reports into the owner's daily summary, which is not on main;
the one ticket that provides it is VELDO-0272 AC4 (ready, unlanded, on agent/claude/veldo-approval-scope).
(3) AC4 moved to VELDO-0275b as its AC2: it withholds variables matching "the credential name patterns of
VELDO-0254", and none exist. VELDO-0254 is wholly on main (its branch has no commit main lacks) and delivered
credential value formats (.veldo/secret_scan.py FORMATS, line 157) read by the launch scan, which refuses a
launch (.veldo/control_launch.py 379, credential_delivery_site:environment:<name>), not name patterns that
withhold a variable. Pointing AC4 at those would change its behaviour (refuse instead of withhold), which is
the owner's decision.
(4) AC1 keeps its behaviour and falsifier; only its two references to AC2 now name VELDO-0275b AC1, and the
interim is stated: until 0275b lands a new version is approved as today, and the approved versions' summaries
are written by qualify.py from the checks it already runs. AC3 is unchanged. Title, out of scope and the
reviewer's list follow the moved ACs. Status stays ready: the kept ACs are unchanged in behaviour.

2026-11-08 (lead, before the check): footprint gains the seven proof fixtures and extractor modules that read the replaced per-binary records (listed in proof/VELDO-0275/README.md under Footprint additions) and the split-out draft spec VELDO-0275b. AC3's Codex probe is one real turn because Codex offers no zero-turn probe (README, Premises); the criterion is unchanged.
