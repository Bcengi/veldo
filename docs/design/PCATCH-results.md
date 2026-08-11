# P(catch) EXPERIMENT - RESULTS

Scored against `PCATCH-experiment-preregistration.md`, written before either arm ran. Criteria were not
adjusted after seeing output. **ARM A PENDING at the time of writing; this file is updated when it lands.**

## Cost: use ACTUAL durations, not self-reports

The agents' own wall-clock estimates are unreliable and always high, so every cost figure here is the
harness-measured duration.

| review | self-reported | ACTUAL | note |
|---|---|---|---|
| design review of INVERSION v1 | 18 min | **17.4 min** | accurate |
| ARM B (codified brief) | "roughly 25 min" | **9.8 min** | over-estimated itself by 2.5x |
| code reviews of WARP-1210 | - | 42.6 min mean, n=11 | measured from commit to verdict mtime |

**A design review costs 10 to 18 minutes measured, against a 42.6 minute mean for code review of the same
item.** So version 1's asserted 20 minutes was, if anything, pessimistic. This does not rescue version 1's
recommendation, because what refuted it was the 81.8% trigger rate, not the per-review cost.

## ARM B - codified four-component brief (hindsight-informed, expected to catch)

**RULING: `do_not_build_yet`. All seven dimensions FAIL.**

Scored against pre-registration:

| pre-registered defect | caught? | how it was named |
|---|---|---|
| 1. domain never declared | **YES** | "Domain undeclared, spanning five input sets where the spec names two; the incident record store is load-bearing for three of four measures and appears in neither input list" |
| 2. evidence observes a proxy | **YES** | "Evidence observes the model, not the render, and the HTML renderer is never mentioned" |
| 3. decisions not raised together | **YES** | 13 unasked decisions listed |

**Verdict: FULL CATCH on all three.** Per the pre-registration this proves little ON ITS OWN, because the
brief names domain, enumeration and observation explicitly and that brief was written from this failure.

**BUT ARM B ALSO PRODUCED FINDINGS THE BRIEF DID NOT HINT AT, AND THAT IS NOT HINDSIGHT.** Four of them, and
the first is verified against what the build actually did.

### VERIFIED HIT: the receipt store cannot be enumerated, and the fix is outside the footprint

Arm B, seeing only the pre-build spec: `.veldo/reconciliation_store.py` exposes only `get(rec_id)`; the receipt
id is content-addressed over incident id plus failure signature plus remedy id plus execution digest, so it
cannot be computed from an incident id. AC2's `UNRESOLVED_RECEIPT` requires ENUMERATING the store. That file is
not in the declared footprint, and `shape_gate.footprint_findings()` refuses an out-of-footprint diff by name.
**Predicted consequence: "build stops in hour one, with a choice between a gate refusal and FORKING STORE
LAYOUT INTO A SECOND OWNER."**

What the build actually did, from the shipped code at `.veldo/metrics_readers.py:185-195`:

> "The store's LOCATION is a literal here, **honestly**: FilesystemReconciliationStore builds
> `.veldo/reconciliations/<id>.json` inline and **exposes no constant to read**, so this reader restates the
> path and a selftest BINDS the two by settling a receipt through the SHIPPED store and reading it back
> through here."

**It took the second horn of exactly the dilemma arm B predicted.** The store's layout is now restated in a
second module; `reconciliation_store.py` was never added to the footprint and was never touched during the
item (verified: zero commits against it across the whole build). The builders knew, wrote "honestly" into the
docstring, and mitigated with a binding selftest.

This is design debt taken by DEFAULT under build pressure, not by DECISION. A design review would have
surfaced it as a choice before hour one: add an enumeration API to the store and put it in the footprint, or
accept a second owner of the path with a binding test. The second is defensible; arriving at it by discovery
is what costs.

### Three further findings not traceable to the brief

- **AC5 and AC6 directly contradict each other** on whether a repository with no incidents changes its
  render, and this repository has zero incident events, so the dogfood run IS the contradictory case.
- **The diagnosability score cannot fail.** "Whose receipt records a diagnosis validation" is true by
  construction, because `reconciliation_record()` always writes the block and settlement refuses without a
  valid one. The score therefore reduces to "was an optional string filled in," and an incident with no
  remedy, no proposal and no cited evidence scores as diagnosable. That is the vacuous-guard pattern this
  item has now produced four times.
- **The 5-name exclusion taxonomy is provably insufficient**, with six unnamed input classes including a
  legal closed incident with no `restored_at` (optional per WARP-1201) and a duplicate `incident.closed` that
  WARP-1208's own Notes already flagged as corrupting every measure.

### SIZE, which is the F1 finding arriving unprompted

Arm B counted **about 39 distinct checkable claims and ruled the item splits into 4**. The standing house rule
is one concern per item and 3 to 4 acceptance criteria. **An independent reviewer, given only the spec,
independently reached the same conclusion as the post-mortem: this was four items wearing one item's clothes.**
That is the strongest available evidence for F1 (shrink the item) and it did not come from the brief.

## Follow-up raised, NOT added to WARP-1210

The receipt-store path duplication is real design debt but it is mitigated by a binding selftest, it is
pre-existing in the shipped design, and it is a DIFFERENT CONCERN from what round 13 is fixing. Adding it now
would be the item-size disease in action at round 13. **It gets its own ticket:** either give
`reconciliation_store` an enumeration API and a path constant, or declare the second owner deliberately with
the binding test as its stated mitigation.

## ARM A - generic brief, no dimensions named (the honest P(catch))

**RULING: `do_not_build_yet`, 13 findings.** The brief named no dimensions, no domain, no enumeration, no
observation, and gave no hint that this spec had failed or how.

| pre-registered defect | caught? | how it was named, unprompted |
|---|---|---|
| 1. domain never declared | **YES** | F1: the two headline measures cannot come from the declared inputs at all; they need `.veldo/incidents/`, "a FIFTH STORE the spec never declares, never gives a reader, and never authenticates" |
| 2. evidence observes a proxy | **YES** | F6: "nobody is named as constructor of the real readers, so the shipped default is a permanent stand-down every selftest passes... a green 25-cell matrix is compatible with a dashboard that reports zero authenticated incidents forever" |
| 3. decisions not raised together | **YES** | F11: three human decisions undeclared inside a criterion that claims they are declared (unit and rounding, median convention for even N, the meaning of "recorded order") |
| SIZE (the F1 option) | **YES** | F13: 60 to 65 assertions, most expensive artifact coupled to three other criteria, recommends a three-way split |

**FULL CATCH, generically, with no hindsight. P(catch) = 1 of 1 on the honest arm.**

F6 deserves singling out because it is sharper than the defect I recorded in the post-mortem. I wrote that the
tests observed a reader instead of the four rendered surfaces. Arm A found the deeper version: nothing in the
spec requires the REAL readers to be constructed at all, so every criterion is satisfiable with fakes while
the shipped dashboard reports zero forever, and the gate stays green. That is the proxy defect and the
vacuous-guard defect in one, derived from the spec alone.

## A MINUS B, which was the point of running two arms

**Both arms caught all three defects. So the BRIEF IS A CONVENIENCE, NOT THE MECHANISM.** Design review as an
ACT catches this class without hindsight, which means:

- The mechanism is NOT capped by the failures already harvested into its brief. That was the risk that made
  option D's judgement-first sequencing important, and it is the one finding here that makes the case for a
  judgement layer stronger rather than weaker.
- A codified checklist is not required for the catch, so a mechanical design gate is optional polish rather
  than the substance. WARP-0721 built the polish first, which is why it was refuted.
- The two arms found DIFFERENT things beyond the shared three. B found the receipt-store enumeration dilemma
  (verified hit) and the AC5/AC6 contradiction; A found the fifth undeclared store, the fake-readers hole and
  a status-filtered population that is empty forever. Two independent design reviews of one spec do not
  converge, which argues for the value of a second pair of eyes and against expecting one review to be
  complete.

## HONESTY: arm A produced at least one FALSE POSITIVE, and it belongs in the arithmetic

Arm A's F5 claimed AC1 plus AC3 force "an unbounded mutual recursion" between `entropy.py` and `metrics.py`
because `_load` does not register in `sys.modules`. I checked it. **The premise is right and the conclusion is
wrong:** `_load` genuinely never registers in `sys.modules` (`spec_from_file_location`, `module_from_spec`,
`exec_module`, no assignment), and `entropy.py:82` does load `metrics.py` at module scope, but there is no
cycle - the direction is one way, `dashboard.py` loads `entropy.py` loads `metrics.py`, and `metrics.py` never
loads `entropy.py` (its references at :123, :165, :260 and :336 describe CONSUMERS, not loads).

I also nearly overclaimed this one myself. My first reading was that arm A had predicted round 8's recursion
defect from the spec. **It did not.** Round 8's defect was unbounded DIRECTORY-DEPTH recursion in
`metrics_skip_rule.py:116` failing at about 500 nested directories with an uncaught RecursionError. Same
defect CLASS, different instance. Arm A named the class pre-build; it did not name the instance.

**So a design review's output must itself be ruled, not adopted.** That cost is real and belongs beside the
review cost. It is also the same discipline the code reviewers apply, so it is not a new burden.

## What this does to the arithmetic

Measured design-review cost across three real runs: 17.4, 9.8 and 12.4 minutes, **mean 13.2 min** - against a
42.6 minute mean for code review of the same item. Recomputing the trigger table at the MEASURED cost with
P(catch) at 1 of 1:

| trigger | fires on | policy cost at 13.2 min | catches (of 5 troubled) |
|---|---|---|---|
| universal (option A) | 137 of 137 | **30.1h** | 5 |
| AC >= 6 | 34 of 137 | 7.5h | 3 |
| footprint >= 15 | 9 of 30 | 2.0h | 3 |
| **F3 second failed review** | **1 of 133** | **0.22h** | 1 (the one that mattered) |

**This reverses version 2's rejection of the universal option, and I am stating the reversal rather than
burying it.** At 13.2 minutes a universal design review costs 30.1h against the 33.2h overrun of the single
catastrophe in this history - roughly break-even on the catastrophe term ALONE, and positive once the ordinary
defects both arms found on an ordinary spec are counted.

**But the honest caveats, which keep F3 first:**

1. Break-even on the catastrophe term requires another WARP-1210 in the next 137 items. Base rate is 1 in 145.
2. The ordinary-defect saving cannot be quantified from n=2, and one of arm A's findings was a false positive,
   so the saving is bounded below, not measured.
3. **F3 costs 0.22h and catches the catastrophe class BY CONSTRUCTION**, at 1/137th of the universal cost. No
   arithmetic makes universal review a better first move than F3.

So the package is unchanged in ORDER and changed in AMBITION: ship F3 and F1 first because they are nearly
free, and universal-or-thresholded design review is now genuinely defensible as a second step rather than
refuted. That is a material change from version 2's draft and must go through the second design review before
it reaches Dmitry.
