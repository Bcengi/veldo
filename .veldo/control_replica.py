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
publication cursor and GRADED: off_host only for a remote whose contract the operations authority
qualified (remote_contract_problems() empty), protocol_only for a local remote, which proves the
mechanism and nothing about surviving host loss. Mutation SUCCESS, external dispatch and dependent
publication are withheld until an off-host acknowledgement exists: command_outcome() answers
pending_publication (never success, never rejected) for a committed command without one, and
acknowledged_protocol_only for a local replica. Dispatch is a durable obligation: it runs only for
off-host acknowledged sequences and is recorded when it ran, so a crash between acknowledgement and
dispatch is retried, never skipped. A commit reused for an export is validated (its export bytes
digest to the cursor's recorded digest and its signature verifies), never trusted by subject.
Recovery reconciles against the exact remote ref: a tip this authority never exported, a tip
BEHIND acknowledged history (the remote lost what it acknowledged), and an invalid reused commit
each PAUSE publication by name, and a persisted pause stops publication, acknowledgement and
dispatch until the operations authority resumes it. A store written before the publication cursor
existed refuses to publish a tail: the store's explicit backfill comes first.

WHAT IT IS NOT. It creates no live remote and proves nothing about surviving authority-host loss.
Source landing stays the lander's; host restoration is W33. Standard library only; Git and
OpenSSH are invoked as installed programs.

CRASH POINTS. Under VELDO_CONTROL_TEST_HARNESS=1 a publisher process may SIGKILL itself after the
export is prepared, after the remote ref moved, after the acknowledgement persisted, or after
dispatch ran but before it was recorded. Every window is reconciled by reconcile() on restart.
"""

# Load the shared Git boundary by sibling path, including when imported by file location.
import importlib.util as _git_importlib
from pathlib import Path as _GitPath
_git_spec = _git_importlib.spec_from_file_location("veldo_git_process", _GitPath(__file__).resolve().with_name("git_process.py"))
_git_process = _git_importlib.module_from_spec(_git_spec)
_git_spec.loader.exec_module(_git_process)
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
REFUSALS = ("remote_rejected", "remote_unreachable", "divergent_replica", "lost_acknowledged_history", "invalid_export_commit",
            "export_identity_mismatch", "artifact_missing", "unsigned_export", "remote_unqualified", "publication_paused", "store_read_only")
KILL_POINTS = ("after_export_prepared", "after_remote_ref_updated", "after_ack_persisted", "after_dispatch_before_record")
LOCAL_SCHEMES = ("file://",)


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


def _git(args, cwd, input_bytes=None, check=True, timeout=60):
    r = _git_process.run(["git"] + list(args), cwd=cwd, input=input_bytes, capture_output=True, identity=("veldo-authority", "authority@veldo.local"), timeout=timeout,
                       stdin=None if input_bytes is not None else subprocess.DEVNULL)
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
    its digest and checked against it. `artifact_bytes(digest) -> bytes or None`."""
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
# The remote contract (R23, R26): what makes an acknowledgement off-host durable.
# ---------------------------------------------------------------------------------------------

def is_local_remote(remote):
    """A remote that lives on this host: an absolute or relative path, or a file URL. Only a URL
    with a non-file scheme (ssh://, https://, git://) or the scp-like host:path form is remote."""
    if not _is_str(remote):
        return True
    r = remote.strip()
    if r.startswith(LOCAL_SCHEMES):
        return True
    if "://" in r:
        return False
    head = r.split(":", 1)[0]
    if ":" in r and "/" not in head and not head.startswith("."):
        return False  # host:path
    return True


def remote_contract_problems(remote, evidence=None):
    """Why this remote may NOT be treated as the durable replica (R23, R26): a local path, a
    relative path or a file URL qualifies the PROTOCOL only and is never off-host durability;
    activation needs the operations authority's recorded evidence of remote durability and of
    protected-ref access for AUDIT_REF (force updates refused, writers named), recorded by a
    named person. Empty iff acknowledgements from this remote are off_host."""
    problems = []
    ev = evidence or {}
    if not _is_str(remote):
        return ["no remote named"]
    if is_local_remote(remote):
        problems.append("remote %s is a local path: it qualifies the publication protocol only and is not off-host durability" % remote)
    if ev.get("remote_durability_evidence") in (None, "", False):
        problems.append("no operations evidence of remote durability is recorded for %s" % remote)
    if ev.get("protected_ref") != AUDIT_REF or ev.get("force_update_refused") is not True:
        problems.append("no evidence that %s is protected on the remote (force updates refused, writers named)" % AUDIT_REF)
    if not _is_str(ev.get("recorded_by")) or ev.get("recorded_by", "").strip().lower() in ("agent", "bot", "ava", "machine", "automation"):
        problems.append("the remote contract evidence is not recorded by a named person of the operations authority")
    return problems


# ---------------------------------------------------------------------------------------------
# The publisher: a local bare audit repository, one commit per export, CAS push to the remote.
# ---------------------------------------------------------------------------------------------

class Publisher:
    """Publishes exports to `remote` at AUDIT_REF through a local bare audit repository at
    `audit_dir`. `sign(message_bytes) -> signature_text` and `verify(message_bytes, signature_text)
    -> (ok, detail)` are the caller's (OpenSSH in production). The remote is graded ONCE at
    construction: off_host when `remote_contract` (the operations authority's evidence) has no
    problems, protocol_only when the remote is local and the caller says so explicitly, refused
    otherwise (remote_unqualified). Stateless beyond the audit repository and the store's cursor."""

    def __init__(self, audit_dir, remote, sign, verify, remote_contract=None, protocol_only=False, ref=AUDIT_REF):
        problems = remote_contract_problems(remote, remote_contract)
        if not problems:
            self.durability = "off_host"
        elif protocol_only and is_local_remote(remote):
            self.durability = "protocol_only"
        else:
            raise ReplicaRefused("remote_unqualified", "; ".join(problems) + "; a local remote must be declared protocol_only explicitly")
        self.audit_dir, self.remote, self.sign, self.verify, self.ref = audit_dir, remote, sign, verify, ref
        if not os.path.isdir(os.path.join(audit_dir, "objects")):
            os.makedirs(audit_dir, exist_ok=True)
            _git(["init", "--bare", "-q", audit_dir], cwd=None)

    def local_tip(self):
        r = _git(["rev-parse", "--verify", "-q", self.ref], cwd=self.audit_dir, check=False)
        return r.stdout.decode().strip() or None

    def remote_tip(self):
        r = _git(["ls-remote", "--exit-code", self.remote, self.ref], cwd=self.audit_dir, check=False, timeout=60)
        if r.returncode == 2:
            return None
        if r.returncode != 0:
            raise ReplicaRefused("remote_unreachable", r.stderr.decode("utf-8", "replace").strip()[-300:])
        return r.stdout.decode().split()[0]

    def chain(self):
        tip = self.local_tip()
        if tip is None:
            return []
        return _git(["rev-list", "--reverse", self.ref], cwd=self.audit_dir).stdout.decode().split()

    def _blob(self, commit, name):
        r = _git(["show", "%s:%s" % (commit, name)], cwd=self.audit_dir, check=False)
        return r.stdout if r.returncode == 0 else None

    def commit_for_export(self, export_id):
        """The audit commit whose SUBJECT names `export_id`, or None. A candidate only: validate_commit
        decides whether it IS the export."""
        if self.local_tip() is None:
            return None
        for line in _git(["log", "--format=%H %s", self.ref], cwd=self.audit_dir, check=False).stdout.decode().splitlines():
            sha, _sp, subject = line.partition(" ")
            if subject == "veldo export " + export_id:
                return sha
        return None

    def validate_commit(self, commit, export_id, export_digest):
        """Why `commit` is NOT the export it claims to be: no export.json, bytes whose digest is not
        the cursor's recorded digest, a body naming another export id, no signature, or a signature
        that does not verify over those bytes. Empty iff the commit may be reused or acknowledged."""
        problems = []
        blob = self._blob(commit, "export.json")
        if blob is None:
            return ["commit %s carries no export.json" % commit[:12]]
        if export_digest is not None and digest_of_bytes(blob) != export_digest:
            problems.append("commit %s carries export bytes with digest %s, not the recorded %s" % (commit[:12], digest_of_bytes(blob), export_digest))
        try:
            body = json.loads(blob.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            return problems + ["commit %s carries export.json that is not JSON" % commit[:12]]
        if body.get("export_id") != export_id or body.get("encoding") != EXPORT_ENCODING:
            problems.append("commit %s names export %r (%r), not %s" % (commit[:12], body.get("export_id"), body.get("encoding"), export_id))
        sig = self._blob(commit, "export.sig")
        if sig is None:
            problems.append("commit %s carries no export.sig" % commit[:12])
        else:
            ok, detail = self.verify(blob, sig.decode("utf-8", "replace"))
            if ok is not True:
                problems.append("commit %s: the export signature does not verify: %s" % (commit[:12], detail))
        return problems

    def prepare(self, export):
        """One audit commit for the export (tree: export.json, export.sig, artifact-<hex> blobs),
        parented on the current local tip, and the local ref moved to it. Idempotent by identity: an
        export already prepared returns its existing commit AFTER validating it."""
        existing = self.commit_for_export(export["export_id"])
        if existing:
            problems = self.validate_commit(existing, export["export_id"], export["export_digest"])
            if problems:
                raise ReplicaRefused("invalid_export_commit", "; ".join(problems))
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
        lease = "--force-with-lease=%s:%s" % (self.ref, expected_old or "")
        r = _git(["push", "-q", lease, self.remote, "%s:%s" % (commit, self.ref)], cwd=self.audit_dir, check=False, timeout=120)
        return r.returncode == 0, r.stderr.decode("utf-8", "replace").strip()[-400:]


# ---------------------------------------------------------------------------------------------
# Publish, reconcile, dispatch, outcome, status: everything the store's publication cursor drives.
# ---------------------------------------------------------------------------------------------

def _stopped(out, pending, reason):
    out.update(stopped=True, reason=reason)
    out["pending"] = [r["seq"] for r in pending if r["seq"] not in out["published"]]
    return out


def _pause(conn, store, now, out, pending, code, detail):
    store.pause_publication(conn, "%s: %s" % (code, detail), now)
    return _stopped(out, pending, code)


def _remote_position(conn, store, publisher, out, pending, now):
    """(remote_tip, chain, stopped_out): the remote judged against the local chain and the
    acknowledged history. A tip outside the chain is divergent; a tip behind the last ACKNOWLEDGED
    export is acknowledged history the remote lost. Both pause; stopped_out is then the result."""
    try:
        remote_tip = publisher.remote_tip()
    except ReplicaRefused as e:
        return None, None, _stopped(out, pending, "%s: %s" % (e.code, e.detail))
    chain = publisher.chain()
    if remote_tip is not None and remote_tip not in chain:
        return None, None, _pause(conn, store, now, out, pending, "divergent_replica", "remote %s names %s, which is not in the local export chain" % (publisher.ref, remote_tip))
    acked = store.acknowledged_exports(conn)
    if acked:
        last = acked[-1]["remote_commit"]
        if last in chain and (remote_tip is None or chain.index(remote_tip) < chain.index(last)):
            return None, None, _pause(conn, store, now, out, pending, "lost_acknowledged_history",
                                      "remote %s is at %s, behind the acknowledged export for seq %s (%s): the remote lost history it acknowledged"
                                      % (publisher.ref, remote_tip, acked[-1]["seq"], last[:12]))
    return remote_tip, chain, None


def dispatch_pending(conn, store, dispatch, now):
    """Run the durable dispatch obligation: every OFF-HOST acknowledged sequence not yet recorded as
    dispatched is handed to `dispatch(command_id, export_id)` and then recorded. A crash between the
    two leaves the obligation, so the receiver may see a sequence twice; it never sees it zero times.
    Nothing is dispatched while publication is paused. Returns the sequences dispatched."""
    if dispatch is None or store.publication_watermark(conn)["paused_reason"] is not None:
        return []
    done = []
    for row in store.undispatched_exports(conn):
        dispatch(row["command_id"], row["export_id"])
        _kill_point("after_dispatch_before_record")
        store.mark_dispatched(conn, row["seq"], now)
        done.append(row["seq"])
    return done


def _preconditions(conn, store, out):
    if store.publication_gaps(conn):
        return _stopped(out, store.pending_exports(conn), "publication_backfill_required: journal sequences without a publication row")
    paused = store.publication_watermark(conn)["paused_reason"]
    if paused is not None:
        return _stopped(out, store.pending_exports(conn), "publication_paused: %s" % paused)
    return None


def publish_pending(conn, store, publisher, artifact_bytes, now, dispatch=None):
    """Publish every committed record without an acknowledgement, in sequence, stopping at the first
    failure and leaving the rest visibly pending; then run the dispatch obligation. A persisted pause
    or an unbackfilled store stops everything by name. For each pending export: build it (same
    identity every time), prepare or validate-and-reuse its audit commit, judge the remote against
    the chain and the acknowledged history, CAS-push onto the exact remote tip, verify the remote's
    own answer, persist the GRADED acknowledgement. Returns {published, dispatched, pending, stopped,
    reason}."""
    out = {"published": [], "dispatched": [], "pending": [], "stopped": False, "reason": None}
    stopped = _preconditions(conn, store, out)
    if stopped is not None:
        return stopped
    pending = store.pending_exports(conn)
    records = {r["seq"]: r for r in store.export_journal(conn)} if pending else {}
    for row in pending:
        rec = records[row["seq"]]
        export = build_export(rec, artifact_bytes)
        if row["export_id"] is not None and row["export_id"] != export["export_id"]:
            raise ReplicaRefused("export_identity_mismatch", "seq %s was recorded as %s but the record now names %s: a second identity for one sequence is refused"
                                 % (row["seq"], row["export_id"], export["export_id"]))
        if row["export_id"] is None:
            store.record_export(conn, row["seq"], export["export_id"], export["export_digest"])
        try:
            commit = publisher.prepare(export)
        except ReplicaRefused as e:
            if e.code == "invalid_export_commit":
                return _pause(conn, store, now, out, pending, e.code, e.detail)
            raise
        _kill_point("after_export_prepared")
        remote_tip, chain, stopped = _remote_position(conn, store, publisher, out, pending, now)
        if stopped is not None:
            return stopped
        remote_idx = chain.index(remote_tip) if remote_tip is not None else -1
        if remote_idx >= chain.index(commit):
            problems = publisher.validate_commit(commit, export["export_id"], export["export_digest"])  # a lost acknowledgement: the remote holds it; is it the export?
            if problems:
                return _pause(conn, store, now, out, pending, "invalid_export_commit", "; ".join(problems))
        else:
            ok, detail = publisher.push(commit, remote_tip)
            _kill_point("after_remote_ref_updated")
            if not ok:
                return _stopped(out, pending, "remote_rejected: %s" % detail)
            try:
                confirmed = publisher.remote_tip()
            except ReplicaRefused as e:
                return _stopped(out, pending, "%s after push: %s" % (e.code, e.detail))
            if confirmed != commit:
                return _stopped(out, pending, "the remote answered %s after the push, not %s: no acknowledgement" % (confirmed, commit))
        store.acknowledge_export(conn, row["seq"], commit, publisher.remote, publisher.ref, now, publisher.durability)
        _kill_point("after_ack_persisted")
        out["published"].append(row["seq"])
    out["dispatched"] = dispatch_pending(conn, store, dispatch, now)
    return out


def reconcile(conn, store, publisher, artifact_bytes, now, dispatch=None):
    """Restart path: refuse while paused or unbackfilled; judge the remote against the chain and the
    acknowledged history even when nothing is pending (divergence and lost acknowledged history are
    found and pause publication); then publish_pending, which reuses every prepared export under
    its one identity, settles a lost acknowledgement by the remote's answer, and runs the dispatch
    obligation for anything acknowledged off-host but never dispatched."""
    out = {"published": [], "dispatched": [], "pending": [], "stopped": False, "reason": None}
    stopped = _preconditions(conn, store, out)
    if stopped is not None:
        return stopped
    _tip, _chain, stopped = _remote_position(conn, store, publisher, out, store.pending_exports(conn), now)
    if stopped is not None:
        return stopped
    return publish_pending(conn, store, publisher, artifact_bytes, now, dispatch=dispatch)


def command_outcome(conn, store, command_id):
    """What a caller may say about a committed command (R23): 'succeeded' only when its export is
    acknowledged OFF-HOST; 'acknowledged_protocol_only' when a local replica holds it (not success);
    'pending_publication' while committed but unacknowledged (never 'rejected', never 'safely
    repeatable under a new identity'); 'unknown_command' when no such command was committed."""
    row = store.publication_row_for_command(conn, command_id)
    if row is None:
        return {"outcome": "unknown_command", "command_id": command_id}
    if row["acked_at"] is not None and row["durability"] == "off_host":
        return {"outcome": "succeeded", "command_id": command_id, "seq": row["seq"], "export_id": row["export_id"], "remote_commit": row["remote_commit"],
                "dispatched": row["dispatched_at"] is not None}
    if row["acked_at"] is not None:
        return {"outcome": "acknowledged_protocol_only", "command_id": command_id, "seq": row["seq"], "export_id": row["export_id"], "remote_commit": row["remote_commit"],
                "note": "a local replica holds the export; this is not off-host durability and not success"}
    return {"outcome": "pending_publication", "command_id": command_id, "seq": row["seq"], "export_id": row["export_id"],
            "note": "committed locally; success is withheld until the export is acknowledged off-host; not rejected, and not repeatable under a new identity"}


def replication_status(conn, store, now):
    """The R23 status surface: last durable (off-host acknowledged) sequence, last acknowledged
    sequence of any grade, local committed sequence, pending export count, oldest pending age,
    undispatched count, backfill requirement, and the PAUSED_PUBLICATION condition with its reason.
    Read-only."""
    wm = store.publication_watermark(conn)
    pending = store.pending_exports(conn)
    oldest = None
    for p in pending:
        if p["committed_at"] is not None:
            age = now - p["committed_at"]
            oldest = age if oldest is None or age > oldest else oldest
    return {"schema": "veldo.replication_status/v1", "last_durable_seq": wm["last_durable_seq"], "last_acknowledged_seq": wm["last_acknowledged_seq"],
            "local_committed_seq": wm["local_committed_seq"], "pending_exports": len(pending), "oldest_pending_age_seconds": oldest,
            "undispatched": len(store.undispatched_exports(conn)), "backfill_required": bool(store.publication_gaps(conn)),
            "paused_publication": wm["paused_reason"] is not None, "paused_reason": wm["paused_reason"],
            "pending": [{"seq": p["seq"], "command_id": p["command_id"], "state": "pending_publication"} for p in pending]}
