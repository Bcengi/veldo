"""Per-case reuse keys; traces propose, declared snapshots enforce the inputs."""
import hashlib
import json
import os
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

# A reviewed toolchain may only name system trees: never the checkout, the store or a home.
SYSTEM_ROOTS = ('/usr', '/lib', '/lib64', '/etc')
REVIEW_SCHEMA = 'veldo.case-input-review/v1'
# Review records live only under the protected tree (.veldo/policy.yaml, floor high), and a reviewed
# declaration binds the exact bytes of the record it names (review_sha256, VELDO-0217 F4).
REVIEW_DIRECTORY = 'proof/VELDO-0217/reviews/'
SENSITIVITY_SCHEMA = 'veldo.sensitivity-proof/v1'


def declaration_digest(declaration):
    """What a review record binds: the declaration without its reviewed flag and record binding."""
    return R.digest({k: v for k, v in declaration.items() if k not in ('reviewed', 'review', 'review_sha256')})


def observation_digest(observation):
    """An observation without its free-text failure details, as the store keeps it."""
    return R.digest({k: v for k, v in observation.items() if k != 'failed_details'})


def sensitivity_proved(directory, key):
    """VELDO-0226's clock and randomness proof for this exact key, in the authority store:
    <store>/sensitivity/<key>.json naming the key. Until that proof exists, no key qualifies."""
    try:
        record = json.loads((Path(directory) / 'sensitivity' / (key + '.json')).read_bytes())
    except (OSError, ValueError):
        return False
    return isinstance(record, dict) and record.get('schema') == SENSITIVITY_SCHEMA and record.get('key') == key


class Unavailable(Exception):
    """An environment or store fault, not a finding about the declaration (review N3): the case
    runs fresh in this gate and no authority mark outlives the fault."""


def review_matches(files, name, declaration):
    """The declaration names a review record under proof/VELDO-0217/reviews/ and binds its sha256;
    the record's entry for this case binds this declaration's digest and its proposal's trace
    digests, with a reviewer and a commit. A record anywhere else, or with other bytes, grants nothing."""
    try:
        path = I.safe_name(declaration['review'])
        if not path.startswith(REVIEW_DIRECTORY):
            return False
        body = files[path][1]
        if hashlib.sha256(body).hexdigest() != declaration['review_sha256']:
            return False
        record = json.loads(body)
        entry = record['cases'][name]
        return (record['schema'] == REVIEW_SCHEMA and isinstance(record['reviewer'], str)
                and record['reviewer'].strip() and isinstance(record['commit'], str) and record['commit'].strip()
                and entry['declaration'] == declaration_digest(declaration)
                and entry['traces'] == [run['trace'] for run in declaration['proposal']['runs']])
    except (KeyError, TypeError, ValueError):
        return False


def failed_condition(files, name, declaration):
    """The first mechanical condition of VELDO-0217 AC2 a reviewed declaration fails, or None. The
    reviewer judges the rationale only; everything else is checked here, from the proposal."""
    if not review_matches(files, name, declaration):
        return 'review_mismatch'
    try:
        runs = declaration['proposal']['runs']
        if {run['mode'] for run in runs} != {'baseline', 'noop', 'mutant'} or any(run['exit'] != 0 for run in runs):
            return 'trace_failed'
        for run in runs:
            if run['non_file']:
                return sorted(run['non_file'])[0]
        if declaration['non_file_inputs'] != 'none':
            return 'non_file_unreviewed'
    except (KeyError, TypeError):
        return 'trace_failed'
    if not isinstance(declaration.get('rationale'), str) or not declaration['rationale'].strip():
        return 'no_rationale'
    return None


class Session(M.Session):
    @classmethod
    def for_changes(cls, root, store, repository, commit, inventory, runtimes):
        changes = M.change_module()
        changes.require(changes.SELECTION_ENABLED, 'change selection is inactive until increment 5')
        return ChangeSession(root, store, repository, commit, inventory, runtimes)

    def __init__(self, root, files, cases, head, configuration, *, force_fresh=False,
                 environment=None, cache_directory=None):
        # Retain v1 receipt methods, but never admit a whole-tree profile here.
        unqualified = dict(files)
        unqualified.pop(M.PROFILE, None)
        super().__init__(root, unqualified, cases, head, configuration, force_fresh=force_fresh,
                         environment=environment, cache_directory=cache_directory)
        self.snapshots, self.declarations, self.case_digests, self.runtimes = {}, {}, {}, {}
        self.runtime_absent = {}
        self.stale = {}
        self.unavailable = {}
        self.gate_run = os.urandom(16).hex()
        self.reviewed = {}
        try:
            document = json.loads(files[I.DECLARATIONS][1])
            if document['schema'] != 'veldo.case-inputs/v1':
                raise ValueError('unknown declaration schema')
        except (KeyError, ValueError, TypeError):
            document = {'cases': {}, 'toolchains': {}}
        controls = os.environ if environment is None else environment
        directory = []

        def store_directory():
            if not directory:
                directory.append(cache_directory or controls.get('VELDO_GATE_CACHE')
                                 or R.E.configuration()[1]['store'])
            return directory[0]
        self.store_directory = store_directory
        marks = None
        for case in cases:
            name = case['identity']
            self.case_digests[name] = self.base_digest
            declaration = document['cases'].get(name)
            if declaration is None:
                continue
            try:
                # Proposals alone grant no reuse and do not alter fresh behavior.
                if not isinstance(declaration, dict) or declaration.get('reviewed') is not True:
                    self.reasons[name] = 'unreviewed_declaration'
                    continue
                self.reviewed[name] = declaration
                if marks is None:
                    # Marks that cannot be read deny reuse for every declared case: an
                    # unreachable store never turns into reuse.
                    try:
                        marks = {(entry['identity'], entry['declaration']): entry
                                 for entry in M.stale_entries(store_directory())}
                    except (KeyError, TypeError, ValueError, OSError, RuntimeError) as error:
                        marks = 'stale marks unreadable: ' + str(error)
                if isinstance(marks, str):
                    raise Unavailable(marks)
                prior = marks.get((name, declaration_digest(declaration)))
                if prior is not None:
                    self.mark_stale(case, prior['reason'], prior=prior)
                    continue
                toolchain = document['toolchains'][case['driver']]
                runtime = tuple(toolchain['paths'])
                absent_runtime = tuple(toolchain.get('absent', []))
                for path in absent_runtime:
                    if not Path(path).is_absolute() or Path(path).exists() or Path(path).is_symlink():
                        raise ValueError('expected absent runtime input: ' + path)
                # Runtime grants cannot expose the original repository, cache, or arbitrary homes.
                for path in runtime:
                    resolved = Path(path).resolve()
                    if not any(resolved == Path(p).resolve() or Path(p).resolve() in resolved.parents
                               for p in SYSTEM_ROOTS):
                        raise ValueError('runtime outside approved system roots')
                chosen = I.selected(files, case, declaration)
                if I.gate_entries(chosen):
                    # A suite that starts a gate is never declared (VELDO-0210 AC7): its gate nests in
                    # a fresh worker's tree, which no tracer may follow, so its cases run fresh.
                    self.reasons[name] = 'starts_a_gate'
                    continue
                # VELDO-0217 AC2: every mechanical condition, each failure named; the case runs fresh.
                reason = failed_condition(files, name, declaration)
                if reason is None and toolchain.get('reviewed') is not True:
                    reason = 'toolchain_unreviewed'
                if reason is not None:
                    self.reasons[name] = reason
                    continue
                self.runtime_absent[name] = absent_runtime
                if runtime not in self.runtime_checks:
                    try:
                        identity = M.runtime_identity(runtime, self.environment)
                    except (KeyError, TypeError, ValueError, OSError, RuntimeError) as error:
                        raise Unavailable('runtime identity: ' + str(error)) from error
                    self.runtime_checks[runtime] = identity
                    self.runtime_digests[runtime] = R.digest(identity)
                # VELDO-0217 AC3: the support helpers the suite loads are keyed as their own part.
                loaded = set(I.helpers(files, I.prerequisites(files, case)))
                # The record digest is approval, not an input: re-approving a batch record (which
                # rebinds every declaration it covers) leaves each case's key unchanged.
                keyed_declaration = {k: v for k, v in declaration.items() if k != 'review_sha256'}
                value = {'schema': 'veldo.case-key/v1',
                         'files': I.identity({n: v for n, v in chosen.items() if n not in loaded}),
                         'helpers': I.identity({n: v for n, v in chosen.items() if n in loaded}),
                         'case': case, 'declaration': keyed_declaration, 'toolchain': toolchain,
                         'runtime': self.runtime_digests[runtime], 'configuration': configuration,
                         'authority': R.E.authority_identity()}
                self.case_digests[name] = R.digest(value)
                if self.forced:
                    self.reasons[name] = 'force_fresh'
                    self.snapshots[name], self.declarations[name], self.runtimes[name] = chosen, declaration, runtime
                    continue
                try:
                    store_directory()
                except (KeyError, TypeError, ValueError, OSError, RuntimeError) as error:
                    raise Unavailable('store configuration: ' + str(error)) from error
                if not sensitivity_proved(store_directory(), self.case_digests[name]):
                    self.reasons[name] = 'sensitivity_unproved'
                    continue
                self.snapshots[name], self.declarations[name], self.runtimes[name] = chosen, declaration, runtime
                self.keys[name] = self.case_digests[name]
                self.reasons[name] = 'miss'
            except Unavailable as fault:
                # Fresh for this gate only; nothing is marked, so reuse returns with the store.
                self.reasons[name] = 'reuse_unavailable'
                self.unavailable[name] = str(fault)
                self.runtime_absent.pop(name, None)
            except (KeyError, TypeError, ValueError, OSError) as error:
                self.mark_stale(case, 'declaration no longer closes: ' + str(error))
        if any(self.keys.values()):
            self.store = R.Store(store_directory(), root)

    def mark_stale(self, case, reason, prior=None):
        """Discard the whole declared attempt. Its replacement runs fresh and cannot publish.

        The in-session effects never depend on the store: an unavailable store only means the
        finding is not persisted (reported as persisted false), never a red stage or reuse.
        A finding read from an earlier mark is not written again (review N4)."""
        name = case['identity']
        if name in self.stale:
            return
        self.keys[name] = None
        self.hits.pop(name, None)
        self.reasons[name] = 'declaration_stale'
        self.snapshots.pop(name, None)
        self.runtime_absent.pop(name, None)
        entry = dict(identity=name, declaration=declaration_digest(self.reviewed[name]),
                     gate_run=self.gate_run, reason=reason)
        if prior is not None:
            entry.update(gate_run=prior['gate_run'], reason=prior['reason'], persisted=True, prior=True)
        else:
            try:
                if self.store is None:
                    self.store = R.Store(self.store_directory(), self.root)
                M.mark_stale(self.store, **entry)
                entry['persisted'] = True
            except (KeyError, TypeError, ValueError, OSError, RuntimeError) as error:
                entry.update(persisted=False, persist_error=str(error))
        self.stale[name] = entry

    def withhold(self, case, reason):
        """A run that would publish showed a non-file input (VELDO-0217 AC4): the case stays fresh
        with that class as its reason, and nothing is published under its key."""
        self.keys[case['identity']] = None
        self.reasons[case['identity']] = reason

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


class ChangeSession:
    """Dependency selection has no declaration/profile, full-tree key or audit gate."""
    def __init__(self, root, store, repository, commit, inventory, runtimes):
        self.changes = M.change_module()
        self.plan = self.changes.select(root, store, repository, commit, inventory, runtimes)

    def dispatch(self, execute):
        return self.changes.dispatch(self.plan, execute)
