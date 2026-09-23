"""Decision-record dependency evaluation for the floor slice (PLAN-0019 W39, VELDO-0054, R40, R71).

WHAT THIS MODULE IS. The one answer to "does a governing decision still block this unit?" for every
enabled consumer: plan._decision_blocks (and through it item_state and the plan burn-down),
plan.cmd_run_check, the frontier's plan candidates, and the shared floor Gate's decisions_settled
predicate at selection, direct execution, build, review and publication. Pure predicates over plain
records the caller read from the real control store, plus one seam to the operating system's OpenSSH
tooling (the settlement signature). Standard library only.

A GOVERNING DECISION is an accepted `decision` record (GOVERNING_SCHEMA) that binds its current
revision, the digest of its framing, its subject (a spec or a plan, by id and digest) and its scope
(operation, target, parameters), and names what it blocks: unit ids and `plan:<id>` references.
Existing inline `open_decisions` entries, in a plan file or in the accepted plan record, are
REFERENCES to these records by `decision_id`, never rulings (R71): whatever status, ruling or
resolution text an entry or a record carries, only an accepted settlement unblocks.

A SETTLEMENT is an accepted `decision_settlement` record associated with one governing record and
carrying a signed body (SETTLEMENT_FIELDS) under SETTLEMENT_NAMESPACE. It resolves the decision only
when the signature verifies against the settlement signers this host trusts, and the signed body is
the CURRENT EXACT BINDING: this domain, this decision and revision, the record's framing digest, the
record's subject (kind, id and digest, the digest also equal to the subject's current accepted
digest), the digest of the record's scope, and an approving ruling. Anything else is a named blocker.

THE NAMED BLOCKERS, in the order they are decided for one record:
  invalid_input:<id>/<field>     a malformed governing or settlement record (a wrong type anywhere,
                                 an unhashable id), or invalid_input:decision_reference for an
                                 inline reference that is not an id; decided before anything else
  missing_decision:<ref>         a reference no accepted record carries
  ambiguous_decision:<ref|id>    a reference two records carry, or two verified current settlements
  unresolved_decision:<id>       no settlement is associated with the record
  unsupported_decision:<id>/...  a record this slice cannot evaluate: another schema, a subject kind
                                 other than spec or plan, or a governing obligation
                                 (tripwire, adversarial decision review, anything) Release 1 does not
                                 evaluate; unsupported blocks, it is never presumed satisfied
  unsigned_decision:<id>         no associated settlement verifies against the trusted signers
  unbound_decision:<id>/<field>  a verified settlement that is not the current exact binding
  decision_ruling:<id>/<ruling>  a current exact binding whose ruling does not approve

WHAT IT IS NOT. It writes nothing and settles nothing: the settlement producer is VELDO-0069, and
signed fixtures only test consumption, they authenticate no live owner. Expiry, reopening, reverse
invalidation, tripwires and adversarial decision review are Release 3; their obligations block here.
"""
import hashlib
import json
from pathlib import Path
import importlib.util

SCHEMA = 'veldo.control_decision_dependency/v1'
GOVERNING_SCHEMA = 'veldo.governing_decision/v1'
SETTLEMENT_SCHEMA = 'veldo.decision_settlement/v1'
# The OpenSSH signature namespace a settlement body is signed under (ssh-keygen -Y sign -n). Distinct
# from the command and enrollment namespaces, so no other signed record verifies as a settlement.
SETTLEMENT_NAMESPACE = 'veldo-decision-settlement'
# The signed body of a settlement. Every field is signed; the association to a governing record
# (`decision` on the settlement record) is not, which is why the body is compared with the record.
SETTLEMENT_FIELDS = ('schema', 'domain_uuid', 'decision_id', 'decision_revision', 'framing_digest', 'subject',
                     'scope_digest', 'ruling', 'request_id', 'request_version', 'principals', 'settled_at')
# The subject kinds this slice binds, with the lifecycle fields their accepted digest leaves out
# (a claim moves a unit's state and a plan's status moves as it runs; neither changes what was ruled).
SUBJECT_KINDS = {'spec': ('state',), 'plan': ('status',)}
# Governing obligations Release 1 evaluates: none. Tripwires and adversarial decision review are
# Release 3 (PLAN-0019 revision 3); a record carrying any obligation blocks by name.
SUPPORTED_OBLIGATIONS = ()
APPROVING_RULING = 'approve'

# EVERY ENABLED CONSUMER of this answer, as (module, qualified function). The suite derives the same
# set from the actual call sites (a call to one of CONSUMER_CALLS).
CONSUMERS = (
    ('plan.py', 'cmd_status'),
    ('plan.py', 'cmd_run_check'),
    ('plan.py', '_decision_blocks'),
    ('frontier.py', '_plan_build_candidates'),
    ('runstatus.py', '_burndown'),
    ('control_eligibility.py', 'Gate._predicate'),
    ('control_eligibility.py', 'Gate.decision_blockers'),
    ('control_eligibility.py', 'Gate._decision_codes'),
)
CONSUMER_CALLS = ('decision_blockers', '_decision_blocks', '_decision_codes', 'blockers')

VERIFY_CACHE_LIMIT = 4096


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


def _digest(value):
    return 'sha256:' + hashlib.sha256(_canonical(value)).hexdigest()


def _is_str(value):
    return isinstance(value, str) and value.strip() != ''


def subject_entity(subject):
    """The store entity id an accepted subject lives at, or None for a kind this slice does not bind."""
    if not isinstance(subject, dict) or subject.get('kind') not in SUBJECT_KINDS or not _is_str(subject.get('id')):
        return None
    return subject['id'] if subject['kind'] == 'spec' else 'plan:' + subject['id']


def subject_digest(kind, data):
    """THE ONE SPELLING of a subject's accepted digest: its accepted record minus lifecycle fields.
    None when the subject has no accepted record."""
    if not isinstance(data, dict):
        return None
    drop = SUBJECT_KINDS.get(kind, ())
    return _digest({k: v for k, v in data.items() if k not in drop})


def scope_digest(scope):
    """The digest of a ruling's scope: its operation, target and complete parameters."""
    scope = scope if isinstance(scope, dict) else {}
    return _digest({'operation': scope.get('operation'), 'target': scope.get('target'),
                    'parameters': scope.get('parameters')})


def settlement_bytes(body):
    """The bytes a settlement signature covers: the sorted JSON of every signed body field."""
    body = body if isinstance(body, dict) else {}
    return _canonical({k: body.get(k) for k in SETTLEMENT_FIELDS})


def references(plan_data, unit):
    """The decision ids an accepted plan record's inline open_decisions entries reference for `unit`."""
    out = []
    entries = plan_data.get('open_decisions') if isinstance(plan_data, dict) else None
    for entry in entries if isinstance(entries, list) else []:
        if isinstance(entry, dict) and isinstance(entry.get('blocks'), list) and unit in entry['blocks']:
            out.append(entry.get('id'))
    return out


def governs(record, unit, plan, refs=()):
    """Whether a governing record bears on `unit`: it blocks the unit or its plan, or a reference names
    it. A `blocks` that is one bare id instead of a list still names that unit, so the record is
    evaluated (and refused as invalid) for the unit it concerns rather than silently dropped."""
    if not isinstance(record, dict):
        return False
    blocks = record.get('blocks') or []
    if isinstance(blocks, str):
        blocks = [blocks]
    if not isinstance(blocks, list):
        blocks = []
    return unit in blocks or (bool(plan) and 'plan:' + str(plan) in blocks) or \
        (record.get('decision_id') is not None and record.get('decision_id') in refs)


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _str_list(value):
    return isinstance(value, list) and all(isinstance(v, str) for v in value)


def record_invalid(rid, record):
    """Why a governing record is malformed (invalid_input:<id>/<field>): a field of the wrong type
    wherever it is present, and for a record claiming GOVERNING_SCHEMA every field it must carry."""
    code = 'invalid_input:%s/' % rid
    if not isinstance(record, dict):
        return [code + 'record']
    problems = []
    for name, ok in (('decision_id', record.get('decision_id') is None or isinstance(record.get('decision_id'), str)),
                     ('blocks', record.get('blocks') is None or _str_list(record.get('blocks'))),
                     ('obligations', record.get('obligations') is None or _str_list(record.get('obligations')))):
        if not ok:
            problems.append(code + name)
    if record.get('schema') != GOVERNING_SCHEMA:
        return problems
    subject, scope = record.get('subject'), record.get('scope')
    for name, ok in (('decision_id', _is_str(record.get('decision_id'))),
                     ('revision', _is_int(record.get('revision'))),
                     ('framing_digest', _is_str(record.get('framing_digest'))),
                     ('subject', isinstance(subject, dict) and all(_is_str(subject.get(k)) for k in ('kind', 'id', 'digest'))),
                     ('scope', isinstance(scope, dict) and _is_str(scope.get('operation')) and _is_str(scope.get('target'))
                      and isinstance(scope.get('parameters'), dict))):
        if not ok and code + name not in problems:
            problems.append(code + name)
    return problems


SETTLEMENT_TYPES = {'schema': str, 'domain_uuid': str, 'decision_id': str, 'decision_revision': int,
                    'subject': dict, 'scope_digest': str, 'ruling': str, 'request_id': str,
                    'request_version': int, 'principals': list, 'settled_at': str}


def settlement_invalid(sid, data):
    """Why an associated settlement record is malformed (invalid_input:<id>/<field>): a body that is
    not a mapping, a signature or signer that is present but not text, or a signed field of the wrong
    type. An ABSENT signature is not malformed, it is unsigned; an absent framing digest is a receipt
    without its framing, refused by the binding (never accepted, never invalid)."""
    code = 'invalid_input:%s/' % sid
    body = data.get('settlement')
    problems = []
    if not isinstance(body, dict):
        problems.append(code + 'settlement')
    for name in ('signature', 'signer'):
        if data.get(name) is not None and not isinstance(data.get(name), str):
            problems.append(code + name)
    if isinstance(body, dict):
        for name, kind in SETTLEMENT_TYPES.items():
            value = body.get(name)
            if value is not None and not (isinstance(value, kind) and not isinstance(value, bool)):
                problems.append(code + name)
        if body.get('framing_digest') is not None and not isinstance(body.get('framing_digest'), str):
            problems.append(code + 'framing_digest')
    return problems


def record_problems(rid, record):
    """Why a well-formed governing record is one this slice cannot evaluate
    (unsupported_decision:<id>/<what>): another schema, a subject kind other than spec or plan, or a
    governing obligation Release 1 does not evaluate."""
    code = 'unsupported_decision:%s/' % rid
    if record.get('schema') != GOVERNING_SCHEMA:
        return [code + 'schema']
    kind = record['subject']['kind']
    if kind not in SUBJECT_KINDS:
        return [code + 'subject_kind:%s' % kind]
    return [code + 'obligation:%s' % o for o in record.get('obligations') or [] if o not in SUPPORTED_OBLIGATIONS]


def scope_binding_problems(rid, record, body):
    """Whether the signed ruling is for exactly this record's subject and scope: the subject kind, id
    and digest it names, the digest of the operation, target and parameters, and a target that is the
    subject itself. A ruling on one subject never authorizes another, nor another operation."""
    problems = []
    if body.get('subject') != record.get('subject'):
        problems.append('unbound_decision:%s/subject' % rid)
    if body.get('scope_digest') != scope_digest(record.get('scope')) \
            or (record.get('scope') or {}).get('target') != (record.get('subject') or {}).get('id'):
        problems.append('unbound_decision:%s/scope' % rid)
    return problems


def binding_problems(rid, record, body, current, domain_uuid):
    """Why a VERIFIED settlement body is not the current exact binding of `record`."""
    problems = []
    if body.get('schema') != SETTLEMENT_SCHEMA:
        problems.append('unbound_decision:%s/schema' % rid)
    if body.get('domain_uuid') != domain_uuid:
        problems.append('unbound_decision:%s/domain' % rid)
    if body.get('decision_id') != record.get('decision_id'):
        problems.append('unbound_decision:%s/decision' % rid)
    framing = body.get('framing_digest')
    if not _is_str(framing) or framing != record.get('framing_digest'):
        problems.append('unbound_decision:%s/framing' % rid)
    subject = record.get('subject') or {}
    if current is None or subject.get('digest') != current:
        problems.append('unbound_decision:%s/subject_digest' % rid)
    problems.extend(scope_binding_problems(rid, record, body))
    if not problems and body.get('ruling') != APPROVING_RULING:
        problems.append('decision_ruling:%s/%s' % (rid, body.get('ruling')))
    return problems


def _record_blockers(rid, record, settlements, subjects, verify, domain_uuid):
    invalid = record_invalid(rid, record)
    if invalid:
        return invalid
    mine = [(sid, s) for sid, s in settlements if isinstance(s, dict) and s.get('decision') == rid]
    if not mine:
        return ['unresolved_decision:' + rid]
    problems = record_problems(rid, record)
    if problems:
        return problems
    malformed = [code for sid, s in mine for code in settlement_invalid(sid, s)]
    if malformed:
        return malformed
    verified = []
    for _, s in mine:
        body, signature, signer = s.get('settlement'), s.get('signature'), s.get('signer')
        if verify is None or not isinstance(body, dict) or not _is_str(signature) or not _is_str(signer):
            continue
        if verify(settlement_bytes(body), signature, signer):
            verified.append(body)
    if not verified:
        return ['unsigned_decision:' + rid]
    current = [b for b in verified if b.get('decision_revision') == record['revision']]
    if not current:
        return ['unbound_decision:%s/revision' % rid]
    if len(current) > 1:
        return ['ambiguous_decision:' + rid]
    eid = subject_entity(record['subject'])
    return binding_problems(rid, record, current[0], (subjects or {}).get(eid), domain_uuid)


def blockers(unit, refs, records, settlements, subjects, verify, domain_uuid):
    """THE ANSWER: every named blocker the governing decisions of `unit` raise, [] when none blocks.

    `refs` are the decision ids inline entries reference for the unit; `records` the governing
    [(entity id, data)] the caller read (every record that governs the unit or carries a referenced
    id); `settlements` the [(entity id, data)] of every settlement associated with one of them;
    `subjects` {entity id: current accepted digest}; `verify(message, signature, principal) -> bool`
    the trusted settlement verifier, or None when this host trusts no settlement signer (every
    settlement is then unsigned). Only an exact current binding clears a record; nothing a record says
    of itself does. Malformed input of any shape is a named invalid_input for this unit, never a raise."""
    codes = []
    by_ref = {}
    for rid, data in records:
        if isinstance(data, dict) and isinstance(data.get('decision_id'), str):
            by_ref.setdefault(data['decision_id'], []).append(rid)
    wanted = []
    for ref in refs or ():
        if not isinstance(ref, str):
            codes.append('invalid_input:decision_reference')
        elif ref not in wanted:
            wanted.append(ref)
    for ref in wanted:
        found = by_ref.get(ref, [])
        if not found:
            codes.append('missing_decision:%s' % ref)
        elif len(found) > 1:
            codes.append('ambiguous_decision:%s' % ref)
    ambiguous = {rid for ref in wanted for rid in by_ref.get(ref, []) if len(by_ref[ref]) > 1}
    for rid, data in records:
        if rid in ambiguous:
            continue
        codes.extend(_record_blockers(rid, data, settlements, subjects, verify, domain_uuid))
    return list(dict.fromkeys(codes))


class Unavailable(Exception):
    """The settlement verifier could not be asked (no ssh-keygen, or it timed out): an unavailable
    service, never an unsigned settlement and never a verified one."""


def _ssh_verify():
    spec = importlib.util.spec_from_file_location('decision_authority_contract',
                                                  Path(__file__).with_name('authority_contract.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.ssh_keygen_verify


class SettlementTrust:
    """The settlement signers a host trusts: OpenSSH allowed-signers text whose principals may sign a
    settlement body under SETTLEMENT_NAMESPACE. verify() is ssh-keygen -Y verify over exactly those
    signers; its answer for identical bytes, signature and principal is remembered (bounded). A
    verifier that cannot run raises Unavailable and nothing is remembered."""

    def __init__(self, allowed_signers_text, verifier=None):
        if not isinstance(allowed_signers_text, str) or not allowed_signers_text.strip():
            raise ValueError('settlement signers are empty')
        self.signers = allowed_signers_text
        self._verify = verifier or _ssh_verify()
        self._seen = {}

    def verify(self, message, signature, principal):
        if not _is_str(principal) or not _is_str(signature):
            return False
        key = (bytes(message), signature, principal)
        if key not in self._seen:
            if len(self._seen) >= VERIFY_CACHE_LIMIT:
                self._seen.clear()
            verified, detail = self._verify(bytes(message), signature, self.signers, principal, SETTLEMENT_NAMESPACE)
            if not verified and str(detail).startswith('ssh-keygen unavailable'):
                raise Unavailable(detail)
            self._seen[key] = bool(verified)
        return self._seen[key]
