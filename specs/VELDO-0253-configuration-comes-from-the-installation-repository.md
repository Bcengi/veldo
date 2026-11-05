---
schema: veldo.spec/v1
id: VELDO-0253
title: Veldo loads an installation's configuration from the installation's own repository, keeps the last good configuration when a change is bad, and a workflow saved on the canvas is committed there
status: ready
risk: critical
owner: owner
human_approval: required
lane: standalone
depends_on: [VELDO-0068, VELDO-0132, VELDO-0171, VELDO-0241, VELDO-0259]
placement: [contracts, engine, distribution]
protected_paths:
  - ".veldo/installation.py"
  - "engine/.veldo/installation.py"
  - ".veldo/control_installation_config.py"
  - "engine/.veldo/control_installation_config.py"
  - ".veldo/control_installation_commit.py"
  - "engine/.veldo/control_installation_commit.py"
  - "engine/.veldo/installation_schema/**"
  - ".veldo/installation_schema/**"
  - "engine/.veldo/control_workflow.py"
  - ".veldo/control_workflow.py"
footprint:
  - ".veldo/installation.py"
  - "engine/.veldo/installation.py"
  - ".veldo/control_installation*.py"
  - "engine/.veldo/control_installation*.py"
  - "packs/*/.veldo/control_installation*.py"
  - "engine/.veldo/installation_schema/**"
  - ".veldo/installation_schema/**"
  - "engine/.veldo/installation_template/**"
  - ".veldo/installation_template/**"
  - "engine/.veldo/control_workflow*.py"
  - ".veldo/control_workflow*.py"
  - "packs/*/.veldo/control_workflow*.py"
  - "engine/.veldo/control_project.py"
  - ".veldo/control_project.py"
  - "engine/.veldo/control_service.py"
  - ".veldo/control_service.py"
  - "engine/.veldo/control_factory_setup*.py"
  - ".veldo/control_factory_setup*.py"
  - "engine/.veldo/control_client_api*.py"
  - ".veldo/control_client_api*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "engine/ui/src/api/workflows.ts"
  - "engine/ui/src/features/workflow/**"
  - "docs/installation.md"
  - "scripts/suites/*_veldo_0253_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0253-configuration-comes-from-the-installation-repository.md"
  - "specs/index.md"
  - "proof/VELDO-0253/**"
behavior_bearing: true
observability:
  logs: >
    The loader prints one line per load attempt: the installation folder, the commit id it read, the
    commit it replaced, the outcome (accepted, refused, waiting for approval) and, for a refusal, every
    problem as file path, key and reason. A widening change prints each widening it found by kind and
    key. A canvas save prints workflow, base version, resulting commit id, author and the API command id.
    No secret value is ever read into or printed by the loader; a secret appears only as its name.
  metrics: >
    Count load attempts by outcome, refusals by reason name, widening changes waiting for approval and
    their age, canvas saves accepted and refused by reason, and the age of the live configuration (time
    since the accepted commit became live).
  traces: >
    Every run, approval request and dispatch carries the accepted configuration commit id that was live
    when it started; every unit carries its pinned workflow {id, version, digest}; each accepted
    configuration record joins its commit id to the owner decision that approved it, when one was needed.
  error_taxonomy: >
    installation_invalid:<path>:<key>:<reason> for a value that fails its declared schema or a cross
    reference; installation_unknown_file:<path> for a file no declared pattern matches;
    installation_secret_inline:<path>:<key> for a literal secret value; installation_secret_missing:<name>
    for a secret name the keystore does not hold; installation_waiting_approval:<commit> for a widening
    change with no owner decision yet; installation_unreadable:<reason> for a folder that is not a
    repository or a commit that cannot be read; installation_push_failed:<reason> for a commit Veldo
    made that its declared remote did not accept (the commit stays live locally). A canvas save keeps VELDO-0132 and VELDO-0241 names
    (stale_version, invalid_input:missing_owner_approval:<node>) and adds installation_invalid for a
    tree the new file would make invalid. None of these is a success, and none changes the live
    configuration.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: an installation's configuration is one declared schema over the installation repository, read
      from a commit, applied whole or not at all, and a bad change leaves the last good configuration live.
      Set: the schema (installation_schema, veldo.installation/v1) is the one layout of an installation
      repository. Every other spec that needs installation configuration adds its kind here and defines no
      layout of its own. The schema declares every path pattern the folder may hold and the closed schema
      of each kind:
      installation.yaml (owner display name and owner role id, approver key ids, git identities, the
      repository's git remote, hosts and tailnet names, ports, the messaging bot and its channels with the
      inbound file cap, model accounts with their labels and binary paths, tracker sites and account ids,
      the publisher identity, and receiver settings such as the question window);
      projects/<id>.yaml (a project's account, landing destination, remote and trunk, workflow bindings,
      and its work keys: render command, deploy targets, spend checklist items, renumber hook);
      roles/<id>.yaml and teams/<id>.yaml (roles with their capability grants, and teams);
      services/<name>.yaml, with its optional OpenAPI file and pinned tools snapshot beside it (the outside
      services of VELDO-0251 AC4, schema veldo.outside_service/v1, with their credentials by reference,
      per-service body limit, read overrides, never rules and the OAuth grant declarations of VELDO-0252
      AC2);
      connectors/<name>.yaml (local tool servers that hold no credential and reach nothing outside, with
      their allowed tools and never rules);
      workflows/<id>.json and workflows/<id>.layout.json (workflow definitions and their layouts);
      memory/ (the memory manifest: stores, their servers and the session history sink; a memory server
      that carries a credential is served behind the outside gate as a service under services/);
      schedules/<id>.yaml (schedules the installation declares);
      patterns/ (the personal-setup patterns of VELDO-0259, read only by that check);
      decisions/ (the map from a decision reference to its source message and quote);
      records/ (history records, VELDO-0250 AC2, kept with a digest list and never read as
      configuration);
      research/ and notes/ (declared ignored).
      A file with the same id as a product default (a workflow, a connector) overrides the product's own
      for that installation. The schema declares no kind for runs, approvals, conversations, schedule
      occurrences or account pauses. A secret is a reference by name ({secret: <name>}) resolved from the
      keystore at use time; a literal secret-shaped value is refused. Setup on a new installation creates
      the installation repository from the template the product ships (installation_template) at the path
      VELDO-0259 resolves unless it is given one, and records that path as VELDO_INSTALLATION in the
      service's environment: a private Git repository with the declared layout, the values setup was given,
      the git remote it was given and one first commit. Veldo pushes each commit it makes (the first
      commit, an import commit, a canvas save) to the declared remote once the loader has accepted it,
      never with force; a push the remote refuses is told to the owner by name
      (installation_push_failed). Setup over a factory that already holds configuration (state root
      values, host service and receiver configuration, the team repository, store revisions of roles,
      teams and workflows) writes one import commit holding every declared kind from the values live
      today and records it as accepted with no widening decision, because each value was already live.
      Loading: at start the service reads the
      commit the configured branch names (the committed tree, never uncommitted working files), and then
      subscribes to changes of that branch reference through the operating system's file change
      notification, reconciling by commit id at start and after any missed notification (no timed
      polling). Each new commit is validated as a whole tree: every file against its kind, every cross
      reference (a project's account, a connector's tools, a workflow's roles and tools, a secret name the
      keystore holds), and every workflow through control_workflow's definition and approval checks. Any
      problem refuses the whole commit with each problem named by file and key, keeps the previous
      accepted commit live, and tells the owner through the channel.
    falsified_by: >
      Let the loader apply files one at a time; a commit that adds one valid project and one connector
      file with an unknown key must fail row ac1/whole-commit because the new project is live while the
      commit was refused.
  - id: AC2
    text: >
      Claim: every live configuration is attributable to a commit, and a change that widens authority is
      live only after the owner's approval of that exact commit. Set: each accepted commit is recorded in
      the store (commit id, tree digest, previous accepted commit, author and committer as Git reports them,
      and the classification of the change). The schema marks which fields widen authority; the
      classifier compares the new tree with the last accepted one and lists every widening: a new project,
      account, port or channel chat; a tool added to a connector's allowed list; a never rule removed or
      relaxed; an approver added; a workflow binding changed; a workflow that gains an outward or paid step
      or references a new role or tool; a capability granted to a role or a role added to a team; a new or
      changed schedule; a new outside service, a changed upstream base URL, a new route template, a
      credential reference or location change, a read override, a new pinned tools snapshot, or changed
      grant scopes or endpoints; a new or changed deploy target, render command or renumber hook. A commit with no widening goes live when valid. A commit with any
      widening waits (installation_waiting_approval) while the last good configuration stays live, and
      opens one owner decision that names the commit id, the digest of the widening list and each
      widening in plain words; it goes live only when that decision settles approved through the ordinary
      signed path (VELDO-0068), bound to exactly that commit and digest. A Git author name is recorded
      but grants nothing. A later commit that supersedes a waiting one closes the old decision as stale.
    falsified_by: >
      Classify a tool added to a connector's allowed list as not widening; row ac2/widening-waits must fail
      because that tool is callable before any owner decision names the commit.
  - id: AC3
    text: >
      Claim: a workflow saved on the canvas is committed to the installation repository, and the
      repository is the one source of truth for definitions. Set: workflows.save (VELDO-0132, VELDO-0246)
      no longer writes a revision entity. It writes the definition and its layout as two files under the
      workflow's declared path into a new commit on the configured branch, built with Git's object
      commands against the expected parent (the accepted commit the canvas edited from) and published by
      a compare and swap of the branch reference, so a concurrent change is refused stale_version and
      nothing is overwritten. The commit's author is the saving principal's Git identity from the
      installation, its message names the workflow, base and new version and the API command id. The save
      runs the same whole-tree validation as AC1 before the commit is written, and answers only after the
      loader accepted the commit, or reports it waiting for approval (AC2). When the owner saves, the
      owner's signed save command names the commit and settles its approval; another editor's widening
      save waits. A definition changed by a commit outside the canvas appears on the canvas as the next
      version after the loader accepts it. No other writer of definitions exists.
    falsified_by: >
      Let workflows.save write the store revision directly and skip the commit; row ac3/one-source must
      fail because the store's head version names no commit in the installation repository.
  - id: AC4
    text: >
      Claim: the revision a run used stays readable exactly, whatever later happens to the file. Set: when
      the loader accepts a commit that changes a workflow definition, it writes a content addressed copy of
      the canonical definition into the store, keyed by its definition digest and written once, with the
      source commit, path and blob id beside it, and assigns the next version. A unit pins {id, version,
      digest} at its first station as VELDO-0241 says, and every later station and the run view on the
      canvas read the copy by digest, never the file or the branch. Editing, renaming or deleting the file,
      reverting the commit, or rewriting the branch so the commit is unreachable leaves a running unit on
      its pinned bytes and keeps a finished run's canvas drawing the revision it ran.
    falsified_by: >
      Read a pinned revision from the repository at its recorded commit instead of the store copy; row
      ac4/pinned-survives must fail after the branch is rewritten so that commit is gone.
required_evidence: [unit, integration]
rollback: >
  Revert the change. The service reads configuration as it did before this spec, and workflows.save
  writes store revisions again. The installation repository and its commits stay on disk untouched and
  are simply no longer read; the accepted configuration records and the content addressed definitions
  stay in the store, and every pin still resolves because a pin's digest is the same digest VELDO-0132
  computes. No automatic rollback, retry or recovery is authorized.
---

## Intent

An installation of Veldo is configured the way mature GitOps systems are configured: what the owner sets
up and wants versioned and reviewed lives in the installation's own repository, Veldo's database holds
what happens while Veldo runs, and the keystore holds secrets, never either of them. Veldo is a generic
open-source product, and every installation's own setup lives in that installation's private repository,
never in Veldo.

The repository holds the owner identity and approvers, projects, accounts, ports, the bot and its
channels, roles and teams, outside services, local connectors with their allowed tools and never rules,
landing destinations, workflow definitions, the memory manifest, declared schedules, and the
personal-setup patterns and decision references of VELDO-0259 and the records of VELDO-0250. The
database holds runs,
approvals, conversations, schedule occurrences, account pauses, the record of which configuration commit was live, and which
workflow revision each run used. A workflow saved on the canvas is committed to the repository, so there
is one source of truth for definitions, and the database keeps an exact copy only of what a run used.
Every new installation starts its own private repository from a template that setup creates.

## Context

- VELDO-0259 gives every deployment one installation folder, read only by .veldo/installation.py, and
  documents its layout; VELDO-0250 later moves every personal value out of the product into it. It treats the folder as files on disk. This
  spec makes the folder a Git repository with a declared schema, reads it from commits, and defines how a
  change becomes live. The reader stays the single boundary: the loader here is built on it.
- VELDO-0132 stores immutable workflow revisions in the store; Workflows.save is today the only writer
  and moves the head. VELDO-0241 binds a project's kinds of work to revisions by the project owner's
  signed command and pins {id, version, digest} on each unit. VELDO-0246 is the canvas that saves through
  workflows.save and draws a run against its pinned revision. This spec moves the authoritative copy of a
  definition into the installation repository and keeps the store's copy as the run's record; the
  amendment to VELDO-0241 is proof/VELDO-0253/amend-0241.md.
- Factory setup (VELDO-0139, VELDO-0171, VELDO-0234, the control_factory_setup modules) takes the
  owner, chat, bot token file, workspace, ports and engine choices as arguments and writes them into the
  state root, the host trust and service configuration files. Setup also lays down a small team
  repository for the factory project (VELDO-0143). None of that is versioned or reviewable as a whole,
  and a value changed by hand is live at the next restart with no record of who changed it.
- VELDO-0259 (the owner identity, approvers, patterns and decisions), VELDO-0250 (records), VELDO-0251
  and VELDO-0252 (outside services and their grants) and the specs that move roles, teams, the memory
  manifest, schedules and work keys out of the store each need installation kinds. All of them are declared in this
  spec's one schema (AC1), so no spec defines a layout of its own. Anything else in the folder must be
  declared as ignored by the schema (for example research notes), or it is refused as an unknown file.

## Design

**What goes where.** Configuration is desired state: declared, versioned, reviewed. Runtime state is
observed state: written by Veldo as things happen. Secrets are neither. The schema enforces the split: it
has no kind for runtime state, and the store has no writer for configuration other than the loader's
accepted record and content addressed workflow copies.

**Read from commits, not from files.** The loader reads the tree of the branch's commit through Git, so
a half-edited file in the working copy is never live, and the live configuration always has a commit id.

**Snapshot, subscribe, reconcile.** At start: read the branch, validate, and go live or refuse to start
with the problems named when no accepted commit exists yet (a fresh installation's first commit is valid
by construction from the template). Then subscribe to change notifications of the branch reference; on
each notification and at every reconnect compare the branch's commit id with the live one, and load when
they differ. Every Veldo process serving the installation does the same, and the commit id is the
version they agree on.

**Validate the whole tree, then swap.** The loader builds the full new configuration in memory, runs every
check, and swaps it in one step. A refusal changes nothing that is live. The last good commit is the one
recorded as accepted in the store.

**Widening needs the owner.** Narrowing (removing a tool, adding a never rule, removing a port) is live as
soon as it is valid, so the owner can always reduce authority quickly through the repository. Widening
waits for the owner's signed decision on that exact commit. This is where the repository meets the
owner's signed command path: the commit is the proposal, the decision is the authority.

**The canvas is a Git client.** The canvas save becomes a commit with a compare and swap on the branch,
the same mechanism any other client of the repository uses. There is no second store of definitions.

**The store keeps what a run used.** A run's revision is a content addressed copy, so a run's history
never depends on the repository's history staying intact.

## Out of scope

Hosting the installation's remote; Veldo only pushes to the remote the installation declares. Review
workflows on a Git host (pull requests, required reviewers); the owner may use them, and Veldo's authority
check is the signed decision of AC2 regardless. Moving existing runtime records. Multi-branch promotion of
configuration between environments. Configuration for the product's own defaults, which stay in the
product (the shipped `code` workflow among them).

## Open questions for the owner

- Whether removing a project should count as widening (it narrows authority but can stop work in flight);
  this draft treats it as narrowing and lets units already running finish on their pinned revision.

## What the reviewer judges

- Normal use: a fresh setup produces an installation repository whose first commit is valid; an owner's
  commit that narrows authority is live within one notification; a widening commit shows up as one
  owner decision naming it; a canvas save produces exactly one commit and the next version, pushed to
  the declared remote; a run keeps its revision after the file changes.
- Threat model: a commit that widens authority and goes live without the owner; a Git author name taken
  as authority; a bad file that partially applies; a secret value committed to the repository; a second
  writer of definitions; a run whose recorded revision changes because the repository changed.
- Out of review scope (filed, not blocking): concurrent canvas editors beyond the stale_version refusal;
  very large installation repositories.

## History

2026-11-04: new draft. Owner, Telegram 39098 and 39100: Veldo is a generic open-source product and the
owner's setup lives in the owner's own private installation repository, never in Veldo. 39115: the owner
asked whether configuration belongs in a repository or a database. 39116: the lead's answer this spec
builds: the installation repository holds what the owner sets up and wants versioned and reviewed, the
database holds what happens while Veldo runs and which workflow revision each run used, the keystore holds
secrets; a workflow saved on the canvas is committed to the repository as the one source of truth; every
new installation starts its own private repository from a template setup creates. 39140: the owner asked
for this specification. Standalone; no plan work item. The change to VELDO-0241's revision store is
written as an amendment note, proof/VELDO-0253/amend-0241.md, and VELDO-0241 itself is not edited.

2026-11-04: approved by the owner, Telegram 39144 ("Yes", to 39143). Status ready.

2026-11-04: amended per the plan consistency review (research/veldo-plan-consistency-review-2026-11-04.md) and the lead's rulings (research/veldo-plan-rulings-2026-11-04.md), both in the owner's installation repository, on the owner's request Telegram 39145. AC1 is now the one installation layout and schema with every kind the other specs need (R1, R8; findings D2, C18, A15, A16, A21), the installation overrides the product (D2), setup creates the repository at the VELDO-0250 path and records VELDO_INSTALLATION (C23), the installation declares its git remote and Veldo pushes each commit it makes there (R9, C20; the open question on a remote is answered), and setup writes one import commit from today's values (C17). AC2's widening list adds outside service, credential, route, read override, tools snapshot, grant, role, team, schedule, deploy target, render command and renumber hook changes (C19, R8). VELDO-0246 leaves depends_on, since its save UI builds on this spec's commit backend (D6). Owner field is a role id (B1). Status stays ready; the owner approves the amendments in one message.

2026-11-04: depends on VELDO-0259 instead of VELDO-0250: the installation reader and the personal-setup
check this spec builds on were split out of VELDO-0250 into VELDO-0259, which lands first, on the owner's
request Telegram 39145 (plan consistency review research/veldo-plan-consistency-review-2026-11-04.md,
finding D5). References to the reader and the patterns name VELDO-0259; records/ stays VELDO-0250's.
Criteria unchanged; status stays ready.

2026-11-05: Telegram 39154 and 39155, revised rulings R5, R7 and R14 (no mandatory sandbox): the memory
kind no longer says a run reaches a memory server only through the gate; a memory server that carries a
credential is served behind the outside gate, and runs keep today's access to local services. Status
unchanged.

2026-11-05: the review amendments and new tickets approved by the owner, Telegram 39157 ("Yes", to 39156).
