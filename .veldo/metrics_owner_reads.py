#!/usr/bin/env python3
"""VELDO support numbers: THE ENGINE OWNERS THIS PASS EXECUTES (WARP-1210).

The support pass reads two different kinds of thing, and this module owns the
second kind. Eight DATA sources are read at the repository `root` being measured
(.veldo/metrics_read_accounting.py owns what makes such a read COMPLETE), and four
SIBLING OWNER MODULES are EXECUTED out of the ENGINE that is doing the measuring:

  ENGINE                  the engine whose organs this pass loads, distinct from
                          the `root` whose data it reads
  SUPPORT_OWNERS          the four owners, each a DECLARED SOURCE of its own
  _owner(row) / load_owners()   loaded by path, ONCE per pass
  _owners_for(owners)     the mapping a reader was given, or one it loads itself

WHY IT IS ITS OWN MODULE, and why this is a real seam rather than a place to put
the overflow: an owner is ENGINE CODE and a data source is the MEASURED
REPOSITORY, they fail in unrelated ways (an engine that does not ship an organ is
complete and empty; a repository that does not ship a store is a different fact
about a different tree), and they are resolved against different roots. Round 4
failed this item because those two planes were one: with the one parser unloadable
and the architecture contract untouched and valid, the CONTRACT was blamed with a
detail claiming it was truncated, malformed, a directory or declaring no area -
every clause untrue. Keeping the engine plane in its own module is what makes
"named as ITSELF" structural.

AN OWNER IS LOADED, AND A LOAD IS A READ (WARP-1210 round 11). Round 10 guarded
what an owner RAISES and left what an owner IS: a mode-000, sparse or wrong-kind
.veldo/entropy.py or .veldo/validate.py made the DASHBOARD exit 1 with zero bytes
of stdout while these two surfaces named the same source correctly, and a FIFO at
any of the four module paths hung EVERY surface forever, because exec_module opens
the file and a blocking open raises nothing for the handler below to catch. The
DECLARED KIND TEST (.veldo/metrics_read_kind.py) is therefore asked BEFORE the load.

IT IS ASKED OF THE WHOLE ENGINE'S ORGANS AND NOT OF A LIST OF NAMES, and that
choice is the round's method lesson applied to itself: an owner LOADS OTHER ORGANS
(.veldo/entropy.py loads the one parser at ITS module level, .veldo/incident.py and
.veldo/intent_corpus.py load it inside the functions this pass calls), so a rule
keyed on the row's own path is one name short exactly as a rule keyed on a read
primitive was. The domain that cannot go stale is the ENGINE'S OWN .py ORGANS,
enumerated at the engine being loaded from, so an entry among them that NO read may
open declines every owner load with THAT PATH NAMED. THE COST IS DECLARED: an
unopenable organ no owner would have loaded also stands these four rows down. That
is fail closed, named, and cheaper than being one name short again.

This module is also the FACADE the readers above it bind through, exactly as
.veldo/metrics_readers.py already re-exports the shape readers: one spec block per
consumer rather than two, and one accounted-read instance shared down the chain.

Reads recorded files only: no live system (NG1), no process, thread or timer
(NG3), and nothing is written anywhere.
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# THE ENGINE whose OWNER MODULES this pass executes, distinct from the repository `root` being measured.
# The parser, the record loader, the corpus index and the cost series are ENGINE CODE (exactly as this
# derivation is); every DATA source is read at `root`. Keeping them apart is what lets a temporary tree
# be measured by this engine, and what makes the owner failures reachable in a test without touching the
# engine a run depends on.
ENGINE = ROOT

# THE ACCOUNTED READ, bound at import and RE-EXPORTED for the readers above: the read-record plumbing, the
# presence primitive, the entry accounting and the two read constructors the declared contract owns. One
# direction of dependency (contract, accounting, owners, shape, evidence readers), and nothing about how a
# read is proven complete is restated here.
_aspec = importlib.util.spec_from_file_location("veldo_metrics_read_accounting_for_owners",
                                                ROOT / ".veldo" / "metrics_read_accounting.py")
_accounting = importlib.util.module_from_spec(_aspec)
_aspec.loader.exec_module(_accounting)
_core = _accounting._core
_sibling = _core._sibling
_is_str = _accounting._is_str
_problem = _accounting._problem
_keep = _accounting._keep
_present = _accounting._present
_entry_kind = _accounting._entry_kind
_accounted_dir = _accounting._accounted_dir
_parsed_shortfall = _accounting._parsed_shortfall
_record_shortfall = _accounting._record_shortfall
_dependency_declined = _accounting._dependency_declined
printable = _accounting.printable
read_complete = _accounting.read_complete
read_incomplete = _accounting.read_incomplete
read_proves_complete = _accounting.read_proves_complete

# THE DECLARED READ UNIT, ITS KIND AND THE CLOSURE OF EVERY HAND-OFF, bound here and RE-EXPORTED for the
# readers above: the table that says what each of the thirteen declared sources reads, the one predicate that
# answers whether an entry may be OPENED at all, the TRANSITIVE CLOSURE of what each hand-off's owner opens
# on this pass's behalf, and the ONE delegation boundary an engine owner is reached through. The CLOSURE
# module is the facade for the KIND module below it, so the rule has one instance and one declaration.
_clspec = importlib.util.spec_from_file_location("veldo_metrics_read_closure_for_owners",
                                                 ROOT / ".veldo" / "metrics_read_closure.py")
_closure = importlib.util.module_from_spec(_clspec)
_clspec.loader.exec_module(_closure)
SUPPORT_READ_UNITS = _closure.SUPPORT_READ_UNITS
SUPPORT_DELEGATED_CLOSURE = _closure.SUPPORT_DELEGATED_CLOSURE
KIND_UNOPENABLE = _closure.KIND_UNOPENABLE
KIND_STORE_UNOPENABLE = _closure.KIND_STORE_UNOPENABLE
unopenable = _closure.unopenable
unopenable_entry = _closure.unopenable_entry
unopenable_cached = _closure.unopenable_cached
unopenable_under = _closure.unopenable_under
delegated = _closure.delegated

# THE SIBLING OWNERS THIS PASS EXECUTES, each a DECLARED SOURCE of its own so a failure in one NAMES
# ITSELF. Round 4 found this family in no row at all: with the one parser unloadable and the architecture
# contract untouched and valid, the CONTRACT was blamed, with a detail claiming it was truncated,
# malformed, a directory or declaring no area - every clause untrue. Every one of the four is a contracts
# or derivation organ: no enforcement-core organ (the executor, the whitelist, the two-key rule, the kill
# switch, the ladder) is read or loaded here, directly or transitively.
SUPPORT_OWNERS = (
    {"source": "incident_contract_owner", "module": ".veldo/incident.py",
     "as": "veldo_incident_for_metrics", "reads": "the incident record loader and its schema constant"},
    {"source": "front_matter_parser", "module": ".veldo/validate.py",
     "as": "veldo_validate_for_metrics", "reads": "the ONE front-matter parser and the contract loader"},
    {"source": "intent_corpus_owner", "module": ".veldo/intent_corpus.py",
     "as": "veldo_intent_corpus_for_metrics", "reads": "the corpus index over recorded artifacts"},
    {"source": "entropy_series_owner", "module": ".veldo/entropy.py",
     "as": "veldo_entropy_for_metrics", "reads": "the per-area cost-to-change series"},
)
# THE ENGINE'S OWN ORGANS, the domain the kind test is asked over: every .py entry of the engine's .veldo/
# directory, enumerated at the engine being loaded from rather than listed here, so no organ an owner reaches
# can be missing from it and no list can go stale. The suffix is what keeps the DATA in the same directory
# (the recorded stream, the two stores) out of this question: those are declared sources of their own.
SUPPORT_ENGINE_ORGAN_SUFFIX = ".py"


def _owner(row, reads=None):
    """(the sibling OWNER MODULE, or None) for one row of SUPPORT_OWNERS, loaded by path AS ITS OWN
    DECLARED SOURCE so a failure NAMES ITSELF. The owners are ENGINE CODE, resolved against ENGINE rather
    than against the repository being measured. An ABSENT owner is complete and empty (an engine that does
    not ship the organ), and the dependent rows say what its absence costs them; an owner that is PRESENT
    and will not load is INCOMPLETE under its OWN name, which is what round 4 required: a failure in the
    one parser is not a claim about the architecture contract.

    THE KIND TEST STANDS IN FRONT OF THE LOAD, over the row's OWN module FIRST and then over the ENGINE'S
    OWN ORGANS: exec_module OPENS the file, so a FIFO at any organ an owner reaches blocked every surface of
    both derivations forever, with nothing printed, no exit code and no exception for the handler below to
    name. The row's own module is asked first so it NAMES ITSELF when it is the offender; the engine sweep is
    what reaches the organs an owner loads that this pass never names (the one parser, under the record loader
    and under the corpus index), and it carries the offending PATH so an owner standing down for an organ it
    loads is legible as that rather than as a fault of its own.

    AND A MODULE LOAD OPENS TWO FILES, WHICH ROUND 11 ASKED ONLY HALF OF (round 12): importlib opens the
    SOURCE and, when a cache for it exists, the BYTECODE CACHE that stands in for it, so the sweep is asked
    over the organs' caches too - measured, a FIFO at .veldo/__pycache__/validate.cpython-312.pyc hung ALL
    FOUR SURFACES FOREVER exactly as a FIFO at .veldo/validate.py did. That is the same TRANSITIVE CLOSURE
    rule the delegation boundary now applies to a delegated read, asked here of a LOAD."""
    path = Path(ENGINE) / row["module"]
    blocked = (unopenable(path) or unopenable_entry(Path(ENGINE) / ".veldo", SUPPORT_ENGINE_ORGAN_SUFFIX)
               or unopenable_cached(Path(ENGINE) / ".veldo", SUPPORT_ENGINE_ORGAN_SUFFIX))
    if blocked:
        _keep(reads, read_incomplete(row["source"], row["module"],
                                     "the owner of %s may NOT be LOADED because %s, so this pass reads "
                                     "nothing through it: named as ITSELF rather than charged to whichever "
                                     "data source was being read" % (row["reads"], blocked)))
        return None
    if not _present(path):
        _keep(reads, read_complete(row["source"], row["module"],
                                   "ABSENT: this engine ships no %s, so the pass loads nothing and every "
                                   "row that depends on it says so under its own name" % row["module"]))
        return None
    try:
        owner = _sibling(row["as"], path)
    except Exception as exc:
        _keep(reads, read_incomplete(row["source"], row["module"],
                                     "the owner of %s EXISTS and could NOT be loaded (%s: %s), so this "
                                     "pass reads nothing through it: named as ITSELF rather than charged "
                                     "to whichever data source was being read"
                                     % (row["reads"], type(exc).__name__, exc)))
        return None
    _keep(reads, read_complete(row["source"], row["module"],
                               "LOADED: the owner of %s executed and its declarations are readable"
                               % row["reads"]))
    return owner


def load_owners(reads=None):
    """{source id -> the loaded OWNER MODULE, or None} for every row of SUPPORT_OWNERS, loaded ONCE per
    pass and handed to every reader that needs one. One load per owner is not an optimization: a source
    may have exactly ONE read record, and two readers loading the same owner would hand in two answers
    about one source, which support_completeness() refuses (two answers is a disagreement, not a proof)."""
    return {row["source"]: _owner(row, reads) for row in SUPPORT_OWNERS}


def _owners_for(owners, reads=None):
    """The owner mapping a reader was given, or a fresh one it loads for itself. A reader called DIRECTLY
    (a test, a tool) still loads what it needs; a reader called through load_support_inputs is given the
    ONE mapping, so no source gets two read records."""
    return owners if isinstance(owners, dict) else load_owners(reads)
