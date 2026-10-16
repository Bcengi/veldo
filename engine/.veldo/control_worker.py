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
from types import SimpleNamespace
from pathlib import Path


def organ(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


C = organ('project_runner_macos_control')
CL = organ('control_worker_client')
OUT = organ('control_worker_outbox')
sleep = time.sleep  # Worker-local seam; never patch process-wide time.


class RecorderFailure(OSError):
    """Delivery cannot continue safely without recording its next retry."""


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
    CL.durable_json(Path(clone).parent / 'run-context.json',
                    dict(binding=binding, engine=request['engine']))
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


def recorder_failure(config, request, error):
    # The diagnostic must survive even when the filesystem cannot park the entry.
    print(json.dumps(dict(operation='worker_delivery_recorder_failed',
        dispatch_id=request['dispatch_id'], reason=str(error))), file=sys.stderr, flush=True)
    try:
        OUT.park_recorder_failure(config, request['dispatch_id'])
    except Exception as park_error:
        print(json.dumps(dict(operation='worker_delivery_park_failed',
            dispatch_id=request['dispatch_id'], reason=str(park_error))), file=sys.stderr, flush=True)
    raise RecorderFailure(str(error)) from error


def receive(config, request, *, queued=False):
    lock = None
    acquired = False
    recorder_failed = False
    try:
        # Serialize queue transitions with execution-lock acquisition/completion.
        # Active entries are durable but outside launchd's watched directory.
        with OUT.locked(config) as root:
            if not queued:
                path = OUT.locate(root, request['dispatch_id'])
                if not path.exists():
                    OUT.move(root, path, '.active', CL.durable_json,
                             dict(request=request, attempts=0, due=0))
                else:
                    OUT.enqueue_locked(root, request, CL.durable_json)
            locks = root / '.locks'
            locks.mkdir(exist_ok=True)
            lock = (locks / C.P.digest(request['dispatch_id']).split(':')[-1]).open('a')
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                OUT.move(root, OUT.locate(root, request['dispatch_id']), '.active', CL.durable_json)
                return None
            acquired = True
            OUT.move(root, OUT.locate(root, request['dispatch_id']), '.active', CL.durable_json)
        result = receive_locked(config, request)
        OUT.acknowledge(config, request['dispatch_id'],
                        release=result.get('host_released') or request.get('action') == 'release')
        return result
    except Exception as error:
        try:
            OUT.failure(config, request, error, CL.durable_json)
        except Exception as recording_error:
            recorder_failed = True
            recorder_failure(config, request, recording_error)
        if not isinstance(error, OUT.WaitingForRelease):
            raise
        return None
    finally:
        try:
            if acquired and not recorder_failed:
                with OUT.locked(config) as root:
                    fcntl.flock(lock, fcntl.LOCK_UN)
                    path = root / '.active' / OUT.key(request['dispatch_id'])
                    if path.exists():
                        OUT.move(root, path, '.pending', CL.durable_json)
        except Exception as recording_error:
            recorder_failure(config, request, recording_error)
        finally:
            if lock is not None:
                lock.close()


def retain_crashed_output(host, client, request, directory):
    """Recover measurement from the trusted wrapper before acknowledging a release."""
    context = directory / 'run-context.json'
    slot_dir = host.root / host.label(request['dispatch_id'])
    output = slot_dir / 'engine.out'
    if not output.exists():
        return
    outcome = client.status(request['dispatch_id'])
    binding = outcome['binding']
    wrapper = json.loads((slot_dir / 'request.json').read_text())
    if (wrapper['dispatch_id'] != request['dispatch_id']
            or wrapper['contract_digest'] != request['contract_digest']
            or binding['contract_digest'] != request['contract_digest']):
        raise C.P.Refused('binding_mismatch:retained_output')
    if outcome['record']['state'] == 'exited' and outcome['record'].get('usage') is not None:
        return  # The acknowledged signed final measurement is already on the authority.
    engine = outcome['contract']['capability']['adapter']
    if context.exists():
        retained = json.loads(context.read_text())
        if retained['binding'] != binding or retained['engine'] != engine:
            raise C.P.Refused('binding_mismatch:retained_context')
    # The authority's signed cleanup attestation establishes that retained output
    # is final. Without it, leave the release pending rather than snapshot a live engine.
    if not outcome.get('host_released'):
        raise OUT.WaitingForRelease('release_not_yet_authorized')
    observation = dict(outcome['record'].get('observation') or {}, state='unknown')
    if outcome['record']['state'] == 'exited':
        observation = outcome['record']['observation']
    else:
        observation['cleanup'] = dict(terminated=True, cleaned=True, clone_removed=True)
    usage = engine_usage(SimpleNamespace(directory=slot_dir), engine)
    references = outcome['record'].get('references', {}) if outcome['record']['state'] == 'exited' else {
        'output': output.resolve().as_uri() + '#sha256=' + hashlib.sha256(output.read_bytes()).hexdigest()}
    CL.durable_json(directory / 'result-evidence.json', dict(binding=binding,
        observation=observation, usage=usage, references=references))


def receive_locked(config, request):
    """Installed Mac endpoint: resolve a dispatch through its configured Linux relay.

    Source mirror, account profiles, host qualification and keys are operator
    configuration. The request supplies only identity; execution uses the signed
    authority response. Each invocation gets an independent clone and scratch.
    """
    CL = organ('control_worker_client')
    SIG = organ('control_signer')
    M = organ('project_runner_macos')
    host = M.Supervisor(config['profile'], config['qualification'], migrate=False)
    key = str(Path(config['signing_key']).resolve())
    if key not in {str(Path(p).resolve()) for p in host.profile.get('signing_keys', [])}:
        raise C.P.Refused('missing_evidence:worker_signing_key_custody')
    client = CL.Client(config['workspace'], config['binding'], config['principal'],
        lambda data, namespace='veldo-command': SIG.sign_bytes(key, data, namespace),
        config['ssh_argv'], signing_key=key)
    # The durable scheduler owns retries. A failed dispatch must yield to its peers.
    client.retry_inline = False
    if (request.get('domain') != config['binding']['domain_uuid']
            or request.get('repository') != config['binding']['repository_uuid']):
        raise C.P.Refused('binding_mismatch:receiver_repository')
    directory = Path(config['runs']) / C.P.digest(request['dispatch_id']).split(':')[-1]
    evidence = directory / 'result-evidence.json'
    client.outbox = directory / 'result-request.json'
    directory_existed = directory.exists()
    directory.mkdir(parents=True, exist_ok=True)
    if not evidence.exists() and (directory_existed or request.get('action') in ('release', 'resume')):
        retain_crashed_output(host, client, request, directory)
    # Flush retained measurement before any release confirmation, including an
    # operator wake after a crash. A transport wake never authorizes execution.
    if evidence.exists():
        retained = json.loads(evidence.read_text())
        if retained['binding']['contract_digest'] != request.get('contract_digest'):
            raise C.P.Refused('binding_mismatch:receiver_contract')
        acknowledgement = Path(str(client.outbox) + '.ack')
        try:
            if acknowledgement.exists():
                outcome = json.loads(acknowledgement.read_text())
            elif client.outbox.exists():
                outcome = client.retry_result()
            else:
                outcome = client.result(**retained)
        except Exception as error:
            reason = getattr(error, 'code', str(error))
            if (request.get('action') != 'release' or isinstance(error, (OSError, TimeoutError))
                    or reason.startswith('AUTHORITY_UNAVAILABLE:')):
                raise
            # Keep the refused result and its evidence for operator repair, but
            # independently attempt the signed release already accepted by Linux.
            CL.durable_json(directory / 'result-refusal.json', dict(reason=reason))
            outcome = client.status(request['dispatch_id'])
        if not outcome.get('host_released') and request.get('action') == 'release':
            outcome = client.status(request['dispatch_id'])
            if not outcome.get('host_released'):
                raise OUT.WaitingForRelease('release_not_yet_authorized')
        return apply_release(client, host, retained['binding'], outcome)
    if request.get('action') in ('release', 'resume') or directory_existed:
        outcome = client.status(request['dispatch_id'])
        if not outcome.get('host_released'):
            raise OUT.WaitingForRelease('release_not_yet_authorized')
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
    clone, scratch = directory / 'clone', directory / 'scratch'
    scratch.mkdir()
    # The source mirror is installed configuration, never a source URL from work.
    subprocess.run(['git', 'clone', '--no-local', '--no-checkout', '--', config['source'], str(clone)],
                   check=True, capture_output=True, timeout=60)
    subprocess.run(['git', '-C', str(clone), 'checkout', '--detach', contract['source']['commit']],
                   check=True, capture_output=True, timeout=30)
    return run(client, host, request['dispatch_id'], str(clone), str(scratch), account, claim=claim)


def resume_pending(config, *, drain=False):
    """Drain only indexed events, waiting solely for specific delivery retries."""
    # Recovery logs per-entry failures and retains them outside the watched queue.
    # They must not prevent waiting for the pending entries' retry deadlines.
    OUT.recover_active(config)
    entries = OUT.entries(config, ready_only=True)
    while True:
        if not entries:
            return
        recorder_errors = []
        for entry in entries:
            if entry['due'] > time.time():
                continue
            request = dict(entry['request'])
            if request.get('action') != 'release':
                request['action'] = 'resume'
            try:
                receive(config, request, queued=True)
            except RecorderFailure as error:
                recorder_errors.append(error)
            except Exception:
                pass  # receive durably records/parks this dispatch; drain its peers.
        if recorder_errors:
            raise recorder_errors[0]
        if not drain:
            return
        entries = OUT.entries(config, ready_only=True)
        if not entries:
            return
        sleep(max(0, min(entry['due'] for entry in entries) - time.time()))


def install_resumer(config_path, config):
    """Install the delivery-only launch agent before accepting work on this Mac."""
    label = 'org.veldo.result-delivery.' + C.P.digest(str(Path(config_path).resolve())).split(':')[-1][:16]
    agents = Path(config['profile']['home']) / 'Library' / 'LaunchAgents'
    agents.mkdir(parents=True, exist_ok=True)
    path = agents / (label + '.plist')
    pending = Path(config['runs']) / '.pending'
    pending.mkdir(parents=True, exist_ok=True)
    job = dict(Label=label, ProgramArguments=[sys.executable, str(Path(__file__).resolve()),
        str(Path(config_path).resolve()), '--resume'], RunAtLoad=True,
        QueueDirectories=[str(pending.resolve())],
        StandardErrorPath=str(Path(config['runs']).resolve() / 'delivery-errors.log'))
    payload = plistlib.dumps(job)
    changed = not path.exists() or path.read_bytes() != payload
    if changed:
        temporary = path.with_suffix('.tmp')
        with temporary.open('wb') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    domain = 'gui/' + str(os.getuid())
    loaded = not subprocess.run(['launchctl', 'print', domain + '/' + label], capture_output=True).returncode
    if loaded and changed:
        subprocess.run(['launchctl', 'bootout', domain + '/' + label], check=True, capture_output=True)
    if not loaded or changed:
        subprocess.run(['launchctl', 'bootstrap', domain, str(path)], check=True, capture_output=True)


def main(config_path, resume=False, install=False):
    config = json.loads(Path(config_path).read_text())
    Path(config['runs']).mkdir(parents=True, exist_ok=True)
    if install:
        organ('project_runner_macos').Supervisor(config['profile'], config['qualification'])
        install_resumer(config_path, config)
        return
    if resume:
        organ('project_runner_macos').Supervisor(config['profile'], config['qualification'])
        resume_pending(config, drain=True)
    else:
        install_resumer(config_path, config)
        try:
            result = receive(config, json.loads(sys.stdin.readline(65536)))
        except Exception as error:
            if OUT.retryable(error):
                raise
            # receive recorded the permanent refusal for the operator. A successful
            # transport handoff must not ask Linux to resend this parked command forever.
            print(json.dumps(dict(state='parked', reason=str(error))), flush=True)
            return
        else:
            print(json.dumps(dict(state=result['record']['state'] if result else 'delivery_pending')), flush=True)
        finally:
            # Schedule local orphans on every receiver outcome. Never deliver the
            # backlog on the incoming request's network path.
            try:
                OUT.recover_active(config)
            except Exception as error:
                print(json.dumps(dict(operation='worker_recovery_failed', reason=str(error))),
                      file=sys.stderr, flush=True)


if __name__ == '__main__':
    main(sys.argv[1], '--resume' in sys.argv[2:], '--install' in sys.argv[2:])
