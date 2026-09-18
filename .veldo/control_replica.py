#!/usr/bin/env python3
"""Signed Git replication and off-host acknowledgement (PLAN-0019 W9, VELDO-0024, R23, R26, R27).

WHAT THIS MODULE IS. The exporter that turns each committed journal record into ONE signed
immutable export (the record, its signature and the BYTES of every newly referenced artifact,
never only their locations) and publishes the exports in sequence to a dedicated protected ref
(refs/veldo/audit) on the repository's existing remote, as an audit and recovery replica: not a
second writable authority, not a message queue. The export's identity is a pure function of the
journal record (sequence and record digest), so a retry after any crash reuses the SAME identity;
a fresh identity for an already committed sequence cannot be allocated. Each export is one Git
commit in a local bare audit repository whose parent is the previous export's commit, pushed with
a compare-and-swap lease on the exact expected old tip; the acknowledgement is the remote's own
answer (ls-remote) that the ref now names that commit, persisted through the control store's
publication cursor. Mutation SUCCESS, external dispatch and dependent publication are withheld
until that acknowledgement exists: command_outcome() answers pending_publication, never success
and never rejected, for a committed command whose export has no acknowledgement. Recovery
reconciles a lost acknowledgement against the exact remote ref and export digest; a remote tip
that is not in the local export chain STOPS publication (PAUSED_PUBLICATION, divergent) and
nothing is overwritten.

WHAT IT IS NOT. It creates no live remote and proves nothing about surviving authority-host loss:
a local bare remote qualifies the PROTOCOL only, and remote_contract_problems() says so by name.
Source landing stays the lander's; host restoration is W33. Standard library only; Git and
OpenSSH are invoked as installed programs.

CRASH POINTS. Under VELDO_CONTROL_TEST_HARNESS=1 a publisher process may SIGKILL itself after the
export is prepared (audit commit made, nothing pushed), after the remote ref moved (nothing
acknowledged locally), or after the acknowledgement persisted (no reply). Every window is
reconciled by reconcile() on restart.
"""
import base64
import hashlib
import json
import os
import signal
import subprocess

SCHEMA = "veldo.control_replica/v1"
EXPORT_ENCODING = "veldo.export/v1"
AUDIT_REF = "refs/veldo/audit"
SIGNATURE_NAMESPACE = "veldo-export"
REFUSALS = ("remote_rejected", "remote_unreachable", "divergent_replica", "export_identity_mismatch", "artifact_missing",
            "unsigned_export", "remote_unqualified", "store_read_only")
KILL_POINTS = ("after_export_prepared", "after_remote_ref_updated", "after_ack_persisted")


class ReplicaRefused(Exception):
    def __init__(self, code, detail):
        super().__init__("%s: %s" % (code, detail))
        self.code, self.detail = code, detail


def _is_str(v):
    return isinstance(v, str) and v.strip() != ""


def canonical_bytes(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")


def digest_of_bytes(b):
    return "sha256:" + hashlib.sha256(b).hexdigest()


def _kill_point(name):
    if os.environ.get("VELDO_CONTROL_TEST_HARNESS") == "1" and os.environ.get("VELDO_REPLICA_KILL_AT") == name:
        os.kill(os.getpid(), signal.SIGKILL)


def _git_env():
    env = dict(os.environ)
    env.update({"GIT_AUTHOR_NAME": "veldo-authority", "GIT_AUTHOR_EMAIL": "authority@veldo.local",
                "GIT_COMMITTER_NAME": "veldo-authority", "GIT_COMMITTER_EMAIL": "authority@veldo.local",
                "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull, "GIT_TERMINAL_PROMPT": "0"})
    return env


def _git(args, cwd, input_bytes=None, check=True, timeout=60):
    r = subprocess.run(["git"] + list(args), cwd=cwd, input=input_bytes, capture_output=True, env=_git_env(), timeout=timeout, stdin=None if input_bytes is not None else subprocess.DEVNULL)
    if check and r.returncode != 0:
        raise subprocess.CalledProcessError(r.returncode, r.args, r.stdout, r.stderr)
    return r


# ---------------------------------------------------------------------------------------------
# The export: identity, content, signature.
# ---------------------------------------------------------------------------------------------

def export_identity(record):
    """The ONE identity of a record's export: a function of sequence and record digest and nothing
    else, so any retry names the same export and a second export for one sequence is impossible
    without changing the record itself."""
    return "export-%08d-%s" % (int(record["seq"]), record["record_digest"].split(":", 1)[1][:24])


def build_export(record, artifact_bytes):
    """The immutable export of one journal record: the record (every signed field and its
    signature), the encoding, and the BYTES of every artifact the record references, each keyed by
    its digest and checked against it (a location is not an artifact; a digest that does not match
    its bytes is refused). `artifact_bytes(digest) -> bytes or None`."""
    artifacts = {}
    for d in record.get("artifact_digests") or []:
        b = artifact_bytes(d)
        if b is None:
            raise ReplicaRefused("artifact_missing", "artifact %s referenced by seq %s has no bytes to export" % (d, record["seq"]))
        if digest_of_bytes(b) != d:
            raise ReplicaRefused("artifact_missing", "artifact bytes for %s do not match their digest" % d)
        artifacts[d] = base64.b64encode(b).decode("ascii")
    body = {"encoding": EXPORT_ENCODING, "export_id": export_identity(record), "seq": record["seq"], "record": record, "artifacts": artifacts}
    blob = canonical_bytes(body)
    return {"export_id": body["export_id"], "seq": record["seq"], "body": body, "bytes": blob, "export_digest": digest_of_bytes(blob)}


# ---------------------------------------------------------------------------------------------
# The publisher: a local bare audit repository, one commit per export, CAS push to the remote.
# ---------------------------------------------------------------------------------------------

class Publisher:
    """Publishes exports to `remote` at AUDIT_REF through a local bare audit repository at
    `audit_dir`. `sign(message_bytes) -> signature_text` is the caller's signer (OpenSSH in
    production). Stateless beyond the audit repository and the store's publication cursor."""

    def __init__(self, audit_dir, remote, sign, ref=AUDIT_REF):
        self.audit_dir, self.remote, self.sign, self.ref = audit_dir, remote, sign, ref
        if not os.path.isdir(os.path.join(audit_dir, "objects")):
            os.makedirs(audit_dir, exist_ok=True)
            _git(["init", "--bare", "-q", audit_dir], cwd=None)

    def local_tip(self):
        r = _git(["rev-parse", "--verify", "-q", self.ref], cwd=self.audit_dir, check=False)
        return r.stdout.decode().strip() or None

    def remote_tip(self):
        """The remote's own answer for the audit ref, or raises remote_unreachable."""
        r = _git(["ls-remote", "--exit-code", self.remote, self.ref], cwd=self.audit_dir, check=False, timeout=60)
        if r.returncode == 2:
            return None
        if r.returncode != 0:
            raise ReplicaRefused("remote_unreachable", r.stderr.decode("utf-8", "replace").strip()[-300:])
        return r.stdout.decode().split()[0]

    def commit_for_export(self, export_id):
        """The audit commit already holding `export_id`, or None: the same identity is REUSED,
        never re-prepared under a new commit."""
        tip = self.local_tip()
        if tip is None:
            return None
        r = _git(["log", "--format=%H %s", self.ref], cwd=self.audit_dir, check=False)
        for line in r.stdout.decode().splitlines():
            sha, _sp, subject = line.partition(" ")
            if subject == "veldo export " + export_id:
                return sha
        return None

    def prepare(self, export):
        """One audit commit for the export (tree: export.json, export.sig, artifact-<hex> blobs),
        parented on the current local tip, and the local ref moved to it. Idempotent by identity:
        an export already prepared returns its existing commit."""
        existing = self.commit_for_export(export["export_id"])
        if existing:
            return existing
        sig = self.sign(export["bytes"])
        if not _is_str(sig):
            raise ReplicaRefused("unsigned_export", "the signer returned no signature for %s" % export["export_id"])
        entries = []
        for name, data in (("export.json", export["bytes"]), ("export.sig", sig.encode("utf-8"))):
            sha = _git(["hash-object", "-w", "--stdin"], cwd=self.audit_dir, input_bytes=data).stdout.decode().strip()
            entries.append("100644 blob %s\t%s" % (sha, name))
        for d, b64 in sorted(export["body"]["artifacts"].items()):
            sha = _git(["hash-object", "-w", "--stdin"], cwd=self.audit_dir, input_bytes=base64.b64decode(b64)).stdout.decode().strip()
            entries.append("100644 blob %s\tartifact-%s" % (sha, d.split(":", 1)[1]))
        tree = _git(["mktree"], cwd=self.audit_dir, input_bytes=("\n".join(entries) + "\n").encode()).stdout.decode().strip()
        parent = self.local_tip()
        args = ["commit-tree", tree, "-m", "veldo export " + export["export_id"]] + (["-p", parent] if parent else [])
        commit = _git(args, cwd=self.audit_dir).stdout.decode().strip()
        _git(["update-ref", self.ref, commit] + ([parent] if parent else []), cwd=self.audit_dir)
        return commit

    def push(self, commit, expected_old):
        """Compare-and-swap push of the audit ref: the remote must still be at `expected_old` (None
        for an empty ref). Returns (ok, detail)."""
        lease = "--force-with-lease=%s:%s" % (self.ref, expected_old or "")
        r = _git(["push", "-q", lease, self.remote, "%s:%s" % (commit, self.ref)], cwd=self.audit_dir, check=False, timeout=120)
        return r.returncode == 0, r.stderr.decode("utf-8", "replace").strip()[-400:]

    def chain(self):
        """Every audit commit on the local ref, oldest first."""
        tip = self.local_tip()
        if tip is None:
            return []
        return _git(["rev-list", "--reverse", self.ref], cwd=self.audit_dir).stdout.decode().split()


def remote_contract_problems(remote, evidence=None):
    """Why this remote may NOT be activated as the durable replica (R23, R26): a local path or file
    URL qualifies the PROTOCOL only and is never off-host durability; activation needs the
    operations authority's recorded evidence of remote durability and of protected-ref access for
    AUDIT_REF (who may write it, and that force-updates are refused). Empty iff activation may
    proceed; a protocol-only remote is named as such, never silently accepted."""
    problems = []
    ev = evidence or {}
    if not _is_str(remote):
        return ["no remote named"]
    if remote.startswith("/") or remote.startswith("file://") or remote.startswith("."):
        problems.append("remote %s is a local path: it qualifies the publication protocol only and is not off-host durability" % remote)
    if ev.get("remote_durability_evidence") in (None, "", False):
        problems.append("no operations evidence of remote durability is recorded for %s" % remote)
    if ev.get("protected_ref") != AUDIT_REF or ev.get("force_update_refused") is not True:
        problems.append("no evidence that %s is protected on the remote (force updates refused, writers named)" % AUDIT_REF)
    if not _is_str(ev.get("recorded_by")) or ev.get("recorded_by", "").strip().lower() in ("agent", "bot", "ava", "machine", "automation"):
        problems.append("the remote contract evidence is not recorded by a named person of the operations authority")
    return problems


# ---------------------------------------------------------------------------------------------
# Publish, reconcile, outcome, status: everything the store's publication cursor drives.
# ---------------------------------------------------------------------------------------------

def publish_pending(conn, store, publisher, artifact_bytes, now, dispatch=None):
    """Publish every committed record without an acknowledgement, in sequence, stopping at the first
    failure and leaving the rest visibly pending. For each: build the export (same identity every
    time), prepare or reuse its audit commit, CAS-push onto the exact remote tip, verify the remote's
    own answer, persist the acknowledgement, and only THEN hand the command to `dispatch` (the
    external receiver) if one is given. Returns {published, pending, stopped, reason}."""
    out = {"published": [], "pending": [], "stopped": False, "reason": None}
    pending = store.pending_exports(conn)
    if not pending:
        return out
    records = {r["seq"]: r for r in store.export_journal(conn)}
    for row in pending:
        rec = records[row["seq"]]
        export = build_export(rec, artifact_bytes)
        if row["export_id"] is not None and row["export_id"] != export["export_id"]:
            raise ReplicaRefused("export_identity_mismatch", "seq %s was recorded as %s but the record now names %s: a second identity for one sequence is refused"
                                 % (row["seq"], row["export_id"], export["export_id"]))
        if row["export_id"] is None:
            store.record_export(conn, row["seq"], export["export_id"], export["export_digest"])
        commit = publisher.prepare(export)
        _kill_point("after_export_prepared")
        try:
            remote_tip = publisher.remote_tip()
        except ReplicaRefused as e:
            out.update(stopped=True, reason="%s: %s" % (e.code, e.detail))
            out["pending"] = [r["seq"] for r in pending if r["seq"] not in out["published"]]
            return out
        chain = publisher.chain()
        if remote_tip is not None and remote_tip not in chain:
            # The remote names a commit this authority never exported: a divergent replica. Nothing
            # is overwritten; publication pauses until signed operations reconciliation (R27).
            store.pause_publication(conn, "divergent replica: remote %s names %s, which is not in the local export chain" % (publisher.ref, remote_tip), now)
            out.update(stopped=True, reason="divergent_replica")
            out["pending"] = [r["seq"] for r in pending if r["seq"] not in out["published"]]
            return out
        remote_idx = chain.index(remote_tip) if remote_tip is not None else -1
        if remote_idx >= chain.index(commit):
            pass  # a lost acknowledgement: the remote already holds this export (at it, or past it)
        else:
            # The remote is behind (by this export, or by acknowledged history it lost): the SAME
            # commits move it forward under a lease on its exact current tip; no identity changes.
            ok, detail = publisher.push(commit, remote_tip)
            _kill_point("after_remote_ref_updated")
            if not ok:
                out.update(stopped=True, reason="remote_rejected: %s" % detail)
                out["pending"] = [r["seq"] for r in pending if r["seq"] not in out["published"]]
                return out
            try:
                confirmed = publisher.remote_tip()
            except ReplicaRefused as e:
                out.update(stopped=True, reason="%s after push: %s" % (e.code, e.detail))
                out["pending"] = [r["seq"] for r in pending if r["seq"] not in out["published"]]
                return out
            if confirmed != commit:
                out.update(stopped=True, reason="the remote answered %s after the push, not %s: no acknowledgement" % (confirmed, commit))
                out["pending"] = [r["seq"] for r in pending if r["seq"] not in out["published"]]
                return out
        store.acknowledge_export(conn, row["seq"], commit, publisher.remote, publisher.ref, now)
        _kill_point("after_ack_persisted")
        if dispatch is not None:
            dispatch(rec["command_id"], export["export_id"])
        out["published"].append(row["seq"])
    return out


def reconcile(conn, store, publisher, artifact_bytes, now):
    """Restart path: FIRST ask the remote what it holds and compare it with the local export chain
    (a tip this authority never exported is a divergent replica and pauses publication even when
    nothing is pending; a tip behind the chain is acknowledged history the remote lost, which the
    same commits will move forward), THEN publish_pending: the export identity is deterministic
    and the audit commit is reused, so a crash after the remote ref moved but before the
    acknowledgement persisted is settled by the remote's answer without another export."""
    try:
        remote_tip = publisher.remote_tip()
    except ReplicaRefused as e:
        return {"published": [], "pending": [r["seq"] for r in store.pending_exports(conn)], "stopped": True, "reason": "%s: %s" % (e.code, e.detail)}
    chain = publisher.chain()
    if remote_tip is not None and remote_tip not in chain:
        store.pause_publication(conn, "divergent replica: remote %s names %s, which is not in the local export chain" % (publisher.ref, remote_tip), now)
        return {"published": [], "pending": [r["seq"] for r in store.pending_exports(conn)], "stopped": True, "reason": "divergent_replica"}
    return publish_pending(conn, store, publisher, artifact_bytes, now)


def command_outcome(conn, store, command_id):
    """What a caller may say about a committed command (R23): 'succeeded' only when its export is
    acknowledged off-host; 'pending_publication' while committed but unacknowledged (never
    'rejected', never 'safely repeatable under a new identity'); 'unknown_command' when no such
    command was committed."""
    row = store.publication_row_for_command(conn, command_id)
    if row is None:
        return {"outcome": "unknown_command", "command_id": command_id}
    if row["acked_at"] is not None:
        return {"outcome": "succeeded", "command_id": command_id, "seq": row["seq"], "export_id": row["export_id"], "remote_commit": row["remote_commit"]}
    return {"outcome": "pending_publication", "command_id": command_id, "seq": row["seq"], "export_id": row["export_id"],
            "note": "committed locally; success is withheld until the export is acknowledged off-host; not rejected, and not repeatable under a new identity"}


def replication_status(conn, store, now):
    """The R23 status surface: last durable (acknowledged) sequence, local committed sequence,
    pending export count, oldest pending age in seconds, and the PAUSED_PUBLICATION condition with
    its reason. Read-only."""
    wm = store.publication_watermark(conn)
    pending = store.pending_exports(conn)
    oldest = None
    for p in pending:
        if p["committed_at"] is not None:
            age = now - p["committed_at"]
            oldest = age if oldest is None or age > oldest else oldest
    return {"schema": "veldo.replication_status/v1", "last_durable_seq": wm["last_durable_seq"], "local_committed_seq": wm["local_committed_seq"],
            "pending_exports": len(pending), "oldest_pending_age_seconds": oldest, "paused_publication": wm["paused_reason"] is not None,
            "paused_reason": wm["paused_reason"], "pending": [{"seq": p["seq"], "command_id": p["command_id"], "state": "pending_publication"} for p in pending]}
