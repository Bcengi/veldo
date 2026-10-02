"""Credential-free pinned-binary observations for the role suites."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
BINARY = Path('/home/dmitry/.nvm/versions/node/v22.22.0/lib/node_modules/@openai/codex/node_modules/@openai/'
              'codex-linux-x64/vendor/x86_64-unknown-linux-musl/bin/codex')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def forward(args, config, diagnostic=None):
    """Only a loopback transport can execute the real binary; never a login."""
    provider = config.get('model_providers', {}).get(config.get('model_provider'), {})
    url = urlparse(provider.get('base_url', ''))
    if url.hostname != '127.0.0.1':
        return 98
    sys.path.insert(0, str(ROOT / 'proof/VELDO-0156'))
    guard = load('wire_network_guard', ROOT / 'proof/VELDO-0156/capture_mentions.py')
    done = subprocess.run([str(BINARY)] + args, input='Use no tools.', text=True,
                          stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                          preexec_fn=lambda: guard.deny_network(url.port), timeout=50)
    if diagnostic:
        Path(diagnostic).write_text(done.stderr)
    return done.returncode


def capture(configuration):
    loopback = load('wire_loopback', ROOT / 'proof/VELDO-0127/loopback.py')
    catalog = json.loads(Path(configuration['model_catalog_json']).read_text())
    result = loopback.capture(BINARY, configuration, catalog=catalog)
    return result['requests'][0]['body'] if result['requests'] else {}


def engine_source(catalog, fault):
    return '''#!PYTHON
import importlib.util, json, sys, tomllib
from pathlib import Path
args = sys.argv[1:]
if args[:2] == ['debug', 'models']:
    print(Path(CATALOG).read_text())
    sys.exit(0)
if args[:2] == ['features', 'list']:
    print(json.loads(Path(CATALOG).with_name('features-fixture.json').read_text())['stdout'], end='')
    sys.exit(0)
config = {}
def merge(a, b):
    for k, v in b.items():
        if isinstance(v, dict): merge(a.setdefault(k, {}), v)
        else: a[k] = v
for i, arg in enumerate(args):
    if arg == '-c': merge(config, tomllib.loads(args[i+1]))
servers = config.get('mcp_servers', {})
if args[:2] == ['mcp', 'list']:
    print(json.dumps([dict(name=n, enabled=True) for n in servers]))
    sys.exit(0)
if args[:2] == ['mcp', 'get']:
    name = args[2]
    print(json.dumps(dict(name=name, enabled=True, enabled_tools=servers[name]['enabled_tools'])))
    sys.exit(0)
fault = Path(FAULT).read_text() if Path(FAULT).exists() else ''
if fault == 'missing': args += ['-c', 'tools.update_plan.enabled=false']
if fault == 'extra': args += ['-c', 'features.view_image=true']
if fault == 'mcp': args += ['-c', 'mcp_servers.jira.enabled_tools=[]']
spec = importlib.util.spec_from_file_location('wire_fixture', HELPER)
wire = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wire)
Path(FAULT).with_suffix('.args.json').write_text(json.dumps(args))
sys.exit(wire.forward(args, config, Path(FAULT).with_suffix('.log')))
'''.replace('PYTHON', sys.executable).replace('CATALOG', repr(str(catalog))).replace(
        'FAULT', repr(str(fault))).replace('HELPER', repr(str(Path(__file__).resolve())))
