"""Replaceable graph execution adapter: plain versioned lifecycle data (VELDO-0043).

Domain code talks to a graph runtime ONLY through this module, and this module is standard
library only. It never imports the runtime. It launches the runtime's runner as a separate
process and exchanges one JSON request and one JSON response over stdin/stdout.

The runner receives no store handle or path: a fresh empty working directory, a fixed minimal
environment with no inherited variables, no inherited descriptors, and a request that carries
identities, versions and digests but no filesystem location. Its response is refused unless it
is exactly one of the plain versioned shapes below. Typed proposals are data for separately
authorized commands; this module holds no store and commits nothing.

The runtime is {'python': interpreter, 'runner': runner file}. Adapter.installed() resolves the
locked LangGraph runtime: the virtual environment at <account home>/.local/share/veldo/langgraph/
<lock digest>/ (control_graph_lock.py; the home comes from the password database, never $HOME)
and the sibling runner control_graph_langgraph.py, launched as a child of that interpreter. None,
or an interpreter that is not present, is the named refusal runtime_unavailable, whose detail
names the install command. Release 1 is nonpersistent, so a suspended cycle's resume data is
returned to the caller and never stored by the runtime.

The child's environment turns LangSmith tracing off by construction: the fixed ENVIRONMENT sets
every tracing switch langsmith reads to false, and nothing is inherited from the caller.
"""
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import tempfile

SCHEMA = 'veldo.graph/v1'
OPERATIONS = ('start', 'advance', 'suspend', 'cancel')
OUTCOMES = {
    'start': ('suspended', 'proposal', 'failure'),
    'advance': ('suspended', 'proposal', 'failure'),
    'suspend': ('suspended',),
    'cancel': ('canceled',),
}
# Every proposal is typed; a graph asserts nothing, it proposes to an authorized command.
PROPOSALS = {
    'admission': ('decision', 'subject'),
    'priority': ('priority', 'subject'),
    'completion': ('evidence', 'subject'),
}
FAILURES = ('invalid_input', 'missing_evidence', 'node_failed', 'unsupported_workflow')
IDENTITY = ('cycle_id', 'command_id', 'domain_uuid', 'repository_uuid')
REQUEST_FIELDS = {
    'start': ('snapshot', 'workflow'),
    'advance': ('resume', 'snapshot', 'supplied_results', 'workflow'),
    'suspend': ('resume', 'workflow'),
    'cancel': ('resume', 'workflow'),
}
RESPONSE_FIELDS = {
    'suspended': ('resume',),
    'proposal': ('proposals',),
    'failure': ('failure',),
    'canceled': (),
}
ENVIRONMENT = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8',
               'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1',
               'LANGSMITH_TRACING': 'false', 'LANGSMITH_TRACING_V2': 'false',
               'LANGCHAIN_TRACING': 'false', 'LANGCHAIN_TRACING_V2': 'false'}
HERE = Path(__file__).resolve().parent
INSTALL_COMMAND = 'python3 .veldo/control_graph_install.py'
RUNNER = 'control_graph_langgraph.py'


def resolve_runtime(home=None):
    """The locked runtime for this account, or None when it is not installed."""
    spec = importlib.util.spec_from_file_location('veldo_control_graph_lock', HERE / 'control_graph_lock.py')
    lock = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lock)
    runtime = {'python': str(lock.runtime_directory(home) / 'bin' / 'python'), 'runner': str(HERE / RUNNER)}
    return runtime if available(runtime) else None


class Refused(Exception):
    def __init__(self, code, detail):
        self.code, self.detail = code, detail
        super().__init__(code + ': ' + detail)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode()


def plain(value, where='value'):
    """Exact JSON types only. A subclass of dict, list or str is NOT plain data."""
    kind = type(value)
    if value is None or kind in (bool, int, str):
        return value
    if kind is float:
        if not math.isfinite(value):
            raise Refused('invalid_response', where + ': non-finite number')
        return value
    if kind is list:
        return [plain(item, where + '[]') for item in value]
    if kind is dict:
        for key in value:
            if type(key) is not str:
                raise Refused('invalid_response', where + ': non-string key')
        return {key: plain(item, where + '.' + key) for key, item in value.items()}
    raise Refused('invalid_response', where + ': ' + kind.__name__ + ' is not plain data')


def _exact(value, fields, where, code):
    if type(value) is not dict or set(value) != set(fields):
        raise Refused(code, where + ': fields must be exactly ' + ','.join(sorted(fields)))
    return value


def _identifier(value, where, code):
    if type(value) is not str or not value or len(value) > 200 or '/' in value or '\\' in value:
        raise Refused(code, where + ': invalid identifier')
    return value


def _versioned(value, where, code):
    _exact(value, ('id', 'version', 'digest'), where, code)
    _identifier(value['id'], where + '.id', code)
    if type(value['version']) is not int or value['version'] < 1:
        raise Refused(code, where + '.version must be a positive integer')
    if type(value['digest']) is not str or not value['digest'].startswith('sha256:'):
        raise Refused(code, where + '.digest must be sha256')
    return value


def request(operation, identity, **fields):
    """Build and validate one plain request. Snapshot and workflow are Veldo-accepted versions."""
    if operation not in OPERATIONS:
        raise Refused('invalid_input', 'unknown operation ' + repr(operation))
    body = dict(schema=SCHEMA, operation=operation, **identity, **fields)
    _exact(body, ('schema', 'operation') + IDENTITY + REQUEST_FIELDS[operation], 'request', 'invalid_input')
    for name in IDENTITY:
        _identifier(body[name], name, 'invalid_input')
    _versioned(body['workflow'], 'workflow', 'invalid_input')
    if 'snapshot' in body:
        _versioned(body['snapshot'], 'snapshot', 'invalid_input')
    if 'supplied_results' in body and type(body['supplied_results']) is not list:
        raise Refused('invalid_input', 'supplied_results must be a list')
    try:
        plain(body, 'request')
    except Refused as error:
        raise Refused('invalid_input', error.detail) from error
    return body


def response(sent, raw):
    """Parse the runner's bytes into one accepted plain response, or refuse by name."""
    try:
        value = json.loads(raw, parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
    except ValueError as error:
        raise Refused('invalid_response', 'not one JSON document') from error
    plain(value, 'response')
    if type(value) is not dict:
        raise Refused('invalid_response', 'response must be an object')
    outcome = value.get('outcome')
    if outcome not in OUTCOMES[sent['operation']]:
        raise Refused('invalid_response', 'outcome ' + repr(outcome) + ' is not allowed for ' + sent['operation'])
    _exact(value, ('schema', 'operation', 'outcome', 'runtime') + IDENTITY + RESPONSE_FIELDS[outcome],
           'response', 'invalid_response')
    if value['schema'] != SCHEMA or value['operation'] != sent['operation']:
        raise Refused('invalid_response', 'schema or operation mismatch')
    for name in IDENTITY:
        if value[name] != sent[name]:
            raise Refused('invalid_response', name + ' does not echo the request')
    runtime = _exact(value['runtime'], ('name', 'version'), 'runtime', 'invalid_response')
    if type(runtime['name']) is not str or type(runtime['version']) is not str:
        raise Refused('invalid_response', 'runtime identity must be text')
    if outcome == 'proposal':
        proposals = value['proposals']
        if type(proposals) is not list or not proposals:
            raise Refused('invalid_response', 'a proposal outcome carries at least one proposal')
        seen = set()
        for index, item in enumerate(proposals):
            where = 'proposals[' + str(index) + ']'
            kind = item.get('type') if type(item) is dict else None
            if kind not in PROPOSALS:
                raise Refused('invalid_response', where + ': untyped proposal')
            _exact(item, ('type', 'proposal_id') + PROPOSALS[kind], where, 'invalid_response')
            _identifier(item['proposal_id'], where + '.proposal_id', 'invalid_response')
            _identifier(item['subject'], where + '.subject', 'invalid_response')
            if not _proposal_values(item):
                raise Refused('invalid_response', where + ': ' + kind + ' value has the wrong type')
            if item['proposal_id'] in seen:
                raise Refused('invalid_response', where + ': duplicate proposal_id')
            seen.add(item['proposal_id'])
    if outcome == 'suspended' and type(value['resume']) is not dict:
        raise Refused('invalid_response', 'resume must be an object')
    if outcome == 'failure':
        failure = _exact(value['failure'], ('code', 'detail'), 'failure', 'invalid_response')
        if failure['code'] not in FAILURES or type(failure['detail']) is not str:
            raise Refused('invalid_response', 'failure must carry a named code')
    return value


def _proposal_values(item):
    if item['type'] == 'priority':
        return type(item['priority']) is int and item['priority'] >= 0
    if item['type'] == 'admission':
        return item['decision'] in ('admit', 'decline')
    return (type(item['evidence']) is list and bool(item['evidence'])
            and all(type(ref) is str and ref.startswith('sha256:') for ref in item['evidence']))


def available(runtime):
    return (type(runtime) is dict and set(runtime) == {'python', 'runner'}
            and all(type(runtime[key]) is str and Path(runtime[key]).is_file() for key in runtime))


def exchange(runtime, sent, timeout=120):
    """One request, one response, one child process with nothing inherited."""
    if not available(runtime):
        raise Refused('runtime_unavailable', 'no graph runtime is installed for this operation; install it with: '
                      + INSTALL_COMMAND)
    with tempfile.TemporaryDirectory(prefix='veldo-graph-') as empty:
        try:
            proc = subprocess.run([runtime['python'], '-I', '-B', runtime['runner']],
                                  input=canonical(sent), capture_output=True, cwd=empty,
                                  env=dict(ENVIRONMENT), close_fds=True, timeout=timeout)
        except subprocess.TimeoutExpired as error:
            raise Refused('unknown_outcome', 'graph runtime did not answer within its deadline') from error
        except OSError as error:
            raise Refused('runtime_unavailable', 'graph runtime could not be launched') from error
    if proc.returncode:
        raise Refused('unknown_outcome', 'graph runtime exited ' + str(proc.returncode) + ' without an answer')
    return response(sent, proc.stdout)


class Adapter:
    """Lifecycle operations over one domain and repository, with counts and observations."""

    @classmethod
    def installed(cls, domain_uuid, repository_uuid, home=None, timeout=120):
        """An adapter over the locked runtime this account has installed (None if absent)."""
        return cls(resolve_runtime(home), domain_uuid, repository_uuid, timeout)

    def __init__(self, runtime, domain_uuid, repository_uuid, timeout=120):
        self.runtime, self.timeout = runtime, timeout
        self.domain_uuid, self.repository_uuid = domain_uuid, repository_uuid
        self.counts = {'accepted': 0, 'refused': 0}
        self.observations = []
        self._last = {}

    def _call(self, operation, cycle_id, command_id, **fields):
        identity = dict(cycle_id=cycle_id, command_id=command_id,
                        domain_uuid=self.domain_uuid, repository_uuid=self.repository_uuid)
        record = dict(operation=operation, **identity,
                      accepted_inputs={name: {k: fields[name][k] for k in ('id', 'version', 'digest')}
                                       for name in ('snapshot', 'workflow') if type(fields.get(name)) is dict
                                       and {'id', 'version', 'digest'} <= set(fields[name])})
        try:
            result = exchange(self.runtime, request(operation, identity, **fields), self.timeout)
        except Refused as error:
            self.counts['refused'] += 1
            self.observations.append(dict(record, outcome='refused', refusal=error.code))
            raise
        self.counts['accepted'] += 1
        self._last[cycle_id] = result['outcome']
        self.observations.append(dict(record, outcome=result['outcome'], refusal=None,
                                      runtime=result['runtime']))
        return result

    def start(self, cycle_id, command_id, snapshot, workflow):
        return self._call('start', cycle_id, command_id, snapshot=snapshot, workflow=workflow)

    def advance(self, cycle_id, command_id, snapshot, workflow, resume, supplied_results):
        return self._call('advance', cycle_id, command_id, snapshot=snapshot, workflow=workflow,
                          resume=resume, supplied_results=supplied_results)

    def suspend(self, cycle_id, command_id, workflow, resume):
        return self._call('suspend', cycle_id, command_id, workflow=workflow, resume=resume)

    def cancel(self, cycle_id, command_id, workflow, resume):
        return self._call('cancel', cycle_id, command_id, workflow=workflow, resume=resume)

    def pending(self):
        """Cycles whose last accepted outcome leaves work outstanding."""
        return sorted(cycle for cycle, outcome in self._last.items() if outcome == 'suspended')
