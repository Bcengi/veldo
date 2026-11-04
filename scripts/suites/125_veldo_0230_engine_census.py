"""VELDO-0230: upgrading an agent CLI is one command. The census of agent literals, a newer Claude Code tool
never blocking, and setup taking the Claude Code copy the engines record names.

Run: python3 scripts/selftest.py --suite 125_veldo_0230_engine_census

Only shared ROOT and expect are consumed. census/clean runs scripts/engine_census.py over the checkout: no
engine module, suite, mutation, extractor or fixture builder holds a literal agent version, digest, binary
path, model catalog, tool registry or feature list. census/planted-version and census/planted-digest plant the
qualified Codex version, and the qualified Claude Code digest, as a literal in a copy of a suite's source and
require the census to name it (AC1's falsifier); census/planted-model and census/planted-builtin plant one
catalog model name, a built-in plugin name and a two-name tuple of the built-in skills. newer/claude-tool reads the shipped Claude Code entry with one
registry tool its classification does not know: the VELDO-0173 extractor's classification makes it outward,
the record qualifies (no refusal), the launch options switch it off and the qualify command lists it by name
(AC3). setup/engines-record points `claude` on PATH at a newer, unqualified version and requires factory
setup's engine check to take the engines record's copy, and to refuse by name, not fall back to PATH, when the
record is absent (AC4). The Codex half of AC3 is suite 88's defaults/unknown row. Reads the checkout and the
qualified binaries' digests; writes only temporary files.
"""


def _v230_census_suite():
    import copy
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import tempfile

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'engine_census.py': ROOT / "scripts" / "engine_census.py",
        'qualify.py': ROOT / ".veldo" / "qualify.py",
        'control_factory_setup_engines.py': ROOT / ".veldo" / "control_factory_setup_engines.py",
        'control_engine_claude.py': ROOT / ".veldo" / "control_engine_claude.py",
    }
    ROWS = ('census/clean', 'census/planted-version', 'census/planted-digest', 'census/planted-model',
            'census/planted-builtin', 'newer/claude-tool', 'setup/engines-record')
    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def attempt(call):
        try:
            return call(), None
        except Exception as error:  # the refusal code, or the failure, is the observation
            return None, getattr(error, 'code', type(error).__name__ + ': ' + str(error))

    engines = json.loads((ROOT / '.veldo' / 'runtime' / 'engines.json').read_text())
    try:
        census = load('v230_census', PRODUCTION['engine_census.py'])
        found = census.census(ROOT)
        check('census/clean', 'no governed file holds an agent literal [%s]'
              % '; '.join('%s:%d %s %s' % f for f in found[:5]), found == [])
        check('census/clean', 'the census governs the engine modules, suites, mutations and extractors',
              {'.veldo/control_engine_codex.py', 'scripts/suites/125_veldo_0230_engine_census.py',
               'scripts/check_teeth_mutations.py', 'proof/VELDO-0062/extract_formats.py',
               'proof/VELDO-0127/wire_fixture.py'} <= set(census.governed(ROOT)))

        known = census.qualified(ROOT)
        source = Path(globals().get('__suite_file__', str(ROOT / 'scripts' / 'suites' / '125_veldo_0230_engine_census.py'))).read_text()
        planted = source + '\nPLANTED = %r\n' % engines['codex']['version']
        hits = census.findings(planted, known, 'planted.py')
        check('census/planted-version', 'the qualified Codex version planted in a suite is named [%s]' % hits,
              census.findings(source, known, 'clean.py') == [] and any(h[2] == 'version' for h in hits))
        planted = source + '\nPLANTED = %r\n' % engines['claude_code']['sha256']
        hits = census.findings(planted, known, 'planted.py')
        check('census/planted-digest', 'the qualified Claude Code digest planted in a suite is named [%s]' % hits,
              any(h[2] == 'digest' for h in hits))
        # VELDO-0230 fix round 1: one model name, and the qualified Claude Code's built-in settings (a plugin name;
        # a two-name tuple of its built-in plugins and skills), each planted alone.
        slug = sorted(known['slugs'])[0]
        hits = census.findings(source + '\nPLANTED = {"model": %r}\n' % slug, known, 'planted.py')
        check('census/planted-model', 'one catalog model name planted in a suite is named [%s]' % hits,
              any(h[2] == 'model_name' and h[3] == slug for h in hits))
        entry = json.loads((ROOT / '.veldo' / 'runtime' / 'claude-qualification.json').read_text())['versions'][
            engines['claude_code']['version']]
        pair = tuple(sorted(entry['engine_skills'])[:2]) if len(entry['engine_skills']) > 1 else (
            entry['engine_skills'][0], entry['engine_plugins'][0])
        hits = census.findings(source + '\nPLANTED = %r\n' % (pair,), known, 'planted.py')
        single = census.findings(source + '\nPLANTED = %r\n' % entry['engine_plugins'][0], known, 'planted.py')
        check('census/planted-builtin', 'a two-name tuple of the built-in skills, and one built-in plugin name, '
              'planted in a suite are named [%s, %s]' % (hits, single),
              any(h[2] == 'builtin_setting' for h in hits) and any(h[2] == 'builtin_setting' for h in single))
    except Exception as error:
        for row in ('census/clean', 'census/planted-version', 'census/planted-digest', 'census/planted-model',
                    'census/planted-builtin'):
            check(row, 'raised ' + type(error).__name__ + ': ' + str(error)[:200], False)

    try:
        claude = load('v230_claude', PRODUCTION['control_engine_claude.py'])
        qualify = load('v230_qualify', PRODUCTION['qualify.py'])
        extractor = load('v230_tools', ROOT / 'proof' / 'VELDO-0173' / 'extract_tools.py')
        version = engines['claude_code']['version']
        shipped = json.loads((ROOT / '.veldo' / 'runtime' / 'claude-qualification.json').read_text())
        entry = copy.deepcopy(shipped['versions'][version])
        tools = json.loads((ROOT / 'proof' / 'VELDO-0173' / 'claude-tools.json').read_text())
        future = {'name': 'FutureTool', 'hint': 'a tool a newer binary registers', 'hint_source': 'searchHint'}
        classification = extractor.classify(tools['registry'] + [future], tools['in_run'],
                                            tools.get('unregistered_in_run') or {})
        entry.update(tool_registry=sorted(entry['tool_registry'] + ['FutureTool']), tool_classification=classification)
        record = dict(shipped, versions={version: entry})
        qualified, error = attempt(lambda: claude.qualified_tools(version, entry))
        options, _ = attempt(lambda: claude.tool_options({'version': version, 'tools': qualified}))
        disallowed = (options or {}).get('report', {}).get('disallowed') or []
        listed = qualify.new_tools(entry, shipped['versions'][version]['tool_classification'])
        check('newer/claude-tool', 'an unknown registry tool is outward, the record qualifies, the launch switches it '
              'off and qualify lists it [%s %s %s]' % (error, classification.get('FutureTool'), listed),
              error is None and classification.get('FutureTool', {}).get('class') == 'outward'
              and 'FutureTool' in disallowed and 'FutureTool' not in (qualified or {}).get('in_run', [])
              and listed == [('FutureTool', 'outward')]
              and claude.qualified_baseline({'version': version}, record) == claude.BASELINE)
    except Exception as error:
        check('newer/claude-tool', 'raised ' + type(error).__name__ + ': ' + str(error)[:200], False)

    temp = tempfile.mkdtemp(prefix='v230-setup-')
    saved = os.environ.get('PATH', '')
    try:
        base = Path(temp)
        mods = base / 'mods'
        shutil.copytree(ROOT / '.veldo', mods, ignore=shutil.ignore_patterns('__pycache__', '*.db', 'events.jsonl'))
        shutil.copyfile(PRODUCTION['control_factory_setup_engines.py'], mods / 'control_factory_setup_engines.py')
        newer = base / 'versions' / '9.9.9'
        newer.parent.mkdir()
        newer.write_bytes(b'#!/bin/sh\nexit 0\n')
        newer.chmod(0o755)
        path = base / 'path'
        path.mkdir()
        (path / 'claude').symlink_to(newer)
        # Codex as setup finds it: the vendor binary of the qualified platform package.
        (path / 'codex').symlink_to(qualify.binary('codex', engines))

        class Refused(Exception):
            def __init__(self, code):
                self.code = code
                super().__init__(code)

        os.environ['PATH'] = str(path)
        setup = load('v230_setup_engines', mods / 'control_factory_setup_engines.py')
        result, error = attempt(lambda: setup.check(Refused))
        named = qualify.binary('claude_code', engines)
        check('setup/engines-record', 'with claude on PATH at an unqualified 9.9.9, setup takes the engines '
              "record's copy [%s %s]" % (error, (result or {}).get('claude_code')),
              error is None and result['claude_code'] == {'version': engines['claude_code']['version'],
                                                          'versions': str(named.parent)})
        (mods / 'runtime' / 'engines.json').unlink()
        result, error = attempt(lambda: setup.check(Refused))
        check('setup/engines-record', 'without the engines record setup refuses by name, never PATH [%s]' % error,
              error == 'missing_evidence:engine_source:claude_code' and result is None)
    except Exception as error:
        check('setup/engines-record', 'raised ' + type(error).__name__ + ': ' + str(error)[:200], False)
    finally:
        os.environ['PATH'] = saved
        shutil.rmtree(temp, ignore_errors=True)

    for row, values in rows.items():
        failed = [label for label, ok in values if not ok]
        expect('VELDO-0230 ' + row + (': ' + failed[0] if failed else ''), bool(values) and not failed)


_v230_census_suite()
