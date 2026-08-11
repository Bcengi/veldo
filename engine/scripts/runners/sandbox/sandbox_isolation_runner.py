#!/usr/bin/env python3
"""VELDO sandbox / isolation runner (reference).

Runs a flow inside a REAL container (a runtime such as docker or podman) and
asserts CONFINEMENT: the flow can read and write only within its declared mount
and path scope, and an ESCAPE ATTEMPT (reading or writing a host path outside
the allowed mounts) is DENIED. A sandbox is only as good as the escapes it
actually stops, so a happy-path test that only exercises the intended paths is
no proof. This runner drives the escape attempts themselves at the confined
flow and fails the run naming any host path that leaks through. A path the
journey requires DENIED but the sandbox ALLOWS is a CONFINEMENT BREACH: the
worst kind of silent green, an under-restricted sandbox.

  sandbox_isolation_runner.py <journey.json>
  sandbox_isolation_runner.py <journey.json> --fake   # in-process simulator

Journey format (JSON):

  {
    "name": "scoped mounts, escape denied",
    "image": "busybox:stable",
    "allowed_mounts": [
      {"path": "/data", "mode": "ro"},
      {"path": "/work", "mode": "rw"}
    ],
    "checks": [
      {"name": "read a declared input",
       "kind": "read", "path": "/data/input.json", "expect": "allowed"},
      {"name": "write into the read-only mount is refused",
       "kind": "write", "path": "/data/input.json", "expect": "denied"},
      {"name": "escape attempt: read a host secret is denied",
       "kind": "read", "path": "/etc/shadow", "expect": "denied"}
    ]
  }

A mount is {"path": "/abs", "mode": "ro"|"rw"} (a bare string "/abs" is a
read-only mount). allowed_mounts is the ONLY scope the flow is granted. A check
is a read or a write at an absolute container path with a required verdict:

  allowed  the flow must be able to reach the path. A read is allowed when the
           path falls within some declared mount; a write is allowed only within
           a read-write mount.
  denied   the flow must be refused. A read or write of a path outside every
           mount is denied, and a write into a read-only mount is denied.

The runner drives each check as a probe inside the container and compares the
observed verdict to the required one. A path required DENIED but observed
ALLOWED is a CONFINEMENT BREACH (the dangerous failure, named with the path); a
path required ALLOWED but observed DENIED is OVER-RESTRICTED (a usability
failure). Either disagreement fails the check and names it. A journey with no
checks asserts nothing and is a named journey error, never a silent pass. Exit
0 = every check matched its required verdict; exit 1 = at least one did not,
with the offending path and the direction of the failure on stdout.

The driver is a seam. The live ContainerDriver shells out to `docker run` (or
`podman run`) with only the declared mount scopes, a read-only root filesystem,
no network, and all capabilities dropped, so the confinement is enforced by the
real runtime. It FAILS LOUD when no runtime is installed rather than skipping.
The FakeContainerDriver simulates confinement deterministically in process (a
path is readable when it falls within a mount, writable when within a read-write
mount, denied otherwise), so the runner's control logic is gate-tested with no
container and no host filesystem access. Because the veldo home repository has no
container surface of its own to confine, this runner ships `reference`: an
adopting repo on a host with a working runtime wires the live driver to its own
image and the sandbox or isolation gate slot.
"""
import json
import os
import posixpath
import shutil
import subprocess
import sys
from pathlib import Path


# The probe: a POSIX-sh one-liner that tests reachability of a path inside the
# container. It runs in any image with /bin/sh. $1 is the kind, $2 the path.
# Exit 0 = the operation succeeded (allowed), exit 1 = it was refused (denied),
# exit 2 = an internal probe error (unknown kind), which the runner treats as a
# hard error, never a silent verdict.
PROBE_NAME = "veldo-sandbox-probe"
PROBE_SCRIPT = (
    'kind="$1"; target="$2"; '
    'if [ "$kind" = read ]; then '
    'test -r "$target"; '
    'elif [ "$kind" = write ]; then '
    'dir=$(dirname "$target"); test -d "$dir" && test -w "$dir" && : > "$target"; '
    'else echo "unknown probe kind: $kind" >&2; exit 2; fi'
)

VALID_KINDS = ("read", "write")
VALID_VERDICTS = ("allowed", "denied")
VALID_MODES = ("ro", "rw")


def build_probe(kind, path):
    """Return the argv that probes reachability of a path inside the container.

    Pure: the same argv is what the live driver runs in the container and what
    the fake driver recognizes, so the two agree on the protocol by sharing this
    builder rather than by parsing shell.
    """
    return ["sh", "-c", PROBE_SCRIPT, PROBE_NAME, kind, path]


def _within(path, mount):
    """True when an absolute container path falls within a mount path.

    Lexical (posix normpath, no filesystem access) so it is deterministic. A
    root mount ("/") contains everything; otherwise a path is inside a mount
    when it equals the mount or sits under mount + "/" (the trailing separator
    stops the /data vs /database prefix trap).
    """
    p = posixpath.normpath(path)
    m = posixpath.normpath(mount)
    if m == "/":
        return True
    return p == m or p.startswith(m + "/")


def confine(kind, path, mounts):
    """The confinement model: given the mounts a container was launched with,
    return the verdict ('allowed' or 'denied') a correctly-behaving sandbox
    produces for a read or write at path.

    A read is allowed within any mount; a write only within a read-write mount;
    anything outside every mount is denied. This is the SURFACE behavior the
    fake driver replays, kept separate from the runner's grading so the runner
    observes a result rather than narrating one. mounts is a list of normalized
    {'path', 'mode'} dicts.
    """
    containing = [m for m in mounts if _within(path, m["path"])]
    if not containing:
        return "denied"
    if kind == "read":
        return "allowed"
    # write
    return "allowed" if any(m["mode"] == "rw" for m in containing) else "denied"


def classify(result):
    """Map a driver result to (verdict, error).

    Exit 0 = allowed, exit 1 = denied (the probe ran and the operation was
    refused). Any other code, a None code, or an explicit driver error is an
    ERROR, not a verdict, so a container that failed to start cannot masquerade
    as a clean 'denied'. Returns (verdict|None, error_str|None).
    """
    if result.get("error"):
        return None, result["error"]
    code = result.get("exit_code")
    if code == 0:
        return "allowed", None
    if code == 1:
        return "denied", None
    stderr = (result.get("stderr") or "").strip()
    return None, f"probe exited {code!r} (not a clean allowed/denied): {stderr}"


def normalize_mount(m):
    """Normalize a mount entry to {'path', 'mode'} or raise ValueError.

    A bare string is a read-only mount. A dict must carry an absolute 'path' and
    an optional 'mode' of ro or rw (default ro).
    """
    if isinstance(m, str):
        path, mode = m, "ro"
    elif isinstance(m, dict):
        path = m.get("path")
        mode = m.get("mode", "ro")
    else:
        raise ValueError(f"mount must be a string or object, got {type(m).__name__}")
    if not isinstance(path, str) or not path.startswith("/"):
        raise ValueError(f"mount path must be an absolute path, got {path!r}")
    if mode not in VALID_MODES:
        raise ValueError(f"mount mode must be one of {VALID_MODES}, got {mode!r}")
    return {"path": path, "mode": mode}


def validate_journey(journey):
    """Return an error string if the journey cannot prove confinement, else None.

    A journey with no checks asserts nothing and is rejected (the most common
    rubber-stamp). image and allowed_mounts must be well formed.
    """
    if not isinstance(journey.get("image"), str) or not journey["image"].strip():
        return "journey has no 'image' (a container image name is required)"
    mounts = journey.get("allowed_mounts")
    if not isinstance(mounts, list):
        return "journey 'allowed_mounts' must be a list (may be empty for no scope)"
    try:
        [normalize_mount(m) for m in mounts]
    except ValueError as e:
        return f"invalid mount in allowed_mounts: {e}"
    checks = journey.get("checks")
    if not isinstance(checks, list) or not checks:
        return (f"journey {journey.get('name')!r} declares no checks; a journey "
                "that asserts nothing cannot prove confinement")
    return None


def validate_check(check):
    """Return an error string if the check is malformed, else None."""
    if check.get("kind") not in VALID_KINDS:
        return f"check 'kind' must be one of {VALID_KINDS}, got {check.get('kind')!r}"
    path = check.get("path")
    if not isinstance(path, str) or not path.startswith("/"):
        return f"check 'path' must be an absolute container path, got {path!r}"
    if check.get("expect") not in VALID_VERDICTS:
        return f"check 'expect' must be one of {VALID_VERDICTS}, got {check.get('expect')!r}"
    return None


def grade_check(check, observed, error=None):
    """Compare the observed verdict to the required one.

    Pure (no I/O): returns a failure string or None. A driver error is a hard
    failure. A path required DENIED but observed ALLOWED is a CONFINEMENT BREACH
    named with the path; a path required ALLOWED but observed DENIED is
    OVER-RESTRICTED. The breach direction is the load-bearing one: an
    under-restricted sandbox is the defect this runner exists to catch.
    """
    kind = check.get("kind")
    path = check.get("path")
    expect = check.get("expect")
    if error is not None:
        return f"driver error probing {kind} of {path!r}: {error}"
    if observed == expect:
        return None
    if expect == "denied" and observed == "allowed":
        return (f"CONFINEMENT BREACH: {kind} of host path {path!r} was ALLOWED but "
                "the journey requires it DENIED (the sandbox did not confine it; "
                "an over-broad mount or missing scope let it escape)")
    return (f"OVER-RESTRICTED: {kind} of {path!r} was DENIED but the journey "
            "requires it ALLOWED (the declared mount scope is too narrow)")


def run_journey(journey, driver, out=None):
    """Drive every check through the container driver and grade it.

    Returns {"passed": bool, "checks": [...], "error": str|None}. When out is
    given, prints PASS/FAIL lines naming any breach, over-restriction, or config
    error. Every check runs so every breach is reported, not just the first.
    """
    result = {"journey": journey.get("name"), "passed": True, "checks": [], "error": None}
    jerr = validate_journey(journey)
    if jerr:
        result["passed"] = False
        result["error"] = jerr
        if out is not None:
            print(f"JOURNEY ERROR: {jerr}", file=out)
        return result
    mounts = [normalize_mount(m) for m in journey["allowed_mounts"]]
    image = journey["image"]
    for check in journey["checks"]:
        name = check.get("name") or f"{check.get('kind')} {check.get('path')!r}"
        cerr = validate_check(check)
        if cerr:
            failure = f"config error: {cerr}"
        else:
            res = driver.run(image, build_probe(check["kind"], check["path"]), mounts)
            observed, derr = classify(res)
            failure = grade_check(check, observed, error=derr)
        ok = failure is None
        result["checks"].append({"check": name, "ok": ok, "failure": failure})
        if out is not None:
            if ok:
                print(f"PASS  {name}", file=out)
            else:
                print(f"FAIL  {name}: {failure}", file=out)
        if not ok:
            result["passed"] = False
    return result


# container drivers

def detect_runtime():
    """Return the name of an available container runtime, or None."""
    for name in ("docker", "podman"):
        if shutil.which(name):
            return name
    return None


def require_runtime(runtime):
    """Return the runtime name or raise LOUD when none is available.

    Split out so the fail-loud contract is testable without a runtime installed.
    """
    if not runtime:
        raise RuntimeError(
            "no container runtime found: install docker or podman and put it on "
            "PATH. The sandbox runner needs a real container to enforce "
            "confinement; its control logic is unit-tested with the in-process "
            "FakeContainerDriver, but a live run cannot be faked.")
    return runtime


class ContainerDriver:
    """Live driver: `docker run` (or `podman run`) with only the declared mount
    scopes, a read-only root filesystem, no network, and every capability
    dropped, so confinement is enforced by the real runtime. Fails loud in the
    constructor when no runtime is present."""

    def __init__(self, runtime=None, timeout=60):
        self.runtime = require_runtime(runtime or detect_runtime())
        self.timeout = timeout

    def run(self, image, argv, mounts):
        cmd = [self.runtime, "run", "--rm", "--read-only",
               "--network", "none", "--cap-drop", "ALL",
               "--security-opt", "no-new-privileges"]
        for m in mounts:
            cmd += ["-v", f"{m['path']}:{m['path']}:{m['mode']}"]
        cmd += [image] + list(argv)
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout)
        except FileNotFoundError as e:
            return {"exit_code": None, "stdout": "", "stderr": str(e),
                    "error": f"runtime {self.runtime!r} not executable: {e}"}
        except subprocess.TimeoutExpired as e:
            return {"exit_code": None, "stdout": e.stdout or "", "stderr": e.stderr or "",
                    "error": f"container timed out after {self.timeout}s"}
        return {"exit_code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}


class FakeContainerDriver:
    """In-process confinement simulator for the gate: models a container
    launched with exactly `mounts` (a path is readable within a mount, writable
    within a read-write mount, denied otherwise), so the runner's control logic
    is exercised with no container and no host filesystem access. It recognizes
    the shared probe by argv shape and never touches the real filesystem."""

    def __init__(self):
        self.calls = []

    def run(self, image, argv, mounts):
        self.calls.append((image, tuple(argv),
                           tuple((m["path"], m["mode"]) for m in mounts)))
        if not (len(argv) >= 6 and argv[0] == "sh" and argv[2] == PROBE_SCRIPT
                and argv[3] == PROBE_NAME):
            return {"exit_code": 2, "stdout": "", "stderr": f"unrecognized probe: {argv!r}"}
        kind, path = argv[4], argv[5]
        if kind not in VALID_KINDS:
            return {"exit_code": 2, "stdout": "", "stderr": f"unknown probe kind: {kind}"}
        verdict = confine(kind, path, mounts)
        if verdict == "allowed":
            return {"exit_code": 0, "stdout": "VELDO_PROBE_OK\n", "stderr": ""}
        return {"exit_code": 1, "stdout": "",
                "stderr": f"{kind} {path}: operation not permitted (outside sandbox scope)\n"}


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    flags = {a for a in argv[1:] if a.startswith("--")}
    if not args:
        print(__doc__)
        return 2
    journey = json.loads(Path(args[0]).read_text())
    use_fake = "--fake" in flags or os.environ.get("VELDO_SANDBOX_DRIVER") == "fake"
    if use_fake:
        driver = FakeContainerDriver()
    else:
        driver = ContainerDriver(runtime=os.environ.get("VELDO_CONTAINER_RUNTIME"))
    summary = run_journey(journey, driver, out=sys.stdout)
    total = len(summary["checks"])
    passed = sum(1 for c in summary["checks"] if c["ok"])
    breaches = sum(1 for c in summary["checks"]
                   if c["failure"] and "CONFINEMENT BREACH" in c["failure"])
    tail = f"; {breaches} CONFINEMENT BREACH(es)" if breaches else ""
    if summary["error"]:
        print(f"sandbox isolation runner: JOURNEY ERROR ({summary['error']})")
    else:
        print(f"sandbox isolation runner: {passed}/{total} checks matched their required verdict{tail}")
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
