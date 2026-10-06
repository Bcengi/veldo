"""VELDO-0208: one authenticated landing contract and one confinement config.

The caller is the trusted, unconfined gate/lander. Never load this module or its
configuration from an implementing agent's candidate before reviewing it.
"""
import hashlib
import hmac
import json
import os
import pwd
from pathlib import Path
import stat

PROVENANCE = 'authority-reuse-stage/v2'
SCHEMA = 'veldo.reuse/v3'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('ascii')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


# Only reviewed authority files enter this identity; never a candidate-supplied ID.
AUTHORITY_FILES = ('.veldo/candidate_git.py', 'scripts/agent_sandbox.py', 'scripts/mutation_sandbox.py', 'scripts/gate_candidate.py', 'scripts/reuse_worker.py', 'scripts/mutation_observer.py', 'scripts/check_gate_mutations.py', 'scripts/case_reuse.py', 'scripts/case_inputs.py', 'scripts/case_trace.py', 'scripts/mutation_reuse.py', 'scripts/gate_reuse.py', 'scripts/reuse_stamp.py', 'scripts/agent_sandbox.json', '.veldo/reuse_evidence.py', '.veldo/git_process.py')


def authority_identity():
    root = Path(__file__).resolve().parents[1]
    return digest({name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                   for name in AUTHORITY_FILES})


def configuration(path=None):
    path = Path(path or os.environ.get('VELDO_AGENT_CONFIG') or
                Path(__file__).resolve().parents[1] / 'scripts/agent_sandbox.json').resolve(strict=True)
    document = json.loads(path.read_text())
    if document.get('schema') != 'veldo.agent-sandbox/v1':
        raise ValueError('unknown agent sandbox configuration')
    raw_store = document['store']
    # HOME is private scratch inside the launcher. The store belongs to the uid,
    # not to whichever HOME an implementing process supplies.
    if raw_store.startswith('~/'):
        raw_store = str(Path(pwd.getpwuid(os.getuid()).pw_dir) / raw_store[2:])
    store = Path(raw_store)
    if not store.is_absolute() or '..' in store.parts:
        raise ValueError('reuse store must be absolute')
    document['store'] = str(store.resolve())
    return path, document


def private(path, directory=False):
    info = path.lstat()
    if (not (stat.S_ISDIR if directory else stat.S_ISREG)(info.st_mode)
            or info.st_uid != os.getuid() or info.st_mode & 0o077):
        raise ValueError('cache path must be private and owned')


def probe(directory):
    """Actual kernel checks, not an environment marker an agent can clear.

    The configured agent domain cannot list this directory or open its key.
    A gate in that domain cannot obtain signing authority, even with a copied
    Python module. Opening for write also proves it is not a read-only grant.
    """
    directory = Path(directory)
    private(directory, directory=True)
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        key = directory / 'authentication.key'
        private(key)
        keyfd = os.open(key, os.O_RDWR | os.O_NOFOLLOW)
        try:
            secret = os.read(keyfd, 33)
        finally:
            os.close(keyfd)
        if len(secret) != 32:
            raise ValueError('invalid authentication key')
        return secret
    finally:
        os.close(fd)


def sign(payload, secret):
    return dict(payload=payload, mac=hmac.new(secret, canonical(payload), hashlib.sha256).hexdigest())


def authenticated(document, secret):
    if not isinstance(document, dict) or set(document) != {'payload', 'mac'}:
        raise ValueError('invalid authenticated envelope')
    if not hmac.compare_digest(sign(document['payload'], secret)['mac'], document['mac']):
        raise ValueError('reuse authentication failed')
    return document['payload']


def record(directory, key, secret):
    if not isinstance(key, str) or len(key) != 64 or any(c not in '0123456789abcdef' for c in key):
        raise ValueError('invalid reuse key')
    path = Path(directory) / (key + '.json')
    if path.with_suffix('.json.conflict').exists():
        raise ValueError('conflicting reuse record')
    private(path)
    if path.stat().st_size > 32 * 1024 * 1024:
        raise ValueError('oversized reuse record')
    raw = path.read_bytes()
    envelope = json.loads(raw)
    if raw != canonical(envelope):
        raise ValueError('noncanonical reuse record')
    payload = authenticated(envelope, secret)
    if (set(payload) != {'schema', 'key', 'result', 'provenance', 'authority'} or payload['schema'] != SCHEMA
            or payload['key'] != key or payload['provenance'] != PROVENANCE
            or payload['authority'] != authority_identity()):
        raise ValueError('missing non-agent gate provenance')
    return payload['result']


def landing_problem(document):
    """Every stamp declares freshness; positive reuse requires signed case references.

    Keys are declared-input digests in VELDO-0207. The trusted stage checks the
    current inputs; the signed receipt binds those keys and counts to its commit.
    Rechecking here never trusts a boolean asserting that authentication passed.
    """
    try:
        counts, force = document['reused'], document['force_fresh']
        if (type(force) is not bool or not isinstance(counts, dict) or not counts
                or any(type(n) is not int or n < 0 for n in counts.values())):
            raise ValueError('invalid reuse counts')
        if not any(counts.values()):
            return None
        if force or set(counts) != {'unit', 'mutation'} or counts['unit']:
            raise ValueError('unsupported reuse stage or forced reuse')
        _, config = configuration()
        directory = Path(config['store'])
        secret = probe(directory)
        payload = authenticated(document['reuse_evidence'], secret)
        if (set(payload) != {'schema', 'provenance', 'authority', 'commit', 'force_fresh', 'reused', 'records'}
                or payload['schema'] != 'veldo.landing-reuse/v1'
                or payload['provenance'] != PROVENANCE
                or payload['authority'] != authority_identity()
                or payload['commit'] != document['commit'] or payload['force_fresh'] is not force
                or payload['reused'] != counts or len(payload['records']) != counts['mutation']):
            raise ValueError('landing reuse binding differs')
        seen = set()
        for item in payload['records']:
            key = item['key']
            result = record(directory, key, secret)
            identity = result['case']['identity']
            if (key in seen or result['input_digest'] != key or digest(result) != item['result_digest']
                    or item['identity'] != identity or identity in seen):
                raise ValueError('declared case key or result differs')
            seen.update((key, identity))
        return None
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return 'missing_evidence:gate/authenticated_reuse_required'
