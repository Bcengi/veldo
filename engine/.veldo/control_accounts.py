"""The account registry: logged-in subscription accounts as store records, VELDO-0062.

An `account` record lives at factory scope in the control store (kind `account`, id `account:<id>`),
never in one repository's Git common directory: an id, a provider (`claude_code` or `codex`), a
label, a status (`active`, `paused` by the owner, or `disabled`), a profile directory per host (the
engine's login profile: Claude Code's CLAUDE_CONFIG_DIR, Codex's CODEX_HOME), the rate-limit windows
the provider's CLI reported (utilization, reset time, observed at, source dispatch) and its
concurrency (one run by default). `.veldo/accounts.py` is the local helper that prepares a profile
directory and prints its one login step; this module is the record the Runner and the launch
receiver read. Choosing among accounts is control_account_pool (VELDO-0160).

THE LOGIN COMES FROM THE RECORD. `login_environment` builds an engine's environment from the
inherited one and the adapter's configured one: every provider's profile variable and every variable
that could log either CLI in another way is removed from the inherited environment, the configured one
is added, and the one profile variable of the account's provider is set to that account's profile on
this host. The account is the one the accepted dispatch contract records, never one named by the
caller's environment. MCP server credentials are not provider model credentials and are not touched
here.

THE STRIP IS BY FAMILY AND BY THE BINARIES' OWN LISTS, AND ONLY OF THE INHERITED ENVIRONMENT (`strips`).
Removed from what the engine inherits: every name under the model providers' own prefixes (ANTHROPIC_,
OPENAI_, CODEX_, and CLAUDE_CODE_USE_, the switches that move Claude Code to another provider), so a
variable a later CLI adds there is removed without anyone listing it; and every name the installed
binaries' own lists make a login or a Claude Code setting of the owner's shell (each engine module's
CREDENTIALS and SETTINGS, extracted from the binary; the launch receiver passes their union). A name
is never stripped for a word in it: a count, threshold or usage setting (CLAUDE_CODE_MAX_OUTPUT_TOKENS,
CLAUDE_CODE_IDLE_TOKEN_THRESHOLD) is not a login. General proxy, CA, runtime, cloud and tool
credentials (AWS, Azure, Google, package registries) stay: they are the worker's tools' own, and
neither CLI sends a model request through them once the provider switches are gone.

WHAT THE ADAPTER CONFIGURES IS NEVER SILENTLY DROPPED (`refused`). The families are the inherited
environment's: a configured model (ANTHROPIC_MODEL and the rest of the binary's model table) or
non-login setting reaches the engine as configured. A configured name that is a login, a credential or
settings redirect or a paid-API switch (a profile variable, a CLAUDE_CODE_USE_ switch or a name in
CREDENTIALS) is refused by name when the configuration is loaded, and nothing runs.

A WINDOW REOPENS ONLY ON ITS REPORTED RESET. `blocking` names the windows that refuse a new
invocation now: a window the CLI reported rejected (its allowance exhausted) until its reported reset,
and for ever when no reset was reported, until a later observation of that window says otherwise.

ONE REGISTRATION PER ACCOUNT (VELDO-0160). An account is one login: an id already registered, or a
profile directory already registered for another account on the same host (the same login under
another name), is refused by name (`duplicate_account:<the registered id>`).

A RUN STOPPED BY ITS ACCOUNT'S LIMIT (VELDO-0160). `classify` ends such a run as `account_limit`, with the
window and reset its engine's stream stated (each engine meter's `limit()`): when the engine ended with
its rate-limit result, always; when only the stream reported the window exhausted, unless the run
completed. No other run is classified so.

THE OWNER'S CAP (VELDO-0131, owner Telegram 38184). An account's run concurrency was set only by `register`.
`cap` sets it again by the owner's command, as a versioned change of the same record: it names the account at the
version the owner saw (a version that moved is refused stale, never retried), the person whose command it is
(its journal actor; a person holding an owner role whose membership scope is the whole factory, since an account
is factory scope, else missing_authority), and the new concurrency (an integer from 1 to CAP_LIMIT, unchanged
refused). The record keeps every change in `concurrency_history` (concurrency, previous, by, at, command and,
from the API, the assertion digest). Control_account_pool reads `concurrency` as it always has.

THE OWNER'S PACING (VELDO-0236). An account is never switched off by these commands, only not used until a window
resets. `pause` names an account and one of its usage windows and stores the pause with that window's last reported
reset (VELDO-0166) as its end; `ceiling` caps one window at a utilization percent (absolute, 1 to 100, or relative,
+N added to the window's last observed utilization and stored as the absolute result) until that window's reset; a new
ceiling on a window replaces the old one; `resume` ends the account's pause and its ceilings at once. A window with no
reported reset later than now is refused invalid_input:pause_reset or invalid_input:ceiling_reset, a ceiling value
outside 1 to 100 or any ceiling on a window with no observed utilization invalid_input:ceiling, an unknown account or
window invalid_input:account, and a command of anyone but the factory owner (VELDO-0203's: a current person member who
enrolled himself and holds every bootstrap role) missing_authority:owner_command:not_factory_owner; a refusal writes
nothing. A later observation of the window never moves an end, and none of these sets the indefinite `paused` status.
A pause or a ceiling is out of force from its end on with no command (`paced`, read by control_account_pool);
`lapse`, run at each factory loop pass, commits one record of each end it finds, once. A utilization percent is the
CLI's reported fraction times 100 (`percent`). Every pacing command and end is one signed journal record whose
account record carries the event as `pacing` (type, command id, principal, route, account, window, end, value,
the utilization a ceiling was read against, the window observation it read, the provenance and, for an end, the
pass); `history` reads those records from the journal, never a cache. Observed (`observe`) and counted by type,
route and outcome (`observe_pacing`), never a credential or a profile's contents.

Writes go through the store's signed transaction under a declared owner, so only this module's
command writes an `account` record. `authorize(conn, command)` is the caller's current-authority
predicate, run inside the transaction. Standard library only.
"""
import copy
import datetime
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import zoneinfo

SCHEMA = 'veldo.account/v1'
KIND = 'account'
PREFIX = 'account:'
OPERATION = 'account_registry'
OWNER = 'veldo-0062-accounts'
WRITES = ('entities', 'journal', 'commands', 'nonces')


def _helper():
    spec = importlib.util.spec_from_file_location('control_accounts_helper', Path(__file__).with_name('accounts.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Each provider's login profile variable, from the one place it is named (accounts.PROFILE_ENV).
PROFILES = dict(_helper().PROFILE_ENV)
# The provider families whose every variable is stripped from an engine's inherited environment, and
# the one whose every variable is a provider switch, refused when an adapter configures it.
STRIP_PREFIXES = ('ANTHROPIC_', 'OPENAI_', 'CODEX_', 'CLAUDE_CODE_USE_')
REFUSED_PREFIXES = ('CLAUDE_CODE_USE_',)
STATUSES = ('active', 'paused', 'disabled')
# None means this window was reported without a status (VELDO-0166).
WINDOW_STATUSES = ('allowed', 'rejected', None)
# Who may register or change an account (the owner) and who records what a CLI reported (the
# trusted launch receiver's service membership).
OWNER_ROLES = ('project_owner', 'operations_authority')
# VELDO-0131: the most concurrent runs one account's cap may name.
CAP_LIMIT = 16
OBSERVER_ROLE = 'reservation_service'
# VELDO-0160: the outcome of a run its account's limit stopped, and the signals that state the limit.
LIMIT_OUTCOME = 'account_limit'
LIMIT_SIGNALS = ('stream', 'result')
# VELDO-0236: the owner's pacing commands, the end a factory loop pass records, the routes a command comes by, the
# roles VELDO-0203's factory owner holds, and the event fields every pacing record carries.
PACING = ('pause', 'ceiling', 'resume')
END = 'end'
ROUTES = ('telegram', 'ui')
BOOTSTRAP_ROLES = frozenset({'project_owner', 'membership_steward'})
NOT_FACTORY_OWNER = 'missing_authority:owner_command:not_factory_owner'
EVENT_FIELDS = ('type', 'command_id', 'principal', 'route', 'account', 'window', 'until', 'value', 'utilization',
                'observation', 'provenance', 'ended', 'pass', 'at')


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


def factory_owner(conn, principal, now):
    """VELDO-0203's factory owner: a current person member who enrolled himself and holds every bootstrap role."""
    member = _member(conn, principal)
    if not isinstance(member, dict) or member.get('revoked_at') is not None:
        return False
    expires = member.get('expires_at')
    if expires is not None and (not _number(now) or now >= expires):
        return False
    return (member.get('principal_type') == 'person' and member.get('enrolled_by') == principal
            and BOOTSTRAP_ROLES <= set(member.get('roles') or []))


def percent(utilization):
    """A window's utilization as a percent: the CLI's reported fraction times 100; None when none was reported."""
    return round(utilization * 100, 6) if _number(utilization) else None


def shown(value):
    """A percent as the words and reasons name it: 50, not 50.0."""
    return ('%d' % value) if _number(value) and float(value).is_integer() else ('%g' % value)


def paced(record, now):
    """Why the owner's pacing passes the account over at `now`: (reason, end, command id) of its pause in force
    (paused_until:<reset>) or of a ceiling in force on a window whose last observed utilization is at or above its
    value (ceiling:<window>:<value>); None when neither. Each is out of force from its end on."""
    record = record or {}
    pause = record.get('pause')
    if isinstance(pause, dict) and _number(pause.get('until')) and now < pause['until']:
        return 'paused_until:%d' % math.ceil(pause['until']), pause['until'], pause.get('command_id')
    windows = record.get('windows') or {}
    for window, ceiling in sorted((record.get('ceilings') or {}).items()):
        if not (isinstance(ceiling, dict) and _number(ceiling.get('until')) and now < ceiling['until']):
            continue
        used = percent((windows.get(window) or {}).get('utilization'))
        if used is not None and used >= ceiling['value']:
            return 'ceiling:%s:%s' % (window, shown(ceiling['value'])), ceiling['until'], ceiling.get('command_id')
    return None


def zone_of(name):
    try:
        return datetime.timezone.utc if name in (None, '', 'UTC', 'Etc/UTC', 'GMT') else zoneinfo.ZoneInfo(name)
    except (ValueError, zoneinfo.ZoneInfoNotFoundError):
        return datetime.timezone.utc


def clock(seconds, zone='UTC', now=None):
    """A time in the owner's time zone, in words: 14:05 UTC, with its date first when that is not now's date there."""
    tz = zone_of(zone)
    at = datetime.datetime.fromtimestamp(seconds, tz)
    label = at.tzname() or 'UTC'
    same = _number(now) and datetime.datetime.fromtimestamp(now, tz).date() == at.date()
    return '%s %s' % (at.strftime('%H:%M' if same else '%Y-%m-%d %H:%M'), label)


def words(event, zone='UTC'):
    """The answer to a pacing command, naming the account, the window and the end in words and in `zone`."""
    kind, account, window, now = event.get('type'), event.get('account'), event.get('window'), event.get('at')
    if kind == 'pause':
        return '%s paused until %s, when its %s window resets.' % (account, clock(event['until'], zone, now), window)
    if kind == 'ceiling':
        return '%s capped at %s percent of its %s window until %s, when it resets (now at %s percent).' % (
            account, shown(event['value']), window, clock(event['until'], zone, now), shown(event['utilization']))
    ended = event.get('ended') or []
    if kind == 'resume':
        if not ended:
            return '%s resumed: it had no pause or ceiling in force.' % account
        return '%s resumed: %s ended now.' % (account, ', '.join(
            ('its pause on %s' if e['kind'] == 'pause' else 'its ceiling on %s') % e['window'] for e in ended))
    return '%s: its %s on %s ended at %s, when that window reset.' % (
        account, ' and '.join(e['kind'] for e in ended) or 'nothing', window, clock(event.get('until') or 0, zone, now))


UNRECORDED_END = 'stale_subject:account_pacing_end'


def due(record, now):
    """Whether `record` still holds a pause or a ceiling whose end is at or before `now`."""
    pause = record.get('pause')
    if isinstance(pause, dict) and _number(pause.get('until')) and pause['until'] <= now:
        return True
    return any(isinstance(c, dict) and _number(c.get('until')) and c['until'] <= now
               for c in (record.get('ceilings') or {}).values())


def history(conn, account=None):
    """VELDO-0236 AC4: every pacing record in journal order, read from the journal itself (never a cache): each
    journal record whose account record's `pacing` event is that record's own command, with its sequence."""
    found = []
    for seq, command_id, transition in conn.execute(
            "SELECT seq, command_id, transition FROM journal WHERE transition LIKE '%\"pacing\"%' ORDER BY seq"):
        for eid, entry in sorted(json.loads(transition).items()):
            data = (entry or {}).get('data') or {}
            event = data.get('pacing') if entry.get('kind') == KIND else None
            if (isinstance(event, dict) and event.get('command_id') == command_id
                    and (account is None or event.get('account') == account)):
                found.append(dict(event, seq=seq))
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


def strips(name, named):
    """Whether an inherited variable `name` never reaches an engine: a provider profile variable, a name
    in a provider family, or one the binaries' lists (`named`, their logins and settings) name."""
    return name in PROFILES.values() or name.startswith(STRIP_PREFIXES) or name in named


def refused(configured, credentials):
    """The names of an adapter's configured environment that are a login, a credential or settings
    redirect or a paid-API switch: a profile variable, a provider switch, or one of `credentials`."""
    return sorted(name for name in configured
                  if name in PROFILES.values() or name.startswith(REFUSED_PREFIXES) or name in credentials)


def classify(outcome, limit):
    """(outcome, limit): `account_limit` with {window, reset_at, signal} for a run its account's limit
    stopped, else the outcome as it is and None. `limit` is the engine meter's `limit()`: the last limit
    the stream stated, `signal` `result` when the engine ended with its rate-limit result (always a limit)
    or `stream` when the stream reported the window exhausted (a limit unless the run completed)."""
    if not isinstance(limit, dict) or limit.get('signal') not in LIMIT_SIGNALS or outcome == 'not_executed':
        return outcome, None
    if limit['signal'] == 'stream' and outcome == 'completed':
        return outcome, None
    return LIMIT_OUTCOME, {'window': limit.get('window'), 'reset_at': limit.get('reset_at'), 'signal': limit['signal']}


def _same_profile(value, other):
    return os.path.normpath(value) == os.path.normpath(other)


def login_environment(inherited, record, host, named, configured=None, credentials=frozenset()):
    """The engine environment: `inherited` without every variable `strips` removes, then the adapter's
    `configured` one (refused by name if it names a login, never silently dropped), with the account's
    own profile on `host` set, the only login variable left."""
    variable, directory = profile(record, host)
    configured = dict(configured or {})
    bad = refused(configured, credentials)
    if bad:
        raise Refused('invalid_input:adapter_environment:' + bad[0], ', '.join(bad))
    environment = {k: v for k, v in inherited.items() if not strips(k, named)}
    environment.update(configured)
    environment[variable] = directory
    return environment


class Accounts:
    """The account records over one store connection. `authorize(conn, command)` runs inside the
    store transaction (`authority` in production); `sign(bytes)` signs journal records as `signer`."""

    def __init__(self, store, conn, *, principal, signer, sign, authorize=authority, generation=1,
                 observe_pacing=None):
        if not all(_text(v) for v in (principal, signer)):
            raise Refused('invalid_input', 'principal and signer are named')
        self.store, self.conn = store, conn
        self.principal, self.signer, self.sign = principal, signer, sign
        self.authorize, self.generation = authorize, generation
        self.counts = {'accepted': 0, 'refused': 0}
        # VELDO-0236: pacing commands and ends by type/route/outcome, and what each was observed with.
        self.pacing_counts, self.pacing_events = {}, []
        self.observe_pacing = observe_pacing or (lambda event: None)
        conn.command_registry[OPERATION] = {'transaction_transition': self._in_transaction, 'writes': WRITES}
        store.declare_owners(conn, OWNER, kinds={KIND: (OPERATION,)}, prefixes={PREFIX: (OPERATION,)},
                             module=__file__)

    def _own(self):
        # VELDO-0236: several Accounts may share one connection (the API's and the factory loop's); the one writing
        # now judges its own command, never another instance's last one.
        self.conn.command_registry[OPERATION] = {'transaction_transition': self._in_transaction, 'writes': WRITES}

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
            self._own()
            try:
                result = self.store.execute(self.conn, command, self.signer, self.sign, self.generation)
            except self.store.StoreRefused as error:
                if error.code == 'stale_version':
                    continue
                self.counts['refused'] += 1
                raise
            except Refused as error:
                self.counts['refused'] += 1
                if error.code.startswith('invalid_input:account_profile:inside_memory:'):
                    self.counts['memory_profile_refused'] = self.counts.get('memory_profile_refused', 0) + 1
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

    def observe(self, command_id, account, window_id, *, status, reset_at, utilization, source_dispatch, now,
                clear_rejection=False):
        """Record a window or, with no window id, an explicit clear of a stored unified rejection."""
        if ((not _text(window_id) and not (window_id is None and clear_rejection))
                or status not in WINDOW_STATUSES or (reset_at is not None and not _number(reset_at))
                or (utilization is not None and (not _number(utilization) or utilization < 0))
                or not _text(source_dispatch)):
            raise Refused('invalid_input', 'a window id, status, reset, utilization and source dispatch')
        return self._run(command_id, dict(action='observe', account=account, window_id=window_id, status=status,
                                          reset_at=reset_at, utilization=utilization,
                                          source_dispatch=source_dispatch, now=now, clear_rejection=clear_rejection))

    def cap(self, command_id, account, concurrency, *, base, principal, now, assertion_digest=None):
        """VELDO-0131: the owner's change of one account's run concurrency at version `base`, `principal`'s
        command. Never retried: a version that moved is the owner's stale view, refused stale_version."""
        if (not _text(command_id) or not _text(account) or not _text(principal) or not _number(now)
                or type(concurrency) is not int or not 1 <= concurrency <= CAP_LIMIT
                or type(base) is not int or base < 1):
            raise Refused('invalid_input:cap', 'an account at its version and a concurrency from 1 to %d' % CAP_LIMIT)
        target = entity_id(account)
        params = dict(action='cap', account=account, concurrency=concurrency, now=now, command_id=command_id,
                      assertion_digest=assertion_digest)
        command = dict(command_id=command_id, operation=OPERATION, principal=principal, nonce='account/' + command_id,
                       parameters=params, expected_versions={target: base}, artifact_digests=[])
        self._command = command
        self._own()
        try:
            result = self.store.execute(self.conn, command, self.signer, self.sign, self.generation)
        except (self.store.StoreRefused, Refused):
            self.counts['refused'] += 1
            raise
        self.counts['accepted'] += 1
        return result

    # The owner's pacing (VELDO-0236).

    def pause(self, command_id, account, window, *, principal, now, route, provenance=None):
        """Pause `account` until `window`'s last reported reset. Returns the pacing event."""
        return self._pace(command_id, dict(action='pause', account=account, window=window), principal, now, route,
                          provenance)

    def ceiling(self, command_id, account, window, value, *, principal, now, route, provenance=None):
        """Cap `window` of `account` at `value` (a percent 1 to 100, or '+N' relative) until that window resets."""
        return self._pace(command_id, dict(action='ceiling', account=account, window=window, value=value), principal,
                          now, route, provenance)

    def resume(self, command_id, account, *, principal, now, route, provenance=None):
        """End `account`'s pause and its ceilings at once."""
        return self._pace(command_id, dict(action='resume', account=account, window=None), principal, now, route,
                          provenance)

    def _count(self, kind, route, outcome):
        key = '%s/%s/%s' % (kind, route, outcome)
        self.pacing_counts[key] = self.pacing_counts.get(key, 0) + 1

    def _pace(self, command_id, params, principal, now, route, provenance, attempts=5):
        kind = params['action']
        about = {'kind': 'account_pacing', 'operation': kind, 'command_id': command_id, 'principal': principal,
                 'route': route, 'account': params.get('account'), 'window': params.get('window')}
        try:
            if (not _text(command_id) or not _text(principal) or not _number(now) or route not in ROUTES
                    or (provenance is not None and not _text(provenance, ))):
                raise Refused('invalid_input', 'a command id, principal, time, route and provenance')
            if not _text(params.get('account')) or (kind != 'resume' and not _text(params.get('window'))):
                raise Refused('invalid_input:account', 'an account and one of its windows')
            target = entity_id(params['account'])
            params = dict(params, now=now, command_id=command_id, route=route, provenance=provenance)
            for _ in range(attempts):
                # A pause or ceiling already past its end that no loop pass has recorded yet is recorded first, as
                # its own end record, so the new command never overwrites or folds it away unrecorded.
                self.lapse(now, account=params['account'])
                row = self.conn.execute('SELECT version FROM entities WHERE id=?', (target,)).fetchone()
                command = dict(command_id=command_id, operation=OPERATION, principal=principal,
                               nonce='account/' + command_id, parameters=params,
                               expected_versions={target: row[0] if row else 0}, artifact_digests=[])
                self._command = command
                self._own()
                try:
                    self.store.execute(self.conn, command, self.signer, self.sign, self.generation)
                except (self.store.StoreRefused, Refused) as error:
                    if error.code in ('stale_version', UNRECORDED_END):
                        continue
                    raise
                break
            else:
                raise Refused('stale_subject:account', target)
        except (Refused, self.store.StoreRefused) as error:
            self.counts['refused'] += 1
            self._count(kind, route, 'refused')
            event = dict(about, outcome='refused', refusal=error.code)
            self.pacing_events.append(event)
            self.observe_pacing(event)
            raise
        self.counts['accepted'] += 1
        self._count(kind, route, 'accepted')
        event = (read(self.conn, params['account']) or {}).get('pacing') or {}
        observed = dict(about, outcome='accepted', until=event.get('until'), value=event.get('value'),
                        utilization=event.get('utilization'), observation=event.get('observation'),
                        ended=event.get('ended'))
        self.pacing_events.append(observed)
        self.observe_pacing(observed)
        return event

    def lapse(self, now, *, pass_id=None, account=None):
        """One factory loop pass's ends: for each pause or ceiling whose end is at or before `now` still on its
        account record, one signed record of its end, committed once (a second pass finds it gone). Returns the
        end events committed. With `account`, only that account's (a pacing command records them first)."""
        ended = []
        for record in self.list():
            if account is not None and record.get('id') != account:
                continue
            due = []
            pause = record.get('pause')
            if isinstance(pause, dict) and _number(pause.get('until')) and pause['until'] <= now:
                due.append(('pause', pause))
            for window, ceiling in sorted((record.get('ceilings') or {}).items()):
                if isinstance(ceiling, dict) and _number(ceiling.get('until')) and ceiling['until'] <= now:
                    due.append(('ceiling', dict(ceiling, window=window)))
            for kind, item in due:
                command_id = 'account-end/' + hashlib.sha256(json.dumps(
                    [record['id'], kind, item.get('window'), item.get('command_id')]).encode()).hexdigest()[:32]
                target = entity_id(record['id'])
                row = self.conn.execute('SELECT version FROM entities WHERE id=?', (target,)).fetchone()
                params = dict(action=END, account=record['id'], kind=kind, window=item.get('window'),
                              set_by=item.get('command_id'), now=now, command_id=command_id, pass_id=pass_id)
                command = dict(command_id=command_id, operation=OPERATION, principal=self.principal,
                               nonce='account/' + command_id, parameters=params,
                               expected_versions={target: row[0] if row else 0}, artifact_digests=[])
                self._command = command
                self._own()
                try:
                    self.store.execute(self.conn, command, self.signer, self.sign, self.generation)
                except (Refused, self.store.StoreRefused) as error:
                    self._count(END, 'pass', 'refused')
                    event = {'kind': 'account_pacing', 'operation': END, 'command_id': command_id,
                             'account': record['id'], 'window': item.get('window'), 'pass': pass_id,
                             'outcome': 'refused', 'refusal': error.code}
                    self.pacing_events.append(event)
                    self.observe_pacing(event)
                    continue
                self._count(END, 'pass', 'accepted')
                event = (read(self.conn, record['id']) or {}).get('pacing') or {}
                observed = {'kind': 'account_pacing', 'operation': END, 'command_id': command_id,
                            'principal': self.principal, 'account': record['id'], 'window': item.get('window'),
                            'until': item.get('until'), 'ended': event.get('ended'), 'pass': pass_id,
                            'outcome': 'accepted'}
                self.pacing_events.append(observed)
                self.observe_pacing(observed)
                ended.append(event)
        return ended

    def _pacing(self, conn, params, current):
        """The account record after one pacing command or end, inside the transaction, or Refused by name."""
        action, now, account = params['action'], params['now'], params['account']
        if action != END and not factory_owner(conn, self._command.get('principal'), now):
            raise Refused(NOT_FACTORY_OWNER, str(self._command.get('principal')))
        if current is None:
            raise Refused('invalid_input:account', account)
        value = copy.deepcopy(current)
        event = {f: None for f in EVENT_FIELDS}
        event.update(type=action, command_id=params['command_id'], principal=self._command['principal'],
                     route=params.get('route'), account=account, window=params.get('window'), at=now,
                     provenance=params.get('provenance'))
        window_id = params.get('window')
        if action != END and due(current, now):
            # VELDO-0236 AC4: an end not yet recorded is never overwritten or folded into a resume.
            raise Refused(UNRECORDED_END, '%s has a pause or ceiling ended and not yet recorded' % account)
        if action in ('pause', 'ceiling'):
            window = (current.get('windows') or {}).get(window_id)
            if not isinstance(window, dict):
                raise Refused('invalid_input:account', '%s has no window %s' % (account, window_id))
            reset = window.get('reset_at')
            if not _number(reset) or reset <= now:
                raise Refused('invalid_input:%s_reset' % action, '%s reports no reset after now' % window_id)
            observation = {'observed_at': window.get('observed_at'), 'source_dispatch': window.get('source_dispatch'),
                           'reset_at': reset, 'utilization': window.get('utilization')}
            entry = {'until': reset, 'command_id': params['command_id'], 'by': self._command['principal'], 'at': now,
                     'route': params.get('route'), 'observation': observation}
            event.update(until=reset, observation=observation)
            if action == 'pause':
                value['pause'] = dict(entry, window=window_id)
            else:
                used = percent(window.get('utilization'))
                given = params.get('value')
                if used is None:
                    raise Refused('invalid_input:ceiling', '%s has no observed utilization' % window_id)
                relative = isinstance(given, str) and given.strip().startswith('+')
                try:
                    amount = float(given.strip().lstrip('+')) if isinstance(given, str) else given
                except ValueError:
                    amount = None
                if not _number(amount):
                    raise Refused('invalid_input:ceiling', 'a percent from 1 to 100, or +percent')
                limit = round(used + amount, 6) if relative else amount
                if not 1 <= limit <= 100 or (relative and amount <= 0):
                    raise Refused('invalid_input:ceiling', 'the ceiling is a percent from 1 to 100')
                limit = int(limit) if float(limit).is_integer() else limit
                ceilings = dict(current.get('ceilings') or {})
                ceilings[window_id] = dict(entry, value=limit, utilization=used, relative=given if relative else None)
                value['ceilings'] = ceilings
                event.update(value=limit, utilization=used)
        elif action == 'resume':
            ended = []
            if isinstance(current.get('pause'), dict):
                ended.append({'kind': 'pause', 'window': current['pause'].get('window'),
                              'until': current['pause'].get('until'), 'command_id': current['pause'].get('command_id')})
            for window, ceiling in sorted((current.get('ceilings') or {}).items()):
                ended.append({'kind': 'ceiling', 'window': window, 'until': ceiling.get('until'),
                              'command_id': ceiling.get('command_id')})
            value['pause'], value['ceilings'] = None, {}
            event.update(ended=ended)
        else:
            kind, set_by = params.get('kind'), params.get('set_by')
            if kind == 'pause':
                item = current.get('pause') if isinstance(current.get('pause'), dict) else None
            else:
                item = (current.get('ceilings') or {}).get(window_id)
            if not isinstance(item, dict) or item.get('command_id') != set_by or not (
                    _number(item.get('until')) and item['until'] <= now):
                raise Refused('stale_subject:account_pacing', 'no %s of %s ends now' % (kind, account))
            if kind == 'pause':
                value['pause'] = None
            else:
                value['ceilings'] = {w: c for w, c in (current.get('ceilings') or {}).items() if w != window_id}
            event.update(route=None, until=item['until'], value=item.get('value'), utilization=item.get('utilization'),
                         observation=item.get('observation'), provenance=None,
                         ended=[{'kind': kind, 'window': window_id, 'until': item['until'], 'command_id': set_by}])
            event['pass'] = params.get('pass_id')
        value['pacing'] = event
        return value

    def _in_transaction(self, conn, params, before):
        if params.get('action') in PACING + (END,):
            # VELDO-0236: the owner's pacing is judged by VELDO-0203's factory owner rule, an end by the pass.
            target = entity_id(params['account'])
            current = copy.deepcopy((before.get(target) or {}).get('data'))
            if params['action'] == END and self._command.get('principal') != self.principal:
                raise Refused('missing_authority')
            return {target: {'kind': KIND, 'data': self._pacing(conn, params, current)}}
        if self.authorize(conn, self._command) is not True:
            raise Refused('missing_authority')
        target = entity_id(params['account'])
        current = copy.deepcopy((before.get(target) or {}).get('data'))
        action = params['action']
        if action == 'register':
            spec = importlib.util.spec_from_file_location('account_memory', Path(__file__).with_name('control_memory.py'))
            memory = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(memory)
            try:
                memory.account_outside(conn, params['profiles'])
            except memory.Refused as error:
                raise Refused(error.code) from None
            if current is not None:
                raise Refused('duplicate_account:' + params['account'], params['account'])
            for (data,) in conn.execute('SELECT data FROM entities WHERE kind=? ORDER BY id', (KIND,)):
                other = json.loads(data)
                for host, directory in params['profiles'].items():
                    if _text((other.get('profiles') or {}).get(host)) and _same_profile(other['profiles'][host], directory):
                        # VELDO-0160: the same login under another name is a second registration of it.
                        raise Refused('duplicate_account:' + other['id'], '%s on %s' % (directory, host))
            value = {'schema': SCHEMA, 'id': params['account'], 'provider': params['provider'],
                     'label': params['label'], 'status': 'active', 'profiles': params['profiles'],
                     'windows': {}, 'concurrency': params['concurrency'], 'registered_at': params['now']}
        elif current is None:
            raise Refused('missing_authority:account', params['account'])
        elif action == 'status':
            value = dict(current, status=params['status'])
        elif action == 'cap':
            member = _member(conn, self._command.get('principal')) or {}
            if member.get('scope') not in ('*', ['*']):
                raise Refused('missing_authority:scope', 'an account is factory scope')
            if current.get('concurrency') == params['concurrency']:
                raise Refused('invalid_input:unchanged', 'the account already has this concurrency')
            entry = {'concurrency': params['concurrency'], 'previous': current.get('concurrency'),
                     'by': self._command['principal'], 'at': params['now'], 'command_id': params['command_id']}
            if params.get('assertion_digest'):
                entry.update(channel='api', assertion_digest=params['assertion_digest'])
            value = dict(current, concurrency=params['concurrency'],
                         concurrency_history=list(current.get('concurrency_history') or []) + [entry])
        elif action == 'observe':
            unified = current['windows'].get('unified')
            if (params.get('clear_rejection') and unified is not None
                    and unified.get('status') == 'rejected' and unified['observed_at'] <= params['now']):
                # The clear applies to the account, including a rejection from an earlier dispatch.
                current['windows']['unified'] = dict(unified, status='allowed', observed_at=params['now'],
                                                     source_dispatch=params['source_dispatch'])
            if params['window_id'] is None:
                return {target: {'kind': KIND, 'data': current}}
            prior = current['windows'].get(params['window_id'])
            if prior is not None and prior['observed_at'] > params['now']:
                # Keep any unified lift while leaving the newer companion unchanged.
                return {target: {'kind': KIND, 'data': current}}
            if not params.get('clear_rejection') and params['status'] is None and prior is not None and blocking({'windows': {'w': prior}}, params['now']):
                # VELDO-0166: keep a rejection, but let a later report supply its missing reset.
                # The account then remains blocked only until that reported time.
                if prior.get('reset_at') is None and params['reset_at'] is not None:
                    params = dict(params, status='rejected')
                else:
                    return {}
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
