# VELDO-0143 round 6: the round 5 review's findings

Branch agent/claude/veldo-0143. The review is `../REVIEW-claude-r5-2026-10-23.md`, added unchanged from a40c2f6b
in 16efff83. The code is 26e05c37, the rows and mutations 45240f88 and d63442e5, and DECISIONS 26 and 27, the spec
history and footprint and the phrasings evidence c4fa8b89. Nothing here is a gate result, a review verdict or an
approval.

This sandbox refuses AF_UNIX, has no systemd user manager, and may not write the account's graph stage. So suite
110 runs here through `../round2/sandbox_run.py --stage --agent`, as in rounds 4 and 5, and `scripts/verify.sh`
cannot run here. No timer and no polling was added anywhere.

## The rule as built

Rounds 3, 4 and 5 each widened a reading of which value a negator applies to, and each review found phrasings
that passed a value he refused or replaced. Round 6 removes that reading. `control_project_proposal.correction_problems`
now applies this rule to the identity and the visibility (`named`, `negates`, `bound`):

- His words NAME a value wherever its word (an identity's id or label, or private or public) occurs in them,
  ignoring case, even inside another word.
- They NEGATE where any negator of `_NEGATOR` stands anywhere in them. That covers any line and any distance; a
  negator joined by a hyphen, underscore or period; "no" as a word, including after "?" or "!"; the prefix "non";
  any word ending in n't with any apostrophe; dont, wont, cant, didnt and their kind; and a broad set of others
  (DECISIONS 26 lists them).
- A value other than the one he was shown is bound only where his words name exactly that value of the field
  and negate nothing.
- The shown value stays only where his words name no value of the field.
- A changed project name is bound only where his words name it and negate nothing. The mode binds as before.

Every other reading fails the decision `invalid_input:correction:<field>` before anything is built, and
`settled()` refuses it again. His report (`control_telegram_report`, `CORRECTION_UNCLEAR`) reads, for the identity:
"<name> could not be set up." / "... failed: invalid_input:correction:identity; nothing was activated. Your
correction did not make clear which identity to use: I change something only when your words name exactly one
choice for it and hold no "not", "no" or similar word anywhere, and I keep what you were shown only when your
words name none" / "Ask again with one clear choice for each thing you change and no "not" or "no" in it, for
example "use <identity> and make it private"."

This is conservative by choice: an honest correction with a negator in it is refused rather than guessed
(DECISIONS 26, with the measured refusals and the limits that remain).

Removed from the module: `_CLAUSE`, `_ANSWERED_NO`, `_clauses`, `_occurrences`, `mentions`, `affirmed`,
`negated`, `ambiguous` and the `:ambiguous` code. `_LEFT_EDGE`/`_RIGHT_EDGE` stay, only for `names` (a
project's name, and the identity an approval names). Mutations removed with them: newproject143-negation-ignored,
-word-edge-period, -kept-value-whole-word, -and-ends-clause, -ambiguity-ignored, -negators-round4 and
-answered-no-ignored.

## Each finding: fix, row, falsifier

| Finding | Fix | Row (red on the round-5 engine) | Registered mutation, here |
| --- | --- | --- | --- |
| R5-1 medium | `bound`: the shown value stays only where his words name no value of the field | proposal/correction-negated: identity-kept-named ("use personal", bcengi kept), visibility-kept-named ("make it private", public kept), both-kept-named ("use personal and make it private", bcengi/public kept), each failing by name; settles-identity, -visibility, -both and -period settle as he said. proposal/correction-phrasings: no kept value settles under words that name another, and the plain phrasings settle exactly the readings they say | newproject143-kept-while-named (the round-5 reading, kept unless negated): killed |
| R5-2 low | `negates`: a negator anywhere, on any line, joined by a hyphen or not, "no" after "?" or "!", the prefix "non". With a negator, no value named is bound | proposal/correction-negated: visibility-hyphen-kept and visibility-hyphen ("not-public", kept and taken), identity-hyphen-kept ("not-bcengi please, personal") and identity-hyphen ("not-bcengi"), visibility-line-above ("not", a line break, "public"), visibility-answered ("public!? no"), visibility-anything-but, and the round 3 and round 4 phrasings. proposal/correction-phrasings: 42 phrasings from the three reviews, over all 16 readings each | newproject143-hyphen-negator-ignored: killed. newproject143-negation-affirms (a message with a negator affirms): killed. newproject143-negators-narrow (the round-3 words only): killed |
| R5-3 low | `Line.build_cycles` defers only while the factory project is not CANCELED or COMPLETED (`FACTORY_ENDED`), and each deferral appends `pm_cycles:deferred_to_factory_line` to the pass's faults | activation/factory-canceled (new): with the factory project canceled, the first line visited that wants cycles (another active project's) builds them at the first pass and nothing is deferred. activation/factory-paused-resumed: each paused pass names the deferral. activation/factory-line-restart: the first pass names it, and refusals are still counted at most once | newproject143-ended-factory-deferred: killed. newproject143-deferral-unreported: killed |
| R5-4 low | DECISIONS 26 replaces entry 24's limit list: each guarantee, refusal and limit is a case of `phrasings.py` or a row, and the R5-1 and R5-2 cases are guarantees now | `phrasings.py` (below) | (measurement, not a mutation) |
| brief: plain words | `CORRECTION_UNCLEAR` in the failed report | proposal/correction-told (new): the refused identity and visibility corrections are each told once, with the plain sentence, the rule and how to answer | newproject143-correction-told-code: killed |

Re-anchored and killed here on their own rows: correction-identity-unbound, correction-visibility-unbound,
correction-name-unbound (the new `bound` and name lines), factory-owners-taken and paused-factory-owners-taken
(the new deferral condition). Finding 143 has 45 cases: 7 removed, 7 added.

## Results here

- Suite 110 at d63442e5 (`110-head.json`): 80 passed, red only service/hand-off (AF_UNIX, the host's).
- Suite 110's rows on the round-5 engine (`110-round5-engine.json`): the tree is d63442e5 with the three changed
  modules (both copies) taken from 6dac0cb8, run as the scratch commit object c8f7d14b, which no branch names. 74
  passed. Red: proposal/correction-negated, proposal/correction-phrasings, proposal/correction-told,
  activation/factory-line-restart, activation/factory-paused-resumed, activation/factory-canceled and
  service/hand-off. Each is red by behaviour: the kept, hyphen, line-above and "!? no" readings settle; 15 of the
  42 review phrasings let a named value settle; the report names only the code; no deferral is named; and with
  the factory canceled, no line builds cycles.
- `phrasings.py` over the module alone: `phrasings-round6.jsonl` has 116 cases (98 guarantees, 11 refusals, 7
  limits) and 0 not as recorded. `phrasings-round5-module.jsonl` (the 6dac0cb8 module) has 79 not as recorded.
- Finding 143, `../run_falsifiers.py` in worker mode on a `git archive` of d63442e5 (`falsifiers-143-round6.json`):
  all 44 cases that target suite 110 were run, and all 44 were killed. The baseline before and after is red only
  on service/hand-off and pm/new-project-run (worker mode stands in for nothing). newproject143-scaffold-not-laid
  targets suite 66 and is the host's.
- Consumer suites (`consumer-suites.json`, `../round2/consumer_suites.py`): round 5's 38 suites on `git archive`
  trees of 6dac0cb8 and d63442e5, one after the other. All 38 give the same result on both trees. As in round 5,
  this is evidence only for the suites green here. 72_veldo_0128_reports (the report's other reader) is green on
  both with 18 rows. 83, 92, 93 and 96 are red on both trees here (sandbox limits), so the R5-3 change is not
  judged by them here.
- Suite 66 through `scripts/selftest.py --suite 66_veldo_0047_authority`: 27 passed and 0 failed with its
  prerequisites, but the suite itself reports one row here. It stays on the host list.
- `.veldo/validate.py all` exits 0. check_lint, check_template_sync and check_generated pass.

## Host runs

1. `python3 scripts/selftest.py --suite 110_veldo_0143_new_project`: every row green, service/hand-off,
   provision/signing-no-agent with its recording socket, and pm/new-project-run among them.
2. `python3 scripts/selftest.py --suite 66_veldo_0047_authority`: every row green, authority/installed-assets
   included.
3. `python3 scripts/check_gate_mutations.py --finding 143`: 45 of 45 killed (newproject143-scaffold-not-laid is
   the host's).
4. The consumer suites this sandbox cannot judge, at this branch's head and at 6dac0cb8: 83_veldo_0154_factory_loop,
   92_veldo_0088_pm_cycles, 93_veldo_0152_intake_routes and 96_veldo_0204_reservation_policies first. They drive
   `Line.run`, so a loop with a factory project that defers a line now reports `pm_cycles:deferred_to_factory_line`
   faults. Then the rest of round 5's list.
5. `bash scripts/verify.sh`.
