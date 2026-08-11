#!/usr/bin/env python3
"""VELDO contract validator, part two: the sibling-module delegating validators.

This module is a PURE extraction from .veldo/validate.py, split out solely so that
validate.py stays under the module_lines budget the architecture contract
enforces. It holds the validators that delegate to the sibling contract organs -
the architecture contract (arch.py), the placement/ready gates, decision records
(decision.py), the adversarial decision review (decision_review.py), the decision
tripwires (tripwire.py), the shape-fit review dimension (shape_review.py), and the
read-only tripwire-status projection.

Loaded ONLY by validate.py, by path, the same idiom validate.py uses to load its
other siblings and the idiom shape_gate.py/entropy.py/incident.py use to load
validate.py. The dependency is one-way (validate.py -> validate_checks.py, never
back), so there is no import cycle. validate.py binds this module's parse_yamlish
and fail (its ONE front-matter parser and ONE failure reporter) after loading it,
exactly as it hands those same two callables to arch.py and decision.py - so this
module ships no second parser and no second reporter - and then re-exports every
name defined here into its own namespace, keeping the public API (V.check_arch,
V.check_placement, V.check_ready, V.load_repo_contract, V.tripwire_status, ...)
byte-identical for every caller.
"""
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Bound by validate.py after it loads this module (the one-way load): its ONE
# front-matter parser and ONE failure reporter, the same two callables it hands
# arch.py and decision.py. Declared here so the contract is explicit; validate.py
# is the authoritative binder. This module never loads validate.py (no cycle).
parse_yamlish = None
fail = None

# The proof-corpus enumeration (WARP-0727): the ONE owner of what a corpus path IS, and the
# SAME module .veldo/events.py derives the projection's entitlement domain through. Enforcement
# here REUSES it and never reimplements the enumeration, because the defect being closed is
# precisely two mechanisms enumerating one set in two spellings, with the gap between them
# invisible to both.
_cospec = importlib.util.spec_from_file_location(
    "veldo_verdict_corpus", ROOT / ".veldo" / "verdict_corpus.py")
_CORPUS = importlib.util.module_from_spec(_cospec)
_cospec.loader.exec_module(_CORPUS)


def _corpus(pattern, root=None):
    """The corpus artifacts of one pattern, as absolute paths, through the ONE enumeration.

    THIS IS WHAT THE VALIDATED SET IS. It used to be `(ROOT / "proof").glob("*/<pattern>")`, a
    SECOND spelling of a set .veldo/events.py computed with a git pathspec, and the two differed
    exactly where nobody was looking: a pathlib `*` does not cross `/` and a git pathspec `*`
    does, so `proof/<a>/<b>/verdict.json` sat in the projection's entitlement domain and was
    never validated by anything. Measured at ffaab41, a forged verdict there was appended to the
    append-only log by a plain gate run, at GATE GREEN."""
    base = Path(root) if root else ROOT
    return [base / rel for rel in _CORPUS.disk_corpus(base, pattern)]


def check_verdict_domain_is_the_validated_set(root=None):
    """THE ENTITLEMENT DOMAIN AND THE VALIDATED SET ARE ONE SET, ASSERTED IN BOTH DIRECTIONS
    OVER THE REAL CORPUS.

    One membership rule applied to two path sources cannot differ BY SPELLING, which is the
    class this closes and is structural rather than checked. What one rule cannot make identical
    is the SOURCES: the git index and the working tree. That residual is the whole of what this
    check exists for, measured per path with the reason named, in both directions, because the
    two directions are different harms.

      ENTITLED AND NOT VALIDATED is the FORGERY direction: a key the projection may append an
      event for that no validator will ever look at. It must be EMPTY; any member is red.

      VALIDATED AND NOT ENTITLED is the INVERSE HARM, and it is worse: an artifact no review
      event can ever be derived for, so the log silently stops recording. It is PARTITIONED BY
      WHAT GIT SAYS ABOUT EACH PATH, asked of git directly and never derived from the domain
      under test - independently of the pathspec and the prefix arithmetic, NOT of the process
      environment, which moves both readings together and is declared as a limit by the owner.
      UNTRACKED is the one legitimate reason and is expected (an author validating
      before committing), so it is not red. A path GIT REPORTS AS TRACKED that the domain does
      not hold is a CONTRADICTION, since tracked plus the rule IS the domain, and it is red.

      OVERCLAIMED is the same disagreement read the other way: a domain member git does not
      report as tracked under this root at all. Red, and it is the shape of the anchoring
      forgery - a verdict committed at an OUTER proof root entering a vendored VELDO's domain.

      AN EMPTY DOMAIN AGAINST A NON-EMPTY WORKING TREE IS NEVER UNREPORTED, whatever the per-path
      reasons say. That is the signature both measured anchoring defects wore - 166 artifacts
      validated, 0 entitled, contract green, every genuine verdict withheld forever - and in the
      shape where the proof root is a tracked SYMLINK the per-path buckets are all legitimately
      `untracked`, so nothing else here would say a word. It is RED when git reports anything
      tracked at or below the proof root, because then the index holds a corpus this enumeration
      cannot name a member of; it is a NAMED REPORT when git tracks nothing there at all, which
      is an adopter who has committed nothing yet and is not a defect.

      `UNREPORTED` AND NOT `SILENT`, WHICH IS A WEAKER PROMISE AND THE HONEST ONE. The report
      branch PRINTS A LINE and returns ZERO errors, so `validate.py all` still exits 0 and a CI
      reading only the exit status sees green over it. That is sound by design - an adopter who has
      committed nothing is not a defect and must not red - but the guarantee this branch carries is
      that the shape appears in the OUTPUT, never that it reaches the exit code.

      MISFILED is a verdict-shaped file at a path the rule does not admit. Red, named: it is
      the artifact the shipped pathspec used to hand the projection with a real blob.

    WHICH PATTERNS THIS ACTUALLY EXERCISES IS A PROPERTY OF THE REPOSITORY, NOT OF THE CHECK, and
    saying so is the difference between coverage and the appearance of it. All four declared
    patterns are asked; in THIS repository the design-verdict one runs over an EMPTY SET (counted
    this round at the parent commit 098dc6a: 0 tracked design-verdict artifacts, against 168
    verdicts, 142 manifests and 9 approvals), so that leg is PRESENT AND UNEXERCISED here and must
    not be read as evidence about design-verdict artifacts. Those figures are a MEASUREMENT DATED
    BY ITS COMMIT and not a check: the corpus grows, and nothing here pins its size.

    THERE IS NO STAND-DOWN FOR AN ABSENT PROOF ROOT, and there used to be: `if not (base /
    PROOF_ROOT).is_dir(): return 0`, printing nothing. One ordinary git feature reached it -
    `git sparse-checkout set` naming every top level directory except the proof root - and the
    whole check went quiet while the index still held every artifact: `validate.py all` exited 0
    where the same commit with the proof root present exits 1, and a plain reconciler run appended
    a verdict.recorded for a forged `{"schema": "nope", "verdict": "pass"}` at
    proof/WARP-9999/verdict.json with a real blob. THE EARLY RETURN WAS ALSO UNNECESSARY, which is
    why deleting it is the whole fix: with no proof root and nothing tracked, divergence returns
    all-empty and the body below scores 0 anyway, so an adopter with no corpus is byte-identically
    unaffected while an adopter whose corpus is merely NOT CHECKED OUT is now told so per path.

    ONE ROOT, ONE ANCHORING, AND THAT IS THE OTHER HALF OF THE SAME PROPERTY. The owner takes a
    single root and resolves the pathspec from it, so this check asks the git side and the disk
    side about the SAME directory and about the same one entitlement is decided at. It used to
    ask the CWD-ANCHORED question on both sides while entitlement asked a TOP-ANCHORED one, and
    with VELDO vendored below the top of a larger repository those name different directories: the
    entitled set was 0 against a validated set of 166, every genuine verdict withheld forever,
    and this check passed because both of ITS sides agreed with each other.

    NO GIT IS NOT A WAIVER, IT IS SOUNDNESS. When git cannot answer, the projection's domain is
    empty BY THE SAME ABSENCE, so no key exists for anything to append and containment holds for
    that reason rather than being skipped. The two sides degrade together because they share one
    owner, which is why this can pass there without failing open. IT DOES NOT PASS SILENTLY: the
    equality legs are inert without git, and a skipped check that prints nothing reads exactly
    like a check that ran and found nothing, so one note is printed naming what did not run."""
    base = Path(root) if root else ROOT
    errs = 0
    inert = []
    for pattern in (_CORPUS.VERDICT_PATTERN, _CORPUS.DESIGN_VERDICT_PATTERN,
                    _CORPUS.APPROVAL_PATTERN, _CORPUS.MANIFEST_PATTERN):
        d = _CORPUS.divergence(base, pattern)
        for rel in d["misfiled"]:
            errs += fail(rel, "named like %s but not at <%s>/<spec id>/<name>, so no review "
                              "event can ever be derived for it: move it or rename it"
                         % (pattern, _CORPUS.PROOF_ROOT))
        if not d["git_available"]:
            inert.append(pattern)
            continue
        for rel in d["entitled_not_validated"]:
            errs += fail(rel, "tracked in git but absent from the working tree: it is inside "
                              "the projection's entitlement domain and no validator sees it")
        for rel in d["contradiction"]:
            errs += fail(rel, "git reports this path as TRACKED and the enumerated domain does "
                              "not hold it: the two readings of one index disagree about one set")
        for rel in d["overclaimed"]:
            errs += fail(rel, "in the enumerated domain, yet git does not report it as tracked "
                              "under this root at all: the domain reaches outside the VELDO root")
        if d["validated"] and not d["entitled"]:
            # THE 166-TO-0 SIGNATURE, WHICH MUST NEVER GO UNREPORTED whatever the per-path reasons
            # were. Both measured anchoring defects and the prefix defect wore exactly this shape.
            # The count below is of INDEX ENTRIES and says so: tracked_under_proof comes from
            # `git ls-files`, which prints one record per entry, so a conflicted path appears once
            # per stage (measured: 3 records for 1 path) and calling that 3 paths would be wrong.
            if d["tracked_under_proof"]:
                errs += fail(_CORPUS.PROOF_ROOT,
                             "%d artifact(s) matching %s are validated on disk and the enumerated "
                             "domain holds NONE of them, while git's index carries %d entr(ies) at "
                             "or below this root (e.g. %s): no review event can ever be derived "
                             "for any of them"
                             % (len(d["validated"]), pattern, len(d["tracked_under_proof"]),
                                d["tracked_under_proof"][0]))
            else:
                print("  %s: %d artifact(s) matching %s are on disk and git tracks NOTHING at or "
                      "below this root, so none of them is in the entitlement domain yet and no "
                      "review event can be derived for any of them (expected before they are "
                      "committed; the domain is not withholding them, the repository has not been "
                      "told about them)"
                      % (_CORPUS.PROOF_ROOT, len(d["validated"]), pattern))
    if inert:
        # NOT A FAILURE AND NOT A SILENCE. Containment still holds - no git, no domain, nothing
        # to append - but the equality legs did not run, and an adopter reading a green stage
        # is entitled to know which part of it was inert rather than satisfied.
        print("  %s: git could not enumerate the corpus, so the domain and the validated set "
              "were not compared for %s (the projection can append nothing without git, so "
              "containment holds; the equality check did not run)"
              % (_CORPUS.PROOF_ROOT, ", ".join(inert)))
    return errs


def _arch_module():
    """Load the architecture-contract validator (.veldo/arch.py); it receives this
    module's parser and reporter, so it adds no second YAML parser and there is no
    import cycle. The one place arch.py is loaded (by check_arch and check_placement)."""
    aspec = importlib.util.spec_from_file_location("veldo_arch", ROOT / ".veldo" / "arch.py")
    arch = importlib.util.module_from_spec(aspec)
    aspec.loader.exec_module(arch)
    return arch


def check_arch(path=None, root=None, required=False):
    """Validate the architecture contract (veldo.arch/v1) structurally, delegating
    to .veldo/arch.py. Adoption safe: an absent contract stands down (unless it is
    required), and a repository without a contract is byte-identically unaffected.
    Present, or required-and-absent: fails closed. The parser and the failure
    reporter passed in are this module's own, so arch.py adds no second YAML
    parser and there is no import cycle."""
    base = Path(root) if root else ROOT
    contract = Path(path) if path else base / ".veldo" / "architecture.yaml"
    return _arch_module().check_contract(contract, base, required, parse_yamlish, fail)


def check_placement(path, repo_root=None):
    """Validate a spec's optional PLACEMENT and FOOTPRINT declaration against this
    repository's architecture contract (veldo.arch/v1) at spec-validation time,
    delegating the structural rules to .veldo/arch.py (the W3 organ).

    Adoption safe on two axes. When no contract exists in this repository the whole
    check stands down (a contract-free repository is byte-identically unaffected,
    the C2 posture), and a spec that declares neither placement nor footprint stands
    down too (placement is optional, never forced onto a spec). Once a placement is
    declared and a contract exists it is validated fail closed: each placement area
    id must resolve to a declared contract area, a footprint must be a non-empty glob
    list, and a footprint without a placement is refused.

    HONEST BOUNDARY: this is the declaration and its elaboration-time structural
    validation only. Mechanically enforcing the declared footprint against the
    actual diff at gate time is WARP-1102 (W2), and grading shape-fit is WARP-1104
    (W4); neither is done here."""
    base = Path(repo_root) if repo_root else ROOT
    contract_path = base / ".veldo" / "architecture.yaml"
    if not contract_path.is_file():
        return 0  # adoption safe: no contract in this repo, the check stands down
    text = Path(path).read_text()
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if m is None:
        return 0  # check_spec already reports a missing front matter
    body = m.group(1)
    # Presence gate: parse richly only when the spec actually declares one of the
    # fields, so a spec that declares neither is byte-identically unaffected.
    if not re.search(r"(?m)^(placement|footprint):", body):
        return 0
    try:
        fm = parse_yamlish(body)
    except ValueError as e:
        return fail(path, f"placement/footprint declared but the front matter is outside the parser subset: {e}")
    arch = _arch_module()
    try:
        contract = arch.load_contract(contract_path, parse_yamlish)
    except arch.ArchContractError:
        return 0  # a malformed contract is reported by check_arch; do not double-refuse here
    return arch.validate_placement(fm, contract, str(path), fail)


def _observability_module():
    """Load the diagnosability-gate organ (.veldo/observability.py) the same way arch is
    loaded: it is PURE over parsed dicts and receives this module's failure reporter, so
    it adds no second YAML parser and there is no import cycle. The one place
    observability.py is loaded (by check_observability and check_ready)."""
    ospec = importlib.util.spec_from_file_location("veldo_observability", ROOT / ".veldo" / "observability.py")
    obs = importlib.util.module_from_spec(ospec)
    ospec.loader.exec_module(obs)
    return obs


def check_observability(path, repo_root=None):
    """Validate a spec's optional OBSERVABILITY declaration (the W9 diagnosability-gate
    vocabulary) against this repository's architecture contract at spec-validation time,
    delegating the structural rules to .veldo/observability.py.

    Adoption safe on two axes, mirroring check_placement. When no architecture contract
    exists in this repository the whole check stands down (a contract-free repository is
    byte-identically unaffected, the C2/C7 posture), and a spec that declares neither
    behavior_bearing nor an observability block stands down too (nothing is forced onto a
    spec here). Once a declaration is present and a contract exists it is validated fail
    closed: behavior_bearing (if present) is true|false, and an observability block names
    only recognized criteria, each a non-empty description.

    HONEST BOUNDARY: this is the DECLARATION and its structural validation only, run over
    every spec (present-only, so the already-shipped corpus that declares neither field is
    never touched). The MANDATORY rule - a behavior-bearing spec must declare observability
    criteria - is enforced at the ready TRANSITION (check_ready), never as a static
    check_spec sweep, exactly as the placement gate is; so the shipped corpus is never
    re-evaluated (RJ6). Whether the declared criteria are SUFFICIENT is a review-lane
    judgment, never graded here (NG5)."""
    base = Path(repo_root) if repo_root else ROOT
    contract_path = base / ".veldo" / "architecture.yaml"
    if not contract_path.is_file():
        return 0  # adoption safe: no contract in this repo, the check stands down
    text = Path(path).read_text()
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if m is None:
        return 0  # check_spec already reports a missing front matter
    body = m.group(1)
    # Presence gate: parse richly only when the spec actually declares one of the fields,
    # so a spec that declares neither is byte-identically unaffected.
    if not re.search(r"(?m)^(observability|behavior_bearing):", body):
        return 0
    try:
        fm = parse_yamlish(body)
    except ValueError as e:
        return fail(path, f"observability/behavior_bearing declared but the front matter is outside the parser subset: {e}")
    return _observability_module().validate_observability(fm, str(path), fail)


def load_repo_contract(repo_root=None):
    """(arch_module, parsed_contract) for this repository, or (None, None) when no
    contract exists or it is malformed (adoption safe: a repository without a contract
    is unaffected, and a malformed contract is reported by check_arch, not double
    refused here). This is the single place the mandatory placement gate's consumers -
    the ready transition (check_ready), the claimable frontier (frontier.claimable),
    and run-check (plan.cmd_run_check) - obtain the parsed contract, so arch.py is
    loaded once per pass and all three gate against the SAME artifact."""
    base = Path(repo_root) if repo_root else ROOT
    contract_path = base / ".veldo" / "architecture.yaml"
    if not contract_path.is_file():
        return None, None
    arch = _arch_module()
    try:
        return arch, arch.load_contract(contract_path, parse_yamlish)
    except arch.ArchContractError:
        return None, None


def placement_gate_problems(fm, repo_root=None):
    """The mandatory placement gate's problems for a spec's parsed front matter (from
    parse_yamlish, so placement and footprint arrive as real lists), against this
    repository's contract; empty when the spec passes OR when no contract exists
    (adoption safe). run-check renders these as its refusal reasons. Delegates to the
    one predicate arch.placement_gate so the frontier, run-check, and the ready
    transition never diverge on what a resolving placement is."""
    arch, contract = load_repo_contract(repo_root)
    if contract is None:
        return []
    return arch.placement_gate(fm, contract)


def placement_gate_ok(fm, repo_root=None):
    """Silent boolean form of the mandatory placement gate, for the claimable frontier
    (which must not print). True when the spec passes or when no contract exists."""
    return not placement_gate_problems(fm, repo_root)


def check_ready(path, repo_root=None):
    """The MANDATORY-AT-READY gate (the O3/RJ2 property). When a contract exists, a
    spec may not REACH ready unless it declares a placement that resolves to a contract
    area, and its declared risk is at least the tier its footprint implies (a footprint
    that crosses an area boundary raises the tier; nothing lowers it). Adoption safe: no
    contract in the repository -> stands down (0).

    This is the READY TRANSITION gate: the /veldo:spec skill runs it before it promotes a
    spec to ready, and the claimable frontier and run-check enforce the same predicate at
    claim and build time. It is DELIBERATELY NOT part of run_all(): the already-shipped
    corpus is past ready and past claim, so it is never re-evaluated here and needs no
    migration. Enforcing it at the transition is what makes O3/RJ2 true without sweeping
    the shipped specs."""
    arch, contract = load_repo_contract(repo_root)
    if contract is None:
        return 0
    text = Path(path).read_text()
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if m is None:
        return fail(path, "no front matter: cannot gate placement at the ready transition")
    try:
        fm = parse_yamlish(m.group(1))
    except ValueError as e:
        return fail(path, f"front matter outside the parser subset: {e}")
    errs = 0
    for msg in arch.placement_gate(fm, contract):
        errs += fail(path, msg)
    # The diagnosability gate (W9 of PLAN-0012), enforced at the SAME ready transition:
    # a behavior-bearing spec (behavior_bearing: true) that declares no observability
    # criteria is REFUSED (the load-bearing product, C1), with the C7 soft join to a
    # system's observability rules in the contract. A spec that is not behavior-bearing
    # (absent or false), including every already-shipped spec, is exempt, so the shipped
    # corpus that passes today keeps passing (RJ6). Adoption safe: this whole transition
    # gate has already stood down above when no contract exists.
    obs = _observability_module()
    for msg in obs.observability_gate(fm, contract):
        errs += fail(path, msg)
    return errs


def _decision_module():
    """Load the decision-record validator (.veldo/decision.py) the same way arch is
    loaded: it receives this module's parser and reporter, so it adds no second YAML
    parser and there is no import cycle. The one place decision.py is loaded."""
    dspec = importlib.util.spec_from_file_location("veldo_decision", ROOT / ".veldo" / "decision.py")
    dec = importlib.util.module_from_spec(dspec)
    dspec.loader.exec_module(dec)
    return dec


def check_decision(path, root=None, required=False):
    """Validate ONE decision record (veldo.decision/v1) structurally, delegating to
    .veldo/decision.py. Adoption safe: an absent record stands down (unless it is
    required); present, or required-and-absent, fails closed."""
    base = Path(root) if root else ROOT
    return _decision_module().check_record(Path(path), base, required, parse_yamlish, fail)


def check_decisions(decisions_dir=None, root=None):
    """Validate the per-repo decision records under .veldo/decisions/ (veldo.decision/v1),
    delegating to .veldo/decision.py. Adoption safe: an absent directory stands down
    (a repository without decision records is byte-identically unaffected), while a
    present record fails closed on anything malformed and a duplicate decision id
    across records is refused. The adversarial decision review (WARP-1106) and the
    in-session tripwire pass (WARP-1107) consume these records; this checks only that
    each record is well formed."""
    base = Path(root) if root else ROOT
    ddir = Path(decisions_dir) if decisions_dir else base / ".veldo" / "decisions"
    return _decision_module().check_decisions_dir(ddir, base, parse_yamlish, fail)


def _decision_review_module():
    """Load the decision-review validator (.veldo/decision_review.py) the same way arch
    and decision are loaded: it receives this module's parser and reporter (and the
    decision loader) so it adds no second YAML parser and there is no import cycle. The
    one place decision_review.py is loaded."""
    drspec = importlib.util.spec_from_file_location("veldo_decision_review", ROOT / ".veldo" / "decision_review.py")
    dr = importlib.util.module_from_spec(drspec)
    drspec.loader.exec_module(dr)
    return dr


def check_decision_review(path, root=None, decisions_dir=None):
    """Validate ONE decision review (veldo.decision_review/v1) structurally, and when a
    decisions_dir is given also BIND it to the decision it reviews (the record must resolve,
    the version must match, and every option and assumption must be covered), delegating to
    .veldo/decision_review.py. Adoption safe: an absent review stands down."""
    base = Path(root) if root else ROOT
    dr = _decision_review_module()
    ld = _decision_module().load_record
    return dr.check_review(Path(path), base, False, parse_yamlish, fail,
                           decisions_dir=decisions_dir, load_decision=ld)


def check_decision_reviews(reviews_dir=None, decisions_dir=None, root=None):
    """Validate the per-repo decision reviews under .veldo/decision_reviews/ and enforce the
    decided-requires-review gate over the decision records (veldo.decision/v1), delegating to
    .veldo/decision_review.py (the W6 organ). Adoption safe: with no .veldo/decisions/ and no
    .veldo/decision_reviews/ directory both stand down (a repository with no decision records is
    byte-identically unaffected), while a present review fails closed on anything malformed or
    unbound and a decided record fails closed unless it carries at least the bound adversarial
    reviews its risk tier requires (read from policy.yaml risk_tiers, D5). The in-session tripwire
    pass over the decision's assumption signals is WARP-1107 (W7)."""
    base = Path(root) if root else ROOT
    rdir = Path(reviews_dir) if reviews_dir else base / ".veldo" / "decision_reviews"
    ddir = Path(decisions_dir) if decisions_dir else base / ".veldo" / "decisions"
    dr = _decision_review_module()
    ld = _decision_module().load_record
    policy_path = base / ".veldo" / "policy.yaml"
    required_for = lambda risk: dr.required_reviews_for(risk, policy_path)
    return dr.check_reviews(rdir, ddir, base, parse_yamlish, fail, required_for, ld)


def _tripwire_module():
    """Load the decision-tripwire evaluator (.veldo/tripwire.py) the same way arch, decision,
    and decision_review are loaded: it receives this module's parser and reporter (and the
    decision loader) so it adds no second YAML parser and there is no import cycle. The one
    place tripwire.py is loaded."""
    tspec = importlib.util.spec_from_file_location("veldo_tripwire", ROOT / ".veldo" / "tripwire.py")
    tw = importlib.util.module_from_spec(tspec)
    tspec.loader.exec_module(tw)
    return tw


def check_readings(path, root=None, decisions_dir=None, now=None):
    """Validate ONE readings file (veldo.readings/v1) structurally, and when a decisions_dir is
    given evaluate it against the decision it names (each reading covers a declared assumption,
    the measured comparators parse, the manual-review fields are well formed), delegating to
    .veldo/tripwire.py. Returns STRUCTURAL errs only (a fired tripwire is surfaced by the gate
    pass, not counted here). Adoption safe: an absent readings file stands down."""
    tw = _tripwire_module()
    ld = _decision_module().load_record
    return tw.check_readings(Path(path), decisions_dir, parse_yamlish, fail, ld, now=now)


def check_tripwires(decisions_dir=None, readings_dir=None, root=None, now=None):
    """The in-session tripwire pass over the per-repo decision records and recorded readings (the
    W7 organ), delegating to .veldo/tripwire.py. Adoption safe: an absent .veldo/decisions/ directory
    stands down (a repository with no decision records is byte-identically unaffected), while a
    DECIDED record with a breached measured reading or a lapsed manual-review fails closed as a
    named finding, and a malformed readings set fails closed. It reads recorded files and starts
    nothing (NG1, no detached process); the re-decision draft a breach hands off is written only by
    the explicit tripwires --draft action, never by this read-only gate pass. The entropy
    restoration loop for the decay class is WARP-1108/WARP-1109 (W8/W9)."""
    base = Path(root) if root else ROOT
    ddir = Path(decisions_dir) if decisions_dir else base / ".veldo" / "decisions"
    rdir = Path(readings_dir) if readings_dir else base / ".veldo" / "readings"
    tw = _tripwire_module()
    ld = _decision_module().load_record
    return tw.check_tripwires(ddir, rdir, base, parse_yamlish, fail, ld, now=now)


def _security_review_module():
    """Load the security review dimension (.veldo/security_review.py), spelled exactly like
    _shape_review_module. It imports nothing itself: the floor modules it re-runs are passed
    in by its caller, so there is no second spelling of what a secret or a wildcard is, and no
    import cycle. The one place security_review.py is loaded (by check_json's verdict security
    validation)."""
    secspec = importlib.util.spec_from_file_location("veldo_security_review", ROOT / ".veldo" / "security_review.py")
    sec = importlib.util.module_from_spec(secspec)
    secspec.loader.exec_module(sec)
    return sec


def _shape_review_module():
    """Load the shape-fit review dimension (.veldo/shape_review.py) the same way arch,
    decision, decision_review, and tripwire are loaded. It imports nothing itself: this
    module passes it the arch helpers (the one place placement and the boundary graph are
    read) and the failure reporter, so there is no second parser and no import cycle. The
    one place shape_review.py is loaded (by check_json's verdict shape_fit validation and
    by check_shape_review)."""
    srspec = importlib.util.spec_from_file_location("veldo_shape_review", ROOT / ".veldo" / "shape_review.py")
    sr = importlib.util.module_from_spec(srspec)
    srspec.loader.exec_module(sr)
    return sr


def check_shape_review(spec_path, changed_paths, repo_root=None):
    """The mechanizable half of the shape-fit review dimension (the W4 organ), at review time:
    compute the mechanical shape-fit findings for a change against this repository's architecture
    contract, from the spec's declared placement/footprint and the diff's paths, delegating to
    .veldo/shape_review.py. Each finding is reported by name and counts as an error, so a change
    that does not fit the declared shape fails closed. Adoption safe: no contract in this
    repository stands the whole check down (0), and the pattern-fit JUDGMENT half is the delegated
    fresh-context reviewer's (shape_review.ShapeReviewer), never graded here."""
    arch, contract = load_repo_contract(repo_root)
    if contract is None:
        return 0
    text = Path(spec_path).read_text()
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if m is None:
        return fail(spec_path, "no front matter: cannot grade shape-fit against the contract")
    try:
        fm = parse_yamlish(m.group(1))
    except ValueError as e:
        return fail(spec_path, f"front matter outside the parser subset: {e}")
    sr = _shape_review_module()
    errs = 0
    for msg in sr.mechanical_shape_findings(fm, contract, list(changed_paths), arch):
        errs += fail(spec_path, msg)
    return errs


# The verdict contract's independent review DIMENSIONS, in the one place they are enumerated.
# Both lanes implement the same interface (validate_dimension / dimension_blocks), so adding a
# third dimension is an entry here and touches neither validate.py nor the merge gate's read.
REVIEW_DIMENSIONS = (("shape_fit", _shape_review_module), ("security", _security_review_module))


def _count_fail(_name, _msg):
    """A non-printing failure counter for READ-ONLY tripwire evaluation (the veldo-status
    surface): returns 1 like fail but prints nothing, so a reader that projects the tripwire
    evaluation into a status model counts malformed readings without writing noise to a JSON
    reader's stream."""
    return 1


def tripwire_status(root=None, now=None):
    """READ-ONLY projection of the in-session tripwire pass for the VELDO STATUS surface (the
    third surface PLAN-0011 W7 names, beside the gate output and the weekly pass). Returns a dict
    {fired, warnings, malformed}: the FIRED tripwires (a breached measured reading or a lapsed
    manual-review) as named findings, the approaching-breach and unmonitored assumptions as
    warnings, and the count of malformed readings (which the gate fails closed) for honesty, over
    the per-repo decision records and recorded readings. This is the SAME evaluation the gate pass
    check_tripwires runs (tripwire.evaluate_tripwires), PROJECTED for a reader rather than failed:
    veldo status (the loop-area runstatus reader) calls this over the allow-listed loop -> contracts
    dependency edge to surface a fired foundation as a named finding while there is still time to
    re-decide. Adoption safe: an absent .veldo/decisions/ directory yields an empty surface (a
    repository with no decision records is byte-identically unaffected). Reads recorded files only
    and starts nothing (NG1, the contract invariant no_detached_processes); the current date is
    injected (an ISO string, or None for today) so the projection is deterministic and testable."""
    base = Path(root) if root else ROOT
    ddir = base / ".veldo" / "decisions"
    rdir = base / ".veldo" / "readings"
    out = {"fired": [], "warnings": [], "malformed": 0}
    if not ddir.is_dir():
        return out
    tw = _tripwire_module()
    ld = _decision_module().load_record
    findings, errs = tw.evaluate_tripwires(ddir, rdir, now, parse_yamlish, _count_fail, ld)
    out["malformed"] = errs
    for f in findings:
        entry = {"decision": f.get("decision"), "assumption": f.get("assumption"),
                 "state": f.get("state"), "detail": f.get("detail"),
                 "statement": f.get("statement")}
        if f.get("state") in tw.FIRED:
            out["fired"].append(entry)
        elif f.get("state") in tw.WARN:
            out["warnings"].append(entry)
    return out


# ---------------------------------------------------------------------------
# The SPEC CORPUS contract: the shape of the depends_on field, and the
# uniqueness of a spec id across the corpus. Both live at the layer that
# DECLARES them rather than in the readers that consume them (the claimable
# frontier, the withheld report, the plan burn-down), because a reader cannot
# defend itself against a shape its own contract admits, and every reader
# would need the same defence. They sit in this sibling module for the same
# reason everything else here does: validate.py is at its module_lines budget.
# ---------------------------------------------------------------------------

def check_depends_on(path, text):
    """TYPE the depends_on field: absent, or a list of whitespace-free spec-id strings.

    The field is declared here, so its shape is decided here. Every reader of it iterates the
    value and looks each member up in a {spec_id: status} map - the claimable frontier, the
    withheld report, the plan burn-down - and an untyped field let shapes through this gate that
    no reader can survive or report honestly: a member that is a mapping or a list is unhashable
    and raises TypeError inside the dispatcher, a bare scalar iterates its CHARACTERS and reports
    a spec as waiting on 'W', 'A', 'R', and a block list mis-indented into 'ID: status' pairs
    yields a member no spec can ever match. Typed at the declaring layer instead of guarded in
    each reader: the readers then cannot meet a shape the contract admits.

    Read with parse_yamlish, the SAME parser every reader uses, because a check that types the
    field as a cruder reader sees it types a different value than the one that reaches the code.

    Absent is legal (most specs declare no dependency at all). A member naming a spec that does
    not exist stays legal on purpose: the frontier must treat it as unshipped and report it, and
    refusing it here would move that case out of reach of the code that handles it."""
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if m is None:
        return 0  # the missing-front-matter red belongs to the caller, not to this field
    try:
        fm = parse_yamlish(m.group(1))
    except ValueError as e:
        return fail(path, f"front matter outside the parser subset, so depends_on cannot be typed: {e}")
    if "depends_on" not in fm:
        return 0
    dep = fm["depends_on"]
    if not isinstance(dep, list):
        return fail(path, f"depends_on must be a LIST of spec ids (use [] for none), not "
                          f"{type(dep).__name__} {dep!r}: readers iterate this value and look each "
                          f"member up in a status map, and a value that is not a list of ids "
                          f"cannot be read that way")
    errs = 0
    for i, d in enumerate(dep):
        if not isinstance(d, str) or d.split() != [d]:
            errs += fail(path, f"depends_on[{i}] must be one whitespace-free spec id string, not "
                               f"{type(d).__name__} {d!r}: readers look each member up in a status "
                               f"map, where a mapping or a list is unhashable and a value carrying "
                               f"whitespace matches no spec id")
    return errs


def check_spec_ids(specs_dir=None):
    """A spec id names EXACTLY ONE spec file, over the whole specs directory.

    Every reader of the corpus builds {spec_id: front_matter} by iterating specs/*.md in sorted
    filename order, so two files declaring one id resolve LAST-WINS and the loser's status is
    invisible: a prerequisite sitting at draft in one file reads as shipped from the other, and
    the dependency gate releases work whose prerequisite does not exist. Refused here, at the
    layer that declares what a spec id is, rather than patched into each reader - the plan
    contract already refuses a duplicate spec across its work items and this is the same rule
    for the corpus itself.

    Directory-scoped and parametrized, so it is testable over a temporary tree. A file whose
    front matter is absent or outside the parser subset is skipped: its own red is check_spec's."""
    d = Path(specs_dir) if specs_dir else ROOT / "specs"
    if not d.is_dir():
        return 0
    by_id = {}
    for p in sorted(d.glob("*.md")):
        if p.name.startswith("TEMPLATE") or p.name == "index.md":
            continue
        m = re.match(r"^---\n(.*?)\n---", p.read_text(), re.S)
        if m is None:
            continue
        try:
            fm = parse_yamlish(m.group(1))
        except ValueError:
            continue
        if fm.get("id"):
            by_id.setdefault(fm["id"], []).append(p.name)
    errs = 0
    for sid, names in sorted(by_id.items()):
        if len(names) > 1:
            errs += fail(str(d), f"spec id {sid} is declared by more than one file "
                                 f"({', '.join(names)}): every reader resolves an id last-wins by "
                                 f"sorted filename, so one file's status silently hides the "
                                 f"other's and an unshipped prerequisite can read as shipped")
    return errs
