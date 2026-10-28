#!/usr/bin/env python3
"""VELDO-0161 round 7: suite 86's kill points over the upgrade's prepare step, driven where suite 86 cannot run.

    python3 proof/VELDO-0161/round7/drive_points.py [<modules directory>] [<output.json>]

Suite 86_veldo_0189_engine_upgrade kills a setup "right after its upgrade's Nth step-log line": its kill driver
replaces control_factory_setup.organ so that each call returning control_factory_setup_upgrade wraps that
module's `point` in one more counter, and SIGKILLs at count N. setup loads each module once per run
(_one_setup), so the counter is exact only while the upgrade module is fetched through organ once in a run (by
inspect_engine). A second fetch during the upgrade wraps `point` again and every later write point counts
twice: N is reached before the Nth line, so the kill at "restart" lands before the restart (the previous engine
still serving, which answers ownership_commit invalid_input:packet) and the kill at "removed_previous" lands
before the removal (so serve finds the previous engine beside bin and keeps the previous bindings).

This driver applies that kill-driver patch, counting instead of killing, over the given modules directory
(default: engine/.veldo) in one setup's module scope, over a scratch host shaped as setup at 8bc34e94 and
971186ac leaves it (the owner's enrollment-signers line alone, no adoption key). It fetches the upgrade module
once as inspect_engine does, then runs upgrade_engine with that module, its run standing in for the switch and
the restart: the exchange point, the real prepare step (the engine pin stood in, the adoption signer laid by
setup's own code), then the restart point. It requires that the Nth count is reached exactly when the step log
holds N lines, its last the Nth point, for every N; and that the prepare step still lays the adoption signer at
its three points. Exit 0 only when every check holds.
"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]


def env():
    return {k: v for k, v in os.environ.items() if k not in ('SSH_AUTH_SOCK', 'SSH_AGENT_PID')}


def keygen(path, comment):
    subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', comment, '-f', str(path)], check=True,
                   capture_output=True, timeout=30, stdin=subprocess.DEVNULL, env=env())
    os.chmod(str(path), 0o600)
    return ' '.join(Path(str(path) + '.pub').read_text().split()[:2])


def private(path, text):
    Path(path).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    Path(path).write_text(text)
    os.chmod(str(path), 0o600)


def main(argv):
    mods = Path(argv[0]) if argv else ROOT / 'engine' / '.veldo'
    out = Path(argv[1]) if len(argv) > 1 else None
    spec = importlib.util.spec_from_file_location('r7_setup', str(mods / 'control_factory_setup.py'))
    F = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(F)
    namespace = F.organ('control_eligibility').ENROLLMENT_NAMESPACE
    checks = []

    def check(label, condition):
        checks.append([label, bool(condition)])

    scratch = Path(tempfile.mkdtemp(prefix='r7-points-', dir=os.environ.get('TMPDIR')))
    token = F._SETUP_MODULES.set({})
    try:
        owner_public = keygen(scratch / 'owner', 'r7-owner')
        root, home = scratch / 'state', scratch / 'install' / 'svc'
        keys = root / 'keys'
        keys.mkdir(parents=True, mode=0o700)
        (home / 'config').mkdir(parents=True, mode=0o700)
        keygen(keys / F.SETTLEMENT_KEY, 'r7-settlement')
        plan = {'root': str(root), 'keys': str(keys), 'owner': 'olga', 'owner_public': owner_public,
                'host_trust': str(scratch / 'trust' / 'host_trust.json'), 'host_identity': 'host-r7',
                'install_root': str(home.parent), 'engines': {}}
        earlier = 'olga namespaces="%s" %s\n' % (namespace, owner_public)
        private(root / 'host' / 'enrollment_signers', earlier)
        private(home / 'config' / 'enrollment_signers', earlier)
        installed = {'enrollment_signers': str(home / 'config' / 'enrollment_signers')}
        settlement = F.organ('control_factory_setup_api').derived(str(keys / F.SETTLEMENT_KEY))
        laying = F.adoption_laying(plan, installed, str(home), settlement, F._differs)
        log = home / 'state.jsonl'

        class Engines:
            @staticmethod
            def ensure(*args):
                return {'pins_made': 0, 'engines_record': None}
        source = F.organ
        F.organ = lambda name: Engines if name == 'control_factory_setup_engines' else source(name)

        # Suite 86's kill driver, verbatim but for recording each count with the log it then holds.
        count, hits = [0], []
        organ = F.organ

        def patched(name):
            module = organ(name)
            if name == "control_factory_setup_upgrade":
                original = module.point

                def point(log, entry):
                    original(log, entry)
                    count[0] += 1
                    lines = [json.loads(line).get('point') for line in Path(log).read_text().splitlines()]
                    hits.append({'count': count[0], 'lines': len(lines), 'last': lines[-1:]})
                module.point = point
            return module
        F.organ = patched

        UP = F.organ('control_factory_setup_upgrade')  # inspect_engine's one fetch

        class Upgrade:
            """The engine module upgrade_engine is handed: the fetched module, its run standing in for the
            switch and the restart around the real prepare step."""
            @staticmethod
            def point(log, entry):
                return UP.point(log, entry)

            @staticmethod
            def replace(path, body, mode):
                return UP.replace(path, body, mode)

            @staticmethod
            def run(engine, **kwargs):
                UP.point(engine['log'], {'point': 'exchanged'})
                report = dict({'step': 'engine_upgrade', 'outcome': 'done'}, **(kwargs['prepare']() or {}))
                UP.point(engine['log'], {'point': 'restart', 'outcome': 'restarted'})
                return report
        F.service_answers, F.service_request = (lambda plan: (lambda: True)), (lambda plan, packet: (lambda: True))
        report = F.upgrade_engine(plan, {'module': Upgrade, 'bin': str(home / 'bin'), 'log': str(log)},
                                  None, False, laying)
        points = [json.loads(line).get('point') for line in log.read_text().splitlines()]
        check('the step log names the exchange, the adoption signer\'s three points and the restart [%s]' % points,
              points == ['exchanged', 'adoption_key', 'adoption_signers', 'adoption_signers', 'restart'])
        check('the prepare step lays the adoption signer [%s]' % (report.get('adoption_signer') or {}).get('outcome'),
              (report.get('adoption_signer') or {}).get('outcome') == 'done')
        for at, name in enumerate(points, 1):
            first = next((h for h in hits if h['count'] == at), None)
            check('suite 86\'s kill at %d (after %s) finds %d step-log lines, the last %s [%s]'
                  % (at, name, at, name, first),
                  first is not None and first['lines'] == at and first['last'] == [name])
        check('one count per step-log line [%d counts, %d lines]' % (count[0], len(points)), count[0] == len(points))
    finally:
        F._SETUP_MODULES.reset(token)
        shutil.rmtree(str(scratch), ignore_errors=True)
    failed = [label for label, ok in checks if not ok]
    result = {'schema': 'veldo.drive/v1', 'spec_id': 'VELDO-0161', 'round': 7, 'modules': str(mods),
              'checks': checks, 'passed': len(checks) - len(failed), 'failed': len(failed)}
    text = json.dumps(result, indent=1) + '\n'
    if out:
        out.write_text(text)
    print(text, end='')
    return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
