#!/usr/bin/env python3
"""VELDO promise corpus: a claim a document makes, settled against the tree.

THE HOLE THIS CLOSES. On 2026-08-10 an audit of this project's own shipped documents found 64
false claims across 8 documents - sentences asserting a capability the tree did not have - with
the gate green throughout. Every one was checkable. Nothing checked them, because they lived in
prose and the gate reads code.

WHAT IS AND IS NOT HERE. Reading a document and deciding which sentences make checkable claims
is a judgement call, and a machine that pretended to make it would produce exactly the confident
wrongness this method keeps finding. So EXTRACTION IS AN AUTHORING JOB - a task in VELDO-0003's
queue - whose product is a claim record carrying a DECLARED PREDICATE. This module is the
mechanical half: validate the records, run each predicate over the tree, and report. The same
split the behaviour floor makes, for the same reason.

THE SETTLEMENT IS DERIVED, NEVER READ. A claim may record what its author BELIEVED; that field is
never consulted when settling, and exists only so the report can name a claim whose author and
whose tree disagree. Same rule as VELDO-0002 for a run's own word and VELDO-0003 for a worker's.

A CONTRADICTION CARRIES WHAT IT MEASURED. The audit that motivated this raised fifteen accusations
and FIVE WERE OVERTURNED on challenge. An accusation whose evidence is not in the record is
indistinguishable from a correct one, and the cost of being wrong is deleting a true sentence from
a shipped document. So a settlement is a MEASUREMENT WITH THE READING ATTACHED - the predicate, the
target it read, and what it found - recorded for supported claims too, because a settlement that
only explains itself when it accuses is one nobody can audit.

UNSETTLEABLE IS FIRST-CLASS. A claim no declared predicate can decide is recorded as such with its
reason, counted separately, and never folded into supported: "the tree supports this" and "nothing
here can decide this" are opposite facts about how far to trust the report.

IT GATES NOTHING. PLAN-0018 NG3: a completeness organ that BLOCKED on a heuristic verdict would cut
true sentences and stop real work. Advisory, loud, human-resolved. No score is printed - no ratio,
no percentage, no float - because a proportion of a corpus nobody enumerated is the number that
would get quoted.
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SCHEMA = "veldo.promises/v1"

CORPUS_KEYS = {"schema", "id", "version", "document", "claims"}
CLAIM_KEYS = {"id", "locator", "text", "predicate", "target", "needle", "symbol", "believed",
              "note"}
CORPUS_REQUIRED = ("schema", "id", "document", "claims")
CLAIM_REQUIRED = ("id", "locator", "text", "predicate")

# DELIBERATELY TINY. A predicate that needed judgement would be a machine making a review-lane
# call. Each maps to one mechanical reading of the tree and nothing else.
PRED_PATH_EXISTS = "path_exists"
PRED_PATH_ABSENT = "path_absent"
PRED_TEXT_PRESENT = "text_present"
PRED_TEXT_ABSENT = "text_absent"
PRED_SYMBOL_DEFINED = "symbol_defined"
PRED_UNSETTLEABLE = "unsettleable"
PREDICATES = (PRED_PATH_EXISTS, PRED_PATH_ABSENT, PRED_TEXT_PRESENT, PRED_TEXT_ABSENT,
              PRED_SYMBOL_DEFINED, PRED_UNSETTLEABLE)

# Which predicates need which extra field, so a claim that cannot be run is refused at read time
# rather than settling as unsettleable and looking like an honest limit.
PRED_NEEDS = {
    PRED_PATH_EXISTS: ("target",),
    PRED_PATH_ABSENT: ("target",),
    PRED_TEXT_PRESENT: ("target", "needle"),
    PRED_TEXT_ABSENT: ("target", "needle"),
    PRED_SYMBOL_DEFINED: ("target", "symbol"),
    PRED_UNSETTLEABLE: (),
}

SUPPORTED = "SUPPORTED"
CONTRADICTED = "CONTRADICTED"
UNSETTLEABLE = "UNSETTLEABLE"
OUTCOMES = (SUPPORTED, CONTRADICTED, UNSETTLEABLE)

CAUSE_UNREADABLE = "PROMISE_UNREADABLE"
CAUSE_MISSING_FIELD = "PROMISE_MISSING_FIELD"
CAUSE_KEY_UNRECOGNIZED = "PROMISE_KEY_UNRECOGNIZED"
CAUSE_PREDICATE_UNKNOWN = "PROMISE_PREDICATE_UNKNOWN"
CAUSE_DECLARED_TWICE = "PROMISE_DECLARED_TWICE"
CAUSE_TARGET_UNBOUND = "PROMISE_TARGET_UNBOUND"
CAUSES = (CAUSE_UNREADABLE, CAUSE_MISSING_FIELD, CAUSE_KEY_UNRECOGNIZED,
          CAUSE_PREDICATE_UNKNOWN, CAUSE_DECLARED_TWICE, CAUSE_TARGET_UNBOUND)

STAND_DOWN_NO_DIRECTORY = ("no .veldo/promises/ directory: no document's claims have been "
                           "extracted here, which is NOT the same fact as a document making no "
                           "false claim")
STAND_DOWN_NOTHING_SETTLEABLE = ("every claim in this corpus is UNSETTLEABLE, so no predicate "
                                 "here decided anything: reporting zero contradictions would be "
                                 "a measurement nobody made")
# NAMED SEPARATELY FROM "no corpus declares a claim at all", because they are different facts and
# the stand-down reason is the one sentence a human reads. A corpus whose only claims are malformed
# DOES declare claims; saying nobody declared one misnames what happened, in a module whose whole
# thesis is that a settlement must name what it measured.
STAND_DOWN_NOTHING_READABLE = ("this corpus DOES declare claims and not one of them could be read "
                               "as a claim, so no predicate read anything: the malformed claims "
                               "are named below and none of them is counted anywhere above")

REPORT_KEYS = ("stood_down", "reason", "corpora", "declared", "claims", "supported",
               "contradicted", "unsettleable", "author_disagrees", "unreadable", "malformed")


class PromiseRecordError(ValueError):
    """A corpus could not be read as a corpus. Reported by the caller's reporter, never swallowed
    into a count."""


def default_promises_dir(root=None):
    return (Path(root) if root is not None else ROOT) / ".veldo" / "promises"


def load_corpus(path, parse):
    """Parse one corpus with the CALLER'S front-matter parser, so this module ships no second
    YAML parser."""
    p = Path(path)
    try:
        text = p.read_text()
    except OSError as e:
        raise PromiseRecordError("%s: %s: %s" % (p, CAUSE_UNREADABLE, e))
    try:
        data = parse(text)
    except Exception as e:                        # noqa: BLE001 - any parser failure is one fact
        raise PromiseRecordError("%s: %s: corpus outside the record subset: %s"
                                 % (p, CAUSE_UNREADABLE, e))
    if not isinstance(data, dict):
        raise PromiseRecordError("%s: %s: a corpus is a mapping, got %s"
                                 % (p, CAUSE_UNREADABLE, type(data).__name__))
    return data


def target_problems(target):
    """Why a target cannot be read, or None. IT MUST NAME A PATH INSIDE THE REPOSITORY: a corpus
    is an AUTHORED file, so an absolute path or one escaping the tree would let a claim be settled
    against something outside it."""
    if not isinstance(target, str) or not target.strip():
        return "target is empty, so no predicate could read anything"
    if target.startswith("/") or (len(target) > 1 and target[1] == ":"):
        return "target '%s' is absolute, so it would be read from outside this repository" % target
    if ".." in [seg for seg in target.replace("\\", "/").split("/") if seg]:
        return "target '%s' escapes the repository with '..'" % target
    return None


def claim_problems(claim, where):
    """Every structural problem with ONE claim, as (cause, message) pairs - all of them, because
    an author fixing one at a time is what a named taxonomy prevents."""
    out = []
    if not isinstance(claim, dict):
        return [(CAUSE_UNREADABLE, "%s: a claim is a mapping, got %s"
                 % (where, type(claim).__name__))]
    cid = claim.get("id") if isinstance(claim.get("id"), str) else ""
    label = cid or where
    for field in CLAIM_REQUIRED:
        if not claim.get(field):
            out.append((CAUSE_MISSING_FIELD, "%s: claim %s declares no %s"
                        % (where, label, field)))
    for key in sorted(set(claim) - CLAIM_KEYS):
        out.append((CAUSE_KEY_UNRECOGNIZED,
                    "%s: claim %s declares unrecognised key '%s' (allowed: %s)"
                    % (where, label, key, ", ".join(sorted(CLAIM_KEYS)))))
    pred = claim.get("predicate")
    if pred is not None and pred not in PREDICATES:
        out.append((CAUSE_PREDICATE_UNKNOWN,
                    "%s: claim %s declares predicate '%s' (allowed: %s). The vocabulary is small "
                    "on purpose: a predicate needing judgement would be a machine making a "
                    "review-lane call" % (where, label, pred, ", ".join(PREDICATES))))
    elif pred is not None:
        for need in PRED_NEEDS[pred]:
            val = claim.get(need)
            if not val:
                out.append((CAUSE_MISSING_FIELD,
                            "%s: claim %s declares predicate %s, which needs %s"
                            % (where, label, pred, need)))
            elif need in ("needle", "symbol") and not isinstance(val, str):
                # A NEEDLE AND A SYMBOL ARE TEXT, AND THE ONE PARSER COERCES A BARE NUMBER.
                # `needle: 200` is the obvious way to write "the document says 200 countries", and
                # the front-matter subset yields the INT 200, which `in` cannot search a string for
                # and which a symbol lookup answers NO to - a FALSE ACCUSATION carrying a true
                # looking reading. Refused at read time, like every other claim that cannot be run.
                out.append((CAUSE_MISSING_FIELD,
                            "%s: claim %s declares %s as %s (%r) and predicate %s reads TEXT: "
                            "quote it, because the front-matter subset turns a bare number into an "
                            "int and no predicate can search text for one"
                            % (where, label, need, type(val).__name__, val, pred)))
        if claim.get("target") is not None:
            why = target_problems(claim.get("target"))
            if why:
                out.append((CAUSE_TARGET_UNBOUND, "%s: claim %s: %s" % (where, label, why)))
    if claim.get("believed") is not None and claim.get("believed") not in OUTCOMES:
        out.append((CAUSE_MISSING_FIELD,
                    "%s: claim %s declares believed '%s' (allowed: %s)"
                    % (where, label, claim.get("believed"), ", ".join(OUTCOMES))))
    return out


def corpus_problems(data, where):
    """Every structural problem with one corpus, its own keys included."""
    out = []
    for field in CORPUS_REQUIRED:
        if not data.get(field):
            out.append((CAUSE_MISSING_FIELD, "%s: corpus declares no %s" % (where, field)))
    for key in sorted(set(data) - CORPUS_KEYS):
        out.append((CAUSE_KEY_UNRECOGNIZED,
                    "%s: corpus declares unrecognised key '%s' (allowed: %s)"
                    % (where, key, ", ".join(sorted(CORPUS_KEYS)))))
    if data.get("schema") not in (None, SCHEMA):
        out.append((CAUSE_UNREADABLE, "%s: corpus declares schema '%s', expected %s"
                    % (where, data.get("schema"), SCHEMA)))
    claims = data.get("claims")
    if claims is not None and not isinstance(claims, list):
        out.append((CAUSE_UNREADABLE, "%s: claims is %s rather than a list"
                    % (where, type(claims).__name__)))
        return out
    for claim in (claims or []):
        out.extend(claim_problems(claim, where))
    return out


def read_corpora(pdir=None, root=None, parse=None):
    """[(path, data_or_None, error_or_None)] for every corpus on disk, sorted. An unreadable
    corpus is CARRIED as an error, never dropped: a dropped file is a coverage figure quoted
    without the weakness that produced it."""
    d = Path(pdir) if pdir is not None else default_promises_dir(root)
    out = []
    if not d.is_dir():
        return out
    for p in sorted(d.glob("*.yaml")):
        try:
            out.append((p, load_corpus(p, parse), None))
        except PromiseRecordError as e:
            out.append((p, None, str(e)))
    return out


def check_promises_dir(pdir, root, parse, fail):
    """Validate every corpus structurally. Adoption safe: an absent directory returns clean. A
    claim id in two files is refused with BOTH files named."""
    d = Path(pdir)
    if not d.is_dir():
        return 0
    errs = 0
    seen = {}
    for path, data, err in read_corpora(d, root, parse):
        if err is not None:
            errs += fail(path, err)
            continue
        for cause, msg in corpus_problems(data, str(path)):
            errs += fail(path, "%s: %s" % (cause, msg))
        for claim in (data.get("claims") or []):
            if isinstance(claim, dict) and isinstance(claim.get("id"), str) and claim.get("id"):
                seen.setdefault(claim["id"], []).append(str(path))
    for cid, paths in sorted(seen.items()):
        if len(paths) > 1:
            errs += fail(paths[0], "%s: claim %s is declared by %d files: %s"
                         % (CAUSE_DECLARED_TWICE, cid, len(paths), ", ".join(sorted(paths))))
    return errs


def _symbol_defined(text, name):
    """Whether name is DEFINED at any level of the module - a def, a class, or an assignment. AST,
    not a substring, because a docstring naming a function is prose and a comment is not code."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) \
                and node.name == name:
            return True
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store) and node.id == name:
            return True
    return False


def _outside_repository(path, base):
    """Why this target lies outside the tree once the filesystem has had its say, or None.

    target_problems refuses an absolute path and a '..' segment in the TEXT of a target. A symlink
    committed in the tree is neither, and a claim settled against a file outside the repository is
    an accusation nobody can check - so the resolved path is compared to the resolved root here,
    and a target that leaves the tree settles UNSETTLEABLE rather than accusing anything."""
    try:
        rp, rb = Path(path).resolve(), Path(base).resolve()
    except OSError as e:
        return "target could not be resolved: %s" % e
    if rp != rb and rb not in rp.parents:
        return ("target resolves to %s, which is outside this repository, so nothing here can "
                "settle the claim" % rp)
    return None


def settle(claim, root=None):
    """Run ONE claim's predicate over the tree and return the settlement.

    THE READING IS PART OF THE ANSWER. Every settlement carries the predicate, the target it read
    and what it found, for SUPPORTED as well as CONTRADICTED, because the audit that produced this
    item had five of fifteen accusations overturned and an accusation whose evidence is not in the
    record is indistinguishable from a correct one. `believed` is never consulted."""
    base = Path(root) if root is not None else ROOT
    pred = claim.get("predicate")
    target = claim.get("target")
    out = {"claim": claim.get("id"), "predicate": pred, "target": target,
           "outcome": UNSETTLEABLE, "measured": None,
           "believed": claim.get("believed")}

    if pred == PRED_UNSETTLEABLE:
        # ATTRIBUTED TO ITS AUTHOR, because this reading is a SENTENCE SOMEBODY WROTE and every
        # other value in this column is a machine reading a file. A declared unsettleable settles
        # nothing and must not be able to pass for a measurement.
        out["measured"] = ("DECLARED unsettleable by the claim's author, so no predicate read "
                           "anything here: %s"
                           % (claim.get("note") or "the author gave no reason"))
        return out

    path = base / target if isinstance(target, str) and target else None
    if path is None:
        out["measured"] = "no target to read"
        return out

    escaped = _outside_repository(path, base)
    if escaped is not None:
        out["measured"] = escaped
        return out

    # A NEEDLE AND A SYMBOL ARE TEXT, AND THEY ARE CHECKED BEFORE THE FILESYSTEM IS TOUCHED because
    # the defect is in the CLAIM and does not depend on what the target holds. check_promises_dir
    # refuses both at read time; the guard is here as well because a settler that CRASHES on a claim
    # the validator would have refused takes every other claim in every other corpus down with it,
    # and this module's law is that a claim which cannot be run is NAMED rather than thrown. The one
    # front-matter parser coerces `needle: 200` to an int, which `in` cannot search text for, and an
    # int symbol would resolve to NOTHING and produce a contradiction - a false accusation.
    if pred in (PRED_TEXT_PRESENT, PRED_TEXT_ABSENT) and not isinstance(claim.get("needle"), str):
        out["measured"] = ("needle is %s rather than text, so nothing could be searched for"
                           % type(claim.get("needle")).__name__)
        return out
    if pred == PRED_SYMBOL_DEFINED and not isinstance(claim.get("symbol"), str):
        out["measured"] = ("symbol is %s rather than a name, so nothing could be resolved"
                           % type(claim.get("symbol")).__name__)
        return out

    if pred in (PRED_PATH_EXISTS, PRED_PATH_ABSENT):
        exists = path.exists()
        out["measured"] = "path %s" % ("exists" if exists else "does not exist")
        want = exists if pred == PRED_PATH_EXISTS else not exists
        out["outcome"] = SUPPORTED if want else CONTRADICTED
        return out

    try:
        text = path.read_text(errors="replace")
    except OSError as e:
        out["measured"] = "target could not be read: %s" % e
        return out

    if pred in (PRED_TEXT_PRESENT, PRED_TEXT_ABSENT):
        needle = claim.get("needle")
        found = needle in text
        out["measured"] = ("found %r at offset %d" % (needle, text.index(needle))
                           if found else "did not find %r in %d characters" % (needle, len(text)))
        want = found if pred == PRED_TEXT_PRESENT else not found
        out["outcome"] = SUPPORTED if want else CONTRADICTED
        return out

    if pred == PRED_SYMBOL_DEFINED:
        name = claim.get("symbol")
        defined = _symbol_defined(text, name)
        if defined is None:
            out["measured"] = "target does not parse as Python, so no symbol can be resolved"
            return out
        # WHAT THE PREDICATE LOOKED FOR, NOT AN ASSERTION ABOUT THE NAME. _symbol_defined reads
        # defs, classes and Name-Store assignments, so an IMPORTED binding is not found - and
        # "symbol 'ast' is NOT defined" is a falsehood in the evidence column, which is the wrong
        # accusation failure mode this criterion exists for. The reading now states its own reach.
        out["measured"] = (("symbol %r is defined here by a def, a class or an assignment" % name)
                           if defined else
                           ("no def, class or assignment named %r anywhere in this target (an "
                            "imported binding is not a definition and is not counted)" % name))
        out["outcome"] = SUPPORTED if defined else CONTRADICTED
        return out

    out["measured"] = "no reader for predicate %r" % pred
    return out


def partition_claims(pdir=None, root=None, parse=None):
    """(well_formed, malformed) over every claim a READABLE corpus declares.

    THE MALFORMED HALF IS RETURNED, NEVER DROPPED. It used to be filtered out here and left to
    check_promises_dir - and nothing in an adopting tree calls that, because this module gates
    nothing, so the report was the only surface and it counted ONE claim where the author wrote
    two and then printed a confident zero over the difference. The file-level version of this
    weakness was already carried loudly; this is the claim-level version of the same fact.

    well_formed is [(claim, path, document)] as before. malformed is [dict] with the claim id (or
    None when even that is missing), the file, the document, the named causes and the messages, so
    the report can say what it could not read instead of quietly reporting less."""
    good, bad = [], []
    for path, data, err in read_corpora(pdir, root, parse):
        if err is not None or not isinstance(data, dict):
            continue
        claims = data.get("claims")
        for claim in (claims if isinstance(claims, list) else []):
            problems = claim_problems(claim, str(path))
            if not problems:
                good.append((claim, path, data.get("document")))
                continue
            cid = claim.get("id") if isinstance(claim, dict) else None
            bad.append({"claim": cid if isinstance(cid, str) and cid else None,
                        "declared_in": str(path), "document": data.get("document"),
                        "causes": sorted({cause for cause, _msg in problems}),
                        "problems": [msg for _cause, msg in problems]})
    return good, bad


def all_claims(pdir=None, root=None, parse=None):
    """[(claim, path, document)] for every WELL-FORMED claim: the first half of
    partition_claims, kept as its own name because a caller that only settles wants exactly this
    and the malformed half is reported by promise_report rather than dropped by anyone."""
    return partition_claims(pdir, root, parse)[0]


def promise_report(pdir=None, root=None, parse=None):
    """ONE key shape whether it stood down or not. NO SCORE: no ratio, no percentage and no float
    anywhere, because a proportion of a corpus nobody enumerated is the number that gets quoted."""
    d = Path(pdir) if pdir is not None else default_promises_dir(root)
    rep = {"stood_down": True, "reason": None, "corpora": 0, "declared": 0, "claims": 0,
           "supported": [], "contradicted": [], "unsettleable": [], "author_disagrees": [],
           "unreadable": [], "malformed": []}
    if not d.is_dir():
        rep["reason"] = STAND_DOWN_NO_DIRECTORY
        return rep
    corpora = read_corpora(d, root, parse)
    rep["corpora"] = len(corpora)
    rep["unreadable"] = [str(p) for p, _data, err in corpora if err is not None]
    claims, malformed = partition_claims(d, root, parse)
    rep["malformed"] = malformed
    # DECLARED is what the authors wrote, claims is what could be settled, and the two are
    # separate keys on purpose: one number that quietly means the second is how a corpus loses a
    # claim without anybody being told.
    rep["declared"] = len(claims) + len(malformed)
    rep["claims"] = len(claims)
    for claim, path, document in claims:
        s = settle(claim, root)
        s["declared_in"] = str(path)
        s["document"] = document
        s["locator"] = claim.get("locator")
        s["text"] = claim.get("text")
        if s["outcome"] == SUPPORTED:
            rep["supported"].append(s)
        elif s["outcome"] == CONTRADICTED:
            rep["contradicted"].append(s)
        else:
            rep["unsettleable"].append(s)
        if s["believed"] and s["believed"] != s["outcome"] and s["outcome"] != UNSETTLEABLE:
            rep["author_disagrees"].append(s)
    settleable = len(rep["supported"]) + len(rep["contradicted"])
    if not claims or settleable == 0:
        if claims:
            rep["reason"] = STAND_DOWN_NOTHING_SETTLEABLE
        elif malformed:
            rep["reason"] = STAND_DOWN_NOTHING_READABLE
        else:
            rep["reason"] = "no corpus declares a claim at all"
        return rep
    rep["stood_down"] = False
    return rep


def report_lines(rep):
    """The report as lines a stranger reads. Every contradiction carries its reading, so a human
    can see whether the predicate was pointed at the wrong file before deleting a sentence.

    NO SCORE ON THIS SURFACE EITHER: no ratio, no percentage and no float is printed here, because
    THIS is where a number would be quoted from and a proportion of a corpus nobody enumerated is
    exactly the number that gets quoted.

    THE WEAKNESSES ARE CARRIED ON BOTH PATHS. A stand-down that dropped the unreadable files and
    the malformed claims would be the same silence with a calmer word on it, so they are printed
    whether the read model answered or stood down."""
    if rep["stood_down"]:
        lines = ["promise corpus: stood down - %s" % rep["reason"]]
    else:
        lines = ["promise corpus: %d claim(s) in %d corpus(es): %d supported, %d CONTRADICTED, "
                 "%d unsettleable"
                 % (rep["claims"], rep["corpora"], len(rep["supported"]),
                    len(rep["contradicted"]), len(rep["unsettleable"]))]
    if rep["unreadable"]:
        lines.append("  %d corpus file(s) COULD NOT BE READ and are absent from every count "
                     "above: %s" % (len(rep["unreadable"]), ", ".join(rep["unreadable"])))
    if rep["malformed"]:
        lines.append("  %d DECLARED claim(s) COULD NOT BE READ AS CLAIMS and are absent from every "
                     "count above: %s"
                     % (len(rep["malformed"]),
                        ", ".join("%s in %s (%s)" % (m["claim"] or "an unnamed claim",
                                                     m["declared_in"], ", ".join(m["causes"]))
                                  for m in rep["malformed"])))
    for s in rep["contradicted"]:
        lines.append("  CONTRADICTED %s (%s %s): %s | predicate %s on %s: %s"
                     % (s["claim"], s["document"], s["locator"], s["text"], s["predicate"],
                        s["target"], s["measured"]))
    for s in rep["unsettleable"]:
        lines.append("  UNSETTLEABLE %s (%s %s): %s | %s"
                     % (s["claim"], s["document"], s["locator"], s["text"], s["measured"]))
    for s in rep["author_disagrees"]:
        lines.append("  AUTHOR DISAGREES %s: believed %s, the tree says %s (%s)"
                     % (s["claim"], s["believed"], s["outcome"], s["measured"]))
    return lines
