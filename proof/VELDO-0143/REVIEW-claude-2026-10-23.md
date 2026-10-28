VERDICT: HAS DEFECTS (F1 high, F2 high, F3 medium, F4 medium, F5 medium, F6 low)

# VELDO-0143 independent review (Claude, 2026-10-23)

Range 8f749423..a07ad991 at a07ad991, first review, fresh context. Read: the specification, VELDO-0161, 0153,
0128 and 0154 where 0143 relies on them, proof/VELDO-0143 (README, REBASE.md, DECISIONS.md, falsifiers), every
changed engine module (control_project_proposal, control_effect_executor_creation, control_repository_creation,
control_service_projects, the control_service, control_repository, control_project, control_objective,
control_grooming_request, control_backlog and control_workflow_cycle_pm diffs) and suite 110. 0161 was not
re-reviewed: control_effect_executor_adoption.py, control_repository_provisioner.py, control_client.py and suite 109
are byte-identical to 8f749423 (empty diff), and every `.veldo/` copy equals its engine file.

## Findings

### F1 (high): a decision settled by the factory PM's run never makes the new-project pass due, so the nothing-asked path and every correction stall

- Where: engine/.veldo/control_service.py:1464 (hint_after, the only journal-driven setter of `projects_due`),
  engine/.veldo/control_service.py:2692 (`service.loop.run()` in the serve loop), engine/.veldo/control_workflow_cycle_pm.py
  ProjectCycles.apply (the new-project branch calling NewProjects.propose and NewProjects.correct).
- `projects_due` is set in exactly three places: the instance's start, hint_after (after a packet or a channel pass
  advanced the journal), and the end of a provisioner pipe. The factory PM's result is applied inside a factory loop
  pass: the run's end is seen on its launch pipe (`run_end`), Line.run settles the dispatch through Runner.wait, then
  ProjectCycles.pass_once calls finish, then apply, then `propose()` (which writes the decision `settled` on the
  own_message path) or `correct()` (which writes it `settled` on the correction path). None of that goes through
  hint_after, and FactoryLoop.run never sets `projects_due`.
- Scenario: the owner writes "start a new personal project called tidepool" from his chat, naming identity
  `personal` (the specification's own normal case, AC1's nothing-asked path). The factory PM run ends, the loop pass
  on `run_end` writes `new-project:<id>` `settled`, `projects_due` stays False, and the serve loop never calls
  new_project_pass. No provisioner starts and no report is sent. The decision sits `settled` until some unrelated
  packet or Telegram update advances the journal, or the service restarts. The same happens for every correction:
  the pass writes `correcting` and wakes the loop, the PM's corrected document is applied in a loop pass, and nothing
  makes the pass due again. Only the "answer" path works, because there the owner's answer arrives through a channel
  pass (hint_after). The owner's rule (never poll) is kept, but the event that matters is not wired.
- Why the suite is green: every `service/*` and `provision/*` row settles its decision by calling
  `decisions.propose` directly (`own_decision`) and then calls `new_project_pass()` itself; `pm/new-project-run` builds
  its own loop and stops at `presented`. No row runs a PM-settled decision through the serve loop's due logic.
- Fix: make the new-project pass due when a factory loop pass advanced the journal (in serve: read the watermark
  before `service.loop.run()` and set `projects_due` when it moved; or have NewProjects.write notify the service).
  Add a row that settles a decision through the loop's PM apply (own_message and correction) and, with no further
  event, observes the provisioner started; register a mutation that drops the new setter.

### F2 (high): a correction lets the factory PM choose the identity, flip the visibility or switch to adoption, unchecked, so a repository can be created or pushed under terms the owner never said or saw

- Where: engine/.veldo/control_project_proposal.py:525-533 (settled(), correction branch), :740-760 (correct()),
  :726-735 (apply_settled: an approval that names no offered identity becomes a correction).
- The correction branch of the one judge checks only that the corrected document is well formed, that the rationale
  is his, and that the repository uuid and source are unchanged. Nothing binds the corrected identity, visibility or
  mode to his words. correct() fails the decision only when the PM's document names no identity at all. So the
  safety rests entirely on the PM obeying its instruction ("identity ... only when he named it, else null").
- Scenarios: (a) the proposal offers `bcengi` and `personal` because he named no identity; he answers "yes". That is
  routed to correction (DECISIONS 2), the PM returns `identity: bcengi`, the judge accepts it, and a repository is
  created under the Bcengi organization that he never named, which is exactly what DECISIONS 2 says it avoids ("picks
  something he did not say"). (b) He answers a proposal for `personal` with "call it reef-watch"; the PM returns
  `identity: bcengi, visibility: public`; the judge accepts, and a public repository is created under another owner.
  (c) The corrected name is a directory that is already a Git repository: build() turns it into `mode: adopt`, lays a
  scaffold commit and the decision settles without the brief ever showing it, so his existing remote receives a
  pushed scaffold commit on terms he never saw (the very outcome DECISIONS 8 refuses at provisioning time). DECISIONS 3
  already states the principle for the first message: "the PM's reading alone is not enough". The correction path
  does not apply it, and this is the threat model's "a remote created under the wrong owner".
- Fix: in correct() and in the judge's correction branch, refuse by name (`invalid_input:correction:<field>`, decision
  failed and reported) unless (1) the corrected identity is the presented one or is named in his rationale as a whole
  word (identity_named over the configured identities), (2) a visibility other than the presented one is said in his
  rationale, and (3) the mode equals the presented mode for the chosen identity (a correction that would turn into an
  adoption is presented, or fails by name). Add rows for each and mutations that drop each check.

### F3 (medium): a new project named like an existing one is created on GitHub and then never activated, failed or reported

- Where: engine/.veldo/control_project_proposal.py:157 (document_problems refuses only `factory`), :850-856
  (activate returns `already_exists` without finishing the decision), engine/.veldo/control_service_projects.py:212-213.
- Scenario: project `tidepool` exists (or two new-project messages name the same project under two identities). The
  owner asks for `tidepool` again under `bcengi`; the proposal is built (the directory under bcengi's root is absent),
  he approves, the provisioner creates and pushes `bcengi/tidepool`, the service takes it on, and every following
  pass returns `{step: activation, reason: already_exists}`. The decision stays `settled` forever, no project_ready
  report is sent, and the created repository is orphaned. The error taxonomy's promise that every failure names its
  reason to the owner is broken here.
- Fix: refuse at build() a name that is already a project or the name of another live new-project decision
  (`stale_subject:project_exists`, before he is asked and before anything is created), and have activate() finish the
  decision `failed` with `already_exists` instead of returning it to be retried. Add a row and a mutation.

### F4 (medium): a crash or store refusal between presenting the proposal and recording the decision strands the owner's question and the message for good

- Where: engine/.veldo/control_project_proposal.py:662-665 (propose(): `_present` first, then `write(... 'presented')`).
- Scenario: `_present` records the terms, opens the inbox request and sends the presentation to Telegram; the service
  is killed (or `write` raises StoreRefused) before the decision is written. pending() still lists the NEW_PROJECT
  message with no decision, the next PM run calls propose() again with a fresh `uuid4()` repository, so the terms
  command carries the same deterministic command_id (`new-project-<hash>-terms`) with different content. The store
  answers `command_content_conflict`, propose() refuses `unavailable_service:terms` on every later run, and the
  message never gets a decision. Meanwhile the owner holds a presented question whose answer apply_settled never
  reads (it only looks at decision records). He is told nothing. Verified by reading control_store.execute's
  command_id rule; not reproduced.
- Fix: write the decision first (a `presenting` state carrying the proposal and the alias), then present, then move
  it to `presented`; on a retry, finish the presentation the record names instead of building a new proposal.

### F5 (medium): AC3's "the first unit dispatched in the new repository with the identity as author" has no row, here or on the host

- Where: scripts/suites/110_veldo_0143_new_project.py:1001 (`activation/new-line`).
- The row proves the line (receiver configuration, workspace, Gate, base revision, copied configurations) and that
  GI.author resolves the identity; it never dispatches a unit. `pm/new-project-run`, the only host row that needs the
  graph runtime, covers the factory PM's proposal, not the new project's first cycle or unit. The README's host run 2
  is suite 110, which contains no such row; host run 6 (the live qualification) is "not run anywhere". So this
  observation of AC3 is met only on paper. Also, `activation/applied` runs with `service.loop` None, so the
  `add_line` call in NewProjectPass.activate is not executed by any row.
- Fix: a host row (graph runtime available) that, after activation, runs the new project's PM cycle on the added line
  and observes one dispatch whose workspace is the new repository and whose commit author is the identity; at the
  least, a row that activates with a FactoryLoop attached and observes `add_line` from the pass.

### F6 (low): an installation without a provisioner configuration presents and settles proposals it can never carry out, and the owner is never told

- Where: engine/.veldo/control_service_projects.py:261-266.
- Scenario: a factory set up before this change (DECISIONS 5). The owner asks for a project, is asked, answers; the
  pass logs `unavailable_service:provisioner` once and the decision waits `settled` with no report. The reason is
  named only in the log.
- Fix: refuse at propose() when no provisioner configuration is installed (the owner is told why, nothing is asked),
  or report the waiting decision through VELDO-0128.

## 1. Acceptance criteria

- AC1: built as specified (factory project on its own repository, routing, one proposal with every named field,
  nothing-asked rule judged textually, one presentation, correction without a second question). Rows green here;
  declared falsifier `newproject143-presented-when-named` kills `proposal/nothing-asked` (reproduced). Met, except
  that the nothing-asked path does not reach provisioning in the running service (F1) and a correction is not bound
  to his words (F2).
- AC2: built as specified: settlement judged before anything, steps in order, each recorded, first failure named and
  later steps skipped, REST creation with the standard library and the identity token, push through the identity
  profile. `provision/step-failures` fails each step; `newproject143-provisioner-unsettled` kills
  `provision/settlement-required` (reproduced). Met in the provisioner; reachability in the service is F1.
- AC3: activation refused until the repository is active, also inside the transaction; first team, objective
  accepted by the decision, admitted at default priority, owner told by report. `newproject143-activated-while-provisioning`
  kills `activation/order` (reproduced). The first-unit dispatch is on paper only (F5); a name collision never
  activates or reports (F3).

## 2. DECISIONS.md

1. Correction settles with no second presentation: right reading of "a yes or a correction ... no further
   question", but only if the correction is bound to his words. As built it is not (F2). High attention.
2. Every identity offered in one request: right. Routing an unqualified "yes" to the PM as a correction is wrong:
   the identity must come from his words; the specification requires it to be "asked", so an answer that names none
   should fail by name or (better) the PM document must be refused unless his rationale names one (F2). High attention.
3. Nothing-asked needs the owner's own message plus a textual match of project and identity: right.
4. Factory repository is no line: right; a line for a repository with no code is not required.
5. Old factories keep their factory project: right (no authority to rebind a live project), but see F6.
6. Registered protected effect started only by the service: right, and stronger than a worker-requestable handle.
7. Injected author and commit failures: acceptable; the other seven are real conditions.
8. Empty directory used, link and non-directory refused, repository-ness judged at proposal time: right.
9. Visibility from the identity's `default_visibility`, else private: right; the operating-model design puts the
   default visibility in the identity record the owner configures.
10. New acceptance path `new_project`: right; VELDO-0077 cannot accept an objective that does not exist yet.
11. Owner told by a VELDO-0128 `project_ready` report through the one rendered send: right.
12. Line roles from the loop's first line: acceptable; the proof of the dispatch is missing (F5).
13. Store and host checks before the directory step: right, and required by 0161's "checks that change nothing".
14. Repository configuration judged before the remote is created: right.
15. INTERRUPTED and the lock applied to created records, one re-run per instance: right.
16. Pass driven by events: the design is right and is not a poll, but one event source is missing (F1).

## 3. Rebase onto VELDO-0161 round 5

Kept: the adoption effect, the provisioner module, the client and suite 109 are byte-identical to 8f749423; the
creation path ends in 0161's `take_on` over the socket, answered synchronously, with no wait and no record polling;
the allowlist (`refuse_commands`) and the identity transport's judge (`refuse_transport_config`) run before GitHub is
asked; the push names one explicit refspec (`<commit>:refs/heads/main`), no tag option, under the identity profile.
Nothing 0161 removed comes back: no `_await`, no journal watermark in NewProjectPass, no per-iteration pass. The
d859b3db pass is event driven (start, hint_after, provisioner pipe end in the existing select); it is not on a timer.
Its event set is incomplete (F1). The known limit (a provisioner of an earlier instance that fails later wakes no
one) is documented and acceptable as stated.

## 4. Security

- Creation without the answer: every path into the provisioner and the adoption signer goes through the one judge
  (control_project_proposal.settled), read from the request, terms, settlement, effect and brief, never from the
  record's state; the activation and objective acceptance call it again. A settled answer must be the factory
  owner's alone (`principals == [owner]`, active person holding project_owner). Replay: each decision has its own
  request alias and its record refuses a second propose; the lock and `already_provisioned` stop a second run.
  Nothing reaches GitHub before settlement (the only pre-answer write is 0161's local scaffold ref in an existing
  repository). The gap is F2: the answer is not bound to the identity, visibility and mode that are executed.
- Credentials: the token lives only in GitHub._token for the call; `calls` records method, path and status; refusals
  carry codes, never bodies or headers; no proxy, no redirects; the REST origin is GitHub's or loopback only;
  the configuration is refused unless it is this account's own regular 0600 file. No leak found.

## 5. Crash windows, races, taxonomy

Interrupted creation is failed `unknown_outcome:interrupted` at its last step under the lock; a live run refuses
touching nothing; a remote created just before a crash stays for the owner, per the rollback field. Taxonomy covers
every class the specification lists (directory_not_empty, remote_exists, remote_owner_mismatch, token_unavailable,
creation_refused, push_refused, no_settled_decision, signature_refused). Defects: F3 (unnamed endless retry), F4
(present before record).

## 6. What I ran (this sandbox: AF_UNIX refused, no systemd user manager, no graph runtime)

Exit statuses read directly. A partial selftest run never exits 0 by design (2 when nothing failed, 1 when a row
failed).

- Suite 110: exit 1; 47 rows passed, red only `service/hand-off` (AF_UNIX) and `pm/new-project-run` (runtime).
- Finding 143 through proof/VELDO-0143/run_falsifiers.py: exit 0; 16 of 16 killed, baseline before and after red only
  on the same two rows.
- Suite 109: exit 1; 49 passed, red only the four AF_UNIX rows the bundle names.
- Exit 2, no failed row: 72_veldo_0077_objectives (20), 72_veldo_0128_reports (18), 73_veldo_0078_backlog (20),
  73_veldo_0089_team (26), 75_veldo_0150_own_message_acceptance (13), 76_veldo_0079_grooming (22),
  77_veldo_0149_adopted_activation (13), 68_veldo_0126_intake (18), 69_veldo_0068_settlement (8),
  86_veldo_0168_text (26), 46_veldo_0029_enrollment (7).
- `.veldo/validate.py all`: exit 0. Engine to `.veldo/` copies: identical.
- Not run (need AF_UNIX, the user manager or the graph runtime): the full gate scripts/verify.sh, the mutation
  coordinator, `service/hand-off`, `pm/new-project-run`, the 0161 AF_UNIX rows, and suites 66_veldo_0047_authority,
  83, 71_veldo_0076, 71_veldo_0130, 73_veldo_0139, 106, 85, 91_veldo_0167, 86_veldo_0189, 92, 93, 94, 96; the live
  GitHub qualification was not attempted (no outside service contacted).
