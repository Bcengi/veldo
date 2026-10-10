"""Trusted Mac worker orchestration over the signed relay client, VELDO-0125.

The engine cannot submit commands. Its trusted host supervisor owns this client
and retains the claim binding. Usage is supplied by the configured trusted output
reader, never guessed from a successful exit. Absent usage keeps charge unknown.
"""
import importlib.util
import os
from pathlib import Path


def organ(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


C = organ('project_runner_macos_control')


def run(client, host, dispatch, clone, scratch, account, *, collect=lambda run, result: (None, {})):
    claim = client.claim(dispatch)
    contract, binding = claim['contract'], claim['binding']
    route = contract['input']['context']['host_route']
    if (route.get('runtime_profile') != C.P.digest(host.profile)
            or binding['host'] != host.os.facts()['host'] or route['platform'] != host.os.facts()['platform']
            or account['id'] != contract['reservation']['account']
            or account['provider'] != contract['capability']['adapter']):
        raise C.P.Refused('binding_mismatch:host_account')
    login, environment = C.engine_environment(host, account, dispatch, scratch,
                                               contract['capability']['configuration'].get('environment', {}))
    request = dict(contract=contract, contract_digest=C.D.digest(contract), acceptance='preflight',
                   engine=contract['capability']['adapter'], clone=clone, scratch=scratch,
                   login_profile=login, environment=environment)
    host.preflight(request)
    receiver = C.organ('project_runner_macos_os').identity(os.getpid())
    accepted = client.launch(binding, 'accept', receiver=receiver, runtime_seconds=host.profile['runtime_seconds'])
    request['acceptance'] = accepted['record']['acceptance']
    request['environment']['VELDO_DISPATCH_ACCEPTANCE'] = request['acceptance']
    started = host.start(request)
    try:
        client.launch(binding, 'running', process=started.process)
        observation = started.wait()
        usage, references = collect(started, observation)
        return client.result(binding, observation, usage=usage, references=references)
    except Exception:
        started.stop('authority_unavailable')
        started.wait()
        raise
    # Deliberately retain the host and authority slots. Retirement additionally
    # requires clone cleanup and settled accounting through the existing contract.
