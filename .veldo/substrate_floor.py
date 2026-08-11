#!/usr/bin/env python3
"""The destructive-action floor for substrate changes (WARP-1504, W4 of PLAN-0015).

WHAT IT DOES. Classifies the operations in an infrastructure plan by what they destroy, raises the
risk tier accordingly, and refuses a destructive change that does not carry BOTH keys bound to that
exact plan. Deleting a database is not the same kind of act as adding a DNS record, and a method
that treats them alike is either too slow for the second or too fast for the first.

THE CLASSIFICATION, and the reason it is coarse on purpose. Three tiers:

  standard   nothing is destroyed. Creates, updates, and deletes of resources that hold no state.
  high       something existing is destroyed or replaced, but it holds no state a person could
             lose - a load balancer, a DNS record, a firewall rule. Recoverable by re-applying the
             declaration.
  critical   a STATEFUL resource is deleted or replaced. A database, an object store, a cache with
             anything durable in it. Re-applying the declaration gets you an empty one, which is
             the definition of the thing you cannot undo.

STATEFULNESS IS DECLARED, NOT GUESSED, and the default is the strict direction. `STATEFUL_KINDS`
names what holds durable data, and a kind nobody has classified counts as STATEFUL. That asymmetry
is the whole safety property: a new resource kind that nobody thought about gets the critical
treatment until somebody says otherwise, rather than sliding under the floor because a list was
not updated.

NO SECOND TWO-KEY IMPLEMENTATION. The keys are checked by `.veldo/two_key.py`, the same module the
production responder uses, because a second implementation of "two humans agreed" is a second thing
to get subtly wrong and a second thing an attacker can pick between. This module decides WHICH
changes need the discipline; it does not re-decide what the discipline IS.

WHAT IT IS NOT. It does not prevent destruction - it makes destruction a decision somebody made on
the record, bound to an exact plan digest, with two independent humans behind it. A method that
made deletion impossible would simply be routed around.
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

STANDARD, HIGH, CRITICAL = "standard", "high", "critical"

# Resource kinds that hold durable data. Deleting or replacing one of these loses something that
# re-applying the declaration will not bring back.
STATEFUL_KINDS = frozenset({
    "relational_database", "document_database", "object_store", "cache", "queue", "topic",
    "log_group",
})

# Kinds that are definitively stateless, so an unknown kind is neither and lands in the strict
# direction. Declared explicitly rather than inferred as "not in STATEFUL_KINDS", because that
# inference is what would let a new kind pass unexamined.
STATELESS_KINDS = frozenset({
    "compute", "container_service", "serverless_function", "static_site", "scheduler",
    "load_balancer", "dns_record", "certificate", "network", "firewall_rule",
    "secret_reference", "identity", "role_binding", "observability_sink", "dashboard",
    "alert_rule",
})

DESTRUCTIVE_OPS = frozenset({"replace", "delete"})


def _two_key():
    spec = importlib.util.spec_from_file_location("veldo_two_key_floor", ROOT / ".veldo/two_key.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def is_stateful(kind):
    """Whether this kind holds durable data. AN UNCLASSIFIED KIND IS STATEFUL.

    That is not caution for its own sake. The failure mode being prevented is a resource type
    somebody adds next year, forgets to classify, and then deletes in production because the floor
    quietly treated "unknown" as "safe"."""
    if kind in STATELESS_KINDS:
        return False
    return True


def classify(plan):
    """The tier this plan requires, and why. Returns {tier, destroys, stateful, reasons}.

    `reasons` is per resource rather than a summary, because "this plan is critical" sends someone
    hunting and "critical: deleting `orders-db`, a relational_database" does not."""
    destroys, stateful, reasons = [], [], []
    for op in (plan or {}).get("operations", []):
        if op.get("op") not in DESTRUCTIVE_OPS:
            continue
        r = op.get("before") or {}
        kind = r.get("kind")
        name = op.get("name")
        destroys.append(name)
        if is_stateful(kind):
            stateful.append(name)
            known = " (kind %r is not classified, so it counts as stateful)" % kind \
                if kind not in STATEFUL_KINDS else ""
            reasons.append("%s %s, a %s that holds durable data%s: re-applying the declaration "
                           "gives you an empty one" % (op["op"], name, kind, known))
        else:
            reasons.append("%s %s, a stateless %s: recoverable by re-applying the declaration"
                           % (op["op"], name, kind))
    tier = CRITICAL if stateful else (HIGH if destroys else STANDARD)
    return {"tier": tier, "destroys": destroys, "stateful": stateful, "reasons": reasons}


def check(plan, plan_digest, human_authorization=None, independent_confirmation=None,
          now=None, executor_actor=None):
    """May this plan proceed? Returns (ok, reason, detail).

    A standard plan proceeds with no keys. A high or critical plan needs BOTH keys, bound to
    `plan_digest`, and either one missing refuses. The keys themselves are judged by two_key.py -
    this decides only WHICH plans need them."""
    c = classify(plan)
    if c["tier"] == STANDARD:
        return (True, "no_destruction", "nothing in this plan destroys an existing resource", c)
    tk = _two_key()
    # THE SHIPPED GATE, called exactly as the executor calls it. `authorize` returns (reason,
    # detail) with reason None on success, and it is PURE over already-parsed records: it computes
    # no digest, so the caller passes the one truth in. A substrate plan takes the place of the
    # remedy, since both are "the exact thing these two keys agreed to".
    reason, _detail = tk.authorize(
        {"id": "substrate-plan", "status": "proposed"}, plan_digest,
        human_authorization, independent_confirmation,
        executor_actor=executor_actor, now=now)
    if reason is not None:
        return (False, reason,
                "%s change refused: %s. Both keys must be present and bound to this exact plan"
                % (c["tier"], "; ".join(c["reasons"][:3])), c)
    return (True, "two_key_satisfied",
            "%s change authorised by two independent keys bound to this plan" % c["tier"], c)
