# Signing row

Implementation `86293d834`; old fixture at `4e6b23b99` (same signing source as
`970f12c79`). This ticket was renumbered from the pc2 branch's former VELDO-0364;
historical commits and raw receipts were not rewritten. VELDO-0364 belongs to
speed-reuse. Current paths and registrations use VELDO-0365.

## Cause and reproduction

The last historical-verification conjunct in `signing/kill-after-rotation` uses
`control_keys.active(key, signed_at)`, which requires `signed_at < retired_at`.
The mutant truncates the transition's epoch time, including retirement. If signing
and rotation share a second, retirement moves before the signature. If the real
clock crosses a second between them, historical verification survives.

Three serial baseline/no-op/mutant repetitions per host, before and after, give
36 single-case observations. The old pc2 mutant row was **true, false, false**;
old pc1 was **false, false, false**. For example pc2 passed at signed_at
1795596841.94904 / retired_at 1795596842 and failed at signed_at
1795596879.4598005 / retired_at 1795596879. Every other conjunct of that row
passed. Both hosts report `tsc` and America/New_York. No filesystem timestamp or
timezone conversion feeds this predicate. CPU speed/load can change the chance
of crossing a second, but one host reproducing both outcomes establishes the
timing dependency without attributing it to a particular CPU or clock source.
The receipt's Python/kernel/libc differences are retained as context.

This is a nondeterministic off-target mutant observation, hence a latent failure
of strict result comparison on either host. These runs do not demonstrate a new
production defect on the unmodified code. Other lifecycle rows also use actual
time and retain varying off-target mutant verdicts; this work makes no claim that
the entire observation vector is now deterministic.

## Fix and regression

Only the disposable signing fixture changes. An injected signer clock puts the
receipt at epoch + .25; the rotation child uses epoch + .75. Subsequent publication,
retirement and revocation use explicit instants and fresh verification uses its
existing `now` parameter. All original assertion conjuncts remain. Real Ed25519
signatures, child processes, SQLite transactions, SIGKILL and projection repair
are exercised. The fixture clock hook never enters a production source file.

The named transition-clock test now waits for a child pipe event announcing the
lock attempt. Its injected clock advances only after actual BEGIN IMMEDIATE
acquisition. The former sleep and wall-clock release sample are removed, along
with their two census baseline entries. Preflight time and fractional precision
remain checked by the original assertions.

After the fix, both hosts have three passing baseline rows, three passing no-op
rows, and three failing mutant rows for kill-after-rotation. The named clock row
is also killed three times per host. `check_signing.py` checks the signed timestamps,
historical/fresh verification, crash recovery and both row verdicts from receipts;
it rejects both old receipts and accepts both fixed receipts. Reproduce it with:

```
python3 -B proof/VELDO-0365/check_signing.py proof/VELDO-0365/signing/after-pc1.json.gz proof/VELDO-0365/signing/after-pc2.json.gz
```

The corresponding `before-*.json.gz` command must return 1. Raw observations and
component booleans are retained; no comparator or historical receipt was changed.

## Scope and limits

pc2 commands used `myday/scripts/remote_run.sh --share`
with `/usr/bin/python3 -I -S proof/VELDO-0365/signing_probe.py --output FILE` at
the two commits above. pc1 used that same probe directly with nice 19 and idle
I/O priority, one worker at a time, while its gate was running. The probe uses
the normal mutation materializer and observer, without a coordinator, host load,
host-heavy wrapper or nested gate fixture. This is single-case diagnostic
evidence, not a canonical gate receipt or host qualification.

pc2 baseline/no-op suites had no failed rows. pc1's unrelated existing
process-count-and-listeners row failed in some old runs and all fixed controls;
the raw observations retain it. It is outside this timestamp investigation and
was neither changed nor waived. Thus full pc1 controls and full host parity are
not claimed. Existing worker-tool qualification blockers also remain outstanding.

Census passes, personal setup has zero findings, all 4,045 mutation anchors are
current, and the 100-case selection is unchanged. No live-capture-bound module
or gate confinement declaration changed. No full leg or canonical gate ran.


The existing `signing-prelock-clock` mutant was also killed by the updated named
row in one additional light serial pc1 observation (`prelock-pc1.json`). Its
optional pc2 submission was cancelled before launch while waiting for another
job. Stored supervisor logs redact only the account home prefix and numeric
login UID; timestamp operands and verdicts are unchanged.
