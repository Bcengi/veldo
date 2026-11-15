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
import shutil
import stat
import tempfile
import time

OPT = '-' * 2


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


def answer(document):
    """Only the final answer of the declared engine, never an exit code."""
    if document.get('engine') == 'claude_code':
        return (document.get('terminal') or {}).get('result')
    if document.get('engine') == 'codex':
        messages = [json.loads(line).get('item', {}) for line in document.get('lines') or []
                    if json.loads(line).get('type') == 'item.completed']
        return next((m.get('text') for m in reversed(messages) if m.get('type') == 'agent_message'), None)
    return None


def artifact(record, reference):
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
    if not L.D.completed(record):
        raise Refused('unknown_outcome:engine/' + str(document.get('verdict')))
    return document


SPACE_ENDED = ('removed', 'gone')  # the states of an item whose thing is no longer on disk
SPACE_SAFE = ('gone', 'clear', 'kept')  # the answers of the look with no ledger that allow a delete
_SPACE = {}


def space_signal(space, event, paths, emitter, ended=False, confirm=False, alone=False):
    """VELDO-0303: send `event` through Signal (control_space_signal.signal) for the things at `paths`
    and say what became of each: {path: {item, state, deferral}}. Nothing here deletes anything:
    whatever goes is removed by Signal's removers, after the safety rules and the keep step.

    `space` is what the installation wires in when it has a space ledger: a mapping with ledger (the
    control_space.Ledger) and, under their own names, the arguments Signal is given (probe, kinds,
    remover, free, keep, owner_live, landed, queued, run, proc, borrow_root). The items are the live
    ones the ledger records at or beneath `paths`. The event is signalled once for each owner among
    them, and the subject is every part of that owner. A path the ledger records no live item for
    answers with no item and the deferral not_in_ledger, and nothing is done to it; when the kernel
    says nothing is at that path (not found, and no other answer) it answers gone, for there is
    nothing to remove. Whatever raises removes nothing: every path then answers with the deferral
    remove_refused and what was raised.

    `ended` says the caller has just read from the kernel that the runs owning these items are over:
    rule 3 is answered conclusive for those runs and for no other owner. `confirm` first confirms the
    items still in state declared (a creation that failed part way), so the event reaches them.
    `alone` refuses, with nothing signalled, when the subject would also end a worktree or an agent
    repository that is not at or beneath `paths`."""
    paths = [os.path.normpath(str(path)) for path in paths]
    found = {path: {'item': None, 'state': None, 'deferral': 'not_in_ledger'} for path in paths}

    def beneath(record):
        where = (record.get('locator') or {}).get('path')
        return bool(where) and any(where == path or where.startswith(path + '/') for path in paths)

    def owned(record, subject):
        owner = record.get('owner') or {}
        return all(((owner.get(part) or {}).get('id') if part == 'run' else owner.get(part)) == wanted
                   for part, wanted in subject.items())

    try:
        ledger = space['ledger']
        given = {key: value for key, value in space.items() if key != 'ledger'}
        every = ledger.items()
        live = {identity: record for identity, record in every.items()
                if record.get('state') not in SPACE_ENDED and beneath(record)}
        subjects, runs = [], set()
        for identity, record in sorted(live.items()):
            if confirm and record.get('state') == 'declared':
                ledger.confirm(identity)
            owner = dict(record.get('owner') or {})
            if isinstance(owner.get('run'), dict):
                owner['run'] = owner['run'].get('id')
                runs.add(owner['run'])
            if owner and owner not in subjects:
                subjects.append(owner)
        others = [identity for identity, record in sorted(every.items())
                  if alone and identity not in live and record.get('state') not in SPACE_ENDED
                  and record.get('kind') in ('worktree', 'agent_repository')
                  and any(owned(record, subject) for subject in subjects)]
        if others:
            raise ValueError('the owner of this thing also owns %s: the event would end it too'
                             % ', '.join(others[:3]))
        if ended:
            wired = given.get('owner_live')
            given['owner_live'] = lambda owner: (
                {'conclusive': True, 'group_empty': True} if (owner.get('run') or {}).get('id') in runs
                else wired(owner) if wired else None)
        if 'signal' not in _SPACE:
            _SPACE['signal'] = organ('control_space_signal').signal
        for subject in subjects:
            _SPACE['signal'](ledger, event, subject, emitter=emitter, **given)
        for identity, record in live.items():
            where = record['locator']['path']
            if where in found:
                now = ledger.item(identity) or {}
                found[where] = {'item': identity, 'state': now.get('state'),
                                'deferral': (now.get('deferral') or {}).get('rule')
                                if now.get('state') == 'deferred' else None}
        for path in paths:
            if found[path]['item'] is None and space_absent(path):
                found[path] = {'item': None, 'state': 'gone', 'deferral': None}
    except Exception as error:  # noqa: BLE001 - what could not be signalled is not removed
        raised = '%s: %s' % (type(error).__name__, str(error)[:300])
        found = {path: {'item': None, 'state': None, 'deferral': 'remove_refused', 'raised': raised}
                 for path in paths}
    return found


def space_absent(path):
    """Whether the kernel says nothing is at `path`: not found, and nothing else. A path that could
    not be read (a folder above it that may not be searched, a failing disk) is not absent."""
    try:
        os.lstat(path)
    except FileNotFoundError:
        return True
    except OSError:
        return False
    return False


def space_refusal(entry):
    """The name of the refusal for a thing Signal did not remove: space_deferred and the rule that
    deferred it; for an item no rule deferred, the state it is in (due in report mode, removing when
    it was left under its marked name, kept, present); not_in_ledger when no item records it."""
    return 'space_deferred:' + str(entry.get('deferral') or entry.get('state') or 'not_in_ledger')


def space_standalone(path, kind, main=None, event='run_finished', ticket=None, skip=()):
    """VELDO-0303: the look before a delete where no ledger is wired (control_space_standalone): the
    unique work probe and the keep step for the thing at `path`, {path, item, state, deferral, said,
    refs}. This module deletes the thing only when the state is one of SPACE_SAFE: nothing is there
    (gone), a folder holds no repository (clear), or the commits of a worktree or a private repository
    are on kept refs in `main` (kept). Anything else stays where it is. Whatever raises removes nothing."""
    try:
        if 'standalone' not in _SPACE:
            _SPACE['standalone'] = organ('control_space_standalone').standalone
        return _SPACE['standalone'](str(path), kind, main=None if main is None else str(main), event=event,
                                    ticket=ticket, skip=tuple(str(where) for where in skip))
    except Exception as error:  # noqa: BLE001 - what could not be looked at is not removed
        return {'path': str(path), 'item': None, 'state': None, 'deferral': 'remove_refused',
                'said': '%s: %s' % (type(error).__name__, str(error)[:300]), 'refs': {}}


def configured(root, path=None, space=None):
    path = Path(path) if path is not None else Path(root) / '.veldo' / 'worker.json'
    if not path.is_file():
        raise Refused('missing_authority:worker_configuration')
    return Runtime(root, path, space=space)


class Runtime:
    """One synchronous installed worker session. close() releases owned connections. `space` is the
    installation's space ledger and what Signal is given (space_signal), or None where there is none: with
    it the candidate folders are removed at close through Signal, and `kept` lists each one that was not
    (VELDO-0303)."""

    def __init__(self, root, path, space=None):
        self.space, self.kept = space, []
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
        self.floor = F.FloorAuthority(L.S, self.conn, repo=self.root, projections=c['work']['projections'],
                                      space=space, **common)
        # VELDO-0337: a verdict recorded lost between a verdict's commit and its send is sent again here,
        # at start, from the committed verdicts; it observes what it could not do and never raises.
        self.floor.reconcile_verdicts()
        self.dispatches = L.D.Dispatches(L.S, self.conn, **common)
        self.reservations = L.D.RES.Reservations(L.S, self.conn, authorize=L.D.RES.service_authority, **common)
        self.clones = CL.Clones(self.dispatches, space=space, **c['clones'])
        self.last = None
        self.events = []
        self.candidates = []

    def close(self):
        for directory in self.candidates:
            if self.space is None:
                # No ledger: the unique work probe and the keep step by themselves; a candidate folder whose
                # commits are not on kept refs in the repository, or that holds unsaved files, stays.
                found = space_standalone(directory, 'agent_repository', main=self.root)
                if found['state'] in SPACE_SAFE:
                    shutil.rmtree(directory, ignore_errors=True)
                else:
                    self.kept.append(dict(found, path=directory, refusal=space_refusal(found)))
                continue
            # VELDO-0303: a candidate folder is a private repository. It goes through Signal, after the rules
            # and the keep step, or it stays and the deferral is on the record.
            found = space_signal(self.space, 'run_finished', [directory], 'landing_line.close')[os.path.normpath(directory)]
            if found['state'] not in SPACE_ENDED:
                self.kept.append(dict(found, path=directory, refusal=space_refusal(found)))
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
                self._collect(handles[launch.dispatch_id], result, revision)
            self.events.append({'operation': station, 'unit': unit, 'dispatch': launch.dispatch_id,
                                'identity': role['identity'], 'outcome': 'artifact'})
            return result, {'dispatch': launch.dispatch_id, 'artifact': launch.artifact}
        finally:
            runner.wait(launch)

    def _collect(self, handle, result, revision):
        """Import object bytes only; Git never opens worker-owned metadata or configuration."""
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
        commit = result.get('commit')
        if not P._hex(commit):
            raise Refused('missing_evidence:build_commit')
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
        source = P.blob(self.root, spec['base'], spec['spec_path'])
        payload = {'operation': 'build', 'spec': source.decode(), 'spec_revision': spec['revision'],
                   'producer': role['identity'], 'output': 'Return JSON with final commit and proof. Commit implementation and evidence first, then '
                   'Proof uses veldo.proof/v1, spec_revision, producer, criteria with type/path/digest evidence, '
                   'checks and rollback. Commit that manifest at proof/' + spec['id'] + '/manifest.json in a second '
                   'commit, then return that final commit. Do not change the specification.'}
        result, reference = self._run(spec['id'], 'build', role, spec['base'], payload, context)
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
            body, reference = self._run(unit, 'review', role, assignment['source']['commit'], assignment, context)
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
