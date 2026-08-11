#!/usr/bin/env python3
"""Per-agent, per-task credentials (WARP-1304, W4 of PLAN-0013).

A credential is issued FOR one task, scoped to what that task declared it needs, expiring on its
own, and attributable to the agent that used it. Never an organization-wide key handed round.

**SCOPE IS DERIVED FROM THE TASK, NOT REQUESTED BY THE AGENT.** That inversion is the whole design.
If an agent asks for scopes, it will ask for the ones that make its work succeed, and the honest
failure mode is not malice: it is an agent that hits a permission error, widens the request, and
succeeds. Asking is how least privilege dies. So `issue()` takes the task's DECLARED needs and a
requested scope, and refuses anything the declaration does not already cover. The declaration is
written when the work is specified, by someone thinking about the work rather than about getting
unblocked.

**EXPIRY IS ENFORCED AT USE, NOT ONLY AT ISSUE.** A credential checked only when handed out is a
credential that works forever in practice, because the check happens at the moment nobody is
worried. `authorize_use()` re-checks, and that is where the refusal actually lands.

**ATTRIBUTION IS PART OF THE CREDENTIAL, NOT A LOG LINE BESIDE IT.** Agent and task are fields of
the record, so an audit answers "who did this" from the credential itself rather than from
correlating timestamps across two systems at three in the morning.

**FAKE ISSUER ONLY.** This module mints no real token and reaches nothing; `Issuer` is the seam. A
real one is wired per system, deliberately, by a person.
"""
import hashlib

SCHEMA = "veldo.credential/v1"

# Every refusal, named. A credential system that says "denied" teaches people to route around it.
OVER_BROAD = "scope_exceeds_task_declaration"
NO_TASK_SCOPE = "task_declares_no_scope"
NO_TASK = "no_task"
NO_AGENT = "no_agent"
EXPIRED = "credential_expired"
ORG_WIDE = "organization_wide_scope_refused"
UNKNOWN_SCOPE = "unknown_scope"

# Scopes that are never issuable to an agent no matter what a task declares. A task declaration is
# written by a person, and a person in a hurry can write `*`. This is the floor under that.
NEVER_ISSUABLE = frozenset({"*", "admin", "owner", "root", "org:admin", "billing"})


class CredentialError(RuntimeError):
    """Raised on refusal. Carries the reason and the scopes, never a secret."""

    def __init__(self, reason, detail):
        super().__init__("%s: %s" % (reason, detail))
        self.reason = reason


class FakeIssuer:
    """The reference issuer: derives an opaque handle from the request and records what it issued.
    Mints nothing real, so every property here is proven offline."""

    def __init__(self):
        self.issued = []

    def mint(self, agent, task, scopes, expires_at):
        self.issued.append({"agent": agent, "task": task, "scopes": sorted(scopes),
                            "expires_at": expires_at})
        seed = "|".join([agent, task, ",".join(sorted(scopes)), expires_at])
        return "fake-" + hashlib.sha256(seed.encode()).hexdigest()[:16]


class Credential:
    """An issued credential. The token is opaque and never rendered.

    `__repr__` shows agent, task and scopes - the things an audit needs - and never the token,
    for the same reason `SecretHandle` does not render its value: the commonest way a credential
    reaches a log is an object being printed."""

    __slots__ = ("_token", "agent", "task", "scopes", "expires_at")

    def __init__(self, token, agent, task, scopes, expires_at):
        self._token, self.agent, self.task = token, agent, task
        self.scopes, self.expires_at = tuple(sorted(scopes)), expires_at

    def reveal(self):
        return self._token

    def __repr__(self):
        return "<Credential agent=%s task=%s scopes=%s expires=%s>" % (
            self.agent, self.task, ",".join(self.scopes), self.expires_at)

    __str__ = __repr__


def issue(issuer, agent, task, task_declares, requested, expires_at, now=None):
    """Issue a credential for ONE task, scoped no wider than the task declared.

    `task_declares` is the scope set written when the work was specified. `requested` is what the
    caller wants now. Anything in `requested` outside `task_declares` REFUSES - the agent cannot
    widen its own reach by asking, which is the failure mode least privilege actually dies of."""
    if not (isinstance(agent, str) and agent.strip()):
        raise CredentialError(NO_AGENT, "a credential must be attributable to an agent")
    if not (isinstance(task, str) and task.strip()):
        raise CredentialError(NO_TASK, "a credential is issued FOR a task; there is no general one")
    declared = set(task_declares or ())
    if not declared:
        raise CredentialError(NO_TASK_SCOPE,
                              "task %s declares no scope, so there is nothing to derive a "
                              "credential from. Declare what the work needs when you specify it, "
                              "not when it fails" % task)
    banned = sorted(declared & NEVER_ISSUABLE)
    if banned:
        raise CredentialError(ORG_WIDE,
                              "task %s declares %s, which is never issuable to an agent whatever a "
                              "declaration says. A person in a hurry can write '*'; this is the "
                              "floor under that" % (task, banned))
    want = set(requested or declared)
    excess = sorted(want - declared)
    if excess:
        raise CredentialError(OVER_BROAD,
                              "task %s declared %s and the request adds %s. Scope is DERIVED from "
                              "the task, never asked for: an agent that widens its request until "
                              "the work succeeds is how least privilege dies"
                              % (task, sorted(declared), excess))
    if now is not None and now >= expires_at:
        raise CredentialError(EXPIRED, "refusing to issue an already-expired credential")
    return Credential(issuer.mint(agent, task, want, expires_at), agent, task, want, expires_at)


def authorize_use(cred, scope, now, task=None):
    """May this credential be used for this scope, right now? Returns (ok, reason).

    EXPIRY IS CHECKED HERE, not only at issue. A credential validated only when handed out works
    forever in practice, because the check happens at the moment nobody is worried."""
    if not isinstance(cred, Credential):
        return (False, NO_AGENT)
    if now >= cred.expires_at:
        return (False, EXPIRED)
    if scope not in cred.scopes:
        return (False, UNKNOWN_SCOPE)
    if task is not None and task != cred.task:
        return (False, NO_TASK)
    return (True, "authorized")


def audit_record(cred, action, now):
    """The attribution line. Agent, task, scopes and action come off the credential itself, so
    "who did this" is answerable without correlating two systems by timestamp."""
    return {"schema": SCHEMA, "agent": cred.agent, "task": cred.task,
            "scopes": list(cred.scopes), "action": action, "at": now}
