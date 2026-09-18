"""VELDO-0025: authenticated membership and scoped delegation (PLAN-0019 W10).

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, so its declared
prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 38_veldo_0025_membership

WHAT IS UNDER TEST. .veldo/control_membership.py over .veldo/control_store.py and
.veldo/authority_contract.py against a REAL SQLite store with REAL Ed25519 keys through the installed
ssh-keygen: every administrative command is admitted only when its OpenSSH envelope verifies against
the signer's active committed key and its canonical digest RECOMPUTES from the operation, target and
complete parameters to be executed, so every mutated envelope field and every substituted parameter
(an enrollment public key among them) refuses with membership unchanged (AC1); the owner bootstrap
is accepted exactly once, membership changes need an active person holding membership_steward and
the enrollee's key-possession co-signature, a service never grants itself anything, two role changes
racing one version from two client processes have one winner and a writer killed after acceptance
leaves one committed transition, and assignments needing another named authority stay blocked until
that person is enrolled (AC2); delegated use is judged on every predicate conjunctively and a
delegation cached across its committed supersession is stale (AC3). The three declared falsifiers
are applied to COPIES of the modules (side by side, as the organ loads its siblings) and required to
turn their named row red while the unmutated modules pass it. Without ssh-keygen the suite stands
down by name.
"""
import importlib.util as _v25_ilu
import json as _v25_json
import os as _v25_os
import shutil as _v25_shutil
import subprocess as _v25_sp
import sys as _v25_sys
import tempfile as _v25_tf
from pathlib import Path as _v25_Path

_v25_tmp = _v25_Path(_v25_tf.mkdtemp(prefix="v25"))
_v25_have_ssh = _v25_shutil.which("ssh-keygen") is not None


def _v25_load(name, path):
    spec = _v25_ilu.spec_from_file_location(name, path)
    m = _v25_ilu.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _v25_organs(veldo_dir, tag):
    """(store, membership) loaded from one directory, so the membership organ finds ITS sibling
    authority contract there (a mutant directory carries mutated siblings)."""
    store = _v25_load("v25_store_" + tag, _v25_Path(veldo_dir) / "control_store.py")
    mem = _v25_load("v25_mem_" + tag, _v25_Path(veldo_dir) / "control_membership.py")
    mem.attach(store)
    return store, mem


def _v25_mutant_dir(edits):
    """A copy of the three organs under a temporary directory with the named edits applied
    ({filename: (old, new)}), each exactly once."""
    d = _v25_Path(_v25_tf.mkdtemp(prefix="v25mut", dir=str(_v25_tmp)))
    for f in ("control_store.py", "control_membership.py", "authority_contract.py"):
        src = (ROOT / ".veldo" / f).read_text()
        if f in edits:
            old, new = edits[f]
            assert src.count(old) == 1, (f, old[:60], src.count(old))
            src = src.replace(old, new)
        (d / f).write_text(src)
    return d


CS25, CM25 = _v25_organs(ROOT / ".veldo", "main")
AC25 = CM25.AC
_v25_IDS = {"domain_uuid": "dom-v25", "repository_uuid": "repo-v25", "store_uuid": "store-v25"}
_v25_NOW = 1_900_000_000

if not _v25_have_ssh:
    expect("VELDO-0025 STOOD DOWN by name - ssh-keygen is not installed here, so the real-signature rows cannot run", True)
else:
    _v25_kd = _v25_tmp / "keys"
    _v25_kd.mkdir()

    def _v25_keygen(name):
        _v25_sp.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", name + "@veldo", "-f", str(_v25_kd / name)], check=True, capture_output=True, stdin=_v25_sp.DEVNULL, timeout=60)
        return (_v25_kd / (name + ".pub")).read_text()

    def _v25_sign(name, msg):
        f = _v25_kd / (name + ".msg")
        f.write_bytes(msg)
        sig = _v25_kd / (name + ".msg.sig")
        if sig.exists():
            sig.unlink()  # ssh-keygen asks before overwriting a .sig and would block on stdin
        _v25_sp.run(["ssh-keygen", "-Y", "sign", "-f", str(_v25_kd / name), "-n", AC25.SIGNATURE_NAMESPACE, str(f)], check=True, capture_output=True, stdin=_v25_sp.DEVNULL, timeout=60)
        return sig.read_text()

    _v25_pub = {n: _v25_keygen(n) for n in ("dmitry", "asya", "lena", "svc", "mallory")}

    class _v25_World:
        """A fresh store with the owner bootstrapped, plus helpers that build and sign envelopes
        against the store's committed state."""

        def __init__(self, name, store=None, mem=None):
            self.store, self.mem = (store or CS25), (mem or CM25)
            self.ac = self.mem.AC
            self.dir = _v25_tmp / name
            self.dir.mkdir(parents=True)
            self.db = str(self.dir / "control.sqlite3")
            self.conn = self.store.open_store(self.db)
            self.n = 0

        def nonce(self):
            self.n += 1
            return "nonce-%d" % self.n

        def state(self):
            return self.mem.authority_state(self.store, self.conn)

        def cmd(self, cid, op, params):
            c = {"command_id": cid, "principal": None, "operation": op, "target": "authority", "parameters": params, "artifact_digests": [], "nonce": None, "expected_versions": {}}
            c["expected_versions"] = self.mem.expected_versions_for(self.store, self.conn, c)
            return c

        def envelope(self, principal, command, nonce=None, **over):
            st = self.state()
            env = {"schema": self.ac.ENVELOPE_SCHEMA, **_v25_IDS, "command_id": command["command_id"], "request_revision": 1, "nonce": nonce or self.nonce(),
                   "expires_at": _v25_NOW + 600, "membership_version": st["membership_version"], "delegation_version": st["delegation_version"],
                   "principal": principal, "command_digest": self.ac.canonical_command_digest(command)}
            env.update(over)
            return env

        def admit(self, signer, command, enrollee=None, env=None, signature=None, enrollee_sig=None, now=_v25_NOW):
            env = env or self.envelope(signer, command)
            sig = signature or _v25_sign(signer, self.ac.canonical_envelope_bytes(env))
            esig = enrollee_sig if enrollee_sig is not None else (_v25_sign(enrollee, self.ac.canonical_envelope_bytes(dict(env, principal=enrollee))) if enrollee else None)
            try:
                return self.mem.admit(self.store, self.conn, env, command, sig, _v25_IDS, now, enrollee_signature=esig), None
            except Exception as e:
                if type(e).__name__ == "MembershipRefused":
                    return None, e.code
                raise

        def bootstrap(self):
            c = self.cmd("boot", "enroll_principal", {"principal": "dmitry", "principal_type": "person", "roles": ["project_owner", "membership_steward"],
                                                     "public_key": _v25_pub["dmitry"], "independence_group": "founder", "scope": "*"})
            return self.admit("dmitry", c)

        def enroll(self, cid, principal, ptype, roles, group="ops", scope="*", signer="dmitry"):
            c = self.cmd(cid, "enroll_principal", {"principal": principal, "principal_type": ptype, "roles": roles, "public_key": _v25_pub[principal], "independence_group": group, "scope": scope})
            return self.admit(signer, c, enrollee=principal)

        def members(self):
            return {m["principal"]: sorted(m.get("roles") or []) for m in self.state()["membership"] if m.get("revoked_at") is None}

    # ---------------------------------------------------------------------------------------------
    # AC2 first: the bootstrap, because every other row needs an owner.
    # ---------------------------------------------------------------------------------------------
    _v25_w = _v25_World("main")
    _v25_pre = [
        _v25_w.admit("dmitry", _v25_w.cmd("b-asya", "enroll_principal", {"principal": "asya", "principal_type": "person", "roles": ["project_owner", "membership_steward"], "public_key": _v25_pub["asya"], "independence_group": "x", "scope": "*"}))[1],
        _v25_w.admit("dmitry", _v25_w.cmd("b-roles", "enroll_principal", {"principal": "dmitry", "principal_type": "person", "roles": ["project_owner"], "public_key": _v25_pub["dmitry"], "independence_group": "x", "scope": "*"}))[1],
        _v25_w.admit("dmitry", _v25_w.cmd("b-svc", "enroll_principal", {"principal": "dmitry", "principal_type": "service", "roles": ["project_owner", "membership_steward"], "public_key": _v25_pub["dmitry"], "independence_group": "x", "scope": "*"}))[1],
        _v25_w.admit("dmitry", _v25_w.cmd("b-op", "change_roles", {"principal": "dmitry", "roles": ["project_owner"]}))[1],
    ]
    _v25_boot_res, _v25_boot_code = _v25_w.bootstrap()
    _v25_boot_again = _v25_w.admit("dmitry", _v25_w.cmd("boot2", "enroll_principal", {"principal": "dmitry", "principal_type": "person", "roles": ["project_owner", "membership_steward"], "public_key": _v25_pub["dmitry"], "independence_group": "founder", "scope": "*"}))[1]
    _v25_st1 = _v25_w.state()
    expect("VELDO-0025 AC2 membership/bootstrap: with no membership, an enrollment of someone else, an owner without both bootstrap roles, an "
           "owner typed as a service, and a non-enrollment command are each refused as bootstrap_refused; the owner's self-signed "
           "enrollment with project_owner and membership_steward commits once (membership version 1, one key, one member); a second "
           "bootstrap is refused (membership exists: the ordinary path, which needs a co-signature and refuses self-enrollment)",
           _v25_pre == ["bootstrap_refused"] * 4 and _v25_boot_code is None and _v25_boot_res["committed"] is True
           and _v25_st1["membership_version"] == 1 and len(_v25_st1["keyring"]) == 1 and _v25_w.members() == {"dmitry": ["membership_steward", "project_owner"]}
           and _v25_boot_again in ("key_possession_unproven", "self_grant_refused", "store_refused"))
    _v25_no_cosig = _v25_w.admit("dmitry", _v25_w.cmd("e-asya-0", "enroll_principal", {"principal": "asya", "principal_type": "person", "roles": ["security_authority"], "public_key": _v25_pub["asya"], "independence_group": "ops", "scope": "*"}))[1]
    _v25_wrong_cosig = _v25_w.admit("dmitry", _v25_w.cmd("e-asya-1", "enroll_principal", {"principal": "asya", "principal_type": "person", "roles": ["security_authority"], "public_key": _v25_pub["asya"], "independence_group": "ops", "scope": "*"}), enrollee="mallory")[1]
    _v25_asya = _v25_w.enroll("e-asya", "asya", "person", ["security_authority"])
    _v25_svc = _v25_w.enroll("e-svc", "svc", "service", [])
    expect("VELDO-0025 AC2 membership/key-possession: enrolling asya without her co-signature, or with a co-signature made by another key, "
           "is refused as key_possession_unproven and enrolls nobody; with her own co-signature over the envelope she is enrolled with "
           "her key; a service is enrolled the same way by the steward; the membership version counts each",
           _v25_no_cosig == "key_possession_unproven" and _v25_wrong_cosig == "key_possession_unproven"
           and _v25_asya[1] is None and _v25_svc[1] is None and _v25_w.members() == {"dmitry": ["membership_steward", "project_owner"], "asya": ["security_authority"], "svc": []}
           and _v25_w.state()["membership_version"] == 3 and len(_v25_w.state()["keyring"]) == 3)

    # ---------------------------------------------------------------------------------------------
    # AC1: the envelope and the recomputed digest; membership unchanged on every refusal.
    # ---------------------------------------------------------------------------------------------
    _v25_members_before = _v25_w.members()
    _v25_snap_before = CS25.table_snapshot(_v25_w.conn)
    _v25_c = _v25_w.cmd("e-lena", "enroll_principal", {"principal": "lena", "principal_type": "person", "roles": ["admission_authority"], "public_key": _v25_pub["lena"], "independence_group": "proj", "scope": ["PROJ-A"]})
    _v25_env = _v25_w.envelope("dmitry", _v25_c)
    _v25_sig = _v25_sign("dmitry", AC25.canonical_envelope_bytes(_v25_env))
    _v25_esig = _v25_sign("lena", AC25.canonical_envelope_bytes(dict(_v25_env, principal="lena")))
    _v25_field_results = {}
    for _f in AC25.ENVELOPE_FIELDS:
        _mut = dict(_v25_env)
        _mut[_f] = ({"schema": "veldo.command_envelope/v0", "principal": "asya", "nonce": "other-nonce", "command_digest": "sha256:" + "0" * 64}.get(_f, (_v25_env[_f] + 1) if isinstance(_v25_env[_f], int) else str(_v25_env[_f]) + "x"))
        _v25_field_results[_f] = _v25_w.admit("dmitry", _v25_c, env=_mut, signature=_v25_sig, enrollee_sig=_v25_esig)[1]
    _v25_param_results = {}
    for _pf, _pv in (("principal", "mallory"), ("roles", ["membership_steward"]), ("public_key", _v25_pub["mallory"]), ("principal_type", "service"), ("scope", "*"), ("independence_group", "founder")):
        _swapped = dict(_v25_c, parameters=dict(_v25_c["parameters"], **{_pf: _pv}))
        _swapped["expected_versions"] = CM25.expected_versions_for(CS25, _v25_w.conn, _swapped)  # the attacker adjusts what is not signed
        _v25_param_results[_pf] = _v25_w.admit("dmitry", _swapped, env=_v25_env, signature=_v25_sig, enrollee_sig=_v25_esig)[1]
    _v25_op_swapped = _v25_w.admit("dmitry", dict(_v25_c, operation="change_roles"), env=_v25_env, signature=_v25_sig, enrollee_sig=_v25_esig)[1]
    _v25_target_swapped = _v25_w.admit("dmitry", dict(_v25_c, target="other-authority"), env=_v25_env, signature=_v25_sig, enrollee_sig=_v25_esig)[1]
    _v25_transport = _v25_w.admit("dmitry", _v25_c, env=dict(_v25_env, transport_authenticated=True), signature=_v25_sign("mallory", AC25.canonical_envelope_bytes(_v25_env)), enrollee_sig=_v25_esig)[1]
    _v25_unchanged = _v25_w.members() == _v25_members_before and CS25.table_snapshot(_v25_w.conn) == _v25_snap_before
    expect("VELDO-0025 AC1 membership/envelope-fields: with a validly signed enrollment envelope, mutating EACH of the twelve envelope fields "
           "after signing refuses (the signature no longer verifies, or the envelope names the wrong schema, authority, version, nonce, "
           "principal, expiry or digest), substituting each operation parameter (principal, roles, public key, type, scope, group), the "
           "operation or the target under the original envelope (with the unsigned expected_versions adjusted as an attacker would) "
           "refuses as envelope_refused because the digest is RECOMPUTED, a bad "
           "command signature over an SSH-transport-authenticated envelope refuses (transport is no substitute), and membership and every "
           "store table are unchanged after all of it (field results: %s)" % {k: v for k, v in _v25_field_results.items() if v is None},
           all(v in ("envelope_refused", "signature_invalid") for v in _v25_field_results.values()) and len(_v25_field_results) == 12
           and all(v == "envelope_refused" for v in _v25_param_results.values()) and _v25_op_swapped == "envelope_refused" and _v25_target_swapped == "envelope_refused"
           and _v25_transport == "signature_invalid" and _v25_unchanged)
    _v25_lena = _v25_w.admit("dmitry", _v25_c, env=_v25_env, signature=_v25_sig, enrollee_sig=_v25_esig)
    expect("VELDO-0025 AC1 membership/key-substitution: the enrollment public key swapped for another key under the original valid signature "
           "is refused before execution with membership unchanged (above); the untouched command with the same envelope and signature "
           "then enrolls lena with the key that was signed for, scoped to PROJ-A",
           _v25_param_results["public_key"] == "envelope_refused" and _v25_lena[1] is None and _v25_lena[0]["committed"] is True
           and "lena" in _v25_w.members() and any(k["principal"] == "lena" and k["public_key"] == " ".join(_v25_pub["lena"].split()[:2]) for k in _v25_w.state()["keyring"]))
    # THE DECLARED FALSIFIER: bypass command-digest recomputation and substitute an enrollment public key.
    _v25_m1_dir = _v25_mutant_dir({"authority_contract.py": ('''    if envelope["command_digest"] != canonical_command_digest(command):
        problems.append("envelope digest''', '''    if False:  # mutant: the envelope's digest is taken on trust
        problems.append("envelope digest''')})
    _v25_m1_store, _v25_m1_mem = _v25_organs(_v25_m1_dir, "m1")
    _v25_m1 = _v25_World("m1", _v25_m1_store, _v25_m1_mem)
    _v25_m1.bootstrap()
    _v25_m1_c = _v25_m1.cmd("e-svc", "enroll_principal", {"principal": "svc", "principal_type": "service", "roles": [], "public_key": _v25_pub["svc"], "independence_group": None, "scope": "*"})
    _v25_m1_env = _v25_m1.envelope("dmitry", _v25_m1_c)
    _v25_m1_sig = _v25_sign("dmitry", _v25_m1.ac.canonical_envelope_bytes(_v25_m1_env))
    _v25_m1_swapped = dict(_v25_m1_c, parameters=dict(_v25_m1_c["parameters"], public_key=_v25_pub["mallory"]))
    _v25_m1_swapped["expected_versions"] = _v25_m1_mem.expected_versions_for(_v25_m1_store, _v25_m1.conn, _v25_m1_swapped)  # expected_versions is not a signed field
    _v25_m1_esig = _v25_sign("mallory", _v25_m1.ac.canonical_envelope_bytes(dict(_v25_m1_env, principal="svc")))
    _v25_m1_res = _v25_m1.admit("dmitry", _v25_m1_swapped, env=_v25_m1_env, signature=_v25_m1_sig, enrollee_sig=_v25_m1_esig)
    _v25_m1_key = next((k["public_key"] for k in _v25_m1.state()["keyring"] if k["principal"] == "svc"), None)
    expect("VELDO-0025 AC1 membership/key-substitution DRIVEN (the declared falsifier): with digest recomputation bypassed in a copy of the "
           "authority contract beside a copy of the membership organ, the enrollment with mallory's key substituted under dmitry's original "
           "valid signature commits and the store holds mallory's key for the service, so the row reds; unmutated (the row above) the "
           "substitution is refused before execution",
           _v25_m1_res[1] is None and _v25_m1_key == " ".join(_v25_pub["mallory"].split()[:2]) and _v25_param_results["public_key"] == "envelope_refused")

    # ---------------------------------------------------------------------------------------------
    # AC2: policy, races from real processes, the kill after acceptance, blocked assignments.
    # ---------------------------------------------------------------------------------------------
    _v25_svc_self = _v25_w.admit("svc", _v25_w.cmd("sg1", "change_roles", {"principal": "svc", "roles": ["membership_steward"]}))[1]
    _v25_svc_enroll = _v25_w.admit("svc", _v25_w.cmd("sg2", "enroll_principal", {"principal": "mallory", "principal_type": "service", "roles": [], "public_key": _v25_pub["mallory"], "independence_group": None, "scope": "*"}), enrollee="mallory")[1]
    _v25_asya_self = _v25_w.admit("asya", _v25_w.cmd("sg3", "change_roles", {"principal": "asya", "roles": ["security_authority", "membership_steward"]}))[1]
    _v25_asya_enrolls = _v25_w.admit("asya", _v25_w.cmd("sg4", "enroll_principal", {"principal": "mallory", "principal_type": "person", "roles": [], "public_key": _v25_pub["mallory"], "independence_group": None, "scope": "*"}), enrollee="mallory")[1]
    _v25_svc_steward = _v25_w.admit("dmitry", _v25_w.cmd("sg5", "change_roles", {"principal": "svc", "roles": ["membership_steward"]}))[1]
    _v25_dmitry_self_enroll = _v25_w.admit("dmitry", _v25_w.cmd("sg6", "enroll_principal", {"principal": "dmitry", "principal_type": "person", "roles": ["project_owner"], "public_key": _v25_pub["dmitry"], "independence_group": "founder", "scope": "*"}), enrollee="dmitry")[1]
    _v25_registry_ok = set(CM25.ADMIN_OPERATIONS) <= set(CS25.COMMAND_REGISTRY) and len(CM25.ADMIN_OPERATIONS) == 6
    expect("VELDO-0025 AC2 membership/self-grant: a service signing its own role change or an enrollment is refused as not_a_person; a "
           "person without membership_steward granting herself the steward role or enrolling someone is refused; the steward giving a "
           "service the steward role is refused (a non-person never holds it); the owner re-enrolling himself is refused (a principal does "
           "not enroll itself); membership is unchanged; the six administrative operations are registered in the store",
           _v25_svc_self == "not_a_person" and _v25_svc_enroll == "not_a_person" and _v25_asya_self == "policy_refused" and _v25_asya_enrolls == "policy_refused"
           and _v25_svc_steward == "policy_refused" and _v25_dmitry_self_enroll in ("self_grant_refused", "store_refused")
           and _v25_w.members() == {"dmitry": ["membership_steward", "project_owner"], "asya": ["security_authority"], "svc": [], "lena": ["admission_authority"]}
           and _v25_registry_ok)
    # THE DECLARED FALSIFIER: allow a service principal to grant itself membership during the competing-role-change test.
    _v25_m2_dir = _v25_mutant_dir({"control_membership.py": ('''    if entry is None or entry.get("principal_type") != "person":
        problems.append("not_a_person: signer %r is not an enrolled person; services, policies and agent runs change no membership" % signer)
        return problems
''', '''    if entry is None or entry.get("principal_type") != "person":
        return []  # mutant: a service is trusted with membership
''')})
    _v25_m2_store, _v25_m2_mem = _v25_organs(_v25_m2_dir, "m2")
    _v25_m2 = _v25_World("m2", _v25_m2_store, _v25_m2_mem)
    _v25_m2.bootstrap()
    _v25_m2.enroll("e-svc", "svc", "service", [])
    _v25_m2_a = _v25_m2.cmd("race-a", "change_roles", {"principal": "svc", "roles": ["membership_steward"]})  # the service grants itself the steward role
    _v25_m2_b = _v25_m2.cmd("race-b", "change_roles", {"principal": "svc", "roles": ["operations_authority"]})  # dmitry's competing change, same version
    _v25_m2_res_a = _v25_m2.admit("svc", _v25_m2_a)
    _v25_m2_res_b = _v25_m2.admit("dmitry", _v25_m2_b)
    _v25_m2_roles = _v25_m2.members().get("svc")
    expect("VELDO-0025 AC2 membership/self-grant DRIVEN (the declared falsifier): with a non-person signer trusted in a copy of the membership "
           "organ, the service's self-grant of membership_steward during the competing role change commits and the stored role is the "
           "unauthorized one (dmitry's competing change then loses the version race), so the row reds; unmutated (the row above) the "
           "service's signature changes no membership",
           _v25_m2_res_a[1] is None and _v25_m2_roles == ["membership_steward"] and _v25_m2_res_b[1] == "store_refused" and _v25_svc_self == "not_a_person")

    # Two client PROCESSES race two role changes against one version; then a writer is SIGKILLed after
    # acceptance (after COMMIT, before the reply) and the retry of the same envelope replays.
    _v25_child = '''
import importlib.util, sys, json
def load(n, p):
    sp = importlib.util.spec_from_file_location(n, p); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
veldo = sys.argv[1]
CS = load("cs", veldo + "/control_store.py"); CM = load("cm", veldo + "/control_membership.py"); CM.attach(CS)
conn = CS.open_store(sys.argv[2]); job = json.load(open(sys.argv[3]))
try:
    r = CM.admit(CS, conn, job["envelope"], job["command"], job["signature"], job["ids"], job["now"], enrollee_signature=job.get("enrollee_signature"))
    print("REPLIED " + json.dumps({"seq": r["seq"], "replayed": r["replayed"]}))
except Exception as e:
    print("REFUSED " + getattr(e, "code", type(e).__name__))
'''

    def _v25_job(world, signer, command, env=None):
        env = env or world.envelope(signer, command)
        job = {"envelope": env, "command": command, "signature": _v25_sign(signer, world.ac.canonical_envelope_bytes(env)), "ids": _v25_IDS, "now": _v25_NOW}
        f = world.dir / ("job-%s.json" % command["command_id"])
        f.write_text(_v25_json.dumps(job))
        return str(f)

    def _v25_run_children(world, jobs, kill_at=None):
        env = dict(_v25_os.environ, VELDO_CONTROL_TEST_HARNESS="1" if kill_at else "0", VELDO_CONTROL_KILL_AT=kill_at or "")
        procs = [_v25_sp.Popen([_v25_sys.executable, "-c", _v25_child, str(ROOT / ".veldo"), world.db, j], stdout=_v25_sp.PIPE, stderr=_v25_sp.PIPE, text=True, stdin=_v25_sp.DEVNULL, env=env) for j in jobs]
        outs = []
        for p in procs:
            out, err = p.communicate(timeout=180)
            outs.append((p.returncode, out.strip().split("\n")[-1] if out.strip() else "", err[-200:]))
        return outs

    _v25_ra = _v25_w.cmd("proc-a", "change_roles", {"principal": "lena", "roles": ["admission_authority", "priority_authority"]})
    _v25_rb = _v25_w.cmd("proc-b", "change_roles", {"principal": "lena", "roles": []})
    _v25_race = _v25_run_children(_v25_w, [_v25_job(_v25_w, "dmitry", _v25_ra), _v25_job(_v25_w, "dmitry", _v25_rb)])
    _v25_lena_roles = _v25_w.members().get("lena")
    _v25_mv_after_race = _v25_w.state()["membership_version"]
    _v25_kc = _v25_w.cmd("proc-kill", "change_roles", {"principal": "svc", "roles": ["operations_authority"]})
    _v25_k_env = _v25_w.envelope("dmitry", _v25_kc)
    _v25_k_job = _v25_job(_v25_w, "dmitry", _v25_kc, env=_v25_k_env)
    _v25_killed = _v25_run_children(_v25_w, [_v25_k_job], kill_at="after_commit")
    _v25_svc_after_kill = _v25_w.members().get("svc")
    _v25_mv_after_kill = _v25_w.state()["membership_version"]
    _v25_retry = _v25_run_children(_v25_w, [_v25_k_job])
    _v25_journal_after = len(CS25.export_journal(_v25_w.conn))
    expect("VELDO-0025 AC2 membership/one-transition: two client processes racing two role changes for lena against one membership version "
           "each verify a real signature and exactly one commits (the other loses as store_refused by version), lena holds one of the two "
           "role sets and the membership version advanced by one; a writer SIGKILLed after acceptance (after COMMIT, before the reply) "
           "leaves the change committed with the version advanced, and the retry of the SAME envelope replays the committed result "
           "without a new journal record; historical authority is unchanged (dmitry and asya keep their roles) (race: %s; kill: %s; retry: %s)"
           % ([o[1] for o in _v25_race], [(o[0], o[1]) for o in _v25_killed], [o[1] for o in _v25_retry]),
           sorted(o[1].split(" ")[0] for o in _v25_race) == ["REFUSED", "REPLIED"] and all(o[0] == 0 for o in _v25_race)
           and "store_refused" in "".join(o[1] for o in _v25_race) and _v25_lena_roles in (["admission_authority", "priority_authority"], []) and _v25_mv_after_race == 5
           and _v25_killed[0][0] == -9 and _v25_killed[0][1] == "" and _v25_svc_after_kill == ["operations_authority"] and _v25_mv_after_kill == 6
           and _v25_retry[0][1].startswith("REPLIED") and '"replayed": true' in _v25_retry[0][1] and _v25_journal_after == 6
           and _v25_w.members()["dmitry"] == ["membership_steward", "project_owner"] and _v25_w.members()["asya"] == ["security_authority"])
    _v25_st = _v25_w.state()
    _v25_req_named = {"roles": [], "named_principals": ["ops-lead"], "quorum": 1, "subject_digest": "sha256:s"}
    _v25_req_two = {"roles": [], "named_principals": [], "quorum": 2, "min_independence": 2, "subject_digest": "sha256:s"}
    _v25_att_d = [{"principal": "dmitry", "subject_digest": "sha256:s"}]
    _v25_blocked = AC25.authorize("decision_settlement", _v25_req_named, _v25_att_d, _v25_st["membership"], _v25_NOW)
    _v25_two_blocked = AC25.authorize("decision_settlement", _v25_req_two, _v25_att_d, _v25_st["membership"], _v25_NOW)
    _v25_two_ok = AC25.authorize("decision_settlement", _v25_req_two, _v25_att_d + [{"principal": "asya", "subject_digest": "sha256:s"}], _v25_st["membership"], _v25_NOW)
    expect("VELDO-0025 AC2 membership/blocked-without-named-authority: an assignment naming a principal who is not enrolled is refused as "
           "named_principal_not_satisfied and a quorum of two independent people is not met by the owner alone; with asya enrolled "
           "(a distinct independence group) the two-person quorum is met; the store's committed membership is the registry the "
           "authority contract judges with",
           _v25_blocked[0] is False and any("named_principal_not_satisfied:ops-lead" in r for r in _v25_blocked[1])
           and _v25_two_blocked[0] is False and any(r.startswith("quorum_not_met:1<2") for r in _v25_two_blocked[1]) and _v25_two_ok[0] is True)

    # ---------------------------------------------------------------------------------------------
    # AC3: delegated use, every predicate, and supersession.
    # ---------------------------------------------------------------------------------------------
    _v25_dparams = {"id": "del-1", "principal": "asya", "channel": "telegram_chat", "assertion_kinds": ["decision_answer"], "authority_scope": ["security_authority"],
                    "request_version": 3, "presentation_version": 2, "expires_at": _v25_NOW + 3600, "edge_key_id": "edge-telegram"}
    _v25_g_by_svc = _v25_w.admit("svc", _v25_w.cmd("g0", "grant_delegation", _v25_dparams))[1]
    _v25_g_by_lena = _v25_w.admit("lena", _v25_w.cmd("g0b", "grant_delegation", _v25_dparams))[1]
    _v25_g_wide = _v25_w.admit("asya", _v25_w.cmd("g0c", "grant_delegation", dict(_v25_dparams, authority_scope=["project_owner"])))[1]
    _v25_g = _v25_w.admit("asya", _v25_w.cmd("g1", "grant_delegation", _v25_dparams))
    _v25_st_g = _v25_w.state()
    _v25_req = {"boundary": "decision_settlement", "roles": ["security_authority"], "quorum": 1, "scope": "security_authority", "subject_digest": "sha256:f"}
    _v25_asr = {"channel": "telegram_chat", "assertion_kind": "decision_answer", "request_version": 3}
    _v25_use = {"principal": "asya", "delegation_id": "del-1", "delegation_version": _v25_st_g["delegation_version"]}
    _v25_intact = CM25.delegated_use_problems(_v25_st_g, _v25_use, _v25_asr, _v25_req, _v25_NOW)
    _v25_pred = {
        "channel": CM25.delegated_use_problems(_v25_st_g, _v25_use, dict(_v25_asr, channel="jira"), _v25_req, _v25_NOW),
        "assertion_kind": CM25.delegated_use_problems(_v25_st_g, _v25_use, dict(_v25_asr, assertion_kind="acknowledgement"), _v25_req, _v25_NOW),
        "request_version": CM25.delegated_use_problems(_v25_st_g, _v25_use, dict(_v25_asr, request_version=4), _v25_req, _v25_NOW),
        "scope": CM25.delegated_use_problems(_v25_st_g, _v25_use, _v25_asr, dict(_v25_req, scope="project_owner", roles=["project_owner"]), _v25_NOW),
        "expiry": CM25.delegated_use_problems(_v25_st_g, _v25_use, _v25_asr, _v25_req, _v25_NOW + 4000),
        "principal": CM25.delegated_use_problems(_v25_st_g, dict(_v25_use, principal="svc"), _v25_asr, _v25_req, _v25_NOW),
        "role": CM25.delegated_use_problems(_v25_st_g, _v25_use, _v25_asr, dict(_v25_req, roles=["admission_authority"], scope="admission_authority"), _v25_NOW),
        "quorum": CM25.delegated_use_problems(_v25_st_g, _v25_use, _v25_asr, dict(_v25_req, quorum=2), _v25_NOW),
        "actor_kind": CM25.delegated_use_problems(_v25_st_g, _v25_use, _v25_asr, dict(_v25_req, boundary="dispatch_acceptance"), _v25_NOW),
        "version": CM25.delegated_use_problems(_v25_st_g, dict(_v25_use, delegation_version=_v25_st_g["delegation_version"] - 1), _v25_asr, _v25_req, _v25_NOW),
    }
    expect("VELDO-0025 AC3 membership/delegation-predicates: a delegation is granted only by the delegating person or the steward (a service "
           "and another person are refused) and only within the person's roles; with asya's committed delegation the intact use has no "
           "problems, and invalidating each single predicate (channel, assertion kind, request version, scope, expiry, principal, role, "
           "quorum, actor kind at a boundary that admits no person, delegation version) refuses by name (failures: %s)"
           % [k for k, v in _v25_pred.items() if not v],
           _v25_g_by_svc == "not_a_person" and _v25_g_by_lena == "delegation_refused" and _v25_g_wide == "delegation_refused" and _v25_g[1] is None
           and _v25_intact == [] and all(v for v in _v25_pred.values())
           and _v25_pred["version"][0].startswith("stale_delegation") and _v25_pred["quorum"][0].endswith("quorum_not_met:1<2")
           and any("principal_type_not_admitted" in p for p in _v25_pred["actor_kind"]) and any("not permitted" in p for p in _v25_pred["assertion_kind"]))
    # Supersession races acceptance: an edge caches the delegation state, the person supersedes it, the cached use is stale.
    _v25_cached_state = _v25_w.state()
    _v25_sup_by_lena = _v25_w.admit("lena", _v25_w.cmd("s0", "supersede_delegation", dict(_v25_dparams, id="del-2", supersedes="del-1", request_version=4)))[1]
    _v25_sup_other = _v25_w.admit("asya", _v25_w.cmd("s0b", "supersede_delegation", dict(_v25_dparams, id="del-2", supersedes="del-1", principal="lena")))[1]
    _v25_sup = _v25_w.admit("asya", _v25_w.cmd("s1", "supersede_delegation", dict(_v25_dparams, id="del-2", supersedes="del-1", request_version=4)))
    _v25_sup_twice = _v25_w.admit("asya", _v25_w.cmd("s2", "supersede_delegation", dict(_v25_dparams, id="del-3", supersedes="del-1", request_version=5)))[1]
    _v25_live = _v25_w.state()
    _v25_stale_use = CM25.delegated_use_problems(_v25_live, _v25_use, _v25_asr, _v25_req, _v25_NOW)
    _v25_cached_use = CM25.delegated_use_problems(_v25_cached_state, _v25_use, _v25_asr, _v25_req, _v25_NOW)
    _v25_new_use = CM25.delegated_use_problems(_v25_live, dict(_v25_use, delegation_id="del-2", delegation_version=_v25_live["delegation_version"]), dict(_v25_asr, request_version=4), _v25_req, _v25_NOW)
    _v25_rev = _v25_w.admit("dmitry", _v25_w.cmd("r1", "revoke_delegation", {"id": "del-2", "revoked_at": _v25_NOW - 1}))
    _v25_revoked_use = CM25.delegated_use_problems(_v25_w.state(), dict(_v25_use, delegation_id="del-2", delegation_version=_v25_w.state()["delegation_version"]), dict(_v25_asr, request_version=4), _v25_req, _v25_NOW)
    expect("VELDO-0025 AC3 membership/stale-delegation: supersession by another person, or one that changes the principal, is refused; asya "
           "supersedes del-1 with del-2 (delegation version advances) and a second supersession of del-1 is refused; a signed use naming "
           "del-1 at the old version is stale against the committed state (version AND superseded), and a use judged against the CACHED "
           "pre-supersession state passes, which is exactly why the version is checked against the store; del-2 at the current version "
           "is good until the steward revokes it, after which it refuses as revoked",
           _v25_sup_by_lena == "delegation_refused" and _v25_sup_other == "delegation_refused" and _v25_sup[1] is None and _v25_sup_twice == "store_refused"
           and _v25_live["delegation_version"] == _v25_cached_state["delegation_version"] + 1
           and len([p for p in _v25_stale_use if p.startswith("stale_delegation")]) == 2 and _v25_cached_use == [] and _v25_new_use == []
           and _v25_rev[1] is None and any("is revoked" in p for p in _v25_revoked_use))
    # THE DECLARED FALSIFIER: cache delegation authority across its committed supersession and accept a stale signed command.
    _v25_m3_dir = _v25_mutant_dir({"control_membership.py": ('''    if envelope.get("delegation_version") != state["delegation_version"]:
        problems.append("stale_delegation: envelope delegation_version %r is not the current %r" % (envelope.get("delegation_version"), state["delegation_version"]))
''', '''    if False:  # mutant: the cached delegation authority is trusted across supersession
        problems.append("stale_delegation")
''')})
    _v25_m3_store, _v25_m3_mem = _v25_organs(_v25_m3_dir, "m3")
    _v25_m3 = _v25_World("m3", _v25_m3_store, _v25_m3_mem)
    _v25_m3.bootstrap()
    _v25_m3.enroll("e-asya", "asya", "person", ["security_authority"])
    _v25_m3.admit("asya", _v25_m3.cmd("g1", "grant_delegation", _v25_dparams))
    _v25_m3_cached = _v25_m3.state()
    # the supersession is committed but the mutant's check does not look at superseded_by when the version is skipped? it does: so the
    # falsifier's stale command is one whose delegation record is NOT yet superseded in the cached copy the edge holds, judged by the
    # mutant against the LIVE store where only the version moved (a revocation of del-1 by supersession that replaced its id)
    _v25_m3.admit("asya", _v25_m3.cmd("s1", "supersede_delegation", dict(_v25_dparams, id="del-2", supersedes="del-1", request_version=4)))
    _v25_m3_live = _v25_m3.state()
    _v25_m3_live_unsuperseded = dict(_v25_m3_live, delegations=[dict(d, superseded_by=None) if d["id"] == "del-1" else d for d in _v25_m3_live["delegations"]])
    _v25_m3_stale = _v25_m3_mem.delegated_use_problems(_v25_m3_live_unsuperseded, _v25_use, _v25_asr, _v25_req, _v25_NOW)
    _v25_ref_stale = CM25.delegated_use_problems(_v25_m3_live_unsuperseded, _v25_use, _v25_asr, _v25_req, _v25_NOW)
    expect("VELDO-0025 AC3 membership/stale-delegation DRIVEN (the declared falsifier): with the delegation-version check removed in a copy of "
           "the membership organ, a signed use of del-1 at the pre-supersession version against a state whose version has moved (the "
           "record itself still cached as current) is accepted, so the row reds; unmutated the same use refuses as stale_delegation by "
           "version, before any record field is consulted",
           _v25_m3_live["delegation_version"] == _v25_m3_cached["delegation_version"] + 1 and _v25_m3_stale == []
           and len(_v25_ref_stale) == 1 and _v25_ref_stale[0].startswith("stale_delegation: envelope delegation_version"))
    for _wd in (_v25_w, _v25_m1, _v25_m2, _v25_m3):
        _wd.conn.close()

_v25_shutil.rmtree(_v25_tmp, ignore_errors=True)
