---
schema: veldo.spec/v1
id: VELDO-0269
title: Veldo keeps one copy of its engine in engine/, and the repository's own instance at the root is laid down from it by the installer every adopter runs, so no engine file is ever edited twice
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0007, VELDO-0045, VELDO-0189]
placement: [enforcement, distribution]
protected_paths: [".veldo/policy.yaml", "scripts/verify.sh", "scripts/check_template_sync.sh", "engine/.veldo/init_scaffold.py", "engine/.veldo/pack.py", "engine/.veldo/policy_check.py", "engine/.veldo/validate.py", "engine/scripts/veldo-guard.sh", "scripts/check_install_and_run.py", "scripts/check_gate_mutations.py"]
footprint:
  - ".gitignore"
  - ".veldo/**"
  - "scripts/**"
  - "bin/veldo"
  - "engine/.veldo/init_scaffold.py"
  - "engine/.veldo/pack.py"
  - "engine/.veldo/control_factory_setup_upgrade.py"
  - "engine/scripts/verify.sh"
  - "packs/claude/scripts/veldo-guard.sh"
  - "CLAUDE.md"
  - "specs/VELDO-0269-veldo-keeps-one-copy-of-its-engine.md"
  - "specs/index.md"
  - "proof/VELDO-0269/**"
behavior_bearing: true
observability:
  logs: >
    The lay-down prints one line: the source commit, the number of files laid, the number unchanged and
    the number removed because the source no longer has them. The check that replaces the template sync
    prints the number of produced files compared against the source and, on a failure, each file by path
    with the reason: missing, extra, differs from its source, or laid from another commit.
  metrics: >
    None added.
  traces: >
    The lay-down writes .veldo/engine-laid.json: the source commit, the source tree digest and each laid
    path with its sha256. It is the record the check and every consumer read, and it is untracked.
  error_taxonomy: >
    Two named refusals. engine_not_laid: a consumer started in this repository and found no laid engine
    (a fresh clone that has not run the lay-down). engine_stale: the laid engine's record names a source
    digest other than the current engine/ tree, or a laid file no longer matches its recorded sha256. Both
    name the command that fixes them. Neither is ever turned into a warning: the gate is red and the guard
    refuses, as for any other missing gate input.
acceptance_criteria:
  - id: AC1
    text: >
      One copy. engine/ is the only tracked home of every engine file. Each root file that today is a
      byte-identical copy of an engine file (247 .veldo Python modules, their non-Python engine assets
      such as capabilities.yaml and the examples, the shared scripts under scripts/ that engine/scripts
      also carries, bin/veldo, and the pack copy packs/claude/scripts/veldo-guard.sh) is removed from git
      and its path is listed as ignored. What stays tracked at the root is only what is legitimately local
      and has no engine counterpart or is a declared per-repository file: policy.yaml, architecture.yaml,
      CLAUDE.md, the specs template and index, scripts/verify.sh, the decisions, the run records, and the
      repository-only modules (lessons.py, release.py, request_doorbell.py and the tracker_* modules).
      .veldo/policy.yaml names each protected engine file once, at its engine/ path. CLAUDE.md states
      the new rule in place of "synced copies".
    falsified_by: >
      A unit row lists every tracked file outside engine/ and fails if any is byte-identical to a tracked
      file inside engine/ at its lay-down destination, naming both paths. A registered mutation that
      commits one engine module back at the root (git add -f of .veldo/validate.py) reds it. A second row
      fails if .veldo/policy.yaml names any path twice under a root and an engine/ spelling; a mutation
      that adds scripts/agent_sandbox.py beside engine/scripts/agent_sandbox.py reds it.
  - id: AC2
    text: >
      Every consumer reads the produced engine and passes unchanged. The repository's own instance is laid
      down from engine/ by the same lay-down code an adopter's install runs (init_scaffold's file list and
      runtime asset rule, extended to the files this repository runs), invoked by a single command and by
      the gate as its first step, before any stage reads .veldo/ or scripts/. No symlink is used: 121
      engine modules compute their repository root from Path(__file__).resolve(), so a linked root module
      would resolve into engine/ and read engine/'s specs and policy instead of the repository's, and the
      lay-down already refuses symlinks in what it lays. The consumers that must keep working, with no
      change to their own suites' rows: the gate (scripts/verify.sh and every stage, including the guard
      and the authority checkout it runs its helpers from), init and the pack assembler (engine/.veldo/
      pack.py and scripts/publish.py, which already read engine/), factory setup and its upgrade of an
      earlier installation (VELDO-0189, which lays its engine closure from the templates), the published
      zip packs, and an adopter repository initialised from a pack. A consumer that starts in this
      repository with no laid engine, or a stale one, refuses engine_not_laid or engine_stale by name
      instead of running.
    falsified_by: >
      The full gate is green on the change with the root copies gone, every suite present with the same
      row names and counts as on the base commit (a row list diff in the proof bundle, empty but for the
      retired byte-identity rows of AC4). scripts/check_install_and_run.py (VELDO-0007) composes a pack,
      initialises a fresh repository from it and requires its gate green, unchanged. The VELDO-0189
      upgrade suite upgrades an earlier installation green, unchanged. Two registered mutations from a
      green baseline: deleting the laid .veldo/validate.py makes the gate's first stage red with
      engine_not_laid; editing one byte of a laid file makes it red with engine_stale naming that file.
  - id: AC3
    text: >
      One edit reaches every installed engine. A change to a file under engine/ is the whole change: the
      next lay-down carries it to the repository's own instance, the next pack composition carries it to
      every pack, and the next setup run carries it to an installation, with no second file edited by hand.
      The lay-down is idempotent (a second run with no source change writes nothing) and removes a laid
      file whose source was deleted.
    falsified_by: >
      An integration row on a scratch copy of the repository edits one engine module under engine/ only,
      runs the lay-down, the pack composition and a setup upgrade of a fixture installation, and finds the
      edit byte for byte in the root instance, in every composed pack and in the installation; a second
      lay-down reports zero files written. A registered mutation that makes the lay-down skip files it
      already holds reds the row because the root instance keeps the old bytes. A row that deletes a source
      module and lays down again fails if the laid copy remains.
  - id: AC4
    text: >
      The old sync checks are retired with no coverage lost. scripts/check_template_sync.sh is deleted and
      CHECK_extra runs the produced engine check in its place: every laid file matches its source by
      sha256, nothing is laid that the source does not have, nothing the source ships is missing, and the
      record names the current source digest. Its fail closed floor on an implausible count is kept. The
      per-suite rows that compare a root .veldo file to its engine/ twin (64 such comparisons across 26
      suites, for example suite 08's "is byte-identical root vs engine" rows and suite 06's two
      capabilities.yaml copies) are removed, each listed by suite and row name in the proof bundle with the
      check that now covers it. Rows that compare a pack's engine file with the base (pack.py's drift
      check) stay, because composition is still a copy.
    falsified_by: >
      The mutation that taught the template sync its derived pairs (VELDO-0001's suite 17 note: invert
      engine/.veldo/toe_corpus.py so the corpus always reports itself usable) is re-run against the new
      check: editing the laid copy only reds it as differs, and editing the source only without a lay-down
      reds it as engine_stale. A mutation that makes the check pair nothing reds it through the count
      floor. The proof bundle's table maps each removed byte-identity row to the failure the new check
      reports for the same edit, run once per row.
required_evidence: [unit, integration]
rollback: >
  Revert the commit. The root copies return as tracked files byte-identical to engine/ at that commit,
  scripts/check_template_sync.sh and the per-suite byte-identity rows return, and the ignore entries and
  the laid record go. Nothing outside the repository changes: packs, setup and installed projects read
  engine/ before and after, so no installation or adopter needs migrating.
---

## Intent

Every engine change in this repository lands twice, once under engine/ and once at the root, and the gate
spends a check and dozens of suite rows proving the two still match. Since 2026-09-01, 921 commits touched
engine/.veldo, each mirrored at the root; the lint stage reads about a third of its Python twice. The copy
exists so the repository runs what an adopter installs. That property is better kept by laying the root
instance down from engine/ with the adopter's own installer than by hand-keeping a second copy and checking
it.

## Context

Measured on main at afa292f0 and in the weight audit
(~/projects/myday/research/veldo-core-weight-audit-2026-11-07.md item 3): 247 of 255 root .veldo Python
modules are byte-identical to engine/.veldo (about 119,150 lines); 20 scripts in engine/scripts are
identical to scripts/; bin/veldo equals engine/bin/veldo; packs/claude/scripts/veldo-guard.sh equals the
guard. scripts/check_template_sync.sh compares 303 pairs today, with 6 declared per-repository files.
.veldo/policy.yaml names 22 engine/ paths beside their root twins.

Which copy each tool reads today:

- engine/ (the source already): init_scaffold's DEFAULT_TEMPLATES, .veldo/pack.py and scripts/publish.py
  (compose_packs), factory setup and its upgrade (VELDO-0189) through the template closure, and
  scripts/check_install_and_run.py, which composes a pack and initialises a fresh repository from it.
- the root copy: scripts/verify.sh and every gate stage (VELDO_AUTHORITY is the checkout's root, so
  .veldo/candidate_git.py, validate.py, policy_check.py and the gate scripts are root files),
  scripts/update_index.py, the guard hook, and every suite that imports a .veldo module.
- both: the template sync check, 64 byte-identity comparisons in 26 suites, and the engine census
  (scripts/engine_census.py governs .veldo/*.py and engine/.veldo/*.py).

Why engine/ is the source and not the root: it is already declared the canon (CLAUDE.md, the template
sync header); it is the shape every adopter receives, so every outward consumer already reads it; and it
holds only engine files, while the root .veldo mixes them with this repository's policy, decisions and run
records. Choosing the root would mean rewriting the pack assembler, publish, init and setup to filter local
files out, and every adopter would receive a tree that this repository never laid down.

Why a lay-down and not symlinks: 121 engine modules locate their repository from
Path(__file__).resolve(), which follows a link into engine/; the gate resolves its own path with pwd -P;
the lay-down refuses symlinks in what it lays; and zip packs, pip style installs and a vendored copy
copied by another tool do not carry links the same way on every host. A lay-down is one behaviour for
every consumer.

The core repository's vendored engine (audit item G: 31 of its 42 .veldo modules differ from engine/) is
not changed here. Once this lands it is fed the same way: its local changes are upstreamed into engine/,
and core's .veldo engine files are laid by the same installer from a pinned Veldo commit, recorded in its
engine-laid record, instead of being edited in core.

## Out of scope

The core repository's vendored copy and its upstreaming (a later spec, as above). The pack AGENTS.md
copies, which are method text and not engine code. Any change to what an engine module does. The gate's
confinement (audit item 4) and the run records' tracking (audit item H). Renaming any historical proof
bundle path that names a root copy: old bundles stay as recorded.

## What the reviewer judges

- engine/ is the only tracked copy; nothing at the root, in scripts/ or in a pack is a hand copy of an
  engine file, and the policy names each protected file once.
- The root instance is produced by the adopter's own lay-down code, not a second installer written for
  this repository.
- A missing or stale laid engine stops the gate and the guard by name; nothing runs a stale copy.
- Every removed byte-identity row is matched to the failure the new check reports for the same edit, and
  the suites keep their row names and counts otherwise.

## History

2026-11-07: drafted on the owner's agreement, Telegram 39685 and 39686, to the weight audit's item 3
(~/projects/myday/research/veldo-core-weight-audit-2026-11-07.md): keep one copy of the engine.

2026-11-07: ready on the owner's approval, Telegram 39696 ("Ok") to the summary in 39695.
