"""VELDO-0012: the behaviour floor contract, the root of the legacy on-ramp.

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, which always
runs, so its declared prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 18_veldo_0012_behaviour_floor_contract

WHAT IS UNDER TEST AND WHERE IT LIVES. The artifact and its refusals are
.veldo/behavior_floor.py; the gate wrappers are validate_checks.check_floor and
validate_checks.check_floors. Both are driven through V._VC, which is the module instance
.veldo/validate.py itself loaded and handed the ONE front-matter parser and the ONE failure
reporter, and BF below is the behaviour-floor instance THAT module loaded - so every refusal
here is printed by the reporter the gate prints through and every fixture is read by the parser
the contract is defined in terms of, rather than by a second copy with test wiring.

WHAT THIS FRAGMENT REFUSES TO DO. Every refusal is paired with an ACCEPTING row over a fixture
that differs in exactly the one field, because a refusal asserted alone is indistinguishable from
a validator that refuses everything. The seven criteria of VELDO-0012 each declare a FALSIFIED BY,
and the rows below are named for them.

TWO THINGS THIS FRAGMENT DELIBERATELY DOES NOT CLAIM, stated rather than hidden.

  THE REGISTRATION IN run_all DOES NOT EXIST YET. .veldo/validate.py is wired serially by the
  owner, so this suite calls V._VC.check_floors() DIRECTLY - the exact call the registration will
  make. AC7's own falsification names "the assertion that validate.run_all's output over this
  repository is byte-identical", and the row below asserts precisely that property in the only
  form available before the wiring lands: run_all's (count, output) over this repository, plus the
  check called as run_all will call it, equals run_all's (count, output) alone. Deleting the
  stand-down guard makes the second term RAISE, so the row reds. No row here pretends the
  registration exists.

  THE TWO protected_paths ENTRIES ARE A HUMAN ACT. AC6's rows read the LIVE policy through
  policy_check.protected_patterns(), which is the mechanism the gate uses. The entries are written
  and the rows are green, but registering a protected path is itself a .veldo/policy.yaml edit and
  needs Dmitry's recorded, commit-bound approval; nothing here can grant that and nothing here
  claims it was granted.
"""
import ast as _bf_ast
import contextlib as _bf_ctx
import fnmatch as _bf_fn
import io as _bf_io
import re as _bf_re

# THE INSTANCES THE VALIDATOR ITSELF LOADED, not second copies.
BFC = V._VC                                    # validate_checks, with the one parser/reporter
BF = V._VC._behavior_floor_module()            # the behaviour-floor organ the wrapper drives

_BF_S1 = ".veldo/example.py::normalize"
_BF_S2 = ".veldo/example.py::render"
_BF_S3 = ".veldo/example.py::send_mail"
_BF_REC1 = "normalize of a padded string returns it stripped, and normalize of nothing returns "\
           "the empty string rather than raising"
_BF_REC2 = "render of an empty list returns the empty string and never the literal None"


def _bf_emit(val, indent):
    """Render a dict/list tree as the yamlish subset the ONE parser reads. Sibling keys of a list
    item sit at indent+2 and a nested block under one at indent+4, which is exactly what
    validate._parse_list accepts, so a fixture that fails to parse is a fixture defect and not a
    silent shape difference."""
    lines = []
    if isinstance(val, dict):
        for k in val:
            v = val[k]
            if isinstance(v, (dict, list)):
                lines.append("%s%s:" % (" " * indent, k))
                lines.extend(_bf_emit(v, indent + 2))
            else:
                lines.append("%s%s: %s" % (" " * indent, k, v))
        return lines
    for item in val:
        if not isinstance(item, dict):
            lines.append("%s- %s" % (" " * indent, item))
            continue
        keys = list(item)
        for pos, k in enumerate(keys):
            v = item[k]
            lead = "%s- " % (" " * indent) if pos == 0 else "%s" % (" " * (indent + 2))
            if isinstance(v, (dict, list)):
                lines.append("%s%s:" % (lead, k))
                lines.extend(_bf_emit(v, indent + 4))
            else:
                lines.append("%s%s: %s" % (lead, k, v))
    return lines


def _bf_pin(pid="PIN-1", surface=_BF_S1, recorded=_BF_REC1, language="python", fidelity="exact",
            status="unknown", reproduces="tests/test_example.py::test_normalize", digest=None,
            drop=(), extra=None, obs_extra=None):
    """One pin whose ONLY defect can be the thing a row is about. The digest is COMPUTED through
    the module's own canonicalization unless a row deliberately supplies a stale one, because a
    fixture that hard-codes a digest tests the fixture."""
    pin = {"id": pid, "surface": surface, "language": language, "fidelity": fidelity,
           "reproduces": reproduces, "status": status}
    for k in drop:
        pin.pop(k, None)
    for k in (extra or {}):
        pin[k] = (extra or {})[k]
    obs = {"recorded": recorded}
    for k in (obs_extra or {}):
        obs[k] = (obs_extra or {})[k]
    pin["observation"] = obs
    pin["observation"]["digest"] = digest if digest is not None else BF.observation_digest(pin)
    return pin


def _bf_floor(pins, scope=None, fid="FLOOR-example", schema=BF.SCHEMA, extra=None, drop=()):
    """One floor. scope defaults to a scope block that enumerates every pinned surface and
    declares one it could not reach, which is what a real drafting pass would emit."""
    if scope is None and pins:
        scope = {"method": "read every public function of the module and record its return over "
                           "the fixture inputs, by hand",
                 "enumerated": sorted({p["surface"] for p in pins if isinstance(p, dict)
                                       and "surface" in p}),
                 "unreachable": [_BF_S3]}
    floor = {"schema": schema, "id": fid, "version": 1, "area": "contracts"}
    if scope is not None:
        floor["scope"] = scope
    floor["pins"] = pins
    for k in drop:
        floor.pop(k, None)
    for k in (extra or {}):
        floor[k] = (extra or {})[k]
    return "\n".join(_bf_emit(floor, 0)) + "\n"


def _bf_capture(fn):
    """(count, printed) for one call, or (None, "RAISED: ...") when it raises. A raise is the
    OUTCOME two of this item's declared falsifications produce, and a fragment that dies on the
    exception would report no verdict line at all, so it is captured into a red row instead."""
    buf = _bf_io.StringIO()
    try:
        with _bf_ctx.redirect_stdout(buf):
            n = fn()
    except Exception as exc:                    # noqa: BLE001 - a raise is a RED ROW, not a crash
        return None, "RAISED: %r" % (exc,)
    return n, buf.getvalue()


def _bf_run(*floors, **kw):
    """Write the given floor texts into a fresh .veldo/floors/ and run the GATE WRAPPER over it,
    exactly as the registration will. Returns (count, printed)."""
    import tempfile as _bf_tf
    with _bf_tf.TemporaryDirectory() as d:
        fdir = Path(d) / ".veldo" / "floors"
        fdir.mkdir(parents=True)
        for n, text in enumerate(floors):
            (fdir / ("floor-%d.yaml" % n)).write_text(text)
        return _bf_capture(lambda: BFC.check_floors(floors_dir=fdir, root=Path(d)))


_BF_GOOD_PINS = [_bf_pin(), _bf_pin(pid="PIN-2", surface=_BF_S2, recorded=_BF_REC2,
                                    reproduces="tests/test_example.py::test_render")]
_BF_GOOD = _bf_floor(_BF_GOOD_PINS)

# POSITIVE CONTROL FIRST, on the fixture builder itself. Every refusal below is attributable to
# the one field a row changes rather than to a fixture the validator would reject anyway, and the
# fixture really does parse through the ONE parser into the shape the contract describes.
_BF_PARSED = V.parse_yamlish(_BF_GOOD)
expect("VELDO-0012 fixture: the well-formed floor parses through the ONE front-matter parser into "
       "a floor with a scope block and two pins, and the GATE WRAPPER accepts it printing "
       "nothing, so every refusal below is the one field a row changes",
       _BF_PARSED.get("schema") == BF.SCHEMA
       and isinstance(_BF_PARSED.get("scope"), dict)
       and [p["id"] for p in _BF_PARSED["pins"]] == ["PIN-1", "PIN-2"]
       and _BF_PARSED["pins"][0]["observation"]["digest"].startswith("sha256:")
       and _bf_run(_BF_GOOD) == (0, ""))

# ---------------------------------------------------------------------------------------
# AC1. THE ARTIFACT EXISTS AND THE ONLY STATUS A MACHINE MAY WRITE IS unknown.
#
# FALSIFIED BY (from the criterion itself): widen STATUSES from its single member unknown to also
# admit load_bearing, and the negative-fixture assertion that a pin declaring status load_bearing
# is refused by PIN_VOCAB_UNKNOWN must go red while the well-formed fixture is still accepted, so
# the refusal is discriminating rather than a blanket rejection.
# ---------------------------------------------------------------------------------------
_BF_LOADBEARING = _bf_floor([_bf_pin(status="load_bearing")])
_BF_LB_N, _BF_LB_OUT = _bf_run(_BF_LOADBEARING)
expect("VELDO-0012 AC1: a pin declaring status load_bearing is REFUSED by "
       "PIN_VOCAB_UNKNOWN, exactly once, and the refusal names the floor file, the pin id and the "
       "cause - the only status a machine may write is unknown, so a drafting pass cannot express "
       "a conclusion at all",
       _BF_LB_N == 1 and BF.PIN_VOCAB_UNKNOWN in _BF_LB_OUT and "PIN-1" in _BF_LB_OUT
       and "floor-0.yaml" in _BF_LB_OUT and "load_bearing" in _BF_LB_OUT)
expect("VELDO-0012 AC1 NEGATIVE CONTROL: the SAME validator accepts the SAME fixture with status "
       "unknown, printing nothing, so the row above is the status vocabulary and not a blanket "
       "rejection",
       _bf_run(_bf_floor([_bf_pin(status="unknown")])) == (0, ""))
expect("VELDO-0012 AC1: the status vocabulary has EXACTLY ONE member, and the three RULINGS a "
       "human may choose among are a DIFFERENT vocabulary that is disjoint from it - so no ruling "
       "word is ever a value a floor can carry",
       BF.STATUSES == {"unknown"} and len(BF.STATUSES) == 1
       and BF.RULINGS == {"load_bearing", "incidental", "defect"}
       and not (BF.STATUSES & BF.RULINGS))
expect("VELDO-0012 AC1: fidelity is the closed vocabulary {exact, proxy} - a near-miss value is "
       "refused by the SAME named cause, and both declared members are accepted, so a real "
       "estate's proxy pins are representable",
       _bf_run(_bf_floor([_bf_pin(fidelity="approximate")]))[0] == 1
       and BF.PIN_VOCAB_UNKNOWN in _bf_run(_bf_floor([_bf_pin(fidelity="approximate")]))[1]
       and BF.FIDELITIES == {"exact", "proxy"}
       and _bf_run(_bf_floor([_bf_pin(fidelity="proxy")])) == (0, "")
       and _bf_run(_bf_floor([_bf_pin(fidelity="exact")])) == (0, ""))
for _bf_field in ("id", "surface", "language", "fidelity", "reproduces", "status"):
    _bf_n, _bf_out = _bf_run(_bf_floor([_bf_pin(drop=(_bf_field,))],
                                       scope={"method": "by hand", "enumerated": [_BF_S1],
                                              "unreachable": []}))
    expect("VELDO-0012 AC1: a pin missing %s is refused by PIN_FIELD_MISSING naming the field, "
           "because a pin nobody can locate or reproduce is not a pin" % _bf_field,
           _bf_n >= 1 and BF.PIN_FIELD_MISSING in _bf_out and _bf_field in _bf_out)
expect("VELDO-0012 AC1: a pin with no observation block is refused by PIN_FIELD_MISSING, and so "
       "is one whose observation carries no recorded text - an artifact with no recorded "
       "behaviour records nothing",
       BF.PIN_FIELD_MISSING in _bf_run(_bf_floor([{"id": "PIN-1", "surface": _BF_S1,
                                                   "language": "python", "fidelity": "exact",
                                                   "reproduces": "t::t", "status": "unknown"}]))[1]
       and _bf_run(_bf_floor([_bf_pin(recorded="")]))[0] >= 1)
expect("VELDO-0012 AC1: a duplicate pin id WITHIN one floor is refused by DUPLICATE_PIN_ID, the "
       "rule decision.py:239-241 already applies to decision ids, and the distinct-id fixture is "
       "accepted",
       BF.DUPLICATE_PIN_ID in _bf_run(_bf_floor([_bf_pin(), _bf_pin(surface=_BF_S2,
                                                                   recorded=_BF_REC2)]))[1]
       and _bf_run(_BF_GOOD) == (0, ""))
_BF_DUP_N, _BF_DUP_OUT = _bf_run(_bf_floor([_bf_pin()]),
                                 _bf_floor([_bf_pin(surface=_BF_S2, recorded=_BF_REC2)],
                                           fid="FLOOR-other"))
expect("VELDO-0012 AC1: a duplicate pin id ACROSS THE SET is refused too, naming BOTH floors, "
       "because a duplicate id is an ambiguous reference across the corpus and not only inside "
       "one file",
       _BF_DUP_N == 1 and BF.DUPLICATE_PIN_ID in _BF_DUP_OUT
       and "floor-0.yaml" in _BF_DUP_OUT and "floor-1.yaml" in _BF_DUP_OUT)
_BF_NOSCOPE_N, _BF_NOSCOPE_OUT = _bf_run(_bf_floor([_bf_pin()], drop=("scope",)))
expect("VELDO-0012 AC1: a floor WITH PINS and NO SCOPE BLOCK is refused by SCOPE_MISSING - a "
       "floor that does not say what it did not look at is a coverage claim wearing an artifact's "
       "clothes",
       _BF_NOSCOPE_N == 1 and BF.SCOPE_MISSING in _BF_NOSCOPE_OUT)
expect("VELDO-0012 AC1: a scope block with no METHOD is refused, and so is one that declares the "
       "same surface both enumerated and unreachable, because the pass either reached a surface "
       "or it did not",
       BF.SCOPE_MISSING in _bf_run(_bf_floor([_bf_pin()],
                                             scope={"enumerated": [_BF_S1],
                                                    "unreachable": []}))[1]
       and BF.SCOPE_MISSING in _bf_run(_bf_floor(
           [_bf_pin()], scope={"method": "by hand", "enumerated": [_BF_S1],
                               "unreachable": [_BF_S1]}))[1])
expect("VELDO-0012 AC1: EVERY INTERNAL REFERENCE RESOLVES - a pin over a surface scope.enumerated "
       "does not declare is refused, so a floor cannot pin a behaviour its own coverage claim "
       "never covered",
       BF.SCOPE_MISSING in _bf_run(_bf_floor(
           [_bf_pin(surface=_BF_S2, recorded=_BF_REC2)],
           scope={"method": "by hand", "enumerated": [_BF_S1], "unreachable": []}))[1])
expect("VELDO-0012 AC1: an unreadable floor is refused BY NAME rather than skipped - front matter "
       "outside the parser subset, a wrong schema, and pins that are not a list each name "
       "FLOOR_UNREADABLE",
       BF.FLOOR_UNREADABLE in _bf_run(_BF_GOOD.replace("  - id: PIN-1", "\t- id: PIN-1"))[1]
       and BF.FLOOR_UNREADABLE in _bf_run(_bf_floor([_bf_pin()], schema="veldo.floor/v9"))[1]
       and BF.FLOOR_UNREADABLE in _bf_run("schema: %s\nid: F\nversion: 1\npins: yes\n"
                                          % BF.SCHEMA)[1])
expect("VELDO-0012 AC1: the causes are NINE DIFFERENT NAMES, so a refusal tells an author which "
       "one they hit rather than that a floor is invalid, and the two DISPOSITION reasons are "
       "among them and distinct from every refusal cause",
       len(BF.CAUSES) == 9 and len({BF.FLOOR_UNREADABLE, BF.PIN_FIELD_MISSING,
                                    BF.PIN_VOCAB_UNKNOWN, BF.PIN_KEY_UNRECOGNIZED,
                                    BF.DIGEST_MISMATCH, BF.DUPLICATE_PIN_ID, BF.SCOPE_MISSING,
                                    BF.RULING_NOT_SETTLED, BF.RULING_NOT_CARRIED}) == 9)

# ---------------------------------------------------------------------------------------
# AC2. THE OBSERVATION DIGEST IS DERIVED AND RE-VERIFIED, NEVER TYPED. The load-bearing
# property of the whole item.
#
# FALSIFIED BY: delete the recompute in the pin validator so observation.digest is accepted as
# declared, and the assertion that a fixture whose observation.recorded was edited while its
# digest was left alone is refused by DIGEST_MISMATCH must go red; the positive control (an
# untouched fixture whose declared digest equals the recomputed one) must still pass.
# ---------------------------------------------------------------------------------------
_BF_STALE_PIN = _bf_pin()
_BF_STALE = _bf_floor([dict(_BF_STALE_PIN,
                            observation={"recorded": _BF_REC1 + ", and it also lowercases",
                                         "digest": _BF_STALE_PIN["observation"]["digest"]})])
_BF_STALE_N, _BF_STALE_OUT = _bf_run(_BF_STALE)
expect("VELDO-0012 AC2: a pin whose observation.recorded was EDITED while its digest was left "
       "alone is refused by DIGEST_MISMATCH, and the refusal prints BOTH the declared digest and "
       "the recomputed one so an author sees which is which",
       _BF_STALE_N == 1 and BF.DIGEST_MISMATCH in _BF_STALE_OUT
       and _BF_STALE_PIN["observation"]["digest"] in _BF_STALE_OUT
       and BF.observation_digest(V.parse_yamlish(_BF_STALE)["pins"][0]) in _BF_STALE_OUT)
expect("VELDO-0012 AC2 POSITIVE CONTROL: the untouched fixture, whose declared digest EQUALS the "
       "recomputed one, is still accepted printing nothing, so the check is not simply refusing "
       "every pin",
       _bf_run(_BF_GOOD) == (0, "")
       and all(p["observation"]["digest"] == BF.observation_digest(p)
               for p in V.parse_yamlish(_BF_GOOD)["pins"]))
expect("VELDO-0012 AC2: the digest is DERIVED from the declared field tuple and nothing else - "
       "changing surface or recorded changes it, changing language, fidelity, reproduces or the "
       "pin id does NOT, and the tuple is the module's own declaration",
       BF.OBSERVATION_DIGEST_FIELDS == ("surface", "recorded")
       and BF.observation_digest(_bf_pin()) != BF.observation_digest(_bf_pin(surface=_BF_S2))
       and BF.observation_digest(_bf_pin()) != BF.observation_digest(_bf_pin(recorded="other"))
       and BF.observation_digest(_bf_pin()) == BF.observation_digest(_bf_pin(pid="PIN-9"))
       == BF.observation_digest(_bf_pin(language="kotlin"))
       == BF.observation_digest(_bf_pin(fidelity="proxy"))
       == BF.observation_digest(_bf_pin(reproduces="other::test")))
expect("VELDO-0012 AC2: THE SURFACE IS IN THE TUPLE ON PURPOSE - two pins recording a "
       "byte-identical observation on two DIFFERENT surfaces get DIFFERENT digests, so one "
       "human's judgement about one of them can never silently rule the other",
       BF.observation_digest(_bf_pin(pid="A", surface=_BF_S1, recorded=_BF_REC1))
       != BF.observation_digest(_bf_pin(pid="B", surface=_BF_S2, recorded=_BF_REC1)))
expect("VELDO-0012 AC2: ONE canonicalization, the same shape request_digest uses - a sorted-keys "
       "JSON blob and one hash - deterministic across repeated calls and never read from the "
       "file, so a re-pointed digest cannot survive the recompute",
       _bf_re.fullmatch(r"sha256:[0-9a-f]{16}", BF.observation_digest(_bf_pin()))
       and BF.observation_digest(_bf_pin()) == BF.observation_digest(_bf_pin())
       and BF.observation_digest(dict(_bf_pin(), observation={"recorded": _BF_REC1,
                                                             "digest": "sha256:0000000000000000"}))
       == BF.observation_digest(_bf_pin()))

# ---------------------------------------------------------------------------------------
# AC3. NO RULING AND NO EXEMPTION IS REPRESENTABLE IN THE FLOOR AT ALL.
#
# FALSIFIED BY: delete the unrecognized-key refusal from the pin validator so unknown keys are
# ignored instead of refused, and the three assertions over a fixture planting decided_by, reason
# and exempt_paths on ONE pin must go red (one per planted key).
# ---------------------------------------------------------------------------------------
_BF_PLANTED = _bf_floor([_bf_pin(extra={"decided_by": "dmitry", "reason": "it is fine",
                                        "exempt_paths": "legacy/**"})])
_BF_PL_N, _BF_PL_OUT = _bf_run(_BF_PLANTED)
expect("VELDO-0012 AC3: a pin planting decided_by is REFUSED by PIN_KEY_UNRECOGNIZED naming the "
       "key, so a ruling is structurally unwriteable inside a floor rather than merely "
       "discouraged",
       BF.PIN_KEY_UNRECOGNIZED in _BF_PL_OUT and "'decided_by'" in _BF_PL_OUT)
expect("VELDO-0012 AC3: a pin planting reason is REFUSED by PIN_KEY_UNRECOGNIZED naming the key, "
       "so the human-readable half of a ruling has nowhere to go either",
       BF.PIN_KEY_UNRECOGNIZED in _BF_PL_OUT and "'reason'" in _BF_PL_OUT)
expect("VELDO-0012 AC3: a pin planting exempt_paths is REFUSED by PIN_KEY_UNRECOGNIZED naming the "
       "key - a path exemption exempts a LOCATION forever and the load-bearing behaviour that "
       "appears there next year is invisible, which is the mechanism WARP-1310 refuses for "
       "secrets and this contract does not reintroduce under a friendlier name",
       BF.PIN_KEY_UNRECOGNIZED in _BF_PL_OUT and "'exempt_paths'" in _BF_PL_OUT)
expect("VELDO-0012 AC3: the three planted keys are refused ONCE EACH and nothing else fires, so "
       "the refusal is per-key and discriminating rather than one undifferentiated complaint "
       "about the pin",
       _BF_PL_N == 3 and _BF_PL_OUT.count(BF.PIN_KEY_UNRECOGNIZED) == 3)
expect("VELDO-0012 AC3 NEGATIVE CONTROL: the SAME fixture without the three planted keys is "
       "accepted printing nothing, so the rows above are the closed key set and not a validator "
       "that refuses every pin",
       _bf_run(_bf_floor([_bf_pin()])) == (0, ""))
expect("VELDO-0012 AC3: the key set is CLOSED AT EVERY LEVEL, so there is nowhere in the whole "
       "artifact for a ruling or an exemption to go - a planted key at floor level, inside the "
       "scope block and inside the observation block is each refused by the same named cause",
       BF.PIN_KEY_UNRECOGNIZED in _bf_run(_bf_floor([_bf_pin()],
                                                    extra={"exempt": "legacy"}))[1]
       and BF.PIN_KEY_UNRECOGNIZED in _bf_run(_bf_floor(
           [_bf_pin()], scope={"method": "by hand", "enumerated": [_BF_S1], "unreachable": [],
                               "waived_paths": "legacy"}))[1]
       and BF.PIN_KEY_UNRECOGNIZED in _bf_run(_bf_floor(
           [_bf_pin(obs_extra={"disposition": "incidental"})]))[1])
expect("VELDO-0012 AC3: NO KEY ANYWHERE IN THE ARTIFACT ADDRESSES A LOCATION. Every one of the "
       "four closed key sets is enumerated and none of them carries a path, glob, pattern, "
       "module, directory, file or scope-of-files key, so a path-scoped exemption is not merely "
       "refused, it is unrepresentable",
       not any(_bf_w in _bf_k.lower()
               for _bf_k in (BF.FLOOR_KEYS | BF.SCOPE_KEYS | BF.PIN_KEYS | BF.OBSERVATION_KEYS)
               for _bf_w in ("path", "glob", "pattern", "dir", "file", "exempt", "waiv",
                             "disposition", "decided", "ruling"))
       and BF.PIN_KEYS == {"id", "surface", "language", "fidelity", "observation", "reproduces",
                           "status"})

# ---------------------------------------------------------------------------------------
# AC4. A RULING IS RESOLVED ONLY FROM A DECISION THAT WENT THROUGH THE TICKET CHANNEL, JOINED TO
# THE OBSERVATION BY DIGEST, AND THE FLOOR HOLDS NO POINTER TO IT.
#
# FALSIFIED BY: have disposition_for fall back to the settlement record's own decided_by when the
# request lookup returns nothing, and the assertion that a settlement carrying the pin's digest
# with no accepted veldo.request/v1 record behind it leaves the pin unknown with
# RULING_NOT_SETTLED must go red.
# ---------------------------------------------------------------------------------------
_BF_PIN = _bf_pin()
_BF_DIGEST = BF.observation_digest(_BF_PIN)


def _bf_settlement(digest=None, chosen=None, schema=BF.SETTLEMENT_SCHEMA, decision="decided",
                   request_id="REQ-9"):
    """A settlement in the shape the PLAN-0016 receipt path writes
    (.veldo/request_reconcile.py:247-259), with an optional chosen option the shipped edge does
    NOT write today."""
    rec = {"schema": schema, "request_id": request_id, "changelog_id": "c2",
           "touchpoint": "decision_choice", "settled_by": "veldo.request_reconcile/v1",
           "settled_at": "2026-08-11T00:00:00Z", "decision": decision,
           "decided_by": "dmitry", "bound_digest": digest if digest else _BF_DIGEST,
           "approvers": ["dmitry"]}
    if chosen is not None:
        rec["chosen"] = chosen
    return rec


def _bf_request(status=BF.REQUEST_ACCEPTED, touchpoint=BF.REQUEST_TOUCHPOINT, rid="REQ-9"):
    return {"schema": BF.REQUEST_SCHEMA, "id": rid, "version": 1, "touchpoint": touchpoint,
            "tier": "high", "status": status,
            "bound_artifact": {"kind": "decision", "ref": ".veldo/decisions/d.yaml",
                               "digest": "sha256:aaaaaaaaaaaaaaaa"}}


_BF_FORGED = BF.disposition_for(_BF_PIN, settlements=[_bf_settlement()], requests=[])
expect("VELDO-0012 AC4 NEGATIVE CONTROL, AND IT IS THE LEG THAT MATTERS: a hand-written "
       "settlement carrying the pin's RIGHT digest with NO accepted veldo.request/v1 record "
       "behind it rules NOTHING - the pin stays unknown with RULING_NOT_SETTLED, so a forged file "
       "is not a ruling",
       _BF_FORGED["disposition"] == BF.DISPOSITION_UNKNOWN
       and BF.RULING_NOT_SETTLED in _BF_FORGED["reason"]
       and _BF_FORGED["ruling"] is None and _BF_FORGED["request"] is None
       and "dmitry" not in _BF_FORGED["reason"])
for _bf_label, _bf_req in (("no request at all", []),
                           ("a request that is still open", [_bf_request(status="open")]),
                           ("a request that was rejected", [_bf_request(status="rejected")]),
                           ("a request for a DIFFERENT touchpoint",
                            [_bf_request(touchpoint="spec_approval")]),
                           ("a request whose id does not match the settlement",
                            [_bf_request(rid="REQ-OTHER")])):
    _bf_d = BF.disposition_for(_BF_PIN, settlements=[_bf_settlement()], requests=_bf_req)
    expect("VELDO-0012 AC4: %s leaves the pin unknown with RULING_NOT_SETTLED - the request must "
           "be an ACCEPTED decision_choice or nothing went through the channel" % _bf_label,
           _bf_d["disposition"] == BF.DISPOSITION_UNKNOWN
           and BF.RULING_NOT_SETTLED in _bf_d["reason"])
expect("VELDO-0012 AC4: a settlement that is not a decided veldo.decision/v1 does not match "
       "either - an approval record, and a decision record whose decision is rejected, both leave "
       "the pin unknown",
       BF.disposition_for(_BF_PIN, settlements=[_bf_settlement(schema="veldo.approval/v1")],
                          requests=[_bf_request()])["disposition"] == BF.DISPOSITION_UNKNOWN
       and BF.disposition_for(_BF_PIN, settlements=[_bf_settlement(decision="rejected")],
                              requests=[_bf_request()])["disposition"] == BF.DISPOSITION_UNKNOWN)
_BF_RULED = BF.disposition_for(_BF_PIN, settlements=[_bf_settlement(chosen="load_bearing")],
                               requests=[_bf_request()])
expect("VELDO-0012 AC4 POSITIVE CONTROL: a settlement matching the RECOMPUTED digest, decided, "
       "with an ACCEPTED decision_choice request behind it and a chosen option that resolves, is "
       "the ONE shape that rules - so the rows above are the channel and not a resolver that "
       "never rules",
       _BF_RULED["disposition"] == BF.DISPOSITION_RULED
       and _BF_RULED["ruling"] == "load_bearing" and _BF_RULED["request"] == "REQ-9"
       and _BF_RULED["digest"] == _BF_DIGEST)
expect("VELDO-0012 AC4: THE JOIN IS THE DIGEST AND NOTHING ELSE, so mutating the recorded "
       "observation changes the digest and the SAME settlement stops matching - a granted ruling "
       "cannot be moved onto a behaviour nobody looked at",
       BF.disposition_for(_bf_pin(recorded=_BF_REC1 + " and it also trims tabs"),
                          settlements=[_bf_settlement(chosen="load_bearing")],
                          requests=[_bf_request()])["disposition"] == BF.DISPOSITION_UNKNOWN
       and BF.disposition_for(_bf_pin(surface=_BF_S2),
                              settlements=[_bf_settlement(chosen="load_bearing")],
                              requests=[_bf_request()])["disposition"] == BF.DISPOSITION_UNKNOWN)
expect("VELDO-0012 AC4: THE FLOOR CARRIES NO POINTER TO THE RULING IN EITHER DIRECTION - no key "
       "in the pin, the observation, the scope or the floor names a request, a settlement, a "
       "decision or a ticket, so the join cannot be re-pointed by editing the floor",
       not any(_bf_w in _bf_k.lower()
               for _bf_k in (BF.FLOOR_KEYS | BF.SCOPE_KEYS | BF.PIN_KEYS | BF.OBSERVATION_KEYS)
               for _bf_w in ("request", "settlement", "decision", "ticket", "issue", "approval")))
expect("VELDO-0012 AC4: disposition_for is READ ONLY and never refuses - it returns one of the "
       "three declared dispositions for every input, including a pin with no observation at all, "
       "and writes nothing",
       all(BF.disposition_for(_bf_p, settlements=[], requests=[])["disposition"]
           in BF.DISPOSITIONS
           for _bf_p in (_BF_PIN, {}, {"id": "X"}, {"id": "X", "observation": {}}))
       and BF.DISPOSITIONS == {"ruled", "unknown", "blocked"})

# THE FILESYSTEM READ PATH, once, so the injected-record rows above are not the only thing
# proven: the resolver really does read .veldo/settlements/*.json and .veldo/requests/*.yaml.
with tempfile.TemporaryDirectory() as _bf_fsd:
    _bf_root = Path(_bf_fsd)
    (_bf_root / ".veldo" / "settlements").mkdir(parents=True)
    (_bf_root / ".veldo" / "requests").mkdir(parents=True)
    (_bf_root / ".veldo" / "settlements" / "REQ-9-c2.json").write_text(
        json.dumps(_bf_settlement(chosen="defect"), indent=2, sort_keys=True))
    (_bf_root / ".veldo" / "requests" / "REQ-9.yaml").write_text(
        "\n".join(_bf_emit(_bf_request(), 0)) + "\n")
    _bf_fs = BF.disposition_for(_BF_PIN, root=_bf_root, parse=V.parse_yamlish)
    expect("VELDO-0012 AC4: the resolver reads the REAL record paths the receipt path writes - a "
           "settlement under .veldo/settlements/ and its request under .veldo/requests/ resolve "
           "to a ruling through the filesystem, not only through injected dicts",
           _bf_fs["disposition"] == BF.DISPOSITION_RULED and _bf_fs["ruling"] == "defect")
    (_bf_root / ".veldo" / "requests" / "REQ-9.yaml").unlink()
    expect("VELDO-0012 AC4: delete the request record and the SAME settlement file on disk stops "
           "ruling, which is the forged-file leg proven over the filesystem too",
           BF.disposition_for(_BF_PIN, root=_bf_root,
                              parse=V.parse_yamlish)["disposition"] == BF.DISPOSITION_UNKNOWN)

# ---------------------------------------------------------------------------------------
# AC5. AN UNSUPPORTED RULING BLOCKS BY NAME AND IS NEVER DEFAULTED.
#
# FALSIFIED BY: map the settlement word "decided" onto load_bearing when no chosen option is
# present, and the assertion that such a settlement resolves to blocked with RULING_NOT_CARRIED
# must go red; the companion assertion that a blocked pin is never reported as ruled and never
# silently reported as unknown must go red with it.
# ---------------------------------------------------------------------------------------
_BF_BLOCKED = BF.disposition_for(_BF_PIN, settlements=[_bf_settlement()],
                                 requests=[_bf_request()])
expect("VELDO-0012 AC5: a settlement that matches the pin by digest, is decided, and has an "
       "ACCEPTED decision_choice request behind it but carries NO chosen option resolves to "
       "BLOCKED with RULING_NOT_CARRIED - never to a ruling, never to a default. This is "
       "PLAN-0016's own no-bypass rule applied rather than routed around",
       _BF_BLOCKED["disposition"] == BF.DISPOSITION_BLOCKED
       and BF.RULING_NOT_CARRIED in _BF_BLOCKED["reason"]
       and _BF_BLOCKED["ruling"] is None and _BF_BLOCKED["request"] == "REQ-9")
expect("VELDO-0012 AC5 COMPANION: a blocked pin is NEVER reported as ruled and NEVER silently "
       "reported as unknown - the two reasons are DIFFERENT NAMES that never collapse, because "
       "nobody-has-ruled and the-channel-is-incomplete are different facts and the fix is a "
       "different person's job in each case",
       _BF_BLOCKED["disposition"] != BF.DISPOSITION_RULED
       and _BF_BLOCKED["disposition"] != BF.DISPOSITION_UNKNOWN
       and BF.RULING_NOT_SETTLED not in _BF_BLOCKED["reason"]
       and BF.RULING_NOT_SETTLED != BF.RULING_NOT_CARRIED
       and BF.RULING_NOT_SETTLED in BF.disposition_for(_BF_PIN, settlements=[],
                                                       requests=[])["reason"])
expect("VELDO-0012 AC5: a chosen option OUTSIDE the ruling vocabulary blocks the same way rather "
       "than being taken at face value, and the reason names the three options the repository "
       "would have accepted",
       BF.disposition_for(_BF_PIN, settlements=[_bf_settlement(chosen="probably_fine")],
                          requests=[_bf_request()])["disposition"] == BF.DISPOSITION_BLOCKED
       and "load_bearing" in BF.disposition_for(_BF_PIN, settlements=[_bf_settlement()],
                                                requests=[_bf_request()])["reason"])
# THE CLAIM ABOUT THE SHIPPED CHANNEL, DRIVEN RATHER THAN QUOTED. AC5's whole premise is that the
# inbound edge writes no chosen option; asserting that against the real module is what makes
# BLOCKED the honest reading today instead of a state nothing can reach.
_bf_rrspec = importlib.util.spec_from_file_location("veldo_request_reconcile_for_floor",
                                                    ROOT / ".veldo" / "request_reconcile.py")
_BF_RR = importlib.util.module_from_spec(_bf_rrspec)
_bf_rrspec.loader.exec_module(_BF_RR)
_BF_SHIPPED = _BF_RR._settlement_record(
    {"id": "REQ-9", "touchpoint": "decision_choice"}, ["dmitry"], _BF_DIGEST, "c2",
    {"ts": "2026-08-11T00:00:00Z"}, "accept")
expect("VELDO-0012 AC5: THE SHIPPED INBOUND EDGE REALLY DOES NOT CARRY THE OPTION. Driving "
       "request_reconcile._settlement_record for a decision_choice acceptance produces a "
       "veldo.decision/v1 record carrying decision, decided_by and bound_digest and NO chosen "
       "key at all, and the accept word it derives is exactly the one this resolver matches on - "
       "so BLOCKED is what today's channel produces and not an unreachable state",
       "chosen" not in _BF_SHIPPED
       and _BF_SHIPPED["schema"] == BF.SETTLEMENT_SCHEMA
       and _BF_SHIPPED["decision"] == BF.SETTLEMENT_DECIDED == "decided"
       and _BF_SHIPPED["decided_by"] == "dmitry"
       and _BF_SHIPPED["bound_digest"] == _BF_DIGEST
       and sorted(_BF_RR._DECISION_WORD) == ["accept", "reject"]
       and BF.disposition_for(_BF_PIN, settlements=[_BF_SHIPPED],
                              requests=[_bf_request()])["disposition"] == BF.DISPOSITION_BLOCKED)

# THE REPORT: counts BESIDE the weakness that produced them, and a per-pin line carrying the
# reason, because a reader who cannot tell unknown from blocked will assume the first.
with tempfile.TemporaryDirectory() as _bf_rd:
    _bf_rdir = Path(_bf_rd) / ".veldo" / "floors"
    _bf_rdir.mkdir(parents=True)
    (_bf_rdir / "a.yaml").write_text(_bf_floor(
        [_BF_PIN, _bf_pin(pid="PIN-2", surface=_BF_S2, recorded=_BF_REC2,
                          reproduces="tests/test_example.py::test_render"),
         _bf_pin(pid="PIN-3", surface=".veldo/Example.kt::render", language="kotlin",
                 recorded="the Kotlin renderer returns an empty string for an empty list",
                 reproduces="app/src/test/RenderTest.kt::empty")],
        scope={"method": "by hand", "enumerated": [_BF_S1, _BF_S2, ".veldo/Example.kt::render"],
               "unreachable": [_BF_S3, ".veldo/Example.kt::send"]}))
    _BF_REP = BF.floor_report(fdir=_bf_rdir, root=Path(_bf_rd), parse=V.parse_yamlish,
                              settlements=[_bf_settlement(), _bf_settlement(
                                  digest=BF.observation_digest(
                                      _bf_pin(pid="PIN-2", surface=_BF_S2, recorded=_BF_REC2,
                                              reproduces="tests/test_example.py::test_render")),
                                  chosen="incidental", request_id="REQ-9")],
                              requests=[_bf_request()])
    expect("VELDO-0012 AC5: the report carries the pin, ruled, unknown and blocked counts BESIDE "
           "the scope block's enumerated-surface and unreachable-surface counts, so no coverage "
           "figure is quotable without the weakness that produced it, and the three disposition "
           "counts partition the pins exactly",
           (_BF_REP["pins"], _BF_REP["ruled"], _BF_REP["blocked"], _BF_REP["unknown"]) == (3, 1, 1, 1)
           and (_BF_REP["enumerated_surfaces"], _BF_REP["unreachable_surfaces"]) == (3, 2)
           and _BF_REP["ruled"] + _BF_REP["unknown"] + _BF_REP["blocked"] == _BF_REP["pins"]
           and _BF_REP["standdown"] is False)
    expect("VELDO-0012 AC5: A FLOOR NEVER REPORTS A PERCENTAGE OF AN AREA - no key is a ratio or "
           "a percentage and no value in the report is a float, because a percentage of an estate "
           "nobody enumerated is the one number this repository refuses to print",
           not any(_bf_w in _bf_k.lower() for _bf_k in _BF_REP
                   for _bf_w in ("percent", "pct", "ratio", "coverage", "share"))
           and not any(isinstance(_bf_v, float) for _bf_v in _BF_REP.values()))
    _BF_LINES = BF.report_lines(_BF_REP)
    expect("VELDO-0012 AC5: the disposition read prints, PER PIN, one of ruled, unknown or blocked "
           "WITH the reason, and the blocked line names RULING_NOT_CARRIED while the unknown line "
           "names RULING_NOT_SETTLED, so a reader can tell nobody-ruled from the-channel-is-"
           "incomplete on the page",
           len(_BF_LINES) == 5
           and "3 pin(s): 1 ruled, 1 unknown, 1 blocked" in _BF_LINES[0]
           and "NOT REACHED" in _BF_LINES[0]
           and any(BF.RULING_NOT_CARRIED in ln and " blocked" in ln for ln in _BF_LINES)
           and any(BF.RULING_NOT_SETTLED in ln and " unknown" in ln for ln in _BF_LINES))
    expect("VELDO-0012 AC5: THE LANGUAGE SCOPE IS DECLARED RATHER THAN IMPLIED. The shipped shape "
           "analyzers are PYTHON ONLY - shape_gate filters the changed set to paths ending .py "
           "before any analyzer sees them - so the report names the pin languages no shipped "
           "analyzer covers instead of letting a Kotlin pin look analyzed",
           BF.ANALYZER_LANGUAGES == ("python",)
           and BF.analyzer_supported("python") and not BF.analyzer_supported("kotlin")
           and _BF_REP["unanalyzed_languages"] == ["kotlin"]
           and any("analyzers are python only" in ln for ln in _BF_LINES)
           and 'rel.endswith(".py")' in (ROOT / ".veldo/shape_gate.py").read_text())

# ---------------------------------------------------------------------------------------
# AC6. THE FLOOR AND THE SETTLED RULINGS SIT UNDER protected_paths, BECAUSE THE VALIDATOR IS NOT
# THE INTEGRITY.
#
# FALSIFIED BY: remove the .veldo/floors/* entry from .veldo/policy.yaml and the assertion that
# policy_check.protected_patterns() returns a pattern matching .veldo/floors/example.yaml must go
# red; removing the .veldo/settlements/* entry reds the sibling assertion for a settlement path.
# Both are asserted THROUGH protected_patterns() rather than by reading the file, so the test pins
# the mechanism the gate uses and not a string in a document.
# ---------------------------------------------------------------------------------------
_BF_PATS = P.protected_patterns()


def _bf_protected(rel):
    """Whether the GATE would treat rel as a protected path, through the mechanism
    policy_check.py:439-447 actually uses (protected_patterns plus its two fnmatch forms)."""
    return [p for p in _BF_PATS
            if _bf_fn.fnmatch(rel, p) or _bf_fn.fnmatch(rel, p.rstrip("*") + "*")]


expect("VELDO-0012 AC6: policy_check.protected_patterns() returns a pattern matching "
       ".veldo/floors/example.yaml, so adding a floor or RE-POINTING AN OBSERVATION is a change "
       "that needs a commit-bound, path-scoped approval and the agent being gated cannot author "
       "the record that exempts it",
       _bf_protected(".veldo/floors/example.yaml"))
expect("VELDO-0012 AC6: and the sibling - protected_patterns() returns a pattern matching a "
       "settlement path, so WRITING A SETTLEMENT is a reviewed change too. The integrity of a "
       "disposition record is the integrity of a reviewed change plus the protected-path rules it "
       "sits under, and never its own validation",
       _bf_protected(".veldo/settlements/REQ-9-c2.json"))
expect("VELDO-0012 AC6 NEGATIVE CONTROL: the two rows above are the registration and not "
       "everything being protected - an ordinary module and an ordinary spec match NO protected "
       "pattern, while the policy file itself does, which is why this spec declares "
       "human_approval required and names .veldo/policy.yaml in its own protected_paths",
       not _bf_protected(".veldo/behavior_floor.py")
       and not _bf_protected("specs/VELDO-0012-behaviour-floor-contract.md")
       and _bf_protected(".veldo/policy.yaml"))
expect("VELDO-0012 AC6: the engine template an adopter installs carries the same two "
       "registrations, so an adopter's floor is protected from the first day rather than only "
       "this repository's. policy.yaml is a DECLARED exception to the byte-identical template "
       "sync (scripts/check_template_sync.sh), so this pair is asserted here rather than by that "
       "script - and it is the ONE row in this fragment that reads a policy file as text, "
       "because protected_patterns() only ever reads this repository's own",
       all(_bf_s in (ROOT / "engine/.veldo/policy.yaml").read_text()
           for _bf_s in ('path: ".veldo/floors/*"', 'path: ".veldo/settlements/*"'))
       and "policy.yaml" in (ROOT / "scripts/check_template_sync.sh").read_text())

# ---------------------------------------------------------------------------------------
# AC7. ADOPTION SAFE, AND IT ENFORCES NOTHING.
#
# FALSIFIED BY: delete the `if not d.is_dir(): return 0` guard at the top of check_floors_dir so
# an absent .veldo/floors/ directory RAISES instead of standing down, and the assertion that
# validate.run_all's output over this repository is byte-identical with no floors present must go
# red. That stand-down is the load-bearing leg; the second leg (no gate stage refuses on an
# unruled pin) is the derived-domain scan below.
#
# THE DECLARED FALSIFICATION IS WRONG ABOUT WHICH ROW IT REDS, AND THAT IS MEASURED RATHER THAN
# ARGUED. It assumes deleting the guard makes an absent directory RAISE. It does not: on CPython
# 3.12.3 `Path("missing").glob("*.yaml")` returns an empty iterator and raises nothing, so with the
# guard removed check_floors_dir still returns 0 and still prints nothing. The two behaviours are
# OBSERVATIONALLY IDENTICAL in run_all's (count, output), which means NO assertion over run_all's
# output can ever detect the guard's removal - not this one, and not a stronger version of it. The
# edit was driven anyway (scratch copy, diffed, suite run) and it REDS the sibling row below, the
# one asserting the stand-down was RECORDED with its reason, because that is the only observable
# the guard actually produces. Both rows are kept and neither is widened to hide the gap: the
# byte-identity row states the adoption-safety property the registration must not break, and the
# recorded-stand-down row is the one with teeth against this mutation.
# ---------------------------------------------------------------------------------------
del BF.FLOOR_STANDDOWNS[:]                     # the registry is the record; measure a clean one
_BF_RUNALL = _bf_capture(V.run_all)
# run_all NOW CARRIES THE REGISTRATION, so it records a stand-down of its own into this same
# module-level registry - BF is the CACHED instance, which is the whole point of caching it.
# Cleared again here so the row below measures ONE call's record instead of what has
# accumulated in the process: a cardinality asserted over live accumulation is the defect that
# reddens a gate the moment the thing it measures is actually wired.
del BF.FLOOR_STANDDOWNS[:]
_BF_LIVE = _bf_capture(BFC.check_floors)
_BF_WITH = ((_BF_RUNALL[0] + _BF_LIVE[0], _BF_RUNALL[1] + _BF_LIVE[1])
            if isinstance(_BF_LIVE[0], int) and isinstance(_BF_RUNALL[0], int) else None)
expect("VELDO-0012 AC7: an absent .veldo/floors/ directory stands the whole check down and "
       "returns clean, so validate.run_all's (count, output) over THIS repository is "
       "byte-identical with the check added to it - which is the property the registration line "
       "must not break. Asserted over the EXACT call run_all makes, and the registration in "
       "validate.py now exists, so run_all's own term above already contains it",
       _BF_RUNALL[0] == 0 and _BF_LIVE == (0, "") and _BF_WITH == _BF_RUNALL
       and not (ROOT / ".veldo" / "floors").exists())
expect("VELDO-0012 AC7: the stand-down is RECORDED with the reason it stood down rather than "
       "being a silent pass - a reader can tell a repository that was CHECKED from one the rule "
       "never asked anything of, and the record NAMES which of the two conditions fired",
       len(BF.floor_standdowns()) == 1
       and "no .veldo/floors/ directory" in BF.floor_standdowns()[0][1])
del BF.FLOOR_STANDDOWNS[:]
_BF_EMPTY = _bf_run(_bf_floor([], scope=None))
expect("VELDO-0012 AC7: the OTHER stand-down condition is a DIFFERENT recorded reason - a floor "
       "that declares no pins stands down naming that, and an absent directory and a pins-less "
       "floor are not the same fact",
       _BF_EMPTY == (0, "") and len(BF.floor_standdowns()) == 1
       and "declares no pins" in BF.floor_standdowns()[0][1]
       and BF.floor_standdowns()[0][1] != "no .veldo/floors/ directory")
expect("VELDO-0012 AC7 NEGATIVE CONTROL: the moment a floor EXISTS it fails closed on anything "
       "malformed, which is the other half of the same posture - so the stand-down is the absent "
       "input and not the check refusing nothing",
       _bf_run(_bf_floor([_bf_pin(status="load_bearing")]))[0] > 0
       and _bf_run(_BF_GOOD) == (0, ""))

# THE DOMAIN IS DERIVED FROM scripts/verify.sh, NOT TYPED, in the shape WARP-1409's AC6 uses. A
# universal claim over a hand-typed list is a claim about the list.
_BF_VERIFY = (ROOT / "scripts/verify.sh").read_text()
_BF_PATH_RE = r"(?:\.veldo|scripts)/[\w./-]+\.(?:py|sh)"
_BF_RUN_RE = r"(?:python3|bash|sh)\s+(%s)" % _BF_PATH_RE
_BF_REQUIRED = _bf_re.findall(r'^CHECK_(\w+)="required:(.+)"$', _BF_VERIFY, _bf_re.M)
_BF_STAGES = sorted({p for _n, _c in _BF_REQUIRED for p in _bf_re.findall(_BF_PATH_RE, _c)}
                    | set(_bf_re.findall(_BF_RUN_RE, _BF_VERIFY)))


def _bf_invokes(rel):
    """What ONE gate file EXECUTES or LOADS. An EXECUTES/LOADS edge, deliberately not a MENTIONS
    edge: a closure built on mentions would drag half the repository in and make the absence claim
    unfalsifiable in the other direction."""
    p = ROOT / rel
    if not p.is_file():
        return set()
    t = p.read_text()
    out = set(_bf_re.findall(_BF_RUN_RE, t))
    for _grp in _bf_re.findall(r'(?:ROOT|root|base|BASE)\s*/\s*((?:"[^"]+"\s*/\s*)*"[^"]+")', t):
        _cand = "/".join(_bf_re.findall(r'"([^"]+)"', _grp))
        if _cand.endswith((".py", ".sh")):
            out.add(_cand)
    return {o for o in out if o != rel}


_BF_CLOSURE = set(_BF_STAGES)
_bf_frontier = list(_BF_STAGES)
while _bf_frontier:
    for _bf_edge in _bf_invokes(_bf_frontier.pop()):
        if _bf_edge not in _BF_CLOSURE:
            _BF_CLOSURE.add(_bf_edge)
            _bf_frontier.append(_bf_edge)
_BF_TEXTS = {f: (ROOT / f).read_text() for f in sorted(_BF_CLOSURE) if (ROOT / f).is_file()}

expect("VELDO-0012 AC7: THE GATE DOMAIN IS DERIVED AND IT IS REAL, which is the precondition for "
       "any claim of the form 'no gate stage does X'. Parsed out of scripts/verify.sh: every "
       "catalog item declared required contributes a repository path, the stage set covers the "
       "six required scripts plus the three the always-run body invokes directly, the transitive "
       "closure is STRICTLY LARGER than the stage set, every member exists, and the closure "
       "reaches THIS ITEM'S OWN module through validate.py and validate_checks.py - so the "
       "absence asserted next is asserted over a domain that provably contains the wiring",
       len(_BF_REQUIRED) >= 6
       and {n for n, _c in _BF_REQUIRED} >= {"lint", "unit", "security", "generated", "docs",
                                             "extra"}
       and set(_BF_STAGES) >= {"scripts/check_lint.sh", "scripts/selftest.py",
                               "scripts/check_generated.sh", "scripts/check_docs.sh",
                               ".veldo/validate.py", ".veldo/shape_gate.py", ".veldo/events.py"}
       and _BF_CLOSURE > set(_BF_STAGES)
       and sorted(_BF_TEXTS) == sorted(_BF_CLOSURE)
       and ".veldo/validate_checks.py" in _BF_CLOSURE
       and ".veldo/behavior_floor.py" in _BF_CLOSURE)
def _bf_refs(rel, wanted):
    """Every REFERENCE to `wanted` as an identifier in one Python file's AST: a Name or an
    Attribute, so a call, a bound alias and an attribute access all count while a MENTION in a
    docstring or a comment does not.

    A SUBSTRING SCAN WAS WRONG HERE AND THE FIRST RUN PROVED IT. The wrapper's own docstring says
    it never calls the resolver, and that sentence made a string-absence row RED - a row about
    prose rather than about code, which is this project's own defect class. The closure edge is an
    EXECUTES/LOADS edge, so the absence claim over it is about identifiers, not text."""
    if not rel.endswith(".py"):
        return set()
    try:
        tree = _bf_ast.parse(_BF_TEXTS[rel])
    except SyntaxError:
        return {"UNPARSEABLE"}
    out = set()
    for node in _bf_ast.walk(tree):
        if isinstance(node, _bf_ast.Name) and node.id == wanted:
            out.add(rel)
        if isinstance(node, _bf_ast.Attribute) and node.attr == wanted:
            out.add(rel)
    return out


_BF_DISP_REFS = sorted(f for f in _BF_TEXTS if _bf_refs(f, "disposition_for"))
_BF_DISP_TEXT = sorted(f for f in _BF_TEXTS
                       if not f.endswith(".py") and "disposition_for" in _BF_TEXTS[f])
expect("VELDO-0012 AC7: NO GATE STAGE REFUSES ON A DISPOSITION STATE. Across the derived closure, "
       "the resolver disposition_for is REFERENCED AS AN IDENTIFIER in exactly ONE file - the "
       "module that defines it - by no other Python stage and by no shell stage at all, so "
       "nothing the gate runs can refuse a change because a pin is unknown or blocked. The "
       "precondition at ready and at claim is a later item, and this row reds the moment any gate "
       "file starts calling the resolver",
       _BF_DISP_REFS == [".veldo/behavior_floor.py"] and _BF_DISP_TEXT == []
       and not _bf_refs(".veldo/validate_checks.py", "disposition_for"))
expect("VELDO-0012 AC7 NEGATIVE CONTROL for the row above, in both directions. The AST scan finds "
       "real references where they exist - check_floors_dir IS referenced from the wrapper inside "
       "the closure - and the closure really does carry this item's wiring, so the absence of the "
       "resolver is a measurement rather than a scan that finds nothing anywhere",
       _bf_refs(".veldo/validate_checks.py", "check_floors_dir")
       == {".veldo/validate_checks.py"}
       and "check_floors" in _BF_TEXTS[".veldo/validate_checks.py"]
       and "behavior_floor" in _BF_TEXTS[".veldo/validate_checks.py"])

# WHAT AN ADOPTER INSTALLS IS WHAT THIS REPOSITORY RUNS. Nine estimation modules once shipped into
# engine/ with nobody comparing them, and a review inverted one of them with the gate green.
expect("VELDO-0012: the floor organ and its gate wrapper are byte-identical to the copies "
       "/veldo:init lays down, so the contract an adopter installs is the contract this "
       "repository runs",
       (ROOT / ".veldo/behavior_floor.py").read_bytes()
       == (ROOT / "engine/.veldo/behavior_floor.py").read_bytes()
       and (ROOT / ".veldo/validate_checks.py").read_bytes()
       == (ROOT / "engine/.veldo/validate_checks.py").read_bytes())

del _bf_ast, _bf_ctx, _bf_fn, _bf_io, _bf_re
