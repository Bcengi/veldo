#!/usr/bin/env python3
"""Incident as intent: the compressed loop and RECONCILIATION (W8 of PLAN-0012, outcome O5).

A closed incident is not a restored service, it is a SETTLED PIECE OF INTENT: the ending is that a human validated the
diagnosis, the fix flowed the lane, and the pass left artifacts behind that make the same failure harder next time. In
the old world that ending was a postmortem nobody read, and the failure came back. Five disciplines, each COMPOSING a
shipped organ rather than reimplementing it (the acceptance criteria of WARP-1208 state each in full):

  AC1 THE FAILURE SIGNATURE AND RECURRENCE. failure_signature is a DETERMINISTIC, PURE digest over exactly the
  identity-of-failure fields, so the same failure shares a signature and a different title, severity, timeline, or id
  does not change it; recurrence reports the ordered prior ids that share it, SKIPPING any record whose signature cannot
  be computed. A recurrence is named what the method already calls it: a MISSING SPECIFICATION.

  AC2 THE CLOSE GATE FAILS CLOSED, BY NAME. A settlement refuses on a status that is not diagnosed, on a MISSING human
  diagnosis validation (its absence never defaults open), on a MACHINE actor as validator (the set REUSED from
  authorization.py, so the responder can never validate its own diagnosis, NG4), on a validation that BINDS NO REMEDY
  while a remedy exists, on a bound digest that does not equal the one THIS MODULE RECOMPUTES from the record and its
  remedy (the 0619 lesson: an attestation bound to a value it displayed proves nothing), and on an OPEN emergency
  backfill debt read through an INJECTED debt_reader (default None, which stands the condition down honestly). NO
  ENFORCEMENT MODULE IS IMPORTED: a contracts-area organ never depends on policy_check.py.

  WHAT THE HUMAN ATTESTS TO IS WHAT THE HUMAN VALIDATED. veldo.incident/v1 carries NO diagnosis field: the diagnosis and
  the cited evidence it rests on live on veldo.remedy/v1, which validate_remedy requires precisely so a diagnosis is
  derived from cited artifacts. So the material a validation binds is the incident's own diagnosis material PLUS,
  whenever a remedy exists, that remedy's identity and its CANONICAL PROPOSAL DIGEST - action_executor.proposal_digest,
  the ONE digest the executor's confirmation and the two-key rule already bind. Binding that digest is deliberate over
  hashing a hand-picked {diagnosis, evidence, proposed_action} subset: the canonical digest covers the diagnosis, every
  cited artifact, and the proposed action AND the rest of the proposal's substance (the rollback plan, the risk class,
  the autonomy level, the reversibility analysis, the required authorization), and it means the human's validation and
  the executor's confirmation bind the SAME artifact identity, while a subset would be a SECOND, weaker remedy identity
  that lets everything outside it change after a human validated. Swapping the proposed action, the diagnosis, the
  evidence, or any other substance of the remedy therefore INVALIDATES the validation, and a validation that names no
  remedy while one exists is REFUSED BY NAME rather than settled.

  AC3 THE TWO DRAFTS A HUMAN PROMOTES, AND THE MACHINE STRUCTURALLY CANNOT. A settlement writes a REGRESSION CRITERIA
  draft from the failure mode and a RUNBOOK ACTION draft from the remedy's proposed action. The runbook draft is
  structurally VALID against veldo.action/v1 - ENFORCED, not exhibited: the RENDERED text is parsed by the ONE parser and
  validated through the SHIPPED validate_action inside the write path, so a draft the contract would refuse is REFUSED
  BY NAME and never written - and it is UNREVIEWED, so the SHIPPED whitelist physics excludes it (action_reviewed False,
  absent from build_whitelist) and it does not exist to the machine execution path (NG2). Both land ONLY in declared
  DRAFT directories: the store's PATH GUARD REFUSES BY NAME any target that RESOLVES inside the action whitelist store
  or the spec corpus, and the renderer refuses any review status other than proposed and any verdict field at all,
  because a machine-recorded review is exactly the rubber stamp the method forbids. Promotion is a HUMAN act of moving
  and reviewing a draft.

  AC4 THE RECEIPT IS HONEST AND IDEMPOTENT UNDER REPLAY. The veldo.reconciliation/v1 receipt answers the plan's three
  questions - what was done, what it proved, what regression criteria it leaves - reading the executed action, its
  parameters, and the outcome from the execution RECEIPT and never from the remedy's own claim, with the honest value
  none for a remedy never executed. An execution asked to be recorded with no receipt, or with a receipt whose proposal
  digest does not match the digest recomputed through the shipped proposal_digest, REFUSES by name. The receipt id is
  CONTENT ADDRESSED from the settlement identity and the store is APPEND ONLY WITH COMPARE AND SWAP: a replay returns the
  existing receipt and appends no second record and no second event, a conflicting write refuses, and a receipt that
  EXISTS but cannot be READ is a CONFLICT rather than an absence, so a corrupt record is never overwritten and one
  incident never emits a second incident.closed.

  THE ONE IMPURE EDGE IS A SIBLING ORGAN. The receipt store, the draft writes, the compare-and-swap and the draft path
  guard live in .veldo/reconciliation_store.py (loaded by path like every other owner), so this module is pure control
  logic over an injected seam and the two mechanisms that decide whether anything is written are read together in one
  place. The store's refusal names are folded into the ONE closed taxonomy here rather than restated.

  THE VOCABULARY IS REUSED, NEVER RESTATED. incident.closed is SELECTED from incident.py INCIDENT_EVENT_TYPES and emitted
  through events.py make_event, so the emitter, the metric source, and the gate cannot drift; machine actors come from
  authorization.py, the proposal digest from action_executor.py, the whitelist physics from action.py.

REVIEW LANE (unmechanizable, honestly labeled per NG5, neither silently passed nor falsely mechanized): whether the
drafted regression criteria are SUFFICIENT to catch this failure again, and whether the drafted runbook action is the
RIGHT action, are a HUMAN REVIEWER'S JUDGMENT at promotion time. The mechanical floor enforced here is that the drafts
EXIST, are STRUCTURALLY VALID, are UNREVIEWED, and CANNOT BE PROMOTED BY THE MACHINE. No support measure is derived
either: the numbers that read these events and receipts are WARP-1210 (W10), the init lay-down and docs WARP-1211 (W11).

Pure stdlib, no network, no live production access (NG1); it lays no timer and no daemon and starts nothing detached
(NG3), and nothing calls it, so a repository that never opens an incident is byte-identically unaffected.

  python3 .veldo/incident_reconcile.py selfcheck   # drive a fixture incident lifecycle offline
"""
import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent

SCHEMA = "veldo.reconciliation/v1"
SETTLED_BY = "veldo.incident_reconcile/v1"

# The honest placeholder for a value that does not exist, recorded verbatim rather than invented (a remedy never executed,
# a receipt with no parameters, an absent runbook draft).
NONE_VALUE = "none"
UNRECORDED = "unrecorded-pending-human-promotion"

def _load(name, rel):
    """Load a sibling module by path, the codebase convention: one owner per contract, no reimplementation."""
    spec = importlib.util.spec_from_file_location(name, _HERE / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

# The incident and remedy contracts (WARP-1201, W1): the ONE authority for the lifecycle statuses and the incident event
# vocabulary this pass emits into. Read, never edited.
_INC = _load("veldo_incident_for_reconcile", "incident.py")
INCIDENT_STATUSES = frozenset(_INC.INCIDENT_STATUSES)
INCIDENT_EVENT_TYPES = frozenset(_INC.INCIDENT_EVENT_TYPES)

# The action whitelist store (WARP-1205, W5): the risk ladder, reversibility vocabulary, risk floor, review lifecycle, and
# the store location the runbook DRAFT is rendered against.
_ACT = _load("veldo_action_for_reconcile", "action.py")

# The execution organ (WARP-1206, W6): the ONE canonical proposal digest, so a receipt's binding is RECOMPUTED rather than
# reimplemented. No executor is constructed here and nothing is ever executed.
_AE = _load("veldo_action_executor_for_reconcile", "action_executor.py")
proposal_digest = _AE.proposal_digest

# The frozen authorization matrix (WARP-0616): the machine-actor set, REUSED so there is no second copy and a machine can
# never stand in for the human who validates a diagnosis.
_AUTHZ = _load("veldo_authorization_for_incident_reconcile", "authorization.py")
MACHINE_ACTORS = frozenset(_AUTHZ.MACHINE_ACTORS)

# The event emitter: the ONE envelope builder, which itself refuses a type outside the vocabulary (no literal type here).
_EV = _load("veldo_events_for_reconcile", "events.py")

# The ONE front-matter parser (validate.parse_yamlish), loaded by path exactly as request_reconcile.py loads it. It is
# read for ONE purpose: parsing a RENDERED runbook draft back so the SHIPPED validate_action judges what will land on
# disk. No second parser and no second validator; validate.py is a contracts-area sibling, not the enforcement area.
_V = _load("veldo_validate_for_incident_reconcile", "validate.py")

# THE ONE IMPURE EDGE, a sibling organ: the append-only compare-and-swap receipt store, the draft writes, and the draft
# PATH GUARD. Loaded by path like every other owner, so the store's mechanisms have ONE home and this module stays pure
# control logic over an injected seam. Its public surface is re-exported here so a caller has one front door.
_ST = _load("veldo_reconciliation_store_for_reconcile", "reconciliation_store.py")
ReconcileError = _ST.ReconcileError
ReconciliationStore = _ST.ReconciliationStore
FakeReconciliationStore = _ST.FakeReconciliationStore
FilesystemReconciliationStore = _ST.FilesystemReconciliationStore
UNREADABLE = _ST.UNREADABLE
forbidden_draft_target = _ST.forbidden_draft_target
_token = _ST._token
_require = _ST._require

# The two lifecycle statuses this pass reads, named from the vocabulary incident.py owns (a selftest binds both).
STATUS_DIAGNOSED = "diagnosed"
STATUS_CLOSED = "closed"

# The review status a DRAFT may carry (the shipped lifecycle's proposed rung) and the fields whose presence would make the
# draft a machine-recorded review.
DRAFT_REVIEW_STATUS = "proposed"
FORBIDDEN_DRAFT_REVIEW_FIELDS = ("verdict", "reviewer", "reviewed_at", "reviewed_digest")

# The most dangerous reversibility class in the shipped vocabulary: an unclassified drafted action is assumed to be this
# until a human classifies it, so the draft carries the critical floor (degrade DOWN, never up).
_CONSERVATIVE_REVERSIBILITY = "irreversible"

# The identity of a FAILURE (AC1): exactly these fields decide whether two records describe the same failure. Title,
# severity, timeline, and id are deliberately absent - they describe the INCIDENT, not the failure. The optional two
# participate only when the record carries them.
IDENTITY_FIELDS = ("affected_behavior", "signal")
OPTIONAL_IDENTITY_FIELDS = ("affected_spec", "affected_area")

# The INCIDENT-SIDE material a human diagnosis validation attests to: distinct from the signature (a case-folded equality
# test over the identity of a failure), this is the substance of the record a human read. It is HALF the binding, and
# honestly so: veldo.incident/v1 has no diagnosis field, so "diagnosis" here binds only a record that carries one anyway;
# THE DIAGNOSIS ITSELF AND ITS CITED EVIDENCE LIVE ON THE REMEDY, and diagnosis_material binds that remedy's canonical
# proposal digest whenever a remedy exists (see the module docstring for why the digest rather than a field subset).
DIAGNOSIS_MATERIAL_FIELDS = ("id", "signal", "affected_behavior", "affected_spec", "affected_area",
                             "diagnosis")

# The declared DRAFT home is the store's (reconciliation_store.DEFAULT_DRAFTS_DIR); these are the subdirectories and the
# artifact kinds this pass renders into it.
DRAFTS_SUBDIR_CRITERIA = "criteria"
DRAFTS_SUBDIR_RUNBOOK = "runbook"
DRAFT_CRITERIA = "regression_criteria"
DRAFT_RUNBOOK = "runbook_action"
SCHEMA_CRITERIA_DRAFT = "veldo.regression_criteria/v1"

# The label a REFUSED rendered draft is reported under (it never reaches a path, so it never has a filename).
DRAFT_VALIDATION_LABEL = "the rendered runbook action draft"

# THE NAMED REFUSAL TAXONOMY (fail closed): the refusals are the product (C1). Every path that does not settle returns one
# of these verbatim on the result, so the failure mode is legible from the record, not inferred from a stack trace. The
# three the STORE decides are named by the store and FOLDED IN here, never restated, so the taxonomy is one closed set.
REFUSE_NOT_DIAGNOSED = "incident_not_diagnosed"
REFUSE_MISSING_VALIDATION = "missing_diagnosis_validation"
REFUSE_MACHINE_VALIDATOR = "machine_validated_diagnosis"
REFUSE_VALIDATION_UNBOUND_REMEDY = "validation_binds_no_remedy"
REFUSE_VALIDATION_DIGEST_MISMATCH = "diagnosis_digest_mismatch"
REFUSE_OPEN_EMERGENCY_DEBT = "open_emergency_backfill_debt"
REFUSE_DRAFT_REVIEWED = "reviewed_draft_refused"
REFUSE_DRAFT_INVALID = "structurally_invalid_draft"
REFUSE_UNSUPPORTED_EXECUTION_CLAIM = "unsupported_execution_claim"
REFUSE_DRAFT_PATH_FORBIDDEN = _ST.REFUSE_DRAFT_PATH_FORBIDDEN
REFUSE_RECEIPT_CONFLICT = _ST.REFUSE_RECEIPT_CONFLICT
REFUSE_RECEIPT_UNREADABLE = _ST.REFUSE_RECEIPT_UNREADABLE

REFUSALS = frozenset({
    REFUSE_NOT_DIAGNOSED, REFUSE_MISSING_VALIDATION, REFUSE_MACHINE_VALIDATOR,
    REFUSE_VALIDATION_UNBOUND_REMEDY, REFUSE_VALIDATION_DIGEST_MISMATCH, REFUSE_OPEN_EMERGENCY_DEBT,
    REFUSE_DRAFT_PATH_FORBIDDEN, REFUSE_DRAFT_REVIEWED, REFUSE_DRAFT_INVALID,
    REFUSE_UNSUPPORTED_EXECUTION_CLAIM, REFUSE_RECEIPT_CONFLICT, REFUSE_RECEIPT_UNREADABLE,
})

# The outcome vocabulary a caller reads off a result.
OUTCOME_SETTLED = "settled"
OUTCOME_ALREADY = "already_settled"
OUTCOME_REFUSED = "refused"

REVIEW_LANE_GUIDANCE = (
    "REVIEW LANE (unmechanizable, NG5): whether these drafted regression criteria are SUFFICIENT to "
    "catch this failure again, and whether the drafted runbook action is the RIGHT action, are a human "
    "reviewer's judgment at promotion time. The mechanical floor is that the drafts exist, are "
    "structurally valid, are unreviewed, and cannot be promoted by the machine."
)

def _lifecycle_event(step):
    """The lifecycle event type for one step, SELECTED from the vocabulary the contract owns, never a literal here."""
    for etype in sorted(INCIDENT_EVENT_TYPES):
        if etype.rsplit(".", 1)[-1] == step:
            return etype
    raise ReconcileError("the incident event vocabulary carries no %r lifecycle step" % step)

INCIDENT_CLOSED = _lifecycle_event(STATUS_CLOSED)

def _is_str(v):
    return isinstance(v, str) and v.strip() != ""

def _norm(v):
    return v.strip().lower() if isinstance(v, str) else None

def _one_line(v):
    """One rendered scalar, whitespace collapsed: the front-matter subset is line oriented, so no value has a newline."""
    return " ".join(str("" if v is None else v).split())

def _as_bool(v):
    """The value as a real boolean, or None (the one parser leaves an unquoted true/false as that string; a truthy-
    looking "yes" or 1 is NOT accepted). The idiom each sibling contract organ carries; not a parser."""
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return {"true": True, "false": False}.get(v.strip().lower())
    return None

def _digest(payload):
    """The canonical short-sha digest of a parsed structure, the form proof_digest and proposal_digest use; parses nothing."""
    return "sha256:" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:16]

def _report(fail, name, msg):
    """Emit ONE named line through the injected fail(name, msg) reporter, so every decision is diagnosable from output."""
    if callable(fail):
        fail(name, msg)
    return msg

# --- AC1: the failure signature and recurrence (pure: no clock, no filesystem, no randomness) -----
def _norm_identity(v):
    """One identity field NORMALIZED (whitespace collapsed, case folded). None when it is not a non-empty string."""
    if not _is_str(v):
        return None
    return " ".join(str(v).split()).casefold()

def failure_signature(incident):
    """The DETERMINISTIC identity of a FAILURE: a normalized digest over exactly the identity-of-failure fields, so the
    same failure shares a signature while title, severity, timeline, or id do not change it. PURE and identical across
    processes (sha256 over canonical JSON, never Python's salted hash). None when the record is malformed or an
    identity field is missing, so recurrence SKIPS it rather than silently matching."""
    if not isinstance(incident, dict):
        return None
    material = {}
    for field in IDENTITY_FIELDS:
        value = _norm_identity(incident.get(field))
        if value is None:
            return None
        material[field] = value
    for field in OPTIONAL_IDENTITY_FIELDS:
        if field in incident:
            value = _norm_identity(incident.get(field))
            if value is None:
                return None  # present but malformed: fail closed, never silently dropped
            material[field] = value
    return _digest(material)

def recurrence(incident, prior_incidents):
    """The ORDERED ids of prior incidents sharing this incident's failure signature, excluding itself and skipping any
    record whose signature cannot be computed. Recorded order, de-duplicated, pure."""
    signature = failure_signature(incident)
    if signature is None:
        return []
    iid = incident.get("id") if isinstance(incident, dict) else None
    out = []
    for prior in prior_incidents or []:
        if not isinstance(prior, dict):
            continue
        pid = prior.get("id")
        if not _is_str(pid) or pid == iid or pid in out:
            continue
        if failure_signature(prior) == signature:
            out.append(pid)
    return out

def missing_specification(recurrence_ids):
    """The method's reading, REPORTED not reinterpreted: an emergency that recurs is a MISSING SPECIFICATION (VELDO.md)."""
    return bool(recurrence_ids)

# --- AC2: the diagnosis material, its independent recompute, and the close gate -------------------
def diagnosis_material(incident, remedy=None):
    """The material a human validation attests to, read FROM THE RECORDS, never from the validation itself. Two halves,
    because the diagnosis is not on the incident: the incident's identity and failure fields (and a diagnosis field if
    the record happens to carry one, which veldo.incident/v1 does not define), PLUS - whenever a remedy exists - that
    remedy's id and its CANONICAL PROPOSAL DIGEST, which is what actually carries the diagnosis, the cited evidence, and
    the proposed action a human validated. Reusing action_executor.proposal_digest means the human's validation and the
    executor's confirmation bind ONE artifact identity rather than two definitions of it (see the module docstring)."""
    if not isinstance(incident, dict):
        return {}
    out = {}
    for field in DIAGNOSIS_MATERIAL_FIELDS:
        if field in incident and _is_str(incident.get(field)):
            out[field] = _one_line(incident.get(field))
    timeline = incident.get("timeline")
    if isinstance(timeline, dict) and _is_str(timeline.get("diagnosed_at")):
        out["diagnosed_at"] = _one_line(timeline.get("diagnosed_at"))
    if isinstance(remedy, dict):
        out["remedy"] = _one_line(remedy.get("id"))
        out["remedy_proposal_digest"] = proposal_digest(remedy)
    return out

def diagnosis_digest(incident, remedy=None):
    """The diagnosis material's digest, RECOMPUTED here over the incident AND its remedy; a digest a validation carried
    about itself is not trusted, and a digest over the incident alone would attest to a failure identity and a timestamp
    while leaving the diagnosis, its cited evidence, and the proposed action free to change (the WARP-1208 review's F2)."""
    return _digest(diagnosis_material(incident, remedy))

def validation_binds_remedy(remedy, validation):
    """Whether the validation NAMES the remedy it validated (bound_remedy == the remedy's id). An attestation names its
    subject and binds its digest, the shape request_reconcile's attestations already carry; with no remedy in play there
    is no subject to name, so this holds trivially."""
    if not isinstance(remedy, dict):
        return True
    named = (validation or {}).get("bound_remedy") if isinstance(validation, dict) else None
    return _is_str(named) and named.strip() == _one_line(remedy.get("id"))

def _validation_refusal(incident, remedy, validation):
    """The four fail-closed conditions on the HUMAN DIAGNOSIS VALIDATION (O5), each REFUSED BY NAME: absent (never
    defaults open), machine-authored, naming no remedy while a remedy exists, or bound to a digest that is not the one
    recomputed from the incident AND the remedy."""
    if not isinstance(validation, dict) or not _is_str(validation.get("validated_by")):
        return (REFUSE_MISSING_VALIDATION,
                "no human diagnosis validation was supplied for incident %r: the diagnosis is validated by a HUMAN (O5) "
                "and its absence REFUSES, never defaults open" % (incident.get("id"),))
    who = validation.get("validated_by")
    if _norm(who) in MACHINE_ACTORS:
        return (REFUSE_MACHINE_VALIDATOR,
                "the validation names the machine actor %r: a machine never validates a diagnosis, so "
                "the responder can never validate its own (NG4, authorization.MACHINE_ACTORS)" % (who,))
    if not validation_binds_remedy(remedy, validation):
        return (REFUSE_VALIDATION_UNBOUND_REMEDY,
                "the validation binds no remedy (bound_remedy=%r) while remedy %r carries the diagnosis and its cited "
                "evidence: a validation that names no subject attests to a failure identity, not to a diagnosis, so it "
                "REFUSES rather than settling the proposed action a human never validated"
                % ((validation or {}).get("bound_remedy"), remedy.get("id") if isinstance(remedy, dict) else None))
    recomputed = diagnosis_digest(incident, remedy)
    if validation.get("bound_digest") != recomputed:
        return (REFUSE_VALIDATION_DIGEST_MISMATCH,
                "the validation binds to digest %r but the diagnosis material of %r (with remedy %r) RECOMPUTES to %r: "
                "an attestation bound to a value it displayed proves nothing, and a remedy edited or swapped after the "
                "validation invalidates it"
                % (validation.get("bound_digest"), incident.get("id"),
                   remedy.get("id") if isinstance(remedy, dict) else NONE_VALUE, recomputed))
    return None

def _debt_refusal(incident, debt_reader):
    """The EMERGENCY-LANE condition, DEPENDENCY INVERTED: debt_reader(incident) returns truthy on an OPEN backfill debt.
    NO reader stands the condition down HONESTLY; an open debt refuses so the fix flows the lane first; a reader that
    raises also refuses. No enforcement module is imported."""
    if debt_reader is None:
        return None
    try:
        open_debt = debt_reader(incident)
    except Exception as exc:  # a debt surface that cannot be read fails CLOSED, never open
        return (REFUSE_OPEN_EMERGENCY_DEBT, "the injected emergency-debt reader raised (%s): an unreadable debt "
                                            "surface refuses rather than assuming there is no debt" % (exc,))
    if open_debt:
        return (REFUSE_OPEN_EMERGENCY_DEBT,
                "incident %r carries an OPEN emergency backfill debt (%s): the fix flows the emergency lane "
                "(specification, proof, review backfilled) BEFORE the incident is settled"
                % (incident.get("id"), _one_line(open_debt)))
    return None

# --- AC4: the execution, reconciled against the RECEIPT and never against a claim -----------------
def execution_claim_refusal(remedy, execution_receipt, execution_claim):
    """THE EXECUTION CLAIM IS REFUSED WITHOUT ITS RECEIPT. An execution is CLAIMED when a claim or a receipt is passed at
    all (nothing claimed is the honest none path) and SUPPORTED only when a receipt for a real remedy carries the
    proposal digest RECOMPUTED through the shipped proposal_digest. Anything else refuses: a reconciliation that
    overstates what happened is worse than none."""
    if not (bool(execution_claim) or isinstance(execution_receipt, dict)):
        return None
    recomputed = proposal_digest(remedy) if isinstance(remedy, dict) else None
    recorded = execution_receipt.get("proposal_digest") if isinstance(execution_receipt, dict) else None
    supported = (isinstance(execution_receipt, dict) and isinstance(remedy, dict)
                 and _is_str(recorded) and recorded == recomputed)
    if not supported:
        return (REFUSE_UNSUPPORTED_EXECUTION_CLAIM,
                "an execution was asked to be recorded and cannot be supported (receipt=%s, remedy=%s, receipt digest "
                "%r, recomputed %r): an execution is recorded from its RECEIPT bound to the exact proposal, never from "
                "the remedy's own claim"
                % (isinstance(execution_receipt, dict), isinstance(remedy, dict), recorded, recomputed))
    return None

def what_was_done(incident, remedy, execution_receipt):
    """WHAT WAS DONE, in the plan's W8 language: the incident, the remedy when one exists, and the executed action and
    parameters taken from the execution RECEIPT, never from the remedy's proposed_action (which is only what was
    PROPOSED). A receipt with no parameters yields none, never the remedy's."""
    out = {"incident": incident.get("id"),
           "remedy": remedy.get("id") if isinstance(remedy, dict) else NONE_VALUE,
           "action": NONE_VALUE, "parameters": NONE_VALUE, "system": NONE_VALUE, "source": NONE_VALUE}
    if not isinstance(execution_receipt, dict):
        out["detail"] = "no execution was reconciled, so the executed action is recorded as none, never invented"
        return out
    out["source"] = "the execution receipt (never the remedy's own claim)"
    for field in ("action", "system"):
        if _is_str(execution_receipt.get(field)):
            out[field] = execution_receipt.get(field)
    if isinstance(execution_receipt.get("parameters"), dict):
        out["parameters"] = dict(execution_receipt.get("parameters"))
    else:
        out["detail"] = ("the execution receipt recorded no parameters, so they are none here: the remedy's proposed "
                         "parameters are never substituted for what ran")
    return out

def what_it_proved(remedy, execution_receipt):
    """WHAT IT PROVED: the receipt's RECORDED outcome (executed, refused with its named reason, or unrecorded, never
    inferred), its proposal digest, and the receipt's own content digest. All none when never executed."""
    if not isinstance(execution_receipt, dict):
        return {"outcome": NONE_VALUE, "refused": NONE_VALUE,
                "proposal_digest": NONE_VALUE, "receipt_digest": NONE_VALUE}
    refused = execution_receipt.get("refused")
    executed = _as_bool(execution_receipt.get("executed")) is True
    out = {"outcome": "executed" if executed else ("refused" if _is_str(refused) else "unrecorded"),
           "refused": NONE_VALUE if executed or not _is_str(refused) else refused}
    out["proposal_digest"] = execution_receipt.get("proposal_digest") or NONE_VALUE
    out["recomputed_proposal_digest"] = proposal_digest(remedy) if isinstance(remedy, dict) else NONE_VALUE
    out["receipt_digest"] = _digest(execution_receipt)
    return out

# --- AC3: the two drafts a human promotes ---------------------------------------------------------
def draft_action_problems(text):
    """The SHIPPED contract's problems with a RENDERED runbook draft, as a list of messages (empty when it is valid).
    THE STRUCTURAL VALIDITY IS ENFORCED, NOT EXHIBITED: the rendered text is parsed by the ONE front-matter parser and
    judged by the ONE structural validator (action.validate_action), so a draft is held to exactly the contract the
    whitelist store holds an action to and NOTHING is reimplemented here. A draft that does not parse, or does not parse
    to a mapping, is a problem too (fail closed)."""
    problems = []

    def collect(where, msg):
        problems.append(msg)
        return 1

    try:
        parsed = _V.parse_yamlish(text)
    except ValueError as exc:
        return ["the rendered draft is outside the record subset the one parser reads: %s" % (exc,)]
    if not isinstance(parsed, dict):
        return ["the rendered draft does not parse to a mapping"]
    _ACT.validate_action(parsed, None, DRAFT_VALIDATION_LABEL, collect)
    return problems

def criteria_draft_path(incident):
    """The regression criteria draft's declared path, relative to the drafts directory."""
    return "%s/%s-regression-criteria.yaml" % (DRAFTS_SUBDIR_CRITERIA, _token(incident.get("id")))

def runbook_draft_path(incident, action_ref):
    """The runbook action draft's declared path, relative to the drafts directory."""
    return "%s/%s-%s.yaml" % (DRAFTS_SUBDIR_RUNBOOK, _token(incident.get("id")), _token(action_ref))

def _drafted_at(incident):
    """WHEN the draft describes, from the incident's RECORDED timeline and never a clock, so a re-render is identical."""
    timeline = incident.get("timeline") if isinstance(incident, dict) else None
    if isinstance(timeline, dict):
        for field in ("diagnosed_at", "opened_at"):
            if _is_str(timeline.get(field)):
                return _one_line(timeline.get(field))
    return UNRECORDED

def _recurrence_scalar(recurrence_ids):
    """The recurrence set as an inline list the front-matter subset reads back as a list."""
    return "[%s]" % ", ".join(_token(i) for i in recurrence_ids)

def render_criteria_draft(incident, signature, recurrence_ids):
    """Render the REGRESSION CRITERIA DRAFT from the FAILURE MODE: the affected behavior becomes the acceptance criterion
    and the signal the regression criterion, carrying the incident id, signature, and recurrence set. A DRAFT only a
    HUMAN promotes: status draft, no decider, no promoted flag, no review. PURE, so a re-render is byte-identical."""
    return "\n".join([
        "# VELDO regression criteria DRAFT (%s): the failure mode of a reconciled incident, rendered as"
        % SCHEMA_CRITERIA_DRAFT,
        "# acceptance and regression criteria for a HUMAN to promote into a specification (W8 of PLAN-0012, outcome O5).",
        "# The machine drafts; a human judges whether these criteria are SUFFICIENT and promotes them into a real",
        "# veldo.spec/v1 criterion that flows the normal loop. This draft is inert: no gate sweeps it, no machine promotes it.",
        "# %s" % REVIEW_LANE_GUIDANCE,
        "schema: %s" % SCHEMA_CRITERIA_DRAFT,
        "status: draft",
        "drafted_by: %s (machine draft; a human promotes it into a specification)" % SETTLED_BY,
        "drafted_at: %s" % _drafted_at(incident),
        "incident: %s" % _one_line(incident.get("id")),
        "failure_signature: %s" % signature,
        "recurrence_of: %s" % _recurrence_scalar(recurrence_ids),
        "missing_specification: %s" % ("true" if missing_specification(recurrence_ids) else "false"),
        "acceptance_criterion: the affected behavior holds again and stays held:",
        "  %s" % _one_line(incident.get("affected_behavior")),
        "regression_criterion: a regression reproduces the recorded failure signal and FAILS before the",
        "  fix and PASSES after it:",
        "  %s" % _one_line(incident.get("signal")),
        "review_lane: %s" % REVIEW_LANE_GUIDANCE,
    ]) + "\n"

def _draft_review_block(review):
    """The review block a DRAFT may carry: exactly status proposed. None when REFUSED - any other status, or ANY verdict
    or reviewer field, is the machine-recorded review the method forbids."""
    requested = review if isinstance(review, dict) else {}
    status = requested.get("status", DRAFT_REVIEW_STATUS)
    if status != DRAFT_REVIEW_STATUS or any(f in requested for f in FORBIDDEN_DRAFT_REVIEW_FIELDS):
        return None
    return {"status": DRAFT_REVIEW_STATUS}

def _draft_reversibility(remedy):
    """The drafted action's reversibility from the remedy's RECORDED analysis. With none usable the draft DEGRADES DOWN
    to the most dangerous class, driving the critical risk floor until a human classifies it (C3)."""
    rev = remedy.get("reversibility") if isinstance(remedy, dict) else None
    if (isinstance(rev, dict) and rev.get("class") in _ACT.REVERSIBILITY_CLASSES
            and _is_str(rev.get("analysis")) and _as_bool(rev.get("data_mutating")) is not None):
        return {"class": rev.get("class"), "analysis": _one_line(rev.get("analysis")),
                "data_mutating": "true" if _as_bool(rev.get("data_mutating")) else "false"}
    return {"class": _CONSERVATIVE_REVERSIBILITY, "data_mutating": "true",
            "analysis": "the remedy recorded no usable reversibility analysis, so this draft assumes the most dangerous "
                        "class until a human classifies it at promotion (fail closed)"}

def _draft_risk_class(remedy, reversibility):
    """The drafted risk class: the HIGHER of the remedy's class and the shipped whitelist floor; nothing lowers it (C2)."""
    ranks = [_ACT.RISK_CLASSES.index(_ACT.risk_floor({"reversibility": reversibility}))]
    declared = remedy.get("risk_class") if isinstance(remedy, dict) else None
    if declared in _ACT.RISK_CLASSES:
        ranks.append(_ACT.RISK_CLASSES.index(declared))
    return _ACT.RISK_CLASSES[max(ranks)]

def _draft_parameter_specs(remedy):
    """One declared spec per parameter the remedy's proposed action carried, typed from the observed value, with NO
    constraint: tightening the validation is the human's review, and inventing one would invent a safety envelope."""
    pa = remedy.get("proposed_action") if isinstance(remedy, dict) else None
    params = pa.get("parameters") if isinstance(pa, dict) else None
    if not isinstance(params, dict):
        return []
    out = []
    for key in sorted(params, key=str):
        value, kind = params[key], "string"
        for word, types in (("boolean", bool), ("integer", int), ("number", float)):
            if isinstance(value, types):
                kind = word
                break
        out.append({"name": _one_line(key), "type": kind, "required": "true"})
    return out

def _draft_canary(remedy):
    """The drafted canary from the remedy's recorded shape; a claim with no shape drafts unsupported, never invented."""
    canary = remedy.get("canary") if isinstance(remedy, dict) else None
    if isinstance(canary, dict) and _as_bool(canary.get("supported")) is True and _is_str(canary.get("shape")):
        return {"supported": "true", "shape": _one_line(canary.get("shape"))}
    return {"supported": "false"}

def proposed_action_ref(remedy):
    """The whitelist action reference the remedy proposed, or None (then no runbook draft, and none is recorded)."""
    pa = remedy.get("proposed_action") if isinstance(remedy, dict) else None
    ref = pa.get("action") if isinstance(pa, dict) else None
    return ref if _is_str(ref) else None

def render_runbook_draft(incident, remedy, signature, recurrence_ids, system=None, review=None):
    """Render the RUNBOOK ACTION DRAFT from the remedy's proposed action: a veldo.action/v1 record STRUCTURALLY VALID
    against the shipped contract and carrying review status PROPOSED, so the shipped whitelist physics excludes it and
    it does not exist to the machine execution path (NG2). Returns None when the requested review block is REFUSED.
    PURE, so a re-render is byte-identical."""
    review_block = _draft_review_block(review)
    if review_block is None:
        return None
    action_ref = proposed_action_ref(remedy)
    reversibility = _draft_reversibility(remedy)
    canary = _draft_canary(remedy)
    lines = [
        "# VELDO runbook action DRAFT (%s, review status %s): the remediation of a reconciled incident,"
        % (_ACT.SCHEMA_ACTION, DRAFT_REVIEW_STATUS),
        "# rendered as a runbook action for a HUMAN to review and promote (W8 of PLAN-0012, outcome O5). Runbook actions",
        "# self-maintain from real incidents AS DRAFTS. This one is deliberately UNREVIEWED: the shipped whitelist admits",
        "# only a reviewed, approved, digest-current action, so it does not exist to the machine execution path and no",
        "# machine can promote it; it also lives OUTSIDE the whitelist store, so promotion is a human act of moving it in",
        "# and reviewing it. The parameter constraints are deliberately unconstrained: tightening the safety envelope is",
        "# part of the human review. %s" % REVIEW_LANE_GUIDANCE,
        "schema: %s" % _ACT.SCHEMA_ACTION,
        "id: %s" % _token(action_ref),
        "title: runbook action drafted from incident %s (%s)"
        % (_one_line(incident.get("id")), _one_line(action_ref)),
        "system: %s" % (_one_line(system) if _is_str(system) else UNRECORDED),
        "risk_class: %s" % _draft_risk_class(remedy, reversibility),
        "reversibility:",
        "  class: %s" % reversibility["class"],
        "  analysis: %s" % reversibility["analysis"],
        "  data_mutating: %s" % reversibility["data_mutating"],
    ]
    specs = _draft_parameter_specs(remedy)
    lines.append("parameters: []" if not specs else "parameters:")
    for spec in specs:
        lines.extend(["  - name: %s" % spec["name"], "    type: %s" % spec["type"],
                      "    required: %s" % spec["required"]])
    lines.append("rollback: %s" % (_one_line(remedy.get("rollback")) if _is_str(remedy.get("rollback")) else
                 "unrecorded: the remedy recorded no rollback plan, so a human supplies one before promotion"))
    lines.extend(["canary:", "  supported: %s" % canary["supported"]])
    if "shape" in canary:
        lines.append("  shape: %s" % canary["shape"])
    lines.extend([
        "review:",
        "  status: %s" % review_block["status"],
        "drafted_from:",
        "  incident: %s" % _one_line(incident.get("id")),
        "  remedy: %s" % (_one_line(remedy.get("id")) if isinstance(remedy, dict) else NONE_VALUE),
        "  proposed_action: %s" % _one_line(action_ref),
        "  failure_signature: %s" % signature,
        "  recurrence_of: %s" % _recurrence_scalar(recurrence_ids),
        "  drafted_at: %s" % _drafted_at(incident),
        "  drafted_by: %s (machine draft; only a human reviews and promotes it)" % SETTLED_BY,
        "  review_lane: %s" % REVIEW_LANE_GUIDANCE,
    ])
    return "\n".join(lines) + "\n"

def write_drafts(incident, remedy, signature, recurrence_ids, store,
                 execution_receipt=None, draft_review=None):
    """Render and write the TWO DRAFTS a human promotes through the store's declared DRAFT directory. Returns (drafts,
    refusal): each draft's kind, path (relative, so the receipt stays portable), digest, and per-run outcome, and None
    or (name, detail) when the path or reviewed-draft guard refuses. A runbook draft is rendered only when the remedy
    names a proposed action; otherwise the receipt records none."""
    drafts = []
    put = store.put_draft(criteria_draft_path(incident),
                          render_criteria_draft(incident, signature, recurrence_ids))
    if put.get("refused"):
        return drafts, (put.get("refused"), put.get("detail"))
    drafts.append({"kind": DRAFT_CRITERIA, "path": put.get("path"), "digest": put.get("digest"),
                   "outcome": put.get("outcome")})
    action_ref = proposed_action_ref(remedy)
    if action_ref is None:
        drafts.append({"kind": DRAFT_RUNBOOK, "path": NONE_VALUE, "digest": NONE_VALUE,
                       "outcome": NONE_VALUE,
                       "detail": "the incident has no remedy naming a proposed whitelist action, so no runbook action "
                                 "draft is rendered (recorded as none, never invented)"})
        return drafts, None
    system = execution_receipt.get("system") if isinstance(execution_receipt, dict) else None
    text = render_runbook_draft(incident, remedy, signature, recurrence_ids,
                                system=system, review=draft_review)
    if text is None:
        return drafts, (REFUSE_DRAFT_REVIEWED,
                        "the runbook draft was asked to carry the review block %r: a draft carries review status %r and "
                        "NO verdict or reviewer, because a machine-recorded review is the rubber stamp the method "
                        "forbids" % (draft_review, DRAFT_REVIEW_STATUS))
    # THE STRUCTURAL VALIDITY GUARD, inside the write path: what the SHIPPED validator refuses is never written. A
    # contract-valid remedy can still render an invalid action (a parameter whose key is empty or whitespace only), and
    # an unpromotable artifact recorded on the receipt as a regression criterion is a claim the receipt cannot support.
    problems = draft_action_problems(text)
    if problems:
        return drafts, (REFUSE_DRAFT_INVALID,
                        "the rendered runbook draft does not pass the SHIPPED %s validator (%s): a draft the contract "
                        "refuses is REFUSED here rather than written, because only a structurally valid draft is one a "
                        "human can review and promote" % (_ACT.SCHEMA_ACTION, "; ".join(problems)))
    put2 = store.put_draft(runbook_draft_path(incident, action_ref), text)
    if put2.get("refused"):
        return drafts, (put2.get("refused"), put2.get("detail"))
    drafts.append({"kind": DRAFT_RUNBOOK, "path": put2.get("path"), "digest": put2.get("digest"),
                   "outcome": put2.get("outcome")})
    return drafts, None

# --- AC4: the content-addressed receipt and the append-only compare-and-swap store ----------------
def reconciliation_id(incident_id, signature, remedy_id, execution_digest):
    """The CONTENT-ADDRESSED receipt id: "REC-" plus a digest over the SETTLEMENT IDENTITY (incident id, failure
    signature, remedy id, execution receipt digest). Never a clock and never a counter, so replay safety follows from
    the id itself."""
    return "REC-" + hashlib.sha256(json.dumps(
        {"incident": incident_id, "failure_signature": signature, "remedy": remedy_id,
         "execution_receipt_digest": execution_digest},
        sort_keys=True, default=str).encode()).hexdigest()[:12]

def _recorded_drafts(drafts):
    """The draft entries AS RECORDED: kind, path, digest, and the honest detail when a draft is none. The per-run outcome
    (created versus exists) is EXCLUDED - it describes the pass, not the settlement, and would make a replay look like
    a conflict."""
    out = []
    for draft in drafts:
        entry = {"kind": draft.get("kind"), "path": draft.get("path"), "digest": draft.get("digest")}
        if draft.get("detail"):
            entry["detail"] = draft.get("detail")
        out.append(entry)
    return out

def reconciliation_record(rec_id, incident, remedy, signature, recurrence_ids, validation,
                          execution_receipt, drafts):
    """The veldo.reconciliation/v1 receipt: the plan's three questions plus the signature, the recurrence set, and the
    missing-specification reading. Pure and clock-free, so the same settlement recomputes a byte-identical record and
    the compare-and-swap tells a REPLAY from a CONFLICT."""
    return {
        "schema": SCHEMA,
        "id": rec_id,
        "settled_by": SETTLED_BY,
        "incident": incident.get("id"),
        "remedy": remedy.get("id") if isinstance(remedy, dict) else NONE_VALUE,
        "failure_signature": signature,
        "recurrence_of": list(recurrence_ids),
        "missing_specification": missing_specification(recurrence_ids),
        "diagnosis_validation": {
            "validated_by": (validation or {}).get("validated_by"),
            "validated_at": (validation or {}).get("validated_at") or NONE_VALUE,
            "bound_remedy": (validation or {}).get("bound_remedy") or NONE_VALUE,
            "bound_digest": (validation or {}).get("bound_digest"),
            "recomputed_digest": diagnosis_digest(incident, remedy),
            # WHAT THE DIGEST COVERS, spelled out so a stranger reading the receipt knows what a human attested to
            # rather than inferring it from the block's name.
            "binds": ("the incident's diagnosis material and remedy %s by its canonical proposal digest %s (the "
                      "diagnosis, its cited evidence, and the proposed action)"
                      % (remedy.get("id"), proposal_digest(remedy)) if isinstance(remedy, dict) else
                      "the incident's diagnosis material only: this incident has no remedy, so there is no "
                      "diagnosis artifact to bind"),
        },
        "what_was_done": what_was_done(incident, remedy, execution_receipt),
        "what_it_proved": what_it_proved(remedy, execution_receipt),
        "what_regression_criteria_it_leaves": _recorded_drafts(drafts),
    }

def _closed_event(record):
    """The incident.closed event through the ONE emitter, its type SELECTED from the contract's INCIDENT_EVENT_TYPES.
    This event is the sole source for the WARP-1210 numbers, so a duplicate would corrupt every measure: it is emitted
    only on the FIRST settlement."""
    return _EV.make_event(INCIDENT_CLOSED, producer=SETTLED_BY,
                          correlation_id=record.get("incident"),
                          extra={"incident": record.get("incident"),
                                 "reconciliation": record.get("id"),
                                 "failure_signature": record.get("failure_signature"),
                                 "recurrence_of": list(record.get("recurrence_of") or []),
                                 "missing_specification": record.get("missing_specification")})

# --- the pass (pure control logic over the injected seams) ----------------------------------------
def _result(base, outcome, **extra):
    out = dict(base)
    out["outcome"] = outcome
    out.update(extra)
    return out

def _refused(base, refusal, detail, fail):
    """One REFUSED result, its reason NAMED from the closed taxonomy and reported through the injected reporter."""
    return _result(base, OUTCOME_REFUSED, refused=refusal,
                   reason=_report(fail, base.get("incident"), "%s: %s" % (refusal, detail)))

def _unreadable_detail(rec_id):
    """The one detail behind the unreadable-receipt refusal, so the replay path and the settle path say the same thing."""
    return ("receipt %s EXISTS and cannot be read or parsed: an existing-but-unreadable record is a CONFLICT, never an "
            "absence, so it is not overwritten and no second %s event is appended for this incident. A human resolves "
            "the corrupt record (restore it from history, or remove it deliberately) before the settlement is retried."
            % (rec_id, INCIDENT_CLOSED))

def reconcile_incident(incident, store, remedy=None, prior_incidents=None, validation=None,
                       execution_receipt=None, execution_claim=None, debt_reader=None,
                       draft_review=None, fail=None):
    """Reconcile ONE diagnosed incident into a settled piece of intent. Returns a result a stranger reads: the incident,
    the content-addressed receipt id, the failure signature, the recurrence set and its missing-specification reading,
    the outcome (settled | already_settled | refused), the named refusal when it refused, the drafts, and the receipt.

    incident/remedy: the parsed veldo.incident/v1 record and veldo.remedy/v1 proposal (None with no remedy). store: a
    ReconciliationStore (the receipt AND the drafts). prior_incidents: the records recurrence is detected against.
    validation: the HUMAN diagnosis validation {validated_by, bound_remedy, bound_digest, validated_at}; absent,
    machine-authored, naming no remedy while one exists, or bound to a digest that is not the one RECOMPUTED here from
    the incident AND the remedy each refuse. execution_receipt: what the executor (W6) wrote, or None; execution_claim
    truthy ASKS an execution to be recorded and refuses without a supporting receipt. debt_reader: injected
    emergency-backfill-debt reader (default None stands down honestly). draft_review: a review block for the runbook
    draft, which exists only to be REFUSED. fail: injected fail(name, msg) reporter.

    The guard order is deliberate and fails CLOSED at each step: the status gate, the diagnosis validation (absent,
    machine, unbound remedy, digest), the emergency debt, the execution claim, the drafts (the path guard, the
    reviewed-draft refusal, the structural-validity refusal), then the store's compare-and-swap and its
    unreadable-receipt refusal. It starts no process, thread, or timer and executes nothing."""
    if not isinstance(incident, dict) or not _is_str(incident.get("id")):
        raise ReconcileError("reconcile_incident needs a veldo.incident/v1 record with a non-empty id")
    if store is None:
        raise ReconcileError("reconcile_incident needs a ReconciliationStore (the one impure edge)")
    signature = failure_signature(incident)
    if signature is None:
        raise ReconcileError("incident %r carries no computable failure signature: the identity-of-failure fields %s "
                             "must each be a non-empty string" % (incident.get("id"), list(IDENTITY_FIELDS)))

    recurrence_ids = recurrence(incident, prior_incidents)
    remedy_id = remedy.get("id") if isinstance(remedy, dict) else None
    execution_digest = _digest(execution_receipt) if isinstance(execution_receipt, dict) else NONE_VALUE
    rec_id = reconciliation_id(incident.get("id"), signature, remedy_id, execution_digest)
    base = {"incident": incident.get("id"), "receipt_id": rec_id, "failure_signature": signature,
            "recurrence_of": list(recurrence_ids),
            "missing_specification": missing_specification(recurrence_ids),
            "remedy": remedy_id or NONE_VALUE, "refused": None, "drafts": [], "receipt": None}

    status = incident.get("status")
    # (a) THE STATUS GATE. An OPEN incident is not reconcilable (a human-validated diagnosis is the
    # precondition), and an ALREADY-CLOSED incident takes the IDEMPOTENT REPLAY PATH, never a second
    # settlement: its settlement identity is recomputed and the EXISTING receipt is returned.
    if status != STATUS_DIAGNOSED:
        if status == STATUS_CLOSED:
            existing = store.get(rec_id)
            # A receipt that EXISTS and cannot be READ is never read AS a settlement: the replay path
            # refuses by name rather than returning a corrupt record as the proof of a closed incident.
            if existing is UNREADABLE:
                return _refused(base, REFUSE_RECEIPT_UNREADABLE, _unreadable_detail(rec_id), fail)
            if existing is not None:
                return _result(base, OUTCOME_ALREADY, receipt=existing, reason=_report(
                    fail, incident.get("id"), "already settled (idempotent replay): receipt %s exists, so no second "
                                              "record and no second event" % rec_id))
        return _refused(base, REFUSE_NOT_DIAGNOSED,
                        "the incident status is %r, not %r: an open incident is not reconcilable and a closed one with "
                        "no recorded reconciliation is not settled a second time (the lifecycle statuses are %s)"
                        % (status, STATUS_DIAGNOSED, sorted(INCIDENT_STATUSES)), fail)

    # (b, c, d) THE HUMAN DIAGNOSIS VALIDATION over the incident AND its remedy, then (e) the EMERGENCY
    # LANE through the injected reader, then the EXECUTION CLAIM reconciled against the RECEIPT and never
    # against the remedy's claim.
    refusal = _validation_refusal(incident, remedy, validation)
    if refusal is None:
        refusal = _debt_refusal(incident, debt_reader)
    if refusal is None:
        refusal = execution_claim_refusal(remedy, execution_receipt, execution_claim)
    if refusal is not None:
        return _refused(base, refusal[0], refusal[1], fail)

    # THE TWO DRAFTS, written before the receipt because the receipt records their paths and digests. They
    # are inert, unreviewed, outside the whitelist store, and never overwritten, so writing them ahead of
    # a compare-and-swap conflict leaves nothing to unwind.
    drafts, refusal = write_drafts(incident, remedy, signature, recurrence_ids, store,
                                   execution_receipt=execution_receipt, draft_review=draft_review)
    base["drafts"] = drafts
    if refusal is not None:
        return _refused(base, refusal[0], refusal[1], fail)

    record = reconciliation_record(rec_id, incident, remedy, signature, recurrence_ids, validation,
                                   execution_receipt, drafts)
    outcome, stored = store.settle(rec_id, record, [_closed_event(record)])
    if outcome == "unreadable":
        return _refused(base, REFUSE_RECEIPT_UNREADABLE, _unreadable_detail(rec_id), fail)
    if outcome == "conflict":
        return _refused(dict(base, receipt=stored), REFUSE_RECEIPT_CONFLICT,
                        "receipt %s already records a DIFFERENT reconciliation of this settlement identity: an "
                        "append-only store refuses a conflicting write rather than overwriting history" % rec_id, fail)
    if outcome == "exists":
        return _result(base, OUTCOME_ALREADY, receipt=stored, reason=_report(
            fail, incident.get("id"), "already settled (idempotent replay): receipt %s recorded the same settlement, so "
                                      "no second record and no second %s event" % (rec_id, INCIDENT_CLOSED)))
    return _result(base, OUTCOME_SETTLED, receipt=stored, reason=_report(
        fail, incident.get("id"), "settled: receipt %s written and the %s event appended through the append-only "
                                  "compare-and-swap; %d draft(s) left for a human to promote"
                                  % (rec_id, INCIDENT_CLOSED, len(drafts))))

# --- the in-session self check (a smoke test; the authoritative proof is scripts/selftest.py) ------
def _fixture_incident(iid="INC-1", status=STATUS_DIAGNOSED, **over):
    """The selfcheck's fixture incident (a seeded record, never a live one)."""
    rec = {"schema": _INC.SCHEMA_INCIDENT, "id": iid, "title": "checkout latency regression",
           "signal": "p99 latency rose at the deploy boundary with no error-rate change.",
           "affected_behavior": "The endpoint returns within its latency budget after a charge.",
           "severity": "high", "status": status,
           "timeline": {"opened_at": "2026-07-24T02:14:00Z", "diagnosed_at": "2026-07-24T02:31:00Z"}}
    rec.update(over)
    return rec

def _fixture_remedy():
    """The selfcheck's fixture remedy proposal (valid under the shipped veldo.remedy/v1 contract)."""
    return {"schema": _INC.SCHEMA_REMEDY, "id": "REM-1", "incident": "INC-1", "status": "proposed",
            "diagnosis": "the deploy that crossed the boundary regressed the pool sizing.",
            "evidence": [{"citation": "latency metric series at the deploy boundary"}],
            "proposed_action": {"action": "rollback_deploy",
                                "parameters": {"service": "checkout", "to_release": "prior-known-good"}},
            "risk_class": "standard", "autonomy_level": "L2",
            "reversibility": {"class": "reversible", "data_mutating": "false",
                              "analysis": "a rollback restores the prior release and mutates no data."},
            "rollback": "roll forward to the current release; no data migration is involved.",
            "canary": {"supported": "true", "shape": "route one percent of traffic for five minutes."},
            "required_authorization": "human_confirmation"}

def selfcheck():
    """Drive a fixture incident lifecycle through the reconciliation offline over the fake store and report (exit 0/1).
    No filesystem, no network, no live system; the authoritative proof is the selftest block in scripts/selftest.py."""
    checks = []
    incident, remedy = _fixture_incident(), _fixture_remedy()
    prior = _fixture_incident(iid="INC-0", status=STATUS_CLOSED, title="a differently titled record")
    receipt = {"executed": True, "action": "rollback_deploy", "system": "fake-deploy-controller",
               "parameters": {"service": "checkout", "to_release": "prior-known-good"},
               "proposal_digest": proposal_digest(remedy)}
    validation = {"validated_by": "dmitry", "validated_at": "2026-07-24T02:40:00Z",
                  "bound_remedy": remedy["id"], "bound_digest": diagnosis_digest(incident, remedy)}
    store = FakeReconciliationStore()
    kw = {"remedy": remedy, "prior_incidents": [prior], "validation": validation, "execution_receipt": receipt}

    r1 = reconcile_incident(incident, store, **kw)
    checks.append({"name": "a diagnosed incident with a valid human validation SETTLES once, leaving both drafts and one "
                           "incident.closed event from the contract's own vocabulary",
                   "ok": r1["outcome"] == OUTCOME_SETTLED and store.count() == 1
                   and sorted(d["kind"] for d in r1["drafts"]) == [DRAFT_CRITERIA, DRAFT_RUNBOOK]
                   and [e["type"] for e in store.events()] == [INCIDENT_CLOSED]})
    checks.append({"name": "the recurrence of the same failure signature is reported as a missing specification",
                   "ok": r1["recurrence_of"] == ["INC-0"] and r1["missing_specification"] is True})
    before = store.digest()
    r2 = reconcile_incident(incident, store, **kw)
    checks.append({"name": "a replay is a byte-identical NO-OP with the same receipt id",
                   "ok": r2["outcome"] == OUTCOME_ALREADY and r2["receipt_id"] == r1["receipt_id"]
                   and store.digest() == before and store.count() == 1})
    checks.append({"name": "a settlement with NO human diagnosis validation REFUSES by name",
                   "ok": reconcile_incident(incident, FakeReconciliationStore(), remedy=remedy, validation=None,
                                            execution_receipt=receipt)["refused"] == REFUSE_MISSING_VALIDATION})
    checks.append({"name": "an execution claimed with NO receipt REFUSES by name",
                   "ok": reconcile_incident(incident, FakeReconciliationStore(), remedy=remedy, validation=validation,
                                            execution_claim=True)["refused"] == REFUSE_UNSUPPORTED_EXECUTION_CLAIM})
    swapped = dict(remedy, proposed_action={"action": "drop_customer_table", "parameters": {"table": "customers"}})
    checks.append({"name": "the SAME validation against a SWAPPED remedy REFUSES by name: what the human attested to is "
                           "what the human validated",
                   "ok": reconcile_incident(incident, FakeReconciliationStore(), remedy=swapped, validation=validation,
                                            execution_receipt=None)["refused"] == REFUSE_VALIDATION_DIGEST_MISMATCH})
    checks.append({"name": "a validation that names NO remedy while a remedy exists REFUSES by name",
                   "ok": reconcile_incident(incident, FakeReconciliationStore(), remedy=remedy,
                                            validation={k: v for k, v in validation.items() if k != "bound_remedy"},
                                            execution_receipt=receipt)["refused"] == REFUSE_VALIDATION_UNBOUND_REMEDY})
    passed = all(c["ok"] for c in checks)
    print(json.dumps({"passed": passed, "checks": checks}, indent=2))
    return 0 if passed else 1

def main(argv=None):
    ap = argparse.ArgumentParser(
        description="incident as intent: the compressed loop and reconciliation (a closed incident is a "
                    "settled piece of intent, not a restored service)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selfcheck", help="drive a fixture incident lifecycle through the reconciliation")
    args = ap.parse_args(list(argv) if argv is not None else None)
    if args.cmd == "selfcheck":
        return selfcheck()
    return 2

if __name__ == "__main__":
    sys.exit(main())
