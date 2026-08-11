#!/usr/bin/env python3
"""Execution binding for risky actions (WARP-0621, W8 of PLAN-0016).

THE PROBLEM THIS EXISTS FOR. The two-key rule (W7) proves that two humans authorised SOMETHING.
It does not prove they authorised THIS execution, HERE, NOW, ONCE. A key bound only to a proposal
digest still admits four moves that nobody approved: run it against a different system, run it in
a different environment, run it after the world it was reasoned about has changed, and run it
again tomorrow. Each of those is the same bytes doing a different thing.

So an authorisation for a risky action binds SIX facts, and the executor re-checks every one of
them at the moment of execution rather than at the moment of issue:

  target        the action id it authorises, and nothing else
  system        the system it runs against
  environment   the environment it runs in
  parameters    the EXACT parameter values, canonically serialised
  state_digest  a digest of the world the approver reasoned about
  expiry        after which it is simply gone

plus a NONCE, consumed exactly once, which is what makes the authorisation an event rather than a
standing permission.

WHY RE-CHECK RATHER THAN TRUST THE ISSUE-TIME CHECK. Everything above can change between issue and
execution, and the gap is exactly where an incident lives: the approver looked at a system that was
degraded in one way, and by the time the key is turned it is degraded in another. Checking at issue
time proves what was true then. This module answers "is it still true".

CONSUMPTION IS ATOMIC AND IS THE ONLY PART THAT TOUCHES DISK. `os.open` with O_CREAT|O_EXCL is the
primitive: on POSIX exactly one caller creates the file and every later caller gets FileExistsError,
which is the at-most-once guarantee without a lock, a daemon or a database. Consumption happens
BEFORE the action runs, never after, so a process that dies mid-action cannot leave a nonce that
replays - the failure mode is a risky action that ran at most once and may need re-authorising,
which is the correct direction to fail.

WHAT THIS IS NOT. It is not a forgery defense, for the reason WARP-0730 settled: an agent that can
write the repository can write a binding record. What it buys is that an HONEST execution cannot
drift from what was approved, and that a replay needs an affirmative act (deleting a consumed-nonce
file) rather than merely doing nothing. Same shape as WARP-0732's asymmetry, and stated here so a
later reader does not upgrade the claim.
"""
import hashlib
import json
import os
import re

SCHEMA = "veldo.execution_binding/v1"

# Every refusal this module can produce, NAMED, because a guard that refuses without saying which
# fact failed sends an operator to read code during an incident.
BINDING_ABSENT = "binding_absent"
BINDING_MALFORMED = "binding_malformed"
BINDING_EXPIRED = "binding_expired"
BINDING_REVOKED = "binding_revoked"
BINDING_REPLAYED = "binding_replayed"
BINDING_TARGET_MISMATCH = "binding_target_mismatch"
BINDING_SYSTEM_MISMATCH = "binding_system_mismatch"
BINDING_ENVIRONMENT_MISMATCH = "binding_environment_mismatch"
BINDING_PARAMETERS_CHANGED = "binding_parameters_changed"
BINDING_STATE_CHANGED = "binding_state_changed"
BINDING_PROPOSAL_CHANGED = "binding_proposal_changed"
BINDING_OK = "binding_ok"

REFUSALS = frozenset({
    BINDING_ABSENT, BINDING_MALFORMED, BINDING_EXPIRED, BINDING_REVOKED, BINDING_REPLAYED,
    BINDING_TARGET_MISMATCH, BINDING_SYSTEM_MISMATCH, BINDING_ENVIRONMENT_MISMATCH,
    BINDING_PARAMETERS_CHANGED, BINDING_STATE_CHANGED, BINDING_PROPOSAL_CHANGED,
})

# THE SIX BOUND FACTS, declared once so the checker, the issuer and the selftest cannot disagree
# about what "bound" means. A seventh added here without a check below is caught by the selftest.
BOUND_FACTS = ("target", "system", "environment", "parameters", "state_digest", "proposal_digest")

_NONCE_RE = re.compile(r"\A[a-f0-9]{16,64}\Z")


def canonical(value):
    """The one serialisation of a bound fact, so two spellings of the same parameters are the same
    binding and two different parameter sets never collide. Sorted keys, no whitespace, and a
    refusal to serialise anything json cannot represent (a parameter that is not data is not a
    parameter). Used for BOTH issue and check, which is what makes them comparable at all."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=None)


def digest_of(value):
    """A stable digest of any bound fact. Hex, so it survives a round trip through a text record."""
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def _iso(v):
    return isinstance(v, str) and bool(re.match(r"\A\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z", v))


def validate(binding):
    """Every structural problem with a binding record, as a list of strings. Empty means well
    formed, which is NOT the same as applicable - `check` decides that. Split in two on purpose:
    a malformed record and an inapplicable one are different operator problems."""
    p = []
    if not isinstance(binding, dict):
        return ["a binding must be a mapping; got %s" % type(binding).__name__]
    if binding.get("schema") != SCHEMA:
        p.append("schema must be %r, got %r" % (SCHEMA, binding.get("schema")))
    n = binding.get("nonce")
    if not (isinstance(n, str) and _NONCE_RE.match(n)):
        p.append("nonce must be 16 to 64 lowercase hex characters, got %r" % (n,))
    if not _iso(binding.get("expires_at")):
        p.append("expires_at must be YYYY-MM-DDTHH:MM:SSZ, got %r" % (binding.get("expires_at"),))
    scope = binding.get("scope")
    if not isinstance(scope, dict):
        p.append("scope must be a mapping of the bound facts, got %s" % type(scope).__name__)
    else:
        for f in BOUND_FACTS:
            if f not in scope:
                p.append("scope is missing the bound fact %r: an unbound fact is an unapproved fact" % f)
    if binding.get("revoked") not in (None, False, True):
        p.append("revoked must be absent, true or false, got %r" % (binding.get("revoked"),))
    return p


def issue(nonce, expires_at, target, system, environment, parameters,
          state_digest, proposal_digest, issued_by=None, issued_at=None):
    """One binding record. The caller supplies the nonce and the clock: this module mints neither,
    so it stays a pure function and the selftest can drive it deterministically."""
    return {
        "schema": SCHEMA,
        "nonce": nonce,
        "expires_at": expires_at,
        "issued_by": issued_by,
        "issued_at": issued_at,
        "revoked": False,
        "scope": {
            "target": target,
            "system": system,
            "environment": environment,
            "parameters": digest_of(parameters),
            "state_digest": state_digest,
            "proposal_digest": proposal_digest,
        },
    }


def check(binding, target, system, environment, parameters,
          state_digest, proposal_digest, now, consumed=None):
    """Is this binding still good for THIS execution, right now? Returns (reason, detail).
    `reason` is BINDING_OK or one of REFUSALS, never an exception, because an executor guard that
    raises turns a refusal into a crash.

    ORDER IS DELIBERATE: structure, then existence-class problems (revoked, expired, replayed),
    then the six facts. An operator reading the first refusal should get the most fundamental
    reason, not an incidental one.

    `consumed` is an optional membership test for already-spent nonces, so a caller can answer the
    replay question from wherever it keeps them. Passing None does not skip the check silently: it
    means the caller has no store, and `consume` is then the only replay defense."""
    problems = validate(binding)
    if problems:
        return (BINDING_MALFORMED, "; ".join(problems))
    if binding.get("revoked") is True:
        return (BINDING_REVOKED, "this authorisation was revoked; a revocation forces a new one")
    if not _iso(now):
        return (BINDING_MALFORMED, "the current time must be YYYY-MM-DDTHH:MM:SSZ, got %r" % (now,))
    if now >= binding["expires_at"]:                       # ISO-Z sorts lexicographically
        return (BINDING_EXPIRED,
                "expired at %s and it is now %s: an authorisation is a moment, not a standing "
                "permission" % (binding["expires_at"], now))
    if consumed is not None and binding["nonce"] in consumed:
        return (BINDING_REPLAYED,
                "nonce %s was already consumed: a risky action executes at most once per "
                "authorisation" % binding["nonce"])
    sc = binding["scope"]
    for fact, actual, reason in (
            ("target", target, BINDING_TARGET_MISMATCH),
            ("system", system, BINDING_SYSTEM_MISMATCH),
            ("environment", environment, BINDING_ENVIRONMENT_MISMATCH),
            ("parameters", digest_of(parameters), BINDING_PARAMETERS_CHANGED),
            ("state_digest", state_digest, BINDING_STATE_CHANGED),
            ("proposal_digest", proposal_digest, BINDING_PROPOSAL_CHANGED),
    ):
        if sc.get(fact) != actual:
            return (reason,
                    "%s was authorised as %r and is %r at execution: what changed was not "
                    "approved, so a new authorisation is required" % (fact, sc.get(fact), actual))
    return (BINDING_OK, "")


def consume(store_dir, nonce):
    """Spend a nonce, ATOMICALLY, returning True if this caller spent it and False if it was
    already spent. O_CREAT|O_EXCL is the whole mechanism: the kernel guarantees exactly one
    creator, so two executors racing the same authorisation cannot both proceed, with no lock
    file, no daemon and no second store to keep consistent.

    CALL THIS BEFORE THE ACTION RUNS. Consuming after a successful run would let a process that
    dies mid-action leave a replayable nonce behind, and a risky action that runs twice is worse
    than one that needs re-authorising."""
    if not (isinstance(nonce, str) and _NONCE_RE.match(nonce)):
        raise ValueError("refusing to consume a malformed nonce: %r" % (nonce,))
    os.makedirs(store_dir, exist_ok=True)
    path = os.path.join(store_dir, nonce)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        return False
    with os.fdopen(fd, "w") as fh:
        fh.write(SCHEMA + "\n")
    return True


def spent(store_dir):
    """Every nonce already consumed, as a set, for callers that want to pass `consumed` to check
    and get a NAMED replay refusal instead of a bare False out of consume."""
    try:
        return set(os.listdir(store_dir))
    except (FileNotFoundError, NotADirectoryError):
        return set()
