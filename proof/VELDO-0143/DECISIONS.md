# VELDO-0143: spec-interpretation decisions for the reviewer

Each entry is a place where the specification's words admit more than one reading. For each: the sentence, the
reading this branch implements (and where), and the alternative not taken. The reviewer judges each one; none is
settled by this file. Entries 1 to 12 are the implementation's (README "Assumptions and limits", the
specification's history of 2026-10-22, and the code); entries 13 to 16 come from the rebase onto VELDO-0161
round 5 (REBASE.md). This list was rebuilt from the bundle, the specification and the code, not copied from the
earlier session's final message, which is not available to this session. If that message named a decision
missing here, it is not deliberately left out.

## AC1

**1. A correction settles without a second presentation.**
- Spec: "His one answer, a yes or a correction, settles the project and the first objective, and no further
  question is sent."
- Choice: when his answer returns the proposal with his words (or approves it without naming one of the offered
  identities), the factory PM's next run reads the proposal and his words and returns a corrected document,
  which settles the decision with nothing shown to him again (`control_project_proposal`, ONE ANSWER,
  `correction`). A corrected document that still names no identity fails the decision by name.
- Alternative: show him the corrected proposal for a yes. That is the second question the sentence forbids, but
  it means a correction is settled on the PM's reading of his words, which he never sees before it acts.

**2. When the identity was not said, every configured identity is offered in the same request.**
- Spec: "the identity (asked in the same request when he did not say)".
- Choice: the one proposal carries one complete entry per configured identity (directory, mode, remote,
  adoption), and his approving answer resolves it by naming exactly one of them, by id or label as a whole word
  (`identity_named`). Approving without naming one counts as a correction (entry 1).
- Alternative: propose the identity's default (or the workspace's) and let his yes accept it, or ask a separate
  identity question first. The first picks something he did not say; the second is a second question.

**3. When "his message already names the project and the identity".**
- Spec: "nothing is asked when his message already names the project and the identity ... the first message,
  which named both, is itself that answer and nothing is presented."
- Choice: three conditions together (`nothing_asked`): the message is the factory owner's own authenticated
  message (his intake source), the PM's document names an identity, and the message text contains both the
  project name and that identity's id or label as whole words, case-insensitive. The PM's reading alone is not
  enough.
- Alternative: trust the factory PM's document whenever it names both (no textual check), or require an exact
  phrase form. The first lets the PM infer an identity he never said; the second rejects natural wording.

**4. The factory project's own repository is no line.**
- Spec: "Setup creates the one `factory` project, bound to a small repository of its own under the factory state
  root that holds only its team configuration, with a PM role ..."
- Choice: setup creates `<state root>/factory` holding only `team.json`, enrolled and bound, and activates the
  factory project on it (`control_factory_setup.factory_repository`), but the factory loop gives it no line: the
  factory project's PM cycles run on the work configuration's first line (`FactoryLoop.factory_line`).
- Alternative: make it a full line (its own receiver configuration, workspace, Runner and Gate). That serves a
  repository with no code to build, and its cycles would need a worker profile of their own.

**5. A factory set up before this change.**
- Spec: AC1's setup sentence (entry 4) describes a fresh setup.
- Choice: a re-run of setup neither moves an existing factory project off the workspace's repository nor requires
  the factory repository; such a factory has no provisioner configuration until set up anew, and its new-project
  decisions wait, refused `unavailable_service:provisioner` by name.
- Alternative: migrate on re-run (create the factory repository and re-bind the factory project). That rewrites a
  live project's execution repository, which nothing in the specification authorizes.

## AC2

**6. "A registered protected effect".**
- Spec: "by the repository provisioner as a registered protected effect whose steps run in order".
- Choice: a named effect, `repository_provisioning` (`control_effect_executor_creation.EFFECTS`,
  `control_service_projects.PROTECTED_EFFECTS`), that only the running authority service starts, as its own
  process, with the supervisor-side 0600 provisioner configuration, for a decision the one judge calls settled.
  No worker can name it, its configuration or its evidence.
- Alternative: a VELDO-0028 effect handle a worker requests and the executor carries out. That puts repository
  creation within a worker's reach, which the threat model ("a repository created without a settled owner
  answer") argues against.

**7. Which step failures are real conditions and which are injected.**
- Spec: "Fail each step in turn against a disposable remote and require the repository record `failed` with that
  step named and no later step run."
- Choice: init, scaffold, the token, an existing remote, GitHub answering another owner, a refused creation and a
  refused push are real conditions against the loopback GitHub stand-in and real Git. The author and commit
  failures are injected by replacing that step's function in the effect's step table, since a real failure of
  `git config` or `git commit` on a fresh repository has no clean trigger.
- Alternative: make author and commit fail for real (a read-only `.git/config`, a full disk). Those fixtures are
  fragile and platform-bound.

**8. "A directory that exists and is not empty".**
- Spec: "refuses a directory that exists and is not empty, and takes the adoption path (VELDO-0161) when it is
  already a Git repository".
- Choice: an existing empty directory is used; a symlink and a non-directory are refused as
  `directory_not_empty:link` and `directory_not_empty:not_a_directory`; a directory outside the identity's
  projects root is refused `invalid_input:directory:outside_projects_root`. "Already a Git repository" is judged
  when the proposal is made (`mode: adopt`, with its scaffold commit laid before he is asked); a directory that
  became a repository after he answered a creation proposal is refused `stale_subject:directory_is_a_repository`,
  not adopted.
- Alternative: refuse an existing empty directory too, or switch to adoption at provisioning time. The latter
  adopts on terms he never saw.

**9. Visibility: "private unless he said otherwise".**
- Choice: the PM's document carries the visibility only when he said one; otherwise the identity's
  `default_visibility`, else `private`.
- Alternative: always `private` unless he said otherwise, ignoring the identity's configured default. The
  identity default is configured by the owner, so it is read as part of "unless he said otherwise".

## AC3

**10. The first objective accepted by his answer, an objective that did not exist when he answered.**
- Spec: "its first objective is accepted by his answer, or by his first message when it named both (VELDO-0150),
  and admitted at the default priority with no further question".
- Choice: a new acceptance path, `new_project` (`control_objective.accept_decided`): the objective is proposed by
  the new project's PM after activation, with the proposal's first objective as its outcome, and accepted by the
  settled decision (`via: answer` or `via: own_message`). Work under it is admitted at the default priority with
  no question (`control_grooming_request`, `control_backlog`), as VELDO-0079 admits work under an objective his own
  message accepted.
- Alternative: create the objective when the proposal is presented and accept it through VELDO-0077's acceptance
  by answer. That makes an objective in a project that does not exist yet.

**11. "Observe the owner told ...".**
- Spec: "Observe the owner told 'tidepool is ready; the first objective is next'".
- Choice: the decision record's event `project_ready`, reported by VELDO-0128's reporter through its one rendered
  send (VELDO-0168), with a failed repository reported as "<name> could not be set up." The service's pass sends
  nothing itself.
- Alternative: a direct Telegram send from the service's pass. That adds a second send site beside the reporter.

**12. "The first unit dispatched in the new repository with the identity as author".**
- Choice: the factory loop gains a line for the new repository (`FactoryLoop.add_line`) with the roles of the
  loop's first line (the factory default team's builder and reviewers, `land` removed), its own receiver
  configuration, workspace and Gate; its accepted base revision is the commit it was created or adopted at; the
  default team's capability configurations are copied into it at the revisions the team names. The row proves the
  line and the author; the dispatch itself comes after the new project's PM cycle, which needs the graph runtime
  (host run 2).
- Alternative: derive the line's roles from the new project's own team revision. The new project's first team
  is that default team, but the work configuration's roles are what the loop's Runner dispatches with.

## From the rebase onto VELDO-0161 round 5

**13. The creation path makes every store and host refusal before anything is made.**
- Spec (VELDO-0161, adopted here): the adoption effect's checks "that change nothing, before anything is moved or
  pushed". VELDO-0143 AC2: "steps run in order, each recorded, stopping by name at the first failure."
- Choice: before the directory step, the provisioner checks the host trust and the adoption signer's enrollment,
  the identity binding (check only), the store's binding and the generation (`preflight`). A failure there writes
  the record `failed` at the step it refuses for (`signature`, `identity`, `binding`), so its history is
  `settled, <step>`, not a later creation step.
- Alternative: keep those refusals at their own steps after the push, as round 1 did. Then a misconfigured host
  creates a GitHub repository and pushes before failing.

**14. The created repository's own configuration is judged before GitHub is asked.**
- Choice: after the commit step and before the remote step, `refuse_commands` (the local steps' allowlist, and no
  borrowed objects) and `refuse_transport_config` (the identity transport's own judge for the remote URL). A
  refusal is recorded at the step it prevents, `remote`.
- Alternative: judge only at the push, as the transport already does. Then a GitHub repository is created for a
  push that will be refused. A dedicated `checks` step name was also possible; it would add a history entry to
  every successful run, which AC2's recorded order does not name.

**15. VELDO-0161's INTERRUPTED rule and lock apply to a created record.**
- Choice: a run holds the adoption effect's lock for the repository; a record this decision left `provisioning`
  with no binding is written `failed` `unknown_outcome:interrupted` at its last step (what was made stays, for
  the owner, per the rollback field); a live run's lock refuses `stale_subject:provisioning_in_progress`. The
  service starts the provisioner once more, once per instance, for such a record (it judges it, or refuses
  while that run still lives).
- Alternative: leave a creation interrupted mid-way `provisioning` for the owner. Then the decision never settles
  and he is never told.

**16. Where the new-project pass is triggered.**
- Spec (VELDO-0161, kept): the take-on is synchronous over the socket and nothing polls. VELDO-0143 AC3: "After
  creation and its adoption ... reaches `active`, the settlement is applied as the project's activation."
- Choice: the pass runs when it is due: at the instance's start, after a packet or channel pass that advanced the
  journal (`hint_after`, which includes a take-on the instance answered), and at a provisioner's end, which the
  serve loop's poll set sees on its output pipe. It no longer runs on every loop iteration behind a journal
  watermark comparison.
- Alternative: let the service take a created record on itself when its provisioner ends, rather than relying on
  the provisioner's socket hand-off. That adds a second take-on path beside VELDO-0161's one and would hide a
  failing hand-off. Not taken: a record whose hand-off failed waits for an instance's start, exactly as an
  adopted one.

## Round 3: the first independent review (REVIEW-claude-2026-10-23.md)

Entries 1, 2 and 5 above are changed by round 3 as follows; the text above is kept as it was reviewed.

**17. A correction is bound to his words (F2; changes entry 1).**
- Spec: "His one answer, a yes or a correction, settles the project"; threat model: "a remote created under the
  wrong owner". Entry 1's correction is still settled with no second presentation, but the PM's corrected
  document settles it only when each term is the one he was shown or the one his words say
  (`control_project_proposal.correction_problems`, applied in `correct()` before anything is built and again
  in the one judge, `settled()`): the name (presented, or named in his words), the identity (presented, or the
  one configured identity his words name), the visibility (shown for that identity, or named in his words) and
  the mode (as shown for that identity and name; a name or identity he was not shown is a creation, so an
  adoption is only ever one he was shown, with the scaffold commit shown, kept rather than laid again). Anything
  else fails the decision by name, `invalid_input:correction:<field>`, and its report tells him.
- Also bound here, beyond the review's three fields: the project's name, by the same sentence of the task ("No
  repository is created or pushed on terms he did not say or see"). The first objective's text is not bound:
  it is free text the PM states and he can read in the report; nothing textual can judge it.
- Alternative: show the corrected proposal for a yes (a second question), or trust the PM (the review's F2).

**18. An approval that names no offered identity fails by name (F2; changes entry 2).**
- Spec: "the identity (asked in the same request when he did not say)". The identity was asked and his answer
  did not say it. Of the review's two options this branch takes the first: the decision is `failed`
  `invalid_input:answer:identity` in `apply_settled`, nothing is chosen and nothing reaches the PM. The judge's
  correction path now requires a returned proposal (`return_for_elaboration`).
- Alternative: hand it to the PM and refuse its document unless his words name one. That is the same outcome a
  run later.

**19. One project per name (F3).**
- A name that is already a project's, or another live decision's (presenting, presented, correcting, settled),
  compared without case as GitHub compares, is refused `stale_subject:project_exists` before he is asked; the
  decision is `failed` so the message is not proposed again, and he is told. An activation that finds the name
  taken meanwhile fails the decision `already_exists`.

**20. Recorded before presented (F4).** The decision is written `presenting` with the proposal, the request's
  alias and its deadline before the presentation; the next new-project pass finishes an interrupted one from the
  record with the same commands (the store replays them, the presenter never sends twice).

**21. No proposal without a provisioner configuration (F6; changes entry 5).** A factory with none (set up
  before this change, or upgraded: VELDO-0161's upgrade lays the adoption signer but not `host/provisioner.json`)
  fails a new-project decision `unavailable_service:provisioner` at the proposal, so nothing is asked, and its
  report tells him why. A settled decision whose service has no configuration is failed the same way rather than
  left waiting.

**22. The pass is due when a decision is written outside it (F1).** `NewProjects` calls `notify` after every
  decision it writes; the running service's pass sets `projects_due` unless the write is its own, so a decision
  the factory PM's run settles in a factory loop pass reaches the provisioner in the same serve loop iteration.
  The review's other option (reading the watermark around `service.loop.run()`) would also make the pass due
  after every unrelated loop pass.

**23. The factory line keeps the connection's owners; a line whose cycles cannot be built damages nothing (R3-1).**
- Until VELDO-0188 runs several lines' project cycles on the service's one connection, the line the pass adds for
  a new project cannot build its cycles there (the allocation and snapshot authorities register once per
  connection). Round 3 let that build register its backlog and team owners first and then fail, on every pass,
  so the factory line's backlog commands ran with the new repository's id and workspace.
- `control_workflow_cycle_pm.from_line` is failure-atomic. It attaches the once-only owners first
  (`control_alias.attach`, then `control_readset.attach`, handed to `ProjectCycles`), and the inbox, backlog,
  team, intake and grooming owners only after both hold. A build that raises puts the connection's registrations
  back as it found them.
- `Line.build_cycles`: while the loop's factory line wants cycles it has not built, no other line builds any.
  This holds whatever order the loop visits lines in (sorted repository uuids), so it holds after a restart too.
  The visit order is left as it was: the deferral alone holds the property, and a visit-order change would add
  nothing a row can tell apart. Another line's refused build is a fault of the pass it was refused in
  (`pm_cycles:<code>`) and is not tried again in this process. The factory line's own build is tried on every
  pass until it holds, as before.
- One change in behaviour: a refused build no longer ends the line's part of the pass. The line still offers its
  assigned units through its own Runner, which needs no project cycles. So activation/first-unit is now red only
  on its first part (the new line's cycles), and its dispatch, packet and author parts are green here.
- Also beyond the review's two files: the activation step (`control_service_projects` NewProjectPass.activate)
  builds its own Projects, Teams, Intake and Objectives on the same connection. Their constructors replace the
  factory line's team and intake owners (Teams with requester `pm`). The activation now puts the connection's
  registrations back when it is done, and only then gives the loop the new line.
- Alternatives: keep `add_line` out of the pass and the constructor. That undoes F5's line, which AC3 needs for its
  dispatch. Or mark added lines to build no cycles at all. That is the same outcome with the refusal hidden.

**24. A word he negates is not said: the limit of a textual binding (R3-2; changes entry 17).**
- A changed identity or visibility counts as said only where his words name exactly that one value of the field
  and do not negate it. An identity or visibility he was shown, and whose word he negates, does not stay. That
  second rule is beyond the review: a correction settles with no second presentation, so "not under bcengi"
  with bcengi kept would otherwise create the repository he ruled out.
- What counts as a negation (`control_project_proposal.mentions`): a negator before the word in its clause. The
  negators are not, no, never, nor, without, instead of, rather than, and any word ending n't. The clause is the
  words since the last `, . ; : ! ? ( )`, line break, or "but", "and", "so". The review's sentence reads "keep it
  private, not public", with no word between "not" and "public". But its first clause is "not under bcengi", and
  "don't make it public" puts words between the negator and the value. Strict adjacency would miss both, so the
  clause is the window. "nor" and the n't contractions (isn't, shouldn't, won't) are additions to the review's list.
- Round 5 (R4-1, R4-2, R4-4; entry 25) widens this. The negators are now also neither, nothing, cannot, avoid,
  except, other than, anything but (its "but" ends no clause), and dont, wont, cant, didnt and the other
  apostrophe-less forms of the n't auxiliaries (isnt, doesnt, shouldnt and their kind). A "? no" (or "? not",
  "? never", "? nope") right after the word negates it. An "and" whose next word is another value of the same
  field ends no clause, and "or" and "nor" never end one. A word ends at a final period or hyphen. A value he was
  shown stays only where no occurrence of its word, whatever follows it ("publicly", "bcengi-owned"), has a
  negator before it in its clause. Words that negate one value of a field and affirm another through a bare "and"
  ("don't use bcengi and use personal") are refused as `invalid_input:correction:<field>:ambiguous`.
- Round 6 replaces this reading (entry 26). The clause, the negator list above, "? no", the "and" rule and the
  `:ambiguous` refusal are gone from the module. The round-5 limit list that stood here is withdrawn: four of its
  items were not measured (R5-4), and it left out the fail-open cases of R5-1 and R5-2.
- Round 7 (entry 28) withdraws the textual binding of the identity and the visibility altogether: no text is
  read for either, so this entry has no limit list for them. What stands in its place is what the choices
  guarantee (entry 28).

**25. Round 5: what the round 4 review's fixes chose (R4-1 to R4-6).**
- R4-1 and R4-2 were fixed in round 5 by widening the clause reading (a word's edge at a final period, a kept
  value failing closed, "neither", the "and" before another value, the `:ambiguous` refusal). Round 6 removes
  that reading and replaces it with entry 26's rule, and round 7 removes that for the identity and the
  visibility (entry 28). The word edge stays only for a project's name and the identity his own message names
  (`names`); since round 7 no approval is read for an identity.
- R4-3, Intake reads its projects when they are judged. `Intake(projects=...)` takes a list, as every caller
  before, or a callable called each time a transition (record, route) judges candidates. The factory line's
  intake and the activation's are given `control_intake.store_projects` over the service's connection, the
  project rows there when the transition runs. So no restore and no rebuild can leave it stale. The activation
  still puts back only what was registered before it (the factory line's and the service's owners) and drops
  what it added (its own Projects, Teams, Intake and Objectives, bound to its coordinates). The intake it puts back
  is the factory line's, which now knows the new project. `control_intake.py` is outside this specification's
  footprint as it was; it is added for this one change (a property and a module function; no caller with a list
  behaves differently).
- R4-5, the deferral is wider than the review's wording, by one condition. Another line builds no cycles while
  the factory line has none and the store has a factory project that can still run (round 6, entry 27: not
  CANCELED or COMPLETED). "Whenever the factory line
  exists" alone would also hold back every line of a loop with no factory project at all (a factory set up
  before VELDO-0143, or the consumer suites' loops), whose first line is the factory line by definition and never
  wants cycles. With no factory project there is nothing to keep the owners for.
- R4-6, `service.new_projects()` is built before from_line takes the registrations, under the same conditions
  as before (a channel and a factory project). A failure in that build is the factory line's pass fault, as
  any other, and nothing is cached by a build that raised.

## Round 6: the round 5 review (REVIEW-claude-r5-2026-10-23.md)

**26. A correction binds a value by a rule that does not read negation scope (R5-1, R5-2, R5-4; replaces the
reading of entries 24 and 25).**
- Why. Rounds 3, 4 and 5 each widened a reading of which value a negator applies to, and each review found
  phrasings that pass a value he refused or replaced: "use personal and make it private" with bcengi/public kept
  (R5-1), "not-public", a negator on the line above, "public!? no" (R5-2). Reading negation scope in free text
  cannot be made complete. The owner chose (round 6 brief) a rule whose safety does not depend on it.
- The rule (`control_project_proposal.correction_problems`, `named`, `negates`, `bound`). For the identity and
  the visibility: his words NAME a value wherever its word (an identity's id or label) occurs in them, ignoring
  case, even inside another word. They NEGATE where any negator of `_NEGATOR` stands anywhere in them: on any
  line, at any distance, joined by a hyphen, underscore or period or not, "no" as a word, after a "?" or "!", the
  prefix "non", any word ending n't with any apostrophe, the apostrophe-less forms (dont, wont, cant, didnt and
  their kind), and a broad set of others (neither, nor, none, nothing, never, without, cannot, avoid, except,
  instead of, rather than, other than, anything/everything/all but, skip, drop, remove, refuse, reject, decline,
  against, wrong, stop, hate, dislike, mistake, forget, nope, nah, nicht, kein, nein, pas, and the Russian
  ne, net and ni, written as escapes). A value other than the one he was shown settles only where his words name exactly that value of the
  field and negate nothing. The shown value stays only where his words name no value of the field at all. A
  changed project name settles only where his words name it and negate nothing; the mode is the one shown for
  that identity and name, as before. Every other reading fails the decision `invalid_input:correction:<field>`
  before anything is built, `settled()` refuses it again, and his report says, in plain words
  (`control_telegram_report.CORRECTION_UNCLEAR`), that the project could not be set up, that the correction did
  not make the identity (or the visibility, or the name) clear, the rule, and to ask again with one clear choice.
- The trade-off, by choice. An honest correction with a negator in it is refused rather than guessed, and so is
  one that names the value it keeps. He is told why and answers again. The cost is a second message from him;
  the alternative was a repository under an owner or a visibility he ruled out.
- Round 7 replaces this rule for the identity and the visibility (entry 28): a correction never changes either,
  and no text is read for them. The round-6 lists of what the rule guaranteed, refused and let through for those
  two fields are withdrawn with it; R6-1 to R6-3 (substring naming, an unnamed rejection kept, lookalike
  characters) and R6-4 (this entry's list) were findings against them. What stands in their place is what the
  choices guarantee, in entry 28, each measured. For the project's name the rule stands: a changed name binds only
  where his words name it as a whole word and hold no negator anywhere, and a name kept while his words name
  another ("call it reef-watch" with the presented name kept) still settles, since names are not an enumerable
  field.
- Removed with the clause reading (mutations too, finding 143): `_CLAUSE`, `_ANSWERED_NO`, `_clauses`,
  `_occurrences`, `mentions`, `affirmed`, `negated`, `ambiguous` and the `:ambiguous` code; the cases
  newproject143-negation-ignored, -word-edge-period, -kept-value-whole-word, -and-ends-clause,
  -ambiguity-ignored, -negators-round4 and -answered-no-ignored. Their places are taken by
  newproject143-kept-while-named (R5-1), -hyphen-negator-ignored and -negation-affirms (R5-2), -negators-narrow
  (the negator set) and -correction-told-code (the plain words).

**27. A line defers to the factory line only while the factory project can still run, and says so (R5-3).**
- `Line.build_cycles` defers another line's cycles only while a factory project is in a state other than
  CANCELED or COMPLETED (`control_service.FACTORY_ENDED`; both are terminal in entity_contract's project
  lifecycle) and the factory line has no cycles. Each pass that defers appends `{'repository': ...,
  'reason': 'pm_cycles:deferred_to_factory_line'}` to its faults, so the pass report says why that line's
  project runs no cycles. Rows activation/factory-canceled (a canceled factory project, and the first line that
  wants cycles builds them at the first pass), activation/factory-paused-resumed (each paused pass names the
  deferral) and activation/factory-line-restart (the first pass names it). Mutations
  newproject143-ended-factory-deferred and -deferral-unreported.
- The paused-factory cost, until VELDO-0188. While the factory project is PAUSED (or ACTIVE with its line's
  build not yet held), every other repository's project cycles do not run: one connection holds one set of the
  cycles' owners, and the factory line keeps them. The owner sees `pm_cycles:deferred_to_factory_line` for each
  such line in every pass, and resuming the factory project ends it. A factory whose project is canceled or
  completed no longer holds the other lines. VELDO-0188 gives every project's line its own cycles and removes
  the deferral.
- A deferral entry is a fault, so it is counted in the loop's status (`counts['faults']`) like the refusal entry
  beside it. A loop that defers on its first pass, before the factory line builds later in the same pass,
  reports one entry for that pass; the restart row measures it.

## Round 7: the round 6 review (REVIEW-claude-r6-2026-10-23.md) and the owner's decision (Telegram 36174, 36175)

Rounds 3 to 6 each found typed wording that binds an identity or a visibility he never chose: R6-1 "Personally"
binds personal, R6-2 "not this account" keeps the refused one, R6-3 lookalike characters. The owner decided
(Telegram 36174 asked, 36175 "Ok buttons", 2026-10-23) that reading free text for these two settings cannot be made
safe: they become offered choices he picks. Entries 2, 3, 9, 17, 18, 24 and 26 are changed by this section; their
text above is kept as it was reviewed.

**28. The identity and the visibility are offered choices he picks; nothing he types sets them (replaces the
textual binding of entries 17, 18, 24 and 26 for these two fields).**
- The mechanism is the channel's own (VELDO-0065's choices: REQUEST_FIELDS `choices`, CHOICE_RULINGS,
  `ruling_of`, the `unmatched_choice` and `unmapped_choice` refusals), extended the way it maps a choice to a
  ruling, with one new choice kind: a pick, `accept` followed by the values it picks, each one word
  (`control_channel_presentation.PICK_WORD`, `pick_of`). Its ruling is approve. The channel matches a typed reply
  to an offered pick as it matches any choice, by folding case, width, spaces and hyphens of the whole choice
  (`offered_choice`), never by its parts; a request whose choices fold alike is not presented
  (`ambiguous_choice`, a new refusal of the same contract). Suite 62's answer/pick-choices is the kind's own row.
- One choice per field became one choice per pair. The owner answers a request version once, with one offered
  choice (VELDO-0065: ANSWERS NAME WHAT WAS SHOWN), so a choice per field could not change both fields in one
  answer, and a second answer is a second question, which AC1 forbids. The per-field sets are therefore offered
  as their combinations: each pick names exactly one configured identity and exactly one visibility
  (`accept bcengi private`). The choices are `accept` (approve exactly what is shown; offered only when the
  proposal shows an identity), one pick for every other pair of an offered identity and a visibility,
  `return_for_elaboration` and `reject` (`control_project_proposal.choices`, `picks`). With the suite's three
  identities that is eight choices, or seven when no identity is shown.
- Every configured identity is offered, always, with its own directory, mode, remote and (for a directory that
  is already a repository) adoption, laid before he is asked as before. When the PM named an identity it is the
  one shown and `accept` approves it; when it named none, nothing is shown and only the picks approve. The PM's
  visibility, or else each identity's default, is the visibility shown (entry 9 stands for what is shown).
- What binds (`answered`, `apply_settled`, and the one judge `settled`): the choice the settlement records. `accept`
  settles the identity and the visibility shown; a pick settles exactly the identity and visibility it names; any
  other choice settles nothing (`invalid_input:answer:choice`). The judge also requires the request's choices to
  be exactly `choices(proposal)` (`no_settled_decision:choices`) and the decision's proposal to be exactly the one
  his choice resolves (`no_settled_decision:proposal`). His reason text is recorded and never read for either
  field (`identity_named` is removed).
- A correction (`return_for_elaboration`) changes only the name and the first objective (`correction_problems`).
  The corrected document's identity and visibility must be null or the ones shown; anything else fails the
  decision `invalid_input:correction:identity` or `:visibility` before anything is built, and the judge refuses
  it again. A proposal that showed no identity cannot be corrected into one (`:identity`): the identity is
  picked, never typed. His report says so in plain words (`control_telegram_report.CORRECTION_UNCLEAR`: "Your
  correction would have set the identity: a correction changes only the name and the first objective; the
  identity and the visibility change only by the choice you pick", and to pick the choice that names what he
  wants). The factory PM's instruction says the same (`control_workflow_cycle_pm`).
- What the choices guarantee, each measured:
  - Each configured identity and both visibilities are offered as choices, and his pick binds exactly that
    value: rows proposal/fields (no identity shown: six picks, rulings approve), proposal/choices (identity shown:
    accept, five picks; a pick binds its pair; accept keeps what is shown, whatever his reason says),
    proposal/one-answer, provision/answered-and-corrected (the picked public is created public, the picked
    organization's remote under it).
  - A choice not offered is refused by name, `unmatched_choice`, with nothing recorded, and the request stays
    answerable: a Cyrillic-e and a fullwidth-b "bcengi" pick, a pick naming an unconfigured identity, the pick of
    the pair `accept` already approves, "use bcengi", "Personally", and `accept` where no identity is shown (row
    proposal/choices; suite 62 answer/pick-choices for the Telegram path).
  - No typed text changes the identity or the visibility. Over every phrasing of the round 3 to 6 reviews (90,
    including "Personally I'd make it private", "not this account", the Cyrillic-e "bcengi", the 140,012-character
    one), each of 16 readings (shown identity and visibility times the PM's), exactly the four readings that keep
    what was shown settle (`round7/phrasings.py`: 0 not as claimed on this module, 79 on the round-6 module, 25
    of them settling a value that was not shown). Rows proposal/correction-phrasings (the same 90) and
    proposal/correction-negated (15 decisions end to end: a reading that changes either field fails by name, one
    that keeps them settles exactly what was shown).
  - The PM's document can never change them: a corrected document naming another identity or visibility fails
    by name (proposal/correction-bound, proposal/correction-negated), and a decision written with an identity
    other than his pick is refused by the judge (proposal/choices).
- The cost, by choice. A correction whose words ask for another identity or visibility ("not this account", "keep
  it hidden") settles what he was shown when the PM keeps those values, since no text is read for them; the brief
  he answered says that only a choice changes them, and a PM reading that changes them fails by name. To change
  the identity or the visibility and the name together, he picks the identity and visibility and corrects the name
  in a later request, or corrects nothing and picks. The choices are typed (`<choice>: <reason>`): the channel has
  no buttons today, and building them would be a second mechanism.
- Removed (code): `named`, `bound`, `identity_named` and the offered entries' `words`; `correction_problems` no longer
  takes the configured identities. Kept: `_NEGATOR` and `negates` (a changed name, and entry 29), `names`,
  `identities_named`. Removed (mutations, finding 143): newproject143-correction-identity-unbound and
  -correction-visibility-unbound (their anchors were the textual binding's `bound` lines), -kept-while-named and
  -negation-affirms (`bound` itself), -bare-yes-corrected (the approval that named no identity: `accept` is no
  longer offered without a shown identity, and the channel refuses it). Re-targeted: -hyphen-negator-ignored and
  -negators-narrow now kill proposal/own-message-doubt, the negator set's remaining use for a decision. Added:
  -identity-from-document, -visibility-from-text, -unmatched-choice-accepted, -pick-ignored,
  -choices-not-offered, -pick-unmapped and -ambiguous-choices-presented (suite 62), and the four of entry 29.

**29. His own message settles unasked only where nothing in it could mean another identity (changes entry 3).**
- AC1 keeps its claim: a message that names the project and the identity is its own answer and nothing is
  presented. That reads the identity from his words, the one place left where text decides it, so it now fails
  closed to a presentation (one choice for him) on any doubt (`nothing_asked`): the message is not plain ASCII
  (`not_plain_text`: lookalike letters, a zero-width space); a negator stands anywhere in it (`negated`); it names
  another configured identity besides the PM's (`identity_not_alone`); or the PM's document sets a visibility
  other than the identity's default (`visibility_not_default`: the PM's document never sets the visibility
  unasked). Row proposal/own-message-doubt ("don't put it under bcengi; ...", "... for bcengi", "n" + Cyrillic o +
  "t under bcengi: ...", "... fell, not-public", and a PM visibility of public), mutations
  newproject143-own-message-visibility, -own-message-negated, -own-message-lookalike and
  -own-message-two-identities.
- Alternative: remove the path, so every proposal is presented. That contradicts AC1's claim and its declared
  falsifier, which the owner's decision did not change; the owner may still choose it.

**30. The provisioner's end alone makes the pass due, on the socket branch too (the host's surviving mutation).**
- newproject143-provisioner-end-unseen survived on the host because service/provisions accepted
  `ended != [] or active_before_start`: over the socket, the take-on the service answered made the pass due
  before the provisioner ended. The row now runs a second provisioner (project atoll) whose take-on is withheld:
  nothing serves the socket (its file is removed; where no socket can be made, there is none), so it ends with its
  record `provisioning` and `not_taken_on:authority_unavailable`, and only its end on the output pipe can make the
  pass that names that answer due. The row requires exactly one `ended` event for it with that refusal, on both
  branches. The next instance's take-on and pass then activate it, as VELDO-0161 has it.

## Round 8: the round 7 review (REVIEW-claude-r7-2026-10-23.md)

The review found two paths to a visibility he never picked (R7-1, R7-2), a configuration that leaves every
new-project decision presented to no one (R7-3), a judge check with no row (R7-4) and AC1's text stating an absolute
its own-message path does not keep (R7-5). Entries 28 and 29 are changed by this section; their text above is kept as
it was reviewed. R7-4 changes no code: proposal/choices now settles a request whose recorded choices are not
`choices(proposal)` (only `accept` and `reject`), and the judge refuses it `no_settled_decision:choices`; mutation
newproject143-judge-choices-unchecked.

**31. Unasked, a repository is only ever private (changes entry 29; R7-1, R7-5).**
- `nothing_asked` no longer compares the visibility with the identity's default. It presents whenever the
  proposal's visibility is not private (`visibility_not_private`), whatever the identity's `default_visibility` or
  the PM's document says, and whenever his message holds a word of visibility (`visibility_in_message`:
  private, public, visible, hidden, secret, open, closed, internal and their forms, `says_visibility`), since no
  text is read for the visibility. A public repository therefore always comes from a choice he picks: for an
  identity whose default is public, the presented proposal shows public and offers `accept <identity> private`.
- AC1's sentence now says it: on a presented proposal only the choice he picks binds the identity and the
  visibility; his own message settles unasked only as the nothing-asked rule allows, at private.
- Row proposal/own-message-doubt: a fixture identity (outward) whose default is public, its message saying nothing
  of the visibility, saying "keep it private" and saying "hidden please", and a message under a private identity
  saying "make it public"; each is presented with the reason named, and the first offers private as a pick.
  Mutations newproject143-own-message-visibility (re-targeted to the new reason) and
  -own-message-visibility-word.
- Cost: an own message under an identity whose default is public, or with any word of visibility in it, costs him
  one choice. A word joined to another still counts, so a project named "open-data" is presented too.

**32. An adoption keeps its remote as it is on GitHub, and is offered no visibility (changes entry 28; R7-2).**
- Nothing on the adoption path (VELDO-0161) applies a visibility, and the remote's visibility is not known when the
  entry is laid: `prepare` reads the origin and checks its owner, never GitHub's visibility of it. So an adopt entry
  records `as_on_remote` (`AS_ON_REMOTE`), the brief says "visibility as it is on GitHub", and its choice names the
  identity alone, `accept <identity>` (the pick kind already allows one value; when it is the identity shown,
  `accept` approves it and no pick is offered). `resolve` refuses a visibility for an adoption
  (`invalid_input:visibility`), and `proposal_problems` refuses a resolved adoption whose visibility is anything but
  `as_on_remote` and a creation whose visibility is not private or public, so the one judge refuses a decision
  recording a visibility for an adoption (`no_settled_decision:proposal`) and nothing creates a repository from
  `as_on_remote` (`offered_entry` refuses it too).
- A correction cannot rename a shown adoption: the new name would be a creation whose visibility he never picked,
  so it fails `invalid_input:correction:mode`, and his report now says what a refused mode means and to ask again
  with the name he wants (the PICKED_NEXT advice no longer follows a refused mode).
- Because an adoption is not private as far as anyone here knows, his own message naming a directory to adopt is
  presented (entry 31). Row provision/adoption-path answers it; row proposal/adoption-visibility (quay: the adopted
  entry, its choice, the brief, the two typed visibility picks refused `unmatched_choice`, the pick adopting it as
  it is, `resolve` and the judge refusing a recorded visibility; slipway: the renamed adoption failed by name, GitHub
  not asked). Mutations newproject143-adoption-visibility-offered, -adoption-visibility-recorded,
  -adoption-visibility-shown and -adoption-renamed-created.
- Not done: reading the remote's visibility from GitHub when the entry is laid, so the brief could name it. That is
  a GitHub call before he is asked, with the identity's token, which this decision does not need: the adoption keeps
  whatever the remote is, and the brief says so.

**33. Ids that fold alike are not a configuration; a request that cannot be presented fails by name (R7-3).**
- `control_git_identity.validate` refuses ids that differ only under the presentation module's fold (case, `-`
  and `_`: work and Work, my-org and my_org), `invalid_input:ambiguous_git_identity`; `configure_identities`
  refuses the same for an id added later beside a configured one. The fold is the presentation module's own
  (`presentation_fold` loads `control_channel_presentation._fold`), so the two cannot drift. Row
  proposal/identities-fold-alike; mutations newproject143-identities-fold-alike and -identity-added-folding.
- For a configuration stored before this check, `NewProjects._present` now reads the presenter's outcome. A refusal
  no retry changes (`NOT_PRESENTABLE`: ambiguous_choice, unmapped_choice, presentation_too_long) cancels the request
  he could never answer and fails the decision `invalid_input:<refusal>` (a `presenting` decision may now go to
  `failed`), from `propose` and from `resume`; his report says the question could not be asked and that each Git
  identity needs an id that differs by more than case, `-` or `_`. Other refusals (a transient channel failure) are
  left as before, for the presenter's own retry. Row proposal/not-presentable (a legacy `Bcengi` beside bcengi,
  written as it was stored); mutation newproject143-not-presented-left-presented.

**34. An adoption's pick ends in adopt, so no pick folds like another identity's (changes entry 32; R8-1).**
- A typed pick is matched by the presentation module's fold, which makes `-` and `_` spaces. Round 8's adoption
  pick `accept <identity>` therefore folded like the creation pick `accept <id> <visibility>` of an id it extends
  (`accept bcengi-private` and `accept bcengi private`), so "accept bcengi private" could adopt under bcengi-private,
  and with no identity shown the two folded alike and the request could not be presented.
- Chosen: the shape, not a refusal. An adoption's pick is `accept <identity> adopt` (`ADOPT_WORD`). The fold keeps
  words and their order, so the last word of a folded pick is the last word of the pick: a visibility for a
  creation, adopt for an adoption. Two picks of different shapes never fold alike, and two of the same shape fold
  alike only when their ids do, which `validate` and `configure_identities` already refuse (entry 33). So no check
  is needed in `choices`, and bcengi beside bcengi-private stays a configuration: refusing an id because it ends in
  a visibility word would refuse a configuration that is not ambiguous once the shapes differ. A check in `choices`
  could never fire, so no row could guard it.
- The brief says the adopted directory's choice names "the identity and adopt". Row proposal/adoption-pick-folds
  (bcengi creating shoal, bcengi-private adopting it: "accept bcengi private", "accept bcengi-private" and
  "accept bcengi_private" refused `unmatched_choice`, `accept` creating it under bcengi, private; with no identity
  shown the request is presented); proposal/adoption-visibility answers `accept personal adopt` and refuses
  `accept personal`. Mutation newproject143-adoption-pick-folds restores the two-word pick.

**35. The decision fails before its unpresentable request is canceled (changes entry 33; R8-2).**
- `_present` writes the decision `failed` (`invalid_input:<refusal>`) and only then cancels the request, so a crash
  between them leaves a failed decision, never a presenting one over a canceled request that `resume` would write
  presented to no one. `propose` and `resume` only observe the failure.
- A crash after the failure and before the cancel leaves the request open but never presented. `resume` cancels the
  request of a decision failed as not presentable whose request is still pending, with the same signed command.
- Row proposal/presentation-interrupted: a legacy `Bcengi` beside bcengi, the service killed just after the cancel
  (tombolo: failed and canceled before and after the next pass) and just before it (groyne: failed, its request
  open, then canceled by the next pass). Mutations newproject143-not-presented-canceled-first (cancel, then fail)
  and -unpresented-left-open.

**36. His own message settles unasked only when the rule has read every word of it (changes entry 31; R8-3).**
- No list of visibility words is complete ("share it with everyone", "publish it", "make it opensource"). So
  `nothing_asked` also presents when a word of his message, apart from the project's name and the identity's id or
  label, is not in `PLAIN_WORDS` (words that ask for a project and say nothing of what it should be: start, new,
  project, called, named, a, under, repo, repository and the like), `words_not_read`. It fails closed: a message with
  any other word costs him one choice. The comment at `_VISIBILITY_WORD` now says the visibility words are read as
  whole words and that the allowlist, not that list, is what decides.
- Row proposal/own-message-doubt with "share it with everyone", "publish it", "make it opensource", "publically"
  and "everyone can see"; mutation newproject143-own-message-unread-words.
