#!/usr/bin/env python3
"""VELDO support numbers: the DECLARED SHAPE the incidents are joined to (WARP-1210).

The reader family for the side of the join that is not evidence: the
architecture contract's DECLARED AREAS, the intent corpus's SPEC INDEX, the
placement-to-area index that turns a spec's placement into areas, and the
per-area cost-to-change series. The measures themselves rest on recorded
evidence (.veldo/metrics_readers.py: the stream, the receipts, the records); what
lives here is the shape an incident is ATTRIBUTED to and the cost data the map
joins with, which is a different concern with a different failure mode - the
evidence can be missing while the shape is fine, and the shape can be
unreadable while every incident is authenticated.

FOUR DECLARED SOURCES, FOUR ATTEMPTS, FOUR NAMES, so no failure is ever reported
as another's: round 1 blocked because an unreadable CONTRACT read as an absent
one, round 2 because the same conflation still stood on the CORPUS, round 3
because the placement INDEX had no attempt of its own, and round 4 because the
COST SERIES reported a FALSE absence whenever the index it joins over was empty.
Each is read through the ACCOUNTED READ (.veldo/metrics_read_accounting.py), so
each either proves it read completely or declines and stands the whole support
section down under its own name. ALL THREE ARE READ BY AN ENGINE OWNER THIS PASS
HANDS A PATH TO, so the KIND TEST, the DECLARED CLOSURE of every root that owner
opens ON THIS PASS'S BEHALF and the handler live at ONE hand-off named by its own
DELEGATION (metrics_read_closure.delegated): a FIFO among the specs, and at FOUR
MORE roots the corpus owner opens, hung ALL FOUR surfaces forever raising nothing.

Reads recorded files only: no live system (NG1), no process, thread or timer
(NG3), and nothing is written anywhere.
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# THE ENGINE OWNERS and, through them, THE ACCOUNTED READ: presence by lstat, enumeration by listdir, entry
# accounting against the declared skip rule, and the two read constructors the declared contract owns. ONE
# spec block rather than two, because the owner module is the facade for the plane below it. Nothing about
# HOW a read is proven complete is restated here; this module says WHICH sources it reads and how each parses.
_ospec = importlib.util.spec_from_file_location("veldo_metrics_owner_reads_for_shape",
                                               ROOT / ".veldo" / "metrics_owner_reads.py")
_owners = importlib.util.module_from_spec(_ospec)
_ospec.loader.exec_module(_owners)
_is_str = _owners._is_str
_problem = _owners._problem
_keep = _owners._keep
_present = _owners._present
_accounted_dir = _owners._accounted_dir
delegated = _owners.delegated
_owners_for = _owners._owners_for
_dependency_declined = _owners._dependency_declined
read_complete = _owners.read_complete
read_incomplete = _owners.read_incomplete
read_proves_complete = _owners.read_proves_complete

# THE SUFFIX the corpus consumes, and the corpus owner's OWN non-spec names, restated here and BOUND to the
# owner by a selftest (this repository's drift-binding idiom: a literal plus a test that pins it to the
# owner). The accounting needs them because the owner reads specs/ itself and returns an INDEX, not a file
# list: without them, the two files it skips by name would read as two entries nobody accounted for.
SUPPORT_SPEC_SUFFIX = ".md"
SUPPORT_CORPUS_NON_SPEC_NAME = "index.md"
SUPPORT_CORPUS_NON_SPEC_PREFIX = "TEMPLATE"


def _corpus_detail(cause):
    """The named detail for a corpus that is PRESENT and could not be READ. Its own helper so the naming decision
    is ONE line at each call site - round 2 found this exact naming missing, and a decision spread over five lines
    of string is one nobody can neutralize in a tooth or spot in a diff."""
    return ("the intent corpus over this repository's recorded artifacts EXISTS but could NOT be read "
            "(%s), so the SPEC half of the diagnosability definition is unreadable rather than absent: "
            "ONE malformed spec file empties the whole index, and reporting that as an absence makes a "
            "score of 0.0 percent read as an honest zero over a readable corpus" % cause)


def _corpus_expected(names):
    """How many of a specs/ enumeration the corpus owner is EXPECTED to carry an id for: every accounted
    spec file except the ones the owner itself skips BY NAME. The owner reads the directory and returns an
    INDEX rather than a file list, so the accounting needs its skip rule; the two literals are restated in
    this module's constants and BOUND to the owner by a selftest, which is this repository's drift-binding
    idiom rather than a second implementation of the rule."""
    return [n for n in names
            if n != SUPPORT_CORPUS_NON_SPEC_NAME and not n.startswith(SUPPORT_CORPUS_NON_SPEC_PREFIX)]


def _read_contract(root, V, reads=None):
    """(the contract's parse (arch, contract), its DECLARED area ids or None, the named problem or None) -
    ONE attempt at ONE source. PRESENCE is _present(), NOT exists(): a DIRECTORY named architecture.yaml, a
    symlink LOOP and a DANGLING symlink are each PRESENT and unreadable, and round 2 and round 4 each found
    one of those three reported as an ABSENT contract - the same class, on the same source, one predicate
    over. An absent contract is COMPLETE and empty (the join stands down by name, adoption safe); a present
    one that yields no declared area is INCOMPLETE under its own name."""
    contract_path = root / ".veldo" / "architecture.yaml"
    present = _present(contract_path)
    arch = contract = None
    contract_cause = None
    if V is not None:
        parsed, cause = delegated("architecture_contract", root, lambda: V.load_repo_contract(str(root)))
        arch, contract = parsed if isinstance(parsed, tuple) and len(parsed) == 2 else (None, None)
        contract_cause = cause or None
    declared = sorted(arch.area_ids(contract)) if (arch is not None and contract is not None) else None
    contract_problem = None
    if present and not declared:
        contract_problem = ("the architecture contract at .veldo/architecture.yaml EXISTS but NO declared area "
                            "could be read from it (it is truncated, malformed, a directory, a symlink that "
                            "does not resolve, or it declares none%s), so the shape this join needs is "
                            "unreadable rather than absent"
                            % ("" if contract_cause is None else "; the read raised %s" % contract_cause))
    if V is None:
        _dependency_declined("architecture_contract", str(contract_path), "its owner .veldo/validate.py", reads)
    elif contract_problem is not None:
        _keep(reads, read_incomplete("architecture_contract", str(contract_path), contract_problem))
    elif not present:
        _keep(reads, read_complete("architecture_contract", str(contract_path),
                                   "ABSENT: no directory entry exists at this path (lstat), so this "
                                   "repository declares no architecture contract and the join stands down "
                                   "by name (adoption safe)"))
    else:
        _keep(reads, read_complete("architecture_contract", str(contract_path),
                                   "READ: the contract is present and declares %d area(s)" % len(declared)))
    return (arch, contract), declared, contract_problem


def _read_corpus(root, IC, reads=None):
    """(the spec ids the corpus carries, its named problem or None, the READ) - ONE attempt at ONE source,
    ACCOUNTED against the index the owner returned: every entry of specs/ must be a regular .md file, and the
    owner must carry an id for every one of them except the ones it skips by its own name rule. That is what
    closes the shapes an exception cannot reach - a spec under another suffix, a spec in a subdirectory, and
    TWO FILES CLAIMING ONE ID (the CLASS TWO residual round 3 declared out of reach, because the owner
    resolves it by ITS read order and this pass cannot see the participants without a second front-matter
    parser it refuses to build) each leave an accounted entry with no id behind it."""
    specs_dir, spec_ids, corpus_problem = root / "specs", [], None
    entries, corpus_read = _accounted_dir("spec_corpus", specs_dir, SUPPORT_SPEC_SUFFIX)
    if IC is None:
        corpus_read = read_incomplete("spec_corpus", str(specs_dir),
                                      "the corpus could not be read COMPLETELY because its owner "
                                      ".veldo/intent_corpus.py did not prove a complete read, and an "
                                      "index nobody could build is not an absent corpus")
        corpus_problem = _corpus_detail("the corpus owner .veldo/intent_corpus.py did not load")
        _keep(reads, corpus_read)
        return spec_ids, corpus_problem, corpus_read, entries
    if not read_proves_complete(corpus_read):
        corpus_problem = _corpus_detail(corpus_read["problems"][0]["detail"])
    spec_ids, delegation = delegated("spec_corpus", root, lambda: IC.open_corpus(root).spec_ids(), [])
    if delegation:
        corpus_problem = _corpus_detail(delegation)
        corpus_read = read_incomplete("spec_corpus", str(specs_dir), corpus_problem)
    else:
        expected = _corpus_expected([p.name for p in entries])
        if read_proves_complete(corpus_read) and len(spec_ids) != len(expected):
            corpus_problem = _corpus_detail(
                "the owner carries %d spec id(s) for the %d accounted spec file(s) of specs/, so %d "
                "file(s) it read produced no id this pass can see (a spec declaring none, or two "
                "files claiming ONE id, which its own read order would resolve)"
                % (len(spec_ids), len(expected), abs(len(expected) - len(spec_ids))))
            corpus_read = read_incomplete("spec_corpus", str(specs_dir), corpus_problem)
        elif read_proves_complete(corpus_read):
            # The ENUMERATION's basis is carried forward, not replaced: an entry the DECLARED SKIP RULE
            # accounted for stays visible in the read a human actually sees.
            corpus_read = read_complete("spec_corpus", str(specs_dir),
                                        "ACCOUNTED: the owner carries an id for every one of the %d "
                                        "accounted spec file(s) of specs/ (%d entry(ies) the owner skips "
                                        "by its own declared name rule), over an enumeration that "
                                        "accounted for every entry: %s"
                                        % (len(expected), len(entries) - len(expected),
                                           corpus_read["basis"]))
    _keep(reads, corpus_read)
    return spec_ids, corpus_problem, corpus_read, entries


def _read_area_index(specs_dir, parsed, ENT, corpus_read, entries, problems, reads=None):
    """{spec id -> its declared areas} - ONE attempt at ONE source, and it is ATTEMPTED IN EVERY CASE the
    owner and the contract allow, even when the corpus read already fell short: two sources, two attempts,
    two names is the discipline round 2 credited, and an index that ALSO broke must be NAMED rather than
    hidden behind the corpus that broke beside it. What the corpus shortfall costs the index is its
    AFFIRMATION, applied after the attempt - a join over a directory nobody accounted for is not a complete
    read of that directory's placements."""
    arch, contract = parsed
    areas_by_spec = {}
    if ENT is None:
        _dependency_declined("spec_area_index", str(specs_dir), "its owner .veldo/entropy.py", reads)
        return areas_by_spec
    if contract is None:
        _keep(reads, read_complete("spec_area_index", str(specs_dir),
                                   "NOT JOINED: no readable contract declares an area for a placement to "
                                   "resolve to, which the architecture_contract row names; there is no "
                                   "index to read in part"))
        return areas_by_spec
    areas_by_spec, delegation = delegated(
        "spec_area_index", specs_dir.parent, lambda: ENT.spec_area_index(specs_dir, contract, arch), {})
    if delegation:
        index_unreadable = _problem("spec_area_index", str(specs_dir), "the placement-to-area join over "
                                    "specs/ EXISTS and could NOT be built (%s), so a spec's declared "
                                    "areas are unreadable rather than undeclared and an incident that "
                                    "resolves only through its spec's PLACEMENT cannot be attributed"
                                    % delegation)
        problems.append(index_unreadable)
        _keep(reads, read_incomplete("spec_area_index", str(specs_dir), index_unreadable["detail"]))
    else:
        if not read_proves_complete(corpus_read):
            _dependency_declined("spec_area_index", str(specs_dir),
                                 "the spec_corpus enumeration it joins over", reads)
        else:
            _keep(reads, read_complete("spec_area_index", str(specs_dir),
                                       "ACCOUNTED: the join ran over the same %d accounted spec "
                                       "file(s) and resolved %d of them to a declared area; a spec it "
                                       "omits DECLARES no placement, which is a declared absence "
                                       "rather than an unread file"
                                       % (len(entries), len(areas_by_spec))))
    return areas_by_spec


def load_corpus_areas(root=None, reads=None, owners=None):
    """The CORPUS SPEC INDEX, the contract's DECLARED AREAS, and the NAMED PROBLEM for each of them when it is
    PRESENT and unreadable, each read from its owner in its OWN attempt: the spec ids from the intent corpus
    (intent_corpus.spec_ids, the one index of what the corpus carries) and each spec's declared areas from the
    placement join (entropy.spec_area_index, where a placement and a footprint become areas).

    Returns {spec_areas, contract_areas, contract_problem, corpus_problem, problems} - a mapping rather than a
    growing tuple, because this reader answers for THREE data sources. spec_areas maps every spec the corpus
    carries to its declared areas (EMPTY when it declares none, which is why a governing spec still resolves
    without a contract); contract_areas is the declared area ids, or None when this repository declares NO
    architecture contract at all. THREE SOURCES, THREE ATTEMPTS, THREE NAMES, so no failure is reported as
    another's, and each attempt is its own function so a reader can see that the three are independent."""
    root = Path(root or ROOT)
    problems = []
    owners = _owners_for(owners, reads)
    parsed, declared, contract_problem = _read_contract(root, owners.get("front_matter_parser"), reads)
    spec_ids, corpus_problem, corpus_read, entries = _read_corpus(
        root, owners.get("intent_corpus_owner"), reads)
    areas_by_spec = _read_area_index(root / "specs", parsed, owners.get("entropy_series_owner"),
                                     corpus_read, entries, problems, reads)
    return {"spec_areas": {sid: sorted(areas_by_spec.get(sid) or ()) for sid in spec_ids},
            "contract_areas": declared, "contract_problem": contract_problem,
            "corpus_problem": corpus_problem, "problems": problems}


def load_area_cost(root=None, events=None, spec_areas=None, corpus_reads=None, reads=None, owners=None):
    """(the per-area COST-TO-CHANGE data, the named problems), SELECTED from entropy.area_series
    (the one series the entropy map and the dashboard already read) and never recomputed here:
    {area: {samples, latest}} for every area that HAS a recorded sample, and an EMPTY mapping when none
    does, which stands the cost column down by name (NO_AREA_COST_DATA). A series that is PRESENT and
    cannot be read is a DIFFERENT fact and arrives as its own problem, so a cost cell says
    UNREADABLE_AREA_COST_DATA rather than claiming the data does not exist. The values are entropy's own
    samples; this reader selects, it never computes a cost figure.

    THE SERIES IS ALWAYS CONSULTED, which round 4 blocked on (R3-B3): this returned an empty mapping
    whenever spec_areas was empty, so with real cost data in the stream and an unreadable corpus the
    surviving row said NO_AREA_COST_DATA - a FALSE absence, from the one function whose docstring claims it
    names which fact it is. It now reads the series in every case, and when the index it joins over did not
    prove a complete read it DECLINES: the cost cells then say UNREADABLE rather than absent, and the
    section stands down anyway. `events` are the RECORDED events at `root` (load_events, not the engine's
    stream), so a temporary tree's cost is its own."""
    if events is None:
        # NO STREAM, NO SERIES: this reader never reaches for the ENGINE's own events.jsonl to fill a
        # caller's gap, which is exactly what round 4 found it doing (a temporary tree's cost came from this
        # repository's stream). Without a stream that was read, the cost cannot be read completely either.
        _dependency_declined("area_cost_series", "entropy.area_series",
                             "no recorded event stream was supplied to it", reads)
        return {}, [_problem("area_cost_series", "entropy.area_series",
                             "no recorded event stream was supplied, so the per-area cost series was not "
                             "consulted at all and every cost cell says UNREADABLE rather than absent")]
    index_incomplete = None
    for read in corpus_reads or ():
        if isinstance(read, dict) and read.get("source") in ("spec_corpus", "spec_area_index") \
                and not read_proves_complete(read):
            index_incomplete = read["source"]
            break
    try:
        ENT = _owners_for(owners).get("entropy_series_owner")
        series, stats = ENT.area_series(events, {sid: set(areas) for sid, areas
                                                 in (spec_areas or {}).items()})
        dimensions = ENT.COST_DIMENSIONS
    except Exception as exc:
        cost_unreadable = _problem("area_cost_series", "entropy.area_series", "the per-area cost-to-change "
                                   "series EXISTS and could NOT be read (%s: %s), so every cost cell stands down "
                                   "as UNREADABLE rather than as an absence of recorded cost"
                                   % (type(exc).__name__, exc))
        _keep(reads, read_incomplete("area_cost_series", "entropy.area_series", cost_unreadable["detail"]))
        return {}, [cost_unreadable]
    out = {}
    for area in sorted(series):
        samples = series[area]
        if samples:
            out[area] = {"samples": len(samples),
                         "latest": {dim: samples[-1].get(dim) for dim in dimensions}}
    if index_incomplete is not None:
        dependency = _problem("area_cost_series", "entropy.area_series",
                              "the series was consulted and %d area(s) carry a recorded sample, but the %s "
                              "read this join resolves an area through did NOT prove complete, so the cost "
                              "cells say UNREADABLE rather than reporting an absence of recorded cost that "
                              "would be false (%d shipped change(s) went unattributed)"
                              % (len(out), index_incomplete, stats.get("unattributed_changes", 0)))
        _dependency_declined("area_cost_series", "entropy.area_series",
                             "the %s read it joins over" % index_incomplete, reads)
        return out, [dependency]
    _keep(reads, read_complete("area_cost_series", "entropy.area_series",
                               "READ: the series was consulted over the recorded events and the accounted "
                               "spec index; %d area(s) carry a sample and %d shipped change(s) resolved to "
                               "no declared area" % (len(out), stats.get("unattributed_changes", 0))))
    return out, []
