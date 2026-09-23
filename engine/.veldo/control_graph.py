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
import re
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
# Adapter refusals by name, beyond the runner's failure codes.
REFUSALS = ('invalid_input', 'path_in_request', 'invalid_response', 'missing_evidence',
            'runtime_unavailable', 'unknown_outcome')
DIGEST = re.compile(r'sha256:[0-9a-f]{64}\Z')
RESUME_FIELDS = ('position', 'step', 'notes')
RESULT_FIELDS = ('id', 'version', 'digest', 'value')
MAX_NOTES = 1 << 16
_URL = re.compile(r'https?://[^\s"\'<>]*')
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
# Bounds checked before parsing or walking, without recursion: an answer or request nested deeper
# than MAX_DEPTH, or an answer larger than MAX_ANSWER_BYTES, is a named refusal.
MAX_DEPTH = 32
MAX_ANSWER_BYTES = 1 << 20
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


def text_depth(raw, limit=MAX_DEPTH):
    """Deepest array/object nesting of JSON text, scanned iteratively; stops once past `limit`."""
    depth = deepest = 0
    in_string = escaped = False
    for byte in raw:
        if in_string:
            if escaped:
                escaped = False
            elif byte == 0x5c:
                escaped = True
            elif byte == 0x22:
                in_string = False
        elif byte == 0x22:
            in_string = True
        elif byte in (0x5b, 0x7b):
            depth += 1
            if depth > deepest:
                deepest = depth
                if deepest > limit:
                    return deepest
        elif byte in (0x5d, 0x7d):
            depth -= 1
    return deepest


def value_depth(value, limit=MAX_DEPTH):
    """Deepest list/dict nesting of a Python value, walked with an explicit stack."""
    deepest, stack = 0, [(value, 1)]
    while stack:
        item, depth = stack.pop()
        if type(item) in (list, dict):
            if depth > deepest:
                deepest = depth
                if deepest > limit:
                    return deepest
            stack.extend((child, depth + 1) for child in (item.values() if type(item) is dict else item))
    return deepest


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


def _digest(value, where, code):
    if type(value) is not str or not DIGEST.match(value):
        raise Refused(code, where + ' must be sha256:<64 lowercase hex>')
    return value


def _versioned(value, where, code, fields=('id', 'version', 'digest')):
    _exact(value, fields, where, code)
    _identifier(value['id'], where + '.id', code)
    if type(value['version']) is not int or value['version'] < 1:
        raise Refused(code, where + '.version must be a positive integer')
    _digest(value['digest'], where + '.digest', code)
    return value


def _resume_shape(value, where, code):
    """A resume is closed: a node position, a step count and the graph's notes as text."""
    _exact(value, RESUME_FIELDS, where, code)
    _identifier(value['position'], where + '.position', code)
    if type(value['step']) is not int or value['step'] < 0:
        raise Refused(code, where + '.step must be a non-negative integer')
    if type(value['notes']) is not str or len(value['notes']) > MAX_NOTES:
        raise Refused(code, where + '.notes must be text of at most ' + str(MAX_NOTES) + ' characters')
    return value


def looks_like_path(text):
    """A filesystem location: after http(s) URLs are removed, any / or \\ or a leading ~."""
    rest = _URL.sub('', text)
    return '/' in rest or '\\' in rest or rest.lstrip().startswith('~')


def _strings(value):
    """Every string in a plain value, keys included, walked with an explicit stack."""
    stack = [value]
    while stack:
        item = stack.pop()
        if type(item) is str:
            yield item
        elif type(item) is dict:
            stack.extend(item.keys())
            stack.extend(item.values())
        elif type(item) is list:
            stack.extend(item)


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
    if 'supplied_results' in body:
        if type(body['supplied_results']) is not list:
            raise Refused('invalid_input', 'supplied_results must be a list')
        for index, item in enumerate(body['supplied_results']):
            _versioned(item, 'supplied_results[' + str(index) + ']', 'invalid_input', RESULT_FIELDS)
    if 'resume' in body:
        _resume_shape(body['resume'], 'resume', 'invalid_input')
    if value_depth(body) > MAX_DEPTH:
        raise Refused('invalid_input', 'request nests deeper than ' + str(MAX_DEPTH))
    try:
        plain(body, 'request')
    except Refused as error:
        raise Refused('invalid_input', error.detail) from error
    for text in _strings({key: value for key, value in body.items() if key != 'schema'}):
        if looks_like_path(text):
            raise Refused('path_in_request', 'a request carries no filesystem location: ' + repr(text[:80]))
    return body


def response(sent, raw):
    """Parse the runner's bytes into one accepted plain response, or refuse by name."""
    raw = raw.encode() if type(raw) is str else bytes(raw)
    if len(raw) > MAX_ANSWER_BYTES:
        raise Refused('invalid_response', 'answer is larger than ' + str(MAX_ANSWER_BYTES) + ' bytes')
    if text_depth(raw) > MAX_DEPTH:
        raise Refused('invalid_response', 'answer nests deeper than ' + str(MAX_DEPTH))
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
            and all(type(ref) is str and DIGEST.match(ref) for ref in item['evidence']))


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
