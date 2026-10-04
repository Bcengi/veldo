# VELDO-0162 builder evidence

Starting tree: 08d7edd38d06c17c2aff3ed30ab14f8ce900d8eb. Implementation stays on
build-veldo-0162. No push, gate, live model, real credential or external service is used.
The specification remains ready; independent review and the merged-tree gate are pending.

The capability route executes Configurations.save. The team route sends the derived,
edge-signed command to Teams.apply, which verifies the edge itself. A current project
owner saves an accepted revision and his decision in one team transaction. A member
creates a pending proposal and one exact amendment request. API settlement calls amend;
the authority service's existing publication hook applies Telegram settlements before
notifying the API. A factory owner's default save writes an immutable revision and a
head. Applying a settled default target reads its named revision and checks staffing
against the active destination project, then commits through the team writer.

The read routes are configuration revisions at configurations/revision and project
teams at team, with project=default selecting a default revision or its head. They
reuse authority inspection and the existing API redactor. Save routes are
configurations/save, teams/save and teams/default/save under the domain API prefix.
No browser writes the store. The configuration collection route retains its old path.

Suite 94_veldo_0162_configuration_routes has twenty rows, one report per row:

* AC1: configuration/revisions compares every field of two API-written revisions with
  the store and read route, including native tools, Atlassian and another catalog
  revision, skills, instructions, engine settings and both load modes.
  configuration/unauthorized-save and configuration/refusals require no revision from
  an unauthorized member, stale base or invalid configuration.
* AC2: team/roundtrip saves the required roster then adds builder_jira with its exact
  configuration reference. team/stale-team requires the old version refused without
  a change. team/staffing checks missing and unresolved references and incomplete
  staffing, including each actual owner request returned to the caller.
* AC3: team/owner-save and team/decider check immediate acceptance, no new decision
  request, the retained assertion digest and the journal's actual principal.
  team/unverified-assertion drives both the authority and Teams with signatures from
  another generated key. team/owner-answer compares the exact brief and target,
  repeats the submission at its original base, and settles through the API.
  team/telegram applies a signed Telegram answer through service publication.
  team/decline and team/other-request preserve the current revision on rejection
  or an answer to a different proposal.
* AC4: default/history compares immutable revisions and the head; default/refusals
  rejects stale, unauthorized and invalid saves. default/named-revision applies
  revision one after revision two is saved, with no second question. default/staffing
  gives an underbudget destination no team and returns its staffing request.
* Shared: routes/contract compares the operation, route, UI action and authority
  command registrations and checks session and actor-body refusals. routes/redaction
  plants a generated credential in role text and requires it absent from the response.
  install/assets compares and lays every exercised canonical engine module with the
  scaffolder, including the new team route module.

The fixtures use real signed membership, edge enrollment, capability, catalog, skill,
project activation, request and settlement commands, generated OpenSSH and ES256 keys,
real passkey enrollment and sign-in, the protected signer subprocess, SQLite, and the
production ServiceApi construction and call table. The API handler is driven directly
through a service-call proxy; this suite does not claim a new socket transport proof.
The existing 0130 suite covers that transport. Telegram uses a loopback Bot API stand-in.
Chat enrollment rows use the existing projection fixture's store writer. No fake Claude
or Codex executable is built, so this suite has no fake-engine format capture obligation.

The red driver at drive.py extracts the starting commit unchanged and runs the current
suite against that archive. red-at-08d7edd3.json records all twenty rows red by assertion,
with no raised region. mutations.json registers eighteen finding-162 mutations and
links their exact diffs and expected failing rows. None was executed by this builder;
no mutation rejection is claimed. The existing finding-89 signature mutation retains
its behavior and follows the signature check's new indentation.

checks.json records sequential normal and clean-environment suite runs. Partial selftest
success returns 2 by design. It is not unit evidence from a gate and cannot establish
landing readiness. static-checks.json records validation, Git boundary and anchor checks.
footprint.json separates the 0162 delta from inherited changes: the supplied checker
compares origin/main and reports inherited 0088, 0151 and 0152 paths; the delta from the
supplied starting commit has no path outside 0162's footprint. The footprint adds only
71_veldo_0130_api.py for its complete route census and command fixture registration.
The shared control_api_models.py action table is the only changed 0152 production file;
its intake reader and redaction behavior are retained.

The broad install-and-run suite invokes a nested gate, so it is not run under this
session's prohibition. The scoped asset row and setup-assets suite exercise installation
without invoking that gate. Full selftest, teeth execution and merged-tree verification
remain the reviewer's work.
