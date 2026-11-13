"""VELDO-0338: the declarations reader for a project's space file (.veldo/space.yaml).

Run: python3 scripts/selftest.py --suite 131_veldo_0338_project_space_file

Only shared ROOT and expect are consumed. Every project here is a FIXTURE repository folder written into a
temporary folder with invented values; the installation is a fixture folder too, read through the one
installation reader with an environment of its own. No real project file and no real installation is read.
The integration rows read .veldo/space.yaml and installation.yaml from disk; the unit rows give the reader
a parsed file directly.

AC1 rows: ac1/no-file (a fixture project with no space file is not refused and says the file was absent),
ac1/every-default (each of the nine defaults of 6.8, one check per key), ac1/default-per-key (a file that
gives one key gets the default for every other; an empty file and a key with nothing under it too).

AC2 rows: ac2/unknown-by-name (an unknown key at the top, under protect and under needs, refused as
space_file_invalid:<key>), ac2/misspelled-keep (a file that spells keep wrongly is refused by that name
and no declarations come back, so nothing can read it as a project that keeps nothing; the same file
spelled right keeps the folder), ac2/logged (one line with the project, the key and the reason, never a
value), ac2/malformed-by-name (a malformed value refused by its key's name; an unparseable file refused).

AC3 rows: ac3/adds (each project entry is added, on every engine the installation names),
ac3/installation-volume-kept (a project that lists its own volumes: the installation's protected volume
pattern is still in the result, on both engine contexts), ac3/every-installation-entry-kept (all six of
the installation's entries, whatever the project lists), ac3/cannot-remove (no key removes an entry; an
empty list and a repeated entry change nothing).

reader/full-file: a file with every key read back from disk; reader/canon: the engine canon equals this
repository copy, and the reader is given its document reader.
"""


def _v338_project_space_file_suite():
    import importlib.util
    import io
    import os
    import shutil
    import tempfile
    from pathlib import Path

    # Literal anchors: the registered mutation driver substitutes the production copy here.
    PRODUCTION = {
        'control_space_config.py': ROOT / ".veldo" / "control_space_config.py",
    }
    ROWS = ('ac1/no-file', 'ac1/every-default', 'ac1/default-per-key', 'ac2/unknown-by-name',
            'ac2/misspelled-keep', 'ac2/logged', 'ac2/malformed-by-name', 'ac3/adds',
            'ac3/installation-volume-kept', 'ac3/every-installation-entry-kept', 'ac3/cannot-remove',
            'reader/full-file', 'reader/canon')
    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    temp = Path(tempfile.mkdtemp(prefix='v338-'))
    try:
        CFG = load('v338_control_space_config', PRODUCTION['control_space_config.py'])
        YAML = load('v338_yamlish', PRODUCTION['control_space_config.py'].with_name('yamlish.py'))

        ENGINES = ['default', 'desktop-linux']
        MEGABYTE = 1024 * 1024
        INSTALLED_PATH = str(temp / 'engine' / 'vms' / '0' / 'data')
        SECTION = {
            'enabled': 'true',
            'time_zone': 'Europe/Lisbon',
            'pools': {'host': {'floor': 20000 * MEGABYTE,
                               'needs': {'build': 4000 * MEGABYTE, 'review': 1000 * MEGABYTE,
                                         'gate': 6000 * MEGABYTE}}},
            'engines': list(ENGINES),
            'scratch_roots': {'roots': [str(temp / 'scratch')],
                              'session_pattern': 'sessions/{working_folder}/{session_id}'},
            'build_roots': [str(temp / 'build')],
            'plain_repositories': [],
            'client_accounts': [str(temp / 'client-a')],
            'protect': {
                'paths': [INSTALLED_PATH],
                'volumes': ['atlas_pg_*'],
                'containers': ['atlas-*'],
                'images': ['store/objects'],
                'networks': ['atlas_*'],
                'compose_projects': ['ledgerdb'],
            },
        }
        INSTALLED = [('path', INSTALLED_PATH), ('volume', 'atlas_pg_*'), ('container', 'atlas-*'),
                     ('image', 'store/objects'), ('network', 'atlas_*'), ('compose_project', 'ledgerdb')]

        # The installation: a fixture folder on disk, read through the one installation reader.
        folder = temp / 'installation'
        folder.mkdir()
        (folder / 'installation.yaml').write_text(YAML.dump({
            'schema': 'veldo.installation/v1',
            'owner': {'display_name': 'Fixture Owner', 'role_id': 'owner'},
            'space': SECTION}))
        CONFIG = CFG.read(environ={'VELDO_INSTALLATION': str(folder), 'HOME': str(temp / 'home')},
                          stream=io.StringIO())

        counter = [0]

        def project(text=None, name='orchard'):
            """A fixture repository folder, with .veldo/space.yaml holding `text` when given."""
            counter[0] += 1
            root = temp / ('projects-%d' % counter[0]) / name
            (root / '.veldo').mkdir(parents=True)
            if text is not None:
                (root / '.veldo' / 'space.yaml').write_text(text)
            return root

        def read(root, config=CONFIG, **kwargs):
            """(declarations, refusal code, log text) for one fixture project, from disk."""
            log = io.StringIO()
            try:
                return CFG.read_project(str(root), YAML.read, config=config, stream=log, **kwargs), None, log.getvalue()
            except Exception as error:  # the refusal code, or the failure, is the observation
                return None, getattr(error, 'code', type(error).__name__ + ': ' + str(error)), log.getvalue()

        def on_disk(document, **kwargs):
            return read(project(YAML.dump(document)), **kwargs)

        def entries(config):
            return [(entry['type'], entry['value']) for entry in (config or {}).get('protect', ())]

        # ---- AC1: no file, every default, not refused --------------------------------------------------
        root = project()
        config, code, log = read(root)
        check('ac1/no-file', 'a fixture project with no space file is not refused [%s]' % code, code is None)
        check('ac1/no-file', 'and the answer says the file was absent [%s]' % (config or {}).get('present'),
              config is not None and config.get('present') is False)
        check('ac1/no-file', 'and no refusal line is logged [%s]' % log, log == '')
        bare = temp / 'projects-bare' / 'orchard'
        bare.mkdir(parents=True)
        bare_config, code, log = read(bare)
        check('ac1/no-file', 'a repository with no .veldo folder at all reads the same [%s]' % code,
              code is None and bare_config is not None and bare_config.get('present') is False)
        config = config or {}
        DEFAULTS = {
            'worktree_root': str(root.parent / 'orchard-worktrees'),
            'branch_pattern': ['agent/{agent}/{ticket}'],
            'landing_refs': [],
            'build_output': [],
            'build_variables': [],
            'keep': [],
            'evidence_caches': [],
            'needs': {'build': {}, 'review': {}, 'gate': {}},
            'protect': [{'type': kind, 'value': value, 'engines': ENGINES} for kind, value in INSTALLED],
        }
        for key in CFG.PROJECT_KEYS:
            check('ac1/every-default', 'the default of %s [%s]' % (key, config.get(key)),
                  key in DEFAULTS and config.get(key) == DEFAULTS[key])
        check('ac1/every-default', 'the nine keys are the nine of 6.8 [%s]' % (CFG.PROJECT_KEYS,),
              sorted(CFG.PROJECT_KEYS) == sorted(DEFAULTS))
        check('ac1/every-default', 'the project is named after its repository folder [%s]' % config.get('project'),
              config.get('project') == 'orchard')
        off_config, code, log = read(project(), config=CFG.off())
        check('ac1/every-default', 'with space management off the project still gets its defaults [%s]' % code,
              code is None and off_config is not None and off_config['protect'] == []
              and off_config['keep'] == [] and off_config['branch_pattern'] == ['agent/{agent}/{ticket}'])

        GIVEN = {
            'worktree_root': '../orchard-trees',
            'branch_pattern': ['work/{ticket}', 'agent/{agent}/{ticket}'],
            'landing_refs': ['refs/heads/release', 'refs/heads/staging'],
            'build_output': ['target', '.cache-*'],
            'build_variables': ['CARGO_TARGET_DIR', 'ORCHARD_BUILD_DIR'],
            'keep': ['data/models', 'vendor/licensed'],
            'evidence_caches': ['cache', 'downloads/tmp'],
            'needs': {'build': {'host': 3000 * MEGABYTE}, 'gate': {'host': 5000 * MEGABYTE, 'desktop': 0}},
            'protect': {'paths': ['fixtures/golden'], 'volumes': ['orchard_db_*'],
                        'compose_projects': ['orchard']},
        }
        for key in CFG.PROJECT_KEYS:
            one, code, log = on_disk({key: GIVEN[key]})
            one = one or {}
            others = [other for other in CFG.PROJECT_KEYS if other != key and one.get(other) != (
                DEFAULTS[other] if other != 'worktree_root' else one.get('worktree_root'))]
            check('ac1/default-per-key', 'a file with only %s is accepted, every other key at its default [%s %s]'
                  % (key, code, others), code is None and not others and one.get('present') is True
                  and one.get(key) != DEFAULTS[key])
        one, code, log = on_disk({'keep': ['data/models']})
        check('ac1/default-per-key', 'the worktree root of a file that names only keep is the default one [%s]'
              % (one or {}).get('worktree_root'),
              one is not None and os.path.basename(one['worktree_root']) == 'orchard-worktrees')
        empty, code, log = read(project(''))
        check('ac1/default-per-key', 'an empty file is present and gives every default [%s]' % code,
              code is None and empty is not None and empty['present'] is True
              and all(empty[key] == DEFAULTS[key] for key in CFG.PROJECT_KEYS if key != 'worktree_root'))
        blank, code, log = read(project('keep:\nneeds:\nprotect:\n# worktree_root: ../elsewhere\n'))
        check('ac1/default-per-key', 'a key with nothing under it, and a commented one, get their defaults [%s]' % code,
              code is None and blank is not None and blank['keep'] == [] and blank['needs'] == DEFAULTS['needs']
              and blank['protect'] == DEFAULTS['protect']
              and os.path.basename(blank['worktree_root']) == 'orchard-worktrees')

        # ---- the whole file, from disk -----------------------------------------------------------------
        root = project(YAML.dump(GIVEN))
        full, code, log = read(root)
        check('reader/full-file', 'a file with every key is accepted from disk [%s]' % code, code is None)
        full = full or {}
        check('reader/full-file', 'the worktree root is resolved against the repository [%s]' % full.get('worktree_root'),
              full.get('worktree_root') == str(root.parent / 'orchard-trees'))
        for key in ('branch_pattern', 'landing_refs', 'build_output', 'build_variables', 'keep', 'evidence_caches'):
            check('reader/full-file', '%s as written [%s]' % (key, full.get(key)), full.get(key) == GIVEN[key])
        check('reader/full-file', 'needs per station, bytes per pool, a station left out empty [%s]' % full.get('needs'),
              full.get('needs') == {'build': {'host': 3000 * MEGABYTE}, 'review': {},
                                    'gate': {'host': 5000 * MEGABYTE, 'desktop': 0}})
        named, code, log = read(project(YAML.dump(GIVEN)), project='orchard-main')
        check('reader/full-file', 'the caller may name the project [%s]' % (named or {}).get('project'),
              named is not None and named['project'] == 'orchard-main')
        absolute, code, log = on_disk({'worktree_root': str(temp / 'trees'), 'protect': {'paths': ['~/golden']}})
        check('reader/full-file', 'an absolute path and one under the home folder are read too [%s %s]'
              % (code, (absolute or {}).get('worktree_root')),
              code is None and absolute['worktree_root'] == str(temp / 'trees')
              and absolute['protect'][-1]['value'].endswith('/golden') and '~' not in absolute['protect'][-1]['value'])

        # ---- AC2: an unknown key is refused by name ----------------------------------------------------
        for key in ('colour', 'mode', 'enabled', 'worktree-root', 'keeps'):
            config, code, log = on_disk(dict(GIVEN, **{key: 'value'}))
            check('ac2/unknown-by-name', 'a file with the unknown key %s is refused by that name [%s]' % (key, code),
                  config is None and code == 'space_file_invalid:' + key)
        config, code, log = on_disk({'protect': {'volumes': ['orchard_db_*'], 'files': ['notes']}})
        check('ac2/unknown-by-name', 'an unknown key under protect is refused by its name [%s]' % code,
              config is None and code == 'space_file_invalid:protect.files')
        config, code, log = on_disk({'needs': {'deploy': {'host': 1}}})
        check('ac2/unknown-by-name', 'an unknown station under needs is refused by its name [%s]' % code,
              config is None and code == 'space_file_invalid:needs.deploy')
        try:
            CFG.check_project({'colour': 'green'}, str(root), CONFIG)
            unit = 'accepted'
        except Exception as error:
            unit = getattr(error, 'reason', '') + ':' + getattr(error, 'key', type(error).__name__)
        check('ac2/unknown-by-name', 'a parsed file given directly is refused the same way [%s]' % unit,
              unit == 'unknown:colour')

        # ---- AC2: the misspelled keep key --------------------------------------------------------------
        misspelled = project('kep:\n  - data/models\n')
        config, code, log = read(misspelled)
        check('ac2/misspelled-keep', 'a file that spells keep as kep is refused by that name [%s]' % code,
              code == 'space_file_invalid:kep')
        check('ac2/misspelled-keep', 'no declarations come back, so nothing reads the folder as not kept [%s]'
              % ('keep %s' % config.get('keep') if config else 'none'), config is None)
        check('ac2/misspelled-keep', 'the refusal names the project and the key [%s]' % log.strip(),
              log.strip() == 'veldo space file: project orchard refused kep (unknown)')
        config, code, log = read(project('keep:\n  - data/models\n'))
        check('ac2/misspelled-keep', 'the same file spelled right keeps the folder [%s %s]'
              % (code, (config or {}).get('keep')), code is None and config['keep'] == ['data/models'])
        config, code, log = on_disk(dict(GIVEN, kep=['data/other']))
        check('ac2/misspelled-keep', 'a misspelling beside a right keep key is refused too [%s]' % code,
              config is None and code == 'space_file_invalid:kep')

        # ---- AC2: the log line -------------------------------------------------------------------------
        loud = 'Loud-Value-41'
        config, code, log = on_disk({'colour': loud}, project='orchard-main')
        check('ac2/logged', 'an unknown key is logged with the project, the key and the reason, never its value [%s]'
              % log.strip(), log.strip() == 'veldo space file: project orchard-main refused colour (unknown)'
              and loud not in log)
        config, code, log = on_disk({'keep': ['/' + loud]})
        check('ac2/logged', 'a malformed key is logged the same way [%s]' % log.strip(),
              log.strip() == 'veldo space file: project orchard refused keep[0] (malformed)' and loud not in log)
        config, code, log = read(project('keep: [' + loud + '\n'))
        check('ac2/logged', 'an unparseable file is logged as unreadable, without its content [%s]' % log.strip(),
              log.strip() == 'veldo space file: project orchard refused .veldo/space.yaml (unreadable)'
              and loud not in log)
        config, code, log = on_disk(GIVEN)
        check('ac2/logged', 'an accepted file logs nothing [%s]' % log, log == '')

        # ---- a malformed value by name -----------------------------------------------------------------
        MALFORMED = (
            ('worktree_root', ['a']), ('worktree_root', '~other/trees'), ('branch_pattern', 'agent/{ticket}'),
            ('branch_pattern', ['agent/{agent}']), ('branch_pattern', ['work/{unit}/{ticket}']),
            ('branch_pattern', ['{ticket}/{ticket}']), ('landing_refs', 'refs/heads/release'),
            ('landing_refs', ['release', 'release']), ('build_output', [7]), ('build_variables', ['2FAST']),
            ('build_variables', ['WITH SPACE']), ('keep', 'data/models'), ('keep', ['/data/models']),
            ('keep', ['../outside']), ('keep', ['a/../..']), ('keep', ['.']), ('keep', ['~/models']),
            ('evidence_caches', ['../cache']), ('evidence_caches', [None]), ('needs', ['build']),
            ('needs', {'build': 4000}), ('needs', {'build': {'host': -1}}), ('needs', {'gate': {'host': '5GB'}}),
            ('protect', ['orchard_db_*']), ('protect', {'volumes': 'orchard_db_*'}),
            ('protect', {'images': ['store/a', '']}), ('protect', {'paths': [7]}),
        )
        for key, value in MALFORMED:
            config, code, log = on_disk({key: value})
            check('ac2/malformed-by-name', '%s malformed (%r): refused by that name [%s]' % (key, value, code),
                  config is None and isinstance(code, str) and code.startswith('space_file_invalid:' + key)
                  and code[len('space_file_invalid:' + key):][:1] in ('', '[', '.'))
        config, code, log = read(project('- keep\n- protect\n'))
        check('ac2/malformed-by-name', 'a file that is a list is refused by the file name [%s]' % code,
              config is None and code == 'space_file_invalid:.veldo/space.yaml')
        config, code, log = read(project('keep: [data\n'))
        check('ac2/malformed-by-name', 'a file that does not parse is refused as unreadable [%s]' % code,
              config is None and code == 'space_file_unreadable')
        folder_root = project()
        (folder_root / '.veldo' / 'space.yaml').mkdir()
        config, code, log = read(folder_root)
        check('ac2/malformed-by-name', 'a folder where the file should be is refused, not read as absent [%s]' % code,
              config is None and code == 'space_file_unreadable')

        # ---- AC3: a project's protect entries add to the installation's --------------------------------
        root = project(YAML.dump({'protect': GIVEN['protect']}))
        config, code, log = read(root)
        ADDED = [('path', str(root / 'fixtures' / 'golden')), ('volume', 'orchard_db_*'),
                 ('compose_project', 'orchard')]
        got = entries(config)
        for kind, value in ADDED:
            check('ac3/adds', 'the project entry %s %s is in the result [%s]' % (kind, os.path.basename(value), code),
                  (kind, value) in got)
            check('ac3/adds', 'and it applies on every engine the installation names',
                  {'type': kind, 'value': value, 'engines': ENGINES} in (config or {}).get('protect', ()))
        check('ac3/adds', 'the result is the six installation entries then the three additions [%d]' % len(got),
              got == INSTALLED + ADDED)
        for engine in ENGINES:
            check('ac3/adds', 'the context %s gets all nine' % engine,
                  sorted((entry['type'], entry['value']) for entry in CFG.protect_for(config or {}, engine))
                  == sorted(INSTALLED + ADDED))

        check('ac3/installation-volume-kept',
              'a project that lists its own volumes still has the installation volume pattern atlas_pg_* [%s]'
              % [value for kind, value in got if kind == 'volume'],
              ('volume', 'atlas_pg_*') in got and ('volume', 'orchard_db_*') in got)
        for engine in ENGINES:
            check('ac3/installation-volume-kept', 'and it is in force on the context %s' % engine,
                  {'type': 'volume', 'value': 'atlas_pg_*'} in CFG.protect_for(config or {}, engine))
        only, code, log = on_disk({'protect': {'volumes': ['orchard_db_*']}})
        check('ac3/installation-volume-kept', 'the same when volumes is the only key the project gives [%s]' % code,
              ('volume', 'atlas_pg_*') in entries(only))

        for label, document in (('all six keys', {'protect': {
                'paths': ['fixtures/golden'], 'volumes': ['orchard_db_*'], 'containers': ['orchard-*'],
                'images': ['orchard/app'], 'networks': ['orchard_*'], 'compose_projects': ['orchard']}}),
                                ('one key', {'protect': {'networks': ['orchard_*']}}),
                                ('no protect key', {'keep': ['data/models']})):
            config, code, log = on_disk(document)
            got = entries(config)
            check('ac3/every-installation-entry-kept', 'a project giving %s: all six installation entries stay [%s]'
                  % (label, code), all(entry in got for entry in INSTALLED) and got[:6] == INSTALLED)

        for key in ('remove', 'unprotect', 'except'):
            config, code, log = on_disk({'protect': {key: ['atlas_pg_*']}})
            check('ac3/cannot-remove', 'protect.%s is not a key: refused, nothing removed [%s]' % (key, code),
                  config is None and code == 'space_file_invalid:protect.' + key)
        config, code, log = on_disk({'protect': {'volumes': [], 'paths': [], 'containers': [], 'images': [],
                                                 'networks': [], 'compose_projects': []}})
        check('ac3/cannot-remove', 'six empty lists leave the installation list whole [%s]' % code,
              entries(config) == INSTALLED)
        config, code, log = on_disk({'protect': {'volumes': ['atlas_pg_*', 'orchard_db_*']}})
        check('ac3/cannot-remove', 'an installation entry repeated by the project is there once [%s]' % code,
              entries(config) == INSTALLED + [('volume', 'orchard_db_*')])
        before = [dict(entry, engines=list(entry['engines'])) for entry in CONFIG['protect']]
        on_disk({'protect': GIVEN['protect']})
        check('ac3/cannot-remove', 'reading a project leaves the installation config it was given unchanged',
              CONFIG['protect'] == before)

        # ---- the canon, and the document reader --------------------------------------------------------
        source = (ROOT / '.veldo' / 'control_space_config.py').read_text()
        canon = ROOT / 'engine' / '.veldo' / 'control_space_config.py'
        check('reader/canon', 'the engine canon equals this repository copy',
              canon.is_file() and canon.read_bytes() == (ROOT / '.veldo' / 'control_space_config.py').read_bytes())
        check('reader/canon', 'the reader is given its document reader and names the project file',
              'document = load(path)' in source and "PROJECT_FILE = '.veldo/space.yaml'" in source)
    except Exception as error:
        import traceback
        check('ac1/no-file', 'raised ' + type(error).__name__ + ': ' + str(error)[:300]
              + ' ' + traceback.format_exc().splitlines()[-3][:200], False)
    finally:
        shutil.rmtree(temp, ignore_errors=True)

    for row, values in rows.items():
        failed = [label for label, ok in values if not ok]
        expect('VELDO-0338 ' + row + (': ' + failed[0] if failed else ''), bool(values) and not failed)


_v338_project_space_file_suite()
