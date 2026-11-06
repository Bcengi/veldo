import importlib.util, sys, tempfile, os
p = sys.argv[1]
sp = importlib.util.spec_from_file_location("s", p); S = importlib.util.module_from_spec(sp); sp.loader.exec_module(S)
d = tempfile.mkdtemp(prefix="v261probe-"); db = d + "/control.sqlite3"
h = S.open_store(db); w = S.open_store(db); w.execute("PRAGMA busy_timeout=50")
def begin(conn, cid):
    c = {"command_id": cid, "principal": "owner", "operation": "upsert_entity", "nonce": cid, "artifact_digests": [],
         "expected_versions": {"busy:entity": 0}, "parameters": {"entity_id": "busy:entity", "kind": "note", "data": {}}}
    try:
        S.execute(conn, c, "owner", lambda m: "unsigned", 1); return "committed"
    except S.StoreRefused as e:
        return e.code + " | " + e.detail
h.execute("BEGIN IMMEDIATE"); print("busy:", begin(w, "b1")); h.execute("ROLLBACK")
print("read-only:", begin(S.open_store(db, mode="r"), "b2"))
