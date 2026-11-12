"""VELDO-0117: one coordination domain has one store, and the authority is what says so.

Only ROOT and expect come from the suite harness:

  python3 scripts/selftest.py --suite 113_veldo_0117_domain_store

WHAT IS UNDER TEST. The domain registry in .veldo/control_store.py, the authority's use of it in
.veldo/control_client.py, the binding comparison in .veldo/control_enrollment.py and the service
that runs the authority in production, .veldo/control_service.py. The four modules are copied
into a runtime directory and every authority here is a child process running that copy, so a
mutation of any one of them is what the authority runs. The clones are driven by the unmutated
modules of this checkout: a clone has no registry, and no row may pass because of something a
clone decided.

THE PRODUCTION PATH. The first row also installs two instances of one domain with the production
installer (control_service.install, into one install root, no unit started) and runs each
installed executable as its unit would: `control_service.py serve <service.json>`. Nothing in
this suite hands those processes a registry; they find it as an installation does. Signed
commands reach them through the production client, under the installed enrollment signers and
the stores' own keyrings.

HOW. scripts/fixtures/authority_store.py (VELDO-0115) builds real clones, an Ed25519 signer and
SQLite stores. This suite enrolls the clones with the store identities each case needs, starts
one authority process per store over a registry they share, and sends signed commands through
the production client. Stores and the registry are read back with plain read-only sqlite3
connections, never through the code under test.

Three rows:

  enrollment/authority-refuses-domain-store-conflict   the equality product of domain, store uuid
      and canonical location between a committed binding and a second clone's binding.
  enrollment/one-domain-one-winner                     two stores proposed for an unbound domain,
      in both orders and with the second attempt begun while the first is inside its own.
  enrollment/domain-binding-survives-restart           after each of those, both authorities are
      stopped and started again as new processes, in both orders.

On code without a registry the authorities run as that code runs them, and the rows are red
because a conflicting binding is applied, not because anything raised.
"""
import hashlib as _v117_hashlib
import importlib.util as _v117_import
import itertools as _v117_it
import json as _v117_json
import os as _v117_os
from pathlib import Path as _v117_Path
import select as _v117_select
import shutil as _v117_shutil
import sqlite3 as _v117_sqlite3
import subprocess as _v117_sp
import sys as _v117_sys
import tempfile as _v117_temp
import time as _v117_time
import uuid as _v117_uuid

_v117_spec = _v117_import.spec_from_file_location(
    "v117_authority_store_fixture", ROOT / "scripts/fixtures/authority_store.py")
_v117_FX = _v117_import.module_from_spec(_v117_spec)
_v117_spec.loader.exec_module(_v117_FX)

# The modules an authority runs: three for the child authorities of this suite, and the service
# for the installed ones. The mutation driver replaces one of these paths.
_v117_SOURCES = {
    "control_store.py": ROOT / ".veldo" / "control_store.py",
    "control_client.py": ROOT / ".veldo" / "control_client.py",
    "control_enrollment.py": ROOT / ".veldo" / "control_enrollment.py",
    "control_service.py": ROOT / ".veldo" / "control_service.py",
}
_v117_ROWS = ("enrollment/authority-refuses-domain-store-conflict",
              "enrollment/one-domain-one-winner",
              "enrollment/domain-binding-survives-restart")
# A child authority imports three modules, opens a store and reports: 60 s is the fixture's own
# 20 s readiness bound with room for a loaded host.
_v117_START = (60.0, "the readiness bound of a child authority")
# How long the second registration is watched for getting past the first one's open transaction.
# With the registry's write lock it never does, so each overlapped schedule waits this once.
_v117_OVERLAP = (3.0, "the overlap window of two registrations")

# The authority process. It registers as the code it loads does, reports each step as one JSON
# line, serves its socket and stops when its input closes. A held registration waits for one
# line of input inside the registry's transaction.
_v117_RUNNER = r'''
import importlib.util, json, os, select, sys, time
from pathlib import Path


def main():
    cfg = json.loads(Path(sys.argv[1]).read_text())
    spec = importlib.util.spec_from_file_location("v117_runner_fixture", cfg["fixture"])
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    modules = Path(cfg["modules"])
    client, enrollment, store = [fixture.load(modules / name) for name in fixture.MODULES[:3]]
    signer = fixture.Signer(cfg["key_directory"])

    def say(event, **more):
        print(json.dumps(dict(more, event=event, at=time.monotonic(), pid=os.getpid())), flush=True)

    conn = store.open_store(cfg["store_file"])

    def apply(command):
        return store.execute(conn, command, "fixture", signer.sign, 1, committed_at=2)

    def observe(committed):
        say("checked", committed=committed)
        if cfg["hold"]:
            os.read(0, 64)

    supported = hasattr(store, "DomainRegistry")
    kwargs, authority, error = {}, None, None
    say("begin", registry=supported)
    try:
        if supported:
            kwargs["registry"] = store.DomainRegistry(cfg["registry"], observe=observe)
        authority = client.Authority(
            cfg["store_uuid"], cfg["domain_uuid"], cfg["store_path"], enrollment, signer.verify,
            fixture.HOST, apply,
            watermark=lambda: conn.execute("SELECT COALESCE(MAX(seq),0) FROM journal").fetchone()[0],
            **kwargs)
    except Exception as exc:
        error = "%s: %s" % (type(exc).__name__, str(exc)[:300])
    say("ready", registry=supported, decision=getattr(authority, "domain_store", None), error=error)
    # The socket's own directory, however the operator spelled the store: the gate's mutation
    # worker refuses a bind through a symlinked directory (EACCES), and the file is the same one.
    address = client.socket_path_for({"store_path": os.path.realpath(cfg["store_path"])})
    listener = None
    try:
        if authority is not None:
            listener = client.bind(address)
        say("listening", serving=authority is not None)
        while True:
            readable, _, _ = select.select([0] + ([listener] if listener else []), [], [])
            if 0 in readable:
                if not os.read(0, 64):
                    break
                continue
            client.serve_one(listener, authority)
    finally:
        say("stopped", counts=getattr(authority, "domain_store_counts", None))
        if listener is not None:
            listener.close()
            Path(address).unlink(missing_ok=True)
        conn.close()


main()
'''


def _v117_identity(domain, store_uuid, store_path):
    return {"domain_uuid": domain, "store_uuid": store_uuid,
            "store_path": _v117_os.path.realpath(str(store_path))}


def _v117_registry_rows(path):
    """Every row of the registry, read by a plain read-only connection. [] when there is none."""
    if not _v117_Path(path).is_file():
        return []
    conn = _v117_sqlite3.connect(_v117_Path(path).as_uri() + "?mode=ro", uri=True)
    try:
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='domain_stores'").fetchone():
            return []
        return [{"domain_uuid": r[0], "store_uuid": r[1], "store_path": r[2]} for r in conn.execute(
            "SELECT domain_uuid, store_uuid, store_path FROM domain_stores ORDER BY domain_uuid")]
    finally:
        conn.close()


def _v117_committed(path, domain):
    rows = [row for row in _v117_registry_rows(path) if row["domain_uuid"] == domain]
    return rows[0] if rows else None


def _v117_commands(path):
    return len(_v117_FX.snapshot(path)["commands"])


class _v117_Process:
    """One authority child: its configured identity, its events and its input."""

    def __init__(self, world, name, identity, store_file, registry, hold=False, store_path=None):
        self.name, self.identity, self.seen, self.buffer = name, identity, {}, b""
        self.order = ("begin", "checked", "ready", "listening", "stopped")
        directory = world["scratch"] / "processes"
        directory.mkdir(exist_ok=True)
        tag = "%03d-%s" % (len(world["processes"]), name)
        config = directory / (tag + ".json")
        config.write_text(_v117_json.dumps({
            "fixture": str(ROOT / "scripts/fixtures/authority_store.py"),
            "modules": str(world["runtime"]), "key_directory": str(world["fx"].signer.directory),
            "store_file": str(store_file), "registry": str(registry), "hold": hold,
            "domain_uuid": identity["domain_uuid"], "store_uuid": identity["store_uuid"],
            # The operator's spelling of the store path; the identity holds the canonical one.
            "store_path": str(store_path or identity["store_path"])}))
        self.errors = directory / (tag + ".stderr")
        env = dict(_v117_os.environ, PYTHONDONTWRITEBYTECODE="1")
        for key in ("VELDO_CONTROL_TEST_HARNESS", "VELDO_CONTROL_KILL_AT"):
            env.pop(key, None)
        with open(self.errors, "wb") as errors:
            self.process = _v117_sp.Popen([_v117_sys.executable, str(world["runner"]), str(config)],
                                          stdin=_v117_sp.PIPE, stdout=_v117_sp.PIPE, stderr=errors, env=env)
        world["processes"].append(self)

    def event(self, name, bound=_v117_START):
        """The named event, or None when the bound runs out or the process ends first."""
        deadline = _v117_time.monotonic() + bound[0]
        while name not in self.seen:
            if any(later in self.seen for later in self.order[self.order.index(name) + 1:]):
                return None  # a later step was reported, so this one was never taken
            if b"\n" in self.buffer:
                line, self.buffer = self.buffer.split(b"\n", 1)
                try:
                    record = _v117_json.loads(line)
                except ValueError:
                    continue
                self.seen.setdefault(record.get("event"), record)
                continue
            if self.process.stdout.closed:
                return None
            left = deadline - _v117_time.monotonic()
            if left <= 0 or not _v117_select.select([self.process.stdout], [], [], left)[0]:
                return None
            chunk = _v117_os.read(self.process.stdout.fileno(), 65536)
            if not chunk:
                return None
            self.buffer += chunk
        return self.seen[name]

    def decision(self):
        ready = self.event("ready") or {}
        return (ready.get("decision") or {}).get("decision") or (
            "error: %s" % ready["error"] if ready.get("error") else "none")

    def release(self):
        try:
            self.process.stdin.write(b"go\n")
            self.process.stdin.flush()
        except OSError:
            pass

    def stop(self):
        if self.process.poll() is None:
            try:
                self.process.stdin.close()
            except OSError:
                pass
            try:
                self.process.wait(timeout=_v117_START[0])
            except _v117_sp.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        stopped = self.event("stopped", (1.0, "a stopped process's last line"))
        if not self.process.stdout.closed:
            self.process.stdout.close()
        return stopped


def _v117_enroll(fx, handle, domain, store_uuid, store_path):
    return fx.enrollment.enroll(handle.workspace, domain, store_uuid, str(store_path), _v117_FX.HOST, 1,
                                fx.signer.sign, "fixture", "2026-11-11T00:00:00Z")


def _v117_send(fx, handle, tag):
    """One signed command from this clone through the production client: (outcome, answer)."""
    try:
        answer = fx.client.send(handle.workspace, _v117_FX.command(tag), fx.enrollment,
                                fx.signer.verify, fx.signer.sign, _v117_FX.HOST)
    except fx.client.RoutingRefused as refused:
        return "routing:" + refused.reason, {}
    return ("accepted" if answer.get("accepted") else "refused:%s" % answer.get("reason")), answer


def _v117_admission(world, handle, binding, registry, serving_domain):
    """The reasons the authority's own binding check gives for this binding, held to the store
    the registry commits for the domain that would serve it."""
    fx = world["fx"]
    try:
        problems = world["enrollment"].verify_binding(
            handle.workspace, binding, fx.signer.verify, _v117_FX.HOST, domain_uuid=serving_domain,
            committed_store=_v117_committed(registry, serving_domain))
    except TypeError as error:
        return ["no admission check in this code (%s)" % str(error)[:80]]
    return [reason for reason, _ in problems]


def _v117_started(process, checks, label):
    """Wait for a process to be serving; a start that never reports is a false check, not a raise."""
    ready = process.event("ready")
    listening = process.event("listening")
    checks.append(("%s: the authority process started and reported [%s]" % (
        label, "no report" if ready is None else (ready.get("error") or "ok")),
        ready is not None and listening is not None))
    return ready or {}


# ---------------------------------------------------------------------------------------------
# AC1: the equality product
# ---------------------------------------------------------------------------------------------

def _v117_product(world, checks, records):
    fx = world["fx"] = _v117_FX.Fixture(ROOT, world["scratch"] / "product", runtime=world["runtime"])
    first, second = fx.handles
    registry = world["scratch"] / "product" / "registry" / "domains.sqlite3"
    domain, store = str(_v117_uuid.uuid4()), str(_v117_uuid.uuid4())
    held = _v117_identity(domain, store, first.path)
    _v117_enroll(fx, first, domain, store, first.path)
    # Another spelling of the committed store's file, through a symlinked directory.
    alias = world["scratch"] / "product" / "alias"
    alias.symlink_to(first.path.parent, target_is_directory=True)
    one = _v117_Process(world, "committed", held, first.path, registry)
    ready = _v117_started(one, checks, "the committed store")
    checks.append(("the first authority of the domain registers its configured store [%s]" % one.decision(),
                   (ready.get("decision") or {}).get("decision") == "registered"
                   and _v117_committed(registry, domain) == held))
    for same_domain, same_uuid, same_location in _v117_it.product((True, False), repeat=3):
        cell = "domain %s, uuid %s, location %s" % tuple(
            "equal" if same else "unequal" for same in (same_domain, same_uuid, same_location))
        other_domain = domain if same_domain else str(_v117_uuid.uuid4())
        other_uuid = store if same_uuid else str(_v117_uuid.uuid4())
        binding = _v117_enroll(fx, second, other_domain, other_uuid,
                               alias / first.path.name if same_location else second.path)
        proposed = _v117_identity(other_domain, other_uuid, binding["store_path"])
        before = (_v117_commands(first.path), _v117_commands(second.path))
        # An authority stands at the proposed store when that is another file; the committed
        # store's own authority answers when the binding names its file.
        two = None
        if not same_location:
            two = _v117_Process(world, "proposed", proposed, second.path, registry)
            _v117_started(two, checks, cell)
        serving = domain if same_location else other_domain
        admitted = _v117_admission(world, second, binding, registry, serving)
        committed_before = _v117_committed(registry, domain)
        outcomes = [_v117_send(fx, first, cell + " committed before"), _v117_send(fx, second, cell + " proposed"),
                    _v117_send(fx, first, cell + " committed after")]
        registered = None if two is None else two.decision()
        if two is not None:
            two.stop()
        after = (_v117_commands(first.path), _v117_commands(second.path))
        delta = (after[0] - before[0], after[1] - before[1])
        outcome, answer = outcomes[1]
        if same_domain and same_uuid and same_location:
            wanted = "matching: accepted into the committed store"
            ok = (admitted == [] and outcome == "accepted" and answer.get("domain_store") == held
                  and answer.get("store_path") == held["store_path"] and delta == (3, 0))
        elif same_domain:
            wanted = "conflict: domain_store_conflict at admission and for the command, nothing written"
            ok = (admitted == ["domain_store_conflict"] and outcome == "refused:domain_store_conflict"
                  and answer.get("committed") == held and answer.get("proposed") == proposed
                  and registered in (None, "domain_store_conflict") and (two is None) == same_location
                  and delta == (2, 0))
        elif same_location:
            wanted = "another domain naming the committed file: refused as cross-domain, nothing written"
            ok = admitted == ["cross_domain"] and outcome == "refused:coordinate_not_served" and delta == (2, 0)
        else:
            wanted = "another domain at its own file: registered and accepted into its own store"
            ok = (admitted == [] and registered == "registered" and outcome == "accepted"
                  and answer.get("domain_store") == proposed and delta == (2, 1))
        kept = (committed_before == held and _v117_committed(registry, domain) == held
                and outcomes[0][0] == outcomes[2][0] == "accepted")
        checks.append(("%s is %s [admission %s; registration %s; command %s; transactions %s]"
                       % (cell, wanted, admitted, registered, outcome, delta), ok))
        checks.append(("%s leaves the committed identity as it was and its own clone served [%s; %s, %s]"
                       % (cell, _v117_committed(registry, domain), outcomes[0][0], outcomes[2][0]), kept))
        records.append({"case": cell, "committed": held, "proposed": proposed, "admission": admitted,
                        "registration": registered, "command": outcome, "transactions": list(delta),
                        "passed": bool(ok and kept)})
    # The record gone from the registry, as after a lost file: the authority still running must not
    # serve the domain, and a clone's command must not put the record back.
    if _v117_committed(registry, domain) is not None:
        lost = _v117_sqlite3.connect(str(registry))
        lost.execute("DELETE FROM domain_stores WHERE domain_uuid=?", (domain,))
        lost.commit()
        lost.close()
    commands = _v117_commands(first.path)
    outcome, _ = _v117_send(fx, first, "record removed")
    checks.append(("with the domain's record removed from the registry, its own clone's command is refused, is not "
                   "applied and registers nothing [%s; %d transaction(s); record %s]"
                   % (outcome, _v117_commands(first.path) - commands, _v117_committed(registry, domain)),
                   outcome == "refused:coordinate_not_served" and _v117_commands(first.path) == commands
                   and _v117_committed(registry, domain) is None))
    stopped = one.stop() or {}
    counts = stopped.get("counts") or {}
    # 17 accepted commands named the committed store: 16 from its own clone and the one matching
    # binding. One binding of the domain reached this authority naming another store uuid at its
    # file; the two that named another file were refused by the authority standing there.
    checks.append(("the committed store's authority counted its matching bindings and its conflicts [%s]" % counts,
                   counts.get("matching") == 17 and counts.get("domain_store_conflict") == 1))


# ---------------------------------------------------------------------------------------------
# AC1 on the production path: installed instances, run as their units run them
# ---------------------------------------------------------------------------------------------

class _v117_Fake:
    """The installer's systemctl: records the calls and starts nothing."""

    def __init__(self):
        self.calls = []

    def run(self, args):
        self.calls.append(list(args))
        return 0, "", ""


class _v117_Served:
    """One installed instance run as its unit runs it: <python> -B <bin>/control_service.py serve <config>."""

    def __init__(self, world, report, name):
        self.config = _v117_json.loads(_v117_Path(report["config"]).read_text())
        self.errors = _v117_Path(report["home"]) / "state" / ("serve-%d-%s.stderr" % (len(world["processes"]), name))
        env = dict(_v117_os.environ, PYTHONDONTWRITEBYTECODE="1")
        for key in ("VELDO_CONTROL_TEST_HARNESS", "VELDO_CONTROL_KILL_AT", "NOTIFY_SOCKET"):
            env.pop(key, None)
        with open(self.errors, "wb") as errors:
            self.process = _v117_sp.Popen(
                [_v117_os.path.realpath(_v117_sys.executable), "-B", report["executable"], "serve", report["config"]],
                stdin=_v117_sp.DEVNULL, stdout=_v117_sp.DEVNULL, stderr=errors, env=env)
        world["processes"].append(self)

    def listening(self, bound=_v117_START):
        """Whether the instance bound its socket within the bound; False when it ended first."""
        deadline = _v117_time.monotonic() + bound[0]
        while _v117_time.monotonic() < deadline:
            if _v117_os.path.exists(self.config["socket"]):
                return True
            if self.process.poll() is not None:
                return False
            _v117_time.sleep(0.05)
        return False

    def said(self):
        try:
            return self.errors.read_text()[-300:].strip()
        except OSError:
            return ""

    def observations(self, kind):
        try:
            lines = _v117_Path(self.config["observations"]).read_text().splitlines()
        except OSError:
            return []
        found = []
        for line in lines:
            try:
                record = _v117_json.loads(line)
            except ValueError:
                continue
            if isinstance(record, dict) and (record.get("kind") == kind or record.get("refusal") == kind):
                found.append(record)
        return found

    def stop(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=_v117_START[0])
            except _v117_sp.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        return self.process.returncode


def _v117_production(world, checks, records):
    base = world["scratch"] / "production"
    mods = base / "src" / ".veldo"
    (mods / "services").mkdir(parents=True)
    _v117_shutil.copytree(ROOT / ".veldo" / "runtime", mods / "runtime")
    for source in sorted((ROOT / ".veldo").glob("*.py")):
        _v117_shutil.copyfile(source, mods / source.name)
    _v117_shutil.copyfile(ROOT / ".veldo" / "services" / "veldo-authority.service",
                          mods / "services" / "veldo-authority.service")
    # The four modules under test, as the runtime directory holds them (a mutant's copy among them).
    for name in _v117_SOURCES:
        _v117_shutil.copyfile(world["runtime"] / name, mods / name)
    service = _v117_FX.load(mods / "control_service.py")
    # The clone's side: this checkout's unmutated modules.
    client, enrollment, store = (_v117_FX.load(ROOT / ".veldo" / name) for name in _v117_FX.MODULES[:3])
    contract = _v117_FX.load(ROOT / ".veldo" / "authority_contract.py")
    eligibility = _v117_FX.load(ROOT / ".veldo" / "control_eligibility.py")
    host = "host-117"

    private = base / "private"
    private.mkdir(mode=0o700)
    public = {}
    for who in ("owner", "member"):
        _v117_sp.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(private / who)], check=True,
                     capture_output=True, timeout=20, stdin=_v117_sp.DEVNULL)
        public[who] = (private / (who + ".pub")).read_text().strip()

    def signer(who, namespace):
        def sign(data):
            return _v117_sp.run(["ssh-keygen", "-Y", "sign", "-f", str(private / who), "-n", namespace],
                                input=data, capture_output=True, check=True, timeout=20).stdout.decode()
        return sign

    trust = base / "trust"
    trust.mkdir(mode=0o700)
    signers = trust / "enrollment_signers"
    signers.write_text(contract.allowed_signers_line("owner", public["owner"], eligibility.ENROLLMENT_NAMESPACE) + "\n")
    trust_file = trust / "host_trust.json"
    trust_file.write_text(_v117_json.dumps({"schema": eligibility.HOST_TRUST_SCHEMA, "host_identity": host,
                                            "enrollment_signers": str(signers)}))
    enroll_sign = signer("owner", eligibility.ENROLLMENT_NAMESPACE)
    journal_sign = signer("owner", "veldo-journal")
    member_sign = signer("member", contract.SIGNATURE_NAMESPACE)

    def clone(name):
        path = base / name
        _v117_FX.Fixture.git(base, "init", "-q", str(path))
        (path / "README").write_text(name + "\n")
        _v117_FX.Fixture.git(path, "add", "README")
        _v117_FX.Fixture.git(path, "-c", "user.name=Veldo Fixture", "-c", "user.email=fixture@veldo.invalid",
                             "-c", "commit.gpgsign=false", "commit", "-q", "-m", name)
        return path

    run = _v117_os.urandom(4).hex()
    domain = "dom117" + run
    sides = {}
    for name in ("a", "b"):
        path = base / ("store-" + name) / "control.sqlite3"
        sides[name] = {"workspace": clone("clone-" + name), "store_uuid": "store117%s%s" % (name, run),
                       "repository": "repo117%s%s" % (name, run), "path": path,
                       "identity": _v117_identity(domain, "store117%s%s" % (name, run), path)}
    serial = [0]

    def enroll(side, store_uuid, store_path):
        return enrollment.enroll(str(side["workspace"]), domain, store_uuid, str(store_path), host, 1, enroll_sign,
                                 "owner", "2026-11-11T00:00:00Z", repository_uuid=side["repository"])

    def member(path):
        """The owner's setup of a store before its installation: one member and the member's key."""
        conn = store.open_store(str(path))
        try:
            for identity, kind, data in (
                    ("member", "membership", {"principal_type": "person", "roles": [], "scope": "*"}),
                    ("key:member:1", "verification_key", {"principal": "member", "public_key": public["member"],
                                                          "effective_at": 0})):
                serial[0] += 1
                store.execute(conn, {"command_id": "setup-%d" % serial[0], "principal": "owner",
                                     "operation": "upsert_entity", "nonce": "setup-%d" % serial[0],
                                     "artifact_digests": [], "expected_versions": {identity: 0},
                                     "parameters": {"entity_id": identity, "kind": kind, "data": data}},
                              "owner", journal_sign, 1)
        finally:
            conn.close()

    def send(side, store_uuid, tag):
        """One signed command from this clone through the production client: (outcome, answer)."""
        serial[0] += 1
        entity = "note:%s:%d" % (run, serial[0])
        body = {"command_id": "cmd-%s-%d" % (run, serial[0]), "principal": "member", "operation": "upsert_entity",
                "nonce": "nonce-%s-%d" % (run, serial[0]), "artifact_digests": [], "expected_versions": {entity: 0},
                "parameters": {"entity_id": entity, "kind": "note", "data": {"tag": tag}},
                "domain_uuid": domain, "store_uuid": store_uuid, "repository_uuid": side["repository"]}
        packet = {"command": body, "signature": member_sign(store.canonical_bytes(body))}
        verify = eligibility.HostTrust(host, str(signers)).verifier("owner", str(side["workspace"]))
        try:
            answer = client.send(str(side["workspace"]), packet, enrollment, verify, member_sign, host, timeout=10)
        except client.RoutingRefused as refused:
            return "routing:" + refused.reason, {}
        if answer.get("accepted"):
            result = answer.get("result") or {}
            return ("accepted" if result.get("ok") is not False else "result:%s" % result.get("reason")), answer
        return "refused:%s" % answer.get("reason"), answer

    install_root = base / "install"
    registry = install_root / "domains.sqlite3"
    profile = {"kind": "linux-systemd", "slice": "v117%s.slice" % run, "lock": str(base / "workers.lock"),
               "concurrency": 2, "runtime_seconds": 600, "memory_bytes": 256 << 20, "cpu_percent": 100,
               "file_bytes": 64 << 20, "tasks_max": 256, "stop_grace_seconds": 1, "kill_grace_seconds": 1}
    # The installer qualifies the worker profile against this host's user manager, which the gate's
    # mutation worker does not reach. These instances launch no worker, so where the profile does
    # not qualify the installation proceeds on a qualification answered qualified (as suite 109 does).
    real_qualify = service.C.qualify
    qualification = real_qualify(profile)
    if not qualification.get("qualified"):
        print("  VELDO-0117 production: the worker profile does not qualify here (%s): installing with the "
              "containment qualification answered qualified; the instances under test launch no worker"
              % qualification.get("refusal"))
        service.C.qualify = lambda value, environment=None: dict(
            real_qualify(value, environment), qualified=True, refusal=None, problems=[])
    for name, side in sides.items():
        enroll(side, side["store_uuid"], side["path"])
        member(side["path"])
        keys = base / "keys" / name
        keys.mkdir(parents=True, mode=0o700)
        _v117_os.chmod(str(keys), 0o700)
        side["report"] = service.install(
            [str(side["workspace"])], host_trust=str(trust_file), key_directory=str(keys),
            install_root=str(install_root), unit_dir=str(base / "units"), profile=profile, adapters={},
            writable=[str(base / "work")], runner=_v117_Fake())
        side["installed"] = _v117_json.loads(_v117_Path(side["report"]["config"]).read_text())
    a, b = sides["a"], sides["b"]
    held = a["identity"]
    checks.append(("production: the installer hands neither instance a registry of its own, and both are laid "
                   "down in one install root [%s]" % sorted(p.name for p in install_root.iterdir()),
                   all("domain_registry" not in side["installed"] for side in sides.values())
                   and len({_v117_os.path.dirname(side["report"]["home"]) for side in sides.values()}) == 1))

    def started(side, name, label):
        process = _v117_Served(world, side["report"], name)
        up = process.listening()
        checks.append(("production: %s is running and answers its socket [%s]"
                       % (label, "listening" if up else "not listening: " + process.said()), up))
        return process

    def refused_whole(label, side, sent_uuid, proposed, reader, reader_side):
        """A command of `side`, whose binding names `proposed`, sent and judged: it must be refused
        domain_store_conflict naming the committed and the proposed store, and written nowhere."""
        before = {name: _v117_FX.snapshot(each["path"]) for name, each in sides.items()}
        outcome, answer = send(side, sent_uuid, label)
        unchanged = all(_v117_FX.snapshot(each["path"]) == before[name] for name, each in sides.items())
        seen = [r for r in reader.observations("domain_store_conflict") if r.get("proposed") == proposed]
        checks.append(("production: %s is refused domain_store_conflict by the running service, naming the "
                       "committed and the proposed store, and neither store changes [%s; committed %s; stores "
                       "unchanged %s]" % (label, outcome, answer.get("committed"), unchanged),
                       outcome == "refused:domain_store_conflict" and answer.get("committed") == held
                       and answer.get("proposed") == proposed and unchanged))
        checks.append(("production: the refusal of %s is in the observations of %s's instance with the domain, "
                       "the committed and the proposed store [%d found]" % (label, reader_side, len(seen)),
                       bool(seen) and all(r.get("domain_uuid") == domain and r.get("committed") == held
                                          and r.get("outcome") == "refused" for r in seen)))
        records.append({"case": "production: " + label, "committed": held, "proposed": proposed,
                        "command": outcome, "stores_unchanged": unchanged,
                        "passed": outcome == "refused:domain_store_conflict" and unchanged})

    def accepted_once(label, side):
        commands = _v117_commands(side["path"])
        outcome, answer = send(side, side["store_uuid"], label)
        written = _v117_commands(side["path"]) - commands
        checks.append(("production: %s is accepted into the committed store [%s; %d transaction(s); %s]"
                       % (label, outcome, written, answer.get("domain_store")),
                       outcome == "accepted" and written == 1 and answer.get("domain_store") == held))

    for order in (("a", "b"), ("b", "a")):
        again = "" if order == ("a", "b") else ", after both were stopped and started again, the conflicting one first"
        running = {}
        for name in order:
            label = ("the committed store's instance" if name == "a" else "the instance of another store") + again
            running[name] = started(sides[name], name, label)
            if name == "a" and order == ("a", "b"):
                checks.append(("production: the first instance of the domain registers its configured store in the "
                               "install root's registry [%s]" % _v117_registry_rows(registry),
                               _v117_registry_rows(registry) == [held]))
        decisions = [r.get("decision") for r in running["b"].observations("domain_store")]
        checks.append(("production: the instance of another store is told domain_store_conflict at its start and "
                       "the registry holds the committed store alone%s [%s; %s]"
                       % (again, decisions, _v117_registry_rows(registry)),
                       decisions[-1:] == ["domain_store_conflict"] and _v117_registry_rows(registry) == [held]))
        accepted_once("the committed store's own clone" + again, a)
        refused_whole("a clone bound to another store" + again, b, b["store_uuid"], b["identity"], running["b"], "b")
        accepted_once("the committed store's own clone, after the refusal" + again, a)
        if order == ("a", "b"):
            # The second clone bound to the committed file under another store uuid: the committed
            # store's own instance answers, and its comparison is the registry's.
            other = "store117x" + run
            enroll(b, other, a["path"])
            refused_whole("a clone naming another store uuid at the committed file", b, other,
                          _v117_identity(domain, other, a["path"]), running["a"], "a")
            enroll(b, b["store_uuid"], b["path"])
        codes = [running[name].stop() for name in order]
        checks.append(("production: both instances stop on SIGTERM with exit 0%s [%s]" % (again, codes),
                       codes == [0, 0]))
    checks.append(("production: the registry holds the committed store alone at the end [%s]"
                   % _v117_registry_rows(registry), _v117_registry_rows(registry) == [held]))


# ---------------------------------------------------------------------------------------------
# AC2 and AC3: the race, then the restart
# ---------------------------------------------------------------------------------------------

def _v117_race(world, registry, pair, overlap, label, checks):
    """Start an authority for each of `pair` (handle, identity), the first one first. With
    `overlap` the first is held inside its registration until the second has begun its own.
    Returns the two processes and what was seen."""
    seen = {"held_rows": None, "early": None, "began": None}
    one = _v117_Process(world, label + "-first", pair[0][1], pair[0][0].path, registry, hold=overlap)
    if overlap:
        inside = one.event("checked")
        two = _v117_Process(world, label + "-second", pair[1][1], pair[1][0].path, registry, hold=True)
        seen["began"] = two.event("begin")
        seen["early"] = two.event("checked", _v117_OVERLAP)
        # Read while the first is still inside its registration: nothing of it may be visible.
        seen["held_rows"] = _v117_registry_rows(registry)
        one.release()
        seen["first_ready"] = _v117_started(one, checks, label + " first")
        seen["second_checked"] = two.event("checked")
        two.release()
        seen["second_ready"] = _v117_started(two, checks, label + " second")
        checks.append(("%s: the first registration was held inside its transaction [%s]" % (
            label, "reported" if inside else "no report"), inside is not None))
    else:
        seen["first_ready"] = _v117_started(one, checks, label + " first")
        two = _v117_Process(world, label + "-second", pair[1][1], pair[1][0].path, registry)
        seen["second_ready"] = _v117_started(two, checks, label + " second")
    return one, two, seen


def _v117_schedules(world, race_checks, restart_checks, records):
    schedules = [(order, overlap) for overlap in (False, True) for order in ((0, 1), (1, 0))]
    for number, (order, overlap) in enumerate(schedules):
        label = "%s, %s first" % ("overlapped" if overlap else "one after the other", "ab"[order[0]])
        # A short name: every socket of the schedule lies under it, in a worker home that is long already.
        directory = world["scratch"] / ("s%d" % number)
        fx = world["fx"] = _v117_FX.Fixture(ROOT, directory, runtime=world["runtime"])
        if number == 2:
            # The positive control, before the clones are bound to one domain: the fixture's own
            # pair names two domains, so the same overlapped starts must both register.
            registry = directory / "control-registry" / "domains.sqlite3"
            pair = [(h, _v117_identity(h.binding["domain_uuid"], h.binding["store_uuid"], h.path))
                    for h in fx.handles]
            one, two, seen = _v117_race(world, registry, pair, True, "different domains", race_checks)
            sent = [_v117_send(fx, h, "different domains") for h in fx.handles]
            one.stop(), two.stop()
            race_checks.append((
                "different domains: two stores of two domains, started the same overlapped way, both "
                "register and both serve [%s, %s; %s, %s; %d row(s)]"
                % (one.decision(), two.decision(), sent[0][0], sent[1][0], len(_v117_registry_rows(registry))),
                one.decision() == two.decision() == "registered" and sent[0][0] == sent[1][0] == "accepted"
                and sorted(_v117_registry_rows(registry), key=lambda r: r["domain_uuid"])
                == sorted((p[1] for p in pair), key=lambda r: r["domain_uuid"])))
        registry = directory / "registry" / "domains.sqlite3"
        domain = str(_v117_uuid.uuid4())
        pair = []
        for position in order:
            handle = fx.handles[position]
            store_uuid = str(_v117_uuid.uuid4())
            _v117_enroll(fx, handle, domain, store_uuid, handle.path)
            pair.append((handle, _v117_identity(domain, store_uuid, handle.path)))
        (winner, won), (loser, lost) = pair
        before = (_v117_commands(winner.path), _v117_commands(loser.path))
        one, two, seen = _v117_race(world, registry, pair, overlap, label, race_checks)
        first = (seen["first_ready"].get("decision") or {})
        second = (seen["second_ready"].get("decision") or {})
        rows = _v117_registry_rows(registry)
        race_checks.append(("%s: the first store is registered and the second is told domain_store_conflict "
                            "with the first's identity [%s, %s]" % (label, one.decision(), two.decision()),
                            first.get("decision") == "registered" and first.get("committed") == won
                            and second.get("decision") == "domain_store_conflict"
                            and second.get("committed") == won and second.get("proposed") == lost))
        race_checks.append(("%s: the registry holds one row, the whole identity of the winner [%d row(s)]"
                            % (label, len(rows)), rows == [won]))
        if overlap:
            began, ended = seen["began"] or {}, seen["first_ready"]
            race_checks.append((
                "%s: the second attempt began before the first registration ended, got no further while it was "
                "open, and then read the first's commit [began %s; ahead of the commit: %s; read %s]"
                % (label, "before" if began.get("at", 1e18) < ended.get("at", 0) else "not before",
                   "no" if seen["early"] is None else "yes",
                   "the winner" if (seen["second_checked"] or {}).get("committed") == won else "something else"),
                began.get("at", 1e18) < ended.get("at", 0) and seen["early"] is None
                and (seen["second_checked"] or {}).get("committed") == won))
            race_checks.append(("%s: while the first registration was open no row of it was visible [%s]"
                                % (label, seen["held_rows"]), seen["held_rows"] == []))
        sent = (_v117_send(fx, winner, label + " winner"), _v117_send(fx, loser, label + " loser"))
        after = (_v117_commands(winner.path), _v117_commands(loser.path))
        race_checks.append((
            "%s: read back through both clients, the winner's command is accepted naming the winning identity "
            "and the loser's is refused domain_store_conflict naming the same one, with one transaction in the "
            "winner's store and none in the loser's [%s; %s; %s]"
            % (label, sent[0][0], sent[1][0], (after[0] - before[0], after[1] - before[1])),
            sent[0][0] == "accepted" and sent[0][1].get("domain_store") == won
            and sent[1][0] == "refused:domain_store_conflict" and sent[1][1].get("committed") == won
            and (after[0] - before[0], after[1] - before[1]) == (1, 0)))
        earlier = {one.process.pid, two.process.pid}
        one.stop(), two.stop()
        records[_v117_ROWS[1]].append({"schedule": label, "winner": won, "loser": lost,
                        "decisions": [one.decision(), two.decision()], "registry": rows,
                        "clients": [sent[0][0], sent[1][0]]})
        _v117_restart(world, registry, (winner, won), (loser, lost), earlier, label, restart_checks, records)


def _v117_restart(world, registry, winning, losing, earlier, label, checks, records):
    """Both authorities stopped; new processes started in both orders over the same registry and stores."""
    fx = world["fx"]
    (winner, won), (loser, lost) = winning, losing
    # Two other spellings of the winning store's file. The operator's configuration of the restarted
    # authority names it through a symlinked directory. The winning clone's binding, signed over its
    # spelling, names it through a "." step and no link: the client dials the socket beside the
    # path its binding spells, and the gate's mutation worker refuses a connect through a symlinked
    # directory (EACCES), which reddened this row in every baseline there. The step is two bytes,
    # because the worker's home already brings that socket path near the 107 byte limit.
    alias = world["scratch"] / ("alias-%d" % len(world["processes"]))
    alias.symlink_to(winner.path.parent, target_is_directory=True)
    spelled = str(alias / winner.path.name)
    stepped = _v117_os.path.join(str(winner.path.parent), ".", winner.path.name)
    binding = dict(fx.enrollment.read_binding(winner.workspace), store_path=stepped)
    binding["signature"] = fx.signer.sign(fx.enrollment.binding_signed_bytes(binding))
    binding["binding_digest"] = fx.enrollment.binding_digest(binding)
    _v117_Path(fx.enrollment.binding_path(winner.workspace)).write_text(_v117_json.dumps(binding, sort_keys=True))
    for sequence in (("matching", "conflicting"), ("conflicting", "matching")):
        running = []
        for kind in sequence:
            where = "%s, restarted %s first, the %s store" % (label, sequence[0], kind)
            handle, identity = (winner, won) if kind == "matching" else (loser, lost)
            rows_before = _v117_registry_rows(registry)
            commands = _v117_commands(handle.path)
            process = _v117_Process(world, kind, identity, handle.path, registry,
                                    store_path=spelled if kind == "matching" else None)
            running.append(process)
            ready = _v117_started(process, checks, where)
            outcome, answer = _v117_send(fx, handle, where)
            rows_after = _v117_registry_rows(registry)
            written = _v117_commands(handle.path) - commands
            decision = (ready.get("decision") or {})
            checks.append(("%s: the committed record is the winner's identity before and after the proposal "
                           "[%d row(s) before, %d after]" % (where, len(rows_before), len(rows_after)),
                           rows_before == [won] and rows_after == [won]))
            checks.append(("%s: it runs in a new process [pid %s]" % (where, process.process.pid),
                           process.process.pid not in earlier))
            if kind == "matching":
                checks.append((
                    "%s: under another spelling of its path it matches the committed record and its clone's "
                    "command is applied [%s; %s; %d transaction(s)]" % (where, process.decision(), outcome, written),
                    decision.get("decision") == "matching" and decision.get("committed") == won
                    and outcome == "accepted" and answer.get("domain_store") == won
                    and answer.get("store_path") == won["store_path"] and written == 1))
            else:
                checks.append((
                    "%s: it is told domain_store_conflict again and its clone's command is refused by that name "
                    "with nothing written [%s; %s; %d transaction(s)]" % (where, process.decision(), outcome, written),
                    decision.get("decision") == "domain_store_conflict" and decision.get("committed") == won
                    and outcome == "refused:domain_store_conflict" and answer.get("committed") == won
                    and written == 0))
            records[_v117_ROWS[2]].append({"schedule": label, "restart_order": list(sequence), "proposal": kind,
                            "decision": process.decision(), "command": outcome,
                            "record_before": rows_before, "record_after": rows_after})
        for process in running:
            process.stop()
            earlier.add(process.process.pid)


# ---------------------------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------------------------

def _v117_run():
    results = {row: [] for row in _v117_ROWS}
    records = {row: [] for row in _v117_ROWS}
    digests = {}
    with _v117_temp.TemporaryDirectory(prefix="v117-") as scratch:
        scratch = _v117_Path(scratch)
        runtime = scratch / "runtime"
        runtime.mkdir()
        for name, source in _v117_SOURCES.items():
            _v117_shutil.copyfile(source, runtime / name)
        for name in _v117_FX.module_names(ROOT / ".veldo"):
            if name not in _v117_SOURCES:
                _v117_shutil.copyfile(ROOT / ".veldo" / name, runtime / name)
        digests = {name: _v117_hashlib.sha256((runtime / name).read_bytes()).hexdigest()
                   for name in sorted(_v117_SOURCES)}
        runner = scratch / "authority_runner.py"
        runner.write_text(_v117_RUNNER)
        world = {"scratch": scratch, "runtime": runtime, "runner": runner, "processes": [],
                 "enrollment": _v117_FX.load(runtime / "control_enrollment.py")}
        sections = (
            (_v117_ROWS[:1], lambda: _v117_product(world, results[_v117_ROWS[0]], records[_v117_ROWS[0]])),
            (_v117_ROWS[:1], lambda: _v117_production(world, results[_v117_ROWS[0]], records[_v117_ROWS[0]])),
            (_v117_ROWS[1:], lambda: _v117_schedules(world, results[_v117_ROWS[1]], results[_v117_ROWS[2]],
                                                     records)),
        )
        try:
            for rows, section in sections:
                try:
                    section()
                except Exception as error:  # noqa: BLE001 - a raise is reported as a false check of its rows
                    for row in rows:
                        results[row].append(("the section ran to its end (it raised %s: %s)"
                                             % (type(error).__name__, str(error)[:300]), False))
        finally:
            for process in world["processes"]:
                process.stop()
    return results, records, digests


_v117_results, _v117_records, _v117_digests = _v117_run()
_v117_verdicts = {}
for _v117_row in _v117_ROWS:
    _v117_checks = _v117_results[_v117_row]
    _v117_verdicts[_v117_row] = bool(_v117_checks) and all(ok for _, ok in _v117_checks)
    for _v117_words, _v117_ok in _v117_checks:
        if not _v117_ok:
            print("VELDO-0117 %s detail: %s" % (_v117_row, _v117_words))
    # The gate's mutation worker keeps of a false row only the words after the colon of its name
    # (scripts/mutation_observer.py; the printed detail lines are not read there), so a false row
    # says what it saw in its name: a raised section first, then its first false checks.
    _v117_false = sorted((_v117_words for _v117_words, _v117_ok in _v117_checks if not _v117_ok),
                         key=lambda words: "it raised" not in words)
    expect("VELDO-0117 " + _v117_row + ("" if _v117_verdicts[_v117_row] else ": " + (
        " | ".join(words[:300] for words in _v117_false[:3]) or "no check was made")),
        _v117_verdicts[_v117_row])
if _v117_os.environ.get("VELDO_0117_REPORT"):
    # Each result with what produced it: the digests of the four modules the authorities ran and
    # the fixture's version, beside every case's input identities.
    _v117_Path(_v117_os.environ["VELDO_0117_REPORT"]).write_text(_v117_json.dumps({
        "fixture_version": _v117_FX.VERSION, "module_sha256": _v117_digests, "rows": _v117_verdicts,
        "checks": {row: [len(_v117_results[row]), sum(1 for _, ok in _v117_results[row] if ok)]
                   for row in _v117_ROWS},
        "false_checks": {row: [words[:400] for words, ok in _v117_results[row] if not ok] for row in _v117_ROWS},
        "records": _v117_records}, indent=1, sort_keys=True) + "\n")
