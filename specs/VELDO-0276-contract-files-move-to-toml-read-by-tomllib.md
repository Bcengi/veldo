---
schema: veldo.spec/v1
id: VELDO-0276
title: The human-edited contract files (policy, architecture, capabilities, decisions, decision reviews, examples) move from the YAML subset to TOML read by the standard library's tomllib, through one loader, with an exact converter for adopters
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0268]
placement: [contracts]
protected_paths: [".veldo/policy.yaml", ".veldo/policy_check.py", "engine/.veldo/policy_check.py", "scripts/veldo-guard.sh", "engine/scripts/veldo-guard.sh", ".veldo/control_verification.py", "engine/.veldo/control_verification.py"]
footprint:
  - ".veldo/*.yaml"
  - ".veldo/*.toml"
  - ".veldo/decisions/**"
  - ".veldo/decision_reviews/**"
  - ".veldo/examples/**"
  - ".veldo/*.py"
  - "engine/.veldo/**"
  - "scripts/*.py"
  - "scripts/*.sh"
  - "engine/scripts/**"
  - "packs/**"
  - "scripts/suites/**"
  - "specs/VELDO-0276-contract-files-move-to-toml-read-by-tomllib.md"
  - "specs/index.md"
  - "proof/VELDO-0276/**"
behavior_bearing: true
observability:
  logs: >
    The converter prints one line per file: converted, unchanged, or refused with the first value it
    could not convert exactly. The engine, finding a .yaml contract file and no .toml beside it, prints
    one line naming the file and the converter command.
  metrics: >
    None added.
  traces: >
    The proof bundle records, for every converted file in this repository, the digest of the parsed value
    before and after; they are equal.
  error_taxonomy: >
    Added: contract_format_legacy (a .yaml contract file with no .toml, refused with the converter
    command) and conversion_inexact (converter refusal). Every existing refusal of policy_check, arch and
    the loaders keeps its name and meaning.
acceptance_criteria:
  - id: AC1
    text: >
      Every human-edited contract file of this repository is TOML: .veldo/policy.toml,
      architecture.toml, capabilities.toml, decisions/*.toml, decision_reviews/*.toml and examples/*.toml
      replace their .yaml files, and every reader (policy_check.py, veldo-guard.sh, control_verification.py,
      arch.py, validate.py, validate_checks.py, decision.py, decision_review.py, declared.py, pack.py,
      lander.py, init_scaffold.py, action_executor.py, check_pack_drift.py, check_runner_catalog.py,
      check_template_sync.sh and every other module found by a scan for those file names) reads them
      through one loader in contract_loader.py that calls tomllib. init_scaffold.py writes TOML for a new
      adopter, and every pack carries the same engine. Machine-written records stay JSON. Spec and plan
      front matter are VELDO-0277's, not this spec's.
    falsified_by: >
      A scan row finds no tracked reference to any of the replaced .yaml names outside specs/, proof/ and
      plans/. Registered mutations from a green baseline: (1) policy_check.py keeps reading policy.yaml:
      the protected-path row, which deletes the .yaml and requires a protected path from policy.toml to
      still need approval, goes red; (2) arch.py parses with a private reader: the one-loader row, which
      patches contract_loader's tomllib call to fail and requires every reader to fail, goes red.
  - id: AC2
    text: >
      The conversion is exact. scripts/migrate_contracts_toml.py reads each .yaml contract file with the
      current reader, writes TOML, reads it back with tomllib and refuses (conversion_inexact, nothing
      written) unless the two parsed values are equal, including key order where a reader depends on it,
      null and empty values, and multi-line strings. Its output for this repository is the committed TOML,
      and the policy's protected paths, floors and approval rules are the same set before and after.
    falsified_by: >
      The suite runs the converter over a fixture tree with one file of every value form the YAML subset
      accepts and one value TOML cannot hold (a null inside a list): the first set converts with equal
      values, the second is refused and nothing is written. Registered mutation: the round-trip comparison
      is skipped: the null row goes red.
  - id: AC3
    text: >
      An adopter's tree is never misread. The engine, finding a .yaml contract file without its .toml,
      refuses the command that needed it as contract_format_legacy naming the converter command; it never
      falls back to reading the YAML, and never treats a missing policy as an empty one.
    falsified_by: >
      A fixture adopter with only .veldo/policy.yaml gets contract_format_legacy from policy_check and from
      the guard; after the converter runs, both pass. Registered mutation: the guard treats a missing
      policy.toml as no protected paths: the legacy row goes red.
required_evidence: [unit, integration]
rollback: >
  Revert the commit; the .yaml files come back with it. An adopter that already converted keeps its .yaml
  files until it deletes them, since the converter never removes its input.
---

## Intent

Weight audit item 9, first half: the contract files people edit by hand are read by the standard library
instead of a home-built parser. VELDO-0277 moves spec and plan front matter and then deletes the parser.

## Context

Verified on main at afa292f0. The YAML subset parser .veldo/yamlish.py (430 lines) is reached by 34
modules in .veldo (and their engine copies) and through validate.parse_yamlish and front_matter_match at
149 call sites. Contract files read by it: policy.yaml, architecture.yaml, capabilities.yaml, eight
decisions, two decision reviews and 13 examples. docs/manifest.yaml and site/book.yaml are read by
render_pdfs.py with PyYAML as a manual release act and are out of scope. Python on this host is 3.12.3;
tomllib is standard since 3.11.

The policy file holds the protected paths and approval rules the push guard and landing enforce, so a
misread could drop a protection: owner approval required (security, Telegram 39708). This spec lands
after VELDO-0268, which also changes policy_check.py and the guard.

## Out of scope

Spec, plan and doc front matter (VELDO-0277); deleting yamlish.py (VELDO-0277); core's forked engine
and its files; render_pdfs.py.

## What the reviewer judges

- Normal use: every engine command in this repository and in an adopter that upgrades.
- The policy read from TOML protects exactly the paths the YAML did; nothing falls back to YAML.
- Out of review scope: per the template.

## History

2026-11-07: drafted by the lead from the weight audit's item 9 (Telegram 39708, 39710); split from
VELDO-0277 because the front matter migration touches every spec. A draft; needs the owner.

2026-11-07: ready. Owner approved, Telegram 39756 ("Yes" to 39755, which described both halves).
