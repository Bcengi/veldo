# VELDO-0111 open evidence after round 2

REMAINING. No owner scope reduction or acceptance amendment has been applied.
The implementation no longer appends the unconditional qualification failure.
Qualification now computes named reasons from the actual inventory and socket
receipts. The qualifier's synthetic, gap-free positive control returns COMPLETE;
it is a unit control, not a claim that this host is fully qualified.

## Closed in this round

* accept and accept4 register the returned socket with its listening socket
  identity and local address. Reads and closes use that new identity.
* IPv4 and IPv6 implicit UDP bindings record the assigned local port once.
* Real i386 socketcall socket, bind and listen probes pass. The decoder handles
  the simple scalar socketcall operations and rejects unsupported message layouts
  explicitly. This is a subset of compat support, not a full i386 ABI claim.
* Every injected lifecycle fault is generated from FAULTS and must match its
  capability, category and state with an INCOMPLETE capture. Corruption and loss
  also require lost_events greater than zero. Swallowing corruption, loss or ABI
  detection turns the AC4 row red.
* Both clone and clone3 CLONE_UNTRACED entry checks have a retained falsifier.
  The probe's invalid CLONE_THREAD flags prevent an escaped child in the mutant.

## Named AC2 limitations requiring an owner scope decision

These are implementation or qualification limits. They are not assertions that
the host lacks the corresponding facilities. Each reason is checked against
runtime evidence, with reason-removal red/green controls in round2.

**protocol_inventory_bounds**

4,123 unique family/type/protocol discovery cells: families 0 through 45, seven types, IPv4/IPv6 protocols 0 through 255 plus 262, netlink 0 through 31, other families at protocol zero

Approve an explicit qualification universe or supply a way to qualify additional and autoloadable protocols. This bounded inventory is not exhaustive Linux coverage.

**operation_address_fixture**

Every available cell gets bind/listen entry-path probes. Family-specific addresses are qualified for Unix, IPv4, IPv6 and netlink; other families get explicitly unqualified zero-sockaddr probes with kernel results. The measured host exposed 33 such cells.

Supply meaningful hardware/configuration/address fixtures for families 5, 8, 20, 24, 31, 38, 39, 40, 41, 42, 43 and 45, or approve a narrower universe. An error on a dummy address does not prove an operation unsupported.

**operation_configuration**

IPv6 datagram protocol 115 is available but ordinary IPv6 bind returns EINVAL.

Add its protocol-specific address/configuration fixture. Do not classify this as unavailable.

**io_uring_socket_effects**

Ring setup and REGISTER_PROBE succeed. An IORING_OP_SOCKET completion returns a real socket descriptor. The measured async helper produces an INCOMPLETE capture with io_uring failure.

Implement completion/identity correlation, including shared rings and SQPOLL, or approve a supported-path restriction. A successful submission is never counted as a socket effect.

**socket_destruction**

Successful closes are witnessed; recorded socket destruction is explicitly an inexact descendant-drain bound.

Qualify final reference destruction, including queued SCM_RIGHTS and external references, or amend the lifetime obligation.

**shared_socket_memory**

Entry/exit descriptor checks exist; the receipt explicitly records that they cannot exclude ABA replacement or concurrent sockaddr mutation.

Add a sound shared-memory/descriptor strategy or amend the obligation. A green reason-preservation test does not qualify the races.

**implicit_address**

A real Unix SO_PASSCRED autobind succeeds, and its unresolved local address makes capture INCOMPLETE.

Add exact implicit address enrichment for Unix and other unsupported families. Explicit Unix and implicit IPv4/IPv6 cases are covered.

**compat_socketcall_message**

A real int 0x80 sendmsg entry triggers this named INCOMPLETE capture.

Decode compat msghdr, ancillary data and message batches, then qualify the remaining compat operations. Other i386 syscall entries still fail as compat_syscall.

Generated acknowledged operation probes cover every available cell inside the
bounded inventory. Their successful service events are compared with the trace.
This closes the missing generated-probe mechanism within those bounds, not the
full AC2 exhaustive-universe obligation. Kernel errors and unqualified addresses
remain explicit. A fully qualified real host receipt is still unproven.

## AC4 specification cycle

VELDO-0113, VELDO-0114 and VELDO-0122 depend on VELDO-0111, while AC4 asks this
ticket to verify their implementations. They remain absent here. The exact named
stand-down adapter is tested; end-to-end consumer propagation remains open.

See [spec-conflict.md](spec-conflict.md) for the cycle and proposed owner amendment:
verify the consumer integrations in those tickets when they land. No spec file
was edited. AC4 acceptance remains pending the owner decision or implementation.

Round 1 evidence is historical. Round 2 drivers, receipts, diffs and digests are
under [round2](round2/README.md). Green local rows do not waive these open items.
