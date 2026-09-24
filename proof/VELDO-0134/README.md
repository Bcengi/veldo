# VELDO-0134 proof

The architecture record's one writer, its schema, and the reader held to it. PLAN-0019 revision 3, W97.
Branch `build-veldo-0134`, merged with main at 8dcdd34 (main had not moved at the last fetch).

## What landed

**The only writer.** `.veldo/control_store.py` refuses `entity_owned` for any operation other than
`accept_architecture` that names an `architecture:` id as the row it writes, or whose transition would
change an entity with that prefix or of kind `architecture_contract`. The rule is in `execute`, so it
binds every operation registered now or later, on every connection.

**The accept command.** `.veldo/control_architecture.py` (new, in the scaffold) holds the schema
`veldo.architecture_record/v1` (`record_problems`) and `ArchitectureAuthority.apply`: the canonical
command bytes verified against the signer's active key, an active person holding `project_owner` whose
scope covers the repository, the blob at the named commit read from the bound repository through
`_git_process`, its raw SHA-256 compared with the stated digest, the installed validator's verdict over
those bytes in a private root, and one store transaction that pins the principal, key, membership
versions entity and record versions and consumes the nonce. A replacement names the version it
replaces and moves the previous entry to the end of `superseded`. The owner's front door is the
module's own CLI (`python3 .veldo/control_architecture.py accept --commit ...`), which prints the signed
packet.

**The reader.** VELDO-0053's Gate accepts exactly the schema-valid records and refuses every other as
`missing_authority:architecture`. Suite 60_veldo_0053 now writes its records through the store's
architecture operation on its own connection, as complete schema records.

## Rows, red record, mutations

Suite `scripts/suites/68_veldo_0134_acceptance.py`, 27 rows: 16 criterion rows and 11 `ran/` rows, in
about 2 s (1.94 s in the gate's stage environment).

- AC1: `first` (through the front door), `signers` (every PRINCIPAL_TYPES and ROLES entry, no role,
  scopes), `signature`, `evidence`, `contract-kinds` (every refused CONTRACT_KINDS entry),
  `replay-and-coordinates`.
- AC2: `schema-oracle` (every field and named invalid form of the Notes table, read from the
  specification), `writer-schema`, `raw-digest-crlf`, `raw-digest-no-final-newline`, `raw-digest-bom`
  (each digest from `sha256sum` over the blob Git returns, and the Gate's round trip).
- AC3: `version-history`, `replacement-refusals`, `previous-bytes`.
- AC4: `generic-write` (every registered operation at run time, including one registered by the suite),
  `worker-inputs` (policy, contract, validator stub, every VELDO_ and GIT_ variable named plus HOME,
  agent_run and service signers).

`red-8dcdd34.json` (`python3 -B proof/VELDO-0134/red.py 8dcdd34`): all 16 criterion rows red by
assertion over the pre-change engine, every `ran/` row green, nothing raised.

`mutations.json`: 36 registered mutations of finding 134, each redding its named row by assertion
against a green unmutated baseline of 53 assertions, diffs in `mutations/`. Declared falsifiers:
`architecture-agent-run-signs` (AC1), `architecture-digest-normalizes-line-endings` (AC2),
`architecture-replacement-in-place` (AC3), `architecture-generic-upsert-writes` (AC4). Finding 53: all
52 green after re-anchoring `architecture-unaccepted-record-accepted` to the schema check.

`observations.json` (`python3 -B proof/VELDO-0134/drive.py`): what each region observed.
