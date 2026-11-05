---
schema: veldo.spec/v1
id: VELDO-0256
title: A run reads the production database through a read-only server behind the outside gate, on a database role that can only read, with the connection credential held gate side
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0251, VELDO-0252, VELDO-0253]
placement: [contracts, engine, enforcement]
protected_paths: [".veldo/egress_database.py", "engine/.veldo/egress_database.py"]
footprint:
  - ".veldo/egress_database.py"
  - "engine/.veldo/egress_database.py"
  - ".veldo/egress_declaration.py"
  - "engine/.veldo/egress_declaration.py"
  - "engine/.veldo/installation_schema/**"
  - ".veldo/installation_schema/**"
  - "docs/outside-services.md"
  - "scripts/suites/*_veldo_0256_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0256-the-production-database-is-read-only-behind-the-gate.md"
  - "specs/index.md"
  - "proof/VELDO-0256/**"
behavior_bearing: true
observability:
  logs: >
    The gate's access line of VELDO-0251 covers each database tool call with the service name and the tool,
    never a query value or a result row. The database server writes one line per start: the declared host
    and port, the role it connected as and the result of its read-only check.
  metrics: >
    Database calls by service and tool; database server starts by outcome; starts refused by reason.
  traces: >
    Each database tool call carries the dispatch id and the installation commit whose declaration was in
    force.
  error_taxonomy: >
    database_role_writable:<service> (the server's role could write, so the server does not start),
    database_precondition:<name> (a declared host precondition such as a private network link is absent).
acceptance_criteria:
  - id: AC1
    text: >
      Claim: a run reads the production database through a read-only server behind the gate, and that
      server can only read. Set: an installation may declare a production database service in its
      repository (VELDO-0253): a read-only MCP server that runs in the gate's process tree (VELDO-0251 AC2)
      with one declared destination (host and port), connecting as a database role that can only read; at
      start the server checks the role by a write attempt inside a transaction it rolls back and refuses to
      start as database_role_writable:<service> when it succeeds, and refuses as
      database_precondition:<name> when a declared host precondition (for example a private network link)
      is absent. Its tools are reads. Completeness: every declared production database service starts
      through the same check. Rows: a run's query through the gate's MCP endpoint answers from a fixture
      database; a server configured with a writable role does not start; a server whose declared
      precondition is absent does not start.
    falsified_by: >
      Skip the role check at start; the writable-role row starts the server and fails.
  - id: AC2
    text: >
      Claim: the production database's connection credential is held gate side only, so the read-only
      server is a run's only credentialed way to it. Set: the credential is a keystore item named in the
      service declaration and resolved by the gate; it is never written into a run's files, environment or
      command line (VELDO-0254 AC1). Runs keep their ordinary access to other databases, including shared
      development and test databases, unchanged; no network fence is added. Rows: a run's environment and
      readable files hold no canary for the production credential; a direct connection from a run with no
      credential is refused by the fixture database's own authentication; a run's use of a shared fixture
      development database works as today.
    falsified_by: >
      Pass the production credential into the run's environment; the canary row finds it and fails.
required_evidence: [unit, integration]
rollback: >
  Revert the change and restart the gate: the database server is no longer started, so runs lose read access
  to the production database through the gate. Declarations stay in the installation repository, inert. No
  automatic rollback, retry or recovery is authorized.
---

## Intent

Builds and investigations need to read production data. This ticket gives runs that read through a
read-only server behind the gate, on a role that cannot write, with the credential kept where every
outside-service credential lives: behind the gate.

## Context

- VELDO-0251 serves MCP services behind the gate with credentials held gate side.
- Runs keep today's access to shared databases, the web, package registries and git; those need no route
  through the gate.

## Design

One declared database service per production database, a read-only MCP server in the gate's process tree
with one destination, a role check at start, and the credential resolved gate side. If the pinned gate
cannot host a server with a TCP destination, the build records the blocker in this spec and stops.

## Out of scope

- Web, package registry and git access for runs, which need no route.
- Writes to the production database.
- The gate, its declarations and its check (VELDO-0251, VELDO-0252).

## What the reviewer judges

- Normal use: a run queries the production database read-only through the gate and uses shared
  development databases as today.
- Threat model: a database role that can write, a production credential found in a run, a server started
  without its precondition.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962).

## History

2026-11-04: new draft, Telegram 39145, from research/veldo-plan-consistency-review-2026-11-04.md (C5, C6,
C7, C16 kind 22) and the lead's rulings research/veldo-plan-rulings-2026-11-04.md (R5, R6, R12, R1 for
declarations in the installation repository).

2026-11-05: shrunk, Telegram 39154 and 39155, under revised ruling R14 (and R5): no mandatory sandbox, so
runs keep their web, package registry and git access and need no read route. The web forward route, the
registry routes, the git fetch override and push refusal from runs, the non-HTTP refusal and the dependency
on VELDO-0254 are removed; the read-only production database behind the gate stays. Git push still happens
from the control plane at landing (VELDO-0258). The file is renamed to match.

2026-11-05: the review amendments and new tickets approved by the owner, Telegram 39157 ("Yes", to 39156). Status ready.
