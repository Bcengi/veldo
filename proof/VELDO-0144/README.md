# VELDO-0144 implementation proof

The catalog stores each MCP server as an immutable `mcp_server` revision, with a
separate head. The passkey API and host-signed authority commands use the same
catalog writer. Atlassian is an ordinary HTTP server record. No engine launch or
credential delivery behavior changes; that work belongs to VELDO-0158.

Credential writes use Linux Secret Service through `secret-tool`. The value goes
on stdin. The API signs a digest binding and carries the value separately to the
authority, which checks the binding before writing. The store command, including
its digest input, excludes the value field and binds its SHA-256 digest for replay.
A repeated command id with a changed value is refused by name. A SET record has exactly `id`,
`label`, `reference`, `set_at` and `set_by`. Deletion removes the keystore item and
retains reference metadata and journal history with `deleted: true`. A later SET
removes the tombstone and counts as a write, including on an identical retry. Runtime callers pass
`control_credential_keystore.SecretService()` to the existing
`secretref.resolve_for_runtime` interface; it returns the existing opaque handle.

The configuration action contract lists the three new write operations. The
service records catalog and credential observations with actor, session, command,
revision or credential identity, outcome and named refusal. Its status includes
catalog and credential operation counts. New modules and secretref are scaffold
assets; changed engine modules are byte-identical to their repository copies.

The catalog check guards credential positions and known token shapes before a
revision is stored. One named-position function covers environment names, stdio
flags with inline or following values, HTTP query names, URL userinfo and headers.
Names split on underscores, hyphens, dots and camelCase boundaries into lower-case
tokens. Credential tokens include authorization, authtoken, accesstoken, passphrase
and privatekey. URL query names additionally match sig, signature and code tokens.
Credential tokens match whole tokens, and key or pat match only the last token.
A final file, path, dir, name, port, url, host, id or callback exempts the name. Absolute filesystem paths starting with / or ~/ are allowed as position
values. A bare credential flag consumes the following item unless it starts with
two hyphens or is a single-dash flag of the form -x or -x=VALUE. A single hyphen
followed by a generated hex value is consumed. A string beginning with Bearer or
Basic followed by a space, case-insensitively, is refused in every field. Headers
remain reference-only. Refusals record the top-level field name and reason, with no server id; a refused id cannot enter either catalog
observations or observations.jsonl.
Known shapes reuse the repository scanner's PATTERNS by import. The catalog never
calls scan_text or applies entropy; the repository scanner is unchanged. A secret
the owner types as an ordinary literal elsewhere is the owner's choice, and the
owner is trusted under the threat model. Tagged references must match active
credential metadata in this domain. Another factory's item, an arbitrary keyring
item and a tombstoned credential all receive a named refusal.

## Criterion rows

Suite: `scripts/suites/82_veldo_0144_mcp_catalog.py`. Each row reports once.

- AC1, `catalog/stdio`: Both revisions round trip every field through the API and SQLite.
- AC1, `catalog/http`: Both HTTP revisions preserve URL, reference headers and every other field.
- AC1, `catalog/host-command`: Host-signed service commands create two revisions of each transport.
- AC1, `catalog/immutable-history`: All four API revisions survive later saves and remain selectable by id and revision.
- AC1, `catalog/stale-unauthorized`: Stale saves, another actor, forged signatures and a live session whose owner role was removed are refused without writes.
- AC1, `catalog/invalid`: Invalid transports, fields and literal/reference shapes are refused without writes.
- AC1, AC2, `catalog/atlassian`: Atlassian uses the ordinary HTTP catalog schema and a resolvable keystore reference.
- AC2, `credential/write`: A real TLS passkey request writes exactly five metadata fields; keychain resolution returns the generated value in an opaque handle.
- AC2, `credential/replace-delete`: Replacement resolves only the new value; deletion removes the item and resolution refuses.
- AC2, `credential/read-back`: API reads after write, replacement and deletion all refuse by name.
- AC2, `credential/no-value-on-command-line`: The fake executable observes stdin and scans every accessible live process command line; values appear in none.
- AC2, `credential/no-value-in-records`: During and after writes, a joined scanner process checks the scratch store, WAL, journal, API and signer state, logs and proof. Authority and API fd 1 and fd 2, child stdout and stderr, responses, events, observations and store command inputs contain no value. Lookup stdout must be exactly a candidate value or empty, since it is the runtime value channel.
- AC2, `credential/keystore-refusals`: Locked, unreachable and missing secret-tool cases refuse by name with no record or file fallback.
- AC2, `credential/authority-binding`: Stale versions, unauthorized actors, missing passkey/CSRF and a changed value under a signed binding are refused; role removal applies to a live session.
- AC1, AC2, `catalog/observability`: Session and command provenance, revision and credential identities, and operation/refusal counts agree with the driven changes.
- AC1, AC2, `install/assets`: Scaffold assets, the authority's derived module closure, API handlers and engine copies agree.

- AC1, `catalog/ordinary-config-saves`: All 20 ordinary probe values, the worktree and Mac paths and a Confluence REST URL save with every field compared exactly in the API and store. The probe's environment helper used API_TOKEN; these ordinary values use CONFIG to obey the position rule. Named references and an ordinary generated literal also save exactly. Runtime generated additions exercise author arguments, GIT_AUTHOR_NAME, OAUTH_CALLBACK_PORT, SORT_ORDER, credential file paths, every last-token exemption and a bare no-auth flag followed by a port flag. Pagination and encoding queries and both single-dash flag forms also save. There are 71 saves in this row.
- AC1, `catalog/credential-position-refused`: Generated hex values, including digest widths previously accepted, and short values refuse by name in environment entries, both stdio flag forms and HTTP queries. CamelCase privateKey and accessKey, dotted api.key, PASS, api-key flags and x-api-key literal headers are included. Userinfo and literal headers also refuse. Query sig, signature and code, the five additional credential tokens, a leading-hyphen credential argument and Bearer/Basic values across every string field are included. There are 167 cases, with credential values generated at runtime. No store command is called and no revision or journal entry is written.
- AC1, `catalog/known-shape-refused`: Generated known shapes refuse across string fields, including names and references. All eight existing PATTERNS entries are exercised outside credential positions.
- AC1, `catalog/refusal-no-value`: Generated values refused in credential positions and every known-shape field appear in neither catalog observations nor observations.jsonl. Both records retain the field name and reason; API and host-command refusals of a generated id omit its value.
- AC1, `catalog/deleted-reference`: A tombstoned credential cannot satisfy either an environment or header reference. Both refuse by name without storage.
- AC1, `catalog/credential-domain`: Another domain's reference and a non-Veldo name are refused without writes.
- AC2, `credential/libsecret-protocol`: Piped lookup preserves a real trailing newline, attribute pairs and subset matching work, and store requires a label. Independent full-attribute lookup catches an adapter omitting the application attribute.
- AC2, `credential/replay-value`: Identical command replay is idempotent; a changed value is refused without a keystore call or journal write.
- AC2, `credential/encoding`: A lone surrogate receives a named API refusal and observation without a write.
- AC2, `credential/deleted-state`: Deletion has a tombstone; subsequent SET and its retry report written and restore the five-field record.

## Interfaces and isolation

The fixture generates its own OpenSSH keys, TLS certificate and ES256 passkey.
Registration, possession, steward enrollment and sign-in run through production
interfaces. The protected API signer uses its normal joined subprocess. The
production HTTP handler serves loopback TLS, with serial request scheduling on
the SQLite connection's owning thread. `Service.apply`, `ServiceApi.call`, the
API authority and their store transitions run on that real authority connection.
This suite does not replace the authority's authorization or mutation logic.
The existing VELDO-0047 and VELDO-0130 suites cover installed service IPC.

Every keystore operation executes the generated scratch `secret-tool`. The
session bus address names a nonexistent socket in the scratch directory.
Only the fake keystore's item files are excluded from the file audit. The fixture
captures its process's fd 1 and fd 2 before constructing the authority and API,
and records child pipe outputs before the production callers consume them. It
also scans redirected Python stream buffers used by the proof driver. The
lookup value channel is checked for exact expected bytes, not treated as a log. The argv
observations remain in that audit. File inspection runs in a joined child because
closing a second database descriptor in SQLite's process releases its POSIX locks.
No real keyring, credential file, engine profile or non-loopback host is used.
The suite qualifies the process boundary and libsecret CLI protocol with a fake,
not a live desktop keyring or a deployed TLS terminator.

## Red record and mutations

`red-at-7df42187.json` retains the earlier suite run against unchanged production
files extracted with git archive from
`7df42187524b329a2241e056e125fa3043e19df5`, the original implementation base.
All 26 rows are red by assertion, with no exception-based red.
No other worktree or branch is created or modified. Reproduce with
`python3 proof/VELDO-0144/drive.py red 7df42187`.
`red-at-4baf622f.json` records this follow-up's starting commit; the new
credential-position assertions fail against it by assertion. Reproduce with the
same driver and positional arguments `red 4baf622f`.
`red-at-514915a1.json` records the preceding review round's starting commit.
Earlier red records are retained as historical evidence for their respective review rounds.

Finding 144 registers 37 uniquely named mutations in
`scripts/check_teeth_mutations.py`. `mutations.json` records the baseline, a
byte-identical copy control for each mutated module, every exact edit and source
digest, every row outcome and its failure detail. Both declared falsifiers are
included: `mcp144-overwrite-revision` really overwrites the earlier revision,
and `mcp144-value-on-argv` passes the generated value as an argument. Every mutant
fails on its named row by assertion. Reproduce the detailed record with
`python3 proof/VELDO-0144/drive.py`; the registry checker also rejects all 37 with
finding 144 and two jobs. Finding 130 also rejects all 100 mutations with two
jobs after its expanded command-map anchor is repaired. Names are unique across
the entire mutation registry. The old catalog/credential-literals row and
mcp144-catalog-literal-accepted mutation are replaced by catalog/known-shape-refused
and mcp144-known-shape-accepted. The new entropy-restored mutation requires the
ordinary configuration row to fail, and separate environment, argument and query
mutations require the position row to fail. The deleted-reference mutation
requires the tombstone row to fail. No row still asserts entropy refusal. Four further mutations replace token
matching with substring matching, drop the last-token exemption, consume a
following flag as a bare flag's value, and record a refused id's value. The first
three fail ordinary-config-saves and the last fails refusal-no-value. Two further
mutations drop query extras and the Bearer/Basic value rule; each fails
credential-position-refused by assertion.

## Checks and review boundary

The whole selftest ran once with no concurrent worktree writes: 6,886 passed,
0 failed, exit 0. Both selected selftest runs also have zero failed assertions.
The dispatcher deliberately returns status 2 for successful scoped runs. These
observations are not a gate stamp, an approval or a landing decision.

- `82_veldo_0144_mcp_catalog`: 26 rows passed.
- `71_veldo_0130_api`: 42 rows passed.
- `python3 scripts/selftest.py`: 6,886 rows passed, zero failed.

The requires registry was regenerated without a content change.
`python3 .veldo/validate.py all` passes. The Git boundary check reports no
violations, and template sync passes all 234 compared engine pairs.
`checks.json` retains check outcomes and implementation file digests. The canonical
gate was not run, as instructed. Specification status remains ready; independent
review and approval remain separate. No push was attempted.
