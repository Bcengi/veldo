#!/usr/bin/env python3
"""The naming contract and the residual-name check (WARP-1701, W1 of PLAN-0017).

One declared record of what the name is on every surface class, and a mechanical check that refuses
a residual occurrence of the old name on a surface the contract says has been renamed.

**A BLANKET GREP WOULD BE USELESS HERE, AND THAT IS THE WHOLE DESIGN PROBLEM.** The old name appears
legitimately in places the rename must never touch: every specification id is the OLD prefix, the
historical proof corpus records evidence under identifiers that were true when it was recorded, and
the document histories describe decisions made under the old name. A check that searched the tree
for the word would fire on all of it, and the first thing anybody would do is switch it off.

So the contract enumerates SURFACE CLASSES and the check is scoped per surface. A surface is renamed
or it is not; each carries its own rule; and a surface the contract does not name is not checked,
which is a deliberate hole with a name rather than an accident.

**IT REFUSES NOTHING UNTIL THE RENAME HAS HAPPENED.** The posture is declared, exactly as the secret
inventory's is: `pre_rename` reports and does not block, `post_rename` blocks. The check must exist
and have teeth BEFORE the rename it guards, which means it must be able to run green against a tree
that is still entirely under the old name.

**WHAT REINTRODUCES A NAME IS A PERSON IN A HURRY, NOT AN ATTACKER.** Someone copies an old snippet,
a template still says the old thing, a generated artifact carries a stale schema id. That is why the
negative tests seed a reintroduction PER SURFACE CLASS: a check that only proves the tree is clean
today proves nothing about the tree next month.

Every path and every file's text is passed IN by the caller, so this module reads no filesystem, is
pure over its inputs, and is fully testable against a fake tree.
"""

SCHEMA = "veldo.naming/v1"

# The postures, in the order the migration sequences them.
PRE_RENAME = "pre_rename"
POST_RENAME = "post_rename"
POSTURES = (PRE_RENAME, POST_RENAME)

# THE SURFACE CLASSES the plan enumerates. Each is a place a NAME is user-visible or structurally
# load-bearing. A surface absent from this table is NOT CHECKED, which is a hole with a name.
PRODUCT = "product"
REPOSITORY = "repository"
COMMAND = "command"
STATE_DIR = "state_directory"
SCHEMA_IDS = "schema_identifiers"
PLUGIN = "plugin"
DOCUMENTS = "documents"
SITE = "site"
SURFACES = (PRODUCT, REPOSITORY, COMMAND, STATE_DIR, SCHEMA_IDS, PLUGIN, DOCUMENTS, SITE)

# What is DELIBERATELY NOT RENAMED, recorded here rather than left as an omission somebody has to
# infer. These carry the old name correctly and forever.
NOT_RENAMED = {
    "spec_ids": "a specification id like WARP-1701 is an immutable identifier of a decision that was "
                "made; renaming it would break every cross-reference and every proof that cites it",
    "proof_corpus": "evidence records what was true when it was recorded. A renamed schema identifier "
                    "must not invalidate evidence already on the record",
    "document_history": "a history entry describes a change made under the name in force at the time; "
                        "rewriting it would make the history a fiction",
    "git_history": "commit messages are immutable by construction and are not a surface",
}

# THE CASE RULING, which this contract owed an answer to. Dmitry, 2026-08-09: the name is Veldo in
# prose and branding, VELDO in code identifiers.
#
# The reasoning, recorded so it is not re-litigated: an environment variable is UPPER_SNAKE by
# convention in every shell, and nobody writes Github_TOKEN while still calling the product GitHub.
# So an all-caps ban that reaches identifiers is a ban on a convention, not on a name. The ban is
# therefore scoped to PROSE.
#
# The mechanical test is what FOLLOWS the token, because that is what separates an identifier from a
# word: an identifier continues into an underscore or hyphen plus more token. VELDO_EMERGENCY and
# VELDO-0142 are identifiers and permitted; a bare VELDO in a sentence is prose and refused.
CASE = {
    "prose": "Veldo",
    "branding": "Veldo",
    "identifiers": "VELDO",
    "test": r"VELDO(?![_-]?[A-Z0-9#N])(?!\.[a-z])",
    "ruled_by": "dmitry",
    "ruled_at": "2026-08-09",
}

# ONE THING THIS RULING DOES NOT RESOLVE, recorded as open rather than left to be discovered.
# Specification ids are BOTH identifiers (so VELDO-0142 by the rule above) and immutable references
# (so WARP-0142 forever, per NOT_RENAMED["spec_ids"]). Those cannot both be true of the same string,
# and today the contradiction is invisible only because O2 strips the internal specifications from
# the public tree, so a published document can say VELDO-0142 with nothing for a reader to check it
# against. The durable fix is for the documents to stop citing internal ids at all. That is a
# documents change and belongs in the loop, not in a rename.
SPEC_ID_TENSION = ("published documents render ids under the CURRENT name while the artifacts "
                   "keep the OLD one; harmless only while the specifications are unpublished. "
                   "Both spellings are described rather than quoted, because a prose pass over "
                   "this file once rewrote both sides of the sentence into the same word and "
                   "turned it into a tautology")

# Refusals, each named.
RESIDUAL = "residual_old_name_on_a_renamed_surface"
UNKNOWN_SURFACE = "surface_not_in_the_contract"
UNDECLARED_SURFACE = "contract_does_not_cover_every_surface_class"
UNKNOWN_POSTURE = "posture_not_in_vocabulary"
NO_NEW_NAME = "surface_declares_no_new_name"


class NamingError(ValueError):
    pass


# THE OLD NAME AS DATA, spelled in two pieces so the rename cannot reach it. This module is itself
# renamed; a contiguous literal would be rewritten and the two spellings below would collapse into
# one, silently withdrawing the acceptance this exists to give. Do not rejoin it.
_OLD_NAME = "w" "arp"


def accepted_schemas(current):
    """Both spellings of a schema id, newest first, because EVIDENCE KEEPS THE ID IT WAS RECORDED
    UNDER.

    NOT_RENAMED above says the proof corpus holds the old name forever, and gives the reason: a
    renamed schema identifier must not invalidate evidence already on the record. That promise has a
    cost, and this is the cost: every reader of a recorded artifact has to accept the historical
    spelling, or the rename invalidates exactly what the contract promised it would not.

    ONE definition, because there is now more than one reader that needs it (the event log and the
    recorded slice measurement), and a second copy would be a second answer to the same question.
    Before the cutover this returns a single spelling, because there is no history to accept yet."""
    prefix, _, rest = current.partition(".")
    if not rest or prefix == _OLD_NAME:
        return (current,)
    return (current, _OLD_NAME + "." + rest)


def contract(old, new, surfaces=None, posture=PRE_RENAME):
    """The declared record: what the name IS on every surface class.

    `surfaces` maps a surface class to the concrete thing the name appears as - the command word, the
    state directory, the schema prefix. Defaulting it from `new` is a convenience, not a licence to
    leave one out: `problems()` refuses a contract that does not cover every class in SURFACES."""
    return {"schema": SCHEMA, "old": old, "new": new, "posture": posture,
            "surfaces": dict(surfaces or {s: new for s in SURFACES})}


def problems(c):
    """Everything wrong with the CONTRACT itself, before it is used to judge anything."""
    out = []
    if (c or {}).get("posture") not in POSTURES:
        out.append((UNKNOWN_POSTURE, "posture must be one of %s (got %r)"
                    % (list(POSTURES), (c or {}).get("posture"))))
    surf = (c or {}).get("surfaces") or {}
    for s in SURFACES:
        if s not in surf:
            out.append((UNDECLARED_SURFACE,
                        "surface class %r is not declared. A rename that covers seven of eight "
                        "surfaces is the one that leaves the old name somewhere a stranger reads "
                        "first" % s))
        elif not str(surf.get(s) or "").strip():
            out.append((NO_NEW_NAME, "surface %r declares no new name" % s))
    for s in sorted(surf):
        if s not in SURFACES:
            out.append((UNKNOWN_SURFACE, "surface %r is not a known surface class %s"
                        % (s, list(SURFACES))))
    if not str((c or {}).get("old") or "").strip():
        out.append((NO_NEW_NAME, "the contract must name the OLD name it is renaming from"))
    return out


def residuals(c, items):
    """Residual occurrences of the old name, per surface.

    `items` is [(surface, where, text)] - the caller enumerates the surfaces and reads the text, so
    this module touches no filesystem. Matching is CASE-INSENSITIVE, because `Veldo`, `VELDO` and
    `veldo` are the same name to a reader and a rename that fixes one casing is the rename that
    leaves the other two in the README's first paragraph.

    A surface the contract does not declare yields an UNKNOWN_SURFACE finding rather than being
    quietly skipped: an item arriving from a surface nobody declared is a gap in the contract."""
    old = str((c or {}).get("old") or "").lower()
    declared = set((c or {}).get("surfaces") or {})
    out = []
    if not old:
        return out
    for surface, where, text in (items or []):
        if surface not in declared:
            out.append((UNKNOWN_SURFACE, surface, where,
                        "an item arrived from a surface the contract does not declare, which is a "
                        "gap in the contract rather than a clean result"))
            continue
        lines = (text or "").splitlines() or [""]
        for n, line in enumerate(lines, 1):
            if old in line.lower():
                out.append((RESIDUAL, surface, "%s:%d" % (where, n),
                            "the old name survives on the %s surface, which the contract says is "
                            "now %r" % (surface, (c or {}).get("surfaces", {}).get(surface))))
    return out


def check(c, items):
    """Contract problems and residual findings together, with whether they BLOCK.

    Blocking is posture-dependent BY DESIGN: this check must exist and be green BEFORE the rename it
    guards, so `pre_rename` reports and does not block. A malformed contract never blocks and always
    reports, so a broken contract can neither arm the check by accident nor silently disarm it."""
    probs = problems(c)
    found = residuals(c, items)
    posture = (c or {}).get("posture")
    return {"posture": posture if posture in POSTURES else PRE_RENAME,
            "contract_problems": probs, "residuals": found,
            "blocks": bool(found) and posture == POST_RENAME and not probs}


def report(result):
    lines = ["naming: %d residual(s) across %d surface(s), posture=%s%s"
             % (len(result["residuals"]),
                len({f[1] for f in result["residuals"]}), result["posture"],
                "" if result["blocks"] else " (reporting, not blocking)")]
    for reason, detail in result["contract_problems"]:
        lines.append("  contract %-46s %s" % (reason, detail))
    for reason, surface, where, detail in result["residuals"]:
        lines.append("  %-14s %-20s %s" % (surface, reason, where))
        if reason == RESIDUAL:
            lines.append("      %s" % detail)
    return lines
