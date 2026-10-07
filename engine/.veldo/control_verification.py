#!/usr/bin/env python3
"""veldo control_verification: the canonical gate run by the trusted installation against a candidate,
observed from outside it (VELDO-0058, PLAN-0019 W43).

A candidate is a Git work tree whose code is under test. Nothing it carries may decide whether it
passed: not its own scripts/verify.sh, not its own .veldo/policy_check.py, and not a stamp or an event
it writes into its own tree. This module is the one place the lander (GitLandOps.gate and finalize)
and the executor (LiveLoop.gate) go through for that.

  the installation  a directory holding the trusted scripts/verify.sh and .veldo/ (policy_check.py
                    and the modules it loads). installation_at() lays one down from a TRUSTED COMMIT
                    (the published trunk a candidate is built on, or the base a build started from),
                    read from Git objects into a directory outside the candidate, so what runs is
                    versioned and the candidate cannot replace it. A host may name an installed
                    directory instead.
  observe_gate      runs the installed verifier in candidate mode, `verify.sh --candidate <root>
                    --sink <dir>`, so every check runs in the candidate while the stamp, the gate
                    event and the review-event reconciliation go to a sink outside it. The state of
                    the candidate (HEAD, its tree, HEAD's symbolic target, every index entry, and
                    the bytes of every file in the work tree, tracked, untracked or ignored, outside
                    .git) is taken before and after, and must be equal. Whether every ref of the
                    repository is part of that state is the caller's explicit `bind_refs`, never a
                    default: True where a later reader takes a range from the refs (the lander's
                    own workspace, which shares no refs with anyone), False over a caller's
                    repository whose sibling worktrees and fetches move refs in normal use and
                    where nothing reads a range from them afterwards (the executor). It returns the
                    observation and writes it, canonical JSON, beside the sink: the exact candidate
                    commit and tree, whether the refs were bound, the command, the
                    verifier's digest and origin, the catalog's required checks and each one's
                    captured result, the complete output and its digests, the sink's stamp and gate
                    event, and the post-run equality. green is the conjunction of all of it, and
                    every reason it is not green is named in `refusals`.
  accept            the acceptance of that observation just before anything is published: the file
                    must be outside the candidate, carry exactly the digest recorded when it was
                    written, judge green again from its own content, and the candidate must still be
                    in the state it was verified in, taken with the same `bind_refs` the
                    observation records. Anything else is refused by name; evidence that
                    changes the candidate's bytes needs a new commit and a new verification.
  run_policy        the installed policy_check.py asked about the candidate: the installed module is
                    loaded by its own path (its siblings come from the installation), its subject
                    root is the candidate and its push range is the caller's base (the trunk commit
                    the candidate was built and gated on) to the candidate, never a range read from
                    the candidate's own refs, in a separate process.

The final receipt is never required inside its own candidate: the observation lives outside it, and a
valid candidate is verified and published with no stamp or event added to its tree. Gate process
kill qualification is Release 2. Pure stdlib; Git only through the shared boundary."""

import importlib.util as _git_importlib
from pathlib import Path as _GitPath
_git_spec = _git_importlib.spec_from_file_location("veldo_git_process", _GitPath(__file__).resolve().with_name("git_process.py"))
_git_process = _git_importlib.module_from_spec(_git_spec)
_git_spec.loader.exec_module(_git_process)
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import time
import uuid

GATE_PATH = "scripts/verify.sh"
POLICY_PATH = ".veldo/policy_check.py"
# The installation's policy source: the policy.yaml installation_at lays beside the installed module.
POLICY_SOURCE = "policy.yaml"
# VELDO-0148: the loader helper that loads a file from outside every installed directory by design (the
# trusted installation's policy_check.py, in a separate process of this module's own), declared so the
# authority service's installation, whose land station loads this module, reads it as no module of its own.
EXTERNAL_LOADERS = ("_policy_main",)
INSTALLED_PATHS = ("scripts", ".veldo")
# The line an installed verifier carries when it knows candidate mode. A verifier without it would
# ignore the arguments and verify the directory it lives in, so it is refused, never run.
INTERFACE = "# veldo-gate-interface: candidate-sink/v1"
OUTPUTS = ("last_verify", "events.jsonl")
GIT_SECONDS = 120


class Refused(Exception):
    def __init__(self, code, detail=""):
        super().__init__("%s: %s" % (code, detail) if detail else code)
        self.code, self.detail = code, detail


def _sibling(alias, name):
    spec = importlib.util.spec_from_file_location(alias, Path(__file__).resolve().with_name(name))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_ORGANS = {}


def _proof():
    """control_proof, for its one reading of a catalog and of the gate's printed results."""
    if "proof" not in _ORGANS:
        _ORGANS["proof"] = _sibling("veldo_control_proof_verification", "control_proof.py")
    return _ORGANS["proof"]


def digest(body):
    return "sha256:" + hashlib.sha256(body).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _real(path):
    return os.path.realpath(str(path))


def inside(path, root):
    """Whether `path`, symlinks resolved, is `root` or anything below it."""
    path, root = _real(path), _real(root)
    return path == root or path.startswith(root.rstrip(os.sep) + os.sep)


def _candidate_git():
    return _sibling("candidate_git", "candidate_git.py")


def _git(repo, *args, ok=(0,)):
    try:
        result = _candidate_git().run(repo, args, capture_output=True,
                                  stdin=subprocess.DEVNULL, timeout=GIT_SECONDS)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise Refused("unavailable_service:git/" + args[0], type(error).__name__)
    if result.returncode not in ok:
        raise Refused("unavailable_service:git/" + args[0],
                      result.stderr.decode("utf-8", "replace").strip().splitlines()[:1])
    return result


# The exact state of a candidate.

def _refs(root):
    """Every ref of the repository: its object and, for a symbolic ref, its target. A candidate that
    moves a ref during the run, such as refs/remotes/origin/main, changes what a later reader of those
    refs concludes about it, so where one reads them the refs are part of its state."""
    listed = _git(root, "for-each-ref", "--format=%(refname)%00%(objectname)%00%(symref)").stdout.decode("utf-8", "surrogateescape")
    refs = {}
    for line in listed.splitlines():
        name, _sep, rest = line.partition("\0")
        refs[name] = rest.split("\0")
    return refs


def _head_target(root):
    """HEAD's symbolic target (this work tree's own), None when HEAD is detached."""
    target = _git(root, "symbolic-ref", "-q", "HEAD", ok=(0, 1)).stdout.decode("utf-8", "surrogateescape").strip()
    return target or None


def _bind_refs(bind_refs):
    """The caller's explicit choice of whether the repository's refs are part of the state. Anything
    but True or False is refused: the binding is an input, never an ambient default."""
    if bind_refs is not True and bind_refs is not False:
        raise Refused("invalid_input:bind_refs", repr(bind_refs))
    return bind_refs


def state(root, *, bind_refs):
    """HEAD, its tree, HEAD's symbolic target, every index entry and flag, and the bytes of every entry
    of the work tree outside .git (tracked, untracked and ignored alike, directories and symlinks
    included); with `bind_refs` True, also every ref of the repository. The caller says which, with no
    default: the refs belong to the state where a later reader takes a range from them (the lander's
    own workspace), and not over a caller's repository whose sibling worktrees commit and fetch in
    normal use (the executor). Two states are equal only when all of it is, including the choice."""
    bind_refs = _bind_refs(bind_refs)
    root = Path(root)
    found = _git(root, "rev-parse", "--verify", "--quiet", "HEAD^{commit}", ok=(0, 1)).stdout.decode().strip()
    tree = _git(root, "rev-parse", "--verify", "--quiet", "HEAD^{tree}", ok=(0, 1)).stdout.decode().strip()
    entries = _git(root, "ls-files", "-s", "-v", "-z").stdout
    refs = _refs(root) if bind_refs else None
    head_target = _head_target(root)
    files = {}
    for directory, dirs, names in os.walk(str(root)):
        rel_dir = os.path.relpath(directory, str(root))
        if rel_dir == ".":
            dirs[:] = [d for d in dirs if d != ".git"]
            names = [n for n in names if n != ".git"]
        dirs.sort()
        for name in sorted(names) + [d + "/" for d in dirs]:
            rel = os.path.normpath(os.path.join(rel_dir, name.rstrip("/"))) + ("/" if name.endswith("/") else "")
            path = os.path.join(directory, name.rstrip("/"))
            try:
                info = os.lstat(path)
                if stat.S_ISLNK(info.st_mode):
                    files[rel] = ["link", os.readlink(path)]
                elif stat.S_ISDIR(info.st_mode):
                    files[rel] = ["dir", stat.S_IMODE(info.st_mode)]
                elif stat.S_ISREG(info.st_mode):
                    with open(path, "rb") as handle:
                        files[rel] = ["file", stat.S_IMODE(info.st_mode), digest(handle.read())]
                else:
                    files[rel] = ["other", stat.S_IFMT(info.st_mode)]
            except OSError as error:
                files[rel] = ["unreadable", type(error).__name__]
    body = {"head": found or None, "tree": tree or None, "index": digest(entries), "binds_refs": bind_refs,
            "refs": refs, "head_target": head_target, "files": files}
    return dict(body, digest=digest(canonical(body)))


def changes(before, after):
    """The paths (and index, HEAD, its symbolic target or a ref) that differ between two states, sorted."""
    named = sorted(p for p in set(before["files"]) | set(after["files"])
                   if before["files"].get(p) != after["files"].get(p))
    old, new = before.get("refs") or {}, after.get("refs") or {}
    for ref in sorted(set(old) | set(new), reverse=True):
        if old.get(ref) != new.get(ref):
            named.insert(0, ":ref/" + ref)
    for key in ("head", "tree", "index", "head_target", "binds_refs"):
        if before.get(key) != after.get(key):
            named.insert(0, ":" + key)
    return named


# The trusted installation.

def _safe(name):
    parts = PurePosixPath(name).parts
    return bool(parts) and not PurePosixPath(name).is_absolute() and ".." not in parts


def _verified_objects(repo, oids, algorithm):
    """{oid: (kind, bytes)} for each named object, each re-hashed against its own name. The object
    store maps names to content and is not trusted to do so honestly: a pack an agent planted can
    remap an existing id to other bytes. Such an object fails here and refuses the installation;
    its bytes are never installed."""
    oids = sorted(set(oids))
    try:
        result = _candidate_git().run(repo, ("cat-file", "--batch"), capture_output=True,
                                      input="".join(oid + "\n" for oid in oids).encode(), timeout=GIT_SECONDS)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise Refused("unavailable_service:git/cat-file", type(error).__name__)
    if result.returncode:
        raise Refused("unavailable_service:git/cat-file",
                      result.stderr.decode("utf-8", "replace").strip().splitlines()[:1])
    out, at, found = result.stdout, 0, {}
    for oid in oids:
        end = out.find(b"\n", at)
        header = out[at:end].split(b" ") if end >= 0 else []
        if len(header) != 3 or header[0] != oid.encode() or not header[2].isdigit():
            raise Refused("invalid_input:installation/object", oid)
        kind, size = header[1], int(header[2])
        body = out[end + 1:end + 1 + size]
        if len(body) != size or out[end + 1 + size:end + 2 + size] != b"\n":
            raise Refused("invalid_input:installation/object", oid)
        if hashlib.new(algorithm, kind + b" %d\0" % size + body).hexdigest() != oid:
            raise Refused("invalid_input:installation/object-hash", oid)
        found[oid] = (kind.decode(), body)
        at = end + 2 + size
    return found


def _tree_entries(body, width):
    entries, at = [], 0
    while at < len(body):
        space = body.find(b" ", at)
        nul = body.find(b"\0", space + 1)
        if space < 0 or nul < 0 or nul + 1 + width > len(body):
            raise Refused("invalid_input:installation/tree", "truncated tree")
        name = body[space + 1:nul].decode("utf-8", "surrogateescape")
        if "/" in name or name in ("", ".", ".."):
            raise Refused("invalid_input:installation/path", name)
        entries.append((body[at:space].decode(), name, body[nul + 1:nul + 1 + width].hex()))
        at = nul + 1 + width
    return entries


def installation_at(repo, commit, directory):
    """Lay down the verifier and the policy modules of the trusted `commit` of `repo`, from Git
    objects, in `directory` (a new directory). Returns {root, source}.

    Every object is verified from the commit down (commit, trees, blobs) by hashing its bytes
    against the id that names it, so what is installed is exactly the trusted commit's content
    whatever else a writer of the object store planted. A full object id is taken as the trusted
    commit itself; any other name is resolved through the repository's refs, which the caller
    therefore trusts."""
    directory = Path(directory)
    algorithm = _git(repo, "rev-parse", "--show-object-format").stdout.decode().strip()
    if algorithm not in ("sha1", "sha256"):
        raise Refused("invalid_input:installation/object-format", algorithm)
    width = hashlib.new(algorithm).digest_size
    commit = str(commit)
    if not re.fullmatch("[0-9a-f]{%d}" % (2 * width), commit):
        commit = _git(repo, "rev-parse", "--verify", "--end-of-options",
                      commit + "^{commit}").stdout.decode().strip()
    kind, body = _verified_objects(repo, [commit], algorithm)[commit]
    first = body.split(b"\n", 1)[0]
    if kind != "commit" or not re.fullmatch(rb"tree [0-9a-f]{%d}" % (2 * width), first):
        raise Refused("invalid_input:installation/commit", commit[:12])
    files, level = {}, {first[5:].decode(): [""]}
    while level:
        found = _verified_objects(repo, list(level), algorithm)
        deeper = {}
        for tree, prefixes in level.items():
            kind, body = found[tree]
            if kind != "tree":
                raise Refused("invalid_input:installation/tree", tree)
            for mode, name, child in _tree_entries(body, width):
                for prefix in prefixes:
                    path = prefix + name
                    if not prefix and name not in INSTALLED_PATHS:
                        continue
                    if mode == "40000":
                        deeper.setdefault(child, []).append(path + "/")
                    elif mode in ("100644", "100755"):
                        files[path] = (mode, child)
                    # Links and submodules are not installed, as the archive extraction never did.
        level = deeper
    if GATE_PATH not in files:
        raise Refused("missing_authority:verifier/absent", "%s has no %s" % (commit[:12], GATE_PATH))
    blobs = _verified_objects(repo, [oid for _, oid in files.values()], algorithm)
    directory.mkdir(parents=True)
    for path in sorted(files):
        mode, oid = files[path]
        kind, body = blobs[oid]
        if kind != "blob" or not _safe(path):
            raise Refused("invalid_input:installation/path", path)
        target = directory / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        target.chmod(0o755 if mode == "100755" else 0o644)
    (directory / '.veldo/authority_git_common').write_text(
        str(_candidate_git().common_directory(repo)) + '\n')
    return {"root": str(directory), "source": "commit:" + commit}


def _installation(installation):
    if isinstance(installation, dict):
        return Path(installation["root"]), installation.get("source") or "directory:" + installation["root"]
    return Path(installation), "directory:" + str(installation)


def gate_env():
    """The gate's environment: no inherited Git knob can select another repository (the isolated
    Git profile), and no Python process writes bytecode into the candidate."""
    env = dict(_git_process.clean_env(profile="isolated"), PYTHONDONTWRITEBYTECODE="1")
    # Landing permits authenticated reuse; always select that policy explicitly.
    # Preserve an operator's force-fresh override, including supported truthy forms.
    env["VELDO_GATE_FORCE_FRESH"] = env.get("VELDO_GATE_FORCE_FRESH") or "0"
    return env


# The observation.

def _regular_bytes(path):
    try:
        with open(path, "rb") as handle:
            info = os.fstat(handle.fileno())
            if stat.S_ISREG(info.st_mode) and not os.path.islink(path):
                return handle.read()
    except OSError:
        pass
    return None


def _read_outputs(sink, seeded):
    """The sink's stamp, its last gate event and every event appended beyond the candidate's own log
    (`seeded`, the bytes the sink log was seeded from), each only from a regular file, not a link."""
    found = {}
    for name in OUTPUTS:
        found[name] = _regular_bytes(os.path.join(sink, name))
    stamp = event = None
    try:
        stamp = json.loads(found["last_verify"]) if found["last_verify"] is not None else None
    except ValueError:
        stamp = None
    body = found["events.jsonl"] or b""
    lines = body.decode("utf-8", "replace").splitlines()
    appended = None
    if body.startswith(seeded):
        appended = []
        for line in body[len(seeded):].decode("utf-8", "replace").splitlines():
            try:
                event_line = json.loads(line)
            except ValueError:
                event_line = {"unreadable": True}
            if isinstance(event_line, dict):
                appended.append({k: event_line.get(k) for k in ("type", "commit", "producer", "verdict_path")
                                 if event_line.get(k) is not None})
    for line in reversed(lines):
        try:
            candidate = json.loads(line)
        except ValueError:
            continue
        if isinstance(candidate, dict) and candidate.get("producer") == "verify.sh":
            event = candidate
            break
    return {"sink": str(sink), "last_verify": stamp,
            "last_verify_digest": digest(found["last_verify"]) if found["last_verify"] is not None else None,
            "events_digest": digest(found["events.jsonl"]) if found["events.jsonl"] is not None else None,
            "events_lines": len(lines), "appended": appended, "gate_event": event}


def judge(observation):
    """Every reason `observation` is not a green, complete, unchanged verification of its commit,
    re-derived from its own content: the terminal line and each required check's result read again
    from the captured output, the sink's stamp and event, and the post-run equality."""
    CP = _proof()
    if not isinstance(observation, dict) or observation.get("schema") != CP.OBSERVATION_SCHEMA:
        return ["invalid_input:observation/schema"]
    problems = []
    commit = observation.get("commit")
    stdout = observation.get("stdout")
    if not isinstance(stdout, str) or observation.get("stdout_digest") != digest(stdout.encode("utf-8", "surrogateescape")):
        return ["binding_mismatch:observation/output"]
    required = (observation.get("catalog") or {}).get("required")
    if not isinstance(required, list) or not required:
        problems.append("missing_evidence:catalog")
        required = []
    results, terminal = CP.gate_results(stdout, required)
    if not CP._hex(commit):
        problems.append("invalid_input:observation/commit")
    if observation.get("exit") != 0:
        problems.append("missing_evidence:gate/exit")
    if terminal is None or terminal != observation.get("terminal") or terminal != "GATE: GREEN (%s)" % commit:
        problems.append("missing_evidence:gate/terminal")
    recorded = (observation.get("catalog") or {}).get("results") or {}
    for name in required:
        if results.get(name) is None:
            problems.append("missing_evidence:check/%s" % name)
        elif results[name] != "pass":
            problems.append("missing_evidence:check_failed/%s" % name)
        if recorded.get(name) != results.get(name):
            problems.append("binding_mismatch:check/%s" % name)
    candidate = observation.get("candidate") or {}
    if candidate.get("commit") != commit or not CP._hex(candidate.get("tree")):
        problems.append("binding_mismatch:observation/candidate")
    if candidate.get("binds_refs") is not True and candidate.get("binds_refs") is not False:
        problems.append("invalid_input:observation/bind_refs")
    post = observation.get("post_run") or {}
    if post.get("equal") is not True or post.get("state") != candidate.get("state"):
        problems.append("stale_subject:candidate/changed_during_gate")
    outputs = observation.get("outputs") or {}
    stamp, event = outputs.get("last_verify") or {}, outputs.get("gate_event") or {}
    if stamp.get("commit") != commit or stamp.get("status") != "green":
        problems.append("missing_evidence:gate/stamp")
    if event.get("commit") != commit or event.get("type") != "gate.passed":
        problems.append("missing_evidence:gate/event")
    reuse = _sibling("veldo_reuse_evidence", "reuse_evidence.py")
    for document in (stamp, event):
        problem = reuse.landing_problem(document)
        if problem:
            problems.append(problem)
    return problems


def observe_gate(candidate, installation, directory, *, bind_refs, timeout=None):
    """Run the installed verifier against `candidate` in candidate mode and observe it. `directory` is
    a new or empty directory outside the candidate: it receives the sink and observation.json.
    `bind_refs` (required, True or False) is whether the repository's refs are part of the candidate
    state compared before and after (see state). Returns (observation, reference); reference is
    {path, digest} of the written observation."""
    CP = _proof()
    bind_refs = _bind_refs(bind_refs)
    candidate = Path(_real(candidate))
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    if inside(directory, candidate) or inside(candidate, directory):
        raise Refused("invalid_input:observation/inside_candidate", str(directory))
    root, source = _installation(installation)
    try:
        verifier = (root / GATE_PATH).read_bytes()
    except OSError:
        raise Refused("missing_authority:verifier/absent", str(root / GATE_PATH))
    if inside(root, candidate):
        raise Refused("missing_authority:verifier/in_candidate", str(root))
    text = verifier.decode("utf-8", "surrogateescape")
    if INTERFACE not in text.splitlines():
        raise Refused("unavailable_service:verifier/candidate_mode", "the installed verifier has no candidate mode")
    sink = directory / "sink"
    sink.mkdir()
    seeded = _regular_bytes(str(candidate / ".veldo" / "events.jsonl")) or b""
    before = state(candidate, bind_refs=bind_refs)
    command = ["bash", str(root / GATE_PATH), "--candidate", str(candidate), "--sink", str(sink)]
    started = time.time()
    try:
        # The installation's own launcher finds the marker a nested gate needs (VELDO-0210 AC6).
        run = subprocess.run(command, cwd=str(candidate), capture_output=True, stdin=subprocess.DEVNULL,
                             env=gate_env(), timeout=timeout, pass_fds=CP.launcher_fds(root))
        exit_code, out, err = run.returncode, run.stdout, run.stderr
    except subprocess.TimeoutExpired as error:
        exit_code, out, err = None, error.stdout or b"", (error.stderr or b"") + b"\ngate timed out"
    except OSError as error:
        exit_code, out, err = None, b"", str(error).encode()
    finished = time.time()
    after = state(candidate, bind_refs=bind_refs)
    stdout = out.decode("utf-8", "surrogateescape")
    ran = CP.catalog(text)
    results, terminal = CP.gate_results(stdout, ran["required"])
    changed = changes(before, after)
    observation = {
        "schema": CP.OBSERVATION_SCHEMA, "command": command, "commit": before["head"],
        "gate": {"path": GATE_PATH, "digest": digest(verifier), "installation": source},
        "candidate": {"root": str(candidate), "commit": before["head"], "tree": before["tree"],
                      "state": before["digest"], "binds_refs": bind_refs},
        "catalog": {"required": ran["required"], "commands": ran["commands"], "results": results},
        "exit": exit_code, "stdout": stdout, "stdout_digest": digest(out),
        "stderr": err.decode("utf-8", "surrogateescape"), "stderr_digest": digest(err),
        "terminal": terminal, "outputs": _read_outputs(str(sink), seeded),
        "post_run": {"equal": not changed, "state": after["digest"], "changed": changed[:50],
                     "changed_count": len(changed)},
        "started_at": started, "finished_at": finished, "capture": uuid.uuid4().hex}
    observation["refusals"] = judge(observation)
    observation["green"] = not observation["refusals"]
    body = canonical(observation)
    path = directory / "observation.json"
    path.write_bytes(body)
    return observation, {"path": str(path), "digest": digest(body)}


def accept(reference, candidate, commit, *, bind_refs):
    """Every reason the observation `reference` names cannot be accepted for publishing `commit` from
    `candidate` now, its state taken again with `bind_refs` (required, True or False), which must be
    the binding the observation records. Empty means accepted."""
    bind_refs = _bind_refs(bind_refs)
    reference = reference if isinstance(reference, dict) else {}
    path = reference.get("path")
    if not isinstance(path, str) or not path:
        return ["missing_evidence:observation"]
    if inside(path, candidate):
        return ["invalid_input:observation/inside_candidate"]
    try:
        body = Path(path).read_bytes()
    except OSError:
        return ["missing_evidence:observation/absent"]
    if digest(body) != reference.get("digest"):
        return ["binding_mismatch:observation/digest"]
    try:
        observation = json.loads(body)
    except ValueError:
        return ["invalid_input:observation"]
    problems = judge(observation)
    if observation.get("commit") != commit:
        problems.append("stale_subject:observation/commit")
    if (observation.get("candidate") or {}).get("binds_refs") is not bind_refs:
        problems.append("binding_mismatch:observation/bind_refs")
    try:
        now = state(candidate, bind_refs=bind_refs)
    except Refused as error:
        return problems + [error.code]
    if now["head"] != commit or now["digest"] != (observation.get("candidate") or {}).get("state"):
        problems.append("stale_subject:candidate/changed_after_gate")
    return list(dict.fromkeys(problems))


# The installed policy.

def run_policy(installation, candidate, base, timeout=None):
    """(exit status, output) of the installed policy_check.py asked about `candidate` over the push
    range `base`..candidate, in a separate process started from this module; None as the status when
    it could not be run. `base` is the caller's own record of the trunk commit the candidate was built
    and gated on (a full commit id), never a ref read from the candidate: the candidate's code ran in
    the gate and could have moved its refs. A base that is not such a commit is refused there."""
    root, _source = _installation(installation)
    policy = root / POLICY_PATH
    if not policy.is_file():
        return None, "missing_authority:policy/absent"
    if inside(policy, candidate):
        return None, "missing_authority:policy/in_candidate"
    refused = _policy_source_refusal(policy, candidate)
    if refused:
        return None, refused
    command = [sys.executable, "-B", str(Path(__file__).resolve()), "policy", str(policy), _real(candidate),
               base if isinstance(base, str) else ""]
    try:
        run = subprocess.run(command, cwd=_real(candidate), capture_output=True, text=True,
                             stdin=subprocess.DEVNULL, env=gate_env(), timeout=timeout)
    except (OSError, subprocess.SubprocessError) as error:
        return None, type(error).__name__
    return run.returncode, (run.stdout + run.stderr).strip()


def _policy_source_refusal(policy, candidate):
    """The refusal when the installation's policy.yaml, beside the installed module, is absent or
    inside the candidate; None when it can be the policy source."""
    source = Path(policy).parent / POLICY_SOURCE
    if not source.is_file():
        return "missing_authority:policy_source/absent"
    if inside(source, candidate):
        return "missing_authority:policy_source/in_candidate"
    return None


_FULL_COMMIT = re.compile(r"[0-9a-f]{40}")


def _policy_base_refusal(base, candidate):
    """The refusal when `base` is not a full 40-hex commit id that exists in the candidate's
    repository and is an ancestor of its HEAD; None when it can be the push range's base."""
    if not isinstance(base, str) or not _FULL_COMMIT.fullmatch(base):
        return "missing_authority:policy_base/invalid"
    try:
        if _git(candidate, "cat-file", "-e", base + "^{commit}", ok=(0, 1, 128)).returncode != 0:
            return "missing_authority:policy_base/absent"
        if _git(candidate, "merge-base", "--is-ancestor", base, "HEAD", ok=(0, 1)).returncode != 0:
            return "missing_authority:policy_base/not_ancestor"
    except Refused as error:
        return "missing_authority:policy_base/" + error.code
    return None


def _policy_main(policy, candidate, base):
    """Load the installed policy module by its own path, so it and every sibling it loads are the
    installation's, then point its subject root at the candidate, its policy source at the
    installation's policy.yaml and its push range base at `base`, and ask it. The candidate is the
    subject, never the source of the protected list (its own policy.yaml could empty
    protected_paths) nor of the range (its code could move its own origin refs to HEAD, emptying a
    range read from them), VELDO-0058 AC3."""
    refused = _policy_source_refusal(policy, candidate) or _policy_base_refusal(base, candidate)
    if refused:
        print(refused)
        return 2
    spec = importlib.util.spec_from_file_location("veldo_installed_policy", policy)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = Path(candidate)
    module.POLICY = Path(policy).parent / POLICY_SOURCE
    module.BASE = base
    return module.main()


if __name__ == "__main__":
    if len(sys.argv) == 5 and sys.argv[1] == "policy":
        sys.exit(_policy_main(sys.argv[2], sys.argv[3], sys.argv[4]))
    print("usage: control_verification.py policy <installed policy_check.py> <candidate root> <base commit>")
    sys.exit(2)
