"""Real setup steps, writer construction and generated SSH packets for the 0203 suite."""
import copy
import json
import os
import time


def host(h, suffix, partial=False):
    base = h['base']
    root, workspace = h['fresh_root']('state-' + suffix), h['clone']('clone-' + suffix)
    units = base / ('units-' + suffix)
    manager = h['Manager'](units)
    h['managers'].append(manager)
    args = (root, workspace, base / ('trust-' + suffix) / 'host.json', base / ('install-' + suffix), units, manager)
    step = h['F']._Step.__exit__

    class BeforeApi(BaseException):
        pass

    def pause(self, kind, value, trace):
        result = step(self, kind, value, trace)
        if kind is None and self.name == 'ingress_configuration':
            raise BeforeApi()
        return result

    try:
        if partial:
            h['F']._Step.__exit__ = pause
        code, report = h['setup'](*args)
    except BeforeApi:
        code, report = 0, {'outcome': 'paused_before_api'}
    finally:
        h['F']._Step.__exit__ = step
    return root, manager, code, report


class Writers:
    def __init__(self, h, root, owner_module, modules=None):
        self.h, self.root = h, root
        load, mods = h['load'], modules or h['mods']
        self.F = h['F']
        self.lock = self.F.take_lock(root)
        IN = load('v203_ingress', mods / 'control_channel_ingress.py')
        self.ingress = IN.open_ingress(root / 'host/ingress.json')
        self.conn = self.ingress.conn
        self.S = self.ingress.activations.S
        self.CM = load('v203_membership', mods / 'control_membership.py')
        self.CM.attach(self.S)
        self.AC = self.CM.AC
        self.config = IN.load_config(root / 'host/ingress.json')
        self.ids = self.config['authority_ids']
        self.principal, self.sign = IN.journal_signer(self.config['journal'])
        self.CG = load('v203_config', mods / 'control_agent_config.py')
        self.TR = load('v203_routes', mods / 'control_team_routes.py')
        self.CT = self.TR.CT
        self.configurations = self.CG.Configurations(self.S, self.conn, domain=self.ids['domain_uuid'],
            repository=self.ids['repository_uuid'], signer=self.principal, sign=self.sign)
        teams = self.CT.Teams(self.S, self.CM, self.conn, self.ids, self.principal, self.sign,
            inbox=self.ingress.inbox, assignment=self.ingress.settlement.I, requester='pm',
            request_sign=lambda b: h['sign_with'](root / 'keys/journal', b))
        self.routes = self.TR.TeamRoutes(teams, self.ingress.settlement, self.ingress.presenter)
        self.writer = owner_module.OwnerRevisions(self.S, self.CM, self.conn, ids=self.ids, authority_lock=self.lock,
            configurations=self.configurations, team_routes=self.routes) if owner_module is not None else None
        self.serial = 0

    def close(self):
        self.conn.close()
        if self.lock is not None:
            os.close(self.lock)

    def next_id(self):
        self.serial += 1
        return self.root.name + '-owner-' + str(self.serial)

    def packet(self, operation, parameters, who=None, key=None, command_id=None, **envelope_edits):
        command = dict(command_id=command_id or self.next_id(), operation=operation, target='authority',
                       parameters=copy.deepcopy(parameters))
        state = self.CM.authority_state(self.S, self.conn)
        envelope = dict(self.ids, schema=self.AC.ENVELOPE_SCHEMA, principal=who or self.h['owner'],
            command_id=command['command_id'], command_digest=self.AC.canonical_command_digest(command),
            nonce=command['command_id'], request_revision=1, expires_at=time.time() + 600,
            membership_version=state['membership_version'], delegation_version=state['delegation_version'])
        envelope.update(envelope_edits)
        signature = self.h['sign_with'](key or self.h['owner_key'], self.AC.canonical_envelope_bytes(envelope))
        return dict(command=command, envelope=envelope, signature=signature)

    def admin(self, operation, params, enrollee=None):
        packet = self.packet(operation, params)
        packet['command'].update(artifact_digests=[], expected_versions={})
        possession = (self.h['sign_with'](enrollee, self.AC.canonical_envelope_bytes(
            dict(packet['envelope'], principal=params['principal']))) if enrollee else None)
        return self.CM.admit(self.S, self.conn, packet['envelope'], packet['command'], packet['signature'],
            self.ids, time.time(), enrollee_signature=possession, journal_signer=(self.principal, self.sign))

    def activate(self):
        PJ = self.CT.PJ
        projects = PJ.Projects(self.S, self.CM, self.conn, self.ids, self.principal, self.sign, stop=lambda *a: None)
        command = dict(self.ids, operation='activate', project='factory', principal=self.h['owner'],
            command_id=self.next_id(), nonce=self.next_id(), owner=self.h['owner'],
            charter={'purpose': 'Owner revision fixture'}, execution_repository=self.ids['repository_uuid'],
            authority_policy={'team_amendment': ['project_owner']},
            coordination_budget={'capacity': 5, 'invocations': 20, 'wall_seconds': 500})
        return projects.apply(dict(command=command,
            signature=self.h['sign_with'](self.h['owner_key'], self.S.canonical_bytes(command))))

    def definition(self, role='implementation'):
        return dict(role=role, engine='claude_code', native_tools=[], mcp=[], skills=[], instructions=[], settings={})

    def team(self):
        roles = {}
        for role in self.CT.REQUIRED_ROLES:
            roles[role] = dict(kind='required', capability_configuration={'role': role, 'revision': 1},
                workers=['pm' if role == 'project_manager' else 'worker-' + role],
                responsibilities=[self.CT.REQUIRED_RESPONSIBILITY[role], 'report'], expertise=['python'],
                proposal_permissions=['feature'], engines=['claude_code'],
                budget={'capacity': 1, 'invocations': 2, 'wall_seconds': 100},
                independence={'distinct_from': list(self.CT.REQUIRED_SEPARATION.get(role, ()))})
        return dict(roles=roles)

    def head(self):
        return self.conn.execute('SELECT max(seq) FROM journal').fetchone()[0]
