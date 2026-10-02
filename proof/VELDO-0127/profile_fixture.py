"""Run the receiver's exact generated profile and argv on a guarded loopback."""
import http.server
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[2]
P = '-' * 2


def capture(binary, argv, config, *, read_profile=False):
    sys.path.insert(0, str(ROOT / 'proof/VELDO-0156'))
    from capture_mentions import deny_network
    spec = importlib.util.spec_from_file_location('profile_codex', ROOT / '.veldo/control_engine_codex.py')
    X = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(X)
    requests = []

    class Endpoint(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            requests.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
            self.send_response(400)
            self.end_headers()

    with tempfile.TemporaryDirectory(prefix='v127-profile-') as temp:
        home = Path(temp)
        profile = home / 'profile'
        profile.mkdir()
        for name in ('config.toml', 'model-catalog.json'):
            shutil.copyfile(Path(config) / name, profile / name)
        exact = (profile / 'config.toml').read_bytes() == (Path(config) / 'config.toml').read_bytes()
        server = http.server.HTTPServer(('127.0.0.1', 0), Endpoint)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        provider = {'name': 'profile-proof', 'base_url': 'http://127.0.0.1:%d/v1' % server.server_port,
                    'wire_api': 'responses', 'supports_standalone_web_search': True,
                    'request_max_retries': 0, 'stream_max_retries': 0}
        args = [str(binary)] + argv[1:]
        if read_profile:
            args.remove(P + 'ignore-user-config')
        args += [P + 'skip-git-repo-check']
        for key, value in {'model_provider': 'profile_proof', 'model_providers.profile_proof': provider}.items():
            args += ['-c', key + '=' + X._toml(value)]
        env = dict(PATH='/usr/bin:/bin', HOME=temp, CODEX_HOME=str(profile), TMPDIR=temp, LANG='C.UTF-8')
        try:
            done = subprocess.run(args, input='Use no tools.', text=True, stdout=subprocess.DEVNULL,
                                  stderr=subprocess.PIPE, env=env, cwd=temp, timeout=45,
                                  preexec_fn=lambda: deny_network(server.server_port))
            return {'requests': requests, 'exact_profile': exact, 'returncode': done.returncode,
                    'stderr': done.stderr[-1200:]}
        finally:
            server.shutdown()
            thread.join()
            server.server_close()
