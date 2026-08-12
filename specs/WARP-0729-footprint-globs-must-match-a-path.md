---
schema: veldo.spec/v1
id: WARP-0729
title: A footprint entry that can never match a path is a declaration that asserts nothing - convert the
  trailing-slash form and refuse the unmatchable one
status: draft
risk: standard - the change is a text conversion in five spec frontmatters plus one gate check. The risk is
  not in the mechanism, it is that turning dead entries live can make the footprint rule refuse a diff that
  passed before, which is the rule working and must be measured spec by spec before this is promoted
owner: dmitry
human_approval: not_required
lane: standalone
depends_on: [WARP-1102, WARP-1103]
# NEITHER placement NOR footprint IS DECLARED WHILE THIS IS A DRAFT, AND THE OMISSION IS THE POINT OF THE
# ITEM. The validator requires a footprint once a placement is declared, and the shape gate's footprint rule
# STANDS DOWN when a change set names more than one footprinted spec. So declaring them here would have
# switched that rule off for the very commit that filed this draft, which is the vacuous outcome this spec
# exists to close. Measured on that commit: with no footprint here, footprint_findings binds every changed
# path against WARP-0717's declaration and returns 0 findings; with one, it returns 0 findings for the
# entirely different reason that it stood down over two footprinted specs. Both are declared at promotion,
# when this is the only footprinted spec in its own change set. Intended: placement [enforcement], footprint
# .veldo/shape_gate.py, the four specs it converts, its own file and specs/index.md.
protected_paths: []
behavior_bearing: true
observability:
  logs: The gate names each unmatchable footprint entry by spec and by glob, with the reason it can never
    match, so the remedy is readable without opening the glob compiler.
  error_taxonomy: One new gate finding, in the footprint family already used by WARP-1103: a declared
    footprint glob that matches no path in the tree. It is BLOCKING, like the rest of that rule, because a
    declaration that cannot match is exactly the vacuous check this corpus forbids.
acceptance_criteria:
  - id: AC1
    falsified_by: >
      Restore one trailing-slash entry, `scripts/suites/` in WARP-0712's footprint, and the corpus sweep that
      compiles every footprint entry of every spec under specs/ with arch._glob_re and matches it against
      every path in the tree must go red naming that entry; completeness is by construction over the whole
      corpus, so one restored dead entry is enough to redden it.
    text: >
      NO FOOTPRINT ENTRY IN THE SPEC CORPUS MATCHES NOTHING. The domain is every entry of every
      `footprint` list in every file under specs/, read with the one parser (V.parse_yamlish) and compiled
      with the one glob compiler (.veldo/arch.py `_glob_re`), matched against every path in the tree;
      completeness is BY CONSTRUCTION, since that is the whole corpus and the whole compiler, not a list
      anyone assembled. WHY IT IS A DEFECT: `_glob_re` gives `*` and `**` their meanings and gives a
      trailing slash nothing, so `docs/` compiles to `^docs/$`, which is never a file path and covers no
      changed file, while `docs/**` compiles correctly. COUNTED THIS ROUND over 2302 paths: 9 specs carry
      18 such entries. SIX of them, in FOUR specs, are the trailing-slash form and their remedy is
      mechanical: WARP-0712 has `scripts/suites/`, `engine/scripts/suites/` and
      `packs/*/scripts/suites/`, and WARP-0718, WARP-0719 and WARP-0720 each have `docs/`. Driving the real
      shape_gate.footprint_findings over a representative diff per spec reproduces review 1 exactly: 3
      findings for WARP-0712 and 1 each for the other three. THE REMAINING TWELVE ARE NOT A DIFFERENT
      CONCERN BUT THEY HAVE A DIFFERENT REMEDY, one decision per entry recorded in the proof artifact:
      either the path is created, or the entry is removed as no longer true. They are paths that were
      declared and never created (`engine/scripts/selftest.py`, `.veldo/approvers.yaml`,
      `scripts/check_approver_reconcile.sh` and the `packs/*` mirrors of the same) and `proof/` paths that
      never appeared, which could not bind in any case because `proof/` is diff-excluded. WHAT WOULD REFUTE
      IT: any footprint entry anywhere under specs/ that matches no path in the tree after this lands.
  - id: AC2
    falsified_by: >
      Narrow the new rule in .veldo/shape_gate.py so an entry is matched only against the CHANGED paths of the
      diff rather than against the repository's tracked paths, and the planted-bad fixture carrying
      `scripts/suites/` must stop producing a blocking finding on a small diff, while the planted-good
      wildcard beside it must still pass so the pair stays discriminating.
    text: >
      THE GATE REFUSES A FOOTPRINT GLOB THAT MATCHES NO PATH IN THE TREE, as a BLOCKING finding naming the
      spec and the glob. The domain is every glob in the footprint of every spec the change set names,
      matched against the repository's tracked paths, not only against the changed ones, so an entry that
      is dead for the whole tree is caught even when the diff is small. COMPLETENESS IS BY CONSTRUCTION:
      the check reuses arch._glob_re, so it cannot disagree with the compiler that decides coverage, and it
      runs inside the existing footprint rule rather than as a second traversal. WHAT WOULD REFUTE IT: a
      spec declaring `scripts/suites/` or any other unmatchable glob passing the gate, or a legitimate
      wildcard that matches tracked paths being refused. Both are driven as a matched pair, one planted-bad
      and one planted-good, over a fixture tree.
  - id: AC3
    falsified_by: >
      Drop the landing-diff replay for WARP-0712 and record the before-and-after finding counts for the three
      unlanded specs only, and the assertion that every one of the four converted specs carries a per-spec
      count against its own landing diff must go red; 0712 is the load-bearing one, being the only SHIPPED
      spec of the four and so the only place a change has already landed with the rule not binding.
    text: >
      THE FOUR SPECS CARRYING THE SLASHED FORM ARE RE-BOUND RATHER THAN QUIETLY EDITED. For WARP-0712
      (shipped), WARP-0718 and WARP-0719 (ready) and WARP-0720 (draft), the converted footprint is checked
      against that spec's OWN landing diff where one exists, and the finding count before and after the
      conversion is recorded per spec in the proof artifact. Review 1 could not test whether they passed the
      shape gate at their own landing commits, because that needs their real diffs per commit; this
      criterion is what closes that gap, and WARP-0712 is the one that matters most, because it is the only
      SHIPPED spec of the four and so the only one where a change has already landed with the rule not
      binding. WHAT WOULD REFUTE IT: a
      converted spec whose landing diff produces a finding the dead entry hid, which is a REAL uncovered
      path and must be declared rather than papered over by widening the glob.
  - id: AC4
    falsified_by: >
      Widen one conversion beyond the rewrite, `packs/*/scripts/suites/` to `packs/**`, and the assertion that
      each touched footprint list changes by nothing other than the trailing-slash rewrite must go red,
      because the verbatim before-and-after in the proof artifact no longer reads as that one text
      transformation.
    text: >
      NO SPEC IS EDITED IN A WAY THAT WIDENS WHAT IT COVERS BEYOND ITS OWN LANDING DIFF. A conversion is
      `path/` to `path/**` and nothing else: no new path, no broader wildcard, no entry removed. The
      before-and-after footprint of each touched spec is recorded verbatim in the proof artifact so the
      diff is readable as a text transformation. WHAT WOULD REFUTE IT: any footprint list whose set of
      entries changes by anything other than the trailing-slash rewrite.
required_evidence: [unit]
rollback: >
  Revert the commit. The change is a text conversion in five spec frontmatters plus one check inside the
  existing footprint rule. Reverting restores the dead entries and the rule's silence about them, which is
  a loss of enforcement and nothing more: no runtime behaviour depends on it.
---

## Intent

A footprint declares what a change is allowed to touch, and the footprint rule is blocking. Nine specs
declare entries that match no path at all, so for those entries the rule is blocking nothing. The
declaration reads as protection and provides none, which is the exact shape this corpus refuses everywhere
else: a check that cannot fail.

ONE CORRECTION TO THE FINDING THAT PRODUCED THIS ITEM, because it was overstated in the safe direction and
the numbers here are the ones counted. Review 1 of WARP-0717 called these "four SHIPPED specs". Measured
from the frontmatter this round, the four carrying the trailing-slash form are ONE shipped (WARP-0712), TWO
ready (WARP-0718, WARP-0719) and ONE draft (WARP-0720), and across all nine specs with a dead entry it is
two shipped, four ready and three draft. The difference matters for what the defect cost: for a shipped spec
a change has ALREADY landed with the rule not binding, and for a ready or draft one the next change is the
one that would not bind. Both are worth closing; only the first is a hole in something already claimed.

The measured facts. The first three are review 1 of WARP-0717's, re-counted this round; the fourth is
wider than review 1 reported and is why AC1's domain is every dead entry rather than only the slashed ones.

- `.veldo/arch.py _glob_re` gives a trailing slash no meaning, so `scripts/suites/` compiles to
  `^scripts/suites/$` and matches no file path, while `scripts/suites/**` compiles correctly.
- WARP-0712 declares three such entries and produces 3 footprint findings; WARP-0718, WARP-0719 and
  WARP-0720 each declare `docs/` and produce 1 each. Reproduced this round by driving the real
  shape_gate.footprint_findings over a representative diff per spec.
- The footprint rule is BLOCKING, `docs/` is not diff-excluded (only `proof/` is), and WARP-1102 wired the
  enforcement on 2026-07-22, before WARP-0712 landed.
- Swept this round over 2302 paths in the tree: 9 specs carry 18 footprint entries that match nothing. The
  trailing-slash form is 6 of the 18, in 4 specs. So converting only the slashed form would leave two
  thirds of the dead declarations alive and AC2's check would refuse five further shipped specs the day it
  landed. That is the ordering constraint on this item, and it is the reason AC1 owns the whole sweep.

## Context

- WARP-0717 hit the same defect in its own footprint during its build, measured it, and converted its two
  entries to the `path/**` form. That is why it produces 0 findings at its HEAD. The corpus was not swept
  at the time, which is how four other specs kept theirs.
- Why the gate check and the conversion are ONE item: converting the entries without the check leaves the
  next spec free to write `docs/` again, and adding the check without converting the entries turns the gate
  red for nine shipped specs the moment it lands. Neither half is shippable alone, and AC1 must complete
  before AC2 is switched on inside the same change.
- Why the check matches the whole tracked tree and not just the diff: a glob that matches nothing anywhere
  is dead by construction, and a glob that merely misses today's small diff is not.

## Out of scope

- Any change to `_glob_re` itself. Giving a trailing slash subtree meaning would be a second glob dialect,
  and the corpus already has one form for a subtree.
- Any change to which paths are diff-excluded.
- Re-auditing the footprints of specs whose entries all match. This item converts a syntactic form and adds
  one check; it is not a footprint review.

## Notes

- Verify the id is free before claiming it: `ls specs/` and `python3 .veldo/validate.py all`. A previous
  round collided on WARP-0726.
- The finding text must name the spec and the glob, because the remedy differs per entry.
- RULE #1 clean (ASCII hyphen only, no em dash, no en dash, no prose double hyphen).
