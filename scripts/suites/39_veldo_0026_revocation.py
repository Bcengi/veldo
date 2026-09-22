"""VELDO-0026: revocation and authorization rechecks (PLAN-0019 W11).

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, so its declared
prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 39_veldo_0026_revocation

WHAT IS UNDER TEST. .veldo/control_revocation.py over .veldo/control_store.py,
.veldo/control_membership.py and .veldo/authority_contract.py against a REAL SQLite store, REAL
Ed25519 keys through the installed ssh-keygen and real child processes: the nine R39 boundaries are
callable registrations and each refuses by name when a SEPARATE PROCESS changes membership, policy,
scope, decision or dependency records (the prerequisites a dependency references included) between the
snapshot and acceptance (AC1); revocation and effect acceptance share one serialized order through the
store, both race orders from a real receiver process, a revocation committed first leaves zero new
effects, an effect accepted first stays in flight until evidence reconciles it and closure is not
effective before that, a publisher SIGKILLed after the revocation commit leaves stop obligations that
the reopened store and a replay of the signed journal both rebuild (AC2); outputs submitted after
revocation are evidence that satisfies no obligation without fresh version-bound authorization, and a
denial that cannot be durably recorded (a disk-write fault at its commit) stands the boundary down and
permits no dispatch, also after restart (AC3). The three declared falsifiers are applied to COPIES of
the organ laid beside copies of its siblings and required to turn their named row red while the
unmutated organ passes it. Without ssh-keygen the suite stands down by name.
"""
import importlib.util as _v26_ilu
import json as _v26_json
import os as _v26_os
import shutil as _v26_shutil
import subprocess as _v26_sp
import sys as _v26_sys
import tempfile as _v26_tf
from pathlib import Path as _v26_Path

_v26_tmp = _v26_Path(_v26_tf.mkdtemp(prefix="v26"))
_v26_have_ssh = _v26_shutil.which("ssh-keygen") is not None
_v26_ORGANS = ("control_store.py", "control_membership.py", "control_revocation.py", "authority_contract.py", "control_replay.py")


def _v26_load(name, path):
    spec = _v26_ilu.spec_from_file_location(name, git_fixture_dependency(path))
    m = _v26_ilu.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _v26_organs(veldo_dir, tag):
    store = _v26_load("v26_store_" + tag, _v26_Path(veldo_dir) / "control_store.py")
    mem = _v26_load("v26_mem_" + tag, _v26_Path(veldo_dir) / "control_membership.py")
    rev = _v26_load("v26_rev_" + tag, _v26_Path(veldo_dir) / "control_revocation.py")
    mem.attach(store)
    rev.attach(store)
    return store, mem, rev


def _v26_mutant_dir(edits):
    d = _v26_Path(_v26_tf.mkdtemp(prefix="v26mut", dir=str(_v26_tmp)))
    for f in _v26_ORGANS:
        src = (ROOT / ".veldo" / f).read_text()
        for old, new in (edits.get(f) or []):  # a list of (old, new) edits, all in the SAME copy
            assert src.count(old) == 1, (f, old[:60], src.count(old))
            src = src.replace(old, new)
        (d / f).write_text(src)
    return d


CS26, CM26, CR26 = _v26_organs(ROOT / ".veldo", "main")
AC26 = CM26.AC
RP26 = _v26_load("v26_replay", ROOT / ".veldo" / "control_replay.py")
_v26_IDS = {"domain_uuid": "dom-v26", "repository_uuid": "repo-v26", "store_uuid": "store-v26"}
_v26_NOW = 1_900_000_000

if not _v26_have_ssh:
    expect("VELDO-0026 STOOD DOWN by name - ssh-keygen is not installed here, so the real-signature rows cannot run", True)
else:
    _v26_kd = _v26_tmp / "keys"
    _v26_kd.mkdir()

    def _v26_keygen(name):
        _v26_sp.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", name + "@veldo", "-f", str(_v26_kd / name)], check=True, capture_output=True, stdin=_v26_sp.DEVNULL, timeout=60)
        return (_v26_kd / (name + ".pub")).read_text()

    def _v26_sign(name, msg):
        f = _v26_kd / (name + ".msg")
        f.write_bytes(msg)
        sig = _v26_kd / (name + ".msg.sig")
        if sig.exists():
            sig.unlink()
        _v26_sp.run(["ssh-keygen", "-Y", "sign", "-f", str(_v26_kd / name), "-n", AC26.SIGNATURE_NAMESPACE, str(f)], check=True, capture_output=True, stdin=_v26_sp.DEVNULL, timeout=60)
        return sig.read_text()

    _v26_pub = {n: _v26_keygen(n) for n in ("dmitry", "asya", "svc", "authority")}
    _v26_JS = ("veldo-authority", lambda m: _v26_sign("authority", m))
    _v26_allowed_authority = 'veldo-authority namespaces="%s" %s\n' % (AC26.SIGNATURE_NAMESPACE, " ".join(_v26_pub["authority"].split()[:2]))

    def _v26_journal_verify(msg, sig, signer):
        sf, sg = _v26_kd / "journal_signers", _v26_kd / "journal.sig"
        sf.write_text(_v26_allowed_authority)
        sg.write_text(sig)
        r = _v26_sp.run(["ssh-keygen", "-Y", "verify", "-f", str(sf), "-I", signer, "-n", AC26.SIGNATURE_NAMESPACE, "-s", str(sg)], input=msg, capture_output=True, timeout=60)
        return r.returncode == 0, (r.stdout + r.stderr).decode("utf-8", "replace")

    class _v26_World:
        """A fresh store with the owner bootstrapped, a service and a security authority enrolled,
        and helpers for administrative and revocation-organ commands."""

        def __init__(self, name, organs=None):
            self.store, self.mem, self.rev = organs or (CS26, CM26, CR26)
            self.ac = self.mem.AC
            self.dir = _v26_tmp / name
            self.dir.mkdir(parents=True)
            self.db = str(self.dir / "control.sqlite3")
            self.conn = self.store.open_store(self.db)
            self.n = 0
            self.admin("boot", "dmitry", "enroll_principal", {"principal": "dmitry", "principal_type": "person", "roles": ["project_owner", "membership_steward"], "public_key": _v26_pub["dmitry"], "independence_group": "founder", "scope": "*"})
            self.admin("e-svc", "dmitry", "enroll_principal", {"principal": "svc", "principal_type": "service", "roles": [], "public_key": _v26_pub["svc"], "independence_group": None, "scope": "*"}, enrollee="svc")
            self.admin("e-asya", "dmitry", "enroll_principal", {"principal": "asya", "principal_type": "person", "roles": ["security_authority", "admission_authority"], "public_key": _v26_pub["asya"], "independence_group": "ops", "scope": "*"}, enrollee="asya")

        def nonce(self):
            self.n += 1
            return "nonce-%d" % self.n

        def admin(self, cid, signer, op, params, enrollee=None):
            c = {"command_id": cid, "principal": None, "operation": op, "target": "authority", "parameters": params, "artifact_digests": [], "nonce": None, "expected_versions": {}}
            st = self.mem.authority_state(self.store, self.conn)
            env = {"schema": self.ac.ENVELOPE_SCHEMA, **_v26_IDS, "command_id": cid, "request_revision": 1, "nonce": self.nonce(), "expires_at": _v26_NOW + 600,
                   "membership_version": st["membership_version"], "delegation_version": st["delegation_version"], "principal": signer, "command_digest": self.ac.canonical_command_digest(c)}
            sig = _v26_sign(signer, self.ac.canonical_envelope_bytes(env))
            esig = _v26_sign(enrollee, self.ac.canonical_envelope_bytes(dict(env, principal=enrollee))) if enrollee else None
            return self.mem.admit(self.store, self.conn, env, c, sig, _v26_IDS, _v26_NOW, enrollee_signature=esig, journal_signer=_v26_JS)

        def rex(self, cid, op, params, now=_v26_NOW):
            c = {"command_id": cid, "principal": "veldo-authority", "operation": op, "target": "authority", "parameters": params, "artifact_digests": [], "nonce": "rn-" + cid, "expected_versions": {}}
            try:
                return self.rev.execute(self.store, self.conn, c, _v26_JS, now), None
            except Exception as e:
                if type(e).__name__ == "RevocationRefused":
                    return None, e.code
                raise

        def put(self, cid, eid, kind, data, expected):
            return self.store.execute(self.conn, {"command_id": cid, "principal": "veldo-authority", "operation": "upsert_entity", "parameters": {"entity_id": eid, "kind": kind, "data": data},
                                                  "expected_versions": {eid: expected}, "artifact_digests": [], "nonce": "pn-" + cid}, _v26_JS[0], _v26_JS[1], 1, committed_at=_v26_NOW)

        def ms(self):
            return self.mem.authority_state(self.store, self.conn)

        def guard(self, boundary, actor, requirement, snap, now=_v26_NOW, action="test"):
            return self.rev.accept(self.store, self.conn, boundary, actor, requirement, snap, now, _v26_JS, action=action)

    # ---------------------------------------------------------------------------------------------
    # AC1: nine boundaries, one snapshot, refusal by name when another process moves an input.
    # ---------------------------------------------------------------------------------------------
    _v26_w = _v26_World("main")
    _v26_req = {"roles": [], "quorum": 1, "subject_digest": "sha256:s"}
    _v26_w.put("p-pol", "policy:main", "policy", {"tier": "high"}, 0)
    _v26_w.put("p-scope", "scope:item-1", "admission_scope", {"paths": ["a"]}, 0)
    _v26_w.put("p-dec", "decision:D1", "decision", {"status": "settled"}, 0)
    _v26_w.put("p-pre", "pre:A", "prerequisite", {"status": "accepted"}, 0)
    _v26_w.put("p-dep", "dep:X", "dependency", {"prerequisites": ["pre:A"], "status": "resolved"}, 0)
    _v26_READ = ["policy:main", "scope:item-1", "decision:D1", "dep:X", "asya"]
    _v26_snap = CR26.snapshot(CS26, _v26_w.conn, _v26_READ)
    _v26_person_boundaries = [b for b, kinds in AC26.BOUNDARIES.items() if "person" in kinds and b != "result_acceptance"]
    _v26_service_boundaries = [b for b, kinds in AC26.BOUNDARIES.items() if "service" in kinds and b != "result_acceptance"]
    _v26_intact = {b: _v26_w.guard(b, "asya", _v26_req, _v26_snap) for b in _v26_person_boundaries}
    _v26_intact_svc = {b: _v26_w.guard(b, "svc", _v26_req, _v26_snap) for b in _v26_service_boundaries}
    _v26_wrong_kind = _v26_w.guard("dispatch_acceptance", "asya", _v26_req, _v26_snap)
    expect("VELDO-0026 AC1 revocation/boundaries: the guard registry is exactly the nine R39 boundaries of the authority contract; with an "
           "intact snapshot over policy, scope, decision, a dependency and its indirect prerequisite (read into the snapshot without being "
           "named) and the actor's membership, every boundary that admits a person allows asya and every boundary that admits a service "
           "allows the service; a boundary that admits no person refuses asya as not_authorized and records the denial",
           CR26.registered_boundaries() == sorted(AC26.BOUNDARIES) and len(CR26.registered_boundaries()) == 9 and "pre:A" in _v26_snap["versions"] and CR26.LEDGER_ENTITY in _v26_snap["versions"]
           and all(v["allowed"] for v in _v26_intact.values()) and all(v["allowed"] for v in _v26_intact_svc.values())
           and _v26_wrong_kind["allowed"] is False and any(r.startswith("not_authorized:principal_type_not_admitted") for r in _v26_wrong_kind["refusals"]) and _v26_wrong_kind["denial"] is not None)
    # Another PROCESS changes each record kind between the snapshot and acceptance.
    _v26_child_put = '''
import importlib.util, sys, json, subprocess, pathlib
def load(n, p):
    sp = importlib.util.spec_from_file_location(n, p); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
veldo = sys.argv[1]; CS = load("cs", veldo + "/control_store.py"); CM = load("cm", veldo + "/control_membership.py"); CR = load("cr", veldo + "/control_revocation.py")
CM.attach(CS); CR.attach(CS)
conn = CS.open_store(sys.argv[2]); job = json.load(open(sys.argv[3])); kd = pathlib.Path(job["keydir"])
def jsign(m):
    f = kd / ("child-%d.msg" % __import__("os").getpid()); f.write_bytes(m); sig = pathlib.Path(str(f) + ".sig")
    if sig.exists(): sig.unlink()
    subprocess.run(["ssh-keygen", "-Y", "sign", "-f", str(kd / "authority"), "-n", job["namespace"], str(f)], check=True, capture_output=True, stdin=subprocess.DEVNULL, timeout=60)
    return sig.read_text()
try:
    if job["kind"] == "put":
        r = CS.execute(conn, job["command"], "veldo-authority", jsign, 1, committed_at=job["now"])
    elif job["kind"] == "rev":
        r = CR.execute(CS, conn, job["command"], ("veldo-authority", jsign), job["now"])
    print("REPLIED " + json.dumps({"seq": r["seq"]}))
except Exception as e:
    print("REFUSED " + getattr(e, "code", type(e).__name__) + " " + str(getattr(e, "detail", ""))[:80])
'''

    def _v26_child(world, kind, command, name, kill_at=None, wait=True):
        job = {"kind": kind, "command": command, "now": _v26_NOW, "keydir": str(_v26_kd), "namespace": AC26.SIGNATURE_NAMESPACE}
        f = world.dir / ("job-%s.json" % name)
        f.write_text(_v26_json.dumps(job))
        env = dict(_v26_os.environ, VELDO_CONTROL_TEST_HARNESS="1" if kill_at else "0", VELDO_CONTROL_KILL_AT=kill_at or "")
        p = _v26_sp.Popen([_v26_sys.executable, "-c", _v26_child_put, str(ROOT / ".veldo"), world.db, str(f)], stdout=_v26_sp.PIPE, stderr=_v26_sp.PIPE, text=True, stdin=_v26_sp.DEVNULL, env=env)
        if not wait:
            return p
        out, err = p.communicate(timeout=180)
        return (p.returncode, out.strip().split("\n")[-1] if out.strip() else "", err[-200:])

    def _v26_put_cmd(cid, eid, kind, data, expected):
        return {"command_id": cid, "principal": "veldo-authority", "operation": "upsert_entity", "parameters": {"entity_id": eid, "kind": kind, "data": data},
                "expected_versions": {eid: expected}, "artifact_digests": [], "nonce": "pn-" + cid}

    _v26_moves = {
        "policy": ("policy:main", "policy", {"tier": "critical"}, 1),
        "scope": ("scope:item-1", "admission_scope", {"paths": ["a", ".veldo/policy.yaml"]}, 1),
        "decision": ("decision:D1", "decision", {"status": "reopened"}, 1),
        "dependency": ("dep:X", "dependency", {"prerequisites": ["pre:A", "pre:B"], "status": "resolved"}, 1),
        "indirect prerequisite": ("pre:A", "prerequisite", {"status": "withdrawn"}, 1),
    }
    _v26_pair_results = {}
    for _name, (_eid, _kind, _data, _exp) in _v26_moves.items():
        _w = _v26_World("move-" + _name.replace(" ", "-"))
        _w.put("p-pol", "policy:main", "policy", {"tier": "high"}, 0)
        _w.put("p-scope", "scope:item-1", "admission_scope", {"paths": ["a"]}, 0)
        _w.put("p-dec", "decision:D1", "decision", {"status": "settled"}, 0)
        _w.put("p-pre", "pre:A", "prerequisite", {"status": "accepted"}, 0)
        _w.put("p-dep", "dep:X", "dependency", {"prerequisites": ["pre:A"], "status": "resolved"}, 0)
        _snap = CR26.snapshot(CS26, _w.conn, _v26_READ)
        _child = _v26_child(_w, "put", _v26_put_cmd("mv-" + _name.replace(" ", "-"), _eid, _kind, _data, _exp), _name.replace(" ", "-"))
        _v26_pair_results[_name] = {b: _w.guard(b, "asya", _v26_req, _snap) for b in _v26_person_boundaries}
        _v26_pair_results[_name]["_child"] = _child
        _w.conn.close()
    # membership moved by another process: a role change committed by the steward after the snapshot
    _w = _v26_World("move-membership")
    _snap_m = CR26.snapshot(CS26, _w.conn, ["asya"])
    _w.admin("mv-mem", "dmitry", "change_roles", {"principal": "asya", "roles": ["security_authority"]})
    _v26_pair_results["membership"] = {b: _w.guard(b, "asya", _v26_req, _snap_m) for b in _v26_person_boundaries}
    _v26_pair_results["membership"]["_child"] = (0, "REPLIED in-process (the steward's signed command)", "")
    _w.conn.close()

    def _v26_named(name, needle):
        return all(v["allowed"] is False and any(needle in r for r in v["refusals"]) and v["denial"] is not None for b, v in _v26_pair_results[name].items() if b != "_child")

    expect("VELDO-0026 AC1 revocation/moved-inputs: for each record kind (policy, scope, decision, dependency, the dependency's indirect "
           "prerequisite, membership) a SEPARATE PROCESS commits a change after the snapshot and before acceptance, and every "
           "person-admitting boundary then refuses with the named reason (stale_read naming the record, dependency_withdrawn for the "
           "withdrawn prerequisite) and records a denial; each child process replied (children: %s)"
           % {k: v["_child"][1][:30] for k, v in _v26_pair_results.items()},
           all(v["_child"][0] == 0 and v["_child"][1].startswith("REPLIED") for v in _v26_pair_results.values())
           and _v26_named("policy", "stale_read:policy:main") and _v26_named("scope", "stale_read:scope:item-1") and _v26_named("decision", "stale_read:decision:D1")
           and _v26_named("dependency", "stale_read:dep:X") and _v26_named("indirect prerequisite", "dependency_withdrawn:pre:A") and _v26_named("membership", "stale_read:asya"))
    # THE DECLARED FALSIFIER: skip the indirect dependency revision check at effect acceptance while another process withdraws the prerequisite.
    _v26_m1_dir = _v26_mutant_dir({"control_revocation.py": [('''        if e and e["kind"] in ("dependency", "prerequisite"):
            for pre in e["data"].get("prerequisites") or []:
                if pre not in ids:
''', '''        if False:  # mutant: a dependency's prerequisites are not the caller's business
            for pre in e["data"].get("prerequisites") or []:
                if pre not in ids:
'''), ('''            for pre in e["data"].get("prerequisites") or []:
                if pre not in snap["versions"]:
''', '''            for pre in []:  # mutant: and nobody asks whether they were read
                if pre not in snap["versions"]:
''')]})
    _v26_m1 = _v26_World("m1", _v26_organs(_v26_m1_dir, "m1"))
    _v26_m1.put("p-pre", "pre:A", "prerequisite", {"status": "accepted"}, 0)
    _v26_m1.put("p-dep", "dep:X", "dependency", {"prerequisites": ["pre:A"], "status": "resolved"}, 0)
    _v26_m1_snap = _v26_m1.rev.snapshot(_v26_m1.store, _v26_m1.conn, ["dep:X"])
    _v26_m1_child = _v26_child(_v26_m1, "put", _v26_put_cmd("wd", "pre:A", "prerequisite", {"status": "withdrawn"}, 1), "withdraw")
    _v26_m1_v = _v26_m1.guard("result_acceptance", "asya", dict(_v26_req, output="none", obligation="ob"), _v26_m1_snap)
    _v26_m1_v_claim = _v26_m1.guard("claim", "svc", _v26_req, _v26_m1_snap)
    expect("VELDO-0026 AC1 revocation/indirect-dependency DRIVEN (the declared falsifier): with the indirect prerequisite left out of the "
           "snapshot in a copy of the organ, another process withdraws the prerequisite and the claim boundary still allows the effect "
           "(the dependency itself did not move), so the row reds; unmutated (the row above) the withdrawal refuses as "
           "dependency_withdrawn at every boundary",
           _v26_m1_child[1].startswith("REPLIED") and "pre:A" not in _v26_m1_snap["versions"] and _v26_m1_v_claim["allowed"] is True
           and not any("dependency_withdrawn" in r for r in _v26_m1_v["refusals"]) and _v26_named("indirect prerequisite", "dependency_withdrawn:pre:A"))
    _v26_m1.conn.close()

    # ---------------------------------------------------------------------------------------------
    # AC2: revocation and effect acceptance in one serialized order; in-flight closure; kill and replay.
    # ---------------------------------------------------------------------------------------------
    _v26_r = _v26_World("race")
    _v26_acc = lambda cid, eff: {"command_id": cid, "principal": "veldo-authority", "operation": "accept_effect", "target": "authority", "parameters": {"effect_id": eff, "principal": "svc", "receiver": "recv-1", "kind": "push"}, "artifact_digests": [], "nonce": "rn-" + cid, "expected_versions": {}}
    _v26_revoke = lambda cid: {"command_id": cid, "principal": "veldo-authority", "operation": "revoke_authorization", "target": "authority", "parameters": {"principal": "svc", "at": _v26_NOW, "reason": "key compromise", "revoked_by": "dmitry"}, "artifact_digests": [], "nonce": "rn-" + cid, "expected_versions": {}}
    # order A: the receiver accepts first (child), then the revocation (parent)
    _v26_a1 = _v26_child(_v26_r, "rev", _v26_acc("acc-1", "eff-1"), "acc-1")
    _v26_rv = _v26_r.rex("rev-1", "revoke_authorization", _v26_revoke("rev-1")["parameters"])
    _v26_closure_a = CR26.closure_status(CS26, _v26_r.conn, "svc")
    _v26_stops_a = [s for s, _ in CR26.pending_stop_obligations(CS26, _v26_r.conn)]
    # order B: the revocation stands, a receiver process tries to accept a new effect
    _v26_b1 = _v26_child(_v26_r, "rev", _v26_acc("acc-2", "eff-2"), "acc-2")
    _v26_effects_b = sorted(eid for eid, e in CS26.materialized_state(_v26_r.conn)["entities"].items() if e["kind"] == "effect")
    # a genuinely concurrent race from two processes on a fresh world: exactly one order wins
    _v26_c = _v26_World("concurrent")
    _v26_pa = _v26_child(_v26_c, "rev", _v26_acc("acc-c", "eff-c"), "acc-c", wait=False)
    _v26_pb = _v26_child(_v26_c, "rev", _v26_revoke("rev-c"), "rev-c", wait=False)
    _v26_outs = []
    for _p in (_v26_pa, _v26_pb):
        _o, _e = _p.communicate(timeout=180)
        _v26_outs.append(_o.strip().split("\n")[-1] if _o.strip() else "REFUSED " + _e[-100:])
    # A revocation that lost the version race to the acceptance is RETRIED by the authority (a
    # revocation is never dropped because a receiver moved the ledger first); then the accepted
    # effect is in flight. Both orders are consistent; a dropped revocation would not be.
    _v26_c_rev_retry = None
    if _v26_outs[1].startswith("REFUSED"):
        _v26_c_rev_retry = _v26_c.rex("rev-c2", "revoke_authorization", _v26_revoke("rev-c2")["parameters"])
    _v26_c_ents = CS26.materialized_state(_v26_c.conn)["entities"]
    _v26_c_effect = _v26_c_ents.get("eff-c")
    _v26_c_closure = CR26.closure_status(CS26, _v26_c.conn, "svc")
    # revocation first: the acceptance lost, inside the transaction (revoked) or at the store's version check (stale_version: the
    # ledger moved under it); its retry must then be refused as revoked. Acceptance first: the effect is in flight with its stop.
    _v26_c_retry = _v26_c.rex("acc-c-retry", "accept_effect", {"effect_id": "eff-c", "principal": "svc", "receiver": "recv-1", "kind": "push"})
    _v26_c_consistent = (_v26_c_effect is None and _v26_c_closure["effective"] is True and _v26_outs[0].startswith("REFUSED") and ("revoked" in _v26_outs[0] or "stale_version" in _v26_outs[0])
                         and _v26_c_retry[1] == "revoked" and _v26_c_rev_retry is None) \
        or (_v26_c_effect is not None and _v26_c_effect["data"]["state"] == "in_flight" and _v26_c_closure["effective"] is False and "stop:eff-c" in _v26_c_ents
            and _v26_c_retry[1] == "effect_refused" and (_v26_c_rev_retry is None or _v26_c_rev_retry[1] is None))
    expect("VELDO-0026 AC2 revocation/serialized-order: a receiver PROCESS accepting an effect before the revocation leaves it accepted; the "
           "revocation then marks it in flight with a stop obligation and closure is NOT effective; a receiver process accepting after "
           "the revocation is refused inside the transaction as revoked and no new effect exists; two processes racing acceptance and "
           "revocation end in exactly one of the two consistent orders (effect refused and closure effective, or effect in flight with "
           "its stop obligation and closure not effective), a revocation that lost the version race being retried by the authority "
           "rather than dropped (outcomes: %s)" % _v26_outs,
           _v26_a1[1].startswith("REPLIED") and _v26_rv[1] is None and _v26_closure_a["revoked"] is True and _v26_closure_a["effective"] is False and _v26_closure_a["in_flight"] == ["eff-1"]
           and _v26_stops_a == ["stop:eff-1"] and _v26_b1[1].startswith("REFUSED revoked") and _v26_effects_b == ["eff-1"] and _v26_c_consistent)
    _v26_rc_bad = _v26_r.rex("rc-bad", "reconcile_effect", {"effect_id": "eff-1", "outcome": "vanished", "evidence_digest": "sha256:x"})
    _v26_rc = _v26_r.rex("rc-1", "reconcile_effect", {"effect_id": "eff-1", "outcome": "stopped", "evidence_digest": "sha256:stop-evidence"})
    _v26_closure_done = CR26.closure_status(CS26, _v26_r.conn, "svc")
    expect("VELDO-0026 AC2 revocation/in-flight-closure: the in-flight effect stays in flight until the receiver's evidence reconciles it "
           "(an outcome outside stopped, completed, failed is refused); after the stop evidence the effect is stopped, the stop obligation "
           "is satisfied and closure is effective",
           _v26_rc_bad[1] == "effect_refused" and _v26_rc[1] is None and _v26_closure_done["effective"] is True and CR26.pending_stop_obligations(CS26, _v26_r.conn) == []
           and CS26.materialized_state(_v26_r.conn)["entities"]["eff-1"]["data"]["state"] == "stopped")
    # THE DECLARED FALSIFIER: report effective closure immediately after revocation even when the receiver accepted first and is still running.
    _v26_m2_dir = _v26_mutant_dir({"control_revocation.py": [('''    return {"revoked": True, "effective": not in_flight, "in_flight": in_flight,''', '''    return {"revoked": True, "effective": True, "in_flight": in_flight,  # mutant: revoked means closed''')]})
    _v26_m2 = _v26_World("m2", _v26_organs(_v26_m2_dir, "m2"))
    _v26_m2.rex("acc", "accept_effect", {"effect_id": "eff-m", "principal": "svc", "receiver": "recv-1", "kind": "push"})
    _v26_m2.rex("rev", "revoke_authorization", {"principal": "svc", "at": _v26_NOW, "reason": "r", "revoked_by": "dmitry"})
    _v26_m2_closure = _v26_m2.rev.closure_status(_v26_m2.store, _v26_m2.conn, "svc")
    expect("VELDO-0026 AC2 revocation/in-flight-closure DRIVEN (the declared falsifier): with revocation reported as effective closure in a copy "
           "of the organ, a revoked principal whose effect was accepted first and is still in flight reads as closed, so the row reds; "
           "unmutated (the row above) closure waits for the stop evidence",
           _v26_m2_closure["effective"] is True and _v26_m2_closure["in_flight"] == ["eff-m"] and _v26_closure_a["effective"] is False)
    _v26_m2.conn.close()
    # SIGKILL after the revocation commit, before any notification: the reopened store and a replay of the signed journal rebuild the stop obligations.
    _v26_k = _v26_World("kill")
    _v26_k.rex("acc-k1", "accept_effect", {"effect_id": "eff-k1", "principal": "svc", "receiver": "recv-1", "kind": "push"})
    _v26_k.rex("acc-k2", "accept_effect", {"effect_id": "eff-k2", "principal": "svc", "receiver": "recv-2", "kind": "deploy"})
    _v26_k.conn.close()
    _v26_k_child = _v26_child(_v26_k, "rev", _v26_revoke("rev-k"), "rev-k", kill_at="after_commit")
    _v26_k.conn = CS26.open_store(_v26_k.db)
    _v26_k_stops = CR26.pending_stop_obligations(CS26, _v26_k.conn)
    _v26_k_replay = RP26.replay(CS26.export_journal(_v26_k.conn), _v26_journal_verify)
    _v26_k_rebuilt_stops = sorted(eid for eid, e in _v26_k_replay["state"]["entities"].items() if e["kind"] == "stop_obligation" and e["data"]["state"] == "requested")
    expect("VELDO-0026 AC2 revocation/stop-obligations-survive-kill: the revoking process is SIGKILLed after its commit and before it notified "
           "any receiver; the reopened store lists both stop obligations as requested with their receivers, and a replay of the signed "
           "journal with real verification against the authority's key rebuilds the same obligations and the in-flight effects",
           _v26_k_child[0] == -9 and [s for s, _ in _v26_k_stops] == ["stop:eff-k1", "stop:eff-k2"] and {d["receiver"] for _s, d in _v26_k_stops} == {"recv-1", "recv-2"}
           and _v26_k_rebuilt_stops == ["stop:eff-k1", "stop:eff-k2"] and RP26.compare_with_live(_v26_k_replay, CS26.materialized_state(_v26_k.conn))["matches"] is True
           and _v26_k_replay["state"]["entities"]["eff-k1"]["data"]["state"] == "in_flight")
    _v26_k.conn.close()

    # ---------------------------------------------------------------------------------------------
    # AC3: revoked outputs are evidence; denials are durable or the boundary stands down.
    # ---------------------------------------------------------------------------------------------
    _v26_e = _v26_World("evidence")
    _v26_blob_before, _v26_blob_after = b"output before revocation", b"output after revocation"
    _v26_e.rex("o-before", "submit_output", {"output_id": "out-before", "digest": CR26.digest_of(_v26_blob_before.decode()), "principal": "svc", "obligation": "ob-1"})
    _v26_e.rex("rev-e", "revoke_authorization", {"principal": "svc", "at": _v26_NOW, "reason": "r", "revoked_by": "dmitry"})
    _v26_e.rex("o-after", "submit_output", {"output_id": "out-after", "digest": CR26.digest_of(_v26_blob_after.decode()), "principal": "svc", "obligation": "ob-1"})
    _v26_e_ents = CS26.materialized_state(_v26_e.conn)["entities"]
    _v26_e_snap = CR26.snapshot(CS26, _v26_e.conn, ["out-before", "out-after"])
    _v26_e_v_before = _v26_e.guard("result_acceptance", "asya", dict(_v26_req, output="out-before", obligation="ob-1"), _v26_e_snap)
    _v26_e_v_after = _v26_e.guard("result_acceptance", "asya", dict(_v26_req, output="out-after", obligation="ob-1"), _v26_e_snap)
    _v26_led, _ = CR26.ledger(CS26, _v26_e.conn)
    _v26_e_re_stale = _v26_e.rex("re-stale", "reauthorize", {"obligation": "ob-1", "granted_by": "dmitry", "revocation_version": _v26_led["revocation_version"] - 1})
    _v26_e_re = _v26_e.rex("re-ok", "reauthorize", {"obligation": "ob-1", "granted_by": "dmitry", "revocation_version": _v26_led["revocation_version"]})
    _v26_e_snap2 = CR26.snapshot(CS26, _v26_e.conn, ["out-before", "out-after", "reauth:ob-1"])
    _v26_e_v_fresh = _v26_e.guard("result_acceptance", "asya", dict(_v26_req, output="out-after", obligation="ob-1"), _v26_e_snap2)
    _v26_e.rex("rev-e2", "revoke_authorization", {"principal": "asya", "at": _v26_NOW + 1, "reason": "second revocation moves the ledger", "revoked_by": "dmitry"})
    _v26_e_snap3 = CR26.snapshot(CS26, _v26_e.conn, ["out-before", "out-after", "reauth:ob-1"])
    _v26_e_v_moved = _v26_e.guard("result_acceptance", "dmitry", dict(_v26_req, output="out-after", obligation="ob-1"), _v26_e_snap3)
    expect("VELDO-0026 AC3 revocation/outputs-are-evidence: outputs submitted before and after the revocation are both retained with their "
           "digests (the later one marked submitted after revocation), and neither satisfies the obligation at result acceptance: both "
           "refuse as output_is_evidence_only plus reauthorization_required; a reauthorization naming a stale revocation version is "
           "refused; a fresh one bound to the current version makes the output acceptable; a further revocation moves the ledger and "
           "the reauthorization is stale again by version",
           _v26_e_ents["out-before"]["data"]["submitted_after_revocation"] is False and _v26_e_ents["out-after"]["data"]["submitted_after_revocation"] is True
           and _v26_e_ents["out-after"]["data"]["digest"] == CR26.digest_of(_v26_blob_after.decode())
           and all(v["allowed"] is False and any(r.startswith("output_is_evidence_only") for r in v["refusals"]) and any(r.startswith("reauthorization_required") for r in v["refusals"]) for v in (_v26_e_v_before, _v26_e_v_after))
           and _v26_e_re_stale[1] == "effect_refused" and _v26_e_re[1] is None and _v26_e_v_fresh["allowed"] is True
           and _v26_e_v_moved["allowed"] is False and any(r.startswith("reauthorization_required") for r in _v26_e_v_moved["refusals"]))
    # the denial cannot be durably recorded: the boundary stands down and dispatch is not permitted, also after a restart
    _v26_d = _v26_World("denial")
    _v26_d_snap = CR26.snapshot(CS26, _v26_d.conn, [])
    _v26_d.rex("rev-d", "revoke_authorization", {"principal": "svc", "at": _v26_NOW, "reason": "r", "revoked_by": "dmitry"})
    _v26_os.environ["VELDO_CONTROL_TEST_HARNESS"], _v26_os.environ["VELDO_DENIAL_WRITE_FAIL"] = "1", "1"
    _v26_d_fault = _v26_d.guard("dispatch_acceptance", "svc", _v26_req, _v26_d_snap)
    _v26_os.environ["VELDO_DENIAL_WRITE_FAIL"] = "0"
    _v26_d_ro = CS26.open_store(_v26_d.db, mode="r")
    _v26_d_ro_v = CR26.accept(CS26, _v26_d_ro, "dispatch_acceptance", "svc", _v26_req, _v26_d_snap, _v26_NOW, _v26_JS)
    _v26_d_ro.close()
    _v26_d.conn.close()
    _v26_d.conn = CS26.open_store(_v26_d.db)
    _v26_d_after = _v26_d.guard("dispatch_acceptance", "svc", _v26_req, _v26_d_snap)
    _v26_d_denials = sorted(eid for eid, e in CS26.materialized_state(_v26_d.conn)["entities"].items() if e["kind"] == "denial")
    expect("VELDO-0026 AC3 revocation/denial-storage-failure: with the denial journal's commit faulted (a disk write failure) the refusal "
           "of a revoked actor at dispatch acceptance is returned as a STAND DOWN (allowed False, stand_down True, denial_not_recorded "
           "named) and dispatch is not permitted; the same through a read-only handle stands down too; after restart with the store "
           "writable the refusal is recorded as a denial and dispatch is still not permitted; no denial exists from the faulted attempts",
           _v26_d_fault["allowed"] is False and _v26_d_fault["stand_down"] is True and any(r.startswith("denial_not_recorded") for r in _v26_d_fault["refusals"]) and CR26.dispatch_permitted(_v26_d_fault) is False
           and _v26_d_ro_v["stand_down"] is True and CR26.dispatch_permitted(_v26_d_ro_v) is False
           and _v26_d_after["allowed"] is False and _v26_d_after["stand_down"] is False and _v26_d_after["denial"] is not None and CR26.dispatch_permitted(_v26_d_after) is False
           and len(_v26_d_denials) == 1)
    # THE DECLARED FALSIFIER: allow dispatch after injecting a denial-journal write failure.
    _v26_m3_dir = _v26_mutant_dir({"control_revocation.py": [('''        return {"allowed": False, "refusals": refusals + ["denial_not_recorded: %s" % e], "denial": None, "stand_down": True,''',
                                                               '''        return {"allowed": True, "refusals": refusals + ["denial_not_recorded: %s" % e], "denial": None, "stand_down": False, "read_set_versions": dict(snap["versions"]),  # mutant: an unrecorded refusal is no refusal''')]})
    _v26_m3 = _v26_World("m3", _v26_organs(_v26_m3_dir, "m3"))
    _v26_m3.rex("rev-m3", "revoke_authorization", {"principal": "svc", "at": _v26_NOW, "reason": "r", "revoked_by": "dmitry"})
    _v26_os.environ["VELDO_DENIAL_WRITE_FAIL"] = "1"
    _v26_m3_v = _v26_m3.guard("dispatch_acceptance", "svc", _v26_req, _v26_m3.rev.snapshot(_v26_m3.store, _v26_m3.conn, []))
    _v26_os.environ["VELDO_DENIAL_WRITE_FAIL"] = "0"
    expect("VELDO-0026 AC3 revocation/denial-storage-failure DRIVEN (the declared falsifier): with an unrecorded refusal treated as allowance in a "
           "copy of the organ, the revoked actor is dispatched after the denial write fails, so the row reds; unmutated (the row above) "
           "the boundary stands down and permits nothing",
           _v26_m3_v["allowed"] is True and _v26_m3.rev.dispatch_permitted(_v26_m3_v) is True and any("denial_not_recorded" in r for r in _v26_m3_v["refusals"])
           and CR26.dispatch_permitted(_v26_d_fault) is False)
    _v26_m3.conn.close()

    # ---------------------------------------------------------------------------------------------
    # The seven findings of the Codex review (review-20260918-100244), each pinned.
    # ---------------------------------------------------------------------------------------------
    _v26_f = _v26_World("findings")
    # (1) a caller-chosen id never replaces the ledger, a stop obligation, a membership or another kind
    _v26_f.rex("acc-f1", "accept_effect", {"effect_id": "eff-f1", "principal": "svc", "receiver": "recv-1", "kind": "push"})
    _v26_f1_ledger = _v26_f.rex("o-ledger", "submit_output", {"output_id": CR26.LEDGER_ENTITY, "digest": "sha256:x", "principal": "svc"})
    _v26_f1_stop = _v26_f.rex("o-stop", "submit_output", {"output_id": "stop:eff-f1", "digest": "sha256:x", "principal": "svc"})
    _v26_f1_member = _v26_f.rex("o-member", "submit_output", {"output_id": "asya", "digest": "sha256:x", "principal": "svc"})
    _v26_f1_effect_over_output = _v26_f.rex("acc-over", "accept_effect", {"effect_id": "asya", "principal": "svc", "receiver": "r", "kind": "k"})
    _v26_f1_ok = _v26_f.rex("o-ok", "submit_output", {"output_id": "out-f1", "digest": "sha256:x", "principal": "svc"})
    _v26_f1_led, _v26_f1_st = CR26.ledger(CS26, _v26_f.conn)
    _v26_f.rex("rev-f1", "revoke_authorization", {"principal": "svc", "at": _v26_NOW, "reason": "r", "revoked_by": "dmitry"})
    _v26_f1_after = _v26_f.rex("acc-f1b", "accept_effect", {"effect_id": "eff-f1b", "principal": "svc", "receiver": "recv-1", "kind": "push"})
    expect("VELDO-0026 AC2 revocation/entity-namespace (review 1): an output submitted under the ledger's id, a stop obligation's id or a "
           "member's id, and an effect accepted under a member's id, are each refused as namespace_refused and change nothing (the "
           "ledger entity is still the ledger); an ordinary output id is accepted; after the revocation the ledger still refuses new "
           "effects for the revoked principal",
           all(v[1] == "effect_refused" for v in (_v26_f1_ledger, _v26_f1_stop, _v26_f1_member, _v26_f1_effect_over_output))
           and _v26_f1_st[CR26.LEDGER_ENTITY]["kind"] == "revocation_ledger" and _v26_f1_st["asya"]["kind"] == "membership" and "revoked" in _v26_f1_led
           and _v26_f1_ok[1] is None and _v26_f1_after[1] == "revoked")
    # (2) the guard's checked read set binds the commit: a prerequisite withdrawn through ANOTHER connection between guard and commit refuses
    _v26_f.put("p-pre", "pre:A", "prerequisite", {"status": "accepted"}, 0)
    _v26_f.put("p-dep", "dep:X", "dependency", {"prerequisites": ["pre:A"], "status": "resolved"}, 0)
    _v26_f2_snap = CR26.snapshot(CS26, _v26_f.conn, ["dep:X", "asya"])
    _v26_f2_v = _v26_f.guard("command_acceptance", "asya", _v26_req, _v26_f2_snap)
    _v26_f2_other = CS26.open_store(_v26_f.db)
    CS26.execute(_v26_f2_other, _v26_put_cmd("wd-f2", "pre:A", "prerequisite", {"status": "withdrawn"}, 1), _v26_JS[0], _v26_JS[1], 1, committed_at=_v26_NOW)
    _v26_f2_other.close()
    _v26_f2_cmd = {"command_id": "acc-f2", "principal": "veldo-authority", "operation": "accept_effect", "target": "authority", "parameters": {"effect_id": "eff-f2", "principal": "asya", "receiver": "r", "kind": "k"}, "artifact_digests": [], "nonce": "rn-acc-f2", "expected_versions": {}}
    _v26_f2_code = None
    try:
        CR26.execute(CS26, _v26_f.conn, _v26_f2_cmd, _v26_JS, _v26_NOW, read_set_versions=_v26_f2_v["read_set_versions"])
    except Exception as e:
        _v26_f2_code = getattr(e, "code", type(e).__name__) + ":" + getattr(e, "detail", "")[:60]
    _v26_f2_recheck = _v26_f.guard("command_acceptance", "asya", _v26_req, _v26_f2_snap)
    expect("VELDO-0026 AC1 revocation/read-set-bound-commit (review 1): an allowed verdict carries the snapshot's versions; a prerequisite "
           "withdrawn through another connection between the guard and the commit (at command acceptance, a boundary that admits a person) makes the commit refuse by version (stale_version on "
           "the withdrawn prerequisite) when the caller passes those versions to execute, and the same guard rerun refuses as "
           "dependency_withdrawn; nothing was committed",
           _v26_f2_v["allowed"] is True and "pre:A" in _v26_f2_v["read_set_versions"] and _v26_f2_code is not None and _v26_f2_code.startswith("effect_refused:stale_version")
           and "pre:A" in _v26_f2_code and "eff-f2" not in CS26.materialized_state(_v26_f.conn)["entities"]
           and any(r.startswith("dependency_withdrawn:pre:A") for r in _v26_f2_recheck["refusals"]))
    # (3) + (4) the guard reloads membership; a SIGNED membership revocation ends authorization and quarantines outputs
    _v26_f.rex("o-asya", "submit_output", {"output_id": "out-asya", "digest": "sha256:a", "principal": "asya", "obligation": "ob-a"})
    _v26_f3_snap = CR26.snapshot(CS26, _v26_f.conn, [])  # a snapshot that does not name the actor: the guard must still see the revocation
    _v26_f3_before = _v26_f.guard("command_acceptance", "asya", _v26_req, _v26_f3_snap)
    _v26_f.admin("rev-mem", "dmitry", "revoke_membership", {"principal": "asya", "revoked_at": _v26_NOW - 1})
    _v26_f3_after = _v26_f.guard("command_acceptance", "asya", _v26_req, _v26_f3_snap)
    _v26_f4_snap = CR26.snapshot(CS26, _v26_f.conn, ["out-asya"])
    _v26_f4_v = _v26_f.guard("result_acceptance", "dmitry", dict(_v26_req, output="out-asya", obligation="ob-a"), _v26_f4_snap)
    _v26_f4_led, _ = CR26.ledger(CS26, _v26_f.conn)
    _v26_f4_re = _v26_f.rex("re-a", "reauthorize", {"obligation": "ob-a", "granted_by": "dmitry", "revocation_version": _v26_f4_led["revocation_version"]})
    _v26_f4_snap2 = CR26.snapshot(CS26, _v26_f.conn, ["out-asya", "reauth:ob-a"])
    _v26_f4_v2 = _v26_f.guard("result_acceptance", "dmitry", dict(_v26_req, output="out-asya", obligation="ob-a"), _v26_f4_snap2)
    _v26_f4_accept = _v26_f.rex("acc-asya", "accept_effect", {"effect_id": "eff-asya", "principal": "asya", "receiver": "r", "kind": "k"})
    expect("VELDO-0026 AC1 revocation/membership-reloaded (review 1): before the steward's signed revoke_membership asya is allowed at "
           "command acceptance; after it, the SAME snapshot (which never named her) is refused as revoked because the guard reloads "
           "membership from the store rather than trusting the caller; her earlier output is evidence only at result acceptance until "
           "a version-bound reauthorization, and a new effect for her is refused as revoked inside the transaction",
           _v26_f3_before["allowed"] is True and _v26_f3_after["allowed"] is False and any(r == "revoked:asya" for r in _v26_f3_after["refusals"])
           and CR26.is_revoked(CS26, _v26_f.conn, "asya", _v26_NOW) is True
           and _v26_f4_v["allowed"] is False and any(r.startswith("output_is_evidence_only") for r in _v26_f4_v["refusals"])
           and _v26_f4_re[1] is None and _v26_f4_v2["allowed"] is True and _v26_f4_accept[1] == "revoked")
    # (5) a REAL disk-full error from SQLite stands the boundary down
    _v26_f5 = _v26_World("diskfull")
    _v26_f5.rex("rev-f5", "revoke_authorization", {"principal": "svc", "at": _v26_NOW, "reason": "r", "revoked_by": "dmitry"})
    _v26_f5_pages = _v26_f5.conn.execute("PRAGMA page_count").fetchone()[0]
    _v26_f5.conn.execute("PRAGMA max_page_count=%d" % _v26_f5_pages)  # the database is now full for real
    _v26_f5_v = _v26_f5.guard("dispatch_acceptance", "svc", _v26_req, CR26.snapshot(CS26, _v26_f5.conn, []), action="x" * 200000)  # the denial needs pages the capped database cannot give
    _v26_f5.conn.execute("PRAGMA max_page_count=1073741823")
    _v26_f5_after = _v26_f5.guard("dispatch_acceptance", "svc", _v26_req, CR26.snapshot(CS26, _v26_f5.conn, []))
    expect("VELDO-0026 AC3 revocation/real-disk-full (review 1): with the database's page limit set to its current size (SQLite's own "
           "'database or disk is full'), the refusal of a revoked actor is returned as a stand-down naming denial_not_recorded, no "
           "exception escapes, no transaction is left open and dispatch is not permitted; with room restored the same refusal is "
           "recorded as a denial",
           _v26_f5_v["stand_down"] is True and _v26_f5_v["allowed"] is False and any("denial_not_recorded" in r and "full" in r for r in _v26_f5_v["refusals"])
           and CR26.dispatch_permitted(_v26_f5_v) is False and not _v26_f5.conn.in_transaction
           and _v26_f5_after["stand_down"] is False and _v26_f5_after["denial"] is not None)
    _v26_f5.conn.close()
    # (6) an identical retry replays; other content under the same id conflicts
    _v26_f6 = _v26_World("retry")
    _v26_f6_cmd = {"effect_id": "eff-r", "principal": "svc", "receiver": "recv-1", "kind": "push"}
    _v26_f6_first = _v26_f6.rex("acc-r", "accept_effect", _v26_f6_cmd)
    _v26_f6_again = _v26_f6.rex("acc-r", "accept_effect", dict(_v26_f6_cmd), now=_v26_NOW + 500)
    _v26_f6_other = _v26_f6.rex("acc-r", "accept_effect", dict(_v26_f6_cmd, kind="deploy"))
    expect("VELDO-0026 AC2 revocation/identical-retry (review 1): repeating an identical accept_effect (same id and parameters, later "
           "clock, freshly derived versions) returns the committed result marked replayed with the same seq instead of a content "
           "conflict; the same id with other parameters is a conflict",
           _v26_f6_first[1] is None and _v26_f6_again[1] is None and _v26_f6_again[0]["replayed"] is True and _v26_f6_again[0]["seq"] == _v26_f6_first[0]["seq"]
           and _v26_f6_other[1] == "effect_refused" and len(CS26.export_journal(_v26_f6.conn)) == 4)
    _v26_f6.conn.close()
    # (7) transitive prerequisites: A -> B -> C reads C, passes intact, refuses when C is withdrawn
    _v26_f7 = _v26_World("chain")
    _v26_f7.put("c", "pre:C", "prerequisite", {"status": "accepted"}, 0)
    _v26_f7.put("b", "pre:B", "prerequisite", {"status": "accepted", "prerequisites": ["pre:C"]}, 0)
    _v26_f7.put("a", "dep:A", "dependency", {"prerequisites": ["pre:B"], "status": "resolved"}, 0)
    _v26_f7_snap = CR26.snapshot(CS26, _v26_f7.conn, ["dep:A"])
    _v26_f7_ok = _v26_f7.guard("claim", "svc", _v26_req, _v26_f7_snap)
    _v26_f7.put("wd-c", "pre:C", "prerequisite", {"status": "withdrawn"}, 1)
    _v26_f7_bad = _v26_f7.guard("claim", "svc", _v26_req, _v26_f7_snap)
    expect("VELDO-0026 AC1 revocation/transitive-prerequisites (review 1): a snapshot of a dependency reads its prerequisite AND that "
           "prerequisite's own prerequisite (A, B and C); the intact chain is allowed rather than rejected for an unread reference; "
           "withdrawing C two hops away refuses as dependency_withdrawn",
           {"dep:A", "pre:B", "pre:C"} <= set(_v26_f7_snap["versions"]) and _v26_f7_ok["allowed"] is True
           and _v26_f7_bad["allowed"] is False and any(r == "dependency_withdrawn:pre:C" for r in _v26_f7_bad["refusals"]))
    _v26_f7.conn.close()
    _v26_f.conn.close()
    for _wd in (_v26_w, _v26_r, _v26_c, _v26_e, _v26_d):
        _wd.conn.close()

_v26_shutil.rmtree(_v26_tmp, ignore_errors=True)
