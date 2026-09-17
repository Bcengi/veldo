#!/usr/bin/env python3
"""Section 2 admission semantics (PLAN-0019 W7, VELDO-0022).

WHAT THIS MODULE IS. Pure predicates over plain data, a contract organ beside entity_contract.py
and authority_contract.py: the seven governed work classes and the class-specific authority, lane,
request and priority each needs before execution (R07, R08, R09, AC1); the R66 predicates that let
a policy defect be admitted automatically, and where an item goes when they fail (AC2); the
quarantine, standing-maintenance and break-glass bounds that keep automatic admission attributable
and enforceable (R67, R68, AC3); and the machine-comparable scope whose material change invalidates
admission, with the admission-debt report that grants no authority and hides no unknown (R69,
AC4). Standard library only; it reads no live system, runs no scanner and writes nothing. The
Admission Service that applies these predicates, the quarantine execution environment and the
scanners are later packages; a scanner this module never ran is an unavailable inspection, which
is a failure, never a clean result.
"""
import math

SCHEMA = "veldo.admission_contract/v1"


def _is_str(v):
    return isinstance(v, str) and v.strip() != ""


def _is_pos_int(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 1


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


MACHINE_ACTORS = frozenset({"veldo-executor", "veldo-responder", "executor", "responder", "machine",
                            "agent", "bot", "ava", "automation", "service", "service_account", "service-account"})
PREPARATION_AGENT_KINDS = ("agent_run", "preparation_agent")

# ---------------------------------------------------------------------------------------------
# AC1: one governed work class per item, with its authority, lane, request and priority.
# ---------------------------------------------------------------------------------------------

WORK_CLASSES = ("PRODUCT_CHANGE", "POLICY_DEFECT", "SECURITY_EMERGENCY", "INCIDENT_CONTAINMENT",
                "STANDING_MAINTENANCE", "TECHNICAL_CHANGE", "COMPLIANCE_EXPIRY")
LANES = ("ordinary", "policy_qualified", "emergency")
# WHO ADMITS EACH CLASS (R08): the roles a PERSON must hold, or the signed policy kind an Admission
# Service may apply instead. A preparation agent admits nothing. Priority comes from the priority
# authority or the signed policy, never from the lane and never from automatic admission.
CLASS_POLICY = {
    "PRODUCT_CHANGE": {"lane": "ordinary", "person_roles": ("admission_authority",), "policy_kind": None, "priority_from": ("priority_authority",)},
    "TECHNICAL_CHANGE": {"lane": "ordinary", "person_roles": ("admission_authority",), "policy_kind": None, "priority_from": ("priority_authority",)},
    "POLICY_DEFECT": {"lane": "policy_qualified", "person_roles": ("admission_authority",), "policy_kind": "defect_policy", "priority_from": ("priority_authority", "signed_policy")},
    "SECURITY_EMERGENCY": {"lane": "emergency", "person_roles": ("security_authority",), "policy_kind": "break_glass", "priority_from": ("security_authority", "signed_policy")},
    "INCIDENT_CONTAINMENT": {"lane": "emergency", "person_roles": ("operations_authority",), "policy_kind": "standing_containment", "priority_from": ("operations_authority", "signed_policy")},
    "STANDING_MAINTENANCE": {"lane": "policy_qualified", "person_roles": (), "policy_kind": "standing_ticket", "priority_from": ("signed_policy",)},
    "COMPLIANCE_EXPIRY": {"lane": "ordinary", "person_roles": ("admission_authority",), "policy_kind": "standing_compliance", "priority_from": ("priority_authority", "signed_policy")},
}
QUARANTINED_CLASS = "QUARANTINED"


def classify(item):
    """(work_class or QUARANTINED, reason): every item has exactly one class from the R08
    enumeration before admission; an unknown class, no class, or several classes stays
    quarantined (R08: unknown or unresolved classifications remain quarantined)."""
    classes = item.get("work_class")
    if isinstance(classes, str):
        classes = [classes]
    classes = [c for c in (classes or []) if _is_str(c)]
    if len(classes) != 1:
        return QUARANTINED_CLASS, "an item has exactly one work class; got %d (%s)" % (len(classes), ", ".join(classes) or "none")
    if classes[0] not in WORK_CLASSES:
        return QUARANTINED_CLASS, "work class %r is not one of %s" % (classes[0], WORK_CLASSES)
    return classes[0], "classified"


def _person_with_role(actor, roles):
    return isinstance(actor, dict) and actor.get("kind") == "person" and _is_str(actor.get("principal")) \
        and actor["principal"].strip().lower() not in MACHINE_ACTORS and bool(set(actor.get("roles") or []) & set(roles))


def _signed_policy(policy, kind):
    return isinstance(policy, dict) and policy.get("kind") == kind and _is_str(policy.get("signer")) \
        and policy["signer"].strip().lower() not in MACHINE_ACTORS and _is_str(policy.get("digest")) \
        and _is_pos_int(policy.get("version")) and policy.get("expired") is not True


def admission_problems(item, request, admitter, policy=None, priority=None, context=None):
    """Why an item may NOT be admitted, by name (R07, R08, R09): no single class; no admission
    request or one whose revision is not signed (machine-prepared material is a draft until the
    authorized person or named policy identity signs the exact revision); an admitter that is not a
    person holding the class's role and no signed policy of the class's kind (a preparation agent
    admits nothing, whatever the class); a class whose lane does not match; a compliance class with
    no enrolled obligation and named authority in `context`; a production containment or
    deployment target with no admitted adapter in `context`; a priority that comes from neither the
    priority authority nor a signed policy (automatic admission grants no queue precedence)."""
    problems = []
    cls, why = classify(item)
    if cls == QUARANTINED_CLASS:
        return ["quarantined: %s" % why]
    pol = CLASS_POLICY[cls]
    context = context or {}
    if not isinstance(request, dict) or not _is_pos_int(request.get("revision")) or request.get("signed_revision") != request.get("revision") \
            or not _is_str(request.get("signed_by")) or request["signed_by"].strip().lower() in MACHINE_ACTORS:
        problems.append("the admission request's exact revision is not signed by an authorized person or named policy identity: "
                        "machine-prepared material is a draft (R09)")
    if isinstance(admitter, dict) and admitter.get("kind") in PREPARATION_AGENT_KINDS:
        problems.append("a preparation agent cannot admit %s (or anything): admission is an authorization ceremony (R12)" % cls)
    elif not (_person_with_role(admitter, pol["person_roles"]) or (pol["policy_kind"] and _signed_policy(policy, pol["policy_kind"]))):
        problems.append("%s needs a person holding %s or a signed %s policy; got admitter %r and policy %r"
                        % (cls, list(pol["person_roles"]) or "no role", pol["policy_kind"] or "no", (admitter or {}).get("principal"), (policy or {}).get("kind")))
    if item.get("lane") not in (None, pol["lane"]):
        problems.append("%s runs in the %s lane, not %r; no lane bypasses identity, scope, priority, evidence, quarantine or audit" % (cls, pol["lane"], item.get("lane")))
    if cls == "COMPLIANCE_EXPIRY" and not (context.get("enrolled_obligation") and _is_str(context.get("compliance_authority"))):
        problems.append("compliance work applies only when the enrolled repository has an actual obligation and a named authority; none is enrolled")
    if item.get("target_kind") in ("production_containment", "deployment") and not context.get("admitted_adapter"):
        problems.append("a %s target has no admitted target adapter: production containment and deployment actions stay unavailable" % item["target_kind"])
    if priority is not None:
        src = priority.get("source") if isinstance(priority, dict) else None
        if src not in pol["priority_from"]:
            problems.append("priority from %r is not one of %s for %s: automatic admission does not grant queue precedence" % (src, pol["priority_from"], cls))
    return problems


# ---------------------------------------------------------------------------------------------
# AC2: policy-qualified defects (R66).
# ---------------------------------------------------------------------------------------------

# THE R66 CLAUSE-TO-PREDICATE TABLE: each row is one clause, the field(s) it reads and the refusal.
DISQUALIFYING_CHANGES = ("accepted_contract", "accepted_criterion", "public_behavior", "public_interface", "data_model",
                         "dependency_policy", "protected_path_scope", "release_policy", "compatibility_target")
REPRODUCTION_FIELDS = ("baseline", "environment_digest", "steps", "expected_behavior", "actual_observations", "artifact_identities")
DEFECT_PREDICATES = (
    ("cited_accepted_revision", "R66", "a cited accepted specification revision"),
    ("named_failing_criterion", "R66", "the named criterion that fails"),
    ("supported_version", "R66", "an affected version still supported"),
    ("trusted_reproduction", "R66", "a trusted quarantined reproduction operation (never an agent's assertion)"),
    ("bounded_surface", "R66", "a bounded affected surface"),
    ("change_envelope", "R66", "a proposed change envelope"),
    ("not_duplicate", "R66", "no duplicate of an admitted item"),
    ("not_obsolete", "R66", "the behavior is not obsolete"),
    ("not_destructive", "R66", "the reproduction is not destructive"),
    ("not_production_data_dependent", "R66", "the reproduction needs no production data"),
    ("not_expected_behavior", "R66", "the observed behavior is not the accepted expected behavior"),
    ("single_repository", "R66", "the change stays inside one repository"),
    ("no_disqualifying_change", "R66", "no accepted contract, criterion, interface, data model, dependency policy, protected-path scope, release policy or compatibility target changes"),
)
SEVERITIES = ("low", "medium", "high", "critical")


def trusted_reproduction(rep):
    """A reproduction counts only when a TRUSTED quarantined operation recorded it (kind
    trusted_reproduction with an operator that is not a machine actor's bare assertion, a
    quarantine id) with every R66 field. An agent's statement that it reproduced is an assertion."""
    if not isinstance(rep, dict) or rep.get("kind") != "trusted_reproduction":
        return False
    if not _is_str(rep.get("quarantine_id")) or rep.get("violation_demonstrated") is not True:
        return False
    return all(rep.get(f) not in (None, "", [], {}) for f in REPRODUCTION_FIELDS)


def defect_admission(defect):
    """{admitted, refusals, routing, severity}: automatic POLICY_DEFECT admission (R66). Every
    predicate of DEFECT_PREDICATES must hold; each that fails is named. On failure the item is
    routed, never dropped and never lowered in severity: a disqualifying change routes to
    AWAITING_GROOMING under the class the change belongs to (PRODUCT_CHANGE or TECHNICAL_CHANGE), a
    security-relevant failure routes to security-emergency handling, and anything else to grooming.
    A cross-repository change is blocked as unsupported, never partially admitted."""
    refusals = []
    checks = {
        "cited_accepted_revision": _is_pos_int(defect.get("accepted_revision")) and _is_str(defect.get("specification")),
        "named_failing_criterion": _is_str(defect.get("failing_criterion")),
        "supported_version": defect.get("version_supported") is True,
        "trusted_reproduction": trusted_reproduction(defect.get("reproduction")),
        "bounded_surface": bool(defect.get("affected_surface")),
        "change_envelope": bool(defect.get("change_envelope")),
        "not_duplicate": defect.get("duplicate_of") in (None, ""),
        "not_obsolete": defect.get("obsolete") is not True,
        "not_destructive": defect.get("reproduction_destructive") is not True,
        "not_production_data_dependent": defect.get("needs_production_data") is not True,
        "not_expected_behavior": defect.get("is_expected_behavior") is not True,
        "single_repository": len(set(defect.get("repositories") or [defect.get("repository")])) == 1 and _is_str(defect.get("repository")),
        "no_disqualifying_change": not (set(defect.get("changes") or []) & set(DISQUALIFYING_CHANGES)),
    }
    for name, clause, text in DEFECT_PREDICATES:
        if not checks[name]:
            refusals.append("%s (%s): %s is required" % (name, clause, text))
    severity = defect.get("severity") if defect.get("severity") in SEVERITIES else "unknown"
    if not refusals:
        return {"admitted": True, "refusals": [], "routing": {"class": "POLICY_DEFECT", "state": "ADMITTED"}, "severity": severity}
    if "single_repository" in [r.split(" ")[0] for r in refusals]:
        routing = {"class": "POLICY_DEFECT", "state": "BLOCKED", "reason": "a defect needing several repositories is unsupported and never partially admitted"}
    elif "no_disqualifying_change" in [r.split(" ")[0] for r in refusals]:
        cls = "PRODUCT_CHANGE" if set(defect.get("changes") or []) & {"public_behavior", "public_interface", "accepted_contract", "accepted_criterion"} else "TECHNICAL_CHANGE"
        routing = {"class": cls, "state": "AWAITING_GROOMING", "reason": "the change alters an accepted contract, interface, model, policy or target"}
    elif severity == "critical" or defect.get("security_relevant") is True:
        routing = {"class": "SECURITY_EMERGENCY", "state": "AWAITING_GROOMING", "reason": "lack of clean reproduction never lowers severity; security handling"}
    else:
        routing = {"class": "POLICY_DEFECT", "state": "AWAITING_GROOMING", "reason": "lack of clean reproduction never lowers severity; grooming"}
    return {"admitted": False, "refusals": refusals, "routing": routing, "severity": severity}


# ---------------------------------------------------------------------------------------------
# AC3: quarantine, standing authorization, break-glass (R67, R68).
# ---------------------------------------------------------------------------------------------

QUARANTINE_FIELDS = ("digest", "media_type", "declared_source", "trust_label", "size", "expansion_limit", "executable_content",
                     "secret_scan", "malware_scan", "prompt_injection_taint", "scanner_identity", "scanner_version")
QUARANTINE_LIMITS = {"bytes": 1 << 30, "files": 10000, "depth": 10, "ratio": 100}
SCAN_RESULTS = ("clean", "flagged")  # anything else, unknown and unavailable included, is a failure
SANDBOX_DENIED = ("repository_writes", "credentials", "production_data", "deployment_access", "host_filesystem", "unrestricted_network")
STANDING_TICKET_FIELDS = ("cadence", "start", "expiry", "eligible_paths_or_dependencies", "permitted_version_movement",
                          "prohibited_breaking_changes", "per_occurrence_budget", "concurrency", "tests", "release_limits", "signer")
BREAK_GLASS_FIELDS = ("responder", "policy_signer", "repositories", "targets", "actions", "duration_seconds", "blast_radius")
BREAK_GLASS_ACTIONS = ("disable_feature", "revoke_credential", "rotate_credential", "block_traffic", "halt_release", "reversible_rollback", "isolate_target")
RATIFICATION_DUE_SECONDS = 4 * 3600
REVIEW_DUE_BUSINESS_DAYS = 1
UNRATIFIED_CANARY_MAX_PERCENT = 5


def quarantine_problems(record):
    """Why quarantined material may NOT feed automatic admission (R67): a missing field; a scan
    result that is not literally clean (unknown, unavailable, pending, an error or a flag are all
    failures, never clean); an archive over any expansion bound; executable content or an injection
    taint without the label carried; a sandbox declaration that grants anything in SANDBOX_DENIED;
    network not default-denied or an allowlisted request without its recorded fields."""
    problems = []
    if not isinstance(record, dict):
        return ["a quarantine record is a mapping"]
    for f in QUARANTINE_FIELDS:
        if f not in record:
            problems.append("quarantine record lacks %s" % f)
    for f in ("secret_scan", "malware_scan"):
        if f in record and record.get(f) != "clean":
            problems.append("%s is %r: an unknown or unavailable inspection is a failure for automatic admission, never a clean result" % (f, record.get(f)))
    if record.get("prompt_injection_taint") not in (None, False, "none"):
        problems.append("prompt-injection taint %r survives extraction and derivation; tainted material never authorizes instructions" % (record.get("prompt_injection_taint"),))
    exp = record.get("expansion") or {}
    for key, limit in QUARANTINE_LIMITS.items():
        v = exp.get(key)
        if v is not None and (not _is_num(v) or v > limit):
            problems.append("archive expansion %s %r exceeds the %r bound; an exception needs a signed authority decision that narrows the environment" % (key, v, limit))
    sandbox = record.get("sandbox") or {}
    for d in SANDBOX_DENIED:
        if sandbox.get(d) is True:
            problems.append("quarantine execution grants %s: refused (no repository writes, credentials, production data, deployment access, host filesystem or unrestricted network)" % d)
    if sandbox.get("network_default") not in (None, "denied"):
        problems.append("network default is %r, not denied" % (sandbox.get("network_default"),))
    for req in record.get("network_requests") or []:
        for f in ("destination", "method", "content_digest", "byte_count", "policy_decision"):
            if f not in (req or {}):
                problems.append("an allowlisted network request lacks %s" % f)
    return problems


def standing_ticket_problems(ticket, occurrence, now, prior_occurrences=()):
    """Why a standing-maintenance occurrence may NOT run under its ticket (R68): a missing ticket
    field; a machine signer; a ticket not yet started or expired at `now`; an occurrence without
    its own distinct identity (a repeated occurrence id is refused); a bound exceeded (budget,
    concurrency, an ineligible path), which returns the occurrence to grooming."""
    problems = []
    for f in STANDING_TICKET_FIELDS:
        if f not in (ticket or {}):
            problems.append("standing ticket lacks %s" % f)
    if problems:
        return problems
    if not _is_str(ticket["signer"]) or ticket["signer"].strip().lower() in MACHINE_ACTORS:
        problems.append("a standing ticket is deliberately authored and signed by an authorized person; %r is not one" % (ticket["signer"],))
    if not (_is_num(ticket["start"]) and _is_num(ticket["expiry"]) and ticket["start"] <= now < ticket["expiry"]):
        problems.append("the ticket is not in force at %r (start %r, expiry %r)" % (now, ticket["start"], ticket["expiry"]))
    if not _is_str((occurrence or {}).get("id")) or occurrence["id"] in set(prior_occurrences):
        problems.append("each occurrence has its own distinct identity and receipt chain; %r is missing or reused" % ((occurrence or {}).get("id"),))
    if _is_num((occurrence or {}).get("budget")) and occurrence["budget"] > ticket["per_occurrence_budget"]:
        problems.append("occurrence budget %r exceeds the ticket's per-occurrence budget %r: back to grooming" % (occurrence["budget"], ticket["per_occurrence_budget"]))
    outside = sorted(set((occurrence or {}).get("paths") or []) - set(ticket["eligible_paths_or_dependencies"] or []))
    if outside:
        problems.append("occurrence touches %s, outside the ticket's eligible paths or dependencies: back to grooming" % ", ".join(outside))
    return problems


def break_glass_problems(grant, now):
    """Why a break-glass grant may NOT act (R68): a missing field; a machine responder or signer;
    an action not explicitly listed or not in the permitted containment vocabulary; a duration
    beyond the grant; a ratification more than four hours overdue without the security authority's
    signature; an adversarial review overdue past one business day; an unratified patch beyond a
    five percent canary or not isolated; no qualified reversible action or independent deadline
    enforcer (Veldo stops and requests the security authority); a grant that tries to authorize a
    permanent feature, an API change, an irreversible migration, a new dependency or expanded
    collection."""
    problems = []
    for f in BREAK_GLASS_FIELDS:
        if f not in (grant or {}):
            problems.append("break-glass grant lacks %s" % f)
    if problems:
        return problems
    for who in ("responder", "policy_signer"):
        if not _is_str(grant[who]) or grant[who].strip().lower() in MACHINE_ACTORS:
            problems.append("%s %r is not a named person" % (who, grant[who]))
    for a in grant["actions"] or []:
        if a not in BREAK_GLASS_ACTIONS:
            problems.append("action %r is not a permitted containment action (%s)" % (a, ", ".join(BREAK_GLASS_ACTIONS)))
    for forbidden in ("permanent_feature", "public_api_change", "irreversible_migration", "new_dependency", "expanded_collection"):
        if grant.get(forbidden) is True:
            problems.append("break-glass cannot silently authorize %s" % forbidden)
    granted_at = grant.get("granted_at")
    if _is_num(granted_at) and _is_num(now):
        if now > granted_at + grant["duration_seconds"]:
            problems.append("the grant's duration has elapsed")
        if now > granted_at + RATIFICATION_DUE_SECONDS and not _is_str(grant.get("ratified_by")):
            problems.append("ratification by the security authority was due within %d hours and is absent" % (RATIFICATION_DUE_SECONDS // 3600))
        if grant.get("review_due_at") is not None and now > grant["review_due_at"] and grant.get("reviewed") is not True:
            problems.append("adversarial review and a decision or incident record were due within one business day and are absent")
    if not _is_str(grant.get("ratified_by")):
        pct = grant.get("canary_percent")
        if pct is not None and (not _is_num(pct) or pct > UNRATIFIED_CANARY_MAX_PERCENT):
            problems.append("an unratified patch cannot exceed a %d percent canary (got %r)" % (UNRATIFIED_CANARY_MAX_PERCENT, pct))
        if grant.get("isolated") is not True:
            problems.append("an unratified patch stays isolated from general distribution")
    if grant.get("reversible_action_qualified") is not True or grant.get("independent_deadline_enforcer") is not True:
        problems.append("without a qualified reversible action and an independent deadline enforcer Veldo stops and requests the security authority")
    return problems


# ---------------------------------------------------------------------------------------------
# AC4: scope, readmission and admission debt (R69).
# ---------------------------------------------------------------------------------------------

SCOPE_DIMENSIONS = ("paths", "interfaces", "specifications", "criteria", "data_classes", "dependencies", "targets", "risk_tier", "artifact_types")
BUDGET_FREE_INCREASE_RATIO = 0.20
RISK_ORDER = ("low", "standard", "high", "critical")
DEBT_AGE_DAYS = 7
ANDON_AGE_DAYS = 14
DEBT_STATES = ("RAW", "PREPARED", "AWAITING_GROOMING")


def scope_change_problems(admitted, current, protected_paths=(), signed_ceiling=None):
    """The material changes between an admitted scope and the current one, each by name (R69): a
    new protected path; a public-interface change; a migration; an unlisted dependency; a new
    target; increased risk; a changed criterion; a budget increase above twenty percent; a smaller
    increase that still exceeds the signed ceiling (the threshold is not free spending); a class
    change. Both scopes must be machine-comparable over every dimension. Empty iff admission stands."""
    problems = []
    for d in SCOPE_DIMENSIONS:
        if d not in (admitted or {}) or d not in (current or {}):
            problems.append("scope is not machine-comparable: dimension %s is missing" % d)
    if problems:
        return problems
    new_paths = set(current["paths"]) - set(admitted["paths"])
    for p in sorted(new_paths):
        if any(p == pp or (pp.endswith("*") and p.startswith(pp[:-1])) for pp in protected_paths):
            problems.append("new protected path %s" % p)
    if set(current["interfaces"]) != set(admitted["interfaces"]):
        problems.append("public interface change")
    if current.get("migration") and not admitted.get("migration"):
        problems.append("a migration appeared")
    for d in sorted(set(current["dependencies"]) - set(admitted["dependencies"])):
        problems.append("unlisted dependency %s" % d)
    for t in sorted(set(current["targets"]) - set(admitted["targets"])):
        problems.append("new target %s" % t)
    if current["risk_tier"] in RISK_ORDER and admitted["risk_tier"] in RISK_ORDER and RISK_ORDER.index(current["risk_tier"]) > RISK_ORDER.index(admitted["risk_tier"]):
        problems.append("risk increased from %s to %s" % (admitted["risk_tier"], current["risk_tier"]))
    if set(current["criteria"]) != set(admitted["criteria"]):
        problems.append("changed criterion set")
    if current.get("work_class") and admitted.get("work_class") and current["work_class"] != admitted["work_class"]:
        if current["work_class"] == "SECURITY_EMERGENCY" and current.get("security_escalation") is True:
            problems.append("security escalation grants only its bounded emergency authority (R68); the original admission does not carry over")
        else:
            problems.append("class changed from %s to %s" % (admitted["work_class"], current["work_class"]))
    b0, b1 = admitted.get("budget"), current.get("budget")
    if _is_num(b0) and _is_num(b1) and b1 > b0:
        if b1 > b0 * (1 + BUDGET_FREE_INCREASE_RATIO):
            problems.append("budget increased by more than 20 percent (%r to %r)" % (b0, b1))
        elif _is_num(signed_ceiling) and b1 > signed_ceiling:
            problems.append("budget %r exceeds the signed ceiling %r: the 20 percent threshold is not free spending permission" % (b1, signed_ceiling))
    return problems


def invalidation_effect(problems):
    """What a material scope change does (R69): units to AWAITING_AUTHORITY, the item to
    AWAITING_GROOMING, build and merge stop, only containment, observation and reconciliation may
    continue. Empty problems leave everything as it was."""
    if not problems:
        return {"invalidated": False}
    return {"invalidated": True, "units": "AWAITING_AUTHORITY", "item": "AWAITING_GROOMING",
            "stopped": ("build", "merge"), "may_continue": ("authorized_containment", "observation", "reconciliation"), "reasons": list(problems)}


def debt_report(items, now_day):
    """The admission-debt report (R69): per state in DEBT_STATES the count and the oldest age in
    days; admission debt as the prepared items older than seven days with their total proposed
    Tokens of Effort, unknown estimates counted as unknown (never zero) and their number reported;
    an andon warning for debt older than fourteen days. The report grants no authority and
    reprioritizes nothing: it is numbers about waiting work."""
    counts = {s: 0 for s in DEBT_STATES}
    oldest = {s: None for s in DEBT_STATES}
    debt, debt_toe, unknown_estimates, andon = [], 0, 0, []
    for it in items or []:
        st = it.get("state")
        if st not in DEBT_STATES:
            continue
        counts[st] += 1
        age = now_day - it.get("entered_day", now_day) if _is_num(it.get("entered_day")) else None
        if age is not None and (oldest[st] is None or age > oldest[st]):
            oldest[st] = age
        if st == "PREPARED" and age is not None and age > DEBT_AGE_DAYS:
            debt.append(it.get("alias") or it.get("uuid"))
            toe = it.get("proposed_toe")
            if _is_num(toe):
                debt_toe += toe
            else:
                unknown_estimates += 1
            if age > ANDON_AGE_DAYS:
                andon.append(it.get("alias") or it.get("uuid"))
    return {"counts": counts, "oldest_age_days": oldest, "debt_items": debt,
            "debt_toe": {"known_total": debt_toe, "unknown_estimates": unknown_estimates,
                         "note": "unknown estimates are reported as unknown, never as zero"},
            "andon_warnings": andon, "grants_authority": False, "reprioritizes": False}
