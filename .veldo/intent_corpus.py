#!/usr/bin/env python3
"""VELDO intent corpus at runtime (veldo.intent_corpus/v1): the queryable index of the
project's OWN recorded artifacts, so the production support responder does DIAGNOSIS FROM
ARTIFACTS instead of diagnosis from memory.

This is the W3 organ of PLAN-0012 and the machinery behind Invention #3's design center.
When agents author everything, the five-minute diagnosis that used to be a free byproduct
of authorship is gone: whoever gets paged is a stranger to the code. But the method already
produces what the old world never had - every behavior traces to a specification (its
acceptance criteria), every change to its proof and its verdict, every module to its place
in the declared shape - so the responder does not need to have written the code. It ASKS
the record: what specification governs this behavior, what did it promise, what proved it,
what changed here recently, and where the affected module sits in the declared shape when
an architecture contract exists. Total recall without authorship.

WHAT THIS IS, precisely (RULE #6, the right architecture, no shortcut):

  A READ OVER THE PROJECT'S OWN RECORD. The corpus INDEXES the existing recorded artifacts;
  it introduces NO new store, NO new parser, and NO new instrumentation (NG5). It reuses
  the repo's own readers - the one front-matter parser (validate.parse_yamlish) for specs
  and plans, json for proofs and verdicts, validate.proof_digest for a proof's identity,
  validate.plan_registry for the plans, .veldo/decision.py for decision records, and
  validate.load_repo_contract for the architecture contract - so there is one truth and no
  second parser. Git history and the event stream (.veldo/events.jsonl) are the recorded
  change log; git is read IN-SESSION and synchronously through an injected reader (the
  default is a thin synchronous `git log`, never a detached or background process, NG3).

  AN ARTIFACT-GROUNDED ANSWER, NEVER A FABRICATED ONE. Diagnosis from artifacts means the
  answer rests on real artifacts or it says it cannot. A query that resolves returns a
  Trace whose every element cites a real artifact path (the spec, the proof manifest, the
  verdict). A query for a behavior no recorded artifact governs returns a Trace with
  governed=False and the reason "no governing artifact" - it NEVER invents a spec, a
  criterion, a proof, or a verdict. The no-fabrication guarantee is the product: a
  responder that fabricated a governing spec would be worse than one that admitted it does
  not know.

  FAIL CLOSED, DEGRADE DOWN (C3). A malformed query (an empty or non-string spec id, path,
  or behavior) refuses by name. A malformed corpus artifact (a spec with no front matter, a
  proof manifest that is not valid JSON) refuses at build time, by name. And the cross-plan
  join is soft (C7): the module-to-area answer resolves against a PLAN-0011 architecture
  contract when one exists and STANDS DOWN honestly to spec and git level when none is
  present - it never fakes an area.

Two postures shared with the sibling organs .veldo/incident.py and .veldo/evidence.py:
  ADOPTION SAFE. A repository with no specs and no proofs builds an EMPTY corpus that
  stands down: every query returns an ungoverned Trace or an empty change list, no error,
  byte-identically unaffected.
  FAIL CLOSED. The moment a malformed artifact or a malformed query appears, the corpus
  refuses by name.

Honest deferrals (NG1/the plan's ordered delivery, not a dodge): the FIRST CONSUMER is the
responder investigation loop WARP-1204 (W4), the in-session agent that, given an incident,
reads this corpus and the evidence plane and produces a cited diagnosis and a proposal;
this module is the query surface it reads, not the agent. Landing a corpus check into
validate.py run_all and the /veldo:init lay-down is WARP-1211 (W11). Nothing here
investigates, proposes, or executes; the corpus is a read and only a read, and it opens no
connection to any live system - the only external program it ever runs is a synchronous,
in-session `git log` over this repository's own history.
"""
from pathlib import Path
import fnmatch
import importlib.util
import json

SCHEMA = "veldo.intent_corpus/v1"

# The proof-corpus enumeration (WARP-0727), loaded BY PATH the way this module's other organs
# load their siblings, so there is ONE owner of what a corpus path is and no import cycle. A
# private `glob("*/verdict*.json")` here would be another spelling of the set .veldo/events.py
# derives entitlement from, and the gap between two spellings is the defect.
_vcspec = importlib.util.spec_from_file_location(
    "veldo_verdict_corpus", Path(__file__).resolve().parent / "verdict_corpus.py")
_VC = importlib.util.module_from_spec(_vcspec)
_vcspec.loader.exec_module(_VC)


def _corpus_files(proof_dir, pattern):
    """The corpus artifacts of one pattern under a caller-named proof directory, through the
    ONE enumeration, so this reader agrees by construction with the set the projection derives
    entitlement from and the set the contract validator validates."""
    d = Path(proof_dir)
    return _VC.corpus_in_dir(d, pattern) if d.is_dir() else []


class IntentCorpusError(RuntimeError):
    """A query was malformed, or a corpus artifact was malformed. Raised by name so a
    refusal never silently no-ops (parallels EvidencePlaneError and IncidentContractError).
    An UNGOVERNED behavior is NOT this error: it is a truthful Trace(governed=False), so the
    responder can tell a malformed request apart from an honest "no artifact governs this"."""


# --- the git seam: in-session, synchronous, NEVER detached (mirrors fleet.py) ------------

def default_git_reader(root, *args):
    """The default change-log reader: a single synchronous `git ...` over this repository's
    own history, read IN-SESSION. subprocess is imported LAZILY here (never at module top),
    exactly as fleet.py imports it only for its in-line `git worktree` helper, and this
    reader spawns NO detached, forked, session-detached, or background process (NG3); it
    runs git synchronously and waits for it. Returns the non-empty output lines, or [] when
    git is unavailable or the command fails (so a query simply has no git history, never an
    error). A runtime may inject its own reader; this default keeps the corpus
    batteries-included."""
    import subprocess  # lazy: the only external program is a synchronous in-session git read
    try:
        r = subprocess.run(["git", *args], cwd=str(root), capture_output=True, text=True)
    except (OSError, ValueError):
        return []
    if r.returncode != 0:
        return []
    return [ln.rstrip("\n") for ln in r.stdout.splitlines() if ln.strip()]


# --- helpers -----------------------------------------------------------------------------

def _is_str(v):
    return isinstance(v, str) and v.strip() != ""


def _as_list(v):
    return v if isinstance(v, list) else []


def _require_query(v, what):
    """A query argument must be a non-empty string, or the corpus REFUSES by name (fail
    closed on a malformed query, C3). This is the boundary that keeps a garbage query from
    quietly returning a garbage answer."""
    if not _is_str(v):
        raise IntentCorpusError("malformed query: %s must be a non-empty string (got %r)" % (what, v))
    return v.strip()


def _fold_text(v):
    """Normalize a scalar the ONE front-matter parser produced from a `>` or `|` block
    scalar. parse_yamlish does not interpret the YAML block indicator (the contract is a
    subset, not full YAML), so a `text: >` field arrives as its folded body with a leading
    ">" (or "|") token; strip that leading indicator so the recorded criterion reads as
    authored. This normalizes the parser's own representation; it is not a second parser."""
    if not isinstance(v, str):
        return v
    s = v.strip()
    if s[:2] in ("> ", "| "):
        return s[2:].strip()
    if s in (">", "|"):
        return ""
    return s


# --- the Trace: an artifact-grounded answer that never fabricates ------------------------

class Trace:
    """One artifact-grounded answer from the corpus. When governed is True the answer rests
    on real artifacts and `citations` lists their real paths (the spec, the proof manifest,
    the verdict); the responder cites these. When governed is False the corpus found NO
    governing artifact and says so in `reason` - it carries no fabricated spec, criteria,
    proof, or verdict. This is the diagnosis-from-artifacts guarantee made concrete: an
    answer is grounded, or it is honestly absent, never invented."""

    __slots__ = ("governed", "reason", "spec_id", "title", "status", "criteria", "plan",
                 "work", "proof", "verdicts", "areas", "contract_present", "recent_changes",
                 "matched_by", "candidates", "citations")

    def __init__(self, governed, reason=None, spec_id=None, title=None, status=None,
                 criteria=None, plan=None, work=None, proof=None, verdicts=None, areas=None,
                 contract_present=False, recent_changes=None, matched_by=None,
                 candidates=None, citations=None):
        self.governed = bool(governed)
        self.reason = reason
        self.spec_id = spec_id
        self.title = title
        self.status = status
        self.criteria = criteria or []          # the acceptance criteria = what the spec PROMISED
        self.plan = plan
        self.work = work
        self.proof = proof                       # the proof record, or None (never fabricated)
        self.verdicts = verdicts or []           # the review verdict(s), or [] (never fabricated)
        self.areas = areas                        # a set of area ids, or None when no contract
        self.contract_present = bool(contract_present)
        self.recent_changes = recent_changes      # {git, events} when enriched, else None
        self.matched_by = matched_by              # how the behavior resolved (spec_id | footprint)
        self.candidates = candidates or []        # every spec a footprint query matched (grounded)
        self.citations = citations or []          # the REAL artifact paths this answer rests on

    @classmethod
    def ungoverned(cls, reason, spec_id=None):
        """The honest negative: no governing artifact. Carries the reason and nothing
        fabricated, so the caller can never mistake it for a grounded answer."""
        return cls(False, reason=reason, spec_id=spec_id)

    def as_dict(self):
        return {k: (sorted(v) if isinstance(v, set) else v)
                for k, v in ((s, getattr(self, s)) for s in self.__slots__)}

    def __repr__(self):
        if not self.governed:
            return "<Trace ungoverned reason=%r>" % self.reason
        return "<Trace spec=%r status=%r criteria=%d proof=%s verdicts=%d citations=%d>" % (
            self.spec_id, self.status, len(self.criteria),
            "yes" if self.proof else "none", len(self.verdicts), len(self.citations))


# --- readers over the recorded artifacts (reuse the repo's own readers, injected) --------

def _spec_front_matter(text, parse):
    """The full front matter of a spec, parsed by the ONE injected parser, so lists like
    acceptance_criteria, placement, and footprint arrive as real structures. A spec with no
    front matter, or one outside the parser subset, is a malformed corpus artifact and
    REFUSES by name (fail closed)."""
    import re
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        raise IntentCorpusError("corpus artifact malformed: a spec has no YAML front matter")
    try:
        return parse(m.group(1))
    except ValueError as e:
        raise IntentCorpusError("corpus artifact malformed: a spec front matter is outside the record subset: %s" % e)


def _read_specs(specs_dir, parse):
    """{spec_id: record} for every spec under specs_dir. Reuses the injected parser; builds
    no second parser. A malformed spec refuses at build time (fail closed). Absent dir: {}
    (adoption safe)."""
    out = {}
    d = Path(specs_dir)
    if not d.is_dir():
        return out
    for p in sorted(d.glob("*.md")):
        if p.name.startswith("TEMPLATE") or p.name == "index.md":
            continue
        fm = _spec_front_matter(p.read_text(), parse)
        sid = fm.get("id")
        if not _is_str(sid):
            continue
        crit = [{"id": c.get("id"), "text": _fold_text(c.get("text"))}
                for c in _as_list(fm.get("acceptance_criteria")) if isinstance(c, dict)]
        out[sid] = {
            "path": str(p), "title": fm.get("title"), "status": fm.get("status"),
            "criteria": crit, "plan": fm.get("plan"), "work": fm.get("work"),
            "placement": _as_list(fm.get("placement")), "footprint": _as_list(fm.get("footprint")),
            "fm": fm,
        }
    return out


def _read_proofs(proof_dir, proof_digest):
    """{spec_id: proof-record} from proof/*/manifest.json. Reuses the injected proof_digest
    (the canonical identity of a proof), never a second one. A manifest that is not valid
    JSON is a malformed corpus artifact and REFUSES by name (fail closed)."""
    out = {}
    d = Path(proof_dir)
    if not d.is_dir():
        return out
    for p in _corpus_files(d, _VC.MANIFEST_PATTERN):
        try:
            m = json.loads(p.read_text())
        except (OSError, ValueError) as e:
            raise IntentCorpusError("corpus artifact malformed: proof manifest %s is not valid JSON: %s" % (p, e))
        sid = m.get("spec_id")
        if not _is_str(sid):
            continue
        out[sid] = {
            "path": str(p), "commit": m.get("commit"), "digest": proof_digest(m),
            "plan": m.get("plan"), "work": m.get("work"),
            "criteria": [{"id": c.get("id"), "status": c.get("status")}
                         for c in _as_list(m.get("criteria")) if isinstance(c, dict)],
            "checks": [{"name": c.get("name"), "status": c.get("status")}
                       for c in _as_list(m.get("checks")) if isinstance(c, dict)],
        }
    return out


def _read_verdicts(proof_dir):
    """{spec_id: [verdict-record, ...]} from proof/*/verdict*.json. Absent or unreadable
    verdicts leave a spec with [] (a spec may legitimately have no verdict yet); the corpus
    reports the absence, it never fabricates a verdict."""
    out = {}
    d = Path(proof_dir)
    if not d.is_dir():
        return out
    for p in _corpus_files(d, _VC.VERDICT_PATTERN):
        try:
            v = json.loads(p.read_text())
        except (OSError, ValueError):
            continue
        sid = v.get("spec_id")
        if not _is_str(sid):
            continue
        out.setdefault(sid, []).append({
            "path": str(p), "verdict": v.get("verdict"), "reviewer": v.get("reviewer"),
            "commit": v.get("commit"),
        })
    return out


def _read_events(events_path):
    """The recorded event stream (.veldo/events.jsonl) as a list of envelopes. A malformed
    line is skipped (the events validator in validate.py owns refusing a corrupt stream);
    the corpus reads it only to join changes to their events, never to validate it."""
    out = []
    p = Path(events_path)
    if not p.is_file():
        return out
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def _read_decisions(decisions_dir, decision_loader, parse):
    """{decision_id: decision-record} from .veldo/decisions/*.yaml, read through the injected
    decision loader (.veldo/decision.py's load_record - no second parser). Absent dir or no
    loader: {} (adoption safe). A decision that does not parse is skipped here; decision.py
    owns refusing a malformed decision record in the gate."""
    out = {}
    d = Path(decisions_dir) if decisions_dir else None
    if not d or not d.is_dir() or decision_loader is None:
        return out
    for p in sorted(d.glob("*.yaml")):
        try:
            rec = decision_loader(p, parse)
        except Exception:
            continue
        did = rec.get("id") if isinstance(rec, dict) else None
        if _is_str(did):
            out[did] = {"path": str(p), "id": did, "title": rec.get("title"),
                        "status": rec.get("status")}
    return out


# --- the corpus: the runtime query surface (read-only, in-session) -----------------------

class IntentCorpus:
    """The queryable index of the project's own record. Every method is a READ; the corpus
    holds no write path and opens no live connection. Constructed by build_corpus from the
    repo's own readers, so it reuses recorded data only and adds no instrumentation."""

    def __init__(self, root, specs, proofs, verdicts, plans, decisions, events,
                 arch=None, contract=None, git_reader=None):
        self._root = Path(root)
        self._specs = specs
        self._proofs = proofs
        self._verdicts = verdicts
        self._plans = plans or {}
        self._decisions = decisions or {}
        self._events = events or []
        self._arch = arch                      # the arch module, or None (no contract)
        self._contract = contract              # the parsed architecture contract, or None
        self._git = git_reader or default_git_reader

    @property
    def empty(self):
        """Adoption-safe stand-down: no specs and no proofs means there is nothing to trace,
        so every query returns an ungoverned Trace or an empty change list without error."""
        return not self._specs and not self._proofs

    @property
    def contract_present(self):
        return self._contract is not None

    def stats(self):
        return {"specs": len(self._specs), "proofs": len(self._proofs),
                "verdicts": sum(len(v) for v in self._verdicts.values()),
                "plans": len(self._plans), "decisions": len(self._decisions),
                "events": len(self._events), "contract_present": self.contract_present}

    def spec_ids(self):
        return sorted(self._specs)

    # -- module to contract area (soft cross-plan join, C7) --

    def area_of(self, module_path):
        """The declared architecture areas a module path belongs to, WHEN a PLAN-0011
        architecture contract exists; otherwise the honest stand-down. Returns
        {contract_present, areas}: areas is a set of area ids when a contract is present
        (possibly empty when the path lies outside every declared area), and None when no
        contract exists - the corpus degrades to spec and git level and never fakes an area
        (C7). Fail closed on a malformed path."""
        module_path = _require_query(module_path, "module path")
        if self._contract is None:
            return {"contract_present": False, "areas": None}
        return {"contract_present": True,
                "areas": sorted(self._arch.area_for_path(module_path, self._contract))}

    # -- the governance trace: spec -> criteria + proof + verdict --

    def trace(self, spec_id):
        """The governance chain for a spec id: what it PROMISED (its acceptance criteria),
        what PROVED it (its proof, with the criteria statuses, the checks, the bound commit,
        and the proof digest), and the VERDICT that reviewed it - each citing the real
        artifact. An unknown spec id returns a truthful ungoverned Trace ("no governing
        artifact"), never a fabricated one. Fail closed on a malformed query."""
        spec_id = _require_query(spec_id, "spec id")
        s = self._specs.get(spec_id)
        if s is None:
            return Trace.ungoverned(
                "no governing artifact in the corpus: no spec %r is recorded" % spec_id,
                spec_id=spec_id)
        citations = [s["path"]]
        proof = self._proofs.get(spec_id)
        if proof:
            citations.append(proof["path"])
        verdicts = self._verdicts.get(spec_id, [])
        citations.extend(v["path"] for v in verdicts)
        areas = None
        if self._contract is not None:
            areas = set()
            for fp in s["footprint"]:
                if _is_str(fp):
                    areas |= self._arch.area_for_path(fp, self._contract)
            for pl in s["placement"]:
                if _is_str(pl):
                    areas.add(pl)
        return Trace(
            True, spec_id=spec_id, title=s["title"], status=s["status"],
            criteria=s["criteria"], plan=s["plan"], work=s["work"],
            proof=proof, verdicts=verdicts, areas=areas,
            contract_present=self.contract_present, matched_by="spec_id",
            citations=citations)

    # -- behavior to governing spec --

    def governing_spec(self, behavior):
        """Resolve a behavior descriptor to its governing spec, then trace it. Resolution is
        artifact-grounded: a behavior that names a recorded spec id resolves to that spec; a
        behavior that is a path matching a spec's declared footprint resolves to that spec
        (the candidates are all reported). A behavior no recorded artifact governs returns a
        truthful ungoverned Trace ("no governing artifact") - it is NEVER resolved to an
        arbitrary spec, because a fabricated governor is exactly what diagnosis-from-artifacts
        forbids. Fail closed on a malformed query."""
        behavior = _require_query(behavior, "behavior")
        if behavior in self._specs:
            t = self.trace(behavior)
            t.matched_by = "spec_id"
            return t
        matches = sorted(sid for sid, s in self._specs.items()
                         if any(_is_str(fp) and fnmatch.fnmatch(behavior, fp) for fp in s["footprint"]))
        if matches:
            t = self.trace(matches[0])
            t.matched_by = "footprint"
            t.candidates = matches
            return t
        return Trace.ungoverned(
            "no governing artifact in the corpus for behavior %r (not a recorded spec id "
            "and matches no recorded spec footprint)" % behavior)

    # -- change to proof and verdict --

    def proof_for_commit(self, commit):
        """The proof(s) and verdict(s) whose recorded commit matches this commit, so a
        change traces to what proved it and how it was reviewed. Matching is by commit
        prefix (a short git sha is a prefix of the full sha the proof records). Returns []
        when no recorded proof binds to the commit (truthful, never fabricated). Fail closed
        on a malformed query."""
        commit = _require_query(commit, "commit")
        out = []
        for sid, pr in sorted(self._proofs.items()):
            pc = pr.get("commit") or ""
            if pc and (pc.startswith(commit) or commit.startswith(pc)):
                out.append({"spec_id": sid, "proof_path": pr["path"], "commit": pc,
                            "verdicts": self._verdicts.get(sid, [])})
        return out

    # -- recent changes per path, from git AND the event stream --

    def recent_changes(self, path, limit=10):
        """Recent changes touching a path, from BOTH sources the method records: git history
        (a synchronous in-session `git log` over the path) and the event stream (the events
        whose recorded commit matches one of those git commits). Returns {path, git, events};
        an untouched path yields empty lists, never a fabricated change. Fail closed on a
        malformed path."""
        path = _require_query(path, "path")
        lines = self._git(self._root, "log", "--oneline", "-n", str(int(limit)), "--", path)
        git = []
        shorts = []
        for ln in lines:
            sha, _, subject = ln.partition(" ")
            if sha:
                git.append({"commit": sha, "subject": subject.strip()})
                shorts.append(sha)
        events = []
        for e in self._events:
            ec = e.get("commit") or ""
            if ec and any(ec.startswith(s) or s.startswith(ec) for s in shorts):
                events.append({"commit": ec, "type": e.get("type"), "at": e.get("at")})
        return {"path": path, "git": git, "events": events}

    # -- a decision record by id (part of the recorded corpus) --

    def decision(self, decision_id):
        """A recorded foundational decision (veldo.decision/v1) by id, or None when none is
        recorded. Fail closed on a malformed query. Decisions are part of the project's own
        record the corpus indexes; the responder can trace a behavior's governing choice."""
        decision_id = _require_query(decision_id, "decision id")
        return self._decisions.get(decision_id)

    # -- the artifact-grounded trace for an incident (the read W4 diagnoses from) --

    def trace_incident(self, incident):
        """Assemble the artifact-grounded governance trace for an incident record
        (veldo.incident/v1): resolve its governing spec (from affected_spec when the incident
        names one, otherwise from affected_behavior), and enrich the resolved Trace with the
        recent changes touching the governing spec's footprint and, WHEN an architecture
        contract exists, the areas those paths sit in (degrading to spec and git level
        without a contract, C7). This is the READ the responder investigation loop
        WARP-1204 (W4) diagnoses FROM; it is a query over the record, not an investigation:
        this module composes no prose diagnosis and emits no proposal (that is W4, the first
        consumer, honestly deferred). An incident whose behavior no artifact governs yields a
        truthful ungoverned Trace ("no governing artifact"), never a fabricated diagnosis.
        Fail closed on a malformed incident (no affected_behavior)."""
        if not isinstance(incident, dict):
            raise IntentCorpusError("malformed query: an incident must be a record (mapping)")
        affected_spec = incident.get("affected_spec")
        affected_behavior = incident.get("affected_behavior")
        t = None
        if _is_str(affected_spec):
            t = self.trace(affected_spec)
        if (t is None or not t.governed) and _is_str(affected_behavior):
            t = self.governing_spec(affected_behavior)
        if t is None:
            raise IntentCorpusError(
                "malformed query: an incident names neither affected_spec nor affected_behavior")
        if not t.governed:
            return t
        s = self._specs.get(t.spec_id, {})
        changes = {}
        for fp in s.get("footprint", []):
            if _is_str(fp) and "*" not in fp:      # a concrete path has a real change log
                changes[fp] = self.recent_changes(fp)
        t.recent_changes = changes
        return t


# --- the factory (dependency injected) and the batteries-included opener -----------------

def build_corpus(root, parse, proof_digest, plan_registry=None, repo_contract=(None, None),
                 decision_loader=None, decisions_dir=None, events_path=None, git_reader=None):
    """Build the corpus from the repo's OWN readers, injected: `parse` is the one
    front-matter parser (validate.parse_yamlish), `proof_digest` the canonical proof
    identity (validate.proof_digest), `plan_registry` the plan reader (validate.plan_registry),
    `repo_contract` the (arch_module, contract) pair (validate.load_repo_contract),
    `decision_loader` the decision-record reader (.veldo/decision.py load_record). No reader is
    reimplemented here; the corpus only INDEXES what these already read (NG5, no new
    instrumentation). Fail closed on a malformed spec or proof; adoption safe on absent dirs."""
    root = Path(root)
    specs = _read_specs(root / "specs", parse)
    proofs = _read_proofs(root / "proof", proof_digest)
    verdicts = _read_verdicts(root / "proof")
    plans = plan_registry(root / "plans") if plan_registry else {}
    ddir = decisions_dir if decisions_dir is not None else (root / ".veldo" / "decisions")
    decisions = _read_decisions(ddir, decision_loader, parse)
    events = _read_events(events_path if events_path is not None else root / ".veldo" / "events.jsonl")
    arch, contract = repo_contract if isinstance(repo_contract, (tuple, list)) else (None, None)
    return IntentCorpus(root, specs, proofs, verdicts, plans, decisions, events,
                        arch=arch, contract=contract, git_reader=git_reader)


def open_corpus(root=None):
    """The batteries-included opener: load validate.py and decision.py BY PATH (the same way
    the sibling organs load validate.py, so there is one front-matter parser and NO import
    cycle), wire their readers, and build the corpus over this repository. This is the entry
    the responder loop (W4) and the release wiring (W11) reuse; nothing is reimplemented."""
    import importlib.util
    here = Path(__file__).resolve().parent
    root = Path(root) if root else here.parent
    vspec = importlib.util.spec_from_file_location("veldo_validate", here / "validate.py")
    V = importlib.util.module_from_spec(vspec)
    vspec.loader.exec_module(V)
    dspec = importlib.util.spec_from_file_location("veldo_decision", here / "decision.py")
    D = importlib.util.module_from_spec(dspec)
    dspec.loader.exec_module(D)
    return build_corpus(
        root, V.parse_yamlish, V.proof_digest, plan_registry=V.plan_registry,
        repo_contract=V.load_repo_contract(repo_root=str(root)),
        decision_loader=D.load_record, decisions_dir=D.default_decisions_dir(root))


def _cli(argv):
    """Standalone runner: open the corpus over this repository and answer one query, reusing
    validate.py's parser, proof-digest, plan registry, and contract loader (no second
    parser). Wiring a corpus check into validate.py run_all and the init lay-down is
    WARP-1211 (W11, land the checks in the canonical engine); this module ships runnable
    in-session and exercised through the selftest, matching how W1 and W2 shipped."""
    corpus = open_corpus()
    if len(argv) >= 3 and argv[1] == "trace":
        t = corpus.trace(argv[2])
    elif len(argv) >= 3 and argv[1] == "behavior":
        t = corpus.governing_spec(argv[2])
    elif len(argv) >= 3 and argv[1] == "changes":
        print(json.dumps(corpus.recent_changes(argv[2]), indent=2, default=str))
        return 0
    elif len(argv) >= 3 and argv[1] == "area":
        print(json.dumps(corpus.area_of(argv[2]), indent=2, default=str))
        return 0
    else:
        print("veldo intent corpus: %s" % json.dumps(corpus.stats(), sort_keys=True))
        print("usage: intent_corpus.py [trace <SPEC> | behavior <text> | changes <path> | area <path>]")
        return 0
    print(json.dumps(t.as_dict(), indent=2, default=str))
    return 0


if __name__ == "__main__":
    import sys
    try:
        sys.exit(_cli(sys.argv))
    except IntentCorpusError as e:
        print("veldo intent corpus: %s" % e)
        sys.exit(1)
