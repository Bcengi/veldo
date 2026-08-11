#!/usr/bin/env python3
"""VELDO support numbers: THE DECLARED SKIP RULE, and what a store ENTRY IS (WARP-1210).

ONE DIRECTORY ENTRY, two questions: WHAT IS IT, and MAY A NAME DISMISS IT UNREAD.
The accounted read (.veldo/metrics_read_accounting.py) asks both once per entry and
owns nothing else about them; this module is the DECLARATION an adopter reads and
may extend, which is why it is the one module of the pass that loads NOTHING - no
engine sibling, no contract, no owner. It holds:

  SUPPORT_STORE_SKIP          the NAMES a store may hold that are not records
  SUPPORT_STORE_SKIP_MAX_DEPTH  how deep a dismissible directory may be walked
  store_skip_reason(name)     WHY one name is a non-record, by POSITIVE match
  _skippable_entry(path, sfx) the only KINDS of entry such a name may dismiss
  _entry_kind(path)           WHAT an entry is, from ONE lstat, for a human
  _unaccounted_detail(...)    one entry a read could not account for, NAMED

WHAT "A RECORD" MEANS HERE, because the skip rule can be no stronger than that
definition: a store identifies a record BY ITS NAME (name.endswith(suffix), which
the accounted read asks FIRST at every entry), so an entry not bearing the suffix
is not a record of that store whatever its bytes are, and no rule here opens a
file to ask. The skip rule therefore decides on the KIND of an entry and never on
its content. THE TWO RESIDUALS THAT FOLLOW, declared and measured rather than
implied away: a skip-named REGULAR FILE is never opened, so record-shaped bytes
inside a conventionally-named non-record file are not consumed; and a HARDLINK
bearing a skip name IS a regular file, indistinguishable from one by design, so
it is skipped as the regular file it is. Both are availability-neutral and
correctness-visible: the store's own convention says neither is a record, and
deciding record-ness by CONTENT would consume files that convention excludes
while opening entries this pass deliberately refuses to open.

Reads recorded files only, opens none of them: no live system (NG1), no process,
thread or timer (NG3), and nothing is written anywhere.
"""
import os
import stat
from pathlib import Path

# THE DECLARED SKIP RULE: the NAMES a store directory may hold that are NOT records, and whose presence
# therefore says nothing about whether its records were read completely. It is the pattern the CORPUS read
# already carries for its owner's index.md and TEMPLATE* names, applied at the THREE directory reads this
# pass performs, TWO of which had no such rule. It exists because of a MEASURED cost: without it ONE
# .gitkeep left an entry nobody could account for and stood the WHOLE SECTION down permanently, as did one
# README, one .gitignore and one editor swapfile. A NAME IS ONLY HALF THE DECISION: the entry must also be
# of a KIND the rule may be applied to (_skippable_entry), because a SYMLINK can resolve to records and a
# DIRECTORY can hold them, and dismissing either LOSES them while the section renders. THE RESIDUAL IS
# OPEN-ENDED BY DESIGN: a closed positive-match table cannot enumerate convention, so a conventional name
# no row lists (.editorconfig, LICENSE, a CHANGELOG, a subdirectory named drafts/, the next tool's dotfile)
# is still UNACCOUNTED and still stands the section down, which is the fail-closed side to be on.
SUPPORT_STORE_SKIP = (
    {"match": "exact", "pattern": ".gitkeep", "why": "the placeholder that commits an empty store directory"},
    {"match": "exact", "pattern": ".keep", "why": "the .gitkeep synonym other tooling writes"},
    {"match": "exact", "pattern": ".gitignore", "why": "the version-control ignore rules for this store"},
    {"match": "exact", "pattern": ".gitattributes", "why": "the version-control attributes for this store"},
    {"match": "exact", "pattern": ".DS_Store", "why": "a file browser's own directory index"},
    {"match": "exact", "pattern": "Thumbs.db", "why": "a file browser's own thumbnail cache"},
    {"match": "exact", "pattern": "desktop.ini", "why": "a file browser's own folder settings"},
    {"match": "exact", "pattern": "archive", "why": "an operator's archive of superseded records, "
                                                    "dismissible only while it holds none of them "
                                                    "within the declared depth bound"},
    {"match": "prefix", "pattern": "README", "why": "documentation an operator left beside the records"},
    {"match": "prefix", "pattern": ".#", "why": "an editor lock file over a record being edited"},
    {"match": "suffix", "pattern": ".swp", "why": "an editor swapfile over a record being edited"},
    {"match": "suffix", "pattern": ".swo", "why": "an editor's SECOND swapfile over a record"},
    {"match": "suffix", "pattern": "~", "why": "an editor backup copy of a record"},
    {"match": "suffix", "pattern": ".orig", "why": "a merge tool's copy of a record before the merge"},
    {"match": "suffix", "pattern": ".rej", "why": "a patch tool's rejected hunks against a record"},
    {"match": "suffix", "pattern": ".bak", "why": "a hand-made backup copy of a record"},
)
_SUPPORT_SKIP_MATCH = {"exact": lambda name, pattern: name == pattern,
                       "prefix": lambda name, pattern: name.startswith(pattern),
                       "suffix": lambda name, pattern: name.endswith(pattern)}
# THE DECLARED DEPTH BOUND OF THE DIRECTORY HALF, because "its OWN enumeration finds no record" quantifies
# over a domain no fixture can enumerate: a tree has no maximum depth, the walk below RECURSES, and CPython
# answers an unbounded recursion with RecursionError - a RuntimeError, neither the OSError nor the ValueError
# the path predicates swallow, so NO handler in this pass caught it. MEASURED on the unbounded round-8 walk
# (CPython 3.12, default 1000-frame limit): 2 frames per level, dismissible at 495 levels and RecursionError
# at 500, which exited ALL FOUR SURFACES printing nothing where standing ONE source down was the honest
# answer (R8-B1, R6-B1's class). A subtree deeper than this bound is therefore NOT dismissible: the entry is
# UNACCOUNTED and the section stands down BY NAME with the bound stated, the same fail-closed answer a
# directory this pass cannot LIST already gets. 32 levels costs 69 frames (measured: 5 + 2 per level), under
# 7 percent of that limit, so THE RULE stops the walk first WHENEVER THE CALLER HAS THAT MUCH STACK LEFT -
# which is not a universal and is why the call site keeps a RecursionError backstop: a caller already deep in
# its own frames, or a lowered limit, can still exhaust the stack inside 32 levels, and the backstop turns
# that into the same UNACCOUNTED answer. The bound is far past any archive an operator writes
# (archive/2026/Q1/) - DECLARED as a named constant so an adopter who nests deeper reads why it stood down.
SUPPORT_STORE_SKIP_MAX_DEPTH = 32


def store_skip_reason(name):
    """WHY one enumerated entry of a store directory is SKIPPED rather than consumed, or None when nothing
    declares it skippable. POSITIVE MATCH ONLY, exactly like read_proves_complete: a match kind this table
    does not declare matches nothing, so the fail-closed default survives the skip rule and an entry this
    function does not name is still an entry the read has to account for some other way. A NAME ALONE, this:
    whether the entry is of a KIND that may be dismissed at all is _skippable_entry's call."""
    for row in SUPPORT_STORE_SKIP:
        match = _SUPPORT_SKIP_MATCH.get(row["match"])
        if match is not None and match(str(name), row["pattern"]):
            return row["why"]
    return None


def _skippable_entry(path, suffix, depth=0):
    """WHETHER THE DECLARED SKIP RULE MAY BE APPLIED TO THIS ENTRY AT ALL: to a REGULAR FILE, and to a
    DIRECTORY that proves BY ITS OWN ENUMERATION, WITHIN SUPPORT_STORE_SKIP_MAX_DEPTH levels of it, that it
    holds no record and nothing that could hold one - every entry inside it answering this same question and
    bearing no record suffix, which an EMPTY directory satisfies, and which a directory this pass cannot
    LIST and a subtree DEEPER THAN THE BOUND do not. A SYMLINK IS NEVER EITHER, whatever it resolves to. The
    directory half is the enumerate-or-fail-closed doctrine of the accounted read applied one level down,
    and it is why an `archive` of superseded records is dismissible while it holds none of them and stands
    the section down the moment it holds one: those records are records this pass did not read. A DECLARED
    NAME is required only at the level the read enumerates; below it the only question is whether a record
    could be hiding.

    R6-B2(a) was a real data loss - the rule matched on NAME alone, so a DIRECTORY named archive or
    .gitkeep holding a record, an archive symlinked to a directory of records and a .gitkeep symlinked to a
    record were each SKIPPED while the section rendered at 100 percent, a seeded record gone in silence.
    isfile FOLLOWS the link, so the islink clause is what makes the ENTRY ITSELF decide (the lstat doctrine,
    one predicate over). The path predicates swallow OSError and ValueError and answer False, and False here
    means UNACCOUNTED, so an error they swallow fails CLOSED rather than dismissing. THE ERRORS THEY DO NOT
    SWALLOW ARE THE ONES THIS FUNCTION CAN RAISE ITSELF, and its enumeration names all FOUR DECLARED CLASSES
    for that reason: RecursionError is a RuntimeError, so at round 8 it passed every handler and took all
    four surfaces down (the bound above refuses it first and the one call site keeps a backstop), and
    MemoryError - named nowhere in this repository until round 10 - is neither an OSError nor a ValueError
    either, so a listdir too large for the memory the process may have would have escaped identically.

    THE ASYMMETRY BETWEEN THE THREE BRANCHES IS DELIBERATE AND THE TOCTOU WINDOW OF EACH IS NAMED, because
    this function does DISMISS A DIRECTORY UNREAD on an enumeration that can change after the check exactly
    as a link's target can. CONSUMING a link's resolved record is safe: the bytes are read, parsed and
    counted, so a target that changes changes what was read. DISMISSING A DIRECTORY decides on the entry's
    OWN content, enumerated THROUGH THE ENTRY at every level (no level follows a link, so the walk cannot
    leave the subtree), and the accepted window is from that enumeration to the moment the model renders: a
    record written under a dismissed directory inside that window is not in this read, which stays a true
    statement about the store AS ENUMERATED, and the NEXT read stands the section down by name. Every read
    of a filesystem carries that window - a consumed record can be appended to a microsecond after it is
    parsed - so refusing it would refuse the whole read. DISMISSING A SYMLINK is refused on the MEASURED
    loss rather than on that window: a link's target is a DIFFERENT object which the entry does not contain,
    so the fact checked is not a fact about the entry at all."""
    if os.path.isfile(str(path)) and not os.path.islink(str(path)):
        return True
    if os.path.islink(str(path)) or not os.path.isdir(str(path)):
        return False
    if depth > SUPPORT_STORE_SKIP_MAX_DEPTH:
        return False
    try:
        inner = os.listdir(str(path))
    except (OSError, ValueError, RecursionError, MemoryError):
        return False
    return all(_skippable_entry(Path(path) / n, suffix, depth + 1) and not n.endswith(suffix)
               for n in inner)


def _entry_kind(path):
    """A short, honest description of what a directory entry IS, for the detail of an unaccounted entry:
    the reader has to say WHAT it could not account for, or a human cannot act on the stand-down.

    LINK-NESS IS DECIDED FIRST, from ONE os.lstat rather than from a sequence of predicates that follow the
    link, which is R7-B4: this function asked isdir and isfile first, so a .gitkeep SYMLINKED to a real
    record was reported as "a file this reader does not consume" and an archive symlinked to a directory of
    records as "a directory". Both named the entry after its TARGET, while the fact that made it
    unaccountable - that it is a LINK, which the skip rule may never dismiss - went unsaid in the one line a
    human reads. lstat is the presence doctrine of the accounted read, one function over, and it is what
    makes the error branch below REACHABLE: os.path.* swallow OSError and ValueError and answer False, so a
    describer built on them could never say that it could not look. IT DIFFERS FROM _skippable_entry
    DELIBERATELY: that guard is a conjunction which may fail CLOSED on an answer it cannot get, while a
    describer has to name something whatever happens."""
    try:
        entry = os.lstat(str(path))
    except (OSError, ValueError, RecursionError, MemoryError) as exc:
        return "an entry that cannot be inspected (%s)" % type(exc).__name__
    if stat.S_ISLNK(entry.st_mode):
        try:
            target = os.stat(str(path))
        except (OSError, ValueError, RecursionError, MemoryError):
            return "a symlink that does not resolve"
        return "a symlink to %s" % ("a directory" if stat.S_ISDIR(target.st_mode)
                                    else "a file" if stat.S_ISREG(target.st_mode)
                                    else "an entry that is neither a file nor a directory")
    if stat.S_ISDIR(entry.st_mode):
        return "a directory"
    if stat.S_ISREG(entry.st_mode):
        return "a file this reader does not consume"
    return "an entry that is neither a regular file nor a directory"


def _unaccounted_detail(name, entry):
    """ONE unaccounted entry named for a human: WHAT it is, and - when the DECLARED TABLE does name it -
    that the name was recognized and it is the entry's KIND the rule could not be applied to. Without that
    second half an operator reads a name this table declares skippable, reported as unaccounted, and has
    nothing to act on; with it the line says which of the two halves of the rule refused. FOR A DIRECTORY,
    the one kind whose dismissal is a PROOF rather than a kind, it also states the DEPTH BOUND that proof is
    taken within: "it stood down on my archive/" is unactionable unless the walk's reach is on the line."""
    reason = store_skip_reason(name)
    declared = ("; the declared skip rule NAMES this entry (%s) and its KIND is what the rule may not be "
                "applied to" % reason) if reason is not None else ""
    bounded = ("; a DIRECTORY is dismissible only while its OWN enumeration, bounded at %d levels below it, "
               "finds no record and nothing that could hold one, so a record anywhere inside that bound, and "
               "a subtree deeper than it, both leave this entry UNACCOUNTED" % SUPPORT_STORE_SKIP_MAX_DEPTH
               ) if os.path.isdir(str(entry)) and not os.path.islink(str(entry)) else ""
    return "%s (%s%s%s)" % (name, _entry_kind(entry), declared, bounded)
