"""The account registry: logged-in subscription accounts as store records, VELDO-0062.

An `account` record lives at factory scope in the control store (kind `account`, id `account:<id>`),
never in one repository's Git common directory: an id, a provider (`claude_code` or `codex`), a
label, a status (`active`, `paused` by the owner, or `disabled`), a profile directory per host (the
engine's login profile: Claude Code's CLAUDE_CONFIG_DIR, Codex's CODEX_HOME), the rate-limit windows
the provider's CLI reported (utilization, reset time, observed at, source dispatch) and its
concurrency (one run by default). `.veldo/accounts.py` is the local helper that prepares a profile
directory and prints its one login step; this module is the record the Runner and the launch
receiver read. Choosing among accounts, the pool and the limit are VELDO-0160.

THE LOGIN COMES FROM THE RECORD. `login_environment` builds an engine's environment from the
inherited one: every provider's profile variable and every paid-API credential variable is removed,
and the one profile variable of the account's provider is set to that account's profile on this host.
The account is the one the accepted dispatch contract records, never one named by the caller's
environment. MCP server credentials are not provider model credentials and are not touched here.

A WINDOW REOPENS ONLY ON ITS REPORTED RESET. `blocking` names the windows that refuse a new
invocation now: a window the CLI reported rejected (its allowance exhausted) until its reported reset,
and for ever when no reset was reported, until a later observation of that window says otherwise.

Writes go through the store's signed transaction under a declared owner, so only this module's
command writes an `account` record. `authorize(conn, command)` is the caller's current-authority
predicate, run inside the transaction. Standard library only.
"""
import copy
import json
import math

SCHEMA = 'veldo.account/v1'
KIND = 'account'
PREFIX = 'account:'
OPERATION = 'account_registry'
OWNER = 'veldo-0062-accounts'
WRITES = ('entities', 'journal', 'commands', 'nonces')
# Each provider's login profile variable, the one place it is named.
PROFILES = {'claude_code': 'CLAUDE_CONFIG_DIR', 'codex': 'CODEX_HOME'}
STATUSES = ('active', 'paused', 'disabled')
WINDOW_STATUSES = ('allowed', 'rejected')
# Who may register or change an account (the owner) and who records what a CLI reported (the
# trusted launch receiver's service membership).
OWNER_ROLES = ('project_owner', 'operations_authority')
OBSERVER_ROLE = 'reservation_service'


class Refused(Exception):
    def __init__(self, code, detail=''):
        self.code, self.detail = code, detail
        super().__init__(code + (': ' + detail if detail else ''))


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def entity_id(account):
    return PREFIX + account


def read(conn, account):
    """The stored record of `account`, or None. A plain read inside or outside a transaction."""
    if not _text(account):
        return None
    row = conn.execute('SELECT kind, data FROM entities WHERE id=?', (entity_id(account),)).fetchone()
    return json.loads(row[1]) if row and row[0] == KIND else None


def _member(conn, principal):
    row = conn.execute('SELECT data FROM entities WHERE id=?', (principal,)).fetchone()
    return json.loads(row[0]) if row else None


def authority(conn, command, now=None):
    """The production predicate: a current member, a person holding an owner role for registration
    and status, the reservation service for a reported window."""
    member = _member(conn, command.get('principal'))
    if not isinstance(member, dict) or member.get('revoked_at') is not None:
        return False
    expires = member.get('expires_at')
    at = (command.get('parameters') or {}).get('now') if now is None else now
    if expires is not None and (not _number(at) or at >= expires):
        return False
    roles = member.get('roles') or []
    if (command.get('parameters') or {}).get('action') == 'observe':
        return OBSERVER_ROLE in roles
    return member.get('principal_type') == 'person' and any(role in roles for role in OWNER_ROLES)


def blocking(record, now):
    """The ids of the record's windows that refuse a new invocation at `now`: reported rejected and
    not yet at the reset it reported (no reported reset: blocked until observed otherwise)."""
    found = []
    for window_id, window in sorted(((record or {}).get('windows') or {}).items()):
        if window.get('status') != 'rejected':
            continue
        reset = window.get('reset_at')
        if not _number(reset) or now < reset:
            found.append(window_id)
    return found


def profile(record, host):
    """(variable, directory): the login profile of the account on `host`, or Refused by name."""
    if not isinstance(record, dict):
        raise Refused('missing_authority:account', 'no registered account')
    if record.get('status') != 'active':
        raise Refused('missing_authority:account_status:%s' % record.get('status'), record.get('id', ''))
    variable = PROFILES.get(record.get('provider'))
    directory = (record.get('profiles') or {}).get(host)
    if variable is None:
        raise Refused('invalid_input:account_provider', str(record.get('provider')))
    if not _text(directory):
        raise Refused('missing_authority:account_profile:%s' % host, record.get('id', ''))
    return variable, directory


def login_environment(inherited, record, host, paid_api):
    """The engine environment: `inherited` without any provider's profile variable or any paid-API
    credential variable in `paid_api`, with the account's own profile on `host` set."""
    variable, directory = profile(record, host)
    environment = {k: v for k, v in inherited.items() if k not in PROFILES.values() and k not in paid_api}
    environment[variable] = directory
    return environment


class Accounts:
    """The account records over one store connection. `authorize(conn, command)` runs inside the
    store transaction (`authority` in production); `sign(bytes)` signs journal records as `signer`."""

    def __init__(self, store, conn, *, principal, signer, sign, authorize=authority, generation=1):
        if not all(_text(v) for v in (principal, signer)):
            raise Refused('invalid_input', 'principal and signer are named')
        self.store, self.conn = store, conn
        self.principal, self.signer, self.sign = principal, signer, sign
        self.authorize, self.generation = authorize, generation
        self.counts = {'accepted': 0, 'refused': 0}
        conn.command_registry[OPERATION] = {'transaction_transition': self._in_transaction, 'writes': WRITES}
        store.declare_owners(conn, OWNER, kinds={KIND: (OPERATION,)}, prefixes={PREFIX: (OPERATION,)},
                             module=__file__)

    def get(self, account):
        return read(self.conn, account)

    def list(self, provider=None):
        found = []
        for (data,) in self.conn.execute('SELECT data FROM entities WHERE kind=? ORDER BY id', (KIND,)):
            record = json.loads(data)
            if provider is None or record.get('provider') == provider:
                found.append(record)
        return found

    def _run(self, command_id, params, attempts=5):
        """One signed command; a version another writer moved between the read and the commit is read
        again, so concurrent observations of one account are all kept."""
        if not _text(command_id) or not _number(params.get('now')):
            raise Refused('invalid_input', 'a command id and time')
        target = entity_id(params['account'])
        for _ in range(attempts):
            row = self.conn.execute('SELECT version FROM entities WHERE id=?', (target,)).fetchone()
            command = dict(command_id=command_id, operation=OPERATION, principal=self.principal,
                           nonce='account/' + command_id, parameters=params,
                           expected_versions={target: row[0] if row else 0}, artifact_digests=[])
            self._command = command
            try:
                result = self.store.execute(self.conn, command, self.signer, self.sign, self.generation)
            except self.store.StoreRefused as error:
                if error.code == 'stale_version':
                    continue
                self.counts['refused'] += 1
                raise
            except Refused:
                self.counts['refused'] += 1
                raise
            self.counts['accepted'] += 1
            return result
        self.counts['refused'] += 1
        raise Refused('stale_subject:account', target)

    def register(self, command_id, account, provider, label, profiles, *, concurrency=1, now):
        if (not _text(account) or provider not in PROFILES or not _text(label) or not isinstance(profiles, dict)
                or not profiles or not all(_text(h) and _text(d) for h, d in profiles.items())
                or not isinstance(concurrency, int) or isinstance(concurrency, bool) or concurrency < 1):
            raise Refused('invalid_input', 'an id, a provider, a label, a profile per host and a concurrency')
        return self._run(command_id, dict(action='register', account=account, provider=provider, label=label,
                                          profiles=dict(profiles), concurrency=concurrency, now=now))

    def status(self, command_id, account, status, *, now):
        if status not in STATUSES:
            raise Refused('invalid_input', 'status is one of ' + ', '.join(STATUSES))
        return self._run(command_id, dict(action='status', account=account, status=status, now=now))

    def observe(self, command_id, account, window_id, *, status, reset_at, utilization, source_dispatch, now):
        """Record one rate-limit window exactly as the account's CLI reported it."""
        if (not _text(window_id) or status not in WINDOW_STATUSES or (reset_at is not None and not _number(reset_at))
                or (utilization is not None and (not _number(utilization) or utilization < 0))
                or not _text(source_dispatch)):
            raise Refused('invalid_input', 'a window id, status, reset, utilization and source dispatch')
        return self._run(command_id, dict(action='observe', account=account, window_id=window_id, status=status,
                                          reset_at=reset_at, utilization=utilization,
                                          source_dispatch=source_dispatch, now=now))

    def _in_transaction(self, conn, params, before):
        if self.authorize(conn, self._command) is not True:
            raise Refused('missing_authority')
        target = entity_id(params['account'])
        current = copy.deepcopy((before.get(target) or {}).get('data'))
        action = params['action']
        if action == 'register':
            if current is not None:
                raise Refused('duplicate_account', params['account'])
            value = {'schema': SCHEMA, 'id': params['account'], 'provider': params['provider'],
                     'label': params['label'], 'status': 'active', 'profiles': params['profiles'],
                     'windows': {}, 'concurrency': params['concurrency'], 'registered_at': params['now']}
        elif current is None:
            raise Refused('missing_authority:account', params['account'])
        elif action == 'status':
            value = dict(current, status=params['status'])
        elif action == 'observe':
            prior = current['windows'].get(params['window_id'])
            if prior is not None and prior['observed_at'] > params['now']:
                return {}  # An older observation never replaces a newer one.
            value = current
            value['windows'][params['window_id']] = {
                'status': params['status'], 'reset_at': params['reset_at'], 'utilization': params['utilization'],
                'observed_at': params['now'], 'source_dispatch': params['source_dispatch']}
        else:
            raise Refused('invalid_input', action)
        return {target: {'kind': KIND, 'data': value}}


def usage(reservations, accounts=None):
    """What the usage screen shows, read from the stored ledger: per account (with its label,
    provider, status and windows), per project and per unit, the totals in each declared unit, the
    capacity held, the remaining allowance under each cap (None where unknown usage makes it
    unknowable, never a number that counts unknown as zero), the units still unknown, the calls still
    open and the watermark (the journal sequence of the latest usage the subject's calls recorded).
    Attribution is the stored context of each reservation, never a label a caller or worker gives."""
    records = reservations._records()
    known = {r['id']: r for r in (accounts.list() if accounts is not None else [])}
    shown = {'account': {}, 'project': {}, 'unit': {}}
    for scope in shown:
        subjects = sorted({r['context'][scope] for r in records.values()
                           if r['type'] in ('worker', 'invocation') and r['context']['domain'] == reservations.domain})
        for subject in subjects:
            balance = reservations.balances(scope, subject, records)
            calls = [r for r in records.values() if r['type'] == 'invocation' and reservations._matches(r, scope, subject)]
            unknown = sorted({u for r in calls for u in r['unknown']})
            policy = records.get(reservations._policy_id(scope, subject)) or {}
            remaining = {u: (None if u in unknown else cap - balance.get(u, 0))
                         for u, cap in sorted((policy.get('caps') or {}).items())}
            row = {'totals': {u: v for u, v in balance.items() if u != 'capacity'}, 'capacity': balance['capacity'],
                   'remaining': remaining, 'unknown': unknown,
                   'open': sum(r['state'] in ('pending', 'unknown') for r in calls),
                   'watermark': max((r.get('reported_seq') or r['accepted_seq'] for r in calls), default=None)}
            if scope == 'account' and subject in known:
                record = known[subject]
                row.update(label=record['label'], provider=record['provider'], status=record['status'],
                           windows=copy.deepcopy(record['windows']))
            shown[scope][subject] = row
    return shown
