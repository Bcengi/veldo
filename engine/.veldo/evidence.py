#!/usr/bin/env python3
"""VELDO evidence plane (veldo.evidence/v1): the read-only access physics the production
support responder investigates through, and its structural validator that fails closed.

This is the W2 organ of PLAN-0012 and the machinery behind Invention #3's design center:
an agent with production access can destroy a company by simply doing the wrong thing
there, so its safety cannot be a policy it follows - it has to be an architecture it
cannot escape. The evidence plane is where the responder investigates, built as read-only
PHYSICS: the credential the responder runs on cannot write, not because it agrees not to
but because the write path structurally does not exist. Everything here is proven OFFLINE
against a FAKE plane; wiring the plane to any real source is a separate, per-system,
human-approved enablement act (NG1), and the live edge fails loud so nothing connects live
inside the gate.

THE DESIGN CENTER this module ENCODES, fail closed (the refusals are the product, C1):

  THE CREDENTIAL CANNOT WRITE, AND THAT IS PHYSICS. Two layers. Structurally, the
  responder's types carry no write capability: a ReadOnlyCredential yields only a
  ReadHandle, and the read handle has only a query operation - there is no write, insert,
  update, delete, execute, or mutate method, so a write cannot even be expressed. And at
  the seam, even a raw crafted write submitted with the responder's credential is refused,
  because the plane authorizes a write by the credential's GRANTED ROLE and a read-only
  credential grants only read. The refusal is proven NON-VACUOUS: a write-granted
  credential (which the responder never holds) applies the same write, so it is the
  read-only grant that makes the write impossible, not a globally disabled store.

  READ-ONLY IS NOT HARMLESS, so the read path is a BROKER, not a raw connection. Reads can
  exfiltrate, overload, or cross tenant lines. The broker enforces templated query shapes
  (only a shape the source declares; a free-form query is refused), a row-limit quota, a
  rate quota, and a per-query timeout, REDACTS the source's declared sensitive fields from
  every row BEFORE the row enters the caller's context, and AUDITS every query (allowed or
  refused) in a full query audit log.

  NEVER A PRIMARY, AND NEVER A RAW SECRET. A declared source is a read-only kind (logs,
  metrics, traces, a read replica), never a primary; its access is read_only; and its
  credential is a secret REFERENCE resolved at the seam (an env variable or an OS keychain
  reference, per D4), never a raw literal in a file, prompt, proof, or log. The config
  validator refuses each of these at contract time.

This module validates the source declaration STRUCTURALLY, the same way .veldo/incident.py
and .veldo/decision.py validate theirs: required fields present, closed vocabularies
honored, a field rejected at record time when it is absent. It reuses the caller's front
matter parser (validate.parse_yamlish) and failure reporter (validate.fail), so it adds no
second YAML parser and no import cycle. Dependency free by construction: it imports only
pathlib and reads no global state (the environment used to resolve a secret reference is
injected by the caller), so it starts no process, thread, or timer.

Two postures, both shared with the sibling contract organs:
  ADOPTION SAFE. A repository with no .veldo/evidence/ directory is untouched:
  check_evidence_dir stands down and returns clean, so a repository that never configures
  the responder is byte-identically unaffected. The moment a config exists it is validated
  and fails closed.
  FAIL CLOSED. A malformed config, a source declared as a primary (or any out-of-vocabulary
  kind), an access that is not read_only, a secret given as a raw literal, a missing or
  non-positive row/rate/timeout quota, a source that declares no templated query shapes,
  and a duplicate source id each REFUSE by name.

The responder investigation loop (WARP-1204, W4), the intent corpus (WARP-1203, W3), the
action whitelist (WARP-1205, W5), the execution organ (WARP-1206, W6), and the two-key rule
(WARP-1207, W7) are honestly later items; nothing here investigates, proposes, or executes,
and the evidence plane has no write path, live or fake.
"""
from pathlib import Path

SCHEMA = "veldo.evidence/v1"

# The read-only source vocabulary: the kinds a read-only evidence source may be. A PRIMARY
# is never a valid evidence source - the responder reads replicas and the log, metric, and
# trace stores, never the primary a write could reach.
READ_ONLY_KINDS = {"logs", "metrics", "traces", "read_replica"}
# The one access mode a source may declare. A source declared writable is refused at
# contract time: read-only is the physics, and the config layer refuses to describe
# anything else.
ACCESS_READ_ONLY = "read_only"
# The recognized secret-reference schemes (D4): a credential is resolved at the seam from
# an environment variable or an OS keychain reference, never a raw literal.
SECRET_REF_SCHEMES = ("env:", "keychain:")

# The grants a role can carry. The responder's credential carries only read; write is the
# grant a read-only credential never has, and the credential seam authorizes a write by
# this grant, never by inspecting the query text or asking a policy.
GRANT_READ = "read"
GRANT_WRITE = "write"

# What a redacted field reads as in a row that reaches context. The field is replaced, not
# dropped, so the row shape is stable and the absence of a leak is visible.
REDACTION_MARKER = "***redacted***"


class EvidencePlaneError(RuntimeError):
    """The evidence plane refused, a config is malformed, or a live edge was reached.
    Raised by name so a refusal never silently no-ops (parallels IncidentContractError)."""


class EvidenceWriteRefused(EvidencePlaneError):
    """A write was refused AT THE CREDENTIAL SEAM: the submitting credential grants no
    write. A distinct type so the credential-seam negative test binds to the seam refusal
    specifically, not to any error that happens to be raised."""


def default_evidence_dir(root=None):
    return Path(root or ".") / ".veldo" / "evidence"


def _is_str(v):
    return isinstance(v, str) and v.strip() != ""


def _as_list(v):
    return v if isinstance(v, list) else []


def _is_pos_int(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 1


def _is_secret_ref(v):
    return _is_str(v) and any(v.startswith(s) for s in SECRET_REF_SCHEMES)


# --- the source declaration and its structural validator ---------------------------------

def _load(path, parse):
    p = Path(path)
    try:
        text = p.read_text()
    except OSError as e:
        raise EvidencePlaneError("evidence-plane config unreadable: %s" % e)
    try:
        data = parse(text)
    except ValueError as e:
        raise EvidencePlaneError("evidence-plane config outside the record subset: %s" % e)
    if not isinstance(data, dict):
        raise EvidencePlaneError("evidence-plane config must be a mapping at the top level")
    return data


def load_plane(path, parse):
    """Parse an evidence-plane config through the caller's front-matter parser (the VELDO
    yamlish subset). The single place a config is read, so the responder loop (W4) reuses
    it rather than parsing the file a second way."""
    return _load(path, parse)


def validate_plane(data, root, record_path, fail):
    """Structural validation of one parsed veldo.evidence/v1 config. Reports each problem
    through fail(name, msg) and returns the error count. Pure over the dict, so it is
    reused by the directory scan and the single-file entry point.

    This is where the read-only physics becomes structural at the CONFIG layer. Every
    declared source is a read-only kind (never a primary), its access is read_only, its
    credential is a secret reference (never a raw literal, D4), it declares its templated
    query shapes and its row, rate, and timeout quotas, and it names the sensitive fields
    it redacts before context. A source that violates any of these is refused by name."""
    errs = 0
    name = str(record_path)

    if data.get("schema") != SCHEMA:
        errs += fail(name, "schema must be %r (got %r)" % (SCHEMA, data.get("schema")))
    if not _is_str(data.get("id")):
        errs += fail(name, "missing or empty required field: id")

    sources = _as_list(data.get("sources"))
    if not sources:
        errs += fail(name, "no sources: an evidence plane with no declared read-only sources describes nothing to investigate")
    seen_ids = []
    for s in sources:
        if not isinstance(s, dict) or not _is_str(s.get("id")):
            errs += fail(name, "each source needs an id")
            continue
        sid = s["id"]
        seen_ids.append(sid)

        # NEVER A PRIMARY: the kind is a read-only source kind. A primary (or any kind
        # outside the vocabulary) is refused - the responder reads replicas and log,
        # metric, and trace stores, never the primary a write could reach.
        kind = s.get("kind")
        if kind not in READ_ONLY_KINDS:
            errs += fail(name, "source %s: kind must be one of %s and NEVER a primary (got %r): the responder reads replicas and log, metric, and trace stores, never the primary a write could reach" % (sid, sorted(READ_ONLY_KINDS), kind))

        # READ ONLY: the access is read_only. A source declared writable is refused - the
        # config layer refuses to describe anything the responder could write to.
        access = s.get("access")
        if access != ACCESS_READ_ONLY:
            errs += fail(name, "source %s: access must be %r (got %r): the evidence plane is read-only physics; a writable source is refused at contract time" % (sid, ACCESS_READ_ONLY, access))

        # NEVER A RAW SECRET (D4): the credential is a secret reference (env: or keychain:),
        # resolved at the seam, never a raw literal in a file, prompt, proof, or log.
        if not _is_secret_ref(s.get("secret_ref")):
            errs += fail(name, "source %s: secret_ref must be a reference beginning with one of %s and NEVER a raw literal (D4): a credential is never a raw secret in a file, prompt, proof, or log" % (sid, list(SECRET_REF_SCHEMES)))

        # TEMPLATED SHAPES: the source declares the query shapes it permits. Without them
        # the broker would have to allow free-form queries, and a free-form read is exactly
        # the exfiltration path read-only is not harmless against.
        if not _as_list(s.get("templates")):
            errs += fail(name, "source %s: templates must be a non-empty list of the query shapes this source permits (free-form queries are not allowed; the broker refuses any undeclared shape)" % sid)

        # QUOTAS AND TIMEOUT: a row cap, a rate cap, and a per-query timeout, each a positive
        # integer. Reads can overload, so the limits are required, not optional.
        for q in ("max_rows", "rate_max", "timeout_ms"):
            if not _is_pos_int(s.get(q)):
                errs += fail(name, "source %s: %s must be a positive integer (a read-only source still needs a row cap, a rate cap, and a timeout; reads can overload)" % (sid, q))

        # REDACTION: the sensitive fields stripped before context. A list (possibly empty
        # for a source that carries no PII), never a scalar; a scalar would silently redact
        # nothing.
        redact = s.get("redact")
        if redact is not None and not isinstance(redact, list):
            errs += fail(name, "source %s: redact, when present, must be a list of the sensitive field names redacted before context" % sid)

    for sid in sorted(set(seen_ids)):
        if seen_ids.count(sid) > 1:
            errs += fail(name, "duplicate source id %r across the plane's sources (an ambiguous reference)" % sid)

    return errs


def sources_by_id(plane):
    """{source_id: source-config-dict} for a parsed plane. The one place a source is looked
    up, so the broker and the credential seam agree on what a source is."""
    out = {}
    for s in _as_list(plane.get("sources")):
        if isinstance(s, dict) and _is_str(s.get("id")):
            out.setdefault(s["id"], s)
    return out


# --- the credential seam: read-only PHYSICS ----------------------------------------------

class _ResolvedSecret:
    """An opaque marker for a secret resolved at the seam. It holds the REFERENCE it was
    resolved from, never the raw value, and it redacts itself in every string form, so a
    secret can never leak into a context, a proof, a log, or an audit entry (C5/D4)."""

    __slots__ = ("_ref",)

    def __init__(self, ref):
        self._ref = ref

    def __repr__(self):
        return "<ResolvedSecret ref=%r value=%s>" % (self._ref, REDACTION_MARKER)
    __str__ = __repr__


def resolve_secret_ref(ref, env=None, allow_keychain_offline=False):
    """Resolve a secret REFERENCE at the seam (D4). ref must be a reference:
      env:NAME       resolved from the injected environment mapping (env); the module
                     reads no global state, so the caller passes the environment in.
      keychain:NAME  an OS keychain reference; resolving it is a live per-system act, so
                     offline it FAILS LOUD unless allow_keychain_offline names a stub.
    A raw literal (no recognized scheme) is REFUSED: a credential is never a raw secret.
    Returns a _ResolvedSecret marker; the raw value is used only to authenticate and never
    returned into any context."""
    if not _is_secret_ref(ref):
        shown = "***" if _is_str(ref) else ref
        raise EvidencePlaneError("secret must be a reference beginning with one of %s and never a raw literal (D4): got %r" % (list(SECRET_REF_SCHEMES), shown))
    scheme, _, name = ref.partition(":")
    if scheme == "env":
        table = env if isinstance(env, dict) else {}
        if name not in table:
            raise EvidencePlaneError("secret reference %r is unresolved: the injected environment has no %r (fail closed)" % (ref, name))
        return _ResolvedSecret(ref)
    # keychain: a live per-system resolution
    if allow_keychain_offline:
        return _ResolvedSecret(ref)
    raise EvidencePlaneError("keychain secret resolution is a live per-system act; inject a real keychain adapter at enablement (no live resolution in the gate)")


class ReadHandle:
    """The ONLY handle a read-only credential yields. It exposes a single read operation,
    query(), and nothing else: there is no write, insert, update, delete, execute, or
    mutate method on this type. The ABSENCE of a write method is the physics - a write
    cannot be expressed through the responder's handle, not because a flag forbids it but
    because the capability is not on the type."""

    def __init__(self, credential, plane, broker):
        self._credential = credential
        self._plane = plane
        self._broker = broker

    def query(self, source_id, template, params=None, est_rows=0, est_ms=0):
        """Read through the broker. Every read is templated, quota-bounded, timed,
        redacted, and audited; a violation refuses by name."""
        return self._broker.query(self._credential, source_id, template,
                                  params or {}, est_rows, est_ms)
    # No write, insert, update, delete, execute, or mutate. Deliberately absent: the write
    # path does not exist on the responder's handle.


class ReadOnlyCredential:
    """A resolved read-only credential for one evidence source. It authenticates with a
    secret resolved at the seam (held privately, never surfaced), and it can open ONLY a
    read handle: there is no open_write, execute, or mutate method on this type. Its
    granted role is frozen to read alone, so the credential seam (the plane's write path)
    refuses any write submitted with it. The write path does not exist on this type and is
    not granted to it: physics, not policy."""

    GRANTS = frozenset({GRANT_READ})

    def __init__(self, source_id, resolved_secret):
        self._source_id = source_id
        self._secret = resolved_secret  # never surfaced

    @property
    def source_id(self):
        return self._source_id

    @property
    def grants(self):
        return self.GRANTS

    def open_read(self, plane, broker):
        """The one handle this credential yields: a read handle. There is no open_write."""
        return ReadHandle(self, plane, broker)

    def context_view(self):
        """What the agent may see about this credential: the source and the granted role,
        NEVER the secret (C5/D4)."""
        return {"source_id": self._source_id, "grants": sorted(self.grants),
                "secret": REDACTION_MARKER}

    def __repr__(self):
        return "<ReadOnlyCredential source=%r grants=%s secret=%s>" % (
            self._source_id, sorted(self.grants), REDACTION_MARKER)
    __str__ = __repr__
    # No open_write, execute, mutate, insert, update, or delete.


class WriteCapableCredential:
    """A write-granted credential. The responder NEVER holds one. It exists so the fake
    plane can be seeded and so the credential-seam negative test can prove its refusal is
    NON-VACUOUS: the same write a read-only credential is refused DOES apply with a write
    grant, so it is the read-only grant that blocks the write, not a disabled store. It is
    not part of the responder's harness and is never returned by open_read_only."""

    def __init__(self, source_id, resolved_secret=None):
        self._source_id = source_id
        self._secret = resolved_secret

    @property
    def source_id(self):
        return self._source_id

    @property
    def grants(self):
        return frozenset({GRANT_READ, GRANT_WRITE})


def open_read_only(source_config, env=None):
    """Resolve the read-only credential the responder investigates with, at the seam. The
    secret is a reference (env: or keychain:), resolved here and held privately; a raw
    literal is refused (D4). Returns a ReadOnlyCredential - the only credential the
    responder ever holds. There is deliberately no open_write counterpart."""
    secret = resolve_secret_ref(source_config.get("secret_ref"), env=env)
    return ReadOnlyCredential(source_config.get("id"), secret)


# --- the read broker: templated shapes, quotas, timeout, redaction, audit ----------------

def redact_row(row, fields):
    """Strip the declared sensitive fields from one row BEFORE it enters context. A present
    field is replaced with the redaction marker, not dropped, so the row shape is stable and
    the absence of a leak is visible. PII redaction runs here, before any row reaches the
    caller (O1/C5)."""
    redset = set(fields or [])
    return {k: (REDACTION_MARKER if k in redset else v) for k, v in row.items()}


class QueryAudit:
    """The full audit log of every query the broker processes, allowed or refused. Reads
    can exfiltrate or overload, so the audit is not optional: it is the record O1 requires
    (every query the responder runs lands in a full audit log). It holds the source, the
    template, the parameters, the decision, and the row count - never a raw secret."""

    def __init__(self):
        self.entries = []

    def record(self, source_id, template, params, decision, rows):
        self.entries.append({"source_id": source_id, "template": template,
                             "params": dict(params or {}), "decision": decision,
                             "rows": rows})
        return self.entries[-1]

    def __len__(self):
        return len(self.entries)


class Broker:
    """The read path is a BROKER, not a raw connection: read-only is not harmless. It
    enforces templated query shapes (only a template the source declares), a row-limit
    quota, a rate quota, and a per-query timeout, redacts the source's declared sensitive
    fields before the rows enter context, and audits every query. Any violation refuses by
    name, fail closed. It never writes: it reads through the plane's read path only."""

    def __init__(self, sources, plane, audit=None):
        self._sources = sources          # {source_id: source-config-dict}
        self._plane = plane
        self.audit = audit if audit is not None else QueryAudit()
        self._rate = {}                  # source_id -> queries used in the window

    def _source(self, source_id):
        s = self._sources.get(source_id)
        if s is None:
            raise EvidencePlaneError("unknown evidence source %r (fail closed)" % source_id)
        return s

    def query(self, credential, source_id, template, params=None, est_rows=0, est_ms=0):
        params = params or {}
        s = self._source(source_id)

        # TEMPLATED SHAPE: only a declared template. A free-form or undeclared query is
        # refused - a free-form read is the exfiltration path read-only is not harmless
        # against.
        templates = _as_list(s.get("templates"))
        if template not in templates:
            self.audit.record(source_id, template, params, "refused:free_form", 0)
            raise EvidencePlaneError("query refused: %r is not a declared template shape for %r (free-form queries are not permitted; declared shapes: %s)" % (template, source_id, sorted(templates)))

        # RATE QUOTA: queries beyond the source's rate cap within the window are refused.
        rate_max = s.get("rate_max")
        used = self._rate.get(source_id, 0)
        if isinstance(rate_max, int) and used >= rate_max:
            self.audit.record(source_id, template, params, "refused:rate_quota", 0)
            raise EvidencePlaneError("query refused: rate quota exhausted for %r (%d used, cap %d)" % (source_id, used, rate_max))

        # ROW QUOTA (pre-flight): a query whose declared result size exceeds the row cap is
        # refused before it runs.
        max_rows = s.get("max_rows")
        if isinstance(max_rows, int) and est_rows > max_rows:
            self.audit.record(source_id, template, params, "refused:row_quota", 0)
            raise EvidencePlaneError("query refused: row quota exceeded for %r (%d rows > cap %d)" % (source_id, est_rows, max_rows))

        # TIMEOUT: a query whose estimated duration exceeds the source's timeout is refused.
        timeout_ms = s.get("timeout_ms")
        if isinstance(timeout_ms, int) and est_ms > timeout_ms:
            self.audit.record(source_id, template, params, "refused:timeout", 0)
            raise EvidencePlaneError("query refused: estimated %dms exceeds timeout %dms for %r" % (est_ms, timeout_ms, source_id))

        # The read runs, and only now does it count against the rate window.
        self._rate[source_id] = used + 1
        raw = self._plane.execute_read(credential, source_id, {"template": template, "params": params})

        # ROW QUOTA (overload guard): a read that returns more rows than the cap is refused
        # even if the pre-flight estimate was under it, so a source cannot overload context.
        if isinstance(max_rows, int) and len(raw) > max_rows:
            self.audit.record(source_id, template, params, "refused:row_quota", len(raw))
            raise EvidencePlaneError("query refused: source %r returned %d rows > cap %d (overload guard)" % (source_id, len(raw), max_rows))

        # REDACTION before context: strip the source's declared sensitive fields from every
        # row BEFORE it reaches the caller.
        redacted = [redact_row(r, s.get("redact")) for r in raw]
        self.audit.record(source_id, template, params, "allowed", len(redacted))
        return redacted


# --- the fake plane (offline proof) and the live edge (fail loud) ------------------------

class FakeEvidencePlane:
    """An offline, in-memory reference evidence plane for proving the access physics without
    any live system. It holds seeded rows per source (including seeded PII so redaction can
    be proven), and it models a backing store that CAN be written internally, precisely so
    the credential seam has something real to refuse: a write is authorized by the
    submitting credential's GRANT, and the responder's read-only credential grants no write,
    so submit_write refuses AT THE SEAM. Nothing here connects to a real system; the live
    edge that would is LiveEvidencePlane, and it fails loud."""

    def __init__(self, rows=None):
        self._rows = {sid: [dict(r) for r in rs] for sid, rs in (rows or {}).items()}

    def execute_read(self, credential, source_id, selector):
        """The read path the broker calls. A read is available to any credential that grants
        read (the responder's credential does). Returns a copy of the source's raw rows; the
        broker applies the quota, the timeout, and the redaction."""
        if GRANT_READ not in credential.grants:
            raise EvidencePlaneError("read refused at the credential seam: credential for %r grants %s, not read" % (source_id, sorted(credential.grants)))
        return [dict(r) for r in self._rows.get(source_id, [])]

    def submit_write(self, credential, source_id, write_op):
        """The write path, guarded at the CREDENTIAL SEAM. A write is authorized by the
        credential's granted role, NEVER by inspecting write_op or asking a policy: a
        credential that does not grant write is refused here, fail closed. The responder's
        ReadOnlyCredential grants only read, so a write submitted with it is structurally
        refused at this seam; a write-granted credential (which the responder never holds)
        applies, proving the refusal is the credential, not a disabled store."""
        if GRANT_WRITE not in credential.grants:
            raise EvidenceWriteRefused("write refused at the credential seam: credential for %r grants %s, not write - a read-only credential makes the write impossible (physics, not a policy prompt)" % (source_id, sorted(credential.grants)))
        self._rows.setdefault(source_id, []).append(dict(write_op))
        return True

    def row_count(self, source_id):
        return len(self._rows.get(source_id, []))


class LiveEvidencePlane:
    """The live edge: the reference seam to a REAL declared source. It FAILS LOUD.
    Connecting the evidence plane to a real logs, metrics, or trace store or a read replica
    is a separate, per-system, human-approved enablement act (NG1); this seam never opens a
    live connection inside the gate. Every method raises EvidencePlaneError naming the
    deferral, so a runtime that wants live evidence must INJECT a real read-only adapter,
    exactly as executor.LiveLoop refuses to fabricate a build. A gate that silently
    connected to production would be worse than one that refuses."""

    def __init__(self, source_config=None):
        self._source_config = source_config

    def connect(self, source_id):
        raise EvidencePlaneError("live evidence connection is a separate per-system human-approved enablement act (NG1); no live connection is opened in the gate. Inject a real read-only adapter at enablement.")

    def execute_read(self, credential, source_id, selector):
        raise EvidencePlaneError("live evidence read is a separate per-system human-approved enablement act (NG1); inject a real read-only adapter. Refusing to fabricate a live read.")

    def submit_write(self, credential, source_id, write_op):
        raise EvidenceWriteRefused("the evidence plane has no write path, live or fake: the responder investigates read-only (physics). Execution is a separate organ, WARP-1206 (W6).")


# --- gate entry points (adoption safe, fail closed) --------------------------------------

def check_plane_file(path, root, required, parse, fail):
    """Single-file entry point for an evidence-plane config. Absent file: stand down
    (adoption safe) unless required, then fail closed. Present: parse and validate."""
    p = Path(path)
    if not p.is_file():
        if required:
            return fail(str(p), "evidence-plane config is referenced as required but absent (fail closed)")
        return 0
    try:
        data = load_plane(p, parse)
    except EvidencePlaneError as e:
        return fail(str(p), str(e))
    return validate_plane(data, root, p, fail)


def check_evidence_dir(evidence_dir, root, parse, fail):
    """The gate entry point over the per-repo evidence-plane configs. Adoption safe: with no
    .veldo/evidence/ directory this stands down and returns clean, so a repository that never
    configures the responder is byte-identically unaffected. Present configs each fail closed
    on anything malformed, and a plane id declared by more than one config is refused."""
    d = Path(evidence_dir)
    if not d.is_dir():
        return 0
    errs = 0
    ids = {}
    for p in sorted(d.glob("*.yaml")):
        errs += check_plane_file(p, root, False, parse, fail)
        try:
            data = load_plane(p, parse)
        except EvidencePlaneError:
            continue  # already reported by check_plane_file
        pid = data.get("id")
        if _is_str(pid):
            ids.setdefault(pid, []).append(p.name)
    for pid, files in sorted(ids.items()):
        if len(files) > 1:
            errs += fail(str(d), "duplicate evidence-plane id %r across configs: %s" % (pid, ", ".join(sorted(files))))
    return errs


def _cli(argv):
    """Standalone runner: validate a repository's evidence-plane configs (or a single file)
    reusing validate.py's ONE front-matter parser and failure reporter, so there is no
    second YAML parser. This mirrors how validate.py invokes the sibling contract
    validators; wiring this into validate.py run_all and the init lay-down is WARP-1211
    (W11, land the checks in the canonical engine)."""
    import importlib.util
    here = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location("veldo_validate", here / "validate.py")
    V = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(V)
    root = here.parent
    arg = argv[1] if len(argv) > 1 else None
    if arg and Path(arg).is_file():
        errs = check_plane_file(arg, root, False, V.parse_yamlish, V.fail)
    else:
        errs = check_evidence_dir(default_evidence_dir(root), root, V.parse_yamlish, V.fail)
    if errs:
        print("veldo evidence plane: %d problem(s)" % errs)
        return 1
    print("veldo evidence plane: clean")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_cli(sys.argv))
