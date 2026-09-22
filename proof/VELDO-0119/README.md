# Shared reader grammar agreement

Decisions and full corpus outcomes were committed at `fd36a1c` before any
reader change. `dispositions.jsonl` assigns every one of the 218 historical
records by original filename/line and input digest. Duplicate byte witnesses
remain distinct. `control:N` means line N of
`proof/VELDO-0118/control-disagreements.jsonl`; `coverage:N` means line N of
`proof/VELDO-0118/coverage-disagreements.jsonl`. All 218 now agree through
both shipped readers.

| Root cause | Records (control + coverage) | Disposition | Commit | Assertion |
| --- | ---: | --- | --- | --- |
| All-blank clipped literal/folded blocks retained a spurious newline | 180 + 20 | (a) reader defect; clip excludes trailing empty lines | `0871194` | `reader/generated-grammar-agrees` |
| Empty flow-map values refused at comma/closing brace | 12 + 3 | (a) reader defect; written grammar explicitly permits mapping empties | `dd2d162` | `reader/generated-grammar-agrees` |
| Raw literal DEL rejected by general YAML | 0 + 3 | (c) already documented plain/continuation dialect permission | `cb1fd0a` | `reader/generated-grammar-agrees` |

No cause required disposition (b): no accepted syntax, target, input bytes or
generator changed. The grammar JSON digest remains
`4251a3e2891b059b9c92fd7eb49207149fd9be6d8f81b213079bcbf88266e404`.
DEL is explicitly permitted by the inherited written lexical registry.
The independent fixture adapter retains PyYAML's original invalid-YAML
observation, then composes a length-preserving printable substitution and
reverses it only in plain values. This supplementary observation does not
consult either reader. `literal-del-observations.json` retains all three.
Booleans, null-like words and leading-zero identifiers continue to use the
existing style/spelling rule: only canonical decimal integers become ints.
`dialect-samples.json` preserves raw YAML tags beside those typed answers.

Suite and mutation wiring landed in `5110cbb`. The footprint was expanded to
name the adapter, consumer and mutation harness files actually changed.
The spec remains ready; no self-approval, independent review, merge or push
is claimed.

## Complete domain and observations

Both copies independently execute 1,088 accepted witnesses and 457 boundary
inputs: 1,545 executions per copy, 457 refusals per copy, 1,545 independent
oracle comparisons, zero unobserved and zero disagreements with PyYAML 6.0.1
plus the documented adapter. Boundaries retain separate classifications:
225 invalid YAML and 232 valid YAML outside this dialect.

The unchanged input inventory digest from VELDO-0118 is
`708592a8d2e43d631023d7b30119cd2be78d534c7f8cb6ccf343df0f456df635`.
All 22 productions, 934 lexical alternatives, 132 directly allowed nesting
pairs and 457 boundary rule/site targets remain covered. The complete target
identities are in `proof/VELDO-0118/coverage-targets.json`; `measurement.json`
binds that inventory by SHA-256 and reports missing/unexpected sets.
This is the declared coverage domain, not all possible unbounded strings.

`observations.jsonl.xz.b64` contains every raw observation and both reader results,
including derivation, input digest, source, boundary classification and typed
expected tree. `measurement.json` binds its uncompressed SHA-256, grammar and
fixture versions/digests, both implementation digests and executed inventories.
Failures retain source, refusal line, and differing field/type/value.
The actual absent-oracle run is in `absence.json`; it explicitly stands down
agreement while still executing both readers and all boundaries. Full-domain
absent, broken-import, broken-runtime and omitted-input controls never qualify.
The omitted run executes 1,544 inputs per copy and records one unobserved input.

## Mutations

Every drive uses a temporary copy, completes all named rows, and fails the
named assertion. `mutation-controls.jsonl` records the six individual drives
with unmutated controls. `gate-mutation-controls.jsonl` additionally retains
exact baseline, no-op and mutant observations from the canonical mutation
stage. The exact applied diffs are under `mutations/`.

| Named row | Declared falsifier | Second mutation |
| --- | --- | --- |
| `reader/generated-grammar-agrees` | Strip a hash inside a quoted scalar | Coerce leading-zero spellings to integers |
| `reader/generated-boundaries-refuse` | Allow duplicate mapping keys to overwrite | Accept an unclosed flow collection |
| `reader/agreement-requires-full-oracle-domain` | Count unavailable oracle inputs as comparisons | Remove omitted input from the required domain |

All six are registered as finding 119 in `scripts/check_teeth_mutations.py`.
The stage freezes `engine/.veldo` as well as the repository reader so the
second independently loaded copy is present in every temporary drive.

## Real corpus

`corpus-before.json.xz.b64` records full parsed trees/refusals and parser inputs
for both copies across 651 documents at `b34d17d`: 49 YAML/YML documents and
602 Markdown documents. It includes specs, plans, manifests, substrate records,
engine copies and templates; unread Markdown prose is omitted. This deliberately
includes documents beyond runtime callers. Per copy: 509 parsed values,
141 absent-metadata results and one refusal. The pre-existing refusal is
`proof/decisions-archive/round1-v2/REV-DEC-0001.yaml:12` (colon in plain scalar).

Each `corpus-after-*.json` compares the same frozen inputs following its fix.
All three comparisons contain an empty changes array: no real document changes
meaning or starts/stops refusing. The owner's `.veldo/policy.yaml` retains its
entire parsed tree; the audit exits with an explicit stop if that ever differs.
`baseline-validation.json` additionally reloads both original readers and
every full document from Git at `b34d17d`, exactly reproducing all saved
input/reader digests and parse outcomes.
Only `yamlish.py` changed under `.veldo/`, mirrored byte-identically into
`engine/.veldo/`. No policy content was edited.

## Cost and gate

`timing.json` measures a 3.917624-second suite run, or 7.835248 seconds across
the gate's two normal invocations. Sequential mutation-stage runs on identical
clean inputs took 19.377806 seconds without finding 119 and 23.881394 seconds
with it, adding 4.503588 seconds. Total measured added gate work: **12.338836
seconds**, below the 60-second stop limit. The baseline registry filter was
in memory for measurement only; no gate or source configuration was changed.
The full mutation stage rejected all 54 registered mutations.

The canonical gate started from clean commit `96935a747ca33adcca3b23fbb29c5e08ed5067e6`
and completed in 619.442338 seconds. `verification.json` records its log digest,
integration result and actual suite/mutation-stage timings.

```
selftest: 5580 passed, 0 failed
GATE: GREEN (96935a747ca33adcca3b23fbb29c5e08ed5067e6)
```

The two checkout-local gate byproducts were restored before the final evidence
commit. The reviewer supplies the stamp from verification of the merged tree.

The first gate attempt at `5110cbb` completed with 5,580 unit and integration
checks passing and all 54 mutations detected, but was red because the docs
sweep treats xz proof files as text. The final proof uses an ASCII base64
envelope around those same compressed bytes; decoded contents are unchanged.
`initial-verification.json` retains that failed attempt separately.

## Reproduce

```
python3 proof/VELDO-0119/measure.py --output-dir /tmp/veldo-0119-observations
python3 proof/VELDO-0119/corpus.py --output /tmp/veldo-0119-corpus.json
python3 scripts/check_teeth_mutations.py --finding 119 --diff-dir /tmp/veldo-0119-diffs
bash scripts/verify.sh
```

The first command regenerates complete unfiltered observations and coverage
inventories outside the checkout. The frozen corpus includes the original
parser inputs so source edits after the baseline cannot mask a reader change.
