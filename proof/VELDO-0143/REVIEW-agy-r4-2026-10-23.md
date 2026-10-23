VERDICT: HAS DEFECTS (R4-1 medium, R4-2 medium, R4-3 medium, R4-4 low, R4-5 low, R4-6 low)

# VELDO-0143 round 4: fix review (agy, 2026-10-23)

Fresh context, independent of the builder. Worktree at 91b9291c, range 2ac953ea..91b9291c. Read: the round 3 review,
round4/README.md, DECISIONS 23 and 24, the specification's round-4 footprint, every engine change in the range
(control_workflow_cycle_pm from_line and _cycles, control_service Line.run, wants_cycles, build_cycles and
FactoryLoop, control_service_projects NewProjectPass.activate, control_project_proposal mentions, affirmed, negated
and correction_problems), the three new rows of suite 110 and the five new and three re-anchored mutations. Each
`.veldo/` copy of the four changed modules is byte-identical to its `engine/.veldo/` file.

## Summary of the four questions

1. R3-1 is fixed as the review asked. A failed from_line puts the registry back, and the once-only owners now come
   first, so a refused build on the service's one connection never replaces backlog_operation or team_operation.
   Another line's refused build is a fault once and is not tried again. The factory line keeps the owners in every
   visit order, after a restart too. The activation's restore has a side effect, though: the factory line's intake
   no longer knows the new project (R4-3, a regression against round 3). There are also two narrow gaps in the
   ordering and atomicity claims (R4-5, R4-6).
2. R3-2 is fixed for the review's phrasings. "not bcengi" is refused, and "no, bcengi", "bcengi not personal" and
   "keep it private, not public" settle the way he means them. "anything but public" still passes wrongly (entry 24
   records this as a known limit). Other phrasings that still pass wrongly, measured: a word at the end of a
   sentence ("Keep it private, not public." keeps public, R4-1). "neither X nor Y" and "don't use X and Y", which
   round 3 refused and round 4 accepts (R4-2). Negators missing from the list: "cannot", "dont", "neither",
   "nothing", "except", "other than", "avoid" (R4-4). And a negator after the word ("public? no").
3. Each new row fails without its fix. I reproduced the builder's falsifier records independently (section 5).
4. New defects: R4-1 to R4-6 below. The security-relevant ones come first: R4-1 and R4-2 let a correction the owner
   ruled out by name settle, and the one judge `settled()` uses the same function, so creation is not blocked
   either. I found no credential, logging or outside-service change in the range.

## Findings

### R4-1 (medium): the owner's negated word goes unseen when it ends a sentence, so the value he refused stays

- Where: engine/.veldo/control_project_proposal.py:138 (`_WORD_EDGE = r'[A-Za-z0-9_.-]'`), used by `mentions` at
  :220 to :229; the rule "a value he was shown and negates does not stay" at :283 (identity) and :289 to :290
  (visibility).
- Mechanism: `mentions` finds a value only as a whole word, and its right edge counts `.` and `-` as word
  characters. So "public." and "bcengi." are no mention at all. `negated()` then returns False, and the value he was
  shown stays. For a changed value this fails safe (not named, so refused), but for the kept value it fails open.
  Entry 24 says "Every misreading fails toward refusal where a negator is present". That does not hold here.
- Scenario (measured with a scratch call to correction_problems at 91b9291c): proposal shown under personal,
  visibility public. The owner returns "Keep it private, not public." The PM's corrected document keeps public.
  correction_problems returns [] and the decision settles. `settled()` gives the same answer, so the provisioner
  creates a public repository he refused in so many words. The same holds for identity: shown bcengi, he writes
  "Not under bcengi.", the PM keeps bcengi, and it settles. Without the final period both are refused. This is the
  round 3 review's own example sentence with a period added, and a final period is the normal way to type it.
- Fix: in `mentions`, do not let a sentence-ending period (or a hyphen followed by a space or the end) extend the
  word. For example, take the right edge as `(?![A-Za-z0-9_-]|\.[A-Za-z0-9_])`. Better still, make the kept-value
  check fail closed: count a value as negated when any case-insensitive occurrence of its word, whatever surrounds
  it, has a negator before it in its clause. Add rows to proposal/correction-negated with a final period on both the
  kept-identity and the kept-visibility case, and register a mutation that restores the current edge.

### R4-2 (medium): round 4 accepts a changed identity that round 3 refused, when he rules out both

- Where: engine/.veldo/control_project_proposal.py:215 (`_NEGATOR` has no "neither"), :217 (`_CLAUSE` ends a clause
  at "and"), :281 (`said` counts only affirmed identities).
- Mechanism: round 3 required the one identity named, and both are named, so it refused. Round 4 drops a negated
  identity from `said`. If one of the two refused identities is seen as negated and the other is not, the other one
  becomes "said".
- Scenarios (measured, round 3 module from 2ac953ea against the round 4 module):
  - Shown bcengi. He writes "neither personal nor bcengi" and the PM corrects to personal. "nor" negates bcengi;
    "neither" is not a negator, so personal is affirmed. Round 3 refused this (invalid_input:correction:identity).
    Round 4 settles it.
  - Shown bcengi. He writes "don't use bcengi and personal" and the PM corrects to personal. "and" starts a new
    clause, so personal is affirmed. Round 3 refused; round 4 settles.
  - In both cases the repository is created under an identity he refused by name. That is exactly what R3-2 set out
    to prevent, and it is a new wrong pass the round-4 rule introduced.
- Fix: add "neither" to the negators. Do not end a negator's clause at "and", "or" or "nor" when the next word is
  itself a value of the same field. Or treat a sentence that negates one value of a field and affirms another
  through a bare conjunction as ambiguous and refuse it. Add both phrasings as rows.

### R4-3 (medium): after an activation, the factory's intake does not know the new project until the service restarts

- Where: engine/.veldo/control_service_projects.py:298 to :303 (the activation puts the whole registry back);
  engine/.veldo/control_workflow_cycle_pm.py:646 (the factory line's Intake takes its `projects` list once, when
  it is built); engine/.veldo/control_intake.py:505 and control_intake_routes.py:109 (the transitions take their
  candidates from that list).
- Mechanism: the activation builds an Intake whose projects include the new project, and that Intake registers
  intake_record, intake_question_asked and intake_route. Round 4 then restores the registry, which puts back the
  factory line's Intake. That Intake was built before the project existed, and nothing rebuilds it in this process.
  In round 3 the activation's Intake stayed registered: the new line's failed from_line replaced only Backlog and
  Teams, both before the allocation attach.
- Shown here: I added a probe to a copy of suite 110, in activation/factory-line-kept after the activation and the
  two loop passes. It reads the Intake bound to each of the three intake operations. At 91b9291c each one's
  projects lack `kestrel`. On the round-3 engine (the four modules from 2ac953ea) each one's projects include it.
- Scenario: the owner creates `kestrel` from chat and it activates. His next message naming kestrel, or the
  factory PM's existing_project route to kestrel, is judged against candidates without kestrel. An explicit project
  is refused unauthorized:project, and an implicit one is not hinted, so it falls to the factory or to "which
  project?" offering only the old projects. That is the problem the specification's background describes, back
  until the next restart. No row runs intake after an activation.
- Fix: restore only the owners that must stay the factory line's (allocation, snapshot, backlog, team, grooming
  and the cycles' record). Or, after the restore, rebuild the factory cycles' intake with the current project rows
  (its constructor registers it). Or have Intake read the project rows when the transition runs, not when it is
  built. Add a row: after activation/factory-line-kept's passes, a message naming the new project is recorded with
  it as a candidate, and the factory PM's route to it is accepted.

### R4-4 (low): common negators are not in the list, so the negated value passes

- Where: engine/.veldo/control_project_proposal.py:215.
- Measured wrong passes, shown personal/public with public kept, or shown private with the PM moving to public:
  - "it cannot be public": "not" inside "cannot" fails the left edge, and there is no n't.
  - "dont make it public": chat without the apostrophe.
  - "nothing public please".
  - "neither public".
  - "except public" and "other than public".
  - "avoid bcengi" with bcengi kept.
  - "public? no" (entry 24 records this one).
- Entry 24 lists "anything but" and a negator after the word as limits, but not these. "cannot" and "dont" are a
  negator present in his words that the rule does not see, which contradicts the entry's "fails toward refusal where
  a negator is present".
- Fix: add cannot, dont, wont, cant, didnt, neither, nothing, except, other than, avoid. Or, more robustly, refuse
  any correction whose rationale contains a word from a broader negation set anywhere in the value's sentence and
  ask again. Record whatever remains as a limit in entry 24.

### R4-5 (low): a line that built cycles while the factory line did not want them keeps the owners for good

- Where: engine/.veldo/control_service.py:2028 to :2029 (the deferral applies only while `factory.wants_cycles()`),
  :2034 to :2035 (the factory line's own refused build raises on every pass).
- Scenario (by reading): the factory project is PAUSED (control_project pause) when the service starts, and no
  other active project executes in the factory line's repository. The taken-on new repository's project is ACTIVE.
  The factory line does not want cycles, so the new line's build is not deferred: it succeeds and holds the
  allocation and snapshot authorities. When the owner resumes the factory project, the factory line's from_line is
  refused invalid_registration on every pass. Intake routing, new-project proposals and corrections stay stopped
  until another restart. The same happens in-process if the factory line has never built (factory project paused
  since start) when a settled decision activates. DECISIONS 23 says the factory line keeps the owners "whatever
  order the loop visits lines in". That holds for visit order, but not for the order in time.
- Fix: until VELDO-0188, defer another line's build whenever the factory line exists and has no cycles, whether or
  not it wants them now. Or, when the factory line comes to want cycles and another line holds them, drop that
  line's cycles (record a refusal), restore the registry as it was before that build, and build the factory's.

### R4-6 (low): a failed from_line can strip the NewProjects registration it created, for the life of the process

- Where: engine/.veldo/control_workflow_cycle_pm.py:614 and :621 to :622 (whole-registry snapshot and restore) with
  :653 (`service.new_projects()` builds and caches NewProjectPass.decisions on first use; its constructor registers
  `new_project_record`, control_project_proposal.py:745).
- Mechanism (by reading): in the serve loop, `service.loop.run()` comes before `new_project_pass()`
  (control_service.py:2721 and :2727). So the factory line's first from_line is usually what first builds
  NewProjects. Suppose the build then raises after :653, for example in Grooming's input checks or in
  ProjectCycles' declare_owners (BEGIN IMMEDIATE on a locked store the first time its rows are declared). The
  restore then removes `new_project_record`. The cached NewProjects object survives, and `new_projects()` never
  builds it again, so the factory line's successful retry on the next pass leaves the operation unregistered. Every
  new-project decision write is then refused unregistered_operation until a restart.
- Fix: call `service.new_projects()` before taking `before`, or restore only the keys the build itself added or
  replaced that belong to objects it discards.

## Each new row fails without its fix (independent runs)

| Check | Result here |
| --- | --- |
| Suite 110 at 91b9291c, in this worktree | exit 1; 96 passed, 1 failed: activation/first-unit (invalid_registration, as approved for VELDO-0188). Same as the host. |
| Suite 110 on 91b9291c with the four modules (both copies) from 2ac953ea, a git archive in /tmp | exit 1; red: proposal/correction-negated, activation/factory-line-kept (take no_such_feature; the new line faulted on both passes), activation/factory-line-restart, activation/first-unit. Matches round4/110-round3-engine.json (service/hand-off is green here). |
| newproject143-cycles-owners-after | killed (factory-line-kept and factory-line-restart red) |
| newproject143-refused-cycles-retried | killed (factory-line-kept red) |
| newproject143-factory-owners-taken | killed (factory-line-restart red) |
| newproject143-activation-owners-left | killed (factory-line-kept red) |
| newproject143-negation-ignored | killed (correction-negated red) |
| re-anchored newproject143-correction-identity-unbound and -visibility-unbound, and newproject143-line-not-added | each killed (its target row red) |

Each mutation was applied by exact replacement, from check_teeth_mutations.cases(), to both copies of the module in
a git archive copy in /tmp. Each old text occurred exactly once. The rows bind what the review asked for: the
factory line's backlog take on its own repository, the registry's backlog, team and snapshot owners, a single
refusal of the new line, and the restart order with the new uuid first. What they do not bind: intake after the
activation (R4-3), a final period or the regression phrasings (R4-1, R4-2), and the factory project paused at start
(R4-5).

## What I ran

- `python3 scripts/selftest.py` with the suite option for 110_veldo_0143_new_project, in this worktree: exit 1, 96
  passed, 1 failed (above). The worktree was unchanged afterwards.
- The round-3-engine comparison, the eight mutations and the intake probe: in git archive copies under /tmp, with
  the same selftest command. I read each exit status directly.
- Scratch calls to correction_problems from both the round 3 and the round 4 module, for the phrasings above.
- `.veldo/validate.py all` on an archive copy: exit 0 (without git, as it reports).
- Not run: scripts/verify.sh, suite 66, the consumer suites, the falsifiers of earlier rounds, and the R4-5 and
  R4-6 sequences as live runs (shown by reading). No outside service was contacted.
