"""VELDO-0292: spellings of git that the Design's three forms do not read.

Usage: python3 proof/VELDO-0292/unread_spellings.py

Each command writes a git alias that pushes main to the configuration with printf, through a quoted
path, and then runs the alias through a spelling of git. For each one the script builds a scratch
repository one commit ahead of a local bare remote and records three things: the exit code of the
guard as it was at 646ff7c8, the exit code of this tree's guard, and whether bash then moves the
remote's main. The fixture has no gate stamp, so a guard that judges the command exits 2.

AC2 says such a command is refused exactly as at 646ff7c8. A line reading "base 2, tree 0, main
moved" is a command where that does not hold. The last command is a control the spec's own row
covers. Writes proof/VELDO-0292/unread-spellings.summary.json. Takes a few seconds; the only git
commands it runs outside its scratch repositories read the old guard from the base commit.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = '646ff7c8'
ENV = {k: v for k, v in os.environ.items() if not k.startswith(('GIT_', 'VELDO_', 'CLAUDE_')) and k not in ('x', 'y')}
ENV.update(GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1', GIT_AUTHOR_NAME='Fixture',
           GIT_AUTHOR_EMAIL='fixture@example.invalid', GIT_COMMITTER_NAME='Fixture',
           GIT_COMMITTER_EMAIL='fixture@example.invalid')
SECTION = "printf '[alias]\\n\\tp = !git push origin main\\n' >> '.g''it/config'; "
COMMANDS = (
    ('a command substitution that prints nothing', SECTION + "sh -c 'gi$(true)t p'"),
    ('the same in backquotes', SECTION + "sh -c 'gi\x60true\x60t p'"),
    ('an expansion with nested braces', SECTION + "sh -c 'gi${x:-${y}}t p'"),
    ('a brace expansion in a string given to bash', SECTION.replace('\\tp =', '\\tt =') + "bash -c '{gi,}t'"),
    ('a backslash before a newline inside the name', SECTION + 'gi\\\nt p'),
    ('control: a backslash inside the name, which the first form reads', SECTION + "sh -c 'g\\it p'"),
)


def git(cwd, *args):
    return subprocess.run(['git'] + list(args), cwd=str(cwd), env=ENV, capture_output=True, text=True, check=True)


def fixture(base, guard_text):
    """A clone on main, one commit ahead of its bare remote's main, carrying the guard under test."""
    bare, work = base / 'remote.git', base / 'work'
    git(base, 'init', '-q', '--bare', '-b', 'main', str(bare))
    git(base, 'init', '-q', '-b', 'main', str(work))
    (work / '.veldo').mkdir()
    (work / 'guard.sh').write_text(guard_text)
    (work / 'README').write_text('fixture\n')
    git(work, 'add', '-A')
    git(work, 'commit', '-q', '-m', 'seed')
    git(work, 'remote', 'add', 'origin', str(bare))
    git(work, 'push', '-q', 'origin', 'main')
    (work / 'app.txt').write_text('change\n')
    git(work, 'add', '-A')
    git(work, 'commit', '-q', '-m', 'change')
    return work, bare, git(work, 'rev-parse', 'HEAD').stdout.strip()


def judged(guard_text, command, run):
    """(the guard's exit code, whether bash then moved the remote's main; None when not run)."""
    with tempfile.TemporaryDirectory(prefix='v292u-') as tmp:
        work, bare, head = fixture(Path(tmp), guard_text)
        payload = json.dumps({'tool_name': 'Bash', 'tool_input': {'command': command}, 'cwd': str(work)})
        code = subprocess.run(['bash', str(work / 'guard.sh')], cwd=str(work), input=payload, capture_output=True,
                              text=True, env=dict(ENV, CLAUDE_PROJECT_DIR=str(work))).returncode
        if not run:
            return code, None
        subprocess.run(['bash', '-c', command], cwd=str(work), env=ENV, capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, timeout=120)
        return code, git(bare, 'rev-parse', 'refs/heads/main').stdout.strip() == head


def main():
    old = subprocess.run(['git', 'show', BASE + ':scripts/veldo-guard.sh'], cwd=str(ROOT), capture_output=True,
                         text=True, check=True).stdout
    new = (ROOT / 'scripts' / 'veldo-guard.sh').read_text()
    rows = []
    for name, command in COMMANDS:
        before, _ = judged(old, command, False)
        after, moved = judged(new, command, True)
        rows.append({'spelling': name, 'command': command, 'guard_at_base_exit': before, 'guard_in_tree_exit': after,
                     'bash_moves_main': moved})
        print('base %d, tree %d, main %s: %s' % (before, after, 'moved' if moved else 'not moved', name))
    passed = [r['spelling'] for r in rows if r['guard_at_base_exit'] == 2 and r['guard_in_tree_exit'] == 0
              and r['bash_moves_main']]
    deciding = {
        'rows': rows,
        'bound': 'AC2: each command is refused as at the base commit, so guard_in_tree_exit is 2 wherever '
                 'guard_at_base_exit is 2 and bash moves main',
        'refused_at_base_and_passed_in_tree': passed,
        'verdict': 'pass' if not passed else 'fail',
    }
    spec = importlib.util.spec_from_file_location('validate', ROOT / '.veldo' / 'validate.py')
    validate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validate)
    bash = subprocess.run(['bash', '--version'], capture_output=True, text=True).stdout.splitlines()[:1]
    sh = os.path.realpath('/bin/sh')
    validate.write_proof_summary(Path(__file__).with_name('unread-spellings.summary.json'),
                                 'python3 proof/VELDO-0292/unread_spellings.py', deciding, discarded=[], root=ROOT,
                                 extra={'tools': {'bash': bash[0] if bash else 'unknown', 'sh': sh}})
    return 0 if not passed else 1


if __name__ == '__main__':
    sys.exit(main())
