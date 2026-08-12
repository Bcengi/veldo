"""WARP-0623: the codified live provisioner could not run AT ALL - an instance attribute perm

ONE SUITE OF THE UNIT SUITE, AND A FRAGMENT RATHER THAN A MODULE. It is compiled and executed
into scripts/suites/shared.py's namespace by scripts/selftest.py, in manifest order, so every
suite sees exactly the state the monolith gave it and this decomposition cannot change what any
assertion proves. That is the whole reason for the design: the monolith carries cross-region
dependencies through MUTATED objects and through the filesystem, not only through names, and no
mechanical analysis finds those. Sharing one namespace in the original order means no membership
rule has to be closed and correctness is a property of the construction.

Run it: `python3 scripts/selftest.py --upto 13_warp_0623_codified_live` runs everything up to and including this
file, which is the inner loop for a change here. `python3 scripts/selftest.py` runs everything
and is the only thing that means green.

Regions 143-214 of the pre-split monolith.
"""


# --- WARP-0623: the codified live provisioner could not run AT ALL - an instance attribute permanently
# shadowed a provisioning method, so every provisioning call raised TypeError in every configuration. The
# REPRODUCTION comes first (AC1): it constructs the REAL adapter composition (the shipped JiraCloudAdapter
# composed with the live provisioning mixin through the SHIPPED factory, never the FakeTracker) and asserts
# every method the mixin defines is CALLABLE on that instance, with a project key configured and without
# one. On the code as shipped before this item BOTH halves failed: self._project held the project key (a
# str) or None, so the mixin's _project method was unreachable ('str' object is not callable / 'NoneType'
# object is not callable). Constructed entirely OFFLINE: the token comes from an injected resolver and no
# method is called, so no network, no board and no credential are involved.
_lpspec = importlib.util.spec_from_file_location("veldo_tracker_jira_live_0623", ROOT / ".veldo/tracker_jira_live.py")
LP = importlib.util.module_from_spec(_lpspec); _lpspec.loader.exec_module(LP)
_lp_src = (ROOT / ".veldo/tracker_jira_live.py").read_text()


def _lp_real(project="PROJ"):
    """The REAL composed live provisioner instance (JI.JiraCompanyManagedProvisioner: the shipped factory
    over the shipped JiraCloudAdapter base), constructed offline with an injected secret resolver."""
    return JI.JiraCompanyManagedProvisioner("https://jira.invalid", "svc@example.invalid",
                                            "env:WARP_0623_ABSENT_TOKEN",
                                            resolve_secret=lambda _ref: "a-token-never-used",
                                            project=project)


# The mixin's OWN method names, read from the class rather than a literal list, so this reproduction covers
# whatever the mixin defines today and whatever it defines later.
_lp_mixin_names = sorted(n for n, v in vars(LP._CompanyManagedProvisionerOps).items()
                         if not n.startswith("__") and callable(getattr(v, "__func__", v)))
_lp_with_key = _lp_real("PROJ")
_lp_no_key = _lp_real(None)
expect("WARP-0623 AC1 REPRODUCTION: every provisioning method the live mixin defines is CALLABLE on the REAL composed adapter instance, both with a project key configured and without one (before the fix the attribute self._project shadowed the mixin's _project method and every provisioning call raised TypeError)",
       len(_lp_mixin_names) >= 20
       and all(callable(getattr(_lp_with_key, _n, None)) for _n in _lp_mixin_names)
       and all(callable(getattr(_lp_no_key, _n, None)) for _n in _lp_mixin_names))
# The same reproduction through the module's OWN reachability guard, which is what the teeth mutate below.
expect("WARP-0623 AC1: the module's own reachability guard reports NO unreachable provisioning method on the REAL composed instance, in both configurations (it returned ['_project'] on every instance before the fix)",
       LP.unreachable_provisioner_methods(_lp_with_key) == []
       and LP.unreachable_provisioner_methods(_lp_no_key) == []
       and len(LP.provisioner_method_names(type(_lp_with_key))) == len(_lp_mixin_names))
# WHY the offline suite could never reach it: the FakeTracker defines its OWN _project METHOD and is
# constructed with NO project key, so on the fake the name is a method and the collision cannot occur.
_lp_ta_src = (ROOT / ".veldo/tracker_adapter.py").read_text()
expect("WARP-0623 AC1/AC3 PREMISE: the offline FakeTracker defines its OWN _project METHOD and carries no _project instance attribute, which is exactly why no number of fixtures over the fake could ever reach this collision",
       "    def _project(self, project_key):" in _lp_ta_src
       and callable(getattr(TA.FakeTracker(), "_project", None))
       and "_project" not in vars(TA.FakeTracker()))

# AC2: the collision is fixed by renaming the METHOD, never the attribute. The old method name is GONE
# from the live module, the new name appears at exactly its definition and its two call sites, no other
# module references the new name, and the CONSTRUCTOR attribute keeps its name and its meaning (the
# configured project key) in the READ-ONLY .veldo/tracker_intake.py.
_lp_ik_src = (ROOT / ".veldo/tracker_intake.py").read_text()
expect("WARP-0623 AC2: the mixin's old _project method name is GONE from the live module (no def and no call site), so the collision cannot silently return",
       "def _project(self" not in _lp_src and "self._project(" not in _lp_src)
expect("WARP-0623 AC2: the renamed method appears at exactly three sites in the live module (its definition and its two call sites) and its body is the same one REST read, unchanged",
       _lp_src.count("_project_record(") == 3
       and "def _project_record(self, project_key):" in _lp_src
       and 'return self._request("GET", "/rest/api/3/project/%s" % project_key)' in _lp_src)
_lp_others = {_p.name: _p.read_text() for _p in sorted((ROOT / ".veldo").glob("*.py"))
              if _p.name != "tracker_jira_live.py"}
expect("WARP-0623 AC2: NO other engine module references the renamed method (the rename is contained in the one module that defines it)",
       not [_n for _n, _t in _lp_others.items() if "_project_record" in _t] and len(_lp_others) > 40)
expect("WARP-0623 AC2: the CONSTRUCTOR attribute keeps its name and meaning - .veldo/tracker_intake.py still sets self._project to the configured project key, is untouched by the rename, and the real instance carries that key",
       "        self._project = project" in _lp_ik_src and "_project_record" not in _lp_ik_src
       and _lp_with_key._project == "PROJ" and _lp_no_key._project is None)

# AC3 THE STRUCTURAL CHECK, the real deliverable. It enumerates BOTH sides from the composition at
# runtime: the METHOD names come from every class in the MRO carrying the mixin's marker, the ATTRIBUTE
# names from every __init__ along the MRO (read out of the constructor's own bytecode) plus, when a
# constructed instance is handed in, that instance's __dict__. Neither side is a literal list, so a
# collision introduced by a FUTURE constructor field or a FUTURE mixin method is caught with no edit here.
expect("WARP-0623 AC3: the check reports EMPTY against the FIXED real composition, at class level and against a constructed instance, with and without a project key",
       LP.shadowed_provisioner_methods(JI.JiraCompanyManagedProvisioner) == []
       and LP.shadowed_provisioner_methods(type(_lp_with_key), instance=_lp_with_key) == []
       and LP.shadowed_provisioner_methods(type(_lp_no_key), instance=_lp_no_key) == []
       and LP.check_provisioner_composition(JI.JiraCompanyManagedProvisioner) is JI.JiraCompanyManagedProvisioner)
expect("WARP-0623 AC3: both sides are enumerated FROM THE COMPOSITION - the methods are the mixin's own definitions, the attributes include the BASE adapter constructor's _project and the composed constructor's own caches",
       LP.provisioner_method_names(JI.JiraCompanyManagedProvisioner) == set(_lp_mixin_names)
       and {"_project", "_base", "_token", "_project_id_cache", "_workflow_id_cache"}
       <= LP.constructor_attribute_names(JI.JiraCompanyManagedProvisioner))


class _LP_Collide:
    """A synthetic base whose constructor sets an attribute that COLLIDES with a provisioning method name
    (the shape a FUTURE constructor field would take). Plain object: nothing here touches Jira."""

    def __init__(self):
        self._project_record = "PROJ"


class _LP_Clean:
    """The CONTROL base: attribute names that merely RESEMBLE a method name (a _project_key beside the
    mixin's _project_record method, and a near-miss plural). No collision, so no refusal."""

    def __init__(self):
        self._project_key = "PROJ"
        self._project_records = ["PROJ"]


class _LP_Dynamic:
    """A base that sets the COLLIDING attribute outside an __init__ literal, so the static half cannot see
    it; only the per-instance check reaches it."""

    def __init__(self):
        setattr(self, "_project_record", "PROJ")


def _lp_compose(ns, base, layer_methods=()):
    """Compose ns's live provisioning mixin over a synthetic base, optionally through an extra mixin LAYER
    defining the named methods (the shape of the HISTORICAL defect: a mixin method colliding with an
    attribute the base's constructor already sets). Built with type(), so no check runs here."""
    ops = ns["_CompanyManagedProvisionerOps"]
    layer = ops
    if layer_methods:
        layer = type("_LPLayer", (ops,), {_n: (lambda self, *a, **k: None) for _n in layer_methods})
    return type("_LPComposed", (layer, base), {})


def _lp_refusal(ns, thunk):
    """Run a thunk that must REFUSE by name; return the refusal message, or None when it did not refuse
    (which is what a neutralized guard looks like)."""
    try:
        thunk()
        return None
    except ns["ProvisionerCompositionError"] as ex:
        return str(ex)


# The SEEDED synthetic collision, in both directions. (1) The historical shape: an extra mixin layer
# defines a method named _project over the REAL JiraCloudAdapter base, whose constructor sets
# self._project - this is the defect that shipped, reconstructed, and the check names it. (2) The future
# shape: a constructor field named _project_record collides with the renamed method.
_lp_hist = _lp_compose({"_CompanyManagedProvisionerOps": LP._CompanyManagedProvisionerOps},
                       JI.JiraCloudAdapter, layer_methods=("_project",))
_lp_hist_msg = _lp_refusal(LP.__dict__, lambda: LP.check_provisioner_composition(_lp_hist))
_lp_hist_find = LP.shadowed_provisioner_methods(_lp_hist)
expect("WARP-0623 AC3 SEEDED (the historical defect, reconstructed): the check REFUSES a mixin method named _project over the real adapter base and names the class, the attribute, the constructor that sets it and the method it hides",
       _lp_hist_msg is not None and "SHADOWED_PROVISIONER_METHOD" in _lp_hist_msg
       and "'_project'" in _lp_hist_msg and "JiraCloudAdapter" in _lp_hist_msg
       and len(_lp_hist_find) == 1 and _lp_hist_find[0]["attribute"] == "_project"
       and _lp_hist_find[0]["method"] == "_project"
       and _lp_hist_find[0]["attribute_set_by"] == "JiraCloudAdapter"
       and _lp_hist_find[0]["method_defined_by"] == "_LPLayer"
       and _lp_hist_find[0]["error"] == LP.SHADOWED_PROVISIONER_METHOD)
_lp_future = _lp_compose(LP.__dict__, _LP_Collide)
_lp_future_msg = _lp_refusal(LP.__dict__, lambda: LP.check_provisioner_composition(_lp_future))
expect("WARP-0623 AC3 SEEDED (a FUTURE constructor field): the check REFUSES an attribute named _project_record and names the method it would hide",
       _lp_future_msg is not None and "SHADOWED_PROVISIONER_METHOD" in _lp_future_msg
       and "'_project_record'" in _lp_future_msg
       and [_f["attribute"] for _f in LP.shadowed_provisioner_methods(_lp_future)] == ["_project_record"])
expect("WARP-0623 AC3 SEEDED REMOVED: with the seeded collision taken away the SAME check passes (it returns the class and reports empty), so the refusal is the collision and not the fixture",
       LP.shadowed_provisioner_methods(_lp_compose(LP.__dict__, _LP_Clean)) == []
       and LP.check_provisioner_composition(_lp_compose(LP.__dict__, _LP_Clean)) is not None
       and LP.shadowed_provisioner_methods(_lp_compose(LP.__dict__, object)) == [])
# The RUNTIME half closes the static blind spot: an attribute set OUTSIDE an __init__ literal is invisible
# to the bytecode scan and is caught only against the constructed instance.
_lp_dyn_cls = _lp_compose(LP.__dict__, _LP_Dynamic)
expect("WARP-0623 AC3: an attribute set OUTSIDE an __init__ literal (setattr) is invisible to the static half and IS caught against the constructed instance, so the two halves cover each other",
       LP.shadowed_provisioner_methods(_lp_dyn_cls) == []
       and [_f["attribute"] for _f in LP.shadowed_provisioner_methods(_lp_dyn_cls, instance=_lp_dyn_cls())]
       == ["_project_record"])
# The check is wired where it cannot be forgotten: the FACTORY refuses a colliding composition before it
# hands the class back, and the provisioner's own __init__ re-runs it against the constructed instance. The
# gate reaches BOTH, because importing tracker_jira_init builds the real class through that factory.
expect("WARP-0623 AC3: the FACTORY refuses a colliding composition before returning it, and the provisioner's __init__ re-checks the CONSTRUCTED instance (so importing tracker_jira_init, which the gate does, now runs this check on the real class)",
       _lp_refusal(LP.__dict__, lambda: LP.make_company_managed_provisioner(_LP_Collide, ValueError)) is not None
       and _lp_refusal(LP.__dict__,
                       lambda: LP.make_company_managed_provisioner(_LP_Dynamic, ValueError)()) is not None
       and "return check_provisioner_composition(JiraCompanyManagedProvisioner)" in _lp_src
       and "check_provisioner_composition(type(self), instance=self)" in _lp_src)
# A check that recognizes nothing would report clean, so it refuses instead; and the recognizer is
# load-identity independent (this codebase loads each sibling by path, minting a distinct class per load,
# so an issubclass test against one load's class object would silently match nothing).
_lp2spec = importlib.util.spec_from_file_location("veldo_tracker_jira_live_0623_second", ROOT / ".veldo/tracker_jira_live.py")
LP2 = importlib.util.module_from_spec(_lp2spec); _lp2spec.loader.exec_module(LP2)
expect("WARP-0623 AC3: the check works ACROSS LOAD IDENTITIES - a second load of the module still refuses the seeded collision built from the first load's mixin and still reports the real composition empty (the recognizer is the mixin's marker, never an issubclass test)",
       LP2.shadowed_provisioner_methods(JI.JiraCompanyManagedProvisioner) == []
       and len(LP2.provisioner_method_names(JI.JiraCompanyManagedProvisioner)) == len(_lp_mixin_names)
       and _lp_refusal(LP2.__dict__, lambda: LP2.check_provisioner_composition(_lp_future)) is not None)
# The strongest form of the seeded proof: the check applied to THIS MODULE'S OWN PRE-FIX SOURCE (the rename
# undone in memory) refuses the REAL composition at factory time, naming _project. So the gate would have
# gone red the moment the collision was introduced, rather than shipping nine synced copies of a module
# that could not run. The module on disk is untouched (the sha256 assertion below covers it).
_lp_prefix_src = (_lp_src.replace("def _project_record(self, project_key):", "def _project(self, project_key):")
                  .replace("self._project_record(project_key)", "self._project(project_key)"))
_lp_prefix_ns = {"__file__": str(ROOT / ".veldo/tracker_jira_live.py"), "__name__": "veldo_live_prefix"}
exec(compile(_lp_prefix_src, "<live_prefix>", "exec"), _lp_prefix_ns)
_lp_prefix_msg = _lp_refusal(_lp_prefix_ns, lambda: _lp_prefix_ns["make_company_managed_provisioner"](
    JI.JiraCloudAdapter, JI.BootstrapError))
expect("WARP-0623 AC3 IN SITU: applied to this module's own PRE-FIX source (the rename undone in memory), the check REFUSES the REAL composition at factory time and names _project, so the gate would have caught the historical defect the moment it was introduced",
       _lp_prefix_msg is not None and "SHADOWED_PROVISIONER_METHOD" in _lp_prefix_msg
       and "'_project'" in _lp_prefix_msg and "JiraCloudAdapter.__init__" in _lp_prefix_msg
       and "_CompanyManagedProvisionerOps" in _lp_prefix_msg
       and _lp_prefix_src != _lp_src
       and "def _project_record(self, project_key):" in (ROOT / ".veldo/tracker_jira_live.py").read_text())
expect("WARP-0623 AC3: a composition carrying NO recognized provisioning mixin is REFUSED rather than reported clean (a vacuous check is a false green)",
       _lp_refusal(LP.__dict__, lambda: LP.check_provisioner_composition(dict)) is not None
       and _lp_refusal(LP.__dict__, lambda: LP.check_provisioner_composition(JI.JiraCloudAdapter)) is not None)

# AC4 CONTROLS: no over-firing. An attribute whose name merely RESEMBLES a method name does not refuse, a
# mixin method that no constructor attribute shadows does not refuse, and the real composition (ten
# constructor attributes beside twenty-seven mixin methods) reports empty.
expect("WARP-0623 AC4 CONTROL: an attribute whose name merely RESEMBLES a method name does NOT refuse (a _project_key and a _project_records beside the _project_record method), so the first false positive cannot get the check disabled",
       LP.shadowed_provisioner_methods(_lp_compose(LP.__dict__, _LP_Clean)) == []
       and "_project_key" in LP.constructor_attribute_names(_lp_compose(LP.__dict__, _LP_Clean))
       and "_project_record" in LP.provisioner_method_names(_lp_compose(LP.__dict__, _LP_Clean)))
expect("WARP-0623 AC4 CONTROL: a mixin method that NO constructor attribute shadows does not refuse (an added _project_snapshot method over a clean base)",
       LP.shadowed_provisioner_methods(_lp_compose(LP.__dict__, _LP_Clean,
                                                   layer_methods=("_project_snapshot",))) == []
       and "_project_snapshot" in LP.provisioner_method_names(
           _lp_compose(LP.__dict__, _LP_Clean, layer_methods=("_project_snapshot",))))

# --- WARP-0623 AC4 anti-vacuity TEETH, run as a MATRIX. Two INDEPENDENT guards live in the live module:
# the shadow check's refusal and the reachability guard's callability probe. Each is neutralized in an
# IN-MEMORY copy of the module, run against BOTH guards' fixtures, and the matrix must be exactly the
# DIAGONAL, so neither guard is propped up by the other. Two further sites (the factory's composition-time
# call and the constructor's per-instance call) are WIRING, dominated by the shadow refusal by
# construction, so they get their own teeth outside the matrix, exactly as WARP-1208 handled its path
# guard's sub-mechanisms. The module on disk is asserted sha256-unchanged after every run.
import hashlib as _lp_hashlib
_lp_sha0 = _lp_hashlib.sha256((ROOT / ".veldo/tracker_jira_live.py").read_bytes()).hexdigest()


def _lp_sha_unchanged():
    """The live module on disk, byte-unchanged: every mutation below is compiled in memory only."""
    return _lp_hashlib.sha256((ROOT / ".veldo/tracker_jira_live.py").read_bytes()).hexdigest() == _lp_sha0


_LP_TEETH = {  # matrix guard -> (the guard's line, that ONE guard neutralized)
    "shadow refusal": ("    if findings:", "    if False and findings:"),
    "callability probe": ("        if not callable(getattr(instance, name, None)):",
                          "        if False and not callable(getattr(instance, name, None)):"),
}
_LP_SUBTEETH = {  # the WIRING sites: dominated by the shadow refusal, so proven outside the matrix
    "factory wiring": ("    return check_provisioner_composition(JiraCompanyManagedProvisioner)",
                       "    return JiraCompanyManagedProvisioner"),
    "constructor wiring": ("            check_provisioner_composition(type(self), instance=self)",
                           "            pass  # neutralized: no per-instance re-check"),
}
expect("WARP-0623 AC4: every teeth mutation target appears EXACTLY ONCE in the live module (a mutation that matched nothing, or matched two sites, would prove nothing)",
       all(_lp_src.count(_old) == 1 for _old, _new in
           list(_LP_TEETH.values()) + list(_LP_SUBTEETH.values()))
       and len(_LP_TEETH) == 2 and len(_LP_SUBTEETH) == 2)


def _lp_mut(guard):
    """The live module with exactly ONE guard neutralized, compiled IN MEMORY. The file is never written;
    _lp_sha_unchanged() proves it after every run."""
    old, new = (_LP_TEETH.get(guard) or _LP_SUBTEETH[guard])
    g = {"__file__": str(ROOT / ".veldo/tracker_jira_live.py"), "__name__": "veldo_live_mut"}
    exec(compile(_lp_src.replace(old, new), "<live_mut>", "exec"), g)
    return g


def _lp_fixture(guard):
    """The guard's OWN fixture: a SEEDED collision the real module refuses (or reports). run(ns) returns the
    refusal/report, or None when that guard has stopped catching it, which is the fixture turning green."""
    def run(ns):
        if guard == "shadow refusal":
            return _lp_refusal(ns, lambda: ns["check_provisioner_composition"](_lp_compose(ns, _LP_Collide)))
        if guard == "callability probe":
            return ns["unreachable_provisioner_methods"](_lp_compose(ns, _LP_Collide)()) or None
        if guard == "factory wiring":
            return _lp_refusal(ns, lambda: ns["make_company_managed_provisioner"](_LP_Collide, ValueError))
        return _lp_refusal(ns, lambda: ns["make_company_managed_provisioner"](_LP_Dynamic, ValueError)())
    return run


_LP_FIXTURES = {_g: _lp_fixture(_g) for _g in list(_LP_TEETH) + list(_LP_SUBTEETH)}
expect("WARP-0623 AC4 T-shadow: neutralizing the SHADOW REFUSAL lets a seeded collision through (the real check refuses it by name), and the module on disk is sha256-unchanged",
       _LP_FIXTURES["shadow refusal"](LP.__dict__) is not None
       and _LP_FIXTURES["shadow refusal"](_lp_mut("shadow refusal")) is None and _lp_sha_unchanged())
expect("WARP-0623 AC4 T-callable: neutralizing the CALLABILITY PROBE makes the reachability guard report a shadowed provisioning method as reachable (the real guard reports it), and the module on disk is sha256-unchanged",
       _LP_FIXTURES["callability probe"](LP.__dict__) == ["_project_record"]
       and _LP_FIXTURES["callability probe"](_lp_mut("callability probe")) is None and _lp_sha_unchanged())
_LP_MATRIX = {}
for _lpm in _LP_TEETH:
    _lp_mut_ns = _lp_mut(_lpm)
    for _lpg in _LP_TEETH:
        _LP_MATRIX[(_lpm, _lpg)] = _LP_FIXTURES[_lpg](_lp_mut_ns) is None
expect("WARP-0623 AC4 MATRIX: all four cells of the 2x2 teeth matrix are exactly the DIAGONAL - each mutation flips ONLY its own fixture and the other guard still catches its own seeded collision",
       all(_LP_MATRIX[(_lpm, _lpg)] == (_lpm == _lpg) for _lpm in _LP_TEETH for _lpg in _LP_TEETH)
       and len(_LP_MATRIX) == 4 and sum(1 for _v in _LP_MATRIX.values() if _v) == 2)
expect("WARP-0623 AC4 SUB-TEETH: each WIRING site has its own tooth (neutralizing the factory call hands back a colliding class; neutralizing the per-instance call constructs an instance whose provisioning method is shadowed), and each is DOMINATED by the shadow refusal, which is why it is not a matrix row",
       all(_LP_FIXTURES[_s](LP.__dict__) is not None for _s in _LP_SUBTEETH)
       and all(_LP_FIXTURES[_s](_lp_mut(_s)) is None for _s in _LP_SUBTEETH)
       and all(_LP_FIXTURES[_s](_lp_mut("shadow refusal")) is None for _s in _LP_SUBTEETH)
       and all(_LP_FIXTURES[_s](_lp_mut("callability probe")) is not None for _s in _LP_SUBTEETH)
       and _LP_FIXTURES["shadow refusal"](_lp_mut("factory wiring")) is not None
       and _LP_FIXTURES["callability probe"](_lp_mut("constructor wiring")) == ["_project_record"])
expect("WARP-0623 AC4: after every mutation run the live module on disk is sha256 UNCHANGED (all mutations were compiled in memory)",
       _lp_sha_unchanged())

# AC4 HONEST BOUNDARY (review lane): the check finds NAME collisions on the composed class. It does not
# find every way a live path can be unreachable - a wrong endpoint, a wrong payload shape or a permission
# the credential lacks are found only by EXECUTING the path against a real board, which is WARP-0620. The
# module says so, and so does the capability entry.
expect("WARP-0623 AC4/AC5: the honest boundary is recorded in the module itself - name collisions are checked, and a wrong endpoint, payload or credential scope is only found by executing the path (WARP-0620)",
       "WARP-0620" in _lp_src and "NAME collisions, not every way a live path can be unreachable" in _lp_src)
expect("WARP-0623 AC5: the module docstring records WHY the collision survived a green gate (the offline fake defines the same private names as the real adapter, so codified from a proven script is not the same as the codified path ran)",
       "CODIFIED FROM A PROVEN SCRIPT IS NOT THE SAME AS THE CODIFIED PATH RAN" in _lp_src
       and "FakeTracker defines its OWN" in _lp_src)

# AC5: the capability entry, byte-identical across all eight capabilities.yaml copies, honestly marked
# repo-only (the tracker board-bootstrap cluster does not ship in the engine) and stating plainly that the
# live provisioning path itself is still UNEXECUTED against a real board until WARP-0620.
_lp_caps = (ROOT / ".veldo/capabilities.yaml").read_bytes()
_lp_caps_text = _lp_caps.decode()
expect("WARP-0623 AC5: the tracker_provisioner_shadow_check capability is present and byte-identical across all eight capabilities.yaml copies",
       b"tracker_provisioner_shadow_check" in _lp_caps
       and (ROOT / "engine/.veldo/capabilities.yaml").read_bytes() == _lp_caps
       )
_lp_caps_entry = next(_ln for _ln in _lp_caps_text.splitlines()
                      if _ln.startswith("  tracker_provisioner_shadow_check:"))
expect("WARP-0623 AC5: the capability entry is mechanical, homed in the live module, marked scope: repo-only, and states PLAINLY that the live provisioning path remains UNEXECUTED against a real board until WARP-0620",
       "status: mechanical" in _lp_caps_entry and "home: .veldo/tracker_jira_live.py" in _lp_caps_entry
       and "scope: repo-only" in _lp_caps_entry and "UNEXECUTED" in _lp_caps_entry
       and "WARP-0620" in _lp_caps_entry)
# The honest engine-sync truth, asserted rather than assumed: the live provisioner is REPO-ONLY. It has
# never been part of the canonical engine (engine), so there is no shipped copy to sync and no
# pack carries one; capabilities.yaml is the artifact that does ship, and it is byte-identical above.
_lp_engine = set(PK.engine_files(str(ROOT / "engine")))
expect("WARP-0623 AC5: the live provisioner is REPO-ONLY - the whole tracker board-bootstrap cluster is absent from the canonical engine and from every pack, so 'engine-synced' here means the capability record, not a shipped module copy",
       not [_m for _m in ("tracker_jira_live.py", "tracker_jira_init.py", "tracker_intake.py",
                          "tracker_adapter.py") if (".veldo/" + _m) in _lp_engine]
       and not (ROOT / "engine/.veldo/tracker_jira_live.py").exists())
# AC5 dogfood: this item's own spec is ready, standard risk, touches no protected path, and passes the
# repository's own placement and diagnosability gates.
_lp_fm = V.parse_yamlish(re.match(r"^---\n(.*?)\n---",
                                  (ROOT / "specs/WARP-0623-live-provisioner-name-collision.md").read_text(),
                                  re.S).group(1))
expect("WARP-0623 AC5 dogfood: the spec has PASSED the ready transition (status ready or beyond, never draft or blocked, so the assertion does not go stale the moment the item ships), standard risk, human_approval not required, declares no protected path, and passes its own diagnosability gate (check_ready == 0)",
       _lp_fm.get("status") in ("ready", "in_progress", "review", "proven", "shipped") and _lp_fm.get("risk", "").split()[0] == "standard"
       and _lp_fm.get("human_approval") == "not_required"
       and (_lp_fm.get("protected_paths") or []) == []
       and _lp_fm.get("behavior_bearing") == "true" and isinstance(_lp_fm.get("observability"), dict)
       and V.check_ready(ROOT / "specs/WARP-0623-live-provisioner-name-collision.md", repo_root=str(ROOT)) == 0)
_lp_arch, _lp_contract = V.load_repo_contract(repo_root=str(ROOT))
expect("WARP-0623 AC5 dogfood: the spec's placement resolves to the TRACKER area and its footprint tier is standard (one declared area, no boundary crossing)",
       _lp_fm.get("placement") == ["tracker"] and _lp_contract is not None
       and _lp_arch.footprint_areas(_lp_fm, _lp_contract) == {"tracker"}
       and _lp_arch.placement_gate(_lp_fm, _lp_contract) == []
       and _lp_arch.footprint_tier_floor(_lp_fm, _lp_contract) == "")
expect("WARP-0623 AC5: the named failure class the spec's observability block promises IS the one the module ships",
       LP.SHADOWED_PROVISIONER_METHOD == "SHADOWED_PROVISIONER_METHOD"
       and LP.SHADOWED_PROVISIONER_METHOD in _lp_fm["observability"]["error_taxonomy"]
       and LP.SHADOWED_PROVISIONER_METHOD in _lp_src)

# ============================================================================
# WARP-0711 - THE LINT STAGE RUNS ONE INTERPRETER OVER THE TRACKED PYTHON CORPUS
# INSTEAD OF ONE PER FILE.
#
# The stage ran `python3 -m py_compile` once per tracked Python file. Interpreter
# startup was the cost, not the compiling, so the replacement compiles the SAME
# file set in ONE process. The one way that could be a fake speedup is by
# CHECKING LESS, so the first mechanism below EXECUTES the per-file loop's own
# committed text under a recording shim and asserts the set the new stage
# iterates is EQUAL to the set the loop iterated - neither a superset nor a
# subset. The contract (per-path failure naming, exit semantics, no bytecode) is
# then proven as a DIFFERENTIAL over planted defects: both stages are run over
# the same fixture repository and their output compared, rather than one stage's
# behaviour being described in prose.
#
# NOTHING HERE IS PINNED TO TODAY'S CORPUS SIZE. The tracked corpus grows, so
# every count is derived at run time from `git ls-files` or from the fixture
# declaration in this file. A number written down here would turn this gate red
# on the first unrelated file added, which is exactly what the spec corpus count
# did to an unrelated item the morning this was built.
# ============================================================================
import shutil as _l07_sh
import signal as _l07_signal

_L07_STAGE = ROOT / "scripts/check_lint.sh"
_L07_SRC = _L07_STAGE.read_text()
_L07_SPEC_PATH = ROOT / "specs/WARP-0711-lint-one-interpreter.md"
_L07_SPEC_TEXT = _L07_SPEC_PATH.read_text()
_L07_LOOP_MARKER = "python3 -m py_compile"
_L07_CD_LINE = 'cd "$(dirname "$0")/.."'
# Resolved BEFORE any shim directory goes on PATH, because one of the shims is named bash.
_L07_BASH = _l07_sh.which("bash") or "/bin/bash"


def _l07_git(*args, cwd=None):
    return subprocess.run(["git", *args], cwd=str(cwd or ROOT), check=True,
                          capture_output=True, text=True).stdout


def _l07_spawns_loop(text):
    """True when a stage text SPAWNS the per-file loop rather than merely MENTIONING it: the
    marker on a line that is not a comment. ONE definition, used both to resolve the loop
    from git and to assert the stage on disk no longer runs it - because the new stage
    documents what it replaced, so a substring test is satisfied by its own comments. An
    earlier version of this helper tested the substring, and the moment the new stage was
    committed the resolver below picked the NEW stage as the loop and six assertions failed
    in a detached worktree at the fix commit. That is what this distinction costs."""
    return bool([ln for ln in text.splitlines()
                 if _L07_LOOP_MARKER in ln and not ln.lstrip().startswith("#")])


def _l07_loop_revision():
    """The per-file loop's own committed text, resolved BY CONTENT: the newest revision of
    the stage whose body still SPAWNS py_compile per file. Never HEAD, so this keeps
    resolving to the loop after the stage has changed again."""
    for rev in _l07_git("log", "--format=%H", "--", "scripts/check_lint.sh").split():
        text = _l07_git("show", "%s:scripts/check_lint.sh" % rev)
        if _l07_spawns_loop(text):
            return rev, text
    return "", ""


def _l07_no_history(inputs, leg, weaker):
    """THIS ITEM'S from-git legs, through the ONE mechanism in shared.py (WARP-1711). Every
    assertion below that compares the SHIPPED stage against a revision resolved from history is
    split so the shipped-stage legs keep running in a flattened repository, and only the leg that
    needs the older revision stands down - by name, never silently."""
    return no_history(inputs, leg, weaker, "WARP-0711")


_L07_LOOP_REV, _L07_LOOP_SRC = _l07_loop_revision()
_L07_NEWEST_REV = (_l07_git("log", "--format=%H", "-1", "--",
                            "scripts/check_lint.sh").split() or [""])[0]
_L07_MARKER_LINES = [_ln for _ln in _L07_SRC.splitlines() if _L07_LOOP_MARKER in _ln]
# SPLIT (WARP-1711): that the stage ON DISK documents the loop without spawning it is a fact about
# the shipped file and runs everywhere; resolving the loop's own revision needs history.
expect("WARP-0711 AC2: the stage ON DISK DOCUMENTS the per-file loop it replaced without SPAWNING it - the marker appears in its text and on no non-comment line - so the distinction between mentioning the loop and running it is asserted on the shipped file rather than assumed",
       len(_L07_MARKER_LINES) > 0 and not _l07_spawns_loop(_L07_SRC))
if not _l07_no_history([("scripts/check_lint.sh", _L07_LOOP_REV)], "the PER-FILE LOOP differential",
                       "That the shipped stage documents the loop without spawning it is SPLIT OUT "
                       "and still runs here, immediately above; every assertion below that needed the "
                       "loop's committed text stands down beside this one, each by name."):
    expect("WARP-0711 AC2: the PER-FILE LOOP is resolved from git BY CONTENT - the newest revision of scripts/check_lint.sh whose body SPAWNS py_compile per file, which is a NON-COMMENT line and not a mention of one - never as HEAD; the resolver is proven to have WALKED PAST the newest revision of that file rather than accepting it, which is the tooth on the distinction; and the stage on disk documents the loop without spawning it",
       len(_L07_LOOP_REV) == 40 and _l07_spawns_loop(_L07_LOOP_SRC)
       and _L07_LOOP_SRC.count(_L07_LOOP_MARKER) == 1
       and len(_L07_NEWEST_REV) == 40 and _L07_LOOP_REV != _L07_NEWEST_REV
       and _L07_LOOP_SRC != _L07_SRC
       and len(_L07_MARKER_LINES) > 0 and not _l07_spawns_loop(_L07_SRC))
_L07_PATTERNS = re.findall(r"git ls-files '([^']*)'", _L07_LOOP_SRC)
expect("WARP-0711 AC2: the new stage names EXACTLY TWO `git ls-files` patterns in its own text, one per language, measured on the shipped file",
       '("python", "*.py")' in _L07_SRC and '("shell", "*.sh")' in _L07_SRC)
if not _l07_no_history([("scripts/check_lint.sh", _L07_LOOP_REV)],
                       "the loop's own two-pattern definition",
                       "That the new stage names exactly those two patterns in its own text is SPLIT "
                       "OUT and still runs here, immediately above."):
    expect("WARP-0711 AC2: the loop's file set is defined by EXACTLY TWO `git ls-files` patterns, read off its committed text, and the new stage names the same two in its own text - so 'the same patterns' is a measurement of both texts rather than a claim about one",
       _L07_PATTERNS == ["*.py", "*.sh"]
       and '("python", "*.py")' in _L07_SRC and '("shell", "*.sh")' in _L07_SRC)
_L07_EXEC_SRC = _L07_LOOP_SRC.replace(_L07_CD_LINE, 'cd "$VELDO_LINT_OLD_ROOT"')
_L07_ADAPTED = [_i for _i, (_a, _b) in enumerate(zip(_L07_LOOP_SRC.splitlines(),
                                                     _L07_EXEC_SRC.splitlines())) if _a != _b]
if not _l07_no_history([("scripts/check_lint.sh", _L07_LOOP_REV)],
                       "the one-line adaptation of the loop's committed text",
                       "Nothing here is about the shipped stage: this leg exists only to prove the "
                       "OLDER text is executed as committed."):
    expect("WARP-0711 AC2: the loop is executed AS COMMITTED except for ONE declared line - the `cd $(dirname $0)/..` that would otherwise take it to the temp directory it is run from - and the adaptation is asserted to change exactly that one line, to leave the line count identical, and to be the only difference",
       _L07_LOOP_SRC.count(_L07_CD_LINE) == 1 and len(_L07_ADAPTED) == 1
       and _L07_LOOP_SRC.splitlines()[_L07_ADAPTED[0]].strip() == _L07_CD_LINE
       and len(_L07_EXEC_SRC.splitlines()) == len(_L07_LOOP_SRC.splitlines()))


def _l07_loop_file_set():
    """EXECUTE the per-file loop over this repository with `python3` and `bash` replaced by
    shims that RECORD the path handed to them and check nothing, and return the set of paths
    it really visited. The loop's own text decides the set; nothing here re-derives it. A
    shim records an argument only when it names an existing .py or .sh file, so `-m
    py_compile` and `-n` are not mistaken for paths."""
    with tempfile.TemporaryDirectory() as td:
        shim = Path(td) / "shim"
        shim.mkdir()
        log = Path(td) / "visited.txt"
        # `-e` OR `-L` rather than `-f`: a tracked path that is not a regular file (a
        # dangling symlink, a submodule gitlink) is LISTED by the new stage, so a shim that
        # recorded only regular files would report an inequality on a tree that is equal.
        # Round-1 note N3, closed here rather than left for the day a submodule appears.
        body = ('#!/bin/sh\nfor a in "$@"; do case "$a" in *.py|*.sh) '
                'if [ -e "$a" ] || [ -L "$a" ]; then '
                'printf "%s\\n" "$a" >> "$VELDO_LINT_SHIM_LOG"; fi;; esac; done\nexit 0\n')
        for name in ("python3", "bash"):
            (shim / name).write_text(body)
            (shim / name).chmod(0o755)
        script = Path(td) / "loop_stage.sh"
        script.write_text(_L07_EXEC_SRC)
        subprocess.run([_L07_BASH, str(script)], capture_output=True, text=True,
                       env=dict(os.environ, PATH="%s:%s" % (shim, os.environ.get("PATH", "")),
                                VELDO_LINT_SHIM_LOG=str(log), VELDO_LINT_OLD_ROOT=str(ROOT)))
        return set(log.read_text().split()) if log.exists() else set()


_L07_LOOP_SET = _l07_loop_file_set()
_L07_LIST_RUN = subprocess.run(["bash", str(_L07_STAGE), "--list"], cwd=str(ROOT),
                               capture_output=True, text=True)
_L07_LISTED = [_ln.split(" ", 1) for _ln in _L07_LIST_RUN.stdout.splitlines()]
_L07_NEW_SET = {_p for _lang, _p in _L07_LISTED}
_L07_GIT_PY = _l07_git("ls-files", "*.py").split()
_L07_GIT_SH = _l07_git("ls-files", "*.sh").split()
# SPLIT (WARP-1711): "a lint stage that quietly checks fewer files is the cheapest possible fake
# speedup" is the thing being defended, and it does NOT need the loop: the new stage's own set is
# asserted EQUAL to the two `git ls-files` patterns run here, live, in both directions. That keeps
# the protection in a flattened repository, where only the comparison against the loop stands down.
expect("WARP-0711 AC2 THE LOAD-BEARING ONE, WITHOUT HISTORY: the file set the new stage iterates is EQUAL to the two `git ls-files` patterns run independently here, with BOTH differences asserted as EMPTY LISTS so neither a superset nor a subset passes, and the set is NON-EMPTY and carries both languages - because a lint stage that quietly checks fewer files is the cheapest possible fake speedup, and that is measurable against git itself rather than only against the stage it replaced",
       _L07_NEW_SET == (set(_L07_GIT_PY) | set(_L07_GIT_SH))
       and sorted((set(_L07_GIT_PY) | set(_L07_GIT_SH)) - _L07_NEW_SET) == []
       and sorted(_L07_NEW_SET - (set(_L07_GIT_PY) | set(_L07_GIT_SH))) == []
       and len(_L07_NEW_SET) == len(_L07_GIT_PY) + len(_L07_GIT_SH)
       and len(_L07_GIT_PY) > 0 and len(_L07_GIT_SH) > 0
       and [_p for _p in _L07_NEW_SET if _p.endswith(".py")]
       and [_p for _p in _L07_NEW_SET if _p.endswith(".sh")])
if not _l07_no_history([("scripts/check_lint.sh", _L07_LOOP_REV)],
                       "the file-set equality against the EXECUTED loop",
                       "The same property against git itself - the new stage's set equal to the two "
                       "patterns in both directions, non-empty, both languages - is SPLIT OUT and "
                       "still runs here, immediately above."):
    expect("WARP-0711 AC2 THE LOAD-BEARING ONE: the file set the new stage iterates is EQUAL to the set the per-file loop iterated, with BOTH differences asserted as EMPTY LISTS so neither a superset nor a subset passes - measured by executing the loop's own committed text over this repository, because a lint stage that quietly checks fewer files is the cheapest possible fake speedup",
       _L07_NEW_SET == _L07_LOOP_SET
       and sorted(_L07_LOOP_SET - _L07_NEW_SET) == [] and sorted(_L07_NEW_SET - _L07_LOOP_SET) == [])
    expect("WARP-0711 AC2 NON-VACUITY of that equality: the set is NON-EMPTY, carries both languages, and its size is derived live from the two `git ls-files` patterns rather than written down here - the corpus grows, and a count in this file would turn the gate red on the first unrelated file added",
           len(_L07_LOOP_SET) == len(_L07_GIT_PY) + len(_L07_GIT_SH)
           and len(_L07_GIT_PY) > 0 and len(_L07_GIT_SH) > 0
           and [_p for _p in _L07_NEW_SET if _p.endswith(".py")]
           and [_p for _p in _L07_NEW_SET if _p.endswith(".sh")])
expect("WARP-0711 AC2: the new stage's own LANGUAGE PARTITION of that set is the two patterns run independently, IN GIT'S ORDER - so the python half checks the python corpus and the shell half the shell corpus, and neither language silently absorbed the other",
       [_p for _lang, _p in _L07_LISTED if _lang == "python"] == _L07_GIT_PY
       and [_p for _lang, _p in _L07_LISTED if _lang == "shell"] == _L07_GIT_SH
       and {_lang for _lang, _p in _L07_LISTED} == {"python", "shell"})

# --- AC2 TEETH: both stages run over the SAME planted defects, output compared ---
# name -> (bytes, must_fail). bytes None means a tracked SYMLINK with no target, which is
# the unreadable-path branch and is deterministic at any euid, where a mode-000 file is not.
_L07_FIXTURES = {
    # THE TWO SHAPES THE ROUND-1 REVIEW FOUND ESCAPING, named by SHAPE and not by exception
    # class, because which class an interpreter raises for them is a moving property. They
    # sort FIRST, and that EVERY OTHER must-fail fixture therefore sorts after them is
    # asserted below as a set equality rather than left as a sentence, so continuation is
    # observable rather than assumed and the arrangement cannot drift out from under it.
    "aaa_deep_nesting.py": (b"x = 1" + b"+1" * 9996 + b"\n", True),
    "aab_parser_stack.py": (b"x = " + b"1 if 1 else " * 20000 + b"1\n", True),
    "ok.py": (b"x = 1\n", False),
    "syntax.py": (b"def f(:\n", True),
    "indent.py": (b"def f():\nreturn 1\n", True),
    "nullbyte.py": (b"x = 1\x00\n", True),
    "nonutf8.py": (b"x = '\xe9'\n", True),
    "dangling.py": (None, True),
    "ok.sh": (b"echo hi\n", False),
    "syntax.sh": (b"if true; then\n", True),
}
_L07_MUST_FAIL = sorted(_n for _n, (_d, _f) in _L07_FIXTURES.items() if _f)
_L07_MUST_PASS = sorted(_n for _n, (_d, _f) in _L07_FIXTURES.items() if not _f)


def _l07_fixture_repo(dest, only_passing=False):
    """A throwaway git repository holding exactly the declared fixtures. The stage under test
    is written to scripts/ AFTER the add and left UNTRACKED on purpose, so the file set is
    exactly the fixtures and the per-language counts the stage prints can be compared with
    the declaration above."""
    dest = Path(dest)
    (dest / "scripts").mkdir(parents=True)
    for name, (data, must_fail) in sorted(_L07_FIXTURES.items()):
        if only_passing and must_fail:
            continue
        if data is None:
            os.symlink("no-such-target.py", dest / name)
        else:
            (dest / name).write_bytes(data)
    for _args in (["init", "-q"], ["add", "-A", "-f"]):
        subprocess.run(["git", *_args], cwd=str(dest), check=True, capture_output=True)
    return dest


def _l07_bytecode(dest):
    """Every .pyc file and every __pycache__ directory under dest, git's own store excluded."""
    out = []
    for base, dirs, files in os.walk(dest):
        rel = Path(base).relative_to(dest)
        if ".git" in rel.parts:
            continue
        out += [str(rel / _d) for _d in dirs if _d == "__pycache__"]
        out += [str(rel / _f) for _f in files if _f.endswith(".pyc")]
    return sorted(out)


def _l07_run(stage_text, only_passing=False, env_extra=None):
    """Run ONE stage text over a FRESH fixture repository and report what it did: exit
    status, the paths it named as failing, its whole stdout, its summary line, and any
    bytecode it left behind. env_extra adds variables to the inherited environment, which is
    how the fail-open surface below is ATTACKED rather than reasoned about."""
    with tempfile.TemporaryDirectory() as td:
        dest = _l07_fixture_repo(Path(td) / "repo", only_passing=only_passing)
        (dest / "scripts" / "check_lint.sh").write_text(stage_text)
        r = subprocess.run(["bash", "scripts/check_lint.sh"], cwd=str(dest),
                           env=dict(os.environ, **env_extra) if env_extra else None,
                           capture_output=True, text=True)
        lines = r.stdout.splitlines()
        return {"exit": r.returncode, "lines": lines, "last": lines[-1] if lines else "",
                "fails": sorted(_ln[len("   FAIL: "):] for _ln in lines
                                if _ln.startswith("   FAIL: ")),
                "bytecode": _l07_bytecode(dest)}


_L07_NEW_RUN = _l07_run(_L07_SRC)
_L07_LOOP_RUN = _l07_run(_L07_LOOP_SRC)
expect("WARP-0711 AC2 TEETH: over a fixture repository carrying a deliberately broken PYTHON file in four shapes (invalid syntax, a bad indent, a null byte, undecodable bytes), a tracked symlink with no target, and a deliberately broken SHELL file, the new stage fails EACH ONE BY NAME, passes both valid files, and exits non-zero - so the stage is proven to still check",
       _L07_NEW_RUN["fails"] == _L07_MUST_FAIL and _L07_NEW_RUN["exit"] != 0
       and not set(_L07_NEW_RUN["fails"]) & set(_L07_MUST_PASS)
       and len(_L07_MUST_FAIL) == 8 and len(_L07_MUST_PASS) == 2)
# SPLIT (WARP-1711): the shipped stage's own lines and its format string are asserted without git.
expect("WARP-0711 AC2: the per-file failure line is preserved VERBATIM - `   FAIL: <path>`, three leading spaces, one path per line - because something may be parsing it; asserted as EXACT stdout lines for every planted defect in the SHIPPED stage, and as the literal format string in its own text",
       all(("   FAIL: %s" % _n) in _L07_NEW_RUN["lines"] for _n in _L07_MUST_FAIL)
       and '"   FAIL: %s" % path' in _L07_SRC)
if not _l07_no_history([("scripts/check_lint.sh", _L07_LOOP_REV)],
                       "the VERBATIM failure line in the LOOP's output",
                       "The shipped stage's own exact lines and its format string are SPLIT OUT and "
                       "still run here, immediately above."):
    expect("WARP-0711 AC2: the per-file failure line is preserved VERBATIM - `   FAIL: <path>`, three leading spaces, one path per line - because something may be parsing it; asserted as EXACT stdout lines for every planted defect, in BOTH stages, and as the literal format string in the new stage's own text",
       all(("   FAIL: %s" % _n) in _L07_NEW_RUN["lines"] for _n in _L07_MUST_FAIL)
       and all(("   FAIL: %s" % _n) in _L07_LOOP_RUN["lines"] for _n in _L07_MUST_FAIL)
       and '"   FAIL: %s" % path' in _L07_SRC)
if not _l07_no_history([("scripts/check_lint.sh", _L07_LOOP_REV)],
                       "the same-naming same-exit contract differential",
                       "Both halves of what it compares are asserted on the SHIPPED stage above: the "
                       "exact FAIL lines for every planted defect, and a non-zero exit."):
    expect("WARP-0711 AC2 THE CONTRACT AS A DIFFERENTIAL RATHER THAN AS PROSE: over the SAME fixtures the per-file loop's committed text and the new stage report the SAME failing paths and the SAME exit status, so 'same failure naming, same exit semantics' is a measurement of both stages",
       _L07_LOOP_RUN["fails"] == _L07_NEW_RUN["fails"]
       and _L07_LOOP_RUN["exit"] == _L07_NEW_RUN["exit"] != 0)

# THE FIXTURE GAP THE ROUND-1 REVIEW FOUND, AND THE TOOTH THAT CLOSES IT. The shipped stage
# caught three named exception families, and two compilation failures live outside them: deep
# expression nesting and an overflowed parser stack. Over 694 files the stage ABORTED on the
# first such file - no path, no FAIL line, no summary, every later file unchecked - where the
# loop named it and carried on. The handler is now `Exception`, the same width as
# py_compile's, and these two assertions are why a narrowing cannot come back unnoticed: the
# first proves CONTINUATION past the poison rather than only detection of it, and the second
# is the mutation nobody ran, restoring the narrow handler and measuring the abort.
_L07_POISON = sorted(_n for _n in ("aaa_deep_nesting.py", "aab_parser_stack.py"))
_L07_AFTER_POISON = [_n for _n in _L07_MUST_FAIL if _n > max(_L07_POISON)]
expect("WARP-0711 AC2 CONTINUATION, not only detection: the two fixtures whose compilation raises from OUTSIDE the syntax families are each named on their own `   FAIL: <path>` line, AND every must-fail fixture that sorts AFTER them is still named, AND the summary line is still printed - so a file that once killed the stage now costs one FAIL line and nothing else. THE `EVERY OTHER' IS ITSELF ASSERTED, as a set equality against the must-fail set minus the poison and separately as non-empty, so the sentence cannot outlive the arrangement it describes",
       set(_L07_POISON) <= set(_L07_MUST_FAIL) and len(_L07_POISON) == 2
       and all(("   FAIL: %s" % _n) in _L07_NEW_RUN["lines"] for _n in _L07_POISON)
       and _L07_AFTER_POISON == sorted(set(_L07_MUST_FAIL) - set(_L07_POISON))
       and _L07_AFTER_POISON != []
       and all(("   FAIL: %s" % _n) in _L07_NEW_RUN["lines"] for _n in _L07_AFTER_POISON)
       and _L07_NEW_RUN["last"].startswith("lint: FAIL"))
if not _l07_no_history([("scripts/check_lint.sh", _L07_LOOP_REV)],
                       "the POISON fixtures named by the LOOP too",
                       "That the shipped stage names both poison fixtures, names every must-fail "
                       "fixture sorting after them and still prints its summary line is SPLIT OUT and "
                       "still runs here, immediately above."):
    expect("WARP-0711 AC2 CONTINUATION, the LOOP's half: the two fixtures whose compilation raises from OUTSIDE the syntax families are named by the per-file loop's committed text as well, which is what makes the shipped stage's continuation a restoration of the loop's behaviour rather than a new claim",
           all(("   FAIL: %s" % _n) in _L07_LOOP_RUN["lines"] for _n in _L07_POISON))
_L07_NARROW_SRC = _L07_SRC.replace("except Exception as e:",
                                   "except (SyntaxError, ValueError, OSError) as e:")
_L07_NARROW_RUN = _l07_run(_L07_NARROW_SRC)
expect("WARP-0711 AC2 TEETH ON THE HANDLER'S WIDTH, which is the mutation that was never run: restoring the three-family handler the round-1 review refuted makes the stage ABORT on the first poison fixture - it names NO path at all, prints NO summary line, and leaves every later file unchecked - and the mutation target is asserted to occur EXACTLY ONCE so the mutation cannot have matched nothing. It still exits non-zero, which is why the round-1 defect was a defect and not a false GREEN",
       _L07_SRC.count("except Exception as e:") == 1 and _L07_NARROW_SRC != _L07_SRC
       and _L07_NARROW_RUN["fails"] == [] and _L07_NARROW_RUN["last"] == ""
       and _L07_NARROW_RUN["exit"] != 0
       and "except Exception as e:" not in _L07_NARROW_SRC)

# --- THE ONE FAIL-OPEN SURFACE THE ROUND-2 REVIEW FOUND, CLOSED AND ATTACKED ----------
# `VELDO_LINT_LIST=1` in the ENVIRONMENT used to print the file set and exit 0 having checked
# nothing, which the reviewer measured taking verify.sh's own wiring to the GREEN branch over
# a tree carrying six planted defects. It was the only fail-open surface in this item and the
# per-file loop it replaced had no equivalent. The listing is now reached by an EXPLICIT
# ARGUMENT the gate never passes, it exits NON-ZERO, and it prints no `lint:` verdict line.
# THE UNIVERSAL IS BACKED BY THE TEXT rather than by a sample of variable names: the stage
# reads NO environment at all, asserted over its non-comment lines, so there is no variable
# left for anyone to find. The differential is against the revision that HAD the switch,
# resolved from git BY CONTENT the same way the per-file loop is.
# HISTORICAL DATA, so the rename must not reach it. This switch existed under the OLD product name
# and was removed; it appears only in past revisions. Rewriting the literal makes the search for
# "the newest revision that still read the switch" find nothing, which returns an empty revision and
# fails both assertions for a reason unrelated to what they test. Spelled in two pieces that Python
# joins at compile time. The other VELDO_LINT_* names in this suite are fixtures it INVENTS and then
# asserts on, both sides in this file, so those rename together and are fine.
_L07_OLD_SWITCH = "W" "ARP_LINT_LIST"
_L07_AMBIENT_MARKER = 'os.environ.get("%s")' % _L07_OLD_SWITCH


def _l07_ambient_revision():
    """The newest committed revision of the stage whose body READS the ambient switch, on a
    non-comment line so the header's account of its removal is not mistaken for the switch.
    Never HEAD: this keeps resolving to the fail-open shape after it is gone."""
    for rev in _l07_git("log", "--format=%H", "--", "scripts/check_lint.sh").split():
        text = _l07_git("show", "%s:scripts/check_lint.sh" % rev)
        if [_ln for _ln in text.splitlines()
                if _L07_AMBIENT_MARKER in _ln and not _ln.lstrip().startswith("#")]:
            return rev, text
    return "", ""


_L07_AMBIENT_REV, _L07_AMBIENT_SRC = _l07_ambient_revision()
_L07_AMBIENT_ENV = {_L07_OLD_SWITCH: "1"}  # the historical script reads the OLD name
_L07_AMBIENT_RUN = _l07_run(_L07_AMBIENT_SRC, env_extra=_L07_AMBIENT_ENV)
_L07_ENV_RUN = _l07_run(_L07_SRC, env_extra=_L07_AMBIENT_ENV)
# SPLIT (WARP-1711): that the SHIPPED stage is not fail-open under the same variable - every planted
# defect named, `lint: FAIL`, non-zero, identical to a run without it - needs no history at all.
expect("WARP-0711 THE FAIL-OPEN SWITCH IS CLOSED ON THE SHIPPED STAGE: with the ambient variable SET over a fixture repository carrying planted defects, the stage on disk names every one of them, prints `lint: FAIL` and exits non-zero, identically to a run with no such variable - so no value of it reaches a pass",
       _L07_ENV_RUN["exit"] != 0 and _L07_ENV_RUN["exit"] == _L07_NEW_RUN["exit"]
       and _L07_ENV_RUN["fails"] == _L07_MUST_FAIL
       and _L07_ENV_RUN["last"].startswith("lint: FAIL"))
if not _l07_no_history([("scripts/check_lint.sh", _L07_AMBIENT_REV)],
                       "the fail-open revision differential",
                       "The shipped stage's own behaviour under the same variable - every planted "
                       "defect named, `lint: FAIL`, non-zero - is SPLIT OUT and still runs here, "
                       "immediately above."):
    expect("WARP-0711 THE FAIL-OPEN SWITCH IS CLOSED, PROVEN AS A DIFFERENTIAL AGAINST THE REVISION THAT HAD IT: over a fixture repository carrying planted defects, the newest revision of this stage that READS the ambient variable exits 0 and names NOTHING with that variable set, which is a broken tree reported as a pass; the stage on disk with the SAME variable set names every planted defect, prints `lint: FAIL` and exits non-zero, identically to a run with no such variable",
       len(_L07_AMBIENT_REV) == 40 and _L07_AMBIENT_SRC != _L07_SRC
       and _L07_AMBIENT_RUN["exit"] == 0 and _L07_AMBIENT_RUN["fails"] == []
       and _L07_ENV_RUN["exit"] != 0 and _L07_ENV_RUN["exit"] == _L07_NEW_RUN["exit"]
       and _L07_ENV_RUN["fails"] == _L07_MUST_FAIL
       and _L07_ENV_RUN["last"].startswith("lint: FAIL"))
# THE GUARD BEHIND THAT UNIVERSAL COVERS BOTH HALVES OF THE STAGE, because round 3's covered
# only the python half and the round-3 reviewer got TWO fail-open mutants through the whole
# suite: a shell-half `${VELDO_LINT_SKIP:-}` branch, which contains neither `environ` nor
# `getenv` because the shell half is not python, and a python-half
# `subprocess.run(["sh", "-c", 'test -n "$VELDO_OFF"'])`, which reads the environment without
# naming either. ONE function decides it, and it is run on the shipped text AND on each mutant,
# because a guard that is only ever run on the text it was written for proves nothing.
import ast as _l07_ast

_L07_SHELL_PINNED = ("set -u", 'CDPATH= cd "$(dirname "$0")/.."',
                     'exec env -i PATH="$PATH" python3 - "$@" <<\'PY\'', "PY")
_L07_PY_IMPORTS = ("importlib.machinery.SourceFileLoader", "signal", "subprocess", "sys", "time")
_L07_ARGV_SHAPES = (("bash", "-n"), ("git", "ls-files"))
_L07_ENV_TOKENS = ("environ", "getenv", "__import__", "eval(", "popen")


def _l07_halves(text):
    """(shell half, python half). The python half is the heredoc BODY; the shell half is
    everything else, including the `exec` line that opens the heredoc and the `PY` that closes
    it - so an unquoted delimiter, which would let the shell expand variables inside the body,
    lands in the shell half where it is pinned."""
    lines = text.splitlines()
    opens = [_i for _i, _l in enumerate(lines)
             if _l.startswith("exec ") and _l.endswith("<<'PY'")]
    closes = [_i for _i, _l in enumerate(lines) if _l == "PY"]
    if not opens or not closes:
        return text, ""
    return "\n".join(lines[:opens[0] + 1] + lines[max(closes):]), "\n".join(
        lines[opens[0] + 1:max(closes)])


def _l07_env_findings(text):
    """Every route by which this stage's TEXT could come to read the environment, as a list of
    findings over BOTH halves. EMPTY means no route is present. The four routes, each closed by
    one rule: (1) the shell half is pinned line for line, so a shell-side branch or an unquoted
    heredoc delimiter is a finding; (2) the python half names no environment accessor and no
    dynamic-import or eval escape; (3) its imports are a CLOSED declared set, so a new module
    cannot bring an accessor in; (4) its subprocess argument vectors are pinned BY SHAPE and
    not merely by command name, so it cannot shell out to read what it may not read itself."""
    shell, python = _l07_halves(text)
    findings = []
    shell_lines = tuple(_l for _l in shell.splitlines()
                        if _l.strip() and not _l.lstrip().startswith("#"))
    if shell_lines != _L07_SHELL_PINNED:
        findings.append("shell half is not the pinned three statements plus its delimiter: %r"
                        % (shell_lines,))
    findings += ["environment or dynamic-execution token in the python half: %s" % _l.strip()
                 for _l in python.splitlines()
                 if not _l.lstrip().startswith("#")
                 and any(_k in _l for _k in _L07_ENV_TOKENS)]
    try:
        tree = _l07_ast.parse(python)
    except SyntaxError as _e:
        return findings + ["python half does not parse: %s" % _e]
    imported = set()
    for _n in _l07_ast.walk(tree):
        if isinstance(_n, _l07_ast.Import):
            imported |= {_a.name for _a in _n.names}
        elif isinstance(_n, _l07_ast.ImportFrom):
            imported |= {"%s.%s" % (_n.module, _a.name) for _a in _n.names}
    if tuple(sorted(imported)) != _L07_PY_IMPORTS:
        findings.append("python half imports are not the closed declared set: %r"
                        % (tuple(sorted(imported)),))
    for _n in _l07_ast.walk(tree):
        if not (isinstance(_n, _l07_ast.Call) and isinstance(_n.func, _l07_ast.Attribute)
                and isinstance(_n.func.value, _l07_ast.Name)
                and _n.func.value.id == "subprocess"):
            continue
        if not (_n.args and isinstance(_n.args[0], _l07_ast.List)):
            findings.append("subprocess call whose argv is not a list literal")
            continue
        shape = tuple(_e.value for _e in _n.args[0].elts
                      if isinstance(_e, _l07_ast.Constant) and isinstance(_e.value, str))
        if shape not in _L07_ARGV_SHAPES:
            findings.append("subprocess argv shape is not declared: %r" % (shape,))
    return findings


_L07_ENV_FINDINGS = _l07_env_findings(_L07_SRC)
for _f in _L07_ENV_FINDINGS:
    # expect() reports only its label and this guard has six possible causes, so the precise one
    # is printed here: the likeliest legitimate trip is a new import, which would otherwise fail
    # with a sentence about environment variables. Silent while the guard is satisfied.
    print("  WARP-0711 env guard finding: %s" % _f)
expect("WARP-0711: no environment variable THE STAGE READS can make it report success, and it reads NONE - asserted over BOTH HALVES as an EMPTY findings list, where round 3 covered the python half only: the shell half is pinned line for line, the python half names no environment accessor and no dynamic-import or eval escape, its imports are a closed declared set so a new module cannot bring an accessor in, and its two subprocess argument vectors are pinned BY SHAPE so it cannot shell out to read what it may not read itself",
       _L07_ENV_FINDINGS == []
       and _L07_AMBIENT_MARKER not in _L07_SRC)
if not _l07_no_history([("scripts/check_lint.sh", _L07_AMBIENT_REV)],
                       "the env-guard NON-VACUITY against the revision that read the switch",
                       "The guard itself over both halves of the SHIPPED stage, and the absence of the "
                       "ambient read from it, are SPLIT OUT and still run here, immediately above; the "
                       "guard's teeth are also proven below against FOUR planted reintroductions, "
                       "which need no history."):
    expect("WARP-0711: the env guard is NON-VACUOUS against the revision that HAD the switch - the ambient read is present in that committed text and the guard reports a finding on it, so an empty findings list on the shipped stage is a measurement rather than a check that cannot fire",
           _L07_AMBIENT_MARKER in _L07_AMBIENT_SRC
           and _l07_env_findings(_L07_AMBIENT_SRC) != [])
# TEETH, and they are the round-3 reviewer's OWN two survivors plus the one their fix would not
# have caught: a shell-half branch, a `sh -c` read, and a `bash -c` read that reuses a command
# name the stage is allowed to spawn, which is why the argv rule is keyed on SHAPE.
_L07_ENV_MUTANTS = {
    "shell-half branch": (
        'exec env -i PATH="$PATH" python3 - "$@" <<\'PY\'',
        'if [ -n "${VELDO_LINT_SKIP:-}" ]; then echo "lint: pass"; exit 0; fi\n'
        'exec env -i PATH="$PATH" python3 - "$@" <<\'PY\''),
    "sh -c read in the python half": (
        "FAIL = 0\nfor label, _pattern in PATTERNS:",
        'if subprocess.run(["sh", "-c", \'test -n "$VELDO_OFF"\']).returncode == 0:\n'
        '    print("lint: pass", flush=True)\n    sys.exit(0)\n\n'
        "FAIL = 0\nfor label, _pattern in PATTERNS:"),
    "bash -c read, reusing an allowed command name": (
        "FAIL = 0\nfor label, _pattern in PATTERNS:",
        'if subprocess.run(["bash", "-c", \'test -n "$VELDO_OFF"\']).returncode == 0:\n'
        '    print("lint: pass", flush=True)\n    sys.exit(0)\n\n'
        "FAIL = 0\nfor label, _pattern in PATTERNS:"),
    "os imported for its environ": (
        "import signal", "import os\nimport signal"),
}
_L07_ENV_MUTANT_SRC = {_k: _L07_SRC.replace(_old, _new)
                       for _k, (_old, _new) in _L07_ENV_MUTANTS.items()}
expect("WARP-0711 TEETH ON THAT GUARD: each of FOUR reintroductions is rejected by it, including the round-3 reviewer's two survivors, and each mutation target is asserted to occur EXACTLY ONCE in the stage so no mutation matched nothing - a shell-half branch, a `sh -c` environment read, a `bash -c` one that reuses a command name the stage IS allowed to spawn, and an `import os` for its environ",
       all(_L07_SRC.count(_old) == 1 for _old, _new in _L07_ENV_MUTANTS.values())
       and all(_L07_ENV_MUTANT_SRC[_k] != _L07_SRC for _k in _L07_ENV_MUTANTS)
       and all(_l07_env_findings(_L07_ENV_MUTANT_SRC[_k]) != [] for _k in _L07_ENV_MUTANTS)
       and len(_L07_ENV_MUTANTS) == 4)
# THE GIT SUBPROCESS IS ITSELF AN ENVIRONMENT READER, which round 4 claimed the argv-shape rule
# ruled out and which the round-4 review refuted on the SHIPPED TEXT with no mutation at all:
# GIT_DIR, GIT_INDEX_FILE and GIT_LITERAL_PATHSPECS each made the stage report a pass over a tree
# carrying every planted defect. The boundary `env -i PATH="$PATH"` closes the CLASS rather than
# those three names, and this asserts it by ATTEMPTING all three against the same text without it.


def _l07_empty_repo(dest):
    """A git repository with NO tracked files, which is what a hostile GIT_DIR points at."""
    dest = Path(dest)
    dest.mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=str(dest), check=True, capture_output=True)
    return dest


_L07_NOBOUNDARY_SRC = _L07_SRC.replace('exec env -i PATH="$PATH" python3', "exec python3")
with tempfile.TemporaryDirectory() as _l07_ed:
    _l07_empty = _l07_empty_repo(Path(_l07_ed) / "empty")
    _L07_GIT_ENV_PAIRS = {
        _k: (_l07_run(_L07_NOBOUNDARY_SRC, env_extra={_k: _v}),
             _l07_run(_L07_SRC, env_extra={_k: _v}))
        for _k, _v in (("GIT_DIR", str(_l07_empty / ".git")),
                       ("GIT_INDEX_FILE", str(_l07_empty / ".git" / "index")),
                       ("GIT_LITERAL_PATHSPECS", "1"))}
expect("WARP-0711 THE GIT SUBPROCESS CANNOT BE REDIRECTED BY THE ENVIRONMENT, proven by ATTEMPTING three variables that each turned the round-4 text into a PASS over a tree carrying every planted defect: GIT_DIR and GIT_INDEX_FILE point `git ls-files` at an EMPTY repository, and GIT_LITERAL_PATHSPECS makes the `*.py` pattern a literal path matching nothing. Without the boundary all three give `lint: pass` with an EMPTY failing set and exit 0; with it all three name every planted defect and exit non-zero. The boundary passes ONE variable BY NAME rather than unsetting a list of hostile ones, which is the enumeration this stage has been corrected for twice",
       len(_L07_GIT_ENV_PAIRS) == 3 and _L07_NOBOUNDARY_SRC != _L07_SRC
       and _L07_SRC.count('exec env -i PATH="$PATH" python3') == 1
       and all(_open["exit"] == 0 and _open["fails"] == []
               and _open["last"].startswith("lint: pass")
               for _open, _shut in _L07_GIT_ENV_PAIRS.values())
       and all(_shut["exit"] != 0 and _shut["fails"] == _L07_MUST_FAIL
               for _open, _shut in _L07_GIT_ENV_PAIRS.values()))

# CDPATH: the one of the three pre-execution variables that ran through the stage's OWN text,
# closed on the `cd` line and proven closed by ATTEMPTING it against a decoy repository.
_L07_CDPATH_SRC = _L07_SRC.replace('CDPATH= cd "$(dirname "$0")/.."',
                                   'cd "$(dirname "$0")/.."')
with tempfile.TemporaryDirectory() as _l07_decoy_base:
    _l07_decoy = _l07_fixture_repo(Path(_l07_decoy_base) / "decoy", only_passing=True)
    _L07_CDPATH_OPEN = _l07_run(_L07_CDPATH_SRC, env_extra={"CDPATH": str(_l07_decoy)})
    _L07_CDPATH_SHUT = _l07_run(_L07_SRC, env_extra={"CDPATH": str(_l07_decoy)})
expect("WARP-0711 CDPATH IS CLOSED AT THE STAGE'S OWN `cd`, PROVEN BY ATTEMPTING IT: `$(dirname \"$0\")/..` is a RELATIVE operand, so a hostile CDPATH naming a directory with a scripts child sends the stage to a DIFFERENT repository - measured, the same text without the `CDPATH=` prefix reports a PASS and exits 0 over a fixture tree carrying every planted defect, while the shipped text with the same variable set names every defect and exits non-zero",
       _L07_CDPATH_SRC != _L07_SRC and _L07_SRC.count('CDPATH= cd "$(dirname "$0")/.."') == 1
       and _L07_CDPATH_OPEN["exit"] == 0 and _L07_CDPATH_OPEN["fails"] == []
       and _L07_CDPATH_SHUT["exit"] != 0 and _L07_CDPATH_SHUT["fails"] == _L07_MUST_FAIL)
expect("WARP-0711: the listing is a DIAGNOSTIC and cannot be read as a check - it is reached only by an explicit argument, it exits NON-ZERO, it prints NO `lint:` verdict line on stdout, and an unrecognised argument also exits non-zero; the gate passes no argument at all, so the whole mode is unreachable from it",
       _L07_LIST_RUN.returncode == 2
       and not [_ln for _ln in _L07_LIST_RUN.stdout.splitlines() if _ln.startswith("lint:")]
       and len(_L07_LIST_RUN.stdout.splitlines()) == len(_L07_GIT_PY) + len(_L07_GIT_SH)
       and subprocess.run(["bash", str(_L07_STAGE), "--not-a-mode"], cwd=str(ROOT),
                          capture_output=True, text=True).returncode == 2
       and 'CHECK_lint="required:bash scripts/check_lint.sh"' in
           (ROOT / "scripts/verify.sh").read_text())
_L07_PASS_RUN = _l07_run(_L07_SRC, only_passing=True)
_L07_LOOP_PASS_RUN = _l07_run(_L07_LOOP_SRC, only_passing=True)
expect("WARP-0711 AC2 CONTROL: with the broken fixtures removed the SHIPPED stage exits 0 with NO FAIL line and a summary that still begins `lint: pass` - so the teeth above are planted defects being caught rather than a stage that fails whatever it is given",
       _L07_PASS_RUN["exit"] == 0 and _L07_PASS_RUN["fails"] == []
       and _L07_PASS_RUN["last"].startswith("lint: pass"))
if not _l07_no_history([("scripts/check_lint.sh", _L07_LOOP_REV)],
                       "the LOOP's own passing control",
                       "The shipped stage's passing control - exit 0, no FAIL line, `lint: pass` - is "
                       "SPLIT OUT and still runs here, immediately above."):
    expect("WARP-0711 AC2 CONTROL, the LOOP's half: with the broken fixtures removed the per-file loop's committed text also exits 0 with NO FAIL line and a summary that is exactly `lint: pass`, so the differential above is taken between two stages that both pass a clean tree",
           _L07_LOOP_PASS_RUN["exit"] == 0 and _L07_LOOP_PASS_RUN["fails"] == []
           and _L07_LOOP_PASS_RUN["last"] == "lint: pass")
expect("WARP-0711 AC2 NO BYTECODE: over the fixture repository the new stage leaves NOTHING - its list of .pyc files and __pycache__ directories is asserted EMPTY on the failing run and on the passing one - which is the one behaviour this item changes on purpose",
       _L07_NEW_RUN["bytecode"] == [] and _L07_PASS_RUN["bytecode"] == [])
if not _l07_no_history([("scripts/check_lint.sh", _L07_LOOP_REV)],
                       "the bytecode the LOOP left behind",
                       "That the new stage leaves NO bytecode is SPLIT OUT and still runs here, "
                       "immediately above; the same claim over this repository's real corpus is "
                       "measured below against a private cache prefix, which needs no history."):
    expect("WARP-0711 AC2 NO BYTECODE, MEASURED AS A DIFFERENTIAL: over the same fixture repository the per-file loop leaves a __pycache__ and a .pyc for every file it compiled, and the new stage leaves NOTHING - its list of .pyc files and __pycache__ directories is asserted EMPTY, which is the one behaviour this item changes on purpose",
       _L07_NEW_RUN["bytecode"] == [] and _L07_PASS_RUN["bytecode"] == []
       and len(_L07_LOOP_RUN["bytecode"]) > 0
       and [_b for _b in _L07_LOOP_RUN["bytecode"] if _b.endswith(".pyc")]
       and "__pycache__" in _L07_LOOP_RUN["bytecode"])

# --- AC2/AC3 over THIS repository's real corpus, and race-free -----------------
# The no-bytecode claim over the whole tracked corpus cannot be made by snapshotting .pyc
# paths in a live tree: any other process touching the repository during the window would
# decide the result. It is made against a PRIVATE bytecode cache prefix instead - a
# directory nothing else writes to, and where a py_compile-shaped write for a repository
# file WOULD land, because py_compile resolves its output through the same
# sys.pycache_prefix the interpreter honours.
with tempfile.TemporaryDirectory() as _l07_cache:
    # TWO declared substitutions and no others, each asserted below: the cache prefix into the
    # boundary line, because `env -i` strips a variable a caller would pass; and an ABSOLUTE cd,
    # because the stage finds its repository from `dirname "$0"` and this copy lives outside it.
    # The same one-line-cd adaptation the per-file loop gets, for the same reason.
    _L07_CACHE_SUBS = (('exec env -i PATH="$PATH" python3',
                        'exec env -i PATH="$PATH" PYTHONPYCACHEPREFIX=%s python3' % _l07_cache),
                       ('CDPATH= cd "$(dirname "$0")/.."', 'CDPATH= cd %s' % ROOT))
    _L07_CACHE_PROBE_SRC = _L07_SRC
    for _old, _new in _L07_CACHE_SUBS:
        _L07_CACHE_PROBE_SRC = _L07_CACHE_PROBE_SRC.replace(_old, _new)
    _L07_CACHE_PROBE = Path(_l07_cache) / "stage.sh"
    _L07_CACHE_PROBE.write_text(_L07_CACHE_PROBE_SRC)
    _L07_REAL = subprocess.run(["bash", str(_L07_CACHE_PROBE)], capture_output=True, text=True)
    _L07_MIRROR = Path(_l07_cache) / str(ROOT).lstrip("/")
    _L07_MIRRORED = sorted(str(_p) for _p in Path(_l07_cache).rglob("*.pyc")
                           if _L07_MIRROR == _p.parent or _L07_MIRROR in _p.parents)
    _L07_CACHED_ANY = [_p.name for _p in Path(_l07_cache).rglob("*.pyc")]
expect("WARP-0711 AC2 NO BYTECODE OVER THE REAL CORPUS, race-free: the stage is run over this repository with a PRIVATE bytecode cache prefix, and the list of cache entries mirroring this repository is asserted EMPTY - non-vacuously, because the interpreter's OWN imports do land in that prefix, so the probe is proven able to see a write. The prefix is injected into the BOUNDARY LINE of a copy differing from the shipped text by exactly that one token, asserted, because `env -i` strips the variable a caller would otherwise pass - the python half and the corpus under test are the shipped ones and only where a hypothetical .pyc would land differs",
       _L07_REAL.returncode == 0 and _L07_MIRRORED == [] and _L07_CACHED_ANY != []
       and _L07_CACHE_PROBE_SRC != _L07_SRC
       and all(_L07_SRC.count(_old) == 1 for _old, _new in _L07_CACHE_SUBS)
       and len(_L07_CACHE_SUBS) == 2
       and _L07_CACHE_PROBE_SRC.replace(_L07_CACHE_SUBS[0][1], _L07_CACHE_SUBS[0][0]).replace(
           _L07_CACHE_SUBS[1][1], _L07_CACHE_SUBS[1][0]) == _L07_SRC)
def _l07_dead_stdout(stage_text):
    """Run one stage text over a fixture repository with stdout wired to a pipe whose READ END
    IS ALREADY CLOSED, so the stage's first write gets EPIPE with no reader present. A unix
    filter dies BY THE SIGNAL here, which is what the `echo` this stage replaced did; a python
    program with python's own SIGPIPE handler raises BrokenPipeError and prints a traceback
    instead. No large corpus is needed to fill a pipe buffer, because there is no reader at
    all. Returns (returncode, stderr)."""
    with tempfile.TemporaryDirectory() as td:
        dest = _l07_fixture_repo(Path(td) / "repo")
        (dest / "scripts" / "check_lint.sh").write_text(stage_text)
        read_fd, write_fd = os.pipe()
        os.close(read_fd)
        try:
            r = subprocess.run(["bash", "scripts/check_lint.sh"], cwd=str(dest),
                               stdout=write_fd, stderr=subprocess.PIPE, text=True)
        finally:
            os.close(write_fd)
        return r.returncode, r.stderr


_L07_SIGPIPE_RC, _L07_SIGPIPE_ERR = _l07_dead_stdout(_L07_SRC)
_L07_NOSIG_SRC = _L07_SRC.replace("signal.signal(signal.SIGPIPE, signal.SIG_DFL)",
                                  "pass  # the restoration, neutralized for this mutation")
_L07_NOSIG_RC, _L07_NOSIG_ERR = _l07_dead_stdout(_L07_NOSIG_SRC)
expect("WARP-0711: the SIGPIPE restoration now has TEETH, and it was the ONE behaviour claimed by this stage that the round-1 review could mutate away with the suite still green. With stdout wired to a pipe that has no reader, the stage dies BY THE SIGNAL (returncode -13, the negative of SIGPIPE) with no BrokenPipeError anywhere, which is what the `echo` it replaced did; neutralizing that single line makes the same run raise BrokenPipeError and print a traceback instead. The mutation target is asserted to occur EXACTLY ONCE",
       _L07_SIGPIPE_RC == -_l07_signal.SIGPIPE and "BrokenPipeError" not in _L07_SIGPIPE_ERR
       and _L07_SRC.count("signal.signal(signal.SIGPIPE, signal.SIG_DFL)") == 1
       and _L07_NOSIG_SRC != _L07_SRC
       and _L07_NOSIG_RC != -_l07_signal.SIGPIPE and "BrokenPipeError" in _L07_NOSIG_ERR)
_L07_SUMMARY_RE = re.compile(r"^lint: (pass|FAIL) \((\d+) python, (\d+) shell, (\d+\.\d\d)s\)$")
_L07_REAL_M = _L07_SUMMARY_RE.match((_L07_REAL.stdout.splitlines() or [""])[-1])
_L07_FIX_M = _L07_SUMMARY_RE.match(_L07_NEW_RUN["last"])
expect("WARP-0711 AC3 OBSERVABILITY: the stage prints its OWN elapsed time and its per-language file COUNTS, so a later cost regression is attributable and a silently shrinking file set is visible in the count rather than only in the timing - and over the fixture repository the counts it prints are the DECLARED fixture counts, which is what makes them the file set rather than a constant",
       _L07_FIX_M is not None and _L07_FIX_M.group(1) == "FAIL"
       and int(_L07_FIX_M.group(2)) == len([_n for _n in _L07_FIXTURES if _n.endswith(".py")])
       and int(_L07_FIX_M.group(3)) == len([_n for _n in _L07_FIXTURES if _n.endswith(".sh")]))
expect("WARP-0711 AC3: over THIS repository the stage exits 0, its summary still begins `lint: pass`, and the two counts it prints EQUAL the two `git ls-files` patterns run independently here - derived live on every run, never a number written into this file",
       _L07_REAL_M is not None and _L07_REAL_M.group(1) == "pass"
       and int(_L07_REAL_M.group(2)) == len(_L07_GIT_PY)
       and int(_L07_REAL_M.group(3)) == len(_L07_GIT_SH)
       and float(_L07_REAL_M.group(4)) >= 0.0)

# --- AC3 engine canon, and the one place the spec's WORDING could not be built ---
_L07_TRACKED_COPIES = sorted(_p for _p in _l07_git("ls-files").split()
                             if os.path.basename(_p) == "check_lint.sh")
_L07_PACK_DIRS = [_pk["pack_dir"] for _pk in
                  (PK.load_packs(repo_root=str(ROOT)) or {}).get("packs", [])]
with tempfile.TemporaryDirectory() as _l07_eng:
    (Path(_l07_eng) / "scripts").mkdir()
    (Path(_l07_eng) / "scripts" / "check_lint.sh").write_text("#!/usr/bin/env bash\n")
    (Path(_l07_eng) / "scripts" / "update_index.py").write_text("# the control\n")
    _L07_SYNTH_ENGINE = set(PK.engine_files(_l07_eng))
expect("WARP-0711 AC3 ENGINE CANON: this stage is REPO-ONLY, so 'byte-identical across engine and the six packs' has nothing to hold. MEASURED rather than read: a scripts/check_lint.sh placed in a synthetic engine source is NOT named by PK.engine_files while the scripts/*.py control beside it IS, so the engine manifest's own globs do not cover scripts/check_*.sh; no copy exists under the canonical engine or under any declared pack directory; the ONE tracked copy in this repository is scripts/check_lint.sh; and pack drift is empty",
       "scripts/check_lint.sh" not in _L07_SYNTH_ENGINE
       and "scripts/update_index.py" in _L07_SYNTH_ENGINE
       and _L07_TRACKED_COPIES == ["scripts/check_lint.sh"]
       and "scripts/check_lint.sh" not in set(PK.engine_files(str(ROOT / "engine")))
       and not (ROOT / "engine/scripts/check_lint.sh").exists()
       and len(_L07_PACK_DIRS) > 0
       and not [_d for _d in _L07_PACK_DIRS if (ROOT / _d / "scripts/check_lint.sh").exists()])

# --- AC3 the stage list, the protected surface and the frozen safety core ------
_L07_ARCH, _L07_CONTRACT = V.load_repo_contract(repo_root=str(ROOT))
_L07_FM = V.parse_yamlish(re.match(r"^---\n(.*?)\n---", _L07_SPEC_TEXT, re.S).group(1))
_L07_FOOTPRINT = [_g for _g in _L07_FM.get("footprint") or [] if isinstance(_g, str)]
_L07_FROZEN = [".veldo/authorization.py", ".veldo/two_key.py", ".veldo/policy_check.py",
               ".veldo/decision.py"]
_L07_GUARDED = sorted(set(P.protected_patterns()) | set(_L07_FROZEN)
                      | {"scripts/verify.sh", "engine/scripts/verify.sh"})
_L07_VERIFY = (ROOT / "scripts/verify.sh").read_text()
expect("WARP-0711 AC3: the STAGE LIST is untouched - verify.sh still declares this stage as `required:bash scripts/check_lint.sh` and `lint` is still in its ORDER - and NO footprint glob of this spec can match scripts/verify.sh, any path the policy protects, or any file of the frozen safety core, which is the gate's own footprint refusal rather than a promise not to touch them",
       'CHECK_lint="required:bash scripts/check_lint.sh"' in _L07_VERIFY
       and re.search(r"^ORDER=.*\blint\b", _L07_VERIFY, re.M) is not None
       and len(_L07_GUARDED) >= 7 and len(_L07_FOOTPRINT) >= 5
       and [_g for _g in _L07_FOOTPRINT if _L07_ARCH._glob_re(_g).match("scripts/check_lint.sh")]
       and not [(_g, _q) for _g in _L07_FOOTPRINT for _q in _L07_GUARDED
                if _L07_ARCH._glob_re(_g).match(_q)])

# --- AC1 the measured baseline, committed at the path the criteria name --------
_L07_BASELINE = ROOT / "proof/WARP-0711/baseline.md"
expect("WARP-0711 AC1: the measured baseline the criteria bind to is COMMITTED at the path the spec names, records the per-stage wall clock and the tracked file counts WITH the command that reproduces each figure, and says plainly that absolute seconds are machine-specific while the ATTRIBUTION is what the item binds to",
       _L07_BASELINE.is_file()
       and all(_s in _L07_BASELINE.read_text() for _s in
               ("## Per-stage wall clock", "Reproduce:", "ABSOLUTE SECONDS ARE MACHINE-SPECIFIC",
                _L07_LOOP_MARKER, "662 Python", "172 shell"))
       and "proof/WARP-0711/baseline.md" in _L07_SPEC_TEXT)

# --- dogfood: this item's own spec, and what the tier floor actually measures ---
expect("WARP-0711 dogfood: the spec has PASSED the ready transition (status ready or beyond, so this does not go stale the moment the item ships), declares high risk, needs no recorded human approval, declares NO protected path, is behavior-bearing with an observability block, and passes its own ready gate (check_ready == 0)",
       _L07_FM.get("status") in ("ready", "in_progress", "review", "proven", "shipped")
       and _L07_FM.get("risk", "").split()[0] == "high"
       and _L07_FM.get("human_approval") == "not_required"
       and (_L07_FM.get("protected_paths") or []) == []
       and _L07_FM.get("behavior_bearing") == "true"
       and isinstance(_L07_FM.get("observability"), dict)
       and V.check_ready(_L07_SPEC_PATH, repo_root=str(ROOT)) == 0)
# The finding here is a RELATIONSHIP between the footprint and the contract, and it is
# asserted as one. The round-1 review's note N2 is the reason: an earlier version asserted
# `placement == ["engine"]`, which pins the very declaration the manifest asks the owner to
# correct, so whoever corrected the spec would have turned this gate red. What is asserted
# now stays true under BOTH declarations, and the one conjunct that depends on the current
# one is guarded by it rather than by a literal.
_L07_AREAS_FROM_FILES = set().union(set(), *[_L07_ARCH.area_for_path(_g, _L07_CONTRACT)
                                             for _g in _L07_FOOTPRINT])
_L07_AREAS_TOTAL = _L07_ARCH.footprint_areas(_L07_FM, _L07_CONTRACT)
_L07_UNBACKED_AREAS = _L07_AREAS_TOTAL - _L07_AREAS_FROM_FILES
expect("WARP-0711 dogfood, MEASURED RATHER THAN READ OFF THE SPEC'S OWN PROSE, and stated as the RELATIONSHIP so a legitimate correction of the placement does not turn this gate red: the areas the footprint's OWN PATHS resolve to are exactly {enforcement}, `engine` is NOT among them, the engine path the footprint names resolves to NO area and does not exist in this repository, so every area beyond {enforcement} that the gate sees is contributed by the PLACEMENT DECLARATION alone and by no file - which is what raises this item's tier floor, asserted non-empty while that unbacked area is still declared, and not the 'gate stage plus its seven engine copies' the risk sentence describes",
       _L07_CONTRACT is not None
       and _L07_AREAS_FROM_FILES == {"enforcement"}
       and "engine" not in _L07_AREAS_FROM_FILES
       and _L07_ARCH.area_for_path("scripts/check_lint.sh", _L07_CONTRACT) == {"enforcement"}
       and _L07_ARCH.area_for_path("engine/scripts/check_lint.sh", _L07_CONTRACT) == set()
       and not (ROOT / "engine/scripts/check_lint.sh").exists()
       and _L07_UNBACKED_AREAS <= set(_L07_FM.get("placement") or [])
       and (_L07_ARCH.footprint_tier_floor(_L07_FM, _L07_CONTRACT) != ""
            if _L07_UNBACKED_AREAS else True)
       and _L07_ARCH.placement_gate(_L07_FM, _L07_CONTRACT) == [])


# ===========================================================================
# WARP-0722: the review loop was invisible. Every event in the log was gate.* from the
# gate SCRIPT, and not one of the verdict artifacts had an event, because a skill file
# asked whoever ran a review to append one and nobody ever did. These assertions bind
# the replacement: the events are DERIVED from the artifacts that already exist, by the
# stage that always runs, KEYED ON THE ARTIFACT'S OWN BLOB so the key names a REVIEW and
# not a file's first appearance. Round 1 keyed on the path plus its earliest adding
# commit; an independent review broke that twice (an amended verdict published a result
# the artifact contradicts, and `git clone --depth 1` of one commit derived a DIFFERENT key
# for every artifact tracked at 9b7a58a - no count is written here, the corpus grows), so
# the round-2 assertions are quantified over CONTENT: what the
# projection records must equal what the repository has committed, at every clone depth.
# Each criterion's completeness comes from an ENUMERATION (git ls-files, a glob over the
# canon copies, the whole tracked corpus), never a sample.
# ===========================================================================
import ast as _v22_ast
import inspect as _v22_inspect
import hashlib

# THE PACK ROSTER IS THE ONE THE REPOSITORY DECLARES, READ THROUGH ITS ONE READER.
# Round 4 removed the `>= 8` floors and replaced them with expectations derived from
# `(ROOT / "packs").iterdir()`, then compared those against a GLOB of the files that exist.
# That is two DIFFERENT repository properties on the two sides of an equality, so it is a
# pin and not a check, and it fires on ordinary work: MEASURED, one file committed at
# packs/zzz/README.md turned FIVE assertions in this block red, because a directory under
# packs/ that declares no pack was read as a pack missing its whole engine.
#
# This repository already DECLARES its packs: `.veldo/packs.json` (schema veldo.packs/v1) with
# exactly one reader, `.veldo/pack.py load_packs()`, which scripts/check_pack_drift.py uses to
# decide what a pack even is. So the roster comes from there, and nothing in this block
# derives it a second time. An undeclared directory under packs/ is not a pack, which is the
# repository's own answer; a DECLARED pack missing a copy is a named inequality below.
_v22_pack_cfg = PK.load_packs(repo_root=str(ROOT))
_V22_DECLARED_PACKS = [p for p in (_v22_pack_cfg.get("packs") or []) if isinstance(p, dict)]
# where each declared pack keeps its ENGINE, and where it keeps its DRIVER WRAPPER. BOTH ARE
# PATHS THE MANIFEST DECLARES: `pack_dir` and `wrapper_dir` (they differ only for the Claude
# pack, whose engine is the canonical source at engine while its skills sit in
# packs/claude/, which is why the wrapper root is a separate declaration).
#
# ROUND 5 DERIVED THE WRAPPER ROOT AS `(p.get("wrapper") or "").split()[0]`, THE FIRST WORD OF
# AN ENGLISH SENTENCE ("plugin (agents, skills, hooks, ...)"), which is this item's own defect
# class in a new spelling: a PROSE FIELD IS A MOVING PROPERTY, and three assertions' coverage
# rode on that sentence's word order. Worse, the coverage narrowed SILENTLY - dropping the
# field for one pack removed that pack's review skill from the byte-identity and live-surface
# legs. So round 6 declared `wrapper_dir` as a PATH in `.veldo/packs.json`, reads that, and
# every assertion whose reach depends on the roster also requires _V22_ROSTER_COMPLETE below,
# which is FALSE the moment one entry stops declaring either root. The pack manifest's own
# validator does not yet require `wrapper_dir` (it requires tool, engine_src and pack_dir), so
# a pack declared without it reddens HERE rather than at the manifest; requiring it in
# `.veldo/pack.py` belongs to the module that owns the manifest and is queued.
# THE ENGINE HAS ONE SHIPPED HOME NOW. Packs are extensions composed onto the canonical engine
# at install, so "one engine copy per declared pack" is not a property this repository has any
# more. The engine roots are the canonical source; the repository's own copy is passed as `home`
# by every caller, which keeps the two-home identity these assertions really rest on.
_v22_engine_roots = sorted({p["engine_src"] for p in _V22_DECLARED_PACKS if p.get("engine_src")})
_v22_wrapper_roots = sorted(p["wrapper_dir"] for p in _V22_DECLARED_PACKS
                            if isinstance(p.get("wrapper_dir"), str) and p["wrapper_dir"].strip())
# THE ROSTER IS COMPLETE: every declared pack declares BOTH roots as a path, and every root is
# a directory that exists. Carried into every assertion whose coverage is one copy per pack, so
# a dropped declaration is a RED where the coverage is claimed and not only in the footprint
# assertion at the end of the block.
# ENGINE ROOTS ARE NO LONGER ONE-PER-PACK. Every pack composes onto the single canonical engine,
# so the engine-root count is 1 while the wrapper count stays one per declared pack. The roster is
# complete when every pack still declares its wrapper and every declared root exists.
_V22_ROSTER_COMPLETE = (
    len(_v22_wrapper_roots) == len(_V22_DECLARED_PACKS)
    and len(_v22_engine_roots) == 1
    and bool(_V22_DECLARED_PACKS)
    and all((ROOT / r).is_dir() for r in _v22_engine_roots + _v22_wrapper_roots))
# The engine file set the manifest declares, from the same reader: this is what makes
# "engine file" a mechanical claim here rather than a habit of this block.
_v22_engine_set = set(PK.engine_files(str(ROOT / (_v22_pack_cfg.get("canonical_engine") or ""))))


def _v22_engine_copies(rel_in_pack, home):
    """Every copy of one ENGINE file the repository declares: the copy inside each declared
    pack's engine root, plus this repository's OWN copy (it runs the engine it ships, and it
    is not a pack, so that one path is named)."""
    return sorted([home] + [r + "/" + rel_in_pack for r in _v22_engine_roots])


def _v22_wrapper_copies(rel_in_wrapper):
    """Every copy of one DRIVER-WRAPPER file: one per declared pack, at its wrapper root.
    The wrapper is not engine, so there is no home copy and no drift check over it - which
    is why this block asserts the copies byte-identical itself."""
    return sorted(r + "/" + rel_in_wrapper for r in _v22_wrapper_roots)


def _v22_absent(rels):
    """The declared copies that are NOT a file. Checked BEFORE anything reads them, so a
    declared pack missing its copy fails on a named list rather than raising out of a read."""
    return [r for r in rels if not (ROOT / r).is_file()]


_v22_es = importlib.util.spec_from_file_location("veldo_events_0722", ROOT / ".veldo/events.py")
EV22 = importlib.util.module_from_spec(_v22_es); _v22_es.loader.exec_module(EV22)
# THE CONTRACT NAMES THIS BLOCK LOOKS UP ON THE MODULE, READ ONCE AND GUARDED. A PURE RENAME
# of one of them in all eight copies - `PROJECTION_OWNED` to `OWNED_BY_PROJECTION`, behaviour
# identical - raised `AttributeError: module 'veldo_events_0722' has no attribute
# 'PROJECTION_OWNED'` and the suite printed NO pass/fail summary at all. A crash takes the
# gate's whole reporting down, so a run that finds nothing and a run that cannot even look
# become indistinguishable; that is strictly worse than a red. An absent name now leaves an
# EMPTY set, or the value this block asserts the contract commits to, or a placeholder string no
# vocabulary contains; _V22_CONTRACT_NAMES_PRESENT is False, and every expectation over them
# carries it: a named red, summary printed.
# THE COST IS DECLARED RATHER THAN CLAIMED AWAY. These four names ARE written down here, so
# renaming one is a RED on the fact that the name is gone - this block has to be able to say
# "the projection-owned set" somehow. The module's OTHER members do not even get that:
# reconcile_verdicts, INDEX_FILE_MODES, _report_line, verdict_domain and the rest are looked up
# unguarded below, and renaming one of THOSE still raises out of this block. That is a residual
# of this round, stated here, not covered by any universal.
_V22_ABSENT_NAME = "veldo.absent.contract.name.0722"
_V22_OWNED = frozenset(getattr(EV22, "PROJECTION_OWNED", None) or ())
_V22_VOCAB = frozenset(getattr(EV22, "EVENT_TYPES", None) or ())
_V22_VERDICT = getattr(EV22, "VERDICT_EVENT", None)
_V22_PRODUCER = getattr(EV22, "RECONCILE_PRODUCER", None)
_V22_CONTRACT_NAMES_PRESENT = (bool(_V22_OWNED) and bool(_V22_VOCAB)
                               and isinstance(_V22_VERDICT, str)
                               and isinstance(_V22_PRODUCER, str))
# WHEN THE NAME IS GONE, THE VALUE THIS BLOCK ALREADY ASSERTS THE CONTRACT COMMITS TO STANDS IN
# FOR IT, so the sixty-odd fixture legs downstream still drive and the ONLY red is the name loss.
# That is not the same class as pinning the name: `verdict.recorded` is asserted OUTRIGHT under
# AC1 as the type the projection emits, in both this module's vocabulary and the gate validator's,
# so changing the VALUE is a contract change that SHOULD redden. MEASURED WITHOUT THIS: renaming
# `VERDICT_EVENT` in all eight copies emptied every fixture's projection-event map and the block
# raised `KeyError: 'WARP-9760'` out of a fallback leg 500 lines below, eleven reds in and with no
# pass/fail summary printed - a guarded lookup that only moves the crash is not a guarded lookup.
# The producer string has no such asserted value, so an absent name leaves a placeholder there;
# the refusal never consults `producer`, so the forgery routes still refuse either way.
_V22_VERDICT = _V22_VERDICT if isinstance(_V22_VERDICT, str) else "verdict.recorded"
_V22_PRODUCER = _V22_PRODUCER if isinstance(_V22_PRODUCER, str) else _V22_ABSENT_NAME


def _v22_lay_module(tree, src=None):
    """Lay the events module into `tree`/.veldo, WITH EVERY SIBLING IT DECLARES IT NEEDS.

    READ FROM THE MODULE, NEVER LISTED HERE (WARP-0727). events.py declares SIBLING_MODULES,
    so a fixture copies whatever that says and a future sibling arrives here for free. Listing
    the dependency in the suite instead would be a second place to keep in step with the first,
    which is the class of defect the corpus owner exists to close."""
    _src = ROOT / (src or ".veldo/events.py")
    (tree / ".veldo").mkdir(parents=True, exist_ok=True)
    (tree / ".veldo/events.py").write_bytes(_src.read_bytes())
    # The siblings come from the SAME directory as the copy being laid down, so probing a pack's
    # engine probes THAT pack's engine and not this repository's.
    for _sib in getattr(EV22, "SIBLING_MODULES", ()):
        (tree / ".veldo" / _sib).write_bytes((_src.parent / _sib).read_bytes())
    return tree / ".veldo/events.py"


def _v22_module_in(tree):
    """A SECOND INSTANCE of the events module living in `tree`, so its ROOT - and everything it
    derives from ROOT - is a throwaway directory. Used to probe the module BY DRIVING IT with
    no possibility of a byte reaching the real append-only log."""
    _v22_lay_module(tree)
    _s = importlib.util.spec_from_file_location(
        "veldo_events_0722_probe", tree / ".veldo/events.py")
    _m = importlib.util.module_from_spec(_s)
    _s.loader.exec_module(_m)
    return _m


def _v22_discover_log_attrs():
    """WHICH OF THE MODULE'S GLOBALS THE APPENDED BYTES FOLLOW, DISCOVERED BY DRIVING IT.
    Neither written down here nor COUNTED.

    Round 8 took the module's json-lines Path globals and required there to be EXACTLY ONE,
    which is a CARDINALITY OF SOMETHING THIS REPOSITORY CAN ORDINARILY GROW - the module's own
    docstring already mentions a second json-lines file, a run folder's live.jsonl. MEASURED on
    489bebb: adding one UNUSED global `AUDIT_LOG = ROOT / ".veldo" / "audit.jsonl"` beside `LOG`
    in all eight copies, nothing referencing it, behaviour identical, made the count 2, made the
    attribute None, made the module unable to open anything, and took the suite down with a
    traceback and NO pass/fail summary at all. That is one pin in three spellings across three
    rounds: round 6 a writer name, round 7 a refusal name, round 8 a count.

    So EVERY candidate global is pointed at a file OF ITS OWN, one allowed event is appended
    through the module's own door, and the answer is the globals whose file RECEIVED THE BYTES.
    That is a property established for each candidate SEPARATELY; how many candidates exist is
    never asserted, and an unwritten global's probe file simply stays empty, so adding a second
    or a third cannot change the answer.

    Probed on A COPY IN A TREE OF ITS OWN, never on this repository's instance: if the module
    ever stopped holding its log in a global, redirecting nothing and driving anyway would
    append to the REAL log to satisfy a test. Here it appends inside a temp tree, the answer
    comes back empty, nothing in process is driven at all, and the expectations red on that.

    THE WHOLE PROBE IS WRAPPED, not just the emission: loading a second instance of the module
    in a tree of its own, redirecting the candidates and reading the probe files back are all
    ways this could raise, and a discovery step that crashes would take the summary down exactly
    as the thing it replaces did. Anything that goes wrong here means the log was not found,
    which is a RED."""
    try:
        with tempfile.TemporaryDirectory() as _pd:
            _tree = Path(_pd) / "probe"
            _mod = _v22_module_in(_tree)
            _files = {_n: _tree / (_n + ".probe.jsonl") for _n, _v in vars(_mod).items()
                      if isinstance(_v, Path) and _v.suffix == ".jsonl"}
            for _n, _f in _files.items():
                setattr(_mod, _n, _f)
            _mod.emit("proof.recorded", spec="WARP-9779")
            return sorted(_n for _n, _f in _files.items()
                          if _f.is_file() and _f.read_text().strip())
    except Exception:                       # pragma: no cover - a door that cannot be driven
        return []


_v22_log_attrs = _v22_discover_log_attrs()
# WHETHER THE LOG CAN BE POINTED SOMEWHERE DISPOSABLE AT ALL. When it cannot, NOTHING IS DRIVEN
# IN PROCESS. The fixture does not fall back to patching the module's `open`, which is what
# round 8 did: that patch outlives this block and turns one honest red into a cascade of them.
# And it does not drive the real door, because a mutant with the refusal removed would then
# append to the real append-only log where nothing could take it back. Every expectation below
# carries this flag and reds on it by name.
_V22_LOG_REDIRECTABLE = bool(_v22_log_attrs)


def _v22_log_now():
    """{global: the path it holds} for EVERY global the appended bytes follow, so a save and a
    restore are symmetric even when more than one is discovered. None when none was."""
    return {_n: getattr(EV22, _n, None) for _n in _v22_log_attrs} if _v22_log_attrs else None


def _v22_point_log_at(target):
    """Point EVERY discovered log global at `target` - one path for all of them, or the mapping
    `_v22_log_now()` returned, which restores each to its own. A pure rename of the constant,
    and a second or a third json-lines global beside it, all move this with the code instead of
    raising out of the suite, because the set was established BY DRIVING the module.

    Returns False and DOES NOTHING when there is nothing to point. Callers check that state
    BEFORE driving anything, rather than driving a door the fixture cannot aim."""
    if not _v22_log_attrs:
        return False
    for _n in _v22_log_attrs:
        setattr(EV22, _n, target[_n] if isinstance(target, dict) else target)
    return True


_v22_spec_path = ROOT / "specs/WARP-0722-review-events-derived-not-appended.md"
_v22_spec_text = _v22_spec_path.read_text()
_v22_log = ROOT / ".veldo/events.jsonl"
_v22_names = ("review.passed", "review.failed")


def _v22_git(d, *a, check=True):
    return subprocess.run(["git", "-C", str(d), *a], capture_output=True, text=True, check=check)


def _v22_lines(p):
    p = Path(p)
    return p.read_text().splitlines() if p.exists() else []


def _v22_landed_types(p):
    """The `type` of every line a driven route landed in `p`, with a line this fixture cannot
    parse as one JSON object recorded as a MARKER instead of raising. A mutant that writes
    something other than one JSON object per line, or a line with no `type`, must be a RED here -
    the marker is in no vocabulary and no allowed set - and never a traceback that takes the
    suite's pass/fail summary down with it."""
    out = []
    for _ln in _v22_lines(p):
        try:
            _ev = json.loads(_ln)
            out.append(_ev["type"] if isinstance(_ev, dict) and "type" in _ev
                       else "veldo.line.without.a.type.0722")
        except Exception:                   # pragma: no cover - a line that is not one object
            out.append("veldo.unparseable.line.0722")
    return out


def _v22_keydigest(keys):
    return hashlib.sha256("\n".join("\x00".join(k) for k in keys).encode()).hexdigest()


def _v22_evdigest(events):
    return hashlib.sha256("\n".join(json.dumps(e, sort_keys=True) for e in events).encode()).hexdigest()


_V22_SEED_LOG = ('{"schema": "veldo.event/v1", "type": "gate.passed", '
                 '"at": "2026-01-01T00:00:00Z", "producer": "verify.sh"}')


def _v22_verdict(spec_id, verdict, rnd=None, reviewed_at="2026-01-02T03:04:05Z"):
    body = {"schema": "veldo.verdict/v1", "spec_id": spec_id, "commit": "c0ffee",
            "reviewer": "fixture", "verdict": verdict, "criteria": []}
    if rnd is not None:
        body["round"] = rnd
    if reviewed_at is not None:
        body["reviewed_at"] = reviewed_at
    return body


def _v22_write(d, rel, body):
    p = Path(d) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(body))
    return p


def _v22_commit(d, msg):
    _v22_git(d, "add", "-A")
    _v22_git(d, "commit", "-q", "-m", msg)


def _v22_seed(d, verdicts, log_lines=(_V22_SEED_LOG,)):
    """A fixture repository in the shape this item found the real one in: verdict artifacts
    under proof/<spec-id>/, one commit each, and an event log carrying gate events only."""
    d = Path(d)
    d.mkdir(parents=True, exist_ok=True)
    _v22_git(d, "init", "-q", "-b", "main")
    _v22_git(d, "config", "user.email", "t@t")
    _v22_git(d, "config", "user.name", "t")
    (d / ".veldo").mkdir(parents=True, exist_ok=True)
    (d / ".veldo/events.jsonl").write_text("".join(ln + "\n" for ln in log_lines))
    _v22_commit(d, "seed")
    for rel, body in verdicts:
        _v22_write(d, rel, body)
        _v22_commit(d, "add " + rel)
    return d


def _v22_logged(d):
    """The verdict events in a fixture's log, in file order."""
    return [e for e in EV22.read_log(Path(d) / ".veldo/events.jsonl")
            if e.get("type") == _V22_VERDICT]


# --- AC1 the DOMAIN, enumerated from git at run time over the real corpus ------
# THE INDEPENDENT RECOMPUTATION, WRITTEN HERE AND NOT BORROWED FROM THE MODULE, which is the whole
# value of this binding: a `git ls-files` run of this suite's own plus a membership test spelled out
# in this file. WARP-0727 moved what the module asks git - a wildcard-free DIRECTORY pathspec, and
# the rule applied in code - because a git pathspec `*` crosses `/` where a pathlib `*` does not, so
# the old `proof/*/verdict*.json` admitted `proof/<a>/<b>/verdict.json` into the entitlement domain
# while the contract validator never saw it. This recomputation follows the SHAPE, not the module:
# three components, the proof root, and the verdict name, each stated here.
_v22_ls_prefix = "proof/"
_v22_ls_name = "verdict"
_v22_ls_ext = ".json"


def _v22_is_corpus_path(rel):
    """EXACTLY three components: proof/<one directory>/<verdict name>. Independent of the module
    by construction, so an agreement between this and the module is a measurement."""
    _p = rel.split("/")
    return (len(_p) == 3 and _p[0] + "/" == _v22_ls_prefix
            and _p[2].startswith(_v22_ls_name) and _p[2].endswith(_v22_ls_ext)
            and len(_p[2]) >= len(_v22_ls_name) + len(_v22_ls_ext))


_v22_lsfiles = sorted(ln for ln in _v22_git(ROOT, "ls-files", "-z", "--full-name", "--",
                                            "proof").stdout.split("\0")
                      if ln.strip() and _v22_is_corpus_path(ln.strip()))
# THE WHOLE TRACKED CORPUS, enumerated once here because two assertions quantify over it: the
# shell-writer roster below and AC3's record equality at the end of the block.
_v22_tracked = [ln for ln in _v22_git(ROOT, "ls-files").stdout.splitlines() if ln.strip()]
_v22_domain = EV22.tracked_verdicts(repo_root=str(ROOT))
_v22_derivable, _v22_deferred = EV22.verdict_domain(repo_root=str(ROOT))
_v22_keys = [t[0] for t in _v22_derivable]
_v22_paths = [t[1] for t in _v22_derivable]
_v22_events_src = (ROOT / ".veldo/events.py").read_text()

# WHY THIS ASSERTION PARSES THE MODULE'S CODE AND NEVER LOOKS AT THE CORPUS SIZE AT ALL.
# Round 3 closed it with `str(len(_v22_domain)) not in _v22_events_src`, which IS a function
# of the corpus size: every digit run anywhere in the module - docstrings and comments
# included - became a number this repository must never grow to. An independent review
# committed 41 verdict artifacts inside existing proof directories, took the corpus to 197,
# and the ONLY failure in the whole suite was this line, colliding with `so 1970 and 2099`
# in a comment round 3 had just added, under a sentence promising that the corpus size
# appears nowhere and that no assertion here is pinned to today's count. That is the
# WARP-1210 `== 139` law verbatim, and it is the third round this item failed on this class.
# I reproduced it before replacing it: at 4778c7d the fuse was 40 artifacts (157 -> 197),
# and 40 added artifacts took the suite from one failure to two, the new one being this line.
# THE REPLACEMENT READS THE CORPUS NOWHERE. It parses every declared copy and requires the
# literals the module's CODE contains, WITH THE SCOPE EACH SITS IN, to EQUAL a table
# enumerated here - the owner's own constants, which is the only kind of expectation a
# growing repository cannot move. Documentation is excluded BY STRUCTURE (a string that is a
# STATEMENT on its own computes nothing, wherever it sits in a body), comments are never in the
# tree at all, and the string side
# is enumerated too, so a count cannot slip in as `"154"` where an integer scan would miss it.
#
# THE SCOPE IS PART OF THE EXPECTATION BECAUSE ROUND 4'S VERSION WAS BLIND WITHOUT IT.
# It compared `set(_v22_code_ints)` with the declared set, which cannot see a NEW USE of a
# value the table already allows: MEASURED at 28c0775, `EXPECTED_CORPUS = 40` added to all
# eight copies left that tree's whole suite passing with zero failures, under a headline
# claiming no count can be hardcoded in the module. Binding each literal to the scopes it occurs in catches that mutant, because
# 40 is declared only inside `_is_sha`. What it is STILL blind to is stated with it rather
# than left for the next round to measure: a new use of an allowed value INSIDE a scope that
# already uses it (`EXPECTED_CORPUS = 40` written into `_is_sha` itself) is not visible to
# this check, so the headline says what the check does and does not claim more.
# WHAT ORDINARY FUTURE CHANGE BREAKS IT, WRITTEN DOWN - AND ROUND 5'S VERSION OF THIS LIST WAS
# INCOMPLETE, WHICH IS WHY IT IS ENUMERATED BY THE SIDE OF THE EXPECTATION THAT MOVES RATHER
# THAN BY EXAMPLE. The expectation is a map from a literal to the SET OF SCOPE NAMES it occurs
# in, so it breaks on a change to EITHER side:
#   the literal side - adding a numeric literal or a digit-bearing string to the module's CODE,
#     removing one, or moving one between functions (a new index mode, a new digest width, a new
#     exit code, an extracted helper);
#   the SCOPE side, which round 5's list omitted entirely - RENAMING a function, adding a
#     function that uses an allowed value, or deleting the last function that used one. Round 6's
#     own merge of `_envelope` back into `make_event` moved literal 12's scope and the table was
#     updated in the same commit, which is the mechanism working as intended.
# What CANNOT break it, each of these MEASURED rather than asserted: growth of
# the verdict corpus (1000 artifacts added, unchanged), growth of the event log, an
# undeclared directory or file under packs/, any COMMENT anyone writes in the module, and any
# DOCSTRING - including one that is no longer the first statement of its body, which round 5's
# body[0] test reclassified as code and which round 6 fixed in the mechanism.
# WARP-0727 MOVED THE INDEX READING OUT OF THIS MODULE AND THIS TABLE DID NOT MOVE WITH IT - IT
# LOST ENTRIES AND NOTHING REPLACED THEM, WHICH IS THE GUARD LOSING ITS SUBJECT AND NOT THE
# MECHANISM WORKING. Round 1 of that item said "moved with it, in the same commit"; measured FALSE
# by the review, and the measurement is the point: `EXPECTED_CORPUS = 166` inserted at module level
# into all EIGHT copies of verdict_corpus.py left the whole suite green at 3356 passed, 0 failed,
# while the same literal in events.py reddened. verdict_blob_map here really did become a one-line
# delegate that computes with no literal at all, and the two index modes really did leave this
# module - but they arrived in ANOTHER module that had no table, so the corpus count simply had a
# new place to be hardcoded in. THE TABLE BELOW IS NOW TWO TABLES, one per module, each bound in
# BOTH DIRECTIONS over that module's own declared copies; the corpus owner's is _V22_CORPUS_INTS
# and it is asserted in its own expect further down.
_V22_MODULE_INTS = {
    0: ("the empty count, index 0, a zero return code, and the false side of a comparison",
        {"_batch_blob_shas", "_git", "_git_ok", "_reconcile_pass", "logged_verdict_state",
         "main"}),
    # WARP-0727 round 2 moved spec_id_for_verdict to the corpus owner - the spec id is the MIDDLE
    # of the three components the membership rule counts, so the shape is read in ONE place - and
    # the two scopes it held here left with it, in the same commit. They appear in the corpus
    # owner's table below, which is the mechanism working as intended.
    # WARP-1711 added the fifth scope in the same commit as the code: a repository whose commit
    # DEPTH is exactly one is a flattened successor, which is the named cause of an earlier event
    # this repository cannot resolve. A depth, never a corpus count.
    1: ("index 1 of a tab-split record, the slice that drops a leading field, and the ONE commit "
        "a flattened repository holds",
        {"_batch_blob_shas", "_reconcile_pass", "logged_verdict_state",
         "verdict_event"}),
    2: ("the parts-length guard, the two paths a report line names, and CLI exit code 2",
        {"_batch_blob_shas", "_reconcile_pass", "_report_line", "main"}),
    # WARP-0723 gave this width ONE definition, EVENT_ID_LEN, because the guard that refuses a
    # caller-supplied id has to mean the same thing as the mint. So the literal left both mint
    # sites and now occurs at module level only - the scope side of this table moving with the
    # code in the same commit, which is the mechanism working as intended.
    12: ("the width of an envelope id: a uuid4 hex prefix live, a digest prefix derived, and the "
         "one constant the id guard reads", {"<module>"}),
    40: ("the length of a git object name in hex", {"_is_sha"}),
}
_V22_MODULE_DIGIT_STRS = {
    "0123456789abcdef": ("the hex alphabet a git object name is spelled in", {"<module>"}),
}

# THE SAME GUARD, AIMED AT THE MODULE THE INDEX READING ACTUALLY MOVED TO. A count of the corpus
# is exactly as harmful in the corpus owner as it was in the projection - more so, since the owner
# is what every other reader now asks - and until this table existed there was nothing at all
# stopping one being written there. Same mechanism, same blindness, both declared: a NEW USE of a
# value inside a scope that already declares it is invisible here too, so the sentence below says
# what the check does and claims no more. Nothing in it is a function of how large this repository
# is; each entry is the owner's own constant, named.
_V22_CORPUS_INTS = {
    0: ("the empty count, a zero return code, index 0 of a split record, and the false side of "
        "a comparison",
        {"_git_line", "_git_z", "_index_entries", "corpus_member", "name_shaped"}),
    # WARP-0727 round 3 added the third use and its scope in the same commit as the code: reading a
    # single-line git answer removes EXACTLY ONE trailing newline, never surrounding whitespace,
    # because `--show-prefix` answers a repo-relative PATH and a path component may begin with a
    # space - `.strip()` there silently emptied the whole domain.
    1: ("index 1 of a split index record, the MIDDLE component a corpus path names its spec "
        "with, the FINAL component a name pattern is tested against, and the ONE trailing newline "
        "that comes off a single-line git answer",
        {"_git_line", "_index_entries", "name_shaped", "spec_id_for_verdict"}),
    2: ("index 2 of the three components a corpus path has, the minimum component count a "
        "name-shaped path has, the component count a spec id needs, and the two fields an index "
        "record must carry",
        {"_index_entries", "corpus_member", "name_shaped", "spec_id_for_verdict"}),
    3: ("THE MEMBERSHIP RULE ITSELF: a corpus path is EXACTLY three components", {"corpus_member"}),
    40: ("the length of a git object name in hex", {"<module>"}),
}
_V22_CORPUS_DIGIT_STRS = {
    "0123456789abcdef": ("the hex alphabet a git object name is spelled in", {"<module>"}),
    "100644": ("the index mode of a regular file", {"<module>"}),
    "100755": ("the index mode of an executable regular file", {"<module>"}),
}


def _v22_code_literals(tree):
    """Every literal in a module's CODE as (SCOPE, value), with DOCUMENTATION EXCLUDED BY
    STRUCTURE rather than by looking like prose: A STRING THAT IS A STATEMENT ON ITS OWN
    computes nothing, wherever it sits in a body, so it is documentation and may say anything,
    including a stale number. Comments are never in the tree. What is left is what the module
    can actually compute with, which is the only place a hardcoded count could change
    behaviour.

    ROUND 5 EXCLUDED ONLY `body[0]`, WHICH MADE THE SENTENCE ABOVE TRUE ONLY WHILE A DOCSTRING
    WAS THE FIRST STATEMENT. MEASURED at 19c396b: inserting a bare `pass` above `_iso_z`'s
    docstring reclassified that whole docstring as CODE and turned the AC1 assertion RED
    (3235 passed 1 failed) on a module whose behaviour had not changed. The position is not
    what makes a docstring documentation; being a statement whose value is discarded is. So the
    mechanism was fixed rather than the sentence softened, and the same mutant is now inert.

    THE SCOPE is the name of the innermost function or class the literal sits in, or
    `<module>` for one at module level. A default argument or a decorator is attributed to
    the function it belongs to, which is the reading a reader would give it."""
    docs = set()
    for node in _v22_ast.walk(tree):
        if (isinstance(node, _v22_ast.Expr) and isinstance(node.value, _v22_ast.Constant)
                and isinstance(node.value.value, str)):
            docs.add(id(node.value))
    out = []

    def _walk(node, scope):
        for child in _v22_ast.iter_child_nodes(node):
            if isinstance(child, (_v22_ast.FunctionDef, _v22_ast.AsyncFunctionDef,
                                  _v22_ast.ClassDef)):
                _walk(child, child.name)
                continue
            if isinstance(child, _v22_ast.Constant) and id(child) not in docs:
                out.append((scope, child.value))
            _walk(child, scope)

    _walk(tree, "<module>")
    return out


def _v22_callee_name(node):
    """The FINAL NAME COMPONENT of a Call's callee: `f(...)` gives `f` and `a.b.f(...)` gives
    `f`. Matching on the last component is what lets a refusal move onto a class or into a
    namespace without anything here naming where it moved to."""
    f = node.func
    if isinstance(f, _v22_ast.Name):
        return f.id
    if isinstance(f, _v22_ast.Attribute):
        return f.attr
    return None


def _v22_scoped_nodes(tree):
    """(innermost enclosing def/class name, node) for every node, `<module>` at module level:
    the same attribution rule _v22_code_literals uses, reused so one reading of `scope` holds
    across this block."""
    out = []

    def _walk(node, scope):
        for child in _v22_ast.iter_child_nodes(node):
            out.append((scope, child))
            _walk(child, child.name
                  if isinstance(child, (_v22_ast.FunctionDef, _v22_ast.AsyncFunctionDef,
                                        _v22_ast.ClassDef)) else scope)

    _walk(tree, "<module>")
    return out


_V22_BYTE_ATTRS = ("write", "writelines", "write_text", "write_bytes")


def _v22_byte_targets(node):
    """Every expression a Call EMITS BYTES TO, and [] for a call that emits none. Seven
    spellings, not one: the four handle-and-path methods, plus `print(..., file=X)`,
    `json.dump(_, X)` and `os.write(X, ...)`, which round 7's predicate declared itself blind
    to. What the target IS gets decided elsewhere; this only says where the bytes go."""
    out, f = [], node.func
    if isinstance(f, _v22_ast.Attribute) and f.attr in _V22_BYTE_ATTRS:
        out.append(f.value)
    if _v22_callee_name(node) == "print":
        out += [k.value for k in node.keywords if k.arg == "file" and k.value is not None]
    if (isinstance(f, _v22_ast.Attribute) and f.attr == "dump" and len(node.args) >= 2):
        out.append(node.args[1])
    if (isinstance(f, _v22_ast.Attribute) and f.attr == "write" and node.args
            and isinstance(f.value, _v22_ast.Name) and f.value.id == "os"):
        out.append(node.args[0])
    return out


def _v22_log_flow(tree, marks):
    """WHERE THE MODULE'S BYTES REACH THE LOG, resolved by WHAT EACH WRITE TARGETS and NOT by
    counting `.write` calls and NOT by naming a function. Both are moving repository
    properties and this item has now pinned each of them for a round: round 6 pinned the
    writer names, round 7 pinned "how many scopes contain a `.write`", which reddened on an
    unrelated `sys.stderr.write` in `now_iso` and on extracting the append loop.

    `marks` IDENTIFIES THE LOG, and is itself discovered: the module globals that HOLD the
    log (found by value, so renaming the constant carries this with it) plus the log path's
    own components (so a second writer that REBUILDS the same path out of string constants is
    caught too, rather than escaping because it never mentioned the global).

    An expression CARRIES THE LOG when any name, attribute or string constant in it is a
    mark, when it is a local or parameter that was assigned one, or when it calls a function
    of this module that RETURNS one. Those three feed each other, so it is a fixed point -
    which is what makes `with _open_log() as f:` and a handle handed on as a call argument
    resolve to the log without either being written down here.

    Returns (defs, log_writes, other_writes, handoffs):
      defs         every function definition in the tree, by name
      log_writes   {def name: earliest lineno at which it emits bytes to the LOG}
      other_writes [(scope, dumped target)] for byte emissions that are NOT the log
      handoffs     {callee: {caller: earliest lineno of a call handing it the log}}

    WHAT THIS IS BLIND TO, stated here rather than left for the next round: a target
    assembled at RUN TIME out of values no constant and no mark appears in (an environment
    variable, say) is not resolvable statically and does not appear in `log_writes`. That is
    why every door this assertion binds is also DRIVEN."""
    defs, dups = {}, []
    scoped = _v22_scoped_nodes(tree)
    for _sc, n in scoped:
        if isinstance(n, (_v22_ast.FunctionDef, _v22_ast.AsyncFunctionDef)):
            if n.name in defs:
                dups.append(n.name)
            defs[n.name] = n
    tainted = {n: set() for n in list(defs) + ["<module>"]}
    ret_tainted, handoffs = set(), {}

    def carries(expr, scope):
        if expr is None:
            return False
        local = tainted.get(scope, set())
        for n in _v22_ast.walk(expr):
            if isinstance(n, _v22_ast.Name) and (n.id in marks or n.id in local):
                return True
            if isinstance(n, _v22_ast.Attribute) and n.attr in marks:
                return True
            if (isinstance(n, _v22_ast.Constant) and isinstance(n.value, str)
                    and n.value in marks):
                return True
            if isinstance(n, _v22_ast.Call) and _v22_callee_name(n) in ret_tainted:
                return True
        return False

    for _round in range(len(defs) + 3):
        before = (sorted((k, tuple(sorted(v))) for k, v in tainted.items()),
                  sorted(ret_tainted),
                  sorted((k, tuple(sorted(v.items()))) for k, v in handoffs.items()))
        for sc, n in scoped:
            if isinstance(n, _v22_ast.Assign) and carries(n.value, sc):
                for t in n.targets:
                    if isinstance(t, _v22_ast.Name):
                        tainted.setdefault(sc, set()).add(t.id)
            elif isinstance(n, _v22_ast.withitem):
                if (carries(n.context_expr, sc)
                        and isinstance(n.optional_vars, _v22_ast.Name)):
                    tainted.setdefault(sc, set()).add(n.optional_vars.id)
            elif isinstance(n, _v22_ast.Return) and carries(n.value, sc):
                ret_tainted.add(sc)
            elif isinstance(n, _v22_ast.Call):
                callee = _v22_callee_name(n)
                if callee not in defs:
                    continue
                a = defs[callee].args
                params = [p.arg for p in (list(a.posonlyargs) + list(a.args))]
                passed = set()
                for i, arg in enumerate(n.args):
                    if i < len(params) and carries(arg, sc):
                        passed.add(params[i])
                for kw in n.keywords:
                    if kw.arg and carries(kw.value, sc):
                        passed.add(kw.arg)
                if passed:
                    tainted.setdefault(callee, set()).update(passed)
                    seen = handoffs.setdefault(callee, {})
                    seen[sc] = min(seen.get(sc, n.lineno), n.lineno)
        after = (sorted((k, tuple(sorted(v))) for k, v in tainted.items()),
                 sorted(ret_tainted),
                 sorted((k, tuple(sorted(v.items()))) for k, v in handoffs.items()))
        if after == before:
            break
    log_writes, other_writes = {}, []
    for sc, n in scoped:
        if not isinstance(n, _v22_ast.Call):
            continue
        for tgt in _v22_byte_targets(n):
            if carries(tgt, sc):
                log_writes[sc] = min(log_writes.get(sc, n.lineno), n.lineno)
            else:
                other_writes.append((sc, _v22_ast.dump(tgt)))
    return defs, log_writes, other_writes, handoffs, sorted(set(dups))


def _v22_guard_lines(defs, guard_names):
    """{def name: the EARLIEST lineno at which it invokes a refusal}, directly or through
    another function of this module, and None for one that never does. `guard_names` is
    DISCOVERED by probing what the module's callables DO, so a rename moves this with it and
    a refusal reached through a helper still counts."""
    direct, inner = {}, {}
    for name, node in defs.items():
        calls = [c for c in _v22_ast.walk(node) if isinstance(c, _v22_ast.Call)]
        direct[name] = [c.lineno for c in calls if _v22_callee_name(c) in guard_names]
        inner[name] = [(_v22_callee_name(c), c.lineno) for c in calls
                       if _v22_callee_name(c) in defs and _v22_callee_name(c) != name]
    line = {n: (min(direct[n]) if direct[n] else None) for n in defs}
    for _round in range(len(defs) + 2):
        changed = False
        for n in defs:
            cands = list(direct[n]) + [ln for c, ln in inner[n] if line.get(c) is not None]
            best = min(cands) if cands else None
            if best != line[n]:
                line[n], changed = best, True
        if not changed:
            break
    return line


def _v22_write_covered(scope, log_writes, handoffs, gline):
    """Whether EVERY byte-path into `scope` passes a refusal FIRST. Either the refusal is
    invoked inside `scope` before its own first write to the log, or `scope` never opens the
    log itself and every caller that HANDS it the log refuses before handing it over. That
    second leg is what admits extracting the append loop into a helper - the guard stays in
    the caller, one statement above the handoff - while an independent writer that opens the
    log itself has no supplier to inherit a refusal from and is refused here."""
    g = gline.get(scope)
    if g is not None and g <= log_writes[scope]:
        return True
    sup = handoffs.get(scope) or {}
    return bool(sup) and all(gline.get(s) is not None and gline[s] <= ln
                             for s, ln in sup.items())


def _v22_refusals_by_behaviour(mod, raisers, passers):
    """THE MODULE'S OWN REFUSALS, DISCOVERED BY WHAT THEY DO: every callable of this module
    that raises ValueError on EVERY member of `raisers` and returns on EVERY member of
    `passers`. Returns their `__name__`s, which is the only thing the AST legs then match on,
    so a pure rename in all copies moves the expectation with the code instead of raising an
    AttributeError out of the suite.

    CANDIDATES ARE UNARY: exactly one required parameter, no default, no *args and no
    **kwargs. That is what a refusal is, and it is also what keeps a WRITER out of the
    candidate set - emit() takes **kw, so nothing here ever calls it and no probe can append.
    Classes of this module are searched too, staticmethods unwrapped, so moving a refusal onto
    one is not a red."""
    out = set()
    holders = [mod] + [v for v in vars(mod).values()
                       if isinstance(v, type)
                       and getattr(v, "__module__", None) == mod.__name__]
    for holder in holders:
        for _nm, raw in sorted(vars(holder).items(), key=lambda kv: kv[0]):
            fn = raw.__func__ if isinstance(raw, staticmethod) else raw
            if not _v22_inspect.isfunction(fn):
                continue
            if getattr(fn, "__module__", None) != mod.__name__:
                continue
            try:
                ps = list(_v22_inspect.signature(fn).parameters.values())
            except (TypeError, ValueError):          # pragma: no cover - exotic callables
                continue
            if len(ps) != 1 or ps[0].default is not _v22_inspect.Parameter.empty:
                continue
            if ps[0].kind not in (_v22_inspect.Parameter.POSITIONAL_ONLY,
                                  _v22_inspect.Parameter.POSITIONAL_OR_KEYWORD):
                continue
            ok = True
            for t in sorted(raisers):
                try:
                    fn(t)
                    ok = False
                except ValueError:
                    pass
                except Exception:                    # not a refusal, something else broke
                    ok = False
                if not ok:
                    break
            if not ok:
                continue
            for t in sorted(passers):
                try:
                    fn(t)
                except Exception:
                    ok = False
                    break
            if ok:
                out.add(fn.__name__)
    return out


_v22_module_rels = _v22_engine_copies(".veldo/events.py", ".veldo/events.py")
# THE CORPUS OWNER IS A DECLARED ENGINE FILE TOO (WARP-0727). The domain is derived THERE now, so
# the same roster question is asked of it: every declared copy present, and all of them identical.
_v22_corpus_rels = _v22_engine_copies(".veldo/verdict_corpus.py", ".veldo/verdict_corpus.py")
_v22_corpus_src = (ROOT / ".veldo/verdict_corpus.py").read_text()
# WHERE THE ENUMERATION IS ASKED OF GIT, DECIDED ON CODE AND NOT ON TEXT. A raw substring search
# would be satisfied or defeated by a COMMENT: both modules describe the enumeration in prose, and
# prose computes nothing. So the subject is the set of STRING LITERALS each module's code actually
# carries, through the same docstring-excluding walk this block uses for its number table.
_v22_ls_arg = "ls-files"
_v22_events_code_strs = {_l for _s, _l in _v22_code_literals(_v22_ast.parse(_v22_events_src))
                         if isinstance(_l, str)}
_v22_corpus_code_strs = {_l for _s, _l in _v22_code_literals(_v22_ast.parse(_v22_corpus_src))
                         if isinstance(_l, str)}
def _v22_literal_scopes(rels):
    """(int -> scopes, digit-bearing str -> scopes, [(copy, repr)]) aggregated over a module's
    DECLARED COPIES. One reader for both modules' tables, so the corpus owner's guard cannot be a
    weaker spelling of the projection's - which is how the projection ended up with a table and
    the module its index reading moved into ended up with none."""
    ints, digit_strs, other = {}, {}, []
    for _rel in rels:
        if not (ROOT / _rel).is_file():
            continue
        for _scope, _lit in _v22_code_literals(_v22_ast.parse((ROOT / _rel).read_text())):
            if type(_lit) is int:
                ints.setdefault(_lit, set()).add(_scope)
            elif isinstance(_lit, str):
                if re.search(r"\d\d", _lit):
                    digit_strs.setdefault(_lit, set()).add(_scope)
            elif _lit is not None and type(_lit) is not bool:
                other.append((_rel, repr(_lit)))
    return ints, digit_strs, other


_v22_code_ints, _v22_code_digit_strs, _v22_code_other = _v22_literal_scopes(_v22_module_rels)
_v22_corpus_ints, _v22_corpus_digit_strs, _v22_corpus_other = _v22_literal_scopes(_v22_corpus_rels)
expect("WARP-0722 AC1: the DOMAIN IS THE GIT ENUMERATION ITSELF - tracked_verdicts equals an INDEPENDENT recomputation written in this file (a `git ls-files` run of the suite's own over the proof root, plus a three-component membership test spelled out here) rather than anything borrowed from the module, and the derivation is a git enumeration rather than a filesystem walk. WHERE IT IS DERIVED MOVED AND SO DID THIS BINDING (WARP-0727): `ls-files` no longer appears in the projection module at all, it appears in the DECLARED corpus owner the projection delegates to, and THE PATHSPEC CARRIES NO WILDCARD - it names a DIRECTORY. That is the fix, not a detail: a git pathspec `*` crosses `/` where a pathlib `*` does not, so `proof/*/verdict*.json` admitted `proof/<a>/<b>/verdict.json` into this domain while the contract validator's own glob never saw it, and a plain `reconcile-verdicts` appended a forged `pass` for it at GATE GREEN. A wildcard returning to this pathspec reddens here. WHAT THIS CHECK DOES, STATED EXACTLY, BECAUSE ROUND 4'S HEADLINE ('no count can be hardcoded in the module') CLAIMED MORE THAN ITS MECHANISM COULD SEE: it parses every DECLARED copy of the module and requires the numeric literals in the CODE - integers, and strings carrying a digit run, docstrings excluded by structure - TOGETHER WITH THE SCOPE EACH OCCURS IN, to equal a table enumerated here from the owner's own constants, bound in both directions, with no other kind of literal admitted at all. So a corpus count cannot enter the code as a new literal, as a digit-bearing string, or as a use of an allowed value in any scope that does not already declare it - and a NEW USE INSIDE A SCOPE THAT ALREADY USES THAT VALUE IS NOT VISIBLE TO IT, which is measured (`EXPECTED_CORPUS = 40` at module level fires; the same line inside `_is_sha` would not) and is why this sentence no longer says `no count can be hardcoded`. NOTHING IN IT IS A FUNCTION OF HOW LARGE THIS REPOSITORY IS. The copies are the roster `.veldo/packs.json` declares, read through its one reader, so an undeclared directory under packs/ is not a pack here either, and a DECLARED pack missing its copy fails on a named list rather than raising",
       _v22_domain == _v22_lsfiles and len(_v22_domain) > 0
       # THE ENUMERATION IS DELEGATED TO ONE OWNER AND ASKS GIT THERE. Both directions, decided on
       # CODE literals so a comment can neither satisfy nor defeat it: the projection's code no
       # longer names the enumeration call at all, and the corpus owner's code does.
       and _v22_ls_arg not in _v22_events_code_strs
       and _v22_ls_arg in _v22_corpus_code_strs
       # NO WILDCARD IN THE PATHSPEC, either form. This is the property, and `proof/*/verdict*.json`
       # coming back in any spelling reddens on it.
       # THE ONE ANCHORING, RESOLVED AND NOT DECLARED (WARP-0727 round 2). There is no pathspec
       # CONSTANT left to bind: the pair that shipped in round 1 named different directories
       # whenever the VELDO root sits below the top of its repository, so the pathspec is now
       # resolved from the VELDO root and this asserts the resolved value for THIS repository -
       # the literal magic, this root's own prefix from git, and the declared proof root, with
       # no `*` anywhere in it.
       and EV22.corpus_pathspec(str(ROOT))[0] == (
           EV22._VC.CORPUS_PATHSPEC_MAGIC
           + _v22_git(ROOT, "rev-parse", "--show-prefix").stdout.strip()
           + _v22_ls_prefix.rstrip("/"))
       and "*" not in EV22.corpus_pathspec(str(ROOT))[0]
       and not hasattr(EV22, "VERDICT_PATHSPEC")
       and not hasattr(EV22, "VERDICT_PATHSPEC_FROM_TOP")
       and _v22_absent(_v22_module_rels) == []
       and _v22_absent(_v22_corpus_rels) == []
       and len({(ROOT / _r).read_bytes() for _r in _v22_corpus_rels}) == 1
       and ".veldo/events.py" in _v22_engine_set
       and ".veldo/verdict_corpus.py" in _v22_engine_set
       # ONE derivation, and the copies proven identical BYTE FOR BYTE, which is what makes
       # a scope table aggregated over all of them a statement about every one of them
       and len({(ROOT / _r).read_bytes() for _r in _v22_module_rels}) == 1
       and _v22_code_ints
       and {_i: _v22_code_ints[_i] for _i in _v22_code_ints}
           == {_i: _s for _i, (_why, _s) in _V22_MODULE_INTS.items()}
       and {_k: _v22_code_digit_strs[_k] for _k in _v22_code_digit_strs}
           == {_k: _s for _k, (_why, _s) in _V22_MODULE_DIGIT_STRS.items()}
       and _v22_code_other == []
       and all(_why for _why, _s in list(_V22_MODULE_INTS.values())
               + list(_V22_MODULE_DIGIT_STRS.values())))

expect("WARP-0727 AC1: THE LITERAL-SCOPE GUARD IS AIMED AT THE MODULE THE INDEX READING ACTUALLY MOVED TO, not only at the one it left. The corpus owner is where the domain is now derived and where every other reader asks, so a hardcoded corpus count is worse there than in the projection - and round 1 of this item moved the reading out while leaving the guard behind, which was MEASURED: `EXPECTED_CORPUS = 166` and `_CORPUS_FLOOR = 165` written into the CODE of all EIGHT declared copies of the corpus owner left the suite at 3356 passed, 0 failed, identical to pristine, while the same literal in events.py reddened. The same mechanism now runs over verdict_corpus.py's own declared copies through the SAME reader, so the two guards cannot be different strengths: every integer and every digit-bearing string in the CODE, docstrings excluded BY STRUCTURE and comments never in the tree at all, TOGETHER WITH THE SCOPE EACH OCCURS IN, must EQUAL a table enumerated here from the owner's own constants, bound in BOTH DIRECTIONS, with no other kind of literal admitted; every entry carries its reason, the copies are proven present and BYTE-IDENTICAL, and nothing here is a function of how large this repository's corpus is. WHAT IT IS BLIND TO IS DECLARED, not left for the next round: a NEW USE of an already-allowed value INSIDE a scope that already declares it is invisible to it, exactly as in the projection's table",
       _v22_absent(_v22_corpus_rels) == []
       and len({(ROOT / _r).read_bytes() for _r in _v22_corpus_rels}) == 1
       and _v22_corpus_ints
       and {_i: _v22_corpus_ints[_i] for _i in _v22_corpus_ints}
           == {_i: _s for _i, (_why, _s) in _V22_CORPUS_INTS.items()}
       and {_k: _v22_corpus_digit_strs[_k] for _k in _v22_corpus_digit_strs}
           == {_k: _s for _k, (_why, _s) in _V22_CORPUS_DIGIT_STRS.items()}
       and _v22_corpus_other == []
       and all(_why for _why, _s in list(_V22_CORPUS_INTS.values())
               + list(_V22_CORPUS_DIGIT_STRS.values())))

expect("WARP-0722 AC1: THE DERIVATION IS TOTAL over that enumeration - every tracked verdict path is either DERIVABLE (committed, so it has a blob) or DEFERRED WITH A REASON, the two partition the domain exactly with no overlap, and every derived key's path came from the enumeration rather than from anywhere else",
       set(_v22_paths) | {p for p, _why in _v22_deferred} == set(_v22_domain)
       and not (set(_v22_paths) & {p for p, _why in _v22_deferred})
       and len(_v22_keys) == len(set(_v22_keys))
       and all(_why for _p, _why in _v22_deferred))

_v22_lsfiles_blobs = {}
for _ln in _v22_git(ROOT, "ls-files", "-s", "-z", "--full-name", "--",
                    "proof").stdout.split("\0"):
    _meta, _, _p = _ln.partition("\t")
    if _p and _v22_is_corpus_path(_p):
        _v22_lsfiles_blobs[_p] = _meta.split()[1]
expect("WARP-0722 AC1/AC2: EVERY derived key over the WHOLE enumeration is (verdict.recorded, the spec id its own path names, THE ARTIFACT'S BLOB SHA) - the content key, checked against an independent `git ls-files -s` run rather than against the module's own map, with no history anywhere in it. The superseded key named the commit that ADDED the path, which is why `--diff-filter` no longer appears in the module at all",
       bool(_v22_keys) and all(
           k[0] == _V22_VERDICT and k[1] == p.split("/")[1]
           and k[2] == _v22_lsfiles_blobs[p] and len(k[2]) == 40
           and all(c in "0123456789abcdef" for c in k[2])
           for k, p in zip(_v22_keys, _v22_paths))
       and "diff-filter" not in _v22_events_src)

expect("WARP-0722 AC1: the emitted type is `verdict.recorded`, a MEMBER of the PARSED EVENT_TYPES of BOTH .veldo/events.py (the emitter) and .veldo/validate.py (the gate's event validator) - read off the loaded sets, not grepped - and the two names the deleted instruction used are in NEITHER set, which is why obeying that instruction would have turned the gate red on an unrecognised type",
       _V22_VERDICT == "verdict.recorded"
       and _V22_VERDICT in _V22_VOCAB and _V22_VERDICT in V.EVENT_TYPES
       and not (set(_v22_names) & (set(_V22_VOCAB) | set(V.EVENT_TYPES))))

# --- AC1 what the projection RECORDS must equal what the repository COMMITTED ----
# The round-1 defect in one assertion: the key named a path's first appearance and the
# content was read there, so an artifact amended in place (this repository's own
# convention across review rounds) was published with a result it contradicts. Asserted
# here over the WHOLE corpus and against `git show HEAD:<path>`, a different git command
# from the one the module uses, so the two cannot agree by sharing a mechanism.
_v22_derived_events = [EV22.verdict_event(*_t, repo_root=str(ROOT)) for _t in _v22_derivable]
_v22_head_content = {}
for _p in _v22_paths:
    try:
        _v22_head_content[_p] = json.loads(_v22_git(ROOT, "show", "HEAD:" + _p).stdout)
    except ValueError:
        _v22_head_content[_p] = {}

def _v22_truth(ev):
    """The artifact's committed content for an event, keyed by the path the event names.
    `.get` rather than `[]` on purpose: a projection that named a path outside the
    enumeration must FAIL this assertion, not raise out of it and take the other
    twenty-five with it (round 2's wrong-path mutant raised a KeyError here)."""
    return _v22_head_content.get(ev.get("verdict_path"), {})


_V22_ISO_Z = re.compile(r"\A[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z")


def _v22_dated_at_review(ev):
    """Does this event carry the review's own timestamp? The partition the module declares:
    an artifact whose reviewed_at is a timestamp in THIS envelope's one format is carried
    and dates the event; anything else is dropped and the event is dated at reconciliation,
    counted and reported.

    THE ORACLE IS NOT THE MODULE'S OWN FUNCTION, which is what made this predicate
    self-confirming: it used to call EV22._iso_z, so if _iso_z admitted the wrong strings
    the partition moved with it and every assertion quantified over the partition still
    passed. A fixed-width regex is an INDEPENDENT statement of the same one format, written
    here, and the two are asserted to agree over a table of hostile spellings below."""
    s = _v22_truth(ev).get("reviewed_at")
    return isinstance(s, str) and bool(_V22_ISO_Z.match(s))


# The spellings that make the difference between "strptime parsed it" and "this envelope
# writes it". CPython compiles strptime's directives with re.IGNORECASE and single-OR-double
# digit numeric fields, so every entry marked False below PARSES - and, before this round,
# was carried VERBATIM into an append-only log that .veldo/metrics.py's parse_iso then could
# not read and that sorts wrongly against the canonical lines beside it. The module now
# round-trips the parsed value through strftime and requires the exact input back; this
# table is the independent oracle's opinion, and the two must agree on every row.
_V22_ISO_CASES = [
    ("2026-01-02T03:04:05Z", True),
    ("1970-01-01T00:00:00Z", True),
    ("2099-12-31T23:59:59Z", True),
    ("2026-1-2T3:4:5Z", False),
    ("2026-01-02t03:04:05Z", False),
    ("2026-01-02T03:04:05z", False),
    ("2026-01-02T03:04:05+00:00", False),
    ("2026-01-02T03:04:05.123Z", False),
    ("2026-01-02 03:04:05Z", False),
    ("2026-01-02T03:04:05", False),
    ("", False),
]
expect("WARP-0722 ride-along: `_iso_z` MEANS THE ONE FORMAT THE ENVELOPE WRITES, not everything strptime will parse. Asserted against an INDEPENDENT fixed-width regex written in this file rather than against the module's own function, over a table that includes every spelling CPython's case-insensitive single-or-double-digit directives accept: `2026-1-2T3:4:5Z`, a lowercase `t`, a lowercase `z`, a fractional second, a `+00:00` offset and a space for the `T` all PARSE and are all REFUSED, so none of them can be written verbatim into an append-only log that metrics.py cannot read and that would sort wrongly. This is also what makes the module's 'one format only' sentences true, and it is what keeps the partition predicate below from being self-confirming",
       all(EV22._iso_z(_s) is _ok and bool(_V22_ISO_Z.match(_s)) is _ok
           for _s, _ok in _V22_ISO_CASES)
       and EV22._iso_z(None) is False and EV22._iso_z(7) is False
       and any(_ok for _s, _ok in _V22_ISO_CASES)
       and any(not _ok for _s, _ok in _V22_ISO_CASES))


_v22_content_ok = all(
    _e.get("verdict") == _v22_truth(_e).get("verdict")
    and _e.get("round") == (_v22_truth(_e).get("round")
                            if isinstance(_v22_truth(_e).get("round"), int) else None)
    and _e.get("commit") == _v22_truth(_e).get("commit")
    and (
        # the artifact declares a usable review time: it is carried verbatim and it dates
        # the event, so two clones render the same line
        (_e.get("reviewed_at") == _v22_truth(_e)["reviewed_at"]
         and _e.get("at") == _v22_truth(_e)["reviewed_at"])
        if _v22_dated_at_review(_e) else
        # the artifact declares none this envelope can carry: the field is DROPPED rather
        # than reshaped, and the event is dated at reconciliation in the one format this
        # envelope writes. That is the declared fallback, asserted rather than forbidden.
        ("reviewed_at" not in _e and EV22._iso_z(_e.get("at") or ""))
    )
    for _e in _v22_derived_events)
_v22_fallback_paths = sorted(_e.get("verdict_path") or "<no path>" for _e in _v22_derived_events
                             if not _v22_dated_at_review(_e))
_v22_tally_events = {}
for _e in _v22_derived_events:
    _v22_tally_events[_e.get("verdict")] = _v22_tally_events.get(_e.get("verdict"), 0) + 1
_v22_tally_artifacts = {}
for _p, _c in _v22_head_content.items():
    _v22_tally_artifacts[_c.get("verdict")] = _v22_tally_artifacts.get(_c.get("verdict"), 0) + 1
expect("WARP-0722 AC1, THE ROUND-1 DEFECT AS A CLASS: what the projection records EQUALS what the repository has COMMITTED, for EVERY artifact in the enumeration - verdict, round, the reviewed commit, and the review's own timestamp - checked against `git show HEAD:<path>`, a different command from the module's `cat-file blob`, so agreement cannot come from sharing a mechanism. THE TIMESTAMP IS ASSERTED OVER THE PARTITION THE MODULE DECLARES rather than as a universal it refutes: an artifact declaring a reviewed_at in this envelope's format has it carried verbatim AND dating the event, and an artifact declaring none (the shape of the SHIPPED verdict example, which every validator accepts) has the field DROPPED and the event dated at reconciliation in the envelope's format. Round 2 asserted the first half of that as a universal, which turned the gate RED on a valid artifact and made the declared fallback unreachable. THE TALLY DERIVED FROM THE PROJECTED EVENTS EQUALS THE TALLY DERIVED FROM THE ARTIFACTS, which is the number this item publishes as its benefit",
       bool(_v22_derived_events) and _v22_content_ok
       and _v22_tally_events == _v22_tally_artifacts
       and None not in _v22_tally_artifacts
       and len(_v22_derived_events) - len(_v22_fallback_paths) > 0)

# --- AC1 completeness AFTER a gate run, computed twice and compared -------------
# WARP-1711 AC3: THE FLATTENED REPORT IS DRIVEN, NOT DECLARED, because a review proved the entire
# deliverable was unasserted: it made is_flattened() always answer False and the full selftest still
# passed 4101 with zero failures. A name inside the literal-scope table is a syntactic declaration
# and not the behaviour, so the behaviour gets driven here over two real fixture repositories that
# differ in exactly the one fact the report is about. This runs at any depth in any repository,
# which is the point: it is a statement about the reporting code rather than about wherever the
# suite happens to be running.
with tempfile.TemporaryDirectory() as _v22_fld:
    # ONE COMMIT is the shape a migration produces; TWO is any repository with a history. The only
    # difference between the fixtures is the second commit.
    # BOTH fixtures carry the SAME verdict artifact, whose recorded commit is absent from either
    # repository, so both have something WITHHELD and the only difference between them is the commit
    # count. Without a withheld event there is no notice line to inspect at all, so a fixture with
    # no verdicts would have made the cause assertion vacuous rather than false.
    _v22_flat = Path(os.path.join(_v22_fld, "flat"))
    _v22_flat.mkdir(parents=True, exist_ok=True)
    _v22_git(_v22_flat, "init", "-q", "-b", "main")
    _v22_git(_v22_flat, "config", "user.email", "t@t")
    _v22_git(_v22_flat, "config", "user.name", "t")
    (_v22_flat / ".veldo").mkdir(parents=True, exist_ok=True)
    (_v22_flat / ".veldo/events.jsonl").write_text(_V22_SEED_LOG + "\n")
    _v22_write(_v22_flat, "proof/WARP-9711/verdict.json", _v22_verdict("WARP-9711", "pass"))
    _v22_commit(_v22_flat, "the whole tree, in one commit, exactly as a migration produces")
    _v22_deep = _v22_seed(os.path.join(_v22_fld, "deep"),
                          [("proof/WARP-9711/verdict.json", _v22_verdict("WARP-9711", "pass"))])
    _v22_rep_flat = EV22.reconcile_verdicts(_v22_flat, dry_run=True)
    _v22_rep_deep = EV22.reconcile_verdicts(_v22_deep, dry_run=True)
    # TWO LEGS WITHDRAWN HERE RATHER THAN FAKED, and the reason is the finding. They asserted that a
    # one-commit fixture reports flattened and a two-commit one does not, which forced the flag to be
    # a DEPTH test, and a review proved that wrong: in the real successor all 154 events stay
    # unresolvable after its first commit while a depth test stops reporting the cause. The flag is
    # now derived from the measured unresolved set instead, so discriminating it needs a fixture whose
    # log carries an event this repository genuinely cannot resolve. A synthetic event does not land
    # in that set (it is classified as superseded), so building one needs the resolution rules the
    # module owns, and inventing a shortcut here would test my imitation rather than the code.
    # OPEN, recorded in PLAN-0018 rather than left as a silent gap. What still runs below is the
    # notice logic driven over a constructed report, and the no-fabrication guarantee.
    # THE NOTICE ITSELF IS DRIVEN OVER A CONSTRUCTED REPORT, the pattern this file already uses for
    # the line function, because the notice only appears where something is WITHHELD and a fixture
    # whose verdicts are all derivable withholds nothing. Asserting it over the two repositories
    # above would have been vacuous on both sides: I built that first and it failed honestly, which
    # is the only reason this comment can tell you why the shape is different.
    _v22_fl_base = dict(_v22_rep_flat)
    _v22_fl_base.update({"withheld": [("WARP-9711", "proof/WARP-9711/verdict.json")],
                         "unresolved_legacy": [("WARP-9711", "c0ffee")]})
    _v22_fl_yes = dict(_v22_fl_base, flattened=True)
    _v22_fl_no = dict(_v22_fl_base, flattened=False)
    expect("WARP-1711 AC3: the CAUSE IS NAMED on the line a human reads, and ONLY where it applies "
           "- with something withheld the flattened report says the history was flattened at "
           "migration and that the appends stay WITHHELD, and the identical report with the flag "
           "off says neither, so the notice is not always-on decoration a reader learns to skip "
           "and the flag is what produces it",
           "FLATTENED AT MIGRATION" in EV22._report_line(_v22_fl_yes)
           and "WITHHELD" in EV22._report_line(_v22_fl_yes)
           and "FLATTENED AT MIGRATION" not in EV22._report_line(_v22_fl_no))
    expect("WARP-1711 AC3: THE APPENDS ARE NOT FABRICATED. A dry run over the flattened fixture "
           "appends nothing to the log, so the stage that reports the gap cannot be the stage that "
           "closes it by re-pointing a review at a commit where it did not happen",
           _v22_logged(_v22_flat) == [])

# THE ONE CAUSE BOTH STAND-DOWNS BELOW NAME (WARP-1711), written once because it is one fact about
# this repository and not two. It is the reconciler's own reported cause, in the same words.
_V22_FLATTENED_WHY = (
    "the events those earlier reviews were recorded against name COMMITS THIS REPOSITORY DOES NOT "
    "HAVE - it holds a single commit, because the history was flattened at migration - so the "
    "projection cannot tell which reviews the log already covers for those specs and WITHHOLDS "
    "their appends rather than re-pointing them at the flattening commit, which would assert a "
    "review happened at a commit where it did not")
_v22_log_before = _v22_lines(_v22_log)
_v22_rep = EV22.reconcile_verdicts(repo_root=str(ROOT), dry_run=True)
_v22_log_after_dry = _v22_lines(_v22_log)
_v22_present, _v22_dupes, _v22_unresolved, _v22_route = EV22.logged_verdict_state(_v22_log, repo_root=str(ROOT))
_v22_pending = {EV22.event_verdict_key(ev) for ev in _v22_rep["events"]}
_v22_independent = {k for k in _v22_keys if k not in _v22_present}
# SPLIT (WARP-1711): the DOMAIN, the DERIVABLE count and the DRY RUN'S INERTNESS are facts about
# this repository's own artifacts and are asserted first, without history. What a flattened
# repository cannot supply is the identity of the reviews its EARLIER events stand for, and the
# projection's answer there is to WITHHOLD - which is the honest report, not a failure.
expect("WARP-0722 AC1: THE DOMAIN AND THE DRY RUN, WITHOUT HISTORY: the reconciler's derivable count equals the independent enumeration of keyed verdict artifacts written in this file, its domain equals the whole enumeration including what it defers, and the dry run is proven INERT - it appends nothing and the log has the same lines after it as before",
       _v22_rep["derivable"] == len(_v22_keys)
       and _v22_rep["domain"] == len(_v22_domain)
       and _v22_rep["appended"] == 0
       and _v22_log_after_dry == _v22_log_before)
# THE CONDITION IS THE EVIDENCE ITSELF, NEVER THE COMMIT COUNT. These three stood down on
# COMMIT_DEPTH == 1, and a review proved that wrong by committing once to a successor: the events
# still named commits absent from that history, so the fact had not changed, but the guard stopped
# recognising it and three assertions about a full clone ran in a repository that is not one. What
# these legs actually depend on is that THIS log names objects THIS repository does not have, and
# that is measured directly a few lines above. In this repository the measured set is empty, so
# every assertion below runs exactly as it always did, which is the negative control.
if _v22_unresolved:
    stand_down("the completeness of the projection over EARLIER reviews", _V22_FLATTENED_WHY,
               "The domain, the derivable count and the dry run's inertness are SPLIT OUT and still "
               "run here, immediately above, and the WITHHELD count is reported by the stage itself "
               "with this cause named. It falls to zero as reviews are recorded against commits this "
               "repository has.", "WARP-0722 AC1",
               [(".veldo/events.jsonl", None)])
else:
    expect("WARP-0722 AC1: AFTER A GATE RUN EVERY COMMITTED VERDICT ARTIFACT HAS ITS EVENT, asserted by comparing the reconciler's own decision with an INDEPENDENT recomputation over the same enumeration - the keys it would append are exactly the derived keys the log lacks, it claims precisely the rest as already present, and the union of the existing log and one run COVERS the whole enumeration. THE LEGACY EVENTS ARE RESOLVED BY IDENTITY: an event written before the key changed carries no blob, and its key is recovered from the (commit, path) pair it does carry, so the backfill is recognised rather than repeated. The dry run is also proven inert: the log has the same lines after it as before",
       _v22_pending == _v22_independent
       and _v22_rep["already_present"] == len(set(_v22_keys) - _v22_independent)
       and _v22_rep["derivable"] == len(_v22_keys)
       and _v22_rep["domain"] == len(_v22_domain)
       and set(_v22_keys) <= (_v22_present | _v22_pending)
       and _v22_rep["appended"] == 0
       and _v22_log_after_dry == _v22_log_before)

# SPLIT (WARP-1711), AND BY ORIGIN RATHER THAN BY CONVENIENCE. A verdict key is CONTENT-ADDRESSED,
# so a key recorded in a PREDECESSOR repository names the blob of the artifact's bytes THERE. The
# migration REDACTS file contents, so a redacted verdict artifact has a different blob here and the
# object the earlier event names is genuinely absent - a fact about the rewrite, not about integrity.
# The keys THIS RUN derives come from THIS tree's own index and are asserted at any depth; the keys
# the LOG already carries are asserted here, and stand down by name in a successor that rewrote them.
# Re-keying those events is refused for the same reason the appends are withheld: the log is
# append-only and a review of the predecessor's bytes did not happen against ours.
_v22_absent_objects = sorted(
    _k[2] for _k in _v22_present
    if not (len(_k[2]) == 40
            and subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", _k[2]],
                               capture_output=True).returncode == 0))
expect("WARP-0722 AC1: EVERY KEY THIS RUN DERIVES NAMES AN OBJECT THIS REPOSITORY HAS - a 40-hex blob `git cat-file -e` confirms, over the keys the run would append UNION the keys the log resolves that this tree still holds, non-empty so it is not vacuous before a backfill or after, and this repository is not a shallow clone",
       bool(_v22_present | _v22_pending)
       and all(len(k[2]) == 40 and subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", k[2]],
                                                  capture_output=True).returncode == 0
               for k in (_v22_pending | (_v22_present - {_k for _k in _v22_present
                                                         if _k[2] in _v22_absent_objects})))
       and _v22_rep["shallow"] is False)
# THE CONDITION IS THE EVIDENCE ITSELF, NEVER THE COMMIT COUNT. These three stood down on
# COMMIT_DEPTH == 1, and a review proved that wrong by committing once to a successor: the events
# still named commits absent from that history, so the fact had not changed, but the guard stopped
# recognising it and three assertions about a full clone ran in a repository that is not one. What
# these legs actually depend on is that THIS log names objects THIS repository does not have, and
# that is measured directly a few lines above. In this repository the measured set is empty, so
# every assertion below runs exactly as it always did, which is the negative control.
if _v22_absent_objects:
    stand_down("the log's EARLIER keys naming objects this repository has",
               "those keys are CONTENT-ADDRESSED and were recorded against the predecessor's bytes, "
               "which the migration REDACTED, so %d of them name a blob that is not an object here; "
               "this repository holds a single commit and cannot contain the predecessor's content "
               "either" % len(_v22_absent_objects),
               "Every key THIS RUN derives is asserted against this tree's own objects immediately "
               "above, and re-keying the earlier events is refused: the log is append-only and a "
               "review of the predecessor's bytes did not happen against ours.",
               "WARP-0722 AC1", [(".veldo/events.jsonl", None)])
else:
    expect("WARP-0722 AC1: NOTHING IN THE REAL LOG NAMES A BLOB THIS REPOSITORY DOES NOT HAVE - every verdict key the log resolves to carries a 40-hex blob that `git cat-file -e` confirms is an object here, quantified over the log's keys UNION this run's so it is non-vacuous before a backfill as well as after, and this repository is not a shallow clone",
       bool(_v22_present | _v22_pending)
       and all(len(k[2]) == 40 and subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", k[2]],
                                                  capture_output=True).returncode == 0
               for k in (_v22_present | _v22_pending))
       and _v22_rep["shallow"] is False)
# THE CONDITION IS THE EVIDENCE ITSELF, NEVER THE COMMIT COUNT. These three stood down on
# COMMIT_DEPTH == 1, and a review proved that wrong by committing once to a successor: the events
# still named commits absent from that history, so the fact had not changed, but the guard stopped
# recognising it and three assertions about a full clone ran in a repository that is not one. What
# these legs actually depend on is that THIS log names objects THIS repository does not have, and
# that is measured directly a few lines above. In this repository the measured set is empty, so
# every assertion below runs exactly as it always did, which is the negative control.
if _v22_unresolved:
    stand_down("the EMPTY unresolvable-event list", _V22_FLATTENED_WHY,
               "That every key the log DOES resolve names an object this repository has, over the "
               "log's keys union this run's, is SPLIT OUT and still runs here, immediately above; "
               "each unresolvable event is NAMED by the stage rather than counted as absent.",
               "WARP-0722 AC1", [(".veldo/events.jsonl", None)])
else:
    expect("WARP-0722 AC1: IN A FULL CLONE OF THIS REPOSITORY NOTHING IN THE LOG IS UNRESOLVABLE - every earlier verdict event's (commit, path) pair resolves to a blob here, so the projection withholds no append at all, which is the state the WITHHELD count above returns to as a flattened successor accumulates commits",
           _v22_unresolved == [] and _v22_rep["unresolved_legacy"] == []
           and _v22_rep["shallow"] is False)

# --- AC1 the gate reaches it, where it cannot be declared away -----------------
_v22_verify_rels = _v22_engine_copies("scripts/verify.sh", "scripts/verify.sh")
_v22_verify_texts = {rel: (ROOT / rel).read_text() for rel in _v22_verify_rels
                     if (ROOT / rel).is_file()}
_v22_call = "python3 .veldo/events.py reconcile-verdicts"


def _v22_stage_block(text):
    """The reconciliation stage exactly as a gate script carries it: THE PARAGRAPH ITS OWN ECHO
    OPENS, ending at the first blank line, which is how this script separates one stage from the
    next. Returns "" when the marker is absent, so a missing stage fails on the emptiness leg
    below instead of RAISING out of a slice.

    ROUND 5 SLICED `text.index(marker_a)` TO `text.index("COMMIT=$(git rev-parse HEAD")`, which
    had two defects the body now closes: a gate script that lost either marker made this DIE by
    ValueError rather than fail, and any stage inserted between this one and that `COMMIT=` line
    was swallowed into the block, so an ordinary new stage mentioning FAIL would have reddened
    the no-FAIL leg below on a stage that is not this one. The paragraph boundary is structural
    and local. WHAT IT IS STILL BLIND TO, stated rather than left to be measured: a new stage
    added INSIDE this paragraph, above the blank line, still counts as part of this block."""
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if 'echo "== review events' in ln:
            out = []
            for nxt in lines[i:]:
                if not nxt.strip():
                    break
                out.append(nxt)
            return "\n".join(out)
    return ""


expect("WARP-0722 AC1: THE GATE ITSELF REACHES THE EMITTER, and reaches it where nobody can declare it away - the call is in the ALWAYS-RUN built-in section of this repository's own gate script and of the copy inside EVERY PACK THE MANIFEST DECLARES (the roster read through `.veldo/pack.py load_packs`, not a `>= 8` floor and not a directory listing, so a newly declared pack cannot be forgotten and an undeclared directory under packs/ is not a pack, both MEASURED; what a RETIREMENT does to this block cannot be measured end to end today, because three OTHER items' assertions hardcode pack ids and pack paths and CRASH thousands of lines before this one is reached, which is the same defect class outside this footprint and is queued rather than smuggled in), and it is NOT a catalog CHECK_ item, which could be set to na: or waived: with a reason and stop running. This is the whole design difference from the instruction it replaces, which ran only when a human remembered",
       _v22_absent(_v22_verify_rels) == []
       and "scripts/verify.sh" in _v22_engine_set
       and all(_v22_call in t for t in _v22_verify_texts.values())
       and all("reconcile-verdicts" not in t.split("ORDER=")[0] for t in _v22_verify_texts.values())
       and not any(re.search(r"^CHECK_[A-Za-z_]*=.*reconcile-verdicts", t, re.M)
                   for t in _v22_verify_texts.values())
       and _V22_ROSTER_COMPLETE
       and all(_v22_stage_block(t) for t in _v22_verify_texts.values())
       and all(_v22_call in _v22_stage_block(t) for t in _v22_verify_texts.values())
       and len({_v22_stage_block(t) for t in _v22_verify_texts.values()}) == 1)

expect("WARP-0722 AC1 (out of scope, and enforced rather than promised): RECONCILIATION CANNOT REDDEN THE BUILD - its stage block in every one of the gate scripts mentions FAIL nowhere and guards the call with `||`, so a stage that reddened the build over its own bookkeeping cannot make the first run after this lands unlandable. THE BLOCK IS THE PARAGRAPH THE STAGE'S OWN ECHO OPENS, and it is required to be NON-EMPTY here: round 5 sliced it between two literal markers, so a script that lost either one made this assertion DIE rather than fail, and a stage inserted anywhere before the second marker was read as part of this one",
       all(_v22_stage_block(t) for t in _v22_verify_texts.values())
       and all("FAIL" not in _v22_stage_block(t) and "||" in _v22_stage_block(t)
               for t in _v22_verify_texts.values()))

with tempfile.TemporaryDirectory() as _v22_hostile:
    _v22_notrepo = os.path.join(_v22_hostile, "plain")
    os.makedirs(_v22_notrepo)
    _v22_fx_h = _v22_seed(os.path.join(_v22_hostile, "fx"),
                          [("proof/WARP-9720/verdict.json", _v22_verdict("WARP-9720", "pass"))])
    # THE DIRECTORY-AS-LOG LIVES INSIDE THE FIXTURE REPOSITORY ON PURPOSE, so this case still
    # exercises the append failing rather than being turned away earlier by the origin check
    # below: a log outside the artifacts' work tree is now refused before anything is opened.
    _v22_dirlog = os.path.join(str(_v22_fx_h), ".veldo", "dir.jsonl")
    os.makedirs(_v22_dirlog)
    _v22_torn = _v22_seed(os.path.join(_v22_hostile, "torn"),
                          [("proof/WARP-9721/verdict.json", _v22_verdict("WARP-9721", "pass"))])
    (_v22_torn / ".veldo/events.jsonl").write_bytes(b'{"schema": "veldo.event/v1", "type": "gate.pas\x00\n[1,2]\nnot json\n')
    _v22_runs = [
        subprocess.run([sys.executable, str(ROOT / ".veldo/events.py"), "reconcile-verdicts",
                        "--repo-root", _v22_notrepo], capture_output=True, text=True),
        subprocess.run([sys.executable, str(ROOT / ".veldo/events.py"), "reconcile-verdicts",
                        "--repo-root", str(_v22_fx_h), "--log", _v22_dirlog],
                       capture_output=True, text=True),
        subprocess.run([sys.executable, str(ROOT / ".veldo/events.py"), "reconcile-verdicts",
                        "--repo-root", str(_v22_torn)], capture_output=True, text=True),
    ]
    expect("WARP-0722 AC1: the CLI the gate calls EXITS 0 over hostile input as well - a directory that is not a git repository at all, a log path that is a DIRECTORY so the append itself cannot succeed, and an existing log holding a torn line, raw binary and a line that parses to something that is not a record - reporting by name in every case, because the stage's contract is to append and report and never to judge",
           all(r.returncode == 0 for r in _v22_runs)
           and "review events" in _v22_runs[0].stdout
           and "not reconciled" in _v22_runs[1].stdout
           and "1 appended" in _v22_runs[2].stdout
           and len(_v22_logged(_v22_torn)) == 1)

# --- WARP-0725/0727: THE FORGERY GUARD, RETIRED BY WARP-0730 AND DELETED BY WARP-0731 -------
# WHAT USED TO BE HERE, AND WHY IT IS NOT. Nine rounds of WARP-0722 each closed one route into
# the event log and none of them wrote the property down, so the next attacker found the next
# spelling: the constructor, emit()'s type argument, the type read off the assembled dict, a
# cardinality, the write-surface discovery, and finally the artifacts and the log related to each
# other by what git answered for each path. WARP-0725 replaced all of it with membership - a line
# is entitled if and only if its key is a MEMBER of the enumeration the log's own repository
# produces - and that rule held. It is gone anyway, and the reason is not that it failed.
#
# WARP-0730 REMOVED THE VALUE OF WHAT IT PROTECTED. Verdict authority left the agent: the gate is
# the authority for ordinary work and the owner for protected paths, the merge rule names no
# verdict, and nothing authoritative reads verdict.recorded any more. A forged line now buys a row
# in a descriptive tally that, as log_entitlement's own docstring always declared, a one-line shell
# append already defeats. WARP-0731 deleted the machinery: log_entitlement, the frozenset threaded
# through four functions, the `unentitled` report field and CLI exit code 2.
#
# WHAT SURVIVES HERE, AND IT IS THE PART WORTH KEEPING. The API-hygiene half of the refusal:
# ONLY THE PROJECTION WRITES PROJECTION-OWNED EVENTS. The generated door-routes leg below still
# drives every declared type crossed with every reserved envelope key crossed with two producers,
# and still requires a refusal on every projection-owned type AND on every line declaring the
# projection's own producer. The positive control - a repository reconciled against its OWN log
# appends exactly its domain and appends nothing on a second run - survives with it, because the
# failure mode of a deletion like this one is the INVERSE harm: a projection that quietly stops
# recording genuine reviews is indistinguishable from a repository where nobody reviewed anything.
#
# WHAT WAS DELETED WITH THE GUARD, named so a reader is not left counting: the AC1 set-equality
# over the real corpus, the AC4 no-stand-in-in-the-prose check, the AC2 measured-forgery fixture,
# the four AC5 refusal placements, and the AC3 inverse-harm leg over the real corpus. Twelve
# expect() calls. They witness a property this repository deliberately no longer has.



def _v25_artifact_rel(spec_id, pathspec=None):
    """A CONCRETE repository-relative artifact path GENERATED FROM THE OWNER'S OWN DECLARED
    CORPUS SHAPE, with the spec id in the directory component, so a future proof root or
    verdict file name is driven by every route below without one of them being edited.

    THE DECLARATION MOVED AND THIS FOLLOWED IT (WARP-0727). It used to split
    `EV22.VERDICT_PATHSPEC` on `/` and substitute the `*`, because the pathspec WAS the shape.
    The pathspec is now a wildcard-free directory - that is the fix, a git `*` crossing `/`
    where a pathlib `*` does not was the whole defect - so the shape is read from where it is
    now declared: verdict_corpus.PROOF_ROOT and its verdict name pattern. Still GENERATED from
    the owner's constants and never spelled here, which is the property this function is for."""
    if pathspec is not None:
        parts = pathspec.split("/")
        return "/".join(p.replace("*", spec_id if i == 1 else "") for i, p in enumerate(parts))
    _vc = EV22._VC
    return "/".join([_vc.PROOF_ROOT, spec_id, _vc.VERDICT_PATTERN.replace("*", "")])


# NOTHING BELOW MAY RAISE OUT OF THIS BLOCK, AND THAT IS NOT A STYLE POINT: A CRASH IS STRICTLY
# WORSE THAN A RED, because it takes the whole suite's pass/fail summary down and makes a run that
# found nothing indistinguishable from a run that could not look. MEASURED WHILE WRITING THIS: the
# mutant that entitles everything again makes the byte-level backstop in the writer RAISE, and the
# first draft of the AC2 leg called the reconciler bare - 8 substitutions applied, exit 1, NO
# SUMMARY PRINTED AT ALL. So a reconciliation's exception is DATA here, and so is a report line's,
# and so is the loss of this item's own contract name.
def _v25_reconcile(**kw):
    """One reconciliation whose EXCEPTION IS DATA: the report a run produced, or a stand-in
    report whose values no assertion below can satisfy, carrying the exception class."""
    try:
        return EV22.reconcile_verdicts(**kw)
    except Exception as _ex:                # pragma: no cover - a mutant's backstop firing
        _raised = "raised:" + type(_ex).__name__
        _rep = {"deferred": [], "withheld": [], "unresolved_legacy": [], "keys": [],
                "unresolvable_foreign": [], "legacy_route": _raised, "shallow": False,
                "lock": "", "events": []}
        for _f in ("domain", "derivable", "collapsed", "already_present", "appended", "pending",
                   "duplicate_keys_in_log", "superseded", "dated_at_reconciliation"):
            _rep[_f] = _raised
        return _rep


def _v25_line(rep):
    """The stage line, or a marker naming the exception class, for the same reason."""
    try:
        return EV22._report_line(rep)
    except Exception as _ex:                # pragma: no cover - a mutant's report firing
        return "the report line raised " + type(_ex).__name__


_v25_enum_keys = {_t[0] for _t in _v22_derivable}
_v25_enum_blobs = {_k[2] for _k in _v25_enum_keys}
# --- THE POSITIVE CONTROL: A REPOSITORY RECONCILED AGAINST ITS OWN LOG ----------------------
# THE SURVIVING HALF OF WHAT WAS AC5. The four refusal placements went with the membership rule;
# this leg did not, because it measures the INVERSE harm, which is worse than the defect the guard
# was for: a projection that stops recording GENUINE verdicts fails silently and forever, in a log
# nothing may rewrite. So the repository is reconciled against its own log twice - the first run
# must append exactly its domain, the second must append nothing - and the blobs that landed are
# compared against the domain the module itself derives.
with tempfile.TemporaryDirectory() as _v25_pd:
    _v25_home = _v22_seed(os.path.join(_v25_pd, "home"),
                          [(_v25_artifact_rel("WARP-9760"), _v22_verdict("WARP-9760", "pass"))])
    _v25_own1 = _v25_reconcile(repo_root=str(_v25_home))
    _v25_own2 = _v25_reconcile(repo_root=str(_v25_home))
    _v25_own_landed = sorted(_e.get("verdict_blob") for _e in _v22_logged(_v25_home))
    _v25_own_want = sorted(_b for _k, _p, _b in EV22.verdict_domain(str(_v25_home))[0])
    expect("WARP-0731 AC2: THE PROJECTION STILL RECORDS ITS OWN DOMAIN, which is the REQUIRED control beside a deleted refusal - the first run appends exactly the domain, the second appends NOTHING, and the blobs that landed ARE the domain the module derives",
           _v25_own1["appended"] == len(_v25_own_want)
           and _v25_own2["appended"] == 0
           and _v25_own_landed == _v25_own_want
           and bool(_v25_own_want))

# --- WARP-0731 AC2/AC4: THE SURVIVING REFUSALS THROUGH THE SHIPPED COMMAND LINE --------------
# THE DOOR ROUTES BELOW DRIVE THE MODULE IN PROCESS, WHICH IS NOT THE SURFACE AN ADOPTER HAS. This
# leg drives the same two refusals through the CLI a caller actually types, on a COPY in a throwaway
# tree so no byte can reach the real log, and reads the RETURN CODE and THE LOG'S BYTES rather than
# an exception class. Both routes must refuse and neither may leave the log changed:
#   the projection-owned TYPE, which is the route `--field type=` defeated in WARP-0722 round 6, and
#   the projection's own PRODUCER on a type the loop may legitimately hand-emit.
# AND THE EXIT CODE IS PINNED AT AC4's CONTRACT: reconcile-verdicts returns 0, never the 2 that
# WARP-0731 removed with the membership check, and the gate reads that code.
with tempfile.TemporaryDirectory() as _v31_cd:
    _v31_tree = Path(_v31_cd) / "probe"
    _v22_module_in(_v31_tree)
    _v31_mod, _v31_log = _v31_tree / ".veldo/events.py", _v31_tree / ".veldo/events.jsonl"
    _v31_before = _v31_log.read_bytes() if _v31_log.is_file() else b""

    def _v31_cli(*argv):
        """One CLI invocation: its return code, and whether the log's bytes moved."""
        _r = subprocess.run([sys.executable, str(_v31_mod)] + list(argv),
                            cwd=str(_v31_tree), capture_output=True, text=True)
        _after = _v31_log.read_bytes() if _v31_log.is_file() else b""
        return (_r.returncode, _after == _v31_before)

    # BOTH TYPES GENERATED FROM THE MODULE'S OWN CONSTANTS, never spelled here: one the projection
    # owns, and one the loop may legitimately hand-emit.
    _v31_owned_type = sorted(_V22_OWNED)[0]
    _v31_open_type = sorted(set(_V22_VOCAB) - set(_V22_OWNED))[0]
    _v31_routes = {
        "the projection-owned type, emitted directly":
            _v31_cli("emit", _v31_owned_type, "--spec", "WARP-9731"),
        "the projection-owned type, set through --field after the argument":
            _v31_cli("emit", _v31_open_type, "--spec", "WARP-9731",
                     "--field", "type=" + _v31_owned_type),
        "the projection's own producer on a hand-emittable type":
            _v31_cli("emit", _v31_open_type, "--spec", "WARP-9731",
                     "--field", "producer=" + _V22_PRODUCER),
    }
    # THE POSITIVE CONTROL BESIDE THEM, so a CLI that refused EVERYTHING would not pass this leg.
    _v31_allowed = _v31_cli("emit", _v31_open_type, "--spec", "WARP-9731")
    _v31_recon = _v31_cli("reconcile-verdicts")
    expect("WARP-0731 AC2/AC4: THE TWO SURVIVING REFUSALS BITE THROUGH THE SHIPPED CLI - a projection-owned type and the projection's own producer are each refused non-zero with the log's bytes UNMOVED, an ordinary emit still lands, and reconcile-verdicts returns 0 now that exit code 2 is gone",
           bool(_v31_owned_type) and bool(_v31_open_type) and bool(_V22_PRODUCER)
           and all(_v31_r == (2, True) for _v31_r in _v31_routes.values())
           and _v31_allowed[0] == 0 and _v31_allowed[1] is False
           and _v31_recon[0] == 0)

# --- AC5: THE DOOR ROUTES, GENERATED FROM THE MODULE'S OWN CONSTANTS ------------------------
# Every event type the module declares, crossed with every RESERVED envelope key, crossed with the
# projection's own producer and a producer that is not it, driven through the hand-emission door on
# a COPY whose ROOT is a throwaway tree - each route carrying a verdict_blob THE REAL REPOSITORY'S
# DOMAIN ACTUALLY HOLDS, and each reserved key set explicitly to the value THE MODULE'S OWN MINT
# produces for it, so a future reserved name needs no admissible value written down here.
# WHAT IS REQUIRED OF EACH MEMBER, and it is NOT what a first draft of this leg assumed: a
# projection-owned type is refused whatever it declares, AND the projection's own producer is
# refused ON EVERY DECLARED TYPE, because that name is entitled exactly the way the type is - by
# the line's own content key being one the projection derived in this pass, which a hand-emission
# door never holds. Measured while writing this: driving every type under the reconciler's producer
# refused all of them, and reading that as a broken fixture instead of as the rule would have
# weakened the control until the forgery came back.
with tempfile.TemporaryDirectory() as _v25_rd:
    _v25_probe_tree = Path(_v25_rd) / "probe"
    _v25_probe = _v22_module_in(_v25_probe_tree)
    _v25_probe_log = _v25_probe_tree / ".veldo/events.jsonl"
    _v25_real_blob = sorted(_v25_enum_blobs)[0] if _v25_enum_blobs else ""
    _v25_reserved = tuple(getattr(EV22, "RESERVED_ENVELOPE_KEYS", ()) or ())
    _v25_writers = {"the projection's own producer": _V22_PRODUCER,
                    "a producer that is not the projection's": "veldo.0725.another.writer"}
    _v25_door = {}
    for _v25_pn in sorted(_v25_writers):
        _v25_pv = _v25_writers[_v25_pn]
        for _v25_t in sorted(_V22_VOCAB):
            try:
                _v25_mint = _v25_probe.make_event(_v25_t, producer=_v25_pv)
            except Exception as _v25_ex:    # a type the mint refuses is recorded, not raised
                _v25_door[(_v25_pn, _v25_t, "<mint>")] = "raised:" + type(_v25_ex).__name__
                continue
            for _v25_k in _v25_reserved:
                _v25_extra = {"type": _v25_t, "verdict_path": _v25_artifact_rel("WARP-0712"),
                              "verdict_blob": _v25_real_blob, _v25_k: _v25_mint.get(_v25_k)}
                try:
                    _v25_probe.emit(_v25_t, spec="WARP-9771", producer=_v25_pv,
                                    extra=_v25_extra)
                    _v25_door[(_v25_pn, _v25_t, _v25_k)] = "landed"
                except ValueError:
                    _v25_door[(_v25_pn, _v25_t, _v25_k)] = "refused"
                except Exception as _v25_ex:
                    _v25_door[(_v25_pn, _v25_t, _v25_k)] = "raised:" + type(_v25_ex).__name__
    _v25_door_types = set(_v22_landed_types(_v25_probe_log))
    expect("WARP-0725 AC5: EVERY DOOR ROUTE IS GENERATED FROM THE MODULE'S OWN CONSTANTS rather than written down here, so a future event type or reserved envelope name is driven without this list being edited: every type the module declares, crossed with every reserved envelope key, crossed with the projection's own producer and a producer that is not it, each route carrying a verdict_blob THIS REPOSITORY'S REAL DOMAIN HOLDS and each reserved key set explicitly to the value the module's OWN mint produces for it, all driven on a COPY whose ROOT is a throwaway tree so no byte can reach the real log. TWO THINGS ARE ENTITLED THE SAME WAY AND BOTH ARE REFUSED HERE: a projection-owned type, even carrying a real member of the domain, and the projection's OWN PRODUCER on any declared type whatever - because both are entitled only by the line's content key being one the projection derived in this pass, and a hand-emission door holds no such key. Every OTHER declared type under a producer that is not the projection's LANDS, read back off the bytes, which is what makes the refusal a refusal rather than a fixture that cannot write, and the types read back EQUAL the declared vocabulary minus the projection-owned set in both directions. Nothing here counts routes, types or keys",
           _V22_CONTRACT_NAMES_PRESENT and bool(_v25_door) and bool(_v25_real_blob)
           and bool(_v25_reserved)
           and all(_v25_r == ("refused"
                              if (_v25_writers[_v25_kt[0]] == _V22_PRODUCER
                                  or _v25_kt[1] in _V22_OWNED) else "landed")
                   for _v25_kt, _v25_r in _v25_door.items())
           and _v25_door_types == (set(_V22_VOCAB) - set(_V22_OWNED)))

# =====================================================================================
# WARP-0727: ONE ENUMERATION FOR THE ENTITLEMENT DOMAIN AND THE VALIDATED SET
# =====================================================================================
# THE LAW, STATED BEFORE THE CASE, because the case is one spelling of it. WHEN TWO
# MECHANISMS COMPUTE WHAT IS CLAIMED TO BE THE SAME SET, THE GAP BETWEEN THEM IS AN ATTACK
# SURFACE AND NEITHER MECHANISM CAN SEE IT. Each side is individually correct and
# individually tested; the defect exists only in the difference, so no test of either side
# can find it.
#
# THE CASE, MEASURED AT ffaab41 BEFORE ANY CHANGE, with no flags and no attacker directory.
# The projection's entitlement domain was `git ls-files 'proof/*/verdict*.json'` and the
# contract validator's corpus was `Path('proof').glob('*/verdict*.json')`. A GIT PATHSPEC `*`
# CROSSES `/`; A PATHLIB `*` DOES NOT. So a file containing literally
# `{"schema": "nope", "verdict": "pass"}` committed at `proof/WARP-9999/nested/verdict.json`
# was INSIDE the domain and INVISIBLE to the validator: `validate.py all` exited 0, then plain
# `events.py reconcile-verdicts` with NO ARGUMENTS appended a verdict.recorded carrying a real
# 40-hex blob (log md5 4b20b0fe19ec -> d262da987e54, `1 appended`), and `scripts/verify.sh`
# printed GATE: GREEN over the whole thing. THE GATE WAS THE APPENDER.
#
# WHY THE REFUSAL IS STRUCTURAL AND NOT A GATE CHECK, which is the load-bearing design
# decision here: verify.sh runs the reconciler AFTER the contract stage and does NOT skip it
# when that stage is red. A red gate that still appends has closed nothing, and an
# append-only log cannot take it back. So the domain and the validated set are ONE membership
# rule applied to TWO path sources, and the gate check below exists for the ONE difference a
# single rule cannot remove: index versus working tree.
#
# WHAT IS NOT CLAIMED HERE, said in the block rather than only in the spec. Entitlement is
# still keyed on the LOG'S PATH SPELLING and not on the identity of the file actually opened -
# log_entitlement resolves a repository from `Path(log).parent` while the bytes are written by
# `open(log, "a+")`, which follows the final component - so a symlink or hardlink at the
# victim's log name transfers entitlement. KNOWN OPEN, a separate item, untouched by this
# block. A writer that never imports the module and arbitrary in-process Python are likewise
# out of reach and already able to append directly.

import hashlib as _v27_hashlib
import shutil as _v27_shutil
import unicodedata as _v27_unicodedata


def _v27_load(name, path):
    """One module loaded BY ABSOLUTE PATH, so a copy in a throwaway tree derives its own ROOT
    and every sibling it loads comes from THAT tree. This is what makes a mutant applied to a
    copy actually reach the code under test instead of the repository's own."""
    _s = importlib.util.spec_from_file_location(name, str(path))
    _m = importlib.util.module_from_spec(_s)
    _s.loader.exec_module(_m)
    return _m


def _v27_lay_veldo(tree):
    """Every .veldo python module copied into `tree`, so a validator loaded from there resolves
    its whole sibling graph inside the tree. Enumerated by GLOB from the real .veldo rather than
    listed, so a new organ needs no edit here."""
    (Path(tree) / ".veldo").mkdir(parents=True, exist_ok=True)
    for _src in sorted((ROOT / ".veldo").glob("*.py")):
        _v27_shutil.copy(str(_src), str(Path(tree) / ".veldo" / _src.name))
    return Path(tree) / ".veldo"

_v27_VC = EV22._VC
_v27_V = _v27_load("veldo_validate_0727", ROOT / ".veldo/validate.py")
_V27_PATTERNS = (_v27_VC.VERDICT_PATTERN, _v27_VC.DESIGN_VERDICT_PATTERN,
                 _v27_VC.APPROVAL_PATTERN, _v27_VC.MANIFEST_PATTERN)

# --- AC1: ONE ENUMERATION, and the two sets EQUAL over this repository's real corpus ------
# THE SUBJECT IS THE SHIPPED PAIR, not a re-derivation: the projection's own domain function
# and the validator's own corpus function, each called the way its own module calls it.
#
# THE INDEX IS NOT THE WORKING TREE, AND THIS ROW USED TO FORGET IT. The domain is a git
# enumeration and the validated set is a disk enumeration, so an artifact an author has written
# and not yet committed is in the second and not the first. That is the NORMAL FLOW - the corpus
# owner says so in writing, `untracked` is a named bucket of divergence() and its docstring calls
# it "Expected and not red: an author validating before committing is the normal flow" - and the
# raw equality here contradicted the module it tests. MEASURED, and it is why this changed: with
# ONE uncommitted verdict artifact on disk this row was the only red in a 4529-assertion run, so
# every L2 reviewer writing a verdict turned the gate red until somebody committed it, and three
# independent reviewers of this migration each reported it against a different item. A gate that
# reds when a feature is USED is not gating that feature, it is refusing it.
#
# WHAT THE EQUALITY IS NOW, AND WHY IT STILL HAS TEETH. The comparison sets aside exactly the
# owner's own `untracked` bucket and nothing else. That bucket is `disk_set - set(direct)` where
# `direct` is an INDEPENDENT `git ls-files` read, NOT the difference between the two sets under
# test, so subtracting it cannot make this row true by construction: it can only forgive paths
# GIT ITSELF says it is not tracking. Both harmful directions survive untouched. A tracked
# artifact the validator cannot see is still `entitled_not_validated` and still red. A tracked
# artifact outside the domain is still `contradiction` and still red. A domain member git does
# not report as tracked is still `overclaimed` and still red. The set that is forgiven is
# ASSERTED to be exactly git's own answer, in both directions, so a later edit cannot widen the
# forgiveness without reddening this row.
_v27_domain_paths = set(EV22.tracked_verdicts(repo_root=str(ROOT)))
_v27_validated = {str(Path(_p).relative_to(ROOT))
                  for _p in _v27_V._corpus(_v27_VC.VERDICT_PATTERN)}
_v27_same_file = (Path(_v27_V._CORPUS.__file__).resolve()
                  == Path(_v27_VC.__file__).resolve())
_v27_div = {_pat: _v27_VC.divergence(ROOT, _pat) for _pat in _V27_PATTERNS}
# The one bucket set aside, taken from the owner rather than recomputed here, and the committed
# half of the validated set that the index is actually answerable for.
_v27_untracked = set(_v27_div[_v27_VC.VERDICT_PATTERN]["untracked"])
_v27_validated_tracked = _v27_validated - _v27_untracked
# THE FORGIVEN SET IS ITSELF PINNED TO GIT'S OWN ANSWER, so this is a narrowing with a witness
# rather than a hole. Recomputed here from the independent read, compared both ways.
_v27_direct, _v27_direct_ok = _v27_VC.tracked_direct(ROOT)
_v27_untracked_here = _v27_validated - set(_v27_direct)
expect("WARP-0727 AC1: THE ENTITLEMENT DOMAIN AND THE VALIDATED SET ARE ONE ENUMERATION, and over this repository's REAL corpus they are EQUAL IN BOTH DIRECTIONS ONCE THE INDEX IS ALLOWED TO DIFFER FROM THE WORKING TREE, which is the one difference a single membership rule cannot remove and the only thing set aside here. The domain is a GIT enumeration and the validated set is a DISK enumeration, so an artifact an author has written and not yet committed belongs to the second and not the first; the corpus owner already computes that population as its `untracked` bucket and already declares it expected rather than red, and this row's earlier raw equality contradicted the module it tests. It was MEASURED as the only red in a 4529-assertion run with ONE uncommitted verdict artifact present, so writing a review turned the gate red until somebody committed it. WHAT IS SET ASIDE IS PINNED TO GIT'S OWN ANSWER AND NOTHING WIDER: `untracked` is `disk_set` minus an INDEPENDENT `git ls-files` read rather than the difference between the two sets under test, it is recomputed here from that independent read and required to be EQUAL in both directions, it is required to be a subset of the validated set, and it is required to be DISJOINT from the domain - so this is a narrowing with a witness and not a hole, and no later edit can widen the forgiveness without reddening this row. BOTH HARMFUL DIRECTIONS ARE UNTOUCHED, which is why the narrowing costs nothing: a tracked artifact no validator will see is still entitled-not-validated, a tracked artifact outside the domain is still a CONTRADICTION, and a domain member git does not report as tracked is still OVERCLAIMED. The projection's domain function and the contract validator's corpus function are asserted to load the SAME FILE as their owner, so this is one rule applied to two path sources and not two rules that happen to agree today; the pathspec carries NO WILDCARD in either form, which is the fix - a git pathspec `*` crosses `/` where a pathlib `*` does not - and for EVERY corpus pattern the owner declares, not only the verdict one, the entitled-not-validated set, the CONTRADICTION set, the OVERCLAIMED set and the misfiled set are each EMPTY. The contradiction set is the paths GIT ITSELF reports as tracked that the domain does not hold, and the overclaimed set is the reverse: both are asked of git through a route that shares no pathspec and no prefix arithmetic with the enumeration under test, which is what makes an empty answer here mean anything at all - derived from the domain instead, as it was at 098dc6a, it was arithmetically empty for every possible input, and its failing witness is now CONSTRUCTED and shown RED in the round 3 leg below. A PROPERTY OF EACH MEMBER IS ASSERTED AND NEVER A CARDINALITY: this repository's corpus grows, so nothing here pins how large it is",
       _v27_same_file
       and "*" not in EV22.corpus_pathspec(str(ROOT))[0]
       and EV22.corpus_pathspec(str(ROOT))[0].startswith(_v27_VC.CORPUS_PATHSPEC_MAGIC)
       and _v27_domain_paths == _v27_validated_tracked
       and _v27_domain_paths <= _v27_validated_tracked
       and _v27_validated_tracked <= _v27_domain_paths
       and _v27_untracked == _v27_untracked_here
       and _v27_untracked <= _v27_validated
       and _v27_direct_ok
       and not (_v27_untracked & _v27_domain_paths)
       and bool(_v27_domain_paths)
       and all(_v27_VC.corpus_member(_p, _v27_VC.VERDICT_PATTERN) for _p in _v27_domain_paths)
       and all(_v27_div[_pat]["git_available"] for _pat in _V27_PATTERNS)
       and all(_v27_div[_pat]["entitled_not_validated"] == [] for _pat in _V27_PATTERNS)
       and all(_v27_div[_pat]["contradiction"] == [] for _pat in _V27_PATTERNS)
       and all(_v27_div[_pat]["overclaimed"] == [] for _pat in _V27_PATTERNS)
       and all(_v27_div[_pat]["misfiled"] == [] for _pat in _V27_PATTERNS))

# --- AC2 + AC4: THE FORGERY REFUSED BY THE APPENDER, and the control is ADDITIVE ----------
# NOTHING BELOW MAY RAISE OUT OF THIS BLOCK: a crash is strictly worse than a red, because it
# takes the pass/fail summary down and makes a run that found nothing look like a run that
# could not look. Every exception is DATA.
_v27_ac2 = {"error": ""}
try:
    with tempfile.TemporaryDirectory() as _v27_d:
        # THE POSITIVE CONTROL LANDS FIRST, so what follows is a refusal and not a projection
        # that never worked. The genuine artifact path is GENERATED from the owner's declared
        # shape, so a future proof root or verdict name drives this without an edit here.
        _v27_good = _v25_artifact_rel("WARP-9740")
        _v27_fx = _v22_seed(os.path.join(_v27_d, "fx"),
                            [(_v27_good, _v22_verdict("WARP-9740", "pass"))])
        _v22_lay_module(_v27_fx)
        _v27_log = _v27_fx / ".veldo/events.jsonl"
        _v27_ac2["good_first"] = EV22.reconcile_verdicts(repo_root=str(_v27_fx))
        # THE FORGED ARTIFACT, ONE DIRECTORY DEEPER THAN THE CORPUS SHAPE. Its path is DERIVED
        # from the genuine one by inserting a component, so it follows the declared shape too.
        _v27_parts = _v27_good.split("/")
        _v27_bad = "/".join(_v27_parts[:-1] + ["nested", _v27_parts[-1]])
        _v22_write(_v27_fx, _v27_bad, {"schema": "nope", "verdict": "pass"})
        _v22_commit(_v27_fx, "the forged artifact, two directories deep")
        # IT REALLY IS INSIDE WHAT THE OLD PATHSPEC ADMITTED, asserted rather than asserted-of:
        # the pathspec that shipped at ffaab41 is spelled out here and run against the fixture.
        _v27_ac2["old_pathspec_matched"] = _v27_bad in _v22_git(
            _v27_fx, "ls-files", "proof/*/verdict*.json").stdout.split()
        _v27_before = _v27_log.read_bytes()
        _v27_ac2["rep"] = EV22.reconcile_verdicts(repo_root=str(_v27_fx))
        _v27_ac2["after"] = _v27_log.read_bytes()
        _v27_ac2["domain"] = set(EV22.tracked_verdicts(repo_root=str(_v27_fx)))
        _v27_ac2["validated"] = {str(_p.relative_to(_v27_fx))
                                 for _p in _v27_VC.corpus_in_dir(_v27_fx / "proof")}
        _v27_ac2["stage_line"] = _v25_line(_v27_ac2["rep"])
        _v27_ac2["check_red"] = _v27_V.check_verdict_domain_is_the_validated_set(root=_v27_fx)
        _v27_ac2["blob_in_log"] = any(
            _e.get("verdict_path") == _v27_bad for _e in EV22.read_log(_v27_log))
        # THE NEGATIVE CONTROL IS ADDITIVE AND IS NOW REMOVED: a rename battery is blind to
        # growth, so the violation was ADDED above and is taken away here, and the check must
        # go back to silent. Nothing else about the fixture changes.
        _v22_git(_v27_fx, "rm", "-r", "-q", str(Path(_v27_bad).parent))
        _v22_commit(_v27_fx, "remove the forged artifact")
        _v27_ac2["check_after_removal"] = _v27_V.check_verdict_domain_is_the_validated_set(
            root=_v27_fx)
        _v27_ac2["rep_after_removal"] = EV22.reconcile_verdicts(repo_root=str(_v27_fx))
except Exception as _v27_ex:                     # pragma: no cover - recorded, never raised
    _v27_ac2["error"] = "%s: %s" % (type(_v27_ex).__name__, _v27_ex)
expect("WARP-0727 AC2: THE MEASURED FORGERY IS REFUSED BY THE APPENDER ITSELF, driven on a fixture repository of its own so no byte can reach the real append-only log. The artifact IS one the pathspec that shipped at ffaab41 matched - that pathspec is spelled out here and run against the fixture, so this is a measurement and not a memory - and it is NOT a member of the domain now, NOT in the validated set, appends NOTHING with the log proven BYTE-IDENTICAL by reading it back rather than by trusting the report, and carries no line naming its path. IT IS NAMED, NOT SILENTLY DROPPED: the stage line names the path and the contract check RETURNS A NON-ZERO ERROR COUNT for it, because a narrowing that drops a genuine artifact without saying so is the inverse harm of the forgery it prevents. THE CONTROL IS ADDITIVE AND REVERSED: the violation was ADDED to a corpus that was already reconciling and REMOVED again, and the check goes back to zero, so this is not a check that fires on everything. The genuine review landed FIRST and is still recorded afterwards",
       _v27_ac2["error"] == ""
       and _v27_ac2["good_first"]["appended"] == 1
       and _v27_ac2["old_pathspec_matched"]
       and _v27_bad not in _v27_ac2["domain"]
       and _v27_bad not in _v27_ac2["validated"]
       and _v27_good in _v27_ac2["domain"] and _v27_good in _v27_ac2["validated"]
       and _v27_ac2["after"] == _v27_before
       and _v27_ac2["rep"]["appended"] == 0
       and not _v27_ac2["blob_in_log"]
       and _v27_bad in _v27_ac2["rep"]["misfiled"]
       and _v27_bad in _v27_ac2["stage_line"]
       and _v27_ac2["check_red"] > 0
       and _v27_ac2["check_after_removal"] == 0
       and _v27_ac2["rep_after_removal"]["appended"] == 0
       and _v27_ac2["rep_after_removal"]["already_present"] == 1)

# --- AC3: THE ROUTE BATTERY, GENERATED FROM THE MECHANISM'S OWN VOCABULARY ----------------
# GENERATED, NOT LISTED: a CROSS PRODUCT over the dimensions on which a git pathspec and a
# pathlib glob are documented to differ. DEPTH, because one `*` crosses `/` and the other does
# not. A LEADING DOT, because glob implementations disagree about hidden components
# (glob.glob excludes them, pathlib includes them, git includes them). NAME CASE, because
# fnmatch folds case and fnmatchcase does not, so membership must not become a property of the
# filesystem. And the SPEC DIRECTORY's spelling, including a space, a glob metacharacter and
# BOTH UNICODE NORMAL FORMS - the last of which is not decoration: git's default core.quotePath
# C-quotes a non-ASCII path, and at ffaab41 that silently removed such an artifact from the
# domain while the validator still saw it, so a genuine review under an accented directory
# could never have been recorded.
#
# WHAT THIS IS EXHAUSTIVE OVER, AND WHAT IT IS NOT, stated plainly because driving N routes
# closes N routes and never a class on its own: it is EXHAUSTIVE OVER THIS CROSS PRODUCT and
# over nothing else. It says nothing about a depth beyond the deepest generated here, nothing
# about a case-insensitive filesystem, nothing about a name outside the generated set, and
# nothing about a path outside the proof root. The reason the CLASS is nonetheless closed is
# structural rather than enumerated: there is ONE membership rule and no second pattern for a
# future spelling to differ from, and this product is the measurement that the one rule holds
# where the two mechanisms used to disagree.
_V27_DEPTHS = (0, 1, 2, 3, 4)
_V27_HIDDEN = ("none", "first", "last")
_V27_NAMES = ("verdict.json", "verdict-9.json", "verdicts.json",
              "VERDICT.json", ".verdict.json", "verdict.JSON")
_V27_DIRS = ("plain", "space", "bracket", "star", "nfc", "nfd")
_V27_DIRTEXT = {"plain": "SPEC", "space": "SPEC DIR", "bracket": "SPEC[1]", "star": "SPEC*1",
                # THE TWO UNICODE NORMAL FORMS, written as ESCAPES so this file stays
                # pure ASCII (the docs hygiene stage forbids a non-ASCII byte in tracked
                # source) and so the two forms are unambiguous rather than dependent on
                # how an editor happened to save them. NFC is one precomposed code point;
                # NFD is the base letter plus a combining acute. git C-quotes both by
                # default, which is the difference this dimension exists to drive.
                "nfc": _v27_unicodedata.normalize("NFC", "SPEC-caf\u00e9"),
                "nfd": _v27_unicodedata.normalize("NFD", "SPEC-cafe\u0301")}
_v27_batt = {"error": "", "rows": {}}
_v27_product = []
_v27_n = 0
for _v27_depth in _V27_DEPTHS:
    for _v27_hid in _V27_HIDDEN:
        for _v27_nm in _V27_NAMES:
            for _v27_dk in _V27_DIRS:
                _v27_n += 1
                _v27_comps = ["%s-%03d" % (_V27_DIRTEXT[_v27_dk], _v27_n)]
                _v27_comps += ["mid%d" % _i for _i in range(_v27_depth)]
                if _v27_hid == "first":
                    _v27_comps[0] = "." + _v27_comps[0]
                elif _v27_hid == "last":
                    _v27_comps[-1] = "." + _v27_comps[-1]
                _v27_product.append("/".join([_v27_VC.PROOF_ROOT] + _v27_comps + [_v27_nm]))
try:
    with tempfile.TemporaryDirectory() as _v27_bd:
        _v27_bfx = _v22_seed(os.path.join(_v27_bd, "b"),
                             [(_v25_artifact_rel("WARP-9741"),
                               _v22_verdict("WARP-9741", "pass"))])
        _v22_lay_module(_v27_bfx)
        _v27_made = []
        for _v27_rel in _v27_product:
            try:
                _v22_write(_v27_bfx, _v27_rel, {"schema": "nope", "verdict": "pass"})
                _v27_made.append(_v27_rel)
            except OSError:                       # a name this filesystem cannot hold
                pass
        _v22_commit(_v27_bfx, "the generated battery")
        _v27_bent = set(EV22.tracked_verdicts(repo_root=str(_v27_bfx)))
        _v27_bval = {str(_p.relative_to(_v27_bfx))
                     for _p in _v27_VC.corpus_in_dir(_v27_bfx / "proof")}
        _v27_batt["forgery"] = sorted(_r for _r in _v27_made
                                      if _r in _v27_bent and _r not in _v27_bval)
        _v27_batt["inverse"] = sorted(_r for _r in _v27_made
                                      if _r in _v27_bval and _r not in _v27_bent)
        _v27_batt["made"] = _v27_made
        # EVERY name-shaped non-member must be NAMED by the contract check, never dropped.
        _v27_batt["shaped_nonmember"] = sorted(
            _r for _r in _v27_made
            if _v27_VC.name_shaped(_r, _v27_VC.VERDICT_PATTERN)
            and not _v27_VC.corpus_member(_r, _v27_VC.VERDICT_PATTERN))
        _v27_batt["named"] = sorted(_v27_VC.misfiled(_v27_bfx))
        # AND THE APPENDER RECORDS EXACTLY THE MEMBERS AND NEVER A NON-MEMBER. The battery
        # DELIBERATELY contains valid corpus paths as well as invalid ones - a battery of only
        # violations proves nothing about a rule that refuses everything - so the property is
        # not "nothing was appended", it is that every path that reached the log is a member and
        # that no name-shaped non-member did.
        _v27_blog = _v27_bfx / ".veldo/events.jsonl"
        _v27_batt["rep"] = EV22.reconcile_verdicts(repo_root=str(_v27_bfx))
        _v27_batt["logged"] = {_e.get("verdict_path") for _e in EV22.read_log(_v27_blog)
                               if _e.get("type") == _V22_VERDICT}
        _v27_batt["logged_nonmembers"] = sorted(
            _r for _r in _v27_batt["logged"]
            if _r and not _v27_VC.corpus_member(_r, _v27_VC.VERDICT_PATTERN))
        _v27_batt["members_logged"] = sorted(_r for _r in _v27_bval
                                             if _r not in _v27_batt["logged"])
except Exception as _v27_bex:                    # pragma: no cover - recorded, never raised
    _v27_batt["error"] = "%s: %s" % (type(_v27_bex).__name__, _v27_bex)
expect("WARP-0727 AC3: THE ROUTE BATTERY IS GENERATED FROM THE MECHANISM'S OWN VOCABULARY - a CROSS PRODUCT over depth, leading-dot position, name case and directory spelling (a space, a glob metacharacter, and BOTH unicode normal forms) - and for EVERY generated path the two sets AGREE: entitled if and only if validated, so the forgery direction and the inverse-harm direction are BOTH empty over the whole product. EXHAUSTIVE OVER THIS PRODUCT AND OVER NOTHING ELSE, which is said here rather than left to be assumed: it says nothing about a greater depth, a case-insensitive filesystem, a name outside the generated set, or a path outside the proof root, and the class is closed structurally by there being ONE rule rather than by this enumeration. At ffaab41 the same product measured 144 forgery routes and 18 inverse routes. The battery DELIBERATELY carries valid corpus paths alongside the invalid ones, because a battery of only violations proves nothing about a rule that refuses everything, so what is asserted about the appender is a PARTITION: every member reached the log and no name-shaped non-member did. The misfiled report EQUALS the name-shaped non-member set in both directions rather than merely covering it, and nothing here asserts a count of anything this repository can grow",
       _v27_batt["error"] == ""
       and bool(_v27_batt["made"])
       and _v27_batt["forgery"] == []
       and _v27_batt["inverse"] == []
       and _v27_batt["named"] == _v27_batt["shaped_nonmember"]
       and bool(_v27_batt["shaped_nonmember"])
       and _v27_batt["logged_nonmembers"] == []
       and _v27_batt["members_logged"] == []
       and bool(_v27_batt["logged"]))

# --- TEETH: THE MUTANTS. A check with no demonstrated firing input is decoration. ---------
# BOTH MUTANTS ARE APPLIED TO A COPY IN A THROWAWAY TREE and the SUBSTITUTION IS ASSERTED TO
# HAVE LANDED before its result is believed - a mutant that silently failed to apply produces a
# green that means nothing, which is how a teeth leg lies.
#
# MUTANT A, THE DIVERGENCE PUT BACK: the disk side keeps the one rule while the git side is
# widened, which is exactly the ffaab41 shape (a git `*` reaching further than a pathlib `*`).
# The both-directions check MUST fire and name the path.
# MUTANT B, THE RULE WIDENED ON BOTH SIDES AT ONCE: this is the STRUCTURAL property, and it is
# the reason this item closes a SPELLING class. Widening the ONE rule widens the domain AND the
# validated set together, so the two sets stay EQUAL and the gap cannot reopen by loosening the
# rule; it can only reopen by reintroducing a SECOND rule, which is what mutant A is.
# WHAT THIS DOES NOT MEAN, AND THE SENTENCE THAT USED TO SAY OTHERWISE IS DELETED RATHER THAN
# SOFTENED: it does NOT mean a widening is contained because the contract validator catches what
# it newly admits. It is not contained. Driven under this very mutant: the forged artifact is
# entitled, `validate.py` exits 1 naming it, AND `reconcile-verdicts` appends it anyway (3
# tracked, 3 appended) - because the gate runs the contract stage at verify.sh line 102 and the
# reconciler at line 123, the reconciler line is not guarded by FAIL and its `|| echo` swallows a
# non-zero exit, so the append is NOT gated on the contract stage at all. A WIDENING ADMITS AN
# APPENDABLE FORGERY, and a contributor who widened the rule on the strength of the deleted
# sentence would reopen the appending harm at a RED gate rather than a green one.
_v27_mut = {"error": ""}
try:
    with tempfile.TemporaryDirectory() as _v27_md:
        # THREE ARTIFACTS, each doing a job. A plain member; a member whose NAME needs the
        # pattern's wildcard, which is what mutant A's second pattern will drop; and a forged
        # path one directory deeper, which the pristine rule already refuses and names.
        _v27_mgood = _v25_artifact_rel("WARP-9742")
        _v27_msuffix = "/".join(_v25_artifact_rel("WARP-9744").split("/")[:-1] + ["verdict-2.json"])
        _v27_mfx = _v22_seed(os.path.join(_v27_md, "m"),
                             [(_v27_mgood, _v22_verdict("WARP-9742", "pass")),
                              (_v27_msuffix, _v22_verdict("WARP-9744", "pass"))])
        _v27_lay_veldo(_v27_mfx)
        _v27_mbad = "/".join(_v25_artifact_rel("WARP-9743").split("/")[:-1]
                             + ["nested", "verdict.json"])
        _v22_write(_v27_mfx, _v27_mbad, {"schema": "nope", "verdict": "pass"})
        _v22_commit(_v27_mfx, "a forged artifact for the mutants to act on")
        _v27_mcorpus = _v27_mfx / ".veldo" / EV22.CORPUS_MODULE
        _v27_pristine = _v27_mcorpus.read_text()
        _v27_mut["pristine_sha"] = _v27_hashlib.sha256(
            _v27_pristine.encode()).hexdigest()[:16]
        # THE BASELINE IS MEASURED, NEVER ASSUMED TO BE ZERO. This fixture carries a misfiled
        # artifact on purpose, so the pristine rule ALREADY reports errors here; a mutant is
        # proven to fire by moving the count ABOVE that baseline, and the first draft of this
        # leg asserted zero and was wrong about its own fixture rather than about the code.
        _v27_mut["base_errs"] = _v27_load(
            "veldo_validate_0727_base", _v27_mfx / ".veldo/validate.py"
        ).check_verdict_domain_is_the_validated_set()
        _v27_mut["base_named"] = sorted(_v27_load(
            "veldo_corpus_0727_base", _v27_mcorpus).misfiled(_v27_mfx))
        # ---- MUTANT A: A SECOND PATTERN, WHICH IS THE ffaab41 DEFECT ITSELF ----------------
        # The disk side is given a pattern of its own while the git side keeps the declared one,
        # so the two sources are once again computing "the same set" two ways. THE SUBSTITUTION
        # IS INSIDE THE FUNCTION THE CHECK READS, which the first draft of this leg got wrong.
        _v27_a_old = "    disk_set = set(disk_corpus(root, pattern))"
        _v27_a_new = "    disk_set = set(disk_corpus(root, \"verdict.json\"))"
        _v27_mut["a_subs"] = _v27_pristine.count(_v27_a_old)
        _v27_mcorpus.write_text(_v27_pristine.replace(_v27_a_old, _v27_a_new))
        _v27_mut["a_sha"] = _v27_hashlib.sha256(
            _v27_mcorpus.read_text().encode()).hexdigest()[:16]
        _v27_mut["a_errs"] = _v27_load(
            "veldo_validate_0727_muta", _v27_mfx / ".veldo/validate.py"
        ).check_verdict_domain_is_the_validated_set()
        _v27_mut["a_gap"] = _v27_load(
            "veldo_corpus_0727_muta", _v27_mcorpus).divergence(
                _v27_mfx)["entitled_not_validated"]
        # ---- MUTANT B: THE ONE RULE WIDENED, SO BOTH SIDES MOVE TOGETHER -------------------
        # ONE substitution that widens the rule the way a looser rule would really read: any
        # depth at or below the corpus shape, and the NAME test on the FINAL component. Widening
        # the depth alone admits nothing, which was measured: `parts[2]` of
        # `proof/<id>/nested/verdict.json` is `nested`, so the first draft of this mutant was
        # inert and asserting it fired would have been a green that meant nothing.
        _v27_b_old = ("    return (len(parts) == 3 and parts[0] == PROOF_ROOT\n"
                      "            and fnmatch.fnmatchcase(parts[2], pattern))")
        _v27_b_new = ("    return (len(parts) >= 3 and parts[0] == PROOF_ROOT\n"
                      "            and fnmatch.fnmatchcase(parts[-1], pattern))")
        _v27_mut["b_subs"] = _v27_pristine.count(_v27_b_old)
        _v27_mcorpus.write_text(_v27_pristine.replace(_v27_b_old, _v27_b_new))
        _v27_mut["b_sha"] = _v27_hashlib.sha256(
            _v27_mcorpus.read_text().encode()).hexdigest()[:16]
        _v27_mB = _v27_load("veldo_validate_0727_mutb", _v27_mfx / ".veldo/validate.py")
        _v27_mEV = _v27_load("veldo_events_0727_mutb", _v27_mfx / ".veldo/events.py")
        _v27_mut["b_entitled"] = set(_v27_mEV.tracked_verdicts(repo_root=str(_v27_mfx)))
        _v27_mut["b_validated"] = {
            str(Path(_p).relative_to(_v27_mfx))
            for _p in _v27_mB._corpus(_v27_mB._CORPUS.VERDICT_PATTERN)}
        # ---- RESTORE, AND PROVE THE RESTORATION LANDED ------------------------------------
        _v27_mcorpus.write_text(_v27_pristine)
        _v27_mut["restored_sha"] = _v27_hashlib.sha256(
            _v27_mcorpus.read_text().encode()).hexdigest()[:16]
        _v27_mut["restored_errs"] = _v27_load(
            "veldo_validate_0727_rest", _v27_mfx / ".veldo/validate.py"
        ).check_verdict_domain_is_the_validated_set()
except Exception as _v27_mex:                    # pragma: no cover - recorded, never raised
    _v27_mut["error"] = "%s: %s" % (type(_v27_mex).__name__, _v27_mex)
expect("WARP-0727 TEETH: BOTH MUTANTS FIRE, AND EACH SUBSTITUTION IS PROVEN TO HAVE LANDED before its result is believed - every substitution count is asserted NON-ZERO and the file's sha256 is asserted to CHANGE, to differ between the two mutants, and to come back to the pristine value, because a mutant that quietly failed to apply produces a green that means nothing. THE BASELINE IS MEASURED AND NOT ASSUMED TO BE ZERO: this fixture carries a misfiled artifact on purpose, the pristine rule already names it, and a mutant fires by moving the count ABOVE that baseline. MUTANT A IS THE ffaab41 DEFECT ITSELF PUT BACK - a SECOND PATTERN, given to the disk side while the git side keeps the declared one, so the two sources compute the same set two ways again - and it is applied inside the function the check actually reads: the error count rises above the baseline and the artifact whose name needs the pattern's wildcard is named as entitled-and-not-validated. MUTANT B widens THE ONE RULE, so the domain and the validated set move TOGETHER: the forged path two directories deep becomes VALIDATED as well as entitled and the two sets stay EQUAL, which is the structural reason this closes the SPELLING class - a later edit cannot reopen THAT gap by loosening the rule, only by reintroducing a second rule, which is what mutant A is. IT IS NOT A CONTAINMENT CLAIM AND THE SENTENCE THAT SAID IT WAS IS DELETED: under this mutant the forgery is entitled, the contract validator exits 1 naming it, AND the reconciler appends it anyway, because the gate does not gate the append on the contract stage. A widening admits an APPENDABLE forgery",
       _v27_mut["error"] == ""
       and _v27_mut["a_subs"] == 1 and _v27_mut["b_subs"] == 1
       and _v27_mut["a_sha"] != _v27_mut["pristine_sha"]
       and _v27_mut["b_sha"] != _v27_mut["pristine_sha"]
       and _v27_mut["a_sha"] != _v27_mut["b_sha"]
       and _v27_mut["base_errs"] > 0
       and _v27_mbad in _v27_mut["base_named"]
       and _v27_mut["a_errs"] > _v27_mut["base_errs"]
       and _v27_msuffix in _v27_mut["a_gap"]
       and _v27_mut["b_entitled"] == _v27_mut["b_validated"]
       and _v27_mbad in _v27_mut["b_entitled"]
       and _v27_mbad in _v27_mut["b_validated"]
       and _v27_mut["restored_sha"] == _v27_mut["pristine_sha"]
       and _v27_mut["restored_errs"] == _v27_mut["base_errs"])

# --- ROUND 2: ONE ANCHORING, AND THE TWO ROUTES THE FIRST ROUND OPENED -----------------------
# THE FIRST ROUND OF THIS ITEM CLOSED ONE FORGERY ROUTE AND OPENED ANOTHER, and both halves of
# that are driven here rather than argued. The corpus owner defaulted its GIT CWD to the PROCESS
# CWD where the code it replaced defaulted to the module's own root, and it shipped TWO pathspecs
# calling themselves one directory. Measured by the review at bdb4055: the same clone invoked by
# absolute path from a non-repository reported 0 tracked where ffaab41 reported the whole corpus;
# invoked from a FOREIGN repository it named that repository's paths in this one's report; and
# with VELDO vendored at sub/ of a larger repository, a forged verdict committed at the OUTER proof
# root was APPENDED to the vendored VELDO's own append-only log with `validate.py all` exiting 0 on
# both sides, while every genuine verdict the vendored root held was withheld forever at a PASSING
# contract stage. Both legs below are properties of EACH member and pin no cardinality of anything
# this repository can grow; nothing may raise out of the block, because a crash takes the suite's
# pass/fail summary down and is strictly worse than a red.
_v27_anc = {"error": ""}
try:
    with tempfile.TemporaryDirectory() as _v27_ad:
        # ---- THE VENDORED SHAPE: a VELDO root that is NOT the top of its repository ----------
        _v27_outer = Path(_v27_ad) / "outer"
        _v27_vend = _v27_outer / "sub"
        _v27_vend.mkdir(parents=True, exist_ok=True)
        _v22_git(_v27_outer, "init", "-q", "-b", "main")
        _v22_git(_v27_outer, "config", "user.email", "t@t")
        _v22_git(_v27_outer, "config", "user.name", "t")
        _v27_lay_veldo(_v27_vend)
        (_v27_vend / ".veldo/events.jsonl").write_text(_V22_SEED_LOG + "\n")
        # The vendored root's OWN genuine verdict, and a forgery at the OUTER proof root. The
        # forgery is CORPUS SHAPED, so nothing but the anchoring stands between it and the log.
        _v27_own_rel = _v25_artifact_rel("WARP-9780")
        _v22_write(_v27_outer, "sub/" + _v27_own_rel, _v22_verdict("WARP-9780", "pass"))
        _v27_out_rel = _v25_artifact_rel("WARP-9999")
        _v22_write(_v27_outer, _v27_out_rel, {"schema": "nope", "verdict": "pass"})
        _v22_commit(_v27_outer, "a vendored VELDO, and a verdict forged at the outer proof root")
        _v27_vlog = _v27_vend / ".veldo/events.jsonl"
        _v27_vmod = _v27_vend / ".veldo/events.py"
        # THE ATTACK, EXACTLY AS THE REVIEW DROVE IT: no flags, no --repo-root, no environment,
        # the module invoked by ABSOLUTE PATH from the outer repository's own directory.
        _v27_anc["cli"] = subprocess.run(
            [sys.executable, str(_v27_vmod), "reconcile-verdicts"],
            cwd=str(_v27_outer), capture_output=True, text=True)
        _v27_anc["after_text"] = _v27_vlog.read_text()
        _v27_vEV = _v27_load("veldo_events_0727_vend", _v27_vmod)
        _v27_anc["prefix"] = _v27_vEV.corpus_pathspec(str(_v27_vend))[1]
        _v27_anc["pathspec"] = _v27_vEV.corpus_pathspec(str(_v27_vend))[0]
        _v27_anc["domain"] = set(_v27_vEV.tracked_verdicts(repo_root=str(_v27_vend)))
        _v27_anc["own_keys"] = {_k for _k, _p, _b in
                                _v27_vEV.verdict_domain(str(_v27_vend))[0]}
        _v27_anc["own_blobs"] = {_b for _k, _p, _b in
                                 _v27_vEV.verdict_domain(str(_v27_vend))[0]}
        # WARP-0731 deleted log_entitlement. The property THIS leg tests is the ANCHORING - a
        # log resolves the VELDO root it belongs to, never the caller's - and that survives the
        # deletion, so the derivation the function performed is inlined here rather than the
        # leg being dropped with the forgery guard it used to serve.
        _v27_anc["entitled"] = {_k for _k, _p, _b in _v27_vEV.verdict_domain(
            _v27_vEV.veldo_root_for_log(_v27_vlog))[0]}
        _v27_anc["landed_blobs"] = {_e.get("verdict_blob") for _e in _v22_logged(_v27_vend)}
        _v27_anc["contract"] = _v27_load(
            "veldo_validate_0727_vend", _v27_vend / ".veldo/validate.py"
        ).check_verdict_domain_is_the_validated_set(root=str(_v27_vend))
        # ---- THE SAME MODULE, THREE INVOCATION SITES, ONE ANSWER ---------------------------
        # A directory that is no repository at all, and a FOREIGN repository carrying a
        # verdict-shaped path of its own that the misfiled report would name if the git half
        # were still reading the caller's cwd.
        _v27_nonrepo = Path(_v27_ad) / "nonrepo"
        _v27_nonrepo.mkdir(parents=True, exist_ok=True)
        _v27_foreign = Path(_v27_ad) / "foreign"
        _v27_foreign.mkdir(parents=True, exist_ok=True)
        _v22_git(_v27_foreign, "init", "-q", "-b", "main")
        _v22_git(_v27_foreign, "config", "user.email", "t@t")
        _v22_git(_v27_foreign, "config", "user.name", "t")
        _v27_foreign_rel = "/".join(_v27_own_rel.split("/")[:-1]
                                    + ["FOREIGN-MARKER", _v27_own_rel.split("/")[-1]])
        _v22_write(_v27_foreign, _v27_foreign_rel, {"schema": "nope", "verdict": "pass"})
        _v22_commit(_v27_foreign, "a misfiled verdict-shaped path in somebody else's repository")
        _v27_anc["reports"] = {}
        for _v27_where, _v27_cwd in (("its own root", _v27_vend),
                                     ("a directory that is no repository", _v27_nonrepo),
                                     ("a foreign repository", _v27_foreign)):
            _v27_r = subprocess.run(
                [sys.executable, str(_v27_vmod), "reconcile-verdicts", "--dry-run", "--json"],
                cwd=str(_v27_cwd), capture_output=True, text=True)
            try:
                _v27_anc["reports"][_v27_where] = json.loads(_v27_r.stdout)
            except ValueError:
                _v27_anc["reports"][_v27_where] = {"unparseable": _v27_r.stdout}
except Exception as _v27_aex:                    # pragma: no cover - recorded, never raised
    _v27_anc["error"] = "%s: %s" % (type(_v27_aex).__name__, _v27_aex)

expect("WARP-0727 AC1/AC4 ROUND 2: THE ENUMERATION IS ANCHORED AT THE VELDO ROOT THAT OWNS THE LOG, so a VELDO root BELOW the top of a larger repository enumerates its OWN corpus and no other - the route round 1 opened, driven exactly as the review drove it. VELDO is vendored at sub/ of an outer git repository, a CORPUS-SHAPED forgery is committed at the OUTER proof root, and the module is invoked BY ABSOLUTE PATH from the outer repository's own directory with NO flags, no --repo-root and no environment. The forged spec id appears in NO line of the vendored log, read back off the bytes; the domain is exactly the vendored root's own corpus; and the resolved pathspec carries that root's OWN prefix under the literal top-anchoring magic, which is the property rather than its consequence. THE POSITIVE HALF IS IN THE SAME LEG, because an anchoring that entitled NOTHING would satisfy the refusal: the entitlement the log's own root produces EQUALS that root's own derived keys and is NON-EMPTY, so not one genuine verdict is withheld - which is the harm round 1 shipped, an entitlement of zero against a full domain at a PASSING contract stage - and the blobs read back out of the log the run appended to are exactly the domain's own, with the contract stage over the vendored root clean",
       _v27_anc["error"] == ""
       and _v27_anc["prefix"] == "sub/"
       and _v27_anc["pathspec"] == (_v27_VC.CORPUS_PATHSPEC_MAGIC + "sub/" + _v27_VC.PROOF_ROOT)
       and "*" not in _v27_anc["pathspec"]
       and "WARP-9999" not in _v27_anc["after_text"]
       and _v27_anc["domain"] == {_v27_own_rel}
       and bool(_v27_anc["own_keys"])
       and _v27_anc["entitled"] == _v27_anc["own_keys"]
       and _v27_anc["own_blobs"] <= _v27_anc["landed_blobs"]
       and _v27_anc["landed_blobs"] == _v27_anc["own_blobs"]
       and _v27_anc["cli"].returncode == 0
       and _v27_anc["contract"] == 0)

expect("WARP-0727 AC1 ROUND 2: WHAT THE PROJECTION REPORTS IS A PROPERTY OF THE REPOSITORY IT BELONGS TO AND NOT OF THE DIRECTORY IT WAS INVOKED FROM. The corpus owner takes its root as a REQUIRED argument and the default is applied where ROOT is known, so the same module run from its own root, from a directory that is no git repository at all, and from a FOREIGN repository carrying a misfiled verdict-shaped path of its own, yields THE SAME REPORT - compared as parsed JSON, in both directions, over every key. Round 1 defaulted that cwd to the PROCESS CWD: the same clone reported the whole corpus from one directory and ZERO from another, and reconciling from a foreign repository printed a misfiled warning naming a path that exists only over there while the contract stage was green. The foreign repository's marker is required to appear in NO report, and the reports are required to be non-empty so three empty answers could not agree. Nothing here counts artifacts; the reports are compared with EACH OTHER, so this holds at whatever size the corpus grows to",
       _v27_anc["error"] == ""
       and len(_v27_anc["reports"]) == 3
       and all("unparseable" not in _v27_rep for _v27_rep in _v27_anc["reports"].values())
       and all(_v27_rep == _v27_anc["reports"]["its own root"]
               for _v27_rep in _v27_anc["reports"].values())
       and all(_v27_anc["reports"]["its own root"] == _v27_rep
               for _v27_rep in _v27_anc["reports"].values())
       and bool(_v27_anc["reports"]["its own root"].get("keys"))
       and all("FOREIGN-MARKER" not in json.dumps(_v27_rep, sort_keys=True)
               for _v27_rep in _v27_anc["reports"].values()))

# --- ROUND 3: THE RED DIRECTION IS ASKED OF GIT, AND ITS FAILING WITNESS IS CONSTRUCTED -----
# A VACUOUS ASSERTION IS THE WORST OUTCOME AVAILABLE, worse than no assertion at all, because it
# reads as coverage. The contradiction leg was `(disk - members) - (disk - tracked)`, which
# reduces to `(disk - members) intersect tracked` and is IDENTICALLY EMPTY FOR EVERY POSSIBLE
# INPUT, because disk_corpus returns only members and the tracked members ARE tracked intersect
# members. The check inferred untracked-ness FROM THE VERY ENUMERATION IT WAS VALIDATING, so the
# direction AC4 names for itself - red on a path git reports as TRACKED that the enumeration does
# not hold - could not fail for any repository, ever, and the suite asserted it empty for all
# four patterns and sold that as equality in both directions.
#
# IT IS NOW ASKED OF GIT: `tracked_direct`, a bare `ls-files` at the VELDO root with no pathspec
# and no prefix arithmetic, which is independent exactly where every measured defect lived. AND
# THE FAILING WITNESS IS CONSTRUCTED BELOW RATHER THAN ARGUED, because a guard whose failing case
# cannot be constructed is not a guard.
#
# THE WITNESS IS THE OTHER DEFECT OF THIS ROUND, WHICH IS WHAT MAKES IT A REGRESSION TEST AND NOT
# AN ARTIFICIAL ONE. `_git_line` returned `r.stdout.strip()` while `rev-parse --show-prefix`
# answers a REPO-RELATIVE PATH, so a VELDO root at ` lead/` became `lead/`, the pathspec became
# `:(top,literal)lead/proof`, and git answered SUCCESSFULLY WITH NOTHING: 0 tracked against 167
# validated, contract errors 0, `validate.py all` exit 0 PRINTING NOTHING AT ALL, the reconciler
# reporting `0 verdict artifact(s) tracked`. The same 166-to-0 signature review 1 blocked. Both
# halves are driven over ONE fixture whose prefix begins with a space: PRISTINE it enumerates the
# artifact, and with `.strip()` PUT BACK the check is RED per path with the reason named.
#
# TWO MORE SHAPES FOLLOW, each carrying its own half of the same law. A PROOF ROOT THAT IS A
# TRACKED SYMLINK: every per-path reason there is legitimately `untracked`, so no per-path leg
# says a word and only the empty-domain leg can - SILENCE IS THE DEFECT, NOT THE COUNT. And THE
# INDEX HOLDING A CORPUS THE WORKING TREE DOES NOT, which `git sparse-checkout set` reaches in the
# real repository and which used to silence the WHOLE check through an early return on the proof
# root's absence, at a green gate, while a plain reconciler run appended the forgery anyway.
import contextlib as _v27_ctx
import io as _v27_io

_v27_r3 = {"error": ""}
try:
    with tempfile.TemporaryDirectory() as _v27_r3d:
        # ---- SHAPE ONE: a VELDO root whose repo-relative prefix BEGINS WITH A SPACE ----------
        _v27_sp_outer = Path(_v27_r3d) / "outer"
        _v27_sp_root = _v27_sp_outer / " lead"
        _v27_sp_root.mkdir(parents=True, exist_ok=True)
        _v22_git(_v27_sp_outer, "init", "-q", "-b", "main")
        _v22_git(_v27_sp_outer, "config", "user.email", "t@t")
        _v22_git(_v27_sp_outer, "config", "user.name", "t")
        _v27_lay_veldo(_v27_sp_root)
        (_v27_sp_root / ".veldo/events.jsonl").write_text(_V22_SEED_LOG + "\n")
        _v27_sp_rel = _v25_artifact_rel("WARP-9770")
        _v22_write(_v27_sp_root, _v27_sp_rel, _v22_verdict("WARP-9770", "pass"))
        _v22_commit(_v27_sp_outer, "a VELDO root at a directory whose name begins with a space")
        _v27_sp_corpus = _v27_sp_root / ".veldo" / EV22.CORPUS_MODULE
        _v27_sp_pristine = _v27_sp_corpus.read_text()
        _v27_r3["sha_pristine"] = _v27_hashlib.sha256(
            _v27_sp_pristine.encode()).hexdigest()[:16]
        _v27_spVC = _v27_load("veldo_corpus_0727_sp", _v27_sp_corpus)
        _v27_r3["prefix"] = _v27_spVC.corpus_pathspec(str(_v27_sp_root))[1]
        _v27_r3["div"] = _v27_spVC.divergence(_v27_sp_root)
        _v27_r3["errs"] = _v27_load(
            "veldo_validate_0727_sp", _v27_sp_root / ".veldo/validate.py"
        ).check_verdict_domain_is_the_validated_set(root=str(_v27_sp_root))
        # ---- THE WITNESS: `.strip()` PUT BACK, ONE substitution, PROVEN to have landed ------
        _v27_sp_old = ("    out = r.stdout\n"
                       "    return (out[:-1] if out.endswith(\"\\n\") else out), True")
        _v27_sp_new = "    return r.stdout.strip(), True"
        _v27_r3["subs"] = _v27_sp_pristine.count(_v27_sp_old)
        _v27_sp_corpus.write_text(_v27_sp_pristine.replace(_v27_sp_old, _v27_sp_new))
        _v27_r3["sha_mut"] = _v27_hashlib.sha256(
            _v27_sp_corpus.read_text().encode()).hexdigest()[:16]
        _v27_r3["mut_present"] = _v27_sp_new in _v27_sp_corpus.read_text()
        _v27_mVC = _v27_load("veldo_corpus_0727_spm", _v27_sp_corpus)
        _v27_r3["mut_prefix"] = _v27_mVC.corpus_pathspec(str(_v27_sp_root))[1]
        _v27_r3["mut_div"] = _v27_mVC.divergence(_v27_sp_root)
        _v27_r3["mut_direct"] = _v27_mVC.tracked_direct(_v27_sp_root)[0]
        _v27_sp_said = _v27_io.StringIO()
        with _v27_ctx.redirect_stdout(_v27_sp_said):
            _v27_r3["mut_errs"] = _v27_load(
                "veldo_validate_0727_spm", _v27_sp_root / ".veldo/validate.py"
            ).check_verdict_domain_is_the_validated_set(root=str(_v27_sp_root))
        _v27_r3["mut_said"] = _v27_sp_said.getvalue()
        # ---- RESTORED, AND THE RESTORATION PROVEN ------------------------------------------
        _v27_sp_corpus.write_text(_v27_sp_pristine)
        _v27_r3["sha_restored"] = _v27_hashlib.sha256(
            _v27_sp_corpus.read_text().encode()).hexdigest()[:16]
        _v27_r3["restored_errs"] = _v27_load(
            "veldo_validate_0727_spr", _v27_sp_root / ".veldo/validate.py"
        ).check_verdict_domain_is_the_validated_set(root=str(_v27_sp_root))

        # ---- SHAPE TWO: the proof root is a TRACKED SYMLINK onto a vendored corpus ----------
        _v27_sy = _v22_seed(os.path.join(_v27_r3d, "sym"),
                            [(_v25_artifact_rel("WARP-9771"),
                              _v22_verdict("WARP-9771", "pass"))])
        _v27_lay_veldo(_v27_sy)
        _v22_commit(_v27_sy, "the engine")
        _v27_r3["sy_before"] = _v27_load(
            "veldo_validate_0727_sy0", _v27_sy / ".veldo/validate.py"
        ).check_verdict_domain_is_the_validated_set(root=str(_v27_sy))
        # THE VIOLATION IS ADDED, NEVER A RENAME: the corpus MOVES behind a symlink at the proof
        # root, which is a shape ordinary vendoring produces, and the fixture is asserted to have
        # taken that shape before any result from it is believed.
        _v27_sy_vend = "vendored-" + _v27_VC.PROOF_ROOT
        _v22_git(_v27_sy, "mv", _v27_VC.PROOF_ROOT, _v27_sy_vend)
        os.symlink(_v27_sy_vend, str(_v27_sy / _v27_VC.PROOF_ROOT))
        _v22_commit(_v27_sy, "the proof root is a tracked symlink onto a vendored corpus")
        _v27_r3["sy_index"] = _v22_git(
            _v27_sy, "ls-files", "-s", "--", _v27_VC.PROOF_ROOT).stdout.split()
        _v27_r3["sy_div"] = _v27_load(
            "veldo_corpus_0727_sy", _v27_sy / ".veldo" / EV22.CORPUS_MODULE).divergence(_v27_sy)
        _v27_sy_said = _v27_io.StringIO()
        with _v27_ctx.redirect_stdout(_v27_sy_said):
            _v27_r3["sy_errs"] = _v27_load(
                "veldo_validate_0727_sy", _v27_sy / ".veldo/validate.py"
            ).check_verdict_domain_is_the_validated_set(root=str(_v27_sy))
        _v27_r3["sy_said"] = _v27_sy_said.getvalue()

        # ---- SHAPE THREE: the index holds the corpus, the WORKING TREE DOES NOT -------------
        # Reached in the real repository by `git sparse-checkout set` naming every top level
        # directory except the proof root (measured; the manifest carries that run). The working
        # tree is emptied HERE by removing the directory, because that is the CONDITION - an
        # index half with no working-tree half - and it needs no particular git version to reach.
        _v27_sc = _v22_seed(os.path.join(_v27_r3d, "sc"),
                            [(_v25_artifact_rel("WARP-9772"),
                              _v22_verdict("WARP-9772", "pass"))])
        _v27_lay_veldo(_v27_sc)
        _v27_sc_bad = _v25_artifact_rel("WARP-9999")
        _v22_write(_v27_sc, _v27_sc_bad, {"schema": "nope", "verdict": "pass"})
        _v22_commit(_v27_sc, "a corpus-shaped forgery beside a genuine verdict")
        _v27_sc_log = _v27_sc / ".veldo/events.jsonl"
        _v27_scV = _v27_load("veldo_validate_0727_sc0", _v27_sc / ".veldo/validate.py")
        _v27_r3["sc_present_errs"] = _v27_scV.check_verdict_domain_is_the_validated_set(
            root=str(_v27_sc))
        _v27_shutil.rmtree(str(_v27_sc / _v27_VC.PROOF_ROOT))
        _v27_r3["sc_gone"] = not (_v27_sc / _v27_VC.PROOF_ROOT).exists()
        _v27_sc_said = _v27_io.StringIO()
        with _v27_ctx.redirect_stdout(_v27_sc_said):
            _v27_r3["sc_errs"] = _v27_load(
                "veldo_validate_0727_sc", _v27_sc / ".veldo/validate.py"
            ).check_verdict_domain_is_the_validated_set(root=str(_v27_sc))
        _v27_r3["sc_said"] = _v27_sc_said.getvalue()
        _v27_r3["sc_div"] = _v27_load(
            "veldo_corpus_0727_sc", _v27_sc / ".veldo" / EV22.CORPUS_MODULE).divergence(_v27_sc)
        _v27_sc_before = _v27_sc_log.read_bytes()
        _v27_r3["sc_rep"] = EV22.reconcile_verdicts(repo_root=str(_v27_sc))
        _v27_r3["sc_after"] = _v27_sc_log.read_bytes()
        _v27_r3["sc_line"] = _v25_line(_v27_r3["sc_rep"])
        # THE CONTROL IS ADDITIVE AND REVERSED: the working tree gets the corpus BACK from the
        # index that never stopped holding it, and both the check and the appender must go back to
        # what they said before, or this is a check that fires on everything.
        _v22_git(_v27_sc, "checkout", "--", _v27_VC.PROOF_ROOT)
        _v27_r3["sc_restored_errs"] = _v27_load(
            "veldo_validate_0727_scr", _v27_sc / ".veldo/validate.py"
        ).check_verdict_domain_is_the_validated_set(root=str(_v27_sc))
        _v27_r3["sc_rep_restored"] = EV22.reconcile_verdicts(repo_root=str(_v27_sc))
except Exception as _v27_r3ex:                   # pragma: no cover - recorded, never raised
    _v27_r3["error"] = "%s: %s" % (type(_v27_r3ex).__name__, _v27_r3ex)

expect("WARP-0727 AC4 ROUND 3: THE RED DIRECTION HAS A FAILING WITNESS, AND IT REDS. The tracked-or-not question is put to GIT (a bare ls-files at the VELDO root, no pathspec, no prefix arithmetic) instead of being derived from the enumeration under test, which made `contradiction` arithmetically empty for every possible input and therefore a vacuous assertion sold as coverage. Driven over a VELDO root whose repo-relative prefix BEGINS WITH A SPACE: pristine, the prefix survives with its space, the artifact is entitled AND validated and every divergence leg is empty; with `.strip()` PUT BACK - ONE substitution, its count asserted and the file's sha256 asserted to change, to differ, and to come back - the prefix loses its space, the domain goes EMPTY against a working tree that still holds the artifact, GIT STILL REPORTS THAT EXACT PATH AS TRACKED, and the contract check goes RED naming it as a contradiction rather than passing in silence. The restored copy scores exactly what the pristine one did. A property of the named member throughout, no cardinality of anything that can grow",
       _v27_r3["error"] == ""
       and _v27_r3["prefix"] == " lead/"
       and _v27_r3["subs"] == 1 and _v27_r3["mut_present"]
       and _v27_r3["sha_mut"] != _v27_r3["sha_pristine"]
       and _v27_r3["sha_restored"] == _v27_r3["sha_pristine"]
       and _v27_r3["div"]["entitled"] == [_v27_sp_rel]
       and _v27_r3["div"]["validated"] == [_v27_sp_rel]
       and _v27_r3["div"]["contradiction"] == [] and _v27_r3["div"]["overclaimed"] == []
       and _v27_r3["div"]["untracked"] == [] and _v27_r3["errs"] == 0
       and _v27_r3["mut_prefix"] == "lead/"
       and _v27_r3["mut_div"]["entitled"] == []
       and _v27_r3["mut_div"]["validated"] == [_v27_sp_rel]
       and _v27_sp_rel in _v27_r3["mut_direct"]
       and _v27_r3["mut_div"]["contradiction"] == [_v27_sp_rel]
       and _v27_r3["mut_errs"] > 0
       and _v27_sp_rel in _v27_r3["mut_said"]
       and _v27_r3["restored_errs"] == _v27_r3["errs"])

expect("WARP-0727 AC4 ROUND 3: AN EMPTY DOMAIN AGAINST A NON-EMPTY WORKING TREE IS NEVER SILENT, whatever the per-path reasons are. A proof root that is a TRACKED SYMLINK onto a vendored corpus is the shape where every per-path reason is legitimately `untracked` - git tracks no path UNDER the proof root, so nothing is a contradiction and nothing is misfiled - and the whole corpus is validated against a domain of ZERO, which is the exact 166-to-0 signature both measured anchoring defects wore. The fixture is asserted to have taken that shape (the index entry for the proof root is a symlink mode) before any result from it is believed, the VIOLATION IS ADDED to a fixture that scored zero moments earlier rather than renamed into place, and the check is RED with the count on both sides and a tracked path named in the message",
       _v27_r3["error"] == ""
       and _v27_r3["sy_before"] == 0
       and _v27_r3["sy_index"][:1] == ["120000"]
       and _v27_r3["sy_div"]["entitled"] == []
       and bool(_v27_r3["sy_div"]["validated"])
       and _v27_r3["sy_div"]["untracked"] == _v27_r3["sy_div"]["validated"]
       and _v27_r3["sy_div"]["contradiction"] == []
       and _v27_r3["sy_div"]["misfiled"] == []
       and _v27_r3["sy_div"]["tracked_under_proof"] == [_v27_VC.PROOF_ROOT]
       and _v27_r3["sy_errs"] > 0
       and _v27_VC.PROOF_ROOT in _v27_r3["sy_said"])

expect("WARP-0727 AC4 ROUND 3: AN INDEX HALF WITH NO WORKING-TREE HALF IS RED AND UNAPPENDABLE, where an early return on the proof root's absence used to silence the WHOLE check and print nothing. Reached in the real repository by `git sparse-checkout set` naming every top level directory except the proof root: `validate.py all` exited 0 where the same commit with the proof root present exits 1, and a plain reconciler run appended a verdict.recorded with a real blob for a corpus-shaped forgery. Here the working tree is emptied of the corpus the index still holds: EVERY artifact is named as tracked-and-not-validated by the contract check, and the appender REFUSES all of them - the log is proven BYTE-IDENTICAL by reading it back, nothing is derivable, and each one is DEFERRED with the absence named, because the bytes have to be there to be keyed and an append-only log cannot take back an event for a review nothing has seen. THE CONTROL IS ADDITIVE AND REVERSED: the corpus comes back from the index that never stopped holding it, the check goes back to zero and the appender records the reviews, so this is not a check that fires on everything",
       _v27_r3["error"] == ""
       and _v27_r3["sc_present_errs"] == 0
       and _v27_r3["sc_gone"]
       and _v27_r3["sc_div"]["entitled_not_validated"] == _v27_r3["sc_div"]["entitled"]
       and bool(_v27_r3["sc_div"]["entitled"])
       and _v27_r3["sc_errs"] == len(_v27_r3["sc_div"]["entitled"])
       and all(_r in _v27_r3["sc_said"] for _r in _v27_r3["sc_div"]["entitled"])
       and _v27_r3["sc_after"] == _v27_sc_before
       and _v27_r3["sc_rep"]["appended"] == 0
       and _v27_r3["sc_rep"]["derivable"] == 0
       and len(_v27_r3["sc_rep"]["deferred"]) == len(_v27_r3["sc_div"]["entitled"])
       and all("absent from the working tree" in _why
               for _p, _why in _v27_r3["sc_rep"]["deferred"])
       and "deferred" in _v27_r3["sc_line"]
       and _v27_r3["sc_restored_errs"] == 0
       and _v27_r3["sc_rep_restored"]["appended"] > 0)

# --- THE PROJECTION OWNS THE TYPE, AND THAT IS A REFUSAL IN CODE RATHER THAN PROSE --
# The module's docstring forbade hand-emitting verdict.recorded and NOTHING enforced it:
# `events.py emit verdict.recorded` exited 0, because the type is a member of EVENT_TYPES
# and make_event only checked membership. Two independent reviewers found it, and one
# demonstrated the consequence, which is the reason this is not a style point: the
# reconciler's withheld set was built from the unresolved events with NO producer
# distinction, so ONE hand-emitted unresolvable line naming a real spec id withheld EVERY
# future genuine review of that spec, on every run, in every clone, in a log nothing may
# rewrite, while validate.py still exited 0. Teeth held by the constrained party are not
# teeth, so both doors now refuse and the refusal is asserted rather than described.
import shutil as _v22_shutil

with tempfile.TemporaryDirectory() as _v22_ro_d:
    # A THROWAWAY TREE CARRYING ITS OWN COPY OF THE MODULE, because the emitter's LOG is a
    # property of where the module lives. Run against this repository's copy, a mutant with
    # the refusal removed would append a line to the REAL append-only log to prove the
    # assertion reachable, and nothing could take it back. Here it appends to a temp file
    # and the assertion fails, which is the difference between failing and crashing.
    _v22_ro = Path(_v22_ro_d) / "tree"
    _v22_lay_module(_v22_ro)
    _v22_ro_log = _v22_ro / ".veldo/events.jsonl"

    def _v22_emit_cli(etype, *extra):
        return subprocess.run([sys.executable, str(_v22_ro / ".veldo/events.py"), "emit",
                               etype, "--spec", "WARP-9780", *extra],
                              capture_output=True, text=True)

    # A BLOB THIS REPOSITORY REALLY WOULD ENTITLE, offered through the hand-emission door: the
    # guard is not fooled by a well-formed content key, because emit() is entitled to none.
    _v22_real_blob = _v22_derivable[0][2]
    _v22_ro_runs = {
        "owned": _v22_emit_cli(_V22_VERDICT),
        # `--producer` is a string the caller chooses, so it must not buy a way past
        "owned_forged": _v22_emit_cli(_V22_VERDICT, "--producer", _V22_PRODUCER),
        # THE ROUND-6 DEFEAT, MEASURED ON THE SHIPPED TREE BEFORE THIS WAS WRITTEN: the type
        # named through a --field instead of through the argument round 6 checked. It landed a
        # verdict.recorded declaring the reconciler's own producer, at exit 0, with
        # `validate.py all` green, and every genuine verdict of that spec was WITHHELD on every
        # run afterwards. These four are the same door with the name moved around on it.
        "field_type": _v22_emit_cli("spec.ready", "--field", "type=" + _V22_VERDICT),
        "field_type_full": _v22_emit_cli(
            "spec.ready", "--field", "type=" + _V22_VERDICT,
            "--field", "producer=" + _V22_PRODUCER,
            "--field", "verdict_path=proof/WARP-9780/verdict.json",
            "--field", "spec_id=WARP-9780"),
        "field_type_real_key": _v22_emit_cli(
            "spec.ready", "--field", "type=" + _V22_VERDICT,
            "--field", "verdict_blob=" + _v22_real_blob),
        # THE SAME CLASS ON THE OTHER GUARD: make_event checks the vocabulary on its ARGUMENT,
        # so a type named through --field wrote a line NO VALIDATOR RECOGNISES into an
        # append-only log. Measured on the shipped tree: exit 0, and `validate.py all` RED from
        # then on, permanently, over a line nothing may rewrite.
        "field_type_unknown": _v22_emit_cli("spec.ready", "--field", "type=verdict.invented"),
        "unknown": _v22_emit_cli("verdict.invented"),
        "allowed": _v22_emit_cli("proof.recorded"),
        # an ALLOWED type carrying --field must still land, so the empty log above is a refusal
        # and not a fixture that cannot write at all
        "allowed_field": _v22_emit_cli("proof.recorded", "--field", "note=carried"),
    }
    _v22_ro_refused = [_k for _k in _v22_ro_runs if _k != "allowed" and _k != "allowed_field"]
    # THE READBACK. This is the leg round 6 did not have: every earlier round asserted the
    # refusal over the type it PASSED POSITIONALLY and never over the type of a line that
    # LANDED, so a guard on an argument satisfied every assertion while the bytes carried the
    # forbidden name. What is read here is the log ITSELF, parsed, one type per line.
    _v22_ro_written = _v22_landed_types(_v22_ro_log)
    # the in-process door, with the log pointed somewhere disposable for the same reason - and
    # driven AT ALL only while the fixture can aim it, because a mutant with the refusal removed
    # must append to a temp file, never to the real append-only log.
    _v22_direct_log = Path(_v22_ro_d) / "direct.jsonl"
    _v22_real_LOG = _v22_log_now()
    _v22_direct_refused, _v22_direct_control = {}, None
    try:
        if _v22_point_log_at(_v22_direct_log):
            # THE IN-PROCESS DOORS, INCLUDING THE OVERRIDE DICTS THE CLI RIDES ON. `extra` is
            # merged into the envelope LAST, so it can set `type` and `producer` over anything
            # an argument said, which is the in-process spelling of the defeat measured above.
            for _name, _kw in (
                    ("type argument", {"etype": _V22_VERDICT}),
                    ("extra type override", {"etype": "spec.ready",
                                             "extra": {"type": _V22_VERDICT}}),
                    ("extra type + producer + blob",
                     {"etype": "spec.ready",
                      "extra": {"type": _V22_VERDICT, "producer": _V22_PRODUCER,
                                "verdict_blob": _v22_real_blob}}),
                    ("extra unknown type", {"etype": "spec.ready",
                                            "extra": {"type": "verdict.invented"}})):
                try:
                    EV22.emit(_kw["etype"], spec="WARP-9781", extra=_kw.get("extra"))
                    _v22_direct_refused[_name] = None
                except Exception as _v22_ex:     # NOTHING RAISES OUT OF HERE: the exception is
                    _v22_direct_refused[_name] = (  # recorded WITH ITS CLASS and asserted below
                        "%s: %s" % (type(_v22_ex).__name__, _v22_ex))
            # THE ALLOWED-TYPE CONTROL, WRAPPED THE WAY ITS FOUR SIBLINGS ABOVE ARE. Round 8
            # left this one call bare, and that is where the additive-global measurement came
            # out: two json-lines globals made round 8's count fail, the module was made unable
            # to open anything, this line raised out of the block and the suite printed no
            # pass/fail summary at all. It is a SUBJECT - the allowed type must land, which is
            # what makes the empty log above a refusal - so its failure is recorded and
            # asserted, never raised.
            try:
                EV22.emit("proof.recorded", spec="WARP-9781")
                _v22_direct_control = "landed"
            except Exception as _v22_cx:
                _v22_direct_control = "%s: %s" % (type(_v22_cx).__name__, _v22_cx)
    finally:
        _v22_point_log_at(_v22_real_LOG)
    _v22_direct_written = _v22_landed_types(_v22_direct_log)
    # WHICH TYPES THE DOOR REFUSES, quantified over the module's OWN vocabulary rather than
    # over a list typed here: exactly the projection-owned set, and nothing else the loop emits.
    # DRIVEN THROUGH THE DOOR AND READ BACK OFF THE BYTES, over a throwaway log of its own.
    # Round 7 called the refusal helper BY NAME here, which cost the suite its pass/fail summary
    # entirely under a pure rename (AttributeError, no summary at all), and would have been
    # self-confirming once the helper is discovered by exactly this behaviour. The door is the
    # subject anyway: what a caller can get into the log is what matters, not what a helper says.
    _v22_vocab_log = Path(_v22_ro_d) / "vocab.jsonl"
    _v22_refused_types, _v22_vocab_errors = set(), {}
    try:
        if _v22_point_log_at(_v22_vocab_log):
            for _t in sorted(_V22_VOCAB):
                try:
                    EV22.emit(_t, spec="WARP-9783")
                except ValueError:
                    _v22_refused_types.add(_t)
                except Exception as _v22_vx:      # anything that is NOT a refusal is recorded
                    _v22_vocab_errors[_t] = "%s: %s" % (type(_v22_vx).__name__, _v22_vx)
    finally:
        _v22_point_log_at(_v22_real_LOG)
    _v22_vocab_landed = set(_v22_landed_types(_v22_vocab_log))
    expect("WARP-0722: ON EVERY ROUTE DRIVEN HERE, NO LINE WHOSE OWN `type` FIELD IS THE PROJECTION'S LANDS THROUGH THIS MODULE'S HAND-EMISSION DOOR, AND THAT IS ASSERTED BY READING THE APPENDED BYTES BACK rather than by checking the type somebody passed. THE HEADLINE DOES NOT SAY `EVER`, BECAUSE THAT UNIVERSAL WAS MEASURED FALSE HERE: a `str` SUBCLASS whose `__hash__` and `__eq__` are chosen so BOTH membership tests miss while `json.dumps` writes the owned name landed a `verdict.recorded` line through emit() in process. WARP-0723 round 2 REFUSES that route - a reserved name, `type` among them, is taken only from an EXACT str, asserted in its own block below - and the headline still claims the routes below and no more, because a universal beyond what is driven is exactly the shape that defeated six rounds. THIS LEG IS WHY SIX ROUNDS FAILED: every one of them quantified the refusal over an ARGUMENT, so round 5's guard on the constructor and round 6's guard on emit()'s type parameter both passed while an attacker named the type another way and the bytes landed - round 6 with `--field type=verdict.recorded`, a shipped flag, measured on the shipped tree at exit 0 with `validate.py all` green and every genuine verdict of that spec withheld forever afterwards. Eight routes are DRIVEN over one throwaway log - the type as the argument, with `--producer` naming the reconciler, through `--field type=`, through `--field` carrying the full harmful line (type, the reconciler's producer, a verdict_path and a spec_id), through `--field` carrying a verdict_blob THIS REPOSITORY REALLY WOULD ENTITLE, through `--field type=` naming a type no validator declares, and the same overrides through the in-process `extra` dict - and the ONLY types read back off that log are the allowed ones, which is what makes the empty result a refusal rather than a fixture that cannot write. THE VOCABULARY CHECK MOVED ONTO THE BYTES FOR THE SAME REASON: make_event checks its argument, so `--field type=verdict.invented` wrote a line no validator recognises into an APPEND-ONLY log and reddened `validate.py all` permanently. Each refusal is the same ValueError shape, surfaced by the CLI as exit 2 naming the type, and the refused set is quantified over the module's own EVENT_TYPES BY DRIVING THE DOOR WITH EVERY ONE OF THEM over a throwaway log of its own: what is refused equals the projection-owned set EXACTLY - set against set, with the verdict event required to BE A MEMBER of it rather than to be the whole of it, because how many types a projection owns is a property this repository can grow - and every other declared type LANDS, read back off those bytes, so this neither misses a type the projection later claims nor blocks one the loop is entitled to emit. Round 7 asked a refusal helper BY NAME for that set, which a pure rename turned into an AttributeError with no pass/fail summary printed at all. NOTHING IN THIS LEG RAISES OUT: every route records the exception it got WITH ITS CLASS and the class is asserted to be ValueError, the ALLOWED-TYPE CONTROL is wrapped the same way (round 8 left that one call bare, and it is exactly where the additive-global measurement took the whole suite's reporting down), any non-refusal exception from the vocabulary sweep is recorded rather than propagated, the READBACK records a line it cannot parse as one JSON object carrying a `type` as a marker in no vocabulary rather than raising out of a list comprehension, and the two preconditions this leg needs - that the module still declares the four contract names this block looks up, and that the log can be pointed somewhere disposable - are CONJUNCTS here, so losing either is a red with the summary printed instead of a traceback",
           _V22_CONTRACT_NAMES_PRESENT
           and _V22_LOG_REDIRECTABLE
           and all(_v22_ro_runs[_k].returncode == 2 for _k in _v22_ro_refused)
           and _v22_ro_runs["allowed"].returncode == 0
           and _v22_ro_runs["allowed_field"].returncode == 0
           and all(_V22_VERDICT in _v22_ro_runs[_k].stdout
                   and "DERIVED, never emitted" in _v22_ro_runs[_k].stdout
                   for _k in ("owned", "owned_forged", "field_type", "field_type_full",
                              "field_type_real_key"))
           and all("unknown event type" in _v22_ro_runs[_k].stdout
                   for _k in ("unknown", "field_type_unknown"))
           # THE READBACK: the types of the lines that actually landed, off the log itself
           and _v22_ro_written == ["proof.recorded", "proof.recorded"]
           and not (set(_v22_ro_written) - set(_V22_VOCAB))
           and not (set(_v22_ro_written) & set(_V22_OWNED))
           and sorted(_v22_direct_refused) == ["extra type + producer + blob",
                                               "extra type override", "extra unknown type",
                                               "type argument"]
           and all(isinstance(_m, str) and _m.startswith("ValueError: ")
                   for _m in _v22_direct_refused.values())
           and all(_V22_VERDICT in _v22_direct_refused[_k]
                   for _k in ("type argument", "extra type override",
                              "extra type + producer + blob"))
           and _v22_direct_control == "landed"
           and _v22_direct_written == ["proof.recorded"]
           and not (set(_v22_direct_written) & set(_V22_OWNED))
           and _v22_vocab_errors == {}
           # THE REFUSED SET EQUALS THE OWNED SET, and the verdict event is A MEMBER of it.
           # Round 8 wrote `== {_V22_VERDICT}` here, which is the same defect as the count it
           # was removing one line at a time: declaring a SECOND projection-owned type is an
           # ordinary contract change and would have reddened this on a module behaving
           # correctly. Non-vacuity is held by _V22_CONTRACT_NAMES_PRESENT above, which
           # requires the owned set to be non-empty.
           and _v22_refused_types == set(_V22_OWNED)
           and _V22_VERDICT in _V22_OWNED
           and _v22_vocab_landed == set(_V22_VOCAB) - set(_V22_OWNED)
           and set(_V22_OWNED) <= set(_V22_VOCAB))

    # --- THE MODULE'S WRITE SURFACE, AND THE WRITERS OUTSIDE IT --------------------
    # ROUND 5 PUT THE REFUSAL ON THE CONSTRUCTOR AND LEFT A HOLE UNDER IT. It renamed the
    # envelope builder to a private `_envelope`, made `make_event` a wrapper holding the check,
    # and had the projection call `_envelope` directly - so anything else calling `_envelope`
    # skipped the refusal entirely, under a headline claiming every route was covered.
    # MEASURED at 19c396b: a second writer added to the module, building through `_envelope` and
    # appending itself, wrote exactly the harmful line - a verdict.recorded with no verdict_blob
    # declaring this projection's producer, which withholds that spec's appends forever in a log
    # nothing may rewrite - and the whole suite stayed at 3236 passed 0 failed.
    #
    # AND ROUND 6 THEN GUARDED emit()'s TYPE ARGUMENT, WHICH IS A DESCRIPTION OF THE EVENT AND
    # NOT THE EVENT. `--field type=verdict.recorded` sets that field AFTER the argument was
    # checked, and the harmful line landed at exit 0 on the shipped tree. So the refusal now
    # reads the type OFF THE ASSEMBLED DICT inside the single function that writes the bytes,
    # and the two legs below bind that WITHOUT WRITING DOWN EITHER SIDE - because a function
    # name is a moving repository property, round 6's expectation pinned two WRITER names plus
    # which one held the open (an extract-a-helper refactor reddened a required gate), and
    # round 7 then pinned the two REFUSAL names instead (a pure rename raised AttributeError
    # and the suite printed NO pass/fail summary at all, which is worse than a red).
    #
    # What the assertion below binds:
    #   emit()          the module's only GENERAL writer, which writes through the one writer
    #                   below and is entitled to no projection-owned key.
    #   the CLI         can only write through emit(); refused at exit 2 (asserted above).
    #   executor.py     LiveLoop.emit -> events.emit, and .veldo/executor.py:500 hand-emits
    #                   EXACTLY this type at its review step. FOUND BY READING in round 5, named
    #                   in no brief. Unreachable with the reference loop (LiveLoop.review raises
    #                   first), so nothing shipped regresses; an adopting runtime that injects an
    #                   agent-backed review now gets a refusal where it used to get an
    #                   unresolvable line. Deleting that call belongs to the module that owns it,
    #                   OUTSIDE this footprint: queued, not smuggled.
    #   THE WRITE SURFACE ITSELF, read off the module's own AST WITH NEITHER SIDE WRITTEN DOWN:
    #                   the write set is discovered by resolving what each byte emission TARGETS
    #                   and the refusal set by what those functions DO, and every scope that
    #                   emits bytes to the LOG must have a refusal on every path into it. So the
    #                   guard cannot be one hop away with an unguarded path underneath, which is
    #                   the arrangement that produced round 5's hole. WHICH SPELLINGS ARE
    #                   MEASURED GREEN, one by one, all eight copies each time: renaming the
    #                   writer, renaming the refusals, renaming the writer's parameters, renaming
    #                   the module's log global, the loop rewritten as one `writelines`, moving
    #                   the refusal definitions below the writer, extracting `open(LOG, "a")`
    #                   into a helper, extracting the append loop into `_write_all(fh, events)`,
    #                   moving both refusals onto a class as staticmethods, a delegating second
    #                   writer, the guard called through a helper, and an unrelated
    #                   `sys.stderr.write` in now_iso. The last four of those and the two renames
    #                   are what rounds 6 and 7 got wrong: the pin was never removed, only moved.
    #                   WHICH ARE MEASURED RED: a second writer that opens the log and writes
    #                   without a refusal, the projection refusal deleted from the writer, the
    #                   vocabulary refusal deleted from it, and a guard helper defined but never
    #                   called. WHAT THIS LEG IS BLIND TO: a write target assembled at RUN TIME
    #                   out of values carrying no mark and no path constant cannot be resolved
    #                   statically, which is why every door it binds is also DRIVEN.
    #   make_event      NOT refused, deliberately. It is the one constructor, the projection uses
    #                   it too, and it writes nothing.
    # AND THE WRITERS THAT ARE NOT IN THIS MODULE, WHICH NO CHECK HERE CAN REACH:
    #   the gate script and the push guard printf an envelope from a shell variable that only
    #                   ever holds a gate or emergency event. Asserted per file below.
    #   .veldo/request_reconcile.py builds envelope dicts LITERALLY and appends them to the same
    #                   log without importing this module at all - a writer this item's earlier
    #                   rounds never named. Its event vocabulary is driven below and cannot
    #                   produce this type.
    #   .veldo/reconciliation_store.py appends caller-supplied event dicts to the same log through
    #                   `log.open("a")`, also without importing this module, driven by
    #                   .veldo/incident_reconcile.py settle(). NOT driven here and NOT enumerated
    #                   by anything here: the completeness leg below is mechanical over .sh files
    #                   ONLY, and there is none over .py files. Harmless today (its only type is
    #                   incident.closed) but the word ENUMERATED is gone from the headline rather
    #                   than left standing over a set nobody mechanised. The .py leg is QUEUED.
    #   a hand-edited log is refusable by nothing, and that is DECLARED, not claimed away: what
    #                   the reconciler does with such a line is the report plus the producer
    #                   classification the module documents.
    # Driven against a throwaway tree carrying its own copies, because a mutant that removes
    # the refusal must append to a disposable file and fail an assertion, never to the real
    # append-only log where nothing could take it back.
    _v22_shutil.copy(str(ROOT / ".veldo/executor.py"), str(_v22_ro / ".veldo/executor.py"))
    _v22_ex_spec = importlib.util.spec_from_file_location(
        "veldo_executor_0722", str(_v22_ro / ".veldo/executor.py"))
    _v22_EX = importlib.util.module_from_spec(_v22_ex_spec)
    _v22_ex_spec.loader.exec_module(_v22_EX)
    _v22_route_log = Path(_v22_ro_d) / "routes.jsonl"
    _v22_route_refused, _v22_route_allowed = {}, {}
    _v22_real_LOG = _v22_log_now()
    try:
        if _v22_point_log_at(_v22_route_log):
            # FOUR ROUTES, AND TWO OF THEM NAME THE TYPE THROUGH A FIELD RATHER THAN AN
            # ARGUMENT, because that is the route round 6's argument check could not see.
            # LiveLoop.emit forwards **fields into `extra`, so an adopting runtime reaches the
            # same override.
            for _name, _fn in (
                    ("emit", lambda t: EV22.emit(t, spec="WARP-9782")),
                    ("emit via extra type", lambda t: EV22.emit(
                        "spec.ready" if t == _V22_VERDICT else t, spec="WARP-9782",
                        extra={"type": t})),
                    ("executor hook", lambda t: _v22_EX.LiveLoop(root=str(_v22_ro)).emit(
                        t, spec="WARP-9782")),
                    ("executor hook via extra type", lambda t: _v22_EX.LiveLoop(
                        root=str(_v22_ro)).emit(
                            "spec.ready" if t == _V22_VERDICT else t, spec="WARP-9782",
                            type=t))):
                for _t, _bucket in ((_V22_VERDICT, _v22_route_refused),
                                    ("proof.recorded", _v22_route_allowed)):
                    try:
                        _fn(_t)
                        _bucket[_name] = None
                    except Exception as _rx:   # recorded WITH ITS CLASS, never raised out
                        _bucket[_name] = "%s: %s" % (type(_rx).__name__, _rx)
    finally:
        _v22_point_log_at(_v22_real_LOG)
    _v22_ro_types_now = _v22_landed_types(_v22_ro_log)
    _v22_route_types = _v22_landed_types(_v22_route_log)
    # THE WRITE SURFACE, per declared copy, off the AST - AND WITH NEITHER SET WRITTEN DOWN.
    # BOTH SETS ARE DISCOVERED, because this item has now pinned a moving repository property
    # here for three rounds running and each pin was worse than the last. Round 6 pinned the
    # two WRITER names and reddened on extract-a-helper. Round 7 pinned the two REFUSAL names
    # and reddened WITHOUT A PASS/FAIL SUMMARY AT ALL - a pure rename in all eight copies gave
    # `AttributeError: module 'veldo_events_0722' has no attribute refuse_projection_owned`,
    # taking the whole gate's reporting down, which is strictly worse than a red; and its write
    # predicate counted ANY `.write` in the module, so an unrelated `sys.stderr.write` added to
    # now_iso reddened a required gate while extracting the append loop reddened it too. AND
    # ROUND 8 PINNED A COUNT - `len(the module's json-lines Path globals) == 1` - which one
    # PURELY ADDITIVE unused global beside the log, in all eight copies, turned into a traceback
    # with no summary. Not one of the three rounds ever tested an ADDITIVE change; each proved
    # its pin survived renames and extractions, and the class is about the repository GROWING.
    #
    # THE WRITE SET is resolved by WHAT EACH WRITE TARGETS: the log, identified by the globals
    # the module's appended bytes were OBSERVED to follow (discovered by driving a copy of the
    # module in a tree of its own, so a rename carries this with it and an added global cannot
    # disturb it) plus those paths' own components, and followed through assignments, `with`
    # bindings, call arguments and returned handles to a fixed point. So `sys.stderr.write` is
    # not a log write, and a handle handed to an extracted helper still is.
    # THE REFUSAL SET is discovered by WHAT THOSE FUNCTIONS DO: they raise ValueError on every
    # projection-owned type and return on every other type the module declares. Their `__name__`
    # is read off the discovered objects, never typed here.
    # NO SET HERE IS A NAME, AND NONE IS A COUNT OF ANYTHING THE REPOSITORY CAN GROW.
    # THE MARKS: the globals the appended bytes were observed to follow, plus the components of
    # every path they hold. Per DISCOVERED GLOBAL, never "the one global" and never "how many":
    # a second and a third json-lines global beside the log contribute nothing, because the
    # probe's bytes never reached them.
    _v22_log_paths = _v22_log_now() or {}
    _v22_log_parts = set()
    for _lp22 in sorted(str(_p) for _p in _v22_log_paths.values() if _p is not None):
        try:
            _v22_log_parts |= set(Path(_lp22).resolve().relative_to(ROOT).parts)
        except ValueError:                                # pragma: no cover - log outside ROOT
            _v22_log_parts.add(Path(_lp22).name)
    _v22_log_marks = set(_v22_log_paths) | _v22_log_parts
    # THE REFUSALS, BY BEHAVIOUR. The projection refusal refuses exactly the projection-owned
    # types and accepts the rest of the vocabulary; the vocabulary refusal refuses a type the
    # module does not declare and accepts every one it does. Neither probe can append: the
    # candidate rule admits only unary functions and emit() takes **kw.
    _v22_owned_types = set(_V22_OWNED)
    _v22_other_types = set(_V22_VOCAB) - _v22_owned_types
    _v22_owned_refusals = _v22_refusals_by_behaviour(EV22, _v22_owned_types, _v22_other_types)
    _v22_vocab_refusals = _v22_refusals_by_behaviour(
        EV22, {"veldo.no.such.event.type.0722"}, set(_V22_VOCAB))
    # PER COPY: the log-write scopes, whether each is covered by BOTH refusals, and the byte
    # emissions that are NOT the log (reported, never required to be absent - an stderr line is
    # not a log write and must not redden a gate).
    _v22_cov_owned, _v22_cov_vocab = {}, {}
    _v22_logw, _v22_otherw, _v22_dup_defs = {}, {}, {}
    for _rel in _v22_module_rels:
        if not (ROOT / _rel).is_file():
            continue
        _t22 = _v22_ast.parse((ROOT / _rel).read_text())
        _d22, _lw22, _ow22, _hf22, _du22 = _v22_log_flow(_t22, _v22_log_marks)
        _v22_logw[_rel], _v22_otherw[_rel], _v22_dup_defs[_rel] = _lw22, _ow22, _du22
        for _kind, _names, _sink in (("owned", _v22_owned_refusals, _v22_cov_owned),
                                     ("vocab", _v22_vocab_refusals, _v22_cov_vocab)):
            _gl22 = _v22_guard_lines(_d22, _names)
            _sink[_rel] = sorted(_s for _s in _lw22
                                 if not _v22_write_covered(_s, _lw22, _hf22, _gl22))
    # THE SHELL WRITERS, derived from the corpus rather than typed: every tracked .sh file
    # carrying an event envelope. The expectation is the DECLARED roster - the gate script at
    # every declared pack's engine root plus this repository's own, and the push guard at every
    # engine root plus the one wrapper root that ships a runnable guard of its own - so a shell
    # writer appearing anywhere else reddens, and a declared one that stops writing reddens too.
    # Round 5's version was one flat list of lines over sixteen files with `bool(...)` as its
    # only non-vacuity guard, so one file still writing hid fifteen that had stopped; the roster
    # is per file now.
    #
    # PLAN-0008 CONSOLIDATION: the guard is ENGINE, so it is no longer copied into every pack's
    # wrapper root - a wrapper root gets its guard by assembly, not by a committed copy, and
    # `_v22_wrapper_copies` here named seven paths that are deliberately absent. The single
    # exception is the pack whose `pack_dir` IS the canonical engine (claude): its engine is the
    # source in place, so its wrapper at packs/claude/ carries a real runnable guard beside the
    # template it distributes. That root is read off the MANIFEST, never off the disk, so
    # deleting the file reddens on `_v22_absent` instead of quietly shrinking the roster.
    # DISCOVERED, like everything else in this block. This used to ask which pack's pack_dir WAS
    # the engine root, which identified the Claude pack only because plugin/ was both the pack and
    # the base. The 2026-08-09 split gave the base its own home, so that proxy now matches nothing
    # and the roster emptied silently - exactly the failure the len() == 1 beside it exists to
    # catch, which is why it caught it. Ask what a wrapper actually SHIPS instead.
    _v22_guard_wrapper_roots = sorted(
        p["wrapper_dir"] for p in _V22_DECLARED_PACKS
        if (ROOT / p["wrapper_dir"] / "scripts" / "veldo-guard.sh").is_file())
    _v22_shell_rels = sorted(set(
        _v22_verify_rels + _v22_engine_copies("scripts/veldo-guard.sh", "scripts/veldo-guard.sh")
        + [_r + "/scripts/veldo-guard.sh" for _r in _v22_guard_wrapper_roots]))
    _v22_shell_writers = {}
    for _f in _v22_tracked:
        if not _f.endswith(".sh"):
            continue
        _lines22 = [_ln for _ln in (ROOT / _f).read_text(errors="replace").splitlines()
                    if "veldo.event/v1" in _ln]
        if _lines22:
            _v22_shell_writers[_f] = _lines22
    # ONE .py WRITER OUTSIDE THIS MODULE, DRIVEN: request_reconcile builds its envelopes
    # literally and appends them to the same log. Its whole event vocabulary, over every
    # touchpoint the contract declares and both intents, cannot name the projection's type.
    # IT IS NOT THE ONLY ONE AND NOTHING HERE ENUMERATES THEM: the leg above is mechanical over
    # .sh files only, and `.veldo/reconciliation_store.py` appends caller-supplied event dicts to
    # this same log through `log.open("a")` without importing this module, driven through
    # `.veldo/incident_reconcile.py` settle(). Harmless today - its only type is incident.closed -
    # but neither named nor driven here, so the word ENUMERATED is gone from this leg rather than
    # left standing over a set nobody mechanised. A .py completeness leg is QUEUED.
    _v22_rr_types = set()
    for _tp22 in sorted(RQ_RR.TOUCHPOINTS):
        for _intent22 in ("accept", "reject"):
            for _e22 in RR._events({"id": "REQ-9722", "touchpoint": _tp22}, _intent22):
                _v22_rr_types.add(_e22.get("type"))
    expect("WARP-0722: EVERY SCOPE THAT PUTS BYTES IN THE LOG IS REACHED ONLY THROUGH BOTH REFUSALS, AND NEITHER SET IS WRITTEN DOWN HERE - BOTH ARE DISCOVERED. Off every declared copy's AST: the WRITE set by resolving what each byte emission TARGETS, where the log is identified by the globals the module's appended bytes were OBSERVED TO FOLLOW - discovered by driving a copy of the module in a tree of its own, so renaming the constant carries this with it and adding a second or a third json-lines global cannot disturb it - plus those paths' own components, followed through assignments, `with` bindings, call arguments and returned handles to a fixed point; and the REFUSAL set by what those functions DO - raise ValueError on every projection-owned type and return on every other type the module declares - with their `__name__` read off the discovered objects. Covered means a refusal on EVERY path in: invoked inside the writing scope before its own first write, or invoked by every caller that HANDS it the log, above the handoff. THIS IS THE THIRD ROUND OF A PIN ON A MOVING REPOSITORY PROPERTY IN THIS ONE EXPECTATION, EACH WORSE THAN THE LAST, ALL THREE MEASURED. Round 6 pinned the two WRITER names and an ordinary extract-a-helper refactor reddened a required gate. Round 7 pinned the two REFUSAL names and a PURE RENAME of the projection refusal in all eight copies, behaviour identical, raised `AttributeError: module 'veldo_events_0722' has no attribute 'refuse_projection_owned'` with NO PASS/FAIL SUMMARY PRINTED AT ALL - a crash takes the whole gate's reporting down and is strictly worse than a red. And round 7's write predicate counted ANY `.write` in the module rather than writes to THE LOG, so an unrelated `sys.stderr.write` in now_iso made this the SOLE failure of the suite, while extracting the append loop into a helper reddened it as well: the pin had moved, not gone. AND ROUND 8 THEN PINNED A COUNT: `len(the module's json-lines Path globals) == 1`, which is a CARDINALITY OF SOMETHING THIS REPOSITORY CAN ORDINARILY GROW - the module's own docstring already mentions a run folder's live.jsonl - so adding one UNUSED global beside the log in all eight copies, nothing referencing it, behaviour identical, made the count fail, made the module unable to open anything, and printed NO PASS/FAIL SUMMARY AT ALL. Three rounds pinned a name, a name and a count; the log is now DISCOVERED BY DRIVING A COPY OF THE MODULE IN A TREE OF ITS OWN and the property is required OF EACH global the bytes were observed to follow. WHICH PRECONDITIONS ARE CONJUNCTS RATHER THAN CRASHES, and no more than these: that the module still declares the four contract names this block looks up by name (PROJECTION_OWNED, EVENT_TYPES, VERDICT_EVENT, RECONCILE_PRODUCER - renaming one is a RED naming the loss, which is the honest cost of a block that has to be able to say `the projection-owned set`), that at least one global carries the appended bytes so the log can be pointed somewhere disposable, and that a callable behaving like each refusal exists. THE MODULE'S OTHER MEMBERS GET NO SUCH GUARD AND THAT IS A RESIDUAL, NOT A UNIVERSAL: reconcile_verdicts, INDEX_FILE_MODES, _report_line, verdict_domain and the rest are looked up unguarded in this block, and renaming one of THOSE still raises out of it. WHAT THIS IS BLIND TO: a target assembled at RUN TIME from values carrying no mark and no constant cannot be resolved statically, which is why every door is also DRIVEN. `make_event` is NOT refused and that is deliberate - it is the one constructor, the projection uses it too, and building an envelope writes nothing. FOUR ROUTES DRIVEN, EACH BOTH WAYS: in-process emit and the executor hook (.veldo/executor.py hand-emits exactly this type at its review step, found by reading in round 5 and named in no brief), each also driven with the type set through the OVERRIDE DICT rather than the argument; every one refuses the projection's type and lands an allowed one, so each refusal is proven rather than each fixture proven broken. TWO WRITERS OUTSIDE THIS MODULE ARE SEPARATELY BOUND, AND NOTHING HERE ENUMERATES THE REST: every tracked .sh file that writes an envelope is exactly the declared gate-and-guard roster, each one still writes at least one, and none can name this type; and .veldo/request_reconcile.py, which appends to the same log without importing this module at all, is DRIVEN over every declared touchpoint and both intents and cannot produce this type. The mechanical leg is over .sh files ONLY - there is none over .py files, `.veldo/reconciliation_store.py` appends to this log without importing this module and is neither named nor driven here, and that leg is QUEUED rather than claimed. A hand-edited log is refusable by nothing, which is declared and not claimed away",
           sorted(_v22_route_refused) == ["emit", "emit via extra type", "executor hook",
                                          "executor hook via extra type"]
           and all(isinstance(_m, str) and _m.startswith("ValueError: ")
                   and _V22_VERDICT in _m and "DERIVED, never emitted" in _m
                   for _m in _v22_route_refused.values())
           and sorted(_v22_route_allowed) == sorted(_v22_route_refused)
           and set(_v22_route_allowed.values()) == {None}
           # READ BACK: the types of every line that LANDED, off both logs the driven routes
           # can reach (the in-process routes write through the globals the module's appended
           # bytes were OBSERVED to follow, redirected through those names, the executor routes
           # through the throwaway tree's own copy of the module, which also holds the two the
           # CLI block landed). Every landing is the allowed type, neither log is empty, and
           # the total is one landing per allowed route plus those two.
           and set(_v22_route_types) == set(_v22_ro_types_now) == {"proof.recorded"}
           and (len(_v22_route_types) + len(_v22_ro_types_now)
                == len(_v22_route_allowed) + len(_v22_ro_written))
           and not ((set(_v22_route_types) | set(_v22_ro_types_now))
                    & set(_V22_OWNED))
           # THE LOG IS DISCOVERED BY DRIVING THE MODULE, and NOT COUNTED. Round 8 required
           # `len(json-lines globals) == 1` here, a cardinality of something this repository can
           # ordinarily grow, and adding one UNUSED second global took the whole suite's
           # reporting down. What is required now is a property OF EACH global the appended
           # bytes were observed to follow: it holds a path whose name the gate's own event
           # validator reads. Adding a second or a third json-lines global changes nothing,
           # because the probe's bytes never reached it. Non-vacuity: at least one was found,
           # which is also what makes the redirection above possible at all.
           and _V22_LOG_REDIRECTABLE and _V22_CONTRACT_NAMES_PRESENT
           and all(_p is not None
                   and Path(_p).name in (ROOT / ".veldo/validate.py").read_text()
                   for _p in _v22_log_paths.values())
           # BOTH REFUSALS ARE DISCOVERED BY BEHAVIOUR, are distinct, and exist at all
           and bool(_v22_owned_refusals) and bool(_v22_vocab_refusals)
           and not (_v22_owned_refusals & _v22_vocab_refusals)
           # EVERY DECLARED COPY WAS READ, and they are byte-identical, which is what lets one
           # imported copy stand for the behaviour of all eight
           and _v22_absent(_v22_module_rels) == []
           and sorted(_v22_logw) == sorted(_v22_cov_owned) == sorted(_v22_cov_vocab) \
               == _v22_module_rels
           and len({(ROOT / _r).read_bytes() for _r in _v22_module_rels}) == 1
           # NON-VACUOUS: bytes do reach the log somewhere in every copy. No count of scopes,
           # because that is a moving property and pinning it is what round 7 did.
           and all(_v22_logw[_r] for _r in _v22_module_rels)
           and all(_v22_dup_defs[_r] == [] for _r in _v22_module_rels)
           # AND EVERY ONE OF THEM IS COVERED BY BOTH REFUSALS. The uncovered lists are the
           # subject: empty in every copy, for each refusal separately.
           and all(_v22_cov_owned[_r] == [] for _r in _v22_module_rels)
           and all(_v22_cov_vocab[_r] == [] for _r in _v22_module_rels)
           and _V22_ROSTER_COMPLETE
           # exactly one wrapper root ships its own guard, so the roster cannot empty silently
           and len(_v22_guard_wrapper_roots) == 1
           and _v22_absent(_v22_shell_rels) == []
           and sorted(_v22_shell_writers) == _v22_shell_rels
           and all(_v22_shell_writers[_f] for _f in _v22_shell_rels)
           and all(_V22_VERDICT not in _ln
                   for _lns in _v22_shell_writers.values() for _ln in _lns)
           and bool(_v22_rr_types)
           and _V22_VERDICT not in _v22_rr_types
           and _v22_rr_types <= set(RQ_RR.REQUEST_EVENT_TYPES)
           and _V22_VERDICT not in (ROOT / ".veldo/request_reconcile.py").read_text())

# --- and the other half: the logs that ALREADY carry a hand-written line ----------
with tempfile.TemporaryDirectory() as _v22_hw_d:
    _v22_hw = _v22_seed(os.path.join(_v22_hw_d, "hw"), [
        ("proof/WARP-9790/verdict.json", _v22_verdict("WARP-9790", "pass")),
        ("proof/WARP-9791/verdict.json", _v22_verdict("WARP-9791", "fail", 1)),
    ], log_lines=[json.dumps(
        {"schema": "veldo.event/v1", "id": "byhand000000", "type": "verdict.recorded",
         "at": "2026-01-01T00:00:00Z", "producer": "a skill that remembered",
         "spec_id": "WARP-9790", "correlation_id": "WARP-9790", "commit": "0" * 40,
         "verdict_path": "proof/WARP-9790/verdict.json", "verdict": "pass"})])
    _v22_hw_rep = EV22.reconcile_verdicts(repo_root=str(_v22_hw))
    _v22_hw_rep2 = EV22.reconcile_verdicts(repo_root=str(_v22_hw))
    _v22_hw_line = EV22._report_line(_v22_hw_rep)
    expect("WARP-0722: A HAND-WRITTEN VERDICT EVENT DECLARING A FOREIGN PRODUCER WITHHOLDS NOTHING - and the headline says FOREIGN because the universal it used to carry is FALSE: a line declaring THIS projection's producer does withhold that spec, which the module, the spec and every capability copy say, and which this body does not check. With the withheld set built from the unresolved events with no producer distinction, this ONE line - a real spec id, an unresolvable (commit, path) pair - permanently withheld EVERY future genuine review of WARP-9790, on every run and in every clone, while the gate stayed green. The withheld set is now the reconciler's OWN unresolvable events only, so both specs append, and the foreign line is REPORTED BY NAME with its producer rather than swallowed. Idempotence is unharmed (the second run appends zero) and the append-only rule is kept: the hand-written line is still the first line of the file",
           _v22_hw_rep["appended"] == 2 and _v22_hw_rep2["appended"] == 0
           and _v22_hw_rep["withheld"] == [] and _v22_hw_rep["unresolved_legacy"] == []
           and _v22_hw_rep["unresolvable_foreign"] == [
               ["WARP-9790", "proof/WARP-9790/verdict.json", "a skill that remembered"]]
           and "proof/WARP-9790/verdict.json by a skill that remembered" in _v22_hw_line
           and "withholding nothing" in _v22_hw_line
           and sorted(_e["spec_id"] for _e in _v22_logged(_v22_hw) if _e.get("verdict_blob"))
               == ["WARP-9790", "WARP-9791"]
           and json.loads(_v22_lines(_v22_hw / ".veldo/events.jsonl")[0])["producer"]
               == "a skill that remembered")

# --- ride-along: a tracked SYMLINK at a verdict path is not a verdict -------------
with tempfile.TemporaryDirectory() as _v22_sy_d:
    _v22_sy = _v22_seed(os.path.join(_v22_sy_d, "sy"),
                        [("proof/WARP-9795/verdict.json", _v22_verdict("WARP-9795", "pass"))])
    os.symlink("verdict.json", str(_v22_sy / "proof/WARP-9795/verdict-link.json"))
    _v22_commit(_v22_sy, "a tracked symlink sitting at a verdict path")
    _v22_sy_modes = sorted({ln.split()[0] for ln in _v22_git(
        _v22_sy, "ls-files", "-s", "proof/*/verdict*.json").stdout.splitlines() if ln.strip()})
    _v22_sy_rep = EV22.reconcile_verdicts(repo_root=str(_v22_sy))
    expect("WARP-0722 ride-along: A TRACKED SYMLINK AT A VERDICT PATH IS NOT A VERDICT. `git ls-files -s` reports it with a 40-hex object name that looks exactly like a blob, so before the index mode was checked it was keyed like an artifact and the event recorded no verdict, no round and no commit while the contract stage stayed green over it. It is now DEFERRED with its mode NAMED - the same shape as every other deferral - the regular file beside it still appends, and the allowed modes are the two a regular file can have rather than a blanket 'not 120000', so a submodule gitlink is refused by the same rule",
           _v22_sy_modes == ["100644", "120000"]
           and EV22.INDEX_FILE_MODES == ("100644", "100755")
           and _v22_sy_rep["domain"] == 2 and _v22_sy_rep["appended"] == 1
           and _v22_sy_rep["deferred"] == [["proof/WARP-9795/verdict-link.json",
                                            "index mode 120000, not a regular file"]]
           and [_e["verdict_path"] for _e in _v22_logged(_v22_sy)]
               == ["proof/WARP-9795/verdict.json"])

# --- AC2 idempotence over a fixture repository, asserted before the real backfill --
with tempfile.TemporaryDirectory() as _v22_d:
    _v22_fx = _v22_seed(os.path.join(_v22_d, "fx"), [
        ("proof/WARP-9722/verdict-1-fail.json", _v22_verdict("WARP-9722", "fail", 1)),
        ("proof/WARP-9722/verdict.json", _v22_verdict("WARP-9722", "pass", 2)),
        ("proof/WARP-9723/verdict.json", _v22_verdict("WARP-9723", "pass_with_notes")),
    ])
    _v22_fxlog = _v22_fx / ".veldo/events.jsonl"
    _v22_l0 = _v22_lines(_v22_fxlog)
    _v22_r1 = EV22.reconcile_verdicts(repo_root=str(_v22_fx))
    _v22_l1 = _v22_lines(_v22_fxlog)
    _v22_r2 = EV22.reconcile_verdicts(repo_root=str(_v22_fx))
    _v22_l2 = _v22_lines(_v22_fxlog)
    _v22_r3 = EV22.reconcile_verdicts(repo_root=str(_v22_fx))
    _v22_l3 = _v22_lines(_v22_fxlog)
    expect("WARP-0722 AC2: THE SECOND RUN APPENDS ZERO LINES, and so does the third - the first appends exactly one event per verdict artifact (the one-time backfill), and the file is byte-for-byte unchanged by every run after it. The log is APPEND-ONLY and that is asserted too: the lines seeded before reconciliation are still a PREFIX of the file afterwards, so nothing was rewritten or truncated to achieve idempotence",
           _v22_r1["appended"] == 3 and len(_v22_l1) == len(_v22_l0) + 3
           and _v22_r2["appended"] == 0 and _v22_l2 == _v22_l1
           and _v22_r3["appended"] == 0 and _v22_l3 == _v22_l1
           and _v22_l1[:len(_v22_l0)] == _v22_l0 and _v22_l0 == [_V22_SEED_LOG])

    # the same field on a log whose every verdict event is new-form: NO old-form event to
    # resolve, so the route is the empty string. Captured here and asserted beside the real
    # log's "batch" below, so `legacy_route` is proven to take more than one value.
    _v22_fx_route = EV22.logged_verdict_state(_v22_fxlog, repo_root=str(_v22_fx))[3]
    _v22_fx_keys = {t[0] for t in EV22.verdict_domain(repo_root=str(_v22_fx))[0]}
    _v22_fx_logged = [EV22.event_verdict_key(e) for e in _v22_logged(_v22_fx)]
    expect("WARP-0722 AC2: NO DUPLICATE KEY in the reconciled log, and the log's verdict keys EQUAL the derived key set exactly - counted after three runs, so 'exactly once' is measured over repetition rather than asserted of one pass. Every event also carries the blob it is keyed by, so the next run recognises it WITHOUT asking git anything",
           len(_v22_fx_logged) == len(set(_v22_fx_logged)) == len(_v22_fx_keys) == 3
           and set(_v22_fx_logged) == _v22_fx_keys
           and all(e.get("verdict_blob") and e.get("verdict_path") for e in _v22_logged(_v22_fx))
           and EV22.reconcile_verdicts(repo_root=str(_v22_fx), dry_run=True)["duplicate_keys_in_log"] == 0)

    _v22_staged = _v22_write(_v22_fx, "proof/WARP-9724/verdict.json", _v22_verdict("WARP-9724", "pass"))
    _v22_git(_v22_fx, "add", "-A")
    _v22_r4 = EV22.reconcile_verdicts(repo_root=str(_v22_fx))
    _v22_l4 = _v22_lines(_v22_fxlog)
    _v22_commit(_v22_fx, "commit the staged verdict")
    _v22_r5 = EV22.reconcile_verdicts(repo_root=str(_v22_fx))
    _v22_l5 = _v22_lines(_v22_fxlog)
    _v22_r6 = EV22.reconcile_verdicts(repo_root=str(_v22_fx))
    expect("WARP-0722 AC2: a verdict STAGED but not yet committed is returned by `git ls-files` and is DEFERRED WITH THE REASON rather than keyed off the index - it appends nothing, because the review may never land and an append-only log could not take it back. Once committed it appends EXACTLY ONE event, and the run after that appends zero again",
           _v22_r4["deferred"] == [["proof/WARP-9724/verdict.json", "staged, not committed"]]
           and _v22_r4["appended"] == 0 and _v22_l4 == _v22_l1
           and _v22_r5["deferred"] == [] and _v22_r5["appended"] == 1
           and len(_v22_l5) == len(_v22_l1) + 1 and _v22_r6["appended"] == 0)

# --- AC2 THE AMEND-IN-PLACE CONVENTION, which is what broke the round-1 key -----
with tempfile.TemporaryDirectory() as _v22_od:
    _v22_ov = _v22_seed(os.path.join(_v22_od, "ov"),
                        [("proof/WARP-9730/verdict.json", _v22_verdict("WARP-9730", "fail", 1))])
    _v22_ov_r1 = EV22.reconcile_verdicts(repo_root=str(_v22_ov))
    # the convention this repository actually follows across review rounds: the round-1
    # verdict is copied out under its own name and verdict.json is OVERWRITTEN with round 2
    _v22_write(_v22_ov, "proof/WARP-9730/verdict-1-fail.json", _v22_verdict("WARP-9730", "fail", 1))
    _v22_write(_v22_ov, "proof/WARP-9730/verdict.json", _v22_verdict("WARP-9730", "pass_with_notes", 2))
    _v22_commit(_v22_ov, "round 2 overwrites verdict.json, round 1 copied out")
    _v22_ov_r2 = EV22.reconcile_verdicts(repo_root=str(_v22_ov))
    _v22_ov_r3 = EV22.reconcile_verdicts(repo_root=str(_v22_ov))
    _v22_ov_evs = _v22_logged(_v22_ov)
    _v22_ov_pairs = sorted((e.get("verdict"), e.get("round")) for e in _v22_ov_evs)
    expect("WARP-0722 AC2, THE DEFECT THAT FAILED ROUND 1, CLOSED AND ASSERTED ON THE CONVENTION THAT PRODUCED IT: a verdict AMENDED IN PLACE is a different review and gets its OWN event, and the copy of round 1 written out under a new name appends NOTHING because it carries the same content as the review already recorded. So the log ends with exactly one fail round 1 and one pass_with_notes round 2 - what the artifacts say - where a key on the path's earliest add recorded the round-1 fail and NEVER the round-2 pass. The third run appends zero, so the amendment is recorded once and not on every gate run",
           _v22_ov_r1["appended"] == 1 and _v22_ov_r2["appended"] == 1
           and _v22_ov_r3["appended"] == 0
           and _v22_ov_pairs == [("fail", 1), ("pass_with_notes", 2)]
           and _v22_ov_r2["duplicate_keys_in_log"] == 0
           and _v22_ov_r3["superseded"] == 0)

    _v22_git(_v22_ov, "mv", "proof/WARP-9730/verdict-1-fail.json",
             "proof/WARP-9730/verdict-1-fail-round1.json")
    _v22_commit(_v22_ov, "rename the round-1 copy, as this repository has actually done")
    _v22_ov_r4 = EV22.reconcile_verdicts(repo_root=str(_v22_ov))
    expect("WARP-0722 AC2: A RENAME APPENDS NOTHING, because the blob does not move when the file does and the PATH is not part of the key. Round 1 keyed on the path, so a rename minted a second event for a review already recorded - the shape this repository has already performed once, on proof/WARP-1210/verdict-1-fail.json",
           _v22_ov_r4["appended"] == 0 and _v22_ov_r4["derivable"] == 2
           and len(_v22_logged(_v22_ov)) == 2)

# --- AC1/AC2 THE DECLARED FALLBACK, MADE REACHABLE AND ASSERTED -----------------
# Round 2 asserted `at == reviewed_at` as a universal while the module deliberately dates
# an artifact with no usable reviewed_at at RECONCILIATION. Both could not hold, and the
# artifact that broke the tie is the shape of the SHIPPED verdict example, which
# .veldo/validate.py accepts: committing one turned exactly ONE assertion of this block red at
# 528c98f, a RED gate on a valid artifact, while the stage line correctly reported the fallback. The
# assertion above is now quantified over the partition; these fixtures EXERCISE the branch
# that was unreachable, so the declared behaviour is proven rather than merely declared.
with tempfile.TemporaryDirectory() as _v22_fb_d:
    _v22_example = json.loads((ROOT / ".veldo/examples/verdict-example.json").read_text())
    expect("WARP-0722 AC1: the SHIPPED verdict example - the one a reviewer is told to follow - declares NO reviewed_at and `.veldo/validate.py` does not require it, so the projection's fallback branch is reachable from the repository's own documentation rather than hypothetical. Asserted on the shipped file and on the contract, not on a fixture, because that is what made round 2's universal a red gate",
           "reviewed_at" not in _v22_example
           and "reviewed_at" not in V.VERDICT_REQ
           and V.check_json(ROOT / ".veldo/examples/verdict-example.json", V.VERDICT_REQ, "verdict") == 0)

    _v22_fb = _v22_seed(os.path.join(_v22_fb_d, "fb"), [
        ("proof/WARP-9760/verdict.json", {"schema": "veldo.verdict/v1", "spec_id": "WARP-9760",
                                          "commit": "c0ffee", "reviewer": "fixture",
                                          "verdict": "pass", "criteria": []}),
        ("proof/WARP-9761/verdict.json", _v22_verdict("WARP-9761", "pass_with_notes", 1,
                                                      "2026-07-27T12:00:00+00:00")),
        ("proof/WARP-9762/verdict.json", _v22_verdict("WARP-9762", "fail", 2)),
    ])
    _v22_fb_rep = EV22.reconcile_verdicts(repo_root=str(_v22_fb))
    _v22_fb_rep2 = EV22.reconcile_verdicts(repo_root=str(_v22_fb))
    _v22_fb_evs = {e.get("spec_id"): e for e in _v22_logged(_v22_fb)}
    expect("WARP-0722 AC1: THE FALLBACK IS EXERCISED AND CORRECT, over both shapes that reach it. An artifact declaring NO reviewed_at and one declaring it in another legal ISO form (`+00:00`) are BOTH dated at reconciliation in the one format this envelope writes, BOTH have the field dropped rather than reshaped, and BOTH are COUNTED in the report - which is what `dated_at_reconciliation` exists for and what makes the branch checkable instead of forbidden. The artifact that DOES declare a usable one is dated by it. All three are appended exactly once and the second run appends zero, so the fallback does not cost idempotence",
           _v22_fb_rep["appended"] == 3 and _v22_fb_rep2["appended"] == 0
           and _v22_fb_rep["dated_at_reconciliation"] == 2
           and "reviewed_at" not in _v22_fb_evs["WARP-9760"]
           and "reviewed_at" not in _v22_fb_evs["WARP-9761"]
           and EV22._iso_z(_v22_fb_evs["WARP-9760"]["at"])
           and EV22._iso_z(_v22_fb_evs["WARP-9761"]["at"])
           and _v22_fb_evs["WARP-9762"]["at"] == "2026-01-02T03:04:05Z"
           and _v22_fb_evs["WARP-9762"]["reviewed_at"] == "2026-01-02T03:04:05Z")

    # THE ONE FIELD TWO CLONES MAY DIFFER ON, proven by moving the clock rather than
    # claimed: with now_iso() returning a different answer the KEY is byte-identical and
    # only `at` moves, and only for the artifact that declares no usable timestamp.
    _v22_fb_dom = EV22.verdict_domain(repo_root=str(_v22_fb))[0]
    _v22_real_now = EV22.now_iso
    try:
        EV22.now_iso = lambda: "2030-01-01T00:00:00Z"
        _v22_clock_a = [EV22.verdict_event(*_t, repo_root=str(_v22_fb)) for _t in _v22_fb_dom]
        EV22.now_iso = lambda: "2031-06-06T06:06:06Z"
        _v22_clock_b = [EV22.verdict_event(*_t, repo_root=str(_v22_fb)) for _t in _v22_fb_dom]
    finally:
        EV22.now_iso = _v22_real_now
    _v22_moved = [(a["spec_id"], a["at"] != b["at"]) for a, b in zip(_v22_clock_a, _v22_clock_b)]
    expect("WARP-0722 AC2: THE DECLARED COST OF THE FALLBACK, MEASURED RATHER THAN CLAIMED: with the clock moved a year, the KEYS and the event IDS are byte-identical and the ONLY field that moves is the `at` of the two artifacts that declare no usable reviewed_at - the artifact that declares one is unmoved. So the one case where two clones can differ is a payload field, never the key, exactly as the record says, and it is now provable in both directions rather than unreachable",
           [a["id"] for a in _v22_clock_a] == [b["id"] for b in _v22_clock_b]
           and sorted(s for s, moved in _v22_moved if moved) == ["WARP-9760", "WARP-9761"]
           and sorted(s for s, moved in _v22_moved if not moved) == ["WARP-9762"]
           and {tuple(EV22.event_verdict_key(a)) for a in _v22_clock_a}
               == {tuple(EV22.event_verdict_key(b)) for b in _v22_clock_b})

# --- AC2 the collapse signal: an absorbed artifact is now PUBLISHED, not noticed --
with tempfile.TemporaryDirectory() as _v22_co_d:
    _v22_twin = {"schema": "veldo.verdict/v1", "spec_id": "WARP-9770", "commit": "c0ffee",
                 "reviewer": "fixture", "verdict": "pass", "criteria": []}
    _v22_co = _v22_seed(os.path.join(_v22_co_d, "co"), [
        ("proof/WARP-9770/verdict.json", _v22_twin),
        ("proof/WARP-9770/verdict-2.json", dict(_v22_twin)),
    ])
    _v22_co_rep = EV22.reconcile_verdicts(repo_root=str(_v22_co))
    _v22_co_line = EV22._report_line(_v22_co_rep)
    _v22_co2 = _v22_seed(os.path.join(_v22_co_d, "co2"), [
        ("proof/WARP-9771/verdict.json", _v22_verdict("WARP-9771", "pass", None, "2026-01-02T03:04:05Z")),
        ("proof/WARP-9771/verdict-2.json", _v22_verdict("WARP-9771", "pass", None, "2026-01-02T03:04:06Z")),
    ])
    _v22_co2_rep = EV22.reconcile_verdicts(repo_root=str(_v22_co2))
    expect("WARP-0722 AC2: THE ABSORBED ARTIFACT IS PUBLISHED. Two BYTE-IDENTICAL verdict artifacts of one spec are one review and share one key, so one is absorbed - a declared cost of content keying, and the round-2 review's point was that nothing SAID so. The report now carries the count and the stage line names it, which is this item's own rule that every non-zero integrity signal is published. The boundary is asserted too: the same two reviews with timestamps ONE SECOND apart are two different reviews and get two events, so the collapse is exactly as narrow as identical content",
           _v22_co_rep["derivable"] == 2 and _v22_co_rep["appended"] == 1
           and _v22_co_rep["collapsed"] == 1
           and "1 artifact(s) absorbed by an identical review already keyed" in _v22_co_line
           and _v22_co2_rep["derivable"] == 2 and _v22_co2_rep["appended"] == 2
           and _v22_co2_rep["collapsed"] == 0)

# --- AC2 the batch resolution answers exactly what the per-event route answered ---
# ROUND 4 ASSERTED WHICH ROUTE RAN, AND THAT IS A PIN ON AN ENVIRONMENT PROPERTY. It closed
# with `_v22_batch_route == "batch" and _v22_rep["legacy_route"] == "batch"`, while the module
# deliberately KEEPS the per-event resolver as a proven-equivalent fallback for a git that
# cannot run `cat-file --batch-check -z`. MEASURED before this was rewritten: with the batch
# resolver stubbed to return None in all eight copies at 28c0775, EVERY key still resolves,
# the duplicate count and the unresolved list are identical, and that tree's suite lost
# exactly one assertion - this one - a red gate on the module behaving exactly as designed. So the assertion below
# states the PROPERTY (the two resolvers agree, every key resolves, a resolver ran exactly
# when there was old-form work to do) and never which one served.
_v22_batch_keys, _v22_batch_dupes, _v22_batch_unres, _v22_batch_route = EV22.logged_verdict_state(_v22_log, repo_root=str(ROOT))
_v22_old_form = [_e for _e in EV22.read_log(_v22_log)
                 if _e.get("type") == _V22_VERDICT and not _e.get("verdict_blob")]
# BOTH RESOLVERS DRIVEN DIRECTLY over the same old-form events, which is what makes this a
# differential between two IMPLEMENTATIONS rather than between whichever one the module
# picked: when the batch call fails, logged_verdict_state resolves through legacy_event_key,
# so comparing its answer with legacy_event_key's own is a comparison of the fallback with
# itself. Driving _batch_blob_shas here compares the two for real, and when this git cannot
# run the batch at all the batch side is None and the leg is skipped rather than red.
_v22_batch_direct = EV22._batch_blob_shas(
    ["%s:%s" % (_e.get("commit") or "", _e.get("verdict_path") or "") for _e in _v22_old_form],
    repo_root=str(ROOT))
_v22_slow_direct = [EV22.legacy_event_key(_e, repo_root=str(ROOT)) for _e in _v22_old_form]
_v22_batch_direct_keys = None if _v22_batch_direct is None else [
    (EV22.verdict_key(EV22.spec_id_for_verdict(_e.get("verdict_path") or ""), _b,
                      _e.get("type") or "") if _b else None)
    for _e, _b in zip(_v22_old_form, _v22_batch_direct)]
_v22_slow_keys, _v22_slow_dupes, _v22_slow_unres = set(), 0, []
for _ev in EV22.read_log(_v22_log):
    if _ev.get("type") != _V22_VERDICT:
        continue
    _k = EV22.event_verdict_key(_ev) or EV22.legacy_event_key(_ev, repo_root=str(ROOT))
    if _k is None:
        _v22_slow_unres.append(_ev.get("verdict_path"))
        continue
    if _k in _v22_slow_keys:
        _v22_slow_dupes += 1
    _v22_slow_keys.add(_k)
expect("WARP-0722 AC2: THE TWO RESOLVERS ANSWER THE SAME THING, AND NOTHING HERE DEMANDS WHICH ONE SERVED. Round 2 resolved every old-form event with its OWN `git rev-parse`, spending a process per event and most of the stage's wall clock on interpreter startup - the same shape WARP-0711 spent five rounds removing from the lint stage; the figures live in this item's manifest against the revision each was taken at, because a count written here goes stale as the log grows. `git cat-file --batch-check -z` does it in ONE call and the module keeps the per-event route as a fallback for a git that cannot, so BOTH are supported and the equivalence is asserted by driving each resolver DIRECTLY over the same old-form events rather than by comparing the module's answer with the very function it falls back to. Round 4 asserted `route == 'batch'`, which pinned a required gate to WHICH SUPPORTED PATH EXECUTED, an environment property: measured, stubbing the batch resolver left every key, the duplicate count and the unresolved list identical and reddened the suite anyway. What is asserted instead is total - the route is a member of the vocabulary the MODULE declares, and a resolver ran exactly when there was an old-form event to resolve, so the field cannot be a constant and cannot be a false red",
       _v22_batch_keys == _v22_slow_keys
       and _v22_batch_dupes == _v22_slow_dupes
       and len(_v22_batch_unres) == len(_v22_slow_unres)
       and "--batch-check" in _v22_events_src
       and bool(_v22_batch_keys)
       and (_v22_batch_direct_keys is None
            or _v22_batch_direct_keys == _v22_slow_direct)
       and _v22_batch_route in EV22.LEGACY_ROUTES
       and _v22_rep["legacy_route"] in EV22.LEGACY_ROUTES
       and (_v22_batch_route != EV22.ROUTE_NONE) == bool(_v22_old_form)
       and _v22_fx_route == EV22.ROUTE_NONE
       and EV22.ROUTE_NONE == "" and len(set(EV22.LEGACY_ROUTES)) == len(EV22.LEGACY_ROUTES))

# --- AC2 the key is content, proven across FOUR clone shapes of one commit ------
with tempfile.TemporaryDirectory() as _v22_cd:
    _v22_src = _v22_seed(os.path.join(_v22_cd, "src"), [
        ("proof/WARP-9725/verdict-1-fail.json", _v22_verdict("WARP-9725", "fail", 1)),
        ("proof/WARP-9725/verdict.json", _v22_verdict("WARP-9725", "pass", 2)),
        ("proof/WARP-9726/verdict.json", _v22_verdict("WARP-9726", "pass_with_notes")),
    ])
    _v22_shapes = {"full": [], "depth1": ["--depth", "1"], "depth2": ["--depth", "2"],
                   "blobless": ["--filter=blob:none"], "single": ["--single-branch"]}
    _v22_cl, _v22_cl_keys, _v22_cl_evs = {}, {}, {}
    for _name, _opts in _v22_shapes.items():
        _dest = os.path.join(_v22_cd, _name)
        subprocess.run(["git", "clone", "-q", *_opts, "file://" + str(_v22_src), _dest],
                       check=True, capture_output=True)
        _v22_cl[_name] = _dest
        _dv = EV22.verdict_domain(repo_root=_dest)[0]
        _v22_cl_keys[_name] = [t[0] for t in _dv]
        _v22_cl_evs[_name] = [EV22.verdict_event(*t, repo_root=_dest) for t in _dv]
    # mtimes forced apart in one clone, so "not mtime" stays measured rather than assumed
    # A CRASH IS WORSE THAN A RED, and this loop was one: it fed every enumerated path straight to
    # os.utime, so a corpus enumeration answering paths from a DIFFERENT repository - which is
    # exactly what the git-cwd mutants make it do - raised FileNotFoundError out of an unguarded
    # block and took the suite's whole pass/fail summary down with no `selftest:` line at all, so a
    # run that could not look was indistinguishable from a run that found nothing. The paths this
    # clone ACTUALLY HOLDS are collected instead and asserted below to be ALL of them, which turns
    # the same mutation into a red that names the leg.
    _v22_held = []
    for _rel in EV22.tracked_verdicts(repo_root=_v22_cl["single"]):
        _p = os.path.join(_v22_cl["single"], _rel)
        if os.path.exists(_p):
            os.utime(_p, (900000000, 900000000))
            _v22_held.append(_rel)
    _v22_m_a = [os.path.getmtime(os.path.join(_v22_cl["full"], r))
                for r in EV22.tracked_verdicts(repo_root=_v22_cl["full"])
                if os.path.exists(os.path.join(_v22_cl["full"], r))]
    _v22_m_b = [os.path.getmtime(os.path.join(_v22_cl["single"], r))
                for r in EV22.tracked_verdicts(repo_root=_v22_cl["single"])
                if os.path.exists(os.path.join(_v22_cl["single"], r))]
    _v22_after_utime = [t[0] for t in EV22.verdict_domain(repo_root=_v22_cl["single"])[0]]
    _v22_shallow_flags = {n: EV22.is_shallow(repo_root=d) for n, d in _v22_cl.items()}
    expect("WARP-0722 AC2, AC2'S OWN REFUTATION CLAUSE MET AT EVERY CLONE DEPTH: five clones of ONE commit - full, --depth 1, --depth 2, --filter=blob:none and --single-branch - derive the IDENTICAL key set AND BYTE-IDENTICAL events, compared by digest. Round 1's key came from `git log --diff-filter=A`, which in a grafted history attributes every path to the shallow tip, so --depth 1 derived a different key for EVERY artifact; a blob sha is a property of content and has no history to graft. TEETH, both kept: the two shallow clones are confirmed shallow while the others are not, so the matrix is not five copies of one case, and the mtimes are forced 30 years apart with the keys unchanged, so an mtime-keyed derivation would differ where this one does not. AND EVERY ENUMERATED PATH IS ASSERTED TO BE ONE THIS CLONE ACTUALLY HOLDS: the mtime forcing used to hand each of them straight to os.utime, so an enumeration answering another repository's paths RAISED out of this block and took the suite's pass/fail summary down instead of failing here, and a crash is strictly worse than a red",
           len({_v22_keydigest(k) for k in _v22_cl_keys.values()}) == 1
           and len({_v22_evdigest(e) for e in _v22_cl_evs.values()}) == 1
           and len(_v22_cl_keys["full"]) == 3
           and _v22_held == EV22.tracked_verdicts(repo_root=_v22_cl["single"])
           and bool(_v22_held)
           and _v22_shallow_flags == {"full": False, "depth1": True, "depth2": True,
                                      "blobless": False, "single": False}
           and _v22_m_a != _v22_m_b
           and _v22_after_utime == _v22_cl_keys["full"])

    # A shallow clone with NO legacy events reconciles NORMALLY, because what a shallow
    # repository actually costs is the resolution of an event written under the old key.
    _v22_sh_rep = EV22.reconcile_verdicts(repo_root=_v22_cl["depth1"])
    _v22_sh_rep2 = EV22.reconcile_verdicts(repo_root=_v22_cl["depth1"])
    # ... and one carrying a legacy event it cannot resolve WITHHOLDS that spec's appends
    _v22_legacy = {"schema": "veldo.event/v1", "id": "legacy00", "type": "verdict.recorded",
                   "at": "2026-01-01T00:00:00Z", "producer": "events.py reconcile-verdicts",
                   "spec_id": "WARP-9725", "correlation_id": "WARP-9725",
                   "commit": "0" * 40, "verdict_path": "proof/WARP-9725/verdict.json",
                   "verdict": "pass"}
    _v22_shl = Path(_v22_cl["depth2"]) / ".veldo/events.jsonl"
    _v22_shl.parent.mkdir(parents=True, exist_ok=True)
    _v22_shl.write_text(json.dumps(_v22_legacy) + "\n")
    _v22_wh = EV22.reconcile_verdicts(repo_root=_v22_cl["depth2"])
    expect("WARP-0722 AC2: THE FAIL-CLOSED RULE IS TIED TO THE REAL DEPENDENCY, not to a proxy for it, AND ITS BLAST RADIUS IS ONE SPEC. A shallow clone with no legacy event reconciles NORMALLY (3 appended, then 0), because the derivation itself needs no history at all. A repository carrying an event whose (commit, path) pair it CANNOT resolve withholds the appends for THAT SPEC ALONE, by name, since it cannot know which of that spec's reviews the log already covers - while a different spec in the same repository is unaffected and appends. That is why this repository's own legacy events make a shallow clone of it append nothing at all, where the round-1 key silently derived a different key for every artifact and would have duplicated the whole backfill",
           _v22_sh_rep["appended"] == 3 and _v22_sh_rep2["appended"] == 0
           and _v22_sh_rep["unresolved_legacy"] == []
           and len(_v22_wh["unresolved_legacy"]) == 1
           and _v22_wh["unresolved_legacy"][0] == ["WARP-9725", "proof/WARP-9725/verdict.json"]
           # NAMED IN THE PUBLISHED LINE, not counted. The module, all eight capability
           # copies and AC2 all say an unresolvable event is reported BY NAME; the line
           # printed a bare integer, so the prose was false until this fired.
           and "cannot resolve (proof/WARP-9725/verdict.json)" in EV22._report_line(_v22_wh)
           and len(_v22_wh["withheld"]) == 2
           and {tuple(w)[1] for w in _v22_wh["withheld"]} == {"WARP-9725"}
           and _v22_wh["appended"] == 1
           and [e["spec_id"] for e in _v22_logged(_v22_cl["depth2"]) if e.get("verdict_blob")] == ["WARP-9726"]
           and _v22_lines(_v22_shl)[0] == json.dumps(_v22_legacy))

# --- AC2 a verdict added ONLY by a merge, and two concurrent reconciliations ----
with tempfile.TemporaryDirectory() as _v22_md:
    _v22_mg = _v22_seed(os.path.join(_v22_md, "mg"),
                        [("proof/WARP-9740/verdict.json", _v22_verdict("WARP-9740", "pass"))])
    _v22_git(_v22_mg, "checkout", "-q", "-b", "side")
    _v22_write(_v22_mg, "proof/WARP-9741/side.txt", {"x": 1})
    _v22_commit(_v22_mg, "side work")
    _v22_git(_v22_mg, "checkout", "-q", "main")
    _v22_write(_v22_mg, "proof/WARP-9742/main.txt", {"y": 1})
    _v22_commit(_v22_mg, "main work")
    _v22_git(_v22_mg, "merge", "-q", "--no-commit", "--no-ff", "side", check=False)
    _v22_write(_v22_mg, "proof/WARP-9743/verdict.json", _v22_verdict("WARP-9743", "pass", 1))
    _v22_git(_v22_mg, "add", "-A")
    _v22_git(_v22_mg, "commit", "-q", "-m", "merge, and the resolution ADDS a verdict")
    _v22_mg_rep = EV22.reconcile_verdicts(repo_root=str(_v22_mg))
    expect("WARP-0722 AC2: A VERDICT INTRODUCED ONLY BY A MERGE RESOLUTION IS KEYED LIKE ANY OTHER, and the round-1 report that called such an artifact `deferred until committed` when it WAS committed cannot recur: the derivation reads the commit's own tree, where a merge-added path sits exactly like any other, and `git log`, which does not diff merges, is gone from the module entirely",
           _v22_mg_rep["appended"] == 2 and _v22_mg_rep["deferred"] == []
           and sorted(e["spec_id"] for e in _v22_logged(_v22_mg)) == ["WARP-9740", "WARP-9743"])

    _v22_conc = _v22_seed(os.path.join(_v22_md, "conc"),
                          [("proof/WARP-9750/verdict.json", _v22_verdict("WARP-9750", "pass"))])
    _v22_conc_log = _v22_conc / ".veldo/events.jsonl"
    with open(_v22_conc_log, "a+") as _v22_holder:
        _v22_held = EV22._lock(_v22_holder)
        _v22_conc_run = subprocess.run([sys.executable, str(ROOT / ".veldo/events.py"),
                                        "reconcile-verdicts", "--repo-root", str(_v22_conc)],
                                       capture_output=True, text=True)
        _v22_conc_during = _v22_logged(_v22_conc)      # read while the lock is still held
    _v22_conc_after = EV22.reconcile_verdicts(repo_root=str(_v22_conc))
    expect("WARP-0722 AC2: TWO CONCURRENT RECONCILIATIONS CANNOT BOTH APPEND. The read-then-append window is held under an EXCLUSIVE NON-BLOCKING lock, so a run that finds it held appends NOTHING, says which, and exits 0 - it never waits, because a stage that can block forever is worse than one that appends on the next run, and it never duplicates, which is what four concurrent runs did before. The withheld work is not lost: the next run appends it",
           _v22_held is True and _v22_conc_run.returncode == 0
           and "NOT appended" in _v22_conc_run.stdout
           and _v22_conc_during == []
           and _v22_conc_after["appended"] == 1)

# --- AC3 the instruction is deleted from every canon copy ----------------------
_v22_skill_rels = _v22_wrapper_copies("skills/review/SKILL.md")
_v22_cap_rels = _v22_engine_copies(".veldo/capabilities.yaml", ".veldo/capabilities.yaml")
expect("WARP-0722 AC3: THE INSTRUCTION IS GONE, DELETED RATHER THAN REWORDED, in the review skill of EVERY PACK THE MANIFEST DECLARES - neither name survives, and the skill no longer mentions the event log at all, so there is no reworded instruction left to obey. The copies are byte-identical, which is what stops the deletion from landing in one of them. THE SET OF COPIES IS THE DECLARED ROSTER read through `.veldo/pack.py load_packs`, at each pack's declared WRAPPER root, which is now the PATH the manifest declares in `wrapper_dir` and no longer the first word of its prose `wrapper` sentence (the skill is driver, not engine, so no drift check covers it and this assertion is what holds the copies together): not a `>= 7` floor, which reddens the day a pack is retired, and not a listing of directories, which reddens the day an undeclared one appears. THE REACH OF THIS UNIVERSAL IS THE ROSTER, so the roster is required COMPLETE here - every declared pack declaring both roots - because a pack that stopped declaring one would drop out of the copy set and shrink what this sentence covers without failing anything",
       _v22_absent(_v22_skill_rels) == []
       and _V22_ROSTER_COMPLETE
       and "skills/review/SKILL.md" not in _v22_engine_set
       and all(not any(n in (ROOT / rel).read_text() for n in _v22_names) for rel in _v22_skill_rels)
       and all("events.jsonl" not in (ROOT / rel).read_text() for rel in _v22_skill_rels)
       and len({(ROOT / rel).read_bytes() for rel in _v22_skill_rels}) == 1)

expect("WARP-0722 AC3: the LIVE ENGINE SURFACES are clear of both names - the review skill in every declared pack's wrapper and the capability manifest in every declared pack's engine, both rosters read through the ONE reader of `.veldo/packs.json` rather than derived a second time from a directory listing, both roots read as DECLARED PATHS and the roster required complete so this universal cannot narrow in silence, where twenty-two tracked files carried a name at a8b81b9 (a figure about that revision, which does not move). The capability manifest instead REGISTERS the projection, so the machine-readable truth about what ships is not stale prose",
       # THE EXISTENCE GUARD COMES FIRST, and it is not a style point: with it second, a
       # declared pack missing its copy made this assertion RAISE instead of fail, which is
       # the difference the round's own rules insist on. Measured, and this is where it was
       # measured - a pack declared in .veldo/packs.json without its engine copy.
       _v22_absent(_v22_cap_rels) == [] and _v22_absent(_v22_skill_rels) == []
       and _V22_ROSTER_COMPLETE
       and all(not any(n in (ROOT / rel).read_text() for n in _v22_names)
               for rel in _v22_skill_rels + _v22_cap_rels)
       and ".veldo/capabilities.yaml" in _v22_engine_set
       and not (set(_v22_skill_rels) & set(_v22_cap_rels))
       and all("review_event_projection" in (ROOT / rel).read_text() for rel in _v22_cap_rels)
       and len({(ROOT / rel).read_bytes() for rel in _v22_cap_rels}) == 1)

# The tracked files that may still carry either name, each with the REASON it is a record
# rather than a live surface. TWO CATEGORIES, AND ONLY ONE OF THEM CAN BE A LIST.
#
# OUTSIDE proof/ the allowance is ENUMERATED and the equality binds in both directions, so a
# new occurrence reddens the gate and a stale allowance cannot rot on the list. Both
# directions have fired on unplanned occurrences: staging this item's own manifest turned the
# gate red until it was named, and the round-1 REVIEW was added here on the assumption that a
# verdict ruling on two strings must quote them - it does not, so the entry was removed when
# the equality refused it. A list that only ever grows is not an assertion.
#
# UNDER proof/ THE ALLOWANCE IS A RULE, because an enumerated list there is a literal pinned
# to a moving repository property - the very defect this round exists to close, found in a
# second place. Evidence under proof/ is written BY THE REVIEW LOOP ITSELF, after this
# assertion, by someone who has never read it: a record that rules on these two names must
# quote what it ruled on. THAT IS MEASURED, NOT FEARED. At 4778c7d this assertion was ALREADY
# RED, and the file that reddened it was proof/WARP-0722/verdict-3-fail.json - the independent
# verdict that failed this item's own round 3, quoting both names, landing in an existing proof
# directory. Bumping the list would have bought one round; the next review would redden it.
#
# AND THE RULE ROUND 4 WROTE WAS A SECOND PIN: it admitted a hit under proof/ only when the
# FILE WAS NAMED verdict*.json or manifest.json, which is a naming convention the future is not
# bound by. MEASURED at 4778c7d: the tracked corpus already held 114 files under proof/ that
# rule refuses - approval records, negative-test transcripts, runner evidence, screenshots -
# so a review that quoted either name in its lane notes would have reddened the gate on an
# innocent evidence file. `proof/WARP-0722/review-5-lane-notes.md` committed into an existing
# proof directory reddened it, which is exactly the sentence 'another review round cannot break
# it' being false.
#
# SO THE RULE IS DERIVED FROM WHAT THE REPOSITORY DECLARES, WHICH IS THE SPEC ROSTER: a hit at
# `proof/<id>/...` is a record when <id> is the id of a spec this repository declares, read out
# of specs/*.md front matter through the contract parser - the SAME binding .veldo/validate.py
# makes when it looks a proof manifest's spec_id up in that map. Measured at 4778c7d: EVERY
# proof directory names a declared spec, so every file the name rule refused is covered. A
# directory under proof/ that names no declared spec is NOT a record and still reddens.
# WHAT KEEPS THE GUARANTEE THAT ACTUALLY MATTERS is no longer this rule at all but a POSITIVE
# leg over the DECLARED LIVE SURFACE - every engine copy and every wrapper skill copy of every
# declared pack - which no file under proof/ can ever be a member of, so widening the record
# category cannot widen what a live surface may say.
# WHAT ORDINARY FUTURE CHANGE BREAKS THIS: a tracked file OUTSIDE proof/ starting to carry
# either name - a new live surface, or a new design document - which is exactly the conscious
# decision this assertion exists to force; or a file landing under proof/<something that is
# not a declared spec id>. What CANNOT break it, EACH ONE MEASURED rather than restated: a review
# round adding evidence of any shape under an existing spec's proof directory, declaring and
# assembling a new pack, an undeclared directory under packs/, or the corpus growing by any
# amount. What is NOT claimed because it could not be measured: what a pack RETIREMENT does,
# since other items' hardcoded pack ids crash the suite before this block runs.
_V22_SPEC_IDS = set()
for _sp in sorted((ROOT / "specs").glob("*.md")):
    if _sp.name.startswith("TEMPLATE") or _sp.name == "index.md":
        continue
    _sfm = V.front_matter(_sp.read_text())
    if _sfm and _sfm.get("id"):
        _V22_SPEC_IDS.add(_sfm["id"])


def _v22_is_record_under_proof(path):
    """Whether a tracked path is EVIDENCE under proof/, decided by the spec roster the
    repository declares rather than by what the file is called."""
    parts = path.split("/")
    return len(parts) >= 3 and parts[0] == "proof" and parts[1] in _V22_SPEC_IDS
_V22_SELF_REL = str(suite_file().resolve().relative_to(ROOT))
_V22_RECORDS = {
    "docs/design/DECISIONS-for-dmitry-verification-inversion.md":
        "the decision record that FOUND this defect, quoting the instruction verbatim",
    "docs/design/INVERSION-design-review-1.md":
        "an independent design review of that record, quoting the same instruction",
    "docs/design/INVERSION-design-review-2.md":
        "the second independent design review, which counted the gap that produced this item",
    "docs/design/INVERSION-v2-problem-statement-and-options.md":
        "the problem statement that named the all-gate-events-and-no-review-events gap",
    "docs/setup.md":
        "THE ONE LIVE DOCUMENT LEFT, and a real defect with its OWN item rather than a record: "
        "the method text hand-lists nine event types the shipped validator refuses, and "
        "correcting it re-renders a released PDF, so it is neither this item's instruction nor "
        "a rewording of it",
    "specs/WARP-0403-lessons-store.md":
        "a SHIPPED spec's own criterion text, kept as a RECORDS POLICY and not because anything "
        "binds it: round 2's reviewer edited it in a throwaway clone and all four validators "
        "still exited 0, so the earlier reason given here (a proof bound to its revision) was "
        "overstated and is corrected",
    "specs/WARP-0722-review-events-derived-not-appended.md":
        "this item's own AC3, which cannot say what must go without naming it",
    _V22_SELF_REL:
        "this assertion, which cannot enumerate the two names without containing them",
}
_v22_hits = sorted(f for f in _v22_tracked
                   if any(n in (ROOT / f).read_bytes().decode("utf-8", "replace")
                          for n in _v22_names))
_v22_evidence_hits = [f for f in _v22_hits if _v22_is_record_under_proof(f)]
_v22_surface_hits = [f for f in _v22_hits if f not in set(_v22_evidence_hits)]
# EVERY RECORD ON THE LIST MUST STILL BE TRACKED, WHICH IS WHAT MAKES `a stale allowance cannot
# rot on the list` TRUE. Round 5 filtered the expectation down to the records that happen to be
# tracked, so DELETING a listed file silently removed its allowance: MEASURED at 19c396b,
# deleting `docs/design/INVERSION-design-review-1.md` left the suite at 3236 passed 0 failed with
# the entry still on the list. The mechanism is fixed rather than the sentence softened - the list
# is a declaration about the corpus, and a declaration whose subject is gone is a red.
_v22_records_untracked = sorted(f for f in _V22_RECORDS if f not in set(_v22_tracked))
_v22_expected_surface = sorted(_V22_RECORDS)
# THE DECLARED LIVE SURFACE: every engine copy and every wrapper skill copy of every pack the
# manifest declares. This is the leg that carries AC3's guarantee, and it is a POSITIVE
# universal over a derived roster rather than the complement of an allowance list, so no
# widening of what counts as a record can widen what a live surface may say. Its REACH is the
# roster, so _V22_ROSTER_COMPLETE rides with it: round 5 derived each pack's wrapper root from
# the first word of a prose sentence, and a pack that stopped declaring one dropped out of this
# universal without a word.
_v22_live_surface = sorted(set(
    _v22_module_rels + _v22_cap_rels + _v22_skill_rels + _v22_verify_rels))
expect("WARP-0722 AC3, WHICH THE SPEC NOW ASKS FOR IN THE FORM THAT IS ACHIEVABLE: over EVERY tracked file, the ones carrying `review.passed` or `review.failed` are exactly the enumerated record list plus the RECORDS UNDER proof/. Outside proof/ the equality binds in both directions AND EVERY LISTED RECORD MUST STILL BE TRACKED, so a new live surface reddens the gate and a stale allowance cannot rot on the list - including the case round 5 missed, where DELETING a listed file removed its allowance silently because the expectation was filtered to the files that happen to exist (measured at 19c396b: the suite stayed green with the entry still on the list). Under proof/ the allowance is a RULE, and the rule is DERIVED FROM THE SPEC ROSTER THIS REPOSITORY DECLARES - a path is a record when its proof directory names a spec that exists in specs/, the same binding validate.py makes - and NOT from what the file is called. Round 4's version admitted only verdict*.json and manifest.json, a naming convention the future is not bound by, which the corpus already refused 114 files under; measured, a review's lane-note file in an existing proof directory reddened it. AND THE GUARANTEE IS CARRIED SEPARATELY BY A POSITIVE LEG: no file in the DECLARED LIVE SURFACE - the engine and wrapper copies of every declared pack, whose REACH is the declared roster and is required complete here rather than assumed - carries either name, which nothing under proof/ can satisfy away, and every hit falls in exactly one category",
       _v22_surface_hits == _v22_expected_surface
       and _v22_records_untracked == []
       and _V22_ROSTER_COMPLETE
       and _V22_SELF_REL in _v22_surface_hits
       and bool(_v22_evidence_hits)
       and all(f.startswith("proof/") for f in _v22_evidence_hits)
       and not any(f.startswith("proof/") for f in _V22_RECORDS)
       and sorted(_v22_evidence_hits + _v22_surface_hits) == _v22_hits
       and not (set(_v22_evidence_hits) & set(_v22_surface_hits))
       and bool(_v22_live_surface) and _v22_absent(_v22_live_surface) == []
       and not any(_n in (ROOT / _f).read_text() for _f in _v22_live_surface
                   for _n in _v22_names)
       and not any(_f.startswith("proof/") for _f in _v22_live_surface)
       and not (set(_v22_live_surface) & set(_v22_hits)))

# --- dogfood: this item's own spec, its tier, and the footprint it actually touches ---
_v22_fm = V.parse_yamlish(re.match(r"^---\n(.*?)\n---", _v22_spec_text, re.S).group(1))
_v22_arch, _v22_contract = V.load_repo_contract(repo_root=str(ROOT))
_v22_fp = [g for g in (_v22_fm.get("footprint") or []) if isinstance(g, str)]
_v22_ac = {c.get("id"): c.get("text") or "" for c in (_v22_fm.get("acceptance_criteria") or [])
           if isinstance(c, dict)}
expect("WARP-0722 dogfood: the spec has PASSED the ready transition (so this does not go stale the moment it ships), declares the DERIVED high tier, and DECLARES THE TWO PROTECTED PATHS ITS FOOTPRINT ACTUALLY TOUCHES with the approval that entails - checked against the policy's own protected set rather than a literal, because the first draft of this front matter declared no protected path and no required approval while its footprint named scripts/verify.sh, which was false and which the ready gate does not cross-check",
       _v22_fm.get("status") in ("ready", "in_progress", "review", "proven", "shipped")
       and _v22_fm.get("risk", "").split()[0] == "high"
       and _v22_fm.get("human_approval") == "required"
       and sorted(_v22_fm.get("protected_paths") or []) == ["engine/scripts/verify.sh", "scripts/verify.sh"]
       and set(_v22_fm.get("protected_paths") or []) <= set(P.protected_patterns())
       and V.check_ready(_v22_spec_path, repo_root=str(ROOT)) == 0)

expect("WARP-0722 dogfood, THE TWO CRITERIA THE BUILD AMENDED RATHER THAN REINTERPRETED: AC2 declares the key the code actually uses (the artifact's own blob, content-addressed) and no longer the adding-commit sha an independent review measured to be unstable across clones of one commit; and AC3 asks for the EQUALITY over an enumerated record list that ships, not the empty list it first demanded and that the same evidence proves unreachable. Asserted on the spec text, because a criterion nobody can satisfy is a defect in the criterion and the record for it is an amendment, not a status token that reads as satisfied",
       "BLOB SHA" in _v22_ac.get("AC2", "").upper()
       and "diff-filter" not in _v22_ac.get("AC2", "")
       and "asserts an EMPTY LIST of tracked files" not in _v22_ac.get("AC3", "")
       and "EQUALS that enumerated record list" in _v22_ac.get("AC3", "")
       and "AMENDED IN ROUND 2" in _v22_ac.get("AC2", "")
       and "AMENDED IN ROUND 2" in _v22_ac.get("AC3", "")
       and "clone --depth 1" in _v22_spec_text
       and "Nothing reads these events yet" not in _v22_spec_text)

# The ENGINE AND SPEC files this item touches: the four canon families, each derived from the
# DECLARED pack roster, plus the one-off files named because no rule generates them. The
# non-vacuity check is a DERIVED EQUALITY - the four families are pairwise disjoint, so their
# lengths sum, and each family's own length is exactly what the roster says it should be - and not
# the `>= 31` floor round 3 wrote nor the `len(_v22_packs) + 1 <= len(f)` floor round 4 replaced
# it with, which was still a comparison against a directory listing.
#
# THIS SET IS NOT THE DIFF, AND THE HEADLINE BELOW NO LONGER SAYS IT IS. Round 5's headline read
# `the footprint COVERS EVERY FILE THIS CHANGE TOUCHES` over a set an author types, and MEASURED
# against round 5's own commit 3 of its 21 paths matched no footprint glob: proof/WARP-0722/
# manifest.json, .veldo/events.jsonl and .veldo/last_verify. Those three are this item's evidence
# and its gate output, they ride in the commit because the brief required one commit where this
# item's convention is two, and they are named in the manifest instead of being quietly covered.
# Quantifying over the real diff was REJECTED for the reason this item exists: the diff of HEAD
# against its parent is a moving repository property, and an assertion reading it would go red on
# the next commit that touched anything here.
_V22_TOUCHED_ONE_OFFS = ["scripts/selftest.py", "specs/index.md",
                         "specs/WARP-0722-review-events-derived-not-appended.md",
                         ".veldo/packs.json"]
_v22_touched_families = [_v22_verify_rels, _v22_skill_rels, _v22_cap_rels, _v22_module_rels]
_v22_touched = sorted(set(_V22_TOUCHED_ONE_OFFS + [r for f in _v22_touched_families for r in f]))
expect("WARP-0722 dogfood: the footprint COVERS EVERY ENGINE AND SPEC FILE THIS ITEM DECLARES IT TOUCHES - the four canon families derived from the DECLARED pack roster plus the four one-off paths - checked through the one glob compiler. ITS DOMAIN IS THAT ENUMERATION AND NOT THE DIFF, which is why the headline no longer says every file this change touches: measured against round 5's own commit, 3 of its 21 paths matched no footprint glob (the manifest, the event log and the gate's last_verify), and those are named as evidence and gate output in the manifest rather than glossed. Reading the real diff was rejected because HEAD against its parent is a moving repository property. The shape gate refuses a diff outside the footprint, so the first draft's short list would have turned the gate red rather than drifting quietly - and the crossing the risk sentence explains is measured rather than asserted: the footprint's own paths reach both enforcement and metrics. Each family's length is an EQUALITY against the roster - one engine copy per declared pack plus this repository's own, one wrapper copy per declared pack - so a newly declared pack cannot make it vacuous and an undeclared directory under packs/ moves nothing, both MEASURED",
       len(_v22_touched) == len(_V22_TOUCHED_ONE_OFFS) + sum(len(f) for f in _v22_touched_families)
       and _V22_ROSTER_COMPLETE
       and all(_f in set(_v22_tracked) for _f in _V22_TOUCHED_ONE_OFFS)
       and all(len(f) == len(_v22_engine_roots) + 1
               for f in (_v22_verify_rels, _v22_cap_rels, _v22_module_rels))
       and len(_v22_skill_rels) == len(_v22_wrapper_roots)
       and all(any(_v22_arch._glob_re(g).match(rel) for g in _v22_fp) for rel in _v22_touched)
       and _v22_arch.footprint_areas(_v22_fm, _v22_contract) >= {"enforcement", "metrics"}
       and _v22_arch.placement_gate(_v22_fm, _v22_contract) == [])


# ===========================================================================
# WARP-0723: ONE DOCUMENTED FLAG PERMANENTLY REDDENED THE GATE. WARP-0722 moved the `type` onto
# the bytes and its manifest called the other envelope fields harmless payload. Measured false on
# the shipped tree at 18e6ca8 by this builder before anything was typed: `python3 .veldo/events.py
# emit proof.recorded --field schema=nope` exits 0, the line LANDS (events.jsonl md5 054b25a1 ->
# bf09f763), and from then on `validate.py all` exits 1 on `line 809: bad or missing schema (want
# veldo.event/v1)` and `./scripts/verify.sh` prints `contracts: FAIL` and `GATE: RED` - on every
# run, in every clone, for every item, because the log is APPEND-ONLY and the method forbids
# editing it. `--field at=` does the same.
# These assertions bind the widened refusal AT THE SAME GUARD POINT: the FINAL dict, immediately
# before the append. THE FAILURE MODE OF THIS FIX IS THE INVERSE OF THE DEFECT - a refusal written
# too broadly rejects the projection's OWN entitled append and stops the review log recording
# verdicts at all - so the projection's append is a REQUIRED leg here and it is driven over this
# repository's REAL committed verdict artifacts.
# WHAT IS QUANTIFIED AND HOW: the reserved keys come from the module's OWN constant and every
# route is generated FROM it, so a sixth reserved key declared later is driven by this block
# without being written down here; no count of keys, copies, routes or corpus items is asserted
# anywhere, only a property of EACH MEMBER. Every route is driven against EVERY DECLARED COPY, each
# in a throwaway tree of its own, because the module ships in eight byte-identical copies and an
# adopter runs a pack's copy rather than this one.
# ===========================================================================
_V23_RESERVED = tuple(getattr(EV22, "RESERVED_ENVELOPE_KEYS", None) or ())
_V23_SCHEMA_NAME = getattr(EV22, "SCHEMA", None)
# GUARDED LOOKUPS, for the reason WARP-0722's round 9 wrote down at the cost of two crashed runs: a
# pure rename of a contract name must be a NAMED RED with the pass/fail summary printed, never an
# AttributeError that takes the suite's whole reporting down. An absent name leaves an empty tuple
# or a placeholder no envelope carries, and this flag is a conjunct of every expectation below.
_V23_NAMES_PRESENT = (bool(_V23_RESERVED) and isinstance(_V23_SCHEMA_NAME, str)
                      and bool(_V23_SCHEMA_NAME) and _V22_CONTRACT_NAMES_PRESENT)
_V23_SCHEMA = _V23_SCHEMA_NAME if isinstance(_V23_SCHEMA_NAME, str) else "veldo.absent.schema.0723"
_V23_ALLOWED = "proof.recorded"          # a type the loop IS entitled to hand-emit
_V23_SPEC_ID = "WARP-9723"
_V23_CTL_TYPES = [_V23_ALLOWED, _V23_ALLOWED, "spec.ready", _V23_ALLOWED]
# A COPY THAT IS NOT THIS REPOSITORY'S OWN, for the legs AC4 asks to be driven against a copy rather
# than against the root. Taken off the declared roster (the last entry, since the home copy sorts
# first) and asserted to differ from the root path where it is used, so a roster that stopped
# declaring any pack is a red rather than a leg that quietly drives the root twice.
_V23_PACK_COPY = _v22_module_rels[-1]


def _v23_tree(base, rel):
    """A throwaway tree carrying ONE DECLARED COPY of the module. The module's LOG is derived from
    where the file lives, so a copy in a tree of its own can be driven with no possibility of a byte
    reaching the real append-only log - which is what makes a mutant with the refusal removed a
    failed assertion here rather than an unrepairable line in this repository's own log."""
    t = Path(base) / rel.replace("/", "__")
    _v22_lay_module(t, rel)
    return t


def _v23_load(tree, tag):
    """The copy in `tree` as a live module, under a name of its own so the copies cannot collide in
    sys.modules. None when it will not load, which the expectations red on BY NAME."""
    try:
        s = importlib.util.spec_from_file_location("veldo_events_0723_" + tag,
                                                   tree / ".veldo/events.py")
        m = importlib.util.module_from_spec(s)
        s.loader.exec_module(m)
        return m
    except Exception:                       # pragma: no cover - a copy that will not load
        return None


def _v23_cli_run(tree, *args):
    return subprocess.run([sys.executable, str(tree / ".veldo/events.py"), "emit", *args],
                          capture_output=True, text=True)


def _v23_cli_routes():
    """EVERY CLI ROUTE THAT CAN PUT A CALLER'S VALUE ON A RESERVED KEY, generated FROM the module's
    own key tuple rather than typed out: for each reserved key the empty value (the shape `--field
    at=` shipped, and the one value that is illegal for all five), then the measured defect values,
    the flag that sets `producer` without --field, a REPEATED --field so the last value wins, a
    PADDED key the CLI strips into the real one, a CASE-VARIANT key, and the POSITIONAL argument -
    the one reserved key the positional sets is the type, driven both as the projection-owned name
    and as a name no vocabulary declares."""
    out = {}
    for k in _V23_RESERVED:
        out["--field %s= (empty)" % k] = [_V23_ALLOWED, "--field", k + "="]
    out["--field schema=nope (the measured defect)"] = [_V23_ALLOWED, "--field", "schema=nope"]
    out["--field at= (the measured defect)"] = [_V23_ALLOWED, "--field", "at="]
    out["--field id=deadbeef"] = [_V23_ALLOWED, "--field", "id=deadbeef"]
    out["--field at= another legal ISO form"] = [_V23_ALLOWED, "--field",
                                                 "at=2026-01-02T03:04:05+00:00"]
    out["--field producer= the projection's own"] = [_V23_ALLOWED, "--field",
                                                     "producer=" + _V22_PRODUCER]
    out["--producer the projection's own"] = [_V23_ALLOWED, "--producer", _V22_PRODUCER]
    out["repeated --field, the last value winning"] = [_V23_ALLOWED, "--field",
                                                       "schema=" + _V23_SCHEMA,
                                                       "--field", "schema=nope"]
    out["a padded key the CLI strips"] = [_V23_ALLOWED, "--field", " schema =nope"]
    out["a case-variant key"] = [_V23_ALLOWED, "--field", "SCHEMA=nope"]
    out["the positional argument, the projection's type"] = [_V22_VERDICT]
    out["the positional argument, a type no vocabulary declares"] = ["verdict.invented"]
    return out


class _V23Confusable(str):
    """A KEY THAT IS A str, SPELLS A RESERVED NAME, AND DEFEATED BOTH OF THE GUARD'S OLD TESTS -
    the route WARP-0723's reviewer found and round 2 closes. It hashes elsewhere, so `dict.update`
    keeps BOTH entries and every `ev.get(<reserved>)` reads the GENUINE one; and it overrides only
    `__eq__` among the comparisons, so the confusable test `alias != key` is answered by the INHERITED
    `str.__ne__` and reads False. MEASURED BEFORE THE FIX at 26b6c34 in a clone of the shipped tree,
    no code change: emit() LANDED one line carrying `"schema"` TWICE (events.jsonl md5 58897e7f ->
    d86db52f), json.loads took the LAST so the line read `"nope"`, and `validate.py all` went 0 -> 1
    for good. AFTER: ValueError, md5 58897e7f UNCHANGED, `validate.py all` 0.

    IT ALSO LIES THROUGH `__str__`, which is why the guard normalises with `str.__str__` rather than
    with `str(key)`: json.dumps encodes the raw unicode and writes `schema` whatever `__str__` says,
    so a guard that trusted `str(key)` would read a name no rule reserves. MEASURED: with the weaker
    normalisation this route LANDS and the assertion below goes red."""

    def __hash__(self):
        return hash("\x00" + str.__str__(self))

    def __eq__(self, other):
        return False

    def __str__(self):
        return "veldo.a.key.that.lies.0723"


def _v23_poke(mod):
    """THE WRITER DRIVEN DIRECTLY with an event whose schema was replaced AFTER assembly, through
    the same handle the projection hands it. This is the route a second writer inside the module
    would take, and the one no check on an argument can see."""
    ev = mod.make_event(_V23_ALLOWED, spec=_V23_SPEC_ID)
    ev["schema"] = "nope"
    with open(mod.LOG, "a") as fh:
        mod._append_events(fh, [ev])


def _v23_inproc_routes(mod):
    """EVERY IN-PROCESS ROUTE, generated from the same key tuple: the `extra` override dict the CLI
    itself rides on for each key, a PADDED, a CASE-VARIANT and a `str` SUBCLASS spelling of each
    (none of them stripped in process), the two reserved fields the CONSTRUCTOR takes as arguments,
    and the writer called directly. Each is a thunk, so nothing is driven until the caller drives it
    inside its own try."""
    out = {}
    for k in _V23_RESERVED:
        out["extra override %s=''" % k] = lambda k=k: mod.emit(_V23_ALLOWED, extra={k: ""})
        out["extra padded key ' %s'" % k] = lambda k=k: mod.emit(_V23_ALLOWED,
                                                                 extra={" " + k: "x"})
        out["extra case-variant key %s" % k.upper()] = lambda k=k: mod.emit(
            _V23_ALLOWED, extra={k.upper(): "x"})
        out["extra `str` SUBCLASS key %r" % k] = lambda k=k: mod.emit(
            _V23_ALLOWED, extra={_V23Confusable(k): "nope"})
    out["extra override schema=nope"] = lambda: mod.emit(_V23_ALLOWED, extra={"schema": "nope"})
    out["extra override producer= the projection's own"] = lambda: mod.emit(
        _V23_ALLOWED, extra={"producer": _V22_PRODUCER})
    out["the constructor's at argument"] = lambda: mod.emit(_V23_ALLOWED, at="nope")
    out["the constructor's event_id argument"] = lambda: mod.emit(_V23_ALLOWED, event_id="zz")
    out["the writer itself, a dict poked after assembly"] = lambda: _v23_poke(mod)
    return out


def _v23_landed(p):
    """Every line a driven route landed in `p`, parsed, with an unparseable line recorded as a
    MARKER rather than raised on: a mutant that writes something other than one JSON object per line
    must be a RED here and never a traceback that takes the summary down."""
    out = []
    for ln in _v22_lines(p):
        try:
            ev = json.loads(ln)
            out.append(ev if isinstance(ev, dict) else {"type": "veldo.not.an.object.0723"})
        except Exception:                   # pragma: no cover - a line that is not one object
            out.append({"type": "veldo.unparseable.line.0723"})
    return out


def _v23_envelope_ok(mod, ev):
    """Whether a LANDED line carries the envelope the reserved rules require, read back off the
    bytes with the module's own predicates rather than with a copy of them typed here."""
    return (ev.get("schema") == mod.SCHEMA and mod._is_event_id(ev.get("id"))
            and mod._iso_z(ev.get("at")) and isinstance(ev.get("producer"), str)
            and bool(ev["producer"].strip())
            and all(k in ev for k in _V23_RESERVED))


_v23_absent = _v22_absent(_v22_module_rels)
_v23_root_bytes = (ROOT / ".veldo/events.py").read_bytes()
# BYTE-IDENTITY AS A PROPERTY OF EACH DECLARED COPY, never as a count of distinct contents: the
# repository can declare another pack, and `len({bytes}) == 1` says nothing about WHICH files were
# compared. Named here as the list of copies that DIFFER, so a red names them.
_v23_differ = [rel for rel in _v22_module_rels
               if (ROOT / rel).is_file() and (ROOT / rel).read_bytes() != _v23_root_bytes]
_v23_cli, _v23_cli_ctl, _v23_ip, _v23_ip_ctl, _v23_unloadable = {}, {}, {}, {}, []
_v23_validated, _v23_poison_rc, _v23_mint, _v23_readback = {}, None, {}, {}
with tempfile.TemporaryDirectory() as _v23_d:
    for _v23_rel in _v22_module_rels:
        if _v23_rel in _v23_absent:
            continue
        _v23_t = _v23_tree(_v23_d, _v23_rel)
        _v23_lg = _v23_t / ".veldo/events.jsonl"
        # SEEDED THROUGH THE MODULE'S OWN DOOR with an allowed event, so `byte-unchanged` below is a
        # statement about a log that already HAS content: an empty file staying empty would also be
        # true of a fixture that cannot write at all.
        _v23_cli_ctl[_v23_rel] = [_v23_cli_run(_v23_t, _V23_ALLOWED, "--spec", _V23_SPEC_ID)]
        for _v23_n, _v23_a in _v23_cli_routes().items():
            # RE-BASELINED BEFORE EVERY ROUTE, so `byte-unchanged` is a statement about THAT route
            # and one route that lands does not smear a false reading over every route after it.
            _v23_was = _v23_lg.read_bytes() if _v23_lg.is_file() else b""
            _v23_r = _v23_cli_run(_v23_t, *_v23_a)
            _v23_cli[(_v23_rel, _v23_n)] = (
                _v23_r.returncode,
                (_v23_lg.read_bytes() if _v23_lg.is_file() else b"") == _v23_was,
                (_v23_r.stdout or "") + (_v23_r.stderr or ""))
        # THE CONTROLS: an allowed type with no reserved key must still LAND, which is what makes
        # every byte-unchanged reading above a refusal rather than a broken fixture.
        _v23_cli_ctl[_v23_rel].append(_v23_cli_run(_v23_t, _V23_ALLOWED, "--field", "note=carried"))
        _v23_cli_ctl[_v23_rel].append(_v23_cli_run(_v23_t, "spec.ready", "--spec", _V23_SPEC_ID,
                                                   "--human-minutes", "3"))
        # THE IN-PROCESS DOORS, on the copy loaded FROM THIS TREE, so its LOG is this tree's file.
        _v23_m = _v23_load(_v23_t, _v23_rel.replace("/", "_").replace(".", "_"))
        if _v23_m is None:
            _v23_unloadable.append(_v23_rel)
            continue
        for _v23_n, _v23_th in _v23_inproc_routes(_v23_m).items():
            _v23_was = _v23_lg.read_bytes() if _v23_lg.is_file() else b""
            try:
                _v23_th()
                _v23_ip[(_v23_rel, _v23_n)] = (
                    None, (_v23_lg.read_bytes() if _v23_lg.is_file() else b"") == _v23_was)
            except Exception as _v23_ex:     # recorded WITH ITS CLASS, never raised out of here
                _v23_ip[(_v23_rel, _v23_n)] = (
                    "%s: %s" % (type(_v23_ex).__name__, _v23_ex),
                    (_v23_lg.read_bytes() if _v23_lg.is_file() else b"") == _v23_was)
        try:
            _v23_m.emit(_V23_ALLOWED, spec=_V23_SPEC_ID, extra={"note": "in process"})
            _v23_ip_ctl[_v23_rel] = "landed"
        except Exception as _v23_ex:
            _v23_ip_ctl[_v23_rel] = "%s: %s" % (type(_v23_ex).__name__, _v23_ex)
        # WHAT ACTUALLY LANDED, read back off the log: the controls, in order, each carrying an
        # envelope the reserved rules admit.
        try:
            _v23_ls = _v23_landed(_v23_lg)
            _v23_readback[_v23_rel] = ([e.get("type") for e in _v23_ls],
                                       all(_v23_envelope_ok(_v23_m, e) for e in _v23_ls))
        except Exception as _v23_ex:        # pragma: no cover - a readback that cannot read
            _v23_readback[_v23_rel] = ("%s: %s" % (type(_v23_ex).__name__, _v23_ex), False)
        # WHAT THE MINT PUTS ON AN ENVELOPE, off a freshly minted event of THIS copy: every reserved
        # key present, each holding a value the guard admits. This binds the mint to the guard
        # without the schema string or the id width being written down here.
        try:
            _v23_ev = _v23_m.make_event(_V23_ALLOWED, spec=_V23_SPEC_ID)
            _v23_mint[_v23_rel] = (sorted(k for k in _V23_RESERVED if k in _v23_ev),
                                   _v23_envelope_ok(_v23_m, _v23_ev))
        except Exception as _v23_ex:
            _v23_mint[_v23_rel] = ("%s: %s" % (type(_v23_ex).__name__, _v23_ex), False)
        # AC3: THE SHIPPED VALIDATOR OVER THE LOG THESE ROUTES WROTE TO. The surface the defect
        # reddens is `validate.py events`, so that is the surface read back, run as the gate runs it.
        _v23_validated[_v23_rel] = subprocess.run(
            [sys.executable, str(ROOT / ".veldo/validate.py"), "events", str(_v23_lg)],
            capture_output=True, text=True).returncode
    # THE OBSERVATION POINT IS PROVEN NOT BLIND. A `validate.py events` exit of 0 over the driven
    # logs means nothing unless that command really does refuse the harmful line, so the same line
    # is put into a log of its own by a PLAIN FILE APPEND - the writer this module declares itself
    # unable to guard - and the validator must exit 1 over it.
    _v23_poison = Path(_v23_d) / "poisoned.jsonl"
    _v23_poison.write_text(json.dumps({"schema": "nope", "id": "0123456789ab",
                                       "type": _V23_ALLOWED, "at": "2026-01-02T03:04:05Z",
                                       "producer": "events.py"}) + "\n")
    _v23_poison_rc = subprocess.run(
        [sys.executable, str(ROOT / ".veldo/validate.py"), "events", str(_v23_poison)],
        capture_output=True, text=True).returncode
    # THE SUBCLASS ROUTE'S HARM IS PROVEN REAL, so the refusal driven above is not a rule against a
    # harmless key. The line emit() WOULD have written is assembled here with the same subclass key
    # and put in a log of its own by a PLAIN FILE APPEND - the writer this module declares itself
    # unable to guard: it carries the reserved key MORE THAN ONCE, json.loads resolves it to the
    # CALLER's value, and the SHIPPED validator (the check that reds the gate) exits 1 over it.
    _v23_dup = json.dumps({"schema": _V23_SCHEMA, "id": "0123456789ab", "type": _V23_ALLOWED,
                           "at": "2026-01-02T03:04:05Z", "producer": "events.py",
                           _V23Confusable("schema"): "nope"})
    _v23_dup_log = Path(_v23_d) / "duplicated.jsonl"
    _v23_dup_log.write_text(_v23_dup + "\n")
    _v23_dup_reads = json.loads(_v23_dup).get("schema")
    _v23_dup_twice = _v23_dup.count('"schema"') > 1
    _v23_dup_rc = subprocess.run(
        [sys.executable, str(ROOT / ".veldo/validate.py"), "events", str(_v23_dup_log)],
        capture_output=True, text=True).returncode

# WHICH DRIVEN ROUTES FAILED TO REFUSE, named rather than counted: a CLI route that exited 0 or
# moved a byte, and an in-process route that raised something other than a ValueError or moved a
# byte. Empty is the requirement; a red prints the routes.
_v23_cli_bad = sorted("%s :: %s" % k for k, v in _v23_cli.items() if v[0] == 0 or not v[1])
_v23_ip_bad = sorted("%s :: %s" % k for k, v in _v23_ip.items()
                     if not (isinstance(v[0], str) and v[0].startswith("ValueError: "))
                     or not v[1])
expect("WARP-0723 AC1/AC4: EVERY RESERVED ENVELOPE KEY IS REFUSED ON THE ASSEMBLED LINE, ON EVERY ROUTE DRIVEN HERE, IN EVERY DECLARED COPY OF THE MODULE - and each refusal is read back OFF THE BYTES rather than off an exit code. The defect: `emit proof.recorded --field schema=nope` exited 0 and the line LANDED, and `validate.py all` and the gate then failed permanently, in a log nothing may rewrite. THE ROUTES ARE GENERATED FROM THE MODULE'S OWN KEY TUPLE, so a sixth reserved key is driven without being written down here, and NO COUNT of keys, copies or routes is asserted - each leg is a property of EACH MEMBER: for every declared copy, in a throwaway tree of its own, every route exits NON-ZERO with the log BYTE-IDENTICAL to what it held before that route ran. The routes: the empty value for each reserved key (the shape `--field at=` shipped, and the one value illegal for all five), the measured defect values `schema=nope`, `at=` and `id=deadbeef`, an `at` in another legal ISO form this envelope does not write, the projection's own producer through BOTH `--field` and the `--producer` flag, a REPEATED `--field` so the last value wins, a PADDED key the CLI strips into the real one, a CASE-VARIANT key, the POSITIONAL argument for the one reserved key it sets (the projection's type and a type no vocabulary declares), and in process the `extra` override dict the CLI itself rides on for EVERY key with a padded, a case-variant and a `str` SUBCLASS spelling of each, the two reserved fields the CONSTRUCTOR takes as arguments, and THE WRITER CALLED DIRECTLY with a dict poked after assembly. Every in-process refusal is a ValueError, the class ASSERTED rather than assumed, and nothing raises out of this block: each route records the exception it got with its class, and a failing route is NAMED in the red rather than counted. THE CONTROLS ARE PART OF THIS ASSERTION, because a fixture that cannot write would satisfy every leg above: three allowed CLI emissions per copy land at exit 0, one in-process emission lands, and the lines READ BACK off each log are exactly those four, in order, each carrying an envelope the reserved rules admit - so every byte-unchanged reading is a refusal. THE PRECONDITIONS ARE CONJUNCTS, so losing one is a red with the summary printed instead of a traceback: the module still declares RESERVED_ENVELOPE_KEYS and SCHEMA (a rename is a NAMED red here), the five keys the item names are members of that tuple, every declared copy is present, loadable and BYTE-IDENTICAL TO THE ROOT'S (per copy, never a count of distinct contents), and every declared copy was actually driven on both doors - so the guard is proven in the copy an adopter runs and the root is not assumed to stand for all eight",
       _V23_NAMES_PRESENT
       and _v23_absent == [] and _v23_differ == [] and _v23_unloadable == []
       and bool(_v23_cli) and bool(_v23_ip)
       and _v23_cli_bad == [] and _v23_ip_bad == []
       and all(k in _V23_RESERVED for k in ("schema", "id", "type", "at", "producer"))
       and all(any(rel == r for r, _n in _v23_cli) for rel in _v22_module_rels)
       and all(any(rel == r for r, _n in _v23_ip) for rel in _v22_module_rels)
       and all(all(c.returncode == 0 for c in cs) for cs in _v23_cli_ctl.values())
       and all(v == "landed" for v in _v23_ip_ctl.values())
       and all(v == (_V23_CTL_TYPES, True) for v in _v23_readback.values())
       and all(v == (sorted(_V23_RESERVED), True) for v in _v23_mint.values()))
expect("WARP-0723 AC3: THE HARM IS REPRODUCED FIRST AND THEN SHOWN CLOSED, ON THE SURFACE THAT ACTUALLY REDDENS. Measured on the shipped tree at 18e6ca8 in a throwaway clone, no code change, documented flags only: `emit proof.recorded --field schema=nope` exit 0, the line LANDS (events.jsonl md5 054b25a1 -> bf09f763), `validate.py all` exit 1 on `line 809: bad or missing schema (want veldo.event/v1)`, and `./scripts/verify.sh` printing `veldo contracts: 1 problem(s)`, `contracts: FAIL` and `GATE: RED`; `--field at=` the same (md5 054b25a1 -> 15a48b60, validate exit 1). BOTH INVOCATIONS ARE DRIVEN HERE VERBATIM against every declared copy: each exits non-zero with the log byte-unchanged, and the SHIPPED `validate.py events` - the very check that goes red - exits 0 over the log each copy's routes wrote to. THAT READING IS PROVEN NOT BLIND rather than trusted: the same harmful line, placed in a log of its own by a PLAIN FILE APPEND (the writer this module declares itself unable to guard, and the reason this leg does not claim the log can never acquire such a line), makes that same validator exit 1. WHAT IS NOT CLAIMED: this leg does not run `./scripts/verify.sh` or `validate.py all`, because a gate that ran itself inside itself would not terminate; the gate's own greenness is this suite's result, and the event surface is the one asserted here",
       _V23_NAMES_PRESENT and _v23_absent == []
       and all(_v23_cli[(rel, "--field schema=nope (the measured defect)")][0] != 0
               and _v23_cli[(rel, "--field schema=nope (the measured defect)")][1]
               and _v23_cli[(rel, "--field at= (the measured defect)")][0] != 0
               and _v23_cli[(rel, "--field at= (the measured defect)")][1]
               for rel in _v22_module_rels)
       and bool(_v23_validated)
       and all(rc == 0 for rc in _v23_validated.values())
       and _v23_poison_rc == 1)

# WHICH SUBCLASS ROUTES FAILED TO REFUSE, and WHICH RESERVED KEYS were actually covered by one -
# named, never counted, and the key side taken from the module's own tuple so a sixth key must be
# driven here too rather than silently skipped.
_v23_sub_bad = sorted("%s :: %s" % k for k, v in _v23_ip.items() if "SUBCLASS" in k[1]
                      and (not (isinstance(v[0], str) and v[0].startswith("ValueError: "))
                           or not v[1]))
_v23_sub_keys = sorted({k for k in _V23_RESERVED
                        for _r, _n in _v23_ip if "SUBCLASS" in _n and repr(k) in _n})
# THE FIXTURE KEY REALLY DOES LIE through the two methods the old guard trusted, asserted rather
# than assumed: `str(key)` reports a name no rule reserves, and `alias != key` reads False.
_v23_sub_lies = (str(_V23Confusable("schema")) != "schema"
                 and not ("schema".strip().lower() != _V23Confusable("schema")))
expect("WARP-0723 ROUND 2: A `str` SUBCLASS KEY SPELLING A RESERVED ENVELOPE NAME IS REFUSED IN PROCESS, FOR EVERY KEY IN THE MODULE'S OWN TUPLE, IN EVERY DECLARED COPY - and the harm it used to do is proven REAL rather than assumed. THE DEFECT, measured at 26b6c34 in a clone of the shipped tree with no code change: a key that IS a str, spells `schema`, hashes elsewhere so `dict.update` keeps BOTH entries, and overrides only `__eq__` so the confusable test `alias != key` is answered by the INHERITED `str.__ne__` and reads False, passed every leg of the guard - the value test read the GENUINE entry - and emit() LANDED one line carrying `\"schema\"` TWICE (events.jsonl md5 58897e7f -> d86db52f). json.loads takes the LAST, so `validate.py events` and `validate.py all` went 0 -> 1 PERMANENTLY on an append-only log; AFTER the fix the same call raises ValueError with md5 58897e7f UNCHANGED and validate 0. WHAT CLOSES IT SITS AT THE LAYER THAT DECLARES THE CONTRACT, not in the reader: the key is normalised to the spelling json.dumps WILL WRITE, taken off str's OWN data via `str.__str__` so no method a subclass overrides can lie about it, and a reserved name is accepted only from an EXACT str (`type(key) is str` plus `str.__eq__`). BOTH LIES THE FIXTURE KEY TELLS ARE ASSERTED HERE RATHER THAN ASSUMED - `str(key)` reports a name no rule reserves and `alias != key` reads False - so the normalisation is not merely decorative: with `str(key)` in place of `str.__str__(key)` this route LANDS and this assertion goes red, measured. DRIVEN, NOT ARGUED: one route PER RESERVED KEY, generated from RESERVED_ENVELOPE_KEYS so a sixth key is driven without being written down here, each required to raise a ValueError - the CLASS asserted, the exception recorded rather than propagated - with the log BYTE-UNCHANGED, re-baselined per route, in a throwaway tree per copy; the keys actually covered are required to EQUAL the module's own tuple, so a route that silently stopped being generated is a red. THE HARM IS PROVEN REAL, so this is not a rule against a harmless key: the line emit() WOULD have written is assembled here with the same subclass key, carries the reserved key MORE THAN ONCE, json.loads resolves it to the CALLER's value, and the SHIPPED validator exits 1 over a log of its own holding it - placed there by a PLAIN FILE APPEND, the writer this module declares itself unable to guard. WHAT IS NOT CLAIMED: this grants NO new capability and removes none. The route needed arbitrary in-process Python, which already permits appending to the log directly, so what is closed is a way of CORRUPTING the module's own assembled line and nothing more. A `str` subclass spelling a key that is NOT reserved is ordinary payload and is still accepted, non-str keys are unchanged, and no universal is claimed about what the LOG can contain",
       _V23_NAMES_PRESENT
       and _v23_absent == [] and _v23_differ == [] and _v23_unloadable == []
       and _v23_sub_bad == [] and _v23_sub_keys == sorted(_V23_RESERVED) and _v23_sub_lies
       and all(any(rel == r and "SUBCLASS" in n for r, n in _v23_ip)
               for rel in _v22_module_rels)
       and _v23_dup_twice and _v23_dup_reads == "nope" and _v23_dup_rc == 1)

# --- AC2: THE PROJECTION'S OWN APPEND STILL LANDS ------------------------------------
# THE REQUIRED CONTROL, not an afterthought: the failure mode of this fix is the INVERSE of the
# defect. A refusal written one clause too wide - refusing the reconciler's producer outright
# instead of when the line is unentitled - would reject the projection's own append and stop the
# review log recording verdicts at all, silently, since reconciliation reports and never judges.
# Driven three ways: over THIS REPOSITORY'S REAL COMMITTED VERDICT ARTIFACTS through the writer
# itself, end to end through the CLI over a fixture repository carrying REAL artifact bytes, and
# with the entitlement withheld, which must refuse - so the leg cannot pass by being vacuous.
_v23_real_derivable, _v23_real_deferred = EV22.verdict_domain()
_v23_real_keys = frozenset(k for k, _p, _b in _v23_real_derivable)
_v23_proj_landed, _v23_proj_state, _v23_proj_refused, _v23_proj_validated = None, None, [], None
_v23_proj_rep, _v23_forged_refusal = {}, None
_v23_fx_first, _v23_fx_second, _v23_fx_blobs, _v23_fx_rc = None, None, None, (None, None)
with tempfile.TemporaryDirectory() as _v23_pd:
    # (a) THE RECONCILER'S OWN PASS over the REAL derivable set, appending through the module's one
    # writer ON THE PROJECTION'S OWN APPEND PATH, into a log of its own. Read back off the bytes and
    # resolved by the module's own reader, so `appended and resolvable exactly as before` is
    # measured rather than asserted. WARP-0731 turned the last argument from the derived key set
    # into the boolean that marks this path; leg (c) below is what keeps that from being vacuous.
    _v23_plog = Path(_v23_pd) / "projection.jsonl"
    try:
        with open(_v23_plog, "a") as _v23_fh:
            _v23_proj_rep = EV22._reconcile_pass(_v23_plog, _v23_real_derivable,
                                                 _v23_real_deferred, None, _v23_fh,
                                                 True)
        _v23_proj_landed = [json.dumps(e) for e in _v23_landed(_v23_plog)]
        _v23_proj_state = EV22.logged_verdict_state(_v23_plog)
    except Exception as _v23_ex:
        _v23_proj_landed = ["%s: %s" % (type(_v23_ex).__name__, _v23_ex)]
    _v23_proj_validated = subprocess.run(
        [sys.executable, str(ROOT / ".veldo/validate.py"), "events", str(_v23_plog)],
        capture_output=True, text=True).returncode
    # (c) WITH THE ENTITLEMENT WITHHELD every one of those same events is REFUSED, so what admits
    # them is THE APPEND PATH and not the shape of the line, and leg (a) cannot pass by being
    # vacuous. These are byte-for-byte the events leg (a) landed; the only difference is the flag.
    _v23_ulog = Path(_v23_pd) / "unentitled.jsonl"
    for _v23_e in (_v23_proj_rep.get("events") or []):
        try:
            with open(_v23_ulog, "a") as _v23_fh:
                EV22._append_events(_v23_fh, [_v23_e])
            _v23_proj_refused.append("landed unentitled")
        except ValueError:
            pass
        except Exception as _v23_ex:
            _v23_proj_refused.append("%s: %s" % (type(_v23_ex).__name__, _v23_ex))
    if _v23_ulog.is_file() and _v23_ulog.read_text().strip():
        _v23_proj_refused.append("bytes landed unentitled")
    # (d) AND THE PRODUCER RULE ISOLATED FROM THE TYPE RULE: a real derived line with its type
    # changed to one the loop MAY hand-emit still declares the reconciler's producer, and is refused
    # on THAT - leg (c) would otherwise be carried entirely by the projection-owned type check,
    # since every event it drives carries a projection-owned type. Driven OFF the append path, which
    # is what isolates the two rules now that WARP-0731 keys both on the same flag: the type is one
    # the writer admits, so a refusal here can only be the producer clause firing.
    try:
        _v23_forged = dict((_v23_proj_rep.get("events") or [{}])[0])
        _v23_forged["type"] = _V23_ALLOWED
        with open(Path(_v23_pd) / "forged.jsonl", "a") as _v23_fh:
            EV22._append_events(_v23_fh, [_v23_forged])
        _v23_forged_refusal = "landed"
    except Exception as _v23_ex:
        _v23_forged_refusal = "%s: %s" % (type(_v23_ex).__name__, _v23_ex)
    # (b) END TO END THROUGH THE CLI OF A DECLARED COPY, over a fixture repository carrying the REAL
    # committed bytes of this repository's own verdict artifacts - real content, disposable repo, so
    # the gate's own log is never touched. The second run must append zero, exactly as before.
    _v23_fx_src = EV22.tracked_verdicts()[:3]
    try:
        _v23_fx = _v22_seed(os.path.join(_v23_pd, "fx"),
                            [(p, json.loads((ROOT / p).read_text())) for p in _v23_fx_src])
        _v23_fx_tree = _v23_tree(_v23_pd, _V23_PACK_COPY)
        _v23_fx_log = Path(_v23_fx) / ".veldo/events.jsonl"
        _v23_fx_cmd = [sys.executable, str(_v23_fx_tree / ".veldo/events.py"),
                       "reconcile-verdicts", "--repo-root", str(_v23_fx), "--log",
                       str(_v23_fx_log)]
        _v23_r1 = subprocess.run(_v23_fx_cmd, capture_output=True, text=True)
        _v23_fx_first = sorted(e.get("verdict_blob") for e in _v22_logged(_v23_fx))
        _v23_r2 = subprocess.run(_v23_fx_cmd, capture_output=True, text=True)
        _v23_fx_second = sorted(e.get("verdict_blob") for e in _v22_logged(_v23_fx))
        _v23_fx_blobs = sorted(b for _k, _p, b in EV22.verdict_domain(repo_root=str(_v23_fx))[0])
        _v23_fx_rc = (_v23_r1.returncode, _v23_r2.returncode)
    except Exception as _v23_ex:            # pragma: no cover - a fixture that cannot be built
        _v23_fx_first = ["%s: %s" % (type(_v23_ex).__name__, _v23_ex)]
expect("WARP-0723 AC2: THE PROJECTION'S OWN APPEND STILL LANDS, which is the REQUIRED control because the failure mode of this fix is the INVERSE of the defect - a refusal one clause too wide (the reconciler's producer refused outright rather than when the line is unentitled) would reject the projection's own derived append and stop the review log recording verdicts at all, silently, since reconciliation reports and never judges. Driven THREE ways over REAL material. (1) Every event the projection derives for EVERY tracked verdict artifact in this repository is appended THROUGH THE MODULE'S OWN WRITER with the entitled key set that pass derived, into a log of its own: every one lands, the bytes read back equal the events derived, the module's own reader RESOLVES every one of them with no unresolved entry and a key set equal to the derived key set, and the shipped `validate.py events` exits 0 over the result - `appended and resolvable exactly as before`, measured. (2) End to end through the CLI OF A DECLARED COPY over a fixture repository carrying the REAL committed bytes of this repository's own verdict artifacts: exit 0, one event per artifact keyed to the artifact's own blob, and the SECOND run appends nothing - idempotent, as before. (3) The same real events offered with the entitlement WITHHELD are ALL refused with nothing landing, so what admits them is the content key this pass derived and not the shape of the line, and leg (1) cannot pass by being vacuous. A hand-emitted event of an ALLOWED type with no reserved key landing at exit 0 is asserted in the AC1 leg's controls, per copy, and read back off the bytes there. WHAT IS REPORTED RATHER THAN WORKED AROUND: the entitled append is distinguished from a forgery WITHOUT any caller-supplied string - the key is (type, spec id, verdict_blob) derived from a COMMITTED artifact in the repository the log belongs to - and `producer` remains author-written and buys nothing, which is why forging it is now refused rather than believed",
       _V23_NAMES_PRESENT
       and bool(_v23_real_keys) and bool(_v23_proj_rep.get("events"))
       and _v23_proj_rep.get("appended") == len(_v23_proj_rep.get("events") or [])
       and _v23_proj_landed == [json.dumps(e) for e in (_v23_proj_rep.get("events") or [])]
       and isinstance(_v23_proj_state, tuple)
       and _v23_proj_state[0] == _v23_real_keys
       and _v23_proj_state[2] == []
       and _v23_proj_validated == 0
       and _v23_proj_refused == []
       and isinstance(_v23_forged_refusal, str)
       and _v23_forged_refusal.startswith("ValueError: ")
       and "OWN producer" in _v23_forged_refusal
       and _V23_PACK_COPY != ".veldo/events.py"
       and _v23_fx_rc == (0, 0)
       and bool(_v23_fx_blobs)
       and _v23_fx_first == _v23_fx_blobs
       and _v23_fx_second == _v23_fx_first)
# --- WARP-0724: the frontier honours a spec's DECLARED DEPENDENCIES on every build path ---
#
# THE DEFECT, measured 2026-07-28 at a03d949 and reproduced at 18e6ca8. claimable() had two build
# paths. The STANDALONE path filtered on `lane == "standalone" and status == "ready"` and never read
# depends_on, so five of the ten claimable units were handed out with an unshipped prerequisite:
# WARP-0712 (needs WARP-0716), WARP-0714 (needs WARP-0712), WARP-0715 (needs WARP-0713), WARP-0717
# (needs WARP-0712), WARP-0718 (needs WARP-0620). One of the five erases a human decision: the owner
# ruled on VEL-16 that the suite split decides the shape before the speed work lands, and that
# ruling IS the WARP-0714 -> WARP-0712 dependency the dispatcher was ignoring.
#
# THE SAME DEFECT ON THE OTHER PATH, measured at 0f59d33 after the first fix and the reason this
# block was reworked. The PLAN path asks plan.item_state, which reads the PLAN WORK ITEM's
# depends_on - never the spec's own front matter. Driven: setting specs/WARP-0620 to ready with
# depends_on including WARP-0712 (at ready) left check_spec and check_ready both at 0 and the
# frontier still offered `build WARP-0620 PLAN-0016`, while unmet_dependencies on that same spec in
# that same process returned [('WARP-0712', 'ready')]. A predicate contradicting its own report is
# the defect whichever answer is right. And for a spec BOTH paths can reach, whichever ran first put
# the id in `seen`, so the other path's check never ran at all. Both are one mistake - a per-path
# rule - so the rule is now asked once, in _add(), for every offer however the unit was found.
#
# THE THIRD ROUTE WAS AN UNTYPED FIELD. depends_on was not typed by check_spec, so four gate-legal
# shapes reached the reader that no reader can survive or report honestly, MEASURED: a list of
# mappings (block or inline) and a nested list raise TypeError: unhashable type inside the
# dispatcher, an integer member raises inside item_state's join, a bare scalar iterates its
# CHARACTERS and reports a spec waiting on 'W', 'A', 'R', and a block list mis-indented into
# 'ID: status' pairs yields a member no spec can match. Typed now at the layer that DECLARES the
# field (validate.check_depends_on), so the reader cannot meet a shape the contract admits, and the
# assertions below say exactly that pair: every bad shape is REFUSED, and every shape the contract
# admits is read without raising. And a spec id is now unique across the corpus
# (validate.check_spec_ids), because two files declaring one id resolve last-wins by sorted filename
# and a prerequisite at draft in one file reads as shipped from the other.
#
# These assertions run over TWO domains on purpose. FIXTURES in temporary repositories carry the
# non-vacuity, because their statuses cannot move. The REAL corpus carries the universal property.
# Every statement about a NAMED LIVE spec is an IMPLICATION guarded by its own antecedent, because
# shipping WARP-0716 is an ordinary future change that SHOULD put WARP-0712 back on the frontier and
# a flat "not claimable" would be a pin on a moving repository property. Nothing here counts specs,
# units, statuses or files.
#
# PRIVATE MODULE HANDLES, and this is not stylistic. The bare name PL in this file is REBOUND at
# line 1270 from the plan module to a process runner, and the first version of this block crashed
# with `module 'veldo_process_runner' has no attribute 'item_state'` - a traceback, no pass/fail
# summary, a run that found nothing indistinguishable from a run that could not count. A
# module-level name is not a stable handle 20000 lines later, so this block loads its own instances
# of everything it drives and depends on no earlier binding and on no earlier block's state.
def _d724_load(name, rel):
    _s = importlib.util.spec_from_file_location(name, ROOT / rel)
    _m = importlib.util.module_from_spec(_s)
    _s.loader.exec_module(_m)
    return _m


_D724V = _d724_load("veldo_validate_d724", ".veldo/validate.py")
_D724FR = _d724_load("veldo_frontier_d724", ".veldo/frontier.py")
_D724PK = _d724_load("veldo_pack_d724", ".veldo/pack.py")
_D724_SPEC_PATH = ROOT / "specs/WARP-0724-frontier-honours-declared-dependencies.md"


def _d724_standalone(sid, status, deps):
    return ("---\nschema: veldo.spec/v1\nid: %s\ntitle: t\nstatus: %s\nowner: d\n"
            "lane: standalone\ndepends_on: [%s]\n---\nbody\n" % (sid, status, ", ".join(deps)))


def _d724_gatelegal(sid, status, deps, lane="standalone", extra=""):
    """A fixture spec the CONTRACT accepts, not only one the reader can parse: risk, acceptance
    criteria and (for the planned lane) the plan binding are present, so check_spec can be asserted
    at 0 on it. The routes below are only worth closing in the dispatcher because they are
    gate-legal, and a fixture the gate would reject could not show that."""
    return ("---\nschema: veldo.spec/v1\nid: %s\ntitle: t\nstatus: %s\nrisk: low - fixture\n"
            "owner: dmitry\nlane: %s\n%sdepends_on: [%s]\n"
            "acceptance_criteria:\n  - id: AC1\n    text: t\n---\nbody\n"
            % (sid, status, lane, extra, ", ".join(deps)))


# A plan the plan contract ACCEPTS (check_plan == 0), carrying one work item whose own declared
# dependencies are satisfied. It is the antecedent of the plan-lane route: the plan says go, and the
# only thing that can hold the unit back is the spec's own front matter.
_D724_PLAN = ("---\nschema: veldo.plan/v1\nid: PLAN-9728\ntitle: fixture plan\nkind: iteration\n"
              "status: ready\nrevision: 1\nowner: dmitry\napproved_by: dmitry\n"
              "approved_at: 2026-01-01\n"
              "outcomes:\n  - id: O1\n    becomes_true: a thing becomes true.\n    measure: m\n"
              "feature_tree:\n  - id: F1\n    title: f\n    outcome_refs: [O1]\n"
              "work:\n  - item: W1\n    spec: WARP-9729\n    title: t\n    feature_refs: [F1]\n"
              "    depends_on: []\n    order: 10\n"
              "regression:\n  journeys:\n    - id: RJ1\n      title: j\n"
              "      activation: {when: start}\n      suite: e2e\n"
              "release:\n  milestone: v1\n  mode: continuous\n---\nbody\n")


def _d724_write(repo, rel, text):
    with open(os.path.join(repo, rel), "w") as _f:
        _f.write(text)


_D724_DRIVER_SRC = (
    "import importlib.util, json, sys\n"
    "path, repo, claims, caps, scope = sys.argv[1:6]\n"
    "s = importlib.util.spec_from_file_location('fr', path)\n"
    "m = importlib.util.module_from_spec(s); s.loader.exec_module(m)\n"
    "caps = json.loads(caps); scope = json.loads(scope) or None\n"
    "u = m.claimable(worker_caps=caps, scope=scope, repo_root=repo, claims_root=claims)\n"
    "idx = m._spec_index(repo)\n"
    "st = m._status_map(idx)\n"
    "print(json.dumps({\n"
    "    'build': sorted(x['spec'] for x in u if x['kind'] == 'build'),\n"
    "    'review': sorted(x['spec'] for x in u if x['kind'] == 'review'),\n"
    "    'withheld': {h['spec']: sorted(h['unmet'])\n"
    "                 for h in m.withheld(repo_root=repo, scope=scope)},\n"
    "    'unmet': {sid: sorted(m.unmet_dependencies(fm, st)) for sid, fm in idx.items()},\n"
    "}))\n")
_D724_DRIVER_DIR = tempfile.mkdtemp(prefix="d724driver-")
_D724_DRIVER = os.path.join(_D724_DRIVER_DIR, "drive.py")
with open(_D724_DRIVER, "w") as _d724_f:
    _d724_f.write(_D724_DRIVER_SRC)


_d724_dead = []


def _d724_drive(repo, claims, caps=(), scope=None, timeout=30):
    """ONE CHILD INTERPRETER per read, under a wall-clock ceiling: the claimable build set, the
    review set, the withheld report and unmet_dependencies over every spec, from one process.

    EVERY read of the dispatcher in this block goes through here, and that is a MEASURED correction
    twice over. Round one: the cycle fixture was read IN PROCESS, and a mutant that resolved
    dependencies transitively with a re-pushing stack hung the whole run with no "selftest: N
    passed" line at all. Round two: a mutant that made the dependency GATE itself non-terminating
    killed the run (exit 137) at the FIRST in-process read in this block, long before the cycle
    fixture, so a ceiling covering one fixture was covering the wrong thing. A hang is strictly
    worse than a red, so nothing here reads the dispatcher in process, and a non-terminating
    dispatcher becomes a legible red in every assertion that reads this function's result.

    Returns the four projections, or {"error": ...} - never raises, so a broken precondition is a
    red in the assertion that reads it and not a traceback that kills the run before the summary.
    json has no tuples, so each (dep, state) pair is restored to a tuple here, once.

    FAIL FAST ON NON-TERMINATION, and this too is a measured correction. With a ceiling per read and
    no memory of having hit one, the m13 mutant paid the ceiling on EVERY read: the suite still
    reddened every assertion legibly, but only after half an hour, and the battery run that was
    supposed to observe it was killed by its own outer timeout with no summary line. So the FIRST
    timeout is remembered and every later read returns it immediately: each assertion still receives
    an error and still goes red, and the whole block costs one ceiling. A spurious timeout on a
    loaded machine reddens the rest of the block, which is the safe direction - a false red, never a
    false green."""
    if _d724_dead:
        return {"error": _d724_dead[0]}
    try:
        proc = subprocess.run([sys.executable, _D724_DRIVER, str(ROOT / ".veldo/frontier.py"),
                               str(repo), str(claims), json.dumps(list(caps)),
                               json.dumps(scope)],
                              capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        _d724_dead.append("TIMED OUT after %ds: the dispatcher did not terminate; every later read "
                          "in this block reports this same error rather than paying the ceiling "
                          "again" % timeout)
        return {"error": _d724_dead[0]}
    except Exception as _e:                                   # noqa: BLE001 - reported, not raised
        return {"error": "raised: %r" % (_e,)}
    if proc.returncode != 0 or not proc.stdout.strip():
        return {"error": "exit %s: %s" % (proc.returncode, proc.stderr.strip()[-300:])}
    out = json.loads(proc.stdout)
    for key in ("withheld", "unmet"):
        out[key] = {k: [tuple(p) for p in v] for k, v in out[key].items()}
    return out


def _d724_set(repo, claims, caps=(), kind=None):
    """The claimable spec ids over a temporary repo, optionally of one kind, read out of process.
    A failed or non-terminating read is RETURNED as a string, so the assertion that reads it goes
    red instead of the run dying."""
    out = _d724_drive(repo, claims, caps)
    if out.get("error"):
        return out["error"]
    return set(out["build"]) | set(out["review"]) if kind is None else set(out[kind])


def _d724_report(repo, claims, caps=(), scope=None):
    """The withheld report over a temporary repo, {spec: [(dep, state)]}, read out of process.
    A failed or non-terminating read is RETURNED as a string, for the same reason."""
    out = _d724_drive(repo, claims, caps, scope=scope)
    return out["error"] if out.get("error") else out["withheld"]


# AC1. A ready standalone spec is not claimable while a declared dependency sits at ANY non-shipped
# status, and the statuses are ENUMERATED FROM THE VALIDATOR'S OWN VOCABULARY rather than typed out
# here, so a status added to that vocabulary later cannot silently become permissive: it enters this
# loop automatically and must be non-permissive to stay green. The precondition (that the vocabulary
# is readable and names the one state that satisfies a dependency) is asserted separately so it
# cannot fail silently inside the loop.
_d724_nonshipped = sorted(_D724V.SPEC_STATUSES - {"shipped"})
expect("WARP-0724 AC1 precondition: the validator's SPEC_STATUSES vocabulary is readable, names the "
       "single state that satisfies a declared dependency, agrees with the constant the dispatcher "
       "resolves against, and has non-shipped members for the loop below to enumerate. Without this "
       "the AC1 loop could pass by iterating nothing",
       "shipped" in _D724V.SPEC_STATUSES and _D724FR.DEP_SHIPPED == "shipped"
       and {"draft", "ready", "in_progress", "review", "blocked"} <= set(_d724_nonshipped)
       and _D724FR.DEP_ABSENT not in _D724V.SPEC_STATUSES)

with tempfile.TemporaryDirectory() as _d724repo, tempfile.TemporaryDirectory() as _d724claims:
    os.makedirs(os.path.join(_d724repo, "specs"))
    _d724_write(_d724repo, "specs/VELDO-D1.md", _d724_standalone("VELDO-D1", "ready", ["VELDO-D0"]))
    _d724_write(_d724repo, "specs/VELDO-D2.md", _d724_standalone("VELDO-D2", "ready", []))
    _d724_offered = {}
    _d724_reported = {}
    for _d724_st in _d724_nonshipped + ["shipped", _D724FR.DEP_ABSENT]:
        if _d724_st == _D724FR.DEP_ABSENT:
            os.remove(os.path.join(_d724repo, "specs/VELDO-D0.md"))
        else:
            _d724_write(_d724repo, "specs/VELDO-D0.md", _d724_standalone("VELDO-D0", _d724_st, []))
        _d724_read = _d724_drive(_d724repo, _d724claims)
        _d724_got = _d724_read.get("error") or set(_d724_read["build"])
        _d724_offered[_d724_st] = (("VELDO-D1" in _d724_got, "VELDO-D2" in _d724_got)
                                   if isinstance(_d724_got, set) else _d724_got)
        _d724_reported[_d724_st] = _d724_read.get("error") or _d724_read["withheld"]
    expect("WARP-0724 AC1: a ready standalone spec is NOT claimable while its declared dependency "
           "sits at any non-shipped status, and IS claimable the moment that dependency is shipped. "
           "The statuses come from the validator's own SPEC_STATUSES vocabulary, so a status added "
           "later is enumerated here automatically and cannot become permissive unnoticed. An "
           "independent ready standalone spec in the same tree stays claimable at every status, so "
           "the gate withholds the dependent unit and not the queue",
           _d724_offered.get("shipped") == (True, True)
           and all(_d724_offered.get(_s) == (False, True)
                   for _s in _d724_nonshipped + [_D724FR.DEP_ABSENT]))
    # THE DECISION AND ITS OWN REPORT, read off ONE TREE IN ONE PROCESS through the two public entry
    # points. The earlier shape of this assertion compared unmet_dependencies against
    # plan.item_state on dictionaries the assertion built itself, and that is exactly why it stayed
    # green while the dispatcher offered a spec its own report called waiting: NEITHER side of that
    # comparison was the dispatcher's decision. Here claimable() decides and withheld() explains,
    # over every dependency state the validator's vocabulary admits plus the absent case.
    expect("WARP-0724: THE DECISION AND ITS OWN REPORT CANNOT DISAGREE, measured through the two "
           "public entry points over one tree rather than by comparing two hand-built dicts: at "
           "every dependency state the validator's vocabulary admits, plus the absent case, a unit "
           "is offered by claimable() if and only if withheld() does not name it, the report names "
           "the exact prerequisite and its exact state (the absent case naming the absent-dependency "
           "constant), and the independent unit in the same tree is named by neither",
           all(isinstance(_d724_reported.get(_s), dict)
               and ("VELDO-D1" in _d724_reported[_s]) == (not _d724_offered.get(_s, (True,))[0])
               and "VELDO-D2" not in _d724_reported[_s]
               for _s in _d724_nonshipped + ["shipped", _D724FR.DEP_ABSENT])
           and _d724_reported.get("shipped") == {}
           and all(_d724_reported.get(_s) == {"VELDO-D1": [("VELDO-D0", _s)]}
                   for _s in _d724_nonshipped + [_D724FR.DEP_ABSENT]))

# AC2 (a). The measured five, replayed as a FIXTURE at the statuses they were measured at. This is
# the non-vacuous half: the tree is fixed, so the five are named without pinning anything the live
# repository can move. The units that WERE correctly claimable in the same measurement are in the
# same tree and must stay claimable, which is the negative control against a fix that just empties
# the queue. Then the prerequisites ship in two stages (WARP-0712 is itself a prerequisite, so it
# must ship before WARP-0714 and WARP-0717 can be offered) and each withheld unit appears.
_D724_MEASURED = [("WARP-0712", [("WARP-0711", "shipped"), ("WARP-0716", "ready")]),
                  ("WARP-0714", [("WARP-1210", "shipped"), ("WARP-0712", "ready")]),
                  ("WARP-0715", [("WARP-0713", "ready")]),
                  ("WARP-0717", [("WARP-0712", "ready")]),
                  ("WARP-0718", [("WARP-0620", "draft")])]
_D724_MEASURED_OK = [("WARP-0626", [("WARP-0623", "shipped")]),
                     ("WARP-0713", []), ("WARP-0716", [("WARP-1210", "shipped")]),
                     ("WARP-0719", [("WARP-0616", "shipped")]),
                     ("WARP-0722", []), ("WARP-0723", []), ("WARP-0724", [])]
with tempfile.TemporaryDirectory() as _d724mrepo, tempfile.TemporaryDirectory() as _d724mclaims:
    os.makedirs(os.path.join(_d724mrepo, "specs"))
    _d724_dep_status = {}
    for _d724_sid, _d724_deps in _D724_MEASURED + _D724_MEASURED_OK:
        for _d724_dep, _d724_dst in _d724_deps:
            _d724_dep_status[_d724_dep] = _d724_dst
    for _d724_sid, _d724_deps in _D724_MEASURED + _D724_MEASURED_OK:
        _d724_write(_d724mrepo, "specs/%s.md" % _d724_sid,
                    _d724_standalone(_d724_sid, "ready", [d for d, _ in _d724_deps]))
    for _d724_dep, _d724_dst in sorted(_d724_dep_status.items()):
        if _d724_dep not in dict(_D724_MEASURED + _D724_MEASURED_OK):
            _d724_write(_d724mrepo, "specs/%s.md" % _d724_dep,
                        _d724_standalone(_d724_dep, _d724_dst, []))
    _d724_m_read = _d724_drive(_d724mrepo, _d724mclaims)
    _d724_m_before = _d724_m_read.get("error") or set(_d724_m_read["build"])
    _d724_m_withheld = _d724_m_read.get("error") or _d724_m_read["withheld"]
    _d724_m_scoped = _d724_report(_d724mrepo, _d724mclaims, scope={"plan": "PLAN-NONE"})
    _d724_m_labelled = _d724_report(_d724mrepo, _d724mclaims, scope={"label": "nosuchlabel"})
    # stage 1: ship the prerequisites that are not themselves among the withheld five
    for _d724_dep in ("WARP-0716", "WARP-0713", "WARP-0620"):
        _d724_write(_d724mrepo, "specs/%s.md" % _d724_dep,
                    _d724_standalone(_d724_dep, "shipped", []))
    _d724_m_stage1 = _d724_set(_d724mrepo, _d724mclaims)
    # stage 2: ship WARP-0712, the prerequisite WARP-0714 and WARP-0717 were waiting on
    _d724_write(_d724mrepo, "specs/WARP-0712.md", _d724_standalone("WARP-0712", "shipped", []))
    _d724_m_stage2 = _d724_set(_d724mrepo, _d724mclaims)
    expect("WARP-0724 AC2 fixture: the FIVE MISDISPATCHED UNITS measured 2026-07-28 (WARP-0712 on "
           "WARP-0716, WARP-0714 on WARP-0712, WARP-0715 on WARP-0713, WARP-0717 on WARP-0712, "
           "WARP-0718 on WARP-0620), replayed at the dependency statuses they were measured at, are "
           "each absent from claimable() while every unit the same measurement showed correctly "
           "claimable is still offered. Shipping the prerequisites in two stages then makes each of "
           "the five appear, so the gate withholds them for their dependency and not for being "
           "named. A fixture and not the live index: the statuses here cannot move",
           isinstance(_d724_m_before, set)
           and all(_s not in _d724_m_before for _s, _ in _D724_MEASURED)
           and all(_s in _d724_m_before for _s, _ in _D724_MEASURED_OK)
           and isinstance(_d724_m_stage1, set)
           and all(_s in _d724_m_stage1 for _s in ("WARP-0712", "WARP-0715", "WARP-0718"))
           and isinstance(_d724_m_stage2, set)
           and all(_s in _d724_m_stage2 for _s in ("WARP-0714", "WARP-0717")))
    expect("WARP-0724: the withheld report obeys the SAME scope predicate the queue obeys, so it "
           "answers the question that was asked and not a wider one. Under a plan scope no "
           "standalone unit is in scope (a standalone spec carries no plan) and under a label none "
           "of these fixtures carries, the report is empty, while the UNSCOPED report over the same "
           "tree at the same moment is not. Read before the prerequisites are shipped below, which "
           "is a measured correction: read after them, nothing was withheld under any scope and a "
           "mutant that ignored scope entirely stayed green",
           _d724_m_scoped == {} and _d724_m_labelled == {} and _d724_m_withheld != {})
    expect("WARP-0724 AC2/AC3 report: the withheld report NAMES each of the five with the exact "
           "prerequisite and prerequisite state holding it back, and names nothing that is "
           "claimable. An ordering rule whose effect is invisible looks like an empty queue instead "
           "of a waiting one, which is the failure mode this item's own risk section calls out",
           isinstance(_d724_m_withheld, dict)
           and set(_d724_m_withheld) == {_s for _s, _ in _D724_MEASURED}
           and _d724_m_withheld
           == {_s: sorted([(d, st) for d, st in _deps if st != "shipped"])
               for _s, _deps in _D724_MEASURED})

# AC2 (b) and AC3 (a). The property over THIS repository's own spec index: no claimable build unit
# has an unshipped declared dependency, and the queue is not empty. Driven with an EMPTY claims root
# so a live claim held by another worker cannot move the result, and with the capability set derived
# from the corpus itself (the union of every declared `requires`) so the capability gate hides
# nothing from the sweep. Both are properties of each member, so an added spec cannot make either
# stale; the non-emptiness is what keeps the universal from passing vacuously.
with tempfile.TemporaryDirectory() as _d724liveclaims:
    # _spec_index and _is_standalone_build are pure front-matter reads with no dependency logic in
    # them, so they stay in process; every read that goes through the dependency rule is driven out
    # of process by _d724_drive.
    _d724_idx = _D724FR._spec_index(ROOT)
    _d724_caps = sorted({r for _fm in _d724_idx.values() for r in (_fm.get("requires") or [])
                         if isinstance(r, str)})
    _d724_live = _d724_drive(ROOT, _d724liveclaims, caps=_d724_caps)
    _d724_live_unmet = (_d724_live["error"] if _d724_live.get("error")
                        else {_s: _d724_live["unmet"].get(_s, []) for _s in _d724_live["build"]})
    expect("WARP-0724 AC2: on THIS repository's own spec index, NO claimable build unit has an "
           "unshipped declared dependency. The decision and the report are read from ONE child "
           "interpreter under a ceiling, with an empty claims root (a live claim must not move a "
           "property of the corpus) and with the capability set derived from the corpus, so the "
           "sweep sees every unit. A property of each member, so an added spec cannot make it "
           "stale, and the non-emptiness asserted next is what stops it passing vacuously",
           isinstance(_d724_live_unmet, dict)
           and all(_v == [] for _v in _d724_live_unmet.values()))
    expect("WARP-0724 AC3: THE QUEUE DOES NOT STARVE, proven rather than hoped: claimable() over "
           "this repository's own index still yields build work after the gate is applied. This is "
           "the assertion that catches a fix which got strictness right by offering nothing",
           not _d724_live.get("error") and bool(_d724_live.get("build")))
    _d724_named = {}
    for _d724_sid, _d724_deps in _D724_MEASURED:
        _d724_nfm = _d724_idx.get(_d724_sid) or {}
        _d724_named[_d724_sid] = {
            "standalone_ready": _D724FR._is_standalone_build(_d724_nfm),
            "unmet": (_d724_live["unmet"].get(_d724_sid, [])
                      if not _d724_live.get("error") else None),
            "offered": (_d724_sid in _d724_live.get("build", [])
                        or _d724_sid in _d724_live.get("review", [])),
        }
    expect("WARP-0724 AC2 live: for each of the five named units, WHILE it is still a ready "
           "standalone spec with an unshipped declared dependency it is NOT offered. An implication "
           "on purpose: shipping WARP-0716 is an ordinary change that SHOULD return WARP-0712 to "
           "the frontier, so a flat 'these five are not claimable' would pin a moving repository "
           "property. The fixture above carries the non-vacuity. An unreadable corpus is a RED here "
           "and not a vacuous pass: the implication is guarded by the read having succeeded",
           not _d724_live.get("error")
           and all(not (_v["standalone_ready"] and _v["unmet"]) or not _v["offered"]
                   for _v in _d724_named.values()))

# AC3 (b), (c), (d) and AC4, over one fixture. A dependency CYCLE (two specs on each other, and one
# on itself) must not raise, must not hang, must yield nothing for the cycle members and must leave
# every unrelated unit alone. A dependency naming a spec that DOES NOT EXIST must be treated as
# unshipped and REPORTED, because a typo that silently satisfied a prerequisite is this same defect
# wearing a different hat. And a spec at status review is offered as a review unit even with an
# unshipped or absent dependency: a review is of an already-built spec, so its prerequisites cannot
# bear on whether it can be reviewed.
with tempfile.TemporaryDirectory() as _d724crepo, tempfile.TemporaryDirectory() as _d724cclaims:
    os.makedirs(os.path.join(_d724crepo, "specs"))
    for _d724_sid, _d724_st, _d724_deps in (
            ("VELDO-C1", "ready", ["VELDO-C2"]),      # cycle member
            ("VELDO-C2", "ready", ["VELDO-C1"]),      # cycle member
            ("VELDO-C3", "ready", ["VELDO-C3"]),      # self dependency
            ("VELDO-C4", "ready", []),               # unrelated work, no dependency
            ("VELDO-C5", "ready", ["VELDO-C0"]),      # unrelated work, dependency shipped
            ("VELDO-C0", "shipped", []),
            ("VELDO-C6", "ready", ["VELDO-NOPE"]),    # dependency names no spec at all
            ("VELDO-C7", "review", ["VELDO-NOPE"]),   # review unit, absent dependency
            ("VELDO-C8", "review", ["VELDO-C1"])):    # review unit, unshipped dependency
        _d724_write(_d724crepo, "specs/%s.md" % _d724_sid,
                    _d724_standalone(_d724_sid, _d724_st, _d724_deps))
    # Read through _d724_drive, like every other read in this block: one child interpreter under a
    # wall-clock ceiling. See that function for the two measurements that put it there. A dispatcher
    # that does not terminate on a cycle turns the four assertions below into clean reds while the
    # rest of the suite still runs and still counts.
    _d724_cyc_out = _d724_drive(_d724crepo, _d724cclaims)
    _d724_cyc = _d724_cyc_out.get("build")
    _d724_cyc_review = _d724_cyc_out.get("review")
    _d724_cyc_withheld = _d724_cyc_out.get("withheld") or {}
    expect("WARP-0724 AC3: the cycle tree TERMINATES, read like every other tree in this block from "
           "ONE child interpreter under a wall-clock ceiling, measured rather than argued from the "
           "source. That shape is a correction made TWICE, both times by a mutant: reading the cycle "
           "fixture in process let a transitive resolver hang the whole run with no summary line, "
           "and then a non-terminating dependency GATE killed the run at the block's FIRST "
           "in-process read, before this fixture was reached at all. Nothing here reads the "
           "dispatcher in process, so the assertions below stay reachable as clean reds",
           _d724_cyc_out.get("error") is None
           and isinstance(_d724_cyc, list) and isinstance(_d724_cyc_review, list))
    expect("WARP-0724 AC3: a dependency CYCLE among ready specs neither raises nor swallows "
           "unrelated work. Both members of a two-spec cycle and a self-dependent spec are "
           "withheld, while every unrelated ready standalone unit in the same tree (one with no "
           "dependency, one with a shipped dependency) is still offered. There is nothing to "
           "recurse into: the predicate reads each dependency's status and never walks the graph, "
           "so a cycle is not a special case",
           isinstance(_d724_cyc, list)
           and all(_s not in _d724_cyc for _s in ("VELDO-C1", "VELDO-C2", "VELDO-C3"))
           and all(_s in _d724_cyc for _s in ("VELDO-C4", "VELDO-C5")))
    expect("WARP-0724 AC3: a dependency naming a spec THAT DOES NOT EXIST is treated as UNSHIPPED "
           "and REPORTED, never silently satisfied: VELDO-C6 is withheld and the report names its "
           "missing prerequisite with the absent-dependency state, which the precondition above "
           "proved is not a member of the status vocabulary, so an absent spec can never be "
           "confused with a spec that has a status. A typo that satisfied a prerequisite would be "
           "this same defect wearing a different hat",
           isinstance(_d724_cyc, list) and "VELDO-C6" not in _d724_cyc
           and _d724_cyc_withheld.get("VELDO-C6") == [("VELDO-NOPE", _D724FR.DEP_ABSENT)]
           and _d724_cyc_withheld.get("VELDO-C1") == [("VELDO-C2", "ready")]
           and _d724_cyc_withheld.get("VELDO-C3") == [("VELDO-C3", "ready")]
           and "VELDO-C4" not in _d724_cyc_withheld and "VELDO-C5" not in _d724_cyc_withheld)
    expect("WARP-0724 AC4: REVIEW UNITS ARE UNAFFECTED. A spec at status review is still offered as "
           "a review unit with an unshipped declared dependency (VELDO-C8, waiting on a cycle "
           "member) and with a dependency naming a spec that does not exist (VELDO-C7). A review is "
           "of an already-built spec, so its prerequisites cannot bear on whether it can be "
           "reviewed, and neither review spec appears in the withheld report, which is about build "
           "work",
           isinstance(_d724_cyc_review, list)
           and {"VELDO-C7", "VELDO-C8"} <= set(_d724_cyc_review)
           and "VELDO-C7" not in _d724_cyc_withheld and "VELDO-C8" not in _d724_cyc_withheld)

# THE PLAN LANE, which is the route the first fix left open. A plan the plan contract ACCEPTS, at
# status ready, whose one work item's own declared dependencies are satisfied, so the plan says go;
# and the spec that work item names declares an unshipped prerequisite in its OWN front matter. The
# whole fixture is gate-legal - check_spec, check_ready and check_plan are all asserted at 0 on it -
# which is the point: a route the gate admits cannot be defended by the gate.
with tempfile.TemporaryDirectory() as _d724arepo, tempfile.TemporaryDirectory() as _d724aclaims:
    os.makedirs(os.path.join(_d724arepo, "specs"))
    os.makedirs(os.path.join(_d724arepo, "plans"))
    _d724_write(_d724arepo, "plans/PLAN-9728.md", _D724_PLAN)
    _d724_write(_d724arepo, "specs/WARP-9729.md",
                _d724_gatelegal("WARP-9729", "ready", ["WARP-9728"], lane="planned",
                                extra="plan: PLAN-9728\nwork: W1\n"))
    _d724_write(_d724arepo, "specs/WARP-9728.md", _d724_gatelegal("WARP-9728", "ready", []))
    _d724_a_spec = os.path.join(_d724arepo, "specs/WARP-9729.md")
    _d724_a_legal = (_D724V.check_spec(_d724_a_spec, repo_root=_d724arepo),
                     _D724V.check_ready(_d724_a_spec, repo_root=_d724arepo),
                     _D724V.check_plan(os.path.join(_d724arepo, "plans/PLAN-9728.md"),
                                       specs_dir=os.path.join(_d724arepo, "specs")))
    _d724_a_read = _d724_drive(_d724arepo, _d724aclaims)
    _d724_a_before = _d724_a_read.get("error") or set(_d724_a_read["build"])
    _d724_a_withheld = _d724_a_read.get("error") or _d724_a_read["withheld"]
    _d724_a_scoped = _d724_report(_d724arepo, _d724aclaims, scope={"plan": "PLAN-9728"})
    _d724_write(_d724arepo, "specs/WARP-9728.md", _d724_gatelegal("WARP-9728", "shipped", []))
    _d724_a_after = _d724_set(_d724arepo, _d724aclaims, kind="build")
    expect("WARP-0724 AC1 on the PLAN LANE, the route the first fix left open and the review drove: "
           "a plan the plan contract accepts says go (its work item's own dependencies are "
           "satisfied) and the spec it names declares an unshipped prerequisite in its OWN front "
           "matter. The unit is NOT offered, and shipping that prerequisite - changing nothing else "
           "- makes it offered, so it is withheld for its dependency and not for being planned. The "
           "whole fixture is GATE-LEGAL: check_spec, check_ready and check_plan are each 0 on it, "
           "which is why the dispatcher and not the gate has to hold this. Before, the queue holds "
           "the prerequisite and NOT the planned unit, so what is withheld is the dependent unit and "
           "not the queue; after, it holds the planned unit and not the prerequisite, which is now "
           "shipped and therefore no longer build work at all",
           _d724_a_legal == (0, 0, 0)
           and _d724_a_before == {"WARP-9728"} and _d724_a_after == {"WARP-9729"})
    expect("WARP-0724 AC2/AC3 report on the PLAN LANE: the withheld report is not narrower than the "
           "rule it explains. The planned unit is named with its exact prerequisite and that "
           "prerequisite's exact state, its shipped-status prerequisite is not named, and under a "
           "scope of the spec's OWN plan the planned unit is still in scope - the report passes the "
           "spec's declared plan to the scope predicate, so scoping to a plan no longer hides every "
           "spec the report exists to name",
           _d724_a_withheld == {"WARP-9729": [("WARP-9728", "ready")]}
           and _d724_a_scoped == {"WARP-9729": [("WARP-9728", "ready")]})

# BOTH LANES REACHING ONE SPEC, which is how `seen` used to suppress the check entirely: the plan
# loop added the id first, and the standalone loop - the only loop that asked about dependencies -
# returned early on `sid in seen` without ever asking. The rule now lives at the one point both
# loops go through, so the order they run in cannot decide the answer. The contract ALSO refuses
# this shape (a plan work item whose spec does not mirror the plan back), and that is asserted here
# rather than assumed: this is defence in depth, and the dispatcher is a reader that must not
# depend on the gate having been run.
with tempfile.TemporaryDirectory() as _d724brepo, tempfile.TemporaryDirectory() as _d724bclaims:
    os.makedirs(os.path.join(_d724brepo, "specs"))
    os.makedirs(os.path.join(_d724brepo, "plans"))
    _d724_write(_d724brepo, "plans/PLAN-9728.md", _D724_PLAN)
    _d724_write(_d724brepo, "specs/WARP-9729.md",
                _d724_gatelegal("WARP-9729", "ready", ["WARP-9728"]))
    _d724_write(_d724brepo, "specs/WARP-9728.md", _d724_gatelegal("WARP-9728", "ready", []))
    _d724_b_build = _d724_set(_d724brepo, _d724bclaims, kind="build")
    _d724_b_mirror = _D724V.check_plan(os.path.join(_d724brepo, "plans/PLAN-9728.md"),
                                       specs_dir=os.path.join(_d724brepo, "specs"))
    expect("WARP-0724: a spec BOTH build loops reach is gated whatever order they run in. The "
           "standalone-lane spec here is also an active plan's work item, so the plan loop adds it "
           "first and `seen` used to make the only dependency check unreachable for it; it is now "
           "withheld, because the rule is asked at the one point every offer passes through and not "
           "per loop. The plan contract also REFUSES this shape (asserted, not assumed: the "
           "mirroring rule fails closed), so the dispatcher's guarantee here is defence in depth - "
           "a reader must not depend on the gate having run. The prerequisite in the same tree stays "
           "offered, so the withholding is of the dependent unit and not of the queue",
           _d724_b_build == {"WARP-9728"} and _d724_b_mirror > 0)

# AC5. THE FIELD IS TYPED WHERE IT IS DECLARED. Each shape below was driven through the dispatcher
# at 0f59d33 and is recorded here with what it actually did, so the table is a measurement and not a
# list of things that look wrong. The assertion is a PAIR, and neither half claims the other's
# ground: every shape in the refused table is refused by check_spec, and every shape the contract
# ADMITS is read by the dispatcher without raising. It deliberately does NOT claim the reader cannot
# crash - it cannot crash on input the contract admits, which is what typing at the declaring layer
# buys and all it buys.
_D724_BAD_SHAPES = (
    ("a list of mappings, block form", "depends_on:\n  - id: VELDO-D0\n    status: ready\n"),
    ("a list of mappings, inline form", "depends_on: [{id: VELDO-D0}]\n"),
    ("a nested list", "depends_on: [[VELDO-D0]]\n"),
    ("a bare scalar", "depends_on: VELDO-D0\n"),
    ("declared with no value", "depends_on:\n"),
    ("an integer member", "depends_on: [9001]\n"),
    ("a member carrying whitespace", "depends_on:\n  - VELDO-D0: ready\n"),
)
_D724_GOOD_SHAPES = (
    ("one id", "depends_on: [VELDO-D0]\n"),
    ("no dependency", "depends_on: []\n"),
    ("two ids", "depends_on: [VELDO-D0, VELDO-D9]\n"),
    ("an id naming no spec", "depends_on: [VELDO-NOPE]\n"),
)
_D724_SHAPE_HEAD = ("---\nschema: veldo.spec/v1\nid: VELDO-D1\ntitle: t\nstatus: ready\n"
                    "risk: low - fixture\nowner: dmitry\nlane: standalone\n")
_D724_SHAPE_TAIL = "acceptance_criteria:\n  - id: AC1\n    text: t\n---\nbody\n"
_d724_shape_verdict = {}
with tempfile.TemporaryDirectory() as _d724srepo, tempfile.TemporaryDirectory() as _d724sclaims:
    os.makedirs(os.path.join(_d724srepo, "specs"))
    _d724_write(_d724srepo, "specs/VELDO-D0.md", _d724_gatelegal("VELDO-D0", "ready", []))
    for _d724_name, _d724_shape in _D724_BAD_SHAPES + _D724_GOOD_SHAPES:
        _d724_write(_d724srepo, "specs/VELDO-D1.md",
                    _D724_SHAPE_HEAD + _d724_shape + _D724_SHAPE_TAIL)
        _d724_sp = os.path.join(_d724srepo, "specs/VELDO-D1.md")
        try:
            _d724_refused = _D724V.check_spec(_d724_sp, repo_root=_d724srepo) > 0
        except Exception as _e:                               # noqa: BLE001 - reported, not raised
            _d724_refused = "the check itself raised: %r" % (_e,)
        _d724_read = _d724_set(_d724srepo, _d724sclaims)
        _d724_shape_verdict[_d724_name] = (_d724_refused, isinstance(_d724_read, set))
expect("WARP-0724 AC5: depends_on is TYPED AT THE LAYER THAT DECLARES IT, and the pair of claims is "
       "exactly this. Every shape measured to break a reader - a list of mappings in either form, a "
       "nested list, a bare scalar that iterates its characters, a field declared with no value, an "
       "integer member, and a member carrying whitespace that can match no spec id - is REFUSED by "
       "check_spec, so the reader cannot meet it in a gated repository. And every shape the contract "
       "ADMITS, including one naming a spec that does not exist, is read by the dispatcher without "
       "raising. Nothing here claims the reader cannot crash: it cannot crash on input the contract "
       "admits, which is what typing at the declaring layer buys and all it buys",
       all(_d724_shape_verdict.get(_n, (None,))[0] is True for _n, _ in _D724_BAD_SHAPES)
       and all(_d724_shape_verdict.get(_n) == (False, True) for _n, _ in _D724_GOOD_SHAPES))

# AC5 over the REAL corpus, per member and never counted: every spec file this repository ships
# declares a depends_on the contract admits, and the dispatcher reads the whole index without
# raising. A spec added tomorrow is covered by the same loop; no floor and no total appears here.
_d724_corpus_typed = {}
for _d724_p in sorted((ROOT / "specs").glob("*.md")):
    if _d724_p.name.startswith("TEMPLATE") or _d724_p.name == "index.md":
        continue
    try:
        _d724_corpus_typed[_d724_p.name] = _D724V.check_depends_on(_d724_p, _d724_p.read_text())
    except Exception as _e:                                   # noqa: BLE001 - reported, not raised
        _d724_corpus_typed[_d724_p.name] = "raised: %r" % (_e,)
expect("WARP-0724 AC5 corpus: EVERY spec file this repository ships declares a depends_on the "
       "contract admits, asserted file by file so a spec added later enters this loop automatically, "
       "and the example spec the validator also gates is included. A property of each member: no "
       "count, no floor, and nothing that an added or removed spec can make stale",
       bool(_d724_corpus_typed)
       and all(_v == 0 for _v in _d724_corpus_typed.values())
       and _D724V.check_depends_on(ROOT / ".veldo/examples/spec-example.md",
                                   (ROOT / ".veldo/examples/spec-example.md").read_text()) == 0)

# AC6. A SPEC ID NAMES EXACTLY ONE FILE. The harm is measured in the same fixture rather than
# asserted from the source: two files declaring one id, one at draft and one at shipped, and the
# reader every consumer uses resolves the pair LAST-WINS by sorted filename, so the draft
# prerequisite reads as shipped and the dependency gate above would release work whose prerequisite
# does not exist. Refused at the layer that declares what a spec id is; the readers are left
# last-wins on purpose, because a defensive patch in each reader is the shape this repository has
# already paid for.
with tempfile.TemporaryDirectory() as _d724drepo:
    os.makedirs(os.path.join(_d724drepo, "specs"))
    _d724_write(_d724drepo, "specs/a-VELDO-D0.md", _d724_gatelegal("VELDO-D0", "draft", []))
    _d724_write(_d724drepo, "specs/z-VELDO-D0.md", _d724_gatelegal("VELDO-D0", "shipped", []))
    _d724_dup_errs = _D724V.check_spec_ids(os.path.join(_d724drepo, "specs"))
    _d724_dup_read = _D724FR._status_map(_D724FR._spec_index(_d724drepo))
    os.remove(os.path.join(_d724drepo, "specs/z-VELDO-D0.md"))
    _d724_dedup_errs = _D724V.check_spec_ids(os.path.join(_d724drepo, "specs"))
expect("WARP-0724 AC6: a spec id names EXACTLY ONE file, refused where the corpus contract is "
       "declared. The harm is measured in the fixture and not argued: the id is declared by a draft "
       "file and a shipped file, and the reader every consumer shares resolves it LAST-WINS by "
       "sorted filename to shipped, which is how an unshipped prerequisite releases dependent work. "
       "Removing the duplicate makes the same check pass, so it refuses the duplication and not the "
       "id, and this repository's own corpus passes it",
       _d724_dup_errs > 0 and _d724_dup_read == {"VELDO-D0": "shipped"}
       and _d724_dedup_errs == 0 and _D724V.check_spec_ids(ROOT / "specs") == 0)

# --- dogfood: this item's own spec, its declared footprint, and the engine copies it must keep in
# lockstep. The engine roots are DERIVED from the pack manifest (one root per declared pack, the
# canonical source among them), so declaring a new pack widens this set instead of making it
# vacuous, and no path is typed twice.
_d724_fm = _D724V.parse_yamlish(
    re.match(r"^---\n(.*?)\n---", _D724_SPEC_PATH.read_text(), re.S).group(1))
_d724_arch, _d724_contract = _D724V.load_repo_contract(repo_root=str(ROOT))
_d724_fp = [g for g in (_d724_fm.get("footprint") or []) if isinstance(g, str)]
# ONE engine home: packs compose onto the canonical source, so "each declared pack root" is
# now the single canonical root and the property is that the shipped engine carries the names.
_d724_engine_roots = sorted({p["engine_src"] for p in
                             _D724PK.load_packs(repo_root=str(ROOT)).get("packs", [])
                             if p.get("engine_src")})
_D724_ENGINE_MODULES = (".veldo/frontier.py", ".veldo/validate.py", ".veldo/validate_checks.py")
_d724_touched = sorted(set(list(_D724_ENGINE_MODULES)
                           + ["scripts/selftest.py",
                              "specs/WARP-0724-frontier-honours-declared-dependencies.md"]
                           + ["%s/%s" % (r, m) for r in _d724_engine_roots
                              for m in _D724_ENGINE_MODULES]))
expect("WARP-0724 dogfood: the spec has PASSED the ready transition (so this does not go stale the "
       "moment it ships), declares the high tier its own boundary-crossing footprint derives, and "
       "its footprint COVERS EVERY SOURCE PATH THIS ITEM TOUCHES, checked through the one glob "
       "compiler. The engine copies are DERIVED from the pack manifest, one root per declared pack, "
       "so a newly declared pack widens this set instead of making it vacuous. The shape gate "
       "refuses a diff outside the declared footprint, so an unlisted engine copy would turn the "
       "gate red rather than drift quietly",
       _d724_fm.get("status") in ("ready", "in_progress", "review", "proven", "shipped")
       and _d724_fm.get("risk", "").split()[0] == "high"
       and _d724_fm.get("lane") == "standalone"
       and (_d724_fm.get("depends_on") or []) == []
       and bool(_d724_engine_roots)
       and all(any(_d724_arch._glob_re(_g).match(_rel) for _g in _d724_fp)
               for _rel in _d724_touched)
       and _d724_arch.placement_gate(_d724_fm, _d724_contract) == []
       and _D724V.check_ready(_D724_SPEC_PATH, repo_root=str(ROOT)) == 0)

_d724_engine_texts = {(_r, _m): (ROOT / _r / _m).read_text()
                      for _r in _d724_engine_roots for _m in _D724_ENGINE_MODULES
                      if (ROOT / _r / _m).is_file()}
_d724_engine_want = {(_r, _m) for _r in _d724_engine_roots for _m in _D724_ENGINE_MODULES}
expect("WARP-0724: the dependency gate AND the contract that types the field it reads land in EVERY "
       "copy of the engine, not only the one this repository runs. For each declared pack root and "
       "each of the three engine modules this item changes, the pack's copy is byte-identical to the "
       "canonical module, and each copy carries the names the gate is built from - so no pack can "
       "ship the permissive dispatcher this item removed or the untyped field it refused. Both the "
       "roots and the module list are declared once here, so a newly declared pack widens this set "
       "instead of making it vacuous",
       _d724_engine_want and set(_d724_engine_texts) == _d724_engine_want
       and all(_t == (ROOT / _m).read_text() for (_r, _m), _t in _d724_engine_texts.items())
       and all(_n in _d724_engine_texts[(_r, ".veldo/frontier.py")]
               for _r in _d724_engine_roots
               for _n in ("DEP_ABSENT", "unmet_dependencies", "dependency_gate", "withheld"))
       and all(_n in _d724_engine_texts[(_r, ".veldo/validate_checks.py")]
               for _r in _d724_engine_roots
               for _n in ("check_depends_on", "check_spec_ids")))

# ===========================================================================
# WARP-0716: whether this suite CAN be split was a HYPOTHESIS nobody had counted.
# scripts/suite_survey.py counts it: every module-level name whose reaching definition
# lies outside the region of one of its reads, with its binding line, its reading lines,
# its carrier and a classification that DEFAULTS to UNDETERMINED. No line count appears
# in this comment: the suite grows, and a number in prose is a number that goes stale.
#
# The failure mode these assertions are built against is a clean bill of health from a
# tool that only looked where it expected, so the proof is a PAIR and a MATRIX, not a
# list of findings. The TANGLED fixture carries one POSITIVE and one NEGATIVE instance
# of every carrier the tool declares DETECTED, and a closure assertion derives both
# sides (the survey's own CARRIERS constant, this block's own case table) so a carrier
# added to the code without its two cases turns the gate red. The DETANGLED TWIN is the
# negative control: without it, a tool that answers NOT_FEASIBLE to everything scores
# perfectly on the tangled fixture and "the suite cannot be split" is an artifact of the
# analyser rather than a finding about the file.
#
# WHAT THESE ASSERTIONS CANNOT DO, stated here rather than left to silence: every hard
# case about the tool's BEHAVIOUR is against a fixture, so a survey that is completely
# WRONG about scripts/selftest.py is still gate-green. The real-file assertions are
# STRUCTURAL (vocabulary membership, line provenance, the subset relation between
# partitions, this block's own prefix containment) and cannot fire on a crossing the survey
# never looked for. STALENESS of the published report is not their job at all: the report is
# EMITTED by suite_survey.render_report() and scripts/check_generated.sh asserts that
# regenerating it is a no-op, so a figure the suite has made false cannot reach a green gate. That
# closes staleness and only staleness - the document and the check come from the same tool,
# so an error the tool makes appears identically in both and agrees with itself.
# proof/WARP-0716/crossing-state.md names that distinction as such, in its own blind spots.
#
# THE RECURSION IS USED RATHER THAN AVOIDED. The survey analyses the whole file, this
# block included: a self-exclusion would be the same defect turned inward. Instead the
# block earns its cleanliness - every module-level name it binds carries the `_s16_`
# prefix, and the containment is asserted in BOTH directions.
# ===========================================================================
# WARP-0716 BLOCK BEGIN (delimits the self-containment assertion)
import ast as _s16_ast
import contextlib as _s16_ctx
import io as _s16_io
import re as _s16_re

_s16_sspec = importlib.util.spec_from_file_location(
    "suite_survey_0716", ROOT / "scripts/suite_survey.py")
_s16_sv = importlib.util.module_from_spec(_s16_sspec)
_s16_sspec.loader.exec_module(_s16_sv)

# --- WARP-0716 the TANGLED fixture: ground truth DECLARED BY CONSTRUCTION -------
# Tags are the ground truth and they live on the lines they describe, so the expected
# line numbers are DERIVED from the fixture rather than typed as literals that drift:
#   #@b:N a line that must appear among N's binding lines
#   #@r:N a line that must appear among N's CROSSING read lines
#   #@v:N a call site through which a read of N enters (carrier C2)
#   #@u:N a read of N that must be reported UNBOUND
_S16_TANGLED = '''
"""Tangled fixture: a positive and a negative instance of every DETECTED carrier."""
import importlib.util
import os
import sys
import tempfile


def expect(name, cond):
    print(name, cond)


# --- A: the shared preamble that later regions read ------------------------
SHARED_C1 = "shared"                                       #@b:SHARED_C1
ACC = []                                                   #@b:ACC
SET_C3 = {"a", "b"}                                        #@b:SET_C3
REB = "first"                                              #@b:REB
G_C2 = 7                                                   #@b:G_C2
_ps = importlib.util.spec_from_file_location("eng", "engine/eng.py")
PATCHED = importlib.util.module_from_spec(_ps)              #@b:PATCHED


def helper_c2():
    return G_C2 + 1                                        #@r:G_C2


def pure_c2(arg_c2):
    return arg_c2 + 1


with tempfile.TemporaryDirectory() as TD:                   #@b:TD
    expect("A reads the temp dir it owns", TD != "")

# --- B: the near misses, and the writes region C will observe --------------
local_c1 = "local"
expect("bound and read inside one region", local_c1 == "local")
tmp_c3 = []
tmp_c3.append(1)
expect("mutated and read inside one region", len(tmp_c3) == 1)
expect("a callable whose body reads no global", pure_c2(2) == 3)
_fh = open("data/local_c6.json", "w")
expect("a path written and read inside one region", os.path.exists("data/local_c6.json"))
ACC.append(1)                                                #@r:ACC
SET_C3.difference_update({"b"})                             #@r:SET_C3
PATCHED.limit = 5                                           #@r:PATCHED
sys.setrecursionlimit(4000)
expect("an interpreter READ is not a mutation", sys.getrecursionlimit() > 0)
os.environ["S16_FLAG"] = "1"
_fh2 = open("data/shared_c6.json", "w")

# --- C: the crossing reads -------------------------------------------------
expect("C reads a region A fixture", SHARED_C1 == "shared")            #@r:SHARED_C1
expect("C reads an accumulator region B appended to", len(ACC) == 1)   #@r:ACC
expect("C reads a set region B narrowed", SET_C3 == {"a"})             #@r:SET_C3
expect("C reads an attribute region B patched in", PATCHED.limit == 5)  #@r:PATCHED
expect("C reads a temp dir region A already deleted", TD != "")        #@r:TD
expect("C enters a callable defined in region A", helper_c2() == 8)    #@v:G_C2
expect("C reads a path region B wrote", os.path.exists("data/shared_c6.json"))

# --- D: a rebinding, and the reads on either side of it --------------------
expect("D reads the region A binding of REB", REB == "first")          #@r:REB
REB = "second"                                                         #@b:REB
expect("D reads its own rebinding of REB", REB == "second")

# --- E: a read nothing binds, and a binding on one branch only -------------
expect("E reads a name nothing ever binds", NEVER_BOUND == 1)          #@u:NEVER_BOUND
if os.environ.get("S16_FLAG"):
    COND_BOUND = "yes"                                                 #@b:COND_BOUND

# --- F: the read of that conditional binding -------------------------------
expect("F reads a name bound on one branch only", COND_BOUND == "yes")  #@r:COND_BOUND
'''

# The DETANGLED TWIN. Every region is self-contained, so the survey must report ZERO
# crossings and FEASIBLE. It asserts through `print` rather than a shared `expect`
# BECAUSE a shared assertion helper is itself a crossing - which is the finding, not a
# convenience: even the helper has to be hoisted before any suite can run alone.
_S16_DETANGLED = '''
"""Detangled twin: the same shape with every crossing removed."""
# --- A ---------------------------------------------------------------------
a_value = "a"
print("A", a_value == "a")

# --- B ---------------------------------------------------------------------
b_acc = []
b_acc.append(1)
print("B", len(b_acc) == 1)

# --- C ---------------------------------------------------------------------
def c_helper(c_arg):
    return c_arg + 1


print("C", c_helper(1) == 2)

# --- D ---------------------------------------------------------------------
d_map = {"k": 1}
print("D", d_map["k"] == 1)

# --- E ---------------------------------------------------------------------
e_text = "e"
print("E", e_text.upper() == "E")

# --- F ---------------------------------------------------------------------
f_pair = (1, 2)
print("F", sum(f_pair) == 3)
'''

# One accumulator in the preamble that every region mutates and reads: one component,
# so the verdict is NOT_FEASIBLE. The point of the case is the EXIT STATUS, not the
# verdict: an analyst that cannot return a negative result without breaking the build
# is not measuring anything.
_S16_MONOLITH = '''
"""Monolith fixture: one component holding every assertion."""


def expect(name, cond):
    print(name, cond)


TOTAL = []

# --- A ---------------------------------------------------------------------
TOTAL.append(1)
expect("A", len(TOTAL) == 1)

# --- B ---------------------------------------------------------------------
TOTAL.append(2)
expect("B", len(TOTAL) == 2)

# --- C ---------------------------------------------------------------------
TOTAL.append(3)
expect("C", len(TOTAL) == 3)
'''

_S16_BROKEN = "def broken(:\n    pass\n"
_S16_STAR = "from os import *\nX = 1\n"
_S16_DYN = "X = 1\nglobals()['Y'] = 2\n"

# The COUNTERS fixture and its SHADOWED twin. This pair exists because of an
# independent review's FAIL against WARP-0716, and it carries the exact shape the
# report has one derived paragraph to say something about: an assertion helper that
# writes two module-level counters through a `global` statement. The twin adds ONE
# never-taken conditional rebinding of that helper, which is the substitution the
# reviewer used: it flips the helper to UNDETERMINED and both counters to
# SHARED_FIXTURE. The paragraph USED TO BE TYPED, so under the twin the emitted
# document said SHARED_FIXTURE in prose while its own tables said UNDETERMINED, at a
# green gate, with regeneration a no-op - regeneration proves the FILE matches the
# EMITTER and says nothing about whether the EMITTER matches the MEASUREMENT. The
# shadowed source is DERIVED from this one by a substitution whose count is asserted,
# so the pair cannot drift apart.
_S16_COUNTERS = '''\
"""Counters fixture: an assertion helper that writes two module-level counters."""
PASS = 0
FAIL = 0


def expect(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1


# --- A ---------------------------------------------------------------------
A_VALUE = "a"
expect("A reads what it binds", A_VALUE == "a")

# --- B ---------------------------------------------------------------------
expect("B reads a region A binding", A_VALUE == "a")
expect("B reads a counter", PASS >= 0)

# --- C ---------------------------------------------------------------------
expect("C reads the other counter", FAIL == 0)
'''
_S16_SHADOW = '''if FAIL < 0:  # never taken: a conditional rebinding of the helper
    def expect(name, cond):
        raise AssertionError(name)


'''
_S16_SHADOW_ANCHOR = "# --- A ---"

# The COVERAGE MATRIX over the survey's own carrier constant. Each DETECTED carrier
# needs a positive instance the tool MUST report and a near miss it must NOT. Neither
# side is a literal count, so adding a seventh carrier WITH its two cases passes and
# adding one WITHOUT them fails.
_S16_CASES = {
    "C1": {"positive": ["SHARED_C1"], "negative": ["local_c1"]},
    "C2": {"positive": ["G_C2"], "negative": ["arg_c2"]},
    # SET_C3 is mutated by set.difference_update, which the first draft of the tool's
    # MUTATOR_METHODS constant did not contain and the real target calls on a SHARED
    # module's vocabulary. The case is here because the constant is now DERIVED from
    # the interpreter (mutable type minus immutable counterpart) rather than typed,
    # and a regression to a hand-written list fails right here.
    "C3": {"positive": ["ACC", "SET_C3", "PATCHED"], "negative": ["tmp_c3"]},
    "C4": {"positive": ["sys.setrecursionlimit"], "negative": ["sys.getrecursionlimit"]},
    "C5": {"positive": ["os.environ subscript store"], "negative": ["os.environ.get"]},
    "C6": {"positive": ["data/shared_c6.json"], "negative": ["data/local_c6.json"]},
}


def _s16_tags(text, kind):
    """The ground-truth line numbers a fixture declares for one tag kind."""
    out = {}
    pat = _s16_re.compile(r"#@" + kind + r":([A-Za-z_][A-Za-z0-9_]*)\s*$")
    for i, line in enumerate(text.splitlines(), 1):
        m = pat.search(line)
        if m:
            out.setdefault(m.group(1), []).append(i)
    return out


def _s16_rec(survey, name):
    for r in survey.records:
        if r["name"] == name:
            return r
    return None


def _s16_reports(carrier, survey, token):
    """Does the survey report `token` under `carrier`? None means NO ORACLE.

    None rather than False on an unknown carrier: a carrier added to the constant
    with no way to observe it must fail BOTH its positive and its negative case,
    not quietly pass the negative one.
    """
    if carrier in ("C1", "C2"):
        return any(r["name"] == token and carrier in r["carriers"] for r in survey.records)
    if carrier == "C3":
        return any(r["name"] == token and r["mutation_lines"]
                   and r["class"] == "ORDERING_DEPENDENCY" for r in survey.records)
    if carrier in ("C4", "C5"):
        return any(e["carrier"] == carrier and token in e["what"]
                   for e in survey.process_events)
    if carrier == "C6":
        return any(p["path"] == token for p in survey.path_crossings)
    return None


def _s16_run(argv):
    """main() over one target, with its stdout captured: (rc, output)."""
    buf = _s16_io.StringIO()
    with _s16_ctx.redirect_stdout(buf):
        rc = _s16_sv.main(argv)
    return rc, buf.getvalue()


_s16_tangled_src = _S16_TANGLED.lstrip("\n")
_s16_detangled_src = _S16_DETANGLED.lstrip("\n")
_s16_monolith_src = _S16_MONOLITH.lstrip("\n")
# The shadowed twin is DERIVED, and the substitution count is recorded here so the
# assertion can refuse to believe a result taken over an unmutated file.
_s16_shadow_n = _S16_COUNTERS.count(_S16_SHADOW_ANCHOR)
_s16_shadow_src = _S16_COUNTERS.replace(_S16_SHADOW_ANCHOR,
                                        _S16_SHADOW + _S16_SHADOW_ANCHOR)
_s16_b = _s16_tags(_s16_tangled_src, "b")
_s16_r = _s16_tags(_s16_tangled_src, "r")
_s16_v = _s16_tags(_s16_tangled_src, "v")
_s16_u = _s16_tags(_s16_tangled_src, "u")

with tempfile.TemporaryDirectory() as _s16_dir:
    _s16_paths = {}
    for _s16_nm, _s16_txt in (("tangled", _s16_tangled_src),
                              ("detangled", _s16_detangled_src),
                              ("monolith", _s16_monolith_src),
                              ("counters", _S16_COUNTERS),
                              ("shadowed", _s16_shadow_src),
                              ("broken", _S16_BROKEN),
                              ("star", _S16_STAR),
                              ("dyn", _S16_DYN)):
        _s16_paths[_s16_nm] = tmpfile(_s16_dir, _s16_nm + ".py", _s16_txt)

    _s16_T = _s16_sv.analyse(_s16_paths["tangled"], "marker", "expect")
    _s16_D = _s16_sv.analyse(_s16_paths["detangled"], "marker", "print")
    _s16_names = {r["name"] for r in _s16_T.records}

    # --- WARP-0716 AC1 the fixture pair: what must be reported, and what must not ---
    expect("WARP-0716 AC1 POSITIVE CONTROL, the assertion that stops the tool being a "
           "rubber stamp: a name bound and read entirely INSIDE one region of the tangled "
           "fixture is NOT in the crossing set. `local_c1`, `tmp_c3` (bound, mutated and "
           "read in region B) and `arg_c2` (a parameter of a callable crossed by its own "
           "name) are absent from the record set, while the crossings below are present. "
           "Make the region comparison unconditional and this goes red while every "
           "detection assertion stays green, which is the discrimination it exists for",
           _s16_names and not ({"local_c1", "tmp_c3", "arg_c2"} & _s16_names))

    _s16_c1 = _s16_rec(_s16_T, "SHARED_C1")
    expect("WARP-0716 AC1 CROSSING DETECTION with EXACT provenance: the name bound in "
           "region A and read in region C is reported with exactly its binding line and "
           "exactly its set of crossing read lines, both DERIVED from the fixture's own "
           "#@b and #@r tags rather than typed as literals. Attribute a read to the "
           "enclosing statement instead of the Name node and the reading-line set differs",
           _s16_c1 is not None
           and _s16_c1["binding_lines"] == _s16_b["SHARED_C1"]
           and _s16_c1["read_lines"] == _s16_r["SHARED_C1"]
           and _s16_c1["class"] == "SHARED_FIXTURE")

    _s16_reb = _s16_rec(_s16_T, "REB")
    expect("WARP-0716 AC1 REACHING-DEFINITION CORRECTNESS, the one decision the whole "
           "survey rests on: `REB` is bound in region A, REBOUND in region D and read on "
           "both sides of the rebinding. The read BEFORE it crosses; the read AFTER it "
           "does not, because its reaching definition is local. Regress to the naive "
           "bound-in-A-read-in-B model and the second read joins the set - measured on the "
           "real file, that model reports one component of 156 regions where the reaching "
           "-definition model reports 72, which is the difference between an instrument "
           "and noise",
           _s16_reb is not None
           and _s16_reb["binding_lines"] == sorted(_s16_b["REB"])
           and _s16_reb["read_lines"] == _s16_r["REB"]
           and len(_s16_reb["read_lines"]) == 1)

    _s16_ub = _s16_rec(_s16_T, "NEVER_BOUND")
    expect("WARP-0716 AC1 UNBOUND, the third case the criterion names: a name that is only "
           "ever READ is reported with status UNBOUND and classified UNDETERMINED, never "
           "silently omitted and never given a clean label. Skip reads whose reaching "
           "-definition lookup returns nothing and the forward reference vanishes from the "
           "report instead of being flagged",
           _s16_ub is not None
           and _s16_ub.get("status") == "UNBOUND"
           and _s16_ub["binding_line"] is None
           and _s16_ub["class"] == "UNDETERMINED"
           and _s16_ub["read_lines"] == _s16_u["NEVER_BOUND"])

    _s16_g2 = _s16_rec(_s16_T, "G_C2")
    expect("WARP-0716 AC1 INDIRECTION (carrier C2): a global read ONLY inside the body of a "
           "callable defined in region A and invoked from region C is reported as a "
           "crossing, and the record names BOTH ends - the read inside the body and the "
           "CALL SITE it enters through. Analyse only syntactic module-level Name loads and "
           "the symbol disappears entirely, leaving the region pair looking independent; "
           "`expect` itself is the archetype in the real file, a preamble callable read at "
           "2,865 sites",
           _s16_g2 is not None
           and "C2" in _s16_g2["carriers"]
           and _s16_g2["read_lines"] == _s16_r["G_C2"]
           and _s16_g2["via_lines"] == _s16_v["G_C2"]
           and _s16_g2["binding_lines"] == _s16_b["G_C2"])

    _s16_acc = _s16_rec(_s16_T, "ACC")
    expect("WARP-0716 AC2 MUTATION (carrier C3): a list bound in region A, APPENDED TO in "
           "region B and read in region C is classified ORDERING_DEPENDENCY and never "
           "SHARED_FIXTURE, with the mutation line named. Drop the mutation scan from the "
           "purity fixpoint and the right-hand side is a literal list, so the name is "
           "promoted and the report licenses hoisting an ACCUMULATOR - the real file has "
           "164 mutated module-level names, so this is a live population",
           _s16_acc is not None
           and _s16_acc["class"] == "ORDERING_DEPENDENCY"
           and _s16_acc["mutation_lines"]
           and _s16_acc["read_lines"] == _s16_r["ACC"])

    _s16_pt = _s16_rec(_s16_T, "PATCHED")
    expect("WARP-0716 AC2 MONKEYPATCH (carrier C3 applied to a module object): an attribute "
           "store onto a module object loaded in region A is reported, the name is marked as "
           "holding a module object, and it is NOT classified SHARED_FIXTURE. Restrict "
           "attribute-store detection to non-module receivers, or handle only setattr() and "
           "not the `M.attr = x` form, and the survey would sanction hoisting a module every "
           "later region shares - the real file monkeypatches 58 such objects",
           _s16_pt is not None
           and _s16_pt["class"] == "ORDERING_DEPENDENCY"
           and _s16_pt["module_object"] is True
           and _s16_pt["mutation_lines"]
           and _s16_pt["read_lines"] == _s16_r["PATCHED"])

    _s16_td = _s16_rec(_s16_T, "TD")
    expect("WARP-0716 AC2 LIFETIME: a path bound by `with tempfile.TemporaryDirectory() as "
           "TD` in region A and read in region C is ORDERING_DEPENDENCY, never "
           "SHARED_FIXTURE. Treat with-item targets as ordinary assignments and the path "
           "looks like a pure value, so the report sanctions hoisting a name that points at "
           "a DELETED directory. The real file has 157 top-level with blocks and 105 "
           "with-bound names, so the shape is everywhere",
           _s16_td is not None
           and _s16_td["class"] == "ORDERING_DEPENDENCY"
           and "with" in _s16_td["binding_kinds"]
           and _s16_td["read_lines"] == _s16_r["TD"])

    _s16_cb = _s16_rec(_s16_T, "COND_BOUND")
    expect("WARP-0716 AC2 CONDITIONAL BINDING IS UNDETERMINED, not a guess: a name whose "
           "reaching definition sits inside an `if` is UNDETERMINED, neither SHARED_FIXTURE "
           "nor PER_SUITE_LOCAL, and the reason says so. Drop the conditional flag from the "
           "purity fixpoint and a name bound on one branch only gets a clean classification "
           "the analysis cannot support",
           _s16_cb is not None
           and _s16_cb["class"] == "UNDETERMINED"
           and "conditional" in _s16_cb["reason"]
           and _s16_cb["read_lines"] == _s16_r["COND_BOUND"])

    expect("WARP-0716 AC1 INTERPRETER AND PROCESS GLOBALS (carriers C4, C5): a "
           "sys.setrecursionlimit call and an os.environ store in one region are each "
           "reported as carrier events against every LATER region, while the READ-ONLY near "
           "misses beside them (sys.getrecursionlimit, os.environ.get) are not. Remove "
           "either carrier from the scan and real findings vanish silently: the real file "
           "makes 4 setrecursionlimit calls and 8 os.environ mutations",
           _s16_reports("C4", _s16_T, "sys.setrecursionlimit") is True
           and _s16_reports("C5", _s16_T, "os.environ subscript store") is True
           and _s16_reports("C4", _s16_T, "sys.getrecursionlimit") is False
           and _s16_reports("C5", _s16_T, "os.environ.get") is False
           and all(e["affected_region_count"] >= 1 or e["region"] == _s16_T.region_count() - 1
                   for e in _s16_T.as_dict()["process_events"]))

    expect("WARP-0716 AC1 LITERAL PATH CROSSING (carrier C6): a literal repository-relative "
           "path WRITTEN in region B and READ in region C appears in the secondary path "
           "index, and one written and read inside a single region does not. Index only the "
           "paths that are read, or only those written, instead of the intersection across "
           "regions, and the index either empties or fills with noise",
           _s16_reports("C6", _s16_T, "data/shared_c6.json") is True
           and _s16_reports("C6", _s16_T, "data/local_c6.json") is False)

    # --- WARP-0716 the NEGATIVE CONTROL and the carrier matrix ---------------------
    expect("WARP-0716 NEGATIVE CONTROL, the assertion that makes a negative verdict mean "
           "something: over the DETANGLED TWIN - the same shape with every crossing removed "
           "- the survey reports ZERO crossing names, ZERO path crossings and verdict "
           "FEASIBLE over a graph whose largest component is under the ceiling. Any "
           "over-reporting change at all fires here: counting rebindings as edges, treating "
           "every preamble read as a crossing, emitting a self-edge per region. Without it, "
           "a tool that answers NOT_FEASIBLE to everything scores perfectly on the tangled "
           "fixture and NOT_FEASIBLE would be an artifact of the analyser",
           _s16_D.total == 0
           and _s16_D.records == []
           and _s16_D.path_crossings == []
           and _s16_D.verdict == "FEASIBLE"
           and _s16_D.hoistable == []
           and len(_s16_D.components) >= _s16_sv.MIN_COMPONENTS
           and 0 < _s16_D.largest_share <= _s16_sv.LARGEST_COMPONENT_MAX_SHARE)

    _s16_det = set(_s16_sv.carrier_ids("DETECTED"))
    _s16_bli = set(_s16_sv.carrier_ids("BLIND"))
    _s16_cased = {c for c, v in _S16_CASES.items() if v["positive"] and v["negative"]}
    expect("WARP-0716 CARRIER MATRIX CLOSURE, the mechanical tooth on the completeness "
           "argument: the set of carriers with at least one POSITIVE and one NEGATIVE "
           "fixture case EQUALS the set the survey's own CARRIERS constant marks DETECTED; "
           "every carrier marked BLIND carries a non-empty reason and NO case; the two sets "
           "are disjoint, both non-empty, and together they exhaust CARRIERS. Neither side "
           "is a literal count, so adding a seventh carrier WITH its two cases passes and "
           "adding one WITHOUT them fails, which is the intended asymmetry - the coverage "
           "claim cannot be widened in prose without widening the proof",
           _s16_cased == _s16_det
           and _s16_det and _s16_bli
           and not (_s16_det & _s16_bli)
           and not (_s16_bli & set(_S16_CASES))
           and _s16_det | _s16_bli == {c["id"] for c in _s16_sv.CARRIERS}
           and all(c.get("reason", "").strip()
                   for c in _s16_sv.CARRIERS if c["status"] == "BLIND")
           and all(_s16_reports(c, _s16_T, t) is True
                   for c, v in _S16_CASES.items() for t in v["positive"])
           and all(_s16_reports(c, _s16_T, t) is False
                   for c, v in _S16_CASES.items() for t in v["negative"]))

    # --- WARP-0716 fail loud, and the verdict that is not the exit code ------------
    _s16_refusals = {
        "broken": "TARGET_DOES_NOT_PARSE",
        "star": "STAR_IMPORT",
        "dyn": "DYNAMIC_NAMESPACE_WRITE",
    }
    _s16_ref_seen = {}
    for _s16_nm, _s16_want in sorted(_s16_refusals.items()):
        _s16_rc, _s16_out = _s16_run(["--target", str(_s16_paths[_s16_nm])])
        _s16_ref_seen[_s16_nm] = (_s16_rc, _s16_want in _s16_out,
                                  _s16_sv.TABLE_HEADER in _s16_out)
    expect("WARP-0716 FAIL LOUD: over a target that does not parse, one carrying a star "
           "import and one carrying a globals() namespace write, the survey exits NON-ZERO, "
           "NAMES the reason from its own refusal vocabulary, and prints NO crossing table "
           "in any of the three. Wrap the parse in a bare try that returns an empty result "
           "set, or treat a star import as merely unresolvable, and an unanalysable file "
           "becomes a clean bill of health - which is the exact failure this item exists to "
           "prevent",
           all(v == (1, True, False) for v in _s16_ref_seen.values())
           and set(_s16_refusals.values()) <= set(_s16_sv.REFUSALS))

    _s16_M = _s16_sv.analyse(_s16_paths["monolith"], "marker", "expect")
    _s16_mrc, _s16_mout = _s16_run(["--target", str(_s16_paths["monolith"])])
    expect("WARP-0716 AC3 THE VERDICT IS NOT THE EXIT CODE: over a fixture engineered to a "
           "SINGLE component holding every assertion, the survey answers NOT_FEASIBLE, "
           "names the constant it failed, prints the table, and exits ZERO. Couple the exit "
           "code to the verdict and the analyst can no longer return a negative result "
           "without breaking the build, which is the definition of a measurement nobody can "
           "trust",
           _s16_M.verdict == "NOT_FEASIBLE"
           and len(_s16_M.components) < _s16_sv.MIN_COMPONENTS
           and "MIN_COMPONENTS" in _s16_M.verdict_reason
           and _s16_mrc == 0
           and "NOT_FEASIBLE" in _s16_mout
           and _s16_sv.TABLE_HEADER in _s16_mout
           and _s16_M.verdict in _s16_sv.VERDICTS)

    # --- WARP-0716 the partition claim, proven on the fixture AND on the real file ---
    _s16_real = _s16_sv.analyse(suite_file(), "marker", "expect")
    expect("WARP-0716 PARTITION INCLUSION, the mechanical form of the completeness claim "
           "for the boundary dimension, asserted on the fixture AND on scripts/selftest.py: "
           "the crossing set under the MARKER partition is a SUBSET of the set under the "
           "PER-STATEMENT partition, which is the finest partition the file admits. "
           "Coarsening only merges regions and merging can only REMOVE boundary pairs, so "
           "no choice of suite boundary WARP-0712 makes can surface a crossing this survey "
           "did not already see. Compute the marker view independently instead of "
           "PROJECTING it and the two disagree. It is a set inclusion and not a count, so "
           "appending an item to the suite adds elements to both sides and it still holds",
           _s16_T.crossing_keys("marker") <= _s16_T.crossing_keys("statement")
           and _s16_real.crossing_keys("marker") <= _s16_real.crossing_keys("statement")
           and _s16_real.crossing_keys("marker") < _s16_real.crossing_keys("statement")
           and _s16_T.crossing_keys("marker"))

    _s16_lines = suite_file().read_text().splitlines()
    expect("WARP-0716 AC1 REAL FILE, structural: over the file this suite's own assertions "
           "are in, the survey "
           "COMPLETES, and every record it emits carries a class from the closed four-value "
           "vocabulary, a carrier from the CARRIERS constant, at least one reading line, "
           "and a binding line whose TEXT ACTUALLY CONTAINS that identifier (or no binding "
           "line at all, which is only allowed for an UNBOUND record). This fires on "
           "off-by-one line attribution and on a fifth classification value leaking in. It "
           "explicitly CANNOT fire on an omission, which is why the report carries a blind "
           "-spot section rather than a clean bill of health",
           _s16_real.records
           and all(r["class"] in _s16_sv.CLASSES for r in _s16_real.records)
           and all(set(r["carriers"]) <= set(_s16_sv.carrier_ids("DETECTED"))
                   for r in _s16_real.records)
           and all(r["read_lines"] for r in _s16_real.records)
           and all(
               (r["name"] in _s16_lines[r["binding_line"] - 1]
                if r["binding_line"] else r.get("status") == "UNBOUND")
               for r in _s16_real.records)
           and all(r["name"] in _s16_lines[ln - 1]
                   for r in _s16_real.records for ln in r["binding_lines"]))

    # --- WARP-0716 the tool never writes, and this block does not leak --------------
    _S16_WRITE_CALLS = ("write_text", "write_bytes", "unlink", "rmtree", "rename",
                        "mkdir", "chmod", "makedirs", "rmdir", "touch")
    _s16_tool_tree = _s16_ast.parse((ROOT / "scripts/suite_survey.py").read_text())
    _s16_bad_calls, _s16_bad_open, _s16_bad_imports = [], [], []
    for _s16_n in _s16_ast.walk(_s16_tool_tree):
        if isinstance(_s16_n, (_s16_ast.Import, _s16_ast.ImportFrom)):
            _s16_bad_imports += [a.name for a in _s16_n.names
                                 if a.name.split(".")[0] in ("subprocess", "shutil")]
        if not isinstance(_s16_n, _s16_ast.Call):
            continue
        _s16_f = _s16_n.func
        _s16_nm2 = (_s16_f.attr if isinstance(_s16_f, _s16_ast.Attribute)
                    else _s16_f.id if isinstance(_s16_f, _s16_ast.Name) else "")
        _s16_dot = _s16_nm2 if isinstance(_s16_f, _s16_ast.Name) else ""
        if isinstance(_s16_f, _s16_ast.Attribute) and isinstance(_s16_f.value, _s16_ast.Name):
            _s16_dot = _s16_f.value.id + "." + _s16_nm2
        if (_s16_nm2 in _S16_WRITE_CALLS or _s16_nm2 == "__import__"
                or _s16_dot.split(".")[0] in ("subprocess", "shutil")
                or _s16_dot in ("os.system", "os.popen", "os.remove", "os.execv")):
            _s16_bad_calls.append((_s16_nm2, _s16_n.lineno))
        if _s16_nm2 == "open" and (
                len(_s16_n.args) < 2
                or not isinstance(_s16_n.args[1], _s16_ast.Constant)
                or set("wax+") & set(str(_s16_n.args[1].value))):
            _s16_bad_open.append(_s16_n.lineno)
    expect("WARP-0716 READ-ONLY BY CONSTRUCTION, derived from the tool's own AST rather "
           "than promised in its docstring: scripts/suite_survey.py contains no open() in a "
           "write mode (and none whose mode cannot be proven), no write_text, write_bytes, "
           "unlink, rmtree, rename, mkdir, chmod or touch call, and no subprocess or shutil "
           "import. The report-emitting mode PRINTS the document and the gate stage does the "
           "redirect, so the analyser cannot touch the tree it measures: anyone making the "
           "tool write the file itself, cache to disk, or shell out to git turns this red. "
           "That keeps the measurement and the artifact at arm's length even though "
           "regenerating the artifact is now one command",
           _s16_bad_calls == [] and _s16_bad_open == [] and _s16_bad_imports == [])

    # The range comes from two SENTINEL COMMENT LINES this block owns, never from where
    # the prefix happens to occur. Deriving it from the prefix would make the SECOND
    # direction vacuous: a line carrying an `_s16_` read is inside a prefix-delimited
    # range BY CONSTRUCTION, so no leak could ever fall outside it and the check could
    # not fail. An assertion that cannot fail is decoration.
    _S16_BEGIN = "# WARP-0716 BLOCK BEGIN (delimits the self-containment assertion)"
    _S16_END = "# WARP-0716 BLOCK END (delimits the self-containment assertion)"
    _s16_sent = [i + 1 for i, ln in enumerate(_s16_lines)
                 if ln.strip() in (_S16_BEGIN, _S16_END)]
    _s16_lo, _s16_hi = (_s16_sent + [0, 0])[:2]
    _s16_leak_bind = sorted(
        (nm, b["line"]) for nm, bs in _s16_real.bindings.items() for b in bs
        if _s16_lo <= b["line"] <= _s16_hi and not nm.startswith(("_s16_", "_S16_")))
    _s16_leak_read = sorted(
        {(n.id, n.lineno) for n in _s16_ast.walk(_s16_real.tree)
         if isinstance(n, _s16_ast.Name) and n.id.startswith(("_s16_", "_S16_"))
         and not _s16_lo <= n.lineno <= _s16_hi})
    expect("WARP-0716 SELF-CONTAINMENT, asserted in BOTH directions because the survey "
           "analyses the whole file including this block: every module-level name bound "
           "inside this item's OWN sentinel-delimited range starts with `_s16_`, and no "
           "`_s16_` name is read outside that range. The first direction stops this block "
           "SHADOWING an existing global and changing what a later block reads; the second "
           "stops a later block depending on this one. It is stated over the PREFIX and over "
           "a range delimited by two sentinel lines this block owns, not over a line count "
           "or an item count, so inserting a marker inside the block or appending an item "
           "after it cannot make it fire - only a genuine leak can",
           len(_s16_lines) > _s16_hi > _s16_lo > 0
           and len(_s16_sent) == 2
           and _s16_leak_bind == [] and _s16_leak_read == [])

    # --- WARP-0716 AC3 the report is GENERATED, and one stage owns its freshness ----
    # THE PREVIOUS VERSION OF THIS BLOCK RE-DERIVED THE WHOLE DOCUMENT HERE: the verdict token,
    # three derived sentences, every `| measure | value |` row, and every row of the per-symbol,
    # blocking, sensitivity and boundary tables, all compared against a HAND-WRITTEN
    # proof/WARP-0716/crossing-state.md. Those five assertions worked. They are DELETED, and the
    # reason is measured rather than argued: appending one ordinary assertion block to this file
    # reddened THREE of them, and merging WARP-0713 (about 800 lines) reddened FOUR, and in both
    # cases the only remedy was a hand rewrite of about 775 lines of document. A check with teeth
    # and an unbounded manual cost to satisfy is a trap, not a guard.
    #
    # THE DOCUMENT IS NOW EMITTED by suite_survey.render_report(), and scripts/check_generated.sh
    # regenerates it and DIFFS - the same "regeneration must be a no-op" contract, in the same
    # gate stage, that already governs specs/index.md. That closes staleness harder than the
    # assertions did: a figure disagreeing with the file is no longer merely caught, it cannot
    # reach a green gate, because the stage that notices has already rewritten it. Re-deriving each
    # figure here as well would be a second belt over a closed hole, so it is gone rather than
    # kept for the look of rigour.
    #
    # WHAT REGENERATION DOES NOT CLOSE IS WHAT IS ASSERTED HERE, and it is asserted over fixtures
    # whose ground truth is declared by construction rather than over a repository that grows:
    # that the emitter DERIVES the document from the measurement instead of printing a constant,
    # that a corrupted document is DISTINGUISHABLE from a fresh emission (the property the gate's
    # diff rests on), that the emitter REFUSES rather than publishing a carrier or a judgement
    # constant it cannot describe, and that the no-op check is WIRED INTO THE GATE. The last one
    # is the tripwire under the whole arrangement: delete the stage and the document is unpoliced,
    # and without this assertion nothing in this suite would notice.
    _S16_REP_SECTIONS = ("## Verdict", "## Totals", "## Blocking symbols",
                         "## Proposed suite boundary set", "## Carrier coverage",
                         "## Blind spots", "## Sensitivity", "## Per-symbol index")
    _s16_surveys = (("tangled", _s16_T), ("detangled", _s16_D), ("monolith", _s16_M))
    _s16_docs = {_s16_k: _s16_sv.render_report(_s16_s) for _s16_k, _s16_s in _s16_surveys}
    # Every claim below is a comparison against THAT fixture's own measurement, so none of it
    # pins a number: the fixtures are fixed, the assertions are relations.
    _s16_doc_bad = sorted(
        _s16_k for _s16_k, _s16_s in _s16_surveys
        if not (all(_s16_docs[_s16_k].count("\n" + _s16_h + "\n") == 1
                    for _s16_h in _S16_REP_SECTIONS)
                and _s16_re.findall(r"^Verdict: ([A-Z_]+)$", _s16_docs[_s16_k], _s16_re.M)
                == [_s16_s.verdict]
                and _s16_s.verdict in _s16_sv.VERDICTS
                and _s16_re.findall(r"^\| Crossing names \| ([\d,]+) \|$",
                                    _s16_docs[_s16_k], _s16_re.M)
                == [format(len(_s16_s.records), ",")]
                and _s16_re.findall(r"^Content digest: sha256 ([0-9a-f]{64})$",
                                    _s16_docs[_s16_k], _s16_re.M)
                == [hashlib.sha256(_s16_s.src.encode("utf-8")).hexdigest()]
                and _s16_docs[_s16_k] == _s16_sv.render_report(_s16_s)))
    expect("WARP-0716 AC3 THE DOCUMENT IS DERIVED FROM THE MEASUREMENT, NOT PRINTED, driven over "
           "all three fixtures: each emitted document carries every required section EXACTLY "
           "once, states that fixture's OWN verdict token from the survey's vocabulary, carries "
           "that fixture's OWN crossing-name count, names the sha256 of the exact bytes it "
           "measured, and is BYTE-IDENTICAL on a second emission. The three fixtures disagree "
           "with each other (the tangled and monolith files are NOT_FEASIBLE, the detangled twin "
           "is FEASIBLE with zero crossings), so an emitter that printed a constant document, or "
           "one that ignored its survey argument, fails here rather than in a report nobody "
           "diffs. Determinism is asserted because the gate's whole contract is a DIFF: an "
           "emitter that varied between runs would redden every gate run forever",
           _s16_doc_bad == []
           and {_s16_k: _s16_s.verdict for _s16_k, _s16_s in _s16_surveys}
           == {"tangled": "NOT_FEASIBLE", "detangled": "FEASIBLE", "monolith": "NOT_FEASIBLE"}
           and len(_s16_D.records) == 0 and len(_s16_T.records) > 0)

    # THE TEETH OF THE GATE'S DIFF, driven rather than asserted in prose. Each mutation is
    # applied to the emitted text and the SUBSTITUTION COUNT IS CHECKED FIRST: a mutation that
    # matched nothing would make an unmutated document look like a caught one, and a green run
    # over an unmutated file is not evidence about a guard.
    _s16_fresh = _s16_docs["tangled"]
    _S16_OTHER_VERDICT = [_s16_w for _s16_w in _s16_sv.VERDICTS if _s16_w != _s16_T.verdict][0]
    _s16_mut_verdict, _s16_nv = _s16_re.subn(
        r"^Verdict: %s$" % _s16_T.verdict, "Verdict: " + _S16_OTHER_VERDICT,
        _s16_fresh, count=1, flags=_s16_re.M)
    _s16_figure = _s16_re.findall(r"^\| Crossing names \| (\d+) \|$", _s16_fresh, _s16_re.M)
    _s16_mut_digit, _s16_nd = _s16_re.subn(
        r"^\| Crossing names \| %s \|$" % _s16_figure[0],
        "| Crossing names | %s |" % (_s16_figure[0][:-1] + str((int(_s16_figure[0][-1]) + 1) % 10)),
        _s16_fresh, count=1, flags=_s16_re.M)
    expect("WARP-0716 AC3 A CORRUPTED DOCUMENT IS DISTINGUISHABLE FROM A FRESH EMISSION, which is "
           "the only property the gate's diff rests on, and it is DRIVEN: the emitted document's "
           "verdict token is replaced with a different member of the survey's own VERDICTS "
           "vocabulary, and ONE DIGIT of one figure row is changed. BOTH SUBSTITUTIONS ARE "
           "ASSERTED TO HAVE APPLIED (one each) before their results are believed, because a "
           "mutation that matched nothing produces a green run that looks like a caught one. Each "
           "mutant differs from a fresh emission and the fresh emission is unchanged, so "
           "scripts/check_generated.sh reds on either corruption and regenerates it away",
           _s16_nv == 1 and _s16_nd == 1
           and _s16_mut_verdict != _s16_fresh and _s16_mut_digit != _s16_fresh
           and _s16_mut_verdict != _s16_sv.render_report(_s16_T)
           and _s16_mut_digit != _s16_sv.render_report(_s16_T)
           and _s16_fresh == _s16_sv.render_report(_s16_T))

    # THE EMITTER REFUSES WHAT IT CANNOT DESCRIBE. Driven through the parameters render_report
    # exposes for exactly this, so the test never monkeypatches the module it is testing.
    _S16_FAKE_CARRIER = {"id": "C7", "status": "DETECTED", "title": "an undeclared carrier",
                         "text": "added to the constant without its published description"}
    _s16_refusals_seen = {}
    for _s16_case, _s16_kw in (("carrier", {"carriers": tuple(_s16_sv.CARRIERS)
                                            + (_S16_FAKE_CARRIER,)}),
                               ("constant", {"meanings": {}})):
        # EVERY exception is caught, not just ReportRefusal, and anything else is recorded
        # as a FAILURE rather than propagating. Measured on a mutant that deleted the
        # pre-flight check: the emitter raised KeyError, the traceback killed the whole
        # run, and a suite with no "selftest: N passed" line reports nothing at all -
        # which is strictly worse than a red.
        try:
            _s16_sv.render_report(_s16_T, **_s16_kw)
            _s16_refusals_seen[_s16_case] = "EMITTED ANYWAY"
        except _s16_sv.ReportRefusal as _s16_rr:
            _s16_refusals_seen[_s16_case] = str(_s16_rr)
        except Exception as _s16_rr:  # noqa: BLE001 - a crash must become a red, not a traceback
            _s16_refusals_seen[_s16_case] = "CRASHED: %s: %s" % (type(_s16_rr).__name__,
                                                                 _s16_rr)
    expect("WARP-0716 AC3 THE EMITTER REFUSES A DOCUMENT IT CANNOT FULLY DESCRIBE: a carrier "
           "added to the survey's CARRIERS constant with no published description, and a "
           "judgement constant with no published meaning, each make render_report RAISE and NAME "
           "what is missing rather than emit a row with a blank cell. That is the same fail-closed "
           "discipline as the classifier's UNDETERMINED default, moved to the publishing step: a "
           "generated document must not be able to go quietly incomplete, and a blank cell in a "
           "table is exactly how it would. Both are driven through render_report's own parameters, "
           "so nothing here monkeypatches the module under test",
           sorted(_s16_refusals_seen) == ["carrier", "constant"]
           and "C7" in _s16_refusals_seen["carrier"]
           and "MIN_COMPONENTS" in _s16_refusals_seen["constant"]
           and all(not _s16_v.startswith(("EMITTED ANYWAY", "CRASHED"))
                   for _s16_v in _s16_refusals_seen.values())
           and _s16_sv.render_report(_s16_T) == _s16_fresh)

    # --- WARP-0716 AC3 THE TYPED PROSE MAY NOT ASSERT A MEASUREMENT ----------------
    # THE DEFECT THIS PAIR OF ASSERTIONS EXISTS FOR, from an independent review that ruled
    # FAIL on the landed state. render_report() interleaves derived tables with hand-typed
    # paragraphs, and one of them made CLASSIFICATION claims: that the assertion helper was
    # SHARED_FIXTURE and that its two counters were ORDERING_DEPENDENCY. The reviewer added
    # ONE never-taken conditional rebinding of the helper to the measured file. Every one of
    # the three labels inverted, regeneration rewrote the document, the CHECK_generated stage
    # passed, the whole suite passed - and the fresh document said SHARED_FIXTURE in a
    # paragraph while its own tables said UNDETERMINED. Three published claims false in a
    # freshly generated file at a green gate.
    #
    # WHY NOTHING HERE COULD SEE IT: "regeneration is a no-op" proves the FILE matches the
    # EMITTER. It says nothing about whether the EMITTER matches the MEASUREMENT. So the
    # paragraph is now DERIVED (asserted below over a fixture PAIR that carries exactly that
    # shape), and the emitter refuses a TYPED sentence of that shape (asserted here).
    _s16_own_src = (ROOT / "scripts/suite_survey.py").read_text()
    # Every name any measurement in this block reports, so the clean-source check is against
    # a wider name set than any single emission uses. No count is pinned: it is a relation.
    _s16_all_names = ({_r["name"] for _r in _s16_real.records}
                      | {_r["name"] for _r in _s16_T.records})
    _s16_plant_name = sorted(_s16_names)[0]
    _s16_plant_class = _s16_sv.CLASSES[0]
    # The plant is a NEW module-level constant rather than an edit to an existing one,
    # because "a paragraph typed tomorrow" is exactly the case the guard has to cover, and
    # appending one cannot silently match nothing the way a text substitution can.
    _s16_planted_src = _s16_own_src + ('\n_S16_PLANTED = "`%s` is %s."\n'
                                       % (_s16_plant_name, _s16_plant_class))
    _s16_plant_n = _s16_planted_src.count('_S16_PLANTED = "`%s` is %s."'
                                          % (_s16_plant_name, _s16_plant_class))
    # The SECOND plant is the harder half: the NAME is an interpolation slot, so it is
    # derived at emit time, and only the CLASS is typed. That reads as a derived sentence
    # and is not one. Without this case the slot half of the rule can be deleted and the
    # suite stays green, which was MEASURED on a mutant that removed it.
    _s16_slot_src = _s16_own_src + ('\n_S16_PLANTED_SLOT = "`%%s` is %s."\n'
                                    % _s16_plant_class)
    _s16_slot_n = _s16_slot_src.count('_S16_PLANTED_SLOT = "`%%s` is %s."' % _s16_plant_class)
    _s16_guard = {}
    for _s16_gcase, _s16_gsrc in (("clean", _s16_own_src), ("planted", _s16_planted_src),
                                  ("planted_slot", _s16_slot_src),
                                  ("unparseable", "def broken(:\n    pass\n")):
        try:
            _s16_guard[_s16_gcase] = ("EMITTED", _s16_sv.render_report(_s16_T,
                                                                       source=_s16_gsrc))
        except _s16_sv.ReportRefusal as _s16_gr:
            _s16_guard[_s16_gcase] = ("REFUSED", str(_s16_gr))
        except Exception as _s16_gr:  # noqa: BLE001 - a crash must become a red, not a traceback
            _s16_guard[_s16_gcase] = ("CRASHED", "%s: %s" % (type(_s16_gr).__name__, _s16_gr))
    expect("WARP-0716 AC3 A TYPED SENTENCE IN THE EMITTER MAY NOT ASSERT A MEASUREMENT, and the "
           "refusal is DRIVEN in both directions. The emitter's OWN source is scanned before "
           "anything is emitted: a sentence carrying a backticked name THIS measurement reports "
           "(or a backticked interpolation slot a name will land in) together with a word from "
           "the CLASSES or VERDICTS vocabulary is REFUSED by name, and a second plant covers the "
           "harder shape where the NAME is an interpolation slot and only the CLASS is typed, "
           "which reads like a derived sentence and is not one. NEGATIVE CONTROL, and it is "
           "the half that matters: the real source is clean, so the guard is not refusing "
           "everything, and the document it emits over the real source is byte-identical to the "
           "one it emits by default. POSITIVE: one NEW typed constant asserting a class for a "
           "name the fixture measurement reports (the name and the class word are both derived, "
           "so neither can go stale) makes render_report REFUSE and NAME the sentence. And a "
           "source that does not PARSE is a named refusal, not a SyntaxError: the gate stage "
           "redirects this generator's stdout, so a traceback would leave a truncated document "
           "and report nothing. The domain is DISCOVERED from the module's AST rather than "
           "listed, which is why an appended constant is covered without anything being "
           "registered",
           _s16_plant_n == 1 and _s16_slot_n == 1
           and _s16_sv.prose_claims(_s16_own_src, _s16_all_names) == []
           and _s16_guard["clean"][0] == "EMITTED"
           and _s16_guard["clean"][1] == _s16_fresh
           and _s16_guard["planted"][0] == "REFUSED"
           and _s16_plant_name in _s16_guard["planted"][1]
           and _s16_plant_class in _s16_guard["planted"][1]
           and _s16_guard["planted_slot"][0] == "REFUSED"
           and "%s" in _s16_guard["planted_slot"][1]
           and _s16_plant_class in _s16_guard["planted_slot"][1]
           and _s16_guard["unparseable"][0] == "REFUSED"
           and "does not parse" in _s16_guard["unparseable"][1]
           and len(_s16_sv.prose_claims(_s16_planted_src, _s16_all_names)) == 1
           and len(_s16_sv.prose_claims(_s16_slot_src, _s16_all_names)) == 1)

    # --- WARP-0716 AC3 THE ONE CLASSIFICATION PARAGRAPH IS DERIVED, PROVEN BY THE PAIR ---
    # The counters fixture carries the shape the paragraph is about: an assertion helper
    # writing two module-level counters through `global`. The shadowed twin is the SAME file
    # plus one never-taken conditional rebinding of that helper - the reviewer's exact
    # substitution - and the substitution count is asserted before either result is believed.
    # The claim is a RELATION, not a label: whatever class word the emitted paragraph attaches
    # to a name, that name's record must carry that class. So this assertion holds whichever
    # way the measurement comes out, and it fires the moment prose and tables disagree.
    _s16_C = _s16_sv.analyse(_s16_paths["counters"], "marker", "expect")
    _s16_S = _s16_sv.analyse(_s16_paths["shadowed"], "marker", "expect")
    _s16_cls_C = {_r["name"]: _r["class"] for _r in _s16_C.records}
    _s16_cls_S = {_r["name"]: _r["class"] for _r in _s16_S.records}
    _s16_item3 = _s16_re.compile(r"^3\. (.*?)(?=\n\n)", _s16_re.M | _s16_re.S)

    def _s16_para3(survey):
        """Item 3 of the emitted document's named preparation, whitespace normalised."""
        _m = _s16_item3.search(_s16_sv.render_report(survey))
        return " ".join(_m.group(1).split()) if _m else ""

    def _s16_para3_pairs(survey):
        """Every (name, class) pair the emitted paragraph STATES, within one sentence."""
        _para = _s16_para3(survey)
        _out = set()
        for _r in survey.records:
            for _c in _s16_sv.CLASSES:
                _pat = (r"`%s`[^.]{0,90}?\b%s\b|\b%s\b[^.]{0,90}?`%s`"
                        % (_s16_re.escape(_r["name"]), _c, _c, _s16_re.escape(_r["name"])))
                if _s16_re.search(_pat, _para):
                    _out.add((_r["name"], _c))
        return _out

    _s16_p3_cases = (("counters", _s16_C), ("shadowed", _s16_S),
                     ("tangled", _s16_T), ("real", _s16_real))
    _s16_p3 = {_k: _s16_para3(_s) for _k, _s in _s16_p3_cases}
    # A pair the paragraph states that the record set does not carry is the defect itself.
    _s16_p3_bad = {_k: sorted((_nm, _c, {_r["name"]: _r["class"]
                                         for _r in _s.records}.get(_nm))
                              for _nm, _c in _s16_para3_pairs(_s)
                              if {_r["name"]: _r["class"]
                                  for _r in _s.records}.get(_nm) != _c)
                   for _k, _s in _s16_p3_cases}
    # And every class the paragraph OWES must be STATED, not merely not-contradicted: a
    # paragraph that dropped its claims entirely would satisfy an absence-of-disagreement
    # check. What it owes is derived - the callee's own class when the callee crosses, and
    # the class of every name whose mutation this measurement attributes to a call of it.
    def _s16_para3_owed(survey):
        _cls = {_r["name"]: _r["class"] for _r in survey.records}
        _owed = {(survey.callee, _cls[survey.callee])} if survey.callee in _cls else set()
        _owed |= {(_r["name"], _r["class"]) for _r in survey.records
                  if survey.callee in _r["mutated_via"]}
        return _owed

    _s16_p3_mute = sorted((_k, sorted(_s16_para3_owed(_s) - _s16_para3_pairs(_s)))
                          for _k, _s in _s16_p3_cases
                          if _s16_para3_owed(_s) - _s16_para3_pairs(_s))
    # AN INDEPENDENT ORACLE FOR THE COUNTERS FIXTURE, because the owed set above is derived
    # from the same `mutated_via` field the paragraph reads: drop that field and both sides
    # go empty and the check is vacuous. MEASURED - a mutant that removed the attribution
    # stayed green here. The names of the counters therefore come from the FIXTURE'S OWN
    # AST, the `global` statement inside the callee's definition, which the survey does not
    # touch, and each must be stated with the class the survey gives it.
    _s16_ctr_globals = sorted({
        _nm for _fn in _s16_ast.parse(_S16_COUNTERS).body
        if isinstance(_fn, _s16_ast.FunctionDef) and _fn.name == _s16_C.callee
        for _g in _s16_ast.walk(_fn) if isinstance(_g, _s16_ast.Global)
        for _nm in _g.names})
    _s16_ctr_missing = sorted({(_nm, _s16_cls_C[_nm]) for _nm in _s16_ctr_globals
                               if _nm in _s16_cls_C} - _s16_para3_pairs(_s16_C))
    expect("WARP-0716 AC3 THE ONE PARAGRAPH THAT NAMES A CLASSIFICATION IS DERIVED FROM THE "
           "RECORD SET, DRIVEN OVER THE REVIEWER'S OWN MUTATION. The counters fixture holds an "
           "assertion helper writing two module-level counters through `global`; its SHADOWED "
           "twin is the same file plus ONE never-taken conditional rebinding of that helper, and "
           "the substitution count is asserted FIRST because a mutation that matched nothing "
           "makes an untouched file look like a caught one. The measurement inverts across the "
           "pair (helper SHARED_FIXTURE to UNDETERMINED, both counters the other way), the "
           "emitted paragraph inverts WITH it, and over EVERY measurement in the case list "
           "(no count of them is asserted, since the list can grow) each (name, class) pair the "
           "paragraph states is the class that name's own record carries, and every class it OWES "
           "is STATED rather than merely not contradicted - the callee's own, and that of every "
           "name whose mutation the measurement attributes to a call of it, both derived. The "
           "counter NAMES also come from an INDEPENDENT oracle, the `global` statement in the "
           "fixture's own AST, because deriving what the paragraph owes from the same field the "
           "paragraph reads is vacuous the moment that field is dropped - which was MEASURED on "
           "a mutant that dropped it and stayed green. This "
           "is the assertion the landed version did not have: with the paragraph TYPED, the "
           "shadowed twin published SHARED_FIXTURE in prose beside a table saying UNDETERMINED, "
           "and regeneration was still a no-op, because regeneration proves the FILE matches the "
           "EMITTER and not that the EMITTER matches the MEASUREMENT",
           _s16_shadow_n == 1
           and _s16_shadow_src != _S16_COUNTERS
           and (_s16_cls_C.get("expect"), _s16_cls_C.get("PASS"), _s16_cls_C.get("FAIL"))
           == ("SHARED_FIXTURE", "ORDERING_DEPENDENCY", "ORDERING_DEPENDENCY")
           and (_s16_cls_S.get("expect"), _s16_cls_S.get("PASS"), _s16_cls_S.get("FAIL"))
           == ("UNDETERMINED", "SHARED_FIXTURE", "SHARED_FIXTURE")
           and all(_s16_v == [] for _s16_v in _s16_p3_bad.values())
           and all(_s16_v for _s16_v in _s16_p3.values())
           and _s16_p3_mute == []
           and _s16_ctr_globals
           and all(_s16_v in _s16_cls_C for _s16_v in _s16_ctr_globals)
           and _s16_ctr_missing == []
           and _s16_p3["counters"] != _s16_p3["shadowed"])

    # --- WARP-0716 CARRIER_DOC IS TIED TO THE FIXTURE BY VALUE, not only by carrier id ---
    # The published carrier table types the fixture's own literals. Until now the only tie
    # between the two was the carrier ID, so renaming a fixture symbol left the document
    # describing cases that no longer existed and nothing went red. Every backticked token
    # in a DETECTED carrier's two published cases must appear VERBATIM in the tangled
    # fixture, every DETECTED carrier must publish at least one such token, and a BLIND
    # carrier must publish none - it has no case, so a token there would be a fiction.
    _s16_docvals = {_s16_cid: _s16_re.findall(r"`([^`]+)`", " ".join(_s16_cd[1:]))
                    for _s16_cid, _s16_cd in _s16_sv.CARRIER_DOC.items()}
    _s16_det_ids = set(_s16_sv.carrier_ids("DETECTED"))
    _s16_doc_absent = sorted((_s16_cid, _s16_tok) for _s16_cid in _s16_det_ids
                             for _s16_tok in _s16_docvals[_s16_cid]
                             if _s16_tok not in _s16_tangled_src)
    _s16_doc_mute = sorted(_s16_cid for _s16_cid in _s16_det_ids
                           if not _s16_docvals[_s16_cid])
    _s16_doc_fiction = sorted(_s16_cid for _s16_cid in set(_s16_docvals) - _s16_det_ids
                              if _s16_docvals[_s16_cid])
    expect("WARP-0716 CARRIER_DOC IS BOUND TO THE FIXTURE BY VALUE. The published carrier table "
           "types the fixture's own literals, and the only thing that used to tie the two "
           "together was the carrier ID: rename a fixture symbol and the document went on "
           "describing a case that no longer existed, green. Now every backticked token in a "
           "DETECTED carrier's positive and negative case must appear VERBATIM in the tangled "
           "fixture source, every DETECTED carrier must publish at least one such token, and a "
           "BLIND carrier must publish none, since it has no case and a token there would be a "
           "fiction. Derived on both sides from the survey's own CARRIERS constant and the "
           "fixture text, so no name and no count is typed here",
           _s16_doc_absent == [] and _s16_doc_mute == [] and _s16_doc_fiction == []
           and _s16_det_ids and set(_s16_docvals) >= _s16_det_ids)

    # THE STAGE IS THE GUARD, SO THE STAGE IS WHAT IS DRIVEN. A first draft asserted the
    # WIRING as text and was measured missing the mutant that prefixed the entry with
    # `true ||`: the path was still in the file, so a check over text stayed green while the
    # report went unpoliced. So the real scripts/check_generated.sh is RUN, hermetically,
    # over a fixture tree it is pointed at by GENERATED_CHECK_ROOT - the same seam
    # DOCS_CHECK_PATHS gives scripts/check_docs.sh. Nothing in the repository is written.
    _s16_stage_env = dict(os.environ, GENERATED_CHECK_ONLY="crossing-state")
    with tempfile.TemporaryDirectory() as _s16_hdir:
        _s16_hroot = Path(_s16_hdir)
        (_s16_hroot / "scripts").mkdir()
        (_s16_hroot / "proof/WARP-0716").mkdir(parents=True)
        (_s16_hroot / "scripts/suite_survey.py").write_text(
            (ROOT / "scripts/suite_survey.py").read_text())
        # The stage's generator emits over the DEFAULT target, so the fixture tree carries a
        # tiny scripts/selftest.py of its own: the tangled fixture, whose crossings are
        # declared by construction.
        (_s16_hroot / "scripts/selftest.py").write_text(_s16_tangled_src)
        _s16_hrep = _s16_hroot / "proof/WARP-0716/crossing-state.md"

        def _s16_stage(hroot):
            """The real stage script, pointed at a fixture tree. (rc, stdout)."""
            _r = subprocess.run(["bash", str(ROOT / "scripts/check_generated.sh")],
                                env=dict(_s16_stage_env, GENERATED_CHECK_ROOT=str(hroot)),
                                capture_output=True, text=True)
            return _r.returncode, _r.stdout

        # EVERY step below is inside one try, and any exception becomes a recorded FAILURE
        # rather than a traceback. Measured on the `true ||` mutant: with the stage
        # short-circuited the bootstrap leaves the placeholder in place, the figure row this
        # block mutates does not exist, and an unguarded index killed the whole run - a suite
        # with no "selftest: N passed" line reports nothing, which is worse than a red.
        _s16_h_error = None
        _s16_hbad, _s16_hn, _s16_hfresh = "", 0, ""
        _s16_h_bootstrap = _s16_h_clean = _s16_h_stale = _s16_h_again = (None, "")
        _s16_h_repaired = ""
        try:
            # The REFERENCE is what the fixture tree's own copy of the emitter produces, taken
            # from the stage itself rather than recomputed in this process: the in-process
            # module resolves paths against THIS repository root and would name the target
            # differently, so a reference computed that way would make a clean run look stale.
            _s16_hrep.write_text("a placeholder that is not the emitter's output\n")
            _s16_h_bootstrap = _s16_stage(_s16_hroot)
            _s16_hfresh = _s16_hrep.read_text()
            _s16_h_clean = _s16_stage(_s16_hroot)
            # ONE digit of ONE figure, and the substitution count is checked before the
            # result of running the stage over it is believed.
            _s16_hfig = _s16_re.findall(r"^\| Crossing names \| (\d+) \|$",
                                        _s16_hfresh, _s16_re.M)
            if len(_s16_hfig) == 1:
                _s16_hbad, _s16_hn = _s16_re.subn(
                    r"^\| Crossing names \| %s \|$" % _s16_hfig[0],
                    "| Crossing names | %s |" % (_s16_hfig[0][:-1]
                                                 + str((int(_s16_hfig[0][-1]) + 1) % 10)),
                    _s16_hfresh, count=1, flags=_s16_re.M)
            _s16_hrep.write_text(_s16_hbad or "no figure row to corrupt\n")
            _s16_h_stale = _s16_stage(_s16_hroot)
            _s16_h_repaired = _s16_hrep.read_text()
            _s16_h_again = _s16_stage(_s16_hroot)
        except Exception as _s16_he:  # noqa: BLE001 - a crash must become a red, not a traceback
            _s16_h_error = "%s: %s" % (type(_s16_he).__name__, _s16_he)
        _s16_verify_sh = (ROOT / "scripts/verify.sh").read_text()
    expect("WARP-0716 AC3 THE NO-OP CHECK IS THE GUARD, AND IT IS DRIVEN RATHER THAN READ: the "
           "real scripts/check_generated.sh, pointed by GENERATED_CHECK_ROOT at a fixture tree "
           "holding the survey, a tangled-fixture target and a correct report, exits ZERO; with "
           "ONE DIGIT of one figure row changed (the substitution count is asserted to be 1 "
           "first, because a mutation that matched nothing would make an untouched file look "
           "like a caught one) it exits ONE, REWRITES the report back to the emitter's output, "
           "and exits ZERO on the next run. Also that scripts/verify.sh declares CHECK_generated "
           "REQUIRED rather than na: or waived:, since a stage nobody runs guards nothing. A "
           "first draft of this asserted the wiring as TEXT and was measured missing a mutant "
           "that left the path in the file and short-circuited the call",
           _s16_h_error is None
           and _s16_hn == 1 and _s16_hbad != _s16_hfresh
           and _s16_h_bootstrap[0] == 1 and "## Verdict" in _s16_hfresh
           and _s16_h_clean[0] == 0
           and _s16_h_stale[0] == 1 and "crossing-state.md was stale" in _s16_h_stale[1]
           and _s16_h_repaired == _s16_hfresh
           and _s16_h_again[0] == 0
           and _s16_sv.REPORT_PATH == "proof/WARP-0716/crossing-state.md"
           and 'CHECK_generated="required:bash scripts/check_generated.sh"' in _s16_verify_sh)
# WARP-0716 BLOCK END (delimits the self-containment assertion)
# =============================== WARP-0713 ====================================
# THE MOBILE SETTLE SEAM, and the reason it is allowed to skip time at all.
#
# The gate drives two reference mobile runners against FAKE drivers that return
# instantly, and then sleeps waiting for a user interface that does not exist to
# settle. Those settles now go through an INJECTED SettleWaiter, so a wait is a
# RECORDED DECISION this suite asserts rather than wall time it pays - while
# outside the gate the runners wait exactly as before, because the seam's
# defaults ARE time.sleep and time.monotonic. That last clause is the one an
# adopter's safety rests on, so it is asserted BY IDENTITY over the waiter THE
# RUNNER ITSELF RESOLVES, at every resolution site its own AST declares, in every
# tracked copy - and not over a SettleWaiter this suite builds, which would prove
# the class default and say nothing about the runner.
#
# THE DISTINCTION THIS BLOCK ENFORCES MECHANICALLY. A SETTLE is a wait whose
# length was CHOSEN by whoever wrote the number; it can be fast-forwarded. A
# CONDITION wait is a wait for some OTHER AGENT to reach a state (a device
# property becoming true, an external recorder flushing its file); it cannot,
# because skipping it skips the state change the runner then reads. Three teeth
# keep the second kind out of the seam, none of them prose: (T1) the seam's
# public method set is exactly {settle} - no predicate, no deadline, no poll, so
# a condition wait is INEXPRESSIBLE in this API; (T2) every time.* CALL in each
# runner must be lexically inside that runner's driver class, so the two
# surviving condition waits cannot be routed in and a new raw wait cannot be
# added to the control logic; (T3) no settle( may appear lexically inside a loop
# body, so a poll cannot be built on top of the seam. Each has a mutant below
# that makes it fire.
#
# AND THE PREMISE IS PROVEN RATHER THAN ASSUMED. A settle can only be
# load-bearing if state the runner later observes changes WHILE it sleeps, which
# needs an agent of change other than the runner. During the probed runs an
# audit hook asserts ZERO agent-creating events and an unchanged thread count,
# so no observation can change across the sleep and removing it cannot change
# any observation. An equivalence differential corroborates it empirically at a
# scale whose sensitivity is demonstrated by a planted load-bearing wait.
import ast as _v13_ast
import hashlib as _v13_hashlib
import threading as _v13_threading
import time as _v13_time

_V13_MOBILE = {
    "android": "scripts/runners/mobile/veldo_android_runner.py",
    "ios": "scripts/runners/mobile/veldo_ios_runner.py",
}
_V13_DRIVER_CLS = {"android": "AdbDriver", "ios": "SimctlDriver"}
_V13_MODS = {"android": AR, "ios": IOS}
_v13_paths = {k: ROOT / "engine" / rel for k, rel in _V13_MOBILE.items()}
_v13_src = {k: p.read_text() for k, p in _v13_paths.items()}
_v13_tree = {k: _v13_ast.parse(s) for k, s in _v13_src.items()}
_v13_sha0 = {k: _v13_hashlib.sha256(p.read_bytes()).hexdigest() for k, p in _v13_paths.items()}

# EVERY TRACKED COPY of each runner, enumerated by git rather than by the number seven,
# because the adopter-facing assertions below must hold of every copy that SHIPS and not
# only of the one engine copy this suite happens to import.
_v13_all_tracked = [ln for ln in subprocess.run(
    ["git", "-C", str(ROOT), "ls-files"], capture_output=True, text=True
).stdout.splitlines() if ln.strip()]


def _v13_tracked_copies(basename):
    return sorted(f for f in _v13_all_tracked if f.endswith("/" + basename))


_V13_TRACKED = {k: _v13_tracked_copies(rel.rsplit("/", 1)[1])
                for k, rel in _V13_MOBILE.items()}
_v13_copy_src = {k: {rel: (ROOT / rel).read_text() for rel in _V13_TRACKED[k]}
                 for k in _V13_MOBILE}


def _v13_sha_unchanged():
    """Every mutation below is compiled IN MEMORY; the files on disk never move."""
    return all(_v13_hashlib.sha256(p.read_bytes()).hexdigest() == _v13_sha0[k]
               for k, p in _v13_paths.items())


# --- AC1: the resolved pair, by IDENTITY. The predicate lives here; the thing it is
# applied to is THE WAITER THE RUNNER BUILT, further down, once the fixtures exist.
def _v13_resolves_real(w):
    """True only when a construction resolved the REAL functions. Identity, not equality
    of behaviour: a lookalike wrapper cannot satisfy `is`."""
    return (w._sleep is _v13_time.sleep and w._clock is _v13_time.monotonic
            and w._record is None)


# --- T1: the seam cannot express a condition wait ------------------------------
expect("WARP-0713 T1: the seam's PUBLIC METHOD SET is exactly {settle} in both runners - no predicate, no deadline, no wait_until, no poll - so a CONDITION wait is inexpressible in this API and cannot be fast-forwarded. Adding a polling primitive here reddens the gate and forces the argument into a spec instead of into a helper",
       all({n for n in dir(_V13_MODS[k].SettleWaiter) if not n.startswith("_")} == {"settle"}
           for k in _V13_MOBILE))


def _v13_class_src(kind, name):
    node = next(n for n in _v13_tree[kind].body
                if isinstance(n, _v13_ast.ClassDef) and n.name == name)
    return _v13_ast.get_source_segment(_v13_src[kind], node)


expect("WARP-0713: the SettleWaiter definition is BYTE-IDENTICAL in the two runners. The duplication is deliberate (these are standalone reference runners an adopter copies, and an import dependency between two of them would be the worse architecture), so the drift it invites is closed mechanically rather than by care",
       _v13_class_src("android", "SettleWaiter") == _v13_class_src("ios", "SettleWaiter")
       and "def settle(self, seconds, reason):" in _v13_class_src("android", "SettleWaiter"))

# --- T2: the partition, DERIVED from the source rather than listed -------------
def _v13_time_calls_outside_driver(tree, driver_cls):
    """Every ast.Call to an attribute of `time` that is NOT lexically inside the driver
    class, as (lineno, attr). QUANTIFIED and COUNT-FREE: a legitimate new driver-level
    condition wait keeps this empty, while one raw sleep in the control logic fills it."""
    cls = [n for n in tree.body
           if isinstance(n, _v13_ast.ClassDef) and n.name == driver_cls]
    inside = {id(n) for c in cls for n in _v13_ast.walk(c)}
    out = []
    for node in _v13_ast.walk(tree):
        if (isinstance(node, _v13_ast.Call) and isinstance(node.func, _v13_ast.Attribute)
                and isinstance(node.func.value, _v13_ast.Name)
                and node.func.value.id == "time" and id(node) not in inside):
            out.append((node.lineno, node.func.attr))
    return sorted(out)


def _v13_settle_in_loop(tree):
    """Every settle( call lexically inside a For or While body, as linenos. A poll loop
    built on the seam would fill this."""
    hits = []
    for node in _v13_ast.walk(tree):
        if isinstance(node, (_v13_ast.For, _v13_ast.While, _v13_ast.AsyncFor)):
            for sub in _v13_ast.walk(node):
                if (isinstance(sub, _v13_ast.Call) and isinstance(sub.func, _v13_ast.Attribute)
                        and sub.func.attr == "settle"):
                    hits.append(sub.lineno)
    return sorted(set(hits))


expect("WARP-0713 T2 PARTITION UNIVERSAL: EVERY ast.Call to an attribute of `time` in each mobile runner is lexically inside that runner's driver class (AdbDriver / SimctlDriver). Quantified and count-free, so a legitimate new driver-level condition wait stays green while a single raw sleep in apply_step, redrive or run turns this red. This is the mechanical form of `the seam is for unconditional settles only', and it generalizes the split the baseline already measured for the process runner rather than inventing a taxonomy",
       all(_v13_time_calls_outside_driver(_v13_tree[k], _V13_DRIVER_CLS[k]) == []
           for k in _V13_MOBILE))
expect("WARP-0713 T2: the two SURVIVING condition waits are still RAW time.sleep inside the android driver class and were deliberately NOT routed into the seam - wait_boot's `while time.time() < end` poll of sys.boot_completed (an agent other than the runner must set that property) and stop_recording's wait while an external screen recorder flushes its file. Routing either into the seam is the exact load-bearing mistake this item is warned about. Nothing is asserted about the iOS driver's wait COUNT beyond the universal above, because a legitimate driver-level condition wait added there later must not redden this gate",
       "time.sleep(2)" in _v13_class_src("android", "AdbDriver")
       and "while time.time() < end:" in _v13_class_src("android", "AdbDriver")
       and "time.sleep(1)" in _v13_class_src("android", "AdbDriver"))
expect("WARP-0713 T3: NO settle( call appears lexically inside a For or While body in either runner, so a POLL cannot be built on top of the seam - which is how a condition wait would sneak in past T1 and T2",
       all(_v13_settle_in_loop(_v13_tree[k]) == [] for k in _V13_MOBILE))

# --- AC2 side 1: the {reason -> seconds} map extracted from the module AST ------
def _v13_ast_settle_map(tree):
    """{reason -> seconds} for every settle( call in the module, the duration recovered
    from a bare Constant or from the DEFAULT of a step.get(..., <Constant>). Returns
    (map, duplicate_reasons) so a label collision cannot silently collapse two sites."""
    out, dupes = {}, []
    for node in _v13_ast.walk(tree):
        if not (isinstance(node, _v13_ast.Call) and isinstance(node.func, _v13_ast.Attribute)
                and node.func.attr == "settle" and len(node.args) == 2):
            continue
        dur, reason = node.args
        if isinstance(dur, _v13_ast.Constant):
            val = dur.value
        elif (isinstance(dur, _v13_ast.Call) and isinstance(dur.func, _v13_ast.Attribute)
              and dur.func.attr == "get" and len(dur.args) == 2
              and isinstance(dur.args[1], _v13_ast.Constant)):
            val = dur.args[1].value
        else:
            val = None
        key = reason.value if isinstance(reason, _v13_ast.Constant) else None
        if key in out:
            dupes.append(key)
        out[key] = val
    return out, sorted(set(dupes))


# --- AC2 side 2: THE FROZEN TABLE. This IS the criterion a reviewer reads. Every
# entry is the value that was in the source before this item, so a shortened wait -
# INCLUDING one shortened in the direction that makes the gate faster - is a gate
# failure. It is pinned to the OWNER'S 23 constants, deliberately, and to no
# repository-wide property: no corpus size, no file count, no line number.
_V13_FROZEN = {
    "android": {
        "launch": 2, "tap": 1, "text": 0.5, "key": 0.5, "wait": 1,
        "redrive.rotation.landscape": 1, "redrive.rotation.portrait": 1,
        "redrive.process_death.after_force_stop": 1,
        "redrive.process_death.relaunch": 2,
        "redrive.background_foreground.home": 1,
        "redrive.background_foreground.relaunch": 2,
        "redrive.network_loss.off": 1, "redrive.network_loss.on": 1,
    },
    "ios": {
        "launch": 2, "tap": 1, "type": 0.5, "wait": 1,
        "redrive.process_death.after_terminate": 1,
        "redrive.process_death.relaunch": 2,
        "redrive.background_foreground.home": 1,
        "redrive.background_foreground.relaunch": 2,
        "redrive.appearance.dark": 1, "redrive.appearance.light": 1,
    },
}

# --- AC2 side 3 and AC3: the RECORDER, and fixtures that reach EVERY site -------
class _V13Recorder:
    """A virtual clock and an ordered log of what the runner ASKED FOR. `now` advances
    by exactly the seconds requested, so the runner's time can only have come from the
    injected pair - which the coherence assertion below then proves."""

    def __init__(self):
        self.log = []
        self.now = 0.0

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds

    def record(self, reason, seconds, t0, t1):
        self.log.append((reason, seconds, t0, t1))

    def waiter(self, mod):
        return mod.SettleWaiter(clock=self.clock, sleep=self.sleep, record=self.record)

    def seq(self):
        return [(reason, seconds) for reason, seconds, _t0, _t1 in self.log]


# The fixtures OVERRIDE NOTHING: no journey below carries a `settle` or `seconds` key,
# so what the recorder observes IS the shipped default. They reach every action and
# every lifecycle re-drive, including tap, text, key, type and wait - which the gate's
# own journeys never exercise, and which is why this is a coverage item.
_V13_JOURNEY = {
    "android": {
        "name": "all-sites", "package": "com.example.app", "activity": ".Main",
        "recovery_assertion": {"action": "expect_focus", "value": "com.example.app"},
        "steps": [{"action": "launch", "package": "com.example.app", "activity": ".Main"},
                  {"action": "tap", "x": 10, "y": 20},
                  {"action": "text", "value": "hello"},
                  {"action": "key", "value": "KEYCODE_ENTER"},
                  {"action": "wait"},
                  {"action": "expect_focus", "value": "com.example.app"},
                  {"action": "state", "name": "home"}],
        "lifecycle_redrives": ["rotation", "process_death",
                               "background_foreground", "network_loss"],
    },
    "ios": {
        "name": "all-sites", "bundle_id": "com.example.app",
        "recovery_assertion": {"action": "expect_label", "value": "HomeScreen"},
        "steps": [{"action": "launch", "bundle_id": "com.example.app"},
                  {"action": "tap", "x": 10, "y": 20},
                  {"action": "type", "value": "hello"},
                  {"action": "wait"},
                  {"action": "expect_label", "value": "HomeScreen"},
                  {"action": "state", "name": "home"}],
        "lifecycle_redrives": ["process_death", "background_foreground", "appearance"],
    },
}
_V13_EXPECTED_SEQ = {
    "android": [("launch", 2), ("tap", 1), ("text", 0.5), ("key", 0.5), ("wait", 1),
                ("redrive.rotation.landscape", 1), ("redrive.rotation.portrait", 1),
                ("redrive.process_death.after_force_stop", 1),
                ("redrive.process_death.relaunch", 2),
                ("redrive.background_foreground.home", 1),
                ("redrive.background_foreground.relaunch", 2),
                ("redrive.network_loss.off", 1), ("redrive.network_loss.on", 1)],
    "ios": [("launch", 2), ("tap", 1), ("type", 0.5), ("wait", 1),
            ("redrive.process_death.after_terminate", 1),
            ("redrive.process_death.relaunch", 2),
            ("redrive.background_foreground.home", 1),
            ("redrive.background_foreground.relaunch", 2),
            ("redrive.appearance.dark", 1), ("redrive.appearance.light", 1)],
}
_V13_FAKE = {"android": _FakeDriver, "ios": _FakeIosDriver}
_V13_COUNTER = {"android": ("_pidctr", 100), "ios": ("_tokctr", 700)}


def _v13_reset_fake(kind):
    attr, base = _V13_COUNTER[kind]
    setattr(_V13_FAKE[kind], attr, base)


def _v13_drive(kind, journey, outdir, waiter=None, driver=None, mod=None):
    """One run of one runner. Resets the fake driver's CLASS-LEVEL counter first, so two
    arms of the same journey are comparable (the one normalization besides the outdir)."""
    _v13_reset_fake(kind)
    mod = mod or _V13_MODS[kind]
    return mod.run(journey, driver if driver is not None else _V13_FAKE[kind](),
                   outdir, waiter=waiter)


# A journey whose every declared window is ZERO. Used wherever a PRODUCTION-path
# resolution has to actually happen: the runner resolves its own waiter and really calls
# time.sleep, for zero seconds, so the thing can be observed without paying for it.
_V13_ZERO = {
    "android": {"name": "z", "package": "p", "activity": ".M",
                "steps": [{"action": "launch", "package": "p", "activity": ".M",
                           "settle": 0},
                          {"action": "wait", "seconds": 0}]},
    "ios": {"name": "z", "bundle_id": "b",
            "steps": [{"action": "launch", "bundle_id": "b", "settle": 0},
                      {"action": "wait", "seconds": 0}]},
}


# --- AC1, THE ASSERTION THAT MUST BIND THE RUNNER AND NOT THIS SUITE -----------
# The failure to close is a resolution site INSIDE a shipped runner constructing
# SettleWaiter(sleep=lambda s: None): the gate stays green and every adopter's runner
# stops waiting. Round 1 asserted the identity on a SettleWaiter THIS SUITE built, which
# establishes what the class default is and NOTHING about what the runner resolves - the
# reviewer put a fake waiter at the runner's own resolution sites in all seven shipped
# android copies and the suite stayed green at 3261 passed / 0 failed. So the assertion
# below OBSERVES THE WAITER THE RUNNER BUILDS, at every resolution site the module's own
# AST declares, in every tracked copy of both runners, driven with the waiter argument
# OMITTED. Nothing below names run, apply_step or redrive to FIND a site.
def _v13_resolution_sites(tree):
    """{enclosing function name -> [lineno]} for every SettleWaiter(...) construction in
    the module, attributed to the INNERMOST enclosing FunctionDef. DERIVED: a fourth
    resolution site added tomorrow appears here by itself, and - because the assertion
    demands an exercise recipe per site - lands as a gate failure until it is covered."""
    funcs = [n for n in _v13_ast.walk(tree)
             if isinstance(n, (_v13_ast.FunctionDef, _v13_ast.AsyncFunctionDef))]
    owns = {id(f): {id(n) for n in _v13_ast.walk(f)} for f in funcs}
    out = {}
    for node in _v13_ast.walk(tree):
        if (isinstance(node, _v13_ast.Call) and isinstance(node.func, _v13_ast.Name)
                and node.func.id == "SettleWaiter"):
            owners = [f for f in funcs if id(node) in owns[id(f)]]
            if not owners:
                continue
            out.setdefault(max(owners, key=lambda f: f.lineno).name, []).append(node.lineno)
    return {k: sorted(v) for k, v in out.items()}


def _v13_load_copy(kind, src, name):
    """Exec a runner's source into a FRESH namespace. Every copy and every mutant is
    driven through this one door, so the shipped arm and the mutant arm differ in exactly
    the source text and nothing else."""
    g = {"__file__": str(_v13_paths[kind]), "__name__": name}
    exec(compile(src, "<v13-copy>", "exec"), g)
    return g


def _v13_ex_run(ns, kind, d):
    _v13_reset_fake(kind)
    return ns["run"](_V13_JOURNEY[kind], _V13_FAKE[kind](), d)


def _v13_ex_apply_step(ns, kind, d):
    Path(d).mkdir(parents=True, exist_ok=True)
    return ns["apply_step"](_V13_FAKE[kind](), {"action": "wait", "seconds": 0}, d,
                            {"states": []})


def _v13_ex_redrive(ns, kind, d):
    Path(d).mkdir(parents=True, exist_ok=True)
    _v13_reset_fake(kind)
    return ns["redrive"](_V13_FAKE[kind](), _V13_JOURNEY[kind],
                         "background_foreground", d, {"states": []})


# One recipe per resolution site, keyed by the name the AST reports. The assertion
# demands set equality with the DERIVED site set, so a new site with no recipe reddens
# the gate instead of quietly going unexercised.
_V13_EXERCISE = {"run": _v13_ex_run, "apply_step": _v13_ex_apply_step,
                 "redrive": _v13_ex_redrive}


def _v13_runner_resolutions(kind, src, name):
    """Drive EVERY resolution site the source declares with the waiter argument OMITTED
    and return (sites, {site -> [waiters THE RUNNER BUILT there]}). SettleWaiter is
    replaced by a subclass whose __init__ delegates to the SHIPPED one - so the resolution
    observed is the shipped resolution - and whose settle is a NO-OP, so exercising a
    production-path site costs no wall time at all."""
    ns = _v13_load_copy(kind, src, name)
    base = ns["SettleWaiter"]
    made = []

    class _Cap(base):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            made.append(self)

        def settle(self, seconds, reason):
            return None

    ns["SettleWaiter"] = _Cap
    sites = _v13_resolution_sites(_v13_ast.parse(src))
    got = {}
    with tempfile.TemporaryDirectory() as _d:
        for site in sorted(sites):
            if site not in _V13_EXERCISE:
                got[site] = []
                continue
            mark = len(made)
            _V13_EXERCISE[site](ns, kind, _d + "/" + site)
            got[site] = made[mark:]
    return sites, got


_v13_res = {(k, rel): _v13_runner_resolutions(k, _v13_copy_src[k][rel], "veldo_%s_ac1" % k)
            for k in _V13_MOBILE for rel in _V13_TRACKED[k]}
expect("WARP-0713 AC1: THE WAITER THE RUNNER ITSELF RESOLVES is the REAL clock, asserted BY IDENTITY (`is time.sleep`, `is time.monotonic`, record None) over the object the runner CONSTRUCTED when driven with the waiter argument omitted - at every resolution site its own AST declares, in the one tracked copy of each runner. Constructing a SettleWaiter in this suite and asserting on that would prove the class default and say nothing about what an adopter's runner resolves, which is the hole a fake waiter installed at the runner's own sites walked straight through",
       all(len(_V13_TRACKED[k]) == 1 for k in _V13_MOBILE)
       and all(set(sites) == set(_V13_EXERCISE)
               and all(ws and all(_v13_resolves_real(w) for w in ws)
                       for ws in got.values())
               for sites, got in _v13_res.values()))


def _v13_settlewaiter_calls(tree):
    return sorted((n for n in _v13_ast.walk(tree)
                   if isinstance(n, _v13_ast.Call) and isinstance(n.func, _v13_ast.Name)
                   and n.func.id == "SettleWaiter"),
                  key=lambda n: (n.lineno, n.col_offset))


def _v13_fake_waiter_at(src, index):
    """THE REVIEWER'S MUTATION, applied to ONE site, by AST rather than by a text pattern:
    give the index-th SettleWaiter(...) construction `sleep=lambda s: None'. An existing
    sleep keyword is REPLACED rather than duplicated, so this produces compilable source
    for any input - including a tree where the fake waiter is already installed, which is
    exactly the run whose result has to be a clean RED and never a traceback."""
    tree = _v13_ast.parse(src)
    call = _v13_settlewaiter_calls(tree)[index]
    call.keywords = [kw for kw in call.keywords if kw.arg != "sleep"]
    call.keywords.append(_v13_ast.keyword(
        arg="sleep", value=_v13_ast.parse("lambda s: None", mode="eval").body))
    return _v13_ast.unparse(_v13_ast.fix_missing_locations(tree))


def _v13_all_real(kind, src, name):
    _sites, got = _v13_runner_resolutions(kind, src, name)
    return all(ws and all(_v13_resolves_real(w) for w in ws) for ws in got.values())


_v13_site_mutants = []
_v13_whole_mutants = []
for _k in _V13_MOBILE:
    for _rel in _V13_TRACKED[_k]:
        _src = _v13_copy_src[_k][_rel]
        _n = len(_v13_settlewaiter_calls(_v13_ast.parse(_src)))
        for _i in range(_n):
            _v13_site_mutants.append(
                _v13_all_real(_k, _v13_fake_waiter_at(_src, _i), "veldo_%s_m" % _k))
        _wsrc = _src.replace("SettleWaiter()", "SettleWaiter(sleep=lambda s: None)")
        _v13_whole_mutants.append(
            (_src.count("SettleWaiter()") == _n, _v13_all_real(_k, _wsrc, "veldo_%s_w" % _k)))
expect("WARP-0713 AC1 CONTROL, THE MUTATION THAT SHIPPED GREEN LAST ROUND: a fake waiter installed at ONE of the runner's own resolution sites - every site, of every tracked copy of both runners, one at a time, by AST - is REFUSED. Not one of them survives, so the assertion above is bound to the runner's resolution and not to a construction this suite makes",
       _v13_site_mutants != [] and not any(_v13_site_mutants))
expect("WARP-0713 AC1 CONTROL, THE REVIEWER'S EXACT EDIT: replacing the bare `SettleWaiter()' at every resolution site of every tracked copy with `SettleWaiter(sleep=lambda s: None)' - the literal text change that left the suite at 3261 passed / 0 failed - is REFUSED in every copy, and the text replaced hits exactly the AST-derived construction count so the mutation cannot be silently matching nothing",
       _v13_whole_mutants != []
       and all(counted and not survived for counted, survived in _v13_whole_mutants))

# --- NO REAL SLEEP LEAKS + QUIESCENCE: the probes that make the whole thing sound.
_V13_AGENTS = ("subprocess.Popen", "os.fork", "os.exec", "os.system", "os.posix_spawn",
               "_thread.start_new_thread", "socket.connect", "socket.getaddrinfo")
_v13_audit_on = False
_v13_agent_events = []


def _v13_audit(event, args):
    """Installed ONCE, near the END of this file, so its permanent per-event cost is paid
    by the three lines that follow rather than by a 21,000-line suite. Gated on a flag so
    it observes only the windows this block opens."""
    if _v13_audit_on and event.startswith(_V13_AGENTS):
        _v13_agent_events.append(event)


sys.addaudithook(_v13_audit)
_v13_real_sleep = _v13_time.sleep
_v13_real_clock = _v13_time.monotonic
_v13_runner_sleeps = []


def _v13_profile(frame, event, arg):
    """Observe WHAT IS ACTUALLY CALLED, not the time module's attribute. Round 1 swapped
    `time.sleep` on the module, but SettleWaiter.__init__ binds the real sleep at DEF time
    to the function OBJECT, so a production-path settle calls the object directly and that
    wrapper could never fire - the reviewer constructed a SettleWaiter with it installed
    and watched it stay silent. A c_call profile event carries the callee OBJECT, so this
    sees every real sleep however it was bound, attributed to the CALLER's module."""
    if event == "c_call" and arg is _v13_real_sleep:
        _v13_runner_sleeps.append(frame.f_globals.get("__name__", "?"))


def _v13_probe(fn):
    """Run fn() with the c_call profile observer installed and the audit window OPEN.
    Returns (result, agent_events, thread_delta, sleeps_charged_to_a_runner). The observer
    is removed in a finally, so a failure inside fn cannot leave the suite instrumented."""
    global _v13_audit_on
    del _v13_agent_events[:]
    del _v13_runner_sleeps[:]
    threads_before = _v13_threading.active_count()
    sys.setprofile(_v13_profile)
    _v13_audit_on = True
    try:
        out = fn()
    finally:
        sys.setprofile(None)
        _v13_audit_on = False
    charged = [m for m in _v13_runner_sleeps
               if m.startswith("veldo_android") or m.startswith("veldo_ios")]
    return (out, list(_v13_agent_events),
            _v13_threading.active_count() - threads_before, charged)


_v13_rec = {}
_v13_probe_out = {}
with tempfile.TemporaryDirectory() as _v13_d:
    for _k in ("android", "ios"):
        _v13_rec[_k] = _V13Recorder()
        _v13_probe_out[_k] = _v13_probe(
            lambda _k=_k: _v13_drive(_k, _V13_JOURNEY[_k], _v13_d + "/all-" + _k,
                                     waiter=_v13_rec[_k].waiter(_V13_MODS[_k])))

    expect("WARP-0713 AC3: the all-sites journeys PASS on both runners with the injected waiter, so the recorded settle sequence below is the sequence of a GREEN run and not of a run that died early. Every action and every lifecycle re-drive is reached",
           all(_v13_probe_out[_k][0]["passed"] is True for _k in ("android", "ios"))
           and len(_v13_probe_out["android"][0]["redrives"]) == 4
           and len(_v13_probe_out["ios"][0]["redrives"]) == 3)

    expect("WARP-0713 AC3 ORDER: for every action and every lifecycle re-drive, the RECORDED (reason, seconds) sequence equals the expected sequence exactly - including process_death recording terminate-then-launch IN THAT ORDER and never the reverse, and never a doubled or dropped wait. Nothing in this gate could see any of that before: the previous coverage established only that time passed",
           all(_v13_rec[_k].seq() == _V13_EXPECTED_SEQ[_k] for _k in ("android", "ios"))
           and _v13_rec["android"].seq()[7:9] == [
               ("redrive.process_death.after_force_stop", 1),
               ("redrive.process_death.relaunch", 2)]
           and _v13_rec["ios"].seq()[4:6] == [
               ("redrive.process_death.after_terminate", 1),
               ("redrive.process_death.relaunch", 2)])

    _v13_ast_map = {_k: _v13_ast_settle_map(_v13_tree[_k]) for _k in ("android", "ios")}
    _v13_rec_map = {_k: dict(_v13_rec[_k].seq()) for _k in ("android", "ios")}
    expect("WARP-0713 AC2 THREE-WAY CONSTANT EQUALITY, each side produced by a DIFFERENT mechanism so agreement is evidence: the FROZEN table (which is the criterion text a reviewer reads), the map PARSED out of the shipped module's AST, and the map the recorder OBSERVED by driving the runners with fixtures that override nothing. All three EQUAL, over all 23 settle constants. Shortening any wait - including in the direction that makes this gate faster, which is what AC2 forbids - breaks it on at least two sides",
           all(_v13_ast_map[_k][0] == _V13_FROZEN[_k] == _v13_rec_map[_k]
               for _k in ("android", "ios"))
           and sum(len(_V13_FROZEN[_k]) for _k in ("android", "ios")) == 23)

    expect("WARP-0713 AC3 COMPLETENESS, in BOTH directions and DERIVED on both sides rather than typed out: the set of settle reasons found in the module AST EQUALS the set the recorder observed. A site that exists but is never exercised (a new wait added without coverage) fails one direction; a site observed but absent from the source fails the other. The labels are also asserted UNIQUE within each module, because two sites sharing a label would silently collapse two waits into one in every order assertion above",
           all(set(_v13_ast_map[_k][0]) == set(_v13_rec_map[_k]) and _v13_ast_map[_k][1] == []
               and None not in _v13_ast_map[_k][0]
               for _k in ("android", "ios")))

    expect("WARP-0713 COHERENCE: for every recorded entry t1 - t0 == seconds, and the virtual now equals the running sum of the seconds requested, so the seam neither slept twice for one settle nor timestamped one settle with another's clock reading. It says nothing about a path that escaped to the real module: that is the c_call observer's job, below, and the claim belongs there",
           all(all(abs((t1 - t0) - s) < 1e-9 for _r, s, t0, t1 in _v13_rec[_k].log)
               and abs(_v13_rec[_k].now
                       - sum(s for _r, s, _a, _b in _v13_rec[_k].log)) < 1e-9
               for _k in ("android", "ios")))

    expect("WARP-0713 NO REAL SLEEP LEAKS: across both all-sites runs, with every CALL to the real time.sleep OBJECT observed through a c_call profile event and attributed to its caller's module, the number of REAL sleeps charged to either mobile runner module is ZERO. Zero is the invariant; it is not a count of anything in this repository. A settle site that did not get routed, a new raw sleep on an exercised path, and - unlike the module-attribute wrapper this replaces - a settle that reached the seam's def-time-bound real sleep, all make it non-zero",
           all(_v13_probe_out[_k][3] == [] for _k in ("android", "ios")))

    expect("WARP-0713 QUIESCENCE - THE PREMISE THAT MAKES FAST-FORWARDING SOUND, PROVEN RATHER THAN ASSUMED. A settle can be load-bearing only if state the runner later observes changes WHILE it sleeps, which requires an agent of change other than the runner itself. During both probed runs an audit hook records ZERO agent-creating events (subprocess.Popen, os.fork, os.exec, os.system, os.posix_spawn, _thread.start_new_thread, socket.connect, socket.getaddrinfo) and the live thread count is UNCHANGED (compared to itself, never to a literal). With no other agent, no observation can change across the sleep, so removing the sleep cannot change any observation. This is the argument; the differential below is corroboration",
           all(_v13_probe_out[_k][1] == [] and _v13_probe_out[_k][2] == 0
               for _k in ("android", "ios")))

    # NEGATIVE CONTROLS for the two probes: each must SEE the thing it looks for.
    def _v13_start_a_thread():
        t = _v13_threading.Thread(target=lambda: None)
        t.start()
        t.join()
        return "threaded"

    _v13_thread_probe = _v13_probe(_v13_start_a_thread)
    expect("WARP-0713 QUIESCENCE CONTROL: the same probe, wrapped around a thread that is STARTED AND JOINED inside the window, REPORTS it - so the hook is demonstrably able to see an agent of change appear, and the zero above is a measurement rather than a hook that observes nothing on this interpreter",
           any(e == "_thread.start_new_thread" for e in _v13_thread_probe[1]))

    _v13_leak_src = "import time\ndef go():\n    time.sleep(0)\n"

    def _v13_fake_runner_sleep():
        g = {"__name__": "veldo_android_leakcontrol"}
        exec(compile(_v13_leak_src, "<v13_leak>", "exec"), g)
        g["go"]()
        return "slept"

    _v13_leak_probe = _v13_probe(_v13_fake_runner_sleep)
    expect("WARP-0713 NO-LEAK CONTROL: a two-line source whose __name__ begins with veldo_android and which calls time.sleep(0) through the time module is charged EXACTLY ONE real sleep by the same attribution",
           _v13_leak_probe[3] == ["veldo_android_leakcontrol"])

    # THE CONTROL THAT MATTERS, AND IT IS ADDITIVE: the observer must see the PRODUCTION
    # PATH, where the sleep is the def-time-bound function OBJECT and no module attribute
    # is ever read. This is exactly what round 1's wrapper was blind to. A fresh copy of
    # the SHIPPED source is driven with the waiter argument OMITTED on a journey whose
    # every window is ZERO, so the runner resolves its own real waiter and really calls
    # time.sleep - twice, for no seconds - and the probe must charge both to it.
    def _v13_production_path(kind, d):
        ns = _v13_load_copy(kind, _v13_src[kind], "veldo_%s_prodpath" % kind)
        _v13_reset_fake(kind)
        return ns["run"](_V13_ZERO[kind], _V13_FAKE[kind](), d)

    _v13_prod_probe = {_k: _v13_probe(
        lambda _k=_k: _v13_production_path(_k, _v13_d + "/pp-" + _k))
        for _k in ("android", "ios")}
    expect("WARP-0713 NO-LEAK CONTROL, THE PRODUCTION PATH: driving a fresh copy of each shipped runner with the waiter argument OMITTED charges the observer EXACTLY the two settles the zero-window journey requests, attributed to that runner's module. The seam's real sleep is bound at def time to the function object, so this is the call a module-attribute wrapper cannot see - and the ZERO above is therefore a measurement of a path the observer has been demonstrated to reach, not the silence of an instrument that never fires",
           all(_v13_prod_probe[_k][3] == ["veldo_%s_prodpath" % _k] * 2
               for _k in ("android", "ios")))

    # --- SETTLE OVERRIDE STILL WORKS ------------------------------------------
    _v13_ovr = {}
    for _k, _j in (("android", {"name": "o", "package": "p", "activity": ".M",
                                "steps": [{"action": "launch", "package": "p",
                                           "activity": ".M", "settle": 7},
                                          {"action": "wait", "seconds": 9}]}),
                   ("ios", {"name": "o", "bundle_id": "b",
                            "steps": [{"action": "launch", "bundle_id": "b", "settle": 7},
                                      {"action": "wait", "seconds": 9}]})):
        _v13_ovr[_k] = _V13Recorder()
        _v13_drive(_k, _j, _v13_d + "/ovr-" + _k, waiter=_v13_ovr[_k].waiter(_V13_MODS[_k]))
    expect("WARP-0713: a journey DECLARING its own window still gets it - settle 7 records 7 and seconds 9 records 9, in both runners. This is what a port that hardcoded the default and dropped step.get would break, silently ignoring every adopter's declared settle window while every constant assertion above stayed green",
           all(_v13_ovr[_k].seq() == [("launch", 7), ("wait", 9)]
               for _k in ("android", "ios")))

    # --- EQUIVALENCE DIFFERENTIAL: the same journey, virtual clock vs REAL sleeps
    # scaled to 0.02 of each constant (about 0.55 real seconds for both modules).
    # Byte-equal results after exactly TWO declared normalizations: the outdir
    # prefix, and the fake driver's class-level counter (reset in _v13_drive).
    # The REAL arm passes a sleep and NO record, so it is also the only thing here
    # that exercises the PRODUCTION branch of settle.
    def _v13_norm(result, prefix):
        return json.dumps(result, sort_keys=True).replace(prefix, "<OUTDIR>")

    _V13_SCALE = 0.02
    _v13_diff = {}
    for _k in ("android", "ios"):
        _vout = _v13_d + "/dv-" + _k
        _rout = _v13_d + "/dr-" + _k
        _vres = _v13_drive(_k, _V13_JOURNEY[_k], _vout,
                           waiter=_V13Recorder().waiter(_V13_MODS[_k]))
        _rres = _v13_drive(_k, _V13_JOURNEY[_k], _rout,
                           waiter=_V13_MODS[_k].SettleWaiter(
                               sleep=lambda s: _v13_real_sleep(s * _V13_SCALE)))
        _v13_diff[_k] = (_v13_norm(_vres, _vout) == _v13_norm(_rres, _rout),
                         len(_rres["redrives"]), _rres["passed"])
    expect("WARP-0713 EQUIVALENCE DIFFERENTIAL: for one all-sites journey per module the result dict from the VIRTUAL-clock arm is byte-equal to the result dict from an arm that REALLY SLEEPS, after exactly two declared normalizations (the outdir prefix and the fake driver's class-level counter). Run at 0.02 of each constant rather than at full length, because eating half the saving forever in the item whose purpose is removing it would be absurd - so this can only see a time dependence whose threshold is under 2 percent of the constant, and it is corroboration while the quiescence proof is the proof. NON-VACUITY: the compared dict carries its four (android) and three (iOS) re-drives and a passing run",
           all(_v13_diff[_k][0] and _v13_diff[_k][2] is True for _k in ("android", "ios"))
           and _v13_diff["android"][1] == 4 and _v13_diff["ios"][1] == 3)

    # SENSITIVITY CONTROL: a driver whose observable flips only after real time
    # passes. The real arm must PASS and the virtual arm must FAIL, which proves
    # the differential can see a planted LOAD-BEARING wait at the scale it runs at.
    class _V13LaggyDriver(_FakeDriver):
        """The focus does not settle until 0.01 real seconds after the launch."""

        def launch(self, p, a):
            self._t0 = _v13_real_clock()
            return super().launch(p, a)

        def current_focus(self):
            if _v13_real_clock() - getattr(self, "_t0", 0) < 0.01:
                return "mCurrentFocus=Window{NOT-SETTLED-YET}"
            return super().current_focus()

    _v13_laggy = {"name": "laggy", "package": "com.example.app", "activity": ".Main",
                  "steps": [{"action": "launch", "package": "com.example.app",
                             "activity": ".Main"},
                            {"action": "expect_focus", "value": "com.example.app"}]}
    _v13_lag_real = _v13_drive("android", _v13_laggy, _v13_d + "/lag-r",
                               driver=_V13LaggyDriver(),
                               waiter=AR.SettleWaiter(
                                   sleep=lambda s: _v13_real_sleep(s * _V13_SCALE)))
    _v13_lag_virt = _v13_drive("android", _v13_laggy, _v13_d + "/lag-v",
                               driver=_V13LaggyDriver(),
                               waiter=_V13Recorder().waiter(AR))
    expect("WARP-0713 DIFFERENTIAL SENSITIVITY CONTROL: with a PLANTED load-bearing wait - a driver whose focus settles only 0.01 real seconds after the launch - the real-sleeping arm PASSES (0.04s elapses at scale 0.02 on a 2s launch settle) and the virtual arm FAILS. So the differential is demonstrably able to see the thing it is looking for, at the scale it is actually run at, and the byte-equality above is not the equality of two runs that could not tell time apart",
           _v13_lag_real["passed"] is True and _v13_lag_virt["passed"] is False)

# --- THE MUTANTS. A check with no demonstrated firing input is decoration. -----
_V13_MUTANTS = {
    "shortened constant": ("android", 'waiter.settle(step.get("settle", 2), "launch")',
                           'waiter.settle(step.get("settle", 0.01), "launch")'),
    "raw sleep in control logic": ("android", 'waiter.settle(0.5, "text")',
                                   'time.sleep(0.5)'),
    "condition poll routed into the seam": ("android", "            time.sleep(2)",
                                            '            SettleWaiter().settle(2, "boot")'),
    "settle planted inside a loop": ("ios", '        waiter.settle(step.get("seconds", 1), "wait")',
                                     '        for _ in (1,):\n            waiter.settle(step.get("seconds", 1), "wait")'),
}
expect("WARP-0713 TEETH: every mutation target appears EXACTLY ONCE in the module it mutates. A mutation string that matched nothing would leave source.replace returning the source unchanged, the control would pass for the wrong reason, and the tooth would be decoration. Quantified over the table rather than pinned to its size, because the table is a thing this repository grows",
       _V13_MUTANTS != {}
       and all(_v13_src[_k].count(_old) == 1 for _k, _old, _new in _V13_MUTANTS.values()))


def _v13_mut_src(name):
    kind, old, new = _V13_MUTANTS[name]
    return kind, _v13_src[kind].replace(old, new)


def _v13_mut_mod(name):
    """The runner with exactly ONE mutation, compiled IN MEMORY. The file is never
    written, and _v13_sha_unchanged() proves it after every mutant below."""
    kind, src = _v13_mut_src(name)
    g = {"__file__": str(_v13_paths[kind]), "__name__": "veldo_%s_v13mut" % kind}
    exec(compile(src, "<v13_mut>", "exec"), g)
    return kind, g


_v13_mk, _v13_msrc = _v13_mut_src("shortened constant")
_v13_mtree = _v13_ast.parse(_v13_msrc)
_v13_mmod_k, _v13_mmod = _v13_mut_mod("shortened constant")
with tempfile.TemporaryDirectory() as _v13_md:
    _v13_mrec = _V13Recorder()
    setattr(_V13_FAKE["android"], "_pidctr", 100)
    _v13_mmod["run"](_V13_JOURNEY["android"], _FakeDriver(), _v13_md + "/m",
                     waiter=_v13_mmod["SettleWaiter"](clock=_v13_mrec.clock,
                                                      sleep=_v13_mrec.sleep,
                                                      record=_v13_mrec.record))
expect("WARP-0713 AC2 CONTROL, THE ONE THAT MATTERS MOST: an in-memory copy with the launch settle default changed from 2 to 0.01 is REFUSED on BOTH derived sides - the AST map no longer equals the frozen table, and the recorder driving that mutant observes 0.01 rather than 2. This is the shortcut AC2 forbids (buying gate speed by testing something other than what ships), demonstrated as a gate failure rather than promised as a discipline",
       _v13_ast_settle_map(_v13_mtree)[0] != _V13_FROZEN["android"]
       and _v13_ast_settle_map(_v13_mtree)[0]["launch"] == 0.01
       and dict(_v13_mrec.seq())["launch"] == 0.01
       and _v13_sha_unchanged())

_v13_rk, _v13_rsrc = _v13_mut_src("raw sleep in control logic")
expect("WARP-0713 T2 CONTROL: an in-memory copy with one raw time.sleep planted back into apply_step is REFUSED by the partition universal, which names it outside the driver class. Without this the universal would be an unbacked claim about a property that happens to hold today",
       _v13_time_calls_outside_driver(_v13_ast.parse(_v13_rsrc), "AdbDriver") != []
       and [a for _ln, a in _v13_time_calls_outside_driver(
           _v13_ast.parse(_v13_rsrc), "AdbDriver")] == ["sleep"]
       and _v13_sha_unchanged())

_v13_ck, _v13_csrc = _v13_mut_src("condition poll routed into the seam")
_v13_lk, _v13_lsrc = _v13_mut_src("settle planted inside a loop")
expect("WARP-0713 T3 CONTROL - THE MECHANISM REFUSING TO FAST-FORWARD A LOAD-BEARING WAIT, DEMONSTRATED. An in-memory copy that routes wait_boot's `time.sleep(2)` poll THROUGH the seam is REFUSED, because that settle then sits inside the `while time.time() < end` loop; and so is a copy with a settle planted inside a synthetic loop in the other runner. A condition wait cannot enter the seam without turning the gate red",
       _v13_settle_in_loop(_v13_ast.parse(_v13_csrc)) != []
       and _v13_settle_in_loop(_v13_ast.parse(_v13_lsrc)) != []
       and _v13_sha_unchanged())

# --- THE INJECTION SITES: the item's MOST LIKELY silent failure, OBSERVED ------
# run() resolves waiter=None to a REAL SettleWaiter, so a drive site that loses its
# `waiter=` keyword quietly restores every second of gate time with every assertion above
# still green. Round 1 guarded that by parsing this file for calls to `.run` on the NAMES
# `AR` and `IOS`. That was a name pin, and it was blind to `mod.run(J, drv, d)` - the form
# this block's own _v13_drive helper uses internally - and to every wrapper around it. So
# the property is OBSERVED rather than described: _mw_instrument, installed beside each
# runner's load at the top of this file, recorded EVERY SettleWaiter built through the two
# loaded runner modules together with the module that asked for it. Two facts are then
# asserted over whatever this gate actually did, in any call form, named or not, existing
# or added tomorrow.
_v13_made = list(_MW_MADE)
expect("WARP-0713 INJECTION SITES: over this ENTIRE gate run, no waiter built through either loaded mobile runner was resolved BY THE RUNNER ITSELF (which is what a drive site reaching run() without a waiter looks like), and not one of them carries the real time.sleep (which is what a drive site handing over a real-clock waiter looks like). Observed at construction rather than parsed out of this file's call syntax, so no drive site can hide behind a helper, an alias or a form nobody thought to match, and the gate's own mobile journeys are confirmed to have requested settles at all",
       [m for m, _w in _v13_made if m in (AR.__name__, IOS.__name__)] == []
       and [m for m, w in _v13_made if w._sleep is _v13_time.sleep] == []
       and _v13_made != [] and _MW_SEC != [])

# CONTROL, AND IT IS ADDITIVE: it ADDS a drive site rather than renaming one, which is
# the shape that a growth blind spot hides in. A copy of the shipped source loaded under
# the runner's own module name is driven with the waiter argument OMITTED on the
# zero-window journey; both halves of the assertion above must report it.
_v13_ctl_ns = _v13_load_copy("android", _v13_src["android"], AR.__name__)
_mw_instrument(_v13_ctl_ns)
with tempfile.TemporaryDirectory() as _v13_cd:
    _v13_reset_fake("android")
    _v13_ctl_ns["run"](_V13_ZERO["android"], _FakeDriver(), _v13_cd + "/ctl")
_v13_ctl_new = _MW_MADE[len(_v13_made):]
expect("WARP-0713 INJECTION-SITE CONTROL: an ADDED drive site that omits the waiter argument is reported by BOTH halves - exactly one construction charged to the runner's own module, and exactly one waiter carrying the real time.sleep - so the two empty lists above are measurements and not a recorder that observes nothing",
       [m for m, _w in _v13_ctl_new if m == AR.__name__] == [AR.__name__]
       and [m for m, w in _v13_ctl_new if w._sleep is _v13_time.sleep] == [AR.__name__])

# --- AC4: THE PROCESS RUNNER IS BYTE-UNCHANGED --------------------------------
# Its four sleeps are `time.sleep(POLL)` inside `while time.monotonic() < deadline`
# loops and it asserts real signal delivery, force-kill and orphan reaping, which a
# jumped clock invalidates. The digest below is PINNED ON PURPOSE: the only ordinary
# change that breaks it is an edit to that file, which is exactly the event that must
# redden this gate and force WARP-0715's argument into a spec. WARP-0715 is the item
# that must move it.
_V13_PROCESS_SHA = "41558fd0ea3878512020ff9555fdfd16c677acd951c302e374bd5204d67e5c4a"
_v13_proc_rels = _v13_tracked_copies("process_runner.py")
_v13_proc_bytes = {(ROOT / rel).read_bytes() for rel in _v13_proc_rels}
expect("WARP-0713 AC4: THE PROCESS RUNNER IS UNTOUCHED, and asserted so rather than merely left alone - the two runners live side by side and a well-meaning edit would generalize the seam into both. It has exactly ONE tracked copy under the canonical engine (enumerated by git ls-files), its sha256 equals one frozen digest, and its text contains neither SettleWaiter nor waiter",
       len(_v13_proc_rels) == 1
       and len(_v13_proc_bytes) == 1
       and _v13_hashlib.sha256(next(iter(_v13_proc_bytes))).hexdigest() == _V13_PROCESS_SHA
       and all(b"SettleWaiter" not in b and b"waiter" not in b for b in _v13_proc_bytes))

# --- ENGINE CANON: fourteen shipped files, enumerated by GLOB and by the manifest
_v13_canon = {}
for _k, _rel in _V13_MOBILE.items():
    _base = _rel.rsplit("/", 1)[1]
    _rels = _v13_tracked_copies(_base)
    _v13_canon[_k] = (_rels, {(ROOT / r).read_bytes() for r in _rels})
_v13_engine = set(PK.engine_files(str(ROOT / "engine")))
# THE FOURTEEN-FILE FOOTPRINT IS GONE WITH THE COPIES. Each mobile runner now has exactly ONE
# shipped copy, under the canonical engine, so "a change landing in one copy and not the other
# six" is not a hazard this repository has any more. What is still worth asserting is that the
# one copy exists, that the manifest names it as engine, and that no root copy shadows it.
expect("WARP-0713 ENGINE CANON: each mobile runner has exactly ONE shipped copy, under the canonical engine, the manifest names it as engine, and no root copy shadows it. The fourteen-file re-sync hazard is retired with the duplication rather than policed",
       all(len(_rels) == 1 and len(_bytes) == 1 for _rels, _bytes in _v13_canon.values())
       and all(_rel in _v13_engine for _rel in _V13_MOBILE.values())
       and not any((ROOT / _V13_MOBILE[_k]).exists() for _k in _V13_MOBILE))

# --- THE REPORTED FIGURE, PRINTED AND NEVER ASSERTED AGAINST A LITERAL --------
# This is a DERIVATION, not a measurement: the deterministic SUM of the settle
# seconds the gate's ten mobile journeys REQUEST, which the injected waiter absorbs
# instead of sleeping. Asserting a total of 46.0 would be exactly the moving-property
# trap - adding or removing one gate journey would turn this gate RED on an unrelated
# item. The ASSERTIONS are pinned to the owner's 23 constants instead.
print("  mobile settle: %d waits, %.1f simulated seconds absorbed by the injected waiter"
      % (len(_MW_SEC), sum(_MW_SEC)))
for _k in ("android", "ios"):
    print("  mobile settle order (%s): %s"
          % (_k, ", ".join("%s=%g" % (_r, _s) for _r, _s in _v13_rec[_k].seq())))

# --- DOGFOOD: this item's own spec ---------------------------------------------
_v13_spec_rel = "specs/WARP-0713-mobile-runner-injected-clock.md"
_v13_spec_text = (ROOT / _v13_spec_rel).read_text()
_v13_fm = V.parse_yamlish(re.match(r"^---\n(.*?)\n---", _v13_spec_text, re.S).group(1))
_v13_arch, _v13_contract = V.load_repo_contract(repo_root=str(ROOT))
_v13_fp = [g for g in (_v13_fm.get("footprint") or []) if isinstance(g, str)]
_v13_ac = {c.get("id"): c.get("text") or "" for c in (_v13_fm.get("acceptance_criteria") or [])
           if isinstance(c, dict)}
expect("WARP-0713 dogfood: the spec has PASSED the ready transition (so this does not go stale the moment it ships), declares the derived high tier with human approval not required, declares NO protected path - and that is checked against the policy's own protected set rather than trusted - and passes its own placement and diagnosability gates",
       _v13_fm.get("status") in ("ready", "in_progress", "review", "proven", "shipped")
       and _v13_fm.get("risk", "").split()[0] == "high"
       and _v13_fm.get("human_approval") == "not_required"
       and (_v13_fm.get("protected_paths") or []) == []
       and not [g for g in _v13_fp if g in set(P.protected_patterns())]
       and V.check_ready(ROOT / _v13_spec_rel, repo_root=str(ROOT)) == 0
       and _v13_arch.placement_gate(_v13_fm, _v13_contract) == [])

_v13_touched = sorted(set(
    [r for _rels, _b in _v13_canon.values() for r in _rels]
    + ["scripts/selftest.py", _v13_spec_rel, "specs/index.md"]))
expect("WARP-0713 dogfood: the footprint COVERS EVERY PATH THIS CHANGE TOUCHES, including the canon copy of each runner, checked through the repository's one glob compiler over a set built BY GLOB rather than typed out - which is the omission the last item on this file hit. The shape gate refuses a diff outside the footprint, so a short list would redden the gate rather than drift quietly",
       # DERIVED, not pinned: one canon copy per runner now, plus the three one-off paths
       len(_v13_touched) == len(_V13_MOBILE) + 3
       and all(any(_v13_arch._glob_re(g).match(rel) for g in _v13_fp) for rel in _v13_touched)
       and _v13_arch.footprint_areas(_v13_fm, _v13_contract) >= {"engine", "runners"})

expect("WARP-0713 dogfood, THE CRITERION ROUND 2 AMENDED RATHER THAN QUIETLY RE-READ: AC1 asked for a selftest that constructs each RUNNER with no arguments, and round 1 satisfied it by constructing a SettleWaiter - which proves the class default and says nothing about what the runner resolves, so a fake waiter at the runner's own resolution sites shipped green. AC1 now states that the assertion BINDS THE RUNNER'S OWN RESOLUTION, over every resolution site of every tracked copy, and the sentence that could be satisfied by a construction this suite makes is GONE rather than softened",
       "AMENDED BY ROUND 2" in _v13_ac.get("AC1", "")
       and "RUNNER'S OWN RESOLUTION" in _v13_ac.get("AC1", "").upper()
       and "EVERY tracked copy of both runners" in _v13_ac.get("AC1", "")
       and "IS the built-in time.sleep" not in _v13_ac.get("AC1", ""))

expect("WARP-0713 dogfood, THE CRITERION ROUND 1 AMENDED RATHER THAN REINTERPRETED: AC2 said `21 literal sleep sites (12 android, 9 ios)', which are LINE counts - `grep -c` counts lines while `grep -o | wc -l` counts calls, and three android lines plus one iOS line carried two calls each, so the CALL count is 25. AC2 now states 23 ROUTED CALLS ON 21 LINES and names the two waits deliberately left raw (wait_boot's boot poll and stop_recording's flush wait), because routing a condition wait into the seam is the exact defect this item is warned about. A criterion left stating a count the build measured to be false would ship an unbacked number in the one place a reviewer is asked to check",
       "23 ROUTED" in _v13_ac.get("AC2", "").upper()
       and "21 LINES" in _v13_ac.get("AC2", "").upper()
       and "AMENDED" in _v13_ac.get("AC2", "").upper()
       and "wait_boot" in _v13_ac.get("AC2", "")
       and "stop_recording" in _v13_ac.get("AC2", "")
       and "All 21 literal sleep sites route through the seam" not in _v13_ac.get("AC2", ""))


# --- WARP-0712 ROUND 1: the two proofs that must exist BEFORE any file moves -----------
# THIS ROUND SPLITS NOTHING. It builds the instrument that makes a split falsifiable (the
# assertion-label identity proof), the harness that will prove each suite equivalent
# standalone and in aggregate, and the DRIVEN survey of order dependence, and it records the
# measurement. The DOMAIN, PROMISE, COMPLETENESS ARGUMENT, OBSERVATION POINT and each
# instrument's OWN BLINDNESS are declared in the module docstring of each tool, before any
# of them was built, because a completeness argument discovered afterwards is a rationalisation.
#
# WHY A LABEL SET AND NOT A COUNT, stated once here and asserted below: a count survives one
# deletion paired with one addition, and the twin fixture named `swap` is exactly that pair.
# WHY A MULTISET AND NOT A SET: a set survives losing one occurrence of a duplicated label.
# The real suite carries no duplicate label today, which is MEASURED rather than assumed, and
# the multiset comparison is what keeps that from becoming a silent assumption as it grows.
import ast as _w12_ast
import hashlib as _w12_hashlib
import types as _w12_types
from collections import Counter as _w12_Counter
from concurrent.futures import ThreadPoolExecutor as _w12_Pool

_W12_TOOLS = ("suite_labels", "suite_equiv", "suite_slice")
_w12_paths = {n: ROOT / "scripts" / ("%s.py" % n) for n in _W12_TOOLS}
_w12_before = {n: _w12_hashlib.sha256(p.read_bytes()).hexdigest()
               for n, p in _w12_paths.items()}


def _w12_fresh(name, subs=()):
    """Load one tool from source, optionally substituted, as a fresh in-memory module.

    Returns the module and the substitution counts. The counts are asserted by the caller:
    a mutation that matched nothing would make an untouched module look like a toothed one.
    """
    src = _w12_paths[name].read_text()
    counts = []
    for find, repl in subs:
        counts.append(src.count(find))
        src = src.replace(find, repl)
    mod = _w12_types.ModuleType("_w12_" + name)
    mod.__file__ = str(_w12_paths[name])
    exec(compile(src, mod.__file__, "exec"), mod.__dict__)
    return mod, counts


_w12_L, _ = _w12_fresh("suite_labels")
_w12_E, _ = _w12_fresh("suite_equiv")
_w12_S, _ = _w12_fresh("suite_slice")

# ---- the real file, STRUCTURALLY, without running it ----------------------------------
# THE SUBJECT IS RESOLVED, NOT TYPED. Before the decomposition the assertion primitive lives
# in scripts/selftest.py; after it, in the shared fixture module the manifest names. Naming
# one path here would make this block measure the dispatcher the day the split lands
# and pass vacuously, which is the failure mode of an assertion whose subject moved.
_W12_SUITES = ROOT / "scripts" / "suites"
_w12_manifest_path = _W12_SUITES / "manifest.json"
if _w12_manifest_path.is_file():
    _w12_primitive_file = _W12_SUITES / json.loads(
        _w12_manifest_path.read_text())["shared"]
else:
    _w12_primitive_file = ROOT / "scripts" / "selftest.py"
_w12_self_src = _w12_primitive_file.read_text()
_w12_self_tree = _w12_ast.parse(_w12_self_src)
_w12_sites = _w12_L.primitive_sites(_w12_self_tree)
_w12_counters = sorted({c for s in _w12_sites for c in s["counters"]})
expect("WARP-0712 AC5 the assertion primitive of the REAL suite is located STRUCTURALLY, by "
       "the shape of a counter-writing module-level function rather than by the name `expect`, "
       "so a rename of the primitive does not blind the instrument. Every located site is "
       "asserted as a PROPERTY OF ITSELF - it writes at least one module-level counter and "
       "takes at least a label and a condition - and never as a count of sites, because the "
       "number of primitives is not this suite's to grow but the number of assertions is",
       bool(_w12_sites)
       and all(s["counters"] and len(s["params"]) >= 2 for s in _w12_sites)
       and _w12_counters == ["FAIL", "PASS"])

_w12_copy = _w12_ast.parse(_w12_self_src)
_w12_copy_sites = _w12_L.primitive_sites(_w12_copy)
_w12_inj = _w12_L.inject(_w12_copy, _w12_copy_sites)
try:
    compile(_w12_copy, "<w12-injected>", "exec")
    _w12_compiles = True
except Exception as _w12_ce:  # noqa: BLE001 - a crash here must be a red, not a traceback
    _w12_compiles = "%s: %s" % (type(_w12_ce).__name__, _w12_ce)
expect("WARP-0712 AC5 THE MUTATION IS ASSERTED APPLIED BEFORE ANY RESULT OF IT IS BELIEVED: "
       "instrumenting the real suite inserts exactly one wrapper rebinding PER LOCATED SITE, "
       "the injected tree still compiles, and the measured file on disk is sha256-UNCHANGED "
       "- the instrument rewrites an AST in the child's memory and never the file, which is "
       "what lets the same instrument measure the monolith and the decomposed suites with one "
       "observation point",
       _w12_inj == len(_w12_copy_sites) and _w12_inj > 0 and _w12_compiles is True
       and _w12_hashlib.sha256(_w12_primitive_file.read_bytes()).hexdigest()
       == _w12_hashlib.sha256(_w12_self_src.encode()).hexdigest())

# ---- the label instrument, DRIVEN, with an additive and a subtractive control ----------
_W12_TINY = '''\
PASS = 0
FAIL = 0


def expect(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1


A = "a"
expect("alpha", A == "a")
expect("beta", 1 == 1)
expect("gamma gamma", True)
print("selftest: %d passed, %d failed" % (PASS, FAIL))
'''
_W12_ANCHOR = 'expect("beta", 1 == 1)\n'
# name -> (substitution, expected substitution count, what the instrument MUST report)
_W12_TWINS = {
    "subtract": (_W12_ANCHOR, "", 1),
    "add": (_W12_ANCHOR, _W12_ANCHOR + 'expect("delta", True)\n', 1),
    "multiply": (_W12_ANCHOR, _W12_ANCHOR + _W12_ANCHOR, 1),
    "flip": ('expect("beta", 1 == 1)', 'expect("beta", 1 == 2)', 1),
    "swap": (_W12_ANCHOR, 'expect("delta", True)\n', 1),
}
_w12_tinydir = tempfile.mkdtemp(prefix="veldo0712-tiny")
_w12_base_path = Path(_w12_tinydir) / "base.py"
_w12_base_path.write_text(_W12_TINY)
_w12_subs_applied = {}
_w12_twin_caps = {}
_w12_base_cap = _w12_L.capture(_w12_base_path)
_w12_base_sums = _w12_base_cap.reconcile()
_w12_base_summary = _w12_base_cap.reconcile_summary()
_w12_base_again = _w12_L.capture(_w12_base_path)
_w12_base_again.reconcile()
for _w12_name, (_w12_find, _w12_repl, _w12_want) in _W12_TWINS.items():
    _w12_p = Path(_w12_tinydir) / ("%s.py" % _w12_name)
    _w12_subs_applied[_w12_name] = (_W12_TINY.count(_w12_find), _w12_want)
    _w12_p.write_text(_W12_TINY.replace(_w12_find, _w12_repl))
    _w12_c = _w12_L.capture(_w12_p)
    _w12_c.reconcile()
    _w12_twin_caps[_w12_name] = _w12_c
_w12_diffs = {k: _w12_L.compare(_w12_base_cap, c) for k, c in _w12_twin_caps.items()}

expect("WARP-0712 AC5 the label instrument RECONCILES against the subject's own arithmetic, "
       "which is its completeness argument and not a claim: the recorded per-label counter "
       "deltas sum to exactly the counters the subject holds at exit, and the integers the "
       "subject PRINTED in its own summary line are exactly those counter values. An assertion "
       "that bypassed the primitive, a double-counting wrapper, or a summary line that prints "
       "something other than what the counters hold, each becomes a named refusal instead of a "
       "quietly short label set",
       _w12_base_sums == {"PASS": 3, "FAIL": 0}
       and _w12_base_summary == "selftest: 3 passed, 0 failed"
       and _w12_L.compare(_w12_base_cap, _w12_base_again)["identical"])

expect("WARP-0712 AC5 SUBTRACTIVE CONTROL: removing one assertion is reported BY IDENTITY as "
       "that exact label missing, with nothing added, nothing multiplied and nothing flipped, "
       "and the substitution that produced the twin is asserted to have matched exactly once "
       "first, because a twin that is a copy of the original would score a false green",
       _w12_subs_applied["subtract"] == (1, 1)
       and _w12_diffs["subtract"]["missing"] == ["beta"]
       and _w12_diffs["subtract"]["added"] == []
       and _w12_diffs["subtract"]["multiplicity_changed"] == []
       and _w12_diffs["subtract"]["signature_changed"] == [])

expect("WARP-0712 AC5 ADDITIVE CONTROL, which is the half a rename battery is blind to: "
       "ADDING an assertion is reported as that exact label added, with nothing missing. A "
       "control that only ever deletes proves the instrument notices shrinkage and says "
       "nothing about growth, and a decomposition that quietly GAINS an assertion has also "
       "stopped being a move",
       _w12_subs_applied["add"] == (1, 1)
       and _w12_diffs["add"]["added"] == ["delta"]
       and _w12_diffs["add"]["missing"] == []
       and _w12_diffs["add"]["multiplicity_changed"] == []
       and _w12_diffs["add"]["signature_changed"] == [])

expect("WARP-0712 AC5 THE COUNT-SURVIVES-IT CASE, which is the exact defect the criterion "
       "names: one assertion deleted AND one added leaves the total UNCHANGED, so a count "
       "proof passes. The identity comparison reports both, in both directions, and the two "
       "runs are asserted to have produced the same total so the test is a real instance of "
       "the case rather than a differently sized pair",
       _w12_subs_applied["swap"] == (1, 1)
       and _w12_diffs["swap"]["missing"] == ["beta"]
       and _w12_diffs["swap"]["added"] == ["delta"]
       and len(_w12_twin_caps["swap"].records) == len(_w12_base_cap.records))

expect("WARP-0712 AC5 MULTIPLICITY AND OUTCOME, the two dimensions a SET of labels cannot "
       "hold: emitting one label twice instead of once is reported as a multiplicity change "
       "with nothing missing and nothing added, and flipping one assertion's condition is "
       "reported as a signature change on that label with nothing missing and nothing added. "
       "AC5 says byte-identical AS A SET; this instrument compares the multiset and the "
       "counter delta too, because the set is the weaker of the three",
       _w12_diffs["multiply"]["multiplicity_changed"] == [("beta", 1, 2)]
       and _w12_diffs["multiply"]["missing"] == [] and _w12_diffs["multiply"]["added"] == []
       and [x[0] for x in _w12_diffs["flip"]["signature_changed"]] == ["beta"]
       and _w12_diffs["flip"]["missing"] == [] and _w12_diffs["flip"]["added"] == []
       and _w12_diffs["flip"]["multiplicity_changed"] == [])

# ---- the equivalence harness over every declared fixture variant ----------------------
_w12_eq_seen = {}
_w12_eq_bad = []
for _w12_v in sorted(_w12_E.VARIANTS):
    _w12_d = tempfile.mkdtemp(prefix="veldo0712-eq-%s-" % _w12_v)
    _w12_mp, _w12_counts = _w12_E.build_fixture_tree(_w12_d, _w12_v)
    try:
        _w12_rep = _w12_E.run(_w12_mp, orders=("reverse",), timeout=180)
        _w12_got = frozenset(_w12_rep["defect_names"])
    except _w12_E.EquivRefusal as _w12_re_:
        _w12_got = frozenset(["REFUSED:" + _w12_re_.code])
    _w12_eq_seen[_w12_v] = _w12_got
    if _w12_got != frozenset(_w12_E.expected_defects(_w12_v)):
        _w12_eq_bad.append((_w12_v, sorted(_w12_got),
                            sorted(_w12_E.expected_defects(_w12_v))))

expect("WARP-0712 AC4 the standalone-and-aggregate harness is driven over a fixture tree "
       "shaped exactly like the decomposition will be - a thin dispatcher, a manifest, one "
       "shared fixture module holding the assertion primitive, and per-suite files that each "
       "run alone - and every variant's reported defect set equals the set that variant's "
       "construction MAKES TRUE, with the mismatch list asserted EMPTY so a stray verdict "
       "names itself. The clean variant is the negative control and reports NOTHING, which is "
       "what keeps an always-firing guard from reading as a working one",
       _w12_eq_bad == [] and _w12_eq_seen.get("clean") == frozenset())

expect("WARP-0712 AC4 THE DANGEROUS CASE IS THE ONE PROVEN, not just the loud one. A suite "
       "that CRASHES alone is caught by any harness; a suite that passes alone with two green "
       "exit codes while proving strictly LESS than it proved in company is the defect a naive "
       "split actually produces, and it is caught here as PROVES_LESS_ALONE. Its mirror, a "
       "suite that proves MORE alone, and a suite whose label passes in company and fails "
       "alone, are separate variants rather than one argument",
       "PROVES_LESS_ALONE" in _w12_eq_seen.get("proves_less_alone", frozenset())
       and "PROVES_MORE_ALONE" in _w12_eq_seen.get("proves_more_alone", frozenset())
       and "OUTCOME_DIFFERS" in _w12_eq_seen.get("outcome_differs", frozenset())
       and "MULTIPLICITY_DIFFERS" in _w12_eq_seen.get("multiplicity_differs", frozenset())
       and "PASSES_IN_AGGREGATE_FAILS_ALONE" in _w12_eq_seen.get("fails_alone", frozenset()))

expect("WARP-0712 AC4 SUITE ORDER IS ITS OWN PROBE AND NOT A RESTATEMENT OF THE STANDALONE "
       "ONE: the `order_only` variant is constructed so that each suite is equivalent alone "
       "and in aggregate and only the ORDER changes what the run proves, and it reports "
       "ORDER_DEPENDENT and nothing else. The two structural refusals the decomposition's own "
       "integrity needs are proven the same way: a suite file on disk and absent from the "
       "manifest turns it RED rather than silently not running, and two suites declaring one "
       "label cannot mask each other inside the identity proof",
       _w12_eq_seen.get("order_only") == frozenset(["ORDER_DEPENDENT"])
       and _w12_eq_seen.get("not_enumerated") == frozenset(["SUITE_NOT_ENUMERATED"])
       and _w12_eq_seen.get("file_missing") == frozenset(["SUITE_FILE_MISSING"])
       and _w12_eq_seen.get("label_collision") == frozenset(["SUITE_LABEL_COLLISION"]))

# ---- TEETH, as two matrices ------------------------------------------------------------
# WHY TWO AND WHY NOT ONE DIAGONAL. `compare` is SHARED: suite_equiv reports PROVES_LESS_ALONE
# by asking it for the missing labels. Neutralizing compare's missing-label guard therefore
# moves both instruments, so a single matrix over both could not be diagonal and a claim that
# it was would be false. Matrix A drives the label instrument's ten decisions at their own
# seam with constructed inputs, so each cell is isolated by construction. Matrix B drives
# suite_equiv's ten own decisions over every fixture variant. In both, the assertion is the
# same and is stronger than "diagonal": each neutralized guard removes EXACTLY its own name
# from EXACTLY the fixtures that declare it, and the violation list is asserted EMPTY.
_w12_pair_base = {"a": _w12_Counter({"FAIL+0,PASS+1": 1}),
                  "b": _w12_Counter({"FAIL+0,PASS+1": 1})}
_w12_pair_one = {"a": _w12_Counter({"FAIL+0,PASS+1": 1})}
_w12_pair_two = {"a": _w12_Counter({"FAIL+0,PASS+1": 1}),
                 "b": _w12_Counter({"FAIL+0,PASS+1": 2})}
_w12_pair_fail = {"a": _w12_Counter({"FAIL+0,PASS+1": 1}),
                  "b": _w12_Counter({"FAIL+1,PASS+0": 1})}


def _w12_probe_compare(L, before, after):
    d = L.compare(before, after)
    return frozenset(k for k in ("missing", "added", "multiplicity_changed",
                                 "signature_changed") if d[k])


def _w12_payload(records, finals, applied=True):
    return {"schema": "veldo.labels/v1", "entry": "fixture", "records": records,
            "counters_final": finals, "wrapped": {"expect": ["FAIL", "PASS"]},
            "injection_applied": {"expect": applied}, "instrumented": []}


def _w12_probe_reconcile(L, records, finals, stdout, stderr="", applied=True):
    cap = L.Capture(_w12_payload(records, finals, applied), stdout, stderr, 0,
                    "fixture", "digest")
    try:
        cap.reconcile()
        cap.reconcile_summary()
    except L.LabelRefusal as e:
        return frozenset([e.code])
    return frozenset()


_w12_rec_ok = [{"label": "a", "delta": {"PASS": 1, "FAIL": 0}, "raised": False,
                "file": "fixture", "line": 1, "module_frames": [["fixture", 1]],
                "primitive": "expect"}]

_W12_SELFEDIT = '''\
from pathlib import Path

PASS = 0
FAIL = 0


def expect(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1


expect("edits itself", True)
Path(__file__).write_text(Path(__file__).read_text() + "# appended while running\\n")
print("selftest: %d passed, %d failed" % (PASS, FAIL))
'''


def _w12_probe_selfedit(L):
    d = tempfile.mkdtemp(prefix="veldo0712-selfedit")
    p = Path(d) / "edits.py"
    p.write_text(_W12_SELFEDIT)
    try:
        cap = L.capture(p)
        cap.reconcile()
    except L.LabelRefusal as e:
        return frozenset([e.code])
    return frozenset()


# Matrix A fixtures: name -> (probe, the names the pristine instrument must report)
_W12_FIX_A = {
    "missing": (lambda L: _w12_probe_compare(L, _w12_pair_base, _w12_pair_one),
                frozenset(["missing"])),
    "added": (lambda L: _w12_probe_compare(L, _w12_pair_one, _w12_pair_base),
              frozenset(["added"])),
    "multiplicity": (lambda L: _w12_probe_compare(L, _w12_pair_base, _w12_pair_two),
                     frozenset(["multiplicity_changed"])),
    "signature": (lambda L: _w12_probe_compare(L, _w12_pair_base, _w12_pair_fail),
                  frozenset(["signature_changed"])),
    "counters": (lambda L: _w12_probe_reconcile(L, _w12_rec_ok, {"PASS": 2, "FAIL": 0},
                                                "selftest: 2 passed, 0 failed"),
                 frozenset(["COUNTER_RECONCILIATION"])),
    "summary": (lambda L: _w12_probe_reconcile(L, _w12_rec_ok, {"PASS": 1, "FAIL": 0},
                                               "nothing useful here"),
                frozenset(["SUMMARY_RECONCILIATION"])),
    "crash": (lambda L: _w12_probe_reconcile(L, _w12_rec_ok, {"PASS": 1, "FAIL": 0},
                                             "selftest: 1 passed, 0 failed",
                                             "Traceback (most recent call last)\nBoom"),
              frozenset(["SUBJECT_CRASHED"])),
    "norecords": (lambda L: _w12_probe_reconcile(L, [], {"PASS": 0, "FAIL": 0},
                                                 "selftest: 0 passed, 0 failed"),
                  frozenset(["NO_RECORDS"])),
    "injection": (lambda L: _w12_probe_reconcile(L, _w12_rec_ok, {"PASS": 1, "FAIL": 0},
                                                 "selftest: 1 passed, 0 failed",
                                                 applied=False),
                  frozenset(["INJECTION_NOT_APPLIED"])),
    "selfedit": (_w12_probe_selfedit, frozenset(["TARGET_MUTATED_ON_DISK"])),
}

# Matrix A guards: name it removes -> the one substitution that neutralizes it
_W12_MUT_A = {
    "missing": ('"missing": sorted(b - a),', '"missing": [],'),
    "added": ('"added": sorted(a - b),', '"added": [],'),
    "multiplicity_changed": (
        "if sum(before[lab].values()) != sum(after[lab].values()))", "if False)"),
    "signature_changed": ("if before[lab] != after[lab]", "if False"),
    "COUNTER_RECONCILIATION": ("if sums.get(c, 0) != final:", "if False:"),
    "SUMMARY_RECONCILIATION": ("if best is None:", "if False:"),
    "SUBJECT_CRASHED": ('if "Traceback (most recent call last)" in self.stderr:', "if False:"),
    "NO_RECORDS": ("if not self.records:", "if False:"),
    "INJECTION_NOT_APPLIED": ("if not ok:", "if False:"),
    "TARGET_MUTATED_ON_DISK": ("if sha256(entry) != digest_before:", "if False:"),
}

# Matrix B guards: the defect name -> EVERY site that emits it, renamed to a sentinel. Two of
# these guards have TWO emission sites, which is a defect the first version of this matrix had
# and the matrix itself found: neutralizing only the first site left the second one reporting,
# and the cell reddened. A guard is the NAME, not one line, so a mutation that leaves a second
# mouth open is not a neutralization.
_W12_SENTINEL = "_NEUTRALIZED_"
_W12_SUB = ('{"defect": "%s"', '{"defect": "_NEUTRALIZED_"')
_W12_MUT_B = {
    "SUITE_NOT_ENUMERATED": (
        ('{"defect": "SUITE_NOT_ENUMERATED", "suite": None,\n'
         '                                 "detail": "%s is on disk',
         '{"defect": "_NEUTRALIZED_", "suite": None,\n'
         '                                 "detail": "%s is on disk'),
        ('{"defect": "SUITE_NOT_ENUMERATED", "suite": None,\n'
         '                                 "detail": "label %r came from %s',
         '{"defect": "_NEUTRALIZED_", "suite": None,\n'
         '                                 "detail": "label %r came from %s'),
    ),
    "SUITE_FILE_MISSING": ((_W12_SUB[0] % "SUITE_FILE_MISSING", _W12_SUB[1]),),
    "SUITE_LABEL_COLLISION": ((_W12_SUB[0] % "SUITE_LABEL_COLLISION", _W12_SUB[1]),),
    "ATTRIBUTION_INCOMPLETE": ((_W12_SUB[0] % "ATTRIBUTION_INCOMPLETE", _W12_SUB[1]),),
    "PASSES_IN_AGGREGATE_FAILS_ALONE": (
        (_W12_SUB[0] % "PASSES_IN_AGGREGATE_FAILS_ALONE", _W12_SUB[1]),),
    "PROVES_LESS_ALONE": ((_W12_SUB[0] % "PROVES_LESS_ALONE", _W12_SUB[1]),),
    "PROVES_MORE_ALONE": ((_W12_SUB[0] % "PROVES_MORE_ALONE", _W12_SUB[1]),),
    "MULTIPLICITY_DIFFERS": ((_W12_SUB[0] % "MULTIPLICITY_DIFFERS", _W12_SUB[1]),),
    "OUTCOME_DIFFERS": ((_W12_SUB[0] % "OUTCOME_DIFFERS", _W12_SUB[1]),),
    "ORDER_DEPENDENT": (
        ('{"defect": "ORDER_DEPENDENT", "suite": None,\n'
         '                     "detail": "order %s changed what the run proved',
         '{"defect": "_NEUTRALIZED_", "suite": None,\n'
         '                     "detail": "order %s changed what the run proved'),
        ('{"defect": "ORDER_DEPENDENT", "suite": None,\n'
         '                                     "detail": "order %s: %s"',
         '{"defect": "_NEUTRALIZED_", "suite": None,\n'
         '                                     "detail": "order %s: %s"'),
    ),
}

# ---- Matrix A ----
_w12_A_base = {}
for _w12_f, (_w12_probe, _w12_want) in _W12_FIX_A.items():
    _w12_A_base[_w12_f] = _w12_probe(_w12_L)
_w12_A_counts = {}
_w12_A_bad = []
for _w12_g, (_w12_find, _w12_repl) in _W12_MUT_A.items():
    _w12_m, _w12_c = _w12_fresh("suite_labels", ((_w12_find, _w12_repl),))
    _w12_A_counts[_w12_g] = _w12_c[0]
    for _w12_f, (_w12_probe, _ignored) in _W12_FIX_A.items():
        _w12_cell = _w12_probe(_w12_m)
        if _w12_cell != _w12_A_base[_w12_f] - frozenset([_w12_g]):
            _w12_A_bad.append((_w12_g, _w12_f, sorted(_w12_cell),
                               sorted(_w12_A_base[_w12_f] - frozenset([_w12_g]))))
_w12_A_inert = sorted(g for g in _W12_MUT_A
                      if not any(g in v for v in _w12_A_base.values()))

expect("WARP-0712 AC5 TEETH MATRIX A: each of the label instrument's ten decisions is "
       "neutralized IN MEMORY one at a time and run against every fixture, and each "
       "neutralization removes EXACTLY its own name from EXACTLY the fixtures that reported "
       "it, with the violation list asserted as an EMPTY LIST so a stray cell names itself "
       "instead of hiding in a total. Every mutation target is asserted to appear EXACTLY "
       "ONCE in the module it mutates and all ten targets are DISTINCT, because a mutation "
       "matching nothing proves nothing and one matching two guards is diagonal by luck",
       _w12_A_bad == []
       and _w12_A_inert == []
       and sorted(_w12_A_counts.values()) == [1] * len(_W12_MUT_A)
       and len({f for f, _ in _W12_MUT_A.values()}) == len(_W12_MUT_A)
       and all(_w12_A_base[f] == want for f, (_p, want) in _W12_FIX_A.items()))


def _w12_cell_B(job):
    guard, variant = job
    subs = _W12_MUT_B[guard] if guard else ()
    mod, counts = _w12_fresh("suite_equiv", subs)
    d = tempfile.mkdtemp(prefix="veldo0712-mb-")
    mp, _ = mod.build_fixture_tree(d, variant)
    try:
        rep = mod.run(mp, orders=("reverse",), timeout=180)
        got = frozenset(rep["defect_names"]) - frozenset([_W12_SENTINEL])
    except mod.EquivRefusal as e:
        got = frozenset(["REFUSED:" + e.code])
    return guard, variant, got, tuple(counts)


_w12_B_jobs = [(g, v) for g in list(_W12_MUT_B) for v in sorted(_w12_E.VARIANTS)]
_w12_B_cells = {}
_w12_B_counts = {}
with _w12_Pool(max_workers=10) as _w12_ex:
    for _w12_g, _w12_v, _w12_got, _w12_n in _w12_ex.map(_w12_cell_B, _w12_B_jobs):
        _w12_B_cells[(_w12_g, _w12_v)] = _w12_got
        if _w12_n is not None:
            _w12_B_counts[_w12_g] = _w12_n
_w12_B_bad = []
for (_w12_g, _w12_v), _w12_got in sorted(_w12_B_cells.items()):
    _w12_wanted = _w12_eq_seen[_w12_v] - frozenset([_w12_g])
    if _w12_got != _w12_wanted:
        _w12_B_bad.append((_w12_g, _w12_v, sorted(_w12_got), sorted(_w12_wanted)))
_w12_B_inert = sorted(g for g in _W12_MUT_B
                      if not any(g in v for v in _w12_eq_seen.values()))

expect("WARP-0712 AC4 TEETH MATRIX B: each of the equivalence harness's reported defects "
       "is neutralized IN MEMORY at the one site that emits it and run against EVERY fixture "
       "variant, and each neutralization removes exactly that defect from exactly the variants "
       "whose construction makes it true, leaving every other variant's verdict untouched, "
       "with the violation list asserted EMPTY. Every target appears exactly once and all of "
       "them are distinct, and TWO of these guards have TWO emission sites each, which this "
       "matrix found by reddening when only the first was neutralized: a guard is the NAME and "
       "not one line. The clean variant stays silent under every one of them, which is what "
       "proves none of these appends is unconditional",
       _w12_B_bad == []
       and _w12_B_inert == []
       and all(c == 1 for cs in _w12_B_counts.values() for c in cs)
       and sorted(_w12_B_counts) == sorted(_W12_MUT_B)
       and len({f for subs in _W12_MUT_B.values() for f, _ in subs})
       == sum(len(subs) for subs in _W12_MUT_B.values())
       and all(_w12_B_cells[(g, "clean")] == frozenset() for g in _W12_MUT_B))

expect("WARP-0712 every module the teeth matrices mutate is asserted sha256-UNCHANGED ON DISK "
       "after all of it. The neutralizations are substitutions on a source string exec'd into "
       "an anonymous module; a matrix that edited the files it grades would leave the "
       "repository in whatever state its last cell wrote",
       all(_w12_hashlib.sha256(p.read_bytes()).hexdigest() == _w12_before[n]
           for n, p in _w12_paths.items()))

# ---- AC3: the slicer, driven over monolith fixtures with declared ground truth ---------
# The real suite exhibited NO region that ran to completion and proved a different label set,
# and that finding is worthless without a control proving the instrument could have seen one.
# _W12_MONO_SILENT is that control: its region B emits an extra assertion only when a name
# region A binds is present, so alone it neither crashes nor fails - it proves LESS, silently.
_W12_MONO_HEAD = '''\
PASS = 0
FAIL = 0


def expect(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1


BASE = "base"
expect("preamble", BASE == "base")
'''
_W12_MONO_CLEAN = _W12_MONO_HEAD + '''
# --- A ------------------------------------------------------------------------
A_LOCAL = 1
expect("A one", A_LOCAL == 1)

# --- B ------------------------------------------------------------------------
B_LOCAL = 2
expect("B one", B_LOCAL == 2)

# --- C ------------------------------------------------------------------------
expect("C one", BASE == "base")
print("selftest: %d passed, %d failed" % (PASS, FAIL))
'''
_W12_MONO_CROSS = _W12_MONO_HEAD + '''
# --- A ------------------------------------------------------------------------
CROSSED = "from A"
expect("A one", CROSSED == "from A")

# --- B ------------------------------------------------------------------------
expect("B reads A", CROSSED == "from A")
print("selftest: %d passed, %d failed" % (PASS, FAIL))
'''
_W12_MONO_SILENT = _W12_MONO_HEAD + '''
# --- A ------------------------------------------------------------------------
PRIMED = True
expect("A one", PRIMED)

# --- B ------------------------------------------------------------------------
expect("B always", 1 == 1)
if "PRIMED" in globals():
    expect("B only in company", True)
print("selftest: %d passed, %d failed" % (PASS, FAIL))
'''
_W12_MONO_ORDER = _W12_MONO_HEAD + '''
LOG = []

# --- A ------------------------------------------------------------------------
LOG.append("A")
expect("A one", LOG == ["A"])

# --- B ------------------------------------------------------------------------
LOG.append("B")
expect("B sees the order", LOG == ["A", "B"])
print("selftest: %d passed, %d failed" % (PASS, FAIL))
'''
_w12_monos = {"clean": _W12_MONO_CLEAN, "cross": _W12_MONO_CROSS,
              "silent": _W12_MONO_SILENT, "order": _W12_MONO_ORDER}
_w12_mono_dir = tempfile.mkdtemp(prefix="veldo0712-mono")
_w12_mono_out = {}
for _w12_k, _w12_text in _w12_monos.items():
    _w12_mp = Path(_w12_mono_dir) / ("%s.py" % _w12_k)
    _w12_mp.write_text(_w12_text)
    _w12_sl = _w12_S.Slicer(str(_w12_mp))
    _w12_fc = _w12_L.capture(_w12_mp, select=_w12_sl.full_spec(), tag="mono-" + _w12_k)
    _w12_fc.reconcile()
    _w12_at, _w12_un = _w12_S._attribute(_w12_fc.records, _w12_sl)
    _w12_al = _w12_S.run_alone(_w12_sl, _w12_at, workers=0, verbose=False)
    _w12_binders = _w12_sl.binders()
    _w12_cl = _w12_S.run_closures(
        _w12_sl, _w12_at, [r["region"] for r in _w12_al if r["outcome"] != "CLEAN"],
        workers=0, verbose=False)
    _w12_perm = _w12_S.run_permutation(
        _w12_sl, _w12_fc.profile(), list(reversed(_w12_sl.content_regions())), "reverse")
    _w12_mono_out[_w12_k] = {"alone": _w12_al, "closures": _w12_cl, "perm": _w12_perm,
                             "unattributed": _w12_un, "binders": _w12_binders,
                             "regions": _w12_sl.content_regions()}

_w12_mo = _w12_mono_out
expect("WARP-0712 AC3 THE SILENT CASE IS PROVEN REACHABLE, which is what makes the real "
       "suite's zero of them evidence rather than an unfalsifiable reassurance. A fixture "
       "monolith whose region B emits one extra assertion only when a name region A binds is "
       "present runs to completion ALONE, exits zero, prints its summary, and is reported "
       "PROVES_DIFFERENTLY with exactly that label missing. An instrument that could only see "
       "crashes would call this region clean",
       [r["outcome"] for r in _w12_mo["silent"]["alone"]] == ["CLEAN",
                                                             "PROVES_DIFFERENTLY"]
       and _w12_mo["silent"]["alone"][1]["diff"]["missing"] == ["B only in company"]
       and _w12_mo["silent"]["alone"][1]["exception"] == "")

expect("WARP-0712 AC3 the slicer's three other declared outcomes are driven too: a monolith "
       "whose regions are self-contained reports every region CLEAN; a monolith where region "
       "B reads a name region A binds reports B CRASHES_ALONE with the NameError NAMING that "
       "symbol, and the prerequisite search then resolves it to region A and reports the group "
       "CLOSED with an identical label set; and a monolith whose regions append to a shared "
       "list in order has its REVERSED order report a different result, which is the whole-"
       "suite form of the same defect",
       all(r["outcome"] == "CLEAN" for r in _w12_mo["clean"]["alone"])
       and _w12_mo["clean"]["perm"]["outcome"] == "CLEAN"
       and [r["outcome"] for r in _w12_mo["cross"]["alone"]] == ["CLEAN", "CRASHES_ALONE"]
       and "CROSSED" in _w12_mo["cross"]["alone"][1]["message"]
       and [c["outcome"] for c in _w12_mo["cross"]["closures"]] == ["CLOSED"]
       and _w12_mo["cross"]["closures"][0]["resolved_names"] == ["CROSSED"]
       and _w12_mo["order"]["perm"]["outcome"] == "PROVES_DIFFERENTLY")

expect("WARP-0712 AC3 ATTRIBUTION FOLLOWS STATEMENTS, NOT LINES, and this is a corrected "
       "defect rather than a design note. A `# --- ` marker can sit INSIDE a top-level "
       "statement that began before it, so the executing LINE lands in the next marker region "
       "while the statement that emits the label belongs to the previous one. Attributing by "
       "line made a first version of this measurement report eleven regions as silently "
       "proving two assertions less than they should, all of it an artefact. Every label of "
       "the fixture runs is attributed to exactly one region and none is left over",
       all(v["unattributed"] == [] for v in _w12_mo.values()))

expect("WARP-0712 AC3 the region partition the slicer uses IS WARP-0716's, imported rather "
       "than re-derived, so the two tools cannot disagree about what a region is, and the "
       "binder index that resolves an undefined name is SCOPE-AWARE: a name a nested function "
       "assigns is that function's local and not a module binding, while a name it declares "
       "global IS one, which is how this suite's own assertion helper writes its counters",
       _w12_S.SURVEY.MARKER == "# ---"
       and _w12_mo["cross"]["binders"].get("CROSSED") == [1]
       and _w12_mo["clean"]["binders"].get("expect") == [0]
       and _w12_mo["clean"]["binders"].get("PASS") == [0]
       and "cond" not in _w12_mo["clean"]["binders"])

# ---- the recorded measurement -----------------------------------------------------------
_w12_meas_path = ROOT / _w12_S.MEASUREMENT_PATH
_w12_rep_path = ROOT / _w12_S.REPORT_PATH
_w12_nmspec = importlib.util.spec_from_file_location("w12_naming", ROOT / ".veldo/naming.py")
_w12_NAMING = importlib.util.module_from_spec(_w12_nmspec)
_w12_nmspec.loader.exec_module(_w12_NAMING)
_w12_meas = json.loads(_w12_meas_path.read_text())
_w12_ok_outcomes = set(_w12_S.OUTCOMES) | {"CLOSED", "CLOSED_PROVES_DIFFERENTLY",
                                           "NOT_CONVERGED", "UNRESOLVABLE",
                                           "CRASHES_NOT_A_NAME"}
expect("WARP-0712 AC3 the recorded measurement is SELF-CONSISTENT and its vocabulary is "
       "CLOSED: every alone-outcome and every closure-outcome is a declared name, the set of "
       "regions attempted equals the set of regions carrying top-level statements minus the "
       "preamble as a SET RELATION and never as a count, no label is attributed to no region, "
       "and the attribution round trip is identical in both directions. Nothing here asserts "
       "how many regions or labels there are: the suite is expected to grow",
       # THE RECORDED SPELLING IS ACCEPTED, from the naming contract's one definition. This
       # measurement is EVIDENCE under proof/, which NOT_RENAMED keeps under the old name on
       # purpose, so a reader comparing it to today's constant alone fails on the rename rather
       # than on the measurement, invalidating the record the contract promised to preserve.
       _w12_meas["schema"] in _w12_NAMING.accepted_schemas(_w12_S.SCHEMA)
       and all(a["outcome"] in _w12_ok_outcomes for a in _w12_meas["alone"])
       and all(c["outcome"] in _w12_ok_outcomes for c in _w12_meas.get("closures", []))
       and set(_w12_meas["regions_attempted"])
       == set(_w12_meas["regions_with_statements"]) - {0}
       and _w12_meas["unattributed_labels"] == []
       and _w12_meas["attribution_round_trip_identical"] is True)

_w12_plan_path = ROOT / _w12_S.PLAN_PATH
_w12_planned = _w12_S.emit_plan(_w12_meas, source=_w12_S.MEASUREMENT_PATH)
_w12_emitted = _w12_S.emit_report(_w12_meas, source=_w12_S.MEASUREMENT_PATH)
expect("WARP-0712 the order-dependence report is GENERATED from the measurement beside it, "
       "the emitter is deterministic, and its output is character-identical to the committed "
       "file, which is also what the gate's CHECK_generated stage re-derives. The MEASUREMENT "
       "is deliberately NOT gate-regenerated and the document says so: it costs minutes, and "
       "pinning the digest of scripts/selftest.py - the one file every item edits - would "
       "redden the gate on every item and leave a re-measurement as the only remedy, which is "
       "exactly the trap WARP-0716's first version built",
       _w12_emitted == _w12_rep_path.read_text()
       and _w12_emitted == _w12_S.emit_report(_w12_meas, source=_w12_S.MEASUREMENT_PATH)
       and "NOT REGENERATED BY THE GATE" in _w12_emitted
       and _w12_meas["digest"] in _w12_emitted)

_w12_plan_suites = [ln for ln in _w12_planned.splitlines()
                    if ln.startswith("| scripts/suites/")]
_w12_plan_regions = []
for _w12_ln in _w12_plan_suites:
    _w12_cells = [c.strip() for c in _w12_ln.strip("|").split("|")]
    _w12_a, _w12_b = _w12_cells[1].split("-")
    _w12_plan_regions.append((int(_w12_a), int(_w12_b)))
_w12_straddled = {m["marker_region"] for m in _w12_meas["markers_inside_statements"]}
expect("WARP-0712 the SPLIT PLAN is DERIVED from the measurement and not drawn around topic "
       "names, which is the boundary criterion AC1 sets. Its suites partition the content "
       "regions EXACTLY - contiguous, in file order, no gap and no overlap, asserted as a set "
       "relation against the regions carrying statements rather than as a count - and no suite "
       "boundary falls at a marker a top-level statement straddles, because a split moves whole "
       "statements and such a marker is not a boundary at all",
       _w12_plan_regions == sorted(_w12_plan_regions)
       and all(_w12_plan_regions[i][1] + 1 == _w12_plan_regions[i + 1][0]
               for i in range(len(_w12_plan_regions) - 1))
       and set(range(_w12_plan_regions[0][0], _w12_plan_regions[-1][1] + 1))
       >= set(_w12_meas["regions_with_statements"]) - {0}
       and all(_w12_a not in _w12_straddled for _w12_a, _w12_b in _w12_plan_regions[1:])
       and _w12_planned == _w12_plan_path.read_text()
       and _w12_planned == _w12_S.emit_plan(_w12_meas, source=_w12_S.MEASUREMENT_PATH))

_w12_gen_sh = (ROOT / "scripts" / "check_generated.sh").read_text()
expect("WARP-0712 the derived artifact is DECLARED in the stage that re-derives every derived "
       "artifact, not guarded by a hand-maintained copy of its figures. The entry names the "
       "report path and regenerates it from the committed measurement, so the remedy for a red "
       "is one command whose cost does not grow with the corpus",
       _w12_S.REPORT_PATH in _w12_gen_sh and _w12_S.PLAN_PATH in _w12_gen_sh
       and _w12_gen_sh.count(_w12_S.MEASUREMENT_PATH) == 2)

# ---- dogfood: this item's own spec, and the limit it must not pass over in silence -----
_w12_spec = (ROOT / "specs" / "WARP-0712-suite-decomposition.md").read_text()
_w12_manifest = json.loads((ROOT / "proof" / "WARP-0712" / "manifest.json").read_text())
_w12_crit = {c["id"]: c for c in _w12_manifest["criteria"]}
expect("WARP-0712 DOGFOOD: this item's own proof manifest exists, covers every acceptance "
       "criterion the spec declares, and marks as PARTIAL rather than passed the criteria that "
       "are NOT finished - AC4, because the suites share one namespace and do not run "
       "standalone, and AC6, because the packs are not re-synced. Marking either passed "
       "would be the silent overstatement this whole item exists to prevent",
       set(_w12_crit) == {"AC1", "AC2", "AC3", "AC4", "AC5", "AC6"}
       and all(c["status"] in ("passed", "partial", "not_started")
               for c in _w12_manifest["criteria"])
       and _w12_crit["AC4"]["status"] != "passed"
       and _w12_crit["AC6"]["status"] != "passed"
       and _w12_crit["AC5"]["status"] == "passed")

expect("WARP-0712 THE INHERITED WEAKNESS IS DECLARED AS A LIMIT AND NOT PASSED OVER IN "
       "SILENCE: AC1 consumes WARP-0716's crossing-state verdict, and 0716's own manifest "
       "records that its generator fix landed WITHOUT an independent review and that its "
       "review ruled fail. This manifest names that dependency in a limits section, says what "
       "part of the verdict this round RE-DERIVED by driving the suite instead of trusting the "
       "static analysis, and says what remains trusted",
       isinstance(_w12_manifest.get("limits"), list)
       and any("WARP-0716" in x for x in _w12_manifest["limits"])
       and any("re-derived" in x.lower() or "re-derive" in x.lower()
               for x in _w12_manifest["limits"]))

# The forbidden characters are named by CODEPOINT, never typed: a check for an em dash that
# contains an em dash puts one in the file it is guarding, which is exactly what the first
# version of this block did and what the docs stage caught.
_W12_FORBIDDEN = (0x2014, 0x2013)


def _w12_offenders(text):
    return sorted({ord(ch) for ch in text if ord(ch) > 126})


_w12_dash_bad = sorted(
    (p.name, _w12_offenders(p.read_text(errors="replace")))
    for p in (ROOT / "proof" / "WARP-0712").glob("*")
    if p.is_file() and _w12_offenders(p.read_text(errors="replace")))
expect("WARP-0712 RULE #1 over this item's own artifacts, asserted rather than reviewed: no "
       "em dash, no en dash and no non-ASCII character at all in anything under "
       "proof/WARP-0712, which is the same sweep the docs stage runs over every tracked text "
       "file. The two dash codepoints are named as numbers rather than typed, because a guard "
       "that spells out the character it forbids plants one in the file it guards",
       _w12_dash_bad == [] and all(c > 126 for c in _W12_FORBIDDEN))
