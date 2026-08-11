#!/usr/bin/env python3
"""Ephemeral environment and fixture provisioning (F3 of PLAN-0004).

The runners drive a surface; this gives them a CLEAN surface with seeded data
to drive, then takes it away. The value is not the surface itself (a database,
a filesystem sandbox, a container) but the four guarantees a runner may lean on
no matter which surface backs it:

  1. an environment is CLEAN on create (no leftover state from a prior run),
  2. seeding is applied and observable,
  3. teardown is idempotent (a second teardown does not error) and leaves
     nothing behind, and
  4. a create-without-teardown is DETECTABLE - a leaked environment is a named
     failure, not a silent resource left running.

The seam is EnvProvisioner: create() -> handle, seed(handle, fixtures),
observe(handle), paths(handle), teardown(handle). The base owns the lifecycle
and leak accounting so every backend detects a leak the same way; a subclass
implements only the surface primitives. Crucially the base ties liveness and
teardown to a REAL observation of the surface (_is_live), never to its own
bookkeeping, so a backend that pretends to tear down while leaving the resource
running is still caught as a leak - the exact non-tautology this module owes.

Two backends ship:

  FakeProvisioner        a deterministic in-memory surface (a dict of buckets)
                         for the gate: the control logic is exercised end to end
                         with no external dependency.

  ContainerEnvProvisioner  the live reference: an ephemeral environment backed by
                         a container the adopting repo names (its own image and
                         seed). It FAILS LOUD when no container runtime is on
                         PATH, so an absent surface is never a silent skip. The
                         veldo home repo ships no image of its own, so it does not
                         run this; an adopting repo wires it to its container and
                         fixtures.

Stdlib only. No new service, no hosting stack.

  python3 .veldo/env_provision.py selfcheck   # drive the fake through the loop
"""
import argparse
import json
import shutil
import subprocess
import sys
import uuid


class EnvProvisionUnavailable(RuntimeError):
    """Raised loudly when the live surface (a container runtime, etc.) is absent.

    A reference capability must fail here, never degrade to a no-op that reports
    a clean run against nothing.
    """


class EnvStateError(RuntimeError):
    """Raised when an environment is used after it is gone (observed torn down)."""


class EnvHandle:
    """An opaque reference to one provisioned environment.

    Carries only identity and the surface-supplied access coordinates; all
    lifecycle state of record lives at the surface, read back via _is_live.
    """

    def __init__(self, env_id, kind, paths=None):
        self.env_id = env_id
        self.kind = kind
        self.paths = dict(paths or {})

    def __repr__(self):
        return f"EnvHandle({self.env_id!r}, kind={self.kind!r})"


class EnvProvisioner:
    """The provisioning seam and its lifecycle/leak bookkeeping.

    Subclasses implement the surface primitives (_create, _seed, _observe,
    _paths, _teardown, _is_live). The public methods here add the guarantees
    every backend must uphold, so the runner asserts against the seam and not
    against any one surface.
    """

    def __init__(self):
        # Every handle ever created, so a create-without-teardown is detectable
        # by re-observing the surface, not by trusting a decrement here.
        self._created = []

    # --- surface primitives a subclass MUST implement ----------------------
    def _create(self):
        raise NotImplementedError

    def _seed(self, handle, fixtures):
        raise NotImplementedError

    def _observe(self, handle):
        raise NotImplementedError

    def _paths(self, handle):
        raise NotImplementedError

    def _teardown(self, handle):
        raise NotImplementedError

    def _is_live(self, handle):
        """True while the underlying surface for this handle still exists.

        This is the source of truth for cleanliness, teardown, and leaks; it
        MUST observe the real surface, never a flag the base set.
        """
        raise NotImplementedError

    # --- the guaranteed lifecycle ------------------------------------------
    def create(self):
        handle = self._create()
        self._created.append(handle)
        return handle

    def seed(self, handle, fixtures):
        if not self._is_live(handle):
            raise EnvStateError(f"cannot seed {handle.env_id}: environment is not live")
        self._seed(handle, fixtures)

    def observe(self, handle):
        """Read the environment's current state.

        Fails LOUD once the surface is gone, so an observation after teardown
        can never quietly return stale seeded data and read as still present.
        """
        if not self._is_live(handle):
            raise EnvStateError(
                f"cannot observe {handle.env_id}: environment is not live "
                "(torn down or never created)")
        return self._observe(handle)

    def paths(self, handle):
        return self._paths(handle)

    def teardown(self, handle):
        """Remove the environment. Idempotent: a second call is a no-op.

        The base always delegates to _teardown; there is no early return on a
        flag, because the leak check re-observes the surface and a backend that
        pretends to tear down must still be caught.
        """
        self._teardown(handle)

    def leaked(self):
        """env_ids created but still live at the surface (leaked environments).

        A leaked environment is named here, so a run that forgets teardown or a
        backend whose teardown does not actually remove the surface is a failure,
        not a silent resource left running.
        """
        return sorted(h.env_id for h in self._created if self._is_live(h))


class FakeProvisioner(EnvProvisioner):
    """Deterministic in-memory provisioner for the gate.

    The surface is a dict keyed by env id. create allocates a fresh EMPTY bucket
    (clean on create), seed appends fixture rows, observe reads them back,
    teardown deletes the bucket, and liveness is bucket existence. Because
    liveness is real bucket existence and not a flag, a subclass whose teardown
    does not delete the bucket is detected as a leak.
    """

    def __init__(self):
        super().__init__()
        self._surface = {}
        self._counter = 0

    def _create(self):
        self._counter += 1
        env_id = f"fake-env-{self._counter}"
        # clean on create: a brand-new bucket with no leftover rows.
        self._surface[env_id] = {"rows": []}
        return EnvHandle(env_id, kind="fake", paths={"url": f"memory://{env_id}"})

    def _seed(self, handle, fixtures):
        bucket = self._surface[handle.env_id]
        for row in (fixtures or {}).get("rows", []):
            bucket["rows"].append(row)

    def _observe(self, handle):
        return list(self._surface[handle.env_id]["rows"])

    def _paths(self, handle):
        return dict(handle.paths)

    def _teardown(self, handle):
        # idempotent: popping an already-absent bucket is not an error.
        self._surface.pop(handle.env_id, None)

    def _is_live(self, handle):
        return handle.env_id in self._surface


def _default_runtime_finder():
    """Return the first container runtime on PATH, or None if none is present."""
    for candidate in ("docker", "podman"):
        path = shutil.which(candidate)
        if path:
            return path
    return None


class ContainerEnvProvisioner(EnvProvisioner):
    """Live reference: an ephemeral environment backed by a container.

    An adopting repo names its own image (with its own seed baked in or applied
    through seed_cmd) and points a runner at the resulting url. This backend
    FAILS LOUD via EnvProvisionUnavailable when no container runtime is on PATH,
    so an absent surface is a named error rather than a run that reports clean
    against nothing. It shells the runtime through injectable seams (runtime
    finder and a run function) so the fail-loud guard is provable without a
    live daemon, and the veldo home repo - which ships no image - does not run it.
    """

    def __init__(self, image, port=None, seed_cmd=None,
                 runtime_finder=None, run=None):
        super().__init__()
        self._image = image
        self._port = port
        self._seed_cmd = list(seed_cmd or [])
        self._find_runtime = runtime_finder or _default_runtime_finder
        self._run = run or self._run_subprocess
        self._runtime = None

    @staticmethod
    def _run_subprocess(args):
        return subprocess.run(args, capture_output=True, text=True)

    def _runtime_or_fail(self):
        if self._runtime is None:
            self._runtime = self._find_runtime()
        if not self._runtime:
            raise EnvProvisionUnavailable(
                "no container runtime found (looked for docker, podman on PATH); "
                "ephemeral_env_provisioning is a reference capability - an adopting "
                "repo must provide a container runtime and its own image")
        return self._runtime

    def _create(self):
        runtime = self._runtime_or_fail()
        env_id = f"veldo-env-{uuid.uuid4().hex[:12]}"
        args = [runtime, "run", "-d", "--rm", "--name", env_id]
        if self._port:
            args += ["-p", f"{self._port}"]
        args += [self._image]
        result = self._run(args)
        if getattr(result, "returncode", 1) != 0:
            raise EnvProvisionUnavailable(
                f"container start failed for {self._image}: "
                f"{getattr(result, 'stderr', '') or 'no detail'}")
        paths = {"container": env_id}
        if self._port:
            paths["url"] = f"http://127.0.0.1:{str(self._port).split(':')[0]}"
        return EnvHandle(env_id, kind="container", paths=paths)

    def _seed(self, handle, fixtures):
        if not self._seed_cmd:
            return
        runtime = self._runtime_or_fail()
        result = self._run([runtime, "exec", handle.env_id] + self._seed_cmd)
        if getattr(result, "returncode", 1) != 0:
            raise EnvProvisionUnavailable(
                f"seed command failed in {handle.env_id}: "
                f"{getattr(result, 'stderr', '') or 'no detail'}")

    def _observe(self, handle):
        runtime = self._runtime_or_fail()
        result = self._run([runtime, "inspect", "--format", "{{.State.Running}}",
                            handle.env_id])
        return {"running": (getattr(result, "stdout", "") or "").strip() == "true"}

    def _paths(self, handle):
        return dict(handle.paths)

    def _teardown(self, handle):
        runtime = self._runtime_or_fail()
        # --rm containers are removed on stop; force removal is idempotent and
        # tolerates an already-absent container so a second teardown is a no-op.
        self._run([runtime, "rm", "-f", handle.env_id])

    def _is_live(self, handle):
        runtime = self._runtime_or_fail()
        result = self._run([runtime, "inspect", "--format", "{{.State.Running}}",
                            handle.env_id])
        if getattr(result, "returncode", 1) != 0:
            return False
        return (getattr(result, "stdout", "") or "").strip() == "true"


def _fixtures_present(observed, fixtures):
    """True when every seeded row is visible in the observed state."""
    want = (fixtures or {}).get("rows", [])
    if not want:
        return False
    have = observed if isinstance(observed, list) else []
    return all(row in have for row in want)


def verify_provisioner(provisioner, fixtures):
    """Drive one provisioner through the full guaranteed lifecycle.

    Returns a report {passed, checks:[{name, ok, detail}]}. Every check is a real
    observation of the surface, so a provisioner that ignores seeding or skips a
    real teardown fails a named check and cannot pass vacuously.
    """
    report = {"passed": True, "checks": []}

    def check(name, ok, detail=""):
        report["checks"].append({"name": name, "ok": bool(ok), "detail": detail})
        if not ok:
            report["passed"] = False

    handle = provisioner.create()

    # G1: clean on create - a fresh environment has no leftover state.
    before = provisioner.observe(handle)
    check("clean_on_create", before == [] or before == {} or not before,
          f"expected empty, observed {before!r}")

    # G2: seeding is applied and observable.
    provisioner.seed(handle, fixtures)
    after = provisioner.observe(handle)
    check("seed_observable", _fixtures_present(after, fixtures),
          f"seeded rows not observed; observed {after!r}")

    # access coordinates are available for a runner to drive.
    check("paths_available", bool(provisioner.paths(handle)),
          "no url/paths returned for the environment")

    # G3a: teardown leaves nothing - observing a torn-down env fails loud.
    provisioner.teardown(handle)
    try:
        provisioner.observe(handle)
        check("gone_after_teardown", False,
              "environment still observable after teardown")
    except EnvStateError:
        check("gone_after_teardown", True)

    # G3b: teardown is idempotent - a second teardown does not error.
    try:
        provisioner.teardown(handle)
        check("teardown_idempotent", True)
    except Exception as exc:  # noqa: BLE001 - any error here is the failure
        check("teardown_idempotent", False, f"second teardown raised {exc!r}")

    # G4: no leak once a properly torn-down env is accounted for.
    leaked = provisioner.leaked()
    check("no_leak_after_teardown", leaked == [], f"leaked environments: {leaked}")

    return report


def selfcheck():
    """Run the fake provisioner through the guarantees and report (exit 0/1)."""
    report = verify_provisioner(FakeProvisioner(), {"rows": [{"id": 1}, {"id": 2}]})
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="ephemeral environment provisioning")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selfcheck", help="drive the fake provisioner through the guarantees")
    args = ap.parse_args(argv)
    if args.cmd == "selfcheck":
        return selfcheck()
    return 2


if __name__ == "__main__":
    sys.exit(main())
