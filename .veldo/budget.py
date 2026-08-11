#!/usr/bin/env python3
"""VELDO cost and token budget governance: track AND enforce spend on the stream.

Spend rides the one existing event stream (.veldo/events.jsonl): tokens and
cost_usd are optional envelope fields an event carries, attributed by the same
correlation_id the rest of the envelope uses (which defaults to the spec/plan
id). This module is a READER and ENFORCER over that single stream, never a
second store: it aggregates spend through metrics.compute() (the one
calculation) and enforces it against the budgets a plan declares.

A plan declares budgets in a light 'budgets' block in its front matter:

  budgets:
    tokens: 500000            # optional plan-level token cap
    cost_usd: 25.0            # optional plan-level cost cap (USD)
    per_spec:                 # optional per-work-item caps
      - spec: WARP-0405
        tokens: 100000
        cost_usd: 5.0

A missing budgets block means no budget governance for that plan (backward
compatible). Plan-level spend is attributed to the plan id and its work-item
spec correlations; a per-spec cap is checked against that spec's correlation
alone. The enforcer reports OVER/UNDER and, if any declared budget is exceeded,
exits non-zero naming the plan or spec and the overage; it exits 0 when every
declared budget is within limit or no budgets are declared.

  python3 .veldo/budget.py check <plan.md | PLAN-id>
  python3 .veldo/budget.py check <plan.md> --json

No state of its own; the events are the truth and metrics.compute() is the one
aggregation, so the enforcer and any dashboard can never disagree.
"""
import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Load the shared reader (single source of truth for spend) and the contract
# parser (for the plan front matter) exactly as the other .veldo tools do -
# importing them rather than reimplementing guarantees one calculation, not two.
_mspec = importlib.util.spec_from_file_location("veldo_metrics", ROOT / ".veldo" / "metrics.py")
metrics = importlib.util.module_from_spec(_mspec)
_mspec.loader.exec_module(metrics)

_vspec = importlib.util.spec_from_file_location("veldo_validate", ROOT / ".veldo" / "validate.py")
V = importlib.util.module_from_spec(_vspec)
_vspec.loader.exec_module(V)

_SPEC_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*-\d+$")
_BUDGET_KEYS = {"tokens", "cost_usd", "per_spec"}
_PER_SPEC_KEYS = {"spec", "tokens", "cost_usd"}


class BudgetError(ValueError):
    """A budgets block that does not satisfy the shape contract.

    Named (and a ValueError subclass) so a malformed budget is loud and never
    silently treated as no-governance. Governs the SHAPE the same lightweight
    yamlish way the plan validator checks plan fields - not a JSON Schema.
    """


def _num(val, where, allow_float):
    """Coerce a cap value to a number. The yamlish front-matter subset parses
    integers but leaves floats (and everything else) as strings, so a numeric
    string is coerced here; a non-numeric or negative value is a BudgetError.
    tokens is integral (allow_float False); cost_usd may be fractional."""
    if isinstance(val, bool):
        raise BudgetError("%s must be a number, got a boolean" % where)
    v = val
    if isinstance(v, str):
        s = v.strip()
        try:
            v = float(s) if (allow_float or "." in s or "e" in s.lower()) else int(s)
        except ValueError:
            raise BudgetError("%s must be a number, got %r" % (where, val))
    if not isinstance(v, (int, float)):
        raise BudgetError("%s must be a number" % where)
    if allow_float:
        v = float(v)
    else:
        if isinstance(v, float) and not v.is_integer():
            raise BudgetError("%s must be an integer" % where)
        v = int(v)
    if v < 0:
        raise BudgetError("%s must be >= 0" % where)
    return v


def parse_budgets(plan_fm):
    """Validate the SHAPE of a plan's 'budgets' block and return it normalized,
    or None when the plan declares no budgets (no governance, backward
    compatible). Raises BudgetError on any malformed shape - a bad budget is a
    decision nobody made about spend, so it is loud, never a silent pass.
    """
    raw = (plan_fm or {}).get("budgets")
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise BudgetError("budgets must be a mapping of caps")
    unknown = set(raw) - _BUDGET_KEYS
    if unknown:
        raise BudgetError("unknown budget key(s): %s (allowed: %s)"
                          % (sorted(unknown), sorted(_BUDGET_KEYS)))
    out = {}
    if "tokens" in raw:
        out["tokens"] = _num(raw["tokens"], "budgets.tokens", allow_float=False)
    if "cost_usd" in raw:
        out["cost_usd"] = _num(raw["cost_usd"], "budgets.cost_usd", allow_float=True)
    per_spec = []
    if "per_spec" in raw:
        entries = raw["per_spec"]
        if not isinstance(entries, list):
            raise BudgetError("budgets.per_spec must be a list of per-spec caps")
        seen = set()
        for ent in entries:
            if not isinstance(ent, dict):
                raise BudgetError("each budgets.per_spec entry must be a mapping")
            unk = set(ent) - _PER_SPEC_KEYS
            if unk:
                raise BudgetError("unknown per_spec key(s): %s (allowed: %s)"
                                  % (sorted(unk), sorted(_PER_SPEC_KEYS)))
            sid = ent.get("spec")
            if not isinstance(sid, str) or not _SPEC_ID_RE.match(sid):
                raise BudgetError("per_spec entry needs a spec id like PREFIX-0000, got %r" % (sid,))
            if sid in seen:
                raise BudgetError("duplicate per_spec entry for %s" % sid)
            seen.add(sid)
            norm = {"spec": sid}
            if "tokens" in ent:
                norm["tokens"] = _num(ent["tokens"], "per_spec[%s].tokens" % sid, allow_float=False)
            if "cost_usd" in ent:
                norm["cost_usd"] = _num(ent["cost_usd"], "per_spec[%s].cost_usd" % sid, allow_float=True)
            if "tokens" not in norm and "cost_usd" not in norm:
                raise BudgetError("per_spec entry for %s declares no cap (tokens or cost_usd)" % sid)
            per_spec.append(norm)
    if per_spec:
        out["per_spec"] = per_spec
    if not out:
        raise BudgetError("budgets block declares no cap (tokens, cost_usd, or per_spec)")
    return out


def plan_work_specs(plan_fm):
    """The spec ids of the plan's work items, in declared order."""
    return [w.get("spec") for w in (plan_fm.get("work") or [])
            if isinstance(w, dict) and w.get("spec")]


def _spend_index(events):
    """The one spend aggregation: metrics.compute()'s spend_by_correlation.

    Reading through compute() is what makes the enforcer's numbers EQUAL the
    reader's and any dashboard's - there is no second calculation here.
    """
    return metrics.compute(events).get("spend_by_correlation", {})


def _corr_spend(by_corr, corr):
    b = by_corr.get(corr) or {}
    return int(b.get("tokens", 0) or 0), float(b.get("cost_usd", 0.0) or 0.0)


def plan_spend(plan_fm, events):
    """Spend attributed to this plan: the plan id and its work-item spec
    correlations, summed - NOT the global stream total (an unrelated plan's
    spend is not this plan's)."""
    by_corr = _spend_index(events)
    corrs = [plan_fm.get("id")] + plan_work_specs(plan_fm)
    tokens, cost = 0, 0.0
    for c in corrs:
        if not c:
            continue
        t, u = _corr_spend(by_corr, c)
        tokens += t
        cost += u
    return {"tokens": tokens, "cost_usd": round(cost, 6)}


def spec_spend(spec_id, events):
    """Spend attributed to one spec: its own correlation alone."""
    t, u = _corr_spend(_spend_index(events), spec_id)
    return {"tokens": t, "cost_usd": round(u, 6)}


def _violation(level, ident, resource, limit, actual):
    return {
        "level": level,          # "plan" or "spec"
        "id": ident,
        "resource": resource,    # "tokens" or "cost_usd"
        "limit": limit,
        "actual": actual,
        "overage": round(actual - limit, 6),
    }


def check(plan_fm, events):
    """Compute spend per plan and per spec over the event stream and return the
    list of budget violations (empty when all within budget or no budgets are
    declared). Raises BudgetError if the declared budgets block is malformed.
    """
    budgets = parse_budgets(plan_fm)
    if not budgets:
        return []
    by_corr = _spend_index(events)
    viols = []

    # plan-level: spend over the plan id and its work-item spec correlations
    corrs = [plan_fm.get("id")] + plan_work_specs(plan_fm)
    p_tokens, p_cost = 0, 0.0
    for c in corrs:
        if not c:
            continue
        t, u = _corr_spend(by_corr, c)
        p_tokens += t
        p_cost += u
    p_cost = round(p_cost, 6)
    plan_id = plan_fm.get("id")
    if budgets.get("tokens") is not None and p_tokens > budgets["tokens"]:
        viols.append(_violation("plan", plan_id, "tokens", budgets["tokens"], p_tokens))
    if budgets.get("cost_usd") is not None and p_cost > budgets["cost_usd"]:
        viols.append(_violation("plan", plan_id, "cost_usd", budgets["cost_usd"], p_cost))

    # per-spec: each cap checked against that spec's own correlation
    for ent in budgets.get("per_spec", []):
        sid = ent["spec"]
        s_tokens, s_cost = _corr_spend(by_corr, sid)
        s_cost = round(s_cost, 6)
        if ent.get("tokens") is not None and s_tokens > ent["tokens"]:
            viols.append(_violation("spec", sid, "tokens", ent["tokens"], s_tokens))
        if ent.get("cost_usd") is not None and s_cost > ent["cost_usd"]:
            viols.append(_violation("spec", sid, "cost_usd", ent["cost_usd"], s_cost))
    return viols


def report_lines(plan_fm, events):
    """Human-readable OVER/UNDER report. Reads the same numbers check() enforces."""
    plan_id = plan_fm.get("id")
    lines = ["budget governance for %s" % plan_id]
    try:
        budgets = parse_budgets(plan_fm)
    except BudgetError as ex:
        lines.append("  MALFORMED budgets block: %s" % ex)
        return lines, None
    if not budgets:
        lines.append("  no budgets declared - no governance")
        return lines, []
    ps = plan_spend(plan_fm, events)
    lines.append("  plan spend: %d tokens, $%s (attributed to the plan and its work specs)"
                 % (ps["tokens"], ps["cost_usd"]))
    viols = check(plan_fm, events)
    if "tokens" in budgets:
        lines.append("  plan tokens: %d / %d cap" % (ps["tokens"], budgets["tokens"]))
    if "cost_usd" in budgets:
        lines.append("  plan cost_usd: $%s / $%s cap" % (ps["cost_usd"], budgets["cost_usd"]))
    for ent in budgets.get("per_spec", []):
        sp = spec_spend(ent["spec"], events)
        caps = []
        if "tokens" in ent:
            caps.append("%d / %d tokens" % (sp["tokens"], ent["tokens"]))
        if "cost_usd" in ent:
            caps.append("$%s / $%s" % (sp["cost_usd"], ent["cost_usd"]))
        lines.append("  spec %s: %s" % (ent["spec"], ", ".join(caps)))
    if not viols:
        lines.append("  RESULT: UNDER budget (all declared caps within limit)")
    else:
        lines.append("  RESULT: OVER budget - %d violation(s):" % len(viols))
        for v in viols:
            lines.append("    OVER %s %s %s: %s exceeds cap %s by %s"
                         % (v["level"], v["id"], v["resource"],
                            v["actual"], v["limit"], v["overage"]))
    return lines, viols


def _load_plan_fm(arg):
    """Accept a plan file path or a PLAN-id and return its front matter."""
    p = Path(arg)
    if p.exists():
        m = V.re.match(r"^---\n(.*?)\n---", p.read_text(), V.re.S)
        if not m:
            raise SystemExit("no front matter in %s" % arg)
        return V.parse_yamlish(m.group(1))
    reg = V.plan_registry(ROOT / "plans")
    if arg in reg:
        return reg[arg]["fm"]
    raise SystemExit("no plan found: %s" % arg)


def main():
    ap = argparse.ArgumentParser(
        description="VELDO cost and token budget governance: enforce declared spend budgets over the event stream.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="check a plan's declared budgets against events.jsonl")
    c.add_argument("plan", help="a plan file path or a PLAN-id")
    c.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    fm = _load_plan_fm(args.plan)
    events = metrics.load()
    if args.cmd == "check":
        try:
            viols = check(fm, events)
        except BudgetError as ex:
            print("budget check: MALFORMED budgets block in %s: %s" % (fm.get("id"), ex))
            return 2
        if args.json:
            print(json.dumps({"plan": fm.get("id"),
                              "plan_spend": plan_spend(fm, events),
                              "violations": viols}, indent=2))
        else:
            lines, _ = report_lines(fm, events)
            print("\n".join(lines))
        return 1 if viols else 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
