# VELDO-0203 builder evidence

Built on build-veldo-0203 from 4159d35b. Review, mutation execution and the
merged-tree gate remain reviewer work. No push, real model, login, real secret,
external host or user service manager was used.

The new OwnerRevisions entry point authenticates with control_membership's
shared authenticate function and delegates both saves to their existing writers.
Admit preserves its operation, command identity, journal signer and retry checks
before authentication, and keeps possession, policy and expected versions on
the same authority snapshot. Its existing callers were tested before and after.

AC1 needs one footprint extension: control_agent_config.py and its engine copy.
The writer had no assertion digest argument, and its store CAS refused a stale
base as plain stale_version. The optional assertion_digest retains signed
provenance in the immutable revision and names that CAS refusal
stale_version:agent_configuration when supplied. Existing API callers omit it;
their arguments, revision data and refusal names are unchanged. Authorization,
schema, base, version and read-back checks remain in the writer.

The only overlap with 0167 production files is the service route and the runtime
scaffold inventory that AC4 requires. No 0167 record or hint behavior is changed.

## Row coverage

* AC1: offline/saves executes real setup through ingress configuration, before
  the API edge is enrolled. It activates factory through the owner's signed
  project command, constructs the existing writers with setup's pm requester
  and real Inbox, saves all four role configurations and the default team,
  reads every revision back, and checks the journal principal, nonce, signed
  envelope digest, observations and metrics. Writer rows refuse stale bases,
  a missing required role and a generated credential literal with no write.
* AC2: authentication rows refuse absent signatures, another enrolled member's
  key, a revoked owner's key, a co-owner who is not the bootstrap owner,
  changed definitions, bases and teams, stale membership and delegation
  versions, foreign authority coordinates, expiry and a mismatched command id.
  Every refusal checks the unchanged journal and observation signer and class.
  Administrative and unknown operations are rejected, and admit continues to
  refuse both revision operations as policy_refused.
* AC3: replay rows return both committed revisions without writing, reject
  the same identity over different configuration or team content, and refuse
  consumed or unbound nonces. The store retains a command digest and transition,
  not original command bodies. Replay reconstructs the writer command from
  the immutable revision and before-versions, verifies its digest, then compares
  the presented parameters with the committed parameters as canonical bytes.
  This distinguishes JSON false from zero even though Python equality does not.
* AC4: a writable second connection cannot save while the installed service
  holds the lock. The actual installed service receives signed packets through
  control_client.send, commits and replays all five saves, records the forged
  signer, and returns a writer's own stale-team refusal. The sending process
  opens only a read-only SQLite handle during socket sends. The service's
  observations name the revision and digest. Missing API configuration is
  refused by name, and the runtime module is installed and scaffolded.
* format/fake-lines and the separate 0172 fake/capture report drive generated
  Claude and Codex installation fixtures through the shared format constructor
  and compare their emitted lines at teardown. No real CLI is executed.

Each row is reported once. An unexercised row fails, and raised journeys are
explicitly identified rather than counted as successful negative controls.

## Retained records

The red driver at drive.py uses the named selftest dispatcher against a
4159d35b archive with unchanged production. It overlays only the current suite,
its two fixture helpers and their suite registration. red-at-4159d35b.json retains every named failed assertion and
source hashes. It rejects raised journeys, duplicate failures or green owner
behavior rows, and requires the non-owner compatibility row to pass. Its scope
red mode instead requires only that compatibility row to fail against the
global-check regression. These are red records, not gate results.

mutations.json records 15 finding-203 mutations, exact diffs and source hashes.
They include each declared falsifier: replace the signed base with the head,
accept any active signing key, omit replay content comparison, and leave saves
to the service fallback. Additional mutations cover owner identity, signatures,
command identity, nonce binding, the lock, installation, provenance, the online
signer and writer refusal names. None was executed by this builder; rejected
mutation results belong to the reviewer.

checks.json records scoped suite summaries and their log hashes. Partial suite
runs return exit code 2 on success. They do not supply gate evidence or a
landing decision. No gate byproduct is committed.

## Limitations

Suite 86_veldo_0127_agent_configuration reports missing or stale committed live
Claude and Codex captures after the configuration writer changes. Its other
checks pass. Refreshing those captures would run real models, which the builder
instructions prohibit; the records are neither edited nor represented as fresh.

The supplied footprint checker compares origin/main with HEAD and includes
inherited 0167 and specification changes, so it reports outside paths.
footprint.json instead records this task's delta from the supplied 4159d35b
starting commit. No unrelated path is added to 0203's footprint to hide that
inherited difference.

## Original implementation scoped checks

The final suite passes 32 checks normally and under the empty gate environment.
Its unchanged-baseline red record has 31 distinct rows, all false by assertion.
Six admit dependency suites passed before extraction and after it. Sixteen
selected suites ran individually in both environments; fifteen passed, with
only the two live-capture rows of 0127 failing as described above. The final
standalone 0172 census passes and lists 0203_owner_revisions.

Validation passes, the Git subprocess boundary passes, all mutation names and
anchors are valid with zero bad anchors, and all five engine modules match
the repository copies byte for byte. The starting-commit footprint has no
outside paths. The supplied origin/main checker reports 59 inherited outside
paths, all present before this task.

## Review corrections at 3d209f42

Both supplied writers must use the exact connection whose authority lock was
checked; a mismatch returns missing_authority:not_the_authority. The new
lock/writer-connection row constructs each writer on another writable connection
in turn and requires refusal, an unchanged journal and a named observation.

Malformed packets, commands and envelopes return invalid_input:owner_command:packet
before authority or authentication checks. input/malformed covers top-level values
and both fields; service/malformed sends malformed fields over the installed
service socket and checks the refusal and observation. The transport already
rejects non-object top-level packets before dispatch. Both rows exercise null,
empty and nonempty arrays, strings, numbers and booleans.

The service imports control_owner_revisions once alongside its other organs.
The existing service/saves row still proves socket saves and exact replay.
The new finding-203 mutations are v203-writer-connection-unchecked and
v203-packet-shape-unchecked; the latter targets both malformed-input rows.
All 15 registered mutations have refreshed source hashes and exact diffs;
execution remains reviewer work. No footprint extension was needed.

All eight requested suites pass individually in both the ordinary and supplied
empty gate environments: 95_veldo_0203_owner_revisions,
38_veldo_0025_membership, 39_veldo_0026_revocation, 56_veldo_0027_signing,
71_veldo_0138_channel_service, 73_veldo_0139_factory_setup,
85_veldo_0171_setup_api and 82_veldo_0172_live_formats. Suite 95 passes 35
checks, including 34 behavior rows and the 0172 format check. The refreshed
4159d35b red record contains 34 failures by assertion with no raised journey.
The first test attempt also sent top-level malformed values over the socket;
the transport's existing malformed_request refusal correctly intercepted them.
The final socket row targets the malformed fields that reach Service.apply.

Validation and the Git boundary check pass in both environments. All five
engine copies match. Literal AST inspection confirms all 15 finding-203
mutation anchors and recorded mutant hashes without executing any mutation.
checks.json retains the earlier implementation runs and records the new runs
under review_fixes, with exact environment and log hashes. No full selftest,
mutation runner or gate was run. The 0127 proof remains untouched; the reviewer
still owns mutation execution and the merged-tree gate.

## Owner route scope correction at d04ed684

Service.apply no longer calls packet_problem before selecting a route. On the
owner route it reads the envelope principal only from a dict, then delegates
packet validation to OwnerRevisions.apply. Other routes retain their original
refusal paths. input/malformed retains direct packet, command and envelope
coverage; service/malformed sends owner-operation commands with non-dict
envelopes. service/non-owner-malformed sends non-dict commands through an
installed service and requires the original invalid_input:packet refusal,
unchanged journal and matching observation.

The refreshed 4159d35b record has 34 owner rows red by assertion and the new
compatibility row green. The driver requires that split explicitly. The
v203-packet-shape-unchecked mutation now bypasses packet_problem inside
OwnerRevisions.apply, targeting both malformed-owner rows. The signer mutation
anchor follows the guarded principal read. All 15 mutation anchors, hashes and
diffs are refreshed without execution. All 17 requested suites pass individually
in both the ordinary and exact gate environments: 34 runs, 391 suite checks per environment, zero failures. This
includes all seven suites numbered 82, the six admit caller suites and every
suite whose filename mentions service, channel, inbox, enrollment, mcp or claim.
Suite 95 passes 36 checks in each environment. Validation and the Git boundary
check pass in both environments, and all five engine copies remain identical.
checks.json records the runs under scope_correction with log and source hashes.

The unchanged d04ed684 archive makes exactly service/non-owner-malformed red by
assertion; its other 34 behavior rows pass. red-at-d04ed684.json retains that
result. The driver overlays only the suite, helpers and registration, just as
for the original base. No production is edited in either archive, and no
mutation is executed. The reviewer retains mutation execution and the
merged-tree gate.
