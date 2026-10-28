"""Repository records, the adoption proposal, the settled decision and the adoption signer (VELDO-0161).

WHAT THIS MODULE IS. The one reader and writer of a repository's record in the control store, and the one
judge of whether a settled owner decision names a repository for adoption. Three callers share it: the
adoption effect (control_effect_executor_adoption), which provisions and enrolls the repository; the
adoption signer below, which signs the repository's VELDO-0029 binding; and the running authority service
(control_service.Service.take_on), which takes the repository on without a restart.

THE RECORD. Entity `repository:<uuid>` of kind `repository` (design section 5): the repository uuid and
name, its one Git identity, its path, its remote (url, owner, default branch), its origin (`adopted`, or
`created` by the provisioner's creation steps, VELDO-0143, whose record also names the step it failed at), the
digest of its VELDO-0029 binding, the settled decision it was adopted on, the scaffold commit when one was
laid, and its state: `provisioning`, `active` or `failed` with a named reason. Every write appends one
entry to `history` and never changes an earlier one. provisioning -> active and provisioning -> failed are
the only transitions; a record is never written again once it is active or failed (the owner removes it
by hand, as the rollback says). A step within provisioning (the binding signed) is a provisioning write.

THE SETTLED DECISION (settled, below). An inbox request (VELDO-0064) whose VELDO-0068 settlement terms
name ADOPTION_TOUCHPOINT and a target of kind ADOPTION_TARGET for the record id and the digest of the
proposal, SATISFIED by the settlement of its current version, whose ruling is approve and whose typed
effect approves exactly these terms and this proposal, whose brief (what the owner was shown) is exactly
adoption_brief(proposal), and whose only principal is the owner the proposal names, an active person
holding project_owner. Anything else refuses `no_settled_decision:<why>` by name, read only. A decision id
of control_project_proposal (`new-project:<intake proposal>`, VELDO-0143) is judged by that module's one
judge instead (repository_decision): the owner's one answer to the factory PM's new-project proposal, or his
own message when it named the project and the identity, naming the one repository it creates or adopts.

THE ADOPTION SIGNER (AdoptionSigner). A service key setup generates in the protected key directory and
enrolls among this host's enrollment signers (control_factory_setup.adoption_signer, host_files), under
principal SIGNER_PRINCIPAL. Its only use is signing a VELDO-0029 binding for a repository a settled owner
decision names: before it signs it judges the bytes it is asked to sign itself (a binding, enrolled by it,
for this domain, store, host and authority generation, the generation not below the store's own, naming
exactly the repository the settled decision names, whose root commits are the repository's at the
proposal's path) against that decision (scope), refuses a decision it has already signed for, and journals
the signature (an `adoption_signature` entity naming the decision, the
repository and the binding digest) before it hands the signature back. A refusal is
`signature_refused:<why>` and signs and journals nothing. No ssh-keygen this module runs ever reaches an SSH
agent (_quiet_env): the signer's key is the file named, never a key an agent offers.

Observations name repositories, identities, decisions, commits and digests, never a token, a key or a
signature. Standard library only; every organ is loaded as a sibling by path.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import time


def organ(name):
    spec = importlib.util.spec_from_file_location('repository_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CE = organ('control_enrollment')
GI = organ('control_git_identity')
AC = organ('authority_contract')

SCHEMA = 'veldo.repository/v1'
KIND = 'repository'
ID_PREFIX = 'repository:'
SIGNATURE_KIND = 'adoption_signature'
SIGNATURE_PREFIX = 'adoption-signature:'
# The commands that write them, registered on the writing connection only (never a generic store command).
OPERATION = 'repository_record'
SIGN_OPERATION = 'adoption_signature'
WRITES = ('entities', 'journal', 'commands', 'nonces')
STATES = ('provisioning', 'active', 'failed')
# provisioning -> provisioning records a step (the binding's digest once it is signed).
TRANSITIONS = {None: ('provisioning',), 'provisioning': ('provisioning', 'active', 'failed')}
ORIGIN = 'adopted'
ORIGINS = ('adopted', 'created')
# VELDO-0143: the settled decisions control_project_proposal judges (a new project from chat).
NEW_PROJECT_PREFIX = 'new-project:'
# The adoption request a settled answer answers (VELDO-0068 terms).
ADOPTION_TOUCHPOINT = 'decision_disposition'
ADOPTION_TARGET = 'repository_adoption'
REQUEST_KIND, TERMS_KIND, SETTLEMENT_KIND, EFFECT_KIND = 'assignment', 'settlement_terms', 'request_settlement', 'settlement_effect'
SETTLED_STATE, APPROVED_EFFECT = 'SATISFIED', 'decision_approved'
OWNER_ROLE = 'project_owner'
# The adoption signer's principal: the name its line in the host's enrollment signers carries and every
# binding it signs is enrolled by.
SIGNER_PRINCIPAL = 'adoption-signer'
# The namespace every VELDO-0029 binding signature is made under (control_eligibility.ENROLLMENT_NAMESPACE).
CE_NAMESPACE = 'veldo-enrollment'
# The take-on request the adoption effect hands the running authority service (control_service.Service.
# take_on_request): its packet operation, and the namespace its journal-key signature is made under, which
# nothing else signs in.
TAKE_ON_OPERATION = 'take_on'
TAKE_ON_NAMESPACE = 'veldo-adoption-take-on'
# What a proposal binds, in the order a missing one is named.
PROPOSAL_FIELDS = ('repository', 'name', 'owner', 'identity', 'path', 'remote', 'default_branch', 'base_commit',
                   'scaffold_commit')
# The error taxonomy (the spec's observability contract): each refusal's class.
# push_unconfirmed: the push was accepted but the remote's branch could not be read back as the commit.
# VELDO-0143 adds the creation steps' own: a directory that exists and is not empty, a remote that already
# exists, an identity token that is not available and a creation the host refused.
REASONS = ('remote_owner_mismatch', 'push_refused', 'push_unconfirmed', 'no_settled_decision', 'signature_refused',
           'not_taken_on', 'directory_not_empty', 'remote_exists', 'token_unavailable', 'creation_refused')
TAXONOMY = {'binding_mismatch:remote_owner': 'remote_owner_mismatch', 'push_refused': 'push_refused',
            'push_unconfirmed': 'push_unconfirmed', 'no_settled_decision': 'no_settled_decision',
            'signature_refused': 'signature_refused', 'not_taken_on': 'not_taken_on',
            'directory_not_empty': 'directory_not_empty', 'remote_exists': 'remote_exists',
            'token_unavailable': 'token_unavailable', 'creation_refused': 'creation_refused'}
_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$')
# A repository id is one Git ref component (refs/veldo/adoption/<id>): no slash, no '..', no '.lock' end.
_REPOSITORY = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$')
_COMMIT = re.compile(r'^[0-9a-f]{40}([0-9a-f]{24})?$')


class Refused(Exception):
    def __init__(self, code, detail=''):
        super().__init__('%s: %s' % (code, detail) if detail else code)
        self.code, self.detail = code, detail


def reason(code):
    """The error class of a refusal code: one of REASONS, or the code's own first part."""
    code = str(code or '')
    for prefix, name in TAXONOMY.items():
        if code == prefix or code.startswith(prefix + ':'):
            return name
    return code.split(':', 1)[0] or None


def record_id(repository):
    return ID_PREFIX + str(repository)


def _is_str(value):
    return isinstance(value, str) and value.strip() != ''


def _quiet_env():
    """The environment every ssh-keygen call runs in: never through an agent."""
    return {k: v for k, v in os.environ.items() if k not in ('SSH_AUTH_SOCK', 'SSH_AGENT_PID')}


def repository_id_problems(repository):
    """Why `repository` is not a repository id that names one ref component (empty when it is)."""
    if (not isinstance(repository, str) or not _REPOSITORY.match(repository) or '..' in repository
            or repository.endswith(('.lock', '.'))):
        return ['invalid_input:proposal:repository']
    return []


def digest(value):
    return 'sha256:' + hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                                 ensure_ascii=True).encode()).hexdigest()


# ---------------------------------------------------------------------------------------------
# The proposal the owner answers
# ---------------------------------------------------------------------------------------------

def adoption_proposal(**fields):
    """The proposal an adoption request carries: every PROPOSAL_FIELDS value, the scaffold commit None when
    the repository already carries the scaffold."""
    missing = [f for f in PROPOSAL_FIELDS if f not in fields]
    if missing or set(fields) - set(PROPOSAL_FIELDS):
        raise Refused('invalid_input:proposal', ', '.join(missing) or 'unknown field')
    return {f: fields[f] for f in PROPOSAL_FIELDS}


def proposal_problems(proposal):
    if not isinstance(proposal, dict) or set(proposal) != set(PROPOSAL_FIELDS):
        return ['invalid_input:proposal:fields']
    problems = []
    for field in ('repository', 'owner', 'identity', 'path', 'remote', 'default_branch'):
        if not _is_str(proposal[field]):
            problems.append('invalid_input:proposal:' + field)
    if _is_str(proposal['repository']):
        problems.extend(repository_id_problems(proposal['repository']))
    if not _is_str(proposal['name']) or not _NAME.match(proposal['name']):
        problems.append('invalid_input:proposal:name')
    if not isinstance(proposal['path'], str) or not os.path.isabs(proposal['path']):
        problems.append('invalid_input:proposal:path')
    if not isinstance(proposal['base_commit'], str) or not _COMMIT.match(proposal['base_commit']):
        problems.append('invalid_input:proposal:base_commit')
    if proposal['scaffold_commit'] is not None and (not isinstance(proposal['scaffold_commit'], str)
                                                    or not _COMMIT.match(proposal['scaffold_commit'])):
        problems.append('invalid_input:proposal:scaffold_commit')
    return problems


def adoption_brief(proposal):
    """Exactly what the owner is shown when asked to adopt `proposal`, in plain text: every value adoption
    binds, the scaffold commit by its id when one was laid, so an approval approves exactly what is adopted
    and exactly the commit that is pushed."""
    p = proposal if isinstance(proposal, dict) else {}

    def shown(field):
        return str(p[field]) if field in p and p[field] is not None else '(not given)'
    scaffold = ('laid as commit %s on %s, pushed on your answer' % (p['scaffold_commit'], shown('default_branch'))
                if p.get('scaffold_commit') else 'already present, nothing is committed')
    return ('Adopt repository %s.\nIdentity: %s\nPath: %s\nRemote: %s (branch %s, at %s)\nScaffold: %s\n'
            'Owner: %s\nRepository id: %s\nApproving adopts exactly this repository under this identity.'
            % (shown('name'), shown('identity'), shown('path'), shown('remote'), shown('default_branch'),
               shown('base_commit'), scaffold, shown('owner'), shown('repository')))


def adoption_target(proposal):
    """The settlement terms target of an adoption request for `proposal`: the record and the digest of the
    proposal, so a settled answer names exactly what it adopts."""
    repository = proposal.get('repository') if isinstance(proposal, dict) else None
    return {'kind': ADOPTION_TARGET, 'ref': record_id(repository), 'digest': digest(proposal)}


# ---------------------------------------------------------------------------------------------
# The settled decision
# ---------------------------------------------------------------------------------------------

def _row(conn, eid):
    if not _is_str(eid):
        return None
    row = conn.execute('SELECT kind, version, data FROM entities WHERE id=?', (eid,)).fetchone()
    return None if row is None else {'kind': row[0], 'version': row[1], 'data': json.loads(row[2])}


def settled(store, membership, conn, request, now=None):
    """The settled owner decision `request` is, naming one repository for adoption, or Refused
    no_settled_decision:<why>. Reads only. Returns {proposal, request, request_version, settlement_id,
    effect_id, presentation_id, versions}."""
    if isinstance(request, str) and request.startswith(NEW_PROJECT_PREFIX):
        PP = organ('control_project_proposal')
        try:
            return PP.repository_decision(store, membership, conn, request, now)
        except PP.Refused as error:
            raise Refused(error.code, error.detail) from None
    found = _row(conn, request)
    data = found['data'] if found is not None and found['kind'] == REQUEST_KIND else None
    if not isinstance(data, dict) or type(data.get('request_version')) is not int:
        raise Refused('no_settled_decision:no_request', str(request))
    subject = data.get('subject') if isinstance(data.get('subject'), dict) else {}
    terms_row = _row(conn, subject.get('ref'))
    terms = terms_row['data'] if terms_row is not None and terms_row['kind'] == TERMS_KIND else None
    if not isinstance(terms, dict) or digest(terms) != subject.get('digest'):
        raise Refused('no_settled_decision:no_terms', 'the request names no recorded settlement terms')
    target = terms.get('target') if isinstance(terms.get('target'), dict) else {}
    if terms.get('touchpoint') != ADOPTION_TOUCHPOINT or target.get('kind') != ADOPTION_TARGET:
        raise Refused('no_settled_decision:not_an_adoption', 'the request does not ask to adopt a repository')
    proposal = terms.get('proposal')
    if proposal_problems(proposal) or target != adoption_target(proposal):
        raise Refused('no_settled_decision:proposal', 'the target is not the proposal it names')
    version = data['request_version']
    reference = data.get('settlement') if isinstance(data.get('settlement'), dict) else {}
    settlement = _row(conn, reference.get('settlement_id'))
    effect = _row(conn, reference.get('effect_id'))
    if not (data.get('state') == SETTLED_STATE and reference.get('request_version') == version
            and settlement is not None and settlement['kind'] == SETTLEMENT_KIND):
        raise Refused('no_settled_decision:not_settled', 'the request version is not settled')
    s, e = settlement['data'] or {}, (effect or {}).get('data') or {}
    if s.get('ruling') != 'approve':
        raise Refused('no_settled_decision:not_approved:%s' % s.get('ruling'), 'the owner did not approve it')
    if (s.get('request_id') != request or s.get('request_version') != version
            or s.get('terms_id') != terms.get('terms_id') or s.get('terms_digest') != digest(terms)
            or effect is None or effect['kind'] != EFFECT_KIND or e.get('settlement_id') != s.get('settlement_id')
            or e.get('type') != APPROVED_EFFECT or e.get('target') != target or e.get('proposal') != proposal):
        raise Refused('no_settled_decision:settlement', 'the settlement is not the approval of these terms')
    if data.get('brief') != adoption_brief(proposal):
        raise Refused('no_settled_decision:brief', 'the owner was shown something other than this proposal')
    if s.get('principals') != [proposal['owner']]:
        raise Refused('no_settled_decision:not_owner', 'the settled answer is not the owner\'s the proposal names')
    state = membership.authority_state(store, conn)
    entry = AC.membership_entry(state['membership'], proposal['owner'])
    active, _why = AC.active_member(entry, time.time() if now is None else now)
    if not active or entry.get('principal_type') != 'person' or OWNER_ROLE not in (entry.get('roles') or []):
        raise Refused('no_settled_decision:not_owner', 'the owner is not a current person holding project_owner')
    return {'proposal': proposal, 'request': request, 'request_version': version,
            'settlement_id': s.get('settlement_id'), 'effect_id': reference.get('effect_id'),
            'presentation_id': s.get('presentation_id'), 'terms_id': subject.get('ref'),
            'versions': {request: found['version'], subject.get('ref'): terms_row['version'],
                         reference.get('settlement_id'): settlement['version'],
                         reference.get('effect_id'): effect['version']}}


# ---------------------------------------------------------------------------------------------
# The record
# ---------------------------------------------------------------------------------------------

def read(conn, repository):
    found = _row(conn, record_id(repository))
    if found is None or found['kind'] != KIND:
        return None
    return dict(found['data'], version=found['version'])


def records(conn, domain=None):
    """Every repository record (of `domain`, when named), oldest id first."""
    out = []
    for eid, version, data in conn.execute("SELECT id, version, data FROM entities WHERE kind=? ORDER BY id", (KIND,)):
        record = dict(json.loads(data), version=version)
        if domain is None or record.get('domain_uuid') == domain:
            out.append(record)
    return out


def signatures(conn):
    return [dict(json.loads(data), id=eid) for eid, data in conn.execute(
        "SELECT id, data FROM entities WHERE kind=? ORDER BY id", (SIGNATURE_KIND,))]


def _journal_command(conn, store, journal, operation, transition, params, expected, nonce, generation=1):
    conn.command_registry[operation] = {'transition': transition, 'writes': WRITES}
    principal, sign = journal
    command = {'command_id': '%s:%s' % (operation, nonce), 'principal': principal, 'operation': operation,
               'parameters': params, 'expected_versions': expected, 'artifact_digests': [], 'nonce': nonce}
    return store.execute(conn, command, principal, sign, generation)


def write(store, conn, journal, repository, state, *, step, at=None, generation=1, origin=None, **fields):
    """Write the record of `repository` into `state` (TRANSITIONS), appending one history entry naming the
    step; `fields` set the record's other values. Its origin is set when it is first written (`adopted`
    unless named) and never changed. Refused invalid_transition by name, writing nothing."""
    if state not in STATES:
        raise Refused('invalid_input:state', state)
    prior = read(conn, repository)
    current = None if prior is None else prior.get('state')
    if state not in TRANSITIONS.get(current, ()):
        raise Refused('invalid_transition:%s->%s' % (current, state), repository)
    at = time.time() if at is None else at
    record = {k: v for k, v in (prior or {}).items() if k != 'version'}
    record.update(fields)
    kept = (prior or {}).get('origin')
    if origin not in (None, kept) and (kept is not None or origin not in ORIGINS):
        raise Refused('invalid_input:origin', repository)
    record.update(schema=SCHEMA, repository=repository, state=state, origin=kept or origin or ORIGIN, updated_at=at)
    entry = {'step': step, 'state': state, 'at': at}
    if fields.get('reason'):
        entry['reason'] = fields['reason']
    record['history'] = list(record.get('history') or []) + [entry]
    eid = record_id(repository)

    def transition(params, before):
        return {eid: {'kind': KIND, 'data': params['record']}}
    nonce = '%s:%d:%s' % (repository, len(record['history']), state)
    return _journal_command(conn, store, journal, OPERATION, transition, {'record': record},
                            {eid: 0 if prior is None else prior['version']}, nonce, generation)


def metrics(conn, observations=()):
    """Repositories adopted and refused by reason, adoption signatures issued, repositories taken on by the
    running service; from the store's records and the given observations."""
    every = records(conn)
    refused = {}
    for event in observations:
        if event.get('outcome') == 'refused' and event.get('operation') in ('adopt', 'take_on'):
            code = reason(event.get('refusal'))
            refused[code] = refused.get(code, 0) + 1
    return {'adopted': sum(1 for r in every if r.get('state') == 'active' and r.get('origin') == ORIGIN),
            'created': sum(1 for r in every if r.get('state') == 'active' and r.get('origin') == 'created'),
            'provisioning': sum(1 for r in every if r.get('state') == 'provisioning'),
            'failed': sum(1 for r in every if r.get('state') == 'failed'),
            'failed_by_reason': {k: sum(1 for r in every if r.get('state') == 'failed' and reason(r.get('reason')) == k)
                                 for k in sorted({reason(r.get('reason')) for r in every if r.get('state') == 'failed'})},
            'refused_by_reason': refused,
            'signatures': len(signatures(conn)),
            'taken_on': sum(1 for r in every if isinstance(r.get('taken_on'), dict))}


# ---------------------------------------------------------------------------------------------
# The adoption signer
# ---------------------------------------------------------------------------------------------

def public_key(key):
    """The OpenSSH public key of the private key file `key`, derived from it."""
    done = subprocess.run(['ssh-keygen', '-y', '-f', str(key)], capture_output=True, text=True, timeout=30,
                          stdin=subprocess.DEVNULL, env=_quiet_env())
    if done.returncode:
        raise Refused('signature_refused:key', 'the adoption signer key does not load')
    return ' '.join(done.stdout.split()[:2])


def enrolled(signers_text, key):
    """Whether `signers_text` (an OpenSSH allowed-signers file) names the adoption signer's key under its
    principal for enrollment: the line setup writes for it (control_factory_setup.host_files). A key that is
    missing or does not load is not enrolled."""
    try:
        want = public_key(key)
    except Refused:
        return False
    for line in (signers_text or '').splitlines():
        parts = line.split()
        if (len(parts) >= 4 and parts[0] == SIGNER_PRINCIPAL and parts[1] == 'namespaces="%s"' % CE_NAMESPACE
                and ' '.join(parts[2:4]) == want):
            return True
    return False


def store_generation(conn):
    """The highest authority generation the store's journal records (1 for an empty journal)."""
    return conn.execute('SELECT COALESCE(MAX(authority_generation), 1) FROM journal').fetchone()[0]


class AdoptionSigner:
    """Signs one VELDO-0029 binding per settled adoption decision, and nothing else (see the module
    docstring). `ids` are the coordinates it signs for: the store's (domain_uuid, store_uuid, store_path) and
    this host's identity and authority generation (host_identity, authority_generation); `journal` is
    (principal, sign) for the journal record of each signature."""

    def __init__(self, key, store, membership, conn, ids, journal, clock=time.time):
        self.key, self.store, self.membership, self.conn = str(key), store, membership, conn
        self.ids, self.journal, self.clock = dict(ids), journal, clock
        self.asked, self.observations = [], []

    def scope(self, fields, request):
        """Every reason this signer may not sign `fields` (the binding it was asked to sign) for `request`."""
        try:
            decision = settled(self.store, self.membership, self.conn, request)
        except Refused as error:
            return ['signature_refused:' + error.code], None
        proposal = decision['proposal']
        problems = []
        if not isinstance(fields, dict) or fields.get('schema') != CE.BINDING_SCHEMA:
            return ['signature_refused:scope:not_a_binding'], decision
        if fields.get('enrolled_by') != SIGNER_PRINCIPAL:
            problems.append('signature_refused:scope:principal')
        if fields.get('repository_uuid') != proposal['repository']:
            problems.append('signature_refused:scope:repository')
        if (fields.get('domain_uuid') != self.ids['domain_uuid'] or fields.get('store_uuid') != self.ids['store_uuid']
                or fields.get('store_path') != os.path.realpath(self.ids['store_path'])):
            problems.append('signature_refused:scope:store')
        if fields.get('host_identity') != self.ids.get('host_identity'):
            problems.append('signature_refused:scope:host')
        generation = fields.get('authority_generation')
        if (type(generation) is not int or generation != self.ids.get('authority_generation')
                or generation < store_generation(self.conn)):
            problems.append('signature_refused:scope:generation')
        try:
            roots = CE.root_commits(proposal['path'])
        except CE.EnrollmentRefused:
            roots = None
        if roots is None or sorted(fields.get('repository_root_commit') or []) != roots:
            problems.append('signature_refused:scope:repository_identity')
        return problems, decision

    def signer(self, request):
        """sign(bytes) for control_enrollment.enroll, signing for the settled decision `request` only."""
        def sign(message):
            return self.sign(message, request)
        return sign

    def sign(self, message, request):
        self.asked.append(request)
        event = {'operation': 'adoption_signature', 'request': request, 'at': self.clock()}
        try:
            try:
                fields = json.loads(message)
            except (TypeError, ValueError):
                fields = None
            problems, decision = self.scope(fields, request)
            if problems:
                raise Refused(problems[0], '; '.join(problems))
            event.update(repository=decision['proposal']['repository'], settlement=decision['settlement_id'])
            eid = SIGNATURE_PREFIX + str(decision['settlement_id'])
            if _row(self.conn, eid) is not None:
                raise Refused('signature_refused:already_signed', 'this decision has its binding signature')
            done = subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', self.key, '-n', CE_NAMESPACE], input=message,
                                  capture_output=True, timeout=30, stdin=None, env=_quiet_env())
            if done.returncode:
                raise Refused('signature_refused:key', 'the adoption signer key did not sign')
            binding_digest = 'sha256:' + hashlib.sha256(message).hexdigest()
            record = {'repository': decision['proposal']['repository'], 'request': request,
                      'settlement': decision['settlement_id'], 'binding_digest': binding_digest,
                      'signer': SIGNER_PRINCIPAL, 'domain_uuid': self.ids['domain_uuid'], 'at': event['at']}

            def transition(params, before):
                return {eid: {'kind': SIGNATURE_KIND, 'data': params['signature']}}
            # Journaled before the signature leaves the signer: a signature with no journal record is never
            # handed back.
            _journal_command(self.conn, self.store, self.journal, SIGN_OPERATION, transition, {'signature': record},
                             {eid: 0}, 'adoption-signature:' + str(decision['settlement_id']))
        except Refused as error:
            self.observations.append(dict(event, outcome='refused', refusal=error.code))
            raise
        self.observations.append(dict(event, outcome='signed', binding_digest=binding_digest))
        return done.stdout.decode()
