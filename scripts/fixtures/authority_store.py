"""Real enrolled Authority/store fixture for VELDO-0115 and later consumers.

No service installation, host locks or detached children. Each handle owns a child,
its pipes, a real enrolled clone and a SQLite file. Snapshot readers use fresh,
read-only sqlite3 connections rather than the authority or store snapshot helpers.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import select
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import uuid

VERSION = "veldo.authority_store_fixture/v1"
HOST = "fixture-host"
MODULES = ("control_client.py", "control_enrollment.py", "control_store.py",
           "git_process.py", "yamlish.py")


def module_names(directory):
    """Carry the registry on runtimes that include the VELDO-0112 prelude."""
    registry = "control_client_registry.py"
    return MODULES + ((registry,) if (Path(directory) / registry).is_file() else ())


def load(path):
    spec = importlib.util.spec_from_file_location("fixture_" + Path(path).stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(value):
    return "sha256:" + hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def snapshot(path):
    """All logical tables, including ones added by a future consumer, in one read transaction."""
    conn = sqlite3.connect(Path(path).as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("BEGIN")
        names = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        return {name: sorted([dict(r) for r in conn.execute(
            'SELECT * FROM "' + name.replace('"', '""') + '"')],
            key=lambda row: json.dumps(row, sort_keys=True)) for name in names}
    finally:
        conn.close()


def watermark(state):
    return max((row["seq"] for row in state["journal"]), default=0)


class Signer:
    """Real disposable Ed25519 signatures for enrollment, requests and journal records."""
    def __init__(self, directory, create=False):
        self.directory = Path(directory)
        self.key = self.directory / "key"
        self.allowed = self.directory / "allowed"
        if create:
            self.directory.mkdir()
            subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(self.key)],
                           check=True, capture_output=True)
            self.allowed.write_text("fixture " + self.key.with_suffix(".pub").read_text())

    def sign(self, payload):
        return subprocess.run(["ssh-keygen", "-Y", "sign", "-f", str(self.key),
                               "-n", "veldo-fixture"], input=payload, check=True,
                              capture_output=True).stdout.decode()

    def verify(self, payload, signature):
        with tempfile.NamedTemporaryFile(dir=self.directory) as sig:
            sig.write(signature.encode())
            sig.flush()
            return subprocess.run(["ssh-keygen", "-Y", "verify", "-f", str(self.allowed),
                                   "-I", "fixture", "-n", "veldo-fixture", "-s", sig.name],
                                  input=payload, capture_output=True).returncode == 0


def command(tag):
    identity = str(uuid.uuid4())
    entity = "fixture:" + identity
    return {"command_id": identity, "nonce": str(uuid.uuid4()), "principal": "fixture",
            "operation": "upsert_entity", "parameters": {
                "entity_id": entity, "kind": "fixture", "data": {"tag": tag}},
            "expected_versions": {entity: 0}, "artifact_digests": []}


class AuthorityHandle:
    def __init__(self, fixture, name):
        self.fixture, self.name = fixture, name
        self.workspace = fixture.directory / name
        fixture.git(fixture.seed, "clone", "-q", str(fixture.seed), str(self.workspace))
        self.path = self.workspace / ".git/veldo/control/control.sqlite3"
        self.binding = fixture.enrollment.enroll(
            self.workspace, str(uuid.uuid4()), str(uuid.uuid4()), str(self.path), HOST, 1,
            fixture.signer.sign, "fixture", "2026-10-28T00:00:00Z")
        self.process = None
        self.ready = None
        with self.open_store() as conn:
            fixture.store.execute(conn, command("positive-control:" + name), "fixture",
                                  fixture.signer.sign, 1, committed_at=1)
        conn.close()
        self.baseline = self.snapshot()

    def open_store(self):
        """A real production write handle; the caller closes it explicitly."""
        return self.fixture.store.open_store(str(self.path))

    def snapshot(self):
        return snapshot(self.path)

    def start(self, peer, ambient=(False, False, False)):
        if self.process is not None:
            raise RuntimeError("authority already started")
        cwd_other, import_other, db_other = ambient
        location = peer if import_other else self
        modules = location.workspace / ".veldo"
        modules.mkdir(exist_ok=True)
        for name in module_names(self.fixture.runtime):
            shutil.copyfile(self.fixture.runtime / name, modules / name)
        cfg = {"modules": str(modules), "path": str(self.path), "peer_path": str(peer.path),
               "binding": self.binding, "key_directory": str(self.fixture.signer.directory)}
        cfgpath = self.workspace / "authority.json"
        cfgpath.write_text(json.dumps(cfg))
        env = dict(os.environ, VELDO_CONTROL_DB=str(peer.path if db_other else self.path),
                   PYTHONDONTWRITEBYTECODE="1")
        for key in ("VELDO_CONTROL_TEST_HARNESS", "VELDO_CONTROL_KILL_AT"):
            env.pop(key, None)
        self.process = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "serve", str(cfgpath)],
            cwd=peer.workspace if cwd_other else self.workspace, env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if not select.select([self.process.stdout], [], [], 20)[0]:
            raise RuntimeError("authority startup produced no readiness record")
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError("authority startup failed: " + self.process.stderr.read())
        self.ready = json.loads(line)
        return self

    def stop(self):
        if self.process is None:
            return
        proc = self.process
        proc.stdin.close()
        proc.wait()
        error = proc.stderr.read()
        proc.stdout.close()
        proc.stderr.close()
        self.process = None
        if proc.returncode != 0:
            raise RuntimeError("authority exit %s: %s" % (proc.returncode, error))

    def kill(self):
        if self.process is not None:
            proc = self.process
            proc.kill()
            proc.wait()
            for stream in (proc.stdin, proc.stdout, proc.stderr):
                stream.close()
            self.process = None


class Fixture:
    def __init__(self, root, directory, runtime=None):
        self.root, self.directory = Path(root), Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.runtime = Path(runtime) if runtime else self.root / ".veldo"
        # Baselines always use the original executor, independently of a mutant server.
        self.store = load(self.root / ".veldo/control_store.py")
        self.enrollment = load(self.root / ".veldo/control_enrollment.py")
        self.client = load(self.root / ".veldo/control_client.py")
        self.signer = Signer(self.directory / "signing", create=True)
        self.seed = self.directory / "seed"
        self.seed.mkdir()
        self.git(self.seed, "init", "-q")
        (self.seed / "seed").write_text("real clone fixture\n")
        self.git(self.seed, "add", "seed")
        self.git(self.seed, "-c", "user.name=Veldo Fixture", "-c",
                 "user.email=fixture@veldo.invalid", "commit", "-q", "-m", "fixture seed")
        self.handles = []
        for name in ("a", "b"):
            self.handles.append(AuthorityHandle(self, name))

    @staticmethod
    def git(repo, *args):
        return subprocess.run(["git", "-C", str(repo), *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    def send(self, handle, cmd, client=None):
        client = client or self.client
        return client.send(handle.workspace, cmd, self.enrollment, self.signer.verify,
                           self.signer.sign, HOST)

    def close(self):
        errors = []
        for handle in self.handles:
            try:
                handle.stop()
            except Exception as exc:
                errors.append(exc)
        if errors:
            raise errors[0]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def serve(config):
    """The existing apply seam delegates directly to production control_store.execute."""
    cfg = json.loads(Path(config).read_text())
    modules = Path(cfg["modules"])
    client, enrollment, store = [load(modules / name) for name in MODULES[:3]]
    signer = Signer(cfg["key_directory"])
    conn = store.open_store(cfg["path"])
    peer_conn = store.open_store(cfg["peer_path"])
    binding = cfg["binding"]

    def apply(cmd):
        return store.execute(conn, cmd, "fixture", signer.sign, 1, committed_at=2)

    authority = client.Authority(
        binding["store_uuid"], binding["domain_uuid"], cfg["path"], enrollment,
        signer.verify, HOST, apply,
        watermark=lambda: conn.execute("SELECT COALESCE(MAX(seq),0) FROM journal").fetchone()[0])
    listener = client.bind(client.socket_path_for(binding))
    try:
        print(json.dumps({"pid": os.getpid(), "cwd": os.getcwd(), "modules": str(modules),
                          "environment_db": os.environ.get("VELDO_CONTROL_DB"),
                          "binding": binding, "database": conn.execute("PRAGMA database_list").fetchall(),
                          "module_digests": {name: hashlib.sha256((modules / name).read_bytes()).hexdigest()
                                             for name in module_names(modules)}}), flush=True)
        while True:
            readable, _, _ = select.select([sys.stdin, listener], [], [])
            if sys.stdin in readable:
                break
            client.serve_one(listener, authority)
    finally:
        listener.close()
        conn.close()
        peer_conn.close()
        Path(client.socket_path_for(binding)).unlink(missing_ok=True)


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "serve":
        raise SystemExit("usage: authority_store.py serve CONFIG")
    serve(sys.argv[2])
