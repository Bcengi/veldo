"""VELDO-0296: the declarations reader for the installation's space section.

Run: python3 scripts/selftest.py --suite 130_veldo_0296_space_section

Only shared ROOT and expect are consumed. Every installation here is a FIXTURE folder written into a
temporary folder with invented values and read through the one installation reader; no real installation
is read (each read is given its own environment naming the fixture folder). The unit rows give the reader
a section directly; the integration rows read installation.yaml from disk.

AC1 rows: ac1/no-section (a fixture installation with settings and no space section reads as space
management off and is not refused), ac1/no-installation (no installation folder at all reads the same).

AC2 rows: ac2/missing-by-name (each of the nine keys left out, one at a time, and nested keys, refused as
installation_missing:<key>), ac2/missing-floor (the floor key left out of a pool is refused by its name,
from disk and from a given section), ac2/malformed-by-name (installation_invalid:<key> for each malformed
value), ac2/logged (one line naming the key and the reason, never the value).

AC3 rows, one per entry of the fixture's protect list, each asked on both engine contexts:
ac3/engine-image-folder, ac3/repository-folder, ac3/volume-pattern, ac3/container-pattern,
ac3/image-pattern, ac3/network-pattern, ac3/compose-project-one, ac3/compose-project-two,
ac3/image-name-one, ac3/image-name-two; ac3/whole-list (ten entries, nothing else, none without an engine);
and ac3/empty-engines (an engines list naming none is refused by name, from disk and from a given section,
so no protect list is ever in force on no engine).

AC4 rows: ac4/no-mode-key (the reader's key list and its answer carry no mode), ac4/mode-refused (mode: act
written into the section is refused as unknown by name, from disk and from a given section).

reader/full-section: the whole fixture section read back from disk, every key; reader/one-opener: the
declarations reader names no installation folder itself, and the engine canon equals this copy.
"""


def _v296_space_section_suite():
    import copy
    import importlib.util
    import io
    import shutil
    import tempfile
    from pathlib import Path

    # Literal anchors: the registered mutation driver substitutes the production copy here.
    PRODUCTION = {
        'control_space_config.py': ROOT / ".veldo" / "control_space_config.py",
    }
    ENTRY_ROWS = ('ac3/engine-image-folder', 'ac3/repository-folder', 'ac3/volume-pattern',
                  'ac3/container-pattern', 'ac3/image-pattern', 'ac3/network-pattern',
                  'ac3/compose-project-one', 'ac3/compose-project-two', 'ac3/image-name-one',
                  'ac3/image-name-two')
    ROWS = ('ac1/no-section', 'ac1/no-installation', 'ac2/missing-by-name', 'ac2/missing-floor',
            'ac2/malformed-by-name', 'ac2/logged') + ENTRY_ROWS + (
            'ac3/whole-list', 'ac3/empty-engines', 'ac4/no-mode-key', 'ac4/mode-refused', 'reader/full-section',
            'reader/one-opener')
    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    temp = Path(tempfile.mkdtemp(prefix='v296-'))
    try:
        CFG = load('v296_control_space_config', PRODUCTION['control_space_config.py'])
        YAML = load('v296_yamlish', PRODUCTION['control_space_config.py'].with_name('yamlish.py'))

        ENGINES = ['default', 'desktop-linux']
        ENGINE_IMAGE = str(temp / 'engine' / 'vms' / '0' / 'data')
        REPOSITORY = str(temp / 'projects' / 'atlas')
        MEGABYTE = 1024 * 1024
        SECTION = {
            'enabled': 'true',
            'time_zone': 'Europe/Lisbon',
            'pools': {
                'host': {'floor': 20000 * MEGABYTE,
                         'needs': {'build': 4000 * MEGABYTE, 'review': 1000 * MEGABYTE,
                                   'gate': 6000 * MEGABYTE}},
                'desktop': {'floor': 8000 * MEGABYTE,
                            'needs': {'build': 0, 'review': 0, 'gate': 3000 * MEGABYTE}},
            },
            'engines': list(ENGINES),
            'scratch_roots': {'roots': [str(temp / 'scratch')],
                              'session_pattern': 'sessions/{working_folder}/{session_id}'},
            'build_roots': [str(temp / 'build')],
            'plain_repositories': [{'repository': str(temp / 'projects' / 'plain'),
                                    'worktree_root': str(temp / 'projects' / 'plain-worktrees')}],
            'client_accounts': [str(temp / 'client-a'), str(temp / 'client-b')],
            'protect': {
                'paths': [ENGINE_IMAGE, REPOSITORY],
                'volumes': ['atlas_pg_*'],
                'containers': ['atlas-*'],
                'images': ['atlas-*', 'store/objects', 'store/client'],
                'networks': ['atlas_*'],
                'compose_projects': ['atlas', 'ledgerdb'],
            },
        }
        ENTRIES = dict(zip(ENTRY_ROWS, (
            ('path', ENGINE_IMAGE), ('path', REPOSITORY), ('volume', 'atlas_pg_*'),
            ('container', 'atlas-*'), ('image', 'atlas-*'), ('network', 'atlas_*'),
            ('compose_project', 'atlas'), ('compose_project', 'ledgerdb'), ('image', 'store/objects'),
            ('image', 'store/client'))))
        BASE = {'schema': 'veldo.installation/v1', 'owner': {'display_name': 'Fixture Owner', 'role_id': 'owner'}}

        counter = [0]

        def on_disk(section='absent', raw=None):
            """Read a fixture installation folder from disk: (config, refusal code, log text)."""
            counter[0] += 1
            folder = temp / ('installation-%d' % counter[0])
            folder.mkdir()
            settings = dict(BASE)
            if section != 'absent':
                settings['space'] = section
            text = YAML.dump(settings) if raw is None else raw
            (folder / 'installation.yaml').write_text(text)
            return read(environ={'VELDO_INSTALLATION': str(folder), 'HOME': str(temp / 'home')})

        class Given:
            """An installation that answers a section directly: the unit rows."""

            def __init__(self, section):
                self.section = section

            def space(self):
                return self.section

        def read(**kwargs):
            log = io.StringIO()
            try:
                return CFG.read(stream=log, **kwargs), None, log.getvalue()
            except Exception as error:  # the refusal code, or the failure, is the observation
                return None, getattr(error, 'code', type(error).__name__ + ': ' + str(error)), log.getvalue()

        def given(section):
            return read(installation=Given(section))

        def without(path):
            section = copy.deepcopy(SECTION)
            at = section
            for part in path[:-1]:
                at = at[part]
            del at[path[-1]]
            return section

        def changed(path, value):
            section = copy.deepcopy(SECTION)
            at = section
            for part in path[:-1]:
                at = at[part]
            at[path[-1]] = value
            return section

        def dotted(path):
            out = 'space'
            for part in path:
                out += '[%d]' % part if isinstance(part, int) else '.' + part
            return out

        # ---- AC1: no section is space management off, and is not refused --------------------------------
        config, code, log = on_disk()
        check('ac1/no-section', 'a fixture installation with no space section is not refused [%s]' % code,
              code is None)
        check('ac1/no-section', 'and reads as space management off [%s]' % config,
              config == {'present': False, 'enabled': False})
        check('ac1/no-section', 'and no refusal line is logged [%s]' % log, 'refused' not in log)
        config, code, log = given(None)
        check('ac1/no-section', 'the reader given no section answers off [%s %s]' % (config, code),
              code is None and config == {'present': False, 'enabled': False})
        config, code, log = read(environ={'VELDO_INSTALLATION': str(temp / 'nowhere'), 'HOME': str(temp / 'home')})
        check('ac1/no-installation', 'no installation folder at all reads as off, not refused [%s %s]'
              % (config, code), code is None and config == {'present': False, 'enabled': False})
        check('ac1/no-installation', 'and the installation reader said none was found [%s]' % log.strip(),
              'none found' in log)

        # ---- the whole section, from disk ----------------------------------------------------------------
        config, code, log = on_disk(SECTION)
        check('reader/full-section', 'the fixture section is accepted from disk [%s]' % code, code is None)
        full = config or {}
        check('reader/full-section', 'enabled and the time zone [%s %s]' % (full.get('enabled'), full.get('time_zone')),
              full.get('enabled') is True and full.get('time_zone') == 'Europe/Lisbon' and full.get('present') is True)
        check('reader/full-section', 'pools with floor and the need per station [%s]' % full.get('pools'),
              full.get('pools') == SECTION['pools'])
        check('reader/full-section', 'engines [%s]' % full.get('engines'), full.get('engines') == ENGINES)
        check('reader/full-section', 'scratch roots and the session pattern',
              full.get('scratch_roots') == SECTION['scratch_roots'])
        check('reader/full-section', 'build roots, plain repositories and client accounts',
              full.get('build_roots') == SECTION['build_roots']
              and full.get('plain_repositories') == SECTION['plain_repositories']
              and full.get('client_accounts') == SECTION['client_accounts'])
        config, code, log = on_disk(changed(['enabled'], 'false'))
        check('reader/full-section', 'enabled false is read as off with the section still checked [%s %s]'
              % (code, (config or {}).get('enabled')), code is None and config['enabled'] is False
              and config['present'] is True and len(config['protect']) == 10)
        config, code, log = given(changed(['build_roots'], ['~/build']))
        check('reader/full-section', 'a path under the home folder is written with a tilde and read expanded [%s %s]'
              % (code, (config or {}).get('build_roots')),
              code is None and config['build_roots'][0].endswith('/build') and '~' not in config['build_roots'][0])

        # ---- AC2: a missing key by name ------------------------------------------------------------------
        for key in CFG.KEYS:
            config, code, log = given(without([key]))
            check('ac2/missing-by-name', 'the section without %s is refused by that name [%s]' % (key, code),
                  code == 'installation_missing:space.' + key)
        check('ac2/missing-by-name', 'the nine keys are the ones the design names [%s]' % (CFG.KEYS,),
              sorted(CFG.KEYS) == sorted(SECTION))
        for path in (['pools', 'host', 'needs'], ['pools', 'desktop', 'needs', 'gate'],
                     ['scratch_roots', 'session_pattern'], ['scratch_roots', 'roots'], ['protect', 'networks'],
                     ['protect', 'compose_projects'], ['plain_repositories', 0, 'worktree_root']):
            config, code, log = given(without(path))
            check('ac2/missing-by-name', 'without %s: refused by that name [%s]' % (dotted(path), code),
                  code == 'installation_missing:' + dotted(path))
        config, code, log = on_disk(raw=YAML.dump(BASE) + 'space:\n')
        check('ac2/missing-by-name', 'a section written with nothing under it is present and refused [%s]' % code,
              code == 'installation_missing:space.enabled')
        config, code, log = on_disk(without(['time_zone']))
        check('ac2/missing-by-name', 'from disk, the section without time_zone is refused by that name [%s]' % code,
              code == 'installation_missing:space.time_zone')

        config, code, log = on_disk(without(['pools', 'host', 'floor']))
        check('ac2/missing-floor', 'from disk, a pool with the floor key left out is refused by its name [%s]' % code,
              code == 'installation_missing:space.pools.host.floor')
        config, code, log = given(without(['pools', 'desktop', 'floor']))
        check('ac2/missing-floor', 'a given section with the floor left out is refused, never given a value [%s %s]'
              % (code, ((config or {}).get('pools') or {}).get('desktop')),
              code == 'installation_missing:space.pools.desktop.floor')

        # ---- AC2: a malformed key by name ----------------------------------------------------------------
        MALFORMED = (
            (['enabled'], 'yes'), (['enabled'], 1), (['time_zone'], 'Nowhere/Never'), (['time_zone'], 7),
            (['pools'], ['host']), (['pools', 'host'], 'large'), (['pools', 'host', 'floor'], -1),
            (['pools', 'host', 'floor'], '20GB'), (['pools', 'host', 'needs'], 4000),
            (['pools', 'host', 'needs', 'build'], 'much'), (['engines'], 'default'), (['engines'], []),
            (['engines'], ['default', 'default']), (['engines'], ['default', '']),
            (['scratch_roots'], [str(temp)]), (['scratch_roots', 'roots'], ['relative/scratch']),
            (['scratch_roots', 'session_pattern'], 'sessions/{other}/{session_id}'),
            (['scratch_roots', 'session_pattern'], 'sessions/{working_folder}'),
            (['build_roots'], str(temp)), (['build_roots'], ['build']),
            (['plain_repositories'], {'repository': str(temp)}), (['plain_repositories', 0], str(temp)),
            (['plain_repositories', 0, 'repository'], 'plain'), (['client_accounts'], [7]),
            (['protect'], ['atlas']), (['protect', 'paths'], ['projects/atlas']),
            (['protect', 'volumes'], 'atlas_pg_*'), (['protect', 'images'], ['store/objects', None]),
            (['protect', 'compose_projects'], [' atlas']),
        )
        for path, value in MALFORMED:
            config, code, log = given(changed(path, value))
            name = dotted(path)
            check('ac2/malformed-by-name', '%s malformed (%s): refused by that name [%s]'
                  % (name, type(value).__name__, code),
                  isinstance(code, str) and code.startswith('installation_invalid:' + name)
                  and code[len('installation_invalid:' + name):][:1] in ('', '['))
        config, code, log = on_disk(changed(['pools', 'host', 'floor'], '20GB'))
        check('ac2/malformed-by-name', 'from disk, a floor that is not a number is refused by its name [%s]' % code,
              code == 'installation_invalid:space.pools.host.floor')
        for path in (['colour'], ['pools', 'host', 'ceiling'], ['protect', 'files'], ['scratch_roots', 'depth'],
                     ['pools', 'host', 'needs', 'deploy']):
            config, code, log = given(changed(path, 'value'))
            check('ac2/malformed-by-name', 'an unknown key %s is refused by its name [%s]' % (dotted(path), code),
                  code == 'installation_invalid:' + dotted(path))
        config, code, log = on_disk(raw=YAML.dump(BASE) + 'space: on\n')
        check('ac2/malformed-by-name', 'a section that is not a mapping is refused by its name [%s]' % code,
              code == 'installation_invalid:space')
        check('ac2/logged', 'a section that is not a mapping is logged with the section line [%s]'
              % log.strip().splitlines()[-1:],
              log.strip().splitlines()[-1:] == ['veldo space section: refused space (malformed)']
              and log.count('veldo space section:') == 1)

        # ---- AC2: the log line ---------------------------------------------------------------------------
        config, code, log = given(without(['pools', 'host', 'floor']))
        check('ac2/logged', 'a missing key is logged with its name and the reason [%s]' % log.strip(),
              log.strip() == 'veldo space section: refused space.pools.host.floor (missing)')
        secret_value = 'Nowhere/Loud-Value-41'
        config, code, log = given(changed(['time_zone'], secret_value))
        check('ac2/logged', 'a malformed key is logged with its name and the reason, never its value [%s]'
              % log.strip(), log.strip() == 'veldo space section: refused space.time_zone (malformed)'
              and secret_value not in log)
        config, code, log = given(changed(['colour'], secret_value))
        check('ac2/logged', 'an unknown key is logged with its name and the reason, never its value [%s]'
              % log.strip(), log.strip() == 'veldo space section: refused space.colour (unknown)'
              and secret_value not in log)
        config, code, log = given(SECTION)
        check('ac2/logged', 'an accepted section logs no refusal [%s]' % log, log == '')

        # ---- AC3: the protect list, read back from disk, on both engine contexts ----------------------------
        config, code, log = on_disk(SECTION)
        config = config or {}
        per_engine = {engine: CFG.protect_for(config, engine) for engine in ENGINES}
        for row, (kind, value) in ENTRIES.items():
            for engine in ENGINES:
                check(row, '%s %s is returned for the context %s' % (kind, value, engine),
                      {'type': kind, 'value': value} in per_engine[engine])
            check(row, 'and the entry itself names both contexts',
                  {'type': kind, 'value': value, 'engines': ENGINES} in config.get('protect', []))
        wanted = sorted(ENTRIES.values())
        for engine in ENGINES:
            got = sorted((entry['type'], entry['value']) for entry in per_engine[engine])
            check('ac3/whole-list', 'the context %s gets the ten entries and nothing else [%d]' % (engine, len(got)),
                  got == wanted)
        check('ac3/whole-list', 'a context the installation does not name gets none',
              CFG.protect_for(config, 'elsewhere') == [])
        check('ac3/whole-list', 'no entry of the accepted section is without an engine',
              bool(config.get('protect')) and all(entry['engines'] for entry in config['protect']))

        # An engines list naming none would leave every entry, host paths included, in force nowhere.
        empty_config, code, log = given(changed(['engines'], []))
        check('ac3/empty-engines', 'a given section with engines naming none is refused by name [%s]' % code,
              empty_config is None and code == 'installation_invalid:space.engines')
        check('ac3/empty-engines', 'and logged as malformed [%s]' % log.strip(),
              log.strip() == 'veldo space section: refused space.engines (malformed)')
        empty_config, code, log = on_disk(changed(['engines'], []))
        check('ac3/empty-engines', 'from disk, engines naming none is refused, with no protect list returned [%s %s]'
              % (code, (empty_config or {}).get('protect')),
              empty_config is None and code == 'installation_invalid:space.engines')

        # ---- AC4: mode is not a key ----------------------------------------------------------------------
        check('ac4/no-mode-key', 'the reader has no mode key [%s]' % (CFG.KEYS,), 'mode' not in CFG.KEYS)
        check('ac4/no-mode-key', 'and the section read back carries no mode [%s]' % sorted(config),
              bool(config) and 'mode' not in config)
        mode_config, code, log = on_disk(changed(['mode'], 'act'))
        check('ac4/mode-refused', 'from disk, mode: act in the section is refused as unknown by name [%s]' % code,
              mode_config is None and code == 'installation_invalid:space.mode')
        check('ac4/mode-refused', 'and logged as unknown without its value [%s]' % log.strip().splitlines()[-1:],
              log.strip().splitlines()[-1:] == ['veldo space section: refused space.mode (unknown)'])
        for value in ('act', 'report'):
            mode_config, code, log = given(changed(['mode'], value))
            check('ac4/mode-refused', 'a given section with mode: %s is refused, never accepted and ignored [%s]'
                  % (value, code), mode_config is None and code == 'installation_invalid:space.mode')

        # ---- the reader opens nothing itself -------------------------------------------------------------
        source = (ROOT / '.veldo' / 'control_space_config.py').read_text()
        check('reader/one-opener', 'the declarations reader goes through the installation reader',
              "with_name('installation.py')" in source and 'installation.space()' in source
              and 'yamlish' not in source and 'open(' not in source and 'read_text' not in source)
        for name in ('control_space_config.py', 'installation.py'):
            canon = ROOT / 'engine' / '.veldo' / name
            check('reader/one-opener', 'the engine canon of %s equals this repository copy' % name,
                  canon.is_file() and canon.read_bytes() == (ROOT / '.veldo' / name).read_bytes())
    except Exception as error:
        import traceback
        check('ac1/no-section', 'raised ' + type(error).__name__ + ': ' + str(error)[:300]
              + ' ' + traceback.format_exc().splitlines()[-3][:200], False)
    finally:
        shutil.rmtree(temp, ignore_errors=True)

    for row, values in rows.items():
        failed = [label for label, ok in values if not ok]
        expect('VELDO-0296 ' + row + (': ' + failed[0] if failed else ''), bool(values) and not failed)


_v296_space_section_suite()
