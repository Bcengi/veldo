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
_v16_clspec = _v16_ilu.spec_from_file_location("v16_contract_loader", ROOT / ".veldo" / "contract_loader.py")
CL16 = _v16_ilu.module_from_spec(_v16_clspec)
_v16_clspec.loader.exec_module(CL16)

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


def _v16_probe(adapter, fx, V):
    """(outcome, detail) for one registered adapter over one fixture. Each adapter is loaded
    FROM THE FIXTURE'S ENGINE COPY, so its own ROOT is the fixture and nothing is patched. Probes
    are keyed by the registry row's ENTRY and load the row's MODULE by the name the registry gives,
    so this file names no engine module of its own."""
    R, P = PC16.REFUSED, PC16.PROCEEDED
    spec_path = str(fx / "specs" / "FX-0001-fixture.md")
    adapter_id = adapter["entry"]
    mod = lambda: _v16_mod(fx, adapter["module"].rsplit("/", 1)[1][:-3])
    if adapter_id == "load_contract_state":
        load = V.load_contract_state(str(fx))
        return (R if load.refused else P), (load.state, load.kind)
    if adapter_id == "load_repo_contract":
        try:
            arch, contract = V.load_repo_contract(str(fx))
        except V.ContractRefused as e:
            return R, e.load.kind
        return P, ("contract" if contract is not None else "none")
    if adapter_id == "check_arch":
        n, text = _v16_quiet(lambda: V.check_arch(root=str(fx)))
        return (R if n else P), text.strip()
    if adapter_id == "placement_gate_problems":
        probs = V.placement_gate_problems(dict(_V16_FM_OK), repo_root=str(fx))
        return (R if any("architecture contract refused" in m for m in probs) else P), probs
    if adapter_id == "placement_gate_ok":
        ok = V.placement_gate_ok(dict(_V16_FM_OK), repo_root=str(fx))
        return (P if ok else R), ok
    if adapter_id == "check_ready":
        n, text = _v16_quiet(lambda: V.check_ready(spec_path, repo_root=str(fx)))
        return (R if n else P), text.strip()
    if adapter_id == "check_shape_review":
        n, text = _v16_quiet(lambda: V.check_shape_review(spec_path, [".veldo/validate.py"], repo_root=str(fx)))
        return (R if n else P), text.strip()
    if adapter_id == "claimable":
        FR = mod()
        claims = fx / "claims"
        claims.mkdir(exist_ok=True)
        offers = FR.claimable(repo_root=str(fx), claims_root=str(claims))
        return (P if offers else R), (offers, FR.contract_refusal(str(fx)))
    if adapter_id == "cmd_run_check":
        PL = mod()
        rc, text = _v16_quiet(lambda: PL.cmd_run_check(str(fx / "plans" / "PLAN-FX-fixture.md"), "FX-0001"))
        return (R if rc else P), text.strip()
    if adapter_id == "run":
        SG = mod()
        standdown, problems, _notes = SG.run(fx, set())
        return (R if problems else P), (standdown, problems)
    if adapter_id == "_cli":
        OB = mod()
        rc, text = _v16_quiet(lambda: OB._cli(["observability.py", spec_path]))
        return (R if rc else P), text.strip()
    if adapter_id == "open_corpus":
        IC = mod()
        corpus = IC.open_corpus(fx)  # the corpus OPENS whatever the contract says: its reads are its own
        try:
            corpus.area_of(".veldo/validate.py")
        except IC.IntentCorpusError as e:
            return (R if "architecture contract refused" in str(e) else "error"), str(e)
        return P, ("opened; contract_refused=%s" % corpus.stats()["contract_refused"])
    if adapter_id == "entropy_report":
        EN = mod()
        # entropy loads its own validate instance by path, so its ContractRefused is a different
        # class object from V's: the registry says it raises ContractRefused, matched here by name.
        try:
            rep = EN.entropy_report(events=[], root=str(fx))
        except Exception as e:
            if type(e).__name__ == "ContractRefused":
                return R, e.load.kind
            raise
        return P, ("standdown" if rep.get("standdown") else "report")
    if adapter_id == "repo_report":
        CTC = mod()
        rep, _text = _v16_quiet(lambda: CTC.repo_report(root=str(fx)))
        return (R if rep.get("refused") else P), rep.get("reason")
    if adapter_id == "_read_contract":
        MSR = mod()
        _parsed, _declared, problem = MSR._read_contract(fx, V)
        return (R if problem else P), problem
    raise AssertionError("no probe for adapter entry %r" % adapter_id)


# The ENTRIES this suite probes, compared with the registry in both directions below.
_V16_PROBED = {"load_contract_state", "load_repo_contract", "check_arch", "placement_gate_problems",
               "placement_gate_ok", "check_ready", "check_shape_review", "claimable", "cmd_run_check",
               "run", "_cli", "open_corpus", "entropy_report", "repo_report", "_read_contract"}


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
                        observed, detail = _v16_probe(a, fx, V)
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
       {a["entry"] for a in PC16.LOADER_ADAPTERS} == _V16_PROBED
       and len({a["entry"] for a in PC16.LOADER_ADAPTERS}) == len(PC16.LOADER_ADAPTERS))

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
_v16_ecl = _v16_ilu.spec_from_file_location("v16_engine_cl", ROOT / "engine" / ".veldo" / "contract_loader.py")
_V16_ECL = _v16_ilu.module_from_spec(_v16_ecl)
_v16_ecl.loader.exec_module(_V16_ECL)
expect("VELDO-0016 AC3 policy-loading/sync: the canonical engine copies of the loader, validate_checks and the "
       "policy contract are byte-identical to the root instances, the two loaders expose the same ContractLoad "
       "fields, and both entry points answer the same (state, kind) for this repository's own contract",
       all((ROOT / ".veldo" / f).read_bytes() == (ROOT / "engine" / ".veldo" / f).read_bytes()
           for f in ("validate_checks.py", "contract_loader.py", "policy_contract.py"))
       and CL16.ContractLoad._fields == _V16_ECL.ContractLoad._fields
       and type(_v16_root_load).__name__ == type(_v16_eng_load).__name__ == "ContractLoad"
       and (_v16_root_load.state, _v16_root_load.kind) == (_v16_eng_load.state, _v16_eng_load.kind) == ("valid", "valid"))
expect("VELDO-0016 AC3 policy-loading/result-type: ContractLoad carries state, kind, arch, contract, "
       "problems, path and required, refused is derived from state and the flag alone, and the kinds "
       "vocabulary is exactly the six the taxonomy names",
       CL16.ContractLoad._fields == ("state", "kind", "arch", "contract", "problems", "path", "required")
       and CL16.ContractLoad("invalid", "unreadable", None, None, ("x",), "p", False).refused is True
       and CL16.ContractLoad("absent", "required_absence", None, None, ("x",), "p", True).refused is True
       and CL16.ContractLoad("absent", "optional_absence", None, None, (), "p", False).refused is False
       and CL16.ContractLoad("valid", "valid", None, {}, (), "p", True).refused is False
       and set(CL16.CONTRACT_KINDS) == {"optional_absence", "required_absence", "unreadable",
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
        _v16_CLa = _v16_mod(_v16_fa, "contract_loader")
        expect("VELDO-0016 AC3 policy-loading/required-flag: the explicit flag is separate from the policy "
               "line - required=True on an optional-policy tree refuses absence, required=False on a "
               "required-policy tree stands down, and the policy line decides when the flag is None",
               _v16_Va.load_contract_state(str(_v16_fa), required=True).kind == "required_absence"
               and _v16_Vb.load_contract_state(str(_v16_fb), required=False).kind == "optional_absence"
               and _v16_Va.load_contract_state(str(_v16_fa)).kind == "optional_absence"
               and _v16_Vb.load_contract_state(str(_v16_fb)).kind == "required_absence"
               and _v16_Va.check_arch(root=str(_v16_fa)) == 0
               and _v16_quiet(lambda: _v16_Va.check_arch(root=str(_v16_fa), required=True))[0] == 1
               and _v16_CLa.contract_requirement(str(_v16_fa)) is False
               and _v16_CLa.contract_requirement(str(_v16_fb)) is True)
        (_v16_fa / ".veldo" / "policy.yaml").write_text(_V16_POLICY % "requried")
        expect("VELDO-0016 AC3 policy-loading/required-flag: a policy line that is present and does not say "
               "optional means required (a misspelling closes rather than opens)",
               _v16_CLa.contract_requirement(str(_v16_fa)) is True)
        (_v16_fa / ".veldo" / "policy.yaml").unlink()
        (_v16_fa / ".veldo" / "policy.yaml").mkdir()
        expect("VELDO-0016 AC3 policy-loading/required-flag: a policy entry that is not a regular file is never "
               "opened and means required (the kind question is asked before the read, so a FIFO cannot block "
               "the loader and an unreadable policy closes rather than opens)",
               _v16_CLa.contract_requirement(str(_v16_fa)) is True
               and _v16_Va.load_contract_state(str(_v16_fa)).kind == "required_absence")
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
        p = fx / ".veldo" / "contract_loader.py"
        s = p.read_text()
        assert s.count(old) == 1, (old, s.count(old))
        p.write_text(s.replace(old, new))
    return mutate


def _v16_failing(rows):
    return [(r[0], r[1], r[2]) for r in rows if r[4] != r[3]]


# THE DECLARED FALSIFIER: the pre-fix presence test, under which a directory at the path is
# "absent" and an optional absence proceeds everywhere.
_v16_m1_rows, _v16_m1_kinds = _v16_run_matrix(
    mutate=_v16_mutant("    if not os.path.lexists(p):\n        if req:", "    if not p.is_file():\n        if req:"),
    states=("unreadable",))
_v16_m1_fail = _v16_failing(_v16_m1_rows)
_V16_GUARDED = set(PC16.guarded_adapters())
_V16_UNGUARDED = [a["id"] for a in PC16.LOADER_ADAPTERS if a["id"] not in _V16_GUARDED]
_V16_GUARD_ID = PC16.guarded_adapters()[0]
expect("VELDO-0016 AC3 policy-loading/unreadable DRIVEN (the declared falsifier): mapping an unreadable "
       "present contract to optional absence turns the unreadable row RED for the loader and for every "
       "adapter without a presence guard of its own under the optional flag (%d of %d rows red; guarded: %s)"
       % (len(_v16_m1_fail), len(_v16_m1_rows), sorted(_V16_GUARDED)),
       ("validate_checks.load_contract_state", "unreadable", False) in _v16_m1_fail
       and _v16_m1_kinds[("unreadable", False)] == ("absent", "optional_absence")
       and all((aid, "unreadable", False) in _v16_m1_fail for aid in _V16_UNGUARDED)
       and [g.rsplit(".", 1)[1] for g in sorted(_V16_GUARDED)] == ["_read_contract"])

# The pre-fix ArchContractError handler: a malformed file becomes optional absence.
_v16_m2_rows, _v16_m2_kinds = _v16_run_matrix(
    mutate=_v16_mutant(
        '        kind = "unreadable" if getattr(e, "kind", None) == "unreadable" else "parse_failure"\n'
        '        return ContractLoad(CONTRACT_INVALID, kind, arch, None, (str(e),), str(p), req)\n',
        '        return ContractLoad(CONTRACT_ABSENT, "optional_absence", None, None, (), str(p), False)  # noqa\n'),
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
       (_V16_GUARD_ID, "unreadable", False) not in _v16_m1_fail
       and (_V16_GUARD_ID, "malformed", False) not in _v16_m2_fail
       and (_V16_GUARD_ID, "absent", True) in _v16_m3_fail)

# Additive negative control: the unmutated harness passes exactly the rows the mutants red, so the
# reds above are the mutation's and not the harness's.
expect("VELDO-0016 AC3 policy-loading/control: the unmutated engine passes every row the three mutants "
       "turn red (unreadable, malformed, absent/required), so the drive measures the loader and not the "
       "harness",
       not [r for r in _v16_failing(_v16_rows)
            if r[1:] in {("unreadable", False), ("malformed", False), ("absent", True)}])

# ---------------------------------------------------------------------------------------------
# AC1: decision-to-policy activation. Only an accepted, version-bound, person-decided record
# choosing the activating option, with its adversarial reviews bound, activates a boundary.
# ---------------------------------------------------------------------------------------------
_v16_dspec = _v16_ilu.spec_from_file_location("v16_decision", ROOT / ".veldo" / "decision.py")
D16 = _v16_ilu.module_from_spec(_v16_dspec)
_v16_dspec.loader.exec_module(D16)
_v16_records = [D16.load_record(p, V.parse_yamlish) for p in sorted((ROOT / ".veldo" / "decisions").glob("*.yaml"))]
_v16_by_id = {r["id"]: r for r in _v16_records}

_v16_matrix = PC16.boundary_matrix_problems(_v16_records)
expect("VELDO-0016 AC1 policy-activation/matrix: the decision-to-policy matrix derived from the records' "
       "policy_boundary declarations equals the activation registry in both directions, every registered "
       "decision resolves, and every activating option is one its record declares (problems: %s)" % _v16_matrix,
       _v16_matrix == [] and len(PC16.POLICY_BOUNDARIES) == 6)
expect("VELDO-0016 AC1 policy-activation/matrix: the registry covers the R03 boundaries and every one of the "
       "four open PLAN-0019 choices (D1/D2 under operational_persistence, D3 inside process_lifetime, D4 under "
       "worker_repository_access)",
       {b["id"] for b in PC16.POLICY_BOUNDARIES} == {"repository_placement", "process_lifetime",
                                                     "operational_persistence", "replaceable_execution",
                                                     "review_and_completion", "worker_repository_access"}
       and {b["decision"] for b in PC16.POLICY_BOUNDARIES} == {"VELDO-DEC-000%d" % i for i in range(3, 9)})

_v16_rep = PC16.activation_report(ROOT)
expect("VELDO-0016 AC1 policy-activation/today: over this repository's records nothing is activated - every "
       "registered boundary refuses as draft, because every record is a draft awaiting Dmitry's decision and "
       "its bound reviews (%s)" % [(r["boundary"], r["refusal"]) for r in _v16_rep["boundaries"]],
       _v16_rep["activated"] == [] and _v16_rep["matrix_problems"] == []
       and all(r["refusal"] == "draft" and not r["accepted"] for r in _v16_rep["boundaries"]))


def _v16_decided(bid, **over):
    """A synthetic DECIDED version of the registered record for boundary bid, with `over` applied
    on top, so each refusal class is exercised one change away from the accepted record."""
    b = PC16.boundary(bid)
    rec = dict(_v16_by_id[b["decision"]])
    rec["status"] = "decided"
    rec["decision"] = {"chosen": b["activating_option"], "decided_by": "dmitry", "decided_at": "2026-09-17"}
    for k, v in over.items():
        if v is None:
            rec.pop(k, None)
        else:
            rec[k] = v
    return rec


for _v16_b in PC16.POLICY_BOUNDARIES:
    _v16_bid = _v16_b["id"]
    _v16_need = 2 if _v16_by_id[_v16_b["decision"]].get("risk") == "critical" else 1
    _v16_cases = [
        ("missing", None, 9),
        ("malformed", {"schema": "veldo.plan/v1", "id": _v16_b["decision"]}, 9),
        ("wrong_record", _v16_decided(_v16_bid, id="VELDO-DEC-0001"), 9),
        ("draft", dict(_v16_by_id[_v16_b["decision"]]), 9),
        ("superseded", _v16_decided(_v16_bid, status="superseded", superseded_by="VELDO-DEC-0099"), 9),
        ("stale", _v16_decided(_v16_bid, version=_v16_b["version"] + 1), 9),
        ("wrong_option", _v16_decided(_v16_bid, decision={"chosen": "not-the-activating-option",
                                                           "decided_by": "dmitry", "decided_at": "2026-09-17"}), 9),
        ("undecided_by_a_person", _v16_decided(_v16_bid, decision={"chosen": _v16_b["activating_option"],
                                                                    "decided_at": "2026-09-17"}), 9),
        ("under_reviewed", _v16_decided(_v16_bid), _v16_need - 1),
    ]
    for _v16_cls, _v16_rec, _v16_have in _v16_cases:
        _v16_ok, _v16_ref, _v16_why = PC16.activation_authority(_v16_bid, _v16_rec, _v16_have, _v16_need)
        expect("VELDO-0016 AC1 policy-activation/%s %s: refused by class %r (%s)"
               % (_v16_cls, _v16_bid, _v16_cls, _v16_why[:110]),
               _v16_ok is False and _v16_ref == _v16_cls)
    _v16_ok, _v16_ref, _v16_why = PC16.activation_authority(_v16_bid, _v16_decided(_v16_bid), _v16_need, _v16_need)
    expect("VELDO-0016 AC1 policy-activation/accepted %s: the registered record, decided by a person, at the "
           "registered version, choosing the activating option, with its %d bound supporting review(s), "
           "activates the boundary and nothing less does" % (_v16_bid, _v16_need),
           _v16_ok is True and _v16_ref is None)
expect("VELDO-0016 AC1 policy-activation/unknown_boundary: a boundary the registry does not know is refused by "
       "class, never treated as unguarded",
       PC16.activation_authority("telepathy", _v16_decided("process_lifetime"), 2, 2)[1] == "unknown_boundary")
expect("VELDO-0016 AC1 policy-activation/review-floor: a required count below one is raised to one, so a decided "
       "record with zero bound reviews never activates even when a policy tier says zero",
       PC16.activation_authority("replaceable_execution", _v16_decided("replaceable_execution"), 0, 0)[1] == "under_reviewed"
       and PC16.activation_authority("replaceable_execution", _v16_decided("replaceable_execution"), 1, 0)[0] is True)

# Matrix teeth: each direction of the comparison, driven with one seeded defect.
_v16_seed = [dict(r) for r in _v16_records]
_v16_seed.append({"schema": PC16.DECISION_SCHEMA, "id": "VELDO-DEC-0090", "policy_boundary": "telepathy", "options": []})
expect("VELDO-0016 AC1 policy-activation/matrix TEETH: a record claiming a boundary the registry does not know is "
       "named", any("telepathy" in m and "does not know" in m for m in PC16.boundary_matrix_problems(_v16_seed)))
_v16_seed = [dict(r) for r in _v16_records if r["id"] != "VELDO-DEC-0006"]
expect("VELDO-0016 AC1 policy-activation/matrix TEETH: a registered decision that resolves to no record is named, "
       "and so is the boundary nobody claims",
       any("VELDO-DEC-0006" in m and "resolves to no decision record" in m for m in PC16.boundary_matrix_problems(_v16_seed)))
_v16_seed = [dict(r) for r in _v16_records]
_v16_seed[[i for i, r in enumerate(_v16_seed) if r["id"] == "VELDO-DEC-0005"][0]]["policy_boundary"] = "process_lifetime"
_v16_twice = PC16.boundary_matrix_problems(_v16_seed)
expect("VELDO-0016 AC1 policy-activation/matrix TEETH: two records claiming one boundary, and the boundary the "
       "moved record abandoned, are each named",
       any("process_lifetime is claimed by 2 records" in m for m in _v16_twice)
       and any("operational_persistence" in m for m in _v16_twice))
_v16_seed = [dict(r) for r in _v16_records]
_v16_i = [i for i, r in enumerate(_v16_seed) if r["id"] == "VELDO-DEC-0007"][0]
_v16_seed[_v16_i]["options"] = [o for o in _v16_seed[_v16_i]["options"] if o["id"] != "gate-and-owner-authorize-review-informs"]
expect("VELDO-0016 AC1 policy-activation/matrix TEETH: a registered activating option the record no longer "
       "declares is named",
       any("gate-and-owner-authorize-review-informs" in m and "does not declare" in m
           for m in PC16.boundary_matrix_problems(_v16_seed)))

# THE DECLARED FALSIFIER: accept a draft process decision as activation authority. The mutant
# removes the draft refusal from a copy of the contract module; the policy-activation/draft row
# for process_lifetime must red under it and pass unmutated (it did, above).
def _v16_mutated_pc(old, new):
    d = Path(tempfile.mkdtemp(prefix="v16pc"))
    src = (ROOT / ".veldo" / "policy_contract.py").read_text()
    assert src.count(old) == 1, (old, src.count(old))
    (d / "policy_contract.py").write_text(src.replace(old, new))
    spec = _v16_ilu.spec_from_file_location("v16_pc_mut_%s" % d.name, d / "policy_contract.py")
    m = _v16_ilu.module_from_spec(spec)
    spec.loader.exec_module(m)
    _v16_shutil.rmtree(d, ignore_errors=True)
    return m


_V16_PCM1 = _v16_mutated_pc('    if status != "decided":\n', '    if False:\n')
_v16_draft_rec = dict(_v16_by_id["VELDO-DEC-0004"])
_v16_m_ok, _v16_m_ref, _v16_m_why = _V16_PCM1.activation_authority("process_lifetime", _v16_draft_rec, 2, 2)
expect("VELDO-0016 AC1 policy-activation/draft DRIVEN (the declared falsifier): with the draft refusal removed, "
       "the draft process decision VELDO-DEC-0004 is no longer refused as draft (it now falls to %r: %s), so the "
       "policy-activation/draft row reds; unmutated it refuses as draft" % (_v16_m_ref, _v16_m_why[:80]),
       _v16_m_ref != "draft"
       and PC16.activation_authority("process_lifetime", _v16_draft_rec, 2, 2)[1] == "draft")
_V16_PCM2 = _v16_mutated_pc('    if version != b["version"]:\n', '    if False:\n')
expect("VELDO-0016 AC1 policy-activation/stale DRIVEN: with the version check removed a re-decided record at "
       "version 2 activates, so the stale row reds; unmutated it refuses as stale",
       _V16_PCM2.activation_authority("operational_persistence", _v16_decided("operational_persistence", version=2), 2, 2)[0] is True
       and PC16.activation_authority("operational_persistence", _v16_decided("operational_persistence", version=2), 2, 2)[1] == "stale")
_V16_PCM3 = _v16_mutated_pc('    if have < need:\n', '    if False:\n')
expect("VELDO-0016 AC1 policy-activation/under_reviewed DRIVEN: with the review count check removed a decided "
       "critical record with one bound review of the two required activates, so the row reds; unmutated it "
       "refuses as under_reviewed",
       _V16_PCM3.activation_authority("review_and_completion", _v16_decided("review_and_completion"), 1, 2)[0] is True
       and PC16.activation_authority("review_and_completion", _v16_decided("review_and_completion"), 1, 2)[1] == "under_reviewed")


# ---------------------------------------------------------------------------------------------
# AC2: the governed runner's R43/R44 obligations replace the lexical ban, behind activation.
# ---------------------------------------------------------------------------------------------
_v16_process = _v16_by_id["VELDO-DEC-0004"]
_v16_obl = PC16.obligation_registry_problems(_v16_process)
expect("VELDO-0016 AC2 policy-activation/obligations: the obligation registry covers every group VELDO-DEC-0004's "
       "replacement_obligations names and nothing else, every obligation cites R43 or R44 and carries a test "
       "registration slot, and the R44 timers are the versioned defaults (10s heartbeat, 30s deadline, 10s then "
       "5s stop, 2s fence) (problems: %s)" % _v16_obl,
       _v16_obl == [] and len(PC16.RUNNER_OBLIGATIONS) == 15
       and (PC16.HEARTBEAT_SECONDS, PC16.LIVENESS_DEADLINE_SECONDS, PC16.STOP_TERMINATE_AFTER_SECONDS,
            PC16.STOP_KILL_AFTER_SECONDS, PC16.LEADERSHIP_FENCE_SECONDS) == (10, 30, 10, 5, 2))
_v16_rec_less = dict(_v16_process)
_v16_rec_less["replacement_obligations"] = {k: v for k, v in _v16_process["replacement_obligations"].items() if k != "retirement"}
_v16_rec_more = dict(_v16_process)
_v16_rec_more["replacement_obligations"] = dict(_v16_process["replacement_obligations"], telemetry="x")
expect("VELDO-0016 AC2 policy-activation/obligations TEETH: a record that drops a group and a record that names a "
       "group the registry lacks are each named",
       any("retirement" in m and "does not name" in m for m in PC16.obligation_registry_problems(_v16_rec_less))
       and any("telemetry" in m for m in PC16.obligation_registry_problems(_v16_rec_more)))

_v16_elig, _v16_missing = PC16.runner_profile_eligible()
expect("VELDO-0016 AC2 policy-activation/eligibility: with no test registered the governed runner profile is NOT "
       "eligible and every one of the %d obligations is named as untested" % len(PC16.RUNNER_OBLIGATIONS),
       _v16_elig is False and _v16_missing == [o["id"] for o in PC16.RUNNER_OBLIGATIONS])
_v16_all = {o["id"]: "scripts/suites/40_fake_%s.py" % o["id"] for o in PC16.RUNNER_OBLIGATIONS}
_v16_one_short = dict(_v16_all)
del _v16_one_short["hard_memory_limit"]
expect("VELDO-0016 AC2 policy-activation/eligibility: every obligation registered makes the profile eligible; one "
       "missing registration refuses it naming that obligation (no partial eligibility)",
       PC16.runner_profile_eligible(_v16_all) == (True, [])
       and PC16.runner_profile_eligible(_v16_one_short) == (False, ["hard_memory_limit"]))

_v16_full = {p: True for p in PC16.RETIREMENT_PROOFS}
expect("VELDO-0016 AC2 policy-activation/retirement-obligation: retirement is allowed only with every proof present "
       "and true, and each missing proof refuses it by name; empty containment is one of the four",
       PC16.retirement_allowed(_v16_full) == (True, [])
       and all(PC16.retirement_allowed(dict(_v16_full, **{p: False})) == (False, [p]) for p in PC16.RETIREMENT_PROOFS)
       and PC16.retirement_allowed({}) == (False, list(PC16.RETIREMENT_PROOFS))
       and "containment_empty" in PC16.RETIREMENT_PROOFS)
expect("VELDO-0016 AC2 policy-activation/retirement-obligation: silence is not proof - an evidence value that is "
       "not literally True (a truthy string, None, 1) does not count",
       PC16.retirement_allowed(dict(_v16_full, containment_empty="yes"))[0] is False
       and PC16.retirement_allowed(dict(_v16_full, containment_empty=1))[0] is False)

# THE DECLARED FALSIFIER: remove the empty-containment proof from the retirement predicate; the row
# above must red under the mutant and pass unmutated (it did).
_V16_PCM4 = _v16_mutated_pc('RETIREMENT_PROOFS = ("containment_empty", "outcome_recorded", "accounting_recorded", "cleanup_done")',
                            'RETIREMENT_PROOFS = ("outcome_recorded", "accounting_recorded", "cleanup_done")')
expect("VELDO-0016 AC2 policy-activation/retirement-obligation DRIVEN (the declared falsifier): with the "
       "empty-containment proof removed from the retirement predicate, a slot with unproven emptiness is "
       "released, so the row reds; unmutated it is refused by name",
       _V16_PCM4.retirement_allowed(dict(_v16_full, containment_empty=False))[0] is True
       and PC16.retirement_allowed(dict(_v16_full, containment_empty=False)) == (False, ["containment_empty"]))

# The scoped exception clause in this repository's contract, and its teeth.
_v16_contract = V.load_contract_state(str(ROOT)).contract
expect("VELDO-0016 AC2 policy-activation/exception: this repository's contract (revision 2) declares the "
       "project_runner area and exactly one exception clause, on no_detached_processes, for that area, "
       "activated by the process_lifetime boundary; the contract validator accepts it and the policy contract "
       "finds no problem (%s)" % PC16.exception_clause_problems(_v16_contract),
       _v16_contract is not None and _v16_contract.get("version") == 2
       and PC16.exception_clause_problems(_v16_contract) == []
       and [(r, ex["area"], ex["activated_by"]) for r, ex in PC16.exception_clauses(_v16_contract)]
       == [("no_detached_processes", "project_runner", "process_lifetime")]
       and "project_runner" in _v16_contract["areas"][-1]["id"])
import copy as _v16_copy
_v16_c1 = _v16_copy.deepcopy(_v16_contract)
_v16_c1["invariants"][0]["exceptions"][0]["area"] = "fleet"
_v16_c2 = _v16_copy.deepcopy(_v16_contract)
_v16_c2["invariants"][0]["exceptions"][0]["activated_by"] = "telepathy"
_v16_c3 = _v16_copy.deepcopy(_v16_contract)
_v16_c3["patterns"][0]["exceptions"] = [dict(_v16_contract["invariants"][0]["exceptions"][0])]
_v16_c4 = _v16_copy.deepcopy(_v16_contract)
_v16_c4["invariants"][0]["exceptions"][0]["activated_by"] = "repository_placement"
expect("VELDO-0016 AC2 policy-activation/exception TEETH: an exception for another area (the floor's fleet), one "
       "activated by an unregistered boundary, one on a second rule, and one activated by a registered but "
       "wrong boundary are each refused by name",
       any("only project_runner is excepted" in m for m in PC16.exception_clause_problems(_v16_c1))
       and any("telepathy" in m and "not a registered policy boundary" in m for m in PC16.exception_clause_problems(_v16_c2))
       and any("only no_detached_processes may" in m for m in PC16.exception_clause_problems(_v16_c3))
       and any("permits exactly one" in m for m in PC16.exception_clause_problems(_v16_c3))
       and any("repository_placement" in m and "activated by process_lifetime" in m for m in PC16.exception_clause_problems(_v16_c4)))
_v16_c5 = _v16_copy.deepcopy(_v16_contract)
_v16_c5["invariants"][0]["exceptions"][0]["area"] = "nowhere"
_v16_arch_errs = []
V._arch_module().validate_contract(_v16_c5, str(ROOT), "fixture", lambda _n, m: (_v16_arch_errs.append(m), 1)[1])
expect("VELDO-0016 AC2 policy-activation/exception TEETH: the contract validator itself refuses an exception clause "
       "naming an undeclared area or missing a field (referenced but absent), so a malformed clause never loads",
       any("exception area 'nowhere' is not a declared area" in m for m in _v16_arch_errs)
       and V._arch_module().validate_contract(
           {**_v16_copy.deepcopy(_v16_contract), "invariants": [{"id": "x", "text": "t", "enforcement": "review",
                                                                 "exceptions": [{"area": "fleet"}]}]},
           str(ROOT), "fixture", lambda _n, m: 1) >= 2)

# Effective only through activation: today it is not, and each precondition is named in turn.
_v16_eff, _v16_why = PC16.exception_effective(_v16_contract, _v16_rep["boundaries"])
expect("VELDO-0016 AC2 policy-activation/exception: over this repository the exception is NOT in force - the "
       "process_lifetime boundary is a draft (%s)" % _v16_why[:100],
       _v16_eff is False and "not activated" in _v16_why)
_v16_rows_on = [dict(r, accepted=(r["boundary"] == "process_lifetime"), refusal=None) for r in _v16_rep["boundaries"]]
expect("VELDO-0016 AC2 policy-activation/exception: with the boundary activated but no obligation tested, the "
       "exception is still not in force (qualification is separate from the decision); with every obligation "
       "registered it is; on a contract at another revision it is not; without the clause it is not",
       PC16.exception_effective(_v16_contract, _v16_rows_on)[0] is False
       and "not eligible" in PC16.exception_effective(_v16_contract, _v16_rows_on)[1]
       and PC16.exception_effective(_v16_contract, _v16_rows_on, _v16_all) == (True, "the process exception is in force for the project_runner area")
       and PC16.exception_effective(dict(_v16_contract, version=1), _v16_rows_on, _v16_all)[0] is False
       and "revision" in PC16.exception_effective(dict(_v16_contract, version=1), _v16_rows_on, _v16_all)[1]
       and PC16.exception_effective(dict(_v16_contract, invariants=[dict(i, exceptions=None) for i in _v16_contract["invariants"]]),
                                    _v16_rows_on, _v16_all)[0] is False)

# The lexical scan stays where it is and is not extended to the runner.
_v16_scan_src = (ROOT / PC16.LEXICAL_SCAN_SCOPE["suite"]).read_text()
expect("VELDO-0016 AC2 policy-activation/lexical-scan: the floor's detach-token scan in suite 06 still reads "
       ".veldo/fleet.py, still defines _DETACH_TOKENS and _no_detached_worker_spawn, and names no project_runner "
       "module: the prohibition is replaced for the governed runner by the obligations above, never extended",
       '(ROOT / ".veldo/fleet.py").read_text()' in _v16_scan_src
       and "_DETACH_TOKENS = (" in _v16_scan_src and "def _no_detached_worker_spawn(" in _v16_scan_src
       and PC16.LEXICAL_SCAN_SCOPE["never_targets"] not in _v16_scan_src)


# ---------------------------------------------------------------------------------------------
# AC4: the boundary table. Every clause has a predicate here, every predicate rejects its seeded
# violation and accepts a clean case, and the review-is-not-authority row is driven by a mutant.
# ---------------------------------------------------------------------------------------------
expect("VELDO-0016 AC4 policy-boundaries/table: the clause-to-predicate table covers exactly R21, R35, R46, R50 "
       "and R53, and every predicate it names is a callable of the contract module",
       [r["clause"] for r in PC16.BOUNDARY_TABLE] == ["R21", "R35", "R46", "R50", "R53"]
       and all(callable(getattr(PC16, r["predicate"], None)) for r in PC16.BOUNDARY_TABLE)
       and all(r["seeded_violation"] for r in PC16.BOUNDARY_TABLE))

# R21
expect("VELDO-0016 AC4 policy-boundaries/checkpoint-isolation: a checkpoint-namespace statement is allowed; the "
       "seeded INSERT ... SELECT from a domain table, a bare domain read, an ATTACH, a view over a domain table "
       "and a statement naming no checkpoint table are each refused by name",
       PC16.checkpoint_statement_allowed("INSERT INTO langgraph_checkpoints (id, blob) VALUES (?, ?)")[0] is True
       and PC16.checkpoint_statement_allowed(PC16.BOUNDARY_TABLE[0]["seeded_violation"]) == (
           False, "statement names domain table(s) claims: checkpoint writes cannot touch domain tables (R21)")
       and PC16.checkpoint_statement_allowed("SELECT * FROM journal")[0] is False
       and PC16.checkpoint_statement_allowed("ATTACH DATABASE 'control.sqlite3' AS other")[1].startswith("statement uses ATTACH")
       and PC16.checkpoint_statement_allowed("CREATE VIEW langgraph_v AS SELECT * FROM receipts")[1].startswith("statement uses CREATE VIEW")
       and PC16.checkpoint_statement_allowed("SELECT 1")[0] is False
       and PC16.checkpoint_statement_allowed("select id from main.langgraph_writes where thread_id = ?")[0] is True)

# R35: over the real engine, then the seeded violation in a temporary tree, executing nothing.
_v16_clean, _v16_imp = PC16.enforcement_imports_stdlib_only(ROOT)
expect("VELDO-0016 AC4 policy-boundaries/stdlib-enforcement: every enforcement module of this engine imports the "
       "standard library only, decided by an AST walk that executes nothing (problems: %s)" % _v16_imp,
       _v16_clean is True and _v16_imp == [] and len(PC16.ENFORCEMENT_MODULES) >= 12)
with tempfile.TemporaryDirectory(prefix="v16r35") as _v16_r35:
    (Path(_v16_r35) / ".veldo").mkdir()
    for _v16_rel in PC16.ENFORCEMENT_MODULES:
        _v16_shutil.copyfile(ROOT / _v16_rel, Path(_v16_r35) / _v16_rel)
    (Path(_v16_r35) / ".veldo" / "authorization.py").write_text("import langgraph\n" + (ROOT / ".veldo/authorization.py").read_text())
    _v16_bad, _v16_bad_p = PC16.enforcement_imports_stdlib_only(_v16_r35)
    expect("VELDO-0016 AC4 policy-boundaries/stdlib-enforcement: the seeded violation (authorization importing "
           "langgraph) is refused by module and name, and the walk needs no langgraph installed to say so",
           _v16_bad is False and _v16_bad_p == [".veldo/authorization.py imports langgraph, which is not the standard library (R35)"]
           and "langgraph" not in sys.modules)
    (Path(_v16_r35) / ".veldo" / "arch.py").unlink()
    expect("VELDO-0016 AC4 policy-boundaries/stdlib-enforcement: a missing enforcement module is a problem, never clean",
           ".veldo/arch.py is missing" in PC16.enforcement_imports_stdlib_only(_v16_r35)[1])
expect("VELDO-0016 AC4 policy-boundaries/stdlib-enforcement: loading the engine's validate.py brought no execution "
       "runtime into the process (no langgraph module is loaded)",
       not any(m == "langgraph" or m.startswith("langgraph.") for m in sys.modules))

# R46
_v16_receipt_ok = {k: True for k in PC16.LANDING_REQUIREMENTS}
expect("VELDO-0016 AC4 policy-boundaries/review-is-not-authority: a receipt with every requirement true authorizes; "
       "the seeded receipt carrying verdict pass and nothing else is refused with all seven requirements missing; "
       "one open blocking finding or a builder who is the reviewer refuses by name",
       PC16.landing_authorized(_v16_receipt_ok) == (True, [])
       and PC16.landing_authorized({"verdict": "pass"}) == (False, list(PC16.LANDING_REQUIREMENTS))
       and PC16.landing_authorized(dict(_v16_receipt_ok, blocking_findings_disposed=False)) == (False, ["blocking_findings_disposed"])
       and PC16.landing_authorized(dict(_v16_receipt_ok, builder_differs_from_reviewer=False)) == (False, ["builder_differs_from_reviewer"])
       and PC16.landing_authorized(dict(_v16_receipt_ok, verdict="fail")) == (True, []))
# THE DECLARED FALSIFIER: treat a passing reviewer assertion as landing authorization.
_V16_PCM5 = _v16_mutated_pc("""    missing = [k for k in LANDING_REQUIREMENTS if receipt.get(k) is not True]
    return (not missing), missing
""", """    if receipt.get("verdict") == "pass":
        return True, []  # mutant: the verdict authorizes
    missing = [k for k in LANDING_REQUIREMENTS if receipt.get(k) is not True]
    return (not missing), missing
""")
expect("VELDO-0016 AC4 policy-boundaries/review-is-not-authority DRIVEN (the declared falsifier): with a passing "
       "verdict treated as authorization, the seeded receipt lands, so the row reds; unmutated it is refused",
       _V16_PCM5.landing_authorized({"verdict": "pass"})[0] is True
       and PC16.landing_authorized({"verdict": "pass"})[0] is False)

# R50
with tempfile.TemporaryDirectory(prefix="v16r50") as _v16_r50:
    _v16_cand = Path(_v16_r50) / "candidate"
    (_v16_cand / "scripts").mkdir(parents=True)
    _v16_inst = Path(_v16_r50) / "installed" / "veldo" / "scripts"
    _v16_inst.mkdir(parents=True)
    expect("VELDO-0016 AC4 policy-boundaries/installed-verifier: a verifier outside the candidate tree is independent; "
           "the seeded verifier inside the candidate tree, and the candidate root itself, are refused",
           PC16.verifier_independent(_v16_inst / "verify.sh", _v16_cand)[0] is True
           and PC16.verifier_independent(_v16_cand / "scripts" / "verify.sh", _v16_cand)[0] is False
           and PC16.verifier_independent(_v16_cand, _v16_cand)[0] is False
           and "cannot supply the enforcement" in PC16.verifier_independent(_v16_cand / "scripts" / "verify.sh", _v16_cand)[1])

# R53
expect("VELDO-0016 AC4 policy-boundaries/exclusive-responsibilities: each of the four actions is allowed to its owner "
       "alone; the seeded violation (the runner publishing source), a store launching an engine, and an unassigned "
       "action are each refused by name",
       all(PC16.responsibility_allowed(o, a)[0] is True for a, o in PC16.RESPONSIBILITIES.items())
       and PC16.responsibility_allowed("runner", "publish_source") == (False, "only the lander may publish_source; 'runner' may not (R53)")
       and PC16.responsibility_allowed("store", "launch_engine")[0] is False
       and PC16.responsibility_allowed("store", "delete_history")[0] is False
       and set(PC16.RESPONSIBILITIES.values()) == {"store", "runner", "lander", "evidence_service"})
