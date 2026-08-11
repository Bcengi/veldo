---
schema: veldo.spec/v1
id: WARP-0302
title: Auth/authorization runner (reference) - B5 of PLAN-0003
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0003
work: B5
plan_revision: 2
human_approval: not_required
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A generic authorization runner ships at
      engine/scripts/runners/auth/veldo_auth_runner.py. It reads an
      authorization journey fixture (JSON base_url, a named identities map where
      each identity carries the request headers that establish it, and a list of
      checks). Each check drives one request as a named identity (the identity
      headers merged with any check-level headers, the check winning) and
      declares an authorization expectation of allow (the identity must be
      authorized) or deny (the identity must be refused). It drives the endpoint
      with only the Python standard library (urllib), evaluates each check, and
      stops at the first failing check. It exits 0 when every check holds and
      exits 1 with the failing check and every failed assertion named.
  - id: AC2
    text: The authorization semantics are owner-scoping and cross-tenant safe,
      and fail loud. For a deny check, any 2xx response is an authorization
      bypass and fails the check even when no body assertion is given; a status
      outside the allowed denial set fails; and any body_must_not_contain string
      that appears in the response is reported as a cross-tenant data leak. For
      an allow check, a non-authorized status (by default not 2xx, or outside an
      explicit allow_status) fails, and any missing body_must_contain owner-data
      string fails. A check with no allow or deny expectation, or one naming an
      identity absent from the identities map, is a fixture error that fails loud
      (never a silent pass). A transport error is a named check failure, not a
      pass.
  - id: AC3
    text: A passing fixture and a deliberately-failing fixture ship under
      engine/scripts/runners/auth/fixtures/, driven against the bundled
      stdlib mock server. The mock server enforces owner-scoping on its /orders
      resource (the owner gets 200 with their record, a different user gets 403,
      an anonymous caller gets 401) and also exposes a deliberately-vulnerable
      /leaky/orders resource that returns any record to any caller (a classic
      insecure-direct-object-reference). The passing fixture asserts owner-allow,
      cross-tenant-deny, and anonymous-deny against /orders and the runner exits
      0; the failing fixture points the same cross-tenant deny check at
      /leaky/orders, the runner catches the bypass and the owner-data leak, and
      exits 1 with the cross-tenant violation named.
  - id: AC4
    text: The runner's control logic is unit-tested in scripts/selftest.py with
      no external dependency - an in-process stdlib http.server (ephemeral port,
      in a thread) models both the owner-scoping and the vulnerable resources,
      the runner is driven over both shipped fixtures (pass to exit 0, fail to
      exit 1 with the bypass named), and the pure authorization-evaluation
      function is exercised directly for allow and deny in both their true and
      false outcomes (the 2xx-bypass rule, a wrong denial status, a body data
      leak, missing owner data, and a missing or invalid expectation and an
      unknown identity). All prior selftest cases keep passing and the gate stays
      green.
  - id: AC5
    text: The runner is generic - zero company or product names in the runner,
      fixtures, mock server, wrapper, or README - and .veldo/capabilities.yaml
      (template and repository instance, kept byte-identical) declares it status
      reference (a shipped reference an adopting repo wires to its authorization
      or contract gate slot; the veldo repo does not run it), never mechanical.
      The docs-hygiene, secret, lint, and template-sync gates stay green.
required_evidence: [unit, operational]
rollback: git revert; B5 adds a new runner directory under engine, a
  selftest block, and an honest capabilities entry (template and instance) - no
  protected gate script or enforcer is touched, so reverting removes the
  reference artifact and its unit block with no effect on any running gate; the
  prior selftest cases are unchanged.
---

## Intent

PLAN-0003 (the batteries) ships a reference runner for every common product
surface. B1 shipped the HTTP/API journey runner and deferred authentication and
authorization to a later battery; B5 is that battery. The outcome that should
become true is that a repository with an authenticated API can drop in a generic
runner, describe a few identities and the resources they own, and get proof that
authorization holds: the owner reaches their own resource and no other identity
can reach it. Authorization defects are among the most common and most damaging
product bugs (cross-tenant reads, insecure direct object references), and they
are invisible to a runner that only checks the happy path as one user. This
runner drives the endpoint as more than one identity and asserts the boundary
between them.

## Context

B5 of PLAN-0003, feature F1 (surface runners), pulled against plan revision 2.
Depends on WARP-0301 (the HTTP/API runner), whose flow-first, stdlib, fixture-
pair, in-process-mock-server pattern this runner follows. The runner is
self-contained (its own request driver) so an adopting repo can drop in the auth
runner alone without also copying the API runner. The "fake driver" is a tiny
stdlib mock server that enforces owner-scoping on one resource and is
deliberately vulnerable on another, so the every-commit gate proves the
authorization evaluation and the request driving with no external service. The
central assertion is the deny check: for a request made as a non-owner, a 2xx is
an authorization bypass on its own, and any owner data appearing in the response
is a cross-tenant leak - both fail loud, because a runner that treated a
data-leaking 200 as "the endpoint answered" would be worse than none.

## Out of scope

Authentication mechanics themselves (token acquisition, refresh, session
management, signature verification) - this runner takes the headers that
establish an identity as given and asserts what that identity is allowed to
reach. Role and permission modeling beyond allow/deny against a resource. Rate
limiting and abuse controls. Wiring the veldo home repository's gate to this
runner: the home repo has no authenticated HTTP surface of its own, so the
runner ships as a reference marked status reference and is not run in the home
gate.

## Notes

Identity is expressed as headers so the runner stays mechanism-agnostic: a
bearer token, a cookie, or a signed header all reduce to "these headers make the
request this identity." An allow check defaults to accepting any 2xx and can pin
an explicit allow_status; a deny check defaults to the denial set 401, 403, 404
and can pin an explicit deny_status, but a 2xx is a bypass regardless of the set.
body_must_contain confirms the owner actually receives their data on an allow
(so an empty 200 does not masquerade as success), and body_must_not_contain is
the leak assertion on a deny. The optional [base_url] CLI argument (or the
BASE_URL environment variable) overrides the journey's base_url so the same
fixture aims at local, staging, or the in-process test server unchanged.
capabilities.yaml states the honest status: reference - never mechanical,
because the veldo repo does not itself run it against a live authenticated
endpoint.
