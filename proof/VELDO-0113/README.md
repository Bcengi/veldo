# VELDO-0113: blocked before implementation

Base: `1df7ae358bae1cf44b4ab5e1571f0c6fd523aa37`.
This bundle records a contract counterexample, not completed acceptance proof.
No production code, adapters, suite declarations or mutation registrations changed.

## Measured blocker

`reproduce_contract_gap.py` loads the production registry and the unchanged
VELDO-0112 adapter for `control_dispatch:Dispatches.prepare/in_process`.
The existing authority fixture prepares its valid arguments before shutdown.
The adapter subsequently receives those arguments and invokes the real registered
callable. Its store and connection are real and unchanged. The only argument
adjustment increases the fixture contract's 60-second deadline to 1200 seconds.

With the fixture server stopped and joined, the endpoint is removed. For the
second case a child binds/listens at the same endpoint, acknowledges readiness
through a pipe, then is killed and reaped. That child is only an endpoint fixture,
not a replacement authority. The kernel refuses connections with ENOENT (absent)
and ECONNREFUSED (dead socket). Both calls still return `prepared` and advance the
signed journal from sequence 12 to 13. `contract-gap.txt` binds each result to the
inventory, implementation, fixture sources and enrollment identities.

This refutes the universal endpoint-refusal premise of AC1. It does not establish
that the callable launches a process or listener. Inventing a refusing store or
filtering the inventory would hide this mismatch. The intended authority-loss
boundary for these in-process calls needs a contract decision before implementation.

## Source trace

- `scripts/fixtures/registered_clients.py:40`: eight Dispatches and two dispatcher
  entries use `in_process`; enumeration at line 74 joins the complete registry.
- `scripts/fixtures/registered_clients.py:26`: adapters call the public registered
  callable with arguments supplied by the consumer's fixture.
- `scripts/suites/113_veldo_0112_registered_clients.py:62`: Dispatches receives
  the real store connection; lines 154-179 prepare its valid arguments.
- `.veldo/control_dispatch.py:679` and `:747`: writes call `self.store.execute`;
  `:761` routes prepare to that writer. There is no socket check.
- `.veldo/dispatch.py:346`, `:567`: registered dispatcher front doors;
  the dependency fixture's floor seam at `113_veldo_0112_registered_clients.py:229`
  also writes directly to the store.
- `.veldo/control_claim_client.py:57` calls `.veldo/control_client.py:265`;
  its connection-failure handler at `:300` raises `authority_unavailable`.
- `.veldo/claim.py:329`, `:361`, `:379` delegate to the explicit claim client.
  `.veldo/work.py:178`, `:183`, `:210` and `.veldo/lander.py:308`, `:322`, `:340`
  are callers. The API and service wrappers preserve transport refusals at
  `.veldo/control_client_api.py:100` and `.veldo/control_service.py:5061`.
- The three footprint production files match their engine copies byte for byte.

## Census limitation

The independent no-op invocation in `census-receipt.json.gz` has COMPLETE event
capture and INCOMPLETE host qualification. It names protocol inventory bounds,
operation configuration and asynchronous socket effects as gaps. All three
VELDO-0113 consumer rows are STANDS DOWN with `census_incomplete`. This is a
dependency diagnostic, not the required registry/state consumer integration.
The compressed archive retains the complete original receipt; its digest is in
`contract-gap.txt`.

## Reproduction and remaining work

Run `python3 -B proof/VELDO-0113/reproduce_contract_gap.py` through the externally
provided host-heavy wrapper. Exit zero means the counterexample was reproduced,
not that VELDO-0113 passed. Readiness is acknowledged through a pipe and shutdown
through joins/waits; all new deadlines are 1200-second hang bounds. No sleeps are
used by the diagnostic. Dependency fixture code is unchanged.

The full client/state census integration, predeclared launch envelopes, three
declared red/green falsifiers, teeth registrations and mutation-gate findings
remain unimplemented. No gate was run. No independent review or approval is claimed.
Selected dependency selftests are supplemental diagnostics only; their dispatcher
deliberately exits 2 for a partial run and prohibits treating it as gate evidence.

All three selected runs completed with zero failures: VELDO-0109 reported 5 suite
assertions, VELDO-0112 reported 3, and VELDO-0111 reported 13 (their shared checks
bring the respective diagnostic totals to 31, 29 and 39). Lint passed over 1328
Python and 44 shell files. The personal-setup checker swept every ticket proof
file and the changed specification and reported zero findings. Its sweep API was
used to avoid the ancestry subcommand prohibited for this task. The installation
diagnostic's home prefix is normalized to `<user-home>` in the retained text.
