#!/usr/bin/env python3
"""Substrate declarations and their validator (WARP-1501, W1 of PLAN-0015).

THE REPOSITORY BECOMES THE SOURCE OF TRUTH FOR WHAT SHOULD BE RUNNING. An environment and the
resources in it are declared here, in a versioned record, and a change to that record is an
ordinary spec through the ordinary loop: specified, proven, gated, merged. No console clicks, no
drift between what someone remembers provisioning and what is actually there.

WHAT A DECLARATION IS. One environment, its resources, their kinds and versions, the relationships
between them, and the per-environment parameters that differ. Nothing else, and specifically not
any value that could be a credential.

***

THREE RULES THAT ARE THE WHOLE CONTRACT, each of which fails CLOSED:

**1. UNKNOWN KINDS ARE REJECTED AT CONTRACT TIME.** A resource kind this repository does not
declare is not a resource, it is a typo or an invention, and admitting it would mean the validator
silently passes things nothing downstream can act on. The kind vocabulary is declared ONCE, in
`RESOURCE_KINDS`, and adding to it is a deliberate contract change rather than a string appearing
in a file somewhere.

**2. SECRETS ARE REFERENCES, NEVER VALUES (C5).** A parameter may name a secret; it may never hold
one. The check is deliberately blunt and slightly over-eager: anything that looks like a literal
credential is refused, and the fix is always to replace it with a reference rather than to add an
exemption. That asymmetry is the point. A false positive costs a minute of reshaping; a false
negative puts a credential in git history where it lives forever.

**3. RELATIONSHIPS MUST RESOLVE.** A resource that depends on a name no resource in the environment
declares is a broken declaration, and finding that at contract time is the difference between a
failed validation and a half-provisioned environment at three in the morning.

WHAT THIS MODULE DOES NOT DO. It provisions nothing, reaches no network, holds no credential and
runs no process. It reads a declaration and reports what is wrong with it. Provisioning against a
declaration is W7's ephemeral-environment seam and the drift comparison is W6; both are separate
items on purpose, because a validator that can also act is a validator you cannot safely run.
"""
import re

SCHEMA = "veldo.substrate/v1"

# THE KIND VOCABULARY, declared ONCE. An unknown kind is refused rather than passed through: the
# alternative is a declaration that validates and then means nothing to anything downstream.
RESOURCE_KINDS = frozenset({
    "compute", "container_service", "serverless_function", "static_site",
    "relational_database", "document_database", "cache", "object_store",
    "queue", "topic", "scheduler",
    "load_balancer", "dns_record", "certificate", "network", "firewall_rule",
    "secret_reference", "identity", "role_binding",
    "observability_sink", "log_group", "dashboard", "alert_rule",
})

# Environments are ordered: a promotion pipeline (W5) needs to know which way is forward. Declared
# here so the pipeline and the validator cannot disagree about what "later" means.
ENVIRONMENT_ORDER = ("ephemeral", "development", "staging", "production")

REQUIRED_TOP = ("schema", "environment", "version", "resources")
REQUIRED_RESOURCE = ("name", "kind")

# A parameter value that looks like a literal credential. Deliberately over-eager: see rule 2.
_SECRET_SHAPES = (
    (re.compile(r"\A[A-Za-z0-9+/]{40,}={0,2}\Z"), "a long base64-like literal"),
    (re.compile(r"\A[a-f0-9]{32,}\Z", re.I), "a long hex literal"),
    (re.compile(r"\A(sk|pk|ghp|gho|xox[baprs]|AKIA|ASIA)[-_A-Za-z0-9]{8,}", re.I),
     "a known credential prefix"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "an inline private key"),
)
# Names that say "this holds a secret". A value under one of these must be a reference.
_SECRET_NAMES = re.compile(
    r"(password|passwd|secret|token|api[_-]?key|apikey|private[_-]?key|credential|"
    r"access[_-]?key|client[_-]?secret|connection[_-]?string)", re.I)

# What a reference looks like: a pointer into a managed store, resolved at use time.
_REFERENCE = re.compile(r"\A(ref|secret|env|vault|ssm|kms|sops):[A-Za-z0-9_./\-]+\Z")


def is_reference(value):
    """A parameter value that POINTS at a secret rather than holding one."""
    return isinstance(value, str) and bool(_REFERENCE.match(value))


def secret_problem(key, value):
    """Why this parameter is a literal secret, or None. Two independent tests, because each catches
    what the other misses: a value shaped like a credential under any name, and any value at all
    under a name that announces itself as a secret."""
    if not isinstance(value, str) or is_reference(value):
        return None
    for rx, why in _SECRET_SHAPES:
        if rx.search(value):
            return ("parameter %r holds %s: secrets are REFERENCES, never values (C5). Replace it "
                    "with a pointer such as 'ref:name' or 'vault:path/to/name'" % (key, why))
    if _SECRET_NAMES.search(str(key)) and value.strip():
        return ("parameter %r is named as a secret but holds a literal value: it must be a "
                "reference such as 'ref:%s' so the runtime resolves it at use time" % (key, key))
    return None


def _params_problems(where, params, out):
    if params is None:
        return
    if not isinstance(params, dict):
        out.append("%s: parameters must be a mapping, got %s" % (where, type(params).__name__))
        return
    for k, v in sorted(params.items()):
        if isinstance(v, dict):
            _params_problems("%s.%s" % (where, k), v, out)
            continue
        p = secret_problem(k, v)
        if p:
            out.append("%s: %s" % (where, p))


def validate(decl):
    """Every structural problem with one substrate declaration, as a list of strings. Empty means
    valid. Never raises and never partially reports: a caller gets the whole list so one run of the
    validator fixes one round of problems rather than N runs fixing N."""
    out = []
    if not isinstance(decl, dict):
        return ["a substrate declaration must be a mapping, got %s" % type(decl).__name__]
    for k in REQUIRED_TOP:
        if k not in decl:
            out.append("missing required top-level key %r" % k)
    if decl.get("schema") not in (None, SCHEMA):
        out.append("schema must be %r, got %r" % (SCHEMA, decl.get("schema")))
    env = decl.get("environment")
    if env is not None and env not in ENVIRONMENT_ORDER:
        out.append("environment %r is not one of %s: an undeclared environment has no place in the "
                   "promotion order" % (env, list(ENVIRONMENT_ORDER)))
    v = decl.get("version")
    if v is not None and not (isinstance(v, int) and v > 0):
        out.append("version must be a positive integer (a declaration is versioned so a diff is a "
                   "reviewable change), got %r" % (v,))
    res = decl.get("resources")
    if res is None:
        return out
    if not isinstance(res, list):
        out.append("resources must be a list, got %s" % type(res).__name__)
        return out

    names = []
    for i, r in enumerate(res):
        where = "resources[%d]" % i
        if not isinstance(r, dict):
            out.append("%s: each resource must be a mapping, got %s" % (where, type(r).__name__))
            continue
        for k in REQUIRED_RESOURCE:
            if k not in r:
                out.append("%s: missing required key %r" % (where, k))
        name = r.get("name")
        if name is not None:
            if not (isinstance(name, str) and name.strip()):
                out.append("%s: name must be a non-empty string, got %r" % (where, name))
            else:
                names.append(name)
                where = "resource %r" % name
        kind = r.get("kind")
        if kind is not None and kind not in RESOURCE_KINDS:
            out.append("%s: unknown resource kind %r. The vocabulary is declared once in "
                       "RESOURCE_KINDS; an unknown kind is refused at contract time because "
                       "nothing downstream could act on it" % (where, kind))
        ver = r.get("version")
        if ver is not None and not isinstance(ver, str):
            out.append("%s: version must be a string (pin it: '15.4', not 15.4), got %r"
                       % (where, ver))
        _params_problems(where, r.get("parameters"), out)

    dupes = sorted({n for n in names if names.count(n) > 1})
    if dupes:
        out.append("duplicate resource name(s) %s: a name is how a relationship resolves, so two "
                   "resources cannot share one" % dupes)

    known = set(names)
    for r in res:
        if not isinstance(r, dict):
            continue
        deps = r.get("depends_on") or []
        if not isinstance(deps, list):
            out.append("resource %r: depends_on must be a list, got %s"
                       % (r.get("name"), type(deps).__name__))
            continue
        for d in deps:
            if d not in known:
                out.append("resource %r depends on %r, which no resource in this environment "
                           "declares: a relationship that cannot resolve is a broken declaration, "
                           "and finding it here is the difference between a failed validation and "
                           "a half-provisioned environment" % (r.get("name"), d))
    return out


def promotion_index(environment):
    """Where an environment sits in the promotion order, or -1. W5's pipeline needs one answer to
    "which way is forward" and this is it, so the pipeline and the validator cannot disagree."""
    return ENVIRONMENT_ORDER.index(environment) if environment in ENVIRONMENT_ORDER else -1
