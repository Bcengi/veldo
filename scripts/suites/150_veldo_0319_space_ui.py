"""VELDO-0319: the console's Space screen, in a browser. The screen's states, its figures and its live reads.

Run: python3 scripts/selftest.py --suite 150_veldo_0319_space_ui

Only shared ROOT and expect are consumed. As suite 120 does: the UI source (engine/ui) is copied into scratch with
the production copies named in PRODUCTION below laid over it (the registered mutation driver substitutes each of
them here), its locked dependencies are the checkout's engine/ui/node_modules (or `npm ci --prefer-offline` into
the scratch copy when the checkout has none), and it is built with the package's own build script (vue-tsc, then
vite). The Space feature's Vitest specs run on that copy. Then the browser tests of engine/ui/e2e/space.spec.ts
run in system Chrome against e2e/space_harness.py (VELDO-0131's factory harness with the space ledger's records)
with the API organs of ORGANS laid over a scratch copy of the checkout's .veldo. A row is green only when its
test ran and passed.

unit/space             the Space feature's and the runs list's Vitest specs
ac1/usage-table-1280, ac1/usage-table-390
                       the usage figures on the screen equal the sums of the harness's item records, a deferred
                       item counted, the plain repository and "No project" rows of their own, the totals row
ac2/pending-removed    every due and deferred item with its reason in words, its retry events and its request;
                       a review group's worktrees under their one request by index; every removal with its
                       event, size and free space before and after; no raw record text on the screen
ac3/owner-commands     Reconcile and Abandon sent as signed commands through the real API edge and authority;
                       a member who is not the owner refused each beside its control, nothing written
ac3/answer-path        an open request links to the decision it is answered through
ac4/live-no-clock      with the page's clock stopped, a hold and a removal reach the screen from the record stream
                       without a reload. Falsifier (declared): poll on an interval; this row turns red
ac4/runs-list          a waiting run and a run that would have waited show need, free, held and floor on the
                       runs list, and the same numbers on the Pools section
ui/states-360, -390, -1280, -1440
                       loading, error, empty and populated, the Abandon confirmation, a refused Reconcile and
                       the runs list: no page-wide overflow, no overlapping controls, no text out of its box,
                       the primary action visible and 44 px on a phone, axe, no content security policy violation
ui/api-only            every request of the screen is a published route of this origin; a member scoped to one
                       project sees that project only

Needs node (the nvm toolchain), the npm cache or a checkout node_modules, and system Chrome; without them every
row fails by name. Writes only temporary files.
"""


def _v319_space_ui():
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
        'src/views/SpaceView.vue': ROOT / "engine/ui/src/views" / "SpaceView.vue",
        'src/features/space/space.css': ROOT / "engine/ui/src/features/space" / "space.css",
        'src/features/space/space.ts': ROOT / "engine/ui/src/features/space" / "space.ts",
        'src/features/space/SpacePending.vue': ROOT / "engine/ui/src/features/space" / "SpacePending.vue",
        'src/features/run/runs.ts': ROOT / "engine/ui/src/features/run" / "runs.ts",
        'src/api/actions.ts': ROOT / "engine/ui/src/api" / "actions.ts",
        'src/composables/useLiveRead.ts': ROOT / "engine/ui/src/composables" / "useLiveRead.ts",
    }
    # The API organs the harness loads (VELDO_ORGANS): the checkout's .veldo, with these production copies laid
    # over a scratch copy of it (the registered mutation driver substitutes each of them here).
    ORGANS = {
        'control_api_models.py': ROOT / ".veldo" / "control_api_models.py",
        'control_api_authority.py': ROOT / ".veldo" / "control_api_authority.py",
    }
    BROWSER = ('ac1/numeric-alignment-1440', 'ac1/usage-table-1280', 'ac1/usage-table-390', 'ac2/pending-removed', 'ac3/owner-commands',
               'ac3/answer-path', 'ac4/live-no-clock', 'ac4/runs-list', 'ui/states-360', 'ui/states-390',
               'ui/states-1280', 'ui/states-1440', 'ui/api-only')
    ROWS = ('unit/space',) + BROWSER
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
        """The caller's environment with the account's newest nvm Node first on PATH when it has one."""
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
        code, out = run(['npx', 'vitest', 'run', 'src/features/space', 'src/features/run/runs.spec.ts'], ui, timeout=600)
        counted = re.search(r'Tests\s+(\d+) passed \((\d+)\)', out)
        check('unit/space', 'the Space feature\'s and the runs list\'s Vitest specs pass [%s]' % tail(out, 4),
              code == 0 and counted is not None and counted.group(1) == counted.group(2) and int(counted.group(1)) >= 20)

        e2e = base / 'e2e.json'
        code, out = run(['npx', 'playwright', 'test', 'e2e/space.spec.ts'], ui,
                        env={'VELDO_UI_DIST': str(dist), 'VELDO_ORGANS': str(organs), 'VELDO_E2E_REPORT': str(e2e)},
                        timeout=3000)
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
        check('ui/api-only', 'the spec file holds exactly this suite\'s browser rows [%s]' % sorted(set(seen) ^ set(BROWSER)),
              set(seen) == set(BROWSER))

    try:
        with tempfile.TemporaryDirectory(prefix='v319-ui-') as directory:
            exercise(Path(directory))
    except Exception as error:  # noqa: BLE001
        all_rows('ran to its end (raised %s: %s)' % (type(error).__name__, str(error)[:250]))
    for name, observed in rows.items():
        ok = bool(observed) and all(one for _, one in observed)
        for label, one in observed:
            if not one or os.environ.get('VELDO_0319_DETAILS'):
                print('  VELDO-0319 space319ui/%s %s: %s' % (name, 'detail' if not one else 'observed', label))
        if not observed:
            print('  VELDO-0319 space319ui/%s detail: no check ran' % name)
        expect('VELDO-0319 space319ui/' + name, ok)
    print('VELDO-0319 UI suite seconds: %.3f' % (time.monotonic() - started))


_v319_space_ui()
