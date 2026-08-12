---
schema: veldo.spec/v1
id: VELDO-0007
title: Install and run, proven from the artifact an adopter receives - compose the packs, initialise a
  fresh repository from a COMPOSED pack, and require that repository's own gate to be green
status: ready
risk: standard - it adds one gate stage that composes, installs and runs a nested gate, and changes no
  product behaviour. It is NOT low because it is the only check whose subject is the artifact a
  stranger receives rather than this repository, and 1.0 shipped UNINSTALLABLE precisely because every
  test ran against the one tree nobody installs. It is not high because it writes only inside a
  temporary directory and refuses no change except the one it is about
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0018
work: W6
placement: [enforcement]
footprint:
  - "scripts/check_install_and_run.py"
  - "scripts/verify.sh"
  - ".veldo/capabilities.yaml"
  - "engine/.veldo/capabilities.yaml"
  - "scripts/suites/24_veldo_0007_install_and_run.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0007-install-and-run-from-the-artifact-an-adopter-receives.md"
  - "specs/index.md"
protected_paths:
  - "scripts/verify.sh"
behavior_bearing: true
observability:
  logs: >
    One line per pack: the pack name, the file count init laid down, the pack directory it installed
    FROM, THE SCAFFOLDER PATH IT ACTUALLY LAUNCHED with whether that tree carries an engine/
    directory, and whether that repository's own gate went green, with the nested gate's own last
    lines quoted on failure so a reader sees WHY the adopter's gate failed rather than only that it
    did. The executed path is on the line because the line used to name only the directory handed in,
    which read identically whichever scaffolder ran and made the engine/ clause a provenance claim
    that could be false while sounding measured. The stage prints the
    composed pack set it derived and the count, so a run that composed nothing is visible rather than
    silently clean.
  error_taxonomy: >
    COMPOSE_FAILED (the publisher could not produce a tree at all), NO_PACKS_COMPOSED (it produced a
    tree with no composed pack, which would make every later assertion vacuous), INIT_FAILED (init
    refused or laid nothing from a composed pack - the 1.0 defect exactly) and ADOPTER_GATE_RED (the
    scaffolded repository's own gate failed). Each is separate because each names a different broken
    stage of the adopter's first ten minutes, and the last one is the only one that can be a defect in
    the adopter's tree rather than in ours.
acceptance_criteria:
  - id: AC1
    falsified_by: >
      Point the installer at this repository's own .veldo/init_scaffold.py instead of the COMPOSED
      pack's copy in scripts/check_install_and_run.py, and the assertion that the scaffolder was run
      from a tree containing no engine/ directory must go red. The tree asserted is the one the
      EXECUTED path belongs to, read out of the argv the child was handed: a record of the directory
      the installer was PASSED leaves this mutation green, which is how it shipped.
    text: >
      IT INSTALLS FROM THE COMPOSED PACK, NOT FROM THIS REPOSITORY, AND THAT IS THE ENTIRE POINT. In
      this repository the template base is a separate tree at engine/; in a composed pack the base has
      been laid INTO the pack, so the pack root IS the template source and there is no engine/ at all.
      1.0 shipped uninstallable because init assumed the first shape, and every test ran against this
      repository - the one tree nobody installs. So the stage runs the COMPOSED PACK'S OWN
      init_scaffold.py, and asserts the tree it ran from has no engine/ directory, because that
      absence is the condition that broke. THE TREE IT RAN FROM IS DERIVED FROM THE EXECUTABLE THE
      CHILD WAS HANDED, never from the directory the installer was passed: those two agree in every
      case except the one this criterion exists to catch, which is why a review pointing the launch
      at this repository left the old rows green.
  - id: AC2
    falsified_by: >
      Replace the derived pack set in scripts/check_install_and_run.py with a hand-written list naming
      one pack, and the assertion that the installed set EQUALS every pack the publisher composed must
      go red.
    text: >
      THE PACK SET IS DERIVED FROM WHAT THE PUBLISHER COMPOSED, NEVER TYPED. Every pack the publisher
      produces is installed and run, and the stage asserts SET EQUALITY between what it installed and
      what the publisher composed. A hand-kept list is the defect this repository has shipped twice:
      seven listed pairs guarded nine modules that arrived later. FAILS CLOSED ON A VACUOUS RUN: if
      the publisher composes NO pack, that is NO_PACKS_COMPOSED and the stage is red, because a loop
      over an empty set passes while proving nothing.
  - id: AC3
    falsified_by: >
      Ignore the nested gate's exit status in scripts/check_install_and_run.py and report success
      whenever init laid files, and the assertion that a scaffolded repository whose own gate FAILS
      makes the stage red - driven by writing an INVALID STARTER PLAN into the composed pack, which
      init lays down happily and the adopter's own gate then refuses - must go red. Corrupting a
      required substrate file does NOT drive this row, and this text used to say it did: that
      corruption breaks init before the gate is ever consulted, so the failure is INIT_FAILED and
      that row accepts either name. The suite carries both; only the invalid starter plan isolates
      the gate's exit status.
    text: >
      THE ADOPTER'S OWN GATE MUST GO GREEN, AND THE PROOF IS A BROKEN ONE GOING RED. Laying files down
      is not installing: 1.0 laid nothing and said so, but a scaffolder that lays a repository whose
      gate is red is worse, because the adopter's first act fails and the failure looks like their
      fault. The stage runs the scaffolded repository's OWN scripts/verify.sh and requires exit zero,
      and the suite proves that assertion has teeth twice over inside a real composed pack: by
      corrupting a required substrate file, which breaks init and must fail by one of the two named
      failures, and by writing an invalid starter plan, which init lays down happily so the ONLY
      thing that can refuse it is the adopter's own gate. The second is the row that isolates the
      exit status; the first alone left a deleted gate check green. On failure the nested gate's last
      lines are quoted, because "their gate failed" without the reason sends nobody anywhere.
  - id: AC4
    falsified_by: >
      Make scripts/check_install_and_run.py write anywhere outside its temporary directory - into
      $HOME, or into a git-ignored path inside the repository, which are the two blind spots that let
      this criterion ship unasserted - or leave its temporary directory behind, or detach its children
      with start_new_session=True, and the assertion that the inventory of the repository under check
      and of the process's own HOME is identical across the run must go red.
    text: >
      IT TOUCHES NOTHING OUTSIDE A TEMPORARY DIRECTORY. The stage composes, installs and runs a nested
      gate, which is a great deal of writing, and every byte of it lands under a temporary directory
      that is removed. THE SUITE OBSERVES THE WRITES RATHER THAN A PROXY FOR THEM: it runs the stage
      in a sandbox where every root it could legitimately write to is declared - its own copy of the
      working tree, its own HOME, its own TMPDIR - and requires a recursive inventory of path, size,
      modification time and digest over the first two to be identical across a run that demonstrably
      did the work, plus the same inventory over THIS repository across a real in-process run. A
      comparison of `git status --porcelain` was the first attempt and it is blind twice over, to
      every path outside the repository and to every ignored path inside it, so a review wrote into
      $HOME on every call and clobbered .veldo/trackers.json with every row still green. It also makes
      no network call and starts no detached process, the second asserted on the launch call's own
      KEYWORD ARGUMENTS through the one helper every child goes through, because a keyword argument
      has no identifier for a scan to find.
  - id: AC5
    falsified_by: >
      Declare the stage as `na` in scripts/verify.sh, or name the script in an `na:` slot without
      requiring it, and the assertions that this repository's gate carries it as `required:` and that
      mentioning it equals requiring it must go red.
    text: >
      IT IS A REQUIRED CATALOG ITEM IN THIS REPOSITORY'S GATE, because a proof that only runs when
      somebody remembers is the state this item exists to leave. LANDED, not pending: Dmitry approved
      the protected-path edit on 2026-08-12 and it sits in the EXISTING packaging slot, because
      composing the published packs and proving a stranger can install and run them IS packaging
      verification, and a new catalog name would have changed a vocabulary the approval did not cover.
      THE CRITERION IS UNCONDITIONAL AND ITS REPORTING BRANCH IS GONE, which driving forced: while the
      posture was derived from the live gate, REMOVING the registration entirely satisfied both
      branches, so the enforcing state could be silently reverted. A posture cannot catch its own
      removal. IT IS DELIBERATELY NOT IN THE SHIPPED
      TEMPLATE, and that was CORRECTED BY THIS REPOSITORY'S OWN CAPABILITY-HONESTY CHECK: the script
      does not ship to an adopter, and an adopter does not publish packs, so a slot demanding it in
      their gate would be a required check they cannot run. The capability is marked scope: repo-only
      for the same reason. scripts/verify.sh is a PROTECTED PATH: this change edits it, which is why
      this spec declares it and why landing that edit needs the approval protection implies.
required_evidence: [unit]
rollback: >
  Declare the slot `na` with a reason and delete scripts/check_install_and_run.py. Nothing imports it
  and no other stage depends on it, so the retreat is one catalog line and one file, and the previously
  proven install path is unaffected because the stage only observes it.
---

# Install and run, from the artifact an adopter receives

## The defect this makes impossible to ship again

Veldo 1.0.0 could not be initialised by anyone. `/veldo:init` failed from every composed pack with
"gate template drift" and laid nothing down. The cause was a shape difference: in this repository the
template base is a separate tree at `engine/`, and in a composed pack the base has been laid INTO the
pack, so the pack root is the template source and there is no `engine/` directory at all.

The reason it shipped is recorded in one sentence in PLAN-0018's ledger: **nothing had ever run init
from a composed pack, because every test runs against this repository, which is the one tree nobody
installs.**

## Why this is cheap enough to be a required stage

Measured on 2026-08-12: composing every pack takes about half a second, initialising a fresh
repository from a composed pack lays 57 files in about a second, and that repository's own gate runs
green in a few more. The whole path, for one pack, is seconds. There is no reason for the only check
of the adopter's experience to be a thing somebody does by hand once per release.

## What it deliberately does not do

It does not publish, push, or touch a network. `scripts/publish.py`'s own contract is that producing a
public tree and publishing it are two acts; this stage performs the first into a temporary directory
and never the second.
