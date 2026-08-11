#!/usr/bin/env python3
"""VELDO support numbers: THE TRANSITIVE CLOSURE OF A DELEGATED READ (WARP-1210, round 12).

THE DEFECT CLASS THIS MODULE EXISTS TO CLOSE is the half round 11 got wrong. Round
11 keyed the sweep on WHAT THE ITEM DECLARES rather than on the mechanism its code
happens to reach the artifact by, which was the correction three rounds had needed,
and the sweep that key produced found the hang at SIX declared read units where the
report named ONE. What it then quantified over was THE FILESYSTEM OBJECT THIS PASS
OPENS ITSELF. Six of the thirteen declared rows are DELEGATED, and for a delegated
row that object is where the read STARTS rather than the whole read:

  * MEASURED, 16 of 16 surface runs: a FIFO at proof/*/manifest.json,
    proof/*/verdict*.json, plans/*.md or .veldo/decisions/*.yaml HUNG ALL FOUR
    SURFACES FOREVER - zero bytes, no exit code, killed by a clock - because the
    kind test in front of the corpus hand-off asked about the entries of specs/
    only, while the OWNER it hands that read to opens four more roots with a bare
    read_text() and no predicate in front of any of them.
  * MEASURED, 16 of 16: so did a FIFO at the BYTECODE CACHE of an engine organ. A
    module LOAD opens the cache as well as the source, and the organ sweep in front
    of an owner load asked about the source alone.

THE DOMAIN OF A DELEGATED READ IS THE TRANSITIVE CLOSURE OF WHAT IS OPENED ON THIS
PASS'S BEHALF, and that is what this module declares. Every hand-off publishes its
closure ROOT BY ROOT with the owner, the call and WHERE each root's kind question is
asked, and the closure is PROVEN COMPLETE BY MEASUREMENT rather than by reading an
owner's code: the selftest runs each hand-off in a child under an interpreter AUDIT HOOK
installed BEFORE that process's first in-tree open, so the owner IMPORT is observed as
well as the owner CALL, and asserts that no path opened INSIDE THE TREE lies outside the
declared roots - so an owner that begins opening a new in-tree root fails the gate
instead of wedging a surface. A path OUTSIDE the tree is DISCARDED and nothing here is
claimed about it. THE HOOK IS PROVEN NOT BLIND BY ATTEMPTING an undeclared open at
IMPORT and at CALL time and requiring both to be caught rather than by reading its own
source. A closure a human enumerated is exactly the artifact that was one name short
four rounds running.

  SUPPORT_DELEGATED_CLOSURE     the closure of each hand-off, root by root
  unopenable_under(root, row)   the NAMED reason a path under one of a hand-off's
                                OWN roots may not be OPENED at all
  unopenable_cached(store, sfx) the same question asked of an organ's BYTECODE
                                CACHE, because a module load opens two files
  delegated(gate, root, call)   the ONE way a declared source's read is handed to
                                an ENGINE OWNER: the UNIT's kind, then EVERY root
                                of the closure this boundary owns, then the whole
                                Exception family, so an owner can neither BLOCK nor
                                RAISE past the boundary

WHY THE UNIT COMES OUT OF THE DECLARATION AND NOT OUT OF THE CALLER, which is the
structural half of the fix and the part a later round must not undo: round 11's
boundary took the unit as an ARGUMENT, so the guard was only ever asked about what
the caller remembered to hand it, and a domain that depends on a caller's memory is
the same defect in a new place. Here a caller names its DELEGATION and the boundary
derives the unit, the unit's kind and every root of the closure from this table. A
caller cannot ask the question about the wrong thing, a hand-off this table does not
declare is REFUSED rather than passed through, and an IN-TREE root nobody declared is a
GATE FAILURE rather than a hang.

Reads nothing and opens nothing: no live system (NG1), no process, thread or timer
(NG3), and nothing is written anywhere.
"""
import importlib.util
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# THE DECLARED READ UNIT AND ITS KIND, bound at import and RE-EXPORTED for the plane above: the thirteen-row
# table, the one predicate that answers whether an entry may be OPENED at all, its STORE form, the entry
# describer and the one string primitive that makes a filesystem name printable on any stream. ONE direction
# of dependency (contract, accounting, kind, THIS, owners, shape, evidence readers) and no second copy of any
# predicate: this module adds the DOMAIN question to that plane and restates no answer already given there.
_kspec = importlib.util.spec_from_file_location("veldo_metrics_read_kind_for_closure",
                                                ROOT / ".veldo" / "metrics_read_kind.py")
_kind = importlib.util.module_from_spec(_kspec)
_kspec.loader.exec_module(_kind)
SUPPORT_READ_UNITS = _kind.SUPPORT_READ_UNITS
KIND_UNOPENABLE = _kind.KIND_UNOPENABLE
KIND_STORE_UNOPENABLE = _kind.KIND_STORE_UNOPENABLE
unopenable = _kind.unopenable
unopenable_entry = _kind.unopenable_entry
_entry_kind = _kind._entry_kind
printable = _kind.printable

# THE TRANSITIVE CLOSURE OF EVERY HAND-OFF, one row per DELEGATION: the GATE (which is the declared source
# the loss is charged to), the READ UNIT this pass names it by and that unit's KIND, the OWNER and the CALL
# that do the reading, and EVERY ROOT that call opens ON THIS PASS'S BEHALF together with WHERE that root's
# kind question is asked. The roots are glob patterns relative to the repository being MEASURED, except the
# engine's own organs, which are resolved against the ENGINE the owners are loaded from (an owner is engine
# code, a data source is the measured tree, and metrics_owner_reads.py owns that distinction).
#   HERE   this boundary asks unopenable() at every path the pattern matches, before the hand-off
#   STORE  this boundary asks unopenable_entry() over the whole store, which is BROADER than the pattern
#   UNIT   the same path is another declared row's own READ UNIT, asked at that row's own gate, and the
#          owner also asks a presence predicate of its own before opening it
#   ORGAN  an engine .py organ or its BYTECODE CACHE, swept in front of EVERY owner load
#   OPENER the opener itself cannot BLOCK on that path, because it asks a predicate of its own before
#          opening (entropy's is_file filter over the contract's area files) or opens O_CREAT|O_EXCL, which
#          FAILS on an existing entry rather than blocking on it (importlib's cache write)
# ONE root is not expressible as a glob and is written in ANGLE BRACKETS: what the CONTRACT'S OWN area
# includes expand to, which only the contract can say. The completeness proof expands it through the owner's
# own function rather than through a second list, so a contract change cannot make this table stale.
SUPPORT_DELEGATED_CLOSURE = (
    {"gate": "architecture_contract", "unit": ".veldo/architecture.yaml", "kind": "file",
     "owner": ".veldo/validate.py", "call": "load_repo_contract", "opens": (
         (".veldo/architecture.yaml", "UNIT", ".veldo/metrics_shape_readers.py:_read_contract"),
         (".veldo/*.py", "ORGAN", ".veldo/metrics_owner_reads.py:_owner"),
         (".veldo/__pycache__/*.pyc", "ORGAN", ".veldo/metrics_owner_reads.py:_owner"),
         (".veldo/__pycache__/*.pyc.*", "OPENER", "importlib's O_EXCL cache write"))},
    {"gate": "spec_corpus", "unit": "specs", "kind": "store",
     "owner": ".veldo/intent_corpus.py", "call": "open_corpus().spec_ids", "opens": (
         ("specs/*.md", "STORE", ".veldo/metrics_shape_readers.py:_read_corpus"),
         ("proof/*/manifest.json", "HERE", ".veldo/metrics_read_closure.py:unopenable_under"),
         ("proof/*/verdict*.json", "HERE", ".veldo/metrics_read_closure.py:unopenable_under"),
         ("plans/*.md", "HERE", ".veldo/metrics_read_closure.py:unopenable_under"),
         (".veldo/decisions/*.yaml", "HERE", ".veldo/metrics_read_closure.py:unopenable_under"),
         (".veldo/architecture.yaml", "UNIT", ".veldo/metrics_shape_readers.py:_read_contract"),
         (".veldo/events.jsonl", "UNIT", ".veldo/metrics_event_stream.py:read_stream"),
         (".veldo/*.py", "ORGAN", ".veldo/metrics_owner_reads.py:_owner"),
         (".veldo/__pycache__/*.pyc", "ORGAN", ".veldo/metrics_owner_reads.py:_owner"),
         (".veldo/__pycache__/*.pyc.*", "OPENER", "importlib's O_EXCL cache write"))},
    {"gate": "spec_area_index", "unit": "specs", "kind": "store",
     "owner": ".veldo/entropy.py", "call": "spec_area_index", "opens": (
         ("specs/*.md", "STORE", ".veldo/metrics_shape_readers.py:_read_area_index"),
         (".veldo/architecture.yaml", "UNIT", ".veldo/metrics_shape_readers.py:_read_contract"),
         (".veldo/*.py", "ORGAN", ".veldo/metrics_owner_reads.py:_owner"),
         (".veldo/__pycache__/*.pyc", "ORGAN", ".veldo/metrics_owner_reads.py:_owner"),
         (".veldo/__pycache__/*.pyc.*", "OPENER", "importlib's O_EXCL cache write"))},
    {"gate": "entropy_series_owner", "unit": "specs", "kind": "store",
     "owner": ".veldo/entropy.py", "call": "entropy_report", "opens": (
         ("specs/*.md", "STORE", ".veldo/dashboard.py:entropy_figures"),
         (".veldo/architecture.yaml", "UNIT", ".veldo/metrics_shape_readers.py:_read_contract"),
         (".veldo/*.py", "ORGAN", ".veldo/metrics_owner_reads.py:_owner"),
         (".veldo/__pycache__/*.pyc", "ORGAN", ".veldo/metrics_owner_reads.py:_owner"),
         (".veldo/__pycache__/*.pyc.*", "OPENER", "importlib's O_EXCL cache write"),
         ("<the contract's own area includes>", "OPENER",
          ".veldo/entropy.py:_area_source_files (is_file)"))},
)

# THE ONE SENTENCE for a root of a closure no read may open, and the one for an organ's bytecode cache. Each
# carries the PATH, WHAT THE ENTRY IS (the describer the accounted read already uses, so every plane says the
# same words), WHOSE BEHALF the open would have happened on, and WHY nothing here opens it.
KIND_CLOSURE_UNOPENABLE = ("the read of %s is DELEGATED to %s, which also opens %s ON THIS PASS'S BEHALF, "
                           "and %d of the %d path(s) there may NOT be OPENED (%s), so this read is NOT "
                           "handed to that owner: a whole-file read of such an entry BLOCKS until a writer "
                           "appears rather than raising, which no exception name can catch and which exits "
                           "a surface with nothing printed, no exit code and no traceback at all")
KIND_CACHE_UNOPENABLE = ("%d of the %d organ(s) under %s carry a BYTECODE CACHE no read may OPEN (%s), and a "
                         "module LOAD opens the cache as well as the source, so nothing here may load an "
                         "organ: a whole-file read of such an entry BLOCKS until a writer appears rather "
                         "than raising, which no exception name can catch and which exits a surface with "
                         "nothing printed at all")


def _delegation(gate):
    """The DECLARED row for one hand-off, or None. A caller names its delegation and receives the unit, the
    kind and the closure the DECLARATION says that hand-off has; there is no argument by which a caller can
    ask the question about something else, which is the round-11 defect stated structurally."""
    for row in SUPPORT_DELEGATED_CLOSURE:
        if row["gate"] == gate:
            return row
    return None


def unopenable_under(root, row):
    """The NAMED reason a path under one of THIS hand-off's OWN roots may not be OPENED, or "".

    Only the roots this boundary OWNS (class HERE) are asked here; the others are asked at the gate the
    declaration names, and asking twice would put two sentences on one fact. A root that cannot be
    ENUMERATED answers "" for the same reason the store form does: glob() SWALLOWS a permission error and
    yields nothing, and whether a directory was read COMPLETELY is the ACCOUNTED READ's question, which must
    have ONE answer rather than two that can disagree. What this closes is the shape no accounting can
    reach - an entry whose OPEN never returns, so nothing raises and no record is ever written."""
    for pattern, kind, _where in row["opens"]:
        if kind != "HERE":
            continue
        try:
            matched = sorted(Path(root).glob(pattern))
        except (OSError, ValueError, RecursionError, MemoryError):
            continue
        refused = [p for p in matched if unopenable(p)]
        if refused:
            return KIND_CLOSURE_UNOPENABLE % (
                printable(str(Path(root) / row["unit"])), row["owner"], pattern,
                len(refused), len(matched),
                ", ".join("%s (%s)" % (printable(str(p)), _entry_kind(p)) for p in refused))
    return ""


def unopenable_cached(store, suffix):
    """The NAMED reason the BYTECODE CACHE of a store's own SOURCE organs may not be OPENED, or "".

    A MODULE LOAD IS TWO READS, and the organ sweep asked only one of them: importlib opens the SOURCE and,
    when a cache for that source exists, the CACHE that stands in for it - measured, a FIFO at
    .veldo/__pycache__/validate.cpython-312.pyc hung ALL FOUR SURFACES FOREVER exactly as a FIFO at
    .veldo/validate.py did, and for the same structural reason. cache_from_source is the ONE place that
    mapping is computed and it honours PYTHONPYCACHEPREFIX, so this asks about the path the loader will
    really open rather than about a __pycache__ literal that is right on one machine. An ABSENT cache is not
    refused, because nothing opens what is not there."""
    try:
        names = sorted(os.listdir(str(store)))
    except (OSError, ValueError, RecursionError, MemoryError):
        return ""
    try:
        cached = [importlib.util.cache_from_source(str(Path(store) / n))
                  for n in names if n.endswith(suffix)]
    except Exception:
        # THE INTERPRETER'S OWN MAPPING, and this pass may not enumerate what it raises: an implementation
        # with no cache_tag at all refuses to name a cache path, and one that names none OPENS none, so
        # there is nothing here to refuse. Its own try rather than a FIFTH name in the declared four.
        return ""
    refused = [c for c in cached if unopenable(c)]
    if not refused:
        return ""
    return KIND_CACHE_UNOPENABLE % (
        len(refused), len(cached), printable(str(store)),
        ", ".join("%s (%s)" % (printable(c), _entry_kind(c)) for c in refused))


def delegated(gate, root, call, refused=None):
    """(the OWNER'S ANSWER, "") or (`refused`, the NAMED reason) - THE ONE WAY this pass hands a DECLARED
    SOURCE'S read to an ENGINE OWNER, so an owner can neither BLOCK nor RAISE past the boundary. The caller
    names its DELEGATION and states the EMPTY value of its own source (no spec id, no area) rather than
    testing for None; the UNIT, its KIND and its CLOSURE all come out of the declaration.

    THREE REFUSALS AND NOTHING ELSE. The KIND of the UNIT, because a read that BLOCKS raises nothing and no
    handler, no declared exception set and no `except Exception` can reach it. Then EVERY ROOT OF THE CLOSURE
    this boundary owns, because the unit is where the owner STARTS and not where it stops: four roots the
    corpus owner opens with a bare read_text() wedged all four surfaces forever while the unit itself was
    perfectly readable. Then the whole Exception family, because this pass cannot know what an owner's own
    read of its own files can raise - the owners decode through the LOCALE's codec, parse with their own
    predicates and load organs of their own, and every one of those is outside this item's footprint.

    A HAND-OFF THIS TABLE DOES NOT DECLARE IS REFUSED, not passed through: the domain of a delegated read is
    a DECLARATION, and a call site that has none has no domain to be checked against. The caller NAMES the
    refusal against ITS OWN declared source and states what the loss costs that source, which is why this
    returns a reason rather than a read record: one boundary, thirteen declared sources, and no source
    charged for another's failure (round 4's finding)."""
    row = _delegation(gate)
    if row is None:
        return refused, ("the hand-off %r declares no READ CLOSURE, so nothing is handed to an owner: the "
                         "domain of a delegated read is a declaration and this one has none" % gate)
    unit = Path(root) / row["unit"]
    refusal = (unopenable_entry(unit) if row["kind"] == "store" else unopenable(unit)) \
        or unopenable_under(root, row)
    if refusal:
        return refused, refusal
    try:
        return call(), ""
    except Exception as exc:
        return refused, "%s: %s" % (type(exc).__name__, exc)
