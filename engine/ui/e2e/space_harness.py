#!/usr/bin/env python3
"""The Space screen's harness (VELDO-0319): VELDO-0131's factory harness with the space ledger's records.

WHAT IT ADDS, on the same store connection and authority thread:

- THE SPACE LEDGER'S RECORDS, in the shapes control_space writes them (its docstring and its transitions:
  _new_item, _t_pool, _t_hold, _t_admit, _t_outcome, _t_group_join): two pools (a filesystem and an engine
  image kept on it), holds in every state (one waiting, one advised that the live run's dispatch contract
  carries, one admitted, one released), and items of three projects' tickets, of a plain repository and of no
  project, in every state: present, kept (one by the owner's Keep), due, deferred (in use by a process; unique
  work with a request of its own; three review worktrees of one review group with its one request), removed
  (a build folder, a worktree with its kept refs and snapshot, a volume in the engine pool with the host figure
  apart) and gone. They are written as store entities (upsert_entity, the harness's `fixture`): the Ledger's
  writers need real git repositories, real folders and a Docker engine that a browser test does not have. The
  API reads them through its real space reads, digests and member scope. These records are fixtures and certify
  the screen only, never the Ledger: suite 150_veldo_0319_space_screen reads records the real Ledger wrote.
- THE GROUP'S REQUEST as a real pending decision: the group record's alias is opened through the real inbox and
  presenter (the base harness's open_request), so the screen's link reaches a decision that can be answered.
  Its choices are the base harness's, not the space terms': the real request is published by
  control_space.publish_disposition, which suites 150_veldo_0340 and 150_veldo_0342 exercise.
- THE OWNER'S TWO COMMANDS. The real control_api_authority judges space.reconcile and space.abandon (the edge's
  signature, the session's member, the owner's role and the space scope) and then calls the service's entries.
  No authority service runs here, so two stand-ins take their place and write what the real ones would have the
  Ledger write: `reconcile` adopts one worktree and writes a reconcile record; `abandon` refuses a version that
  is not the item's and otherwise leaves the worktree removed, or deferred when it is the one with unique work,
  which it names under discard_required. The real entries are control_service.Service.space_reconcile and
  .space_abandon (suites 156_veldo_0315 and 149_veldo_0312).

With VELDO_SPACE_SEED=0 nothing of the space ledger is written, for the screen's empty state.

THE CONTROL PORT adds:
  /space/ids   {}   the identities the tests name: the items, holds, pools, the group and its request

Run: python3 -B engine/ui/e2e/space_harness.py --dist engine/ui/dist
"""
import hashlib
import os
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness as H  # noqa: E402
import factory_harness as F  # noqa: E402

HOST = 'veldo-linux-1'
GIB = 1024 ** 3
MIB = 1024 ** 2
ROOT = '/srv/veldo/worktrees'
LIFECYCLE = 7
ENDS = {'worktree': ['ticket_ended', 'project_ended', 'worktree_abandoned'],
        'build_output': ['run_finished', 'ticket_ended', 'project_ended'],
        'agent_repository': ['ticket_ended', 'project_ended'],
        'scratch': ['session_ended'], 'volume': ['run_finished', 'ticket_ended'],
        'evidence': ['project_ended'], 'review_run_scratch': ['verdict_recorded', 'ticket_ended', 'project_ended']}
GROUP_ALIAS = 'space-review-e2e-1'


def project(name):
    return {'type': 'project', 'id': name}


class SpaceUi(F.FactoryUi):
    def _build(self):
        super()._build()
        self.space_ids = {}
        self.authority.space_reconcile = self._reconcile
        self.authority.space_abandon = self._abandon
        if os.environ.get('VELDO_SPACE_SEED', '1') != '0':
            self._space_seed()
            self.deliver()

    def _item(self, name, kind, path, owner, state, size=None, pool='main', **more):
        identity = 'space:item:e2e-' + name
        locator = more.pop('locator', None) or {'path': path}
        data = {'kind': kind, 'host': HOST, 'pool': pool, 'locator': locator,
                'key': 'path:' + path if path else 'object:' + name, 'parent': more.pop('parent', None),
                'owner': owner, 'creator': more.pop('creator', 'seam'), 'adopted': more.pop('adopted', False),
                'branch': more.pop('branch', None), 'start': more.pop('start', None), 'form': None, 'process': None,
                'state': state, 'ends_on': {'version': LIFECYCLE, 'events': list(ENDS.get(kind, ['ticket_ended']))},
                'size': {'bytes': size[0], 'event': size[1]} if size else None, 'confirmed': None, 'deferral': None,
                'removal': None, 'report': None}
        data.update(more)
        self.fixture(identity, 'space_item', data)
        self.space_ids[name] = identity
        return identity

    def _space_seed(self):
        fixture = self.fixture
        pool = 'space:pool:%s:' % HOST
        fixture(pool + 'main', 'space_pool', {'name': 'main', 'host': HOST, 'type': 'filesystem', 'device': '259:2',
                                              'engine': None, 'floor': 20 * GIB, 'returns_space': True, 'backing': None})
        fixture(pool + 'desktop-engine', 'space_pool', {
            'name': 'desktop-engine', 'host': HOST, 'type': 'engine_image', 'device': None, 'engine': 'desktop-linux',
            'floor': 8 * GIB, 'returns_space': False, 'backing': 'main'})
        self.space_ids.update(pool_main=pool + 'main', pool_engine=pool + 'desktop-engine')

        def hold(name, state, need, reason=None, used=None, scope='project-a', source='declared'):
            identity = 'dispatch/' + hashlib.sha256(name.encode()).hexdigest()
            fixture('space:hold:' + identity, 'space_hold', {
                'scope': project(scope), 'needs': {'main': need}, 'source': {'main': source}, 'state': state,
                'reason': reason, 'used': used or {}, 'retry_asked': state == 'waiting', 'freed': False})
            self.space_ids['hold_' + name] = 'space:hold:' + identity
            return identity

        def reason(need, free, held):
            return {'pool': 'main', 'need': need, 'free': free, 'held': held, 'floor': 20 * GIB}
        hold('waiting', 'waiting', 12 * GIB, reason(12 * GIB, 41 * GIB + 300 * MIB, 14 * GIB), source='default')
        advised = hold('advised', 'advised', 6 * GIB, reason(6 * GIB, 38 * GIB, 14 * GIB), used={'main': 2 * GIB})
        hold('admitted', 'admitted', 10 * GIB)
        hold('released', 'released', 30 * GIB, scope='project-b')
        # The live run's dispatch carries the advised hold (control_dispatch: contract.space).
        live = self.recorders['live']
        live['data'] = dict(live['data'], contract=dict(live['data']['contract'],
                                                        space={'hold': advised, 'needs': {'main': 6 * GIB}}))
        fixture('dispatch:' + live['id'], 'dispatch', live['data'])

        def owner(name, ticket=None, run=None, station='build', **more):
            out = dict(scope=project(name), **more)
            if ticket:
                out['ticket'] = ticket
            if run:
                out['run'] = {'id': run, 'station': station}
            return out
        a = lambda ticket, run=None, station='build': owner('project-a', ticket, run, station)  # noqa: E731
        item = self._item
        tree = ROOT + '/project-a/'
        item('tree', 'worktree', tree + 'VELDO-9146', a('VELDO-9146', 'run-9146'), 'present', (3 * GIB + 200 * MIB, 'run_finished'),
             branch='veldo-9146', start='1a2b3c4' * 5 + 'cd')
        item('build', 'build_output', tree + 'VELDO-9146/build', a('VELDO-9146', 'run-9146'), 'present',
             (5 * GIB, 'run_finished'), parent='space:item:e2e-tree')
        item('agent', 'agent_repository', '/srv/veldo/agents/project-a/agent-VELDO-9146-run-9146', a('VELDO-9146', 'run-9146'),
             'present', (800 * MIB, 'run_finished'))
        item('unmeasured', 'build_output', tree + 'VELDO-9147/build', a('VELDO-9147', 'run-9147', 'review'), 'declared')
        item('kept', 'worktree', tree + 'VELDO-9144-kept-by-the-owner', a('VELDO-9144'), 'kept', (1 * GIB + 512 * MIB, 'ticket_ended'),
             branch='veldo-9144', owner_keep={'by': 'owner', 'at': time.time() - 86400, 'request': 'space-disposition-kept-1'})
        item('due', 'build_output', tree + 'VELDO-9145/build', a('VELDO-9145', 'run-9145'), 'due', (2 * GIB, 'run_finished'),
             due={'event': 'ticket_ended'})
        retry = ENDS['build_output']
        item('busy', 'build_output', tree + 'VELDO-9149/build-in-use', a('VELDO-9149', 'run-9149', 'review'), 'deferred',
             (4 * GIB + 100 * MIB, 'run_finished'), due={'event': 'run_finished'},
             deferral={'event': 'run_finished', 'emitter': {'process': 'receiver'}, 'action': 'remove', 'carrier': None,
                       'rule': 'in_use', 'refused_by': 'process_use', 'order': 4, 'retry': retry, 'attempts': 3,
                       'found': {'processes': [{'pid': 4412, 'command': 'vite', 'uses': ['cwd']}], 'containers': [],
                                 'git': {'read': True, 'files': [], 'worktree_locked': False},
                                 'unread': {'processes': [], 'table': None, 'engines': [], 'git': None, 'folders': None},
                                 'reader': {'state': 'used'}}})

        def unique(files):
            names = ['notes/file-%d.md' % n for n in range(files)]
            return {'cases': [1, 3], 'branch': None, 'commit': '6f1c2ab' * 5 + 'ab', 'modified': names[:1], 'staged': [],
                    'untracked': names[1:], 'operation': None, 'unlanded': None,
                    'more': {'modified': 0, 'staged': 0, 'untracked': 0}}

        def deferred_tree(name, path, who, files, disposition):
            return item(name, 'worktree', path, who, 'deferred', (600 * MIB, 'ticket_ended'), due={'event': 'ticket_ended'},
                        disposition=disposition, disposition_history=[],
                        deferral=dict({'event': 'ticket_ended', 'emitter': {'process': 'authority'}, 'action': 'remove',
                                       'carrier': None, 'rule': 'unique_work', 'refused_by': 'unique_work', 'order': 5,
                                       'retry': ENDS['worktree'], 'attempts': 1, 'found': unique(files),
                                       'decision_request': disposition['alias']},
                                      **({'review_group': disposition['group']} if disposition.get('group') else {})))
        solo_alias = 'space-disposition-' + hashlib.sha256(b'space:item:e2e-solo').hexdigest()[:32] + '-1'
        deferred_tree('solo', tree + 'VELDO-9149', a('VELDO-9149', 'run-9149', 'build'), 3,
                      {'number': 1, 'alias': solo_alias, 'proposal': {'worktrees': []}, 'head': None, 'state': 'requested'})
        gid = 'space:group:project:project-a:2026-11-16:1'
        members, entries = [], []
        long_tail = 'review-of-the-importer-with-a-very-long-worktree-folder-name-that-must-wrap-on-a-phone-and-never-push-the-page-wide'
        for index, (name, tail, files) in enumerate((('review1', 'review-9147-a', 2), ('review2', long_tail, 5),
                                                     ('review3', 'review-9147-c', 1)), 1):
            path = tree + 'reviews/' + tail
            entry = {'item': 'space:item:e2e-' + name, 'path': path, 'files': ['notes/file-%d.md' % n for n in range(files)],
                     'kept_branch': None}
            # A review worktree is added detached inside a review run and names no ticket (control_space.review_worktree).
            deferred_tree(name, path, owner('project-a', None, 'review-run-%d' % index, 'review'), files,
                          {'number': 1, 'alias': GROUP_ALIAS, 'group': gid, 'index': index,
                           'proposal': {'worktrees': [entry]}, 'head': None, 'state': 'requested'})
            entries.append(entry)
            members.append({'index': index, 'item': entry['item'], 'run': 'review-run-%d' % index, 'files': entry['files'],
                            'kept_branch': None, 'head': None, 'at': time.time() - 3600, 'entry': entry})
        rid = self.open_request(GROUP_ALIAS, brief='Three review worktrees of project-a hold work that is in no other '
                                                   'place. Save it, keep the worktrees, or discard?', risk='Medium')
        fixture(gid, 'space_review_group', {
            'schema': 'veldo.space_review_group/v1', 'scope': project('project-a'), 'day': '2026-11-16', 'sequence': 1,
            'members': members, 'state': 'open',
            'request': {'alias': GROUP_ALIAS, 'number': 1, 'version': 3, 'id': rid,
                        'proposal': {'group': gid, 'worktrees': entries, 'indexes': [1, 2, 3], 'picks': [1, 2]}}})
        self.space_ids.update(group=gid, request=rid, group_alias=GROUP_ALIAS, solo_alias=solo_alias)

        def removal(event, size, before, after, **more):
            return dict({'event': event, 'emitter': {'process': 'authority'}, 'action': 'remove', 'carrier': None,
                         'method': 'rmtree', 'bytes': size, 'bytes_source': 'measured', 'pool': 'main',
                         'pool_free_before': before, 'pool_free_after': after, 'freed': after - before, 'host': None}, **more)
        item('gone-build', 'build_output', tree + 'VELDO-9143/build', a('VELDO-9143', 'run-9143'), 'removed',
             (7 * GIB, 'run_finished'), removal=removal('run_finished', 7 * GIB, 30 * GIB, 37 * GIB))
        item('gone-tree', 'worktree', tree + 'VELDO-9143', a('VELDO-9143', 'run-9143'), 'removed', (2 * GIB, 'ticket_ended'),
             removal=removal('ticket_ended', 2 * GIB, 37 * GIB, 39 * GIB),
             kept={'repository': '/srv/veldo/projects/importer', 'path': tree + 'VELDO-9143',
                   'refs': {'refs/veldo/kept/VELDO-9143/e2e-gone-tree/1/head': '6f1c2ab' * 5 + 'ab',
                            'refs/veldo/kept/VELDO-9143/e2e-gone-tree/1/veldo-9143': '6f1c2ab' * 5 + 'ab'},
                   'snapshots': [{'path': '/srv/veldo/state/space-saved/e2e-gone-tree/1', 'number': 1, 'size': 4096,
                                  'manifest': 'sha256:' + hashlib.sha256(b'm').hexdigest()}],
                   'attempt': {'number': 1, 'head': '6f1c2ab' * 5 + 'ab'}})
        item('gone-volume', 'volume', None, a('VELDO-9143', 'run-9143'), 'removed', (3 * GIB, 'run_finished'),
             pool='desktop-engine', locator={'engine': 'desktop-linux', 'id': 'vol-9143', 'name': 'importer_pgdata_9143'},
             removal=removal('run_finished', 3 * GIB, 11 * GIB, 14 * GIB, method='docker volume rm', pool='desktop-engine',
                             host={'pool': 'main', 'freed': 0, 'free_before': 39 * GIB, 'free_after': 39 * GIB}))
        item('vanished', 'build_output', tree + 'VELDO-9142/build', a('VELDO-9142'), 'gone', (9 * GIB, 'run_finished'))
        # Another project, a plain repository and no project.
        item('b-tree', 'worktree', ROOT + '/project-b/VELDO-9148', owner('project-b', 'VELDO-9148', 'run-9148'), 'present',
             (1 * GIB, 'run_finished'), branch='veldo-9148')
        item('plain', 'worktree', '/home/owner/tools/worktrees/experiment',
             {'scope': {'type': 'plain_repository', 'id': '/home/owner/tools'}}, 'present', (350 * MIB, 'reconcile'),
             adopted=True, creator='reconcile', branch='experiment')
        item('scratch', 'scratch', '/srv/veldo/scratch/session-41', {'scope': {'type': 'no_project'}, 'session': 'session-41'},
             'present', (64 * MIB, 'session_started'))

    # The stand-ins of the service's two entries (the module docstring).

    def _row(self, identity):
        row = self.conn.execute('SELECT version, data FROM entities WHERE id=?', (identity,)).fetchone()
        return (row[0], H.json.loads(row[1])) if row else (0, None)

    def _reconcile(self, started_by, project=None):
        name = 'adopted-%d' % (len([k for k in self.space_ids if k.startswith('adopted-')]) + 1)
        self._item(name, 'worktree', '%s/%s/found-by-reconcile-%s' % (ROOT, project or 'project-a', name),
                   {'scope': {'type': 'project', 'id': project or 'project-a'}}, 'present', (128 * MIB, 'reconcile'),
                   adopted=True, creator='reconcile')
        counts = {'matched': 12, 'adopted': 1, 'reported': 0, 'gone': 0, 'completed': 0}
        self.fixture('space:reconcile:e2e-' + name, 'space_reconcile', {
            'started_by': started_by, 'roots': [ROOT], 'engines': ['desktop-linux'], 'counts': counts})
        return {'ok': True, 'counts': counts}

    def _abandon(self, item, version=None, by=None, cause=None):
        current, record = self._row(item)
        if record is None or record.get('kind') != 'worktree':
            return {'sent': False, 'reason': 'space_no_item'}
        if version != current:
            return {'sent': False, 'reason': 'space_item_version:' + item}
        record = dict(record, owner_keep=None, abandoned={'by': by, 'at': time.time(), 'ended_keep': record.get('owner_keep')})
        if item == self.space_ids.get('solo'):
            # Unique work: it stays, deferred, until the owner's Discard, which saves first.
            self.fixture(item, 'space_item', dict(record, state='deferred'))
            return {'sent': True, 'removed': [], 'deferred': [{'item': item, 'deferral': 'unique_work'}],
                    'discard_required': [item]}
        size = (record.get('size') or {}).get('bytes') or 0
        self.fixture(item, 'space_item', dict(
            record, state='removed',
            removal={'event': 'worktree_abandoned', 'emitter': {'by': by, 'cause': cause}, 'action': 'remove',
                     'carrier': None, 'method': 'git worktree remove', 'bytes': size, 'bytes_source': 'measured',
                     'pool': 'main', 'pool_free_before': 39 * GIB, 'pool_free_after': 39 * GIB + size, 'freed': size,
                     'host': None},
            kept={'repository': '/srv/veldo/projects/importer', 'path': record['locator']['path'],
                  'refs': {'refs/veldo/kept/abandoned/1/head': '6f1c2ab' * 5 + 'ab'}, 'snapshots': [],
                  'attempt': {'number': 1, 'head': '6f1c2ab' * 5 + 'ab'}}))
        return {'sent': True, 'removed': [{'item': item}], 'deferred': [], 'discard_required': []}


BASE_CONTROL = F.control_server


def control_server(factory, stop):
    server = BASE_CONTROL(factory, stop)
    handler = server.RequestHandlerClass
    route = handler.route

    def extended(self, path, body):
        if path == '/space/ids':
            return {'ids': dict(factory.space_ids)}
        return route(self, path, body)
    handler.route = extended
    return server


def main():
    H.Factory = SpaceUi
    H.control_server = control_server
    H.main()


if __name__ == '__main__':
    os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
    main()
