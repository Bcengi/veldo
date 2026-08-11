#!/usr/bin/env python3
"""Regenerate specs/index.md from specification and plan front matter.

The index is derived, never authoritative: if the index and a specification
disagree, the specification wins. The plan section is the burn-down: per-item
state comes from the spec files, the frontier is computed from shipped
dependencies, and nothing here is ever hand-edited. Run after any spec or
plan change, or let the /veldo:index skill do it.
"""
import importlib.util, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPECS = ROOT / "specs"
PLANS = ROOT / "plans"

_vspec = importlib.util.spec_from_file_location("veldo_validate", ROOT / ".veldo" / "validate.py")
V = importlib.util.module_from_spec(_vspec)
_vspec.loader.exec_module(V)


def front_matter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        if re.match(r"^[A-Za-z_]+:", line):
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip()
    return fm


def spec_status_by_id():
    out = {}
    for p in sorted(SPECS.glob("*.md")):
        if p.name.startswith("TEMPLATE") or p.name == "index.md":
            continue
        fm = front_matter(p.read_text())
        if fm.get("id"):
            out[fm["id"]] = fm.get("status", "?")
    return out


def plan_lines():
    if not PLANS.exists():
        return []
    reg = V.plan_registry(PLANS)
    if not reg:
        return []
    status_by_id = spec_status_by_id()
    lines = ["", "## Product Plans", ""]
    for pid in sorted(reg):
        fm = reg[pid]["fm"]
        work = [w for w in (fm.get("work") or []) if isinstance(w, dict)]
        blocked_by_decision = {}
        for d in fm.get("open_decisions") or []:
            if isinstance(d, dict):
                for s in d.get("blocks") or []:
                    blocked_by_decision.setdefault(s, []).append(d.get("id"))
        shipped = {w["spec"] for w in work if status_by_id.get(w.get("spec")) == "shipped"}
        rows, frontier = [], []
        for w in sorted(work, key=lambda w: (w.get("order") or 0)):
            sid = w.get("spec")
            st = status_by_id.get(sid)
            waiting = [d for d in (w.get("depends_on") or []) if d not in shipped]
            if st == "shipped":
                state = "shipped"
            elif waiting:
                state = "waiting: " + ", ".join(waiting)
            elif sid in blocked_by_decision:
                state = "blocked: decision " + ",".join(blocked_by_decision[sid])
            else:
                state = st if st else "unstarted"
                state += " (frontier)"
                frontier.append(f"{sid} ({w.get('item')})")
            rows.append((w.get("item", "?"), sid or "?", str(w.get("title", "")),
                         ", ".join(w.get("depends_on") or []) or "-", state))
        lines.append(f"### {pid} - {fm.get('title', '')}")
        lines.append("")
        lines.append(f"Status {fm.get('status', '?')}, revision {fm.get('revision', '?')}, "
                     f"owner {fm.get('owner', '?')}. "
                     f"{len(shipped)}/{len(work)} work items shipped.")
        if frontier:
            lines.append(f"Ready frontier: {', '.join(frontier)}.")
        for d in fm.get("open_decisions") or []:
            if isinstance(d, dict) and d.get("id"):
                blocks = ", ".join(d.get("blocks") or []) or "nothing"
                lines.append(f"Open decision {d['id']} blocks: {blocks}.")
        lines.append("")
        lines.append("| Item | Spec | Title | Depends on | State |")
        lines.append("|---|---|---|---|---|")
        for r in rows:
            lines.append("| " + " | ".join(r) + " |")
        lines.append("")
    return lines


def main():
    rows = []
    for p in sorted(SPECS.glob("*.md")):
        if p.name.startswith("TEMPLATE") or p.name == "index.md":
            continue
        fm = front_matter(p.read_text())
        rows.append((
            fm.get("id", p.stem),
            fm.get("title", ""),
            fm.get("status", "?"),
            fm.get("risk", "?").split()[0] if fm.get("risk") else "?",
            fm.get("owner", "?"),
            fm.get("human_approval", "not_required").split()[0],
            p.name,
        ))

    order = {"in_progress": 0, "review": 1, "ready": 2, "blocked": 3,
             "draft": 4, "proven": 5, "shipped": 6}
    rows.sort(key=lambda r: (order.get(r[2], 9), r[0]))

    lines = [
        "# Specification Index",
        "",
        # NO GENERATION DATE. This file is checked by REGENERATING it and comparing, so a wall
        # clock in the output makes it differ from itself on any later day: a fresh clone ran the
        # gate and got a RED on a date stamp, with nothing actually wrong. A derived artifact that
        # must be byte-reproducible cannot carry the time it was produced, and the date was never
        # checkable anyway - git records when this changed, accurately, and for free.
        "Generated from specification front matter. "
        "Derived, never authoritative: the specification file wins.",
        "",
        "| ID | Title | Status | Risk | Owner | Approval | File |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append("| " + " | ".join(r) + " |")
    if not rows:
        lines.append("| - | no specifications yet | - | - | - | - | - |")
    lines.extend(plan_lines())
    (SPECS / "index.md").write_text("\n".join(lines) + "\n")
    print(f"index: {len(rows)} specification(s)")


if __name__ == "__main__":
    main()
