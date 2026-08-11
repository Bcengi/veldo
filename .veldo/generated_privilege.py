#!/usr/bin/env python3
"""Least privilege on generated infrastructure (WARP-1307, W7 of PLAN-0013).

Infrastructure a machine writes is held to least privilege at the gate. Wildcard permissions,
over-broad roles and public-exposure defaults refuse, each with the rule named.

**WHY GENERATED INFRASTRUCTURE SPECIFICALLY.** Every one of these violations exists in the training
data in enormous quantity, because `"Action": "*"` and `0.0.0.0/0` are what tutorials use - they
make the example work without explaining IAM. An agent reproducing the most common shape of a thing
will reproduce exactly the shape that got a thousand blog posts past their authors' patience. It is
not a reasoning failure and arguing with the model about it does not scale. Checking the artifact
does.

**EACH VIOLATION CLASS REFUSES WITH ITS OWN NAME AND THE NARROWER ALTERNATIVE.** "Least privilege
violation" sends somebody to read source at the moment they are least able to. "`Action: *` on
`s3:*` - name the four verbs you actually call" is a refusal they can act on without leaving the
message.

**PROPORTIONATE, STDLIB, WITH A PER-STACK SLOT.** This is a reference check over parsed structures,
not a policy engine. A real per-stack analyser plugs in behind `Analyzer`; the shipped one covers
the classes that actually recur. Reaching for a full IAM simulator here would be the wrong trade -
the check that runs on every change beats the check that is correct and unwired.

**IT READS PARSED DATA, NEVER TEXT.** A regex over HCL or YAML matches a wildcard in a comment and
misses one built by string concatenation. The caller parses; this decides.
"""

SCHEMA = "veldo.generated_privilege/v1"

WILDCARD_ACTION = "wildcard_action"
WILDCARD_RESOURCE = "wildcard_resource"
WILDCARD_PRINCIPAL = "wildcard_principal"
PUBLIC_INGRESS = "public_ingress"
PUBLIC_STORAGE = "public_storage"
ADMIN_ROLE = "over_broad_role"
NO_EXPIRY = "long_lived_credential"

# Roles that grant more than any generated artifact should ask for. Named, not pattern-matched, so
# adding one is a decision rather than a regex that quietly widens.
BROAD_ROLES = frozenset({
    "*", "admin", "administrator", "owner", "editor", "roles/owner", "roles/editor",
    "AdministratorAccess", "PowerUserAccess", "cluster-admin",
})

OPEN_CIDRS = frozenset({"0.0.0.0/0", "::/0"})

# The narrower thing to do instead, per rule. A refusal that does not say this is a refusal somebody
# works around rather than fixes.
INSTEAD = {
    WILDCARD_ACTION: "name the specific verbs this component calls; there are usually three or four",
    WILDCARD_RESOURCE: "scope to the exact resource arn or path this component touches",
    WILDCARD_PRINCIPAL: "name the role or service account that assumes this, never everyone",
    PUBLIC_INGRESS: "restrict to the load balancer's range, a VPC cidr, or a named security group",
    PUBLIC_STORAGE: "keep it private and front it with a signed url or a cdn origin identity",
    ADMIN_ROLE: "bind the narrowest predefined role that covers the calls, or write a custom one",
    NO_EXPIRY: "set an expiry; a credential with none is one nobody will ever rotate",
}


class Analyzer:
    """The per-stack slot. A real analyser for Terraform, CloudFormation or Kubernetes plugs in
    here; `check` runs the shipped reference rules and then whatever this adds."""

    def extra(self, artifact):                          # pragma: no cover - interface
        return []


def _is_wild(v):
    return v == "*" or (isinstance(v, str) and v.endswith(":*"))


def _as_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def check_statement(stmt, where):
    """One IAM-shaped statement: action, resource, principal."""
    out = []
    for act in _as_list(stmt.get("action") or stmt.get("Action")):
        if _is_wild(act):
            out.append((WILDCARD_ACTION, where, "action %r grants every verb" % act))
    for res in _as_list(stmt.get("resource") or stmt.get("Resource")):
        if _is_wild(res):
            out.append((WILDCARD_RESOURCE, where, "resource %r grants every object" % res))
    princ = stmt.get("principal") or stmt.get("Principal")
    for p in (_as_list(princ) if not isinstance(princ, dict) else
              [v for vs in princ.values() for v in _as_list(vs)]):
        if _is_wild(p):
            out.append((WILDCARD_PRINCIPAL, where, "principal %r is everyone, including anonymous"
                        % p))
    return out


def check(artifact, analyzer=None):
    """Every least-privilege problem in one PARSED generated artifact.

    Returns (rule, where, detail). Reads structure, never text: a regex over HCL matches a wildcard
    in a comment and misses one built by concatenation."""
    out = []
    a = artifact or {}

    for i, stmt in enumerate(_as_list(a.get("statements") or a.get("Statement"))):
        if isinstance(stmt, dict):
            out.extend(check_statement(stmt, "statement[%d]" % i))

    for name, role in sorted((a.get("roles") or {}).items()):
        if str(role) in BROAD_ROLES:
            out.append((ADMIN_ROLE, name, "role %r grants far more than a generated component "
                                          "should hold" % role))

    for name, rule in sorted((a.get("ingress") or {}).items()):
        src = rule.get("cidr") if isinstance(rule, dict) else rule
        if src in OPEN_CIDRS:
            out.append((PUBLIC_INGRESS, name, "ingress from %s is the whole internet" % src))

    for name, bucket in sorted((a.get("storage") or {}).items()):
        b = bucket if isinstance(bucket, dict) else {}
        if b.get("public") is True or b.get("acl") in ("public-read", "public-read-write"):
            out.append((PUBLIC_STORAGE, name, "storage is publicly readable by default"))

    for name, cred in sorted((a.get("credentials") or {}).items()):
        c = cred if isinstance(cred, dict) else {}
        if not c.get("expires_at") and not c.get("ttl"):
            out.append((NO_EXPIRY, name, "credential has neither an expiry nor a ttl"))

    if analyzer is not None:
        out.extend(analyzer.extra(a))
    return out


def report(problems):
    """One line per problem, each naming the NARROWER THING TO DO. A refusal without the
    alternative is one somebody routes around instead of fixing."""
    if not problems:
        return ["generated privilege: no problems"]
    lines = ["generated privilege: %d problem(s)" % len(problems)]
    for rule, where, detail in problems:
        lines.append("  %-20s %s: %s" % (rule, where, detail))
        if rule in INSTEAD:
            lines.append("      instead: %s" % INSTEAD[rule])
    return lines
