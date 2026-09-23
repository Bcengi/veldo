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
and the frontier's plan candidates. The consumer set is `CONSUMERS`, checked against the actual call
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
`unsigned_decision`, `unbound_decision:<id>/<field>` and `decision_ruling`. A verifier that cannot
run is `unavailable_service:settlement_verifier`. Each maps to the Gate's error taxonomy.

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

Suite `scripts/suites/62_veldo_0054_decisions.py`, 12 rows (8 assertions and 4 `ran/` rows, one per
region). One temporary tree is both the repository the plan and frontier readers read and the
installed `.veldo` they run from; a real SQLite store with keyed journal signatures; settlements
signed by real Ed25519 keys through `ssh-keygen -Y sign` and verified by the production
`SettlementTrust`. 34 units are admitted, claimed, approved and dependency-free under ready plans,
and each has exactly one governing-decision situation, so every hold-back is the decision
evaluation's. The fixture spells every digest and the signed bytes itself, so the reader is judged
against an independent writer. Every consumer is asked about every unit: the five stations, the
frontier, `_decision_blocks`, `item_state`, the burn-down lines of `cmd_status` and `cmd_run_check`
(its exit and every named refusal it prints). `observations.json` holds each unit's answers.

Every mutation below is registered as finding 54 in `scripts/check_teeth_mutations.py`, applied to a
temporary copy, and required to turn its named row red by a failed assertion while the unmutated
copy is green; none reddened a `ran/` row. All 18 were rejected (`mutations.json`, each diff in
`mutations/`).

**AC1, exact binding.** Rows `decisions/consumers-from-call-sites`, `decisions/exact-binding` and
`decisions/wrong-framing`. The consumer set derived from call sites equals `CONSUMERS` plus one
named unwired reader (below), the stations that ask `decisions_settled` are exactly selection,
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

**Two readers keep the pre-factory reading.** `runstatus._burndown` (not in this footprint) still
calls `plan._decision_blocks(fm)` without a Gate, so its display shows every inline entry as blocking
and does not show a store-only governing decision; it grants no eligibility. The scan lists it by
name so it cannot be forgotten. `plan.cmd_release_check` was not in the enumerated set and still
refuses a release while any inline `open_decisions` entry exists, which is conservative.

## Cost and verification

Suite 62 runs in 1.18 s (`observations.json`, `suite_seconds`). `--finding 54` drives 18 mutations
in 44.7 s here (36 suite runs of about 1.24 s); in the gate's mutation stage (8 workers) that is
about 22 runs (18 mutants and 4 control groups) or roughly 3.5 s of wall time, and it raises the
stage's scaled budget by 36 s. Targeted checks run on this branch:
`python3 -B scripts/selftest.py --suite 62_veldo_0054_decisions` (38 passed, 12 of them this suite's),
`python3 -B scripts/check_teeth_mutations.py --finding 54` (18 rejected), `python3 .veldo/validate.py
all`, `bash scripts/check_generated.sh`, `bash scripts/check_template_sync.sh`, lint, docs,
install-and-run, and every other suite that loads a module touched here, suite 60 included. The full gate is run by the lead.

`drive.py` regenerates `observations.json` from one run of the suite.
