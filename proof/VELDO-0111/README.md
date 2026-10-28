# VELDO-0111 implementation and evidence

This is partial implementation evidence, not full acceptance or a landing claim.
The four required named checks exercise concrete kernel effects and fault
propagation. Full host qualification remains INCOMPLETE. See OPEN.md for the
remaining contract, including the forward reference to unbuilt consumers.

The ticket has no dependencies. PLAN-0019 places it among the standalone Release 2
qualification follow-ups. The owner's inventory dated 2026-10-28 confirms that
0113, 0114 and 0122 are not built. The starting branch was made from main at
59b119a1. No specification status has been changed.

## Implemented measurement

The repository-only fixture launches a supervisor, collector and measured root.
The supervisor is a private subreaper and consumes only its own child waits.
The root uses TRACEME and stops before exec. The collector establishes FORK,
VFORK, CLONE, EXEC, EXIT, TRACESYSGOOD and EXITKILL options before release.
Kernel wait events establish scope and identities. Names never decide scope.
The collector follows double forks and thread exec identity changes through
terminal waits, and records separate armed, call-return and descendant-drain
barriers. An early child stop waits for its parent's creation event.

Native x86_64 syscall entry and exit stops record successful socket creation,
bind, listen, close and descriptor alias operations. Socket inodes enrich those
events, including inherited and SCM_RIGHTS-transferred descriptors. IPv4 and
IPv6 assigned addresses are enriched at the stopped successful syscall exit.
Unix addresses retain their complete sockaddr bytes, including abstract names.
The measurement has no fixture-directory or address-family exclusion.
Descriptor-close events are exact syscall observations; socket destruction is
currently only bounded by the final drain. That distinction is not qualification.

An unsupported ABI, escaped tracing attempt, corrupt stream, unavailable facility,
failed arming, collector death or drain failure produces an incomplete receipt.
Collector death is an actual SIGKILL with live tracees; EXITKILL and the private
subreaper terminate and reap those tracees. The adapter emits all eleven consumer
row names as STANDS DOWN with census_incomplete. It never passes a consumer.

Receipts record kernel, Python, ABI, fixture version, input identity and digest,
implementation digest, events, process ancestry, socket attributes, barriers,
failures and metrics. Runtime socket discovery covers family numbers 0 through 45
and seven Linux socket types at protocol zero, recording actual kernel errors.
Discovery is explicitly not exhaustive protocol or operation qualification.

## Checks and falsifiers

The suite is scripts/suites/113_veldo_0111_census.py. Direct execution runs only
this ticket. The shared dispatcher was also checked with only this suite selected:
five ticket rows passed, no failures; its standard partial-run exit was 2. The
dispatcher additionally executes its own shared harness initialization checks.
No aggregate verification or full gate was run.

| Criterion | Named check | Independent evidence | Declared mutation |
| --- | --- | --- | --- |
| AC1 | census/process-lifetimes | Child-written PID/TID acknowledgements, fork, native clone, clone3 availability, thread, vfork/exec, immediate exit, double fork, reparenting and nonleader exec | Remove descendants that exited before root return from processes and events |
| AC2 | census/listener-lifetimes | Fourteen acknowledged service operations across IPv4, IPv6, pathname and abstract Unix, netlink, duplicate, inherited and transferred descriptors | Discard IPv6 service events |
| AC3 | census/observer-is-outside | Empty interval plus children named after the observer and pgrep, exact acknowledged identity sets | Exclude descendants named after the observer |
| AC4 | census/incomplete-is-not-empty | Lifecycle fault matrix, real collector death and drain expiry, all eleven exact consumer row names, malformed receipts | Return COMPLETE with an empty trace after collector death |

The fifth check, census/qualification-does-not-overclaim, independently exercises
322 family/type discovery cells and io_uring setup. It requires INCOMPLETE and
all named consumer stand-downs. A green fifth row proves honest incompleteness,
not general process or listener absence.

drive.py applies each mutation to an isolated scratch copy, retains its diff,
and runs the same suite through that exact copy and its subprocess supervisor.
It requires the named row to be false in a completed run, then requires every
row green using a fresh original copy. A crash, omitted row or exception fails
the drive. results.json records the outcomes and source/suite digests; compressed
JSON logs retain the complete receipts and acknowledgements for each run.

All mutation execution uses the owner's blocking flock on the host gate lock.
The tests never acquire or release that lock and never use it as a fixture lock.
Only this ticket's processes, files and scratch directories are manipulated.

## Limits and sources

The full AC2 qualification is open: available asynchronous operations, additional
families/protocols, compat socketcall, implicit addresses and races remain
unqualified. The fixture deliberately cannot issue COMPLETE receipts yet.
AC4's actual consumer integrations remain in 0113, 0114 and 0122. Green mutation
controls do not close those gaps. No protected path was edited, no service was
activated, and nothing was pushed or merged.

Public interface references consulted:
[Linux ptrace manual](https://man7.org/linux/man-pages/man2/ptrace.2.html) and
[kernel Yama documentation](https://docs.kernel.org/admin-guide/LSM/Yama.html).
The local Linux UAPI headers supplied constant/layout confirmation. No external
project code or third-party Python dependency was used.
