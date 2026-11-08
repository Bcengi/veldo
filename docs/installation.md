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

Factory setup's answer and the API's status record name the installation folder and its revision (the
commit id when the folder is a git checkout) that the running service loaded.

## Layout

The layout is the one installation schema the installation loader declares (it builds on this reader). This reader
uses these of its kinds:

```
installation.yaml          the deployment's settings (below)
connectors/<id>.yaml       local tool servers; same id as a product connector overrides it
services/<id>.yaml         outside services; same id as a product service overrides it
workflows/<id>.json        workflow definitions; same id as a product workflow overrides it
patterns/*.yaml            the personal-setup patterns (below), read only by the personal-setup check
decisions/*.yaml           the map from a decision reference to its source message and quote
records/                   history records; listed, never read as configuration
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

Every key is optional; an action that needs one and does not find it refuses by name. A key not listed
here is `installation_invalid:<key>`. Under `channels`, `accounts` and `trackers`, a field whose name says
it holds a credential (token, secret, password, credential, api key) must be `{secret: <name>}`.

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
