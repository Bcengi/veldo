"""Explicit Git identities and immutable repository bindings (VELDO-0142).

Setup owns these local metadata tables, like control_store's repository path registry.
All checks precede writes in one transaction. Credentials are keychain references only;
this module neither reads nor copies their values. Repository creation/adoption calls
configure with the identity chosen by the owner, never one inferred from Git.
"""
import json
import os
import re


class Refused(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


FIELDS = {'id', 'label', 'author_name', 'author_email', 'remote_host', 'remote_owner',
          'api_token', 'push_credential', 'projects_root', 'default_visibility'}
AUTHOR_PREFIXES = ('GIT_AUTHOR_', 'GIT_COMMITTER_')


def text(value):
    return isinstance(value, str) and bool(value.strip()) and not any(c in value for c in '\n\r\x00')


def identifier(value):
    return isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', value) is not None


def reference(value):
    return isinstance(value, str) and re.fullmatch(r'keychain:[A-Za-z0-9_][A-Za-z0-9_./-]*', value) is not None


def validate(identities):
    if not isinstance(identities, list) or not identities:
        raise Refused('missing_authority:git_identities')
    found = {}
    for record in identities:
        if not isinstance(record, dict) or set(record) != FIELDS:
            raise Refused('invalid_input:git_identity')
        push = record['push_credential']
        if (not identifier(record['id']) or not all(text(record[k]) for k in FIELDS - {'push_credential'})
                or any(c in record['author_name'] + record['author_email'] for c in '<>')
                or '@' not in record['author_email'] or record['remote_host'] != 'github.com'
                or not identifier(record['remote_owner']) or not os.path.isabs(record['projects_root'])
                or record['default_visibility'] not in ('private', 'public')
                or not reference(record['api_token']) or not isinstance(push, dict)
                or set(push) != {'kind', 'reference'} or push['kind'] not in ('token', 'ssh')
                or not reference(push['reference'])):
            raise Refused('invalid_input:git_identity')
        if record['id'] in found:
            raise Refused('invalid_input:duplicate_git_identity')
        found[record['id']] = record
    return found


def one(identity):
    if identity is None or identity == '' or identity == []:
        raise Refused('missing_authority:repository_identity')
    if isinstance(identity, (list, tuple, dict, set)):
        raise Refused('invalid_input:second_repository_identity')
    if not identifier(identity):
        raise Refused('invalid_input:repository_identity')
    return identity


def exists(conn, table):
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def records(conn, domain):
    if not exists(conn, 'git_identities'):
        return []
    return [json.loads(row[0]) for row in conn.execute(
        'SELECT data FROM git_identities WHERE domain=? ORDER BY identity', (domain,))]


def repository_record(conn, domain, repository):
    if not exists(conn, 'git_identity_repositories'):
        raise Refused('missing_authority:repository_identity')
    row = conn.execute('SELECT path, identity FROM git_identity_repositories WHERE domain=? AND repository=?',
                       (domain, repository)).fetchone()
    if row is None:
        raise Refused('missing_authority:repository_identity')
    return dict(domain=domain, repository=repository, path=row[0], identity=one(row[1]))


def resolve(conn, domain, repository, path=None):
    bound = repository_record(conn, domain, repository)
    if path is not None and bound['path'] != os.path.realpath(path):
        raise Refused('binding_mismatch:repository_identity_path')
    for record in records(conn, domain):
        if record['id'] == bound['identity']:
            return record
    raise Refused('missing_authority:git_identity')


def configure(conn, domain, identities, repositories, *, check_only=False, observe=None):
    """Atomically add identities and {repository: {path, identity}} records, or replay.

    An existing identity definition or repository binding can never be replaced.
    check_only is the setup rerun preflight and performs no writes, including DDL.
    """
    emit = observe or (lambda event: None)
    event = dict(operation='configure_git_identities', domain=domain)
    try:
        wanted = validate(identities)
        if not text(domain) or not isinstance(repositories, dict):
            raise Refused('invalid_input:repository_identity')
        targets = {}
        for repository, record in repositories.items():
            if not text(repository) or not isinstance(record, dict):
                raise Refused('invalid_input:repository_identity')
            identity = one(record.get('identity'))
            if set(record) != {'path', 'identity'} or not text(record['path']):
                raise Refused('invalid_input:repository_identity')
            targets[repository] = dict(path=os.path.realpath(record['path']), identity=identity)
        if len({target['path'] for target in targets.values()}) != len(targets):
            raise Refused('binding_mismatch:repository_identity_path')
        conn.execute('BEGIN' if check_only else 'BEGIN IMMEDIATE')
        try:
            prior = {r['id']: r for r in records(conn, domain)}
            for identity, record in wanted.items():
                if identity in prior and prior[identity] != record:
                    raise Refused('binding_mismatch:git_identity_change')
            for repository, target in targets.items():
                if target['identity'] not in dict(prior, **wanted):
                    raise Refused('missing_authority:git_identity')
                if exists(conn, 'git_identity_repositories'):
                    other = conn.execute('SELECT repository FROM git_identity_repositories WHERE domain=? AND path=?',
                                         (domain, target['path'])).fetchone()
                    if other is not None and other[0] != repository:
                        raise Refused('binding_mismatch:repository_identity_path')
                try:
                    old = repository_record(conn, domain, repository)
                except Refused as error:
                    if error.code != 'missing_authority:repository_identity':
                        raise
                else:
                    if old['identity'] != target['identity']:
                        raise Refused('binding_mismatch:repository_identity_change')
                    if old['path'] != target['path']:
                        raise Refused('binding_mismatch:repository_identity_path')
            if not check_only:
                conn.execute('CREATE TABLE IF NOT EXISTS git_identities (domain TEXT, identity TEXT, data TEXT NOT NULL, PRIMARY KEY(domain, identity))')
                conn.execute('CREATE TABLE IF NOT EXISTS git_identity_repositories (domain TEXT, repository TEXT, path TEXT NOT NULL, identity TEXT NOT NULL, PRIMARY KEY(domain, repository), UNIQUE(domain, path))')
                for identity, record in wanted.items():
                    conn.execute('INSERT OR IGNORE INTO git_identities VALUES (?,?,?)',
                                 (domain, identity, json.dumps(record, sort_keys=True)))
                for repository, target in targets.items():
                    conn.execute('INSERT OR IGNORE INTO git_identity_repositories VALUES (?,?,?,?)',
                                 (domain, repository, target['path'], target['identity']))
            conn.execute('ROLLBACK' if check_only else 'COMMIT')
        except BaseException:
            if conn.in_transaction:
                conn.execute('ROLLBACK')
            raise
    except Refused as error:
        emit(dict(event, outcome='refused', refusal=error.code))
        raise
    for identity in wanted:
        emit(dict(event, identity=identity, outcome='accepted'))
    return records(conn, domain)


def environment(environment):
    return {key: value for key, value in environment.items()
            if not (key.startswith(AUTHOR_PREFIXES) or key in ('GIT_CONFIG_PARAMETERS', 'GIT_CONFIG_COUNT')
                    or re.fullmatch(r'GIT_CONFIG_(KEY|VALUE)_[0-9]+', key))}


def author(record):
    return record['author_name'], record['author_email']


def metrics(observations):
    counts = {}
    for event in observations:
        row = counts.setdefault(event.get('identity'), {'accepted': 0, 'refusals': {}})
        if event.get('outcome') == 'accepted':
            row['accepted'] += 1
        if event.get('refusal'):
            reason = event['refusal']
            row['refusals'][reason] = row['refusals'].get(reason, 0) + 1
    return counts
