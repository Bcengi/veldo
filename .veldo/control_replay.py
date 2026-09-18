#!/usr/bin/env python3
"""Deterministic replay of the signed journal (PLAN-0019 W8, VELDO-0023 AC3, R22, R53).

WHAT THIS MODULE IS. A reader that rebuilds materialized domain state from verified, versioned,
canonical journal records and nothing else: no live SQLite, no execution runtime, no other Veldo
organ. It verifies, in order, that the encoding is one it knows, that sequence numbers run 1, 2, 3
with no gap, duplicate or reorder, that every record's previous-record digest is the digest of the
record before it (the first names the genesis digest), that every record digest recomputes from
the record's own fields, and that every signature verifies through the callable the caller
supplies (OpenSSH in production) against the record's signed bytes. Only then does it apply the
transitions, checking each before-version against the state it has built, and it returns the
rebuilt state with its digest for comparison with the live store's state_digest. Any invalid
history refuses reconstruction by name and rebuilds nothing: no invalid history may rebuild
writable authority.

Standard library only; imports nothing but hashlib and json.
"""
import hashlib
import json

SCHEMA = "veldo.control_replay/v1"
SUPPORTED_ENCODINGS = ("veldo.journal/v1",)
GENESIS_DIGEST = "sha256:genesis"
JOURNAL_FIELDS = ("seq", "prev_digest", "authority_generation", "command_id", "command_digest", "principal", "signer",
                  "before_versions", "after_versions", "transition", "nonce", "reservations", "effects", "receipt_refs", "artifact_digests", "encoding")
STATE_PARTS = ("entities", "reservations", "effects", "nonces")
JOURNAL_SIGNED_FIELDS = JOURNAL_FIELDS + ("record_digest",)
REFUSALS = ("invalid_journal", "unsupported_encoding", "sequence_broken", "chain_broken", "digest_mismatch", "signature_invalid",
            "transition_inconsistent", "state_mismatch")


class ReplayRefused(Exception):
    """Reconstruction refused by name (one of REFUSALS) at a record; no state is returned."""

    def __init__(self, code, seq, detail):
        super().__init__("%s at seq %r: %s" % (code, seq, detail))
        self.code, self.seq, self.detail = code, seq, detail


def canonical_bytes(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")


def digest_of(obj):
    return "sha256:" + hashlib.sha256(canonical_bytes(obj)).hexdigest()


def record_digest(record):
    return digest_of({k: record.get(k) for k in JOURNAL_FIELDS})


def signed_bytes(record):
    return canonical_bytes({k: record.get(k) for k in JOURNAL_SIGNED_FIELDS})


def state_digest(state):
    return digest_of({part: state.get(part, {}) for part in STATE_PARTS})


def verify_chain(records, verify):
    """Verify the whole chain before applying any of it. `verify(message_bytes, signature_text,
    signer) -> (ok, detail)`. Refuses by name at the first bad record."""
    if not isinstance(records, list):
        raise ReplayRefused("invalid_journal", None, "the journal is a list of records")
    prev = GENESIS_DIGEST
    for i, rec in enumerate(records):
        expected_seq = i + 1
        if not isinstance(rec, dict):
            raise ReplayRefused("invalid_journal", expected_seq, "record is not a mapping")
        missing = [f for f in JOURNAL_SIGNED_FIELDS + ("signature",) if f not in rec]
        if missing:
            raise ReplayRefused("invalid_journal", rec.get("seq", expected_seq), "record lacks %s" % ", ".join(missing))
        if rec["encoding"] not in SUPPORTED_ENCODINGS:
            raise ReplayRefused("unsupported_encoding", rec["seq"], "encoding %r is not one this reader knows (%s)" % (rec["encoding"], ", ".join(SUPPORTED_ENCODINGS)))
        if rec["seq"] != expected_seq:
            raise ReplayRefused("sequence_broken", rec["seq"], "expected seq %d (records run 1, 2, 3 with no gap, duplicate or reorder)" % expected_seq)
        if rec["prev_digest"] != prev:
            raise ReplayRefused("chain_broken", rec["seq"], "prev_digest %s is not the digest of the record before it (%s)" % (rec["prev_digest"], prev))
        if record_digest(rec) != rec["record_digest"]:
            raise ReplayRefused("digest_mismatch", rec["seq"], "record_digest %s does not recompute from the record's fields (%s)" % (rec["record_digest"], record_digest(rec)))
        ok, detail = verify(signed_bytes(rec), rec["signature"], rec["signer"])
        if ok is not True:
            raise ReplayRefused("signature_invalid", rec["seq"], "signature by %r does not verify: %s" % (rec["signer"], detail))
        prev = rec["record_digest"]
    return prev


def replay(records, verify):
    """Verify the chain, then rebuild the whole domain state deterministically: entities from the
    transitions (each record's before-versions checked against the state built so far, each
    transition's own digest recomputed), reservations, effects and consumed nonces from the record
    (a nonce, reservation or effect seen twice is inconsistent). Returns {"state", "state_digest",
    "head_digest", "records"} with state keyed by STATE_PARTS."""
    head = verify_chain(records, verify)
    state = {part: {} for part in STATE_PARTS}
    ents = state["entities"]
    for rec in records:
        if rec["nonce"] in state["nonces"]:
            raise ReplayRefused("transition_inconsistent", rec["seq"], "nonce %r was already consumed by %s" % (rec["nonce"], state["nonces"][rec["nonce"]]))
        state["nonces"][rec["nonce"]] = rec["command_id"]
        for r in rec["reservations"]:
            if r["id"] in state["reservations"]:
                raise ReplayRefused("transition_inconsistent", rec["seq"], "reservation %s recorded twice" % r["id"])
            state["reservations"][r["id"]] = {"command_id": rec["command_id"], "ceiling": r["ceiling"], "delta": r["delta"]}
        for e in rec["effects"]:
            if e["id"] in state["effects"]:
                raise ReplayRefused("transition_inconsistent", rec["seq"], "effect %s recorded twice" % e["id"])
            state["effects"][e["id"]] = {"command_id": rec["command_id"], "kind": e["kind"], "target": e["target"], "state": e["state"]}
        for eid, v in rec["before_versions"].items():
            have = ents.get(eid, {}).get("version", 0)
            if have != v:
                raise ReplayRefused("transition_inconsistent", rec["seq"], "record says %s was at version %r before it, the rebuilt state has %r" % (eid, v, have))
        for eid, t in rec["transition"].items():
            if rec["after_versions"].get(eid) != t.get("version") or t.get("version") != rec["before_versions"].get(eid, 0) + 1:
                raise ReplayRefused("transition_inconsistent", rec["seq"], "entity %s: after version %r, transition version %r, before %r do not agree"
                                    % (eid, rec["after_versions"].get(eid), t.get("version"), rec["before_versions"].get(eid, 0)))
            if digest_of({"kind": t.get("kind"), "data": t.get("data"), "version": t.get("version")}) != t.get("digest"):
                raise ReplayRefused("transition_inconsistent", rec["seq"], "entity %s: the transition's digest does not recompute from its kind, data and version" % eid)
            ents[eid] = {"kind": t["kind"], "version": t["version"], "digest": t["digest"], "data": t["data"]}
        for eid, v in rec["after_versions"].items():
            if ents.get(eid, {}).get("version", 0) != v:
                raise ReplayRefused("transition_inconsistent", rec["seq"], "record says %s is at version %r after it, the rebuilt state has %r" % (eid, v, ents.get(eid, {}).get("version", 0)))
    return {"state": state, "state_digest": state_digest(state), "head_digest": head, "records": len(records)}


def compare_with_live(rebuilt, live_state):
    """The replay's verdict against a live materialized state: equal digests, or a named
    state_mismatch listing the entities that differ."""
    live_digest = state_digest(live_state)
    if rebuilt["state_digest"] == live_digest:
        return {"matches": True, "digest": live_digest, "differences": []}
    diffs = []
    for part in STATE_PARTS:
        a, b = rebuilt["state"].get(part, {}), live_state.get(part, {})
        diffs += ["%s:%s" % (part, k) for k in sorted(set(a) ^ set(b))] + ["%s:%s" % (part, k) for k in sorted(set(a) & set(b)) if a[k] != b[k]]
    return {"matches": False, "rebuilt_digest": rebuilt["state_digest"], "live_digest": live_digest, "differences": diffs}
