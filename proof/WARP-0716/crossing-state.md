# WARP-0716 crossing-state survey: can the unit suite be split?

THIS DOCUMENT IS GENERATED, not transcribed. `python3 scripts/suite_survey.py --emit-report` emits
it whole from one live run of the survey over `scripts/selftest.py`, and the gate's
CHECK_generated stage regenerates it and DIFFS: regeneration must be a no-op, exactly as it must
for `specs/index.md`. A stale report cannot reach a green gate: the stage that finds it stale has
already rewritten it and reddened the run with the diff, so the only version that passes is the
emitter's output.

ONE CAVEAT THAT OUTRANKS EVERY FIGURE BELOW: THE SUBJECT MOVED. WARP-0712 has since cut the
monolith this survey was built to measure into scripts/suites/, leaving at the measured path a
dispatcher that holds no assertion of its own, and the target stays pointed there because this
tool's own fixture tree pins that path (recorded as a limit in proof/WARP-0712/manifest.json). So
the figures and the verdict below describe that dispatcher and, through it, the pre-split monolith
this survey was written for; they are not a statement about today's assertion suite, and the
question of whether that suite can be split has already been answered by splitting it. The
measurement the decomposition actually used is the order-dependence survey in proof/WARP-0712/,
which was driven over the monolith region by region.

AND GENERATED DOES NOT MEAN NOTHING WAS TYPED. The tables are derived; the paragraphs between them
are hand-typed constants in the emitter, and one of them USED TO ASSERT A MEASUREMENT: it named
the assertion helper's classification and its counters' classification in prose, an independent
review DROVE one conditional rebinding into the measured file, and this document shipped at a
green gate saying SHARED_FIXTURE in a paragraph while its own tables said UNDETERMINED.
Regeneration cannot see that, and the reason is worth stating exactly: regeneration proves the
FILE matches the EMITTER, and says nothing about whether the EMITTER matches the MEASUREMENT. Two
things changed. That paragraph is now DERIVED from the record set. And before emitting anything,
the emitter scans its OWN source for a typed SENTENCE that carries a backticked name this
measurement reports together with a classification or verdict word, and REFUSES to publish rather
than let one be typed again. What that tooth cannot see is the typed-prose blind spot below, named
there rather than left to silence.

THE PREVIOUS VERSION OF THIS DOCUMENT WAS HAND-WRITTEN AND GUARDED, and the guard was the trap. It
re-derived every figure from the suite and compared, which caught staleness exactly as intended,
and which also made the document unsatisfiable: ordinary growth of the suite moves the target line
count, the statement count and the assertion-site totals. Measured twice. Merging an item that
added about 800 lines took the suite from 3287 passed and 0 failed to 3316 passed and 4 FAILED,
all four of them freshness assertions; appending one ordinary two-assertion block reddened three.
Either way the only remedy was a hand rewrite of the whole document. A check with teeth and an
unbounded manual cost to satisfy is not a guard. The teeth are unchanged and the cost is now one
command, because the remedy for a red is to run the emitter and commit its output.

THE VERSION BEFORE THAT WAS FROZEN INSTEAD, and it published its own failure under Blind spots:
"the cost of the choice is that a stale report stays green". That came true. Commit e9cf123 gave
the one obstructing region a PRIVATE validator instance, which removed the obstruction this survey
had named, and the published verdict stayed NOT_FEASIBLE while the file measured
FEASIBLE_WITH_PREPARATION. Nothing went red, because a prose warning is not a check.

Measured from: `scripts/selftest.py`, 201 lines
Content digest: sha256 e1986ae80787dbac127acfa1edf148a32cbaeebf816374d315215e89d6737264

WHY A DIGEST AND NOT A COMMIT. The line above names the exact bytes these figures were read off. A
commit id cannot do that job in a GENERATED file: it would go stale the moment anything else in
the repository was committed, redden this gate on every commit, and rebuild the trap the previous
version was. The digest changes exactly when the measured file changes, which is exactly when the
figures below change, and a reader who wants the tree can find the commit that carries these
bytes.

Reproduce: `python3 scripts/suite_survey.py --target scripts/selftest.py`
Machine-readable: the same command with `--json`. Finest partition: `--partition statement`.
Regenerate: `python3 scripts/suite_survey.py --emit-report`, which is what the gate runs.

Target: 201 lines, 40 top-level statements, 1 `# --- ` marker regions, 0 `expect(` sites.

## Verdict

Verdict: NOT_FEASIBLE

Reason, in the rule's own words: the residual graph has 1 component(s), below MIN_COMPONENTS=2.

The residual graph has 1 components. Its giant holds 1 of 1 regions and 0 of 0 assertion sites, a
share of 0.0000 against a ceiling of 0.50.
NOTHING BLOCKS A SPLIT. The survey reports no crossing name classified ORDERING_DEPENDENCY or
UNDETERMINED at all, so there is neither a removal set nor a sensitivity row: the residual graph
is already the boundary set.

THE MEASUREMENT BEFORE e9cf123 SAID NOT_FEASIBLE, and the difference was one commit. Until e9cf123
`V`, the module object for `.veldo/validate.py`, was MUTATED in one of the regions that read it,
which made every region reading it ordering-dependent and welded the giant. Commit e9cf123 gave
that region its own module instance; a private instance bound and mutated inside a single region
does not cross at all and does not appear in this report. The survey did not change. The file did.
What `V` is classified as NOW is a row of the per-symbol index below, which is emitted, rather
than a sentence here, which would be a memory.

A verdict of NOT_FEASIBLE is EXIT 0, and so is this one. The exit code reports whether the
ANALYSIS completed, never what it found. An analyst that cannot return a negative result without
breaking the build is not measuring anything.

### The rule, and the constants it is a rule over

| constant | value | meaning |
|---|---|---|
| `MIN_COMPONENTS` | 2 | fewer residual components than this and there is nothing to split |
| `LARGEST_COMPONENT_MAX_SHARE` | 0.50 | of assertion sites; a bigger giant delivers neither parallel lanes nor a fast subset run |
| `UNDETERMINED_MAX_SHARE` | 0.10 | of crossing names; above this the analysis cannot support a split decision |

NOT_FEASIBLE if the residual components are below the minimum or the undetermined share is over
its ceiling or the largest share is over its ceiling with hoisting already applied; FEASIBLE if
all three hold with no preparatory hoisting; FEASIBLE_WITH_PREPARATION otherwise. THE THREE
CONSTANTS ARE JUDGEMENTS, not derivations. They are published here, next to the distribution and
the sensitivity table, precisely so a reader who disagrees with the largest-share ceiling can see
what changes. A reader who reads only the verdict line will not catch that, which is the
thresholds blind spot below.

### The named preparation

Published whatever the verdict. Greedy by edge count, so it is an UPPER BOUND on the work and not
a proven minimum.

1. HOIST nothing. No crossing name is classified SHARED_FIXTURE, so there is no fixture module to
   extract.
2. REMOVE nothing. The greedy search returns an empty removal set, so the constants hold on
   hoisting alone. This step used to name `V` and e9cf123 landed it.
3. NOT required by the rule but required by honesty: the assertion callee `expect` is not a
   crossing name in this measurement at all, so it is not in the hoist set and there is nothing to
   carry with it.

## Totals

Every row here is emitted from the measurement. None of them is typed.

| measure | value |
|---|---|
| Target lines | 201 |
| Crossing names | 0 |
| Crossing read sites | 0 |
| Regions (marker partition) | 1 |
| Top-level statements (finest partition) | 40 |
| Assertion sites | 0 |
| Raw components (all crossing edges) | 1 |
| Residual components (SHARED_FIXTURE edges removed) | 1 |
| Largest residual component, assertion sites | 0 |
| Largest residual component, regions | 1 |
| Literal path crossings (carrier C6) | 0 |
| Interpreter and process events (carriers C4, C5) | 2 |
| Module objects crossing regions | 0 |
| Module names loaded more than once | 0 |
| Hoistable symbols (class SHARED_FIXTURE) | 0 |
| Symbols a split must move together or remove | 0 |
| Symbols the greedy preparation search says to remove | 0 |
| Largest residual share | 0.0000 |
| Undetermined share of crossing names | 0.0000 |

Total crossing names: 0

| class | count |
|---|---|
| SHARED_FIXTURE | 0 |
| PER_SUITE_LOCAL | 0 |
| ORDERING_DEPENDENCY | 0 |
| UNDETERMINED | 0 |

UNDETERMINED IS THE DEFAULT AND EVERY OTHER LABEL NEEDS POSITIVE MECHANICAL PROOF. SHARED_FIXTURE
requires a purity FIXPOINT: every binding unconditional, every right-hand side an import, a def, a
class, a literal, a literal collection, a module load, or a call whose callee and every argument
are themselves already proven pure, iterated to a least solution. A conditional binding, a
with-item target, any mutation, or a callable read outside call position keeps the name
UNDETERMINED or ORDERING_DEPENDENCY. The costs are not symmetric: a wrong SHARED_FIXTURE licenses
a move that silently breaks an assertion, a wrong UNDETERMINED costs someone a manual look.

## Blocking symbols

EVERY name the survey classifies ORDERING_DEPENDENCY or UNDETERMINED, which is exactly the set a
split must move together or remove rather than hoist. The table IS the survey's own non-hoistable
record set, emitted whole, so a name entering that class (a new monkeypatch) or leaving it (which
is what e9cf123 did to `V`) changes the document and lands in the diff instead of silently
contradicting a published table. Every row is auditable from the columns alone: open the file at
the binding line and at any read line.

| symbol | class | bound | crossing reads | regions | mutation lines, or why undetermined |
|---|---|---|---|---|---|

The table is EMPTY, which is the finding: over `scripts/selftest.py` the survey classifies no
crossing name as an ordering dependency or as undetermined, so a split has nothing to move
together and nothing to remove.

### The interpreter and process carriers, which are not names

These cross to EVERY later region regardless of any name.

| carrier | line | what | later regions affected |
|---|---|---|---|
| C4 | 60 | sys.path.insert() | 0 |
| C4 | 61 | sys.path.insert() | 0 |

### The filesystem index (carrier C6), a PARTIAL view by construction

Literal repository-relative paths written by one region and read by another. Paths built by an
f-string or by `os.path.join` over variables are carrier B1 and INVISIBLE here.

| path | written at | read at | regions |
|---|---|---|---|

WHETHER A GIVEN ROW IS A REAL SHARED-STATE CROSSING or an artifact of a path written into a
temporary clone and read back from the repository IS NOT DECIDED HERE, and no sentence in this
document decides it for every row at once. The previous version of this paragraph did claim that
for every row, which is a universal about a table the suite can grow, and nothing checked it. The
columns are the audit: open the write line and the read line. The index is published as it is
measured.

### Module loads

No module name is loaded more than once through `importlib.util.spec_from_file_location`, so the
independence a second distinct module object would buy is not in play here.

## Proposed suite boundary set

DERIVED FROM THE READ PATTERN, never from the topic names in the region headers. The nodes are
regions, the edges are crossings NOT classified SHARED_FIXTURE, and the boundaries are the
connected components of that graph. A boundary drawn where data actually stops crossing yields
suites that are independent by construction; a boundary drawn around a topic yields suites that
look tidy and share state. Size is measured in `expect(` sites, not in lines, because WARP-0712's
goal is a developer running one suite in a second and cost tracks assertions.

The distribution, as emitted rows:

| measure | value |
|---|---|
| Components with 100 or more assertion sites | 0 |
| Components with 50 to 99 assertion sites | 0 |
| Components with 10 to 49 assertion sites | 0 |
| Components with 1 to 9 assertion sites | 0 |
| Components with 0 assertion sites | 1 |

EVERY residual component, in descending order of assertion sites. This table IS the proposed
boundary set, so it is published whole rather than as a top-N prefix: a truncated table would let
a component merge or divide below the cut without changing a line, and there would be no row count
to pin without pinning a number the suite can grow.

The region column is the survey's own region label, normalised the only two ways a markdown cell
forces: a `|` becomes `/` and surrounding whitespace goes.

| assertion sites | regions | first region in the component |
|---|---|---|
| 0 | 1 | (preamble) |

The tail is what the rows above make of it: 1 of the 1 residual components hold fewer than fifty
assertions each and 1 hold fewer than ten, while the largest holds 0 of 0 assertion sites. Under
the published constants those numbers give the verdict NOT_FEASIBLE. Most of this suite is
therefore ALREADY independent and needs the shared fixtures hoisted rather than a rewrite.

WARP-0712 should re-derive these boundaries after hoisting rather than reading them off this
table: hoisting removes edges, so the component set after preparation is finer than the one here.

## Carrier coverage

The completeness claim has two dimensions and they are defended differently. Saying which is which
is the point.

DIMENSION 1, THE BOUNDARY CHOICE: PROVEN. A crossing is only defined relative to a partition, so
the survey computes the relation ONCE at the FINEST partition the file admits, one top-level
statement per region, and derives every coarser view by PROJECTION. Coarsening only merges regions
and merging can only remove boundary pairs, never create them, so every crossing under any coarser
partition is a crossing under the finest one. The selftest asserts that inclusion as a SET
RELATION on the fixture and on the real file. Consequence: no choice of suite boundary WARP-0712
makes can surface a crossing this survey did not already enumerate.

DIMENSION 2, THE CARRIER SET: ARGUED, with a proven coverage matrix over the declared carriers and
an explicit blind list for the rest. A value written by earlier module-level code can be observed
by later code only if it lives somewhere, and the table below partitions those places. A seventh
carrier would have to be a place a value can be that is none of: this module's namespace, an
object reachable from it, the interpreter, the process, or the filesystem. That enumeration cannot
be PROVEN exhaustive. It is published as a constant with a stated partitioning principle so a
reviewer can NAME the seventh carrier instead of reverse-engineering what was checked.

Each DETECTED carrier has at least one POSITIVE fixture case the tool must report and at least one
NEGATIVE near-miss it must not. A selftest assertion computes, from the survey's own `CARRIERS`
constant and from the case table in the assertion block, that the set of carriers with both kinds
of case EQUALS the set marked DETECTED, that every BLIND carrier has a non-empty reason and no
case, and that the two sets exhaust the constant. Adding a carrier to the code without writing
both cases turns the gate red. Neither side is a literal count. The row below is emitted from that
same constant, and the emitter REFUSES to publish a carrier it has no description for, so an
undocumented carrier cannot reach this table either.

| id | status | carrier | positive fixture case | negative fixture case |
|---|---|---|---|---|
| C1 | DETECTED | module namespace: a name bound by one statement and read by another | `SHARED_C1` bound in region A, read in region C | `local_c1` bound and read inside region B |
| C2 | DETECTED | indirection: a callable defined in one region whose body reads a global, invoked from another | `G_C2` read only inside `helper_c2`, called from region C | `arg_c2`, a parameter of a callable crossed by its own name |
| C3 | DETECTED | value mutation: container mutation, subscript store, augmented assignment, attribute store (a monkeypatch is this carrier applied to a module object) | `ACC` appended to, `SET_C3` narrowed by `difference_update`, `PATCHED.limit` stored | `tmp_c3` bound, mutated and read inside region B |
| C4 | DETECTED | interpreter globals: recursion limit, `sys.path`, `sys.modules`, warnings filters, locale, random state | `sys.setrecursionlimit(4000)` | `sys.getrecursionlimit()`, a read |
| C5 | DETECTED | process globals: `os.environ`, cwd, umask | `os.environ["S16_FLAG"] = "1"` | `os.environ.get("S16_FLAG")`, a read |
| C6 | DETECTED | filesystem, LITERAL paths written by one region and read by another | `data/shared_c6.json` written in B, read in C | `data/local_c6.json` written and read in B |
| B1 | BLIND | filesystem paths that are not literals | none, and none possible from an AST | none |
| B2 | BLIND | conditional-binding shadowing | none | none |
| B3 | BLIND | reflective namespace reads | none | none |

The tool's `MUTATOR_METHODS` set is DERIVED from the interpreter (the methods a mutable builtin
has and its immutable counterpart does not) rather than typed out. The first draft was typed and
omitted `set.difference_update`, which the target was calling on a validator module's vocabulary
at the time, so the omission cost a real crossing. Whether the target still calls it is a row of
the tables below and not a sentence here: the sentence that used to claim it was a present-tense
claim about the measured file with nothing checking it. The `SET_C3` fixture case exists so a
regression to a hand-written list fails mechanically.

The NEGATIVE CONTROL is a second fixture: a DETANGLED TWIN of the tangled one, same shape with
every crossing removed, over which the survey must report ZERO crossings, ZERO path crossings and
FEASIBLE. Without it, a tool that answered NOT_FEASIBLE to everything would score perfectly on the
tangled fixture and this document's verdict would be an artifact of the analyser rather than a
finding about the file. The twin asserts through `print` rather than a shared `expect`, BECAUSE a
shared assertion helper is itself a crossing. That is not a fixture convenience, it is the finding
restated: even the assertion helper has to be hoisted before any suite can run alone.

## Blind spots

Named so that silence does not read as coverage. In descending order of how badly each could
mislead WARP-0712.

1. THE CARRIER ENUMERATION IS AN ARGUMENT AND ITS FAILURE IS TOTALLY SILENT. If a seventh carrier
   exists that nobody named, there is no fixture case for it, the matrix shows every declared
   carrier DETECTED, every assertion is green, this report reads clean, and it is wrong. The
   fail-closed UNDETERMINED default does NOT save this: fail-closed fires on a symbol the tool
   sees and cannot classify, while a carrier nobody looks at produces no symbol at all. Absence of
   a look is indistinguishable from absence of a crossing. This is the largest silent-failure path
   in the item and it is NOT closed.
2. COMPUTED FILESYSTEM PATHS ARE INVISIBLE (carrier B1). A region that writes an artifact through
   an f-string path and a later region that reads it look mutually independent, land in different
   components, get split into different suites, and the second then passes alone while checking
   something weaker. Nothing goes red anywhere in that sequence. The literal index above is the
   part that could be measured, not the whole of C6.
3. THE FIXTURE PROVES SHAPES, NOT CARRIERS. Within a DETECTED carrier the fixture contains
   particular shapes. A crossing through a class attribute, a default argument evaluated at def
   time, a module-level decorator, or a closure over a loop variable could be missed while every
   fixture case passes green. The matrix asserts one positive and one negative case per carrier;
   it cannot assert that the case is representative.
4. THE CONDITIONAL-BINDING MASK (carrier B2). The reaching-definition scan is flow-insensitive
   about whether a conditional binding executed. A conditional reaching definition is marked
   UNDETERMINED, which is visible noise. But when a conditional binding is later SHADOWED by an
   unconditional one, the crossing that existed on the path where the conditional did not fire is
   hidden and carries no flag.
5. REGENERATION PROVES THIS DOCUMENT MATCHES THE MEASUREMENT, NOT THAT THE MEASUREMENT IS RIGHT.
   Every figure here comes from the same tool that produced it, so a survey that is WRONG about
   the measured file produces a document that agrees with itself and a green gate. Generation
   closes staleness completely: a stale figure is not merely caught, it cannot reach a green gate
   at all. It cannot close error, and the two are different failures.
6. EVERY HARD ASSERTION ABOUT THE TOOL'S BEHAVIOUR IS AGAINST A FIXTURE. The real-file assertions
   that bear on the survey being CORRECT are structural: vocabulary membership, provenance of each
   named binding line, the subset relation between partitions, and the assertion block's own
   prefix containment. None of them can fire on a crossing the survey never looked for. That is
   the definitional blindness of a proxy and it does not go away by being mentioned. What
   partially covers it is the per-symbol index below: any single false entry is falsifiable by
   hand.
7. THE THRESHOLDS LAUNDER A JUDGEMENT INTO A VERDICT. A largest component just under the ceiling
   reports FEASIBLE_WITH_PREPARATION and reads as a green light; just over it reports
   NOT_FEASIBLE. The constants are the author's, derived from nothing. The distribution and the
   sensitivity table let a reader catch it; a reader who reads only the verdict line will not.
8. THE MARKER CONVENTION IS NOT ENFORCED. A future block that omits its `# --- ` header merges
   into its predecessor's marker region and its crossings disappear from the marker VIEW. The
   per-statement computation still sees them and the marker view is a projection, so the totals do
   not lie, but a reader reading only the region tables sees a tidier file than exists.
9. NO DYNAMIC OBSERVATION WAS BUILT. A `sys.settrace` or audit-hook harness would catch computed
   paths and reflective access that an AST cannot. It was rejected here for three reasons: it
   requires executing the full suite; it is the subset runner's job; and it observes only the
   paths one run happens to take, so it is not a superset of the static view. The confirming
   experiment is named as WARP-0712's obligation: run each candidate suite ALONE and in AGGREGATE
   and compare the assertion label sets.
10. GENERATION MAKES THE FIGURES UNFALSIFIABLE BY A READER, AND THAT IS A REAL COST. When this
    document was hand-written, a reader who disbelieved a number could compare it to the tool's
    output and find a discrepancy; now the two agree by construction and that particular check is
    gone. What replaces it is stronger for staleness and weaker for nothing else: the emitter is
    one function over the survey's own record set, and the fixture assertions in the suite drive
    the emitter over fixtures whose verdicts DISAGREE with each other so it cannot degenerate into
    printing a constant. No count of fixtures appears in that sentence: the suite can grow one,
    and a number typed here would be the next thing to go stale.
11. THE TYPED PROSE IS NOT DERIVED, AND ITS GUARD IS A SHAPE TRIPWIRE RATHER THAN A PROOF. Every
    paragraph in this document is a hand-typed constant in the emitter; only the tables and the
    sentences built from them are derived. One typed paragraph did assert a measurement and
    shipped contradicting the tables beside it at a green gate, which is why the emitter now scans
    its own source and REFUSES a typed SENTENCE that pairs a backticked name this measurement
    reports with a word from the class or verdict vocabulary. THAT IS ALL IT CATCHES. It does not
    see a claim split across two sentences, a class named in lower-case prose rather than in the
    vocabulary's own spelling, a claim about a read count or a region count rather than a class, a
    claim about a name the measurement does not report, or any prose in this document that is
    simply wrong about something the survey never measures. The remedy for those is the same one
    that found the first one: an independent review that drives a mutation and reads the emitted
    file.

### Obligation on WARP-0712

Re-run the survey after restructuring `scripts/selftest.py` and let the gate republish this
document; the figures need no human. What is still handed to WARP-0712 by name, because no
generator can do it, is the DYNAMIC confirmation: run each candidate suite ALONE and in AGGREGATE
and compare the assertion label sets. That is the experiment this static survey cannot be.

## Sensitivity

What the same rule would say with the top blocking symbols removed. Rows after the first assume
the SHARED_FIXTURE hoist is ALREADY applied, which is why they may read FEASIBLE rather than
FEASIBLE_WITH_PREPARATION. Every row is emitted from a re-run of the rule.

| symbols removed | components | largest share | verdict |
|---|---|---|---|
| none (as measured) | 1 | 0.0000 | NOT_FEASIBLE |

There is no blocking symbol to drop, so the table has no rows after the first. Every figure in
that claim is an emitted row above or an emitted cell of the constants table: the residual
component count against `MIN_COMPONENTS`, the undetermined share against `UNDETERMINED_MAX_SHARE`,
and the largest residual share against `LARGEST_COMPONENT_MAX_SHARE`.

## Per-symbol index

Every crossing symbol the survey reports, so a verdict can be audited without re-running anything:
open `scripts/selftest.py` at the binding line, check any read line, and disagree with the class.
Sorted by class then by crossing read sites. The last column carries the first mutation line for a
mutated name, or the first C2 call site for a name that crosses by indirection. This table IS the
survey's record set, emitted whole, so a symbol appearing, vanishing, changing class or moving its
binding line changes the document. It is the section a reader audits by hand, which is why the
line numbers in it are emitted rather than transcribed.

| symbol | class | carrier | bound | crossing reads | read lines | mutation / via |
|---|---|---|---|---|---|---|
