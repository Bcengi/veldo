"""Content identities and a private, authenticated, append-only result store."""
import hashlib
import importlib.util
import hmac
import json
import os
from pathlib import Path
import stat
import tempfile
import warnings

_spec = importlib.util.spec_from_file_location('reuse_evidence',
    Path(__file__).resolve().parents[1] / '.veldo/reuse_evidence.py')
E = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(E)
SCHEMA = E.SCHEMA


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('ascii')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def tree_identity(path):
    """Read every regular file, directory name and mode; ambiguity is a miss upstream."""
    path = Path(path)
    result = {}

    visited = set()

    def visit(current, name):
        visited.add(current.absolute())
        info = current.lstat()
        mode = stat.S_IMODE(info.st_mode)
        if stat.S_ISREG(info.st_mode):
            value = hashlib.sha256(current.read_bytes()).hexdigest()
        elif stat.S_ISDIR(info.st_mode):
            value = 'directory'
            for child in sorted(current.iterdir()):
                visit(child, name + '/' + child.name)
        elif stat.S_ISLNK(info.st_mode):
            target = current.resolve(strict=True)
            # Directory back-links are represented by the already visited target path.
            value = ['symlink', os.readlink(current), str(target)]
            if target not in visited:
                visit(target, name + '/@target')
        else:
            raise ValueError('unclosed runtime input: ' + str(current))
        result[name] = [mode, value]
    visit(path, '.')
    return result


class Store:
    """A record cannot be forged by editing its data or recomputing a plain checksum.

    The key stays separate from records. Agent domains cannot read or write it;
    the unconfined owner and orchestrator are trusted. I/O errors are misses.
    """
    def __init__(self, directory, repository):
        self.directory = None
        self.secret = None
        self.integrity_errors = []
        try:
            self.directory = Path(directory).expanduser().resolve()
            root = Path(repository).resolve()
            if self.directory == root or root in self.directory.parents:
                return
            # Worker runtime trees must never contain coordinator credentials.
            if any(self.directory == Path(p).resolve() or Path(p).resolve() in self.directory.parents
                   for p in ('/usr', '/lib', '/lib64', '/etc', '/dev', '/proc', '/run', '/sys')):
                return
            self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            self._private(self.directory, directory=True)
            keypath = self.directory / 'authentication.key'
            secret = os.urandom(32)
            # Publish only complete keys. Concurrent creators use the winning key.
            self._publish(keypath, secret, key_creation=True)
            self._private(keypath)
            self.secret = E.probe(self.directory)
            if len(self.secret) != 32:
                self.secret = None
        except (OSError, ValueError, TypeError, RuntimeError):
            self.secret = None

    @staticmethod
    def _private(path, directory=False):
        info = path.lstat()
        kind = stat.S_ISDIR if directory else stat.S_ISREG
        if not kind(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError('cache path must be private and owned')

    def _publish(self, target, body, key_creation=False, existing_valid=None):
        fd, name = tempfile.mkstemp(prefix='.pending-', dir=self.directory)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(body)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(name, target)
            except FileExistsError:
                # A valid record already present wins: an equivalent run publishing different
                # bytes is not a conflict. Only an existing record that fails validation is.
                if (not key_creation and target.read_bytes() != body
                        and not (existing_valid is not None and existing_valid())):
                    self.integrity_errors.append(target.name)
                    # Poisoned identities stay misses until explicitly removed.
                    (self.directory / (target.name + '.conflict')).touch(mode=0o600)
                    warnings.warn('reuse integrity failure: conflicting record ' + target.name)
                    raise ValueError('conflicting cache record')
        finally:
            os.unlink(name)

    def _path(self, key):
        if not isinstance(key, str) or len(key) != 64 or any(c not in '0123456789abcdef' for c in key):
            raise ValueError('invalid reuse key')
        return self.directory / (key + '.json')

    def get(self, key):
        if self.secret is None:
            return None
        try:
            return E.record(self.directory, key, self.secret)
        except (OSError, ValueError, TypeError, KeyError):
            return None

    def put(self, key, result, accept=None):
        """Publish `result` once. An existing authenticated record that `accept` (the stage's own
        result validation) admits is kept; any other differing record, or any differing record
        when no validation is supplied, is a conflict."""
        if self.secret is None:
            return False
        try:
            if self._path(key).with_suffix('.json.conflict').exists():
                self.integrity_errors.append(self._path(key).name)
                return False
            if E.probe(self.directory) != self.secret:
                return False
            payload = dict(schema=SCHEMA, key=key, result=result, provenance=E.PROVENANCE,
                           authority=E.authority_identity())
            document = dict(payload=payload,
                            mac=hmac.new(self.secret, canonical(payload), hashlib.sha256).hexdigest())
            def existing_valid():
                existing = self.get(key)
                return accept is not None and existing is not None and accept(existing)
            self._publish(self._path(key), canonical(document), existing_valid=existing_valid)
            return True
        except (OSError, ValueError, TypeError):
            return False


# ---- VELDO-0206: exact input suite result reuse in the canonical gate ----------------------------
#
# WHO DOES WHAT. The unit stage's dispatcher (scripts/selftest.py) is candidate code and runs in
# the gate's confinement, which cannot open the store. So every decision that needs the store is
# made here, by the authority, around the stage:
#
#   suite-plan    before the stage: one exact key per manifest suite, or the named reason it has
#                 none, and an authenticated passing record looked up for each key. The answer is
#                 handed to the dispatcher in VELDO_SUITE_REUSE: the suites it may leave out, bound
#                 to this root and to one run's nonce. Nothing else reaches the candidate.
#   suite-settle  after the stage: the dispatcher's own result lines are read back, every manifest
#                 suite is accounted for, every key is computed again, and only then is a fresh
#                 passing result published. It writes the stage's receipt.
#   suite-stamp   the receipt's reused count, put into the stamp's reuse fields.
#
# WHAT A KEY HOLDS. The suites share one mutable namespace, so a suite's inputs are not its own
# file: they are the state every prerequisite suite left behind. A key therefore holds, for the
# suite AND for every member of its prerequisite closure (scripts/suites/requires.json), the suite
# file, its manifest entry, its reviewed qualification and the content of every input that
# qualification declares; and beside them the shared preamble, the dispatcher, the authority's
# unconfined list, the interpreter and tool trees, the named environment values and the root.
#
# A SUITE IS REUSABLE ONLY BY EXPLICIT QUALIFICATION. The qualifications are a literal in the
# candidate's scripts/run_scope.py, a protected file, read here with ast and never imported. A
# qualification pins the digest of the code it reviewed (the shared preamble and every closure
# suite file), so an edit to any of them is an unknown closure until it is reviewed again. A suite
# with no qualification, with an unqualified or unconfined prerequisite, or with a closure that
# cannot be read runs fresh, always.
SUITE_KEY = 'veldo.suite-key/v1'
SUITE_RESULT = 'veldo.suite-result/v1'
SUITE_PLAN = 'veldo.suite-plan/v1'
SUITE_RECEIPT = 'veldo.suite-receipt/v1'
SUITE_CLOSURES = 'veldo.suite-closures/v1'
SUITE_VARIABLE = 'VELDO_SUITE_REUSE'
SUITE_LINE = 'selftest-suite-reuse'
SUITE_MANIFEST = 'scripts/suites/manifest.json'
SUITE_REQUIRES = 'scripts/suites/requires.json'
SUITE_REGISTRY = 'scripts/run_scope.py'
SUITE_DISPATCHER = ('scripts/selftest.py', 'scripts/run_scope.py')
# Read by every suite's process whatever it tests; a qualification names any further variable.
SUITE_ENVIRONMENT = ('PATH', 'LANG', 'LC_ALL', 'LC_CTYPE', 'TZ', 'TMPDIR', 'PYTHONPATH',
                     'PYTHONHASHSEED', 'VELDO_AGENT_CONFIG')
SUITE_QUALIFICATION = {'closure_digest', 'inputs', 'runtime_paths', 'environment',
                       'non_file_inputs', 'rationale'}
SUITE_RESULT_FIELDS = {'schema', 'suite', 'input_digest', 'status', 'scope', 'complete',
                       'passed', 'failed'}
SUITE_LOGS = ('unit.log', 'unit.confined.log', 'unit.unconfined.log')


class SuiteUnknown(Exception):
    """A suite with no exact closure: the reason is its name, and the suite runs fresh."""


def _sibling(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def suite_registry(root):
    """The candidate's reviewed qualifications: a literal, parsed, never executed."""
    import ast
    tree = ast.parse((Path(root) / SUITE_REGISTRY).read_text())
    found = [node.value for node in tree.body
             if isinstance(node, ast.Assign) and len(node.targets) == 1
             and isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'SUITE_REUSE']
    if len(found) != 1:
        raise ValueError('scripts/run_scope.py does not hold exactly one SUITE_REUSE literal')
    document = ast.literal_eval(found[0])
    if (not isinstance(document, dict) or set(document) != {'schema', 'suites'}
            or document['schema'] != SUITE_CLOSURES or not isinstance(document['suites'], dict)):
        raise ValueError('invalid suite qualifications')
    return document['suites']


def _suite_path(root, relative):
    if (not isinstance(relative, str) or not relative or os.path.isabs(relative)
            or '..' in Path(relative).parts):
        raise ValueError('a declared input must be a path inside the repository')
    return Path(root) / relative


def suite_input(root, relative):
    """Content, names and modes of one declared input; an absent one is its own identity."""
    path = _suite_path(root, relative)
    if not os.path.lexists(path):
        return 'absent'
    return tree_identity(path)


def suite_qualification(value):
    if (not isinstance(value, dict) or set(value) != SUITE_QUALIFICATION
            or value['non_file_inputs'] != 'none'
            or not isinstance(value['rationale'], str) or not value['rationale'].strip()
            or not isinstance(value['closure_digest'], str)
            or not isinstance(value['inputs'], list)
            or not all(isinstance(item, str) for item in value['inputs'])
            or not isinstance(value['runtime_paths'], list) or not value['runtime_paths']
            or not all(isinstance(item, str) for item in value['runtime_paths'])
            or not isinstance(value['environment'], list)
            or not all(isinstance(item, str) and item for item in value['environment'])):
        raise SuiteUnknown('invalid_qualification')
    return value


def suite_code_digest(root, shared, closure, files):
    """What a qualification pins: the shared preamble and every closure suite's file."""
    code = {'shared': suite_input(root, 'scripts/suites/' + shared)}
    for member in closure:
        code[member] = suite_input(root, 'scripts/suites/' + files[member])
    return digest(code), code


def suite_unconfined():
    """Names the authority's list sends, whole or by rows, to the unconfined leg, and its digest."""
    path = Path(__file__).with_name('gate_unconfined.json')
    if not path.exists():
        return set(), 'absent'
    document, declaration = _sibling('gate_legs').load(path)
    return {entry['suite'] for entry in document['suites']}, declaration


def suite_entries(root, environ, forced, runtime=None):
    """(names in manifest order, {name: {suite, key, reason}}). A key is None with its reason."""
    root = Path(root).resolve()
    manifest = json.loads((root / SUITE_MANIFEST).read_text())
    suites = [s for s in manifest['suites'] if s['file'] != manifest['shared']]
    names = [s['name'] for s in suites]
    if len(set(names)) != len(names):
        raise ValueError('the manifest names a suite twice')
    entries = {name: {'suite': name, 'key': None, 'reason': 'force_fresh' if forced else 'unqualified'}
               for name in names}
    if forced:
        return names, entries
    try:
        registry = suite_registry(root)
    except (OSError, ValueError, SyntaxError, TypeError):
        registry = {}
    if not any(name in registry for name in names):
        return names, entries
    by_name = {s['name']: s for s in suites}
    files = {s['name']: s['file'] for s in suites}
    try:
        requires = json.loads((root / SUITE_REQUIRES).read_text())['requires']
        if not isinstance(requires, dict):
            raise ValueError('invalid closure table')
    except (OSError, ValueError, KeyError, TypeError):
        requires = {}
    try:
        listed, declaration = suite_unconfined()
        base = digest({'schema': SUITE_KEY, 'root': str(root), 'authority': E.authority_identity(),
                       'dispatcher': {name: suite_input(root, name) for name in SUITE_DISPATCHER},
                       'shared': manifest['shared'], 'unconfined': declaration})
    except Exception:
        for name in names:
            if name in registry:
                entries[name]['reason'] = 'closure_error'
        return names, entries
    runtime = suite_runtime if runtime is None else runtime
    runtimes = {}
    for name in names:
        if name not in registry:
            continue
        try:
            closure = requires.get(name)
            if (not isinstance(closure, list) or name not in closure
                    or any(member not in by_name for member in closure)):
                raise SuiteUnknown('closure_unavailable')
            if any(member in listed for member in closure):
                raise SuiteUnknown('unconfined_leg')
            if any(member not in registry for member in closure):
                raise SuiteUnknown('unqualified_prerequisite')
            qualification = suite_qualification(registry[name])
            pinned, code = suite_code_digest(root, manifest['shared'], closure, files)
            if qualification['closure_digest'] != pinned:
                raise SuiteUnknown('stale_qualification')
            members = list(closure)  # the prerequisite state: every closure member enters the key
            state = []
            for member in members:
                reviewed = suite_qualification(registry[member])
                state.append({'suite': member, 'file': code[member], 'entry': by_name[member],
                              'qualification': reviewed,
                              'inputs': {item: suite_input(root, item) for item in sorted(reviewed['inputs'])}})
            variables = tuple(sorted(set(SUITE_ENVIRONMENT) | set(qualification['environment'])))
            identity = (tuple(qualification['runtime_paths']), variables)
            if identity not in runtimes:
                runtimes[identity] = digest(runtime(identity[0], {v: environ.get(v) for v in variables}))
            entries[name].update(key=digest({'base': base, 'suite': name, 'code': pinned, 'closure': state,
                                             'runtime': runtimes[identity]}), reason='miss')
        except SuiteUnknown as unknown:
            entries[name]['reason'] = str(unknown)
        except (OSError, ValueError, KeyError, TypeError, RuntimeError):
            entries[name]['reason'] = 'closure_error'
    return names, entries


def suite_required_runtime(environment):
    """What every suite's process runs on whatever it tests: the interpreter, its library, and
    the tools a suite reaches by name. Libraries and configuration those load are the
    qualification's to declare, as in VELDO-0205: a qualification is a reviewed contract."""
    import shutil
    import sys
    import sysconfig
    required = [Path(sys.executable).resolve(), Path(sysconfig.get_path('stdlib')).resolve()]
    for tool in ('git', 'sh', 'bash'):
        found = shutil.which(tool, path=environment.get('PATH') or '/usr/bin:/bin')
        if found:
            required.append(Path(found).resolve())
    return required


def suite_runtime(paths, environment):
    """Interpreter, standard library and tools by content, names and modes; the values of the
    named environment variables are hashed, never printed."""
    import platform
    import sys
    trees = {}
    for name in paths:
        path = Path(name)
        if not path.is_absolute() or '..' in path.parts:
            raise ValueError('runtime paths must be absolute')
        trees[str(path)] = tree_identity(path)
    covered = [Path(name).resolve() for name in trees]
    for required in suite_required_runtime(environment):
        if not any(required == path or path in required.parents for path in covered):
            raise ValueError('runtime dependency is outside the closure: ' + str(required))
    return {'trees': trees, 'executable': str(Path(sys.executable).resolve()), 'python': sys.version,
            'implementation': sys.implementation.name, 'cache_tag': sys.implementation.cache_tag,
            'platform': list(platform.uname()), 'environment': digest(dict(environment))}


def validate_suite_result(result, suite, key):
    """Only a complete passing observation of the whole suite, under exactly this key, is a hit."""
    if (not isinstance(result, dict) or set(result) != SUITE_RESULT_FIELDS
            or result['schema'] != SUITE_RESULT or result['suite'] != suite
            or result['input_digest'] != key or result['status'] != 'passed'
            or result['scope'] != 'full' or result['complete'] is not True
            or type(result['passed']) is not int or result['passed'] < 1
            or type(result['failed']) is not int or result['failed'] != 0):
        raise ValueError('not a complete passing suite observation')
    return result


def _suite_store(root, environ, store=None):
    directory = store or environ.get('VELDO_GATE_CACHE')
    try:
        if not directory:
            directory = E.configuration()[1]['store']
        return Store(directory, root)
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _suite_forced(environ, force_fresh):
    return _sibling('mutation_reuse').truthy(force_fresh) or \
        _sibling('mutation_reuse').truthy(environ.get('VELDO_GATE_FORCE_FRESH', '0'))


def suite_plan(root, state, environ=None, force_fresh='0', store=None, runtime=None):
    """Write the authority's plan under `state` and return the value the dispatcher is handed."""
    environ = os.environ if environ is None else environ
    root = Path(root).resolve()
    forced = _suite_forced(environ, force_fresh)
    names, entries = suite_entries(root, environ, forced, runtime)
    if any(entry['key'] for entry in entries.values()):
        opened = _suite_store(root, environ, store)
        for name in names:
            entry = entries[name]
            if not entry['key'] or opened is None:
                continue
            record = opened.get(entry['key'])
            if record is None:
                continue
            try:
                validate_suite_result(record, name, entry['key'])
            except ValueError:
                entry['reason'] = 'invalid_record'
            else:
                entry.update(reason='hit', record=record)
    plan = {'schema': SUITE_PLAN, 'nonce': os.urandom(16).hex(), 'root': str(root),
            'force_fresh': forced, 'suites': [entries[name] for name in names]}
    state = Path(state)
    fd = os.open(state / 'plan.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(plan, stream)
    return json.dumps({'schema': SUITE_PLAN, 'nonce': plan['nonce'], 'root': plan['root'],
                       'reuse': {entry['suite']: entry['record']['passed'] for entry in plan['suites']
                                 if entry['reason'] == 'hit'}},
                      sort_keys=True, separators=(',', ':'))


def suite_observations(texts, nonce):
    """{leg: {begin, results, end}} from the dispatcher's lines of this run, and what is wrong
    with them. A line is found wherever it stands, so another process's unfinished line before it
    hides nothing."""
    import re
    pattern = re.compile(re.escape(SUITE_LINE) + ' ' + re.escape(nonce) + r' (begin|result|end) (\{.*\})\s*$')
    legs, problems = {}, []
    for text in texts:
        for line in text.splitlines():
            found = pattern.search(line)
            if not found:
                continue
            kind = found.group(1)
            try:
                item = json.loads(found.group(2))
                leg = item['leg']
                if leg not in (None, 'confined', 'unconfined'):
                    raise ValueError('unknown leg')
            except (ValueError, KeyError, TypeError):
                problems.append('an unreadable dispatcher line')
                continue
            name = leg or 'whole'
            if kind == 'begin':
                if name in legs:
                    problems.append('the %s leg began twice' % name)
                    continue
                legs[name] = {'begin': item, 'results': {}, 'end': None}
            elif name not in legs or legs[name]['end'] is not None:
                problems.append('a %s line of the %s leg stands outside its run' % (kind, name))
            elif kind == 'end':
                legs[name]['end'] = item
            elif (not isinstance(item.get('suite'), str) or item.get('source') not in ('fresh', 'reused')
                  or type(item.get('passed')) is not int or type(item.get('failed')) is not int
                  or item['passed'] < 0 or item['failed'] < 0):
                problems.append('a malformed result line in the %s leg' % name)
            elif item['suite'] in legs[name]['results']:
                problems.append('%s reported twice in the %s leg' % (item['suite'], name))
            else:
                legs[name]['results'][item['suite']] = item
    return legs, problems


def suite_settle(root, state, texts, stage_status, environ=None, store=None, runtime=None):
    """Account for every manifest suite, publish what may be published, write the receipt.

    Returns (receipt, problems). `problems` are what makes the gate RED on their own: a suite the
    stage did not account for while it reported a pass, a reused result the plan did not
    authenticate or whose inputs changed during the stage, a fresh failure behind a passing status.
    """
    environ = os.environ if environ is None else environ
    root, state = Path(root).resolve(), Path(state)
    plan = json.loads((state / 'plan.json').read_text())
    if plan.get('schema') != SUITE_PLAN or plan.get('root') != str(root):
        raise ValueError('the suite plan is not this run\'s')
    forced = plan['force_fresh']
    planned = {entry['suite']: entry for entry in plan['suites']}
    names = list(planned)
    legs, problems = suite_observations(texts, plan['nonce'])
    try:
        now_names, now = suite_entries(root, environ, forced, runtime)
    except (OSError, ValueError, KeyError, TypeError) as error:
        now_names, now = None, {}
        problems.append('the suite inputs cannot be read again (%s)' % error)
    if now_names is not None and now_names != names:
        problems.append('the manifest changed during the stage')
    failed = stage_status != 'pass'
    for name, leg in legs.items():
        if leg['end'] is None:
            failed = True
            if stage_status == 'pass':
                problems.append('the %s leg did not finish' % name)
        elif leg['end'].get('exit') != 0:
            failed = True
            if stage_status == 'pass':
                problems.append('the %s leg exited %r behind a passing stage' % (name, leg['end'].get('exit')))
        for suite in leg['results']:
            if suite not in planned:
                problems.append('%s is no suite of the planned manifest' % suite)
    opened = None
    results, published = [], 0
    for name in names:
        entry = planned[name]
        seen = [(leg_name, leg, leg['results'][name]) for leg_name, leg in legs.items() if name in leg['results']]
        result = {'suite': name, 'key': entry['key'], 'reason': entry['reason'], 'source': 'not_run',
                  'passed': 0, 'failed': 0, 'legs': [leg_name for leg_name, _, _ in seen]}
        unchanged = entry['key'] is not None and now.get(name, {}).get('key') == entry['key']
        if not seen:
            failed = True
            if stage_status == 'pass':
                problems.append('%s has no result behind a passing stage' % name)
        elif any(item['source'] == 'reused' for _, _, item in seen):
            item = seen[0][2]
            result.update(source='reused', passed=item['passed'])
            if (len(seen) != 1 or forced or entry['reason'] != 'hit'
                    or item['passed'] != entry['record']['passed'] or item['failed'] != 0):
                problems.append('%s was reused without an authenticated record of this plan' % name)
            elif not unchanged:
                problems.append('the inputs of reused %s changed during the stage' % name)
        else:
            result.update(source='fresh', passed=sum(item['passed'] for _, _, item in seen),
                          failed=sum(item['failed'] for _, _, item in seen))
            if entry['reason'] == 'hit':
                result['reason'] = 'prerequisite_of_fresh'
            if result['failed']:
                failed = True
                if stage_status == 'pass':
                    problems.append('%s failed %d row(s) behind a passing stage' % (name, result['failed']))
            leg_name, leg, item = seen[0]
            complete = (len(seen) == 1 and leg['end'] is not None
                        and leg['begin'].get('scope') == 'full')
            if entry['key'] is not None and not forced and not unchanged:
                result['reason'] = 'input_changed'
            elif (entry['key'] is not None and not forced and complete
                  and item['failed'] == 0 and item['passed'] >= 1):
                record = {'schema': SUITE_RESULT, 'suite': name, 'input_digest': entry['key'],
                          'status': 'passed', 'scope': 'full', 'complete': True,
                          'passed': item['passed'], 'failed': 0}
                if opened is None:
                    opened = _suite_store(root, environ, store)

                def accept(existing, name=name, key=entry['key']):
                    try:
                        validate_suite_result(existing, name, key)
                    except ValueError:
                        return False
                    return True
                if opened is not None and opened.put(entry['key'], record, accept):
                    published += 1
                    result['published'] = True
        results.append(result)
    receipt = {'schema': SUITE_RECEIPT, 'status': 'failed' if failed or problems else 'passed',
               'force_fresh': forced, 'registered': len(names),
               'executed': sum(r['source'] == 'fresh' for r in results),
               'reused': sum(r['source'] == 'reused' for r in results),
               'not_run': sum(r['source'] == 'not_run' for r in results),
               'qualified': sum(r['key'] is not None for r in results),
               'published': published, 'legs': sorted(legs), 'problems': problems, 'results': results}
    (state / 'receipt.json').write_text(json.dumps(receipt, indent=1) + '\n')
    return receipt, problems


def suite_stamp(state, fields, force_fresh='0', environ=None):
    """The stamp's reuse fields with the unit stage's reused count; unchanged text when it is 0."""
    environ = os.environ if environ is None else environ
    document = json.loads('{' + fields + '}')
    receipt = json.loads((Path(state) / 'receipt.json').read_text())
    results = receipt['results']
    reused = sum(result['source'] == 'reused' for result in results)
    if (receipt.get('schema') != SUITE_RECEIPT or receipt.get('status') not in ('passed', 'failed')
            or len(results) != receipt['registered'] or reused != receipt['reused']
            or sum(result['source'] == 'fresh' for result in results) != receipt['executed']
            or receipt['executed'] + receipt['reused'] + receipt['not_run'] != receipt['registered']
            or (receipt['status'] == 'passed' and (receipt['not_run'] or receipt['problems']))
            or any(result['source'] == 'reused' and not result['key'] for result in results)
            or type(receipt.get('force_fresh')) is not bool
            or receipt['force_fresh'] != _suite_forced(environ, force_fresh)
            or (receipt['force_fresh'] and reused)):
        raise ValueError('missing or inconsistent suite reuse receipt')
    if not reused:
        return fields
    document['reused']['unit'] = reused
    return json.dumps(document, separators=(',', ':'))[1:-1]


def main(argv):
    """suite-plan, suite-settle and suite-stamp, for verify.sh. Each refusal is one line."""
    import argparse
    import sys
    parser = argparse.ArgumentParser(description='Suite result reuse steps of the canonical gate.')
    parser.add_argument('step', choices=('suite-plan', 'suite-settle', 'suite-stamp'))
    parser.add_argument('--root', required=True)
    parser.add_argument('--state', required=True)
    parser.add_argument('--force-fresh', default='0')
    parser.add_argument('--logs', help='the directory holding the unit stage\'s output')
    parser.add_argument('--stage-status', default='FAIL')
    args = parser.parse_args(argv[1:])
    try:
        if args.step == 'suite-plan':
            print(suite_plan(args.root, args.state, force_fresh=args.force_fresh))
            return 0
        if args.step == 'suite-stamp':
            fields = sys.stdin.read().strip()
            try:
                print(suite_stamp(args.state, fields, args.force_fresh))
            except (OSError, ValueError, KeyError, TypeError) as error:
                print('suite reuse: no stamp fields: %s; the gate is RED and claims no suite reuse'
                      % error, file=sys.stderr)
                print(fields)
                return 1
            return 0
        texts = []
        for name in SUITE_LOGS:
            path = Path(args.logs) / name
            if path.is_file():
                texts.append(path.read_text(errors='replace'))
        receipt, problems = suite_settle(args.root, args.state, texts, args.stage_status)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print('suite reuse: %s failed: %s' % (args.step, error), file=sys.stderr)
        return 1
    for result in receipt['results']:
        print('   suite %s: source=%s key=%s reason=%s passed=%d failed=%d'
              % (result['suite'], result['source'], result['key'] or 'none', result['reason'],
                 result['passed'], result['failed']))
    print('   suite reuse: %s; registered=%d fresh=%d reused=%d not_run=%d qualified=%d published=%d '
          'force_fresh=%s' % (receipt['status'], receipt['registered'], receipt['executed'],
                              receipt['reused'], receipt['not_run'], receipt['qualified'],
                              receipt['published'], str(receipt['force_fresh']).lower()))
    for problem in problems:
        print('   suite reuse: RED: %s' % problem)
    return 1 if problems else 0


if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))
