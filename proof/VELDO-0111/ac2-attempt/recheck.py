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
from shared_memory import instrument, run as shared_witness
import memory_aba


HERE = Path(__file__).resolve().parent
SUITE = ROOT / 'scripts/suites/113_veldo_0111_census.py'
NEXT = 'io_uring_socket_effects'  # first retained obligation not addressed by this run


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
    report = dict(base='7f1ea5e0', status='INCOMPLETE', next_obligation=NEXT,
                  scope='VELDO-0111 only; regressions are not AC2 qualification',
                  source_digest=sha(SOURCE), suite_digest=sha(SUITE),
                  recheck_digest=sha(Path(__file__)),
                  witness_digest=sha(HERE / 'socket_destruction.py'),
                  shared_witness_digest=sha(HERE / 'shared_memory.py'),
                  memory_aba_digest=sha(HERE / 'memory_aba.py'),
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

    def diff(label, changed):
        (HERE / (label + '.diff')).write_text(''.join(difflib.unified_diff(
            original.splitlines(True), changed.splitlines(True), n=0,
            fromfile='a/scripts/fixtures/lifecycle_census.py', tofile='b/scripts/fixtures/lifecycle_census.py')))

    def patched(*pairs):
        changed = original
        for old, new in pairs:
            assert changed.count(old) == 1, ('ambiguous mutation', old)
            changed = changed.replace(old, new)
        return changed

    # Two independent detectors: the SCM_RIGHTS send decoder (attribution) and
    # the epoll file-release observer (any outside reference after drain).
    SEND = ('            self.sent_rights(pid, entry, result)', '            pass  # ignore SCM_RIGHTS sends')
    RELEASE = ("            elif obj['inode'] in alive:", "            elif False:  # ignore references after drain")
    WATCH = ('        self.watch(pid, fd, obj)\n', '')
    # Kernel state, not tracee memory, for bind addresses, socketpair results
    # and received descriptors; shared tables and seccomp listeners fail closed.
    BIND = ("                if obj['kernel_sockaddr_hex'] is not None and not sampled_matches(",
            "                if False and not sampled_matches(")
    PAIR = (('            if created != sorted(', '            if False and created != sorted('),
            ('            for fd in created:\n', '            for fd in struct.unpack("<2i", self.memory(pid, a[3], 8)):\n'))
    RECEIVED = ('            for fd, link in sorted(self.installed(pid, entry).items()):',
                '            for fd, link in []:  # trust received control memory')
    SHARERS = ('        for other in self.live:\n            if other == pid:',
               '        for other in ():\n            if other == pid:')
    SECCOMP = ('        if nr == 317 and a[0] == 1 and a[1] & 8:', '        if False:')
    NETLINK = ("                elif obj['family'] == socket.AF_NETLINK and obj.get('kernel_sockaddr_hex'):",
               '                elif False:  # netlink implicit address undecoded')
    MUTANTS = {'ignore-scm-rights': (SEND,), 'ignore-scm-rights-and-release': (SEND, RELEASE),
               'ignore-release': (RELEASE,), 'skip-release-watch': (WATCH,),
               'trust-bind-sample': (BIND,), 'socketpair-from-memory': PAIR,
               'trust-received-control': (RECEIVED,), 'ignore-sharers': (SHARERS,),
               'ignore-seccomp-listener': (SECCOMP,), 'drop-netlink-implicit': (NETLINK,)}
    sources = {label: patched(*pairs) for label, pairs in MUTANTS.items()}
    for label, changed in sources.items():
        diff(label, changed)

    # Lead falsifier: ignoring SCM_RIGHTS must lose the named escape in all four
    # families. With the release observer alone disabled the capture also turns
    # green (COMPLETE) for scope-created transports; both are caught by the row.
    for mode in ('owned', 'sendmmsg', 'imported'):
        for phase, label in (('green', None), ('red', 'ignore-scm-rights'),
                             ('red', 'ignore-scm-rights-and-release')):
            with tempfile.TemporaryDirectory(prefix='v111-rights-') as temporary:
                path = Path(temporary) / 'lifecycle_census.py'
                path.write_text(sources[label] if label else original)
                live = witness(path, mode)
                assert live['passed'] == (phase == 'green')
                assert all(case['passed'] == (phase == 'green') for case in live['cases'])
                cases = live['cases']
                if label == 'ignore-scm-rights':
                    # The release observer still fails these captures honestly.
                    assert all(c['referenced_after_drain'] and c['receipt']['capture_status'] == 'INCOMPLETE'
                               for c in cases)
                if label == 'ignore-scm-rights-and-release':
                    assert all(not c['escape_failures'] for c in cases)
                    if mode != 'imported':
                        assert all(c['receipt']['capture_status'] == 'COMPLETE' for c in cases)
                if phase == 'green':
                    assert all(c['send_attributed'] and c['referenced_after_drain'] for c in cases)
                name = 'escaped-reference-' + mode + '-' + (label or 'green')
                records.append(dict(label=name, phase=phase, mutant=label,
                    completed=True, row=live['row'], passed=live['passed'], needs_ptrace=True,
                    implementation_digest=sha(path), families=[dict(family=c['family'],
                        passed=c['passed'], capture_status=c['receipt']['capture_status'],
                        send_attributed=c['send_attributed'],
                        referenced_after_drain=c['referenced_after_drain'],
                        escape_failures=c['escape_failures'], witness=c['witness']) for c in cases]))
                print(name, live['passed'], flush=True)
                save()

    # Real external process_vm_writev makes entry/exit control snapshots agree
    # while the kernel sends SCM_RIGHTS: the send decoder is blind. The release
    # observer must still name the escape; disabling it must turn the row red.
    instrumented = instrument(original)
    diff('shared-memory-scheduling', instrumented)
    for phase, label in (('green', None), ('red', 'ignore-release')):
        with tempfile.TemporaryDirectory(prefix='v111-shared-') as temporary:
            path = Path(temporary) / 'lifecycle_census.py'
            path.write_text(sources[label] if label else original)
            live = shared_witness(path)
            assert live['passed'] == (phase == 'green')
            if phase == 'green':
                (HERE / 'shared-memory.txt').write_text(json.dumps(live, indent=2) + '\n')
            records.append(dict(label='control-aba-' + (label or 'green'), phase=phase, mutant=label,
                completed=True, row=live['row'], passed=live['passed'], needs_ptrace=True,
                implementation_digest=sha(path), instrumented_digest=live['instrumented_digest'],
                actual_fd_received_after_drain=live['actual_fd_received_after_drain'],
                identical_entry_exit_samples=live['identical_entry_exit_samples'],
                send_decoder_attributed=live['send_decoder_attributed'],
                escaped_reference_detected=live['escaped_reference_detected'],
                capture_status=live['receipt']['capture_status']))
            print('control-aba', phase, live['passed'], flush=True)
            save()
    report['shared_memory_witness'] = dict(evidence='shared-memory.txt',
        digest=sha(HERE / 'shared-memory.txt'), row='census/escape-detected-despite-control-aba')

    # Outside-writer ABA on bind/socketpair/recvmsg memory: the original must
    # name each from kernel state; each mutant trusting memory loses its case.
    diff('memory-aba-scheduling', memory_aba.instrument(original))
    for label, scenario in ((None, None), ('trust-bind-sample', 'bind'),
                            ('socketpair-from-memory', 'socketpair'),
                            ('trust-received-control', 'recvmsg')):
        with tempfile.TemporaryDirectory(prefix='v111-maba-') as temporary:
            path = Path(temporary) / 'lifecycle_census.py'
            path.write_text(sources[label] if label else original)
            live = memory_aba.run(path)
            outcome = {c['scenario']: c['passed'] for c in live['cases']}
            if label is None:
                assert live['passed'], outcome
                (HERE / 'memory-aba.txt').write_text(json.dumps(live, indent=2) + '\n')
            else:
                assert outcome[scenario] is False and not live['passed'], (label, outcome)
            records.append(dict(label='memory-aba-' + (label or 'green'), mutant=label,
                completed=True, row=live['row'], passed=live['passed'], cases=outcome,
                needs_ptrace=True, implementation_digest=sha(path),
                instrumented_digest=live['instrumented_digest']))
            print('memory-aba', label or 'green', outcome, flush=True)
            save()
    report['memory_aba_witness'] = dict(evidence='memory-aba.txt',
        digest=sha(HERE / 'memory-aba.txt'), row=memory_aba.ROW)

    def mutate(label, old, new, target, groups=None):
        assert original.count(old) == 1, (label, 'ambiguous mutation')
        changed = original.replace(old, new)
        diff(label, changed)
        with tempfile.TemporaryDirectory(prefix='v111-recheck-') as temporary:
            path = Path(temporary) / 'lifecycle_census.py'
            path.write_text(changed)
            run(label + '-red', path, groups, target, True)
        if groups is not None:
            run(label + '-green', groups=groups)
        else:
            records[-1]['controls'] = ['baseline', 'final-control']
        assert SOURCE.read_text() == original

    # Whole-suite drives of the same mutants against their named rows.
    for label, target in (('ignore-scm-rights', 'census/escaped-reference'),
                          ('ignore-release', 'census/destruction-at-drain'),
                          ('skip-release-watch', 'census/destruction-at-drain'),
                          ('ignore-sharers', 'census/shared-descriptor-table-fails-closed'),
                          ('ignore-seccomp-listener', 'census/shared-descriptor-table-fails-closed'),
                          ('drop-netlink-implicit', 'census/netlink-implicit-binding')):
        (old, new), = MUTANTS[label]
        mutate(label, old, new, target)

    # protocol_inventory_bounds: the scan must cover what the kernel accepts, the
    # registry must fail closed on unknown entries, and an undiscovered measured
    # protocol must be refused.
    PROTOCOL = (
        ('narrow-protocol-scan', 'PROTOCOL_BOUNDS = {1: 16, 2: 1024, 10: 1024, 16: 64}',
         'PROTOCOL_BOUNDS = {2: 256, 10: 256, 16: 32}', 'census/protocol-inventory-covers-kernel'),
        ('trust-registry', '    return dict(registered=registered, aliases=aliases, unexplained=unexplained)',
         '    return dict(registered=registered, aliases=aliases, unexplained=[])',
         'census/protocol-inventory-covers-kernel'),
        ('skip-undiscovered-refusal', '    if undiscovered:\n', '    if False:\n',
         'census/undiscovered-protocol-refused'))
    # operation_configuration: protocol-specific fixtures, kernel-sockaddr
    # decoding, exact L2TP connection ids and SCTP bindx refusal.
    OPERATION = 'census/protocol-specific-operations'
    PROTOCOL += (
        ('generic-l2tp-address', '    if protocol != L2TP_IP:\n', '    if True:\n', OPERATION),
        ('drop-kernel-address-decoding', '        if decoded:\n', '        if False:\n', OPERATION),
        ('ignore-sctp-bindx', '        if nr in (54, 55) and a[1] == 132',
         '        if False and nr in (54, 55) and a[1] == 132', OPERATION),
        ('ignore-l2tp-conn-id',
         '    if protocol == L2TP_IP and family in (socket.AF_INET, socket.AF_INET6):\n',
         '    if False:\n', OPERATION))
    for label, old, new, target in PROTOCOL:
        mutate(label, old, new, target)

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
            fromfile='a/scripts/fixtures/lifecycle_census.py', tofile='b/scripts/fixtures/lifecycle_census.py', n=0)))
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
        save()
    report['recheck_completed'] = True
    save()
    current = dict(report['qualification'], source_digest=report['source_digest'],
        suite_digest=report['suite_digest'], spec_digest=report['spec_digest'],
        acceptance=dict(AC2=False), next_obligation=NEXT,
        current_receipt='ac2-attempt/receipt.json', receipt_digest=sha(HERE / 'receipt.json'),
        scope='Live regression and counterexample evidence; full AC2 qualification remains INCOMPLETE')
    (HERE.parent / 'qualification.json').write_text(json.dumps(current, indent=2) + '\n')
    print(f'Recheck complete. AC2 remains INCOMPLETE: next open obligation is {NEXT}.', flush=True)


if __name__ == '__main__':
    main()
