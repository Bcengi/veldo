"""VELDO-0113 lead decision 2: real CLI IPC refusal and authority authentication.

Pipe readiness and child completion synchronize the fixture; deadlines only detect
hangs. The authority owns its real SQLite connection. A recording loop measures
only the accepted wake, not execution or completion of a build.
"""


def _v113_work_suite():
    import contextlib
    import importlib.machinery
    import importlib.util
    import io
    import json
    import os
    from pathlib import Path
    import signal
    import socket
    import subprocess
    import tempfile
    from types import SimpleNamespace
    from unittest.mock import patch

    def load(name, path):
        loader = importlib.machinery.SourceFileLoader(name, str(path))
        spec = importlib.util.spec_from_loader(name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        return module

    helper = load('work113_helper', ROOT / 'scripts/fixtures/no_autostart.py')
    with helper.hang_bounds(), tempfile.TemporaryDirectory(prefix='v113-work-') as temporary:
        base = Path(temporary)
        CS = load('work113_service', ROOT / '.veldo/control_service.py')
        E, CC, S, AC, EL = CS.E, CS.CC, CS.S, CS.AC, CS.EL
        workspace = base / 'clone'
        git = load('work113_git', ROOT / '.veldo/git_process.py')
        git.run(['git', 'init', '-q', str(workspace)], check=True, capture_output=True)
        git.run(['git', '-C', str(workspace), '-c', 'commit.gpgsign=false', 'commit',
                 '-q', '--allow-empty', '-m', 'fixture'], check=True, capture_output=True,
                identity=('Fixture', 'fixture@example.invalid'))
        keys = base / 'keys'
        keys.mkdir()
        for who in ('owner', 'outsider'):
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(keys / who)],
                           check=True, capture_output=True, timeout=1200)

        def signer(who, namespace='veldo-command'):
            def sign(data):
                return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(keys / who), '-n', namespace],
                                      input=data, check=True, capture_output=True, timeout=1200).stdout.decode()
            return sign

        public = (keys / 'owner.pub').read_text().strip()
        signers = base / 'signers'
        signers.write_text(AC.allowed_signers_line('owner', public, EL.ENROLLMENT_NAMESPACE) + '\n')
        database = base / 'authority' / 'store.sqlite3'
        database.parent.mkdir()
        binding = E.enroll(str(workspace), 'domain', 'store', str(database), 'fixture-host', 1,
                           signer('owner', EL.ENROLLMENT_NAMESPACE), 'owner', 'fixture',
                           repository_uuid='repository')
        trust = EL.HostTrust('fixture-host', str(signers))
        conn = S.open_store(str(database))
        for i, (identity, kind, data) in enumerate((
                ('owner', 'membership', dict(principal_type='person', roles=['project_owner'], scope=['repository'])),
                ('key:owner', 'verification_key', dict(principal='owner', public_key=public, effective_at=0)),
                ('scoped', 'membership', dict(principal_type='person', roles=['project_owner'], scope=['elsewhere'])),
                ('key:scoped', 'verification_key', dict(principal='scoped', public_key=public, effective_at=0)),
                ('member', 'membership', dict(principal_type='person', roles=[], scope=['repository'])),
                ('key:member', 'verification_key', dict(principal='member', public_key=public, effective_at=0)))):
            S.execute(conn, dict(command_id=str(i), principal='owner', operation='upsert_entity', nonce=str(i),
                artifact_digests=[], expected_versions={identity: 0},
                parameters=dict(entity_id=identity, kind=kind, data=data)), 'owner', signer('owner', 'veldo-journal'), 1)
        conn.close()
        address = CC.socket_path_for(binding)
        config = dict(domain_uuid='domain', store_uuid='store', repositories={'repository': [str(workspace)]},
                      principal='owner', authority_generation=1, enrollment_signers=str(signers),
                      observations=str(base / 'observations'), journal_key=str(keys / 'owner'))
        sources = (ROOT / 'bin/veldo', ROOT / 'engine/bin/veldo')
        for index, source in enumerate(sources):
            cli = load('work113_cli' + str(index), source)
            # Forbid the old local execution seam even if the source calls it again.
            def local_dispatch():
                raise AssertionError('client attempted local dispatch')
            cli._dispatch = local_dispatch
            request = cli._request_work
            def no_store_request(*args, **kwargs):
                with patch('sqlite3.connect', side_effect=AssertionError('client opened a store')):
                    return request(*args, **kwargs)
            cli._request_work = no_store_request
            error = io.StringIO()
            with contextlib.redirect_stderr(error):
                result = cli.cmd_work(repo_root=base / 'not-a-repository', trust=trust)
            expect('VELDO-0113 work/unenrolled/' + str(index),
                   result != 0 and 'unenrolled_workspace' in error.getvalue())
            for state in helper.STATES:
                if Path(address).exists():
                    Path(address).unlink()
                if state == 'sigkill_socket':
                    helper.make_dead_socket(address)
                before = database.read_bytes()
                error = io.StringIO()
                with contextlib.redirect_stderr(error):
                    result = cli.cmd_work(repo_root=workspace, principal='owner', sign=signer('owner'), trust=trust)
                expect('VELDO-0113 work/refuses/' + str(index) + '/' + state,
                       result != 0 and 'authority_unavailable' in error.getvalue()
                       and database.read_bytes() == before)

            # The listener is bound before fork; the child opens the only live writer.
            listener = CC.bind(address)
            listener.settimeout(1200)
            ready, started = os.pipe()
            pid = os.fork()
            if pid == 0:
                os.close(ready)
                try:
                    connection = S.open_store(str(database))
                    service = CS.Service(config, connection)
                    wakes = []
                    line = SimpleNamespace(roles={'builder': {'account': 'configured'}})
                    service.loop = SimpleNamespace(lines={'repository': line}, wake=lambda *args: wakes.append(args))
                    authority = CC.Authority('store', 'domain', str(database), E, service.verify,
                        'fixture-host', service.apply, watermark=service.watermark, context=True)
                    os.write(started, b'R')
                    os.close(started)
                    for _ in range(8):
                        CC.serve_one(listener, authority, timeout=1200)
                    service.loop = None
                    CC.serve_one(listener, authority, timeout=1200)
                    (base / 'wakes.json').write_text(json.dumps(wakes))
                    connection.close()
                    os._exit(0)
                except BaseException:
                    import traceback
                    traceback.print_exc()
                    os._exit(1)
            os.close(started)
            listener.close()
            try:
                assert os.read(ready, 1) == b'R'
                result = cli._request_work(str(workspace), 'configured', 'owner', signer('owner'), trust)
                expect('VELDO-0113 work/authority-queues/' + str(index),
                       result == dict(ok=True, state='queued', repository_uuid='repository'))
                for account, who, principal, reason in (
                        ('other', 'owner', 'owner', 'unsupported_configuration:work_account'),
                        (None, 'outsider', 'owner', 'command_signature_invalid'),
                        (None, 'owner', 'outsider', 'unauthorized:work'),
                        (None, 'owner', 'scoped', 'unauthorized:work'),
                        (None, 'owner', 'member', 'unauthorized:work'),
                        ([], 'owner', 'owner', 'invalid_input:parameters')):
                    try:
                        cli._request_work(str(workspace), account, principal, signer(who), trust)
                    except cli._work().CL.ClaimStopped as error:
                        found = error.reason
                    else:
                        found = None
                    expect('VELDO-0113 work/refuses-' + reason + '/' + principal + '/' + str(index), found == reason)
                # The outer request's valid signature cannot replace the inner command signature.
                command = dict(operation='work', domain_uuid='domain', store_uuid='store',
                               repository_uuid='repository', principal='owner', parameters={'account': None})
                answer = CC.send(str(workspace), dict(command=command, signature=signer('outsider')(
                    S.canonical_bytes(command))), E, trust.verifier('owner', str(workspace)),
                    signer('owner'), 'fixture-host', timeout=1200)
                expect('VELDO-0113 work/inner-signature/' + str(index),
                       answer['accepted'] and answer['result']['reason'] == 'unauthorized:work')
                try:
                    cli._request_work(str(workspace), None, 'owner', signer('owner'), trust)
                except cli._work().CL.ClaimStopped as error:
                    found = error.reason
                else:
                    found = None
                expect('VELDO-0113 work/unconfigured-loop/' + str(index),
                       found == 'unavailable_service:work')
                ended, status = os.waitpid(pid, 0)
                pid = None
                expect('VELDO-0113 work/only-authorized-wake/' + str(index),
                       status == 0 and len(json.loads((base / 'wakes.json').read_text())) == 1)
            finally:
                os.close(ready)
                if pid is not None:
                    os.kill(pid, signal.SIGKILL)
                    os.waitpid(pid, 0)


_v113_work_suite()
