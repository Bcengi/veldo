"""Run only suite 107, sequentially, with the refusal mutant in a disposable TMPDIR copy.

Exit zero means the three unit rows rejected the mutant and accepted the restored code.
It does not mean the integration suite completed; every suite exit is recorded separately.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def assess(observations, names):
    """Required unit kills remain mandatory; sockets may expose additional integration kills."""
    labels = {'SELFTEST FAIL: VELDO-0153 refusal-unit/' + name for name in names}
    rejected = labels.issubset(observations['red']['failures'])
    eager_rejected = ('SELFTEST FAIL: VELDO-0153 profile/isolated-without-identity-asset'
                      in observations['eager']['failures'])
    restored = (observations['green']['failures'] == [] and observations['green']['unit_observations']
                == dict.fromkeys(names, 'binding_mismatch:identity_transport_config'))
    return rejected, eager_rejected, restored


def main(output):
    root = Path(__file__).resolve().parents[2]
    names = ('route-insteadof', 'route-push-instead-of', 'shape-config-exit')
    observations = {}
    with tempfile.TemporaryDirectory(prefix='v153-refusal-', dir=os.environ['TMPDIR']) as directory:
        scratch = Path(directory)
        checkout = scratch / 'checkout'
        shutil.copytree(root, checkout, ignore=shutil.ignore_patterns('.git', '__pycache__'))
        temporary = scratch / 'tmp'
        temporary.mkdir()
        sources = [checkout / prefix / 'git_process.py' for prefix in ('.veldo', 'engine/.veldo')]
        originals = {path: path.read_text() for path in sources}
        for mode in ('red', 'eager', 'green'):
            for path, source in originals.items():
                anchor = '        return _IDENTITY_TRANSPORT\n'
                if source.count(anchor) != 1:
                    raise AssertionError('refusal module anchor is not unique')
                if mode == 'red':
                    source = source.replace(anchor, '        return _load_identity_transport()\n')
                elif mode == 'eager':
                    source = source.replace('_IDENTITY_TRANSPORT = None\n',
                                            '_IDENTITY_TRANSPORT = _load_identity_transport()\n')
                path.write_text(source)
            command = [sys.executable, 'scripts/selftest.py', '--suite', '107_veldo_0153_identity_push']
            log_path = scratch / (mode + '.log')
            with log_path.open('w') as log:
                result = subprocess.run(command, cwd=checkout, env=dict(os.environ, TMPDIR=str(temporary)),
                                        stdout=log, stderr=subprocess.STDOUT, timeout=120)
            lines = log_path.read_text().splitlines()
            failures = [line.strip() for line in lines if 'SELFTEST FAIL:' in line]
            observed = next((json.loads(line.split(': ', 1)[1]) for line in lines
                             if line.startswith('VELDO-0153 refusal unit observations: ')), None)
            observations[mode] = dict(command=command, exit=result.returncode, failures=failures,
                                      unit_observations=observed,
                                      infrastructure=[line for line in lines if 'PermissionError:' in line],
                                      summary=[line for line in lines if line.startswith('selftest (PARTIAL')])
    rejected, eager_rejected, restored = assess(observations, names)
    record = dict(scope='three refusal unit rows only; no aggregate suite or host claim',
                  mutant='identity153-refusal-module-identity', rejected=rejected,
                  eager_mutant='identity153-eager-transport', eager_rejected=eager_rejected,
                  restored=restored, runs=observations)
    Path(output).write_text(json.dumps(record, indent=2) + '\n')
    print('refusal unit falsifiers: rejected=%s eager_rejected=%s restored=%s; suite exits=%s' % (
        rejected, eager_rejected, restored, {mode: run['exit'] for mode, run in observations.items()}))
    return 0 if rejected and eager_rejected and restored else 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1]))
