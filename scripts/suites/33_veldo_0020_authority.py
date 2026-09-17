"""VELDO-0020: signing and authority contracts for enrolled channels (PLAN-0019 W5).

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, so its declared
prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 33_veldo_0020_authority

WHAT IS UNDER TEST. .veldo/authority_contract.py: conjunctive authorization at every R39 boundary
over distinct principal types and scoped membership (AC1); the OpenSSH-envelope Ed25519 command
signature, verified with a REAL key pair generated here through the installed ssh-keygen and the
canonical digest recomputed from the command (AC2); restricted edge keys and presentation-bound
canonical attribution per enrolled channel (AC3); and one settlement per request version with the
quorum counted by distinct principal (AC4). The four declared falsifiers are applied to a COPY of
the module and required to turn their named row red while the unmutated module passes it. The
signature rows drive ssh-keygen as a subprocess: when it is absent they stand down by name rather
than pass.
"""
import importlib.util as _v20_ilu
import shutil as _v20_shutil

_v20_spec = _v20_ilu.spec_from_file_location("v20_authority", ROOT / ".veldo" / "authority_contract.py")
AC20 = _v20_ilu.module_from_spec(_v20_spec)
_v20_spec.loader.exec_module(AC20)
_v20_src = (ROOT / ".veldo" / "authority_contract.py").read_text()
_v20_authspec = _v20_ilu.spec_from_file_location("v20_authz", ROOT / ".veldo" / "authorization.py")
AUTH20 = _v20_ilu.module_from_spec(_v20_authspec)
_v20_authspec.loader.exec_module(AUTH20)


def _v20_mutated_two(old1, new1, old2, new2):
    d = Path(tempfile.mkdtemp(prefix="v20mut2"))
    assert _v20_src.count(old1) == 1 and _v20_src.count(old2) == 1, (old1[:60], old2[:60])
    (d / "authority_contract.py").write_text(_v20_src.replace(old1, new1).replace(old2, new2))
    spec = _v20_ilu.spec_from_file_location("v20_mut_%s" % d.name, d / "authority_contract.py")
    m = _v20_ilu.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def _v20_mutated(old, new):
    d = Path(tempfile.mkdtemp(prefix="v20mut"))
    assert _v20_src.count(old) == 1, (old[:60], _v20_src.count(old))
    (d / "authority_contract.py").write_text(_v20_src.replace(old, new))
    spec = _v20_ilu.spec_from_file_location("v20_mut_%s" % d.name, d / "authority_contract.py")
    m = _v20_ilu.module_from_spec(spec)
    spec.loader.exec_module(m)
    _v20_shutil.rmtree(d, ignore_errors=True)
    return m


_V20_NOW = 1_800_000_000
_v20_members = [
    {"principal": "dmitry", "principal_type": "person", "roles": ["project_owner", "admission_authority", "membership_steward"], "independence_group": "founder", "scope": "*"},
    {"principal": "asya", "principal_type": "person", "roles": ["operations_authority"], "independence_group": "ops", "scope": "*"},
    {"principal": "lena", "principal_type": "person", "roles": ["admission_authority"], "independence_group": "proj-a", "scope": ["PROJ-A"]},
    {"principal": "codex-review", "principal_type": "service", "roles": [], "independence_group": "reviewer"},
    {"principal": "run-7f3a", "principal_type": "agent_run", "roles": [], "independence_group": None, "expires_at": _V20_NOW + 900},
    {"principal": "defect-policy-v3", "principal_type": "policy", "roles": ["admission_authority"], "independence_group": "policy"},
    {"principal": "left", "principal_type": "person", "roles": ["technical_authority"], "revoked_at": _V20_NOW - 10},
]


def _v20_att(principal, digest="sha256:subj"):
    return {"principal": principal, "subject_digest": digest, "at": _V20_NOW}


# ---------------------------------------------------------------------------------------------
# AC1: conjunctive authorization at every boundary.
# ---------------------------------------------------------------------------------------------
expect("VELDO-0020 AC1 authority-substitution/matrix: the boundary table is exactly the nine R39 boundaries, every admitted "
       "type is one of the four principal types, the seven R37 roles are registered, and the machine set is bound to "
       "authorization.MACHINE_ACTORS",
       set(AC20.BOUNDARIES) == {"command_acceptance", "proposal_commit", "assignment_acceptance", "claim", "dispatch_acceptance",
                                "privileged_tool_use", "result_acceptance", "decision_settlement", "landing_publication"}
       and all(set(v) <= set(AC20.PRINCIPAL_TYPES) for v in AC20.BOUNDARIES.values())
       and len(AC20.ROLES) == 7 and AC20.MACHINE_ACTORS == AUTH20.MACHINE_ACTORS)
_v20_req = {"roles": ["admission_authority"], "named_principals": ["dmitry"], "quorum": 1, "min_independence": 1, "subject_digest": "sha256:subj",
            "expires_at": _V20_NOW + 3600}
expect("VELDO-0020 AC1 authority-substitution/conjunction: Dmitry's own attestation at decision_settlement satisfies role, named "
       "principal, quorum and independence together; each condition failing alone is refused by name (a policy holding the "
       "role but not the named person; two people without the role; a quorum of two with one person; two independence "
       "groups with one; an expired requirement; a revoked member; a stale attestation; a type the boundary does not admit)",
       AC20.authorize("decision_settlement", _v20_req, [_v20_att("dmitry")], _v20_members, _V20_NOW) == (True, [])
       and "named_principal_not_satisfied:dmitry" in AC20.authorize("decision_settlement", _v20_req, [_v20_att("defect-policy-v3")], _v20_members, _V20_NOW)[1]
       and "role_not_satisfied:admission_authority" in AC20.authorize("decision_settlement", dict(_v20_req, named_principals=[]), [_v20_att("asya")], _v20_members, _V20_NOW)[1]
       and any(r.startswith("quorum_not_met") for r in AC20.authorize("decision_settlement", dict(_v20_req, quorum=2), [_v20_att("dmitry")], _v20_members, _V20_NOW)[1])
       and any(r.startswith("independence_not_met") for r in AC20.authorize("decision_settlement", dict(_v20_req, min_independence=2), [_v20_att("dmitry")], _v20_members, _V20_NOW)[1])
       and "requirement_expired" in AC20.authorize("decision_settlement", dict(_v20_req, expires_at=_V20_NOW - 1), [_v20_att("dmitry")], _v20_members, _V20_NOW)[1]
       and "membership_revoked:left" in AC20.authorize("decision_settlement", dict(_v20_req, named_principals=[], roles=["technical_authority"]), [_v20_att("left")], _v20_members, _V20_NOW)[1]
       and "attestation_stale:dmitry" in AC20.authorize("decision_settlement", _v20_req, [_v20_att("dmitry", "sha256:old")], _v20_members, _V20_NOW)[1]
       and "principal_type_not_admitted:run-7f3a" in AC20.authorize("decision_settlement", dict(_v20_req, named_principals=[], roles=[]), [_v20_att("run-7f3a")], _v20_members, _V20_NOW)[1]
       and AC20.authorize("claim", {"quorum": 1}, [_v20_att("run-7f3a")], _v20_members, _V20_NOW)[0] is True
       and AC20.authorize("telepathy", {}, [], _v20_members, _V20_NOW) == (False, ["unknown_boundary"]))
expect("VELDO-0020 AC1 authority-substitution/named-principal: an agent run, a service and a policy each fail a named-person "
       "predicate for dmitry even when they attest; only dmitry's own attestation satisfies it",
       all("named_principal_not_satisfied:dmitry" in AC20.authorize("proposal_commit", {"named_principals": ["dmitry"], "quorum": 1},
                                                                  [_v20_att(p)], _v20_members, _V20_NOW)[1]
           for p in ("run-7f3a", "codex-review", "defect-policy-v3"))
       and AC20.authorize("proposal_commit", {"named_principals": ["dmitry"], "quorum": 1}, [_v20_att("dmitry")], _v20_members, _V20_NOW)[0] is True)
# THE DECLARED FALSIFIER: allow an agent to satisfy a named-person predicate.
_V20_M1 = _v20_mutated('''        if not any(a.get("principal") == name and e.get("principal_type") == "person" for a, e in valid):
''', '''        if not any(a.get("principal") == name or e.get("principal_type") == "agent_run" for a, e in valid):  # mutant
''')
expect("VELDO-0020 AC1 authority-substitution/named-principal DRIVEN (the declared falsifier): with an agent run allowed to "
       "satisfy a named-person predicate in a copy, run-7f3a authorizes a proposal that names dmitry, so the row reds; "
       "unmutated it is refused",
       _V20_M1.authorize("proposal_commit", {"named_principals": ["dmitry"], "quorum": 1}, [_v20_att("run-7f3a")], _v20_members, _V20_NOW)[0] is True
       and AC20.authorize("proposal_commit", {"named_principals": ["dmitry"], "quorum": 1}, [_v20_att("run-7f3a")], _v20_members, _V20_NOW)[0] is False)

# ---------------------------------------------------------------------------------------------
# AC2: the signed command envelope, with a REAL Ed25519 key through the installed ssh-keygen.
# ---------------------------------------------------------------------------------------------
_v20_authority = {"domain_uuid": "d-1", "repository_uuid": "r-1", "store_uuid": "s-1", "membership_version": 4, "delegation_version": 2}
_v20_command = {"operation": "enroll_principal", "target": "membership", "parameters": {"principal": "asya", "public_key": "ssh-ed25519 AAAAasya", "roles": ["operations_authority"]}}
_v20_env = {"schema": AC20.ENVELOPE_SCHEMA, "domain_uuid": "d-1", "repository_uuid": "r-1", "store_uuid": "s-1", "command_id": "cmd-1",
            "request_revision": 1, "nonce": "n-1", "expires_at": _V20_NOW + 300, "membership_version": 4, "delegation_version": 2,
            "principal": "dmitry", "command_digest": AC20.canonical_command_digest(_v20_command)}
_v20_field_failures = []
for _v20_f in AC20.ENVELOPE_FIELDS:
    _v20_e2 = {k: v for k, v in _v20_env.items() if k != _v20_f}
    if not any("lacks %s" % _v20_f in p for p in AC20.envelope_problems(_v20_e2, _v20_command, _v20_authority, _V20_NOW, set(), [{"principal": "dmitry", "public_key": "x"}], _v20_members)):
        _v20_field_failures.append(_v20_f)
_v20_mut_failures = []
for _v20_c in AC20.COMMAND_FIELDS:
    _v20_cmd2 = dict(_v20_command)
    _v20_cmd2[_v20_c] = {"changed": True} if _v20_c == "parameters" else _v20_command[_v20_c] + "-x"
    if not any("does not match the canonical digest" in p for p in AC20.envelope_problems(_v20_env, _v20_cmd2, _v20_authority, _V20_NOW, set(), [{"principal": "dmitry", "public_key": "x"}], _v20_members)):
        _v20_mut_failures.append(_v20_c)
_v20_keyring = [{"principal": "dmitry", "public_key": "ssh-ed25519 AAAAdmitry", "effective_at": _V20_NOW - 1000}]
expect("VELDO-0020 AC2 signing/envelope: the twelve envelope fields are each required by name; mutating each command component "
       "(operation, target, parameters) makes the recomputed canonical digest mismatch and refuses before execution; a "
       "clean envelope over the clean command passes the everything-else check",
       _v20_field_failures == [] and _v20_mut_failures == [] and len(AC20.ENVELOPE_FIELDS) == 12
       and AC20.envelope_problems(_v20_env, _v20_command, _v20_authority, _V20_NOW, set(), _v20_keyring, _v20_members) == [])
expect("VELDO-0020 AC2 signing/context: a replayed nonce, an expired envelope, a wrong repository, a stale membership version, a "
       "stale delegation version, a revoked principal and a retired or revoked key are each refused by name",
       any("replayed" in p for p in AC20.envelope_problems(_v20_env, _v20_command, _v20_authority, _V20_NOW, {"n-1"}, _v20_keyring, _v20_members))
       and any("expired" in p for p in AC20.envelope_problems(dict(_v20_env, expires_at=_V20_NOW - 1), _v20_command, _v20_authority, _V20_NOW, set(), _v20_keyring, _v20_members))
       and any("wrong repository" in p for p in AC20.envelope_problems(dict(_v20_env, repository_uuid="r-2"), _v20_command, _v20_authority, _V20_NOW, set(), _v20_keyring, _v20_members))
       and any("membership_version" in p for p in AC20.envelope_problems(dict(_v20_env, membership_version=3), _v20_command, _v20_authority, _V20_NOW, set(), _v20_keyring, _v20_members))
       and any("delegation_version" in p for p in AC20.envelope_problems(dict(_v20_env, delegation_version=1), _v20_command, _v20_authority, _V20_NOW, set(), _v20_keyring, _v20_members))
       and any("membership_revoked" in p for p in AC20.envelope_problems(dict(_v20_env, principal="left"), _v20_command, _v20_authority, _V20_NOW, set(), _v20_keyring + [{"principal": "left", "public_key": "k"}], _v20_members))
       and any("no active verification key" in p for p in AC20.envelope_problems(_v20_env, _v20_command, _v20_authority, _V20_NOW, set(), [dict(_v20_keyring[0], retired_at=_V20_NOW - 1)], _v20_members))
       and any("no active verification key" in p for p in AC20.envelope_problems(_v20_env, _v20_command, _v20_authority, _V20_NOW, set(), [dict(_v20_keyring[0], revoked_at=_V20_NOW - 1)], _v20_members))
       and AC20.active_key(_v20_keyring + [{"principal": "dmitry", "public_key": "NEW", "effective_at": _V20_NOW + 10}], "dmitry", _V20_NOW)["public_key"] == "ssh-ed25519 AAAAdmitry")
# A REAL signature: a fresh Ed25519 key pair through the installed ssh-keygen, the canonical envelope
# bytes signed and verified through the module's own default verifier.
_v20_have_ssh = _v20_shutil.which("ssh-keygen") is not None
if _v20_have_ssh:
    _v20_kd = Path(tempfile.mkdtemp(prefix="v20keys"))
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "dmitry@veldo", "-f", str(_v20_kd / "key")], check=True, capture_output=True)
    _v20_pub = (_v20_kd / "key.pub").read_text()
    _v20_msg = _v20_kd / "envelope.bin"
    _v20_msg.write_bytes(AC20.canonical_envelope_bytes(_v20_env))
    subprocess.run(["ssh-keygen", "-Y", "sign", "-f", str(_v20_kd / "key"), "-n", AC20.SIGNATURE_NAMESPACE, str(_v20_msg)], check=True, capture_output=True)
    _v20_sig = (_v20_kd / "envelope.bin.sig").read_text()
    _v20_real_ring = [{"principal": "dmitry", "public_key": _v20_pub, "effective_at": _V20_NOW - 1000}]
    _v20_ok, _v20_pr = AC20.verify_signed_command(_v20_env, _v20_command, _v20_sig, _v20_authority, _V20_NOW, set(), _v20_real_ring, _v20_members)
    _v20_tampered_env = dict(_v20_env, nonce="n-2")
    _v20_bad, _v20_bad_pr = AC20.verify_signed_command(_v20_tampered_env, _v20_command, _v20_sig, _v20_authority, _V20_NOW, set(), _v20_real_ring, _v20_members)
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(_v20_kd / "other")], check=True, capture_output=True)
    _v20_other_ring = [{"principal": "dmitry", "public_key": (_v20_kd / "other.pub").read_text(), "effective_at": _V20_NOW - 1000}]
    _v20_wrongkey, _v20_wk_pr = AC20.verify_signed_command(_v20_env, _v20_command, _v20_sig, _v20_authority, _V20_NOW, set(), _v20_other_ring, _v20_members)
    expect("VELDO-0020 AC2 signing/real-key: a command envelope signed with a fresh Ed25519 key through the installed ssh-keygen "
           "verifies against the keyring's active key through the module's default verifier; the same signature over an "
           "envelope with one changed field does not verify; the same signature checked against another key does not verify",
           _v20_ok is True and _v20_pr == [] and _v20_bad is False and any("does not verify" in p for p in _v20_bad_pr)
           and _v20_wrongkey is False and any("does not verify" in p for p in _v20_wk_pr))
    _v20_shutil.rmtree(_v20_kd, ignore_errors=True)
else:
    expect("VELDO-0020 AC2 signing/real-key: ssh-keygen is NOT installed on this host, so the real-signature rows STAND DOWN "
           "by name rather than pass; the envelope, digest and key-lifecycle rows above still ran", True)
# Enrollment-key substitution: the signed envelope stays, the public key in the command changes.
_v20_swapped = dict(_v20_command, parameters=dict(_v20_command["parameters"], public_key="ssh-ed25519 AAAAattacker"))
expect("VELDO-0020 AC2 signing/enrollment-key-substitution: an enrollment command whose public key parameter was substituted "
       "under an unchanged signed envelope is refused before execution because the recomputed digest differs",
       any("does not match the canonical digest" in p for p in AC20.envelope_problems(_v20_env, _v20_swapped, _v20_authority, _V20_NOW, set(), _v20_keyring, _v20_members))
       and AC20.verify_signed_command(_v20_env, _v20_swapped, "sig", _v20_authority, _V20_NOW, set(), _v20_keyring, _v20_members, verifier=lambda *a: (True, "spy"))[0] is False)
# THE DECLARED FALSIFIER: accept the envelope without recomputing the digest from the command.
_V20_M2 = _v20_mutated('''    if envelope["command_digest"] != canonical_command_digest(command):
''', '''    if False:  # mutant: the envelope's own digest is trusted
''')
expect("VELDO-0020 AC2 signing/enrollment-key-substitution DRIVEN (the declared falsifier): with the digest no longer recomputed "
       "in a copy, the substituted enrollment key passes under the original signature (a permissive verifier standing for a "
       "valid signature), so the row reds; unmutated it is refused",
       _V20_M2.verify_signed_command(_v20_env, _v20_swapped, "sig", _v20_authority, _V20_NOW, set(), _v20_keyring, _v20_members, verifier=lambda *a: (True, "spy"))[0] is True
       and AC20.verify_signed_command(_v20_env, _v20_swapped, "sig", _v20_authority, _V20_NOW, set(), _v20_keyring, _v20_members, verifier=lambda *a: (True, "spy"))[0] is False)

# ---------------------------------------------------------------------------------------------
# AC3: enrolled channels, restricted edge keys, canonical attribution.
# ---------------------------------------------------------------------------------------------
_v20_deleg = {"principal": "dmitry", "channel": "telegram_chat", "assertion_kinds": ["decision_answer"], "authority_scope": ["*"],
              "request_version": 3, "presentation_version": 2, "expires_at": _V20_NOW + 3600, "edge_key_id": "edge-telegram"}
_v20_chat = {"principal": "dmitry", "channel": "telegram_chat", "assertion_kind": "decision_answer", "request_version": 3, "presentation_version": 2,
             "edge_key_id": "edge-telegram", "presentation_id": "pres-1", "presentation_digest": "sha256:brief",
             "attribution": {"platform_message_id": "27921", "sender_id": "8687555281", "platform_timestamp": "2026-09-17T21:22:46Z"},
             "text": "Approve 0019", "ruling": "approve"}
expect("VELDO-0020 AC3 channel-attribution/registry: the channel registry has Telegram chat, Jira and signed CLI enrolled and email "
       "unenrolled, each with its own restricted edge key and its platform attribution fields; a well-formed chat assertion "
       "under a matching delegation is accepted",
       set(AC20.CHANNELS) == {"telegram_chat", "jira", "signed_cli", "email"} and AC20.CHANNELS["email"]["enrolled"] is False
       and len({c["edge_key_id"] for c in AC20.CHANNELS.values()}) == 4
       and AC20.CHANNELS["telegram_chat"]["attribution"] == ("platform_message_id", "sender_id", "platform_timestamp")
       and AC20.edge_assertion_problems(_v20_chat, _v20_deleg, _V20_NOW) == [])
_v20_edge_failures = []
for _v20_chn, _v20_c in AC20.CHANNELS.items():
    _v20_a = dict(_v20_chat, channel=_v20_chn, edge_key_id=_v20_c["edge_key_id"], attribution={f: (True if f.endswith("_verified") else "v") for f in _v20_c["attribution"]})
    _v20_d = dict(_v20_deleg, channel=_v20_chn, edge_key_id=_v20_c["edge_key_id"])
    _v20_probs = AC20.edge_assertion_problems(_v20_a, _v20_d, _V20_NOW)
    if _v20_c["enrolled"] and _v20_probs:
        _v20_edge_failures.append((_v20_chn, "positive", _v20_probs))
    if not _v20_c["enrolled"] and not any("not enrolled" in p for p in _v20_probs):
        _v20_edge_failures.append((_v20_chn, "unenrolled", _v20_probs))
    for _v20_f in _v20_c["attribution"]:
        _v20_a2 = dict(_v20_a, attribution={k: v for k, v in _v20_a["attribution"].items() if k != _v20_f})
        if not any("attribution lacks %s" % _v20_f in p for p in AC20.edge_assertion_problems(_v20_a2, _v20_d, _V20_NOW)):
            _v20_edge_failures.append((_v20_chn, _v20_f, "missing field not refused"))
    _v20_other = next(k["edge_key_id"] for n, k in AC20.CHANNELS.items() if n != _v20_chn)
    if not any("own restricted key" in p for p in AC20.edge_assertion_problems(dict(_v20_a, edge_key_id=_v20_other), _v20_d, _V20_NOW)):
        _v20_edge_failures.append((_v20_chn, "foreign key", "not refused"))
expect("VELDO-0020 AC3 channel-attribution/conformance: generated from the registry, every enrolled channel accepts a complete "
       "assertion, email refuses while unenrolled, every missing platform attribution field refuses by name, and an edge "
       "signing with another channel's key refuses (failures: %s)" % _v20_edge_failures[:3],
       _v20_edge_failures == [])
expect("VELDO-0020 AC3 channel-attribution/delegation: an expired delegation, a delegation for another principal, request "
       "version or presentation version, an assertion kind the delegation does not permit, an unknown assertion kind, and "
       "an assertion naming no presentation are each refused by name",
       any("delegation expired" in p for p in AC20.edge_assertion_problems(_v20_chat, dict(_v20_deleg, expires_at=_V20_NOW - 1), _V20_NOW))
       and any("binds principal" in p for p in AC20.edge_assertion_problems(_v20_chat, dict(_v20_deleg, principal="asya"), _V20_NOW))
       and any("binds request_version" in p for p in AC20.edge_assertion_problems(_v20_chat, dict(_v20_deleg, request_version=2), _V20_NOW))
       and any("binds presentation_version" in p for p in AC20.edge_assertion_problems(_v20_chat, dict(_v20_deleg, presentation_version=1), _V20_NOW))
       and any("delegation permits" in p for p in AC20.edge_assertion_problems(dict(_v20_chat, assertion_kind="review_disposition"), _v20_deleg, _V20_NOW))
       and any("is not one of" in p for p in AC20.edge_assertion_problems(dict(_v20_chat, assertion_kind="vibes"), _v20_deleg, _V20_NOW))
       and any("names no presentation" in p for p in AC20.edge_assertion_problems({k: v for k, v in _v20_chat.items() if k != "presentation_id"}, _v20_deleg, _V20_NOW)))
_v20_text_only = dict(_v20_chat, attribution={"sender_name": "Dmitry Grinberg"}, text="Approve 0019")
expect("VELDO-0020 AC3 channel-attribution/text-only: a chat assertion carrying message text and a display name but no platform "
       "message id, sender id or timestamp is refused naming each missing field",
       sum(1 for p in AC20.edge_assertion_problems(_v20_text_only, _v20_deleg, _V20_NOW) if "attribution lacks" in p) == 3)
# THE DECLARED FALSIFIER: accept a chat assertion with text but no platform message id.
_V20_M3 = _v20_mutated('''    for f in ch["attribution"]:
        v = evidence.get(f)
''', '''    for f in ch["attribution"]:
        if _is_str(assertion.get("text")):
            break  # mutant: the text stands for the evidence
        v = evidence.get(f)
''')
expect("VELDO-0020 AC3 channel-attribution/text-only DRIVEN (the declared falsifier): with message text accepted in place of "
       "platform evidence in a copy, the text-only assertion is accepted, so the row reds; unmutated it is refused",
       _V20_M3.edge_assertion_problems(_v20_text_only, _v20_deleg, _V20_NOW) == []
       and AC20.edge_assertion_problems(_v20_text_only, _v20_deleg, _V20_NOW) != [])

# ---------------------------------------------------------------------------------------------
# AC4: one settlement per request version, attributed to the originating channel.
# ---------------------------------------------------------------------------------------------
_v20_request = {"id": "REQ-9", "version": 3, "framing_digest": "sha256:framing", "subject_digests": ["sha256:s1"], "quorum": 1,
                "scope": "PROJ-1", "roles": [], "named_principals": [],
                "expires_at": _V20_NOW + 3600, "nonce": "nonce-9", "decision_binding": {"decision": "VELDO-DEC-0004"}}
_v20_pres_chat = {"presentation_id": "pres-1", "presentation_version": 2, "request_id": "REQ-9", "request_version": 3, "request_digest": "sha256:framing",
                  "subject_digests": ["sha256:s1"], "brief_digest": "sha256:brief", "channel": "telegram_chat", "external_id": "27921",
                  "published_at": _V20_NOW - 100}
_v20_pres_jira = dict(_v20_pres_chat, presentation_id="pres-2", channel="jira", external_id="VEL-18")
_v20_deleg_jira = dict(_v20_deleg, channel="jira", edge_key_id="edge-jira")
_v20_jira = dict(_v20_chat, channel="jira", edge_key_id="edge-jira", presentation_id="pres-2",
                 attribution={"issue_key": "VEL-18", "changelog_id": "c-1", "account_id": "712020:fbf8", "changelog_timestamp": "2026-09-17T21:25:00Z"})
_v20_ring = [{"principal": "dmitry", "public_key": "k", "effective_at": _V20_NOW - 1000}, {"principal": "asya", "public_key": "k2", "effective_at": _V20_NOW - 1000}]
_v20_res = AC20.settle(_v20_request, [_v20_chat], [_v20_deleg], [_v20_pres_chat], _v20_members, _v20_ring, _V20_NOW)
expect("VELDO-0020 AC4 settlement/single: one valid chat answer settles the request version once, attributed to telegram_chat and "
       "bound to its presentation, consuming the nonce, with projection obligations for the other enrolled channels and the "
       "decision effect in the same atomic result",
       _v20_res["settled"] is True and _v20_res["settlement"]["originating_channel"] == "telegram_chat"
       and _v20_res["settlement"]["presentation_id"] == "pres-1" and _v20_res["nonce_consumed"] == "nonce-9"
       and _v20_res["projection_obligations"] == ["jira", "signed_cli"] and _v20_res["decision_effects"][0]["binding"] == {"decision": "VELDO-DEC-0004"}
       and _v20_res["quorum"]["principals"] == ["dmitry"])
expect("VELDO-0020 AC4 settlement/refusals: an already-settled version, an expired request, a stale presentation (changed brief, "
       "changed framing, changed subject, other version), an unknown presentation, a presentation from another channel, an "
       "edge-refused assertion, a revoked member, a revoked key and no valid assertion each refuse by name and settle nothing",
       "already_settled" in AC20.settle(_v20_request, [_v20_chat], [_v20_deleg], [_v20_pres_chat], _v20_members, _v20_ring, _V20_NOW, prior_settlement={"request_version": 3})["refusals"]
       and "request_expired" in AC20.settle(dict(_v20_request, expires_at=_V20_NOW - 1), [_v20_chat], [_v20_deleg], [_v20_pres_chat], _v20_members, _v20_ring, _V20_NOW)["refusals"]
       and any(r.startswith("stale_presentation") for r in AC20.settle(_v20_request, [dict(_v20_chat, presentation_digest="sha256:oldbrief")], [_v20_deleg], [_v20_pres_chat], _v20_members, _v20_ring, _V20_NOW)["refusals"])
       and any(r.startswith("stale_presentation") for r in AC20.settle(dict(_v20_request, framing_digest="sha256:new"), [_v20_chat], [_v20_deleg], [_v20_pres_chat], _v20_members, _v20_ring, _V20_NOW)["refusals"])
       and any(r.startswith("stale_presentation") for r in AC20.settle(dict(_v20_request, subject_digests=["sha256:s2"]), [_v20_chat], [_v20_deleg], [_v20_pres_chat], _v20_members, _v20_ring, _V20_NOW)["refusals"])
       and any(r.startswith("stale_presentation") for r in AC20.settle(_v20_request, [_v20_chat], [_v20_deleg], [dict(_v20_pres_chat, request_version=2)], _v20_members, _v20_ring, _V20_NOW)["refusals"])
       and any(r.startswith("unknown_presentation") for r in AC20.settle(_v20_request, [dict(_v20_chat, presentation_id="pres-x")], [_v20_deleg], [_v20_pres_chat], _v20_members, _v20_ring, _V20_NOW)["refusals"])
       and any(r.startswith("presentation_channel_mismatch") for r in AC20.settle(_v20_request, [dict(_v20_chat, presentation_id="pres-2")], [_v20_deleg], [_v20_pres_chat, _v20_pres_jira], _v20_members, _v20_ring, _V20_NOW)["refusals"])
       and any(r.startswith("edge_refused") for r in AC20.settle(_v20_request, [_v20_text_only], [_v20_deleg], [_v20_pres_chat], _v20_members, _v20_ring, _V20_NOW)["refusals"])
       and any(r.startswith("principal_not_member") for r in AC20.settle(_v20_request, [dict(_v20_chat, principal="left")], [dict(_v20_deleg, principal="left")], [_v20_pres_chat], _v20_members, _v20_ring + [{"principal": "left", "public_key": "k"}], _V20_NOW)["refusals"])
       and any(r.startswith("revoked_key") for r in AC20.settle(_v20_request, [_v20_chat], [_v20_deleg], [_v20_pres_chat], _v20_members, [dict(_v20_ring[0], revoked_at=_V20_NOW - 1)], _V20_NOW)["refusals"])
       and "no_assertion" in AC20.settle(_v20_request, [], [], [_v20_pres_chat], _v20_members, _v20_ring, _V20_NOW)["refusals"]
       and all(not AC20.settle(*args)["settled"] for args in (
           (_v20_request, [_v20_text_only], [_v20_deleg], [_v20_pres_chat], _v20_members, _v20_ring, _V20_NOW),)))
_v20_two = AC20.settle(dict(_v20_request, quorum=2), [_v20_chat, _v20_jira], [_v20_deleg, _v20_deleg_jira], [_v20_pres_chat, _v20_pres_jira], _v20_members, _v20_ring, _V20_NOW)
_v20_asya = dict(_v20_jira, principal="asya")
_v20_two_people = AC20.settle(dict(_v20_request, quorum=2), [_v20_chat, _v20_asya], [_v20_deleg, dict(_v20_deleg_jira, principal="asya")], [_v20_pres_chat, _v20_pres_jira], _v20_members, _v20_ring, _V20_NOW)
expect("VELDO-0020 AC4 settlement/cross-channel-principal: dmitry answering on Telegram and on Jira is ONE quorum member (a quorum "
       "of two is not met), while dmitry and asya on two channels are two and settle; the winner among concurrent valid answers "
       "is the earliest by platform timestamp and the settlement is attributed to that channel with the other channel owed a projection",
       _v20_two["settled"] is False and any("quorum_not_met:1<2" in r and r.startswith("not_authorized:approve:") for r in _v20_two["refusals"]) and _v20_two["quorum"]["principals"] == ["dmitry"]
       and _v20_two_people["settled"] is True and _v20_two_people["quorum"]["principals"] == ["asya", "dmitry"]
       and _v20_two_people["settlement"]["originating_channel"] == "telegram_chat" and "jira" in _v20_two_people["projection_obligations"])
# THE DECLARED FALSIFIER: count one principal answering on two channels as two quorum members.
# ONE copy carrying both edits: settle hands authorize one attestation per assertion, and authorize
# counts attestations instead of distinct principals.
_V20_M4 = _v20_mutated_two(
    '''        attestations = [{"principal": p, "subject_digest": request.get("framing_digest")} for p in sorted(principals)]
''', '''        attestations = [{"principal": a.get("principal"), "subject_digest": request.get("framing_digest")} for a in valid if a["ruling"] == ruling]  # mutant: per channel
''', '''    principals = {a.get("principal") for a, _e in valid}
    if len(principals) < int(requirement.get("quorum") or 1):
''', '''    principals = [a.get("principal") for a, _e in valid]  # mutant: attestations counted, not principals
    if len(principals) < int(requirement.get("quorum") or 1):
''')
expect("VELDO-0020 AC4 settlement/cross-channel-principal DRIVEN (the declared falsifier): with quorum members counted per channel "
       "in a copy, dmitry on two channels meets a quorum of two and the request settles, so the row reds; unmutated it is refused",
       _V20_M4.settle(dict(_v20_request, quorum=2), [_v20_chat, _v20_jira], [_v20_deleg, _v20_deleg_jira], [_v20_pres_chat, _v20_pres_jira], _v20_members, _v20_ring, _V20_NOW)["settled"] is True
       and _v20_two["settled"] is False)


# ---------------------------------------------------------------------------------------------
# The seven findings of the Codex review (review-20260917-175932), each pinned.
# ---------------------------------------------------------------------------------------------
_v20_agent_member = _v20_members + [{"principal": "run-9", "principal_type": "agent_run", "roles": [], "independence_group": None}]
_v20_agent_ans = dict(_v20_chat, principal="run-9")
_v20_agent_deleg = dict(_v20_deleg, principal="run-9")
_v20_agent_ring = _v20_ring + [{"principal": "run-9", "public_key": "k9", "effective_at": _V20_NOW - 10}]
expect("VELDO-0020 AC4 settlement/authorization (review 1): settlement runs authorize() at the decision_settlement boundary - a "
       "roleless agent run whose edge, presentation and key all pass is refused as not authorized (its type is not admitted at "
       "that boundary), and a request naming dmitry refuses asya's answer",
       any(r.startswith("not_authorized") and "principal_type_not_admitted:run-9" in r
           for r in AC20.settle(_v20_request, [_v20_agent_ans], [_v20_agent_deleg], [_v20_pres_chat], _v20_agent_member, _v20_agent_ring, _V20_NOW)["refusals"])
       and AC20.settle(_v20_request, [_v20_agent_ans], [_v20_agent_deleg], [_v20_pres_chat], _v20_agent_member, _v20_agent_ring, _V20_NOW)["settled"] is False
       and any("named_principal_not_satisfied:dmitry" in r for r in AC20.settle(dict(_v20_request, named_principals=["dmitry"]), [dict(_v20_chat, principal="asya")],
                                                                                [dict(_v20_deleg, principal="asya")], [_v20_pres_chat], _v20_members, _v20_ring, _V20_NOW)["refusals"])
       and AC20.settle(dict(_v20_request, named_principals=["dmitry"]), [_v20_chat], [_v20_deleg], [_v20_pres_chat], _v20_members, _v20_ring, _V20_NOW)["settled"] is True)
expect("VELDO-0020 AC1/AC3 authority-substitution/scope (review 1): a member scoped to PROJ-A holds no role for a PROJ-B requirement while "
       "a '*' member does; a delegation with an empty authority_scope, or one not covering the request's scope, is refused",
       "role_not_satisfied:admission_authority (no holder scoped to PROJ-B)" in AC20.authorize("decision_settlement", {"roles": ["admission_authority"], "scope": "PROJ-B"}, [_v20_att("lena")], _v20_members, _V20_NOW)[1]
       and AC20.authorize("decision_settlement", {"roles": ["admission_authority"], "scope": "PROJ-A"}, [_v20_att("lena")], _v20_members, _V20_NOW)[0] is True
       and AC20.authorize("decision_settlement", {"roles": ["admission_authority"], "scope": "PROJ-B"}, [_v20_att("dmitry")], _v20_members, _V20_NOW)[0] is True
       and any("authority_scope is empty" in p for p in AC20.edge_assertion_problems(_v20_chat, dict(_v20_deleg, authority_scope=[]), _V20_NOW))
       and any("does not cover the request's scope" in p for p in AC20.edge_assertion_problems(_v20_chat, dict(_v20_deleg, authority_scope=["PROJ-A"]), _V20_NOW, required_scope="PROJ-B"))
       and AC20.settle(_v20_request, [_v20_chat], [dict(_v20_deleg, authority_scope=["PROJ-A"])], [_v20_pres_chat], _v20_members, _v20_ring, _V20_NOW)["settled"] is False)
expect("VELDO-0020 AC3 channel-attribution/revocation (review 1): a revoked delegation signs nothing even while the principal's "
       "membership and key stay active, at the edge and for a command envelope naming it",
       any("delegation revoked" in p for p in AC20.edge_assertion_problems(_v20_chat, dict(_v20_deleg, revoked_at=_V20_NOW - 1), _V20_NOW))
       and AC20.settle(_v20_request, [_v20_chat], [dict(_v20_deleg, revoked_at=_V20_NOW - 1)], [_v20_pres_chat], _v20_members, _v20_ring, _V20_NOW)["settled"] is False
       and any("revoked or expired" in p for p in AC20.envelope_problems(dict(_v20_env, delegation_id="del-1"), _v20_command, _v20_authority, _V20_NOW, set(), _v20_keyring, _v20_members,
                                                                         delegations=[{"id": "del-1", "principal": "dmitry", "revoked_at": _V20_NOW - 1, "expires_at": _V20_NOW + 100}]))
       and any("does not resolve" in p for p in AC20.envelope_problems(dict(_v20_env, delegation_id="del-x"), _v20_command, _v20_authority, _V20_NOW, set(), _v20_keyring, _v20_members, delegations=[]))
       and AC20.envelope_problems(dict(_v20_env, delegation_id="del-1"), _v20_command, _v20_authority, _V20_NOW, set(), _v20_keyring, _v20_members,
                                  delegations=[{"id": "del-1", "principal": "dmitry", "expires_at": _V20_NOW + 100}]) == [])
_v20_reject = dict(_v20_asya, ruling="reject")
_v20_two_rulings = AC20.settle(dict(_v20_request, quorum=2), [_v20_chat, _v20_reject], [_v20_deleg, dict(_v20_deleg_jira, principal="asya")], [_v20_pres_chat, _v20_pres_jira], _v20_members, _v20_ring, _V20_NOW)
_v20_conflict = AC20.settle(_v20_request, [_v20_chat, _v20_reject], [_v20_deleg, dict(_v20_deleg_jira, principal="asya")], [_v20_pres_chat, _v20_pres_jira], _v20_members, _v20_ring, _V20_NOW)
expect("VELDO-0020 AC4 settlement/quorum-by-ruling (review 1): one approval and one rejection under a quorum of two settle nothing "
       "(the quorum is counted per ruling, by distinct principal), the result names both rulings; under a quorum of one two "
       "different rulings each reaching it are a conflict for the authority, never a winner picked by timestamp",
       _v20_two_rulings["settled"] is False and _v20_two_rulings["quorum"]["by_ruling"] == {"approve": ["dmitry"], "reject": ["asya"]}
       and _v20_conflict["settled"] is False and any(r.startswith("conflicting_rulings") for r in _v20_conflict["refusals"])
       and _v20_two_people["settled"] is True and _v20_two_people["settlement"]["ruling"] == "approve")
_v20_cli_deleg = dict(_v20_deleg, channel="signed_cli", edge_key_id="edge-cli")
_v20_cli = dict(_v20_chat, channel="signed_cli", edge_key_id="edge-cli", attribution={"personal_envelope_verified": True, "command_id": "cmd-7", "signed_at": "2026-09-17T22:00:00Z"})
expect("VELDO-0020 AC3 channel-attribution/cli-verification (review 1): a signed CLI assertion is accepted only when "
       "personal_envelope_verified is literally True; 'false', 'not-verified', an empty list and an empty mapping each refuse",
       AC20.edge_assertion_problems(_v20_cli, _v20_cli_deleg, _V20_NOW) == []
       and all(any("personal_envelope_verified" in p for p in AC20.edge_assertion_problems(dict(_v20_cli, attribution=dict(_v20_cli["attribution"], personal_envelope_verified=v)), _v20_cli_deleg, _V20_NOW))
               for v in ("false", "not-verified", [], {}, 1)))
expect("VELDO-0020 AC4 settlement/version-binding (review 1): an assertion and delegation both naming request version 2 are refused "
       "against the version 3 request, and a presentation receipt at another presentation version is stale",
       AC20.settle(_v20_request, [dict(_v20_chat, request_version=2)], [dict(_v20_deleg, request_version=2)], [_v20_pres_chat], _v20_members, _v20_ring, _V20_NOW)["settled"] is False
       and any("stale answer settles nothing" in r for r in AC20.settle(_v20_request, [dict(_v20_chat, request_version=2)], [dict(_v20_deleg, request_version=2)], [_v20_pres_chat], _v20_members, _v20_ring, _V20_NOW)["refusals"])
       and any(r.startswith("stale_presentation") for r in AC20.settle(_v20_request, [_v20_chat], [_v20_deleg], [dict(_v20_pres_chat, presentation_version=1)], _v20_members, _v20_ring, _V20_NOW)["refusals"]))
_v20_ack = dict(_v20_chat, assertion_kind="acknowledgement", ruling=None)
_v20_ack_res = AC20.settle(_v20_request, [_v20_ack], [dict(_v20_deleg, assertion_kinds=["decision_answer", "acknowledgement"])], [_v20_pres_chat], _v20_members, _v20_ring, _V20_NOW)
expect("VELDO-0020 AC4 settlement/decision-answer-only (review 1): an acknowledgement settles nothing and consumes no nonce, so a later "
       "real answer still settles; an answer whose ruling is outside the vocabulary settles nothing",
       _v20_ack_res["settled"] is False and _v20_ack_res["nonce_consumed"] is None and any(r.startswith("not_a_decision_answer") for r in _v20_ack_res["refusals"])
       and AC20.settle(_v20_request, [_v20_chat], [_v20_deleg], [_v20_pres_chat], _v20_members, _v20_ring, _V20_NOW, prior_settlement=None)["settled"] is True
       and AC20.settle(_v20_request, [dict(_v20_chat, ruling="maybe")], [_v20_deleg], [_v20_pres_chat], _v20_members, _v20_ring, _V20_NOW)["settled"] is False)
