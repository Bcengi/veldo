# VELDO-0270 build status

Branch agent/claude/veldo-small-proof, base afa292f0. Stopped on the lock rule: the gate lock was
held by another full gate (landing-b verify.sh, started 08:20) after about 17 minutes of total lock
waits, so the remaining runs are in `pending_runs.sh` (bash -n: exit 0). The full gate was not run.

## AC1: refused by the gate and by the push guard (built)

- e28c5ed6, 207815d1, cab9acc9: `.veldo/validate.py` (canon `engine/.veldo/validate.py`, kept equal)
  `check_proof_files` in `all` and mode `proof-files`: proof_file_over_limit,
  proof_encoded_archive (.b64/.base64 names; base64 runs of 64+ characters decoding to gzip, zip,
  bzip2, xz, zstd, or tar magic at 257), proof_reference_dangling (full path, bundle relative path,
  or bare name in the same directory; once per file and removed path), proof_summary_incomplete,
  proof_policy_invalid. Git goes through git_process (the boundary check passes).
- 7d07e5bf: `.veldo/policy.yaml` gains `proof.max_file_bytes: 1048576` and
  `proof.protected_refs: [refs/heads/main, refs/tags/*]`.
- 64242e95, 611bf741: the guard runs `validate.py push-proof` on `VELDO_PUSH_REFS` (after the
  emergency lane, so VELDO_EMERGENCY still passes and is recorded); all seven
  `packs/*/hooks/pre-push` now export git's ref lines and the remote name to it (edited with the
  Edit tool).

## AC2: writers write summaries (built)

4600fda7, 52cd0ae1: `validate.py` gains `proof_summary`/`write_proof_summary`
(veldo.proof-summary/v1: command, environment with commit, tree, host, tool versions and load when
timing sensitive, discarded name/bytes/sha256, deciding), `summarize_mutation_receipt`,
`summarize_gate_transcript` and mode `gate-summary <transcript> <out>` (the gate transcript
capture). `check_gate_mutations.py` (and engine copy) and `check_teeth_mutations.py` gain
a summary option; `parser_corpus_audit.py` and `writer_corpus_audit.py` write counts and differing
entries through `write_summary`; `proof/VELDO-0123/drive.py` writes a per case summary.

## AC3: files over the limit replaced (built)

3fa18597 removes the eight files in one commit; each `<name>.summary.json` carries original path,
bytes, sha256, readable_at afa292f0, command, environment, deciding numbers. References re-pointed
in VELDO-0110 README, VELDO-0121 results summaries, VELDO-0123 manifest/README/history,
VELDO-0189 digests.json, VELDO-0215 and VELDO-0230 manifests; recorded digests kept. Suites 45, 51,
86, 93 and the writer audit now read the summary, or the bytes from history at readable_at.
`proof-files` over the tree: 5832 files, largest 1,038,784 bytes, 0 problems. No commit rewritten.

## AC4: the rule paragraph (built)

531d3f59: the paragraph is in CLAUDE.md, VELDO.md, engine/VELDO.md and all seven pack reviewer
briefs, which also ask whether the bundle holds anything a reviewer does not need.

## Rows (suite 129, registered in manifest.json, requires.json regenerated)

Run at cab9acc9 under the lock: 33 rows passed, 0 failed (59 with shared rows). First run at
52cd0ae1: 1 red (`p270/dangling/manifest-naming-removed-file-refused`, a file was reported twice),
fixed in cab9acc9.

## Falsifiers (scripts/check_teeth_mutations.py, finding 270)

guard-judges-only-the-tip, limit-hard-coded-default, references-unchecked,
mutation-writer-copies-raw, rule-deleted-from-engine-veldo. Run once: the stage failed at its noop
controls (worker exit 1, executed 0), so no mutant was judged; red then green is NOT shown. Cause
unknown (the suite is green outside the sandbox); `pending_runs.sh` reruns with worker logs.

## Still open

- Teeth 270 must pass; then each falsifier is red (mutant) and green (fix).
- Not run: suites 45, 51, 52, 86, 93, 06, 50, 107, 109, 58, 86_0148, contracts `all`,
  check_docs, template sync (all in `pending_runs.sh`).
- Outside the footprint, not changed: AC4's falsifier names `scripts/check_docs.sh`; the paragraph
  check lives in suite 129 instead. Drivers `proof/*/drive.py` outside the footprint bundles are
  unchanged. Recorded approvals were not re-verified here.

## Fix round 1 (a2f920d0)

The lead ran the first `pending_runs.sh` at 91523cc9 (summary in `pending-summary.txt`). Reds:

1. Teeth 270, executed 0: every noop control raised "suite production-copy anchor moved". Suite 129
   spelled paths as `ROOT / '.veldo/validate.py'`; the mutation observer substitutes only
   `ROOT / ".veldo" / "validate.py"` (and the same form for `scripts` and `engine`). Caused by this
   diff. Fixed: suite 129 spells the three anchors, every scratch repository copies the .veldo that
   holds the validate.py under test, and the three validate.py cases set `siblings` (it loads
   yamlish.py and git_process.py beside itself).
2. Suite 86_veldo_0189_engine_upgrade, row `VELDO-0189 upgrade/census`: the fixture reader required a
   summary for `census.json.gz`, which stays in the tree. Caused by this diff. Fixed: a fixture in
   the tree is read and matched against digests.json; only a removed archive goes through its summary.
3. The 4 suite run, row `WARP-1309 AC6: validate.py stays at or under its file_lines budget after
   the wiring` (suite 01_warp_0101_reviewer_notes, limit 1000 lines): validate.py is 1224 lines here,
   828 on main afa292f0. Caused by this diff. NOT fixed: keeping the budget means moving the proof
   checks into a new `.veldo` module (and its engine copy), outside the footprint; reported to the lead.

Reruns not done: the gate lock was not free within 20 minutes of waiting. They are in
`pending_runs.sh` (bash -n: exit 0), lines prefixed `round1` in `pending-summary.txt`.

## Fix round 2 (4f4d04c4)

Red 3 fixed under the footprint the lead widened in 3b0b7468. The proof size rules moved unchanged
from validate.py into `.veldo/proof_size.py` (engine copy byte-identical). validate.py loads it by
path from beside itself on first use, the way it loads request.py, binds its parser and reporter,
and delegates the same public names, so callers (V.check_proof_files, V.write_proof_summary, ...)
are unchanged. Lazy, not eager: scripts/suites/shared.py loads validate.py, and 28 declared cases in
scripts/mutation_case_inputs.json (outside the footprint) freeze inputs without proof_size.py.
validate.py: 1224 lines before, 871 after (budget 1000); proof_size.py 399 lines. init_scaffold.py
lists proof_size.py after validate_checks.py in both _FILES and REQUIRED_SUBSTRATE (engine copy
identical). Falsifier anchors followed the code: the three validate.py teeth cases of finding 270
now mutate proof_size.py, and suite 129 spells `ROOT / ".veldo" / "proof_size.py"` and drives the
validate.py beside it. Local checks: `validate.py proof-files` exit 0, template sync pass.

Runs at 4f4d04c4, command `flock -w 1200 <gate lock> python3 scripts/selftest.py --suite
129_veldo_0270_small_proof`: 59 passed, 0 failed, exit 2 (PARTIAL convention), host lock wait 8.6 min.
Suite 01_warp_0101_reviewer_notes and teeth 270 not run: the lock was not free within the
remaining wait (20 minutes total). They are in `pending_runs.sh` (bash -n: exit 0), lines prefixed
`round2` in `pending-summary.txt`.
