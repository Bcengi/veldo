"""Replaceable graph execution adapter: plain versioned lifecycle data (VELDO-0043).

Domain code talks to a graph runtime ONLY through this module, and this module is standard
library only. It never imports the runtime. It launches the runtime's runner as a separate
process and exchanges one JSON request and one JSON response over stdin/stdout.

The runner receives no store handle or path: a fresh empty working directory, a fixed minimal
environment with no inherited variables, no inherited descriptors, and a request that carries
identities, versions and digests but no filesystem location. Its response is refused unless it
is exactly one of the plain versioned shapes below. Typed proposals are data for separately
authorized commands; this module holds no store and commits nothing.

The runtime is {'python': interpreter, 'runner': runner source file, 'stage': directory}.
Adapter.installed() resolves the locked LangGraph runtime: the virtual environment at
<account home>/.local/share/veldo/langgraph/<lock digest>/ (control_graph_lock.py; the home comes
from the password database, never $HOME), the sibling runner source control_graph_langgraph.py,
and the per-account stage <account home>/.local/state/veldo/graph-stage/, separate from the
runtime. Before each launch the runner is copied, content-addressed, to <stage>/runners/<sha256>.py
and run from there in a fresh working directory under <stage>/work/, so the child's argv[0],
__file__, script directory, working directory and any Git discovery from them lead to no
repository and no store. The adapter follows no link it did not make: a link at runners/, work/
or the staged runner, a stage inside a Git repository, or a working directory that does not
resolve outside every repository immediately before launch, is refused as runtime_unavailable. What the adapter hands the child leads nowhere; a hostile node reading its parent
through /proc as the same account is a stated limit, confined in Release 2. None,
or an interpreter that is not present, is the named refusal runtime_unavailable, whose detail
names the install command. Release 1 is nonpersistent, so a suspended cycle's resume data is
returned to the caller and never stored by the runtime.

The child's environment turns LangSmith tracing off by construction: the fixed ENVIRONMENT sets
every tracing switch langsmith reads to false, and nothing is inherited from the caller.
"""
import hashlib
import importlib.util
import json
import os
import math
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
import time
import unicodedata
import urllib.parse

SCHEMA = 'veldo.graph/v1'
OPERATIONS = ('start', 'advance', 'suspend', 'cancel')
OUTCOMES = {
    'start': ('suspended', 'proposal', 'failure'),
    'advance': ('suspended', 'proposal', 'failure'),
    'suspend': ('suspended', 'failure'),
    'cancel': ('canceled', 'failure'),
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
MAX_REQUEST_BYTES = 1 << 20
# Every character that renders as a path separator, besides the two ASCII ones.
SEPARATORS = ('/', '\\', '\u2044', '\u2215', '\u2216', '\u29f5', '\u29f8', '\u29f9', '\ufe68',
              '\uff0f', '\uff3c')
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
# Staged runner copies and child working directories: per account, separate from the runtime,
# which holds only what the lock installed.
STAGE_RELATIVE = Path('.local/state/veldo/graph-stage')


NO_RUNTIME = {'name': 'none', 'version': ''}


def _lock():
    spec = importlib.util.spec_from_file_location('veldo_control_graph_lock', HERE / 'control_graph_lock.py')
    lock = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lock)
    return lock


def runtime_evidence():
    """The runtime label an answer must carry to count as evidence from the locked LangGraph."""
    return {'name': 'langgraph', 'version': dict((name, version) for name, version, _, _ in _lock().PACKAGES)['langgraph']}


def evidenced(result, evidence):
    """An answer is runtime evidence when the locked LangGraph produced it. A failure may instead
    say that nothing ran (NO_RUNTIME); a failure confers nothing."""
    if result['outcome'] == 'failure':
        return result['runtime'] in (evidence, NO_RUNTIME)
    return result['runtime'] == evidence


def resolve_runtime(home=None):
    """The locked runtime for this account, or None when it is not installed."""
    lock = _lock()
    directory = lock.runtime_directory(home)
    runtime = {'python': str(directory / 'bin' / 'python'), 'runner': str(HERE / RUNNER),
               'stage': str(lock.account_home() / STAGE_RELATIVE if home is None else Path(home) / STAGE_RELATIVE)}
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
    if (type(value) is not str or not value or len(value) > 200 or '/' in value or '\\' in value
            or '..' in value or any(ord(char) < 32 or ord(char) == 127 for char in value)):
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
    """A filesystem location in any form: a path separator (ASCII, look-alike or compatibility
    form), a percent-encoded one, or a leading ~. No URL exemption here."""
    folded = unicodedata.normalize('NFKC', text).lower()
    return (any(separator in folded for separator in SEPARATORS) or '%2f' in folded or '%5c' in folded
            or folded.lstrip().startswith('~'))


def is_url(text):
    """An http(s) URL with a non-empty host and no whitespace or control characters."""
    if any(char.isspace() or ord(char) < 32 for char in text):
        return False
    try:
        parts = urllib.parse.urlsplit(text)
        return parts.scheme in ('http', 'https') and bool(parts.hostname)
    except ValueError:
        return False


def url_field(key):
    """A declared URL field: a key named url or ending in _url."""
    return type(key) is str and (key == 'url' or key.endswith('_url'))


def value_bounds(value, depth_limit=MAX_DEPTH, size_limit=MAX_REQUEST_BYTES):
    """(deepest nesting, approximate JSON bytes) of a Python value, walked with an explicit stack;
    stops as soon as either passes its limit, so a huge or self-referential value costs little."""
    deepest, size, stack = 0, 0, [(value, 1)]
    while stack:
        item, depth = stack.pop()
        kind = type(item)
        if kind is str:
            size += (len(item) if len(item) > size_limit else len(item.encode('utf-8', 'surrogatepass'))) + 2
        elif kind is list or kind is dict:
            deepest = max(deepest, depth)
            if deepest > depth_limit:
                return deepest, size
            size += 2 + len(item)
            if kind is dict:
                for key, child in item.items():
                    size += len(key) + 3 if type(key) is str else 8
                    stack.append((child, depth + 1))
            else:
                stack.extend((child, depth + 1) for child in item)
        else:
            size += 8
        if size > size_limit:
            return deepest, size
    return deepest, size


def _strings(value):
    """(string, declared URL field) for every string in a plain value, keys included, walked with
    an explicit stack."""
    stack = [(value, False)]
    while stack:
        item, declared = stack.pop()
        if type(item) is str:
            yield item, declared
        elif type(item) is dict:
            stack.extend((key, False) for key in item)
            stack.extend((child, url_field(key)) for key, child in item.items())
        elif type(item) is list:
            stack.extend((child, False) for child in item)


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
    deepest, size = value_bounds(body)
    if deepest > MAX_DEPTH:
        raise Refused('invalid_input', 'request nests deeper than ' + str(MAX_DEPTH))
    if size > MAX_REQUEST_BYTES:
        raise Refused('invalid_input', 'request is larger than ' + str(MAX_REQUEST_BYTES) + ' bytes')
    try:
        plain(body, 'request')
    except Refused as error:
        raise Refused('invalid_input', error.detail) from error
    for text, declared in _strings({key: value for key, value in body.items() if key != 'schema'}):
        if declared and is_url(text):
            continue
        if looks_like_path(text):
            raise Refused('path_in_request', 'a request carries no filesystem location: ' + repr(text[:80]))
    if len(canonical(body)) > MAX_REQUEST_BYTES:
        raise Refused('invalid_input', 'request is larger than ' + str(MAX_REQUEST_BYTES) + ' bytes')
    return body


def response(sent, raw):
    """Parse the runner's bytes into one accepted plain response, or refuse by name."""
    raw = raw.encode() if type(raw) is str else bytes(raw)
    if len(raw) > MAX_ANSWER_BYTES:
        raise Refused('invalid_response', 'answer is larger than ' + str(MAX_ANSWER_BYTES) + ' bytes')
    try:
        # Strictly UTF-8 and parsed as text: json.loads(bytes) would also accept UTF-16 and UTF-32,
        # which the byte-level depth scan cannot follow.
        text = raw.decode('utf-8')
    except UnicodeDecodeError as error:
        raise Refused('invalid_response', 'answer is not UTF-8') from error
    if text_depth(raw) > MAX_DEPTH:
        raise Refused('invalid_response', 'answer nests deeper than ' + str(MAX_DEPTH))
    try:
        value = json.loads(text, parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
    except RecursionError as error:
        raise Refused('invalid_response', 'answer nests too deeply to parse') from error
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
    if outcome == 'suspended':
        _resume_shape(value['resume'], 'resume', 'invalid_response')
    if outcome == 'failure':
        failure = _exact(value['failure'], ('code', 'detail'), 'failure', 'invalid_response')
        if failure['code'] not in FAILURES or type(failure['detail']) is not str or len(failure['detail']) > 500:
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
    return (type(runtime) is dict and set(runtime) == {'python', 'runner', 'stage'}
            and all(type(runtime[key]) is str for key in runtime)
            and Path(runtime['python']).is_file() and Path(runtime['runner']).is_file()
            and Path(runtime['stage']).is_absolute())


def inside_repository(path):
    """Whether a path lies inside a Git working tree or Git directory, judged both as written and
    as resolved: a repository's own virtual environment links out to the system interpreter, and
    resolving that link must not hide where the path was written."""
    def within(path):
        return any((parent / '.git').exists() or parent.name == '.git' or (parent / 'HEAD').is_file()
                   and (parent / 'objects').is_dir() for parent in (path, *path.parents))
    return within(Path(os.path.abspath(path))) or within(Path(path).resolve())


def _unlinked(root, name):
    """<root>/<name> as a real directory the adapter made or accepted: never a link, and resolving
    exactly under the resolved stage root."""
    path = root / name
    if path.is_symlink():
        raise Refused('runtime_unavailable', 'the stage ' + name + ' is a link the adapter did not make')
    path.mkdir(mode=0o700, exist_ok=True)
    if path.is_symlink() or not path.is_dir() or path.resolve() != path:
        raise Refused('runtime_unavailable', 'the stage ' + name + ' does not resolve under the stage root')
    return path


def stage(runtime):
    """The runner, copied content-addressed into the stage, outside every repository. The stage is a
    per-account directory separate from the runtime; the adapter follows no link it did not make."""
    root = Path(runtime['stage']).resolve()
    if inside_repository(root):
        raise Refused('runtime_unavailable', 'the runtime stage lies inside a repository')
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    runners, work = _unlinked(root, 'runners'), _unlinked(root, 'work')
    source = Path(runtime['runner']).read_bytes()
    target = runners / (hashlib.sha256(source).hexdigest() + '.py')
    if target.is_symlink():
        raise Refused('runtime_unavailable', 'the staged runner is a link the adapter did not make')
    if not target.is_file() or target.read_bytes() != source:
        temporary = runners / ('.staging-' + os.urandom(8).hex())
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, 'wb') as out:
            out.write(source)
        os.replace(temporary, target)
    if target.is_symlink() or target.resolve().parent != runners:
        raise Refused('runtime_unavailable', 'the staged runner does not resolve under the stage root')
    return target, work


def runtime_problems(runtime):
    """Why the runtime interpreter would lead a child toward a repository: the interpreter itself
    resolving inside one, or a path in its virtual environment's pyvenv.cfg (such as the creating
    interpreter recorded in `command`) that lies inside one. Checked before every launch."""
    problems = []
    python = Path(runtime['python'])
    if inside_repository(os.path.realpath(python)):
        problems.append('the runtime interpreter resolves inside a repository')
    config = python.parent.parent / 'pyvenv.cfg'
    if config.is_file():
        for line in config.read_text(errors='replace').splitlines():
            key, _, value = line.partition('=')
            for token in value.split():
                if token.startswith('/') and inside_repository(token):
                    problems.append('pyvenv.cfg ' + key.strip() + ' names a repository path')
    return problems


def _working_directory(work):
    """A fresh working directory for one child, resolved and checked immediately before launch."""
    path = Path(tempfile.mkdtemp(prefix='veldo-graph-', dir=work))
    resolved = path.resolve()
    if resolved.parent != work.resolve() or inside_repository(resolved):
        raise Refused('runtime_unavailable', 'the child working directory does not resolve outside every repository')
    return resolved


def _remove(path):
    try:
        if path.is_symlink():
            path.unlink()
        else:
            shutil.rmtree(path)
    except OSError:
        pass


def _wait_unreaped(pid, timeout):
    """Wait for the child to exit without reaping it, so its process group id cannot be reused
    before the group is killed. True if it exited within the deadline."""
    deadline = time.monotonic() + timeout
    while os.waitid(os.P_PID, pid, os.WEXITED | os.WNOWAIT | os.WNOHANG) is None:
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.005)
    return True


def _end_group(proc):
    """Kill the child's whole process group (its own session), then reap the child."""
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    proc.kill()
    proc.wait()


def exchange(runtime, sent, timeout=120):
    """One request, one response, one child process with nothing inherited, in its own session;
    the whole process group is killed on the deadline and on every exit path."""
    if not available(runtime):
        raise Refused('runtime_unavailable', 'no graph runtime is installed for this operation; install it with: '
                      + INSTALL_COMMAND)
    problems = runtime_problems(runtime)
    if problems:
        raise Refused('runtime_unavailable', '; '.join(problems))
    staged, work = stage(runtime)
    empty = _working_directory(work)
    # Request and answer travel through anonymous files, not pipes, so a subprocess a node left
    # holding the answer stream cannot keep the exchange open.
    with tempfile.TemporaryFile() as given, tempfile.TemporaryFile() as answer:
        given.write(canonical(sent))
        given.seek(0)
        try:
            proc = subprocess.Popen([runtime['python'], '-I', '-B', str(staged)],
                                    stdin=given, stdout=answer, stderr=subprocess.DEVNULL, cwd=str(empty),
                                    env=dict(ENVIRONMENT), close_fds=True, start_new_session=True)
        except OSError as error:
            _remove(empty)
            raise Refused('runtime_unavailable', 'graph runtime could not be launched') from error
        try:
            finished = _wait_unreaped(proc.pid, timeout)
        finally:
            _end_group(proc)
            _remove(empty)
        if not finished:
            raise Refused('unknown_outcome', 'graph runtime did not answer within its deadline')
        if proc.returncode:
            raise Refused('unknown_outcome', 'graph runtime exited ' + str(proc.returncode) + ' without an answer')
        answer.seek(0)
        raw = answer.read(MAX_ANSWER_BYTES + 1)
    return response(sent, raw)


class Adapter:
    """Lifecycle operations over one domain and repository, with counts and observations."""

    @classmethod
    def installed(cls, domain_uuid, repository_uuid, home=None, timeout=120, stage=None):
        """An adapter over the locked runtime this account has installed (None if absent), whose
        answers must be runtime evidence from that locked LangGraph. `stage` replaces the account
        stage directory (the suite stages into a temporary one)."""
        runtime = resolve_runtime(home)
        if runtime is not None and stage is not None:
            runtime = dict(runtime, stage=str(stage))
        return cls(runtime, domain_uuid, repository_uuid, timeout, evidence=runtime_evidence())

    def __init__(self, runtime, domain_uuid, repository_uuid, timeout=120, evidence=None):
        self.runtime, self.timeout, self.evidence = runtime, timeout, evidence
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
            if self.evidence is not None and not evidenced(result, self.evidence):
                raise Refused('missing_evidence', 'answer labelled ' + repr(result['runtime'])
                              + ' is not runtime evidence from ' + repr(self.evidence))
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
