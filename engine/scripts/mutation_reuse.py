"""Conservative mutation reuse admission. Unknown external closure always runs fresh.

Profiles are reviewed qualifications, never inferred from a passing run or an observed
read trace. Their repository digest pins every byte whose behavior was reviewed.
"""
import hashlib
import importlib.util
import json
import os
import random
import math
from pathlib import Path
import platform
import sys
import sysconfig
import shutil

_spec = importlib.util.spec_from_file_location('gate_reuse', Path(__file__).with_name('gate_reuse.py'))
R = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R)
PROFILE = 'scripts/mutation_reuse_profiles.json'


def input_identity(files):
    return {name: [mode, hashlib.sha256(body).hexdigest()]
            for name, (mode, body) in files.items()}


def qualification_digest(files):
    return R.digest({name: value for name, value in input_identity(files).items() if name != PROFILE})


def truthy(value):
    value = str(value).strip().lower()
    if value in ('1', 'true', 'yes', 'on'):
        return True
    if value in ('0', 'false', 'no', 'off', ''):
        return False
    raise ValueError('unknown VELDO_GATE_FORCE_FRESH value: ' + value)


def required_runtime(environment):
    # Libraries already mapped before Landlock are inputs too (notably libc and the loader).
    mapped = set()
    for line in Path('/proc/self/maps').read_text().splitlines():
        fields = line.split()
        if len(fields) >= 6 and fields[-1].startswith('/') and '.so' in fields[-1]:
            mapped.add(Path(fields[-1]).resolve())
    return sorted(mapped) + [Path(sys.executable).resolve(), Path(sysconfig.get_path('stdlib')).resolve(),
            Path(shutil.which('git', path=environment.get('PATH', '/usr/bin:/bin'))).resolve(),
            Path(shutil.which('sh', path=environment.get('PATH', '/usr/bin:/bin'))).resolve()]


def runtime_identity(paths, environment):
    """The profile must cover libraries, tool dependencies and configuration, not just binaries."""
    executable = Path(sys.executable).resolve()
    trees = {}
    for name in paths:
        path = Path(name)
        if not path.is_absolute() or '..' in path.parts:
            raise ValueError('runtime paths must be absolute')
        trees[str(path)] = R.tree_identity(path)
    for required in required_runtime(environment):
        if not any(required == Path(p).resolve() or Path(p).resolve() in required.parents for p in trees):
            raise ValueError('runtime dependency is outside the closure: ' + str(required))
    return {'trees': trees, 'executable': str(executable), 'python': sys.version,
            'implementation': sys.implementation.name, 'cache_tag': sys.implementation.cache_tag,
            'platform': list(platform.uname()), 'environment': R.digest(dict(environment))}


STALE_SCHEMA = 'veldo.stale-declaration/v1'


def stale_entries(directory):
    """Authority findings, also consumed by the proposer and the VELDO-0218 audit.
    Marks only deny reuse; they never authorize it. One immutable file per finding avoids
    lost updates between concurrent stages. Reading does not create a store or credentials.
    """
    base = Path(directory).expanduser() / 'stale'
    try:
        names = sorted(os.listdir(base))
    except FileNotFoundError:
        return []
    # A list or a mark that cannot be read raises (OSError): marks only deny reuse, so a
    # caller that cannot read them must deny reuse, never treat the list as empty.
    entries = []
    for name in names:
        if not name.endswith('.json'):
            continue
        body = (base / name).read_bytes()
        try:
            entry = json.loads(body)
            if (entry['schema'] == STALE_SCHEMA and all(isinstance(entry[k], str) and entry[k]
                    for k in ('identity', 'declaration', 'gate_run', 'reason'))):
                entries.append(entry)
        except (ValueError, KeyError, TypeError):
            continue
    return entries


def mark_stale(store, *, identity, declaration, gate_run, reason):
    """Write a stale finding beside authenticated results, using the same private store boundary.
    The audit calls this same API for mismatches. No candidate or worker path is an output.
    """
    if not all(isinstance(value, str) and value for value in (identity, declaration, gate_run, reason)):
        raise ValueError('invalid stale finding')
    if store.secret is None:
        raise ValueError('authority stale store unavailable')
    directory = store.directory / 'stale'
    directory.mkdir(mode=0o700, exist_ok=True)
    store._private(directory, directory=True)
    entry = dict(schema=STALE_SCHEMA, identity=identity, declaration=declaration,
                 gate_run=gate_run, reason=reason)
    store._publish(directory / (R.digest(entry) + '.json'), R.canonical(entry))
    return entry


def audit_sample(records):
    """Draw only after lookup, using new authority entropy, with a quota in every suite.

    VELDO-0222 admission is authority record metadata, never a candidate's sampling knob.
    Per-suite rounding can exceed the global floor; no small suite can disappear in a big one.
    """
    rng = random.Random(int.from_bytes(os.urandom(32), 'big'))
    groups = {}
    for identity, record in records.items():
        rate = R.E.audit_rate(record)
        groups.setdefault((record['case']['suite'], rate), []).append(identity)
    selected = set()
    for (_, rate), identities in groups.items():
        selected.update(rng.sample(sorted(identities), math.ceil(len(identities) * rate / 100)))
    remaining = sorted(set(records) - selected)
    selected.update(rng.sample(remaining, max(0, min(len(records), 8) - len(selected))))
    return selected


class Session:
    def __init__(self, root, files, cases, head, configuration, *, force_fresh=False,
                 environment=None, cache_directory=None):
        self.root, self.files = Path(root), files
        controls = os.environ if environment is None else environment
        self.environment = dict(configuration.get('worker_environment', {}) if environment is None else environment)
        parsed_force = truthy(controls.get('VELDO_GATE_FORCE_FRESH', '0'))
        self.forced = force_fresh or parsed_force
        self.keys, self.reasons, self.hits = {}, {}, {}
        self.authenticated_digests = {}
        self.runtime_checks = {}
        self.runtime_digests = {}
        self.store = None
        self.base = {'schema': 'veldo.mutation-key/v1', 'files': input_identity(files),
                     'head': head, 'configuration': configuration, 'authority': R.E.authority_identity()}
        self.base_digest = R.digest(self.base)
        self.source_digest = qualification_digest(files)
        try:
            profiles = json.loads(files[PROFILE][1])
            if profiles['schema'] != 'veldo.mutation-closures/v1':
                raise ValueError('unknown profile schema')
            profiles = profiles['profiles']
            if not isinstance(profiles, dict):
                raise ValueError('invalid profiles')
        except (KeyError, ValueError, TypeError):
            profiles = {}
        for case in cases:
            identity = case['identity']
            self.keys[identity] = None
            self.reasons[identity] = 'force_fresh' if self.forced else 'unknown_closure'
            if self.forced:
                continue
            try:
                profile = profiles[identity]
                if (profile['tree_digest'] != self.source_digest
                        or profile['case_digest'] != R.digest(case)
                        or profile['non_file_inputs'] != 'none'
                        or not isinstance(profile['rationale'], str)
                        or not profile['rationale'].strip()
                        or not profile['runtime_paths']):
                    continue
                paths = tuple(profile['runtime_paths'])
                if paths not in self.runtime_checks:
                    self.runtime_checks[paths] = runtime_identity(paths, self.environment)
                    self.runtime_digests[paths] = R.digest(self.runtime_checks[paths])
                self.keys[identity] = R.digest({'inputs': self.base_digest, 'case': case, 'profile': profile,
                                                 'runtime': self.runtime_digests[paths]})
                self.reasons[identity] = 'miss'
            except (KeyError, ValueError, TypeError, OSError):
                continue
        if any(self.keys.values()):
            directory = cache_directory or controls.get('VELDO_GATE_CACHE')
            if not directory:
                directory = R.E.configuration()[1]['store']
            self.store = R.Store(directory, root)

    def lookup(self, case, validate):
        identity = case['identity']
        key = self.keys[identity]
        record = self.store.get(key) if key and self.store else None
        if record is not None:
            # Validation enriches the in-memory verdict. Preserve the authenticated
            # bytes' digest for audit/landing bindings, including older cache records.
            self.authenticated_digests[identity] = R.E.digest(record)
            try:
                validate(record, case)
                if record['input_digest'] != self.base_digest:
                    raise ValueError('record input identity differs')
            except Exception as error:
                if getattr(error, 'code', None) == 'mutation_budget_exceeded':
                    raise
                self.reasons[identity] = 'invalid_record'
            else:
                self.hits[identity] = record
                self.reasons[identity] = 'hit'
                return record
        return None

    def mark_stale(self, case, reason):
        """Legacy whole-tree profiles also revoke authority records on an audit mismatch."""
        identity = case['identity']
        mark_stale(self.store, identity=identity, declaration=self.source_digest,
                   gate_run=self.base_digest, reason=reason)
        self.keys[identity] = None
        self.hits.pop(identity, None)
        self.reasons[identity] = 'declaration_stale'

    def unchanged(self):
        try:
            return all(runtime_identity(paths, self.environment) == before
                       for paths, before in self.runtime_checks.items())
        except (OSError, ValueError):
            return False

    def publish(self, case, record, validate):
        key = self.keys[case['identity']]
        if not key or not self.store:
            return False
        try:
            validate(record, case)
            if record.get('input_digest') != self.base_digest:
                return False
            # Free-text failure details (paths, messages) never enter the stored record, so
            # two valid runs of the same inputs publish identical bytes.
            stored = dict(record, **{mode: {k: v for k, v in record[mode].items() if k != 'failed_details'}
                                     for mode in ('baseline', 'noop', 'mutant')})
            validate(stored, case)

            def accept(existing):
                try:
                    validate(existing, case)
                except Exception:
                    return False
                return existing.get('input_digest') == self.base_digest
            return self.store.put(key, stored, accept)
        except Exception as error:
            if getattr(error, 'code', None) == 'mutation_budget_exceeded':
                raise
            return False

    def evidence(self, case, record, reused):
        return dict(record, reuse_key=self.keys[case['identity']],
                    source='reused' if reused else 'fresh', reuse_reason=self.reasons[case['identity']])


SCOPED_RESULT = 'veldo.mutation-result/v2'
CONTROL_RECORD = 'veldo.suite-controls/v1'
KILL_RECORD = 'veldo.mutation-kill/v1'


def change_module():
    return R._sibling('gate_changes')


def suite_identity(case, configuration):
    """Sharing is by suite, leg, runtime and fixture configuration, across modules."""
    C = change_module()
    C.require(configuration['leg'] in ('confined', 'unconfined') and
              C.hex_id(configuration['runtime_digest']) and isinstance(configuration['fixture_configuration'], dict),
              'suite configuration')
    return dict(suite=case['suite'], leg='confined' if case.get('confined_only') is True else configuration['leg'],
                runtime=configuration['runtime_digest'],
                fixture=configuration['fixture_configuration'])


def control_rows(record, cases):
    """Controls prove every row and every case's target wiring before any mutant starts."""
    honest, noop = record['baseline'], record['noop']
    for value in (honest, noop):
        rows = value['observations']
        if (not rows or value['count'] != len(rows) or value['row_names'] != [n for n, _ in rows]
                or any(ok is not True for _, ok in rows) or len({n for n, _ in rows}) != len(rows)
                or any(value.get(k) for k in ('watchdog_fired', 'hung_rows', 'not_run_rows', 'failed_rows'))):
            raise ValueError('control_failed')
    if honest['observations'] != noop['observations']:
        raise ValueError('control_failed')
    for case in cases:
        for target in case['rows']:
            if [ok for name, ok in honest['observations'] if name.split()[-1] == target] != [True]:
                raise ValueError('missing control target')
    return honest['row_names']


def authenticated_controls(store, key, suite, cases):
    C = change_module()
    record = C.referenced(store, key, CONTROL_RECORD,
                          ('suite', 'cases', 'source_commit', 'dependency', 'baseline', 'noop'))
    C.require(record['suite'] == suite and record['cases'] == sorted(cases, key=lambda c: c['identity']),
              'control identity')
    C.validate_dependency(record['dependency'])
    C.require(record['source_commit'] == record['dependency']['observed_commit'], 'control source')
    control_rows(record, cases)
    return record


class SuiteControls:
    """One control pair per compatible suite per gate, including dependency-based carry."""
    def __init__(self, store, changed, source_commit):
        self.store, self.changed, self.source_commit = store, changed, source_commit
        self.results = {}

    def get(self, suite, cases, execute, prior=None):
        C = change_module()
        key = C.digest(suite)
        if key in self.results:
            C.require(self.results[key]['cases'] == sorted(cases, key=lambda c: c['identity']), 'control membership')
            return self.results[key]
        record = None
        if prior is not None and self.changed is not None:
            try:
                previous = authenticated_controls(self.store, prior, suite, cases)
                dependency = previous['dependency']
                if (dependency['complete'] and dependency['runtime_digest'] == suite['runtime'] and
                        not C.intersects(dependency, self.changed)):
                    record = previous
            except (OSError, ValueError, KeyError, TypeError):
                pass
        if record is None:
            baseline, noop, dependency = execute(cases)
            C.validate_dependency(dependency)
            C.require(dependency['observed_commit'] == self.source_commit, 'fresh control source')
            record = C.sealed(CONTROL_RECORD, suite=suite, cases=sorted(cases, key=lambda c: c['identity']),
                              source_commit=self.source_commit, dependency=dependency, baseline=baseline, noop=noop)
            control_rows(record, cases)
            C.require(self.store.change_put(record), 'control publication')
        self.results[key] = record
        return record


def prior_killing_rows(store, key, case, validate):
    if key is None:
        return None
    C = change_module()
    try:
        prior = C.referenced(store, key, KILL_RECORD, ('source_commit', 'dependency', 'result'))
        C.validate_dependency(prior['dependency'])
        C.require(prior['source_commit'] == prior['dependency']['observed_commit'], 'kill source')
        result = prior['result']
        validate(result, case)
        rows = [entry['row'] for entry in result['kills'] if entry['kill_by'] in ('assertion', 'terminal')]
        C.require(rows and len(rows) == len(set(rows)), 'unusable prior kills')
        return rows
    except Exception as error:
        if isinstance(error, (OSError, ValueError, KeyError, TypeError, RuntimeError)) or getattr(error, 'code', None) in (
                'control_failed', 'hung_not_killed', 'missing_target', 'mutation_survived', 'driver_error'):
            return None
        raise


def selected_mutation(case, controls, execute, validate, *, store, prior=None):
    """Try authenticated killing rows, then the suite. Failed controls stop first."""
    control_rows(controls, [case])
    rows = prior_killing_rows(store, prior, case, validate)
    attempts = []
    for selected in ([rows, None] if rows else [None]):
        result = execute(selected)
        # Unsupported row bodies explicitly request fallback before executing them.
        if result is None and selected is not None:
            attempts.append(dict(execution_scope='rows', selected_rows=selected, unavailable=True))
            continue
        result.update(schema=SCOPED_RESULT, execution_scope='rows' if selected else 'suite',
                      selected_rows=selected or [], observed_rows=result['mutant']['row_names'],
                      prior_kill_receipt_digest=prior if rows else None,
                      control_receipt_digest=controls['record_digest'],
                      baseline=controls['baseline'], noop=controls['noop'])
        attempt = dict(execution_scope=result['execution_scope'], selected_rows=selected or [],
                       observation=result['mutant'])
        attempts.append(attempt)
        result['attempts'] = list(attempts)
        try:
            validate(result, case)
            return result
        except Exception as error:
            # Hangs, incomplete execution and invalid evidence are never kills.
            # Only a complete survivor qualifies for the ordinary fallback.
            if selected is None or getattr(error, 'code', None) != 'mutation_survived':
                raise
    raise ValueError('mutation_survived')
