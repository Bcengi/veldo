# VELDO-0185 signed setup command blocker

Preflight on f63d86e5f596da178d5c43aaf8d258eec674c498, branch
build-veldo-0185b. This records a dependency gap, not implementation evidence.

The earlier attempt's missing revision writers have landed. The remaining AC1
gap is their authenticated entry point for fresh factory setup, which has the
owner's SSH key but no enrolled passkey or API session yet.

The actual VELDO-0162 interfaces are:

- `control_agent_config.Configurations.save`: writes immutable capability
  revisions through `save_agent_configuration`, checking the principal's
  authority. It accepts a principal, definition, base and command identity,
  but no owner command signature.
- `control_team_routes.TeamRoutes.save_default`: writes immutable default
  revisions through `save_default_team_revision`, checking the factory owner,
  roster, capabilities and base. It accepts an assertion digest, but no owner
  command signature. `read_default` provides the required revision read-back.
- `control_api_authority.Authority._apply`: the authenticated production route
  to those writers verifies an API-edge signature and requires a current
  credential through `control_api_credentials.current`. The HTTP edge builds
  that assertion from the owner's authenticated session. An owner SSH signature
  cannot substitute for the API-edge signature or the passkey credential.

These observations come from the checked-in production code, not a failing
fixture or a missing method-name guess. The relevant boundaries are
`control_agent_config.py:165`, `control_team_routes.py:179`,
`control_api_authority.py:342`, and `control_api.py:752`, with byte-identical
engine counterparts.

Neither of setup's existing signed-command paths fills this gap:

- `control_factory_setup.py:420` sends the owner's signed envelope through
  `control_membership.admit`. Its `ADMIN_OPERATIONS` contains only membership
  and delegation commands. A configuration or default-team operation is
  refused as `policy_refused` before admission.
- `control_service.Service.apply` routes API calls, MCP commands, enrollment,
  channel, inbox and claim operations, then falls back to `mutate`.
  `mutate` accepts only `MUTATIONS`, the store's generic command snapshot.
  Neither revision operation is in that snapshot; it is refused as
  `invalid_input:operation`. The revision writers register their transitions
  on the connection, which does not expand that external command boundary.

AC1 explicitly requires the owner's signed commands. Calling a writer with
the owner's principal string or supplying an assertion digest does not meet
that requirement. Generating an API credential or inventing an owner-signed
command adapter here would supply the missing prerequisite rather than consume
the promised interface. The user's instruction explicitly requires stopping
when that interface is absent or unusable.

Required prerequisite: an authenticated owner-key command entry point for both
revision writers, usable before passkey enrollment, preserving their existing
authorization, versioning and schema checks. A running-service use must also
obey VELDO-0171's lock rule. Alternatively, the owner can explicitly assign
that missing command integration to this specification.

No production files, VELDO-0167 files, acceptance criteria, status or protected
paths changed. AC1 to AC4 remain unimplemented by this attempt. There is no
behavior suite, red record or mutation rejection claim. No fake engine was
added. No real engine, credential, external host or service manager was used.
Final check results will be recorded below.
