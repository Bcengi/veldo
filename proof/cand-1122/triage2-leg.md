# Round 2 isolated triage proof

Implementation: `5ab6d340ad81d042e3004fc56c1a01f87bf01919` (branch triage2-cand-1122-d650).
Input: d65033a8d unit leg, 297 printed failures, then reuse-audit abort.

Full group ledger, exact-tip comparisons, commands and evidence:
`myday research/claude-runs/triage2-cand-1122-leg.md`.
Raw selected-suite logs: sibling `triage2-evidence/` directory.

- Reuse audit: 38/0; stale declarations: 37/0. Authenticated cache digests
  remain bound before verdict enrichment; fresh records are bound after enrichment.
- Conversation replies: 43/0; factory UI: 43/0; UI scope: 34/0.
- Execution records: 67/0; worker wiring: 56/0; factory loop: 42/0;
  re-land: 53/0; reservation policies: 47/0; dispatch setup: 48/0.
- Landing containment: 60/0; canary: 34/0; static secret scan: 49/0.
- Space census: 53/0; Docker census: 56/0; run finished: 65/0;
  admission fixture: 52/0; space principals: 57/0.
- Actual store guard and nested guarded query journey: 47/0.
- Shared-descriptor census: 50/0; both exact historical tips also green.

273 input rows belong to repaired groups with green representatives; this is
attribution, not a full-leg rerun. 24 remain assigned to proof-reader incompatibility
(2), partially repaired space-run / host visibility (11), inherited live captures
and qualification resources (3), and unreproduced aggregate scratch/census (8).
The full space-run representative remains 56/10; proof remains 39/2.

Historical paired comparisons use 8656888f8 and 382c847b6. All tests selected
one suite and ran via the requested pc2 runner or host_heavy. No full leg,
verify.sh, load generator, guard bypass, or guard-off marker. The running candidate
worktree was untouched. No claim is made for unexecuted suites beyond the abort.

Personal setup: 0 findings (built-in shapes; no installation).
Template sync: 361 pairs passed. Space boundary, wall-clock census, Python syntax
and whitespace checks passed. gate_unconfined.json is unchanged.
