"""Installed build and independent review through the qualified Runner (VELDO-0129).

The owner supplies a receiver configuration plus `work`: a builder and reviewers,
each naming identity, account, adapter, configuration and seconds. Review identities
also name a signing file in a protected directory. No callable is configuration.
Every process gets a new dispatch and clone. Results are JSON in the engine's final
answer, bound by the receiver's artifact. Build results name commit and proof;
review results answer the floor assignment. Only the owning services accept them.
"""
import contextlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
import time

OPT = '-' * 2
PHASES = ('edit', 'test', 'proof')
PHASE_MESSAGES, PHASE_DISPATCHES, SOFT_MARGIN = 80, 6, 10
NOTE_PATH = 'proof/{unit}/phase-state.md'
NOTE_BYTES, BRIEF_BYTES = 8192, 4096
REMAINS_LINES, LINE_CHARS = 10, 200
READING_RULE = 'Read only needed parts of large files, by search and line range; never a whole large file.'
NOTE_RULE = ('Keep proof/<unit>/phase-state.md current in every commit: done, left, decisions made, '
             'approaches tried and rejected. At phase.soft steps stop new work, commit and finish the note.')
CAPPED_NOTE = 'Stopped at the phase cap. Uncommitted work is lost.'
OUTPUT = (
    'Edit and commit the change. Return JSON: commit (last or source), done (boolean), note (one line), '
    'remains (list of lines). Do not change the specification.',
    'Test and fix the change. Return JSON: commit (last or source), done (boolean), note (one line), '
    'remains (list of lines). Do not change the specification.',
    'Commit evidence first. Then commit proof/{unit}/manifest.json: veldo.proof/v1, spec_revision, producer, '
    'criteria with type/path/digest evidence, checks, rollback. Delete proof/{unit}/phase-state.md '
    '(overrides note rule). Return JSON: commit, proof, done:true, note, remains. Do not change the spec.',
)


def organ(name):
    spec = importlib.util.spec_from_file_location('work_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


L = organ('control_launch')
P = organ('control_proof')
EL = organ('control_eligibility')
CL = organ('control_clone')
_git_process = organ('git_process')


class Refused(EL.Refused):
    pass


def _brief_size(payload):
    measured = {key: value for key, value in payload.items() if key != 'spec'}
    if 'state' in measured:
        measured['state'] = {key: value for key, value in measured['state'].items() if key != 'note'}
    return len(P.canonical(measured))


def brief(spec, spec_text, role, phase, limits, source, done, remains, state):
    payload = dict(operation='build', spec=spec_text, spec_revision=spec['revision'], producer=role['identity'],
                   phase=dict(name=PHASES[phase], index=phase + 1, of=len(PHASES),
                              messages=limits['messages'], soft=limits['soft']),
                   source={'commit': source},
                   done=[dict(entry, note=entry['note'][:LINE_CHARS]) for entry in done],
                   remains=[line[:LINE_CHARS] for line in remains[:REMAINS_LINES]],
                   reading=READING_RULE, note=NOTE_RULE, output=OUTPUT[phase].format(unit=spec['id']))
    if state is not None:
        payload['state'] = dict(state)
    while _brief_size(payload) > BRIEF_BYTES:
        oldest = next((entry for entry in payload['done'] if entry['note']), None)
        if oldest is not None:
            oldest['note'] = ''
        elif payload['remains']:
            payload['remains'].pop()
        else:
            raise Refused('missing_authority:worker_configuration/build', 'brief_bytes')
    return payload


def _head_file(path, limit):
    """Read one entire regular file without following a link."""
    try:
        if not stat.S_ISREG(path.lstat().st_mode):
            raise ValueError('not_regular')
        with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), 'rb') as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
                raise ValueError('not_regular_or_oversize')
            data = handle.read(limit + 1)
        if len(data) > limit:
            raise ValueError('oversize')
        return data
    except (OSError, ValueError) as error:
        raise Refused('invalid_input:build_head', str(error)) from error


def answer(document):
    """Only the final answer of the declared engine, never an exit code."""
    if document.get('engine') == 'claude_code':
        return (document.get('terminal') or {}).get('result')
    if document.get('engine') == 'codex':
        messages = [json.loads(line).get('item', {}) for line in document.get('lines') or []
                    if json.loads(line).get('type') == 'item.completed']
        return next((m.get('text') for m in reversed(messages) if m.get('type') == 'agent_message'), None)
    return None


def stopped_by(document):
    if document.get('engine') == 'claude_code':
        return (document.get('exit') or {}).get('cause')
    if document.get('engine') == 'codex':
        return document.get('cause')
    return None


def bound(record, reference):
    """Resolve exactly the receiver document bound into the dispatch's exit."""
    missing = 'missing_evidence:build_artifact' if record.get('contract', {}).get('station') == 'build' else 'missing_evidence:engine_artifact'
    try:
        raw = Path(reference['path']).read_bytes()
        document = json.loads(raw)
    except (OSError, ValueError, TypeError, KeyError):
        raise Refused(missing)
    if (P.digest(raw) != (record.get('artifact') or {}).get('digest')
            or document.get('dispatch_id') != record.get('dispatch_id')):
        raise Refused(missing if record.get('contract', {}).get('station') == 'build' else 'binding_mismatch:engine_artifact')
    return document


def artifact(record, reference):
    document = bound(record, reference)
    if not L.D.completed(record):
        raise Refused('unknown_outcome:engine/' + str(document.get('verdict')))
    return document


def configured(root, path=None):
    path = Path(path) if path is not None else Path(root) / '.veldo' / 'worker.json'
    if not path.is_file():
        raise Refused('missing_authority:worker_configuration')
    return Runtime(root, path)


class Runtime:
    """One synchronous installed worker session. close() releases owned connections."""

    def __init__(self, root, path):
        self.root, self.path = Path(root).resolve(), Path(path).resolve()
        self.config = json.loads(self.path.read_text())
        c = self.config
        if not isinstance(c.get('work'), dict) or not c.get('clones'):
            raise Refused('missing_authority:worker_configuration')
        self.conn = L.S.open_store(c['store'])
        SIG = organ('control_signer')
        self.sign = lambda data: SIG.sign_bytes(c['journal_key'], data, L.JOURNAL_NAMESPACE)
        common = dict(domain=c['domain'], repository=c['repository'], principal=c['principal'],
                      signer=c['principal'], sign=self.sign, generation=c.get('authority_generation', 1))
        trust = EL.load_host_trust(c['host_trust']) if c.get('host_trust') else None
        if c.get('host_trust') and trust is None:
            raise Refused('missing_authority:host_trust')
        self.gate = EL.Gate(L.S, self.conn, domain_uuid=c['domain'], repository_uuid=c['repository'],
                            workspace=str(self.root), authority_generation=common['generation'],
                            settlement_trust=trust.settlement_trust(c.get('workspace')) if trust else None)
        self.proofs = P.ProofService(L.S, self.conn, repo=self.root, **common)
        F = organ('dispatch')
        self.floor = F.FloorAuthority(L.S, self.conn, repo=self.root, projections=c['work']['projections'], **common)
        self.dispatches = L.D.Dispatches(L.S, self.conn, **common)
        self.reservations = L.D.RES.Reservations(L.S, self.conn, authorize=L.D.RES.service_authority, **common)
        self.clones = CL.Clones(self.dispatches, **c['clones'])
        self.last = None
        self.events = []
        self.candidates = []

    def close(self):
        for directory in self.candidates:
            shutil.rmtree(directory, ignore_errors=True)
        self.floor.close()
        self.conn.close()

    @contextlib.contextmanager
    def launch(self, station, unit, *, context, ticket):
        """The executor scope; the Runner and receiver own the actual reservations."""
        self.gate.require(station, unit, context=context, ticket=ticket)
        yield type('Scope', (), {'context': dict(context), 'ticket': ticket})()

    def role(self, station, identity=None):
        roles = ([self.config['work'].get('builder')] if station == 'build'
                 else self.config['work'].get('reviewers') or [])
        role = next((r for r in roles if isinstance(r, dict) and (identity is None or r.get('identity') == identity)), None)
        if (role is None or not all(role.get(k) for k in ('identity', 'account', 'adapter', 'seconds'))
                or not isinstance(role.get('configuration'), dict)):
            raise Refused('missing_authority:worker_configuration/' + station)
        adapter = self.config.get('adapters', {}).get(role['adapter']) or {}
        if adapter.get('engine') not in L.ENGINES or adapter.get('identity', 'local') != 'local':
            raise Refused('unsupported_configuration:worker_adapter')
        # The custody and clone entrances are mandatory for this installed journey.
        argv = adapter.get('argv') or []
        inner = L.custody_worker(argv)
        if inner == argv or inner[:5] != self.clones.adapter([])[:5]:
            raise Refused('unsupported_configuration:worker_isolation')
        return role

    def reviewer(self, unit):
        record = self.floor.record(unit) or {}
        used = {r['reviewer'] for r in record.get('reviews') or [] if r['attempt'] == record.get('attempt')}
        for role in self.config['work'].get('reviewers') or []:
            if role.get('identity') not in used and role.get('identity') not in record.get('builders', []):
                return self.role('review', role.get('identity'))
        raise Refused('missing_authority:independent_reviewer')

    def _run(self, unit, station, role, revision, payload, context):
        context = dict(context, holder=context.get('holder') or role['identity'])
        self.gate.require('provider_request', unit, context=context)
        handles = {}

        def receive(contract):
            handles[contract['dispatch_id']] = self.clones.create(contract)
            if station == 'build':
                # Still authority-owned: no worker has entered this clone yet.
                work = Path(self.clones._paths(handles[contract['dispatch_id']])['work'])
                _git_process.run(['git', '-C', str(work), 'repack', '-a', '-d'],
                                 check=True, capture_output=True, timeout=60)
                (work / '.git/objects/info/alternates').unlink(missing_ok=True)
            return L.invoke(self.path, contract, self.dispatches)

        runner = L.Runner(self.gate, self.reservations, self.dispatches, receive,
                          account=role['account'], clones=self.clones)
        launch = runner.submit(unit, station, holder=context['holder'], source=str(self.root), revision=revision,
                               payload=payload, adapter=role['adapter'], configuration=role['configuration'],
                               deadline=time.time() + role['seconds'], context=context)
        try:
            record = launch.wait()
            self.last = {'record': record, 'artifact': launch.artifact, 'messages': launch.messages}
            if not L.D.completed(record) or not record.get('artifact'):
                if station == 'build' and record.get('state') == 'exited' and record.get('artifact'):
                    doc = bound(record, launch.artifact)
                    if stopped_by(doc) == 'phase_cap':
                        gitdir = self._gitdir(handles[launch.dispatch_id])
                        commit = self._head(gitdir)
                        if commit != revision:
                            self._import(gitdir, commit, revision)
                        return None, {'dispatch': launch.dispatch_id, 'artifact': launch.artifact,
                                      'commit': commit}, 'phase_cap'
                raise Refused((record or {}).get('refusal') or 'unknown_outcome:engine')
            doc = artifact(record, launch.artifact)
            text = answer(doc)
            try:
                result = json.loads(text) if isinstance(text, str) else None
            except ValueError:
                result = None
            if not isinstance(result, dict):
                raise Refused('missing_evidence:' + station + '_result')
            if station == 'build':
                if type(result.get('done')) is not bool:
                    raise Refused('missing_evidence:build_result')
                self._collect(handles[launch.dispatch_id], result, revision)
            self.events.append({'operation': station, 'unit': unit, 'dispatch': launch.dispatch_id,
                                'identity': role['identity'], 'outcome': 'artifact'})
            return result, {'dispatch': launch.dispatch_id, 'artifact': launch.artifact,
                            'commit': result.get('commit')}, 'returned'
        finally:
            runner.wait(launch)

    def _gitdir(self, handle):
        work = Path(self.clones._paths(handle)['work'])
        gitdir = work / '.git'
        # Check directory entries before any Git call, including dangling links.
        if gitdir.is_symlink():
            raise Refused('invalid_input:build_gitdir/symlink')
        if not gitdir.is_dir():
            raise Refused('invalid_input:build_gitdir/not_directory')
        for name in ('commondir', 'objects/info/alternates', 'objects/info/http-alternates'):
            if os.path.lexists(gitdir / name):
                raise Refused('invalid_input:build_gitdir/' + name.rsplit('/', 1)[-1])
        return gitdir

    def _head(self, gitdir):
        raw = _head_file(gitdir / 'HEAD', 1024)
        try:
            head = raw.decode('ascii').removesuffix('\n')
            if re.fullmatch('[0-9a-f]{40}', head):
                return head
            if not head.startswith('ref: refs/heads/'):
                raise ValueError('head')
            name = head[len('ref: refs/heads/'):]
            parts = name.split('/')
            if (len(name) > 255 or any(not re.fullmatch('[A-Za-z0-9_.-]+', part)
                                     or part.startswith('.') or part.endswith('.lock') for part in parts)):
                raise ValueError('ref_name')
            parent = gitdir
            for part in ['refs', 'heads', *parts[:-1]]:
                parent = parent / part
                if os.path.lexists(parent) and not stat.S_ISDIR(parent.lstat().st_mode):
                    raise ValueError('ref_directory')
            ref = gitdir / 'refs' / 'heads' / name
            if os.path.lexists(ref):
                raw = _head_file(ref, 1024)
                commit = raw.decode('ascii').removesuffix('\n')
                if re.fullmatch('[0-9a-f]{40}', commit):
                    return commit
                raise ValueError('ref_commit')
            packed = _head_file(gitdir / 'packed-refs', 1024 * 1024).decode('ascii')
            matches = []
            for line in packed.splitlines():
                if line.startswith(('#', '^')):
                    continue
                fields = line.split()
                if fields and fields[-1] == 'refs/heads/' + name:
                    if len(fields) != 2 or not re.fullmatch('[0-9a-f]{40}', fields[0]):
                        raise ValueError('packed_commit')
                    matches.append(fields[0])
            if len(matches) != 1:
                raise ValueError('packed_matches')
            return matches[0]
        except (OSError, ValueError) as error:
            raise Refused('invalid_input:build_head', str(error)) from error

    def _state(self, commit, unit):
        path = NOTE_PATH.format(unit=unit)

        def read(*args):
            result = P._git(self.root, *args)
            if result.returncode:
                raise ValueError('git')
            return result.stdout

        try:
            entry = read('ls-tree', '-z', commit, OPT, path)
            if not entry:
                return {'missing': 'absent'}
            fields, found = entry.rstrip(b'\0').split(b'\t', 1)
            mode, kind, oid = fields.split()
            if found != path.encode() or mode not in (b'100644', b'100755') or kind != b'blob':
                return {'missing': 'not_a_file'}
            size = int(read('cat-file', '-s', oid.decode('ascii')))
            if size < 0:
                raise ValueError('size')
            if size > NOTE_BYTES:
                return {'missing': 'oversize'}
            raw = read('cat-file', 'blob', oid.decode('ascii'))
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            raise Refused('binding_mismatch:build_commit', 'state_note') from error
        try:
            return {'note': raw.decode('utf-8')}
        except UnicodeDecodeError:
            return {'missing': 'not_a_file'}

    def limits(self, spec, role):
        phase = role.get('phase', {})
        refusal = 'missing_authority:worker_configuration/build'
        if not isinstance(phase, dict):
            raise Refused(refusal, 'phase')
        limits = dict(messages=phase.get('messages', PHASE_MESSAGES),
                      dispatches=phase.get('dispatches', PHASE_DISPATCHES))
        for key, minimum in (('messages', 1), ('dispatches', len(PHASES))):
            if type(limits[key]) is not int or limits[key] < minimum:
                raise Refused(refusal, key)
        limits['soft'] = max(1, limits['messages'] - SOFT_MARGIN)
        # Even empty entries cost bytes. Avoid allocating an unbounded override.
        if limits['dispatches'] - 1 > BRIEF_BYTES // len(P.canonical(dict(phase='proof', commit='0' * 40, note=''))):
            raise Refused(refusal, 'brief_bytes')
        done = [dict(phase='proof', commit='0' * 40, note='') for _ in range(limits['dispatches'] - 1)]
        for index in range(len(PHASES)):
            brief(spec, '', role, index, limits, spec['base'], done, [], {'missing': 'not_a_file'})
        return limits

    def _collect(self, handle, result, revision):
        """Import object bytes only; Git never opens worker-owned metadata or configuration."""
        gitdir = self._gitdir(handle)
        commit = result.get('commit')
        if not P._hex(commit):
            raise Refused('missing_evidence:build_commit')
        self._import(gitdir, commit, revision)

    def _import(self, gitdir, commit, revision):
        with tempfile.TemporaryDirectory(prefix='import-', dir=self.config['work']['candidates']) as directory:
            source, collected = Path(directory) / 'source.git', Path(directory) / 'collected.git'
            for repo in (source, collected):
                _git_process.run(['git', 'init', '-q', OPT + 'bare', OPT + 'template=', str(repo)],
                                 check=True, capture_output=True, timeout=30)
            # An authority-owned fetch source exposes only the clone's object data. Copying
            # regular files (never hardlinks) also prevents later worker writes changing it.
            objects = gitdir / 'objects'
            def copy_objects(origin, target):
                if not stat.S_ISDIR(origin.lstat().st_mode):
                    raise Refused('invalid_input:build_gitdir/objects')
                target.mkdir(exist_ok=True)
                for entry in origin.iterdir():
                    mode = entry.lstat().st_mode
                    if stat.S_ISDIR(mode):
                        copy_objects(entry, target / entry.name)
                    elif stat.S_ISREG(mode):
                        shutil.copyfile(entry, target / entry.name, follow_symlinks=False)
                    else:
                        raise Refused('invalid_input:build_gitdir/objects')
            try:
                copy_objects(objects, source / 'objects')
            except OSError as error:
                raise Refused('invalid_input:build_gitdir/objects') from error
            (source / 'HEAD').write_text(commit + '\n')
            fetched = _git_process.run(['git', '-C', str(collected), '-c', 'core.hooksPath=/dev/null',
                                        'fetch', OPT + 'no-tags', OPT + 'no-write-fetch-head',
                                        str(source), commit], capture_output=True, timeout=60)
            if fetched.returncode or not P.commit_exists(collected, commit) or not P.descends(collected, revision, commit):
                raise Refused('binding_mismatch:build_commit')
            fetched = _git_process.run(['git', '-C', str(self.root), '-c', 'core.hooksPath=/dev/null',
                                        'fetch', OPT + 'no-tags', OPT + 'no-write-fetch-head',
                                        str(collected), commit], capture_output=True, timeout=60)
            if fetched.returncode or not P.commit_exists(self.root, commit):
                raise Refused('unavailable_service:build_objects')
        # VELDO-0254 AC2: the landing candidate's changed files are scanned before it can land. The scan reports
        # what it finds, masked; it never refuses the candidate, and a scan that fails is logged to the owner's
        # scan log by name and changes nothing here.
        L.candidate_scan(self.config, self.config.get('repository'), self.root, revision, commit)

    def build(self, spec, calls=None):
        role = self.role('build')
        context = dict(getattr(calls, 'context', {}) or {}, holder=role['identity'])
        spec_text = P.blob(self.root, spec['base'], spec['spec_path']).decode()
        limits = self.limits(spec, role)
        phase, count, source = 0, 0, spec['base']
        done, remains, state = [], [], None
        while phase < len(PHASES):
            if count >= limits['dispatches']:
                raise Refused('phase_budget:build', PHASES[phase])
            payload = brief(spec, spec_text, role, phase, limits, source, done, remains, state)
            result, reference, ended = self._run(spec['id'], 'build', role, source, payload, context)
            self.events.append(dict(operation='phase', unit=spec['id'], phase=PHASES[phase], index=phase + 1,
                                    dispatch=reference['dispatch'], identity=role['identity'], source=source,
                                    commit=reference['commit'], ended=ended))
            if ended == 'phase_cap':
                note = CAPPED_NOTE
                source = reference['commit']
            else:
                note = result.get('note') if isinstance(result.get('note'), str) else ''
                remains = [line for line in result.get('remains', []) if isinstance(line, str)] if isinstance(
                    result.get('remains'), list) else []
                source = result['commit']
            done.append(dict(phase=PHASES[phase], commit=source, note=note))
            state = self._state(source, spec['id'])
            count += 1
            if ended == 'returned' and result['done']:
                phase += 1
        proof = result.get('proof')
        if not isinstance(proof, dict) or proof.get('spec_revision') != spec['revision']:
            raise Refused('missing_evidence:build_proof')
        # Verification uses a fresh checkout of the collected commit, never the worker's config or hooks.
        directory = tempfile.mkdtemp(prefix='candidate-', dir=self.config['work']['candidates'])
        self.candidates.append(directory)
        _git_process.run(['git', 'clone', '-q', OPT + 'no-checkout', OPT + 'no-hardlinks', str(self.root), directory],
               check=True, capture_output=True, timeout=60)
        _git_process.run(['git', '-C', directory, 'checkout', '-q', OPT + 'detach', result['commit']],
               check=True, capture_output=True, timeout=30)
        return dict(result, ok=True, producer=role['identity'], dispatch=reference['dispatch'], artifact=reference['artifact'], workspace=directory)

    def accept_build(self, spec, build):
        claim = L.D._entity(self.conn, L.D.CLM.claim_id(self.config['repository'], spec['id']))
        data = (claim or {}).get('data') or {}
        return self.floor.accept_build(spec['id'], commit=build['commit'], gate={'green': True},
                                       holder=data.get('holder'), generation=data.get('generation'),
                                       artifact=build.get('artifact'))

    def review(self, spec, calls=None):
        unit = spec['id']
        supplied = spec.get('assignment')
        last = None
        while supplied or self.floor.handoff_refusals(unit):
            role = self.role('review', supplied['reviewer']) if supplied else self.reviewer(unit)
            assignment = supplied or self.floor.assign_review(unit, role['identity'])
            context = dict(getattr(calls, 'context', {}) or {}, reviewer=role['identity'])
            context.setdefault('holder', (self.floor.record(unit) or {}).get('builder'))
            body, reference, _ended = self._run(unit, 'review', role, assignment['source']['commit'], assignment, context)
            required = {'schema': 'veldo.review_receipt/v1', 'assignment': assignment['assignment'], 'unit': unit,
                        'reviewer': role['identity'], 'source': assignment['source']['commit'],
                        'proof': assignment['proof']['digest']}
            if (any(body.get(k) != v for k, v in required.items()) or body.get('verdict') not in
                    ('pass', 'pass_with_notes', 'fail', 'escalate') or not isinstance(body.get('findings'), list)):
                raise Refused('missing_evidence:review_verdict')
            SIG = organ('control_signer')
            signature = SIG.sign_bytes(role['signing_file'], P.canonical(body), 'veldo-review')
            receipt = dict(reference, output=P.canonical({'body': body, 'signature': signature}).decode())
            last = dict(body, receipt=receipt)
            if supplied:
                return last
            recorded = self.floor.record_review(unit, assignment['assignment'], receipt, return_to='ready')
            if recorded['state'] != 'review':
                return last
        if last is None:
            raise Refused('missing_evidence:review_verdict')
        return last
