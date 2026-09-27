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
GP = organ('git_process')


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
    try:
        raw = Path(reference['path']).read_bytes()
        document = json.loads(raw)
    except (OSError, ValueError, TypeError, KeyError):
        raise Refused('missing_evidence:engine_artifact')
    if (P.digest(raw) != (record.get('artifact') or {}).get('digest')
            or document.get('dispatch_id') != record.get('dispatch_id')):
        raise Refused('binding_mismatch:engine_artifact')
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
        """Read worker Git only after neutralizing its local configuration and hooks."""
        work = Path(self.clones._paths(handle)['work'])
        commit = result.get('commit')
        if not P._hex(commit):
            raise Refused('missing_evidence:build_commit')
        config = work / '.git' / 'config'
        config.unlink(missing_ok=True)
        config.write_text('[core]\nrepositoryformatversion = 0\nbare = false\nhooksPath = /dev/null\nfsmonitor = false\n')
        if not P.commit_exists(work, commit) or not P.descends(work, revision, commit):
            raise Refused('binding_mismatch:build_commit')
        fetched = GP.run(['git', '-C', str(self.root), '-c', 'core.hooksPath=/dev/null', 'fetch', OPT + 'no-tags',
                          OPT + 'no-write-fetch-head', str(work), commit], capture_output=True, timeout=60)
        if fetched.returncode or not P.commit_exists(self.root, commit):
            raise Refused('unavailable_service:build_objects')

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
        GP.run(['git', 'clone', '-q', OPT + 'no-checkout', OPT + 'no-hardlinks', str(self.root), directory],
               check=True, capture_output=True, timeout=60)
        GP.run(['git', '-C', directory, 'checkout', '-q', OPT + 'detach', result['commit']],
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
