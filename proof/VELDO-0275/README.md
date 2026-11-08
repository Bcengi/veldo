# VELDO-0275 proof: approved engine pinned by digest, records replaced by summaries, stream probe on every launch

Branch agent/claude/veldo-0275, base main 918e7c0e, spec as revised at 765d3101. Builds on the AC1 pin
(0eb521e0, 8b0e991d). Suite and mutation runs inside the gate lock are pending:
proof/VELDO-0275/pending_runs.sh (see "Runs" at the end). Local runs below are partial and not gate evidence.

## Summary per AC

| AC | State |
| --- | --- |
| AC1 approved version pinned by digest | Built (0eb521e0, 8b0e991d): suite 130, four mutations |
| AC1 records replaced by summaries | Built (203b5a30): reviewed tables plus per-engine summaries; extractors run as checks |
| AC3 stream probe on every launch | Built (eecbbb40 and later): Claude Code in the stream, Codex before acceptance; suite 131, two mutations |

## AC1: records replaced by summaries and reviewed tables

What replaced what, in every runtime copy (.veldo/runtime, engine/runtime):

| Before | After | Size |
| --- | --- | --- |
| codex-qualification.json (793,287 B) | codex-tables.json: the same tables minus the bundled model catalog; its digest (`model_catalog_digest`) stays | 38,401 B |
| claude-qualification.json (96,204 B) | claude-tables.json: the approved version's tables (stream forms, tool classes, baseline, login status) | 96,204 B |
| (none) | claude-summary.json, codex-summary.json: per check name, outcome, duration; verdict, version, digest | about 1.2 KB each |
| engines.json | adds `summary` per engine (`runtime/claude-summary.json`, `runtime/codex-summary.json`) | 820 B |

- The Codex model catalog (748 KB) is read at launch from the approved binary itself (`control_engine_codex.model_catalog`:
  `debug models --bundled` offline, as qualify.py read it, 0.1 s on this host) and must have the recorded digest, else
  engine_not_approved; a fixture record carrying a catalog inline gives that one. Its readers moved to it:
  control_agent_config.codex_grants, control_agent_config_handoff.codex_model and .codex, control_factory_setup_dispatch.codex_model,
  scripts/engine_census.py (model slugs from `model_tool_modes`). Suites and proof fixtures needing the catalog read
  proof/VELDO-0127/catalog-fixture.json, which qualify.py already writes from the same binary.
- qualify.py: each extractor in the nine proof directories runs in its own `--check` mode (writes nothing; fails when
  the binary differs from the committed table). The suites keep comparing against those committed tables, so every
  check they feed stays. `--write-tables` runs them in write mode instead: how a new version is approved until
  VELDO-0275b. The record writers, the init probe, the VELDO-0127 loopback captures and a final "tables load as a
  launch reads them" step are checks too. Summaries are written only when every check passed; a failed check approves
  nothing (exit nonzero, nothing written).
- The tables keep the schema name `veldo.engine_qualification/v1` and their structure, so every reader and fixture
  needed only the path; Claude Code's stays keyed by version (one entry, the approved one).
- Local reproduction: `python3 .veldo/qualify.py --codex <approved> --claude 2.1.317` rewrote every runtime file and
  VELDO-0127 fixture byte for byte except the fixtures' `production` module digests (modules changed), in 102 s.

Suite 126 now checks: every file written reproduces (a summary's durations aside); both tables and summaries in both
runtimes; every reader of the binaries ran as a passed check in the summary of each engine it reads; none of their
tables was rewritten; each summary is under 1 MB with only name, outcome and duration per check, approved for the
recorded version and digest, and named by the engines record.

## AC3: stream probe on every launch

- Claude Code (`control_engine_claude.Guard`): the zero-turn PROBE (shouldQuery false) is written before the prompt on
  every launch, not only role-bound ones; the receiver holds the prompt for every Claude Code launch
  (control_launch Metering). Every frame printed in answer is read by the run's own stream reader: a frame that is no
  JSON object with a string type, or whose type is neither a known message nor a tool-free frame of the version's
  stream tables (control frames aside), or an undecodable result, stops the launch `stream_probe_failed`; so does no
  result frame within PROBE_SECONDS (30). The prompt is never written. The artifact's `login` carries
  `{stop: stream_probe_failed, probe: {reason, frame, frames}}` (frames bounded: 16, 2 KB each). The stop cause is
  `configuration_stop`.
- Codex (`control_engine_codex.stream_probe`, run by `control_launch.Receiver._stream_probe` before acceptance, after
  the login checks): see Premises. Every line goes through the run's reader (`_malformed`); an unclassifiable line or
  no terminal frame refuses the launch `stream_probe_failed`, nothing accepted or spawned. One `stream_probe` event per
  launch names engine, binary, version and result (parsed or failed, with the frame).

### New suite: scripts/suites/131_veldo_0275_stream_probe.py

Registered in manifest.json; requires.json regenerated (`python3 scripts/run_scope.py --emit-requires`).

| Row | What it checks | Local outcome |
| --- | --- | --- |
| probe/unknown-frame | Fake Claude Code (real process, driven as the receiver drives it) prints an unknown frame in its probe: stopped stream_probe_failed with that frame, prompt never written; no result frame in time: same; fake Codex (receiver's probe step) prints an unknown frame or no terminal frame: refused stream_probe_failed with the frame in the event | green |
| probe/accepted | Today's format: Claude Code role-free launch gets its prompt once after the probe result; Codex proceeds with one parsed probe event | green |

### Falsifiers (scripts/check_teeth_mutations.py, finding 275)

Red checked by swapping each mutation into the production module in place, running suite 131, restoring (git status
clean afterwards); green without it as above.

| Mutation | Defect | Rows red |
| --- | --- | --- |
| probe275-claude-skipped | the Guard probes only a role-bound launch (as before) | probe/unknown-frame (and probe/accepted) |
| probe275-codex-skipped | the receiver skips the Codex probe | probe/unknown-frame (and probe/accepted) |

## Premises

- The spec assumed every engine has "the zero-turn probe the adapters already run (assistants_before_prompt,
  num_turns 0)". Claude Code has it (stream JSON input, a user message with shouldQuery false). Codex does not:
  `codex exec` reads only the prompt and always runs a model turn (0.166.0 `exec --help` lists no dry or zero-turn
  mode). So, as the lead allowed, Codex's probe is the smallest real one: one turn, prompt "Reply with the single word
  ready and nothing else. Use no tool.", `--ephemeral --skip-git-repo-check --sandbox read-only`,
  `web_search="disabled"`, the baseline's everything-off options and configuration, the account's login environment,
  an empty temporary directory, 120 s bound. It costs one small model turn on the account per Codex launch. A
  terminal frame of either kind (turn.completed or turn.failed) proves the stream; a usage-limited account therefore
  still launches and is classified by the run as today.
- The probe answer of the real binaries was not run here (no account turn spent in this build); the fakes follow the
  committed stream tables and proof/VELDO-0172's frame templates.

## Footprint additions (files outside the spec's footprint, each the smallest change)

| File | Why |
| --- | --- |
| proof/VELDO-0186/fixtures.py, proof/VELDO-0162/setup_assets.py | read the catalog from proof/VELDO-0127/catalog-fixture.json instead of the deleted Codex record |
| proof/VELDO-0167/review_rows.py | the pre-record engine (f1e1abb9) reads the old record names: written there from the new tables |
| proof/VELDO-0182/integration_fixtures.py | record path renamed; the fake answers the Claude Code probe (a result of no turn) and the Codex probe (--ephemeral) |
| proof/VELDO-0188/round2/served_scenario.py | record path renamed; its fake's `debug models` prints the catalog fixture |
| proof/VELDO-0230/fix2_unevaluated.py | record path renamed |
| scripts/suites/manifest.json, scripts/suites/requires.json | suite 131 registered (scripts/suites/** is in the footprint; listed for clarity) |
| proof/VELDO-0275/** fake-engine edits in other suites | see the list under Runs (all under scripts/suites/**, in the footprint) |

Protected paths changed: scripts/mutation_case_inputs.json (declared in protected_paths): record names renamed in the
case input lists.

## Runs

See the end of this file, updated after the local sweep.
