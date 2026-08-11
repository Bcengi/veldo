"""WARP-0717: the subset runner, and the structural reason a partial run cannot verify.

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest
order, like every other fragment. It holds no fixture of its own beyond what it builds in a
temporary tree.

Run it: `python3 scripts/selftest.py --suite 14_warp_0717_subset_runner` runs this fragment
plus its declared prerequisite closure, which is itself alone.

WHAT IS OBSERVED HERE, and how, because the how is the whole point of AC2. The three
verification-bearing acts are ATTEMPTED on a partial scope and the refusal is asserted BY
NAME. Nothing here greps the source for the absence of a call: an absent call is a fact
about today's text, and a raised refusal is a fact about the behaviour. Each refusal is
paired with its positive control on a FULL scope, so a scope that refused everything
unconditionally would red these rather than pass them.

THE FULL PATH IS DRIVEN TOO, in a hermetic fixture tree holding byte-identical copies of
the dispatcher and the scope module over a two-fragment manifest, with .veldo symlinked so
shared.py loads the real validators. That fixture is what lets a FULL run, which must emit
the aggregate line and exit 0, be observed here in milliseconds instead of ninety seconds.
"""
import re as _w17_re
import shutil as _w17_shutil

_W17_REFUSAL = "PARTIAL_RUN_CANNOT_VERIFY"
_w17_scripts = ROOT / "scripts"
_w17_suites = _w17_scripts / "suites"

_w17_rs_spec = importlib.util.spec_from_file_location(
    "w17_run_scope", _w17_scripts / "run_scope.py")
_W17RS = importlib.util.module_from_spec(_w17_rs_spec)
_w17_rs_spec.loader.exec_module(_W17RS)

_w17_manifest = json.loads((_w17_suites / "manifest.json").read_text())
_w17_names = [s["name"] for s in _W17RS.fragments(_w17_manifest)]
_w17_requires = _W17RS.load_requires()


def _w17_raises(fn, *a, **kw):
    """(raised, message) for one attempt. The MESSAGE is what carries the refusal name, so
    it is returned rather than only the boolean: an assertion that something raised, without
    checking WHAT, would pass on an unrelated TypeError."""
    try:
        fn(*a, **kw)
    except BaseException as e:
        return True, "%s: %s" % (type(e).__name__, e)
    return False, ""


# ---------------------------------------------------------------------------------------
# AC2. THE THREE ACTS, ATTEMPTED ON A PARTIAL SCOPE, REFUSED BY NAME.
# The scope under test is built the way the dispatcher builds one for `--suite`, and the
# SELECTOR is what makes it partial. Note the second scope: it names EVERY suite and is
# still partial, because a run that went through a selector must not be able to claim
# verification just because the selector happened to reach everything.
# ---------------------------------------------------------------------------------------
_w17_partial = _W17RS.RunScope("--suite %s" % _w17_names[0], [_w17_names[0]], _w17_names)
_w17_partial_all = _W17RS.RunScope("--suite " + ",".join(_w17_names), _w17_names, _w17_names)
_w17_full = _W17RS.full_scope(_w17_manifest)

expect("WARP-0717 AC2: a PARTIAL run ASKED FOR THE AGGREGATE SUMMARY LINE is REFUSED BY "
       "NAME. The attempt is made, not described: scope.aggregate_line(3, 0) is CALLED on a "
       "scope built from a selector and it raises, and the exception message carries "
       "PARTIAL_RUN_CANNOT_VERIFY. This is the line the gate and the operator guide parse, "
       "so a partial run that reached it would be indistinguishable in a pasted log from a "
       "full one",
       all([_w17_raises(_w17_partial.aggregate_line, 3, 0)[0],
            _W17_REFUSAL in _w17_raises(_w17_partial.aggregate_line, 3, 0)[1]]))

expect("WARP-0717 AC2: a PARTIAL run ASKED TO WRITE THE VERIFY STAMP is REFUSED BY NAME. "
       "scope.verify_stamp_payload(...) is CALLED and raises with PARTIAL_RUN_CANNOT_VERIFY "
       "in the message. Declared honestly in run_scope.py's docstring and repeated here: "
       "this method has no production caller, because .veldo/last_verify is written by "
       "scripts/verify.sh IN SHELL. The present-day protection is the exit code, asserted "
       "below; this refusal is what the first Python-side stamp writer will hit",
       all([_w17_raises(_w17_partial.verify_stamp_payload, "abc", "green", "t", 4, 18)[0],
            _W17_REFUSAL in _w17_raises(
                _w17_partial.verify_stamp_payload, "abc", "green", "t", 4, 18)[1]]))

expect("WARP-0717 AC2: a PARTIAL run ASKED TO SATISFY THE REQUIRED-EVIDENCE CHECK is "
       "REFUSED BY NAME. scope.unit_evidence_check(0) is CALLED and raises with "
       "PARTIAL_RUN_CANNOT_VERIFY. Same honest caveat as the stamp: proof artifacts are "
       "written by hand today, so this is the guard the first GENERATED unit-evidence "
       "record hits, and nothing in a test suite can stop a human typing one",
       all([_w17_raises(_w17_partial.unit_evidence_check, 0)[0],
            _W17_REFUSAL in _w17_raises(_w17_partial.unit_evidence_check, 0)[1]]))

expect("WARP-0717 AC2: PARTIALITY IS DECIDED BY THE SELECTOR AND NOT BY HOW MUCH RAN, so a "
       "selector that names EVERY suite is still refused all three acts. Without this a "
       "`--suite a,b,c,...` listing the whole manifest would be a laundering route straight "
       "back to a claimable run",
       all(_w17_raises(fn, *args)[0] and _W17_REFUSAL in _w17_raises(fn, *args)[1]
           for fn, args in ((_w17_partial_all.aggregate_line, (3, 0)),
                            (_w17_partial_all.verify_stamp_payload, ("a", "green", "t", 1, 1)),
                            (_w17_partial_all.unit_evidence_check, (0,)))))

# The positive controls. A scope that refused unconditionally would satisfy every assertion
# above and be useless, so each act is also driven on a FULL scope and its RESULT checked.
expect("WARP-0717 AC2 NON-VACUITY: the FULL scope PRODUCES the aggregate summary line, in "
       "the monolith's exact format, so the three refusals above are the SELECTOR's doing "
       "and not a method that always raises. A scope that refused unconditionally would "
       "pass every refusal assertion in this block and break the gate",
       _w17_full.aggregate_line(3362, 0) == "selftest: 3362 passed, 0 failed"
       and _w17_full.aggregate_line(0, 7) == "selftest: 0 passed, 7 failed")

# The stamp's SHAPE is taken from verify.sh's own printf line rather than retyped here, so
# the payload cannot drift from the file that actually writes it.
_w17_verify_text = (_w17_scripts / "verify.sh").read_text()
_w17_stamp_keys = _w17_re.findall(r'"([a-z_]+)":', _w17_verify_text.split("last_verify")[0].split(
    "printf")[-1]) if "last_verify" in _w17_verify_text else []
_w17_payload = _w17_full.verify_stamp_payload("deadbeef", "green", "2026-01-01T00:00:00Z", 4, 18)
expect("WARP-0717 AC2 NON-VACUITY: the FULL scope's verify-stamp payload carries EXACTLY "
       "the keys scripts/verify.sh's own printf writes into .veldo/last_verify, with the key "
       "list PARSED OUT OF verify.sh rather than retyped here, so the payload cannot drift "
       "from the file that actually writes the stamp",
       bool(_w17_stamp_keys) and sorted(_w17_payload) == sorted(_w17_stamp_keys))

with tempfile.TemporaryDirectory() as _d:
    # The criterion's own evidence is deliberately a DIFFERENT kind, so the only thing
    # carrying `unit` into this proof is the check entry the SCOPE produced. That is what
    # makes the pair below bind the scope's contribution rather than the fixture's.
    _w17_spec = tmpfile(_d, "WARP-9717-fixture.md", GOOD_SPEC)
    _w17_proof = {
        "schema": "veldo.proof/v1", "spec_id": "WARP-9001", "commit": "deadbeef",
        "producer": "selftest", "rollback": "git revert",
        "criteria": [{"id": "AC1", "status": "passed",
                      "evidence": [{"type": "operational", "ref": "x"}]}],
        "checks": [_w17_full.unit_evidence_check(0)],
    }
    _w17_pf_with = tmpfile(_d, "proof-with.json", json.dumps(_w17_proof))
    _w17_pf_without = tmpfile(_d, "proof-without.json",
                              json.dumps(dict(_w17_proof, checks=[])))
    expect("WARP-0717 AC2 NON-VACUITY: the FULL scope's unit-evidence check entry is what "
           "CARRIES the unit kind into a proof, driven through the real "
           "validate.check_required_evidence over a matched pair: with the scope's entry the "
           "spec's required_evidence [unit] is SATISFIED, and with the entry removed, which "
           "is exactly what a partial run is left with because the scope refuses to make "
           "one, it is REFUSED. The criterion's own evidence is a different kind on purpose, "
           "so the entry is the only thing under test. STATED AS MEASURED, NOT AS HOPED: "
           "check_required_evidence reads the KIND and NOT the status, so flipping the "
           "entry's status to failed does NOT make it refuse; withholding the entry is the "
           "whole of what the refusal buys here",
           V.check_required_evidence(_w17_spec, _w17_pf_with) == 0
           and V.check_required_evidence(_w17_spec, _w17_pf_without) > 0
           and V.check_required_evidence(
               _w17_spec, tmpfile(_d, "proof-failed.json", json.dumps(
                   dict(_w17_proof, checks=[{"name": "unit", "status": "failed"}])))) == 0)

# ---------------------------------------------------------------------------------------
# AC2. THE EXIT CODE, which is the PRESENT-DAY mechanism by which a partial run cannot
# produce a green stamp: verify.sh decides green from the exit status of its unit slot.
# ---------------------------------------------------------------------------------------
expect("WARP-0717 AC2: A PARTIAL RUN'S EXIT CODE IS NEVER 0, passing or failing, while a "
       "full run's is 0 exactly when nothing failed. This is the mechanism the stamp "
       "actually hangs on: scripts/verify.sh writes .veldo/last_verify green only when its "
       "unit slot SUCCEEDS, so a partial unit slot forces status red without verify.sh "
       "knowing anything about selectors. Both partial values are checked, and they stay "
       "DISTINCT (2 passed, 1 failed) so a partial run that failed is still tellable from "
       "one that did not",
       _w17_partial.exit_code(0) == 2 and _w17_partial.exit_code(3) == 1
       and _w17_partial_all.exit_code(0) == 2
       and _w17_full.exit_code(0) == 0 and _w17_full.exit_code(1) == 1)

# ---------------------------------------------------------------------------------------
# AC2. scripts/verify.sh RUNS THE FULL MANIFEST. Asserted as the durable PROPERTY rather
# than as a hash: a pinned digest would red on any unrelated catalog change and get
# rubber-stamped back to green, which is ceremony, not a guard. The property is that the
# unit slot carries no selector and that no selector flag appears anywhere in the file.
# ---------------------------------------------------------------------------------------
_w17_unit_slot = [ln for ln in _w17_verify_text.splitlines() if ln.startswith("CHECK_unit=")]
expect("WARP-0717 AC2: THE GATE STILL INVOKES THE SUITE WITH NO SELECTOR. scripts/verify.sh "
       "declares exactly one unit slot and its command is `python3 scripts/selftest.py` with "
       "nothing after it, so the gate runs the FULL manifest. Asserted as the property "
       "rather than as a pinned digest, because a digest reds on any unrelated catalog edit "
       "and teaches people to re-pin it",
       _w17_unit_slot == ['CHECK_unit="required:python3 scripts/selftest.py"'])

expect("WARP-0717 AC2: NO SELECTOR FLAG APPEARS ANYWHERE IN scripts/verify.sh, not in the "
       "unit slot and not in any other slot, so no catalog entry can be running a subset "
       "under a different name. A future person who WANTS to shortcut the gate has to edit "
       "this file, which is a visible act in the diff",
       "--suite" not in _w17_verify_text and "--upto" not in _w17_verify_text)

# ---------------------------------------------------------------------------------------
# AC1. THE PREREQUISITE CLOSURE. It is a FIXPOINT, and that is load-bearing rather than
# tidy: taking each fragment's DIRECT demand only was measured to leave 5 of 13 fragments
# producing ZERO of their own labels, because a fragment inside the closure died first.
# ---------------------------------------------------------------------------------------
expect("WARP-0717 AC1: THE CLOSURE TABLE AND THE MANIFEST ENUMERATE THE SAME FRAGMENTS, "
       "bound in BOTH DIRECTIONS, so a fragment added to the manifest without regenerating "
       "scripts/suites/requires.json turns this red instead of silently having no closure. "
       "It is a set equality against the manifest and NOT a count, so the suite can grow",
       sorted(_w17_requires) == sorted(_w17_names))

# EVERY LOOKUP BELOW GOES THROUGH .get, and every derivation through _w17_try. Witnesses
# measured the direct versions CRASHING the run instead of reddening it: dropping one entry
# from requires.json raised KeyError, and adding a fragment with no prerequisites on record
# let the generator's (correct) CLOSURE_UNAVAILABLE refusal escape. A run that dies prints no
# verdict line at all, which reads like a run that found nothing wrong, so a crash is worse
# than a red and neither is allowed to happen here.
def _w17_closure_of(name):
    got = _w17_requires.get(name)
    return got if isinstance(got, list) else []


def _w17_try(fn, *a):
    """fn(*a), or None if it raised. A refusal from the generator is a legitimate outcome
    that must surface as a RED assertion rather than as a dead run."""
    try:
        return fn(*a)
    except BaseException:
        return None


expect("WARP-0717 AC1: EVERY CLOSURE CONTAINS ITS OWN FRAGMENT and is ordered by manifest "
       "position, which is what makes `--suite NAME` runnable as a filter over the manifest "
       "order rather than a second ordering nobody validates",
       all(name in _w17_closure_of(name)
           and _w17_closure_of(name) == [n for n in _w17_names
                                         if n in set(_w17_closure_of(name))]
           for name in _w17_names))

expect("WARP-0717 AC1: THE CLOSURE IS A FIXPOINT: for every fragment, the union of its "
       "closure members' own closures is exactly its closure. A prerequisite set that is "
       "not closed under its own relation is not a prerequisite set, and this repository "
       "MEASURED that: the direct demand alone left 5 of 13 fragments producing zero of "
       "their own labels, fragment 13 dying on NameError _FakeLoop inside fragment 06, "
       "whose own demand names two fragments 13's direct demand omits",
       all(_w17_closure_of(name)
           and set().union(*[set(_w17_closure_of(m)) for m in _w17_closure_of(name)])
           == set(_w17_closure_of(name)) for name in _w17_names))

# The fixpoint assertion above would pass on ANY relation that happened to be closed,
# including the direct demand if it were already closed. So the direct demand is derived
# separately and shown to be DIFFERENT: that is what makes the closing step non-decorative.
_w17_measurement = json.loads((ROOT / "proof/WARP-0712/order-dependence.json").read_text())
_w17_direct = _w17_try(_W17RS.direct_demand, _w17_manifest, _w17_measurement)
_w17_derived = _w17_try(_W17RS.transitive_close, _w17_direct) if _w17_direct else None
_w17_grew = ([n for n in _w17_direct
              if set(_w17_derived.get(n, [])) != set(_w17_direct.get(n, []))]
             if _w17_direct and _w17_derived else [])
expect("WARP-0717 AC1: THE COMMITTED CLOSURE TABLE IS EXACTLY WHAT RE-DERIVING FROM THE "
       "COMMITTED MEASUREMENT PRODUCES, so requires.json cannot be hand-edited into "
       "something the measurement does not support. check_generated.sh holds the file "
       "fresh; this binds the derivation itself, in the same run as the assertions that "
       "trust it. IT GOES THROUGH THE GENERATOR'S OWN ENTRY POINTS, derive_requires and "
       "requires_document, and not only through the two halves recomposed here: a witness "
       "measured that recomposing them locally is BLIND to the generator dropping its "
       "closing step, because the committed file would still match a locally closed "
       "relation while every future regeneration produced an unclosed one",
       _w17_derived == _w17_requires
       and _w17_try(_W17RS.derive_requires, _w17_manifest, _w17_measurement) == _w17_requires
       and (_w17_try(_W17RS.requires_document, _w17_manifest, _w17_measurement) or {}
            ).get("requires") == _w17_requires)

expect("WARP-0717 AC1 NON-VACUITY OF THE FIXPOINT: closing the relation CHANGES THE ANSWER "
       "for at least one fragment, so the fixpoint step is load-bearing and not a restating "
       "of an already-closed relation. Without this, the fixpoint assertion above would pass "
       "unchanged on the direct demand, which was MEASURED to leave 5 of 13 fragments "
       "producing zero of their own labels. Bound as a non-empty set of fragments that GREW, "
       "not as a count of them, so the suite can grow",
       _w17_grew != []
       and all(set(_w17_direct.get(n, [])) <= set(_w17_derived.get(n, []))
               for n in _w17_names)
       and any(len(_w17_derived.get(n, [])) > len(_w17_direct.get(n, []))
               for n in _w17_names))

# ---------------------------------------------------------------------------------------
# THE HERMETIC FIXTURE. Byte-identical copies of the dispatcher and the scope module over a
# small manifest, with .veldo symlinked so the real shared.py loads the real validators.
# This is what lets a FULL run be observed here in milliseconds: it must emit the aggregate
# line and exit 0, which is the positive control for the whole mechanism.
# ---------------------------------------------------------------------------------------
_W17_FRAG_A = ('expect("w17 fixture a1", True)\n'
               'expect("w17 fixture a2", True)\n')
_W17_FRAG_B = 'expect("w17 fixture b1", True)\n'


def _w17_fixture(d, suites, requires=None):
    """A runnable copy of the dispatcher over a synthetic manifest. Returns the root."""
    root = Path(d)
    (root / "scripts" / "suites").mkdir(parents=True)
    for rel in ("scripts/selftest.py", "scripts/run_scope.py", "scripts/suites/shared.py"):
        _w17_shutil.copy(ROOT / rel, root / rel)
    os.symlink(ROOT / ".veldo", root / ".veldo")
    entries = [{"name": "shared", "file": "shared.py", "regions": "preamble"}]
    for name, body, req in suites:
        (root / "scripts" / "suites" / (name + ".py")).write_text(body)
        e = {"name": name, "file": name + ".py", "regions": "none"}
        if req is not None:
            e["requires"] = req
        entries.append(e)
    (root / "scripts" / "suites" / "manifest.json").write_text(json.dumps(
        {"schema": "veldo.suites/v1", "entry": "selftest.py", "shared": "shared.py",
         "note": "fixture", "ordering_dependencies": [], "suites": entries}))
    if requires is not None:
        (root / "scripts" / "suites" / "requires.json").write_text(json.dumps(
            {"schema": "veldo.suite_requires/v1", "note": "fixture",
             "derived_from": {}, "requires": requires}))
    return root


def _w17_run(root, *args):
    r = subprocess.run([sys.executable, str(root / "scripts" / "selftest.py")] + list(args),
                       capture_output=True, text=True, cwd=str(root))
    return r.returncode, r.stdout + r.stderr


with tempfile.TemporaryDirectory() as _d:
    _w17_root = _w17_fixture(_d, [("f1", _W17_FRAG_A, ["f1"]), ("f2", _W17_FRAG_B, ["f1", "f2"])],
                             requires={"f1": ["f1"], "f2": ["f1", "f2"]})
    _w17_rc_full, _w17_out_full = _w17_run(_w17_root)
    _w17_rc_sub, _w17_out_sub = _w17_run(_w17_root, "--suite", "f1")

    expect("WARP-0717 AC2 POSITIVE CONTROL, THROUGH THE REAL DISPATCHER: a run with NO "
           "selector EMITS the aggregate summary line and EXITS 0. Driven over a hermetic "
           "two-fragment fixture holding byte-identical copies of scripts/selftest.py and "
           "scripts/run_scope.py, so the mechanism under test is the shipped one and the "
           "observation costs milliseconds instead of the whole suite. Without this the "
           "refusals prove only that something is broken",
           _w17_rc_full == 0
           and _w17_re.search(r"^selftest: \d+ passed, 0 failed$", _w17_out_full, _w17_re.M) is not None)

    expect("WARP-0717 AC2, THROUGH THE REAL DISPATCHER: a run WITH a selector emits NO "
           "aggregate summary line at all, prints the partial banner naming itself, and "
           "exits non-zero. Same fixture, same binary, one flag different, so the "
           "difference is attributable to the selector",
           _w17_rc_sub != 0
           and _w17_re.search(r"^selftest: \d+ passed, \d+ failed$", _w17_out_sub, _w17_re.M) is None
           and "PARTIAL RUN OF THE UNIT SUITE" in _w17_out_sub
           and _W17_REFUSAL in _w17_out_sub)

    # THE ADDITIVE GROWTH CONTROL. A fragment the WARP-0712 measurement never saw has no
    # region range, so its closure cannot be derived. It must DECLARE one, and a fragment
    # that declares nothing is a REFUSAL rather than a silent empty closure, because an
    # empty closure would run it alone and it would die on a NameError that reads as a
    # defect in the fragment. This is ADDITIVE: it adds a fragment, and no assertion here
    # pins how many fragments exist.
    expect("WARP-0717 AC1 GROWTH, FAIL CLOSED: a fragment present in the manifest with no "
           "region range in the WARP-0712 measurement and NO declared `requires` makes the "
           "closure generator REFUSE by name (CLOSURE_UNAVAILABLE), never hand back an "
           "empty closure. An empty closure would run that fragment alone, and every "
           "fragment was measured PASSES_IN_AGGREGATE_FAILS_ALONE, so the silent version "
           "would surface as a NameError that reads like a defect in the new fragment",
           _w17_raises(_W17RS.derive_requires,
                       {"schema": "veldo.suites/v1", "shared": "shared.py", "suites": [
                           {"name": "shared", "file": "shared.py", "regions": "preamble"},
                           {"name": "newbie", "file": "newbie.py", "regions": "none"}]},
                       _w17_measurement)[0]
           and "CLOSURE_UNAVAILABLE" in _w17_raises(
               _W17RS.derive_requires,
               {"schema": "veldo.suites/v1", "shared": "shared.py", "suites": [
                   {"name": "shared", "file": "shared.py", "regions": "preamble"},
                   {"name": "newbie", "file": "newbie.py", "regions": "none"}]},
               _w17_measurement)[1])

    expect("WARP-0717 AC1 GROWTH, FAIL CLOSED: a fragment whose declared `requires` names "
           "something the manifest does not enumerate is REFUSED by name rather than "
           "quietly dropped, so a typo in a declaration cannot shrink a run",
           "CLOSURE_UNAVAILABLE" in _w17_raises(
               _W17RS.derive_requires,
               {"schema": "veldo.suites/v1", "shared": "shared.py", "suites": [
                   {"name": "shared", "file": "shared.py", "regions": "preamble"},
                   {"name": "newbie", "file": "newbie.py", "regions": "none",
                    "requires": ["newbie", "nobody_by_that_name"]}]},
               _w17_measurement)[1])

# ---------------------------------------------------------------------------------------
# AC1. THE UNKNOWN-NAME REFUSAL, driven through the REAL dispatcher for four hostile shapes.
# A selector that matches nothing and exits 0 is the most dangerous output this feature
# could have, so each shape is required to exit non-zero, print no aggregate line, and NAME
# the available suites.
# ---------------------------------------------------------------------------------------
_W17_HOSTILE = [
    ("a name nothing defines", "no_such_suite_anywhere"),
    ("a PREFIX of a real name, which must NOT resolve", _w17_names[0][:2]),
    ("the EMPTY STRING, which must not mean everything", ""),
    ("a GLOB METACHARACTER, which must not expand", "*"),
]
# A LIST, NOT A DICT KEYED BY THE BAD NAME, AND BOUND TO len(_W17_HOSTILE) BELOW. Review 1
# measured the dict form: two shapes that happened to share a key would collapse into one
# entry and silently SHRINK the checked set, and an emptied _W17_HOSTILE would leave both
# all() assertions vacuously true over nothing. The binding is a pin on a literal in THIS
# file, which is what a length pin is allowed to be: it is not a cardinality of anything the
# repository can grow, and the count is the same FOUR the label states.
_w17_hostile_runs = []
for _label, _bad in _W17_HOSTILE:
    _r = subprocess.run([sys.executable, str(_w17_scripts / "selftest.py"), "--suite", _bad],
                        capture_output=True, text=True, cwd=str(ROOT))
    _w17_hostile_runs.append((_label, _bad, _r.returncode, _r.stdout + _r.stderr))

expect("WARP-0717 AC1: AN UNRESOLVABLE SELECTOR IS A REFUSAL THAT NAMES THE AVAILABLE "
       "SUITES, driven through the real scripts/selftest.py for FOUR hostile shapes: a name "
       "nothing defines, a PREFIX of a real name, the EMPTY STRING, and a GLOB "
       "METACHARACTER. Every one exits non-zero, prints UNKNOWN_SUITE, and lists every "
       "fragment the manifest enumerates. A selector that matched nothing and exited 0 "
       "would report success for having tested nothing, which is the worst output this "
       "feature could produce. THE all() IS BOUND TO THE LENGTH OF ITS OWN LITERAL SOURCE, "
       "so an emptied shape list REDS this instead of passing over nothing",
       len(_w17_hostile_runs) == len(_W17_HOSTILE) == 4 and _w17_names != []
       and all(rc != 0 and "UNKNOWN_SUITE" in out
               and all(n in out for n in _w17_names)
               for _l, _b, rc, out in _w17_hostile_runs))

expect("WARP-0717 AC1: NONE of the four hostile selectors emits an aggregate summary line, "
       "so nothing that parses that line can read a refused run as a pass. Checked "
       "separately from the exit code because a log is read by humans and by greps, and the "
       "exit code is gone by the time either happens. BOUND TO THE SAME LENGTH, for the same "
       "reason: an all() over an iterable nothing pins is a check that can be emptied",
       len(_w17_hostile_runs) == len(_W17_HOSTILE) == 4
       and all(_w17_re.search(r"^selftest: \d+ passed, \d+ failed$", out, _w17_re.M) is None
               for _l, _b, _rc, out in _w17_hostile_runs))

# ---------------------------------------------------------------------------------------
# AC1. THE FLAG SHAPES, which is a DIFFERENT hole from the unknown NAME above and was found
# by review 1 rather than by this build. `--suite=NAME` is not the string `--suite`, so the
# equals form was recognised by nothing and fell through to a FULL run at exit 0 with the
# aggregate line printed. Measured on a byte-identical copy of the pre-correction dispatcher:
# all four shapes below ran the whole fixture and exited 0. It failed in the SAFE direction,
# because a genuine full run happened, but a person chasing a fast loop paid the entire suite
# and read a green line as their subset's. The fix refuses ANY unrecognised argument starting
# with `--`, which closes both selectors' equals forms and every future flag typo at once.
# ---------------------------------------------------------------------------------------
_W17_BAD_FLAGS = [
    ("the EQUALS FORM of --suite with a REAL name", "--suite=05_tracker_routing_resolver_veldo"),
    ("the EQUALS FORM of --suite with a name nothing defines", "--suite=no_such_suite"),
    ("the EQUALS FORM of the other selector", "--upto=05_tracker_routing_resolver_veldo"),
    ("a flag this dispatcher does not define at all", "--only-the-fast-bits"),
]


def _w17_drive_bounded(arg, timeout=30):
    """One dispatcher run under a WALL-CLOCK BOUND, returning (exit code or None, output).

    THE BOUND IS NOT TIDINESS, IT IS THE ONLY THING THAT KEEPS A REMOVED REFUSAL A RED. If
    the flag refusal is ever taken out, these arguments go back to starting a FULL run of the
    suite, and a full run CONTAINS THIS FRAGMENT, which would drive them again. Unbounded,
    that is a recursion rather than a failing assertion, and a hang prints no verdict line at
    all. Bounded, the child is killed long before a full run could reach this fragment (about
    95s in), so the depth stops at one and the outcome is a RED. A timeout yields None, which
    is not 2, so the assertion below fails rather than skipping.
    """
    try:
        r = subprocess.run([sys.executable, str(_w17_scripts / "selftest.py"), arg],
                           capture_output=True, text=True, cwd=str(ROOT), timeout=timeout)
    except subprocess.TimeoutExpired as e:
        return None, "TIMEOUT after %ss: %s" % (timeout, e.output or "")
    return r.returncode, r.stdout + r.stderr


_w17_flag_runs = [(_label, _arg) + _w17_drive_bounded(_arg) for _label, _arg in _W17_BAD_FLAGS]

expect("WARP-0717 AC1: AN UNRECOGNISED ARGUMENT BEGINNING WITH `--` IS A NAMED REFUSAL AT "
       "EXIT 2, driven through the real scripts/selftest.py for FOUR shapes: the equals form "
       "of --suite with a REAL suite name, the equals form with a name nothing defines, the "
       "equals form of --upto, and a flag nothing defines at all. Each prints "
       "UNRECOGNISED_FLAG, exits 2, and emits NO aggregate summary line. REVIEW 1 MEASURED "
       "THE PRE-CORRECTION DISPATCHER RUNNING THE WHOLE SUITE AND EXITING 0 FOR ALL FOUR, "
       "printing the aggregate line, because the equals form is not the string the value "
       "parser looked for. Each run is WALL-CLOCK BOUNDED, so a refusal removed in future is "
       "a RED here rather than a recursive full run of a suite that contains this fragment. "
       "Bound to the length of its own literal shape list, so emptying that list REDS this",
       len(_w17_flag_runs) == len(_W17_BAD_FLAGS) == 4
       and all(rc == 2 and "UNRECOGNISED_FLAG" in out
               and _w17_re.search(r"^selftest: \d+ passed, \d+ failed$", out,
                                  _w17_re.M) is None
               for _l, _a, rc, out in _w17_flag_runs))

# The positive control for the flag refusal: the shapes that MUST still work. `--upto` and
# the no-selector path are driven whole elsewhere in this fragment (the AC3 no-regression
# assertion and the hermetic fixture's full run), so what is driven here is `--list`, whose
# output shape is otherwise unasserted: one line per enumerated fragment, exit 0.
_w17_list = subprocess.run([sys.executable, str(_w17_scripts / "selftest.py"), "--list"],
                           capture_output=True, text=True, cwd=str(ROOT))
_w17_list_lines = [ln for ln in _w17_list.stdout.splitlines() if ln.strip()]
expect("WARP-0717 AC3 NO REGRESSION FROM THE FLAG REFUSAL: `--list` still prints exactly one "
       "line per fragment the manifest enumerates, each naming that fragment and its closure "
       "size, and still exits 0. A refusal that swept up the recognised flags with the "
       "unrecognised ones would take the diagnostic down with it, and `--list` is how a "
       "person finds a name to select in the first place",
       _w17_list.returncode == 0
       and len(_w17_list_lines) == len(_w17_names) and _w17_names != []
       and all(_w17_re.search(r"^%s\s+%s\s+closure \d+$" % (_w17_re.escape(s["name"]),
                                                            _w17_re.escape(s["file"])),
                              _w17_list.stdout, _w17_re.M) is not None
               for s in _W17RS.fragments(_w17_manifest)))

# ---------------------------------------------------------------------------------------
# AC1. `--suite NAME` RUNS EXACTLY THE CLOSURE, and `--upto` still works. Driven on the real
# suite with the cheapest fragment, so the real closure path is observed once for real.
# ---------------------------------------------------------------------------------------
_w17_cheap = "05_tracker_routing_resolver_veldo"
_w17_r = subprocess.run([sys.executable, str(_w17_scripts / "selftest.py"),
                         "--suite", _w17_cheap], capture_output=True, text=True, cwd=str(ROOT))
_w17_real_out = _w17_r.stdout + _w17_r.stderr

def _w17_banner_ran(out):
    """The fragments the banner says it ran, or [] if the banner does not say.

    DEFENSIVE ON PURPOSE. A witness measured the unguarded version of this parse CRASHING
    the whole run when the banner text was mutated: it indexed split("suites:")[1] on a line
    that no longer had that separator, and a run that dies prints no verdict line at all,
    which reads like a run that found nothing wrong. A crash is worse than a red, so a
    banner this cannot parse yields [] and REDS the assertion below.
    """
    for ln in out.splitlines():
        if ln.strip().startswith("running") and "suites:" in ln:
            return [n for n in ln.split("suites:", 1)[1].replace(" ", "").split(",") if n]
    return []


_w17_ran = _w17_banner_ran(_w17_real_out)
expect("WARP-0717 AC1: `--suite NAME` RUNS EXACTLY THE FRAGMENTS THE CLOSURE TABLE NAMES, "
       "no more and no fewer, observed by parsing the banner of a REAL run of the REAL "
       "suite rather than by reading the dispatcher's source. The fragment chosen is the "
       "one whose closure is itself alone, which is also the measured floor of this "
       "feature: 0.03s against the 21.35s prefix --upto would run to reach it",
       _w17_ran != [] and _w17_ran == _w17_closure_of(_w17_cheap)
       and _w17_r.returncode == 2)

expect("WARP-0717 AC1: a partial run REPORTS ITS OWN ELAPSED TIME AND THE SELECTED "
       "FRAGMENT'S OWN ASSERTION COUNT, which is what makes it usable as an inner loop: the "
       "reader sees what this fragment proved and what it cost, not only a union",
       _w17_re.search(r"^\s+%s\s+\d+ passed\s+\d+\.\d\ds$" % _w17_re.escape(_w17_cheap),
                 _w17_real_out, _w17_re.M) is not None
       and _w17_re.search(r"^selftest \(PARTIAL, \d+ of \d+ suites\): \d+ passed, \d+ failed "
                     r"in \d+\.\d\ds$", _w17_real_out, _w17_re.M) is not None)

_w17_upto = subprocess.run([sys.executable, str(_w17_scripts / "selftest.py"),
                            "--upto", _w17_names[0]], capture_output=True, text=True,
                           cwd=str(ROOT))
_w17_upto_out = _w17_upto.stdout + _w17_upto.stderr
expect("WARP-0717 AC3 NO REGRESSION: `--upto` STILL WORKS, still exits 2 on success, and "
       "its final line still BEGINS with the exact text WARP-0712 gave it, "
       "`selftest (PARTIAL, N of M suites): P passed, F failed`, which is now a strict "
       "prefix of a line that also carries the elapsed time. So anything that already "
       "recognised a partial run still does, and the two selectors print the same shape",
       _w17_upto.returncode == 2
       and _w17_re.search(r"^selftest \(PARTIAL, 1 of %d suites\): \d+ passed, 0 failed in "
                     r"\d+\.\d\ds$" % len(_w17_names), _w17_upto_out, _w17_re.M) is not None
       and "PARTIAL RUN OF THE UNIT SUITE" in _w17_upto_out
       and _w17_re.search(r"^selftest: \d+ passed, \d+ failed$", _w17_upto_out, _w17_re.M) is None)

# THE PROBE LIST IS BUILT FIRST AND ITS SHAPE IS BOUND, because review 1 measured this
# all() vacuously true over an EMPTY pack roster: absence asserted against a roster that
# declares nothing is a check that passes for having looked nowhere. The canon root
# contributes its probes from a LITERAL tuple in this file, so the list can never be empty
# while that tuple is not, and the total is bound to the roster's own length rather than to
# a count of packs, which the repository can grow.
_W17_CANON_FILES = ("selftest.py", "run_scope.py")
_w17_pack_roster = json.loads((ROOT / ".veldo/packs.json").read_text())["packs"]
_w17_canon_probes = ([ROOT / "engine/scripts" / f for f in _W17_CANON_FILES]
                     + [ROOT / p["pack_dir"] / "scripts" / f
                        for p in _w17_pack_roster for f in _W17_CANON_FILES])
expect("WARP-0717 AC3: THE SELECTOR AND ITS BANNER ARE NOT ENGINE CANON AND ARE CORRECTLY "
       "ABSENT FROM engine AND EVERY PACK. The unit suite is THIS repository's "
       "own 3000-plus assertions about its own engine; the canonical engine source is "
       "engine (.veldo/packs.json), whose script globs never matched a "
       "selftest.py. Shipping it to adopters would ship our tests. Asserted as absence "
       "against the DECLARED pack roster rather than a fixed list of directories, so a "
       "newly declared pack is covered. THE PROBE SET IS BOUND: both files of the literal "
       "pair, for the canon root and for every declared pack, and a roster declaring "
       "NOTHING reds instead of passing over nothing",
       len(_W17_CANON_FILES) == 2 and _w17_pack_roster != []
       and len(_w17_canon_probes) == len(_W17_CANON_FILES) * (1 + len(_w17_pack_roster))
       and all(not p.exists() for p in _w17_canon_probes))

del _w17_re, _w17_shutil
