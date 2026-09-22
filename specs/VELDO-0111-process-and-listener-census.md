---
schema: veldo.spec/v1
id: VELDO-0111
title: Observe process creation and every supported listener during a call
status: draft
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: []
placement: [contracts, runners]
protected_paths: []
footprint:
  - "scripts/fixtures/lifecycle_census.py"
  - "scripts/suites/*_veldo_0111_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0111-process-and-listener-census.md"
  - "specs/index.md"
  - "proof/VELDO-0111/*"
behavior_bearing: true
observability:
  logs: >
    Record observation barriers, process birth identities and ancestry, socket family/type/address, listener lifetime, and the measured scope separately from the observer.
  metrics: >
    Report event totals, lost events, measured process count and supported/unsupported socket families.
  traces: >
    Bind every result to the input identity, implementation digest and fixture version.
  error_taxonomy: >
    Distinguish observer_unavailable, observation_incomplete, event_loss and lifecycle_violation; observation failures yield census status INCOMPLETE and named consumer stand-downs, never a successful absence observation.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: A reusable census captures process births, execs and exits throughout the measured call, including short-lived, double-forked and reparented descendants.
      Set: The fixture-launched root and every task in its kernel-traced descendant scope from a start barrier before the call until return and descendant quiescence; qualification helpers cover fork, vfork, clone/clone3, threads, exec, immediate exit and daemonization.
      Completeness: Use Linux ptrace with PTRACE_TRACEME at the root's pre-exec stop and PTRACE_O_TRACEFORK, PTRACE_O_TRACEVFORK, PTRACE_O_TRACECLONE, PTRACE_O_TRACEEXEC and PTRACE_O_TRACEEXIT set before release. Consume kernel events through waitpid with __WALL and PTRACE_GETEVENTMSG, following automatically traced descendants across reparenting and thread exec identity changes through their terminal waits. Account for each birth identity (PID/TID plus birth sequence), not periodic process listings. The helper's independently acknowledged births must equal the trace inventory, including children that exit between barriers; missing trace inheritance or an unobservable creation path makes the receipt INCOMPLETE.
      Refutation: census/process-lifetimes is false on any missing birth or prematurely closed interval.
    falsified_by: >
      Drop exit-before-return descendants from the census event stream; census/process-lifetimes must turn red.
  - id: AC2
    text: >
      Claim: The same census records every successful transition to listening and every new service receive binding during the interval, even if closed immediately.
      Set: All address families and socket types exposed by the qualification kernel, including pathname and abstract Unix, IPv4 and IPv6; addresses are unrestricted. Datagram/raw receive bindings are included as service exposure even where listen is inapplicable.
      Completeness: Use ptrace PTRACE_SYSCALL entry/exit stops with PTRACE_O_TRACESYSGOOD as the kernel observation mechanism, decoding socket operations and successful return values for every traced task and qualified syscall ABI, without family or path filters. Track socket identities and descriptor inheritance/duplication/transfer, bind/listen/close and implicit service receive bindings; record successful exposure before the task resumes and closes the socket. Qualify against a runtime family/type and operation inventory with generated acknowledged probes for every available combination, including socketcall where supported. /proc and sock_diag may enrich identity/address data but snapshots cannot supply transient-event evidence. An available path whose effects cannot be decoded, including asynchronous io_uring socket operations, prevents a complete result; do not treat a successful submission as a successful socket operation. Record unsupported combinations with the kernel error and do not claim unqualified families.
      Refutation: census/listener-lifetimes is false if the expected service event is missing, including a transient abstract Unix listener or a listener outside the fixture directory.
    falsified_by: >
      Discard AF_INET6 listener events in the collector; census/listener-lifetimes must turn red on the required IPv6 qualification host.
  - id: AC3
    text: >
      Claim: The observer and fixture orchestration cannot count themselves or hide a measured child by its name.
      Set: Observer, event sink and setup helpers created outside the measured scope before arming, plus measured processes with names identical to the observer and to a process-search command.
      Completeness: Membership is established by the fixture root's ptrace relationship, inherited tracing and birth identity; no name matching is allowed. A paired empty interval and a same-name child interval require respectively zero measured births and exactly the acknowledged child's birth, apart from the separately declared root launch. Out-of-scope observer activity is separately recorded.
      Refutation: census/observer-is-outside is false if observer events leak into the result or the same-name child disappears.
    falsified_by: >
      Exclude measured processes whose command name equals the observer's name; census/observer-is-outside must turn red.
  - id: AC4
    text: >
      Claim: An absence result is valid only after successful arming, loss-free collection and complete drain; unavailable observation is explicitly incomplete.
      Set: Normal runs, ptrace denied by Yama/LSM/seccomp policy, missing Linux facilities, unsupported syscall ABI/observation paths, event-stream loss or corruption, collector death and drain deadline expiry.
      Completeness: Generate fault cases from the collector's lifecycle states and terminal statuses; require every status to have a result. Unavailable or partial observation must return INCOMPLETE with the failed capability and reason. Every dependent row must be emitted by its exact name as STANDS DOWN with census_incomplete, never green, omitted or counted as a pass. Drive this propagation through VELDO-0113, VELDO-0114 and VELDO-0122, whose named row lists are part of their consumer contracts; no incomplete receipt satisfies qualification.
      Refutation: census/incomplete-is-not-empty is false if any injected observation failure yields a complete empty trace.
    falsified_by: >
      Return a complete empty trace after collector death; census/incomplete-is-not-empty must turn red.
required_evidence: [unit, integration]
rollback: >
  Revert this capability and its consumer wiring together; retain the evidence gap as open rather than reporting coverage from the earlier weaker rows.
---

## Intent

Provide one reusable lifecycle measurement capability for the no-auto-start and no-listener obligations.

## Context

The gaps are recorded in proof/VELDO-0108/README.md:35-40 and proof/VELDO-0109/README.md:71-77 at 2d19756. VELDO-0108 AC3 and VELDO-0109 AC1/AC3 currently observe only socket snapshots. Consumer rules belong to separate dependent drafts.

## Out of scope

Client refusal semantics, deciding which launches consumers allow, filesystem-write observation, and implementing a host monitoring service.

## Notes

The selected mechanism is Linux ptrace of children launched by the fixture. This prefers an ordinary unprivileged developer account: same-user, dumpable children using PTRACE_TRACEME need neither root nor CAP_SYS_PTRACE under normal tracing policy, including Yama ptrace_scope 0 or 1. Yama modes 2/3, another LSM, container seccomp policy, an unsupported ABI or absent kernel facilities may prevent it. Preflight the actual launch/trace/probe path; never invoke sudo or relax host policy automatically. PID/user namespaces and cgroup administration are not prerequisites. The required qualification host must support the IPv4/IPv6/Unix probes and complete observation; unavailable hosts produce INCOMPLETE and the named consumer stand-downs, not empty green traces. The Linux [ptrace manual](https://www.man7.org/linux/man-pages/man2/ptrace.2.html) and [Yama documentation](https://cdn.kernel.org/doc/html/latest/admin-guide/LSM/Yama.html) define the lifecycle/syscall-stop interface and privilege restrictions.

The collector and its probe programs are repository-only test apparatus, not shipped enforcement code. The Python fixture may depend on the Python standard library (including ctypes to call the host libc ptrace interface), Linux UAPI constants for explicitly qualified ABIs, libc, /proc and optional NETLINK_SOCK_DIAG enrichment through stdlib socket. It requires no third-party Python packages, installed tracing daemon, eBPF toolchain or compiler. Receipt validation and consumer/gate decisions remain standard-library-only enforcement. Record kernel, ABI, Python and collector versions and capability failures in the receipt. This choice does not assert that ptrace alone observes every kernel effect: unqualified asynchronous paths, socket address/identity races, escaped tracees or lost stops force INCOMPLETE. In particular, VELDO-0122 must separately qualify mmap and asynchronous filesystem effects; it cannot infer them from this process census.

This is an in-session fixture with bounded teardown, never a detached monitor. Establish tracing options before releasing the root and use PTRACE_O_EXITKILL plus supervised cleanup and terminal waits so collector death cannot leave traced workers running or certify a completed interval. Fixture processes and pre-existing authority/SSH endpoints are established outside the measured scope before the barrier; the call and all its descendants stay inside. A consumer may exclude only explicit launch identities declared before observation, never matching names or paths. No ptrace stop, unsupported capability or permission error is silently replaced with polling.

This is planned work, not implementation evidence. All named rows below this contract are obligations for a future ready implementation. For each declared falsifier, retain the applied diff, require the named row to become false in an otherwise completed run, and revert the mutation. A crash, missing row or timeout is an invalid drive, not a detected falsifier.
