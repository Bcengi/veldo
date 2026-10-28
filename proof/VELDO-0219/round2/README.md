# VELDO-0219 round two

Status: REMAINING only for the joint canonical qualification and canonical
falsifiers deferred under owner rule 37191, plus the inherited batch dependency
noted in OPEN.md. This directory contains targeted implementation evidence,
not a canonical green gate or a landing approval.

## Dependency and changes

The first commit of this round is the ordinary merge e4b71c37 of
agent/codex/veldo-0216 at 18e375b0, including round two at 1160ed38 and the approved
AC4 amendment. Git merged cleanly and retained both branches' work.

The scheduler's authority channel now has a one-time handoff. It atomically
shrinks the mutation root to coordinator overhead, drops its aggregate
manager exclusion and preserves the root's reserved floor and host lock claim.
Fresh coordinator measurements take precedence over the cold graph default;
the actual overhead is deducted from the reserved worker floor.
Worker admission cannot precede the handoff. Unit lifecycle channels are handed
only to workers whose admitted manifest demand includes manager use. The authority supplies capacities,
remaining worker floor, actual gate totals and the refusing resource. The driver
records all resources encountered while waiting. A process really runs through
the channel check, followed by real CPU, memory and manager refusals and grants.
The former aggregate-handoff-refused success row is replaced with aggregate-handoff.

Without measured admission the default remains at most 16 workers, including
repositories that ship without a graph. Measured admission keeps the ceiling of
twice usable CPUs. A claim takes the maximum within-run CPU rate, never a numerator
and denominator from different runs. Memory claims preserve the largest measured
peak or conservative final-accounting bound.

Unit ownership registration now waits for an authority acknowledgement before
launch. The authority retains each owned slice, and installs a private accounting
parent for each owned service. The parent kernel CPU counter survives child cgroup
removal. The manager reference preserves final accounting across explicit stop;
InvocationID and cgroup identity distinguish restarts. All manager calls made by
the worker's Python subprocess launcher notify the authority before and after
completion. These notifications contain unit names, never candidate-supplied
measurements. Cleanup removes the drop-ins, stops the private slice and releases
references and descriptors. Existing service limits stay on the service itself.

Anonymous memory remains sampled and is reported as such. The kernel's durable
memory.peak is stored separately as peak_memory_bytes and conservatively bounds
admission for an allocation too brief for the anonymous samples. It includes
cache; neither the code nor this proof calls it measured anonymous memory. The
native check intentionally has zero anonymous samples for its short units while
still retaining their CPU totals and a memory bound above the allocated 32 MiB.

## Red and green evidence

| Finding | Red | Green |
| --- | --- | --- |
| Production aggregate refusal | admission-red.json, handoff false | admission-final-green.json and suite 115 aggregate-handoff |
| Measured coordinator overhead | warm-handoff-red.json | warm-handoff-green.json and warm-handoff-suite-green.log |
| Unmetered worker count | admission-red.json, fixed-cap false | admission-final-green.json and suite 115 unmetered-fixed-cap |
| Cross-run CPU demand | admission-red.json, cpu-per-run false | admission-final-green.json and suite 115 cpu-per-run |
| Refusal resource and gate totals | resource-red-green.json, old implementation false | resource-red-green.json true, plus CPU, memory and manager checks over the real channel |
| Short units and repeated cgroup paths | lifecycle-red.json and lifecycle-falsifier-red.json | lifecycle-green.json, two real short units across a slice restart and a real installed service through the ownership channel |
| Lifecycle requires manager admission | lifecycle-manager-red.log | lifecycle-manager-green.log, including both manager and non-manager workers |
| Batch qualification contract | open-red.json | open-green.json |

Suite 115's lifecycle row uses a real ownership socket and a joining worker
thread with controlled kernel files. Removing parent retention makes it fail.
The new registered admission219-short-unit-unaccounted falsifier exercises that
row. The native counterpart additionally executes real user units without any
discovery poll during their lifetimes. All subprocesses are joined and all test
units are removed before the test returns.

falsifiers.py runs only the four VELDO-0219 registered falsifiers, each in mutant,
baseline and no-op mode, then suite 115 and the native lifecycle check.
Its invocation takes the blocking owner host lock. Test fixtures never acquire
that real lock. Single-file development checks are also retained here. Partial
selftest success has exit status 2 by repository convention.

falsifiers-before-manager-guard.json retains the earlier passing controls before
the final lifecycle-channel restriction. The later falsifiers.json supersedes it.

falsifiers.json binds the checks to HEAD and exact source digests. A later
proof-only commit can contain that receipt without changing those source bytes.
Repository and engine copies of all four changed authority modules are identical.
No canonical verification command, push, detached process or main merge ran.

## Deferred batch work

See [../OPEN.md](../OPEN.md) for the exact joint contract. The full fresh gate must
meet 6,000 seconds with VELDO-0216 and VELDO-0219, without VELDO-0221. VELDO-0219's
separate 4,000 second mutation target is unchanged. Both timing results and the
fixed-sixteen and serialized canonical falsifiers await the batch gate.
