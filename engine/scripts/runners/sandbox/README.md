# Veldo sandbox / isolation runner (reference)

A generic runner for the sandbox surface: it runs a flow inside a REAL container
(a runtime such as docker or podman) and asserts CONFINEMENT. The flow can read
and write only within its declared mount and path scope, and an escape attempt
(reading or writing a host path outside the allowed mounts) is denied. A sandbox
is only as good as the escapes it actually stops, so a happy-path test that only
touches the intended paths is no proof. This runner drives the escape attempts
themselves and fails the run naming any host path that leaks through. It uses
only the Python standard library.

## Use

```
sandbox_isolation_runner.py <journey.json>          # live: docker/podman required
sandbox_isolation_runner.py <journey.json> --fake   # in-process simulator
test_sandbox_isolation_runner.sh                    # self-contained regression
```

`--fake` (or `VELDO_SANDBOX_DRIVER=fake`) drives the journey through the
in-process `FakeContainerDriver` instead of a container, so the fixtures and the
control logic run with no runtime installed. `VELDO_CONTAINER_RUNTIME` pins the
live runtime name (default: docker, then podman).

## Journey format

A journey names an image, the mounts that scope the flow, and a list of checks:

```json
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
```

A mount is `{"path": "/abs", "mode": "ro"|"rw"}` (a bare string `"/abs"` is a
read-only mount). `allowed_mounts` is the ONLY scope the flow is granted. A
check is a `read` or a `write` at an absolute container path with a required
`expect` verdict:

- `allowed` the flow must reach the path. A read is allowed when the path falls
  within some declared mount; a write is allowed only within a read-write mount.
- `denied` the flow must be refused. A read or write outside every mount is
  denied, and a write into a read-only mount is denied.

The runner drives each check as a probe inside the container and compares the
observed verdict to the required one:

- a path required `denied` but observed `allowed` is a `CONFINEMENT BREACH` (the
  dangerous failure, named with the path)
- a path required `allowed` but observed `denied` is `OVER-RESTRICTED` (a
  usability failure)

A journey with no checks asserts nothing and is a named journey error, never a
silent pass. Exit 0 = every check matched its required verdict; exit 1 = at
least one did not, with the offending path and the direction named on stdout.

## The driver seam

`ContainerDriver.run(image, argv, mounts)` shells out to `docker run` (or
`podman run`) with only the declared mount scopes, a read-only root filesystem
(`--read-only`), no network (`--network none`), and every capability dropped
(`--cap-drop ALL --security-opt no-new-privileges`), so confinement is enforced
by the real runtime. It FAILS LOUD in its constructor when no runtime is on
PATH rather than skipping the check. `FakeContainerDriver` simulates confinement
deterministically in process (a path is readable within a mount, writable within
a read-write mount, denied otherwise) and never touches the real filesystem, so
the runner's control logic is gate-tested with no container.

## Fixtures

`fixtures/pass.sandbox.json` is a correctly-confined journey: reads inside the
mounts succeed, a write lands in the read-write mount, a write into the
read-only mount is refused, and two escape attempts (a host secret read, a host
path write) are denied, so the runner exits 0. `fixtures/fail.sandbox.json` is
the deliberately-failing journey: an over-broad `/` mount (a real
misconfiguration) leaves `/etc/shadow` reachable while the journey still
requires that read denied, so the escape succeeds and the runner exits 1 naming
the `CONFINEMENT BREACH` on `/etc/shadow`. Both are driven through the
`FakeContainerDriver` so the pair runs with no runtime.

```
sandbox_isolation_runner.py --fake fixtures/pass.sandbox.json   # exit 0
sandbox_isolation_runner.py --fake fixtures/fail.sandbox.json   # exit 1
```

## Why this is a reference

The confinement model (`confine`), the verdict classifier (`classify`), and the
runner's grading (`grade_check`, `run_journey` over both fixtures via the fake
driver) are pure or fake-driven with no container and no host filesystem access,
so the control logic is unit-tested in `scripts/selftest.py` with no external
dependency. But the veldo home repository has no container surface of its own to
confine, and a live run needs a working container runtime this box does not
reliably have, so the runner ships `reference`: an adopting repo on a host with
docker or podman wires the live `ContainerDriver` to its own image and the
sandbox or isolation gate slot. When no runtime is present the live path fails
loud with a clear message; it is never silently skipped.
