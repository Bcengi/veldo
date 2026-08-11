#!/usr/bin/env python3
"""VELDO contract validator. Proportionate by design: required-field checks,
not a schema stack. Used by verify.sh; also runnable directly.

Usage:
  python3 .veldo/validate.py all                 # validate specs, plans, proofs, examples
  python3 .veldo/validate.py spec <file.md>
  python3 .veldo/validate.py plan <file.md>
  python3 .veldo/validate.py proof <manifest.json>
  python3 .veldo/validate.py verdict <verdict.json>
  python3 .veldo/validate.py approval <approval.json>
  python3 .veldo/validate.py arch [<architecture.yaml>]
  python3 .veldo/validate.py decisions [<record.yaml | dir>]
  python3 .veldo/validate.py requests [<record.yaml | dir>]
  python3 .veldo/validate.py decision-review [<review.yaml | dir>]
  python3 .veldo/validate.py tripwires [<readings.yaml> | --draft]
  python3 .veldo/validate.py placement <spec.md>
  python3 .veldo/validate.py ready <spec.md>
  python3 .veldo/validate.py shape-review <spec.md> [changed-path ...]
"""
import importlib.util
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The routing resolver (WARP-0601) is the one place that reads the per-org
# tracker config and knows the set of routable repos. Enforcement here REUSES
# it - it never reimplements config parsing or resolution.
_trspec = importlib.util.spec_from_file_location("veldo_tracker", ROOT / ".veldo" / "tracker.py")
_TRACKER = importlib.util.module_from_spec(_trspec)
_trspec.loader.exec_module(_TRACKER)

SPEC_STATUSES = {"draft", "ready", "in_progress", "review", "proven", "shipped", "blocked"}
RISKS = {"low", "standard", "high", "critical"}
VERDICTS = {"pass", "pass_with_notes", "fail", "escalate"}
PLAN_STATUSES = {"draft", "ready", "in_progress", "released", "closed"}
PLAN_KINDS = {"iteration", "mvp", "release"}
RELEASE_MODES = {"continuous", "coordinated"}


def fail(name, msg):
    print(f"  {name}: {msg}")
    return 1


def front_matter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None
    fm = {}
    key = None
    for line in m.group(1).splitlines():
        if re.match(r"^[A-Za-z_]+:", line):
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip()
        elif key and line.strip().startswith("-"):
            fm.setdefault(key + "__list", []).append(line.strip())
    return fm


def check_tracker_repo(path, fm, repo_root=None):
    """Optional per-repo routing target, enforced parallel to the lane fields.

    A spec or plan mirrored to an external tracker names the repo it targets in
    tracker_repo, because one tracker project (a Jira project, say) spans many
    repos. The field is OPTIONAL - omit it for the single-repo default, which is
    every spec and plan in this repo today. When present it must be a non-empty
    string; and when a tracker config is wired for this repo (.veldo/trackers.json,
    loaded via .veldo/tracker.py) the value MUST be a repo id that config knows or
    it FAILS CLOSED by name - a routing target nobody can resolve is a decision
    nobody made. When no config is present the integration is simply not wired
    here, so a present field is allowed but not enforced. Reuses the resolver to
    read the config and the known repo ids; it does not reimplement resolution."""
    if "tracker_repo" not in fm:
        return 0
    val = fm.get("tracker_repo")
    if not isinstance(val, str) or not val.strip():
        return fail(path, "tracker_repo, when present, must be a non-empty string")
    repo = val.strip()
    if len(repo) >= 2 and repo[0] == repo[-1] and repo[0] in "\"'":
        repo = repo[1:-1].strip()
    if not repo:
        return fail(path, "tracker_repo, when present, must be a non-empty string")
    cfg = _TRACKER.load_tracker_config(repo_root=str(repo_root or ROOT))
    if not cfg:
        return 0  # integration not wired for this repo: allowed, not enforced
    known = _TRACKER._known_repo_ids(cfg)
    if repo not in known:
        return fail(path, f"tracker_repo {repo!r} is not a known repo in the tracker config (known: {sorted(known)})")
    return 0


def check_spec(path, repo_root=None):
    errs = 0
    text = Path(path).read_text()
    fm = front_matter(text)
    if fm is None:
        return fail(path, "no YAML front matter")
    for field in ("schema", "id", "title", "status", "risk", "owner"):
        if field not in fm:
            errs += fail(path, f"missing front-matter field: {field}")
    if fm.get("status") and fm["status"] not in SPEC_STATUSES:
        errs += fail(path, f"bad status: {fm['status']}")
    if fm.get("risk") and fm["risk"].split()[0] not in RISKS:
        errs += fail(path, f"bad risk: {fm['risk']}")
    if "acceptance_criteria__list" not in fm and "acceptance_criteria" not in fm:
        errs += fail(path, "no acceptance criteria")
    if fm.get("required_evidence"):
        for kind in [k.strip() for k in fm["required_evidence"].strip("[]").split(",") if k.strip()]:
            if kind not in CANONICAL_KINDS:
                errs += fail(path, f"unknown evidence kind '{kind}' (canonical: {sorted(CANONICAL_KINDS)})")
    # Lane fields: a spec is planned (bound to a Product Plan work item) or
    # standalone (the direct path for bugs and isolated work). When 'lane' is
    # declared it must agree with the presence of plan/work; when it is
    # absent the lane is inferred, so older specs stay valid.
    lane = fm.get("lane")
    has_plan, has_work = bool(fm.get("plan")), bool(fm.get("work"))
    if lane is not None:
        if lane not in ("planned", "standalone"):
            errs += fail(path, f"bad lane: {lane!r} (planned | standalone)")
        elif lane == "planned" and not (has_plan and has_work):
            errs += fail(path, "lane: planned requires both plan and work")
        elif lane == "standalone" and (has_plan or has_work):
            errs += fail(path, "lane: standalone must not declare plan or work")
    errs += check_depends_on(path, text)
    errs += check_tracker_repo(path, fm, repo_root)
    errs += check_placement(path, repo_root)
    errs += check_observability(path, repo_root) + _VC.check_falsification_declared(path, repo_root)
    return errs


EVIDENCE_KIND_ALIASES = {
    # spec vocabulary -> acceptable evidence "type" values or check names in the proof
    "unit": {"unit", "test"},
    "integration": {"integration", "test"},
    "journeys": {"journeys", "journey", "e2e"},
    "ui_states": {"ui_states", "state_capture"},
    "figma_composite": {"figma_composite", "composite", "visual"},
    "interaction_recording": {"interaction_recording", "recording", "video"},
    "baseline": {"baseline", "visual_baselines"},
    "device_matrix": {"device_matrix", "matrix"},
    "design_review": {"design_review"},
    "operational": {"operational"},
    "staging_run": {"staging_run", "staging"},
}


def evidence_kinds_in_proof(data):
    kinds = set()
    for c in data.get("criteria", []):
        for e in c.get("evidence", []):
            if e.get("type"):
                kinds.add(e["type"])
    for ch in data.get("checks", []):
        if ch.get("name"):
            kinds.add(ch["name"])
    return kinds


CANONICAL_KINDS = set(EVIDENCE_KIND_ALIASES.keys())


def check_required_evidence(spec_path, proof_path):
    """Every kind the spec declares in required_evidence must appear in the
    proof (as an evidence type or a check name, via the alias table).
    design_review is satisfied by a design-verdict file next to the manifest."""
    errs = 0
    fm = front_matter(Path(spec_path).read_text())
    declared = []
    if fm and "required_evidence" in fm:
        declared = [k.strip() for k in fm["required_evidence"].strip("[]").split(",") if k.strip()]
    if not declared:
        return 0
    try:
        data = json.loads(Path(proof_path).read_text())
    except Exception:
        return fail(proof_path, "unreadable proof for required-evidence check")
    present = evidence_kinds_in_proof(data)
    for kind in declared:
        if kind not in CANONICAL_KINDS:
            errs += fail(spec_path, f"unknown evidence kind '{kind}' (canonical vocabulary: {sorted(CANONICAL_KINDS)})")
            continue
        accepted = EVIDENCE_KIND_ALIASES[kind]
        if kind == "design_review":
            # THROUGH THE ONE ENUMERATION (WARP-0727 round 2), never a private glob. This was a
            # SECOND spelling of a set the corpus owner already declares DESIGN_VERDICT_PATTERN
            # for; it agreed with the owner on this platform, which is what makes it a law
            # violation rather than a live divergence. The owner is asked about the proof root
            # and the answer is narrowed to the manifest's own spec directory, so the membership
            # rule that decides the corpus decides this too.
            _spec_dir = Path(proof_path).parent
            if not [p for p in _CORPUS.corpus_in_dir(_spec_dir.parent,
                                                     _CORPUS.DESIGN_VERDICT_PATTERN)
                    if p.parent == _spec_dir]:
                errs += fail(proof_path, "required design_review: no design-verdict*.json beside the manifest")
            continue
        if not (accepted & present):
            errs += fail(proof_path, f"required evidence kind '{kind}' absent from proof (no matching evidence type or check name)")
    return errs


def spec_criterion_ids(spec_path):
    text = Path(spec_path).read_text()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return []
    return re.findall(r"^\s*-\s*id:\s*(\S+)", m.group(1), re.M)


def check_criteria_coverage(spec_path, proof_path):
    """Every spec criterion appears exactly once in the proof; no invented ids."""
    errs = 0
    want = spec_criterion_ids(spec_path)
    try:
        data = json.loads(Path(proof_path).read_text())
    except Exception:
        return 0
    have = [c.get("id") for c in data.get("criteria", [])]
    for cid in want:
        if cid not in have:
            errs += fail(proof_path, f"spec criterion {cid} missing from proof")
    for cid in have:
        if cid not in want:
            errs += fail(proof_path, f"proof criterion {cid} not in the specification (invented)")
        if have.count(cid) > 1:
            errs += fail(proof_path, f"duplicate proof criterion {cid}")
    return errs


import hashlib as _hashlib


def proof_digest(manifest):
    """Stable digest of a proof manifest's substance (spec, criteria, checks).
    Canonical copy; policy_check has an identical one and selftest guards drift."""
    payload = {
        "spec_id": manifest.get("spec_id"),
        "commit": manifest.get("commit"),
        "criteria": manifest.get("criteria"),
        "checks": manifest.get("checks"),
    }
    blob = json.dumps(payload, sort_keys=True, default=str)
    return "sha256:" + _hashlib.sha256(blob.encode()).hexdigest()[:16]


def check_json(path, required, name):
    errs = 0
    try:
        data = json.loads(Path(path).read_text())
    except Exception as e:
        return fail(path, f"invalid JSON: {e}")
    for field in required:
        if field not in data:
            errs += fail(path, f"missing field: {field}")
    if name == "proof":
        for c in data.get("criteria", []):
            if c.get("status") == "passed" and not c.get("evidence"):
                errs += fail(path, f"criterion {c.get('id')} passed without evidence")
    if name == "approval" and data.get("decision") not in ("approved", "rejected"):
        errs += fail(path, f"bad approval decision: {data.get('decision')!r} (canonical: approved, rejected) - a near-miss value makes the approval silently inert")
    if name == "verdict":
        if data.get("verdict") not in VERDICTS:
            errs += fail(path, f"bad verdict: {data.get('verdict')}")
        fnd = data.get("findings")
        if fnd is not None:
            if isinstance(fnd, dict):
                for k in fnd:
                    if k not in ("blocking", "non_blocking"):
                        errs += fail(path, f"findings dict key '{k}' (allowed: blocking, non_blocking)")
                for k in ("blocking", "non_blocking"):
                    if k in fnd and not isinstance(fnd[k], list):
                        errs += fail(path, f"findings.{k} must be a list")
            elif isinstance(fnd, list):
                for item in fnd:
                    if not isinstance(item, dict) or item.get("severity") not in ("blocking", "note") or not item.get("text"):
                        errs += fail(path, "list-shaped findings entries need severity blocking|note and text")
            else:
                errs += fail(path, "findings must be a dict {blocking, non_blocking} or a list of {severity, text}")
        # The verdict carries the independent review DIMENSIONS (shape-fit PLAN-0011 W4, security
        # PLAN-0013 W9), each validating itself fail closed through the one dimension interface and
        # enumerated ONCE in validate_checks.REVIEW_DIMENSIONS, so a third never edits this file.
        for _dim, _load in _VC.REVIEW_DIMENSIONS:
            if data.get(_dim) is not None:
                errs += _load().validate_dimension(data.get(_dim), path, fail)
    return errs


PROOF_REQ = ["schema", "spec_id", "commit", "producer", "criteria", "checks", "rollback"]
VERDICT_REQ = ["schema", "spec_id", "commit", "reviewer", "verdict", "criteria"]
APPROVAL_REQ = ["schema", "id", "decision", "approver", "scope", "recorded_at", "expires_at"]


# ---------------------------------------------------------------------------
# Product Plans (veldo.plan/v1): the layer above specs. A plan is holistic
# intent decomposed into ordered, dependency-declared work items; the
# validator makes the ordering mechanical instead of aspirational.
# ---------------------------------------------------------------------------

def _split_top(s, sep):
    """Split on sep at bracket/brace/quote depth zero."""
    out, buf, depth, quote = [], [], 0, None
    for ch in s:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            buf.append(ch)
        elif ch in "[{":
            depth += 1
            buf.append(ch)
        elif ch in "]}":
            depth -= 1
            buf.append(ch)
        elif ch == sep and depth == 0:
            out.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        out.append("".join(buf))
    return out


def _scalar(s):
    s = s.strip()
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        return [_scalar(x) for x in _split_top(inner, ",")] if inner else []
    if s.startswith("{") and s.endswith("}"):
        out = {}
        inner = s[1:-1].strip()
        if inner:
            for part in _split_top(inner, ","):
                k, _, v = part.partition(":")
                out[k.strip()] = _scalar(v)
        return out
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    return s


_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):(.*)$")


def parse_yamlish(src):
    """Parse the VELDO front-matter subset: nested maps, lists of maps, lists
    of scalars, inline [] and {}, and deeper-indented continuation lines
    folded into the previous scalar. Deliberately dependency-free: the
    contract is this subset, not full YAML, so behavior is identical on
    every machine. Raises ValueError with a line hint on anything outside
    the subset."""
    ls = []
    for n, raw in enumerate(src.splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw[:len(raw) - len(raw.lstrip())].count("\t"):
            raise ValueError(f"tab indentation (line {n}): the subset is space-indented only")
        ls.append((len(raw) - len(raw.lstrip(" ")), raw.strip()))
    val, i = _parse_block(ls, 0, 0)
    if i != len(ls):
        raise ValueError(f"unparsed trailing content near: {ls[i][1]!r}")
    return val if val is not None else {}


def _parse_block(ls, i, ind):
    if i >= len(ls) or ls[i][0] < ind:
        return None, i
    if ls[i][1].startswith("- ") or ls[i][1] == "-":
        return _parse_list(ls, i, ls[i][0])
    return _parse_map(ls, i, ls[i][0])


def _parse_map(ls, i, ind):
    out, lastkey = {}, None
    while i < len(ls):
        lind, txt = ls[i]
        if lind < ind:
            break
        if lind > ind:
            if lastkey is not None and isinstance(out.get(lastkey), str):
                out[lastkey] = out[lastkey] + " " + txt
                i += 1
                continue
            raise ValueError(f"unexpected indent near: {txt!r}")
        if txt.startswith("- "):
            raise ValueError(f"list item at map level near: {txt!r}")
        m = _KEY_RE.match(txt)
        if not m:
            raise ValueError(f"expected 'key: value' near: {txt!r}")
        key, rest = m.group(1), m.group(2).strip()
        if key in out:
            raise ValueError(f"duplicate key {key!r}: last-wins would silently drop the first value")
        i += 1
        if rest == "":
            if i < len(ls) and ls[i][0] > ind:
                val, i = _parse_block(ls, i, ls[i][0])
            else:
                val = None
            out[key] = val
            lastkey = None
        else:
            out[key] = _scalar(rest)
            lastkey = key if isinstance(out[key], str) else None
    return out, i


def _parse_list(ls, i, ind):
    out = []
    while i < len(ls) and ls[i][0] == ind and (ls[i][1].startswith("- ") or ls[i][1] == "-"):
        body = ls[i][1][2:].strip() if ls[i][1] != "-" else ""
        i += 1
        m = _KEY_RE.match(body) if body else None
        if m:
            # map item: first key inline after the dash, siblings indented deeper
            item_ind = ind + 2
            item, lastkey = {}, None
            key, rest = m.group(1), m.group(2).strip()
            if rest == "":
                if i < len(ls) and ls[i][0] > item_ind:
                    val, i = _parse_block(ls, i, ls[i][0])
                else:
                    val = None
                item[key] = val
            else:
                item[key] = _scalar(rest)
                lastkey = key if isinstance(item[key], str) else None
            while i < len(ls) and ls[i][0] > ind:
                lind2, txt2 = ls[i]
                if lind2 == item_ind and not txt2.startswith("- "):
                    m2 = _KEY_RE.match(txt2)
                    if not m2:
                        raise ValueError(f"expected 'key: value' near: {txt2!r}")
                    key, rest = m2.group(1), m2.group(2).strip()
                    if key in item:
                        raise ValueError(f"duplicate key {key!r} in list item")
                    i += 1
                    if rest == "":
                        if i < len(ls) and ls[i][0] > item_ind:
                            val, i = _parse_block(ls, i, ls[i][0])
                        else:
                            val = None
                        item[key] = val
                        lastkey = None
                    else:
                        item[key] = _scalar(rest)
                        lastkey = key if isinstance(item[key], str) else None
                elif lind2 > item_ind and lastkey is not None and isinstance(item.get(lastkey), str):
                    item[lastkey] = item[lastkey] + " " + txt2
                    i += 1
                else:
                    raise ValueError(f"unexpected structure in list item near: {txt2!r}")
            out.append(item)
        else:
            val = _scalar(body) if body else ""
            # deeper-indented lines continue a scalar item
            while i < len(ls) and ls[i][0] > ind and isinstance(val, str):
                val = (val + " " + ls[i][1]).strip()
                i += 1
            out.append(val)
    return out, i


def _ids(items, key):
    return [it.get(key) for it in items if isinstance(it, dict)]


def check_plan(path, specs_dir=None, repo_root=None):
    """Structural validation of a veldo.plan/v1 file. specs_dir enables the
    forward mirroring check (plan work item -> existing spec must bind back)."""
    errs = 0
    text = Path(path).read_text()
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return fail(path, "no YAML front matter")
    try:
        fm = parse_yamlish(m.group(1))
    except ValueError as e:
        return fail(path, f"front matter outside the contract subset: {e}")

    for field in ("schema", "id", "title", "kind", "status", "revision", "owner"):
        if field not in fm or fm.get(field) in (None, ""):
            errs += fail(path, f"missing front-matter field: {field}")
    if fm.get("schema") not in (None, "veldo.plan/v1"):
        errs += fail(path, f"bad schema: {fm.get('schema')}")
    if fm.get("id") and not re.fullmatch(r"PLAN-\d+", str(fm["id"])):
        errs += fail(path, f"bad plan id: {fm['id']}")
    if fm.get("kind") and fm["kind"] not in PLAN_KINDS:
        errs += fail(path, f"bad kind: {fm['kind']} (allowed: {sorted(PLAN_KINDS)})")
    status = fm.get("status")
    if status and status not in PLAN_STATUSES:
        errs += fail(path, f"bad status: {status} (allowed: {sorted(PLAN_STATUSES)})")
    if not isinstance(fm.get("revision"), int) or (isinstance(fm.get("revision"), int) and fm["revision"] < 1):
        errs += fail(path, "revision must be an integer >= 1")
    if status and status != "draft":
        for field in ("approved_by", "approved_at"):
            if not fm.get(field):
                errs += fail(path, f"status {status} requires {field}: a plan leaves draft only by a recorded human approval")

    errs += check_tracker_repo(path, fm, repo_root)

    outcomes = fm.get("outcomes") or []
    if not outcomes:
        errs += fail(path, "no outcomes: a plan without outcomes is a task list, not a plan")
    oids = _ids(outcomes, "id")
    if len(oids) != len(set(oids)):
        errs += fail(path, "duplicate outcome ids")
    for o in outcomes:
        if not isinstance(o, dict) or not o.get("id") or not o.get("becomes_true") or not o.get("measure"):
            errs += fail(path, f"outcome {o.get('id') if isinstance(o, dict) else o!r} needs id, becomes_true, measure")

    features = fm.get("feature_tree") or []
    fids = _ids(features, "id")
    if len(fids) != len(set(fids)):
        errs += fail(path, "duplicate feature ids")
    for ft in features:
        if not isinstance(ft, dict) or not ft.get("id") or not ft.get("title"):
            errs += fail(path, "feature_tree entries need id and title")
            continue
        if not ft.get("outcome_refs"):
            errs += fail(path, f"feature {ft['id']}: no outcome_refs - a feature that serves no outcome does not belong in the plan")
        for ref in ft.get("outcome_refs") or []:
            if ref not in oids:
                errs += fail(path, f"feature {ft['id']}: unknown outcome ref {ref}")

    work = fm.get("work") or []
    if not work:
        errs += fail(path, "no work items")
    items = _ids(work, "item")
    spec_ids = _ids(work, "spec")
    if len(items) != len(set(items)):
        errs += fail(path, "duplicate work item ids")
    if len(spec_ids) != len(set(spec_ids)):
        errs += fail(path, "duplicate spec ids across work items")
    spec_set = set(s for s in spec_ids if s)
    deps = {}
    for w in work:
        if not isinstance(w, dict) or not w.get("item") or not w.get("spec") or not w.get("title"):
            errs += fail(path, f"work item {w.get('item') if isinstance(w, dict) else w!r} needs item, spec, title")
            continue
        if not isinstance(w.get("spec"), str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9]*-\d+", w["spec"]):
            errs += fail(path, f"work {w['item']}: spec id {w.get('spec')!r} must be a string like PREFIX-0000")
        if not w.get("feature_refs"):
            errs += fail(path, f"work {w['item']}: no feature_refs - unattributed work is exactly the random stream the plan exists to end")
        for ref in w.get("feature_refs") or []:
            if ref not in fids:
                errs += fail(path, f"work {w['item']}: unknown feature ref {ref}")
        dl = w.get("depends_on")
        if dl is None:
            errs += fail(path, f"work {w['item']}: depends_on must be declared (use [] for none): an undeclared dependency is a decision nobody made")
            dl = []
        for d in dl:
            if d not in spec_set:
                errs += fail(path, f"work {w['item']}: depends_on {d} is not a spec of any work item")
            if d == w.get("spec"):
                errs += fail(path, f"work {w['item']}: depends on itself")
        if isinstance(w.get("spec"), str):
            deps[w["spec"]] = [d for d in dl if d in spec_set and isinstance(d, str)]

    # DAG acyclicity over depends_on (iterative DFS, deterministic order)
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {s: WHITE for s in deps}
    for start in sorted(deps):
        if color[start] != WHITE:
            continue
        stack = [(start, iter(sorted(deps[start])))]
        color[start] = GRAY
        while stack:
            node, it = stack[-1]
            advanced = False
            for nxt in it:
                if color.get(nxt, BLACK) == GRAY:
                    errs += fail(path, f"dependency cycle through {nxt}")
                    color[nxt] = BLACK
                elif color.get(nxt, BLACK) == WHITE:
                    color[nxt] = GRAY
                    stack.append((nxt, iter(sorted(deps[nxt]))))
                    advanced = True
                    break
            if not advanced:
                color[node] = BLACK
                stack.pop()

    reg = fm.get("regression") or {}
    jids = _ids(reg.get("journeys") or [], "id")
    if len(jids) != len(set(jids)):
        errs += fail(path, "duplicate regression journey ids")
    for j in reg.get("journeys") or []:
        if not isinstance(j, dict) or not j.get("id") or not j.get("title") or not j.get("activation"):
            errs += fail(path, "regression journeys need id, title, activation")
            continue
        # activation.when: start | after:<work-spec> | manual - the condition
        # that makes the journey active. Malformed activation is a decision
        # nobody made about when a regression runs.
        act = j.get("activation")
        when = act.get("when") if isinstance(act, dict) else None
        if not when:
            errs += fail(path, f"regression {j['id']}: activation needs a when")
        elif when in ("start", "manual"):
            pass
        elif isinstance(when, str) and when.startswith("after:"):
            dep = when[len("after:"):]
            if dep not in spec_set:
                errs += fail(path, f"regression {j['id']}: activation after:{dep} is not a work item spec")
        else:
            errs += fail(path, f"regression {j['id']}: bad activation when {when!r} (start | after:<spec> | manual)")
        # owner_spec, when present, must be a work item spec
        if j.get("owner_spec") and j["owner_spec"] not in spec_set:
            errs += fail(path, f"regression {j['id']}: owner_spec {j['owner_spec']} is not a work item spec")
        # profiles, when present, must be a subset of {per_spec, release}
        profs = j.get("profiles")
        if profs is not None:
            if not isinstance(profs, list) or any(p not in ("per_spec", "release") for p in profs):
                errs += fail(path, f"regression {j['id']}: profiles must be a list from per_spec, release")
            elif not profs:
                errs += fail(path, f"regression {j['id']}: profiles is empty - a journey that runs nowhere is dead")

    rel = fm.get("release") or {}
    if not rel or not rel.get("milestone"):
        errs += fail(path, "release.milestone missing: a plan must say what done is")
    if rel.get("mode") and rel["mode"] not in RELEASE_MODES:
        errs += fail(path, f"bad release mode: {rel['mode']} (allowed: {sorted(RELEASE_MODES)})")

    for d in fm.get("open_decisions") or []:
        if not isinstance(d, dict) or not d.get("id") or not d.get("text") or "blocks" not in d:
            errs += fail(path, "open decisions need id, text, and an explicit blocks list ([] if nothing waits on it)")
            continue
        for b in d.get("blocks") or []:
            if b not in spec_set:
                errs += fail(path, f"open decision {d['id']}: blocks unknown spec {b}")

    # forward mirroring: a work item whose spec exists must be bound back
    if specs_dir is not None:
        specs_dir = Path(specs_dir)
        for w in work:
            if not isinstance(w, dict) or not w.get("spec"):
                continue
            matches = sorted(specs_dir.glob(f"{w['spec']}*.md"))
            if not matches:
                continue
            sfm = front_matter(matches[0].read_text()) or {}
            if sfm.get("plan") != fm.get("id") or sfm.get("work") != w.get("item"):
                errs += fail(path, f"mirroring: {matches[0].name} exists but does not declare plan: {fm.get('id')} / work: {w.get('item')} (declares plan: {sfm.get('plan')} / work: {sfm.get('work')})")
    return errs


def plan_registry(plans_dir):
    """id -> {path, fm} for every plan file; parse failures are skipped here
    (check_plan reports them)."""
    reg = {}
    if not Path(plans_dir).exists():
        return reg
    for p in sorted(Path(plans_dir).glob("*.md")):
        if p.name.startswith("TEMPLATE"):
            continue
        m = re.match(r"^---\n(.*?)\n---", p.read_text(), re.S)
        if not m:
            continue
        try:
            fm = parse_yamlish(m.group(1))
        except ValueError:
            continue
        if fm.get("id"):
            reg[fm["id"]] = {"path": p, "fm": fm}
    return reg


def check_spec_plan_binding(spec_path, fm, registry):
    """Reverse mirroring: a spec that claims a plan must be that plan's truth."""
    errs = 0
    has_plan, has_work = bool(fm.get("plan")), bool(fm.get("work"))
    if has_plan != has_work:
        return fail(spec_path, "plan and work must be declared together")
    if not has_plan:
        # BELONGING TO NO PLAN MUST BE DECLARED, NOT INFERRED FROM SILENCE: this used to
        # `return 0`, so a standalone spec and a forgetful author were indistinguishable.
        if (fm.get("lane") or "").strip() != "standalone":
            return fail(spec_path, "declares no plan work item and no `lane: standalone`: a spec "
                                   "belonging to no plan must say so or it is invisible to anyone "
                                   "reading the plans to find what work exists")
        return 0
    plan = registry.get(fm["plan"])
    if not plan:
        return fail(spec_path, f"declares plan {fm['plan']} but no such plan exists")
    for w in plan["fm"].get("work") or []:
        if isinstance(w, dict) and w.get("item") == fm["work"]:
            if w.get("spec") != fm.get("id"):
                errs += fail(spec_path, f"plan {fm['plan']} work {fm['work']} is spec {w.get('spec')}, not {fm.get('id')}")
            return errs
    return fail(spec_path, f"plan {fm['plan']} has no work item {fm['work']}")



EVENT_TYPES = {
    "plan.created", "plan.approved", "plan.revised", "work.pulled",
    "spec.ready", "spec.shipped", "spec.blocked",
    "gate.passed", "gate.failed",
    "proof.recorded", "review.requested", "verdict.recorded",
    "approval.recorded",
    "emergency.push", "emergency.closed",
    "merge.completed", "index.updated",
    # The incident lifecycle (PLAN-0012): an incident opens, is diagnosed from
    # artifacts, a remediation is proposed, and the incident is closed by
    # reconciliation. The contract that OWNS this vocabulary is .veldo/incident.py
    # (INCIDENT_EVENT_TYPES) and .veldo/events.py carries it for the emitter; this
    # is the GATE's recognition of the same four types, which WARP-1201 deferred
    # to WARP-1208 (the reconciliation that actually emits incident.closed). A
    # selftest binds all three sets so the emitter, the metric source, and the
    # gate cannot drift. Recognition only: it refuses nothing that passed before.
    "incident.opened", "incident.diagnosed", "remedy.proposed", "incident.closed",
}


def check_events(path):
    """Every line must be a valid event envelope: JSON, schema, a known type, a timestamp.
    BOTH schema spellings are accepted, because the log is append-only history that keeps the old
    name. The legacy id is SPLIT so the rename cannot collapse it to a duplicate. Do not rejoin."""
    errs = 0
    p = Path(path)
    if not p.exists():
        return 0
    for n, line in enumerate(p.read_text().splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except Exception:
            errs += fail(path, f"line {n}: not valid JSON")
            continue
        if e.get("schema") not in ("veldo.event/v1", "w" "arp.event/v1"):
            errs += fail(path, f"line {n}: bad or missing schema (want veldo.event/v1)")
        if e.get("type") not in EVENT_TYPES:
            errs += fail(path, f"line {n}: unknown event type {e.get('type')!r}")
        if not e.get("at"):
            errs += fail(path, f"line {n}: missing at (timestamp)")
    return errs


# ---------------------------------------------------------------------------
# The sibling-module delegating validators (architecture, placement/ready,
# decision, decision-review, tripwire, shape-fit review, and the tripwire-status
# projection) live in .veldo/validate_checks.py, so this module stays under the
# module_lines budget the architecture contract enforces. This is a PURE
# extraction: no validation logic, no message, and no behavior changed, only the
# file the code lives in. The sub-module is loaded here BY PATH the same way this
# module loads its sibling contract validators (arch.py, decision.py, ...) - and,
# symmetrically, the way shape_gate.py, entropy.py, and incident.py load this
# module - so there is one front-matter parser and one failure reporter, no second
# parser, and NO import cycle: the dependency is one-way (validate.py ->
# validate_checks.py, never back). This module hands the sub-module its own two
# helpers (the one parser parse_yamlish and the one reporter fail; the sub-module
# derives ROOT itself and loads its own siblings), then re-exports every moved name
# back into this module's namespace, so every existing caller keeps resolving them
# on validate.py exactly as before (V.check_arch, V.check_placement, V.check_ready,
# V.load_repo_contract, V.tripwire_status, ... are unchanged public names).
_vcspec = importlib.util.spec_from_file_location("veldo_validate_checks", ROOT / ".veldo" / "validate_checks.py")
_VC = importlib.util.module_from_spec(_vcspec)
_vcspec.loader.exec_module(_VC)
_VC.parse_yamlish = parse_yamlish
_VC.fail = fail
_arch_module = _VC._arch_module
check_arch = _VC.check_arch
check_placement = _VC.check_placement
_observability_module = _VC._observability_module
check_observability = _VC.check_observability
load_repo_contract = _VC.load_repo_contract
placement_gate_problems = _VC.placement_gate_problems
placement_gate_ok = _VC.placement_gate_ok
check_ready = _VC.check_ready
_decision_module = _VC._decision_module
check_decision = _VC.check_decision
check_decisions = _VC.check_decisions
_decision_review_module = _VC._decision_review_module
check_decision_review = _VC.check_decision_review
check_decision_reviews = _VC.check_decision_reviews
_tripwire_module = _VC._tripwire_module
check_readings = _VC.check_readings
check_tripwires = _VC.check_tripwires
_shape_review_module = _VC._shape_review_module
check_shape_review = _VC.check_shape_review
_count_fail = _VC._count_fail
tripwire_status = _VC.tripwire_status
# The spec-corpus contract: the depends_on field's shape and the uniqueness of a spec id.
# Re-exported here because check_spec and run_all below are their callers and because
# V.check_depends_on / V.check_spec_ids are the names the selftest and any adopting
# repository resolve on this module.
check_depends_on = _VC.check_depends_on
check_spec_ids = _VC.check_spec_ids
# The proof-corpus enumeration (WARP-0727) and the both-directions equality check over it.
# _CORPUS is re-exported because the corpus PATTERNS are the vocabulary run_all iterates.
_CORPUS = _VC._CORPUS
_corpus = _VC._corpus
check_verdict_domain_is_the_validated_set = _VC.check_verdict_domain_is_the_validated_set


# The human-touchpoint request envelope (veldo.request/v1, PLAN-0016 W2) is a sibling
# contract organ loaded BY PATH the same way this module loads its other siblings, and
# it receives this module's ONE front-matter parser and ONE failure reporter, so it
# adds no second YAML parser and there is no import cycle. It REFERENCES the shipped
# settlement records and makes no change to the frozen readers (policy_check, two_key,
# decision); the W3 projection (WARP-0617), W6 authorization (WARP-0616), and W5 inbound
# edge (WARP-0619) consume these records, this validates only that each is well formed.
def _request_module():
    rspec = importlib.util.spec_from_file_location("veldo_request", ROOT / ".veldo" / "request.py")
    req = importlib.util.module_from_spec(rspec)
    rspec.loader.exec_module(req)
    return req


def check_requests(requests_dir=None, root=None):
    """Validate the per-repo request records under .veldo/requests/ (veldo.request/v1),
    delegating to .veldo/request.py in the EXACT adoption-safe, fail-closed,
    dependency-free style of check_decisions. Adoption safe: an absent directory stands
    down (a repository without request records is byte-identically unaffected), while a
    present record fails closed on anything malformed and a duplicate request id across
    records is refused."""
    base = Path(root) if root else ROOT
    rdir = Path(requests_dir) if requests_dir else base / ".veldo" / "requests"
    return _request_module().check_requests_dir(rdir, base, parse_yamlish, fail)


def run_all():
    errs = 0
    errs += check_events(ROOT / ".veldo" / "events.jsonl")
    errs += check_arch()
    errs += check_decisions()
    errs += check_requests()
    errs += check_decision_reviews()
    errs += check_tripwires()
    registry = plan_registry(ROOT / "plans")
    for p in sorted((ROOT / "plans").glob("*.md")) if (ROOT / "plans").exists() else []:
        if p.name.startswith("TEMPLATE"):
            continue
        errs += check_plan(p, specs_dir=ROOT / "specs")
    errs += check_spec_ids(ROOT / "specs")
    for p in sorted((ROOT / "specs").glob("*.md")):
        if p.name.startswith("TEMPLATE") or p.name == "index.md":
            continue
        errs += check_spec(p)
        fm = front_matter(p.read_text())
        if fm:
            errs += check_spec_plan_binding(p, fm, registry)
    spec_by_id = {}
    for p in sorted((ROOT / "specs").glob("*.md")):
        if p.name.startswith("TEMPLATE") or p.name == "index.md":
            continue
        fm = front_matter(p.read_text())
        if fm and fm.get("id"):
            spec_by_id[fm["id"]] = p
    for p in _corpus(_CORPUS.MANIFEST_PATTERN):
        errs += check_json(p, PROOF_REQ, "proof")
        try:
            sid = json.loads(p.read_text()).get("spec_id")
        except Exception:
            sid = None
        if sid and sid in spec_by_id:
            errs += check_required_evidence(spec_by_id[sid], p)
            errs += check_criteria_coverage(spec_by_id[sid], p)
    # actual verdicts and approvals are validated too, not just the examples
    for p in _corpus(_CORPUS.VERDICT_PATTERN):
        errs += check_json(p, VERDICT_REQ, "verdict")
    for p in _corpus(_CORPUS.DESIGN_VERDICT_PATTERN):
        errs += check_json(p, VERDICT_REQ, "verdict")
    for p in _corpus(_CORPUS.APPROVAL_PATTERN):
        errs += check_json(p, APPROVAL_REQ, "approval")
    errs += check_verdict_domain_is_the_validated_set()
    ex = ROOT / ".veldo" / "examples"
    if ex.exists():
        errs += check_spec(ex / "spec-example.md")
        errs += check_json(ex / "proof-example.json", PROOF_REQ, "proof")
        errs += check_json(ex / "verdict-example.json", VERDICT_REQ, "verdict")
        errs += check_json(ex / "approval-example.json", APPROVAL_REQ, "approval")
        if (ex / "plan-example.md").exists():
            errs += check_plan(ex / "plan-example.md")
        if (ex / "decision-example.md").exists():
            errs += check_decision(ex / "decision-example.md")
        if (ex / "decision-example.yaml").exists():
            errs += check_decision(ex / "decision-example.yaml")
        # The decision-review example binds to the decision example (both in .veldo/examples),
        # so it is validated AND bound against the examples directory, not a real records dir.
        if (ex / "decision-review-example.yaml").exists():
            errs += check_decision_review(ex / "decision-review-example.yaml", decisions_dir=ex)
        # The readings example is measured against the decision example (both in .veldo/examples),
        # so it is validated AND evaluated against the examples directory, not a real records dir.
        if (ex / "readings-example.yaml").exists():
            errs += check_readings(ex / "readings-example.yaml", decisions_dir=ex)
    return errs


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    mode = sys.argv[1]
    if mode == "all":
        errs = run_all()
    elif mode == "spec":
        errs = check_spec(sys.argv[2])
    elif mode == "plan":
        errs = check_plan(sys.argv[2], specs_dir=ROOT / "specs")
    elif mode == "events":
        errs = check_events(sys.argv[2] if len(sys.argv) > 2 else ROOT / ".veldo" / "events.jsonl")
    elif mode == "proof":
        errs = check_json(sys.argv[2], PROOF_REQ, "proof")
    elif mode == "verdict":
        errs = check_json(sys.argv[2], VERDICT_REQ, "verdict")
    elif mode == "approval":
        errs = check_json(sys.argv[2], APPROVAL_REQ, "approval")
    elif mode == "arch":
        errs = check_arch(sys.argv[2] if len(sys.argv) > 2 else None)
    elif mode == "placement":
        errs = check_placement(sys.argv[2])
    elif mode == "ready":
        errs = check_ready(sys.argv[2])
    elif mode == "shape-review":
        # shape-review <spec-file> [changed-path ...]: the mechanizable half of the W4
        # shape-fit review dimension over a change's diff paths. Fails closed on each
        # mechanical misfit; adoption safe (stands down with no contract). The pattern-fit
        # judgment is the delegated fresh-context reviewer's, carried in the verdict.
        errs = check_shape_review(sys.argv[2], sys.argv[3:])
    elif mode == "decisions":
        arg = sys.argv[2] if len(sys.argv) > 2 else None
        if arg and Path(arg).is_file():
            errs = check_decision(arg)
        else:
            errs = check_decisions(arg)
    elif mode == "requests":
        arg = sys.argv[2] if len(sys.argv) > 2 else None
        if arg and Path(arg).is_file():
            errs = _request_module().check_record(Path(arg), ROOT, False, parse_yamlish, fail)
        else:
            errs = check_requests(arg)
    elif mode == "decision-review":
        arg = sys.argv[2] if len(sys.argv) > 2 else None
        if arg and Path(arg).is_file():
            # Resolve the referenced decision from the review's own directory (a co-located
            # example) or the repository's decision records, whichever declares it.
            parent = Path(arg).resolve().parent
            repo_decisions = ROOT / ".veldo" / "decisions"
            ddir = parent
            try:
                dr = _decision_review_module()
                ld = _decision_module().load_record
                rdata = dr.load_review(Path(arg), parse_yamlish)
                if (dr.resolve_decision(rdata.get("decision"), parent, parse_yamlish, ld) is None
                        and repo_decisions.is_dir()):
                    ddir = repo_decisions
            except Exception:
                pass
            errs = check_decision_review(arg, decisions_dir=ddir)
        else:
            errs = check_decision_reviews(arg)
    elif mode == "tripwires":
        args2 = sys.argv[2:]
        draft = "--draft" in args2
        fileargs = [a for a in args2 if not a.startswith("--")]
        if fileargs and Path(fileargs[0]).is_file():
            # A single readings file: resolve its decision from its own directory (a co-located
            # example) or the repository's decision records, whichever declares it.
            rp = Path(fileargs[0])
            parent = rp.resolve().parent
            repo_decisions = ROOT / ".veldo" / "decisions"
            ddir = parent
            try:
                tw = _tripwire_module()
                ld = _decision_module().load_record
                rdata = tw.load_readings(rp, parse_yamlish)
                if (tw.resolve_decision(rdata.get("decision"), parent, parse_yamlish, ld) is None
                        and repo_decisions.is_dir()):
                    ddir = repo_decisions
            except Exception:
                pass
            errs = check_readings(rp, decisions_dir=ddir)
        else:
            # The repository-wide in-session pass (adoption safe: stands down with no records).
            errs = check_tripwires()
            if draft:
                tw = _tripwire_module()
                ld = _decision_module().load_record
                drafts = tw.draft_redecisions(ROOT / ".veldo" / "decisions", ROOT / ".veldo" / "readings",
                                              ROOT / ".veldo" / "redecisions", parse_yamlish, fail, ld)
                for did, outcome in drafts:
                    print(f"  re-decision draft {did}: {outcome}")
    else:
        print(f"unknown mode: {mode}")
        return 2
    if errs:
        print(f"veldo contracts: {errs} problem(s)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
