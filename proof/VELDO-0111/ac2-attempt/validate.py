"""Validate retained digests and personal-setup cleanliness without ancestry queries."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    report = json.loads((HERE / 'receipt.json').read_text())
    qualification = json.loads((HERE.parent / 'qualification.json').read_text())
    paths = dict(source_digest=ROOT / 'scripts/fixtures/lifecycle_census.py',
                 suite_digest=ROOT / 'scripts/suites/113_veldo_0111_census.py',
                 spec_digest=ROOT / 'specs/VELDO-0111-process-and-listener-census.md',
                 recheck_digest=HERE / 'recheck.py', witness_digest=HERE / 'socket_destruction.py',
                 shared_witness_digest=HERE / 'shared_memory.py', memory_aba_digest=HERE / 'memory_aba.py',
                 unconfined_declaration_digest=ROOT / 'scripts/gate_unconfined.json')
    assert report['recheck_completed'] and report['next_obligation'] is None
    assert qualification['next_obligation'] is None and qualification['acceptance']['AC2'] is False
    assert report['qualification']['gaps'] == [] and report['qualification']['reasons'] == []
    assert qualification['receipt_digest'] == sha(HERE / 'receipt.json')
    for key, path in paths.items():
        assert report[key] == sha(path), key
    for key in ('socket_destruction_witness', 'shared_memory_witness', 'memory_aba_witness'):
        assert report[key]['digest'] == sha(HERE / report[key]['evidence'])
    assert all(case['completed'] for case in report['cases'])
    for label in ('baseline', 'final-control'):
        case, = [c for c in report['cases'] if c['label'] == label]
        assert len(case['rows']) == 23 and all(ok for _, ok in case['rows'])
    for mode in ('owned', 'sendmmsg', 'imported'):
        for label in ('green', 'ignore-scm-rights', 'ignore-scm-rights-and-release'):
            case, = [c for c in report['cases'] if c['label'] == 'escaped-reference-' + mode + '-' + label]
            green = label == 'green'
            assert len(case['families']) == 4 and case['passed'] == green
            assert all(c['passed'] == green for c in case['families'])
            if green:
                assert all(c['send_attributed'] and c['referenced_after_drain'] for c in case['families'])
            if label == 'ignore-scm-rights':
                assert all(c['referenced_after_drain'] and c['capture_status'] == 'INCOMPLETE'
                           for c in case['families'])
            if label == 'ignore-scm-rights-and-release':
                assert all(not c['escape_failures'] for c in case['families'])
                if mode != 'imported':
                    assert all(c['capture_status'] == 'COMPLETE' for c in case['families'])
    green, = [c for c in report['cases'] if c['label'] == 'control-aba-green']
    red, = [c for c in report['cases'] if c['label'] == 'control-aba-ignore-release']
    assert green['passed'] and green['escaped_reference_detected'] and not green['send_decoder_attributed']
    assert not red['passed'] and red['capture_status'] == 'COMPLETE'
    maba, = [c for c in report['cases'] if c['label'] == 'memory-aba-green']
    assert maba['passed'] and all(maba['cases'].values()) and len(maba['cases']) == 3
    for label, scenario in (('trust-bind-sample', 'bind'), ('socketpair-from-memory', 'socketpair'),
                            ('trust-received-control', 'recvmsg')):
        case, = [c for c in report['cases'] if c['label'] == 'memory-aba-' + label]
        assert not case['passed'] and case['cases'][scenario] is False
    for label in ('ignore-scm-rights-red', 'ignore-release-red', 'skip-release-watch-red',
                  'ignore-sharers-red', 'ignore-seccomp-listener-red', 'drop-netlink-implicit-red'):
        case, = [c for c in report['cases'] if c['label'] == label]
        assert case['completed'] and not all(ok for _, ok in case['rows'])
    # Continuation 2: each retained obligation's mutants redden exactly their row.
    for row, labels in (
            ('census/protocol-inventory-covers-kernel', ('narrow-protocol-scan', 'trust-registry')),
            ('census/undiscovered-protocol-refused', ('skip-undiscovered-refusal',)),
            ('census/protocol-specific-operations', ('generic-l2tp-address', 'drop-kernel-address-decoding',
                                                     'ignore-sctp-bindx', 'ignore-l2tp-conn-id')),
            ('census/io-uring-refused-in-scope', ('skip-inherited-ring-scan', 'ignore-installed-rings')),
            ('census/compat-abi-qualified', ('drop-i386-socket-map', 'native-compat-message-layout',
                                             'drop-compat-socketcall-messages', 'compat-aliases-native')),
            ('census/close-range-accounted', ('refuse-close-range', 'ignore-close-range', 'cloexec-closes-now',
                                              'ignore-exec-closes', 'allow-unknown-close-range-flags',
                                              'ignore-shared-close-range'))):
        for label in labels:
            case, = [c for c in report['cases'] if c['label'] == label + '-red']
            assert case['completed'] and dict(case['rows'])[row] is False, label
    expected_names = {
        'VELDO-0113': ['unavailable/no-client-starts-the-authority', 'unavailable/no-client-hosts-a-listener',
                       'unavailable/no-auto-start-needs-census'],
        'VELDO-0114': ['relay/one-endpoint-one-judgement', 'relay/no-listener-during-call',
                       'relay/no-second-process', 'relay/listener-proof-needs-census'],
        'VELDO-0122': ['filesystem/transient-and-escaped-writes-are-seen', 'unavailable/no-transient-write',
                       'unavailable/no-out-of-directory-write', 'unavailable/no-write-needs-complete-observation']}
    assert len(report['fault_receipts']) == 8
    for receipt in report['fault_receipts'].values():
        for consumer, names in expected_names.items():
            rows = receipt['consumer_rows'][consumer]
            assert [r['name'] for r in rows] == names
            assert all(r['status'] == 'STANDS DOWN' and r['reason'] == 'census_incomplete' for r in rows)
    for path in HERE.glob('*.diff'):
        subprocess.run(['git','apply','--check','--unidiff-zero',str(path.relative_to(ROOT))],
                       cwd=ROOT, check=True, capture_output=True)
    total = sum(p.stat().st_size for p in HERE.parent.rglob('*') if p.is_file())
    assert total < 1_000_000, total
    print('Receipt, source, suite, spec, witness and protected-declaration digests: valid')
    print('Baseline/final: 23 green rows each, no qualification gaps; 13 continuation-2 and 6 close_range mutants red; escape, release, control/memory-ABA matrices and eight fault receipts: valid')
    print('Retained zero-context diffs: apply cleanly')
    print('Proof bytes:', total, '(below 1 MB)')
    spec = importlib.util.spec_from_file_location('personal_setup', ROOT / 'scripts/check_personal_setup.py')
    checker = importlib.util.module_from_spec(spec); spec.loader.exec_module(checker)
    files = [p.relative_to(ROOT) for p in paths.values()]
    files.extend(p.relative_to(ROOT) for p in HERE.parent.rglob('*') if p.is_file())
    # The checker announces the local installation search path. Keep that local
    # setup line out of portable proof; retain its actual finding count unchanged.
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        findings = checker.sweep(ROOT, sorted(set(map(str, files))), out=output)
    for line in output.getvalue().splitlines():
        if not line.startswith('veldo installation:'):
            print(line)
    assert not findings
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
    print('Whitespace check: passed')


if __name__ == '__main__':
    main()
