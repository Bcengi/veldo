#!/usr/bin/env python3
"""Ephemeral environments: created from a declaration, and provably gone (WARP-1507, W7 of PLAN-0015).

A per-change environment is worth having only if it reliably DISAPPEARS. One that usually tears down
is a slow leak of money and attack surface, and the leak is invisible because nobody looks at an
environment that was supposed to stop existing. So the interesting half of this module is not
create, it is the residue check.

**TEARDOWN IS VERIFIED AGAINST THE PROVIDER'S LEDGER, NOT ASSUMED FROM A RETURN CODE.** `teardown`
asks the provider what it still holds for that environment and reports anything left as RESIDUE. A
destroy call that returned success while leaving a volume behind is the exact failure this catches,
and it is common: deleting a compute instance frequently leaves its disk, and deleting a database
frequently leaves its backups.

**REPRODUCIBLE MEANS IDENTICAL RESULTS, WHICH MEANS THE NAME IS DERIVED.** An environment id is
computed from the change it belongs to, so creating twice for one change yields ONE environment
rather than two, and a retry after a crash adopts what is already there instead of doubling it.
Anything that minted a random id would make "create is idempotent" untestable and leaks the first
attempt.

**REAL PROVISIONING STAYS BEHIND HUMAN-APPROVED WIRING (D5).** The shipped provider is a fake that
keeps a ledger in memory. This module reaches nothing. That is what lets teardown, residue and
idempotence be proven offline, which is the only way anyone would trust them.
"""
import hashlib

SCHEMA = "veldo.ephemeral_env/v1"

CREATED, TORN_DOWN, LEAKED = "created", "torn_down", "leaked"


def environment_id(change_id, prefix="eph"):
    """The environment name for a change. DERIVED, never minted.

    Two creates for one change must give one environment, or a crashed retry silently doubles the
    bill and leaves the first one orphaned with nobody looking for it."""
    h = hashlib.sha256(str(change_id).encode("utf-8")).hexdigest()[:10]
    return "%s-%s" % (prefix, h)


class FakeProvider:
    """The reference provider: a ledger in memory and no network. Every property of this module is
    proven against it, which is the point - a lifecycle whose only tested path needs real
    infrastructure is a lifecycle nobody tests.

    `leaks` names resource kinds this provider fails to remove on teardown, so the residue check can
    be driven against a provider that behaves like real ones do rather than a perfect one."""

    def __init__(self, leaks=()):
        self.ledger = {}
        self._leaks = set(leaks)
        self.calls = []

    def create(self, env, resources):
        self.calls.append(("create", env))
        self.ledger.setdefault(env, [])
        have = {r["name"] for r in self.ledger[env]}
        for r in resources:
            if r.get("name") not in have:
                self.ledger[env].append(dict(r))
        return list(self.ledger[env])

    def destroy(self, env):
        """Remove what it can. Anything whose kind is in `leaks` stays, exactly as a real provider
        leaves a disk behind when the instance it belonged to is deleted."""
        self.calls.append(("destroy", env))
        kept = [r for r in self.ledger.get(env, []) if r.get("kind") in self._leaks]
        self.ledger[env] = kept
        return True                    # a success return that may still have left residue

    def inspect(self, env):
        """What the provider actually still holds. The residue check reads THIS, never the return
        value of destroy."""
        return list(self.ledger.get(env, []))


def create(provider, change_id, declaration):
    """Create the environment for a change, idempotently. Returns the lifecycle record."""
    env = environment_id(change_id)
    before = provider.inspect(env)
    resources = (declaration or {}).get("resources", [])
    after = provider.create(env, resources)
    return {"schema": SCHEMA, "environment": env, "change": change_id, "state": CREATED,
            "resources": len(after), "adopted_existing": bool(before)}


def teardown(provider, change_id):
    """Destroy the environment and VERIFY it is gone against the provider's own ledger.

    Returns a record whose `state` is torn_down only when the ledger is empty. Residue is named
    resource by resource, because "teardown incomplete" tells an operator nothing and "the disk
    `data-vol` is still there" tells them what to go and delete."""
    env = environment_id(change_id)
    provider.destroy(env)
    residue = provider.inspect(env)
    return {
        "schema": SCHEMA, "environment": env, "change": change_id,
        "state": TORN_DOWN if not residue else LEAKED,
        "residue": [{"name": r.get("name"), "kind": r.get("kind")} for r in residue],
        "detail": "gone" if not residue else
                  "destroy returned success but the provider still holds %d resource(s): %s. A "
                  "success code is not a teardown"
                  % (len(residue), ", ".join("%s (%s)" % (r.get("name"), r.get("kind"))
                                             for r in residue)),
    }


def lifecycle_events(record):
    """The event-stream entries for one lifecycle record, so an environment that leaked is visible
    in the same log as everything else rather than only in whoever ran the teardown's terminal."""
    base = {"environment": record["environment"], "correlation_id": record.get("change")}
    if record["state"] == CREATED:
        return [dict(base, type="run.started", detail="ephemeral environment created")]
    if record["state"] == TORN_DOWN:
        return [dict(base, type="run.done", detail="ephemeral environment torn down, no residue")]
    return [dict(base, type="run.blocked",
                 detail="ephemeral environment LEAKED: %d resource(s) survived teardown"
                        % len(record["residue"]))]
