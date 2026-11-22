"""Tracker commands are signed requests to the installation's authority service.

The service chooses the enrolled repository and its accepted installation routing.
No caller supplies a site, credential, event file or email override.
"""
import importlib.util
import json
import os
from pathlib import Path
import time
import uuid


def organ(name):
    spec = importlib.util.spec_from_file_location('tracker_service_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def execute(service, packet, repository):
    command = packet['command']
    S, CM, AC = organ('control_store'), organ('control_membership'), organ('authority_contract')
    CP = organ('control_plane_calls')
    CP.require_service('tracker')
    now = time.time()
    state = CM.authority_state(S, service.conn)
    principal = command.get('principal')
    member = AC.membership_entry(state['membership'], principal)
    key = AC.active_key(state['keyring'], principal, now) if AC.active_member(member, now)[0] else None
    if (key is None or member.get('principal_type') != 'person'
            or 'project_owner' not in member.get('roles', ())
            or not CM.scope_covers(member.get('scope'), repository)
            or not AC.ssh_keygen_verify(S.canonical_bytes(command), packet.get('signature') or '',
                                       AC.allowed_signers_line(principal, key['public_key']), principal)[0]):
        return {'ok': False, 'reason': 'unauthorized:tracker_call'}
    coordinates = dict(domain_uuid=service.domain, store_uuid=service.store, repository_uuid=repository)
    if any(command.get(k) != v for k, v in coordinates.items()):
        return {'ok': False, 'reason': 'invalid_input:coordinates'}
    if type(command.get('expires_at')) not in (int, float) or not now < command['expires_at'] <= now + 300:
        return {'ok': False, 'reason': 'invalid_input:expired'}
    parameters = command.get('parameters')
    if (not isinstance(parameters, dict) or set(parameters) != {'action', 'tracker', 'dry_run'}
            or parameters['action'] not in ('mirror', 'init', 'snapshot')
            or type(parameters['dry_run']) is not bool
            or parameters['tracker'] is not None and not isinstance(parameters['tracker'], str)):
        return {'ok': False, 'reason': 'invalid_input:parameters'}
    config = organ('tracker').load_tracker_config()
    if not config:
        return {'ok': False, 'reason': 'installation_missing:tracker_routing'}
    workspace = service.repositories[repository][0]
    action, dry = parameters['action'], parameters['dry_run']
    runner = organ('tracker_mirror_runner')
    jira = organ('tracker_jira_init')
    try:
        if action == 'mirror':
            adapter = runner.FakeTracker() if dry else runner.build_live_adapter(config, parameters['tracker'])
            result = runner.run_from_repo(adapter, config=config, repo_root=workspace)
            summary = runner._summary(result)
        else:
            adapter = jira.FakeTracker() if dry else jira.build_live_provisioner(config, parameters['tracker'])
            if dry:
                bc = jira.resolve_bootstrap_config(config)
                if bc:
                    adapter.seed_project(bc['project_key'], bc['required_project_type'], issue_types=[])
                    adapter.seed_instance_issue_types(bc['issue_types'])
            if action == 'init':
                result = jira.bootstrap(adapter, config=config, repo_root=workspace)
                summary = jira._report_summary(result)
            else:
                result = jira.snapshot_from_repo(adapter, config=config, repo_root=workspace)
                summary = jira._snapshot_summary(result)
        return {'ok': True, 'summary': summary}
    except Exception as error:
        # A remote body is never a command result or an observation.
        return {'ok': False, 'reason': getattr(error, 'code', 'unavailable_service:tracker_call')}


def cli(action, args):
    CP = organ('control_plane_calls')
    try:
        CP.not_run('tracker')
        if not args.principal or not args.key or args.email or getattr(args, 'events_path', None):
            raise ValueError('owner identity and installation settings required')
        workspace = os.path.realpath(args.repo_root or os.getcwd())
        E, EL = organ('control_enrollment'), organ('control_eligibility')
        binding = E.read_binding(workspace)
        trust = EL.load_host_trust(args.host_trust)
        sign = organ('control_channel_activation').ssh_signer(os.path.realpath(args.key))
        command = {k: binding[k] for k in ('domain_uuid', 'store_uuid', 'repository_uuid')}
        command.update(operation='tracker_call', principal=args.principal, command_id='tracker:' + uuid.uuid4().hex,
                       expires_at=time.time() + 300,
                       parameters=dict(action=action, tracker=args.tracker, dry_run=args.dry_run))
        packet = {'command': command, 'signature': sign(organ('control_store').canonical_bytes(command))}
        response = organ('control_client').send(workspace, packet, E,
            trust.verifier(binding.get('enrolled_by'), workspace), sign, trust.host_identity, timeout=300)
        result = response.get('result') if response.get('accepted') else response
    except Exception as error:
        result = {'ok': False, 'reason': getattr(error, 'code', 'unavailable_service:tracker_command')}
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get('ok') else 2
