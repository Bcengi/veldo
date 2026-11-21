# VELDO-0111 open AC2 qualification

REMAINING: full AC2 qualification within Unix, IPv4, IPv6 and netlink.
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

## Retained AC2 obligations

These are implementation gaps, not missing owner decisions or claims that the
kernel lacks the facilities. Local regression success is not full acceptance.

* protocol_inventory_bounds: the current discovery table is bounded. Limiting
  its family universe does not establish exhaustive protocols and paths inside
  those families. exhaustive remains false, so no real receipt is yet COMPLETE.
  Measured 2026-11-21 on the qualification host: socket(AF_INET or AF_INET6,
  SOCK_STREAM, 256) succeeds (IPPROTO_SMC, registered as INET_SMC/SMC6 in
  /proc/net/protocols) and lies outside the scanned range 0-255 plus 262. A
  scan of 256-69999 found only 256 and 262. The bound is therefore demonstrably
  not exhaustive. A candidate qualification: reconcile every registered entry in
  /proc/net/protocols and every net-pf-{1,2,10,16} alias in modules.alias with a
  discovered (family, type, protocol) cell, failing closed on any unexplained
  entry. Not implemented yet.
* operation_configuration: the available IPv6 datagram protocol 115 still needs
  its specific address/configuration fixture. EINVAL on a generic address does
  not qualify that protocol.
* io_uring_socket_effects: the host probe witnesses an actual completed socket
  creation. Shared rings, SQPOLL and completion-to-socket correlation remain
  unqualified. A successful interface call causes an explicit capture failure.
* compat_socketcall_message and compat_syscall: scalar socketcall probes work;
  compat message/control layouts and other i386 entries remain unqualified.

No obligation above was removed by the family amendment. Exact qualification
within the four families needs further implementation and live evidence before
AC2 can be marked complete. The existing ptrace event stream alone does not
supply asynchronous completions or final socket-reference destruction events.

Round 3 regressions, falsifiers, receipts and digests are in
[round3](round3/README.md). The current attempt's compact receipt and logs are in
[ac2-attempt](ac2-attempt/README.md). Earlier round records are historical.
