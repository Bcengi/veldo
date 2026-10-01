# Capture relocation repair

Diagnostic follow-up to the three finding 127 `live.py` mutations at
`19944b3c`. This is selected-suite evidence only, not gate verification or a
passed unit-evidence manifest. Independent review and the gate remain with
the owner.

## Cause

The failure depends on the module's location, not its bytes or a stale capture
hash. `scripts/check_teeth_mutations.py:9835` materializes a separate module;
line 9872 writes the original bytes for `noop`. Its worker substitutes that
copy's path for the suite's `LIVE_PATH` anchor (line 9906). These three cases
have no sibling-copy configuration.

`proof/VELDO-0127/live.py:21` derives `HERE` from `__file__`, and its Codex
capture loads `HERE / 'loopback.py'` at line 135. The relocated driver has no
such sibling. The suite's `attempt()` catches `FileNotFoundError`, returns no
capture, and the nonempty capture assertion fails. Merely copying loopback
would also relocate its own repository-relative `.veldo` and proof dependencies.

Before the repair, the honest suite had 53 passing rows; the exact byte-identical
no-op had 52 passing rows and only `VELDO-0127 review/codex-capture` failed.
Its diagnostic was `capture error=FileNotFoundError`, with no copied loopback
present. The original and no-op SHA-256 were both:

```
e8139dbcb7273cd5cf4a1f84325150c3eee25653d260514042202ad9420f4cdb
```

## Fix

Commit `43d2b4ab` makes suite 86 explicitly supply the unchanged dependency
directory from its own tree. It still imports the supplied driver, including
any mutation. As a regression control, every standalone run now relocates that
driver and appends a comment before importing it, so baseline testing also
exercises this boundary. The real loopback capture and all existing equality,
model-refusal and probe assertions remain intact. Capture failures now name
the caught exception in their assertion detail.

No production driver, capture fixture, mutation registration, acceptance
criterion or digest check changed.

## Reproduction

The exact harness no-op is byte-identical relocation; an additional comment
control separately verifies changed bytes with unchanged behavior.
[reproduce-capture-controls.py](reproduce-capture-controls.py) reads the three
registered edits as AST data, applies each to a private copy, and substitutes
that copy into a private suite. It does not import or run either mutation
driver. Its only child test command is:

```
python3 scripts/selftest.py --suite 86_veldo_0127_agent_configuration
```

Run the honest command from the checkout with output redirected to a log. Run
each control separately from the checkout, substituting one MODE from the
results below:

```
python3 proof/VELDO-0127/reproduce-capture-controls.py MODE /tmp/capture-control.log > /tmp/capture-control-result.json 2>&1
```

The script retains a JSON record beside the log and asserts exactly the named
failed rows, successful completion of the suite, and the expected dispatcher
exit status. Green selected suites intentionally exit 2; assertion-red suites
exit 1. Every run was sequential. The gate, full selftest and both mutation
scripts were not run.

## Results

Exact output excerpts and source digests are retained in
[capture-relocation-results.json](capture-relocation-results.json).

| Version | Mode | Passed / failed | Failed assertion row |
| --- | --- | --- | --- |
| before | `baseline` | 53 / 0 | none |
| before | `noop` | 52 / 1 | `VELDO-0127 review/codex-capture` |
| after | `baseline` | 53 / 0 | none |
| after | `noop` | 53 / 0 | none |
| after | `comment` | 53 / 0 | none |
| after | `role127-lead-model-mode-ignored` | 52 / 1 | `VELDO-0127 review/codex-capture` |
| after | `role127-loopback-tool-observation-lost` | 52 / 1 | `VELDO-0127 review/codex-capture` |
| after | `role127-probe-capture-omitted` | 52 / 1 | `VELDO-0127 review/probe-terminal` |

All three post-fix mutants completed the suite and failed only their registered
assertion row. The model mutant fails `unknown model is refused`; the loopback
mutant fails the capture comparison with `capture error=None`, proving it is
an assertion failure after successful capture; the probe mutant fails the
zero-turn result and assistant-count assertion. The byte-identical and
comment-only copies both pass all 53 rows. No mutants were removed.
