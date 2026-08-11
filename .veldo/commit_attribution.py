#!/usr/bin/env python3
"""Signed, attributable commits (WARP-1308, W8 of PLAN-0013).

Every commit says which actor produced it, and a signature by a key the REPOSITORY declares is what
turns that claim into evidence.

**A TRAILER ALONE IS A CLAIM, NOT ATTRIBUTION.** `Veldo-Agent: builder-3` is a line of text anybody
can type, including the agent that wants to be somebody else. The trailer says who; the signature is
the only part that says the who is true. So this module never treats an attribution trailer as
evidence on its own, and the refusal for a signed-but-unattributed commit is different from the one
for an attributed-but-unsigned commit, because they are different failures.

**GIT'S "GOOD SIGNATURE" IS NOT A TRUST DECISION AND MUST NOT BE READ AS ONE.** `git verify-commit`
reports G for a signature made by any key the LOCAL KEYRING happens to hold. A local keyring is a
file in the environment the agent is running in. An attacker who can write a commit can usually also
add a key, at which point every commit they make verifies beautifully. So the check here pins the
signing FINGERPRINT against a registry declared in the repository, and a good signature from an
unregistered key REFUSES with its own reason. This is the WARP-0730 lesson in a second place: the
predicate has to live somewhere the thing being checked cannot reach.

**FAIL CLOSED ON UNKNOWN, NOT OPEN.** Git reports several verification states and new ones have been
added over time. Anything that is not an explicitly recognised good state refuses, so a state this
module has never heard of cannot be the one that lets a commit through.

**CONFIGURABLE, ON FROM FIRST RELEASE (D3).** The machinery ships either way; `Policy` carries the
switch. With enforcement off the checks still RUN and still report, they simply do not refuse -
because a check that is turned off entirely goes stale, and the day somebody turns it on they get a
wall of findings and turn it back off.

**THIS MODULE SIGNS NOTHING.** Signing is git's job and the key material is the operator's. What
lives here is verification and policy over PARSED commit records; the caller runs git.
"""

SCHEMA = "veldo.commit_attribution/v1"

# The trailer convention. Named constants because two spellings of a trailer key is how attribution
# silently stops matching anything.
AGENT_TRAILER = "Veldo-Agent"
TASK_TRAILER = "Veldo-Task"
MODEL_TRAILER = "Veldo-Model"

# Git's verification states, split into the ones that mean something and the ones that do not. Only
# GOOD is a pass; everything else, INCLUDING A STATE NOT LISTED HERE, refuses.
GOOD = "G"                    # good signature
STATES = {
    "G": "good signature",
    "U": "good signature with unknown validity",
    "X": "good signature that has expired",
    "Y": "good signature made by an expired key",
    "R": "good signature made by a revoked key",
    "B": "BAD signature",
    "E": "signature could not be checked (missing key)",
    "N": "no signature",
}

# Refusals, each named. "Commit policy violation" tells a person nothing they can act on.
UNSIGNED = "commit_unsigned"
BAD_SIGNATURE = "commit_signature_bad"
UNVERIFIABLE = "commit_signature_unverifiable"
UNREGISTERED_KEY = "signing_key_not_in_registry"
UNATTRIBUTED = "commit_names_no_actor"
UNKNOWN_ACTOR = "actor_not_in_registry"
ACTOR_MISMATCH = "actor_does_not_own_signing_key"
TASK_MISSING = "commit_names_no_task"
EXPECTED_MISMATCH = "actor_is_not_the_one_that_ran"


class Registry:
    """Who may sign, and with which keys. DECLARED IN THE REPOSITORY, which is the whole point.

    A registry stored where the signer can edit it is a registry the signer can add themselves to.
    This object is built from a repo file that the protected-path rules cover, so changing it is a
    reviewed change rather than a step in an attack."""

    def __init__(self, actors=None):
        # {actor: frozenset(fingerprints)}. Fingerprints are compared case-insensitively and with
        # separators stripped, because the same key is spelled four ways by four tools.
        self.actors = {a: frozenset(_norm(f) for f in fps)
                       for a, fps in (actors or {}).items()}

    def owner_of(self, fingerprint):
        fp = _norm(fingerprint)
        for actor, fps in sorted(self.actors.items()):
            if fp in fps:
                return actor
        return None

    def knows(self, actor):
        return actor in self.actors


class Policy:
    """The configurable switch (D3). Enforcement is ON from first release.

    With enforcement off the checks STILL RUN and still report; they just do not refuse. A check
    that is switched off entirely rots, and the day somebody enables it they meet a wall of findings
    and switch it back off."""

    def __init__(self, enforce=True, require_task=True, require_signature=True):
        self.enforce = bool(enforce)
        self.require_task = bool(require_task)
        self.require_signature = bool(require_signature)


def _norm(fp):
    return "".join(str(fp or "").split()).replace(":", "").lower()


def trailers(message):
    """The trailer block of a commit message, as a mapping.

    Only trailers in the LAST paragraph count, which is what git itself means by a trailer. A
    `Veldo-Agent:` line in the middle of a body is prose somebody quoted, and treating it as
    attribution would let a commit be attributed by quoting an earlier one."""
    out = {}
    para = (message or "").rstrip().split("\n\n")[-1]
    for line in para.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            if k.strip() and " " not in k.strip():
                out[k.strip()] = v.strip()
    return out


def format_trailers(actor, task, model=None):
    """The convention, produced in one place so it is spelled one way."""
    lines = ["%s: %s" % (AGENT_TRAILER, actor), "%s: %s" % (TASK_TRAILER, task)]
    if model:
        lines.append("%s: %s" % (MODEL_TRAILER, model))
    return "\n".join(lines)


def check_commit(commit, registry, policy=None, expected_actor=None):
    """Every signing and attribution problem with ONE parsed commit, as (reason, detail).

    `commit` carries `sha`, `message`, `signature_state` (git's %G? letter) and `key_fingerprint`
    (git's %GF). The caller runs git; this decides. Returns findings whether or not enforcement is
    on - `refuses()` is what turns findings into a refusal."""
    pol = policy or Policy()
    c = commit or {}
    out = []
    state = c.get("signature_state")
    fp = c.get("key_fingerprint")
    tr = trailers(c.get("message"))
    actor = tr.get(AGENT_TRAILER)

    if pol.require_signature:
        if state in (None, "", "N"):
            out.append((UNSIGNED, "commit %s carries no signature, so its attribution is a claim "
                                  "anybody could have typed" % c.get("sha", "?")))
        elif state == "B":
            out.append((BAD_SIGNATURE, "signature does not verify: the commit was altered after "
                                       "signing, or was never signed by the key it names"))
        elif state != GOOD:
            out.append((UNVERIFIABLE,
                        "signature state %r (%s) is not a good signature. Anything that is not an "
                        "explicitly recognised good state refuses, so a state this check has never "
                        "heard of cannot be the one that lets a commit through"
                        % (state, STATES.get(state, "unrecognised state"))))
        else:
            # THE POINT OF THE WHOLE MODULE. Git said good; git says good for any key in the local
            # keyring, and the keyring is a file in the environment the agent runs in.
            owner = registry.owner_of(fp)
            if owner is None:
                out.append((UNREGISTERED_KEY,
                            "signature is good but key %s is in NO declared signer registry. Git "
                            "reports a good signature for any key the local keyring holds, and an "
                            "attacker who can write a commit can usually add a key" % (fp or "?")))
            elif actor and owner != actor:
                out.append((ACTOR_MISMATCH,
                            "the commit claims %s but the signing key belongs to %s. The trailer "
                            "says who; the signature is the part that says the who is true"
                            % (actor, owner)))

    if not actor:
        out.append((UNATTRIBUTED,
                    "no %s trailer: the fleet's work is only auditable end to end if each commit "
                    "names the actor that produced it" % AGENT_TRAILER))
    elif not registry.knows(actor):
        out.append((UNKNOWN_ACTOR, "actor %r appears in no signer registry" % actor))
    elif expected_actor is not None and actor != expected_actor:
        out.append((EXPECTED_MISMATCH,
                    "commit names %s but the run that produced it was bound to %s"
                    % (actor, expected_actor)))

    if pol.require_task and not tr.get(TASK_TRAILER):
        out.append((TASK_MISSING, "no %s trailer: a change nobody can tie to a unit of work is a "
                                  "change nobody can review the reason for" % TASK_TRAILER))
    return out


def check_range(commits, registry, policy=None):
    """Findings across a push range, as (sha, reason, detail). Every commit is checked.

    NOT just the tip: a range is merged as a unit, and an unsigned commit three back is merged just
    as thoroughly as the one on top."""
    return [(c.get("sha", "?"), r, d)
            for c in (commits or [])
            for r, d in check_commit(c, registry, policy)]


def refuses(findings, policy=None):
    """Whether these findings BLOCK. Separated from finding them on purpose: with enforcement off
    the checks still run and still report, so the day somebody turns enforcement on they are not
    met by a wall of findings that makes them turn it straight back off."""
    return bool(findings) and (policy or Policy()).enforce


def report(findings, policy=None):
    pol = policy or Policy()
    if not findings:
        return ["commit attribution: no problems"]
    head = "commit attribution: %d problem(s)%s" % (
        len(findings), "" if pol.enforce else " (enforcement OFF: reporting, not refusing)")
    return [head] + ["  %s %-32s %s" % (s[:8], r, d) for s, r, d in findings]
