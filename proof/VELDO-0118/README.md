# Grammar-generated oracle fixture

Work in progress on build-veldo-0118, starting at 59e6fff. The reader and its
engine mirror are unchanged. No push, deployment, merge or independent
approval is represented by this work.

The generator enumerates syntax derivations without consulting the reader.
The count in `expected-counts.json` is computed by a separate recursive
feature polynomial, not measured as generated or compared cases. The full
qualification retains duplicate-byte derivations and generates every
applicable registered edit. A 60-second operational stop reports incomplete
generation as red, never as a smaller passing domain.

The assertion controls use an explicitly separate domain: 919 generated
derivations and 8,685 boundary edits. The baseline remains 510,928,488
derivations, including 56 separate multiline/BOM witnesses, and
5,013,490,520 boundary edits. Full qualification has not yet completed.

All eight mutation drives completed their five assertions. Each declared
falsifier and a second mutation made its named row false; every unmutated
control was green. `mutation-controls.jsonl` records the results and
`mutations/` retains each applied diff. Reproduce with:

```
python3 scripts/check_teeth_mutations.py --finding 118
```

Capability controls exercise both reader and policy consumers with PyYAML
installed, absent, broken during import, missing an internal dependency,
and broken at runtime. A separate `python3 -S` drive confirmed actual
top-level import absence: each consumer generated one case, compared zero,
reported one unobserved case and zero agreements, with `oracle_unavailable`.

The clean starting-tree gate took 569.874720 seconds and reported
`selftest: 5567 passed, 0 failed` and
`GATE: RED (59e6fff1ccaa371e141fd1ea9d147432e28c880c)`.
Its existing security failure is two undispositioned reachable-history
entries: `proof/VELDO-0123/gate-cold.log:47@9a83d484` and
`proof/VELDO-0123/gate-warm.log:47@a6b5f28a`. Neither is changed here.

Regeneration commands (full inventories belong outside the checkout):

```
python3 scripts/fixtures/grammar_cases.py --count
python3 scripts/fixtures/grammar_cases.py --inventory --seconds 0 --output /tmp/grammar-inputs.jsonl
python3 scripts/fixtures/yaml_oracle.py --inventory /tmp/grammar-inputs.jsonl --output /tmp/grammar-oracle.jsonl
```

The unlimited commands are explicit qualification requests, not claims that
the full domain has been executed. Final gate timing and actual generated
baseline counts will be recorded after the gate run.

## Control-domain findings for VELDO-0119

`control-comparison.json` records a complete diagnostic comparison of the
separate control domain: 919 derivations, 8,685 boundary edits, 9,604 oracle
observations, and 192 disagreements. Every disagreement is retained in
`control-disagreements.jsonl`, with input bytes, derivation, production,
reader answer, raw oracle observation and normalized dialect answer.
All disagreements concern accepted derivations: 180 differing values and
12 reader refusals. No generated accepted control was invalid general YAML.
The controls produced 5,588 valid and 4,016 invalid general YAML inputs.
These observations do not qualify the much larger baseline domain.

For example, `a: |\n \n` yields `{"a": "\n"}` in the reader and
`{"a": ""}` in the oracle. No reader change is made. Reproduce all findings:

```
python3 proof/VELDO-0118/compare_control.py --output-dir /tmp/grammar-control
```

The scalar count now uses separate arithmetic rather than scalar enumeration.
An initial post-wiring gate attempt was cancelled before reaching the new
suite to make that independence correction; it is excluded from timing
comparisons. The completed clean-tree gate below is the measured run.
