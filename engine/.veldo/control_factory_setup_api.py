"""API installation steps and the fixed-path Tailscale transport (VELDO-0171)."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys


def organ(name):
    spec = importlib.util.spec_from_file_location('setup_api_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


F = organ('control_factory_setup')
PORT = 8765
TAILSCALE_PATHS = ('/usr/bin/tailscale', '/usr/local/bin/tailscale', '/bin/tailscale', '/opt/homebrew/bin/tailscale')


class Tailscale:
    def __init__(self):
        self.binary = next((p for p in TAILSCALE_PATHS if os.path.isfile(p) and os.access(p, os.X_OK)), None)
        if self.binary is None:
            raise F.Refused('unavailable_service:tailscale')

    def run(self, args):
        try:
            done = subprocess.run([self.binary] + args, capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired):
            raise F.Refused('unavailable_service:tailscale') from None
        if done.returncode:
            raise F.Refused('unavailable_service:tailscale')
        return done.stdout + done.stderr


def transport(cli):
    try:
        status = json.loads(cli.run(['status', '--json']))
        prefs = json.loads(cli.run(['debug', 'prefs']))
        help_text = cli.run(['serve', '--help'])
        served = json.loads(cli.run(['serve', 'status', '--json']))
    except (ValueError, TypeError):
        raise F.Refused('unavailable_service:tailscale') from None
    name = (status.get('Self') or {}).get('DNSName', '').rstrip('.')
    if status.get('BackendState') != 'Running' or not name:
        raise F.Refused('unavailable_service:tailscale')
    if not prefs.get('OperatorUser'):
        raise F.Refused('unavailable_service:tailscale:operator')
    if name not in (status.get('CertDomains') or []):
        raise F.Refused('unavailable_service:tailscale:https')
    if '--bg' not in help_text.split():
        raise F.Refused('unavailable_service:tailscale:persistence')
    desired = {'TCP': {'443': {'HTTPS': True}},
               'Web': {name + ':443': {'Handlers': {'/': {'Proxy': 'http://127.0.0.1:%d' % PORT}}}}}
    if served and served != desired:
        raise F.Refused('invalid_input:tailscale_serve:occupied')
    return name, desired, bool(served)


def text(value):
    return json.dumps(value, indent=1, sort_keys=True) + '\n'


def service_config(plan, ids, name):
    return {'schema': 'veldo.api_service/v1', 'store_path': plan['store'], 'authority_ids': ids,
            'authority_generation': 1, 'journal': {'principal': F.JOURNAL_PRINCIPAL,
                                                  'key': os.path.join(plan['keys'], F.JOURNAL_KEY)},
            'api_edge': F.API_EDGE, 'domain': ids['domain_uuid'], 'projects': [ids['repository_uuid']],
            'rp_id': name, 'origin': 'https://' + name, 'workflows_repository': plan['workspace'],
            'publication_root': os.path.join(plan['root'], 'authority', 'publication')}


def files(plan, ids, name, home, unit):
    host = Path(plan['root']) / 'host'
    config = service_config(plan, ids, name)
    process = {'schema': 'veldo.api_process/v1', 'workspace': plan['workspace'], 'host_trust': plan['host_trust'],
               'signer': {'config': str(host / 'signer.json'), 'edge_key_id': organ('control_channel_enrollment').edge_key_id('api'),
                          'connection_key': str(Path(plan['root']) / 'edge' / 'api-auth')},
               'listen': {'host': '127.0.0.1', 'port': PORT},
               'api': {'origin': config['origin'], 'rp_id': name, 'host': name, 'domain': ids['domain_uuid'],
                       'edge': F.API_EDGE, 'ids': ids, 'state_dir': str(Path(plan['root']) / 'api')}}
    target = Path(home) / 'config' / 'api-process.json'
    api_unit = unit.replace('veldo-authority-', 'veldo-api-')
    template = Path(__file__).with_name('services') / 'veldo-api.service'
    unit_text = template.read_text()
    values = {'AUTHORITY': unit, 'PYTHON': os.path.realpath(sys.executable),
              'EXECUTABLE': str(Path(home) / 'bin' / 'control_client_api.py'), 'CONFIG': str(target)}
    for key, value in values.items():
        if not organ('control_service').UNIT_VALUE.fullmatch(value):
            raise F.Refused('invalid_input:unit_value:' + key.lower())
        unit_text = unit_text.replace('@' + key + '@', value)
    return {str(host / 'api-service.json'): (text(config), 0o600),
            str(Path(home) / 'config' / 'api-service.json'): (text(config), 0o600),
            str(target): (text(process), 0o600),
            str(Path(plan['unit_dir']) / api_unit): (unit_text, 0o644)}


def check_files(expected):
    for path, (data, mode) in expected.items():
        if os.path.lexists(path) and (Path(path).read_text() != data or (os.stat(path).st_mode & 0o777) != mode):
            raise F.Refused('invalid_input:state_root:differs:' + path)


def write_files(expected):
    check_files(expected)
    done = []
    for path, (data, mode) in expected.items():
        if not os.path.exists(path):
            Path(path).parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            F._private(path, data, mode)
            done.append(path)
    return done
