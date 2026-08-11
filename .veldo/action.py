#!/usr/bin/env python3
"""VELDO action whitelist (veldo.action/v1): runbook actions as code, and the whitelist
STORE that admits an action to the machine path only after a recorded, digest-bound
review. This is the W5 organ of PLAN-0012 and the third pillar of Invention #3's design
center: execution is a WHITELIST of pre-vetted, parameterized runbook actions reviewed
like the code they are, and free-form production commands do not exist in the machine
path.

An agent with production access can destroy a company by simply doing the wrong thing
there, so its safety cannot be a policy it follows: it has to be an architecture it
cannot escape. The whitelist is that architecture on the execution side. There is no
general shell, no free-form command, no "just run this" path anywhere. The ONLY thing
the machine can point at is a pre-vetted action reference with validated parameters;
anything else is unresolvable, and an unresolvable action is a human's job by
definition (NG2). This module ships the CONTRACT, the STORE, and the reference trio
against FAKE systems; the EXECUTOR that would run an action is a separate privileged
organ on its own credentials and code path (WARP-1206, W6), NOT built here, and the
two-key rule is WARP-1207 (W7).

  veldo.action/v1 - a pre-vetted, parameterized runbook action. It declares what system
  it acts against (a FAKE system here, NG1), its parameter specs (each with a type and a
  validation constraint), its risk class, its reversibility (class, analysis,
  data_mutating), a rollback plan, whether it supports a canary and its shape, and a
  RECORDED REVIEW. An action is code: it is proposed, reviewed through the normal VELDO
  loop, and only a human promotes it. The review is recorded on the artifact and is bound
  by a digest to the exact content it vetted.

THE DESIGN CENTER this module ENCODES, fail closed (the refusals are the product, C1):

  ANYTHING NOT IN THE WHITELIST DOES NOT EXIST TO THE MACHINE PATH (O2/C4, NG2). An
  action reference is a whitelist KEY, never command text. resolve_action of an unknown
  reference returns None and there is NO free-form fallback: require_action REFUSES by
  name, so the machine can point only at a pre-vetted action and never at a crafted
  command. A present-but-unreviewed action (status proposed) is likewise unresolvable: it
  is not in the effective whitelist, so it does not exist to the machine path either.

  THE STORE REJECTS AN ACTION WITHOUT A RECORDED REVIEW. Every action carries a review
  block, and only an action whose review status is reviewed, whose verdict is approved,
  and whose recorded reviewed_digest still MATCHES the action's current content is
  admitted to the whitelist. An action reviewed and then EDITED is refused (the review is
  STALE: a vetted action cannot be silently changed), the verdict-proof digest binding of
  WARP-0109 applied to a runbook action, so "reviewed" means reviewed EXACTLY THIS.

  A RUNBOOK ACTION CARRIES A HIGH RISK FLOOR, AND NOTHING LOWERS A CLASS (C2). Being in
  the whitelist is an execution path, so an action may not declare a risk class below
  high; a data-mutating or irreversible action carries the critical tier. An action that
  declares a class below its floor is REFUSED (nothing lowers a class; anything may raise
  one).

  PARAMETERS ARE VALIDATED, OUT-OF-RANGE REFUSED BY NAME. An action declares typed
  parameter specs with validation constraints (an enum, a numeric range, a string
  pattern). validate_parameters refuses an unknown parameter, a missing required
  parameter, a wrong type, and a value outside the declared range, enum, or pattern, each
  NAMING the parameter, so a malformed parameter never reaches the executor.

  A PROPOSAL MISSING ANY ELEMENT IS INVALID. A veldo.action/v1 missing its parameter
  specs, risk class, reversibility, rollback plan, or canary declaration is refused at
  contract time.

This module validates the action STRUCTURALLY, the same way .veldo/incident.py and
.veldo/decision.py validate theirs: required fields present, closed vocabularies honored,
an element rejected at record time when it is absent. It reuses the caller's front-matter
parser (validate.parse_yamlish) and failure reporter (validate.fail), so it adds no
second YAML parser and no import cycle. It owns the action artifact's own canonical
digest (action_digest, the way validate.proof_digest is the proof manifest's own digest);
that is not a second parser.

veldo.action/v1 BINDS INTO veldo.remedy/v1 (W1): a remedy's proposed_action is an action
reference plus a parameters mapping, never command text. bind_remedy_action resolves that
reference against the whitelist (unknown or unreviewed refuses, does not exist to the
machine path) and validates the parameters (out of range refuses by name), reusing the
remedy dict W1 already parsed and validated. It RESOLVES and VALIDATES only; it runs
nothing (execution is WARP-1206, W6, which binds the resolved action to a proposal digest
on its own credentials).

Two postures, both shared with the sibling contract organs:
  ADOPTION SAFE. A repository with no .veldo/actions/ directory is untouched: check_actions
  stands down and returns clean, so a repository that never configures the responder is
  byte-identically unaffected. The reference trio ships as illustrative EXAMPLES only; the
  effective whitelist of a fresh repository is empty until a human vets and promotes an
  action.
  FAIL CLOSED. A malformed action, an out-of-vocabulary field, a risk class below the
  floor, a stale review, a duplicate id, an unknown or unreviewed action reference, and an
  out-of-range parameter each REFUSE by name.

Dependency free by construction: pathlib for paths, json and hashlib for the artifact's
own digest, re to compile a declared parameter pattern; it reads no global state and
starts no process, thread, or timer (NG3). The executor (W6) and the two-key rule (W7)
are honestly later items; nothing here runs anything, and this module carries no
execution capability.
"""
from pathlib import Path
import json
import hashlib
import re

SCHEMA_ACTION = "veldo.action/v1"

# The one tier ladder the method uses, ordered low -> critical. A rank compare decides
# whether a declared class sits at or above the action's risk floor.
RISK_CLASSES = ("low", "standard", "high", "critical")
# Reversibility mirrors the decision-record reversal-cost ladder, so "irreversible" means
# the same thing across the method.
REVERSIBILITY_CLASSES = {"reversible", "costly", "irreversible"}
# The parameter type vocabulary. A supplied value is validated against its declared type
# and the type-appropriate constraint (an enum's values, a number's range, a string's
# pattern).
PARAM_TYPES = {"string", "integer", "number", "boolean", "enum"}
# The action review lifecycle: an action is proposed, reviewed through the normal VELDO
# loop, and eventually retired. Only a reviewed (and approved, digest-current) action is
# admitted to the effective whitelist.
REVIEW_STATUSES = {"proposed", "reviewed", "retired"}
REVIEW_VERDICTS = {"approved", "rejected"}

# The whitelist carries a HIGH risk floor (C2): being pre-vetted for execution is itself a
# high-risk fact. A data-mutating or irreversible action carries the critical tier. Nothing
# may lower a class; anything may raise one.
WHITELIST_RISK_FLOOR = "high"


class ActionContractError(ValueError):
    """A veldo.action/v1 record is malformed. Raised by name so a bad action never
    silently no-ops (parallels IncidentContractError and DecisionRecordError)."""


def default_actions_dir(root=None):
    return Path(root or ".") / ".veldo" / "actions"


def _is_str(v):
    return isinstance(v, str) and v.strip() != ""


def _as_list(v):
    return v if isinstance(v, list) else []


def _as_bool(v):
    """The value as a real boolean, or None when it is neither. The one front-matter
    parser leaves an unquoted true/false as the string "true"/"false" (it coerces only
    integers), so a boolean contract field arrives as that string; this accepts the string
    forms and a real bool and refuses anything else, so a truthy-looking value like "yes"
    or 1 is not silently accepted (the same idiom incident.py and evidence.py use)."""
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        s = v.strip().lower()
        if s == "true":
            return True
        if s == "false":
            return False
    return None


def _as_number(v):
    """The value as an int or float, or None when it is neither. A real bool is NOT a
    number here (the parser never coerces a bool to int, and treating True as 1 would let
    a boolean satisfy a numeric range silently)."""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v
    return None


def _risk_rank(word):
    try:
        return RISK_CLASSES.index(word)
    except ValueError:
        return -1


def action_digest(data):
    """The stable digest of an action's REVIEWABLE substance: everything that defines what
    the action does and its safety envelope, EXCLUDING the review block itself (a review
    cannot cover its own record). The recorded review binds to this digest, so an action
    edited after review no longer matches and is refused as stale. This is the action
    artifact's OWN canonical digest, the way validate.proof_digest is the proof manifest's;
    it is one digest for one artifact type, not a second parser."""
    payload = {k: v for k, v in data.items() if k != "review"}
    blob = json.dumps(payload, sort_keys=True, default=str)
    return "sha256:" + hashlib.sha256(blob.encode()).hexdigest()[:16]


def _load(path, parse):
    p = Path(path)
    try:
        text = p.read_text()
    except OSError as e:
        raise ActionContractError("action record unreadable: %s" % e)
    try:
        data = parse(text)
    except ValueError as e:
        raise ActionContractError("action record outside the record subset: %s" % e)
    if not isinstance(data, dict):
        raise ActionContractError("action record must be a mapping at the top level")
    return data


def load_action(path, parse):
    """Parse an action through the caller's front-matter parser (the VELDO yamlish subset).
    The single place an action is read, so the store and the executor (W6) reuse it."""
    return _load(path, parse)


def risk_floor(data):
    """The minimum risk class this action may declare. The whitelist floor is high (C2);
    a data-mutating or irreversible action carries the critical tier. Returns a class from
    RISK_CLASSES. Nothing may lower the class this returns; anything may raise it."""
    rev = data.get("reversibility")
    if isinstance(rev, dict):
        if _as_bool(rev.get("data_mutating")) is True or rev.get("class") == "irreversible":
            return "critical"
    return WHITELIST_RISK_FLOOR


def _validate_parameter_spec(p, i, fail, where):
    """Structural validation of ONE declared parameter spec: a name, a type from the
    vocabulary, a required flag, and the type-appropriate constraint (an enum's values, a
    numeric range that is not inverted, a string pattern that compiles). Returns the error
    count. A malformed parameter spec is a malformed action (fail closed)."""
    errs = 0
    if not isinstance(p, dict):
        return fail(where, "parameter %d is not a mapping (each parameter declares a name, type, required, and its constraint)" % i)
    pname = p.get("name")
    if not _is_str(pname):
        errs += fail(where, "parameter %d has no name (a parameter spec names the parameter it validates)" % i)
    ptype = p.get("type")
    if ptype not in PARAM_TYPES:
        errs += fail(where, "parameter %r type must be one of %s (got %r)" % (pname, sorted(PARAM_TYPES), ptype))
    if _as_bool(p.get("required")) is None:
        errs += fail(where, "parameter %r required is required and must be true or false" % pname)
    if ptype == "enum":
        vals = _as_list(p.get("values"))
        if not vals:
            errs += fail(where, "parameter %r is an enum and must declare a non-empty values list (the allowed values)" % pname)
    if ptype in ("integer", "number"):
        mn, mx = _as_number(p.get("min")), _as_number(p.get("max"))
        if p.get("min") is not None and mn is None:
            errs += fail(where, "parameter %r min must be a number" % pname)
        if p.get("max") is not None and mx is None:
            errs += fail(where, "parameter %r max must be a number" % pname)
        if mn is not None and mx is not None and mn > mx:
            errs += fail(where, "parameter %r declares min %r greater than max %r (an inverted range validates nothing)" % (pname, mn, mx))
    if "pattern" in p:
        try:
            re.compile(str(p.get("pattern")))
        except re.error as e:
            errs += fail(where, "parameter %r pattern does not compile: %s" % (pname, e))
    return errs


def validate_action(data, root, record_path, fail):
    """Structural and risk-floor validation of one parsed veldo.action/v1 record. Reports
    each problem through fail(name, msg) and returns the error count. Pure over the dict,
    so the directory scan and the single-file entry point reuse it.

    This does NOT check whether the recorded review is CURRENT (that the reviewed_digest
    still covers the content); a well-formed record and a current review are separate
    concerns, and the currency check is the store's admission concern (review_stale /
    check_action / build_whitelist), so validate_action stays a pure structural check like
    its siblings."""
    errs = 0
    name = str(record_path)

    if data.get("schema") != SCHEMA_ACTION:
        errs += fail(name, "schema must be %r (got %r)" % (SCHEMA_ACTION, data.get("schema")))
    for field in ("id", "title", "system"):
        if not _is_str(data.get(field)):
            errs += fail(name, "missing or empty required field: %s (an action names its id, a human-readable title, and the system it acts against)" % field)

    risk = data.get("risk_class")
    if risk not in RISK_CLASSES:
        errs += fail(name, "risk_class must be one of %s (got %r): an action names its risk class" % (list(RISK_CLASSES), risk))

    # REVERSIBILITY: the class, a stated analysis, and whether the action mutates data.
    # These decide the risk floor below.
    rev = data.get("reversibility")
    if not isinstance(rev, dict):
        errs += fail(name, "reversibility is required: a mapping with a class, an analysis, and data_mutating")
    else:
        if rev.get("class") not in REVERSIBILITY_CLASSES:
            errs += fail(name, "reversibility.class must be one of %s (got %r)" % (sorted(REVERSIBILITY_CLASSES), rev.get("class")))
        if not _is_str(rev.get("analysis")):
            errs += fail(name, "reversibility.analysis is required (why the action is or is not reversible)")
        if _as_bool(rev.get("data_mutating")) is None:
            errs += fail(name, "reversibility.data_mutating is required and must be true or false")

    # PARAMETER SPECS: a list (possibly empty for a parameterless action), each a valid spec.
    params = data.get("parameters")
    if not isinstance(params, list):
        errs += fail(name, "parameters is required: a list of parameter specs (each with a name, a type, required, and its validation constraint); an action with no parameters declares an empty list")
    else:
        seen = set()
        for i, p in enumerate(params):
            errs += _validate_parameter_spec(p, i, fail, name)
            if isinstance(p, dict) and _is_str(p.get("name")):
                if p["name"] in seen:
                    errs += fail(name, "duplicate parameter name %r (a parameter is validated once)" % p["name"])
                seen.add(p["name"])

    # ROLLBACK PLAN (a safety omission that fails closed): an action that does not say how
    # to undo itself is invalid.
    if not _is_str(data.get("rollback")):
        errs += fail(name, "rollback is required: an action that omits its rollback plan is invalid (fail closed)")

    # CANARY SUPPORT: whether the action runs a canary first and, if so, its shape.
    canary = data.get("canary")
    if not isinstance(canary, dict):
        errs += fail(name, "canary is required: a mapping declaring whether the action supports a canary first (supported) and its shape")
    else:
        supported = _as_bool(canary.get("supported"))
        if supported is None:
            errs += fail(name, "canary.supported is required and must be true or false")
        if supported is True and not _is_str(canary.get("shape")):
            errs += fail(name, "canary.shape is required when canary.supported is true (what the canary runs first)")

    # THE RECORDED REVIEW: every action carries one. An action is code; it is reviewed
    # through the normal VELDO loop before it can be trusted. A reviewed action must name its
    # reviewer, an approving verdict, when it was reviewed, and the digest of what was
    # reviewed. A reviewed action whose verdict is not approved is a contradiction (a
    # rejected review does not vet the action) and is refused.
    review = data.get("review")
    if not isinstance(review, dict):
        errs += fail(name, "review is required: every action carries a recorded review (an action is code, reviewed through the normal VELDO loop); a proposed action declares review.status proposed")
    else:
        rstatus = review.get("status")
        if rstatus not in REVIEW_STATUSES:
            errs += fail(name, "review.status must be one of %s (got %r)" % (sorted(REVIEW_STATUSES), rstatus))
        if rstatus == "reviewed":
            if not _is_str(review.get("reviewer")):
                errs += fail(name, "a reviewed action requires review.reviewer (who vetted it)")
            if review.get("verdict") not in REVIEW_VERDICTS:
                errs += fail(name, "a reviewed action requires review.verdict, one of %s (got %r)" % (sorted(REVIEW_VERDICTS), review.get("verdict")))
            elif review.get("verdict") != "approved":
                errs += fail(name, "review.status reviewed with verdict %r is a contradiction: a rejected review does not vet the action (it may not enter the whitelist)" % review.get("verdict"))
            if not _is_str(review.get("reviewed_at")):
                errs += fail(name, "a reviewed action requires review.reviewed_at (when it was reviewed)")
            if not _is_str(review.get("reviewed_digest")):
                errs += fail(name, "a reviewed action requires review.reviewed_digest binding the review to the content it vetted (an action cannot be silently edited after review)")

    # THE RISK FLOOR (C2): nothing lowers a class. An action that declares a class below its
    # floor is refused; declaring a higher class is always allowed.
    if risk in RISK_CLASSES:
        floor = risk_floor(data)
        if _risk_rank(risk) < _risk_rank(floor):
            errs += fail(name, "risk_class %r is below the floor %r for this action: the whitelist carries a high risk floor and a data-mutating or irreversible action carries critical (C2, anything may raise a risk class, nothing may lower it)" % (risk, floor))

    return errs


def review_stale(data):
    """True iff the action claims a COMPLETED review but its current content no longer
    matches the recorded reviewed_digest: a vetted action was edited after review. This
    FAILS CLOSED (a whitelisted action cannot be silently changed), distinct from a proposed
    action that was simply never reviewed. Pure over the dict."""
    review = data.get("review")
    if not isinstance(review, dict) or review.get("status") != "reviewed":
        return False
    rd = review.get("reviewed_digest")
    return _is_str(rd) and rd != action_digest(data)


def action_reviewed(data):
    """True iff the action is admitted to the effective whitelist: its review status is
    reviewed, its verdict is approved, and its recorded reviewed_digest STILL matches the
    action's current content. A proposed or retired action, a non-approving verdict, or a
    stale digest is NOT admitted, so an unreviewed or edited action does not exist to the
    machine path. Pure over the dict."""
    review = data.get("review")
    if not isinstance(review, dict):
        return False
    if review.get("status") != "reviewed" or review.get("verdict") != "approved":
        return False
    rd = review.get("reviewed_digest")
    return _is_str(rd) and rd == action_digest(data)


def check_action(path, root, required, parse, fail):
    """Single-file entry point for an action record. Absent file: stand down (adoption
    safe) unless required, then fail closed. Present: parse, validate structurally, and
    fail closed on a STALE review (a reviewed action whose content changed)."""
    p = Path(path)
    if not p.is_file():
        if required:
            return fail(str(p), "action record is referenced as required but absent (fail closed)")
        return 0
    try:
        data = load_action(p, parse)
    except ActionContractError as e:
        return fail(str(p), str(e))
    errs = validate_action(data, root, p, fail)
    if review_stale(data):
        errs += fail(str(p), "review is STALE: the action content changed after it was reviewed (review.reviewed_digest no longer matches); a vetted action cannot be silently edited (re-review it, WARP-0109 digest binding)")
    return errs


def _scan_ids(actions_dir, parse):
    """id -> [filenames] for every parseable veldo.action/v1 record in actions_dir."""
    ids = {}
    for p in sorted(Path(actions_dir).glob("*.yaml")):
        try:
            data = load_action(p, parse)
        except ActionContractError:
            continue  # already reported by the per-file check
        if isinstance(data, dict) and data.get("schema") == SCHEMA_ACTION and _is_str(data.get("id")):
            ids.setdefault(data["id"], []).append(p.name)
    return ids


def check_actions(actions_dir, root, parse, fail):
    """The gate entry point over the per-repo action records. Adoption safe: with no
    .veldo/actions/ directory this stands down and returns clean, so a repository that never
    configures the responder is byte-identically unaffected. Present records each fail
    closed on anything malformed or a stale review; a duplicate id is refused (an ambiguous
    reference in the whitelist)."""
    d = Path(actions_dir)
    if not d.is_dir():
        return 0
    errs = 0
    for p in sorted(d.glob("*.yaml")):
        errs += check_action(p, root, False, parse, fail)
    for aid, files in sorted(_scan_ids(d, parse).items()):
        if len(files) > 1:
            errs += fail(str(d), "duplicate action id %r across records: %s (a whitelist reference must resolve to exactly one action)" % (aid, ", ".join(sorted(files))))
    return errs


def build_whitelist(actions_dir, parse, fail):
    """The effective whitelist: a mapping {action id -> action} of every VALID, REVIEWED,
    APPROVED, digest-current action under actions_dir, plus the error count. A proposed or
    retired action is a valid record but is NOT admitted (it does not exist to the machine
    path). A malformed or stale-review action fails closed and is not admitted. A duplicate
    admitted id is refused (an ambiguous reference). Adoption safe: no directory yields an
    empty whitelist and no error."""
    whitelist, errs = {}, 0
    d = Path(actions_dir)
    if not d.is_dir():
        return whitelist, errs
    for p in sorted(d.glob("*.yaml")):
        try:
            data = load_action(p, parse)
        except ActionContractError as e:
            errs += fail(str(p), str(e))
            continue
        if validate_action(data, str(d), p, fail) != 0:
            continue
        if review_stale(data):
            errs += fail(str(p), "review is STALE: the action content changed after it was reviewed; it is not admitted to the whitelist")
            continue
        if not action_reviewed(data):
            continue  # a valid draft (proposed/retired): not admitted, but not an error
        aid = data["id"]
        if aid in whitelist:
            errs += fail(str(p), "duplicate admitted action id %r (a whitelist reference must resolve to exactly one action)" % aid)
            continue
        whitelist[aid] = data
    return whitelist, errs


def resolve_action(ref, whitelist):
    """The action the reference names, or None. The load-bearing C4/NG2 property: the
    reference is a whitelist KEY, never command text, and there is NO free-form fallback,
    so anything not in the whitelist resolves to None and does not exist to the machine
    path. A non-string reference is unresolvable."""
    if not _is_str(ref):
        return None
    return whitelist.get(ref)


def require_action(ref, whitelist, fail, where):
    """Resolve the reference or FAIL CLOSED by name. Returns (action, errs): (action, 0) on
    a hit, (None, 1) when the reference is not in the whitelist (unknown, or present but
    unreviewed, either way not admitted). This is the fail-closed seam the executor (W6)
    calls before it may bind an action to a proposal digest; an unresolvable reference is a
    human's job by definition (NG2)."""
    action = resolve_action(ref, whitelist)
    if action is None:
        return None, fail(where, "action %r is not in the whitelist: it does not exist to the machine path (C4/NG2, there is no free-form execution path; an unknown or unreviewed action is unresolvable, never interpreted as command text)" % ref)
    return action, 0


def _check_value(spec, value, fail, where):
    """Validate one SUPPLIED value against its declared parameter spec, refusing by name on
    a wrong type or a value outside the declared range, enum, or pattern. Returns the error
    count."""
    pname, ptype = spec.get("name"), spec.get("type")
    if ptype == "enum":
        vals = _as_list(spec.get("values"))
        if value not in vals:
            return fail(where, "parameter %r value %r is not in the allowed set %r (out-of-enum, refused)" % (pname, value, vals))
        return 0
    if ptype == "boolean":
        if _as_bool(value) is None:
            return fail(where, "parameter %r must be a boolean (got %r)" % (pname, value))
        return 0
    if ptype in ("integer", "number"):
        num = _as_number(value)
        if num is None or (ptype == "integer" and not isinstance(value, int)):
            return fail(where, "parameter %r must be %s (got %r)" % (pname, ptype, value))
        errs = 0
        mn, mx = _as_number(spec.get("min")), _as_number(spec.get("max"))
        if mn is not None and num < mn:
            errs += fail(where, "parameter %r value %r is below the declared minimum %r (out-of-range, refused)" % (pname, num, mn))
        if mx is not None and num > mx:
            errs += fail(where, "parameter %r value %r is above the declared maximum %r (out-of-range, refused)" % (pname, num, mx))
        return errs
    # string (the default typed value)
    if not isinstance(value, str):
        return fail(where, "parameter %r must be a string (got %r)" % (pname, value))
    errs = 0
    pat = spec.get("pattern")
    if _is_str(pat) and not re.fullmatch(str(pat), value):
        errs += fail(where, "parameter %r value %r does not match the declared pattern %r (invalid, refused)" % (pname, value, pat))
    ml = _as_number(spec.get("max_length"))
    if ml is not None and len(value) > ml:
        errs += fail(where, "parameter %r value is longer than the declared max_length %r (invalid, refused)" % (pname, ml))
    return errs


def validate_parameters(action, params, fail, where):
    """Validate the SUPPLIED parameters against the action's declared parameter specs,
    refusing by name: an unknown parameter (not declared by the action), a missing required
    parameter, a wrong type, and a value outside the declared range, enum, or pattern.
    Returns the error count. This is what the executor (W6) runs to refuse a bad parameter
    before it ever binds the action; the refusal is the product (C1)."""
    if not isinstance(params, dict):
        return fail(where, "parameters must be a mapping of the action's declared parameters")
    specs = {}
    for p in _as_list(action.get("parameters")):
        if isinstance(p, dict) and _is_str(p.get("name")):
            specs[p["name"]] = p
    errs = 0
    for k in params:
        if k not in specs:
            errs += fail(where, "unknown parameter %r: the action %r declares no such parameter (only declared parameters are accepted)" % (k, action.get("id")))
    for pname, spec in specs.items():
        required = _as_bool(spec.get("required")) is True
        if pname not in params:
            if required:
                errs += fail(where, "missing required parameter %r for action %r" % (pname, action.get("id")))
            continue
        errs += _check_value(spec, params[pname], fail, where)
    return errs


def bind_remedy_action(remedy, whitelist, fail, where):
    """The seam veldo.action/v1 binds into veldo.remedy/v1 (W1). A remedy's proposed_action is
    an action REFERENCE plus a parameters mapping (W1 validates its shape; it never carries
    command text). This resolves that reference against the whitelist (unknown or unreviewed
    refuses, does not exist to the machine path) and validates the supplied parameters
    (out-of-range refuses by name). It reuses the remedy dict W1 already parsed and
    validated - no second parser. Returns the error count. It RESOLVES and VALIDATES only;
    it runs NOTHING (execution is the separate organ WARP-1206 W6, which binds the resolved
    action to the proposal digest on its own credentials)."""
    pa = remedy.get("proposed_action")
    if not isinstance(pa, dict):
        return fail(where, "remedy has no proposed_action mapping to bind (a proposal names a whitelist action and its parameters)")
    action, errs = require_action(pa.get("action"), whitelist, fail, where)
    if action is None:
        return errs
    errs += validate_parameters(action, pa.get("parameters") or {}, fail, where)
    return errs


def _cli(argv):
    """Standalone runner: validate a repository's action records (or a single file) and
    print the effective whitelist, reusing validate.py's ONE front-matter parser and
    failure reporter, so there is no second YAML parser. This mirrors how validate.py
    invokes the sibling contract validators; wiring this into validate.py run_all is
    WARP-1211 (W11, land the checks in the canonical engine)."""
    import importlib.util
    here = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location("veldo_validate", here / "validate.py")
    V = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(V)
    root = here.parent
    arg = argv[1] if len(argv) > 1 else None
    if arg and Path(arg).is_file():
        errs = check_action(arg, root, False, V.parse_yamlish, V.fail)
        if errs:
            print("veldo action contract: %d problem(s)" % errs)
            return 1
        print("veldo action contract: clean")
        return 0
    actions_dir = default_actions_dir(root)
    errs = check_actions(actions_dir, root, V.parse_yamlish, V.fail)
    whitelist, werrs = build_whitelist(actions_dir, V.parse_yamlish, V.fail)
    errs += werrs
    if errs:
        print("veldo action whitelist: %d problem(s)" % errs)
        return 1
    if whitelist:
        print("veldo action whitelist: %d admitted action(s): %s" % (len(whitelist), ", ".join(sorted(whitelist))))
    else:
        print("veldo action whitelist: clean (no .veldo/actions/ configured; adoption safe stand-down)")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_cli(sys.argv))
