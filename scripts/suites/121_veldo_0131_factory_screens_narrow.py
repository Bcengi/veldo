"""VELDO-0131: the Veldo factory screens at the phone widths (360 and 390 px), split from suite 120 so that each
piece fits the mutation stage's floor (the four ac1/screens rows took 60 of suite 120's 99 browser seconds).

Run: python3 scripts/selftest.py --suite 121_veldo_0131_factory_screens_narrow

Only shared ROOT and expect are consumed. As suite 120 does: the UI source (engine/ui) is copied into scratch with the
production copies named in PRODUCTION below laid over it (the registered mutation driver substitutes each of them
here), its locked dependencies are the checkout's engine/ui/node_modules (or `npm ci --prefer-offline` into the
scratch copy when the checkout has none), and it is built with the package's own build script (vue-tsc, then vite).
Then the browser tests of engine/ui/e2e/factory.spec.ts whose titles begin with ac1/screens-360 or ac1/screens-390
(Playwright --grep) run in system Chrome against e2e/factory_harness.py with the API organs of ORGANS (VELDO-0163's
team harness over VELDO-0145's real factory, as suite 120 describes): every screen row at that width in its
loading, empty, error and populated states, with no page-wide overflow, no overlapping controls, the primary action
visible, unclipped and uncovered (44 px on a phone), and axe on the real accessibility tree. A row is green only
when its test ran and passed.

Needs node (the nvm toolchain), the npm cache or a checkout node_modules, and system Chrome; without them every
row fails by name. Writes only temporary files.
"""


def _v131_screens_narrow():
    import glob
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
        'src/features/backlog/completion.ts': ROOT / "engine/ui/src/features/backlog" / "completion.ts",
        'src/features/workflow/FlowProperties.vue': ROOT / "engine/ui/src/features/workflow" / "FlowProperties.vue",
        'src/features/decisions/DecisionDetail.vue': ROOT / "engine/ui/src/features/decisions" / "DecisionDetail.vue",
        'package-lock.json': ROOT / "engine/ui" / "package-lock.json",
        # Fix round 2 (review-2026-11-01): the modules of the new screens and actions.
        'src/features/repositories/repositories.ts': ROOT / "engine/ui/src/features/repositories" / "repositories.ts",
        'src/features/configuration/configuration.ts': ROOT / "engine/ui/src/features/configuration" / "configuration.ts",
        'src/features/catalog/catalog.ts': ROOT / "engine/ui/src/features/catalog" / "catalog.ts",
        'src/features/usage/usage.ts': ROOT / "engine/ui/src/features/usage" / "usage.ts",
        'src/features/workers/workers.ts': ROOT / "engine/ui/src/features/workers" / "workers.ts",
        'src/api/actions.ts': ROOT / "engine/ui/src/api" / "actions.ts",
    }
    # The API organs the factory harness loads (VELDO_ORGANS): the checkout's .veldo, with these production copies
    # laid over a scratch copy of it (the registered mutation driver substitutes each of them here).
    ORGANS = {
        'control_api_models.py': ROOT / ".veldo" / "control_api_models.py",
    }
    BROWSER = ('ac1/screens-360', 'ac1/screens-390')
    ROWS = BROWSER
    rows = {name: [] for name in ROWS}
    started = time.monotonic()
    UI = ROOT / 'engine' / 'ui'
    SKIP = {'node_modules', 'dist', 'test-results', 'playwright-report'}

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
                all_rows('the locked UI dependencies are installed (npm ci) [%s]' % tail(out))
                return
        dist = base / 'dist'
        code, out = run(['npm', 'run', 'build', '--', '--outDir', str(dist), '--emptyOutDir'], ui)
        if code != 0 or not (dist / 'index.html').is_file():
            all_rows('the UI builds with its own build script (vue-tsc, then vite) [%s]' % tail(out))
            return

        e2e = base / 'e2e.json'
        # Only this suite's rows: the title of each test begins with its row name and a colon.
        code, out = run(['npx', 'playwright', 'test', 'e2e/factory.spec.ts', '--grep', 'ac1/screens-(360|390):'],
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
        with tempfile.TemporaryDirectory(prefix='v131-') as directory:
            exercise(Path(directory))
    except Exception as error:  # noqa: BLE001
        all_rows('ran to its end (raised %s: %s)' % (type(error).__name__, str(error)[:250]))
    for name, observed in rows.items():
        ok = bool(observed) and all(one for _, one in observed)
        for label, one in observed:
            if not one or os.environ.get('VELDO_0131_DETAILS'):
                print('  VELDO-0131 %s %s: %s' % (name, 'detail' if not one else 'observed', label))
        if not observed:
            print('  VELDO-0131 %s detail: no check ran' % name)
        failed = next((label for label, one in observed if not one), 'no check ran' if not observed else '')
        expect('VELDO-0131 ' + name + (': ' + failed if failed else ''), ok)
    print('VELDO-0131 suite seconds: %.3f' % (time.monotonic() - started))


_v131_screens_narrow()
