#!/usr/bin/env python3
"""VELDO-0161 round 7 (round 6's driver; lay_adoption_signer now takes the upgrade module its caller holds):
the adoption signer an engine upgrade lays down, driven where suite 86 cannot run.

    python3 proof/VELDO-0161/round7/drive_signer.py [<modules directory>] [<output.json>]

Suite 86_veldo_0189_engine_upgrade needs this host's systemd user manager and local sockets; this sandbox has
neither, so the suite is the host's. This driver runs the two functions the upgrade's prepare step calls
(control_factory_setup.adoption_laying, read only, and lay_adoption_signer, the writes) from the given modules
directory (default: engine/.veldo) over a scratch host shaped as setup at 8bc34e94 and 971186ac leaves it: the
owner's enrollment-signers line alone, in the host trust and in the installation's copy, and no adoption key.

It requires: the read-only judgment finds the signer due; one run lays the key (0600, its public half beside it)
and the signers in both files exactly as a fresh setup renders them (host_files with the key); a second run
writes nothing; a run SIGKILLed right after each of its write points (the points the step log records, and so
the points suite 86's kill rows kill at) is finished by the next run to the same bytes; and a signers file that
is neither the owner's line alone nor the fresh rendering, a copy that is not 0600, and a key that does not
derive are each refused by name before anything is written. Exit 0 only when every check holds.
"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
CHILD = r'''
import importlib.util, json, os, signal, sys
spec = importlib.util.spec_from_file_location('r6_setup', os.path.join(sys.argv[1], 'control_factory_setup.py'))
F = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F)
plan, installed, home, kill_at = json.loads(sys.argv[2]), json.loads(sys.argv[3]), sys.argv[4], int(sys.argv[5])
settlement = F.organ('control_factory_setup_api').derived(os.path.join(plan['keys'], F.SETTLEMENT_KEY))
laying = F.adoption_laying(plan, installed, home, settlement, F._differs)
count, points = [0], []
def observe(point):
    points.append(point)
    count[0] += 1
    if count[0] == kill_at:
        os.kill(os.getpid(), signal.SIGKILL)
laid = F.lay_adoption_signer(plan, laying, observe, F.organ('control_factory_setup_upgrade'))
print(json.dumps({'due': laying['due'], 'laid': laid, 'points': points}))
'''


def env():
    return {k: v for k, v in os.environ.items() if k not in ('SSH_AUTH_SOCK', 'SSH_AGENT_PID')}


def keygen(path, comment):
    subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', comment, '-f', str(path)], check=True,
                   capture_output=True, timeout=30, stdin=subprocess.DEVNULL, env=env())
    os.chmod(str(path), 0o600)
    return ' '.join(Path(str(path) + '.pub').read_text().split()[:2])


def derived(path):
    done = subprocess.run(['ssh-keygen', '-y', '-f', str(path)], capture_output=True, text=True, timeout=30,
                          stdin=subprocess.DEVNULL, env=env())
    return ' '.join(done.stdout.split()[:2]) if done.returncode == 0 else None


def private(path, text, mode=0o600):
    Path(path).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    Path(path).write_text(text)
    os.chmod(str(path), mode)


def main(argv):
    mods = Path(argv[0]) if argv else ROOT / 'engine' / '.veldo'
    out = Path(argv[1]) if len(argv) > 1 else None
    spec = importlib.util.spec_from_file_location('r6_setup_parent', str(mods / 'control_factory_setup.py'))
    F = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(F)
    namespace = F.organ('control_eligibility').ENROLLMENT_NAMESPACE
    checks = []

    def check(label, condition):
        checks.append([label, bool(condition)])

    scratch = Path(tempfile.mkdtemp(prefix='r6-signer-', dir=os.environ.get('TMPDIR')))
    try:
        owner_key = scratch / 'owner'
        owner_public = keygen(owner_key, 'r6-owner')

        def host(name):
            """A scratch host as an earlier setup left it: no adoption key, the owner's line alone in both files."""
            root = scratch / name
            keys, home = root / 'keys', scratch / ('install-' + name) / 'svc'
            keys.mkdir(parents=True, mode=0o700)
            (home / 'config').mkdir(parents=True, mode=0o700)
            keygen(keys / F.SETTLEMENT_KEY, 'r6-settlement')
            plan = {'root': str(root), 'keys': str(keys), 'owner': 'olga', 'owner_public': owner_public,
                    'host_trust': str(scratch / ('trust-' + name) / 'host_trust.json'), 'host_identity': 'host-r6',
                    'install_root': str(home.parent)}
            settlement = derived(keys / F.SETTLEMENT_KEY)
            signers = root / 'host' / 'enrollment_signers'
            earlier = 'olga namespaces="%s" %s\n' % (namespace, owner_public)
            check(name + ': the owner-only file this host starts with is what host_files renders with no adoption key',
                  F.host_files(plan, settlement)[str(signers)] == earlier)
            private(signers, earlier)
            private(home / 'config' / 'enrollment_signers', earlier)
            installed = {'enrollment_signers': str(home / 'config' / 'enrollment_signers')}
            return plan, installed, home, settlement, signers

        def child(plan, installed, home, kill_at):
            done = subprocess.run([sys.executable, '-B', '-c', CHILD, str(mods), json.dumps(plan), json.dumps(installed),
                                   str(home), str(kill_at)], capture_output=True, text=True, timeout=120,
                                  stdin=subprocess.DEVNULL, env=env())
            lines = done.stdout.strip().splitlines()
            return done.returncode, (json.loads(lines[-1]) if lines else {'stderr': done.stderr[-400:]})

        def state(plan, home, signers):
            key = Path(plan['keys']) / F.ADOPTION_KEY
            return {'key_mode': oct(os.lstat(key).st_mode & 0o777) if key.exists() else None,
                    'public': derived(key) if key.exists() else None,
                    'pub_file': (' '.join(Path(str(key) + '.pub').read_text().split()[:2])
                                 if Path(str(key) + '.pub').exists() else None),
                    'host': signers.read_text(), 'copy': (home / 'config' / 'enrollment_signers').read_text(),
                    'leftovers': sorted(p.name for p in Path(plan['keys']).iterdir() if p.name.endswith('.upgrade')
                                        or p.name.endswith('.upgrade.pub'))
                    + sorted(p.name for p in (signers.parent, home / 'config') for p in p.iterdir()
                             if p.name.endswith('.upgrade'))}

        def fresh_like(plan, settlement, now):
            """Exactly what a fresh setup writes for the key the host now holds: host_files with that key."""
            return (now['public'] is not None and now['key_mode'] == '0o600' and now['pub_file'] == now['public']
                    and now['host'] == F.host_files(plan, settlement, now['public'])[str(Path(plan['root']) / 'host'
                                                                                       / 'enrollment_signers')]
                    and now['copy'] == now['host']
                    and now['host'].splitlines()[-1] == '%s namespaces="%s" %s' % (F.ADOPTION_PRINCIPAL, namespace,
                                                                                   now['public'])
                    and len(now['host'].splitlines()) == 2 and not now['leftovers'])

        # One whole run, then a second.
        plan, installed, home, settlement, signers = host('whole')
        code, first = child(plan, installed, home, 0)
        points = [p.get('point') for p in first.get('points', [])]
        check('whole: the read-only judgment finds the signer due on an earlier host [%s]' % first.get('due'),
              code == 0 and first.get('due') is True)
        check('whole: one run writes the key, then the host trust\'s signers, then the installation\'s copy, each one '
              'write point [%s]' % points, points == ['adoption_key', 'adoption_signers', 'adoption_signers'])
        now = state(plan, home, signers)
        check('whole: the host holds the adoption signer exactly as a fresh setup lays it down [%s]'
              % now['host'].splitlines()[-1:], fresh_like(plan, settlement, now))
        code, second = child(plan, installed, home, 0)
        check('whole: a second run finds it laid and writes nothing [%s %s]'
              % (second.get('due'), (second.get('laid') or {}).get('outcome')),
              code == 0 and second.get('due') is False and second.get('points') == []
              and (second.get('laid') or {}).get('outcome') == 'already_done' and state(plan, home, signers) == now)

        # SIGKILLed right after each write point, then run again.
        for at, name in enumerate(points, 1):
            plan, installed, home, settlement, signers = host('kill-%d' % at)
            code, _ = child(plan, installed, home, at)
            check('killed at %d (%s): the run died by SIGKILL [%s]' % (at, name, code), code == -signal.SIGKILL)
            code, again = child(plan, installed, home, 0)
            now = state(plan, home, signers)
            check('killed at %d (%s): the next run finishes it to a fresh setup\'s bytes, writing only what was left '
                  '[%s]' % (at, name, [p.get('point') for p in again.get('points', [])]),
                  code == 0 and fresh_like(plan, settlement, now)
                  and len(again.get('points', [])) == len(points) - at)
            code, third = child(plan, installed, home, 0)
            check('killed at %d (%s): a run after that writes nothing' % (at, name),
                  code == 0 and third.get('points') == [] and state(plan, home, signers) == now)

        # The upgrade's own prepare step (upgrade_engine), the step finding 161's upgrade161-adoption-signer-not-laid
        # removes: run with the upgrade's switch and the engine pin stood in, so only setup's own code lays the signer.
        plan, installed, home, settlement, signers = host('prepare')
        logged = []

        class Upgrade:
            @staticmethod
            def point(log, entry):
                logged.append(entry.get('point'))

            # The upgrade module's own file replacement, which production's engine module (inspect_engine's) has.
            replace = staticmethod(F.organ('control_factory_setup_upgrade').replace)

            @staticmethod
            def run(engine, **kwargs):
                return dict({'step': 'engine_upgrade', 'outcome': 'done'}, **(kwargs['prepare']() or {}))

        class Engines:
            @staticmethod
            def ensure(*args):
                return {'pins_made': 0, 'engines_record': None}
        source = F.organ
        F.organ = lambda name: Engines if name == 'control_factory_setup_engines' else source(name)
        F.service_answers, F.service_request = (lambda plan: (lambda: True)), (lambda plan, packet: (lambda: True))
        try:
            laying = F.adoption_laying(plan, installed, str(home), settlement, F._differs)
            report = F.upgrade_engine(dict(plan, engines={}), {'module': Upgrade, 'bin': str(home / 'bin'),
                                                               'log': str(home / 'state.jsonl')}, None, False, laying)
        finally:
            F.organ = source
        now = state(plan, home, signers)
        check('prepare: the engine upgrade\'s prepare step lays the adoption signer as a fresh setup does, each write a '
              'point of the upgrade\'s step log [%s %s]' % ((report.get('adoption_signer') or {}).get('outcome'), logged),
              (report.get('adoption_signer') or {}).get('outcome') == 'done' and fresh_like(plan, settlement, now)
              and logged == ['adoption_key', 'adoption_signers', 'adoption_signers'])

        # Refused by name before anything is written.
        def refused(label, damage, expected):
            plan, installed, home, settlement, signers = host('refuse-' + label)
            damage(plan, home, signers)
            before = {str(p): p.read_bytes() for p in scratch.rglob('*') if p.is_file()}
            code, shown = child(plan, installed, home, 0)
            after = {str(p): p.read_bytes() for p in scratch.rglob('*') if p.is_file()}
            check('%s: refused naming %s, writing nothing [%s]' % (label, expected, shown.get('stderr', '')[-160:]),
                  code != 0 and expected in shown.get('stderr', '') and before == after)
        refused('foreign-line', lambda plan, home, signers: signers.write_text(
            signers.read_text() + 'mallory namespaces="%s" %s\n' % (namespace, owner_public)), 'enrollment_signers')
        refused('copy-mode', lambda plan, home, signers: os.chmod(str(home / 'config' / 'enrollment_signers'), 0o644),
                'config/enrollment_signers')
        refused('bad-key', lambda plan, home, signers: private(Path(plan['keys']) / F.ADOPTION_KEY, 'not a key\n'),
                F.ADOPTION_KEY)
    finally:
        shutil.rmtree(str(scratch), ignore_errors=True)
    failed = [label for label, ok in checks if not ok]
    report = {'schema': 'veldo.drive/v1', 'spec_id': 'VELDO-0161', 'round': 7, 'modules': str(mods),
              'checks': checks, 'passed': len(checks) - len(failed), 'failed': len(failed)}
    text = json.dumps(report, indent=1) + '\n'
    if out:
        out.write_text(text)
    print(text, end='')
    return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
