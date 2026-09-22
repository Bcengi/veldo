# Grammar-generated oracle fixture: stopped at the cost limit

Implementation stopped under the requested 60-second rule. The specification
remains ready, not complete: full derivation generation, boundary coverage and
oracle observation are UNPROVEN. The baseline domain was not reduced to obtain
a pass. The production reader and its engine mirror are unchanged.

## Measured domain and cost

| Inventory | Expected | Actually generated in the gate's unit run |
| --- | ---: | ---: |
| Base derivations | 510,928,432 | 2,059,668 |
| Separate multiline/BOM witnesses | 56 | 0 |
| All derivations | 510,928,488 | 2,059,668 |
| Boundary edits | 5,013,490,520 | 19,756,060 |

Generation took **60.000076 seconds**, and the new suite took **60.001075
seconds** in the direct unit run. It returned normally with
`generation_incomplete`; the completeness assertions failed. This was not a
crash, hang, smaller qualification domain, or passing timeout. The full-domain
oracle phase did not start: compared=0 and unobserved=5,524,419,008. No full-domain
agreement is claimed.

The separate arithmetic counter, which does not call the scalar or tree
generator, counts 896 scalar derivations per block value. Two-child root maps
alone account for 503,196,096 derivations: 78 distinct-key pair derivations,
898 child choices (including the two empty flow collections), and eight
formatting choices. These cross-products and their generated boundary neighbors
drive the cost. These are expected counts, never relabeled as generated counts.

`baseline-prefix.json` records actual counts, production/alternative coverage,
missing witnesses, grammar revision, implementation/fixture digests and the
prefix inventory digest. `expected-counts.json` records the independently
computed totals. Duplicate-byte derivations remain separate records.

The exact recorded prefix digest is:

```
a0ad33c7b088aa0df56b2eb56eee5f143e3c4d6a18af405f10abeef325bee463
```

Regenerate that prefix outside the repository with:

```
python3 proof/VELDO-0118/reproduce_prefix.py --count 2059668 --output /tmp/grammar-prefix.jsonl
```

The reproducer explicitly reports a prefix, never full qualification. Its
one-derivation smoke check ran; the full prefix was not rerun after the cost
stop. To request an unlimited inventory and raw oracle observations explicitly:

```
python3 scripts/fixtures/grammar_cases.py --count
python3 scripts/fixtures/grammar_cases.py --inventory --seconds 0 --output /tmp/grammar-inputs.jsonl
python3 scripts/fixtures/yaml_oracle.py --inventory /tmp/grammar-inputs.jsonl --output /tmp/grammar-oracle.jsonl
```

Those unlimited commands were not run. They do not change the baseline bounds.
The counts and coverage describe only this versioned finite grammar; they do
not establish coverage of an unbounded language or close AC1's reconciliation.

## Clean-tree gate

The final gate started from clean commit
`69def368bbf63e2735797df5496efbdcad0b883b` and reported:

```
selftest: 5569 passed, 3 failed
GATE: RED (69def368bbf63e2735797df5496efbdcad0b883b)
```

The three false rows are `grammar/all-bounded-derivations-exist`,
`grammar/all-boundary-edits-exist`, and `grammar/oracle-observations-complete`.
The independence and capability-control rows passed. The integration stage
completed both its mutated run (338 seconds) and pristine run (339 seconds),
each with the same 5,569 passed and three failed assertions; it attributed no
new failure to the spend writer. Unit was the final gate's only failed stage.

The clean starting-tree gate at `59e6fff` took **569.874720 seconds**; the
clean post-change gate took **1,033.377872 seconds**. The measured difference
is **463.503151 seconds**, exceeding the requested 60-second limit. This is
an observed wall-time difference on this machine, including ordinary timing
variation and the extra pristine comparison caused by the new completeness
failures. It is not an estimate or a claim of isolated microbenchmark precision.

The starting gate had 5,567 passed and zero failed unit assertions, but was
RED on two reachable-history secret-inventory entries. The final security
stage reported zero outstanding entries and passed. Neither history nor
security policy was changed by this work. `verification.json` retains both
observations, timings, platform and full-log digests. Raw gate logs are not
committed. One earlier post-wiring attempt was cancelled before reaching the
new suite to separate lexical counting from enumeration; it is excluded from
the timing comparison.

## Every observed disagreement, for VELDO-0119

Before the cost stop, a complete diagnostic comparison ran over the separately
named mutation-control domain: **919 derivations, 8,685 boundary edits, and
9,604 oracle observations**, with PyYAML 6.0.1. It found **192 disagreements**.
All concern accepted derivations: 180 differing values and 12 reader refusals.
The 192 inputs are distinct. No generated accepted control was invalid general
YAML. Across accepted inputs and neighbors, the oracle observed 5,588 valid
and 4,016 invalid general YAML documents.

Every disagreement is retained in `control-disagreements.jsonl`, including
input bytes, derivation, grammar production, reader answer, raw oracle
observation and normalized dialect answer. `control-comparison.json` binds
the run to input/observation digests and the reader and fixture digests.
For example, `a: |\n \n` yields `{"a": "\n"}` in the reader and
`{"a": ""}` in the oracle; `a: {a: }\n` is refused by the reader but
composes to `{"a": {"a": null}}`. No reader defect is fixed here.

Reproduce all diagnostic observations and findings:

```
python3 proof/VELDO-0118/compare_control.py --output-dir /tmp/grammar-control
```

This control domain exercises the fixture and its assertions; it is not a
replacement for the baseline domain and cannot close full agreement.

## Mutation drives and capability controls

Each declared falsifier and a second distinct mutation ran on a temporary
fixture copy. Every run completed all five assertions; each named target
became false, and every unmutated control was green. `mutations/` contains
the eight applied diffs, and `mutation-controls.jsonl` records the results.
`capability-controls.json` records installed, absent, import-failure,
missing-internal-dependency and runtime-failure outcomes for both reader
and policy fixture consumers. A separate actual `python3 -S` absence drive
reported, for each consumer, generated=1, compared=0, unobserved=1, agreed=0
and `oracle_unavailable`.

After the gate, both gate byproducts were restored and the requested full
`python3 scripts/check_teeth_mutations.py` run exited zero. Its last line was:

```
{"mutations_rejected": 41, "green_suites": {"47_veldo_0107_ipc.py": 23, "48_veldo_0108_relay.py": 10, "44_veldo_0105_startline.py": 8, "46_veldo_0029_enrollment.py": 7, "49_veldo_0109_unavailable.py": 5, "53_veldo_0118_grammar.py": 5}}
```

`teeth-all.jsonl` retains the compact complete driver results. No per-case
inventory dump, gate stamp, or event-log byproduct is committed. No push,
merge, deployment, or independent approval is represented by this work.
