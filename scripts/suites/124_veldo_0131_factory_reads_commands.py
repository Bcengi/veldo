"""VELDO-0131: the factory's fix-round read rows and the owner's three work commands, split from suite 120 so that
each piece fits the mutation stage's floor (VELDO-0229: suite 120 took 51 s alone with the Nuxt UI, and its
mutation controls ran 85 to 120 s each under the gate's own load).

Run: python3 scripts/selftest.py --suite 124_veldo_0131_factory_reads_commands

Only shared ROOT, expect and WAITS (the support module) are consumed. As suite 120 does: the UI source (engine/ui) is copied into scratch with the
production copies named in PRODUCTION below laid over it (the registered mutation driver substitutes each of them
here), its locked dependencies are the checkout's engine/ui/node_modules (or `npm ci --prefer-offline` into the
scratch copy when the checkout has none), and it is built with the package's own build script (vue-tsc, then vite).
Then the browser tests of engine/ui/e2e/factory.spec.ts whose titles begin with one of this suite's rows
(Playwright --grep) run in system Chrome against e2e/factory_harness.py with the API organs of ORGANS (VELDO-0163's
team harness over VELDO-0145's real factory, as suite 120 describes):

- fix round 2 (review-2026-11-01): ac1/repositories, the read-only Git identities and repositories (a table on a
  desktop, cards on a phone); ac1/every-configuration, every stored role revision and skill; ac1/whole-catalog,
  every catalog server and credential record by label, set at and set by; ac1/usage-provider, each account's
  provider and the provider breakdown; ac1/worker-capability, each worker's capability and the named cap gap.
- fix round 3 (owner, Telegram 38184): ac2/priority-save, ac2/worker-stop and ac2/worker-cap, the owner's three work
  commands through the real API: accepted, a stale version refused and an unauthorized member refused beside the
  control, nothing written.

A row is green only when its test ran and passed.

VELDO-0358 (a gate's verdict does not depend on how busy the machine is). Every child this suite starts (the
install, the build, the unit run, the browser run) is a heavy child: WAITS.run_heavy, with no bound on its total
time, ended only after the process hang bound has passed with no output from it, and then reported as hung. The
browser run writes a line at each test and step (VELDO_E2E_PROGRESS), so that bound counts from its last step.
Rows added:
- timers/profile-applied (AC15): the harness the browser tests ran against selected the timers profile in its
  organs' timers table before loading them and reported it in its ready line; every effective value it reported,
  the harness's own sentinel entry among them, is the wait hang bound (timer_unset otherwise).
- wave1/no-sites (AC10): the wall-clock census over the browser configuration, fixtures, specifications and harness
  named in E2E below and over suites 120, 121 and 124 finds no site outside the declared exceptions.

Needs node (the nvm toolchain), the npm cache or a checkout node_modules, and system Chrome; without them every
row fails by name. Writes only temporary files.
"""


def _v131_reads_commands():
    import glob
    import importlib.util
    import json
    import os
    import pwd
    import re
    from pathlib import Path
    import shutil
    import tempfile

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
        # VELDO-0358 AC15: the timers table the organs arm their giving-up deadlines from (the canon's; the
        # checkout's synced copy is the same file once it is laid down).
        'timers.py': ROOT / "engine/.veldo" / "timers.py",
    }
    # Fix round 2 (review-2026-11-01 F1 to F5) and fix round 3 (owner, Telegram 38184); suite 120 runs the rest.
    BROWSER = ('ac1/repositories', 'ac1/every-configuration', 'ac1/whole-catalog', 'ac1/usage-provider',
               'ac1/worker-capability', 'ac2/priority-save', 'ac2/worker-stop', 'ac2/worker-cap')
    ROWS = BROWSER
    # VELDO-0358: the browser tests' own files (literal anchors: the registered mutation driver substitutes each of
    # them here). They are laid over the scratch copy with PRODUCTION, and wave1/no-sites reads them.
    E2E = {
        'playwright.config.ts': ROOT / "engine/ui" / "playwright.config.ts",
        'e2e/fixtures.ts': ROOT / "engine/ui/e2e" / "fixtures.ts",
        'e2e/factory-fixtures.ts': ROOT / "engine/ui/e2e" / "factory-fixtures.ts",
        'e2e/team-fixtures.ts': ROOT / "engine/ui/e2e" / "team-fixtures.ts",
        'e2e/factory.spec.ts': ROOT / "engine/ui/e2e" / "factory.spec.ts",
        'e2e/layout.spec.ts': ROOT / "engine/ui/e2e" / "layout.spec.ts",
        'e2e/screens.spec.ts': ROOT / "engine/ui/e2e" / "screens.spec.ts",
        'e2e/run.spec.ts': ROOT / "engine/ui/e2e" / "run.spec.ts",
        'e2e/harness.py': ROOT / "engine/ui/e2e" / "harness.py",
    }
    SUITES = {
        '120_veldo_0131_factory_ui.py': ROOT / "scripts/suites" / "120_veldo_0131_factory_ui.py",
        '121_veldo_0131_factory_screens_narrow.py': ROOT / "scripts/suites" / "121_veldo_0131_factory_screens_narrow.py",
        '124_veldo_0131_factory_reads_commands.py': ROOT / "scripts/suites" / "124_veldo_0131_factory_reads_commands.py",
    }
    WAVE = ('timers/profile-applied', 'wave1/no-sites')
    ROWS = ROWS + WAVE
    BUILT = tuple(row for row in ROWS if row != 'wave1/no-sites')
    rows = {name: [] for name in ROWS}
    started = WAITS.stamp()
    UI = ROOT / 'engine' / 'ui'
    SKIP = {'node_modules', 'dist', 'test-results', 'playwright-report'}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def all_rows(label, names=ROWS, condition=False):
        for row in names:
            check(row, label, condition)

    def tail(text, n=12):
        lines = [line.strip() for line in (text or '').splitlines()
                 if line.strip() and not line.startswith('e2e progress: ')]
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

    def run(args, cwd, kind, env=None):
        """One heavy child of `kind` (VELDO-0358): no bound on its total time. It is ended only after the process
        hang bound has passed with no output from it, and that is said in what is returned."""
        try:
            done = WAITS.run_heavy(args, kind, cwd=str(cwd), env=dict(environment(), **(env or {})))
        except OSError as error:
            return -1, '%s: %s' % (type(error).__name__, error)
        out = (done.stdout or '') + (done.stderr or '')
        if done.hung:
            return -1, out + '\nHUNG: the %s wrote nothing for the process hang bound and was ended' % kind
        return done.returncode, out

    def census_row():
        """wave1/no-sites: the census's own readers over the browser tests' files and the three suites."""
        try:
            spec = importlib.util.spec_from_file_location('v131_census', ROOT / 'scripts' / 'check_wallclock.py')
            census = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(census)
            found = []
            for relative, source in E2E.items():
                text, rel = Path(source).read_text(), 'engine/ui/' + relative
                found += (census.Python(rel, text, census.RULES).scan() if relative.endswith('.py')
                          else census.scan_script(rel, text, census.RULES))
            for name, source in SUITES.items():
                found += census.Python('scripts/suites/' + name, Path(source).read_text(), census.RULES).scan()
            excepted = census.load_list(ROOT / census.EXCEPTIONS, True)[0]
            counts, first = census.counted(found)
            over = sorted('%s:%s %s (%s)' % (first[k]['file'], first[k]['line'], k[1], first[k]['form'])
                          for k, n in counts.items() if n > excepted.get(k, 0))
        except Exception as error:  # noqa: BLE001
            check('wave1/no-sites', 'the census could be run (%s: %s)' % (type(error).__name__, error), False)
            return
        check('wave1/no-sites', 'the census finds no site outside the declared exceptions in the browser tests\' '
              'files and suites 120, 121 and 124 (wallclock_site %s)' % over[:8], not over)

    def timers_row(path):
        """timers/profile-applied: what each harness of the browser run said of the product's timers."""
        hang = WAITS.WAIT_HANG_SECONDS
        try:
            said = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
        except (OSError, ValueError):
            said = []
        check('timers/profile-applied', 'a harness of the browser run reported its timers (%d)' % len(said), said)
        for one in said:
            timers = one.get('timers') or {}
            values = {entry.get('name'): entry.get('value') for entry in timers.get('effective') or []}
            unset = sorted(str(name) for name, value in values.items() if value != hang)
            check('timers/profile-applied', '%s selected the profile of the wait hang bound with no timer excepted (%s)'
                  % (one.get('harness'), timers.get('profile')),
                  timers.get('profile') == {'except': None, 'hang_seconds': hang})
            check('timers/profile-applied', '%s reports its own sentinel entry among the table\'s (%s)'
                  % (one.get('harness'), sorted(map(str, values))), 'e2e_harness.SENTINEL_SECONDS' in values)
            check('timers/profile-applied', '%s: every effective timer is the wait hang bound (timer_unset %s)'
                  % (one.get('harness'), unset), not unset)

    def exercise(base):
        ui = base / 'engine' / 'ui'
        shutil.copytree(UI, ui, ignore=lambda d, names: [n for n in names if n in SKIP and Path(d) == UI])
        for relative, source in list(PRODUCTION.items()) + list(E2E.items()):
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
            code, out = run(['npm', 'ci', '--prefer-offline', '--no-audit', '--no-fund'], ui, 'package install')
            if code != 0:
                all_rows('the locked UI dependencies are installed (npm ci) [%s]' % tail(out), BUILT)
                return
        dist = base / 'dist'
        code, out = run(['npm', 'run', 'build', '--', '--outDir', str(dist), '--emptyOutDir'], ui,
                        'package install')  # the package's own build script, run by npm as its install is
        if code != 0 or not (dist / 'index.html').is_file():
            all_rows('the UI builds with its own build script (vue-tsc, then vite) [%s]' % tail(out), BUILT)
            return

        e2e = base / 'e2e.json'
        said = base / 'timers.jsonl'
        browser_env = {'VELDO_UI_DIST': str(dist), 'VELDO_ORGANS': str(organs), 'VELDO_E2E_REPORT': str(e2e),
                       'VELDO_E2E_PROGRESS': '1', 'VELDO_E2E_TIMERS': str(said)}
        # Only this suite's rows: the title of each test begins with its row name and a colon.
        code, out = run(['npx', 'playwright', 'test', 'e2e/factory.spec.ts', '--grep', '(' + '|'.join(BROWSER) + '):'],
                        ui, 'browser run', env=browser_env)
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
        timers_row(said)

    census_row()
    try:
        with tempfile.TemporaryDirectory(prefix='v131-') as directory:
            exercise(Path(directory))
    except Exception as error:  # noqa: BLE001
        all_rows('ran to its end (raised %s: %s)' % (type(error).__name__, str(error)[:250]), BUILT)
    for name, observed in rows.items():
        ok = bool(observed) and all(one for _, one in observed)
        for label, one in observed:
            if not one or os.environ.get('VELDO_0131_DETAILS'):
                print('  VELDO-0131 %s %s: %s' % (name, 'detail' if not one else 'observed', label))
        if not observed:
            print('  VELDO-0131 %s detail: no check ran' % name)
        failed = next((label for label, one in observed if not one), 'no check ran' if not observed else '')
        expect('VELDO-0131 ' + name + (': ' + failed if failed else ''), ok)
    print('VELDO-0131 suite began %s, ended %s' % (started.iso(), WAITS.stamp().iso()))


_v131_reads_commands()
