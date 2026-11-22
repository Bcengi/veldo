# AC2 continuation, 2026-11-21

Base: `bb0686b3`, branch `veldo-0111-complete`. The lead's 2026-11-21 decision
is recorded in the specification History. The owner's 2026-10-28 amendment is
kept and not weakened. **All retained AC2 obligations are addressed; AC2
acceptance awaits independent review.**

## Results

One recheck through the owner's external `host_heavy.sh` completed with exit 0
(`recheck.txt`, `validation.txt`), base `bb0686b3` plus the close_range
follow-up. Baseline and final control: 23/23 rows. All whole-suite mutants,
witness mutants, the 13 continuation-2 mutants and the 6 close_range mutants
were detected (each close_range mutant reddens only
`census/close-range-accounted`); all controls were green. The baseline host receipt
names **no qualification gaps**: `protocol_inventory_bounds`,
`operation_configuration` and `io_uring_socket_effects` no longer appear, and
compat i386 calls are qualified. A plain measured call on this host (for
example the compat `direct` drive) now yields a COMPLETE receipt with READY
consumer rows. The inventory drive itself stays INCOMPLETE because it creates
sockets of families outside the four. No named-gap replay remains to run.
These are regression and falsifier results; acceptance needs independent
review.

## Follow-up, 2026-11-22: close_range

Found by VELDO-0113: the collector refused close_range (syscall 436), which
Python's subprocess issues before every exec, so most of its client runs ended
INCOMPLETE. close_range is now accounted exactly like close on every descriptor
in its range. The range is read from the kernel descriptor table at the entry
stop and checked against the exit stop; each socket in it gets a `close` event
(`syscall: 436`) and a `descriptor_closes` entry. Release is still proven only
by the file-release observer, so a reference already queued elsewhere by
SCM_RIGHTS stays `escaped_reference`. CLOSE_RANGE_CLOEXEC emits
`close_on_exec_marked` and closes nothing; a successful exec then emits a
`close` (`cause: close_on_exec`) for each socket it closed. Refused by name
(`descriptor_operation`): flags outside UNSHARE|CLOEXEC, and close_range on a
descriptor table another live task shares (its contents can change between the
entry stop and the kernel's close). A vfork child shares memory, not the table,
so it is not refused.

Row `census/close-range-accounted` (live drives, each checked against the
probe's own acknowledgements):

* `subprocess`: a client holding a listener runs `git --version` through
  subprocess; the receipt is COMPLETE and the child's close_range closes the
  listener (`syscall: 436`) before the client's own close.
* `only`: a TCP and a Unix listener are closed only by one close_range; both
  are observed released, and the client rebinds the same port and abstract
  name (only a released listener frees them).
* `cloexec`: CLOSE_RANGE_CLOEXEC leaves the listener open until exec; the
  close is accounted at exec, not at close_range.
* `escaped`: a listener sent by SCM_RIGHTS to an outside receiver, then closed
  by close_range(3, ~0U), yields exactly the send-attributed and the
  referenced-after-drain `escaped_reference`; the receiver gets a live listener.
* `shared` (thread) and a unit replay with flag 0x8 are refused by name.

Mutants (whole suite, each reddens the row): `refuse-close-range` (the old
behaviour), `ignore-close-range`, `cloexec-closes-now`, `ignore-exec-closes`,
`allow-unknown-close-range-flags`, `ignore-shared-close-range`.

## Continuation 2: the four retained obligations

One commit each; each is driven by whole-suite mutants in `recheck.py`
(red mutant, shared baseline and final control).

| Obligation | Row | Mutants |
| --- | --- | --- |
| protocol_inventory_bounds | `census/protocol-inventory-covers-kernel`, `census/undiscovered-protocol-refused` | `narrow-protocol-scan`, `trust-registry`, `skip-undiscovered-refusal` |
| operation_configuration | `census/protocol-specific-operations` | `generic-l2tp-address`, `drop-kernel-address-decoding`, `ignore-sctp-bindx`, `ignore-l2tp-conn-id` |
| io_uring_socket_effects | `census/io-uring-refused-in-scope` | `skip-inherited-ring-scan`, `ignore-installed-rings` |
| compat ABIs | `census/compat-abi-qualified` | `drop-i386-socket-map`, `native-compat-message-layout`, `drop-compat-socketcall-messages`, `compat-aliases-native` |

* Protocols: bounds Unix 0-15, IPv4/IPv6 0-1023, netlink 0-63, each cell with
  the kernel's (domain, type, protocol); exhaustive only if every
  `/proc/net/protocols` name and `net-pf-{1,2,10,16}` alias is inside them
  (unknown names fail closed); an undiscovered measured triple is refused.
  The row re-probes 0-4095 (netlink and Unix 0-1023) and extreme values with
  libc `socket` independently of the fixture.
* Operations: L2TP/IP binds with its own sockaddr and exact connection id;
  endpoints without a `/proc` table are decoded from the kernel's
  getsockname; SCTP bindx/connectx/peeloff fail closed (live bindx drive).
* io_uring: an outside helper owns a ring and permits `pidfd_getfd`; the
  measured task takes it and tries a `/proc` reopen (ENXIO on this host);
  capture fails naming syscall 438. A replayed first stop holding a ring fails
  as inherited.
* Compat: int 0x80 from a live tracee - direct socket/bind/listen plus an
  i386 setgid that would alias native sendmsg (a COMPLETE receipt with an
  i386 listen service), SCM_RIGHTS via socketcall and direct
  sendmsg/sendmmsg in compat layouts (exactly one escaped_reference each),
  and i386 clone with CLONE_UNTRACED. The row derives every native number the
  collector compares from its source and requires an i386 mapping for it.

## Two independent escape detectors

**SCM_RIGHTS send decoder (attribution).** The collector decodes outgoing
native `sendmsg` and `sendmmsg` controls before testing whether it knows the
transport. A successful SCM_RIGHTS transfer without a proven contained peer
emits `escaped_reference` (`lifecycle_violation`, reason
`SCM_RIGHTS send <sequence> has no exclusively measured receiver`), leaves
capture INCOMPLETE, and stands down all eleven named consumer rows. This
includes a transport received from outside the measured scope. A failed send
is not reported as an escape. Only an unexported, scope-created socketpair has
a proven peer; every other transport is treated conservatively as outside.

**File-release observer (destruction at drain).** At each socket's creation
stop the collector duplicates the descriptor with `pidfd_getfd`, registers the
open file in a collector-owned epoll set, and closes the duplicate before the
tracee resumes. An epoll item holds no file reference; the kernel removes it in
`__fput` when the last reference is released. After the `descendants_drained`
barrier the collector reads its epoll set from `/proc/self/fdinfo`:

* item gone: the final reference was released at or before drain; the socket
  record gets `closed = {barrier: descendants_drained, released: true,
  observer: epoll_file_release}`;
* item present: a reference survives outside the drained scope, whatever path
  carried it there; `escaped_reference` (`<identity> file is still referenced
  after descendant drain`), `closed: null`, capture INCOMPLETE;
* never registered (observer unavailable or failed): no destruction claim;
  the named `socket_destruction` gap remains for that socket.

The blanket host-level `socket_destruction` gap is therefore replaced by an
observation: it is named only for a socket whose release was not observed.
"Released" means the socket file's last reference went away (`sock_close`).
It does not claim protocol-level teardown of orphaned TCP connections, which
have no socket file and no listening state.

## Kernel state instead of tracee memory (shared_socket_memory)

* bind: the kernel's address (getsockname on a pidfd_getfd duplicate) must be
  one the sampled sockaddr requested; otherwise `shared_socket_memory`.
* socketpair and received descriptors (recvmsg/recvmmsg): taken from the diff
  of the kernel descriptor table between entry and exit stops; a socketpair
  array that disagrees fails; a received out-of-scope socket fails as
  `descriptor_transfer`; a received io_uring instance fails as `io_uring`.
* a socket syscall while another live measured task shares the descriptor
  table or address space (kcmp) fails closed, as does creating a seccomp
  user-notification listener (it can install descriptors from outside).
* send controls: escapes are caught by the release observer even when the
  control memory is rewritten.
* netlink implicit binding: the kernel sockaddr gives the autobound port id.

## Falsifiers

`socket_destruction.py` keeps the original Unix, IPv4, IPv6 and netlink live
counterexamples: each queues its service descriptor to a receiver outside the
scope, closes, exits and drains; the external receiver then exercises, receives
and releases the still-live socket. Modes `owned` (scope-created transport),
`sendmmsg`, and `imported` (transport received from outside) run all four
families. The row `census/escaped-reference` requires the send-attributed
failure; the release observer's detection is recorded beside it.

| Drive | Expected |
| --- | --- |
| original, 3 modes x 4 families | row green; both detectors fire |
| `ignore-scm-rights` (send decoder off) | row red; release observer still fails every capture |
| `ignore-scm-rights-and-release` (both off) | row red; owned/sendmmsg captures turn COMPLETE (the lead's "turns them green") |
| `control-aba` original | `census/escape-detected-despite-control-aba` green |
| `control-aba` with `ignore-release` | row red; capture turns COMPLETE |
| whole suite, `ignore-scm-rights` | `census/escaped-reference` red |
| whole suite, `ignore-release` | `census/destruction-at-drain` red |
| whole suite, `skip-release-watch` | `census/destruction-at-drain` red |
| `memory-aba` original | `census/memory-aba-uses-kernel-state` green in bind, socketpair, recvmsg |
| `trust-bind-sample`, `socketpair-from-memory`, `trust-received-control` | each loses exactly its scenario |
| whole suite, `ignore-sharers`, `ignore-seccomp-listener` | `census/shared-descriptor-table-fails-closed` red |
| whole suite, `drop-netlink-implicit` | `census/netlink-implicit-binding` red |

`shared_memory.py` is the control-memory ABA witness. An unmeasured ancestor
uses real `process_vm_writev` calls, scheduled by acknowledgements from an
instrumented copy of the collector, to replace valid credentials with three
SCM_RIGHTS copies of a listener after the entry sample and restore them before
the exit sample. The send decoder sees credentials both times (asserted), the
kernel really transfers the listener (the external receiver gets it after drain
and checks inode, address and listening state), and the release observer must
still name the escape. A benign unmodified run with the same control is
COMPLETE with no received rights.

The new suite row `census/destruction-at-drain` creates and closes a listener
or binding in each of the four families (each must be observed released) and
lets an outside ancestor take a listener with `pidfd_getfd` - no SCM_RIGHTS, no
send event. That listener must be the only `escaped_reference`.

`memory_aba.py` uses the same scheduling-only instrumentation and real
`process_vm_writev` to make tracee memory lie in three places: the bind
sockaddr (127.0.0.1 at both stops, kernel bound 127.0.0.2), the socketpair
result array (rewritten to an older genuine pair), and a received SCM_RIGHTS
control (erased after the kernel filled it). Each drive first asserts the lie
really happened, so a non-event is an invalid drive, not a pass.

## Reproduction and proof integrity

Run from the worktree with the owner's external `host_heavy.sh` command wrapper;
its personal installation path is deliberately absent from committed files:

```
host_heavy.sh python3 -B proof/VELDO-0111/ac2-attempt/recheck.py
python3 -B proof/VELDO-0111/ac2-attempt/validate.py
```

Ordering comes from socket acknowledgements, syscall stops and terminal waits.
Timeouts are hang detectors, never pass conditions based on elapsed time.
Mutants live in temporary files; the worktree collector is never replaced.
A missing row, exception, timeout or failed baseline invalidates a drive.
The recheck retains zero-context applied diffs, source digests, exact named
outcomes, eight fault receipts and all eleven consumer stand-down rows. The
existing acceptance, round-3, swallowed-fault, CLONE_UNTRACED and fresh
named-qualification-gap falsifiers remain. `recheck.txt` is the run log;
`validation.txt` records the validator. This is ticket-local evidence, not a
broad repository gate or full AC2 qualification.

`scripts/gate_unconfined.json` remains unchanged and still omits suite
`113_veldo_0111_census`. Ptrace-dependent cases require the authority driver's
unconfined leg; a denied baseline is invalid, never a killed mutant. The direct
host-wrapper runs do not claim an authority mutation-driver result. Consumer
tickets remain unchanged.
