"""VELDO-0159: the owner defines an MCP server in the UI's server form, each save a new catalog revision through the
API's catalog route (AC1), and sets its credential through a write-only field (AC2).

Run: python3 scripts/selftest.py --suite 118_veldo_0159_mcp_credential_form

Only shared ROOT and expect are consumed. The UI source (engine/ui) is copied into scratch with the production copies
named in PRODUCTION laid over it, built there with the package's own build script (type-check, then Vite), and its
browser rows (engine/ui/e2e/servers.spec.ts, Playwright in system Chrome) run against the browser tests' real factory
harness (engine/ui/e2e/harness.py): a signed SQLite authority store, the real control_api_authority with the real
VELDO-0144 catalog and credential commands, the real protected signer and the real control_api.ControlApi on the real
loopback listener serving that build, with a passkey session from the browser's virtual authenticator. The keystore
is control_credential_keystore.SecretService running a stand-in `secret-tool` that keeps values in a 0600 scratch
file, so a value reaches it on standard input exactly as it reaches the Secret Service. Each browser test's title
names the row it proves in brackets; this suite reads the rows from Playwright's JSON report. The definition row runs
the form's pure definition module's unit tests (Vitest) in the same scratch copy. Needs `npm ci` in engine/ui and
Google Chrome; without them every row fails by name. Mutation workers replace the production copies named in
PRODUCTION, never assertions, the harness or the browser tests. Writes only temporary files.
"""


def _v159_suite():
    import glob
    import json
    import os
    from pathlib import Path
    import pwd
    import re
    import shutil
    import subprocess
    import tempfile
    import time

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'mcp.ts': ROOT / "engine/ui/src/api" / "mcp.ts",
        'ServerForm.vue': ROOT / "engine/ui/src/features/servers" / "ServerForm.vue",
        'CredentialField.vue': ROOT / "engine/ui/src/features/servers" / "CredentialField.vue",
        'ServersView.vue': ROOT / "engine/ui/src/views" / "ServersView.vue",
    }
    PLACE = {
        'mcp.ts': 'src/api/mcp.ts',
        'ServerForm.vue': 'src/features/servers/ServerForm.vue',
        'CredentialField.vue': 'src/features/servers/CredentialField.vue',
        'ServersView.vue': 'src/views/ServersView.vue',
    }
    BROWSER = ('mcp/define-desktop', 'mcp/define-phone', 'mcp/stale-save', 'mcp/phone-actions',
               'cred/metadata-only', 'cred/no-value-kept')
    ROWS = BROWSER + ('mcp/definition-unit',)
    rows = {name: [] for name in ROWS}
    started = time.monotonic()
    UI = ROOT / 'engine' / 'ui'

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def environment():
        """The caller's environment with the account's newest nvm Node first on PATH when it has one: the locked
        dependencies need a current Node, and a distribution's /usr/bin/node may be older."""
        env = dict(os.environ)
        home = pwd.getpwuid(os.getuid()).pw_dir
        found = sorted(glob.glob(os.path.join(home, '.nvm', 'versions', 'node', 'v*', 'bin')),
                       key=lambda p: [int(x) for x in re.findall(r'\d+', os.path.basename(os.path.dirname(p)))])
        if found:
            env['PATH'] = found[-1] + os.pathsep + env.get('PATH', '')
        return env

    def run(argv, cwd, env, timeout):
        try:
            done = subprocess.run(argv, cwd=str(cwd), env=env, capture_output=True, text=True, timeout=timeout)
            return done.returncode, (done.stdout or '') + (done.stderr or '')
        except (OSError, subprocess.SubprocessError) as error:
            return -1, '%s: %s' % (type(error).__name__, error)

    def tail(text, n=6):
        kept = [re.sub(r'[^\x20-\x7e]+', ' ', line).strip() for line in text.splitlines()
                if re.search(r'(error|Error|failed|Expected|Received|passed)', line)]
        return ' | '.join(kept[-n:])[:600]

    def specs(node):
        for spec in node.get('specs') or []:
            yield spec
        for child in node.get('suites') or []:
            yield from specs(child)

    def exercise(base):
        env = environment()
        if not (UI / 'node_modules' / '.bin' / 'vite').exists():
            for row in ROWS:
                check(row, 'engine/ui has its locked dependencies (run npm ci in engine/ui)', False)
            return
        repo = base / 'repo'
        ui = repo / 'engine' / 'ui'
        shutil.copytree(str(UI), str(ui), symlinks=True, ignore=shutil.ignore_patterns(
            'node_modules', 'dist', 'test-results', 'playwright-report'))
        os.symlink(str(UI / 'node_modules'), str(ui / 'node_modules'))
        os.symlink(str(ROOT / '.veldo'), str(repo / '.veldo'))
        for name, source in PRODUCTION.items():
            target = ui / PLACE[name]
            if target.exists():
                target.unlink()
            if Path(source).is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(str(source), str(target))
        dist = base / 'dist'
        code, out = run(['npm', 'run', 'build', '--', '--outDir', str(dist), '--emptyOutDir'], ui, env, 300)
        built = code == 0 and (dist / 'index.html').is_file()
        if not built:
            for row in ROWS:
                check(row, 'the UI with these production copies builds [%s]' % tail(out), False)
            return
        code, out = run([str(ui / 'node_modules' / '.bin' / 'vitest'), 'run', 'src/features/servers'], ui, env, 120)
        check('mcp/definition-unit', 'the form\'s definition module turns what the form holds into the catalog route\'s '
              'definition, by transport, and a stored revision back [%s]' % tail(out, 3), code == 0)
        report = base / 'e2e.json'
        browser_env = dict(env, VELDO_UI_DIST=str(dist), VELDO_E2E_REPORT=str(report), VELDO_ORGANS=str(ROOT / '.veldo'))
        browser_env.pop('VELDO_UI_INSTALLED', None)
        code, out = run([str(ui / 'node_modules' / '.bin' / 'playwright'), 'test', 'e2e/servers.spec.ts'], ui,
                        browser_env, 420)
        try:
            data = json.loads(report.read_text())
        except (OSError, ValueError):
            data = {}
        seen = {}
        for spec in specs(data):
            tag = re.search(r'\[([a-z0-9/-]+)\]', spec.get('title') or '')
            if tag:
                errors = [e.get('message', '') for t in spec.get('tests') or [] for r in t.get('results') or []
                          for e in r.get('errors') or []]
                seen.setdefault(tag.group(1), []).append((spec.get('title'), bool(spec.get('ok')),
                                                          re.sub(r'\x1b\[[0-9;]*m', '', ' '.join(errors))[:500]))
        for row in BROWSER:
            found = seen.get(row)
            if not found:
                check(row, 'its browser test ran [exit %s: %s]' % (code, tail(out)), False)
                continue
            for title, ok, error in found:
                check(row, '%s%s' % (title, '' if ok else ' [%s]' % error), ok)

    try:
        with tempfile.TemporaryDirectory(prefix='v159-') as directory:
            exercise(Path(directory))
    except Exception as error:  # noqa: BLE001
        for row in ROWS:
            check(row, 'ran to its end (raised %s: %s)' % (type(error).__name__, str(error)[:250]), False)
    for name, observed in rows.items():
        ok = bool(observed) and all(one for _, one in observed)
        for label, one in observed:
            if not one or os.environ.get('VELDO_0159_DETAILS'):
                print('  VELDO-0159 %s %s: %s' % (name, 'detail' if not one else 'observed', label))
        if not observed:
            print('  VELDO-0159 %s detail: no check ran' % name)
        failed = next((label for label, one in observed if not one), 'no check ran' if not observed else '')
        expect('VELDO-0159 ' + name + (': ' + failed if failed else ''), ok)
    print('VELDO-0159 suite seconds: %.3f' % (time.monotonic() - started))


_v159_suite()
