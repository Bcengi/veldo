# VELDO-0124 round 3, 2026-10-29

Scope: fixcheck N1 and N2 at baseline `754b9101`. Implementation commit:
`6570d20d`. The Mac owner action was not attempted. Acceptance text is unchanged,
and all acceptance criteria remain pending native qualification and review.

## Forged qualification coverage

Each new case changes one evidence property while keeping all other properties
valid. The outside file contains the original document and matching digest. The
relative path resolves to the original protected file from the test's working
directory. The blocked document retains every required row, with exactly one
value changed to `blocked`. Schema and kind changes have updated reference
digests. Every case requires the named qualification refusal and its exact
ValueError cause; a KeyError fails the test. Intact evidence admits preflight
after the fixture is restored, and no worker was bootstrapped by a refused case.

| Removed check | Expected refusal cause | Mutant artifact stem |
| --- | --- | --- |
| Protected root containment | evidence must be protected | AC1-evidence-protected-root |
| Passed row | evidence row | AC1-evidence-passed-row |
| Document schema | evidence binding | AC1-evidence-schema |
| Native kind | evidence binding | AC1-evidence-native-kind |
| Absolute path | absolute evidence path required | AC1-evidence-absolute-path |

Each stem identifies a patch and log in `falsifiers/`. Each patch disables only
its named check in an isolated module copy. Its required failed row is
`AC1/forged-qualification`. Installed and canonical runtime sources are unchanged.
The existing ten mutants remain in the same ticket runner.

## Verification

All five new mutants are RED with exit 1 on `AC1/forged-qualification`. Each log
shows the expected refusal was missing for its own case. All fifteen ticket
mutants are rejected on their named rows; the negative control runner exits 0.
`qualification-red-green.json` maps each new mutant's patch and failed row to
the common restored GREEN log, `suite-103.log`: 29 owning rows, 55 total checks
passed, zero failed, partial exit 2. The unchanged profile source SHA256 matches
every new mutant's recorded source SHA256.

Suite 104 capture is pending. The original queued runner reopened that log after
a supervised rerun, so its final capture is awaited. `supervised-runs.json`
preserves the earlier run metadata; `runs.json` records the original runner.
All commands run under `/home/dmitry/.local/state/core-gates/.gate.lock`.
These are scoped diagnostics only. No full gate or native Mac test is part of
this round, and no native qualification or landing decision is claimed.

## Fixture identity and historical correction

The round 2 driver now uses `Fixture <fixture@example.invalid>` for fixture
commits. The round 2 README corrects its historical blocked-row coverage claim:
that case could fail because other rows were absent. Round 3 supplies the
complete row map and per-check falsifiers described above.
