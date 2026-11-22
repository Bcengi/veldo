# The installation folder

Veldo is a product, and each factory is one deployment of it. The product ships generic defaults and
documented extension points. Everything that belongs to one deployment (who owns it, its accounts,
channels, hosts, its own connectors and workflows, its records) lives in one installation folder that the
product reads and never contains.

## Where it is

The folder is resolved in a fixed order:

1. the `VELDO_INSTALLATION` environment variable, when it is set and not empty;
2. else `$XDG_CONFIG_HOME/veldo/installation`, when `XDG_CONFIG_HOME` is an absolute path;
3. else `~/.config/veldo/installation`.

This is the same configuration root that holds `host_trust.json`. Every Veldo command that reads the
installation prints one line naming the folder it resolved and how (the environment variable or the
documented default), or that none was found and where it looked.

## One reader

`.veldo/installation.py` (schema `veldo.installation/v1`) is the only code that opens the folder. A value
the product needs is a named key with a schema:

- `installation_missing:<key>` when an action needs a value that is absent, for example
  `installation_missing:owner` when no owner is declared. Nothing falls back to a built-in person, account,
  host or path.
- `installation_invalid:<key>` when the file is present and the value fails its schema.

Factory setup creates a private Git repository from the shipped installation template. Use
`--installation` to choose its path and `--installation-remote` to declare its remote. The service's
environment records `VELDO_INSTALLATION`. A setup re-run imports existing live configuration once;
workflow versions and their definition digests stay unchanged.

The service reads the configured branch's committed tree and watches reference changes through the
operating system. Working-copy edits have no effect. It validates the whole tree before accepting it;
one bad file keeps the previous accepted configuration live and reports every problem to the owner.
Status names the accepted commit, pending widening, refusals and configuration age.

Changes that widen authority wait for an ordinary signed owner decision naming the exact commit and
the digest of its widening list. A later commit makes the earlier pending decision stale. Narrowing
changes need no new decision. Git authorship records provenance and grants no authority.

These changes wait for the owner's decision (the schema's `widening` and `deletion` sections):

- installation: a new or changed account or channel chat, a new port, a new approver, a changed owner
  role, a new or changed remote, a changed bot token reference, a new or changed tracker, host or
  tailnet name, a changed publisher identity, a raised inbound file cap;
- space (what Veldo may remove): removals turned on, a protect entry dropped (a path, volume,
  container, image, network or compose project), an engine, scratch root, build root, plain
  repository or client account added, a changed session pattern, time zone or process reader, a
  pool dropped or its floor or needs lowered;
- projects: a new project; a changed, added or removed workflow binding, account, landing
  destination, remote, repository, trunk, render command or renumber hook; a new or changed deploy
  target; deleting a project file that declares bindings (its work falls back to the default);
- connectors: a tool added to the allowed list, a never rule removed, a changed, added or removed
  command, argument list or environment;
- memory: a new or changed server or store, a changed history sink or manifest;
- roles and teams: a capability granted, a role added to a team;
- services: a new service, a changed base URL, credential reference or location, grants, OpenAPI
  file or tools snapshot, a new route or read override, a never rule removed, a raised body limit;
- schedules: a new or changed schedule;
- workflows: a new outward or paid step, a new role or tool reference, and deleting an installation
  file that overrides a product default (the product's own definition runs again).

Everything else applies as soon as the commit is valid, because it only reduces authority: removing a
tool from an allowed list, adding a never rule, removing a port, account, channel, approver or
deploy target, lowering a limit, and deleting a connector, service, schedule, role, team, memory
server or a project file with no bindings. In the space section: turning removals off, adding a
protect entry, removing an engine, root, plain repository or client account, adding a pool or
raising its floor or needs, and removing the section (space management off). Metadata such as
labels and display names also applies directly.

Every cross reference is checked: a project's account, workflow bindings and deploy target services,
a schedule's workflow and project, a memory server's service and a store's server, a team's roles, a
connector's allowed tools and a service's documents. A reference to something the tree does not hold
refuses the whole commit with `installation_invalid:<path>:<key>:unknown_reference`, and the last
good configuration stays live.

Veldo sends commits it makes to the declared remote after local acceptance, without force. A refused
send reports `installation_push_failed` and keeps the accepted commit live locally.

## Layout

The closed, machine-readable declaration is `.veldo/installation_schema/schema.json`. Unknown files
and unknown fields refuse the entire commit. Runtime state has no installation kind.

```
installation.yaml          the deployment's settings (below)
projects/<id>.yaml         account, repository, workflow bindings and work commands
roles/<id>.yaml            capability grants and role configuration
teams/<id>.yaml            teams and their roles
connectors/<id>.yaml       local tool servers; same id as a product connector overrides it
services/<id>.yaml         outside services; same id as a product service overrides it
workflows/<id>.json        workflow definitions; same id as a product workflow overrides it
workflows/<id>.layout.json canvas layout, versioned separately from the definition
services/<id>.openapi.json optional service API description
services/<id>.tools.json   pinned service tool snapshot
memory/*.yaml             stores, servers and the session history sink
schedules/<id>.yaml        declared schedules, never schedule occurrences
patterns/*.yaml            the personal-setup patterns (below), read only by the personal-setup check
decisions/*.yaml           the map from a decision reference to its source message and quote
records/                   history with records/digests.json; never configuration
research/, notes/          explicitly ignored
```

### installation.yaml

```yaml
schema: veldo.installation/v1
owner:
  display_name: Example Owner      # who the owner role resolves to
  role_id: owner                   # the role id a spec's owner field holds
git_identities:
  owner: {name: Example Owner, email: owner@example.com}
approvers: [owner-key-1]           # approver key ids
git: {branch: main, remote: origin}
channels:
  main:
    kind: chat
    chat: "1000"
    token: {secret: chat_token}    # secrets by reference only; a literal is refused
accounts:
  primary: {label: primary-account}
hosts:
  build: build.example.com
tailnet_names:
  build: build-node
ports:
  api: 8710
trackers:
  main: {site: tracker.example.com, account_id: acct-1}
publisher: {name: Example Publisher, email: publisher@example.com}
```

The schema discriminator is required; an action needing another absent key refuses by name.
Validation reports `installation_invalid:<path>:<key>:<reason>`, `installation_unknown_file:<path>`,
`installation_secret_inline:<path>:<key>` or `installation_secret_missing:<name>`. Credentials use
`{secret: <name>}`. Validation checks keystore metadata only; credentials are resolved at use time.
A plain value under a key that names a credential (any key containing `token`, `password`, `secret`,
`credential`, `api_key`, `private_key` or `access_key`, or ending in `key`) is refused as
`installation_secret_inline`, never stored. Connectors hold no credential at all: their environment
takes plain strings only, so a credential a local tool server needs belongs to an outside service.
Before Veldo itself commits a tree (setup's import, a canvas save) it also scans the files it never
reads, such as `notes/` and `research/`, and refuses the commit if one holds a credential.

## Workflow saves and pins

A canvas save names its base version and accepted configuration commit. It validates the proposed
whole tree, builds a Git commit with the editor's declared identity, and publishes the branch with a
compare-and-swap. A moved branch refuses `stale_version`. A widening save returns its pending commit;
the owner's signed save names that commit and carries its ordinary signed settlement answer.

Veldo builds its commits from Git objects, not from the working copy. When the checkout is on the
configured branch and clean, a save also moves the checkout's files and index to the new commit, so a
later `git commit -a` keeps the save. A checkout with uncommitted edits is never touched; bring it up
to date with `git status` and `git checkout` before committing, or a commit made from the stale index
can undo a save.

The loader records immutable canonical definition copies by digest. A layout-only commit updates the
layout without allocating a definition version. Existing runs retain their pinned version and digest
even if the original Git commit is deleted. Project files declare workflow bindings; the former
binding command refuses `installation_managed`. An installed `code` workflow overrides the shipped
version 0 for new units; the shipped definition is never copied into the installation by default.

### decisions/*.yaml

```yaml
decisions:
  D-1: {source: message 12, quote: "Yes"}
```

### patterns/*.yaml

```yaml
schema: veldo.installation.patterns/v1
patterns:
  - {category: owner_name, literal: Example Owner}
  - {category: chat_id, expression: '\b1000\d{6}\b'}
```

Each pattern has a category (lower case, digits and underscores) and exactly one of `literal` (matched
without regard to case) or `expression` (a regular expression).

## The personal-setup check

`scripts/check_personal_setup.py` runs as the gate stage `personal_setup` over the lines a candidate adds
against its base, and in sweep mode (`--sweep`) over a whole tree; `scripts/publish.py` runs the same code
over the tree it produces. Its patterns come from the installation's `patterns/` folder, never from the
repository. Its only built-in rules are shapes that name nobody:

- `home_path`: an absolute path under a user's home directory;
- `login_uid`: a login uid in a systemd or runtime path;
- `fixture_email`: an email outside the reserved example domains (`example.com`, `example.org`,
  `example.net`, and names under `.example`, `.test`, `.invalid`, `.localhost`) in a fixture (a file under
  a `fixtures`, `fixture`, `testdata`, `test`, `tests` or `suites` folder, or named `test_*` or `*fixture*`);
- `secret`: the shapes the secret scanner knows, less the lines the repository's secret inventory has
  dispositioned.

A finding refuses the candidate as `personal_setup:<category>` with file, line and a masked match (the
first two characters, then `***`); the matched value is never printed. A closing line counts findings per
category. With no installation the check runs the built-in shapes and says so on its own line, so a
contributor is not blocked by patterns they do not have.
