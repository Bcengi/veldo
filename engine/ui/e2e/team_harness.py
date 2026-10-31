#!/usr/bin/env python3
"""The VELDO-0145 factory harness with the role and team services of VELDO-0162 (VELDO-0163).

WHAT IT ADDS to e2e/harness.py's real factory, on the same store connection and authority thread: the real
VELDO-0144 catalog writer (control_mcp_catalog.Catalog), the real VELDO-0127 configuration writer
(control_agent_config.Configurations), and the real VELDO-0089 team service with VELDO-0162's routes
(control_team.Teams and control_team_routes.TeamRoutes), handed to the real control_api_authority exactly as
control_service_api.ServiceApi hands them, so the API's configuration and team routes execute the authority's
own commands. It activates two projects with the real control_project.Projects (`factory`, whose owner keeps the
default team, and `project-a`), both owned by `owner`; `owner2` is a second person member with the project
owner role scoped to project-a, so a team that person saves is a proposal that waits for owner's answer. It
enrolls the agent-run workers a team is staffed with, saves one Atlassian server and one skill through their own
writers (the catalog form is VELDO-0159's), and gives project-a a first team (four required roles, with a
specialist role `reporter`) through the owner-save path of the team route, and the same roles as the default
team's first revision through the default team route.

THE CONTROL PORT adds /team/read (the stored team record of a project, or of the default team) and
/configuration/read (a stored configuration revision), so a browser test can compare what the form sent with
what the authority stored, and /team/requests (the team amendment requests opened).

Run: python3 -B engine/ui/e2e/team_harness.py --dist engine/ui/dist
"""
import json
import os
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness as H  # noqa: E402

WORKERS = ('w-elab', 'w-build', 'w-build2', 'w-rev1', 'w-rev2')
ATLASSIAN = dict(id='atlassian', label='Atlassian', transport='http', command=None, arguments=[],
                 url='https://mcp.atlassian.example/v1/sse', environment={}, headers={}, hosts=['linux'],
                 read_only_tools=['jira_get_issue', 'jira_search', 'confluence_get_page'])


def role(configuration, workers, responsibility, permissions=('feature',), engines=('claude_code',), distinct=(),
         kind='required'):
    return dict(kind=kind, capability_configuration=dict(configuration), workers=list(workers),
                responsibilities=[responsibility, 'report'], expertise=['python'],
                proposal_permissions=list(permissions), engines=list(engines),
                budget={'capacity': 1, 'invocations': 2, 'wall_seconds': 100},
                independence={'distinct_from': list(distinct)})


def first_team(configuration):
    return {'roles': {
        'project_manager': role(configuration, ['pm'], 'coordinate', ('objective', 'feature', 'team_amendment')),
        'elaboration': role(configuration, ['w-elab'], 'elaborate'),
        'implementation': role(configuration, ['w-build', 'w-build2'], 'implement', ('finding',)),
        'independent_review': role(configuration, ['w-rev1', 'w-rev2'], 'review', ('finding',),
                                   ('claude_code', 'codex'), ('implementation',)),
        'reporter': role(configuration, ['w-elab'], 'summarize', kind='specialist')}}


class TeamFactory(H.Factory):
    def _build(self):
        super()._build()
        organs, S, CM, conn, ids = self.organs, self.S, self.CM, self.conn, self.ids
        AUTH = H.load('e2e_team_authority', organs / 'control_api_authority.py')
        PJ = H.load('e2e_team_project', organs / 'control_project.py')
        CG = AUTH.organ('control_agent_config')
        routes = AUTH.organ('control_team_routes')
        common = dict(domain=ids['domain_uuid'], repository=ids['repository_uuid'], signer='authority',
                      sign=self.journal_sign)
        self.catalog = AUTH.MC.Catalog(S, conn, **common)
        self.configurations = CG.Configurations(S, conn, **common)
        self.CG, self.CT, self.routes_module = CG, routes.CT, routes
        teams = routes.CT.Teams(S, CM, conn, ids, 'authority', self.journal_sign, inbox=self.inbox,
                                assignment=self.I, requester='pm', request_sign=lambda m: self.sign_as('pm', m))
        self.team_routes = routes.TeamRoutes(teams, self.settlement, self.presenter)
        authority = self.authority
        authority.catalog, authority.configurations, authority.team_routes = (
            self.catalog, self.configurations, self.team_routes)
        # The workers a team is staffed with: agent runs any project covers.
        for who in WORKERS:
            path = self.base / 'keys' / who
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'e2e-' + who, '-f', str(path)],
                           check=True, capture_output=True, timeout=10)
            self.keyfile[who] = path
            public = ' '.join(path.with_name(path.name + '.pub').read_text().split()[:2])
            self.admin('steward', 'enroll_principal', {'principal': who, 'principal_type': 'agent_run', 'roles': [],
                                                       'public_key': public, 'independence_group': who, 'scope': '*'},
                       enrollee=who)
        self.projects = PJ.Projects(S, CM, conn, ids, 'authority', self.journal_sign, stop=lambda d, r: False)
        for name in (PJ.FACTORY_PROJECT, 'project-a'):
            got = self.projects.apply(self.signed_command('owner', dict(
                ids, operation='activate', project=name, principal='owner', command_id=self.next_id('activate'),
                nonce=self.next_id('activate-nonce'), owner='owner', charter={'purpose': 'Factory UI fixture.'},
                execution_repository=ids['repository_uuid'],
                authority_policy={'team_amendment': ['project_owner'], 'admission': ['admission_authority']},
                coordination_budget={'capacity': 5, 'invocations': 12, 'wall_seconds': 500})))
            # The intake's neighbor fixture (proof/VELDO-0152) may have activated `factory` for owner already.
            if not got.get('ok') and not (name == PJ.FACTORY_PROJECT and got.get('reason') == 'already_exists'):
                raise RuntimeError('activate %s: %s' % (name, got.get('reason')))
        saved = self.catalog.save(dict(ATLASSIAN), principal='owner', base=0, command_id=self.next_id('catalog'))
        if saved.get('outcome') not in ('saved', None) and not saved.get('revision'):
            raise RuntimeError('catalog: %s' % saved)
        self.configurations.save(dict(skill='coding', source='factory', path='skills/coding.md'), principal='owner',
                                 base=0, command_id=self.next_id('skill'), kind=CG.KINDS[1])
        self.configurations.save(dict(role='general', engine='claude_code',
                                      native_tools=[dict(name='Read', load='always')], mcp=[], skills=[],
                                      instructions=[], settings={}),
                                 principal='owner', base=0, command_id=self.next_id('general'))
        cookie, token = self.session('owner')
        status, _h, answer = self.call('POST', '/api/v1/domains/%s/teams/save' % H.DOMAIN,
                                       dict(project='project-a', team=first_team({'role': 'general', 'revision': 1}),
                                            team_version=0), cookie, token)
        if status != 200:
            raise RuntimeError('first team: %s' % answer)
        status, _h, answer = self.call('POST', '/api/v1/domains/%s/teams/default/save' % H.DOMAIN,
                                       dict(team=first_team({'role': 'general', 'revision': 1}), base=0), cookie, token)
        if status != 200:
            raise RuntimeError('default team: %s' % answer)
        self.api.sessions.end_by_principal('owner')

    # reads for the browser tests' comparisons

    def team_record(self, project):
        if project == 'default':
            head = self.conn.execute('SELECT data FROM entities WHERE id=?', (self.routes_module.HEAD,)).fetchone()
            if head is None:
                return None
            revision = json.loads(head[0])['revision']
            row = self.conn.execute('SELECT version, data FROM entities WHERE id=?',
                                    (self.routes_module.default_id(revision),)).fetchone()
        else:
            row = self.conn.execute('SELECT version, data FROM entities WHERE id=?', ('team:' + project,)).fetchone()
        return None if row is None else dict(json.loads(row[1]), version=row[0])

    def default_revision(self, revision):
        row = self.conn.execute('SELECT data FROM entities WHERE id=?',
                                (self.routes_module.default_id(revision),)).fetchone()
        return None if row is None else json.loads(row[0])

    def configuration(self, role, revision):
        CG, ids = self.CG, self.ids
        row = self.conn.execute('SELECT data FROM entities WHERE id=?', (CG.identity(
            ids['domain_uuid'], ids['repository_uuid'], CG.KINDS[0], role, revision),)).fetchone()
        return None if row is None else json.loads(row[0])

    def team_requests(self):
        return sorted(r[0] for r in self.conn.execute("SELECT id FROM entities WHERE kind='assignment'")
                      if r[0] not in set(self.requests.values()))


def control_server(factory, stop):
    server = H.control_server(factory, stop)
    handler = server.RequestHandlerClass
    route = handler.route

    def extended(self, path, body):
        f = factory
        if path == '/team/read':
            return {'team': f.on_thread(f.team_record, body['project'])}
        if path == '/team/default':
            return {'default': f.on_thread(f.default_revision, body['revision'])}
        if path == '/configuration/read':
            return {'configuration': f.on_thread(f.configuration, body['role'], body['revision'])}
        if path == '/team/requests':
            return {'requests': f.on_thread(f.team_requests)}
        return route(self, path, body)
    handler.route = extended
    return server


def main():
    H.Factory = TeamFactory
    H.control_server = control_server
    H.main()


if __name__ == '__main__':
    os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
    main()
