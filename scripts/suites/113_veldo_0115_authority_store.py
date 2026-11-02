"""VELDO-0115: observe real transactions, isolation and durability through local IPC.

Only ROOT and expect come from the suite harness. The standalone driver also
executes this file, including under each declared falsifier, without other suites.
"""
import ast as _v115_ast
import importlib.util as _v115_import
import itertools as _v115_it
import json as _v115_json
import os as _v115_os
from pathlib import Path as _v115_Path
import tempfile as _v115_temp

_v115_fixture_path = _v115_Path(globals().get(
    "V115_FIXTURE", ROOT / "scripts/fixtures/authority_store.py"))
_v115_spec = _v115_import.spec_from_file_location("authority_store_fixture", _v115_fixture_path)
_v115_fixture = _v115_import.module_from_spec(_v115_spec)
_v115_spec.loader.exec_module(_v115_fixture)

# Exhaust the public client API, rather than silently testing a hardcoded subset
# when another entry point is added. Builders and server-side dispatch are listed
# explicitly; send is the public routing call accepting an arbitrary mutation.
_v115_api = {
    "send": "mutation", "inspect": "read",
    "build_request": "builder", "signed_bytes": "encoding", "request_problems": "validation",
    "socket_path_for": "address", "service_id": "identity", "service_unit": "identity",
    "start_guidance": "diagnostic", "peer_uid": "authentication", "seen_path": "cache",
    "record_seen": "cache", "last_seen": "cache", "bind": "server",
    "serve_one": "server", "serve_forever": "server", "main": "help",
    "Authority.judge": "server",
}
_v115_tree = _v115_ast.parse((ROOT / ".veldo/control_client.py").read_text())
_v115_actual = {node.name for node in _v115_tree.body
                if isinstance(node, (_v115_ast.FunctionDef, _v115_ast.AsyncFunctionDef))
                and not node.name.startswith("_")}
for _v115_node in _v115_tree.body:
    if isinstance(_v115_node, _v115_ast.ClassDef):
        _v115_actual.update(_v115_node.name + "." + method.name for method in _v115_node.body
                           if isinstance(method, _v115_ast.FunctionDef)
                           and not method.name.startswith("_"))
_v115_census = _v115_actual == set(_v115_api)
_v115_routes = {name for name, kind in _v115_api.items() if kind == "mutation"}
_v115_modes = list(_v115_it.product((False, True), repeat=3))
_v115_expected = {(route, mode, direction) for route in _v115_routes
                  for mode in _v115_modes for direction in (0, 1)}
_v115_completed = set()
_v115_records = []
_v115_reopens = []
_v115_controls = []
_v115_units = []


def _v115_transaction(before, after, cmd, response, binding, signer):
    """Independent expected upsert plus exact delta across every logical table."""
    if set(before) != set(after):
        return False
    added = {}
    for table in before:
        if not all(row in after[table] for row in before[table]):
            return False
        added[table] = [row for row in after[table] if row not in before[table]]
        wanted = 1 if table in ("entities", "journal", "commands", "nonces", "publication") else 0
        if len(added[table]) != wanted or len(after[table]) != len(before[table]) + wanted:
            return False
    seq = _v115_fixture.watermark(before) + 1
    eid = cmd["parameters"]["entity_id"]
    data = cmd["parameters"]["data"]
    entity = {"kind": "fixture", "data": data, "version": 1}
    edigest = _v115_fixture.digest(entity)
    if added["entities"] != [{"id": eid, "kind": "fixture", "version": 1,
                              "digest": edigest, "data": _v115_json.dumps(data, sort_keys=True)}]:
        return False
    prior = max(before["journal"], key=lambda row: row["seq"])
    record = {
        "seq": seq, "prev_digest": prior["record_digest"], "authority_generation": 1,
        "command_id": cmd["command_id"], "command_digest": _v115_fixture.digest(cmd),
        "principal": "fixture", "signer": "fixture", "before_versions": {eid: 0},
        "after_versions": {eid: 1}, "transition": {eid: dict(entity, digest=edigest)},
        "nonce": cmd["nonce"], "reservations": [], "effects": [], "receipt_refs": [],
        "artifact_digests": [], "encoding": "veldo.journal/v1",
    }
    record["record_digest"] = _v115_fixture.digest(record)
    journal = dict(added["journal"][0])
    signature = journal.pop("signature")
    for field in ("before_versions", "after_versions", "transition", "reservations", "effects",
                  "receipt_refs", "artifact_digests"):
        journal[field] = _v115_json.loads(journal[field])
    signed = _v115_json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    if journal != record or not signer.verify(signed, signature):
        return False
    result = {"committed": True, "command_id": cmd["command_id"], "seq": seq,
              "record_digest": record["record_digest"], "after_versions": {eid: 1},
              "effects": [], "reservations": []}
    result["result_digest"] = _v115_fixture.digest(result)
    publication = {"seq": seq, "command_id": cmd["command_id"], "committed_at": 2.0,
                   "export_id": None, "export_digest": None, "remote_commit": None,
                   "remote": None, "ref": None, "acked_at": None, "durability": None,
                   "dispatched_at": None, "backfilled": 0}
    return (added["commands"] == [{"command_id": cmd["command_id"],
                                  "command_digest": _v115_fixture.digest(cmd),
                                  "result": _v115_json.dumps(result, sort_keys=True),
                                  "result_digest": result["result_digest"], "seq": seq}]
            and added["nonces"] == [{"nonce": cmd["nonce"], "command_id": cmd["command_id"]}]
            and added["publication"] == [publication]
            and response == {"schema": "veldo.control_response/v1", "accepted": True,
                             "store_uuid": binding["store_uuid"], "store_path": binding["store_path"],
                             "watermark": seq, "result": dict(result, replayed=False)}
            and _v115_fixture.watermark(after) == seq)


with _v115_temp.TemporaryDirectory(prefix="v115-") as _v115_scratch:
    for _v115_index, _v115_mode in enumerate(_v115_modes):
        with _v115_fixture.Fixture(ROOT, _v115_Path(_v115_scratch) / str(_v115_index),
                                  runtime=globals().get("V115_RUNTIME")) as _v115_pair:
            _v115_a, _v115_b = _v115_pair.handles
            _v115_signed = _v115_pair.signer.sign(b"fixture unit control")
            _v115_units.append(_v115_pair.signer.verify(b"fixture unit control", _v115_signed)
                               and not _v115_pair.signer.verify(b"altered control", _v115_signed))
            _v115_controls.append(all(len(h.baseline["commands"]) == 1
                                      and len(h.baseline["entities"]) == 1
                                      and _v115_fixture.watermark(h.baseline) == 1
                                      for h in _v115_pair.handles)
                                  and _v115_a.binding["clone_uuid"] != _v115_b.binding["clone_uuid"]
                                  and _v115_a.binding["domain_uuid"] != _v115_b.binding["domain_uuid"])
            for _v115_direction in (0, 1):
                _v115_target = _v115_pair.handles[_v115_direction]
                _v115_peer = _v115_pair.handles[1 - _v115_direction]
                for _v115_route in sorted(_v115_routes):
                    _v115_a.start(_v115_b, _v115_mode)
                    _v115_b.start(_v115_a, _v115_mode)
                    for _v115_serving, _v115_other in ((_v115_a, _v115_b), (_v115_b, _v115_a)):
                        _v115_ready = _v115_serving.ready
                        _v115_controls.append(
                            _v115_ready["cwd"] == str((_v115_other if _v115_mode[0] else _v115_serving).workspace)
                            and _v115_ready["modules"] == str(
                                (_v115_other if _v115_mode[1] else _v115_serving).workspace / ".veldo")
                            and _v115_ready["environment_db"] == str(
                                (_v115_other if _v115_mode[2] else _v115_serving).path)
                            and _v115_ready["database"] == [[0, "main", str(_v115_serving.path)]]
                            and _v115_ready["binding"] == _v115_serving.binding
                            and _v115_ready["pid"] == _v115_serving.process.pid)
                    _v115_controls.append(_v115_a.process.pid != _v115_b.process.pid)
                    _v115_before = [h.snapshot() for h in _v115_pair.handles]
                    _v115_cmd = _v115_fixture.command(str((_v115_route, _v115_mode, _v115_direction)))
                    _v115_client = _v115_fixture.load(
                        _v115_Path(_v115_target.ready["modules"]) / "control_client.py")
                    _v115_cwd = _v115_os.getcwd()
                    _v115_env = _v115_os.environ.get("VELDO_CONTROL_DB")
                    try:
                        _v115_os.chdir(_v115_peer.workspace if _v115_mode[0] else _v115_target.workspace)
                        _v115_os.environ["VELDO_CONTROL_DB"] = str(
                            _v115_peer.path if _v115_mode[2] else _v115_target.path)
                        _v115_answer = getattr(_v115_client, _v115_route)(
                            _v115_target.workspace, _v115_cmd, _v115_pair.enrollment,
                            _v115_pair.signer.verify, _v115_pair.signer.sign, _v115_fixture.HOST)
                    finally:
                        _v115_os.chdir(_v115_cwd)
                        if _v115_env is None:
                            _v115_os.environ.pop("VELDO_CONTROL_DB", None)
                        else:
                            _v115_os.environ["VELDO_CONTROL_DB"] = _v115_env
                    _v115_after = [h.snapshot() for h in _v115_pair.handles]
                    _v115_ok = _v115_transaction(
                        _v115_before[_v115_direction], _v115_after[_v115_direction],
                        _v115_cmd, _v115_answer, _v115_target.binding, _v115_pair.signer)
                    _v115_unchanged = _v115_before[1 - _v115_direction] == _v115_after[1 - _v115_direction]
                    # A success response cannot turn an unchanged database into
                    # a transaction in the independent observer.
                    _v115_units.append(not _v115_transaction(
                        _v115_before[_v115_direction], _v115_before[_v115_direction],
                        _v115_cmd, _v115_answer, _v115_target.binding, _v115_pair.signer))
                    _v115_route_ok = (_v115_answer.get("store_uuid") == _v115_target.binding["store_uuid"]
                                     and _v115_answer.get("store_path") == str(_v115_target.path))
                    _v115_record = {"route": _v115_route, "ambient": _v115_mode,
                        "direction": _v115_direction, "command": _v115_cmd,
                        "authority": _v115_target.ready, "response": _v115_answer,
                        "before": _v115_before, "after": _v115_after,
                        "transaction": _v115_ok, "peer_unchanged": _v115_unchanged,
                        "committed_target_delta": len(_v115_after[_v115_direction]["commands"])
                            - len(_v115_before[_v115_direction]["commands"]),
                        "committed_peer_delta": len(_v115_after[1 - _v115_direction]["commands"])
                            - len(_v115_before[1 - _v115_direction]["commands"]),
                        "errors": ([] if _v115_route_ok else ["routing_mismatch"])
                                  + ([] if _v115_ok else ["store_not_changed"])
                                  + ([] if _v115_unchanged else ["unexpected_store_change"])}
                    _v115_records.append(_v115_record)
                    _v115_completed.add((_v115_route, _v115_mode, _v115_direction))
                    _v115_pair.close()
                    _v115_final = [h.snapshot() for h in _v115_pair.handles]
                    # Reopen after EACH acceptance, including its untouched peer.
                    _v115_reopened = _v115_transaction(
                        _v115_before[_v115_direction], _v115_final[_v115_direction],
                        _v115_cmd, _v115_answer, _v115_target.binding, _v115_pair.signer)
                    _v115_reopened = (_v115_reopened
                        and _v115_final[1 - _v115_direction] == _v115_before[1 - _v115_direction])
                    _v115_record["reopened"] = _v115_final
                    _v115_record["durable"] = _v115_reopened
                    if not _v115_reopened:
                        _v115_record["errors"].append("non_durable_acceptance")
                    _v115_reopens.append(_v115_reopened)
                    _v115_controls.append(_v115_final == _v115_after)

_v115_unique = all(len({r["command"][field] for r in _v115_records}) == len(_v115_records)
                   for field in ("command_id", "nonce"))
_v115_complete = (_v115_census and _v115_completed == _v115_expected
                  and _v115_unique and all(_v115_controls))
_v115_rows = {
    "ipc/configured-store-really-changes": _v115_complete and all(r["transaction"] for r in _v115_records),
    "ipc/only-the-bound-store-changes": _v115_complete and all(
        r["transaction"] and r["peer_unchanged"] for r in _v115_records),
    "ipc/accepted-state-survives-reopen": _v115_complete and all(_v115_reopens),
    "ipc/fixture-unit-controls": bool(_v115_units) and all(_v115_units),
}
for _v115_label, _v115_passed in _v115_rows.items():
    expect(_v115_label, _v115_passed)
if globals().get("V115_REPORT"):
    _v115_Path(V115_REPORT).write_text(_v115_json.dumps({
        "fixture_version": _v115_fixture.VERSION, "api": _v115_api,
        "census_matches": _v115_census, "expected_cases": len(_v115_expected),
        "completed_cases": len(_v115_completed), "rows": _v115_rows,
        "records": _v115_records}, indent=2, sort_keys=True) + "\n")
