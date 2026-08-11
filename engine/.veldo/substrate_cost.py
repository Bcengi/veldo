#!/usr/bin/env python3
"""Cost in the proof: an infrastructure change declares what it will cost (WARP-1503, W3 of PLAN-0015).

THE PROBLEM. Infrastructure spend is discovered on a monthly bill, weeks after the change that
caused it, by which time nobody remembers which change it was. Meanwhile the change itself went
through a review where the one number that mattered was never on the page. So the cost delta
becomes a required proof element: it is computed from the plan, held against a declared budget for
the environment, and read by a human before the change lands rather than by an accountant after.

DECLARED STATIC ESTIMATES FIRST, PRICING ADAPTERS AS A SLOT (D2). A live pricing API is a
dependency, a credential and a network call in the gate, and it buys precision nobody needs at
review time: the question is "is this ten dollars or ten thousand", not "is this $412.60 or
$418.90". So the shipped source is a declared price table in the repository, versioned and
reviewable like anything else, and `PriceSource` is the seam a real adapter can arrive at later.

OVER BUDGET REFUSES, AND NAMES THE BUDGET. A refusal that says "too expensive" sends someone to
read code. A refusal that says which environment, what the delta was, what the budget is and which
resources drove it is a refusal somebody can act on in one read.

***

TWO HONEST LIMITS, both stated because this is the kind of module that gets over-trusted.

**A static table is an estimate, not a bill.** It says what the declared prices imply, and it is
wrong whenever the table is stale or a resource's real cost depends on usage the declaration cannot
see - egress, request volume, storage growth. The budget check is a guard against an obvious
mistake, not a forecast.

**An unpriced resource kind is NOT free, and this module refuses to pretend otherwise.** A kind
missing from the table produces `unpriced`, and an unpriced change is reported rather than costed
at zero. Treating unknown as zero is how a budget check passes a change that doubles the bill.
"""

SCHEMA = "veldo.substrate_cost/v1"

# The declared price table, monthly, in whole currency units. Repo-committed and reviewable: a
# price change is a diff somebody reads, which is the property a live pricing API would remove.
# Deliberately coarse. See the docstring: the question at review time is the order of magnitude.
DEFAULT_PRICES = {
    "compute": 40.0,
    "container_service": 25.0,
    "serverless_function": 5.0,
    "static_site": 1.0,
    "relational_database": 90.0,
    "document_database": 70.0,
    "cache": 30.0,
    "object_store": 5.0,
    "queue": 5.0,
    "topic": 5.0,
    "scheduler": 1.0,
    "load_balancer": 20.0,
    "dns_record": 0.0,
    "certificate": 0.0,
    "network": 10.0,
    "firewall_rule": 0.0,
    "secret_reference": 0.0,
    "identity": 0.0,
    "role_binding": 0.0,
    "observability_sink": 15.0,
    "log_group": 5.0,
    "dashboard": 0.0,
    "alert_rule": 0.0,
}

# A budget per environment, monthly. An environment with no declared budget is UNBUDGETED, which is
# reported and does not silently pass: see `check`.
DEFAULT_BUDGETS = {
    "ephemeral": 50.0,
    "development": 200.0,
    "staging": 500.0,
    "production": 5000.0,
}

CREATE, UPDATE, REPLACE, DELETE = "create", "update", "replace", "delete"


class PriceSource:
    """The seam a real pricing adapter arrives at. The shipped implementation is the declared
    table; a live adapter would implement `monthly` against a provider's API. Kept as a class
    rather than a bare dict so that swapping it never means changing a caller."""

    def __init__(self, prices=None):
        self._prices = dict(DEFAULT_PRICES if prices is None else prices)

    def monthly(self, kind):
        """The declared monthly cost of one resource of this kind, or None if UNPRICED.

        None is not zero and callers must not coerce it. A kind absent from the table is a kind
        nobody has priced, and costing it at zero is how a budget check waves through the change
        that doubles the bill."""
        return self._prices.get(kind)

    def known(self):
        return set(self._prices)


def _kind(op):
    r = op.get("after") if op.get("op") != DELETE else op.get("before")
    return (r or {}).get("kind")


def delta(plan, source=None):
    """The projected monthly cost change of one plan, plus what could not be priced.

    Sign convention, stated because getting it backwards is silent: a CREATE adds, a DELETE
    subtracts, a REPLACE is the difference between the two kinds (usually zero, non-zero when the
    kind itself changed), and an UPDATE is zero because changing a parameter does not change what
    the resource IS. The table prices KINDS, so an update that resizes a machine is invisible here
    - that is the static-table limit and it is in the docstring, not hidden."""
    src = source or PriceSource()
    total, unpriced, lines = 0.0, [], []
    for op in (plan or {}).get("operations", []):
        o = op.get("op")
        name = op.get("name")
        if o == UPDATE:
            lines.append({"name": name, "op": o, "monthly": 0.0})
            continue
        if o == REPLACE:
            before = src.monthly((op.get("before") or {}).get("kind"))
            after = src.monthly((op.get("after") or {}).get("kind"))
            if before is None or after is None:
                unpriced.append({"name": name, "op": o, "kind": _kind(op)})
                continue
            d = after - before
        else:
            price = src.monthly(_kind(op))
            if price is None:
                unpriced.append({"name": name, "op": o, "kind": _kind(op)})
                continue
            d = price if o == CREATE else -price
        total += d
        lines.append({"name": name, "op": o, "monthly": round(d, 2)})
    return {
        "schema": SCHEMA,
        "monthly_delta": round(total, 2),
        "lines": lines,
        "unpriced": unpriced,
        "priced_all": not unpriced,
    }


def check(plan, environment, current_monthly=0.0, source=None, budgets=None):
    """Does this change fit the environment's declared budget? Returns (ok, reason, detail).

    THREE WAYS TO FAIL, each named separately, because "no" is not an actionable answer:
      unpriced_resources   something in the plan has no declared price, so the delta is not a
                           total and no budget claim can honestly be made about it
      no_declared_budget   the environment has no budget, so there is nothing to hold the change
                           to - reported rather than passed, since silence is not permission
      over_budget          the projection exceeds the budget, with the numbers and the resources
                           that drove it named
    """
    b = dict(DEFAULT_BUDGETS if budgets is None else budgets)
    d = delta(plan, source)
    if d["unpriced"]:
        names = ", ".join("%s (%s)" % (u["name"], u["kind"]) for u in d["unpriced"][:4])
        return (False, "unpriced_resources",
                "%d resource(s) have no declared price, so this delta is not a total and no budget "
                "claim can be made: %s. An unpriced kind is NOT free; price it or the check cannot "
                "protect you" % (len(d["unpriced"]), names), d)
    if environment not in b:
        return (False, "no_declared_budget",
                "environment %r has no declared budget, so there is nothing to hold this change to. "
                "Silence is not permission" % (environment,), d)
    projected = round(float(current_monthly) + d["monthly_delta"], 2)
    if projected > b[environment]:
        drivers = sorted((l for l in d["lines"] if l["monthly"] > 0),
                         key=lambda l: -l["monthly"])[:3]
        return (False, "over_budget",
                "projected %.2f exceeds the declared %s budget of %.2f (current %.2f, delta %+.2f). "
                "Largest contributors: %s"
                % (projected, environment, b[environment], float(current_monthly),
                   d["monthly_delta"],
                   ", ".join("%s +%.2f" % (l["name"], l["monthly"]) for l in drivers) or "none"),
                d)
    return (True, "within_budget",
            "projected %.2f against the declared %s budget of %.2f (delta %+.2f)"
            % (projected, environment, b[environment], d["monthly_delta"]), d)
