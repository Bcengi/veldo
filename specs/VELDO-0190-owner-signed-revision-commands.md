---
schema: veldo.spec/v1
id: VELDO-0190
title: The factory owner saves a capability configuration revision and the default team revision by an SSH-signed command, before any passkey or API session exists, through the existing revision writers, on setup's own store connection or through the running service, and anything not signed by the factory owner's key is refused by name
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W150
plan_revision: 4
depends_on: [VELDO-0025, VELDO-0139, VELDO-0162, VELDO-0171]
placement: [contracts, engine, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_owner_revisions.py"
  - ".veldo/control_owner_revisions.py"
  - "engine/.veldo/control_membership.py"
  - ".veldo/control_membership.py"
  - "engine/.veldo/control_service.py"
  - ".veldo/control_service.py"
  - "scripts/suites/*_veldo_0190_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0190-owner-signed-revision-commands.md"
  - "specs/index.md"
  - "proof/VELDO-0190/*"
behavior_bearing: true
observability:
  logs: >
    Record each owner revision command with its operation, command id, signer, outcome and refusal, and
    for a save the revision, role or team and digest the writer read back; never a key, a signature or a
    definition's settings.
  metrics: >
    Count owner revision commands by operation and outcome, and refusals by name.
  traces: >
    Join each owner revision command to the journal record the writer committed (its command id and
    nonce), and an online one to the service observation that carried it.
  error_taxonomy: >
    Distinguish a command whose envelope does not bind it to this store, its current versions, an unused
    nonce equal to its command id and an unexpired time (missing_authority:owner_command:envelope_refused),
    a signature that does not verify with the signer's active key
    (missing_authority:owner_command:signature_invalid), a signer who is not the factory owner
    (missing_authority:owner_command:not_factory_owner), an operation other than the two
    (invalid_input:owner_command:operation), a command id already committed with other signed content
    (stale_subject:owner_command:command_content_conflict), and a caller that does not hold the store's
    lock (missing_authority:not_the_authority, control_api_authority's name). A writer's own refusal is
    passed through unchanged.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The factory owner's SSH-signed command saves a capability configuration revision and a default
      team revision through the existing writers, with nothing else enrolled: no passkey credential, no API
      session and no api edge key. Set and completeness: A new module, control_owner_revisions, takes one
      packet, a command (command_id, operation, target `authority`, parameters) with its envelope and the
      owner's signature over the envelope, exactly the form control_membership's admit takes. It accepts
      only two operations with the API's names and parameter sets (control_api_assertion OPERATIONS):
      `save_capability_configuration` with `definition` and `base`, which it hands to
      control_agent_config's Configurations.save, and `save_default_team` with `team` and `base`, which it
      hands to control_team_routes' TeamRoutes.save_default, with the digest of the signed envelope as the
      assertion digest. The principal it passes is the envelope's verified signer, never a parameter; the
      command id it passes is the signed one. Each writer keeps its authorization, owner and roster checks,
      base and versioning, schema validation and read-back as they are, and the answer is the writer's
      read-back revision and digest; a writer's refusal is returned unchanged. The suite lays a store down
      with VELDO-0139's setup steps and the factory project record the default team writer requires, then
      saves one configuration revision per required role and one default team revision by the owner's
      signed commands on a connection holding the store's lock, reads them back through Configurations
      read and TeamRoutes read_default, and requires the journal records to name the owner as principal and
      the envelope's nonce. Writer rows send a stale base (stale_version:agent_configuration and
      stale_version:default_team), a team missing a required role (incomplete_roster:missing_staffing:<role>)
      and a definition holding a credential literal (invalid_input:agent_configuration), each signed
      correctly. Falsifier: Hand the writers the base the store's head names instead of the signed base, and
      the stale-base row must fail on a save accepted over a newer head.
    falsified_by: >
      Hand the writers the base the store's head names instead of the signed base, and the stale-base row
      must fail on a save accepted over a newer head.
  - id: AC2
    text: >
      Claim: The owner command is authenticated the one way control_membership authenticates an owner
      command, and anything not signed by the current factory owner's key is refused by name with nothing
      written. Set and completeness: The ordinary-path checks control_membership's admit runs today (the
      executed command id is the signed one, AC.envelope_problems against this store's ids, the current
      membership and delegation versions, the consumed nonces, the expiry and the signer's active
      membership and key, then the signature over the canonical envelope bytes against the signer's active
      key) move into one function, control_membership's authenticate, which admit and control_owner_revisions
      both call; admit's bootstrap path, policy and refusal names are unchanged, and VELDO-0025's membership
      rows stay green. control_owner_revisions then requires the signer to be the factory owner: the current
      person member whose own enrollment is the store's owner bootstrap (enrolled_by is itself) and who
      holds project_owner and membership_steward. Rows, each against a store with a saved head, each
      requiring the named refusal, an unchanged journal head and a refused observation with that refusal and
      its class: no signature; the owner named as signer but signed by another enrolled member's key; signed
      by the owner's key after it was revoked; signed by an enrolled person who is not the factory owner,
      with that person's own active key (not_factory_owner); a parameter (the base, the team or the
      definition) changed after signing; an envelope naming an earlier membership version, another store's
      ids or an expired time; and an administrative operation or any other operation sent here
      (invalid_input:owner_command:operation), while admit still refuses both revision operations as
      policy_refused. Falsifier: Verify the signature against any active key in the keyring instead of the
      signer's own, and the other-key row must fail on an accepted save.
    falsified_by: >
      Verify the signature against any active key in the keyring instead of the signer's own, and the
      other-key row must fail on an accepted save.
  - id: AC3
    text: >
      Claim: A signed owner command is executed at most once, and its identity is the signed content. Set and
      completeness: The envelope's nonce must equal its command id, so the nonce the owner signed is the one
      the writer's commit consumes (both writers commit with the command id as nonce) in the same
      transaction as the revision. Before authenticating, a command id already in the store's commands is
      judged as admit judges a retry: when the committed record names the same signer and nonce and the
      envelope's digest is the digest of the command presented, the answer is the committed revision with
      replayed true and nothing is written; otherwise it is refused
      (stale_subject:owner_command:command_content_conflict). The suite sends a saved command again, sends
      the same command id signed over another definition, and sends a new command id whose envelope reuses a
      consumed nonce; the first answers replayed with the journal head unchanged, the other two are refused
      by name with nothing written. Falsifier: Answer a committed command id from the store without comparing
      its signed digest, and the content-conflict row must fail on a differently signed command answered as
      replayed.
    falsified_by: >
      Answer a committed command id from the store without comparing its signed digest, and the
      content-conflict row must fail on a differently signed command answered as replayed.
  - id: AC4
    text: >
      Claim: The command obeys VELDO-0171's lock rule: it is executed only by the holder of the store's lock,
      on setup's own connection when no service runs and by the running service when it does. Set and
      completeness: control_owner_revisions takes the caller's lock descriptor and refuses first, writing
      nothing, unless control_api_authority's authority_problem finds it holds authority.lock beside the
      store its connection opened (missing_authority:not_the_authority). Offline, setup holds the lock it
      took (control_factory_setup take_lock) and calls the module on its own connection with writers built
      on it. Online, setup sends the same packet, command, envelope and signature, to the running service
      over its socket, as it sends the api edge enrollment (control_client send); control_service's apply
      routes the two operations carrying an envelope to the module, before its mutate fallback, with the
      service's lock and its API authority's Configurations and TeamRoutes, and without an API authority
      refuses unavailable_service:api:not_configured as its other API-backed commands do. The service's
      observation of the command names its operation, command id, signer, outcome, refusal and class, as
      every other packet's does. Rows: the offline saves of AC1; the same command called on a second
      connection while the service holds the lock, refused not_the_authority with the journal head
      unchanged; and a running service fixture that commits the saves sent over its socket, where the
      journal shows the service committed them and setup opened no store connection for writing, and a
      forged command sent the same way appears refused in the service's observations. Falsifier: Leave the
      two operations to the mutate fallback, and the running-service row must fail on
      invalid_input:operation.
    falsified_by: >
      Leave the two operations to the mutate fallback, and the running-service row must fail on
      invalid_input:operation.
required_evidence: [unit, integration]
rollback: >
  Remove control_owner_revisions and its service route and restore admit's inline checks; the API edge
  remains the writers' only route. Revisions already saved stay as accepted records, superseded by the
  owner's next revision. No automatic rollback is authorized.
---

## Intent

The owner, setting up a factory on a fresh host with nothing but an SSH key, can have setup save the
starting team's capability configurations and the default team in the owner's name, through the same
writers the role form uses, so the factory is configured before the first login.

## Context

W150 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5, ahead of W145.
VELDO-0185 AC1 is blocked twice (proof/VELDO-0185/README.md, 2026-10-04): VELDO-0162 landed the writers,
control_agent_config's Configurations.save and control_team_routes' TeamRoutes.save_default with
read_default, but their only authenticated production route is control_api_authority's ApiAuthority
_apply, which needs the api edge's signature and an enrolled passkey credential. Fresh setup has the
owner's SSH key and neither. Setup's owner-signed paths refuse both operations: control_membership's admit
takes only ADMIN_OPERATIONS (policy_refused), and control_service's apply falls back to mutate, which
takes only the store's generic commands (invalid_input:operation). This specification adds the missing
entry point and nothing else; VELDO-0185 AC1 consumes it. The writers trust the principal they are given;
the API edge authenticates it with a passkey, and this path authenticates it with the owner's signed
command. Owner commands are already authenticated the same way in three places (control_membership,
control_channel_enrollment, control_api_credentials); this one reuses control_membership's checks as one
function rather than copying them a fourth time.

## Out of scope

Setup's own steps that send these commands, and the factory project record save_default requires
(VELDO-0185); any operation other than the two, a skill revision (the writer's `agent_skill` kind) and a
team proposal among them; rate limits, key rotation and signing by any key but the owner's; moving
control_channel_enrollment and control_api_credentials onto the shared function.

## What the reviewer judges

- Normal use: on a fresh host, setup signs one save per role and one default team save with the owner's
  key and has them committed on its own store connection; on a host whose service runs, it sends the same
  signed commands to the service, which commits them; either way the revisions read back as the role form
  would have saved them, and sending them again changes nothing.
- Threat model: a revision saved in the owner's name without the owner's key, by another member's key, by
  the owner's revoked key, or by a member who is not the factory owner; a signed command whose parameters
  were changed after signing; a command executed twice, or a replay answered with another command's
  result; a second writer that skips the writers' owner, roster, base or schema checks; a store written by
  a process that does not hold its lock; an administrative operation smuggled through this path, or these
  operations through admit; a refusal that leaves no observation.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962), such as a
  revocation committed by another process between the check and the commit (the lock leaves one writer);
  forged rows in our own store.

## Notes

Using the API's operation names and parameter sets keeps one vocabulary for the two saves, so the role
form and setup produce revisions no reader can tell apart except by the assertion digest, which names the
signed envelope here and the API assertion there. The factory owner is read from the store, not from
setup's arguments, so a later owner command from any host is judged by the same rule.

## History

2026-10-04: new specification for the VELDO-0185 AC1 blocker recorded on build-veldo-0185b at a4dbfd8d,
written and marked ready at the owner's request; VELDO-0185 now depends on it.
