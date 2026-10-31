"""VELDO-0163: the owner writes a role's capability configuration and a project's team roles (and the default team)
in the factory UI, through VELDO-0162's routes.

Run: python3 scripts/selftest.py --suite 119_veldo_0163_role_team_form

Only shared ROOT and expect are consumed. The UI source (engine/ui) is copied into scratch with the production
copies named in PRODUCTION below laid over it (the registered mutation driver substitutes each of them here), its
locked dependencies are the checkout's engine/ui/node_modules (or `npm ci --prefer-offline` into the scratch copy
when the checkout has none), and it is built with the package's own build script (vue-tsc, then vite). Then:

- unit/forms: the forms' Vitest specs (src/features/roles, src/features/team) in jsdom.
- every other row: the browser tests of engine/ui/e2e/roles.spec.ts in system Chrome (Playwright), against
  e2e/team_harness.py: VELDO-0145's real factory harness (a signed SQLite store, real membership, the real
  inbox, presenter, settlement and API authority, the real control_api on its loopback listener serving the
  scratch build under its content security policy, passkeys as real WebAuthn ceremonies from Chrome's virtual
  authenticator) with the real VELDO-0144 catalog, VELDO-0127 configuration and VELDO-0089 team services and
  VELDO-0162's routes handed to that authority. The harness's modules are the checkout's .veldo. Each test's
  title begins with its row name; a row is green only when its test ran and passed.

Needs node (the nvm toolchain), the npm cache or a checkout node_modules, and system Chrome; without them every
row fails by name. Writes only temporary files.
"""


def _v163_suite():
    import json
    import os
    from pathlib import Path
    import shutil
    import subprocess
    import tempfile
    import time

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'src/features/roles/useRoleForm.ts': ROOT / "engine/ui/src/features/roles" / "useRoleForm.ts",
        'src/features/team/useTeamForm.ts': ROOT / "engine/ui/src/features/team" / "useTeamForm.ts",
        'src/features/team/team-draft.ts': ROOT / "engine/ui/src/features/team" / "team-draft.ts",
    }
    ROWS = ('unit/forms', 'role/revisions', 'role/stale-save', 'role/widths', 'team/owner-save', 'team/authoritative',
            'team/refusals', 'team/default-team', 'team/default-stale-save', 'team/widths')
    rows = {name: [] for name in ROWS}
    started = time.monotonic()
    UI = ROOT / 'engine' / 'ui'
    SKIP = {'node_modules', 'dist', 'test-results', 'playwright-report'}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def all_rows(label, condition=False):
        for row in ROWS:
            check(row, label, condition)

    def tail(text, n=12):
        lines = [line.strip() for line in (text or '').splitlines() if line.strip()]
        return ' | '.join(line.encode('ascii', 'replace').decode() for line in lines[-n:])[:900]

    def run(args, cwd, env=None, timeout=900):
        try:
            done = subprocess.run(args, cwd=str(cwd), env=dict(os.environ, **(env or {})), capture_output=True,
                                  text=True, timeout=timeout, stdin=subprocess.DEVNULL)
            return done.returncode, (done.stdout or '') + (done.stderr or '')
        except (OSError, subprocess.TimeoutExpired) as error:
            return -1, '%s: %s' % (type(error).__name__, error)

    def exercise(base):
        # The UI source in scratch, beside the checkout's .veldo and proof (the harness reads both through its
        # own ROOT, three levels above e2e/), with the production copies laid over it.
        ui = base / 'engine' / 'ui'
        shutil.copytree(UI, ui, ignore=lambda d, names: [n for n in names if n in SKIP and Path(d) == UI])
        for relative, source in PRODUCTION.items():
            target = ui / relative
            if Path(source).is_file():
                target.write_bytes(Path(source).read_bytes())
            elif target.exists():
                target.unlink()
        os.symlink(ROOT / '.veldo', base / '.veldo')
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

        report = base / 'vitest.json'
        code, out = run(['npx', 'vitest', 'run', 'src/features/roles', 'src/features/team', '--reporter=json',
                         '--outputFile=' + str(report)], ui, timeout=300)
        try:
            unit = json.loads(report.read_text())
        except (OSError, ValueError):
            unit = {}
        failed = [a.get('fullName') for f in unit.get('testResults') or [] for a in f.get('assertionResults') or []
                  if a.get('status') != 'passed']
        check('unit/forms', 'the role and team forms\' unit specs pass [%s passed, failed %s; %s]'
              % (unit.get('numPassedTests'), failed[:4], '' if code == 0 else tail(out, 6)),
              code == 0 and unit.get('numPassedTests', 0) > 0 and unit.get('numFailedTests', 1) == 0 and not failed)

        e2e = base / 'e2e.json'
        code, out = run(['npx', 'playwright', 'test', 'e2e/roles.spec.ts'], ui,
                        env={'VELDO_UI_DIST': str(dist), 'VELDO_ORGANS': str(ROOT / '.veldo'),
                             'VELDO_E2E_REPORT': str(e2e)}, timeout=1200)
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
        for row in ROWS[1:]:
            outcomes, errors = seen.get(row, ([], []))
            check(row, 'its browser test ran and passed [%s%s]' % (
                outcomes or 'not run: ' + tail(out, 6), ('; ' + tail(errors[0], 4)) if errors else ''),
                outcomes == ['passed'])

    try:
        with tempfile.TemporaryDirectory(prefix='v163-') as directory:
            exercise(Path(directory))
    except Exception as error:  # noqa: BLE001
        all_rows('ran to its end (raised %s: %s)' % (type(error).__name__, str(error)[:250]))
    for name, observed in rows.items():
        ok = bool(observed) and all(one for _, one in observed)
        for label, one in observed:
            if not one or os.environ.get('VELDO_0163_DETAILS'):
                print('  VELDO-0163 %s %s: %s' % (name, 'detail' if not one else 'observed', label))
        if not observed:
            print('  VELDO-0163 %s detail: no check ran' % name)
        failed = next((label for label, one in observed if not one), 'no check ran' if not observed else '')
        expect('VELDO-0163 ' + name + (': ' + failed if failed else ''), ok)
    print('VELDO-0163 suite seconds: %.3f' % (time.monotonic() - started))


_v163_suite()
