"""VELDO-0022: Section 2 admission semantics (PLAN-0019 W7).

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, so its declared
prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 34_veldo_0022_admission

WHAT IS UNDER TEST. .veldo/admission_contract.py: one governed work class per item with its
class-specific authority, lane, request and priority (AC1); the R66 clause-to-predicate table for
automatic defect admission and the routing on failure (AC2); quarantine, standing-ticket and
break-glass bounds (AC3); and the machine-comparable scope whose material change invalidates
admission, with the admission-debt report (AC4). The four declared falsifiers are applied to a COPY
of the module and required to turn their named row red while the unmutated module passes it.
"""
import importlib.util as _v22_ilu
import shutil as _v22_shutil

_v22_spec = _v22_ilu.spec_from_file_location("v22_admission", ROOT / ".veldo" / "admission_contract.py")
AD22 = _v22_ilu.module_from_spec(_v22_spec)
_v22_spec.loader.exec_module(AD22)
_v22_src = (ROOT / ".veldo" / "admission_contract.py").read_text()
_v22_authspec = _v22_ilu.spec_from_file_location("v22_authz", ROOT / ".veldo" / "authorization.py")
AUTH22 = _v22_ilu.module_from_spec(_v22_authspec)
_v22_authspec.loader.exec_module(AUTH22)


def _v22_mutated(old, new):
    d = Path(tempfile.mkdtemp(prefix="v22mut"))
    assert _v22_src.count(old) == 1, (old[:60], _v22_src.count(old))
    (d / "admission_contract.py").write_text(_v22_src.replace(old, new))
    spec = _v22_ilu.spec_from_file_location("v22_mut_%s" % d.name, d / "admission_contract.py")
    m = _v22_ilu.module_from_spec(spec)
    spec.loader.exec_module(m)
    _v22_shutil.rmtree(d, ignore_errors=True)
    return m


# ---------------------------------------------------------------------------------------------
# AC1: one class, class-specific authority.
# ---------------------------------------------------------------------------------------------
_v22_dmitry = {"kind": "person", "principal": "dmitry", "roles": ["admission_authority", "project_owner"]}
_v22_sec = {"kind": "person", "principal": "asya", "roles": ["security_authority"]}
_v22_ops = {"kind": "person", "principal": "asya", "roles": ["operations_authority"]}
_v22_agent = {"kind": "preparation_agent", "principal": "prep-run-1"}
_v22_req = {"revision": 2, "signed_revision": 2, "signed_by": "dmitry"}
_v22_pol = lambda kind: {"kind": kind, "signer": "dmitry", "digest": "sha256:p", "version": 1}
expect("VELDO-0022 AC1 admission/registry: the work classes are exactly the seven of R08, the class policy registry equals them in "
       "both directions, every lane is one of the three, and the machine set is bound to authorization.MACHINE_ACTORS",
       set(AD22.WORK_CLASSES) == {"PRODUCT_CHANGE", "POLICY_DEFECT", "SECURITY_EMERGENCY", "INCIDENT_CONTAINMENT", "STANDING_MAINTENANCE", "TECHNICAL_CHANGE", "COMPLIANCE_EXPIRY"}
       and set(AD22.CLASS_POLICY) == set(AD22.WORK_CLASSES) and all(p["lane"] in AD22.LANES for p in AD22.CLASS_POLICY.values())
       and AD22.MACHINE_ACTORS == AUTH22.MACHINE_ACTORS)
expect("VELDO-0022 AC1 admission/classify: no class, two classes and an unknown class each stay quarantined; one known class classifies",
       AD22.classify({"work_class": []})[0] == "QUARANTINED" and AD22.classify({"work_class": ["PRODUCT_CHANGE", "TECHNICAL_CHANGE"]})[0] == "QUARANTINED"
       and AD22.classify({"work_class": "FEATURE"})[0] == "QUARANTINED" and AD22.classify({"work_class": "PRODUCT_CHANGE"}) == ("PRODUCT_CHANGE", "classified"))
_v22_ctx = {"enrolled_obligation": True, "compliance_authority": "dmitry", "admitted_adapter": True}
_v22_controls = {
    "PRODUCT_CHANGE": (_v22_dmitry, None), "TECHNICAL_CHANGE": (_v22_dmitry, None),
    "POLICY_DEFECT": ({"kind": "service", "principal": "admission-service"}, _v22_pol("defect_policy")),
    "SECURITY_EMERGENCY": (_v22_sec, None), "INCIDENT_CONTAINMENT": (None, _v22_pol("standing_containment")),
    "STANDING_MAINTENANCE": (None, _v22_pol("standing_ticket")), "COMPLIANCE_EXPIRY": (_v22_dmitry, None),
}
_v22_class_failures = []
for _v22_cls, (_v22_adm, _v22_p) in _v22_controls.items():
    _v22_item = {"work_class": _v22_cls}
    if AD22.admission_problems(_v22_item, _v22_req, _v22_adm, _v22_p, {"source": AD22.CLASS_POLICY[_v22_cls]["priority_from"][0]}, _v22_ctx):
        _v22_class_failures.append((_v22_cls, "control refused", AD22.admission_problems(_v22_item, _v22_req, _v22_adm, _v22_p, None, _v22_ctx)))
    if not any("preparation agent" in p for p in AD22.admission_problems(_v22_item, _v22_req, _v22_agent, _v22_p, None, _v22_ctx)):
        _v22_class_failures.append((_v22_cls, "preparation agent admitted"))
    if not any("draft" in p for p in AD22.admission_problems(_v22_item, dict(_v22_req, signed_revision=1), _v22_adm, _v22_p, None, _v22_ctx)):
        _v22_class_failures.append((_v22_cls, "unsigned revision admitted"))
    if AD22.admission_problems(_v22_item, _v22_req, {"kind": "person", "principal": "nobody", "roles": []}, None, None, _v22_ctx) == []:
        _v22_class_failures.append((_v22_cls, "role-less person admitted without policy"))
    if not any("lane" in p for p in AD22.admission_problems(dict(_v22_item, lane="wrong"), _v22_req, _v22_adm, _v22_p, None, _v22_ctx)):
        _v22_class_failures.append((_v22_cls, "wrong lane accepted"))
    if not any("does not grant queue precedence" in p for p in AD22.admission_problems(_v22_item, _v22_req, _v22_adm, _v22_p, {"source": "automatic"}, _v22_ctx)):
        _v22_class_failures.append((_v22_cls, "automatic priority accepted"))
expect("VELDO-0022 AC1 admission/matrix: every class admits under its permitted control (its person's role or its signed policy) and "
       "refuses a preparation agent, an unsigned request revision, a role-less person without policy, a wrong lane and an "
       "automatic priority (failures: %s)" % _v22_class_failures[:3],
       _v22_class_failures == [])
expect("VELDO-0022 AC1 admission/context: compliance work with no enrolled obligation and named authority refuses (none is enrolled "
       "for Veldo), and a production containment or deployment target with no admitted adapter refuses",
       any("none is enrolled" in p for p in AD22.admission_problems({"work_class": "COMPLIANCE_EXPIRY"}, _v22_req, _v22_dmitry, None, None, {}))
       and any("no admitted target adapter" in p for p in AD22.admission_problems({"work_class": "INCIDENT_CONTAINMENT", "target_kind": "production_containment"}, _v22_req, _v22_ops, None, None, {}))
       and AD22.admission_problems({"work_class": "INCIDENT_CONTAINMENT", "target_kind": "production_containment"}, _v22_req, _v22_ops, None, None, {"admitted_adapter": True}) == [])
expect("VELDO-0022 AC1 admission/technical-authority: a preparation agent cannot admit a TECHNICAL_CHANGE; the admission authority can",
       any("preparation agent" in p for p in AD22.admission_problems({"work_class": "TECHNICAL_CHANGE"}, _v22_req, _v22_agent, None, None, {}))
       and AD22.admission_problems({"work_class": "TECHNICAL_CHANGE"}, _v22_req, _v22_dmitry, None, None, {}) == [])
# THE DECLARED FALSIFIER: permit TECHNICAL_CHANGE admission by a preparation agent.
_V22_M1 = _v22_mutated('''    if isinstance(admitter, dict) and admitter.get("kind") in PREPARATION_AGENT_KINDS:
        problems.append("a preparation agent cannot admit %s (or anything): admission is an authorization ceremony (R12)" % cls)
    elif not (''', '''    if isinstance(admitter, dict) and admitter.get("kind") in PREPARATION_AGENT_KINDS and cls == "TECHNICAL_CHANGE":
        pass  # mutant: a preparation agent may admit technical changes
    elif not (''')
expect("VELDO-0022 AC1 admission/technical-authority DRIVEN (the declared falsifier): with a preparation agent permitted to admit "
       "TECHNICAL_CHANGE in a copy, the agent's admission passes, so the row reds; unmutated it is refused",
       _V22_M1.admission_problems({"work_class": "TECHNICAL_CHANGE"}, _v22_req, _v22_agent, None, None, {}) == []
       and AD22.admission_problems({"work_class": "TECHNICAL_CHANGE"}, _v22_req, _v22_agent, None, None, {}) != [])

# ---------------------------------------------------------------------------------------------
# AC2: policy-qualified defects.
# ---------------------------------------------------------------------------------------------
_v22_rep = {"kind": "trusted_reproduction", "quarantine_id": "q-1", "violation_demonstrated": True, "baseline": "sha256:base", "environment_digest": "sha256:env",
            "steps": ["run", "observe"], "expected_behavior": "200", "actual_observations": "500", "artifact_identities": ["sha256:log"]}
_v22_defect = {"specification": "VELDO-0016", "accepted_revision": 1, "failing_criterion": "AC3", "version_supported": True, "reproduction": _v22_rep,
               "affected_surface": ["contract loader"], "change_envelope": ["contract_loader.py"], "repository": "veldo", "severity": "high"}
expect("VELDO-0022 AC2 admission/defect-table: the R66 table has thirteen predicates each citing R66, and a complete defect with a trusted "
       "quarantined reproduction is admitted as POLICY_DEFECT with its severity kept",
       len(AD22.DEFECT_PREDICATES) == 13 and all(c == "R66" for _n, c, _t in AD22.DEFECT_PREDICATES)
       and AD22.defect_admission(_v22_defect) == {"admitted": True, "refusals": [], "routing": {"class": "POLICY_DEFECT", "state": "ADMITTED"}, "severity": "high"})
_v22_fixtures = {
    "cited_accepted_revision": dict(_v22_defect, accepted_revision=None),
    "named_failing_criterion": {k: v for k, v in _v22_defect.items() if k != "failing_criterion"},
    "supported_version": dict(_v22_defect, version_supported=False),
    "trusted_reproduction": dict(_v22_defect, reproduction={"kind": "agent_assertion", "text": "I reproduced it"}),
    "bounded_surface": dict(_v22_defect, affected_surface=[]),
    "change_envelope": dict(_v22_defect, change_envelope=None),
    "not_duplicate": dict(_v22_defect, duplicate_of="VELDO-0099"),
    "not_obsolete": dict(_v22_defect, obsolete=True),
    "not_destructive": dict(_v22_defect, reproduction_destructive=True),
    "not_production_data_dependent": dict(_v22_defect, needs_production_data=True),
    "not_expected_behavior": dict(_v22_defect, is_expected_behavior=True),
    "single_repository": dict(_v22_defect, repositories=["veldo", "core"]),
    "no_disqualifying_change": dict(_v22_defect, changes=["public_interface"]),
}
_v22_table_failures = [n for n, fx in _v22_fixtures.items()
                       if AD22.defect_admission(fx)["admitted"] or not any(r.startswith(n + " ") for r in AD22.defect_admission(fx)["refusals"])]
expect("VELDO-0022 AC2 admission/defect-table: every predicate has one independently failing fixture refused by its own name with the "
       "positive control admitted (failures: %s)" % _v22_table_failures,
       set(_v22_fixtures) == {n for n, _c, _t in AD22.DEFECT_PREDICATES} and _v22_table_failures == [])
expect("VELDO-0022 AC2 admission/routing: a disqualifying interface change routes to AWAITING_GROOMING as PRODUCT_CHANGE, a dependency "
       "policy change as TECHNICAL_CHANGE, a cross-repository defect is BLOCKED and never partially admitted, a critical defect "
       "without clean reproduction goes to security handling, and any other failure goes to grooming; severity is never lowered",
       AD22.defect_admission(dict(_v22_defect, changes=["public_interface"]))["routing"] == {"class": "PRODUCT_CHANGE", "state": "AWAITING_GROOMING", "reason": "the change alters an accepted contract, interface, model, policy or target"}
       and AD22.defect_admission(dict(_v22_defect, changes=["dependency_policy"]))["routing"]["class"] == "TECHNICAL_CHANGE"
       and AD22.defect_admission(dict(_v22_defect, repositories=["veldo", "core"]))["routing"]["state"] == "BLOCKED"
       and AD22.defect_admission(dict(_v22_defect, severity="critical", reproduction=None))["routing"]["class"] == "SECURITY_EMERGENCY"
       and AD22.defect_admission(dict(_v22_defect, reproduction=None))["routing"] == {"class": "POLICY_DEFECT", "state": "AWAITING_GROOMING", "reason": "lack of clean reproduction never lowers severity; grooming"}
       and all(AD22.defect_admission(fx)["severity"] == "high" for fx in _v22_fixtures.values()))
expect("VELDO-0022 AC2 admission/untrusted-reproduction: an agent's reproduction assertion, a trusted record missing a field, one whose "
       "violation was not demonstrated, and one without a quarantine id are each not a trusted reproduction and refuse admission",
       AD22.trusted_reproduction({"kind": "agent_assertion", "text": "reproduced"}) is False
       and AD22.trusted_reproduction({k: v for k, v in _v22_rep.items() if k != "environment_digest"}) is False
       and AD22.trusted_reproduction(dict(_v22_rep, violation_demonstrated=False)) is False
       and AD22.trusted_reproduction({k: v for k, v in _v22_rep.items() if k != "quarantine_id"}) is False
       and AD22.trusted_reproduction(_v22_rep) is True
       and AD22.defect_admission(dict(_v22_defect, reproduction={"kind": "agent_assertion", "text": "reproduced"}))["admitted"] is False)
# THE DECLARED FALSIFIER: admit a defect supported only by an agent reproduction assertion.
_V22_M2 = _v22_mutated('''    if not isinstance(rep, dict) or rep.get("kind") != "trusted_reproduction":
        return False
''', '''    if isinstance(rep, dict) and rep.get("kind") == "agent_assertion":
        return True  # mutant: the agent's word is a reproduction
    if not isinstance(rep, dict) or rep.get("kind") != "trusted_reproduction":
        return False
''')
expect("VELDO-0022 AC2 admission/untrusted-reproduction DRIVEN (the declared falsifier): with an agent assertion accepted as a "
       "reproduction in a copy, the defect is admitted, so the row reds; unmutated it is refused",
       _V22_M2.defect_admission(dict(_v22_defect, reproduction={"kind": "agent_assertion", "text": "reproduced"}))["admitted"] is True
       and AD22.defect_admission(dict(_v22_defect, reproduction={"kind": "agent_assertion", "text": "reproduced"}))["admitted"] is False)

# ---------------------------------------------------------------------------------------------
# AC3: quarantine, standing tickets, break-glass.
# ---------------------------------------------------------------------------------------------
_v22_q = {"digest": "sha256:q", "media_type": "application/zip", "declared_source": "customer", "trust_label": "untrusted", "size": 1024,
          "expansion_limit": 1 << 30, "executable_content": False, "secret_scan": "clean", "malware_scan": "clean", "prompt_injection_taint": "none",
          "scanner_identity": "clamav", "scanner_version": "1.4.1", "expansion": {"bytes": 4096, "files": 3, "depth": 1, "ratio": 4},
          "sandbox": {"network_default": "denied"}, "network_requests": [{"destination": "pypi.org", "method": "GET", "content_digest": "sha256:x", "byte_count": 10, "policy_decision": "allow"}]}
expect("VELDO-0022 AC3 quarantine/fields-and-bounds: a complete clean record passes; each missing field refuses by name; each expansion "
       "bound (1 GB, 10000 files, depth 10, ratio 100:1) accepts the bound and refuses one over it; a granted sandbox capability, a "
       "network default other than denied, and an allowlisted request missing a recorded field each refuse",
       AD22.quarantine_problems(_v22_q) == []
       and all(any("lacks %s" % f in p for p in AD22.quarantine_problems({k: v for k, v in _v22_q.items() if k != f})) for f in AD22.QUARANTINE_FIELDS)
       and all(AD22.quarantine_problems(dict(_v22_q, expansion=dict(_v22_q["expansion"], **{k: lim}))) == [] for k, lim in AD22.QUARANTINE_LIMITS.items())
       and all(any("exceeds" in p for p in AD22.quarantine_problems(dict(_v22_q, expansion=dict(_v22_q["expansion"], **{k: lim + 1})))) for k, lim in AD22.QUARANTINE_LIMITS.items())
       and AD22.QUARANTINE_LIMITS == {"bytes": 1 << 30, "files": 10000, "depth": 10, "ratio": 100}
       and all(any("grants %s" % d in p for p in AD22.quarantine_problems(dict(_v22_q, sandbox={d: True}))) for d in AD22.SANDBOX_DENIED)
       and any("not denied" in p for p in AD22.quarantine_problems(dict(_v22_q, sandbox={"network_default": "allow"})))
       and any("request lacks policy_decision" in p for p in AD22.quarantine_problems(dict(_v22_q, network_requests=[{"destination": "x"}]))))
expect("VELDO-0022 AC3 quarantine/unknown-scan: an unavailable, unknown, pending or errored malware or secret scan is a failure, never "
       "clean; a flagged scan refuses; a surviving injection taint refuses",
       all(any("never a clean result" in p for p in AD22.quarantine_problems(dict(_v22_q, malware_scan=v))) for v in ("unavailable", "unknown", None, "pending", "error", "flagged"))
       and any("never a clean result" in p for p in AD22.quarantine_problems(dict(_v22_q, secret_scan="unavailable")))
       and any("taint" in p for p in AD22.quarantine_problems(dict(_v22_q, prompt_injection_taint="suspected"))))
# THE DECLARED FALSIFIER: treat an unavailable malware inspection as clean.
_V22_M3 = _v22_mutated('''        if f in record and record.get(f) != "clean":
''', '''        if f in record and record.get(f) not in ("clean", "unavailable"):  # mutant: unavailable reads as clean
''')
expect("VELDO-0022 AC3 quarantine/unknown-scan DRIVEN (the declared falsifier): with an unavailable inspection read as clean in a copy, "
       "the record passes quarantine, so the row reds; unmutated it is refused",
       _V22_M3.quarantine_problems(dict(_v22_q, malware_scan="unavailable")) == []
       and AD22.quarantine_problems(dict(_v22_q, malware_scan="unavailable")) != [])
_V22_NOW = 1_900_000_000
_v22_ticket = {"cadence": "weekly", "start": _V22_NOW - 86400, "expiry": _V22_NOW + 86400 * 30, "eligible_paths_or_dependencies": ["deps/", "lock"],
               "permitted_version_movement": "minor", "prohibited_breaking_changes": True, "per_occurrence_budget": 5000, "concurrency": 1,
               "tests": ["unit"], "release_limits": "none", "signer": "dmitry"}
_v22_occ = {"id": "occ-2026-09-17", "budget": 4000, "paths": ["deps/"]}
expect("VELDO-0022 AC3 quarantine/standing-ticket: an in-force signed ticket with a fresh occurrence inside its bounds runs; a missing "
       "field, a machine signer, an expired ticket, a reused occurrence id, an over-budget occurrence and an ineligible path each "
       "refuse by name",
       AD22.standing_ticket_problems(_v22_ticket, _v22_occ, _V22_NOW) == []
       and any("lacks cadence" in p for p in AD22.standing_ticket_problems({k: v for k, v in _v22_ticket.items() if k != "cadence"}, _v22_occ, _V22_NOW))
       and any("authorized person" in p for p in AD22.standing_ticket_problems(dict(_v22_ticket, signer="agent"), _v22_occ, _V22_NOW))
       and any("not in force" in p for p in AD22.standing_ticket_problems(_v22_ticket, _v22_occ, _V22_NOW + 86400 * 60))
       and any("reused" in p for p in AD22.standing_ticket_problems(_v22_ticket, _v22_occ, _V22_NOW, prior_occurrences=["occ-2026-09-17"]))
       and any("exceeds the ticket's per-occurrence budget" in p for p in AD22.standing_ticket_problems(_v22_ticket, dict(_v22_occ, budget=6000), _V22_NOW))
       and any("outside the ticket's eligible" in p for p in AD22.standing_ticket_problems(_v22_ticket, dict(_v22_occ, paths=["src/"]), _V22_NOW)))
_v22_grant = {"responder": "asya", "policy_signer": "dmitry", "repositories": ["veldo"], "targets": ["credentials"], "actions": ["rotate_credential"],
              "duration_seconds": 7200, "blast_radius": "one credential", "granted_at": _V22_NOW - 600, "isolated": True, "canary_percent": 0,
              "reversible_action_qualified": True, "independent_deadline_enforcer": True}
expect("VELDO-0022 AC3 quarantine/break-glass: a bounded grant acts; a machine responder, an unlisted action, a forbidden authorization "
       "(permanent feature, API change), an elapsed duration, a ratification overdue past four hours, an overdue review, an "
       "unratified canary over five percent or not isolated, and a missing reversible action or independent deadline enforcer "
       "each refuse by name; the constants are the R68 numbers",
       AD22.break_glass_problems(_v22_grant, _V22_NOW) == []
       and any("not a named person" in p for p in AD22.break_glass_problems(dict(_v22_grant, responder="bot"), _V22_NOW))
       and any("not a permitted containment action" in p for p in AD22.break_glass_problems(dict(_v22_grant, actions=["deploy_feature"]), _V22_NOW))
       and any("cannot silently authorize permanent_feature" in p for p in AD22.break_glass_problems(dict(_v22_grant, permanent_feature=True), _V22_NOW))
       and any("duration has elapsed" in p for p in AD22.break_glass_problems(_v22_grant, _V22_NOW + 8000))
       and any("ratification" in p for p in AD22.break_glass_problems(dict(_v22_grant, duration_seconds=86400), _V22_NOW + 5 * 3600))
       and any("one business day" in p for p in AD22.break_glass_problems(dict(_v22_grant, duration_seconds=86400 * 3, review_due_at=_V22_NOW, ratified_by="asya"), _V22_NOW + 60))
       and any("5 percent canary" in p for p in AD22.break_glass_problems(dict(_v22_grant, canary_percent=6), _V22_NOW))
       and any("stays isolated" in p for p in AD22.break_glass_problems(dict(_v22_grant, isolated=False), _V22_NOW))
       and any("requests the security authority" in p for p in AD22.break_glass_problems(dict(_v22_grant, independent_deadline_enforcer=False), _V22_NOW))
       and (AD22.RATIFICATION_DUE_SECONDS, AD22.REVIEW_DUE_BUSINESS_DAYS, AD22.UNRATIFIED_CANARY_MAX_PERCENT) == (14400, 1, 5))

# ---------------------------------------------------------------------------------------------
# AC4: scope, readmission, admission debt.
# ---------------------------------------------------------------------------------------------
_v22_scope = {"paths": [".veldo/x.py"], "interfaces": ["cli"], "specifications": ["VELDO-0022"], "criteria": ["AC1", "AC2"], "data_classes": ["none"],
              "dependencies": [], "targets": ["repo"], "risk_tier": "high", "artifact_types": ["source"], "budget": 100.0, "work_class": "PRODUCT_CHANGE"}
expect("VELDO-0022 AC4 readmission/dimensions: the nine scope dimensions are machine-comparable and an unchanged scope stands; a missing "
       "dimension refuses comparison; a new protected path, an interface change, a migration, an unlisted dependency, a new target, "
       "increased risk, a changed criterion and a class change each invalidate by name; a security escalation grants only its "
       "bounded authority",
       len(AD22.SCOPE_DIMENSIONS) == 9 and AD22.scope_change_problems(_v22_scope, dict(_v22_scope)) == []
       and any("not machine-comparable" in p for p in AD22.scope_change_problems(_v22_scope, {k: v for k, v in _v22_scope.items() if k != "targets"}))
       and any("new protected path .veldo/policy.yaml" in p for p in AD22.scope_change_problems(_v22_scope, dict(_v22_scope, paths=[".veldo/x.py", ".veldo/policy.yaml"]), protected_paths=[".veldo/policy.yaml"]))
       and any("interface change" in p for p in AD22.scope_change_problems(_v22_scope, dict(_v22_scope, interfaces=["cli", "http"])))
       and any("migration appeared" in p for p in AD22.scope_change_problems(_v22_scope, dict(_v22_scope, migration=True)))
       and any("unlisted dependency langgraph" in p for p in AD22.scope_change_problems(_v22_scope, dict(_v22_scope, dependencies=["langgraph"])))
       and any("new target prod" in p for p in AD22.scope_change_problems(_v22_scope, dict(_v22_scope, targets=["repo", "prod"])))
       and any("risk increased" in p for p in AD22.scope_change_problems(_v22_scope, dict(_v22_scope, risk_tier="critical")))
       and any("changed criterion set" in p for p in AD22.scope_change_problems(_v22_scope, dict(_v22_scope, criteria=["AC1"])))
       and any("class changed" in p for p in AD22.scope_change_problems(_v22_scope, dict(_v22_scope, work_class="TECHNICAL_CHANGE")))
       and any("bounded emergency authority" in p for p in AD22.scope_change_problems(_v22_scope, dict(_v22_scope, work_class="SECURITY_EMERGENCY", security_escalation=True))))
expect("VELDO-0022 AC4 readmission/budget: a budget increase at twenty percent stands, above it invalidates, and a ten percent increase "
       "that exceeds the signed ceiling invalidates while one within the ceiling stands; invalidation moves units to "
       "AWAITING_AUTHORITY and the item to AWAITING_GROOMING with build and merge stopped",
       AD22.scope_change_problems(_v22_scope, dict(_v22_scope, budget=120.0)) == []
       and any("more than 20 percent" in p for p in AD22.scope_change_problems(_v22_scope, dict(_v22_scope, budget=120.5)))
       and any("exceeds the signed ceiling" in p for p in AD22.scope_change_problems(_v22_scope, dict(_v22_scope, budget=110.0), signed_ceiling=105.0))
       and AD22.scope_change_problems(_v22_scope, dict(_v22_scope, budget=110.0), signed_ceiling=115.0) == []
       and AD22.invalidation_effect(["x"]) == {"invalidated": True, "units": "AWAITING_AUTHORITY", "item": "AWAITING_GROOMING", "stopped": ("build", "merge"),
                                                "may_continue": ("authorized_containment", "observation", "reconciliation"), "reasons": ["x"]}
       and AD22.invalidation_effect([]) == {"invalidated": False})
# THE DECLARED FALSIFIER: permit a ten percent budget increase that exceeds the signed ceiling.
_V22_M4 = _v22_mutated('''        elif _is_num(signed_ceiling) and b1 > signed_ceiling:
''', '''        elif False:  # mutant: under 20 percent is free
''')
expect("VELDO-0022 AC4 readmission/signed-ceiling DRIVEN (the declared falsifier): with increases under twenty percent treated as free in a "
       "copy, a ten percent increase past the signed ceiling stands, so the row reds; unmutated it invalidates",
       _V22_M4.scope_change_problems(_v22_scope, dict(_v22_scope, budget=110.0), signed_ceiling=105.0) == []
       and AD22.scope_change_problems(_v22_scope, dict(_v22_scope, budget=110.0), signed_ceiling=105.0) != [])
_v22_items = [{"alias": "I1", "state": "RAW", "entered_day": 90}, {"alias": "I2", "state": "PREPARED", "entered_day": 92, "proposed_toe": 30},
              {"alias": "I3", "state": "PREPARED", "entered_day": 80}, {"alias": "I4", "state": "AWAITING_GROOMING", "entered_day": 85, "proposed_toe": 10},
              {"alias": "I5", "state": "ADMITTED", "entered_day": 70}, {"alias": "I6", "state": "PREPARED", "entered_day": 99, "proposed_toe": 5}]
_v22_debt = AD22.debt_report(_v22_items, 100)
expect("VELDO-0022 AC4 readmission/debt: the report counts RAW, PREPARED and AWAITING_GROOMING with oldest ages (7, 14 and 15 days at "
       "seven and fourteen-day thresholds), lists the prepared items older than seven days as debt with their known effort and the "
       "number of unknown estimates (never zero), raises an andon warning past fourteen days, and grants no authority",
       _v22_debt["counts"] == {"RAW": 1, "PREPARED": 3, "AWAITING_GROOMING": 1} and _v22_debt["oldest_age_days"] == {"RAW": 10, "PREPARED": 20, "AWAITING_GROOMING": 15}
       and _v22_debt["debt_items"] == ["I2", "I3"] and _v22_debt["debt_toe"]["known_total"] == 30 and _v22_debt["debt_toe"]["unknown_estimates"] == 1
       and _v22_debt["andon_warnings"] == ["I3"] and _v22_debt["grants_authority"] is False and _v22_debt["reprioritizes"] is False)
