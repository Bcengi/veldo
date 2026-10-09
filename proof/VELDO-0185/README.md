# VELDO-0185 current build blocker

2026-10-08, branch agent/codex/veldo-0185 at 294e1933. The earlier
owner revision and reservation policy prerequisites are present. This attempt
stopped at host qualification, before its new dispatch setup steps could run.
No implementation or acceptance proof is claimed.

The installed-host fixture reused the real setup and installation machinery
from VELDO-0171 and the generated CLI assets used by VELDO-0203. The first run
of draft suite `106_veldo_0185_dispatch_setup` refused setup with
`unavailable_service:profile:user_manager`. The unchanged
`control_containment._host_problems` queries the user's systemd manager before
setup writes the factory. The socket at `/run/user/1000/bus` exists, but a direct
systemctl query returns `Failed to connect to bus: Operation not permitted`.
Repeating the read-only query with explicit runtime-directory and bus-address
environment variables returns the same error.

The machine-readable [preflight record](host-preflight-2026-10-08.json) preserves
the commands and selected failure output. The draft run reported 26 shared
harness assertions passed and five failed checks. Four failures depended on
the host qualification refusal. The fifth was a separate incorrect call to
the fake-format observer in the incomplete test draft, not host evidence.
The unverified production draft, suite and registrations were removed. No
qualification bypass or replacement of the real host check was retained.

Resume requires an authorized execution environment in which the existing
installed-host fixture can query the systemd user manager. This is an execution
environment blocker, not a finding that the specification is contradictory or
that a new product prerequisite is missing. Suite 106 still needs to be built
and registered when implementation resumes.

The acceptance criteria remain unchanged and unproven:

| Criterion | Operational proof still required | Required falsifier |
| --- | --- | --- |
| AC1 | Read four saved role configurations and the default team; verify both installed adapters and an available, configured loop. | Omit the installer's work option; loop configured must be false. |
| AC2 | Reserve as authority and launch-receiver; launch through installed receivers with the shared state root. | Enroll both principals without reservation_service; reservations must be refused. |
| AC3 | Compare all file bytes and the journal head after a second run; check additive upgrades and named differing-file refusals. | Repeat both enrollments; the changed journal head must fail the second-run row. |
| AC4 | Register every host account, read its policy, refuse a logged-out account before spawn, and build and review through every logged-in account. | Omit Codex to fail every-account coverage; omit registration to fail fresh account read-back. |

Only the draft specification suite was run. No full selftest, mutation driver,
canonical gate, real engine login, push or merge ran. There is no green gate
stamp, proof manifest or independent review for this attempt. The spec remains
ready; this record does not mark it shipped.

## Historical signed-command blocker


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
- `control_api_authority.ApiAuthority._apply`: the authenticated production route
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

Checks of this blocker-only change:

- Suite `82_veldo_0172_live_formats` passes normally and in the specified empty
  gate environment: four suite rows, 30 assertions including harness checks,
  zero failures in each run. Its census lists the existing 16 producers; there
  is no 0185 producer to qualify. These partial runs prove no 0185 criterion.
- The supplied anchor checker reports 0 bad anchors. Git boundary passes.
- The four cited production modules have identical engine counterparts.
- The supplied footprint checker compares with local `origin/main` and reports
  65 changed paths, 48 outside this spec, inherited from the supplied base.
  The actual attempt's delta from f63d86e5 contains only this README and the
  spec History entry, both inside the declared footprint. No footprint was
  expanded to absorb inherited changes.
- Repository validation of all records passes. The full selftest, mutation
  runners and canonical gate were not run. No gate stamp is claimed.
