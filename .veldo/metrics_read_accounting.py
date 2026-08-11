#!/usr/bin/env python3
"""VELDO support numbers: THE ACCOUNTED READ (WARP-1210).

What makes a read of a filesystem source COMPLETE, and how a reader PROVES it.
The support pass reads eight data sources at the repository being measured; this
module owns the mechanism all of them go through, so the completeness rule is
implemented ONCE rather than per source (the four sibling OWNER modules it
executes are the other plane, in .veldo/metrics_owner_reads.py, and the DECLARED
SKIP RULE with the entry describer its refusals are read through is the third, in
.veldo/metrics_skip_rule.py):

  _present(path)              PRESENCE by os.lstat, never exists()/is_dir()
  _accounted_dir(...)         one directory ENUMERATED and every entry ACCOUNTED
  _record_shortfall(read)     one artifact's text is a RECORD, or WHY it is not
  _parsed_shortfall(...)      a collection read in PART is INCOMPLETE, and
  _dependency_declined(...)   a source whose dependency fell short does not affirm

WHY IT IS ITS OWN MODULE, and why these primitives rather than the obvious ones:
three consecutive reviews failed this item on shapes nobody had enumerated, and
every one of them entered through a Python path predicate that answers
plausibly instead of raising.

  * glob() SWALLOWS PermissionError and yields nothing, so a mode-000 directory
    read as an EMPTY one. os.listdir RAISES, so it is what enumerates here.
  * exists() and is_dir() FOLLOW the link and swallow the error, so a symlink
    LOOP and a DANGLING symlink both answered False while the directory entry
    was plainly there, and the source was reported ABSENT. os.lstat sees the
    entry itself, so it is what decides presence here.
  * a PATTERN cannot account for what it does not match, so a record in a
    subdirectory, under an uppercase suffix or under a sibling suffix simply was
    not there. Every enumerated entry is ACCOUNTED for here, and one entry a
    reader cannot account for leaves the read INCOMPLETE.

An ABSENT source is COMPLETE and empty (adoption safe). Everything else has to
be AFFIRMED to count, through the contract's read_complete with a BASIS that
says what makes it complete, so a shape nobody has thought of yet fails CLOSED
without anyone adding a name for it. An entry the DECLARED SKIP RULE names AND
may be applied to (a .gitkeep, a README, an editor swapfile, an empty archive) is
ACCOUNTED as the non-record it is: counted and named in the read record, carried
into the model as read_skipped, rendered on all three surfaces, and it does not
stand the section down. A RECORD IS IDENTIFIED BY ITS NAME here (the suffix is
asked FIRST at every entry), so what a name may dismiss is a KIND of entry rather
than a content, and the two residuals that follow are declared where the rule is
(.veldo/metrics_skip_rule.py): a skip-named regular file is never OPENED, and a
HARDLINK bearing a skip name is skipped as the regular file it is.

THE CODEC IS DECLARED AT EVERY READ OF A RECORDED ARTIFACT IN THIS PASS AND
NEVER INHERITED FROM THE ENVIRONMENT (read_text(encoding="utf-8"), at the event
stream and the receipt files in .veldo/metrics_readers.py and at the loop reader
in .veldo/metrics.py, which states the measurement in full). read_text() with no
encoding decodes through the LOCALE's codec, so ONE valid-UTF-8 character made
the loop reader skip a recorded line under LC_ALL=C and keep it under C.UTF-8:
the same bytes, two different numbers, silently. A recorded artifact has ONE
encoding, so whether a source THIS PASS READS ITSELF is READ or stood DOWN is a
property of its bytes rather than of the operator's environment. WHAT IS STILL
ENVIRONMENT-DEPENDENT and is declared rather than fixed here: the four ENGINE
OWNERS this pass executes (.veldo/incident.py, .veldo/validate.py,
.veldo/intent_corpus.py, .veldo/entropy.py) read their own files through the
locale's codec, which is outside this item's footprint - measured, the source that
owner reads stands DOWN BY NAME under an ASCII locale, so it costs AVAILABILITY
and moves no MEASURE. TWO NUMBERS DO MOVE and saying otherwise was measured
false: this section's own incomplete_source_count (0 to 3) and renderable (true to
false), which IS the stand-down being visible. Every non-support key of --json is
byte-equal across the two locales.

Every enumerated NAME reaches a rendered detail through the contract's
printable(), because a directory entry name is bytes the filesystem accepted and
the stream that prints it may be ASCII - applied in the read-record and problem
CONSTRUCTORS every detail here is built into, rather than per name at each
interpolation, so the boundary is one place a tooth can hold.

Reads recorded files only: no live system (NG1), no process, thread or timer
(NG3), and nothing is written anywhere.
"""
import importlib.util
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The core derivation supplies the ONE sibling-module loader, bound here rather than reimplemented: one
# loader for the whole metrics area, no second copy.
_cspec = importlib.util.spec_from_file_location("veldo_metrics_core_for_reads",
                                                ROOT / ".veldo" / "metrics.py")
_core = importlib.util.module_from_spec(_cspec)
_cspec.loader.exec_module(_core)
_sibling = _core._sibling

# The DECLARED CONTRACT: the two read constructors that are the only way to affirm or to decline, the ONE
# decision that judges them, and the one string primitive that makes a name renderable on any stream. No
# source id is spelled twice: the literals the readers pass in ARE the table's rows, and a selftest asserts
# the union of the literals across the pass IS the table.
_ctspec = importlib.util.spec_from_file_location("veldo_metrics_support_contract_for_reads",
                                                 ROOT / ".veldo" / "metrics_support_contract.py")
_contract = importlib.util.module_from_spec(_ctspec)
_ctspec.loader.exec_module(_contract)
_is_str = _contract._is_str
printable = _contract.printable
read_complete = _contract.read_complete
read_incomplete = _contract.read_incomplete
read_proves_complete = _contract.read_proves_complete

# THE DECLARED SKIP RULE, the ONE plane this module asks about a single directory ENTRY: the table of names
# a store may hold that are not records, the KIND test a name may only be applied through, and the describer
# an unaccounted entry is named by. It was SPLIT OUT of this module when the round-8 hardening would not fit
# the declared bound: a DECLARATION an adopter reads and may extend is not the same thing as the MECHANISM
# that accounts a read, they share exactly the two call sites below, and compressing the declaration to make
# room would have been the wrong answer to a bound.
_skspec = importlib.util.spec_from_file_location("veldo_metrics_skip_rule_for_reads",
                                                 ROOT / ".veldo" / "metrics_skip_rule.py")
_skip = importlib.util.module_from_spec(_skspec)
_skspec.loader.exec_module(_skip)
SUPPORT_STORE_SKIP = _skip.SUPPORT_STORE_SKIP
SUPPORT_STORE_SKIP_MAX_DEPTH = _skip.SUPPORT_STORE_SKIP_MAX_DEPTH
_SUPPORT_SKIP_MATCH = _skip._SUPPORT_SKIP_MATCH
store_skip_reason = _skip.store_skip_reason
_skippable_entry = _skip._skippable_entry
_entry_kind = _skip._entry_kind
_unaccounted_detail = _skip._unaccounted_detail


def _problem(source, subject, detail):
    """One reader problem in the shape the derivation NAMES from SUPPORT_SOURCES: the declared source, the subject
    that failed (a path or a file name), and the detail. No reason name is written here (the table owns the
    taxonomy), and a problem is a record, never a bare string nobody reads. The SUBJECT is a filesystem name
    and the DETAIL quotes what was read, so both pass through printable(): one unencodable byte in this
    record used to exit the two surfaces that PRINT it at the print. This is ONE of the two INGEST
    boundaries (the other is the contract's two read constructors), and between them every name this pass
    enumerates is printable in the MODEL, before any surface is asked to render it."""
    return {"source": source, "subject": printable(subject), "detail": printable(detail)}


def _keep(reads, read):
    """Hand ONE read record to the accumulator the derivation will judge, and return it. A reader that
    never calls this leaves its source with NO read at all, which support_completeness() treats as
    INCOMPLETE - so wiring a reader is not optional and forgetting one fails closed."""
    if isinstance(reads, list):
        reads.append(read)
    return read


def _present(path):
    """WHETHER A DIRECTORY ENTRY EXISTS AT THIS PATH, decided by os.lstat and never by exists() or
    is_dir(). This is the primitive three reviews' worth of misclassification came from: exists() and
    is_dir() FOLLOW the link and swallow the error, so a SYMLINK LOOP and a DANGLING SYMLINK both answer
    False while the entry is plainly there, and the source was then reported ABSENT. lstat looks at the
    entry itself. An OSError that is not FileNotFoundError (a loop, an unreadable parent directory) means
    the entry cannot even be stat'ed, which is PRESENT and unreadable rather than absent: fail closed."""
    try:
        os.lstat(str(path))
    except FileNotFoundError:
        return False
    except (OSError, ValueError, RecursionError, MemoryError):
        # THE FOUR DECLARED CLASSES A READ OF A RECORDED ARTIFACT NAMES, identical at every such site in the
        # pass rather than chosen here: a path the platform refuses (an embedded NUL) raises ValueError, and
        # one of the four escaping would take the whole surface down instead of standing this source down.
        return True
    return True


def _accounted_dir(source, path, suffix):
    """(the entries this reader will consume, the READ RECORD) for ONE directory source, ENUMERATED AND
    ACCOUNTED rather than globbed.

    An ABSENT directory is COMPLETE and empty (adoption safe). A directory that cannot be ENUMERATED is
    INCOMPLETE: os.listdir raises where glob returns an empty iterator, which is the whole difference
    between a mode-000 store standing the section down and a mode-000 store reading as an empty one.
    Every enumerated entry must be a file whose suffix is exactly `suffix` - a SYMLINK that resolves to one
    INCLUDED, because isfile follows the link - or an entry the DECLARED SKIP RULE names AND may be applied
    to (a .gitkeep, a README, an editor swapfile, an empty archive/); anything else - a subdirectory that
    holds something this read cannot dismiss, a symlink the suffix branch did not consume, a FIFO, a named
    pipe's sibling kinds, another suffix, a case variant - is UNACCOUNTED and leaves the read INCOMPLETE
    with the entries named. A record this pass never opened is not an absent record, and that is the whole
    item.

    THE TWO BRANCHES BELOW TREAT A SYMLINK DIFFERENTLY, deliberately: the CONSUME branch asks isfile, which
    FOLLOWS the link, so a symlink NAMED as a record and resolving to one IS read and counted; the SKIP
    branch refuses a link whatever it resolves to, because dismissing an entry UNREAD on the strength of a
    target that can change after the check is the shape that lost a record. Reading a resolved record is
    safe; declining to read one on its target's word is not.

    THE THIRD BRANCH DISMISSES A DIRECTORY UNREAD ON AN ENUMERATION THAT CAN CHANGE IDENTICALLY, so its
    window is NAMED here rather than left to the symlink paragraph: from the enumeration of that subtree to
    the moment the model renders, a record written under a dismissed directory is not in this read. That
    stays TRUE of the store as it was enumerated, the NEXT read stands the section down by name, and every
    read of a filesystem carries the same window (a consumed record can be appended to a microsecond after
    it is parsed). What makes it acceptable where the symlink case is not: the fact checked IS a fact about
    the entry, enumerated through the entry at every level and never through a link, so the walk cannot
    leave the subtree - where a link's target is a DIFFERENT object the entry does not contain, and refusing
    links rests on a MEASURED loss besides. The walk is bounded at SUPPORT_STORE_SKIP_MAX_DEPTH levels.

    A SKIPPED ENTRY IS STILL ACCOUNTED: counted and NAMED with the declared reason in this read's basis AND
    in the read record's own `skipped` list, which the derivation carries into the model and all three
    surfaces render, so "not read" is visible rather than silent. Without the rule ONE .gitkeep stood the
    whole section down permanently, which is a cost availability cannot carry and honesty does not require;
    without its KIND half an archive/ holding a record was skipped and the record was LOST while the
    section rendered, which honesty does not permit either."""
    if not _present(path):
        return [], read_complete(source, str(path),
                                 "ABSENT: no directory entry exists at this path (lstat), so there is "
                                 "nothing here to read and nothing here to miss")
    if not os.path.isdir(str(path)):
        # PRESENT and not a directory, named as its own fact rather than as a failed enumeration: this is
        # the shape that raises nothing at all and simply yields an empty index, which makes it the one
        # most likely to read as an honest absence.
        return [], read_incomplete(source, str(path),
                                   "the path EXISTS and is not a directory (%s), so nothing here can be "
                                   "read and no entry can be accounted for: present and unreadable, "
                                   "never an absent store" % _entry_kind(path))
    try:
        names = sorted(os.listdir(str(path)))
    except (OSError, ValueError, RecursionError, MemoryError) as exc:
        return [], read_incomplete(source, str(path),
                                   "the path EXISTS and could NOT be enumerated (%s: %s), so nothing "
                                   "here can say what it holds: a directory this pass cannot list is "
                                   "never an empty one" % (type(exc).__name__, exc))
    consume, skipped, unaccounted = [], [], []
    for name in names:
        entry = Path(path) / name
        # THE SUFFIX IS ASKED FIRST, so no skip row can take a record out of the read: a file that IS a
        # record is consumed even if its name also matches a declared non-record pattern.
        if name.endswith(suffix) and os.path.isfile(str(entry)):
            consume.append(entry)
            continue
        try:
            dismissible = _skippable_entry(entry, suffix) and store_skip_reason(name) is not None
        except (RecursionError, MemoryError):
            # DEFENCE IN DEPTH BEHIND THE SKIP RULE'S OWN DEPTH BOUND, which should make the first of these
            # unreachable. Neither is an OSError or a ValueError: at round 8 an unbounded walk raised
            # RecursionError past every handler and exited all four surfaces printing nothing (R8-B1), and a
            # listdir too large for the memory the process may have raises MemoryError the same way (R9-B1's
            # class). A guard that cannot answer means UNACCOUNTED: one entry's dismissal, not four surfaces.
            dismissible = False
        if dismissible:
            skipped.append("%s (%s)" % (name, store_skip_reason(name)))
        else:
            unaccounted.append(_unaccounted_detail(name, entry))
    accounted = ("; SKIPPED as the declared non-records this store may hold: %s" % ", ".join(skipped)
                 if skipped else "")
    if unaccounted:
        return consume, read_incomplete(
            source, str(path),
            "the directory holds %d of %d entry(ies) this reader consumes %s files and cannot account "
            "for the rest: %s. An entry nobody opened is NOT an absent record, so this read is INCOMPLETE "
            "rather than a shorter one%s"
            % (len(consume), len(names), suffix, ", ".join(unaccounted), accounted))
    return consume, read_complete(
        source, str(path), "ACCOUNTED: %d of the %d enumerated entry(ies) is a %s file this reader "
        "consumed, so nothing in this directory went unread%s" % (len(consume), len(names), suffix,
                                                                 accounted),
        # THE SKIPPED ENTRIES AS DATA rather than as basis prose alone: the model carries them and all three
        # surfaces render them, which is what makes "a human can see what was not read" true.
        skipped=skipped)


def _parsed_shortfall(source, path, problems, total):
    """The read record for a directory whose entries were all ACCOUNTED and some could not be PARSED: a
    partially parsed collection is INCOMPLETE, and every file that failed is named on its own beside it.
    Round 4's rule, applied: absent is complete, and everything else has to be affirmed."""
    named = [str(p.get("subject")) if isinstance(p, dict) else "an entry whose problem record was lost"
             for p in problems]
    return read_incomplete(source, str(path),
                           "%d of the %d accounted entry(ies) could NOT be read or parsed (%s), so this "
                           "collection was read in PART: the entries that did parse are not a complete "
                           "read of it" % (len(problems), total, ", ".join(named)))


def _record_shortfall(read):
    """(the parsed RECORD, None) or (None, WHY it is not one) for ONE recorded artifact - a receipt file's
    bytes, or ONE line of the event stream - read and parsed by the caller's `read` thunk.

    ONE ANSWER TO "IS THIS A RECORD" FOR BOTH, which is round 5's note 6: a receipt file that parsed to a
    list was NAMED and an event line that did was accepted in SILENCE, and a text that is not a record is
    the same fact whichever store it came from. The CALLER names it against its own source with its own
    consequence, so the two details stay honest about what the loss costs. ALL FOUR DECLARED CLASSES ARE
    NAMED HERE, at the pass's ONE read of an INJECTED THUNK that cannot know what it does: ValueError for a
    byte the declared codec cannot decode (it took the WHOLE dashboard down); RECURSION ERROR because
    json.loads recurses per nesting level, so 20000 nested arrays in a receipt file or an event line raised
    a RuntimeError neither of the first two catches out of ALL FOUR SURFACES (round 9); and MEMORY ERROR
    because an artifact larger than the memory the process may have does the same and was named NOWHERE in
    this repository until round 10 (measured: a SPARSE receipt file, one truncate and ZERO bytes on disk,
    exited all four surfaces 1 with zero stdout under 4 GiB). No stack, no allocator, no record: NAMED."""
    try:
        record = read()
    except (OSError, ValueError, RecursionError, MemoryError) as exc:
        return None, "could not be read or parsed (%s: %s)" % (type(exc).__name__, exc)
    if not isinstance(record, dict):
        return None, "parses to a %s rather than a record (mapping)" % type(record).__name__
    return record, None


def _dependency_declined(source, subject, depends_on, reads=None):
    """DECLINE one source's affirmation because a source it DEPENDS ON did not prove a complete read, and
    say which one. A dependent read that affirmed anyway would be the same lie one level up: "the series
    holds no cost" when the truth is that the index the join needs was never read."""
    return _keep(reads, read_incomplete(
        source, subject, "this source could not be read COMPLETELY because %s did not prove a complete "
        "read, and a figure derived from a source that was not fully read is not an absence of data: "
        "declined here rather than reported as empty" % depends_on))
