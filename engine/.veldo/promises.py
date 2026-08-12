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

REPORT_KEYS = ("stood_down", "reason", "corpora", "claims", "supported", "contradicted",
               "unsettleable", "author_disagrees", "unreadable")


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
            if not claim.get(need):
                out.append((CAUSE_MISSING_FIELD,
                            "%s: claim %s declares predicate %s, which needs %s"
                            % (where, label, pred, need)))
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
        out["measured"] = (claim.get("note")
                           or "declared unsettleable: no mechanical predicate decides this claim")
        return out

    path = base / target if isinstance(target, str) and target else None
    if path is None:
        out["measured"] = "no target to read"
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
        out["measured"] = "symbol %r is %sdefined" % (name, "" if defined else "NOT ")
        out["outcome"] = SUPPORTED if defined else CONTRADICTED
        return out

    out["measured"] = "no reader for predicate %r" % pred
    return out


def all_claims(pdir=None, root=None, parse=None):
    """[(claim, path, document)] for every WELL-FORMED claim. Malformed claims are excluded here
    and reported by check_promises_dir, so nothing settles a half-read claim."""
    out = []
    for path, data, err in read_corpora(pdir, root, parse):
        if err is not None or not isinstance(data, dict):
            continue
        for claim in (data.get("claims") or []):
            if not claim_problems(claim, str(path)):
                out.append((claim, path, data.get("document")))
    return out


def promise_report(pdir=None, root=None, parse=None):
    """ONE key shape whether it stood down or not. NO SCORE: no ratio, no percentage and no float
    anywhere, because a proportion of a corpus nobody enumerated is the number that gets quoted."""
    d = Path(pdir) if pdir is not None else default_promises_dir(root)
    rep = {"stood_down": True, "reason": None, "corpora": 0, "claims": 0, "supported": [],
           "contradicted": [], "unsettleable": [], "author_disagrees": [], "unreadable": []}
    if not d.is_dir():
        rep["reason"] = STAND_DOWN_NO_DIRECTORY
        return rep
    corpora = read_corpora(d, root, parse)
    rep["corpora"] = len(corpora)
    rep["unreadable"] = [str(p) for p, _data, err in corpora if err is not None]
    claims = all_claims(d, root, parse)
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
        rep["reason"] = (STAND_DOWN_NOTHING_SETTLEABLE if claims
                         else "no corpus declares a claim at all")
        return rep
    rep["stood_down"] = False
    return rep


def report_lines(rep):
    """The report as lines a stranger reads. Every contradiction carries its reading, so a human
    can see whether the predicate was pointed at the wrong file before deleting a sentence."""
    if rep["stood_down"]:
        return ["promise corpus: stood down - %s" % rep["reason"]]
    lines = ["promise corpus: %d claim(s) in %d corpus(es): %d supported, %d CONTRADICTED, "
             "%d unsettleable"
             % (rep["claims"], rep["corpora"], len(rep["supported"]), len(rep["contradicted"]),
                len(rep["unsettleable"]))]
    if rep["unreadable"]:
        lines.append("  %d corpus file(s) COULD NOT BE READ and are absent from every count "
                     "above: %s" % (len(rep["unreadable"]), ", ".join(rep["unreadable"])))
    for s in rep["contradicted"]:
        lines.append("  CONTRADICTED %s (%s %s): %s -- predicate %s on %s %s"
                     % (s["claim"], s["document"], s["locator"], s["text"], s["predicate"],
                        s["target"], s["measured"]))
    for s in rep["unsettleable"]:
        lines.append("  UNSETTLEABLE %s (%s %s): %s -- %s"
                     % (s["claim"], s["document"], s["locator"], s["text"], s["measured"]))
    for s in rep["author_disagrees"]:
        lines.append("  AUTHOR DISAGREES %s: believed %s, the tree says %s (%s)"
                     % (s["claim"], s["believed"], s["outcome"], s["measured"]))
    return lines
