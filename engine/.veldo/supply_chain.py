#!/usr/bin/env python3
"""Supply chain policy as code (WARP-1306, W6 of PLAN-0013).

A new dependency is a decision somebody made, not a convenience that appeared. Adding one refuses
unless a decision reference is recorded with the change.

**WHY THIS ONE MATTERS MORE FOR AGENTS THAN FOR PEOPLE.** A person adding a dependency has usually
at least glanced at it. An agent picks packages the way it picks patterns: by familiarity from
training data. That is a completely different selection function, and it is trivially poisoned -
a package named plausibly enough to look familiar is the whole of a typosquat attack. Meanwhile the
agent adds it in seconds, in the middle of a change about something else, with a commit message
about the something else.

So the requirement is not review quality, it is VISIBILITY: a dependency arrives attached to a
reason, or it does not arrive.

**THE INTEGRITY CHECK IS SEPARATE FROM THE POLICY CHECK, AND BOTH FAIL CLOSED.** A lockfile whose
hashes are missing is not a lockfile, it is a list of names, and a manifest change with no
corresponding lockfile change means somebody edited one and not the other - which is how a resolved
version silently drifts from the declared one.

**SOFT SEAM (C6).** Where PLAN-0011's foundational-decision records exist, a `DEC-` reference is
required and checked against them. Where they do not, a built-in decision NOTE satisfies the same
requirement: a short written reason recorded with the change. Standing down to a weaker artifact is
correct; standing down to nothing would make the whole check optional in exactly the repositories
least likely to have the machinery.
"""
import re

SCHEMA = "veldo.supply_chain/v1"

# Refusals, each named. "Dependency policy violation" sends somebody to read source.
NO_DECISION = "dependency_added_without_decision"
LOCKFILE_MISSING_HASHES = "lockfile_entry_without_integrity"
MANIFEST_LOCKFILE_DRIFT = "manifest_changed_without_lockfile"
LICENSE_REFUSED = "license_not_permitted"
UNKNOWN_LICENSE = "license_undeclared"
DECISION_NOT_FOUND = "decision_reference_unresolvable"

# Declared in policy, not here. These are the defaults an adopting repo starts from and edits.
DEFAULT_PERMITTED_LICENSES = frozenset({
    "MIT", "BSD-2-Clause", "BSD-3-Clause", "Apache-2.0", "ISC", "PSF-2.0", "Unlicense", "CC0-1.0",
})

_DEC_REF = re.compile(r"\ADEC-[A-Za-z0-9._-]+\Z")


def added_dependencies(before, after):
    """Dependencies present in `after` and not `before`. Name and resolved version.

    A VERSION CHANGE IS NOT AN ADDITION and is not flagged here: bumping a dependency you already
    decided to take is ordinary work, and treating it as a new decision would make the check so
    noisy it gets removed. What is new is the RELATIONSHIP, not the number."""
    b, a = set(before or {}), dict(after or {})
    return sorted((n, a[n]) for n in set(a) - b)


def lockfile_problems(lock):
    """Entries with no integrity hash. A lockfile without hashes is a list of names.

    This is separate from the policy check on purpose: a repository can have a perfectly good
    reason for every dependency it holds and still be installing whatever the registry serves
    today."""
    out = []
    for name, entry in sorted((lock or {}).items()):
        if not isinstance(entry, dict):
            out.append((name, "entry is not a mapping, so it carries no integrity"))
            continue
        digest = entry.get("integrity") or entry.get("hash") or entry.get("sha256")
        if not (isinstance(digest, str) and len(digest) >= 32):
            out.append((name, "no integrity hash: this pins a NAME, not a package"))
    return out


def license_problems(after, permitted=None, licenses=None):
    """Dependencies whose license is not permitted, or not declared at all.

    UNDECLARED IS REFUSED, NOT ASSUMED PERMISSIVE. A dependency whose license nobody recorded is
    a dependency nobody checked, and the permissive assumption is how a copyleft package ends up
    in a proprietary product."""
    allow = set(DEFAULT_PERMITTED_LICENSES if permitted is None else permitted)
    lic = dict(licenses or {})
    out = []
    for name in sorted(after or {}):
        got = lic.get(name)
        if not got:
            out.append((name, UNKNOWN_LICENSE, "no license recorded, and undeclared is refused "
                                               "rather than assumed permissive"))
        elif got not in allow:
            out.append((name, LICENSE_REFUSED, "license %s is not in the permitted set" % got))
    return out


def check(before, after, lock_before=None, lock_after=None, decisions=None,
          decision_refs=None, permitted=None, licenses=None, decision_notes=None):
    """Every supply-chain problem with one change, as (reason, subject, detail).

    `decisions` is the set of known DEC- ids where PLAN-0011 has shipped; `decision_notes` is the
    stand-down artifact where it has not. Supplying NEITHER for an added dependency refuses -
    standing down to a weaker artifact is correct, standing down to nothing would make the check
    optional in exactly the repositories least able to afford that."""
    problems = []
    added = added_dependencies(before, after)
    refs = dict(decision_refs or {})
    notes = dict(decision_notes or {})
    known = set(decisions) if decisions is not None else None

    for name, version in added:
        ref, note = refs.get(name), notes.get(name)
        if ref:
            if not _DEC_REF.match(str(ref)):
                problems.append((DECISION_NOT_FOUND, name,
                                 "decision reference %r is not a DEC- id" % ref))
            elif known is not None and ref not in known:
                problems.append((DECISION_NOT_FOUND, name,
                                 "decision %s is referenced but no such record exists" % ref))
        elif isinstance(note, str) and len(note.strip()) >= 20:
            continue                                   # the stand-down artifact, and it is enough
        else:
            problems.append((NO_DECISION, name,
                             "%s@%s was added with no decision reference and no written reason. An "
                             "agent picks packages by familiarity from training data, which is "
                             "trivially poisoned; a dependency arrives attached to a reason or it "
                             "does not arrive" % (name, version)))

    # MANIFEST AND LOCKFILE MOVE TOGETHER, or a resolved version has drifted from a declared one.
    if added and lock_after is not None:
        missing = [n for n, _v in added if n not in (lock_after or {})]
        if missing:
            problems.append((MANIFEST_LOCKFILE_DRIFT, ", ".join(missing),
                             "added to the manifest but absent from the lockfile: somebody edited "
                             "one and not the other, which is how a resolved version drifts"))
    for name, why in lockfile_problems(lock_after):
        problems.append((LOCKFILE_MISSING_HASHES, name, why))
    for name, reason, why in license_problems(
            {n: v for n, v in added}, permitted, licenses):
        problems.append((reason, name, why))
    return problems


def report(problems):
    if not problems:
        return ["supply chain: no problems"]
    return ["supply chain: %d problem(s)" % len(problems)] + \
           ["  %-38s %s: %s" % (r, s, d) for r, s, d in problems]
