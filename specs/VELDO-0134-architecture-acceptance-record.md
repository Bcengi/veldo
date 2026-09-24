---
schema: veldo.spec/v1
id: VELDO-0134
title: Accept a repository's architecture contract by a signed owner command
status: ready
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W97
plan_revision: 3
depends_on: [VELDO-0053]
placement: [contracts, distribution, fleet]
protected_paths: []
footprint:
  - "plans/PLAN-0019-dark-factory.md"
  - "engine/.veldo/control_architecture*.py"
  - ".veldo/control_architecture*.py"
  - "packs/*/.veldo/control_architecture*.py"
  - "engine/.veldo/control_store.py"
  - ".veldo/control_store.py"
  - "packs/*/.veldo/control_store.py"
  - "engine/.veldo/control_eligibility*.py"
  - ".veldo/control_eligibility*.py"
  - "packs/*/.veldo/control_eligibility*.py"
  - "bin/veldo"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0134_*.py"
  - "scripts/suites/*_veldo_0053_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0134-architecture-acceptance-record.md"
  - "specs/index.md"
  - "proof/VELDO-0134/*"
behavior_bearing: true
observability:
  logs: >
    Record the operation (accept or replace), domain, repository, the signing principal, the
    commit and path the bytes were read from, the accepted digest, the contract version before and
    after, the accepted input versions, the outcome and any named refusal. Never log the contract
    bytes, a signature or key material.
  metrics: >
    Count accepted and refused acceptance commands by refusal, count refused writes of an
    architecture record by any other operation, and expose the current accepted contract version
    and digest per repository.
  traces: >
    Join the signed acceptance command, its journal record, the architecture record version it
    wrote, the superseded entry it recorded, and the VELDO-0053 eligibility decisions that read that
    record version, by identity.
  error_taxonomy: >
    Distinguish invalid input, not authorized, stale subject, invalid contract, missing evidence,
    refused writer and unavailable service; a refused or unknown acceptance is never reported as
    accepted, and a record that does not match the schema is never read as an acceptance.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The record architecture:<repository> is created only by an accept command signed by
      an active person member holding project_owner whose scope covers the repository, verified
      against that person's active key in the store's committed keyring and committed through the
      store's registered command path, and it names the digest of the exact bytes of
      .veldo/architecture.yaml at the commit the command names, read from the repository's object
      store and judged valid by the installed structural validator. Once written, VELDO-0053's Gate
      reports basis accepted and the contract required whatever the workspace's policy says. Set
      and completeness: One valid first acceptance, and against it every refused form: a signature
      that does not verify, a revoked key, a signer that is an active agent_run, service or policy
      member, a person without project_owner, a person whose scope does not cover the repository, a
      stated digest that differs from the bytes at the commit, a commit that does not exist or
      carries no contract, bytes the installed validator refuses (one row per refused contract kind
      of contract_loader), a consumed nonce, and coordinates naming another domain or repository.
      The signer rows are derived from authority_contract.PRINCIPAL_TYPES and the roles from
      authority_contract.ROLES, so a principal type or role added later with no row fails the
      check. Drive real signed commands through the authority's command path on the real configured
      store; each refused form carries its named refusal and leaves the record, the journal and the
      nonces unchanged; after the valid one, drive the Gate over a workspace whose policy.yaml says
      architecture_contract: optional and require the required-absence refusal for a missing
      contract. Falsifier: Accept the command from an active agent_run member whose scope covers
      the repository; the non-person signer row must fail.
    falsified_by: >
      Accept the command from an active agent_run member whose scope covers the repository; the
      non-person signer row must fail.
  - id: AC2
    text: >
      Claim: The record's format is the schema written in this specification's Notes, and both the
      writer (the accept command) and the reader (VELDO-0053's Gate) are checked against that
      schema and against an outside digest implementation, never against each other. The writer
      produces only schema-valid records whose digest equals the outside implementation's digest
      of the raw bytes; the reader treats exactly the schema-valid records as an acceptance and
      refuses every other one as missing_authority:architecture. Set and completeness: The oracle
      rows are the schema's fields, each with its valid form and each named invalid form listed
      beside it in the schema (missing, wrong type, unknown extra field, digest without the sha256:
      prefix, with another prefix, in uppercase hex, of the wrong length, entity kind other than
      architecture_contract, repository_uuid not matching the entity id, state other than
      accepted, contract_version zero or a boolean, a superseded list out of order), written into
      the store for the reader through a suite-registered operation on the suite's own connection;
      a check fails when a schema field has no row. The contract bytes include a file with CRLF
      line endings, one with no final newline and one with a byte order mark, and each expected
      digest is computed by the operating system's sha256sum (or shasum -a 256 on the Mac) over
      the blob Git returns. The round trip requires the Gate to accept every record the writer
      wrote, over a workspace holding those exact bytes. Falsifier: Have the writer hash the
      contract after normalizing line endings instead of the raw bytes; the CRLF raw-digest row
      must fail.
    falsified_by: >
      Have the writer hash the contract after normalizing line endings instead of the raw bytes;
      the CRLF raw-digest row must fail.
  - id: AC3
    text: >
      Claim: Replacing an accepted contract is a new accepted version: an accept command that names
      the current contract_version as the one it replaces writes contract_version plus one, moves
      the previous version's entry, byte for byte, to the end of superseded, and changes nothing
      else of the prior entries; no command edits an accepted version in place. Set and
      completeness: Drive a first acceptance, a replacement and a second replacement, and against
      each current version the refused forms: naming a replaced version that is not current
      (stale_subject), naming none when a record exists (stale_subject), accepting the digest that
      is already current (invalid_input), and a retry of an accepted command with changed content
      (the store's content conflict). After each step read the record and the journal back from
      the store and require every earlier superseded entry unchanged, one journal record per
      accepted version, and the Gate refusing the previous bytes as
      missing_authority:architecture/unaccepted_artifact while accepting the current bytes.
      Falsifier: Write a replacement over the current entry in place, keeping its contract_version
      and recording no superseded entry; the version-history row must fail.
    falsified_by: >
      Write a replacement over the current entry in place, keeping its contract_version and
      recording no superseded entry; the version-history row must fail.
  - id: AC4
    text: >
      Claim: No input a worker controls creates, changes or removes the architecture record: the
      accept command is the only operation that writes it, every other registered store operation
      naming it is refused, and nothing in a workspace or a process environment is read by the
      writer. Set and completeness: The worker-controlled inputs are enumerated, not sampled: the
      workspace's .veldo/policy.yaml (optional, absent, unreadable), the workspace's
      .veldo/architecture.yaml (edited, deleted, replaced by a symlink), a validator copy in the
      workspace replaced by a success stub, every environment variable with the VELDO_ or GIT_
      prefix plus HOME, and a command signed by an enrolled agent_run or service. The store
      operations are every entry of the store's registered command set at run time (the generic
      upsert_entity and retire_entity among them) driven against the record's identity and against
      a new identity of kind architecture_contract, so an operation registered later with no row
      fails the check. With each input changed, drive the accept path and the Gate and require the
      record's entity version and digest, the journal and the Gate's basis unchanged, and each
      store write refused by name. Falsifier: Let the generic upsert_entity operation write
      architecture:<repository>; the generic-write row must fail.
    falsified_by: >
      Let the generic upsert_entity operation write architecture:<repository>; the generic-write
      row must fail.
required_evidence: [unit, integration]
rollback: >
  Disable the accept command and preserve every accepted record, superseded entry and journal
  record. The Gate keeps reading any record already accepted; returning a repository to
  policy-decided architecture requires an explicit operations decision.
---

## Intent

Whether a repository's architecture contract is required, and which bytes are the accepted ones,
is decided by the owner through a signed command the authority records, never by a file a
worker can edit. VELDO-0053 built the reader of that decision; this item builds its only writer
and fixes the format both must follow.

## Context

W97 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 1. The
[design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated 2026-09-22
scope amendments. R50 requires enforcement to run outside worker control, and says PLAN-0019's
required contracts cannot stand down through absence. R38 names baseline acceptance among the
decisions that need the applicable principal's signature.

VELDO-0053 makes every floor entry refuse when the architecture contract is malformed, missing
when required, or not the accepted bytes. It reads a store record, `architecture:<repository>`,
with state `accepted` and a `sha256:` digest of the accepted bytes, and that record makes the
contract required whatever the clone's policy says. Nothing writes that record. Until something
does, whether the contract is required comes from the workspace's own `.veldo/policy.yaml`, which
a worker can edit, so R50 is not met. The record's format is also defined only by its reader:
today the reader checks the state and the digest prefix and nothing else, and VELDO-0053's own
suite seeds the record through the generic `upsert_entity` operation, so any holder of the
authority's journal signer could write it.

## Out of scope

Hardening is Release 2 and is not part of these criteria or their evidence: no recovery of a
lost acknowledgement, no concurrent acceptance matrix beyond the store's ordinary expected-version
refusal, and no clock qualification. Withdrawing an accepted contract (returning a repository to
policy-decided architecture) is not offered; if the owner wants it, it is a new item. No
`architecture.yaml` amendment is made or authorized here. Membership, keys and delegation
(VELDO-0025, VELDO-0027), the authority service (VELDO-0047) and VELDO-0053's refusal names are
consumed, not changed. Acceptance through Telegram or the factory API is not added here; the
authenticated API may later carry the same signed packet unchanged.

## What the reviewer judges

- Normal use: the owner, an active person member holding project_owner whose scope covers the
  repository, signs an accept command naming a commit. The authority verifies the signature against
  that person's active key in the store's committed keyring, reads `.veldo/architecture.yaml` at that
  commit from the object store, requires the installed structural validator to accept it and the
  stated digest to equal the SHA-256 of its raw bytes, and records `architecture:<repository>` in the
  schema in Notes through the store's registered command path. From then on VELDO-0053's Gate treats
  the contract as required whatever the workspace's policy says. A later acceptance replaces it with
  the next contract_version. The reader accepts exactly the schema-valid records.
- Threat model: a worker editing `.veldo/policy.yaml` to make the contract optional; a signer who is
  not an active person with project_owner covering the repository (an agent_run, service or policy
  member, a revoked key, a scope that does not cover it); a digest that does not match the bytes at the
  commit; a missing commit or contract; bytes the validator refuses; a replayed nonce; coordinates
  naming another domain or repository; a record in any shape other than the schema, including one
  written through the generic upsert operation. The owner's account, the store and the installed
  validator are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); recovery of a
  lost acknowledgement, concurrent acceptance beyond the store's expected-version refusal and clock
  qualification (Release 2); withdrawing an accepted contract; acceptance through Telegram or the API;
  rows written into our own store file directly, outside every command path; files planted in the
  installed directory.

## Notes

The record schema, `veldo.architecture_record/v1`. The store entity id is
`architecture:<repository_uuid>` and its entity kind is exactly `architecture_contract`. Its data
is a closed mapping (an unknown field makes the record invalid) with these fields:

| Field | Valid form | Named invalid forms |
|---|---|---|
| `schema` | the string `veldo.architecture_record/v1` | missing, another string, not a string |
| `repository_uuid` | the repository identity, equal to the entity id after `architecture:` | missing, not matching the id, not a string |
| `state` | the string `accepted` (the only state in Release 1) | missing, any other value |
| `contract_version` | an integer of at least 1, 1 for the first acceptance, one more for each replacement | missing, zero, negative, a boolean, not an integer |
| `digest` | `sha256:` followed by 64 lowercase hexadecimal characters: SHA-256 over the raw bytes of the contract blob, with no decoding, no line-ending or byte-order-mark normalization and no trimming | missing, no prefix, another prefix, uppercase hex, wrong length, not a string |
| `source` | a mapping of `commit` (the full lowercase object id of the commit the bytes were read from) and `path` (exactly `.veldo/architecture.yaml`) | missing, an abbreviated or uppercase commit, another path, an extra key |
| `accepted_by` | the principal identity of the signing person | missing, not a string |
| `command_id` | the identity of the signed accept command that wrote this version | missing, not a string |
| `superseded` | a list, empty at version 1, of the prior versions' entries in ascending `contract_version` from 1, each exactly the `contract_version`, `digest`, `source`, `accepted_by` and `command_id` that version carried | missing, out of order, a gap, an entry with a changed or extra field |

The reader and the writer are held to this table, not to each other. The suite encodes the table
as its oracle rows by reading it from this section, so a field added here with no suite row fails,
and every expected digest comes from an implementation outside Veldo (coreutils `sha256sum`, or
`shasum -a 256` on the Mac) over the blob `git cat-file` returns. VELDO-0053's reader is brought to
the schema: a record that fails any row is refused as `missing_authority:architecture`, as a record
in the wrong state is today, and its existing refusal names are unchanged.

The accept command. The owner runs `veldo architecture accept`, naming the commit, from his own
machine; the front door computes the digest of the contract blob at that commit, builds the
command and signs it with his personal key through `ssh-keygen -Y sign`. The signed command
carries the operation, principal, command identity, nonce, the domain, repository and store
coordinates, the commit, the digest, and `replaces`: the contract version it replaces, 0 when
none has been accepted. It reaches the authority through the ordinary command path and is admitted
exactly as the inbox's signed commands are (VELDO-0064's `Inbox.apply`): the canonical command
bytes are verified against the signer's active key in the store's committed keyring; the stored
membership must show an active `person` member holding `project_owner` whose scope covers the
repository; and one registered store transaction commits the record together with the versions
of every authority input it read (the principal, the key, the membership versions entity and the
record itself) and consumes the nonce. The authority reads the blob from the repository's object
store at that commit through `git_process` (which strips every inherited `GIT_` variable by
prefix and ignores system and global configuration), recomputes the digest and refuses a
mismatch, and runs the installed structural validator beside it over those bytes, never a
workspace copy, refusing a contract it rejects under that validator's kind. Only `project_owner`
is admitted because it is the role the owner holds today through the bootstrap enrollment;
admitting `technical_authority` as well is a membership-policy decision for the owner, not made
here.

The only writer. The store refuses, as `transition_refused`, any registered operation other than
the accept operation that would write an entity whose id begins with `architecture:` or whose kind
is `architecture_contract`, including the generic `upsert_entity` and `retire_entity`. The refusal
is in the store's command path, so it binds every operation registered now or later, not a list
of the ones known today. VELDO-0053's suite, which seeds the record with `upsert_entity`, is moved
to the accept command (or, for schema-invalid rows, a suite-registered operation on its own
connection) and its rows and finding-53 mutations stay green.

Implement canonical engine assets with synchronized installed copies. Derive executable check
registrations from each criterion's declared set; retain the actual observations and each driven
negative-control diff and failing row, registered as finding 134 of the teeth mutation driver.
Real stores, signatures, Git objects and the installed validator are required where named.

## History

2026-09-23: new draft for PLAN-0019 revision 3, Release 1 stage 1. It closes the gap VELDO-0053
left: the record that makes the architecture contract required had a reader and no writer, so
whether the contract was required still came from a file a worker can edit. The simple function
is in this release; recovery, concurrency and clocks are Release 2.
2026-09-23: plans/PLAN-0019-dark-factory.md joined the footprint because this specification's own writing
change adds its work item (W97) to the plan, and the shape gate holds a change that names one
specification to that specification's footprint.

2026-09-24: the owner marked this specification ready (Telegram 29041).

2026-09-24, build: .veldo/init_scaffold.py and its engine and pack copies joined the footprint, because the
new module .veldo/control_architecture.py is installed by the scaffold like every runtime asset.

2026-09-24, build: landed on build-veldo-0134. The store refuses a write of the record by any other
operation as entity_owned, the store's existing name for a command writing an entity it does not own,
where the Notes say transition_refused; the refusal is by name either way and the criteria name none.
VELDO-0053's suite writes its records through the store's architecture operation with its own
transition on its own connection, not through the signed accept command, because most of its records
name the digest of bytes the validator refuses, which the accept command cannot write; this suite
drives the real command. The front door is control_architecture.py's own command line; routing it
through bin/veldo would also change engine/bin/veldo, which is outside this footprint, and is left for
the owner to decide. Evidence: proof/VELDO-0134/.
