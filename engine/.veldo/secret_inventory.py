#!/usr/bin/env python3
"""The honest migration (WARP-1310, W10 of PLAN-0013).

Inventory a repository for literal secrets - working tree AND reachable history - report every
finding by REFERENCE SHAPE and never by value, name what needs rotating by a human, and let a
repository flip its gate check to fail-closed only once its own inventory is clean.

**HISTORY IS THE POINT.** A working tree somebody cleaned up last year is not a clean repository. A
credential committed and then deleted is still in every clone, in every fork, and in whatever CI
cached the checkout. Scanning only the tree finds the secrets nobody has hidden yet and misses the
ones that already leaked, which is precisely backwards.

**A FINDING NEVER CARRIES THE VALUE.** An inventory that quotes what it found is a second copy of
every secret in the repository, in a file that gets pasted into tickets and chat. Findings carry the
location, the detector that fired, and a truncated digest - enough to tell two findings apart, match
a rotation to a finding, and confirm a fix, and not enough to use.

**ROTATION IS A HUMAN ACT AND THIS MODULE NEVER PERFORMS IT.** What was in reachable history was
exposed, and the only real remedy is a new credential issued by whoever owns the system. The machine
cannot know who that is, cannot be trusted to guess, and must not quietly rotate production
credentials at three in the morning. So `rotation_worklist` produces named work for named people and
stops there.

**THE FLIP IS DECLARED, NOT INFERRED (D4).** A repository is advisory until its inventory is clean,
then it flips to fail-closed. The flip is a DECLARED, DATED FACT in a file, not something derived
from a scan returning zero: a scan that happens to come back empty because a path was skipped or a
detector broke would otherwise silently arm the gate, and the same accident in reverse would
silently disarm it. Declaring it means somebody decided, on a date, with the inventory in hand.

**AND IT DOES NOT SILENTLY DOWNGRADE.** Once a repository declares enforcing, moving back to
advisory is refused unless the declaration names a reason. The commonest way a security gate dies is
somebody turning it off during an incident and nobody turning it back on.

The scanner and the git plumbing are PASSED IN, so this module imports nothing, adds no second
spelling of what a secret looks like, and is fully testable with a fake history.
"""

SCHEMA = "veldo.secret_inventory/v1"

# Postures, in the order D4 sequences them. Advisory first per repository, then the flip.
ADVISORY = "advisory"
ENFORCING = "enforcing"
POSTURES = (ADVISORY, ENFORCING)

# WHICH DETECTOR GATES, and why - this split is MEASURED, not assumed. Over this repository's own
# working tree plus all 3,252 reachable blobs, the shipped detectors produced 898 pattern hits and
# 17,849 entropy hits. Entropy is a proportionate DIFF-time tripwire, where the unit is a handful of
# changed lines; used as an inventory gate at a 20:1 noise ratio it guarantees the gate gets turned
# off, which costs more than the tail it catches. So pattern findings GATE and entropy findings are
# reported ADVISORY. This is a scope decision about an instrument, not an exception for a secret.
GATING_DETECTORS = frozenset({"pattern"})

# Where a finding lives, which decides whether it needs a code fix or a code fix AND a rotation.
IN_TREE = "working_tree"
IN_HISTORY = "reachable_history"

# Refusals around the posture declaration itself.
UNKNOWN_POSTURE = "posture_not_in_vocabulary"
FLIP_WITH_FINDINGS = "flip_declared_while_inventory_is_dirty"
SILENT_DOWNGRADE = "enforcing_downgraded_without_a_reason"
NO_DATE = "posture_declared_without_a_date"


class InventoryError(ValueError):
    """Raised on a malformed posture declaration. Carries no fragment of any secret."""


def finding(where, location, line, kind, why, digest, blob=None):
    """One finding, BY REFERENCE. The value is never a field, so there is nowhere for it to be.

    THE SCANNER NEVER HANDS BACK WHAT IT MATCHED - it returns (line, kind, why) and nothing else -
    so there is no value here to leak even by accident. `digest` identifies the LINE, supplied by
    the caller, which is enough to tell two findings apart, match a rotation to a finding and
    confirm a fix, and not enough to use."""
    return {"schema": SCHEMA, "where": where, "location": location, "line": line, "detector": kind,
            "why": why, "digest": digest, "blob": blob}


def scan_tree(files, scan, digest_of):
    """Inventory the working tree. `files` is {path: text}; `scan` is the shipped detector module.

    Returns findings by reference. The text is read here and dropped here - it is never stored on a
    finding and never returned."""
    out = []
    for path in sorted(files or {}):
        lines = (files[path] or "").splitlines()
        for line_no, kind, why in scan.scan_text(files[path]) or []:
            src = lines[line_no - 1] if 0 < line_no <= len(lines) else ""
            out.append(finding(IN_TREE, path, line_no, kind, why, digest_of(src)))
    return out


def scan_history(blobs, scan, digest_of):
    """Inventory REACHABLE HISTORY. `blobs` is [(sha, path, text)] over every reachable object.

    THIS IS THE HALF THAT MATTERS. A credential committed and then deleted is still in every clone,
    every fork, and whatever CI cached the checkout. A tree-only scan finds the secrets nobody has
    hidden yet and misses the ones that already leaked."""
    out = []
    for sha, path, text in (blobs or []):
        lines = (text or "").splitlines()
        for line_no, kind, why in scan.scan_text(text) or []:
            src = lines[line_no - 1] if 0 < line_no <= len(lines) else ""
            out.append(finding(IN_HISTORY, path, line_no, kind, why, digest_of(src), blob=sha))
    return out


def exposed(findings):
    """The findings that require ROTATION rather than only a fix.

    Anything reachable in history was exposed the moment the branch was pushed, whatever the working
    tree looks like today. Deleting the line does not un-publish it."""
    return [f for f in (findings or []) if f.get("where") == IN_HISTORY]


def rotation_worklist(findings, owners=None):
    """Named work for NAMED PEOPLE. This module rotates nothing, ever.

    A rotation is a new credential issued by whoever owns the system. The machine cannot know who
    that is, must not guess, and must not quietly rotate production credentials at three in the
    morning. Where no owner is declared for a detector the item is still raised, addressed to
    `unassigned`, because an unowned exposed credential is the one most worth surfacing."""
    own = dict(owners or {})
    items = {}
    for f in exposed(findings):
        key = (f.get("detector"), f.get("digest"))
        it = items.setdefault(key, {"detector": f["detector"], "digest": f["digest"],
                                    "owner": own.get(f.get("detector"), "unassigned"),
                                    "locations": [], "action": "rotate: issue a new credential and "
                                                               "retire this one. Removing the line "
                                                               "does not un-publish it"})
        it["locations"].append("%s:%s@%s" % (f.get("location"), f.get("line"),
                                                 (f.get("blob") or "")[:8]))
    return [items[k] for k in sorted(items)]


def disposition_key(f):
    """What a disposition covers: ONE exact line, by digest, and the detector that fired.

    NOT a path and NOT a pattern. A path allowlist exempts a location forever, so a real credential
    dropped there later is invisible - which is the mechanism WARP-1302 refuses to ship, and this
    does not reintroduce it under another name. A disposition covers one byte-identical line: change
    the line and it no longer matches, so a real secret can never inherit a fixture's exemption."""
    return (f.get("detector"), f.get("digest"))


def validate_disposition(d):
    """A disposition is a human decision on the record: who, when, why. Returns problems.

    The integrity of this file is the integrity of any reviewed change plus the protected-path rules
    it should sit under - NOT this validation, which only checks that a decision was written down by
    somebody. Saying otherwise would be the false confidence the whole plan exists to avoid."""
    probs = []
    if not str((d or {}).get("digest") or "").strip():
        probs.append("a disposition covers one exact line and must name its digest")
    if not str((d or {}).get("decided_by") or "").strip():
        probs.append("a disposition is a decision a PERSON made and must name them")
    if not str((d or {}).get("decided_on") or "").strip():
        probs.append("a disposition must carry the date it was decided")
    if len(str((d or {}).get("reason") or "").strip()) < 20:
        probs.append("a disposition must say WHY in a sentence somebody can disagree with")
    return probs


def triage(findings, dispositions=None):
    """Split an inventory into what gates, what a human already dispositioned, and what is advisory.

    Returns {outstanding, dispositioned, advisory}. `outstanding` is the only bucket that can block:
    gating-detector findings nobody has dispositioned. A MALFORMED disposition does not disposition
    anything - it lands in outstanding with the finding, so an incomplete record fails toward the
    finding being visible rather than away from it."""
    known = {}
    for d in (dispositions or []):
        if not validate_disposition(d):
            known[(d.get("detector", "pattern"), d.get("digest"))] = d
    out = {"outstanding": [], "dispositioned": [], "advisory": []}
    for f in (findings or []):
        if f.get("detector") not in GATING_DETECTORS:
            out["advisory"].append(f)
        elif disposition_key(f) in known:
            out["dispositioned"].append(f)
        else:
            out["outstanding"].append(f)
    return out


def validate_posture(declaration, findings=None, previous=None):
    """Check a posture declaration, returning (posture, problems, notes).

    `problems` are STRUCTURAL and invalidate the declaration, which falls the posture back to
    advisory. `notes` are things the operator must see that do NOT invalidate anything - the
    separation exists because conflating them once made this gate fail open.

    THE FLIP IS DECLARED, NOT INFERRED. A scan that comes back empty because a path was skipped or
    a detector broke must not silently arm the gate, and the same accident in reverse must not
    silently disarm it. And once enforcing, a move back to advisory is refused unless it names a
    reason: the commonest way a security gate dies is somebody turning it off during an incident and
    nobody turning it back on."""
    d = declaration or {}
    posture, problems, notes = d.get("posture"), [], []
    # ABSENT IS NOT MALFORMED. A repository that has never declared a posture is advisory by
    # default, which is exactly what D4 sequences. Reporting that as a problem would greet every
    # freshly scaffolded repository with a refusal-shaped line about a decision it has not had the
    # chance to make yet, and noise like that is what teaches people to skim the gate.
    if not d:
        return (ADVISORY, problems, notes)
    if posture not in POSTURES:
        problems.append((UNKNOWN_POSTURE, "posture must be one of %s (got %r)"
                         % (list(POSTURES), posture)))
        return (ADVISORY, problems, notes)
    if not d.get("declared_on"):
        problems.append((NO_DATE, "a posture is a decision somebody made on a date, with the "
                                  "inventory in hand; an undated one is a default nobody chose"))
    # NOT A DECLARATION PROBLEM, AND THIS DISTINCTION IS THE WHOLE POINT. An earlier draft made
    # outstanding-findings-under-enforcing INVALIDATE the declaration, and since gate_result only
    # blocks when the declaration is problem-free, the gate then FAILED OPEN at exactly the moment a
    # real secret appeared: the secret invalidated the posture that was supposed to catch it. Caught
    # by running the teeth check the hour enforcing was first switched on.
    #
    # D4's "advisory first" is about the MOMENT SOMEBODY WRITES THE FLIP, which is a human act on a
    # date. Encoding it as a permanent property of the declaration turns a one-time sequencing rule
    # into a standing hole. So it is reported as a NOTE the operator sees, and it does not touch
    # validity.
    if posture == ENFORCING and findings:
        notes.append((FLIP_WITH_FINDINGS,
                      "%d finding(s) outstanding while enforcing. If this declaration is a FRESH "
                      "flip, revert it: D4 sequences advisory first per repository so nobody is "
                      "blocked on day one. If enforcing was already standing, this is the gate "
                      "doing its job and the findings are the thing to fix" % len(findings)))
    if previous == ENFORCING and posture == ADVISORY and not str(d.get("reason") or "").strip():
        problems.append((SILENT_DOWNGRADE,
                         "this repository already declared enforcing; going back to advisory needs "
                         "a written reason. A gate switched off during an incident is one nobody "
                         "turns back on"))
    return (posture, problems, notes)


def gate_result(findings, declaration, dispositions=None, previous=None):
    """What the gate does with an inventory, under the declared posture.

    Advisory REPORTS and does not block; enforcing blocks on anything OUTSTANDING. A malformed
    declaration falls back to advisory AND reports its own problem, so a broken declaration cannot
    arm the gate by accident - and cannot disarm a working one silently either, because the problem
    is in the output where somebody reads it."""
    t = triage(findings, dispositions)
    posture, problems, notes = validate_posture(declaration, t["outstanding"], previous)
    return {"posture": posture, "findings": len(findings or []),
            "outstanding": len(t["outstanding"]), "dispositioned": len(t["dispositioned"]),
            "advisory": len(t["advisory"]), "exposed": len(exposed(t["outstanding"])),
            "declaration_problems": problems, "declaration_notes": notes,
            "blocks": bool(t["outstanding"]) and posture == ENFORCING and not problems}


def report(result, findings=None):
    """The operator-facing lines. BY REFERENCE, never by value - an inventory that quotes what it
    found is a second copy of every secret in the repository, in a file people paste into tickets."""
    lines = ["secret inventory: %d outstanding (%d exposed in reachable history), %d "
             "dispositioned, %d advisory, %d scanned; posture=%s%s"
             % (result["outstanding"], result["exposed"], result["dispositioned"],
                result["advisory"], result["findings"], result["posture"],
                "" if result["blocks"] else " (reporting, not blocking)")]
    for reason, detail in result.get("declaration_problems") or []:
        lines.append("  declaration %-42s %s" % (reason, detail))
    for reason, detail in result.get("declaration_notes") or []:
        lines.append("  note        %-42s %s" % (reason, detail))
    for f in (findings or []):
        lines.append("  %-16s %-8s %s:%s%s" % (f["where"], f["detector"], f["location"],
                                               f["line"],
                                               "@" + f["blob"][:8] if f.get("blob") else ""))
    return lines
