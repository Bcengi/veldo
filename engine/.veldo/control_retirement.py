#!/usr/bin/env python3
"""Retirement of a dispatch's worker slot: it follows the actual end of the worker and its whole
group, keeps each obligation that is still open, and releases the VELDO-0036 capacity slot exactly
once (PLAN-0019 W26, VELDO-0041, R44).

THE OBLIGATIONS, each read at every attempt from its own source, never from a report:

- termination: the worker's recorded process is gone (/proc, with its boot id and start time).
- group: the containment group the VELDO-0039 receiver reported has no process left (its
  cgroup.events), so no descendant is alive (control_containment.retirement, VELDO-0040).
- outcome: the dispatch record has a known end. `exited` and `refused` are the receiver's recorded
  ends; a record still `prepared` (or none) never had a worker, and VELDO-0036's own acceptance check
  refuses to launch it once its slot is retired. An `accepted` or `running` record has no recorded
  end, and an `unknown` one has an outcome this Release cannot establish (recovery is Release 2): the
  slot stays held with the obligation open.
- clone files: when the runner provisions worker clones (VELDO-0042, control_clone.Clones), the
  clone the dispatch uses is removed through that provisioner's own teardown, which deletes its files
  and releases its pins only once every user of the clone has ended. The receiver's group is recorded
  on the clone's user first, so the teardown reads that user's ending from the kernel too. Teardown
  is attempted only once termination, group and outcome are complete.
- accounting: every model call reserved under the dispatch has its final report. VELDO-0036's
  `retire` transition judges this itself (missing_accounting). A final report that left usage units
  unknown settles the call as unknown there; this retirement RETAINS those units in its record
  (`retained`), never reports them as known.

ONE GATE AND ONE RELEASE. The release is VELDO-0036's `retire` transition of the dispatch's own
worker slot under one command identity per dispatch (`retire/<dispatch id>`); the observation it
records is taken INSIDE that transaction by `lifecycle`, which refuses a still open outcome or clone
by name, and the transition itself refuses a live worker (worker_alive), a populated group
(cleanup_incomplete) and missing accounting. The first open obligation in ORDER names the refusal.
A slot already retired is refused `already_retired` before anything is submitted, and the store
refuses a second commit under the same command identity, so no retry, runner or race releases a slot
twice.

KEPT. A refused attempt leaves the dispatch in `pending()` with each open obligation named and the
group the receiver reported (a later attempt observes the same group, never "no group"); `retire`
is called again once an obligation is completed.

OBSERVABILITY. Each attempt appends one event to `observations`: operation, domain, repository, unit,
dispatch, request, accepted slot version, outcome, named refusal and its taxonomy, the obligations
still open and what the kernel said of the group. `status()` counts accepted and refused attempts and
lists the pending ones.

WHAT IT IS NOT. What it tracks is in memory: retirement that survives the runner's crash, recovery of
an unknown outcome and leadership fencing are Release 2. Standard library only.
"""
import importlib.util
import json
from pathlib import Path
import time


def _organ(name):
    spec = importlib.util.spec_from_file_location('retirement_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


C = _organ('control_containment')
RES = _organ('control_reservations')

SCHEMA = 'veldo.retirement/v1'
OBSERVER = 'launch_runner'
# The obligations in the order they are judged: the first one still open names the refusal.
ORDER = ('termination', 'group', 'outcome', 'clone', 'accounting')
REFUSALS = {'termination': 'worker_alive', 'group': 'cleanup_incomplete', 'outcome': 'outcome_unknown',
            'clone': 'cleanup_incomplete:clone', 'accounting': 'missing_accounting'}
# Dispatch states with a known end: never launched (prepared) or ended as the receiver recorded it.
CONCLUSIVE = ('prepared', 'exited', 'refused')
TAXONOMY = {'worker_alive': 'stale_subject', 'cleanup_incomplete': 'stale_subject', 'already_retired': 'stale_subject',
            'stale_version': 'stale_subject', 'outcome_unknown': 'unknown_outcome', 'missing_accounting': 'missing_evidence',
            'missing_worker': 'invalid_input', 'missing_outcome': 'invalid_input', 'invalid_input': 'invalid_input',
            'command_content_conflict': 'invalid_input', 'missing_authority': 'missing_authority'}


def taxonomy(code):
    """The error class of a retirement refusal; a code with no class is an unknown outcome, never success."""
    return TAXONOMY.get(str(code).split(':', 1)[0], 'unknown_outcome')


def _members(group):
    """Every process the kernel lists anywhere in a group's subtree, for the record."""
    cgroup = group.get('cgroup') if isinstance(group, dict) else None
    found = []
    if cgroup:
        for procs in sorted((C.CGROUP / cgroup.lstrip('/')).rglob('cgroup.procs')):
            try:
                found += [int(pid) for pid in procs.read_text().split()]
            except (OSError, ValueError):
                continue
    return sorted(found)


class Retirements:
    """The runner's retirement of worker slots. `reservations` is VELDO-0036's service, `dispatches` the
    runner's control_dispatch.Dispatches, `clones` VELDO-0042's clone provisioner when dispatches use
    clones, and `observations` the list each attempt's event is appended to."""

    def __init__(self, reservations, dispatches, *, clones=None, clock=None, observations=None):
        self.reservations, self.dispatches, self.clones = reservations, dispatches, clones
        self.store = reservations.store
        self.clock = clock or time.time
        self.observations = observations if observations is not None else []
        self.entries = {}
        self.counts = {'accepted': 0, 'refused': 0}

    def _entry(self, dispatch_id):
        return self.entries.setdefault(dispatch_id, {'group': None, 'stop_requested': False, 'supervision': None,
                                                     'clone': None, 'attempts': 0, 'released': 0, 'open': [],
                                                     'refusal': None, 'observed': None})

    def track(self, dispatch_id, *, group=None, stop_requested=False, supervision=None):
        """What the runner knows of a dispatch it will retire: the group the receiver reported, whether it
        asked for a stop and the receiver's supervision. A later call never erases a reported group."""
        entry = self._entry(dispatch_id)
        if isinstance(group, dict) and (group.get('cgroup') or not entry['group']):
            entry['group'] = dict(group)
        entry['stop_requested'] = entry['stop_requested'] or bool(stop_requested)
        if supervision is not None:
            entry['supervision'] = supervision
        return entry

    def _slot(self, dispatch_id):
        entity = RES.entity('worker', [self.reservations.domain, dispatch_id])
        row = self.reservations.conn.execute('SELECT version, data FROM entities WHERE id=?', (entity,)).fetchone()
        return entity, (row[0] if row else 0), (json.loads(row[1]) if row else None)

    def _clone(self, dispatch_id, entry):
        """The clone this dispatch uses, remembered once found, and whether its files are still there."""
        if self.clones is None:
            return None
        if entry['clone'] is None:
            handle = self.clones.clone_of(dispatch_id)
            if handle is None:
                return None
            entry['clone'] = {'handle': handle, 'clone_id': handle.env_id, 'root': handle.paths.get('root'),
                              'teardown': None, 'refusal': None}
        clone = entry['clone']
        # The provisioner's own liveness surface (env_provision): its root on disk or a pin still held.
        return {'clone_id': clone['clone_id'], 'root': clone['root'], 'present': bool(self.clones._is_live(clone['handle'])),
                'teardown': clone['teardown'], 'refusal': clone['refusal']}

    def _calls(self, dispatch_id):
        return [r for r in self.reservations._records().values() if r.get('type') == 'invocation'
                and r['context']['domain'] == self.reservations.domain and r['dispatch'] == dispatch_id]

    def _observe(self, dispatch_id, entry):
        """Every obligation of one dispatch, read now from its own source."""
        record = self.dispatches.record(dispatch_id) or {}
        kernel = C.retirement(entry['group'], record.get('process'))
        state = record.get('state')
        clone = self._clone(dispatch_id, entry)
        calls = self._calls(dispatch_id)
        pending = sorted(r['invocation'] for r in calls if r['state'] not in ('settled', 'unknown'))
        obligations = {
            'termination': {'open': not kernel['terminated'], 'process': record.get('process')},
            'group': {'open': not kernel['cleaned'], 'group': kernel['group'], 'members': _members(entry['group'])},
            'outcome': {'open': state is not None and state not in CONCLUSIVE, 'state': state},
            'clone': dict(clone, open=clone['present']) if clone else {'open': False, 'clone_id': None},
            'accounting': {'open': bool(pending), 'pending': pending, 'calls': len(calls)},
        }
        retained = {'accounting_unknown': {r['invocation']: sorted(r['unknown']) for r in calls if r['unknown']}}
        return {'kernel': kernel, 'obligations': obligations, 'retained': retained,
                'open': [name for name in ORDER if obligations[name]['open']]}

    def _complete_clone(self, dispatch_id, entry, seen):
        """Remove the clone through its provisioner once the dispatch has ended; a refusal keeps it."""
        obligations = seen['obligations']
        if not obligations['clone']['open'] or any(obligations[n]['open'] for n in ('termination', 'group', 'outcome')):
            return
        clone = entry['clone']
        try:
            if isinstance(entry['group'], dict) and entry['group'].get('cgroup'):
                self.clones.record_group(dispatch_id, {k: entry['group'].get(k) for k in ('unit', 'slice', 'cgroup')})
            self.clones.retire(clone['handle'])
            clone['teardown'], clone['refusal'] = 'retired', None
        except Exception as error:  # noqa: BLE001 - a refused teardown keeps the clone and the slot
            clone['teardown'], clone['refusal'] = 'refused', getattr(error, 'code', None) or type(error).__name__

    def retire(self, dispatch_id, outcome, basis):
        """Try to release the dispatch's worker slot now. True once released; False keeps it, with the
        open obligations named in `pending()`."""
        entry = self._entry(dispatch_id)
        entry['attempts'] += 1
        if outcome in ('completed', 'failed') and entry['stop_requested']:
            outcome = 'cancelled'  # the runner asked for the stop
        entity, version, slot = self._slot(dispatch_id)
        record = self.dispatches.record(dispatch_id) or {}
        request = 'retire/' + dispatch_id
        event = {'schema': SCHEMA, 'operation': 'retire', 'domain': self.reservations.domain,
                 'repository': self.reservations.repository, 'dispatch_id': dispatch_id, 'request': request,
                 'unit': ((record.get('contract') or {}).get('unit') or ((slot or {}).get('context') or {}).get('unit')),
                 'accepted_versions': {entity: version}, 'basis': basis, 'attempt': entry['attempts']}
        entry['observed'] = None
        if slot is not None and slot.get('retired'):
            return self._refused(entry, event, 'already_retired')
        entry['observed'] = self._observe(dispatch_id, entry)
        self._complete_clone(dispatch_id, entry, entry['observed'])

        def lifecycle(_dispatch):
            # Inside VELDO-0036's retire transaction: the observation that transaction records.
            seen = self._observe(dispatch_id, entry)
            entry['observed'] = seen
            first = seen['open'][0] if seen['open'] else None
            if first in ('outcome', 'clone'):
                raise self.store.StoreRefused(REFUSALS[first], 'the %s obligation is still open' % first)
            return dict(seen['kernel'], outcome=outcome, observer=OBSERVER, basis=basis, supervision=entry['supervision'],
                        obligations=seen['obligations'], retained=seen['retained'])
        try:
            self.reservations.retire(request, dispatch_id, lifecycle, now=self.clock())
        except Exception as error:  # noqa: BLE001 - a refused retirement keeps the slot held
            return self._refused(entry, event, getattr(error, 'code', None) or type(error).__name__)
        seen = entry['observed']
        entry.update(released=entry['released'] + 1, open=[], refusal=None)
        self.counts['accepted'] += 1
        self.observations.append(dict(event, outcome='retired', open=[], retained=seen['retained'],
                                      observed=seen['kernel']['group'].get('observed'), clone=self._clone_event(entry)))
        return True

    @staticmethod
    def _clone_event(entry):
        clone = entry['clone']
        return {k: clone[k] for k in ('clone_id', 'teardown', 'refusal')} if clone else None

    def _refused(self, entry, event, code):
        seen = entry['observed']
        entry.update(open=list(seen['open']) if seen else [], refusal=code)
        self.counts['refused'] += 1
        self.observations.append(dict(event, outcome='refused', refusal=code, taxonomy=taxonomy(code),
                                      open=list(entry['open']), clone=self._clone_event(entry),
                                      observed=seen['kernel']['group'].get('observed') if seen else None))
        return False

    def pending(self):
        """Every tracked dispatch whose slot is still held, with its open obligations and last refusal."""
        held = {}
        for dispatch_id, entry in sorted(self.entries.items()):
            slot = self._slot(dispatch_id)[2]
            if slot is not None and not slot.get('retired'):
                held[dispatch_id] = {'open': list(entry['open']), 'refusal': entry['refusal'], 'attempts': entry['attempts']}
        return held

    def status(self):
        return dict(self.counts, pending=self.pending())
