# VELDO-0275 proof: approved engine pinned by digest (partly built), stream probe (blocked)

Branch agent/claude/veldo-0275, base main 918e7c0e, spec as revised at 765d3101. This build replaces the
earlier blocker note (bbffb0ce). Suite and mutation runs inside the gate lock are pending:
proof/VELDO-0275/pending_runs.sh (see the end of this file).

## Summary per AC

| AC | State |
| --- | --- |
| AC1 approved version pinned by digest | Built: launch and setup refusal, setup resolves the approved binaries, new suite, four mutations |
| AC1 records replaced by summaries | Not built: blocked, readers and extractors outside the footprint (below) |
| AC3 stream probe on every launch | Not built: blocked, fake engines outside the footprint (below) |

## AC1: what was built

- `.veldo/control_engine_claude.py` (and its engine/ copy): `qualified()` refuses a version the qualification
  record does not list as `engine_not_approved` (was `invalid_input:engine_version:<v>`); `pin()` and `bind()`
  refuse a copy whose digest differs from the approved one as `engine_not_approved` (was
  `binding_mismatch:engine_digest`).
- `.veldo/control_engine_codex.py` (and copy): `bind()` refuses a package version or a digest other than the
  approved one as `engine_not_approved` (was `stale_subject:engine_version` and `stale_subject:engine_digest`).
- `.veldo/control_factory_setup_engines.py` (and copy): `check()` resolves the approved Codex binary
  (`approved_codex`): the one the `codex` on PATH runs if its digest is the approved one, else the installer's
  kept copy that runtime/engines.json names. A newer version on PATH is never used. If neither matches, setup is
  refused `engine_not_approved`. Claude Code was already taken from the engines record (VELDO-0230). The
  `stale_subject` to `binding_mismatch` mapping is gone: both engines give the same code.
- Suites whose expected codes moved: 78 (0060), 79 (0061), 86 (0186), 86 (0189). Registered mutations whose
  anchors moved: claude-pin-digest-unchecked, upgrade189-codex-refusal-differs, setup186-claude-unlisted-taxonomy,
  setup186-codex-unlisted-taxonomy. Each still injects the same kind of defect.

### New suite: scripts/suites/130_veldo_0275_approved_engine.py

Registered in scripts/suites/manifest.json. requires.json was regenerated with
`python3 scripts/run_scope.py --emit-requires`.

| Row | What it checks | Local outcome |
| --- | --- | --- |
| approved/stays-on-approved | Newer Claude Code and Codex are installed and on PATH. Setup still resolves the approved version and binary, pins and binds them, and refuses a launch naming the newer one as engine_not_approved (8 checks) | green |
| approved/changed-bytes | After approval, the bytes of the approved pinned Claude copy and of the Codex binary change. Both bindings and setup refuse engine_not_approved; once the bytes are restored, setup resolves again (5 checks) | green |

These local results come from `python3 scripts/selftest.py --suite 130_veldo_0275_approved_engine`, outside
the lock. It printed "2 passed" in 0.05 s. That is a partial run and not gate evidence.

### Falsifiers (registered in scripts/check_teeth_mutations.py, finding 275)

To see each one go red, I swapped the mutation into the production module in place, ran suite 130, then restored
the file (git status was clean afterwards). Each one is green again without the mutation, as shown above.

| Mutation | Defect | Row that went red |
| --- | --- | --- |
| approved275-claude-newest-installed | setup takes the newest file in the versions directory | approved/stays-on-approved |
| approved275-codex-newest-installed | setup takes the first installed Codex (the newer one on PATH) | approved/stays-on-approved |
| approved275-claude-digest-skipped | the Claude pinned copy's digest is not checked | approved/changed-bytes |
| approved275-codex-digest-skipped | the Codex binary's digest is not checked | approved/changed-bytes |

The driver runs (`check_teeth_mutations.py --case ...`) are pending in pending_runs.sh.

## Blockers: files outside the footprint that would have to change

1. AC1 record replacement. The two records cannot be deleted and replaced by summaries without changing these
   files, which the footprint does not list:
   - Readers of the records: proof/VELDO-0186/fixtures.py line 42 (suite 86 0186 calls it), proof/VELDO-0162/setup_assets.py,
     proof/VELDO-0167/review_rows.py, proof/VELDO-0182/integration_fixtures.py, proof/VELDO-0188/round2/served_scenario.py,
     proof/VELDO-0230/fix2_unevaluated.py.
   - "The extractors that only fed them" live in proof/VELDO-0060, 0061, 0062, 0141, 0155, 0156, 0165, 0173 and 0185
     (qualify.py EXTRACTORS). Running qualify.py, which the spec says writes the summaries, also rewrites their tables
     in those directories.
   - Sizes: the Codex record is 793 KB, and 748 KB of it is the bundled model catalog. Every role-bound Codex run passes
     that catalog to the engine whole (control_agent_config_handoff.codex_model, model_catalog_json), so a "small
     reviewed tables" file still has to carry it or read it from the binary at launch. That is a design choice for
     the spec.
   - For the same reason, engines.json does not yet name a summary path: no summary file exists to point at.
2. AC3 stream probe. Today the probe only runs for role-bound Claude Code runs (Guard.release with `expected` set).
   Running it on every launch breaks every fake Claude Code engine that answers the initialize request but treats
   the next user message as the prompt. One is proof/VELDO-0182/integration_fixtures.py (suite 105), which is
   outside the footprint. About fifteen suite fakes inside the footprint (78, 75, 78 0160, 80, 82 0141, 82 0165,
   85 0158 and others) would need a probe answer as well. Codex has no zero-turn probe to reuse (exec reads only
   the prompt), so "every launch" for Codex also needs the spec to say what the probe is.
3. Taxonomy leftovers. The exec-time re-hash still reports `binding_mismatch:engine_digest`, in .veldo/control_clone.py
   line 400 (outside the footprint) and in the wrapper message at .veldo/control_launch.py line 2783, which I kept
   matching the clone. The observability lines (one launch line per engine; version and probe result in the
   execution record) depend on AC3 and the summary, so they are not built either.

## Runs

- No lock needed: `bash scripts/check_lint.sh`: lint pass (1157 python, 39 shell). Suite 130 alone: 2 passed (partial).
  I also checked by script that every registered mutation on the three changed modules finds its anchor exactly once.
- Pending, inside the lock: `bash proof/VELDO-0275/pending_runs.sh`. It writes one line per step to
  proof/VELDO-0275/pending-summary.txt (step, exit code, /tmp log path). It checks that the tree is clean before and
  after, ignoring that summary file. Steps: lint, suite 130, 41 suites that load the engine or setup modules,
  the four new mutations, and the seven registered mutations whose anchors or codes this change touched.
- Inherited reds: none observed. No full suite was run in this build.
