# VELDO-0111 open evidence

The starting main revision has no VELDO-0113, VELDO-0114 or VELDO-0122 suite or
consumer implementation. AC4 asks for propagation through those consumers while
their specifications depend on this ticket. This ticket provides and tests the
exact named stand-down contract. End-to-end consumer integration belongs to their
implementation and remains unproven here. Existing snapshot rows are not upgraded
or presented as census evidence.

The consumer specifications' footprints and this ticket's footprint place their
actual integration in separate tickets. An owner scope decision is needed if
that work is to be folded into this ticket instead. The exact eleven row names
and failure propagation API are implemented and tested here.

## Remaining kernel qualification

The measured host supports native x86_64 ptrace, fork, vfork, clone, clone3,
threads, nonleader exec, IPv4, IPv6 and Unix probes. qualification.json records
322 protocol-zero socket discovery combinations: 45 available and 277 refused
with kernel errors. It also records successful io_uring setup. Discovery does
not qualify every operation on those available combinations.

AC2 remains incomplete. The implementation still needs:

* Exhaustive available family/protocol/type operation probes, beyond the fourteen
  acknowledged service operations exercised here. Family numbers above the
  declared UAPI inventory cannot be certified by this inventory.
* Async socket effect decoding and acknowledgement. A successful io_uring setup
  or submission is never treated as a successful socket effect.
* Compat ABI/socketcall qualification, or a qualification environment where that
  path is unavailable. Native x86_64 is the only implemented syscall decoder.
* Complete implicit service-binding addresses, shared-address and descriptor
  race handling, external descriptor transfers, and exact socket destruction
  lifetimes. Current close events record successful descriptor closes; final
  descendant drain supplies only an upper bound on socket lifetime.

Every ordinary receipt therefore remains INCOMPLETE and every dependent row
stands down. The green event-fidelity checks and detected falsifiers establish
their concrete exercised behavior, not the full AC2 or downstream AC4 contract.
These are implementation and qualification gaps, not an owner-approved scope
reduction. The work is REMAINING.
