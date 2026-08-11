#!/usr/bin/env python3
"""veldo fleet environment provisioning: attach a heavy shared read-only dependency ONCE for
the whole fleet, and give a mutating build a cheap isolated write layer - never a wholesale
copy of a 75-million-row dataset.

WARP-0406 (ephemeral_env_provisioning) gives a single build a clean ephemeral env with a
create/seed/observe/teardown lifecycle. This is the FLEET layer on top:

  - A repo declares its dependencies and each one's SHARING MODE in .veldo/fleet_env.json:
      ephemeral   - a fresh per-build env (the WARP-0406 path); nothing shared.
      shared_ro   - one shared read-only instance the whole fleet ATTACHES to; a mutating
                    build gets an isolated WRITE LAYER over it (a schema/prefix, a
                    copy-on-write clone, or a small fixture), declared per dep - never a copy.
    A heavy dep may also declare a CAPABILITY tag; only a worker advertising it can run a
    build that needs the dep (reusing the claim ledger's capability match), so the giant
    dataset is provisioned only where it is mounted and never duplicated elsewhere.

  - resolve_plan() turns a build's declared needs into a provisioning plan honoring the
    modes. There is deliberately NO 'copy the shared dataset' action: a mutating use of a
    shared_ro dep resolves to a write layer, a read use attaches read-only.

  - A shared_ro dep is REF-COUNTED across the fleet: the first worker to need it brings it
    up, every other worker attaches to the same instance, and it is torn down only when the
    LAST worker releases it. The ref count lives in a file under the git common dir and is
    mutated atomically by reusing the claim ledger's per-unit lock, so two workers never
    bring up two copies. The actual bring-up/attach/teardown is delegated to an injected
    FleetEnvBackend (the real one runs docker / a DB / a CoW clone; a fake drives the gate)."""
import importlib.util
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CL = _load("veldo_claim_fe", ".veldo/claim.py")  # reuse the hardened lock + capability match

MODES = ("ephemeral", "shared_ro")
WRITE_LAYERS = ("schema", "cow", "fixture")


class FleetEnvError(Exception):
    pass


def load_env_def(repo_root=None):
    """Load the repo's fleet env definition from .veldo/fleet_env.json, or {} if absent.
    Shape: {"deps": {name: {mode, capability?, write_layer?, image?, fixture?}}}."""
    p = Path(repo_root or ROOT) / ".veldo" / "fleet_env.json"
    if not p.exists():
        return {"deps": {}}
    data = json.loads(p.read_text())
    if not isinstance(data.get("deps"), dict):
        raise FleetEnvError("fleet_env.json must have a 'deps' object")
    return data


def resolve_plan(defn, needs, worker_caps=None):
    """Turn a build's needs into a provisioning plan honoring each dep's sharing mode.

    needs: {dep_name: {"mutates": bool}}. Returns a list of actions, each
    {dep, action, ...} where action is one of:
      ephemeral         - a fresh per-build env (WARP-0406).
      attach_shared_ro  - attach read-only to the one shared instance.
      write_layer       - an isolated write layer (strategy: schema|cow|fixture) over the
                          shared data, for a mutating build. NEVER a wholesale copy.
    Raises FleetEnvError on an unknown dep, a bad mode, a capability the worker lacks, or a
    mutating use of a shared dep with no declared write_layer."""
    caps = set(worker_caps or [])
    deps = (defn or {}).get("deps", {})
    plan = []
    for name, use in (needs or {}).items():
        d = deps.get(name)
        if d is None:
            raise FleetEnvError("unknown dependency %r (not in fleet_env.json)" % name)
        mode = d.get("mode")
        if mode not in MODES:
            raise FleetEnvError("dep %r has bad mode %r (%s)" % (name, mode, "|".join(MODES)))
        cap = d.get("capability")
        if cap and not CL.capability_ok(caps, [cap]):
            raise FleetEnvError(
                "dep %r requires capability %r the worker does not advertise" % (name, cap))
        mutates = bool((use or {}).get("mutates"))
        if mode == "ephemeral":
            plan.append({"dep": name, "action": "ephemeral"})
        elif mode == "shared_ro":
            if mutates:
                wl = d.get("write_layer")
                if wl not in WRITE_LAYERS:
                    raise FleetEnvError(
                        "mutating use of shared dep %r needs a write_layer (%s), not a copy"
                        % (name, "|".join(WRITE_LAYERS)))
                plan.append({"dep": name, "action": "write_layer", "strategy": wl})
            else:
                plan.append({"dep": name, "action": "attach_shared_ro"})
    return plan


def shared_env_root(override=None):
    """veldo/shared_env under the git common dir (shared across worktrees), or an override."""
    root = override or os.environ.get("VELDO_RUNS_ROOT")
    if not root:
        import subprocess
        common = subprocess.check_output(
            ["git", "rev-parse", "--git-common-dir"], text=True).strip()
        root = os.path.join(os.path.abspath(common), "veldo")
    return os.path.join(root, "shared_env")


def _dep_path(dep, root=None):
    return os.path.join(shared_env_root(root), CL._safe(dep) + ".json")


class FleetEnvBackend:
    """The seam the provisioner drives; a real backend runs docker / a DB / a CoW clone, a
    fake drives the gate. Each returns an opaque handle where relevant."""

    def bring_up_shared(self, dep):
        """Provision the ONE shared read-only instance for dep (called for the first user)."""
        raise NotImplementedError

    def teardown_shared(self, dep):
        """Tear down the shared instance for dep (called when the last user releases it)."""
        raise NotImplementedError

    def attach_ro(self, dep):
        """Return a read-only handle onto the shared instance (no data copied)."""
        raise NotImplementedError

    def make_write_layer(self, dep, strategy):
        """Return an isolated write layer over the shared data (schema|cow|fixture); the
        shared dataset is not copied, only the small mutable delta is per-build."""
        raise NotImplementedError

    def provision_ephemeral(self, dep):
        """Return a handle to a fresh per-build ephemeral env for dep."""
        raise NotImplementedError

    def teardown(self, handle):
        """Tear down a per-build handle (a write layer or an ephemeral env)."""
        raise NotImplementedError


class SharedDepRegistry:
    """Fleet-wide ref count for shared_ro deps: bring up once, attach many, tear down when the
    last worker leaves. The count is a file under the git common dir mutated atomically by
    reusing the claim ledger's per-unit lock, so two workers never bring up two copies."""

    def __init__(self, backend, root=None):
        self.backend = backend
        self.root = root

    def acquire(self, dep, worker_id):
        """Attach worker_id to the shared instance for dep. Brings it up if it is the first
        holder. Returns True if this call brought it up (was the first), else False. The
        per-unit lock is held across bring_up_shared so it runs exactly once even under
        contention; a backend's bring_up_shared must therefore not re-enter acquire for the
        SAME dep (it would self-deadlock on the lock) - a sane backend never does."""
        path = _dep_path(dep, self.root)
        with CL._unit_lock(path):
            rec = CL._read(path) or {"dep": dep, "refs": 0, "holders": []}
            first = rec["refs"] == 0
            if first:
                self.backend.bring_up_shared(dep)  # exactly once: the lock serializes us
            if worker_id not in rec["holders"]:
                rec["holders"].append(worker_id)
                rec["refs"] = len(rec["holders"])
            CL._publish(os.path.dirname(path), path, rec)
            return first

    def release(self, dep, worker_id):
        """Detach worker_id. Tears the shared instance down if it was the last holder.
        Returns True if this call tore it down (was the last), else False."""
        path = _dep_path(dep, self.root)
        with CL._unit_lock(path):
            rec = CL._read(path)
            if not rec or worker_id not in rec.get("holders", []):
                return False
            rec["holders"].remove(worker_id)
            rec["refs"] = len(rec["holders"])
            last = rec["refs"] == 0
            if last:
                self.backend.teardown_shared(dep)  # exactly once: the lock serializes us
                try:
                    os.remove(path)
                except OSError:
                    pass
            else:
                CL._publish(os.path.dirname(path), path, rec)
            return last

    def refs(self, dep):
        rec = CL._read(_dep_path(dep, self.root))
        return rec.get("refs", 0) if rec else 0


class EnvLease:
    """What a build holds for the duration of its run: the shared deps it attached (released
    on teardown, dropping the fleet ref count) and the per-build handles it created (torn
    down on teardown). Provisioning is done; teardown reverses exactly what was provisioned."""

    def __init__(self, registry, backend, worker_id):
        self._registry = registry
        self._backend = backend
        self._worker_id = worker_id
        self.attached_shared = []   # dep names attached read-only via the ref count
        self.handles = []           # (dep, handle) for write layers and ephemeral envs

    def teardown(self):
        for dep, handle in self.handles:
            self._backend.teardown(handle)
        for dep in self.attached_shared:
            self._registry.release(dep, self._worker_id)
        self.handles = []
        self.attached_shared = []


def provision(defn, needs, worker_id, backend, worker_caps=None, root=None):
    """Provision the env for a build: resolve the plan, then for each action attach the shared
    dep (ref-counted), make a write layer, or provision an ephemeral env - via the backend.
    Returns an EnvLease whose teardown() reverses everything. Raises FleetEnvError before any
    side effect if the plan is invalid (unknown dep, missing capability, mutate-without-layer)."""
    plan = resolve_plan(defn, needs, worker_caps)  # validates first, before any provisioning
    registry = SharedDepRegistry(backend, root=root)
    lease = EnvLease(registry, backend, worker_id)
    try:
        for step in plan:
            dep = step["dep"]
            if step["action"] == "attach_shared_ro":
                registry.acquire(dep, worker_id)
                lease.attached_shared.append(dep)  # recorded BEFORE attach so a failing
                backend.attach_ro(dep)             # attach still drops the ref on teardown
            elif step["action"] == "write_layer":
                registry.acquire(dep, worker_id)  # the shared data is attached, then layered
                lease.attached_shared.append(dep)
                lease.handles.append((dep, backend.make_write_layer(dep, step["strategy"])))
            elif step["action"] == "ephemeral":
                lease.handles.append((dep, backend.provision_ephemeral(dep)))
    except Exception:
        # a backend failure partway through must not leak a fleet ref count or a per-build
        # env: tear down exactly what was provisioned so far, then re-raise. The ref count has
        # no TTL, so an un-released shared dep would keep a heavy dataset up indefinitely.
        lease.teardown()
        raise
    return lease
