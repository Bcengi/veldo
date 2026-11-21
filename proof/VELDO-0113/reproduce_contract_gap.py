"""Diagnostic counterexample, not acceptance evidence or a substitute census.

Run from any directory. Uses VELDO-0112's unchanged registry and adapter.
The original fixture prepares valid arguments before its endpoint is stopped.
Only the argument supplier is frozen; the registered production callable runs.
"""
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]


def load(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    fixtures = load('scripts/fixtures/registered_clients.py', 'v113_registry_fixture')
    positive = load('scripts/suites/113_veldo_0112_registered_clients.py', 'v113_positive')
    runtime = fixtures.registry(ROOT)
    inventory = fixtures.cases(runtime)
    case = next(c for c in inventory if c.adapter.entrypoint == 'control_dispatch:Dispatches.prepare')
    observations = []
    for state in ('absent', 'sigkill_dead_socket'):
        with tempfile.TemporaryDirectory(prefix='v113-gap-') as temporary:
            authority = positive.AuthorityFixture(ROOT, runtime, Path(temporary))
            child = None
            try:
                args, kwargs = authority.arguments(case.adapter.entrypoint, case.transport)
                # The dependency fixture uses a 60-second contract deadline. This
                # diagnostic allows 1200 seconds and never synchronizes on elapsed time.
                args[1]['deadline'] = time.time() + 1200
                authority.stop.set()
                authority.server.join(timeout=1200)
                if authority.server.is_alive():
                    raise RuntimeError('fixture server did not stop')
                authority.socket.close()
                Path(authority.address).unlink()
                if state == 'sigkill_dead_socket':
                    child = subprocess.Popen([sys.executable, '-B', '-c',
                        'import signal,socket,sys\n'
                        's=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)\n'
                        's.bind(sys.argv[1]); s.listen(1)\n'
                        'print("bound",flush=True)\n'
                        'signal.pause()\n', authority.address], stdout=subprocess.PIPE, text=True)
                    # The pipe acknowledgement, followed by wait(), orders the
                    # endpoint's birth and death without a timing assumption.
                    if child.stdout.readline() != 'bound\n':
                        raise RuntimeError('endpoint did not acknowledge its bind')
                    child.kill()
                    child.wait(timeout=1200)
                    if child.returncode != -9 or not Path(authority.address).is_socket():
                        raise RuntimeError('SIGKILL did not leave a socket inode')
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                    connection.settimeout(1200)
                    try:
                        connection.connect(authority.address)
                    except OSError as error:
                        endpoint_errno = error.errno
                    else:
                        raise RuntimeError('endpoint still accepts connections')
                before = authority.conn.execute('SELECT MAX(seq) FROM journal').fetchone()[0]
                supplied = SimpleNamespace(arguments=lambda entry, transport: (args, kwargs))
                result = case.invoke(runtime, supplied)
                after = authority.conn.execute('SELECT MAX(seq) FROM journal').fetchone()[0]
                observations.append(dict(case=case.identity, endpoint_state=state,
                    endpoint_errno=endpoint_errno, endpoint_is_socket=Path(authority.address).is_socket(),
                    endpoint_child_status=None if child is None else child.returncode,
                    implementation_digest=case.implementation_digest,
                    registration_digest=case.registration_digest,
                    input_identity=authority.identity(), before_seq=before, after_seq=after,
                    result_state=result.get('state'), refused=False,
                    counterexample=after > before and result.get('state') == 'prepared'))
            finally:
                if child is not None:
                    if child.poll() is None:
                        child.kill()
                        child.wait(timeout=1200)
                    child.stdout.close()
                authority.close()
    sources = ('scripts/fixtures/registered_clients.py',
               'scripts/suites/113_veldo_0112_registered_clients.py',
               '.veldo/control_client_registry.py', '.veldo/control_dispatch.py')
    report = dict(kind='contract-gap-diagnostic', acceptance_complete=False,
        registry_cases=[c.identity for c in inventory],
        source_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sources},
        observations=observations)
    census = load('scripts/fixtures/lifecycle_census.py', 'v113_census')
    observed = census.census([sys.executable, '-B', '-c', 'pass'],
                            identity='VELDO-0113/dependency-qualification')
    archive = Path(__file__).with_name('census-receipt.json.gz')
    archive.write_bytes(gzip.compress(json.dumps(observed, sort_keys=True).encode(), mtime=0))
    report['dependency_census'] = dict(status=observed['status'],
        capture_status=observed['capture_status'], qualification=observed['qualification']['status'],
        gaps=observed['qualification']['gaps'], consumer_rows=observed['consumer_rows']['VELDO-0113'],
        archive='proof/VELDO-0113/census-receipt.json.gz',
        archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    print(json.dumps(report, indent=2))
    return 0 if all(o['counterexample'] for o in observations) else 1


if __name__ == '__main__':
    sys.exit(main())
