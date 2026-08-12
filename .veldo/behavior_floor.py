#!/usr/bin/env python3
"""VELDO behaviour floor (veldo.behavior_floor/v1): an existing codebase's CURRENT
behaviour as a recorded artifact the machine may draft and may NEVER rule on.

This is the ROOT of the legacy on-ramp (VELDO-0012) and only the root. Every real
adopter has an existing codebase, and the shipped method had no answer for one: the
pilot path and the adoption sequence both write specifications and turn on a gate
against a codebase whose behaviour nobody has written down. The book promises that a
change to legacy code BEGINS by pinning what the code does today and that the spec is
then written against that pinned floor. This module is the artifact that promise needs.

THE HARD PART, STATED RATHER THAN ROUTED AROUND. A characterization test pins current
behaviour INCLUDING current bugs, so pinning is not the deliverable. The deliverable is
a record of which pinned behaviour is LOAD BEARING, which is merely present, and which
is a defect somebody has now seen. That is a human judgement, because the question is
not what the code does (a machine reads that better than a person) but whether what it
does is what it SHOULD do. Three answers were available and two are wrong: reviewing
every pin is a survey of an estate, and letting the machine classify puts a GUESS in the
record, which is worse than no record because the guess becomes authoritative.

So the design, and each half is enforced here rather than asked for in prose:

  THE ONLY STATUS A MACHINE MAY WRITE IS unknown. STATUSES has exactly ONE member. A
  pin declaring load_bearing is refused by PIN_VOCAB_UNKNOWN, so a drafting pass cannot
  express a conclusion at all - not "should not", CANNOT.

  NO RULING AND NO EXEMPTION IS REPRESENTABLE IN THE FLOOR. Every key set is CLOSED (the
  floor, its scope block, each pin, each observation), so decided_by, decided_at, reason,
  disposition, waived and exempt are structurally unwriteable, and no key addresses a
  LOCATION: there is no path, glob, module or pattern scoped exemption, because a path
  exemption exempts a location forever and the load-bearing behaviour that appears there
  next year is invisible. That is the mechanism .veldo/secret_inventory.py:139-144
  already refuses for secrets and this contract does not reintroduce under a friendlier
  name. The refusal is in the SCHEMA because prose instructions do not execute: the floor
  is a file the agent under the gate can open, so the only real answer is that there is
  nowhere in it for a ruling to go.

  THE RULING ARRIVES THROUGH THE ONE CHANNEL THIS REPOSITORY HAS FOR HUMAN DECISIONS.
  plans/PLAN-0016-human-decisions-through-jira.md is approved at risk critical and its O6
  says NO decision is ever captured outside the ticket channel, there is no manual
  hand-advancement of a record, and an unsupported decision kind BLOCKS rather than
  bypassing. So this module invents NO decision kind and NO ruling field. A ruling is a
  decision_choice touchpoint (.veldo/request.py:74-77) whose settlement the receipt path
  writes to .veldo/settlements/ (.veldo/request_reconcile.py:353-390), and disposition_for
  resolves one ONLY from a settlement whose bound_digest equals the RECOMPUTED observation
  digest AND whose request_id resolves to an accepted veldo.request/v1 record. A
  hand-written settlement with no accepted request behind it rules NOTHING.

  THE JOIN IS A DIGEST THE VALIDATOR RECOMPUTES, NEVER ONE IT TRUSTS. This is the
  load-bearing property of the whole item. observation_digest is derived from the pin's
  own recorded observation over ONE canonical serialization (the discipline
  .veldo/request.py:126-136 uses for request_digest over the declared field tuple at
  .veldo/request.py:113-114: a sorted-keys JSON blob and one hash, no second spelling),
  and a declared digest that does not equal it refuses by DIGEST_MISMATCH. The reason is
  adversarial rather than tidy: the digest is the ONLY join between a human's ruling and a
  behaviour, so a digest that is merely TYPED is a writable pointer at somebody else's
  judgement, and re-pointing it at a different observation is exactly how an agent grants
  itself a ruling it was never given. There is ONE canonicalization function and both the
  validator and the disposition read call it, so the two can never disagree.

WHAT THE CHANNEL CANNOT CARRY YET, AND WHY THAT BLOCKS RATHER THAN DEFAULTS. A pin ruling
is a THREE-way choice, and the inbound edge derives only accept or reject from board
states (.veldo/request_reconcile.py:104-107); its settlement carries decision, decided_by
and bound_digest and NEVER the chosen option (.veldo/request_reconcile.py:247-256), while
a decided veldo.decision/v1 requires a chosen option that resolves
(.veldo/decision.py:183-190). So today a human can settle a decision on a pin's
observation and the repository cannot learn WHICH way they ruled. That state is BLOCKED
with RULING_NOT_CARRIED: never a ruling, never a default, and never quietly back to
unknown as if nobody had decided anything. RULING_NOT_SETTLED and RULING_NOT_CARRIED must
never collapse into one name - the first means nobody has ruled and the second means the
channel is incomplete, and the fix is a different person's job in each case. The option
carrier is a PLAN-0016 work item because it is PLAN-0016's edge, and it is deliberately
not invented here.

THE LANGUAGE SCOPE, DECLARED RATHER THAN IMPLIED. The shipped shape analyzers are PYTHON
ONLY: .veldo/shape_gate.py:174-181 filters the changed set to paths ending .py before any
analyzer sees them. So a floor over a Java, Kotlin, Rust or SQL surface gets no help from
the shipped analyzers, its reproduces reference points at a test in the ADOPTING
repository's own framework, and its language field plus the scope block's unreachable list
is how the artifact says so. ANALYZER_LANGUAGES records that scope and analyzer_supported
reports it per pin; nothing here claims a floor over a surface it cannot enumerate, and
nothing here REFUSES a pin for its language either, because refusing one would be this
module pretending the shipped analyzers are the only way to characterize behaviour.

TWO POSTURES, both shared with the decision and request organs this mirrors:
  ADOPTION SAFE, AND IT ENFORCES NOTHING. An absent .veldo/floors/ directory stands the
  whole check down and returns clean, exactly as .veldo/decision.py:219-227 does for
  decision records, so a repository with no floors is byte-identically unaffected. NO
  CHANGE IS REFUSED BECAUSE A PIN IS unknown OR blocked: the artifact is inert data, no
  gate stage calls disposition_for, and the precondition at ready and at claim is a later
  item. The stand-down is RECORDED with its reason (floor_standdowns) rather than printed,
  because the gate check must leave validate.run_all's output byte-identical over a
  repository with no floors; the report is where a reader SEES which condition stood it
  down, and a stand-down is never a silent pass.
  FAIL CLOSED. The moment a floor exists, anything malformed refuses by NAME: an
  unreadable floor, a missing pin field, an out-of-vocabulary status or fidelity, an
  unrecognized key (the shape an inline ruling would take), a declared digest that is not
  the recomputed one, a duplicate pin id across the set, or a scope block that does not
  say what the pass could not reach.

Dependency free by construction: the caller (.veldo/validate_checks.py) passes in the
front-matter parser and the failure reporter it already owns, so this module adds no
second YAML parser and no import cycle. This module WRITES NOTHING and reads no clock.
"""
import hashlib
import json
from pathlib import Path

SCHEMA = "veldo.behavior_floor/v1"

# THE ONLY STATUS A MACHINE MAY WRITE. Exactly one member, deliberately: a drafting pass
# records an observation and cannot express a conclusion about it. Widening this set is
# how this contract's central property would be lost, which is why the suite's AC1
# falsification is exactly that widening.
STATUSES = {"unknown"}

# How faithfully a pin reproduces the behaviour. Much of a real estate cannot be pinned
# exactly (a timestamp, an ordering, a production-only path), so BOTH answers are
# representable and the contract is stable either way. Whether a proxy pin may ever be the
# guard that blocks a change is a later item's decision, not this one's.
FIDELITIES = {"exact", "proxy"}

# The three rulings a HUMAN may choose among. NOT a status vocabulary and never writeable
# into a floor: these are the OPTIONS of a decision_choice touchpoint, resolved from the
# settled decision, and they appear here only so disposition_for can recognise one when the
# channel finally carries it. No fourth decision kind is invented (PLAN-0016 O6).
RULINGS = {"load_bearing", "incidental", "defect"}

# What a READ of a pin can conclude. Three states, and the reader is told which - because
# "unknown" and "a human ruled and the channel could not carry which way" are different
# facts and a reader who cannot tell them apart will assume the first.
DISPOSITION_RULED = "ruled"
DISPOSITION_UNKNOWN = "unknown"
DISPOSITION_BLOCKED = "blocked"
DISPOSITIONS = {DISPOSITION_RULED, DISPOSITION_UNKNOWN, DISPOSITION_BLOCKED}

# THE CLOSED KEY SETS. This is AC3, and it is the whole of AC3: an unrecognized key is
# REFUSED rather than ignored at every level of the artifact, which makes decided_by,
# decided_at, reason, disposition, waived and exempt structurally unwriteable inside a
# floor, and makes a path/glob/module/pattern scoped exemption unrepresentable because no
# key addresses a LOCATION anywhere in these four sets.
FLOOR_KEYS = {"schema", "id", "version", "area", "scope", "pins"}
SCOPE_KEYS = {"method", "enumerated", "unreachable"}
PIN_KEYS = {"id", "surface", "language", "fidelity", "observation", "reproduces", "status"}
OBSERVATION_KEYS = {"recorded", "digest"}
PIN_REQUIRED = ("id", "surface", "language", "fidelity", "reproduces", "status")

# The declared field tuple the ONE canonical digest is taken over, the same discipline
# request.DIGEST_FIELDS declares for request_digest. The SURFACE is in the tuple on
# purpose: without it two pins recording a byte-identical observation on two different
# surfaces would share a digest, and one human's judgement about one of them would
# silently rule the other - which is the exact transfer this join exists to prevent.
OBSERVATION_DIGEST_FIELDS = ("surface", "recorded")

# The languages the SHIPPED analyzers cover, declared rather than implied
# (.veldo/shape_gate.py filters the changed set to .py before any analyzer runs). A pin in
# another language is legitimate and is NOT refused; it simply gets no help from them, and
# saying so is the artifact's job.
ANALYZER_LANGUAGES = ("python",)

# --- the error taxonomy: named, distinguishable causes, never one undifferentiated refusal
FLOOR_UNREADABLE = "FLOOR_UNREADABLE"
PIN_FIELD_MISSING = "PIN_FIELD_MISSING"
PIN_VOCAB_UNKNOWN = "PIN_VOCAB_UNKNOWN"
PIN_KEY_UNRECOGNIZED = "PIN_KEY_UNRECOGNIZED"
DIGEST_MISMATCH = "DIGEST_MISMATCH"
DUPLICATE_PIN_ID = "DUPLICATE_PIN_ID"
SCOPE_MISSING = "SCOPE_MISSING"
# The two DISPOSITION reasons. Not refusals: a read reports them, no change is refused for
# either, and they must never collapse into one name.
RULING_NOT_SETTLED = "RULING_NOT_SETTLED"
RULING_NOT_CARRIED = "RULING_NOT_CARRIED"

CAUSES = {FLOOR_UNREADABLE, PIN_FIELD_MISSING, PIN_VOCAB_UNKNOWN, PIN_KEY_UNRECOGNIZED,
          DIGEST_MISMATCH, DUPLICATE_PIN_ID, SCOPE_MISSING,
          RULING_NOT_SETTLED, RULING_NOT_CARRIED}

# The settlement shape a ruling must arrive in, read from the records PLAN-0016's receipt
# path already writes (.veldo/request_reconcile.py:96-107 and :247-259). Named here so the
# resolver reads the SHIPPED vocabulary rather than a second spelling of it.
SETTLEMENT_SCHEMA = "veldo.decision/v1"
SETTLEMENT_DECIDED = "decided"
REQUEST_SCHEMA = "veldo.request/v1"
REQUEST_TOUCHPOINT = "decision_choice"
REQUEST_ACCEPTED = "accepted"

# The stand-down REGISTRY: which floors the check stood down for and why, recorded rather
# than printed, so the gate check leaves run_all's output byte-identical while a reader can
# still tell a floor that was CHECKED from one the rule never asked anything of. Mirrors
# validate_checks.FALSIFICATION_STANDDOWNS. A caller clears it with
# `del FLOOR_STANDDOWNS[:]`.
FLOOR_STANDDOWNS = []


class FloorRecordError(ValueError):
    """A floor record is malformed. Raised by name so a bad floor never silently no-ops
    (parallels DecisionRecordError, RequestRecordError and ArchContractError)."""


def default_floors_dir(root=None):
    return Path(root or ".") / ".veldo" / "floors"


def default_settlements_dir(root=None):
    """Where the PLAN-0016 receipt path writes a settlement
    (.veldo/request_reconcile.py:379-383). Read-only from here, always."""
    return Path(root or ".") / ".veldo" / "settlements"


def default_requests_dir(root=None):
    return Path(root or ".") / ".veldo" / "requests"


def _standdown(where, why):
    FLOOR_STANDDOWNS.append((str(where), why))
    return 0


def floor_standdowns():
    """Every recorded stand-down as (path, reason), in the order recorded."""
    return tuple(FLOOR_STANDDOWNS)


def _is_str(v):
    return isinstance(v, str) and v.strip() != ""


def _as_list(v):
    return v if isinstance(v, list) else []


def _is_pos_int(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 1


def analyzer_supported(language):
    """Whether the SHIPPED analyzers cover a pin's language. False is not a defect and
    refuses nothing; it is the fact the scope block's unreachable list exists to carry."""
    return isinstance(language, str) and language.strip().lower() in ANALYZER_LANGUAGES


def _digest_payload(pin):
    """The canonical payload of ONE observation, over the declared field tuple. One
    spelling, read by the validator and by the disposition read alike."""
    obs = pin.get("observation") if isinstance(pin, dict) else None
    src = {"surface": pin.get("surface") if isinstance(pin, dict) else None,
           "recorded": obs.get("recorded") if isinstance(obs, dict) else None}
    return {k: src.get(k) for k in OBSERVATION_DIGEST_FIELDS}


def observation_digest(pin):
    """THE ONE canonical digest of the observation a pin records: a sorted-keys JSON blob
    over OBSERVATION_DIGEST_FIELDS and one hash, the same discipline request.request_digest
    uses. DERIVED, never read from the file.

    This is the only join between a human's ruling and a behaviour. Mutating the recorded
    observation changes the digest, so the settlement that ruled the old one stops matching
    and the pin falls back to unknown - which is what makes a granted ruling immovable onto
    a behaviour nobody looked at."""
    blob = json.dumps(_digest_payload(pin), sort_keys=True, default=str)
    return "sha256:" + hashlib.sha256(blob.encode()).hexdigest()[:16]


def load_floor(path, parse):
    """Parse the floor at path into a dict using the caller's front-matter parser (the
    VELDO yamlish subset), raising FloorRecordError on unreadable or unparseable input. The
    single place a floor is read, so the report and the drafting pass reuse it rather than
    parsing the file a second way."""
    p = Path(path)
    try:
        text = p.read_text()
    except OSError as e:
        raise FloorRecordError("%s: floor unreadable: %s" % (FLOOR_UNREADABLE, e))
    try:
        data = parse(text)
    except ValueError as e:
        raise FloorRecordError("%s: floor outside the record subset: %s" % (FLOOR_UNREADABLE, e))
    if not isinstance(data, dict):
        raise FloorRecordError("%s: a floor must be a mapping at the top level" % FLOOR_UNREADABLE)
    return data


def _unknown_keys(mapping, allowed, subject, name, fail):
    """Refuse every unrecognized key by name. THIS is where an inline ruling or a
    path-scoped exemption would have to live, so there is nowhere for one to go."""
    errs = 0
    for key in sorted(k for k in mapping if k not in allowed):
        errs += fail(name, "%s: %s carries the unrecognized key %r - the key set is CLOSED, so "
                           "no ruling, disposition, reason, waiver or path-scoped exemption is "
                           "representable in a floor at all (allowed: %s)"
                     % (PIN_KEY_UNRECOGNIZED, subject, key, sorted(allowed)))
    return errs


def _validate_scope(scope, pins, name, fail):
    """The scope block: which surfaces the drafting pass ENUMERATED, by what METHOD, and
    which it COULD NOT REACH. A floor with pins and no scope block is refused, because a
    floor that does not say what it did not look at is a coverage claim wearing an
    artifact's clothes. Returns (errors, enumerated, unreachable)."""
    if not isinstance(scope, dict):
        return (fail(name, "%s: a floor with pins carries no scope block - a floor that does not "
                           "say which surfaces were enumerated, by what method, and which it "
                           "COULD NOT REACH is a coverage claim wearing an artifact's clothes"
                     % SCOPE_MISSING), [], [])
    errs = _unknown_keys(scope, SCOPE_KEYS, "scope", name, fail)
    if not _is_str(scope.get("method")):
        errs += fail(name, "%s: scope.method is required - a surface list with no method is a "
                           "claim nobody can reproduce or disagree with" % SCOPE_MISSING)
    enumerated, unreachable = [], []
    for field, out in (("enumerated", enumerated), ("unreachable", unreachable)):
        val = scope.get(field)
        if val is None or (isinstance(val, list) and all(_is_str(s) for s in val)):
            out.extend(_as_list(val))
        else:
            errs += fail(name, "%s: scope.%s must be a list of surface names (%r)"
                         % (SCOPE_MISSING, field, val))
    both = sorted(set(enumerated) & set(unreachable))
    if both:
        errs += fail(name, "%s: scope declares %s as BOTH enumerated and unreachable - the pass "
                           "either reached a surface or it did not"
                     % (SCOPE_MISSING, ", ".join(repr(s) for s in both)))
    # EVERY INTERNAL REFERENCE RESOLVES: a pin over a surface the scope does not list as
    # enumerated is a pin the floor's own coverage claim does not cover.
    known = set(enumerated)
    for pin in pins:
        if isinstance(pin, dict) and _is_str(pin.get("surface")) and pin["surface"] not in known:
            errs += fail(name, "%s: pin %r pins the surface %r, which scope.enumerated does not "
                               "declare - a pin outside the enumerated set is a reference the "
                               "floor's own coverage claim does not resolve"
                         % (SCOPE_MISSING, pin.get("id"), pin["surface"]))
    return errs, enumerated, unreachable


def _validate_pin(pin, index, name, fail):
    """One pin, fail closed by NAME on every cause. A refusal names the floor file, the pin
    id (or its position when it has none) and WHICH cause fired, so an author fixes one pin
    rather than being told a floor is invalid."""
    if not isinstance(pin, dict):
        return fail(name, "%s: pins[%d] is not a mapping" % (FLOOR_UNREADABLE, index))
    pid = pin.get("id") if _is_str(pin.get("id")) else "pins[%d]" % index
    errs = _unknown_keys(pin, PIN_KEYS, "pin %s" % pid, name, fail)
    for field in PIN_REQUIRED:
        if not _is_str(pin.get(field)):
            errs += fail(name, "%s: pin %s is missing the required field %s"
                         % (PIN_FIELD_MISSING, pid, field))
    fidelity = pin.get("fidelity")
    if _is_str(fidelity) and fidelity not in FIDELITIES:
        errs += fail(name, "%s: pin %s declares fidelity %r (allowed: %s)"
                     % (PIN_VOCAB_UNKNOWN, pid, fidelity, sorted(FIDELITIES)))
    status = pin.get("status")
    if _is_str(status) and status not in STATUSES:
        errs += fail(name, "%s: pin %s declares status %r - the ONLY status a machine may write "
                           "is %s (allowed: %s). A ruling is a human decision settled through the "
                           "ticket channel and joined to the observation by its digest; it is not "
                           "a value anything writes into a floor"
                     % (PIN_VOCAB_UNKNOWN, pid, status, sorted(STATUSES)[0], sorted(STATUSES)))
    obs = pin.get("observation")
    if not isinstance(obs, dict):
        return errs + fail(name, "%s: pin %s carries no observation block {recorded, digest}"
                           % (PIN_FIELD_MISSING, pid))
    errs += _unknown_keys(obs, OBSERVATION_KEYS, "pin %s observation" % pid, name, fail)
    for field in ("recorded", "digest"):
        if not _is_str(obs.get(field)):
            errs += fail(name, "%s: pin %s is missing observation.%s"
                         % (PIN_FIELD_MISSING, pid, field))
    # THE LOAD-BEARING CHECK OF THE WHOLE ITEM: the digest is RECOMPUTED and compared,
    # never accepted as declared. A typed digest is a writable pointer at somebody else's
    # judgement, and re-pointing it is how an agent grants itself a ruling it was never
    # given.
    if _is_str(obs.get("recorded")) and _is_str(obs.get("digest")):
        recomputed = observation_digest(pin)
        if obs["digest"] != recomputed:
            errs += fail(name, "%s: pin %s declares observation.digest %r but the digest "
                               "RECOMPUTED from the recorded observation is %r - the digest is "
                               "derived, never typed, because it is the only join between a "
                               "human's ruling and a behaviour"
                         % (DIGEST_MISMATCH, pid, obs["digest"], recomputed))
    return errs


def validate_floor(data, root, floor_path, fail):
    """Structural validation of ONE parsed veldo.behavior_floor/v1 record. Reports each
    problem through fail(name, msg) and returns the error count. PURE over the dict (no
    filesystem access), so it is reused by the directory scan and the single-file entry
    point unchanged. A floor with no pins is a recorded STAND-DOWN rather than a refusal."""
    errs = 0
    name = str(floor_path)

    if data.get("schema") != SCHEMA:
        errs += fail(name, "%s: schema must be %r (got %r)"
                     % (FLOOR_UNREADABLE, SCHEMA, data.get("schema")))
    errs += _unknown_keys(data, FLOOR_KEYS, "the floor", name, fail)
    if not _is_str(data.get("id")):
        errs += fail(name, "%s: missing or empty required field: id" % PIN_FIELD_MISSING)
    if not _is_pos_int(data.get("version")):
        errs += fail(name, "%s: version must be an integer >= 1: a floor is versioned"
                     % PIN_FIELD_MISSING)
    if data.get("area") is not None and not _is_str(data.get("area")):
        errs += fail(name, "%s: area, when present, is the one area this floor records"
                     % PIN_FIELD_MISSING)

    pins = data.get("pins")
    if pins is not None and not isinstance(pins, list):
        return errs + fail(name, "%s: pins must be a list of pins (%r)" % (FLOOR_UNREADABLE, pins))
    pins = _as_list(pins)
    if not pins:
        _standdown(name, "the floor declares no pins, so there is nothing to validate and "
                         "nothing to read a disposition for")
        return errs

    errs += _validate_scope(data.get("scope"), pins, name, fail)[0]
    ids = []
    for index, pin in enumerate(pins):
        errs += _validate_pin(pin, index, name, fail)
        if isinstance(pin, dict) and _is_str(pin.get("id")):
            ids.append(pin["id"])
    for pid in sorted(set(ids)):
        if ids.count(pid) > 1:
            errs += fail(name, "%s: pin id %r is declared %d times in this floor"
                         % (DUPLICATE_PIN_ID, pid, ids.count(pid)))
    return errs


def check_floor(path, root, required, parse, fail):
    """Single-file entry point. Absent file: stand down (adoption safe) unless it is
    required, in which case fail closed (referenced but absent). Present file: parse and
    validate structurally, failing closed on anything malformed."""
    p = Path(path)
    if not p.is_file():
        if required:
            return fail(str(p), "%s: floor is referenced as required but absent (fail closed)"
                        % FLOOR_UNREADABLE)
        return _standdown(p, "the floor is absent and nothing requires it")
    try:
        data = load_floor(p, parse)
    except FloorRecordError as e:
        return fail(str(p), str(e))
    return validate_floor(data, root, p, fail)


def check_floors_dir(fdir, root, parse, fail):
    """The gate entry point over the per-repo floors. ADOPTION SAFE: an absent
    .veldo/floors/ directory stands the whole check down and returns clean, exactly as
    decision.check_decisions_dir does, so a repository with no floors is byte-identically
    unaffected and adding this check refuses nothing anywhere. Present floors each fail
    closed on anything malformed, and a pin id declared by more than one floor is refused
    (a duplicate id is an ambiguous reference across the set, the rule
    .veldo/decision.py:239-241 already applies to decision ids).

    ENFORCES NOTHING BEYOND WELL-FORMEDNESS: no change is refused because a pin is unknown
    or blocked. This never calls disposition_for."""
    d = Path(fdir)
    if not d.is_dir():
        return _standdown(d, "no .veldo/floors/ directory: a repository that has not adopted "
                             "the behaviour floor is byte-identically unaffected")
    errs = 0
    ids = {}
    for p in sorted(d.glob("*.yaml")):
        errs += check_floor(p, root, False, parse, fail)
        try:
            data = load_floor(p, parse)
        except FloorRecordError:
            continue  # already reported by check_floor above
        for pin in _as_list(data.get("pins")):
            if isinstance(pin, dict) and _is_str(pin.get("id")):
                ids.setdefault(pin["id"], set()).add(p.name)
    for pid, files in sorted(ids.items()):
        if len(files) > 1:
            errs += fail(str(d), "%s: pin id %r is declared by more than one floor: %s"
                         % (DUPLICATE_PIN_ID, pid, ", ".join(sorted(files))))
    return errs


# --- the READ-ONLY disposition resolver -------------------------------------------------
def _load_settlements(root):
    """Every settlement record the receipt path has written, as parsed dicts keyed by file
    name for determinism. READ ONLY; this module writes nothing, ever."""
    out = []
    d = default_settlements_dir(root)
    if not d.is_dir():
        return out
    for p in sorted(d.glob("*.json")):
        try:
            rec = json.loads(p.read_text())
        except (OSError, ValueError):
            continue
        if isinstance(rec, dict):
            out.append(rec)
    return out


def _load_requests(root, parse):
    """Every veldo.request/v1 record, as parsed dicts. READ ONLY, through the caller's ONE
    parser, so there is no second parser here either."""
    out = []
    d = default_requests_dir(root)
    if not d.is_dir() or parse is None:
        return out
    for p in sorted(d.glob("*.yaml")):
        try:
            rec = parse(p.read_text())
        except (OSError, ValueError):
            continue
        if isinstance(rec, dict):
            out.append(rec)
    return out


def _accepted_request(request_id, requests):
    """The veldo.request/v1 record that carries this settlement, ONLY when it is a
    decision_choice touchpoint whose status is accepted (.veldo/request.py:74-77, and the
    accepted-binding rule at .veldo/request.py:273-274). Anything else returns None, which
    leaves the pin unknown: a settlement file with no accepted request behind it is a
    forgery, not a ruling."""
    if not _is_str(request_id):
        return None
    for req in requests:
        if (req.get("schema") == REQUEST_SCHEMA and req.get("id") == request_id
                and req.get("touchpoint") == REQUEST_TOUCHPOINT
                and req.get("status") == REQUEST_ACCEPTED):
            return req
    return None


def _matching_settlements(digest, settlements):
    """The settlements that claim THIS observation: schema veldo.decision/v1, decision
    "decided", and bound_digest equal to the RECOMPUTED digest. Sorted for determinism."""
    out = [s for s in settlements
           if s.get("schema") == SETTLEMENT_SCHEMA
           and s.get("decision") == SETTLEMENT_DECIDED
           and _is_str(s.get("bound_digest")) and s["bound_digest"] == digest]
    return sorted(out, key=lambda s: (str(s.get("request_id")), str(s.get("changelog_id"))))


def disposition_for(pin, root=None, parse=None, settlements=None, requests=None):
    """READ-ONLY: what a human has said about ONE pin's observation, or why nothing is
    known. Returns {pin, digest, disposition, reason, ruling, request}.

    A RULING IS RESOLVED ONLY FROM A DECISION THAT WENT THROUGH THE TICKET CHANNEL, JOINED
    TO THE OBSERVATION BY DIGEST, AND THE FLOOR HOLDS NO POINTER TO IT. The join is the
    digest and nothing else, in ONE direction, so mutating the recorded observation changes
    the digest and the same settlement stops matching.

      ruled    a settlement matches the recomputed digest, its request_id resolves to an
               ACCEPTED decision_choice veldo.request/v1 record, and the chosen option
               resolves to a member of RULINGS.
      blocked  all of that holds and the settlement carries NO chosen option that resolves
               (RULING_NOT_CARRIED). This is today's state for every real ruling: the
               inbound edge derives only accept or reject and never writes the option, so
               the repository cannot learn WHICH way a human ruled. It BLOCKS with the
               reason named - never a ruling, never a default, and never quietly back to
               unknown as if nobody had decided anything, which is PLAN-0016's own
               no-bypass rule applied rather than routed around.
      unknown  nothing settled carries this observation, or what does has no accepted
               request behind it (RULING_NOT_SETTLED). NOBODY HAS RULED.

    settlements/requests may be injected as lists of parsed records (the suite does); when
    they are not, they are read from root. This function never writes and never refuses."""
    digest = observation_digest(pin)
    pid = pin.get("id") if isinstance(pin, dict) else None
    setts = settlements if settlements is not None else _load_settlements(root)
    reqs = requests if requests is not None else _load_requests(root, parse)
    blocked = None
    for s in _matching_settlements(digest, setts):
        req = _accepted_request(s.get("request_id"), reqs)
        if req is None:
            continue
        chosen = s.get("chosen")
        if _is_str(chosen) and chosen in RULINGS:
            return {"pin": pid, "digest": digest, "disposition": DISPOSITION_RULED,
                    "ruling": chosen, "request": req.get("id"),
                    "reason": "ruled %s by an attributed human through request %s, bound to this "
                              "observation's recomputed digest" % (chosen, req.get("id"))}
        if blocked is None:
            blocked = {"pin": pid, "digest": digest, "disposition": DISPOSITION_BLOCKED,
                       "ruling": None, "request": req.get("id"),
                       "reason": "%s: a human settled a decision on this observation through "
                                 "request %s and the inbound edge carried no chosen option, so "
                                 "the repository cannot learn WHICH of %s they chose. BLOCKED "
                                 "with the reason named rather than defaulted; the option "
                                 "carrier is a PLAN-0016 work item"
                                 % (RULING_NOT_CARRIED, req.get("id"), sorted(RULINGS))}
    if blocked is not None:
        return blocked
    return {"pin": pid, "digest": digest, "disposition": DISPOSITION_UNKNOWN, "ruling": None,
            "request": None,
            "reason": "%s: nothing settled through the ticket channel carries this observation's "
                      "digest with an accepted decision_choice request behind it. NOBODY HAS "
                      "RULED - which is a different fact from a human having ruled unreadably"
                      % RULING_NOT_SETTLED}


# --- the report: counts BESIDE the weakness that produced them --------------------------
def floor_report(fdir=None, root=None, parse=None, settlements=None, requests=None):
    """The read-only floor report. ONE key shape whether it stood down or not, so a
    consumer never guesses whether a key is missing or genuinely empty.

    The pin, ruled, unknown and blocked counts sit BESIDE the scope block's
    enumerated-surface and unreachable-surface counts, so no coverage figure is quotable
    without the weakness that produced it. A FLOOR NEVER REPORTS A PERCENTAGE OF AN AREA:
    there is no ratio key and no float anywhere in this report, because a percentage of an
    estate nobody enumerated is the one number this repository refuses to print."""
    base = Path(root) if root is not None else Path(".")
    d = Path(fdir) if fdir is not None else default_floors_dir(base)
    rep = {"standdown": True, "reason": None, "floors": 0, "pins": 0,
           DISPOSITION_RULED: 0, DISPOSITION_UNKNOWN: 0, DISPOSITION_BLOCKED: 0,
           "enumerated_surfaces": 0, "unreachable_surfaces": 0,
           "unanalyzed_languages": [], "dispositions": []}
    if not d.is_dir():
        rep["reason"] = ("no .veldo/floors/ directory: this repository has not adopted the "
                         "behaviour floor")
        return rep
    setts = settlements if settlements is not None else _load_settlements(base)
    reqs = requests if requests is not None else _load_requests(base, parse)
    langs = set()
    for p in sorted(d.glob("*.yaml")):
        try:
            data = load_floor(p, parse)
        except FloorRecordError:
            continue
        rep["floors"] += 1
        scope = data.get("scope") if isinstance(data.get("scope"), dict) else {}
        rep["enumerated_surfaces"] += len(_as_list(scope.get("enumerated")))
        rep["unreachable_surfaces"] += len(_as_list(scope.get("unreachable")))
        for pin in _as_list(data.get("pins")):
            if not isinstance(pin, dict):
                continue
            rep["pins"] += 1
            if not analyzer_supported(pin.get("language")):
                langs.add(pin.get("language"))
            disp = disposition_for(pin, root=base, parse=parse, settlements=setts, requests=reqs)
            disp["floor"] = p.name
            rep["dispositions"].append(disp)
            rep[disp["disposition"]] += 1
    rep["unanalyzed_languages"] = sorted(str(x) for x in langs)
    if rep["pins"] == 0:
        rep["reason"] = ("no floor in .veldo/floors/ declares a pin, so there is no recorded "
                         "behaviour to read a disposition for")
        return rep
    rep["standdown"] = False
    return rep


def report_lines(rep):
    """The report as lines a stranger reads. The stand-down NAMES which condition stood it
    down, and each pin line carries its disposition WITH the reason, because "unknown" and
    "a human ruled and the channel could not carry which way" are different facts."""
    if rep.get("standdown"):
        return ["behaviour floor: stood down - %s" % rep.get("reason")]
    lines = ["behaviour floor: %d floor(s), %d pin(s): %d ruled, %d unknown, %d blocked. "
             "Scope: %d surface(s) enumerated, %d NOT REACHED"
             % (rep["floors"], rep["pins"], rep[DISPOSITION_RULED], rep[DISPOSITION_UNKNOWN],
                rep[DISPOSITION_BLOCKED], rep["enumerated_surfaces"],
                rep["unreachable_surfaces"])]
    if rep.get("unanalyzed_languages"):
        lines.append("  the shipped analyzers are %s only, so no analyzer covers: %s"
                     % (", ".join(ANALYZER_LANGUAGES), ", ".join(rep["unanalyzed_languages"])))
    for disp in rep["dispositions"]:
        lines.append("  %s %s: %s - %s" % (disp.get("floor"), disp.get("pin"),
                                           disp.get("disposition"), disp.get("reason")))
    return lines
