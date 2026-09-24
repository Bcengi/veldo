#!/usr/bin/env python3
"""The control store: atomic journaled commands over one local SQLite authority (PLAN-0019 W8,
VELDO-0023, R21, R22, R53).

WHAT THIS MODULE IS. The ONLY writer of domain state. One local SQLite database at
<git-common-dir>/veldo/control/control.sqlite3 on a filesystem qualified for locking and
durability (network-mounted storage refuses to open for writes); foreign keys enforced and full
durability set, both read back after opening rather than assumed. A registered mutating command
carries a globally unique command id, an authenticated principal, its expected entity versions,
referenced artifact digests and a nonce; one transaction commits the entity versions, the signed
journal record, the consumed nonce, the reservation rows and the effect obligations together, or
none of them. A duplicate command with identical content returns its prior committed result; the
same id with different content is refused as a content conflict; a stale expected version is
refused before anything is written. The journal record carries sequence, previous-record digest,
authority generation, command digest, identities, before and after versions, transition data and
receipt references in a versioned deterministic canonical encoding; the record digest covers all
of them and the signature (OpenSSH, through a signer callable the caller supplies) covers the
digest's bytes. Plan revision is never used as a concurrency version.

WHAT IT IS NOT. It imports no execution runtime (no LangGraph, no worker engine) and no other
Veldo organ: signing and verification are callables passed in, so the store never holds key
material. Replication is W9; the checkpoint adapter's tables are not created here. Standard
library only.

ENTITY OWNERSHIP. A service whose commands alone may write some entities (VELDO-0035's snapshots
and accepted revisions, VELDO-0037's alias counters, reservations and immutable document versions)
DECLARES that with declare_owners: for each owned entity kind, and for each owned entity id prefix,
the commands allowed to write it, and the one module file whose code those commands are, with the
sha256 of that file's bytes. The declaration is persisted in the store itself (the
entity_owners table, created by the first declaration, so a store nobody declared into has none),
and execute reads it inside every command's own BEGIN IMMEDIATE, so it binds EVERY connection to
the file: one another process opened, one opened before the declaration, one whose module copy
registered nothing, and one on which a later registration replaced an earlier one. A command
writing an entity refuses entity_owned unless it is allowed by every declaration matching that
entity: its kind after the write, its kind before it, and every declared prefix of its id. So
where a command is registered, and in what order, decides nothing about what it may write.
Nor does its NAME: before an owned command's transition runs, execute requires that the callable
registered for it, and every function its closure holds, was compiled from exactly the declared
module file, and that the file's bytes still have the declared digest; a same-named registration
from any other code, a genuine wrapper around a foreign body, or an edited module is refused
foreign_transition and nothing is written.
No declaration may name one of the store's own generic commands (COMMAND_REGISTRY): they are what
ownership keeps out, and binding one to a module would refuse it for every entity.
STATED LIMITS, not claims. Enforcement is code in execute, under a same-account threat model: raw
SQL on the file, a copy of this module from before the rule, and deleting entity_owners all write
owned entities, and code that deliberately compiles a function under the declared file name, or
patches the owning module's globals in the same process, passes the origin check. The declaration
names one file and its bytes, so the owning service runs only from that copy as it was when it
first attached: an upgraded module, or the same module attached from another checkout's copy, is
refused ownership_conflict at attach, and Release 1 has no re-declaration path (Release 2).
Declarations and repository bindings are not part of the journal, so a store rebuilt from its
journal carries neither (Release 2 recovery).
A declaration is immutable: the same declaration again is a no-op, a different one for a declared
kind or prefix refuses ownership_conflict, and so does a first declaration for a kind or prefix
that entities already occupy, because they were written while nobody owned them.

THE ARCHITECTURE RECORD HAS ONE WRITER (VELDO-0134, R50). An entity whose id begins with
ARCHITECTURE_PREFIX, or whose kind (before or after the write) is ARCHITECTURE_KIND, is written by
the operation named ARCHITECTURE_OPERATION and by nothing else: execute refuses entity_owned for any
other operation whose parameters name such an id as the row it writes (WRITE_IDENTITY_PARAMETERS),
and for any other operation whose transition would change such an entity. The rule is here, in the
command path, not in a declaration, so it binds every operation registered now or later, the
generic upsert_entity and retire_entity among them, on every connection, with or without the
accepting service attached. It names an operation, not code: which transition a connection
registers under that name is that connection's owner's business (VELDO-0134's accept command in
production, a suite's own writer of deliberately invalid records on the suite's own connection).

ACCEPTED REPOSITORIES. A service that reads an enrolled repository's commits BINDS each repository
uuid of a domain to the local Git repository it reads, with bind_repositories, and the binding is
persisted beside the declarations (the repository_bindings table, created by the first binding).
The first binding wins and is immutable: the same path again is a no-op and another path refuses
repository_binding_conflict, so every service on every connection to this store reads one
repository for one uuid. Transitions read it back inside their own transaction with
bound_repository. Neither table is part of the journal.

CRASH POINTS. For the SIGKILL matrix the spec requires, a writer process may be told through the
environment to kill itself at a durable boundary (before COMMIT, inside COMMIT through the
progress handler, or after COMMIT before replying). The hooks act only when
VELDO_CONTROL_TEST_HARNESS=1 is also set, so no production path can be told to die.
"""
import hashlib
import json
import os
import signal
import sqlite3
import subprocess
import time

SCHEMA = "veldo.control_store/v1"
JOURNAL_ENCODING = "veldo.journal/v1"
GENESIS_DIGEST = "sha256:genesis"
DB_RELATIVE = os.path.join("veldo", "control", "control.sqlite3")

# Network or otherwise unqualified filesystems: SQLite locking is not trustworthy there (R21).
UNSUPPORTED_FSTYPES = frozenset({"nfs", "nfs4", "cifs", "smb", "smb2", "smb3", "smbfs", "sshfs", "fuse.sshfs", "9p", "afs",
                                 "ceph", "glusterfs", "davfs", "fuse.davfs2", "lustre", "gpfs", "beegfs"})

# The domain tables Veldo owns (R21). Checkpoint tables are adapter-owned and never listed here.
DOMAIN_TABLES = ("entities", "journal", "commands", "nonces", "reservations", "effects", "publication", "publication_control")

COMMAND_FIELDS = ("command_id", "principal", "operation", "parameters", "expected_versions", "artifact_digests", "nonce")
JOURNAL_FIELDS = ("seq", "prev_digest", "authority_generation", "command_id", "command_digest", "principal", "signer",
                  "before_versions", "after_versions", "transition", "nonce", "reservations", "effects", "receipt_refs", "artifact_digests", "encoding")
JOURNAL_SIGNED_FIELDS = JOURNAL_FIELDS + ("record_digest",)

REFUSALS = ("malformed_command", "unregistered_operation", "command_content_conflict", "stale_version", "nonce_consumed",
            "foreign_key_violation", "unsupported_filesystem", "incomplete_transaction", "durability_not_enabled", "transition_refused",
            "read_only_handle", "publication_backfill_required", "no_explicit_store_path", "entity_owned",
            "ownership_conflict", "repository_binding_conflict", "foreign_transition")
DURABILITY_GRADES = ("off_host", "protocol_only")

# VELDO-0134: the architecture record and the one operation that writes it (see the module docstring).
ARCHITECTURE_OPERATION = "accept_architecture"
ARCHITECTURE_KIND = "architecture_contract"
ARCHITECTURE_PREFIX = "architecture:"
# The parameters by which a command names the row it writes (an entity, a receipt, a reservation or
# an effect); a command naming the architecture record through one of them is refused before its
# transition runs.
WRITE_IDENTITY_PARAMETERS = ("entity_id", "receipt_id", "reservation_id", "effect_id")

_DDL = (
    "CREATE TABLE IF NOT EXISTS entities (id TEXT PRIMARY KEY, kind TEXT NOT NULL, version INTEGER NOT NULL, digest TEXT NOT NULL, data TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS journal (seq INTEGER PRIMARY KEY, prev_digest TEXT NOT NULL, record_digest TEXT NOT NULL UNIQUE, "
    "authority_generation INTEGER NOT NULL, command_id TEXT NOT NULL UNIQUE, command_digest TEXT NOT NULL, principal TEXT NOT NULL, "
    "signer TEXT NOT NULL, signature TEXT NOT NULL, before_versions TEXT NOT NULL, after_versions TEXT NOT NULL, transition TEXT NOT NULL, "
    "nonce TEXT NOT NULL, reservations TEXT NOT NULL, effects TEXT NOT NULL, "
    "receipt_refs TEXT NOT NULL, artifact_digests TEXT NOT NULL, encoding TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS commands (command_id TEXT PRIMARY KEY, command_digest TEXT NOT NULL, result TEXT NOT NULL, result_digest TEXT NOT NULL, "
    "seq INTEGER NOT NULL REFERENCES journal(seq))",
    "CREATE TABLE IF NOT EXISTS nonces (nonce TEXT PRIMARY KEY, command_id TEXT NOT NULL REFERENCES commands(command_id))",
    "CREATE TABLE IF NOT EXISTS reservations (id TEXT PRIMARY KEY, command_id TEXT NOT NULL REFERENCES commands(command_id), ceiling TEXT NOT NULL, delta REAL NOT NULL)",
    "CREATE TABLE IF NOT EXISTS effects (id TEXT PRIMARY KEY, command_id TEXT NOT NULL REFERENCES commands(command_id), kind TEXT NOT NULL, target TEXT NOT NULL, state TEXT NOT NULL)",
    # The publication cursor (R21, R23): one row per committed journal sequence, created with the
    # record inside the SAME transaction (committed_at), the export identity and digest recorded
    # when the export is built, the acknowledgement (the remote's own answer) when it arrives.
    "CREATE TABLE IF NOT EXISTS publication (seq INTEGER PRIMARY KEY REFERENCES journal(seq), command_id TEXT NOT NULL REFERENCES commands(command_id), "
    "committed_at REAL NOT NULL, export_id TEXT, export_digest TEXT, remote_commit TEXT, remote TEXT, ref TEXT, acked_at REAL, "
    "durability TEXT, dispatched_at REAL, backfilled INTEGER NOT NULL DEFAULT 0)",
    "CREATE TABLE IF NOT EXISTS publication_control (id INTEGER PRIMARY KEY CHECK (id = 1), paused_reason TEXT, paused_at REAL)",
)

# Entity ownership (see the module docstring). Not part of _DDL: the first declaration creates it, so
# a store into which nothing was ever declared carries exactly the DOMAIN_TABLES and no owner rule.
OWNERS_TABLE = "entity_owners"
_OWNERS_DDL = ("CREATE TABLE IF NOT EXISTS entity_owners (selector TEXT NOT NULL CHECK (selector IN ('kind', 'prefix')), "
               "value TEXT NOT NULL, owner TEXT NOT NULL, commands TEXT NOT NULL, module TEXT NOT NULL, "
               "module_digest TEXT NOT NULL, PRIMARY KEY (selector, value))")


# Accepted repositories (see the module docstring), created by the first binding like entity_owners.
BINDINGS_TABLE = "repository_bindings"
_BINDINGS_DDL = ("CREATE TABLE IF NOT EXISTS repository_bindings (domain_uuid TEXT NOT NULL, repository_uuid TEXT NOT NULL, "
                 "path TEXT NOT NULL, PRIMARY KEY (domain_uuid, repository_uuid))")


class StoreRefused(Exception):
    """A named refusal (one of REFUSALS) with its detail; nothing was written."""

    def __init__(self, code, detail):
        super().__init__("%s: %s" % (code, detail))
        self.code, self.detail = code, detail


def _is_str(v):
    return isinstance(v, str) and v.strip() != ""


def canonical_bytes(obj):
    """THE canonical encoding: sorted-key compact JSON, UTF-8. Versioned by JOURNAL_ENCODING on the
    record; deterministic across hosts because nothing about it depends on dict order or locale."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")


def digest_of(obj):
    return "sha256:" + hashlib.sha256(canonical_bytes(obj)).hexdigest()


def command_digest(command):
    """The digest a command's content is judged by: every COMMAND_FIELDS value, so a retry with the
    same id and one changed parameter is a different command."""
    return digest_of({k: command.get(k) for k in COMMAND_FIELDS})


# ---------------------------------------------------------------------------------------------
# Placement and qualification (R21).
# ---------------------------------------------------------------------------------------------

def control_db_path(path):
    """The authority's database at an EXPLICIT path. It derives nothing, and that is the point.

    WHAT IT USED TO DO, and why that was a loaded gun. It answered from VELDO_CONTROL_DB in the
    environment, and failing that by running `git rev-parse --git-common-dir` in whatever directory
    the process happened to be in. Two throwaway repositories and one call showed it: standing in
    the first it answered the first repository's database, standing in the second it answered the
    second's, and with the variable set it answered neither. A command carries the repository it
    means and is signed; a resolver that answers from the caller's position rather than from the
    command lets a correctly signed command commit into another repository with nothing in the chain
    comparing the two. R20 says the coordinate comes from the command.

    It had NO CALLERS. Every place that opens the store passes a path. So nothing was reaching the
    wrong database; what existed was the means to, sitting where the next person to need a default
    would find it. This closes that rather than waiting for them.

    WHERE A PATH SHOULD COME FROM: control_enrollment.resolve_store(workspace, ...), which reads the
    workspace's own signed enrollment binding and refuses by name when it cannot. This module
    deliberately does not call it. control_store imports no other Veldo organ, which is a property
    its own docstring states and the shape gate checks, and a store that reached into enrollment to
    find itself would be the same circularity in the other direction.

    DB_RELATIVE below still records the conventional layout, <git-common-dir>/veldo/control, which is
    what an enrollment writes into a binding. Recording a convention is not the same as deriving
    from it."""
    if not path:
        raise StoreRefused(
            "no_explicit_store_path",
            "control_db_path requires an explicit store path: it no longer derives one from the "
            "environment or from the process's current directory, because a database chosen by "
            "where the caller was standing is not the database the command named. Resolve it with "
            "control_enrollment.resolve_store(workspace, ...), which reads the workspace's signed "
            "binding.")
    return os.path.abspath(path)


def filesystem_type(path, mounts_text=None):
    """The filesystem type of the mount holding `path` (longest mount-point prefix in /proc/mounts),
    or None when it cannot be determined. `mounts_text` lets a test supply the table."""
    try:
        text = mounts_text if mounts_text is not None else open("/proc/mounts").read()
    except OSError:
        return None
    target = os.path.abspath(path)
    best, best_type = "", None
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        mp = parts[1].replace("\\040", " ")
        if (target == mp or target.startswith(mp.rstrip("/") + "/")) and len(mp) > len(best):
            best, best_type = mp, parts[2]
    return best_type


def filesystem_problems(path, mounts_text=None):
    """Why `path` may NOT hold the authority for writes (R21): a network or otherwise unsupported
    filesystem, or one whose type cannot be determined (unknown is not qualified)."""
    fstype = filesystem_type(path, mounts_text)
    if fstype is None:
        return ["filesystem type of %s cannot be determined: an unqualified filesystem does not hold the authority" % path]
    if fstype.lower() in UNSUPPORTED_FSTYPES or fstype.lower().startswith("fuse.sshfs"):
        return ["filesystem %s at %s is network-mounted or unsupported for SQLite locking and durability" % (fstype, path)]
    return []


def resolved_target(path):
    """The database's REAL location: every symlink in the path and in the file itself resolved, so
    qualification judges the storage that will hold the bytes, not a link that points at it."""
    return os.path.realpath(os.path.abspath(path))


class StoreConnection(sqlite3.Connection):
    """Service registrations belong to this handle, never to the process-wide catalog."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.command_registry = {}
        self.command_transaction = False

    def close(self):
        self.command_registry.clear()
        super().close()


def open_store(path, mode="rw", mounts_text=None, allow_unbackfilled=False):
    """A connection to the store with foreign keys, WAL and FULL synchronous set AND READ BACK; a
    write-mode open refuses an unsupported filesystem by name (judged at the RESOLVED target, so a
    symlink cannot place the authority on network storage) and creates the schema; a read-mode open
    is a genuinely read-only SQLite handle (URI mode=ro) through which no write can commit. A store
    whose journal has sequences without a publication row (written before the cursor existed)
    refuses a write-mode open as publication_backfill_required unless `allow_unbackfilled` is set
    by the explicit backfill step: an upgrade never leaves history out of the replica silently.
    Autocommit is off in the sqlite3 sense (isolation_level=None): every transaction is explicit."""
    if mode not in ("r", "rw"):
        raise ValueError("mode is r or rw")
    target = resolved_target(path)
    if mode == "rw":
        problems = filesystem_problems(os.path.dirname(target) or ".", mounts_text)
        if problems:
            raise StoreRefused("unsupported_filesystem", "; ".join(problems))
        os.makedirs(os.path.dirname(target), exist_ok=True)
        conn = sqlite3.connect(target, isolation_level=None, timeout=30, factory=StoreConnection)
    else:
        if not os.path.exists(target):
            raise StoreRefused("incomplete_transaction", "no store at %s to read" % path)
        conn = sqlite3.connect("file:%s?mode=ro" % target, uri=True, isolation_level=None, timeout=30, factory=StoreConnection)
    conn.execute("PRAGMA foreign_keys=ON")
    if mode == "rw":
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=FULL")
        for ddl in _DDL:
            conn.execute(ddl)
    fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    sync = conn.execute("PRAGMA synchronous").fetchone()[0]
    if fk != 1 or (mode == "rw" and sync != 2):
        conn.close()
        raise StoreRefused("durability_not_enabled", "foreign_keys=%r synchronous=%r after opening; the store refuses to run without both" % (fk, sync))
    if mode == "rw" and not allow_unbackfilled:
        missing = publication_gaps(conn)
        if missing:
            conn.close()
            raise StoreRefused("publication_backfill_required", "journal sequences %s have no publication row (a store written before the publication cursor "
                               "existed): run backfill_publication() explicitly; the replica must carry the complete history, never a tail" % missing[:5])
    return conn


# ---------------------------------------------------------------------------------------------
# The command registry (R22): every mutating operation and its transition.
# ---------------------------------------------------------------------------------------------

def _t_upsert_entity(params, before):
    """parameters: entity_id, kind, data (mapping). New or existing; the caller's expected version
    must match the existing one (checked before this runs)."""
    if not _is_str(params.get("entity_id")) or not _is_str(params.get("kind")) or not isinstance(params.get("data"), dict):
        raise StoreRefused("transition_refused", "upsert_entity needs entity_id, kind and a data mapping")
    return {params["entity_id"]: {"kind": params["kind"], "data": params["data"]}}


def _t_retire_entity(params, before):
    if not _is_str(params.get("entity_id")) or params["entity_id"] not in before:
        raise StoreRefused("transition_refused", "retire_entity needs an existing entity_id")
    cur = before[params["entity_id"]]
    return {params["entity_id"]: {"kind": cur["kind"], "data": dict(cur["data"], retired=True)}}


def _t_record_receipt(params, before):
    if not _is_str(params.get("receipt_id")) or not _is_str(params.get("subject")) or not _is_str(params.get("digest")):
        raise StoreRefused("transition_refused", "record_receipt needs receipt_id, subject and digest")
    return {params["receipt_id"]: {"kind": "receipt", "data": {"subject": params["subject"], "digest": params["digest"]}}}


def _t_reserve(params, before):
    if not _is_str(params.get("reservation_id")) or params.get("ceiling") not in ("account", "project", "unit") \
            or not isinstance(params.get("delta"), (int, float)) or isinstance(params.get("delta"), bool):
        raise StoreRefused("transition_refused", "reserve needs reservation_id, a ceiling (account, project, unit) and a numeric delta")
    return {}


def _t_record_effect(params, before):
    if not _is_str(params.get("effect_id")) or not _is_str(params.get("kind")) or not _is_str(params.get("target")):
        raise StoreRefused("transition_refused", "record_effect needs effect_id, kind and target")
    return {}


COMMAND_REGISTRY = {
    "upsert_entity": {"transition": _t_upsert_entity, "writes": ("entities", "journal", "commands", "nonces")},
    "retire_entity": {"transition": _t_retire_entity, "writes": ("entities", "journal", "commands", "nonces")},
    "record_receipt": {"transition": _t_record_receipt, "writes": ("entities", "journal", "commands", "nonces")},
    "reserve": {"transition": _t_reserve, "writes": ("reservations", "journal", "commands", "nonces")},
    "record_effect": {"transition": _t_record_effect, "writes": ("effects", "journal", "commands", "nonces")},
}


def architecture_writer(operation):
    """Whether `operation` may write the architecture record (VELDO-0134): the accept operation alone."""
    return operation == ARCHITECTURE_OPERATION


def architecture_entity(entity_id, kinds=()):
    """Whether an entity is the architecture record's: its id has ARCHITECTURE_PREFIX or one of its
    kinds (before or after a write) is ARCHITECTURE_KIND."""
    return (isinstance(entity_id, str) and entity_id.startswith(ARCHITECTURE_PREFIX)) or ARCHITECTURE_KIND in kinds


def command_problems(command, registry=None):
    """Why a command is malformed, by name: a missing field, a blank id or principal, an
    operation outside the registry, expected_versions not a mapping of ids to positive integers,
    artifact_digests not a list of strings, a blank nonce."""
    if not isinstance(command, dict):
        return ["a command is a mapping"]
    problems = ["command lacks %s" % f for f in COMMAND_FIELDS if f not in command]
    if problems:
        return problems
    if not _is_str(command["command_id"]):
        problems.append("command_id is blank: every command carries a globally unique id")
    if not _is_str(command["principal"]):
        problems.append("principal is blank: every command carries its authenticated principal")
    registry = COMMAND_REGISTRY if registry is None else registry
    if command["operation"] not in registry:
        problems.append("operation %r is not a registered command (%s)" % (command["operation"], ", ".join(sorted(registry))))
    if not isinstance(command["parameters"], dict):
        problems.append("parameters is not a mapping")
    ev = command["expected_versions"]
    if not isinstance(ev, dict) or not all(_is_str(k) and isinstance(v, int) and not isinstance(v, bool) and v >= 0 for k, v in ev.items()):
        problems.append("expected_versions is not a mapping of entity id to a non-negative integer version (0 means the entity must not exist)")
    if not isinstance(command["artifact_digests"], list) or not all(_is_str(d) for d in command["artifact_digests"]):
        problems.append("artifact_digests is not a list of digests")
    if not _is_str(command["nonce"]):
        problems.append("nonce is blank")
    return problems


# ---------------------------------------------------------------------------------------------
# Execution: one transaction, all of it or none (R22).
# ---------------------------------------------------------------------------------------------

def _kill_point(name):
    """Self-inflicted SIGKILL at a named boundary, only under the test harness. This is how the
    crash matrix reaches the durable boundaries of a real writer process."""
    if os.environ.get("VELDO_CONTROL_TEST_HARNESS") == "1" and os.environ.get("VELDO_CONTROL_KILL_AT") == name:
        os.kill(os.getpid(), signal.SIGKILL)


def _now():
    return time.time()


def _entities(conn, ids):
    out = {}
    for eid in ids:
        row = conn.execute("SELECT kind, version, digest, data FROM entities WHERE id=?", (eid,)).fetchone()
        if row:
            out[eid] = {"kind": row[0], "version": row[1], "digest": row[2], "data": json.loads(row[3])}
    return out


def _last_journal(conn):
    row = conn.execute("SELECT seq, record_digest FROM journal ORDER BY seq DESC LIMIT 1").fetchone()
    return (row[0], row[1]) if row else (0, GENESIS_DIGEST)


def journal_record_digest(record):
    """The record digest: over every JOURNAL_FIELDS value in canonical encoding."""
    return digest_of({k: record.get(k) for k in JOURNAL_FIELDS})


def journal_signed_bytes(record):
    """The bytes a journal signature covers: the JOURNAL_FIELDS plus the record digest."""
    return canonical_bytes({k: record.get(k) for k in JOURNAL_SIGNED_FIELDS})


def execute(conn, command, signer, sign, authority_generation, receipt_refs=(), committed_at=None):
    """Run one registered command in ONE transaction. `sign(message_bytes) -> signature_text` is
    the caller's signer (OpenSSH in production; the store holds no key). Returns the committed
    result; an identical retry returns the ORIGINAL result with replayed=True and writes nothing;
    every refusal raises StoreRefused with its name and nothing written."""
    registry = dict(COMMAND_REGISTRY, **conn.command_registry)
    problems = command_problems(command, registry)
    if problems:
        raise StoreRefused("malformed_command", "; ".join(problems))
    if not _is_str(signer) or not isinstance(authority_generation, int) or isinstance(authority_generation, bool) or authority_generation < 1:
        raise StoreRefused("malformed_command", "signer must be named and authority_generation a positive integer")
    if not architecture_writer(command["operation"]):
        named = sorted(k for k in WRITE_IDENTITY_PARAMETERS if architecture_entity(command["parameters"].get(k)))
        if named:
            raise StoreRefused("entity_owned", "%s may not write %s: the architecture record is written only by %s"
                               % (command["operation"], command["parameters"][named[0]], ARCHITECTURE_OPERATION))
    cdigest = command_digest(command)
    receipt_refs = list(receipt_refs or ())  # materialized ONCE: an iterator consumed twice signs one list and stores another
    if not all(_is_str(r) for r in receipt_refs):
        raise StoreRefused("malformed_command", "receipt_refs must be strings")
    try:
        conn.execute("BEGIN IMMEDIATE")
    except sqlite3.OperationalError as e:
        raise StoreRefused("read_only_handle", "this handle cannot write (%s): open the store with mode='rw' at a qualified location" % e)
    conn.command_transaction = True
    try:
        prior = conn.execute("SELECT command_digest, result FROM commands WHERE command_id=?", (command["command_id"],)).fetchone()
        if prior:
            if prior[0] != cdigest:
                raise StoreRefused("command_content_conflict", "command %s was committed with content %s; this retry carries %s" % (command["command_id"], prior[0], cdigest))
            conn.execute("ROLLBACK")
            return dict(json.loads(prior[1]), replayed=True)
        if conn.execute("SELECT 1 FROM nonces WHERE nonce=?", (command["nonce"],)).fetchone():
            raise StoreRefused("nonce_consumed", "nonce %s was consumed by an earlier command" % command["nonce"])
        touched = set(command["expected_versions"]) | {v for v in (command["parameters"].get("entity_id"), command["parameters"].get("receipt_id")) if _is_str(v)}
        before = _entities(conn, sorted(touched))
        for eid, expected in command["expected_versions"].items():
            actual = before.get(eid, {}).get("version", 0)
            if actual != expected:
                raise StoreRefused("stale_version", "entity %s is at version %r, the command expected %r" % (eid, actual, expected))
        reg = registry[command["operation"]]
        if "snapshot_id" in command["parameters"] and "transaction_transition" not in reg:
            raise StoreRefused("unregistered_inputs", "snapshot command requires a connection-local guard")
        owners = entity_owners(conn)
        # An owned command runs only the code its declaration names, whoever registered it.
        origin = owning_modules(owners).get(command["operation"])
        if origin is not None:
            problem = transition_origin_problem(reg.get("transaction_transition", reg.get("transition")), *origin)
            if problem is not None:
                raise StoreRefused("foreign_transition", "%s is owned by the code in %s: %s" % (command["operation"], origin[0], problem))
        if "transaction_transition" in reg:
            changes = reg["transaction_transition"](conn, command["parameters"], before)
        else:
            changes = reg["transition"](command["parameters"], before)
        for eid in changes:
            if eid not in command["expected_versions"]:
                raise StoreRefused("stale_version", "entity %s is written without an expected version: a command declares every version it depends on" % eid)
        for eid, new in changes.items():
            kinds = {new["kind"], before.get(eid, {}).get("kind")}
            if architecture_entity(eid, kinds) and not architecture_writer(command["operation"]):
                raise StoreRefused("entity_owned", "%s may not write %s: the architecture record is written only by %s"
                                   % (command["operation"], eid, ARCHITECTURE_OPERATION))
            for selector, value, owner, commands, _module, _digest in owners:
                hit = value in kinds if selector == "kind" else eid.startswith(value)
                if hit and command["operation"] not in commands:
                    raise StoreRefused("entity_owned", "%s may not write %s: %s %r belongs to %s, written only by %s"
                                       % (command["operation"], eid, selector, value, owner, ", ".join(commands)))
        before_versions = {eid: before.get(eid, {}).get("version", 0) for eid in sorted(set(before) | set(changes))}
        after_versions = dict(before_versions)
        transition = {}
        for eid, new in changes.items():
            after_versions[eid] = before_versions[eid] + 1
            edigest = digest_of({"kind": new["kind"], "data": new["data"], "version": after_versions[eid]})
            transition[eid] = {"kind": new["kind"], "data": new["data"], "version": after_versions[eid], "digest": edigest}
            conn.execute("INSERT INTO entities (id, kind, version, digest, data) VALUES (?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET "
                         "kind=excluded.kind, version=excluded.version, digest=excluded.digest, data=excluded.data",
                         (eid, new["kind"], after_versions[eid], edigest, json.dumps(new["data"], sort_keys=True)))
        p = command["parameters"]
        reservations = [{"id": p["reservation_id"], "ceiling": p["ceiling"], "delta": float(p["delta"])}] if command["operation"] == "reserve" else []
        effects = [{"id": p["effect_id"], "kind": p["kind"], "target": p["target"], "state": "obligated"}] if command["operation"] == "record_effect" else []
        seq, prev = _last_journal(conn)
        record = {"seq": seq + 1, "prev_digest": prev, "authority_generation": authority_generation, "command_id": command["command_id"],
                  "command_digest": cdigest, "principal": command["principal"], "signer": signer, "before_versions": before_versions,
                  "after_versions": after_versions, "transition": transition, "nonce": command["nonce"], "reservations": reservations, "effects": effects,
                  "receipt_refs": receipt_refs, "artifact_digests": list(command["artifact_digests"]), "encoding": JOURNAL_ENCODING}
        record["record_digest"] = journal_record_digest(record)
        signature = sign(journal_signed_bytes(record))
        if not _is_str(signature):
            raise StoreRefused("incomplete_transaction", "the signer returned no signature; an unsigned record is not appended")
        conn.execute("INSERT INTO journal (seq, prev_digest, record_digest, authority_generation, command_id, command_digest, principal, signer, signature, "
                     "before_versions, after_versions, transition, nonce, reservations, effects, receipt_refs, artifact_digests, encoding) "
                     "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                     (record["seq"], prev, record["record_digest"], authority_generation, command["command_id"], cdigest, command["principal"], signer, signature,
                      json.dumps(before_versions, sort_keys=True), json.dumps(after_versions, sort_keys=True), json.dumps(transition, sort_keys=True),
                      command["nonce"], json.dumps(reservations, sort_keys=True), json.dumps(effects, sort_keys=True),
                      json.dumps(receipt_refs), json.dumps(list(command["artifact_digests"])), JOURNAL_ENCODING))
        result = {"committed": True, "command_id": command["command_id"], "seq": record["seq"], "record_digest": record["record_digest"],
                  "after_versions": after_versions, "effects": [e["id"] for e in effects], "reservations": [r["id"] for r in reservations]}
        result["result_digest"] = digest_of({k: v for k, v in result.items() if k != "result_digest"})
        # The commands row first: nonces, reservations and effects reference it by foreign key.
        conn.execute("INSERT INTO commands (command_id, command_digest, result, result_digest, seq) VALUES (?,?,?,?,?)",
                     (command["command_id"], cdigest, json.dumps(result, sort_keys=True), result["result_digest"], record["seq"]))
        if command["operation"] == "reserve":
            conn.execute("INSERT INTO reservations (id, command_id, ceiling, delta) VALUES (?,?,?,?)", (p["reservation_id"], command["command_id"], p["ceiling"], float(p["delta"])))
        if command["operation"] == "record_effect":
            conn.execute("INSERT INTO effects (id, command_id, kind, target, state) VALUES (?,?,?,?,?)", (p["effect_id"], command["command_id"], p["kind"], p["target"], "obligated"))
        conn.execute("INSERT INTO nonces (nonce, command_id) VALUES (?,?)", (command["nonce"], command["command_id"]))
        # The publication cursor row is born in the same transaction as the record it will publish:
        # a committed sequence is visibly pending publication from the moment it exists (R23).
        conn.execute("INSERT INTO publication (seq, command_id, committed_at) VALUES (?,?,?)",
                     (record["seq"], command["command_id"], float(committed_at) if committed_at is not None else float(_now())))
        _kill_point("before_commit")
        if os.environ.get("VELDO_CONTROL_TEST_HARNESS") == "1" and os.environ.get("VELDO_CONTROL_KILL_AT") == "in_commit":
            conn.set_progress_handler(lambda: os.kill(os.getpid(), signal.SIGKILL), 1)
        conn.execute("COMMIT")
        conn.set_progress_handler(None, 0)
        _kill_point("after_commit")
        return dict(result, replayed=False)
    except sqlite3.IntegrityError as e:
        conn.execute("ROLLBACK")
        raise StoreRefused("foreign_key_violation", str(e))
    except sqlite3.OperationalError as e:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        if "readonly" in str(e).lower() or "read-only" in str(e).lower():
            raise StoreRefused("read_only_handle", "this handle cannot write (%s)" % e)
        raise
    except StoreRefused:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise

    finally:
        conn.command_transaction = False


# ---------------------------------------------------------------------------------------------
# Entity ownership: declared once per store, enforced by execute on every connection.
# ---------------------------------------------------------------------------------------------

def entity_owners(conn):
    """Every persisted declaration as (selector, value, owner, commands, module, module_digest), or
    [] when none exists."""
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (OWNERS_TABLE,)).fetchone():
        return []
    return [(r[0], r[1], r[2], tuple(json.loads(r[3])), r[4], r[5]) for r in conn.execute(
        "SELECT selector, value, owner, commands, module, module_digest FROM entity_owners ORDER BY selector, value")]


def owning_modules(owners):
    """{command: (module, module_digest)} for every command a declaration names."""
    return {command: (row[4], row[5]) for row in owners for command in row[3]}


def module_digest(path):
    """sha256 of a module file's bytes, or None when it cannot be read."""
    try:
        with open(path, "rb") as handle:
            return "sha256:" + hashlib.sha256(handle.read()).hexdigest()
    except OSError:
        return None


def transition_files(transition):
    """The resolved source file of every function a registered transition is, or holds: through
    bound methods and closure cells. None stands for a callable with no Python function code (a
    builtin, a partial, a callable object), whose source nothing here names, so it is never the
    declared module."""
    files, seen, pending = set(), set(), [transition]
    while pending:
        function = pending.pop()
        if id(function) in seen:
            continue
        seen.add(id(function))
        if hasattr(function, "__func__") and hasattr(function, "__self__"):
            pending.append(function.__func__)
            continue
        code = getattr(function, "__code__", None)
        if code is None or not hasattr(code, "co_filename") or not hasattr(function, "__closure__"):
            if callable(function) and not isinstance(function, type):
                files.add(None)
            continue
        files.add(os.path.realpath(code.co_filename))
        for cell in function.__closure__ or ():
            try:
                pending.append(cell.cell_contents)
            except ValueError:
                continue
    return files


def transition_origin_problem(transition, module, digest):
    """Why a registered transition is not the declared module's code, or None when it is."""
    files = transition_files(transition)
    if files != {module}:
        return "the registered transition runs code from %s" % ", ".join(sorted(str(f) for f in files - {module}) or ["nowhere"])
    if module_digest(module) != digest:
        return "%s no longer has the declared bytes %s" % (module, digest)
    return None


def _ownership_rows(owner, kinds, prefixes, module):
    if not _is_str(owner):
        raise StoreRefused("malformed_command", "an ownership declaration names its owner")
    if not _is_str(module):
        raise StoreRefused("malformed_command", "an ownership declaration names the module file whose code writes what it owns")
    module = os.path.realpath(module)
    digest = module_digest(module)
    if digest is None:
        raise StoreRefused("malformed_command", "the owning module %s cannot be read" % module)
    rows = []
    for selector, table in (("kind", kinds or {}), ("prefix", prefixes or {})):
        if not isinstance(table, dict):
            raise StoreRefused("malformed_command", "owned %ss map each value to its writing commands" % selector)
        for value, commands in table.items():
            if not _is_str(value) or isinstance(commands, str) or not commands or not all(_is_str(c) for c in commands):
                raise StoreRefused("malformed_command", "owned %s %r needs a value and at least one command" % (selector, value))
            builtin = sorted(set(commands) & set(COMMAND_REGISTRY))
            if builtin:
                # The store's own generic commands are what ownership keeps out; binding one to a
                # service's module would refuse it for every entity on every connection.
                raise StoreRefused("malformed_command", "owned %s %r names the store's generic command %s, which no service owns"
                                   % (selector, value, ", ".join(builtin)))
            rows.append((selector, value, owner, tuple(sorted(set(commands))), module, digest))
    if not rows:
        raise StoreRefused("malformed_command", "an ownership declaration owns at least one kind or prefix")
    return rows


def _occupied(conn, selector, value):
    if selector == "kind":
        return conn.execute("SELECT 1 FROM entities WHERE kind=? LIMIT 1", (value,)).fetchone() is not None
    return conn.execute("SELECT 1 FROM entities WHERE substr(id, 1, ?)=? LIMIT 1", (len(value), value)).fetchone() is not None


def declare_owners(conn, owner, kinds=None, prefixes=None, module=None):
    """Persist that the entities of each kind in `kinds`, and every entity whose id begins with a
    prefix in `prefixes`, are written only by the commands mapped to it, and that those commands are
    the code in the file `module` (the caller's own __file__), whose bytes the store digests now.
    Idempotent for the same declaration; ownership_conflict for a different one, for a command
    another declaration binds to other code, or for a first declaration of a kind or prefix that
    entities already occupy. Its own transaction, like the publication cursor's writes."""
    rows = _ownership_rows(owner, kinds, prefixes, module)
    if set(rows) <= set(entity_owners(conn)):
        return rows
    try:
        conn.execute("BEGIN IMMEDIATE")
    except sqlite3.OperationalError as e:
        raise StoreRefused("read_only_handle", "this handle cannot declare ownership (%s)" % e)
    try:
        conn.execute(_OWNERS_DDL)
        declared = {(r[0], r[1]): r for r in entity_owners(conn)}
        bound = owning_modules(declared.values())
        for row in rows:
            for command in row[3]:
                if bound.get(command, row[4:]) != row[4:]:
                    raise StoreRefused("ownership_conflict", "%s is bound to the code in %s (%s); %s declares %s (%s)"
                                       % (command, bound[command][0], bound[command][1], owner, row[4], row[5]))
            prior = declared.get(row[:2])
            if prior is not None:
                if prior != row:
                    raise StoreRefused("ownership_conflict", "%s %r is owned by %s (written only by %s); %s declares %s"
                                       % (row[0], row[1], prior[2], ", ".join(prior[3]), owner, ", ".join(row[3])))
                continue
            if _occupied(conn, row[0], row[1]):
                raise StoreRefused("ownership_conflict", "entities of %s %r exist already, written while nobody owned them"
                                   % (row[0], row[1]))
            conn.execute("INSERT INTO entity_owners (selector, value, owner, commands, module, module_digest) VALUES (?,?,?,?,?,?)",
                         (row[0], row[1], owner, json.dumps(list(row[3])), row[4], row[5]))
        conn.execute("COMMIT")
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    return rows


def bound_repository(conn, domain_uuid, repository_uuid):
    """The resolved path of the local repository bound to a domain's repository uuid, or None."""
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (BINDINGS_TABLE,)).fetchone():
        return None
    row = conn.execute("SELECT path FROM repository_bindings WHERE domain_uuid=? AND repository_uuid=?",
                       (domain_uuid, repository_uuid)).fetchone()
    return row[0] if row else None


def bind_repositories(conn, domain_uuid, repositories):
    """Persist that each repository uuid of `domain_uuid` in `repositories` is read from the Git
    repository at its path (resolved), all of them or none. Idempotent for the same paths;
    repository_binding_conflict for another path, because the first binding is the one every
    accepted commit of that repository has been checked against. Its own transaction, like
    declare_owners."""
    if not _is_str(domain_uuid) or not isinstance(repositories, dict) or not repositories or not all(
            _is_str(r) and _is_str(p) for r, p in repositories.items()):
        raise StoreRefused("malformed_command", "a repository binding names its domain and maps each repository to a path")
    targets = {repository: os.path.realpath(path) for repository, path in sorted(repositories.items())}
    if all(bound_repository(conn, domain_uuid, r) == t for r, t in targets.items()):
        return targets
    try:
        conn.execute("BEGIN IMMEDIATE")
    except sqlite3.OperationalError as e:
        raise StoreRefused("read_only_handle", "this handle cannot bind a repository (%s)" % e)
    try:
        conn.execute(_BINDINGS_DDL)
        for repository, target in targets.items():
            prior = bound_repository(conn, domain_uuid, repository)
            if prior is None:
                conn.execute("INSERT INTO repository_bindings (domain_uuid, repository_uuid, path) VALUES (?,?,?)",
                             (domain_uuid, repository, target))
            elif prior != target:
                raise StoreRefused("repository_binding_conflict", "repository %s of domain %s is read from %s in this store, not %s"
                                   % (repository, domain_uuid, prior, target))
        conn.execute("COMMIT")
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    return targets


# ---------------------------------------------------------------------------------------------
# Reading back: the state a replay is compared with, and the journal a replay reads.
# ---------------------------------------------------------------------------------------------

def export_journal(conn):
    """Every journal record as a plain mapping (JOURNAL_SIGNED_FIELDS plus signature), in sequence."""
    rows = conn.execute("SELECT seq, prev_digest, record_digest, authority_generation, command_id, command_digest, principal, signer, signature, "
                        "before_versions, after_versions, transition, nonce, reservations, effects, receipt_refs, artifact_digests, encoding "
                        "FROM journal ORDER BY seq").fetchall()
    out = []
    for r in rows:
        out.append({"seq": r[0], "prev_digest": r[1], "record_digest": r[2], "authority_generation": r[3], "command_id": r[4], "command_digest": r[5],
                    "principal": r[6], "signer": r[7], "signature": r[8], "before_versions": json.loads(r[9]), "after_versions": json.loads(r[10]),
                    "transition": json.loads(r[11]), "nonce": r[12], "reservations": json.loads(r[13]), "effects": json.loads(r[14]),
                    "receipt_refs": json.loads(r[15]), "artifact_digests": json.loads(r[16]), "encoding": r[17]})
    return out


def materialized_state(conn):
    """The live DOMAIN state a replay must reproduce: entities {id: {kind, version, digest, data}},
    reservations {id: {ceiling, delta, command_id}}, effects {id: {kind, target, state, command_id}}
    and consumed nonces {nonce: command_id}. Not just the entity table: a rebuild that loses spend
    holds, pending obligations or replay protection has not recovered the authority."""
    ents = conn.execute("SELECT id, kind, version, digest, data FROM entities ORDER BY id").fetchall()
    res = conn.execute("SELECT id, command_id, ceiling, delta FROM reservations ORDER BY id").fetchall()
    eff = conn.execute("SELECT id, command_id, kind, target, state FROM effects ORDER BY id").fetchall()
    non = conn.execute("SELECT nonce, command_id FROM nonces ORDER BY nonce").fetchall()
    return {"entities": {r[0]: {"kind": r[1], "version": r[2], "digest": r[3], "data": json.loads(r[4])} for r in ents},
            "reservations": {r[0]: {"command_id": r[1], "ceiling": r[2], "delta": r[3]} for r in res},
            "effects": {r[0]: {"command_id": r[1], "kind": r[2], "target": r[3], "state": r[4]} for r in eff},
            "nonces": {r[0]: r[1] for r in non}}


STATE_PARTS = ("entities", "reservations", "effects", "nonces")


def state_digest(state):
    """One digest over every part of a materialized state, the comparison a replay is judged by."""
    return digest_of({part: state.get(part, {}) for part in STATE_PARTS})


# ---------------------------------------------------------------------------------------------
# The publication cursor (R23): store-owned writes outside the command path, never a command.
# ---------------------------------------------------------------------------------------------

def _pub_row(r):
    return {"seq": r[0], "command_id": r[1], "committed_at": r[2], "export_id": r[3], "export_digest": r[4], "remote_commit": r[5],
            "remote": r[6], "ref": r[7], "acked_at": r[8], "durability": r[9], "dispatched_at": r[10], "backfilled": bool(r[11])}


_PUB_COLS = "seq, command_id, committed_at, export_id, export_digest, remote_commit, remote, ref, acked_at, durability, dispatched_at, backfilled"


def publication_gaps(conn):
    """Journal sequences with no publication row: history the replica would leave out."""
    return [r[0] for r in conn.execute("SELECT j.seq FROM journal j LEFT JOIN publication p ON p.seq = j.seq WHERE p.seq IS NULL ORDER BY j.seq").fetchall()]


def backfill_publication(path, now, mounts_text=None):
    """The EXPLICIT upgrade step for a store written before the publication cursor existed: one
    pending row per journal sequence lacking one, marked backfilled, committed_at = now, so the
    publisher exports the whole history in order. Returns the sequences backfilled."""
    conn = open_store(path, mounts_text=mounts_text, allow_unbackfilled=True)
    try:
        gaps = publication_gaps(conn)
        if gaps:
            conn.execute("BEGIN IMMEDIATE")
            for seq in gaps:
                cid = conn.execute("SELECT command_id FROM journal WHERE seq=?", (seq,)).fetchone()[0]
                conn.execute("INSERT INTO publication (seq, command_id, committed_at, backfilled) VALUES (?,?,?,1)", (seq, cid, float(now)))
            conn.execute("COMMIT")
        return gaps
    finally:
        conn.close()


def pending_exports(conn):
    """Committed sequences with no off-host acknowledgement, in order."""
    return [_pub_row(r) for r in conn.execute("SELECT %s FROM publication WHERE acked_at IS NULL ORDER BY seq" % _PUB_COLS).fetchall()]


def publication_row(conn, seq):
    r = conn.execute("SELECT %s FROM publication WHERE seq=?" % _PUB_COLS, (seq,)).fetchone()
    return _pub_row(r) if r else None


def publication_row_for_command(conn, command_id):
    r = conn.execute("SELECT %s FROM publication WHERE command_id=?" % _PUB_COLS, (command_id,)).fetchone()
    return _pub_row(r) if r else None


def record_export(conn, seq, export_id, export_digest):
    """Bind the sequence to its ONE export identity and digest; a different identity for a sequence
    that already has one is refused (a second export for one sequence never exists)."""
    row = publication_row(conn, seq)
    if row is None:
        raise StoreRefused("incomplete_transaction", "seq %r has no publication row" % (seq,))
    if row["export_id"] not in (None, export_id) or row["export_digest"] not in (None, export_digest):
        raise StoreRefused("command_content_conflict", "seq %r is bound to export %s (%s); %s (%s) is a second identity" % (seq, row["export_id"], row["export_digest"], export_id, export_digest))
    _write(conn, "UPDATE publication SET export_id=?, export_digest=? WHERE seq=?", (export_id, export_digest, seq))


def acknowledge_export(conn, seq, remote_commit, remote, ref, acked_at, durability):
    """Persist the acknowledgement: the remote's own answer that `ref` names `remote_commit` holding
    this sequence's export, GRADED: off_host (a remote whose contract the operations authority
    qualified) or protocol_only (a local remote; never success). Idempotent for the same commit; a
    different commit for an acknowledged sequence is refused."""
    if durability not in DURABILITY_GRADES:
        raise StoreRefused("malformed_command", "durability is one of %s" % (DURABILITY_GRADES,))
    row = publication_row(conn, seq)
    if row is None or row["export_id"] is None:
        raise StoreRefused("incomplete_transaction", "seq %r has no export to acknowledge" % (seq,))
    if row["remote_commit"] not in (None, remote_commit):
        raise StoreRefused("command_content_conflict", "seq %r was acknowledged at %s; %s is a different replica commit" % (seq, row["remote_commit"], remote_commit))
    if row["acked_at"] is None:
        _write(conn, "UPDATE publication SET remote_commit=?, remote=?, ref=?, acked_at=?, durability=? WHERE seq=?", (remote_commit, remote, ref, float(acked_at), durability, seq))


def acknowledged_exports(conn):
    """Every acknowledged sequence, in order (what the remote must still hold)."""
    return [_pub_row(r) for r in conn.execute("SELECT %s FROM publication WHERE acked_at IS NOT NULL ORDER BY seq" % _PUB_COLS).fetchall()]


def undispatched_exports(conn):
    """Acknowledged OFF-HOST sequences whose external dispatch has not been recorded: the durable
    dispatch obligation a crash between acknowledgement and dispatch leaves behind."""
    return [_pub_row(r) for r in conn.execute("SELECT %s FROM publication WHERE acked_at IS NOT NULL AND durability='off_host' AND dispatched_at IS NULL ORDER BY seq" % _PUB_COLS).fetchall()]


def mark_dispatched(conn, seq, at):
    row = publication_row(conn, seq)
    if row is None or row["acked_at"] is None:
        raise StoreRefused("incomplete_transaction", "seq %r is not acknowledged; nothing is dispatched before acknowledgement" % (seq,))
    if row["dispatched_at"] is None:
        _write(conn, "UPDATE publication SET dispatched_at=? WHERE seq=?", (float(at), seq))


def pause_publication(conn, reason, at):
    _write(conn, "INSERT INTO publication_control (id, paused_reason, paused_at) VALUES (1,?,?) ON CONFLICT(id) DO UPDATE SET paused_reason=excluded.paused_reason, paused_at=excluded.paused_at",
           (reason, float(at)))


def resume_publication(conn):
    _write(conn, "UPDATE publication_control SET paused_reason=NULL, paused_at=NULL WHERE id=1", ())


def publication_watermark(conn):
    """{last_durable_seq (off-host acknowledged), last_acknowledged_seq (any grade), local_committed_seq,
    paused_reason, paused_at}: the R23 numbers."""
    durable = conn.execute("SELECT MAX(seq) FROM publication WHERE acked_at IS NOT NULL AND durability='off_host'").fetchone()[0]
    proto = conn.execute("SELECT MAX(seq) FROM publication WHERE acked_at IS NOT NULL").fetchone()[0]
    local = conn.execute("SELECT MAX(seq) FROM journal").fetchone()[0]
    ctl = conn.execute("SELECT paused_reason, paused_at FROM publication_control WHERE id=1").fetchone()
    return {"last_durable_seq": durable or 0, "last_acknowledged_seq": proto or 0, "local_committed_seq": local or 0,
            "paused_reason": ctl[0] if ctl else None, "paused_at": ctl[1] if ctl else None}


def _write(conn, sql, params):
    """One store-owned write in its own transaction; a read-only handle refuses by name."""
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(sql, params)
        conn.execute("COMMIT")
    except sqlite3.OperationalError as e:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        if "readonly" in str(e).lower() or "read-only" in str(e).lower():
            raise StoreRefused("read_only_handle", "this handle cannot write (%s)" % e)
        raise


def table_snapshot(conn):
    """Every domain table's rows, for the crash matrix to compare a reopened store with the
    complete old or complete new state."""
    snap = {}
    for t in DOMAIN_TABLES:
        snap[t] = [tuple(r) for r in conn.execute("SELECT * FROM %s ORDER BY 1" % t).fetchall()]
    return snap
