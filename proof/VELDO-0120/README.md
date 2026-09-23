# VELDO-0120 proof

Built on `build-veldo-0120`. The policy reader needed no production change:
`.veldo/fix_validation_record.py` and its engine mirror remain byte-identical
to the starting revision, as does `.veldo/policy.yaml`. No push, merge,
independent review or self-approval is claimed; the specification remains ready.

## Measurement before rows

The first measurement is retained in `measurement-initial.json`. The prospective
witness/site/boolean/commit tensor is
`(1088 + 457) * 4 * 18 * 15 = 1,668,600` inputs. A coverage construction generated
8,093 inputs in 1.804 seconds and checked both reader copies with PyYAML in
0.737 seconds. Linear extrapolation gives about 372 seconds to construct and
152 seconds to check that tensor. It was not enumerated.

The initial root-scalar discrepancy is retained, not filtered away: the shared
dialect permits mapping and sequence documents, so a scalar root is a syntax
refusal even though general YAML accepts it. Quoted policy-key spellings and
boundary edits directly on policy nodes complete the final coverage inventory.

| Construction | Inputs |
| --- | ---: |
| Every supported grammar witness at each of four policy positions | 4,352 |
| Every shared boundary witness at each position | 1,828 |
| Every scalar lexical witness directly in each setting | 1,792 |
| Schema partitions and named-key spellings | 133 |
| Additional applicable edits directly on policy nodes | 91 |
| Total | 8,196 |

The four positions are document root, `fix_validation`, `required`, and
`from_commit`. Full grammar documents placed in scalar settings intentionally
exercise invalid shapes; the additional direct scalar placements exercise their
lexical meaning. A document BOM moves to the enclosing document's start. The
shared grammar owns rendering and exclusion edits. Schema partitions cover all
18 case variants of the six boolean words, 15 commit lexical classes, absent
settings, scalar/list/map/empty invalid shapes, and plain/single/double quoted
policy keys in block/flow/BOM/CRLF forms. No ancestry or commit resolution is
performed. All inputs are constructed before production readers answer.

`expected_ids()` derives required witness identities from grammar declarations,
separately from emission. Exact Counter equality checks expected, both executed,
and compared inventories, including multiplicity. `measurement.jsonl` retains
all inputs, raw independent observations, expected schema outcomes, reader
outcomes and input SHA-256 values. `measurement.json` binds that artifact to its
SHA-256, both implementation digests, fixture digest and grammar revision.

## Agreement and refusal

Both readers produce exactly 3,022 setting outcomes, 3,254 schema refusals and
1,920 syntax refusals, with zero disagreements and zero unobserved inputs.
Among syntax-refusal cases, PyYAML accepts 978 as general YAML and rejects 942.
Those general-YAML inputs still refuse under the shared dialect.

The oracle composes YAML into a raw tree before the existing separate dialect
adapter interprets it; the independent policy schema adapter then computes the
flag and exact start-line string. YAML 1.1 tags are observations, not policy
semantics: leading zeros remain strings, canonical integers decimalize without
loss, null words remain words, quoted hashes remain data, and the documented
plain DEL extension uses the VELDO-0119 oracle adaptation. No intentional dialect
difference is omitted from qualification.

The current owner settings remain `required: true` and
`from_commit: 5c6473325b19604b9b1d28b8af8eb488a4a64e8c`.
The owner file's SHA-256 is recorded in `measurement.json`.

## Oracle accounting and assertion drives

Full-inventory absent, broken-import, broken-runtime and omitted-result runs
cannot qualify. Absent or broken oracle runs execute stdlib grammar and schema
checks over every input while recording zero comparisons. A real `python3 -S`
run is retained in `absence.json`; qualification explicitly stays open there.
An omitted expected result breaks inventory equality. These development controls
are not substitutes for the canonical gate.

All six mutations are registered in `scripts/check_teeth_mutations.py` and run
on temporary copies. The exact applied diffs are in `mutations/`; `timing.json`
and `mutation-controls.jsonl` retain baseline, no-op and mutant observations.
Every named row is present and false in completed mutant runs, never inferred
from a crash or timeout.

| Named row | Declared falsifier | Second mutation |
| --- | --- | --- |
| `policyread/generated-settings-agree` | Strip quoted hash text in the syntax reader before schema interpretation | Coerce leading-zero commit text to an integer |
| `policyread/generated-invalid-is-not-absent` | Turn a shared-reader syntax error into an empty policy | Turn an invalid policy block into an empty policy |
| `policyread/generated-oracle-coverage-is-honest` | Qualify an absent oracle | Remove the omitted result from the required inventory |

The added-work measurement includes two complete suite executions (unit and
first-use integration) plus the isolated required mutation stage, including its
setup. Its conservative total is 23.196 seconds, below the 60-second ceiling.
The initial gate attempt was stopped after the footprint assertions failed;
`initial-verification.json` records why. Both explicitly authorized extensions
are now in the spec's machine-readable footprint and prose history.

## Reproduce

```
python3 -B proof/VELDO-0120/measure.py /tmp/policy-measurement.json --records
python3 -B scripts/check_teeth_mutations.py --finding 120 --diff-dir /tmp/policy-mutations
python3 -B proof/VELDO-0120/timing.py /tmp/policy-timing.json
bash scripts/verify.sh
```

Generation is deterministic; timing is observational. The regenerated JSONL's
SHA-256 must match `measurement.json`'s `observations_sha256`. The historical
seventeen-example suite remains a regression check and explicitly points to the
new suite for complete generated qualification.

## Canonical gate

Started from clean commit `d94ea52c9cf08706eb30083719c917e2c64b7831`.

```
GATE: GREEN (d94ea52c9cf08706eb30083719c917e2c64b7831)
selftest: 5678 passed, 0 failed
mutations: passed registered=84 executed=84 rejected=84 workers=112 elapsed=59.210s
```

First-use integration passed over the sanctioned writer mutation. See
`verification.json` and `gate-mutations.json` for the recorded results.
The two checkout-local gate byproducts are restored before the final proof
commit; the reviewer records the stamp for the merged tree. Final proof-only
changes follow this verified commit and do not claim to be its gate stamp.
