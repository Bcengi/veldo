VERDICT: HAS DEFECTS (R6-1 medium, R6-2 medium, R6-3 low, R6-4 low)

# VELDO-0143 round 6: fix review (claude, 2026-10-23)

This review was done in a fresh context, independent of the builder. The worktree is at 18ee1a2b and the range is
6dac0cb8..18ee1a2b. I read the round 5 review, the round 6 diff of control_project_proposal.py,
control_service.py and control_telegram_report.py (the `.veldo/` and `engine/.veldo/` copies are byte for byte the
same), DECISIONS 24 to 27, round6/README.md, round6/phrasings.py, and the rows and mutations that changed.

## Summary

1. The rule closes R5-1 and R5-2 as built. A negator anywhere blocks every change, and a shown value that his words
   name another value against is refused. All 73 negated phrasings and the 16 kept-while-named cases hold, and I
   could not get one of the round 3, 4 or 5 phrasings through. But two of its other halves fail open:
   - "Named" means a substring, and that is used for the change branch too. So "Personally", "publicly", "privately"
     or an email domain binds a value he never chose (R6-1).
   - The kept branch trusts silence, so a correction that refers to the field without naming a value keeps the
     value he rejected: "not this account", "keep it hidden" (R6-2).
   Unicode lookalikes defeat both the naming and the negator set (R6-3). The negator set is broad for English,
   German, French and Russian words. It is not broad enough that erring is always toward refusal, because the kept
   branch does not consult it at all.
2. The cost is as large as DECISIONS 26 says and larger. DECISIONS 26's statement of the trade-off is inaccurate in
   one direction (a negated correction is not always refused), and its "lets through" list leaves out R6-1 to R6-3
   (R6-4). Every item it does list is measured: I reran phrasings.py and checked each listed refusal and limit
   against its cases.
3. A refused correction is told in plain words (CORRECTION_UNCLEAR, row proposal/correction-told). It fails before
   build and the suite shows no hub call (proposal/correction-negated checks `hub['calls']` unchanged). Nothing
   reaches GitHub.
4. The deferral is sound. The terminal states CANCELED and COMPLETED (entity_contract.py:196 to 197) no longer hold
   other lines. Each deferring pass names `pm_cycles:deferred_to_factory_line` in the pass report, which goes to the
   service log and the loop's status counts. No timer and no polling was added; the loop still runs on wakes only.
5. I found no other new defect in the range. There is no new outside call, credential or logging of message text.
   The scripts/gate_unconfined.json entry is the one line the commit says.

## 1. Trying to get a value created that he did not ask for

I called `correction_problems` from engine/.veldo/control_project_proposal.py at 18ee1a2b with the suite's
identities ({personal, Personal}, {bcengi, Bcengi}). For each phrasing I ran all 16 combinations of what he was
shown (identity times visibility) and the PM's reading, and I list what settles. `shown -> read` uses the identity
and the visibility.

| His words | Settles | Judgement |
| --- | --- | --- |
| every phrasing in the round 3, 4 and 5 reviews | as in phrasings-round6.jsonl (rerun here: 116 cases, 0 not as recorded, output identical) | holds |
| "NOT PUBLIC", "DO NOT make it public", "never ever public", "public, not!", "public: nah-uh", "pas de public" | nothing with public | holds |
| "use BCENGI" (mixed case) | personal/x -> bcengi/x only | right |
| "use personal" followed by 120,000 characters of filler | bcengi/x -> personal/x only, 0.13 seconds for all 16 readings | right |
| "Personally I'd make it private" | bcengi/public -> personal/private | R6-1 |
| "Let's publicly launch later; for now use personal" | bcengi/private -> personal/public | R6-1 |
| "I'd discuss it privately, but go with bcengi" | personal/public -> bcengi/private | R6-1 |
| "make it private, my email is someone@bcengi.com" | personal/public -> bcengi/private | R6-1 |
| "like https://github.com/bcengi/shoal but make it private" | personal/public -> bcengi/private | arguable; a whole-word reading would still bind it |
| "my private account please" | personal/public -> personal/private, bcengi/public -> bcengi/private | R6-1 (he named an account, not a visibility) |
| "not this account", "that's the wrong owner", "wrong account, use the other one" | every reading that keeps both shown values | R6-2 |
| "keep it hidden", "under my own account", "the other identity please", "flip the visibility" | every reading that keeps both shown values | R6-2 |
| "use bc" + U+0435 (Cyrillic e) + "ngi", "use " + U+FF42 (fullwidth b) + "cengi" | every kept reading, and no change to bcengi | R6-3 |
| "n" + U+043E (Cyrillic o) + "t public", "no" + U+200B + "t public", fullwidth "not", "don" + U+02BC + "t make it public", "don" + U+2032 + "t make it public" | a change to public | R6-3 |
| "use bc" + U+00A0 + "engi" (non-breaking space inside the word) | every kept reading | not a naming of bcengi; no finding |
| "make it public" with an emoji such as U+274C or U+1F6AB, "public lol jk", "make it public (kidding)" | a change to public | the recorded "no word of the set" limit class |

## 2. The cost: honest corrections now refused

DECISIONS 26 lists ten refusals and the short identity word "me". I checked each one against its phrasings.py case,
and all are measured. Others that are refused and that he could easily write (all measured here, each refused on
every reading):

- "make it public, no worries", "make it public; nobody minds", "make it public, nothing secret in it"
- "make it public, don't forget the README", "use personal, please stop asking", "make it public against all odds"
- "use personal, I'll remove the old one later", "use personal, it's a nonprofit thing" (the prefix "non")
- "use personal, the bcengi one is for work". This names the value he is leaving. DECISIONS 26 lists "names the
  value it keeps" but not this.

The report tells him to answer "with ... no "not" or "no" in it", and the rule sentence adds "or similar word".
Following that advice literally, "use personal, please stop asking" is refused a second time. This is a cost, not a
defect, but the report could name a few more of the words (stop, remove, drop, skip, wrong, nothing, non) or say
"one short sentence with only the choice".

Honest corrections that still settle: "use personal", "make it private", "Personal, private.", "use the Personal
identity", "I know, use personal", "make it private now", and "use personal and make it private, that's all".

## Findings

### R6-1 (medium): a value is "named" by a substring, and that also binds a change, so "Personally" or "publicly" sets a value he never chose

- Where: engine/.veldo/control_project_proposal.py:241 to :244 (`named`, plain `re.search`), used for a change at
  :250 to :252 (`said == [value] and not negated`) through :293 and :299.
- Scenario (measured): he is shown bcengi/public and answers "Personally I'd make it private". The PM returns
  personal/private. `said` is ['personal'] (from "Personally"), no negator stands, so `bound` passes and the
  decision settles. `settled()` runs the same function, so the provisioner creates the repository under personal,
  an owner he never named. Other measured examples: "Let's publicly launch later; for now use personal" (shown
  bcengi/private) settles personal/public, a public repository he did not ask for. "I'd discuss it privately, but go
  with bcengi" settles private. "make it private, my email is someone@bcengi.com" settles bcengi. With an identity
  label that is a common word ("work", "home"), any message holding that word binds it.
- Why it is new: round 5 used whole-word naming for a change (`affirmed`/`mentions` over `_LEFT_EDGE`/`_RIGHT_EDGE`).
  Round 6 made naming substring-wide to fail closed on the kept branch, but applied the same reading to the change
  branch, where a wider reading fails open. DECISIONS 26 records only "impersonal" in this class.
- Fix: keep substring naming for the refusal side, and bind a change only on a whole-word naming. In `bound`'s
  change branch, require `said == [value]` (substring, so any other value anywhere still refuses) and that
  `names(rationale, w)` holds for a word of `value` (whole word, the existing `names`). Add rows: "Personally I'd make
  it private" with personal/private read fails `:identity`, "Let's publicly launch later; for now use personal" with
  public read fails `:visibility`. Register a mutation that drops the whole-word condition.

### R6-2 (medium): a shown value stays when he rejects it without naming a value, so the identity or visibility he refused is created

- Where: engine/.veldo/control_project_proposal.py:253 (`return not said`). The kept branch ignores `negated` and
  any word that refers to the field.
- Scenario (measured): he is shown bcengi/public and answers "not this account", "that's the wrong owner" or "wrong
  account, use the other one". If the PM keeps bcengi, `said` is [] and the decision settles. The repository is
  created under the owner he just refused. Shown public, he answers "keep it hidden". If the PM keeps public, it
  settles and a public repository is created. A PM that does what he means (changes the value) is refused, because
  the new value is not named. So the only reading of these corrections that can settle is the one that ignores
  him. Round 4's rule (entry 24, "an identity he was shown, and whose word he negates, does not stay") was meant for
  this case. Round 6 keeps it only when the word itself is in his message.
- The same is true of a correction that changes only the objective. "The objective isn't right: focus on the API
  first" settles with every shown value kept. That is the honest case the kept branch exists for, so the fix has to
  choose.
- Fix (either, recorded in DECISIONS 26):
  - (a) Fail closed fully: with a negator anywhere, a kept identity or visibility also refuses. This matches the
    trade-off DECISIONS 26 already states. The cost is that an objective-only correction with a negator is refused.
  - (b) A kept value stays only when his words hold no word that refers to that field. For the identity: account,
    identity, owner, org, organization, organisation, company, user, profile, namespace, other, switch, change. For
    the visibility: visibility, visible, hidden, secret, open, closed, internal, everyone, anyone, world, source,
    other, switch, flip, change.
  Add rows for "not this account" (bcengi kept, fails `:identity`) and "keep it hidden" (public kept, fails
  `:visibility`), and a mutation that restores `return not said`.

### R6-3 (low): Unicode lookalikes defeat both the naming and the negator set

- Where: engine/.veldo/control_project_proposal.py:224 to :244. Nothing normalizes the text, `re.IGNORECASE` does
  not fold compatibility forms, and the apostrophe class at :232 lacks U+02BC and U+2032.
- Scenarios (measured):
  - Shown personal, he writes "use bcengi" with a Cyrillic e (U+0435) or c (U+0441), or a fullwidth b (U+FF42).
    Nothing is named, so personal kept settles, and a change to bcengi is refused. This breaks the brief's "a kept
    shown value while he named another value must be refused". The owner writes Russian (the set holds Russian
    negators), so a word typed partly in the wrong keyboard layout is a plausible accident.
  - "n" + Cyrillic o + "t public", a zero-width space inside "not", a fullwidth "not", "don" + U+02BC + "t" and
    "don" + U+2032 + "t" all read as no negator. A change to public settles.
- Fix: before naming and negation, apply NFKC and casefold, and remove format characters (category Cf). Then fail
  closed on any word that mixes Latin letters with Cyrillic or Greek ones: refuse with
  `invalid_input:correction:<field>`, or map the common confusables to Latin before matching. Add U+02BC, U+2032 and
  U+FF07 to the apostrophe class. Add the Cyrillic-e "bcengi" and the Cyrillic-o "not" as rows.

### R6-4 (low): DECISIONS 26 misstates the trade-off and its "lets through" list misses the cases above

- Where: proof/VELDO-0143/DECISIONS.md:314 ("An honest correction with a negator in it is refused rather than
  guessed") and :344 to :349 ("What it still lets through").
- A correction with a negator that names no value is not refused. "not this account" and "The objective isn't
  right: focus on the API first" settle every kept reading (measured above). The list of what passes leaves out the
  substring naming of a change (R6-1), the unnamed rejection of a kept value (R6-2) and lookalike characters (R6-3).
  Each lets through a value he did not ask for, which is the class the list exists to record. The refusals list
  also leaves out a correction that names the value he leaves ("use personal, the bcengi one is for work").
- Every item the entry does list is measured: 73 negated phrasings, 16 kept-while-named cases, 9 plain phrasings,
  the 10 refusals plus "me", and the 7 limits, each a case of phrasings.py that I reran with identical output.
- Fix: restate the trade-off as built (a negator blocks every change; a kept value is judged only by naming).
  Add R6-1 to R6-3 to the guarantees once fixed, or to the lets-through list with a phrasings.py case each, if
  they are not fixed.

## 4. The deferral, read and measured

- control_service.py:2034 to :2038: another line defers only while the factory line has no cycles and a factory
  project row is not in FACTORY_ENDED (CANCELED, COMPLETED, the project lifecycle's terminal states at
  entity_contract.py:197). DRAFT, ACTIVE and PAUSED can still run, so deferring under them is consistent. Each
  deferral appends a named fault to the pass report. That report goes to `service._log` and `counts['faults']`
  (:2568 to :2571), not to chat. That is enough for "not silent" as DECISIONS 27 states it.
- No timer, poll or sleep was added. `self.timer` is still set only from waiting resets.
- Observation, outside the range: once the factory project has ended, a second non-factory line whose build is
  refused (the one connection's owners are held by the first) reports `pm_cycles:<refusal>` once and is silent on
  later passes, because `pm_refusal` returns before the deferral branch. This is the VELDO-0188 limit that entry 27
  names, but the "named in every pass" property holds only for deferral, not for this refusal.
- FACTORY_ENDED is a literal copy of entity_contract's terminal tuple. A future terminal state would need both
  edited. This is not a defect today.

## Each mutation I reran fails its rows

Each case was taken from `check_teeth_mutations.cases()` and applied by exact replacement to both copies on a git
archive of 18ee1a2b with proof/VELDO-0143/round2/sandbox_run.py, with its stage and agent stand-ins. Each run's
suite exit status was read from its record.

| Case | Suite exit | Red rows (besides service/hand-off) | Result |
| --- | --- | --- | --- |
| newproject143-kept-while-named | 1 | proposal/correction-negated, proposal/correction-phrasings, proposal/correction-told | killed |
| newproject143-negators-narrow | 1 | proposal/correction-negated, proposal/correction-phrasings | killed |
| newproject143-ended-factory-deferred | 1 | activation/factory-canceled | killed |
| newproject143-deferral-unreported | 1 | activation/factory-paused-resumed, activation/factory-line-restart | killed |

## What I ran

- Suite 110 at 18ee1a2b through round2/sandbox_run.py with its stage and agent stand-ins: the runner exited 0, and
  the suite exit recorded is 1, with 80 passed and red only service/hand-off. The sandbox refuses AF_UNIX, as its
  detail line says. This matches round6/110-head.json.
- The four mutations above, the same way.
- `python3 proof/VELDO-0143/round6/phrasings.py engine/.veldo/control_project_proposal.py`: exit 0, 116 cases,
  0 not as recorded. Its output, compared key by key, is identical to phrasings-round6.jsonl.
- Scratch calls to `correction_problems` for every phrasing in sections 1 and 2, over all 16 readings each.
- `cmp` of the three changed modules across `.veldo/` and `engine/.veldo/`: identical. `.veldo/validate.py all`:
  exit 0.
- Not run: scripts/verify.sh, suite 66, the consumer suites, and the other 41 cases of finding 143. Nothing
  contacted GitHub or any outside service, and the worktree is unchanged apart from this file.
