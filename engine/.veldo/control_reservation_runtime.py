"""Runner seam for every logged-in subscription CLI call, VELDO-0036.

Adapters register all three boundaries and supply launch/stop callables. The runner
passes its complete configured capabilities unchanged to launch. No model API,
engine command construction, capability filtering or process supervisor lives here.
The supervisor calls observe during execution and at its wall-time deadline, even
when the CLI emits nothing. Retirement uses the supervisor's actual observations.
"""
ADAPTERS = {
    'claude_code': ('initial', 'retry', 'follow_on'),
    'codex': ('initial', 'retry', 'follow_on'),
}


class InvocationGuard:
    def __init__(self, reservations, adapter, launch, stop):
        if adapter not in ADAPTERS:
            raise ValueError('unregistered_subscription_adapter')
        self.reservations, self.adapter = reservations, adapter
        self.launch, self.stop = launch, stop
        self.active = {}

    def invoke(self, command_id, dispatch, invocation, boundary, wall_seconds, configuration, *, now):
        if boundary not in ADAPTERS[self.adapter]:
            raise ValueError('unregistered_invocation_boundary')
        try:
            receipt = self.reservations.reserve_call(command_id, dispatch, invocation, boundary, wall_seconds, now=now)
        except Exception:
            self.stop(dispatch)
            raise
        if receipt['replayed']:
            return receipt  # Acceptance never proves non-execution and never authorizes another launch.
        self.active[invocation] = dict(dispatch=dispatch, start=now, wall_seconds=wall_seconds, stopped=False)
        self.launch(invocation, configuration)
        return receipt

    def observe(self, command_id, invocation, sequence, usage, *, now, final=False, outcome=None):
        active = self.active[invocation]
        try:
            reached = now - active['start'] >= active['wall_seconds']
            if reached:
                self._stop(active)
            receipt = self.reservations.report(command_id, invocation, sequence, usage,
                                               now=now, final=final, outcome=outcome)
            records = self.reservations._records()
            call = next(r for r in records.values() if r['type'] == 'invocation' and r['invocation'] == invocation
                        and r['context']['domain'] == self.reservations.domain)
            reached = reached or call['observed'].get('wall_seconds', 0) >= active['wall_seconds']
            for policy in self.reservations._policies(call['context'], records):
                balance = self.reservations.balances(policy['scope'], policy['subject'], records)
                for unit in ('tokens', 'messages'):
                    if unit in policy['caps'] and balance[unit] >= policy['caps'][unit]:
                        reached = True
                if final and balance['invocations'] >= policy['caps']['invocations']:
                    reached = True
                for window in policy.get('windows', {}).values():
                    if window['remaining'] is None:
                        reached = True
                    elif now < window['reset_at']:
                        unit = window['unit']
                        exposed = [r for key, r in records.items() if r['type'] == 'invocation'
                                   and self.reservations._matches(r, policy['scope'], policy['subject'])
                                   and (r['accepted_seq'] > window['store_watermark'] or key in window['outstanding'])]
                        used = sum((r['observed'] if unit == 'wall_seconds' else r['charge']).get(unit, 0)
                                   for r in exposed)
                        if window['remaining'] == 0 or (used >= window['remaining'] and (unit != 'invocations' or final)):
                            reached = True
            if reached:
                self._stop(active)
            return dict(receipt, stop_required=reached)
        except Exception:
            # Reporting, authorization and policy reads must fail closed for the worker.
            self._stop(active)
            raise

    def _stop(self, active):
        if not active['stopped']:
            self.stop(active['dispatch'])
            active['stopped'] = True
