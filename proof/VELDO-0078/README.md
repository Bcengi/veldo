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
    `decision_disposition` answer approving exactly that block (`block_target`), shown exactly
    `resume_brief` of it; it records the resumed phase and clears the blockers.
  - `dispose_unit` is the authorized alternative outcome: the owner's settled answer naming the unit at its
    revision, shown exactly `alternative_brief` of it, with the proposal `{'outcome': 'not_required'}`. A
    unit a VELDO-0133 `close` already CANCELED while its item stayed ACTIVE (the close is the decliner's
    answer, not the owner's) is no outcome; the same settled answer from the owner records the
    authorization on it without another transition, and only then can the item be DONE. `complete`
    (ACTIVE to DONE) needs, for every unit of the decomposition, the receipt the one completion reader
    (`control_eligibility.Gate.landing`, over the transaction's connection) finds for its current revision,
    or that authorized alternative; otherwise `missing_outcome:<unit>`. The backlog judges no receipt
    itself. `cancel` is the project owner's.
  - `executable_problems(conn, unit)` asks the executable question over any connection, and
    `outcome_problems(reader, unit)` is the one answer to whether a unit's outcome is accepted, read
    through the Gate.
- **`.veldo/control_backlog_priority.py` (new).** The executable question,
  `executable_record_problems(unit, item)`, in a module that imports nothing: [] only when the item is
  PRIORITIZED or ACTIVE and the unit is neither PLANNED nor terminal. The service re-exports it and
  refuses to load (ImportError, named) when its state classification does not partition the entity
  contract's backlog_item states, or its execution_unit classes (PLANNED, the prioritized non-terminal
  states, the terminal set) do not partition that vocabulary's states, or its terminal sets differ from
  the contract's. It also holds `unit_binding(unit, item)`, what a ticket for one unit binds of its
  backlog item: the item's identity, project, objective, title, scope and work class, its admission,
  completion and cancellation, whether its state is executable (the state itself is judged fresh by
  `priority_current`), the unit's own decomposition entry, the first priority record that names it (the
  one that prioritized it), and any field the module does not classify. Every other field is a sibling's
  entry or bookkeeping: the rest of the decomposition and the later priority records, the history, the
  applied requests, the decomposition revision and digest, the latest priority and the blocks.
- **`.veldo/control_eligibility.py`.** `priority_current` is a predicate of every station, answered by
  that module over the unit and backlog records the decision consumed, so selection (the frontier's
  offers and the VELDO-0132 cycle's assignment step), claim, direct execution, build, review,
  publication and provider requests refuse admitted but unprioritized work by one decision. The Gate
  loads the import-free module, never the service: the service's entity contract loads the engine's
  parser, which the Gate runs only inside its VELDO-0053 snapshot (loading the service turned suite
  60_veldo_0053's `architecture/identity-keyed-by-module` red). `Gate.landing` returns the id of the
  receipt that establishes `revision_landed`, the evidence DONE records. A ticketed decision compares the
  unit's backlog item by the digest of `unit_binding` for that unit, never the whole record: the backlog
  service rewrites the item on a sibling's append, prioritization and disposal, and the approved units
  continue meanwhile (review 2), so `CallHandle.invoke` against the build decision and
  `Dispatcher._land` against the review decision stay current, while a change bearing on the unit is
  `stale_input:backlog`.
- **`.veldo/frontier.py`.** Unchanged against main: the Gate's selection station now asks the question.
- **`.veldo/tasks.py`.** With a Gate (an enrolled repository always has one, through
  `control_eligibility.gate_for`), `claim_task`, `claim_answer`, `claimable` and `task_report` refuse
  work the Gate's claim station refuses, by its first named reason, before the ledger is asked, and
  `concluded` is the unit's accepted outcome through the Gate; the declared product on disk decides
  nothing. An unenrolled tree with no Gate keeps the pre-factory answers.
- **`.veldo/init_scaffold.py`.** Installs `control_backlog.py`. Engine copies are byte-identical.

The claim receiver (`control_claim.py`) is unchanged: it already refuses a unit that is not READY and an
item that is neither PRIORITIZED nor ACTIVE, and its first claim already moves the unit to CLAIMED and
the item to ACTIVE with the claim record in one transaction, which is the activation this criterion asks
for. The admission and prioritized-set block `executable_problems` carried for records this service
writes is removed, not driven: every real writer moves a unit out of PLANNED only by the prioritization
of its item's current revision, so it answered differently only for rows forged into the store, which are
outside the threat model. `request.py` and `claim.py` are unchanged: neither is on the path the running
factory uses (the file ledger is the pre-factory compatibility path, and claim.py hands an authority
client root to the receiver). Backlog items and units carry no ownership declaration, because the claim
transition writes both and `declare_owners` binds each command to one module.

## Rows, falsifiers and red record

Suite `scripts/suites/73_veldo_0078_backlog.py` (about 5.5 s): the real SQLite store with OpenSSH command,
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
admission, its units admitted by record and PLANNED, the Gate's selection refusing it with
`missing_authority:priority` (so the frontier does not offer it), every one of the seven Gate stations
naming that reason, claim and direct execution naming it alone, the VELDO-0132 cycle's real assignment
step (`Cycles._assign`, its role check answered None) refusing it while it assigns prioritized work, and
`tasks.claim_task` refusing it with the ledger never asked. `priority/gate-question`: the question
imports nothing, the Gate's predicate is that module and the service re-exports the same function, the
Gate loads no entity contract and no service, the classification is the entity contract's, a drifted
classification is named, and the service refuses to load over it (a copy of the installed tree with the
unit terminal set changed). `priority/store-inspection` reads every executable unit in the store and requires its item's
accepted admission and priority. `priority/owner-decision` refuses an admission answer, another
project_owner member's answer, an answer to another brief, prepared work and a reused answer.
`lifecycle/foreign-sources` covers the take path (once per feature, policy classes refused, only features).

**AC2.** `activation/first-claim`: the owner's prioritization of the approved decomposition, the first
claim granted, the claim, unit and item agreeing on the owner, a second holder refused and a unit outside
the decomposition absent. `activation/decomposition-growth` (the declared falsifier's row): two appends,
each a new revision; the appended units PLANNED and refused by the receiver, the task claim (the Gate
naming the missing priority) and the frontier; an approved unit claimed meanwhile; the earlier prioritization not covering them and an answer
to an earlier revision refused; the fresh prioritization of the current revision making them READY.
`ticket/sibling-changes` (review 2's blocking finding): a running unit's build and review decisions, then
the real `CallHandle.invoke` against the build decision (a stub provider behind it) and the real
`Dispatcher._land` against the review decision (a stub lander) accepted after a sibling is appended, after
its prioritization and after its authorized disposal, with the item's entries and bookkeeping rewritten
each time, and every field the service writes on the item one the binding classifies.
`ticket/own-changes`: with the item record rewritten by a fixture and then restored, a change to the unit's
own decomposition entry, to the priority record that prioritized it, to the item's scope, or a field the
binding does not classify, refuses both as `stale_input:backlog`, while a change to a sibling's entry alone
leaves both accepted (the additive control) and the restored record is current again.
`priority/gate-question` also names an entity contract with an extra non-terminal unit state.

**AC3.** `blocked/resume-binding`: the recorded phase and reason, the Gate and the claim blocked, resume
refused with no answer, an answer about another subject, an answer bound to another block, an answer to
this block shown another brief and the owner's refusal; the owner's settled resolution resuming exactly
that phase and clearing the blockers.
`done/missing-outcome` (the declared falsifier's row) drives the declared set: path-only output (the
declared outputs exist and are reported; the task with its product on disk is not concluded), a canceled
attempt, a missing required receipt, an incomplete landing receipt and one for another revision, with the
completion reader agreeing. `done/authorized-alternative` (an answer shown another brief refused too) and
`done/accepted-outcomes` show that only complete receipts or the owner's authorized alternative make it
DONE. `done/one-completion-reader`: DONE records exactly the receipt `Gate.landing` finds, a reader that
finds no landing makes a landed unit a missing outcome and one that finds a landing makes an unlanded unit
accepted, and the backlog's source names no completion contract and no receipt predicate.
`done/closed-unit` (the review's proof gap) drives a real VELDO-0133 close: a worker enrolled for the
project claims a unit and opens a stop, the named owner declines, the decliner answers the disposition
`close` and the inbox disposes it, so the unit is CANCELED with that close on the decliner's answer while
its item stays ACTIVE; DONE refuses it as `missing_outcome:<unit>` and the backlog names it; the owner's
settled `decision_disposition` answer then counts it (still CANCELED, the close kept) and the item is DONE
with that outcome. `lifecycle/regular-path` checks the
main item's whole history and the reject, return and cancel branches. `other-process` and
`observability` complete the set.

`red-at-8bc4517.json`: the current suite run against `git archive 8bc4517` (the build review 2 judged)
unchanged. Three of 20 rows fail, each by its own assertions (`by_assertion: true`):
priority/gate-question (an extra unit state was not named), ticket/sibling-changes (the subscription call
and the landing refused `stale_input:backlog` after the sibling's append, prioritization and disposal, and
no field classification) and ticket/own-changes (a sibling's entry alone made the tickets stale, and the
restored record was still stale). The other 17 rows cover behavior 8bc4517 already had.
`red-at-8bb474c.json`: the review 1 suite's record against `git archive 8bb474c` (the build review 1
judged). Ten of 18 rows fail, each by its own assertions (`by_assertion: true`): install/assets
(no import-free question), priority/missing-priority (the Gate accepted unprioritized work),
priority/gate-question, activation/decomposition-growth (the Gate's reason), blocked/resume-binding and
done/authorized-alternative (no brief bound), done/accepted-outcomes, done/one-completion-reader (no
`Gate.landing`), done/closed-unit (the owner could not count a closed unit) and other-process. The other
eight rows cover behavior 8bb474c already had. `red-at-467d168.json` is the first build's record against
the tree before the backlog service, with that build's suite.

`mutations.json` (from `python3 -B proof/VELDO-0078/drive.py`, about 181 s serial): the baseline and a
no-op copy of each of the five mutated modules are green, and each of the 29 finding-78 mutations turns its
named row red by assertion. The applied diffs are beside it. Names are unique across every finding.

| Mutation | Module | Named row |
|---|---|---|
| task-claim-skips-priority (AC1 declared) | tasks.py | priority/missing-priority |
| frontier-offers-unprioritized (selection skips priority) | control_eligibility.py | priority/missing-priority |
| backlog-priority-only-at-selection | control_eligibility.py | priority/missing-priority |
| backlog-priority-not-a-gate-predicate | control_eligibility.py | priority/missing-priority |
| backlog-gate-loads-the-service | control_eligibility.py | priority/gate-question |
| backlog-classification-unchecked | control_backlog.py | priority/gate-question |
| any-member-decides | control_backlog.py | priority/owner-decision |
| backlog-not-scaffolded | init_scaffold.py | install/assets |
| backlog-question-not-scaffolded | init_scaffold.py | install/assets |
| appended-unit-executable (AC2 declared) | control_backlog.py | activation/decomposition-growth |
| stale-revision-answer-applies | control_backlog.py | activation/decomposition-growth |
| output-file-done (AC3 declared) | tasks.py | done/missing-outcome |
| resume-without-resolution | control_backlog.py | blocked/resume-binding |
| blocked-item-executable | control_backlog_priority.py | blocked/resume-binding |
| backlog-done-on-output | control_backlog.py | done/missing-outcome |
| incomplete-landing-accepted | control_eligibility.py | done/missing-outcome |
| backlog-done-own-landing-reader | control_backlog.py | done/one-completion-reader |
| backlog-closed-unit-accepted (any CANCELED unit an outcome) | control_backlog.py | done/closed-unit |
| backlog-closed-unit-not-counted | control_backlog.py | done/closed-unit |
| backlog-resume-brief-unbound | control_backlog.py | blocked/resume-binding |
| backlog-alternative-brief-unbound | control_backlog.py | done/authorized-alternative |
| backlog-ticket-whole-record (the ticket binds the record minus its state again) | control_eligibility.py | ticket/sibling-changes |
| backlog-ticket-binds-sibling-entries | control_backlog_priority.py | ticket/sibling-changes |
| backlog-ticket-binds-sibling-priorities | control_backlog_priority.py | ticket/sibling-changes |
| backlog-ticket-own-entry-unbound | control_backlog_priority.py | ticket/own-changes |
| backlog-ticket-own-priority-unbound | control_backlog_priority.py | ticket/own-changes |
| backlog-ticket-scope-unbound | control_backlog_priority.py | ticket/own-changes |
| backlog-ticket-unclassified-unbound | control_backlog_priority.py | ticket/own-changes |
| backlog-unit-drift-open (only the terminal set and PLANNED checked) | control_backlog.py | priority/gate-question |

`python3 scripts/check_teeth_mutations.py --finding 78` rejects all 29. The findings of the changed
modules still reject in full: 52 (49), 53 (52), 54 (59), 57 (33), 76 (23), 77 (24), 132 (28), 133 (21)
and 135 (16). Every suite that loads `control_eligibility.py` or `control_backlog.py` passes, with
20_veldo_0003_task_source, 58_veldo_0031_claims, 69_veldo_0133, 72_veldo_0077, 53_veldo_0123 and
50_git_environment.

## Stated limits

Recovery and restart are Release 2. A returned item is groomed again with its recorded decomposition;
reshaping it, exhaustive state-pair qualification and advanced backlog states are Release 3. Trusted
automatic defect admission and standing or emergency policy paths are not executable here. Observations
carry identities, versions, outcomes and named refusals, never reasons, rationales or signatures.
