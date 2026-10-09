"""One owner-signed memory record, shared by every account (VELDO-0182)."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import time


def organ(name):
    spec = importlib.util.spec_from_file_location('memory_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PARTS = ('file_memory', 'ava_memory', 'knowledge_graph', 'memory_kb', 'claude_mem')
FIXED = {'ava_memory': 'data', 'knowledge_graph': 'knowledge_graph.db', 'memory_kb': 'data/chromadb'}
SAVE, HEAD, KIND = 'save_memory_store', 'memory:head', 'memory_store'
CM = organ('control_membership')
AC = CM.AC


class Refused(Exception):
    def __init__(self, code, detail=''):
        self.code, self.detail = code, detail
        super().__init__(code + (': ' + detail if detail else ''))


def digest(value):
    return 'sha256:' + hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def checked(path, part, kind='directory', owner=True):
    reason = None
    if not isinstance(path, str) or not os.path.isabs(path):
        reason = 'absolute_path_required'
    else:
        p = Path(path)
        # Runtime interpreters commonly use venv or system symlinks. Keep the
        # invocation path (venv discovery needs it), but validate the executable.
        if kind == 'interpreter':
            try:
                target = p.resolve(strict=True)
                info = target.stat()
                if info.st_uid not in (0, os.geteuid()) or info.st_mode & 0o022:
                    raise Refused('invalid_input:memory:%s:unsafe_interpreter' % part, path)
                if not target.is_file() or not os.access(target, os.X_OK):
                    raise Refused('invalid_input:memory:%s:not_executable' % part, path)
                return os.path.abspath(path)
            except OSError:
                raise Refused('invalid_input:memory:%s:missing' % part, path) from None
        if any(v.is_symlink() for v in (p, *p.parents)):
            reason = 'link'
        else:
            try:
                info = p.stat()
                if owner and info.st_uid != os.geteuid():
                    reason = 'not_owner'
                elif not (stat.S_ISDIR(info.st_mode) if kind == 'directory' else stat.S_ISREG(info.st_mode)):
                    reason = 'not_' + kind
                elif kind == 'interpreter' and not os.access(p, os.X_OK):
                    reason = 'not_executable'
            except OSError:
                reason = 'missing'
    if reason:
        raise Refused('invalid_input:memory:%s:%s' % (part, reason), str(path))
    return os.path.realpath(path)


def within(child, parent):
    return os.path.commonpath((os.path.realpath(child), os.path.realpath(parent))) == os.path.realpath(parent)


def locations(definition):
    for part, entry in definition['parts'].items():
        # The code directory is handed too, so it cannot contain a login either.
        yield part, entry.get('code', entry['data'])
        if entry.get('code'):
            yield part, entry['data']


def normalize(manifest):
    if (not isinstance(manifest, dict) or set(manifest) != {'host', 'assistant_mcp', 'parts'}
            or not isinstance(manifest['host'], str) or not manifest['host']
            or not isinstance(manifest['parts'], dict) or set(manifest['parts']) != set(PARTS)):
        raise Refused('invalid_input:memory:manifest')
    result = dict(host=manifest['host'], assistant_mcp=checked(manifest['assistant_mcp'], 'assistant_mcp', 'file'), parts={})
    for part in PARTS:
        e = manifest['parts'][part]
        fields = {'data'} if part == 'file_memory' else ({'code', 'interpreter'} if part in FIXED else {'code', 'command', 'data'})
        if not isinstance(e, dict) or set(e) != fields:
            raise Refused('invalid_input:memory:%s:entry' % part)
        entry = dict(e)
        if part != 'file_memory':
            entry['code'] = checked(e['code'], part)
        if part in FIXED:
            entry['interpreter'] = checked(e['interpreter'], part, 'interpreter')
            entry['data'] = os.path.join(entry['code'], FIXED[part])
        entry['data'] = checked(entry['data'], part, 'file' if part == 'knowledge_graph' else 'directory')
        if part == 'file_memory':
            checked(os.path.join(entry['data'], 'MEMORY.md'), part, 'file')
        if part == 'ava_memory':
            checked(os.path.join(entry['data'], 'chromadb'), part)
            checked(os.path.join(entry['data'], 'history.db'), part, 'file')
        if part == 'claude_mem':
            checked(os.path.join(entry['code'], 'package.json'), part, 'file')
            checked(os.path.join(entry['data'], 'claude-mem.db'), part, 'file')
            if not isinstance(e['command'], list) or not e['command'] or not all(isinstance(s, str) and s for s in e['command']):
                raise Refused('invalid_input:memory:claude_mem:command')
            checked(e['command'][0], part, 'interpreter')
        result['parts'][part] = entry
    return result


def manifest_of(definition):
    out = json.loads(json.dumps(definition))
    for part in FIXED:
        out['parts'][part].pop('data')
    return out


def read(conn):
    row = conn.execute('SELECT data FROM entities WHERE id=?', (HEAD,)).fetchone()
    return json.loads(row[0]) if row else None


def no_nested_links(definition):
    # Do not traverse links: even a nested alias can expose a profile at handoff.
    for part, entry in definition['parts'].items():
        path = entry['data']
        if Path(path).is_dir():
            for parent, dirs, files in os.walk(path, followlinks=False):
                for name in dirs + files:
                    if (Path(parent) / name).is_symlink():
                        raise Refused('invalid_input:memory:%s:link' % part)


def profiles_outside(conn, definition):
    for (raw,) in conn.execute("SELECT data FROM entities WHERE kind='account'"):
        for directory in json.loads(raw).get('profiles', {}).values():
            for part, path in locations(definition):
                if within(directory, path):
                    raise Refused('invalid_input:memory:contains_account_profile:' + part)
                if Path(path).is_dir():
                    for parent, dirs, files in os.walk(path, followlinks=False):
                        for name in dirs + files:
                            alias = Path(parent) / name
                            if alias.is_symlink() and (within(directory, alias) or within(alias, directory)):
                                raise Refused('invalid_input:memory:%s:link' % part)


def account_outside(conn, profiles):
    record = read(conn)
    if record:
        definition = record['definition']
        for directory in profiles.values():
            for part, path in locations(definition):
                if within(directory, path):
                    raise Refused('invalid_input:account_profile:inside_memory:' + part)


def handoff(conn):
    record = read(conn)
    if record is None:
        return None
    definition = normalize(manifest_of(record['definition']))
    profiles_outside(conn, definition)
    no_nested_links(definition)
    return dict(revision=record['revision'], definition=definition)


class Memory:
    def __init__(self, store, conn, ids, signer, sign, generation=1):
        self.S, self.conn, self.ids = store, conn, ids
        self.signer, self.sign, self.generation = signer, sign, generation
        store.declare_owners(conn, 'memory', kinds={KIND: (SAVE,)}, prefixes={'memory:': (SAVE,)}, module=__file__)
        conn.command_registry[SAVE] = {'transaction_transition': self.transition,
                                      'writes': ('entities', 'journal', 'commands', 'nonces')}

    def transition(self, conn, params, before):
        command, signature = params['signed_command'], params['signature']
        if (command.get('operation') != SAVE or any(command.get(k) != v for k, v in self.ids.items())
                or set(command.get('parameters', {})) != {'definition', 'base'}):
            raise Refused('invalid_input:memory:command')
        principal = command.get('principal')
        state, now = CM.authority_state(self.S, conn), time.time()
        member = AC.membership_entry(state['membership'], principal)
        key = AC.active_key(state['keyring'], principal, now) if AC.active_member(member, now)[0] else None
        if (not key or member.get('principal_type') != 'person' or 'project_owner' not in member.get('roles', [])
                or not CM.scope_covers(member.get('scope'), self.ids['repository_uuid'])
                or not AC.ssh_keygen_verify(self.S.canonical_bytes(command), signature,
                                           AC.allowed_signers_line(principal, key['public_key']), principal)[0]):
            raise Refused('unauthorized:memory_signature')
        p = command['parameters']
        definition = normalize(manifest_of(p['definition']))
        if definition != p['definition']:
            raise Refused('invalid_input:memory:definition')
        profiles_outside(conn, definition)
        previous = read(conn)
        revision = previous['revision'] if previous else 0
        if type(p['base']) is not int or p['base'] != revision:
            raise Refused('stale_version:memory')
        if previous and previous['owner'] != principal:
            raise Refused('unauthorized:memory_owner')
        value = dict(schema='veldo.memory_store/v1', revision=revision + 1, owner=principal,
                     definition=definition, signed_command=command, signature=signature)
        return {HEAD: {'kind': KIND, 'data': value},
                'memory:revision:%d' % (revision + 1): {'kind': KIND, 'data': value}}

    def admit(self, packet):
        command = packet['command']
        base = command['parameters']['base']
        if type(base) is not int or base < 0:
            raise Refused('invalid_input:memory:base')
        internal = dict(command_id=command['command_id'], operation=SAVE, principal=command['principal'],
                        nonce=command['command_id'], parameters=dict(signed_command=command, signature=packet.get('signature', '')),
                        artifact_digests=[], expected_versions={HEAD: base, 'memory:revision:%d' % (base + 1): 0})
        result = self.S.execute(self.conn, internal, self.signer, self.sign, self.generation)
        return dict(ok=True, revision=base + 1, seq=result['seq'])


def record_launch(root, dispatch_id, handed):
    """Durable metadata receipt; no sample or memory content, and no account login."""
    directory = Path(root) / 'memory' / 'launches'
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    checked(str(directory), 'launches')
    path = directory / (hashlib.sha256(dispatch_id.encode()).hexdigest() + '.json')
    receipt = dict(dispatch_id=dispatch_id, **handed)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as out:
        json.dump(receipt, out, sort_keys=True)
    return str(path)
