"""VELDO-0114: the relay opens no service and starts no second process during its whole invocation.

This fragment is executed by scripts/selftest.py into shared.py's namespace, like every other
fragment, and its declared prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 113_veldo_0114_relay_census

Direct execution (python3 -B scripts/suites/113_veldo_0114_relay_census.py) prints the rows, the
stood-down rows and the evidence as JSON.

WHAT IS MEASURED. .veldo/control_relay.py runs as the root of a VELDO-0111 lifecycle census
(scripts/fixtures/lifecycle_census.py): a PTRACE_TRACEME root that execs the relay with the request
on its standard input, traced from before the relay executable runs until it returns and every
descendant has drained. The endpoints it talks to (a real authority judging signed requests, and
plain fixture endpoints for the limit and refusal exchanges) are listening in this process BEFORE
the call, so they are setup outside the measured scope. Every socket the relay opens is inside it,
whatever its family or address. Connecting is allowed; a service event (a transition to listening
or a service receive binding) or any task the relay creates is not.

WHAT A ROW MEANS. A row is judged from complete census receipts only, one per invocation. When any
receipt is missing or INCOMPLETE (no ptrace, a denied or lost observation, a dead collector, an
unqualified host), every row VELDO-0111 names for VELDO-0114 STANDS DOWN with census_incomplete: it
is printed by name and recorded, never passed. The fixture-local pathname snapshots the VELDO-0108
row used are still taken and carried beside each invocation, and the judge never consults them.
relay/stand-down-is-not-green holds the judge to that on every VELDO-0111 fault, wherever this
runs, because fault injection checks propagation without needing a qualified host.

QUALIFICATION. Copies of the relay that open and close one transient service before forwarding
(IPv4 and IPv6 listeners, an IPv4 datagram receive binding, pathname Unix in and out of the fixture
directory, abstract Unix) and copies that fork a short-lived or reparented helper must each be seen
by the same census and judge, so neither an address nor a short life narrows the claim.
"""
import concurrent.futures as _v114_cf
import hashlib as _v114_hashlib
import hmac as _v114_hmac
import importlib.util as _v114_ilu
import json as _v114_json
import os as _v114_os
import select as _v114_select
import shutil as _v114_shutil
import socket as _v114_socket
import subprocess as _v114_sp
import sys as _v114_sys
import tempfile as _v114_tf
import threading as _v114_threading
from pathlib import Path as _v114_Path

if __name__ == "__main__":
    ROOT = _v114_Path(__file__).resolve().parents[2]
    _v114_direct_rows = []

    def expect(name, condition):
        _v114_direct_rows.append([name.split(":", 1)[0], bool(condition)])

# A hang detector only, never a pass condition and never a measure of this host (load rule).
_v114_HANG = 300
_v114_tmp = _v114_Path(_v114_tf.mkdtemp(prefix="v114"))
_v114_outside = _v114_Path(_v114_tf.mkdtemp(prefix="v114-elsewhere"))


def _v114_load(name, path):
    spec = _v114_ilu.spec_from_file_location(name, path)
    module = _v114_ilu.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


LC114 = _v114_load("v114_lifecycle_census", ROOT / "scripts" / "fixtures" / "lifecycle_census.py")
_v114_ROWS = tuple(LC114.CONSUMERS["VELDO-0114"])
_v114_RELAY_SOURCE = (ROOT / ".veldo" / "control_relay.py").read_text()
_v114_FORWARD = "        answer = forward(address, payload)\n"
_v114_CONNECT = "    conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)\n"


def _v114_relay_copy(tag, anchor=None, insert=""):
    """A directory holding a relay (with one insertion before an exact anchor) and its registry."""
    directory = _v114_tmp / ("relay_" + tag)
    directory.mkdir()
    _v114_shutil.copy2(ROOT / ".veldo" / "control_client_registry.py", directory / "control_client_registry.py")
    source = _v114_RELAY_SOURCE
    if anchor is not None:
        if source.count(anchor) != 1:
            raise RuntimeError("VELDO-0114 relay probe anchor moved: " + tag)
        source = source.replace(anchor, insert + anchor)
    (directory / "control_relay.py").write_text(source)
    return directory / "control_relay.py"


RL114 = _v114_load("v114_relay", _v114_relay_copy("main"))
_v114_RELAY = _v114_tmp / "relay_main" / "control_relay.py"

# The measured root: read the launch description, put the request on standard input, and exec the
# relay. It never forks unless a fault drive asks it to give the collector a birth to fault on.
_v114_LAUNCHER = (
    "import json, os, sys\n"
    "c = json.load(open(sys.argv[1]))\n"
    "fd = os.open(c['stdin'], os.O_RDONLY)\n"
    "os.dup2(fd, 0)\n"
    "os.close(fd)\n"
    "if c.get('fork_first'):\n"
    "    p = os.fork()\n"
    "    if p == 0:\n"
    "        os._exit(0)\n"
    "    os.waitpid(p, 0)\n"
    "os.execve(c['argv'][0], c['argv'], dict(os.environ, **c.get('env', {})))\n")


def _v114_place(tag):
    """Each invocation's own fixture directory, so concurrent invocations never share a snapshot."""
    place = _v114_tmp / tag
    place.mkdir(exist_ok=True)
    return place


def _v114_unix_paths(prefix):
    """The VELDO-0108 evidence: the kernel's pathname Unix socket table under the fixture."""
    try:
        text = open("/proc/net/unix").read()
    except OSError:
        return None
    return sorted({parts[-1] for parts in (line.split() for line in text.splitlines()[1:])
                   if len(parts) >= 8 and parts[-1].startswith(prefix)})


class _V114Endpoint:
    """A listening endpoint of this process, established BEFORE the measured call (setup, outside
    the measured scope). It serves at most one connection. It stops on an event, never a clock: the
    census returns only after the relay and every descendant have exited, and then the stop pipe
    wakes a thread still waiting for a connection that will never come."""

    def __init__(self, tag, serve):
        self.address = str(_v114_place(tag) / "endpoint.sock")
        self.server = _v114_socket.socket(_v114_socket.AF_UNIX, _v114_socket.SOCK_STREAM)
        self.server.bind(self.address)
        self.server.listen(4)
        self.serve, self.received, self.error = serve, [], None
        self.stop_read, self.stop_write = _v114_os.pipe()
        self.thread = _v114_threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        try:
            ready, _, _ = _v114_select.select([self.server, self.stop_read], [], [], _v114_HANG)
            if self.server in ready:
                self.serve(self)
        except OSError as exc:
            self.error = repr(exc)

    def finish(self):
        _v114_os.write(self.stop_write, b"x")
        self.thread.join(_v114_HANG)
        self.server.close()
        for fd in (self.stop_read, self.stop_write):
            _v114_os.close(fd)
        return not self.thread.is_alive()


def _v114_answer_with(response):
    def serve(endpoint):
        conn, _ = endpoint.server.accept()
        with conn:
            conn.settimeout(_v114_HANG)
            chunks = []
            while True:
                chunk = conn.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
            endpoint.received.append(b"".join(chunks))
            conn.sendall(response)
    return serve


def _v114_invoke(tag, relay, address, payload, env=None, fork_first=False, fault=None, serve=None):
    """One relay invocation, measured by one census, with the old snapshots carried beside it."""
    endpoint = _V114Endpoint(tag, serve) if serve is not None else None
    target = endpoint.address if endpoint is not None else address
    stdin = _v114_place(tag) / "stdin"
    stdin.write_bytes(payload)
    launch = _v114_place(tag) / "launch.json"
    launch.write_text(_v114_json.dumps(dict(
        stdin=str(stdin), env=env or {}, fork_first=fork_first,
        argv=[_v114_sys.executable, "-B", str(relay), target])))
    before = _v114_unix_paths(str(_v114_place(tag)) + "/")
    receipt = LC114.census([_v114_sys.executable, "-B", "-c", _v114_LAUNCHER, str(launch)],
                           identity="VELDO-0114/" + tag, cwd=str(_v114_place(tag)), fault=fault)
    after = _v114_unix_paths(str(_v114_place(tag)) + "/")
    drained = endpoint.finish() if endpoint is not None else True
    status = receipt.get("root_status")
    return dict(tag=tag, receipt=receipt, snapshots=(before, after), endpoint_drained=drained,
                exit=_v114_os.waitstatus_to_exitcode(status) if isinstance(status, int) else None,
                stdout=receipt.get("stdout", ""), stderr=receipt.get("stderr", ""),
                received=list(endpoint.received) if endpoint is not None else None,
                endpoint_error=endpoint.error if endpoint is not None else None)


def _v114_ready(receipt):
    return isinstance(receipt, dict) and all(
        row["status"] == "READY" for row in LC114.consumer_rows(receipt, "VELDO-0114"))


def _v114_judge(invocations, comparison=None):
    """One verdict for each row VELDO-0111 names for VELDO-0114, from census receipts alone.

    Every invocation must carry its own complete receipt, or every row stands down with
    census_incomplete. The pathname snapshots each invocation carries are never read here: matching
    snapshots are what the old row saw, and they do not observe a transient or out-of-directory
    service. `comparison` is the composite row's endpoint/judgement comparison; it can fail the
    composite, never pass it without the census."""
    receipts = [invocation.get("receipt") for invocation in invocations]
    ready = bool(invocations) and all(_v114_ready(receipt) for receipt in receipts)
    one_each = ready and len({receipt["input_identity"] for receipt in receipts}) == len(invocations)
    if not (ready and one_each):
        return {name: dict(status="STANDS DOWN", reason="census_incomplete") for name in _v114_ROWS}
    services = [dict(invocation=invocation["tag"], family=event.get("family"), type=event.get("type"),
                     operation=event.get("operation"), address=event.get("address"))
                for invocation in invocations for event in invocation["receipt"]["events"]
                if event.get("kind") == "service"]
    births = [dict(invocation=invocation["tag"], identity=task["identity"], operation=task["operation"])
              for invocation in invocations for task in invocation["receipt"]["processes"]
              if not task["root"]]
    listener = dict(status="FAIL" if services else "PASS", reason="relay_listener" if services else None,
                    services=services)
    process = dict(status="FAIL" if births else "PASS", reason="relay_child_process" if births else None,
                   births=births)
    composite_ok = comparison is True and listener["status"] == "PASS"
    return {
        "relay/one-endpoint-one-judgement": dict(
            status="PASS" if composite_ok else "FAIL",
            reason=None if composite_ok else ("comparison_failed" if comparison is not True
                                              else "relay_listener")),
        "relay/no-listener-during-call": listener,
        "relay/no-second-process": process,
        "relay/listener-proof-needs-census": dict(status="PASS", reason=None,
                                                  receipts=len(receipts)),
    }


def _v114_record(invocation):
    """What a reader needs to bind a result to its input, without the receipt's bulk."""
    receipt = invocation["receipt"]
    services = {}
    for event in receipt.get("events", []):
        if event.get("kind") == "service":
            key = str(event.get("family"))
            services[key] = services.get(key, 0) + 1
    root = [task for task in receipt.get("processes", []) if task.get("root")]
    return dict(
        invocation=invocation["tag"], exit=invocation["exit"], status=receipt.get("status"),
        capture_status=receipt.get("capture_status"),
        qualification=(receipt.get("qualification") or {}).get("status"),
        failures=[failure.get("capability") for failure in receipt.get("failures", [])],
        input_identity=receipt.get("input_identity"), input_digest=receipt.get("input_digest"),
        implementation_digest=receipt.get("implementation_digest"),
        fixture_version=receipt.get("fixture_version"), host=receipt.get("host"),
        root_launch=[dict(identity=task["identity"], operation=task["operation"],
                          execs=len(task.get("execs", []))) for task in root],
        births=sum(not task.get("root") for task in receipt.get("processes", [])),
        service_events_by_family=services,
        sockets=[dict(family=o.get("family"), type=o.get("type")) for o in receipt.get("sockets", [])],
        snapshots_equal=invocation["snapshots"][0] == invocation["snapshots"][1],
        consumer_rows=LC114.consumer_rows(receipt, "VELDO-0114"))


_v114_evidence = dict(schema="veldo.relay-census-evidence/v1", rows=list(_v114_ROWS), exchanges=[],
                      listener_probes=[], process_probes=[], faults=[], stood_down=[], verdicts={})


def _v114_emit(label, name, verdict, text):
    """A verdict becomes a row; a stand-down is printed by name and recorded, never passed."""
    _v114_evidence["verdicts"][name] = {k: v for k, v in verdict.items() if k in ("status", "reason")}
    if verdict["status"] == "STANDS DOWN":
        _v114_evidence["stood_down"].append(dict(row=name, reason=verdict["reason"]))
        print("   VELDO-0114 %s %s: STANDS DOWN (%s), recorded and NOT passed; the obligation is "
              "unproven on this host and qualification is incomplete" % (label, name, verdict["reason"]))
        return
    expect("VELDO-0114 %s %s: %s" % (label, name, text), verdict["status"] == "PASS")


# ---- the endpoints: a real authority judging signed requests, set up outside the scope -----------
_v114_have_git = _v114_shutil.which("git") is not None
_v114_KEY = b"the relay never sees this key"
_v114_HOST = "workstation-114"


def _v114_sign(payload):
    return "hmac-sha256:" + _v114_hmac.new(_v114_KEY, payload, _v114_hashlib.sha256).hexdigest()


def _v114_verify(payload, signature):
    return _v114_hmac.compare_digest(_v114_sign(payload), signature)


_v114_authority = None
_v114_applied = []
if _v114_have_git:
    # The production authority modules, loaded in place: they are the endpoint, never under test here.
    EN114 = _v114_load("v114_enroll", ROOT / ".veldo" / "control_enrollment.py")
    CC114 = _v114_load("v114_client", ROOT / ".veldo" / "control_client.py")
    _v114_repo = _v114_tmp / "repo"
    _v114_repo.mkdir()
    _v114_genv = dict(_v114_os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                      GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    for _v114_args in (["init", "-q"], ["checkout", "-q", "-b", "trunk"]):
        _v114_sp.run(["git", "-C", str(_v114_repo), *_v114_args], check=True, capture_output=True,
                     env=_v114_genv)
    (_v114_repo / "seed.txt").write_text("seed\n")
    _v114_sp.run(["git", "-C", str(_v114_repo), "add", "-A"], check=True, capture_output=True, env=_v114_genv)
    _v114_sp.run(["git", "-C", str(_v114_repo), "commit", "-q", "-m", "seed"], check=True,
                 capture_output=True, env=_v114_genv)
    _v114_store = str(_v114_tmp / "auth" / "control.sqlite3")
    _v114_binding = EN114.enroll(_v114_repo, "dom-114", "store-114", _v114_store, _v114_HOST, 1,
                                 _v114_sign, "owner", "2026-11-22T00:00:00Z")

    def _v114_apply(command):
        _v114_applied.append(command)
        return {"applied": True, "operation": command.get("operation")}

    _v114_authority = CC114.Authority("store-114", "dom-114", _v114_store, EN114, _v114_verify, _v114_HOST,
                                      _v114_apply, watermark=lambda: len(_v114_applied))

    def _v114_serve_authority(endpoint):
        # Judged by the production serving path, with a read bound that only detects a hang.
        endpoint.received.append(CC114.serve_one(endpoint.server, _v114_authority, timeout=_v114_HANG))


def _v114_signed(command_id):
    return _v114_json.dumps(CC114.build_request(_v114_repo, _v114_binding,
                                                {"operation": "upsert", "id": command_id},
                                                _v114_sign)).encode()


def _v114_answer(invocation):
    try:
        return _v114_json.loads(invocation["stdout"]) if invocation["stdout"] else None
    except ValueError:
        return None


# ---- the invocation set: every exchange outcome, each under its own census ---------------------
_v114_MAX = RL114.MAX_BYTES
_v114_exchanges = []
_v114_exchange_ok = []
if _v114_authority is not None:
    _v114_valid = _v114_signed("relayed-114")
    for _v114_tag, _v114_payload, _v114_expect in (
            ("successful", _v114_valid,
             lambda a: a.get("accepted") is True),
            ("refused", _v114_valid.replace(b'"relayed-114"', b'"tampered-114"'),
             lambda a: a.get("accepted") is False and a.get("reason") == "command_signature_invalid"),
            ("empty", b"",
             lambda a: a.get("accepted") is False and a.get("reason") == "malformed_request"),
            ("limit-sized-request", b"x" * _v114_MAX,
             lambda a: a.get("accepted") is False and a.get("reason") == "malformed_request")):
        _v114_inv = _v114_invoke(_v114_tag, _v114_RELAY, None, _v114_payload, serve=_v114_serve_authority)
        _v114_exchanges.append(_v114_inv)
        _v114_got = _v114_answer(_v114_inv)
        _v114_exchange_ok.append((_v114_tag, _v114_inv["exit"] == RL114.EXIT_OK and isinstance(_v114_got, dict)
                                  and _v114_expect(_v114_got) and _v114_inv["endpoint_drained"]
                                  and len(_v114_inv["received"]) == 1))


def _v114_plain(tag, payload, response=None, address=None, expect_exit=0, expect_stdout=""):
    """A non-authority exchange: the limit-sized response and the relay's transport refusals."""
    inv = _v114_invoke(tag, _v114_RELAY, address, payload,
                       serve=_v114_answer_with(response) if response is not None else None)
    ok = (inv["exit"] == expect_exit and inv["stdout"] == expect_stdout and inv["endpoint_drained"]
          and (response is None or inv["received"] == [payload]))
    return inv, ok


for _v114_tag, _v114_kwargs in (
        ("limit-sized-response", dict(payload=b"request", response=b"y" * _v114_MAX,
                                      expect_stdout="y" * _v114_MAX)),
        ("transport-unreachable", dict(payload=b"request", address=str(_v114_tmp / "absent" / "nobody.sock"),
                                       expect_exit=RL114.EXIT_UNREACHABLE)),
        ("transport-oversized-request", dict(payload=b"x" * (_v114_MAX + 1),
                                             address=str(_v114_tmp / "absent" / "never-dialled.sock"),
                                             expect_exit=RL114.EXIT_TOO_LARGE)),
        ("transport-oversized-response", dict(payload=b"request", response=b"y" * (_v114_MAX + 1),
                                              expect_exit=RL114.EXIT_TOO_LARGE))):
    _v114_inv, _v114_ok = _v114_plain(_v114_tag, **_v114_kwargs)
    _v114_exchanges.append(_v114_inv)
    _v114_exchange_ok.append((_v114_tag, _v114_ok))
_v114_evidence["exchanges"] = [dict(_v114_record(inv), outcome_as_expected=ok)
                               for inv, (_, ok) in zip(_v114_exchanges, _v114_exchange_ok)]
_v114_outcomes_ok = (_v114_authority is not None and len(_v114_exchange_ok) == 8
                     and all(ok for _, ok in _v114_exchange_ok))
_v114_live = _v114_judge(_v114_exchanges)


# ---- qualification: the same census and judge must see every kind of transient service ---------
def _v114_listener_probe(tag, family, code, name_hex=None):
    relay = _v114_relay_copy("probe-" + tag, _v114_FORWARD, code)
    inv = _v114_invoke("probe-" + tag, relay, None, b"probe", serve=_v114_answer_with(b"probe-answer"))
    return inv, family, name_hex


_v114_inside_path = str(_v114_place("probe-unix-pathname-listener") / "transient.sock")
_v114_outside_path = str(_v114_outside / "transient.sock")
_v114_abstract = "v114-transient-%d" % _v114_os.getpid()
_v114_LISTENER_PROBES = (
    ("ipv4-listener", 2, "        _p = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n"
                         "        _p.bind(('127.0.0.1', 0)); _p.listen(1); _p.close()\n", None),
    ("ipv6-listener", 10, "        _p = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)\n"
                          "        _p.bind(('::1', 0)); _p.listen(1); _p.close()\n", None),
    ("ipv4-datagram-binding", 2, "        _p = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)\n"
                                 "        _p.bind(('127.0.0.1', 0)); _p.close()\n", None),
    ("unix-pathname-listener", 1, "        _p = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)\n"
                                  "        _p.bind(%r); _p.listen(1); _p.close(); os.unlink(%r)\n"
                                  % (_v114_inside_path, _v114_inside_path),
     _v114_inside_path.encode().hex()),
    ("unix-out-of-directory-listener", 1, "        _p = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)\n"
                                          "        _p.bind(%r); _p.listen(1); _p.close(); os.unlink(%r)\n"
                                          % (_v114_outside_path, _v114_outside_path),
     _v114_outside_path.encode().hex()),
    ("unix-abstract-listener", 1, "        _p = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)\n"
                                  "        _p.bind('\\0' + %r); _p.listen(1); _p.close()\n" % _v114_abstract,
     (b"\0" + _v114_abstract.encode()).hex()),
)
_v114_PROCESS_PROBES = (
    ("short-lived-child", "    _h = os.fork()\n    if _h == 0:\n        os._exit(0)\n    os.waitpid(_h, 0)\n", 1),
    ("reparented-grandchild", "    _h = os.fork()\n    if _h == 0:\n        if os.fork() == 0:\n"
                              "            os._exit(0)\n        os._exit(0)\n    os.waitpid(_h, 0)\n", 2),
)


def _v114_process_probe(tag, code, births):
    relay = _v114_relay_copy("probe-" + tag, _v114_CONNECT, code)
    inv = _v114_invoke("probe-" + tag, relay, None, b"probe", serve=_v114_answer_with(b"probe-answer"))
    return inv, births


# The census's own fault matrix, driven through relay invocations. loss and collector_death fault
# on a birth event, so those launches fork one helper first; the relay itself is unchanged.
_v114_FAULT_FORKS = ("loss", "collector_death")

with _v114_cf.ThreadPoolExecutor(max_workers=4) as _v114_pool:
    _v114_listener_jobs = [_v114_pool.submit(_v114_listener_probe, *probe) for probe in _v114_LISTENER_PROBES]
    _v114_process_jobs = [_v114_pool.submit(_v114_process_probe, *probe) for probe in _v114_PROCESS_PROBES]
    _v114_fault_jobs = [(fault, _v114_pool.submit(
        _v114_invoke, "fault-" + fault, _v114_RELAY, None, b"fault",
        fork_first=fault in _v114_FAULT_FORKS, fault=fault, serve=_v114_answer_with(b"fault-answer")))
        for fault in LC114.FAULTS]
    _v114_listener_results = [job.result() for job in _v114_listener_jobs]
    _v114_process_results = [job.result() for job in _v114_process_jobs]
    _v114_fault_results = [(fault, job.result()) for fault, job in _v114_fault_jobs]


def _v114_probe_seen(inv, family, name_hex):
    """Complete, forwarded, and judged a relay_listener with this family (and exact Unix name)."""
    verdict = _v114_judge([inv])["relay/no-listener-during-call"]
    if verdict["status"] == "STANDS DOWN" or inv["exit"] != 0:
        # No complete census, or the host could not open this service at all (no IPv6, say):
        # the claim is not qualified for this address kind here, which is never a pass.
        return "stands down"
    hits = [s for s in verdict.get("services", []) if s["family"] == family
            and (name_hex is None or name_hex in _v114_json.dumps(s["address"]))]
    return (verdict["status"] == "FAIL" and verdict["reason"] == "relay_listener" and bool(hits)
            and inv["exit"] == 0 and inv["stdout"] == "probe-answer")


def _v114_birth_seen(inv, births):
    verdict = _v114_judge([inv])["relay/no-second-process"]
    if verdict["status"] == "STANDS DOWN":
        return "stands down"
    return (verdict["status"] == "FAIL" and verdict["reason"] == "relay_child_process"
            and len(verdict["births"]) == births and inv["exit"] == 0 and inv["stdout"] == "probe-answer")


_v114_listener_seen = [_v114_probe_seen(*result) for result in _v114_listener_results]
_v114_births_seen = [_v114_birth_seen(*result) for result in _v114_process_results]
_v114_evidence["listener_probes"] = [dict(_v114_record(inv), probe=probe[0], family=family, seen=seen)
                                     for probe, (inv, family, _), seen in
                                     zip(_v114_LISTENER_PROBES, _v114_listener_results, _v114_listener_seen)]
_v114_evidence["process_probes"] = [dict(_v114_record(inv), probe=probe[0], seen=seen)
                                    for probe, (inv, _), seen in
                                    zip(_v114_PROCESS_PROBES, _v114_process_results, _v114_births_seen)]


def _v114_qualified(seen):
    """True when every probe was seen, None when any stood down, False when a complete census missed one."""
    if any(s is not True and s != "stands down" for s in seen):
        return False
    return None if any(s == "stands down" for s in seen) else True


def _v114_with_qualification(verdict, qualified, outcomes_ok):
    """A live verdict can pass only on a qualified census and the full set of exchange outcomes."""
    if verdict["status"] == "STANDS DOWN":
        return verdict
    if qualified is None:
        return dict(status="STANDS DOWN", reason="census_incomplete")
    if qualified is False:
        return dict(verdict, status="FAIL", reason="census_missed_a_probe")
    if not outcomes_ok:
        return dict(verdict, status="FAIL", reason="invocation_set_incomplete")
    return verdict


# ---- stand-down propagation: every fault, a missing receipt and a mixed set ----------------------
def _v114_relay_qualification(verdicts):
    """The relay claim's own qualification: complete only when no row stood down. A faulted capture
    on a host whose census qualifies is still an incomplete relay qualification."""
    return "INCOMPLETE" if any(v["status"] == "STANDS DOWN" for v in verdicts.values()) else "COMPLETE"


_v114_contract = []
for _v114_fault, _v114_inv in _v114_fault_results:
    _v114_r = _v114_inv["receipt"]
    _v114_capability = LC114.FAULTS[_v114_fault][2]
    _v114_verdicts = _v114_judge([_v114_inv], comparison=True)
    _v114_contract.append(dict(
        case="fault-" + _v114_fault,
        # The drive counts only when the receipt really is incomplete; which capability failed is
        # recorded (a host without ptrace fails earlier than the injected fault would).
        injected=_v114_r.get("status") == "INCOMPLETE",
        failed=sorted({f.get("capability") for f in _v114_r.get("failures", [])}),
        fault_capability_seen=any(f.get("capability") == _v114_capability for f in _v114_r.get("failures", [])),
        snapshots_equal=_v114_inv["snapshots"][0] == _v114_inv["snapshots"][1],
        census_status=_v114_r.get("status"),
        host_qualification=(_v114_r.get("qualification") or {}).get("status"),
        qualification=_v114_relay_qualification(_v114_verdicts),
        stood_down=[name for name, v in _v114_verdicts.items()
                    if v["status"] == "STANDS DOWN" and v["reason"] == "census_incomplete"],
        green=[name for name, v in _v114_verdicts.items() if v["status"] == "PASS"]))
_v114_evidence["faults"] = [dict(_v114_record(inv), fault=fault) for fault, inv in _v114_fault_results]
# A complete receipt beside a missing one, and an invocation with no receipt at all.
# The last two need one complete receipt, so a host without a qualified census drives the faults
# and the missing receipt only.
_v114_complete = [inv for inv in _v114_exchanges if _v114_ready(inv["receipt"])][:1]
_v114_sets = [("missing-receipt", [dict(tag="missing", receipt=None, snapshots=([], []))])]
if _v114_complete:
    _v114_sets += [("mixed-set", _v114_complete + [dict(_v114_fault_results[0][1], tag="mixed-incomplete")]),
                   ("shared-receipt", _v114_complete + [dict(_v114_complete[0], tag="reused")])]
for _v114_case, _v114_set in _v114_sets:
    _v114_verdicts = _v114_judge(_v114_set, comparison=True)
    _v114_contract.append(dict(
        case=_v114_case, injected=bool(_v114_set), snapshots_equal=all(
            inv["snapshots"][0] == inv["snapshots"][1] for inv in _v114_set),
        qualification=_v114_relay_qualification(_v114_verdicts),
        stood_down=[name for name, v in _v114_verdicts.items()
                    if v["status"] == "STANDS DOWN" and v["reason"] == "census_incomplete"],
        green=[name for name, v in _v114_verdicts.items() if v["status"] == "PASS"]))
_v114_evidence["contract"] = _v114_contract
_v114_contract_ok = (
    len(_v114_contract) == len(LC114.FAULTS) + len(_v114_sets) and _v114_ROWS == (
        "relay/one-endpoint-one-judgement", "relay/no-listener-during-call",
        "relay/no-second-process", "relay/listener-proof-needs-census")
    and all(c["injected"] and c["snapshots_equal"] and c["qualification"] == "INCOMPLETE"
            and c["stood_down"] == list(_v114_ROWS) and not c["green"] for c in _v114_contract))

expect("VELDO-0114 AC3 relay/stand-down-is-not-green: every VELDO-0111 fault (unavailable facilities, "
       "denied ptrace, unsupported ABI, a corrupt or lost event stream, a killed collector, drain expiry "
       "and finalization failure) driven through a relay invocation, a missing receipt, a complete "
       "receipt beside an incomplete one and one receipt shared by two invocations each leave all four "
       "VELDO-0114 rows STANDS DOWN with census_incomplete and none green, with qualification "
       "INCOMPLETE, even though the fixture's pathname snapshots match and the composite's comparison "
       "is supplied as true. This needs no qualified host: it checks propagation, not absence",
       _v114_contract_ok)

# ---- the live rows ---------------------------------------------------------------------------------
_v114_listeners_qualified = _v114_qualified(_v114_listener_seen)
_v114_births_qualified = _v114_qualified(_v114_births_seen)
_v114_metrics = dict(
    invocations=len(_v114_exchanges),
    births=sum(not t["root"] for inv in _v114_exchanges for t in inv["receipt"].get("processes", [])),
    service_events_by_family={})
for _v114_inv in _v114_exchanges:
    for _v114_fam, _v114_n in _v114_record(_v114_inv)["service_events_by_family"].items():
        _v114_metrics["service_events_by_family"][_v114_fam] = (
            _v114_metrics["service_events_by_family"].get(_v114_fam, 0) + _v114_n)
_v114_evidence["metrics"] = _v114_metrics
_v114_root_launches = all(
    len([t for t in inv["receipt"].get("processes", []) if t.get("root")]) == 1
    and [t for t in inv["receipt"]["processes"] if t.get("root")][0]["operation"] == "root"
    and len([t for t in inv["receipt"]["processes"] if t.get("root")][0]["execs"]) >= 1
    for inv in _v114_exchanges if _v114_ready(inv["receipt"]))

if _v114_authority is None:
    for _v114_name in _v114_ROWS[1:]:
        _v114_emit("AC1-AC3", _v114_name, dict(status="STANDS DOWN", reason="authority_fixture_unavailable"),
                   "")
else:
    _v114_emit("AC1", "relay/no-listener-during-call", _v114_with_qualification(
        _v114_live["relay/no-listener-during-call"], _v114_listeners_qualified, _v114_outcomes_ok),
        "the relay run as the root of a VELDO-0111 census, from before its executable runs through its "
        "exit and descendant drain, on successful, refused, empty, limit-sized (both directions) and "
        "transport-error (unreachable, oversized request, oversized response) exchanges, makes no "
        "service event of any family: no listen and no service receive binding, even transiently, with "
        "a complete receipt for every invocation. Qualified the same run: relay copies opening and "
        "closing an IPv4 listener, an IPv6 listener, an IPv4 datagram binding, a pathname Unix listener "
        "in and out of the fixture directory and an abstract Unix listener before forwarding are each "
        "judged relay_listener with that family and exact Unix name")
    _v114_emit("AC2", "relay/no-second-process", _v114_with_qualification(
        dict(_v114_live["relay/no-second-process"], status=(
            _v114_live["relay/no-second-process"]["status"] if _v114_root_launches
            or _v114_live["relay/no-second-process"]["status"] == "STANDS DOWN" else "FAIL")),
        _v114_births_qualified, _v114_outcomes_ok),
        "over the same invocation set, measured from before relay startup through exit and descendant "
        "drain, the census records exactly one task per invocation, the intended relay root launch "
        "(recorded separately, with its execs), and zero tasks the relay created. The authority and "
        "every endpoint are processes of this suite set up before the call, outside the measured "
        "scope, never exempted by name. Qualified the same run: a relay copy forking a short-lived "
        "helper before connecting and one whose helper's child is reparented are judged "
        "relay_child_process with one and two births")
    _v114_emit("AC3", "relay/listener-proof-needs-census", _v114_with_qualification(
        dict(_v114_live["relay/listener-proof-needs-census"],
             status=_v114_live["relay/listener-proof-needs-census"]["status"] if _v114_contract_ok
             or _v114_live["relay/listener-proof-needs-census"]["status"] == "STANDS DOWN" else "FAIL"),
        True, _v114_outcomes_ok),
        "every live invocation consumed its own complete census receipt, and on every fault, missing, "
        "mixed and shared receipt all four rows stood down with census_incomplete although the "
        "pathname snapshots matched: snapshot equality never substitutes for a failed observer")
    if _v114_live["relay/one-endpoint-one-judgement"]["status"] == "STANDS DOWN":
        _v114_evidence["stood_down"].append(dict(row="relay/one-endpoint-one-judgement",
                                                 reason="census_incomplete",
                                                 emitted_by="48_veldo_0108_relay"))

_v114_evidence["exchange_outcomes"] = dict(_v114_exchange_ok)

if __name__ == "__main__":
    print(_v114_json.dumps(dict(rows=_v114_direct_rows, evidence=_v114_evidence), sort_keys=True))
    raise SystemExit(0 if all(ok for _, ok in _v114_direct_rows) else 1)
