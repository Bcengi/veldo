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
    AND WHAT THAT GREEN CONTAINS, on a second line per pack, because the word GREEN cannot be told
    apart from a measurement of nothing: how many catalog slots ran and how many were not applicable,
    how many files the one required check actually scanned against the size of the tracked corpus, the
    commit the nested gate stamped, and EVERY BUILT-IN THAT STOOD DOWN BY NAME. A stand-down is
    recorded by the nested gate as a pass it did not measure, so leaving it in a dict and printing
    three zeros is the recorded-but-not-reported defect in a new place.
  error_taxonomy: >
    COMPOSE_FAILED (the publisher could not produce a tree at all), NO_PACKS_COMPOSED (it produced a
    tree with no composed pack, which would make every later assertion vacuous), INIT_FAILED (init
    refused or laid nothing from a composed pack - the 1.0 defect exactly), COMMIT_FAILED (the
    scaffolded tree could not be committed, so its own gate would read an EMPTY INDEX and the one
    required check in the shipped catalog would enumerate nothing) and ADOPTER_GATE_RED (the
    scaffolded repository's own gate failed). Each is separate because each names a different broken
    stage of the adopter's first ten minutes, and the last one is the only one that can be a defect in
    the adopter's tree rather than in ours.
acceptance_criteria:
  - id: AC1
    falsified_by: >
      Point the installer at this repository's own .veldo/init_scaffold.py instead of the COMPOSED
      pack's copy in scripts/check_install_and_run.py, and the assertion that the scaffolder was run
      from a tree containing no engine/ directory must go red. DRIVEN AT BOTH DEPTHS, because two
      weaker reads each survived this mutation: a record of the directory the installer was PASSED,
      and a record built from an argv list assigned one line above the call - swap the CALL alone and
      that one stays green too. The tree asserted is the one the EXECUTED path belongs to, read off the
      COMPLETED LAUNCH (subprocess's own args on the CompletedProcess), and a recorder wrapping the one
      launcher observes the argv independently, so the row's subject is the launch and not a variable
      near it. Emptying that record must red the same NAMED rows rather than raising, which is also
      driven.
    text: >
      IT INSTALLS FROM THE COMPOSED PACK, NOT FROM THIS REPOSITORY, AND THAT IS THE ENTIRE POINT. In
      this repository the template base is a separate tree at engine/; in a composed pack the base has
      been laid INTO the pack, so the pack root IS the template source and there is no engine/ at all.
      1.0 shipped uninstallable because init assumed the first shape, and every test ran against this
      repository - the one tree nobody installs. So the stage runs the COMPOSED PACK'S OWN
      init_scaffold.py, and asserts the tree it ran from has no engine/ directory, because that
      absence is the condition that broke. THE TREE IT RAN FROM IS DERIVED FROM THE COMPLETED LAUNCH,
      never from the directory the installer was passed and never from a list assigned beside the call:
      A RECORD OF AN ARGUMENT IS NOT A RECORD OF A LAUNCH, and this criterion has now been driven green
      through two such records - the first survived pointing the launch at this repository, the second
      survived swapping the call while the record stayed put, and both printed a provenance line saying
      the tree had no engine/ for a launch out of the tree that has one. The record is subprocess's own
      args off the CompletedProcess, a recorder wrapping the single launcher observes the same argv
      independently and the executable is required to sit under the composed pack root, and a launch
      whose argv names no scaffolder or several leaves the record unanswerable and NAMED rather than
      raising out of the reader.
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
      AND SEPARATELY: skip the commit between init and the gate, and the assertion that the adopter's
      one required check reached MORE THAN ZERO files must go red, because that check enumerates
      through `git ls-files`. Driven the other way too, through real git rather than a stub: a target
      whose .git is a FILE lets init succeed and makes the stage fail as COMMIT_FAILED.
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
      THE TREE IS COMMITTED BEFORE ITS GATE RUNS, AND WHAT THE GREEN CONTAINS IS CORRECTED TO WHAT THE
      ARTIFACT SAYS. The green is not a full gate and this criterion no longer implies one. The shipped
      catalog is twenty-three slots of which ONE is `required:` (scripts/secret_inventory.py), two
      built-ins legitimately STAND DOWN in a starter tree - no releases directory, no architecture
      contract - and are counted as passes, and the substance that bites is the built-in veldo contracts
      validation plus that one scan. IT USED TO SCAN NOTHING: the stage ran `git init` and never
      committed, so the check, which enumerates through `git ls-files`, reported "0 scanned" over 83
      laid-down files under a green labelled "GATE: GREEN (no-git)". So the tree is now COMMITTED, which
      is also what a real adopter's first ten minutes look like; a failed commit is COMMIT_FAILED rather
      than a gate run over an empty index; and the stage REPORTS the catalog split, the scan reach
      against the tracked corpus, and every stand-down BY NAME, because a stand-down recorded and not
      reported reads exactly like a measurement. NO COUNT IS PINNED: what is required is that a commit
      happened, that the index is not empty and that the required check reached more than zero files,
      because a green whose required check inspected an empty corpus is a defect by construction while
      every one of those numbers moves as the template grows.
  - id: AC4
    falsified_by: >
      Make scripts/check_install_and_run.py write anywhere outside its temporary directory - into
      $HOME, or into a git-ignored path inside the repository, which are the two blind spots that let
      this criterion ship unasserted - or leave its temporary directory behind, or detach its children
      with start_new_session=True, and the assertion that the inventory of the repository under check
      and of the process's own HOME is identical across the run must go red.
      AND: put a network identifier into scripts/publish.py or a network command into
      engine/scripts/verify.sh, and the two rows that ask the no-network question of THE CHILDREN THIS
      STAGE LAUNCHES must go red. The additive control drives both readers over constructed text
      carrying urlopen, socket, requests, curl, `git push` and `pip install` and requires each to be
      found, because a scan that cannot fire returns the same empty answer as a clean file.
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
      THE TEMPORARY-DIRECTORY CLAIM SAYS WHAT IT MEASURES AND NAMES WHAT IT DOES NOT. It observes a run
      that RETURNS: the removal sits in a `finally`, which a killed process never reaches, and a review
      measured 302MB of leftover trees on this machine whose timestamps matched three earlier
      interrupted runs. That is a real limit of the cleanup and it is not something this row can see, so
      the row states the property it drives and names the one it cannot, rather than claiming that a
      sweep of runs cannot fill the disk. Its scope stays the directory the row itself created, never
      the machine's /tmp, which is live state nobody owns.
      AND THE NO-NETWORK PROPERTY COVERS THE CHILDREN, NOT ONLY THIS FILE. It used to inject
      VELDO_NO_NETWORK=1 into every child, which read as a kill-switch and was read by NOTHING in this
      repository, while the property itself rested on an AST scan of one file that says nothing about
      what that file launches. The inert flag is GONE - a control that appears to enforce and executes
      nothing is worse than none, because it stops the reader looking - and ONE identifier set and ONE
      token set are now asked of this file, of scripts/publish.py and of the shipped scripts/verify.sh
      the pack's copy descends from. The flag's absence is asserted over string constants AND CALL
      KEYWORD NAMES, because the shape it had was a keyword and a constant-only scan reads clean over
      exactly that line.
  - id: AC5
    falsified_by: >
      Declare the stage as `na` in scripts/verify.sh, or name the script in an `na:` slot without
      requiring it, and the assertions that this repository's gate carries it as `required:` and that
      mentioning it equals requiring it must go red. THAT RULE IS ABOUT THIS REPOSITORY'S GATE ONLY:
      the shipped-template row is falsified by REQUIRING the stage there, driven additively by
      rewriting the template's packaging slot to `required:` in memory and requiring the reader to
      find it, and NOT by mentioning the path in an `na:` reason, which is documentation. Removing
      `scope: repo-only` from engine/.veldo/capabilities.yaml must red the row that reads it.
    text: >
      IT IS A REQUIRED CATALOG ITEM IN THIS REPOSITORY'S GATE, because a proof that only runs when
      somebody remembers is the state this item exists to leave. LANDED, not pending: Dmitry approved
      the protected-path edit on 2026-08-12 and it sits in the EXISTING packaging slot, because
      composing the published packs and proving a stranger can install and run them IS packaging
      verification, and a new catalog name would have changed a vocabulary the approval did not cover.
      THE CRITERION IS UNCONDITIONAL AND ITS REPORTING BRANCH IS GONE, which driving forced: while the
      posture was derived from the live gate, REMOVING the registration entirely satisfied both
      branches, so the enforcing state could be silently reverted. A posture cannot catch its own
      removal. THE SHIPPED TEMPLATE MUST NOT REQUIRE IT, WHICH IS NOT THE SAME AS NOT MENTIONING IT,
      and that distinction was bought by driving: the row asserted the path was ABSENT from
      engine/scripts/verify.sh, so writing the true reason into that template's `na:` slot - the
      natural place to record why the slot does not apply to an adopter - reddened THIS repository's
      gate. "Mentioning equals requiring" is the right rule here, where a slot IS the registration; in
      the shipped template a reason string is documentation. So the subject is the set of `required:`
      slots there naming this stage, which is a DEFECT SET BY CONSTRUCTION - a required check an adopter
      cannot possibly run - and may therefore be required empty forever while the template grows.
      THE EXCLUSION WAS CORRECTED BY THIS REPOSITORY'S OWN CAPABILITY-HONESTY CHECK: the script does not
      ship to an adopter, and an adopter does not publish packs. The shipped manifest DOES carry the
      path - engine/.veldo/capabilities.yaml declares home: scripts/check_install_and_run.py and the
      scaffolder lays that manifest into every adopter tree, where the named file does not exist - and
      `scope: repo-only` is the marker that makes that declaration correct rather than broken. Nothing
      read that marker until this round; a row now does. scripts/verify.sh is a PROTECTED PATH: this
      change edits it, which is why this spec declares it and why landing that edit needs the approval
      protection implies.
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

Measured on 2026-08-12, one pack end to end in about 0.9 seconds: composing every pack takes about
half a second, initialising a fresh repository from a composed pack lays 84 files, committing them
puts 66 tracked paths in the index, and that repository's own gate runs green over them. All seven
packs, with the suite's mutation rows on top, is about 8 seconds. There is no reason for the only
check of the adopter's experience to be a thing somebody does by hand once per release.

## What the adopter's green actually contains

Worth writing down because "their own gate went green" is easy to read as more than it is. The
shipped catalog has twenty-three slots and exactly ONE is `required:`
(`scripts/secret_inventory.py`). In a starter tree two built-ins stand down honestly - there is no
`releases/` directory and no architecture contract - and both are recorded as passes. So the
substance is the built-in veldo contracts validation plus that one scan.

That scan used to cover nothing at all. The stage ran `git init` and never committed, and the check
enumerates through `git ls-files`, so it reported `0 scanned` over 83 laid-down files under a green
labelled `GATE: GREEN (no-git)`. The tree is now committed before its gate runs, which is what an
adopter's first ten minutes look like anyway, and the stage prints the catalog split, the scan reach
and every stand-down by name so a reader is not left inferring any of it from the word GREEN.

## What it deliberately does not do

It does not publish, push, or touch a network. `scripts/publish.py`'s own contract is that producing a
public tree and publishing it are two acts; this stage performs the first into a temporary directory
and never the second.
