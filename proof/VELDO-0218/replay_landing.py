"""Replay the existing landing contract assertions without their unrelated kernel setup.

This executes the exact block in suite 101, not a second implementation of its assertions.
The real store, signatures, reducer and both landing validators use controlled observations.
"""
import copy
import importlib.util
import json
import tempfile
import textwrap
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def load(relative):
    spec = importlib.util.spec_from_file_location('replay_' + Path(relative).stem, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    E = load('.veldo/reuse_evidence.py')
    R = load('scripts/gate_reuse.py')
    gate = load('scripts/check_gate_mutations.py')
    reducer = load('scripts/reuse_stamp.py')
    landing = load('engine/.veldo/control_verification.py')
    assertions = []
    def expect(name, condition):
        assertions.append((name, bool(condition)))
        assert condition, name
    with tempfile.TemporaryDirectory(prefix='v218-landing-replay-') as temporary:
        top = Path(temporary)
        worktree, storepath = top / 'candidate', top / 'store'
        worktree.mkdir()
        store = R.Store(storepath, worktree)
        config = top / 'config.json'
        config.write_text(json.dumps(dict(schema='veldo.agent-sandbox/v1', store=str(storepath))))
        case = dict(identity='check_teeth_mutations.py:fixture', name='fixture',
                    driver='check_teeth_mutations.py', rows=['target'], suite='fixture.py',
                    module='subject.py', old='good', new='bad')
        key = E.digest(case)
        observation = lambda ok: dict(observations=[['fixture target', ok]], count=1,
            row_names=['fixture target'], failed_rows=[] if ok else ['fixture target'])
        record = dict(schema=gate.SCHEMA, case=case, fixture_version=gate.FIXTURE_VERSION,
            input_digest=key, replacement_count=1, old_digest='a', new_digest='b',
            baseline=observation(True), noop=observation(True), mutant=observation(False), elapsed=.1)
        assert store.put(key, record)
        path = storepath / (key + '.json')
        raw = path.read_bytes()
        payload = json.loads(raw)['payload']
        legacy = dict(payload)
        legacy.pop('provenance')
        source = (ROOT / 'scripts/suites/101_veldo_0208_landing_reuse.py').read_text()
        start = source.index("        commit = 'a' * 40\n        receipt = dict(")
        end = source.index('            # Drive the real shell guard;', start)
        block = textwrap.dedent(source[start:end])
        namespace = dict(globals(), **locals())
        exec(compile(block, 'suite-101-landing-block', 'exec'), namespace)
        print('landing fixture replay: %d passed, 0 failed' % len(assertions))
        print('Replayed existing assertions: ' + ', '.join(name for name, _ in assertions))


if __name__ == '__main__':
    main()
