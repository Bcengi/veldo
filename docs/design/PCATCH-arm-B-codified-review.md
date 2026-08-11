# PCATCH arm B - codified adversarial design review of WARP-1210

Item: `specs/WARP-1210-the-support-numbers.md` (status `ready`, risk `standard`, plan PLAN-0012 W10, depends_on WARP-1208)
Reviewer: independent adversarial design gate, pre-build. No `proof/WARP-1210` exists, by construction.
Tree reviewed: the supplied checkout only. Read: `docs/method.md` (partial), `docs/change-management.md` (index only), `VELDO.md`, `CLAUDE.md`, `plans/PLAN-0012`, `specs/WARP-1208`, `specs/WARP-1209`, `specs/WARP-1212`, `specs/index.md`, `proof/WARP-1208/verdict.json`, and the shipped organs `.veldo/metrics.py`, `.veldo/dashboard.py`, `.veldo/entropy.py`, `.veldo/incident.py`, `.veldo/incident_reconcile.py`, `.veldo/reconciliation_store.py`, `.veldo/events.py`, `.veldo/arch.py`, `.veldo/architecture.yaml`, `.veldo/shape_gate.py`, `.veldo/policy.yaml`, `.veldo/budget.py`, `scripts/selftest.py` (structure).

---

## 1. RULING

`do_not_build_yet`

---

## 2. THE SEVEN DIMENSIONS

### 1. PROMISE - FAIL

The spec makes two promises and only one of them is checkable.

The checkable one is real and I tried hard to break it. AC2 states it plainly: "Every measure counts ONLY an incident whose closure is backed by a reconciliation receipt that resolves to that incident id", and the Intent closes with "Every number here is backed by a reconciliation receipt or it is excluded and named." That is a universal with a decidable predicate, it names its own failure mode, and its threat model is not invented: `.veldo/events.py` ships a CLI (`emit incident.closed --field ...`) that lets any writer append a close event with arbitrary fields, and `.veldo/validate.py` now recognizes the type (WARP-1208 AC4). I could not find a reading of AC2 under which it is vacuous. That half of the promise is stated in checkable form.

The other promise is the one the spec's own `risk` field calls load-bearing: "The one property that makes this item worth reviewing carefully is HONESTY OF NUMBERS ... a derived measure that silently counts an unbacked event, or invents a denominator, is a lie a human will act on." That promise is carried entirely by adjectives - "honest denominators", "no invented precision", "never fakes itself", "standing down honestly" - with no stated universal over which it holds and no stated method for showing it holds.

The failure is sharpest at the item's flagship measure. AC1 defines the diagnosability score as "the share of closed incidents resolved FROM ARTIFACTS ALONE, defined mechanically as those whose receipt records a diagnosis validation and whose incident resolves to a governing spec or area in the corpus". Read against the shipped code, the first conjunct is a tautology and the second is a field-presence check:

- `.veldo/incident_reconcile.py:694` `reconciliation_record()` unconditionally writes a `diagnosis_validation` block into every receipt, and `_validation_refusal()` (line 340) refuses settlement outright when the validation is absent, machine-authored, unbound, or digest-mismatched. Therefore **every receipt that exists records a diagnosis validation**. The conjunct cannot be false anywhere in the authenticated domain.
- `validation_binds_remedy()` (line 331) returns `True` trivially when there is no remedy, and WARP-1208 AC5 ships the control "an incident with no remedy at all settles with an honest none execution block rather than refusing". `.veldo/incident.py` defines no `diagnosis` field on `veldo.incident/v1` (stated at `incident_reconcile.py:306`). So an incident with **no remedy, no proposal, and no cited evidence at all** produces a receipt whose `diagnosis_validation` is present, and therefore scores as "resolved from artifacts alone" provided only that the optional `affected_spec` or `affected_area` string was filled in.
- Those two fields are optional and unvalidated against anything. `.veldo/incident.py:227` treats `affected_spec` and `affected_area` as soft join fields "only required to be non-empty when present ... never faked and never resolved against a contract in W1".

So the number the spec headlines as the share of incidents diagnosed from artifacts is mechanically the share of incidents whose author typed an optional string, and it is highest for the incidents with the least evidence behind them. AC5 labels the proxy review-lane in one sentence ("whether an incident was TRULY resolved from artifacts alone is a human judgment, and the mechanical definition in AC1 is a declared proxy"), which is honest as far as it goes, but it does not disclose that one conjunct is unfalsifiable and the other measures form-filling rather than diagnosis.

**What the spec must say instead.** State one promise, as a universal with a decidable predicate, at the top: "for every element of the declared input set, the output carries either a value derived from that element or exactly one named reason it carries none, and no other outcome is possible." Then, for the diagnosability score specifically, either (a) define the proxy over something that can be false - for example, the receipt's `what_it_proved` naming a real execution receipt, or the remedy's cited evidence resolving, both of which vary across real inputs - and state the false-positive and false-negative direction, or (b) drop the measure from this item and record it as an unbuilt intent. A measure whose definition contains a term that is true by construction should not ship as a number a human acts on.

### 2. DOMAIN - FAIL

The set over which the promise holds is never declared, and the spec's own two attempts at declaring it disagree with each other and with the code.

AC1 says the measures are "a PURE function over the parsed events and receipts". The Notes say "Keep every reader injected (events, receipts, the contract, the per-area cost data)" - four inputs. Both lists omit the input the criteria actually consume most:

- AC1 requires `opened_at`, `diagnosed_at` and `restored_at` "taken from the incident record's timeline".
- AC3 requires "the incident record's `affected_area` when it declares one, else ... the `affected_spec` resolved to that spec's placement".

The incident **record** set is therefore load-bearing for three of the four measures and the whole area join, and it appears in neither input list. It is also a real, separate store: `.veldo/incident.py:130` `default_incidents_dir()` returns `.veldo/incidents`, and records are parsed by an injected parser through `resolve_incident(incident_id, incidents_dir, parse, loader)`. AC3's "affected_spec resolved to that spec's placement" adds a fifth set, the spec corpus, since `placement` is spec front matter that must be parsed (`validate.parse_yamlish`, or `.veldo/intent_corpus.py`). So the item consumes five sets and declares two.

Worse, the per-measure domains are not the same set and the spec never says so:

- recurrence rate: closed, receipt-backed incidents.
- diagnosability score: closed, receipt-backed incidents whose record resolves.
- time-to-diagnosis: those with a parseable `opened_at` and `diagnosed_at`.
- time-to-restore: those with a parseable `opened_at` **and** `restored_at` - and `restored_at` is optional even for a closed incident. `.veldo/incident.py:242` requires `diagnosed_at` for status `diagnosed` or `closed`; `restored_at` is only checked for non-negativity when present (line 246). A closed, fully authenticated incident with no `restored_at` is legal, and the spec has nowhere to put it.

AC1 also leans on an invariant it does not own: "both taken from the incident record's timeline that WARP-1201 already validates as non-negative". WARP-1201's validation is lexicographic over strings (`_iso_or_none` at `.veldo/incident.py:190` returns the raw string, and the comparison is `restored < opened`), it does not require ISO-8601 parseability, and it runs only when the contract validator is run over the incidents directory - which is a different code path from the derivation. `.veldo/metrics.py:38` `parse_at()` needs `datetime.fromisoformat` to succeed and returns `None` when it does not. So the derivation's input can be a record WARP-1201 accepts and `parse_at` rejects, and the spec assumes that case away.

**What the spec must say instead.** Declare the input set explicitly, by name and by reader, one line each: the event stream, the receipt store, the incident record store, the architecture contract, the per-area cost series, the spec corpus. Then declare the domain of each measure as a stated subset of that set, and state, per measure, the exact predicate that puts an element in the denominator. Prefer the domain the item can own: the union of "close events, receipts, incident records" is enumerable by construction from three directories, and every element of it either produces a value or a named reason.

### 3. ENUMERATION - FAIL

The spec declares its exclusion vocabulary CLOSED and asserts its guard list is complete. Both are false against the spec's own text and the shipped code, and no method of proving completeness is stated.

The observability block declares five names as "a closed, named set (UNBACKED_EVENT, UNRESOLVED_RECEIPT, EMPTY_DENOMINATOR, NO_AREA_COST_DATA, NO_ARCHITECTURE_CONTRACT)" and promises that "Every excluded or unresolvable input is reported by NAME in the rendered output ... rather than dropped silently". Here are input classes the criteria consume for which the closed set has no name, so each one is dropped silently or fabricated:

1. A closed, receipt-backed incident with **no `restored_at`** (legal per `.veldo/incident.py`). Excluded from the restore trend with no name.
2. A timeline timestamp that is present and non-empty but **not ISO-parseable**. Legal per WARP-1201, fatal to `parse_at`. No name.
3. A receipt-backed incident whose **incident record is missing or unreadable**. AC2 names `UNRESOLVED_RECEIPT` for "a receipt whose incident cannot be resolved", which may be this case or may be a receipt with an empty `incident` field; the spec does not say, and the two need different names because one is a missing record and the other is a malformed receipt.
4. An `affected_area` naming an **area the contract does not declare**. W1 explicitly never resolves it against a contract, and `.veldo/architecture.yaml` declares exactly ten area ids. AC3 says "a cost figure is never carried for an area the contract does not declare" but gives no name for the incident that named it, so a typo removes an incident from the map invisibly.
5. An `affected_spec` that **does not resolve**, or resolves to a spec with **no placement**. No name.
6. A **duplicate `incident.closed`** for one incident. WARP-1208's own Notes say "a duplicated incident.closed silently corrupts every W10 measure", and WARP-1208 only guarantees no duplicate *from the reconcile path*; AC2's whole threat model is a hand-appended event. Two close events for one incident, both naming a real receipt, inflate the denominators and add a phantom point to both trends. No guard, no name.

The completeness assertion is also refutable from the spec alone. AC5 says "Every guard in this item - the unbacked-event exclusion, the unresolved-receipt exclusion, the zero-denominator stand-down, the no-cost-data stand-down, and the no-contract stand-down". But AC1 declares a guard ("reported as a TREND ... never a single average that hides a regression"), AC3 declares two more ("an unattributable incident is never assigned to a default area", "a cost figure is never carried for an area the contract does not declare"), and AC4 declares two more ("A trend with a single data point is reported as a single observation and not as a trend direction", "Every share is reported with its numerator and denominator beside it"). Five declared behaviours with numeric consequences sit outside the five-guard matrix that claims to cover "every guard in this item".

**What the spec must say instead.** Two changes, both mechanical. First, make the taxonomy the module's own exported constant and require the matrix to be **derived from it**: "the teeth matrix enumerates its mutation targets from `EXCLUSIONS` and asserts set equality with the guards under test, so a guard added without a tooth fails the gate." That converts completeness from a list someone wrote into an assertion that fails when the list drifts. Second, prove input coverage the same way: require the derivation to be **total** over the declared union, and assert `len(rows) == len(close_events) + len(orphan_receipts) + len(unclosed_records_in_scope)` with every row carrying either a value or exactly one taxonomy member. Then a missing name is a failing test, not a silent drop.

### 4. OBSERVATION - FAIL

Four separate places where the evidence observes a stand-in for the promised thing, none of them justified.

**(a) The promise is about what a human reads; the evidence reads the model.** The observability block promises exclusions are named "in the rendered output and in the returned model". Every selftest AC1 through AC5 describes is an assertion over values ("asserts each measure", "names every exclusion", "the numerator and denominator accompany every share"). The spec never says any assertion runs against `render_text()` or `render_html()`. This is not pedantry here: `.veldo/dashboard.py` has **two** renderers, and the HTML one is a fixed list of `_card()` calls (lines 153 to 168 plus 187 to 201). Nothing in the spec says the support measures appear in the HTML path at all, and nothing says what an exclusion looks like as a card. A number can be present in the model and absent from the page a human opens, and the spec as written passes.

**(b) The one assertion aimed at reality observes an empty repository.** AC3 promises "A further selftest asserts this repository's REAL state honestly, whatever it is". I measured this repository's real state: `grep -c incident.closed .veldo/events.jsonl` returns **0**, there is no `.veldo/incidents`, no `.veldo/remedies`, and no `.veldo/reconciliations`. So that assertion will assert the empty state, which is already AC5's control. Every one of the four measures will be observed **only** over fixtures the item itself seeds. That is consistent with NG1 and with how WARP-1208 was proven, so I am not calling it a defect on its own - but it means the spec's stand-in is total, and the spec should say so rather than imply a real-state check adds coverage.

**(c) AC6's central assertion has nothing to observe against.** "a selftest asserts every measure already computed by `.veldo/metrics.py` is byte-identical before and after this change over the same event stream". After the change there is no "before" in the tree. Either a golden artifact is committed (and the spec must say where, and that it was generated at the parent commit) or the assertion degrades to "the pre-existing keys are still present", which is a much weaker claim wearing the words "byte-identical". `compute()` returns a dict; the only place bytes exist is `python3 .veldo/metrics.py --json`, and that output **will** change bytes the moment a key is added. The precedent in this repo (`scripts/selftest.py:8494`, WARP-1108 AC5) uses "byte-identical" for **file** sync across pack locations, never for computed values.

**(d) AC5 and AC6 make contradictory demands on the observed render.** AC6: "a repository with no incident events renders exactly as it did before (adoption safe)". AC5: "a repository with no incidents at all renders the support section as an honest empty state rather than an error or a row of zeros". A render that gains an empty-state support section is not the render it was before. Both cannot be observed as true. And because this repository has zero incident events, the dogfood run is exactly the contradictory case, so this is a build-stopper rather than a hypothetical.

**What the spec must say instead.** Name the observation surface per criterion: "asserted against `render_text()` output and against `render_html()` output, and against the returned model" for anything the observability block promises a reader can see. Resolve (d) explicitly with one sentence choosing a side ("the support section renders always, so the no-incident render gains exactly N lines, and the assertion is that the pre-existing lines are unchanged"). For (c), name the baseline artifact and its provenance.

### 5. REFUTATION - FAIL

For each of the item's central claims, here is the observation that would prove it false, and whether the spec arranges for anyone to make it.

| Claim | Refuting observation | Arranged? |
|---|---|---|
| Numbers are authenticated (AC2) | A forged `incident.closed` is counted | YES - AC2 explicitly seeds one and asserts it is excluded while genuine ones count. This is the spec's best criterion. |
| Numbers are authenticated (AC2) | Two `incident.closed` events for one incident, both naming a real receipt, double-count | NO - no guard, no name, no fixture, and WARP-1208's Notes already flagged the exact corruption |
| Diagnosability score measures diagnosis from artifacts (AC1) | An incident with no remedy and no evidence scores as diagnosable | NO - and it cannot be arranged, because the conjunct is true by construction |
| Every exclusion is named, never silently dropped (observability) | A closed incident with no `restored_at`, or an unparseable timestamp, vanishes from a trend | NO - no taxonomy member exists to fire |
| The join never fakes itself (AC3) | An incident naming an area the contract does not declare disappears from the map | NO |
| Every guard is non-vacuous (AC5) | A guard exists with no tooth | Partially - the matrix is asserted diagonal and each target asserted to appear exactly once, which is a genuinely strong mechanism borrowed from WARP-1208's round-2 verdict. But the guard **list** is hand-written, and I refuted its completeness above from AC1, AC3 and AC4 alone. A test that enumerates its own targets from a list that is wrong cannot detect that the list is wrong. |
| No existing number changed (AC6) | A pre-existing measure differs | NO - no baseline to compare against |

Two criteria cannot fail as written: AC1's diagnosability definition (one conjunct universally true) and AC6's byte-identity (no observable "before"). Under this gate's standard, those are ceremony.

**What the spec must say instead.** For each criterion, one line naming the observation that would refute it and the fixture that looks for it. The three missing fixtures that matter most: a duplicate close event; a closed incident missing `restored_at`; an `affected_area` outside the contract.

### 6. UNASKED DECISIONS - FAIL

Every one of these stops the build when it surfaces, and none is raised in the spec. Listed together, which is the point.

1. **Which direction does the authentication join run?** Event to receipt (`incident.closed` carries `reconciliation`, the receipt id - see `_closed_event()` at `incident_reconcile.py:727`), or receipt to event (enumerate receipts, index by their `incident` field)? These are different security properties: the first trusts a field on the forgeable event, the second does not. AC2's `UNRESOLVED_RECEIPT` case requires the second, because an orphan receipt is undetectable without enumerating receipts.
2. **Where does receipt enumeration come from?** This is the hard one. `.veldo/reconciliation_store.py` exposes **only** `get(rec_id)` (line 180); the backends implement `_get`, `_append`, `_read_draft`, `_write_draft` and nothing else. There is no list, iterate, or find-by-incident primitive, and the receipt id is content-addressed over incident id plus failure signature plus remedy id plus execution receipt digest (`reconciliation_id()`, line 673), so it **cannot be computed from an incident id alone**. So either (a) `reconciliation_store.py` gains an enumeration primitive - but that file is **not in the declared footprint**, and `.veldo/shape_gate.py:357` `footprint_findings()` refuses by name when the diff touches a path outside the footprint of the one footprinted spec, so the gate stops the build; or (b) `metrics.py` re-implements knowledge of the `.veldo/reconciliations/<id>.json` layout, which forks a store's layout into a second owner and violates the pattern this repo enforces everywhere ("loaded by path from the module that already owns it", `reuse_one_parser` in `architecture.yaml:69`, and WARP-1208's own "no second machine-actor list, event vocabulary, or proposal-digest implementation"). Neither branch is available without a decision, and one of them changes the footprint.
3. **Is the incident record store an input, and through which reader and parser?** `incident.default_incidents_dir()` plus `validate.parse_yamlish`, presumably, but nothing says so, and nothing says what happens when a receipt-backed incident has no record.
4. **Units and rounding.** Are the trends in hours (the sibling `spec_to_ship_hours_avg` convention), minutes, or seconds? To how many decimals? AC4 says "Rounding is declared and consistent" - a promise to declare, not a declaration.
5. **The median convention** on an even-length series: lower, upper, or the mean of the two middles.
6. **What "recorded order" means.** AC1 asserts "the trend preserves recorded order" and reports "the latest". Receipts are deliberately clock-free (`reconciliation_record()` docstring: "Pure and clock-free"), so order must come from the event stream's file order, the event `at` field, or the incident's `opened_at`. Those give different sequences and a different "latest".
7. **Does the support derivation live inside `compute()`'s return dict, or as its own function?** `compute()` already has four call sites that care only about spend and cost: `.veldo/dashboard.py:45`, `.veldo/entropy.py:97`, `.veldo/budget.py:161`, and `.veldo/governor.py` via a path load. Folding four incident measures plus five readers into `compute()` makes every one of those callers pay for a derivation it does not use, and it is what breaks AC6's byte-identity of the `--json` output.
8. **Default wiring at the CLI and dashboard edge.** AC1 forbids "filesystem beyond the injected readers", but `python3 .veldo/metrics.py` and `python3 .veldo/dashboard.py` must get readers from somewhere or they show the empty state forever. Who wires the defaults, and do the three existing callers pass readers or not?
9. **Text renderer, HTML renderer, or both**, and what an exclusion looks like as an HTML card.
10. **The AC5-versus-AC6 contradiction** on the no-incident render, above. Someone must choose.
11. **Which area source for a spec-derived attribution:** the spec's `placement` field (what AC3 says) or `arch.footprint_areas(fm, contract)` (what `.veldo/entropy.py:192` actually uses to key the cost series being joined). If they differ, the two columns of the "ONE map" are keyed differently.
12. **Is time-to-restore in scope at all**, given `restored_at` is optional, and if so what its named stand-down is.
13. **Which copy of `recurrence_of` is authoritative** - the receipt (AC1 says receipt) or the event (which also carries it, `_closed_event()`). Worth one sentence, since the whole item is about not trusting the event.

### 7. SIZE - FAIL

This is at least four items. Counting distinct checkable claims in the acceptance criteria: AC1 carries 8 (four measure definitions, the trend shape, purity, cross-process determinism, order preservation), AC2 carries 5, AC3 carries 7, AC4 carries 5, AC5 carries 6, AC6 carries 8 or 9 (no-change byte-identity, adoption-safe render, no process, no live system, engine sync across `engine` and six packs, the capabilities entry, gate green, RULE #1, three dogfood properties). That is **roughly 39 distinct checkable claims across 6 criteria**, in an item whose own risk field describes it as "a single declared area".

The evidence in this tree says that shape does not survive. WARP-1208 is the nearest sibling and the closest in size; `proof/WARP-1208/verdict.json` records a first-round FAIL with four blocking defects, a second reviewer rebuilding a 12 by 12 matrix, seven carried notes, two worsened round-one notes, three manifest overstatements corrected in review, and a follow-up hardening spec. It also records note 7: "the criterion's own text still says four conditions and five refusals where the shipped gate now has five and six, because the spec was edited for footprint only" - a spec that lost track of its own claim count under revision. WARP-1210 as written has more claims than WARP-1208 and a weaker domain.

**Where the split lines fall.** The seam is the derivation pipeline, and it is clean:

- **Item A - the authenticated incident index.** The one load-bearing concern: enumerate close events, receipts and incident records; join them; emit one row per element of that union carrying either a resolved incident or exactly one named reason; report authenticated-versus-excluded counts. Includes the receipt-store enumeration primitive and its footprint. No measures at all. Roughly 4 criteria. This is where AC2's teeth belong, and it is provable by construction.
- **Item B - the four measures over the index.** Definitions, trend shape, honest denominators, numerator and denominator beside every share, units and rounding, purity and determinism. Roughly 4 criteria. Cannot silently lie, because it consumes only item A's rows.
- **Item C - incidents-per-area, the C7 soft join.** Area attribution, the join with `entropy.py`'s cost series, the two stand-downs, the never-invent rules. Roughly 3 criteria. Genuinely independent of A and B: it shares no input with the authentication spine.
- **Item D - the render and the engine sync.** Text and HTML surfaces, exclusions visible to a reader, capabilities entry, byte-identical sync across `engine` and the packs, the no-regression baseline. Roughly 3 criteria.

`specs/WARP-1212-two-key-freshness-fail-closed.md` shows a spec in this corpus carrying no `plan`/`work` fields, so adding sibling items to W10 is procedurally available without pretending one spec is one work item.

---

## 3. FINDINGS RANKED BY WHAT THEY WOULD COST IF UNFIXED

1. **The receipt store cannot be enumerated, and the file that would fix it is outside the footprint.** (Unasked decision 2.) Cost: the build stops at the first line of AC2 with a choice between a gate refusal (`shape_gate.footprint_findings`) and an architecture violation (a second owner of the receipt store layout). This is not a review note, it is a blocker discovered in the first hour of building, and it is the single cheapest thing to fix now.
2. **AC5 and AC6 contradict each other on the no-incident render, and this repository is the no-incident case.** Cost: the builder cannot satisfy both, picks one, and a reviewer refutes the other. Guaranteed round-two.
3. **The diagnosability score's mechanical definition contains a conjunct that is true by construction, and the other conjunct measures an optional field.** Cost: a number shipped to a human dashboard that is highest for the least-evidenced incidents. This is the exact failure mode the item's own risk field names ("a lie a human will act on"), and unlike the others it survives review, because no test can fail.
4. **The exclusion taxonomy is declared closed and is provably insufficient** - six unnamed input classes, including a legal closed incident with no `restored_at` and a duplicate close event that WARP-1208's Notes already flagged as corrupting every W10 measure. Cost: silent drops in a surface whose whole promise is that nothing is dropped silently, plus a taxonomy change mid-build, which is a change to a "closed set" and therefore to the observability block and every fixture.
5. **AC5's "every guard" list omits five guards its sibling criteria declare.** Cost: the matrix ships diagonal and complete-looking while a third of the item's numeric behaviour has no tooth. This is the cheapest fix on the list (derive the list from the module constant) and the highest leverage per character.
6. **The domain is undeclared and spans five input sets, two of which the spec names.** Cost: this is the meta-cause of findings 3, 4 and 7. Any counterexample can be, and will be, ruled out of scope after the fact.
7. **AC6's "byte-identical before and after" has no baseline artifact.** Cost: either the assertion is quietly weakened during the build (the failure mode `docs/method.md:478` and `policy.yaml`'s `gate_is_the_only_done` both forbid) or a golden file is invented mid-build without a stated provenance.
8. **Evidence observes the returned model where the promise is about the rendered output, and the HTML renderer is never mentioned.** Cost: exclusions absent from the page a human actually opens, with a green gate.
9. **Units, rounding, median convention, and the meaning of "recorded order" are undeclared.** Cost: four small stoppages, each cheap alone, each requiring the owner.
10. **`compute()` accumulating five readers and four measures for four callers that want spend.** Cost: not a defect today, a cohesion problem the reviewer will name under shape-fit and the reason AC6 gets hard.

---

## 4. THE SINGLE CHANGE

If I could make only one change: **declare the domain as one set the item owns, and make the derivation total over it.**

Concretely, replace AC1's purity sentence and AC2's exclusion sentence with a single stated promise:

> The derivation's input is the union of (a) every `incident.closed` event in the stream, (b) every receipt in the reconciliation store, and (c) every incident record in the incident store. The derivation emits exactly one row per element of that union. Every row carries either a resolved, authenticated incident with its derived values, or exactly one reason drawn from the module's exported `EXCLUSIONS` constant. A selftest asserts the row count equals the size of the union, that every reason is a member of `EXCLUSIONS`, and that the teeth matrix enumerates its mutation targets from `EXCLUSIONS` itself, so a guard or a reason added without a tooth fails the gate.

That one change fixes five of the top six findings at once. It declares the domain (dimension 2). It makes enumeration provable by construction rather than by a list someone wrote (dimension 3), and every currently unnamed input class - the missing `restored_at`, the unparseable timestamp, the missing record, the undeclared area, the duplicate close - becomes a failing assertion instead of a silent drop. It gives the promise a decidable form (dimension 1). It gives every criterion a refuting observation (dimension 5). And it forces decision 2 to the surface before a line is written, because you cannot enumerate the receipt store without deciding how.

It does not fix the diagnosability score, which needs its own decision: define the proxy over something that can be false, or do not ship the number.
