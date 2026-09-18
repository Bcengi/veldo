"""VELDO-0024: signed Git replication and off-host acknowledgement (PLAN-0019 W9).

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, so its declared
prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 37_veldo_0024_replica

WHAT IS UNDER TEST. .veldo/control_replica.py over .veldo/control_store.py against a REAL SQLite
store, a REAL local bare Git remote and real publisher processes: every committed record becomes one
signed immutable export (record, signature, artifact BYTES) published in sequence to refs/veldo/audit
with a compare-and-swap lease, and mutation success and external dispatch are withheld until the
remote's own answer acknowledges the export (AC1); a publisher SIGKILLed after the export is
prepared, after the remote ref moved and after the acknowledgement persisted reconciles the SAME
export identity on restart with no second export and no divergent history (AC2); the status surface
shows a committed unacknowledged command as pending with its identity, never rejected, and a local
bare remote is named as protocol-only by the remote contract check (AC3). The three declared
falsifiers are applied to a COPY of the module and required to turn their named row red while the
unmutated module passes it. Signing uses a deterministic stub signer (the journal's real OpenSSH
signing is VELDO-0023's row); Git is the installed git.
"""
import importlib.util as _v24_ilu
import json as _v24_json
import os as _v24_os
import shutil as _v24_shutil
import subprocess as _v24_sp
import sys as _v24_sys
import tempfile as _v24_tf
from pathlib import Path as _v24_Path

_v24_store_path = ROOT / ".veldo" / "control_store.py"
_v24_replica_path = ROOT / ".veldo" / "control_replica.py"


def _v24_load(name, path):
    spec = _v24_ilu.spec_from_file_location(name, path)
    m = _v24_ilu.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


CS24 = _v24_load("v24_store", _v24_store_path)
CP24 = _v24_load("v24_replica", _v24_replica_path)
_v24_replica_src = _v24_replica_path.read_text()
_v24_tmp = _v24_Path(_v24_tf.mkdtemp(prefix="v24"))


def _v24_mutated(old, new, old2=None, new2=None):
    """A COPY of the replica module with ONE edit (or two edits in the SAME copy, when a falsifier
    needs both a check and its backstop removed); returns (module, path) for child processes."""
    d = _v24_Path(_v24_tf.mkdtemp(prefix="v24mut", dir=str(_v24_tmp)))
    assert _v24_replica_src.count(old) == 1, (old[:60], _v24_replica_src.count(old))
    src = _v24_replica_src.replace(old, new)
    if old2 is not None:
        assert src.count(old2) == 1, (old2[:60], src.count(old2))
        src = src.replace(old2, new2)
    p = d / "control_replica.py"
    p.write_text(src)
    return _v24_load("v24_mut_%s" % d.name, p), p


def _v24_stub_sign(msg):
    return "stub:" + CS24.digest_of(msg.decode("utf-8"))


def _v24_try(fn):
    """The refusal code of a call, or None. Caught by SHAPE (a `code` attribute on a StoreRefused or
    ReplicaRefused by class name), because a mutant copy raises its own copy of the class."""
    try:
        fn()
        return None
    except Exception as e:
        if type(e).__name__ in ("StoreRefused", "ReplicaRefused") and hasattr(e, "code"):
            return e.code
        raise


def _v24_cmd(cid, entity, data, expected, digests=()):
    return {"command_id": cid, "principal": "dmitry", "operation": "upsert_entity", "parameters": {"entity_id": entity, "kind": "k", "data": data},
            "expected_versions": {entity: expected}, "artifact_digests": list(digests), "nonce": "n-" + cid}


def _v24_world(name):
    """A fresh store, audit repo and bare remote."""
    d = _v24_tmp / name
    d.mkdir(parents=True)
    remote = str(d / "remote.git")
    _v24_sp.run(["git", "init", "--bare", "-q", remote], check=True, stdin=_v24_sp.DEVNULL)
    return str(d / "control.sqlite3"), str(d / "audit.git"), remote


_v24_blob = b"artifact bytes for VELDO-0024"
_v24_blob_digest = CP24.digest_of_bytes(_v24_blob)
_v24_art = lambda dg: _v24_blob if dg == _v24_blob_digest else None

# ---------------------------------------------------------------------------------------------
# AC1: exports in sequence to the protected ref; success withheld until acknowledged.
# ---------------------------------------------------------------------------------------------
_v24_db, _v24_audit, _v24_remote = _v24_world("ac1")
_v24_conn = CS24.open_store(_v24_db)
CS24.execute(_v24_conn, _v24_cmd("c1", "E1", {"a": 1}, 0, [_v24_blob_digest]), "dmitry", _v24_stub_sign, 1, committed_at=1000.0)
CS24.execute(_v24_conn, _v24_cmd("c2", "E1", {"a": 2}, 1), "dmitry", _v24_stub_sign, 1, committed_at=1001.0)
_v24_before = CP24.command_outcome(_v24_conn, CS24, "c1")
_v24_st0 = CP24.replication_status(_v24_conn, CS24, 1005.0)
_v24_pub = CP24.Publisher(_v24_audit, _v24_remote, _v24_stub_sign)
_v24_calls = []
_v24_r = CP24.publish_pending(_v24_conn, CS24, _v24_pub, _v24_art, 1006.0, dispatch=lambda cid, eid: _v24_calls.append((cid, eid)))
_v24_rec1 = CS24.export_journal(_v24_conn)[0]
_v24_exp1 = CP24.build_export(_v24_rec1, _v24_art)
_v24_tree = _v24_sp.run(["git", "ls-tree", "--name-only", _v24_pub.chain()[0]], cwd=_v24_audit, capture_output=True, text=True, stdin=_v24_sp.DEVNULL).stdout.split()
_v24_remote_log = _v24_sp.run(["git", "log", "--format=%s", CP24.AUDIT_REF], cwd=_v24_remote, capture_output=True, text=True, stdin=_v24_sp.DEVNULL).stdout.split("\n")
expect("VELDO-0024 AC1 replica/sequence: two committed commands are pending_publication before any export (the status shows durable 0, "
       "committed 2, two pending, oldest age 5s); publishing exports both in order to refs/veldo/audit on the real bare remote (the "
       "remote's log names export 1 then export 2, the remote tip equals the local audit tip), the export commit tree carries "
       "export.json, export.sig and the artifact BYTES blob (digest checked), dispatch runs once per command only after its "
       "acknowledgement, and afterwards both commands are succeeded with durable 2 and nothing pending",
       _v24_before["outcome"] == "pending_publication" and _v24_st0["last_durable_seq"] == 0 and _v24_st0["local_committed_seq"] == 2
       and _v24_st0["pending_exports"] == 2 and _v24_st0["oldest_pending_age_seconds"] == 5.0
       and _v24_r["published"] == [1, 2] and _v24_r["stopped"] is False
       and [l for l in _v24_remote_log if l] == ["veldo export " + CP24.export_identity(CS24.export_journal(_v24_conn)[1]), "veldo export " + _v24_exp1["export_id"]]
       and _v24_pub.remote_tip() == _v24_pub.local_tip() and len(_v24_pub.chain()) == 2
       and set(_v24_tree) == {"export.json", "export.sig", "artifact-" + _v24_blob_digest.split(":")[1]}
       and list(_v24_exp1["body"]["artifacts"]) == [_v24_blob_digest] and _v24_calls == [("c1", _v24_exp1["export_id"]), ("c2", CP24.export_identity(CS24.export_journal(_v24_conn)[1]))]
       and CP24.command_outcome(_v24_conn, CS24, "c1")["outcome"] == "succeeded" and CP24.command_outcome(_v24_conn, CS24, "c2")["remote_commit"] == _v24_pub.chain()[1]
       and CP24.replication_status(_v24_conn, CS24, 1010.0)["last_durable_seq"] == 2 and CP24.replication_status(_v24_conn, CS24, 1010.0)["pending_exports"] == 0
       and CP24.command_outcome(_v24_conn, CS24, "nope")["outcome"] == "unknown_command")
expect("VELDO-0024 AC1 replica/export-content: an export's identity is a function of sequence and record digest alone (the same record "
       "twice gives one identity, a different record digest another); an artifact with no bytes or with bytes not matching its digest "
       "refuses the export as artifact_missing; a signer that returns nothing refuses preparation as unsigned_export; the export "
       "digest covers the encoding, the record with its signature and the artifact bytes",
       CP24.export_identity(_v24_rec1) == CP24.export_identity(dict(_v24_rec1)) and CP24.export_identity(_v24_rec1) != CP24.export_identity(dict(_v24_rec1, record_digest="sha256:" + "0" * 64))
       and _v24_try(lambda: CP24.build_export(_v24_rec1, lambda dg: None)) == "artifact_missing"
       and _v24_try(lambda: CP24.build_export(_v24_rec1, lambda dg: b"other bytes")) == "artifact_missing"
       and _v24_try(lambda: CP24.Publisher(str(_v24_tmp / "unsigned.git"), _v24_remote, lambda m: None).prepare(CP24.build_export(dict(_v24_rec1, seq=99, record_digest="sha256:" + "1" * 64), _v24_art))) == "unsigned_export"
       and _v24_exp1["body"]["encoding"] == CP24.EXPORT_ENCODING and _v24_exp1["body"]["record"]["signature"] == _v24_rec1["signature"]
       and _v24_exp1["export_digest"] == CP24.digest_of_bytes(_v24_exp1["bytes"]))
# The receive hook rejects: the committed command stays pending, no dispatch, no success.
_v24_hook = _v24_Path(_v24_remote) / "hooks" / "pre-receive"
_v24_hook.write_text("#!/bin/sh\necho rejected by policy >&2\nexit 1\n")
_v24_hook.chmod(0o755)
CS24.execute(_v24_conn, _v24_cmd("c3", "E1", {"a": 3}, 2), "dmitry", _v24_stub_sign, 1, committed_at=1020.0)
_v24_calls3 = []
_v24_r3 = CP24.publish_pending(_v24_conn, CS24, _v24_pub, _v24_art, 1021.0, dispatch=lambda cid, eid: _v24_calls3.append(cid))
_v24_calls3_after_rejection = list(_v24_calls3)
_v24_st3 = CP24.replication_status(_v24_conn, CS24, 1030.0)
_v24_out3 = CP24.command_outcome(_v24_conn, CS24, "c3")
_v24_hook.unlink()
_v24_r3b = CP24.publish_pending(_v24_conn, CS24, _v24_pub, _v24_art, 1031.0, dispatch=lambda cid, eid: _v24_calls3.append(cid))
expect("VELDO-0024 AC1 replica/pending-success: with the remote's receive hook rejecting, a committed command's export is refused "
       "(remote_rejected), the command stays pending_publication with its identity (never succeeded, never rejected), the receiver "
       "is called zero times, the status shows one pending export of age 10s with durable 2 and committed 3; once the hook is gone the "
       "same export publishes, the receiver is called once and the command is succeeded",
       _v24_r3["stopped"] is True and _v24_r3["reason"].startswith("remote_rejected") and _v24_r3["pending"] == [3]
       and _v24_out3["outcome"] == "pending_publication" and _v24_out3["command_id"] == "c3" and "not rejected" in _v24_out3["note"]
       and _v24_calls3_after_rejection == [] and _v24_st3["pending_exports"] == 1 and _v24_st3["oldest_pending_age_seconds"] == 10.0 and _v24_st3["last_durable_seq"] == 2 and _v24_st3["local_committed_seq"] == 3
       and _v24_r3b["published"] == [3] and _v24_calls3 == ["c3"] and CP24.command_outcome(_v24_conn, CS24, "c3")["outcome"] == "succeeded")
# THE DECLARED FALSIFIER: return success after the SQLite commit while the remote receive hook rejects publication.
_V24_M1, _V24_M1_PATH = _v24_mutated('''            if not ok:
                out.update(stopped=True, reason="remote_rejected: %s" % detail)
                out["pending"] = [r["seq"] for r in pending if r["seq"] not in out["published"]]
                return out
''', '''            if not ok:
                pass  # mutant: the local commit is success enough
''', '''            if confirmed != commit:
                out.update(stopped=True, reason="the remote answered %s after the push, not %s: no acknowledgement" % (confirmed, commit))
''', '''            if False:  # mutant: the remote's answer is not consulted
                out.update(stopped=True, reason="the remote answered %s after the push, not %s: no acknowledgement" % (confirmed, commit))
''')
_v24_hook.write_text("#!/bin/sh\nexit 1\n")
_v24_hook.chmod(0o755)
CS24.execute(_v24_conn, _v24_cmd("c4", "E1", {"a": 4}, 3), "dmitry", _v24_stub_sign, 1, committed_at=1040.0)
_v24_m1_calls = []
_v24_m1_r = _V24_M1.publish_pending(_v24_conn, CS24, _V24_M1.Publisher(_v24_audit, _v24_remote, _v24_stub_sign), _v24_art, 1041.0, dispatch=lambda cid, eid: _v24_m1_calls.append(cid))
_v24_m1_out = CP24.command_outcome(_v24_conn, CS24, "c4")
_v24_hook.unlink()
expect("VELDO-0024 AC1 replica/pending-success DRIVEN (the declared falsifier): with a rejected push treated as success in a copy, the "
       "command whose export the remote refused is dispatched and reported succeeded although the remote never took it, so the row "
       "reds; unmutated (the row above) the same rejection leaves the command pending with zero receiver calls",
       _v24_m1_calls == ["c4"] and 4 in _v24_m1_r["published"] and _v24_m1_out["outcome"] == "succeeded" and _v24_pub.remote_tip() != _v24_pub.local_tip()
       and _v24_r3["stopped"] is True and _v24_calls3_after_rejection == [])
# repair the world the mutant damaged: the false acknowledgement is not something the store can un-say,
# so AC2 and AC3 use fresh worlds; here we only confirm the remote is still behind (the mutant lied).
_v24_conn.close()

# ---------------------------------------------------------------------------------------------
# AC2: a lost acknowledgement retries the SAME export identity; crash windows in real processes.
# ---------------------------------------------------------------------------------------------
_v24_child = '''
import importlib.util, sys, json
def load(n, p):
    sp = importlib.util.spec_from_file_location(n, p); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
CS = load("cs", sys.argv[1]); CP = load("cp", sys.argv[2])
conn = CS.open_store(sys.argv[3]); pub = CP.Publisher(sys.argv[4], sys.argv[5], lambda m: "stub:" + CS.digest_of(m.decode("utf-8")))
r = CP.publish_pending(conn, CS, pub, lambda d: None, 2000.0)
print("REPLIED " + json.dumps(r["published"]))
'''


def _v24_publisher_process(replica_path, db, audit, remote, kill_at):
    env = dict(_v24_os.environ, VELDO_CONTROL_TEST_HARNESS="1", VELDO_REPLICA_KILL_AT=kill_at)
    return _v24_sp.run([_v24_sys.executable, "-c", _v24_child, str(_v24_store_path), str(replica_path), db, audit, remote], env=env, capture_output=True, text=True, timeout=180, stdin=_v24_sp.DEVNULL)


def _v24_exports_for(audit, export_id):
    log = _v24_sp.run(["git", "log", "--format=%s", CP24.AUDIT_REF], cwd=audit, capture_output=True, text=True, stdin=_v24_sp.DEVNULL).stdout.splitlines()
    return [l for l in log if l == "veldo export " + export_id]


def _v24_crash_windows(replica_module, replica_path, name):
    db, audit, remote = _v24_world(name)
    conn = CS24.open_store(db)
    pub = replica_module.Publisher(audit, remote, _v24_stub_sign)
    CS24.execute(conn, _v24_cmd("seed", "E1", {}, 0), "dmitry", _v24_stub_sign, 1, committed_at=1000.0)
    replica_module.publish_pending(conn, CS24, pub, _v24_art, 1001.0)
    results = []
    for i, kp in enumerate(CP24.KILL_POINTS):
        cid = "k-" + kp
        CS24.execute(conn, _v24_cmd(cid, "E1", {"k": kp}, i + 1), "dmitry", _v24_stub_sign, 1, committed_at=1100.0 + i)
        remote_before = pub.remote_tip()
        journal_before = len(CS24.export_journal(conn))
        p = _v24_publisher_process(replica_path, db, audit, remote, kp)
        row_before = CS24.publication_row_for_command(conn, cid)
        rr = replica_module.reconcile(conn, CS24, pub, _v24_art, 1200.0 + i)
        row = CS24.publication_row_for_command(conn, cid)
        remote_tip = pub.remote_tip()
        results.append({"kill": kp, "rc": p.returncode, "acked_before_reconcile": row_before["acked_at"] is not None, "remote_moved_by_child": remote_before != pub.chain()[-1] and remote_before != remote_tip and row_before["acked_at"] is None and kp != "after_export_prepared",
                        "reconciled": rr["published"], "acked": row["acked_at"] is not None, "export_id": row["export_id"],
                        "exports_for_seq": len(_v24_exports_for(audit, row["export_id"])) if row["export_id"] else 0,
                        "remote_equals_local": remote_tip == pub.local_tip(), "journal_unchanged": len(CS24.export_journal(conn)) == journal_before,
                        "remote_commits": len(_v24_sp.run(["git", "rev-list", CP24.AUDIT_REF], cwd=remote, capture_output=True, text=True, stdin=_v24_sp.DEVNULL).stdout.split())})
    conn.close()
    return results


_v24_windows = _v24_crash_windows(CP24, _v24_replica_path, "ac2")
expect("VELDO-0024 AC2 replica/lost-ack-identity: a real publisher process SIGKILLed after the export is prepared, after the remote ref "
       "moved and after the acknowledgement persisted (three kills) is reconciled on restart against the exact remote ref: each "
       "command ends acknowledged with exactly ONE export commit for its sequence (the identity is reused, never a second export), the "
       "remote tip equals the local audit tip, the journal gained no record, the remote holds one commit per acknowledged export "
       "(four), and the kill after the ref moved is the one where the remote had moved with nothing acknowledged locally (windows: %s)"
       % [(w["kill"], w["rc"], w["acked_before_reconcile"], w["reconciled"]) for w in _v24_windows],
       all(w["rc"] == -9 for w in _v24_windows) and all(w["acked"] and w["exports_for_seq"] == 1 and w["remote_equals_local"] and w["journal_unchanged"] for w in _v24_windows)
       and [w["acked_before_reconcile"] for w in _v24_windows] == [False, False, True]
       and [len(w["reconciled"]) for w in _v24_windows] == [1, 1, 0] and _v24_windows[-1]["remote_commits"] == 4)
# THE DECLARED FALSIFIER: allocate a fresh export identity after a kill following the remote ref update.
_V24_M2, _V24_M2_PATH = _v24_mutated('''    return "export-%08d-%s" % (int(record["seq"]), record["record_digest"].split(":", 1)[1][:24])
''', '''    import uuid  # mutant: every attempt is a new export
    return "export-%08d-%s" % (int(record["seq"]), uuid.uuid4().hex[:24])
''')
_v24_m2_db, _v24_m2_audit, _v24_m2_remote = _v24_world("ac2-m2")
_v24_m2c = CS24.open_store(_v24_m2_db)
CS24.execute(_v24_m2c, _v24_cmd("m2", "E1", {}, 0), "dmitry", _v24_stub_sign, 1, committed_at=1000.0)
_v24_m2_p = _v24_publisher_process(_V24_M2_PATH, _v24_m2_db, _v24_m2_audit, _v24_m2_remote, "after_remote_ref_updated")
_v24_m2_row = CS24.publication_row_for_command(_v24_m2c, "m2")
_v24_m2_code = _v24_try(lambda: _V24_M2.reconcile(_v24_m2c, CS24, _V24_M2.Publisher(_v24_m2_audit, _v24_m2_remote, _v24_stub_sign), _v24_art, 1200.0))
_v24_m2_log = _v24_sp.run(["git", "log", "--format=%s", CP24.AUDIT_REF], cwd=_v24_m2_audit, capture_output=True, text=True, stdin=_v24_sp.DEVNULL).stdout.splitlines()
expect("VELDO-0024 AC2 replica/lost-ack-identity DRIVEN (the declared falsifier): with a fresh export identity allocated on every attempt in a "
       "copy, the restart after a kill following the remote ref update names a second identity for the same sequence: the store's "
       "cursor refuses it as export_identity_mismatch and the local audit log shows the sequence exported under a different name than "
       "the cursor recorded, so the row reds; unmutated (the row above) every window ends with one export per sequence",
       _v24_m2_p.returncode == -9 and _v24_m2_row["export_id"] is not None and _v24_m2_row["acked_at"] is None
       and _v24_m2_code == "export_identity_mismatch" and len(_v24_m2_log) == 1 and _v24_m2_log[0] == "veldo export " + _v24_m2_row["export_id"]
       and all(w["exports_for_seq"] == 1 for w in _v24_windows))
_v24_m2c.close()
# A divergent remote (a tip this authority never exported) pauses publication and overwrites nothing.
_v24_dv_db, _v24_dv_audit, _v24_dv_remote = _v24_world("divergent")
_v24_dvc = CS24.open_store(_v24_dv_db)
_v24_dv_pub = CP24.Publisher(_v24_dv_audit, _v24_dv_remote, _v24_stub_sign)
CS24.execute(_v24_dvc, _v24_cmd("d1", "E1", {}, 0), "dmitry", _v24_stub_sign, 1, committed_at=1000.0)
CP24.publish_pending(_v24_dvc, CS24, _v24_dv_pub, _v24_art, 1001.0)
_v24_foreign = _v24_tmp / "foreign"
_v24_sp.run(["git", "init", "-q", str(_v24_foreign)], check=True, stdin=_v24_sp.DEVNULL)
(_v24_foreign / "x").write_text("x")
_v24_fenv = dict(_v24_os.environ, GIT_AUTHOR_NAME="x", GIT_AUTHOR_EMAIL="x@x", GIT_COMMITTER_NAME="x", GIT_COMMITTER_EMAIL="x@x", GIT_CONFIG_GLOBAL=_v24_os.devnull, GIT_CONFIG_SYSTEM=_v24_os.devnull)
_v24_sp.run(["git", "-C", str(_v24_foreign), "add", "x"], check=True, env=_v24_fenv, stdin=_v24_sp.DEVNULL)
_v24_sp.run(["git", "-C", str(_v24_foreign), "commit", "-q", "-m", "foreign"], check=True, env=_v24_fenv, stdin=_v24_sp.DEVNULL)
_v24_sp.run(["git", "-C", str(_v24_foreign), "push", "-q", "-f", _v24_dv_remote, "HEAD:" + CP24.AUDIT_REF], check=True, env=_v24_fenv, stdin=_v24_sp.DEVNULL)
_v24_foreign_tip = _v24_dv_pub.remote_tip()
CS24.execute(_v24_dvc, _v24_cmd("d2", "E1", {"b": 1}, 1), "dmitry", _v24_stub_sign, 1, committed_at=1002.0)
_v24_dv_rec = CP24.reconcile(_v24_dvc, CS24, _v24_dv_pub, _v24_art, 1003.0)
_v24_dv_pub2 = CP24.publish_pending(_v24_dvc, CS24, _v24_dv_pub, _v24_art, 1004.0)
_v24_dv_st = CP24.replication_status(_v24_dvc, CS24, 1010.0)
expect("VELDO-0024 AC2 replica/divergent-remote: a remote whose audit ref names a commit this authority never exported is a divergent "
       "replica: reconcile and publish both stop as divergent_replica, publication is PAUSED with the reason naming the foreign tip, "
       "the remote is left exactly as found (never overwritten), and the committed command stays pending_publication",
       _v24_dv_rec["stopped"] is True and _v24_dv_rec["reason"] == "divergent_replica" and _v24_dv_pub2["reason"] == "divergent_replica"
       and _v24_dv_st["paused_publication"] is True and _v24_foreign_tip in _v24_dv_st["paused_reason"]
       and _v24_dv_pub.remote_tip() == _v24_foreign_tip and CP24.command_outcome(_v24_dvc, CS24, "d2")["outcome"] == "pending_publication")
_v24_dvc.close()

# ---------------------------------------------------------------------------------------------
# AC3: the status surface; the remote contract.
# ---------------------------------------------------------------------------------------------
_v24_st_db, _v24_st_audit, _v24_st_remote = _v24_world("status")
_v24_stc = CS24.open_store(_v24_st_db)
_v24_st_pub = CP24.Publisher(_v24_st_audit, _v24_st_remote, _v24_stub_sign)
_v24_empty = CP24.replication_status(_v24_stc, CS24, 500.0)
CS24.execute(_v24_stc, _v24_cmd("s1", "E1", {}, 0), "dmitry", _v24_stub_sign, 1, committed_at=1000.0)
CP24.publish_pending(_v24_stc, CS24, _v24_st_pub, _v24_art, 1001.0)
_v24_caught = CP24.replication_status(_v24_stc, CS24, 1002.0)
CS24.execute(_v24_stc, _v24_cmd("s2", "E1", {"p": 1}, 1), "dmitry", _v24_stub_sign, 1, committed_at=1010.0)
CS24.execute(_v24_stc, _v24_cmd("s3", "E1", {"p": 2}, 2), "dmitry", _v24_stub_sign, 1, committed_at=1020.0)
# the publisher dies before any acknowledgement persists, then status is read after "restart" through a fresh read-only handle
_v24_st_p = _v24_publisher_process(_v24_replica_path, _v24_st_db, _v24_st_audit, _v24_st_remote, "after_remote_ref_updated")
_v24_ro = CS24.open_store(_v24_st_db, mode="r")
_v24_pending_st = CP24.replication_status(_v24_ro, CS24, 1050.0)
_v24_ro.close()
# the Run Lens surface: runstatus.status() over a temp root with the store present, read-only, and the terminal rendering
_v24_rs_root = _v24_tmp / "rsroot"
(_v24_rs_root / ".veldo").mkdir(parents=True)
for _f in ("runstatus.py", "runlog.py", "control_store.py", "control_replica.py"):
    _v24_shutil.copyfile(ROOT / ".veldo" / _f, _v24_rs_root / ".veldo" / _f)
_v24_sp.run(["git", "init", "-q", str(_v24_rs_root)], check=True, stdin=_v24_sp.DEVNULL)
RS24 = _v24_load("v24_runstatus", _v24_rs_root / ".veldo" / "runstatus.py")
def _v24_lens(db):
    """The Run Lens replication section over `db` (the reader's own _replication, read-only), in a
    model shaped like status() builds (the repo-wide reads of status() need a whole repository)."""
    return {"schema": "veldo.runstatus/v1", "at": "", "repo": {"root": str(_v24_rs_root), "head": "0" * 40, "branch": "x"}, "burndown": {},
            "runs": [], "events_tail": [], "recent_verdicts": [], "tripwires": {}, "replication": RS24._replication(_v24_rs_root, 1050.0, db_path=db)}


_v24_model = _v24_lens(_v24_st_db)
_v24_text = RS24.render_text(_v24_model)
_v24_absent = _v24_lens(str(_v24_tmp / "nowhere.sqlite3"))
_v24_status_src = (ROOT / ".veldo" / "runstatus.py").read_text()
expect("VELDO-0024 AC3 replica/status-pending: the status surface reads an empty store (durable 0, committed 0, nothing pending), a "
       "caught-up store (durable 1, committed 1), and after the publisher died with the remote ref moved and nothing acknowledged, a "
       "pending store read through a READ-ONLY handle: durable 1, committed 3, two pending, oldest age 40s, each pending command "
       "listed by its ORIGINAL identity as pending_publication, not paused; the Run Lens model carries the same numbers with the "
       "condition PENDING_PUBLICATION and its terminal view prints the pending commands with 'not rejected'; a missing store renders "
       "as absent with a reason, never as an empty replica",
       _v24_empty["last_durable_seq"] == 0 and _v24_empty["local_committed_seq"] == 0 and _v24_empty["pending_exports"] == 0 and _v24_empty["oldest_pending_age_seconds"] is None
       and _v24_caught["last_durable_seq"] == 1 and _v24_caught["local_committed_seq"] == 1 and _v24_caught["pending_exports"] == 0
       and _v24_st_p.returncode == -9
       and _v24_pending_st["last_durable_seq"] == 1 and _v24_pending_st["local_committed_seq"] == 3 and _v24_pending_st["pending_exports"] == 2
       and _v24_pending_st["oldest_pending_age_seconds"] == 40.0 and _v24_pending_st["paused_publication"] is False
       and [p["command_id"] for p in _v24_pending_st["pending"]] == ["s2", "s3"] and all(p["state"] == "pending_publication" for p in _v24_pending_st["pending"])
       and _v24_model["replication"]["present"] is True and _v24_model["replication"]["condition"] == "PENDING_PUBLICATION"
       and _v24_model["replication"]["last_durable_seq"] == 1 and _v24_model["replication"]["pending_exports"] == 2
       and "replication: PENDING_PUBLICATION  durable_seq=1 committed_seq=3 pending=2 oldest_pending=40s" in _v24_text
       and "pending_publication seq=2 command=s2" in _v24_text and "not rejected" in _v24_text and "rejected" not in _v24_text.replace("not rejected", "")
       and _v24_absent["replication"]["present"] is False and "no control store" in _v24_absent["replication"]["reason"]
       and '"replication": _replication(root, now, db_path=control_db)' in _v24_status_src and 'mode="r"' in _v24_status_src)
# THE DECLARED FALSIFIER: render a committed pending command as rejected after publisher death.
_V24_M3, _V24_M3_PATH = _v24_mutated('''"pending": [{"seq": p["seq"], "command_id": p["command_id"], "state": "pending_publication"} for p in pending]}''',
                                     '''"pending": [{"seq": p["seq"], "command_id": "unknown", "state": "rejected"} for p in pending]}  # mutant: unpublished is rejected''')
_v24_ro2 = CS24.open_store(_v24_st_db, mode="r")
_v24_m3_st = _V24_M3.replication_status(_v24_ro2, CS24, 1050.0)
_v24_ro2.close()
expect("VELDO-0024 AC3 replica/status-pending DRIVEN (the declared falsifier): with an unpublished command rendered as rejected under an "
       "unknown identity in a copy, the pending commands after publisher death read as rejected and lose their command ids, so the "
       "row reds; unmutated (the row above) they read as pending_publication under s2 and s3",
       [p["state"] for p in _v24_m3_st["pending"]] == ["rejected", "rejected"] and [p["command_id"] for p in _v24_m3_st["pending"]] == ["unknown", "unknown"]
       and [p["command_id"] for p in _v24_pending_st["pending"]] == ["s2", "s3"])
_v24_ops_ok = {"remote_durability_evidence": "ops-record-2026-09-18", "protected_ref": CP24.AUDIT_REF, "force_update_refused": True, "recorded_by": "dmitry"}
expect("VELDO-0024 AC3 replica/remote-contract: a local bare remote (path or file URL) is named protocol-only and never off-host "
       "durability; activation also needs recorded operations evidence of remote durability, evidence that refs/veldo/audit is protected "
       "with force updates refused, and a named person recording it (an agent is not one); a complete contract over a real remote URL "
       "has no problems; the audit ref is refs/veldo/audit",
       any("protocol only" in p for p in CP24.remote_contract_problems(_v24_st_remote, _v24_ops_ok))
       and any("protocol only" in p for p in CP24.remote_contract_problems("file:///srv/git/veldo.git", _v24_ops_ok))
       and any("no operations evidence" in p for p in CP24.remote_contract_problems("git@github.com:Bcengi/veldo.git", {k: v for k, v in _v24_ops_ok.items() if k != "remote_durability_evidence"}))
       and any("is protected" in p for p in CP24.remote_contract_problems("git@github.com:Bcengi/veldo.git", dict(_v24_ops_ok, force_update_refused=False)))
       and any("is protected" in p for p in CP24.remote_contract_problems("git@github.com:Bcengi/veldo.git", dict(_v24_ops_ok, protected_ref="refs/heads/main")))
       and any("named person" in p for p in CP24.remote_contract_problems("git@github.com:Bcengi/veldo.git", dict(_v24_ops_ok, recorded_by="agent")))
       and CP24.remote_contract_problems("git@github.com:Bcengi/veldo.git", _v24_ops_ok) == [] and CP24.AUDIT_REF == "refs/veldo/audit"
       and len(CP24.remote_contract_problems(_v24_st_remote, {})) == 4)
_v24_stc.close()
_v24_shutil.rmtree(_v24_tmp, ignore_errors=True)
