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

Suite `scripts/suites/62_veldo_0054_decisions.py`, 23 rows (14 assertions and 9 `ran/` rows, one per
region; 12 before the first review, 15 before the second). One temporary tree is both the repository the plan and frontier readers read and the
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
copy is green; none reddened a `ran/` row. All 32 were rejected (18 before the first review, 24 before the second) (`mutations.json`, each diff in
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
- A unit record whose `plan` field is a list makes `Gate.read` raise (`'plan:' + data['plan']`, VELDO-0052
  code); every consumer that visits that unit raises. `veldo status` now names it
  (`burndown_unanswerable:TypeError`, the probe row `decisions/status-names-its-stop`) but the other
  consumers still raise.
- A plan file whose `open_decisions` entry has a `blocks` holding a nested list makes
  `plan._decision_blocks` (its inline half) and `.veldo/validate.py` raise on the unhashable member.
- `scripts/update_index.py` derives each plan item's frontier state in the committed `specs/index.md`
  from the inline `open_decisions` text. That is by design: the committed index is generated from the
  checkout and cannot read the control store, so it shows every inline entry as blocking and knows
  nothing of settlements; the store-backed readers (plan status, `veldo status`, the frontier) are
  the authority.

## Cost and verification

After both reviews suite 62 runs in 2.5 s here (`observations.json`, `suite_seconds`; 1.2 s as first
built; the growth is the new regions' sweeps, and this host was carrying other builds).
`--finding 54` drives 32 mutations in 167 s here (64 suite runs); in the gate's mutation stage (8
workers) that is about 37 runs (32 mutants and 5 control groups) or roughly 12 s of wall time, and it
raises the stage's scaled budget by 64 s. `--finding 52` drives 49 mutations (47 before review A) in
157 s here. Targeted checks run on this branch:
`python3 -B scripts/selftest.py --suite 62_veldo_0054_decisions` (49 passed, 23 of them this suite's),
`--suite 60_veldo_0052_eligibility` (80 passed), `python3 -B scripts/check_teeth_mutations.py --finding 54`
(32 rejected) and `--finding 52` (49 rejected), `check_first_use.py` (pass, 353 s, at 1e1bc00), `python3 .veldo/validate.py
all`, `bash scripts/check_generated.sh`, `bash scripts/check_template_sync.sh`, lint, docs,
install-and-run, and every other suite that loads a module touched here, suite 60 included. The full gate is run by the lead.

`drive.py` regenerates `observations.json` from one run of the suite.
