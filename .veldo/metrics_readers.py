#!/usr/bin/env python3
"""VELDO support numbers: the RECORDED EVIDENCE readers and the ONE gatherer (WARP-1210).

The support derivation in .veldo/metrics_support.py is pure over injected inputs.
This is where those inputs come from, and it is the entry point every surface
uses: load_support_inputs() returns exactly the keyword arguments the derivation
takes, including one READ RECORD per declared source.

WHAT THIS MODULE READS is the RECORDED EVIDENCE the measures are authenticated
against - the event stream (the index), the reconciliation receipts (the
authority), the incident records (the timelines), and the vocabulary that
recognizes a closure at all. The other side of the join - the architecture
contract, the spec corpus, the placement index and the per-area cost series -
lives in .veldo/metrics_shape_readers.py, because the evidence can be missing
while the shape is fine and the shape can be unreadable while every incident is
authenticated. HOW any of them proves it read completely lives in
.veldo/metrics_read_accounting.py, once for all of them.

EVERY READER PROVES IT READ COMPLETELY, OR IT DOES NOT AFFIRM (AC3). Each reader
hands the derivation a read record carrying a POSITIVE assertion of completeness
with the BASIS for it; anything short of that stands the WHOLE SUPPORT SECTION
down with the source named. An ABSENT source is COMPLETE and empty (adoption
safe). `root` is honored by EVERY read, including the event stream, which round 4
found reading the ENGINE's own: a temporary tree's receipts were authenticated
against this repository's events.

Reads recorded files only: no live system (NG1), no process, thread or timer
(NG3), and nothing is written anywhere.
"""
import importlib.util
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# THE ENGINE OWNERS (and through them THE ACCOUNTED READ) and the SHAPE readers, bound at import. Nothing
# about how a read is proven complete is restated here, and nothing about the declared shape is read here:
# one direction of dependency, one job.
_ospec = importlib.util.spec_from_file_location("veldo_metrics_owner_reads",
                                                ROOT / ".veldo" / "metrics_owner_reads.py")
_owners = importlib.util.module_from_spec(_ospec)
_ospec.loader.exec_module(_owners)
_problem = _owners._problem
_keep = _owners._keep
_present = _owners._present
_entry_kind = _owners._entry_kind
_accounted_dir = _owners._accounted_dir
_parsed_shortfall = _owners._parsed_shortfall
_record_shortfall = _owners._record_shortfall
_owners_for = _owners._owners_for
_dependency_declined = _owners._dependency_declined
load_owners = _owners.load_owners
read_complete = _owners.read_complete
read_incomplete = _owners.read_incomplete
read_proves_complete = _owners.read_proves_complete

_sspec = importlib.util.spec_from_file_location("veldo_metrics_shape_readers",
                                               ROOT / ".veldo" / "metrics_shape_readers.py")
_shape = importlib.util.module_from_spec(_sspec)
_sspec.loader.exec_module(_shape)
load_corpus_areas = _shape.load_corpus_areas
load_area_cost = _shape.load_area_cost

# The lifecycle STEP whose event type this derivation reads, resolved against the vocabulary the incident
# contract owns (never a literal event type here), by the same selection rule the reconciliation pass uses
# over the same owner's set, so the emitter, the gate, and this metric source cannot drift.
SUPPORT_CLOSED_STEP = "closed"

# THE SUFFIX each evidence store consumes, declared so the ACCOUNTING has something to account against. An
# entry whose suffix is not exactly this is UNACCOUNTED, never absent: .YAML, .yml and a subdirectory each
# turned a real measure into a plausible wrong one in silence before this existed.
SUPPORT_RECEIPT_SUFFIX = ".json"
SUPPORT_RECORD_SUFFIX = ".yaml"

_SUPPORT_VOCAB = None


def support_vocabulary(root=None, reads=None, owners=None):
    """The incident lifecycle CLOSE event type, READ from the contract that OWNS the vocabulary
    (.veldo/incident.py INCIDENT_EVENT_TYPES) and SELECTED from it by its lifecycle step rather than written as a
    literal here. The owner is loaded by path LAZILY and cached, so compute() stays exactly as light as it was and
    a repository that never derives the support numbers pays nothing. `root` is accepted and deliberately NOT used
    for the OWNER: the vocabulary is ENGINE CODE (a constant inside the engine's own module), exactly like the one
    front-matter parser, so it is resolved against ENGINE while every DATA source is read at root - stated here
    because round 4 read the two as one thing. An engine where the owner is ABSENT resolves to None, the derivation
    then recognizes no close event, and the section stands down to the honest empty state (adoption safe) - but an
    owner PRESENT and unreadable, or one that declares no event type for the close STEP, is a DIFFERENT fact and is
    named rather than borrowing that silence."""
    global _SUPPORT_VOCAB
    if _SUPPORT_VOCAB is None:
        closed, vocab_problem = None, None
        owner = _owners_for(owners).get("incident_contract_owner")
        if owner is not None:
            try:
                for etype in sorted(owner.INCIDENT_EVENT_TYPES):
                    if etype.rsplit(".", 1)[-1] == SUPPORT_CLOSED_STEP:
                        closed = etype
            except Exception as exc:
                vocab_problem = ("the vocabulary owner .veldo/incident.py loaded but its event-type set "
                                 "could NOT be read (%s: %s), so the close event type is unreadable "
                                 "rather than absent" % (type(exc).__name__, exc))
        elif _present(Path(_owners.ENGINE) / ".veldo" / "incident.py"):
            vocab_problem = ("the vocabulary owner .veldo/incident.py EXISTS but could NOT be read, so "
                             "the close event type is unreadable rather than absent and the stand-down "
                             "below is not the adoption-safe one")
        if closed is None and vocab_problem is None and owner is not None:
            vocab_problem = ("the vocabulary owner .veldo/incident.py declares NO event type whose "
                             "lifecycle step is %r, so nothing here can recognize a closure: the "
                             "vocabulary is present and unusable rather than absent" % SUPPORT_CLOSED_STEP)
        _SUPPORT_VOCAB = {"closed_event_type": closed, "problem": vocab_problem}
    vocab = dict(_SUPPORT_VOCAB)
    # .get, not [], on the cached mapping: a caller may PIN the cache to a shape of its own (the suite
    # pins it to prove the adoption-safe stand-down), and a reader that raised on the pinned shape would
    # turn a stand-down into a crash on the very path this pass exists to keep standing.
    if vocab.get("problem") is not None:
        _keep(reads, read_incomplete("incident_vocabulary", ".veldo/incident.py", vocab["problem"]))
    elif vocab.get("closed_event_type") is None:
        _keep(reads, read_complete("incident_vocabulary", ".veldo/incident.py",
                                   "ABSENT: this engine declares no incident vocabulary at all, so no "
                                   "closure is recognized and the section stands down adoption safe"))
    else:
        _keep(reads, read_complete("incident_vocabulary", ".veldo/incident.py",
                                   "READ: the owner declares the close event type %r for the %r step"
                                   % (vocab["closed_event_type"], SUPPORT_CLOSED_STEP)))
    return vocab


# --- the WIRED readers: the ONE impure edge, so the derivation above stays pure -------------------
def load_events(root=None, reads=None):
    """(the RECORDED EVENT STREAM as parsed records, the named problems) from <root>/.veldo/events.jsonl,
    ACCOUNTED line by line. THE ROOT IS HONORED, which round 4 found it was not: both fallbacks in this
    module called metrics.load(), which is bound to the ENGINE's own events.jsonl, so a temporary tree's
    receipts were authenticated against THIS repository's events. An ABSENT stream is complete and empty;
    a line that is not blank and does not parse leaves the read INCOMPLETE and is named, because
    metrics.load() skips such a line silently and a stream read in part is not a shorter history."""
    path = Path(root or ROOT) / ".veldo" / "events.jsonl"
    problems = []
    if not _present(path):
        _keep(reads, read_complete("event_stream", str(path),
                                   "ABSENT: no directory entry exists at this path (lstat), so no event "
                                   "is recorded here and none is missed"))
        return [], problems
    if not os.path.isfile(str(path)):
        _keep(reads, read_incomplete("event_stream", str(path),
                                     "the event stream path EXISTS and is not a regular file (%s), so "
                                     "no recorded event can be read from it: present and unreadable, "
                                     "never an absent stream" % _entry_kind(path)))
        return [], problems
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, ValueError, RecursionError, MemoryError) as exc:
        # ALL FOUR DECLARED CLASSES, because this is a WHOLE-FILE read of an UNROTATED APPEND-ONLY LOG: the
        # ValueError is R5-B2 (read_text raises UnicodeDecodeError, not an OSError, on one undecodable byte,
        # and it took the WHOLE dashboard down), and the MemoryError is R9-B1 - measured, a SPARSE stream
        # exited all four surfaces 1 with zero stdout under a 4 GiB ceiling. Standing THIS source down is the
        # answer, and the codec is named above rather than taken from the locale.
        _keep(reads, read_incomplete("event_stream", str(path),
                                     "the event stream EXISTS and could NOT be read (%s: %s)"
                                     % (type(exc).__name__, exc)))
        return [], problems
    events, blank = [], 0
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            blank += 1
            continue
        record, shortfall = _record_shortfall(lambda text=line: json.loads(text))
        if shortfall is None:
            events.append(record)
        else:
            problems.append(_problem("event_stream", "%s line %d" % (path.name, number),
                                     "the recorded event line EXISTS and %s, so the stream was read in "
                                     "PART: named exactly as a receipt file that does, because a line "
                                     "this pass cannot read as an event is not a shorter history"
                                     % shortfall))
    if problems:
        _keep(reads, _parsed_shortfall("event_stream", path, problems, len(lines) - blank))
    else:
        _keep(reads, read_complete("event_stream", str(path),
                                   "ACCOUNTED: all %d recorded line(s) parsed (%d blank line(s) carry no "
                                   "event and are accounted as such)" % (len(events), blank)))
    return events, problems


def load_receipts(root=None, reads=None):
    """(the RECONCILIATION RECEIPTS as parsed records, the named problems) from the shipped store.
    The store's LOCATION is a literal here, honestly: FilesystemReconciliationStore builds
    .veldo/reconciliations/<id>.json inline and exposes no constant to read, so this reader restates the path and
    a selftest BINDS the two by settling a receipt through the SHIPPED store and reading it back through here. A
    receipt file that cannot be read or does not parse to a mapping is NOT passed to the derivation (fail closed;
    the store itself refuses to overwrite such a file) and is REPORTED BY NAME: its incident then reads as
    UNBACKED_EVENT, which alone would say no receipt was ever written. The store is read through the ACCOUNTED
    enumeration, so an absent store is complete and empty while a store that cannot be listed, holds a
    subdirectory, or holds a file under another suffix leaves this source INCOMPLETE and renders nothing."""
    d = Path(root or ROOT) / ".veldo" / "reconciliations"
    problems = []
    entries, read = _accounted_dir("receipt_store", d, SUPPORT_RECEIPT_SUFFIX)
    out = []
    for p in entries:
        record, shortfall = _record_shortfall(lambda path=p: json.loads(path.read_text(encoding="utf-8")))
        if shortfall is None:
            out.append(record)
        else:
            receipt_unreadable = _problem("receipt_store", p.name, "the receipt file EXISTS and %s, so "
                                          "it authenticates nothing" % shortfall)
            problems.append(receipt_unreadable)
    if problems:
        read = _parsed_shortfall("receipt_store", d, problems, len(entries))
    _keep(reads, read)
    return out, problems


def load_incidents(root=None, reads=None, owners=None):
    """(the INCIDENT RECORDS as parsed veldo.incident/v1 records, the named problems), read through the
    contract's OWN loader (incident.load_incident) and the ONE front-matter parser (validate.parse_yamlish),
    so there is no second parser and no second schema literal. A record that does not parse, or that does not
    declare the contract's schema, contributes no timeline observation and is REPORTED BY NAME rather than
    inferred from a sample count: a record nobody could read and a record nobody wrote produce the same
    missing sample and are different facts. The store is read through the ACCOUNTED enumeration, and this
    reader answers for the incident_timeline source too: the timelines the trends read ARE the records read
    here, so the two rows are affirmed together and neither can be affirmed without the other."""
    d = Path(root or ROOT) / ".veldo" / "incidents"
    problems = []
    owners = _owners_for(owners, reads)
    INC = owners.get("incident_contract_owner")
    V = owners.get("front_matter_parser")
    if INC is None or V is None:
        missing = ".veldo/incident.py" if INC is None else ".veldo/validate.py"
        for source in ("incident_record_store", "incident_timeline"):
            _dependency_declined(source, str(d), "its owner %s" % missing, reads)
        return [], problems
    entries, read = _accounted_dir("incident_record_store", d, SUPPORT_RECORD_SUFFIX)
    out = []
    for p in entries:
        record_unreadable = None
        try:
            record = INC.load_incident(p, V.parse_yamlish)
        except Exception as exc:
            record_unreadable = _problem("incident_record_store", p.name, "the incident record EXISTS and could "
                                         "not be parsed (%s: %s), so its recorded timeline is unreadable rather "
                                         "than unwritten" % (type(exc).__name__, exc))
        else:
            if isinstance(record, dict) and record.get("schema") == INC.SCHEMA_INCIDENT:
                out.append(record)
            else:
                record_unreadable = _problem("incident_record_store", p.name, "the file does not declare the "
                                             "incident record schema %r, so it is not a recorded timeline this "
                                             "pass can read" % INC.SCHEMA_INCIDENT)
        if record_unreadable is not None:
            problems.append(record_unreadable)
    if problems:
        read = _parsed_shortfall("incident_record_store", d, problems, len(entries))
    _keep(reads, read)
    # THE TIMELINES ARE THE RECORDS: this row is affirmed on the SAME accounting, never on its own word.
    # An unreadable TIMESTAMP inside a record that parsed is a per-incident condition the derivation names
    # (UNREADABLE_TIMESTAMP) and not an unread source, which is why it never stands the section down.
    if read_proves_complete(read):
        _keep(reads, read_complete("incident_timeline", str(d),
                                   "ACCOUNTED: the timelines this pass reads are exactly the %d record(s) "
                                   "accounted above; a timestamp recorded and unreadable inside one of "
                                   "them is named per incident rather than left to a missing sample"
                                   % len(out)))
    else:
        _dependency_declined("incident_timeline", str(d), "the incident_record_store read it rides on", reads)
    return out, problems


def load_support_inputs(root=None, events=None):
    """THE WIRED READERS for support_numbers, gathered at this ONE impure edge so the derivation stays pure and
    every stand-down is testable without a filesystem. Returns the keyword arguments support_numbers takes,
    including source_reads: ONE READ RECORD PER DECLARED SOURCE, each carrying a POSITIVE assertion that the
    read was COMPLETE and the BASIS for it. A source that is ABSENT arrives as an honest empty value and an
    AFFIRMED read (no receipts, no incident records, no contract, no corpus, no cost data, no stream); every
    source PRESENT and unreadable arrives as its own named problem AND an unaffirmed read, which stands the
    whole section down. `root` is honored by EVERY read, including the event stream: round 4 found both event
    fallbacks here reading the ENGINE's stream, so a temporary tree's receipts authenticated against this
    repository's events. Reads recorded files only: no live system (NG1), no process, thread or timer (NG3)."""
    root = Path(root or ROOT)
    reads = []
    owners = load_owners(reads)
    stream, stream_problems = load_events(root, reads)
    events = events if events is not None else stream
    corpus_reads = []
    corpus = load_corpus_areas(root, corpus_reads, owners)
    receipts, receipt_problems = load_receipts(root, reads)
    records, record_problems = load_incidents(root, reads, owners)
    area_cost, cost_problems = load_area_cost(root, events, corpus["spec_areas"], corpus_reads, reads,
                                              owners)
    vocab = support_vocabulary(root, reads, owners)
    reads.extend(corpus_reads)
    problems = (list(corpus["problems"]) + receipt_problems + record_problems + cost_problems
                + stream_problems)
    if vocab.get("problem"):
        problems.append(_problem("incident_vocabulary", ".veldo/incident.py", vocab["problem"]))
    return {"receipts": receipts, "incidents": records,
            "spec_areas": corpus["spec_areas"], "contract_areas": corpus["contract_areas"],
            "contract_problem": corpus["contract_problem"], "corpus_problem": corpus["corpus_problem"],
            "area_cost": area_cost, "input_problems": problems,
            "closed_event_type": vocab["closed_event_type"], "source_reads": reads}
