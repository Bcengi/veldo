---
schema: veldo.spec/v1
id: VELDO-0225
title: A file a case copies but never reads again is keyed by its presence, not its content
status: ready
risk: high
owner: Dmitry Grinberg
human_approval: required
lane: standalone
depends_on: [VELDO-0207, VELDO-0217, VELDO-0222, VELDO-0224]
placement: [enforcement]
protected_paths: ["scripts/case_trace.py", "engine/scripts/case_trace.py", "scripts/case_inputs.py", "engine/scripts/case_inputs.py", "scripts/case_reuse.py", "engine/scripts/case_reuse.py", "scripts/propose_case_inputs.py", "scripts/mutation_case_inputs.json"]
footprint:
  - scripts/case_trace.py
  - engine/scripts/case_trace.py
  - scripts/case_inputs.py
  - engine/scripts/case_inputs.py
  - scripts/case_reuse.py
  - engine/scripts/case_reuse.py
  - scripts/propose_case_inputs.py
  - scripts/mutation_case_inputs.json
  - scripts/check_teeth_mutations.py
  - scripts/suites/*_veldo_0225_*.py
  - scripts/suites/manifest.json
  - scripts/suites/requires.json
  - specs/VELDO-0225-a-copied-file-nobody-reads-is-keyed-by-presence-not-content.md
  - specs/index.md
  - proof/VELDO-0225/*
behavior_bearing: true
observability:
  logs: The proposer names, per case, how many declared files are content inputs and how many are presence inputs, and for each presence input the copy that made it one.
  metrics: Per engine module, the share of declared cases that read it by content; the measured share of cases a landing that changes one engine module re-runs.
  traces: Each presence input in a declaration names its copy destination and the trace digest that shows the destination unread.
  error_taxonomy: A copy the tracer cannot follow (a read and write loop, an unresolved descriptor), a destination that is later opened, renamed or linked, or a listing that reveals contents all make the source a content input; nothing is ever downgraded by judgment.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: the tracer records copy provenance: a sendfile or copy_file_range call whose source and
      destination descriptors resolve to paths makes the destination a copy of the source; a
      source whose every copy is never opened, renamed, linked or mapped again by any traced
      process, and which is not itself read any other way, is a presence input; every other read
      file stays a content input. Set: a fixture case that copies a module tree with shutil and
      imports one module from the copy, one that copies with a read and write loop, one that renames
      a copy, and one that hashes the copied tree. Completeness: row presence-inputs/provenance
      requires exactly the never-reopened copies of the first case to be presence inputs and every
      file of the other three to be content inputs.
    falsified_by: >
      Ignore opens of a destination made after the copy. Registered mutant
      presence225-reopen-ignored must fail presence-inputs/provenance.
  - id: AC2
    text: >
      Claim: a presence input is keyed by its name, mode, size and modification time and is still
      present in the snapshot with its current bytes; a content input is keyed by its bytes as today.
      The snapshot writer (case_inputs.freeze) sets every file's modification time to one fixed
      value, so the time a stat of a copy shows is the same in every run and carries nothing of the
      source's content (shutil.copy2 copies that time to the copy). So an edit to a module a case
      only copies changes no key of that case unless the edit changes the module's size or mode,
      and an edit to a module it reads by content misses it. Set: the fixture case of
      AC1, an edit to a copied-only module that keeps its size, one that changes its size, and an
      edit to the imported module. Completeness: row presence-inputs/keys requires the first edit to
      hit and the other two to miss.
    falsified_by: >
      Key presence inputs by name only. Registered mutant presence225-size-unkeyed must fail
      presence-inputs/keys.
  - id: AC3
    text: >
      Claim: a presence classification is rechecked on every run that would publish, never trusted
      from the proposal alone: the provenance pass runs again on that run's baseline, no-op and
      mutant traces, and if any copy of a presence input is opened, renamed, linked, mapped or
      listed there, the case is declaration_stale (VELDO-0224): it runs fresh and nothing is
      published. Set: a fixture case whose declaration was proposed when it imported nothing from
      its copy, run after an edit makes it import one copied module. Completeness: row
      presence-inputs/rechecked-each-run requires the edited case stale, fresh and unpublished.
    falsified_by: >
      Run the provenance pass at proposal time only. Registered mutant presence225-proposal-only
      must fail presence-inputs/rechecked-each-run.
  - id: AC4
    text: >
      Claim: the effect is measured, not assumed. After the proposal pass of VELDO-0217 the proof
      records, for each engine module under .veldo/, the share of declared cases that read it by
      content, and replays the last 37 landings on main against the new declarations to state the
      share of cases each would re-run. Set: the full proposal set. Completeness: the replay uses
      the same grouping by specification id as VELDO-0217's estimate and reports both figures side by
      side for every landing.
    falsified_by: >
      Report the share from presence and content inputs together. The replay's engine-module
      landings then show the old figure of about 73 percent and the comparison check fails.
required_evidence: [unit, integration]
rollback: Revert the provenance rule; every read file is a content input again, as under VELDO-0207.
---

## Intent

Under VELDO-0217's keys, 14 of the last 37 landings, those that change a shared engine module under
.veldo/, would re-run about 73 percent of the declared cases, about 40 to 45 minutes per landing.
The reason is visible in VELDO-0207's traced read sets: about two thirds of sampled cases read 233 of
the 241 engine modules, because their fixtures copy the whole engine directory into a fixture
repository (shutil.copytree of ROOT/.veldo appears in suites 12, 15, 101 and 109 among others), and a
copy reads every byte. Most of those copies are never read again: the case imports a handful of the
copied modules. A copy whose destination nobody reads cannot carry its source's content into the
result, but its presence can (a listing, an existence check, a size).

This design targets the engine-module landings without touching a fixture, a case or an assertion,
and under the owner's decision D2: the downgrade from content to presence is made only from what the
trace shows, and any doubt keeps the content key.

## Design

shutil.copy2, which copytree uses, copies through os.sendfile on Linux, and the coordinator's trace
already records system calls with resolved descriptor paths, so the source and destination of each
copy are in the trace. case_trace.py adds the provenance pass; case_inputs.py splits a declaration's
files into content and presence inputs; case_reuse.py keys each class as AC2 says. The snapshot is
unchanged except that its files carry one fixed modification time: every declared file is present
with its real bytes, so the case runs as before. Because a later edit can make a case read a copy it
used to ignore, the classification is rechecked on every publishing run (AC3).

What remains a content input: anything the case opens to read other than as a copy source, every
source of a copy whose destination is opened, renamed, linked or mapped afterwards, every copy the
tracer cannot follow, and every file under a directory whose listing a case uses to read contents.

Expected saving: unknown until AC3's replay. If an engine-module landing then re-runs only the cases
that import the changed module, it falls from about 73 percent of cases toward the 3 to 20 percent of
suite-only landings, which would bring those landings from about 40 to 45 minutes to about 15 to 25.
The replay decides; this spec claims no number before it.

## Out of scope

Changing fixtures to copy less; the cases and their assertions; suite result reuse.

## What the reviewer judges

Normal use: proposals and landing gates with reviewed declarations. Threat model: as in VELDO-0207.
Out of review scope: none beyond VELDO-0207's; copies the tracer cannot follow are content inputs by
rule, so no class of copy is left to judgment.
