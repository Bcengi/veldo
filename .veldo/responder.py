#!/usr/bin/env python3
"""VELDO responder investigation loop (L0 investigate / L1 propose): the in-session agent
brief and harness that, given an incident, reaches a CITED diagnosis from the intent corpus
and the read-only evidence plane and emits a veldo.remedy/v1 PROPOSAL - and that STRUCTURALLY
CANNOT execute anything.

This is the W4 organ of PLAN-0012 and the first CONSUMER of the three roots it composes: the
incident and remedy contracts (.veldo/incident.py, W1), the read-only evidence plane
(.veldo/evidence.py, W2), and the intent corpus at runtime (.veldo/intent_corpus.py, W3). It is
Invention #3's design center made operational: when agents author everything, the five-minute
diagnosis that used to be a free byproduct of authorship is gone, so the responder that
replaces the hero does not need to have written the code - it reads the record (the corpus)
and queries the read-only evidence, reaches a diagnosis every claim of which cites a real
artifact, and proposes a remedy. Everything here is proven OFFLINE against the fake evidence
plane and a seeded incident (NG1); no live production access exists in this harness.

THE LOAD-BEARING SAFETY PROPERTY this module ENCODES (Invention #3, O2/C4, the refusals are
the product, C1):

  THE HARNESS CONTAINS NO EXECUTION CAPABILITY AT ALL. Diagnosis and execution are separate
  organs. The responder can investigate and propose, and it CANNOT execute anything, because
  the write/execute path DOES NOT EXIST on its type - not "it declines to", but "it cannot be
  expressed". ResponderHarness has no execute, apply, run, remediate, mutate, write, deploy,
  restart, or scale method; the only production-touching capability it holds is a read-only
  ReadHandle from the evidence plane (query only, W2's physics), and it holds no
  write-capable credential. Execution is a SEPARATE privileged organ on its own credentials
  and code path, WARP-1206 (W6), NOT built here. Separation is structural, not instructed: a
  negative test proves the harness cannot execute, and it is NON-VACUOUS (a mutation ADDING an
  execute method turns the check red).

  THE LADDER FLOOR IS READ-ONLY. This harness operates ONLY at L0 (investigate) or L1
  (propose); it is constructed at one of those two levels and REFUSES to be constructed at L2
  or L3 (the execution rungs), which are a separate organ per the resolved decision D2 (start
  and stay at L0/L1; L3 disabled by default and may never be enabled). propose requires L1;
  at L0 (the investigate-only floor) propose refuses and degrades down, never up (C3).

  THE INTELLIGENT REASONING IS A DELEGATED FAIL-LOUD SEAM. The mechanical control logic is
  built here: assemble the corpus governance trace and the read-only evidence context, hold
  the loop at L0/L1, GROUND every citation to a real artifact, structurally exclude execution,
  derive the required human authorization, and emit the validated veldo.remedy/v1 proposal. The
  intelligent diagnosis itself - the judgment a stranger to the code reaches by reading the
  record - is a fresh-context step DELEGATED through the Responder seam, exactly like the
  executor's LiveLoop.build/review, the dispatch reviewer, and the shape and decision
  reviewers. The reference LiveResponder is wired to nothing and RAISES rather than fabricate a
  diagnosis; an adopting runtime injects a responder that dispatches a genuinely fresh context.
  A fabricated diagnosis is REFUSED: every citation the responder returns must resolve to a
  real artifact in the assembled context (a corpus artifact path, a recorded change commit, or
  an allowed evidence query), or the harness refuses by name. A responder that fabricated a
  citation would be worse than one that admitted it cannot diagnose.

Dependency free by construction and no second parser: the harness receives the incident/remedy
contract module (.veldo/incident.py) and the built intent corpus injected, exactly as the
sibling organs receive the parser and reporter, so validation reuses INC.validate_remedy and
INC.bind_remedy and there is no second YAML parser and no import cycle. The harness reads the
evidence plane only through a read-only ReadHandle (W2); it opens no live connection (NG1) and
starts no process, thread, or timer (NG3, no-detach): its top imports are pathlib only.

Honest deferrals (the plan's ordered delivery, not a dodge): the action whitelist the proposal
references is WARP-1205 (W5); the execution organ that would run a proposal at L2/L3 is
WARP-1206 (W6); the two-key rule an irreversible or data-mutating proposal binds to is
WARP-1207 (W7); the compressed loop and reconciliation that close an incident are WARP-1208
(W8); the support metrics are WARP-1210 (W10); and landing a responder check into
validate.py run_all and lay-down via init is WARP-1211 (W11). Nothing here executes, and
nothing here pretends those later organs are built.
"""
from pathlib import Path

# The schema this organ is known by (veldo.responder/v1), mirroring the sibling organs'
# SCHEMA constants; the harness is an in-session agent, not a validated per-repo artifact, so
# the constant names the organ rather than a stored record format. The investigation CONTEXT
# the harness assembles for the delegated reasoner is its own versioned shape.
SCHEMA = "veldo.responder/v1"
SCHEMA_CONTEXT = "veldo.responder_context/v1"

# The autonomy ladder floor this harness operates on (PLAN-0012 O3, D2). L0 investigates and
# L1 proposes; the EXECUTION rungs L2 and L3 are a SEPARATE organ (WARP-1206, W6) and are
# structurally absent here - a harness cannot even be constructed at L2 or L3.
RESPONDER_LEVELS = ("L0", "L1")
_LEVEL_ORDER = {"L0": 0, "L1": 1}

# The method/attribute names an EXECUTION capability would carry. The harness must have NONE
# of them: the no-execution negative test asserts hasattr is false for every one, and a
# mutation adding any of them turns the test red (non-vacuous). This is the enumerated shape
# of "the write/execute path does not exist", mirroring how the evidence plane's ReadHandle
# carries no write/insert/update/delete/execute/mutate method.
FORBIDDEN_EXECUTION_METHODS = (
    "execute", "apply", "run", "remediate", "mutate", "write", "deploy",
    "perform", "act", "rollback", "restart", "scale", "commit_change",
    "submit_write", "open_write",
)

# The agent brief: what a fresh-context responder agent injected into the seam must do. It is
# the L0/L1 contract in prose, so the delegated reasoner and the mechanical harness agree on
# the boundary. The harness ENFORCES every line of it mechanically (grounding, the level floor,
# the no-execution physics, the contract validation of the emitted proposal).
RESPONDER_BRIEF = (
    "You are a VELDO production support responder operating at the read-only floor (L0 "
    "investigate, L1 propose). You are given an incident record (veldo.incident/v1), the "
    "intent-corpus governance trace for it (the governing spec and its acceptance criteria, "
    "the proof that proved it, the verdict that reviewed it, and the recent changes touching "
    "its footprint, each a real artifact path), and a READ-ONLY evidence handle (query only). "
    "Reach a diagnosis every claim of which CITES a real artifact from that context - a corpus "
    "artifact path, a recorded change commit, or an evidence query you actually issued - and "
    "NEVER invent a citation. At L1, also propose a whitelist action with its parameters, a "
    "risk class, the autonomy level executing it would need, a reversibility analysis, a "
    "rollback plan, and a canary shape. You CANNOT execute anything and you must not claim to: "
    "execution is a separate organ. If you cannot ground the diagnosis in real artifacts, say "
    "so; do not fabricate."
)


class ResponderError(RuntimeError):
    """The responder harness refused, or the delegated reasoner is not wired or fabricated a
    diagnosis. Raised by name so a refusal never silently no-ops (parallels ShapeReviewError,
    EvidencePlaneError, and IntentCorpusError). This is the type the negative tests bind to."""


def _is_str(v):
    return isinstance(v, str) and v.strip() != ""


def _as_list(v):
    return v if isinstance(v, list) else []


def _as_bool(v):
    """The value as a real boolean, or None. A delegated reasoner returns real Python values,
    but the front-matter parser leaves an unquoted true/false as the string "true"/"false";
    accept both and refuse anything else, exactly as incident.py's _as_bool does, so a
    truthy-looking value like "yes" is never silently accepted."""
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        s = v.strip().lower()
        if s == "true":
            return True
        if s == "false":
            return False
    return None


# --- the cited diagnosis (an artifact-grounded answer, never fabricated) ------------------

class Diagnosis:
    """One cited diagnosis of an incident. When governed is True the diagnosis rests on the
    corpus's governing artifacts (the spec, its proof, its verdict) and `cited` lists the real
    artifact citations that ground it; when governed is False the corpus found no governing
    artifact and the diagnosis rests only on evidence and the change log (an honest degrade,
    never a fabricated governor). Every entry in `cited` resolved to a real artifact in the
    investigation context, or the harness would have refused before this object was built."""

    __slots__ = ("governed", "reason", "incident_id", "spec_id", "diagnosis", "cited",
                 "areas", "contract_present")

    def __init__(self, governed, incident_id, diagnosis, cited, spec_id=None, reason=None,
                 areas=None, contract_present=False):
        self.governed = bool(governed)
        self.incident_id = incident_id
        self.diagnosis = diagnosis
        self.cited = cited or []
        self.spec_id = spec_id
        self.reason = reason
        self.areas = areas
        self.contract_present = bool(contract_present)

    def as_dict(self):
        return {k: (sorted(v) if isinstance(v, set) else v)
                for k, v in ((s, getattr(self, s)) for s in self.__slots__)}

    def __repr__(self):
        return "<Diagnosis incident=%r governed=%s spec=%r cited=%d>" % (
            self.incident_id, self.governed, self.spec_id, len(self.cited))


# --- the delegated fresh-context reasoning seam (fail loud, never fabricate) --------------

class Responder:
    """The fresh-context responder reasoning seam. diagnose(incident, context) returns the
    intelligent diagnosis the mechanical harness cannot synthesize: a mapping with the
    diagnosis text, the cited evidence, and (at L1) the proposed whitelist action, risk class,
    autonomy level, reversibility, rollback, and canary. A concrete responder dispatches a
    genuinely fresh context over the incident, the corpus governance trace, and the read-only
    evidence handle; this module talks only to this interface, so a diagnosis is never
    fabricated in code and the reference cannot pretend to have diagnosed."""

    def diagnose(self, incident, context):
        raise NotImplementedError


class LiveResponder(Responder):
    """Reference responder wired to nothing. Fails LOUD: an adopting runtime must inject a
    responder that dispatches a genuinely fresh context over the incident record, the
    intent-corpus governance trace, and the read-only evidence plane, and returns its cited
    diagnosis (and at L1 the proposed whitelist action). Refusing to fabricate a diagnosis is
    the honest default, exactly as the executor's LiveLoop.build/review, the dispatch
    LiveReviewer, and the shape and decision reviewers refuse to fabricate their judgment."""

    def diagnose(self, incident, context):
        raise ResponderError(
            "responder diagnosis is a delegated fresh-context step; no responder agent is "
            "wired. Inject a responder that dispatches a genuinely fresh context over the "
            "incident record, the intent-corpus governance trace, and the read-only evidence "
            "plane, and returns its cited diagnosis (and at L1 the proposed whitelist action). "
            "The mechanical control logic - assemble the corpus and evidence context, hold the "
            "loop at L0/L1, ground every citation to a real artifact, structurally exclude "
            "execution, and emit the validated veldo.remedy/v1 proposal - is built in the "
            "harness; this is the reasoning half. Refusing to fabricate a diagnosis.")


# --- the responder harness (mechanical control logic; NO execution capability) ------------

class ResponderHarness:
    """The responder investigation loop at L0 (investigate) and L1 (propose). It composes the
    intent corpus (W3, read-only) and a read-only evidence handle (W2, query only) to reach a
    CITED diagnosis of an incident (W1's veldo.incident/v1) and, at L1, emit a validated
    veldo.remedy/v1 PROPOSAL (W1). The intelligent diagnosis is delegated through the Responder
    seam (fail loud, never fabricated); the harness grounds every citation to a real artifact.

    THE LOAD-BEARING PROPERTY is structural, not instructed: this type carries NO execution
    capability at all. There is no execute, apply, run, remediate, mutate, write, deploy,
    restart, or scale method; the harness holds a read-only ReadHandle (query only) and no
    write-capable credential; and it cannot be constructed at an execution rung (L2/L3). The
    write/execute path does not exist here; execution is a separate organ, WARP-1206 (W6)."""

    def __init__(self, corpus, inc, autonomy="L1", evidence_read=None, evidence_audit=None,
                 reasoner=None, root=None):
        if corpus is None:
            raise ResponderError("a responder harness needs an intent corpus (W3) to diagnose from")
        if inc is None:
            raise ResponderError("a responder harness needs the incident/remedy contract module (W1) to validate its proposal against")
        if autonomy not in RESPONDER_LEVELS:
            raise ResponderError(
                "the responder harness operates ONLY at the read-only floor L0 (investigate) or "
                "L1 (propose); autonomy %r is refused. The execution rungs L2 and L3 are a "
                "SEPARATE organ (WARP-1206, W6), structurally absent from this harness (D2: start "
                "and stay at L0/L1; L3 disabled by default and may never be enabled)." % (autonomy,))
        if evidence_read is not None and not hasattr(evidence_read, "query"):
            raise ResponderError("the evidence handle must be a read-only handle exposing query() (W2); the responder investigates read-only")
        self._corpus = corpus
        self._inc = inc
        self._autonomy = autonomy
        self._evidence = evidence_read      # a read-only ReadHandle (query only) or None
        self._audit = evidence_audit        # the QueryAudit, for grounding evidence citations
        self._reasoner = reasoner if reasoner is not None else LiveResponder()
        self._root = Path(root) if root is not None else None

    # Deliberately NO execute, apply, run, remediate, mutate, write, deploy, restart, or scale
    # method. The write/execute path does not exist on this type: separation is structural, not
    # a policy flag. Execution is a separate organ (WARP-1206, W6).

    @property
    def autonomy(self):
        return self._autonomy

    def _require_incident(self, incident):
        if not isinstance(incident, dict):
            raise ResponderError("an incident must be a record (mapping); got %r" % type(incident).__name__)
        if not _is_str(incident.get("id")):
            raise ResponderError("the incident record has no id (fail closed): a diagnosis must bind to a real incident")

    def _require_level(self, minimum):
        if _LEVEL_ORDER[self._autonomy] < _LEVEL_ORDER[minimum]:
            raise ResponderError(
                "%s requires autonomy %s; this harness is at %s. Degrade down, never up (C3). "
                "L0 investigates and only L1 proposes; execution (L2/L3) is a separate organ "
                "(WARP-1206, W6)." % (minimum == "L1" and "propose" or minimum, minimum, self._autonomy))

    def investigation_context(self, incident):
        """The brief the delegated reasoner receives: the incident id, the intent-corpus
        governance TRACE (the governing spec, its criteria, its proof, its verdict, and the
        recent changes touching its footprint, each a real artifact path), a READ-ONLY evidence
        handle (query only, or None), and the operating level. This is a query over the record
        and a read-only handle; it opens no live connection and holds no write path."""
        self._require_incident(incident)
        trace = self._corpus.trace_incident(incident)
        return {
            "schema": SCHEMA_CONTEXT,
            "incident_id": incident.get("id"),
            "trace": trace,
            "evidence": self._evidence,
            "autonomy": self._autonomy,
            "allowed_levels": list(RESPONDER_LEVELS),
            "brief": RESPONDER_BRIEF,
        }

    def _allowed_citations(self, trace, audit_start):
        """The set of citations that resolve to a REAL artifact in the investigation context:
        every corpus artifact path the trace cites (the spec, its proof, its verdict), every
        recorded change commit (git and the event stream) touching the governing spec's
        footprint, and every evidence query the reasoner ACTUALLY issued and the broker allowed
        during this investigation (audit entries from audit_start onward). Membership in this
        set is, by construction, "resolves to a real artifact" - the set is built only from
        real corpus paths, real change commits, and real allowed queries."""
        allowed = set(trace.citations or [])
        for _fp, ch in (trace.recent_changes or {}).items():
            if not isinstance(ch, dict):
                continue
            for g in _as_list(ch.get("git")):
                if isinstance(g, dict) and _is_str(g.get("commit")):
                    allowed.add(g["commit"])
            for ev in _as_list(ch.get("events")):
                if isinstance(ev, dict) and _is_str(ev.get("commit")):
                    allowed.add(ev["commit"])
        if self._audit is not None:
            for entry in self._audit.entries[audit_start:]:
                if isinstance(entry, dict) and entry.get("decision") == "allowed":
                    allowed.add("evidence:%s/%s" % (entry.get("source_id"), entry.get("template")))
        return allowed

    def _run_reasoner(self, incident):
        """Drive the delegated reasoner and GROUND its answer. The reasoner (fail loud if
        unwired) returns a diagnosis mapping; the harness snapshots the audit, calls diagnose,
        then verifies every citation resolves to a real artifact - refusing a fabricated one by
        name. Returns (Diagnosis, result-mapping, context)."""
        self._require_incident(incident)
        ctx = self.investigation_context(incident)
        audit_start = len(self._audit.entries) if self._audit is not None else 0
        result = self._reasoner.diagnose(incident, ctx)  # delegated; LiveResponder RAISES here
        if not isinstance(result, dict):
            raise ResponderError("the responder returned no diagnosis mapping (fail loud): a real fresh-context responder returns {diagnosis, evidence, ...}")
        diag = self._ground(incident, ctx, result, audit_start)
        return diag, result, ctx

    def _ground(self, incident, ctx, result, audit_start):
        """Build the cited Diagnosis, refusing a fabricated one. Every evidence citation must
        resolve to a real artifact in the context (the no-fabrication guarantee, O4/C1); a
        governed incident must cite at least one corpus artifact, so the diagnosis is grounded
        in the record and not in evidence alone."""
        trace = ctx["trace"]
        text = result.get("diagnosis")
        if not _is_str(text):
            raise ResponderError("the responder produced no diagnosis text (fail loud): a diagnosis is required")
        evidence = result.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise ResponderError("the responder produced no cited evidence: a diagnosis is derived from artifacts, each cited (O4); an uncited diagnosis is refused")
        allowed = self._allowed_citations(trace, audit_start)
        cited = []
        for e in evidence:
            c = e.get("citation") if isinstance(e, dict) else None
            if not _is_str(c):
                raise ResponderError("an evidence entry carries no citation: a diagnosis without citations is not derived from artifacts")
            if c not in allowed:
                raise ResponderError(
                    "FABRICATED DIAGNOSIS REFUSED: citation %r does not resolve to a real artifact "
                    "in the investigation context (a corpus artifact path, a recorded change "
                    "commit, or an evidence query actually issued). Diagnosis from artifacts means "
                    "the answer rests on a real artifact or it is refused; a responder that "
                    "fabricated a citation would be worse than one that admitted it cannot "
                    "diagnose." % (c,))
            cited.append(c)
        if trace.governed:
            corpus_cites = set(trace.citations or [])
            if not any(c in corpus_cites for c in cited):
                raise ResponderError(
                    "a cited diagnosis of a governed incident must cite at least one corpus "
                    "artifact (the governing spec, its proof, or its verdict); the governing "
                    "trace cites %s but the diagnosis cited only %s" % (sorted(corpus_cites), cited))
        return Diagnosis(
            governed=trace.governed, incident_id=incident.get("id"), diagnosis=text,
            cited=cited, spec_id=trace.spec_id, reason=trace.reason,
            areas=(sorted(trace.areas) if isinstance(trace.areas, set) else trace.areas),
            contract_present=trace.contract_present)

    def investigate(self, incident):
        """L0: investigate the incident over the corpus and the read-only evidence and return a
        CITED diagnosis (no proposal). Available at L0 and L1. The delegated reasoning fails
        loud without a wired responder; a fabricated citation is refused."""
        diag, _result, _ctx = self._run_reasoner(incident)
        return diag

    def propose(self, incident):
        """L1: investigate, then emit a validated veldo.remedy/v1 PROPOSAL (a diagnosis, the
        cited evidence, the proposed whitelist action and parameters, the risk class, the
        autonomy level the action needs, a reversibility analysis, a rollback plan, a canary
        shape, and the required human authorization). Requires L1; at L0 it refuses (degrade
        down, never up). The harness EMITS the proposal artifact and stops - it structurally
        cannot execute it (execution is WARP-1206, W6)."""
        self._require_level("L1")
        diag, result, _ctx = self._run_reasoner(incident)
        return self._build_proposal(incident, diag, result)

    def _build_proposal(self, incident, diag, result):
        """Assemble the veldo.remedy/v1 proposal from the diagnosis and the reasoner's proposed
        action, DERIVE the required human authorization mechanically (the safety wiring the
        harness owns, not the reasoner: irreversible or data-mutating forces two_key so the
        two-key path W7 has something exact to bind to), and VALIDATE it structurally through
        the W1 contract - refusing a proposal missing any element (fail closed). The proposal
        binds to the incident it remediates and can never claim to have executed (W1 forbids an
        execution status or capability field)."""
        rev = result.get("reversibility") if isinstance(result.get("reversibility"), dict) else {}
        needs_two_key = (rev.get("class") == "irreversible") or (_as_bool(rev.get("data_mutating")) is True)
        required_auth = "two_key" if needs_two_key else "human_confirmation"
        remedy = {
            "schema": self._inc.SCHEMA_REMEDY,
            "id": result.get("id") if _is_str(result.get("id")) else ("REM-%s" % incident.get("id")),
            "incident": incident.get("id"),
            "status": "proposed",
            "diagnosis": diag.diagnosis,
            "evidence": [{"citation": c} for c in diag.cited],
            "proposed_action": result.get("proposed_action"),
            "risk_class": result.get("risk_class"),
            "autonomy_level": result.get("autonomy_level"),
            "reversibility": result.get("reversibility"),
            "rollback": result.get("rollback"),
            "canary": result.get("canary"),
            "required_authorization": required_auth,
        }
        problems = []

        def _collect(where, msg):
            problems.append(msg)
            return 1

        errs = self._inc.validate_remedy(remedy, str(self._root or "."), "responder.proposal", _collect)
        errs += self._inc.bind_remedy(remedy, incident, "responder.proposal", _collect)
        if errs:
            raise ResponderError(
                "the responder proposal is invalid at contract time (%d problem(s)): a proposal "
                "missing any element is refused (fail closed). %s" % (errs, "; ".join(problems)))
        return remedy


# --- the batteries-included opener (dependency injected, loaded by path) ------------------

def build_harness(root=None, autonomy="L1", reasoner=None, evidence_read=None,
                  evidence_audit=None):
    """Build a responder harness over this repository: open the intent corpus (W3) and load the
    incident/remedy contract module (W1) BY PATH, the same way the sibling organs load
    validate.py, so there is one front-matter parser and no import cycle. A runtime injects a
    real responder (fresh-context agent) and, at enablement, a real read-only evidence handle;
    offline the caller injects a fake handle over the fake evidence plane (NG1). importlib is
    imported LAZILY here (never at module top), so the module top imports pathlib only and
    starts no process (NG3, no-detach)."""
    import importlib.util
    here = Path(__file__).resolve().parent
    root = Path(root) if root else here.parent

    def _load(name, filename):
        spec = importlib.util.spec_from_file_location(name, here / filename)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    corpus = _load("veldo_intent_corpus_responder", "intent_corpus.py").open_corpus(root)
    inc = _load("veldo_incident_responder", "incident.py")
    return ResponderHarness(corpus, inc, autonomy=autonomy, evidence_read=evidence_read,
                            evidence_audit=evidence_audit, reasoner=reasoner, root=root)


def _cli(argv):
    """Standalone runner: open a responder harness over this repository and, given an incident
    record file, print the assembled investigation context and then attempt to investigate. The
    default reasoner is the fail-loud LiveResponder, so with no responder agent wired this
    honestly REFUSES (the delegated seam fails loud) rather than fabricate a diagnosis - the
    same posture the shape and decision reviewers take. Wiring a responder check into
    validate.py run_all and the init lay-down is WARP-1211 (W11)."""
    import json
    harness = build_harness()
    print("veldo responder: harness at %s (levels %s); reasoning is a delegated fresh-context seam"
          % (harness.autonomy, list(RESPONDER_LEVELS)))
    if len(argv) >= 2 and Path(argv[1]).is_file():
        import importlib.util
        here = Path(__file__).resolve().parent
        vspec = importlib.util.spec_from_file_location("veldo_validate", here / "validate.py")
        V = importlib.util.module_from_spec(vspec)
        vspec.loader.exec_module(V)
        incident = V.parse_yamlish(Path(argv[1]).read_text())
        ctx = harness.investigation_context(incident)
        print(json.dumps({"incident_id": ctx["incident_id"], "governed": ctx["trace"].governed,
                          "spec_id": ctx["trace"].spec_id,
                          "citations": ctx["trace"].citations}, indent=2, default=str))
        try:
            diag = harness.investigate(incident)
            print(json.dumps(diag.as_dict(), indent=2, default=str))
        except ResponderError as e:
            print("veldo responder: %s" % e)
            return 1
        return 0
    print("usage: responder.py <incident.yaml>  (reasoning is delegated; the reference "
          "LiveResponder fails loud until a responder agent is injected)")
    return 0


if __name__ == "__main__":
    import sys
    try:
        sys.exit(_cli(sys.argv))
    except ResponderError as e:
        print("veldo responder: %s" % e)
        sys.exit(1)
