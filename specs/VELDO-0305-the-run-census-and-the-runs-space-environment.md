---
schema: veldo.spec/v1
id: VELDO-0305
title: "The run census and the run's space environment"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0301]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_launch.py"
  - ".veldo/control_launch.py"
  - "scripts/suites/*_veldo_0305_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0305-the-run-census-and-the-runs-space-environment.md"
  - "specs/index.md"
  - "proof/VELDO-0305/**"
behavior_bearing: true
observability:
  logs: >
    Each census writes the items it declared and each size with the event it was measured at.
  error_taxonomy: >
    None of its own. An untracked path git does not ignore is never recorded as an item; it makes the
    worktree unique work.
acceptance_criteria:
  - id: AC1
    text: >
      At each run event every ignored folder git reports in the run's worktree that a committed ignore
      file of the project or a declared pattern covers becomes a build output item, whatever its name and
      depth; a keep entry is left out, and so is a folder only a personal ignore rule covers
    falsified_by: >
      Match the name target; the row's folder named otherwise has no item and fails
  - id: AC2
    text: >
      An untracked path git does not ignore is never recorded as build output and makes the worktree
      unique work. So does an ignored path that no committed ignore file and no declared pattern covers,
      and a loose ignored file outside every build output folder
    falsified_by: >
      Record every untracked folder; the row's new source folder becomes build output and fails
  - id: AC3
    text: >
      The run's temporary folder and build variables point at folders declared before the worker starts
    falsified_by: >
      Set the variables without declaring; the row finds the build root with no item and fails
  - id: AC4
    text: >
      In a worktree reconcile adopted, only folders matching the project's declared patterns are recorded
    falsified_by: >
      Apply the ignored-folder rule to adopted worktrees; the adopted fixture's ignored data folder
      becomes build output and fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. Runs leave build output with no record.
---

## Intent

An agent's own commands create build folders Veldo never sees being made. At each run event the receiver
reads what the run left: every ignored folder git reports in the run's worktree becomes a build output
item, whatever its name. The run's temporary folder and build root are declared before the worker starts.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 6.3 (what a run is given, and the
census) and 8.1 (steps 4 and 7). Section 12 of the design holds the ticket itself; its acceptance criteria
and falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Receiver.

Build order. It is built after 0301, in any order with the other tickets of that step (0302, 0303, 0305 to
0314, 0323, 0324, 0328, 0329, 0333, 0335, 0336, 0337 and 0341). The design states no dependency for this
ticket, so depends_on holds the step before it in the build order.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
- 2026-11-13: amended for the owner's rule that no work is ever lost (Telegram 41209), design section 0.
  AC1: an ignored folder is build output only when a committed ignore file of the project or a declared
  pattern covers it; a folder only a personal ignore rule covers is left out. AC2: an ignored path that
  nothing of the project covers, and a loose ignored file outside every build output folder, make the
  worktree unique work, because git's non-forced worktree remove deletes ignored files without refusing.
  Both falsifiers are unchanged. Rule 5's reading of such a path is VELDO-0347 AC1.
- 2026-11-14: built. No acceptance criterion changed. What the build decided, recorded here because
  the criteria do not say it:
  - Where it is. Three functions in control_launch.py, the receiver's module and the one engine file
    in this footprint: space_census, space_run_folders and space_environment. The receiver calls the
    second from its one spawn, before the execution record and before any process is started, and the
    first from its end, before it sends run finished. Neither deletes anything: the census declares,
    confirms and measures, and what it declares goes later by Signal's removers. Nothing in the
    engine builds `space` yet (VELDO-0303's note), so until that is wired a run is given what it was
    given before.
  - Committed means in HEAD and unchanged. An ignore file covers a folder only when the worktree's
    HEAD holds that file and the file on disk is that very content. A rule somebody added and has not
    committed covers nothing, so a worker cannot turn a folder of notes into build output by editing
    the ignore file. This is narrower than the remover's last look, which asks only that git tracks
    the file; the two agree again once the rule is committed.
  - A keep entry holds the folder it is, a folder inside it, and a folder it lies in: when the
    project keeps models/weights and git reports models/ as one ignored folder, the whole folder is
    left out, because removing it would take the kept path with it.
  - A declared pattern is matched against an ignored folder's own name, as the remover matches it.
    A folder git does not ignore is never recorded, whatever its name (AC2).
  - The census is for a worktree a live item records, of the kind worktree or agent repository. One
    no item records gets nothing, and the answer says not_in_ledger. New items are owned by the run
    when the receiver names it, so run finished reaches them, and by the worktree's owner otherwise.
  - The folders. The temporary folder is <first scratch root>/runs/<the dispatch's digest>, a
    scratch item. The build root, for a project that declares build variables, is <first build
    root>/<the worktree's name>-<a digest of its path>, a build output item; one a live build output
    item of the same scope records is used as it is, so it passes from one run of a worktree to the
    next. A folder that is already there with no live item is never taken over, and the launch is
    refused as unavailable_service:space_ledger, as it is when the ledger refuses or cannot be
    reached. A build variable that names a variable of the launch (a reserved name, a factory name, a
    delivered credential) is refused as invalid_input:space_build_variable.
  - Who is given nothing: a worktree no item records, a station the ledger has no run for
    (coordination, turn), an engine on another host, and a run in the confined runner, which has a
    temporary folder of its own and may write nowhere outside its worktree. Their environment is
    unchanged, and what such a run builds stays in the worktree, where the census reads it.
  - An engine's environment is stripped by the trusted wrapper at the exec, the temporary folder
    variable included, so the values are also written into what the wrapper installs again.
  - Not built here: the run's label and compose project name and the census of Docker objects
    (VELDO-0306), the order census, Signal, release and the conclusive end (VELDO-0308), the gate's
    census at a verdict (VELDO-0309), and rule 5's own reading of ignored work (VELDO-0347 AC1).
- 2026-11-14: fixed from the independent review (verdict FIX, findings 1 to 5). No acceptance
  criterion changed. What changed, each with a row on a real repository and a registered falsifier:
  - Committed means the project's, not the run's (finding 1). An ignore file covers a folder only
    when the commit the worktree's item records as its start holds it, the worktree's HEAD holds
    that very content and so does the disk. A rule the run added or changed, committed on its own
    branch or not, covers nothing, and neither does the rest of that file: a run that touches an
    ignore file leaves its ignored folders as work, which costs space and loses nothing. A worktree
    whose item records no start commit gets the declared patterns only. This replaces "committed
    means in HEAD and unchanged" above; row ac1/uncommitted-rule now ends with the run's commit
    still covering nothing, and row review/run-commits-ignore-rule is the reviewer's case.
  - A negation keeps the folder (finding 2). When a negation pattern of any .gitignore on disk
    from the folder's directory up to the top could match the folder or a path inside it, the
    folder is work, whole. The match is wider than git's on purpose; a folder that cannot be
    walked is work. Row review/negation-keeps-folder.
  - A personal excludes file is never read (finding 3). Every census read sets core.excludesFile
    to nothing, and a rule read from a per-directory ignore file covers only folders inside that
    file's directory. Row review/local-excludes-file.
  - The refusals (finding 4). A folder that is there with no item is refused as
    invalid_state:space_folder_unrecorded, one a live item records as something else as
    invalid_state:space_folder_recorded_otherwise; the detail names the folder, and the receiver's
    refused event carries the detail for these codes. The dispatch record holds the code only: its
    refuse command has no detail field and control_dispatch.py is outside this footprint. A ledger
    that refuses or cannot be reached keeps unavailable_service:space_ledger. Row
    review/refusal-names-the-folder.
  - The temporary folder (finding 5) is <first scratch root>/run-scratch/<the dispatch's digest>,
    and one that is the run directory, holds it or lies in it is refused as
    invalid_state:space_folder_run_directory with nothing declared. Row
    review/scratch-apart-from-run-directory.
  - Left open, as the review states them: finding 6 (a reused build root keeps its first run as
    owner; build output, so no work is lost), the remover's last look, which has finding 1's hole
    and is VELDO-0347's, and a build output item declared before a run changed the ignore file,
    which stays an item.
- 2026-11-14: fixed from the re-review (verdict FIX, finding 2-b). No acceptance criterion changed.
  - A negation keeps the folder wherever its owner wrote it. Beside every .gitignore from the
    folder's directory up to the top, the census now reads the negation patterns of the
    repository's own exclude file (resolved with git rev-parse --git-path info/exclude, so a
    linked worktree reads the common directory's) and of every .gitignore inside the folder, at
    any depth, tracked or not. Git reads neither once the folder is excluded; the census does,
    because a negation only ever keeps. A pattern that could match the folder or a path inside
    it, or a file that cannot be read, makes the folder work, whole. A positive rule in either
    place still covers nothing. The folder is now always walked, where before it was walked only
    when a negation above it was found. Rows review/negation-in-info-exclude and
    review/negation-in-nested-ignore-file, with three registered falsifiers.
  - The re-review's finding 7 (the first fix commit carried four files of VELDO-0306 without
    their canon) was closed by VELDO-0306's own commits: the template sync check passes and
    suites 133 to 141 have no red canon row on this tree. The proof's suite list is taken again
    from the committed tree.
  - Still open: finding 6, as recorded above. A negation in a personal excludes file that
    core.excludesFile names is not read, as that file is never read at all. And the re-review's
    note 1: the recorded start commit must be a commit the project landed, never the tip of a
    run's branch, which the writer of those records (VELDO-0302, VELDO-0347) has to keep.
