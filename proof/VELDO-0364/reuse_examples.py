"""Single-case unit fixture: real transitive reads, materializer, keys and authenticated store.

Review/sensitivity admission and runtime identity are fixture seams, NOT production
qualification. No record is written to the owner's store. The absent native sensitivity
producer is reported separately, never replaced by this fixture's admission seam.
"""
import importlib.util
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    C, G, D = (load(n) for n in ('case_reuse', 'check_gate_mutations', 'check_teeth_mutations'))
    case = dict(name='transitive', identity='check_teeth_mutations.py:transitive',
                driver='check_teeth_mutations.py', suite='fixture.py', module='subject.py',
                old='return answer', new='return False', rows=['target'])
    files = {n: ((ROOT / n).stat().st_mode & 0o777, (ROOT / n).read_bytes())
             for n in (*C.I.MANDATORY, *C.I.DRIVERS)}
    files.update({
        '.veldo/subject.py': (0o644, b'''from pathlib import Path
def value():
    namespace = {}
    exec(Path(__file__).with_name('dependency.py').read_text(), namespace)
    answer = namespace['answer']
    return answer
'''),
        '.veldo/dependency.py': (0o644, b'answer = True\n'),
        'product-ui.txt': (0o644, b'unrelated product view\n'),
        'scripts/suites/shared.py': (0o644, b'''from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
def expect(name, condition):
    pass
'''),
        'scripts/suites/fixture.py': (0o644, b'''import importlib.util
source = ROOT / ".veldo" / "subject.py"
spec = importlib.util.spec_from_file_location('subject', source)
subject = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subject)
expect('fixture target', subject.value() is True)
''')})
    declaration = {'files': ['.veldo/dependency.py'], 'directories': [], 'absent': [],
                   'reviewed': True, 'non_file_inputs': 'none', 'rationale': 'Controlled unit fixture only.'}
    files[C.I.DECLARATIONS] = (0o644, C.R.canonical({'schema': 'veldo.case-inputs/v1',
        'toolchains': {case['driver']: {'paths': ['/usr/bin/python3'], 'reviewed': True}},
        'cases': {case['identity']: declaration}}))
    results = {}
    with tempfile.TemporaryDirectory(prefix='v364-transitive-') as temporary:
        top = Path(temporary)
        root = top / 'candidate'
        root.mkdir()
        def session(source, *, fresh=False):
            with patch.object(C, 'failed_condition', return_value=None), \
                 patch.object(C, 'sensitivity_proved', return_value=True), \
                 patch.object(C.M, 'runtime_identity', return_value={'fixture': 'fixed'}):
                return C.Session(root, source, [case], 'fixture-head', {}, force_fresh=fresh,
                                 cache_directory=top / 'store')

        def execute(source, current, name):
            candidate = top / name
            candidate.mkdir()
            for n, (mode, body) in source.items():
                p = candidate / n
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(body)
                p.chmod(mode)
            D.ROOT = candidate
            record = dict(schema=G.SCHEMA, fixture_version=G.FIXTURE_VERSION,
                          case=case, input_digest=current.input_digest(case))
            for mode in ('baseline', 'noop', 'mutant'):
                made = D.materialize(case, mode, top / (name + '-' + mode), root=candidate)
                record[mode] = D.worker(case, str(made['mutant']) if made['mutant'] else None)
                if mode == 'mutant':
                    record.update({k: made[k] for k in ('replacement_count', 'old_digest', 'new_digest')})
            G.validate_result(record, case)
            return record

        cold = session(files)
        record = execute(files, cold, 'original')
        assert cold.publish(case, record, G.validate_result)
        unrelated = dict(files, **{'product-ui.txt': (0o644, b'ordinary UI edit\n')})
        hit = session(unrelated)
        stored = dict(record, **{m: {k: v for k, v in record[m].items() if k != 'failed_details'}
                                for m in ('baseline', 'noop', 'mutant')})
        results['unrelated_edit_hit'] = hit.lookup(case, G.validate_result) == stored
        transitive = dict(files, **{'.veldo/dependency.py': (0o644, b'answer = bool(1)\n')})
        miss = session(transitive)
        results['transitive_dependency_miss'] = (miss.input_digest(case) != cold.input_digest(case)
                                                and miss.lookup(case, G.validate_result) is None)
        forced = session(unrelated, fresh=True)
        repeated = execute(unrelated, forced, 'forced')
        results['forced_fresh_equivalence'] = (forced.lookup(case, G.validate_result) is None
            and all(repeated[m] == record[m] for m in ('baseline', 'noop', 'mutant'))
            and not forced.publish(case, repeated, G.validate_result))
        path = top / 'store' / (cold.keys[case['identity']] + '.json')
        path.write_text('{}')
        results['corrupted_record_miss'] = session(files).lookup(case, G.validate_result) is None
    assert all(results.values()), results
    output = dict(scope='single-case unit fixture; review, runtime and sensitivity admission stood in',
                  results=results, production_sensitivity='NOT PROVED; missing runner/library')
    Path(__file__).with_suffix('.json').write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps(output))


if __name__ == '__main__':
    main()
