---
schema: veldo.spec/v1
id: VELDO-0277
title: Spec, plan and doc front matter move to TOML read by tomllib, every generated document is written as TOML or JSON, and yamlish.py with its grammar, agreement and boundary suites is deleted
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0276]
placement: [contracts]
protected_paths: [".veldo/policy_check.py", "engine/.veldo/policy_check.py", "scripts/veldo-guard.sh", "engine/scripts/veldo-guard.sh"]
footprint:
  - "specs/**"
  - "plans/**"
  - "docs/**"
  - ".veldo/*.py"
  - "engine/.veldo/**"
  - "scripts/*.py"
  - "scripts/*.sh"
  - "scripts/fixtures/**"
  - "engine/scripts/**"
  - "packs/**"
  - "scripts/suites/**"
  - "proof/VELDO-0277/**"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
behavior_bearing: true
observability:
  logs: >
    The converter prints one line per file: converted, or refused with the first field it could not
    convert exactly. A reader meeting a document that still opens with --- prints the path and the
    converter command.
  metrics: >
    None added.
  traces: >
    The proof bundle records, for every converted document, the digest of the parsed front matter before
    and after; they are equal.
  error_taxonomy: >
    Added: front_matter_legacy (a --- document, refused with the converter command) and
    conversion_inexact. Removed: every yamlish grammar refusal and the parser and writer boundary
    findings. Every validator refusal on a field's value keeps its name.
acceptance_criteria:
  - id: AC1
    text: >
      Every spec, plan and doc with front matter in this repository opens with a +++ fenced TOML block,
      including specs/TEMPLATE.md and plans' template, and every reader takes it through one function
      (validate.front_matter, calling tomllib) in place of parse_yamlish and front_matter_match at all of
      their call sites. A document that still opens with --- is refused as front_matter_legacy naming the
      converter; it is never read as empty front matter, so human_approval, protected_paths, status and
      depends_on can never be lost to a misread.
    falsified_by: >
      A scan row finds no call of parse_yamlish, front_matter_match or yamlish in tracked code outside
      proof/ and specs/. Registered mutations from a green baseline: (1) a legacy document reads as empty
      front matter: the legacy row, which requires policy_check to refuse a fixture spec with
      human_approval required in --- form, goes red; (2) one reader keeps a private regex for the fence:
      the one-reader row, which breaks validate.front_matter and requires every reader to fail, goes red.
  - id: AC2
    text: >
      The conversion is exact and is how this repository's documents were converted.
      scripts/migrate_front_matter_toml.py, which carries the YAML subset reader privately for the
      migration and nothing else, converts a tree in place, reads each result back with tomllib and
      refuses the file (nothing written) unless the parsed values are equal. Its run over specs/, plans/
      and docs/ is the commit; the proof lists every file with its before and after digest.
    falsified_by: >
      The suite converts a fixture tree holding every field form the corpus uses (folded strings, lists of
      tables, empty lists, quoted ids) plus one value TOML cannot hold: the first convert with equal values,
      the second is refused. Registered mutation: the read-back comparison is skipped: the refused row goes
      red.
  - id: AC3
    text: >
      Nothing writes YAML any more. restoration.py writes the specs it generates as TOML front matter
      through a small writer limited to the value forms the spec contract uses and checked by reading back
      with tomllib; incident_reconcile.py and estimate.py write their records as JSON.
    falsified_by: >
      The restoration suite's generated spec is read back by validate.front_matter and passes validate.py
      spec. Registered mutation: the writer emits an unquoted string holding a colon and a hash: the
      read-back row goes red.
  - id: AC4
    text: >
      The parser and its qualification are gone: .veldo/yamlish.py and its engine copy; suites 45, 51, 52,
      54, 55 and 57 (or, for 45, only its parser rows); scripts/test_yamlish.py, parser_corpus_audit.py,
      writer_corpus_audit.py, check_parser_boundary.py and check_writer_boundary.py; the fixtures
      yamlish_grammar.json, grammar_cases.py, policy_agreement.py, reader_agreement.py and yaml_oracle.py;
      the mutation cases on them; and the architecture pattern reuse_one_parser names tomllib. The
      converter and its private reader stay for one release so adopters can convert, and a follow-up spec
      deletes them.
    falsified_by: >
      A scan row finds none of the deleted names in tracked files outside specs/, proof/ and plans/, and
      requires the manifest and the mutation case inputs to name none of them. Registered mutation: one
      deleted suite is left in the manifest: the scan row goes red.
required_evidence: [unit, integration]
rollback: >
  Revert the commit; the documents return to --- front matter with it and yamlish.py comes back. An
  adopter that converted runs the converter's inverse mode, which the proof exercises once.
---

## Intent

Weight audit item 9, second half: after VELDO-0276, move the front matter of every spec, plan and doc,
then delete the parser and the roughly 3,700 lines that qualify it against PyYAML.

## Context

Verified on main at afa292f0: yamlish.py is 430 lines; it is reached at 149 call sites through
validate.parse_yamlish and front_matter_match; specs/ holds 424 spec files (VELDO and WARP) plus the template and index, plans/
21 files, and docs/ several pages with front matter. yamlish.dump is still called by restoration.py
(generated specs), incident_reconcile.py and estimate.py. The suites the audit names are 1,053 lines
(45, 51, 52, 54, 55, 57); the five tools named in AC4 are 454 lines; the yamlish fixtures make up most
of scripts/fixtures (2,994 lines in all, of which authority_store.py, registered_clients.py and
relay_exchange.py are not the parser's and stay).

Front matter carries human_approval, protected_paths and status, which decide approval and landing, so a
misread is a security failure under the owner's scope (Telegram 39708): owner approval required.

The audit's risk stands: specs in core are core's to migrate under its forked engine (audit item G) and
are out of scope here.

## Out of scope

Core's specs and engine; render_pdfs.py and site/book.yaml; the meaning of any front matter field.

## What the reviewer judges

- Normal use: every engine command over specs and plans after the change, and an adopter converting.
- No field's parsed value changes in conversion; no legacy document is read as anything but a refusal.
- Out of review scope: per the template.

## History

2026-11-07: drafted by the lead from the weight audit's item 9 (Telegram 39708, 39710), split from
VELDO-0276. A draft; needs the owner.

2026-11-07: ready. Owner approved, Telegram 39756 ("Yes" to 39755, which described both halves).

2026-11-07: footprint gains the suite registration files (scripts/suites/manifest.json, requires.json and scripts/check_teeth_mutations.py where missing), by the lead under Telegram 39708 (mechanical, ACs unchanged): selftest refuses a suite file the manifest does not enumerate, so a ticket that adds a suite must register it (VELDO-0272 build stopped on this, proof/VELDO-0272/README.md).
