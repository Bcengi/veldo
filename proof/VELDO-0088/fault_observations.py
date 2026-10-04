"""Unexpected scheduler faults propagate from real initial and pending cycles."""


def observe(v):
    cycles, runner, f, check = (v[k] for k in ('cycles', 'runner', 'f', 'check'))
    original = cycles.start
    fault = RuntimeError('injected scheduler fault')

    def broken_start(*args):
        raise fault

    def surfaced(name):
        try:
            cycles.pass_once()
        except RuntimeError as error:
            raised = error is fault
        else:
            raised = False
        check(name, 'the original unexpected exception reaches the caller', raised)

    try:
        cycles.seen.pop('proj-a', None)
        cycles.start = broken_start
        surfaced('followup/initial-fault')
        cycles.start = original
        active = cycles.start('proj-a', cycles.inputs('proj-a'))
        rid, receipt = f['present']('fault-pending', {'kind': 'pm', 'ref': 'proj-a',
            'digest': v['PM'].SN.digest(b'fault-pending')}, 'Choose the scope.')
        answer = f['answer'](receipt, 'accept')
        check('followup/pending-fault', 'a real owner answer changes accepted input',
              answer.get('outcome') == 'settled' and cycles.inputs('proj-a') != active['input_key'])
        runner.wait(runner.launches[active['dispatch']], timeout=15)
        cycles.start = broken_start
        surfaced('followup/pending-fault')
    finally:
        cycles.start = original
