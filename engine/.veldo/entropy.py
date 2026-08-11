#!/usr/bin/env python3
"""VELDO entropy metrics (veldo.entropy/v1): cost-to-change per architecture area - entropy
becomes a NUMBER that trends, not an opinion.

This is the W8 organ of PLAN-0011 and the entropy-reconciliation half of the method's "The
Shape of the System" invention. Decay accumulates through many changes; this module measures
it. Cost-to-change per contract area is DERIVED FROM WHAT THE LOOP ALREADY RECORDS - per-event
tokens and cost, review cycles, gate failures, and human minutes - joined to areas through the
PLACEMENT declarations W3 introduced and the files each change touched. The gate's own static
shape measures (duplication, complexity, boundary pressure) sit on the SAME per-area map. There
is no new instrumentation: the recorded event stream is read through metrics.compute (the single
aggregation), and the join key is the spec's placement/footprint resolved through arch.

Three properties are load bearing:

  REUSE, NOT REINVENT (RULE #6, no shortcuts). The per-correlation cost components come from
  metrics.compute's cost_by_correlation (the one calculation the dashboard and the budget
  enforcer also read), the area resolution is arch.footprint_areas / arch.area_for_path (the one
  place a change maps to the areas it touched), and the static shape measures are shape_gate's
  reference analyzers (the one duplication and complexity implementation). This module adds no
  second parser, no second store, and no second measurement pipeline.

  ADVISORY, NOTHING AUTO-GATES (resolved decision D2, and the invention). The threshold is a
  RELATIVE degradation of an area against its OWN trailing baseline, ADVISORY during a
  calibration period before its crossings are trusted. No absolute number is smuggled in, and
  NOTHING here fails the build: this module is surfaced through the metrics CLI and the
  dashboard, exactly like the sibling metrics derivations, and is never wired into
  scripts/verify.sh or validate.py run_all. A threshold crossing is a SIGNAL the restoration-spec
  generator WARP-1109 (W9) consumes to draft a restoration spec a human promotes; this module
  does not build that draft. The later incident-metrics join (PLAN-0012) is referenced only.

  IN-SESSION ONLY, NOTHING DETACHED (NG1, the contract invariant no_detached_processes, and this
  codebase's feedback_no_rogue_processes). The derivation is a PURE function that reads recorded
  files (events.jsonl, spec front matter, source files) and takes the events and the
  trailing-window policy as INJECTED parameters; it starts no process and no thread, installs no
  timer, and never polls in the background. It runs only where the CLI, the dashboard, and the
  weekly pass invoke it, and nothing outlives the session. A selftest string-scan of the source
  proves it contains no spawn primitive, with mutation teeth.

ADOPTION SAFE. A repository with no architecture contract stands the whole derivation down (a
standdown report); a repository with a contract but no recorded events yields empty series. A
change that declares no placement (history before W3) is UNATTRIBUTED and counted honestly, the
best-effort limit PLAN-0011's data-provenance section names.

  python3 .veldo/entropy.py            # human-readable per-area report
  python3 .veldo/entropy.py --json     # machine-readable (WARP-1109 consumes the crossings)
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SCHEMA = "veldo.entropy/v1"

# The recorded cost dimensions reused from the event stream (no new instrumentation): the
# per-correlation components metrics.compute derives. Each trends on its own series against the
# area's own baseline, so no invented weighting collapses them into one opaque scalar.
COST_DIMENSIONS = ("human_minutes", "tokens", "cost_usd", "review_cycles", "gate_failures")

# D2 threshold-policy defaults (relative degradation vs a trailing baseline, advisory during a
# calibration period). The recommended defaults; tunable per repo. NOTHING here auto-gates on a
# number - a crossing is a signal WARP-1109 (W9) consumes, never a gate refusal.
BASELINE_WINDOW = 5       # trailing prior samples that form an area's baseline
DEGRADATION_FACTOR = 0.5  # latest >= baseline * (1 + factor) is a relative-degradation crossing
CALIBRATION_MIN = 8       # an area needs at least this many samples before crossings are trusted


def _load(name, rel):
    """Load a sibling engine module the way budget.py and dashboard.py do: one canonical source,
    no reimplementation. metrics (the single cost aggregation), validate (the one front-matter
    parser and the arch area resolver, over the allow-listed metrics -> contracts edge), and
    shape_gate (the reference static analyzers) are loaded here."""
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


metrics = _load("veldo_metrics", ".veldo/metrics.py")
V = _load("veldo_validate", ".veldo/validate.py")


def _shape_gate():
    """The gate's static analyzers (.veldo/shape_gate.py), reused for the per-area static shape
    measures so there is one duplication and one complexity implementation. Loaded lazily so a
    report that needs no static measures (a pure series computation in a test) pays nothing."""
    return _load("veldo_shape_gate", ".veldo/shape_gate.py")


def per_correlation_cost(events):
    """The recorded cost components per correlation, straight from metrics.compute (the single
    aggregation): tokens, cost_usd, human_minutes, review_cycles, gate_failures, and ship time.
    No second aggregation - this is metrics.compute's cost_by_correlation, unchanged."""
    return metrics.compute(events).get("cost_by_correlation", {})


def _mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def area_series(events, area_index):
    """Per-area, time-ordered cost-to-change samples. A SAMPLE is one shipped change (a
    correlation with a spec.shipped event, so shipped_at is set) attributed to each contract area
    its placement/footprint touched (area_index[correlation]); a cross-area change contributes
    its recorded cost to EACH area it touched. Returns (series_by_area, stats) where
    series_by_area maps an area id to a list of samples ordered by ship time, each sample a dict
    of the recorded dimensions, and stats carries attributed and unattributed change counts. A
    change with no area (pre-placement history) is unattributed and counted, never dropped."""
    cost = per_correlation_cost(events)
    shipped = [(c, b) for c, b in cost.items() if b.get("shipped_at")]
    shipped.sort(key=lambda cb: (cb[1]["shipped_at"], cb[0]))
    series = {}
    attributed = 0
    unattributed = 0
    for c, b in shipped:
        areas = area_index.get(c) or set()
        if not areas:
            unattributed += 1
            continue
        attributed += 1
        sample = {"correlation": c, "at": b["shipped_at"]}
        for dim in COST_DIMENSIONS:
            sample[dim] = b.get(dim, 0)
        for a in sorted(areas):
            series.setdefault(a, []).append(sample)
    return series, {"attributed_changes": attributed, "unattributed_changes": unattributed}


def detect_crossings(series_by_area, baseline_window=BASELINE_WINDOW,
                     degradation_factor=DEGRADATION_FACTOR, calibration_min=CALIBRATION_MIN):
    """Relative-degradation crossings per D2. For each area and each recorded dimension, compare
    the LATEST sample against the mean of the trailing baseline_window PRIOR samples and flag a
    crossing when the latest is at least baseline * (1 + degradation_factor) with a positive
    baseline: a relative worsening against the area's OWN history, never an absolute threshold. A
    crossing is ADVISORY while the area is still calibrating (fewer than calibration_min samples),
    so a young series is measured but its crossings are not yet trusted. NOTHING here auto-gates -
    a crossing is a signal WARP-1109 (W9) consumes to draft a restoration spec a human promotes.
    Returns a deterministic-order list of crossing dicts."""
    crossings = []
    for area in sorted(series_by_area):
        samples = series_by_area[area]
        n = len(samples)
        if n < 2:
            continue
        calibrating = n < calibration_min
        for dim in COST_DIMENSIONS:
            values = [float(s.get(dim, 0) or 0) for s in samples]
            latest = values[-1]
            prior = values[-(baseline_window + 1):-1]
            baseline = _mean(prior)
            if baseline > 0 and latest >= baseline * (1 + degradation_factor):
                crossings.append({
                    "area": area,
                    "dimension": dim,
                    "latest": round(latest, 6),
                    "baseline": round(baseline, 6),
                    "relative_increase": round((latest - baseline) / baseline, 4),
                    "threshold_factor": degradation_factor,
                    "samples": n,
                    "advisory": calibrating,
                    "consumed_by": "WARP-1109",
                })
    return crossings


def spec_area_index(specs_dir, contract, arch):
    """Map spec id -> the set of contract areas the change TOUCHED, via its declared placement and
    footprint (arch.footprint_areas, the W3 join key). This is the placement-declaration join the
    entropy map needs. A spec with no placement/footprint (pre-W3) contributes no area, so its
    recorded cost is unattributed - the best-effort limit the plan's data-provenance section
    names (per-area attribution starts accumulating when W3 ships)."""
    idx = {}
    d = Path(specs_dir)
    if not d.is_dir():
        return idx
    for p in sorted(d.glob("*.md")):
        if p.name.startswith("TEMPLATE") or p.name == "index.md":
            continue
        m = V.re.match(r"^---\n(.*?)\n---", p.read_text(), V.re.S)
        if not m:
            continue
        try:
            fm = V.parse_yamlish(m.group(1))
        except ValueError:
            continue
        sid = fm.get("id")
        if not sid:
            continue
        areas = arch.footprint_areas(fm, contract)
        if areas:
            idx[sid] = areas
    return idx


def _area_source_files(area_id, contract, root):
    """Repo-relative source files under an area's declared includes globs, expanded against root.
    The one place the contract's area membership becomes concrete files for the static-shape
    snapshot, so the per-area measures cover exactly what the contract declares the area holds."""
    files = []
    for a in (contract.get("areas") or []):
        if not isinstance(a, dict) or a.get("id") != area_id:
            continue
        for inc in (a.get("includes") or []):
            if not isinstance(inc, str) or not inc.strip():
                continue
            if inc.endswith("/**"):
                base = Path(root) / inc[:-3]
                matches = base.rglob("*") if base.is_dir() else []
            else:
                matches = Path(root).glob(inc)
            for pth in matches:
                if pth.is_file():
                    files.append(str(pth.relative_to(root)))
    return sorted(set(files))


def area_static_shape(area_id, contract, arch, sg, root):
    """The gate's static shape measures for one area, REUSED from shape_gate's reference analyzers
    over the area's current source files: duplication, cyclomatic complexity, function length,
    and the boundary-pressure count (references over an unmodeled edge). The contract's own budgets
    supply the limits. Counts only - this is the static half of the per-area entropy map, beside
    the cost-to-change series."""
    files = _area_source_files(area_id, contract, root)
    budgets = {b.get("kind"): b for b in (contract.get("budgets") or []) if isinstance(b, dict)}

    def maxof(kind, default):
        b = budgets.get(kind)
        mx = b.get("max") if isinstance(b, dict) else None
        return mx if isinstance(mx, int) and not isinstance(mx, bool) else default

    return {
        "files": len(files),
        "duplication": len(sg.duplication_findings(files, root, maxof("duplication_ratio", 8))),
        "complexity": len(sg.complexity_findings(files, root, maxof("cyclomatic_complexity", 20))),
        "function_length": len(sg.function_length_findings(files, root, maxof("function_lines", 120))),
        "boundary_pressure": len(sg.boundary_findings(files, root, contract, arch)),
    }


def entropy_report(events=None, root=None):
    """The full per-area entropy map for a repository: the cost-to-change series (from the recorded
    events joined to areas through placement), the static shape measures (from the gate), and the
    relative-baseline threshold crossings (advisory during calibration; WARP-1109 consumes the
    trusted ones). Adoption safe: no architecture contract yields a standdown report and a
    repository without a contract is byte-identically unaffected. Pure over the injected events
    (defaulting to the recorded stream) and the repository's recorded files."""
    root = Path(root or ROOT)
    ev = events if events is not None else metrics.load()
    arch, contract = V.load_repo_contract(repo_root=str(root))
    if contract is None:
        return {"schema": SCHEMA, "standdown": True,
                "reason": "no architecture contract (adoption safe: byte-identically unaffected)",
                "areas": {}, "crossings": [],
                "attributed_changes": 0, "unattributed_changes": 0}
    area_index = spec_area_index(root / "specs", contract, arch)
    series, stats = area_series(ev, area_index)
    crossings = detect_crossings(series)
    sg = _shape_gate()
    areas_out = {}
    for area in sorted(arch.area_ids(contract)):
        samples = series.get(area, [])
        areas_out[area] = {
            "samples": len(samples),
            "calibrating": len(samples) < CALIBRATION_MIN,
            "series": {dim: [s.get(dim) for s in samples] for dim in COST_DIMENSIONS},
            "latest": {dim: (samples[-1].get(dim) if samples else None) for dim in COST_DIMENSIONS},
            "static_shape": area_static_shape(area, contract, arch, sg, str(root)),
        }
    return {
        "schema": SCHEMA,
        "standdown": False,
        "areas": areas_out,
        "crossings": crossings,
        "attributed_changes": stats["attributed_changes"],
        "unattributed_changes": stats["unattributed_changes"],
        "policy": {
            "baseline_window": BASELINE_WINDOW,
            "degradation_factor": DEGRADATION_FACTOR,
            "calibration_min": CALIBRATION_MIN,
            "note": "relative degradation vs a trailing baseline; advisory during calibration; "
                    "nothing auto-gates on a number (D2). Crossings feed WARP-1109 restoration.",
        },
    }


def area_figures(report):
    """The exact per-area figures a renderer shows, each drawn straight from entropy_report, so a
    dashboard consuming this never recomputes a number of its own (the no-fork discipline the
    metrics dashboard already follows). Returns a list of per-area dicts in area order."""
    out = []
    for area in sorted(report.get("areas", {})):
        a = report["areas"][area]
        out.append({
            "area": area,
            "samples": a["samples"],
            "calibrating": a["calibrating"],
            "latest": a["latest"],
            "static_shape": a["static_shape"],
        })
    return out


def render_text(report):
    if report.get("standdown"):
        return "VELDO entropy: no architecture contract, standing down (adoption safe)"
    lines = [
        "VELDO entropy - cost-to-change per area (derived from events.jsonl + placements; "
        "advisory, never gates)",
        "=" * 72,
        "  changes attributed to an area: %d, unattributed (pre-placement history): %d"
        % (report["attributed_changes"], report["unattributed_changes"]),
    ]
    for fig in area_figures(report):
        cal = " [calibrating]" if fig["calibrating"] else ""
        ss = fig["static_shape"]
        lt = fig["latest"]
        lines.append("  area %s: %d change-sample(s)%s" % (fig["area"], fig["samples"], cal))
        lines.append("    latest cost-to-change: human_minutes=%s tokens=%s cost_usd=%s "
                     "review_cycles=%s gate_failures=%s"
                     % (lt["human_minutes"], lt["tokens"], lt["cost_usd"],
                        lt["review_cycles"], lt["gate_failures"]))
        lines.append("    static shape (from the gate): duplication=%d complexity=%d "
                     "function_length=%d boundary_pressure=%d over %d file(s)"
                     % (ss["duplication"], ss["complexity"], ss["function_length"],
                        ss["boundary_pressure"], ss["files"]))
    if report["crossings"]:
        lines.append("  threshold crossings (relative degradation vs trailing baseline; "
                     "WARP-1109 consumes the trusted ones):")
        for c in report["crossings"]:
            tag = "ADVISORY (calibrating)" if c["advisory"] else "TRUSTED"
            lines.append("    %s %s.%s: latest %s vs baseline %s (+%.0f%%), feeds W9 restoration"
                         % (tag, c["area"], c["dimension"], c["latest"], c["baseline"],
                            100 * c["relative_increase"]))
    else:
        lines.append("  threshold crossings: none")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(
        description="VELDO entropy metrics: per-area cost-to-change (advisory, never gates).")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()
    report = entropy_report()
    print(json.dumps(report, indent=2) if args.json else render_text(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
