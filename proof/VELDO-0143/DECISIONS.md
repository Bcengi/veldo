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
- Limits that remain, each measured on the round-5 module (`round5/phrasings.py`), not solved by more rules:
  - A negator after the word other than "? no" is not seen: "public, no", "public - no", "public: no way" and
    "public is wrong" keep a shown public.
  - Negators outside the list are not known: "none of it public", "skip public", "nope, public is wrong" keep a
    shown public. Nor are another language's ("nicht").
  - A negator whose clause ends at punctuation before the other value: "don't use bcengi, and personal" settles
    personal (the comma, not a bare "and", joins them).
  - "Not only private but public" reads public as said, so it settles a change to public.
  - Double negation and irony read wrong.
  - A negator early in a clause with no punctuation refuses what he did say ("no rush make it public").
  - The fail-closed reading of a shown value refuses where its word is only part of another word that a negator
    precedes; an identity whose id or label is a short common word would be refused more often than he means.
  - A negated project name ("not called fjord") is not judged by this rule; the name rule is entry 17's.
- The phrasings suite 110 refuses and settles are its rows proposal/correction-negated and
  proposal/correction-phrasings; the limits above are measured, not rows, and some of them pass a value he
  negated. Where the binding refuses, the decision fails by name (`invalid_input:correction:<field>`), he is told,
  and he can ask again. What reaches creation is still judged
  by the one judge, `settled()`, and checked against the identity's owner at creation (VELDO-0153). The binding
  stops a PM from choosing for him. It is not a parser of his intent.

**25. Round 5: what the round 4 review's fixes chose (R4-1 to R4-6).**
- R4-1, the kept value fails closed. A value he was shown is negated when any occurrence of its word, matched
  from a word's start with nothing required after it, has a negator before it in its clause, or "? no" after it.
  The word edge is fixed too, for the values he changes and for names: a '.' or '-' continues a word only when a
  letter, digit or underscore follows it, so "public." and "bcengi." are named, and "shoal-two" and "fjord.io"
  stay one word. The two are separate mutations, each killed by its own rows: the edge by "Use personal." and
  "Keep it private." (a changed value at a sentence end settles), the fail-closed reading by "don't host it
  publicly" and "nothing bcengi-owned".
- R4-2, the review's three options, all taken: "neither" is a negator; an "and" whose next word is another value
  of the field does not end the clause; and a value affirmed in a clause that began at a bare "and", after a
  clause that negates another value of the field, makes the field ambiguous, refused by that name. Only the
  negated-then-affirmed order is ambiguous: "use personal and not bcengi" negates in its own clause and settles.
  "or" and "nor" end no clause at all, so "not bcengi or personal" negates both.
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
  the factory line has none and the store has a factory project, whatever its state. "Whenever the factory line
  exists" alone would also hold back every line of a loop with no factory project at all (a factory set up
  before VELDO-0143, or the consumer suites' loops), whose first line is the factory line by definition and never
  wants cycles. With no factory project there is nothing to keep the owners for.
- R4-6, `service.new_projects()` is built before from_line takes the registrations, under the same conditions
  as before (a channel and a factory project). A failure in that build is the factory line's pass fault, as
  any other, and nothing is cached by a build that raised.
