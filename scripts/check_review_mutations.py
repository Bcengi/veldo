#!/usr/bin/env python3
"""Drive the five reviewed false-green rows against defective copies, without editing the checkout."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

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


def cases():
    return [dict(name=key, finding=key, suite=suite, module=module,
                 rows=[label], old=old, new=new)
            for key, (suite, module, label, old, new) in CASES.items()]


def worker(case, mutant):
    from check_teeth_mutations import worker as observe
    definition = next(c for c in cases() if c['name'] == case)
    result = observe(definition, mutant)
    matches = result['targets'][definition['rows'][0]]
    return dict(result, case=case, row=definition['rows'][0],
                matched=len(matches), passed=matches == [True])


def main():
    from check_teeth_mutations import materialize
    if len(sys.argv) > 1:
        print(json.dumps(worker(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)))
        return
    results = []
    with tempfile.TemporaryDirectory(prefix='review-mutants-') as directory:
        for definition in cases():
            case, label, new = definition['name'], definition['rows'][0], definition['new']
            mutant = materialize(definition, 'mutant', Path(directory) / case)['mutant']
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
