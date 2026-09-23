# VELDO-0054 proof

Decision-record dependency evaluation for the floor slice, Release 1 stage 1 of PLAN-0019 revision 3
(W39). Specification status, policy and every other specification are unchanged. Branch
`build-veldo-0054`, built on main acd877c.

## What landed

**One answer, every consumer.** `.veldo/control_decision_dependency.py` (mirrored byte-identically
in `engine/.veldo/`, laid down by `init_scaffold.py`) answers "does a governing decision still block
this unit?" as a list of named blockers, empty when nothing blocks. The shared Gate's
`decisions_settled` predicate (VELDO-0052) now asks it at selection, direct execution, build, review
and publication, and a new `Gate.decision_blockers(unit, references)` gives the same answer to
`plan._decision_blocks` (and through it `item_state` and the plan burn-down), `plan.cmd_run_check`
the frontier's plan candidates and `veldo status` (`runstatus._burndown`). The consumer set is `CONSUMERS`, checked against the actual call
sites by AST.

**What a governing decision is.** An accepted `decision` record (`veldo.governing_decision/v1`)
carrying `decision_id`, `revision`, `framing_digest`, `subject` (kind `spec` or `plan`, id, digest),
`scope` (operation, target, parameters), `blocks` (unit ids and `plan:<id>`) and `obligations`. The
subject digest has one spelling, `subject_digest`: the subject's accepted store record minus its
lifecycle field (a unit's `state`, a plan's `status`), so a claim moving a unit leaves a ruling
current and a changed subject does not. Inline `open_decisions` entries, in the plan file or in the
accepted plan record, are references by `decision_id` (R71), never rulings.

**What clears one.** An accepted `decision_settlement` record associated with the governing record,
whose signed body (`SETTLEMENT_FIELDS`, OpenSSH signature under namespace
`veldo-decision-settlement`) verifies against the settlement signers the host trusts, and is the
current exact binding: this domain, the record's decision id and revision, its framing digest, its
subject (kind, id and digest, the digest also equal to the subject's current accepted digest), the
digest of its scope with a target that is the subject itself, and the ruling `approve`. The named
blockers are `missing_decision`, `ambiguous_decision`, `unresolved_decision`, `unsupported_decision`
(another schema, a subject kind other than spec or plan, a malformed field, or any obligation, since
Release 1 evaluates none: tripwires and adversarial decision review are Release 3),
`unsigned_decision`, `unbound_decision:<id>/<field>` and `decision_ruling`. A malformed governing or
settlement record is `invalid_input:<id>/<field>`, decided first (review B, below). A verifier that
cannot run is `unavailable_service:settlement_verifier`. Each maps to the Gate's error taxonomy.

**Where the trust comes from.** `HostTrust` may name `settlement_signers`, an absolute path whose
resolved file lies outside the checked workspace (the same rule as the enrollment signers); the
production `entry_gate` builds its Gate with that `SettlementTrust`. A host naming none trusts no
settlement, so every governing decision blocks.

**Tickets and observations.** A station decision now also consumes the governing records, their
settlements and one derived input, `decision_subjects`, whose digest is exactly the subject digests
consumed. Every `decision_blockers` read is recorded with a decision id, domain, repository, unit,
references, watermark, accepted input versions, outcome, refusals and taxonomy; `Gate.status()`
reports `decisions` (accepted, refused, and the units whose latest decision evaluation blocked).

## Criteria, rows and driven mutations

Suite `scripts/suites/62_veldo_0054_decisions.py`, 37 rows (21 assertions and 16 `ran/` rows, one per
region; 12 before the first review, 15 before the second, 23 before the third, 31 before the fourth). One temporary tree is both the repository the plan and frontier readers read and the
installed `.veldo` they run from; a real SQLite store with keyed journal signatures; settlements
signed by real Ed25519 keys through `ssh-keygen -Y sign` and verified by the production
`SettlementTrust`. 34 units are admitted, claimed, approved and dependency-free under ready plans,
and each has exactly one governing-decision situation, so every hold-back is the decision
evaluation's. The fixture spells every digest and the signed bytes itself, so the reader is judged
against an independent writer. Every consumer is asked about every unit: the five stations, the
frontier, `_decision_blocks`, `item_state`, the burn-down lines of `cmd_status`, `veldo status`'s
burn-down and `cmd_run_check` (its exit and every named refusal it prints). `observations.json` holds each unit's answers.

Every mutation below is registered as finding 54 in `scripts/check_teeth_mutations.py`, applied to a
temporary copy, and required to turn its named row red by a failed assertion while the unmutated
copy is green; none reddened a `ran/` row. All 50 were rejected (18 before the first review, 24 before the second, 32 before the third, 43 before the fourth) (`mutations.json`, each diff in
`mutations/`).

**AC1, exact binding.** Rows `decisions/consumers-from-call-sites`, `decisions/exact-binding` and
`decisions/wrong-framing`. The consumer set derived from call sites equals `CONSUMERS` (review A
removed the one unwired reader it used to name), the stations that ask `decisions_settled` are exactly selection,
direct execution, build, review and publication, and the signed fields equal the fixture's. Spec
and plan subjects with current signed settlements are clear everywhere before any change; after
it, only the current exact bindings unblock (VELDO-9401 spec, VELDO-9406 plan): a subject whose
accepted record changed (`/subject_digest`, spec VELDO-9402 and plan VELDO-9407), a record that
followed the subject while the signed ruling did not (`/subject`), a framing revised in place
(`/framing`) or as a new revision (`/revision`), and a rejecting ruling (`decision_ruling`) all
block. Wrong framing: a receipt without its framing digest, one for another framing and one with an
empty digest each block with `/framing`.
- Declared falsifier `framing-receipt-without-digest` (accept a receipt without its framing digest):
  red `wrong-framing`.
- Second mutation `framing-shape-only` (framing checked for shape, not equality): red `wrong-framing`.
- Further driven rows: `subject-currency-ignored` and `floor-stations-skip-decisions`
  (exact-binding), `consumer-unregistered` (consumers-from-call-sites).

**AC2, named blockers.** Rows `decisions/named-blockers` and `decisions/unsigned-resolution`. Missing
(a reference in the accepted plan record and file, and one only the file carries), ambiguous (a
reference two records carry, and two verified current settlements), unsupported (a tripwire
obligation, an adversarial decision review obligation, a contract subject, each WITH a valid
settlement), unresolved, and a valid referenced decision, through every consumer. A file-only
reference is held back by every file reader and invisible to the store-backed stations, which is
exactly what they can see. No inline resolution substitutes for settlement: a record saying
`state: settled`, `ruling: approve`, `resolved: true`; a settlement with no signature; one signed by
an untrusted key; one whose body was edited after signing; and plan entries (store and file) saying
`status: resolved, ruling: approve` all block.
- Declared falsifier `inline-status-as-ruling` (a record's settled status taken as a ruling): red
  `unsigned-resolution`.
- Second mutations `unsigned-settlement-accepted` and `plan-inline-resolution-honored`: red
  `unsigned-resolution`.
- Further driven rows: `ambiguous-settlement-first`, `unsupported-obligation-presumed`,
  `missing-reference-ignored`, `frontier-inline-decisions`, `run-check-ignores-file-references`
  (named-blockers).

**AC3, subject and scope.** Row `decisions/scope-binding`. A ruling on VELDO-9440 re-pointed at
VELDO-9441 with the same framing, decision and revision; a copy of that signed ruling associated with
another decision; rulings whose operation, target or parameters changed; a plan ruling on PLAN-9404
re-pointed at PLAN-9405; and a consistently signed ruling whose scope targets another spec are each
clear or valid before the change and refused after it, with a valid control clear. The journal
watermark, every entity's version and digest, and every spec and plan file are byte-identical before
and after all the consumers ran.
- Declared falsifier `scope-binding-ignored` (reuse one subject's ruling for another): red
  `scope-binding`.
- Second mutation `scope-target-may-differ`: red `scope-binding`.

**Production construction and observability.** Row `decisions/production-gate-verifies`: in a really
enrolled workspace, `entry_gate` with host-trusted settlement signers clears VELDO-9401; a host
naming none yields `unsigned_decision`; signers inside the workspace or named relatively stop by name.
Driven by `production-trust-not-wired`. Row `decisions/observations`: every family is seen with its
taxonomy, no refusal is `unknown_outcome`, every dependency read carries its identity keys, the
metrics count and list the blocked units, and with no ssh-keygen on PATH the answer is
`unavailable_service:settlement_verifier`. Driven by `taxonomy-unbound-unknown` and
`verifier-unavailable-as-unsigned`.

## Narrowest seams, stated

The governing decision record and the settlement record are consumed, not produced: VELDO-0069 is
the settlement producer that will write them, and VELDO-0020's `settle` is the transition it will
sign. The fixture's signatures test consumption only and authenticate no live owner. The Gate's other
inputs are VELDO-0052's seams as landed.

## The suite 60 fixture, and two readers outside the footprint

**Suite 60 lost one fixture line.** `scripts/suites/60_veldo_0052_eligibility.py` stored
`decision:settled`, a record whose only resolution was `state: 'settled'` with no settlement, and
expected it NOT to block VELDO-9106, its valid unit. That is exactly the inline status edit this
specification's AC2 refuses, so with the new predicate suite 60 was red (15 rows). By the lead's
decision the file joined VELDO-0054's footprint with a History line, and that one line was deleted
(no other change): suite 60 passes 80 of 80 and `--finding 52` rejects all 47 mutations. VELDO-9104's
expectation (`unresolved_decision:decision:9104`) is unchanged.

**One reader keeps the pre-factory reading.** `plan.cmd_release_check` was not in the enumerated set
and still refuses a release while any inline `open_decisions` entry exists, which is conservative.

## 2026-09-23 review: two fixes and one open item

A fresh review of af58be2..1e1bc00 found nothing that bypasses the binding, and two defects. Each was
fixed test first: rows that fail by assertion over 1e1bc00's production modules (`red.py`, recorded in
`red-1e1bc00-suite62.json` and `red-1e1bc00-suite60.json`), then the fix, then two or more registered
mutations per new row with the unmutated copy as control.

**A, `veldo status` reads decisions through the Gate (c4a33bc).** `runstatus._burndown` built its
burn-down with `plan._decision_blocks(fm)` and no Gate, so a unit a governing decision held back
showed at the frontier in `veldo status` while plan status blocked it. It now passes
`EL.gate_for(root, eligibility)`, joins `CONSUMERS` (the scan's unwired whitelist is gone) and the
footprint with a History line. Suite 62's new row `decisions/status-reader-agrees` compares the two
for every unit (VELDO-9428 `blocked: decision unresolved_decision:decision:D-9428` in both), and
suite 60's `completion/status-reader-agrees` now compares `veldo status` with plan status read through
the Gate (VELDO-9104 held by its unresolved decision). Both were red by assertion at 1e1bc00.
Mutations `status-reader-inline-decisions` and `status-reader-ignores-decisions` (finding 54, red
`status-reader-agrees`), `status-reader-decisions-inline` and `status-reader-decisions-dropped`
(finding 52, red `completion/status-reader-agrees`).

**B, malformed records are named, never a crash (13fdb00).** At 1e1bc00 one `decision_settlement`
whose `decision` was a list made the Gate's read, `decision_blockers`, plan status, run-check and the
frontier raise an unnamed `TypeError` for every unit (in the red record the production and
observations regions raise on that same record). Now a malformed governing record (a wrong type
anywhere, an unhashable `decision_id`) or a malformed associated settlement (a body that is not a
mapping, a signature or signer that is not text, a signed field of the wrong type) is
`invalid_input:<id>/<field>` for the units it governs, decided before anything else; an inline
reference that is not an id is `invalid_input:decision_reference`; and a settlement nothing can
associate (a list or mapping in `decision`; the store itself refuses non-mapping data) concerns no
unit, is left out of every read and is recorded once as an `invalid_record` observation and in
`Gate.status()['decisions']['invalid_records']`. Row `decisions/malformed-records-named`: two such
settlements in the store, five units each with one malformed input held back by exactly its named
code at every consumer, VELDO-9401 and VELDO-9406 still clear, and `blockers()` called directly
with junk of every shape returns named codes. Mutations `invalid-record-not-observed`,
`record-invalid-ignored`, `settlement-invalid-ignored` and `reference-invalid-dropped`.

**C, open item, not built here: signers files the workspace controls through a sibling worktree or a
hardlink.** `_workspace_areas` resolves the checked workspace, its working tree and its git common
directory, but not the other linked worktrees of the same repository, and it compares paths, not
files. So a settlement signers file (or, identically, an enrollment signers file) placed in a SIBLING
linked worktree of the same repository, or a host path that is a hardlink to a workspace file, is
accepted. This predates VELDO-0054 (the enrollment rule is the same predicate, from VELDO-0052) and
needs its own ticket: enumerate every worktree of the common directory, and compare by device and
inode rather than by path.

## 2026-09-23 second review: three shape fixes and three open items

A fresh review of c4a33bc..53847df found fix A correct and two gaps in fix B, plus a naming
inconsistency. Each was fixed test first, one commit per item: its row fails by assertion over
53847df's production modules (`red-53847df-suite62.json`: exactly the four new rows red, no region
raised), then the fix, then two mutations per new row with the unmutated copy as control.

**1, an unhashable subject field (2babe03).** A governing record whose `subject.kind` was a list or a
mapping made the Gate's read raise `TypeError`, so decide, plan status, the frontier and `veldo
status` crashed. `subject_entity` and `record_problems` check the subject's types before any lookup,
and the unit is held by `invalid_input:<id>/subject` at every consumer. `runstatus._burndown_or_stop`
now names a burn-down it cannot build (`refused:<code>`, `burndown_unanswerable:<type>`) instead of
letting one malformed accepted record take the whole read model down. Rows
`decisions/malformed-subject-named` (kind a list, a mapping, id a list, digest a mapping) and
`decisions/status-names-its-stop`; mutations `subject-digest-type-unchecked`,
`subject-kind-type-unchecked`, `status-stop-crashes`, `status-stop-unnamed`.

**2, a malformed blocks (d315d7c).** A `blocks` that was a mapping or a nested list governed nothing,
so the unit its author meant to hold was offered and built. A `blocks` present and not a list of ids
now governs every unit it names anywhere inside it, where it is refused by `invalid_input:<id>/blocks`,
and the record is recorded once in `invalid_records` with a named observation; one naming no unit
holds no one. Row `decisions/malformed-blocks-held`; mutations `malformed-blocks-govern-nothing`,
`malformed-blocks-unrecorded`.

**3, a wrong-typed schema (a7f2e53).** A schema that is a list or a number is
`invalid_input:<id>/schema`, not unsupported or unresolved, and every `invalid_input` is decided before
unsupported and before unresolved. Row `decisions/invalid-before-unsupported`; mutations
`schema-type-unchecked`, `invalid-after-unresolved`.

**Open items, each for its own ticket (all predate VELDO-0054).**
- A unit record whose `plan` field is a list fails inside `Gate.read` (`'plan:' + data['plan']`,
  VELDO-0052 code). Since the third review's item 1 no consumer raises on it: decide and
  decision_blockers name it `unknown_outcome:evaluation_error/TypeError` for that unit. It should be a
  specific `invalid_input:<unit>/plan`, which is its ticket.
- A plan file whose `open_decisions` entry has a `blocks` holding a nested list makes
  `plan._decision_blocks` (its inline half) and `.veldo/validate.py` raise on the unhashable member.
  `veldo status` names it (`burndown_unanswerable:TypeError`, row `decisions/status-names-its-stop`).
- A tampered accepted row makes plan status and the frontier raise the store's named
  `Refused: input_digest_mismatch` from VELDO-0052's completion reader; decide, decision_blockers and
  `veldo status` name it `missing_authority:input_digest_mismatch`.
- A unit record whose `backlog_item_uuid` is a list, or whose `depends_on` holds a nested list, is
  reported `unavailable_service:store`: the value reaches a SQLite parameter bind, which fails, and
  decide maps every `sqlite3.Error` to an unavailable store. It should be `invalid_input:<unit>/<field>`.
- A malformed governing record reached only through an ambiguous reference (two records carrying
  the same `decision_id`, one of them malformed) is named `ambiguous_decision:<ref>` alone; the
  malformed one's own `invalid_input` is not reported beside it.
- `scripts/update_index.py` derives each plan item's frontier state in the committed `specs/index.md`
  from the inline `open_decisions` text. That is by design: the committed index is generated from the
  checkout and cannot read the control store, so it shows every inline entry as blocking and knows
  nothing of settlements; the store-backed readers (plan status, `veldo status`, the frontier) are
  the authority.

## 2026-09-23 third review: two blocking fixes, one ordering fix and three minor ones

A fresh review of 53847df..f1c9803 found two blocking defects, an ordering inconsistency and three
minor gaps. Each was fixed test first, one commit per item: its row fails by assertion over f1c9803's
production modules (`red-f1c9803-suite62.json`: exactly the four new rows red, no region raised),
then the fix, then two or three mutations per new row with the unmutated copy as control.

**1, deep blocks and unexpected faults (84d8b19).** The recursive walker over a malformed `blocks`
raised `RecursionError` on one nested about 1000 deep, which the store accepts, and broke every unit's
decide, the frontier, plan status and run-check. The walker now uses an explicit stack, and decide and
decision_blockers name any fault nothing anticipated as `unknown_outcome:evaluation_error/<type>` for
the unit concerned instead of raising. Row `decisions/deep-blocks-named` (5000 deep, and a verifier
that raises); mutations `blocks-walk-recursive`, `decide-raises-unexpected`,
`blockers-raise-unexpected`. The status-stop row now probes with a plan file whose inline `blocks`
holds a nested list, since decide no longer raises on a unit whose plan is a list.

**2, a store refusal in `veldo status` (cac608c).** The broad catch reported a tampered accepted row as
`burndown_unanswerable:Refused`. The Gate exposes its store refusals (`refusal_types`) and their one
naming (`refusal_code`); the burn-down catches exactly those and reports
`refused:missing_authority:input_digest_mismatch`, and decision_blockers now names them as decide
does. Row `decisions/status-names-store-refusal` (one row tampered, then restored); mutations
`status-store-refusal-generic`, `status-store-refusal-code-dropped`, `blockers-store-refusal-renamed`.

**3, settlements before unsupported (50548d5).** A malformed settlement is `invalid_input` before its
record is judged unsupported. Row `decisions/settlement-invalid-before-unsupported`; mutations
`unsupported-before-settlement-invalid`, `settlement-signature-type-unchecked`.

**Minor (f928eb0, anchor follow-up b1ec5ff).** A `blocks` string naming two ids, or one padded id, holds every id it
names; a plan reference that is not an id is recorded in `invalid_records` under the plan record, and
so is a record whose `decision_id` is malformed; the dead kind check in `record_problems` is gone.
Row `decisions/minor-shapes`; mutations `blocks-string-not-split`, `plan-reference-unrecorded`,
`decision-id-unrecorded`.

## 2026-09-23 fourth review: three small fixes and a changelog correction

A fresh review of f1c9803..e6146ad found nothing blocking and one defect with two related gaps. The
branch first merged origin/main (486ca23, including the parallel mutation driver). Each fix was test
first, one commit per item: its row fails by assertion over e6146ad's production modules
(`red-e6146ad-suite62.json`: exactly the three new rows red, no region raised), then the fix, then two
or three mutations per new row with the unmutated copy as control.

**1, signer and signature text (0c7b133).** A settlement signer or signature holding NUL, or text that
does not encode (a lone surrogate), reached ssh-keygen and failed there, so decide named the unit
`unknown_outcome:evaluation_error` and dropped its other refusals. `settlement_invalid` now refuses
such text as `invalid_input:<id>/signer` or `/signature`, and the unit's other refusals stand beside
it. Row `decisions/settlement-text-encodable`; mutations `settlement-nul-passed`,
`settlement-unencodable-passed`.

**2, a stop under decide (23045f0).** The catch-all also caught eligibility's own `Stopped`, turning a
terminal stop into a hold on one unit; decide and decision_blockers now re-raise it. Row
`decisions/stops-propagate`; mutations `decide-holds-a-stop`, `blockers-hold-a-stop`.

**3, the fault's message (904e6b5).** An unexpected fault is named
`unknown_outcome:evaluation_error/<type>/<message>`, the message on one line, ASCII only and bounded
to 160 characters. Row `decisions/unexpected-message`; mutations `unexpected-message-dropped`,
`unexpected-message-unbounded`, `unexpected-message-multiline`.

**4, the changelog.** The third review's History entry said a store refusal is named by its code
everywhere; it now says where that holds (decide, decision_blockers and `veldo status`) and that plan
status and the frontier are the open item.

## Cost and verification

After four reviews suite 62 runs in 4.4 s here (`observations.json`, `suite_seconds`; 1.2 s as first
built; the growth is the new regions' sweeps, each of which reads every decision and settlement
record per unit), measured while this host's load average was about 36. With main's parallel driver
`--finding 54` drives 50 mutations in 50.15 s here and `--finding 52` drives 49 in 12.14 s. In the gate's
mutation stage (8 workers) finding 54 is about 55 runs (50 mutants and 5 control groups) or roughly
30 s of wall time at this host's current speed, and it raises the stage's scaled budget by 100 s;
with the unit stage that is about 35 s the new suite adds to the gate, under the 60 s limit. Targeted checks run on this branch:
`python3 -B scripts/selftest.py --suite 62_veldo_0054_decisions` (63 passed, 37 of them this suite's),
`--suite 60_veldo_0052_eligibility` (80 passed), `python3 -B scripts/check_teeth_mutations.py --finding 54`
(50 rejected) and `--finding 52` (49 rejected), `check_first_use.py` (pass, 353 s, at 1e1bc00), `python3 .veldo/validate.py
all`, `bash scripts/check_generated.sh`, `bash scripts/check_template_sync.sh`, lint, docs,
install-and-run, and every other suite that loads a module touched here, suite 60 included. The full gate is run by the lead.

`drive.py` regenerates `observations.json` from one run of the suite.
