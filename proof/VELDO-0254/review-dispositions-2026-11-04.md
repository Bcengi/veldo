# Review dispositions for the new gate prerequisite tickets, 2026-11-04

Source: research/veldo-plan-consistency-review-2026-11-04.md (95 findings) and the lead's rulings
research/veldo-plan-rulings-2026-11-04.md (R1 to R14, binding). Owner request: Telegram 39145.

Scope of this writer: new tickets only, VELDO-0254 to VELDO-0258, on branch agent/claude/veldo-gate-prereqs.
No existing spec was edited. Before each ticket was written, the gate cluster (VELDO-0249 to VELDO-0253),
the workflow cluster (PLAN-0019, VELDO-0241 to VELDO-0247) and the parity cluster (VELDO-0232, VELDO-0234
to VELDO-0240, VELDO-0248) were searched at their branch tips; none covers the concern of any new ticket.

## New tickets and the section (c) findings each answers

- VELDO-0254, every run starts in the unprivileged sandbox with a gate-only network and an engine-only
  model login: C9 (model hosts recorded by qualification and read from the pinned record), C10 (rows for
  every engine the engines record names), C12 (the namespace setup refused by name at setup and launch).
  Also answers D1, A8 and R14, R5 (model hosts), R7, R13 (an engine the sandbox cannot confine waits).
- VELDO-0255, the outside gate and its check service are installed, supervised, upgraded and
  health-checked: C11, C12 (the keystore tool refused by name; the guide lists prerequisites).
- VELDO-0256, runs read the web, package registries and git through declared read routes, and a database
  only through a read-only server behind the gate: C5, C6, C7, C16 (kind 22).
- VELDO-0257, existing credential deliveries into runs move behind the gate and the old paths are removed:
  C4 (the VELDO-0181 part), C8 (memory store servers and the session-history worker), C13 (the end state for
  programs outside Veldo), C21. Also answers A1, A2, A6, A10, A13, A14, D9 (VELDO-0177 and VELDO-0183 part),
  E2, under R2, R5 and R7.
- VELDO-0258, Veldo's own outside calls take credentials from the keystore and settings from the
  installation repository: C15. Also answers A9 under R6 and R1.

## Every finding handled, one line each

- C1, rejected for a new ticket: the stored exact request is an amendment of VELDO-0252 under R4 (gate cluster).
- C2, rejected for a new ticket: canonical form and multipart digests are an amendment of VELDO-0252 and amend-0249 under R4 (gate cluster).
- C3, rejected for a new ticket: R3's release approved once and performed by the control-plane executor is VELDO-0244 on VELDO-0028's effect executor, absorbed by amending VELDO-0244 (workflow cluster); a chunked upload is a release of one file digest there.
- C4, applied in part: the VELDO-0181 path is VELDO-0257 AC3; the workflow nodes (VELDO-0241, VELDO-0243 to VELDO-0245) are amendments under R4 (workflow cluster).
- C5, applied: VELDO-0256 AC1, a read-only forward route, GET and HEAD only, with gate-side resolution and a destination filter.
- C6, applied: VELDO-0256 AC2 (registries as declared read routes) and AC3 (git fetch by a reviewed exact override, push never from a run).
- C7, applied: VELDO-0256 AC4, a read-only database server behind the gate with a role checked at start; mail and other non-HTTP protocols unreachable from runs (R5).
- C8, applied in part: memory store servers and the session-history worker are VELDO-0257 AC2; rejected for core's test ports: that belongs to the project's own repository, not to Veldo.
- C9, applied: VELDO-0254 AC3, qualification records each engine version's model hosts and the adapter reads them from the pinned record (R5).
- C10, applied in VELDO-0254 (rows for every engine the engines record names); the change to VELDO-0251's footprint and rows is the gate cluster's.
- C11, applied: VELDO-0255 AC1 to AC3 (units, restart, ports from the installation, health, upgrade); VELDO-0252 AC4 keeps the pin and checksum.
- C12, applied: VELDO-0254 AC1 (namespace setup) and VELDO-0255 AC4 (keystore tool, guide); the owner's cutover list is outside the Veldo repository.
- C13, applied: covered for launched processes by VELDO-0251 AC1; the end state for programs outside Veldo is VELDO-0257 AC4.
- C14, rejected for a new ticket: VELDO-0252 AC2 already defines the owner's consent from the UI and the channel; the VELDO-0234 dependency and the guide note are amendments of VELDO-0252 (gate cluster).
- C15, applied: VELDO-0258 under R6 (control plane outside the gate) and R1 (tracker and doorbell kinds in VELDO-0253's schema).
- C16, applied for kind 22 in VELDO-0256 AC4; rejected for a new ticket otherwise: kind 32 stays installation work in the factory repository (R10), kind 21 waits on C2 (gate cluster), kind 20's credential list is an amendment of VELDO-0251 AC4 and its spend checklist belongs to VELDO-0243 (R11, workflow cluster), the paid-service flag is R11 in VELDO-0251 and VELDO-0252 (gate cluster).
- C17, rejected for a new ticket: the one-time import commit is an amendment of VELDO-0253 or VELDO-0250 AC4 (gate cluster).
- C18, rejected for a new ticket: the full kind list is VELDO-0253 AC1 under R1 and R8 (gate cluster); VELDO-0258 adds its tracker and doorbell kinds there.
- C19, rejected for a new ticket: the widening list is an amendment of VELDO-0253 AC2 (gate cluster).
- C20, rejected for a new ticket: R9 makes the installation's declared remote the backup, an amendment of VELDO-0253 (gate cluster).
- C21, applied: VELDO-0257 AC4, the move into the keystore leaves other programs' copies untouched and the guide states the end state per service.
- C22, rejected for a new ticket: the cutover plan is the owner's installation document outside the Veldo repository; the Veldo steps it lacks are VELDO-0254 AC1 and VELDO-0255.
- C23, rejected for a new ticket: VELDO-0253 AC1 already creates the installation repository from the template; its location and VELDO_INSTALLATION are an amendment of VELDO-0253 (gate cluster).
- C24, rejected for a new ticket: R6 rules that messages to the owner through Veldo's own channel need no per-call approval, stated in VELDO-0240 and VELDO-0242 (parity and workflow clusters); VELDO-0258 AC3 repeats it for the control plane.
- D1, applied: VELDO-0254 owns the network namespace and the wiring of the launch into the sandbox; VELDO-0209 (withdrawn) and VELDO-0210 (draft) are not its dependencies, and VELDO-0210 is superseded (VELDO-0254 History); dropping them from VELDO-0251's depends_on is the gate cluster's.
- A8, applied: VELDO-0254 AC4, the engine's login readable by the engine process only (R7).
- A1, applied by VELDO-0257 AC1 instead of amending VELDO-0177, which lands as built (R2).
- A2, applied by VELDO-0257 AC2 instead of amending VELDO-0183, which lands as built (R2).
- A6, applied by VELDO-0257 AC3 instead of amending VELDO-0181, which lands as built (R2).
- A10, applied by VELDO-0257 AC1 (web through the read route, an engine's own sandbox network off) once VELDO-0256 exists.
- A13, applied by VELDO-0257 AC2 (the session-history server behind the gate, R5).
- A14, applied by VELDO-0257 AC2 (store servers reached only from the gate's tree, R5).
- A9, applied by VELDO-0258 AC1 (keystore references only for the tracker).
- D9, applied for VELDO-0177 and VELDO-0183 by VELDO-0257 depending on VELDO-0251; the other specs it names belong to the parity cluster.
- E2, applied by VELDO-0257 AC2 (memory tools classed by VELDO-0251 AC3, reads only by reviewed exact overrides).
- E6, applied: the new tickets call agentgateway "the outside gate".
- B1, rejected for these tickets: the request fixes owner dmitry; the role id is VELDO-0250's change.
- B2, rejected for these tickets: History keeps Telegram ids until VELDO-0250 replaces them, as requested; no requirement names a personal value.
