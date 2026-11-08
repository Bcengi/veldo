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
| proof/VELDO-0186/fixtures.py, proof/VELDO-0162/setup_assets.py | AC1: read the bundled catalog from proof/VELDO-0127/catalog-fixture.json instead of the deleted Codex record |
| proof/VELDO-0167/review_rows.py | AC1: the pre-record engine (f1e1abb9) reads the old record names; they are written there from the new tables |
| proof/VELDO-0188/round2/served_scenario.py | AC1: record path renamed, its fake's `debug models` prints the catalog fixture; AC3: its Codex fake answers the probe |
| proof/VELDO-0230/fix2_unevaluated.py | AC1: record path renamed |
| proof/VELDO-0182/integration_fixtures.py | AC1: path renamed and stream tables carried; AC3: the fake answers the Claude Code probe (a result of no turn) and the Codex probe (--ephemeral) |
| proof/VELDO-0172/compare_formats.py | AC3: the shared fake read-back wrote only the Guard's first release, which is now the probe; it writes each release in turn until the prompt |

Protected paths changed: scripts/mutation_case_inputs.json (already in the spec's protected_paths): the record names
renamed in its case input lists. No other protected path was touched.

Inside the footprint but worth naming: scripts/suites/** fakes in 75, 78 0060, 78 0160, 79, 80, 81, 82 0129, 82 0141,
82 0165, 82 0173, 83 0154, 85, 86 0127, 86 0148, 93, 94, 95, 106, 110, 116, 129 and support/v174_journey.py answer the
probe; suites that build a Claude record by hand now carry its `stream_forms`; 78 0060 counts the probe's result line;
82 0129's missing-usage row allows the probe's own result its modelUsage; the earlier-host rows of 106, 117 and 127
write the old record names the earlier engine reads.

## Behaviour notes for the reviewer

- The usage meter ignores a result of zero turns (the probe's): it settles no usage. A real run that ends with zero
  turns keeps its tokens unknown and its reservation retained, the conservative reading.
- A Claude Code run whose engine ends before its login is confirmed (the probe never sent) fails as before; one that
  reached the probe and ended without its result is `stream_probe_failed` (missing_result); both are configuration
  stops (outcome cancelled), as a role-bound run's unwritten prompt already was.
- A Claude Code record without stream tables refuses the probe by name (`no_stream_tables`) instead of crashing the
  receiver.

## Runs

No lock taken (the shared gate lock was busy). Every result here is a local, partial run and not gate evidence.

- `bash scripts/check_lint.sh`: lint pass (1158 python, 40 shell).
- `python3 .veldo/qualify.py` on the approved binaries: exit 0, every check pass, rewrote the runtime files and the
  VELDO-0127 fixtures (the four resources-*.json files change only in the `production` module digests).
- Local suites at a45cf474 and later (scratch worktrees, `python3 scripts/selftest.py --suite <name>`), green:
  70 0073, 73 0139, 75 0062, 78 0060, 78 0160, 79 0061, 80 0155, 81 0156, 82 0129, 82 0141, 82 0165, 82 0172,
  82 0173, 83 0154, 83 0166, 85 0158, 86 0148, 86 0186, 86 0189, 87 0127, 88 0127, 89 0127, 90 0127, 91 0167, 93 0152,
  94 0162, 95 0203, 102 0210, 105 0182, 106 0185, 110 0143, 116 0188, 117 0227, 123 0174, 125 0230, 127 0234, 129 0254,
  130 0275, 131 0275.
- Falsifiers, red then green (in-place swap, suite run, restore; git status clean after): approved275-claude-newest-installed,
  approved275-codex-newest-installed (stays-on-approved red), approved275-claude-digest-skipped,
  approved275-codex-digest-skipped (changed-bytes red), probe275-claude-skipped, probe275-codex-skipped
  (unknown-frame red).
- Not green, inherited: suite 86 0127 rows live/claude and live/codex ("missing or stale live capture"). The live
  captures (proof/VELDO-0127/claude-live.json, codex-live.json) bind the production digests of five modules; they
  were already stale at 45772a2e (the AC1 pin changed control_engine_claude.py and control_engine_codex.py) and need
  the lead's live recapture with real accounts (proof/VELDO-0127/live.py), as at 3b9b9a8c.
- Suite 126 0230 (qualify reproduces, real binaries offline): green, 30 passed, 102 s, at the final qualify commit.
- Not green, inherited: suite 101 0208 rows sandbox/unavailable-refuses-before-exec and sandbox/old-abi-refuses-before-exec.
  The same two rows are red at 45772a2e in a scratch worktree on this host (214 passed, 2 failed both times); every
  other row of 101 is green here, its fixture-sharers row included (suite 126's text names no proof module it does not
  load).
- Pending, inside the lock: `bash proof/VELDO-0275/pending_runs.sh` (summary lines in
  proof/VELDO-0275/pending-summary.txt: step, exit code, /tmp log path; the tree is checked clean before and after,
  ignoring that file). Steps: lint, suites 130 and 131, the engine and setup suites, the six VELDO-0275 mutations
  and the seven registered mutations whose anchors or codes this change touched.
