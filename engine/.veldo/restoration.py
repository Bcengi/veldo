#!/usr/bin/env python3
"""VELDO restoration-spec generation (veldo.restoration/v1): a per-area entropy crossing becomes
RESTORATION INTENT that flows through the normal loop - entropy gets a RESPONSE, not just a number.

This is the W9 organ of PLAN-0011 and the closing half of the method's "The Shape of the System"
invention. WARP-1108 (W8) made decay a NUMBER: a per-area cost-to-change series derived from what
the loop already records, with a RELATIVE-degradation threshold whose crossing is an advisory
SIGNAL (D2). This module is the CONSUMER of that signal. A threshold crossing on an area's series
DRAFTS a restoration spec that NAMES the area, the crossed rule (the cost-to-change dimension that
degraded), and the EXPECTED post-restoration measure (the area's own trailing baseline, the level
the restoration must bring the cost-to-change back to). The work then flows through the normal loop
like any spec, and the post-restoration measure CLOSES THE LOOP by reporting the cost delta.

Four properties are load bearing and enforced honestly (RULE #6, no shortcuts):

  A DRAFT ONLY A HUMAN PROMOTES (NG2, the plan's no-self-promotion rule). The draft is a
  veldo.restoration/v1 restoration-INTENT artifact homed per-repo under .veldo/restorations/ (a
  directory the engine glob does not sweep), carrying status: draft, drafted_by the machine, and
  NO decider, NO chosen option, NO promoted flag. A HUMAN promotes it: reads the intent and authors
  a real veldo.spec/v1 restoration spec placed in the named area, which then flows through the normal
  loop (spec, gate, proof, fresh-context review) exactly like any other spec. The machine drafts the
  intent; it never authors the spec, never promotes its own draft, and never restores anything
  itself. This mirrors WARP-1107 (W7), where a fired decision tripwire drafts a veldo.redecision/v1
  DRAFT a human promotes into a full decision record; here a crossing drafts a restoration intent a
  human promotes into a full spec. Drafting a real claimable spec directly would be the machine
  injecting its own work onto the frontier, exactly the self-promotion NG2 forbids.

  IDEMPOTENT (the plan's re-derivation rule). The idempotency key is the crossed rule in an area:
  the (area, dimension) pair, rendered .veldo/restorations/<area>__<dimension>.yaml. Re-deriving the
  SAME crossing resolves to the SAME file, and an existing draft is NEVER overwritten, so a second
  derivation of the same crossing drafts no duplicate. Only a TRUSTED crossing drafts: an ADVISORY
  crossing (the area is still calibrating, D2) is measured and surfaced but does NOT draft, because
  D2's generation starts advisory before its drafts are trusted. This is the FIRED-versus-warning
  split WARP-1107 uses (a breach fires, an approaching-breach only warns).

  THE LOOP CLOSES ON THE COST DELTA (O6). restoration_delta reports the AFTER-versus-BEFORE area
  measure: the draft records the BEFORE measure at crossing time (the degraded latest and the
  baseline it degraded from); once a restoration ships, the area's current cost-to-change for the
  crossed dimension is the AFTER measure, and the delta (before minus after) plus a paid_off finding
  (the cost-to-change returned to or below the pre-degradation baseline) proves whether the refactor
  paid off. Pure over the injected recorded events (the W8 derivation) and the recorded draft.

  IN-SESSION ONLY, NOTHING DETACHED (NG1, the contract invariant no_detached_processes, this
  codebase's feedback_no_rogue_processes). The derivation is a pure read over recorded files
  (events.jsonl through the W8 entropy report, and the draft files) and the drafting is an EXPLICIT
  in-session write action a CLI or the weekly pass invokes; it starts no process and no thread,
  installs no timer, and never polls in the background. It runs only where the CLI and the weekly
  pass invoke it. NOTHING AUTO-GATES and NOTHING AUTO-PROMOTES: like the W8 entropy derivation this
  module is never wired into scripts/verify.sh or validate.py run_all, so no crossing ever fails the
  build and no draft is ever promoted without a human. A selftest string-scan of the source proves
  it contains no spawn primitive, with mutation teeth.

REUSE, NOT REINVENT (RULE #6). The crossings come from .veldo/entropy.py (W8: detect_crossings and
entropy_report, the ONE detection), the area cost measure comes from the SAME entropy report (no
second aggregation), and the front-matter parser is validate.parse_yamlish through the entropy
module's own validate handle (no second parser, no second store). This module adds only the drafting
and the close-the-loop measure.

ADOPTION SAFE. A repository with no architecture contract stands the whole W8 derivation down, so
there are no crossings and nothing drafts (a standdown report); a repository with a contract but no
trusted crossing drafts nothing. The restoration drafts are per-repo generated artifacts (like the
re-decision drafts), never shipped in the engine.

  python3 .veldo/restoration.py            # report: trusted crossings (would draft), advisory, drafts
  python3 .veldo/restoration.py --draft    # write a draft per trusted crossing (idempotent, in-session)
  python3 .veldo/restoration.py --close    # report the cost delta for existing drafts (close the loop)
  python3 .veldo/restoration.py --json     # machine-readable
"""
import argparse
import importlib.util
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SCHEMA = "veldo.restoration/v1"


def _load(name, rel):
    """Load a sibling engine module the way entropy.py and dashboard.py do: one canonical source,
    no reimplementation. .veldo/entropy.py (W8) is the ONE crossing detection and the ONE per-area
    cost measure; it in turn owns the single metrics aggregation and the single front-matter
    parser, so this module reuses both through it and adds no second detection, store, or parser."""
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


entropy = _load("veldo_entropy", ".veldo/entropy.py")
# The one front-matter parser (validate.parse_yamlish), reached through the entropy module's own
# validate handle so this module never opens a second parser. entropy.V is .veldo/validate.py.
V = entropy.V


def default_restorations_dir(root=None):
    return Path(root or ".") / ".veldo" / "restorations"


def crossing_key(crossing):
    """The idempotency key for a crossing: the crossed rule in an area, the (area, dimension) pair.
    Two derivations of the SAME crossing yield the SAME key, so the draft file is written once and a
    re-derivation never drafts a duplicate. area ids and the fixed cost dimensions are filename-safe
    tokens, so the key doubles as the draft's basename <area>__<dimension>."""
    return "%s__%s" % (crossing.get("area"), crossing.get("dimension"))


def trusted_crossings(report):
    """The crossings from a W8 entropy report that are TRUSTED (not advisory): the actionable ones
    D2 names. An advisory crossing (the area is still calibrating) is measured but not yet trusted,
    so it never drafts - generation starts advisory before its drafts are trusted (D2). This is the
    FIRED-versus-warning split the tripwire pass uses, applied to the crossing signal."""
    return [c for c in (report.get("crossings") or []) if not c.get("advisory")]


def advisory_crossings(report):
    """The crossings that are ADVISORY (the area is still calibrating): surfaced for visibility but
    NOT drafted, so a young series is not punished for having no history (D2)."""
    return [c for c in (report.get("crossings") or []) if c.get("advisory")]


def _num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.strip())
        except ValueError:
            return None
    return None


def _pct(crossing):
    ri = crossing.get("relative_increase")
    n = _num(ri)
    return 0.0 if n is None else 100 * n


def render_draft(crossing, today):
    """Render one veldo.restoration/v1 DRAFT for a human to promote into a real veldo.spec/v1
    restoration spec. It NAMES the area, the crossed rule (the cost-to-change dimension that
    degraded against the area's own trailing baseline), and the EXPECTED post-restoration measure
    (the baseline the restoration must bring the cost-to-change back to). It records the BEFORE
    measure so the loop can close on the cost delta once the restoration ships. It carries status
    draft and NO decider, NO chosen, NO promoted flag: the machine drafts, a human promotes (NG2)."""
    area = crossing.get("area")
    dim = crossing.get("dimension")
    latest = crossing.get("latest")
    baseline = crossing.get("baseline")
    lines = [
        "# VELDO restoration draft (veldo.restoration/v1): a per-area cost-to-change series crossed",
        "# its relative-degradation threshold (PLAN-0011 W9, resolved decision D2), so the area's",
        "# entropy must be RESTORED through the normal loop. This is a DRAFT the entropy pass wrote",
        "# for a HUMAN to promote: read the intent, author a veldo.spec/v1 restoration spec placed in",
        "# the named area, and let it flow through the loop like any spec. The machine drafts the",
        "# intent; it never authors the spec, never promotes its own draft, and never restores",
        "# anything itself (NG2). The loop closes when the area's cost-to-change for the crossed",
        "# rule returns to or below the expected measure (run restoration.py --close after it ships).",
        "schema: %s" % SCHEMA,
        "status: draft",
        "drafted_by: veldo-entropy-pass (machine draft; a human promotes it into a veldo.spec/v1 restoration spec)",
        "drafted_at: %s" % today.isoformat(),
        "area: %s" % area,
        "crossed_rule: %s" % dim,
        "reason: the %s cost-to-change for area %s rose to %s against its own trailing baseline %s "
        "(+%.0f%%), crossing the relative-degradation threshold; restore the area so the "
        "cost-to-change returns to baseline." % (dim, area, latest, baseline, _pct(crossing)),
        "before:",
        "  latest: %s" % latest,
        "  baseline: %s" % baseline,
        "  relative_increase: %s" % crossing.get("relative_increase"),
        "expected_post_restoration_measure:",
        "  dimension: %s" % dim,
        "  target: %s" % baseline,
        "  condition: <= %s" % baseline,
    ]
    return "\n".join(lines) + "\n"


def draft_from_crossings(crossings, restorations_dir, today=None):
    """Draft exactly ONE veldo.restoration/v1 DRAFT per TRUSTED crossing under restorations_dir,
    keyed by the (area, dimension) pair so a re-derivation of the same crossing never drafts a
    duplicate (an existing draft is never overwritten). Advisory crossings are skipped (D2: not yet
    trusted). This writes a file (an explicit in-session action a CLI or the weekly pass invokes),
    but starts NO process and NO thread. Pure over the crossings list and the directory. Returns a
    list of (key, 'created' | 'exists')."""
    today = today or date.today()
    rdir = Path(restorations_dir)
    out = []
    seen = set()
    for c in crossings:
        if c.get("advisory"):
            continue
        key = crossing_key(c)
        if key in seen:
            continue
        seen.add(key)
        dst = rdir / ("%s.yaml" % key)
        if dst.exists():
            out.append((key, "exists"))
            continue
        rdir.mkdir(parents=True, exist_ok=True)
        dst.write_text(render_draft(c, today))
        out.append((key, "created"))
    return out


def draft_restorations(events=None, root=None, restorations_dir=None, today=None):
    """The in-session drafting pass over the recorded event stream (the W9 organ). Reads the W8
    entropy report (the ONE crossing detection) over the injected events (defaulting to the recorded
    stream) and this repository's contract, and drafts exactly one restoration DRAFT per TRUSTED
    crossing for a human to promote. Adoption safe: no architecture contract stands the derivation
    down (no crossings, nothing drafts). Idempotent. Reads recorded files and writes a draft file;
    starts nothing. Returns (drafts, report) where drafts is the (key, outcome) list."""
    base = Path(root or ROOT)
    report = entropy.entropy_report(events=events, root=base)
    rdir = Path(restorations_dir) if restorations_dir else default_restorations_dir(base)
    drafts = draft_from_crossings(trusted_crossings(report), rdir, today=today)
    return drafts, report


def load_draft(path, parse=None):
    """The parsed veldo.restoration/v1 draft at path, using the ONE front-matter parser
    (validate.parse_yamlish through the entropy module). Returns a dict, or raises ValueError on
    unparseable input. The single place a draft is read back, so the close pass reuses it."""
    parse = parse or V.parse_yamlish
    return parse(Path(path).read_text())


def restoration_delta(draft, after_latest):
    """CLOSE THE LOOP for one restoration draft: report the AFTER-versus-BEFORE area measure. The
    draft recorded the BEFORE measure at crossing time (the degraded latest and the baseline it
    degraded from); after_latest is the area's CURRENT cost-to-change for the crossed dimension once
    a restoration has shipped. Returns the delta (before minus after, positive when the cost-to-change
    dropped) and paid_off (the cost-to-change returned to or below the pre-degradation baseline).
    Pure over the draft dict and one number; touches no filesystem and starts nothing."""
    before = draft.get("before") if isinstance(draft.get("before"), dict) else {}
    before_latest = _num(before.get("latest"))
    before_baseline = _num(before.get("baseline"))
    after = _num(after_latest)
    delta = (before_latest - after) if (before_latest is not None and after is not None) else None
    paid_off = (after is not None and before_baseline is not None and after <= before_baseline)
    return {
        "area": draft.get("area"),
        "crossed_rule": draft.get("crossed_rule"),
        "before_latest": before_latest,
        "before_baseline": before_baseline,
        "after_latest": after,
        "delta": delta,
        "paid_off": paid_off,
        "measured": after is not None,
    }


def _area_latest(report, area, dimension):
    """The area's current cost-to-change for one dimension from a W8 entropy report, or None when
    the area has no samples yet. The one place the AFTER measure is read, straight from the report,
    so the close pass never recomputes a number of its own."""
    a = (report.get("areas") or {}).get(area)
    if not isinstance(a, dict):
        return None
    return (a.get("latest") or {}).get(dimension)


def close_restorations(events=None, root=None, restorations_dir=None):
    """The in-session close pass: for each existing restoration draft, recompute the area's current
    cost-to-change (from the SAME W8 entropy report) and report the after-versus-before cost delta.
    Adoption safe: no drafts yields an empty list; no contract stands the derivation down. Reads
    recorded files only and starts nothing. Returns a list of delta dicts (one per readable draft)."""
    base = Path(root or ROOT)
    rdir = Path(restorations_dir) if restorations_dir else default_restorations_dir(base)
    if not rdir.is_dir():
        return []
    report = entropy.entropy_report(events=events, root=base)
    out = []
    for p in sorted(rdir.glob("*.yaml")):
        try:
            draft = load_draft(p)
        except ValueError:
            continue
        if not isinstance(draft, dict) or draft.get("schema") != SCHEMA:
            continue
        after = _area_latest(report, draft.get("area"), draft.get("crossed_rule"))
        out.append(restoration_delta(draft, after))
    return out


def report_model(events=None, root=None, restorations_dir=None):
    """The full machine-readable model: the trusted crossings that WOULD draft, the advisory
    crossings surfaced only, the existing drafts, and the close-the-loop deltas. Pure read over the
    injected events and the recorded drafts; the CLI renders this and --draft writes from it."""
    base = Path(root or ROOT)
    report = entropy.entropy_report(events=events, root=base)
    rdir = Path(restorations_dir) if restorations_dir else default_restorations_dir(base)
    existing = sorted(p.name for p in rdir.glob("*.yaml")) if rdir.is_dir() else []
    return {
        "schema": SCHEMA,
        "standdown": bool(report.get("standdown")),
        "trusted_crossings": trusted_crossings(report),
        "advisory_crossings": advisory_crossings(report),
        "existing_drafts": existing,
        "deltas": close_restorations(events=events, root=base, restorations_dir=rdir),
    }


def render_text(model):
    if model.get("standdown"):
        return "VELDO restoration: no architecture contract, standing down (adoption safe)"
    lines = [
        "VELDO restoration - entropy crossings become restoration intent a human promotes (advisory, "
        "never gates, never self-promotes)",
        "=" * 72,
    ]
    trusted = model["trusted_crossings"]
    if trusted:
        lines.append("  trusted crossings (each drafts one restoration intent under .veldo/restorations/):")
        for c in trusted:
            lines.append("    %s.%s: latest %s vs baseline %s (+%.0f%%) -> restore to <= %s"
                         % (c["area"], c["dimension"], c["latest"], c["baseline"],
                            _pct(c), c["baseline"]))
    else:
        lines.append("  trusted crossings: none")
    for c in model["advisory_crossings"]:
        lines.append("    ADVISORY (calibrating, not drafted) %s.%s: latest %s vs baseline %s"
                     % (c["area"], c["dimension"], c["latest"], c["baseline"]))
    lines.append("  existing drafts: %s" % (", ".join(model["existing_drafts"]) or "none"))
    for d in model["deltas"]:
        if not d["measured"]:
            lines.append("    %s.%s: not yet measured (no post-restoration sample)"
                         % (d["area"], d["crossed_rule"]))
        else:
            verdict = "PAID OFF" if d["paid_off"] else "not yet at baseline"
            lines.append("    %s.%s close: before %s -> after %s (delta %s), %s"
                         % (d["area"], d["crossed_rule"], d["before_latest"],
                            d["after_latest"], d["delta"], verdict))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(
        description="VELDO restoration-spec generation: an entropy crossing drafts a restoration "
                    "intent a human promotes (advisory, never gates, never self-promotes).")
    ap.add_argument("--draft", action="store_true",
                    help="write one restoration draft per trusted crossing (idempotent, in-session)")
    ap.add_argument("--close", action="store_true",
                    help="report the cost delta for existing drafts (close the loop)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()
    if args.draft:
        drafts, _report = draft_restorations()
        for key, outcome in drafts:
            print("  restoration draft %s: %s" % (key, outcome))
        if not drafts:
            print("  no trusted crossing to draft (advisory or none; adoption safe)")
        return 0
    model = report_model()
    if args.json:
        print(json.dumps(model, indent=2))
    else:
        print(render_text(model))
    return 0


if __name__ == "__main__":
    sys.exit(main())
