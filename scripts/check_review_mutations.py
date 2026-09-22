#!/usr/bin/env python3
"""Drive the five reviewed false-green rows against defective copies, without editing the checkout."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
CASES = {
    '13': ('44_veldo_0105_startline.py', 'fix_validation_record.py',
           'proofcheck/unanswerable-ancestry-fails-closed',
           '    if r.returncode == 0:\n        return True',
           '    if r.returncode == 1:\n        return False\n    if r.returncode == 0:\n        return True'),
    '14': ('47_veldo_0107_ipc.py', 'control_client.py',
           'ipc/transport-and-command-are-checked-separately',
           '        if not self.verify(signed_bytes(request), request["signature"]):',
           '        if not self.verify(signed_bytes(request), request["signature"]):\n            self.apply(request["command"])'),
    '15': ('48_veldo_0108_relay.py', 'control_relay.py',
           'relay/the-authority-judges-not-the-relay',
           '        payload = read_all(stdin)',
           '        payload = read_all(stdin)\n        import json\n        payload = json.dumps(json.loads(payload)).encode()'),
    '16': ('48_veldo_0108_relay.py', 'control_relay.py',
           'relay/an-unreachable-authority-is-reported-not-answered',
           '        return EXIT_UNREACHABLE',
           '        stdout.write(b"{}")\n        return EXIT_UNREACHABLE'),
    '17': ('49_veldo_0109_unavailable.py', 'control_client.py',
           'unavailable/no-local-authority-appears',
           '            seen = last_seen(enrollment, workspace, binding)',
           '            with open(seen_path(enrollment, workspace), "a") as corrupt:\n                corrupt.write(" ")\n            seen = last_seen(enrollment, workspace, binding)'),
}


def worker(case, mutant):
    suite, module, label, _, _ = CASES[case]
    shared = ROOT / 'scripts/suites/shared.py'
    ns = {'__file__': str(shared)}
    captured = io.StringIO()
    rows = []
    with contextlib.redirect_stdout(captured):
        exec(compile(shared.read_text(), str(shared), 'exec'), ns)
        ns['expect'] = lambda name, condition: rows.append((name, bool(condition)))
        source = (ROOT / 'scripts/suites' / suite).read_text()
        if mutant:
            source = source.replace('ROOT / ".veldo" / "' + module + '"',
                                    '__import__("pathlib").Path(' + repr(mutant) + ')')
        ns['__suite_file__'] = str(ROOT / 'scripts/suites' / suite)
        exec(compile(source, ns['__suite_file__'], 'exec'), ns)
    matches = [ok for name, ok in rows if label in name]
    return {'case': case, 'row': label, 'matched': len(matches),
            'passed': matches == [True], 'failed_rows': [name for name, ok in rows if not ok]}


def main():
    if len(sys.argv) > 1:
        print(json.dumps(worker(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)))
        return
    results = []
    with tempfile.TemporaryDirectory(prefix='review-mutants-') as directory:
        for case, (_, module, label, old, new) in CASES.items():
            source = (ROOT / '.veldo' / module).read_text()
            assert source.count(old) == 1, (case, 'mutation anchor moved')
            mutant = Path(directory) / (case + '_' + module)
            mutant.write_text(source.replace(old, new))
            pair = []
            for args in ([case], [case, str(mutant)]):
                proc = subprocess.run([sys.executable, __file__, *args],
                                      capture_output=True, text=True, timeout=60)
                if proc.returncode:
                    raise RuntimeError(f'case {case} did not reach its row: {proc.stderr}')
                pair.append(json.loads(proc.stdout))
            honest, broken = pair
            assert honest['matched'] == broken['matched'] == 1, pair
            assert honest['passed'] and not honest['failed_rows'], honest
            assert not broken['passed'], broken
            result = {'finding': case, 'row': label, 'baseline': 'green', 'broken_variant': 'red',
                      'mutation': new, 'failed_rows': broken['failed_rows']}
            results.append(result)
            print(json.dumps(result), flush=True)
    print(f'{len(results)} broken variants rejected by their named rows')


if __name__ == '__main__':
    main()
