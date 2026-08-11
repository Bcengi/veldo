#!/usr/bin/env python3
"""VELDO shape gate (the W2 organ of PLAN-0011): gate-time enforcement of the
mechanizable shape rules the architecture contract declares.

scripts/verify.sh calls this after the contract validator. It reads
.veldo/architecture.yaml and, for every rule the contract marks
enforcement: mechanizable, applies the enforcement that REFUSES a violation and
fails the gate with the rule NAMED, before any reviewer sees it (outcome O2). A
rule the contract marks enforcement: review is reviewer guidance and is surfaced
as a NON-BLOCKING note, never a gate refusal - the honest reading of "mechanizable
shape rules" (NG5: the gate never carries a vacuous check, and a rule that cannot
be checked mechanically stays honestly in the review lane).

Two postures, both load bearing and shared with the sibling organs (W1, W3, W4):

  ADOPTION SAFE (C2). A repository with no architecture contract stands the whole
  gate down (returns 0, prints one standdown line), so adding this check changes no
  existing gate and a contract-free repository is byte-identically unaffected.

  FAIL CLOSED (C2, C1, NG5). The moment a contract exists the mechanizable rules
  fail closed. A contract that marks a rule mechanizable which this gate has NO
  wired enforcement for REFUSES by name (you cannot mark a rule mechanizable and
  enforce nothing - the anti-vacuity rule), and a mechanizable rule whose enforcing
  check has been deleted REFUSES by name (the enforcement can never silently vanish).

CHANGE SCOPED, never a corpus re-sweep (the W3 posture restated). The size budget
binds the files THIS CHANGE touches (the diff against the trunk plus the working
tree), exactly as W3's placement gate is enforced at the transition and the claim
and never as a static sweep of the already-shipped corpus. A change that ADDS a new
over-budget module, or GROWS a module past its budget, fails the gate; the historical
corpus is grandfathered and not retroactively refused. This is the ONLY green-safe
reading here: this repository's own .veldo/validate.py already exceeds the file_lines
budget (a pre-contract module), so a whole-tree corpus sweep at max would turn the
current green gate red - which the size rule must not do. Bringing that module under
budget is a separate restoration unit (the W8/W9 entropy loop), not this gate's job;
this gate stops NEW entropy at the cheapest moment.

FOOTPRINT VERSUS DIFF (deferred from W3, the O3 half W3 left to W2). When the change
set names EXACTLY ONE spec that declares a footprint, every changed source path must
be covered by that spec's declared footprint globs, or the gate refuses by name (a
change may not silently touch a path its spec never declared). Scoped precisely to be
green safe: it stands down when the change set names zero footprinted specs (the clean
committed tree) or more than one (a multi-spec landing is out of this item's scope,
stated honestly), and it reuses the ONE glob compiler arch._glob_re, so footprint
coverage and area resolution agree on what a glob matches. It never re-sweeps the
shipped corpus: a shipped spec's footprint is only re-examined if that spec file is
itself in the change set.

D6 pluggable per-language reference slot. Stdlib reference implementations for the
import-boundary, function-length, duplication, and complexity checks ship here
(the analyzer functions), dispatched by rule kind so they are the reference the
contract's analyzers slot names. They are enforced (gate-blocking) only when the
contract marks their rule mechanizable AND the code is proven to pass; while the
contract marks them review (as it does today, honestly) they are surfaced as
non-blocking notes over the changed governed sources. Nothing here flips a rule from
review to mechanizable; the contract's enforcement label is the sole authority.

Dependency free of a second parser: it loads .veldo/validate.py (the one front-matter
parser, parse_yamlish) and .veldo/arch.py (the one place a path maps to an area and a
modeled boundary is defined) the same way plan.py does, so there is no second YAML
parser, no second glob compiler, and no second placement or boundary implementation.
"""
import ast
import importlib.util
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Runtime and derived artifacts the gate itself writes or regenerates are NOT "the
# change": the gate stamps .veldo/last_verify and appends .veldo/events.jsonl on every
# run, and specs/index.md is derived (governed by derived_never_authoritative, which
# regenerates it), so footprint-versus-diff excludes them rather than demand a spec
# declare its own gate bookkeeping. proof/ is evidence, not source.
_DIFF_EXCLUDE_EXACT = {".veldo/last_verify", ".veldo/events.jsonl", "specs/index.md"}
_DIFF_EXCLUDE_PREFIX = ("proof/",)

# The VELDO engine invariants and patterns this gate ships enforcement for. A contract
# that marks one of these mechanizable is enforced by the named catalog check(s), and
# the gate fails closed if a named enforcing check has been deleted (the enforcement
# can never silently vanish). adoption_safe_fail_closed is enforced by THIS gate's own
# stand-down (an empty tuple: no external file, the gate embodies it and the selftest
# proves it). A mechanizable prose rule whose id is NOT here has no wired enforcement
# and is refused (anti-vacuity): a novel mechanizable pattern must wire an analyzer via
# the pluggable slot or stay in the review lane.
_ENGINE_PROSE_ENFORCEMENT = {
    "engine_byte_identical": ("scripts/check_pack_drift.py", "scripts/check_template_sync.sh"),
    "derived_never_authoritative": ("scripts/check_generated.sh",),
    "adoption_safe_fail_closed": (),
}

# The budget kinds this gate has a stdlib reference implementation for (the D6 slot).
# A mechanizable budget of one of these kinds is enforced; a mechanizable budget of an
# unknown kind is refused by name (anti-vacuity). validate_contract already rejects an
# unknown kind at contract time, so this is defense in depth.
_BUDGET_KINDS = {"file_lines", "function_lines", "duplication_ratio", "cyclomatic_complexity"}


def _load(root):
    """(V, arch, contract) for root, reusing the one parser and the one contract loader
    (validate.load_repo_contract). The validate module and, through it, arch.py are loaded
    from THIS engine's location (the way check_placement does), while the CONTRACT is read
    from repo_root, so the gate runs in-repo in production (root is the repo) and a test can
    point root at a temporary tree without copying the engine. contract is None when no
    contract exists or it is malformed (adoption safe: a malformed contract is reported by the
    contract validator, not double refused here)."""
    vspec = importlib.util.spec_from_file_location("veldo_validate_shape", ROOT / ".veldo" / "validate.py")
    V = importlib.util.module_from_spec(vspec)
    vspec.loader.exec_module(V)
    arch, contract = V.load_repo_contract(repo_root=str(root))
    return V, arch, contract


def _as_list(v):
    return v if isinstance(v, list) else []


def _is_str(v):
    return isinstance(v, str) and v.strip() != ""


def _line_count(path):
    try:
        return len(Path(path).read_text().splitlines())
    except OSError:
        return 0


# ---------------------------------------------------------------------------
# The change set: the files THIS change touches, so the size and footprint rules
# bind the change and never re-sweep the shipped corpus.
# ---------------------------------------------------------------------------

def _git(root, *args):
    try:
        r = subprocess.run(["git", *args], cwd=str(root), capture_output=True, text=True)
    except (OSError, ValueError):
        return []
    if r.returncode != 0:
        return []
    return [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]


def _denied(rel):
    return rel in _DIFF_EXCLUDE_EXACT or any(rel.startswith(p) for p in _DIFF_EXCLUDE_PREFIX)


def changed_source_paths(root):
    """The repo-relative source paths this change touches: the working tree (unstaged and
    staged) plus untracked files plus the commits ahead of the trunk (merge-base..HEAD).
    Runtime/derived/evidence artifacts are excluded (they are not the change). Empty when
    git is unavailable or nothing changed, so the size and footprint rules simply have
    nothing to bind (green), never a corpus sweep."""
    paths = set()
    paths |= set(_git(root, "diff", "--name-only", "HEAD"))
    paths |= set(_git(root, "diff", "--name-only", "--cached"))
    paths |= set(_git(root, "ls-files", "--others", "--exclude-standard"))
    head = _git(root, "rev-parse", "HEAD")
    head = head[0] if head else ""
    for ref in ("origin/main", "origin/master", "main", "master"):
        base = _git(root, "rev-parse", "--verify", ref)
        if base and base[0] and base[0] != head:
            paths |= set(_git(root, "diff", "--name-only", ref + "...HEAD"))
            break
    return {p for p in paths if p and not _denied(p)}


# ---------------------------------------------------------------------------
# The stdlib reference analyzers (the D6 pluggable per-language slot). Each returns a
# list of finding strings over a set of python source files. They are the reference the
# contract's analyzers slot names; the contract's enforcement label decides whether a
# finding blocks the gate (mechanizable) or is a reviewer note (review).
# ---------------------------------------------------------------------------

def _py_sources(paths, root):
    out = []
    for rel in sorted(paths):
        if rel.endswith(".py"):
            p = Path(root) / rel
            if p.is_file():
                out.append((rel, p))
    return out


def _parse(path):
    try:
        return ast.parse(Path(path).read_text())
    except (OSError, SyntaxError):
        return None


def function_length_findings(paths, root, max_lines):
    """Reference function-length analyzer: a def/async def whose span exceeds max_lines."""
    findings = []
    for rel, p in _py_sources(paths, root):
        tree = _parse(p)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                end = getattr(node, "end_lineno", None)
                if end is not None:
                    span = end - node.lineno + 1
                    if span > max_lines:
                        findings.append("function_lines: %s:%d %s is %d lines, over the %d-line budget"
                                        % (rel, node.lineno, node.name, span, max_lines))
    return findings


_BRANCH_NODES = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler,
                 ast.With, ast.AsyncWith, ast.IfExp, ast.comprehension, ast.Assert)


def complexity_findings(paths, root, max_cc):
    """Reference cyclomatic-complexity analyzer: 1 + the branch nodes and boolean
    operators inside each function, refused over max_cc."""
    findings = []
    for rel, p in _py_sources(paths, root):
        tree = _parse(p)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                cc = 1
                for sub in ast.walk(node):
                    if isinstance(sub, _BRANCH_NODES):
                        cc += 1
                    elif isinstance(sub, ast.BoolOp):
                        cc += len(sub.values) - 1
                if cc > max_cc:
                    findings.append("cyclomatic_complexity: %s:%d %s has complexity %d, over the %d budget"
                                    % (rel, node.lineno, node.name, cc, max_cc))
    return findings


def duplication_findings(paths, root, max_ratio):
    """Reference duplication analyzer: the percentage of non-trivial lines that recur (a
    normalized line appearing more than once), refused over max_ratio percent. Proportionate
    and stdlib: a line-level signal, not a token clone detector, honestly labeled."""
    findings = []
    for rel, p in _py_sources(paths, root):
        lines = [ln.strip() for ln in Path(p).read_text().splitlines()]
        lines = [ln for ln in lines if len(ln) > 12 and not ln.startswith("#")]
        if len(lines) < 20:
            continue
        seen, dup = {}, 0
        for ln in lines:
            seen[ln] = seen.get(ln, 0) + 1
        for ln, n in seen.items():
            if n > 1:
                dup += n - 1
        ratio = round(100 * dup / len(lines))
        if ratio > max_ratio:
            findings.append("duplication_ratio: %s is %d%% duplicated lines, over the %d%% budget"
                            % (rel, ratio, max_ratio))
    return findings


def boundary_findings(paths, root, contract, arch):
    """Reference import-boundary analyzer: a source file in one declared area that loads a
    module in another declared area over an edge the contract's dependencies.allow does not
    model is a boundary violation. It reads the intra-repo module reference the VELDO engine
    actually uses - spec_from_file_location(name, ROOT/'.veldo'/'X.py') and the co-located
    string paths - and maps both ends to their area through arch.area_for_path, the one place
    a path resolves to an area. Best effort by construction (dynamic loading is not fully
    statically resolvable), which is exactly why the contract marks dependencies review."""
    findings = []
    edges = arch._allowed_edges(contract)
    for rel, p in _py_sources(paths, root):
        src_areas = arch.area_for_path(rel, contract)
        if not src_areas:
            continue
        text = Path(p).read_text()
        for other in _referenced_veldo_modules(text):
            tgt_areas = arch.area_for_path(other, contract)
            for sa in sorted(src_areas):
                for ta in sorted(tgt_areas):
                    if sa != ta and not arch._areas_connected(sa, ta, edges):
                        findings.append("dependencies: %s (area %s) references %s (area %s) over an "
                                        "edge dependencies.allow does not model" % (rel, sa, other, ta))
    return findings


def _referenced_veldo_modules(text):
    """The repo-relative .veldo module paths a source references through the engine's
    spec_from_file_location(name, ROOT / '.veldo' / 'X.py') idiom. A best-effort static read
    of the one coupling shape the engine uses; it invents no edge it cannot see."""
    import re
    refs = set()
    for m in re.finditer(r"\.veldo\"\s*[,/]\s*\"([A-Za-z_][A-Za-z0-9_]*\.py)\"", text):
        refs.add(".veldo/" + m.group(1))
    for m in re.finditer(r"\"\.veldo/([A-Za-z_][A-Za-z0-9_]*\.py)\"", text):
        refs.add(".veldo/" + m.group(1))
    return sorted(refs)


# ---------------------------------------------------------------------------
# The mechanizable rule enforcement.
# ---------------------------------------------------------------------------

def _in_budget_scope(rel, applies_to, contract, arch):
    """A changed file is in a budget's scope when it is GOVERNED (resolves to a declared
    area) and the budget's applies_to is '*' or one of the file's areas. A file outside the
    declared shape (no area) is outside every budget: the contract governs the shape it
    declares."""
    areas = arch.area_for_path(rel, contract)
    if not areas:
        return False
    return applies_to == "*" or applies_to in areas


def file_lines_findings(changed, root, budget, contract, arch):
    """Enforce one file_lines budget over the CHANGED governed files in its scope. A
    changed file over the budget refuses by name; the shipped corpus is untouched (only
    changed files are examined)."""
    findings = []
    for rel in sorted(changed):
        if not _in_budget_scope(rel, budget.get("applies_to"), contract, arch):
            continue
        n = _line_count(Path(root) / rel)
        if n > budget["max"]:
            findings.append("budget %s (file_lines): %s is %d lines, over the %d-line budget"
                            % (budget.get("id"), rel, n, budget["max"]))
    return findings


def _budget_by_kind_findings(kind, changed, root, budget, contract, arch):
    """The reference analyzer for a non-file_lines budget kind, over the changed governed
    python sources in scope. Used gate-blocking when the budget is mechanizable, and for
    the review-lane notes otherwise."""
    in_scope = [rel for rel in changed if _in_budget_scope(rel, budget.get("applies_to"), contract, arch)]
    mx = budget["max"]
    if kind == "function_lines":
        return function_length_findings(in_scope, root, mx)
    if kind == "cyclomatic_complexity":
        return complexity_findings(in_scope, root, mx)
    if kind == "duplication_ratio":
        return duplication_findings(in_scope, root, mx)
    return []


def prose_enforcement_findings(rule_id, root):
    """Confirm a mechanizable engine invariant/pattern is wired: its named enforcing
    catalog check(s) exist, else refuse (the enforcement can never silently vanish). An
    UNKNOWN mechanizable prose id has no wired enforcement and refuses (anti-vacuity)."""
    if rule_id not in _ENGINE_PROSE_ENFORCEMENT:
        return ["mechanizable rule %r has no wired gate enforcement: wire a per-language "
                "analyzer (the pluggable slot) or mark it review-lane (a mechanizable rule "
                "the gate cannot enforce is exactly the vacuous check NG5 forbids)" % rule_id]
    missing = [c for c in _ENGINE_PROSE_ENFORCEMENT[rule_id] if not (Path(root) / c).is_file()]
    if missing:
        return ["mechanizable rule %r is enforced by %s, which is absent (the enforcement "
                "may not silently vanish)" % (rule_id, ", ".join(missing))]
    return []


def footprint_findings(changed, root, V, arch):
    """Footprint versus diff (the O3 half deferred from W3). When the change set names
    EXACTLY ONE spec that declares a footprint, every changed source path must be covered
    by that spec's footprint globs. Stands down for zero or more than one footprinted spec
    (green safe, no corpus re-sweep). Reuses the one glob compiler arch._glob_re and the one
    parser (V.parse_yamlish), so it introduces no second glob or parser implementation."""
    specs = []
    for rel in sorted(changed):
        if rel.startswith("specs/") and rel.endswith(".md") and (Path(root) / rel).is_file():
            fm = _spec_fm(V, Path(root) / rel)
            fp = [g for g in _as_list(fm.get("footprint")) if _is_str(g)]
            if fp:
                specs.append((rel, fp))
    if len(specs) != 1:
        return []
    spec_rel, globs = specs[0]
    regexes = [arch._glob_re(g) for g in globs]
    findings = []
    for rel in sorted(changed):
        if not any(rx.match(rel) for rx in regexes):
            findings.append("the diff touches %r, outside the footprint declared by %s: a change "
                            "may not silently touch a path its spec did not declare"
                            % (rel, spec_rel))
    return findings


def _spec_fm(V, path):
    text = Path(path).read_text()
    m = V.re.match(r"^---\n(.*?)\n---", text, V.re.S)
    if not m:
        return {}
    try:
        return V.parse_yamlish(m.group(1))
    except ValueError:
        return {}


# ---------------------------------------------------------------------------
# The gate driver.
# ---------------------------------------------------------------------------

def run(root=None, changed=None):
    """Run the shape gate over root. Returns (standdown, problems, notes): standdown True
    when no contract exists (adoption safe); problems the gate-BLOCKING refusals; notes the
    NON-BLOCKING reviewer-guidance findings. Pure over the loaded contract and the change set
    except for reading source files."""
    root = Path(root or ROOT)
    V, arch, contract = _load(root)
    if contract is None:
        return True, [], []
    if changed is None:
        changed = changed_source_paths(root)
    problems, notes = [], []

    # Budgets, dispatched by kind. mechanizable -> gate-blocking; review -> note.
    for b in _as_list(contract.get("budgets")):
        if not isinstance(b, dict) or not _is_str(b.get("id")):
            continue
        kind, label = b.get("kind"), b.get("enforcement")
        if kind not in _BUDGET_KINDS:
            if label == "mechanizable":
                problems.append("budget %s: mechanizable but kind %r has no reference implementation"
                                % (b.get("id"), kind))
            continue
        if kind == "file_lines":
            found = file_lines_findings(changed, root, b, contract, arch)
        else:
            found = _budget_by_kind_findings(kind, changed, root, b, contract, arch)
        (problems if label == "mechanizable" else notes).extend(found)

    # Dependencies block, dispatched by its enforcement label.
    deps = contract.get("dependencies")
    if isinstance(deps, dict):
        found = boundary_findings(changed, root, contract, arch)
        (problems if deps.get("enforcement") == "mechanizable" else notes).extend(found)

    # Patterns and invariants: free-text prose. mechanizable -> confirm the wired engine
    # enforcement (fail closed on an unknown id or a deleted check); review -> a note that
    # names the rule as reviewer guidance.
    for block in ("patterns", "invariants"):
        for r in _as_list(contract.get(block)):
            if not isinstance(r, dict) or not _is_str(r.get("id")):
                continue
            if r.get("enforcement") == "mechanizable":
                problems.extend(prose_enforcement_findings(r["id"], root))
            else:
                notes.append("%s %s (review lane): reviewer guidance, not gate-enforced" % (block[:-1], r["id"]))

    # Footprint versus diff (the O3 half deferred from W3).
    problems.extend(footprint_findings(changed, root, V, arch))
    return False, problems, notes


def main():
    try:
        standdown, problems, notes = run()
    except Exception as e:  # fail closed: an unexpected error never passes the gate silently
        print("   shape gate: FAIL (error while enforcing the contract: %s)" % e)
        return 1
    if standdown:
        print("   shape gate: no architecture contract, standing down (adoption safe)")
        return 0
    for n in notes:
        print("   shape (review lane, non-blocking): %s" % n)
    if problems:
        for p in problems:
            print("   shape gate FAIL: %s" % p)
        print("   shape gate: %d mechanizable-rule violation(s)" % len(problems))
        return 1
    print("   shape gate: pass (mechanizable rules enforced; review-lane rules are reviewer guidance)")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
