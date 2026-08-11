#!/usr/bin/env python3
"""VELDO plan operations: the mechanical teeth behind the /veldo:plan skill.

The skill (a procedure) runs the dialogue; this module answers the questions
that must be computed, not narrated:

  plan.py status <plan.md>          the burn-down: per-item state + frontier
  plan.py release-check <plan.md>   is the plan releasable, and if not, why
  plan.py impact <plan.md> <SPEC>   what a change to SPEC affects (blast radius)
  plan.py regression <plan.md> <ctx> active regression journeys for a context:
                                    ctx = per_spec:<SPEC> | release
  plan.py bundle <plan.md> <SPEC>   the plan context bundle for building SPEC
  plan.py run-check <plan.md> <SPEC> refuse if deps unshipped or revision stale
  plan.py hash <plan.md>            stable hash of the plan (for proof binding)

All three read spec status from specs/*.md, so they report the same truth the
index does: derived, never hand-maintained.
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_vspec = importlib.util.spec_from_file_location("veldo_validate", ROOT / ".veldo" / "validate.py")
V = importlib.util.module_from_spec(_vspec)
_vspec.loader.exec_module(V)


def spec_status_by_id():
    out = {}
    specs = ROOT / "specs"
    if not specs.exists():
        return out
    for p in sorted(specs.glob("*.md")):
        if p.name.startswith("TEMPLATE") or p.name == "index.md":
            continue
        fm = V.front_matter(p.read_text())
        if fm and fm.get("id"):
            out[fm["id"]] = fm.get("status", "?")
    return out


def load_plan(arg):
    """Accept a plan file path or a PLAN-id."""
    p = Path(arg)
    if p.exists():
        m = V.re.match(r"^---\n(.*?)\n---", p.read_text(), V.re.S)
        return (p, V.parse_yamlish(m.group(1))) if m else (p, {})
    reg = V.plan_registry(ROOT / "plans")
    if arg in reg:
        return reg[arg]["path"], reg[arg]["fm"]
    raise SystemExit(f"no plan found: {arg}")


def _work(fm):
    return [w for w in (fm.get("work") or []) if isinstance(w, dict)]


def _shipped_set(fm, status):
    return {w["spec"] for w in _work(fm) if status.get(w.get("spec")) == "shipped"}


def _decision_blocks(fm):
    blocked = {}
    for d in fm.get("open_decisions") or []:
        if isinstance(d, dict):
            for s in d.get("blocks") or []:
                blocked.setdefault(s, []).append(d.get("id"))
    return blocked


def item_state(w, status, shipped, blocked):
    sid = w.get("spec")
    st = status.get(sid)
    waiting = [d for d in (w.get("depends_on") or []) if d not in shipped]
    if st == "shipped":
        return "shipped"
    if waiting:
        return "waiting: " + ", ".join(waiting)
    if sid in blocked:
        return "blocked: decision " + ",".join(blocked[sid])
    return (st or "unstarted") + " (frontier)"


def cmd_status(arg):
    path, fm = load_plan(arg)
    status = spec_status_by_id()
    shipped = _shipped_set(fm, status)
    blocked = _decision_blocks(fm)
    work = sorted(_work(fm), key=lambda w: (w.get("order") or 0))
    print(f"{fm.get('id')} - {fm.get('title', '')}")
    print(f"status {fm.get('status')}, revision {fm.get('revision')}, "
          f"{len(shipped)}/{len(work)} shipped")
    frontier = []
    for w in work:
        state = item_state(w, status, shipped, blocked)
        if state.endswith("(frontier)"):
            frontier.append(f"{w.get('spec')} ({w.get('item')})")
        print(f"  {w.get('item'):<4} {w.get('spec'):<12} {state}")
    print("frontier: " + (", ".join(frontier) if frontier else "none"))
    return 0


def cmd_release_check(arg):
    path, fm = load_plan(arg)
    status = spec_status_by_id()
    work = _work(fm)
    rel = fm.get("release") or {}
    reasons = []
    if str(rel.get("require_all_work_shipped")).lower() == "true":
        unshipped = [w.get("spec") for w in work if status.get(w.get("spec")) != "shipped"]
        if unshipped:
            reasons.append(f"work not shipped: {', '.join(unshipped)}")
    if str(rel.get("require_full_regression")).lower() == "true":
        journeys = (fm.get("regression") or {}).get("journeys") or []
        if not journeys:
            reasons.append("require_full_regression set but no regression journeys defined")
    for d in fm.get("open_decisions") or []:
        if isinstance(d, dict) and (d.get("blocks")):
            reasons.append(f"open decision {d.get('id')} still blocks {', '.join(d['blocks'])}")
    if not rel.get("milestone"):
        reasons.append("no release.milestone")
    if reasons:
        print(f"{fm.get('id')}: NOT releasable")
        for r in reasons:
            print(f"  - {r}")
        return 1
    print(f"{fm.get('id')}: releasable ({rel.get('milestone')})")
    return 0


def cmd_impact(arg, spec_id):
    """Transitive dependents of spec_id within the plan: what a change to it
    could invalidate downstream."""
    path, fm = load_plan(arg)
    work = _work(fm)
    if spec_id not in {w.get("spec") for w in work}:
        raise SystemExit(f"{spec_id} is not a work item of {fm.get('id')}")
    rev = {}
    for w in work:
        for d in w.get("depends_on") or []:
            rev.setdefault(d, []).append(w.get("spec"))
    seen, stack, order = set(), [spec_id], []
    while stack:
        cur = stack.pop()
        for dep in sorted(rev.get(cur, [])):
            if dep not in seen:
                seen.add(dep)
                order.append(dep)
                stack.append(dep)
    status = spec_status_by_id()
    print(f"impact of {spec_id} in {fm.get('id')}:")
    if not order:
        print("  no downstream dependents")
    for s in order:
        print(f"  {s} ({status.get(s, 'unknown')})")
    shipped_downstream = [s for s in order if status.get(s) == "shipped"]
    if shipped_downstream:
        print(f"  WARNING: {len(shipped_downstream)} already-shipped dependent(s) "
              f"may need re-proof: {', '.join(shipped_downstream)}")
    return 0


def _journey_active(j, context, spec_id, shipped):
    """context is 'per_spec' or 'release'. Returns True if journey j runs in
    that context given the shipped set (and, for per_spec, the spec being
    built). Default profiles = both contexts."""
    profs = j.get("profiles") or ["per_spec", "release"]
    if context not in profs:
        return False
    act = j.get("activation") or {}
    when = act.get("when")
    if when == "manual":
        return False          # manual journeys run only on their own trigger
    if when == "start":
        return True
    if isinstance(when, str) and when.startswith("after:"):
        dep = when[len("after:"):]
        # active once the naming spec is shipped (for per_spec, that means
        # shipped before the current spec; the shipped set already excludes it)
        return dep in shipped and dep != spec_id
    return False


def cmd_regression(arg, ctx):
    path, fm = load_plan(arg)
    status = spec_status_by_id()
    shipped = _shipped_set(fm, status)
    journeys = (fm.get("regression") or {}).get("journeys") or []
    if ctx == "release":
        context, spec_id = "release", None
    elif ctx.startswith("per_spec:"):
        context, spec_id = "per_spec", ctx[len("per_spec:"):]
    else:
        raise SystemExit("context must be release or per_spec:<SPEC>")
    active = [j for j in journeys if _journey_active(j, context, spec_id, shipped)]
    print(f"{fm.get('id')} regression active in {ctx}:")
    if not active:
        print("  (none)")
    for j in active:
        owner = f" owner={j['owner_spec']}" if j.get("owner_spec") else ""
        print(f"  {j.get('id')}  [{j.get('suite', 'no suite')}]{owner}")
    # deferred/manual journeys are surfaced so nothing is silently skipped
    manual = [j for j in journeys if (j.get("activation") or {}).get("when") == "manual"]
    if manual and context == "release":
        print("  manual (run on their own trigger, not auto at release):")
        for j in manual:
            print(f"    {j.get('id')}  [{j.get('suite', 'no suite')}]")
    return 0


import hashlib as _hashlib
import json as _json


def plan_hash(fm):
    """Stable content hash of a plan's front matter, excluding volatile keys,
    so a proof can bind to the exact plan state it was built against."""
    volatile = {"approved_at", "recorded_at"}
    payload = {k: v for k, v in fm.items() if k not in volatile}
    blob = _json.dumps(payload, sort_keys=True, default=str)
    return "sha256:" + _hashlib.sha256(blob.encode()).hexdigest()[:16]


def _spec_fm(spec_id):
    from pathlib import Path as _P
    for p in sorted((ROOT / "specs").glob(f"{spec_id}*.md")):
        return V.front_matter(p.read_text()) or {}
    return {}


def _spec_fm_rich(spec_id):
    """Parse a spec's front matter with the full subset parser (parse_yamlish), so
    list fields like placement and footprint arrive as real lists for the mandatory
    placement gate; the simple front_matter reader flattens inline lists to strings."""
    for p in sorted((ROOT / "specs").glob(f"{spec_id}*.md")):
        m = V.re.match(r"^---\n(.*?)\n---", p.read_text(), V.re.S)
        return V.parse_yamlish(m.group(1)) if m else {}
    return {}


def cmd_hash(arg):
    _, fm = load_plan(arg)
    print(plan_hash(fm))
    return 0


def cmd_bundle(arg, spec_id):
    """The whole reaches the part: everything the agent building SPEC needs to
    see the iteration it belongs to, without copying the plan around."""
    path, fm = load_plan(arg)
    work = _work(fm)
    item = next((w for w in work if w.get("spec") == spec_id), None)
    if not item:
        raise SystemExit(f"{spec_id} is not a work item of {fm.get('id')}")
    status = spec_status_by_id()
    print(f"PLAN CONTEXT BUNDLE for {spec_id} ({item.get('item')})")
    print(f"plan: {fm.get('id')} - {fm.get('title')} (revision {fm.get('revision')})")
    print(f"plan_hash: {plan_hash(fm)}")
    print("")
    print("outcomes this iteration must make true:")
    for o in fm.get("outcomes") or []:
        print(f"  {o.get('id')}: {o.get('becomes_true')}")
    print("")
    print(f"this work item: {item.get('title')}")
    frefs = item.get("feature_refs") or []
    for ft in fm.get("feature_tree") or []:
        if ft.get("id") in frefs:
            print(f"  serves feature {ft.get('id')}: {ft.get('title')}")
    deps = item.get("depends_on") or []
    print(f"  depends on: {', '.join(deps) if deps else 'nothing'}")
    for d in deps:
        print(f"    {d}: {status.get(d, 'unknown')}")
    print("")
    print("constraints (inherited by every spec in this plan):")
    for c in fm.get("constraints") or []:
        print(f"  {c.get('id')}: {c.get('text')}")
    print("")
    active = [j for j in (fm.get("regression") or {}).get("journeys") or []
              if _journey_active(j, "per_spec", spec_id, _shipped_set(fm, status))]
    print("regression that must stay green while building this:")
    for j in active:
        print(f"  {j.get('id')}: {j.get('title')} [{j.get('suite', 'no suite')}]")
    if not active:
        print("  (none active for this spec)")
    return 0


def cmd_run_check(arg, spec_id):
    """The run-time refusal: a planned spec may not be built if its declared
    dependencies are not all shipped, if the plan has revised since the spec was
    pulled (its context is stale), or - when the repository carries an architecture
    contract - if it lacks a placement that resolves to a contract area or its risk
    is below the tier its footprint's boundary crossing implies. Deliberate order,
    placement, and tier, enforced at the cheapest moment before the build."""
    path, fm = load_plan(arg)
    work = _work(fm)
    item = next((w for w in work if w.get("spec") == spec_id), None)
    if not item:
        raise SystemExit(f"{spec_id} is not a work item of {fm.get('id')}")
    status = spec_status_by_id()
    reasons = []
    for d in item.get("depends_on") or []:
        if status.get(d) != "shipped":
            reasons.append(f"dependency {d} is {status.get(d, 'unshipped')}, not shipped")
    spec_fm = _spec_fm(spec_id)
    sr = spec_fm.get("plan_revision")
    if sr is not None:
        try:
            sr_i = int(sr)
            if sr_i < int(fm.get("revision", 1)):
                reasons.append(f"stale plan context: spec built against revision {sr_i}, "
                               f"plan is now revision {fm.get('revision')} - re-pull it")
        except (ValueError, TypeError):
            reasons.append(f"spec plan_revision {sr!r} is not an integer")
    # Mandatory placement gate (the O3/RJ2 property) at build time: when a contract
    # exists, a planned spec may not be built (pulled onto a worker) without a placement
    # that resolves to a contract area, and a footprint that crosses an area boundary
    # raises the required tier. Reuses the one predicate (arch.placement_gate via
    # validate) so run-check, the claimable frontier, and the ready transition agree.
    # Adoption safe: no contract in the repository adds no reasons.
    for msg in V.placement_gate_problems(_spec_fm_rich(spec_id), repo_root=ROOT):
        reasons.append(msg)
    if reasons:
        print(f"run-check {spec_id}: REFUSED")
        for r in reasons:
            print(f"  - {r}")
        return 1
    print(f"run-check {spec_id}: clear to build (deps shipped, plan context current)")
    return 0


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    mode, arg = sys.argv[1], sys.argv[2]
    if mode == "status":
        return cmd_status(arg)
    if mode == "release-check":
        return cmd_release_check(arg)
    if mode == "impact":
        if len(sys.argv) < 4:
            print("impact needs a SPEC id")
            return 2
        return cmd_impact(arg, sys.argv[3])
    if mode == "regression":
        if len(sys.argv) < 4:
            print("regression needs a context: per_spec:<SPEC> | release")
            return 2
        return cmd_regression(arg, sys.argv[3])
    if mode == "hash":
        return cmd_hash(arg)
    if mode == "bundle":
        if len(sys.argv) < 4:
            print("bundle needs a SPEC id")
            return 2
        return cmd_bundle(arg, sys.argv[3])
    if mode == "run-check":
        if len(sys.argv) < 4:
            print("run-check needs a SPEC id")
            return 2
        return cmd_run_check(arg, sys.argv[3])
    print(f"unknown mode: {mode}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
