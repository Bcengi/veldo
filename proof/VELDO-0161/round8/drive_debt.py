#!/usr/bin/env python3
"""VELDO-0161 round 8 (R6R7-1): the restart a laid adoption signer owes, driven where suite 86 cannot run.

    python3 proof/VELDO-0161/round8/drive_debt.py [<modules directory>] [<output.json>]

A host whose installed engine is already current can still lack the adoption signer (one a setup from before
round 6 upgraded). setup lays it in the engine upgrade's prepare step and, because the service reads its
enrollment signers only at its start, makes the restart due (control_factory_setup: `if adoption['due'] and
engine['state'] == 'current'`). Round 7 lost that restart when the run ended after the signers were laid and
before the restart: the next run found the files laid (`due` False) and nothing in the step log owing a restart.

This driver runs setup's own upgrade_engine and the upgrade module's own run, over the given modules directory
(default: engine/.veldo), against a scratch host shaped that way: the owner's enrollment-signers line alone in
both signers files, no adoption key, the installed engine current (state `current`, nothing to write). The
service manager is a stand-in that records what it is asked (the unit active, every restart answering), the
engine pin step and the service's socket answers are stood in. A run's restart_due is computed as setup computes
it: inspect_engine's `switched_without_restart(log)`, then setup's adoption rule. A kill is a BaseException
raised right after the Nth step-log line, so nothing after it runs, as with suite 86's SIGKILL.

Rows: a whole run lays the signer and restarts once, and leaves nothing owed; a run killed after the last
adoption_signers point leaves the restart owed, and the next run restarts the service once and leaves nothing
owed; a run whose restart fails (the manager refuses it) the same; after a whole run, a further run restarts
nothing. Exit 0 only when every check holds.
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


class Killed(BaseException):
    """The stand-in for SIGKILL: nothing after it runs."""


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


class Manager:
    """The owner's user manager, stood in: the unit active, `fail` restarts refused, every call recorded."""

    def __init__(self, fail=0):
        self.calls, self.fail = [], fail

    def run(self, args):
        self.calls.append(list(args))
        if args[0] == 'show':
            return 0, 'ActiveState=active\n', ''
        if args[0] == 'restart' and self.fail:
            self.fail -= 1
            return 1, '', 'the stand-in refuses this restart'
        return 0, '', ''

    def restarts(self):
        return sum(1 for c in self.calls if c[0] == 'restart')


def main(argv):
    mods = Path(argv[0]) if argv else ROOT / 'engine' / '.veldo'
    out = Path(argv[1]) if len(argv) > 1 else None
    spec = importlib.util.spec_from_file_location('r8_setup', str(mods / 'control_factory_setup.py'))
    F = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(F)
    namespace = F.organ('control_eligibility').ENROLLMENT_NAMESPACE
    checks = []

    def check(label, condition):
        checks.append([label, bool(condition)])

    scratch = Path(tempfile.mkdtemp(prefix='r8-debt-', dir=os.environ.get('TMPDIR')))
    token = F._SETUP_MODULES.set({})
    try:
        owner_public = keygen(scratch / 'owner', 'r8-owner')
        settlement_key = scratch / 'settlement'
        keygen(settlement_key, 'r8-settlement')

        class Engines:
            @staticmethod
            def ensure(*args):
                return {'pins_made': 0, 'engines_record': None}
        source = F.organ
        F.organ = lambda name: Engines if name == 'control_factory_setup_engines' else source(name)
        F.service_answers, F.service_request = (lambda plan: (lambda: True)), (lambda plan, packet: (lambda: True))
        UP = F.organ('control_factory_setup_upgrade')
        real_point = UP.point
        hosts = [0]

        def host():
            """A fresh scratch host: current engine, no adoption key, the owner's line alone in both signers."""
            hosts[0] += 1
            top = scratch / ('host-%d' % hosts[0])
            root, home = top / 'state', top / 'install' / 'svc'
            keys = root / 'keys'
            keys.mkdir(parents=True, mode=0o700)
            (home / 'config').mkdir(parents=True, mode=0o700)
            shutil.copy(str(settlement_key), str(keys / F.SETTLEMENT_KEY))
            plan = {'root': str(root), 'keys': str(keys), 'owner': 'olga', 'owner_public': owner_public,
                    'host_trust': str(top / 'trust' / 'host_trust.json'), 'host_identity': 'host-r8',
                    'install_root': str(home.parent), 'engines': {}}
            earlier = 'olga namespaces="%s" %s\n' % (namespace, owner_public)
            private(root / 'host' / 'enrollment_signers', earlier)
            private(home / 'config' / 'enrollment_signers', earlier)
            return {'plan': plan, 'home': home, 'log': str(home / 'state.jsonl'), 'earlier': earlier,
                    'signers': [root / 'host' / 'enrollment_signers', home / 'config' / 'enrollment_signers']}

        def run(h, manager, kill_at=0):
            """One setup run's engine upgrade over host `h`; (report or the refusal or 'killed', the run's points)."""
            plan = h['plan']
            installed = {'enrollment_signers': str(h['home'] / 'config' / 'enrollment_signers')}
            settlement = F.organ('control_factory_setup_api').derived(str(Path(plan['keys']) / F.SETTLEMENT_KEY))
            adoption = F.adoption_laying(plan, installed, str(h['home']), settlement, F._differs)
            # inspect_engine's plan for an installed engine that is already current, then setup's adoption rule.
            engine = {'state': 'current', 'home': str(h['home']), 'bin': str(h['home'] / 'bin'),
                      'stage': str(h['home'] / 'bin.previous'), 'stage_left': False, 'log': h['log'],
                      'previous_digest': 'sha256:current', 'current_digest': 'sha256:current', 'changed': [],
                      'added': [], 'removed': [], 'writes': [], 'unit': 'veldo-authority-r8.service',
                      'restart_due': UP.switched_without_restart(h['log']), 'module': UP}
            if adoption['due'] and engine['state'] == 'current':
                engine['restart_due'] = True
            held = len(Path(h['log']).read_text().splitlines()) if os.path.isfile(h['log']) else 0
            count = [0]

            def point(log, entry):
                real_point(log, entry)
                count[0] += 1
                if count[0] == kill_at:
                    raise Killed()
            UP.point = point
            try:
                outcome = F.upgrade_engine(plan, engine, manager, True, adoption)
            except Killed:
                outcome = 'killed'
            except F.Refused as error:
                outcome = 'refused:' + error.code
            finally:
                UP.point = real_point
            lines = Path(h['log']).read_text().splitlines() if os.path.isfile(h['log']) else []
            return outcome, [json.loads(line).get('point') for line in lines[held:]], adoption['due']

        def laid(h):
            texts = [p.read_text() for p in h['signers']]
            return texts[0] == texts[1] and texts[0].startswith(h['earlier']) and len(texts[0].splitlines()) == 2 \
                and texts[0].splitlines()[1].startswith(F.ADOPTION_PRINCIPAL + ' ')

        # A whole run.
        h, manager = host(), Manager()
        report, points, due = run(h, manager)
        check('a whole run over a current engine lacking the signer lays it and restarts the service once [%s %s]'
              % (points, manager.restarts()),
              due and isinstance(report, dict) and report.get('restart') == 'restarted' and manager.restarts() == 1
              and points == ['begin', 'adoption_key', 'adoption_signers', 'adoption_signers', 'restart', 'done']
              and laid(h))
        check('the whole run leaves no restart owed [%s]' % UP.recovery(h['log']), not UP.switched_without_restart(h['log']))
        again = Manager()
        report, points, due = run(h, again)
        check('a further run writes nothing and restarts nothing [%s %s %s]'
              % (report.get('outcome') if isinstance(report, dict) else report, points, again.restarts()),
              not due and isinstance(report, dict) and report.get('outcome') == 'already_done' and points == []
              and again.restarts() == 0)
        whole = ['begin', 'adoption_key', 'adoption_signers', 'adoption_signers', 'restart', 'done']
        last = max(i + 1 for i, p in enumerate(whole) if p == 'adoption_signers')

        # Killed after each point before the restart: the next run restarts once and leaves nothing owed.
        for at in range(1, whole.index('restart') + 1):
            h, manager = host(), Manager()
            outcome, points, _due = run(h, manager, kill_at=at)
            check('killed at %d (%s): the run died there, before any restart [%s %s]'
                  % (at, whole[at - 1], outcome, points),
                  outcome == 'killed' and points == whole[:at] and manager.restarts() == 0)
            if at == last:
                check('killed at %d, after the last adoption_signers: both signers files are laid and the step log owes '
                      'the restart [%s]' % (at, UP.recovery(h['log'])),
                      laid(h) and UP.switched_without_restart(h['log']))
            report, points, due = run(h, manager)
            check('killed at %d (%s): the next run restarts the service once and finishes [%s %s; %d restart(s)]'
                  % (at, whole[at - 1], report.get('restart') if isinstance(report, dict) else report, points,
                     manager.restarts()),
                  isinstance(report, dict) and report.get('restart') == 'restarted' and manager.restarts() == 1
                  and points[-2:] == ['restart', 'done'] and laid(h))
            check('killed at %d (%s): nothing is owed after the next run' % (at, whole[at - 1]),
                  not UP.switched_without_restart(h['log']))

        # A restart that fails after the signers were laid: refused, and the next run restarts.
        h, manager = host(), Manager(fail=1)
        outcome, points, _due = run(h, manager)
        check('a run whose restart fails is refused by name, the signers laid, the restart owed [%s %s %s]'
              % (outcome, points, UP.recovery(h['log'])),
              outcome == 'refused:unavailable_service:authority:upgrade_start' and 'restart' not in points
              and laid(h) and UP.switched_without_restart(h['log']))
        report, points, due = run(h, manager)
        check('after the failed restart the next run restarts the service and finishes [%s %s; %d restart call(s)]'
              % (report.get('restart') if isinstance(report, dict) else report, points, manager.restarts()),
              not due and isinstance(report, dict) and report.get('restart') == 'restarted' and manager.restarts() == 2
              and points[-2:] == ['restart', 'done'] and not UP.switched_without_restart(h['log']))
    finally:
        F._SETUP_MODULES.reset(token)
        shutil.rmtree(str(scratch), ignore_errors=True)
    failed = [label for label, ok in checks if not ok]
    result = {'schema': 'veldo.drive/v1', 'spec_id': 'VELDO-0161', 'round': 8, 'modules': str(mods),
              'checks': checks, 'passed': len(checks) - len(failed), 'failed': len(failed)}
    text = json.dumps(result, indent=1) + '\n'
    if out:
        out.write_text(text)
    print(text, end='')
    return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
