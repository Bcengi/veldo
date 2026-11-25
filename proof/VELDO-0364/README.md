# Mutation-host admission and qualification

Owner Telegram 43610; rank 5 phase 1 only. The scheduler caps the aggregate reservation
at measured host capacity. Coordinator, worker, resource, manager, port and lock checks
remain enforced. The existing large-host reservation and claims are unchanged.

Run the explicit diagnostic entry point with the distro interpreter:

```
/usr/bin/python3 -I -S scripts/qualify_mutation_host.py --receipt qualification.json
```

The command takes the existing host lock, uses the existing 16 GiB delegated scope,
and records every native probe. `--cases FILE --batch-receipt FILE` additionally runs
selected names through the existing single-host coordinator, only if qualification passes.
It uses short private scratch paths for socket fixtures and removes them afterwards.
A receipt is evidence for that invocation, never a reusable host authorization or a full gate.
The supervisor's virtualenv is unsuitable: fixture children cannot read its configuration
under the worker boundary. The native probe now tests that child interpreter launch.

Full host qualification also requires tools visible to workers. The remote supervisor's
private Node does not satisfy the UI suites' system/account-nvm lookup. Missing tools
make the qualification red before workers start. No grant is widened and no tool is installed.

`run.sh` reproduces the 100-case diagnostic and compares full observations, mutation digests,
case definitions and named kills with completed gate-15 records. Gate 15 itself was red;
only its validated completed cases are the comparison baseline. `guards.sh` drives the
five registered admission/qualification falsifiers. `compare_controls.py` rejects omitted,
duplicate and changed results, invalid controls, reuse and incomplete cleanup.
`final_checks.sh` performs static checks and the final native qualification. All workload
execution is through the owner's remote runner on the second host. No full gate, full leg,
live engine capture, transport, aggregator or first-host workload is part of this evidence.
