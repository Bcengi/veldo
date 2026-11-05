---
schema: veldo.spec/v1
id: VELDO-0256
title: Runs read web pages, package registries and git remotes through declared read routes of the outside gate, never push from a run, and reach a database only through a read-only server behind the gate
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0251, VELDO-0252, VELDO-0253, VELDO-0254]
placement: [contracts, engine, enforcement]
protected_paths: [".veldo/egress_classify.py", "engine/.veldo/egress_classify.py"]
footprint:
  - ".veldo/egress_gate.py"
  - "engine/.veldo/egress_gate.py"
  - ".veldo/egress_classify.py"
  - "engine/.veldo/egress_classify.py"
  - ".veldo/egress_declaration.py"
  - "engine/.veldo/egress_declaration.py"
  - ".veldo/egress_read_routes.py"
  - "engine/.veldo/egress_read_routes.py"
  - ".veldo/egress_database.py"
  - "engine/.veldo/egress_database.py"
  - ".veldo/control_launch*.py"
  - "engine/.veldo/control_launch*.py"
  - "engine/.veldo/installation_schema/**"
  - ".veldo/installation_schema/**"
  - "docs/outside-services.md"
  - "scripts/suites/*_veldo_0256_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0256-runs-read-the-web-package-registries-and-git-through-declared-read-routes.md"
  - "specs/index.md"
  - "proof/VELDO-0256/**"
behavior_bearing: true
observability:
  logs: >
    The gate's access line of VELDO-0251 covers each read route call, with the route kind (web, registry,
    git, database), the destination host and the declared template, never a query value or body. Each
    reviewed read override is logged once per accepted installation commit with its exact method and path
    template and the commit that declared it. The database server writes one line per start: the declared
    host and port, the role it connected as and the result of its read-only check.
  metrics: >
    Read route calls by kind and verdict; web reads refused by reason (method, destination address);
    git pushes refused from runs; database calls by tool; database server starts refused.
  traces: >
    Each read route call carries the dispatch id and the installation commit whose declaration was in
    force; each override joins to the owner decision that approved its commit.
  error_taxonomy: >
    route_read_only:<method> (a method other than GET or HEAD on the web route), destination_refused:
    <address class> (a web read that resolves to a loopback, private, link-local or the gate host's own
    address), read_override_not_declared:<service>:<method>:<template> (a POST read with no reviewed
    override, which then follows the write rule), git_push_from_run, database_role_writable:<service> (the
    server's role could write, so the server does not start), database_precondition:<name> (a declared host
    precondition such as a private network link is absent), protocol_not_routable:<scheme> (a non-HTTP
    service a run asked for that has no declared server).
acceptance_criteria:
  - id: AC1
    text: >
      Claim: a run reads web pages through one read-only forward route of the gate, and nothing else passes
      it. Set: the gate offers a forward route that accepts GET and HEAD to any public host on the declared
      ports, resolves names on the gate side, terminates TLS with an installation-local certificate
      authority whose certificate (never its key) is placed in the run's trust settings, verifies the
      destination's certificate against the system roots, and refuses every other method as
      route_read_only:<method> and any destination that resolves to a loopback, private, link-local or
      gate host address as destination_refused:<class>. The launcher sets the run's proxy variables to this
      route. Completeness: the route is the only web path a run has (VELDO-0254 AC2); the engines' own web
      fetch tools and any script use it. Rows: a GET and a HEAD of a fixture public page pass; a POST and a
      PUT are refused; a name that resolves to host loopback and one that resolves to a private address are
      refused; a page with an invalid certificate is refused.
    falsified_by: >
      Let the forward route pass every method; the POST row reaches the fixture page's server and fails.
  - id: AC2
    text: >
      Claim: package registries are declared read routes, and a run installs dependencies through them with
      no registry credential in the run. Set: an installation declares each registry it uses (for example a
      crates, npm or PyPI index or a mirror) as an outside service of VELDO-0251 AC4 whose reads are GET and
      HEAD; the launcher writes the run's registry settings (the package managers' configuration or
      environment) to point at VELDO_SERVICE_<NAME>_URL; a private registry's token is added by the gate,
      never placed in the run. A registry operation that reads by POST passes only under a reviewed
      override (AC3); a publish stays a write. Rows: a fixture build fetches its crates, its npm packages
      and its Python packages through fixture registries behind the gate; a private fixture registry
      receives the gate's token and the run holds none; a publish is refused approval_required.
    falsified_by: >
      Leave the run's registry settings pointing at the public index; the fetch rows find no route out and
      fail.
  - id: AC3
    text: >
      Claim: git fetch works through a declared read route, git push never leaves a run, and a read that
      uses POST is a read only by a reviewed override. Set: an installation declares a git remote host as an
      outside service whose upload-pack routes are read only by a per-route override naming the exact method
      and path template (git-upload-pack's POST, a registry search POST), committed to the installation
      repository and live only as a widening approved by the owner (VELDO-0253 AC2), and logged by name;
      without it the POST follows the write rule. A receive-pack route is refused from every run as
      git_push_from_run whatever its approval; landing pushes are made by the control plane outside the
      gate. Rows: a fetch of a fixture remote passes with the override and is refused without it; a push from
      a run is refused by name with an approval present; a prefix or wildcard override is refused at load.
    falsified_by: >
      Treat a declared git remote's routes as reads by host; the push row's receive-pack POST is classified
      read and reaches the fixture remote, and fails.
  - id: AC4
    text: >
      Claim: a run reaches a database only through a read-only server behind the gate, and no other non-HTTP
      service from a run. Set: an installation may declare a database service: a read-only MCP server that
      runs in the gate's process tree (VELDO-0251 AC2) with one declared TCP destination (host and port) as
      its only way out, the connection credential held gate side, connecting as a database role that can
      only read; at start the server checks the role by a write attempt inside a transaction it rolls back
      and refuses to start as database_role_writable:<service> when it succeeds, and refuses as
      database_precondition:<name> when a declared host precondition (for example a private network link)
      is absent. Its tools are reads. Mail submission and every other non-HTTP protocol have no route from a
      run and are refused by name. Rows: a run's query through the gate's MCP endpoint answers from a
      fixture database; a server configured with a writable role does not start; a run's direct TCP to the
      database fails; an SMTP connection from a run fails.
    falsified_by: >
      Skip the role check at start; the writable-role row starts the server and fails.
required_evidence: [unit, integration]
rollback: >
  Revert the change and restart the gate: the read routes and the database server are no longer generated,
  so runs lose web reads, registries and git fetch, and every such call is refused by the gate. Declarations
  and overrides stay in the installation repository, inert. No automatic rollback, retry or recovery is
  authorized.
---

## Intent

The gate takes away every network path a run had, including the ordinary reads builds and research need:
fetching a page, installing dependencies, cloning a repository, querying a database. This ticket gives
those back as declared reads through the gate, keeps writes behind approval, keeps pushes in the control
plane, and leaves every other protocol unreachable from a run.

## Context

- VELDO-0251 classifies by method: GET, HEAD and OPTIONS read, everything else write, and serves HTTP
  routes and MCP only; a stdio server behind the gate reaches its vendor only through a gate route that
  accepts a base URL, which a database does not have.
- git over HTTPS fetches with a POST to git-upload-pack, so without an override every fetch needs an
  approval.
- A CONNECT tunnel cannot be classified as read or write, so a forward route must terminate TLS.
- Provider-side web search rides the model connection and is unaffected.

## Design

1. Web. One forward route with TLS termination by an installation-local authority, GET and HEAD only,
   gate-side resolution and a destination address filter so the route can never reach the host.
2. Registries. Declared services whose URLs the launcher writes into the package managers' settings.
3. Git. Declared remotes; upload-pack read by a reviewed exact override; receive-pack refused from runs.
4. Database. A read-only server behind the gate with one declared TCP destination and a role checked at
   start. If the pinned gate cannot host a forward route with TLS termination or a server with a TCP
   destination, the build records the blocker in this spec and stops.

## Out of scope

- Write approval, the check and the declarations themselves (VELDO-0251, VELDO-0252).
- The network rule (VELDO-0254).
- Mail sending and other non-HTTP writes; reports to the owner go through Veldo's own channel.
- Vendored or offline dependency caches.

## What the reviewer judges

- Normal use: a run researches a public page, builds a project that fetches its dependencies, clones a
  repository and queries a declared database read-only, all with no credential in the run.
- Threat model: a web read aimed at a host service or a private address, a POST through the web route, an
  override written as a prefix, a push from a run, a database role that can write, a direct socket to the
  database.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962).

## History

2026-11-04: new draft, Telegram 39145, from research/veldo-plan-consistency-review-2026-11-04.md (C5, C6,
C7, C16 kind 22) and the lead's rulings research/veldo-plan-rulings-2026-11-04.md (R5, R6, R12, R1 for
declarations in the installation repository). Standalone; no plan work item.
