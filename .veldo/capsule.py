"""Reproduction capsules: the reviewer's own reproduction of a defect, saved byte for byte and run
again later against the commit it reviewed and against the commit that claims to fix it (VELDO-0101).

A capsule is a directory. It holds manifest.json and the reviewer's files exactly as the reviewer
wrote them: the script, its fixtures, the command that runs it, and the observation the reviewer
made. The manifest carries a SHA-256 digest of every file in the directory. Loading a capsule
verifies every digest and refuses a directory whose bytes do not match, whose manifest names a file
that is missing, or which contains a file the manifest does not digest. Running a capsule copies the
named commit into a fresh temporary directory, places the capsule beside it under .capsule/, runs the
saved command there with a deadline, and compares what happened against the expected observation in
a SEPARATE function. The runner never edits the reviewer's files: their digests are checked again
after the run and a change is an error, not a result.

Standard library only. The review brief that tells the reviewer to save capsules is the text
brief_text() returns; the review script appends it to its prompt when this file is present in the
repository under review.

    python3 .veldo/capsule.py brief
    python3 .veldo/capsule.py check <capsule-dir>
    python3 .veldo/capsule.py run <capsule-dir> <repo> <commit> [--timeout SECONDS]
"""
from __future__ import annotations

# Load the shared Git boundary by sibling path, including when imported by file location.
import importlib.util as _git_importlib
from pathlib import Path as _GitPath
_git_spec = _git_importlib.spec_from_file_location("veldo_git_process", _GitPath(__file__).resolve().with_name("git_process.py"))
_git_process = _git_importlib.module_from_spec(_git_spec)
_git_spec.loader.exec_module(_git_process)

import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

SCHEMA = "veldo.capsule/v1"
MANIFEST = "manifest.json"
CAPSULE_ROOT = ".veldo-review/capsules"     # where the reviewer writes them inside its worktree
MOUNT = ".capsule"                          # where the runner places the capsule beside the checkout
# A capsule names the commit it was taken at, and every consumer of a capsule puts that string into a
# git argument list. Git reads a leading dash as an option, so this is a commit id and nothing else:
# the same rule the plan's own commit fields follow, at the other place a commit enters this system.
COMMIT_ISH = __import__("re").compile(r"[0-9a-fA-F]{7,40}")
EXPECTATION_KINDS = ("exit_code", "stdout_contains", "stderr_contains", "output_contains", "file_exists")
KILL_WAIT = 5  # seconds the runner waits for the killed group's pipes to close before recording a survivor
DEFAULT_TIMEOUT = 300


class CapsuleError(Exception):
    """A capsule that cannot be trusted: bytes changed, a file missing, an undigested file present, a
    malformed manifest, or a runner that altered the reviewer's files."""


# --------------------------------------------------------------------------------------------------
# The brief. One paragraph the reviewer reads before it writes its first finding.
# --------------------------------------------------------------------------------------------------

def brief_text() -> str:
    return (
        "REPRODUCTIONS ARE SAVED, NOT DESCRIBED. For every defect you confirm, before you write the finding, "
        f"save the reproduction as files under {CAPSULE_ROOT}/<finding-id>/ inside this worktree: the script "
        "that exposes the defect, any fixtures it needs, and manifest.json with the fields finding_id, "
        "reviewed_commit, command (the exact argument list that runs the script from the repository root, with "
        f"the capsule mounted at {MOUNT}/), expected (one of {', '.join(EXPECTATION_KINDS)} with its value, "
        "the observation that shows the defect), and observation (what you saw, in one or two sentences). "
        "Write the files exactly as you ran them; a later runner executes the same command against the same "
        "commit and against the fix, and it never rewrites your files. A finding without a capsule is reported "
        "as UNCONFIRMED, not as a finding. Saving the capsule is part of the review, not a follow-up. "
        "reviewed_commit is the COMMIT ID you read, seven to forty hexadecimal characters, not HEAD or a branch "
        "name: a later runner passes it to git as an argument, and git reads a name beginning with a dash as an option."
    )


# --------------------------------------------------------------------------------------------------
# Digests and loading
# --------------------------------------------------------------------------------------------------

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _files_under(root: Path):
    for p in sorted(root.rglob("*")):
        if p.is_file() and not p.is_symlink():
            yield p.relative_to(root).as_posix()


def _symlinks_under(root: Path) -> list:
    """Every symbolic link below root (file or directory), by relative path. rglob does not descend into
    a linked directory and is_file() is false for it, so a link is neither digested nor counted as an
    extra file unless it is looked for by name; a capsule may not carry one."""
    out = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in dirnames + filenames:
            p = Path(dirpath) / name
            if p.is_symlink():
                out.append(p.relative_to(root).as_posix())
    return sorted(out)


def capsule_digest(manifest: dict) -> str:
    """One digest for the whole capsule as it will run: the file digests AND the command and the expected
    observation from the manifest, which are the only bytes the file digests do not cover."""
    blob = json.dumps({"files": manifest.get("files"), "command": manifest.get("command"), "expected": manifest.get("expected")}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


def digest_files(capsule_dir: str | os.PathLike) -> dict:
    """Digest every file in the directory except the manifest itself."""
    root = Path(capsule_dir)
    return {rel: _sha256(root / rel) for rel in _files_under(root) if rel != MANIFEST}


def write_manifest(capsule_dir: str | os.PathLike, finding_id: str, reviewed_commit: str, command: list,
                   expected: dict, observation: str) -> dict:
    """Write manifest.json for a capsule directory the reviewer has already populated. Used by the
    reviewer's tooling and by tests; the digests are computed from the bytes on disk."""
    root = Path(capsule_dir)
    if not isinstance(command, list) or not command or not all(isinstance(a, str) for a in command):
        raise CapsuleError("command must be a non-empty list of strings")
    if not isinstance(expected, dict) or expected.get("kind") not in EXPECTATION_KINDS:
        raise CapsuleError(f"expected.kind must be one of {EXPECTATION_KINDS}")
    if not isinstance(reviewed_commit, str) or not COMMIT_ISH.fullmatch(reviewed_commit):
        raise CapsuleError(f"reviewed_commit must be a commit id, 7 to 40 hexadecimal characters, not {str(reviewed_commit)[:80]!r}")
    m = {
        "schema": SCHEMA,
        "finding_id": finding_id,
        "reviewed_commit": reviewed_commit,
        "command": command,
        "expected": expected,
        "observation": observation,
        "files": digest_files(root),
    }
    (root / MANIFEST).write_text(json.dumps(m, indent=1, sort_keys=True) + "\n")
    return m


def load_capsule(capsule_dir: str | os.PathLike) -> dict:
    """Read and verify a capsule. Every file the manifest names must exist with the digest recorded;
    every file present must be named. The manifest itself is validated for shape."""
    root = Path(capsule_dir)
    mp = root / MANIFEST
    if not mp.is_file():
        raise CapsuleError(f"no {MANIFEST} in {root}")
    try:
        m = json.loads(mp.read_text())
    except (OSError, ValueError) as e:
        raise CapsuleError(f"unreadable manifest: {e}")
    if not isinstance(m, dict) or m.get("schema") != SCHEMA:
        raise CapsuleError(f"manifest schema must be {SCHEMA}")
    for field in ("finding_id", "reviewed_commit", "command", "expected", "observation", "files"):
        if field not in m:
            raise CapsuleError(f"manifest lacks {field}")
    if not isinstance(m["command"], list) or not m["command"] or not all(isinstance(a, str) for a in m["command"]):
        raise CapsuleError("manifest command must be a non-empty list of strings")
    if not isinstance(m["reviewed_commit"], str) or not COMMIT_ISH.fullmatch(m["reviewed_commit"]):
        # Checked on the way IN and again on the way OUT: the first stops a mistake, the second stops a
        # file that was written by something else, which is what a capsule read off disk always is.
        raise CapsuleError(f"manifest reviewed_commit must be a commit id, not {str(m['reviewed_commit'])[:80]!r}")
    if not isinstance(m["expected"], dict) or m["expected"].get("kind") not in EXPECTATION_KINDS:
        raise CapsuleError(f"manifest expected.kind must be one of {EXPECTATION_KINDS}")
    if not isinstance(m["files"], dict) or not m["files"]:
        raise CapsuleError("manifest must digest at least one file")
    links = _symlinks_under(root)
    if links:
        raise CapsuleError(f"capsule {root.name} carries symbolic links, which the digests cannot cover: {links}")
    actual = digest_files(root)
    missing = sorted(set(m["files"]) - set(actual))
    extra = sorted(set(actual) - set(m["files"]))
    changed = sorted(rel for rel in set(m["files"]) & set(actual) if m["files"][rel] != actual[rel])
    if missing or extra or changed:
        raise CapsuleError(f"capsule {root.name} does not match its manifest: missing={missing} undigested={extra} changed={changed}")
    return m


# --------------------------------------------------------------------------------------------------
# Running
# --------------------------------------------------------------------------------------------------

def _checkout(repo: str | os.PathLike, commit: str, dest: Path) -> None:
    """Copy the tree of <commit> into dest with git archive. The repository itself is never the run
    directory."""
    dest.mkdir(parents=True, exist_ok=True)
    ar = _git_process.run(["git", "-C", str(repo), "archive", "--format=tar", commit], capture_output=True, timeout=120)
    if ar.returncode != 0:
        raise CapsuleError(f"git archive {commit} failed: {ar.stderr.decode('utf-8', 'replace')[:300]}")
    tar = subprocess.run(["tar", "-x", "-C", str(dest)], input=ar.stdout, capture_output=True, timeout=120)
    if tar.returncode != 0:
        raise CapsuleError(f"untar failed: {tar.stderr.decode('utf-8', 'replace')[:300]}")


def observation_matches(expected: dict, result: dict) -> bool:
    """The decisive comparison, kept apart from execution so that it can be read and tested alone.
    'reproduced' means the run showed the defect the reviewer described."""
    kind, value = expected.get("kind"), expected.get("value")
    if kind == "exit_code":
        return result.get("exit_code") == int(value)
    if kind == "stdout_contains":
        return str(value) in (result.get("stdout") or "")
    if kind == "stderr_contains":
        return str(value) in (result.get("stderr") or "")
    if kind == "output_contains":
        return str(value) in ((result.get("stdout") or "") + (result.get("stderr") or ""))
    if kind == "file_exists":
        return bool(result.get("files_present", {}).get(str(value)))
    return False


def run_capsule(capsule_dir: str | os.PathLike, repo: str | os.PathLike, commit: str, timeout: int = DEFAULT_TIMEOUT,
                workdir: str | os.PathLike | None = None) -> dict:
    """Run a verified capsule against <commit> of <repo> in a fresh directory. Returns a result record:
    reproduced (the observation matched), exit_code, stdout and stderr tails, duration, timed_out, and
    the digests of the capsule files before and after the run (they must be identical)."""
    m = load_capsule(capsule_dir)
    # The reference for every later comparison is the MANIFEST's digests, which load_capsule has just
    # verified against the bytes on disk. Re-reading the directory here would open a window in which a
    # byte could change and every comparison would still agree, each with the changed bytes.
    before = m["files"]
    root = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="capsule-run-"))
    tree = root / "tree"
    _checkout(repo, commit, tree)
    mount = tree / MOUNT
    if mount.exists():
        raise CapsuleError(f"the commit already carries {MOUNT} at its root; the capsule cannot be mounted there")
    shutil.copytree(capsule_dir, mount, symlinks=True)
    mounted = digest_files(mount)
    if mounted != before:
        raise CapsuleError(f"the mounted copy does not match the manifest: {sorted(k for k in set(before) | set(mounted) if before.get(k) != mounted.get(k))}")
    # The checkout root goes first on PYTHONPATH so a reproduction can import the code it exposes the
    # way the reviewer did from the repository root; nothing else about the environment is changed.
    env = dict(os.environ, VELDO_CAPSULE_DIR=str(mount), VELDO_CAPSULE_COMMIT=commit)
    env.pop("PWD", None)
    env["PYTHONPATH"] = str(tree) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    import time
    t0 = time.monotonic()
    timed_out = False
    # The command runs as the leader of a new process group. On the deadline the WHOLE group is killed,
    # not only the command: a reproduction that spawned helpers must leave nothing running behind it,
    # and a helper holding the output pipe must not keep the runner waiting after the command is dead.
    p = subprocess.Popen(m["command"], cwd=str(tree), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    children_left_running = False
    try:
        out_b, err_b = p.communicate(timeout=timeout)
        exit_code = p.returncode
    except subprocess.TimeoutExpired:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        # A helper that left the process group and still holds the output pipe would keep this wait
        # open forever; the wait after the kill is bounded and such a survivor is recorded by name.
        try:
            out_b, err_b = p.communicate(timeout=KILL_WAIT)
        except subprocess.TimeoutExpired:
            children_left_running = True
            p.kill()
            out_b, err_b = b"", b""
            try:
                p.wait(timeout=1)
            except subprocess.TimeoutExpired:
                pass
        timed_out, exit_code = True, None
    out, err = out_b.decode("utf-8", "replace"), err_b.decode("utf-8", "replace")
    duration = time.monotonic() - t0
    files_present = {}
    fe = m["expected"].get("value") if m["expected"].get("kind") == "file_exists" else None
    if fe:
        # The path a capsule names is confined to the checkout the same way a plan's paths are: an
        # absolute path or one through .. would ask about a file outside the copy, and the answer to
        # that question is never evidence about this commit.
        rel = str(fe)
        inside = not rel.startswith(("/", "\\")) and ".." not in Path(rel).parts
        target = (tree / rel) if inside else None
        try:
            inside = inside and target.resolve().relative_to(tree.resolve()) is not None
        except ValueError:
            inside = False
        files_present[rel] = bool(inside and target.exists())
    after = digest_files(capsule_dir)
    if after != before:
        raise CapsuleError(f"the run changed the reviewer's files: {sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))}")
    result = {
        "schema": "veldo.capsule-run/v1",
        "finding_id": m["finding_id"],
        "capsule_digest": capsule_digest(m),
        "commit": commit,
        "command": m["command"],
        "exit_code": exit_code,
        "timed_out": timed_out,
        "children_left_running": children_left_running,
        "duration_seconds": round(duration, 3),
        "stdout": out,
        "stderr": err,
        "files_present": files_present,
    }
    # The observation is judged over the WHOLE output; only the record keeps a tail.
    result["reproduced"] = (not timed_out) and observation_matches(m["expected"], result)
    result["stdout"], result["stderr"] = out[-4000:], err[-4000:]
    result["output_truncated"] = len(out) > 4000 or len(err) > 4000
    return result


# --------------------------------------------------------------------------------------------------
# Command line
# --------------------------------------------------------------------------------------------------

def main(argv: list) -> int:
    if len(argv) >= 2 and argv[1] == "brief":
        print(brief_text())
        return 0
    if len(argv) == 3 and argv[1] == "check":
        try:
            m = load_capsule(argv[2])
        except CapsuleError as e:
            print(f"REFUSED: {e}")
            return 2
        print(f"OK {m['finding_id']} reviewed at {m['reviewed_commit']}: {len(m['files'])} file(s) verified")
        return 0
    if len(argv) >= 5 and argv[1] == "run":
        timeout = DEFAULT_TIMEOUT
        if "--timeout" in argv:
            timeout = int(argv[argv.index("--timeout") + 1])
        try:
            r = run_capsule(argv[2], argv[3], argv[4], timeout=timeout)
        except CapsuleError as e:
            print(f"REFUSED: {e}")
            return 2
        print(json.dumps(r, indent=1, sort_keys=True))
        return 0 if r["reproduced"] else 1
    print(__doc__)
    return 64


if __name__ == "__main__":
    sys.exit(main(sys.argv))
