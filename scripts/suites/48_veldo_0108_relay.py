"""VELDO-0108: the SSH command relay carries, and decides nothing (PLAN-0019 W85).

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, so its declared
prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 48_veldo_0108_relay

WHAT IS UNDER TEST. .veldo/control_relay.py, run as a REAL CHILD PROCESS with the request on its
standard input, which is exactly how sshd runs it, against a real authority child process on a real
AF_UNIX socket. Its carrying promise is also tested against a bare echo socket with payloads chosen
to break a careless implementation: a NUL byte, text that is not valid UTF-8, half a megabyte, and
nothing at all.

WHAT IS HONESTLY NOT TESTED, AND WHY, and this is named in the row rather than left out. There is no
SSH SERVER on this machine, so the leg where sshd authenticates the remote principal and refuses an
unknown one is NOT exercised. That leg is sshd's, not this program's. What IS exercised is every
decision this program makes, and the thing that matters about the boundary: the relay is given SSH's
own environment, including a principal, and it changes nothing about the answer, because the relay
never reads it and the authority never sees it.
"""
import hashlib as _v108_hashlib
import hmac as _v108_hmac
import importlib.util as _v108_ilu
import json as _v108_json
import os as _v108_os
import shutil as _v108_shutil
import socket as _v108_socket
import subprocess as _v108_sp
import sys as _v108_sys
import tempfile as _v108_tf
import threading as _v108_threading
import time as _v108_time
from pathlib import Path as _v108_Path

_v108_tmp = _v108_Path(_v108_tf.mkdtemp(prefix="v108"))
_v108_have_git = _v108_shutil.which("git") is not None
_v108_have_sshd = bool(_v108_shutil.which("sshd") or _v108_os.path.exists("/usr/sbin/sshd"))
_v108_KEY = b"the owner's key, which no module here ever sees"
_v108_OTHER = b"somebody else's key"
_v108_HOST = "workstation-1"
_v108_children = []


def _v108_load(name, path):
    spec = _v108_ilu.spec_from_file_location(name, git_fixture_dependency(path))
    m = _v108_ilu.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _v108_organ(tag, edits=()):
    """A copy of the relay with the client and the enrollment reader beside it."""
    d = _v108_tmp / ("organ_" + tag)
    d.mkdir()
    for name in ("control_enrollment.py", "control_client.py"):
        _v108_shutil.copy2(ROOT / ".veldo" / name, d / name)
    src = (ROOT / ".veldo" / "control_relay.py").read_text()
    for old, new in edits:
        assert src.count(old) == 1, (old[:70], src.count(old))
        src = src.replace(old, new)
    (d / "control_relay.py").write_text(src)
    return d, _v108_load("v108_relay_" + tag, d / "control_relay.py")


def _v108_sign_with(key, payload):
    return "hmac-sha256:" + _v108_hmac.new(key, payload, _v108_hashlib.sha256).hexdigest()


def _v108_sign(payload):
    return _v108_sign_with(_v108_KEY, payload)


def _v108_verify(payload, signature):
    return _v108_hmac.compare_digest(_v108_sign(payload), signature)


_v108_MAIN, RL108 = _v108_organ("main")
EN108 = _v108_load("v108_enroll", _v108_MAIN / "control_enrollment.py")
CC108 = _v108_load("v108_client", _v108_MAIN / "control_client.py")

FORWARD_108 = "        answer = forward(address, payload)"
ADDRESS_108 = "    address = argv[1]"

# ---- the carrying promise, against a bare echo socket ------------------------------------------
# Byte for byte, on payloads chosen to break a careless implementation. This needs no authority and
# no git, so it runs wherever the suite runs.
_v108_echo_dir = _v108_tmp / "echo"
_v108_echo_dir.mkdir(parents=True)
_v108_echo_addr = str(_v108_echo_dir / "echo.sock")
_v108_echo_srv = _v108_socket.socket(_v108_socket.AF_UNIX, _v108_socket.SOCK_STREAM)
_v108_echo_srv.bind(_v108_echo_addr)
_v108_echo_srv.listen(8)


_v108_echo_srv.settimeout(0.5)


def _v108_echo_once():
    """Echo one connection, and GIVE UP rather than wait forever.

    A mutant that makes the relay answer without connecting leaves this thread waiting on accept(),
    and a suite thread that never returns hangs the whole gate instead of reporting a red row. The
    row reads the timeout as a payload that never arrived, which is exactly what it is."""
    try:
        conn, _ = _v108_echo_srv.accept()
    except OSError:
        return
    conn.settimeout(2)
    data = b""
    while True:
        chunk = conn.recv(65536)
        if not chunk:
            break
        data += chunk
    conn.sendall(data)
    conn.close()


_v108_PAYLOADS = {
    "a NUL byte and control characters": b'{"a":"\x00\x01\x02\x7f"}',
    "text that is valid utf-8 but awkward": "dot . slash / \u6f22\u5b57 robot \U0001F916 sep \u2028".encode("utf-8"),
    "bytes that are NOT valid utf-8": b"\xff\xfe\x00binary",
    "half a megabyte": bytes(range(256)) * 2048,
    "nothing at all": b"",
    "JSON with significant transport whitespace": b' { "z" : 1, "a" : 2 } \n',
}
_v108_byte_rows = []
for _v108_name, _v108_payload in _v108_PAYLOADS.items():
    _v108_t = _v108_threading.Thread(target=_v108_echo_once, daemon=True)
    _v108_t.start()
    try:
        _v108_exec = _v108_sp.run([_v108_sys.executable,
                                  str(_v108_MAIN / "control_relay.py"), _v108_echo_addr],
                                 input=_v108_payload, capture_output=True, timeout=5)
        _v108_got = _v108_exec.stdout if _v108_exec.returncode == 0 else None
    except (OSError, _v108_sp.TimeoutExpired):
        _v108_got = None
    _v108_t.join(timeout=15)
    _v108_byte_rows.append((_v108_name, _v108_got == _v108_payload))
_v108_echo_srv.close()

if not _v108_have_git:
    expect("VELDO-0108 STOOD DOWN in part by name - git is not installed here, so the rows that need a real "
           "enrolled repository and a real authority cannot run; the carrying promise above does not need "
           "one and it %s" % ("PASSED" if all(ok for _, ok in _v108_byte_rows) else "FAILED"),
           all(ok for _, ok in _v108_byte_rows))
else:
    _v108_env = dict(_v108_os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                     GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")

    def _v108_repo(name):
        d = _v108_tmp / name
        d.mkdir(parents=True)
        for args in (["init", "-q"], ["checkout", "-q", "-b", "trunk"]):
            _v108_sp.run(["git", "-C", str(d), *args], check=True, capture_output=True, env=_v108_env)
        (d / "seed.txt").write_text(name + "\n")
        _v108_sp.run(["git", "-C", str(d), "add", "-A"], check=True, capture_output=True, env=_v108_env)
        _v108_sp.run(["git", "-C", str(d), "commit", "-q", "-m", "seed"], check=True,
                     capture_output=True, env=_v108_env)
        return d

    RUNNER_108 = ROOT / "scripts" / "suites" / "support" / "v107_authority_runner.py"

    def _v108_start(tag, organ_dir, address, domain, store_uuid, store_path):
        cfgdir = _v108_tmp / ("cfg_" + tag)
        cfgdir.mkdir(exist_ok=True)
        cfg = {"enrollment_module": str(organ_dir / "control_enrollment.py"),
               "client_module": str(organ_dir / "control_client.py"), "key": _v108_KEY.decode(),
               "store_uuid": store_uuid, "domain_uuid": domain, "store_path": store_path,
               "host_identity": _v108_HOST, "address": address,
               "applied_log": str(cfgdir / "applied.jsonl"),
               "ready_flag": str(cfgdir / "ready"), "stop_flag": str(cfgdir / "stop")}
        (cfgdir / "config.json").write_text(_v108_json.dumps(cfg))
        proc = _v108_sp.Popen([_v108_sys.executable, str(RUNNER_108), str(cfgdir / "config.json")],
                              stdout=_v108_sp.PIPE, stderr=_v108_sp.PIPE)
        _v108_children.append((proc, cfg))
        for _ in range(250):
            if _v108_os.path.exists(cfg["ready_flag"]):
                break
            _v108_time.sleep(0.02)
        return proc, cfg

    def _v108_applied(cfg):
        p = _v108_Path(cfg["applied_log"])
        return [] if not p.is_file() else [_v108_json.loads(ln) for ln in p.read_text().splitlines() if ln.strip()]

    def _v108_unix_paths(prefix):
        """The kernel's own table of unix sockets, filtered to this fixture's directory."""
        try:
            text = open("/proc/net/unix").read()
        except OSError:
            return None
        out = set()
        for line in text.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 8 and parts[-1].startswith(prefix):
                out.add(parts[-1])
        return out

    def _v108_stop_all():
        for _proc, cfg in _v108_children:
            _v108_Path(cfg["stop_flag"]).write_text("stop\n")
        for proc, _cfg in _v108_children:
            try:
                proc.wait(timeout=5)
            except Exception:  # noqa: BLE001 - a child that will not stop is killed, not waited on
                proc.kill()
                proc.wait(timeout=5)

    if not RUNNER_108.is_file():
        expect("VELDO-0108 STOOD DOWN by name - the authority runner support script is absent, so no real "
               "authority can be started", True)
    else:
        try:
            _v108_A = _v108_repo("repoA")
            _v108_B = _v108_repo("repoB")
            _v108_PA = str(_v108_tmp / "authA" / "control.sqlite3")
            _v108_PB = str(_v108_tmp / "authB" / "control.sqlite3")
            _v108_bA = EN108.enroll(_v108_A, "dom-a", "store-a", _v108_PA, _v108_HOST, 1, _v108_sign,
                                    "dmitry", "2026-09-21T00:00:00Z")
            _v108_bB = EN108.enroll(_v108_B, "dom-b", "store-b", _v108_PB, _v108_HOST, 1, _v108_sign,
                                    "dmitry", "2026-09-21T00:00:00Z")
            _v108_ADDR_A = CC108.socket_path_for(_v108_bA)
            _v108_ADDR_B = CC108.socket_path_for(_v108_bB)
            _v108_pA, _v108_cA = _v108_start("A", _v108_MAIN, _v108_ADDR_A, "dom-a", "store-a", _v108_PA)
            _v108_pB, _v108_cB = _v108_start("B", _v108_MAIN, _v108_ADDR_B, "dom-b", "store-b", _v108_PB)

            def _v108_relay(relay_dir, address, payload, extra_env=None):
                """The relay as sshd runs it: a child process with the request on stdin."""
                e = dict(_v108_os.environ)
                e.update(extra_env or {})
                r = _v108_sp.run([_v108_sys.executable, str(relay_dir / "control_relay.py"), address],
                                 input=payload, capture_output=True, env=e, timeout=10)
                try:
                    answer = _v108_json.loads(r.stdout.decode()) if r.stdout else None
                except ValueError:
                    answer = {"unparsable_stdout": r.stdout[:200].decode("utf-8", "replace")}
                return r.returncode, answer, r.stderr.decode("utf-8", "replace")

            # ---- AC1: the authority judges, not the relay -------------------------------------
            _v108_cmd = {"operation": "upsert", "id": "relayed",
                         "payload": {"nested": [1, 2, 3], "text": "unicode: \u00b7 ok"}}
            _v108_req = CC108.build_request(_v108_A, _v108_bA, _v108_cmd, _v108_sign)
            _v108_raw = _v108_json.dumps(_v108_req).encode()
            _v108_rc_ok, _v108_ans_ok, _ = _v108_relay(_v108_MAIN, _v108_ADDR_A, _v108_raw)
            _v108_arrived = _v108_applied(_v108_cA)[-1] if _v108_applied(_v108_cA) else None
            _v108_rc_tam, _v108_ans_tam, _ = _v108_relay(
                _v108_MAIN, _v108_ADDR_A, _v108_raw.replace(b'"relayed"', b'"tampered"'))
            _v108_foreign = CC108.build_request(_v108_A, _v108_bA, {"operation": "upsert", "id": "foreign"},
                                                lambda p: _v108_sign_with(_v108_OTHER, p))
            _v108_rc_for, _v108_ans_for, _ = _v108_relay(
                _v108_MAIN, _v108_ADDR_A, _v108_json.dumps(_v108_foreign).encode())
            _v108_MUT1, _ = _v108_organ("decides", [
                (FORWARD_108,
                 '        answer = b\'{"schema": "veldo.control_response/v1", "accepted": true, '
                 '"result": {"applied": true}}\'')])
            _v108_rc_mut, _v108_ans_mut, _ = _v108_relay(
                _v108_MUT1, _v108_ADDR_A, _v108_raw.replace(b'"relayed"', b'"tampered"'))

            expect("VELDO-0108 AC1 relay/the-authority-judges-not-the-relay: the relay is run as a REAL CHILD "
                   "PROCESS with the request on its standard input, exactly as sshd runs it, against a real "
                   "authority on a real socket. A valid command is accepted and ARRIVES UNCHANGED, compared "
                   "against what was sent; a command tampered with in transit and a command signed by a key "
                   "the authority does not know are both refused AT THE AUTHORITY on the signature, not at the "
                   "relay. The carrying promise is measured separately against a bare echo socket, byte for "
                   "byte, on a NUL byte, text that is not valid UTF-8, half a megabyte and an empty payload, "
                   "because a relay that quietly re-encodes what it carries breaks signatures for reasons "
                   "nobody can find. DRIVEN: a copy that answers the client itself instead of forwarding "
                   "reports the TAMPERED command as accepted, which is the relay deciding",
                   _v108_rc_ok == 0 and _v108_ans_ok.get("accepted") is True
                   and _v108_arrived == _v108_cmd
                   and _v108_ans_tam.get("reason") == "command_signature_invalid"
                   and _v108_ans_for.get("reason") == "command_signature_invalid"
                   and all(ok for _, ok in _v108_byte_rows)
                   and _v108_ans_mut.get("accepted") is True)

            # ---- AC2: SSH is transport, the signature is authority -----------------------------
            _v108_unsigned = dict(_v108_req, signature="")
            _v108_SSH_ENV = {"SSH_CONNECTION": "10.0.0.5 2222 10.0.0.9 22",
                             "SSH_ORIGINAL_COMMAND": "veldo-relay",
                             "SSH_CLIENT": "10.0.0.5 2222 22",
                             "VELDO_PRINCIPAL": "dmitry"}
            _v108_rc_u, _v108_ans_u, _ = _v108_relay(_v108_MAIN, _v108_ADDR_A,
                                                     _v108_json.dumps(_v108_unsigned).encode(),
                                                     _v108_SSH_ENV)
            # And the mirror: a correctly signed command with NO ssh environment at all is accepted,
            # so the signature is what authorises and SSH's presence is not required for it.
            _v108_signed_noenv = CC108.build_request(_v108_A, _v108_bA,
                                                     {"operation": "upsert", "id": "no-ssh-env"}, _v108_sign)
            _v108_rc_n, _v108_ans_n, _ = _v108_relay(_v108_MAIN, _v108_ADDR_A,
                                                     _v108_json.dumps(_v108_signed_noenv).encode())
            _v108_relay_src = (ROOT / ".veldo" / "control_relay.py").read_text()
            _v108_MUT2, _ = _v108_organ("trustsssh", [
                (FORWARD_108,
                 '        if os.environ.get("VELDO_PRINCIPAL"):\n'
                 '            answer = b\'{"schema": "veldo.control_response/v1", "accepted": true}\'\n'
                 '        else:\n'
                 '            answer = forward(address, payload)')])
            _v108_rc_m2, _v108_ans_m2, _ = _v108_relay(_v108_MUT2, _v108_ADDR_A,
                                                       _v108_json.dumps(_v108_unsigned).encode(),
                                                       _v108_SSH_ENV)

            expect("VELDO-0108 AC2 relay/ssh-is-transport-not-authority: with SSH's own environment set, "
                   "SSH_CONNECTION, SSH_ORIGINAL_COMMAND, SSH_CLIENT and a principal, an UNSIGNED command is "
                   "refused, and a correctly signed command with NO ssh environment at all is accepted: the "
                   "signature authorises and SSH's presence neither adds nor is needed. The relay reads no "
                   "environment variable and performs no verification, asserted in its source. STOOD DOWN BY "
                   "NAME, and this is the honest half: there is no SSH server on this machine, so the leg "
                   "where sshd refuses an unknown principal is NOT exercised here; that leg is sshd's and not "
                   "this program's, and every decision this program does make is above. DRIVEN: a copy that "
                   "accepts because a principal is present passes the unsigned command, which makes every "
                   "host with relay access an authority",
                   _v108_ans_u.get("accepted") is False
                   and _v108_ans_n.get("accepted") is True
                   and "os.environ" not in _v108_relay_src
                   and "verify" not in _v108_relay_src
                   and _v108_ans_m2.get("accepted") is True)

            # ---- AC3: one endpoint, one judgement, and no listener ----------------------------
            _v108_before = _v108_unix_paths(str(_v108_tmp))
            _v108_local = CC108.send(_v108_A, {"operation": "upsert", "id": "same-command"}, EN108,
                                     _v108_verify, _v108_sign, _v108_HOST)
            _v108_rc_r, _v108_ans_r, _ = _v108_relay(
                _v108_MAIN, _v108_ADDR_A,
                _v108_json.dumps(CC108.build_request(_v108_A, _v108_bA,
                                                     {"operation": "upsert", "id": "same-command"},
                                                     _v108_sign)).encode())
            _v108_after = _v108_unix_paths(str(_v108_tmp))
            _v108_log = _v108_applied(_v108_cA)
            # Guarded, because a mutant that stops the relay forwarding leaves this log EMPTY, and a
            # suite that raises IndexError there hangs the row instead of reporting it red. An
            # absent pair is a failed comparison, which is the honest reading.
            _v108_same_two = len(_v108_log) >= 2 and _v108_log[-2] == _v108_log[-1]
            _v108_nobind = "bind(" not in _v108_relay_src and ".listen(" not in _v108_relay_src
            # The endpoint is an ARGUMENT. Pointing the environment at the other RUNNING authority
            # changes nothing, because nothing reads it.
            _v108_rc_amb, _v108_ans_amb, _ = _v108_relay(
                _v108_MAIN, _v108_ADDR_A, _v108_raw,
                {"VELDO_CONTROL_SOCKET": _v108_ADDR_B, "VELDO_CONTROL_DB": _v108_PB})
            _v108_B_log = _v108_applied(_v108_cB)
            _v108_MUT3, _ = _v108_organ("addrfromenv", [
                (ADDRESS_108, '    address = os.environ.get("VELDO_CONTROL_SOCKET") or argv[1]')])
            _v108_rc_m3, _v108_ans_m3, _ = _v108_relay(
                _v108_MUT3, _v108_ADDR_A, _v108_raw,
                {"VELDO_CONTROL_SOCKET": _v108_ADDR_B, "VELDO_CONTROL_DB": _v108_PB})

            expect("VELDO-0108 AC3 relay/one-endpoint-one-judgement: the same command sent locally and through "
                   "the relay produces the same judgement and the same entry in the authority's applied log, "
                   "so a relayed command is not a second code path. The relay opens no listener: the kernel's "
                   "own table of unix sockets under the fixture is identical before and after, and the source "
                   "carries no bind and no listen, because sshd is the network service and this is a command "
                   "it runs. The endpoint is an ARGUMENT: with the environment pointed at the other RUNNING "
                   "authority the relay still reaches the one it was given and the other's log does not grow. "
                   "DRIVEN: a copy that prefers an environment variable for the endpoint reaches the other "
                   "authority, which is the routing decision moved out of the signed binding to the one place "
                   "the binding is not read",
                   _v108_ans_r.get("accepted") is True and _v108_local.get("accepted") is True
                   and _v108_same_two and _v108_nobind
                   and _v108_before == _v108_after and _v108_before is not None
                   and _v108_ans_amb.get("accepted") is True
                   and _v108_ans_m3.get("accepted") is False
                   and _v108_ans_m3.get("reason") == "coordinate_not_served")

            # ---- the authority goes away: reported, never invented -----------------------------
            _v108_count = len(_v108_applied(_v108_cA))
            _v108_Path(_v108_cA["stop_flag"]).write_text("stop\n")
            _v108_pA.wait(timeout=10)
            _v108_rc_down, _v108_ans_down, _v108_err_down = _v108_relay(_v108_MAIN, _v108_ADDR_A, _v108_raw)

            expect("VELDO-0108 AC1 relay/an-unreachable-authority-is-reported-not-answered: with the authority "
                   "stopped, the relay exits %d, writes NOTHING to its standard output, names the endpoint on "
                   "its standard error, and applies nothing. It does not invent an answer, which would be the "
                   "local fallback VELDO-0109 exists to forbid arriving one layer lower down"
                   % RL108.EXIT_UNREACHABLE,
                   _v108_rc_down == RL108.EXIT_UNREACHABLE and _v108_ans_down is None
                   and "not answering" in _v108_err_down
                   and len(_v108_applied(_v108_cA)) == _v108_count)

            # ---- the negative control ----------------------------------------------------------
            _v108_NOOP, _ = _v108_organ("noop", [
                ("import os\nimport socket", "# additive no-op control\nimport os\nimport socket")])
            # Compared against THE ORIGINAL's answers in this same run, never against literals. A
            # control that re-asserts the expected behaviour reds under every mutation of the organ,
            # which makes it a second copy of the other rows rather than a control: its one job is
            # to show that COPYING changes nothing, so it must stay green even when the original is
            # wrong.
            _v108_orig_down = _v108_relay(_v108_MAIN, _v108_ADDR_A, _v108_raw)
            _v108_orig_other = _v108_relay(_v108_MAIN, _v108_ADDR_B, _v108_raw)
            _v108_control = [
                (_v108_relay(_v108_NOOP, _v108_ADDR_A, _v108_raw)[0], _v108_orig_down[0]),
                (_v108_relay(_v108_NOOP, _v108_ADDR_B, _v108_raw)[1].get("reason"),
                 _v108_orig_other[1].get("reason")),
            ]
            expect("VELDO-0108 control relay/copying-is-not-what-changes-it: a copy of the relay carrying only "
                   "an added comment answers exactly as the original does, both against the stopped authority "
                   "and against the other running one, so the difference each DRIVEN mutant shows is the "
                   "mutation and not the copying",
                   all(a == b for a, b in _v108_control))
        finally:
            _v108_stop_all()
