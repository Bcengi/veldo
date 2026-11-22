"""Atomic, attributable installation commits and last-good configuration (VELDO-0253).

The branch proposes; the signed settlement approves widening; one store transaction
records the entire accepted configuration and all workflow copies. No worktree file
is an input. A rejected tree never changes the accepted record.
"""
import json
import time
import os

import importlib.util
from pathlib import Path


def organ(name):
    spec = importlib.util.spec_from_file_location('config_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


I = organ('installation')
V = organ('control_installation_schema')
WF = organ('control_workflow')
Refused = WF.Refused


class Loader:
    def __init__(self, store, conn, repository, *, domain, workflow_repository, signer, sign,
                 secret_exists, decisions=None, notify=None, observe=None, clock=time.time, generation=1):
        self.store, self.conn, self.repo = store, conn, repository
        self.domain, self.workflow_repository = domain, workflow_repository
        self.signer, self.sign, self.generation = signer, sign, generation
        self.secret_exists, self.decisions = secret_exists, decisions
        self.notify = notify or (lambda event: None)
        self.observe = observe or (lambda event: print(json.dumps(event, sort_keys=True)))
        self.clock, self.pending = clock, None
        self.identity = 'installation:' + V.digest([domain, str(Path(repository.folder).resolve())])
        self.status_id = self.identity + ':status'
        self.counts, self.refusals, self.saves = {}, {}, {'accepted': 0, 'refused': 0}
        WF.attach_installation(store, conn, self)

    def record(self):
        return (WF._entity_row(self.conn, self.identity) or {}).get('data')

    @property
    def accepted_commit(self):
        return (self.record() or {}).get('commit')

    @property
    def live(self):
        return (self.record() or {}).get('configuration', {})

    def status(self):
        return (WF._entity_row(self.conn, self.status_id) or {}).get('data', {})

    def validate(self, files):
        return V.validate(files, secret_exists=self.secret_exists, resolve=WF._resolver(self.conn))

    def recheck(self):
        pending = self.pending
        if self.repo.head() != pending['parameters']['commit'] or self.accepted_commit != pending['previous']:
            raise Refused('stale_version')
        _, problems = self.validate(pending['files'])
        if problems:
            raise Refused(problems[0], codes=problems)
        if pending.get('decision') is not None:
            if self.decisions is None or self.decisions.approved(pending['proposal']) != pending['decision']:
                raise Refused('installation_waiting_approval:' + pending['parameters']['commit'])

    def _write(self, changes, snapshot, previous, *, mode, proposal=None, decision=None):
        params = {'commit': snapshot['commit'], 'previous': previous, 'mode': mode,
                  'changes_digest': V.digest(changes)}
        expected = {eid: (WF._entity_row(self.conn, eid) or {}).get('version', 0) for eid in changes}
        expected.setdefault(self.identity, (WF._entity_row(self.conn, self.identity) or {}).get('version', 0))
        command_id = 'installation/' + V.digest([params, expected]).split(':')[1]
        self.pending = {'parameters': params, 'changes': changes, 'files': snapshot['files'],
                        'previous': previous, 'proposal': proposal, 'decision': decision}
        try:
            return self.store.execute(self.conn, {'command_id': command_id, 'principal': self.signer,
                'operation': WF.RECORD, 'parameters': params, 'expected_versions': expected,
                'artifact_digests': [], 'nonce': command_id}, self.signer, self.sign, self.generation)
        finally:
            self.pending = None

    def _event(self, commit, previous, outcome, problems=(), widening=()):
        event = {'installation': self.repo.folder, 'commit': commit, 'previous': previous,
                 'outcome': outcome, 'problems': list(problems), 'widening': list(widening)}
        self.counts[outcome] = self.counts.get(outcome, 0) + 1
        for problem in problems:
            self.refusals[problem] = self.refusals.get(problem, 0) + 1
        self.observe(event)
        if outcome != 'accepted':
            self.notify(event)
        return event

    def reconcile(self, *, bootstrap=False, made=False):
        previous, commit = self.accepted_commit, None
        try:
            snapshot = self.repo.snapshot()
            commit = snapshot['commit']
            config, problems = self.validate(snapshot['files'])
            old_status = self.status()
            if old_status.get('outcome') == 'waiting' and old_status.get('commit') != commit and self.decisions:
                self.decisions.stale(old_status['proposal'])
            if problems:
                return self._event(commit, previous, 'refused', problems)
            if commit == previous:
                self.environment()
                return self._event(commit, previous, 'accepted')
            changes = V.widening(self.live, config)
            proposal = {'commit': commit, 'widening_digest': V.digest(changes), 'widening': changes}
            decision = self.decisions.approved(proposal) if self.decisions is not None and changes else None
            if changes and not bootstrap and decision is None:
                if self.decisions is not None:
                    self.decisions.request(proposal)
                status = {'outcome': 'waiting', 'commit': commit, 'proposal': proposal,
                          'made': made or (old_status.get('commit') == commit and old_status.get('made', False)),
                          'since': old_status.get('since', self.clock()) if old_status.get('commit') == commit else self.clock()}
                if status != old_status:
                    self._write({self.status_id: {'kind': WF.INSTALLATION_KIND, 'data': status}},
                                snapshot, previous, mode='waiting')
                return self._event(commit, previous, 'waiting', ['installation_waiting_approval:' + commit], changes)
            now = self.clock()
            writes = WF.installation_revisions(self.conn, self.domain, self.workflow_repository, snapshot,
                                               config, snapshot['author']['name'], now)
            bindings = self.bindings(config, writes)
            record = {key: snapshot[key] for key in ('commit', 'tree', 'author', 'committer')}
            record.update(configuration=config, previous=previous, accepted_at=now, bindings=bindings,
                          classification='import' if bootstrap else 'widening' if changes else 'non_widening',
                          widening=changes, widening_digest=proposal['widening_digest'], decision=decision)
            writes[self.identity] = {'kind': WF.INSTALLATION_KIND, 'data': record}
            history = self.identity + ':accepted:' + V.digest([commit, previous, now]).split(':')[1]
            writes[history] = {'kind': WF.INSTALLATION_KIND, 'data': record}
            writes[self.status_id] = {'kind': WF.INSTALLATION_KIND, 'data': {'outcome': 'accepted', 'commit': commit}}
            self._write(writes, snapshot, previous, mode='accepted', proposal=proposal, decision=decision)
            self.environment()
            event = self._event(commit, previous, 'accepted', widening=changes)
            if made or (old_status.get('commit') == commit and old_status.get('made')):
                try:
                    self.repo.send(commit, config['installation.yaml'].get('git', {}).get('remote'))
                except I.InstallationError as error:
                    event['push_refusal'] = error.code
                    self.notify(dict(event, outcome='push_failed', problems=[error.code]))
            return event
        except (I.InstallationError, Refused, self.store.StoreRefused) as error:
            return self._event(commit, previous, 'refused', getattr(error, 'codes', [error.code]))

    def environment(self):
        if os.environ.get(I.ENVIRONMENT) == self.repo.folder:
            os.environ['VELDO_INSTALLATION_COMMIT'] = self.accepted_commit
            os.environ['VELDO_INSTALLATION_BRANCH'] = self.repo.branch

    def bindings(self, config, writes):
        result = {}
        for path, project in sorted(config.items()):
            if not path.startswith('projects/'):
                continue
            resolved = {}
            for kind, binding in project.get('workflows', {}).items():
                workflow = binding['workflow']
                hid = WF.head_id(self.domain, self.workflow_repository, workflow)
                head = (writes.get(hid) or WF._entity_row(self.conn, hid) or {}).get('data', {})
                version = binding.get('version', head.get('version', 0))
                if version == 0 and workflow == 'code':
                    definition = organ('control_workflow_unit').shipped()
                    dd = WF.definition_digest(definition)
                elif version == head.get('version'):
                    dd = head['definition_digest']
                    definition = config.get('workflows/%s.json' % workflow)
                else:
                    _, revision = WF.verified_revision(self.store, self.conn, self.domain,
                                                       self.workflow_repository, workflow, version)
                    definition, dd = revision['definition'], revision['definition_digest']
                if definition is None or organ('control_workflow_unit').unit_problems(definition):
                    raise Refused('installation_invalid:%s:workflows.%s:not_unit_workflow' % (path, kind))
                resolved[kind] = {'workflow': workflow, 'version': version, 'digest': dd}
            result[Path(path).stem] = resolved
        return result

    def save(self, document, *, principal, base, command_id=None, base_commit=None, approval=None):
        return organ('control_installation_commit').save(self, document, principal=principal, base=base,
                    command_id=command_id, base_commit=base_commit, approval=approval)

    def metrics(self):
        record, status, now = self.record() or {}, self.status(), self.clock()
        return {'loads': dict(self.counts), 'refusals': dict(self.refusals), 'saves': dict(self.saves),
                'live_age': max(0, now - record.get('accepted_at', now)),
                'waiting': int(status.get('outcome') == 'waiting'),
                'waiting_age': max(0, now - status.get('since', now)) if status.get('outcome') == 'waiting' else 0}
