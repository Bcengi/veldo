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

THREE THINGS ABOUT WHAT THIS FRAGMENT DOES AND DOES NOT CLAIM, stated rather than hidden.

  THE REGISTRATION IN run_all EXISTS. .veldo/validate.py:832 reads
  `check_decisions() + _VC.check_floors()`, so run_all's own term below already contains the check
  and the byte-identity row is asserted over the exact call it makes.

  AC7's DECLARED FALSIFICATION IS WRONG AND IS RECORDED AS WRONG. It says deleting the stand-down
  guard from check_floors_dir makes run_all's output differ. It does not: on CPython
  `Path("missing").glob("*.yaml")` yields nothing and raises nothing, so with the guard deleted the
  function still returns 0 and still prints nothing, and NO assertion over run_all's (count, output)
  can ever see the mutation. The row with teeth against it is the RECORDED STAND-DOWN row, which
  reds because the deletion also removes the only call that records one. Measured both ways.

  THE TWO protected_paths ENTRIES ARE A HUMAN ACT, AND THE HUMAN ACTED. AC6's rows read the LIVE
  policy through policy_check.protected_patterns(), which is the mechanism the gate uses.
  Registering a protected path is itself a .veldo/policy.yaml edit; Dmitry approved these two on
  2026-08-12 and the approval is recorded, commit-bound and path-scoped at
  proof/VELDO-0012/approval-dmitry.json. Nothing here grants it and nothing here infers it.
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
_BF_CAUSE_NAMES = {BF.FLOOR_UNREADABLE, BF.PIN_FIELD_MISSING, BF.PIN_VOCAB_UNKNOWN,
                   BF.PIN_KEY_UNRECOGNIZED, BF.DIGEST_MISMATCH, BF.DUPLICATE_PIN_ID,
                   BF.SCOPE_MISSING, BF.RULING_NOT_SETTLED, BF.RULING_NOT_CARRIED,
                   BF.RULING_BINDING_MISMATCH, BF.RULING_OPTION_OFF_RECORD}
expect("VELDO-0012 AC1: the causes are ELEVEN DIFFERENT NAMES, so a refusal tells an author which "
       "one they hit rather than that a floor is invalid, and the FOUR DISPOSITION reasons are "
       "among them and distinct from every refusal cause and from each other. Pinned by EXACT SET "
       "EQUALITY rather than by a count, so adding a cause without naming it here reds this row",
       BF.CAUSES == _BF_CAUSE_NAMES and len(_BF_CAUSE_NAMES) == 11)

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
       "human's judgement about one of them does not silently rule the other. THE WORDING USED TO "
       "SAY 'can never' AND A REVIEW PRICED IT: the join is 64 bits (the row below), so the honest "
       "claim is that the observations differ and the digests differ with them, up to that bound",
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
# HOW WIDE THE JOIN IS, MEASURED, BECAUSE A REVIEW PRICED IT AND NO CLAIM HERE MAY SAY "can never".
# The digest is sha256 truncated to 16 hex characters - 64 bits - so a second preimage onto an
# EXISTING digest is 2^64 and not a practical concern, while two observations chosen AT DRAFTING TIME
# to collide is a birthday search near 2^32 over short inputs, and the drafting pass authors both
# pins. It is the REPOSITORY'S convention rather than a choice made here, which is why the row
# asserts the two widths are EQUAL rather than asserting a literal twice: widening request_digest
# alone, or this digest alone, reds it, and widening the convention in one place is the defect.
_bf_rqspec = importlib.util.spec_from_file_location("veldo_request_for_floor",
                                                    ROOT / ".veldo" / "request.py")
_BF_RQ = importlib.util.module_from_spec(_bf_rqspec)
_bf_rqspec.loader.exec_module(_BF_RQ)
_BF_OBS_HEX = BF.observation_digest(_bf_pin()).split(":")[1]
_BF_RQ_HEX = _BF_RQ.request_digest({"id": "REQ-9", "touchpoint": "decision_choice", "tier": "high",
                                    "bound_artifact": {"kind": "decision", "digest": "x"}}
                                   ).split(":")[1]
expect("VELDO-0012 AC2: THE JOIN IS 64 BITS AND THE SUITE SAYS SO RATHER THAN LEAVING IT TO A "
       "READER. observation_digest is sha256 truncated to 16 hex characters, and it is the SAME "
       "truncation .veldo/request.py uses for request_digest - asserted as an EQUALITY of the two "
       "widths, so widening either alone reds this row and one convention cannot quietly become "
       "two. What that buys is stated in the module: 2^64 to move a ruling onto an existing digest, "
       "and a birthday search near 2^32 to author two colliding observations, which is why no "
       "assertion in this fragment claims a transfer is impossible",
       len(_BF_OBS_HEX) == len(_BF_RQ_HEX) == 16
       and _bf_re.fullmatch(r"[0-9a-f]+", _BF_OBS_HEX)
       and 4 * len(_BF_OBS_HEX) == 64)

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
# THE CALL SITE, NOT ONLY THE ENUMERATION, WHICH IS WHERE A REVIEW FOUND THE HOLE. validate_floor
# returned EARLY for a pins-less floor BEFORE _validate_scope ever ran, so the scope block's closed
# key set was enforced only when the floor declared a pin: a floor carrying scope.waived_paths:
# legacy/** and scope.disposition: incidental with NO pins validated with ZERO errors and stood down
# as clean. That is the same defect one level down from the blacklist the row above replaced - the
# enumeration was closed and the CALL was conditional - and it is the artifact this design exists to
# make impossible, sitting in a protected directory reading `waived_paths: legacy/**`.
_BF_PINLESS_EXEMPT = _bf_floor([], scope={"method": "none", "waived_paths": "legacy/**",
                                          "modules_not_pinned": "billing", "ruled_by": "dmitry",
                                          "disposition": "incidental"})
_BF_PE_N, _BF_PE_OUT = _bf_run(_BF_PINLESS_EXEMPT)
expect("VELDO-0012 AC3: A FLOOR THAT DECLARES NO PINS IS NOT A HOLE IN THE CLOSED KEY SET. A "
       "pins-less floor whose scope block carries waived_paths, modules_not_pinned, ruled_by and "
       "disposition is refused by PIN_KEY_UNRECOGNIZED ONCE PER KEY, naming each - the scope block "
       "is validated whenever it is PRESENT, not only when the floor happens to pin something",
       _BF_PE_N == 4 and _BF_PE_OUT.count(BF.PIN_KEY_UNRECOGNIZED) == 4
       and all("'%s'" % _bf_k in _BF_PE_OUT for _bf_k in ("waived_paths", "modules_not_pinned",
                                                          "ruled_by", "disposition")))
expect("VELDO-0012 AC3 NEGATIVE CONTROL, ADDITIVE: a pins-less floor whose scope block is "
       "LEGITIMATE - a method plus an enumerated surface the pass reached and pinned nothing on, and "
       "an unreachable one - is still accepted printing nothing, and so is a pins-less floor with no "
       "scope block at all, so the row above is the closed key set rather than a refusal of every "
       "floor that pins nothing",
       _bf_run(_bf_floor([], scope={"method": "read every public function by hand",
                                    "enumerated": [_BF_S1], "unreachable": [_BF_S3]})) == (0, "")
       and _bf_run(_bf_floor([], scope=None)) == (0, ""))
expect("VELDO-0012 AC3: NO KEY ANYWHERE IN THE ARTIFACT CARRIES A RULING OR AN EXEMPTION, AND "
       "NONE SCOPES ONE TO A LOCATION, so a path, glob or module scoped exemption is not merely "
       "refused, it is unrepresentable. ALL FOUR closed sets are pinned by EXACT SET EQUALITY, "
       "not by a word blacklist: the blacklist alone let `modules_not_pinned` into SCOPE_KEYS and "
       "`verdict`/`ruled_by` into OBSERVATION_KEYS with this row still green, because it never "
       "listed those words - a module-scoped exemption and a ruling beside the digest it binds, "
       "both representable, both undetected. A closed set's teeth are its enumeration. NOTE the "
       "claim is deliberately narrower than 'no key addresses a location': `surface` names a file "
       "and function and `area` names an architecture area, because a floor has to say WHAT it "
       "pins. What may not exist is a key that EXEMPTS a location",
       BF.FLOOR_KEYS == {"schema", "id", "version", "area", "scope", "pins"}
       and BF.SCOPE_KEYS == {"method", "enumerated", "unreachable"}
       and BF.PIN_KEYS == {"id", "surface", "language", "fidelity", "observation", "reproduces",
                           "status"}
       and BF.OBSERVATION_KEYS == {"recorded", "digest"}
       and not any(_bf_w in _bf_k.lower()
                   for _bf_k in (BF.FLOOR_KEYS | BF.SCOPE_KEYS | BF.PIN_KEYS
                                 | BF.OBSERVATION_KEYS)
                   for _bf_w in ("path", "glob", "pattern", "dir", "file", "exempt", "waiv",
                                 "disposition", "decided", "ruling", "ruled", "module", "verdict",
                                 "judg", "allow", "legacy", "grandfather")))

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
_BF_DREF = ".veldo/decisions/d.yaml"


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


def _bf_request(status=BF.REQUEST_ACCEPTED, touchpoint=BF.REQUEST_TOUCHPOINT, rid="REQ-9",
                digest=None, ref=_BF_DREF):
    """An accepted decision_choice request BOUND TO THIS OBSERVATION by its own
    bound_artifact.digest, which is the field the receipt path copies into the settlement's
    bound_digest (.veldo/request_reconcile.py:451), so in a settlement the channel wrote the two are
    the same value. `digest` is what the transfer rows re-point to bind a DIFFERENT artifact."""
    return {"schema": BF.REQUEST_SCHEMA, "id": rid, "version": 1, "touchpoint": touchpoint,
            "tier": "high", "status": status,
            "bound_artifact": {"kind": "decision", "ref": ref,
                               "digest": _BF_DIGEST if digest is None else digest}}


def _bf_decision(chosen="load_bearing", status="decided", by="dmitry", at="2026-08-12T00:00:00Z",
                 options=None, drop=(), schema=None):
    """A veldo.decision/v1 DECISION RECORD in the shape .veldo/decision.py validates: an elaborated
    option space (each option an id, a summary and its dead_end) and a decision block A HUMAN filled
    in (chosen, decided_by, decided_at, .veldo/decision.py:176-190). This is where a ruling actually
    lives, and the resolver reads it through the request's bound_artifact.ref rather than trusting a
    key typed onto a settlement. It shares the veldo.decision/v1 schema string with the settlement
    and is a DIFFERENT shape: status decided plus a decision MAPPING, never a decision STRING."""
    rec = {"schema": BF.SETTLEMENT_SCHEMA if schema is None else schema, "id": "DEC-1",
           "version": 1, "status": status,
           "options": [{"id": o, "summary": "the %s reading of this observation" % o,
                        "dead_end": "when a later item consumes the disposition"}
                       for o in (sorted(BF.RULINGS) if options is None else options)],
           "decision": {"chosen": chosen, "decided_by": by, "decided_at": at}}
    for k in drop:
        rec["decision"].pop(k, None)
    return rec


_BF_DECS = {_BF_DREF: _bf_decision()}


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
_BF_RULED = BF.disposition_for(_BF_PIN, settlements=[_bf_settlement()],
                               requests=[_bf_request()], decisions=_BF_DECS)
expect("VELDO-0012 AC4 POSITIVE CONTROL: a settlement matching the RECOMPUTED digest, decided, "
       "with an ACCEPTED decision_choice request behind it that is BOUND TO THAT SAME DIGEST, and a "
       "decided decision record behind THAT carrying a human's chosen option, is the ONE shape that "
       "rules - so the rows above are the channel and not a resolver that never rules. THE "
       "ATTRIBUTION IS READ, NOT ASSERTED: the reason carries the decided_by and decided_at this "
       "resolver actually read off the decision record",
       _BF_RULED["disposition"] == BF.DISPOSITION_RULED
       and _BF_RULED["ruling"] == "load_bearing" and _BF_RULED["request"] == "REQ-9"
       and _BF_RULED["digest"] == _BF_DIGEST
       and "dmitry" in _BF_RULED["reason"] and "2026-08-12T00:00:00Z" in _BF_RULED["reason"])
expect("VELDO-0012 AC4: THE JOIN IS THE DIGEST AND NOTHING ELSE, so mutating the recorded "
       "observation changes the digest and the SAME settlement stops matching - a granted ruling "
       "cannot be moved onto a behaviour nobody looked at",
       BF.disposition_for(_bf_pin(recorded=_BF_REC1 + " and it also trims tabs"),
                          settlements=[_bf_settlement()], requests=[_bf_request()],
                          decisions=_BF_DECS)["disposition"] == BF.DISPOSITION_UNKNOWN
       and BF.disposition_for(_bf_pin(surface=_BF_S2), settlements=[_bf_settlement()],
                              requests=[_bf_request()],
                              decisions=_BF_DECS)["disposition"] == BF.DISPOSITION_UNKNOWN)
# AND WHAT THE JOIN DOES NOT COVER, DRIVEN RATHER THAN LEFT FOR A LATER READER TO DISCOVER. A review
# measured that OBSERVATION_DIGEST_FIELDS is (surface, recorded), so fidelity and reproduces sit
# OUTSIDE it: after a human rules, the machine may flip fidelity exact -> proxy and re-point
# reproduces at a test that asserts nothing, and the SAME settlement still rules the pin. That is the
# declared choice - the tuple is pinned by exact equality above - and the spec's notes now say it
# plainly instead of claiming the digest makes the reproduces reference load bearing. It is asserted
# HERE, as a consequence with teeth, so the item that decides whether either field enters the digest
# AMENDS this row deliberately rather than discovering the property afterwards. Putting fidelity in
# the tuple reds this row, which is the point.
_BF_LOOSE = _bf_pin(fidelity="proxy", reproduces="tests/test_nothing.py::test_always_passes")
_BF_LOOSE_D = BF.disposition_for(_BF_LOOSE, settlements=[_bf_settlement()],
                                 requests=[_bf_request()], decisions=_BF_DECS)
expect("VELDO-0012 AC4: THE DIGEST COVERS THE OBSERVATION, NOT THE PIN'S CLAIMS ABOUT ITSELF. A pin "
       "whose fidelity is flipped from exact to proxy and whose reproduces is re-pointed at a test "
       "that asserts nothing has a BYTE-IDENTICAL digest and is STILL ruled load_bearing by the same "
       "settlement - so a granted ruling survives a rewrite of both fields, and the contract does "
       "NOT pretend the human's judgement covered them. What the digest makes immovable is the "
       "OBSERVATION, asserted by the join row above",
       BF.observation_digest(_BF_LOOSE) == _BF_DIGEST
       and _BF_LOOSE_D["disposition"] == BF.DISPOSITION_RULED
       and _BF_LOOSE_D["ruling"] == "load_bearing" == _BF_RULED["ruling"]
       and BF.OBSERVATION_DIGEST_FIELDS == ("surface", "recorded"))

# THE TRANSFER LEG, WHICH IS THE HARM THIS ITEM EXISTS TO PREVENT AND WHICH A REVIEW FOUND OPEN.
# The resolver used to check the named request for schema, id, touchpoint and status ONLY, and never
# compared the request's OWN bound_artifact.digest to the recomputed observation digest - so a
# settlement could name a REAL accepted decision_choice request that a human settled about a
# DIFFERENT artifact, and it ruled this pin. The comparison is free: the receipt path SETS a
# settlement's bound_digest from that exact field (.veldo/request_reconcile.py:451).
_BF_XFER = BF.disposition_for(_BF_PIN, settlements=[_bf_settlement(chosen="incidental")],
                              requests=[_bf_request(digest="sha256:deadbeefdeadbeef")],
                              decisions=_BF_DECS)
expect("VELDO-0012 AC4: A RULING NEVER TRANSFERS FROM ANOTHER ARTIFACT. A settlement carrying THIS "
       "observation's digest that names a REAL accepted decision_choice request bound to a "
       "DIFFERENT artifact rules NOTHING: the pin is unknown and the reason names "
       "RULING_BINDING_MISMATCH, the request, and BOTH digests, because a settlement whose "
       "bound_digest disagrees with the request's own binding was not written by the channel from "
       "that request",
       _BF_XFER["disposition"] == BF.DISPOSITION_UNKNOWN
       and _BF_XFER["ruling"] is None
       and BF.RULING_BINDING_MISMATCH in _BF_XFER["reason"]
       and "REQ-9" in _BF_XFER["reason"]
       and "sha256:deadbeefdeadbeef" in _BF_XFER["reason"] and _BF_DIGEST in _BF_XFER["reason"])
expect("VELDO-0012 AC4 NEGATIVE CONTROL for the transfer row, and it is ADDITIVE: the SAME "
       "settlement and the SAME decision record with the request's binding RESTORED to this "
       "observation's digest rules again, and a mismatch is a DIFFERENT NAME from nobody having "
       "ruled at all - so the row above is the binding comparison and not a resolver that stopped "
       "resolving",
       BF.disposition_for(_BF_PIN, settlements=[_bf_settlement(chosen="incidental")],
                          requests=[_bf_request()],
                          decisions={_BF_DREF: _bf_decision(chosen="incidental")}
                          )["disposition"] == BF.DISPOSITION_RULED
       and BF.RULING_BINDING_MISMATCH != BF.RULING_NOT_SETTLED
       and BF.RULING_NOT_SETTLED in _BF_FORGED["reason"]
       and BF.RULING_BINDING_MISMATCH not in _BF_FORGED["reason"])

# THE FORGED OPTION, THE OTHER HALF OF THE SAME REVIEW FINDING. The resolver used to read a
# top-level `chosen` key off the settlement AT FACE VALUE, and the shipped receipt path writes no
# option at all - so the only reachable route to `ruled` was a record no shipped writer can produce,
# and writing one by hand produced a reason asserting "an attributed human" nobody had read.
_BF_OFFREC = BF.disposition_for(_BF_PIN, settlements=[_bf_settlement(chosen="incidental")],
                                requests=[_bf_request()], decisions={})
expect("VELDO-0012 AC4: AN OPTION TYPED ONTO A SETTLEMENT IS NOT A RULING. A settlement carrying "
       "chosen: incidental whose request binds NO decided decision record BLOCKS by name with "
       "RULING_OPTION_OFF_RECORD, names the option it refused to take, and rules nothing - the "
       "shipped receipt path writes decision, decided_by and bound_digest and no option AT ALL, so "
       "an option sitting here was typed rather than settled through the channel",
       _BF_OFFREC["disposition"] == BF.DISPOSITION_BLOCKED
       and _BF_OFFREC["ruling"] is None
       and BF.RULING_OPTION_OFF_RECORD in _BF_OFFREC["reason"]
       and "incidental" in _BF_OFFREC["reason"]
       and BF.RULING_OPTION_OFF_RECORD != BF.RULING_NOT_CARRIED)
expect("VELDO-0012 AC4: the settlement's option is COMPARED, never trusted and never ignored. It "
       "is accepted only as a CORROBORATION of the option the decision record carries: the same "
       "option rules, a DIFFERENT one from the record's blocks by the same name rather than letting "
       "either record win, and no option at all leaves the record's own option ruling",
       BF.disposition_for(_BF_PIN, settlements=[_bf_settlement(chosen="load_bearing")],
                          requests=[_bf_request()],
                          decisions=_BF_DECS)["disposition"] == BF.DISPOSITION_RULED
       and BF.RULING_OPTION_OFF_RECORD in BF.disposition_for(
           _BF_PIN, settlements=[_bf_settlement(chosen="defect")], requests=[_bf_request()],
           decisions=_BF_DECS)["reason"]
       and BF.disposition_for(_BF_PIN, settlements=[_bf_settlement()], requests=[_bf_request()],
                              decisions=_BF_DECS)["ruling"] == "load_bearing")
for _bf_label, _bf_dec in (
        ("a decision record that is still a DRAFT", _bf_decision(status="draft")),
        ("a decision record whose chosen option is not one it DECLARES",
         _bf_decision(chosen="load_bearing", options=["incidental", "defect"])),
        ("a decision record whose chosen option is outside the RULING vocabulary",
         _bf_decision(chosen="probably_fine", options=["probably_fine"])),
        ("a decision record with no decided_by", _bf_decision(drop=("decided_by",))),
        ("a decision record with no decided_at", _bf_decision(drop=("decided_at",))),
        ("a request pointed at a SETTLEMENT rather than a decision record",
         _bf_settlement(chosen="load_bearing"))):
    _bf_d = BF.disposition_for(_BF_PIN, settlements=[_bf_settlement()], requests=[_bf_request()],
                              decisions={_BF_DREF: _bf_dec})
    expect("VELDO-0012 AC4: %s carries no ruling - the pin BLOCKS with RULING_NOT_CARRIED and is "
           "NEVER ruled, because the option must resolve to one of the record's own declared "
           "options, to a member of the ruling vocabulary, and to a human who is named with a "
           "date" % _bf_label,
           _bf_d["disposition"] == BF.DISPOSITION_BLOCKED and _bf_d["ruling"] is None
           and BF.RULING_NOT_CARRIED in _bf_d["reason"])
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
    (_bf_root / ".veldo" / "decisions").mkdir(parents=True)
    (_bf_root / ".veldo" / "settlements" / "REQ-9-c2.json").write_text(
        json.dumps(_bf_settlement(), indent=2, sort_keys=True))
    (_bf_root / ".veldo" / "requests" / "REQ-9.yaml").write_text(
        "\n".join(_bf_emit(_bf_request(), 0)) + "\n")
    (_bf_root / _BF_DREF).write_text(
        "\n".join(_bf_emit(_bf_decision(chosen="defect"), 0)) + "\n")
    _bf_fs = BF.disposition_for(_BF_PIN, root=_bf_root, parse=V.parse_yamlish)
    expect("VELDO-0012 AC4: the resolver reads the REAL record paths the receipt path writes - a "
           "settlement under .veldo/settlements/, its request under .veldo/requests/ and the "
           "decision record that request BINDS all resolve through the filesystem, not only "
           "through injected dicts, and the ruling is the option the record carries",
           _bf_fs["disposition"] == BF.DISPOSITION_RULED and _bf_fs["ruling"] == "defect")
    (_bf_root / _BF_DREF).unlink()
    expect("VELDO-0012 AC4: delete the DECISION RECORD and the same settlement and request on disk "
           "stop ruling - they BLOCK, because a human settled something here and no record says "
           "which way, which is the state the shipped channel produces today",
           BF.disposition_for(_BF_PIN, root=_bf_root,
                              parse=V.parse_yamlish)["disposition"] == BF.DISPOSITION_BLOCKED)
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
                                 requests=[_bf_request()], decisions={})
expect("VELDO-0012 AC5: a settlement that matches the pin by digest, is decided, and has an "
       "ACCEPTED decision_choice request bound to that same digest behind it, while NOTHING it "
       "binds carries an option, resolves to BLOCKED with RULING_NOT_CARRIED - never to a ruling, "
       "never to a default. This is PLAN-0016's own no-bypass rule applied rather than routed "
       "around",
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
expect("VELDO-0012 AC5: a chosen option OUTSIDE the ruling vocabulary blocks rather than being "
       "taken at face value - it is refused as an option no record declares "
       "(RULING_OPTION_OFF_RECORD) - and the reason of the carried-nothing state names the three "
       "options the repository would have accepted",
       BF.disposition_for(_BF_PIN, settlements=[_bf_settlement(chosen="probably_fine")],
                          requests=[_bf_request()],
                          decisions=_BF_DECS)["disposition"] == BF.DISPOSITION_BLOCKED
       and BF.RULING_OPTION_OFF_RECORD in BF.disposition_for(
           _BF_PIN, settlements=[_bf_settlement(chosen="probably_fine")], requests=[_bf_request()],
           decisions=_BF_DECS)["reason"]
       and "load_bearing" in _BF_BLOCKED["reason"])
# THE CLAIM ABOUT THE SHIPPED CHANNEL, DRIVEN RATHER THAN QUOTED. AC5's whole premise is that the
# inbound edge writes no chosen option; asserting that against the real module is what makes
# BLOCKED the honest reading today instead of a state nothing can reach.
_bf_rrspec = importlib.util.spec_from_file_location("veldo_request_reconcile_for_floor",
                                                    ROOT / ".veldo" / "request_reconcile.py")
_BF_RR = importlib.util.module_from_spec(_bf_rrspec)
_bf_rrspec.loader.exec_module(_BF_RR)
_BF_RR_SRC = (ROOT / ".veldo" / "request_reconcile.py").read_text()
_BF_SHIPPED = _BF_RR._settlement_record(
    {"id": "REQ-9", "touchpoint": "decision_choice"}, ["dmitry"], _BF_DIGEST, "c2",
    {"ts": "2026-08-11T00:00:00Z"}, "accept")
expect("VELDO-0012 AC5: THE SHIPPED INBOUND EDGE REALLY DOES NOT CARRY THE OPTION. Driving "
       "request_reconcile._settlement_record for a decision_choice acceptance produces a "
       "veldo.decision/v1 record carrying decision, decided_by and bound_digest and NO chosen "
       "key at all, and the accept word it derives is exactly the one this resolver matches on - "
       "so BLOCKED is what today's channel produces and not an unreachable state",
       BF.SETTLEMENT_OPTION_KEY not in _BF_SHIPPED
       and _BF_SHIPPED["schema"] == BF.SETTLEMENT_SCHEMA
       and _BF_SHIPPED["decision"] == BF.SETTLEMENT_DECIDED == "decided"
       and _BF_SHIPPED["decided_by"] == "dmitry"
       and _BF_SHIPPED["bound_digest"] == _BF_DIGEST
       and sorted(_BF_RR._DECISION_WORD) == ["accept", "reject"]
       and BF.disposition_for(_BF_PIN, settlements=[_BF_SHIPPED], requests=[_bf_request()],
                              decisions={})["disposition"] == BF.DISPOSITION_BLOCKED)
# AND THE OTHER HALF OF THE SAME CLAIM, WHICH IS WHY AN OPTION ON A SETTLEMENT BLOCKS. The shipped
# writer takes the settlement's bound_digest STRAIGHT from the request's bound_artifact.digest, so
# comparing the request's binding to the recomputed observation digest costs nothing and is exactly
# what makes a transferred ruling unrepresentable. Driven against the real module rather than quoted.
expect("VELDO-0012 AC4: THE COMPARISON THIS RESOLVER ADDED IS FREE, DRIVEN AGAINST THE SHIPPED "
       "WRITER. request_reconcile._settlement_record sets bound_digest to the digest it is handed, "
       "which the reconcile reads out of the request's own bound_artifact (the `displayed` value), "
       "so a channel-written settlement and its request always agree - and the resolver's new "
       "binding check therefore refuses only the pairs the channel could not have produced",
       _BF_RR._settlement_record({"id": "REQ-9", "touchpoint": "decision_choice"}, ["dmitry"],
                                 "sha256:1234567812345678", "c2",
                                 {"ts": "2026-08-11T00:00:00Z"},
                                 "accept")["bound_digest"] == "sha256:1234567812345678"
       and "bound_artifact" in _bf_re.search(r"displayed = .*", _BF_RR_SRC).group(0)
       and "digest" in _bf_re.search(r"displayed = .*", _BF_RR_SRC).group(0))

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
    _BF_PIN2_DIGEST = BF.observation_digest(
        _bf_pin(pid="PIN-2", surface=_BF_S2, recorded=_BF_REC2,
                reproduces="tests/test_example.py::test_render"))
    _BF_REP = BF.floor_report(fdir=_bf_rdir, root=Path(_bf_rd), parse=V.parse_yamlish,
                              settlements=[_bf_settlement(),
                                           _bf_settlement(digest=_BF_PIN2_DIGEST,
                                                          request_id="REQ-10")],
                              requests=[_bf_request(),
                                        _bf_request(rid="REQ-10", digest=_BF_PIN2_DIGEST,
                                                    ref=".veldo/decisions/d2.yaml")],
                              decisions={".veldo/decisions/d2.yaml":
                                         _bf_decision(chosen="incidental")})
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

# AN UNREADABLE FLOOR IS NAMED, NOT DROPPED BEHIND THE COUNTS. floor_report has no reporter of
# its own, so the `except FloorRecordError: continue` in its read loop used to drop the file and
# then quote pin and surface counts computed over whatever parsed - a coverage figure without the
# weakness that produced it, which is exactly what this report's own contract forbids. Driven with
# two floors on disk, one of them unparseable: the counts must come from the ONE that parsed AND
# the report must name the one that did not, in the dict and on the page.
with tempfile.TemporaryDirectory() as _bf_ud:
    _bf_udir = Path(_bf_ud) / ".veldo" / "floors"
    _bf_udir.mkdir(parents=True)
    (_bf_udir / "good.yaml").write_text(_bf_floor([_bf_pin()]))
    (_bf_udir / "broken.yaml").write_text("schema: veldo.behavior_floor/v1\npins:\n\t- nope\n")
    _BF_UREP = BF.floor_report(fdir=_bf_udir, root=Path(_bf_ud), parse=V.parse_yamlish,
                               settlements=[], requests=[])
    _BF_ULINES = BF.report_lines(_BF_UREP)
    expect("VELDO-0012 AC5: A FLOOR THAT COULD NOT BE READ IS COUNTED AND NAMED, and the pin and "
           "surface counts beside it are the ones from the floors that DID parse - so the report "
           "cannot quote coverage while silently omitting a file, which is the defect its own "
           "contract names. NEGATIVE CONTROL: the readable floor's pin still counts, so naming the "
           "unreadable one is not achieved by refusing the whole report",
           _BF_UREP["unreadable"] == ["broken.yaml"]
           and (_BF_UREP["floors"], _BF_UREP["pins"]) == (1, 1)
           and _BF_UREP["standdown"] is False
           and any("COULD NOT BE READ" in ln and "broken.yaml" in ln for ln in _BF_ULINES))

# AND ONE EXTENSION AWAY FROM IT, WHICH IS WHERE A REVIEW FOUND THE SAME DEFECT STILL OPEN. Every
# reader iterated `*.yaml`, so a floor written as contracts.yml was not validated, not counted, not
# named and not reported: a human reading a PROTECTED directory saw a signed-off exemption that the
# machine reported as absent, which is the confident zero the row above exists to refuse.
with tempfile.TemporaryDirectory() as _bf_yd:
    _bf_ydir = Path(_bf_yd) / ".veldo" / "floors"
    _bf_ydir.mkdir(parents=True)
    (_bf_ydir / "good.yaml").write_text(_bf_floor([_bf_pin()]))
    (_bf_ydir / "contracts.yml").write_text(
        "schema: %s\nid: FLOOR-yml\nversion: 1\nstatus: load_bearing\ndecided_by: dmitry\n"
        "reason: the whole legacy tree is incidental, signed off\nexempt_paths: legacy/**\n"
        % BF.SCHEMA)
    (_bf_ydir / "archive").mkdir()
    _BF_YN, _BF_YOUT = _bf_capture(lambda: BFC.check_floors(floors_dir=_bf_ydir,
                                                           root=Path(_bf_yd)))
    expect("VELDO-0012 AC1: AN ENTRY THE *.yaml RULE DOES NOT CLAIM IS REFUSED BY NAME, never "
           "skipped - a floor written as contracts.yml and a subdirectory parked beside the floors "
           "are each named with FLOOR_UNREADABLE, because a record in a protected directory that no "
           "reader validates, counts or names is an input the machine reports as absent",
           _BF_YN == 2 and _BF_YOUT.count(BF.FLOOR_UNREADABLE) == 2
           and "contracts.yml" in _BF_YOUT and "archive" in _BF_YOUT)
    expect("VELDO-0012 AC1 NEGATIVE CONTROL, ADDITIVE: the well-formed good.yaml sitting in the "
           "SAME directory is still accepted - it contributes no refusal of its own and its pin is "
           "still counted by the report - so the row above is the unclaimed entry and not the check "
           "refusing a directory that contains anything unusual",
           _bf_run(_bf_floor([_bf_pin()])) == (0, "")
           and BF.unclaimed_entries(_bf_ydir) == ["archive", "contracts.yml"])
    _BF_YREP = BF.floor_report(fdir=_bf_ydir, root=Path(_bf_yd), parse=V.parse_yamlish,
                               settlements=[], requests=[])
    _BF_YLINES = BF.report_lines(_BF_YREP)
    expect("VELDO-0012 AC5: THE REPORT NAMES WHAT IT DID NOT READ. The unclaimed entries appear in "
           "the report dict and on the page BESIDE the counts, and the counts themselves are the "
           "ones from the floors the rule DID claim, so no coverage figure is quotable while an "
           "input sits unread next to it",
           _BF_YREP["unclaimed"] == ["archive", "contracts.yml"]
           and (_BF_YREP["floors"], _BF_YREP["pins"]) == (1, 1)
           and _BF_YREP["standdown"] is False
           and any("NOT CLAIMED" in ln and "contracts.yml" in ln and "archive" in ln
                   for ln in _BF_YLINES))
with tempfile.TemporaryDirectory() as _bf_yd2:
    _bf_ydir2 = Path(_bf_yd2) / ".veldo" / "floors"
    _bf_ydir2.mkdir(parents=True)
    (_bf_ydir2 / "contracts.yml").write_text("schema: %s\nid: F\nversion: 1\n" % BF.SCHEMA)
    _BF_Y2REP = BF.floor_report(fdir=_bf_ydir2, root=Path(_bf_yd2), parse=V.parse_yamlish,
                                settlements=[], requests=[])
    expect("VELDO-0012 AC5: AND THE STAND-DOWN OVER AN UNREAD INPUT IS NOT A ZERO. A floors "
           "directory holding ONLY a file the *.yaml rule does not claim still stands down, and the "
           "stand-down reason NAMES the file rather than reporting that no floor declares a pin, "
           "because a stand-down measured over an input nobody read is exactly the confident zero "
           "this report refuses to print",
           _BF_Y2REP["standdown"] is True
           and _BF_Y2REP["unclaimed"] == ["contracts.yml"]
           and "contracts.yml" in _BF_Y2REP["reason"]
           and "not a zero" in _BF_Y2REP["reason"]
           and any("contracts.yml" in ln for ln in BF.report_lines(_BF_Y2REP)))

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
       ".veldo/floors/example.yaml, so COMMITTING a floor or a RE-POINTED OBSERVATION is a change "
       "that needs a commit-bound, path-scoped approval and the agent being gated cannot LAND the "
       "record that exempts it. The verb is committing because the boundary row below measures why",
       _bf_protected(".veldo/floors/example.yaml"))
expect("VELDO-0012 AC6: and the sibling - protected_patterns() returns a pattern matching a "
       "settlement path, so COMMITTING A SETTLEMENT is a reviewed change too. The integrity of a "
       "disposition record is the integrity of a reviewed change plus the protected-path rules it "
       "sits under, and never its own validation",
       _bf_protected(".veldo/settlements/REQ-9-c2.json"))
# THE BOUNDARY OF THE CONTROL, MEASURED, BECAUSE THE CRITERION'S CLAIM USED TO OUTRUN IT. The
# enforcement at policy_check.py:439-447 iterates changed_files(), which is
# `git diff --name-only <base>` (:92-99), so it lists modifications to TRACKED files and never
# untracked ones: an agent that WRITES a floor and a settlement and does not commit them is matched
# by the pattern and never reaches the check. Driven in a throwaway repository against the LIVE
# patterns, with a committed-and-modified floor as the ADDITIVE control in the same fixture, so the
# row measures the boundary in BOTH directions rather than asserting one of them. NOTHING HERE
# REFUSES AN UNTRACKED FLOOR: a floor is authored before it is committed, and a check that reddened
# on that would be refusing the feature rather than gating it. What the boundary buys is written into
# AC6 as a requirement on the CONSUMER - a precondition built on a disposition must require the
# record to be TRACKED - and the enumeration itself belongs to .veldo/policy_check.py, where it is
# one reader to build once rather than four patches, and where it has the same boundary for
# .veldo/secret_inventory.json.
with tempfile.TemporaryDirectory() as _bf_gd:
    _bf_gr = Path(_bf_gd)
    for _bf_argv in (["init", "-q", "-b", "main", "."],
                     ["-c", "user.email=a@b", "-c", "user.name=a", "commit", "-q", "--allow-empty",
                      "-m", "base"]):
        subprocess.run(["git"] + _bf_argv, cwd=_bf_gd, capture_output=True, text=True, check=True)
    (_bf_gr / ".veldo" / "floors").mkdir(parents=True)
    (_bf_gr / ".veldo" / "settlements").mkdir(parents=True)
    (_bf_gr / ".veldo/floors/committed.yaml").write_text(_bf_floor([_bf_pin()]))
    subprocess.run(["git", "add", "-A"], cwd=_bf_gd, capture_output=True, text=True, check=True)
    subprocess.run(["git", "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-q", "-m",
                    "the floor a human reviewed"], cwd=_bf_gd, capture_output=True, text=True,
                   check=True)
    # the three acts AC6 is about: one on a TRACKED record, two on records nobody staged
    (_bf_gr / ".veldo/floors/committed.yaml").write_text(
        _bf_floor([_bf_pin(recorded=_BF_REC1 + ", and it also trims tabs")]))
    (_bf_gr / ".veldo/floors/smuggled.yaml").write_text(_bf_floor([_bf_pin(pid="PIN-S")]))
    (_bf_gr / ".veldo/settlements/forged.json").write_text(json.dumps(_bf_settlement(), indent=2))
    _BF_ENUM = [f for f in subprocess.run(["git", "diff", "--name-only", "HEAD"], cwd=_bf_gd,
                                          capture_output=True, text=True).stdout.splitlines() if f]
    expect("VELDO-0012 AC6: THE CONTROL IS OVER A COMMITTED CHANGE, AND THE BOUNDARY IS MEASURED "
           "RATHER THAN ASSUMED. All three of a modified TRACKED floor, an untracked floor and an "
           "untracked settlement match a live protected pattern, and the enumeration the enforcement "
           "iterates - `git diff --name-only HEAD`, which is what changed_files() runs - contains "
           "ONLY the tracked one. So the pattern is not what fails: an untracked record never reaches "
           "the check, which is why AC6 says committing and why a consumer of a disposition must "
           "require a TRACKED record. ADDITIVE CONTROL in the same fixture: the tracked floor's edit "
           "IS enumerated and IS matched, so protection over a committed change is proven working by "
           "the same measurement",
           _bf_protected(".veldo/floors/committed.yaml")
           and _bf_protected(".veldo/floors/smuggled.yaml")
           and _bf_protected(".veldo/settlements/forged.json")
           and _BF_ENUM == [".veldo/floors/committed.yaml"])
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
# THE STAND-DOWN AND ITS RECORD ARE PROVEN UNCONDITIONALLY, over a directory that CANNOT
# exist, so this leg holds whatever this repository itself happens to contain. It used to be
# driven over the live .veldo/floors/ and paired with `not (...).exists()`, which pinned today's
# emptiness: writing one valid floor - USING the feature - took the suite from 3 failed to 4.
# An assertion measured over the live repository may never require the measured set to be empty.
del BF.FLOOR_STANDDOWNS[:]
with tempfile.TemporaryDirectory() as _bf_nodir:
    _BF_ABSENT = _bf_capture(lambda: BFC.check_floors(
        floors_dir=Path(_bf_nodir) / "floors", root=Path(_bf_nodir)))
expect("VELDO-0012 AC7: an absent floors directory stands the whole check down, returns clean, "
       "AND the stand-down is RECORDED with the reason that fired - so a reader can tell a "
       "repository that was CHECKED from one the rule never asked anything of. Driven over a "
       "path that cannot exist, so nothing here depends on what this repository holds",
       _BF_ABSENT == (0, "")
       and len(BF.floor_standdowns()) == 1
       and "no .veldo/floors/ directory" in BF.floor_standdowns()[0][1])

# The live half: adding the check to run_all must not change run_all's (count, output). That
# property holds in BOTH states - absent, it stands down; present and valid, it validates and
# still adds nothing - so the row states the property and REPORTS which state it measured
# instead of requiring one of them.
del BF.FLOOR_STANDDOWNS[:]
_BF_RUNALL = _bf_capture(V.run_all)
# run_all NOW CARRIES THE REGISTRATION, so it records a stand-down of its own into this same
# module-level registry - BF is the CACHED instance, which is the whole point of caching it.
# Cleared again so the term below measures ONE call rather than process-wide accumulation.
del BF.FLOOR_STANDDOWNS[:]
_BF_LIVE = _bf_capture(BFC.check_floors)
_BF_WITH = ((_BF_RUNALL[0] + _BF_LIVE[0], _BF_RUNALL[1] + _BF_LIVE[1])
            if isinstance(_BF_LIVE[0], int) and isinstance(_BF_RUNALL[0], int) else None)
expect("VELDO-0012 AC7: validate.run_all's (count, output) over THIS repository is byte-identical "
       "with the check added to it, which is the property the registration line must not break. "
       "Asserted over the EXACT call run_all makes. MEASURED IN WHATEVER STATE THIS REPOSITORY IS "
       "IN and the state is reported rather than required: .veldo/floors/ present here = %r"
       % (ROOT / ".veldo" / "floors").is_dir(),
       _BF_RUNALL[0] == 0 and _BF_LIVE == (0, "") and _BF_WITH == _BF_RUNALL)
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
expect("VELDO-0012 AC7: NO GATE STAGE READS A DISPOSITION AT ALL, WHICH IS WHY NONE CAN REFUSE ON "
       "ONE. Across the derived closure, the resolver disposition_for is REFERENCED AS AN IDENTIFIER "
       "in exactly ONE file - the module that defines it - by no other Python stage and by no shell "
       "stage at all. WHAT THIS IS AND IS NOT: not-read is STRICTLY STRONGER than not-refused-on, so "
       "it proves the criterion and then some, and a later item that adds a legitimate non-refusing "
       "READER will red this row and must amend it rather than route around it. It is also NARROWER "
       "than the criterion in one direction, stated so nothing reads wider than it is: a stage could "
       "in principle refuse by scanning a floor's text for `status:` without touching the resolver, "
       "which this row does not exclude and the next clause is why it does not need to - the floor "
       "check itself enforces nothing beyond well-formedness, asserted above",
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
