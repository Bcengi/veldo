"""The running authority service's part of a new project from chat (VELDO-0143).

WHAT IT DOES. After every packet, pass or write that advanced the journal, once the service has taken on
what was adopted (control_service.Service.take_on), the service's NewProjectPass:

  1. applies each settled answer to a presented new-project proposal (control_project_proposal
     NewProjects.apply_settled: settled, handed to the factory PM as a correction, or rejected; nothing is
     ever asked here);
  2. for each settled decision whose repository has no record yet, starts the repository provisioner, the
     registered protected effect control_effect_executor_creation (PROTECTED_EFFECTS), as its own process
     with the installation's provisioner configuration, once per decision; an installation that names none
     refuses unavailable_service:provisioner by name and the decision waits;
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
import hashlib
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


class NewProjectPass:
    """One running service's new-project work (module docstring). `modules` are the service module's globals
    (its S, CM, AC, I and SIG)."""

    def __init__(self, service, modules):
        self.service, self.m = service, modules
        self.decisions = None
        self.running, self.refused, self.mark = {}, set(), None

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
                request_sign=self.pm_sign, templates=(config or {}).get('templates'), generation=s.generation)
        return self.decisions

    def provisioner(self):
        path = self.service.config.get('provisioner')
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
        """One pass (module docstring), when the journal advanced or a provisioner ran. Returns the events."""
        decisions = self.new_projects()
        if decisions is None:
            return []
        mark = self.service.watermark()
        if mark == self.mark and not self.running:
            return []
        self.mark = mark
        made = [self._log(e) for e in decisions.apply_settled()]
        for record in decisions.settled_decisions():
            repository = (record.get('proposal') or {}).get('repository')
            held = self.m['REPO'].read(self.service.conn, repository)
            if held is None:
                event = self.provision(record)
            elif held.get('state') == 'failed':
                decisions.finish(record['id'], activated=False, reason=held.get('reason'))
                event = {'operation': 'failed', 'decision': record['id'], 'repository': repository,
                         'refusal': held.get('reason'), 'step': held.get('failed_step')}
            elif held.get('state') == 'active':
                event = self.activate(record, held)
            else:
                event = None
            if event:
                made.append(self._log(event))
        self.mark = self.service.watermark()
        return made

    def provision(self, record):
        """Start the provisioner for `record` once; read its answer when it ended with nothing recorded."""
        decision = record['id']
        about = {'operation': 'provision', 'decision': decision, 'repository': record['proposal']['repository'],
                 'effect': 'repository_provisioning'}
        running = self.running.get(decision)
        if running is not None:
            process, answer = running
            if process.poll() is None:
                return None
            del self.running[decision]
            try:
                reason = json.loads(Path(answer).read_text().strip().splitlines()[-1]).get('reason')
            except (OSError, ValueError, IndexError):
                reason = 'unknown_outcome:provisioner'
            if self.m['REPO'].read(self.service.conn, record['proposal']['repository']) is None:
                self.decisions.finish(decision, activated=False, reason=reason or 'unknown_outcome:provisioner')
                return dict(about, outcome='refused', refusal=reason)
            return dict(about, outcome='ended')
        config = self.service.config.get('provisioner')
        if not config:
            if decision in self.refused:
                return None
            self.refused.add(decision)
            return dict(about, outcome='refused', refusal='unavailable_service:provisioner')
        answer = os.path.join(os.path.dirname(self.service.config['observations']),
                              'provision-%s.json' % hashlib.sha256(decision.encode()).hexdigest()[:16])
        with open(answer, 'w') as out:
            process = subprocess.Popen([sys.executable, '-B', str(HERE / PROTECTED_EFFECTS['repository_provisioning']),
                                        str(config), decision], stdin=subprocess.DEVNULL, stdout=out,
                                       stderr=subprocess.DEVNULL, close_fds=True, start_new_session=True)
        self.running[decision] = (process, answer)
        return dict(about, outcome='started', pid=process.pid)

    def activate(self, record, held):
        """THE SAME SETTLEMENT ACTIVATES, in this process, once the repository is active."""
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
        if result.get('ok') and s.loop is not None:
            receiver = ((s.config.get('receiver') or {}).get('configs') or {}).get(repository)
            result['line'] = s.loop.add_line(repository, receiver)
        return dict(about, outcome='activated' if result.get('ok') else 'refused', step=result.get('step'),
                    refusal=result.get('reason'), project=result.get('project'))
