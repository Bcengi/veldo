# VELDO-0078 proof

Release 1 stage 4: backlog work moves proposed (RAW), prepared, awaiting grooming, admitted, prioritized,
active, optionally blocked, and done or canceled. Only work the project's owner has admitted and
prioritized creates executable engineering units, on the ordinary path and at every direct claim entry.
The first claim activates the item and follows its approved decomposition only; a unit appended later
needs its own fresh prioritization while the approved units continue. A blocked phase resumes only on the
owner's settled resolution of that block, and DONE needs accepted unit outcomes. Specification status,
risk and `.veldo/policy.yaml` are unchanged. This proof is for independent review; it is not a
self-approval, and the canonical gate is run by the lead, not recorded here.

## What was built

- **`.veldo/control_backlog.py` (new).** The backlog service, the one writer of backlog items
  (`backlog:<hex>`, kind `backlog_item`) and of the units their approved decomposition creates. Every
  operation is a signed command verified against the principal's active key, every transition is asked of
  `entity_contract.transition` on the R11 and R13 vocabularies, and each appends one history entry.
  - `take` makes a RAW item from a RAW VELDO-0077 feature of an accepted objective (the feature record is
    never written here; VELDO-0077 owns its prefix). Only the ordinary lane's classes are taken
    (`unsupported_work_class:<class>` otherwise), so trusted automatic defect admission and standing or
    emergency policy paths stay non-executable in this release.
  - `prepare` records the decomposition at revision 1 with its digest, each unit alias checked by the
    existing validator `claim.unit_id_problem`, and creates each unit PLANNED. `request_grooming` moves
    PREPARED to AWAITING_GROOMING.
  - `admit` and `prioritize` apply the owner's VELDO-0068 settlement on the `admission` and `priority`
    touchpoints. The settled effect must target the item at its CURRENT decomposition revision and digest
    (`decision_target`), the request must have shown exactly `admission_brief` or `priority_brief`, and the
    request's owner and the settlement's only principal must be the project's owner, who must be current.
    Otherwise `invalid_input:request`, `stale_subject:binding`, `stale_subject:brief` or `not_owner`, and
    nothing is written; an answer is applied once (`already_applied`). Admission writes an accepted
    `admission:<unit>` record per unit (the record the Gate's `admission_current` reads); priority moves
    exactly the units still PLANNED to READY at `admitted_revision`, and ADMITTED to PRIORITIZED.
  - `append` adds a unit to a PRIORITIZED or ACTIVE item as a new decomposition revision, the unit PLANNED;
    only a fresh prioritization of that revision makes it READY.
  - `block` records the interrupted phase and reason (ACTIVE to BLOCKED) and a `blocker` record per open
    unit, so every Gate station refuses them (`no_blockers`). `resume` needs the owner's settled
    `decision_disposition` answer approving exactly that block (`block_target`); it records the resumed
    phase and clears the blockers.
  - `dispose_unit` is the authorized alternative outcome: the owner's settled answer naming the unit at its
    revision with the proposal `{'outcome': 'not_required'}`. `complete` (ACTIVE to DONE) needs, for every
    unit of the decomposition, a complete VELDO-0057 confirmed-landing receipt of its current revision
    (completion_contract's `revision_landed` fact with a complete landing receipt for that unit, the
    predicates the completion reader applies) or that authorized alternative; otherwise
    `missing_outcome:<unit>`. `cancel` is the project owner's.
  - `executable_problems(conn, unit)` is the one question every claim entry asks, and
    `outcome_problems(conn, unit)` the one answer to whether a unit's outcome is accepted.
- **`.veldo/frontier.py`.** An offer the Gate's selection station accepts is also asked
  `executable_problems` over the Gate's read connection, for build and review offers alike.
- **`.veldo/tasks.py`.** With a Gate (an enrolled repository always has one, through
  `control_eligibility.gate_for`), `claim_task`, `claim_answer`, `claimable` and `task_report` refuse
  work that is not executable by the backlog's named reason before the ledger is asked, and `concluded`
  is the unit's accepted outcome; the declared product on disk decides nothing. An unenrolled tree with no
  Gate keeps the pre-factory answers.
- **`.veldo/init_scaffold.py`.** Installs `control_backlog.py`. Engine copies are byte-identical.

The claim receiver (`control_claim.py`) and the Gate (`control_eligibility.py`) are unchanged: the
receiver already refuses a unit that is not READY and an item that is neither PRIORITIZED nor ACTIVE, and
its first claim already moves the unit to CLAIMED and the item to ACTIVE with the claim record in one
transaction, which is the activation this criterion asks for. The Gate does not read backlog state; the
frontier asks the backlog after the Gate, and the blockers reach every Gate station through its own
`no_blockers` predicate. `request.py` and `claim.py` are unchanged: neither is on the path the running
factory uses (the file ledger is the pre-factory compatibility path, and claim.py hands an authority
client root to the receiver). Backlog items and units carry no ownership declaration, because the claim
transition writes both and `declare_owners` binds each command to one module; rows forged into the store
are outside the threat model.

## Rows, falsifiers and red record

Suite `scripts/suites/73_veldo_0078_backlog.py` (about 3.5 s): the real SQLite store with OpenSSH command,
claim, journal and API signatures; the backlog items taken from RAW features of an objective the owner
accepted through the real VELDO-0077 service; every admission, priority, block resolution and alternative
outcome a real VELDO-0064 request presented by the VELDO-0065 presenter over a loopback Bot API, answered
through the authenticated API edge and settled by the VELDO-0068 settlement; the real claim entries (the
frontier's offers through the VELDO-0052 Gate over spec files, the VELDO-0031 receiver with signed claim
commands, and `tasks.claim_task` over the file ledger and over claim.py's authority client root, an
in-process client of the same receiver); completion receipts in the VELDO-0057 shape judged by the one
completion reader; and a reader in another process. It also passes in the stage environment (`env -i`,
empty HOME, `GIT_CONFIG_GLOBAL=/dev/null`). Each row is reported once.

**AC1.** `priority/declared-set` drives intake-only, prepared, admitted-without-priority and prioritized
work through the four entries (offer, receiver, task over the ledger, task over the authority) and
requires exactly the expected table: only prioritized work is offered or claimed.
`priority/missing-priority` (the declared falsifier's row) shows the admitted item with its owner's
admission, its units admitted by record and PLANNED, the Gate's selection accepting a unit the frontier
still does not offer, and `tasks.claim_task` refusing `missing_authority:priority` with the ledger never
asked. `priority/store-inspection` reads every executable unit in the store and requires its item's
accepted admission and priority. `priority/owner-decision` refuses an admission answer, another
project_owner member's answer, an answer to another brief, prepared work and a reused answer.
`lifecycle/foreign-sources` covers the take path (once per feature, policy classes refused, only features).

**AC2.** `activation/first-claim`: the owner's prioritization of the approved decomposition, the first
claim granted, the claim, unit and item agreeing on the owner, a second holder refused and a unit outside
the decomposition absent. `activation/decomposition-growth` (the declared falsifier's row): two appends,
each a new revision; the appended units PLANNED and refused by the receiver, the task claim and the
frontier; an approved unit claimed meanwhile; the earlier prioritization not covering them and an answer
to an earlier revision refused; the fresh prioritization of the current revision making them READY.

**AC3.** `blocked/resume-binding`: the recorded phase and reason, the Gate and the claim blocked, resume
refused with no answer, an answer about another subject, an answer bound to another block and the owner's
refusal; the owner's settled resolution resuming exactly that phase and clearing the blockers.
`done/missing-outcome` (the declared falsifier's row) drives the declared set: path-only output (the
declared outputs exist and are reported; the task with its product on disk is not concluded), a canceled
attempt, a missing required receipt, an incomplete landing receipt and one for another revision, with the
completion reader agreeing. `done/authorized-alternative` and `done/accepted-outcomes` show that only
complete receipts or the owner's authorized alternative make it DONE. `lifecycle/regular-path` checks the
main item's whole history and the reject, return and cancel branches. `other-process` and
`observability` complete the set.

`red-at-467d168.json`: the current suite run against `git archive 467d168` unchanged. All 15 rows fail,
each by its own assertions (`by_assertion: true`): that tree has no backlog service, and its frontier and
task source ask no backlog question.

`mutations.json` (from `python3 -B proof/VELDO-0078/drive.py`, about 58 s serial): the baseline and a no-op
copy of each of the four modules are green, and each of the 11 finding-78 mutations turns its named row
red by assertion. The applied diffs are beside it.

| Mutation | Module | Named row |
|---|---|---|
| task-claim-skips-priority (AC1 declared) | tasks.py | priority/missing-priority |
| frontier-offers-unprioritized | frontier.py | priority/missing-priority |
| any-member-decides | control_backlog.py | priority/owner-decision |
| backlog-not-scaffolded | init_scaffold.py | install/assets |
| appended-unit-executable (AC2 declared) | control_backlog.py | activation/decomposition-growth |
| stale-revision-answer-applies | control_backlog.py | activation/decomposition-growth |
| output-file-done (AC3 declared) | tasks.py | done/missing-outcome |
| resume-without-resolution | control_backlog.py | blocked/resume-binding |
| blocked-item-executable | control_backlog.py | blocked/resume-binding |
| backlog-done-on-output | control_backlog.py | done/missing-outcome |
| incomplete-landing-accepted | control_backlog.py | done/missing-outcome |

`python3 scripts/check_teeth_mutations.py --finding 78` rejects all 11. The findings of the changed
modules still reject: 52 (49), 54 (59), 135 (16), 76 (23) and 77 (24) in full, and every other finding's
`init_scaffold.py` mutation (23) turns its named row red. Every suite that loads a changed module passes.

## Stated limits

Recovery and restart are Release 2. A returned item is groomed again with its recorded decomposition;
reshaping it, exhaustive state-pair qualification and advanced backlog states are Release 3. Trusted
automatic defect admission and standing or emergency policy paths are not executable here. Observations
carry identities, versions, outcomes and named refusals, never reasons, rationales or signatures.
