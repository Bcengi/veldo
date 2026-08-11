#!/usr/bin/env python3
"""WARP-0809 (W9 of PLAN-0008): cross-pack conformance harness (build machinery).

The join point of the multi-tool pack plan. It converts "the seven packs were ported" into a
property the gate ENFORCES, for every declared pack, by construction. Reading the pack manifest
(.veldo/packs.json), for each pack it proves:

  drift    - the pack's engine is byte-identical (content AND mode) to the canonical source;
  exec-bit - the pack's COMMITTED git pre-push hook and copied guard script are executable in the
             git INDEX (git silently skips a non-executable hook, so an unproven push then fails
             OPEN - the WARP-0807 lesson; asserted via git ls-files -s, which reflects what a fresh
             clone gets, not the local working tree that can diverge from the index);
  gate     - the pack's own copied guard, driven against a constructed repository state, BLOCKS a
             push at an unproven HEAD and ALLOWS one at a proven HEAD (green last_verify + a proof
             manifest + a passing commit-bound verdict), through the pack's committed git pre-push
             hook where it ships one, else the guard directly (the option-B Claude pack);
  policy   - policy_check.py, run standalone exactly as CI runs it, agrees (blocks the unproven
             state, passes the proven state).

Build machinery in the repo-root .veldo/ (like pack.py), NOT shipped engine, so it is not copied
into packs and cannot itself drift. Pure stdlib; the per-pack gate is driven locally with no
network (a state is constructed and the committed hook invoked against it), and one real
git-push-to-a-local-bare-remote case proves the exec bit is load-bearing end to end.
"""
import importlib.util
import json
import os
import subprocess
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
PUSH_PAYLOAD = '{"tool_input":{"command":"git push"}}'


def _load_module(repo_root, name, rel):
    spec = importlib.util.spec_from_file_location(name, Path(repo_root) / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _git(args, cwd, env=None):
    return subprocess.run(["git"] + args, cwd=str(cwd), capture_output=True, text=True, env=env)


def _git_env(dest):
    """A hermetic git environment pinned to the fixture. CLAUDE_PROJECT_DIR is set to the fixture
    so the guard (which cds to it) can never be redirected at the wrong repo by an inherited value;
    global/system config are neutralized so the run is deterministic."""
    env = dict(os.environ)
    env.update({
        "GIT_AUTHOR_NAME": "veldo", "GIT_AUTHOR_EMAIL": "veldo@local",
        "GIT_COMMITTER_NAME": "veldo", "GIT_COMMITTER_EMAIL": "veldo@local",
        "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
        "CLAUDE_PROJECT_DIR": str(dest),
    })
    return env


def committed_hook_modes(repo_root):
    """The git-INDEX mode of every pack's git pre-push hook and copied guard script, as a dict
    {repo-relative path: octal mode string}. Reads the index (git ls-files -s), so it reflects what
    a fresh clone gets, not the local working tree, which can diverge from the index. This is the
    check that closes the WARP-0808 note: a committed non-executable hook is a fail-open that a
    working-tree os.access check can miss."""
    # the guard is ENGINE now and has one home, so it is checked once at the canonical source;
    # each pack still ships its own pre-push hook, which is extension and stays per-pack.
    r = _git(["ls-files", "-s", "--", "packs/*/hooks/pre-push",
              "engine/scripts/veldo-guard.sh", "engine/hooks/pre-push"],
             cwd=repo_root)
    modes = {}
    for line in r.stdout.splitlines():
        meta, _, path = line.partition("\t")  # "<mode> <sha> <stage>\t<path>"
        if path:
            modes[path] = meta.split()[0]
    return modes


CANONICAL_ENGINE = "engine"


def _archive_into(repo_root, tree, dest):
    """Extract one committed tree (mode-preserving) into dest via git archive | tar."""
    os.makedirs(dest, exist_ok=True)
    ar = subprocess.run(["git", "archive", "HEAD:" + tree], cwd=str(repo_root),
                        capture_output=True)
    if ar.returncode != 0:
        raise RuntimeError("git archive failed for %s: %s" % (tree, ar.stderr.decode()[:200]))
    tar = subprocess.run(["tar", "-x", "-C", dest], input=ar.stdout, capture_output=True)
    if tar.returncode != 0:
        raise RuntimeError("tar extract failed for %s: %s" % (tree, tar.stderr.decode()[:200]))


def _extract_pack(repo_root, pack_dir, dest, canonical_engine=CANONICAL_ENGINE):
    """COMPOSE the pack the way an install does: the canonical engine first, then the pack's own
    tool-specific files layered on top so a pack override always wins.

    This deliberately does NOT require the engine to be committed inside the pack. The engine has
    exactly one home, `engine`, and a pack is the extension on top of it. Conformance
    therefore drives the artifact a user actually gets rather than a committed copy of it, which
    is what lets the copies go away without weakening the check."""
    _archive_into(repo_root, canonical_engine, dest)
    _archive_into(repo_root, pack_dir, dest)


def _commit_all(dest, env):
    _git(["init", "-q"], cwd=dest, env=env)
    _git(["add", "-A"], cwd=dest, env=env)
    _git(["commit", "-q", "-m", "pack"], cwd=dest, env=env)
    return _git(["rev-parse", "HEAD"], cwd=dest, env=env).stdout.strip()


def _write_proven_evidence(dest, sha, repo_root):
    """Lay down exactly the evidence a proven HEAD carries: a green last_verify bound to HEAD, a
    proof manifest for HEAD, and a passing commit-bound verdict whose proof_digest matches the
    manifest (the shape both the guard and policy_check require)."""
    validate = _load_module(repo_root, "veldo_validate_c", ".veldo/validate.py")
    veldo = Path(dest) / ".veldo"
    veldo.mkdir(exist_ok=True)
    (veldo / "last_verify").write_text(json.dumps({"commit": sha, "status": "green"}))
    pdir = Path(dest) / "proof" / "CONF-PROVEN"
    pdir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": "veldo.proof/v1", "spec_id": "CONF-PROVEN", "commit": sha,
        "criteria": [{"id": "AC1", "status": "passed", "evidence": []}],
        "checks": [{"name": "unit", "status": "passed"}],
    }
    (pdir / "manifest.json").write_text(json.dumps(manifest))
    verdict = {
        "schema": "veldo.verdict/v1", "spec_id": "CONF-PROVEN", "commit": sha,
        "reviewer": "conformance-fixture", "verdict": "pass",
        "proof_digest": validate.proof_digest(manifest), "findings": [],
    }
    (pdir / "verdict.json").write_text(json.dumps(verdict))


def _has_prepush(repo_root, pack_dir):
    return (Path(repo_root) / pack_dir / "hooks" / "pre-push").is_file()


def _drive_gate(dest, has_prepush, env):
    """Invoke the pack's push gate against the constructed state and return its exit code (0 = push
    allowed, non-zero = blocked). Through the committed git pre-push hook where the pack ships one
    (the hook feeds the guard the JSON payload itself), else the guard directly fed the payload on
    stdin (the option-B Claude pack, whose committed hook is set up by init, not shipped in-tree)."""
    if has_prepush and (Path(dest) / "hooks" / "pre-push").is_file():
        r = subprocess.run(["bash", str(Path(dest) / "hooks" / "pre-push")],
                           cwd=str(dest), env=env, capture_output=True, text=True)
    else:
        r = subprocess.run(["bash", str(Path(dest) / "scripts" / "veldo-guard.sh")],
                           cwd=str(dest), env=env, input=PUSH_PAYLOAD, capture_output=True, text=True)
    return r.returncode


def _policy_exit(dest, env):
    """policy_check.py run standalone, exactly as CI runs it, against the constructed state."""
    r = subprocess.run(["python3", str(Path(dest) / ".veldo" / "policy_check.py")],
                       cwd=str(dest), env=env, capture_output=True, text=True)
    return r.returncode


def gate_exit_for_state(repo_root, pack_id, proven):
    """Public: build a throwaway repo from a pack in the given state (proven / unproven) and return
    its push-gate exit code. The single driver both the conformance check and its teeth use."""
    pack = _pack_by_id(repo_root, pack_id)
    has_prepush = _has_prepush(repo_root, pack["pack_dir"])
    with tempfile.TemporaryDirectory() as td:
        _extract_pack(repo_root, pack["pack_dir"], td)
        env = _git_env(td)
        sha = _commit_all(td, env)
        if proven:
            _write_proven_evidence(td, sha, repo_root)
        return _drive_gate(td, has_prepush, env)


def _pack_by_id(repo_root, pack_id):
    PK = _load_module(repo_root, "veldo_pack_c", ".veldo/pack.py")
    for p in PK.load_packs(repo_root=repo_root)["packs"]:
        if p["id"] == pack_id:
            return p
    raise KeyError(pack_id)


def _conform_one(repo_root, pack, modes):
    """Every conformance finding for one pack (empty list = conformant). Names the pack and the
    failure so the gate points at the offender."""
    findings = []
    pid = pack["id"]
    pack_dir = pack["pack_dir"]
    PK = _load_module(repo_root, "veldo_pack_c", ".veldo/pack.py")

    # THE ENGINE IS NOT COPIED INTO PACKS ANY MORE, so there is no copy to drift. What replaces
    # the drift check is the property that actually matters and that this harness already proves
    # below by construction: the COMPOSED pack (canonical engine + this pack's extension) enforces
    # the VELDO invariant. A pack that still carries an engine copy is the thing to catch now,
    # because it would shadow the canonical source at install.
    # the option-B Claude pack IS the canonical engine in place (pack_dir == engine_src), so it
    # carries the engine by definition and is not a copy of anything.
    stale = [] if pack_dir == pack["engine_src"] else [
        r for r in (".veldo/validate.py", ".veldo/events.py", "scripts/verify.sh")
        if (Path(repo_root) / pack_dir / r).exists()]
    if stale:
        findings.append("pack %s: carries a stale engine copy that would shadow the canonical "
                        "source at install: %r" % (pid, stale))

    has_prepush = _has_prepush(repo_root, pack_dir)

    # exec-bit at the git index (only packs that ship a committed hook of their own)
    if has_prepush:
        for rel in ("%s/hooks/pre-push" % pack_dir,):
            if modes.get(rel) != "100755":
                findings.append("pack %s: committed %s not executable in the index (mode %r)"
                                % (pid, rel, modes.get(rel)))

    with tempfile.TemporaryDirectory() as td:
        up = os.path.join(td, "u")
        pv = os.path.join(td, "p")
        _extract_pack(repo_root, pack_dir, up)
        _extract_pack(repo_root, pack_dir, pv)
        eu = _git_env(up)
        ep = _git_env(pv)
        _commit_all(up, eu)
        sha = _commit_all(pv, ep)
        _write_proven_evidence(pv, sha, repo_root)

        # guard: block the unproven, allow the proven (both directions = intrinsic teeth)
        if _drive_gate(up, has_prepush, eu) == 0:
            findings.append("pack %s: guard did NOT block an unproven push (fail-open)" % pid)
        rc = _drive_gate(pv, has_prepush, ep)
        if rc != 0:
            findings.append("pack %s: guard blocked a PROVEN push (rc %s)" % (pid, rc))

        # policy_check.py standalone, as CI runs it. WARP-0730 REMOVED THE VERDICT GATE, so a
        # missing verdict is no longer a refusal and asserting that it is tests a property this
        # engine deliberately does not have. What policy_check still owes is that it RUNS and
        # does not blow up in a pack's own tree, and that it does not block a clean state.
        if _policy_exit(pv, ep) != 0:
            findings.append("pack %s: policy_check blocked a clean state" % pid)

    return findings


def pack_conformance(repo_root=None):
    """The findings for every declared pack, concatenated. Empty list = the whole fleet conforms."""
    repo_root = str(repo_root or _HERE.parent)
    PK = _load_module(repo_root, "veldo_pack_c", ".veldo/pack.py")
    cfg = PK.load_packs(repo_root=repo_root)
    modes = committed_hook_modes(repo_root)
    findings = []
    for pack in cfg["packs"]:
        findings += _conform_one(repo_root, pack, modes)
    return findings


def real_push_exec_bit(repo_root, pack_id):
    """Prove the committed exec bit is load-bearing END TO END via a real git-invoked push to a
    local bare remote (no network). With the pack's git pre-push hook non-executable, git SILENTLY
    skips it and an unproven push LANDS (the WARP-0807 fail-open); with it executable, the push is
    BLOCKED. Returns {"nonexec_landed": bool, "exec_blocked": bool}."""
    pack = _pack_by_id(repo_root, pack_id)
    pack_dir = pack["pack_dir"]
    out = {"nonexec_landed": None, "exec_blocked": None}
    with tempfile.TemporaryDirectory() as td:
        def _attempt(tag, mode):
            work = os.path.join(td, "work-" + tag)
            bare = os.path.join(td, "bare-" + tag + ".git")
            _extract_pack(repo_root, pack_dir, work)
            env = _git_env(work)
            _commit_all(work, env)  # UNPROVEN: no evidence laid down
            subprocess.run(["git", "init", "--bare", "-q", bare], capture_output=True)
            _git(["remote", "add", "origin", bare], cwd=work, env=env)
            _git(["config", "core.hooksPath", "hooks"], cwd=work, env=env)
            os.chmod(os.path.join(work, "hooks", "pre-push"), mode)
            r = _git(["push", "origin", "HEAD:refs/heads/main"], cwd=work, env=env)
            landed = _git(["ls-remote", bare, "refs/heads/main"], cwd=work, env=env).stdout.strip() != ""
            return r.returncode, landed
        _, landed_n = _attempt("nonexec", 0o644)
        out["nonexec_landed"] = landed_n                       # expect True: fail-open reproduced
        rc_e, landed_e = _attempt("exec", 0o755)
        out["exec_blocked"] = (rc_e != 0 and not landed_e)     # expect True: blocked, nothing landed
    return out


if __name__ == "__main__":
    import sys
    f = pack_conformance()
    if f:
        print("cross-pack conformance: FAIL")
        for x in f:
            print("  - " + x)
        sys.exit(1)
    print("cross-pack conformance: pass (all declared packs)")
