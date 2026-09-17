"""VELDO-0016: decision records and effective policy amendments (PLAN-0019 W1).

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, so its declared
prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 29_veldo_0016_policy_boundaries

WHAT IS UNDER TEST (AC3). The architecture contract loader, validate_checks.load_contract_state,
and EVERY engine entry that reads the contract through it. Before this spec the loader answered
(None, None) both for a repository with no contract and for a repository whose contract could
not be read, so a directory at the path, a dangling symlink, a truncated file, a file outside the
parser subset or a structurally invalid contract stood every consumer down "adoption safe": the
ready transition let a placeless spec through, the frontier offered it, run-check cleared it and
the shape gate printed that it was standing down. The contract module .veldo/policy_contract.py
enumerates the adapters (LOADER_ADAPTERS) and states the expected outcome per state and flag
(expected_loader_outcome); this fragment DERIVES the callers from the source and compares them
with the registry in both directions, then drives the full product of adapters, states and the
required flag on fixture trees that carry a copy of the engine, so each adapter runs from its own
root exactly the way it runs in production, with nothing monkeypatched.

EVERY ROW IS DRIVEN. Three mutants of the loader are applied to a fixture's engine copy and the
same harness is run over them: the pre-fix presence test (a directory reads as absent), the
pre-fix ArchContractError handler (a malformed file reads as absent) and a dead required flag.
Each must turn its target row red while the unmutated copy passes the same row, or the row proves
nothing. The falsifier the spec declares is the first of these: "map an unreadable present
contract to optional absence; the policy-loading/unreadable row must fail".
"""
import contextlib as _v16_contextlib
import importlib.util as _v16_ilu
import io as _v16_io
import shutil as _v16_shutil

_v16_pcspec = _v16_ilu.spec_from_file_location("v16_policy_contract", ROOT / ".veldo" / "policy_contract.py")
PC16 = _v16_ilu.module_from_spec(_v16_pcspec)
_v16_pcspec.loader.exec_module(PC16)

_V16_CONTRACT_TEXT = (ROOT / ".veldo" / "architecture.yaml").read_text()

_V16_SPEC = """---
schema: veldo.spec/v1
id: FX-0001
title: Fixture spec for the loading product
status: ready
risk: standard
owner: fixture
lane: standalone
placement: [contracts]
footprint:
  - ".veldo/validate.py"
depends_on: []
acceptance_criteria:
  - id: AC1
    text: fixture
---

## Intent

A fixture.
"""

_V16_PLAN = """---
schema: veldo.plan/v1
id: PLAN-FX
title: Fixture plan for run-check
status: ready
revision: 1
owner: fixture
work:
  - id: W1
    spec: FX-0001
    depends_on: []
---

## Intent

A fixture.
"""

_V16_POLICY = """schema: veldo.policy/v1
version: 1
risk_tiers:
  low:      {gate: standard, reviews: 1, min_independence: L1, human_approval: false}
  standard: {gate: full,     reviews: 1, min_independence: L2, human_approval: false}
  high:     {gate: expanded, reviews: 1, min_independence: L2, human_approval: true}
  critical: {gate: expanded, reviews: 2, min_independence: L2, human_approval: true}
architecture_contract: %s
protected_paths:
  - {path: ".veldo/policy.yaml", floor: high}
"""

_V16_FM_OK = {"placement": ["contracts"], "footprint": [".veldo/validate.py"], "risk": "standard"}


def _v16_write_contract(fx, state):
    """Put the fixture's contract artifact into one of the five states. `unreadable` is a
    DIRECTORY at the path: present, and no reader can read it as a file, whoever runs the suite
    (a permission bit is a second unreadable case below, skipped for a root reader)."""
    p = fx / ".veldo" / "architecture.yaml"
    if state == "absent":
        return
    if state == "unreadable":
        p.mkdir()
    elif state == "malformed":
        p.write_text("- not\n- a mapping\n")
    elif state == "invalid":
        p.write_text("schema: veldo.arch/v1\nid: fx\ntitle: fixture without areas\nversion: 1\nstatus: draft\n")
    elif state == "valid":
        p.write_text(_V16_CONTRACT_TEXT)
    else:
        raise AssertionError(state)


def _v16_fixture(state, required, mutate=None):
    """A repository tree carrying a COPY of this engine's .veldo/*.py, a policy whose
    architecture_contract flag is `required`, one ready standalone spec, one plan naming it,
    and the contract in `state`. `mutate(fx)` edits the engine copy before anything loads it."""
    fx = Path(tempfile.mkdtemp(prefix="v16fx"))
    (fx / ".veldo").mkdir()
    for p in (ROOT / ".veldo").glob("*.py"):
        _v16_shutil.copyfile(p, fx / ".veldo" / p.name)
    for d in ("specs", "plans", "proof", "scripts"):
        (fx / d).mkdir()
    # The contract's mechanizable patterns name the gate scripts that enforce them, and the shape
    # gate refuses a contract whose enforcement is absent; a fixture that reads as a repository
    # carries the top-level gate scripts, never the suites.
    for p in (ROOT / "scripts").iterdir():
        if p.is_file():
            _v16_shutil.copyfile(p, fx / "scripts" / p.name)
    (fx / ".veldo" / "policy.yaml").write_text(_V16_POLICY % ("required" if required else "optional"))
    (fx / "specs" / "FX-0001-fixture.md").write_text(_V16_SPEC)
    (fx / "plans" / "PLAN-FX-fixture.md").write_text(_V16_PLAN)
    _v16_write_contract(fx, state)
    if mutate is not None:
        mutate(fx)
    return fx


def _v16_mod(fx, name):
    spec = _v16_ilu.spec_from_file_location("v16_%s_%s" % (name, fx.name), fx / ".veldo" / (name + ".py"))
    m = _v16_ilu.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _v16_quiet(fn):
    """Run fn() with stdout and stderr captured (the adapters print their refusals)."""
    out = _v16_io.StringIO()
    with _v16_contextlib.redirect_stdout(out), _v16_contextlib.redirect_stderr(out):
        return fn(), out.getvalue()


def _v16_probe(adapter_id, fx, V):
    """(outcome, detail) for one registered adapter over one fixture. Each adapter is loaded
    FROM THE FIXTURE'S ENGINE COPY, so its own ROOT is the fixture and nothing is patched."""
    R, P = PC16.REFUSED, PC16.PROCEEDED
    spec_path = str(fx / "specs" / "FX-0001-fixture.md")
    if adapter_id == "validate_checks.load_contract_state":
        load = V.load_contract_state(str(fx))
        return (R if load.refused else P), (load.state, load.kind)
    if adapter_id == "validate_checks.load_repo_contract":
        try:
            arch, contract = V.load_repo_contract(str(fx))
        except V.ContractRefused as e:
            return R, e.load.kind
        return P, ("contract" if contract is not None else "none")
    if adapter_id == "validate_checks.check_arch":
        n, text = _v16_quiet(lambda: V.check_arch(root=str(fx)))
        return (R if n else P), text.strip()
    if adapter_id == "validate_checks.placement_gate_problems":
        probs = V.placement_gate_problems(dict(_V16_FM_OK), repo_root=str(fx))
        return (R if any("architecture contract refused" in m for m in probs) else P), probs
    if adapter_id == "validate_checks.placement_gate_ok":
        ok = V.placement_gate_ok(dict(_V16_FM_OK), repo_root=str(fx))
        return (P if ok else R), ok
    if adapter_id == "validate_checks.check_ready":
        n, text = _v16_quiet(lambda: V.check_ready(spec_path, repo_root=str(fx)))
        return (R if n else P), text.strip()
    if adapter_id == "validate_checks.check_shape_review":
        n, text = _v16_quiet(lambda: V.check_shape_review(spec_path, [".veldo/validate.py"], repo_root=str(fx)))
        return (R if n else P), text.strip()
    if adapter_id == "frontier.claimable":
        FR = _v16_mod(fx, "frontier")
        claims = fx / "claims"
        claims.mkdir(exist_ok=True)
        offers = FR.claimable(repo_root=str(fx), claims_root=str(claims))
        return (P if offers else R), (offers, FR.contract_refusal(str(fx)))
    if adapter_id == "plan.cmd_run_check":
        PL = _v16_mod(fx, "plan")
        rc, text = _v16_quiet(lambda: PL.cmd_run_check(str(fx / "plans" / "PLAN-FX-fixture.md"), "FX-0001"))
        return (R if rc else P), text.strip()
    if adapter_id == "shape_gate.run":
        SG = _v16_mod(fx, "shape_gate")
        standdown, problems, _notes = SG.run(fx, set())
        return (R if problems else P), (standdown, problems)
    if adapter_id == "observability._cli":
        OB = _v16_mod(fx, "observability")
        rc, text = _v16_quiet(lambda: OB._cli(["observability.py", spec_path]))
        return (R if rc else P), text.strip()
    if adapter_id == "intent_corpus.open_corpus":
        IC = _v16_mod(fx, "intent_corpus")
        try:
            IC.open_corpus(fx)
        except IC.IntentCorpusError as e:
            return (R if "architecture contract refused" in str(e) else "error"), str(e)
        return P, "opened"
    if adapter_id == "entropy.entropy_report":
        EN = _v16_mod(fx, "entropy")
        # entropy loads its own validate instance by path, so its ContractRefused is a different
        # class object from V's: the registry says it raises ContractRefused, matched here by name.
        try:
            rep = EN.entropy_report(events=[], root=str(fx))
        except Exception as e:
            if type(e).__name__ == "ContractRefused":
                return R, e.load.kind
            raise
        return P, ("standdown" if rep.get("standdown") else "report")
    if adapter_id == "cost_to_change.repo_report":
        CTC = _v16_mod(fx, "cost_to_change")
        rep, _text = _v16_quiet(lambda: CTC.repo_report(root=str(fx)))
        return (R if rep.get("refused") else P), rep.get("reason")
    if adapter_id == "metrics_shape_readers._read_contract":
        MSR = _v16_mod(fx, "metrics_shape_readers")
        _parsed, _declared, problem = MSR._read_contract(fx, V)
        return (R if problem else P), problem
    raise AssertionError("no probe for adapter %r" % adapter_id)


_V16_PROBED = {
    "validate_checks.load_contract_state", "validate_checks.load_repo_contract",
    "validate_checks.check_arch", "validate_checks.placement_gate_problems",
    "validate_checks.placement_gate_ok", "validate_checks.check_ready",
    "validate_checks.check_shape_review", "frontier.claimable", "plan.cmd_run_check",
    "shape_gate.run", "observability._cli", "intent_corpus.open_corpus",
    "entropy.entropy_report", "cost_to_change.repo_report", "metrics_shape_readers._read_contract",
}


def _v16_run_matrix(mutate=None, states=PC16.LOADER_STATES, flags=(False, True)):
    """Drive every registered adapter over every (state, required) fixture. Returns the list of
    (adapter, state, required, expected, observed, detail) rows, plus the loader's exact
    (state, kind) per fixture."""
    rows, kinds = [], {}
    for state in states:
        for required in flags:
            fx = _v16_fixture(state, required, mutate=mutate)
            try:
                V = _v16_mod(fx, "validate")
                for a in PC16.LOADER_ADAPTERS:
                    expected = PC16.expected_loader_outcome(state, required)
                    try:
                        observed, detail = _v16_probe(a["id"], fx, V)
                    except Exception as e:  # a crash is neither refusal nor proceeding: it is a row that reds by name
                        observed, detail = "crashed", "%s: %s" % (type(e).__name__, e)
                    rows.append((a["id"], state, required, expected, observed, detail))
                    if a["id"] == "validate_checks.load_contract_state":
                        kinds[(state, required)] = detail
            finally:
                _v16_shutil.rmtree(fx, ignore_errors=True)
    return rows, kinds


# ---------------------------------------------------------------------------------------------
# AC3, the registry: derived from the source in both directions, and its teeth.
# ---------------------------------------------------------------------------------------------
_v16_reg_problems = PC16.loader_registry_problems(ROOT)
expect("VELDO-0016 AC3 policy-loading/registry: the loader adapter registry is exactly the set of "
       "engine modules whose source calls the loader or a placement predicate, in both directions "
       "(problems: %s)" % _v16_reg_problems,
       _v16_reg_problems == [] and len(PC16.LOADER_ADAPTERS) >= 15)
expect("VELDO-0016 AC3 policy-loading/registry: every registered adapter has a probe in this suite "
       "and every probe is a registered adapter, so the product below covers the registry and nothing "
       "is probed off the record",
       {a["id"] for a in PC16.LOADER_ADAPTERS} == _V16_PROBED)

with tempfile.TemporaryDirectory(prefix="v16reg") as _v16_rd:
    _v16_rt = Path(_v16_rd)
    (_v16_rt / ".veldo").mkdir()
    for _v16_p in (ROOT / ".veldo").glob("*.py"):
        _v16_shutil.copyfile(_v16_p, _v16_rt / ".veldo" / _v16_p.name)
    (_v16_rt / ".veldo" / "rogue.py").write_text("def f(V, root):\n    return V.load_repo_contract(root)\n")
    _v16_rogue = PC16.loader_registry_problems(_v16_rt)
    expect("VELDO-0016 AC3 policy-loading/registry TEETH: an unregistered module that calls the loader is "
           "named as a consumer the product cannot reach",
           any(".veldo/rogue.py" in m and "no adapter registers it" in m for m in _v16_rogue))
    (_v16_rt / ".veldo" / "rogue.py").unlink()
    (_v16_rt / ".veldo" / "frontier.py").write_text("# a frontier that reads no contract\n")
    _v16_dead = PC16.loader_registry_problems(_v16_rt)
    expect("VELDO-0016 AC3 policy-loading/registry TEETH: a registered adapter whose module no longer calls "
           "the loader is named as a registry row about nothing",
           any(".veldo/frontier.py" in m and "calls no loader entry" in m for m in _v16_dead))

# ---------------------------------------------------------------------------------------------
# AC3, the result type: canonical and synced entry points are the same code and the same type.
# ---------------------------------------------------------------------------------------------
# The engine copy is loaded through ITS validate.py, the way production loads it: validate.py
# wires the parser and the failure reporter into validate_checks, and a validate_checks loaded
# bare has neither.
_v16_eng = _v16_ilu.spec_from_file_location("v16_engine_validate", ROOT / "engine" / ".veldo" / "validate.py")
_V16_EVC = _v16_ilu.module_from_spec(_v16_eng)
_v16_eng.loader.exec_module(_V16_EVC)
_v16_root_load = V.load_contract_state(str(ROOT))
_v16_eng_load = _V16_EVC.load_contract_state(str(ROOT))
expect("VELDO-0016 AC3 policy-loading/sync: the canonical engine/.veldo/validate_checks.py and the root "
       "instance are byte-identical, expose the same ContractLoad fields, and answer the same "
       "(state, kind) for this repository's own contract",
       (ROOT / ".veldo" / "validate_checks.py").read_bytes() == (ROOT / "engine" / ".veldo" / "validate_checks.py").read_bytes()
       and V.ContractLoad._fields == _V16_EVC.ContractLoad._fields
       and (_v16_root_load.state, _v16_root_load.kind) == (_v16_eng_load.state, _v16_eng_load.kind) == ("valid", "valid")
       and (ROOT / ".veldo" / "policy_contract.py").read_bytes() == (ROOT / "engine" / ".veldo" / "policy_contract.py").read_bytes())
expect("VELDO-0016 AC3 policy-loading/result-type: ContractLoad carries state, kind, arch, contract, "
       "problems, path and required, refused is derived from state and the flag alone, and the kinds "
       "vocabulary is exactly the six the taxonomy names",
       V.ContractLoad._fields == ("state", "kind", "arch", "contract", "problems", "path", "required")
       and V.ContractLoad("invalid", "unreadable", None, None, ("x",), "p", False).refused is True
       and V.ContractLoad("absent", "required_absence", None, None, ("x",), "p", True).refused is True
       and V.ContractLoad("absent", "optional_absence", None, None, (), "p", False).refused is False
       and V.ContractLoad("valid", "valid", None, {}, (), "p", True).refused is False
       and set(V.CONTRACT_KINDS) == {"optional_absence", "required_absence", "unreadable",
                                    "parse_failure", "invalid_structure", "valid"})

# ---------------------------------------------------------------------------------------------
# AC3, the product: every adapter over every state under both flags, from fixture roots.
# ---------------------------------------------------------------------------------------------
_v16_rows, _v16_kinds = _v16_run_matrix()
for _v16_state, _v16_req in sorted(_v16_kinds):
    expect("VELDO-0016 AC3 policy-loading/%s%s: the loader reports (state, kind) %r exactly"
           % (_v16_state, "/required" if _v16_req else "", PC16.LOADER_KIND_FOR_STATE[(_v16_state, _v16_req)]),
           _v16_kinds[(_v16_state, _v16_req)] == PC16.LOADER_KIND_FOR_STATE[(_v16_state, _v16_req)])
for _v16_a, _v16_state, _v16_req, _v16_exp, _v16_obs, _v16_detail in _v16_rows:
    expect("VELDO-0016 AC3 policy-loading/%s%s %s: %s (observed %s: %s)"
           % (_v16_state, "/required" if _v16_req else "", _v16_a, _v16_exp, _v16_obs,
              str(_v16_detail)[:160].replace("\n", " ")),
           _v16_obs == _v16_exp)
expect("VELDO-0016 AC3 policy-loading/product: the product is the full registry times five states times "
       "two flags, %d rows, none crashed" % len(_v16_rows),
       len(_v16_rows) == len(PC16.LOADER_ADAPTERS) * len(PC16.LOADER_STATES) * 2
       and not any(r[4] == "crashed" for r in _v16_rows))

# The flag is SEPARATE from the fixture's policy: an explicit flag on the adapters that take one
# overrides the policy line in both directions.
with tempfile.TemporaryDirectory(prefix="v16flag") as _v16_fd:
    _v16_fa = _v16_fixture("absent", False)
    _v16_fb = _v16_fixture("absent", True)
    try:
        _v16_Va, _v16_Vb = _v16_mod(_v16_fa, "validate"), _v16_mod(_v16_fb, "validate")
        expect("VELDO-0016 AC3 policy-loading/required-flag: the explicit flag is separate from the policy "
               "line - required=True on an optional-policy tree refuses absence, required=False on a "
               "required-policy tree stands down, and the policy line decides when the flag is None",
               _v16_Va.load_contract_state(str(_v16_fa), required=True).kind == "required_absence"
               and _v16_Vb.load_contract_state(str(_v16_fb), required=False).kind == "optional_absence"
               and _v16_Va.load_contract_state(str(_v16_fa)).kind == "optional_absence"
               and _v16_Vb.load_contract_state(str(_v16_fb)).kind == "required_absence"
               and _v16_Va.check_arch(root=str(_v16_fa)) == 0
               and _v16_quiet(lambda: _v16_Va.check_arch(root=str(_v16_fa), required=True))[0] == 1
               and _v16_Va.contract_requirement(str(_v16_fa)) is False
               and _v16_Vb.contract_requirement(str(_v16_fb)) is True)
        (_v16_fa / ".veldo" / "policy.yaml").write_text(_V16_POLICY % "requried")
        expect("VELDO-0016 AC3 policy-loading/required-flag: a policy line that is present and does not say "
               "optional means required (a misspelling closes rather than opens)",
               _v16_Va.contract_requirement(str(_v16_fa)) is True)
    finally:
        _v16_shutil.rmtree(_v16_fa, ignore_errors=True)
        _v16_shutil.rmtree(_v16_fb, ignore_errors=True)

# A second unreadable class: a present file the reader may not open. Skipped for a root reader,
# who can open anything, and said so rather than passed vacuously.
if os.geteuid() != 0:
    _v16_fu = _v16_fixture("absent", False)
    try:
        _v16_up = _v16_fu / ".veldo" / "architecture.yaml"
        _v16_up.write_text(_V16_CONTRACT_TEXT)
        os.chmod(_v16_up, 0)
        _v16_Vu = _v16_mod(_v16_fu, "validate")
        _v16_ul = _v16_Vu.load_contract_state(str(_v16_fu))
        expect("VELDO-0016 AC3 policy-loading/unreadable: a present contract file the reader may not open is "
               "invalid/unreadable and refused, never optional absence",
               (_v16_ul.state, _v16_ul.kind, _v16_ul.refused) == ("invalid", "unreadable", True))
        os.chmod(_v16_up, 0o644)
    finally:
        _v16_shutil.rmtree(_v16_fu, ignore_errors=True)
else:
    expect("VELDO-0016 AC3 policy-loading/unreadable: the permission-bit unreadable case is NOT exercised "
           "under a root reader (root opens anything); the directory-at-the-path case above stands for "
           "unreadable in this run", True)

# ---------------------------------------------------------------------------------------------
# AC3, the drive: three loader mutants, each turning its target rows red on the same harness.
# ---------------------------------------------------------------------------------------------
def _v16_mutant(old, new):
    def mutate(fx):
        p = fx / ".veldo" / "validate_checks.py"
        s = p.read_text()
        assert s.count(old) == 1, (old, s.count(old))
        p.write_text(s.replace(old, new))
    return mutate


def _v16_failing(rows):
    return [(r[0], r[1], r[2]) for r in rows if r[4] != r[3]]


# THE DECLARED FALSIFIER: the pre-fix presence test, under which a directory at the path is
# "absent" and an optional absence proceeds everywhere.
_v16_m1_rows, _v16_m1_kinds = _v16_run_matrix(
    mutate=_v16_mutant("if not os.path.lexists(p):", "if not p.is_file():"),
    states=("unreadable",))
_v16_m1_fail = _v16_failing(_v16_m1_rows)
_V16_GUARDED = set(PC16.guarded_adapters())
_V16_UNGUARDED = [a["id"] for a in PC16.LOADER_ADAPTERS if a["id"] not in _V16_GUARDED]
expect("VELDO-0016 AC3 policy-loading/unreadable DRIVEN (the declared falsifier): mapping an unreadable "
       "present contract to optional absence turns the unreadable row RED for the loader and for every "
       "adapter without a presence guard of its own under the optional flag (%d of %d rows red; guarded: %s)"
       % (len(_v16_m1_fail), len(_v16_m1_rows), sorted(_V16_GUARDED)),
       ("validate_checks.load_contract_state", "unreadable", False) in _v16_m1_fail
       and _v16_m1_kinds[("unreadable", False)] == ("absent", "optional_absence")
       and all((aid, "unreadable", False) in _v16_m1_fail for aid in _V16_UNGUARDED)
       and _V16_GUARDED == {"metrics_shape_readers._read_contract"})

# The pre-fix ArchContractError handler: a malformed file becomes optional absence.
_v16_m2_rows, _v16_m2_kinds = _v16_run_matrix(
    mutate=_v16_mutant(
        '        kind = "unreadable" if getattr(e, "kind", None) == "unreadable" else "parse_failure"\n'
        '        return ContractLoad(CONTRACT_INVALID, kind, arch, None, (str(e),), str(p), req)\n',
        '        return ContractLoad(CONTRACT_ABSENT, "optional_absence", None, None, (), str(p), False)\n'),
    states=("malformed",), flags=(False,))
_v16_m2_fail = _v16_failing(_v16_m2_rows)
expect("VELDO-0016 AC3 policy-loading/malformed DRIVEN: the pre-fix handler that returned (None, None) for a "
       "malformed present file turns the malformed row RED for every adapter (%d of %d rows red)"
       % (len(_v16_m2_fail), len(_v16_m2_rows)),
       _v16_m2_kinds[("malformed", False)] == ("absent", "optional_absence")
       and all((aid, "malformed", False) in _v16_m2_fail for aid in _V16_UNGUARDED))

# A dead required flag: required absence reads as optional absence.
_v16_m3_rows, _v16_m3_kinds = _v16_run_matrix(
    mutate=_v16_mutant("req = contract_requirement(base) if required is None else bool(required)",
                       "req = False"),
    states=("absent",), flags=(True,))
_v16_m3_fail = _v16_failing(_v16_m3_rows)
expect("VELDO-0016 AC3 policy-loading/absent/required DRIVEN: a dead required flag turns the required-absence "
       "row RED for every adapter, the presence-guarded one included, because absence is the one state a "
       "boundary's kind question cannot see (%d of %d rows red)" % (len(_v16_m3_fail), len(_v16_m3_rows)),
       _v16_m3_kinds[("absent", True)] == ("absent", "optional_absence")
       and all((a["id"], "absent", True) in _v16_m3_fail for a in PC16.LOADER_ADAPTERS))
expect("VELDO-0016 AC3 policy-loading/guarded: the presence-guarded adapter refuses an unreadable and a "
       "malformed contract under the loader mutants by its own boundary (its rows stay green there), which "
       "is why it is excluded from those two every-row demands and NOT from the required-absence one",
       ("metrics_shape_readers._read_contract", "unreadable", False) not in _v16_m1_fail
       and ("metrics_shape_readers._read_contract", "malformed", False) not in _v16_m2_fail
       and ("metrics_shape_readers._read_contract", "absent", True) in _v16_m3_fail)

# Additive negative control: the unmutated harness passes exactly the rows the mutants red, so the
# reds above are the mutation's and not the harness's.
expect("VELDO-0016 AC3 policy-loading/control: the unmutated engine passes every row the three mutants "
       "turn red (unreadable, malformed, absent/required), so the drive measures the loader and not the "
       "harness",
       not [r for r in _v16_failing(_v16_rows)
            if r[1:] in {("unreadable", False), ("malformed", False), ("absent", True)}])
