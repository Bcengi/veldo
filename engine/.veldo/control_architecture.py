"""The architecture acceptance record and its one writer (VELDO-0134, PLAN-0019 W97, R38, R50).

WHAT THIS MODULE IS. The format of the store record architecture:<repository_uuid>, the schema
veldo.architecture_record/v1 (record_problems, which VELDO-0053's Gate reads through), and the one
command that writes it: a signed accept command applied through ArchitectureAuthority.apply on the
configured real store connection, admitted exactly as the inbox's signed commands are (VELDO-0064).
The canonical command bytes are verified against the signer's active key in the store's committed
keyring; the stored membership must show an active person member holding project_owner whose scope
covers the repository; and one registered store transaction (control_store.ARCHITECTURE_OPERATION,
the only operation the store lets write this record) commits the record together with the versions
of every authority input it read (the principal, the key, the membership versions entity and the
record itself) and consumes the nonce.

THE BYTES. The contract is read from the object store of the repository bound to the command's
repository uuid in the store (control_store.bind_repositories), at the commit the command names,
through _git_process, which strips every inherited GIT_ variable by prefix and ignores system and
global configuration. Nothing is read from a workspace or from the process environment. The digest
is SHA-256 over the raw blob, with no decoding and no line-ending, byte-order-mark or final-newline
normalization, and the command's stated digest must equal it. The installed structural validator
beside this module (validate.py's public entry_contract, the one loader contract_loader implements)
judges those bytes, laid into a private temporary root, never a workspace copy; a refused kind is
refused by name (CONTRACT_REFUSALS).

REPLACEMENT. An accept command names the contract_version it replaces, 0 when none was accepted. A
replacement writes contract_version plus one and moves the previous version's entry, byte for byte,
to the end of superseded; nothing edits an accepted version in place. The transition re-reads the
record inside the store's write transaction, so the version the command replaces is the one current
at commit.

THE FRONT DOOR. build_command and sign_command are the owner's side: `veldo architecture accept`
reads the blob at the commit, computes its digest, builds the command and signs it with the owner's
personal key through `ssh-keygen -Y sign`, printing the signed packet for the authority.

WHAT IT IS NOT. No withdrawal of an accepted contract, no recovery of a lost acknowledgement, no
concurrent acceptance beyond the store's expected-version refusal and no clock qualification
(Release 2). It holds no key: journal records are signed by the caller's signer. Observations
record identities, versions, digests and outcomes, never the contract bytes, a signature or key
material. Standard library only.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid


def _organ(name):
    spec = importlib.util.spec_from_file_location('architecture_' + name, Path(__file__).resolve().with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_git_process = _organ('git_process')

SCHEMA = 'veldo.architecture_record/v1'
ENTITY_KIND = 'architecture_contract'
ENTITY_PREFIX = 'architecture:'
# The store operation that alone writes the record; control_store.ARCHITECTURE_OPERATION must be it.
OPERATION = 'accept_architecture'
COMMAND_OPERATION = 'accept'
CONTRACT_PATH = '.veldo/architecture.yaml'
STATE = 'accepted'
RECORD_FIELDS = ('schema', 'repository_uuid', 'state', 'contract_version', 'digest', 'source', 'accepted_by',
                 'command_id', 'superseded')
SOURCE_FIELDS = ('commit', 'path')
ENTRY_FIELDS = ('contract_version', 'digest', 'source', 'accepted_by', 'command_id')
COORDINATES = ('domain_uuid', 'repository_uuid', 'store_uuid')
COMMAND_FIELDS = ('operation', 'principal', 'command_id', 'nonce') + COORDINATES + ('commit', 'digest', 'replaces')
# Only project_owner is admitted: the role the owner holds through the bootstrap enrollment.
SIGNER_TYPE = 'person'
SIGNER_ROLE = 'project_owner'
WRITES = ('entities', 'journal', 'commands', 'nonces')
# The refusal each contract kind the installed loader refuses is named by (contract_loader.CONTRACT_KINDS).
CONTRACT_REFUSALS = {'required_absence': 'missing_evidence:contract',
                     'unreadable': 'invalid_contract:unreadable',
                     'parse_failure': 'invalid_contract:parse_failure',
                     'invalid_structure': 'invalid_contract:invalid_structure'}
REFUSALS = ('invalid_input:command', 'invalid_input:coordinates', 'invalid_input:commit', 'invalid_input:digest',
            'invalid_input:replaces', 'invalid_input:digest_mismatch', 'invalid_input:current_digest',
            'not_authorized:key', 'not_authorized:signature', 'not_authorized:membership',
            'not_authorized:principal_type', 'not_authorized:role', 'not_authorized:scope', 'stale_subject',
            'missing_evidence:commit', 'missing_authority:repository', 'missing_authority:architecture',
            'unavailable_service:git', 'unavailable_service:validator', 'unavailable_service:store',
            'unknown_outcome') + tuple(CONTRACT_REFUSALS.values())
_DIGEST = re.compile(r'sha256:[0-9a-f]{64}\Z')
_COMMIT = re.compile(r'(?:[0-9a-f]{40}|[0-9a-f]{64})\Z')
_REGULAR_MODES = ('100644', '100755')


def _is_str(value):
    return isinstance(value, str) and value.strip() != ''


def _is_int(value, low):
    return type(value) is int and value >= low


def record_id(repository_uuid):
    return ENTITY_PREFIX + repository_uuid


def raw_digest(body):
    """sha256 over the raw bytes of a contract blob, nothing normalized."""
    return 'sha256:' + hashlib.sha256(body).hexdigest()


# ---------------------------------------------------------------------------------------------
# The record schema, veldo.architecture_record/v1: the one definition the Gate reads through.
# ---------------------------------------------------------------------------------------------

def _source_problems(source, where):
    if not isinstance(source, dict):
        return ['%s source must be a mapping of commit and path' % where]
    problems = []
    if set(source) != set(SOURCE_FIELDS):
        problems.append('%s source carries exactly %s' % (where, ', '.join(SOURCE_FIELDS)))
    if not isinstance(source.get('commit'), str) or not _COMMIT.match(source['commit']):
        problems.append('%s source commit must be a full lowercase object id' % where)
    if source.get('path') != CONTRACT_PATH:
        problems.append('%s source path must be %s' % (where, CONTRACT_PATH))
    return problems


def _entry_problems(entry, where):
    """The problems of one version's entry: contract_version, digest, source, accepted_by, command_id."""
    if not isinstance(entry, dict):
        return ['%s is not a mapping' % where]
    problems = []
    if set(entry) != set(ENTRY_FIELDS):
        problems.append('%s carries exactly %s' % (where, ', '.join(ENTRY_FIELDS)))
    if not _is_int(entry.get('contract_version'), 1):
        problems.append('%s contract_version must be an integer of at least 1' % where)
    if not isinstance(entry.get('digest'), str) or not _DIGEST.match(entry['digest']):
        problems.append('%s digest must be sha256: and 64 lowercase hexadecimal characters' % where)
    if 'source' in entry:
        problems.extend(_source_problems(entry['source'], where))
    for field in ('accepted_by', 'command_id'):
        if not _is_str(entry.get(field)):
            problems.append('%s %s must be a string' % (where, field))
    return problems


def record_problems(entity_id, kind, data):
    """Every way a stored entity fails veldo.architecture_record/v1, by name; [] for a valid record.
    The data is a closed mapping; the entity id is architecture:<repository_uuid>, its kind exactly
    architecture_contract; superseded lists the prior versions' entries in ascending contract_version
    from 1 with no gap."""
    problems = []
    if kind != ENTITY_KIND:
        problems.append('entity kind must be %s' % ENTITY_KIND)
    if not isinstance(entity_id, str) or not entity_id.startswith(ENTITY_PREFIX):
        problems.append('entity id must begin with %s' % ENTITY_PREFIX)
    if not isinstance(data, dict):
        return problems + ['record data must be a mapping']
    missing = [f for f in RECORD_FIELDS if f not in data]
    extra = sorted(set(data) - set(RECORD_FIELDS))
    problems.extend('record lacks %s' % f for f in missing)
    problems.extend('record carries unknown field %s' % f for f in extra)
    if data.get('schema') != SCHEMA:
        problems.append('schema must be %s' % SCHEMA)
    if not _is_str(data.get('repository_uuid')) or entity_id != record_id(data['repository_uuid']):
        problems.append('repository_uuid must be the entity id after %s' % ENTITY_PREFIX)
    if data.get('state') != STATE:
        problems.append('state must be %s' % STATE)
    if not _is_int(data.get('contract_version'), 1):
        problems.append('contract_version must be an integer of at least 1')
    if not isinstance(data.get('digest'), str) or not _DIGEST.match(data['digest']):
        problems.append('digest must be sha256: and 64 lowercase hexadecimal characters')
    if 'source' in data:
        problems.extend(_source_problems(data['source'], 'record'))
    for field in ('accepted_by', 'command_id'):
        if not _is_str(data.get(field)):
            problems.append('%s must be a string' % field)
    superseded = data.get('superseded')
    if 'superseded' in data and not isinstance(superseded, list):
        problems.append('superseded must be a list')
    elif isinstance(superseded, list):
        version = data.get('contract_version')
        if _is_int(version, 1) and len(superseded) != version - 1:
            problems.append('superseded must list the %d prior versions' % (version - 1))
        for index, entry in enumerate(superseded):
            where = 'superseded entry %d' % (index + 1)
            problems.extend(_entry_problems(entry, where))
            if isinstance(entry, dict) and entry.get('contract_version') != index + 1:
                problems.append('%s must be contract_version %d: ascending from 1 with no gap' % (where, index + 1))
    return problems


def _entry_of(data):
    return {f: data[f] for f in ENTRY_FIELDS}


# ---------------------------------------------------------------------------------------------
# The contract at a commit, from the bound repository's object store.
# ---------------------------------------------------------------------------------------------

class Refused(Exception):
    def __init__(self, code, detail=''):
        super().__init__('%s: %s' % (code, detail))
        self.code, self.detail = code, detail


def _git(repo, *args):
    try:
        return _git_process.run(['git', '-C', str(repo)] + list(args), capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as error:
        raise Refused('unavailable_service:git', type(error).__name__)


def contract_entry(repo, commit):
    """(mode, type, bytes) of CONTRACT_PATH at `commit` in the repository at `repo`, or None when the
    commit carries no entry there; bytes only for a regular blob. Missing commit is refused."""
    kind = _git(repo, 'cat-file', '-t', commit)
    if kind.returncode != 0 or kind.stdout.strip() != b'commit':
        raise Refused('missing_evidence:commit', 'no commit %s in the bound repository' % commit)
    listed = _git(repo, 'ls-tree', '-z', commit, '--', CONTRACT_PATH)
    if listed.returncode != 0:
        raise Refused('unavailable_service:git', 'ls-tree failed')
    for record in listed.stdout.split(b'\0'):
        head, _, path = record.partition(b'\t')
        if path.decode('utf-8', 'surrogateescape') != CONTRACT_PATH:
            continue
        mode, otype, oid = head.decode('ascii', 'replace').split(' ')
        if otype == 'blob' and mode in _REGULAR_MODES:
            blob = _git(repo, 'cat-file', 'blob', oid)
            if blob.returncode != 0:
                raise Refused('unavailable_service:git', 'cat-file failed')
            return mode, otype, blob.stdout
        return mode, otype, None
    return None


def _materialize_references(repo, commit, root, validator, parse):
    """Lay the analyzer references the contract names that exist at the commit into `root`, so the
    validator's referenced-but-absent rule is judged against the commit, not an empty directory."""
    try:
        data = validator.load_contract(root / CONTRACT_PATH, parse)
    except Exception:  # noqa: BLE001 - the loader itself names an unparseable contract below
        return
    analyzers = data.get('analyzers') if isinstance(data, dict) else None
    for analyzer in analyzers if isinstance(analyzers, list) else []:
        ref = analyzer.get('ref') if isinstance(analyzer, dict) else None
        parts = Path(ref).parts if _is_str(ref) else ()
        if not parts or Path(ref).is_absolute() or '..' in parts:
            continue
        found = _git(repo, 'cat-file', '-t', '%s:%s' % (commit, Path(*parts).as_posix()))
        if found.returncode == 0:
            target = root.joinpath(*parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            if found.stdout.strip() == b'tree':
                target.mkdir(exist_ok=True)
            elif not target.exists():
                target.write_bytes(b'')


# ---------------------------------------------------------------------------------------------
# The authority's side: the one writer.
# ---------------------------------------------------------------------------------------------

class ArchitectureAuthority:
    """One repository's architecture acceptance on the configured real store connection.

    `store` and `membership` are the control_store and control_membership modules; `repository` is
    the local Git repository bound to the repository uuid (control_store.bind_repositories: the first
    binding wins); `sign(bytes) -> text` signs journal records as `journal_signer`."""

    def __init__(self, store, membership, conn, coordinates, repository, journal_signer, sign,
                 authority_generation=1, clock=time.time, observe=None):
        if set(coordinates) != set(COORDINATES) or not all(_is_str(v) for v in coordinates.values()):
            raise Refused('invalid_input:coordinates', 'coordinates are domain, repository and store identities')
        if getattr(store, 'ARCHITECTURE_OPERATION', None) != OPERATION:
            raise Refused('invalid_input:command', 'the store does not reserve %s for the architecture record' % OPERATION)
        self.store, self.membership, self.AC = store, membership, membership.AC
        self.conn, self.ids = conn, dict(coordinates)
        self.journal_signer, self.sign = journal_signer, sign
        self.authority_generation, self.clock = authority_generation, clock
        self.observe = observe or (lambda event: None)
        self.observations = []
        self.counts = {'accepted': 0, 'refused': 0}
        self.refusals = {}
        self._validator = None
        store.bind_repositories(conn, self.ids['domain_uuid'], {self.ids['repository_uuid']: str(repository)})
        conn.command_registry[OPERATION] = {'transaction_transition': self._in_transaction, 'writes': WRITES}

    @property
    def record_id(self):
        return record_id(self.ids['repository_uuid'])

    def apply(self, packet):
        command = packet.get('command') if isinstance(packet, dict) else None
        command = command if isinstance(command, dict) else {}
        replaces = command.get('replaces')
        observation = dict(self.ids, operation='replace' if _is_int(replaces, 1) else 'accept',
                           principal=command.get('principal'), command_id=command.get('command_id'),
                           commit=command.get('commit'), path=CONTRACT_PATH, digest=command.get('digest'),
                           contract_version_before=None, contract_version_after=None, accepted_versions={})
        try:
            result = self._apply(packet, command, observation)
        except (Refused, self.store.StoreRefused) as error:
            result = {'ok': False, 'reason': error.code}
        except sqlite3.Error:
            result = {'ok': False, 'reason': 'unavailable_service:store'}
        except Exception as error:  # noqa: BLE001 - an unexpected fault is an unknown outcome, never an acceptance
            result = {'ok': False, 'reason': 'unknown_outcome:' + type(error).__name__}
        observation.update(outcome='accepted' if result['ok'] else 'refused',
                           refusal=None if result['ok'] else result['reason'])
        self.counts[observation['outcome']] += 1
        if not result['ok']:
            self.refusals[result['reason']] = self.refusals.get(result['reason'], 0) + 1
        self.observations.append(observation)
        self.observe(observation)
        return result

    def status(self):
        """Accepted and refused commands by refusal, and the current accepted version and digest."""
        row = self.conn.execute('SELECT kind, data FROM entities WHERE id=?', (self.record_id,)).fetchone()
        data = json.loads(row[1]) if row else None
        valid = row is not None and not record_problems(self.record_id, row[0], data)
        return dict(self.counts, refusals=dict(self.refusals), repository_uuid=self.ids['repository_uuid'],
                    contract_version=data['contract_version'] if valid else None,
                    digest=data['digest'] if valid else None)

    def _validate(self):
        if self._validator is None:
            validate = _organ('validate')
            self._validator = (validate, validate.entry_validator())
        return self._validator

    def _authorize(self, packet, command):
        state = self.membership.authority_state(self.store, self.conn)
        now = self.clock()
        principal = command['principal']
        key = self.AC.active_key(state['keyring'], principal, now)
        if not key or not _is_str(key.get('public_key')):
            raise Refused('not_authorized:key', 'no active verification key for the signer')
        verified, _detail = self.AC.ssh_keygen_verify(self.store.canonical_bytes(command), packet['signature'],
                                                      self.AC.allowed_signers_line(principal, key['public_key']),
                                                      principal)
        if not verified:
            raise Refused('not_authorized:signature', 'the command signature does not verify against the active key')
        entry = self.AC.membership_entry(state['membership'], principal)
        active, why = self.AC.active_member(entry, now)
        if not active:
            raise Refused('not_authorized:membership', why or 'no membership')
        if entry.get('principal_type') != SIGNER_TYPE:
            raise Refused('not_authorized:principal_type', 'only a person member accepts an architecture')
        if SIGNER_ROLE not in (entry.get('roles') or []):
            raise Refused('not_authorized:role', 'accepting an architecture needs %s' % SIGNER_ROLE)
        if not self.membership.scope_covers(entry.get('scope'), self.ids['repository_uuid']):
            raise Refused('not_authorized:scope', 'the membership scope does not cover the repository')
        return state, key

    def _apply(self, packet, command, observation):
        if (not isinstance(packet, dict) or not isinstance(packet.get('command'), dict)
                or not isinstance(packet.get('signature'), str) or not packet['signature'].isascii()):
            raise Refused('invalid_input:command', 'a command mapping and its ASCII signature')
        if (set(command) != set(COMMAND_FIELDS) or command['operation'] != COMMAND_OPERATION
                or not all(_is_str(command[k]) for k in ('principal', 'command_id', 'nonce') + COORDINATES)):
            raise Refused('invalid_input:command', 'an accept command carries exactly %s' % ', '.join(COMMAND_FIELDS))
        if any(command[k] != v for k, v in self.ids.items()):
            raise Refused('invalid_input:coordinates', 'the command names another domain, repository or store')
        if not isinstance(command['commit'], str) or not _COMMIT.match(command['commit']):
            raise Refused('invalid_input:commit', 'the commit is a full lowercase object id')
        if not isinstance(command['digest'], str) or not _DIGEST.match(command['digest']):
            raise Refused('invalid_input:digest', 'the digest is sha256: and 64 lowercase hexadecimal characters')
        if not _is_int(command['replaces'], 0):
            raise Refused('invalid_input:replaces', 'replaces is the contract version replaced, 0 for none')
        state, key = self._authorize(packet, command)
        signed = self.store.digest_of(command)
        prior = self.conn.execute('SELECT artifact_digests FROM journal WHERE command_id=?',
                                  (command['command_id'],)).fetchone()
        if prior is not None:
            # A retry of an accepted command: the same signed content is the committed result, other
            # content under the same identity is the store's content conflict.
            if signed not in json.loads(prior[0]):
                raise self.store.StoreRefused('command_content_conflict', 'command %s was accepted with other content'
                                              % command['command_id'])
            result = self.conn.execute('SELECT result FROM commands WHERE command_id=?', (command['command_id'],)).fetchone()
            return {'ok': True, 'reason': 'replayed', 'receipt': dict(json.loads(result[0]), replayed=True),
                    'record': self._record()}
        if self.conn.execute('SELECT 1 FROM nonces WHERE nonce=?', (command['nonce'],)).fetchone():
            raise self.store.StoreRefused('nonce_consumed', 'the nonce was consumed by an earlier command')
        current = state['entities'].get(self.record_id)
        if current is not None and record_problems(self.record_id, current.get('kind'), current.get('data')):
            raise Refused('missing_authority:architecture', 'the stored architecture record is not a valid record')
        version = current['data']['contract_version'] if current is not None else 0
        observation['contract_version_before'] = version
        if command['replaces'] != version:
            raise Refused('stale_subject', 'the command replaces version %r; version %r is current'
                          % (command['replaces'], version))
        if current is not None and current['data']['digest'] == command['digest']:
            raise Refused('invalid_input:current_digest', 'these bytes are the accepted contract already')
        repo = self.store.bound_repository(self.conn, self.ids['domain_uuid'], self.ids['repository_uuid'])
        if repo is None:
            raise Refused('missing_authority:repository', 'no repository is bound to this repository uuid')
        entry = contract_entry(repo, command['commit'])
        if entry is not None and entry[2] is not None and raw_digest(entry[2]) != command['digest']:
            raise Refused('invalid_input:digest_mismatch', 'the stated digest is not the digest of the bytes at the commit')
        self._judge(repo, command['commit'], entry, command['digest'])
        touched = {self.record_id, command['principal'], key['key_id'], self.membership.VERSIONS_ENTITY}
        versions = {eid: state['entities'].get(eid, {}).get('version', 0) for eid in sorted(touched)}
        observation['accepted_versions'] = versions
        params = dict(repository_uuid=self.ids['repository_uuid'], principal=command['principal'],
                      command_id=command['command_id'], commit=command['commit'], digest=command['digest'],
                      replaces=command['replaces'])
        stored = dict(command_id=command['command_id'], principal=command['principal'], operation=OPERATION,
                      parameters=params, expected_versions=versions, artifact_digests=[signed, command['digest']],
                      nonce=command['nonce'])
        receipt = self.store.execute(self.conn, stored, self.journal_signer, self.sign, self.authority_generation)
        record = self._record()
        observation['contract_version_after'] = record['contract_version']
        return {'ok': True, 'reason': 'replaced' if command['replaces'] else 'accepted', 'receipt': receipt,
                'record': record}

    def _record(self):
        row = self.conn.execute('SELECT data FROM entities WHERE id=?', (self.record_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def _judge(self, repo, commit, entry, digest):
        """The installed validator's verdict on the entry at the commit, laid into a private root: a
        regular blob as its bytes, anything else present as a non-regular entry, absence as absence."""
        try:
            validate, validator = self._validate()
        except Exception as error:  # noqa: BLE001 - a validator that cannot load refuses, never accepts
            raise Refused('unavailable_service:validator', type(error).__name__)
        with tempfile.TemporaryDirectory(prefix='veldo-architecture-') as directory:
            root = Path(directory)
            target = root / CONTRACT_PATH
            target.parent.mkdir(parents=True)
            if entry is not None and entry[2] is not None:
                target.write_bytes(entry[2])
                _materialize_references(repo, commit, root, validator, validate.parse_yamlish)
            elif entry is not None:
                target.mkdir()  # present and not a regular file: a tree, a symbolic link or a submodule
            try:
                load, parsed = validate.entry_contract(str(root), True, arch=validator)
            except Exception as error:  # noqa: BLE001
                raise Refused('unavailable_service:validator', type(error).__name__)
        if load.refused:
            raise Refused(CONTRACT_REFUSALS.get(load.kind, 'invalid_contract:' + load.kind), '; '.join(load.problems))
        if parsed != digest:
            raise Refused('invalid_input:digest_mismatch', 'the validator judged other bytes than the stated digest')

    def _in_transaction(self, conn, params, before):
        """Inside the store's write transaction: the record as it stands at commit is the one replaced."""
        refused = self.store.StoreRefused
        aid = record_id(params['repository_uuid'])
        current = before.get(aid)
        prior = current['data'] if current is not None else None
        version = prior.get('contract_version') if isinstance(prior, dict) else 0
        if params['replaces'] != version:
            raise refused('stale_subject', 'version %r is current, the command replaces %r' % (version, params['replaces']))
        source = {'commit': params['commit'], 'path': CONTRACT_PATH}
        if prior is None:
            data = dict(schema=SCHEMA, repository_uuid=params['repository_uuid'], state=STATE, contract_version=1,
                        digest=params['digest'], source=source, accepted_by=params['principal'],
                        command_id=params['command_id'], superseded=[])
        else:
            data = dict(prior, contract_version=version + 1, digest=params['digest'], source=source, accepted_by=params['principal'], command_id=params['command_id'], superseded=list(prior['superseded']) + [_entry_of(prior)])
        problems = record_problems(aid, ENTITY_KIND, data)
        if problems:
            raise refused('transition_refused', '; '.join(problems))
        return {aid: {'kind': ENTITY_KIND, 'data': data}}


# ---------------------------------------------------------------------------------------------
# The front door: the owner's side, on his own machine.
# ---------------------------------------------------------------------------------------------

def build_command(repo, commit, *, principal, coordinates, replaces, command_id=None, nonce=None):
    """The accept command for the contract at `commit` in the repository at `repo`: the digest is of
    the blob's raw bytes. Refused when the commit carries no regular contract blob."""
    full = _git(repo, 'rev-parse', '--verify', '--quiet', commit + '^{commit}')
    if full.returncode != 0:
        raise Refused('missing_evidence:commit', 'no commit %s' % commit)
    commit = full.stdout.decode('ascii').strip()
    entry = contract_entry(repo, commit)
    if entry is None or entry[2] is None:
        raise Refused('missing_evidence:contract', 'the commit carries no regular %s' % CONTRACT_PATH)
    return dict({k: coordinates[k] for k in COORDINATES}, operation=COMMAND_OPERATION, principal=principal,
                command_id=command_id or 'architecture-accept-' + uuid.uuid4().hex,
                nonce=nonce or uuid.uuid4().hex, commit=commit, digest=raw_digest(entry[2]), replaces=int(replaces))


def sign_command(command, key_path, namespace=None):
    """{command, signature}: the canonical command bytes signed with the key at `key_path` through
    `ssh-keygen -Y sign` (the command namespace unless one is named)."""
    store = _organ('control_store')
    namespace = namespace or _organ('authority_contract').SIGNATURE_NAMESPACE
    signed = subprocess.run(['ssh-keygen', '-q', '-Y', 'sign', '-f', str(key_path), '-n', namespace],
                            input=store.canonical_bytes(command), capture_output=True, timeout=60)
    if signed.returncode != 0:
        raise Refused('not_authorized:signature', signed.stderr.decode('utf-8', 'replace').strip())
    return {'command': command, 'signature': signed.stdout.decode('ascii')}


def main(argv=None):
    parser = argparse.ArgumentParser(prog='veldo architecture',
                                     description='Sign an accept command for the architecture contract at a commit.')
    sub = parser.add_subparsers(dest='action', required=True)
    accept = sub.add_parser('accept', help='print the signed accept packet for the authority')
    accept.add_argument('--commit', required=True)
    accept.add_argument('--repo', default='.')
    accept.add_argument('--principal', required=True)
    accept.add_argument('--key', required=True, help='the signing key file (ssh-keygen -Y sign -f)')
    accept.add_argument('--replaces', type=int, default=0, help='the contract version replaced, 0 for none')
    for field in COORDINATES:
        accept.add_argument('--' + field.replace('_', '-'), dest=field, required=True)
    args = parser.parse_args(argv)
    try:
        command = build_command(args.repo, args.commit, principal=args.principal, replaces=args.replaces,
                                coordinates={k: getattr(args, k) for k in COORDINATES})
        packet = sign_command(command, args.key)
    except Refused as error:
        sys.stderr.write('veldo architecture accept refused: %s\n' % error.code)
        return 2
    sys.stdout.write(json.dumps(packet, sort_keys=True) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
