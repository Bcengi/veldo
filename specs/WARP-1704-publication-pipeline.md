---
schema: veldo.spec/v1
id: WARP-1704
title: The public tree is DERIVED from a declared manifest and proven offline, because a curated
  copy is a judgement repeated by hand every release and a leak is permanent the moment it is pushed
status: ready
risk: high - it is the one step that moves bytes from a private repository to a public one. A miss
  is not a bug that can be fixed forward: a leaked customer name, an internal plan or a person's
  details are permanent the moment they are pushed, and remain in history after any later deletion.
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0017
work: W4
depends_on: [WARP-1703]
placement: [distribution]
footprint:
  - "scripts/publish.py"
  - "scripts/check_docs.sh"
  - ".veldo/private_names.txt"
  - "engine/.veldo/private_names.txt"
  - "scripts/suites/*"
  - "specs/WARP-1704-publication-pipeline.md"
  - "specs/index.md"
acceptance_criteria:
  - id: AC1
    text: >
      DERIVED FROM A DECLARED MANIFEST, NEVER CURATED. The public tree is produced by applying an
      INCLUDE manifest of path globs to the private repository, so what ships is a decision recorded
      once and re-applied identically, not a judgement a person repeats each release. A path that
      matches no include rule is ABSENT BY DEFAULT: the pipeline never has to know what is secret,
      only what is publishable, because a default-deny manifest fails safe when the repository grows
      a directory nobody remembered to exclude.
  - id: AC2
    text: >
      IDEMPOTENT AND OFFLINE. Running the pipeline twice over an unchanged repository produces
      byte-identical trees, proven by comparing the two, and it touches no network and no public
      repository: it writes to a scratch target given as an argument and refuses to run without one.
      A pipeline that cannot be run repeatedly and compared cannot be trusted to be reviewed once.
  - id: AC3
    text: >
      THE LEAK SCAN READS THE OUTPUT, NOT THE INPUT. Every file of the PRODUCED tree is swept for
      the private-name list, because a scan over the source proves nothing about what the copy
      actually contains. The name list has ONE definition, shared with the gate's genericity sweep,
      so a name added for one is added for both and the two can never disagree about what private
      means.
  - id: AC4
    text: >
      THE NEGATIVE TEST IS THE POINT. A scan that has never caught anything is not evidence. The
      proof seeds an internal artifact carrying a private name into the source, runs the pipeline,
      and requires the scan to REFUSE and to NAME the file. A green run over a clean tree is
      reported alongside it, so the pass is a measurement rather than an absence.
  - id: AC5
    text: >
      IT REFUSES RATHER THAN CLEANS. On any finding the pipeline fails and writes nothing further:
      it does not strip the offending line and continue. A cleaner would make the output depend on a
      substitution nobody reviewed, and would train us to ignore the finding it just repaired.
  - id: AC6
    text: >
      PACKS SHIP COMPOSED. A published pack is the base plus that pack's own files, so an adopter
      who takes one directory has a working gate, which is what packs/README.md now tells them.
      Composition happens at publication, so the private repository keeps ONE base and no copies.
---

## Outcome

A public tree that can be produced by anyone on the team, twice, with identical results, and whose
safety rests on a manifest and a scan that has been watched to fail rather than on care.

## The design problem, which is not the obvious one

The obvious problem is "do not leak". The real problem is that a curated copy is a judgement repeated
by hand at every release, and judgement degrades with familiarity: the tenth release is copied by
someone who has stopped reading. So the tree is DERIVED, and the manifest is DEFAULT DENY. A new
private directory is invisible to the public tree until somebody deliberately includes it, which is
the safe direction to fail in.

The second problem is that a leak is not reversible. Deleting a pushed file leaves it in history and
in every clone made in the meantime. That is why AC5 refuses instead of cleaning: at the moment the
scan fires, the correct action is a person deciding, not a machine editing.

## Why the scan reads the output

A sweep over the source can pass while the copy carries the same string, because the copy is made by
different code than the sweep reads. Scanning the produced tree removes that gap: what is checked is
exactly what would be pushed.

## What is deliberately not solved here

This does not push anything. Producing a public tree and publishing it are two acts, and the second
one is two-keyed at W6. The pipeline's only output is a directory on this machine.
