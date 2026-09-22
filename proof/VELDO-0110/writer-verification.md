# Write-side full gate verification

- Command: `bash scripts/verify.sh`
- Exit status: `1`
- Result: **RED**
- Verified implementation commit: `c38e8d59aeeeddbbb20792a991c209bee7ad1515`
- Implementation Git tree: `f7f9cf53d0c7b76940170b69f3a7de9fd4a57065`
- Gate completion: `2026-09-22T17:30:34Z`; gate-reported tree: `clean`.
- This run began after the final implementation commit; no source changed during it.
- Unit result: **5,549 passed, 0 failed**.
- First-use integration: **PASS**, including its complete suite over a writer-mutated disposable copy.
- Catalog: **8 run, 15 not applicable, 0 waived, 0 undeclared**.

The **security inventory stage failed**. It names one exact synthetic fixture line,
`sha256:8cd53e2dae3e`, in two locations: `proof/VELDO-0110/gate.log:47` in the
working tree and the same line in reachable blob `253e1c73`. This file was already
present at the starting commit 23e1a2b. The line is the expected guardrail diagnostic
produced by `scripts/suites/01_warp_0101_reviewer_notes.py` for its temporary
`pkg/dirty.py` negative control, whose payload is `FORBIDDEN_TOKEN`.
The inventory recognizes its quoted diagnostic as a literal credential assignment.
It is not a writer round-trip failure, but it still makes the canonical gate red.

All other stages passed: lint, unit, first-use integration, generated artifacts,
documentation, packaging, template synchronization, the built-in secret scan,
contracts, and the mechanizable shape gate. This is **not a green verification**.
The unresolved work is disposition of the historical fixture finding under the
repository's human-decision policy, then a full green gate. Neither the scanner nor
its dispositions were changed; no human decision or independent approval is claimed.

## Writer evidence

| Criterion | Evidence |
|---|---|
| AC5 | Shared `yamlish.dump` and `render_document`; all strings quoted; tracker guard exact-source comparison against 23e1a2b and generated sanitization checks |
| AC6 | 3,580 generated documents; exact value/type agreement with the strict reader and PyYAML 6.0.1; external-emitter reverse direction; eight writer tests passed |
| AC7 | [Corpus report](writer-corpus.json): all 331 baseline paths plus the continuation spec, 332 current documents, 331 with front matter re-emitted, **0 differences/refusals**; the prose-only index is preserved verbatim |
| AC8 | Suite 52 boundary check; planted renamed serializers fail, a delegating adapter passes; all eight changed runtime modules have byte-identical engine mirrors; the shared module remains in both init lists |

[Writer tests with PyYAML](writer-properties.log) and
[without site packages](writer-without-oracle.log) record the two environments.
Without PyYAML, **three oracle tests skip by name**; a separate regression asserts
those skip results. The corpus audit without site packages also reports its oracle
stand-down by name while the strict-reader round trips complete with zero differences.

## Gate log and byproducts

[Gate output](writer-gate.log) retains the complete run except for its one expected
negative-test diagnostic at line 47, replaced by the exact line digest.
This prevents the new evidence file from creating another copy of the known
inventory finding. The failing security stage and all its finding references are
retained. The existing read-side gate log and its historical record are untouched.

- Raw captured log SHA-256: `30570879524e7c23e846d591de6d0b1bc1259ad846cc036961cf5e2f4c1cda98`.
- Stored log SHA-256: `9b111578c4e0979d21737f7055f6f8213e1130ceb6a0943d218b9550bb375b15`.

The checkout's `.veldo/last_verify` and `.veldo/events.jsonl` are restored before
the evidence commit and are not committed. No push, merge, or other worktree change
was made. The reviewer's merged checkout owns its eventual verification stamp.
