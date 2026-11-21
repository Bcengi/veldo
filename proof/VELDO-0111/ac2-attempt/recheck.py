"""Ticket-only replay. Invoke with the external host_heavy.sh wrapper.

Retain compact receipts, actual mutation diffs and text logs, not multi-megabyte
inventories for each replay. Mutants run only in temporary directories. A
missing/duplicate row, exception or failed control is an invalid drive.
"""

import ast
import copy
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import tempfile

from socket_destruction import ROOT, SOURCE, run as witness


HERE = Path(__file__).resolve().parent
SUITE = ROOT / 'scripts/suites/113_veldo_0111_census.py'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def literal(path, name):
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == name for target in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError(name)


def main():
    suite = load('suite111_recheck', SUITE)
    original = SOURCE.read_text()
    records = []
    report = dict(status='INCOMPLETE', blocked_obligation='socket_destruction',
                  scope='VELDO-0111 only; regressions are not AC2 qualification',
                  source_digest=sha(SOURCE), suite_digest=sha(SUITE),
                  recheck_digest=sha(Path(__file__)),
                  witness_digest=sha(HERE / 'socket_destruction.py'),
                  spec_digest=sha(ROOT / 'specs/VELDO-0111-process-and-listener-census.md'),
                  unconfined_declaration_digest=sha(ROOT / 'scripts/gate_unconfined.json'),
                  control_policy='Full-suite mutants share fresh baseline and final-control runs; '
                                 'focused mutants have individual focused controls.',
                  cases=records)
    report['observer_environment'] = dict(
        process_status=[line for line in Path('/proc/self/status').read_text().splitlines()
                        if line.startswith(('CapEff:', 'CapPrm:', 'Seccomp:'))],
        unprivileged_bpf_disabled=Path('/proc/sys/kernel/unprivileged_bpf_disabled').read_text().strip(),
        perf_event_paranoid=Path('/proc/sys/kernel/perf_event_paranoid').read_text().strip(),
        installed_sock_diag_destroy_groups=[line.strip().rstrip(',') for line in
            Path('/usr/include/linux/sock_diag.h').read_text().splitlines()
            if line.strip().startswith('SKNLGRP_') and 'DESTROY' in line])
    with socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, 4) as diagnostic:
        try:
            diagnostic.bind((0, 15))  # The four published destruction groups.
            report['observer_environment']['sock_diag_subscription'] = dict(result=0)
        except OSError as exc:
            report['observer_environment']['sock_diag_subscription'] = dict(result=-1, errno=exc.errno)

    def save():
        (HERE / 'receipt.json').write_text(json.dumps(report, indent=2) + '\n')

    def run(label, path=SOURCE, groups=None, target=None, red=False):
        rows = []
        emit = lambda name, ok: rows.append([name, bool(ok)])
        if groups is None:
            evidence = suite.run_checks(ROOT, emit, path)
        else:
            evidence = suite.run_round3_checks(load('census111_recheck', path), emit, groups)
        names = [name for name, _ in rows]
        assert names and len(names) == len(set(names)), (label, 'invalid rows')
        if red:
            assert target in names and dict(rows)[target] is False, (label, rows)
        else:
            assert all(ok for _, ok in rows), (label, 'invalid_baseline', rows)
        item = dict(label=label, completed=True, rows=rows,
                    implementation_digest=sha(path), needs_ptrace=groups != ('states',))
        records.append(item)
        print(label, rows, flush=True)
        save()
        return evidence

    baseline = run('baseline')
    inventory = baseline['inventory']
    report['qualification'] = dict(status=inventory['status'],
        capture_status=inventory['capture_status'], host=inventory['host'],
        gaps=inventory['qualification']['gaps'],
        reasons=inventory['qualification']['reasons'],
        consumer_rows=inventory['consumer_rows'])
    report['fault_receipts'] = {key: {field: value[field] for field in (
        'status', 'capture_status', 'state', 'failures', 'lost_events', 'consumer_rows')}
        for key, value in baseline.items() if key.startswith('fault_') and key != 'fault_states'}
    # Keep one complete external-reference witness per family, with the large
    # repeated host inventory omitted. These are counterexamples, not COMPLETE receipts.
    external = witness()
    assert external['passed']
    (HERE / 'socket-destruction.txt').write_text(json.dumps(external, indent=2) + '\n')
    report['socket_destruction_witness'] = dict(passed=True, families=[r['family'] for r in external['cases']],
        evidence='socket-destruction.txt', digest=sha(HERE / 'socket-destruction.txt'))
    save()

    def mutate(label, old, new, target, groups=None):
        assert original.count(old) == 1, (label, 'ambiguous mutation')
        changed = original.replace(old, new)
        (HERE / (label + '.diff')).write_text(''.join(difflib.unified_diff(
            original.splitlines(True), changed.splitlines(True),
            fromfile='a/scripts/fixtures/lifecycle_census.py',
            tofile='b/scripts/fixtures/lifecycle_census.py')))
        with tempfile.TemporaryDirectory(prefix='v111-recheck-') as temporary:
            path = Path(temporary) / 'lifecycle_census.py'
            path.write_text(changed)
            run(label + '-red', path, groups, target, True)
        if groups is not None:
            run(label + '-green', groups=groups)
        else:
            records[-1]['controls'] = ['baseline', 'final-control']
        assert SOURCE.read_text() == original

    initial = load('initial111', HERE.parent / 'drive.py')
    for label, target, old, new in initial.CASES:
        mutate(label, old, new, target)
    for label, (old, new, groups, target) in literal(HERE.parent / 'round3/falsifiers.py', 'cases').items():
        mutate(label, old, new, target, groups)
    faults = load('faults111', HERE.parent / 'round2/fault_drive.py')
    for label, (old, new) in faults.CASES.items():
        mutate('swallow-' + label, old, new, 'census/incomplete-is-not-empty')
    mutate('clone-untraced', '            if flags & 0x800000:',
           '            if False: # swallow escape attempt', 'census/clone-untraced')
    run('final-control')

    # Replay the existing named-gap suppression falsifiers against this host's
    # fresh inventory. Do not require a historical, no-longer-present host gap.
    expected = set(inventory['qualification']['gaps'])
    report['reason_replay_input_digest'] = hashlib.sha256(
        json.dumps(inventory, sort_keys=True).encode()).hexdigest()
    for capability in sorted(expected):
        old = '    def gap(capability, reason, evidence):\n'
        changed = original.replace(old, old + f'        if capability == {capability!r}:\n            return\n')
        (HERE / (capability + '.diff')).write_text(''.join(difflib.unified_diff(
            original.splitlines(True), changed.splitlines(True),
            fromfile='a/scripts/fixtures/lifecycle_census.py', tofile='b/scripts/fixtures/lifecycle_census.py')))
        for phase, text in (('red', changed), ('green', original)):
            with tempfile.TemporaryDirectory(prefix='v111-reason-') as temporary:
                path = Path(temporary) / 'lifecycle_census.py'
                path.write_text(text)
                census = load('reason111', path)
                value = copy.deepcopy(inventory)
                value['failures'] = []
                census.qualify(value, value['qualification']['inventory'])
                actual = {f['capability'] for f in value['qualification']['reasons']}
                passed = actual == expected and actual == {f['capability'] for f in value['failures']}
                assert passed == (phase == 'green'), (capability, phase, actual)
                records.append(dict(label=capability + '-' + phase, completed=True,
                    row='census/named-qualification-reasons', passed=passed,
                    actual=sorted(actual), needs_ptrace=False, uses_live_baseline=True,
                    implementation_digest=sha(path)))
                print(capability, phase, passed, flush=True)
                if capability == 'socket_destruction':
                    live = witness(path)
                    assert live['passed'] == (phase == 'green')
                    records.append(dict(label='external-reference-' + phase, completed=True,
                        row=live['row'], passed=live['passed'], needs_ptrace=True,
                        families=[dict(family=c['family'], passed=c['passed'],
                            destruction_reasons=c['destruction_reasons'], witness=c['witness'])
                            for c in live['cases']], implementation_digest=sha(path)))
                    print('external-reference', phase, live['passed'], flush=True)
        save()
    report['recheck_completed'] = True
    save()
    current = dict(report['qualification'], source_digest=report['source_digest'],
        suite_digest=report['suite_digest'], spec_digest=report['spec_digest'],
        acceptance=dict(AC2=False), blocked_obligation='socket_destruction',
        current_receipt='ac2-attempt/receipt.json', receipt_digest=sha(HERE / 'receipt.json'),
        scope='Live regression and counterexample evidence; full AC2 qualification remains INCOMPLETE')
    (HERE.parent / 'qualification.json').write_text(json.dumps(current, indent=2) + '\n')
    print('Recheck complete. AC2 remains INCOMPLETE: socket destruction has no qualified observer.', flush=True)


if __name__ == '__main__':
    main()
