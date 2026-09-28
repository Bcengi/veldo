# VELDO-0171 proof: setup lays the API down behind Tailscale Serve, and a second run changes nothing

## The design as built

**The API steps.** `veldo factory setup` (`.veldo/control_factory_setup.py`) keeps VELDO-0139's steps and
adds, from `.veldo/control_factory_setup_api.py`: the api edge key (`edge-api`, generated in the protected
key directory, its connection key `edge/api-auth` beside the Telegram edge's `edge/edge-auth`); its
enrollment as `api-edge` (the principal the ingress configuration names) by the owner's signed
`enroll_channel_edge` with the key's possession co-signature, exactly as the Telegram edge is enrolled,
and the key projection republished; `host/api-service.json` (veldo.api_service/v1, rp_id the tailnet name,
origin `https://<tailnet name>`), installed with the authority service through VELDO-0047's `api_service`
option; the 0600 `config/api-process.json` (veldo.api_process/v1, listening on 127.0.0.1:8171); the
systemd user unit `veldo-api-<service>.service` rendered from `.veldo/services/veldo-api.service`
(BindsTo, PartOf and After the authority unit, WantedBy it, with the `<authority unit>.wants` link that
`enable` would write), which runs the installation's own `bin/control_client_api.py` (now an entry point
of the fixed executable, `control_service.ENTRY_POINTS`); and `tailscale serve --bg --https=443
http://127.0.0.1:8171`, never Funnel, read back from `tailscale serve status --json`. The report names
every step as done, already done or deferred, with the tailnet name, the port and whether the store write
went through the running service.

**Tailscale, read-only first.** The CLI is the first executable regular file of a fixed list of system
paths (`TAILSCALE_PATHS`), never PATH. After every argument check and before the first write setup reads
`status --json` (a running backend, this node's DNS name as the tailnet name, its certificate domains),
`debug prefs` (OperatorUser), `serve --help` (whether it lists `--bg`) and `serve status --json`, and
refuses by name: `unavailable_service:tailscale` (absent or not running), `:operator`, `:https`,
`:persistence`, and `invalid_input:tailscale_serve:occupied` (the name's HTTPS mapped elsewhere or
funneled). A mapping that already names the API port is kept.

**The lock rule.** Setup writes the store only while it holds `authority.lock` itself (the fresh run takes
it before opening the store). A re-run that finds the lock held by the running authority service sends the
api edge enrollment to the service over its socket as the owner's signed command (the service's new
`api_edge` route in `control_service.py` admits only channel `api`, through control_channel_enrollment,
on its own connection and served repository), then republishes the key projection from a read-only view
of the committed store. Any other store write it would need is refused
`invalid_input:state_root:service_running:<step>`, writing nothing.

**The re-run.** A state root that holds a store is a re-run: accepted only when every argument equals
what the store and the installation were laid down with (owner and his key from the membership, workspace
from the ingress configuration and the binding, chat from the chat enrollment, token file, host trust and
Bot API origin from the ingress configuration, install root from the installation's service
configuration, unit directory from the authority unit, profile from the receiver configurations);
otherwise `invalid_input:state_root:holds_<argument>`, writing nothing. Every earlier step is reported
already done; every file a step writes is compared with what it would write (equal: left alone; absent:
written; different: `invalid_input:state_root:differs:<path>`, never overwritten). The one change to an
existing file is the installation's `service.json` gaining the `api_service` key it held as null. The
installed engine files are replaced only by VELDO-0189's upgrade, which runs first on a re-run over an
older engine (proof/VELDO-0189/); an installation whose engine, after that upgrade, would still have no API
process is refused `unavailable_service:api:not_installed` before anything is written. With the authority running and its installation already naming the API configuration, setup
starts the API unit itself; when this run added it, setup restarts nothing and names
`systemctl --user restart <authority unit>`.

**The passkey command.** `veldo factory passkey --state-root DIR --owner NAME --owner-key FILE` lists the
API's pending registrations (the API state directory's pending files, less those whose credential the
authority already holds) with each one's label, fingerprint and principal
(`control_api_credentials.describe`); with `--sign FINGERPRINT` it signs `enroll_api_credential` with the
owner's key for the ONE registration with that fingerprint and sends it to the running service. An
unknown, ambiguous or expired fingerprint is refused by name, signing nothing.

**The content security policy.** Every API response carries `default-src 'self'; script-src 'self';
connect-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'` (`control_api.CSP`),
the ones http.server writes itself (an unsupported method, a malformed request line) as well.

## The Tailscale capture

On 2026-09-27 the five authorized read-only commands (`tailscale version`, `status --json`,
`serve status --json`, `debug prefs`, `serve --help`) ran against the local tailscaled of the owner's
host, the CLI resolved from the fixed path list (`/usr/bin/tailscale`). The raw output stays only in
`/home/dmitry/projects/veldo-live-captures/2026-09-27/tailscale/`, outside every repository.
`scrub_tailscale.py` builds `tailscale-capture.json` from it by a named field allowlist, as VELDO-0172
does: schema field names and constants (the CLI version, backend states) survive; every other string is
`<string>`, every dynamic map key `<string:N>`, every number zero; the prefs keep only schema names and the
presence of OperatorUser; the serve help keeps only `--bg`. The scrubber checks every raw string, dynamic
key and output line longer than three characters against its result and refuses on any match (101 values,
none found), and an independent literal search of the committed file for every raw JSON string value and
whole output line (152 values) found none; no IP address but 127.0.0.1, no ts.net name, no login and no
account name appear.

Every state the suite's stand-in (`scripts/suites/support/v171_tailscale.py`) replays is a listed field
edit (`field_edits`): `ready` (a tailnet name of the reserved `.invalid` domain, its certificate domain,
no Serve mapping), `operator` (no OperatorUser), `https` (no certificate domain), `persistence` (a help
without `--bg`), `logged-out`, `occupied` (the name's HTTPS mapped to another loopback target) and `served`
(the status after `serve --bg --https=443 <target>`, whose one parametric value `@TARGET@` is the target
that invocation named, because each suite run listens on a port of its own). The real Tailscale leg is
run once by the lead with the owner and recorded; fixtures never count as it.

## Suite 85_veldo_0171_setup_api (18 rows)

- **AC1**: `api-edge/enrolled-by-owner` (the key files, the record, the possession proof, the service
  membership, one enrollment, the republished projection); `api-edge/installed-api-call` (the installed API
  process subscribes through the protected signer's api purpose and the service accepts its calls; a call
  signed with the enrolled edge key is accepted, one signed by the owner's key, the Telegram edge key or an
  unenrolled key is refused `command_signature_invalid`); `api-edge/running-service` (over the VELDO-0139
  host with its service running: the enrollment went through the service, every store connection setup
  opened was `mode=ro` (an audit hook on `sqlite3.connect`), the journal holds exactly the enrollment the
  service accepted, the projection republished; and with the Telegram edge retired and the service
  running, `service_running:edge_enrollment`, writing nothing).
- **AC2**: `tailscale/capture`, `tailscale/fixed-paths`, `tailscale/refusals` (operator, https,
  persistence, logged-out, occupied, absent CLI: each refused by name, nothing written, only read-only
  commands run), `tailscale/serve-bg` (the suite-owned invocation log shows exactly one successful
  `serve --bg` naming the API port and no `funnel`), `api/service-configuration`, `api/unit` (the rendered
  template, the want link, nothing started by setup, the API unit starting and stopping with the authority
  unit), `api/loopback-only` (the API process listens on 127.0.0.1 only, the service on no inet socket, no
  connection beyond loopback), `api/start-rules`.
- **AC3**: `passkey/first-enrollment` (two ES256 passkeys registered over HTTP with the tailnet name as
  Host and Origin, both listed with label, fingerprint and principal, an unknown fingerprint refused, the
  named one signed and admitted, the owner signs in and the session names him, the other cannot sign in and
  is still pending), `api/content-security-policy`.
- **AC4**: `rerun/changes-nothing` (every file under the state root, install root, unit directory, host
  trust directory and the workspace binding byte for byte the same, the journal and the Serve status
  unchanged, no key generated), `rerun/arguments-compared` (each of owner, owner key, workspace, chat,
  token file, host trust, install root, unit directory and profile), `rerun/differs-refused`,
  `rerun/over-0139-host`.
- `install/assets`: the scaffold, the engine copies, bin/veldo's `factory passkey` routing.

The host VELDO-0139 laid down before this change is laid down by the whole `.veldo` of commit 7fefdb9a
(VELDO-0139 with VELDO-0140's delegation), taken from the repository's history with `git archive` through
git_process and set up by that tree's own setup module, so the host holds that commit's engine (amended
AC4). The re-run upgrades it first (VELDO-0189, restarting the running service once) and then runs the API
steps through the restarted service. Over it, the earlier files that change outside the installed engine
are the installation's `service.json` (its engine keys, the `work` key it lacked, and its null
`api_service` key naming the API configuration), the receiver configuration (only the `host_trust` key it
lacked, which the upgrade adds) and the key projection, which AC1 requires republished once the api edge
key is enrolled (the protected signer's api purpose refuses a stale projection); the installed engine is
then the current one, name for name, byte for byte and mode for mode. `api/start-rules` counts the
upgrade's one restart and no other lifecycle call. The store files and the service's own state directory,
which the running service writes, are outside that comparison.

Suites 73 (VELDO-0139) and 74 (VELDO-0140) now give setup the same stand-in (added to this footprint), so
no suite reaches the host's real Tailscale; suite 73's re-run row expects `holds_workspace` (VELDO-0139
AC1 as amended) and its "only reloads" row accepts the second reload after the API unit. Suite 66 (VELDO-0047) names the API process
among the programs an installation runs by path, installed 0500.

## Red record and mutations

**Red record.** `python3 -B proof/VELDO-0171/drive.py --red 7851ae9b` runs the current suite once
against `git archive` of main at 7851ae9b, the commit this branch was built from: all 18 rows red, every
one by its own assertion (no API steps module, setup takes no Tailscale CLI, no capture or stand-in), in
`red-at-7851ae9b.json`.

**Mutations.** Finding 171 in `scripts/check_teeth_mutations.py` registers 17 mutants, each criterion's
declared falsifier first: `api171-edge-not-enrolled` (AC1, red on `api-edge/installed-api-call`: the API
process cannot sign and the service refuses the edge key's request signature), `api171-funnel-in-place-of-serve`
(AC2, red on `tailscale/serve-bg` by the invocation log's `funnel` although setup reports success),
`api171-origin-loopback` (AC3, red on `passkey/first-enrollment` by the registration's origin check) and
`api171-new-key-every-run` (AC4, red on `rerun/changes-nothing`), then the store written while the service
runs, the projection not republished, a listener beyond loopback, the operator setting unchecked, a CLI
location that is not a fixed system path, the API process dropped from the installed executable, the API
started although this run added it, the fingerprint ignored, the policy omitted or weakened, an argument
not compared, a differing file accepted and the module not scaffolded.
`python3 scripts/check_teeth_mutations.py --finding 171 --jobs 2` rejects all 17; `drive.py` records each
mutant red on its named row by assertion, the baseline and the five no-op copies green, in
`mutations.json` with one applied diff per mutant. Findings 139 and 140 still reject all theirs (21 and
12): three finding-139 anchors moved with the code, and its stale-projection mutant now also drops the api
edge's republish, which would otherwise publish the requester's key after it.

Rollback: stop and disable the API unit, run `tailscale serve reset` for the mapping setup made, remove
`host/api-service.json`, `config/api-service.json`, `config/api-process.json`, the API unit and its want
link by hand, set `api_service` in the installation's `service.json` back to null, and revoke the api edge
with the owner's signed retirement. Nothing is rolled back automatically.

Validation on this branch: suites 85, 73 and 74 green through `scripts/selftest.py --suite`, also under
the gate's isolated environment; `scripts/check_git_boundary.py` passes; the footprint check reports
nothing outside VELDO-0171's footprint; the anchor check reports 0 bad anchors; `.veldo/validate.py all`
passes. The gate was not run, no service manager was used and the host's real Tailscale was never run by
any suite.
