"""VELDO-0131: the Veldo factory UI on phone and desktop (the factory screens beside VELDO-0145's shell, run
terminal and decisions, VELDO-0159's server form and VELDO-0163's role and team forms).

Run: python3 scripts/selftest.py --suite 120_veldo_0131_factory_ui

Only shared ROOT, expect and WAITS (the support module) are consumed. The UI source (engine/ui) is copied into scratch with the production
copies named in PRODUCTION below laid over it (the registered mutation driver substitutes each of them here), its
locked dependencies are the checkout's engine/ui/node_modules (or `npm ci --prefer-offline` into the scratch copy
when the checkout has none), and it is built with the package's own build script (vue-tsc, then vite). Then:

- unit/factory: the factory screens' Vitest specs (backlog, completion, projects, proof, usage, configuration,
  catalog, workflow document, workers, the hierarchy table) in jsdom.
- ac4/dependency-policy: VELDO-0145's dependency policy (control_api_ui.dependency_problems, the checkout's
  .veldo) applied to the production lockfile, package.json and dependency-policy.json: every package's license
  allowed, nothing on the deny list (Chinese-origin libraries, libraries with free and paid tiers, shadcn and
  Recharts), every direct package pinned and recorded with its origin, license and tier.
- ac4/stack: the lockfile holds the owner's stack (vue, vue-router, pinia, vite, typescript, tailwindcss,
  monaco-editor, @tanstack/vue-table, chart.js, and Nuxt UI since VELDO-0229) and none of the rejected one
  (react, react-dom, recharts, shadcn, primevue, @vue-flow; @vueuse is no longer rejected, VELDO-0229, the
  VELDO-0131 amendment of 2026-11-01); every direct dependency is one of the stack's or the build's own.
- ac4/served-assets: the build's assets name none of the rejected libraries; the browser row ac2/api-only
  checks that every response the page used came from this origin.
- every other row: the browser tests of engine/ui/e2e/factory.spec.ts but the four ac1/screens tests and the eight
  fix-round tests (Playwright --grep-invert; suites 121_veldo_0131_factory_screens_narrow,
  122_veldo_0131_factory_screens_wide and 124_veldo_0131_factory_reads_commands run those, so that each suite fits
  the mutation stage's floor) in system Chrome, against
  e2e/factory_harness.py: VELDO-0163's team harness over VELDO-0145's real factory (a signed SQLite store,
  real membership, the real inbox, presenter, settlement and API authority, the real control_api on its
  loopback listener serving the scratch build under its content security policy, passkeys as real WebAuthn
  ceremonies) with the real VELDO-0051 journal feed, the real VELDO-0132 workflow service, and the read
  models' records in their writers' stored shapes. Each test's title begins with its row name; a row is green
  only when its test ran and passed.

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


def _v131_suite():
    import fnmatch
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
    }
    # The four ac1/screens rows (360, 390, 1280 and 1440 px) are suites 121 and 122; the fix-round rows
    # ac1/repositories, ac1/every-configuration, ac1/whole-catalog, ac1/usage-provider, ac1/worker-capability,
    # ac2/priority-save, ac2/worker-stop and ac2/worker-cap are suite 124 (VELDO-0229).
    BROWSER = ('ac2/live', 'ac2/completion-receipt', 'ac2/message-intake', 'ac2/decision-settlement', 'ac2/refusals',
               'ac2/api-only', 'ac3/keyboard-desktop', 'ac3/touch-phone', 'ac3/stale-save',
               # Fix round 2 (review-2026-11-01 F1 to F5).
               'ac2/metadata-only')
    ELSEWHERE = ('ac1/screens-', 'ac1/repositories:', 'ac1/every-configuration:', 'ac1/whole-catalog:',
                 'ac1/usage-provider:', 'ac1/worker-capability:', 'ac2/priority-save:', 'ac2/worker-stop:',
                 'ac2/worker-cap:')
    ROWS = ('unit/factory', 'ac4/dependency-policy', 'ac4/stack', 'ac4/served-assets') + BROWSER
    STACK = ('vue', 'vue-router', 'pinia', 'vite', 'typescript', 'tailwindcss', 'monaco-editor', '@tanstack/vue-table',
             'chart.js', '@nuxt/ui')
    REJECTED = ('react', 'react-dom', 'recharts', 'shadcn', 'shadcn-vue', '@shadcn/*', 'primevue', '@primevue/*',
                '@vue-flow/*', 'vue-chartjs', 'echarts')
    BUILD = ('@axe-core/playwright', '@playwright/test', '@tailwindcss/vite', '@types/node', '@vitejs/plugin-vue',
             '@vue/test-utils', 'jsdom', 'vitest', 'vue-tsc', '@fontsource-variable/ibm-plex-sans',
             '@fontsource/ibm-plex-mono', '@iconify-json/lucide')
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

    def policy_rows():
        try:
            lock = json.loads(Path(PRODUCTION['package-lock.json']).read_text())
            package = json.loads((UI / 'package.json').read_text())
            policy = json.loads((UI / 'dependency-policy.json').read_text())
            spec = importlib.util.spec_from_file_location('v131_ui_policy', ROOT / '.veldo' / 'control_api_ui.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            problems = module.dependency_problems(lock, policy, package)
        except Exception as error:  # noqa: BLE001
            all_rows('the dependency policy could be applied (%s: %s)' % (type(error).__name__, error),
                     ('ac4/dependency-policy', 'ac4/stack'))
            return
        check('ac4/dependency-policy', 'the lockfile, package.json and the policy agree with no problem %s'
              % problems[:4], problems == [])
        installed = {path.rsplit('node_modules/', 1)[-1] for path in (lock.get('packages') or {}) if path}
        missing = [name for name in STACK if name not in installed]
        rejected = sorted(name for name in installed if any(fnmatch.fnmatchcase(name, r) for r in REJECTED))
        direct = set(package.get('dependencies') or {}) | set(package.get('devDependencies') or {})
        foreign = sorted(direct - set(STACK) - set(BUILD))
        check('ac4/stack', 'the lockfile holds the owner\'s stack (missing %s)' % missing, not missing)
        check('ac4/stack', 'the lockfile holds no rejected library (%s)' % rejected, not rejected)
        check('ac4/stack', 'every direct dependency is the stack\'s or the build\'s own (others %s)' % foreign,
              not foreign)

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
                all_rows('the locked UI dependencies are installed (npm ci) [%s]' % tail(out),
                         ('unit/factory', 'ac4/served-assets', 'timers/profile-applied') + BROWSER)
                return
        dist = base / 'dist'
        code, out = run(['npm', 'run', 'build', '--', '--outDir', str(dist), '--emptyOutDir'], ui,
                        'package install')  # the package's own build script, run by npm as its install is
        if code != 0 or not (dist / 'index.html').is_file():
            all_rows('the UI builds with its own build script (vue-tsc, then vite) [%s]' % tail(out),
                     ('unit/factory', 'ac4/served-assets', 'timers/profile-applied') + BROWSER)
            return

        assets = [p for p in (dist / 'assets').rglob('*') if p.is_file() and p.suffix in ('.js', '.css')]
        found = sorted({marker for p in assets for marker in ('recharts', 'react-dom', 'shadcn', 'primevue', 'vue-flow')
                        if marker in p.read_text(errors='replace')})
        check('ac4/served-assets', 'the build has assets (%d)' % len(assets), len(assets) > 0)
        check('ac4/served-assets', 'no built asset names a rejected library (%s)' % found, not found)

        report = base / 'vitest.json'
        code, out = run(['npx', 'vitest', 'run'] + ['src/features/' + f for f in (
            'backlog', 'projects', 'proof', 'usage', 'configuration', 'catalog', 'workflow', 'workers', 'table',
            'repositories')] + ['src/api/actions.spec.ts']
            + ['--reporter=json', '--outputFile=' + str(report)], ui, 'suite')
        try:
            unit = json.loads(report.read_text())
        except (OSError, ValueError):
            unit = {}
        failed = [a.get('fullName') for f in unit.get('testResults') or [] for a in f.get('assertionResults') or []
                  if a.get('status') != 'passed']
        check('unit/factory', 'the factory screens\' unit specs pass [%s passed, failed %s; %s]'
              % (unit.get('numPassedTests'), failed[:4], '' if code == 0 else tail(out, 6)),
              code == 0 and unit.get('numPassedTests', 0) > 0 and unit.get('numFailedTests', 1) == 0 and not failed)

        e2e = base / 'e2e.json'
        said = base / 'timers.jsonl'
        browser_env = {'VELDO_UI_DIST': str(dist), 'VELDO_ORGANS': str(organs), 'VELDO_E2E_REPORT': str(e2e),
                       'VELDO_E2E_PROGRESS': '1', 'VELDO_E2E_TIMERS': str(said)}
        code, out = run(['npx', 'playwright', 'test', 'e2e/factory.spec.ts', '--grep-invert', '|'.join(ELSEWHERE)],
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

    policy_rows()
    census_row()
    try:
        with tempfile.TemporaryDirectory(prefix='v131-') as directory:
            exercise(Path(directory))
    except Exception as error:  # noqa: BLE001
        all_rows('ran to its end (raised %s: %s)' % (type(error).__name__, str(error)[:250]),
                 [row for row in ROWS if row != 'wave1/no-sites'])
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


_v131_suite()
