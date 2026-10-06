"""Conservative mutation reuse admission. Unknown external closure always runs fresh.

Profiles are reviewed qualifications, never inferred from a passing run or an observed
read trace. Their repository digest pins every byte whose behavior was reviewed.
"""
import hashlib
import importlib.util
import json
import os
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


class Session:
    def __init__(self, root, files, cases, head, configuration, *, force_fresh=False,
                 environment=None, cache_directory=None):
        self.root, self.files = Path(root), files
        controls = os.environ if environment is None else environment
        self.environment = dict(configuration.get('worker_environment', {}) if environment is None else environment)
        parsed_force = truthy(controls.get('VELDO_GATE_FORCE_FRESH', '0'))
        self.forced = force_fresh or parsed_force
        self.keys, self.reasons, self.hits = {}, {}, {}
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
