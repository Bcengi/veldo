---
schema: veldo.spec/v1
id: WARP-0307
title: Integration/external-service runner (reference) - B7 of PLAN-0003
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0003
work: B7
plan_revision: 2
human_approval: not_required
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A generic integration/external-service runner ships at
      engine/scripts/runners/integration/veldo_integration_runner.py. It
      reads a contract journey (JSON, a base_url, a timeout, and a list of
      interactions, each with a request of method/path/body/headers, an
      expect_status, and a contract of required dotted-path fields with declared
      types and forbidden dotted-path fields). For each interaction it drives the
      request against the sandbox base_url with only the Python standard library
      (urllib), parses the JSON response, and validates the response against the
      declared contract. It exits 0 when every interaction conforms and exits 1
      with each violation named. The transport is a seam - the base_url (or the
      BASE_URL environment variable) is overridable so an adopting repo points the
      same journey at its own sandbox unchanged.
  - id: AC2
    text: The contract checks are real and fail loud. An unexpected status, a
      missing required field, a field of the wrong declared type, and a forbidden
      field that is present each fail, naming the interaction and the exact
      field/type/status. Types are the JSON value kinds (string, number, integer,
      boolean, array, object, null), and because a bool is a subclass of int an
      integer or number type rejects true/false. Nested dotted paths resolve
      (objects by key, lists by integer segment) and distinguish an absent path
      from a present-but-null one. An interaction that declares no expect_status,
      no required field, and no forbidden field asserts nothing and is a journey
      error, because a check that asserts nothing is not proof.
  - id: AC3
    text: A passing fixture and a deliberately-failing fixture ship under
      engine/scripts/runners/integration/fixtures/, driven against a
      bundled stdlib mock server. The passing fixture asserts the full contract
      (expected status, required fields present and correctly typed via dotted
      paths, forbidden fields absent) against a conforming resource and the runner
      exits 0. The failing fixture points a contract at a deliberately-violating
      resource (a required field arrives as the wrong type, another required field
      is missing, and a forbidden internal field is present), the runner catches
      the violations, and it exits 1 with each violation named. The mock returns
      fixed payloads, so both outcomes are deterministic.
  - id: AC4
    text: The runner's control logic is unit-tested in scripts/selftest.py with no
      external dependency - the contract-check helper for every outcome (each
      declared type matched and mismatched including that a bool is not an integer
      or number, a required field present and absent, a forbidden field present
      and absent, a status matched and mismatched, and a nested dotted path
      present and absent), plus the runner driven over both shipped fixtures
      against an in-process mock server on an ephemeral port (pass to exit 0, fail
      to exit 1 with the violation named) and the asserts-nothing journey error.
      All prior selftest cases keep passing and the gate stays green.
  - id: AC5
    text: The runner is generic - zero company or product names in the runner,
      fixtures, wrapper, or README - and .veldo/capabilities.yaml (template and
      repository instance, kept byte-identical) declares it status reference (a
      shipped reference an adopting repo wires to its integration or contract gate
      slot; the veldo repo has no external integration of its own to run), never
      mechanical. The docs-hygiene, secret, lint, and template-sync gates stay
      green.
required_evidence: [unit, operational]
rollback: git revert; B7 adds a new runner directory under engine, a
  selftest block, and an honest capabilities entry (template and instance) - no
  protected gate script or enforcer is touched, so reverting removes the
  reference artifact and its unit block with no effect on any running gate; the
  prior selftest cases are unchanged.
---

## Intent

PLAN-0003 (the batteries) ships a reference runner for every common product
surface. B7 is the integration and external-service surface. The outcome that
should become true is that a repository can drop in a generic runner, drive an
integration in sandbox/contract mode, and get proof that the response conforms
to a declared CONTRACT: the expected status, the required fields present and of
the right type, and the forbidden fields absent. A payload-shape or type drift
(a number that arrives as a string, a required field that vanished, an internal
field that leaked) is a real integration defect that a happy-path "it returned
200" check never sees. This runner reads the contract as data and asserts it.

## Context

B7 of PLAN-0003, feature F4 (boundary surfaces - external integrations, payload
and contract conformance), pulled against plan revision 2, depends on WARP-0301
(the HTTP/API runner, whose request-driving and dotted-path assertion this runner
narrows to contract conformance). It follows the shipped runners' pattern: a
generic reference under engine/scripts/runners/, a fixture PAIR, and a
unit test that gate-tests the control logic. The transport is a SEAM: run()
takes a caller(interaction) -> (status, body) that defaults to a urllib request
against base_url, so the contract logic is gate-tested in-process with no
network, and an adopting repo points the same journey at its own sandbox. The
fixtures keep the gate deterministic by construction: the mock server returns
fixed payloads, one conforming and one deliberately violating, so the pass and
fail outcomes never depend on a live service.

## Out of scope

Full signed or content-addressed schema contracts, versioned golden-payload
capture, and JSON Schema / OpenAPI validation - the reference asserts a
proportionate contract (status, required-and-typed dotted fields, forbidden
fields), and the golden-contract drift surface is B11 (WARP-0311). Authentication
and authorization of the integration (covered by WARP-0302). Streaming and
websocket transports (B12). Provisioning a real third-party sandbox or fixture
data (that is where the base_url and caller seams plug in). Wiring the veldo home
repository's gate to this runner: the home repo has no external integration of
its own, so the runner ships as a reference marked status reference and is not
run in the home gate.

## Notes

The contract is expressed as data so the runner stays mechanism-agnostic:
expect_status is the set of acceptable statuses, contract.required is a map of
dotted-path to declared type, and contract.forbidden is a list of dotted-paths
that must not appear. Types are the JSON value kinds; integer and number reject
bool because a bool is a subclass of int in Python, so True never satisfies an
integer field. A dotted path indexes objects by key and lists by integer segment
(items.0.qty), an absent path is distinguished from a present-but-null one (a
required field set to null is present-but-wrong-type against a non-null type,
not silently missing), and an interaction that asserts nothing is a journey
error rather than a vacuous pass. The optional [base_url] CLI argument (or the
BASE_URL environment variable) overrides the journey's base_url so the same
fixture aims at a local stub, a vendor sandbox, or the in-process test server
unchanged. capabilities.yaml states the honest status: reference - never
mechanical, because the veldo repo does not itself run it against a live
integration.
