"""VELDO-0023: atomic journaled commands and deterministic replay (PLAN-0019 W8).

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, so its declared
prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 36_veldo_0023_journal

WHAT IS UNDER TEST. .veldo/control_store.py and .veldo/control_replay.py against a REAL SQLite
store in a temporary directory: one transaction commits entity versions, the signed journal record,
the consumed nonce, reservation rows and effect obligations together, with foreign keys and FULL
synchronous read back (AC1); a writer PROCESS is SIGKILLed before, inside and after COMMIT for every
registered command and the reopened store is either the complete old or the complete new state
(AC1); identical retries return the original result, altered content under one id and stale
versions refuse, raced from two real client processes against a one-winner oracle (AC2); replay
rebuilds the state from the verified signed history in a process with the execution environment
removed, and every corruption of the history refuses reconstruction (AC3). The journal is signed
and verified with a REAL Ed25519 key through the installed ssh-keygen; when ssh-keygen is absent
those rows stand down by name. The three declared falsifiers are applied to a COPY of the module
and required to turn their named row red while the unmutated module passes it.
"""
import ast as _v23_ast
import copy as _v23_copy
import importlib.util as _v23_ilu
import json as _v23_json
import os as _v23_os
import shutil as _v23_shutil
import subprocess as _v23_sp
import sys as _v23_sys
import tempfile as _v23_tf
from pathlib import Path as _v23_Path

_v23_store_path = ROOT / ".veldo" / "control_store.py"
_v23_replay_path = ROOT / ".veldo" / "control_replay.py"


def _v23_load(name, path):
    spec = _v23_ilu.spec_from_file_location(name, git_fixture_dependency(path))
    m = _v23_ilu.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


CS23 = _v23_load("v23_store", _v23_store_path)
CR23 = _v23_load("v23_replay", _v23_replay_path)
_v23_store_src = _v23_store_path.read_text()
_v23_replay_src = _v23_replay_path.read_text()
_v23_tmp = _v23_Path(_v23_tf.mkdtemp(prefix="v23"))


def _v23_mutated(src, old, new, filename):
    """A COPY of a module with ONE edit, under a temporary directory; returns (module, path) so a
    child process can load the same copy."""
    d = _v23_Path(_v23_tf.mkdtemp(prefix="v23mut", dir=str(_v23_tmp)))
    assert src.count(old) == 1, (old[:60], src.count(old))
    p = d / filename
    p.write_text(src.replace(old, new))
    return _v23_load("v23_mut_%s" % d.name, p), p


# A deterministic stub signer for the crash and race matrices (the signature is a function of the
# bytes, so replay's chain checks still bind); the REAL signer is exercised in the signed-history rows.
def _v23_stub_sign(msg):
    return "stub:" + CS23.digest_of(msg.decode("utf-8"))


def _v23_stub_verify(msg, sig, signer):
    return (sig == _v23_stub_sign(msg), "stub")


def _v23_cmd(cid, op, params, expected, nonce=None, principal="dmitry", digests=()):
    return {"command_id": cid, "principal": principal, "operation": op, "parameters": params, "expected_versions": expected,
            "artifact_digests": list(digests), "nonce": nonce or ("n-" + cid)}


def _v23_try(fn):
    try:
        fn()
        return None
    except CS23.StoreRefused as e:
        return e.code
    except CR23.ReplayRefused as e:
        return e.code


def _v23_fresh_db(name):
    d = _v23_tmp / name
    d.mkdir(parents=True, exist_ok=True)
    return str(d / "control.sqlite3")


# ---------------------------------------------------------------------------------------------
# AC1: one transaction, all of it or none; qualification of the store.
# ---------------------------------------------------------------------------------------------
_v23_db = _v23_fresh_db("ac1")
_v23_conn = CS23.open_store(_v23_db)
_v23_pragmas = (_v23_conn.execute("PRAGMA foreign_keys").fetchone()[0], _v23_conn.execute("PRAGMA synchronous").fetchone()[0],
                _v23_conn.execute("PRAGMA journal_mode").fetchone()[0])
_v23_tables = {r[0] for r in _v23_conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
expect("VELDO-0023 AC1 journal/qualified-store: a fresh store opens with foreign keys ON, synchronous FULL and WAL, all read back "
       "after opening; the eight domain tables (the six of the journal plus the two publication-cursor tables VELDO-0024 added) exist and are exactly DOMAIN_TABLES; a network filesystem (nfs, cifs, sshfs) and an "
       "undeterminable one each refuse to open for writes by name, while the local temp dir is qualified",
       _v23_pragmas == (1, 2, "wal") and _v23_tables == set(CS23.DOMAIN_TABLES) and len(CS23.DOMAIN_TABLES) == 8
       and CS23.filesystem_problems(_v23_db) == []
       and all(any("network-mounted or unsupported" in p for p in CS23.filesystem_problems("/mnt/x/y", "srv:/v /mnt/x %s rw 0 0" % fs)) for fs in ("nfs", "nfs4", "cifs", "fuse.sshfs", "9p"))
       and any("cannot be determined" in p for p in CS23.filesystem_problems("/nowhere", ""))
       and (lambda: (_v23_try(lambda: CS23.open_store(str(_v23_tmp / "nfs" / "c.sqlite3"), mounts_text="srv:/v %s nfs rw 0 0" % str(_v23_tmp)))))() == "unsupported_filesystem")



_v23_c1 = _v23_cmd("c1", "upsert_entity", {"entity_id": "E1", "kind": "spec", "data": {"a": 1}}, {"E1": 0}, digests=["sha256:art"])
_v23_r1 = CS23.execute(_v23_conn, _v23_c1, "dmitry", _v23_stub_sign, 1)
_v23_snap1 = CS23.table_snapshot(_v23_conn)
_v23_rec1 = CS23.export_journal(_v23_conn)[0]
expect("VELDO-0023 AC1 journal/one-transaction: one upsert commits the entity at version 1, one journal record (seq 1, prev the genesis "
       "digest, generation 1, the command digest, before {E1: 0} and after {E1: 1}, the transition with the entity's digest, the "
       "artifact digests, the versioned encoding), the commands row with the result digest, and the consumed nonce, and the record "
       "digest recomputes from the record's fields; the result names seq, record digest and after-versions",
       _v23_r1["committed"] is True and _v23_r1["seq"] == 1 and _v23_r1["after_versions"] == {"E1": 1} and _v23_r1["replayed"] is False
       and len(_v23_snap1["entities"]) == 1 and len(_v23_snap1["journal"]) == 1 and len(_v23_snap1["commands"]) == 1 and len(_v23_snap1["nonces"]) == 1
       and _v23_rec1["prev_digest"] == CS23.GENESIS_DIGEST and _v23_rec1["authority_generation"] == 1 and _v23_rec1["command_digest"] == CS23.command_digest(_v23_c1)
       and _v23_rec1["before_versions"] == {"E1": 0} and _v23_rec1["after_versions"] == {"E1": 1} and _v23_rec1["artifact_digests"] == ["sha256:art"]
       and _v23_rec1["encoding"] == CS23.JOURNAL_ENCODING and _v23_rec1["transition"]["E1"]["digest"] == CS23.digest_of({"kind": "spec", "data": {"a": 1}, "version": 1})
       and CS23.journal_record_digest(_v23_rec1) == _v23_rec1["record_digest"] and _v23_rec1["signature"] == _v23_stub_sign(CS23.journal_signed_bytes(_v23_rec1))
       and set(CS23.JOURNAL_FIELDS) >= {"seq", "prev_digest", "authority_generation", "command_digest", "principal", "before_versions", "after_versions", "transition", "receipt_refs"})
expect("VELDO-0023 AC1 journal/named-refusals: a malformed command (missing field, blank id, unregistered operation, a bool version), a "
       "transition refused by its own check, a signer that returns nothing, and a write without a declared expected version each "
       "refuse by name and write nothing (the snapshot is unchanged)",
       _v23_try(lambda: CS23.execute(_v23_conn, {k: v for k, v in _v23_cmd("x", "upsert_entity", {}, {}).items() if k != "nonce"}, "dmitry", _v23_stub_sign, 1)) == "malformed_command"
       and _v23_try(lambda: CS23.execute(_v23_conn, _v23_cmd(" ", "upsert_entity", {}, {}), "dmitry", _v23_stub_sign, 1)) == "malformed_command"
       and _v23_try(lambda: CS23.execute(_v23_conn, _v23_cmd("x", "drop_everything", {}, {}), "dmitry", _v23_stub_sign, 1)) == "malformed_command"
       and _v23_try(lambda: CS23.execute(_v23_conn, _v23_cmd("x", "upsert_entity", {"entity_id": "E9", "kind": "k", "data": {}}, {"E9": True}), "dmitry", _v23_stub_sign, 1)) == "malformed_command"
       and _v23_try(lambda: CS23.execute(_v23_conn, _v23_cmd("x", "upsert_entity", {"entity_id": "E9"}, {"E9": 0}), "dmitry", _v23_stub_sign, 1)) == "transition_refused"
       and _v23_try(lambda: CS23.execute(_v23_conn, _v23_cmd("x", "upsert_entity", {"entity_id": "E9", "kind": "k", "data": {}}, {"E9": 0}), "dmitry", lambda m: None, 1)) == "incomplete_transaction"
       and _v23_try(lambda: CS23.execute(_v23_conn, _v23_cmd("x", "upsert_entity", {"entity_id": "E9", "kind": "k", "data": {}}, {}), "dmitry", _v23_stub_sign, 1)) == "stale_version"
       and _v23_try(lambda: CS23.execute(_v23_conn, _v23_cmd("x", "upsert_entity", {"entity_id": "E9", "kind": "k", "data": {}}, {"E9": 0}), "dmitry", _v23_stub_sign, 0)) == "malformed_command"
       and CS23.table_snapshot(_v23_conn) == _v23_snap1)

# THE CRASH MATRIX: a real writer process per (registered command, kill point), SIGKILLed at the
# boundary; the reopened store is the complete old state or the complete new state, never a mix.
_v23_child = '''
import importlib.util, sys, json
sp = importlib.util.spec_from_file_location("cs", sys.argv[1]); CS = importlib.util.module_from_spec(sp); sp.loader.exec_module(CS)
conn = CS.open_store(sys.argv[2])
CS.execute(conn, json.loads(sys.argv[3]), "dmitry", lambda m: "stub:" + CS.digest_of(m.decode("utf-8")), 1)
print("REPLIED")
'''
_v23_matrix_cmds = {
    "upsert_entity": lambda tag: _v23_cmd("m-up-" + tag, "upsert_entity", {"entity_id": "U" + tag, "kind": "k", "data": {"t": tag}}, {"U" + tag: 0}),
    "retire_entity": lambda tag: _v23_cmd("m-re-" + tag, "retire_entity", {"entity_id": "E1"}, {"E1": 1}),
    "record_receipt": lambda tag: _v23_cmd("m-rc-" + tag, "record_receipt", {"receipt_id": "R" + tag, "subject": "E1", "digest": "sha256:r"}, {"R" + tag: 0}),
    "reserve": lambda tag: _v23_cmd("m-rs-" + tag, "reserve", {"reservation_id": "RES" + tag, "ceiling": "unit", "delta": 2.5}, {}),
    "record_effect": lambda tag: _v23_cmd("m-ef-" + tag, "record_effect", {"effect_id": "EF" + tag, "kind": "push", "target": "origin"}, {}),
}
KILL_POINTS = ("before_commit", "in_commit", "after_commit")


def _v23_run_child(store_path, db, cmd, kill_at):
    env = dict(_v23_os.environ, VELDO_CONTROL_TEST_HARNESS="1", VELDO_CONTROL_KILL_AT=kill_at)
    return _v23_sp.run([_v23_sys.executable, "-c", _v23_child, str(store_path), db, _v23_json.dumps(cmd)], env=env, capture_output=True, text=True, timeout=120, stdin=_v23_sp.DEVNULL)


def _v23_footprint(snap, cmd):
    """Which of the command's rows are present after reopening: one flag per table it writes."""
    op, p, cid = cmd["operation"], cmd["parameters"], cmd["command_id"]
    flags = {"journal": any(r[4] == cid for r in snap["journal"]), "commands": any(r[0] == cid for r in snap["commands"]),
             "nonces": any(r[0] == cmd["nonce"] for r in snap["nonces"])}
    if op in ("upsert_entity", "record_receipt"):
        flags["entities"] = any(r[0] == p.get("entity_id", p.get("receipt_id")) for r in snap["entities"])
    if op == "retire_entity":
        flags["entities"] = any(r[0] == "E1" and _v23_json.loads(r[4]).get("retired") is True for r in snap["entities"])
    if op == "reserve":
        flags["reservations"] = any(r[0] == p["reservation_id"] for r in snap["reservations"])
    if op == "record_effect":
        flags["effects"] = any(r[0] == p["effect_id"] for r in snap["effects"])
    return flags


def _v23_crash_matrix(store_path, kill_points, extra_ops=()):
    """(inconsistencies, killed, committed): for every registered command and kill point, run a
    writer, kill it, reopen, and check the store is all-or-nothing for that command."""
    db = _v23_fresh_db("matrix-%s-%s" % (_v23_Path(store_path).parent.name, "-".join(kill_points)))  # one store per matrix run
    conn = CS23.open_store(db)
    CS23.execute(conn, _v23_cmd("seed", "upsert_entity", {"entity_id": "E1", "kind": "spec", "data": {}}, {"E1": 0}), "dmitry", _v23_stub_sign, 1)
    conn.close()
    inconsistent, killed, committed = [], 0, 0
    for op, mk in _v23_matrix_cmds.items():
        for kp in kill_points:
            tag = "%s-%s" % (op[:2], kp)
            cmd = mk(tag)
            if op == "retire_entity":
                # E1 must be at version 1 for each retire attempt: give each its own entity.
                cmd = _v23_cmd("m-re-" + tag, "upsert_entity", {"entity_id": "E1", "kind": "spec", "data": {"retired": True}}, {"E1": 1})
                cmd["operation"] = "retire_entity"
                cmd["parameters"] = {"entity_id": "E1"}
                # reset E1 to version 1 with fresh data before the attempt
                c = CS23.open_store(db)
                c.execute("UPDATE entities SET version=1, data='{}' WHERE id='E1'")
                c.close()
            r = _v23_run_child(store_path, db, cmd, kp)
            if r.returncode == -9:
                killed += 1
            c = CS23.open_store(db)
            flags = _v23_footprint(CS23.table_snapshot(c), cmd)
            c.close()
            vals = set(flags.values())
            if len(vals) != 1:
                inconsistent.append((op, kp, flags))
            elif vals == {True}:
                committed += 1
    return inconsistent, killed, committed


_v23_incons, _v23_killed, _v23_committed = _v23_crash_matrix(_v23_store_path, KILL_POINTS)
expect("VELDO-0023 AC1 journal/atomic-kill: for EVERY registered command (the registry's five, compared to the matrix) and every kill "
       "point (before COMMIT, inside COMMIT via the progress handler, after COMMIT before the reply) the writer process is "
       "SIGKILLed (fifteen kills) and the reopened store holds either the complete old or the complete new rows for that command "
       "across entities, journal, commands, nonces, reservations and effects; the after-commit kills are the committed ones "
       "(inconsistencies: %s)" % _v23_incons[:2],
       _v23_incons == [] and _v23_killed == len(CS23.COMMAND_REGISTRY) * len(KILL_POINTS) and _v23_committed == len(CS23.COMMAND_REGISTRY)
       and set(_v23_matrix_cmds) == set(CS23.COMMAND_REGISTRY))
# THE DECLARED FALSIFIER: move journal insertion outside the domain transaction and SIGKILL after the entity commit.
_V23_M1, _V23_M1_PATH = _v23_mutated(_v23_store_src, '''        seq, prev = _last_journal(conn)
        record = {''', '''        conn.execute("COMMIT")  # mutant: the entity commit is its own transaction
        _kill_point("after_entity_commit")
        conn.execute("BEGIN IMMEDIATE")
        seq, prev = _last_journal(conn)
        record = {''', "control_store.py")
_v23_m1_incons, _v23_m1_killed, _v23_m1_committed = _v23_crash_matrix(_V23_M1_PATH, ("after_entity_commit",))
_v23_ok_incons, _v23_ok_killed, _v23_ok_committed = _v23_crash_matrix(_v23_store_path, ("after_entity_commit",))
expect("VELDO-0023 AC1 journal/atomic-kill DRIVEN (the declared falsifier): with journal insertion moved outside the domain transaction "
       "in a copy and the writer SIGKILLed after the entity commit, the reopened store holds entity rows without their journal "
       "record, so the row reds; unmutated, that kill point never fires and every command commits whole",
       _v23_m1_incons != [] and any(f["journal"] is False and f.get("entities") is True for _o, _k, f in _v23_m1_incons)
       and _v23_ok_incons == [] and _v23_ok_killed == 0 and _v23_ok_committed == len(CS23.COMMAND_REGISTRY))

# ---------------------------------------------------------------------------------------------
# AC2: identical retries replay, altered content and stale versions refuse; raced from processes.
# ---------------------------------------------------------------------------------------------
_v23_r1_again = CS23.execute(_v23_conn, _v23_copy.deepcopy(_v23_c1), "dmitry", _v23_stub_sign, 1)
_v23_snap_after_retry = CS23.table_snapshot(_v23_conn)
expect("VELDO-0023 AC2 journal/identical-retry: the same command again returns the ORIGINAL committed result (same seq, record digest, "
       "result digest) marked replayed, and writes nothing; the store is byte-identical to before the retry",
       _v23_r1_again["replayed"] is True and _v23_r1_again["seq"] == _v23_r1["seq"] and _v23_r1_again["record_digest"] == _v23_r1["record_digest"]
       and _v23_r1_again["result_digest"] == _v23_r1["result_digest"] and _v23_snap_after_retry == _v23_snap1)
expect("VELDO-0023 AC2 journal/content-reuse: the same command id with one changed parameter, a changed principal, a changed nonce or a "
       "changed artifact digest is refused as a content conflict; a new id against a stale expected version is refused as stale; a "
       "new id reusing a consumed nonce is refused; each writes nothing",
       _v23_try(lambda: CS23.execute(_v23_conn, dict(_v23_c1, parameters={"entity_id": "E1", "kind": "spec", "data": {"a": 2}}), "dmitry", _v23_stub_sign, 1)) == "command_content_conflict"
       and _v23_try(lambda: CS23.execute(_v23_conn, dict(_v23_c1, principal="asya"), "dmitry", _v23_stub_sign, 1)) == "command_content_conflict"
       and _v23_try(lambda: CS23.execute(_v23_conn, dict(_v23_c1, nonce="other"), "dmitry", _v23_stub_sign, 1)) == "command_content_conflict"
       and _v23_try(lambda: CS23.execute(_v23_conn, dict(_v23_c1, artifact_digests=[]), "dmitry", _v23_stub_sign, 1)) == "command_content_conflict"
       and _v23_try(lambda: CS23.execute(_v23_conn, _v23_cmd("c2", "upsert_entity", {"entity_id": "E1", "kind": "spec", "data": {"a": 2}}, {"E1": 0}), "dmitry", _v23_stub_sign, 1)) == "stale_version"
       and _v23_try(lambda: CS23.execute(_v23_conn, _v23_cmd("c2", "upsert_entity", {"entity_id": "E1", "kind": "spec", "data": {"a": 2}}, {"E1": 1}, nonce="n-c1"), "dmitry", _v23_stub_sign, 1)) == "nonce_consumed"
       and CS23.table_snapshot(_v23_conn) == _v23_snap1)


def _v23_race(store_path, db, cmd_a, cmd_b):
    """Two REAL client processes issue cmd_a and cmd_b concurrently against one store; returns the
    two outcomes (REPLIED / refusal code) and the reopened snapshot."""
    procs = [_v23_sp.Popen([_v23_sys.executable, "-c", _v23_child.replace('print("REPLIED")', 'print("REPLIED")') + '''
''', str(store_path), db, _v23_json.dumps(c)], stdout=_v23_sp.PIPE, stderr=_v23_sp.PIPE, text=True, stdin=_v23_sp.DEVNULL,
                          env=dict(_v23_os.environ, VELDO_CONTROL_TEST_HARNESS="0")) for c in (cmd_a, cmd_b)]
    outs = []
    for p in procs:
        out, err = p.communicate(timeout=120)
        code = "REPLIED" if "REPLIED" in out else next((c for c in CS23.REFUSALS if c + ":" in err), "other:" + err[-200:])
        outs.append(code)
    c = CS23.open_store(db)
    snap = CS23.table_snapshot(c)
    c.close()
    return outs, snap


_v23_race_db = _v23_fresh_db("race")
_v23_rc = CS23.open_store(_v23_race_db)
CS23.execute(_v23_rc, _v23_cmd("seed", "upsert_entity", {"entity_id": "E1", "kind": "spec", "data": {}}, {"E1": 0}), "dmitry", _v23_stub_sign, 1)
_v23_rc.close()
_v23_same = _v23_cmd("race-1", "upsert_entity", {"entity_id": "E1", "kind": "spec", "data": {"v": 1}}, {"E1": 1})
_v23_same_outs, _v23_same_snap = _v23_race(_v23_store_path, _v23_race_db, _v23_same, _v23_copy.deepcopy(_v23_same))
_v23_alt_a = _v23_cmd("race-2", "upsert_entity", {"entity_id": "E1", "kind": "spec", "data": {"v": "a"}}, {"E1": 2})
_v23_alt_b = dict(_v23_alt_a, parameters={"entity_id": "E1", "kind": "spec", "data": {"v": "b"}})
_v23_alt_outs, _v23_alt_snap = _v23_race(_v23_store_path, _v23_race_db, _v23_alt_a, _v23_alt_b)
_v23_ver_a = _v23_cmd("race-3a", "upsert_entity", {"entity_id": "E1", "kind": "spec", "data": {"v": 3}}, {"E1": 3})
_v23_ver_b = _v23_cmd("race-3b", "upsert_entity", {"entity_id": "E1", "kind": "spec", "data": {"v": 4}}, {"E1": 3})
_v23_ver_outs, _v23_ver_snap = _v23_race(_v23_store_path, _v23_race_db, _v23_ver_a, _v23_ver_b)
_v23_race_e1 = next(r for r in _v23_ver_snap["entities"] if r[0] == "E1")
expect("VELDO-0023 AC2 journal/one-winner: two client processes racing the SAME command both reply (one commits, one replays) and one "
       "row of each kind exists; racing two payloads under one id, exactly one commits and the other is a content conflict; racing "
       "two ids with the same expected version, exactly one commits and the other is stale, E1 ends at version 4 with one journal "
       "record per committed command (outcomes: %s %s %s)" % (_v23_same_outs, _v23_alt_outs, _v23_ver_outs),
       _v23_same_outs == ["REPLIED", "REPLIED"] and sum(1 for r in _v23_same_snap["commands"] if r[0] == "race-1") == 1 and sum(1 for r in _v23_same_snap["journal"] if r[4] == "race-1") == 1
       and sorted(_v23_alt_outs) == ["REPLIED", "command_content_conflict"] and sum(1 for r in _v23_alt_snap["commands"] if r[0] == "race-2") == 1
       and sorted(_v23_ver_outs) == ["REPLIED", "stale_version"] and _v23_race_e1[2] == 4
       and len(_v23_ver_snap["journal"]) == 4 and len(_v23_ver_snap["commands"]) == 4 and len(_v23_ver_snap["nonces"]) == 4)
# THE DECLARED FALSIFIER: disable the command-digest equality check and race changed payloads under one id.
_V23_M2, _V23_M2_PATH = _v23_mutated(_v23_store_src, '''            if prior[0] != cdigest:
                raise StoreRefused("command_content_conflict",''', '''            if False:  # mutant: any retry under a known id is the same command
                raise StoreRefused("command_content_conflict",''', "control_store.py")
_v23_m2_db = _v23_fresh_db("race-m2")
_v23_m2c = CS23.open_store(_v23_m2_db)
CS23.execute(_v23_m2c, _v23_cmd("seed", "upsert_entity", {"entity_id": "E1", "kind": "spec", "data": {}}, {"E1": 0}), "dmitry", _v23_stub_sign, 1)
_v23_m2c.close()
_v23_m2_a = _v23_cmd("race-m", "upsert_entity", {"entity_id": "E1", "kind": "spec", "data": {"v": "a"}}, {"E1": 1})
_v23_m2_outs, _v23_m2_snap = _v23_race(_V23_M2_PATH, _v23_m2_db, _v23_m2_a, dict(_v23_m2_a, parameters={"entity_id": "E1", "kind": "spec", "data": {"v": "b"}}))
expect("VELDO-0023 AC2 journal/content-reuse DRIVEN (the declared falsifier): with the command-digest equality check disabled in a copy, "
       "two payloads raced under one id BOTH reply (the altered retry is handed the other's result), so the row reds; unmutated, "
       "the altered retry is a content conflict, in process and in the race",
       _v23_m2_outs == ["REPLIED", "REPLIED"]
       and _V23_M2.execute(CS23.open_store(_v23_m2_db), dict(_v23_m2_a, parameters={"entity_id": "E1", "kind": "spec", "data": {"v": "c"}}), "dmitry", _v23_stub_sign, 1)["replayed"] is True
       and sorted(_v23_alt_outs) == ["REPLIED", "command_content_conflict"])

# ---------------------------------------------------------------------------------------------
# AC3: deterministic replay from verified signed history, with the execution environment removed.
# ---------------------------------------------------------------------------------------------
_v23_have_ssh = _v23_shutil.which("ssh-keygen") is not None
_v23_replay_child = '''
import importlib.util, sys, json
for m in list(sys.modules):
    if "langgraph" in m or "sqlite3" in m:
        raise SystemExit("execution environment present: " + m)
sp = importlib.util.spec_from_file_location("cr", sys.argv[1]); CR = importlib.util.module_from_spec(sp); sp.loader.exec_module(CR)
recs = json.load(open(sys.argv[2]))
def verify(msg, sig, signer):
    return (sig == "stub:" + CR.digest_of(msg.decode("utf-8")), "stub")
out = CR.replay(recs, verify)
print(json.dumps({"state_digest": out["state_digest"], "head": out["head_digest"], "records": out["records"], "sqlite_loaded": "sqlite3" in sys.modules}))
'''
_v23_hist_db = _v23_fresh_db("history")
_v23_hc = CS23.open_store(_v23_hist_db)
for _c in (_v23_cmd("h1", "upsert_entity", {"entity_id": "E1", "kind": "spec", "data": {"a": 1}}, {"E1": 0}),
           _v23_cmd("h2", "upsert_entity", {"entity_id": "E2", "kind": "plan", "data": {"b": [1, 2]}}, {"E2": 0}),
           _v23_cmd("h3", "upsert_entity", {"entity_id": "E1", "kind": "spec", "data": {"a": 2}}, {"E1": 1}),
           _v23_cmd("h4", "reserve", {"reservation_id": "R1", "ceiling": "project", "delta": 1.0}, {}),
           _v23_cmd("h5", "record_receipt", {"receipt_id": "RC1", "subject": "E1", "digest": "sha256:x"}, {"RC1": 0}),
           _v23_cmd("h6", "retire_entity", {"entity_id": "E2"}, {"E2": 1}),
           _v23_cmd("h7", "record_effect", {"effect_id": "F1", "kind": "push", "target": "origin"}, {}),):
    CS23.execute(_v23_hc, _c, "dmitry", _v23_stub_sign, 1)
_v23_hist = CS23.export_journal(_v23_hc)
_v23_live = CS23.materialized_state(_v23_hc)
_v23_hist_file = _v23_tmp / "history.json"
_v23_hist_file.write_text(_v23_json.dumps(_v23_hist))
_v23_rp = _v23_sp.run([_v23_sys.executable, "-I", "-c", _v23_replay_child, str(_v23_replay_path), str(_v23_hist_file)], capture_output=True, text=True, timeout=120, stdin=_v23_sp.DEVNULL)
_v23_rp_out = _v23_json.loads(_v23_rp.stdout) if _v23_rp.returncode == 0 else {"error": _v23_rp.stderr[-300:]}
_v23_replay_imports = sorted({n.names[0].name.split(".")[0] if isinstance(n, _v23_ast.Import) else n.module.split(".")[0]
                              for n in _v23_ast.walk(_v23_ast.parse(_v23_replay_src)) if isinstance(n, (_v23_ast.Import, _v23_ast.ImportFrom))})
_v23_store_imports = sorted({n.names[0].name.split(".")[0] if isinstance(n, _v23_ast.Import) else n.module.split(".")[0]
                             for n in _v23_ast.walk(_v23_ast.parse(_v23_store_src)) if isinstance(n, (_v23_ast.Import, _v23_ast.ImportFrom))})
expect("VELDO-0023 AC3 journal/replay-determinism: seven records of every transition kind (upsert, update, reserve, receipt, retire, "
       "effect) replay in an ISOLATED process (python -I, the replay module alone, sqlite3 never imported) into a state whose digest "
       "equals the live store's, with the head digest equal to the last record's; the replay module imports only hashlib and json "
       "and the store imports only the standard library (no execution runtime); in-process replay agrees and compare_with_live matches",
       _v23_rp.returncode == 0 and _v23_rp_out.get("state_digest") == CS23.state_digest(_v23_live) and _v23_rp_out.get("records") == 7
       and _v23_rp_out.get("head") == _v23_hist[-1]["record_digest"] and _v23_rp_out.get("sqlite_loaded") is False
       and _v23_replay_imports == ["hashlib", "json"] and set(_v23_store_imports) <= {"hashlib", "json", "os", "signal", "sqlite3", "subprocess", "time"}
       and CR23.compare_with_live(CR23.replay(_v23_hist, _v23_stub_verify), _v23_live)["matches"] is True
       and CR23.compare_with_live(CR23.replay(_v23_hist, _v23_stub_verify), dict(_v23_live, entities=dict(_v23_live["entities"], E9={"kind": "k", "version": 1, "digest": "d", "data": {}})))["matches"] is False)
# THE REVIEW'S FOUR FINDINGS, each pinned (review-20260917-220917).
_v23_full = CR23.replay(_v23_hist, _v23_stub_verify)["state"]
_v23_wiped = CS23.open_store(_v23_hist_db)
_v23_wiped.execute("PRAGMA foreign_keys=OFF")
_v23_wiped.execute("DELETE FROM reservations"); _v23_wiped.execute("DELETE FROM effects"); _v23_wiped.execute("DELETE FROM nonces")
_v23_wiped_live = CS23.materialized_state(_v23_wiped)
_v23_wiped_cmp = CR23.compare_with_live(CR23.replay(_v23_hist, _v23_stub_verify), _v23_wiped_live)
_v23_wiped.close()
expect("VELDO-0023 AC3 journal/full-state-recovery (review 1): the signed record carries the consumed nonce, the reservation and the "
       "effect, so replay rebuilds reservations, effects and nonces (seven nonces, R1 with its ceiling and delta, F1 obligated) beside "
       "the entities; a live store whose reservations, effects and nonces were deleted no longer matches the rebuilt state and the "
       "differences name each lost row; the state digest covers all four parts",
       set(_v23_full) == set(CR23.STATE_PARTS) == set(CS23.STATE_PARTS) and len(_v23_full["nonces"]) == 7 and _v23_full["nonces"]["n-h4"] == "h4"
       and _v23_full["reservations"] == {"R1": {"command_id": "h4", "ceiling": "project", "delta": 1.0}}
       and _v23_full["effects"] == {"F1": {"command_id": "h7", "kind": "push", "target": "origin", "state": "obligated"}}
       and _v23_wiped_cmp["matches"] is False and {"reservations:R1", "effects:F1", "nonces:n-h1"} <= set(_v23_wiped_cmp["differences"])
       and {"nonce", "reservations", "effects"} <= set(CS23.JOURNAL_FIELDS) and CS23.JOURNAL_FIELDS == CR23.JOURNAL_FIELDS
       and CS23.state_digest({"entities": _v23_full["entities"]}) != CS23.state_digest(_v23_full))
_v23_iter_db = _v23_fresh_db("iter")
_v23_ic = CS23.open_store(_v23_iter_db)
_v23_ir = CS23.execute(_v23_ic, _v23_cmd("i1", "upsert_entity", {"entity_id": "E1", "kind": "k", "data": {}}, {"E1": 0}), "dmitry", _v23_stub_sign, 1, receipt_refs=iter(["R-a", "R-b"]))
_v23_irec = CS23.export_journal(_v23_ic)[0]
expect("VELDO-0023 AC1 journal/receipt-refs-once (review 1): receipt references passed as an ITERATOR are materialized once, so the signed "
       "record and the stored record carry the same ['R-a', 'R-b'] and the committed history replays; a non-string receipt reference "
       "is refused as malformed before the transaction opens",
       _v23_ir["committed"] is True and _v23_irec["receipt_refs"] == ["R-a", "R-b"] and CR23.replay(CS23.export_journal(_v23_ic), _v23_stub_verify)["records"] == 1
       and _v23_try(lambda: CS23.execute(_v23_ic, _v23_cmd("i2", "upsert_entity", {"entity_id": "E2", "kind": "k", "data": {}}, {"E2": 0}), "dmitry", _v23_stub_sign, 1, receipt_refs=[7])) == "malformed_command")
_v23_ro = CS23.open_store(_v23_iter_db, mode="r")
_v23_ro_code = _v23_try(lambda: CS23.execute(_v23_ro, _v23_cmd("ro1", "upsert_entity", {"entity_id": "RO", "kind": "k", "data": {}}, {"RO": 0}), "dmitry", _v23_stub_sign, 1))
_v23_ro_rows = len(CS23.export_journal(_v23_ro))
_v23_ro.close()
_v23_ic.close()
expect("VELDO-0023 AC1 journal/read-only-handle (review 1): a store opened with mode='r' is a genuinely read-only SQLite handle: a command "
       "through it is refused as read_only_handle, the journal is unchanged and still readable, and a missing store refuses to open "
       "read-only rather than being created",
       _v23_ro_code == "read_only_handle" and _v23_ro_rows == 1 and len(CS23.export_journal(CS23.open_store(_v23_iter_db))) == 1
       and _v23_try(lambda: CS23.open_store(str(_v23_tmp / "absent" / "c.sqlite3"), mode="r")) == "incomplete_transaction"
       and not (_v23_tmp / "absent" / "c.sqlite3").exists())
_v23_real_dir = _v23_tmp / "real-nfs"
_v23_real_dir.mkdir()
_v23_link_dir = _v23_tmp / "link-dir"
_v23_os.symlink(str(_v23_real_dir), str(_v23_link_dir))
_v23_mounts = "srv:/v %s nfs rw 0 0\n" % str(_v23_real_dir)
_v23_ok_db = _v23_fresh_db("ok-target")
_v23_file_link = _v23_tmp / "file-link.sqlite3"
_v23_os.symlink(str(_v23_real_dir / "c.sqlite3"), str(_v23_file_link))
expect("VELDO-0023 AC1 journal/symlink-qualification (review 1): qualification judges the RESOLVED target: a symlinked directory and a "
       "symlinked database file that both point into a network mount (fixture mount table) refuse to open for writes exactly as the "
       "direct path does, and resolved_target returns the real path; a symlink into a qualified directory opens",
       _v23_try(lambda: CS23.open_store(str(_v23_real_dir / "c.sqlite3"), mounts_text=_v23_mounts)) == "unsupported_filesystem"
       and _v23_try(lambda: CS23.open_store(str(_v23_link_dir / "c.sqlite3"), mounts_text=_v23_mounts)) == "unsupported_filesystem"
       and _v23_try(lambda: CS23.open_store(str(_v23_file_link), mounts_text=_v23_mounts)) == "unsupported_filesystem"
       and CS23.resolved_target(str(_v23_link_dir / "c.sqlite3")) == str(_v23_real_dir.resolve() / "c.sqlite3")
       and CS23.open_store(str(_v23_link_dir / "c.sqlite3")) is not None and (_v23_real_dir / "c.sqlite3").exists())


def _v23_corrupt(name):
    tt = _v23_copy.deepcopy(_v23_hist)
    if name == "field":
        tt[2]["transition"]["E1"]["data"]["a"] = 99
    elif name == "reorder":
        tt[1], tt[2] = tt[2], tt[1]
    elif name == "duplicate":
        tt.insert(3, _v23_copy.deepcopy(tt[2]))
    elif name == "remove":
        tt.pop(4)
    elif name == "signature":
        tt[5]["signature"] = tt[4]["signature"]
    elif name == "identity":
        tt[1]["principal"] = "mallory"
    elif name == "encoding":
        tt[0]["encoding"] = "veldo.journal/v0"
    elif name == "generation":
        tt[3]["authority_generation"] = 7
    elif name == "versions":
        tt[2]["before_versions"] = {"E1": 5}
    elif name == "nonce":
        tt[1]["nonce"] = "stolen"
    elif name == "reservation":
        tt[3]["reservations"][0]["delta"] = 1000.0
    elif name == "resign_bad_prev":
        tt[3]["prev_digest"] = "sha256:wrong"
        tt[3]["record_digest"] = CR23.record_digest(tt[3])
        tt[3]["signature"] = _v23_stub_sign(CR23.signed_bytes(tt[3]))
    elif name == "resign_field":
        tt[2]["transition"]["E1"]["data"]["a"] = 99
        tt[2]["record_digest"] = CR23.record_digest(tt[2])
        tt[2]["signature"] = _v23_stub_sign(CR23.signed_bytes(tt[2]))
    return tt


_v23_expected_refusals = {"field": "digest_mismatch", "reorder": "sequence_broken", "duplicate": "sequence_broken", "remove": "sequence_broken",
                          "signature": "signature_invalid", "identity": "digest_mismatch", "encoding": "unsupported_encoding", "generation": "digest_mismatch",
                          "versions": "digest_mismatch", "nonce": "digest_mismatch", "reservation": "digest_mismatch",
                          "resign_bad_prev": "chain_broken", "resign_field": "chain_broken"}
_v23_got = {n: _v23_try(lambda: CR23.replay(_v23_corrupt(n), _v23_stub_verify)) for n in _v23_expected_refusals}
expect("VELDO-0023 AC3 journal/replay-chain: every corruption of the signed history refuses reconstruction by name: a changed field "
       "(digest mismatch), reorder, duplicate and removal (sequence broken), a swapped signature, a changed identity, generation or "
       "versions (digest mismatch), an unknown encoding, and a record RE-SIGNED with a wrong predecessor digest or re-signed after a "
       "field change (chain broken: the next record's prev_digest no longer matches), a changed nonce or reservation delta (digest "
       "mismatch: they are signed fields) (got: %s)" % {k: v for k, v in _v23_got.items() if v != _v23_expected_refusals[k]},
       _v23_got == _v23_expected_refusals)
# THE DECLARED FALSIFIER: skip previous-record digest verification and re-sign one record with an incorrect predecessor digest.
_V23_M3, _V23_M3_PATH = _v23_mutated(_v23_replay_src, '''        if rec["prev_digest"] != prev:
            raise ReplayRefused("chain_broken",''', '''        if False:  # mutant: the chain is taken on trust
            raise ReplayRefused("chain_broken",''', "control_replay.py")
_v23_bad_prev = _v23_corrupt("resign_bad_prev")
# make the chain continue from the re-signed record so only the prev check can catch it
for _i in range(4, len(_v23_bad_prev)):
    _v23_bad_prev[_i]["prev_digest"] = _v23_bad_prev[_i - 1]["record_digest"]
    _v23_bad_prev[_i]["record_digest"] = CR23.record_digest(_v23_bad_prev[_i])
    _v23_bad_prev[_i]["signature"] = _v23_stub_sign(CR23.signed_bytes(_v23_bad_prev[_i]))
expect("VELDO-0023 AC3 journal/replay-chain DRIVEN (the declared falsifier): with previous-record digest verification skipped in a copy, "
       "a history whose fourth record was re-signed with a wrong predecessor digest (sequence continuity retained, later records "
       "re-chained onto it) rebuilds state, so the row reds; unmutated it refuses as chain_broken at seq 4",
       _V23_M3.replay(_v23_bad_prev, _v23_stub_verify)["records"] == 7
       and _v23_try(lambda: CR23.replay(_v23_bad_prev, _v23_stub_verify)) == "chain_broken")

# A REAL signature: the journal signed through the installed ssh-keygen with a fresh Ed25519 key and
# verified through the same OpenSSH; a wrong key and a tampered record refuse.
if _v23_have_ssh:
    _v23_kd = _v23_tmp / "keys"
    _v23_kd.mkdir()
    _v23_sp.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "dmitry@veldo", "-f", str(_v23_kd / "key")], check=True, capture_output=True, stdin=_v23_sp.DEVNULL, timeout=60)
    _v23_sp.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(_v23_kd / "other")], check=True, capture_output=True, stdin=_v23_sp.DEVNULL, timeout=60)
    _v23_pub = (_v23_kd / "key.pub").read_text()
    _v23_signers = 'dmitry namespaces="veldo-journal" %s\n' % " ".join(_v23_pub.split()[:2])
    _v23_other_signers = 'dmitry namespaces="veldo-journal" %s\n' % " ".join((_v23_kd / "other.pub").read_text().split()[:2])

    def _v23_real_sign(msg):
        f = _v23_kd / "m.bin"
        f.write_bytes(msg)
        sig = _v23_kd / "m.bin.sig"
        if sig.exists():
            sig.unlink()  # ssh-keygen asks before overwriting a .sig and would block on stdin
        _v23_sp.run(["ssh-keygen", "-Y", "sign", "-f", str(_v23_kd / "key"), "-n", "veldo-journal", str(f)], check=True, capture_output=True, stdin=_v23_sp.DEVNULL, timeout=60)
        return sig.read_text()

    def _v23_real_verify_with(signers_text):
        def verify(msg, sig, signer):
            sf, sg = _v23_kd / "allowed_signers", _v23_kd / "v.sig"
            sf.write_text(signers_text)
            sg.write_text(sig)
            r = _v23_sp.run(["ssh-keygen", "-Y", "verify", "-f", str(sf), "-I", signer, "-n", "veldo-journal", "-s", str(sg)], input=msg, capture_output=True, stdin=None, timeout=60)
            return r.returncode == 0, (r.stdout + r.stderr).decode("utf-8", "replace")
        return verify

    _v23_sdb = _v23_fresh_db("signed")
    _v23_sc = CS23.open_store(_v23_sdb)
    for _c in (_v23_cmd("s1", "upsert_entity", {"entity_id": "E1", "kind": "spec", "data": {"a": 1}}, {"E1": 0}),
               _v23_cmd("s2", "upsert_entity", {"entity_id": "E1", "kind": "spec", "data": {"a": 2}}, {"E1": 1})):
        CS23.execute(_v23_sc, _c, "dmitry", _v23_real_sign, 1)
    _v23_shist = CS23.export_journal(_v23_sc)
    _v23_stampered = _v23_copy.deepcopy(_v23_shist)
    _v23_stampered[1]["transition"]["E1"]["data"]["a"] = 3
    _v23_stampered[1]["record_digest"] = CR23.record_digest(_v23_stampered[1])
    expect("VELDO-0023 AC3 journal/real-signature: a history signed through the installed ssh-keygen (Ed25519, namespace veldo-journal) "
           "replays to the live state's digest when verified through ssh-keygen against the signer's key; the same history verified "
           "against another key, and a record whose field and digest were changed but not re-signed, each refuse as signature_invalid",
           _v23_shist[0]["signature"].startswith("-----BEGIN SSH SIGNATURE-----")
           and CR23.compare_with_live(CR23.replay(_v23_shist, _v23_real_verify_with(_v23_signers)), CS23.materialized_state(_v23_sc))["matches"] is True
           and _v23_try(lambda: CR23.replay(_v23_shist, _v23_real_verify_with(_v23_other_signers))) == "signature_invalid"
           and _v23_try(lambda: CR23.replay(_v23_stampered, _v23_real_verify_with(_v23_signers))) == "signature_invalid")
    _v23_sc.close()
else:
    expect("VELDO-0023 AC3 journal/real-signature: STOOD DOWN by name - ssh-keygen is not installed here, so the real-signature rows "
           "cannot run; the store and replay rows above ran with the stub signer", True)

_v23_conn.close()
_v23_shutil.rmtree(_v23_tmp, ignore_errors=True)
