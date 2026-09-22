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
the full domain has been executed. Final gate timing, actual generated
counts and all observed disagreements will be recorded after the gate run.
