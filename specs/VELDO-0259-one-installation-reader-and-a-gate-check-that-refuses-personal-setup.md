---
schema: veldo.spec/v1
id: VELDO-0259
title: Veldo reads everything that belongs to one deployment from one installation folder through one reader, no product default names a person, and a gate stage refuses a candidate that adds personal setup
status: ready
risk: "critical - the same change rewires how a running factory finds its owner, accounts, channels and records, so a wrong cutover stops the factory, and a check that lets personal values through feeds them toward a public repository."
owner: dmitry
human_approval: required
lane: standalone
depends_on: [WARP-1701, WARP-1704]
placement: [distribution, enforcement]
protected_paths:
  - ".veldo/installation.py"
  - "engine/.veldo/installation.py"
  - "scripts/check_personal_setup.py"
  - "scripts/gate_graph.json"
  - "scripts/verify.sh"
footprint:
  - ".veldo/installation.py"
  - "engine/.veldo/installation.py"
  - "docs/installation.md"
  - ".veldo/control_*.py"
  - "engine/.veldo/control_*.py"
  - "packs/*/.veldo/**"
  - "scripts/check_personal_setup.py"
  - "scripts/gate_graph.json"
  - "scripts/verify.sh"
  - "scripts/publish.py"
  - "scripts/check_docs.sh"
  - "scripts/suites/**"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0259-one-installation-reader-and-a-gate-check-that-refuses-personal-setup.md"
  - "specs/index.md"
  - "proof/VELDO-0259/**"
behavior_bearing: true
observability:
  logs: >
    Every Veldo command that reads the installation prints one line naming the installation folder it
    resolved and how (environment variable or the documented default), or that none was found. The
    personal-setup check prints each finding as file, line, category and a masked match (first two
    characters, then ***), never the matched value, and a closing count per category. With no
    installation it prints that it ran the built-in shapes only.
  metrics: >
    None added. The check's closing count per category is the measure a reviewer compares.
  traces: >
    Factory setup's status and the API's health record name the installation folder and the
    installation revision (its commit id when it is a git checkout) the running service loaded.
  error_taxonomy: >
    installation_missing:<key> when an action needs an installation value that is absent (the owner
    identity, an approver, a channel, an account); installation_invalid:<key> when the file is present and
    the value fails its schema; personal_setup:<category> for each gate finding.
acceptance_criteria:
  - id: AC1
    text: >
      ONE DOCUMENTED INSTALLATION FOLDER, AND NO PERSONAL VALUE IN ANY DEFAULT. Veldo reads everything that
      belongs to one deployment from one installation folder, resolved in a fixed order: the
      VELDO_INSTALLATION environment variable, else $XDG_CONFIG_HOME/veldo/installation (else
      ~/.config/veldo/installation), the same configuration root that already holds host_trust.json. One
      reader, .veldo/installation.py (schema veldo.installation/v1), is the only code that opens it. Its
      layout is the one installation schema of VELDO-0253 AC1, which lands after this spec and builds its
      loader on this reader, and docs/installation.md documents that layout; this spec defines no layout of
      its own and uses these of its kinds: installation.yaml (owner display name, owner role id, git
      identities, approver key ids, channels with secrets by reference only, model accounts and their
      labels, hosts, tailnet names, ports, tracker sites and account ids, publisher identity), connectors/,
      services/ and workflows/ (an installation file with the same id as the product's own overrides it),
      patterns/ (the personal-setup patterns of AC2), decisions/ (the map from a decision reference to its
      source message and quote) and records/ (the pre-split history VELDO-0250 moves there). Product
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
required_evidence: [unit, integration, operational]
rollback: >
  Per criterion, above. Overall: revert the reader and its consumers and remove the gate stage; every value
  returns to its in-repository place, and the installation folder is inert when nothing reads it. Nothing
  here moves or deletes a file of the product's history; that is VELDO-0250, which runs last. No automatic
  rollback, retry or recovery is authorized.
---

## Intent

Veldo is a product; each factory is one deployment of it. The product ships generic defaults and
documented extension points, and each deployment keeps its identity, accounts, connectors, workflows and
records in one installation folder the product reads but never contains. This ticket builds the two pieces
everything else needs first: the one reader of that folder, and a gate check that refuses a candidate
adding a personal value back to the product. With both live, every spec and change written from then on
is written against the installation and is refused if it names a person, so the scrub before publication
(VELDO-0250) has nothing new to clean.

## Context

- VELDO-0250 (ready) holds the whole move of personal setup out of the product. It was approved to run as
  the last step before publication, but VELDO-0251, VELDO-0252 and VELDO-0253 build on its reader, and
  drafts written meanwhile add personal setup for it to scrub (review finding D5). Its reader and check
  are therefore this separate ticket, landed first; VELDO-0250 keeps the scrub and the fresh public root
  and depends on this ticket.
- VELDO-0253 owns the one installation layout and schema and adds a Git loader on this reader; the kinds
  this ticket reads are declared there (ruling R1).
- WARP-1704's publication pipeline (default-deny manifest, scan of the produced tree, refuse rather than
  clean) and WARP-1701's surface-scoped naming check exist and are reused. Their word list is committed in
  the product, so the guard publishes what it guards; here the patterns live in the installation.
- The host configuration root $XDG_CONFIG_HOME/veldo already holds host_trust.json, so the installation
  folder sits beside it.

## Design

**One boundary.** The reader is the only module that opens the folder, and a value the product needs from
it is a named key with a schema, so a missing or wrong value is refused by name. This is the split a mature
project draws between a release and a site configuration, designed for any number of installations.

**The guard.** The patterns that define what is personal live with the deployment. The product's check
knows only shapes that are personal for anybody (a home path, a uid, a real-looking email, a secret). The
gate stage and the publication scan run the same code, so they cannot disagree.

**Order.** This ticket lands ahead of VELDO-0251, VELDO-0252 and VELDO-0253. VELDO-0250 (records moved,
live files rewritten, fresh public history) runs last, after the tickets in flight land.

## Out of scope

Moving history records, rewriting live files generically, the inventory and the fresh public root
(VELDO-0250). The Git loader, schema and widening rules of the installation repository (VELDO-0253). The
contents of any deployment's installation.

## What the reviewer judges

That no default anywhere names a person; that the reader is the only module opening the folder; that the
check's built-in rules name nobody; that a planted pattern of each category is refused and never printed
unmasked; that a fresh clone with no installation passes its gate.

## History

2026-11-04: split from VELDO-0250 on the owner's request, Telegram 39145, per finding D5 of the plan
consistency review (research/veldo-plan-consistency-review-2026-11-04.md) and the lead's rulings
(research/veldo-plan-rulings-2026-11-04.md). AC1 and AC2 here are VELDO-0250's AC1 and AC3 as amended that
day, with their falsifiers, footprint, observability and rollback; only cross-references changed (AC1's
patterns/ now points at AC2, records/ at VELDO-0250, and the layout notes that VELDO-0253 lands after this
spec). VELDO-0250 keeps the scrub and the fresh public root and depends on this spec; VELDO-0251, VELDO-0252
and VELDO-0253 depend on this spec instead of VELDO-0250. New text, so status draft; the owner approves it
in the next message. Standalone; no plan work item.

2026-11-05: the review amendments and new tickets approved by the owner, Telegram 39157 ("Yes", to 39156). Status ready.
