---
schema: veldo.spec/v1
id: VELDO-0009
title: init stamps what it laid down, so substrate drift has a detector - and the detector reports the
  comparison nobody can make from inside an adopter's repository instead of guessing at it
status: ready
risk: standard - it makes /veldo:init generate one small record and adds a reader that compares it with
  what is available now. It is NOT low because it changes the scaffolder, which is the one code path an
  adopter runs before anything else, and 1.0 shipped with that path broken. It is not high because the
  record is create-only, an absent record is an honest state rather than a failure, and no gate refuses
  anything over it
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0018
work: W8
placement: [contracts]
footprint:
  - ".veldo/init_scaffold.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/version.py"
  - "engine/.veldo/version.py"
  - ".veldo/capabilities.yaml"
  - "engine/.veldo/capabilities.yaml"
  - "scripts/suites/26_veldo_0009_install_stamp.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0009-init-stamps-the-version-it-laid-down.md"
  - "specs/index.md"
protected_paths: []
behavior_bearing: true
observability:
  logs: >
    The stamp records the version, the moment, and the templates path it was laid from, so a reader
    knows not just which version but which tree produced it. The drift reader names both versions when
    they differ and names WHICH comparison it could not make when it cannot, rather than reporting a
    verdict either way.
  error_taxonomy: >
    UNSTAMPED (no record: installed before stamping existed, set up by hand, OR laid from templates that
    declared no version for this project - the third was missing from this reason and it is the one an
    install made TODAY lands in, so init now reports that stand-down at install time),
    VERSION_STAMP_UNREADABLE (a record exists but is not a stamp), VERSION_NOTHING_TO_COMPARE (a stamp
    exists and this tree declares no current version, which is exactly an adopting repository because
    it is not a marketplace - unless the canonical declaration is THERE and unreadable, in which case
    the reason says so, because the repair is that file rather than a version supplied from outside)
    and VERSION_SUBSTRATE_DRIFT (both known and different, naming both). The third is the one that
    would have been a false alarm: an adopter cannot make this comparison from inside their own tree,
    and reporting either verdict there would be a guess.
acceptance_criteria:
  - id: AC1
    falsified_by: >
      Add the stamp to the scaffolder's copied-template list in .veldo/init_scaffold.py instead of
      generating it, and the assertion that a fresh install carries a stamp while NO template for it
      exists in the templates tree must go red.
    text: >
      THE STAMP IS GENERATED, NEVER COPIED, AND THAT IS NOT A STYLE CHOICE. A copied template would
      have to be tracked and published, and its content is a fact about THIS install rather than
      anything a template could hold. It also walks straight into the trap this session already found:
      a template the scaffolder DEMANDS but the published pack does not carry makes every install fail.
      So the stamp is generated like the derived index, and the assertion is that a fresh install has
      one while the templates tree has no such file at all.
  - id: AC2
    falsified_by: >
      Make the scaffolder overwrite an existing stamp in .veldo/init_scaffold.py, and the assertion
      that a second scaffold SKIPS the stamp and leaves the first install's record byte-identical must
      go red.
    text: >
      CREATE-ONLY, LIKE EVERYTHING ELSE THE SCAFFOLDER LAYS. A re-run reports the stamp as skipped and
      leaves it byte-identical, so it keeps saying what the FIRST install was. A stamp rewritten by a
      later re-run that laid nothing would erase the only evidence of drift at the exact moment
      somebody was looking for it.
  - id: AC3
    falsified_by: >
      Write a stamp with a placeholder version when the templates declare none in
      .veldo/init_scaffold.py, and the assertion that a templates tree declaring no version produces
      NO stamp at all rather than one saying unknown must go red. ALSO read the marketplace's
      plugins[0] instead of the entry NAMED veldo, and the row asserting that a co-hosted plugin listed
      FIRST does not become this install's version must go red. ALSO accept any non-empty string as a
      version, and the rows asserting that templates declaring "   ", "TBD", "" or "1" produce no stamp
      must go red. ALSO drop the stand-down reason from _write_stamp's return, and the row asserting
      that the caller is TOLD why no record was laid must go red.
    text: >
      NO STAMP IS BETTER THAN A STAMP THAT GUESSES. When the templates declare no version, nothing is
      written: an unstamped install is an honest state a reader can act on, and a stamp saying
      "unknown" is a fact nobody can. THE VERSION IS FOUND ACROSS THE THREE REAL SHAPES rather than
      one assumed shape - the templates root, its parent (which is how this repository is laid out,
      with templates in engine/ and the manifest above it), a composed Claude pack, and a composed
      pack whose manifest sits at its root. Assuming a single shape is precisely what made 1.0
      uninstallable. AND A GUESS HAS TWO MORE SHAPES, both found by independent review and both closed
      here. BY IDENTITY, NEVER BY POSITION: the read took plugins[0], so a parent marketplace listing
      another plugin first stamped THAT plugin's version as this install's - a fact nobody declared
      about veldo. AND A STRING IS NOT A VERSION: any non-empty string passed, so templates declaring
      "   " produced a stamp whose version was "   ", which the reader returned as a VERSION with no
      cause while drift() reported substrate drift naming it. Both rules are the READER'S OWN, loaded
      from .veldo/version.py rather than copied here, because two enumerations of one rule diverge.
      AND THE STAND-DOWN IS REPORTED, NOT SILENT: when no record can be laid, the reason travels back
      to the caller and init PRINTS it, naming the shapes it searched.
  - id: AC4
    falsified_by: >
      Make drift() in .veldo/version.py report no drift when this tree declares no current version,
      and the assertion that a stamped tree with nothing to compare returns
      VERSION_NOTHING_TO_COMPARE rather than a clean answer must go red. ALSO make drift_contradictions
      return an empty list unconditionally, and the row asserting that two deliberately inconsistent
      answers are NAMED must go red.
    text: >
      THE COMPARISON AN ADOPTER CANNOT MAKE IS REPORTED AS SUCH. A scaffolded repository carries the
      stamp and no marketplace manifest, because it is not a marketplace - so there is nothing IN IT to
      compare against, and that is neither "no drift" nor a drift. It is VERSION_NOTHING_TO_COMPARE,
      and the caller passes the version they can install from now. Reporting "current" there would
      clear an install nobody measured; reporting "drifted" would accuse every adopter. NEGATIVE
      CONTROL: with a current version supplied, the SAME tree reports no drift when they match and
      names BOTH versions when they do not. AND OVER THE LIVE TREE THIS ASSERTS A PROPERTY, NEVER AN
      ANSWER. The first version pinned this repository's answer to UNSTAMPED, so one run of the
      documented create-only scaffolder - idempotent, safe to re-run, writing a stamp that is not
      gitignored - reddened a named row for a correct, non-destructive operation, and the red read as
      "the detector is broken" when the detector had answered correctly. What is asserted instead is
      that NO ANSWER THIS ORGAN GIVES ABOUT A TREE IS FALSE ABOUT THAT TREE: the cause is one of the
      four declared causes or None, it carries a reason, and every value beside it matches the state on
      disk. All five answers are allowed and each is driven; only a contradiction is a finding, and
      that set is a defect set by construction, so a change of state cannot join it.
  - id: AC5
    falsified_by: >
      Return the installed version from the stamp without checking its schema in .veldo/version.py,
      and the assertion that a JSON file at the stamp path which is not a veldo.installed/v1 record is
      VERSION_STAMP_UNREADABLE rather than a version must go red.
    text: >
      AN UNSTAMPED TREE AND A CORRUPT STAMP ARE DIFFERENT FACTS. A file at the stamp path that parses
      but is not a veldo.installed/v1 record carrying a version is VERSION_STAMP_UNREADABLE, not
      UNSTAMPED and not a version: something wrote there and the fix is to look at it, where an
      unstamped tree needs nothing looked at. The same discipline every reader in this plan carries -
      the reason is part of the answer, because the reason is what determines who does what next.
required_evidence: [unit]
rollback: >
  Delete the stamp writer's call in scaffold and the stamp reader in .veldo/version.py. Existing stamps
  become inert data no reader consults, no install breaks because nothing requires the file, and the
  version reader keeps working, so the retreat costs two call sites.
---

# init stamps what it laid down

## The gap, in an adopter's words

An adopter installs the substrate, reads the documentation months later, and has no way to know
whether the code in their repository is the code that documentation describes. Nothing recorded what
they installed. That is substrate drift with no detector, and PLAN-0018 names it as W8.

## Why the stamp is generated rather than shipped

This session found the trap the hard way. Adding a module to the scaffolder's copied-template list
made init DEMAND that template; the published pack did not carry it, because the publisher ships
tracked files and the module was not yet committed; and every scaffolded repository failed with
"template missing". That is the 1.0 defect exactly.

A stamp cannot be a template anyway - its content is a fact about one install - so it is generated,
like the derived spec index, and a criterion asserts that no template for it exists.

## The state that would have been a false alarm

A scaffolded repository has the stamp and no marketplace manifest, because an adopter's repository is
not a marketplace. So the obvious drift check - compare the stamp with what this tree declares -
cannot run there at all.

Reporting "no drift" would clear an install nobody measured. Reporting "drifted" would accuse every
adopter in existence. The honest answer is that the comparison cannot be made from inside that tree,
and the caller supplies the version they can install from now. That is a fourth state, and it is the
one an adopter is actually in.

## The five packs that install with no record, and what is fixed here

Independent review installed all seven composed packs and measured the stamp: `claude` and
`antigravity` get one, and `aider`, `codex`, `copilot`, `cursor` and `opencode` get none. They are the
packs with no native manifest concept, so nothing in them declares a version at any shape the
scaffolder searches, and the composed pack's parent is `packs/`, which declares nothing either.

**Two of the three halves of that are closed here, and the third is named rather than guessed at.**

The install used to say nothing: it printed "substrate complete" and exited 0 with no word that the
record had not been laid. It now prints the stand-down and the shapes it searched, which is ledger
finding 64's rule applied where it belongs - a stand-down that is recorded must also be reported.

The reason the tree then gave was false. `UNSTAMPED` said the repository "was installed before the
stamp existed, or was set up by hand", and both halves are wrong about an install made minutes
earlier; the reason now names the third way, which is the one those five packs land in. AC5's own
principle is that the reason is the actionable half, and that reason sent an adopter looking for an
old install.

**What is NOT fixed here, deliberately.** Those five packs still lay no record, because nothing in the
shipped base declares the version: it lives in `.claude-plugin/marketplace.json`, which is a Claude
artifact and is not composed into a cursor or an aider pack. Closing that means giving the BASE a
declaration of its own and teaching the publisher to carry it, which is `packs/` and `scripts/`
territory rather than this item's, and inventing a `plugin.json` for a tool that has no plugin concept
would be a shortcut wearing a fix. It is recorded as a cross-item dependency instead.
