# PCATCH arm A - independent adversarial DESIGN review of WARP-1210

Reviewer: fresh-context adversarial design reviewer, no access to any other checkout of this project.
Reviewed artifact: `specs/WARP-1210-the-support-numbers.md` at status `ready`, plus the shipped organs it
reads (`.veldo/metrics.py`, `.veldo/dashboard.py`, `.veldo/entropy.py`, `.veldo/events.py`,
`.veldo/incident.py`, `.veldo/incident_reconcile.py`, `.veldo/reconciliation_store.py`,
`.veldo/architecture.yaml`, `.veldo/arch.py`, `.veldo/shape_gate.py`, `plans/PLAN-0012`,
`specs/WARP-1208`, `specs/WARP-1209`, `proof/WARP-1208/verdict*.json`).
This is a review of the THINKING, not of the sections.

---

## 1. RULING

`do_not_build_yet`

Two of the four measures this item exists to produce cannot be derived from the inputs the spec declares,
and the population every measure is computed over ("closed incidents") is defined in a way that resolves to
the empty set against the shipped records. Those are definitional, not implementation, defects. A faithful
build against this document produces either a refuted AC2 or a support section of honest zeros, and in both
cases the spec has to be rewritten and the build redone.

---

## 2. Findings, most expensive first

### F1. The two headline measures cannot come from the declared inputs, and their real source store is neither declared nor authenticated

**Where.** AC1: "TIME-TO-DIAGNOSIS is opened_at to diagnosed_at and TIME-TO-RESTORE is opened_at to
restored_at, both taken from the incident record's timeline that WARP-1201 already validates as
non-negative". AC1 also: "Every measure is a PURE function over the parsed events and receipts". AC2: "The
receipt store is an INJECTED READER". Notes: "Keep every reader injected (events, receipts, the contract,
and the per-area cost data)". Title: "derived from recorded events and AUTHENTICATED against the
reconciliation receipts so a number can never come from an event no reconciliation produced".

**What is wrong.** Neither the events nor the receipts carry a timeline.

- Only ONE incident lifecycle event has an emitter anywhere in the engine. `incident.opened`,
  `incident.diagnosed` and `remedy.proposed` exist in `.veldo/events.py` EVENT_TYPES and in
  `.veldo/incident.py` INCIDENT_EVENT_TYPES as vocabulary only; the sole `make_event` call for any of the
  four is `_closed_event` at `.veldo/incident_reconcile.py:731`, which emits `incident.closed`. Its `extra`
  is exactly `{incident, reconciliation, failure_signature, recurrence_of, missing_specification}`. There
  is no `opened_at` and no `restored_at` in the stream, and no event pair to difference.
- The receipt (`reconciliation_record`, `.veldo/incident_reconcile.py:694-726`) records schema, id,
  settled_by, incident, remedy, failure_signature, recurrence_of, missing_specification,
  diagnosis_validation, what_was_done, what_it_proved, what_regression_criteria_it_leaves. No timeline.

So the two duration measures can only come from the incident RECORD store (`.veldo/incidents/<id>`, read via
`incident.resolve_incident(incident_id, incidents_dir, parse, loader)`). That store is a fifth input. The
spec never names it as an input, never lists it among the injected readers, never says who constructs its
real reader, and never says what authenticates it. Note also that `.veldo/incidents/` does not exist in this
repository, so nothing in the AC set will exercise the real path.

Worse, the authentication story does not reach it even in principle. The receipt's binding over record
content is `diagnosis_digest` over `diagnosis_material` (`.veldo/incident_reconcile.py:160-165` and
`:305-323`): the identity fields, an optional `diagnosis` field the contract does not define,
`timeline.diagnosed_at`, and the remedy's proposal digest. `opened_at` and `restored_at` are NOT bound by
anything. Both duration measures are differences against `opened_at`. Therefore an edit to
`timeline.opened_at` after settlement moves both headline numbers with no receipt mismatch, no exclusion,
and no name - which is precisely the class of lie the Intent section says the item exists to prevent, one
level below where the spec put its guard. AC2 defends against a forged `incident.closed`; the reachable
attack (and the likelier honest accident) is an edited or unvalidated record.

**What it will cost.** The build will read the record store, will honestly believe it satisfied AC2 because
it gated the population on receipt-backing, and the reviewer will refute AC2 on exactly the reasoning of
`proof/WARP-1208/verdict-1-fail.json` F2 ("the comparison is therefore honest but nearly empty"). That is a
minimum of one refuted round on the item's declared load-bearing property, plus a second round because the
fix changes AC1, AC2, the observability taxonomy and the footprint at once.

**What the spec must say instead.** Add a DATA PROVENANCE block, before AC1, with one row per measure
naming: the exact field path, the store it lives in, the reader seam, the constructor of the real reader,
and the receipt binding that authenticates it (with the literal word `unauthenticated` where that is the
truth). Then:
1. Enumerate FIVE injected readers: events, receipts, incident records, the architecture contract, the
   per-area cost data. State the incident record reader's real implementation as
   `incident.resolve_incident(iid, incidents_dir, validate.parse_yamlish, incident.load_incident)`.
2. Require the derivation to RECOMPUTE, for every candidate incident, both
   `incident_reconcile.failure_signature(record)` and `incident_reconcile.diagnosis_digest(record, remedy)`
   from the resolved record and compare them with the receipt's `failure_signature` and
   `diagnosis_validation.recomputed_digest`; a mismatch is excluded and named (`RECORD_DIGEST_MISMATCH`).
   This is the strongest authentication actually available and it is available today.
3. State in AC1 and in the rendered output that `opened_at` and `restored_at` are covered by no receipt
   binding, so the duration trends are receipt-scoped as to WHICH incidents count and unauthenticated as to
   their VALUES. Either accept that with a standing honesty line in the render, or stand the two duration
   trends down until a later item binds the timeline, and say which.

### F2. "Closed incidents" is undefined, and the definition an implementer will reach for resolves to the empty set

**Where.** AC1 uses "closed incidents" as the denominator of both rates ("the share of closed incidents
whose receipt carries a non-empty recurrence_of", "the share of closed incidents resolved FROM ARTIFACTS
ALONE"). AC2 uses "an incident whose closure is backed by a reconciliation receipt". AC5's control speaks of
"a repository with no incidents at all". Nowhere does the spec say what makes an incident closed.

**What is wrong.** There are three candidate populations and they do not coincide.

- `INCIDENT_STATUSES = {"open", "diagnosed", "closed"}` (`.veldo/incident.py:83`). Nothing in the engine ever
  writes `status: closed`. `reconcile_incident` REFUSES unless the status is `diagnosed` (WARP-1208 AC2a),
  and it writes only receipts, drafts and events - it never updates the incident record. So after a
  successful settlement the on-disk record still says `diagnosed`. An implementer who filters on
  `status == "closed"` gets an empty population forever, and every rate renders as its zero-denominator
  stand-down while the repository is full of settled incidents.
- Filtering on the presence of an `incident.closed` event is the correct population but is exactly the
  unauthenticated read AC2 forbids on its own.
- Filtering on receipt-backing is what AC2 wants, and it needs the join key spelled out.

**What it will cost.** This is the single cheapest way to ship a green, faithfully implemented, completely
wrong support section. If it survives review, the numbers are zeros and nobody knows why. If it is caught in
review, it invalidates the denominator of two measures, the fixtures of at least three guards, and the
matrix.

**What the spec must say instead.** One sentence, verbatim precision: "A CLOSED INCIDENT, for every measure
in this item, is an `incident.closed` event in the stream whose `extra.reconciliation` resolves through the
injected receipt reader to a receipt whose `incident` field equals the event's `extra.incident`. The
incident record's `status` field is NEVER consulted to decide closure, because the engine has no writer that
sets it to closed." Add that the receipt id needed for the lookup comes from the event, so no receipt-store
enumeration is required - which matters, because `ReconciliationStore` (`.veldo/reconciliation_store.py`)
exposes only `get(rec_id)`, `settle` and `put_draft`, and has no list primitive on the base class or on
`FilesystemReconciliationStore`.

That last point has a direct consequence the spec must resolve: AC2 also demands `UNRESOLVED_RECEIPT`, "a
receipt whose incident cannot be resolved". Finding those requires enumerating the receipt store, which the
shipped store cannot do, and `.veldo/reconciliation_store.py` is NOT in this item's footprint. The spec must
either (a) redefine `UNRESOLVED_RECEIPT` as event-reachable ("an event whose `extra.reconciliation` resolves
to a receipt whose `incident` does not match the event"), which is implementable today and should be the
choice, or (b) add the store to the footprint and add a `list_ids()` primitive to the base class and every
backend, and accept the tier and re-sync consequences. Do not leave it as prose that reads like (b) and gets
built as (a).

### F3. AC5 asserts an exactly diagonal matrix without making the guards orthogonal, and AC4, AC5 and AC6 require three different renders for the same zero-population input

**Where.** AC5: "Every guard in this item ... is neutralized IN MEMORY one at a time and run against EVERY
guard's fixture, and the resulting matrix is asserted EXACTLY DIAGONAL". AC4: "A measure whose denominator
is zero renders as the named stand-down EMPTY_DENOMINATOR and NEVER as 0 percent, 100 percent, or a dash".
AC5 controls: "a repository with no incidents at all renders the support section as an honest empty state
rather than an error or a row of zeros". AC6: "a repository with no incident events renders exactly as it
did before (adoption safe)".

**What is wrong, part one (the matrix).** The five guards are not independent, and the spec does not
constrain the fixtures enough to make them so. The natural fixture for `EMPTY_DENOMINATOR` is "no
authenticated incidents", and the natural way to build that is incident events with the receipts removed -
which is verbatim the `UNBACKED_EVENT` fixture (AC2 already mandates it: "the SAME lifecycle with the
receipts removed counts NOTHING"). Neutralize the unbacked-event exclusion and that fixture's denominator
becomes non-zero, so the `EMPTY_DENOMINATOR` stand-down disappears: an off-diagonal cell, and the "exactly
diagonal" assertion fails. The same coupling exists between the no-contract stand-down and the no-cost-data
stand-down, since `entropy_report` returns `{"standdown": True}` for the no-contract case and there is no
cost data in that branch either.

**What is wrong, part two (the zero-population render).** For a repository with no incident events, AC6
requires the render to be byte-identical to today (no support section at all), AC5's control requires "an
honest empty state" (a section, with a line in it), and AC4 requires each rate to render its
`EMPTY_DENOMINATOR` stand-down (a section, with several lines in it). Three sentences, three mutually
exclusive outputs, one input. Whichever the builder picks, a reviewer reading either of the other two
sentences records an unmet criterion, and the argument is about wording rather than about a defect - the
most expensive kind of round this project has.

**What it will cost.** The 25-cell matrix is the most expensive single artifact in the item. Building it,
finding one off-diagonal cell, redefining either the guard set or the fixtures, and rebuilding it is most of
a round on its own. The render contradiction is a second round and it is pure wording.

**What the spec must say instead.**
1. Declare each guard's fixture EXPLICITLY and disjointly, and require that the empty-denominator fixture
   contain NO incident events at all so that no other guard can reach it. Then state the expected matrix in
   the spec: "5 diagonal cells green, 20 off-diagonal cells unchanged", so the builder is proving a declared
   result rather than discovering one.
2. Give a precedence rule for the zero-population case, in one place: "ABSENT (no `incident.closed` event in
   the stream) renders NOTHING new - AC6's byte-identity holds and there is no support section. PRESENT BUT
   UNAUTHENTICATED (events exist, zero survive the receipt join) renders the section with the named
   exclusions and the named `EMPTY_DENOMINATOR` stand-down per rate. `EMPTY_DENOMINATOR` is never rendered
   for the ABSENT case." Then delete the phrase "an honest empty state" from AC5, because it names a fourth
   thing.

### F4. Recurrence rate is caller-dependent and will read 0 percent for a reason that is not "no recurrence"

**Where.** AC1: "RECURRENCE RATE is the share of closed incidents whose receipt carries a non-empty
recurrence_of, which is exactly the missing-specification signal WARP-1208 records."

**What is wrong.** `recurrence_of` is not a property of the history; it is a property of what the caller
passed. `reconcile_incident(incident, store, remedy=None, prior_incidents=None, ...)` computes
`recurrence(incident, prior_incidents)` (`.veldo/incident_reconcile.py:281-297, 758, 787`). If a caller
settles an incident without supplying the prior set - the default is `None`, and nothing in the engine calls
this pass automatically - the receipt honestly records `recurrence_of: []` and `missing_specification:
false`. The receipt does not record WHICH priors were considered, so a 0 percent recurrence rate is
indistinguishable from "nobody passed priors at settlement time". This is a number a human acts on ("we are
not repeating failures") that is false for a reason invisible in the output, which is the exact failure the
Intent section names.

**What it will cost.** It will not be caught by any selftest in the current AC set, because the fixtures
seed `prior_incidents` deliberately (WARP-1208's own selftest does: `kw = {..., "prior_incidents": [prior],
...}`). It ships as a confident zero. When someone eventually notices, the fix is a change to the
derivation, not to a test.

**What the spec must say instead.** The derivation has everything it needs to be honest here, because every
receipt carries `failure_signature`. Require: "Recurrence rate is derived by GROUPING the authenticated
receipts by `failure_signature` and counting the incidents that are not the first occurrence of their
signature in recorded order. The recorded `recurrence_of` is then CROSS-CHECKED against that grouping, and a
divergence - two receipts sharing a signature where neither names the other - is reported by name
(`RECURRENCE_UNDERREPORTED`) with both incident ids, because `recurrence_of` depends on the prior set the
settlement caller supplied and a receipt records no evidence of what that set was." This is strictly
derivable from the declared inputs and it turns a silent zero into a named gap.

### F5. AC1 and AC3 together force an unbounded mutual recursion between `.veldo/metrics.py` and `.veldo/entropy.py`

**Where.** AC1: the measures live "in the existing metrics derivation (.veldo/metrics.py, extended)". AC3:
"the result is joined with PLAN-0011's cost-to-change-per-area data on ONE map when that data exists".
Context: "PLAN-0011's per-area cost-to-change data in .veldo/entropy.py".

**What is wrong.** `.veldo/entropy.py` loads `.veldo/metrics.py` at MODULE scope (line 82:
`metrics = _load("veldo_metrics", ".veldo/metrics.py")`) and calls `metrics.compute(events)` inside
`cost_components` (line 97). The `_load` helper uses `spec_from_file_location` + `module_from_spec` +
`exec_module` and does NOT register in `sys.modules`, so there is no cycle-breaking cache. If
`metrics.compute` loads entropy and calls `entropy_report`, then entropy's private metrics copy calls
`compute`, which loads a fresh entropy, which calls `entropy_report` again: recursion until
`RecursionError`. This is not a style concern; it is a guaranteed runtime failure on the first real run of
the joined path, and it will not show up in a selftest that injects a fake cost reader.

Related: `entropy_report(events=None, root=None)` is a root-based filesystem reader that also runs the
shape-gate static analyzers over the tree. It is not an injected-reader design, and calling it from inside
`compute()` would also make `compute()` - which `.veldo/budget.py`, `.veldo/governor.py` and `.veldo/entropy.py`
all call - suddenly do a whole-tree static analysis.

**What it will cost.** One build round discovers it at runtime. The fix relocates the join, which moves an
AC and possibly the footprint, so it is a spec change mid-build.

**What the spec must say instead.** "`.veldo/metrics.py` never references `.veldo/entropy.py`. The per-area
cost figures reach the derivation as an INJECTED mapping of area id to cost figures, constructed by the
top-level callers only (`metrics.main`, `dashboard.render_text`, `dashboard.render_html`) from
`entropy.area_figures(entropy.entropy_report(events=events, root=root))`, which `.veldo/dashboard.py` already
loads. `compute`'s parameter defaults to `None`, which is the `NO_AREA_COST_DATA` stand-down. A selftest
asserts the string `.veldo/entropy.py` does not appear in `.veldo/metrics.py`."

### F6. Nobody is named as the constructor of the real readers, so the shipped default is a permanent stand-down that every selftest passes

**Where.** AC2: "The receipt store is an INJECTED READER, so the derivation stays pure and a repository with
no receipts stands down to zero authenticated incidents rather than falling back to the raw events." AC6:
the change is "additive" and existing numbers are byte-identical.

**What is wrong.** The existing signature is `compute(events)`, and its callers pass exactly one argument:
`dashboard.report_figures` (line 45), `entropy.cost_components` (line 97), plus `budget.py` and
`governor.py`. New readers will therefore be keyword parameters defaulting to `None`. Every AC in this item
is provable with injected fakes. Nothing in the AC set requires the REAL path to be wired. The most likely
outcome of a faithful build is a shipped dashboard that renders "0 authenticated incidents, 0 receipts" on
every repository forever, with a fully green gate and a 25-cell diagonal matrix behind it. That is the
failure mode this whole review exists to catch: rigorous work against a document that never asked for the
wiring.

**What the spec must say instead.** Name the call sites: "`metrics.main()` and `dashboard.main()` construct
the real readers from the repository root: the receipt reader as a `FilesystemReconciliationStore(root)`,
the incident record reader as `incident.resolve_incident` bound to `incident.default_incidents_dir(root)`
and `validate.parse_yamlish`, the contract and per-area cost reader as in F5. `compute` and
`report_figures` gain the readers as keyword parameters with `None` defaults." And add one criterion that
tests it: "A selftest builds a TEMPORARY tree with real files on disk - one incident record, its receipt
under `.veldo/reconciliations/`, its `incident.closed` line in `events.jsonl`, and an architecture contract -
runs `dashboard.render_text` through `main`'s own wiring, and asserts the support section reports ONE
authenticated incident and a non-null value for each of the four measures." Without that single end-to-end
assertion, none of the other 60 assertions can tell a wired build from an unwired one.

### F7. The diagnosability score has one vacuous conjunct and one that measures whether an optional field was filled in

**Where.** AC1: "The DIAGNOSABILITY SCORE is the share of closed incidents resolved FROM ARTIFACTS ALONE,
defined mechanically as those whose receipt records a diagnosis validation and whose incident resolves to a
governing spec or area in the corpus, never inferred from prose."

**What is wrong.** Conjunct one cannot discriminate. `reconcile_incident` REFUSES to settle without a
supplied human diagnosis validation whose actor is non-machine and whose bound digest matches the
independently recomputed digest (`REFUSE_MISSING_VALIDATION`, `REFUSE_MACHINE_VALIDATOR`,
`REFUSE_VALIDATION_DIGEST_MISMATCH`, WARP-1208 AC2). Therefore every receipt that exists carries a
`diagnosis_validation` block. Over the authenticated population the predicate is a constant true: it cannot
be false, it cannot be given teeth, and it contributes nothing to the score while making the definition read
as though it does.

Conjunct two is what is left, and it is "does the record carry `affected_area`, or an `affected_spec` that
resolves in the corpus". `.veldo/incident.py:227-229` makes both fields OPTIONAL and validates them only for
non-emptiness when present. So the "diagnosability score" is the rate at which incident reporters filled in
an optional field. It is presented to a human as "share of incidents resolved from artifacts alone".

This is the same class of finding as `proof/WARP-1208/verdict-1-fail.json` F2, which was recorded blocking:
a stated binding that binds nothing. This reviewer pool will treat it the same way, and it should.

Third gap: an incident carrying an `affected_spec` that does NOT resolve in the corpus (a renamed or deleted
spec) silently lowers the score, and the closed taxonomy has no name for it. A silent downward pressure on a
quality metric is the same defect as a silent upward one.

**What the spec must say instead.** Pick one and write it:
- Option A, honest rename: "ARTIFACT ATTRIBUTION RATE: the share of authenticated incidents that resolve to
  a governing spec or area in the corpus, numerator and denominator shown. It is a declared PROXY for
  diagnosability and it measures attribution, not understanding; the review-lane label says so in the module
  and in the render."
- Option B, add a discriminating conjunct that actually varies over the population and name it, for example
  "and whose receipt's `what_it_proved` records an execution receipt outcome rather than `none`".
Either way, add the named exclusion `SPEC_NOT_IN_CORPUS` for an `affected_spec` that does not resolve, and
state that such an incident is excluded from the numerator AND the denominator rather than counted as
not-diagnosable.

### F8. The closed taxonomy is missing at least four names the design meets on day one, and one of them carries a known identity trap

**Where.** The `observability.error_taxonomy` block: "a closed, named set (UNBACKED_EVENT,
UNRESOLVED_RECEIPT, EMPTY_DENOMINATOR, NO_AREA_COST_DATA, NO_ARCHITECTURE_CONTRACT)".

**What is wrong.** Four reachable states have no name, so the derivation will either drop them silently
(the defect this item is about) or invent a name in the build, which is a spec change.

1. **A closed incident with no `restored_at`.** `.veldo/incident.py:246-248` checks `restored_at` only for
   ordering; a `closed` (or `diagnosed`) record is fully valid without it. AC1 asserts the timeline is one
   "that WARP-1201 already validates as non-negative", which is true and irrelevant: WARP-1201 does not
   require `restored_at` to exist. Time-to-restore is therefore undefined for legitimately valid records,
   and `EMPTY_DENOMINATOR` is about rates, not trends. Needs `RESTORE_TIME_UNRECORDED`.
2. **A receipt that exists and cannot be read.** `store.get()` returns the `UNREADABLE` sentinel, and
   `.veldo/reconciliation_store.py` states in its docstring that a caller "must tell the three apart: an
   unreadable receipt is a CONFLICT, never an absence". Reporting it as `UNBACKED_EVENT` is a false name -
   the event IS backed, the backing is corrupt. Needs `RECEIPT_UNREADABLE`.
   **The trap:** `proof/WARP-1208/verdict.json` carries note 1 - the sentinel is compared by OBJECT
   IDENTITY, so a store loaded from a second module instance defeats an identity check. This item will load
   `reconciliation_store.py` in a different place from whoever constructed the store. So the spec must say:
   "the derivation classifies any return from `store.get` that is neither `None` nor a mapping as
   `RECEIPT_UNREADABLE`, BY SHAPE; it never compares against the store module's `UNREADABLE` sentinel by
   identity, because a second module instance defeats identity (WARP-1208 verdict note 1)."
3. **An event whose incident id resolves to no record on disk.** Needs `INCIDENT_RECORD_MISSING`.
4. **A record that resolves but is malformed** (a non-ISO `opened_at`, a `timeline` that is not a mapping).
   The derivation reads records directly and cannot assume the gate ever validated them - `check_records`
   stands down when the incidents directory is absent, and it is absent here. Needs `MALFORMED_RECORD`.

**What it will cost.** Each unnamed state is one review comment if caught, and one silently wrong number if
not. Item 2 additionally risks an `AttributeError` on the real path only (the sentinel is an object, not a
mapping), which no injected-fake selftest will reach.

### F9. The per-area join specifies three cases and omits the only one that occurs in practice

**Where.** AC3: "Selftests prove all three paths over temporary trees: with a contract and seeded cost data
the map joins and both columns appear; with a contract but no cost data the incident column renders and the
cost column stands down by name; with no contract at all the whole join stands down."

**What is wrong.** `entropy_report` returns a per-area series and sets `standdown: True` only for the
no-contract case. In any live repository some areas have cost samples and some do not, and some areas have
incidents while most do not. The mixed case - contract present, cost data for SOME areas, incidents for a
DIFFERENT some - is the actual state of this repository and every adopter's, and AC3 does not say what it
renders. An implementer with a global `NO_AREA_COST_DATA` flag will either suppress the cost column for
areas that do have data, or print a zero for areas that do not, and AC4 forbids the second.

**What the spec must say instead.** "The join is PER AREA. Each cell renders a value or that side's named
stand-down: an area with incidents and no cost samples renders the incident count and `NO_AREA_COST_DATA`
for the cost cell; an area with cost samples and no incidents renders the cost figures and a zero incident
COUNT (a count of zero is a count, not a rate, and is honest); an area named by neither is not rendered.
`NO_ARCHITECTURE_CONTRACT` is the only global stand-down. A fourth selftest covers the mixed fixture: two
areas, one with cost data and no incidents, one with incidents and no cost data."

### F10. AC6's byte-identity assertion is not implementable as written

**Where.** AC6: "a selftest asserts every measure already computed by .veldo/metrics.py is byte-identical
before and after this change over the same event stream".

**What is wrong.** At test time there is no "before". The old implementation is gone and nothing in the
footprint holds a vendored copy or a golden fixture file. The builder will write something adjacent -
usually a literal expected mapping - and the reviewer will observe that it does not prove what the sentence
claims. It is also silently weak in one direction: an assertion of the form "the new output contains these
key/value pairs" passes even if a pre-existing key is removed.

**What the spec must say instead.** "A selftest seeds a FIXED event stream (declared inline), computes
`compute()`, and asserts that the set of pre-existing top-level keys is EXACTLY the enumerated list
[events_total, changes_tracked, spec_to_ship_hours_avg, spec_to_ship_samples, proof_latency_hours_avg,
human_minutes_total, human_minutes_by_type, spend_tokens_total, spend_cost_usd_total, spend_by_correlation,
cost_by_correlation, gate_pass, gate_fail, gate_pass_rate, open_emergency_debt, verdict_counts,
regression_health] and that each maps to the literal expected value embedded in the selftest. New keys are
asserted to be exactly the declared support keys, so neither a removed key nor an undeclared addition can
pass."

### F11. Three human decisions are left to the builder inside a criterion that claims they are declared

**Where.** AC4: "Rounding is declared and consistent, and no measure is presented to a precision the input
does not support." AC1: "reported as a TREND (per-incident values in recorded order plus the median and the
latest)".

**What is wrong.** The spec declares no rounding, no unit, no order key, and no median convention.
- Unit: the existing derivation reports hours to 2 decimal places (`avg` in `.veldo/metrics.py:191`). Nothing
  says the durations follow it.
- Median for even N: the mean of the two middles manufactures precision the inputs do not have, which AC4
  itself forbids. The spec must resolve its own contradiction.
- "Recorded order": the position of the `incident.closed` event in the stream, or `opened_at` order, or
  receipt id order? These tell different stories about whether things are improving, and AC1 asserts a
  selftest on it.

**What the spec must say instead.** "Durations are reported in HOURS, rounded to 2 decimal places, matching
the existing derivation. The median for an even population is the LOWER of the two central values (no
interpolation, so no invented precision). RECORDED ORDER is the position of the `incident.closed` event in
`events.jsonl`, ties broken by ascending incident id."

### F12. AC3 and the Notes mandate two incompatible test strategies for the same three paths

**Where.** Notes: "Keep every reader injected ... so the derivation is pure and the stand-downs are testable
without a filesystem." AC3: "Selftests prove all three paths over temporary trees."

**What is wrong.** Both are reasonable; the spec asks for both without saying which is authoritative, so
whichever the builder does, a reviewer reading the other sentence records an unmet criterion.

**What the spec must say instead.** "The guard matrix and every stand-down are proven with INJECTED FAKES
and no filesystem. Exactly ONE end-to-end selftest uses a temporary tree, and it is the wiring test of F6."
Delete "over temporary trees" from AC3.

### F13. The item is too large for one round, and its most expensive artifact is coupled to three other criteria

Counting the assertions the AC text mandates: roughly 8 in AC1, 6 in AC2, 4 in AC3, 5 in AC4, about 33 in
AC5 (25 matrix cells, 5 mutation-site uniqueness checks, the sha256 checks, 2 controls), and about 10 in
AC6. Call it 60 to 65 assertions in one item. The 25-cell matrix is defined over guards whose definitions
live in AC2, AC3 and AC4, so any change to any guard's definition invalidates up to 25 cells plus the
diagonality claim. That is the mechanism by which a single wording change costs a full rebuild rather than an
edit, and F1 through F4 are all changes to guard definitions.

**What the spec must say instead.** Split into three items, each with 3 to 4 criteria and its own small
matrix, sequenced so the definitional work lands first:
- **A**: the closed-incident definition, the receipt authentication join, the exclusion taxonomy, the two
  duration trends with their honest provenance statement, honest denominators, and teeth for those guards.
- **B**: recurrence rate (with the signature-grouping cross-check of F4) and the renamed attribution
  measure, with teeth.
- **C**: the per-area soft join, its per-area stand-downs, and teeth.
The engine-sync and adoption-safety criterion (AC6) rides on each of the three rather than being a fourth
concern in one of them.

---

## 3. What I tried to break and could not

- **The risk tier and the footprint tier.** I resolved the declared footprint against
  `.veldo/architecture.yaml` through `arch.area_for_path` and `arch.footprint_tier_floor`. Only
  `.veldo/metrics.py` and `.veldo/dashboard.py` resolve to a declared area (`metrics`);
  `.veldo/capabilities.yaml`, `engine/**`, `packs/**`, `scripts/selftest.py` and `specs/**` match no
  area's `includes`. So `footprint_areas` is `{metrics}`, `len < 2`, and the floor is `""`. The declared
  `standard` tier is correct and is not a lowered class. I also confirmed the enforcement core is genuinely
  untouched: nothing in the footprint reaches `action.py`, `action_executor.py`, `two_key.py`,
  `authorization.py`, `policy_check.py`, `verify.sh`, `veldo-guard.sh` or `policy.yaml`, and a derivation
  cannot open an execution path. The risk paragraph's reasoning holds.
- **The import-boundary analyzer.** I expected the couplings this item needs (metrics loading
  `reconciliation_store.py`, `incident.py`, `entropy.py`, `intent_corpus.py`) to trip
  `shape_gate.boundary_findings`. They do not: that analyzer only fires when the TARGET resolves to a
  declared area, and all four of those modules are outside every area's `includes`. `validate.py` is
  reachable over the allow-listed `metrics -> contracts` edge. So the gate will not refuse the couplings.
  I still note it as review-lane shape: nothing in the contract declares that the metrics area may depend on
  the reconciliation organ, and the spec should say which sibling modules the derivation loads and why.
- **Double counting.** I looked hard for a path to two `incident.closed` events for one incident, which
  would corrupt every measure. The content-addressed receipt id, the compare-and-swap in
  `ReconciliationStore.settle`, the unreadable-is-a-conflict rule and the single emitter close it, and
  `proof/WARP-1208/verdict.json` records that an independent reviewer reproduced eight corruption forms
  against it. WARP-1210 is right to treat the stream as duplicate-free.
- **Recurrence rate's derivability.** Of the four measures, this is the only one fully derivable from the
  inputs the spec declares: the `incident.closed` event's `extra` carries `recurrence_of` and
  `missing_specification`, and the receipt carries both plus the `failure_signature`. F4 is about the value
  being caller-dependent, not about the data being absent. Credit where due: the receipt design does make
  this measure honestly reachable, and the signature field makes the fix in F4 possible without touching
  WARP-1208.
- **The purity assertion.** `PYTHONHASHSEED` recomputation across two subprocesses is a real idiom in this
  codebase (`scripts/selftest.py:13092` does exactly that for WARP-1208), so AC1's purity assertion is
  buildable as written and would catch dict-ordering nondeterminism. No objection.
- **Adoption safety of the sync discipline.** The byte-identical engine sync across `engine` and
  every pack is mechanized (`engine_byte_identical` is marked mechanizable, and `check_template_sync.sh` /
  `check_pack_drift.py` exist), so AC6's sync clause is a real check rather than a claim.

---

## 4. The single change, if I were allowed only one

Add a **DATA PROVENANCE** table to the spec, above AC1, with one row per measure and these columns: the
exact field path it is computed from; the store that field lives in; the reader seam that reaches it; the
function or call site that constructs that reader in the SHIPPED path; and the receipt binding that
authenticates it, using the literal word `unauthenticated` where that is the truth.

Filling in that table cannot be done without deciding F1 (there is no timeline in events or receipts), F2
(what "closed" means, since the row needs a population), F4 (whose prior set produced `recurrence_of`), F6
(who constructs the reader), and most of F7 and F8 (a column that has to name the binding exposes the
conjunct that binds nothing and the states with no name). It converts five expensive discoveries into one
half-hour of writing before the first line of code, and it leaves behind exactly the artifact a reviewer
needs to check the item's central promise in one pass.
