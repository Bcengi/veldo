"""VELDO-0230 AC2: the one command, run against the qualified binaries, reproduces the shipped files byte for byte.

Run: python3 scripts/selftest.py --suite 126_veldo_0230_qualify_reproduces

Only shared ROOT and expect are consumed. Copies what the qualify command reads and writes (the .veldo modules and
runtime records, the engine canon's runtime, the packs, and the proof directories of every extractor and of the
VELDO-0127 fixtures) into scratch, runs the copy's `python3 .veldo/qualify.py` with the Codex and the Claude Code
binaries the engines record names, and requires: the command succeeds; it reports every file it wrote; each
written file is byte-identical to the checkout's; and the written set covers both qualification records and the
engines record in every runtime copy, every extractor's table and the VELDO-0127 fixtures. Runs the qualified
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
    ROWS = ('qualify/reproduces', 'qualify/covers')
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
        differing = [name for name in written
                     if not (tree / name).is_file() or (tree / name).read_bytes() != (ROOT / name).read_bytes()]
        check('qualify/reproduces', 'every file it wrote is byte-identical to the checkout\'s [%s]' % differing[:6],
              bool(written) and not differing)
        record = json.loads((tree / '.veldo' / 'runtime' / 'engines.json').read_text())
        check('qualify/reproduces', 'it qualified the engines record\'s versions',
              record['codex']['version'] == engines['codex']['version']
              and record['claude_code']['version'] == engines['claude_code']['version'])
        wanted = {'.veldo/runtime/engines.json', 'engine/runtime/engines.json',
                  '.veldo/runtime/codex-qualification.json', 'engine/runtime/codex-qualification.json',
                  '.veldo/runtime/claude-qualification.json', 'engine/runtime/claude-qualification.json',
                  'proof/VELDO-0127/catalog-fixture.json', 'proof/VELDO-0127/features-fixture.json',
                  'proof/VELDO-0127/resource-qualification.json'}
        # The suite's own list of every table the binaries' readers write (never the command's own list, so
        # a command that stops running one reds this row).
        tables = {'proof/VELDO-0060/cli-options.json', 'proof/VELDO-0061/codex-exec.json',
                  'proof/VELDO-0062/cli-formats.json', 'proof/VELDO-0141/stream-formats.json',
                  'proof/VELDO-0155/claude-baseline.json', 'proof/VELDO-0156/codex-baseline.json',
                  'proof/VELDO-0156/codex-rendered.json', 'proof/VELDO-0156/codex-mentions.json',
                  'proof/VELDO-0165/claude-environment.json', 'proof/VELDO-0165/codex-environment.json',
                  'proof/VELDO-0173/claude-tools.json', 'proof/VELDO-0185/login-status.json'}
        check('qualify/covers', 'it wrote the engines record and both qualification records in both runtimes and '
              'the VELDO-0127 fixtures [missing %s]' % sorted(wanted - set(written)), wanted <= set(written))
        check('qualify/covers', 'it ran every reader of the binaries in write mode [missing %s]'
              % sorted(tables - set(written)), tables <= set(written))
    except Exception as error:
        for row in ROWS:
            check(row, 'raised ' + type(error).__name__ + ': ' + str(error)[:200], False)
    finally:
        shutil.rmtree(temp, ignore_errors=True)

    for row, values in rows.items():
        failed = [label for label, ok in values if not ok]
        expect('VELDO-0230 ' + row + (': ' + failed[0] if failed else ''), bool(values) and not failed)


_v230_reproduce_suite()
