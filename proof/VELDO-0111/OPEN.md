# VELDO-0111 open evidence after round 3

REMAINING: full AC2 qualification within Unix, IPv4, IPv6 and netlink.
The owner approved the two acceptance amendments in Telegram 37442, answering
Telegram 37440 item 1. They are applied under "Amendment, 2026-10-28" in the
specification. Neither approval waives the obligations inside those families.

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
* operation_configuration: the available IPv6 datagram protocol 115 still needs
  its specific address/configuration fixture. EINVAL on a generic address does
  not qualify that protocol.
* io_uring_socket_effects: the host probe witnesses an actual completed socket
  creation. Shared rings, SQPOLL and completion-to-socket correlation remain
  unqualified. A successful interface call causes an explicit capture failure.
* socket_destruction: close observations and descendant drain do not timestamp
  final reference destruction, including queued SCM_RIGHTS or external holders.
* shared_socket_memory: entry/exit inode checks do not exclude descriptor ABA
  or concurrent sockaddr mutation.
* implicit_address: the reviewed Unix autobind case is fixed. Other implicit
  addresses without a qualified decoder, including netlink, still fail closed.
  Ambiguous or missing Unix name enrichment also fails closed.
* compat_socketcall_message and compat_syscall: scalar socketcall probes work;
  compat message/control layouts and other i386 entries remain unqualified.

No obligation above was removed by the family amendment. Exact qualification
within the four families needs further implementation and live evidence before
AC2 can be marked complete. The existing ptrace event stream alone does not
supply asynchronous completions or final socket-reference destruction events.

Round 3 regressions, falsifiers, receipts and digests are in
[round3](round3/README.md). Earlier round records are historical.
