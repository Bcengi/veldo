#!/usr/bin/env python3
"""VELDO support numbers: THE DECLARED READ UNIT AND ITS KIND (WARP-1210, round 11).

THE DEFECT CLASS THIS MODULE EXISTS TO CLOSE, keyed on WHAT THE ITEM DECLARES
rather than on how the code happens to reach it: A DECLARED SOURCE BECOMES
UNAVAILABLE AND SOME SURFACE PRINTS NOTHING AT ALL. Three rounds drew that
boundary from a MECHANISM and each was one name short:

  * ROUND 8 keyed the sweep on RECURSION and missed two members.
  * ROUND 9 keyed it on the EXCEPTION CLASSES and missed two more.
  * ROUND 10 keyed it on THE READ PRIMITIVE THAT TOUCHES THE ARTIFACT and
    enumerated thirteen names. A MODULE LOAD is a read of a file that none of
    those thirteen name, so two DECLARED SOURCES (.veldo/entropy.py and
    .veldo/validate.py) still exited BOTH dashboard surfaces 1 with ZERO bytes of
    stdout while the two metrics surfaces named them correctly; and a read that
    BLOCKS raises nothing at all, so a FIFO at .veldo/events.jsonl hung ALL FOUR
    surfaces FOREVER, with no output, no exit code and no exception for any
    handler to name.

A RULE QUANTIFIED OVER PRIMITIVES IS ALWAYS ONE NAME SHORT. This pass already
publishes a CLOSED TABLE of THIRTEEN SOURCES (metrics_support_contract.py
SUPPORT_SOURCES), which is ours to enumerate, so the rule is keyed on that table:
EVERY DECLARED SOURCE HAS A READ UNIT here, and the KIND of that unit is asked
before anything opens it.

THE UNIVERSAL THAT STOOD IN THIS DOCSTRING AT ROUND 11 IS DELETED RATHER THAN
REWORDED, because it was measurably false. It read "every code path that can make
one unavailable answers with that source's own name on all four surfaces, HOWEVER
the unit is reached and WHETHER the failure raises or BLOCKS", and FOUR code paths
refuted it: the owner this pass hands specs/ to opens proof/*/manifest.json,
proof/*/verdict*.json, plans/*.md and .veldo/decisions/*.yaml with a bare
read_text(), and a FIFO at any of them hung ALL FOUR SURFACES FOREVER with the
declared source naming nothing at all. A READ UNIT IS WHERE A DELEGATED READ
STARTS, NOT WHERE IT STOPS. The DOMAIN is the TRANSITIVE CLOSURE of what is opened
ON THIS PASS'S BEHALF; it is declared, and proven complete by MEASUREMENT rather
than by reading an owner's code, in .veldo/metrics_read_closure.py. This module
answers only the narrower question it can answer: WHAT ONE ENTRY IS.

  SUPPORT_READ_UNITS      the READ UNIT of each of the thirteen declared sources
  unopenable(unit)        the NAMED reason a unit may not be OPENED at all
  unopenable_entry(store) the same question asked of a STORE's own entries

WHY A KIND TEST AND NOT A HANDLER, which is the part a later round must not
undo: a blocking open raises NOTHING. There is no exception name for it, so no
handler and no declared exception set can reach it, and a gate rule keyed on
handlers is STRUCTURALLY BLIND to it. The only answer is to ASK WHAT THE ENTRY IS
BEFORE OPENING IT, which is the predicate the support pass's own reader of the
event stream has carried since round 4 (metrics_readers.load_events, os.path
.isfile) and which round 10 did not adopt when it aligned the loop reader with
that reader's PRESENCE primitive. A HANG IS WORSE THAN A CRASH: a crash writes a
traceback and fails a CI job, while a wedged process writes nothing, never
returns and holds the terminal, so the surface matrix in scripts/selftest.py runs
every cell under a TIMEOUT and treats exceeding it as a failure.

WHAT IS REFUSED AND WHAT IS DELIBERATELY NOT, measured rather than assumed:

  A REGULAR FILE and a DIRECTORY are never refused here. Opening a directory
  RAISES IsADirectoryError, which every reader of this pass already names with
  its message, and refusing it here would replace a good diagnosis with a
  weaker one.
  AN ENTRY THAT CANNOT BE RESOLVED AT ALL (a symlink LOOP, a DANGLING symlink) is
  not refused here either: os.stat RAISES on it, the read raises the same class,
  and every reader already names it. Refusing it would change what a pre-existing
  shape reports for no gain in safety.
  EVERYTHING ELSE THAT RESOLVES (a FIFO, a named pipe's sibling kinds, a
  character or block device, and a symlink to any of them) IS REFUSED, because a
  whole-file read of one BLOCKS, and that is the only shape no handler can reach.

Reads nothing and opens nothing: no live system (NG1), no process, thread or
timer (NG3), and nothing is written anywhere.
"""
import importlib.util
import os
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# THE ACCOUNTED READ, bound at import for its PRESENCE primitive (os.lstat, never exists()), its ENTRY
# DESCRIBER and the one string primitive that makes a filesystem name printable on any stream. One direction
# of dependency (contract, accounting, THIS, owners, shape, evidence readers) and no second copy of any of
# the three: this module adds the KIND question to that plane and restates nothing already answered there.
_aspec = importlib.util.spec_from_file_location("veldo_metrics_read_accounting_for_kind",
                                                ROOT / ".veldo" / "metrics_read_accounting.py")
_accounting = importlib.util.module_from_spec(_aspec)
_aspec.loader.exec_module(_accounting)
_present = _accounting._present
_entry_kind = _accounting._entry_kind
printable = _accounting.printable

# THE READ UNIT OF EVERY ONE OF THE THIRTEEN DECLARED SOURCES: the filesystem object whose unavailability
# that source's own name is supposed to report, and WHERE the gate stands over it. This table is the SWEEP'S
# KEY, and it is derived from the DECLARATION rather than from any vocabulary of primitives, so a new way of
# reading a unit cannot make the rule go stale. THREE ROWS DECLARE NO UNIT OF THEIR OWN and say which row's
# unit they ride on, because a source derived from another source's bytes cannot fail on its own: naming an
# inherited unit is what keeps the table CLOSED over the thirteen without inventing a fourteenth file.
#   file   read WHOLE by this pass or by an owner it hands the path to
#   store  ENUMERATED by this pass, whose ENTRIES an owner may then open
#   None   derived from another row's unit, named in `inherits`
SUPPORT_READ_UNITS = (
    {"source": "architecture_contract", "unit": ".veldo/architecture.yaml", "kind": "file",
     "inherits": None, "gated_at": ".veldo/metrics_shape_readers.py:_read_contract"},
    {"source": "spec_corpus", "unit": "specs", "kind": "store", "inherits": None,
     "gated_at": ".veldo/metrics_shape_readers.py:_read_corpus"},
    {"source": "spec_area_index", "unit": "specs", "kind": "store", "inherits": None,
     "gated_at": ".veldo/metrics_shape_readers.py:_read_area_index"},
    {"source": "receipt_store", "unit": ".veldo/reconciliations", "kind": "store", "inherits": None,
     "gated_at": ".veldo/metrics_read_accounting.py:_accounted_dir"},
    {"source": "incident_record_store", "unit": ".veldo/incidents", "kind": "store", "inherits": None,
     "gated_at": ".veldo/metrics_read_accounting.py:_accounted_dir"},
    {"source": "area_cost_series", "unit": None, "kind": None, "inherits": "entropy_series_owner",
     "gated_at": ".veldo/metrics_owner_reads.py:_owner"},
    {"source": "incident_vocabulary", "unit": ".veldo/incident.py", "kind": "file", "inherits": None,
     "gated_at": ".veldo/metrics_owner_reads.py:_owner"},
    {"source": "incident_timeline", "unit": None, "kind": None, "inherits": "incident_record_store",
     "gated_at": ".veldo/metrics_read_accounting.py:_accounted_dir"},
    {"source": "event_stream", "unit": ".veldo/events.jsonl", "kind": "file", "inherits": None,
     "gated_at": ".veldo/metrics_event_stream.py:read_stream"},
    {"source": "incident_contract_owner", "unit": ".veldo/incident.py", "kind": "file", "inherits": None,
     "gated_at": ".veldo/metrics_owner_reads.py:_owner"},
    {"source": "front_matter_parser", "unit": ".veldo/validate.py", "kind": "file", "inherits": None,
     "gated_at": ".veldo/metrics_owner_reads.py:_owner"},
    {"source": "intent_corpus_owner", "unit": ".veldo/intent_corpus.py", "kind": "file", "inherits": None,
     "gated_at": ".veldo/metrics_owner_reads.py:_owner"},
    {"source": "entropy_series_owner", "unit": ".veldo/entropy.py", "kind": "file", "inherits": None,
     "gated_at": ".veldo/metrics_owner_reads.py:_owner"},
)

# THE ONE SENTENCE for a unit no read may open. It carries the PATH, WHAT THE ENTRY IS (the describer the
# accounted read already uses, so the two planes say the same words) and WHY nothing here opens it, because a
# refusal an operator cannot act on is the same silence in a different place.
KIND_UNOPENABLE = ("%s EXISTS and is NEITHER A REGULAR FILE NOR A DIRECTORY (%s), so nothing here may OPEN "
                   "it: a whole-file read of such an entry BLOCKS until a writer appears rather than "
                   "raising, which no exception name can catch and which exits a surface with nothing "
                   "printed, no exit code and no traceback at all")
KIND_STORE_UNOPENABLE = ("the store %s holds %d of %d enumerated entry(ies) NO read may OPEN (%s), so this "
                         "read is NOT handed to the owner that would open them: a whole-file read of such "
                         "an entry BLOCKS until a writer appears rather than raising, which no exception "
                         "name can catch and which exits a surface with nothing printed at all")


def unopenable(unit):
    """The NAMED reason this READ UNIT may not be OPENED because of WHAT IT IS, or "" when nothing here
    refuses it.

    ABSENT IS NOT REFUSED: a repository that ships no such artifact is complete and empty, which every
    reader of this pass decides for itself and which must stay adoption safe. AN ENTRY THAT CANNOT BE
    RESOLVED is not refused either, and that is deliberate rather than an omission: os.stat RAISES on a
    symlink LOOP and on a DANGLING symlink, the read raises the same class one line later, and every reader
    already NAMES it with its message - refusing it here would change what a pre-existing shape reports and
    buy nothing, because a read that raises is a read that produced a diagnosis."""
    if not _present(unit):
        return ""
    try:
        mode = os.stat(str(unit)).st_mode
    except (OSError, ValueError, RecursionError, MemoryError):
        return ""
    if stat.S_ISREG(mode) or stat.S_ISDIR(mode):
        return ""
    return KIND_UNOPENABLE % (printable(str(unit)), _entry_kind(unit))


def unopenable_entry(store, suffix=None):
    """The NAMED reason a STORE may not be handed to an owner that will OPEN its entries, or "". With a
    SUFFIX, only the entries bearing it are asked about, which is how the ENGINE's own organs are swept
    without the DATA that sits in the same directory answering for them.

    The accounted read already refuses to CONSUME such an entry itself (it asks isfile at every entry and
    leaves anything else UNACCOUNTED), so this is the half that was missing: a store this pass enumerates and
    then DELEGATES is opened by the owner under the owner's own name rule, and one FIFO among the specs hung
    all four surfaces forever while this pass's own read record already said the entry was unaccounted. A
    store nobody can ENUMERATE returns "" here: that is the accounted read's own answer to give, and two
    sentences for one fact are two that can disagree."""
    try:
        names = sorted(os.listdir(str(store)))
    except (OSError, ValueError, RecursionError, MemoryError):
        return ""
    refused = [n for n in names
               if (suffix is None or n.endswith(suffix)) and unopenable(Path(store) / n)]
    if not refused:
        return ""
    return KIND_STORE_UNOPENABLE % (
        printable(str(store)), len(refused), len(names),
        ", ".join("%s (%s)" % (printable(n), _entry_kind(Path(store) / n)) for n in refused))
