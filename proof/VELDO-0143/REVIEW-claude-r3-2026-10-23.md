VERDICT: HAS DEFECTS (R3-1 high, R3-2 medium)

# VELDO-0143 round 3: fix review (Claude, 2026-10-23)

Fresh context, independent of the builder. Worktree at 2ac953ea. Range reviewed: a07ad991..2ac953ea, rebase-adjusted
(124b84ef..2ac953ea: round 2 and round 3), plus the rebase itself (8f749423..06658f1e against 928918a5..bf6c44ac).
Read: the specification, VELDO-0188 AC1, the first review, round3/README.md, round3/REBASE.md, DECISIONS 17 to 22,
every engine change in the range (control_project_proposal, control_service_projects, control_service,
init_scaffold), the round-3 rows of suite 110 and the thirteen round-3 mutations.

## Findings

### R3-1 (high): the line the pass adds for a new project corrupts the factory's own line from the next loop pass on

- Where: engine/.veldo/control_service_projects.py:331 (the pass gives the loop the new repository's line),
  engine/.veldo/control_service.py:2412 (a restarted service adds the same line in FactoryLoop's constructor),
  engine/.veldo/control_service.py:2001 (Line.run builds a line's cycles with from_line, and tries again on every
  pass while that keeps raising), engine/.veldo/control_workflow_cycle_pm.py:611 to 617 (from_line constructs Backlog
  and Teams before control_alias.attach).
- Mechanism: the Backlog and Teams constructors overwrite `conn.command_registry['backlog_operation']` and
  `['team_operation']` on the service's one connection with transitions bound to the instance being built. Only
  after that does `control_alias.attach` raise `invalid_registration`, because the factory line holds the
  allocation authority. The fault is caught per line in FactoryLoop.run, `pm_cycles` is never set, so every
  later pass builds the new line's Backlog and Teams again before failing again. From then on the factory line's
  cached cycles send backlog commands through `store.execute`, which takes the transition from the registry
  (control_store.py:564). That transition is the new line's `Backlog._in_transaction`, carrying the new
  repository's `ids` and workspace. Demonstrated here with a scratch script (two Backlog instances on one
  connection; the registered transition's owner is the second, `new-repo /w/new`).
- Scenario: the factory serves its main repository R (the first configured line). The owner asks for project
  `fjord`, approves, and the pass activates it and adds its line. At the next loop pass the new line's from_line
  re-registers its Backlog and fails. At the pass after that, the factory PM's backlog `take` of a RAW feature of
  R is judged against the new repository's id (control_backlog.py:538) and refused `no_such_feature`. Any other
  backlog operation reads specifications from the new repository's workspace and writes the new repository's id.
  So the owner's first new project breaks backlog work in the repository the factory was already running. After
  a restart it can be worse. FactoryLoop.run visits lines in sorted repository-uuid order (control_service.py:2523).
  If the new repository's uuid sorts first, the new line takes the allocation authority and the factory line's
  from_line is the one that fails on every pass: the factory project's cycles (intake routing, new-project
  proposals, corrections) stop altogether. With random uuids this happens about half the time.
- This is not the red activation/first-unit row. That row only shows that the new line does not run. Here the
  line that already worked is damaged. No row runs the factory line after an activation with the loop attached.
- Fix: until VELDO-0188 makes several lines run on one connection, do not leave a line in the loop whose cycles
  cannot be built. One option is to keep the add_line call out of the pass and the constructor. Another is to
  mark added lines so that Line.run builds no cycles for them. At the least, make from_line failure-atomic: attach
  the per-connection owners (control_alias, control_readset) first, construct Backlog, Teams and Intake only after
  that succeeds, and do not retry a refused build on every pass. Add a row: activate a project with the factory
  loop attached, run two loop passes, then require the factory line's backlog `take` on its own repository to be
  accepted and the registry's `backlog_operation` transition to be the factory line's. Also add a restart row
  where the new repository's uuid sorts before the factory's, and require that the factory project's cycles still
  run. Register a mutation that restores the current order in from_line.

### R3-2 (medium): a negated word counts as the owner's consent, so the F2 guard accepts exactly what he refused

- Where: engine/.veldo/control_project_proposal.py:247 (identity) and :251 (visibility), correction_problems, used
  by correct() and by the judge `settled()`.
- A changed identity is accepted when it is the one configured identity his words name. A changed visibility is
  accepted when his words contain the word anywhere. `names` is a whole-word match with no regard to negation.
- Scenario (run here against correction_problems): the proposal offered `bcengi` and `personal`. He returns it with
  "not under bcengi please, and keep it private, not public". A PM document reading `bcengi`, `public` settles with
  no problem, and the judge then authorizes creating a public repository under the Bcengi owner. The honest reading
  (`personal`, `private`) fails `invalid_input:correction:identity`. So the guard that exists for a PM that errs
  passes the error he ruled out by name and refuses the correct reading. This is the threat model's "a remote
  created under the wrong owner", reached through his words. The visibility half also applies when he named a
  single identity in his first message.
- Fix: a changed field counts as said only when his words name exactly one value of that field (one identity, one
  of the two visibilities), and no negator ("not", "no", "don't", "never", "without", "instead of", "rather than")
  stands immediately before that word or the identity's label. Otherwise fail by name, as now. Add rows for the
  negated identity and the negated visibility, and a mutation that drops the negation check. DECISIONS 17 should
  record this limit of a textual binding.

## 1. F1 to F4 and F6

- F1: fixed. NewProjects calls `notify(state)` after each write. NewProjectPass.written sets `projects_due` unless
  the write is the pass's own. The service builds NewProjects once (control_service_projects.py:166), and the PM
  cycles use that same instance through `service.new_projects()` (control_workflow_cycle_pm.py:633), so a settle
  inside a factory loop pass is seen. Serve checks `projects_due` after `service.loop.run()` in the same iteration
  (control_service.py:2693 to 2699). Row service/pm-settled-due clears `projects_due`, applies the PM's document
  through `ProjectCycles.apply` for both his own message and his correction, and then uses only the serve loop's
  due check. Both provisioners start and both projects activate. newproject143-pm-settled-not-due: killed here.
- F2: fixed as the review asked. One residual is R3-2.
  - A bare approval when the identity was asked fails `invalid_input:answer:identity` in apply_settled, and
    nothing reaches the PM. The judge's correction path now requires `return_for_elaboration`.
  - correction_problems binds the name, identity, visibility and mode. It runs in correct() on the document's
    terms before build(), so no adoption scaffold is laid for an adoption he was not shown (the row checks the
    repository's refs are unchanged). It runs again on the built proposal, and again in the one judge.
  - Row proposal/correction-bound covers each field, a correction naming every change (settles), and a settled
    correction forged around correct(). The forged one is refused `no_settled_decision:correction:identity`, and
    the provisioner writes nothing and asks nothing of GitHub.
  - The six F2 mutations (identity, visibility, mode, name, bare yes, judge) are each killed here.
- F3: fixed. name_taken folds case over project entities and live decisions. It runs in propose(), in correct()
  and in build(), which raises `stale_subject:project_exists`, and the decision fails and is reported. activate()
  now finishes the decision `already_exists` in both branches. Rows proposal/name-taken and activation/name-taken;
  newproject143-name-not-one-project and newproject143-taken-left-settled: killed here.
- F4: fixed. The decision is written `presenting`, with the proposal, alias and deadline, before `_present`.
  `_present` now takes the recorded alias and deadline, so a retry sends identical commands. The store replays
  them, and the presenter's `present` is idempotent (it returns `already_presented`, or does not send again after
  an unknown outcome). pending() does not list a `presenting` decision, so nothing is built twice. resume() runs
  at the head of each pass, and the `presenting` write's notify makes that pass due. Row
  proposal/presentation-interrupted; newproject143-presentation-not-resumed: killed here.
- F6: fixed. propose() fails the decision `unavailable_service:provisioner` before anything is presented or
  settled. A settled decision on a service with no configuration is failed instead of waiting. Row
  proposal/no-provisioner; both mutations are killed here.

## 2. F5

- Fixed part: real. NewProjectPass.activate returns `line=result.get('line')`, and the event carries the
  repository the loop added. Row activation/line-from-pass, with the factory loop attached, requires the
  `activated` event to name the line, and requires that line's workspace, Gate repository and roles to be the
  first line's. newproject143-line-not-added: killed here.
- The builder's explanation: the mechanism is right. control_alias.attach refuses a second allocation authority on
  one connection, and Backlog, Teams and Intake re-register silently. This sandbox shows the same refusal
  (`invalid_registration: connection already has an allocation authority`). One claim is wrong. "A factory's first
  line always runs the factory project's cycles, so the line of every new project is the second" holds only
  within one process lifetime. After a restart, lines build their cycles in sorted uuid order, so the new line can
  be first (R3-1). The silent re-registration is also not harmless to the factory line (R3-1).
- Is VELDO-0188 AC1 the item: yes, with one addition. Its suite already requires the second project, created
  through 0143's provisioner, to have its first unit dispatched by the same process, so it cannot pass without
  solving this. 0188 also depends on VELDO-0143, so moving AC3's first-unit observation from 0143 to 0188 removes
  a dependency cycle instead of creating one. However, 0188 AC1's text names only the set of Lines, not the
  per-connection owners. The owner should add a sentence to AC1: each Line's project cycles run with their owners
  (allocation, read set, backlog, team, intake, grooming) routed per repository on the service's one connection,
  with a row showing that a second Line's cycles neither are refused nor take the first Line's commands.
  Otherwise 0188 could be built to the letter of its set-of-Lines clause and meet the same wall. R3-1 is 0143's
  own regardless of where AC3's observation goes.

## 3. Rebase onto 928918a5

- `git range-diff 8f749423..06658f1e 928918a5..bf6c44ac`: ten of twelve commits are `=`. The two `!` commits differ
  only in context lines that 0161 rounds 6 to 9 changed (control_factory_setup.py's step-7 docstring, and the
  neighbouring 0161 mutation in check_teeth_mutations.py). 0143's own lines are unchanged.
- 0161 behavior kept byte-identical: the 928918a5 to HEAD diff is empty for control_effect_executor_adoption.py,
  control_repository_provisioner.py, control_client.py, control_factory_setup_upgrade.py and suite 109. In
  control_factory_setup.py, every removed line in that diff is a line 0143 already changed before the rebase;
  0161's lay_adoption_signer and restart debt are intact. Every `.veldo/` copy of a changed engine file equals the
  engine file.
- Nothing 0161 removed comes back: no `_await`, no journal watermark polling in NewProjectPass, and no timer.
- Nothing polls: the round-3 due sources are the decision write's notify and the existing events. The pass runs
  only when `projects_due` is set. resume() runs only inside a pass.
- Suite 109 at HEAD and at 928918a5, the same harness: 49 passed on both, the same four AF_UNIX rows red, exit 1 on
  both.
- Suites 85 and 86 compare a fresh host with an upgraded one over bin, config, units and host/engines.json, not
  host/provisioner.json. I found no new difference by reading; neither suite runs here.

## 4. Security, in the range

- Creation without the answer: every path still goes through the one judge. The judge now also requires a
  returned proposal for a correction and binds the correction's terms (gap: R3-2). The owner and remote are also
  checked at creation: VELDO-0153's check_remote binds the URL's owner to the identity, the URL's path must equal
  the remote name, and the created repository's owner, name and privacy are read back.
- Credentials: unchanged in the range; no new logging of bodies, tokens or rationale text (observations name ids,
  reasons and states).
- R3-1 is an integrity defect: the factory repository's backlog transitions run with another repository's id and
  workspace.

## 5. What I ran (this sandbox: AF_UNIX refused, no systemd user manager, no full gate)

I read each exit status directly. A partial selftest run exits 2 when nothing failed and 1 when a row failed.
Every run used a `git archive` copy of the commit made by the builder's round2/sandbox_run.py, with output written
outside the tree. The worktree is unchanged afterwards.

- Suite 110 at 2ac953ea, with the graph stage and the recording agent stood in: exit 1. 64 passed; red only
  service/hand-off (AF_UNIX) and activation/first-unit (F5, `invalid_registration`, both lines faulted in that
  row's pass). This matches round3/110-head.json.
- The thirteen round-3 finding-143 mutations, through proof/VELDO-0143/run_falsifiers.py in worker mode, in three
  batches: each driver exited 0, and 13 of 13 were killed. The baseline before and after each batch was red only on
  service/hand-off, pm/new-project-run and activation/first-unit. I did not re-run the eighteen earlier mutations.
- Suite 109 at 2ac953ea and at 928918a5: exit 1 on both, identical (above).
- 72_veldo_0128_reports at 2ac953ea: exit 2, 18 passed, none failed.
- `.veldo/validate.py all`: exit 0.
- Scratch checks outside the tree, with isolated Python: the registry overwrite (R3-1) and correction_problems on
  negated words (R3-2).
- Not run: scripts/verify.sh, the mutation coordinator, service/hand-off, pm/new-project-run under the driver,
  suite 66 authority/installed-assets (newproject143-scaffold-not-laid), the other consumer suites the README
  lists for the host, the restart ordering in R3-1 as a live run (shown by reading Line.run and FactoryLoop.run),
  and the live GitHub qualification. No outside service was contacted.
