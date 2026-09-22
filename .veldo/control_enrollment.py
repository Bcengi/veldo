#!/usr/bin/env python3
"""Repository enrollment and authority routing (PLAN-0019 W14, VELDO-0029, R20, R26, R53).

WHAT THIS MODULE IS. The ONLY answer to "which authority does this clone write to". A clone is
enrolled by a signed binding that names the repository, the coordination domain, the store, the host
and the authority generation. Resolution takes the workspace as an EXPLICIT argument and reads the
binding that workspace carries. Nothing here consults the process's current directory, an
environment variable, or the importing module's own location.

WHY THAT SENTENCE IS THE WHOLE POINT. The store this repository shipped picks its database by running
`git rev-parse --git-common-dir` in whatever directory the process happens to be in, or by reading
VELDO_CONTROL_DB. Under that rule the repository a command mutates is decided by where the caller was
standing, and a command that names repository A can commit into repository B while every signature on
it verifies. R20 forbids exactly that: one authority per enrolled repository, reached through explicit
coordinates.

WHAT IDENTITY MEANS HERE, and why a path is not one. The binding records two things about the
repository that a swapped directory cannot carry over: its ROOT COMMIT, which a different repository
does not share, and a per-clone UUID written into the clone's own git common directory at enrollment,
which a fresh clone of the same repository does not have. A directory replaced at the same path fails
one of those two, so it is refused and must reenroll (R26). The absolute path is recorded for
diagnosis and is never an input to the decision.

WHAT IT IS NOT. It holds no key material: signing and verification are callables the caller supplies,
as they are in control_store. It opens no database, starts no service and speaks no protocol; it says
WHICH store, and refuses by name when it cannot. The local IPC client, the SSH relay and the
authority-unavailable behaviour are separate work. Standard library only.
"""

# Load the shared Git boundary by sibling path, including when imported by file location.
import importlib.util as _git_importlib
from pathlib import Path as _GitPath
_git_spec = _git_importlib.spec_from_file_location("veldo_git_process", _GitPath(__file__).resolve().with_name("git_process.py"))
_git_process = _git_importlib.module_from_spec(_git_spec)
_git_spec.loader.exec_module(_git_process)
import hashlib
import json
import os
import subprocess
import uuid

BINDING_SCHEMA = "veldo.enrollment/v1"
BINDING_RELATIVE = os.path.join("veldo", "control", "enrollment.json")
CLONE_UUID_RELATIVE = os.path.join("veldo", "control", "clone_uuid")
DB_RELATIVE = os.path.join("veldo", "control", "control.sqlite3")

# The fields the signature covers. Order is fixed: the signed bytes are a canonical encoding, so a
# field added later changes the encoding and old signatures stop verifying, which is the intent.
BINDING_FIELDS = ("schema", "repository_uuid", "repository_root_commit", "clone_uuid", "domain_uuid", "store_uuid",
                  "store_path", "host_identity", "authority_generation", "enrolled_at", "enrolled_by")

REFUSALS = ("not_enrolled", "malformed_binding", "signature_invalid", "repository_identity_mismatch",
            "clone_replaced", "host_binding_stale", "generation_behind", "cross_domain",
            "store_uuid_mismatch", "not_a_repository")


class EnrollmentRefused(Exception):
    """Refused, with a reason from REFUSALS. Every refusal names the reason and the coordinates it
    judged, because "routing failed" is the one message that cannot be acted on."""

    def __init__(self, reason, message, coordinates=None):
        super().__init__("%s: %s" % (reason, message))
        assert reason in REFUSALS, reason
        self.reason = reason
        self.message = message
        self.coordinates = dict(coordinates or {})


# ---------------------------------------------------------------------------------------------
# Explicit coordinates. Every git call below names its workspace with -C.
# ---------------------------------------------------------------------------------------------

def _git(workspace, *args):
    r = _git_process.run(["git", "-C", str(workspace), *args], capture_output=True, text=True,
                       timeout=60)
    if r.returncode != 0:
        raise EnrollmentRefused("not_a_repository",
                                "git %s failed in %s: %s" % (" ".join(args), workspace, r.stderr.strip()[:200]),
                                {"workspace": str(workspace)})
    return r.stdout.strip()


def git_common_dir(workspace):
    """The git common directory of THIS workspace, shared by its worktrees. Absolute, resolved.

    Named with -C, so a linked worktree resolves to the same common directory as its main clone and
    two different clones never resolve to one another whatever the caller's current directory is."""
    out = _git(workspace, "rev-parse", "--git-common-dir")
    return os.path.realpath(os.path.join(os.path.abspath(str(workspace)), out) if not os.path.isabs(out) else out)


def root_commits(workspace):
    """Every root commit reachable from HEAD, oldest first. A repository's root commits are the one
    piece of its identity that a different repository cannot share and a copy cannot shed."""
    out = _git(workspace, "rev-list", "--max-parents=0", "HEAD")
    return sorted(line.strip() for line in out.splitlines() if line.strip())


def binding_path(workspace):
    return os.path.join(git_common_dir(workspace), BINDING_RELATIVE)


def clone_uuid_path(workspace):
    return os.path.join(git_common_dir(workspace), CLONE_UUID_RELATIVE)


def store_path_for(binding):
    """Where the authority lives, as the BINDING records it. Not derived from the caller."""
    return binding["store_path"]


def workspace_identity(workspace):
    """What this workspace IS, read from the workspace itself: its common directory, its root
    commits, and the clone UUID it carries if it has been enrolled."""
    common = git_common_dir(workspace)
    up = os.path.join(common, CLONE_UUID_RELATIVE)
    clone = None
    try:
        with open(up) as fh:
            clone = fh.read().strip() or None
    except OSError:
        clone = None
    return {"git_common_dir": common, "root_commits": root_commits(workspace), "clone_uuid": clone}


# ---------------------------------------------------------------------------------------------
# The binding
# ---------------------------------------------------------------------------------------------

def canonical_bytes(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def binding_signed_bytes(binding):
    return canonical_bytes({k: binding.get(k) for k in BINDING_FIELDS})


def binding_digest(binding):
    return "sha256:" + hashlib.sha256(binding_signed_bytes(binding)).hexdigest()


def binding_problems(binding):
    """Why this record is not a binding at all, before anything is verified or compared."""
    problems = []
    if not isinstance(binding, dict):
        return ["the binding is not a mapping"]
    if binding.get("schema") != BINDING_SCHEMA:
        problems.append("schema must be %s (got %r)" % (BINDING_SCHEMA, binding.get("schema")))
    for field in BINDING_FIELDS:
        if field == "schema":
            continue
        v = binding.get(field)
        if v is None or (isinstance(v, str) and not v.strip()):
            problems.append("missing or empty required field: %s" % field)
    gen = binding.get("authority_generation")
    if gen is not None and (isinstance(gen, bool) or not isinstance(gen, int) or gen < 1):
        problems.append("authority_generation must be an integer >= 1: a generation is fencing, not a label")
    roots = binding.get("repository_root_commit")
    if roots is not None and not isinstance(roots, list):
        problems.append("repository_root_commit must be a list of commit ids")
    if not binding.get("signature"):
        problems.append("missing or empty required field: signature")
    return problems


def enroll(workspace, domain_uuid, store_uuid, store_path, host_identity, authority_generation,
           sign, enrolled_by, now, repository_uuid=None):
    """Write the signed binding into THIS workspace's git common directory and stamp its clone UUID.

    The clone UUID is generated here and written beside the binding. It is not tracked by git and a
    fresh clone of the same repository does not have it, which is what makes a replaced directory at
    the same path detectable (R26)."""
    common = git_common_dir(workspace)
    ident = workspace_identity(workspace)
    repo_uuid = repository_uuid or str(uuid.uuid4())
    clone = str(uuid.uuid4())
    binding = {
        "clone_uuid": clone,
        "schema": BINDING_SCHEMA,
        "repository_uuid": repo_uuid,
        "repository_root_commit": ident["root_commits"],
        "domain_uuid": domain_uuid,
        "store_uuid": store_uuid,
        "store_path": os.path.realpath(os.path.abspath(store_path)),
        "host_identity": host_identity,
        "authority_generation": authority_generation,
        "enrolled_at": now,
        "enrolled_by": enrolled_by,
    }
    binding["signature"] = sign(binding_signed_bytes(binding))
    binding["binding_digest"] = binding_digest(binding)
    os.makedirs(os.path.dirname(os.path.join(common, BINDING_RELATIVE)), exist_ok=True)
    with open(os.path.join(common, CLONE_UUID_RELATIVE), "w") as fh:
        fh.write(clone + "\n")
    with open(os.path.join(common, BINDING_RELATIVE), "w") as fh:
        json.dump(dict(binding, clone_uuid=clone), fh, indent=2, sort_keys=True)
        fh.write("\n")
    return dict(binding, clone_uuid=clone)


def read_binding(workspace):
    """The binding this workspace carries, or None. Unreadable is None; MALFORMED is not, because a
    binding that exists and cannot be parsed must never look like a clone that was never enrolled."""
    p = binding_path(workspace)
    try:
        with open(p) as fh:
            text = fh.read()
    except OSError:
        return None
    try:
        return json.loads(text)
    except ValueError as e:
        raise EnrollmentRefused("malformed_binding", "%s is not readable JSON: %s" % (p, e),
                                {"workspace": str(workspace), "binding_path": p})


def verify_binding(workspace, binding, verify, host_identity, domain_uuid=None, store_uuid=None,
                   minimum_generation=None):
    """Every reason this workspace may NOT use this binding, as a list, checked independently so a
    caller sees all of them rather than the first."""
    problems = []
    for text in binding_problems(binding):
        problems.append(("malformed_binding", text))
    if problems:
        return problems
    if not verify(binding_signed_bytes(binding), binding["signature"]):
        problems.append(("signature_invalid",
                         "the binding's signature does not verify over its own fields"))
    ident = workspace_identity(workspace)
    if sorted(binding["repository_root_commit"]) != sorted(ident["root_commits"]):
        problems.append(("repository_identity_mismatch",
                         "the binding names root commit(s) %s and this workspace has %s: the directory "
                         "holds a different repository than the one that was enrolled"
                         % (", ".join(c[:12] for c in binding["repository_root_commit"]) or "none",
                            ", ".join(c[:12] for c in ident["root_commits"]) or "none")))
    recorded_clone = binding.get("clone_uuid")
    if not ident["clone_uuid"]:
        problems.append(("clone_replaced",
                         "this workspace carries no clone uuid: the directory was replaced after "
                         "enrollment and must be enrolled again before it may mutate"))
    elif ident["clone_uuid"] != recorded_clone:
        problems.append(("clone_replaced",
                         "this workspace's clone uuid is not the one the binding was written for"))
    if binding["host_identity"] != host_identity:
        problems.append(("host_binding_stale",
                         "the binding was written for host %r and this is host %r: a host change is a "
                         "controlled migration, never an implicit rebind"
                         % (binding["host_identity"], host_identity)))
    if domain_uuid is not None and binding["domain_uuid"] != domain_uuid:
        problems.append(("cross_domain",
                         "the binding is in domain %s and the request names %s: cross-domain work is "
                         "unsupported" % (binding["domain_uuid"], domain_uuid)))
    if store_uuid is not None and binding["store_uuid"] != store_uuid:
        problems.append(("store_uuid_mismatch",
                         "the binding names store %s and the request names %s"
                         % (binding["store_uuid"], store_uuid)))
    if minimum_generation is not None and binding["authority_generation"] < minimum_generation:
        problems.append(("generation_behind",
                         "the binding is at authority generation %s and the authority has fenced to %s: "
                         "the clone must reenroll before it may mutate"
                         % (binding["authority_generation"], minimum_generation)))
    return problems


def resolve_store(workspace, verify, host_identity, domain_uuid=None, store_uuid=None,
                  minimum_generation=None):
    """THE ROUTING DECISION: the absolute path of the authority store this workspace may write to.

    `workspace` is REQUIRED and is the only place the answer comes from. This function reads no
    environment variable and no current directory, and the caller cannot omit the coordinate and get
    a default. Refuses by name; the caller never receives a path it may not use."""
    binding = read_binding(workspace)
    if binding is None:
        raise EnrollmentRefused("not_enrolled",
                                "%s carries no enrollment binding: an unenrolled clone has no authority "
                                "and mutations refuse" % workspace,
                                {"workspace": str(workspace), "binding_path": binding_path(workspace)})
    problems = verify_binding(workspace, binding, verify, host_identity, domain_uuid, store_uuid,
                              minimum_generation)
    if problems:
        reason, text = problems[0]
        raise EnrollmentRefused(reason, text + (
            "" if len(problems) == 1 else "; and %d more: %s" % (
                len(problems) - 1, "; ".join("%s: %s" % p for p in problems[1:]))),
            {"workspace": str(workspace), "binding_path": binding_path(workspace),
             "problems": [p[0] for p in problems]})
    return binding["store_path"]
