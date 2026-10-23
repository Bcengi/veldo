"""The running authority service's part of a new project from chat (VELDO-0143).

WHAT IT DOES. The service's NewProjectPass runs when something happened that it acts on, never on a timer
or by reading the journal for a change (control_service A NEW PROJECT FROM CHAT): at the instance's start,
after a packet or channel pass that advanced the journal (an owner's answer, a take-on the service answered),
when the output pipe of a provisioner it started reaches its end, and when a new-project decision is written
outside the pass (the factory PM's run settles one from his own message or his correction, or presents one,
in a factory loop pass: NewProjects' notify, VELDO-0143 F1). Each pass:

  0. finishes each presentation a crash or the store interrupted (control_project_proposal NewProjects.resume,
     from the decision's record: the same proposal, the same commands, never a second message);
  1. applies each settled answer to a presented new-project proposal (control_project_proposal
     NewProjects.apply_settled: settled, handed to the factory PM as a correction, or rejected; nothing is
     ever asked here);
  2. for each settled decision whose repository has no record yet, starts the repository provisioner, the
     registered protected effect control_effect_executor_creation (PROTECTED_EFFECTS), as its own process
     with the provisioner configuration (provisioner_path), once per decision, its output on a pipe the
     service's poll set watches (pipes, readable); an installation that has none fails the decision
     unavailable_service:provisioner by name, and its report tells the owner (a proposal is not even made
     there, NewProjects.propose, so this is a configuration removed after the answer). A record the decision left
     `provisioning` with no enrollment and no provisioner of this instance running (a run that ended with
     an earlier instance) has the provisioner started once more, which names it interrupted (or refuses,
     touching nothing, while that run is still live). A record `provisioning` with its binding is the
     running service's to take on (VELDO-0161), at the provisioner's hand-off or at an instance's start;
  3. for each settled decision whose repository ended `failed`, fails the decision with that reason (its
     VELDO-0128 report tells the owner; never ready);
  4. for each settled decision whose repository is `active`, the running service having taken it on in this
     process, applies the same settlement as the project's activation (control_project_proposal.activate):
     first the repository's accepted base and the default team's capability configurations at the
     revisions the team names (so the new repository's Runner binds them), then the activation, the first
     team revision, the first objective proposed and accepted, the decision activated (its report tells the
     owner); and the factory loop gains the
     repository's line (FactoryLoop.add_line), so its first unit is dispatched in it.

Every step is observed (kind `new_project`) with the decision, the repository and the outcome or named
refusal, never a token or the owner's words. Organs are the service module's own instances (`modules`),
so every registration is on the one store module the service runs.
"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time


HERE = Path(__file__).resolve().parent


def organ(name):
    spec = importlib.util.spec_from_file_location('service_projects_' + name, HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PP = organ('control_project_proposal')
# The protected effects this service starts, by name, each the trusted executable it runs.
PROTECTED_EFFECTS = {'repository_provisioning': 'control_effect_executor_creation.py'}
INITIAL_REVISION = 'initial-revision:'
# What factory setup names the provisioner configuration in the state root's host directory.
PROVISIONER_FILE = 'provisioner.json'


def accept_base(store, path, domain, repository, workspace, commit, principal, sign, generation):
    """The repository's first accepted revision (VELDO-0035): the commit it was created or adopted at, on a
    connection of its own (a read-set registration replaces its connection's)."""
    RS = organ('control_readset')
    conn = store.open_store(path)
    try:
        revision = INITIAL_REVISION + repository
        if conn.execute('SELECT 1 FROM entities WHERE id=?', (revision,)).fetchone() is not None:
            return revision
        RS.attach_revisions(store, conn, domain, {repository: workspace}).accept(
            revision, repository, commit, principal, documents={}, signer=principal, sign=sign,
            authority_generation=generation)
        return revision
    finally:
        conn.close()


def copy_configurations(conn, CFG, writer, domain, source, team, owner):
    """Every capability configuration the team's roles name, with the skills they name, copied revision by
    revision from the repository the default team was saved against (`source`) into the new repository, so
    each {role, revision} the team names reads the same definition there. Returns what was copied."""
    copied = []

    def copy(kind, name, revision):
        try:
            CFG.read(conn, domain, writer.repository, name, revision, kind)
            return
        except CFG.Refused:
            pass
        for number in range(1, revision + 1):
            try:
                CFG.read(conn, domain, writer.repository, name, number, kind)
                continue
            except CFG.Refused:
                pass
            held = CFG.read(conn, domain, source, name, number, kind)
            if kind == CFG.KINDS[0]:
                for skill in held.get('skills') or []:
                    copy(CFG.KINDS[1], skill['skill'], skill['revision'])
            definition = {k: v for k, v in held.items() if k not in ('revision', 'previous', 'digest', 'assertion_digest')}
            writer.save(definition, principal=owner, base=number - 1, kind=kind,
                        command_id='configuration-copy:%s:%s:%s:%d' % (writer.repository, kind, name, number))
            copied.append({'kind': kind, 'name': name, 'revision': number})
    for role in sorted((team.get('roles') or {}).values(), key=lambda r: json.dumps(r, sort_keys=True)):
        configuration = role.get('capability_configuration') or {}
        if configuration.get('role') and configuration.get('revision'):
            copy(CFG.KINDS[0], configuration['role'], configuration['revision'])
    return copied


class Provisioner:
    """A provisioner process this service started, and what it wrote on its output pipe. Its end is the pipe's
    end, which the service's poll set sees; nothing waits on it or polls it."""

    def __init__(self, process):
        self.process, self.output, self.done = process, b'', False

    def fileno(self):
        return self.process.stdout.fileno()

    def pump(self):
        """Take what the pipe holds; at its end, reap the process. True once it ended."""
        try:
            chunk = os.read(self.fileno(), 65536)
        except OSError:
            chunk = b''
        if chunk:
            # Its answer is its last line; only the end of what it wrote is kept.
            self.output = (self.output + chunk)[-65536:]
            return False
        self.process.stdout.close()
        self.process.wait()
        self.done = True
        return True

    def reason(self):
        """The provisioner's answer's reason: its last output line (main), or unknown_outcome:provisioner."""
        try:
            return json.loads(self.output.decode().strip().splitlines()[-1]).get('reason')
        except (ValueError, IndexError, AttributeError, UnicodeDecodeError):
            return 'unknown_outcome:provisioner'


class NewProjectPass:
    """One running service's new-project work (module docstring). `modules` are the service module's globals
    (its S, CM, AC, I and SIG)."""

    def __init__(self, service, modules):
        self.service, self.m = service, modules
        self.decisions = None
        # {decision: Provisioner} started by this instance; the decisions whose interrupted record this instance
        # has had judged; whether a pass is running (its own writes make no pass due: it acts on them itself).
        self.running, self.rejudged, self.passing = {}, set(), False

    def _ids(self):
        return dict(self.service.channel.ingress.settlement.ids)

    def pm_sign(self, body):
        return self.m['SIG'].sign_bytes(self.service.config['journal_key'], body, self.m['AC'].SIGNATURE_NAMESPACE)

    def new_projects(self):
        if self.decisions is None and self.service.channel is not None:
            ingress, s = self.service.channel.ingress, self.service
            config = self.provisioner()
            self.decisions = PP.NewProjects(
                self.m['S'], self.m['CM'], s.conn, self._ids(), s.principal, s.sign, inbox=ingress.inbox,
                settlement=ingress.settlement, presenter=ingress.presenter, assignment=self.m['I'], requester='pm',
                request_sign=self.pm_sign, templates=(config or {}).get('templates'), generation=s.generation,
                provisioner=self.provisioner_path, notify=self.written)
        return self.decisions

    def written(self, state):
        """A new-project decision was written: outside a pass (the factory PM's run settled, presented or failed
        it), the new-project pass is due, so a decision settled there reaches the provisioner with no other event."""
        if not self.passing:
            self.service.projects_due = True

    def provisioner_path(self):
        """The provisioner configuration: the installation's `provisioner`, else the one factory setup lays down in
        the state root's host directory (<state root>/host/provisioner.json, beside the store's directory), when it
        is there. The provisioner refuses a file that is not this account's own 0600 one."""
        named = self.service.config.get('provisioner')
        if named:
            return named
        store = self.service.config.get('store_path')
        laid = os.path.join(os.path.dirname(os.path.dirname(store)), 'host', PROVISIONER_FILE) if store else None
        return laid if laid and os.path.isfile(laid) else None

    def provisioner(self):
        path = self.provisioner_path()
        if not path:
            return None
        try:
            return json.loads(Path(path).read_text())
        except (OSError, ValueError):
            return None

    def _log(self, event):
        self.service._log(dict(event, kind='new_project', at=time.time(), domain_uuid=self.service.domain))
        return event

    def run(self):
        """One pass (module docstring). Returns the events."""
        decisions = self.new_projects()
        if decisions is None:
            return []
        self.passing = True
        try:
            return self._run(decisions)
        finally:
            self.passing = False

    def _run(self, decisions):
        made = [self._log(e) for e in decisions.resume()]
        made += [self._log(e) for e in decisions.apply_settled()]
        settled = decisions.settled_decisions()
        # A provisioner that ended after its decision was finished (activated, or failed by its record) is gone.
        for decision in [d for d, one in self.running.items() if one.done and d not in {r['id'] for r in settled}]:
            del self.running[decision]
        for record in settled:
            repository = (record.get('proposal') or {}).get('repository')
            held = self.m['REPO'].read(self.service.conn, repository)
            if held is not None and held.get('state') == 'failed':
                decisions.finish(record['id'], activated=False, reason=held.get('reason'))
                event = {'operation': 'failed', 'decision': record['id'], 'repository': repository,
                         'refusal': held.get('reason'), 'step': held.get('failed_step')}
            elif held is not None and held.get('state') == 'active':
                event = self.activate(record, held)
            elif record['id'] in self.running:
                event = self.ended(record, held)
            elif held is None:
                event = self.provision(record)
            elif not held.get('enrollment') and record['id'] not in self.rejudged:
                self.rejudged.add(record['id'])
                event = self.provision(record)
            else:
                event = None
            if event:
                made.append(self._log(event))
        return made

    def pipes(self):
        """{fd: decision}: the output pipe of every provisioner this instance started that has not ended."""
        return {one.fileno(): decision for decision, one in self.running.items() if not one.done}

    def readable(self, fd):
        """The poll set found a provisioner's pipe readable: what it wrote is taken. True once it ended."""
        for one in self.running.values():
            if not one.done and one.fileno() == fd:
                return one.pump()
        return False

    def ended(self, record, held):
        """A provisioner this instance started, once it ended: its answer read; a decision whose provisioner
        ended with no record (it refused before writing one) failed with the provisioner's reason."""
        decision = record['id']
        one = self.running[decision]
        if not one.done:
            return None
        del self.running[decision]
        # Judged by this instance: a record it left provisioning with no binding is not started for again.
        self.rejudged.add(decision)
        reason = one.reason()
        about = {'operation': 'provision', 'decision': decision, 'repository': record['proposal']['repository'],
                 'effect': 'repository_provisioning', 'exit': one.process.returncode}
        if held is None:
            self.decisions.finish(decision, activated=False, reason=reason or 'unknown_outcome:provisioner')
            return dict(about, outcome='refused', refusal=reason)
        return dict(about, outcome='ended', state=held.get('state'), refusal=reason)

    def provision(self, record):
        """Start the provisioner for `record`, its output on a pipe (Provisioner)."""
        decision = record['id']
        about = {'operation': 'provision', 'decision': decision, 'repository': record['proposal']['repository'],
                 'effect': 'repository_provisioning'}
        config = self.provisioner_path()
        if not config:
            self.decisions.finish(decision, activated=False, reason='unavailable_service:provisioner')
            return dict(about, outcome='failed', refusal='unavailable_service:provisioner')
        process = subprocess.Popen([sys.executable, '-B', str(HERE / PROTECTED_EFFECTS['repository_provisioning']),
                                    str(config), decision], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL, close_fds=True, start_new_session=True)
        self.running[decision] = Provisioner(process)
        return dict(about, outcome='started', pid=process.pid)

    def activate(self, record, held):
        """THE SAME SETTLEMENT ACTIVATES, in this process, once the repository is active. VELDO-0143 R3-1: the
        team, intake and project owners it builds register on the service's one connection, replacing the factory
        line's; once it is done the connection's registrations are as it found them, and only then does the loop
        gain the repository's line."""
        s = self.service
        registry = s.conn.command_registry
        before = dict(registry)
        try:
            result = self._activate(record, held)
        finally:
            registry.clear()
            registry.update(before)
        if result['outcome'] == 'activated' and s.loop is not None:
            receiver = ((s.config.get('receiver') or {}).get('configs') or {}).get(result['repository'])
            result['line'] = s.loop.add_line(result['repository'], receiver)
        return result

    def _activate(self, record, held):
        s, m = self.service, self.m
        S, CM = m['S'], m['CM']
        ingress = s.channel.ingress
        ids = self._ids()
        repository = held['repository']
        about = {'operation': 'activate', 'decision': record['id'], 'repository': repository}
        proposal = record['proposal']
        CFG, CT = organ('control_agent_config'), organ('control_team')
        try:
            commit = held.get('scaffold_commit') or held.get('base_commit')
            accept_base(S, s.config['store_path'], s.domain, repository, held['path'], commit, s.principal, s.sign,
                        s.generation)
            saved = PP._row(s.conn, organ('control_team_routes').default_id(proposal['team']['revision']))
            writer = CFG.Configurations(S, s.conn, domain=s.domain, repository=repository, signer=s.principal,
                                        sign=s.sign, generation=s.generation)
            copy_configurations(s.conn, CFG, writer, s.domain, ids['repository_uuid'], saved['data']['team'],
                                proposal['owner'])
        except Exception as error:  # noqa: BLE001 - a step that cannot be taken is named, and tried again
            return dict(about, outcome='refused', step='repository', refusal=getattr(error, 'code', None)
                        or 'unknown_outcome:' + type(error).__name__)
        projects = organ('control_project').Projects(S, CM, s.conn, ids, s.principal, s.sign,
                                                     stop=lambda dispatch, reason: False,
                                                     authority_generation=s.generation)
        teams = CT.Teams(S, CM, s.conn, ids, s.principal, s.sign, inbox=ingress.inbox, assignment=m['I'],
                         requester='pm', request_sign=self.pm_sign, authority_generation=s.generation)
        names = [json.loads(r[0])['name'] for r in s.conn.execute("SELECT data FROM entities WHERE kind='project'")]
        intake = organ('control_intake').Intake(S, CM, m['AC'], ingress.acquirer, s.conn, domain=s.domain,
                                                projects=sorted(set(names) | {proposal['project']}),
                                                api_edge=ingress.settlement.api_edge, journal_signer=s.principal,
                                                sign=s.sign, asker=ingress.presenter.edge,
                                                authority_generation=s.generation)
        coordinates = dict(ids, repository_uuid=repository)
        objectives = organ('control_objective').Objectives(S, CM, s.conn, coordinates, s.principal, s.sign,
                                                           authority_generation=s.generation)
        result = PP.activate(self.decisions, record['id'], projects=projects, teams=teams, intake=intake,
                             objectives=objectives, pm='pm', pm_sign=self.pm_sign, ids=coordinates)
        return dict(about, outcome='activated' if result.get('ok') else 'failed' if result.get('failed') else 'refused',
                    step=result.get('step'), refusal=result.get('reason'), project=result.get('project'), line=None)
