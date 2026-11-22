#!/usr/bin/env python3
"""The REFERENCE-WIRED live provisioner for a COMPANY-MANAGED Jira Cloud project (WARP-0614 F3).

Extracted from tracker_jira_init.py so the bootstrap orchestrator stays inside its module_lines
budget and the reference-wired live edge is a cleanly separated sibling (the reviewer flagged the
split). This module carries ONLY the live integration: the exact Jira Cloud REST v3 calls that were
PROVEN LIVE against the real board during the VEL activation. It invents no API shapes; every call
mirrors a working activation script:

  statuses      POST /rest/api/3/statuses, scope GLOBAL (company-managed lifecycle statuses are
                global), the category mapped onto Jira's TODO | IN_PROGRESS | DONE; existing global
                statuses are read from the paginated GET /rest/api/3/statuses/search.
  workflow      the modern BULK workflow edit: read via POST /rest/api/3/workflows {workflowIds},
                VALIDATE via POST /rest/api/3/workflows/update/validation with the WRAPPER
                {payload, validationOptions}, APPLY via POST /rest/api/3/workflows/update with the
                BARE payload. Every status carries a generated UUID statusReference mapped to its
                real numeric id; EXISTING statuses are KEPT (nothing removed) so an active workflow
                needs no status migration; every transition (even a new one) carries an id.
  fence         a transition condition {operation: ALL, conditionGroups: [] (MANDATORY, an absent
                one is a 400), conditions: [{ruleKey: "system:restrict-issue-transition",
                parameters: {groupIds: <approver-group-UUID>}}]}; groups are addressed by UUID.
  groups        POST /rest/api/3/group (create), GET /rest/api/3/groups/picker (resolve name to
                UUID), GET /rest/api/3/group/member?groupId= (membership read), POST/DELETE
                /rest/api/3/group/user?groupId= (membership write).
  issue types   GET /rest/api/3/issuetype (the instance catalog), attach an instance type to the
                project's scheme via PUT /rest/api/3/issuetypescheme/{schemeId}/issuetype (never a
                wrong-type fallback: a type the instance lacks fails loud).

WHY A FACTORY, NOT A MODULE-LEVEL CLASS. The provisioner MUST subclass the SAME JiraCloudAdapter
object the orchestrator already holds, so it reuses that adapter's auth, _request, and epic/child
upsert, and so an issubclass check against the orchestrator's alias holds. The codebase loads each
sibling module by spec_from_file_location, which mints a DISTINCT class object per load; a class
defined here against a locally loaded adapter would be a different identity. So this module exposes
make_company_managed_provisioner(base_cls, bootstrap_error): the orchestrator passes IN its own
JiraCloudAdapter and BootstrapError, and the returned class subclasses exactly that base and raises
exactly that error. One load world, one identity, no drift. The methods live on a module-level MIXIN
(not nested in the factory), so each stays a short, ordinary def.

WHY THIS MODULE SHIPPED UNRUNNABLE, AND WHAT NOW CHECKS IT (WARP-0623). Every method here was written
from REST shapes a working script had proven, the module was synced, and the gate was green - and the
whole provisioning path still raised TypeError on every call, in every configuration. The adapter
CONSTRUCTOR sets an instance attribute self._project (the configured project KEY) and this module defined
a METHOD _project; an instance attribute shadows a class method permanently, so the method was unreachable
on every instance ('str' object is not callable with a project configured, 'NoneType' object is not
callable without one). The offline suite could not see it BY CONSTRUCTION: the FakeTracker defines its OWN
_project method and is constructed WITHOUT a project key, so no number of fixtures over the fake would
ever reach the collision. The lesson, for whoever next writes a fake that mirrors the real object's
private names: CODIFIED FROM A PROVEN SCRIPT IS NOT THE SAME AS THE CODIFIED PATH RAN. The method is now
named _project_record, and shadowed_provisioner_methods / check_provisioner_composition below close the
whole class of defect - they intersect the constructor's attribute names with the mixin's method names ON
THE COMPOSED CLASS and refuse by name (SHADOWED_PROVISIONER_METHOD), at composition time and again per
instance. They find NAME collisions, not every way a live path can be unreachable: a wrong endpoint, a
wrong payload or a missing credential scope are found only by EXECUTING this module, which is WARP-0620.

NEVER RUN IN THE GATE. Like the reference JiraCloudAdapter and the WARP-0612 provisioner, these live
methods need a real Jira and a scoped admin token; the gate exercises the FakeTracker path only. The
bootstrap LOGIC (detection, idempotency, fence composition, the mirror drive) is what the gate proves
over the deterministic FakeTracker; this class is the real integration point, verified in a separate
live run. GENERIC: no company, board, or site value is hardcoded here (api.atlassian.com in the auth
mode lives in tracker_mirror_runner.py; this module speaks only relative REST v3 paths).
"""
import json
import uuid


# The vendor-neutral status categories (tracker_jira_init.STATUS_CATEGORIES) mapped onto Jira Cloud's
# status category keys: the one vendor coupling, declared once.
_JIRA_STATUS_CATEGORY = {"To Do": "TODO", "In Progress": "IN_PROGRESS", "Done": "DONE"}

# The PROVEN GET /rest/api/3/statuses/search endpoint returns statusCategory as the string enum
# (TODO | IN_PROGRESS | DONE) the workflow apply expects, so no mapping is needed on that path. This
# only defends the case where an endpoint returns the CLASSIC dict shape whose `key` is one of
# new | indeterminate | done: those legacy keys map onto the modern enum here (never passed through
# raw, which would inject a WRONG statusCategory into the workflow payload).
_CLASSIC_CATEGORY_KEY = {"new": "TODO", "indeterminate": "IN_PROGRESS", "done": "DONE"}

# A generic description recorded on a newly created global status. Generic on purpose: no company or
# board name (this module ships in the open-source engine).
_STATUS_DESCRIPTION = "lifecycle status provisioned by the VELDO board bootstrap"


def _uq(s):
    """URL-quote a path/query segment, nothing safe."""
    import urllib.parse
    return urllib.parse.quote(str(s), safe="")


class _CompanyManagedProvisionerOps:
    """The live provisioning + fence primitives, as a mixin composed onto a JiraCloudAdapter base by
    make_company_managed_provisioner. Split out as a mixin so each method is a short, module-level def
    (never nested in a factory closure); the factory combines it with the caller's base so self._request,
    self._email, and the epic/child upsert all come from that ONE adapter identity. Methods raise
    self._BE (the injected BootstrapError). Reference-wired against Jira Cloud REST v3; NEVER run in the
    gate. Every REST shape below is the one PROVEN LIVE by the VEL activation scripts (cited per method)."""

    # The load-identity-INDEPENDENT marker that identifies this mixin (and any layer over it) inside a
    # composition, for the WARP-0623 shadow check below. It cannot be an issubclass test against this
    # module's own class object: the codebase loads each sibling by spec_from_file_location, which mints a
    # DISTINCT class per load, so a check run from one load over a class built by another would recognize
    # NOTHING and report clean - the worst possible failure for a check whose job is to refuse.
    _PROVISIONER_OPS = True

    # --- project reads ------------------------------------------------------
    def _project_record(self, project_key):
        """The Jira project RESOURCE (GET /rest/api/3/project/{key}); its numeric id is cached for the
        status/scheme/workflow scopes. Reference-wired; not run in the gate.

        NAMED _project_record, never _project (WARP-0623): the adapter CONSTRUCTOR sets an instance
        attribute self._project (the configured project KEY), and an instance attribute shadows a class
        method permanently, so a method of that name is unreachable on every instance. The check
        shadowed_provisioner_methods below refuses that collision by name for the whole class."""
        return self._request("GET", "/rest/api/3/project/%s" % project_key)

    def _project_type(self, project_key):
        """company-managed | team-managed, from the project's style/simplified fields. Jira reports a
        team-managed (next-gen) project as style 'next-gen' or simplified true, and a company-managed
        (classic) project otherwise. The VEL board is company-managed (classic, simplified false)."""
        proj = self._project_record(project_key)
        self._project_id_cache[project_key] = proj.get("id")
        style = (proj.get("style") or "").lower()
        if proj.get("simplified") or style == "next-gen":
            return "team-managed"
        return "company-managed"

    def _project_id(self, project_key):
        if project_key not in self._project_id_cache:
            self._project_id_cache[project_key] = self._project_record(project_key).get("id")
        return self._project_id_cache[project_key]

    # --- issue-type provisioning (attach the instance type to the project's SCHEME) -----------------
    def _list_instance_issue_types(self):
        """Every issue type the Jira INSTANCE holds (GET /rest/api/3/issuetype), the catalog a project
        can attach a type FROM (PROVEN: vel_issuetypes.py). Read-only; not run in the gate."""
        return self._request("GET", "/rest/api/3/issuetype") or []

    def _issue_type_scheme_id(self, project_key):
        """The id of the project's ISSUE TYPE SCHEME (GET /rest/api/3/issuetypescheme/project?projectId=),
        the write target for attaching a type. Fails loud by name when none resolves. Read-only."""
        data = self._request("GET", "/rest/api/3/issuetypescheme/project?projectId=%s"
                             % self._project_id(project_key))
        for v in ((data or {}).get("values") or []):
            scheme = v.get("issueTypeScheme") or {}
            if scheme.get("id"):
                return scheme["id"]
        raise self._BE("no issue type scheme resolved for project %r (cannot add an issue type)"
                       % project_key)

    def _existing_issue_types(self, project_key):
        """The issue-type NAMES already on the project's scheme: GET the scheme's id-mapping
        (GET /rest/api/3/issuetypescheme/mapping?issueTypeSchemeId=) then resolve those ids to names
        against the instance catalog (PROVEN: vel_issuetypes.py verify). Read-only; not run in the gate."""
        scheme_id = self._issue_type_scheme_id(project_key)
        mapping = self._request("GET", "/rest/api/3/issuetypescheme/mapping?issueTypeSchemeId=%s"
                                % scheme_id) or {}
        ids = {m.get("issueTypeId") for m in (mapping.get("values") or []) if m.get("issueTypeId")}
        return {it["name"] for it in self._list_instance_issue_types()
                if it.get("id") in ids and it.get("name")}

    def _provision_issue_type(self, project_key, name):
        """Ensure an issue type is on the project's scheme: reuse it if the scheme already has it, else
        attach the INSTANCE type of that name to the scheme (PUT /rest/api/3/issuetypescheme/{schemeId}/
        issuetype with the type id, PROVEN: vel_issuetypes.py). Idempotent by name (present returns
        created=False). FAILS LOUD by name when the instance holds no such type, never a wrong-type
        fallback. NOTE: creating a brand-new standard type (e.g. a Decision type, POST /rest/api/3/
        issuetype {type: standard, hierarchyLevel: 0}) is a documented admin one-off, out of the
        bootstrap's scope, see docs/tracker-operator-guide.md; the bootstrap only ATTACHES existing
        types (so Epic, which cannot be created, is reused). Reference-wired; not run in the gate."""
        instance = self._list_instance_issue_types()
        match = next((it for it in instance if it.get("name") == name), None)
        if name in self._existing_issue_types(project_key):
            return (match.get("id") if match else None), False
        if match is None:
            raise self._BE(
                "the Jira instance has no issue type named %r, so it cannot be added to project %r; add "
                "the issue type to the instance first (the bootstrap never falls back to a wrong type, "
                "e.g. it will not map a plan onto a Sub-task). Creating a new standard type is a "
                "documented admin one-off, see docs/tracker-operator-guide.md." % (name, project_key))
        scheme_id = self._issue_type_scheme_id(project_key)
        self._request("PUT", "/rest/api/3/issuetypescheme/%s/issuetype" % scheme_id,
                      {"issueTypeIds": [match["id"]]})
        return match.get("id"), True

    # --- status provisioning (company-managed statuses are GLOBAL) ----------------------------------
    def _global_statuses(self):
        """Every GLOBAL status by name -> {id, statusCategory}, paginated from GET /rest/api/3/statuses/
        search (PROVEN: vel_activate_1_statuses_groups.py). Company-managed lifecycle statuses are GLOBAL,
        so this is the create-or-reuse source of truth for _provision_status and the id/category source
        for wiring. Read-only; not run in the gate."""
        out = {}
        start = 0
        while True:
            page = self._request("GET", "/rest/api/3/statuses/search?maxResults=200&startAt=%d" % start) or {}
            values = page.get("values") or []
            for v in values:
                if v.get("name"):
                    cat = v.get("statusCategory")
                    if isinstance(cat, dict):
                        cat = _CLASSIC_CATEGORY_KEY.get(cat.get("key"))
                    out[v["name"]] = {"id": v.get("id"), "statusCategory": cat}
            if page.get("isLast", True) or not values:
                break
            start += len(values)
        return out

    def _existing_status_names(self, project_key):
        """The status names already reachable in the project (union across issue types), read from
        GET /rest/api/3/project/{key}/statuses. This is the set the fence's all-or-nothing terminal-
        transition existence check (require_transitions_exist) reads. Read-only; not run in the gate."""
        data = self._request("GET", "/rest/api/3/project/%s/statuses" % project_key)
        names = set()
        for issue_type in (data or []):
            for st in (issue_type.get("statuses") or []):
                if st.get("name"):
                    names.add(st["name"])
        return names

    def _workflow_status_names(self, project_key, issue_type):
        """The status names reachable in one issue type's workflow (GET /rest/api/3/project/{key}/
        statuses filtered to the issue type). Read-only; not run in the gate."""
        data = self._request("GET", "/rest/api/3/project/%s/statuses" % project_key)
        names = set()
        for it in (data or []):
            if it.get("name") == issue_type:
                for st in (it.get("statuses") or []):
                    if st.get("name"):
                        names.add(st["name"])
        return names

    def _provision_status(self, project_key, name, category):
        """Create a GLOBAL status by name if absent, else reuse (PROVEN: POST /rest/api/3/statuses with
        scope GLOBAL, vel_activate_1_statuses_groups.py). The vendor-neutral category maps onto Jira's
        TODO | IN_PROGRESS | DONE. Idempotent by name: an existing global status returns (id, False), a
        new one (id, True). project_key is unused (the status is global) but kept for the seam signature.
        Reference-wired; not run in the gate."""
        existing = self._global_statuses()
        if name in existing:
            return existing[name]["id"], False
        made = self._request("POST", "/rest/api/3/statuses",
                             {"scope": {"type": "GLOBAL"},
                              "statuses": [{"name": name, "statusCategory": _JIRA_STATUS_CATEGORY[category],
                                            "description": _STATUS_DESCRIPTION}]})
        created = made if isinstance(made, list) else []
        new_id = next((s.get("id") for s in created if s.get("name") == name), None)
        return new_id, True

    # --- workflow bulk edit (the modern workflows/update API) ---------------------------------------
    def _workflow_id(self, project_key):
        """Resolve the project's workflow id for the bulk edit, cached. The project's workflow scheme
        (GET /rest/api/3/workflowscheme/project?projectId=) names its default workflow; that NAME is
        resolved to the workflow id via the SAME bulk endpoint the read/edit uses (POST /rest/api/3/
        workflows with {workflowNames}). The live VEL run confirmed the workflow read/update shapes;
        this id resolution uses the standard scheme + bulk-read endpoints (the one step to re-confirm
        per instance, since the scripts had the id pre-discovered). Reference-wired; not run in the gate."""
        if project_key in self._workflow_id_cache:
            return self._workflow_id_cache[project_key]
        pid = self._project_id(project_key)
        scheme = self._request("GET", "/rest/api/3/workflowscheme/project?projectId=%s" % pid) or {}
        values = scheme.get("values") or []
        ws = (values[0].get("workflowScheme") if values else {}) or {}
        # ONLY the resolved default-workflow name is a valid workflow-NAME lookup key. There is no
        # name fallback: ws.get("name") is the workflow-SCHEME name, which is not a workflow name and
        # would resolve to zero workflows, so an unresolved default fails closed below by name.
        name = ws.get("defaultWorkflow")
        found = self._request("POST", "/rest/api/3/workflows", {"workflowNames": [name]}) if name else {}
        ids = [w.get("id") for w in ((found or {}).get("workflows") or []) if w.get("id")]
        if not ids:
            raise self._BE("could not resolve the workflow id for project %r" % project_key)
        self._workflow_id_cache[project_key] = ids[0]
        return ids[0]

    def _read_workflow(self, project_key):
        """Read the project's workflow via the modern bulk endpoint (PROVEN: POST /rest/api/3/workflows
        {workflowIds}, vel_wf_compose4.py / vel_wf_apply.py). Returns the full response: top-level
        statuses plus workflows[0] carrying its version, statuses, and transitions. Not run in the gate."""
        wf_id = self._workflow_id(project_key)
        return self._request("POST", "/rest/api/3/workflows", {"workflowIds": [wf_id]}) or {}

    @staticmethod
    def _norm_transition(t):
        """Normalize a transition read back from the workflow into the exact shape the apply accepts
        (PROVEN: vel_wf_compose4.py), LOSSLESSLY. id (required even for a new transition), type, name,
        actions, and validators are always emitted; EVERY OTHER field the read carries is echoed back
        UNCHANGED when present - toStatusReference, conditions, links, properties, triggers, and the
        legacy `from`. The round-trip must be byte-faithful because a company-managed workflow's
        default transitions are DIRECTED and carry their source routing in
        links: [{fromStatusReference, fromPort, toPort}] (e.g. the default Done/Reopen). Dropping
        links (or properties/triggers/from) on a DIRECTED transition yields a malformed transition on
        re-apply, so the bulk workflow-update fails closed on the first live wire of a fresh board.
        Only NEW statuses/transitions are ever ADDED by the callers; existing transitions survive
        this normalize round-trip intact (resolves review Finding #1)."""
        out = {"id": t["id"], "type": t.get("type", "GLOBAL"), "name": t.get("name"),
               "actions": t.get("actions") or [], "validators": t.get("validators") or []}
        for key in ("toStatusReference", "conditions", "links", "properties", "triggers", "from"):
            if key in t:
                out[key] = t[key]
        return out

    def _compose_bare_payload(self, full):
        """Rebuild the BARE workflow-update request from a bulk read, KEEPING every existing status and
        transition (PROVEN: vel_wf_compose4.py keeps existing statuses so an active workflow needs no
        migration). statusReference stays the UUID the read carries and the workflow version is passed
        back verbatim. The caller mutates this payload (adds a status, or adds a fence condition) before
        _validate_and_apply."""
        wf = (full.get("workflows") or [{}])[0]
        statuses = [{"statusReference": s["statusReference"], "id": s.get("id"),
                     "name": s.get("name"), "statusCategory": s.get("statusCategory")}
                    for s in (full.get("statuses") or []) if s.get("statusReference")]
        wf_statuses = [{"statusReference": s["statusReference"],
                        "layout": s.get("layout") or {"x": 0.0, "y": 0.0}}
                       for s in (wf.get("statuses") or []) if s.get("statusReference")]
        transitions = [self._norm_transition(t) for t in (wf.get("transitions") or []) if t.get("id")]
        return {"statuses": statuses,
                "workflows": [{"id": wf.get("id"), "version": wf.get("version"),
                               "statuses": wf_statuses, "transitions": transitions}]}

    def _validate_and_apply(self, payload):
        """VALIDATE then APPLY a workflow-update payload (PROVEN: vel_wf_apply.py). Validation takes the
        WRAPPER {payload, validationOptions}; a hard ERROR fails loud by name. The apply takes the BARE
        payload. Reference-wired; not run in the gate."""
        val = self._request("POST", "/rest/api/3/workflows/update/validation",
                            {"payload": payload,
                             "validationOptions": {"levels": ["ERROR", "WARNING"]}}) or {}
        errors = [e for e in (val.get("errors") or [])
                  if isinstance(e, dict) and e.get("level") == "ERROR"]
        if errors:
            raise self._BE("Jira refused the workflow update: %s"
                           % "; ".join(e.get("message", "") for e in errors[:5]))
        self._request("POST", "/rest/api/3/workflows/update", payload)

    def _wire_status_into_workflow(self, project_key, issue_type, name):
        """Add a status to the project's workflow if absent, else no-op (idempotent by name). Uses the
        PROVEN bulk edit: read, KEEP every existing status, ADD this one with a generated UUID
        statusReference mapped to its real global numeric id, add a GLOBAL transition (with an id) so the
        status is reachable, then validate (wrapped) and apply (bare). Company-managed shares one workflow
        across issue types, so wiring the same status for a second issue type is a no-op. Reference-wired;
        not run in the gate."""
        payload = self._compose_bare_payload(self._read_workflow(project_key))
        present = {s["name"] for s in payload["statuses"] if s.get("name")}
        if name in present:
            return False
        gstat = self._global_statuses()
        if name not in gstat:
            raise self._BE("status %r is not a global status; provision it before wiring it into the "
                           "workflow" % name)
        ref = str(uuid.uuid4())
        payload["statuses"].append({"statusReference": ref, "id": gstat[name]["id"],
                                    "name": name, "statusCategory": gstat[name]["statusCategory"]})
        wf = payload["workflows"][0]
        n = len(wf["statuses"])
        wf["statuses"].append({"statusReference": ref,
                               "layout": {"x": float(200 + (n % 5) * 240), "y": float(80 + (n // 5) * 170)}})
        ids = [int(t["id"]) for t in wf["transitions"] if str(t.get("id", "")).isdigit()]
        wf["transitions"].append({"id": str((max(ids) if ids else 100) + 1), "type": "GLOBAL",
                                  "name": "To %s" % name, "toStatusReference": ref,
                                  "actions": [], "validators": []})
        self._validate_and_apply(payload)
        return True

    # --- fence primitives (WARP-0614): groups + a terminal-transition restriction -------------------
    def _fence_admin(self):
        """This IS the admin provisioner (the admin token in the two-credential model); the live gate on
        the fence writes is the credential's own group/workflow-admin scopes."""
        return True

    def _group_id(self, name):
        """Resolve a group NAME to its UUID via GET /rest/api/3/groups/picker (PROVEN: the fallback
        resolver in vel_activate_1_statuses_groups.py). Groups are addressed by UUID everywhere else.
        None when no group of that exact name matches. Read-only; not run in the gate."""
        res = self._request("GET", "/rest/api/3/groups/picker?query=%s" % _uq(name)) or {}
        return next((g.get("groupId") for g in (res.get("groups") or []) if g.get("name") == name), None)

    def _group_name(self, group_id):
        """Resolve a group UUID back to its NAME via GET /rest/api/3/group/bulk?groupId=, so the seam's
        transition_restriction reports the group in the config's name-space. None when unresolved."""
        res = self._request("GET", "/rest/api/3/group/bulk?groupId=%s" % _uq(group_id)) or {}
        return next((g.get("name") for g in (res.get("values") or []) if g.get("groupId") == group_id), None)

    def _ensure_group(self, name):
        """Create the group if absent, else reuse, idempotent (PROVEN: POST /rest/api/3/group {name}
        returns its groupId, vel_activate_1_statuses_groups.py). Existence is checked first via the
        picker so an already-present group is a clean no-op (create returns False) rather than a 4xx.
        Reference-wired; not run in the gate."""
        if self._group_id(name) is not None:
            return False
        self._request("POST", "/rest/api/3/group", {"name": name})
        return True

    def _group_has_member(self, account_id, group):
        """Whether an account is in a group, read via GET /rest/api/3/group/member?groupId= (PROVEN:
        vel_activate_1_statuses_groups.py). Addresses the group by UUID. Read-only; not run in the gate."""
        gid = self._group_id(group)
        if gid is None:
            return False
        res = self._request("GET", "/rest/api/3/group/member?groupId=%s" % _uq(gid)) or {}
        return any(m.get("accountId") == account_id for m in (res.get("values") or []))

    def _set_group_membership(self, account_id, group, member):
        """Add (member True) or remove (member False) an account from a group, idempotent by target
        membership. PROVEN add: POST /rest/api/3/group/user?groupId= {accountId} (vel_activate_1_
        statuses_groups.py); the remove is the standard inverse DELETE /rest/api/3/group/user?groupId=&
        accountId=. Addresses the group by UUID. Reference-wired; not run in the gate."""
        if self._group_has_member(account_id, group) == bool(member):
            return False
        gid = self._group_id(group)
        if gid is None:
            raise self._BE("no group %r resolved for a membership change" % group)
        if member:
            self._request("POST", "/rest/api/3/group/user?groupId=%s" % _uq(gid), {"accountId": account_id})
        else:
            self._request("DELETE", "/rest/api/3/group/user?groupId=%s&accountId=%s"
                          % (_uq(gid), _uq(account_id)))
        return True

    @staticmethod
    def _fence_condition(group_id):
        """The PROVEN fence condition (vel_wf_compose4.py): restrict who may fire a transition to a
        group. conditionGroups MUST be [] (an absent conditionGroups is a 400); the rule is
        system:restrict-issue-transition, parameterized by the approver group's UUID."""
        return {"operation": "ALL", "conditionGroups": [],
                "conditions": [{"ruleKey": "system:restrict-issue-transition",
                                "parameters": {"groupIds": group_id}}]}

    @staticmethod
    def _has_fence(transition, group_id):
        """True when a transition already carries the restrict-issue-transition condition scoped to this
        group UUID (the idempotency check for _restrict_transition)."""
        conds = ((transition.get("conditions") or {}).get("conditions")) or []
        return any(c.get("ruleKey") == "system:restrict-issue-transition"
                   and group_id in json.dumps(c.get("parameters") or {}) for c in conds)

    def _restrict_transition(self, project_key, transition, approver_group):
        """Restrict every workflow transition that LANDS on the terminal status named `transition` to the
        approver group, so the fenced agent cannot fire it. Idempotent: already-restricted is a no-op
        (returns False). Uses the PROVEN bulk edit: resolve the approver group NAME to its UUID, read the
        workflow, add the fence condition to each transition whose toStatusReference is the terminal
        status, then validate (wrapped) and apply (bare). A terminal status the workflow lacks fails loud
        by name. Reference-wired; not run in the gate."""
        gid = self._group_id(approver_group)
        if gid is None:
            raise self._BE("no group %r resolved to restrict the transition to %r"
                           % (approver_group, transition))
        payload = self._compose_bare_payload(self._read_workflow(project_key))
        target_ref = next((s["statusReference"] for s in payload["statuses"]
                           if s.get("name") == transition), None)
        if target_ref is None:
            raise self._BE("no terminal status %r in project %r's workflow to restrict a transition to"
                           % (transition, project_key))
        changed = False
        for t in payload["workflows"][0]["transitions"]:
            if t.get("toStatusReference") == target_ref and not self._has_fence(t, gid):
                t["conditions"] = self._fence_condition(gid)
                changed = True
        if not changed:
            return False
        self._validate_and_apply(payload)
        return True

    def _transition_restriction(self, project_key, transition):
        """The approver group NAME a terminal transition is restricted to, or None. Reads the workflow,
        finds a transition landing on the terminal status, and resolves the restrict-issue-transition
        group UUID back to its name (the seam reports in the config's name-space). Not run in the gate."""
        payload = self._compose_bare_payload(self._read_workflow(project_key))
        target_ref = next((s["statusReference"] for s in payload["statuses"]
                           if s.get("name") == transition), None)
        if target_ref is None:
            return None
        for t in payload["workflows"][0]["transitions"]:
            if t.get("toStatusReference") == target_ref:
                for c in ((t.get("conditions") or {}).get("conditions") or []):
                    if c.get("ruleKey") == "system:restrict-issue-transition":
                        gid = (c.get("parameters") or {}).get("groupIds")
                        return self._group_name(gid) if gid else None
        return None


# --- the composition check (WARP-0623): no instance attribute may shadow a provisioning method --------
# An instance attribute shadows a class method PERMANENTLY (attribute lookup reads the instance dict
# first), so a method whose name a constructor also assigns to self is unreachable on every instance and
# every call raises TypeError. That is exactly how the codified provisioner shipped unrunnable: the adapter
# constructor sets self._project (the configured project KEY) and this mixin defined a method _project.
# The offline suite could not see it, because the FakeTracker defines its OWN _project method and is
# constructed WITHOUT a project key, so the collision was structurally unreachable in the gate. The check
# below closes the CLASS, not the instance: it enumerates both sides FROM THE COMPOSITION at runtime and
# refuses by name on any intersection, so a future constructor field or a future mixin method that collides
# is caught without anyone remembering to look.

# The check's single failure class, named in the refusal message so it is greppable from the output alone.
SHADOWED_PROVISIONER_METHOD = "SHADOWED_PROVISIONER_METHOD"


class ProvisionerCompositionError(TypeError):
    """SHADOWED_PROVISIONER_METHOD: a composed live provisioner carries at least one provisioning METHOD
    that an INSTANCE ATTRIBUTE set by one of its constructors permanently shadows, so calling that method
    raises TypeError on every instance in every configuration. A TypeError subclass because it is the
    static form of exactly the TypeError the composition would raise later, at the worst moment (mid-run,
    against a live board). Raised at COMPOSITION time, naming the class, the attribute and the method."""


def _mro(cls):
    """The class's method-resolution order, tolerating a non-class argument (returns just it)."""
    return list(getattr(cls, "__mro__", None) or [cls])


def _is_provisioner_ops(klass):
    """Whether a class in a composition belongs to the provisioning mixin lineage, decided by the mixin's
    own MARKER rather than by an issubclass test, so it holds across the module's multiple load identities
    (see _PROVISIONER_OPS on the mixin)."""
    return isinstance(klass, type) and getattr(klass, "_PROVISIONER_OPS", False) is True


def _methods_defined_by(klass):
    """The METHOD names one class defines in its OWN body: plain functions, staticmethods and classmethods
    alike. Dunders are excluded (never called as provisioning primitives, and __init__ is the other side of
    this check), and so are nested classes, which are types rather than methods."""
    out = set()
    for name, value in vars(klass).items():
        if name.startswith("__"):
            continue
        target = getattr(value, "__func__", value)
        if callable(target) and not isinstance(target, type):
            out.add(name)
    return out


def provisioner_method_names(cls):
    """Every METHOD name the live provisioning mixin contributes to a composed class, enumerated FROM THE
    COMPOSITION: every class in the MRO carrying the mixin's marker (the mixin itself, the composed
    provisioner, and any per-provider layer over it). Never a literal list of today's names, so a method
    added tomorrow is covered with no edit here."""
    names = set()
    for klass in _mro(cls):
        if _is_provisioner_ops(klass):
            names |= _methods_defined_by(klass)
    return names


def _loads_local(instruction, name):
    """Whether this instruction loads the local variable `name` (any LOAD_FAST family member, including the
    fused forms whose argval is a tuple of locals, so the scan holds across interpreter versions)."""
    if instruction is None or not instruction.opname.startswith("LOAD_FAST"):
        return False
    arg = instruction.argval
    return arg == name or (isinstance(arg, tuple) and bool(arg) and arg[-1] == name)


def _self_attributes_assigned(func):
    """The attribute names a function assigns onto its OWN first parameter (self), read from its COMPILED
    CODE: every STORE_ATTR whose target was just loaded from that first local. Bytecode rather than source
    text, so it needs no file on disk and holds for a module loaded by any loader; it needs no instance, no
    credential and no network."""
    import dis  # lazy, introspection-only: read the constructor's own bytecode
    code = getattr(func, "__code__", None)
    if code is None or code.co_argcount < 1:
        return set()
    me = code.co_varnames[0]
    names, prev = set(), None
    for ins in dis.get_instructions(code):
        if ins.opname == "STORE_ATTR" and _loads_local(prev, me):
            names.add(ins.argval)
        prev = ins
    return names


def _attributes_set_by(klass):
    """The instance-attribute names ONE class's own __init__ assigns to self (empty when it defines none)."""
    init = vars(klass).get("__init__") if isinstance(klass, type) else None
    return _self_attributes_assigned(getattr(init, "__func__", init)) if init is not None else set()


def constructor_attribute_names(cls, instance=None):
    """Every INSTANCE ATTRIBUTE name the composition's constructors set on self: read from EVERY __init__
    along the MRO (a BASE adapter's constructor counts, which is exactly where this defect came from),
    plus, when the caller hands in an already CONSTRUCTED instance, the names actually present in its
    __dict__ - so an attribute set outside an __init__ literal (a setattr, a helper) is not a blind spot."""
    names = set()
    for klass in _mro(cls):
        names |= _attributes_set_by(klass)
    if instance is not None:
        names |= set(vars(instance))
    return names


def _method_defined_in(cls, name):
    """The provisioning mixin class that defines this method, for a diagnosable refusal."""
    return next((k.__name__ for k in _mro(cls)
                 if _is_provisioner_ops(k) and name in _methods_defined_by(k)), None)


def _attribute_set_in(cls, name):
    """The class whose own __init__ sets this instance attribute, for a diagnosable refusal."""
    return next((k.__name__ for k in _mro(cls) if name in _attributes_set_by(k)), None)


def shadowed_provisioner_methods(cls, instance=None):
    """THE STRUCTURAL CHECK. Every name that is BOTH an instance attribute a constructor sets and a method
    the live provisioning mixin defines, as a sorted list of findings
    {error, class, attribute, attribute_set_by, method, method_defined_by}. Each such name is a
    provisioning method that CANNOT be called on any instance of this composition. Both sides are
    enumerated from the class at runtime, so the check is GENERIC over the composition rather than a
    hardcoded pair, and it is decidable entirely offline (no board, no credential, no network)."""
    methods = provisioner_method_names(cls)
    attributes = constructor_attribute_names(cls, instance=instance)
    findings = []
    for name in sorted(methods & attributes):
        findings.append({"error": SHADOWED_PROVISIONER_METHOD,
                         "class": getattr(cls, "__name__", str(cls)),
                         "attribute": name,
                         "attribute_set_by": _attribute_set_in(cls, name) or "(the constructed instance)",
                         "method": name,
                         "method_defined_by": _method_defined_in(cls, name)})
    return findings


def check_provisioner_composition(cls, instance=None):
    """REFUSE BY NAME when any provisioning method is shadowed; return cls when the composition is clean.
    Called at composition time (the factory below) and again per instance (the provisioner's __init__ with
    the constructed instance), so neither a static-only nor a runtime-only blind spot is left.

    It also refuses a composition in which it recognizes NO provisioning mixin at all: a check that
    inspected nothing would report clean, which is the one outcome this check exists to make impossible."""
    if not any(_is_provisioner_ops(k) for k in _mro(cls)):
        raise ProvisionerCompositionError(
            "%s: the composition %r carries no provisioning mixin this check recognizes (no class in its "
            "MRO marks _PROVISIONER_OPS), so the check would be vacuous - it refuses rather than report a "
            "composition it never inspected as clean"
            % (SHADOWED_PROVISIONER_METHOD, getattr(cls, "__name__", str(cls))))
    findings = shadowed_provisioner_methods(cls, instance=instance)
    if findings:
        raise ProvisionerCompositionError("%s: %s" % (SHADOWED_PROVISIONER_METHOD, "; ".join(
            "%s sets the instance attribute %r (in %s.__init__), which permanently shadows the "
            "provisioning method %s defined by %s, so every call to it raises TypeError"
            % (f["class"], f["attribute"], f["attribute_set_by"], f["method"], f["method_defined_by"])
            for f in findings)))
    return cls


def unreachable_provisioner_methods(instance):
    """The RUNTIME half, and the WARP-0623 reproduction: the provisioning method names that are NOT callable
    on a CONSTRUCTED instance. Empty is the reachability the codified path needs; a non-empty result is this
    defect OBSERVED rather than inferred (before the fix it returned ['_project'] on every instance)."""
    out = []
    for name in sorted(provisioner_method_names(type(instance))):
        if not callable(getattr(instance, name, None)):
            out.append(name)
    return out


def make_company_managed_provisioner(base_cls, bootstrap_error):
    """Build the live JiraCompanyManagedProvisioner class over the caller's JiraCloudAdapter base and
    BootstrapError, so it shares ONE module identity with the orchestrator (see the module docstring):
    the returned class subclasses exactly base_cls and raises exactly bootstrap_error. The caller
    instantiates it via build_live_provisioner. Reference-wired; the class is never run in the gate.

    The composed class is CHECKED before it is handed back (WARP-0623): a provisioning method that one of
    the constructors shadows with an instance attribute is refused by name here, at import time, rather
    than raising TypeError later against a live board."""

    class JiraCompanyManagedProvisioner(_CompanyManagedProvisionerOps, base_cls):
        """REFERENCE-WIRED live provisioner for a COMPANY-MANAGED Jira Cloud project (must be wired per
        org; needs a live Jira and a scoped admin token; NEVER run in the gate). Extends the reference
        JiraCloudAdapter (inheriting its stdlib-urllib _request, Basic auth, token-from-secret-reference,
        and the epic/child upsert + set_status the mirror drives) with the WARP-0612 provisioning
        primitives and the WARP-0614 fence edges, all against Jira Cloud REST v3 with the shapes proven
        live during the VEL activation (see the module docstring). Company-managed is required for the
        full status + workflow REST API; a team-managed project's workflow wiring is UI-only, so
        detection refuses it before any write."""

        _BE = bootstrap_error

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._project_id_cache = {}
            self._workflow_id_cache = {}
            # The composition check again over the CONSTRUCTED instance (WARP-0623): the class-level pass
            # below reads the constructors statically, this one reads what the instance actually carries,
            # so an attribute set outside an __init__ literal cannot hide a shadowed provisioning method.
            check_provisioner_composition(type(self), instance=self)

    return check_provisioner_composition(JiraCompanyManagedProvisioner)


# --- THE LIVE CHANGELOG FETCH (WARP-0625, W10 of PLAN-0016) ----------------------------------
# The other half of GAP 2. WARP-0625 built the shape translation; this is the read that feeds it.
#
# IT TAKES THE REQUEST CALLABLE RATHER THAN MAKING ONE, which is what makes it testable: the gate
# drives it with a canned payload and exercises the paging, the accumulation and the failure
# handling for real, and only the socket itself goes unexercised. An earlier draft of this item
# declined to write the fetch at all on the grounds that it could not be tested, and that was
# wrong - what could not be tested was a fetch that owned its own transport.
#
# PAGING IS NOT OPTIONAL. Jira returns the changelog in pages of 100 and a decision issue with a
# long history will silently truncate without this loop. A truncated changelog does not error, it
# just quietly loses the earliest transitions - which are exactly the ones the opening-actor
# derivation reads.
CHANGELOG_PAGE = 100
CHANGELOG_MAX_PAGES = 200          # a stop so a malformed isLast cannot spin forever


def fetch_changelog(request, issue_key, page_size=CHANGELOG_PAGE, normalize=None):
    """Every changelog entry for one issue, flattened and ordered, through the caller's `request`.

    `request(method, path)` is the adapter's own authenticated call. `normalize` defaults to the
    ONE normalizer in tracker_adapter - passed in only so a test can prove the fetch hands it the
    accumulated pages rather than one page.

    Returns the flat ordered records. Raises nothing for an empty history; a missing issue is the
    caller's `request` raising, because deciding what a 404 means is the adapter's job and not
    this function's."""
    if normalize is None:
        import importlib.util
        from pathlib import Path as _P
        _s = importlib.util.spec_from_file_location(
            "veldo_tracker_adapter_fetch", _P(__file__).resolve().parent / "tracker_adapter.py")
        _m = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_m)
        normalize = _m.normalize_changelog
    values, start = [], 0
    for _ in range(CHANGELOG_MAX_PAGES):
        page = request("GET", "/rest/api/3/issue/%s/changelog?startAt=%d&maxResults=%d"
                       % (issue_key, start, page_size)) or {}
        got = page.get("values") or []
        values.extend(got)
        # STOP ON THE SERVER'S OWN ANSWER FIRST, then on an empty page as the backstop. Trusting
        # only isLast hangs on a malformed response; trusting only emptiness makes one extra call
        # on every read.
        if page.get("isLast") is True or not got:
            break
        start += len(got)
    return normalize({"values": values})
