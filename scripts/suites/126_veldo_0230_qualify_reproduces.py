"""VELDO-0230 AC2: the one command, run against the qualified binaries, reproduces the shipped files byte for byte.

Run: python3 scripts/selftest.py --suite 126_veldo_0230_qualify_reproduces

Only shared ROOT and expect are consumed. Copies what the qualify command reads and writes (the .veldo modules and
runtime records, the engine canon's runtime, the packs, and the proof directories of every extractor and of the
VELDO-0127 fixtures) into scratch, runs the copy's `python3 .veldo/qualify.py` with the Codex and the Claude Code
binaries the engines record names, and requires: the command succeeds; it reports every file it wrote; each
written file is byte-identical to the checkout's (a qualification summary's check durations aside); and the written
set covers both engines' reviewed tables and qualification summaries and the engines record in every runtime copy
and the VELDO-0127 fixtures. VELDO-0275 AC1: every extractor runs as a check (its --check mode), named with a pass
in both summaries it reads, and none of their tables is rewritten; each summary is small (under 1 MB, per check
only name, outcome and duration) and the engines record names it. Runs the qualified
binaries offline (extractor reads, the VELDO-0156 prompt rendering and loopback request, `features list`, `debug models --bundled`, the loopback capture and the
Claude Code init probe in empty profiles); writes only temporary files.
"""


def _v230_reproduce_suite():
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import subprocess
    import sys
    import tempfile

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'qualify.py': ROOT / ".veldo" / "qualify.py",
    }
    ROWS = ('qualify/reproduces', 'qualify/covers', 'qualify/builtin-plugins', 'qualify/gate-reads')
    rows = {name: [] for name in ROWS}
    COPIED = ('.veldo', 'engine/runtime', 'packs', 'proof/VELDO-0060', 'proof/VELDO-0061', 'proof/VELDO-0062',
              'proof/VELDO-0127', 'proof/VELDO-0141', 'proof/VELDO-0155', 'proof/VELDO-0156', 'proof/VELDO-0165',
              'proof/VELDO-0172', 'proof/VELDO-0173', 'proof/VELDO-0185')

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def builtin_plugins_row():
        """A fake Claude Code whose bytes register two built-in plugins and whose init probe (empty, logged-out
        profile) loads only one: the plugin the account seats (as 2.1.317's cc-plugin-sec-default) must be found,
        listed with its evaluation and, granted, accepted in the init event; one with no evaluation turned off."""
        row = 'qualify/builtin-plugins'
        probed, unlisted, seated = 'cc-plugin-fixture-probed', 'cc-plugin-fixture-unlisted', 'cc-plugin-fixture-seated'
        scratch = Path(tempfile.mkdtemp(prefix='v230-builtins-'))
        try:
            fake = scratch / 'claude'
            fake.write_text('#!%s\nimport json, sys\n# function O(){if(r.builtinPluginsInitialized=!0,'
                            'reg("%s",()=>import.meta.require("/$bunfs/root/chunk-a.js")),'
                            'reg("%s",()=>import.meta.require("/$bunfs/root/chunk-b.js")),'
                            'reg("%s",()=>import.meta.require("/$bunfs/root/chunk-c.js")))}\n'
                            'sys.stdin.readline()\n'
                            'print(json.dumps({"type": "system", "subtype": "init", "skills": [], "plugins": '
                            '[{"name": "%s", "source": "%s@builtin"}]}))\n'
                            % (sys.executable, probed, unlisted, seated, probed, probed))
            fake.chmod(0o755)
            qualify = load('v230_builtins_qualify', PRODUCTION['qualify.py'])
            C = load('v230_builtins_claude', ROOT / '.veldo' / 'control_engine_claude.py')
            plugins, _skills = qualify.claude_builtins(fake, C.BASELINE)
            check(row, 'discovery finds every built-in plugin the binary registers, not only the probe\'s [%s]'
                  % plugins, {probed + '@builtin', unlisted + '@builtin', seated + '@builtin'} <= set(plugins))
            decisions = {'claude_code': {'plugins': {seated + '@builtin': {'decision': 'granted', 'reason': 'fixture'}}}}
            split = getattr(qualify, 'builtin_plugins', None)
            off, accepted, items = split(plugins, {'engine_plugins': [probed + '@builtin']}, set(), False,
                                         decisions) if split else (plugins, [], [])
            listed = {i['name']: i['decision'] for i in items}
            check(row, 'each new built-in plugin is listed with its evaluation [%s]' % listed,
                  listed == {unlisted + '@builtin': 'unevaluated', seated + '@builtin': 'granted'})
            check(row, 'the granted one is accepted, the others turned off [%s; %s]' % (off, accepted),
                  accepted == [seated + '@builtin'] and off == sorted([probed + '@builtin', unlisted + '@builtin']))
            H = load('v230_builtins_handoff', ROOT / '.veldo' / 'control_agent_config_handoff.py')
            wanted = {'tools': [], 'mcp_servers': [], 'skills': [], 'slash_commands': [], 'plugins': [], 'model': None,
                      'accepted_plugins': accepted}
            init = lambda *names: {'tools': [], 'mcp_servers': [], 'skills': [], 'slash_commands': [],
                                   'plugins': [{'name': n, 'source': n + '@builtin'} for n in names]}
            check(row, 'the init comparison accepts the granted plugin present or absent',
                  H.difference(init(seated), wanted) is None and H.difference(init(), wanted) is None)
            check(row, 'an unlisted plugin still stops the run',
                  H.difference(init(seated, unlisted), wanted) == 'configuration_stop:plugins')
        except Exception as error:
            check(row, 'raised ' + type(error).__name__ + ': ' + str(error)[:200], False)
        finally:
            shutil.rmtree(scratch, ignore_errors=True)

    def gate_reads_row():
        """AC2/AC3: the gate's confinement (the gate profile and the mutation workers) can read every binary the
        engines record names, so a suite that runs the qualified binary compares against it, not against a
        PermissionError. Read roots are the sandbox configuration's optional_read_roots; '~' is the account home."""
        import pwd
        row = 'qualify/gate-reads'
        home = Path(pwd.getpwuid(os.getuid()).pw_dir)
        engines = json.loads((ROOT / '.veldo' / 'runtime' / 'engines.json').read_text())
        for config in ('scripts/agent_sandbox.json', 'engine/scripts/agent_sandbox.json'):
            roots = [Path(str(r).replace('~', str(home), 1)) if str(r).startswith('~') else Path(r)
                     for r in json.loads((ROOT / config).read_text()).get('optional_read_roots', [])]
            for engine in ('codex', 'claude_code'):
                named = engines[engine]['binary']
                path = Path(named.replace('~', str(home), 1)) if named.startswith('~') else Path(named)
                check(row, '%s lists a read root above the qualified %s binary %s' % (config, engine, named),
                      any(path == r or r in path.parents for r in roots))

    builtin_plugins_row()
    gate_reads_row()
    temp = tempfile.mkdtemp(prefix='v230-qualify-')
    try:
        tree = Path(temp) / 'tree'
        for part in COPIED:
            source = ROOT / part
            if source.is_dir():
                shutil.copytree(source, tree / part, symlinks=True,
                                ignore=shutil.ignore_patterns('__pycache__', '*.db', 'events.jsonl'))
        shutil.copyfile(PRODUCTION['qualify.py'], tree / '.veldo' / 'qualify.py')
        engines = json.loads((ROOT / '.veldo' / 'runtime' / 'engines.json').read_text())
        qualify = load('v230_reproduce_qualify', PRODUCTION['qualify.py'])
        codex, claude = qualify.binary('codex', engines), qualify.binary('claude_code', engines)
        done = subprocess.run([sys.executable, '-B', str(tree / '.veldo' / 'qualify.py'), '--codex', str(codex),
                               '--claude', str(claude), '--root', str(tree)],
                              capture_output=True, text=True, timeout=1500, stdin=subprocess.DEVNULL,
                              env={'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'HOME': os.environ.get('HOME', '/'),
                                   'LANG': 'C.UTF-8', 'TMPDIR': tempfile.gettempdir()})
        written = [line[len('wrote '):] for line in done.stdout.splitlines() if line.startswith('wrote ')]
        check('qualify/reproduces', 'the command qualifies the engines record\'s binaries [exit %s %s]'
              % (done.returncode, done.stderr.strip().splitlines()[-1:] if done.stderr.strip() else ''),
              done.returncode == 0 and bool(written))
        def same(name):
            if not (tree / name).is_file():
                return False
            if not name.endswith('-summary.json'):
                return (tree / name).read_bytes() == (ROOT / name).read_bytes()
            # VELDO-0275 AC1: a summary's durations are the run's own; everything else reproduces.
            timeless = lambda path: dict(json.loads(path.read_text()), checks=[
                {k: v for k, v in c.items() if k != 'duration_s'} for c in json.loads(path.read_text())['checks']])
            return timeless(tree / name) == timeless(ROOT / name)
        differing = [name for name in written if not same(name)]
        check('qualify/reproduces', 'every file it wrote is byte-identical to the checkout\'s [%s]' % differing[:6],
              bool(written) and not differing)
        record = json.loads((tree / '.veldo' / 'runtime' / 'engines.json').read_text())
        check('qualify/reproduces', 'it qualified the engines record\'s versions',
              record['codex']['version'] == engines['codex']['version']
              and record['claude_code']['version'] == engines['claude_code']['version'])
        wanted = {'.veldo/runtime/engines.json', 'engine/runtime/engines.json',
                  '.veldo/runtime/codex-tables.json', 'engine/runtime/codex-tables.json',
                  '.veldo/runtime/claude-tables.json', 'engine/runtime/claude-tables.json',
                  'proof/VELDO-0127/catalog-fixture.json', 'proof/VELDO-0127/features-fixture.json',
                  'proof/VELDO-0127/resource-qualification.json', 'proof/VELDO-0127/fixture-models.json',
                  '.veldo/runtime/claude-summary.json', 'engine/runtime/claude-summary.json',
                  '.veldo/runtime/codex-summary.json', 'engine/runtime/codex-summary.json'}
        # The suite's own list of every table the binaries' readers write (never the command's own list, so
        # a command that stops running one reds this row).
        tables = {'proof/VELDO-0060/cli-options.json', 'proof/VELDO-0061/codex-exec.json',
                  'proof/VELDO-0062/cli-formats.json', 'proof/VELDO-0141/stream-formats.json',
                  'proof/VELDO-0155/claude-baseline.json', 'proof/VELDO-0156/codex-baseline.json',
                  'proof/VELDO-0156/codex-rendered.json', 'proof/VELDO-0156/codex-mentions.json',
                  'proof/VELDO-0165/claude-environment.json', 'proof/VELDO-0165/codex-environment.json',
                  'proof/VELDO-0173/claude-tools.json', 'proof/VELDO-0185/login-status.json'}
        check('qualify/covers', 'it wrote the engines record and both engines\' tables and summaries in both runtimes '
              'and the VELDO-0127 fixtures [missing %s]' % sorted(wanted - set(written)), wanted <= set(written))
        # VELDO-0275 AC1: the suite's own list of every reader of the binaries, each a check in the summary of every
        # engine it reads; none of their tables is rewritten (the suites keep comparing against the committed ones).
        # (Each path is joined here, so this suite's text names no proof module it does not load.)
        readers = {'proof/%s/%s' % pair: reads for pair, reads in (
            (('VELDO-0062', 'extract_formats.py'), ('claude_code', 'codex')),
            (('VELDO-0061', 'extract_items.py'), ('codex',)), (('VELDO-0060', 'extract_cli.py'), ('claude_code',)),
            (('VELDO-0141', 'extract_stream.py'), ('claude_code', 'codex')),
            (('VELDO-0155', 'extract_baseline.py'), ('claude_code',)),
            (('VELDO-0156', 'extract_baseline.py'), ('codex',)), (('VELDO-0156', 'render_offline.py'), ('codex',)),
            (('VELDO-0156', 'capture_mentions.py'), ('codex',)),
            (('VELDO-0165', 'extract_environment.py'), ('claude_code', 'codex')),
            (('VELDO-0173', 'extract_tools.py'), ('claude_code',)),
            (('VELDO-0185', 'extract_login_status.py'), ('claude_code',)))}
        summaries = {engine: json.loads((tree / '.veldo' / 'runtime' / name).read_text())
                     for engine, name in (('claude_code', 'claude-summary.json'), ('codex', 'codex-summary.json'))}
        unchecked = sorted('%s:%s' % (engine, script) for script, reads in readers.items() for engine in reads
                           if {'name': script, 'outcome': 'pass'} not in [
                               {k: c.get(k) for k in ('name', 'outcome')} for c in summaries[engine]['checks']])
        check('qualify/covers', 'every reader of the binaries ran as a passed check of each engine it reads [missing %s]'
              % unchecked[:4], not unchecked)
        check('qualify/covers', 'it rewrote none of the readers\' tables [%s]' % sorted(tables & set(written)),
              not tables & set(written))
        heavy = [engine for engine, summary in summaries.items()
                 if len(json.dumps(summary)) >= 1 << 20 or summary.get('verdict') != 'approved'
                 or summary.get('version') != record[engine]['version'] or summary.get('sha256') != record[engine]['sha256']
                 or any(set(c) != {'name', 'outcome', 'duration_s'} for c in summary.get('checks') or [None])
                 or record[engine].get('summary') != 'runtime/' + {'claude_code': 'claude', 'codex': 'codex'}[engine]
                 + '-summary.json']
        check('qualify/covers', 'each summary is under 1 MB, approved for the recorded version and digest, holds per '
              'check only its name, outcome and duration, and the engines record names it [%s]' % heavy, not heavy)
    except Exception as error:
        for row in ROWS[:2]:
            check(row, 'raised ' + type(error).__name__ + ': ' + str(error)[:200], False)
    finally:
        shutil.rmtree(temp, ignore_errors=True)

    for row, values in rows.items():
        failed = [label for label, ok in values if not ok]
        expect('VELDO-0230 ' + row + (': ' + failed[0] if failed else ''), bool(values) and not failed)


_v230_reproduce_suite()
