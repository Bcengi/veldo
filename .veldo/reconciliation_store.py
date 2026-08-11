#!/usr/bin/env python3
"""The RECONCILIATION STORE: the ONE IMPURE EDGE of the incident reconciliation (W8 of PLAN-0012, outcome O5).

The pass above (.veldo/incident_reconcile.py) is a set of PURE functions over an injected seam; this module is
that seam, and the only place the reconciliation writes anything. It is a sibling organ, extracted so the two
mechanisms that decide whether a write happens at all have ONE HOME EACH and are read together:

  THE APPEND-ONLY COMPARE-AND-SWAP. A receipt is keyed by the content-addressed settlement id. A replay of the
  same settlement is a NO-OP that returns the existing receipt and appends NO second record and NO second
  event; a DIFFERENT record under an existing id REFUSES rather than overwriting; and a record that EXISTS and
  CANNOT BE READ (a crash-truncated file, a corrupt payload, a payload that is not a mapping) is a CONFLICT,
  NEVER AN ABSENCE. That last distinction is load bearing: a truncated receipt read as absent would be
  OVERWRITTEN and would append a SECOND incident.closed for one incident, and a duplicated incident.closed
  silently corrupts every measure derived from the event stream. Absence is None; unreadable is the UNREADABLE
  sentinel, which is deliberately neither None nor a mapping so no caller can mistake one for the other.

  THE DRAFT PATH GUARD. The machine never writes a draft into the action whitelist STORE the executor reads and
  never authors into the SPEC CORPUS. The guard RESOLVES the target to a real absolute path before deciding, so
  a '..' traversal and a symlinked drafts directory both land on their real location, and it compares
  CASE-INSENSITIVELY, because this engine ships to macOS and Windows adopters whose filesystems are case
  insensitive and where '.VELDO/Actions' IS the whitelist store. A target that cannot be resolved at all is
  REFUSED: a target we cannot resolve is a target we cannot clear (fail closed).

The BASE class owns both, so every backend upholds them identically and a subclass implements only the
underscore primitives (the shape .veldo/request_reconcile.py established for the settlement store). The gate
drives the deterministic in-memory FakeReconciliationStore; FilesystemReconciliationStore is the per-repo wired
path, driven in the gate over a TEMPORARY tree and never over this repository.

Pure stdlib. It reads the action whitelist store's LOCATION from the shipped .veldo/action.py rather than
restating it, so the guard and the store cannot disagree about where the whitelist lives. It starts no process,
lays no timer, spawns nothing detached (NG3), and reaches no network or live system (NG1).
"""
import hashlib
import importlib.util
import json
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _load(name, rel):
    """Load a sibling module by path, the codebase convention: one owner per contract, no reimplementation."""
    spec = importlib.util.spec_from_file_location(name, _HERE / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# The action whitelist store (WARP-1205, W5): READ here for exactly one fact, the store's LOCATION, so the path
# guard and the store the executor reads can never disagree. Nothing is executed and no action is loaded.
_ACT = _load("veldo_action_for_reconciliation_store", "action.py")

# The declared DRAFT home, per repo (a directory the engine glob does not sweep, the posture of .veldo/incidents/
# and .veldo/actions/). Drafts are generated artifacts a human promotes; the engine never ships them.
DEFAULT_DRAFTS_DIR = Path(".veldo") / "incident_drafts"

# THE FORBIDDEN DRAFT ROOTS. The whitelist STORE segments are READ from the shipped store rather than restated.
# The spec corpus root is a LITERAL here, honestly: no engine module owns the corpus root - validate.py,
# plan.py, frontier.py and intent_corpus.py each build `root / "specs"` inline, so there is no owner to read it
# from. This literal is the price of that gap, not a claim that both roots are derived; giving the corpus root an
# owner is the fix, and it belongs to whichever organ next needs it.
_STORE_SEGMENTS = tuple(_ACT.default_actions_dir("").parts)
SPEC_CORPUS_SEGMENT = "specs"
_STORE_FOLDED = tuple(segment.casefold() for segment in _STORE_SEGMENTS)
_SPEC_CORPUS_FOLDED = SPEC_CORPUS_SEGMENT.casefold()

# What forbidden_draft_target names when the target cannot be resolved to a real path at all.
UNRESOLVABLE_TARGET = "an unresolvable path (fail closed)"

# The refusals this store PRODUCES, named here because this module owns the decisions behind them. The pass
# above folds these names into its one closed taxonomy rather than declaring a second copy.
REFUSE_DRAFT_PATH_FORBIDDEN = "forbidden_draft_path"
REFUSE_RECEIPT_CONFLICT = "reconciliation_receipt_conflict"
REFUSE_RECEIPT_UNREADABLE = "reconciliation_receipt_unreadable"


class ReconcileError(ValueError):
    """A malformed CALL into the reconciliation or its store (no incident id, no store, a non-mapping record),
    raised BY NAME so a bad call never silently no-ops. A lifecycle gap is not an error: it is a REFUSED result
    naming one of the taxonomy's refusals, which is the product."""


class _UnreadableRecord:
    """The type of UNREADABLE. It is deliberately NOT None (which means ABSENT) and deliberately NOT a mapping
    (so no caller can read fields off a corrupt record), which is what makes 'exists but unreadable' a state a
    caller must handle rather than a state that silently degrades into 'nothing is recorded here'."""

    __slots__ = ()

    def __repr__(self):
        return "<unreadable reconciliation receipt>"


UNREADABLE = _UnreadableRecord()

_TOKEN_OK = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"


def _require(value, name):
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ReconcileError("%s must be a non-empty value" % name)
    return value


def _token(v):
    """A filesystem-safe token for a draft basename or a receipt filename; the verbatim value is recorded IN
    the artifact, so this never has to be reversible."""
    s = "".join(c if c in _TOKEN_OK else "_" for c in str("" if v is None else v))
    return s.strip("._-") or "unnamed"


def _digest_bytes(blob):
    return "sha256:" + hashlib.sha256(blob).hexdigest()[:16]


def _same_receipt(a, b):
    """Whether two receipts are the SAME settlement recorded twice, as opposed to a conflict under one id."""
    return json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str)


# --- the draft path guard (one home, resolved and case-insensitive, fail closed) -------------------
def _real_parts(path):
    """The target's REAL absolute path parts, CASE FOLDED: a relative target anchored to the working directory,
    every '..' collapsed, and every symlink in the existing prefix followed, so a drafts directory that IS a
    symlink into the whitelist store is judged by where it actually lands. None when the target cannot be
    resolved at all (a symlink loop, a parent that cannot be read), which the guard treats as FORBIDDEN."""
    try:
        resolved = Path(path).resolve()
    except (OSError, RuntimeError, ValueError):
        return None
    return tuple(part.casefold() for part in resolved.parts)


def forbidden_draft_target(path):
    """The forbidden root a draft target falls inside, or None when the target is clear. The machine never
    writes into the action whitelist STORE the executor reads (its location read from the shipped store, not
    restated) and never authors into the SPEC CORPUS. The decision is made on the RESOLVED, CASE-FOLDED path,
    so '.veldo/incident_drafts/../actions', a symlinked drafts directory, an absolute target, and '.VELDO/Actions'
    on a case-insensitive filesystem are all judged by where the write really lands; an unresolvable target
    refuses too. A forbidden segment ANYWHERE above the target refuses, which can refuse an innocent tree whose
    absolute path happens to contain one - that direction is deliberate, because over-refusing a draft costs a
    human one move while under-refusing writes into the store the executor reads."""
    parts = _real_parts(path)
    if parts is None:
        return UNRESOLVABLE_TARGET
    for i, segment in enumerate(parts):
        if segment == _SPEC_CORPUS_FOLDED:
            return "%s/" % SPEC_CORPUS_SEGMENT
        if parts[i:i + len(_STORE_FOLDED)] == _STORE_FOLDED:
            return "%s/" % "/".join(_STORE_SEGMENTS)
    return None


# --- the append-only compare-and-swap store, which also owns the draft writes ----------------------
class ReconciliationStore:
    """The one impure edge: an APPEND-ONLY COMPARE-AND-SWAP receipt store keyed by the content-addressed id,
    which also owns the DRAFT writes. The BASE owns the compare-and-swap, the unreadable-record refusal, and the
    draft PATH GUARD so every backend upholds all three identically (the shape request_reconcile established);
    a subclass implements only the underscore primitives, so idempotency and the path guard each have ONE home.
    A subclass that OVERRIDES settle or put_draft loses them, which is why the primitives are what a backend is
    expected to implement."""

    def __init__(self, drafts_dir=None):
        self.drafts_dir = Path(drafts_dir) if drafts_dir is not None else Path(DEFAULT_DRAFTS_DIR)

    # --- the primitives a backend implements --------------------------------
    def _get(self, rec_id):
        raise NotImplementedError

    def _append(self, rec_id, record, events):
        raise NotImplementedError

    def _read_draft(self, rel):
        raise NotImplementedError

    def _write_draft(self, rel, content):
        raise NotImplementedError

    # --- the seam the reconciliation settles through ------------------------
    def get(self, rec_id):
        """The receipt recorded under rec_id: the record, None when NOTHING is recorded there, or UNREADABLE
        when a record EXISTS and cannot be read or parsed. Read only. A caller must tell the three apart: an
        unreadable receipt is a CONFLICT, never an absence."""
        _require(rec_id, "reconciliation id")
        return self._get(rec_id)

    def settle(self, rec_id, record, events):
        """Write the receipt and append the event(s) through the APPEND-ONLY COMPARE-AND-SWAP. Returns
        ("written", record) when this call wrote them, ("exists", existing) when the SAME settlement was already
        recorded (a REPLAY: no second record, no second event), ("conflict", existing) when a DIFFERENT record
        occupies the id, and ("unreadable", None) when a record EXISTS under the id and cannot be read. The last
        three refuse; nothing is ever overwritten."""
        _require(rec_id, "reconciliation id")
        if not isinstance(record, dict):
            raise ReconcileError("a reconciliation receipt must be a mapping")
        existing = self._get(rec_id)
        # AN EXISTING-BUT-UNREADABLE RECEIPT IS A CONFLICT, NEVER AN ABSENCE. Read as absent it would be
        # OVERWRITTEN and would append a SECOND incident.closed for one incident, corrupting every measure
        # derived from the stream. Neutralizing the backend's sentinel (the anti-vacuity tooth) is exactly
        # that fail-open; the real path refuses and leaves the corrupt file for a human to resolve.
        if existing is UNREADABLE:
            return "unreadable", None
        if existing is not None:
            # THE COMPARE-AND-SWAP. Neutralizing this comparison lets a CONFLICTING write pass as a
            # benign replay (the anti-vacuity tooth); the real path refuses and never overwrites.
            if not _same_receipt(existing, record):
                return "conflict", existing
            return "exists", existing
        self._append(rec_id, record, list(events or []))
        return "written", record

    def put_draft(self, rel, content):
        """Write ONE draft into the declared DRAFT directory, once. Returns {path, outcome, digest} or {path,
        refused, detail}. THE PATH GUARD: the target is RESOLVED to a real absolute path and compared
        case-insensitively, and a target inside the action whitelist store or the spec corpus - or one that
        cannot be resolved at all - REFUSES BY NAME. An existing draft is never overwritten (a human may be
        editing it) and its digest is read from what is ACTUALLY there."""
        target = Path(self.drafts_dir) / rel
        forbidden = forbidden_draft_target(target)
        if forbidden is not None:
            return {"path": rel, "refused": REFUSE_DRAFT_PATH_FORBIDDEN,
                    "detail": "the draft target %s is FORBIDDEN (%s), judged on its RESOLVED path: the machine "
                              "never writes a draft into the action whitelist store the executor reads and "
                              "never authors into the spec corpus, so promotion stays a HUMAN act (NG2)"
                              % (target, forbidden)}
        existing = self._read_draft(rel)
        if existing is not None:
            return {"path": rel, "outcome": "exists", "digest": _digest_bytes(existing)}
        self._write_draft(rel, content)
        wrote = self._read_draft(rel)
        return {"path": rel, "outcome": "created",
                "digest": _digest_bytes(wrote if wrote is not None else content.encode())}


class FakeReconciliationStore(ReconciliationStore):
    """Deterministic in-memory store for the gate (no filesystem, no network) recording every receipt, event,
    and draft, and modelling the compare-and-swap and path guard concretely. receipts={id: record} pre-seeds a
    prior settlement, so a replay and a conflicting write are both provable; seeding UNREADABLE under an id
    models a receipt that exists and cannot be read."""

    def __init__(self, receipts=None, drafts_dir=None):
        ReconciliationStore.__init__(self, drafts_dir)
        self._receipts = dict(receipts or {})
        self._records = []
        self._events = []
        self._drafts = {}

    def _get(self, rec_id):
        return self._receipts.get(rec_id)

    def _append(self, rec_id, record, events):
        self._receipts[rec_id] = record
        self._records.append(record)
        self._events.extend(events)

    def _read_draft(self, rel):
        return self._drafts.get(str(rel))

    def _write_draft(self, rel, content):
        self._drafts[str(rel)] = content.encode()

    # --- observation helpers for tests (read only) --------------------------
    def receipts(self):
        return sorted(self._receipts)

    def records(self):
        return [dict(r) for r in self._records]

    def events(self):
        return [dict(e) for e in self._events]

    def drafts(self):
        return {k: v.decode() for k, v in self._drafts.items()}

    def count(self):
        return len(self._records)

    def digest(self):
        """A stable JSON string of the whole store for a before-and-after assertion. The emitter's event ids and
        timestamps are included deliberately: a replay that appended a second event would change this string."""
        return json.dumps({"receipts": sorted(self._receipts), "records": self._records,
                           "events": self._events, "drafts": sorted(self._drafts)},
                          sort_keys=True, default=str)


class FilesystemReconciliationStore(ReconciliationStore):
    """The per-repo wired store: receipts under .veldo/reconciliations/<id>.json (the record file IS the
    append-only compare-and-swap marker), events appended to .veldo/events.jsonl, drafts under the declared
    drafts directory. Stdlib file operations only; it starts no process and lays no timer. The gate drives it
    over a TEMPORARY tree, never this repository."""

    def __init__(self, root, drafts_dir=None):
        self._root = Path(root)
        ReconciliationStore.__init__(
            self, drafts_dir if drafts_dir is not None else self._root / DEFAULT_DRAFTS_DIR)

    def _receipt_path(self, rec_id):
        return self._root / ".veldo" / "reconciliations" / ("%s.json" % _token(rec_id))

    def _get(self, rec_id):
        """The recorded receipt, None when the file DOES NOT EXIST, or UNREADABLE when it exists and cannot be
        read or parsed into a mapping. Absence and corruption are different answers: a corrupt receipt read as
        an absence would be overwritten and would double-emit the close event."""
        p = self._receipt_path(rec_id)
        if not p.is_file():
            return None  # ABSENT: nothing is recorded under this id
        try:
            record = json.loads(p.read_text())
        except (OSError, ValueError):
            return UNREADABLE  # PRESENT and unreadable (truncated, corrupt, unopenable): a CONFLICT
        return record if isinstance(record, dict) else UNREADABLE

    def _append(self, rec_id, record, events):
        p = self._receipt_path(rec_id)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(record, indent=2, sort_keys=True, default=str) + "\n")
        if events:
            log = self._root / ".veldo" / "events.jsonl"
            log.parent.mkdir(parents=True, exist_ok=True)
            with log.open("a") as f:
                for event in events:
                    f.write(json.dumps(event, default=str) + "\n")

    def _read_draft(self, rel):
        try:
            return (Path(self.drafts_dir) / rel).read_bytes()
        except OSError:
            return None

    def _write_draft(self, rel, content):
        p = Path(self.drafts_dir) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
