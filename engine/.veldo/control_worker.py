"""Trusted Mac worker orchestration over the signed relay client, VELDO-0125.

The engine cannot submit commands. Its trusted host supervisor owns this client
and retains the claim binding. Usage is supplied by the configured trusted output
reader, never guessed from a successful exit. Absent usage keeps charge unknown.
"""
import importlib.util
import os
import json
import subprocess
import shutil
import sys
import hashlib
import tarfile
import fcntl
import time
import plistlib
from pathlib import Path


def organ(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


C = organ('project_runner_macos_control')
CL = organ('control_worker_client')


def engine_usage(started, engine):
    reader = {'codex': 'control_engine_codex', 'claude_code': 'control_engine_claude'}.get(engine)
    output = started.directory / 'engine.out'
    if reader is None or not output.exists():
        return None
    meter = organ(reader).Meter()
    with output.open('rb') as stream:
        for line in stream:
            meter.feed(line)
    meter.close()
    return meter.final() or None


def collect_files(clone, scratch, started, engine):
    """Keep the complete generated trees outside their cleanup roots before deleting either."""
    target = Path(clone).parent / 'deliverables.tar'
    temporary = target.with_suffix('.tmp')
    with tarfile.open(temporary, 'w') as archive:
        for name, path in (('clone', clone), ('scratch', scratch), ('tmp', started.temp)):
            if path is None:
                continue
            archive.add(path, arcname=name)
        output = started.directory / 'engine.out'
        if output.exists():
            archive.add(output, arcname='engine.out')
    with temporary.open('rb') as stream:
        os.fsync(stream.fileno())
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    os.replace(temporary, target)
    # durable_json below syncs the directory containing the archive and evidence.
    return engine_usage(started, engine), {'output': target.resolve().as_uri() + '#sha256=' + digest}


def run(client, host, dispatch, clone, scratch, account, *, collect=None, claim=None):
    keys = {str(Path(p).resolve()) for p in host.profile.get('signing_keys', [])}
    if not client.signing_key or client.signing_key not in keys:
        raise C.P.Refused('missing_evidence:worker_signing_key_custody')
    claim = claim if claim is not None else client.claim(dispatch)
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
        try:
            client.launch(binding, 'running', process=started.process)
        except Exception:
            # Acceptance already owns the slot. Preserve the eventual terminal evidence
            # even when the running notification (or its acknowledgement) is lost.
            started.stop('authority_unavailable')
        observation = started.wait()
        usage, references = collect(started, observation) if collect else collect_files(clone, scratch, started, contract['capability']['adapter'])
        evidence = Path(clone).parent / 'result-evidence.json'
        client.outbox = Path(clone).parent / 'result-request.json'
        def retain():
            CL.durable_json(evidence, dict(binding=binding, observation=observation,
                                          usage=usage, references=references))
        retain()
        if observation['state'] in ('exited', 'unknown'):
            seen = started.retirement()
            if references and all(seen.get(key) is True for key in ('terminated', 'cleaned')):
                try:
                    # Output/proof references must be retained by collect before these run inputs go.
                    for path in (clone, scratch):
                        if os.path.lexists(path):
                            shutil.rmtree(path)
                    if started.temp and os.path.lexists(started.temp):
                        shutil.rmtree(started.temp)
                except (OSError, C.P.Refused):
                    pass  # The signed exit is still useful; missing cleanup keeps the durable hold.
                else:
                    observation = dict(observation, cleanup=dict(terminated=True, cleaned=True, clone_removed=True))
                    retain()
        outcome = client.result(binding, observation, usage=usage, references=references)
        return apply_release(client, host, binding, outcome)
    except Exception:
        if started.state not in ('exited', 'retired'):
            started.stop('authority_unavailable')
            started.wait()
        raise


def apply_release(client, host, binding, outcome):
    if outcome.get('host_released'):
        directory = Path(client.outbox).parent
        CL.durable_json(directory / 'retirement-request.json', dict(binding=binding, outcome=outcome))
        host.release_authority(binding['dispatch_id'], binding['contract_digest'], outcome)
        # This signed confirmation is the only operation that frees Linux capacity.
        outcome = client.retired(binding)
        CL.durable_json(directory / 'delivery-complete.json', outcome)
    return outcome


def receive(config, request):
    # A resumed outbox and an operator wake may race the original receiver.
    locks = Path(config['runs']) / '.locks'
    locks.mkdir(parents=True, exist_ok=True)
    with (locks / C.P.digest(request['dispatch_id']).split(':')[-1]).open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | (fcntl.LOCK_NB if request.get('action') == 'resume' else 0))
        except BlockingIOError:
            return None
        return receive_locked(config, request)


def receive_locked(config, request):
    """Installed Mac endpoint: resolve a dispatch through its configured Linux relay.

    Source mirror, account profiles, host qualification and keys are operator
    configuration. The request supplies only identity; execution uses the signed
    authority response. Each invocation gets an independent clone and scratch.
    """
    CL = organ('control_worker_client')
    SIG = organ('control_signer')
    M = organ('project_runner_macos')
    host = M.Supervisor(config['profile'], config['qualification'])
    key = str(Path(config['signing_key']).resolve())
    if key not in {str(Path(p).resolve()) for p in host.profile.get('signing_keys', [])}:
        raise C.P.Refused('missing_evidence:worker_signing_key_custody')
    client = CL.Client(config['workspace'], config['binding'], config['principal'],
        lambda data, namespace='veldo-command': SIG.sign_bytes(key, data, namespace),
        config['ssh_argv'], signing_key=key)
    if (request.get('domain') != config['binding']['domain_uuid']
            or request.get('repository') != config['binding']['repository_uuid']):
        raise C.P.Refused('binding_mismatch:receiver_repository')
    directory = Path(config['runs']) / C.P.digest(request['dispatch_id']).split(':')[-1]
    evidence = directory / 'result-evidence.json'
    client.outbox = directory / 'result-request.json'
    # Flush retained measurement before any release confirmation, including an
    # operator wake after a crash. A transport wake never authorizes execution.
    if evidence.exists():
        retained = json.loads(evidence.read_text())
        if retained['binding']['contract_digest'] != request.get('contract_digest'):
            raise C.P.Refused('binding_mismatch:receiver_contract')
        acknowledgement = Path(str(client.outbox) + '.ack')
        if acknowledgement.exists():
            outcome = json.loads(acknowledgement.read_text())
        elif client.outbox.exists():
            outcome = client.retry_result()
        else:
            outcome = client.result(**retained)
        if not outcome.get('host_released'):
            outcome = client.status(request['dispatch_id'])
        return apply_release(client, host, retained['binding'], outcome)
    if request.get('action') in ('release', 'resume') or directory.exists():
        outcome = client.status(request['dispatch_id'])
        directory.mkdir(parents=True, exist_ok=True)
        return apply_release(client, host, dict(dispatch_id=request['dispatch_id'],
            contract_digest=request['contract_digest'], host=outcome['binding']['host'],
            unit=outcome['binding']['unit']), outcome)
    claim = client.claim(request['dispatch_id'])
    contract = claim['contract']
    if (claim['binding']['contract_digest'] != request.get('contract_digest')
            or contract['domain'] != request['domain'] or contract['repository'] != request['repository']):
        raise C.P.Refused('binding_mismatch:receiver_contract')
    account = config['accounts'][contract['reservation']['account']]
    directory.mkdir(parents=True, exist_ok=False)
    clone, scratch = directory / 'clone', directory / 'scratch'
    scratch.mkdir()
    # The source mirror is installed configuration, never a source URL from work.
    subprocess.run(['git', 'clone', '--no-local', '--no-checkout', '--', config['source'], str(clone)],
                   check=True, capture_output=True, timeout=60)
    subprocess.run(['git', '-C', str(clone), 'checkout', '--detach', contract['source']['commit']],
                   check=True, capture_output=True, timeout=30)
    return run(client, host, request['dispatch_id'], str(clone), str(scratch), account, claim=claim)


def resume_pending(config):
    """Startup/periodic outbox drain. It never claims or starts an engine."""
    for directory in Path(config['runs']).iterdir():
        if not directory.is_dir() or (directory / 'delivery-complete.json').exists():
            continue
        for name in ('result-evidence.json', 'retirement-request.json'):
            path = directory / name
            if path.exists():
                retained = json.loads(path.read_text())
                binding = retained['binding']
                receive(config, dict(action='resume', domain=config['binding']['domain_uuid'],
                    repository=config['binding']['repository_uuid'], dispatch_id=binding['dispatch_id'],
                    contract_digest=binding['contract_digest']))
                break


def install_resumer(config_path, config):
    """Install the delivery-only launch agent before accepting work on this Mac."""
    label = 'org.veldo.result-delivery.' + C.P.digest(str(Path(config_path).resolve())).split(':')[-1][:16]
    agents = Path(config['profile']['home']) / 'Library' / 'LaunchAgents'
    agents.mkdir(parents=True, exist_ok=True)
    path = agents / (label + '.plist')
    job = dict(Label=label, ProgramArguments=[sys.executable, str(Path(__file__).resolve()),
        str(Path(config_path).resolve()), '--resume'], RunAtLoad=True, KeepAlive=True, ThrottleInterval=30)
    payload = plistlib.dumps(job)
    if not path.exists() or path.read_bytes() != payload:
        temporary = path.with_suffix('.tmp')
        with temporary.open('wb') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    domain = 'gui/' + str(os.getuid())
    if subprocess.run(['launchctl', 'print', domain + '/' + label], capture_output=True).returncode:
        subprocess.run(['launchctl', 'bootstrap', domain, str(path)], check=True, capture_output=True)


def main(config_path, resume=False):
    config = json.loads(Path(config_path).read_text())
    Path(config['runs']).mkdir(parents=True, exist_ok=True)
    if resume:
        while True:
            resume_pending(config)
            time.sleep(30)
    else:
        install_resumer(config_path, config)
        result = receive(config, json.loads(sys.stdin.readline(65536)))
        print(json.dumps(dict(state=result['record']['state'])), flush=True)


if __name__ == '__main__':
    main(sys.argv[1], '--resume' in sys.argv[2:])
