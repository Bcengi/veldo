#!/usr/bin/env python3
"""The infrastructure change type: plan, then apply (WARP-1502, W2 of PLAN-0015).

A DECLARATION DIFF IS AN ORDINARY CHANGE THROUGH THE ORDINARY LOOP. What makes infrastructure
different is not the process, it is that the effect happens somewhere the repository cannot see, and
that some effects cannot be undone. So the loop gains exactly two mechanics and nothing else:

**PLAN THEN APPLY, ALWAYS SEPARATE.** `plan()` compares two declarations and returns the operations
that would reconcile them. It reaches nothing and changes nothing. `apply()` executes a plan that
was computed earlier, against an adapter, and refuses if the world moved underneath it. Every
infrastructure tool worth using has this separation, and the reason is that a human has to be able
to read what will happen before it happens.

**THE PLAN IS BOUND TO WHAT IT WAS COMPUTED FROM.** An apply carries the digest of the from-state and
the to-state it planned against, and refuses if either has changed. A plan computed against a world
that has since moved is not a plan, it is a guess with a formatting convention, and applying one is
how infrastructure tools destroy things nobody asked them to touch.

**ADOPTION-SAFE BY CONSTRUCTION.** A repository with no substrate declarations never calls any of
this, and nothing here runs at gate time. Adopting the method does not opt a repository into
infrastructure management: an empty declaration set produces an empty plan, and an empty plan is a
no-op rather than an error.

**THE EXECUTION SEAM IS PLUGGABLE AND THE REFERENCE IS FAKE.** `Adapter` is the interface; the
shipped implementation is `FakeAdapter`, which records what it was asked to do and does nothing.
Everything in this module is therefore provable offline, and a real adapter is something an operator
wires deliberately - the same shape as the action executor's target system, and for the same reason:
a module that can reach production in its default configuration is one nobody can safely test.
"""
import hashlib
import json

SCHEMA = "veldo.substrate_plan/v1"

# THE OPERATION VOCABULARY. Ordered by how hard they are to undo, and that order is load-bearing:
# W4's destructive floor keys off it, and `irreversible_ops` below is what a risk classifier reads.
CREATE, UPDATE, REPLACE, DELETE = "create", "update", "replace", "delete"
OPERATIONS = (CREATE, UPDATE, REPLACE, DELETE)

# REPLACE and DELETE destroy a resource that exists. UPDATE mutates one in place and CREATE makes a
# new one, and neither loses anything that was there. Declared once so the classifier and the plan
# formatter cannot disagree about which operations deserve fear.
DESTRUCTIVE = frozenset({REPLACE, DELETE})

# Changing one of these on an existing resource cannot be done in place: the resource is destroyed
# and recreated. Getting this list wrong in the permissive direction means an "update" that silently
# deletes something, so it fails toward REPLACE rather than toward UPDATE.
REPLACE_TRIGGERS = ("kind", "name")


def digest(value):
    """A stable digest of a declaration or a fragment. Sorted keys, no whitespace, so two spellings
    of one declaration bind identically and two different ones never collide."""
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def _by_name(decl):
    return {r["name"]: r for r in (decl or {}).get("resources", []) if isinstance(r, dict)
            and isinstance(r.get("name"), str)}


def plan(from_decl, to_decl):
    """The operations that would reconcile `from_decl` into `to_decl`. PURE: reaches nothing,
    changes nothing, and given the same pair returns the same plan every time.

    An empty diff is an empty plan and that is a SUCCESS, not an error - which is what makes a
    repository with no substrate declarations safe: it plans nothing and applies nothing."""
    a, b = _by_name(from_decl), _by_name(to_decl)
    ops = []
    for name in sorted(set(a) | set(b)):
        before, after = a.get(name), b.get(name)
        if before is None:
            ops.append({"op": CREATE, "name": name, "after": after})
        elif after is None:
            ops.append({"op": DELETE, "name": name, "before": before})
        elif before != after:
            trigger = next((k for k in REPLACE_TRIGGERS if before.get(k) != after.get(k)), None)
            if trigger:
                ops.append({"op": REPLACE, "name": name, "before": before, "after": after,
                            "because": "%s changed, which cannot be done in place" % trigger})
            else:
                ops.append({"op": UPDATE, "name": name, "before": before, "after": after})
    return {
        "schema": SCHEMA,
        "from_digest": digest(from_decl),
        "to_digest": digest(to_decl),
        "operations": ops,
        "destructive": sorted({o["name"] for o in ops if o["op"] in DESTRUCTIVE}),
    }


def irreversible_ops(p):
    """The operations in a plan that destroy something that exists. What a risk classifier reads,
    and what W4's destructive floor will key off; kept here so there is ONE answer to which
    operations deserve fear."""
    return [o for o in (p or {}).get("operations", []) if o.get("op") in DESTRUCTIVE]


def summarise(p):
    """One human-readable line per operation, for the proof. The PLANNED EFFECT goes into the proof
    bundle so a reviewer reads what will happen rather than being told that something will."""
    out = []
    for o in (p or {}).get("operations", []):
        line = "%-7s %s" % (o["op"], o["name"])
        if o.get("because"):
            line += "  (%s)" % o["because"]
        out.append(line)
    return out


class Adapter:
    """The execution seam. A real adapter talks to a cloud, a cluster or a config system; this
    interface is all `apply` knows about, so the module is testable offline and a real adapter is
    something an operator wires deliberately rather than something that ships switched on."""

    def execute(self, operation):                       # pragma: no cover - interface
        raise NotImplementedError

    def observe(self):                                  # pragma: no cover - interface
        """The declaration the adapter believes is currently live, or None if it cannot say."""
        return None


class FakeAdapter(Adapter):
    """The reference implementation: records what it was asked to do and does nothing. Every
    property of this module is proven against it, which is the point - a module whose only tested
    path requires real infrastructure is a module nobody tests."""

    def __init__(self, observed=None, fail_on=()):
        self.calls = []
        self._observed = observed
        self._fail_on = set(fail_on)

    def execute(self, operation):
        self.calls.append(operation)
        if operation.get("name") in self._fail_on:
            raise RuntimeError("adapter refused %s on %s" % (operation.get("op"),
                                                             operation.get("name")))
        return {"op": operation.get("op"), "name": operation.get("name"), "applied": True}

    def observe(self):
        return self._observed


def apply(p, adapter, from_decl=None, to_decl=None):
    """Execute a plan computed EARLIER, refusing if the world moved underneath it.

    THE STALENESS CHECK IS THE WHOLE SAFETY PROPERTY. A plan carries the digests of the two
    declarations it was computed from; if either no longer matches, the plan describes a world that
    no longer exists and applying it is how infrastructure tools destroy things nobody asked them
    to touch. Re-plan instead.

    Stops at the FIRST failure and reports what had already been applied, because an adapter that
    failed once is an adapter whose next call is not trustworthy, and a caller needs to know exactly
    how far it got - a partial apply that lies about its extent is worse than one that fails."""
    if not isinstance(p, dict) or p.get("schema") != SCHEMA:
        return {"applied": False, "refused": "not_a_plan",
                "detail": "apply takes a plan produced by plan(); got %r" % type(p).__name__}
    if from_decl is not None and digest(from_decl) != p.get("from_digest"):
        return {"applied": False, "refused": "stale_plan",
                "detail": "the from-state changed since this plan was computed: it describes a "
                          "world that no longer exists, so re-plan rather than apply"}
    if to_decl is not None and digest(to_decl) != p.get("to_digest"):
        return {"applied": False, "refused": "stale_plan",
                "detail": "the to-state changed since this plan was computed: what would be applied "
                          "is not what was reviewed, so re-plan rather than apply"}
    done = []
    for op in p.get("operations", []):
        try:
            done.append(adapter.execute(op))
        except Exception as e:
            return {"applied": False, "refused": "adapter_failed",
                    "detail": "%s: %s" % (type(e).__name__, e),
                    "completed": done, "failed_on": op.get("name")}
    return {"applied": True, "operations": len(done), "completed": done}
