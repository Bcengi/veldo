# Grammar coverage fixture

The owner-approved coverage domain replaces the measured exhaustive domain
of 510,928,488 derivations and 5,013,490,520 boundary edits (Telegram 28810,
answering 28808 about 28805). The specification remains ready. AC3 and AC4,
the production reader, and all 192 historical disagreement records are
unchanged. Suite 54 avoids the number reserved for VELDO-0123 elsewhere.

## Measurement before rewriting the rows

`preflight-measurement.json` was recorded and committed at `b83a8ab` before
the acceptance criteria or suite rows changed. It counted 22 productions,
934 lexical alternatives, 132 parent/child pairs and 457 applicable boundary
rule/site targets. Generation took 1.868413 seconds; generation plus full
oracle/reader observation took 3.775353 seconds. Multiplying by the gate's
two normal suite invocations gives 7.550706 seconds of measured added work,
below the 60-second stop threshold. This is a measurement of the added work,
not a before/after wall-clock measurement of the entire repository gate.

The final boundary construction uses tabs in physical indentation. Nine
preliminary edits put tabs in separator whitespace instead; their complete
observations remain in `preflight-disagreements.jsonl` for audit, but those
nine records are fixture mistakes, not reader defects. No target was removed. Final formatting witnesses also use nested documents
so both indentation alternatives occur in the emitted bytes; flat documents
receive no indentation credit.
`coverage-measurement.json` records the corrected run: generation 1.839771
seconds, total 3.782810 seconds, or 7.565619 seconds across two invocations.
The direct suite control took 3.820577 seconds, including its capability and
independence assertions. The canonical gate result will be recorded after
running this committed implementation from a clean tree.

## Complete target inventory

| Criterion | Independently counted | Enumerated | Witnessed |
| --- | ---: | ---: | ---: |
| Productions | 22 | 22 | 22 |
| Lexical alternatives | 934 | 934 | 934 |
| Direct parent/child pairs (k = 2) | 132 | 132 | 132 |
| Applicable boundary rule/sites | 457 | 457 | 457 |

`coverage-targets.json` retains every required identity. The generator derives
these identities from the versioned production graph and lexical tables;
a separate arithmetic counter does not call target enumeration or rendering.
Coverage is collected from emitted derivation trees. Both counts and exact
missing/unexpected sets are checked. A site is a parent/slot/child edge,
plus the document-root site; recursive occurrences share their grammar site.
This is complete coverage of declared targets, not every bounded derivation
or every unbounded input.

The final domain has 1,088 accepted witnesses and 457 boundary inputs.
All 1,545 received independent observations with PyYAML 6.0.1, with zero
unobserved inputs and zero oracle errors. Duplicate-byte derivations remain
separate records. The input inventory digest is:

```
708592a8d2e43d631023d7b30119cd2be78d534c7f8cb6ccf343df0f456df635
```

Regenerate the compact report, complete input inventory, raw observations
and every disagreement outside the checkout:

```
python3 scripts/fixtures/grammar_cases.py --count
python3 proof/VELDO-0118/measure_coverage.py --output-dir /tmp/grammar-coverage
```

## Disagreements owned by VELDO-0119

`control-disagreements.jsonl` preserves the original 192 records byte for
byte. `coverage-disagreements.jsonl` adds all 26 final coverage disagreement
records: 22 distinct byte strings, including 16 not in the historical file.
Every record includes source bytes, production/derivation, reader answer,
raw oracle observation and dialect answer. Three witnesses contain literal
DEL, which the inherited lexical registry permits but PyYAML rejects. Other
findings concern blank block scalars and empty flow mapping values. All 457
boundary witnesses are refused by the reader. No parser defect was fixed.
Neither complete observation nor a green fixture claims reader agreement.

The original exhaustive count, prefix and stop evidence remain in
`expected-counts.json`, `baseline-prefix.json` and the earlier git history.
`compare_control.py` still reproduces the historical 192 records;
`reproduce_prefix.py` explicitly reproduces only a requested prefix.
The CLI's `--legacy-exhaustive` and `--control` options are historical,
separate domains and are never used to qualify current coverage.

## Mutation and capability controls

The registry in `scripts/check_teeth_mutations.py` drives two mutations for
each of the five named rows over the complete current coverage domain.
Each drive must complete all five assertions, turn its named target false
and have an unmutated green control. Applied patches are retained under
`mutations/`; `omit-first-derivation.diff` is a historical revision-1 patch.
The full driver exited zero: 43 mutations rejected, including all ten current
grammar drives. `teeth-all.jsonl` retains its complete compact receipt and
`mutation-controls.jsonl` contains the ten grammar results, all re-driven
after correcting the indentation witnesses. The earlier gate attempt was
explicitly stopped during unit execution for that correction; it produced
no GATE result and is excluded from final verification and timing.

`suite-control.json` records installed, absent, import-failure,
internal-dependency-failure and runtime-failure controls for both consumers.
`coverage-absence.json` records an actual `python3 -S` run: both consumers
print `oracle_unavailable STANDS DOWN`, compared=0 and unobserved=1,545.
Generation and reader execution still run. These direct controls contain
26 shared preamble assertions plus the five grammar assertions.

No independent review, merge, push or approval of this implementation is
asserted. The reviewer supplies the verification stamp for the merged tree.
