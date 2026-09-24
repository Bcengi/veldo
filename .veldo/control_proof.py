"""Accepted proof bundles and complete contextual proof validation (PLAN-0019 W35, VELDO-0050, R47).

WHAT THIS MODULE IS. The proof service the executor hands a build's proof to before the unit is
offered as built or for review. Two registered store commands, each committed through control_store's
signed journal on the caller's own connection, and each the ONLY writer of its entity kind
(control_store.declare_owners names this file as their code):

  record_gate_observation  what LiveLoop.gate observed when it ran the canonical gate: the command,
                           the commit it ran at, the digest of the gate script that ran, the exit
                           status, and the complete output with its digest. Stored when it is
                           captured, before any proof names it, so a proof can cite only an
                           observation the service already holds, by id and entity digest.
  accept_proof             the proof bundle, accepted only when complete contextual validation finds
                           nothing wrong. The transition reads everything it judges itself, inside
                           the store's transaction: the repository bound to the unit's repository
                           uuid, the Git objects there, and the stored observation.

A bundle is immutable: one per unit and built commit (proof-bundle:[domain, repository, unit,
commit]), never rewritten (proof_immutable), and a rebuild is a new commit with a new bundle.

THE SUBJECTS stay distinct and each is named by its own identity: the accepted specification revision
(the spec document at the run's base commit, by its sha256), the implementation commit (the
manifest's `commit`), and the built commit the gate ran on, which the bundle is keyed by. The built
commit is the implementation commit or a descendant that changes nothing outside proof/<unit>/
(VELDO-0049's rule for accepted proof).

COMPLETE CONTEXTUAL VALIDATION (contextual). The criterion set and the required evidence come from
the accepted specification, never from the manifest; the check set comes from the installed catalog,
the required items of the canonical gate (scripts/verify.sh) at the same base; the evidence kinds are
the installed validator's catalog (validate.EVIDENCE_KIND_ALIASES). Refused by name: an empty,
omitted, duplicate or invented criterion mapping; a criterion not passed or without evidence; an
evidence entry that is not {type, path, digest}, an artifact absent at the built commit or with
another digest; a required evidence kind neither an artifact type nor an observed passing check; an
implementation commit that is not an exact object id, does not exist, is not in the built commit's
history, or is followed by changes outside the proof; a spec revision other than the accepted one,
or a spec the build changed; a missing producer, or one other than the builder; a missing, altered,
or foreign observation (output digest, commit, verifier); a gate that did not exit 0 or printed no
terminal GREEN line for this commit; a required catalog check not observed passing; and a check the
manifest claims that the observation does not show. Every problem is reported, not only the first.

THE CHECKS A BUNDLE RECORDS are the required catalog checks as the observation shows them, each with
its catalog command, the gate line it was read from, the gate's exit and the observation id. They
are derived from the captured output, never from the manifest and never by default: a check with no
observation is not recorded, and the bundle is refused.

RESOLUTION. resolve() is what a fresh reviewer calls with nothing but the store and a unit and
commit: it reads the bundle (entity digest checked), the observation it cites (entity digest equal
to the one cited), the bound repository, re-runs contextual validation over Git and that stored
observation, and requires the result to equal what was accepted. No builder memory, no file outside
the store and the repository.

OBSERVABILITY. Every command is reported to `observe` with operation, domain, repository, unit,
request, accepted versions, outcome, named refusal and its taxonomy (invalid input, missing
authority, stale subject, unavailable service, missing evidence, unknown outcome; unknown is never
success). status() counts accepted and refused commands and names the pending work: observed built
commits with no accepted bundle.

NOT HERE. Crash recovery between the two commands and the executor's next step, and journal
projection (VELDO-0051) are not part of this module; gate-output isolation, the installed verifier
outside the candidate and signed Evidence Service receipts are VELDO-0058's. Standard library only.
"""
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import time
import uuid


def _sibling(alias, name):
    spec = importlib.util.spec_from_file_location(alias, Path(__file__).with_name(name))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# The one Git boundary every read of the repository goes through.
_git_process = _sibling("veldo_git_process_proof", "git_process.py")
_ORGANS = {}


def _organ(name):
    """A sibling organ loaded on first use (the executor's pre-factory path never pays for it)."""
    if name not in _ORGANS:
        _ORGANS[name] = _sibling("veldo_%s_proof" % name, name + ".py")
    return _ORGANS[name]


SCHEMA = "veldo.proof_bundle/v1"
OBSERVATION_SCHEMA = "veldo.gate_observation/v1"
PROOF_SCHEMA = "veldo.proof/v1"
BUNDLE_KIND = "proof_bundle"
OBSERVATION_KIND = "gate_observation"
ACCEPT = "accept_proof"
OBSERVE = "record_gate_observation"
OWNER = "VELDO-0050 accepted proof"
MANIFEST_PATH = "proof/%s/manifest.json"
GATE_PATH = "scripts/verify.sh"
GATE_COMMAND = ("bash", GATE_PATH)
WRITES = ("entities", "journal", "commands", "nonces")
PASSED = ("passed", "pass")

TAXONOMY = {
    "invalid_input": "invalid_input", "missing_authority": "missing_authority",
    "stale_subject": "stale_subject", "binding_mismatch": "stale_subject", "proof_immutable": "stale_subject",
    "missing_evidence": "missing_evidence", "unavailable_service": "unavailable_service",
}


def taxonomy(code):
    """The error class of a refusal code; a code with no class is an unknown outcome, never success."""
    return TAXONOMY.get(str(code).split(":", 1)[0], "unknown_outcome")


class Refused(Exception):
    """A named refusal; nothing was written. `codes` names every problem found."""

    def __init__(self, code, detail="", codes=None):
        self.code, self.detail = code, detail
        self.codes = list(codes or [code])
        super().__init__(code + (": " + detail if detail else ""))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def digest(body):
    return "sha256:" + hashlib.sha256(body).hexdigest()


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _hex(value):
    return isinstance(value, str) and len(value) in (40, 64) and set(value) <= set("0123456789abcdef")


def _bytes(text):
    return text.encode("utf-8", "surrogateescape")


def bundle_id(domain, repository, unit, commit):
    return "proof-bundle:" + json.dumps([domain, repository, unit, commit], separators=(",", ":"))


def observation_id(body):
    return "gate-observation:" + digest(canonical(body))[len("sha256:"):]


# Git reads, all through the one boundary.

def _git(repo, *args):
    return _git_process.run(["git", "-C", str(repo), *args], capture_output=True, timeout=30)


def head(repo):
    """The commit HEAD names in `repo`, or None."""
    r = _git(repo, "rev-parse", "--verify", "--quiet", "HEAD^{commit}")
    value = r.stdout.decode().strip() if r.returncode == 0 else ""
    return value if _hex(value) else None


def commit_exists(repo, commit):
    if not _hex(commit):
        return False
    r = _git(repo, "rev-parse", "--verify", "--quiet", commit + "^{commit}")
    return r.returncode == 0 and r.stdout.decode().strip() == commit


def blob(repo, commit, path):
    """The bytes of `path` at `commit`, or None."""
    if not _hex(commit) or not _text(path):
        return None
    r = _git(repo, "cat-file", "blob", commit + ":" + path)
    return None if r.returncode else r.stdout


def descends(repo, older, newer):
    return _git(repo, "merge-base", "--is-ancestor", older, newer).returncode == 0


def changed(repo, older, newer):
    r = _git(repo, "diff", "--name-only", "--no-renames", "--no-ext-diff", "--ignore-submodules=none", "-z",
             older, newer, "--")
    if r.returncode:
        return None
    return [p for p in r.stdout.decode("utf-8", "surrogateescape").split("\0") if p]


def committed_manifest(repo, commit, unit):
    """The manifest committed at proof/<unit>/manifest.json of `commit`, parsed, or None."""
    body = blob(repo, commit, MANIFEST_PATH % unit) if _text(unit) else None
    if body is None:
        return None
    try:
        parsed = json.loads(body)
    except ValueError:
        return None
    return parsed if isinstance(parsed, dict) else None


# The installed catalog and the gate's own output.

_CHECK = re.compile(r'^CHECK_([A-Za-z0-9_]+)="(.*)"\s*$')
_ORDER = re.compile(r'^ORDER="([^"]*)"', re.M)
_TERMINAL = re.compile(r"^GATE: (GREEN|RED) \(([^)]*)\)$")


def catalog(text):
    """The canonical gate's validation catalog: every CHECK_<name> declaration, the ORDER the gate
    runs them in, and the REQUIRED names (declared required:, or a legacy plain command), each with
    its command. This reads the declarations of the trusted gate script; it runs nothing."""
    declared = {}
    for line in text.splitlines():
        found = _CHECK.match(line)
        if found:
            declared[found.group(1)] = found.group(2)
    order_match = _ORDER.search(text)
    order = order_match.group(1).replace("\\\n", " ").split() if order_match else []
    required, commands = [], {}
    for name in order:
        declaration = declared.get(name, "")
        if not declaration or declaration.startswith(("na:", "waived:")):
            continue
        required.append(name)
        commands[name] = declaration[len("required:"):] if declaration.startswith("required:") else declaration
    return {"order": order, "declared": {name: declared.get(name, "") for name in order},
            "required": required, "commands": commands}


def gate_results(output, names):
    """({name: 'pass' | 'FAIL' | None}, terminal line or None) read off the gate's own lines. A check's
    result is the last '   <name>: pass|FAIL' line after its '== <name>' header (the gate prints it
    only when the check's command has returned); the terminal line is the output's last line."""
    lines = output.splitlines()
    results = {}
    for name in names:
        header, status = False, None
        for line in lines:
            if line == "== " + name:
                header = True
            elif header and line in ("   %s: pass" % name, "   %s: FAIL" % name):
                status = line.rsplit(": ", 1)[1]
        results[name] = status
    last = next((line for line in reversed(lines) if line.strip()), None)
    return results, (last if last is not None and _TERMINAL.match(last) else None)


def capture_gate(root):
    """Run the canonical gate once in `root` and return what was observed: the command, HEAD when it
    started, the digest and catalog of the gate script that ran, the exit status (None when the gate
    could not be run), the complete stdout and stderr with the digests of their exact bytes, and
    whether it was green: exit 0, a terminal GREEN line naming that commit, and every required item
    of its catalog observed passing."""
    root = Path(root)
    try:
        script = (root / GATE_PATH).read_bytes()
    except OSError:
        script = None
    commit = head(root)
    started = time.time()
    try:
        run = subprocess.run(list(GATE_COMMAND), capture_output=True, cwd=str(root))
        exit_code, out, err = run.returncode, run.stdout, run.stderr
    except OSError as error:
        exit_code, out, err = None, b"", str(error).encode()
    stdout = out.decode("utf-8", "surrogateescape")
    ran = catalog(script.decode("utf-8", "surrogateescape")) if script is not None else None
    results, terminal = gate_results(stdout, (ran or {}).get("required", []))
    green = (exit_code == 0 and commit is not None and terminal == "GATE: GREEN (%s)" % commit
             and ran is not None and all(results.get(name) == "pass" for name in ran["required"]))
    return {"schema": OBSERVATION_SCHEMA, "command": list(GATE_COMMAND), "commit": commit,
            "gate": {"path": GATE_PATH, "digest": digest(script) if script is not None else None},
            "exit": exit_code, "stdout": stdout, "stdout_digest": digest(out),
            "stderr": err.decode("utf-8", "surrogateescape"), "stderr_digest": digest(err),
            "terminal": terminal, "green": green, "started_at": started, "finished_at": time.time(),
            "capture": uuid.uuid4().hex}


def detail(observation):
    """One line for the executor's gate step: the terminal line, else the last line printed."""
    if observation.get("terminal"):
        return observation["terminal"]
    lines = [line for line in (observation.get("stdout") or "").splitlines() if line.strip()]
    return lines[-1] if lines else "gate produced no output"


def observation_problems(body):
    """Why `body` is not a gate observation this service records, by name."""
    if not isinstance(body, dict) or body.get("schema") != OBSERVATION_SCHEMA:
        return ["schema"]
    problems = []
    if not isinstance(body.get("command"), list) or not body["command"]:
        problems.append("command")
    if body.get("commit") is not None and not _hex(body.get("commit")):
        problems.append("commit")
    if body.get("exit") is not None and (not isinstance(body.get("exit"), int) or isinstance(body.get("exit"), bool)):
        problems.append("exit")
    if not isinstance(body.get("stdout"), str) or body.get("stdout_digest") != digest(_bytes(body["stdout"])):
        problems.append("stdout")
    if not isinstance(body.get("gate"), dict):
        problems.append("gate")
    return problems


# Complete contextual validation.

def _safe(path):
    return (_text(path) and "\\" not in path and not PurePosixPath(path).is_absolute()
            and ".." not in PurePosixPath(path).parts and str(PurePosixPath(path)) == path)


def _producer(value):
    """The producer's identity: a non-empty name, or a mapping naming its principal."""
    if _text(value):
        return value
    if isinstance(value, dict) and _text(value.get("principal")):
        return value["principal"]
    return None


def accepted_spec(repo, base, spec_path, unit):
    """(spec record, problems): the accepted specification revision, the spec document at the run's
    base commit, with the criterion and required-evidence sets derived from its own front matter."""
    body = blob(repo, base, spec_path) if _safe(spec_path) else None
    if body is None:
        return None, ["missing_authority:spec/absent"]
    V = _organ("validate")
    try:
        fm = V.front_matter(body.decode("utf-8"), spec_path) or {}
        criteria = [c["id"] for c in fm.get("acceptance_criteria") or [] if isinstance(c, dict) and "id" in c]
    except Exception as error:  # noqa: BLE001 - an unreadable accepted spec is refused by name
        return None, ["invalid_input:spec/%s" % type(error).__name__]
    required = fm.get("required_evidence") or []
    if fm.get("id") != unit:
        return None, ["invalid_input:spec/identity"]
    return {"path": spec_path, "revision": digest(body), "criteria": criteria,
            "required_evidence": list(required) if isinstance(required, list) else []}, []


def contextual(repo, *, unit, commit, base, spec_path, manifest, observation, observation_id=None, builder=None):
    """(problems, record): complete contextual validation of `manifest` for `unit` at the built commit
    `commit`, against the accepted specification and the installed catalog at `base`, the repository's
    Git objects and the gate `observation`. `record` is the bundle's derived content (meaningful only
    when there are no problems)."""
    problems = []
    if not _hex(commit) or not commit_exists(repo, commit):
        return ["invalid_input:source_commit"], None
    if not _hex(base) or not commit_exists(repo, base) or not descends(repo, base, commit):
        return ["stale_subject:base"], None
    spec, spec_problems = accepted_spec(repo, base, spec_path, unit)
    if spec is None:
        return spec_problems, None
    gate_bytes = blob(repo, base, GATE_PATH)
    if gate_bytes is None:
        return ["missing_authority:catalog/absent"], None
    installed = catalog(gate_bytes.decode("utf-8", "surrogateescape"))
    if blob(repo, commit, spec_path) is None or digest(blob(repo, commit, spec_path)) != spec["revision"]:
        problems.append("stale_subject:spec/changed_by_build")
    if not isinstance(manifest, dict):
        return problems + ["invalid_input:manifest"], None
    if manifest.get("schema") != PROOF_SCHEMA:
        problems.append("invalid_input:manifest/schema")
    if manifest.get("spec_id") != unit:
        problems.append("invalid_input:manifest/spec_id")
    if manifest.get("spec_revision") != spec["revision"]:
        problems.append("stale_subject:spec_revision")
    # The manifest itself: the committed Git object when the built commit carries one, else these bytes.
    committed = blob(repo, commit, MANIFEST_PATH % unit)
    if committed is not None:
        try:
            same = json.loads(committed) == manifest
        except ValueError:
            same = False
        if not same:
            problems.append("binding_mismatch:manifest")
        manifest_record = {"location": "git", "path": MANIFEST_PATH % unit, "digest": digest(committed)}
    else:
        manifest_record = {"location": "store", "path": None, "digest": digest(canonical(manifest))}
    implementation = manifest.get("commit")
    if not _hex(implementation):
        problems.append("invalid_input:commit")
    elif not commit_exists(repo, implementation):
        problems.append("missing_evidence:commit/nonexistent")
    elif not descends(repo, implementation, commit):
        problems.append("stale_subject:commit/not_ancestor")
    else:
        after = changed(repo, implementation, commit)
        if after is None or any(not p.startswith("proof/%s/" % unit) for p in after):
            problems.append("stale_subject:commit/changed_after_implementation")
    producer = _producer(manifest.get("producer"))
    if producer is None:
        problems.append("missing_authority:producer")
    elif _text(builder) and producer != builder:
        problems.append("binding_mismatch:producer")
    # The criterion set: the accepted spec's, exactly once each.
    criteria = manifest.get("criteria")
    artifacts = []
    if not isinstance(criteria, list) or not criteria:
        problems.append("missing_evidence:criteria/empty")
        criteria = []
    ids = [c.get("id") if isinstance(c, dict) else None for c in criteria]
    problems.extend("missing_evidence:criteria/omitted:%s" % cid for cid in spec["criteria"] if cid not in ids)
    problems.extend("invalid_input:criteria/duplicate:%s" % cid for cid in sorted({i for i in ids if ids.count(i) > 1}, key=str))
    problems.extend("invalid_input:criteria/invented:%s" % cid for cid in sorted({i for i in ids if i not in spec["criteria"]}, key=str))
    for item in criteria:
        cid = item.get("id") if isinstance(item, dict) else None
        evidence = item.get("evidence") if isinstance(item, dict) else None
        if not isinstance(item, dict) or item.get("status") != "passed" or not isinstance(evidence, list) or not evidence:
            problems.append("missing_evidence:criterion/%s" % cid)
            continue
        for entry in evidence:
            if not isinstance(entry, dict) or not all(_text(entry.get(f)) for f in ("type", "path", "digest")) \
                    or not _safe(entry["path"]):
                problems.append("invalid_input:evidence/%s" % cid)
                continue
            body = blob(repo, commit, entry["path"])
            if body is None:
                problems.append("missing_evidence:artifact/%s" % entry["path"])
            elif digest(body) != entry["digest"]:
                problems.append("binding_mismatch:artifact/%s" % entry["path"])
            else:
                artifacts.append({"criterion": cid, "type": entry["type"], "path": entry["path"], "digest": entry["digest"]})
    # The checks: the installed catalog's required items, as the observation shows them.
    checks, results = [], {}
    if observation_problems(observation):
        problems.append("missing_evidence:observation")
    else:
        results, terminal = gate_results(observation["stdout"], installed["required"])
        if observation.get("commit") != commit:
            problems.append("stale_subject:observation/commit")
        if (observation.get("gate") or {}).get("digest") != digest(gate_bytes):
            problems.append("stale_subject:observation/verifier")
        if observation.get("exit") != 0:
            problems.append("missing_evidence:observation/exit")
        if terminal != "GATE: GREEN (%s)" % commit:
            problems.append("missing_evidence:observation/terminal")
        for name in installed["required"]:
            if results.get(name) is None:
                problems.append("missing_evidence:check/%s" % name)
            elif results[name] != "pass":
                problems.append("missing_evidence:check_failed/%s" % name)
            else:
                checks.append({"name": name, "status": "passed", "command": installed["commands"][name],
                               "observed": "   %s: pass" % name, "gate_exit": observation.get("exit"),
                               "observation": observation_id})
    claims = manifest.get("checks")
    if not isinstance(claims, list):
        problems.append("invalid_input:checks")
        claims = []
    observed = {c["name"] for c in checks}
    for claim in claims:
        name = claim.get("name") if isinstance(claim, dict) else None
        status = (claim.get("status") or claim.get("result")) if isinstance(claim, dict) else None
        if (status in PASSED) != (name in observed):
            problems.append("binding_mismatch:check_claim/%s" % name)
    # The required evidence kinds, each an artifact type or an observed passing check.
    aliases = _organ("validate").EVIDENCE_KIND_ALIASES
    kinds = {a["type"] for a in artifacts} | observed
    for kind in spec["required_evidence"]:
        if kind not in aliases:
            problems.append("invalid_input:required/%s" % kind)
        elif not aliases[kind] & kinds:
            problems.append("missing_evidence:required/%s" % kind)
    record = {"schema": SCHEMA, "unit": unit, "source": {"commit": commit}, "base": base,
              "implementation": {"commit": implementation}, "spec": spec,
              "catalog": {"path": GATE_PATH, "digest": digest(gate_bytes), "required": installed["required"],
                          "commands": installed["commands"]},
              "manifest": dict(manifest_record, body=manifest),
              "artifacts": sorted(artifacts, key=lambda a: (str(a["criterion"]), a["path"])),
              "checks": checks, "producer": producer, "builder": builder if _text(builder) else None}
    return problems, record


# The transitions, inside the store's own transaction.

def _entity_row(conn, identity):
    row = conn.execute("SELECT kind, version, digest, data FROM entities WHERE id=?", (identity,)).fetchone()
    return None if row is None else {"kind": row[0], "version": row[1], "digest": row[2], "data": json.loads(row[3])}


def _writer(conn, params):
    """The command's principal is an active `service` member whose scope covers the repository."""
    AC, CM = _organ("authority_contract"), _organ("control_membership")
    principal, now = params.get("principal"), params.get("now")
    row = _entity_row(conn, principal) if _text(principal) else None
    entry = dict(row["data"], principal=principal) if row and row["kind"] == "membership" else None
    active, _why = AC.active_member(entry, now) if isinstance(now, (int, float)) else (False, "clock")
    if (not active or entry.get("principal_type") not in AC.BOUNDARIES["result_acceptance"]
            or entry.get("principal_type") != "service" or not CM.scope_covers(entry.get("scope"), params.get("repository"))):
        raise Refused("missing_authority:principal", "not an active service member for this repository")


def _observe_transition(conn, params, before):
    """THE OBSERVATION: stored once, as captured, under an id its own content names."""
    _writer(conn, params)
    body, oid = params.get("observation"), params.get("observation_id")
    problems = observation_problems(body)
    if problems or (body.get("domain"), body.get("repository")) != (params.get("domain"), params.get("repository")):
        raise Refused("invalid_input:observation", ", ".join(problems) or "domain or repository")
    if oid != observation_id(body):
        raise Refused("invalid_input:observation_id", str(oid))
    if before.get(oid) is not None:
        raise Refused("proof_immutable:observation", oid)
    return {oid: {"kind": OBSERVATION_KIND, "data": body}}


def _accept_transition(conn, params, before):
    """THE ACCEPTANCE: complete contextual validation over the bound repository and the stored
    observation, then one immutable bundle."""
    _writer(conn, params)
    domain, repository, unit, commit = (params.get(k) for k in ("domain", "repository", "unit", "commit"))
    if not all(_text(v) for v in (domain, repository, unit, commit)):
        raise Refused("invalid_input", "domain, repository, unit and commit are named")
    rid = bundle_id(domain, repository, unit, commit)
    if before.get(rid) is not None:
        raise Refused("proof_immutable", rid)
    repo = _organ("control_store").bound_repository(conn, domain, repository)
    if repo is None:
        raise Refused("missing_authority:repository", "no accepted repository is bound for this unit")
    reference = params.get("observation") if isinstance(params.get("observation"), dict) else {}
    stored = before.get(reference.get("id")) if _text(reference.get("id")) else None
    observation, codes = None, []
    if stored is None or stored["kind"] != OBSERVATION_KIND:
        codes.append("missing_evidence:observation/unrecorded")
    elif stored["digest"] != reference.get("digest"):
        codes.append("binding_mismatch:observation")
    elif (stored["data"].get("domain"), stored["data"].get("repository")) != (domain, repository):
        codes.append("binding_mismatch:observation/repository")
    else:
        observation = stored["data"]
    problems, record = contextual(repo, unit=unit, commit=commit, base=params.get("base"),
                                  spec_path=params.get("spec_path"), manifest=params.get("manifest"),
                                  observation=observation, observation_id=reference.get("id"),
                                  builder=params.get("builder"))
    problems = codes + [p for p in problems if not (codes and p == "missing_evidence:observation")]
    if problems:
        raise Refused(problems[0], "; ".join(problems), problems)
    record.update(domain=domain, repository=repository, observation={"id": reference["id"], "digest": reference["digest"]},
                  accepted={"at": params["now"], "principal": params["principal"]})
    return {rid: {"kind": BUNDLE_KIND, "data": record}}


class ProofService:
    """One domain and repository's proof service over a real control store connection. `principal` is
    the service writing (an active `service` member scoped to the repository), `sign(bytes) -> text`
    signs its journal records as `signer`, and `repo` is the enrolled repository it reads, bound to
    the repository uuid in the store."""

    def __init__(self, store, conn, *, domain, repository, repo, principal, signer, sign, generation=1,
                 observe=None, clock=None):
        if not all(_text(v) for v in (domain, repository, principal, signer)):
            raise Refused("invalid_input", "domain, repository, principal and signer are named")
        self.store, self.conn = store, conn
        self.domain, self.repository, self.principal = domain, repository, principal
        self.signer, self.sign, self.generation = signer, sign, generation
        self.observe = observe or (lambda event: None)
        self.clock = clock or time.time
        self.counts = {"accepted": 0, "refused": 0}
        store.declare_owners(conn, OWNER, kinds={BUNDLE_KIND: (ACCEPT,), OBSERVATION_KIND: (OBSERVE,)}, module=__file__)
        store.bind_repositories(conn, domain, {repository: str(repo)})
        conn.command_registry[OBSERVE] = {"transaction_transition": _observe_transition, "writes": WRITES}
        conn.command_registry[ACCEPT] = {"transaction_transition": _accept_transition, "writes": WRITES}

    def _run(self, operation, unit, command_id, params, expected):
        params = dict(params, now=self.clock(), principal=self.principal, domain=self.domain,
                      repository=self.repository)
        command = {"command_id": command_id, "principal": self.principal, "operation": operation,
                   "parameters": params, "expected_versions": expected, "artifact_digests": [],
                   "nonce": command_id + "/nonce"}
        event = {"schema": SCHEMA, "operation": operation, "domain": self.domain, "repository": self.repository,
                 "unit": unit, "request": command_id, "accepted_versions": dict(expected)}
        try:
            result = self.store.execute(self.conn, command, self.signer, self.sign, self.generation)
        except (Refused, self.store.StoreRefused) as error:
            self.counts["refused"] += 1
            codes = list(getattr(error, "codes", None) or [error.code])
            self.observe(dict(event, outcome="refused", refusal=error.code, refusals=codes,
                              taxonomy=taxonomy(error.code)))
            if isinstance(error, Refused):
                raise
            raise Refused(error.code, error.detail) from error
        self.counts["accepted"] += 1
        self.observe(dict(event, outcome="accepted", watermark=result["seq"]))
        return result

    def _version(self, identity):
        row = self.conn.execute("SELECT version FROM entities WHERE id=?", (identity,)).fetchone()
        return row[0] if row else 0

    def record_observation(self, observation, unit=None):
        """Store what the gate was observed doing; returns {id, digest, seq}, the reference a proof cites."""
        body = dict(observation or {}, domain=self.domain, repository=self.repository)
        oid = observation_id(body)
        result = self._run(OBSERVE, unit, "proof/observe/" + oid[len("gate-observation:"):],
                           {"observation": body, "observation_id": oid, "unit": unit}, {oid: self._version(oid)})
        row = _entity_row(self.conn, oid)
        return {"id": oid, "digest": row["digest"], "seq": result["seq"]}

    def accept(self, unit, *, commit, base, spec_path, manifest, observation, builder=None):
        """The proof accepted as immutable evidence: {bundle, digest, seq, record}, or Refused naming
        every problem. `observation` is the reference record_observation returned."""
        reference = observation if isinstance(observation, dict) else {}
        rid = bundle_id(self.domain, self.repository, unit, commit) if _text(unit) and _text(commit) else None
        if rid is None:
            self.counts["refused"] += 1
            self.observe({"schema": SCHEMA, "operation": ACCEPT, "domain": self.domain, "repository": self.repository,
                          "unit": unit, "outcome": "refused", "refusal": "invalid_input", "taxonomy": "invalid_input"})
            raise Refused("invalid_input", "a unit and a built commit are named")
        params = {"unit": unit, "commit": commit, "base": base, "spec_path": spec_path, "manifest": manifest,
                  "observation": {"id": reference.get("id"), "digest": reference.get("digest")}, "builder": builder}
        expected = {rid: self._version(rid)}
        if _text(reference.get("id")):
            expected[reference["id"]] = self._version(reference["id"])
        command_id = "proof/accept/%s/%s" % (unit, digest(canonical(params))[len("sha256:"):][:24])
        result = self._run(ACCEPT, unit, command_id, params, expected)
        row = _entity_row(self.conn, rid)
        return {"bundle": rid, "digest": row["digest"], "seq": result["seq"], "record": row["data"]}

    def bundle(self, unit, commit):
        row = _entity_row(self.conn, bundle_id(self.domain, self.repository, unit, commit))
        return row["data"] if row and row["kind"] == BUNDLE_KIND else None

    def status(self):
        """Metrics: accepted and refused commands, the units with accepted proof, and the pending work
        (observed built commits no accepted bundle names yet)."""
        bundles, observed = {}, {}
        for kind, data in self.conn.execute("SELECT kind, data FROM entities WHERE kind IN (?, ?)",
                                            (BUNDLE_KIND, OBSERVATION_KIND)):
            record = json.loads(data)
            if (record.get("domain"), record.get("repository")) != (self.domain, self.repository):
                continue
            if kind == BUNDLE_KIND:
                bundles.setdefault(record["unit"], set()).add(record["source"]["commit"])
            elif record.get("commit"):
                observed[record["commit"]] = True
        proven = {c for commits in bundles.values() for c in commits}
        return dict(self.counts, proven=sorted(bundles), pending=sorted(c for c in observed if c not in proven))


def resolve(store, conn, *, domain, repository, unit, commit):
    """THE FRESH READER: the accepted bundle of `unit` at the built `commit`, re-derived from Git and
    its stored observation and required equal to what was accepted, or Refused by name."""
    rid = bundle_id(domain, repository, unit, commit)
    row = _entity_row(conn, rid)
    if row is None or row["kind"] != BUNDLE_KIND:
        raise Refused("missing_evidence:proof_bundle", rid)
    data = row["data"]
    if store.digest_of({"kind": row["kind"], "data": data, "version": row["version"]}) != row["digest"]:
        raise Refused("binding_mismatch:bundle_digest", rid)
    if (data.get("schema"), data.get("domain"), data.get("repository"), data.get("unit"),
            (data.get("source") or {}).get("commit")) != (SCHEMA, domain, repository, unit, commit):
        raise Refused("binding_mismatch:bundle_identity", rid)
    repo = store.bound_repository(conn, domain, repository)
    if repo is None:
        raise Refused("missing_authority:repository", repository)
    reference = data.get("observation") or {}
    stored = _entity_row(conn, reference.get("id")) if _text(reference.get("id")) else None
    if stored is None or stored["kind"] != OBSERVATION_KIND or stored["digest"] != reference.get("digest"):
        raise Refused("binding_mismatch:observation", str(reference.get("id")))
    problems, again = contextual(repo, unit=unit, commit=commit, base=data.get("base"),
                                 spec_path=(data.get("spec") or {}).get("path"),
                                 manifest=(data.get("manifest") or {}).get("body"), observation=stored["data"],
                                 observation_id=reference["id"], builder=data.get("builder"))
    if problems:
        raise Refused(problems[0], "; ".join(problems), problems)
    kept = {k: v for k, v in data.items() if k not in ("domain", "repository", "observation", "accepted")}
    if again != kept:
        raise Refused("binding_mismatch:bundle", "the bundle is not what its inputs derive")
    return dict(data, bundle=rid, digest=row["digest"])
