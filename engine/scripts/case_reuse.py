"""Per-case reuse keys; traces propose, declared snapshots enforce the inputs."""
import json
from pathlib import Path
import importlib.util


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


I = load('case_inputs')
M = load('mutation_reuse')
R = M.R


class Session(M.Session):
    def __init__(self, root, files, cases, head, configuration, *, force_fresh=False,
                 environment=None, cache_directory=None):
        # Retain v1 receipt methods, but never admit a whole-tree profile here.
        unqualified = dict(files)
        unqualified.pop(M.PROFILE, None)
        super().__init__(root, unqualified, cases, head, configuration, force_fresh=force_fresh,
                         environment=environment, cache_directory=cache_directory)
        self.snapshots, self.declarations, self.case_digests, self.runtimes = {}, {}, {}, {}
        self.runtime_absent = {}
        try:
            document = json.loads(files[I.DECLARATIONS][1])
            if document['schema'] != 'veldo.case-inputs/v1':
                raise ValueError('unknown declaration schema')
        except (KeyError, ValueError, TypeError):
            document = {'cases': {}, 'toolchains': {}}
        for case in cases:
            name = case['identity']
            self.case_digests[name] = self.base_digest
            declaration = document['cases'].get(name)
            if declaration is None:
                continue
            try:
                # Proposals alone grant no reuse and do not alter fresh behavior.
                if declaration.get('reviewed') is not True:
                    self.reasons[name] = 'unreviewed_declaration'
                    continue
                if declaration['non_file_inputs'] != 'none' or not declaration['rationale'].strip():
                    raise ValueError('non-file inputs are not qualified')
                toolchain = document['toolchains'][case['driver']]
                if toolchain.get('reviewed') is not True:
                    raise ValueError('toolchain is not reviewed')
                runtime = tuple(toolchain['paths'])
                absent_runtime = tuple(toolchain.get('absent', []))
                for path in absent_runtime:
                    if not Path(path).is_absolute() or Path(path).exists() or Path(path).is_symlink():
                        raise ValueError('expected absent runtime input: ' + path)
                self.runtime_absent[name] = absent_runtime
                # Runtime grants cannot expose the original repository, cache, or arbitrary homes.
                for path in runtime:
                    resolved = Path(path).resolve()
                    if not any(resolved == Path(p).resolve() or Path(p).resolve() in resolved.parents
                               for p in ('/usr', '/lib', '/lib64', '/etc')):
                        raise ValueError('runtime outside approved system roots')
                if runtime not in self.runtime_checks:
                    self.runtime_checks[runtime] = M.runtime_identity(runtime, self.environment)
                    self.runtime_digests[runtime] = R.digest(self.runtime_checks[runtime])
                chosen = I.selected(files, case, declaration)
                self.snapshots[name], self.declarations[name], self.runtimes[name] = chosen, declaration, runtime
                value = {'schema': 'veldo.case-key/v1', 'files': I.identity(chosen), 'case': case,
                         'declaration': declaration, 'toolchain': toolchain,
                         'runtime': self.runtime_digests[runtime], 'configuration': configuration,
                         'authority': R.E.authority_identity()}
                self.case_digests[name] = R.digest(value)
                if not self.forced:
                    self.keys[name] = self.case_digests[name]
                    self.reasons[name] = 'miss'
            except (KeyError, TypeError, ValueError, OSError) as error:
                # A reviewed declaration that no longer closes fails, never falls back silently.
                raise ValueError('invalid declaration for ' + name + ': ' + str(error)) from error
        if any(self.keys.values()):
            import os
            controls = os.environ if environment is None else environment
            directory = cache_directory or controls.get('VELDO_GATE_CACHE')
            if not directory:
                directory = R.E.configuration()[1]['store']
            self.store = R.Store(directory, root)

    def unchanged(self):
        return (super().unchanged() and all(not Path(p).exists() and not Path(p).is_symlink()
                for paths in self.runtime_absent.values() for p in paths))

    def input_digest(self, case):
        return self.case_digests[case['identity']]

    def lookup(self, case, validate):
        before = self.base_digest
        self.base_digest = self.input_digest(case)
        try:
            return super().lookup(case, validate)
        finally:
            self.base_digest = before

    def publish(self, case, record, validate):
        before = self.base_digest
        self.base_digest = self.input_digest(case)
        try:
            return super().publish(case, record, validate)
        finally:
            self.base_digest = before

    def prepare(self, case, parent):
        name = case['identity']
        if name not in self.snapshots:
            return {}
        destination = Path(parent) / R.digest(name)
        I.freeze(destination, self.snapshots[name])
        for directory in self.declarations[name].get('directories', []):
            (destination / I.safe_name(directory)).mkdir(parents=True, exist_ok=True)
        return {'snapshot_root': str(destination), 'runtime_paths': self.runtimes[name],
                'declared_files': sorted(self.snapshots[name]),
                'declared_absent': self.declarations[name].get('absent', []),
                'declared_directories': self.declarations[name].get('directories', []),
                'runtime_absent': self.runtime_absent[name]}
