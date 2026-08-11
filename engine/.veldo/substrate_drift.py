#!/usr/bin/env python3
"""Drift tripwires: what is declared versus what is actually running (WARP-1506, W6 of PLAN-0015).

Declaring infrastructure in the repository only helps if somebody notices when reality stops
matching. This compares a declaration against a snapshot of actual state and reports the
differences as NAMED findings, each of which drafts exactly one reconciliation unit a human can
promote.

**IN-SESSION ONLY. NEVER A DAEMON (D4).** This is the tripwire pattern: it runs when the gate runs,
when status is asked for, and in the weekly pass. It starts no process, opens no socket and holds
no timer. A drift detector that runs continuously is a service somebody has to operate, and the
thing it would buy - noticing three hours sooner - is not worth a new always-on component with its
own credentials.

**SNAPSHOT ACQUISITION IS OUT OF SCOPE, DELIBERATELY.** This takes a snapshot as an argument. How a
real snapshot is obtained is per-system wiring the plan puts outside itself, and taking it as data
is what lets every rule here be proven offline against fake snapshots.

***

THE DIRECTION RULE (C2), WHICH IS THE PART MOST EASILY GOT WRONG. Drift has two directions and they
are not symmetrical:

  MISSING     declared but not running. Something did not get created, or was deleted outside the
              method. The declaration is the intent, so the reconciliation is to CREATE it.
  UNMANAGED   running but not declared. Somebody made it by hand, or the declaration lost it. The
              reconciliation is NOT to delete it. It is to bring it under management or to have a
              person decide, because deleting a resource nobody declared is exactly how a drift
              tool destroys the thing that was keeping production alive.
  MODIFIED    declared and running but not matching. Reconciliation is to bring the running one
              back to the declaration, field by field, with the differing fields named.

**An automatic delete is never drafted. Not for unmanaged resources, not ever.** The one
destructive direction is the one a human has to choose, and that asymmetry is the whole safety
content of this module.
"""

SCHEMA = "veldo.substrate_drift/v1"

MISSING, UNMANAGED, MODIFIED = "missing", "unmanaged", "modified"
KINDS = (MISSING, UNMANAGED, MODIFIED)

# What reconciliation each direction drafts. Note what is absent: nothing drafts a delete.
RECONCILIATION = {
    MISSING: "create",
    UNMANAGED: "adopt_or_decide",
    MODIFIED: "update_to_declaration",
}

# Fields compared when both sides hold the resource. `name` is the identity, so it cannot differ.
COMPARED = ("kind", "version", "parameters", "depends_on")


def _index(decl):
    return {r["name"]: r for r in (decl or {}).get("resources", [])
            if isinstance(r, dict) and isinstance(r.get("name"), str)}


def compare(declared, snapshot):
    """Every difference between the declaration and the snapshot, as named findings.

    Each finding carries the direction, the resource, the reconciliation it drafts, and for a
    modification the FIELDS that differ - because "drifted" sends somebody diffing by hand and
    "version declared 15.4, running 14.2" does not."""
    d, a = _index(declared), _index(snapshot)
    out = []
    for name in sorted(set(d) | set(a)):
        want, have = d.get(name), a.get(name)
        if have is None:
            out.append({"drift": MISSING, "name": name,
                        "reconciliation": RECONCILIATION[MISSING],
                        "detail": "declared but not running: it was never created, or it was "
                                  "deleted outside the method"})
        elif want is None:
            out.append({"drift": UNMANAGED, "name": name,
                        "reconciliation": RECONCILIATION[UNMANAGED],
                        "detail": "running but not declared: made by hand, or the declaration lost "
                                  "it. NOT drafted for deletion - a person decides"})
        else:
            fields = [f for f in COMPARED if want.get(f) != have.get(f)]
            if fields:
                out.append({"drift": MODIFIED, "name": name, "fields": fields,
                            "reconciliation": RECONCILIATION[MODIFIED],
                            "detail": "; ".join(
                                "%s declared %r, running %r" % (f, want.get(f), have.get(f))
                                for f in fields)})
    return out


def units(findings, environment):
    """One reconciliation unit per finding, IDEMPOTENTLY.

    The id is derived from the environment, the direction and the resource name, so running the
    comparison twice over unchanged drift produces the same units rather than a growing pile. A
    tripwire that manufactures a new work item on every pass trains everybody to ignore it, which
    is the failure mode that makes drift detection worthless in practice."""
    seen, out = set(), []
    for f in findings:
        uid = "drift-%s-%s-%s" % (environment, f["drift"], f["name"])
        if uid in seen:
            continue
        seen.add(uid)
        out.append({
            "id": uid,
            "environment": environment,
            "drift": f["drift"],
            "resource": f["name"],
            "action": f["reconciliation"],
            "for_human": f["drift"] == UNMANAGED,
            "summary": "%s in %s: %s" % (f["drift"], environment, f["detail"]),
        })
    return out


def report(findings, environment):
    """The lines the gate, status and the weekly pass print. One per finding, naming the direction
    and the resource, because a count alone tells nobody what to do."""
    if not findings:
        return ["substrate drift: none in %s" % environment]
    lines = ["substrate drift in %s: %d finding(s)" % (environment, len(findings))]
    for f in findings:
        lines.append("  %-9s %-24s -> %s" % (f["drift"], f["name"], f["reconciliation"]))
    return lines


def drafts_no_deletion(findings):
    """That no finding, in any direction, drafts a deletion. Exposed as a function rather than left
    implicit so the selftest can assert the property directly over generated drift instead of
    trusting the table by eye."""
    return all(f["reconciliation"] != "delete" for f in findings)
