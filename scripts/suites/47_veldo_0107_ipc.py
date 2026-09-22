"""VELDO-0107: local clients reach the authority over authenticated IPC (PLAN-0019 W84).

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, so its declared
prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 47_veldo_0107_ipc

WHAT IS UNDER TEST. .veldo/control_client.py, over TWO REAL AUTHORITIES running as child processes
on real AF_UNIX sockets, each serving its own store, with two real enrolled git clones. Requests are
sent over the socket, not handed to a function. The signer is an HMAC the suite supplies, because
the module holds no key material and takes signing and verification as callables.

WHAT IS HONESTLY NOT TESTED, and it is named in the row rather than left out. A connection from a
GENUINELY DIFFERENT OS ACCOUNT. This design has one account on purpose, so there is no second uid to
connect from, and inventing one would need the OS boundary the design refuses. The claim is split in
two instead: over a real socket the suite asserts that the uid the module uses is the one the KERNEL
reports through SO_PEERCRED and not anything the request said, and the rule about a foreign uid is
asserted by handing the real judging code a uid the kernel would report for another account. Neither
half is the whole claim and the row says so.
"""
import hashlib as _v107_hashlib
import hmac as _v107_hmac
import importlib.util as _v107_ilu
import json as _v107_json
import os as _v107_os
import shutil as _v107_shutil
import socket as _v107_socket
import subprocess as _v107_sp
import sys as _v107_sys
import tempfile as _v107_tf
import time as _v107_time
from pathlib import Path as _v107_Path

_v107_tmp = _v107_Path(_v107_tf.mkdtemp(prefix="v107"))
_v107_have_git = _v107_shutil.which("git") is not None
_v107_has_peercred = hasattr(_v107_socket, "SO_PEERCRED")
_v107_KEY = b"the owner's key, which neither module ever sees"
_v107_children = []


def _v107_load(name, path):
    spec = _v107_ilu.spec_from_file_location(name, git_fixture_dependency(path))
    m = _v107_ilu.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _v107_organ(tag, edits=()):
    """A copy of control_client.py with control_enrollment.py beside it."""
    d = _v107_tmp / ("organ_" + tag)
    d.mkdir()
    _v107_shutil.copy2(ROOT / ".veldo" / "control_enrollment.py", d / "control_enrollment.py")
    src = (ROOT / ".veldo" / "control_client.py").read_text()
    for old, new in edits:
        assert src.count(old) == 1, (old[:70], src.count(old))
        src = src.replace(old, new)
    (d / "control_client.py").write_text(src)
    return d, _v107_load("v107_client_" + tag, d / "control_client.py")


def _v107_sign(payload):
    return "hmac-sha256:" + _v107_hmac.new(_v107_KEY, payload, _v107_hashlib.sha256).hexdigest()


def _v107_verify(payload, signature):
    return _v107_hmac.compare_digest(_v107_sign(payload), signature)


_v107_MAIN_DIR, CC107 = _v107_organ("main")
EN107 = _v107_load("v107_enroll_main", _v107_MAIN_DIR / "control_enrollment.py")
HOST107 = "workstation-1"

# The mutation anchors, each rebuilding one specific wrong design.
RESOLVE_107 = '''        try:
            store = self.enrollment.resolve_store(request["workspace"], self.verify,
                                                  self.host_identity)
        except self.enrollment.EnrollmentRefused as e:
            return self._no("unenrolled_workspace",
                            "%s does not route anywhere: %s" % (request["workspace"], e.message))'''
PEER_107 = '''        if uid != os.getuid():'''
ADDRESS_107 = '''    return os.path.join(os.path.dirname(binding["store_path"]), SOCKET_NAME)'''

if not (_v107_have_git and _v107_has_peercred):
    expect("VELDO-0107 STOOD DOWN by name - every row needs a real git repository and a kernel that "
           "reports the connecting process's identity through SO_PEERCRED; git present=%s, "
           "SO_PEERCRED present=%s" % (_v107_have_git, _v107_has_peercred), True)
else:
    _v107_env = dict(_v107_os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                     GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")

    def _v107_git(repo, *a):
        return _v107_sp.run(["git", "-C", str(repo), *a], check=True, capture_output=True,
                            text=True, env=_v107_env).stdout.strip()

    def _v107_repo(name, seed):
        d = _v107_tmp / name
        d.mkdir(parents=True)
        _v107_git(d, "init", "-q")
        _v107_git(d, "checkout", "-q", "-b", "trunk")
        (d / "seed.txt").write_text(seed + "\n")
        _v107_git(d, "add", "-A")
        _v107_git(d, "commit", "-q", "-m", "seed " + seed)
        return d

    _v107_A = _v107_repo("repoA", "alpha")
    _v107_B = _v107_repo("repoB", "beta")
    _v107_DOM_A, _v107_ST_A = "a" * 8 + "-dom", "a" * 8 + "-store"
    _v107_DOM_B, _v107_ST_B = "b" * 8 + "-dom", "b" * 8 + "-store"
    _v107_PATH_A = str(_v107_tmp / "authorityA" / "control.sqlite3")
    _v107_PATH_B = str(_v107_tmp / "authorityB" / "control.sqlite3")
    _v107_bind_A = EN107.enroll(_v107_A, _v107_DOM_A, _v107_ST_A, _v107_PATH_A, HOST107, 1,
                                _v107_sign, "dmitry", "2026-09-21T00:00:00Z")
    _v107_bind_B = EN107.enroll(_v107_B, _v107_DOM_B, _v107_ST_B, _v107_PATH_B, HOST107, 1,
                                _v107_sign, "dmitry", "2026-09-21T00:00:00Z")

    def _v107_start(tag, organ_dir, address, domain, store_uuid, store_path):
        """One authority as a REAL child process on a REAL socket.

        The ADDRESS is explicit rather than derived from a binding here, because a mutant authority
        must never bind the address a real one is already serving: bind() unlinks what is there, so
        sharing the address would silently replace the authority under test and every row after it
        would be measuring the mutant."""
        cfgdir = _v107_tmp / ("cfg_" + tag)
        cfgdir.mkdir(exist_ok=True)
        cfg = {
            "enrollment_module": str(organ_dir / "control_enrollment.py"),
            "client_module": str(organ_dir / "control_client.py"),
            "key": _v107_KEY.decode(),
            "store_uuid": store_uuid, "domain_uuid": domain, "store_path": store_path,
            "host_identity": HOST107,
            "address": address,
            "applied_log": str(cfgdir / "applied.jsonl"),
            "ready_flag": str(cfgdir / "ready"), "stop_flag": str(cfgdir / "stop"),
        }
        cfgp = cfgdir / "config.json"
        cfgp.write_text(_v107_json.dumps(cfg))
        proc = _v107_sp.Popen([_v107_sys.executable, str(RUNNER_107), str(cfgp)],
                              stdout=_v107_sp.PIPE, stderr=_v107_sp.PIPE)
        _v107_children.append((proc, cfg))
        for _ in range(200):
            if _v107_os.path.exists(cfg["ready_flag"]):
                break
            _v107_time.sleep(0.02)
        return proc, cfg

    RUNNER_107 = ROOT / "scripts" / "suites" / "support" / "v107_authority_runner.py"
    _v107_runner_present = RUNNER_107.is_file()

    def _v107_applied(cfg):
        p = _v107_Path(cfg["applied_log"])
        return [] if not p.is_file() else [ln for ln in p.read_text().splitlines() if ln.strip()]

    def _v107_stop_all():
        for proc, cfg in _v107_children:
            _v107_Path(cfg["stop_flag"]).write_text("stop\n")
        for proc, cfg in _v107_children:
            try:
                proc.wait(timeout=5)
            except Exception:  # noqa: BLE001 - a child that will not stop is killed, not waited on
                proc.kill()
                proc.wait(timeout=5)

    if not _v107_runner_present:
        expect("VELDO-0107 STOOD DOWN by name - scripts/suites/support/v107_authority_runner.py is "
               "absent, so the authority cannot be started as a real child process", True)
    else:
        try:
            _v107_procA, _v107_cfgA = _v107_start("A", _v107_MAIN_DIR,
                                                  CC107.socket_path_for(_v107_bind_A),
                                                  _v107_DOM_A, _v107_ST_A, _v107_PATH_A)
            _v107_procB, _v107_cfgB = _v107_start("B", _v107_MAIN_DIR,
                                                  CC107.socket_path_for(_v107_bind_B),
                                                  _v107_DOM_B, _v107_ST_B, _v107_PATH_B)

            def _v107_send(workspace, command, client=None):
                c = client or CC107
                try:
                    return c.send(workspace, command, EN107, _v107_verify, _v107_sign, HOST107)
                except c.RoutingRefused as e:
                    return {"accepted": False, "reason": e.reason, "client_side": True}

            # ---- AC1: the coordinate comes from the request ------------------------------------
            _v107_ok_A = _v107_send(_v107_A, {"operation": "upsert", "id": "from-A"})
            _v107_ok_B = _v107_send(_v107_B, {"operation": "upsert", "id": "from-B"})
            _v107_log_A = _v107_applied(_v107_cfgA)
            _v107_log_B = _v107_applied(_v107_cfgB)

            # THE ATTACK. A request naming workspace B, with A's domain and store uuids FORGED into
            # it, signed (the attacker holds the signing key in this fixture, which is the harder
            # case), sent to A's socket. Only resolving B's own binding catches it.
            def _v107_forged(address):
                req = {"schema": CC107.REQUEST_SCHEMA,
                       "workspace": _v107_os.path.realpath(str(_v107_B)),
                       "domain_uuid": _v107_DOM_A, "store_uuid": _v107_ST_A,
                       "command": {"operation": "upsert", "id": "forged"}}
                req["signature"] = _v107_sign(CC107.signed_bytes(req))
                conn = _v107_socket.socket(_v107_socket.AF_UNIX, _v107_socket.SOCK_STREAM)
                conn.settimeout(10)
                conn.connect(address)
                conn.sendall(_v107_json.dumps(req).encode())
                conn.shutdown(_v107_socket.SHUT_WR)
                out = b""
                while True:
                    ch = conn.recv(65536)
                    if not ch:
                        break
                    out += ch
                conn.close()
                return _v107_json.loads(out.decode())

            _v107_forged_real = _v107_forged(CC107.socket_path_for(_v107_bind_A))
            _v107_log_A_after = _v107_applied(_v107_cfgA)

            _v107_MUT_DIR, _v107_M_self = _v107_organ("trustsitself", [
                (RESOLVE_107, "        store = self.store_path")])
            # The mutant serves A's identities from ITS OWN address, so A's authority keeps
            # serving A's socket and every row after this one still measures the real one.
            _v107_MUT_ADDR = str(_v107_tmp / "authorityMut" / "authority.sock")
            _v107_procM, _v107_cfgM = _v107_start("M", _v107_MUT_DIR, _v107_MUT_ADDR, _v107_DOM_A,
                                                  _v107_ST_A, _v107_PATH_A)
            _v107_forged_mut = _v107_forged(_v107_MUT_ADDR)

            expect("VELDO-0107 AC1 ipc/the-coordinate-comes-from-the-request: two authorities run as real "
                   "child processes on real sockets, each serving its own store; a client in each enrolled "
                   "workspace is accepted and its command is applied to ITS OWN store and to no other, "
                   "compared in both logs. Then the attack: a request naming workspace B with A's domain and "
                   "store uuids FORGED into it, correctly signed, sent to A's socket. A refuses it as "
                   "coordinate_not_served and applies nothing, because it resolved B's OWN binding rather "
                   "than believing the uuids the request declared. DRIVEN: a copy whose authority takes the "
                   "store from itself instead of resolving the request's workspace accepts the forgery, which "
                   "is a signed command committing into a repository it does not belong to",
                   _v107_ok_A.get("accepted") is True and _v107_ok_B.get("accepted") is True
                   and len(_v107_log_A) == 1 and len(_v107_log_B) == 1
                   and "from-A" in _v107_log_A[0] and "from-B" in _v107_log_B[0]
                   and _v107_forged_real.get("accepted") is False
                   and _v107_forged_real.get("reason") == "coordinate_not_served"
                   and _v107_log_A_after == _v107_log_A
                   and _v107_forged_mut.get("accepted") is True)

            # ---- AC2: transport and command are checked separately ------------------------------
            # The uid REALLY comes from the kernel: asserted over a real connection.
            _v107_probe_srv = CC107.bind(str(_v107_tmp / "probe" / "authority.sock"))
            _v107_probe_srv.settimeout(5)
            _v107_pc = _v107_socket.socket(_v107_socket.AF_UNIX, _v107_socket.SOCK_STREAM)
            _v107_pc.connect(str(_v107_tmp / "probe" / "authority.sock"))
            _v107_pconn, _ = _v107_probe_srv.accept()
            _v107_kernel_uid = CC107.peer_uid(_v107_pconn)
            _v107_mode = oct(_v107_os.stat(str(_v107_tmp / "probe" / "authority.sock")).st_mode & 0o777)
            _v107_dirmode = oct(_v107_os.stat(str(_v107_tmp / "probe")).st_mode & 0o777)
            _v107_pconn.close()
            _v107_pc.close()
            _v107_probe_srv.close()

            # A real authority object, judged directly, so a uid the kernel would report for another
            # account can be handed to the SAME rule the socket path uses.
            _v107_applied_direct = []
            _v107_auth = CC107.Authority(_v107_ST_A, _v107_DOM_A, _v107_PATH_A, EN107, _v107_verify,
                                         HOST107, lambda c: _v107_applied_direct.append(c) or {"ok": True})
            _v107_good_req = CC107.build_request(_v107_A, _v107_bind_A, {"operation": "upsert"}, _v107_sign)
            _v107_bad_sig = dict(_v107_good_req, signature="hmac-sha256:" + "0" * 64)
            _v107_r_valid = _v107_auth.judge(_v107_good_req, _v107_os.getuid())
            _v107_r_badsig = _v107_auth.judge(_v107_bad_sig, _v107_os.getuid())
            _v107_r_foreign = _v107_auth.judge(_v107_good_req, _v107_os.getuid() + 1)
            _v107_r_nouid = _v107_auth.judge(_v107_good_req, None)
            _v107_MUT2_DIR, _v107_M_nopeer = _v107_organ("nopeer", [(PEER_107, "        if False:")])
            _v107_auth_mut = _v107_M_nopeer.Authority(
                _v107_ST_A, _v107_DOM_A, _v107_PATH_A, EN107, _v107_verify, HOST107, lambda c: {"ok": True})
            _v107_r_foreign_mut = _v107_auth_mut.judge(_v107_good_req, _v107_os.getuid() + 1)

            expect("VELDO-0107 AC2 ipc/transport-and-command-are-checked-separately: over a REAL connection "
                   "the uid the module uses is the one the KERNEL reports through SO_PEERCRED and equals this "
                   "process's own, and the socket is 0600 inside a 0700 directory. Against the same real "
                   "authority object: a valid request is accepted; a valid peer carrying a broken signature is "
                   "refused as command_signature_invalid; a foreign uid is refused as peer_not_authorized even "
                   "though its signature is perfect; and a uid the platform will not report is refused as "
                   "peer_identity_unavailable rather than passed, because a check that is unavailable must not "
                   "become a check that succeeded. HONEST LIMIT, and it is why the claim is split: this design "
                   "has ONE account by intent, so there is no second uid to connect from and the foreign-uid "
                   "rule is exercised by handing the real rule a foreign uid rather than by a real foreign "
                   "connection. DRIVEN: a copy without the peer comparison accepts the foreign uid",
                   _v107_kernel_uid == _v107_os.getuid() and _v107_mode == "0o600"
                   and _v107_dirmode == "0o700"
                   and _v107_r_valid.get("accepted") is True
                   and _v107_r_badsig.get("reason") == "command_signature_invalid"
                   and _v107_r_foreign.get("reason") == "peer_not_authorized"
                   and _v107_r_nouid.get("reason") == "peer_identity_unavailable"
                   and _v107_r_foreign_mut.get("accepted") is True)

            # ---- AC3: the address follows the binding -------------------------------------------
            _v107_src107 = (ROOT / ".veldo" / "control_client.py").read_text()
            _v107_addr_from_binding = CC107.socket_path_for(_v107_bind_A)
            # This row measures ITS OWN delta. It used to compare against a snapshot taken before
            # AC1's forgery, which made it red under AC1's mutant as well: the accepted forgery added
            # a row to A's log and the arithmetic moved. A falsifier that reds a row it was not
            # pointed at is noise that reads like proof, so each row counts from its own baseline.
            _v107_base_A = _v107_applied(_v107_cfgA)
            _v107_base_B = _v107_applied(_v107_cfgB)
            _v107_before = _v107_os.getcwd()
            _v107_os.chdir(str(_v107_B))
            _v107_os.environ["VELDO_CONTROL_SOCKET"] = CC107.socket_path_for(_v107_bind_B)
            _v107_os.environ["VELDO_CONTROL_DB"] = _v107_PATH_B
            try:
                _v107_under_ambient = _v107_send(_v107_A, {"operation": "upsert", "id": "still-A"})
                _v107_log_A_amb = _v107_applied(_v107_cfgA)
                _v107_log_B_amb = _v107_applied(_v107_cfgB)
                _v107_MUT3_DIR, _v107_M_env = _v107_organ("fromenv", [
                    (ADDRESS_107,
                     '    return os.environ.get("VELDO_CONTROL_SOCKET") or os.path.join(\n'
                     '        os.path.dirname(binding["store_path"]), SOCKET_NAME)')])
                _v107_ambient_mut = _v107_M_env.socket_path_for(_v107_bind_A)
            finally:
                _v107_os.chdir(_v107_before)
                for _v107_k in ("VELDO_CONTROL_SOCKET", "VELDO_CONTROL_DB"):
                    _v107_os.environ.pop(_v107_k, None)

            expect("VELDO-0107 AC3 ipc/the-socket-follows-the-binding: the address is derived from the store "
                   "path the binding records, so with the process standing in the OTHER repository and with "
                   "VELDO_CONTROL_SOCKET and VELDO_CONTROL_DB both naming the other RUNNING authority, a "
                   "client in the first workspace still reaches the first authority and the other's log does "
                   "not grow. The other authority is real and running, so the row fails if the answer is right "
                   "only because the alternative was absent. The shipped module reads no environment variable "
                   "at all and contains no os.getcwd and no __file__. DRIVEN: a copy that prefers an "
                   "environment variable for the address reaches the other authority's socket",
                   _v107_under_ambient.get("accepted") is True
                   and len(_v107_log_A_amb) == len(_v107_base_A) + 1
                   and _v107_log_B_amb == _v107_base_B
                   and "os.environ" not in _v107_src107 and "os.getcwd" not in _v107_src107
                   and "__file__" not in _v107_src107
                   and _v107_ambient_mut == CC107.socket_path_for(_v107_bind_B)
                   and _v107_addr_from_binding != _v107_ambient_mut)

            # ---- the negative control ------------------------------------------------------------
            _v107_NOOP_DIR, _v107_M_noop = _v107_organ("noop", [
                ("import socket\nimport struct", "# additive no-op control\nimport socket\nimport struct")])
            _v107_auth_noop = _v107_M_noop.Authority(
                _v107_ST_A, _v107_DOM_A, _v107_PATH_A, EN107, _v107_verify, HOST107, lambda c: {"ok": True})
            # Compared against THE ORIGINAL's answers in this same run, never against literals. A
            # control that re-asserts the expected behaviour reds under every mutation of the organ,
            # which makes it a second copy of the other rows rather than a control: its one job is to
            # show that COPYING changes nothing, so it must stay green even when the original is
            # wrong.
            _v107_control = [
                (_v107_auth_noop.judge(_v107_good_req, _v107_os.getuid()).get("accepted"),
                 _v107_r_valid.get("accepted")),
                (_v107_auth_noop.judge(_v107_bad_sig, _v107_os.getuid()).get("reason"),
                 _v107_r_badsig.get("reason")),
                (_v107_auth_noop.judge(_v107_good_req, _v107_os.getuid() + 1).get("reason"),
                 _v107_r_foreign.get("reason")),
                (_v107_auth_noop.judge(_v107_good_req, None).get("reason"),
                 _v107_r_nouid.get("reason")),
                (_v107_M_noop.socket_path_for(_v107_bind_A), _v107_addr_from_binding),
            ]
            expect("VELDO-0107 control ipc/copying-is-not-what-changes-it: a copy of the organ carrying only "
                   "an added comment answers exactly as the original does on all five cases the rows above "
                   "turn on, so the difference each DRIVEN mutant shows is the mutation and not the copying",
                   all(a == b for a, b in _v107_control))
        finally:
            _v107_stop_all()
