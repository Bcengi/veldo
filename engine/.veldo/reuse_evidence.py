"""VELDO-0208: one authenticated landing contract and one confinement config.

The caller is the trusted, unconfined gate/lander. Never load this module or its
configuration from an implementing agent's candidate before reviewing it.
"""
import hashlib
import hmac
import json
import math
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
AUTHORITY_FILES = ('.veldo/candidate_git.py', 'scripts/agent_sandbox.py', 'scripts/gate_fixtures.py', 'scripts/mutation_sandbox.py', 'scripts/gate_candidate.py', 'scripts/reuse_worker.py', 'scripts/mutation_observer.py', 'scripts/mutation_ownership.py', 'scripts/check_gate_mutations.py', 'scripts/case_reuse.py', 'scripts/case_inputs.py', 'scripts/case_trace.py', 'scripts/mutation_reuse.py', 'scripts/gate_reuse.py', 'scripts/gate_changes.py', 'scripts/reuse_stamp.py', 'scripts/agent_sandbox.json', '.veldo/reuse_evidence.py', '.veldo/git_process.py', 'scripts/gate_legs.py', 'scripts/gate_unconfined.json', 'scripts/gate_schedule.py', 'scripts/gate_graph.json')


# An authority may lack these, and that is a state of its own, not an error: with no unconfined
# list every gate stage is confined (VELDO-0208), as in an authority that predates the list or an
# adopter's installation, which never receives one. Absent is recorded as ABSENT, which no digest
# equals, so adding or removing the list changes the identity; a list that is present is hashed
# like any other file, whatever it holds.
OPTIONAL_AUTHORITY_FILES = ('scripts/gate_unconfined.json', 'scripts/gate_graph.json')
ABSENT = 'absent'


def _file_identity(root, name):
    try:
        return hashlib.sha256((root / name).read_bytes()).hexdigest()
    except FileNotFoundError:
        if name in OPTIONAL_AUTHORITY_FILES:
            return ABSENT
        raise


def authority_identity():
    root = Path(__file__).resolve().parents[1]
    return digest({name: _file_identity(root, name) for name in AUTHORITY_FILES})


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


def audit_rate(record):
    return 10 if record.get('reuse_admission') == 'VELDO-0222' else 5


def audit_differences(stored, fresh, case):
    """Compare exactly the verdict-bearing observations; retain other mutant differences."""
    def fields(record):
        return dict(baseline=record['baseline']['observations'], noop=record['noop']['observations'],
                    mutant_targets=[row for row in record['mutant']['observations']
                                    if row[0].split()[-1] in case['rows']],
                    **{k: record[k] for k in ('replacement_count', 'old_digest', 'new_digest')})
    before, after = fields(stored), fields(fresh)
    differences = {k: dict(reused=before[k], fresh=after[k], verdict=True)
                   for k in before if before[k] != after[k]}
    other = lambda r: [row for row in r['mutant']['observations'] if row[0].split()[-1] not in case['rows']]
    if other(stored) != other(fresh):
        differences['mutant_other'] = dict(reused=other(stored), fresh=other(fresh), verdict=False)
    return differences


def check_audit(audit, reused, force=False):
    """Shared reducer/landing completeness check. Authentication binds the draw to the gate."""
    population, entries = audit['population'], audit['entries']
    members = {p['identity']: p for p in population}
    chosen = {e['identity']: e for e in entries}
    if (len(members) != len(population) or len(chosen) != len(entries)
            or not set(chosen) <= set(members) or len(population) != reused + len(entries)
            or (force and population) or len(entries) < min(len(population), 8)):
        raise ValueError('incomplete reuse audit')
    groups = {}
    for identity, member in members.items():
        if member['rate'] not in (5, 10):
            raise ValueError('invalid reuse audit rate')
        group = groups.setdefault((member['suite'], member['rate']), [0, 0])
        group[0] += 1
        group[1] += identity in chosen
    if any(n < math.ceil(total * rate / 100) for (_, rate), (total, n) in groups.items()):
        raise ValueError('incomplete reuse audit suite spread')
    if (audit['audited'] != len(entries) or audit['matched'] != len(entries) or audit['mismatched'] != 0):
        raise ValueError('inconsistent reuse audit counts')
    for identity, entry in chosen.items():
        member = members[identity]
        fresh = entry['fresh_record']
        if (entry['key'] != member['key'] or fresh['case']['identity'] != identity
                or fresh['case']['suite'] != member['suite'] or entry['matched'] is not True
                or any(d['verdict'] for d in entry['differences'].values())
                or entry['fresh_digest'] != digest(fresh)):
            raise ValueError('invalid reuse audit entry')
    return members, chosen


def authenticate_audit(audit, reused, force, directory, secret):
    members, chosen = check_audit(audit, reused, force)
    for identity, entry in chosen.items():
        stored = record(directory, entry['key'], secret)
        fresh = entry['fresh_record']
        if (stored['case'] != fresh['case'] or stored['input_digest'] != entry['key']
                or digest(stored) != entry['result_digest']
                or audit_rate(stored) != members[identity]['rate']
                or audit_differences(stored, fresh, fresh['case']) != entry['differences']):
            raise ValueError('reuse audit observation binding differs')
    return members, chosen


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
        if not any(counts.values()) and 'reuse_evidence' not in document:
            return None
        if force or set(counts) != {'unit', 'mutation'} or counts['unit']:
            raise ValueError('unsupported reuse stage or forced reuse')
        _, config = configuration()
        directory = Path(config['store'])
        secret = probe(directory)
        payload = authenticated(document['reuse_evidence'], secret)
        if (set(payload) != {'schema', 'provenance', 'authority', 'commit', 'force_fresh', 'reused', 'records', 'audit'}
                or payload['schema'] != 'veldo.landing-reuse/v1'
                or payload['provenance'] != PROVENANCE
                or payload['authority'] != authority_identity()
                or payload['commit'] != document['commit'] or payload['force_fresh'] is not force
                or payload['reused'] != counts or len(payload['records']) != counts['mutation']):
            raise ValueError('landing reuse binding differs')
        members, chosen = authenticate_audit(payload['audit'], counts['mutation'], force, directory, secret)
        seen = set()
        for item in payload['records']:
            key = item['key']
            result = record(directory, key, secret)
            identity = result['case']['identity']
            if (key in seen or result['input_digest'] != key or digest(result) != item['result_digest']
                    or item['identity'] != identity or identity in seen or identity in chosen
                    or members.get(identity) != dict(identity=identity, key=key, suite=result['case']['suite'],
                                                     rate=audit_rate(result))):
                raise ValueError('declared case key or result differs')
            seen.update((key, identity))
        return None
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return 'missing_evidence:gate/authenticated_reuse_required'
