"""Subscription reservations for the trusted authority, VELDO-0036.

One instance owns one connection and store module (as do authority command handlers).
Only control_store writes: allocations, reports and policies are journaled entities in
its existing SQLite database. No second database, prices, engine imports or recovery.
The caller supplies authenticated current-authorization and journal-signing services.
Authorization runs INSIDE the store transaction; a worker must never receive this API
or its connection. See control_reservation_runtime for the runner consumption seam.
"""
import copy
import json
import math

SCHEMA = 'veldo.reservations/v1'
SCOPES = ('account', 'project', 'unit')
USAGE = ('invocations', 'wall_seconds', 'tokens', 'messages')
KINDS = ('capacity',) + USAGE
PREFIX = 'reservation:'


class Refused(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def number(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and value >= 0)


def identity(value):
    if not isinstance(value, str) or not value.strip():
        raise Refused('invalid_input')
    return value


def entity(kind, value):
    return PREFIX + kind + ':' + json.dumps(value, separators=(',', ':'))


class Reservations:
    def __init__(self, store, conn, *, domain, repository, principal, authorize,
                 signer, sign, generation=1, observe=lambda event: None):
        self.store, self.conn = store, conn
        self.domain, self.repository = identity(domain), identity(repository)
        self.principal = identity(principal)
        self.authorize, self.signer, self.sign = authorize, signer, sign
        self.generation, self.observe = generation, observe
        self.counts = dict(accepted=0, refused=0)
        store.COMMAND_REGISTRY['subscription_reservation'] = {
            'transition': self._transition, 'writes': ('entities', 'journal', 'commands', 'nonces')}

    def _records(self):
        return {key: json.loads(data) for key, data in self.conn.execute(
            "SELECT id, data FROM entities WHERE kind='subscription_reservation'")}

    def _context(self, account, project, unit):
        return dict(domain=self.domain, repository=self.repository,
                    account=identity(account), project=identity(project), unit=identity(unit))

    def _matches(self, record, scope, subject):
        return record['context']['domain'] == self.domain and record['context'][scope] == subject

    def balances(self, scope, subject, records=None):
        records = self._records() if records is None else records
        result = dict.fromkeys(KINDS, 0)
        for record in records.values():
            if record['type'] not in ('worker', 'invocation') or not self._matches(record, scope, subject):
                continue
            if record['type'] == 'worker':
                result['capacity'] += int(not record['retired'])
            else:
                for unit in USAGE:
                    result[unit] += record['charge'].get(unit, 0)
        return result

    def _policy_id(self, scope, subject):
        return entity('policy', [self.domain, scope, subject])

    def _policies(self, context, records):
        policies = []
        for scope in SCOPES:
            policy = records.get(self._policy_id(scope, context[scope]))
            if policy is None:
                raise Refused('missing_ceiling:' + scope)
            policies.append(policy)
        return policies

    def _check(self, context, wanted, records, now):
        for policy in self._policies(context, records):
            scope, subject = policy['scope'], policy['subject']
            balance = self.balances(scope, subject, records)
            for unit, cap in policy['caps'].items():
                if unit in ('tokens', 'messages') and wanted.get('invocations'):
                    if any(r['type'] == 'invocation' and self._matches(r, scope, subject)
                           and unit in r['unknown'] for r in records.values()):
                        raise Refused('unknown_allowance:' + unit)
                    if balance[unit] >= cap:
                        raise Refused('usage_cap:' + scope + ':' + unit)
                if balance[unit] + wanted.get(unit, 0) > cap:
                    raise Refused('usage_cap:' + scope + ':' + unit)
            window = policy.get('window')
            if window and wanted.get('invocations'):
                if window['remaining'] is None:
                    raise Refused('unknown_window')
                unit = window['unit']
                outstanding = [r for key, r in records.items() if r['type'] == 'invocation'
                               and self._matches(r, scope, subject)
                               and (r['accepted_seq'] > window['store_watermark']
                                    or key in window['outstanding'])]
                if any(unit in r['unknown'] for r in outstanding):
                    raise Refused('unknown_window_usage')
                if now < window['reset_at']:
                    used = sum(r['charge'].get(unit, 0) for r in outstanding)
                    if window['remaining'] - used <= 0 or used + wanted.get(unit, 0) > window['remaining']:
                        raise Refused('window_exhausted')

    def _run(self, command_id, action, target, payload, now):
        if not number(now):
            raise Refused('invalid_input')
        identity(command_id)
        version = self.conn.execute('SELECT version FROM entities WHERE id=?', (target,)).fetchone()
        params = dict(action=action, target=target, payload=payload, now=now,
                      domain=self.domain, repository=self.repository)
        command = dict(command_id=command_id, operation='subscription_reservation',
                       principal=self.principal, nonce='reservation/' + command_id,
                       parameters=params, expected_versions={target: version[0] if version else 0},
                       artifact_digests=[])
        event = dict(schema=SCHEMA, operation=action, domain=self.domain,
                     repository=self.repository, request=command_id, subject=target,
                     accepted_versions=command['expected_versions'])
        # Store-level retries must reuse the original expected versions as well as content.
        prior = self.conn.execute('SELECT before_versions, transition FROM journal WHERE command_id=?',
                                  (command_id,)).fetchone()
        if prior:
            command['expected_versions'] = json.loads(prior[0])
        self._command = command
        try:
            result = self.store.execute(self.conn, command, self.signer, self.sign, self.generation)
        except (Refused, self.store.StoreRefused) as error:
            self.counts['refused'] += 1
            self.observe(dict(event, outcome='refused', refusal=error.code))
            raise
        self.counts['accepted'] += 1
        self.observe(dict(event, outcome='accepted', watermark=result['seq']))
        return result

    def configure(self, command_id, scope, subject, caps, *, now):
        if scope not in SCOPES or not isinstance(caps, dict) or not caps or set(caps) - set(KINDS):
            raise Refused('invalid_input')
        if any(not number(value) for value in caps.values()):
            raise Refused('invalid_input')
        if not {'capacity', 'invocations', 'wall_seconds'} <= set(caps):
            raise Refused('missing_usage_controls')
        identity(subject)
        return self._run(command_id, 'configure', self._policy_id(scope, subject),
                         dict(scope=scope, subject=subject, caps=caps), now)

    def reserve_worker(self, command_id, dispatch, account, project, unit, *, now):
        return self._run(command_id, 'worker', entity('worker', [self.domain, identity(dispatch)]),
                         dict(dispatch=dispatch, context=self._context(account, project, unit)), now)

    def reserve_call(self, command_id, dispatch, invocation, boundary, wall_seconds, *, now):
        if boundary not in ('initial', 'retry', 'follow_on') or not number(wall_seconds) or wall_seconds <= 0:
            raise Refused('invalid_input')
        return self._run(command_id, 'invocation', entity('invocation', [self.domain, identity(invocation)]),
                         dict(dispatch=identity(dispatch), invocation=invocation, boundary=boundary,
                              wall_seconds=wall_seconds), now)

    def report(self, command_id, invocation, sequence, usage, *, final=False, outcome=None, now):
        if (not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1
                or not isinstance(usage, dict) or set(usage) - set(USAGE)
                or any(not number(v) for v in usage.values())
                or outcome not in (None, 'completed', 'failed', 'timeout', 'cancelled', 'not_executed')):
            raise Refused('invalid_input')
        return self._run(command_id, 'report', entity('invocation', [self.domain, identity(invocation)]),
                         dict(sequence=sequence, usage=usage, final=final, outcome=outcome), now)

    def window(self, command_id, account, unit, remaining, reset_at, watermark, *, now):
        if (unit not in USAGE or (remaining is not None and not number(remaining))
                or not number(reset_at) or not isinstance(watermark, int) or watermark < 1):
            raise Refused('invalid_input')
        return self._run(command_id, 'window', self._policy_id('account', account),
                         dict(unit=unit, remaining=remaining, reset_at=reset_at, watermark=watermark), now)

    def retire(self, command_id, dispatch, lifecycle, *, now):
        """lifecycle(dispatch) is the trusted runner's actual group/cleanup/outcome observer."""
        self._lifecycle = lifecycle
        return self._run(command_id, 'retire', entity('worker', [self.domain, identity(dispatch)]), {}, now)

    def _transition(self, params, before):
        if self.authorize(self.conn, self._command) is not True:
            raise Refused('missing_authority')
        records = self._records()
        action, target, p, now = (params[k] for k in ('action', 'target', 'payload', 'now'))
        current = copy.deepcopy(records.get(target))
        if action == 'configure':
            value = dict(type='policy', **p)
            if current and current.get('window'):
                value['window'] = current['window']
        elif action == 'worker':
            if current:
                raise Refused('duplicate_dispatch')
            self._check(p['context'], {'capacity': 1}, records, now)
            value = dict(type='worker', **p, retired=False)
        elif action == 'invocation':
            if current:
                raise Refused('duplicate_invocation')
            worker = records.get(entity('worker', [self.domain, p['dispatch']]))
            if not worker or worker['retired']:
                raise Refused('missing_worker')
            wanted = dict(invocations=1, wall_seconds=p['wall_seconds'])
            self._check(worker['context'], wanted, records, now)
            value = dict(type='invocation', **p, context=worker['context'], charge=wanted,
                         reserved=wanted.copy(), observed={}, unknown=['tokens', 'messages'],
                         state='pending', sequence=0, reports={}, outcome=None,
                         accepted_seq=self.conn.execute('SELECT COALESCE(MAX(seq),0)+1 FROM journal').fetchone()[0])
        elif action == 'report':
            if not current or current['type'] != 'invocation':
                raise Refused('missing_invocation')
            value = current
            prior = value['reports'].get(str(p['sequence']))
            if prior is not None:
                if prior != p:
                    raise Refused('report_conflict')
                return {}  # Duplicate sequence under a different delivery command settles nothing twice.
            if p['sequence'] <= value['sequence']:
                raise Refused('stale_report')
            if any(v < value['observed'].get(k, 0) for k, v in p['usage'].items()):
                raise Refused('usage_regressed')
            if p['outcome'] != 'not_executed' and p['usage'].get('invocations', 1) != 1:
                raise Refused('invalid_invocation_count')
            value['sequence'] = p['sequence']
            value['reports'][str(p['sequence'])] = p
            value['observed'].update(p['usage'])
            value['outcome'] = p['outcome'] or value['outcome']
            for unit, amount in p['usage'].items():
                value['charge'][unit] = max(value['charge'].get(unit, 0), amount)
                if p['final'] and unit in value['unknown']:
                    value['unknown'].remove(unit)
            if p['outcome'] == 'not_executed':
                # Only the trusted evidence service can attest non-execution via authorize().
                value.update(charge=dict.fromkeys(USAGE, 0), unknown=[], state='settled')
            elif p['final']:
                for unit in ('invocations', 'wall_seconds'):
                    if unit in value['observed']:
                        value['charge'][unit] = value['observed'][unit]
                value['state'] = 'settled' if not value['unknown'] and all(
                    u in value['observed'] for u in ('invocations', 'wall_seconds')) else 'unknown'
        elif action == 'window':
            if not current:
                raise Refused('missing_ceiling:account')
            if current.get('window', {}).get('watermark', 0) >= p['watermark']:
                raise Refused('stale_window')
            value = current
            unresolved = [key for key, r in records.items() if r['type'] == 'invocation'
                          and self._matches(r, 'account', current['subject'])
                          and r['state'] in ('pending', 'unknown')]
            value['window'] = dict(p, outstanding=unresolved, store_watermark=self.conn.execute(
                'SELECT COALESCE(MAX(seq),0) FROM journal').fetchone()[0])
        elif action == 'retire':
            if not current or current['type'] != 'worker':
                raise Refused('missing_worker')
            observation = self._lifecycle(current['dispatch'])
            if observation.get('terminated') is not True:
                raise Refused('worker_alive')
            if observation.get('cleaned') is not True:
                raise Refused('cleanup_incomplete')
            if observation.get('outcome') not in ('completed', 'failed', 'cancelled', 'unknown'):
                raise Refused('missing_outcome')
            calls = [r for r in records.values() if r['type'] == 'invocation'
                     and r['context']['domain'] == self.domain and r['dispatch'] == current['dispatch']]
            if any(r['state'] not in ('settled', 'unknown') for r in calls):
                raise Refused('missing_accounting')
            value = dict(current, retired=True, retirement=observation)
        else:
            raise Refused('invalid_input')
        return {target: {'kind': 'subscription_reservation', 'data': value}}

    def status(self):
        records = self._records()
        own = [r for r in records.values() if r.get('context', {}).get('domain') == self.domain]
        return dict(self.counts, pending=sum(r['type'] == 'invocation' and r['state'] == 'pending' for r in own),
                    unknown=sum(r['type'] == 'invocation' and r['state'] == 'unknown' for r in own),
                    workers=sum(r['type'] == 'worker' and not r['retired'] for r in own))
