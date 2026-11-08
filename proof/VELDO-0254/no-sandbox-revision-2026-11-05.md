# No mandatory sandbox: spec revisions, 2026-11-05

Source: owner correction Telegram 39154 and the lead's answer 39155; revised rulings R5, R7 and R14 at the
end of research/veldo-plan-rulings-2026-11-04.md. Protection comes from where the keys live (only behind
the outside gate); runs keep today's access; leaked keys are caught by a secret scan; the confined runner
stays opt-in for risky work. Statuses unchanged. One line per spec changed.

## veldo-gate-prereqs

- VELDO-0254: replaced by the small ticket of revised R14: AC1 no outside-service credential is delivered into a run (static row and canaries); AC2 a secret scan of workspaces, landing candidates and project trees reports found credentials masked so they are moved behind the gate; AC3 runs keep today's access and the confined runner is opt-in for risky work. Sandbox launch, network namespace, model host list and engine-only login removed; depends on VELDO-0251, 0252, 0253; file renamed; VELDO-0210 no longer superseded.
- VELDO-0256: shrunk to the read-only production database behind the gate (role check at start, credential gate side); web forward route, registry routes, git fetch override, push refusal from runs, non-HTTP refusal and the VELDO-0254 dependency removed; file renamed.
- VELDO-0255: dependency on VELDO-0254, the per-dispatch relay sentence and the sandbox setup prerequisite removed; no confinement setup is a prerequisite.
- VELDO-0257: AC1 drops the web read route, the engine network grant off and the failing direct fetch; AC2 keeps memory store secrets behind the gate but no longer fences runs from store sockets or loopback ports (memory_socket_refused removed); VELDO-0256 dependency removed.
- VELDO-0258: AC3 checks that no run holds a control-plane credential instead of a run finding no route; Context and threat model match.
- VELDO-0259, VELDO-0260: checked, no sandbox, namespace, fence, Landlock or engine-confinement requirement; unchanged.

## veldo-0251

- VELDO-0251: every rule that a run can reach only the gate dropped (namespace, relay, DNS removal, egress fence, forward route, registry and git read routes, engine host list, engine-only login) with the VELDO-0254 dependency; a launcher-signed dispatch assertion replaces the relay's caller identity; kept: credentials only behind the gate, reads pass, writes need the owner's approval for that exact request. Title changed.
- VELDO-0252: relay assertion becomes the dispatch assertion; AC4 no longer claims runs cannot reach the check's loopback listener (a caller without the gate key gets no credential); forward route, public registry and per-dispatch relay mentions removed.
- proof/VELDO-0251/amend-0249.md: the subject header is stripped by the gate alone (no relay).

## Other worktrees

- VELDO-0249 (veldo-0249): AC2's subject digest header is stripped by the outside gate alone.
- VELDO-0253 (veldo-0253): the memory kind no longer says a run reaches a memory server only through the gate; a memory server with a credential is served behind it.
- VELDO-0237 (veldo-parity-a): assistant_codex keeps its network as today; the capture no longer feeds a sandbox host list.
- VELDO-0232 (veldo-0232): old R13 removed (model host list, proxy support, fail-closed wait, engine_proxy refusal); no role waits on engine-only login access; OPEN.md items 5 and 6 withdrawn.
- VELDO-0250 (veldo-0250), VELDO-0246 (veldo-0246), PLAN-0019 and VELDO-0241 to 0245, 0247 (veldo-workflow-process), VELDO-0236, 0238, 0239, 0240 (veldo-parity-a): checked, no requirement depends on the sandbox, the gate-only network or engine confinement; unchanged. PLAN-0019's older worker confinement and channel sandbox constraints (C8, C13, VELDO-0100) predate the gate design and were left as they are.

## Not reconciled

- VELDO-0257 AC2: with runs unfenced, a host memory store server that accepts writes without a credential is reachable from a run directly, so its writes do not pass the gate's approval. Closing that needs the store to require a credential held behind the gate; it is not specified here.
- VELDO-0251: the dispatch assertion in a run's environment is a gate caller identity, not an outside-service credential; a leaked one allows reads of the dispatch's selected services until the dispatch ends. Accepted under R7 as written, flagged for review.
