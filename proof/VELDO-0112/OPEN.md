# VELDO-0112 code and specification reconciliation

The requested main baseline places enrolled claim calls in
`.veldo/control_claim_client.py` and durable dispatch admission in
`.veldo/control_dispatch.py`. The spec footprint names neither file. The relay
carrier is `.veldo/control_relay.py`, also absent from that footprint. The
implementation includes those unprotected files and their engine copies so the
fixture exercises the production paths. The footprint is updated accordingly.

Current supported authority transports are local IPC for claims and commands,
the relay carrier for commands, and an in-process store connection for dispatch
admission. This ticket does not invent a remote dispatch or claim transport.
The explicit filesystem claim compatibility API retains its existing behavior;
the inventory qualifies its enrolled-client mode. Its public front doors are
still guarded by the same registrations.

The orchestration entry points in `dispatch.py` consume externally supplied
build, gate, proof, eligibility and floor services. Their positive controls use
those documented seams. They do not qualify a worker engine, real eligibility,
or the full floor journey. The durable dispatch entry points separately commit
through the real signed store writer with real reservation preconditions.
The relay controls call its real public carrier and CLI function; they do not
qualify SSH authentication. Those qualifications belong to their existing
specifications, not this fixture inventory.

No owner decision is pending. The full batch gate and independent review remain
for the later batch as requested. No claim of source landing is made.
