#!/usr/bin/env python3
"""VELDO support numbers: the DECLARED CONTRACT, and THE COMPLETENESS RULE (WARP-1210).

The first module of the support pass and the one every other module obeys. It
declares WHAT CAN BE SAID (the closed set of exclusion and stand-down names),
WHAT IS READ (the source table, one row per input the pass reads, with the name
of its ABSENT state and the name of its PRESENT-BUT-UNREADABLE state), WHICH
COLLECTIONS ARE KEYED BY AN ID READ FROM A COLLECTION (and what each refuses),
and - the governing rule of this item - WHAT COUNTS AS A COMPLETE READ.

  .veldo/metrics_support_contract.py  this file: the names, the tables, and the
                                     ONE completeness decision.
  .veldo/metrics_support.py           the PURE derivation over injected inputs.
  .veldo/metrics_readers.py           the WIRED readers: the one impure edge.
  .veldo/metrics_support_report.py    the REPORT layer every surface reads.

THE GOVERNING RULE (AC3): EVERY SOURCE PROVES IT READ COMPLETELY, OR NO NUMBER
IS RENDERED AT ALL. This REPLACES the earlier approach of naming each failure
shape of each source, which three consecutive independent reviews refuted at
successively deeper levels: the enumeration bound the declared table to the
places that NAME a problem, so a read that reached no naming call site (a
permission-denied directory that glob swallows, a symlink loop that exists()
calls absent, records in a subdirectory or under a suffix nobody enumerated)
turned a real measure into a plausible wrong one in silence. Every review found
another shape, because the shapes are unbounded and the enumeration is not.

The rule is therefore INVERTED here. A reader returns what it read PLUS a
POSITIVE ASSERTION that the read was complete, and anything short of that
assertion stands the WHOLE SUPPORT SECTION down with the source NAMED. A read is
complete only when the reader can AFFIRM it: an ABSENT source is complete and
empty, and ANY other outcome - a permission error, a symlink loop, a suffix or
placement the reader does not enumerate, a partially parsed collection, a sibling
owner that would not load, a read record of a shape this contract does not
recognize, or NO RECORD AT ALL - is INCOMPLETE. read_proves_complete() is the ONE
decision point, and it grants completeness by POSITIVE MATCH ONLY: there is no
branch anywhere in this contract that returns True for an outcome it does not
recognize, so a filesystem shape nobody has thought of yet fails CLOSED by
construction instead of producing a number a human will act on.
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# THE ONE non-empty-string predicate, BOUND from the core derivation rather than reimplemented, so this
# module ships no second answer to "is this a usable string". Binding it is the only load this module
# performs; every INPUT arrives from the caller.
_cspec = importlib.util.spec_from_file_location("veldo_metrics_core_for_contract",
                                                ROOT / ".veldo" / "metrics.py")
_core = importlib.util.module_from_spec(_cspec)
_cspec.loader.exec_module(_core)
_is_str = _core._is_str


def printable(value):
    """ONE STRING, RENDERABLE ON ANY OUTPUT STREAM, whatever the platform locale. Every name this pass
    ENUMERATES and every detail it renders passes through here, and it is not defensive decoration: a
    directory entry name is bytes the filesystem accepted, os.listdir hands back a lone SURROGATE for a
    byte no codec decodes, and interpolating one into a rendered detail exited the surfaces that PRINT it
    with UnicodeEncodeError - after the measures had already been written, so every PRE-EXISTING number
    was destroyed too, and the crash was inside the stand-down path this item exists to keep standing. The
    same crash is reachable with a plain non-ASCII filename under an ASCII locale (LANG=C, the common cron
    and CI case). backslashreplace keeps the name DIAGNOSABLE - the escape names the exact byte - where
    dropping or replacing the character would leave a human unable to find the file."""
    return str(value).encode("ascii", "backslashreplace").decode("ascii")


# --- the closed set of exclusion and stand-down names ---------------------------------------------
# An honest gap in the numbers is legible as a NAMED category rather than inferred from a missing row.
# Eight names after the round-1 review, eleven more after round 2 (each a real input class handled
# SILENTLY), and SIX more after round 4, which found that a source's unreadable state was named only
# where a reader happened to look: the five undeclared sources (the four sibling OWNERS the readers
# execute and the event stream itself) and the ONE name the completeness rule needs.
SUPPORT_UNBACKED_EVENT = "UNBACKED_EVENT"                      # a close event no receipt backs
SUPPORT_UNRESOLVED_RECEIPT = "UNRESOLVED_RECEIPT"              # a receipt whose incident does not resolve
SUPPORT_CONFLICTING_RECEIPTS = "CONFLICTING_RECEIPTS"          # two receipts for one closure, nothing ordering them
SUPPORT_CONFLICTING_RECORDS = "CONFLICTING_RECORDS"            # two incident records for one id, nothing ordering them
SUPPORT_UNRESOLVED_RECURRENCE = "UNRESOLVED_RECURRENCE"        # a recurrence_of id no AUTHENTICATED incident carries
SUPPORT_UNUSABLE_INTERVAL = "UNUSABLE_INTERVAL"                # a timestamp pair no arithmetic can reach
SUPPORT_UNREADABLE_TIMESTAMP = "UNREADABLE_TIMESTAMP"          # a timestamp RECORDED that no parser can read
SUPPORT_EMPTY_DENOMINATOR = "EMPTY_DENOMINATOR"                # a rate or trend with no population
SUPPORT_NO_AREA_COST_DATA = "NO_AREA_COST_DATA"                # no per-area cost-to-change data
SUPPORT_UNREADABLE_AREA_COST_DATA = "UNREADABLE_AREA_COST_DATA"  # a cost series present but unreadable
SUPPORT_NO_ARCHITECTURE_CONTRACT = "NO_ARCHITECTURE_CONTRACT"  # no contract, so no area to join on
SUPPORT_UNREADABLE_ARCHITECTURE_CONTRACT = "UNREADABLE_ARCHITECTURE_CONTRACT"  # a contract no area reads from
SUPPORT_NO_SPEC_CORPUS = "NO_SPEC_CORPUS"                      # no corpus, so no governing spec to resolve to
SUPPORT_UNREADABLE_SPEC_CORPUS = "UNREADABLE_SPEC_CORPUS"      # a corpus present but unreadable
SUPPORT_UNREADABLE_SPEC_AREA_INDEX = "UNREADABLE_SPEC_AREA_INDEX"  # the placement-to-area join failed
SUPPORT_UNREADABLE_RECEIPT_FILE = "UNREADABLE_RECEIPT_FILE"    # a receipt file present but unreadable
SUPPORT_UNREADABLE_INCIDENT_RECORD = "UNREADABLE_INCIDENT_RECORD"  # a record present but unreadable
SUPPORT_UNREADABLE_INCIDENT_VOCABULARY = "UNREADABLE_INCIDENT_VOCABULARY"  # the owner is there, its set is not
SUPPORT_UNREADABLE_INPUT_SOURCE = "UNREADABLE_INPUT_SOURCE"    # a source problem no declared name covers
SUPPORT_INCOMPLETE_READ = "INCOMPLETE_READ"                    # a source that did not PROVE it read completely
SUPPORT_UNREADABLE_EVENT_STREAM = "UNREADABLE_EVENT_STREAM"    # the recorded stream present and unreadable
SUPPORT_UNREADABLE_INCIDENT_CONTRACT_OWNER = "UNREADABLE_INCIDENT_CONTRACT_OWNER"  # the record loader
SUPPORT_UNREADABLE_FRONT_MATTER_PARSER = "UNREADABLE_FRONT_MATTER_PARSER"          # the one parser
SUPPORT_UNREADABLE_INTENT_CORPUS_OWNER = "UNREADABLE_INTENT_CORPUS_OWNER"          # the corpus index owner
SUPPORT_UNREADABLE_ENTROPY_OWNER = "UNREADABLE_ENTROPY_OWNER"                      # the cost series owner
SUPPORT_REASONS = (SUPPORT_UNBACKED_EVENT, SUPPORT_UNRESOLVED_RECEIPT, SUPPORT_CONFLICTING_RECEIPTS,
                   SUPPORT_CONFLICTING_RECORDS, SUPPORT_UNRESOLVED_RECURRENCE,
                   SUPPORT_UNUSABLE_INTERVAL, SUPPORT_UNREADABLE_TIMESTAMP,
                   SUPPORT_EMPTY_DENOMINATOR, SUPPORT_NO_AREA_COST_DATA,
                   SUPPORT_UNREADABLE_AREA_COST_DATA, SUPPORT_NO_ARCHITECTURE_CONTRACT,
                   SUPPORT_UNREADABLE_ARCHITECTURE_CONTRACT, SUPPORT_NO_SPEC_CORPUS,
                   SUPPORT_UNREADABLE_SPEC_CORPUS, SUPPORT_UNREADABLE_SPEC_AREA_INDEX,
                   SUPPORT_UNREADABLE_RECEIPT_FILE, SUPPORT_UNREADABLE_INCIDENT_RECORD,
                   SUPPORT_UNREADABLE_INCIDENT_VOCABULARY, SUPPORT_UNREADABLE_INPUT_SOURCE,
                   SUPPORT_INCOMPLETE_READ, SUPPORT_UNREADABLE_EVENT_STREAM,
                   SUPPORT_UNREADABLE_INCIDENT_CONTRACT_OWNER,
                   SUPPORT_UNREADABLE_FRONT_MATTER_PARSER, SUPPORT_UNREADABLE_INTENT_CORPUS_OWNER,
                   SUPPORT_UNREADABLE_ENTROPY_OWNER)

# THE DECLARED SOURCES: every input the pass reads, with the name of its ABSENT state and the name of
# its PRESENT-BUT-UNREADABLE state (never conflated, for any source). The table is now ALSO the walk the
# COMPLETENESS RULE takes: support_completeness() iterates THESE ROWS and asks each for a positive
# assertion, so a row with no read is INCOMPLETE rather than silently satisfied, and a source added here
# without a reader that affirms it stands the section down until one exists. Round 4 found FIVE sources
# missing from this table: the four sibling OWNERS the readers execute (a failure in one was charged to
# whichever data source was being read, with a detail whose every clause was untrue) and the recorded
# event stream itself. `absent` is None only where the absence is already legible without a name, and
# each such row says what makes it so.
SUPPORT_SOURCES = (
    {"source": "architecture_contract", "reads": ".veldo/architecture.yaml",
     "absent": SUPPORT_NO_ARCHITECTURE_CONTRACT,
     "unreadable": SUPPORT_UNREADABLE_ARCHITECTURE_CONTRACT},
    {"source": "spec_corpus", "reads": "specs/ through intent_corpus.open_corpus",
     "absent": SUPPORT_NO_SPEC_CORPUS, "unreadable": SUPPORT_UNREADABLE_SPEC_CORPUS},
    {"source": "spec_area_index", "reads": "specs/ placements through entropy.spec_area_index",
     "absent": None, "absent_legible_as": "no contract declares an area to join a placement to, which "
                                          "the architecture_contract row names",
     "unreadable": SUPPORT_UNREADABLE_SPEC_AREA_INDEX},
    {"source": "receipt_store", "reads": ".veldo/reconciliations/", "absent": None,
     "absent_legible_as": "every closure is then reported UNBACKED_EVENT by incident id",
     "unreadable": SUPPORT_UNREADABLE_RECEIPT_FILE},
    {"source": "incident_record_store", "reads": ".veldo/incidents/", "absent": None,
     "absent_legible_as": "the trend's samples-over-population and the records-read figure show the gap",
     "unreadable": SUPPORT_UNREADABLE_INCIDENT_RECORD},
    {"source": "area_cost_series", "reads": "entropy.area_series (the per-area cost-to-change data)",
     "absent": SUPPORT_NO_AREA_COST_DATA, "unreadable": SUPPORT_UNREADABLE_AREA_COST_DATA},
    {"source": "incident_vocabulary", "reads": ".veldo/incident.py INCIDENT_EVENT_TYPES", "absent": None,
     "absent_legible_as": "the section stands down on its own line (adoption safe)",
     "unreadable": SUPPORT_UNREADABLE_INCIDENT_VOCABULARY},
    {"source": "incident_timeline", "reads": "the incident record's own recorded timeline",
     "absent": None, "absent_legible_as": "nothing was recorded, which is a gap and not a corruption, "
                                          "so no observation is made and none is named",
     "unreadable": SUPPORT_UNREADABLE_TIMESTAMP},
    {"source": "event_stream", "reads": ".veldo/events.jsonl", "absent": None,
     "absent_legible_as": "no closure is recognized and the section is the honest empty state",
     "unreadable": SUPPORT_UNREADABLE_EVENT_STREAM},
    # THE SIBLING OWNERS the readers EXECUTE. Each is a source in its own right because each can fail on
    # its own, and round 4 showed what happens when they are not: with the one parser unloadable and the
    # contract file untouched and valid, the CONTRACT was blamed with a detail claiming it was truncated,
    # malformed, a directory or declaring no area, every clause of which was false. Each names ITSELF.
    {"source": "incident_contract_owner", "reads": ".veldo/incident.py (the record loader and its schema)",
     "absent": None, "absent_legible_as": "an engine without the incident contract recognizes no "
                                          "closure, which the incident_vocabulary row names",
     "unreadable": SUPPORT_UNREADABLE_INCIDENT_CONTRACT_OWNER},
    {"source": "front_matter_parser", "reads": ".veldo/validate.py (the ONE front-matter parser)",
     "absent": None, "absent_legible_as": "an engine without the one parser reads no record and no "
                                          "contract, and every dependent row says so",
     "unreadable": SUPPORT_UNREADABLE_FRONT_MATTER_PARSER},
    {"source": "intent_corpus_owner", "reads": ".veldo/intent_corpus.py (the corpus index owner)",
     "absent": None, "absent_legible_as": "an engine without the corpus owner carries no spec index, "
                                          "which the spec_corpus row names",
     "unreadable": SUPPORT_UNREADABLE_INTENT_CORPUS_OWNER},
    {"source": "entropy_series_owner", "reads": ".veldo/entropy.py (the cost-to-change series owner)",
     "absent": None, "absent_legible_as": "an engine without the series owner has no per-area cost "
                                          "data, which the area_cost_series row names",
     "unreadable": SUPPORT_UNREADABLE_ENTROPY_OWNER},
)

# A DUPLICATE KEY IS NEVER RESOLVED BY COLLECTION ORDER. Every dict this pass keys by an id it read is
# declared here with the conflict it REFUSES (detect, exclude, name every participant, keep the
# arithmetic closing) or the reason it cannot conflict.
SUPPORT_ID_KEYED = (
    {"collection": "backing", "built_by": "authenticate_incidents",
     "keyed_by": "the receipt's incident id", "conflict": SUPPORT_CONFLICTING_RECEIPTS},
    {"collection": "records", "built_by": "index_incident_records",
     "keyed_by": "the incident record's own id", "conflict": SUPPORT_CONFLICTING_RECORDS},
    {"collection": "closed", "built_by": "closed_incident_ids",
     "keyed_by": "the close event's incident id", "conflict": None,
     "immune": "MEMBERSHIP ONLY: the de-duplicated list carries no value beside the id, so two close "
               "events for one incident have nothing to lose to an order"},
    {"collection": "per_area", "built_by": "incidents_per_area",
     "keyed_by": "a DECLARED contract area id", "conflict": None,
     "immune": "APPEND ONLY (setdefault then append, never an overwrite), and the key comes from the "
               "contract's de-duplicated area ids rather than from a collection of files"},
    {"collection": "spec_areas", "built_by": "metrics_readers.load_corpus_areas",
     "keyed_by": "a spec id the corpus carries", "conflict": None,
     "immune": "the key set IS intent_corpus.spec_ids(), the keys of a mapping its owner already "
               "de-duplicated, so this pass cannot collide; and the residual round 3 declared out of "
               "reach (a duplicate spec id resolved inside that owner by ITS filename order, which "
               "moved an area row) is now CLOSED by the completeness rule rather than accepted: the "
               "corpus read ACCOUNTS for every entry of specs/ against the index the owner returned, so "
               "two files claiming one id leave an entry unaccounted and the whole section stands down"},
    {"collection": "area_cost", "built_by": "metrics_readers.load_area_cost",
     "keyed_by": "a declared area id", "conflict": None,
     "immune": "the key set is entropy.area_series' own mapping keys, unique by construction"},
)

# THE RECEIPT SCHEMA this derivation authenticates against, restated as a LITERAL and BOUND to its owner
# by a selftest. The only owner of the string is .veldo/incident_reconcile.py's SCHEMA constant, and
# importing that module transitively executes the action executor - an enforcement-core organ this item
# must not read - so the literal is restated here and a selftest asserts it EQUALS
# incident_reconcile.SCHEMA, which is this repository's own drift-binding idiom (a literal plus a test
# that pins it to the owner). Reading a string constant needs no import; forging a receipt now needs the
# owner's schema, so a hand-written mapping in the store no longer authenticates anything.
SUPPORT_RECEIPT_SCHEMA = "veldo.reconciliation/v1"

# DECLARED ROUNDING, applied in exactly one place per measure and nowhere else: elapsed hours to 2
# decimals (the precision the cycle-time average already uses), a rate to 3 and its percent to 1 (the
# precision gate_pass_rate and the dashboard already use). No measure is presented to a precision its
# input does not support.
SUPPORT_ROUNDING = {"hours": 2, "rate": 3, "percent": 1}

SUPPORT_REVIEW_LANE = (
    "REVIEW LANE (unmechanizable, honestly labeled): whether an incident was TRULY resolved from "
    "artifacts alone is a HUMAN judgment. The diagnosability score counts a DECLARED MECHANICAL PROXY "
    "(the receipt records a human diagnosis validation and the incident resolves to a governing spec "
    "or a declared contract area); it is a proxy for understanding, never a measurement of it, and "
    "refining the proxy is a later intent rather than a silent change here.")

# THE ONE TOKEN THAT MEANS "THIS SOURCE PROVED A COMPLETE READ". Deliberately not a boolean and not an
# uppercase word: a truthy flag is the thing an incomplete read accidentally carries, and a versioned
# token can only appear where a reader wrote it on purpose through read_complete().
SUPPORT_READ_COMPLETE = "support.read.complete/v1"


def _skipped_entries(skipped):
    """The DECLARED NON-RECORDS one read accounted for and did not consume, each PRINTABLE. Every read
    record carries this list (empty for a read that skipped nothing), the derivation carries it into the
    model as read_skipped, and all three surfaces render it: "accounted but not read" is a fact a human has
    to be able to SEE, and until round 7 it lived only in the basis text, which reaches no surface."""
    return [printable(entry) for entry in skipped or ()]


def read_complete(source, subject, basis, skipped=None):
    """ONE SOURCE'S READ, AFFIRMED COMPLETE. The ONLY constructor that can produce the completeness
    token, and it produces it only with a non-empty BASIS: the reader must SAY what makes the read
    complete (the entries it accounted for, or the absence it observed), because "trust me" is what the
    three previous rounds shipped. A read affirmed here carries NO problems by construction - a reader
    that found something to name calls read_incomplete() instead. The SUBJECT and the BASIS pass through
    printable(), because a read's subject is a PATH the filesystem gave this pass and both are rendered."""
    return {"source": source, "subject": printable(subject), "problems": [],
            "completeness": SUPPORT_READ_COMPLETE if _is_str(basis) else None,
            "basis": printable(basis) if _is_str(basis) else None,
            "skipped": _skipped_entries(skipped)}


def read_incomplete(source, subject, detail, skipped=None):
    """ONE SOURCE'S READ THAT DID NOT PROVE COMPLETE, with the problem that says why, NAMED against this
    source and no other. The record carries NO completeness token, so read_proves_complete() answers no
    without having to recognize the failure: the shape of the failure is irrelevant to the decision,
    which is the whole point of inverting the rule. The SUBJECT and the DETAIL pass through printable()
    for the reason read_complete states: this record is rendered on three surfaces, and the round-5 crash
    entered through exactly this path with a filesystem name in the detail."""
    return {"source": source, "subject": printable(subject), "completeness": None, "basis": None,
            "skipped": _skipped_entries(skipped),
            "problems": [{"source": source, "subject": printable(subject),
                          "detail": printable(detail)}]}


def read_proves_complete(read):
    """WHETHER ONE READ RECORD PROVES A COMPLETE READ - THE ONE DECISION POINT of this item, and the
    place the FAIL-CLOSED DEFAULT lives.

    It answers YES only for a record that carries EVERY positive property: it is a mapping, it carries
    the EXACT completeness token (not a truthy value, not a different string), it states a NON-EMPTY
    basis, and it names NO problem. Everything else answers NO - a missing record, None, a boolean, a
    token from another version, an empty basis, a read that named a problem, a mapping of a shape this
    function does not recognize, an object it has never seen. There is no `else: return True` and no
    default-allow branch anywhere in this contract, which is exactly why a filesystem shape nobody has
    enumerated cannot pass: it never reaches the affirmation, so it is incomplete without anyone having
    to add a name for it."""
    if not isinstance(read, dict):
        return False
    if read.get("completeness") != SUPPORT_READ_COMPLETE:
        return False
    if not _is_str(read.get("basis")):
        return False
    return not read.get("problems")


def read_problems(source_reads=None):
    """Every problem the reads carry, in the order they were read. The readers report WHAT failed; the
    NAME is decided by support_source_problems() from the declared table, so an incomplete read is
    named on all three surfaces and never only counted."""
    out = []
    for read in source_reads or ():
        if isinstance(read, dict):
            out.extend(p for p in read.get("problems") or () if isinstance(p, dict))
    return out


def _read_shortfall(read):
    """WHY one read record fell short, stated for the reader of the stand-down. It DESCRIBES the record
    that arrived; it never decides anything (read_proves_complete does), so a shape described here as
    unrecognized was already refused rather than being refused because of this text."""
    if read is None:
        return "NO read record was supplied for it at all"
    if not isinstance(read, dict):
        return "the read record is a %s rather than a record (mapping)" % type(read).__name__
    if read.get("problems"):
        return ("the read named %d problem(s), so the collection was read in PART: %s"
                % (len(read["problems"]),
                   "; ".join(str(p.get("detail")) for p in read["problems"] if isinstance(p, dict))))
    if read.get("completeness") != SUPPORT_READ_COMPLETE:
        return ("the read carries no completeness affirmation (it carries %r, and only the token this "
                "contract declares affirms a read)" % (read.get("completeness"),))
    return "the read affirmed completeness with no BASIS, so it states nothing that could be checked"


def support_completeness(source_reads=None):
    """THE GOVERNING RULE (AC3): EVERY DECLARED SOURCE PROVES IT READ COMPLETELY, OR NO NUMBER IS
    RENDERED AT ALL. Returns {"complete", "incomplete", "affirmed", "declared"} where `incomplete` names
    every source that did not prove it, each as {reason, source, subject, detail} in the shape all three
    surfaces render.

    THE WALK IS OVER THE DECLARED TABLE, never over the reads supplied, which is the structural half of
    the fail-closed default: a source whose read is MISSING ENTIRELY is INCOMPLETE rather than absent
    from the answer, so wiring a reader is not optional and adding a row to SUPPORT_SOURCES without a
    reader that affirms it stands the section down until one exists. A read for a source the table does
    NOT declare is itself an incompleteness, because a source nobody declared cannot have proven
    anything about what this pass reads. And the DETAIL of every entry names the state the declared row
    gives this source's unreadability, so a reader of the stand-down sees both facts: the read was not
    proven complete, and this is what that means for this source."""
    reads = {}
    undeclared = []
    declared = {row["source"] for row in SUPPORT_SOURCES}
    for read in source_reads or ():
        source = read.get("source") if isinstance(read, dict) else None
        if source in declared:
            # FIRST WINS, and a SECOND read for one source is an incompleteness rather than an
            # overwrite: two answers about one source is not a proof, it is a disagreement.
            if source in reads:
                undeclared.append({"source": source, "subject": str(read.get("subject")),
                                   "detail": "TWO reads were supplied for this ONE declared source, so "
                                             "nothing here proves which of them read the source: two "
                                             "answers about one source is a disagreement, not a proof"})
            else:
                reads[source] = read
        else:
            undeclared.append({"source": str(source), "subject": str(read.get("subject"))
                               if isinstance(read, dict) else None,
                               "detail": "a read arrived for a source SUPPORT_SOURCES does not declare, "
                                         "so this pass cannot say how its absence and its unreadability "
                                         "are told apart and cannot accept its word for either"})
    incomplete = []
    for row in SUPPORT_SOURCES:
        read = reads.get(row["source"])
        if read_proves_complete(read):
            continue
        incomplete.append({
            "reason": SUPPORT_INCOMPLETE_READ, "source": row["source"],
            "subject": (read or {}).get("subject") or row["reads"],
            "detail": "STANDING DOWN (%s): this source did NOT prove it read COMPLETELY (%s), so the "
                      "whole support section renders NO number: a read that cannot affirm completeness "
                      "is indistinguishable from a read that silently saw nothing, and an unproven read "
                      "is the one thing this pass never treats as an absence"
                      % (row["unreadable"], _read_shortfall(read))})
    for entry in undeclared:
        incomplete.append({"reason": SUPPORT_INCOMPLETE_READ, "source": entry["source"],
                           "subject": entry["subject"], "detail": entry["detail"]})
    return {"complete": not incomplete, "incomplete": incomplete,
            "affirmed": sorted(s for s in reads if read_proves_complete(reads[s])),
            "declared": sorted(declared)}


def source_problem_detail(input_problems, source):
    """The DETAIL of the reported problem for ONE declared source, or None when that source read fine. The
    ONE selector over the readers' problem list, so a problem that must also DECIDE something (a cost series
    nobody could read names its cells UNREADABLE, never absent) is read from the same list the report is
    named from, never from a second argument that could disagree with it."""
    for entry in input_problems or ():
        if isinstance(entry, dict) and entry.get("source") == source and _is_str(entry.get("detail")):
            return entry["detail"]
    return None


def _problem_fields(entry, position, deciding):
    """(source, subject, detail) for ONE reported problem, or (None, None, None) when a DECIDING source
    reported no problem at all. THE PLACE NOTHING IS DROPPED: an entry that is not a record (exactly what
    a reader leaves behind when its naming statement is lost) and a problem whose DETAIL is empty are
    each given a DECLARED SUBSTITUTE detail instead of being discarded, because round 4 found both being
    discarded here and the suite asserting the discard - and a problem dropped for want of a detail is
    the same silence as a problem never reported."""
    if not isinstance(entry, dict):
        return (None, "input problem at position %d" % position,
                "the readers reported a problem that is a %s rather than a record (mapping), so the "
                "source that failed cannot be identified from it: NAMED here rather than dropped, "
                "because a dropped problem is exactly how an unreadable source reads as an absent one"
                % type(entry).__name__)
    raw = entry.get("detail")
    if deciding and raw is None:
        return None, None, None
    if _is_str(raw):
        return entry.get("source"), entry.get("subject"), raw
    return (entry.get("source"), entry.get("subject"),
            "the readers reported this source unreadable and supplied NO detail (%r), which is itself a "
            "defect: the source is NAMED anyway, because a problem dropped for want of a detail is the "
            "same silence as a problem never reported" % (raw,))


def _named_problem(names, source, subject, detail):
    """ONE reported problem under the NAME the declared table gives it, or UNREADABLE_INPUT_SOURCE when
    no row covers it. The single naming statement of the pass, so the taxonomy has one owner and a reader
    can neither invent a name nor lose one."""
    return {"reason": names.get(source, SUPPORT_UNREADABLE_INPUT_SOURCE), "source": source,
            "subject": subject, "detail": detail}


def support_source_problems(input_problems=None, contract_problem=None, corpus_problem=None):
    """EVERY INPUT SOURCE THAT COULD NOT BE READ, NAMED from the declared SUPPORT_SOURCES table:
    {reason, source, subject, detail} per problem, sorted so the set never depends on read order. The
    readers report WHAT failed (source, subject, detail); the NAME is decided HERE from the table, so
    the taxonomy has one owner and a reader can neither invent a name nor drop a problem for want of
    one. NOTHING IS EVER DROPPED (see _problem_fields). A source outside the table is still named
    (UNREADABLE_INPUT_SOURCE). The two problems that also DECIDE something arrive as their own arguments
    and are named here too, once, so every unreadable source is in one place."""
    names = {row["source"]: row["unreadable"] for row in SUPPORT_SOURCES}
    items = [(entry, False) for entry in list(input_problems or [])]
    items += [({"source": "architecture_contract", "subject": ".veldo/architecture.yaml",
                "detail": contract_problem}, True),
              ({"source": "spec_corpus", "subject": "specs/", "detail": corpus_problem}, True)]
    out, seen = [], set()
    for position, (entry, deciding) in enumerate(items):
        source, subject, detail = _problem_fields(entry, position, deciding)
        if detail is None:
            continue                    # a DECIDING source that reported no problem: nothing failed here
        key = (source, subject, detail)
        if key in seen:
            continue
        seen.add(key)
        out.append(_named_problem(names, source, subject, detail))
    return sorted(out, key=lambda e: (str(e["source"]), str(e["subject"]), e["detail"]))
