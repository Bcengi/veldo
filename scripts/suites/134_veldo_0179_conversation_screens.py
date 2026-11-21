"""VELDO-0179 AC1 and AC2: the UI's conversation screens let the owner start, continue, change the role of, attach a
project to and close conversations, every message and reply shown as written with the running turn's state, entirely
through the API; and each turn opens as a live terminal of its execution record.

Run: python3 scripts/selftest.py --suite 134_veldo_0179_conversation_screens

Only shared ROOT and expect are consumed. As suites 120 to 124 do: the UI source (engine/ui) is copied into scratch with
the production copies named in PRODUCTION below laid over it (the registered mutation driver substitutes each of them
here), its locked dependencies are the checkout's engine/ui/node_modules (or `npm ci --prefer-offline` into the scratch
copy when the checkout has none), and it is built with the package's own build script (vue-tsc, then vite). Then:

- unit/conversations: the conversation screens' Vitest specs (list order, opening words, turn markers, the role and
  project controls' lists, the client log with no text, the traces) and the route table's spec, in jsdom.
- every other row: the browser tests of engine/ui/e2e/conversations.spec.ts in system Chrome against
  e2e/conversation_harness.py: VELDO-0131's factory harness (VELDO-0163's team harness over VELDO-0145's real factory:
  a signed SQLite store, real membership, the real API authority and control_api on its loopback listener serving the
  scratch build under its content security policy, passkeys as real WebAuthn ceremonies) with the production
  VELDO-0174 conversation authority handed to the API authority and the intake, the default team's assistant roles
  saved through the real writers, a fixture project on a real one-commit repository, a fake engine that runs every
  turn through the conversation authority's own dispatch and end commands and records its lines through the real
  VELDO-0141 Recorder, and a fake Telegram edge (the loopback Bot API stand-in and the real Acquirer and intake). No
  real engine, login, Telegram or network beyond loopback. Each test's title begins with its row name; a row is green
  only when its test ran and passed.
  ac1/journey (open, two messages and both replies, a Telegram turn and its reply without a reload, role, project,
  close), ac1/as-written (a message and a reply holding markup shown as text), ac1/stale-version (a role change on an
  older version refused stale_version beside the role control, nothing written), ac1/list (open first, then closed,
  each with its opening words, role and last activity), ac1/api-only (every request a published route of this
  origin; the client log keeps route, outcome and latency, never text; metrics and traces), ac2/terminal (the running
  turn's terminal one tap from the conversation, its tool call, command output with its redaction mark and error line
  live while the turn runs, then the whole record with its line count and digest, every line matching the record).

Needs node (the nvm toolchain), the npm cache or a checkout node_modules, and system Chrome; without them every row
fails by name. Writes only temporary files.
"""

def _v179_conversation_screens():
    import fnmatch
    import glob
    import importlib.util
    import json
    import os
    import pwd
    import re
    from pathlib import Path
    import shutil
    import subprocess
    import tempfile
    import time

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'src/views/ConversationView.vue': ROOT / "engine/ui/src/views" / "ConversationView.vue",
        'src/views/ConversationTurnView.vue': ROOT / "engine/ui/src/views" / "ConversationTurnView.vue",
        'src/views/ConversationsView.vue': ROOT / "engine/ui/src/views" / "ConversationsView.vue",
        'src/features/conversations/conversations.ts': ROOT / "engine/ui/src/features/conversations" / "conversations.ts",
        'src/features/conversations/telemetry.ts': ROOT / "engine/ui/src/features/conversations" / "telemetry.ts",
        'src/api/conversations.ts': ROOT / "engine/ui/src/api" / "conversations.ts",
    }
    # The API organs the conversation harness loads (VELDO_ORGANS): a scratch copy of the checkout's .veldo.
    ORGANS = {}
    BROWSER = ('ac1/journey', 'ac1/as-written', 'ac1/stale-version', 'ac1/list', 'ac1/api-only', 'ac2/terminal')
    ROWS = ('unit/conversations',) + BROWSER
    BUILT = ROWS
    rows = {name: [] for name in ROWS}
    started = time.monotonic()
    UI = ROOT / 'engine' / 'ui'
    SKIP = {'node_modules', 'dist', 'test-results', 'playwright-report'}
    SPEC = 'e2e/conversations.spec.ts'

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def all_rows(label, names=ROWS, condition=False):
        for row in names:
            check(row, label, condition)

    def tail(text, n=12):
        lines = [line.strip() for line in (text or '').splitlines() if line.strip()]
        return ' | '.join(line.encode('ascii', 'replace').decode() for line in lines[-n:])[:900]

    def environment():
        """The caller's environment with the account's newest nvm Node first on PATH when it has one: the locked
        dependencies need a current Node, and a distribution's /usr/bin/node may be older (as suite 118 does)."""
        env = dict(os.environ)
        home = pwd.getpwuid(os.getuid()).pw_dir
        found = sorted(glob.glob(os.path.join(home, '.nvm', 'versions', 'node', 'v*', 'bin')),
                       key=lambda p: [int(x) for x in re.findall(r'\d+', os.path.basename(os.path.dirname(p)))])
        if found:
            env['PATH'] = found[-1] + os.pathsep + env.get('PATH', '')
        return env

    def run(args, cwd, env=None, timeout=900):
        try:
            done = subprocess.run(args, cwd=str(cwd), env=dict(environment(), **(env or {})), capture_output=True,
                                  text=True, timeout=timeout, stdin=subprocess.DEVNULL)
            return done.returncode, (done.stdout or '') + (done.stderr or '')
        except (OSError, subprocess.TimeoutExpired) as error:
            return -1, '%s: %s' % (type(error).__name__, error)

    def exercise(base):
        ui = base / 'engine' / 'ui'
        shutil.copytree(UI, ui, ignore=lambda d, names: [n for n in names if n in SKIP and Path(d) == UI])
        for relative, source in PRODUCTION.items():
            target = ui / relative
            if Path(source).is_file():
                target.write_bytes(Path(source).read_bytes())
            elif target.exists():
                target.unlink()
        os.symlink(ROOT / '.veldo', base / '.veldo')
        organs = base / 'organs'
        organs.mkdir()
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, organs / source.name)
        for name, source in ORGANS.items():
            shutil.copyfile(source, organs / name)
        os.symlink(ROOT / 'proof', base / 'proof')
        modules = UI / 'node_modules'
        if modules.is_dir():
            os.symlink(modules, ui / 'node_modules')
        else:
            code, out = run(['npm', 'ci', '--prefer-offline', '--no-audit', '--no-fund'], ui)
            if code != 0:
                all_rows('the locked UI dependencies are installed (npm ci) [%s]' % tail(out), BUILT)
                return
        dist = base / 'dist'
        code, out = run(['npm', 'run', 'build', '--', '--outDir', str(dist), '--emptyOutDir'], ui)
        if code != 0 or not (dist / 'index.html').is_file():
            all_rows('the UI builds with its own build script (vue-tsc, then vite) [%s]' % tail(out), BUILT)
            return

        report = base / 'vitest.json'
        code, out = run(['npx', 'vitest', 'run', 'src/features/conversations', 'src/api/routes.spec.ts',
                         '--reporter=json', '--outputFile=' + str(report)], ui, timeout=300)
        try:
            unit = json.loads(report.read_text())
        except (OSError, ValueError):
            unit = {}
        failed = [a.get('fullName') for f in unit.get('testResults') or [] for a in f.get('assertionResults') or []
                  if a.get('status') != 'passed']
        mine = [a for f in unit.get('testResults') or [] if 'features/conversations/' in (f.get('name') or '')
                for a in f.get('assertionResults') or [] if a.get('status') == 'passed']
        check('unit/conversations', 'the conversation screens\' unit specs pass [%s passed, %d of them the conversation '
              'screens\', failed %s; %s]' % (unit.get('numPassedTests'), len(mine), failed[:4],
                                             '' if code == 0 else tail(out, 6)),
              code == 0 and len(mine) > 0 and unit.get('numFailedTests', 1) == 0 and not failed)

        e2e = base / 'e2e.json'
        # The spec's tests, each title beginning with its row name and a colon.
        code, out = run(['npx', 'playwright', 'test', SPEC],
                        ui, env={'VELDO_UI_DIST': str(dist), 'VELDO_ORGANS': str(organs),
                                 'VELDO_E2E_REPORT': str(e2e)}, timeout=3000)
        try:
            browser = json.loads(e2e.read_text())
        except (OSError, ValueError):
            browser = {}
        seen = {}

        def walk(suite):
            for spec in suite.get('specs') or []:
                outcomes = [r.get('status') for t in spec.get('tests') or [] for r in t.get('results') or []]
                errors = [((r.get('error') or {}).get('message') or '') for t in spec.get('tests') or []
                          for r in t.get('results') or [] if r.get('status') != 'passed']
                seen[spec.get('title', '').split(':', 1)[0]] = (outcomes, errors)
            for child in suite.get('suites') or []:
                walk(child)
        for suite in browser.get('suites') or []:
            walk(suite)
        for row in BROWSER:
            outcomes, errors = seen.get(row, ([], []))
            check(row, 'its browser test ran and passed [%s%s]' % (
                outcomes or 'not run: ' + tail(out, 6), ('; ' + tail(errors[0], 6)) if errors else ''),
                outcomes == ['passed'])

    try:
        with tempfile.TemporaryDirectory(prefix='veldo0179-') as directory:
            exercise(Path(directory))
    except Exception as error:  # noqa: BLE001
        all_rows('ran to its end (raised %s: %s)' % (type(error).__name__, str(error)[:250]))
    for name, observed in rows.items():
        ok = bool(observed) and all(one for _, one in observed)
        for label, one in observed:
            if not one or os.environ.get('VELDO_0179_DETAILS'):
                print('  VELDO-0179 %s %s: %s' % (name, 'detail' if not one else 'observed', label))
        if not observed:
            print('  VELDO-0179 %s detail: no check ran' % name)
        failed = next((label for label, one in observed if not one), 'no check ran' if not observed else '')
        expect('VELDO-0179 ' + name + (': ' + failed if failed else ''), ok)
    print('VELDO-0179 suite seconds: %.3f' % (time.monotonic() - started))


_v179_conversation_screens()
