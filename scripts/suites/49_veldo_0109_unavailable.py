"""VELDO-0109: an unreachable authority stops work and never becomes a local one (PLAN-0019 W86).

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, so its declared
prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 49_veldo_0109_unavailable

WHAT IS UNDER TEST. The availability behaviour of .veldo/control_client.py against a REAL authority
child process on a real AF_UNIX socket that is then STOPPED: what a mutating call does, what an
inspecting call does, and what does NOT appear afterwards.

HOW "NOTHING APPEARED" IS ASKED, because the obvious ways are wrong and both were measured. Comparing
the whole directory listing before and after measures the SHUTDOWN, since the socket file disappears
with the authority; the row asks for NEW files only. And grepping this account's process list for the
authority's name matches the command doing the grepping, which is a check that passes because of
itself; the row asks the kernel three questions instead, none of which can match a string: whether
the socket file exists, whether anything is bound at that address in /proc/net/unix, and whether the
child this fixture started is dead with a return code.
"""
import hashlib as _v109_hashlib
import hmac as _v109_hmac
import importlib.util as _v109_ilu
import json as _v109_json
import os as _v109_os
import shutil as _v109_shutil
import socket as _v109_socket
import subprocess as _v109_sp
import sys as _v109_sys
import tempfile as _v109_tf
import time as _v109_time
from pathlib import Path as _v109_Path

_v109_tmp = _v109_Path(_v109_tf.mkdtemp(prefix="v109"))
_v109_have_git = _v109_shutil.which("git") is not None
_v109_KEY = b"the owner's key, which this module never sees"
_v109_HOST = "workstation-1"
_v109_children = []


def _v109_load(name, path):
    spec = _v109_ilu.spec_from_file_location(name, git_fixture_dependency(path))
    m = _v109_ilu.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _v109_organ(tag, edits=()):
    d = _v109_tmp / ("organ_" + tag)
    d.mkdir()
    _v109_shutil.copy2(ROOT / ".veldo" / "control_enrollment.py", d / "control_enrollment.py")
    src = (ROOT / ".veldo" / "control_client.py").read_text()
    for old, new in edits:
        assert src.count(old) == 1, (old[:70], src.count(old))
        src = src.replace(old, new)
    (d / "control_client.py").write_text(src)
    return d, _v109_load("v109_client_" + tag, d / "control_client.py")


def _v109_sign(payload):
    return "hmac-sha256:" + _v109_hmac.new(_v109_KEY, payload, _v109_hashlib.sha256).hexdigest()


def _v109_verify(payload, signature):
    return _v109_hmac.compare_digest(_v109_sign(payload), signature)


_v109_MAIN, CC109 = _v109_organ("main")
EN109 = _v109_load("v109_enroll", _v109_MAIN / "control_enrollment.py")

FALLBACK_109 = "            seen = last_seen(enrollment, workspace, binding)"
STALE_109 = '        return {"stale": True, "service": e.coordinates.get("service"),'

if not _v109_have_git:
    expect("VELDO-0109 STOOD DOWN by name - every row needs a real enrolled repository and git is not "
           "installed here", True)
else:
    _v109_env = dict(_v109_os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                     GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")

    def _v109_repo(name):
        d = _v109_tmp / name
        d.mkdir(parents=True)
        for args in (["init", "-q"], ["checkout", "-q", "-b", "trunk"]):
            _v109_sp.run(["git", "-C", str(d), *args], check=True, capture_output=True, env=_v109_env)
        (d / "seed.txt").write_text(name + "\n")
        _v109_sp.run(["git", "-C", str(d), "add", "-A"], check=True, capture_output=True, env=_v109_env)
        _v109_sp.run(["git", "-C", str(d), "commit", "-q", "-m", "seed"], check=True,
                     capture_output=True, env=_v109_env)
        return d

    RUNNER_109 = ROOT / "scripts" / "suites" / "support" / "v107_authority_runner.py"

    def _v109_start(tag, organ_dir, address, store_path):
        cfgdir = _v109_tmp / ("cfg_" + tag)
        cfgdir.mkdir(exist_ok=True)
        cfg = {"enrollment_module": str(organ_dir / "control_enrollment.py"),
               "client_module": str(organ_dir / "control_client.py"), "key": _v109_KEY.decode(),
               "store_uuid": "store-a", "domain_uuid": "dom-a", "store_path": store_path,
               "host_identity": _v109_HOST, "address": address,
               "applied_log": str(cfgdir / "applied.jsonl"),
               "ready_flag": str(cfgdir / "ready"), "stop_flag": str(cfgdir / "stop")}
        (cfgdir / "config.json").write_text(_v109_json.dumps(cfg))
        proc = _v109_sp.Popen([_v109_sys.executable, str(RUNNER_109), str(cfgdir / "config.json")],
                              stdout=_v109_sp.PIPE, stderr=_v109_sp.PIPE)
        _v109_children.append((proc, cfg))
        for _ in range(250):
            if _v109_os.path.exists(cfg["ready_flag"]):
                break
            _v109_time.sleep(0.02)
        return proc, cfg

    def _v109_bound_at(address):
        """Is anything bound at this address, according to the kernel? No string matching."""
        try:
            text = open("/proc/net/unix").read()
        except OSError:
            return None
        return [ln for ln in text.splitlines()[1:] if ln.split() and ln.split()[-1] == address]

    def _v109_stop_all():
        for _proc, cfg in _v109_children:
            _v109_Path(cfg["stop_flag"]).write_text("stop\n")
        for proc, _cfg in _v109_children:
            try:
                proc.wait(timeout=5)
            except Exception:  # noqa: BLE001
                proc.kill()
                proc.wait(timeout=5)

    if not RUNNER_109.is_file():
        expect("VELDO-0109 STOOD DOWN by name - the authority runner support script is absent", True)
    else:
        try:
            _v109_A = _v109_repo("repoA")
            _v109_PA = str(_v109_tmp / "authA" / "control.sqlite3")
            _v109_b = EN109.enroll(_v109_A, "dom-a", "store-a", _v109_PA, _v109_HOST, 1, _v109_sign,
                                   "dmitry", "2026-09-21T00:00:00Z")
            _v109_ADDR = CC109.socket_path_for(_v109_b)
            _v109_store_dir = _v109_Path(_v109_os.path.dirname(_v109_PA))
            _v109_proc, _v109_cfg = _v109_start("A", _v109_MAIN, _v109_ADDR, _v109_PA)

            _v109_clone_dir = (_v109_Path(EN109.git_common_dir(_v109_A)) / "veldo" / "control")

            def _v109_listing():
                """BOTH directories a fallback could write into: the AUTHORITY's, and the CLONE's own
                control directory where the last-seen record lives. Watching one of them would miss a
                fallback that wrote into the other, which is the whole thing this row is about."""
                out = {}
                for label, root in (("authority", _v109_store_dir), ("clone", _v109_clone_dir)):
                    if root.is_dir():
                        for q in root.rglob("*"):
                            st = q.lstat()
                            content = q.read_bytes() if q.is_file() and not q.is_symlink() else None
                            out[label + "/" + str(q.relative_to(root))] = (
                                st.st_mode, st.st_mtime_ns, content,
                                _v109_os.readlink(q) if q.is_symlink() else None)
                return out

            def _v109_mutate(client, at=None):
                try:
                    return ("accepted", client.send(_v109_A, {"operation": "upsert", "id": "x"}, EN109,
                                                    _v109_verify, _v109_sign, _v109_HOST, seen_at=at))
                except client.RoutingRefused as e:
                    return ("refused", e)

            # While it is UP: a command is accepted, carries a watermark, and the record is written.
            _v109_up = _v109_mutate(CC109, at="2026-09-21T10:00:00Z")
            _v109_live = CC109.inspect(_v109_A, EN109, _v109_verify, _v109_sign, _v109_HOST,
                                       now="2026-09-21T10:00:05Z")
            _v109_record = CC109.last_seen(EN109, _v109_A, _v109_b)

            # Now STOP it. Everything below is measured against an authority that is gone.
            _v109_Path(_v109_cfg["stop_flag"]).write_text("stop\n")
            _v109_proc.wait(timeout=10)
            _v109_Path(_v109_PA).write_bytes(b"existing durable authority state")
            _v109_before = _v109_listing()

            _v109_down = _v109_mutate(CC109, at="2026-09-21T10:01:00Z")
            _v109_after = _v109_listing()
            _v109_bound = _v109_bound_at(_v109_ADDR)
            _v109_M_fallback, _v109_fb = _v109_organ("fallback", [
                (FALLBACK_109,
                 "            seen = last_seen(enrollment, workspace, binding)\n"
                 "            if seen is not None:\n"
                 '                return {"schema": RESPONSE_SCHEMA, "accepted": True,\n'
                 '                        "store_uuid": binding["store_uuid"],\n'
                 '                        "watermark": seen.get("watermark"),\n'
                 '                        "result": {"applied": True, "locally": True}}')])
            _v109_down_mut = _v109_mutate(_v109_fb, at="2026-09-21T10:02:00Z")

            expect("VELDO-0109 AC1 unavailable/no-local-authority-appears: while the authority is up a command "
                   "is accepted and carries a WATERMARK, and the clone records it. With the authority stopped "
                   "the same command REFUSES by name as authority_unavailable, and the refusal carries the "
                   "service it could not reach and the last watermark it was sure of, because 'routing failed' "
                   "cannot be acted on. The recursive contents and metadata of both state directories are "
                   "unchanged against a snapshot taken AFTER shutdown, including existing files, "
                   "and nothing is bound at the address in the kernel's own "
                   "table, and the same is asked of the CLONE's own control directory where the last-seen "
                   "record lives, because a fallback would write there rather than into the authority's. The "
                   "record on disk does NOT turn the refusal into a success, which is the property "
                   "that matters. DRIVEN: a copy that falls back to that record reports the command APPLIED "
                   "LOCALLY, which is a second authority created at the moment nobody is watching",
                   _v109_up[0] == "accepted" and _v109_up[1].get("watermark") == 1
                   and _v109_record is not None and _v109_record["watermark"] == 2
                   and _v109_down[0] == "refused"
                   and _v109_down[1].reason == "authority_unavailable"
                   and _v109_down[1].coordinates.get("service") == "store-a"
                   and _v109_down[1].coordinates.get("last_watermark") == 2
                   and _v109_after == _v109_before and _v109_bound == []
                   and _v109_down_mut[0] == "accepted"
                   and _v109_down_mut[1].get("result", {}).get("locally") is True)

            # ---- AC2: a stale read says so ----------------------------------------------------
            _v109_stale = CC109.inspect(_v109_A, EN109, _v109_verify, _v109_sign, _v109_HOST)
            _v109_M_silent, _v109_sl = _v109_organ("silentstale", [
                (STALE_109, '        return {"stale": False, "service": e.coordinates.get("service"),')])
            _v109_stale_mut = _v109_sl.inspect(_v109_A, EN109, _v109_verify, _v109_sign, _v109_HOST)

            expect("VELDO-0109 AC2 unavailable/a-stale-read-says-so: inspection still ANSWERS while the "
                   "authority is gone, because refusing to answer a question about the past helps nobody, and "
                   "every answer carries `stale` explicitly: live it is False with the authority's own "
                   "watermark, and with the authority stopped it is True and carries the watermark, the "
                   "service, the moment it was last sure of, the last state, and why. An unlabelled answer "
                   "fails this row, so silence about staleness is a failure and not a missing nicety. DRIVEN: "
                   "a copy that returns the recorded state with stale False hands a caller old state that "
                   "looks current",
                   _v109_live["stale"] is False and _v109_live["watermark"] == 2
                   and _v109_stale["stale"] is True and _v109_stale["watermark"] == 2
                   and _v109_stale["service"] == "store-a"
                   and _v109_stale["as_of"] == "2026-09-21T10:00:05Z"
                   and _v109_stale["state"] is not None and _v109_stale["why"]
                   and _v109_stale_mut["stale"] is False)

            # ---- AC3: nothing starts the authority --------------------------------------------
            # Two shapes: the socket file gone entirely, and a DEAD socket file left in place, which
            # is what a crash leaves behind and the case a careless client treats as "it is there".
            _v109_never = _v109_repo("neverstarted")
            _v109_PN = str(_v109_tmp / "authN" / "control.sqlite3")
            _v109_bn = EN109.enroll(_v109_never, "dom-a", "store-a", _v109_PN, _v109_HOST, 1,
                                    _v109_sign, "dmitry", "2026-09-21T00:00:00Z")
            _v109_addr_n = CC109.socket_path_for(_v109_bn)
            try:
                CC109.send(_v109_never, {"operation": "upsert"}, EN109, _v109_verify, _v109_sign,
                           _v109_HOST)
                _v109_never_reason = "no raise"
            except CC109.RoutingRefused as e:
                _v109_never_reason = e.reason
            _v109_os.makedirs(_v109_os.path.dirname(_v109_addr_n), exist_ok=True)
            _v109_Path(_v109_addr_n).write_text("")          # a dead file where a socket was
            try:
                CC109.send(_v109_never, {"operation": "upsert"}, EN109, _v109_verify, _v109_sign,
                           _v109_HOST)
                _v109_dead_reason = "no raise"
            except CC109.RoutingRefused as e:
                _v109_dead_reason = e.reason
            _v109_bound_n = _v109_bound_at(_v109_addr_n)
            _v109_M_binds, _v109_bd = _v109_organ("bindsitself", [
                (FALLBACK_109,
                 "            seen = last_seen(enrollment, workspace, binding)\n"
                 "            try:\n"
                 "                os.unlink(address)\n"
                 "            except OSError:\n"
                 "                pass\n"
                 "            _s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)\n"
                 "            _s.bind(address)\n"
                 "            _s.listen(1)\n"
                 "            globals().setdefault('_v109_leaked', []).append(_s)")])
            try:
                _v109_bd.send(_v109_never, {"operation": "upsert"}, EN109, _v109_verify, _v109_sign,
                              _v109_HOST)
            except Exception:  # noqa: BLE001 - the mutant's own answer is not the point
                pass
            _v109_bound_after_mut = _v109_bound_at(_v109_addr_n)
            for _v109_s in _v109_bd.__dict__.get("_v109_leaked", []):
                _v109_s.close()

            expect("VELDO-0109 AC3 unavailable/no-client-starts-the-authority: with the authority never "
                   "started, and again with a DEAD socket file left where a socket used to be, which is what "
                   "a crash leaves behind, the client refuses as authority_unavailable and nothing ends up "
                   "bound at that address in the kernel's own table. Starting the authority is an operator's "
                   "act; a client that starts services on first use turns one stopped authority into two. "
                   "DRIVEN: a copy that binds the address itself when it cannot connect leaves a listener "
                   "there, which the kernel's table shows and this row refuses",
                   _v109_never_reason == "authority_unavailable"
                   and _v109_dead_reason == "authority_unavailable"
                   and _v109_bound_n == []
                   and _v109_bound_after_mut != [])

            # ---- the negative control -----------------------------------------------------------
            def _v109_reason(answer):
                """The refusal reason, or None when the answer is not a refusal.

                Shape-agnostic on purpose. The control compared `.reason` directly and CRASHED under
                the fallback mutant, because a copy carrying that mutation answers with a mapping
                rather than raising. A control that raises instead of reporting tells a reader
                nothing about whether copying changed anything."""
                return getattr(answer, "reason", None)

            _v109_NOOP, _v109_noop = _v109_organ("noop", [
                ("import socket\nimport struct", "# additive no-op control\nimport socket\nimport struct")])
            _v109_c1 = _v109_mutate(_v109_noop, at="2026-09-21T10:03:00Z")
            _v109_c2 = _v109_noop.inspect(_v109_A, EN109, _v109_verify, _v109_sign, _v109_HOST)
            expect("VELDO-0109 control unavailable/copying-is-not-what-changes-it: a copy of the organ "
                   "carrying only an added comment answers exactly as the original does, on the refused "
                   "mutation and on the stale inspection, so the difference each DRIVEN mutant shows is the "
                   "mutation and not the copying",
                   _v109_c1[0] == _v109_down[0]
                   and _v109_reason(_v109_c1[1]) == _v109_reason(_v109_down[1])
                   and _v109_c2["stale"] == _v109_stale["stale"]
                   and _v109_c2["watermark"] == _v109_stale["watermark"])

            # SIGKILL the same fixture class after observing an accepted command.
            _v109_kproc, _v109_kcfg = _v109_start("killed", _v109_MAIN, _v109_ADDR, _v109_PA)
            _v109_kup = _v109_mutate(CC109, at="2026-09-21T11:00:00Z")
            _v109_kproc.kill()
            _v109_kproc.wait(timeout=10)
            _v109_kbefore = _v109_listing()
            _v109_kdown = _v109_mutate(CC109, at="2026-09-21T11:01:00Z")
            expect("unavailable/sigkill-refuses-generic-client: after a live accepted upsert, SIGKILL "
                   "leaves a dead socket inode; send refuses with service and last watermark and "
                   "changes neither state directory",
                   _v109_kup[0] == "accepted" and _v109_kproc.returncode == -9
                   and _v109_Path(_v109_ADDR).is_socket()
                   and _v109_kdown[0] == "refused"
                   and getattr(_v109_kdown[1], "reason", None) == "authority_unavailable"
                   and _v109_kdown[1].coordinates.get("service") == "store-a"
                   and _v109_kdown[1].coordinates.get("last_watermark") == 1
                   and _v109_listing() == _v109_kbefore
                   and _v109_bound_at(_v109_ADDR) == [])
        finally:
            _v109_stop_all()
