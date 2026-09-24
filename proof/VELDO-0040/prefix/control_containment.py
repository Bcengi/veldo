"""Stand-in for control_containment.py at f5aebae, where no such module exists (red.py only).

At f5aebae the receiver consults no worker profile: it launches every local worker directly, in the
receiver's own cgroup, refuses no profile and states no mechanism. This file puts that absence behind
the names suite 63 reads from the module: the declared settings schema (the specification's list, so
the suite enumerates the same set), the dispatch's unit name (so the suite looks for a group that is
never made), a qualification that refuses nothing and states nothing, and a status with no groups.
The pre-change control_launch.py never loads it.
"""
import hashlib

SETTINGS = {
    'concurrency': dict(required=True, kind='count'),
    'runtime_seconds': dict(required=True, kind='seconds'),
    'memory_bytes': dict(required=True, kind='bytes'),
    'cpu_percent': dict(required=True, kind='percent'),
    'file_bytes': dict(required=True, kind='bytes'),
    'tasks_max': dict(required=False, kind='count'),
    'stop_grace_seconds': dict(required=False, kind='seconds', default=10),
    'kill_grace_seconds': dict(required=False, kind='seconds', default=5),
}


def unit_name(dispatch_id):
    return 'veldo-dispatch-' + hashlib.sha256(str(dispatch_id).encode()).hexdigest()[:32] + '.scope'


def qualify(profile, environment=None):
    return {'qualified': True, 'refusal': None, 'problems': [], 'settings': {}, 'unbounded': {}, 'host': {},
            'identity': {}}


def status(profile, environment=None):
    return {'qualified': True, 'refusal': None, 'groups': []}
