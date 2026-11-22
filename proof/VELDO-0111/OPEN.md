# VELDO-0111 open AC2 qualification

REMAINING: independent review of AC2. The retained obligations within Unix,
IPv4, IPv6 and netlink are addressed (see below); none is accepted yet.
The owner approved the two acceptance amendments in Telegram 37442, answering
Telegram 37440 item 1. They are applied under "Amendment, 2026-10-28" in the
specification. Neither approval waives the obligations inside those families.

## Continuation, 2026-11-21

The lead's 2026-11-21 restatement supersedes the previous external-reference
`socket_destruction` stop and is recorded in the specification History. The
owner's 2026-10-28 amendment is kept and not weakened.

Closed in this continuation, each with live falsifiers (see
[ac2-attempt](ac2-attempt/README.md); results are in its receipt):

* escaped references: outgoing SCM_RIGHTS on native sendmsg/sendmmsg, including
  through transports the scope did not create, fail the capture as named
  `escaped_reference`. All four live family counterexamples produce it; the
  ignore-SCM_RIGHTS mutants are caught.
* socket_destruction: an epoll file-release observer (no file reference held)
  proves each socket's final release at or before descendant drain, and names
  any socket still referenced after drain as `escaped_reference`, whatever path
  carried it there. The blanket host gap is gone; the gap is named only for a
  socket whose release was not observed.
* shared_socket_memory: bind addresses are checked against the kernel's
  getsockname on a duplicate; socketpair results and received descriptors come
  from the kernel descriptor-table diff; any socket syscall while another live
  task shares the descriptor table or address space (kcmp), and any seccomp
  user-notification listener, fails closed. Outside-writer ABA on bind,
  socketpair, recvmsg and sendmsg control memory is exercised live with real
  process_vm_writev. The blanket host gap is gone.
* implicit_address for netlink: the autobound port id is read from the kernel's
  sockaddr. Unix autobind names (always five hex digits) and IPv4/IPv6 ports
  were already exact; anything else still fails closed.

The protected execution declaration `scripts/gate_unconfined.json` is unchanged.
It omits suite `113_veldo_0111_census`; ptrace-dependent authority mutation cases
need the unconfined leg, otherwise their baseline is invalid. Direct host-wrapper
results do not imply an authority mutation-driver pass. Consumer tickets are
unchanged.

## Closed by the amendment and implementation

* AC2 no longer requires full operation/address fixtures for other families.
  Discovery still records their kernel errors and a named family_not_qualified
  reason. Successful creation of any other family in a measured call makes
  capture INCOMPLETE. The boundary also rejects future family numbers. It does
  not exclude their socket records or turn unavailable addresses into support.
* AC4 verifies the receipt validator and all eleven exact named stand-down rows
  here. VELDO-0113, VELDO-0114 and VELDO-0122 must each drive the complete fault
  matrix through their own integrations. The owner amendment closes the cycle.
* Finding 5: an unbound Unix datagram sender produces no service event and no
  implicit_address failure. A real SO_PASSCRED autobind is enriched from the
  stopped socket's inode and name in /proc and emits its exact autobind name
  once. Other undecoded implicit addresses fail without a service event.
* Finding 6: the suite extracts every assigned lifecycle state from the source
  and compares it with FAULTS. A finalization fault now exercises drained as
  well as preflight, arming, collecting and draining. The full fault row checks
  its capability, category and state and all consumer stand-downs.

## Retained AC2 obligations, addressed in continuation 2 (2026-11-21)

One commit each, each with whole-suite falsifiers in the recheck
([ac2-attempt](ac2-attempt/README.md); results in its receipt). Addressing
them is not acceptance: AC2 needs independent review.

* protocol_inventory_bounds: discovery bounds are Unix 0-15, IPv4/IPv6
  0-1023 and netlink 0-63 (the old scan missed IPPROTO_SMC 256 and Unix
  protocol 1), and every available cell records the kernel's own (domain,
  type, protocol). The inventory is exhaustive only when every
  /proc/net/protocols entry and every net-pf-{1,2,10,16} module alias lies
  inside the bounds; unknown names and unreadable sources fail closed. A
  measured socket whose kernel triple was not discovered is refused as
  `protocol_inventory_bounds`. Row `census/protocol-inventory-covers-kernel`
  also probes 0-4095 and extreme values independently.
* operation_configuration: L2TP/IP (115) binds use its own sockaddr layout
  with an exact connection id; each inventory operation qualifies only if
  the collector's decoder names the endpoint from the kernel's getsockname,
  which the collector also uses for protocols without a /proc table (SCTP,
  UDP-Lite, SMC, L2TP/IP). Successful SCTP bindx, connectx and peeloff fail
  closed.
* io_uring_socket_effects: no ring may exist in measured scope. Rings are
  refused at each task's first stop (inherited), on open/openat/openat2 and
  pidfd_getfd results, on received rights, and on successful setup, enter or
  register. Completions therefore need no correlation, and SQPOLL cannot
  act for a measured task. For review: a ring owned and driven by an outside
  process is treated as that outside process's effect, like a request to an
  outside daemon.
* compat_socketcall_message and compat_syscall: every inspected native call
  has an i386 counterpart; unmapped i386 calls cannot alias native numbers;
  socketcall and direct sendmsg/sendmmsg controls use the compat msghdr and
  cmsghdr layouts. qualified_abis lists x86_64 and i386.

Round 3 regressions, falsifiers, receipts and digests are in
[round3](round3/README.md). The current attempt's compact receipt and logs are in
[ac2-attempt](ac2-attempt/README.md). Earlier round records are historical.
