#!/usr/bin/env python3
"""VELDO contract validator. Proportionate by design: required-field checks,
not a schema stack. Used by verify.sh; also runnable directly.

Usage:
  python3 .veldo/validate.py all                 # validate specs, plans, proofs, examples
  python3 .veldo/validate.py spec <file.md>
  python3 .veldo/validate.py plan <file.md>
  python3 .veldo/validate.py proof <manifest.json>
  python3 .veldo/validate.py proof-files [<root>]     # proof size, encoded archives, summaries
  python3 .veldo/validate.py push-proof [<remote>]    # pre-push ref lines on stdin
  python3 .veldo/validate.py gate-summary <transcript> <out.summary.json> [<command>]
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

import importlib.util as _yaml_importlib
from pathlib import Path as _YamlPath
_yaml_spec = _yaml_importlib.spec_from_file_location("veldo_yamlish", _YamlPath(__file__).resolve().with_name("yamlish.py"))
_Y = _yaml_importlib.module_from_spec(_yaml_spec)
_yaml_spec.loader.exec_module(_Y)

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



# The one syntax reader, loaded by sibling path for file-location imports.
_yamlish_spec = importlib.util.spec_from_file_location("veldo_yamlish", Path(__file__).resolve().with_name("yamlish.py"))
_yamlish = importlib.util.module_from_spec(_yamlish_spec)
_yamlish_spec.loader.exec_module(_yamlish)

front_matter = _yamlish.front_matter
parse_yamlish = _yamlish.parse


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
    try:
        fm = front_matter(text, str(path))
    except ValueError as e:
        return fail(path, str(e))
    if fm is None:
        return fail(path, "no YAML front matter")
    for field in ("schema", "id", "title", "status", "risk", "owner"):
        if field not in fm:
            errs += fail(path, f"missing front-matter field: {field}")
    if fm.get("status") and fm["status"] not in SPEC_STATUSES:
        errs += fail(path, f"bad status: {fm['status']}")
    if fm.get("risk") and fm["risk"].split()[0] not in RISKS:
        errs += fail(path, f"bad risk: {fm['risk']}")
    if "acceptance_criteria" not in fm:
        errs += fail(path, "no acceptance criteria")
    if fm.get("required_evidence"):
        for kind in fm["required_evidence"]:
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
        declared = fm["required_evidence"]
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
    fm = front_matter(Path(spec_path).read_text(), str(spec_path))
    if fm is None:
        raise ValueError(f"{spec_path}: no YAML front matter")
    criteria = fm.get("acceptance_criteria", [])
    if not isinstance(criteria, list) or any(not isinstance(c, dict) for c in criteria):
        raise ValueError(f"{spec_path}: acceptance_criteria must be a list of mappings")
    return [c["id"] for c in criteria if "id" in c]


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
        errs += sum(fail(path, f"criterion {c.get('id')} passed without evidence")
                    for c in data.get("criteria", []) if c.get("status") == "passed" and not c.get("evidence"))
        errs += _VC._fix_validation_record_module().check_proof_bundle(path, data, ROOT, parse_yamlish, front_matter, fail)
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

def _ids(items, key):
    return [it.get(key) for it in items if isinstance(it, dict)]


def check_plan(path, specs_dir=None, repo_root=None):
    """Structural validation of a veldo.plan/v1 file. specs_dir enables the
    forward mirroring check (plan work item -> existing spec must bind back)."""
    errs = 0
    text = Path(path).read_text()
    m = _Y.front_matter_match(text)
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
        m = _Y.front_matter_match(p.read_text())
        if not m:
            continue
        try:
            fm = parse_yamlish(m.group(1))
        except ValueError:
            raise
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



# THE ONE CANONICAL EVENT VOCABULARY (VELDO-0051), the module the emitter (.veldo/events.py) loads
# too, so the gate recognizes exactly what the enabled producers write: the loop's steps, the run
# milestones, the incident lifecycle (incident.py INCIDENT_EVENT_TYPES) and the request lifecycle
# (request.py REQUEST_EVENT_TYPES). Before it this module held its own 21-type list against the
# emitter's 31, and refused a run.done the emitter wrote. EVENT_TYPES and EVENT_SCHEMAS are THIS
# module's own copies, so a private instance of the validator can be driven without mutating another.
_evspec = importlib.util.spec_from_file_location("veldo_event_vocabulary",
                                                 ROOT / ".veldo" / "control_event_vocabulary.py")
_EVENT_VOCABULARY = importlib.util.module_from_spec(_evspec)
_evspec.loader.exec_module(_EVENT_VOCABULARY)
EVENT_TYPES = set(_EVENT_VOCABULARY.EVENT_TYPES)
EVENT_SCHEMAS = tuple(_EVENT_VOCABULARY.SCHEMAS)


def check_events(path):
    """Every line must be a valid event envelope: JSON, schema, a known type, a timestamp.
    BOTH schema spellings are accepted, because the log is append-only history that keeps the old
    name; the canonical vocabulary holds the legacy id SPLIT so the rename cannot collapse it."""
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
        for problem in _EVENT_VOCABULARY.line_problems(e, EVENT_TYPES, EVENT_SCHEMAS):
            errs += fail(path, f"line {n}: {problem}")
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
load_repo_contract, load_contract_state, ContractRefused = _VC.load_repo_contract, _VC.load_contract_state, _VC.ContractRefused
# VELDO-0053: the public seam an eligibility entry judges a workspace's architecture contract through.
# entry_validator loads one structural validator (arch.py) instance for a caller to reuse with it.
entry_contract, entry_validator = _VC.entry_contract, _VC._arch_module
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


# ---------------------------------------------------------------------------------------------
# VELDO-0270: PROOF IS SMALL SUMMARIES, NEVER RAW BULK. One implementation of the rules, used by
# the contracts stage (run_all, mode proof-files) and by the push guard (mode push-proof), so the
# gate and the guard cannot disagree about the limit or about what an encoded archive is.
#   proof_file_over_limit    a tracked proof file larger than proof.max_file_bytes
#   proof_encoded_archive    base64 text decoding to an archive or compressed stream, any size
#   proof_reference_dangling a proof file still naming a removed file instead of its summary
#   proof_summary_incomplete a *.summary.json without its command, environment or discarded digests
# The limit is .veldo/policy.yaml key proof.max_file_bytes, default 1,048,576 bytes when the key
# is absent. A key that is present but not a positive integer is a refusal, never the default.
# ---------------------------------------------------------------------------------------------
import base64 as _b64
import fnmatch as _fnmatch
import os as _os

_gp_spec = importlib.util.spec_from_file_location("validate_git_process", Path(__file__).with_name("git_process.py"))
_git_process = importlib.util.module_from_spec(_gp_spec)
_gp_spec.loader.exec_module(_git_process)

PROOF_LIMIT_DEFAULT = 1048576
PROOF_PROTECTED_REFS_DEFAULT = ["refs/heads/main", "refs/tags/*"]
SUMMARY_SCHEMA = "veldo.proof-summary/v1"
_B64_RUN = re.compile(rb"[A-Za-z0-9+/]{64,}(?:(?:\r?\n|\\n)[A-Za-z0-9+/]+)*={0,2}")
_B64_SEP = re.compile(rb"\r?\n|\\n")
_ARCHIVE_MAGIC = (
    (b"\x1f\x8b", "gzip"),
    (b"PK\x03\x04", "zip"),
    (b"PK\x05\x06", "zip"),
    (b"BZh", "bzip2"),
    (b"\xfd7zXZ\x00", "xz"),
    (b"\x28\xb5\x2f\xfd", "zstd"),
)
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def proof_policy(root=None):
    """(limit, source, protected_refs, problems) read from <root>/.veldo/policy.yaml."""
    base = Path(root) if root else ROOT
    pfile = base / ".veldo" / "policy.yaml"
    problems = []
    limit, source = PROOF_LIMIT_DEFAULT, "the default; .veldo/policy.yaml key proof.max_file_bytes is absent"
    refs = list(PROOF_PROTECTED_REFS_DEFAULT)
    data = {}
    if pfile.is_file():
        try:
            data = parse_yamlish(pfile.read_text()) or {}
        except Exception as e:  # an unreadable policy is a refusal, never the default
            problems.append(f"{pfile}: unreadable ({e})")
            data = {}
    section = data.get("proof") if isinstance(data, dict) else None
    if section is not None and not isinstance(section, dict):
        problems.append(f".veldo/policy.yaml key proof is not a mapping: {section!r}")
        section = None
    section = section or {}
    if "max_file_bytes" in section:
        v = section["max_file_bytes"]
        if isinstance(v, bool) or not isinstance(v, int) or v <= 0:
            problems.append(f".veldo/policy.yaml key proof.max_file_bytes is not a positive integer: {v!r}")
        else:
            limit, source = v, ".veldo/policy.yaml key proof.max_file_bytes"
    if "protected_refs" in section:
        v = section["protected_refs"]
        if not isinstance(v, list) or not v or not all(isinstance(x, str) and x for x in v):
            problems.append(f".veldo/policy.yaml key proof.protected_refs is not a list of refs: {v!r}")
        else:
            refs = list(v)
    return limit, source, refs, problems


def encoded_archives(name, data):
    """[(offset, kind)] for base64 text in data that decodes to an archive or compressed stream.
    A name ending .b64 or .base64 is one at offset 0 whatever it holds."""
    found = []
    if name.endswith(".b64") or name.endswith(".base64"):
        found.append((0, "base64 file name"))
    for m in _B64_RUN.finditer(data):
        text = _B64_SEP.sub(b"", m.group(0)[:1200]).rstrip(b"=")
        text = text[: (min(len(text), 360) // 4) * 4]
        try:
            raw = _b64.b64decode(text)
        except Exception:
            continue
        kind = next((k for magic, k in _ARCHIVE_MAGIC if raw.startswith(magic)), None)
        if kind is None and raw[257:262] == b"ustar":
            kind = "tar"
        if kind:
            found.append((m.start(), kind))
    return found


def _tracked_proof_files(base):
    try:
        out = _git_process.run(["git", "-C", str(base), "ls-files", "-z", "--", "proof"],
                              capture_output=True, check=True).stdout
        rels = [r for r in out.decode("utf-8", "surrogateescape").split("\0") if r]
    except Exception:
        rels = None
    if rels is None:
        pdir = base / "proof"
        rels = sorted(str(p.relative_to(base)) for p in pdir.rglob("*") if p.is_file()) if pdir.is_dir() else []
    return [r for r in rels if (base / r).is_file()]


def summary_problems(data):
    """What a proof summary (veldo.proof-summary/v1) lacks: the exact command, the environment,
    and for every discarded raw file its name, size in bytes and sha256."""
    probs = []
    if not isinstance(data, dict):
        return ["not a JSON object"]
    if data.get("schema") != SUMMARY_SCHEMA:
        probs.append(f"schema is not {SUMMARY_SCHEMA}")
    if not isinstance(data.get("command"), str) or not data.get("command").strip():
        probs.append("no command")
    env = data.get("environment")
    if not isinstance(env, dict) or not env:
        probs.append("no environment")
    disc = data.get("discarded")
    if not isinstance(disc, list):
        probs.append("no discarded list (an empty list when nothing was discarded)")
        disc = []
    for i, d in enumerate(disc):
        if not isinstance(d, dict) or not isinstance(d.get("name"), str) or not d.get("name"):
            probs.append(f"discarded[{i}] has no name")
            continue
        if not isinstance(d.get("bytes"), int) or isinstance(d.get("bytes"), bool) or d["bytes"] < 0:
            probs.append(f"discarded {d['name']} has no size in bytes")
        if not isinstance(d.get("sha256"), str) or not _HEX64.match(d["sha256"]):
            probs.append(f"discarded {d['name']} has no sha256")
    return probs


def _removed_by_summary(base, rels):
    """{original_path: summary_rel} for every summary whose original file is absent."""
    removed = {}
    present = set(rels)
    for r in rels:
        if not r.endswith(".summary.json"):
            continue
        try:
            data = json.loads((base / r).read_text())
        except Exception:
            continue
        orig = data.get("original_path") if isinstance(data, dict) else None
        if isinstance(orig, str) and orig.startswith("proof/") and orig not in present:
            removed[orig] = r
    return removed


def _ref_patterns(orig):
    """The ways a proof file names a removed file: its repository path, its path relative to its
    bundle directory (proof/<ID>/) for files inside that bundle, or its bare name for files in
    its own directory."""
    parts = orig.split("/")
    bundle = "/".join(parts[:2]) + "/"
    rel = "/".join(parts[2:])
    out = [(None, orig)]
    if rel:
        out.append((bundle, rel))
    if len(parts) > 3:
        out.append(("/".join(parts[:-1]) + "/", parts[-1]))
    return out


def check_proof_files(root=None, quiet=False):
    """The four VELDO-0270 refusals over every file tracked under proof/ in the tree at root."""
    base = Path(root) if root else ROOT
    limit, source, _refs, pol = proof_policy(base)
    errs = 0
    for p in pol:
        errs += fail("proof_policy_invalid", p)
    rels = _tracked_proof_files(base)
    largest = (0, None)
    removed = _removed_by_summary(base, rels)
    pats = []
    for orig in removed:
        for scope, text in _ref_patterns(orig):
            rx = re.compile(rb"(?<![A-Za-z0-9_.-])" + re.escape(text.encode()) + rb"(?![A-Za-z0-9_-])(?!\.summary\.json)(?!\.[A-Za-z0-9])")
            pats.append((scope, orig, rx))
    for r in rels:
        fp = base / r
        size = fp.stat().st_size
        if size > largest[0]:
            largest = (size, r)
        if not pol and size > limit:
            errs += fail("proof_file_over_limit", f"{r}: {size} bytes, limit {limit} bytes ({source})")
        data = fp.read_bytes()
        for off, kind in encoded_archives(r, data):
            errs += fail("proof_encoded_archive", f"{r}: base64 run at byte offset {off} decodes to {kind}")
        if r.endswith(".summary.json"):
            try:
                sdata = json.loads(data.decode("utf-8"))
            except Exception as e:
                sdata = None
                errs += fail("proof_summary_incomplete", f"{r}: not JSON ({e})")
            if sdata is not None:
                probs = summary_problems(sdata)
                if probs:
                    errs += fail("proof_summary_incomplete", f"{r}: " + "; ".join(probs))
            continue
        for scope, orig, rx in pats:
            if scope and not r.startswith(scope):
                continue
            if rx.search(data):
                errs += fail("proof_reference_dangling",
                             f"{r} names {orig}, which is absent; name {removed[orig]} instead")
    if not quiet:
        big = f"{largest[1]} {largest[0]} bytes" if largest[1] else "none"
        print(f"  proof files checked: {len(rels)}; largest: {big}; limit {limit} bytes ({source})")
    return errs


def _git(base, *args):
    return _git_process.run(["git", "-C", str(base), *args], capture_output=True, check=True).stdout


def check_push_proof(lines, remote="", root=None):
    """The push guard's half: every commit a push to a protected ref sends that the remote does
    not already have, judged by the same two rules with the same limit. lines are git's pre-push
    stdin: '<local ref> <local sha> <remote ref> <remote sha>'."""
    base = Path(root) if root else Path.cwd()
    limit, source, refs, pol = proof_policy(base)
    errs = 0
    for p in pol:
        errs += fail("proof_policy_invalid", p)
    if pol:
        return errs
    zero = "0" * 40
    for line in lines:
        f = line.split()
        if len(f) != 4:
            continue
        _lref, lsha, rref, rsha = f
        if set(lsha) == {"0"} or not any(_fnmatch.fnmatchcase(rref, pat) for pat in refs):
            continue
        excl = ["--not"]
        if rsha != zero and set(rsha) != {"0"}:
            try:
                _git(base, "cat-file", "-e", rsha + "^{commit}")
                excl.append(rsha)
            except Exception:
                pass
        excl.append(f"--remotes={remote}" if remote else "--remotes")
        commits = _git(base, "rev-list", "--reverse", lsha, *excl).decode().split()
        for c in commits:
            parents = _git(base, "rev-list", "--parents", "-n", "1", c).decode().split()[1:]
            if parents:
                diff = _git(base, "diff-tree", "-r", "-z", "--no-commit-id", "--diff-filter=ACMR",
                            parents[0], c)
            else:
                diff = _git(base, "diff-tree", "-r", "-z", "--root", "--no-commit-id",
                            "--diff-filter=ACMR", c)
            toks = diff.decode("utf-8", "surrogateescape").split("\0")
            i = 0
            while i < len(toks) - 1:
                meta = toks[i].split()
                if not meta:
                    i += 1
                    continue
                n = 3 if meta[-1][:1] in ("R", "C") else 2
                path = toks[i + n - 1]
                blob = meta[3] if len(meta) > 3 else ""
                i += n
                if not path.startswith("proof/") or not blob:
                    continue
                size = int(_git(base, "cat-file", "-s", blob).decode().strip())
                where = f"push to {rref}: commit {c} adds {path}"
                if size > limit:
                    errs += fail("proof_file_over_limit",
                                 f"{where}: {size} bytes, limit {limit} bytes ({source})")
                for off, kind in encoded_archives(path, _git(base, "cat-file", "blob", blob)):
                    errs += fail("proof_encoded_archive",
                                 f"{where}: base64 run at byte offset {off} decodes to {kind}")
    return errs


def proof_summary(command, deciding, discarded=(), root=None, timing=False, extra=None):
    """A veldo.proof-summary/v1 record: what a proof writer keeps instead of its raw output.
    discarded is [(name, raw_bytes)]; each is recorded by name, size and sha256 and then dropped.
    timing adds the host load, for results that are timing sensitive."""
    import hashlib as _hl
    import platform as _pf
    base = Path(root) if root else ROOT

    def _rev(spec):
        try:
            return _git(base, "rev-parse", spec).decode().strip()
        except Exception:
            return "unknown"
    try:
        gitv = _git_process.run(["git", "--version"], capture_output=True, text=True).stdout.strip()
    except Exception:
        gitv = "unknown"
    env = {"commit": _rev("HEAD"), "tree": _rev("HEAD^{tree}"), "host": _pf.node(),
           "python": _pf.python_version(), "git": gitv}
    if timing:
        try:
            env["load"] = list(_os.getloadavg())
        except (OSError, AttributeError):
            env["load"] = "unavailable"
    disc = []
    for name, raw in discarded:
        raw = raw.encode() if isinstance(raw, str) else bytes(raw)
        disc.append({"name": name, "bytes": len(raw), "sha256": _hl.sha256(raw).hexdigest()})
    rec = dict(extra or {})
    rec.update({"schema": SUMMARY_SCHEMA, "command": command, "environment": env,
                "discarded": disc, "deciding": deciding})
    return rec


def write_proof_summary(path, command, deciding, discarded=(), root=None, timing=False, extra=None):
    """Write proof_summary(...) to path and return it. The summary itself must be under the
    policy limit; one that is not is a writer bug and raises rather than landing raw bulk."""
    rec = proof_summary(command, deciding, discarded, root, timing, extra)
    text = json.dumps(rec, indent=1, sort_keys=True, ensure_ascii=True) + "\n"
    limit = proof_policy(root)[0]
    if len(text.encode()) > limit:
        raise ValueError(f"proof summary {path} is {len(text.encode())} bytes, over the limit {limit}")
    Path(path).write_text(text)
    return rec


def _short(value, n=400):
    text = value if isinstance(value, str) else json.dumps(value, sort_keys=True, default=str)
    return text if len(text) <= n else text[:n] + "..."


def summarize_mutation_receipt(receipt):
    """The deciding part of a mutation stage receipt (veldo.mutation-stage/v1): its counts, per case
    the expected and observed verdict, the detail of each case that did not go as expected, and
    the sha256 of the full result array, which is discarded."""
    import hashlib as _hl
    results = receipt.get("results") or []
    rows = []
    for r in results:
        case = r.get("case") or {}
        rows.append({"case": case.get("name") or case.get("identity"), "expected": "killed",
                     "observed": "killed", "source": r.get("source")})
    for r in receipt.get("invalid_results") or []:
        case = r.get("case") or {}
        rows.append({"case": case.get("name") or case.get("identity"), "expected": "killed",
                     "observed": r.get("error") or "invalid", "red": _short(r.get("detail"))})
    body = json.dumps(results, sort_keys=True, separators=(",", ":")).encode()
    counts = {k: receipt.get(k) for k in ("status", "registered", "executed", "reused", "rejected",
                                         "worker_invocations", "elapsed", "error") if k in receipt}
    return {"counts": counts, "rows": rows, "results_count": len(results),
            "results_sha256": _hl.sha256(body).hexdigest()}


_STAGE_LINE = re.compile(r"^   ([a-z][a-z _.-]*(?:: [a-z]+ leg)?): (pass|PASS|FAIL|fail|skip|SKIP|not-applicable)\b"
                         r"(?: \(([\d.]+)s\))?\s*$")
_NODE_LINE = re.compile(r"^node (\S+) end [\d.]+ (\S+) ([\d.]+)s")


def summarize_gate_transcript(text):
    """The stage table of a scripts/verify.sh transcript: each stage's verdict and seconds, the
    final GATE line, and the first failing row's detail. The transcript itself is discarded."""
    stages, nodes, first_fail = [], [], None
    for line in text.splitlines():
        m = _STAGE_LINE.match(line)
        if m:
            stages.append({"stage": m.group(1), "verdict": m.group(2),
                           "seconds": float(m.group(3)) if m.group(3) else None})
            continue
        m = _NODE_LINE.match(line)
        if m:
            nodes.append({"node": m.group(1), "verdict": m.group(2), "seconds": float(m.group(3))})
            continue
        if first_fail is None and re.search(r"\bFAIL\b", line):
            first_fail = line.strip()[:400]
    gate = [l.strip() for l in text.splitlines() if l.startswith("GATE:")]
    return {"gate": gate[-1] if gate else None, "stages": stages, "nodes": nodes,
            "first_failing_row": first_fail}


def write_gate_summary(transcript, out, command="bash scripts/verify.sh", root=None):
    """The gate transcript capture for proof: the stage table, never the transcript."""
    raw = Path(transcript).read_bytes()
    return write_proof_summary(out, command, summarize_gate_transcript(raw.decode("utf-8", "replace")),
                               discarded=[(Path(transcript).name, raw)], root=root, timing=True)


def run_all():
    errs = 0
    errs += check_events(ROOT / ".veldo" / "events.jsonl")
    errs += check_arch()
    errs += check_decisions() + _VC.check_floors()  # VELDO-0012: floors stand down when absent
    errs += check_requests()
    errs += check_decision_reviews()
    errs += check_tripwires()
    registry = plan_registry(ROOT / "plans")
    for p in sorted((ROOT / "plans").glob("*.md")) if (ROOT / "plans").exists() else []:
        if p.name.startswith("TEMPLATE"):
            continue
        errs += check_plan(p, specs_dir=ROOT / "specs")
    errs += check_spec_ids(ROOT / "specs") + _VC.check_releases()  # VELDO-0011: + plan-id uniqueness
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
    errs += check_proof_files()  # VELDO-0270: proof is small summaries, never raw bulk
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
    elif mode == "proof-files":
        errs = check_proof_files(sys.argv[2] if len(sys.argv) > 2 else None)
    elif mode == "gate-summary":
        # gate-summary <transcript> <out.summary.json> [command] (VELDO-0270: the stage table, not the log).
        write_gate_summary(sys.argv[2], sys.argv[3], *(sys.argv[4:5]))
        errs = 0
    elif mode == "push-proof":
        # push-proof [remote]: git's pre-push ref lines on stdin (VELDO-0270, the push guard).
        errs = check_push_proof(sys.stdin.read().splitlines(), sys.argv[2] if len(sys.argv) > 2 else "")
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
