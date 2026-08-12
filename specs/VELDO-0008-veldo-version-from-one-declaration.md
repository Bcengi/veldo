---
schema: veldo.spec/v1
id: VELDO-0008
title: veldo version - one canonical declaration, every other manifest DERIVED from it rather than
  compared against a hand-listed pair, and a CLI that answers what this installation is
status: ready
risk: standard - it adds a read model and one derived check over the version manifests, and changes no
  released number. It is NOT low because the number it reports is what an adopter and a bug report
  identify an installation by, and the manifests have drifted apart once already. It is not high
  because it declares no new version, ships no new file into the release, and refuses nothing except a
  disagreement between copies of one number
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0018
work: W7
placement: [contracts]
footprint:
  - ".veldo/version.py"
  - "engine/.veldo/version.py"
  - ".veldo/init_scaffold.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/capabilities.yaml"
  - "engine/.veldo/capabilities.yaml"
  # DECLARED BECAUSE THIS ITEM CAUSED THEM. Adding version.py to the scaffolder's lay-down list made
  # VELDO-0007's install-and-run stage fail - the composed pack did not carry the new template because
  # the publisher ships TRACKED files only. The finding is recorded in PLAN-0018's ledger (44) and the
  # property in that stage's own docstring, so the next person reads it there rather than rediscovering
  # it. Both edits belong to this change and are declared rather than smuggled.
  - "plans/PLAN-0018-what-a-complex-project-needs.md"
  - "scripts/check_install_and_run.py"
  - "scripts/suites/25_veldo_0008_version.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0008-veldo-version-from-one-declaration.md"
  - "specs/index.md"
protected_paths: []
behavior_bearing: true
observability:
  logs: >
    The reader names the canonical declaration by path, every manifest it found, and the version each
    one declares, so a disagreement is legible without opening three files. A disagreement names both
    values and both paths, because "the versions differ" is not actionable and "this file says X and
    that file says Y" is.
  error_taxonomy: >
    VERSION_CANONICAL_ABSENT (the one declaration is missing or unreadable, so nothing can be derived
    and the reader refuses rather than guessing), VERSION_DISAGREEMENT (a manifest declares a version
    the canonical one does not) and VERSION_UNPARSEABLE (a manifest exists but its version cannot be
    read, which is distinct from declaring the wrong one because the fix differs).
acceptance_criteria:
  - id: AC1
    falsified_by: >
      Replace the derived manifest sweep in .veldo/version.py with a hand-written pair naming
      packs/claude and the marketplace, and the assertion that the checked set INCLUDES
      packs/antigravity/plugin.json - a third declaration nothing checked before this item - must go
      red.
    text: >
      EVERY MANIFEST THAT DECLARES A VERSION IS DERIVED, NOT LISTED. MEASURED on 2026-08-12: three
      tracked files declare this version and the only assertion covering them named TWO, so
      packs/antigravity/plugin.json was unguarded - the same hand-listed-pair defect that let seven
      listed template pairs guard nine modules. The sweep enumerates every tracked plugin.json and
      marketplace.json and derives the set, so a pack added later is covered by arriving rather than by
      being remembered. NEGATIVE CONTROL: the derived set is asserted NON-EMPTY and to contain more
      than two members, because a sweep that matched nothing would satisfy every later assertion.
  - id: AC2
    falsified_by: >
      Make the reader fall back to a default string when the canonical declaration is absent in
      .veldo/version.py, and the assertion that an absent canonical file yields
      VERSION_CANONICAL_ABSENT rather than a version must go red. ALSO delete the shape test from
      read_manifest, and the rows asserting that a canonical declaration of "" or "TBD" is refused
      must go red. ALSO read plugins[0] positionally instead of the entry named PLUGIN_NAME, and the
      rows asserting the reader answers what the veldo ENTRY declares must go red.
    text: >
      NO GUESSED VERSION, EVER. If the canonical declaration is missing or unreadable the reader
      refuses with VERSION_CANONICAL_ABSENT and returns no version at all. A default would be the
      confident-zero disease applied to identity: an installation that reports a version it invented is
      worse than one that reports none, because a bug report against a fabricated number sends
      everybody to the wrong tree. AND A STRING IS NOT A VERSION: "" and "TBD" are strings, so every
      declaration is SHAPE-CHECKED where it is read, because reporting an empty identity with a zero
      exit is the same disease wearing a pass. AND THE READ IS BY IDENTITY, NOT BY POSITION: a
      marketplace manifest hosts a LIST, so this version is the one the entry NAMED veldo declares,
      and a top-level "version" beside that list is a schema version that does not shadow it. Both
      holes were found by independent review of this item, both were reachable with the gate green,
      and each now has its own row. NEGATIVE CONTROL: with the canonical file present the same reader
      returns the real version, so the refusal is a measurement rather than the reader's only answer,
      and a legitimately co-hosted plugin ADDED to the marketplace at its own version changes nothing
      about what this installation reports.
  - id: AC3
    falsified_by: >
      Report only that the versions differ in .veldo/version.py, dropping the two values and two
      paths, and the assertion that a disagreement names BOTH files and BOTH versions must go red.
    text: >
      A DISAGREEMENT NAMES BOTH SIDES. "The versions differ" is not actionable; "this manifest says
      3.10.1 and the canonical declaration says 3.11.0" is, and it also lets a reader see which one is
      wrong, which is not always the copy. The manifests drifted apart once already, which is why an
      assertion exists at all, and the fix for a drift depends entirely on which side moved.
  - id: AC4
    falsified_by: >
      Make the CLI print a version even when the canonical declaration is absent in .veldo/version.py,
      and the assertion that it exits NON-ZERO and prints the refusal rather than a number must go red.
      ALSO let read_manifest accept any string again, and the row asserting that a canonical
      declaration of "" makes BOTH the bare CLI and --report exit non-zero must go red.
    text: >
      THE CLI ANSWERS WHAT THIS INSTALLATION IS, AND FAILS LOUD WHEN IT CANNOT. `python3
      .veldo/version.py` prints the version and exits zero; with no canonical declaration, or with one
      declaring something that is not version-shaped, it prints the refusal and exits non-zero, so a
      script that captures its output can never silently receive a guess. It prints the canonical path
      alongside the number, because an adopter debugging a version needs to know which file to look at.
      THE PRESENCE OF THE NUMBER IS ASSERTED BY EQUALITY on the printed token, never by scanning
      stdout for it: a substring scan cannot fail when the declaration is the empty string, which is
      the one state where the clause had to hold, and that is how this guarantee was false while the
      row proving it passed.
  - id: AC5
    falsified_by: >
      Remove the absent-manifest stand-down from the report in .veldo/version.py, and the assertion
      that a tree with a canonical declaration and NO other manifest reports agreement over a set of
      one, naming that it found only one, must go red.
    text: >
      A TREE WITH ONE MANIFEST AGREES WITH ITSELF, AND SAYS SO. An adopting repository has a canonical
      declaration and no packs, so the sweep finds one manifest and the honest report is agreement over
      a set of ONE with the count named - not silence, and not a claim that many copies were checked.
      This is the same honesty the other read models carry: the count that was checked is part of the
      answer. No gate stage is added by this item; the existing suite assertion is superseded by the
      derived one.
required_evidence: [unit]
rollback: >
  Delete .veldo/version.py and its suite fragment. No manifest changes, no released number moves, and
  the pre-existing two-manifest assertion is untouched, so the retreat costs one file and leaves the
  previously guarded pair still guarded.
---

# veldo version, from one declaration

## The measured gap

Three tracked files declare this project's version, and on 2026-08-12 all three said `3.10.1`:

- `.claude-plugin/marketplace.json` - what an adopter installs from
- `packs/claude/.claude-plugin/plugin.json`
- `packs/antigravity/plugin.json`

One shipped assertion compares the first two, and its own comment says why: **they drifted apart
once and the marketplace copy is what an adopter installs from.** It names two files. The third has
never been checked by anything.

That is the hand-listed-pair defect this repository has now shipped three times: seven listed
template pairs guarding nine modules, two lists in the init scaffolder missing two organs each, and
now two named manifests out of three. The fix is the same every time - derive the set - and the
reason is the same: a list is a promise somebody will remember, and the thing it protects is exactly
what people forget.

## Why the canonical declaration is the marketplace manifest

Because it is the file an adopter installs from, which the existing assertion already identified as
the one that matters. Introducing a fourth file to be canonical would add a declaration rather than
remove two.

## What independent review found: two ways to answer with a version this installation is not

Both were reachable with the gate GREEN, and both are closed here.

**A string is not a version.** The reader refused only when the version KEY was missing, so
`"version": ""` in the canonical manifest made `python3 .veldo/version.py` print
` (from .claude-plugin/marketplace.json)` and exit 0, `--report` claim agreement over three
manifests and exit 0, and the suite stay green at 42 passed. `"TBD"` behaved the same way. The
shape test that guards evidence provenance in the same module was never applied to the number the
module exists to report, and the row that proved the number was PRESENT could not fail in that
state, because it scanned stdout for a substring and the empty string is a substring of everything.
Now every declaration is shape-checked where it is read, an unshaped one is UNPARSEABLE and
therefore a refusal with a non-zero exit, and the presence of the number is asserted by equality on
the printed token.

**The canonical read was positional.** It took `plugins[0]` and never matched the entry named
`veldo` that is right there in the manifest, and a top-level `"version"` shadowed the list entirely.
So a marketplace with one co-hosted entry listed first answered with that entry's version: at
1.0.0 the report named BOTH veldo packs as the ones that had drifted, which is the inverse of the
diagnosis AC3 promises, and at 3.10.1 with the veldo entry bumped to 3.11.0 the reader answered
3.10.1, the report claimed agreement over three manifests, 3.11.0 was never mentioned and the suite
was green. Now the entry is matched by name, two entries claiming that name and disagreeing is an
ambiguity rather than a tie-break to guess at, and a marketplace with no veldo entry refuses while
naming the entries it did find.
