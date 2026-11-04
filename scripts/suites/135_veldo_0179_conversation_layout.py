"""VELDO-0179 AC3: the conversation screens meet VELDO-0131's phone, desktop, accessibility and dependency rules, as
VELDO-0145 AC4 applies them.

Run: python3 scripts/selftest.py --suite 135_veldo_0179_conversation_layout

Only shared ROOT and expect are consumed. As suite 134 does: the UI source (engine/ui) is copied into scratch with the
production copies named in PRODUCTION below laid over it (the registered mutation driver substitutes each of them here),
its locked dependencies are the checkout's engine/ui/node_modules (or `npm ci --prefer-offline`), and it is built with
the package's own build script. Then:

- ac3/dependency-policy and ac3/stack: VELDO-0145's dependency policy (control_api_ui.dependency_problems, the
  checkout's .veldo) applied to the production lockfile, package.json and dependency-policy.json, as suite 120 applies
  it: every package's license allowed, nothing on the deny list, every direct package pinned and recorded with its
  origin, license and tier; the owner's stack locked and none of the rejected one.
- ac3/served-assets: the build serves the conversation screens' assets and none names a rejected library; the browser
  row ac1/api-only of suite 134 checks that every response the page used came from this origin.
- every other row: the browser tests of engine/ui/e2e/conversation-layout.spec.ts in system Chrome against
  e2e/conversation_harness.py (suite 134 describes it): ac3/screens-360, -390, -1280 and -1440 render the list and the
  conversation screen in their loading, empty, waiting, running, error and populated states (and a turn's terminal)
  with no page-wide overflow, overlapping controls or clipped, covered or (on a phone) under 44 px primary action, the
  message box's Send reachable above the phone keyboard, axe (contrast included) on the real accessibility tree at 390
  and 1280 px, and no content security policy violation; ac3/keyboard-desktop runs the owner's path by keyboard only
  with a visible focus on each control; ac3/touch-phone runs it by touch with 44 px targets and every control found by
  its name in the accessibility tree. A row is green only when its test ran and passed.

Needs node (the nvm toolchain), the npm cache or a checkout node_modules, and system Chrome; without them every row
fails by name. Writes only temporary files.
"""

def _v179_conversation_layout():
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
        'src/views/ConversationsView.vue': ROOT / "engine/ui/src/views" / "ConversationsView.vue",
        'src/views/ConversationTurnView.vue': ROOT / "engine/ui/src/views" / "ConversationTurnView.vue",
        'src/styles/conversations.css': ROOT / "engine/ui/src/styles" / "conversations.css",
        'index.html': ROOT / "engine/ui" / "index.html",
        'package-lock.json': ROOT / "engine/ui" / "package-lock.json",
    }
    # The API organs the conversation harness loads (VELDO_ORGANS): a scratch copy of the checkout's .veldo.
    ORGANS = {}
    BROWSER = ('ac3/screens-360', 'ac3/screens-390', 'ac3/screens-1280', 'ac3/screens-1440', 'ac3/keyboard-desktop',
               'ac3/touch-phone')
    ROWS = ('ac3/dependency-policy', 'ac3/stack', 'ac3/served-assets') + BROWSER
    BUILT = ('ac3/served-assets',) + BROWSER
    STACK = ('vue', 'vue-router', 'pinia', 'vite', 'typescript', 'tailwindcss', 'monaco-editor', '@tanstack/vue-table',
             'chart.js', '@nuxt/ui')
    REJECTED = ('react', 'react-dom', 'recharts', 'shadcn', 'shadcn-vue', '@shadcn/*', 'primevue', '@primevue/*',
                '@vue-flow/*', 'vue-chartjs', 'echarts')
    BUILD = ('@axe-core/playwright', '@playwright/test', '@tailwindcss/vite', '@types/node', '@vitejs/plugin-vue',
             '@vue/test-utils', 'jsdom', 'vitest', 'vue-tsc', '@fontsource-variable/ibm-plex-sans',
             '@fontsource/ibm-plex-mono', '@iconify-json/lucide')
    rows = {name: [] for name in ROWS}
    started = time.monotonic()
    UI = ROOT / 'engine' / 'ui'
    SKIP = {'node_modules', 'dist', 'test-results', 'playwright-report'}
    SPEC = 'e2e/conversation-layout.spec.ts'

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

    def policy_rows():
        try:
            lock = json.loads(Path(PRODUCTION['package-lock.json']).read_text())
            package = json.loads((UI / 'package.json').read_text())
            policy = json.loads((UI / 'dependency-policy.json').read_text())
            spec = importlib.util.spec_from_file_location('v179_ui_policy', ROOT / '.veldo' / 'control_api_ui.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            problems = module.dependency_problems(lock, policy, package)
        except Exception as error:  # noqa: BLE001
            all_rows('the dependency policy could be applied (%s: %s)' % (type(error).__name__, error),
                     ('ac3/dependency-policy', 'ac3/stack'))
            return
        check('ac3/dependency-policy', 'the lockfile, package.json and the policy agree with no problem %s'
              % problems[:4], problems == [])
        installed = {path.rsplit('node_modules/', 1)[-1] for path in (lock.get('packages') or {}) if path}
        missing = [name for name in STACK if name not in installed]
        rejected = sorted(name for name in installed if any(fnmatch.fnmatchcase(name, r) for r in REJECTED))
        direct = set(package.get('dependencies') or {}) | set(package.get('devDependencies') or {})
        foreign = sorted(direct - set(STACK) - set(BUILD))
        check('ac3/stack', 'the lockfile holds the owner\'s stack (missing %s)' % missing, not missing)
        check('ac3/stack', 'the lockfile holds no rejected library (%s)' % rejected, not rejected)
        check('ac3/stack', 'every direct dependency is the stack\'s or the build\'s own (others %s)' % foreign,
              not foreign)

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

        assets = [p for p in (dist / 'assets').rglob('*') if p.is_file() and p.suffix in ('.js', '.css')]
        found = sorted({marker for p in assets for marker in ('recharts', 'react-dom', 'shadcn', 'primevue', 'vue-flow')
                        if marker in p.read_text(errors='replace')})
        served = [p for p in assets if 'Conversation' in p.name]
        check('ac3/served-assets', 'the build has the conversation screens\' assets (%s)' % [p.name for p in served][:4],
              len(served) >= 3)
        check('ac3/served-assets', 'no built asset names a rejected library (%s)' % found, not found)

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

    policy_rows()
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


_v179_conversation_layout()
