---
schema: veldo.spec/v1
id: VELDO-0251
title: Every outside call from a run or a project process goes through one gate, which alone holds the credentials, lets reads pass and sends every write to the approval check, with the network itself refusing any other way out
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0144, VELDO-0158, VELDO-0162, VELDO-0203, VELDO-0209, VELDO-0210, VELDO-0249, VELDO-0250, VELDO-0252]
placement: [contracts, engine, enforcement, distribution]
protected_paths: ["scripts/agent_sandbox.py", "engine/scripts/agent_sandbox.py", "scripts/agent_sandbox.json", "engine/scripts/agent_sandbox.json", "scripts/veldo_userns.c", ".veldo/pins/gate.json", "engine/.veldo/pins/gate.json", ".veldo/egress_classify.py", "engine/.veldo/egress_classify.py", ".veldo/installation.py", "engine/.veldo/installation.py"]
footprint:
  - ".veldo/egress_gate.py"
  - "engine/.veldo/egress_gate.py"
  - ".veldo/egress_relay.py"
  - "engine/.veldo/egress_relay.py"
  - ".veldo/egress_classify.py"
  - "engine/.veldo/egress_classify.py"
  - ".veldo/egress_openapi.py"
  - "engine/.veldo/egress_openapi.py"
  - ".veldo/egress_declaration.py"
  - "engine/.veldo/egress_declaration.py"
  - ".veldo/pins/gate.json"
  - "engine/.veldo/pins/gate.json"
  - ".veldo/installation.py"
  - "engine/.veldo/installation.py"
  - ".veldo/control_launch*.py"
  - "engine/.veldo/control_launch*.py"
  - ".veldo/control_credential_delivery.py"
  - "engine/.veldo/control_credential_delivery.py"
  - ".veldo/control_mcp_catalog.py"
  - "engine/.veldo/control_mcp_catalog.py"
  - ".veldo/control_engine_claude.py"
  - "engine/.veldo/control_engine_claude.py"
  - ".veldo/control_engine_codex.py"
  - "engine/.veldo/control_engine_codex.py"
  - ".veldo/control_service.py"
  - "engine/.veldo/control_service.py"
  - ".veldo/init_scaffold.py"
  - "engine/.veldo/init_scaffold.py"
  - "scripts/agent_sandbox.py"
  - "engine/scripts/agent_sandbox.py"
  - "scripts/agent_sandbox.json"
  - "engine/scripts/agent_sandbox.json"
  - "scripts/veldo_userns.c"
  - "docs/outside-services.md"
  - "scripts/suites/*_veldo_0251_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0251-every-outside-call-goes-through-one-gate.md"
  - "specs/index.md"
  - "proof/VELDO-0251/**"
behavior_bearing: true
observability:
  logs: >
    The gate writes one access line per call: dispatch id, project, service, route template or tool name,
    method, the classification (read or write) and the rule that produced it, the check verdict and its
    refusal name, the upstream status and the latency. Paths are logged as the declared template, never
    with query values, header values or bodies. The relay writes one line per accepted connection
    (dispatch, peer process id, bytes each way, close reason) and one line per refused engine tunnel
    (requested host). The declaration loader writes one line per service per revision: the declaration
    revision, the OpenAPI outcome (loaded as is, converted, refused with its name) and each operation
    moved to the HTTP route with its reason. No credential value, token or argument value is logged.
  metrics: >
    Count calls by service, classification and verdict; writes refused by refusal name; relay connections
    per dispatch; refused engine tunnels; declarations loaded, converted and refused by reason; operations
    served by the HTTP route because their body is not JSON; and tool drift events (a tool whose schema or
    annotations differ from its pinned snapshot).
  traces: >
    A dispatch id joins the run's execution record to its relay connections, each relay connection to its
    gate access lines, each write's access line to the approval check decision and token id of VELDO-0252,
    and the gate configuration revision in force to the declaration revisions it was generated from.
  error_taxonomy: >
    Gate and relay side, each returned to the caller by name with no upstream contact:
    service_not_declared:<service>, service_not_selected:<service>, route_not_declared:<service>,
    tool_not_declared:<service>:<tool>, approval_required (a write reached the check with no matching token;
    the check's own refusal names follow VELDO-0252), check_unavailable (the check could not be reached, so
    the call is refused, never let through), engine_tunnel_refused:<host>. Declaration side:
    invalid_input:service:<field>, invalid_input:service:literal_credential:<field>,
    unsupported_credential_kind:<kind>, openapi_refused:<service>:<reason> with reasons unreadable,
    not_openapi, swagger2, unconvertible:<pointer>:<construct>, missing_operation_id:<method>:<path>,
    multiple_servers, cookie_parameter:<operation>, external_ref:<pointer>, gate_load:<first line>;
    http_route_only:<operation>:<media type> (a report line, not an error); gate_config_rejected (the
    pinned gate refused the generated configuration, so the previous one stays in force); tool_drift:<tool>.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: a run or project process can reach an outside service only through the gate, and only the
      services its dispatch selected, because the network it lives in has no other way out. Set and
      completeness: every process Veldo starts for a run or a project (the engine and every tool child,
      catalog servers started inside the run, workflow steps, and the project processes Veldo launches)
      starts in a network namespace of its own that holds only a loopback interface, created by the
      namespace helper of VELDO-0210 before Landlock and the seccomp filter of VELDO-0209 are applied. The
      only listening socket in that namespace that leads anywhere is created there by the trusted launcher
      and held by the launcher-side relay outside the sandbox; the relay forwards each accepted connection
      to the gate's host listener and overwrites the caller identity with a signed assertion of the
      dispatch, its project and the services its capability configuration selected (VELDO-0162), removing
      anything the caller sent under that name. The run learns the gate only through non-secret values in
      its environment: VELDO_GATE_URL and, per selected service, VELDO_SERVICE_<NAME>_URL for its HTTP route
      and the gate MCP endpoint written into the generated MCP configuration. The single exception is the
      engine's own model traffic: the relay accepts an HTTP CONNECT tunnel only to the host and port pairs
      the engine adapter declares for its provider, passes the TLS through uninspected, adds nothing to it,
      and refuses every other tunnel as engine_tunnel_refused:<host>. No DNS resolver exists in the
      namespace. Rows, each against a stub vendor on a routable address with a planted key inside the run: a
      direct HTTPS call by IP, by IPv6, by a name, a UDP send, a raw socket, a CONNECT tunnel to the stub
      through the relay, a connection to the gate's host listener, to the check service of VELDO-0252 and to
      any other host loopback port all fail and the stub records nothing; the same call through the
      service's gate route reaches the stub; a call to a service the dispatch did not select is refused as
      service_not_selected and the stub records nothing; the factory's existing run journeys pass unchanged
      in the namespace.
    falsified_by: >
      Launch the run without the new network namespace, or let the relay forward a CONNECT tunnel to any
      host: the direct-call row or the tunnel row must reach the stub vendor and fail. Or let the relay pass
      the caller's own identity header through: the other-service row is let through and fails.
  - id: AC2
    text: >
      Claim: no outside-service credential or login ever enters a workspace, a run, a project process, an
      agent's environment or its context. Set and completeness: outside-service credentials are declared in
      the installation (AC4) by reference only and are added by the gate to the upstream request it sends,
      from the per-call backend token VELDO-0252 returns; the gate removes any Authorization header, any
      header the declaration names as a credential location and any query parameter it names as one before
      forwarding, so the vendor sees the gate's credential and never the caller's. VELDO-0158's delivery no
      longer resolves keystore references for outside services into a run: a catalog record (VELDO-0144)
      whose environment or headers carry a keychain reference is served behind the gate (its stdio server
      runs in the gate's own confined process tree under the AC1 namespace rule, reaching its vendor through
      the gate route where it accepts a base URL), and selecting such a record for a run directly is refused
      at launch as unsupported_configuration:credential_in_run:<record>. Catalog records with no credential
      (local tools) keep working as today. Rows, with canary values stored in the keystore for a stub service:
      the canaries appear nowhere in the run's readable filesystem, any run process's environment, the
      generated engine configuration, the prompt, the transcript, the execution record, the journal or the
      gate and relay logs; a run that sends its own Authorization header and a planted key in a declared
      query parameter to a route reaches the stub with only the gate's credential; for both engines.
    falsified_by: >
      Keep VELDO-0158's delivery of a record's keychain references into the run's generated configuration,
      or stop the gate from stripping the caller's Authorization header: the canary scan row finds the canary
      or the stub records the planted key, and the row fails.
  - id: AC3
    text: >
      Claim: reads and writes are told apart mechanically, anything unclassified is a write, and no write
      reaches a vendor without passing the approval check. Set and completeness: egress_classify.py is the
      one classifier, and its output for each declaration revision is a table both the gate configuration
      and the check service of VELDO-0252 read. HTTP routes: GET, HEAD and OPTIONS are reads; POST, PUT,
      PATCH, DELETE and every other method are writes. OpenAPI tools: the operation's method decides, by the
      same rule. MCP tools of a vendor server: a tool is a read only when the tools list snapshot pinned in
      the declaration revision marks it readOnlyHint true and not destructiveHint true; a missing or false
      annotation is a write. A tool whose name, input schema or annotations differ from the pinned snapshot
      is a write and is reported as tool_drift until the owner pins a new snapshot. The installation may
      tighten (declare a read as a write) freely, and may loosen only by naming an exact method and path
      template, or an exact tool, as a read in a revision saved by the owner's signed command (VELDO-0203);
      a prefix, a wildcard or an unsigned loosening is refused at load. Paths and tools not in the
      declaration are refused (route_not_declared, tool_not_declared). The gate sends every call of a
      selected service to the check (reads to fetch the backend token, writes also to verify the approval),
      in fail-closed mode: if the check cannot be reached, times out or answers anything but allow, the call
      is refused and nothing goes upstream. Rows against a stub vendor: a POST, PUT, PATCH, DELETE and an
      unknown method with no token, with a token for another call and with an expired token are refused and
      the stub records nothing; a GET passes with no token; an OpenAPI POST operation and an unannotated MCP
      tool demand a token; a tool whose annotations changed after pinning demands a token; with the check
      stopped every call is refused as check_unavailable; with a valid token issued under VELDO-0252 for
      exactly that call the write reaches the stub once.
    falsified_by: >
      Classify a tool with no annotations as a read, or attach the check only to calls the gate itself
      matched as writes and give the gate a rule that misses PATCH: the unannotated-tool row or the PATCH row
      reaches the stub without a token and fails. Or set the check to fail open: the stopped-check row
      reaches the stub and fails.
  - id: AC4
    text: >
      Claim: an installation declares its outside services in one generic schema, Veldo names none, and an
      OpenAPI file either becomes tools, is converted automatically, moves operations to the HTTP route, or
      is refused by name, never silently half-loaded. Set and completeness: each service is one file under
      services/ in the installation folder of VELDO-0250 (schema veldo.outside_service/v1), read only through
      installation.py and saved by the owner's signed command: name, upstream base URL (https only; backend
      TLS verifies the vendor certificate against the system roots, with no skip option), the HTTP route
      path templates the service may use, the credential (a keystore reference, or a grant name of
      VELDO-0252) and its location (bearer, a named header, a named query parameter or basic), optionally an
      OpenAPI file and the operation ids to expose as tools, optionally a vendor MCP server (remote URL, or a
      stdio command run behind the gate) with its pinned tools snapshot, the classification overrides of AC3,
      and the never rules (methods and path templates, or tools, refused outright). A literal secret is
      refused as invalid_input:service:literal_credential:<field>; a signature-based credential scheme is
      refused as unsupported_credential_kind:<kind>. Veldo's own defaults declare no service, and a fresh
      installation reaches no outside service. egress_openapi.py, standard library only, cuts the file down
      to the declared operations first, then: 3.0 loads as is; 3.1 is converted to 3.0 by a closed,
      documented set of rewrites (type lists with null to nullable, examples to example, const to a one-value
      enum, numeric exclusive bounds to the 3.0 form, dropped webhooks and pathItems), and any 3.1 construct
      outside that set refuses the file as openapi_refused:<service>:unconvertible:<pointer>:<construct>;
      Swagger 2.0 is refused as openapi_refused:<service>:swagger2. Each operation whose request body is
      neither application/json nor application/octet-stream is not made a tool and is listed as
      http_route_only:<operation>:<media type>, served by the service's HTTP route; a missing operation id,
      more than one server, a cookie parameter or a non-local reference refuses the file by its name. The
      generated gate configuration is first loaded by the pinned gate binary in a check instance; if that
      load fails the revision is refused as gate_config_rejected and the configuration in force stays. A
      refused file never removes the service's HTTP route. Rows: a 3.0 file loads; a 3.1 file with list
      types, const and webhooks converts and its tools answer through the stub; a form-encoded operation is
      absent from the tools and works through the route with its body unchanged; a file with an
      unconvertible construct, a Swagger 2.0 file and a file with a missing operation id are each refused by
      name while the route still serves; a generated configuration the gate rejects leaves the previous one
      serving.
    falsified_by: >
      Pass a 3.1 file to the gate unconverted, or keep a form-encoded operation as a tool: the conversion row
      fails on the gate's load error, or the form-encoded tool row reaches the stub with an empty body. Or
      swap in a configuration the check instance rejected: the previous-configuration row fails.
required_evidence: [unit, integration]
rollback: >
  Revert the change and restart the services: runs start without the new network namespace and regain the
  open outbound TCP they have today, VELDO-0158 delivery of catalog references into runs returns, and the
  gate and relay stop being started. Declarations in the installation folder, generated configurations and
  gate logs stay on disk, inert. No automatic rollback, retry or recovery is authorized.
---

## Intent

An agent, or a script an agent writes, that holds a vendor key can act on the owner's accounts with no one
asking. The owner decided that every outside call, whether an agent's tool call or a project's own code,
goes through one gate: the credentials live only behind it, reads pass, and every write needs the owner's
approval of that exact call. This spec builds the gate and makes it the only way out, enforced by the
network rather than by convention, so a stray key in a workspace is useless.

## Context

- Today a run's sandbox (VELDO-0209, agent_sandbox.py) confines files, Unix sockets and IPC, but allows
  outbound TCP and TLS in every profile. Catalog servers (VELDO-0144) run inside the run, and VELDO-0158
  resolves their keystore references into the run's generated configuration or the engine environment, so
  the credential is inside the run.
- VELDO-0249 (approved) gives a catalog server a way to verify the owner's approval of an exact write with
  a signed, single-use token. With one gate in front of every service, that check moves to one place; the
  change to 0249 is proposed in proof/VELDO-0251/amend-0249.md for the owner's approval.
- VELDO-0250 (approved) gives every deployment one installation folder; outside services are installation
  configuration, not product.
- The gate is agentgateway (Linux Foundation, Apache-2.0), pinned to v1.7.0 under the dependency rule of
  VELDO-0252. Facts this spec relies on, read from its v1.7.0 source and documentation: its OpenAPI target
  parses 3.0 only and passes only JSON or octet-stream bodies as tool arguments, and one bad operation fails
  the whole file; routes match on path and method and rewrite the authority and path prefix; backend
  authentication can compute the credential per call from extauthz.backend_token and removes the
  caller's credential; extAuthz can include the request body; mcpAuthorization removes denied tools from
  tools/list.

## Design

1. Network. The namespace helper creates a network namespace with loopback only for each run and project
   process tree. The launcher creates a listening socket inside that namespace before confinement and
   hands it to the relay, which stays outside. Sockets keep the namespace they were created in, so no
   forwarder runs inside the sandbox and nothing inside can widen the path.
2. Relay. Plain HTTP inside the namespace, one hop to the gate's host listener. The relay strips and
   writes the caller assertion (dispatch, project, selected services, expiry), signed with a key held by
   the relay and the check service only. It also carries the engine's provider tunnels, nothing else.
3. Gate. One route per declared service under /s/<service>/, one MCP target per service under
   /mcp/<service>, generated from the declarations by egress_gate.py. Every call of a selected service
   goes to the check of VELDO-0252 in fail-closed mode; the check returns the backend token, and for a
   write, only after the approval verifies. Never rules become deny rules ahead of everything else.
4. Classification. One classifier, one table per declaration revision, read by both the gate configuration
   and the check service, so they can never disagree on what is a write.
5. Declarations and OpenAPI. Installation files, owner-signed revisions, standard library conversion with
   a closed rewrite set, operations with non-JSON bodies served by the HTTP route, refusal by name, and a
   check-instance load before any configuration replaces the one in force.

## Out of scope

- The check service itself: approval verification, OAuth grants and backend tokens (VELDO-0252).
- The engine's own model traffic and its subscription login, which stay with the CLI through the adapter's
  declared tunnels; moving them behind the gate is filed for later.
- Signature-based vendor credentials (request signing schemes), refused by name and filed.
- Swagger 2.0 upward conversion, filed; such vendors use the HTTP route.
- Processes Veldo does not start. The installation guide (docs/outside-services.md) says how to keep the
  host's own programs off the vendor credentials, but Veldo cannot confine what it does not launch.
- Standing approvals for recurring writes: every write needs its own token here.

## What the reviewer judges

- Normal use: a project script reads a payments API's charges through VELDO_SERVICE_PAYMENTS_URL and gets
  them with no key in the project; an agent asks to refund one, the owner approves the exact request, and
  the next run's POST passes once; a second identical POST is refused.
- Threat model: a key pasted into a workspace; a script opening a direct socket, resolving a name, using
  IPv6 or UDP; a CONNECT tunnel to a vendor; a forged caller identity; a call to an unselected service; a
  vendor MCP server that changes a tool's annotations after review; a 3.1 file half loaded; a form body
  silently dropped; the check down; a credential reaching a log.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); attacks from
  host processes outside Veldo's launch path.

## Notes

The namespace makes the guarantee independent of any process inside the run behaving well: there is no
route out, so there is nothing to bypass. Writes are refused by default because a mistaken read label is the
one error that turns into an unapproved write; a mistaken write label only costs one approval. New servers
an owner finds in a public server directory enter only through a declaration like any other service.

## History

2026-11-04: new draft. Owner Telegram 39131 to 39140 approved the plan ("You asked for yes - yes"): one gate
for every outside call, credentials only behind it, reads pass and every write needs the owner's approval
token; mostly plain API routes; tools only where they add something, with automatic 3.1 to 3.0 conversion
and the HTTP route for non-JSON vendors; one small service of our own for approvals and OAuth
(VELDO-0252); discovery of new servers stays installation practice. The gate and the service are generic;
which services an installation uses, their credentials and never rules are installation configuration.
Proposed change to VELDO-0249: proof/VELDO-0251/amend-0249.md. Standalone.

2026-11-04: approved by the owner, Telegram 39144 ("Yes", to 39143). Status ready.
