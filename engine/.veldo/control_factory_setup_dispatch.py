"""VELDO-0185: the dispatch configuration factory setup lays down, so the installed factory runs work.

WHAT IT LAYS DOWN, for the engines the host's account registry names (accounts.py, the registry under the
served workspace's Git common directory, or VELDO_RUNS_ROOT as `veldo account add` reads it):

  adapters            one launch receiver adapter per engine the registry names, written by the installer into
                      every receiver configuration (control_service install's `adapters`): `claude_code` names
                      its pinned version, `codex` its vendor binary (VELDO-0186), each marked `account_login`,
                      so the receiver checks the account's own login before acceptance (control_launch).
  work                the veldo.factory_work/v1 configuration (host/work.json, passed as the installer's
                      `work`): the enrolled workspace's repository, its builder from the default team's
                      `implementation` role and its reviewer from `independent_review`, each with
                      control_service's ROLE_FIELDS.
  principals          the owner's signed enroll_principal of `authority` and `launch-receiver` with the
                      reservation_service role (their key is the journal key both sign with).
  factory project     the owner's signed control_project `activate` of `factory` when there is none.
  default team        one capability configuration revision per role and one default team revision, each the
                      owner's signed command through VELDO-0203's OwnerRevisions, its nonce its command id:
                      project_manager, elaboration and implementation on Claude Code and independent_review on
                      Codex, all four on one engine when the registry names only one.
  accounts            each registry account the store holds no record of, through control_accounts
                      Accounts.register with the fields accounts.py `registration` prints, command id
                      `register/<account>`, concurrency 1.
  policies            VELDO-0204's reservation policies, after `authority` holds its role.
  logins              each registered account's engine's own login status in that account's profile
                      environment: Claude Code's `auth status`, Codex's `login status`; one that is not its
                      subscription login is named with its login step (accounts.py `login_step`) and refused by
                      name (missing_authority:account_login:<account>); the others carry on.

Every store writer is the INSTALLED engine's module, loaded from the installation's own directory, so what it
owns in the store is bound to the code the service runs. A host whose registry names no account has nothing to
dispatch to: none of this is laid down and setup says so (`dispatch` deferred). Standard library only.
"""
import importlib.util
import json
import os
from pathlib import Path
import socket
import tempfile
import time


def organ(name, directory=None):
    path = Path(directory or Path(__file__).parent) / (name + '.py')
    spec = importlib.util.spec_from_file_location('setup_dispatch_%s_%s' % (name, os.urandom(4).hex()), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# The operating-model walkthrough's engines per required role (control_team REQUIRED_ROLES).
WALKTHROUGH = {'project_manager': 'claude_code', 'elaboration': 'claude_code', 'implementation': 'claude_code',
               'independent_review': 'codex'}
# The default team's workers: the enrolled PM, and one agent identity per other role.
WORKERS = {'project_manager': 'pm', 'elaboration': 'elaborator', 'implementation': 'builder',
           'independent_review': 'reviewer'}
PERMISSIONS = {'project_manager': ['objective', 'feature', 'backlog_item', 'decision_request', 'finding'],
               'elaboration': ['feature', 'backlog_item', 'finding'], 'implementation': ['finding'],
               'independent_review': ['finding']}
# Each role's budget, and the factory project's coordination budget the account policies sum (VELDO-0204).
ROLE_BUDGET = {'capacity': 1, 'invocations': 20, 'wall_seconds': 3600}
FACTORY_BUDGET = {'capacity': 4, 'invocations': 400, 'wall_seconds': 7 * 86400}
TASKS = {'implementation': 'build the unit', 'independent_review': 'review the unit'}
RESERVATION_PRINCIPALS = ('authority', 'launch-receiver')
RESERVATION_ROLE = 'reservation_service'
WORK_FILE = 'work.json'
ACCOUNT_LOGIN = 'missing_authority:account_login:'
STEPS = ('work_configuration', 'reservation_principals', 'factory_project', 'default_team', 'account_registration',
         'reservation_policies', 'account_login')


def registry_root(workspace, enrollment):
    """Where `veldo account add` keeps the host's account registry for this workspace: VELDO_RUNS_ROOT, else
    `veldo` under the workspace's Git common directory (accounts.py accounts_root)."""
    return os.environ.get('VELDO_RUNS_ROOT') or os.path.join(enrollment.git_common_dir(workspace), 'veldo')


def read_registry(root, Refused, host=None):
    """[{account, provider, label, profiles, login_step}] for every account the registry lists, read only."""
    AR = organ('accounts')
    host = host or socket.gethostname()
    found = []
    for name in AR.list_accounts(root):
        try:
            fields = AR.registration(name, host=host, root=root)
            step = AR.login_step(AR.get(name, root))
        except (AR.AccountError, KeyError) as error:
            raise Refused('invalid_input:account_registry:' + str(name), str(error)) from None
        if fields['provider'] not in AR.PROFILE_ENV or not os.path.isabs(next(iter(fields['profiles'].values()))):
            raise Refused('invalid_input:account_registry:' + str(name), 'a provider and an absolute profile')
        found.append(dict(fields, login_step=step))
    return found


def plan(workspace, engines, enrollment, Refused, root=None):
    """The dispatch plan setup checks before its first write: the registry, its engines, each role's engine,
    the adapters. None when the registry names no account."""
    root = root or registry_root(workspace, enrollment)
    accounts = read_registry(root, Refused)
    if not accounts:
        return None
    present = sorted({a['provider'] for a in accounts})
    roles = dict(WALKTHROUGH) if set(WALKTHROUGH.values()) <= set(present) else {r: present[0] for r in WALKTHROUGH}
    return {'registry': root, 'accounts': accounts, 'engines': present, 'roles': roles,
            'adapters': adapters(engines, present)}


def adapters(engines, present):
    """One receiver adapter per engine present: Claude Code's pinned version, Codex's vendor binary."""
    found = {}
    if 'claude_code' in present:
        found['claude_code'] = {'engine': 'claude_code', 'executable': {'version': engines['claude_code']['version']},
                                'argv': [], 'account_login': True}
    if 'codex' in present:
        vendor = engines['codex']['executable']
        found['codex'] = {'engine': 'codex', 'executable': vendor,
                          'argv': [vendor] + list(organ('control_engine_codex').FLAGS), 'account_login': True}
    return found


def definition(role, engine):
    return dict(role=role, engine=engine, native_tools=[], mcp=[], skills=[], instructions=[], settings={})


def team(CT, roles, revisions):
    """The default team over control_team's REQUIRED_ROLES, each role naming its capability revision."""
    found = {}
    for role in CT.REQUIRED_ROLES:
        found[role] = dict(kind='required', capability_configuration={'role': role, 'revision': revisions[role]},
                           workers=[WORKERS[role]], responsibilities=[CT.REQUIRED_RESPONSIBILITY[role]],
                           expertise=['software'], proposal_permissions=list(PERMISSIONS[role]),
                           engines=[roles[role]], budget=dict(ROLE_BUDGET),
                           independence={'distinct_from': list(CT.REQUIRED_SEPARATION.get(role, ()))})
    return {'roles': found}


def work(repository, roles_of_team, engine_of):
    """The work configuration from a team's roles: the builder from `implementation`, the reviewer from
    `independent_review`, each on the adapter of its role's engine (adapters are named by engine)."""
    def role(name):
        spec = roles_of_team[name]
        return {'identity': spec['workers'][0], 'adapter': engine_of[name],
                'configuration': dict(spec['capability_configuration']), 'seconds': spec['budget']['wall_seconds'],
                'payload': {'task': TASKS[name]}}
    return {'schema': 'veldo.factory_work/v1',
            'repositories': {repository: {'builder': role('implementation'), 'reviewers': [role('independent_review')]}}}


def text(value):
    return json.dumps(value, indent=1, sort_keys=True) + '\n'


def setup_work(CT, repository, dispatch):
    """The work configuration of a fresh host: from the team setup saves (every revision its first)."""
    return work(repository, team(CT, dispatch['roles'], {r: 1 for r in CT.REQUIRED_ROLES})['roles'], dispatch['roles'])


def checked_work(CS, data, repositories, found_adapters, Refused):
    """The installer's own check of a work configuration (control_service installable_work), before a write."""
    with tempfile.TemporaryDirectory(prefix='veldo-work-') as directory:
        path = os.path.join(directory, WORK_FILE)
        Path(path).write_text(data)
        try:
            CS.installable_work(path, repositories, found_adapters)
        except CS.Refused as error:
            raise Refused(error.code, str(error)) from None


# ---------------------------------------------------------------------------------------------
# The store steps, through the installed engine's writers
# ---------------------------------------------------------------------------------------------

def held(conn):
    """What the store already holds of these steps, read only: {step: done}."""
    def row(identity):
        found = conn.execute('SELECT kind, data FROM entities WHERE id=?', (identity,)).fetchone()
        return (found[0], json.loads(found[1])) if found else (None, None)
    PJ, ACC, TR = organ('control_project'), organ('control_accounts'), organ('control_team_routes')
    principals = all(RESERVATION_ROLE in ((row(p)[1] or {}).get('roles') or []) for p in RESERVATION_PRINCIPALS)
    project = row(PJ.project_id(PJ.FACTORY_PROJECT))[0] is not None
    head = row(TR.HEAD)[0] is not None
    accounts = {json.loads(d)['id'] for (d,) in conn.execute('SELECT data FROM entities WHERE kind=?', (ACC.KIND,))}
    return {'reservation_principals': principals, 'factory_project': project, 'default_team': head,
            'accounts': accounts}


def policies_due(conn, domain):
    """Whether any reservation policy VELDO-0204 derives is absent or differs from the stored one, read only."""
    RP = organ('control_reservation_policies')
    return any(caps is not None and (RP._policy(conn, domain, scope, subject)[1] or {}).get('caps') != caps
               for scope, subject, caps, _source in RP.derive(conn))


class Store:
    """The installed engine's writers on one connection of the store, while the caller holds its lock."""

    def __init__(self, bin_dir, ingress, owner, owner_sign, lock, clock=time.time):
        self.bin, self.owner, self.owner_sign, self.lock, self.clock = Path(bin_dir), owner, owner_sign, lock, clock
        IN = organ('control_channel_ingress', bin_dir)
        self.ingress = IN.open_ingress(ingress)
        self.conn, self.S = self.ingress.conn, self.ingress.activations.S
        try:
            self.CM = organ('control_membership', bin_dir)
            self.CM.attach(self.S)
            config = IN.load_config(ingress)
            self.ids, self.generation = dict(config['authority_ids']), config['authority_generation']
            self.principal, self.sign = IN.journal_signer(config['journal'])
            self.journal_key = config['journal']['key']
            self.TR = organ('control_team_routes', bin_dir)
            self.CT = self.TR.CT
        except BaseException:
            self.conn.close()
            raise

    def close(self):
        self.conn.close()

    def head(self):
        return self.conn.execute('SELECT COALESCE(MAX(seq), 0) FROM journal').fetchone()[0]

    def activate(self, command_id):
        """The owner's signed control_project `activate` of `factory`, owned by him."""
        PJ = self.CT.PJ
        projects = PJ.Projects(self.S, self.CM, self.conn, self.ids, self.principal, self.sign,
                               stop=lambda *_: False, authority_generation=self.generation)
        command = dict(self.ids, operation='activate', project=PJ.FACTORY_PROJECT, principal=self.owner,
                       command_id=command_id, nonce=command_id, owner=self.owner,
                       charter={'purpose': 'The factory\'s own work, staffed by its default team.'},
                       execution_repository=self.ids['repository_uuid'],
                       authority_policy={'team_amendment': [PJ.OWNER_ROLE]}, coordination_budget=dict(FACTORY_BUDGET))
        return projects.apply({'command': command, 'signature': self.owner_sign(self.S.canonical_bytes(command))})

    def packet(self, operation, parameters, command_id):
        return owner_packet(self.S, self.CM, self.conn, self.ids, self.owner, self.owner_sign, self.clock, operation,
                            parameters, command_id)

    def revisions(self):
        """The owner revision writer (VELDO-0203) over the existing configuration and team writers."""
        OR, CG = organ('control_owner_revisions', self.bin), organ('control_agent_config', self.bin)
        ACT = organ('control_channel_activation', self.bin)
        configurations = CG.Configurations(self.S, self.conn, domain=self.ids['domain_uuid'],
                                           repository=self.ids['repository_uuid'], signer=self.principal,
                                           sign=self.sign, generation=self.generation)
        teams = self.CT.Teams(self.S, self.CM, self.conn, self.ids, self.principal, self.sign,
                              inbox=self.ingress.inbox, assignment=self.ingress.settlement.I, requester='pm',
                              request_sign=ACT.ssh_signer(self.journal_key), authority_generation=self.generation)
        routes = self.TR.TeamRoutes(teams, self.ingress.settlement, self.ingress.presenter)
        return CG, OR.OwnerRevisions(self.S, self.CM, self.conn, ids=self.ids, authority_lock=self.lock,
                                     configurations=configurations, team_routes=routes)

    def default_team(self, roles, prefix):
        CG, writer = self.revisions()
        return save_team(self.conn, CG, self.CT, self.ids, roles, prefix, writer.apply, self.packet)

    def register(self, accounts):
        """Each registry account the store holds no record of, by control_accounts Accounts.register."""
        ACC = organ('control_accounts', self.bin)
        writer = ACC.Accounts(self.S, self.conn, principal=self.owner, signer=self.principal, sign=self.sign,
                              generation=self.generation)
        registered = []
        for account in accounts:
            if ACC.read(self.conn, account['account']) is not None:
                continue
            writer.register('register/' + account['account'], account['account'], account['provider'],
                            account['label'], account['profiles'], concurrency=1, now=self.clock())
            registered.append(account['account'])
        return registered

    def provision(self):
        """VELDO-0204's reservation policies on this connection, under the lock, written as `authority`."""
        RP = organ('control_reservation_policies', self.bin)
        answer = RP.provision(self.conn, self.lock, RP.writer(self.S, self.conn, domain=self.ids['domain_uuid'],
                                                               repository=self.ids['repository_uuid'],
                                                               principal=self.principal, sign=self.sign,
                                                               generation=self.generation), caller='setup')
        if answer['outcome'] != 'done':
            raise StepRefused(answer.get('refusal') or 'unknown_outcome:reservation_policies')
        return answer


def owner_packet(S, CM, conn, ids, owner, owner_sign, clock, operation, parameters, command_id):
    """VELDO-0203's owner revision packet: his command and envelope, its nonce its command id, SSH-signed by him."""
    command = dict(command_id=command_id, operation=operation, target='authority', parameters=parameters)
    state = CM.authority_state(S, conn)
    envelope = dict(ids, schema=CM.AC.ENVELOPE_SCHEMA, principal=owner, command_id=command_id,
                    command_digest=CM.AC.canonical_command_digest(command), nonce=command_id, request_revision=1,
                    expires_at=clock() + 600, membership_version=state['membership_version'],
                    delegation_version=state['delegation_version'])
    return dict(command=command, envelope=envelope, signature=owner_sign(CM.AC.canonical_envelope_bytes(envelope)))


def save_team(conn, CG, CT, ids, roles, prefix, apply, packet):
    """AC1: one capability configuration revision per role the store has none of, then the default team naming
    each role's head revision, each the owner's packet answered by `apply` (the writer under this run's lock, or
    the running service). Returns (team, what was saved)."""
    revisions, saved = {}, []
    for role in CT.REQUIRED_ROLES:
        try:
            revisions[role] = CG.read(conn, ids['domain_uuid'], ids['repository_uuid'], role)['revision']
            continue
        except CG.Refused:
            pass
        answer = apply(packet('save_capability_configuration', dict(definition=definition(role, roles[role]), base=0),
                              '%s-configuration-%s' % (prefix, role)))
        if not answer.get('ok'):
            raise StepRefused(answer.get('reason') or 'unknown_outcome:default_team')
        revisions[role] = answer['result']['revision']
        saved.append('configuration:%s:%d' % (role, revisions[role]))
    chosen = team(CT, roles, revisions)
    answer = apply(packet('save_default_team', dict(team=chosen, base=0), prefix + '-default-team'))
    if not answer.get('ok'):
        raise StepRefused(answer.get('reason') or 'unknown_outcome:default_team')
    saved.append('default_team:%d' % answer['result']['revision'])
    return chosen, saved


class StepRefused(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def saved_team(conn, ids):
    """(team, {role: engine}) of the store's default team at its head revision, or (None, None)."""
    TR = organ('control_team_routes')
    found = conn.execute('SELECT data FROM entities WHERE id=?', (TR.HEAD,)).fetchone()
    if not found:
        return None, None
    revision = json.loads(found[0])['revision']
    data = json.loads(conn.execute('SELECT data FROM entities WHERE id=?', (TR.default_id(revision),)).fetchone()[0])
    CG = organ('control_agent_config')
    engines = {}
    for role, spec in data['team']['roles'].items():
        reference = spec.get('capability_configuration') or {}
        try:
            engines[role] = CG.read(conn, ids['domain_uuid'], ids['repository_uuid'], reference.get('role'),
                                    reference.get('revision'))['engine']
        except CG.Refused:
            engines[role] = None
    return data['team'], engines


# ---------------------------------------------------------------------------------------------
# The accounts' login, read only
# ---------------------------------------------------------------------------------------------

def logins(bin_dir, conn, accounts, found_adapters, state_root, host=None):
    """Each registry account's own login as its engine reports it, run in its profile environment exactly as
    the launch receiver runs it: [{account, provider, outcome, login, refusal, login_step}]."""
    L = organ('control_launch', bin_dir)
    ACC = L.ACC
    host = host or socket.gethostname()
    found = []
    for account in accounts:
        entry = {'account': account['account'], 'provider': account['provider'], 'login_step': account['login_step']}
        adapter = found_adapters.get(account['provider']) or {}
        record = ACC.read(conn, account['account'])
        module = L.ENGINES.get(account['provider'])
        try:
            bound = module.bind(adapter, state_root)
            environment = ACC.login_environment(dict(os.environ), record, host, L.STRIPPED,
                                                adapter.get('environment') or {}, L.CREDENTIALS)
            kind = module.account_login(bound, environment, None)
        except (module.Refused, ACC.Refused) as error:
            kind = 'unchecked:' + error.code
        if kind is None:
            entry.update(outcome='logged_in')
        else:
            entry.update(outcome='refused', login=kind, refusal=ACCOUNT_LOGIN + account['account'])
        found.append(entry)
    return found


def login_step(found):
    """The setup step of the accounts' logins, which writes nothing: checked when every account is logged in,
    else refused naming each, while the others carry on."""
    refused = [e for e in found if e['outcome'] != 'logged_in']
    return {'step': 'account_login', 'outcome': 'refused' if refused else 'checked', 'accounts': found,
            'refusals': [e['refusal'] for e in refused],
            'metrics': {'accounts': len(found), 'not_logged_in': len(refused)}}


# ---------------------------------------------------------------------------------------------
# A re-run's files: the receivers' adapters and state root, the work configuration
# ---------------------------------------------------------------------------------------------

def receiver_states(paths, found_adapters, root, differs):
    """Read only: {path: 'equal' | 'upgrade'}. A receiver configuration gains its adapters only where it names
    none, and its state root only where it lacks it or holds it as null; any other difference is refused."""
    states = {}
    for path in sorted(paths):
        try:
            held_config = json.loads(Path(path).read_text())
        except (OSError, ValueError):
            raise differs(path) from None
        if not isinstance(held_config, dict):
            raise differs(path)
        if held_config.get('adapters') and held_config['adapters'] != found_adapters:
            raise differs(path)
        if held_config.get('state_root') is not None and held_config['state_root'] != root:
            raise differs(path)
        states[path] = 'equal' if held_config.get('adapters') and held_config.get('state_root') else 'upgrade'
    return states


def apply_receivers(states, found_adapters, root, API):
    added = []
    for path, state in sorted(states.items()):
        if state != 'upgrade':
            continue
        config = json.loads(Path(path).read_text())
        keys = []
        if not config.get('adapters'):
            config['adapters'] = found_adapters
            keys.append('adapters')
        if config.get('state_root') is None:
            config['state_root'] = root
            keys.append('state_root')
        if keys:
            API.replace_file(path, API.text(config), 0o600)
            added.append({'path': path, 'keys': keys})
    return {'step': 'receiver_adapters', 'outcome': 'done' if added else 'already_done', 'added': added}
