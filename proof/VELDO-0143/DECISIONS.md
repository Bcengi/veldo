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
