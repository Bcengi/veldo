"""Fresh owner-run factory setup using generated inputs and inert engine assets."""
import importlib.util
import os
from pathlib import Path
import shutil
import sys
import time


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def observe_pm_authority(f, check):
    """Real setup membership must deny service operations with otherwise valid inputs."""
    R = load('v88_setup_reservations', f['mods'] / 'control_reservations.py')
    A = R.ACC
    S, conn, now = f['S'], f['conn'], time.time()
    signed = dict(signer='authority', sign=f['journal_sign'])
    common = dict(domain=f['DOMAIN'], repository=f['REPO'], authorize=R.service_authority, **signed)
    account, project, unit = 'pm-authority-account', 'proj-a', 'pm-authority-unit'
    service = R.Reservations(S, conn, principal='team-service', **common)
    for scope, subject in (('account', account), ('project', project), ('unit', unit)):
        service.configure(f['next_id']('pm-policy'), scope, subject,
                          dict(capacity=5, invocations=20, wall_seconds=1000), now=now)
    owner = A.Accounts(S, conn, principal='steward', **signed)
    owner.register(f['next_id']('pm-account'), account, 'codex', 'PM authority check',
                   {'fixture-host': str(f['base'] / 'pm-account-profile')}, now=now)
    # Positive controls prove these same operations and inputs are usable by the service.
    service.reserve_worker(f['next_id']('service-reservation'), 'service-authority-dispatch',
                           account, project, unit, now=now)
    window = dict(status='rejected', reset_at=now + 60, utilization=1,
                  source_dispatch='service-authority-dispatch', now=now)
    observer = A.Accounts(S, conn, principal='team-service', **signed)
    observer.observe(f['next_id']('service-window'), account, 'service-window', **window)
    before = observer.get(account)
    pm = R.Reservations(S, conn, principal='pm', **common)
    refused = False
    try:
        pm.reserve_worker(f['next_id']('pm-reservation'), 'pm-authority-dispatch',
                          account, project, unit, now=now)
    except (R.Refused, S.StoreRefused) as error:
        refused = error.code == 'missing_authority'
    check('followup/setup-pm-authority', 'enrolled PM cannot record a Runner reservation',
          refused and pm.worker('pm-authority-dispatch') is None)
    observer = A.Accounts(S, conn, principal='pm', **signed)
    refused = False
    try:
        observer.observe(f['next_id']('pm-window'), account, 'pm-window', **window)
    except (A.Refused, S.StoreRefused) as error:
        refused = error.code == 'missing_authority'
    check('followup/setup-pm-authority', 'enrolled PM cannot report an account limit window',
          refused and observer.get(account) == before)


def setup(root, base, mods, owner_key):
    shutil.copytree(root / '.veldo/services', mods / 'services')
    engines = load('v88_setup_engines', root / 'proof/VELDO-0186/fixtures.py').install(root, base, mods)
    tailscale = load('v88_setup_tailscale', root / 'scripts/suites/support/v171_tailscale.py')
    F = load('v88_setup', mods / 'control_factory_setup.py')
    git = load('v88_setup_git', mods / 'git_process.py')
    workspace = base / 'setup-workspace'
    git.run(['git', 'init', '-q', str(workspace)], check=True, capture_output=True)
    (workspace / 'README').write_text('Factory setup fixture.\n')
    git.run(['git', '-C', str(workspace), 'add', 'README'], check=True, capture_output=True)
    git.run(['git', '-C', str(workspace), 'commit', '-qm', 'Setup source'], check=True,
            capture_output=True, identity=('Fixture', 'fixture@example.invalid'))
    state = base / 'factory-state'
    state.mkdir(mode=0o700)
    token = base / 'setup-token'
    token.write_text('fixture' + os.urandom(12).hex() + '\n')
    token.chmod(0o600)
    profile = dict(kind='linux-systemd', slice='v88setup.slice', lock=str(base / 'setup-workers.lock'),
                   concurrency=1, runtime_seconds=600, memory_bytes=256 << 20, cpu_percent=100,
                   file_bytes=64 << 20, tasks_max=256, stop_grace_seconds=1, kill_grace_seconds=1)

    class Manager:
        def run(self, args):
            if args[0] == 'show':
                return 0, 'LoadState=not-found\nActiveState=inactive\nMainPID=0\n', ''
            if args[0] == 'start':
                raise AssertionError('setup must not start services')
            return 0, '', ''

    previous = os.environ.get('PATH', '')
    ts = tailscale.stand_in(root / 'proof/VELDO-0171/tailscale-capture.json', sys.executable)
    try:
        os.environ['PATH'] = str(engines['path']) + os.pathsep + previous
        return F.setup(str(state), 'steward', str(owner_key), str(workspace), 88001, str(token),
            host_trust=str(base / 'setup-host/host_trust.json'), install_root=str(base / 'setup-install'),
            unit_dir=str(base / 'setup-units'), profile=profile, writable=[], runner=Manager(),
            origin='http://127.0.0.1:1', tailscale=[ts.path], api_port=tailscale.free_port())
    finally:
        os.environ['PATH'] = previous
        ts.close()
