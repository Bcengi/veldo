#!/usr/bin/env python3
"""Native single change falsifiers, one per containment rule and lifecycle mechanism.

/opt/homebrew/bin/python3.12 proof/VELDO-0124/native_falsifiers.py > proof/VELDO-0124/native-falsifiers.json

Each mutant is a copy of the installed .veldo under ../runs with exactly one change,
driven through native_checks.py for claude_code. A mutant is rejected only when its
named row fails. Never run by a Linux suite.
"""
import difflib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PROFILE, WRAPPER, SUPERVISOR = ('project_runner_macos_profile.py', 'project_runner_macos_wrapper.py',
                                'project_runner_macos.py')


def rule(text):
    return '    rules.%s\n' % text


MUTANTS = (
    ('write', PROFILE, rule("""append('(deny file-write* (require-not (require-any %s (literal "/dev/null") (literal "/dev/tty"))))' % grants)"""), '', 'containment', 'write'),
    ('read-ssh', PROFILE, rule("""append(unreadable('(subpath %s)' % json.dumps(home + '/.ssh')))"""), '', 'containment', 'read'),
    ('read-claude', PROFILE, rule("""append(unreadable('(regex %s)' % _regex(home + '/.claude')))"""), '', 'containment', 'read'),
    ('read-codex', PROFILE, rule("""append(unreadable('(regex %s)' % _regex(home + '/.codex')))"""), '', 'containment', 'read'),
    ('read-accounts', PROFILE, rule('extend([unreadable(_any(accounts))] if accounts else [])'), '', 'containment', 'read'),
    ('read-projects', PROFILE, rule('extend([unreadable(_any(projects))] if projects else [])'), '', 'containment', 'read'),
    ('read-dispatches', PROFILE, rule('extend([unreadable(_any(dispatches))] if dispatches else [])'), '', 'containment', 'read'),
    ('launchctl-exec', PROFILE, rule("""append('(deny process-exec (literal "/bin/launchctl"))')"""), '', 'containment', 'launchd'),
    ('job-creation', PROFILE, rule("""append('(deny job-creation)')"""), '', 'containment', 'launchd'),
    ('keychain', PROFILE, rule("""append('(deny mach-lookup (global-name "com.apple.SecurityServer") (global-name "com.apple.securityd") (global-name "com.apple.securityd.xpc"))')"""), '', 'containment', 'keychain'),
    ('signal', PROFILE, rule("""append('(deny signal (require-not (target same-sandbox)))')"""), '', 'containment', 'signal'),
    ('wrapper-backstop', WRAPPER, '            if stage is None and now >= deadline:\n',
     '            if False:\n', 'lifecycle', 'supervisor-loss'),
    ('coalition-kill', SUPERVISOR, "            if pid != self.process['pid']:\n",
     '            if False:\n', 'lifecycle', 'descendant'),
    ('engine-group', WRAPPER, ', close_fds=True, process_group=0)', ', close_fds=True)', 'lifecycle', 'hard-kill'),
)


def main():
    if sys.platform != 'darwin':
        print(json.dumps(dict(status='not_run', reason='requires_real_macos')))
        return 2
    work = ROOT / 'runs'
    work.mkdir(exist_ok=True)
    observations = []
    for name, filename, before, after, suite, row in MUTANTS:
        source = (ROOT / '.veldo' / filename).read_text()
        assert source.count(before) == 1, name
        changed = source.replace(before, after)
        patch = ''.join(difflib.unified_diff(source.splitlines(True), changed.splitlines(True),
                                            fromfile='a/' + filename, tofile='b/' + filename))
        with tempfile.TemporaryDirectory(prefix='mutant-', dir=work) as temporary:
            target = Path(temporary)
            for path in (ROOT / '.veldo').glob('*.py'):
                shutil.copyfile(path, target / path.name)
            (target / filename).write_text(changed)
            child = subprocess.run([sys.executable, str(HERE / 'native_checks.py'), suite, 'claude_code'],
                                   env=dict(os.environ, VELDO_0124_MODULES=str(target), PYTHONDONTWRITEBYTECODE='1'),
                                   capture_output=True, text=True, timeout=600)
        result = json.loads(child.stdout)
        rows = {r['row']: r for r in result['rows']}
        named = rows['native/claude_code/' + row]
        observations.append(dict(name=name, file=filename, suite=suite, row=named['row'],
                                 rejected=named['status'] == 'failed', row_status=named['status'],
                                 error=named.get('error'), observed=named.get('observed'),
                                 other_failed=sorted(r for r, v in rows.items() if v['status'] == 'failed' and r != named['row']),
                                 patch=patch))
        print(name, 'REJECTED' if observations[-1]['rejected'] else 'SURVIVED', named['row'], file=sys.stderr)
    print(json.dumps(dict(schema='veldo.macos_native_falsifiers/v1', kind='native', mutants=observations,
                          status='passed' if all(o['rejected'] for o in observations) else 'failed'), indent=2))
    return 0 if all(o['rejected'] for o in observations) else 1


if __name__ == '__main__':
    sys.exit(main())
