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

The scaffolder also needs the new registry and the existing relay carrier in its
explicit runtime file list. Loading the full client set exposes a pre-existing
formatted path in `dispatch._floor_organ` that the installer cannot resolve. Its
path expression now exposes the literal file suffix without changing the path.
The ticket checks both the scaffold list and the real service dependency closure.

The first selected-suite run found one older assertion incompatible with loading
the registry beside the installed client: suite 47 forbade `__file__` anywhere in
the module. VELDO-0107 AC3 constrains socket placement, not dependency loading.
The assertion now checks socket derivation for `__file__` while retaining the
module-wide environment and current-directory checks, the two live authorities,
and the environment-routing falsifier. The initial failure is retained in
`selected-suites-initial.log` and `selected-suites-initial.json`.
