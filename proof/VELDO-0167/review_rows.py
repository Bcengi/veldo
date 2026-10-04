"""Review regressions through installed setup, record writers and service interfaces."""
import hashlib
import io
import json
import os
from pathlib import Path
import signal
import shutil
import socket
import tarfile
from types import SimpleNamespace


ROWS = ('older-engine-host', 'interrupted-record-write', 'hints-without-api',
        'record-hint-counts', 'upgrade-restart-answer')


def older_engine(h, check):
    row = 'older-engine-host'
    fixtures = h['ROOT'] / 'proof/VELDO-0189/older'
    name = '8bc34e94.tar.gz'
    data = (fixtures / name).read_bytes()
    manifest = json.loads((fixtures / 'digests.json').read_text())
    valid = hashlib.sha256(data).hexdigest() == manifest['files'][name]['sha256']
    check(row, 'historical engine digest matches', valid)
    if not valid:
        return
    directory = h['base'] / 'historical-engine'
    directory.mkdir()
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
        archive.extractall(directory, filter='data')
    old = h['load']('v167_old_engine', directory / '.veldo/control_factory_setup.py')
    args = host(h, 'old')
    code, laid = h['setup'](*args, module=old)
    check(row, 'historical setup succeeds', code == 0)
    if code:
        return
    config = json.loads((Path(laid['home']) / 'config/service.json').read_text())
    paths = list(config['receiver']['configs'].values())
    for path in paths:
        value = json.loads(Path(path).read_text())
        value['runs'] = str(args[0] / 'earlier-runs')
        Path(path).write_text(json.dumps(value, indent=1, sort_keys=True) + '\n')
    original = {p: json.loads(Path(p).read_text()) for p in paths}
    check(row, 'historical receiver lacks engine keys', all('state_root' not in v for v in original.values()))
    code, answer = h['setup'](*args)
    check(row, 'older engine rerun succeeds: ' + str(answer.get('reason')), code == 0)
    for path, before in original.items():
        now = json.loads(Path(path).read_text())
        check(row, 'keeps historical runs and adapters', all(now.get(k) == before.get(k) for k in ('runs', 'adapters')))
        check(row, 'engine and records keys added', now.get('state_root') == str(args[0])
              and now.get('records') == str(args[0] / 'records')
              and now.get('record_hint_service') == config['socket'])


def host(h, suffix):
    base = h['base']
    units = base / ('units-' + suffix)
    manager = h['Manager'](units)
    h['managers'].append(manager)
    return (h['fresh_root']('state-' + suffix), h['clone']('clone-' + suffix),
            base / ('trust-' + suffix) / 'host.json', base / ('install-' + suffix), units, manager)


def interrupted(h, check, args, configs):
    row = 'interrupted-record-write'
    target = configs[0]
    saved = target.read_bytes()
    value = json.loads(saved)
    value.pop('records', None)
    target.write_text(json.dumps(value, indent=1, sort_keys=True) + '\n')
    before = target.read_bytes()
    pid = os.fork()
    if pid == 0:
        replace = os.replace
        def killed(source, destination):
            if str(destination) == str(target) and '.records-' in str(source):
                os.kill(os.getpid(), signal.SIGKILL)
            return replace(source, destination)
        os.replace = killed
        try:
            h['setup'](*args)
        finally:
            os._exit(9)
    _, status = os.waitpid(pid, 0)
    check(row, 'killed after temp open and before replace', os.WIFSIGNALED(status)
          and os.WTERMSIG(status) == signal.SIGKILL)
    check(row, 'destination unchanged by killed writer', target.read_bytes() == before)
    leftovers = list(target.parent.glob(target.name + '.records-*'))
    check(row, 'kill left a private temporary file', bool(leftovers)
          and all(p.stat().st_mode & 0o777 == 0o600 for p in leftovers))
    try:
        code, answer = h['setup'](*args)
    except FileExistsError:
        code, answer = 1, {'reason': 'FileExistsError:stale-record-temporary'}
    check(row, 'later rerun succeeds: ' + str(answer.get('reason')), code == 0
          and json.loads(target.read_text()).get('records') == str(args[0] / 'records'))
    # Restore fixture for the independent record-route assertions after a red baseline.
    target.write_bytes(saved)


def hints(h, check, home, installed, receiver):
    CS = h['load']('v167_hint_service', home / 'bin/control_service.py')
    SA = CS.SA
    if not hasattr(SA, 'RecordHints'):
        for row in ('hints-without-api', 'record-hint-counts'):
            check(row, 'record hint service exists', False)
        return
    # Capture the real recorder's packet, rather than manufacturing a hint.
    path = str(h['base'] / 'hint-capture.sock')
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as capture:
        capture.bind(path)
        capture.listen(1)
        capture.settimeout(3)
        recorder = receiver.recorder
        old_service, old_hints = getattr(recorder, 'hint_service', None), recorder.hints
        recorder.hint_service, recorder.hints = path, [path]
        try:
            recorder.hint(False)
            peer, _ = capture.accept()
            with peer:
                request = json.loads(peer.recv(65536))
        finally:
            recorder.hint_service, recorder.hints = old_service, old_hints
    service = CS.Service(installed, receiver.conn)
    authority = CS.CC.Authority(installed['store_uuid'], installed['domain_uuid'], installed['store_path'], CS.E,
                               service.verify, installed['host_identity'], service.apply,
                               watermark=service.watermark, minimum_generation=installed['authority_generation'], context=True)
    judge = SA.RecordHints(authority, service)
    before = dict(service.counts)
    response = judge.judge(request, os.getuid())
    service.observe_response(response)
    check('hints-without-api', 'valid hint is accepted with no API', response.get('accepted') is True
          and response.get('sent') == 0 and response.get('dropped') == 0)
    check('hints-without-api', 'no refused request counted', service.counts == before)
    channel, refusal = CS.CH.open_channel(installed['channel_ingress'])
    check('record-hint-counts', 'installed channel opens', channel is not None)
    if channel is None:
        return
    lock = os.open(str(Path(installed['store_path']).parent / 'authority.lock'), os.O_RDWR)
    try:
        api, refusal = SA.open_api(installed['api_service'], channel, lock, home / 'state')
        check('record-hint-counts', 'installed API opens: ' + str(refusal), api is not None)
        if api is None:
            return
        service.api = api
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as live, socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as gone:
            for index, listener in enumerate((live, gone)):
                target = str(h['base'] / ('count-%d.sock' % index))
                listener.bind(target)
                listener.listen(4)
                listener.settimeout(3)
                api.subscribe(target)
            gone.close()
            response = judge.judge(request, os.getuid())
            service.observe_response(response)
            peer, _ = live.accept()
            with peer:
                observed = json.loads(peer.recv(65536))
            counts = api.status()['counts']
            check('record-hint-counts', 'record delivery and drop counted separately',
                  counts.get('record_published') == 1 and counts.get('record_dropped') == 1
                  and counts['published'] == 0 and counts['dropped'] == 0
                  and observed.get('dispatch_id') == request['dispatch_id'])
            api.publish()
            peer, _ = live.accept()
            with peer:
                peer.recv(65536)
            counts = api.status()['counts']
            check('record-hint-counts', 'journal counts stay separate', counts['published'] == 1
                  and counts['dropped'] == 0 and counts.get('record_published') == 1 and counts.get('record_dropped') == 1)
    finally:
        os.close(lock)
        channel.close()


def restart(h, check, here):
    row = 'upgrade-restart-answer'
    # The real pre-record API installer, run with the same isolated transport stand-ins.
    data = h['_git_process'].run(['git', '-C', str(here), 'archive', 'f1e1abb9', '.veldo'],
                                 capture_output=True, check=True).stdout
    directory = h['base'] / 'pre-record-engine'
    directory.mkdir()
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        archive.extractall(directory, filter='data')
    old = h['load']('v167_before_records', directory / '.veldo/control_factory_setup.py')
    shutil.copytree(h['mods'] / 'runtime', directory / '.veldo/runtime', dirs_exist_ok=True)
    isolated = SimpleNamespace(main=lambda *args, **kw: old.main(*args, **dict(
        kw, tailscale=[h['ts'].path], api_port=h['port'])))
    args = host(h, 'restart')
    code, laid = h['setup'](*args, module=isolated)
    check(row, 'pre-record setup succeeds', code == 0)
    if code:
        return
    manager = args[-1]
    h['CS'].start(laid['unit'], manager)
    before = manager.pid(laid['unit'])
    at_restart = []
    run = manager.run
    def observe(command):
        if command == ['restart', laid['unit']]:
            at_restart.append(json.loads((Path(laid['home']) / 'config/api-service.json').read_text()).get('records'))
        return run(command)
    manager.run = observe
    code, answer = h['setup'](*args)
    upgrade = next((s for s in answer.get('steps', []) if s['step'] == 'engine_upgrade'), {})
    check(row, 'running engine upgraded and restarted once: ' + str((code, answer.get('reason'), upgrade.get('restart'))), code == 0 and upgrade.get('restart') == 'restarted'
          and manager.pid(laid['unit']) != before)
    check(row, 'record configuration is ready at the single restart', at_restart == [str(args[0] / 'records')])
    check(row, 'answer requires no redundant restart: ' + str(answer.get('next')), code == 0 and not answer.get('next'))
    status = h['service_send'](args[0], {'operation': 'inspect', 'entity_ids': []})
    check(row, 'restarted service has the API open: ' + str((status.get('result') or {}).get('api')),  (status.get('result') or {}).get('api', {}).get('available') is True)
    manager.stop(laid['unit'])
