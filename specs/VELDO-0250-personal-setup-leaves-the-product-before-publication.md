---
schema: veldo.spec/v1
id: VELDO-0250
title: Before Veldo is published, every piece of the owner's personal setup moves to his installation, the owner becomes an installation setting, a gate check refuses its return, and the public repository starts from a fresh history
status: ready
risk: "critical - it moves bytes toward a public repository. A personal value that reaches a public push is permanent, and the same change rewires how the owner's running factory finds its owner, accounts, channels and records, so a wrong cutover stops his factory."
owner: dmitry
human_approval: required
lane: standalone
depends_on: [WARP-1701, WARP-1704]
placement: [distribution, enforcement]
protected_paths:
  - "scripts/check_personal_setup.py"
  - ".veldo/installation.py"
  - "engine/.veldo/installation.py"
  - "scripts/gate_graph.json"
  - "scripts/verify.sh"
  - "scripts/publish.py"
footprint:
  - ".veldo/installation.py"
  - "engine/.veldo/installation.py"
  - "scripts/check_personal_setup.py"
  - "scripts/gate_graph.json"
  - "scripts/verify.sh"
  - "scripts/publish.py"
  - "scripts/check_docs.sh"
  - ".veldo/private_names.txt"
  - "engine/.veldo/private_names.txt"
  - "docs/installation.md"
  - ".veldo/**"
  - "engine/**"
  - "packs/**"
  - "scripts/**"
  - "docs/**"
  - "site/**"
  - "specs/**"
  - "plans/**"
  - "proof/**"
  - "releases/**"
  - "README.md"
  - "CONTRIBUTING.md"
  - "SECURITY.md"
  - "CLAUDE.md"
  - "VELDO.md"
  - ".claude/**"
  - ".claude-plugin/**"
  - "patch-mine-only.diff"
  - "specs/VELDO-0250-personal-setup-leaves-the-product-before-publication.md"
  - "specs/index.md"
  - "proof/VELDO-0250/**"
behavior_bearing: true
observability:
  logs: >
    Every Veldo command that reads the installation prints one line naming the installation folder it
    resolved and how (environment variable or the documented default), or that none was found. The
    personal-setup check prints each finding as file, line, category and a masked match (first two
    characters, then ***), never the matched value, and a closing count per category. With no
    installation it prints that it ran the built-in shapes only.
  metrics: >
    None added. The inventory command reports files and lines per category and per top-level folder in
    the same shape as proof/VELDO-0250/inventory.json, so a before and after are compared by count.
  traces: >
    Factory setup's status and the API's health record name the installation folder and the
    installation revision (its commit id when it is a git checkout) the running service loaded.
  error_taxonomy: >
    installation_missing:<key> when an action needs an installation value that is absent (the owner
    identity, an approver, a channel, an account); installation_invalid:<key> when the file is present and
    the value fails its schema; personal_setup:<category> for each gate finding; publication_history:<reason>
    when the public tree's history is not a single fresh root commit.
acceptance_criteria:
  - id: AC1
    text: >
      ONE DOCUMENTED INSTALLATION FOLDER, AND NO PERSONAL VALUE IN ANY DEFAULT. Veldo reads everything that
      belongs to one deployment from one installation folder, resolved in a fixed order: the
      VELDO_INSTALLATION environment variable, else $XDG_CONFIG_HOME/veldo/installation (else
      ~/.config/veldo/installation), the same configuration root that already holds host_trust.json. One
      reader, .veldo/installation.py (schema veldo.installation/v1), is the only code that opens it, and
      docs/installation.md documents its layout: installation.yaml (owner display name, owner role id, git
      identity, approver key ids, channels with secrets by reference only, model accounts and their
      labels, hosts, tailnet names, ports, tracker sites and account ids, publisher identity),
      connectors/ and workflows/ (searched after the product's own, through the existing catalog and pack
      loaders), patterns/ (the personal-setup patterns of AC3), decisions/ (the map from a decision
      reference to its source message and quote) and records/ (the owner's pre-split history, AC2). Product
      defaults name nobody: the spec owner field holds a role id, an action that needs a person resolves
      it through the installation, and when the value is absent it refuses by name
      (installation_missing:owner), never falls back to a built-in person. A fresh clone with no
      installation passes its own gate.
    falsified_by: >
      With VELDO_INSTALLATION pointing at an empty folder, any product output (setup, API, notification,
      landing commit identity, approval record, generated spec) carrying a name, email, account label,
      host, chat id or path of the owner; any module other than .veldo/installation.py opening the
      folder; a fresh clone with no installation whose gate is red.
    rollback: >
      Revert the reader and the consumer changes; the values return to their in-repository places. The
      installation folder is left on disk untouched and is simply no longer read.
    observability: >
      The resolution line each command prints; the installation folder and revision in factory status and
      the API health record; installation_missing:<key> and installation_invalid:<key> by name.
    footprint: [".veldo/installation.py", "engine/.veldo/installation.py", "docs/installation.md", ".veldo/control_*.py", "engine/.veldo/control_*.py", "packs/*/.veldo/**", "scripts/suites/**"]
    protected_paths: [".veldo/installation.py", "engine/.veldo/installation.py"]
  - id: AC2
    text: >
      THE TREE IS SCRUBBED BY MOVING HISTORY AND REWRITING WHAT IS LIVE, AND THE INVENTORY READS ZERO.
      Records of what happened move, byte for byte, to records/ in the owner's installation repository with
      a digest list: the pre-split proof corpus, the factory's own records (.veldo/events.jsonl,
      lessons.jsonl, decisions/, decision_reviews/), the History and Intent sections of closed specs and
      plans, and the company-internal design and research drafts under docs/design and docs/research. A
      closed spec keeps its contract in the product (front matter, criteria, design) so dependencies still
      resolve, with its owner as a role id and its history as decision references (D-<n>) the installation
      resolves. Live behaviour is rewritten generically in place: code and fixture labels, example
      identities (example.invalid), tracker sites and account ids, product and vendor names in suites and
      fixtures, team and assistant names in docs, the list of automated principal names, the publication
      coordinates in scripts/publish.py (read from the installation's publisher entry), and the committed
      .veldo/private_names.txt, which is deleted because it is itself a list of the owner's products.
      Proof files the gate reads as inputs (fixtures, extractors, baselines) are live, found from the
      suites' declared case inputs and not by guessing, and move to scripts/fixtures with generic
      content. Rerunning the inventory over the scrubbed tree, with the installation's patterns, reports
      zero files in every category, and the full gate is green.
    falsified_by: >
      Any inventory row over the scrubbed tree; a moved file whose digest in records/ differs from its
      digest on the private main before the move; a suite or mutation case that reads a removed proof path;
      a spec whose depends_on no longer resolves; the gate red after the scrub.
    rollback: >
      Revert the scrub commits on the private repository; every moved file is restored from history and
      the installation's copies stay as a harmless duplicate.
    observability: >
      The inventory command's per-category and per-folder counts before and after, committed with the
      proof; the digest list of moved files; the gate's suite results.
    footprint: [".veldo/**", "engine/**", "packs/**", "scripts/**", "docs/**", "site/**", "specs/**", "plans/**", "proof/**", "releases/**", "README.md", "CONTRIBUTING.md", "SECURITY.md", "CLAUDE.md", "VELDO.md", ".claude/**", ".claude-plugin/**", "patch-mine-only.diff"]
    protected_paths: ["scripts/publish.py"]
  - id: AC3
    text: >
      A GATE STAGE REFUSES A CANDIDATE THAT ADDS PERSONAL SETUP AGAIN, AND THE CHECK NAMES NOTHING
      PERSONAL. scripts/check_personal_setup.py runs as a declared stage in scripts/gate_graph.json over the
      lines a candidate adds against its base, and in sweep mode over a whole tree (the publication scan of
      scripts/publish.py calls the same code, so the gate and publication share one definition). Its
      patterns come from the installation's patterns/ folder (literal strings and expressions, each with a
      category), never from the repository; the only built-in rules are shapes that name nobody: an
      absolute path under any user's home directory, a login uid in a systemd or runtime path, an email
      outside the reserved example domains in a fixture, and the secret shapes the existing secret
      scanner already knows. A finding refuses the candidate as personal_setup:<category> with file, line
      and a masked match. With no installation the check runs the built-in shapes and says so on its own
      line, so a contributor is not blocked by patterns they do not have and the owner's factory, which
      always has its installation, is.
    falsified_by: >
      Planting any value from the installation's patterns in a candidate (one per category) and the gate
      passing; the matched value appearing unmasked in any gate output or proof; any pattern string from
      the installation found in a tracked file of the product; the check running with no installation and
      printing nothing about it.
    rollback: >
      Remove the stage from scripts/gate_graph.json; nothing else reads the check. The installation's
      pattern files stay and are inert.
    observability: >
      The stage's per-finding lines and per-category counts in the gate log; the stage result in the gate
      stamp; the built-in-only line when no installation is present.
    footprint: ["scripts/check_personal_setup.py", "scripts/gate_graph.json", "scripts/verify.sh", "scripts/publish.py", "scripts/check_docs.sh", "scripts/suites/**", "scripts/check_teeth_mutations.py"]
    protected_paths: ["scripts/check_personal_setup.py", "scripts/gate_graph.json", "scripts/verify.sh"]
  - id: AC4
    text: >
      THE PUBLIC REPOSITORY STARTS FROM ONE FRESH ROOT COMMIT, THE PRIVATE ONE KEEPS EVERYTHING, AND THE
      OWNER'S FACTORY NEVER STOPS. The scrub lands on the private repository as ordinary commits, so its full
      history (3294 commits on main at measurement, all under the owner's identity) is kept, tagged at the
      cutover point and then archived read-only. The public repository is created from the publication
      pipeline's output of the scrubbed tree as a single root commit authored by the publisher identity from
      the installation, which is a project identity and not a person; nothing from the private history is
      reachable in it. From then on the public repository is upstream and the owner's factory works on
      clones of it, reading everything personal from his installation. The order keeps the factory running:
      first the installation repository is filled from the current values, then factory setup writes
      VELDO_INSTALLATION into the running service's environment, then the reader lands, then the in-tree
      values are removed. After each step a continuity probe dispatches one unit and lands it.
    falsified_by: >
      The public repository having more than one commit, a commit authored by a person named in the
      installation, or any object id that also exists only in the private history; a pattern finding in
      the published tree; the continuity probe failing to dispatch or land after any step.
    rollback: >
      Before the public push, discard the produced tree and the empty public repository; nothing was
      published. After it, the public repository is not rewritten: a finding is fixed forward with a new
      commit and, for a secret, by revoking it. The owner's factory returns to the previous step by
      restoring the service environment that factory setup recorded before the change.
    observability: >
      The publication pipeline's report (tree digest, scan counts, root commit id, author); the private tag
      at the cutover; the continuity probe's dispatch and landing records after each step.
    footprint: ["scripts/publish.py", ".veldo/control_factory_setup.py", "engine/.veldo/control_factory_setup.py", "docs/installation.md", "docs/public-distribution.md"]
    protected_paths: ["scripts/publish.py"]
required_evidence: [unit, integration, operational]
rollback: >
  Per criterion, above. Overall: the private repository keeps every byte and every commit, so any step is
  undone by a revert there, and the installation folder is inert when nothing reads it. The only act that
  cannot be undone is the public push, which happens last, after a clean scan and the owner's approval.
---

## Intent

Owner decisions, Telegram 2026-11-04. 39098: "Remember that veldo repo can't have any of my personal
setup". 39100: "Maybe we need custom repo for our factory with veldo config and all custom connectors and
workflows? We can't commit it back to veldo repo that is open source". 39104: yes to this cleanup ticket.

Veldo is a product; the owner's factory is one deployment of it. A mature open-source project keeps the
two apart the way a server keeps its code apart from its configuration: the product ships generic defaults
and documented extension points, and each deployment carries its own identity, accounts, connectors,
workflows and records in a place the product reads but never contains. The owner's deployment lives in the
owner's installation repository, a separate private repository being created now. Nothing in Veldo names
it.

## Context

The measured inventory of 2026-11-04 (proof/VELDO-0250/inventory.json lists every file, its category and
its matching line count) read all 7419 tracked files on main at 043c2ef6. 1227 files carry personal setup:
741 are history, 231 are live records (open specs and plans), 255 are live behaviour.

- Owner name and email: 728 files, 2233 lines (live 129 files, open records 230, history 369). Every spec's
  owner field, approval records, approver labels in fixtures, a hardcoded personal git identity in
  scripts/migrate_to_veldo.py, docs and prose.
- Telegram ids and quotes: 337 files, 888 lines (live 89, open records 139, history 109). Spec Intent and
  History sections, comments in engine code, the chat id in two suites.
- Paths under the owner's home and his host name: 167 files, 2422 lines, almost all history (162 files in
  proof, mostly worktree paths); 2 live files, 3 open records.
- Company, products, repositories, industry terms, vendors and services: 230 files, 1236 lines (live 55,
  open records 18, history 157). Includes the committed .veldo/private_names.txt, which is itself a list of
  the owner's product names, the company coordinates hardcoded in scripts/publish.py, the company-internal
  methodology drafts in docs/design and docs/research, and the site builder.
- Account names and model-account labels: 14 files, 24 lines (live 8): account labels, an executor label
  named after the owner, tracker account and site ids in suites.
- Machine specifics: 77 files, 494 lines, all history except 2 open records: the login uid in systemd and
  runtime paths. No real tailnet name, device name or port of the owner's was found; the tree uses
  example.ts.net and generic placeholders.
- Secret and token shapes: 5 files, 16 lines, all documented public example values or synthetic detector
  fixtures (masked in the inventory). No live secret.
- Other: team members' first names and the owner's assistant's name, 124 files, 185 lines (live 42), in
  docs, suites and the automated principal lists in .veldo/action_executor.py, admission_contract.py and
  authority_contract.py.
- Outside the tree: all 3294 commits on main carry the owner's name and company email as author and
  committer. Only a fresh history removes them.

By folder, proof holds most of the volume (paths 2401 lines, company 801, owner 741, machine 495), specs
hold the owner field and Telegram citations (415 and 141 files), scripts hold the live fixtures (61 files
with owner identity, 19 with company terms), and engine, .veldo, docs, plans, site and packs hold the rest.

What already exists and is reused: WARP-1704's publication pipeline (default-deny manifest, scan of the
produced tree, refuse rather than clean) and WARP-1701's surface-scoped naming check. What is wrong in
them for this purpose: the scan's word list is committed in the product, so the guard publishes what it
guards. The host configuration root $XDG_CONFIG_HOME/veldo already holds host_trust.json, so the
installation folder sits beside it.

## Design

**Product and deployment.** The product repository holds code, generic defaults, generic fixtures,
documentation and its open design records. The installation holds everything that is true of one
deployment only. The reader is the single boundary: no other module opens the folder, and a value the
product needs from it is a named key with a schema, so a missing or wrong value is refused by name. This
is the same split a mature project draws between a release and a site configuration, and it is designed
for any number of installations, not for this one.

**What moves to the installation repository.** Owner identity, approvers, git identity, channels, model
accounts and their labels, hosts, tailnet names, ports, tracker sites and ids, publisher identity, custom
connectors and workflows (39100), the personal-setup patterns, the decision reference map, and records/:
the history that cannot be rewritten without falsifying it.

**What is rewritten in place.** Everything a user runs or reads: code labels and defaults, suites and
fixtures, open specs and plans, product docs, the site, packs. A spec's owner field becomes a role id; a
spec History cites a decision reference that the installation maps to its source message and quote.

**History.** History records move unchanged; they are true records of the owner's deployment and belong
to it. The private repository keeps every commit. The public repository starts from one root commit.

**The guard.** The patterns that define personal live with the person. The product's check knows only
shapes that are personal for anybody (a home path, a uid, a real-looking email, a secret).

## Out of scope

Changing the license, copyright holder or contributor agreement, and choosing the public hosting
organisation: those are the publisher's legal identity, not personal setup, and stay where they are unless
the owner decides otherwise (open question below). Rewriting the public history after publication. The
contents of the owner's installation repository beyond the layout this spec defines.

## Open questions for the owner

- The copyright line in LICENSE and NOTICE, the contributor agreement counterparty, and the public
  repository's organisation name each name the company. They are treated as the publisher's identity and
  kept; say if they should move to the installation too.
- Whether the closed specs' contracts stay in the public repository (this draft keeps them so dependencies
  resolve) or move wholesale to records/ with the public repository starting its spec numbering fresh.

## What the reviewer judges

That the inventory is complete (rerun the scan from its method; spot-check categories by folder); that no
default anywhere names a person; that the check's built-in rules name nobody; that the cutover order keeps
the factory dispatching and landing at every step; that nothing reaches a public push before a clean scan
and the owner's approval.

## History

2026-11-04: drafted from the owner's decisions in Telegram 39098, 39100 and 39104, with the measured
inventory in proof/VELDO-0250/inventory.json.

2026-11-04: approved by the owner, Telegram 39113 ("Yes", to 39112), with the lead's sequencing: it runs after the tickets in flight land, as the last step before publication. Status ready.
