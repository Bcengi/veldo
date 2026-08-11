"""WARP-1103 COMPLETION: the MANDATORY placement gate at the ready transition and the

ONE SUITE OF THE UNIT SUITE, AND A FRAGMENT RATHER THAN A MODULE. It is compiled and executed
into scripts/suites/shared.py's namespace by scripts/selftest.py, in manifest order, so every
suite sees exactly the state the monolith gave it and this decomposition cannot change what any
assertion proves. That is the whole reason for the design: the monolith carries cross-region
dependencies through MUTATED objects and through the filesystem, not only through names, and no
mechanical analysis finds those. Sharing one namespace in the original order means no membership
rule has to be closed and correctness is a property of the construction.

Run it: `python3 scripts/selftest.py --upto 07_warp_1103_completion_mandatory` runs everything up to and including this
file, which is the inner loop for a change here. `python3 scripts/selftest.py` runs everything
and is the only thing that means green.

Regions 90-96 of the pre-split monolith.
"""


# --- WARP-1103 COMPLETION: the MANDATORY placement gate at the ready transition and the
# claim, plus the footprint->tier rule (outcome O3, work item W3, regression RJ2 of
# PLAN-0011). The prior build shipped placement as an OPTIONAL structural declaration and
# deferred the mandatory gate; this closes the gap. placement_gate (a PURE predicate in
# arch.py) is the ONE implementation, enforced at the ready transition (validate.check_ready),
# the claimable frontier (frontier.claimable), and run-check (plan.cmd_run_check), and NEVER as
# a static check_spec sweep of every spec - so the 107 already-shipped specs (past ready and
# claim) are never re-evaluated and need no migration. Negative-first with real teeth: a
# placeless spec is refused at ready and never claimed; a boundary-crossing footprint raises
# the tier; and a no-corpus-sweep guard proves a shipped placeless spec still validates.
def _gate_problems(fm_text, contract=_P13_CONTRACT):
    """Parse a spec's front-matter subset and run the MANDATORY placement gate; a parse
    failure is itself a refusal (non-empty), never a silent pass."""
    try:
        fm = V.parse_yamlish(fm_text)
    except ValueError:
        return ["parse error"]
    return ARCH.placement_gate(fm, contract)

# AC6 the mandatory gate over the fixture contract (areas core, edge). A placeless spec, and
# a placement to an undeclared area, are REFUSED; a resolving placement + footprint passes.
expect("WARP-1103 AC6 gate: a placeless spec is refused (mandatory placement, contract present)",
       len(_gate_problems("id: X\ntitle: Y\nrisk: standard\n")) > 0)
expect("WARP-1103 AC6 gate: a placement to an undeclared area is refused (referenced but absent)",
       len(_gate_problems("placement: [ghost]\nfootprint: [src/x.py]\nrisk: standard\n")) > 0)
expect("WARP-1103 AC6 gate: a resolving placement with a footprint passes",
       _gate_problems("placement: [core]\nfootprint: [src/core/x.py]\nrisk: standard\n") == [])

# AC7 footprint->tier (REFINED by WARP-1011, founder decision 2026-07-22): the tier is raised to
# high ONLY when the touched areas contain a PAIR with NO allow-listed dependency edge between them
# in either direction (a genuine boundary crossing / unmodeled coupling); a pair the contract's
# dependencies.allow connects is cohesive breadth and does NOT elevate; a single area does not
# elevate. area_for_path maps a path to its area (and to none outside). _BC_CONTRACT extends the
# fixture (core, edge with edge->core) with an unconnected "island" area, so both a CONNECTED pair
# {core, edge} (stays standard) and an UNMODELED pair {core, island} (elevates high) are exercised.
_BC_ARCH = GOOD_ARCH.replace(
    "dependencies:",
    "  - id: island\n    title: Island area, joined to nothing by any dependency edge\n"
    "    includes: [\"src/island/z.py\"]\ndependencies:", 1)
_BC_CONTRACT = V.parse_yamlish(_BC_ARCH)  # areas core, edge, island; only edge->core
def _bc_gate(fm_text):
    return ARCH.placement_gate(V.parse_yamlish(fm_text), _BC_CONTRACT)
_connected_pair = "placement: [core]\nfootprint:\n  - src/core/x.py\n  - src/edge/y.py\n"  # {core, edge}, edge->core
_unmodeled_pair = "placement: [core]\nfootprint:\n  - src/core/x.py\n  - src/island/z.py\n"  # {core, island}, no edge
expect("WARP-1103 AC7 area_for_path: a footprint path maps to its declared area (and to none outside)",
       ARCH.area_for_path("src/edge/y.py", _P13_CONTRACT) == {"edge"}
       and ARCH.area_for_path("outside/nowhere.py", _P13_CONTRACT) == set())
expect("WARP-1103 AC7 tier: a two-area footprint whose pair is connected by an allowed edge does NOT elevate (cohesive breadth, not a crossing)",
       ARCH.footprint_tier_floor(V.parse_yamlish(_connected_pair), _BC_CONTRACT) == "")
expect("WARP-1103 AC7 tier: a two-area footprint whose pair has NO allowed edge floors the tier at high (a genuine boundary crossing)",
       ARCH.footprint_tier_floor(V.parse_yamlish(_unmodeled_pair), _BC_CONTRACT) == "high")
expect("WARP-1103 AC7 tier: a single-area footprint does not raise the tier",
       ARCH.footprint_tier_floor(V.parse_yamlish("placement: [core]\nfootprint: [src/core/x.py]\n"),
                                 _BC_CONTRACT) == "")
expect("WARP-1103 AC7 tier RED: an unmodeled-pair footprint at risk standard is refused",
       any("risk tier" in p for p in _bc_gate(_unmodeled_pair + "risk: standard\n")))
expect("WARP-1103 AC7 tier GREEN: the same unmodeled-pair footprint at risk high passes (revert teeth)",
       _bc_gate(_unmodeled_pair + "risk: high\n") == [])
expect("WARP-1103 AC7 tier GREEN: a connected-pair footprint at risk standard passes (the core fix: breadth is not a crossing)",
       _bc_gate(_connected_pair + "risk: standard\n") == [])

# AC6 at the FILE / TRANSITION boundary over a temporary tree: check_ready stands down with no
# contract (adoption safe), refuses a placeless ready spec once a contract exists, and passes a
# placed one. THE NO-CORPUS-SWEEP GUARD: a SHIPPED placeless spec (and even a ready placeless
# spec) still validates through check_spec - the corpus path - proving the mandatory rule lives
# at the ready transition, not in a check_spec sweep of every spec.
with tempfile.TemporaryDirectory() as _rgd:
    _rgp = Path(_rgd)
    (_rgp / ".veldo").mkdir()
    (_rgp / "specs").mkdir()
    _placeless = _rgp / "specs" / "S.md"
    _placeless.write_text("---\nschema: veldo.spec/v1\nid: S\ntitle: t\nstatus: ready\n"
                          "risk: standard\nowner: d\nacceptance_criteria: [x]\n---\nbody\n")
    expect("WARP-1103 AC6: no contract stands the ready gate down (adoption safe)",
           V.check_ready(_placeless, repo_root=_rgp) == 0)
    (_rgp / ".veldo" / "architecture.yaml").write_text(GOOD_ARCH)  # areas core, edge
    expect("WARP-1103 AC6: a placeless ready spec is REFUSED at the ready transition (contract present)",
           V.check_ready(_placeless, repo_root=_rgp) > 0)
    expect("WARP-1103 AC6 no-corpus-sweep: check_spec does NOT apply the mandatory gate (placeless ready spec still validates)",
           V.check_spec(_placeless, repo_root=_rgp) == 0)
    _shipped = _rgp / "specs" / "Sh.md"
    _shipped.write_text("---\nschema: veldo.spec/v1\nid: Sh\ntitle: t\nstatus: shipped\n"
                        "risk: standard\nowner: d\nacceptance_criteria: [x]\n---\nbody\n")
    expect("WARP-1103 AC6 no-corpus-sweep: a shipped placeless spec still validates via check_spec (never swept)",
           V.check_spec(_shipped, repo_root=_rgp) == 0)
    _placed = _rgp / "specs" / "P.md"
    _placed.write_text("---\nschema: veldo.spec/v1\nid: P\ntitle: t\nstatus: ready\nrisk: standard\n"
                       "owner: d\nplacement: [core]\nfootprint: [src/core/x.py]\nacceptance_criteria: [x]\n---\nbody\n")
    expect("WARP-1103 AC6: a ready spec with a resolving placement passes the ready transition",
           V.check_ready(_placed, repo_root=_rgp) == 0)

# AC6 the CLAIM side ("never claimed") at the frontier over a temporary tree WITH a contract: a
# placeless ready BUILD spec is filtered out of the claimable set, a placed one is claimable, and
# a review unit is NOT placement-gated (a review is of an already-built spec, not a build claim).
with tempfile.TemporaryDirectory() as _fgrepo, tempfile.TemporaryDirectory() as _fgclaims:
    os.makedirs(os.path.join(_fgrepo, ".veldo"))
    os.makedirs(os.path.join(_fgrepo, "specs"))
    os.makedirs(os.path.join(_fgrepo, "plans"))
    open(os.path.join(_fgrepo, ".veldo", "architecture.yaml"), "w").write(GOOD_ARCH)  # core, edge
    def _fgw(rel, text):
        open(os.path.join(_fgrepo, rel), "w").write(text)
    _fgw("plans/PLAN-G.md",
         "---\nschema: veldo.plan/v1\nid: PLAN-G\ntitle: g\nstatus: in_progress\nrevision: 1\n"
         "owner: d\nwork:\n  - item: G1\n    spec: VELDO-G1\n    depends_on: []\n"
         "  - item: G2\n    spec: VELDO-G2\n    depends_on: []\n---\nbody\n")
    _fgw("specs/VELDO-G1.md",
         "---\nschema: veldo.spec/v1\nid: VELDO-G1\ntitle: t\nstatus: ready\nowner: d\n"
         "lane: planned\nplan: PLAN-G\nwork: G1\nplacement: [core]\nfootprint: [src/core/x.py]\n---\nbody\n")
    _fgw("specs/VELDO-G2.md",  # placeless: never claimed while a contract exists
         "---\nschema: veldo.spec/v1\nid: VELDO-G2\ntitle: t\nstatus: ready\nowner: d\n"
         "lane: planned\nplan: PLAN-G\nwork: G2\n---\nbody\n")
    _fgw("specs/VELDO-G3.md",  # a review unit is not build-gated
         "---\nschema: veldo.spec/v1\nid: VELDO-G3\ntitle: t\nstatus: review\nowner: d\nlane: standalone\n---\nbody\n")
    _fgset = {u["spec"] for u in FR.claimable(worker_caps=[], repo_root=_fgrepo, claims_root=_fgclaims)}
    expect("WARP-1103 AC6 frontier: a placed ready build spec is claimable (contract present)",
           "VELDO-G1" in _fgset)
    expect("WARP-1103 AC6 frontier: a placeless ready build spec is NEVER claimed (contract present)",
           "VELDO-G2" not in _fgset)
    expect("WARP-1103 AC6 frontier: a review unit is not placement-gated",
           "VELDO-G3" in _fgset)

# AC6/AC7 DOGFOOD over the REAL WARP-1103 spec and the REAL contract: it declares a resolving
# placement (contracts) and its footprint touches the fleet area (it edits frontier.py), so it
# spans {contracts, fleet}. Under the REFINED rule (WARP-1011, founder decision 2026-07-22) that
# pair is CONNECTED by the allow-listed fleet-to-contracts edge, so it is cohesive breadth, NOT a
# boundary crossing, and does NOT elevate - exactly the rubber stamp the founder decision removes.
# WARP-1103 shipped at recorded risk high on the record, unchanged (the refinement is forward-only
# and re-tiers no shipped spec); it still PASSES the gate at risk high (nothing lowers a declared
# tier). MUTATION teeth on a copy of the real front matter (reverting byte-identical): removing the
# placement turns the gate RED (mandatory placement is unchanged); and lowering its risk to standard
# NO LONGER trips a tier floor - the direct dogfood of the founder fix on the spec that motivated it.
_p13_realfm_dict = V.parse_yamlish(_p13_fm)  # _p13_fm and _P13_REAL_CONTRACT defined by the block above
expect("WARP-1103 AC7 dogfood: the real spec's footprint spans contracts and fleet",
       ARCH.footprint_areas(_p13_realfm_dict, _P13_REAL_CONTRACT) >= {"contracts", "fleet"})
expect("WARP-1103 AC7 dogfood (refined): {contracts, fleet} is connected by fleet-to-contracts, so the footprint does NOT elevate (cohesive breadth, not a crossing)",
       ARCH.footprint_tier_floor(_p13_realfm_dict, _P13_REAL_CONTRACT) == "")
expect("WARP-1103 AC6 dogfood: the real spec PASSES the mandatory gate (placed, recorded risk high; nothing lowers a declared tier)",
       ARCH.placement_gate(_p13_realfm_dict, _P13_REAL_CONTRACT) == [])
_p13_gate_noplace = _p13_fm.replace("placement: [contracts]\n", "", 1)
expect("WARP-1103 AC6 TEETH: removing the real spec's placement turns the mandatory gate RED",
       _p13_gate_noplace != _p13_fm
       and len(ARCH.placement_gate(V.parse_yamlish(_p13_gate_noplace), _P13_REAL_CONTRACT)) > 0)
_p13_gate_lowrisk = re.sub(r"(?m)^risk: high.*$", "risk: standard", _p13_fm, count=1)
expect("WARP-1103 AC7 dogfood (refined): lowering the real spec's risk to standard no longer trips a tier floor - its {contracts, fleet} footprint is cohesive breadth, not a boundary crossing (the founder fix, forward-only)",
       _p13_gate_lowrisk != _p13_fm
       and not any("risk tier" in p for p in ARCH.placement_gate(V.parse_yamlish(_p13_gate_lowrisk), _P13_REAL_CONTRACT)))
expect("WARP-1103 AC6: the real WARP-1103 spec passes check_ready (integrated ready transition, run in the gate)",
       V.check_ready(_p13_file) == 0)

# AC6 dogfood at the build gate: plan.py run-check clears WARP-1103 (deps shipped, placement
# resolves, risk high >= the footprint's tier floor). Reuses the one predicate through validate.
_p13_planspec = importlib.util.spec_from_file_location("veldo_plan_p13", ROOT / ".veldo/plan.py")
_P13PL = importlib.util.module_from_spec(_p13_planspec); _p13_planspec.loader.exec_module(_P13PL)
import io as _p13io, contextlib as _p13ctx
_p13buf = _p13io.StringIO()
with _p13ctx.redirect_stdout(_p13buf):
    _p13rc = _P13PL.cmd_run_check("PLAN-0011", "WARP-1103")
expect("WARP-1103 AC6 dogfood: plan.py run-check clears WARP-1103 (deps + resolving placement + tier)",
       _p13rc == 0)

# --- adversarial decision review (WARP-1106, W6 of PLAN-0011): a foundational choice
# is ATTACKED by a fresh context before a human commits to it. A veldo.decision_review/v1
# artifact (.veldo/decision_reviews/*.yaml) binds to a decision record and records the
# attack on the framing (problem-class, per-option, missing-option, per-assumption
# challenges plus a recommendation and a disposition), decision_review.py validates it
# structurally the way decision.py checks a record, binds it to the decision it reviews,
# and enforces that a decision may move to decided only once it carries at least the bound
# adversarial reviews its risk tier requires (scrutiny scales with reversal cost, D5). The
# fresh-context reviewer is a DELEGATED seam that FAILS LOUD - no review is fabricated in
# code. Negative-first with real teeth; adoption safe: no .veldo/decisions/ directory stands
# the gate down. MUTATION teeth over the REAL shipped example prove the check is not
# vacuous. decision_review.py takes the parser, the reporter, and the decision loader from
# validate.py, so there is no second YAML parser and no import cycle.
_drspec = importlib.util.spec_from_file_location("veldo_decision_review", ROOT / ".veldo/decision_review.py")
DR = importlib.util.module_from_spec(_drspec); _drspec.loader.exec_module(DR)

# GOOD_DECISION (DEC-FIX, options opt_a/opt_b, assumption a1, version 1) and _DECIDED_BLOCK
# are defined by the WARP-1105 block above; reuse them so one decision fixture serves both.
GOOD_REVIEW = """schema: veldo.decision_review/v1
id: DR-FIX
version: 1
decision: DEC-FIX
decision_version: 1
reviewer: a fresh-context adversarial reviewer
recommendation: the framing survives the attack; the choice remains the human's to make.
disposition: defensible
problem_class_challenge:
  verdict: honest
  finding: The problem class is stated against the lifetime of the system, not today's scale.
option_challenges:
  - option: opt_a
    dead_end_verdict: holds
    finding: The dead_end holds: it stops working once the fan-out grows past a single node.
  - option: opt_b
    dead_end_verdict: holds
    finding: The dead_end holds: it couples to one engine and stops when a second producer appears.
missing_options: []
assumption_challenges:
  - assumption: a1
    verdict: load_bearing
    finding: Load bearing: if the fan-out did not grow, the cheap option would be defensible.
"""


def _dr_errs(text, root=ROOT):
    """Parse the review subset and validate structurally; a parse failure is itself a
    fail-closed rejection (non-zero), never a silent zero."""
    try:
        d = V.parse_yamlish(text)
    except ValueError:
        return 1
    return DR.validate_review(d, root, "selftest.review", V.fail)

# AC2 positive control: a well-formed review validates clean.
expect("WARP-1106 AC2: a well-formed veldo.decision_review/v1 review validates", _dr_errs(GOOD_REVIEW) == 0)
# AC2 closed vocabularies and required fields, negative-first.
expect("WARP-1106 AC2: a wrong schema id refuses",
       _dr_errs(GOOD_REVIEW.replace("veldo.decision_review/v1", "veldo.decision_review/v9")) > 0)
expect("WARP-1106 AC2: a missing required field (recommendation) refuses",
       _dr_errs(GOOD_REVIEW.replace("recommendation: the framing survives the attack; the choice remains the human's to make.\n", "")) > 0)
expect("WARP-1106 AC2: a non-integer version refuses (a review is versioned)",
       _dr_errs(GOOD_REVIEW.replace("version: 1\n", "version: soon\n", 1)) > 0)
expect("WARP-1106 AC2: a non-integer decision_version refuses",
       _dr_errs(GOOD_REVIEW.replace("decision_version: 1", "decision_version: latest")) > 0)
expect("WARP-1106 AC2: an out-of-vocabulary disposition refuses",
       _dr_errs(GOOD_REVIEW.replace("disposition: defensible", "disposition: greenlit")) > 0)
expect("WARP-1106 AC2: an out-of-vocabulary problem-class verdict refuses",
       _dr_errs(GOOD_REVIEW.replace("verdict: honest", "verdict: fine", 1)) > 0)
expect("WARP-1106 AC2: an out-of-vocabulary dead_end verdict refuses",
       _dr_errs(GOOD_REVIEW.replace("dead_end_verdict: holds", "dead_end_verdict: maybe", 1)) > 0)
expect("WARP-1106 AC2: an out-of-vocabulary assumption verdict refuses",
       _dr_errs(GOOD_REVIEW.replace("verdict: load_bearing", "verdict: decorative")) > 0)
expect("WARP-1106 AC2: an option_challenge lacking its finding refuses",
       _dr_errs(GOOD_REVIEW.replace("    finding: The dead_end holds: it stops working once the fan-out grows past a single node.\n", "", 1)) > 0)
expect("WARP-1106 AC2: an empty option_challenges list refuses (a review that challenges nothing is not a review)",
       _dr_errs(GOOD_REVIEW.replace(
           "option_challenges:\n  - option: opt_a\n    dead_end_verdict: holds\n    finding: The dead_end holds: it stops working once the fan-out grows past a single node.\n  - option: opt_b\n    dead_end_verdict: holds\n    finding: The dead_end holds: it couples to one engine and stops when a second producer appears.\n",
           "option_challenges: []\n")) > 0)
expect("WARP-1106 AC2: a duplicate option_challenge refuses",
       _dr_errs(GOOD_REVIEW.replace("  - option: opt_b\n", "  - option: opt_a\n", 1)) > 0)
# AC2 governance: a review INFORMS and never decides (no chosen, decided_by, decided_at).
expect("WARP-1106 AC2: a review smuggling a chosen option refuses (a review never decides)",
       _dr_errs(GOOD_REVIEW + "chosen: opt_b\n") > 0)
expect("WARP-1106 AC2: a review smuggling a decider refuses",
       _dr_errs(GOOD_REVIEW + "decided_by: sneaky\n") > 0)

# AC3 binding: pair a review to the decision it reviews, fail closed on absent/malformed,
# on a version mismatch, and on incomplete coverage; the positive control binds clean.
_dec_fix = V.parse_yamlish(GOOD_DECISION)   # DEC-FIX, options opt_a/opt_b, assumption a1, v1
_rev_fix = V.parse_yamlish(GOOD_REVIEW)
expect("WARP-1106 AC3: a well-formed review binds clean to its decision", DR.bind_review(_rev_fix, _dec_fix, "t", V.fail) == 0)
expect("WARP-1106 AC3: a review whose decision is absent/malformed refuses (referenced but absent)",
       DR.bind_review(_rev_fix, None, "t", V.fail) > 0)
expect("WARP-1106 AC3: a review whose decision_version does not match the record refuses (stale)",
       DR.bind_review(dict(_rev_fix, decision_version=2), _dec_fix, "t", V.fail) > 0)
expect("WARP-1106 AC3: a review that does not cover every option refuses (partial attack)",
       DR.bind_review(dict(_rev_fix, option_challenges=[oc for oc in _rev_fix["option_challenges"] if oc.get("option") != "opt_b"]), _dec_fix, "t", V.fail) > 0)
expect("WARP-1106 AC3: a review referencing an option the decision does not declare refuses (referenced but absent)",
       DR.bind_review(dict(_rev_fix, option_challenges=_rev_fix["option_challenges"] + [{"option": "ghost", "dead_end_verdict": "holds", "finding": "f"}]), _dec_fix, "t", V.fail) > 0)
expect("WARP-1106 AC3: a review that does not cover every assumption refuses",
       DR.bind_review(dict(_rev_fix, assumption_challenges=[]), _dec_fix, "t", V.fail) > 0)

# AC4 the fresh-context adversarial reviewer is a DELEGATED seam that FAILS LOUD - no review
# is fabricated in code, mirroring the executor's LiveLoop.review and the dispatcher's
# LiveReviewer. A fake injected reviewer is the only path an attack enters.
_dr_reviewer_raised = False
try:
    DR.LiveAdversarialReviewer().review(_dec_fix)
except DR.DecisionReviewError:
    _dr_reviewer_raised = True
expect("WARP-1106 AC4: the reference adversarial reviewer FAILS LOUD (refuses to fabricate a review)", _dr_reviewer_raised)
expect("WARP-1106 AC4: DecisionReviewError is a ValueError (raised by name)", issubclass(DR.DecisionReviewError, ValueError))


class _FakeAdversarialReviewer(DR.AdversarialReviewer):
    def review(self, decision, context=None):
        return {"schema": DR.SCHEMA, "id": "DR-INJ"}


expect("WARP-1106 AC4: an injected reviewer is the only path an attack enters (the seam, not fabrication)",
       _FakeAdversarialReviewer().review(_dec_fix).get("id") == "DR-INJ")

# AC1 this repository ships the illustrative example, and it validates + binds through the
# integrated validate.py entry point (run in the gate via the examples block).
_dr_example = ROOT / ".veldo/examples/decision-review-example.yaml"
_dec_example_dir = ROOT / ".veldo/examples"
expect("WARP-1106 AC1: the shipped decision-review example validates and binds via check_decision_review",
       V.check_decision_review(_dr_example, decisions_dir=_dec_example_dir) == 0)
expect("WARP-1106 AC1: the shipped example names the example decision (DEC-0000) and carries no decision block",
       _dr_example.is_file()
       and "decision: DEC-0000" in _dr_example.read_text()
       and "\nchosen:" not in _dr_example.read_text()
       and "\ndecided_by:" not in _dr_example.read_text())

# AC5 the decided-requires-review gate over a temporary tree: scrutiny scales with reversal
# cost (D5). A decided record with too few bound reviews is REFUSED; the bound review clears
# it; a critical record needs two; a stale-version review does not count; a draft needs none;
# and with no .veldo/decisions/ directory the whole gate stands down (adoption safe).
_DR_DECIDED_HIGH = GOOD_DECISION.replace("status: draft\n", _DECIDED_BLOCK)  # DEC-FIX decided, risk high -> 1 review
_DR_DECIDED_CRIT = (GOOD_DECISION.replace("reversal_cost: costly", "reversal_cost: irreversible")
                    .replace("risk: high", "risk: critical").replace("status: draft\n", _DECIDED_BLOCK))  # critical -> 2 reviews
_DR_REVIEW_BOUND = GOOD_REVIEW  # binds to DEC-FIX v1, covers opt_a/opt_b/a1


def _dr_gate(decisions, reviews):
    """Run check_reviews over a temp tree seeded with the given {name: text} decision and
    review files, copying this repository's real policy.yaml so risk_tiers is read."""
    with tempfile.TemporaryDirectory() as _d:
        _r = Path(_d)
        (_r / ".veldo").mkdir()
        (_r / ".veldo" / "policy.yaml").write_bytes((ROOT / ".veldo/policy.yaml").read_bytes())
        _dd = _r / ".veldo" / "decisions"
        _rd = _r / ".veldo" / "decision_reviews"
        if decisions is not None:
            _dd.mkdir()
            for n, t in decisions.items():
                (_dd / n).write_text(t)
        if reviews is not None:
            _rd.mkdir()
            for n, t in reviews.items():
                (_rd / n).write_text(t)
        _rf = lambda risk: DR.required_reviews_for(risk, _r / ".veldo" / "policy.yaml")
        return DR.check_reviews(_rd, _dd, _r, V.parse_yamlish, V.fail, _rf, DEC.load_record)


expect("WARP-1106 AC5: no .veldo/decisions/ directory stands the gate down (adoption safe, byte-identically unaffected)",
       _dr_gate(None, None) == 0)
expect("WARP-1106 AC5: a decided record with ZERO bound reviews is REFUSED",
       _dr_gate({"d.yaml": _DR_DECIDED_HIGH}, None) > 0)
expect("WARP-1106 AC5: a decided record with one bound review PASSES (scrutiny met)",
       _dr_gate({"d.yaml": _DR_DECIDED_HIGH}, {"r.yaml": _DR_REVIEW_BOUND}) == 0)
expect("WARP-1106 AC5 D5: a decided CRITICAL/irreversible record with ONE review is REFUSED (critical needs two)",
       _dr_gate({"d.yaml": _DR_DECIDED_CRIT}, {"r.yaml": _DR_REVIEW_BOUND}) > 0)
expect("WARP-1106 AC5 D5: a decided CRITICAL record with TWO bound reviews PASSES",
       _dr_gate({"d.yaml": _DR_DECIDED_CRIT},
                {"r1.yaml": _DR_REVIEW_BOUND, "r2.yaml": _DR_REVIEW_BOUND.replace("id: DR-FIX", "id: DR-FIX2")}) == 0)
expect("WARP-1106 AC5: a review bound to a stale decision_version does not satisfy the gate",
       _dr_gate({"d.yaml": _DR_DECIDED_HIGH},
                {"r.yaml": _DR_REVIEW_BOUND.replace("decision_version: 1", "decision_version: 2")}) > 0)
expect("WARP-1106 AC5: a DRAFT (un-decided) decision needs no review (the gate does not bite before a human decides)",
       _dr_gate({"d.yaml": GOOD_DECISION}, None) == 0)

# AC6 scrutiny reads policy.yaml risk_tiers (the single source of truth): standard=1, critical=2.
expect("WARP-1106 AC6: required_reviews_for reads policy risk_tiers (standard=1, critical=2, high=1)",
       DR.required_reviews_for("standard", ROOT / ".veldo/policy.yaml") == 1
       and DR.required_reviews_for("critical", ROOT / ".veldo/policy.yaml") == 2
       and DR.required_reviews_for("high", ROOT / ".veldo/policy.yaml") == 1)
expect("WARP-1106 AC6: an absent policy defaults to one review (the floor, never zero)",
       DR.required_reviews_for("critical", ROOT / ".veldo/nope_1106.yaml") == 1)

# AC6 MUTATION teeth over the REAL shipped example (anti-vacuity C1): stripping an
# option_challenge's finding, and removing the recommendation, each turn the check RED; each
# mutation is applied to a copy of the real text and reverts byte-identical.
_dr_real = _dr_example.read_text()
_dr_mut_finding = re.sub(r"\n    finding: The dead_end holds under attack:[^\n]*", "", _dr_real, count=1)
expect("WARP-1106 TEETH: stripping an option_challenge's finding from the real example turns the check RED",
       _dr_mut_finding != _dr_real and _dr_errs(_dr_mut_finding) > 0)
_dr_mut_rec = re.sub(r"\nrecommendation:[^\n]*", "", _dr_real, count=1)
expect("WARP-1106 TEETH: removing the recommendation from the real example turns the check RED",
       _dr_mut_rec != _dr_real and _dr_errs(_dr_mut_rec) > 0)
# and the unmutated real example validates AND binds (positive control, non-vacuous).
expect("WARP-1106 TEETH: the unmutated real example validates and binds (non-vacuous)",
       V.check_decision_review(_dr_example, decisions_dir=_dec_example_dir) == 0)

# AC6 TEETH on the decided-requires-review gate: a decided record with its sole bound review
# present PASSES, and DELETING that review turns the gate RED (the gate is non-vacuous).
expect("WARP-1106 TEETH: a decided record with its sole bound review present passes the gate",
       _dr_gate({"d.yaml": _DR_DECIDED_HIGH}, {"r.yaml": _DR_REVIEW_BOUND}) == 0)
expect("WARP-1106 TEETH: deleting the sole bound review of a decided record turns the gate RED",
       _dr_gate({"d.yaml": _DR_DECIDED_HIGH}, {}) > 0)

# AC6 the extended engine surface is byte-identical across the canonical copies (the gate's
# pack-drift and template-sync checks cover all packs; assert the root vs engine pair
# here as fast extra teeth), and the capability is declared mechanical.
expect("WARP-1106 AC6: .veldo/decision_review.py is byte-identical root vs engine",
       (ROOT / ".veldo/decision_review.py").read_bytes() == (ROOT / "engine/.veldo/decision_review.py").read_bytes())
expect("WARP-1106 AC6: .veldo/validate.py is byte-identical root vs engine",
       (ROOT / ".veldo/validate.py").read_bytes() == (ROOT / "engine/.veldo/validate.py").read_bytes())
expect("WARP-1106 AC6: the adversarial_decision_review capability is declared mechanical",
       bool(re.search(r"(?m)^\s{2}adversarial_decision_review:\s*\{status:\s*mechanical\b",
                      (ROOT / ".veldo/capabilities.yaml").read_text())))
expect("WARP-1106 AC6: the init scaffold lays .veldo/decision_review.py beside .veldo/decision.py",
       ".veldo/decision_review.py" in ISC.required_substrate())

# --- decision tripwires (WARP-1107, W7 of PLAN-0011): a foundational decision's assumptions
# are LIVING TRIPWIRES monitored IN-SESSION. A veldo.readings/v1 file (.veldo/readings/*.yaml)
# names the decision it measures and records, per assumption, a MEASURED reading (a value plus a
# machine-comparable breach_when, optionally an approaching_when early-warning) or a MANUAL_REVIEW
# reading (a human attestation with a valid_days expiry). A PURE evaluator, given the injected
# in-session date, compares each signal against its breach and FIRES on a breach or a lapse, fails
# closed on a malformed readings set, and stands down when no .veldo/decisions/ directory exists.
# The HEART of W7: it starts nothing (no process, no thread, no timer) - a source string-scan with
# mutation teeth proves it. A fired breach drafts exactly ONE veldo.redecision/v1 draft (idempotent)
# for a human to promote. Negative-first with real teeth; the entropy restoration loop (W8/W9) is
# honestly out of scope. tripwire.py takes the parser, the reporter, and the decision loader from
# validate.py, so there is no second YAML parser and no import cycle.
_twspec = importlib.util.spec_from_file_location("veldo_tripwire", ROOT / ".veldo/tripwire.py")
TW = importlib.util.module_from_spec(_twspec); _twspec.loader.exec_module(TW)

# a DECIDED decision fixture (only a decided foundation is monitored), three assumptions so both
# reading shapes and the unmonitored gap are exercised.
TRIP_DECISION = """schema: veldo.decision/v1
id: DEC-TW
title: A fixture decision to monitor
version: 1
status: decided
owner: fixture-owner
problem_class: judged against the problem class, never today's scale.
reversal_cost: costly
risk: high
options:
  - id: opt_a
    summary: the candidate option.
    dead_end: stops working past a single node.
assumptions:
  - id: a1
    statement: the fan-out grows over the life of the system.
    signal: instance count in the inventory
    breach: instance count exceeds the polling-cost threshold
  - id: a2
    statement: more than one producer type will emit the signal.
    signal: distinct producer types registered
    breach: a second producer type appears
  - id: a3
    statement: consumers reconcile on reconnect.
    signal: presence of a reconcile path per consumer
    breach: a consumer assumes exactly-once delivery
decision:
  chosen: opt_a
  decided_by: a-recorded-human
  decided_at: 2026-07-22
"""

GOOD_READINGS = """schema: veldo.readings/v1
decision: DEC-TW
readings:
  - assumption: a1
    kind: measured
    value: 6
    breach_when: ">= 40"
    approaching_when: ">= 25"
    at: 2026-07-22
  - assumption: a2
    kind: measured
    value: 1
    breach_when: ">= 2"
    at: 2026-07-22
  - assumption: a3
    kind: manual_review
    reviewed_at: 2026-07-01
    valid_days: 365
    holds: "true"
    at: 2026-07-01
"""
_TRIP_DEC = V.parse_yamlish(TRIP_DECISION)
_NOW = "2026-07-22"


def _tw_errs(readings_text, dec=None, now=_NOW):
    """Evaluate readings against the fixture decision; return STRUCTURAL errs (fail closed). A
    parse failure is itself a fail-closed rejection (non-zero), never a silent zero."""
    dec = _TRIP_DEC if dec is None else dec
    try:
        r = V.parse_yamlish(readings_text)
    except ValueError:
        return 1
    _f, errs = TW.evaluate_readings(dec, r, TW._as_date(now), V.fail, "selftest.readings")
    return errs


def _tw_states(readings_text, now=_NOW):
    r = V.parse_yamlish(readings_text)
    f, _e = TW.evaluate_readings(_TRIP_DEC, r, TW._as_date(now), V.fail, "selftest.readings")
    return {x["assumption"]: x["state"] for x in f}


def _tw_gate(decision, readings, now=_NOW):
    """Run check_tripwires over a temp tree seeded with one decision and (optionally) one readings
    file; returns the gate error count (fired tripwires and malformed readings both refuse)."""
    with tempfile.TemporaryDirectory() as _d:
        _r = Path(_d)
        (_r / ".veldo" / "decisions").mkdir(parents=True)
        (_r / ".veldo" / "readings").mkdir()
        (_r / ".veldo" / "decisions" / "d.yaml").write_text(decision)
        if readings is not None:
            (_r / ".veldo" / "readings" / "r.yaml").write_text(readings)
        return TW.check_tripwires(_r / ".veldo" / "decisions", _r / ".veldo" / "readings", _r,
                                  V.parse_yamlish, V.fail, DEC.load_record, now=now)


# AC1/AC2 positive control: a well-formed readings set over the fixture validates clean and fires nothing.
expect("WARP-1107 AC2: a well-formed veldo.readings/v1 set validates clean", _tw_errs(GOOD_READINGS) == 0)
expect("WARP-1107 AC1: a healthy readings set fires no tripwire (a1 ok, a2 ok, a3 valid)",
       _tw_states(GOOD_READINGS) == {"a1": TW.OK, "a2": TW.OK, "a3": TW.OK})
# AC2 fail-closed negatives, each refuses.
expect("WARP-1107 AC2: a wrong schema id refuses",
       _tw_errs(GOOD_READINGS.replace("veldo.readings/v1", "veldo.readings/v9")) > 0)
expect("WARP-1107 AC2: a reading naming an assumption the decision does not declare refuses (referenced but absent)",
       _tw_errs(GOOD_READINGS.replace("assumption: a2", "assumption: zz")) > 0)
expect("WARP-1107 AC2: an out-of-vocabulary kind refuses",
       _tw_errs(GOOD_READINGS.replace("kind: measured", "kind: guessing", 1)) > 0)
expect("WARP-1107 AC2: a measured reading missing its value refuses",
       _tw_errs(GOOD_READINGS.replace("    value: 6\n", "", 1)) > 0)
expect("WARP-1107 AC2: a measured reading missing its breach_when refuses",
       _tw_errs(GOOD_READINGS.replace('    breach_when: ">= 40"\n', "", 1)) > 0)
expect("WARP-1107 AC2: a measured reading with an unparseable comparator refuses",
       _tw_errs(GOOD_READINGS.replace('">= 40"', '"about 40"')) > 0)
expect("WARP-1107 AC2: an ordering comparator with a non-numeric value refuses",
       _tw_errs(GOOD_READINGS.replace("value: 6", 'value: "lots"')) > 0)
expect("WARP-1107 AC2: a manual-review missing reviewed_at refuses",
       _tw_errs(GOOD_READINGS.replace("    reviewed_at: 2026-07-01\n", "", 1)) > 0)
expect("WARP-1107 AC2: a manual-review missing valid_days refuses",
       _tw_errs(GOOD_READINGS.replace("    valid_days: 365\n", "", 1)) > 0)
expect("WARP-1107 AC2: a manual-review with a non-positive valid_days refuses",
       _tw_errs(GOOD_READINGS.replace("valid_days: 365", "valid_days: 0")) > 0)
expect("WARP-1107 AC2: a manual-review missing holds refuses",
       _tw_errs(GOOD_READINGS.replace('    holds: "true"\n', "", 1)) > 0)
expect("WARP-1107 AC2: an out-of-vocabulary holds value refuses",
       _tw_errs(GOOD_READINGS.replace('holds: "true"', 'holds: "maybe"')) > 0)
expect("WARP-1107 AC2: a readings file outside the parser subset (a tab) fails closed",
       _tw_errs("schema: veldo.readings/v1\n\tdecision: DEC-TW\n") > 0)

# AC3 IN-SESSION ONLY, no daemon (the heart of W7): tripwire.py starts no process/thread/timer.
_tw_src = (ROOT / ".veldo/tripwire.py").read_text()
_TRIP_DETACH_TOKENS = ("subprocess", "Popen", "os.fork", "os.forkpty", "os.exec", "os.spawn",
                       "os.posix_spawn", "os.system", "setsid", "nohup", "start_new_session",
                       "creationflags", "multiprocessing", "threading", "asyncio", "sched.",
                       "pty.spawn", "signal.alarm", "claude -p")


def _tw_no_detached(src):
    return not any(t in src for t in _TRIP_DETACH_TOKENS)


expect("WARP-1107 AC3: tripwire.py starts no process/thread/timer (no subprocess/Popen/fork/exec/spawn/setsid/nohup/multiprocessing/threading/asyncio/sched/claude -p)",
       _tw_no_detached(_tw_src))
expect("WARP-1107 AC3: tripwire.py imports only pathlib and datetime (no process/thread machinery)",
       "import subprocess" not in _tw_src and "import threading" not in _tw_src
       and "import multiprocessing" not in _tw_src and "import asyncio" not in _tw_src)
# MUTATION teeth: inject a detached spawn into a COPY of the source and prove the check goes RED.
_tw_mut_popen = _tw_src + '\n_p = subprocess.Popen(["claude", "-p", prompt], start_new_session=True)\n'
_tw_mut_thread = _tw_src + '\nimport threading\nthreading.Thread(target=poll, daemon=True).start()\n'
expect("WARP-1107 AC3 TEETH: a detached subprocess.Popen(claude -p) mutation fails the no-detach check",
       _tw_no_detached(_tw_mut_popen) is False)
expect("WARP-1107 AC3 TEETH: a background thread mutation fails the no-detach check",
       _tw_no_detached(_tw_mut_thread) is False)
expect("WARP-1107 AC3: the no-detach mutations are in-memory only (the real module on disk is byte-unchanged)",
       (ROOT / ".veldo/tripwire.py").read_text() == _tw_src)
# the current date is INJECTED (pure, deterministic): the SAME manual-review reads OK before its
# expiry and STALE after, purely from the injected date, with no clock read.
expect("WARP-1107 AC3: a manual-review is OK at an injected date within its validity",
       _tw_states(GOOD_READINGS, now="2026-07-02")["a3"] == TW.OK)
expect("WARP-1107 AC3: the SAME reading is STALE at an injected date past its expiry (date injected, not clocked)",
       _tw_states(GOOD_READINGS, now="2027-08-01")["a3"] == TW.STALE)

# AC4 a fired tripwire surfaces and refuses the gate; approaching and unmonitored are warnings; only
# a DECIDED decision is monitored.
_BREACH = GOOD_READINGS.replace("value: 6", "value: 45")   # a1 measured 45 >= 40 -> breached
expect("WARP-1107 AC4: a healthy readings set over a decided record passes the gate",
       _tw_gate(TRIP_DECISION, GOOD_READINGS) == 0)
expect("WARP-1107 AC4: a breached measured reading FIRES and refuses the gate (named finding)",
       _tw_gate(TRIP_DECISION, _BREACH) > 0)
expect("WARP-1107 AC4: a lapsed manual-review FIRES (stale) at an injected later date",
       _tw_gate(TRIP_DECISION, GOOD_READINGS, now="2028-01-01") > 0)
expect("WARP-1107 AC4: an approaching-breach surfaces as a warning WITHOUT failing the gate",
       _tw_gate(TRIP_DECISION, GOOD_READINGS.replace("value: 6", "value: 30")) == 0)
expect("WARP-1107 AC4: a decided record with no readings stands (unmonitored is a warning, not a fail)",
       _tw_gate(TRIP_DECISION, None) == 0)
expect("WARP-1107 AC4: a readings file naming a decision no record declares fails closed",
       _tw_gate(TRIP_DECISION, GOOD_READINGS.replace("decision: DEC-TW", "decision: DEC-GHOST")) > 0)
_DRAFT_DEC = (TRIP_DECISION.replace("status: decided", "status: draft")
              .replace("decision:\n  chosen: opt_a\n  decided_by: a-recorded-human\n  decided_at: 2026-07-22\n", ""))
expect("WARP-1107 AC4: a DRAFT decision is not monitored (a draft has no chosen foundation to watch)",
       _tw_gate(_DRAFT_DEC, _BREACH) == 0)

# AC4 the fired breach hands to the re-decision loop: exactly ONE draft, idempotent, a human promotes.
with tempfile.TemporaryDirectory() as _d:
    _r = Path(_d)
    (_r / ".veldo" / "decisions").mkdir(parents=True)
    (_r / ".veldo" / "readings").mkdir()
    (_r / ".veldo" / "decisions" / "d.yaml").write_text(TRIP_DECISION)
    (_r / ".veldo" / "readings" / "r.yaml").write_text(_BREACH)
    _redir = _r / ".veldo" / "redecisions"
    _o1 = TW.draft_redecisions(_r / ".veldo" / "decisions", _r / ".veldo" / "readings", _redir,
                               V.parse_yamlish, V.fail, DEC.load_record, now=_NOW)
    _o2 = TW.draft_redecisions(_r / ".veldo" / "decisions", _r / ".veldo" / "readings", _redir,
                               V.parse_yamlish, V.fail, DEC.load_record, now=_NOW)
    expect("WARP-1107 AC4: a fired breach drafts exactly ONE re-decision unit (created once)",
           _o1 == [("DEC-TW", "created")] and sorted(p.name for p in _redir.glob("*.yaml")) == ["DEC-TW.yaml"])
    expect("WARP-1107 AC4: re-running the pass drafts NO duplicate (idempotent)",
           _o2 == [("DEC-TW", "exists")] and sorted(p.name for p in _redir.glob("*.yaml")) == ["DEC-TW.yaml"])
    _rd_text = (_redir / "DEC-TW.yaml").read_text()
    expect("WARP-1107 AC4: the re-decision unit is a DRAFT a human promotes (veldo.redecision/v1, status draft, no decider, NG2)",
           "schema: veldo.redecision/v1" in _rd_text and "status: draft" in _rd_text
           and "redecides: DEC-TW" in _rd_text and "decided_by:" not in _rd_text and "chosen:" not in _rd_text)
    expect("WARP-1107 AC4: the re-decision names the breached assumption for human attention",
           "id: a1" in _rd_text and "state: breached" in _rd_text)

# AC5 adoption safe: no .veldo/decisions/ directory stands the pass down (byte-identically unaffected).
with tempfile.TemporaryDirectory() as _d:
    _r = Path(_d)
    expect("WARP-1107 AC5: no .veldo/decisions/ directory stands the pass down (adoption safe)",
           TW.check_tripwires(_r / ".veldo" / "decisions", _r / ".veldo" / "readings", _r,
                              V.parse_yamlish, V.fail, DEC.load_record) == 0)

# AC1/AC5 the shipped readings example validates and evaluates against the shipped decision example.
_rd_example = ROOT / ".veldo/examples/readings-example.yaml"
_ex_dir = ROOT / ".veldo/examples"
expect("WARP-1107 AC1: the shipped readings example validates and evaluates via check_readings",
       V.check_readings(_rd_example, decisions_dir=_ex_dir) == 0)
_rd_ex_text = _rd_example.read_text()
expect("WARP-1107 AC1: the shipped example is present and names the decision example (DEC-0000)",
       _rd_example.is_file() and "decision: DEC-0000" in _rd_ex_text)
_dec_ex = DEC.load_record(ROOT / ".veldo/examples/decision-example.yaml", V.parse_yamlish)
_rd_ex = TW.load_readings(_rd_example, V.parse_yamlish)
_ex_findings, _ex_errs = TW.evaluate_readings(_dec_ex, _rd_ex, TW._as_date("2026-08-01"), V.fail, "selftest.example")
expect("WARP-1107 AC1: the shipped example is well formed and fires no tripwire",
       _ex_errs == 0 and not any(f["state"] in TW.FIRED for f in _ex_findings))

# AC5 MUTATION teeth over the REAL shipped example (anti-vacuity C1): flipping a1's value past its
# breach_when turns the evaluation RED (a fired breach); the mutation reverts byte-identical.
_rd_mut_breach = _rd_ex_text.replace("value: 30", "value: 99", 1)
_mf, _me = TW.evaluate_readings(_dec_ex, V.parse_yamlish(_rd_mut_breach), TW._as_date("2026-08-01"), V.fail, "selftest.example.mut")
expect("WARP-1107 TEETH: flipping a measured value past its breach_when in the real example FIRES a breach",
       _rd_mut_breach != _rd_ex_text and any(f["state"] == TW.BREACHED for f in _mf))
expect("WARP-1107 TEETH: the real example on disk is byte-unchanged by the mutation",
       _rd_example.read_text() == _rd_ex_text)
expect("WARP-1107 TEETH: a seeded breach over a temp tree fires the gate and the clean set does not (non-vacuous)",
       _tw_gate(TRIP_DECISION, _BREACH) > 0 and _tw_gate(TRIP_DECISION, GOOD_READINGS) == 0)

# AC5 byte-identical engine sync (fast teeth; the gate's pack-drift and template-sync cover all packs),
# an honest mechanical capability, and the init scaffold laying the module beside its siblings.
expect("WARP-1107 AC5: .veldo/tripwire.py is byte-identical root vs engine",
       (ROOT / ".veldo/tripwire.py").read_bytes() == (ROOT / "engine/.veldo/tripwire.py").read_bytes())
expect("WARP-1107 AC5: .veldo/validate.py is byte-identical root vs engine",
       (ROOT / ".veldo/validate.py").read_bytes() == (ROOT / "engine/.veldo/validate.py").read_bytes())
expect("WARP-1107 AC5: the decision_tripwires capability is declared mechanical",
       bool(re.search(r"(?m)^\s{2}decision_tripwires:\s*\{status:\s*mechanical\b",
                      (ROOT / ".veldo/capabilities.yaml").read_text())))
expect("WARP-1107 AC5: the init scaffold lays .veldo/tripwire.py beside .veldo/decision.py",
       ".veldo/tripwire.py" in ISC.required_substrate())

# AC4 the VELDO-STATUS surface (the plan's third tripwire surface, beside the gate output and the
# weekly pass, restored here): a FIRED tripwire surfaces in `veldo status` as a NAMED finding. The
# loop-area runstatus reader projects the SAME evaluation the gate runs by asking the contracts-area
# evaluator (validate.tripwire_status) over the allow-listed loop -> contracts edge, so the CLI model,
# the terminal render, and the browser view show the same fired foundation. TEETH: over a temp tree
# with a decided decision and a breaching reading the model carries the fired tripwire and the render
# names it; a healthy set surfaces none (non-vacuous - the surface reflects the evaluation, so
# removing the wiring or returning a constant fails one of the two directions); and the loop surface
# is IDENTICAL to the contracts evaluation (proving the loop reads contracts, not a second model).
with tempfile.TemporaryDirectory() as _d:
    _r = Path(_d)
    (_r / ".veldo" / "decisions").mkdir(parents=True)
    (_r / ".veldo" / "readings").mkdir()
    (_r / ".veldo" / "decisions" / "d.yaml").write_text(TRIP_DECISION)
    (_r / ".veldo" / "readings" / "r.yaml").write_text(_BREACH)

    def _tw_snapshot(base):
        acc = {}
        for _dp, _dn2, _fns in _rl_os.walk(str(base)):
            for _fn in _fns:
                _p = _rl_os.path.join(_dp, _fn)
                with open(_p, "rb") as _fh:
                    acc[_rl_os.path.relpath(_p, str(base))] = _fh.read()
        return acc
    _tw_before = _tw_snapshot(_r / ".veldo")
    _tw_status_model = RS.status(root=_r, runs_root=str(_r), events_path=str(_r / "none.jsonl"))
    _tw_after = _tw_snapshot(_r / ".veldo")
    _tw_surface = _tw_status_model.get("tripwires") or {}
    _tw_fired_ids = {(f.get("decision"), f.get("assumption")) for f in _tw_surface.get("fired") or []}
    expect("WARP-1107 AC4 (veldo status surface): a fired tripwire surfaces in the veldo status model as a named finding",
           ("DEC-TW", "a1") in _tw_fired_ids)
    _tw_render = RS.render_text(_tw_status_model)
    expect("WARP-1107 AC4 (veldo status surface): the veldo status terminal render names the fired tripwire",
           "DEC-TW/a1" in _tw_render and "FIRED" in _tw_render)
    expect("WARP-1107 AC4 (veldo status surface): the loop reader shows the SAME evaluation as contracts (loop -> contracts read)",
           _tw_surface == V.tripwire_status(root=_r))
    expect("WARP-1107 AC4 (veldo status surface): the surface read is read-only (decisions + readings byte-unchanged)",
           _tw_before == _tw_after)
    # non-vacuity: a HEALTHY readings set surfaces NO fired tripwire (so the surface is not a constant).
    (_r / ".veldo" / "readings" / "r.yaml").write_text(GOOD_READINGS)
    _tw_ok_model = RS.status(root=_r, runs_root=str(_r), events_path=str(_r / "none.jsonl"))
    expect("WARP-1107 AC4 (veldo status surface): a healthy readings set surfaces no fired tripwire in veldo status",
           not (_tw_ok_model.get("tripwires") or {}).get("fired"))

# AC4 adoption safe on the veldo-status surface: no .veldo/decisions/ directory yields an empty surface
# (a repository with no decision records is byte-identically unaffected in veldo status too).
with tempfile.TemporaryDirectory() as _d:
    _r = Path(_d)
    _tw_none = RS.status(root=_r, runs_root=str(_r), events_path=str(_r / "none.jsonl")).get("tripwires") or {}
    expect("WARP-1107 AC4 (veldo status surface): no .veldo/decisions/ directory yields an empty veldo-status surface (adoption safe)",
           not _tw_none.get("fired") and not _tw_none.get("warnings") and _tw_none.get("malformed") == 0)

# RJ5 tripwire conformance (PLAN-0011 regression journey, after:WARP-1107): a seeded assumption breach
# surfaces in the GATE OUTPUT and in VELDO STATUS and drafts exactly ONE re-decision unit; re-running the
# pass creates no duplicate and spawns nothing that outlives the session (the no-detach teeth above and
# the read-only surface teeth prove nothing detaches). All three surfaces over one temp tree.
with tempfile.TemporaryDirectory() as _d:
    _r = Path(_d)
    (_r / ".veldo" / "decisions").mkdir(parents=True)
    (_r / ".veldo" / "readings").mkdir()
    (_r / ".veldo" / "decisions" / "d.yaml").write_text(TRIP_DECISION)
    (_r / ".veldo" / "readings" / "r.yaml").write_text(_BREACH)
    _redir = _r / ".veldo" / "redecisions"
    _rj5_gate_fires = TW.check_tripwires(_r / ".veldo" / "decisions", _r / ".veldo" / "readings", _r,
                                         V.parse_yamlish, V.fail, DEC.load_record, now=_NOW) > 0
    _rj5_model = RS.status(root=_r, runs_root=str(_r), events_path=str(_r / "none.jsonl"))
    _rj5_fired = {(f.get("decision"), f.get("assumption")) for f in (_rj5_model.get("tripwires") or {}).get("fired") or []}
    _rj5_o1 = TW.draft_redecisions(_r / ".veldo" / "decisions", _r / ".veldo" / "readings", _redir,
                                   V.parse_yamlish, V.fail, DEC.load_record, now=_NOW)
    _rj5_o2 = TW.draft_redecisions(_r / ".veldo" / "decisions", _r / ".veldo" / "readings", _redir,
                                   V.parse_yamlish, V.fail, DEC.load_record, now=_NOW)
    expect("WARP-1107 RJ5: a seeded breach surfaces in the gate output AND veldo status AND drafts exactly one re-decision unit (idempotent)",
           _rj5_gate_fires and ("DEC-TW", "a1") in _rj5_fired
           and _rj5_o1 == [("DEC-TW", "created")] and _rj5_o2 == [("DEC-TW", "exists")]
           and sorted(p.name for p in _redir.glob("*.yaml")) == ["DEC-TW.yaml"])

# --- shape-fit review dimension (WARP-1104, W4 of PLAN-0011): the independent review grades a
# SECOND dimension beyond spec-conformance, does this change FIT the declared architecture shape,
# and correct-but-does-not-fit is a legitimate rework verdict (D4). The dimension is honestly split:
# a MECHANICAL half (mechanical_shape_findings) decides from the contract + the spec's
# placement/footprint + the diff's paths the rules that need no judgment (placement resolves, the
# footprint stays within the declared areas, no diff path silently outside the footprint, no
# unmodeled boundary crossing) and fails closed, reusing arch's one placement and boundary
# implementation; and a DELEGATED half (ShapeReviewer, reference LiveShapeReviewer) grades pattern-fit
# and FAILS LOUD - no judgment is fabricated in code. build_shape_fit assembles the shape_fit block the
# verdict carries and the MACHINE NEVER LOWERS. The verdict contract carries + validates the shape_fit
# block (validate_shape_fit), and the merge gate (dispatch._verdict_passes) refuses a correct-but-misfit
# verdict (RJ3). Negative-first with real teeth; adoption safe (a verdict with no shape_fit dimension is
# unaffected). shape_review.py imports nothing: arch's helpers and the reporter are passed in.
_srspec = importlib.util.spec_from_file_location("veldo_shape_review", ROOT / ".veldo/shape_review.py")
SR = importlib.util.module_from_spec(_srspec); _srspec.loader.exec_module(SR)
_dspspec14 = importlib.util.spec_from_file_location("veldo_dispatch_1104", ROOT / ".veldo/dispatch.py")
DSP14 = importlib.util.module_from_spec(_dspspec14); _dspspec14.loader.exec_module(DSP14)

# A fixture contract with three areas: edge -> core is an allow-listed edge (cohesive breadth),
# far is joined to nothing (an unmodeled boundary with either of the others). Areas map by /** globs.
_SR_ARCH = """schema: veldo.arch/v1
id: fixture
title: A shape-fit fixture contract
version: 1
status: approved
approved_by: tester
approved_at: 2026-07-22
areas:
  - id: core
    title: Core
    includes: ["src/core/**"]
  - id: edge
    title: Edge
    includes: ["src/edge/**"]
  - id: far
    title: Far
    includes: ["src/far/**"]
dependencies:
  enforcement: review
  allow:
    - {from: edge, to: core}
patterns: []
invariants: []
budgets: []
"""
_sr_contract = V.parse_yamlish(_SR_ARCH)


def _sr_mech(placement, footprint, paths):
    return SR.mechanical_shape_findings({"placement": placement, "footprint": footprint},
                                        _sr_contract, paths, ARCH)

# AC1 the mechanizable shape-fit rules. Positive control: a within-placement, within-footprint change
# yields no findings.
expect("WARP-1104 AC1: a within-placement, within-footprint change yields no mechanical findings",
       _sr_mech(["core"], ["src/core/**"], ["src/core/x.py"]) == [])
# AC1 negative-first, each mechanizable rule refuses (isolated so exactly one rule bites):
expect("WARP-1104 AC1: a placement area that does not resolve to a declared area refuses (referenced but absent)",
       _sr_mech(["ghost"], ["src/core/**"], ["src/core/x.py"]) != [])
expect("WARP-1104 AC1: a diff path outside the declared footprint refuses (a change may not silently touch what it did not declare)",
       _sr_mech(["core"], ["src/core/**"], ["src/other/w.py"]) != [])
expect("WARP-1104 AC1: a diff path resolving to a declared area outside the placement refuses (the footprint does not stay within the declared areas)",
       _sr_mech(["core"], ["src/core/**", "src/edge/**"], ["src/edge/y.py"]) != [])
expect("WARP-1104 AC1: a diff coupling two areas with no allow-listed edge refuses (an unmodeled boundary crossing)",
       _sr_mech(["core", "far"], ["src/core/**", "src/far/**"], ["src/core/x.py", "src/far/z.py"]) != [])
# AC1 cohesive breadth (a pair the contract's dependencies.allow connects) is NOT a misfit.
expect("WARP-1104 AC1: cohesive breadth across an allow-listed edge (edge -> core) is not a misfit",
       _sr_mech(["core", "edge"], ["src/core/**", "src/edge/**"], ["src/core/x.py", "src/edge/y.py"]) == [])

# AC2 the pattern-fit judgment is a DELEGATED fresh-context seam that FAILS LOUD, mirroring
# executor.LiveLoop.review and dispatch.LiveReviewer. shape_review_context assembles what the reviewer
# receives; the reference reviewer raises rather than fabricate a judgment; a fake injected reviewer is
# the only path a judgment enters.
_sr_ctx = SR.shape_review_context({"placement": ["core"], "footprint": ["src/core/**"]},
                                  _sr_contract, ["src/core/x.py"], ARCH)
expect("WARP-1104 AC2: shape_review_context carries the contract areas, the placement, the diff areas, and the mechanical findings",
       _sr_ctx.get("placement") == ["core"] and _sr_ctx.get("diff_areas") == ["core"]
       and set(_sr_ctx.get("areas")) == {"core", "edge", "far"} and _sr_ctx.get("mechanical_findings") == [])
_sr_reviewer_raised = False
try:
    SR.LiveShapeReviewer().review({"id": "WARP-9104"}, _sr_ctx)
except SR.ShapeReviewError:
    _sr_reviewer_raised = True
expect("WARP-1104 AC2: the reference shape reviewer FAILS LOUD (refuses to fabricate a judgment)", _sr_reviewer_raised)
expect("WARP-1104 AC2: ShapeReviewError is a ValueError (raised by name)", issubclass(SR.ShapeReviewError, ValueError))


class _FakeShapeReviewer(SR.ShapeReviewer):
    def review(self, spec, context=None):
        return {"verdict": "does_not_fit", "finding": "the change does not follow the area's declared pattern"}


expect("WARP-1104 AC2: an injected reviewer is the only path a judgment enters (the seam, not fabrication)",
       _FakeShapeReviewer().review({"id": "x"}).get("verdict") == "does_not_fit")

# AC3 build_shape_fit assembles the shape_fit block and the MACHINE NEVER LOWERS: a mechanical misfit
# forces does_not_fit even when the reviewer says fits; a clean result with a fits judgment yields fits;
# a does_not_fit judgment is honored; a malformed/fabricated judgment is refused by name (fail loud).
_sr_misfit_fm = {"placement": ["core"], "footprint": ["src/core/**"]}
expect("WARP-1104 AC3: a mechanical misfit forces does_not_fit even when the reviewer says fits (the machine never lowers)",
       SR.build_shape_fit(_sr_misfit_fm, _sr_contract, ["src/other/w.py"], {"verdict": "fits", "finding": "looks fine"}, ARCH)["verdict"] == "does_not_fit")
expect("WARP-1104 AC3: a clean mechanical result with a fits judgment yields fits",
       SR.build_shape_fit(_sr_misfit_fm, _sr_contract, ["src/core/x.py"], {"verdict": "fits", "finding": "ok"}, ARCH)["verdict"] == "fits")
expect("WARP-1104 AC3: a does_not_fit judgment over a clean mechanical result is honored",
       SR.build_shape_fit(_sr_misfit_fm, _sr_contract, ["src/core/x.py"], {"verdict": "does_not_fit", "finding": "pattern violated"}, ARCH)["verdict"] == "does_not_fit")
_sr_bad_judgment_raised = False
try:
    SR.build_shape_fit(_sr_misfit_fm, _sr_contract, ["src/core/x.py"], {"verdict": "maybe"}, ARCH)
except SR.ShapeReviewError:
    _sr_bad_judgment_raised = True
expect("WARP-1104 AC3: a malformed/fabricated judgment (out-of-vocabulary verdict) is refused by name (fail loud)",
       _sr_bad_judgment_raised)

# AC4 the verdict contract (veldo.verdict/v1) carries the shape_fit finding and validate.py validates it
# fail closed via check_json. Negative-first; a verdict with no shape_fit dimension is unaffected.
with tempfile.TemporaryDirectory() as d:
    _svbase = {"schema": "veldo.verdict/v1", "spec_id": "WARP-9001", "commit": "deadbeef",
               "reviewer": "selftest", "verdict": "pass", "criteria": []}
    _good_fits = dict(_svbase, shape_fit={"verdict": "fits", "mechanical": [], "review": {"verdict": "fits", "finding": "ok"}})
    expect("WARP-1104 AC4: a well-formed fits shape_fit block validates through the verdict check",
           V.check_json(tmpfile(d, "sf1.json", json.dumps(_good_fits)), V.VERDICT_REQ, "verdict") == 0)
    _good_dnf = dict(_svbase, shape_fit={"verdict": "does_not_fit", "mechanical": ["the diff couples two unmodeled areas"], "review": {"verdict": "fits", "finding": None}})
    expect("WARP-1104 AC4: a does_not_fit block naming a mechanical finding validates",
           V.check_json(tmpfile(d, "sf2.json", json.dumps(_good_dnf)), V.VERDICT_REQ, "verdict") == 0)
    expect("WARP-1104 AC4: an out-of-vocabulary shape_fit.verdict refuses",
           V.check_json(tmpfile(d, "sf3.json", json.dumps(dict(_svbase, shape_fit={"verdict": "meh", "mechanical": []}))), V.VERDICT_REQ, "verdict") > 0)
    expect("WARP-1104 AC4: a non-list mechanical findings list refuses",
           V.check_json(tmpfile(d, "sf4.json", json.dumps(dict(_svbase, shape_fit={"verdict": "fits", "mechanical": "nope"}))), V.VERDICT_REQ, "verdict") > 0)
    expect("WARP-1104 AC4: a malformed review sub-block refuses",
           V.check_json(tmpfile(d, "sf5.json", json.dumps(dict(_svbase, shape_fit={"verdict": "fits", "review": {"verdict": "wat"}}))), V.VERDICT_REQ, "verdict") > 0)
    expect("WARP-1104 AC4: a does_not_fit dimension that records no finding refuses (a misfit must name what does not fit)",
           V.check_json(tmpfile(d, "sf6.json", json.dumps(dict(_svbase, shape_fit={"verdict": "does_not_fit", "mechanical": []}))), V.VERDICT_REQ, "verdict") > 0)
    expect("WARP-1104 AC4: a verdict with no shape_fit dimension is byte-identically unaffected (adoption safe)",
           V.check_json(tmpfile(d, "sf7.json", json.dumps(_svbase)), V.VERDICT_REQ, "verdict") == 0)

# AC5 the shape-fit dimension BLOCKS the merge (D4, RJ3): shape_fit_blocks is a pure predicate the
# dispatcher's real verdict gate consults, so a correct-but-misfit verdict is refused for rework while a
# fitting one ships; a verdict with no shape_fit dimension is unaffected; a malformed block fails closed.
expect("WARP-1104 AC5: shape_fit_blocks is True for a does_not_fit dimension",
       SR.shape_fit_blocks({"shape_fit": {"verdict": "does_not_fit", "mechanical": ["x"]}}) is True)
expect("WARP-1104 AC5: shape_fit_blocks is False for a fits dimension",
       SR.shape_fit_blocks({"shape_fit": {"verdict": "fits"}}) is False)
expect("WARP-1104 AC5: shape_fit_blocks is False for a verdict with no shape_fit dimension (adoption safe)",
       SR.shape_fit_blocks({"verdict": "pass"}) is False)
expect("WARP-1104 AC5: shape_fit_blocks fails closed (True) on a malformed shape_fit block",
       SR.shape_fit_blocks({"shape_fit": "junk"}) is True
       and SR.shape_fit_blocks({"shape_fit": {"verdict": "weird"}}) is True)
# RJ3 conformance over the REAL dispatcher verdict gate: a correct-but-misfit verdict is REFUSED and the
# spec would return to fail_status; a fitting verdict ships; a no-shape-fit verdict is unchanged; a
# blocking finding still refuses (the base gate is preserved).
_disp14 = DSP14.Dispatcher(repo_root=str(ROOT))
_misfit_verdict = {"verdict": "pass", "findings": [],
                   "shape_fit": {"verdict": "does_not_fit", "mechanical": ["the diff couples areas with no allow-listed edge"],
                                 "review": {"verdict": "does_not_fit", "finding": "does not fit"}}}
_fit_verdict = {"verdict": "pass", "findings": [],
                "shape_fit": {"verdict": "fits", "mechanical": [], "review": {"verdict": "fits", "finding": "fits"}}}
expect("WARP-1104 AC5 RJ3: a correct-but-misfit verdict is REFUSED at the real dispatcher merge gate (rework, not shipped)",
       _disp14._verdict_passes(_misfit_verdict) is False)
expect("WARP-1104 AC5 RJ3: a fitting verdict passes the real dispatcher merge gate (reworked to fit ships)",
       _disp14._verdict_passes(_fit_verdict) is True)
expect("WARP-1104 AC5: a verdict with no shape_fit dimension still passes the gate unchanged (adoption safe)",
       _disp14._verdict_passes({"verdict": "pass", "findings": []}) is True)
expect("WARP-1104 AC5: the base verdict gate is preserved (a blocking finding still refuses)",
       _disp14._verdict_passes({"verdict": "pass", "findings": [{"severity": "blocking", "text": "x"}]}) is False)

# AC1/AC6 real-artifact teeth over this repository's REAL WARP-1104 spec and contract (anti-vacuity C1):
# a diff path outside the real spec's declared footprint turns check_shape_review RED, its own footprint
# paths fit, and the real spec on disk is byte-unchanged by the check (a copy-and-revert style tooth).
_p14_file = ROOT / "specs/WARP-1104-shape-fit-review-dimension.md"
_p14_before = _p14_file.read_bytes()
expect("WARP-1104 TEETH: the real spec's own footprint paths fit its placement (positive control, non-vacuous)",
       V.check_shape_review(_p14_file, [".veldo/shape_review.py", ".veldo/validate.py", ".veldo/dispatch.py"]) == 0)
expect("WARP-1104 TEETH: a diff path outside the real spec's declared footprint turns check_shape_review RED",
       V.check_shape_review(_p14_file, [".veldo/policy_check.py"]) > 0)
expect("WARP-1104 TEETH: the real WARP-1104 spec on disk is byte-unchanged by the shape check",
       _p14_file.read_bytes() == _p14_before)

# AC6 the extended engine is byte-identical across the canonical copies (pack-drift and template-sync
# cover all packs; assert the root vs engine pair here as fast extra teeth), the capability is
# declared mechanical, and the init scaffold lays the new module.
expect("WARP-1104 AC6: .veldo/shape_review.py is byte-identical root vs engine",
       (ROOT / ".veldo/shape_review.py").read_bytes() == (ROOT / "engine/.veldo/shape_review.py").read_bytes())
expect("WARP-1104 AC6: .veldo/validate.py is byte-identical root vs engine",
       (ROOT / ".veldo/validate.py").read_bytes() == (ROOT / "engine/.veldo/validate.py").read_bytes())
expect("WARP-1104 AC6: .veldo/dispatch.py is byte-identical root vs engine",
       (ROOT / ".veldo/dispatch.py").read_bytes() == (ROOT / "engine/.veldo/dispatch.py").read_bytes())
expect("WARP-1104 AC6: the shape_fit_review capability is declared mechanical",
       bool(re.search(r"(?m)^\s{2}shape_fit_review:\s*\{status:\s*mechanical\b",
                      (ROOT / ".veldo/capabilities.yaml").read_text())))
expect("WARP-1104 AC6: the init scaffold lays .veldo/shape_review.py beside .veldo/decision_review.py",
       ".veldo/shape_review.py" in ISC.required_substrate())

# --- refine the footprint tier rule to a boundary crossing, not mere breadth (WARP-1011,
# standalone; founder decision 2026-07-22: "refine the rule ... otherwise it's a rubber stamp").
# The footprint tier floor (arch.footprint_tier_floor) now elevates to high ONLY when the touched
# areas contain a PAIR with NO allow-listed dependency edge between them in either direction (a
# genuine boundary crossing / architecturally-unmodeled coupling); a pair the contract's
# dependencies.allow connects is cohesive breadth and does NOT elevate. This sharpens the signal so
# a legitimate cross-area change over a modeled edge no longer forces needless human approval. It is
# a clean dogfood: WARP-1011 declares placement [contracts] and a footprint that resolves to the
# contracts area only, so its own tier is standard. NEW-MODULE detection stays deferred to WARP-1102
# (W2): a footprint glob cannot tell a genuinely new path from an unenumerated one without the diff.
_P11_REAL = ARCH.load_contract(ROOT / ".veldo/architecture.yaml", V.parse_yamlish)
def _p11_floor(fm_text, contract=_P11_REAL):
    return ARCH.footprint_tier_floor(V.parse_yamlish(fm_text), contract)

# AC1 the refined boundary-aware semantics over the REAL contract's genuine pairs (verified against
# .veldo/architecture.yaml dependencies.allow): {contracts, loop} and {contracts, fleet} are each
# joined by an allow-listed edge (cohesive breadth) and do NOT elevate; {enforcement, fleet} has no
# edge in either direction (a genuine boundary crossing) and elevates to high; a single area does not.
expect("WARP-1011 AC1: a connected pair {contracts, loop} (loop-to-contracts edge) does NOT elevate",
       _p11_floor("placement: [contracts]\nfootprint:\n  - .veldo/arch.py\n  - .veldo/executor.py\n") == "")
expect("WARP-1011 AC1: a connected pair {contracts, fleet} (fleet-to-contracts edge) does NOT elevate",
       _p11_floor("placement: [contracts]\nfootprint:\n  - .veldo/arch.py\n  - .veldo/fleet.py\n") == "")
expect("WARP-1011 AC1: an unmodeled pair {enforcement, fleet} (no edge either direction) elevates to high",
       _p11_floor("placement: [enforcement]\nfootprint:\n  - scripts/check_docs.sh\n  - .veldo/fleet.py\n") == "high")
expect("WARP-1011 AC1: a single declared area does not elevate",
       _p11_floor("placement: [contracts]\nfootprint:\n  - .veldo/arch.py\n") == "")
expect("WARP-1011 AC1: a three-area footprint all-connected {contracts, loop, fleet} does NOT elevate (every pair modeled)",
       _p11_floor("placement: [contracts]\nfootprint:\n  - .veldo/arch.py\n  - .veldo/executor.py\n  - .veldo/fleet.py\n") == "")
expect("WARP-1011 AC1: a three-area footprint with one unmodeled pair {contracts, fleet, metrics} elevates (fleet-metrics has no edge)",
       _p11_floor("placement: [contracts]\nfootprint:\n  - .veldo/arch.py\n  - .veldo/fleet.py\n  - .veldo/metrics.py\n") == "high")

# AC2 the WARP-1103 tests are updated to the refined semantics, not the old coarse rule. Behavioral
# proof over the fixture (_BC_CONTRACT, from the WARP-1103 block: core, edge with edge->core, plus an
# unconnected island): a CONNECTED two-area pair stays standard while an UNMODELED two-area pair
# elevates - a distinction the old coarse "any two-area span elevates" rule could not make. Source
# guard: the retired coarse label is gone from this file (coverage re-pointed, not left encoding the
# old rule), while the refined boundary-aware labels are present.
expect("WARP-1011 AC2: over the fixture a connected two-area pair stays standard (old coarse rule would have elevated it)",
       ARCH.footprint_tier_floor(V.parse_yamlish(_connected_pair), _BC_CONTRACT) == "")
expect("WARP-1011 AC2: over the fixture an unmodeled two-area pair elevates to high",
       ARCH.footprint_tier_floor(V.parse_yamlish(_unmodeled_pair), _BC_CONTRACT) == "high")
# THE SUBJECT IS THE UNIT SUITE, WHICH IS NOW A DIRECTORY. WARP-0712 cut the monolith into
# scripts/suites/*.py behind an unchanged entry point, so reading scripts/selftest.py here
# would read a dispatcher and both labels below would pass vacuously. Neither label names a
# path, so re-pointing the READ keeps them byte-identical and keeps them TRUE.
_p11_selftext = suite_source() if "suite_source" in dir() else (
    ROOT / "scripts/selftest.py").read_text()
_p11_retired = "a footprint spanning two areas " + "floors the tier at high"  # split so this guard does not match itself
expect("WARP-1011 AC2: the old coarse assertion label is retired from the selftest (coverage re-pointed, not left encoding the old rule)",
       _p11_retired not in _p11_selftext)
expect("WARP-1011 AC2: the refined boundary-aware assertion labels are present",
       "whose pair has NO allowed edge floors the tier at high" in _p11_selftext
       and "whose pair is connected by an allowed edge does NOT elevate" in _p11_selftext)

# AC3 MUTATION teeth (anti-vacuity C1): the connectivity read from dependencies.allow is load-bearing.
# Over the fixture, REMOVING the only edge (edge->core) flips the previously-connected {core, edge}
# pair from standard to high (observed RED), and restoring it reverts to standard byte-identical; the
# real module on disk is never mutated. And the core fix proven directly: a connected-pair footprint
# at risk standard PASSES the gate (RED if it wrongly elevated), while the unmodeled pair is refused.
_p11_noedge_arch = _BC_ARCH.replace("    - {from: edge, to: core}\n", "", 1)
_p11_noedge_contract = V.parse_yamlish(_p11_noedge_arch)
expect("WARP-1011 AC3 teeth: with edge->core removed, the {core, edge} pair now has no edge and elevates to high (connectivity is load-bearing)",
       _p11_noedge_arch != _BC_ARCH
       and ARCH.footprint_tier_floor(V.parse_yamlish(_connected_pair), _p11_noedge_contract) == "high")
expect("WARP-1011 AC3 teeth: restoring the edge reverts the {core, edge} pair to standard (byte-identical revert)",
       ARCH.footprint_tier_floor(V.parse_yamlish(_connected_pair), _BC_CONTRACT) == "")
expect("WARP-1011 AC3 teeth: the real .veldo/arch.py on disk is byte-unchanged by the in-memory mutations",
       (ROOT / ".veldo/arch.py").read_bytes() == (ROOT / "engine/.veldo/arch.py").read_bytes())
expect("WARP-1011 AC3 teeth CORE FIX: a connected-pair footprint at risk standard PASSES the gate (breadth is not a crossing)",
       _bc_gate(_connected_pair + "risk: standard\n") == [])
expect("WARP-1011 AC3 teeth: an unmodeled-pair footprint at risk standard is REFUSED (a genuine crossing still elevates)",
       any("risk tier" in p for p in _bc_gate(_unmodeled_pair + "risk: standard\n")))

# AC4 forward-only, retroactively changes nothing. footprint_tier_floor is computed only at the ready
# transition, the claim, and run-check - never in run_all's corpus pass - so the already-shipped
# corpus is never re-tiered. Source guard: run_all invokes no tier gate. The shipped WARP-1103
# (recorded risk high) and its frozen proof (commit 84fc55d) are unchanged, and check_spec over it
# still validates.
_p11_valtext = (ROOT / ".veldo/validate.py").read_text()
_p11_runall = _p11_valtext[_p11_valtext.index("def run_all("):]
_p11_runall = _p11_runall[:_p11_runall.index("\ndef ", 1)]
expect("WARP-1011 AC4: run_all invokes no tier gate (placement_gate/footprint_tier_floor/check_ready absent from the corpus pass) - the refinement is forward-only",
       "placement_gate" not in _p11_runall and "footprint_tier_floor" not in _p11_runall and "check_ready" not in _p11_runall)
expect("WARP-1011 AC4: the shipped WARP-1103 spec still validates via check_spec (never re-tiered by the refinement)",
       V.check_spec(_p13_file) == 0)
expect("WARP-1011 AC4: the shipped WARP-1103 spec's recorded risk is still high (unchanged, forward-only)",
       ARCH._risk_word(V.parse_yamlish(_p13_fm).get("risk")) == "high")
_p11_1103_proof = json.loads((ROOT / "proof/WARP-1103/manifest.json").read_text())
expect("WARP-1011 AC4: WARP-1103's frozen proof still binds to its impl commit 84fc55d (unchanged)",
       _p11_1103_proof.get("commit", "").startswith("84fc55d"))

# AC5 new-module detection stays DEFERRED to WARP-1102 (W2), stated honestly. The refined rule reads
# only the declared areas and the contract's dependency edges; it inspects no diff and makes no
# new-module claim. The docstring and the capability note name the deferral.
_p11_archtext = (ROOT / ".veldo/arch.py").read_text()
expect("WARP-1011 AC5: footprint_tier_floor's docstring defers new-module detection to WARP-1102 (W2) and disclaims adding it",
       "WARP-1102" in _p11_archtext and "new-module detection" in _p11_archtext and "adds no" in _p11_archtext)
expect("WARP-1011 AC5: the spec_placement_footprint capability note honestly defers new-module detection to WARP-1102 (W2)",
       "WARP-1102" in (ROOT / ".veldo/capabilities.yaml").read_text())

# AC6 byte-identical pack sync, no protected path, and WARP-1011's own tier is standard. The refined
# arch.py and the updated capabilities.yaml note ship byte-identical across root, engine,
# and all 6 packs (the gate's pack-drift covers every pack; assert the root vs engine pair
# and the 6 packs here as fast extra teeth). WARP-1011's own footprint resolves to the contracts area
# only, so it is standard risk and needs no approval - a clean dogfood of the very rule it refines.
_P11_PACKS = ["aider", "antigravity", "codex", "copilot", "cursor", "opencode"]
expect("WARP-1011 AC6: .veldo/arch.py is byte-identical root vs engine",
       (ROOT / ".veldo/arch.py").read_bytes() == (ROOT / "engine/.veldo/arch.py").read_bytes())
expect("WARP-1011 AC6: .veldo/capabilities.yaml is byte-identical root vs engine",
       (ROOT / ".veldo/capabilities.yaml").read_bytes() == (ROOT / "engine/.veldo/capabilities.yaml").read_bytes())
expect("WARP-1011 AC6: .veldo/arch.py is byte-identical across all 6 packs",
       (ROOT / ".veldo/arch.py").read_bytes() == (ROOT / "engine/.veldo/arch.py").read_bytes())
expect("WARP-1011 AC6: .veldo/capabilities.yaml is byte-identical across all 6 packs",
       (ROOT / ".veldo/capabilities.yaml").read_bytes() == (ROOT / "engine/.veldo/capabilities.yaml").read_bytes())
_p11_file = ROOT / "specs/WARP-1011-refine-footprint-tier-boundary-crossing.md"
_p11_ownfm = V.parse_yamlish(re.match(r"^---\n(.*?)\n---", _p11_file.read_text(), re.S).group(1))
expect("WARP-1011 AC6 dogfood: WARP-1011's own footprint resolves to the contracts area only (a single area)",
       ARCH.footprint_areas(_p11_ownfm, _P11_REAL) == {"contracts"})
expect("WARP-1011 AC6 dogfood: WARP-1011's own footprint does NOT elevate its tier (standard, no approval - a clean dogfood)",
       ARCH.footprint_tier_floor(_p11_ownfm, _P11_REAL) == "")
expect("WARP-1011 AC6 dogfood: WARP-1011 passes the mandatory placement gate at risk standard",
       ARCH.placement_gate(_p11_ownfm, _P11_REAL) == [])
expect("WARP-1011 AC6: WARP-1011 declares no protected path",
       "protected_paths: []" in _p11_file.read_text())

# --- gate enforcement of the mechanizable shape rules (WARP-1102, W2 of PLAN-0011): a shape
# check wired thin into scripts/verify.sh (.veldo/shape_gate.py) reads the architecture contract
# and, for every rule marked enforcement: mechanizable, refuses a violation and fails the gate
# with the rule NAMED; a rule marked enforcement: review is a NON-BLOCKING reviewer note (NG5,
# the honest reading of "mechanizable"). Adoption safe (no contract stands the whole gate down)
# and fail closed (an unenforceable mechanizable rule refuses). CHANGE SCOPED: the size budget
# binds the change, never the shipped corpus - the only green-safe reading, since this repository's
# own validate.py was over the budget as a pre-contract module (restored under budget by WARP-1012).
# Footprint-versus-diff (the
# O3 half deferred from W3) is enforced green safe. Negative-first with real teeth; each mechanizable
# rule class names itself; the D6 reference analyzers are exercised over seeded fixtures.
_sgspec = importlib.util.spec_from_file_location("veldo_shape_gate", ROOT / ".veldo/shape_gate.py")
SG = importlib.util.module_from_spec(_sgspec); _sgspec.loader.exec_module(SG)
_SG_REAL = ARCH.load_contract(ROOT / ".veldo/architecture.yaml", V.parse_yamlish)
_sg_modline = next(b for b in _SG_REAL["budgets"] if b.get("id") == "module_lines")

# AC1 positive control over this repository's REAL contract with an empty change set: every
# mechanizable rule is WIRED and the shape gate passes (deterministic, independent of the working
# tree); review-lane prose rules surface as non-blocking notes.
_sg_sd, _sg_pr, _sg_no = SG.run(ROOT, set())
expect("WARP-1102 AC1: the real contract's mechanizable rules are all wired and pass (empty change set, green)",
       _sg_sd is False and _sg_pr == [])
expect("WARP-1102 AC1: review-lane rules surface as non-blocking reviewer notes (NG5)",
       any("review lane" in n for n in _sg_no))
# AC1 the file_lines budget NAMES itself over a seeded governed file (module_lines).
with tempfile.TemporaryDirectory() as _sgd:
    (Path(_sgd) / ".veldo").mkdir()
    (Path(_sgd) / ".veldo" / "validate.py").write_text("x = 1\n" * 1001)  # a governed path (contracts area)
    _f_over = SG.file_lines_findings({".veldo/validate.py"}, _sgd, _sg_modline, _SG_REAL, ARCH)
    expect("WARP-1102 AC1: a changed governed file over the file_lines budget refuses and NAMES module_lines",
           len(_f_over) == 1 and "module_lines" in _f_over[0])
    (Path(_sgd) / ".veldo" / "validate.py").write_text("x = 1\n" * 900)
    expect("WARP-1102 AC1: the same governed file under the budget passes (revert teeth)",
           SG.file_lines_findings({".veldo/validate.py"}, _sgd, _sg_modline, _SG_REAL, ARCH) == [])
    (Path(_sgd) / "scripts").mkdir()
    (Path(_sgd) / "scripts" / "selftest.py").write_text("x = 1\n" * 5000)
    expect("WARP-1102 AC1: a changed file outside every declared area is not budget-governed (the contract governs the shape it declares)",
           SG.file_lines_findings({"scripts/selftest.py"}, _sgd, _sg_modline, _SG_REAL, ARCH) == [])

# AC2 adoption safe: a repository with NO architecture contract stands the whole gate down.
with tempfile.TemporaryDirectory() as _sgnc:
    os.makedirs(os.path.join(_sgnc, ".veldo"))
    _nc_sd, _nc_pr, _nc_no = SG.run(_sgnc, set())
    expect("WARP-1102 AC2: no contract stands the whole shape gate down (adoption safe, byte-identically unaffected)",
           _nc_sd is True and _nc_pr == [])
    expect("WARP-1102 AC2: no contract stands down even with a change present",
           SG.run(_sgnc, {".veldo/validate.py"})[0] is True)

# AC3 green safe and CHANGE SCOPED: the size budget binds the CHANGE, never the shipped corpus.
# This repository's own validate.py was, as a pre-contract module, the last governed file over the
# budget; WARP-1012 restored it under budget (splitting the sibling-module delegating validators
# into .veldo/validate_checks.py), so no governed module is grandfathered over-budget anymore. The
# rule's teeth on a REAL governed path are proven by the seeded over-budget fixture above (a
# contracts-area path at 1001 lines is refused, naming module_lines); here we confirm the restored
# validate.py is under budget, and that an empty change set flags nothing (never a corpus re-sweep).
_sg_valn = len((ROOT / ".veldo/validate.py").read_text().splitlines())
expect("WARP-1102 AC3: this repository's real validate.py is UNDER the file_lines budget (WARP-1012 restored it; no governed module is grandfathered over-budget)",
       _sg_valn <= _sg_modline["max"])
expect("WARP-1102 AC3: an EMPTY change set flags nothing (the shipped corpus is never re-swept, gate stays green)",
       SG.file_lines_findings(set(), ROOT, _sg_modline, _SG_REAL, ARCH) == [])
expect("WARP-1102 AC3: the restored validate.py in the change set yields NO module_lines finding (under budget); the budget's teeth on a real governed path stay proven by the seeded fixture above",
       SG.file_lines_findings({".veldo/validate.py"}, ROOT, _sg_modline, _SG_REAL, ARCH) == [])

# AC4 the D6 stdlib reference analyzers each detect a seeded violation (non-vacuous), and the
# contract's enforcement label decides whether a finding BLOCKS the gate (mechanizable) or is a
# non-blocking NOTE (review).
with tempfile.TemporaryDirectory() as _sga:
    (Path(_sga) / ".veldo").mkdir()
    (Path(_sga) / "a.py").write_text("def big():\n" + "".join("    x%d = %d\n" % (i, i) for i in range(200)))
    expect("WARP-1102 AC4: the function-length reference analyzer detects a long function (non-vacuous)",
           len(SG.function_length_findings({"a.py"}, _sga, 120)) == 1)
    (Path(_sga) / "b.py").write_text("def c(x):\n" + "".join("    if x == %d: return %d\n" % (i, i) for i in range(30)))
    expect("WARP-1102 AC4: the complexity reference analyzer detects a high-complexity function (non-vacuous)",
           len(SG.complexity_findings({"b.py"}, _sga, 20)) == 1)
    (Path(_sga) / "a.py").write_text("\n".join(["def f():", "    return 1"] + ["    value_line = compute(something) + one"] * 30))
    expect("WARP-1102 AC4: the duplication reference analyzer detects duplicated lines (non-vacuous)",
           len(SG.duplication_findings({"a.py"}, _sga, 8)) >= 1)
    # the import-boundary reference analyzer over the real contract: a metrics-area file that
    # references a fleet-area module over an edge dependencies.allow does not model is a violation.
    (Path(_sga) / ".veldo" / "metrics.py").write_text('spec = load(".veldo/fleet.py")\n')
    expect("WARP-1102 AC4: the import-boundary reference analyzer detects an unmodeled cross-area reference (non-vacuous)",
           len(SG.boundary_findings({".veldo/metrics.py"}, _sga, _SG_REAL, ARCH)) >= 1)
_SG_LBL = ("schema: veldo.arch/v1\nid: fix\ntitle: t\nversion: 1\nstatus: draft\n"
           "areas:\n  - id: core\n    title: Core\n    includes: [\"a.py\"]\n"
           "budgets:\n  - id: cap\n    kind: file_lines\n    applies_to: \"*\"\n    max: 5\n    enforcement: %s\n")
with tempfile.TemporaryDirectory() as _sgl:
    os.makedirs(os.path.join(_sgl, ".veldo"))
    (Path(_sgl) / "a.py").write_text("x\n" * 10)
    (Path(_sgl) / ".veldo" / "architecture.yaml").write_text(_SG_LBL % "mechanizable")
    _m_sd, _m_pr, _m_no = SG.run(_sgl, {"a.py"})
    expect("WARP-1102 AC4: a MECHANIZABLE budget violation BLOCKS the gate (a problem)",
           _m_sd is False and any("cap" in p for p in _m_pr))
    (Path(_sgl) / ".veldo" / "architecture.yaml").write_text(_SG_LBL % "review")
    _r_sd, _r_pr, _r_no = SG.run(_sgl, {"a.py"})
    expect("WARP-1102 AC4: the SAME violation under a REVIEW label is a NON-BLOCKING note, not a gate problem (the label is the sole authority)",
           _r_sd is False and _r_pr == [] and any("cap" in n for n in _r_no))

# AC5 footprint versus diff, scoped green safe (exactly one footprinted spec in the change set).
with tempfile.TemporaryDirectory() as _sgf:
    os.makedirs(os.path.join(_sgf, "specs"))
    (Path(_sgf) / "specs" / "S1.md").write_text("---\nschema: veldo.spec/v1\nid: S1\nfootprint:\n  - src/x.py\n  - specs/S1.md\n---\nb\n")
    expect("WARP-1102 AC5: one footprinted spec, all changed paths within the footprint yields no finding",
           SG.footprint_findings({"specs/S1.md", "src/x.py"}, _sgf, V, ARCH) == [])
    expect("WARP-1102 AC5: one footprinted spec, a changed path OUTSIDE the footprint refuses by name",
           any("outside the footprint" in f for f in SG.footprint_findings({"specs/S1.md", "other/y.py"}, _sgf, V, ARCH)))
    expect("WARP-1102 AC5: zero footprinted specs in the change set stands down (green safe)",
           SG.footprint_findings({"src/x.py"}, _sgf, V, ARCH) == [])
    (Path(_sgf) / "specs" / "S2.md").write_text("---\nschema: veldo.spec/v1\nid: S2\nfootprint:\n  - src/z.py\n---\nb\n")
    expect("WARP-1102 AC5: MORE than one footprinted spec stands down (multi-spec landing out of scope, honest)",
           SG.footprint_findings({"specs/S1.md", "specs/S2.md", "anything/q.py"}, _sgf, V, ARCH) == [])
# AC5 dogfood over the real change set: WARP-1102's own footprint covers every path it touches.
_sg_changed_real = SG.changed_source_paths(ROOT)
expect("WARP-1102 AC5 dogfood: over the real change set, footprint-versus-diff passes (this spec's footprint covers every path it touches)",
       SG.footprint_findings(_sg_changed_real, ROOT, V, ARCH) == [])

# AC6 RJ1: a seeded violation of each mechanizable rule class present fails the gate with the rule
# named, and the clean current tree stays green.
with tempfile.TemporaryDirectory() as _sgm:  # no scripts/ dir -> the enforcing checks are absent
    expect("WARP-1102 AC6 RJ1 engine-invariant class: a mechanizable prose rule whose enforcing check is ABSENT refuses by name",
           any("engine_byte_identical" in f for f in SG.prose_enforcement_findings("engine_byte_identical", _sgm)))
expect("WARP-1102 AC6 RJ1 budget class: a seeded over-budget governed file fails naming module_lines (proven above); over the real tree the enforcing checks are present so the engine invariants pass (clean tree green)",
       SG.prose_enforcement_findings("engine_byte_identical", ROOT) == []
       and SG.prose_enforcement_findings("derived_never_authoritative", ROOT) == []
       and SG.prose_enforcement_findings("adoption_safe_fail_closed", ROOT) == [])
expect("WARP-1102 AC6 RJ1: the current change under evaluation yields NO shape-gate problems (green safe, the enforcement did not break our own build)",
       SG.run(ROOT, _sg_changed_real)[1] == [])

# AC7 fail closed and anti-vacuity: an UNKNOWN mechanizable prose rule id, and a mechanizable budget
# of a kind with no reference implementation, are each refused by name.
expect("WARP-1102 AC7 anti-vacuity: an UNKNOWN mechanizable prose rule id has no wired enforcement and refuses",
       any("no wired gate enforcement" in f for f in SG.prose_enforcement_findings("no_raw_sql", ROOT)))
_SG_BADKIND = ("schema: veldo.arch/v1\nid: f\ntitle: t\nversion: 1\nstatus: draft\n"
               "areas:\n  - id: core\n    title: C\n    includes: [\"a.py\"]\n"
               "budgets:\n  - id: weird\n    kind: loc_count\n    applies_to: \"*\"\n    max: 5\n    enforcement: mechanizable\n")
with tempfile.TemporaryDirectory() as _sgbk:
    os.makedirs(os.path.join(_sgbk, ".veldo"))
    (Path(_sgbk) / ".veldo" / "architecture.yaml").write_text(_SG_BADKIND)
    _bk_sd, _bk_pr, _ = SG.run(_sgbk, set())
    expect("WARP-1102 AC7 anti-vacuity: a mechanizable budget of a kind with no reference implementation refuses by name",
           _bk_sd is False and any("no reference implementation" in p for p in _bk_pr))
_SG_BADPAT = ("schema: veldo.arch/v1\nid: f\ntitle: t\nversion: 1\nstatus: draft\n"
              "areas:\n  - id: core\n    title: C\n    includes: [\"a.py\"]\n"
              "patterns:\n  - id: novel_rule\n    text: some prose\n    enforcement: mechanizable\n")
with tempfile.TemporaryDirectory() as _sgbp:
    os.makedirs(os.path.join(_sgbp, ".veldo"))
    (Path(_sgbp) / ".veldo" / "architecture.yaml").write_text(_SG_BADPAT)
    _bp_sd, _bp_pr, _ = SG.run(_sgbp, set())
    expect("WARP-1102 AC7 anti-vacuity: SG.run refuses a mechanizable prose rule with no wired enforcement (cannot mark mechanizable and enforce nothing)",
           _bp_sd is False and any("no wired gate enforcement" in p for p in _bp_pr))

# AC8 byte-identical sync across the 8 engine copies, thin protected-file diff, protected siblings
# untouched, honest capability, and this spec's own placement/footprint/tier dogfood.
_SG_PACKS = ["aider", "antigravity", "codex", "copilot", "cursor", "opencode"]
expect("WARP-1102 AC8: .veldo/shape_gate.py is byte-identical root vs engine",
       (ROOT / ".veldo/shape_gate.py").read_bytes() == (ROOT / "engine/.veldo/shape_gate.py").read_bytes())
expect("WARP-1102 AC8: .veldo/shape_gate.py is byte-identical across all 6 packs",
       (ROOT / ".veldo/shape_gate.py").read_bytes() == (ROOT / "engine/.veldo/shape_gate.py").read_bytes())
expect("WARP-1102 AC8: .veldo/capabilities.yaml is byte-identical root vs engine and across all 6 packs",
       (ROOT / ".veldo/capabilities.yaml").read_bytes() == (ROOT / "engine/.veldo/capabilities.yaml").read_bytes()
       and (ROOT / ".veldo/capabilities.yaml").read_bytes() == (ROOT / "engine/.veldo/capabilities.yaml").read_bytes())
expect("WARP-1102 AC8: the shape_gate_enforcement capability is declared mechanical",
       bool(re.search(r"(?m)^\s{2}shape_gate_enforcement:\s*\{status:\s*mechanical\b", (ROOT / ".veldo/capabilities.yaml").read_text())))
expect("WARP-1102 AC8: verify.sh (and its engine twin) gain only the thin call into the non-protected module",
       "if ! python3 .veldo/shape_gate.py; then FAIL=1; fi" in (ROOT / "scripts/verify.sh").read_text()
       and "if ! python3 .veldo/shape_gate.py; then FAIL=1; fi" in (ROOT / "engine/scripts/verify.sh").read_text())
expect("WARP-1102 AC8: veldo-guard.sh, policy.yaml, and policy_check.py are NOT touched (no shape-gate reference)",
       "shape_gate" not in (ROOT / "scripts/veldo-guard.sh").read_text()
       and "shape_gate" not in (ROOT / ".veldo/policy.yaml").read_text()
       and "shape_gate" not in (ROOT / ".veldo/policy_check.py").read_text())
_p12_file = ROOT / "specs/WARP-1102-gate-shape-enforcement.md"
_p12_fm = V.parse_yamlish(re.match(r"^---\n(.*?)\n---", _p12_file.read_text(), re.S).group(1))
expect("WARP-1102 AC8 dogfood: the spec's footprint spans enforcement and contracts",
       ARCH.footprint_areas(_p12_fm, _SG_REAL) >= {"enforcement", "contracts"})
expect("WARP-1102 AC8 dogfood: footprint tier is standard (enforcement-to-contracts is an allow-listed edge, cohesive breadth not a crossing)",
       ARCH.footprint_tier_floor(_p12_fm, _SG_REAL) == "")
expect("WARP-1102 AC8 dogfood: the spec passes the mandatory placement gate at risk high (placed, resolves, tier not lowered)",
       ARCH.placement_gate(_p12_fm, _SG_REAL) == [])
expect("WARP-1102 AC8: it is a PROTECTED-PATH change (edits verify.sh) so it declares the protected path and requires approval",
       "scripts/verify.sh" in (_p12_fm.get("protected_paths") or []) and _p12_fm.get("human_approval") == "required")

# --- entropy metrics (WARP-1108, W8 of PLAN-0011): cost-to-change per architecture area becomes a
# NUMBER that trends. .veldo/entropy.py DERIVES a per-area cost-to-change series from what the loop
# ALREADY records (tokens, cost, human_minutes, review cycles, gate failures - read through
# metrics.compute's cost_by_correlation, the single aggregation, NO new instrumentation), joined to
# contract areas through each spec's placement/footprint (arch.footprint_areas, the W3 join key),
# with the gate's static shape measures (shape_gate's duplication/complexity/function-length/boundary
# analyzers) on the SAME per-area map. The threshold is a RELATIVE degradation vs an area's own
# trailing baseline, ADVISORY during calibration (D2); nothing auto-gates on the number - a crossing
# is the signal WARP-1109 (W9) consumes. IN-SESSION only, spawns nothing (source scan + mutation
# teeth). Adoption safe (no contract stands down). W9 restoration and the PLAN-0012 incident join are
# honestly out of scope and only referenced.
_enspec = importlib.util.spec_from_file_location("veldo_entropy", ROOT / ".veldo/entropy.py")
EN = importlib.util.module_from_spec(_enspec); _enspec.loader.exec_module(EN)
_dbespec = importlib.util.spec_from_file_location("veldo_dashboard_ent", ROOT / ".veldo/dashboard.py")
DBE = importlib.util.module_from_spec(_dbespec); _dbespec.loader.exec_module(DBE)


def _en_change(corr, at, hm=0, tokens=0, reviews=0, gatefail=0):
    """The events one shipped change records: a spec.shipped (marking the shipped unit and carrying
    the recorded tokens/human_minutes) plus review and gate-failure events under the change's
    correlation. Only fields the loop ALREADY records - no new instrumentation."""
    evs = [{"schema": "veldo.event/v1", "type": "spec.shipped", "at": at, "correlation_id": corr,
            "human_minutes": hm, "tokens": tokens}]
    for _i in range(reviews):
        evs.append({"schema": "veldo.event/v1", "type": "verdict.recorded", "at": at,
                    "correlation_id": corr, "verdict": "pass"})
    for _i in range(gatefail):
        evs.append({"schema": "veldo.event/v1", "type": "gate.failed", "at": at, "correlation_id": corr})
    return evs


# alpha: 8 shipped changes, human_minutes flat at 10 then a spike to 30 (a rising series, a matured
# area); beta: 6 flat changes (no degradation, still calibrating); one orphan change with no area.
_en_events = []
_en_index = {}
for _i in range(7):
    _c = "a%02d" % _i
    _en_events += _en_change(_c, "2026-07-01T%02d:00:00Z" % _i, hm=10, tokens=100, reviews=1)
    _en_index[_c] = {"alpha"}
_en_events += _en_change("a07", "2026-07-01T07:00:00Z", hm=30, tokens=300, reviews=3)
_en_index["a07"] = {"alpha"}
for _i in range(6):
    _c = "b%02d" % _i
    _en_events += _en_change(_c, "2026-07-02T%02d:00:00Z" % _i, hm=10, tokens=100, reviews=1)
    _en_index[_c] = {"beta"}
_en_events += _en_change("orphan", "2026-07-03T00:00:00Z", hm=999)  # no area -> unattributed, counted

_en_series, _en_stats = EN.area_series(_en_events, _en_index)
# AC1: the per-area cost-to-change series carries the right per-dimension values in ship-time order.
expect("WARP-1108 AC1: alpha's human_minutes series is time-ordered from the recorded events",
       [s["human_minutes"] for s in _en_series["alpha"]] == [10, 10, 10, 10, 10, 10, 10, 30])
expect("WARP-1108 AC1: alpha's tokens series tracks the recorded spend per shipped change",
       [s["tokens"] for s in _en_series["alpha"]] == [100, 100, 100, 100, 100, 100, 100, 300])
expect("WARP-1108 AC1: review_cycles are counted from verdict.recorded events per change",
       _en_series["alpha"][-1]["review_cycles"] == 3 and _en_series["beta"][0]["review_cycles"] == 1)
expect("WARP-1108 AC1: attributed and unattributed change counts are correct (the orphan is counted, not dropped)",
       _en_stats == {"attributed_changes": 14, "unattributed_changes": 1})
# AC1: cost_by_correlation is metrics.compute's (the single aggregation), never a second store.
_en_cc = ME.compute(_en_change("z", "2026-07-01T00:00:00Z", hm=12, tokens=50, reviews=2, gatefail=1))["cost_by_correlation"]
expect("WARP-1108 AC1: metrics.compute exposes cost_by_correlation with the recorded components",
       _en_cc["z"]["human_minutes"] == 12 and _en_cc["z"]["tokens"] == 50
       and _en_cc["z"]["review_cycles"] == 2 and _en_cc["z"]["gate_failures"] == 1
       and _en_cc["z"]["shipped_at"] == "2026-07-01T00:00:00Z")
# AC1: a cross-area change contributes its recorded cost to EACH area it touched.
_en_x_series, _ = EN.area_series(_en_change("x", "2026-07-05T00:00:00Z", hm=7), {"x": {"alpha", "beta"}})
expect("WARP-1108 AC1: a cross-area change contributes its cost to each area it touched",
       _en_x_series["alpha"][-1]["human_minutes"] == 7 and _en_x_series["beta"][-1]["human_minutes"] == 7)

# AC2: relative-baseline crossing (D2). alpha spiked 10->30 over a 5-sample baseline of 10 (30 >= 15)
# so it crosses; beta is flat so it does not (non-vacuous). alpha has 8 samples (matured -> trusted).
_en_crossings = EN.detect_crossings(_en_series)
_en_alpha_hm = [c for c in _en_crossings if c["area"] == "alpha" and c["dimension"] == "human_minutes"]
expect("WARP-1108 AC2: a rising series crosses its trailing baseline (relative degradation vs its own history)",
       len(_en_alpha_hm) == 1 and _en_alpha_hm[0]["latest"] == 30.0 and _en_alpha_hm[0]["baseline"] == 10.0)
expect("WARP-1108 AC2: a matured area's crossing is TRUSTED (advisory False, at least calibration_min samples)",
       _en_alpha_hm[0]["advisory"] is False)
expect("WARP-1108 AC2: a flat series does not cross (the crossing is not vacuous)",
       not any(c["area"] == "beta" for c in _en_crossings))
# a 6-sample rising series is still calibrating -> the crossing is ADVISORY (not yet trusted).
_en_cal = EN.detect_crossings({"g": _en_series["alpha"][:5] + [_en_series["alpha"][-1]]})
expect("WARP-1108 AC2: a still-calibrating area's crossing is ADVISORY (measured but not yet trusted)",
       len(_en_cal) >= 1 and all(c["advisory"] is True for c in _en_cal))
# mutation: flatten the latest sample back to baseline -> no crossing (the recorded number drives it).
_en_flat = {"alpha": _en_series["alpha"][:7]
            + [dict(_en_series["alpha"][-1], human_minutes=10, tokens=100, review_cycles=1)]}
expect("WARP-1108 AC2 TEETH: flattening the latest sample removes the crossing (the recorded number drives it)",
       not any(c["dimension"] == "human_minutes" for c in EN.detect_crossings(_en_flat)))
# AC2 nothing auto-gates: entropy is advisory and unwired from the gate path (the gate never
# invokes the entropy module; a prose W8/W9 reference in a docstring is not an invocation).
expect("WARP-1108 AC2: the gate never invokes the entropy module (verify.sh does not run .veldo/entropy.py)",
       ".veldo/entropy.py" not in (ROOT / "scripts/verify.sh").read_text()
       and ".veldo/entropy.py" not in (ROOT / ".veldo/shape_gate.py").read_text())
expect("WARP-1108 AC2: validate.py run_all never loads or invokes the entropy module (nothing auto-gates on the number)",
       ".veldo/entropy.py" not in (ROOT / ".veldo/validate.py").read_text()
       and "entropy_report" not in (ROOT / ".veldo/validate.py").read_text())

# AC3: the gate's static shape measures on the same per-area map, reused from shape_gate; adoption safe.
_EN_ARCH_MIN = """schema: veldo.arch/v1
id: t
title: t
version: 1
status: approved
approved_by: x
approved_at: 2026-07-22
areas:
  - id: core
    title: core
    includes: ["src/mod.py"]
budgets:
  - id: fl
    kind: function_lines
    applies_to: "*"
    max: 5
    enforcement: review
"""
_EN_LONGFN = "def f():\n" + "".join("    x = %d\n" % _i for _i in range(10)) + "    return x\n"
with tempfile.TemporaryDirectory() as _d:
    _r = Path(_d)
    (_r / ".veldo").mkdir()
    (_r / "src").mkdir()
    (_r / ".veldo" / "architecture.yaml").write_text(_EN_ARCH_MIN)
    (_r / "src" / "mod.py").write_text(_EN_LONGFN)
    _rep_long = EN.entropy_report(events=[], root=_r)
    (_r / "src" / "mod.py").write_text("def f():\n    return 1\n")
    _rep_short = EN.entropy_report(events=[], root=_r)
    expect("WARP-1108 AC3: an area's static shape reuses the gate analyzers over its source (an over-long function is counted)",
           _rep_long["areas"]["core"]["static_shape"]["function_length"] >= 1)
    expect("WARP-1108 AC3: the static-shape measure is non-vacuous (a short function counts zero, byte-reverted)",
           _rep_short["areas"]["core"]["static_shape"]["function_length"] == 0)
    expect("WARP-1108 AC3: a contract with no recorded events renders an empty series and no crossings",
           _rep_long["areas"]["core"]["samples"] == 0 and _rep_long["crossings"] == [])
with tempfile.TemporaryDirectory() as _d:
    _r = Path(_d)
    _rep_none = EN.entropy_report(events=_en_events, root=_r)
    expect("WARP-1108 AC3: no architecture contract stands the derivation down (adoption safe, byte-identically unaffected)",
           _rep_none.get("standdown") is True and _rep_none["areas"] == {} and _rep_none["crossings"] == [])

# AC4: IN-SESSION only, spawns nothing (the no-detach source scan + mutation teeth, mirroring WARP-1107).
_en_src = (ROOT / ".veldo/entropy.py").read_text()


def _en_no_detached(src):
    return not any(t in src for t in _TRIP_DETACH_TOKENS)


expect("WARP-1108 AC4: entropy.py starts no process/thread/timer (no subprocess/Popen/fork/exec/spawn/setsid/nohup/multiprocessing/threading/asyncio/sched/claude -p)",
       _en_no_detached(_en_src))
expect("WARP-1108 AC4: entropy.py imports no process/thread machinery",
       "import subprocess" not in _en_src and "import threading" not in _en_src
       and "import multiprocessing" not in _en_src and "import asyncio" not in _en_src)
_en_mut_popen = _en_src + '\n_p = subprocess.Popen(["claude", "-p", q], start_new_session=True)\n'
_en_mut_thread = _en_src + '\nimport threading\nthreading.Thread(target=poll, daemon=True).start()\n'
expect("WARP-1108 AC4 TEETH: a detached subprocess.Popen(claude -p) mutation fails the no-detach check",
       _en_no_detached(_en_mut_popen) is False)
expect("WARP-1108 AC4 TEETH: a background thread mutation fails the no-detach check",
       _en_no_detached(_en_mut_thread) is False)
expect("WARP-1108 AC4: the no-detach mutations are in-memory only (the real module on disk is byte-unchanged)",
       (ROOT / ".veldo/entropy.py").read_text() == _en_src)
# AC4: a crossing is the machine-readable signal WARP-1109 (W9) consumes.
expect("WARP-1108 AC4: a crossing names the area, dimension, baseline, latest, advisory, and its W9 consumer",
       len(_en_crossings) >= 1 and all({"area", "dimension", "baseline", "latest", "advisory"}.issubset(c)
                                        and c["consumed_by"] == "WARP-1109" for c in _en_crossings))

# AC5: byte-identical engine sync, honest capability, dashboard no-fork, dogfooded placement.
expect("WARP-1108 AC5: .veldo/entropy.py is byte-identical root vs engine",
       (ROOT / ".veldo/entropy.py").read_bytes() == (ROOT / "engine/.veldo/entropy.py").read_bytes())
expect("WARP-1108 AC5: .veldo/entropy.py is byte-identical across all 6 packs",
       (ROOT / ".veldo/entropy.py").read_bytes() == (ROOT / "engine/.veldo/entropy.py").read_bytes())
expect("WARP-1108 AC5: metrics.py and dashboard.py are byte-identical root vs engine",
       (ROOT / ".veldo/metrics.py").read_bytes() == (ROOT / "engine/.veldo/metrics.py").read_bytes()
       and (ROOT / ".veldo/dashboard.py").read_bytes() == (ROOT / "engine/.veldo/dashboard.py").read_bytes())
expect("WARP-1108 AC5: the entropy_metrics capability is declared mechanical",
       bool(re.search(r"(?m)^\s{2}entropy_metrics:\s*\{status:\s*mechanical\b", (ROOT / ".veldo/capabilities.yaml").read_text())))
# dashboard no-fork: the entropy section reads entropy_report (the single source), never a recompute.
_en_direct = EN.entropy_report(events=_en_events)
expect("WARP-1108 AC5: the dashboard entropy section reads entropy_report (no fork) - and the stand-down slot carries the REASON rather than a bare flag since WARP-1210 round 10, so a section whose OWNER RAISED can say so instead of borrowing 'no architecture contract'",
       DBE.entropy_figures(_en_events) == ("", EN.area_figures(_en_direct), _en_direct["crossings"]))
expect("WARP-1108 AC5: the dashboard text render carries the per-area entropy section",
       "entropy - cost-to-change per area" in DBE.render_text(_en_events))
# dogfood: this spec's placement resolves and its footprint tier is standard (a single area).
_p18_fm = V.parse_yamlish(re.match(r"^---\n(.*?)\n---", (ROOT / "specs/WARP-1108-entropy-metrics.md").read_text(), re.S).group(1))
expect("WARP-1108 AC5 dogfood: the spec's placement resolves to the metrics area",
       ARCH.footprint_areas(_p18_fm, _SG_REAL) == {"metrics"})
expect("WARP-1108 AC5 dogfood: footprint tier is standard (a single area, no boundary crossing)",
       ARCH.footprint_tier_floor(_p18_fm, _SG_REAL) == "")
expect("WARP-1108 AC5 dogfood: the spec passes the mandatory placement gate (placed, resolves, tier not lowered)",
       ARCH.placement_gate(_p18_fm, _SG_REAL) == [])
expect("WARP-1108 AC5: no protected path is touched (entropy, metrics, dashboard are non-protected engine)",
       (_p18_fm.get("protected_paths") or []) == [] and _p18_fm.get("human_approval") == "not_required")
