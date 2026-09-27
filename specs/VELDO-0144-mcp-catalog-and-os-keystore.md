---
schema: veldo.spec/v1
id: VELDO-0144
title: MCP servers defined once as versioned catalog records, with credentials only in the host OS keystore
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W104
plan_revision: 4
depends_on: [VELDO-0039, VELDO-0047, VELDO-0060, VELDO-0061, VELDO-0130]
placement: [contracts, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_mcp_catalog*.py"
  - ".veldo/control_mcp_catalog*.py"
  - "packs/*/.veldo/control_mcp_catalog*.py"
  - "engine/.veldo/control_credential*.py"
  - ".veldo/control_credential*.py"
  - "packs/*/.veldo/control_credential*.py"
  - "engine/.veldo/secretref.py"
  - ".veldo/secretref.py"
  - "packs/*/.veldo/secretref.py"
  - "engine/.veldo/control_api*.py"
  - ".veldo/control_api*.py"
  - "packs/*/.veldo/control_api*.py"
  - "engine/.veldo/control_service*.py"
  - ".veldo/control_service*.py"
  - "packs/*/.veldo/control_service*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0144_*.py"
  - "scripts/suites/71_veldo_0130_api.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0144-mcp-catalog-and-os-keystore.md"
  - "specs/index.md"
  - "proof/VELDO-0144/*"
behavior_bearing: true
observability:
  logs: >
    Record each catalog save (server id, revision, actor) and each credential write, replacement or
    deletion (credential id, set by), or its named refusal; never a credential value.
  metrics: >
    Count catalog revisions, credential writes, replacements and deletions, and refused saves by reason.
  traces: >
    Join each catalog revision and credential record to the API session and authority command that made it.
  error_taxonomy: >
    Distinguish stale or unauthorized save, invalid server definition, keystore locked, keystore
    unreachable and a refused read-back; none stores a value outside the keystore.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: MCP servers are defined once, through a typed API route and the authority's command, as
      versioned catalog records whose every save is a new immutable revision, and Atlassian is one of
      them. Set and completeness: Save a stdio server and an http server through the API's catalog
      route (a passkey session, VELDO-0130) and the authority's catalog command, then a second revision
      of each; compare every field of `mcp_server` (id, revision, label, transport, command and
      arguments, url, environment as literals or credential references, headers as credential
      references, the hosts it can run on, and the tools the owner marks read-only) with the stored
      revisions, and reject a stale or unauthorized save by name. Configure the Atlassian server as an
      ordinary catalog server with its credential in the keystore; no claude.ai connector is used.
      Falsifier: Overwrite a saved server revision in place; the revision-history check must fail.
    falsified_by: >
      Overwrite a saved server revision in place; the revision-history check must fail.
  - id: AC2
    text: >
      Claim: A credential's value is written to and read from the host OS keystore only, and the store
      keeps only its reference. Set and completeness: Set a credential through the API's credential
      route; the value travels once over TLS inside the passkey session to that route and on to the
      authority's credential command, which writes it to the Secret
      Service through `secret-tool`'s standard input and commits a `credential` record with id, label,
      reference, set at and set by, and nothing else; resolving it realizes secretref's `keychain`
      scheme. During and after the write, search the store, the journal, the event feed, proof, logs and
      every process command line for the value, and require it in none; replace and delete a value
      through the route, and require every read-back attempt refused. Falsifier: Pass the value to
      `secret-tool` as a command-line argument; the no-value-on-command-line check must fail.
    falsified_by: >
      Pass the value to `secret-tool` as a command-line argument; the no-value-on-command-line check
      must fail.
required_evidence: [unit, integration]
rollback: >
  Stop accepting catalog saves and credential writes; recorded revisions, credential records and
  keystore items stay as they are. No automatic rollback is authorized.
---

## Intent

MCP servers are defined in the UI and saved once, and every role selects them by reference instead of
carrying its own copy of each definition. Their credentials live in the local OS keystore, so a secret
never sits in the store, the journal, proof, logs or a command line; a cloud keystore replaces the
local one later through the same references if the factory runs in the cloud.

## Context

W104 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. Section 3 of the
approved [operating-model design](../docs/design/PLAN-0019-operating-model-design.md) (owner Telegram
29162) designs the catalog, the credential's two halves and each delivery route. VELDO-0127 (amended)
refers to catalog revisions instead of embedding definitions. `.veldo/secretref.py` (PLAN-0013) names
a secret by a reference such as `keychain:<name>` and resolves it only at use into a handle that never
prints its value, with only a test store behind it; `.veldo/secret_scan.py` detects credential shapes.
Delivering the values to a run is VELDO-0158, which also adds them to the run's set of resolved values
that VELDO-0141 replaces in its execution record before the scanner runs.

## Out of scope

A cloud keystore, per-run OS users, credential rotation reminders, the claude.ai connectors, storing
MCP credentials in the Mac keychain, and a connection test button.

## What the reviewer judges

- Normal use: the owner adds a server through the catalog route and sets its
  credential through the write-only credential route; roles select the server by id and revision; each
  run's delivery is VELDO-0158 (on the Mac VELDO-0147).
- Threat model: a credential value in the store, journal, event feed, proof, logs or a command line; a
  value read back through the UI or API; a saved revision overwritten; an unauthorized or stale save.
  The owner's account, the keystore and the host are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); a worker's
  tools deliberately reading the credentials its own servers use, or reaching the keystore through the
  owner's unconfined keyring daemon (the stated MVP boundary; separate OS users are Release 2); a
  keystore locked after an unattended reboot, which the owner unlocks at the desktop; forged rows in our
  own store and files planted in the installed directory.

## Notes

On Linux the keystore is the Secret Service of the GNOME keyring daemon already running in the owner's
session, reached through the `secret-tool` executable of the distribution's libsecret-tools package
(0.21.4 in this release's archive, not yet installed; GNOME's libsecret, LGPL-2.1+ with GPL-2+ parts),
run as a separate process and never linked. Installing it is the owner's one-time setup step. The
command's observation and journal entry exclude the value field by name. That needs the authority
service (`control_service`): its generic path commits a command's parameters through the store, which
journals the command's digest and hands the parameters to the owning transition, and records the
observation in the service's own log. So the credential command takes its own branch in the service's
`apply`, as `api_credential` and the channel commands do, which writes the value to the keystore and
commits only the `credential` record, and neither the digested command nor the observation holds the
value.

A Linux run gets its values through VELDO-0158, and a Mac run through one secrets frame over the same
SSH channel, as section 3 of the design sets out; that leg is VELDO-0147 AC4, built once VELDO-0124 and
VELDO-0125 land.

## History

2026-09-25: written as a draft for PLAN-0019 revision 4 from the approved operating-model design
(Telegram 29162), section 3(e). Draft; the owner decides readiness.

2026-09-25, PLAN-0019 revision 4 review: a specification ships whole and the run-check refuses one whose
dependencies are not shipped, so the Mac leg of this Linux-first qualification moves to VELDO-0147,
which is built after VELDO-0124 and VELDO-0125. Status unchanged.

2026-09-25, PLAN-0019 revision 4 review: leaving the value out of the observation and the journal does
need the authority service, so the footprint adds `control_service` (the credential command's own branch
in its `apply`, beside `api_credential`) and drops `control_runner`, which does not exist; the Runner
is class `Runner` in `control_launch`, already in the footprint.

2026-09-25, PLAN-0019 revision 4, third review: the keystore's values must enter each run's set of
resolved values that VELDO-0141 AC4 replaces, which would have been a fifth criterion, so this
specification keeps one concern, defining servers and storing credentials (AC1 the catalog, AC2 the
keystore write through the API's credential route), and delivery at launch is the new draft VELDO-0158:
its AC1 and AC2 are the former AC3 and AC4 with their text and falsifiers unchanged, and its AC3 the new
set criterion. The footprint drops `control_launch` and `control_engine`, which only delivery touches. AC2 sets the
credential through the API's credential route, which is what it drives; no form is part of this
specification.


2026-09-27, implementation on build-veldo-0144: added the immutable mcp_server
catalog and write-only credential commands on the passkey API and authority service.
Linux Secret Service is reached only through secret-tool, with values on standard
input and metadata alone passed to the store. The API assertion binds a separate
value by digest; no value is passed to the assertion signer. The runtime adapter
implements secretref's existing keychain store interface. The scaffold installs the
new modules and secretref; engine copies match the repository copies.

The footprint adds scripts/suites/71_veldo_0130_api.py because AC1 and AC2 extend
its published route and action universe: its forgery and actor-field checks now
exercise the new routes, and its authority fixture registers their real commands.
No existing assertion is removed or narrowed. Suite 82_veldo_0144_mcp_catalog uses
real passkey ceremonies, signed authority commands, SQLite and loopback TLS with
a generated certificate, and a generated fake secret-tool isolated from the real
keyring. Proof, the base-commit red record and finding 144 mutations are retained in
proof/VELDO-0144. Specification status and approval requirements are unchanged.

2026-09-27, review fixes on build-veldo-0144: merged main and repaired finding
130's catalog-expanded command anchor. Catalog revision fields now reject the
repository scanner's credential shapes by name before storage. Reference fields
must resolve by metadata record to a credential in this domain. Values still use
the credential route. Its replay identity includes the value digest; malformed
Unicode receives a named refusal and an API observation. Deleted records carry a
tombstone, while a subsequent SET stores the original five fields and counts as a
write. The keystore adapter preserves trailing newlines on piped lookup output.

The proof now captures authority and API file descriptors 1 and 2 and subprocess
pipe outputs, including fake secret-tool diagnostics and redirected Python stream
buffers in the proof driver. Lookup stdout remains the
intended runtime value channel. The fake requires a store label and matches
attribute pairs, including subset lookups, like Secret Service. Added assertion
rows cover all review decisions and mutations exercise diagnostic leaks, literal
and foreign-reference acceptance, CLI protocol drift, replay mismatch and deleted
state. The signed assertion excludes the value; the request signer receives the
request through pipes. This clarifies the earlier signer statement. The canonical
gate is intentionally not run under the implementation request; scoped checks
and proof remain observations for independent review, not a landing approval.


2026-09-27, third review fix on build-veldo-0144: main was already merged.
The catalog check now guards credential positions and known token shapes. One
named-position function covers credential names in environment entries, both
stdio flag forms, HTTP query parameters, URL userinfo and reference-only headers.
Known shapes reuse the repository scanner's PATTERNS by import. The catalog no
longer calls scan_text or uses entropy. The repository scanner is unchanged.
A secret the owner types as an ordinary literal elsewhere is the owner's choice;
the owner is trusted under the threat model. This check catches mistakes in
credential positions and known shapes, without claiming to identify every secret.

The ordinary-config-saves row preserves all 20 ordinary values from the reviewer's
probe, plus the requested worktree and Mac paths and a Confluence REST URL. The
probe's environment helper used API_TOKEN even for ordinary IDs and public keys;
the row uses CONFIG for those values so that it obeys the named-position rule.
Every saved field is compared exactly through both the API and store. Generated
hex and short values exercise the credential-position-refused row, which also
asserts that the store command was never called. Deleted credential metadata no
longer satisfies a reference; catalog/deleted-reference proves the named refusal.

The former catalog/credential-literals row and
mcp144-catalog-literal-accepted mutation are replaced by
catalog/known-shape-refused and mcp144-known-shape-accepted. They now test known
shapes independently of credential positions, including every existing PATTERNS
entry. The mcp144-entropy-restored mutation makes ordinary-config-saves fail.
Three separate position mutations make credential-position-refused fail, and
mcp144-deleted-reference-accepted makes deleted-reference fail. No row or mutation
continues to require entropy refusal. Status and acceptance criteria are unchanged.


2026-09-27, fourth review fix on build-veldo-0144: merged main. Credential names
now use lower-case tokens split at underscores, hyphens, dots and camelCase
boundaries, with the agreed final-token exemptions and absolute path allowance.
A bare credential flag does not consume a following flag. Known scanner shapes
still refuse anywhere, and headers remain reference-only. Refusal observations
record the field name and reason with the server id absent, including when the
refused value was the id. Extended ordinary and credential-position rows and a
new refusal-value row carry generated values; four new mutations exercise the
regressions. Filed, not fixed here: the repository secret_scan PATTERNS lacks
github_pat_, sk-proj- and sk-ant- shapes, which require a separate scanner change;
a token inside another argument such as docker -e NAME=value or --env NAME=value,
single-dash flags, and SORT_KEY-style names ending in key being refused remain
follow-up work. The repository scanner and acceptance criteria are unchanged.

2026-09-27, fifth review follow-up on build-veldo-0144: merged main; restored sig, signature and code query tokens, added authorization, authtoken, accesstoken, passphrase and privatekey credential tokens, refused Bearer/Basic authorization values in every string field, and refined bare credential flags to consume leading-hyphen values except double-dash flags and single-dash -x or -x=VALUE flags. Extended generated refusal and ordinary-save assertions, including pagination and encoding queries, and added independent query-extra and authorization-value mutations. Acceptance criteria and status are unchanged.

2026-09-27, sixth review follow-up on build-veldo-0144: merged main; refreshed and signed the authority-binding packet immediately before replay and asserted the binding refusal explicitly; narrowed query extras to whole case-insensitive names and Bearer/Basic values to complete credential shapes; added ordinary-name, prose and leading-hyphen assertion rows with three unique finding 144 mutations.
