"""The account pool: which registered subscription account a dispatch runs on, VELDO-0160.

Every registered, active account of an engine runs work at the same time, each on its own login
profile (control_accounts, VELDO-0062). Choosing an account is part of preparing a dispatch, INSIDE its
VELDO-0036 worker reservation: `choose` runs in the reservation's store transaction
(control_reservations.Reservations.reserve_pooled), so the account records and the slots held are
read in the same transaction that takes the slot, and two preparations never both take an account's
last slot. The pool is read at every dispatch: an account the owner registers while work runs is a
candidate at the next dispatch, with nothing restarted.

THE CANDIDATES are the accounts of the dispatch's engine that are active, have a profile on the host the
adapter runs on, are outside every rate-limit window their CLI reported (control_accounts.blocking: a
window reported exhausted takes nothing until its reported reset) and are under their concurrency (the
account's `concurrency`, one by default). An account with no observation yet (no window on its record
and no usage its CLI reported in the ledger) admits one run at a time until its first observation,
because unknown is never zero. The VELDO-0036 account caps are checked for each candidate in turn
(`check`), so an account at its cap is passed over too; a project or unit cap refuses the dispatch.

THE ORDER: the lowest last reported utilization on the tightest window (the highest utilization among
the account's windows whose reported reset has not passed), an account whose utilization is unknown
after every account whose utilization is known; then the fewest active runs; then the least recently
used (the latest slot or invocation the ledger holds for it); then the account id.

NO CANDIDATE: the dispatch waits. `choose` returns no account, each account's reason for being passed
over and the earliest reported reset among the accounts at their limit (the "no account until" time);
the reservation refuses by name (`no_account_until:<reset>`, or `no_account` when no reset is known).

Each choice keeps its trace in the worker record: the engine and host, every candidate with its
utilization, active runs and last use, the reason each other account was passed over, and the windows
read at selection. No secrets. Standard library only.
"""
import copy
import importlib.util
import json
import math
from pathlib import Path


def _organ(name):
    spec = importlib.util.spec_from_file_location('pool_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ACC = _organ('control_accounts')
SCHEMA = 'veldo.account_selection/v1'
# The refusal an account at an account-scoped limit gets from VELDO-0036's check: passed over, not fatal.
ACCOUNT_REFUSALS = ('usage_cap:account:', 'missing_ceiling:account', 'rate_limited:', 'window_exhausted',
                    'unknown_window', 'unknown_allowance:')


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def accounts(conn):
    """Every registered account record, read now (the pool is read at every dispatch)."""
    return [json.loads(data) for (data,) in conn.execute(
        'SELECT data FROM entities WHERE kind=? ORDER BY id', (ACC.KIND,))]


def _uses(records, account):
    """(active runs, last use, observed usage) of `account` in the ledger's reservation records, over every
    domain: accounts are factory scope, so their slots are too."""
    active, last, observed = 0, 0, False
    for record in records.values():
        if (record.get('context') or {}).get('account') != account:
            continue
        if record.get('type') == 'worker':
            active += int(not record.get('retired'))
            last = max(last, record.get('reserved_seq') or 0)
        elif record.get('type') == 'invocation':
            last = max(last, record.get('accepted_seq') or 0)
            observed = observed or any(u in (record.get('observed') or {}) for u in ('tokens', 'messages'))
    return active, last, observed


def observed(record, records):
    """Whether the account has its first observation: a window its CLI reported, or usage its CLI reported."""
    return bool((record or {}).get('windows')) or _uses(records, (record or {}).get('id'))[2]


def utilization(record, now):
    """The last reported utilization on the account's tightest window: the highest among its windows whose
    reported reset has not passed; None when none reported one."""
    found = [w['utilization'] for w in ((record or {}).get('windows') or {}).values()
             if _number(w.get('utilization')) and not (_number(w.get('reset_at')) and w['reset_at'] <= now)]
    return max(found) if found else None


def bound(record, records):
    """The runs the account admits at once: its concurrency, one until its first observation."""
    return (record.get('concurrency') or 1) if observed(record, records) else 1


def choose(conn, records, request, now, check):
    """The account a dispatch runs on, chosen inside its reservation transaction.

    `request` is {engine, host}; `records` the reservation records of the transaction; `check(account)`
    VELDO-0036's check of the slot against that account's caps, raising a refusal with a `code`.
    Returns {account, trace} or {account: None, passed, until}: `passed` names each account's reason for
    being passed over, `until` the earliest reported reset among the accounts at their limit."""
    engine, host = request.get('engine'), request.get('host')
    passed, ranked, until, windows = {}, [], None, {}
    for record in accounts(conn):
        name = record['id']
        if record.get('provider') != engine:
            continue
        windows[name] = copy.deepcopy(record.get('windows') or {})
        if record.get('status') != 'active':
            passed[name] = 'account_status:%s' % record.get('status')
            continue
        if not (record.get('profiles') or {}).get(host):
            passed[name] = 'account_profile:%s' % host
            continue
        limited = ACC.blocking(record, now)
        if limited:
            passed[name] = 'account_limit:' + limited[0]
            resets = [record['windows'][w].get('reset_at') for w in limited]
            if all(_number(r) for r in resets):
                until = max(resets) if until is None else min(until, max(resets))
            continue
        active, last, _ = _uses(records, name)
        admits = bound(record, records)
        if active >= admits:
            passed[name] = 'account_unobserved:one_run' if not observed(record, records) else 'account_concurrency'
            continue
        used = utilization(record, now)
        ranked.append(((0, used) if used is not None else (1, 0), active, last, name))
    candidates = [{'account': name, 'utilization': key[1] if key[0] == 0 else None, 'active': active, 'last_used': last}
                  for key, active, last, name in sorted(ranked)]
    for candidate in candidates:
        try:
            check(candidate['account'])
        except Exception as error:  # noqa: BLE001 - a refusal of VELDO-0036's check, by its code
            code = getattr(error, 'code', None)
            if not isinstance(code, str) or not code.startswith(ACCOUNT_REFUSALS):
                raise
            passed[candidate['account']] = code
            continue
        chosen = candidate['account']
        return {'account': chosen, 'trace': {
            'schema': SCHEMA, 'engine': engine, 'host': host, 'chosen': chosen, 'at': now,
            'candidates': candidates, 'passed': passed, 'windows': windows}}
    return {'account': None, 'passed': passed, 'until': until}


def refusal(choice):
    """The named refusal of a dispatch with no candidate account: when the earliest reset is known."""
    until = choice.get('until')
    return 'no_account_until:%d' % math.ceil(until) if _number(until) else 'no_account'


class Pool:
    """The Runner's account source (control_launch.Runner's `account`): every dispatch's account is chosen
    from the pool inside its worker reservation. `adapters` maps each adapter the Runner may dispatch to
    the engine it runs and the host its profile must be on: {name: {engine, host}}."""

    def __init__(self, adapters):
        if not isinstance(adapters, dict) or not all(
                isinstance(v, dict) and v.get('engine') in ACC.PROFILES and isinstance(v.get('host'), str) and v['host']
                for v in adapters.values()):
            raise ACC.Refused('invalid_input', 'each adapter names its engine and host')
        self.adapters = copy.deepcopy(adapters)

    def reserve(self, reservations, command_id, dispatch_id, project, unit, *, adapter, now):
        """Choose the account and reserve the dispatch's slot on it, in one transaction; the account."""
        target = self.adapters.get(adapter)
        if target is None:
            raise ACC.Refused('unregistered_adapter:' + str(adapter), 'the pool has no engine for this adapter')
        reservations.reserve_pooled(command_id, dispatch_id, {'engine': target['engine'], 'host': target['host']},
                                    project, unit, now=now)
        return reservations.worker(dispatch_id)['context']['account']


def metrics(records):
    """Dispatches per account, and runs ended account_limit per account and window, from the ledger."""
    shown = {'dispatches': {}, 'account_limit': {}}
    for record in records.values():
        account = (record.get('context') or {}).get('account')
        if record.get('type') == 'worker':
            shown['dispatches'][account] = shown['dispatches'].get(account, 0) + 1
        elif record.get('type') == 'invocation' and record.get('outcome') == ACC.LIMIT_OUTCOME:
            window = (record.get('limit') or {}).get('window')
            per = shown['account_limit'].setdefault(account, {})
            per[window] = per.get(window, 0) + 1
    return shown
