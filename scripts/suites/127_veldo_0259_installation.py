"""VELDO-0259: one installation folder read through one reader, and a gate stage that refuses a candidate
adding personal setup.

Run: python3 scripts/selftest.py --suite 127_veldo_0259_installation

Only shared ROOT and expect are consumed. Every installation here is a FIXTURE built in a temporary folder
with invented values; no real installation is read (each row sets VELDO_INSTALLATION, XDG_CONFIG_HOME and
HOME to temporary folders). Every personal-looking value is assembled at run time from pieces, so this file
adds no line the check itself would refuse.

AC1 rows: ac1/resolution (the fixed order VELDO_INSTALLATION, then $XDG_CONFIG_HOME/veldo/installation,
then ~/.config/veldo/installation, and the one resolution line naming the folder and how, or that none was
found); ac1/kinds (installation.yaml keys, overrides of connectors, services and workflows by id, patterns/,
decisions/ and records/); ac1/missing-by-name (an empty folder refuses installation_missing:<key>, never a
built-in person); ac1/invalid-by-name (installation_invalid:<key>, a literal secret in a channel refused);
ac1/revision (the commit id of a git installation); ac1/one-reader (no other product module names the
folder); ac1/traces (factory setup's answer and the API record name the folder and revision, and with an
empty installation carry no value of the fixture); ac1/no-personal-default (the built-in shapes find nothing
in the reader, the check and the consumers); ac1/fresh-clone (a fresh clone of the candidate with no
installation passes the new stage and says it ran the built-in shapes only).

AC2 rows: ac2/planted (one value per installation category and one per built-in shape, added by a candidate,
is refused as personal_setup:<category> with file, line and a masked match); ac2/masked (no planted value
appears unmasked in any output); ac2/added-only (gate mode judges only the lines a candidate adds; sweep mode
judges the whole tree); ac2/no-installation (the built-in-only line, and a clean candidate passes);
ac2/publish-shares (scripts/publish.py refuses a produced tree through the same code); ac2/stage-declared
(scripts/verify.sh declares the stage, and scripts/gate_graph.json carries exactly the node the scheduler
requires for it); ac2/product-clean (no pattern of the fixture installation is in a tracked file).
"""


def _v259_installation_suite():
    import contextlib
    import importlib.util
    import io
    import json
    import os
    from pathlib import Path
    import re
    import shutil
    import subprocess
    import tempfile

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'installation.py': ROOT / ".veldo" / "installation.py",
        'check_personal_setup.py': ROOT / "scripts" / "check_personal_setup.py",
        'control_service.py': ROOT / ".veldo" / "control_service.py",
        'control_factory_setup.py': ROOT / ".veldo" / "control_factory_setup.py",
    }
    ROWS = ('ac1/resolution', 'ac1/kinds', 'ac1/missing-by-name', 'ac1/invalid-by-name', 'ac1/revision',
            'ac1/one-reader', 'ac1/traces', 'ac1/no-personal-default', 'ac1/fresh-clone',
            'ac2/planted', 'ac2/masked', 'ac2/added-only', 'ac2/no-installation', 'ac2/publish-shares',
            'ac2/stage-declared', 'ac2/product-clean')
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

    def git(path, *args):
        done = subprocess.run(['git', '-C', str(path), '-c', 'user.name=fixture', '-c',
                               'user.email=fixture@example.com', '-c', 'commit.gpgsign=false',
                               '-c', 'core.hooksPath=' + os.devnull, *args],
                              capture_output=True, text=True, timeout=60)
        if done.returncode:
            raise RuntimeError('git %s: %s' % (args[0], done.stderr.strip()[:200]))
        return done.stdout.strip()

    # Invented personal values, assembled from pieces so that no line of this file carries one.
    J = ''.join
    OWNER_NAME = J(['Quill', 'ane ', 'Ostr', 'avek'])
    CHAT_ID = J(['77', '0412', '9933'])
    HOST = J(['zeph', 'yr-', 'den', '.lan'])
    ACCOUNT = J(['acct', '-qo-', '71'])
    HOME_PATH = J(['/', 'home', '/', 'qostravek', '/work'])
    UID_PATH = J(['/run', '/user/', '1', '207', '/bus'])
    EMAIL = J(['qo', '@', 'mailbox', '.', 'xyz'])
    SECRET = J(['gh', 'p_', 'Z' * 12, '9' * 12])
    PLANTED = {'owner_name': OWNER_NAME, 'chat_id': CHAT_ID, 'host': HOST, 'account': ACCOUNT,
               'home_path': HOME_PATH, 'login_uid': UID_PATH, 'fixture_email': EMAIL, 'secret': SECRET}

    def write_installation(folder, with_values=True):
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        if not with_values:
            return folder
        (folder / 'installation.yaml').write_text('\n'.join([
            'schema: veldo.installation/v1',
            'owner:',
            '  display_name: "%s"' % OWNER_NAME,
            '  role_id: owner',
            'git_identities:',
            '  owner:',
            '    name: "%s"' % OWNER_NAME,
            '    email: owner@example.com',
            'approvers: [key-one]',
            'channels:',
            '  main:',
            '    kind: chat',
            '    chat: "%s"' % CHAT_ID,
            '    token: {secret: chat_token}',
            'accounts:',
            '  primary:',
            '    label: "%s"' % ACCOUNT,
            'hosts:',
            '  build: "%s"' % HOST,
            'tailnet_names:',
            '  build: build-node',
            'ports:',
            '  api: 8710',
            'trackers:',
            '  main:',
            '    site: tracker.example.com',
            '    account_id: acct-1',
            'publisher:',
            '  name: Publisher',
            '  email: publisher@example.com',
            '']))
        for kind, ident, suffix in (('connectors', 'files', '.yaml'), ('services', 'mail', '.yaml'),
                                    ('workflows', 'standard', '.json')):
            (folder / kind).mkdir()
            (folder / kind / (ident + suffix)).write_text('{}\n' if suffix == '.json' else 'id: %s\n' % ident)
        (folder / 'patterns').mkdir()
        (folder / 'patterns' / 'people.yaml').write_text('\n'.join([
            'schema: veldo.installation.patterns/v1',
            'patterns:',
            '  - category: owner_name',
            '    literal: "%s"' % OWNER_NAME,
            '  - category: chat_id',
            "    expression: '\\b%s\\d{4}\\b'" % CHAT_ID[:6],
            '  - category: host',
            '    literal: "%s"' % HOST,
            '  - category: account',
            '    literal: "%s"' % ACCOUNT,
            '']))
        (folder / 'decisions').mkdir()
        (folder / 'decisions' / 'owner.yaml').write_text(
            'decisions:\n  D-1:\n    source: message 12\n    quote: "Yes, ship it"\n')
        (folder / 'records').mkdir()
        (folder / 'records' / 'old.md').write_text('a history record\n')
        return folder

    saved = {k: os.environ.get(k) for k in ('VELDO_INSTALLATION', 'XDG_CONFIG_HOME', 'HOME')}
    temp = Path(tempfile.mkdtemp(prefix='v259-'))

    def environ(**values):
        for key in ('VELDO_INSTALLATION', 'XDG_CONFIG_HOME'):
            os.environ.pop(key, None)
        os.environ['HOME'] = str(temp / 'home-none')
        for key, value in values.items():
            os.environ[key] = str(value)

    try:
        INST = load('v259_installation', PRODUCTION['installation.py'])
        CPS = load('v259_check_personal_setup', PRODUCTION['check_personal_setup.py'])
        # The check reads the installation through the reader beside the product it checks.
        CPS.LIB = ROOT / '.veldo'
        fixture = write_installation(temp / 'fixture')
        empty = write_installation(temp / 'empty', with_values=False)

        # ---- AC1: resolution ---------------------------------------------------------------------------
        environ(VELDO_INSTALLATION=fixture, XDG_CONFIG_HOME=temp / 'xdg')
        found = INST.resolve()
        check('ac1/resolution', 'VELDO_INSTALLATION wins [%s]' % found,
              found == {'folder': str(fixture), 'how': 'environment', 'found': True})
        environ(XDG_CONFIG_HOME=temp / 'xdg')
        write_installation(temp / 'xdg' / 'veldo' / 'installation')
        found = INST.resolve()
        check('ac1/resolution', 'else $XDG_CONFIG_HOME/veldo/installation [%s]' % found,
              found == {'folder': str(temp / 'xdg' / 'veldo' / 'installation'), 'how': 'default', 'found': True})
        environ(XDG_CONFIG_HOME='relative/path')
        found = INST.resolve()
        check('ac1/resolution', 'else ~/.config/veldo/installation, none found [%s]' % found,
              found == {'folder': str(temp / 'home-none' / '.config' / 'veldo' / 'installation'),
                        'how': 'default', 'found': False})
        stream = io.StringIO()
        environ(VELDO_INSTALLATION=fixture)
        loaded = INST.load(stream=stream)
        line = stream.getvalue()
        check('ac1/resolution', 'one line names the folder and how [%r]' % line,
              line.count('\n') == 1 and str(fixture) in line and 'VELDO_INSTALLATION' in line and loaded.found)
        stream = io.StringIO()
        environ()
        INST.load(stream=stream)
        line = stream.getvalue()
        check('ac1/resolution', 'one line says none was found and where it looked [%r]' % line,
              line.count('\n') == 1 and 'none found' in line and 'default' in line)

        # ---- AC1: the kinds ----------------------------------------------------------------------------
        environ(VELDO_INSTALLATION=fixture)
        inst = INST.load(stream=io.StringIO())
        owner = inst.owner()
        check('ac1/kinds', 'the owner from installation.yaml [%s]' % owner,
              owner == {'display_name': OWNER_NAME, 'role_id': 'owner'})
        check('ac1/kinds', 'git identity, approvers, channel, account',
              inst.git_identity('owner') == {'name': OWNER_NAME, 'email': 'owner@example.com'}
              and inst.approvers() == ['key-one'] and inst.channel('main')['token'] == {'secret': 'chat_token'}
              and inst.account('primary') == {'label': ACCOUNT}
              and inst.value('ports') == {'api': 8710} and inst.value('publisher')['name'] == 'Publisher')
        check('ac1/kinds', 'an installation file with the product id overrides it, else the product default',
              inst.override('connectors', 'files') == fixture / 'connectors' / 'files.yaml'
              and inst.override('services', 'mail') == fixture / 'services' / 'mail.yaml'
              and inst.override('workflows', 'standard') == fixture / 'workflows' / 'standard.json'
              and inst.override('workflows', 'other') is None)
        _, error = attempt(lambda: inst.override('workflows', '../escape'))
        check('ac1/kinds', 'an id that leaves its kind folder is refused [%s]' % error,
              error == 'installation_invalid:workflows')
        patterns = inst.patterns()
        check('ac1/kinds', 'patterns/ read with their categories [%s]' % [p[0] for p in patterns],
              sorted(p[0] for p in patterns) == ['account', 'chat_id', 'host', 'owner_name'])
        check('ac1/kinds', 'decisions/ map a reference to its source and quote',
              inst.decision('D-1') == {'source': 'message 12', 'quote': 'Yes, ship it'})
        check('ac1/kinds', 'records/ are listed, never read as configuration',
              inst.records() == [fixture / 'records' / 'old.md'])

        # ---- AC1: missing and invalid by name ----------------------------------------------------------
        for folder, how in ((empty, 'empty folder'), (temp / 'absent', 'absent folder')):
            environ(VELDO_INSTALLATION=folder)
            bare = INST.load(stream=io.StringIO())
            observed = [attempt(call)[1] for call in (
                bare.owner, lambda: bare.git_identity('owner'), bare.approvers, lambda: bare.channel('main'),
                lambda: bare.account('primary'), lambda: bare.value('publisher'))]
            check('ac1/missing-by-name', '%s refuses each by name [%s]' % (how, observed),
                  observed == ['installation_missing:owner', 'installation_missing:git_identities.owner',
                               'installation_missing:approvers', 'installation_missing:channels.main',
                               'installation_missing:accounts.primary', 'installation_missing:publisher'])
            check('ac1/missing-by-name', '%s has no patterns, overrides or records' % how,
                  bare.patterns() == [] and bare.override('workflows', 'standard') is None and bare.records() == [])
        partial = write_installation(temp / 'partial', with_values=False)
        (partial / 'installation.yaml').write_text('schema: veldo.installation/v1\nowner:\n  role_id: owner\n')
        environ(VELDO_INSTALLATION=partial)
        _, error = attempt(lambda: INST.load(stream=io.StringIO()).owner())
        check('ac1/missing-by-name', 'an owner without a display name is missing by name [%s]' % error,
              error == 'installation_missing:owner.display_name')

        cases = (
            ('ports:\n  api: high\n', 'installation_invalid:ports.api'),
            ('owner: someone\n', 'installation_invalid:owner'),
            ('channels:\n  main:\n    token: plain-literal-value\n', 'installation_invalid:channels.main.token'),
            ('surprise: 1\n', 'installation_invalid:surprise'),
            ('approvers: [1]\n', 'installation_invalid:approvers'),
        )
        for index, (body, code) in enumerate(cases):
            bad = write_installation(temp / ('bad%d' % index), with_values=False)
            (bad / 'installation.yaml').write_text('schema: veldo.installation/v1\n' + body)
            environ(VELDO_INSTALLATION=bad)
            _, error = attempt(lambda: INST.load(stream=io.StringIO()).settings())
            check('ac1/invalid-by-name', '%r is %s [%s]' % (body.strip(), code, error), error == code)
        bad = write_installation(temp / 'badschema', with_values=False)
        (bad / 'installation.yaml').write_text('schema: veldo.installation/v0\n')
        environ(VELDO_INSTALLATION=bad)
        _, error = attempt(lambda: INST.load(stream=io.StringIO()).settings())
        check('ac1/invalid-by-name', 'a foreign schema is installation_invalid:schema [%s]' % error,
              error == 'installation_invalid:schema')
        bad = write_installation(temp / 'badpattern', with_values=False)
        (bad / 'patterns').mkdir()
        (bad / 'patterns' / 'p.yaml').write_text(
            "schema: veldo.installation.patterns/v1\npatterns:\n  - {category: x, expression: '('}\n")
        environ(VELDO_INSTALLATION=bad)
        _, error = attempt(lambda: INST.load(stream=io.StringIO()).patterns())
        check('ac1/invalid-by-name', 'an expression that does not compile is invalid by name [%s]' % error,
              error == 'installation_invalid:patterns/p.yaml:0')

        # ---- AC1: revision -----------------------------------------------------------------------------
        environ(VELDO_INSTALLATION=fixture)
        check('ac1/revision', 'a folder that is not a git checkout has no revision',
              INST.load(stream=io.StringIO()).revision() is None)
        repo = write_installation(temp / 'repo')
        git(repo, 'init', '-q', '-b', 'main')
        git(repo, 'add', '-A')
        git(repo, 'commit', '-q', '-m', 'first')
        head = git(repo, 'rev-parse', 'HEAD')
        environ(VELDO_INSTALLATION=repo)
        trace = INST.trace(stream=io.StringIO())
        check('ac1/revision', 'a git installation names its commit id [%s]' % trace,
              trace == {'folder': str(repo), 'how': 'environment', 'revision': head})
        environ(VELDO_INSTALLATION=temp / 'absent')
        trace = INST.trace(stream=io.StringIO())
        check('ac1/revision', 'no installation: folder and revision are null [%s]' % trace,
              trace == {'folder': None, 'how': 'environment', 'revision': None})

        # ---- AC1: the reader is the only opener ----------------------------------------------------------
        tracked = git(ROOT, 'ls-files', '-z', '--', '*.py', '*.sh').split('\0')
        opener = re.compile(r'VELDO_INSTALLATION|installation\.yaml|[\'"]installation[\'"]\s*\)')
        others = []
        for rel in tracked:
            if not rel or rel.startswith(('scripts/suites/', 'proof/', 'specs/', 'docs/')):
                continue
            if rel in ('.veldo/installation.py', 'engine/.veldo/installation.py'):
                continue
            path = ROOT / rel
            if path.is_file() and opener.search(path.read_text('utf-8', 'replace')):
                others.append(rel)
        check('ac1/one-reader', 'no product module other than the reader names the folder [%s]' % others,
              others == [])
        engine_copy = ROOT / 'engine' / '.veldo' / 'installation.py'
        check('ac1/one-reader', 'the engine canon and this repository copy are the same reader',
              engine_copy.is_file() and engine_copy.read_bytes() == (ROOT / '.veldo' / 'installation.py').read_bytes())
        source = PRODUCTION['check_personal_setup.py'].read_text()
        check('ac1/one-reader', 'the check reads patterns through the reader',
              "'installation.py'" in source and '.patterns()' in source)

        # ---- AC1: the traces in factory setup and the API record ---------------------------------------
        SVC = load('v259_control_service', PRODUCTION['control_service.py'])
        SETUP = load('v259_control_factory_setup', PRODUCTION['control_factory_setup.py'])

        class Stub:
            api = None
            api_refusal = 'not_configured'
            config = {}

        def setup_answer():
            out = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                code = SETUP.main(['setup', '--state-root', str(temp / 'no-state'), '--owner', 'someone',
                                   '--owner-key', str(temp / 'no-key'), '--workspace', str(temp / 'no-ws'),
                                   '--chat', '5', '--token-file', str(temp / 'no-token')])
            return code, json.loads(out.getvalue().strip().splitlines()[-1])

        environ(VELDO_INSTALLATION=repo)
        record = SVC.Service.api_status(Stub())
        code, answer = setup_answer()
        expected = {'folder': str(repo), 'how': 'environment', 'revision': head}
        check('ac1/traces', 'the API record names the installation folder and revision [%s]' % record.get('installation'),
              record.get('installation') == expected)
        check('ac1/traces', 'factory setup names the installation folder and revision [%s]'
              % answer.get('installation'), code == 1 and answer.get('installation') == expected)
        environ(VELDO_INSTALLATION=empty)
        record = SVC.Service.api_status(Stub())
        code, answer = setup_answer()
        text = json.dumps([record, answer])
        leaked = [k for k, v in PLANTED.items() if v in text]
        check('ac1/traces', 'with an empty installation no output carries a value of the fixture [%s]' % leaked,
              leaked == [] and record['installation']['revision'] is None
              and answer['installation'] == {'folder': str(empty), 'how': 'environment', 'revision': None})

        # ---- AC1: no personal value in any default --------------------------------------------------------
        environ(VELDO_INSTALLATION=temp / 'absent')
        defaults = ['.veldo/installation.py', 'engine/.veldo/installation.py', 'scripts/check_personal_setup.py',
                    '.veldo/control_service.py', 'engine/.veldo/control_service.py',
                    '.veldo/control_factory_setup.py', 'engine/.veldo/control_factory_setup.py',
                    'docs/installation.md', 'scripts/publish.py']
        found = CPS.sweep(ROOT, files=defaults, out=io.StringIO())
        check('ac1/no-personal-default', 'the built-in shapes find nothing in the reader, the check and the '
              'consumers [%s]' % found, found == [])

        # ---- AC2: the gate over a candidate ----------------------------------------------------------------
        def candidate(name, lines, base_lines=()):
            root = temp / name
            root.mkdir()
            git(root, 'init', '-q', '-b', 'main')
            (root / 'tests' / 'fixtures').mkdir(parents=True)
            (root / 'app.py').write_text('\n'.join(['x = 1'] + list(base_lines)) + '\n')
            (root / 'tests' / 'fixtures' / 'data.txt').write_text('fixture\n')
            git(root, 'add', '-A')
            git(root, 'commit', '-q', '-m', 'base')
            git(root, 'checkout', '-q', '-b', 'work')
            for rel, text in lines:
                with open(root / rel, 'a') as handle:
                    handle.write(text + '\n')
            git(root, 'add', '-A')
            git(root, 'commit', '-q', '-m', 'work')
            return root

        def gate(root, *extra):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = CPS.main(['--root', str(root), *extra])
            return code, out.getvalue()

        plants = [('app.py', 'NAME = "%s"' % OWNER_NAME), ('app.py', 'CHAT = %s' % CHAT_ID),
                  ('app.py', 'HOST = "%s"' % HOST), ('app.py', 'ACCOUNT = "%s"' % ACCOUNT),
                  ('app.py', 'WHERE = "%s"' % HOME_PATH), ('app.py', 'BUS = "%s"' % UID_PATH),
                  ('tests/fixtures/data.txt', 'mail %s' % EMAIL), ('app.py', 'KEY = "%s"' % SECRET)]
        planted = candidate('planted', plants)
        environ(VELDO_INSTALLATION=fixture)
        code, output = gate(planted)
        for index, category in enumerate(PLANTED):
            rel = plants[index][0]
            number = 1 + sum(1 for r, _ in plants[:index + 1] if r == rel)
            want = 'personal_setup:%s %s:%d %s***' % (category, rel, number, PLANTED[category][:2])
            check('ac2/planted', '%s planted is refused by name with file, line and mask [%s]'
                  % (category, want), code == 1 and want in output)
        check('ac2/planted', 'a closing count per category [%s]' % output.strip().splitlines()[-1:],
              all(('%s=1' % c) in output for c in PLANTED))
        for category in PLANTED:
            single = candidate('single-' + category, [plants[list(PLANTED).index(category)]])
            code, output = gate(single)
            check('ac2/planted', '%s alone turns the stage red [%s]' % (category, code),
                  code == 1 and ('personal_setup:' + category) in output)
        check('ac2/masked', 'no planted value appears unmasked in the gate output',
              not [k for k, v in PLANTED.items() if v in output] and output)
        environ(VELDO_INSTALLATION=fixture)
        code, output = gate(planted)
        check('ac2/masked', 'nor in the full run over every category [%s]' % [k for k, v in PLANTED.items() if v in output],
              not [k for k, v in PLANTED.items() if v in output] and CHAT_ID[:6] not in output)
        check('ac2/masked', 'the mask is the first two characters then ***',
              CPS.mask(OWNER_NAME) == OWNER_NAME[:2] + '***' and CPS.mask('a') == 'a***')

        # Added lines only in gate mode; sweep mode judges the whole tree.
        old = candidate('old', [('app.py', 'y = 2')], base_lines=['NAME = "%s"' % OWNER_NAME])
        code, output = gate(old)
        check('ac2/added-only', 'a value already in the base is not judged at the gate [%s]' % code, code == 0)
        code, output = gate(old, '--sweep')
        check('ac2/added-only', 'sweep mode finds it in the whole tree [%s]' % code,
              code == 1 and 'personal_setup:owner_name app.py:2 Qu***' in output)
        uncommitted = candidate('uncommitted', [('app.py', 'y = 2')])
        (uncommitted / 'new.txt').write_text('host %s\n' % HOST)
        code, output = gate(uncommitted)
        check('ac2/added-only', 'an untracked file of the candidate is judged too [%s]' % code,
              code == 1 and 'personal_setup:host new.txt:1 ze***' in output)
        email_outside = candidate('email-outside', [('app.py', '# write to %s' % EMAIL)])
        code, output = gate(email_outside)
        check('ac2/added-only', 'an email outside a fixture is not a built-in finding [%s]' % code, code == 0)
        reserved = candidate('reserved', [('tests/fixtures/data.txt', 'a@example.org b@site.test c@x.example')])
        code, output = gate(reserved)
        check('ac2/added-only', 'reserved example domains in a fixture pass [%s]' % code, code == 0)

        # No installation: the built-in shapes only, said on its own line.
        environ(VELDO_INSTALLATION=temp / 'absent')
        clean = candidate('clean', [('app.py', 'y = 2')])
        code, output = gate(clean)
        check('ac2/no-installation', 'a clean candidate passes and the run says built-in shapes only [%r]'
              % output, code == 0 and any(l.strip() == 'personal setup: no installation found; ran the built-in '
                                          'shapes only' for l in output.splitlines()))
        code, output = gate(planted)
        check('ac2/no-installation', 'built-in shapes still refuse without an installation, installation '
              'categories do not [%s]' % code,
              code == 1 and 'personal_setup:home_path' in output and 'personal_setup:owner_name' not in output)
        environ(VELDO_INSTALLATION=fixture)
        code, output = gate(clean)
        check('ac2/no-installation', 'with an installation the built-in-only line is absent',
              code == 0 and 'built-in shapes only' not in output)

        # The publication scan calls the same code.
        PUB = load('v259_publish', ROOT / 'scripts' / 'publish.py')
        produced = temp / 'produced'
        produced.mkdir()
        (produced / 'README.md').write_text('owner %s\n' % OWNER_NAME)
        environ(VELDO_INSTALLATION=fixture)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            findings = PUB.personal_setup(produced)
        check('ac2/publish-shares', 'the publication scan refuses through check_personal_setup [%s]' % findings,
              [f['category'] for f in findings] == ['owner_name'] and OWNER_NAME not in out.getvalue()
              and PUB.CPS.sweep.__code__.co_filename.endswith('check_personal_setup.py'))
        pub_source = (ROOT / 'scripts' / 'publish.py').read_text()
        check('ac2/publish-shares', 'build refuses a produced tree on a personal-setup finding',
              'findings = personal_setup(dest)' in pub_source)

        # The declared stage.
        verify = (ROOT / 'scripts' / 'verify.sh').read_text()
        check('ac2/stage-declared', 'verify.sh declares the stage and orders it',
              'CHECK_personal_setup="required:python3 scripts/check_personal_setup.py"' in verify
              and re.search(r'ORDER="[^"]*\bpersonal_setup\b', verify) is not None)
        graph = json.loads((ROOT / 'scripts' / 'gate_graph.json').read_text())
        node = graph['nodes'].get('personal_setup') or {}
        check('ac2/stage-declared', 'gate_graph.json declares the node [%s]' % sorted(node),
              node.get('depends_on') == [] and node.get('writes_candidate') is False)
        SCHED = load('v259_gate_schedule', ROOT / 'scripts' / 'gate_schedule.py')
        catalog = {}
        for name in re.search(r'ORDER="([^"]*)"', verify).group(1).replace('\\\n', ' ').split():
            match = re.search(r'^CHECK_%s="required:([^"]*)"' % name, verify, re.M)
            if match:
                catalog[name] = match.group(1)
        listing = ROOT / 'scripts' / 'gate_unconfined.json'
        legs = SCHED.load_module('gate_legs').load(listing)[0] if listing.exists() else None
        _, error = attempt(lambda: SCHED.read_graph(catalog, legs, ROOT / 'scripts' / 'gate_graph.json'))
        check('ac2/stage-declared', 'the scheduler accepts the graph for the declared catalog [%s]' % error,
              error is None and 'personal_setup' in catalog)

        # ---- AC1: a fresh clone with no installation -------------------------------------------------------
        environ(VELDO_INSTALLATION=temp / 'absent')
        clone = temp / 'clone'
        git(temp, 'clone', '-q', '--no-hardlinks', str(ROOT), str(clone))
        code, output = gate(clone)
        check('ac1/fresh-clone', 'a fresh clone with no installation passes the stage, built-in only [%s %s]'
              % (code, output.strip().splitlines()[-2:]), code == 0 and 'built-in shapes only' in output)

        # ---- AC2: no installation pattern is in the product ------------------------------------------------
        environ(VELDO_INSTALLATION=fixture)
        files = [p for p in git(ROOT, 'ls-files', '-z').split('\0') if p]
        found = [f for f in CPS.sweep(ROOT, files=files, out=io.StringIO())
                 if f['category'] in ('owner_name', 'chat_id', 'host', 'account')]
        check('ac2/product-clean', 'no pattern of the fixture installation is in a tracked file [%s]' % found[:3],
              found == [])
    except Exception as error:
        import traceback
        check('ac1/resolution', 'raised ' + type(error).__name__ + ': ' + str(error)[:300]
              + ' ' + traceback.format_exc().splitlines()[-3][:200], False)
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        shutil.rmtree(temp, ignore_errors=True)

    for row, values in rows.items():
        failed = [label for label, ok in values if not ok]
        expect('VELDO-0259 ' + row + (': ' + failed[0] if failed else ''), bool(values) and not failed)


_v259_installation_suite()
