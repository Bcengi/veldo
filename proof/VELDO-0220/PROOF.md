# VELDO-0220 proof (implementation agent; not an independent review)

Run: `flock /home/dmitry/.local/state/core-gates/.gate.lock python3 proof/VELDO-0220/local_check.py`
at commit 8030ef4d (clean tree), 2026-10-28T14:53:42Z. Record: local_checks.json.

| AC | Row | Falsifier (registered mutant) | Baseline | Mutant |
|----|-----|-------------------------------|----------|--------|
| AC1 | host-lock/held-not-started | host220-ignores-lock (gate_host.py runs the checks when the lock cannot be taken) | green | red, only that row |
| AC1 | host-lock/released-on-exit | host220-lock-inherited (the lock descriptor inherited by gate children) | green | red, only that row |
| AC2 | host-scope/own-scope | host220-no-scope (the gate stays in the caller's cgroup) | green | red, only that row |
| AC3 | host-lock/not-started-not-red | host220-not-started-is-red (the lander charges exit 75 as a failed gate) | green | red, only that row |

Suite 113 plainly: 4 of 4 rows pass. Inside the gate's confinement (scripts/gate_candidate.py): 3 of 4
pass; host-scope/own-scope is red by name because the confinement refuses the user bus
("GATE: RED (gate scope could not be created: ... Failed to connect to bus: Operation not permitted)").
That row needs the owner's entry in the protected scripts/gate_unconfined.json (text in the spec's
implementation record). Until then the canonical gate is red on that row.

Not run: the canonical ./scripts/verify.sh (the owner runs it on a batch, rule 37191); independent review.
