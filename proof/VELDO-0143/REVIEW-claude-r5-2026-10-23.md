VERDICT: HAS DEFECTS (R5-1 medium, R5-2 low, R5-3 low, R5-4 low)

# VELDO-0143 round 5: fix review (claude, 2026-10-23)

This is a fresh context, independent of the builder. The worktree is at 6dac0cb8 and the range is ad37b673..6dac0cb8.
I read the round 4 review (REVIEW-agy-r4-2026-10-23.md), round5/README.md, DECISIONS entries 24 and 25, and every engine
change in the range (control_project_proposal, control_intake, control_intake_routes, control_service,
control_service_projects, control_workflow_cycle_pm). I also read the round-5 rows of suite 110 and the nine new and five
re-anchored mutations. Each `.veldo/` copy of the six changed modules is byte-identical to its `engine/.veldo/` file
(cmp).

## Summary

1. R4-1, R4-2 and R4-4 are fixed for every phrasing the brief named. Each one refuses what he refused and settles what
   he said (table below). The honest correction "use personal and make it private" still settles. But the check does
   not fail closed in two ways. First, a shown value stays when his words name the other value and negate nothing
   (R5-1). This has been there since round 3 and was not introduced here. Second, a negator joined to the word by a
   hyphen, or put on the line above it, is not seen (R5-2).
2. R4-3 is fixed. Intake reads the project rows when it judges. Both callables are read on `service.conn`. That is the
   same connection the store runs `transaction_transition` on (control_store.py:610 passes the registry's connection),
   so inside intake_record and intake_route the rows are read in the command's own transaction. The pre-submit plan
   reads them outside a transaction, as it already did for `_entity`. A project added between the plan and the
   transaction changes the re-plan, and the store refuses it. Nothing polls and no timer was added. ServiceApi's Intake
   (control_service_api.py:169) still takes the configured list. That is unchanged and outside this finding.
3. R4-5 and R4-6 are fixed for the scenarios the review named. `service.new_projects()` caches only on success and is
   now built before `before` is taken. The other things `_cycles` builds are made fresh each time (`service.inbox`) or
   are not built inside the snapshot. The wider R4-5 deferral costs something entry 25 does not record (R5-3).
4. Each new row fails without its fix. I applied all nine new mutations myself and each was killed (below). Entry 24's
   limits are true as measured, but it claims each one is measured when four are not, and it leaves out the fail-open
   cases in R5-1 and R5-2 (R5-4).
5. I found no security defect introduced in the range. There is no new credential handling, logging or outside call.
   `store_projects` is a constant SQL statement. The new proof files hold no email address or local path.

## The brief's phrasings, measured

For each phrasing I called `correction_problems` from engine/.veldo/control_project_proposal.py at 6dac0cb8, with the
suite's two identities (personal, bcengi). I ran every combination of what he was shown (identity times visibility)
and the PM's reading, 16 per phrasing, and listed each one that settles.

| His words | What settles | Judgement |
| --- | --- | --- |
| Keep it private, not public. | Only a reading with private (kept or changed). A shown public kept is refused. | right |
| not public! / not public, thanks | Only a kept private. A kept public is refused. | right |
| neither personal nor bcengi | Nothing | right |
| don't use bcengi and personal | Nothing | right |
| no bcengi | A kept personal only. Shown bcengi read as personal is refused because personal is not said. | safe |
| use personal (not bcengi) | personal, kept or changed | right |
| bcengi? no | A kept personal only | right |
| anything but public | A kept private only. Shown public read as private is refused (private is not said). | safe |
| not under bcengi, use personal | personal, kept or changed | right |
| use personal and make it private | Shown bcengi/public read as personal/private settles, and so does every other reading that changes a field to personal or private. A reading that keeps bcengi/public also settles. | the honest reading settles; the kept reading is R5-1 |

Other phrasings I tried that settle wrongly: "not-public" and "not-bcengi please, personal" (kept value, R5-2); "not",
a line break, then "public" (a change to public settles, R5-2); "public!? no", "public?! no way" (a change to public
settles); and "public. No." (already a recorded limit). Honest corrections that are now refused: "don't make it public
and keep it private" is refused as `:visibility:ambiguous`, while "keep it private and don't make it public" settles.
Entry 25 records this refusal by choice. It fails safe, so I do not raise it as a finding.

## Findings

### R5-1 (medium): a shown value stays when his words name the other value, so the PM can ignore the correction

- Where: engine/.veldo/control_project_proposal.py:344 (identity) and :352 to :353 (visibility). When the term equals
  what he was shown, the only test is `not negated(...)`. Nothing compares it with `said` or `named`.
- Scenario (measured): he is shown bcengi/public and answers "use personal and make it private", or just "use
  personal". The PM's corrected document keeps bcengi/public. `correction_problems` returns [] and the decision
  settles. `settled()` uses the same function, so the provisioner creates a public repository under bcengi, the owner
  and visibility his only words replaced. This is the threat model's "a remote created under the wrong owner". It
  matches entry 17 to the letter ("shown for that identity, or named in his words"), but the owner's correction is
  simply ignored. The behaviour is the same at ad37b673. This range did not introduce it, but the question "is any
  refused value still settled" covers it, and entry 24 does not list it as a limit.
- Fix: when the term equals what he was shown, also require that `said` (`named` for visibility) is empty or is
  exactly that value. In other words, a shown value stays only if his words name no other value of the field. Add rows
  to proposal/correction-negated: "use personal" with bcengi kept fails `:identity`, and "make it private" with public
  kept fails `:visibility`. Register a mutation that drops the new condition.

### R5-2 (low): a negator joined by a hyphen, or on the line above, is not seen, and the fail-closed reading misses it

- Where: engine/.veldo/control_project_proposal.py:144 (`_LEFT_EDGE` treats a letter followed by '.' or '-' as joined,
  so "public" in "not-public" is no word start, even with `whole=False` in `negated`, :275). And :226 (`_CLAUSE` ends a
  clause at a line break).
- Scenarios (measured): shown personal/public, he writes "not-public", and the PM keeps public: it settles. Shown
  bcengi, he writes "not-bcengi please, personal", and the PM keeps bcengi: it settles. Shown private, he writes "not",
  a line break, then "public", and the PM changes to public: it settles. "public!? no" with a change to public settles
  too, because `_ANSWERED_NO` needs '?' straight after the word. In each case a negator stands in his words, and the
  reading fails open. Entry 25 says the kept value "fails closed".
- Fix: for the fail-closed reading in `negated`, match the word with no left-edge requirement beyond a letter or digit
  directly before it (let "-" and "." be edges there), or treat a negator joined by '-' as before the word. Let
  `_ANSWERED_NO` accept `[?!]*\?[?!]*`. If the line break is to stay a clause boundary, record it as a limit in
  entry 24. Add "not-public" (kept) and "not-bcengi" (kept) as rows.

### R5-3 (low): R4-5's deferral silently stops every other repository's project cycles while the factory project is not active, for good once it is canceled or completed

- Where: engine/.veldo/control_service.py:2030 to :2032. Another line returns False, with no report entry, whenever a
  factory project row exists in any state and the factory line has no cycles.
- Scenario (by reading): the factory project is canceled (control_project allows cancel for it, and CANCELED is
  terminal, control_project.py:76 to :77) or completed. A taken-on repository (VELDO-0161) has an ACTIVE project
  executing in it, with a team configured. Its line wants cycles, but the factory line never builds any. So that
  project's PM cycles never run, in this process or after any restart, and no pass reports a fault. Before VELDO-0143
  (39772b77) and in round 4, that line built its cycles. Entry 25 reasons only about the no-factory-project case, and
  this cost is not recorded.
- Fix: leave out the terminal states (CANCELED, COMPLETED), where nothing can resume. When a line is deferred, append
  a named fault or a report entry (for example `pm_cycles:deferred_to_factory_line`) so the owner sees why. Record the
  paused-factory cost in entry 25 until VELDO-0188.

### R5-4 (low): DECISIONS 24 says each limit is measured, but four are not, and the fail-open cases are missing

- Where: proof/VELDO-0143/DECISIONS.md:262 ("Limits that remain, each measured on the round-5 module
  (`round5/phrasings.py`)").
- phrasings.py measures ten limit cases. Entry 24 also lists another language ("nicht"), double negation and irony,
  the fail-closed refusal of a short identity word, and the negated project name. None of these is in phrasings.py.
  The entry also leaves out the R5-1 and R5-2 cases above, each of which passes a value he refused or replaced.
- Fix: either measure each listed limit in phrasings.py or say which ones are argued, not measured. Then add the
  remaining fail-open cases to the list, or fix them.

## Each new row fails without its fix (independent runs)

Each case was taken from `check_teeth_mutations.cases()` and applied by exact replacement to both `.veldo/` and
`engine/.veldo/` copies on a git archive of 6dac0cb8 (`proof/VELDO-0143/round2/sandbox_run.py` with its stage and agent stand-ins and
one replacement per copy). Each old text was found exactly once.

| Case | Red rows (besides service/hand-off) | Result |
| --- | --- | --- |
| newproject143-word-edge-period | proposal/correction-negated, proposal/correction-phrasings | killed |
| newproject143-kept-value-whole-word | proposal/correction-phrasings | killed |
| newproject143-and-ends-clause | proposal/correction-negated | killed |
| newproject143-ambiguity-ignored | proposal/correction-negated, proposal/correction-phrasings | killed |
| newproject143-negators-round4 | proposal/correction-negated, proposal/correction-phrasings | killed |
| newproject143-answered-no-ignored | proposal/correction-phrasings | killed |
| newproject143-intake-projects-built | activation/factory-intake-current | killed |
| newproject143-paused-factory-owners-taken | activation/factory-paused-resumed | killed |
| newproject143-new-projects-in-snapshot | activation/new-projects-kept | killed |

## What I ran

- Suite 110 at 6dac0cb8 through `round2/sandbox_run.py` with its stage and agent stand-ins: the suite exited 1, with 76 passed and red
  only service/hand-off (this sandbox refuses AF_UNIX). This matches round5/110-head.json.
- The nine mutations above, the same way, with each run's failed rows read from its record.
- Scratch calls to `correction_problems` from the 6dac0cb8 and ad37b673 modules, for the phrasings above, and
  `round5/phrasings.py` on the 6dac0cb8 module: it exited 0, with 0 cases not as expected.
- `.veldo/validate.py all`: exit 0.
- Not run: scripts/verify.sh, suite 66, the consumer suites (83, 92 and 93 among them), the re-anchored mutations and
  the other 31 cases of finding 143. R5-3 was shown by reading. Nothing contacted an outside service, and the worktree
  was unchanged apart from this file.
