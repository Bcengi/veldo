"""VELDO-0329: installing the git hooks and the session hooks, and reconcile's report of a missing one.

Real temporary git repositories whose installed hooks git itself runs, a real store and Ledger with
signed observer packets over the spool socket, real client account folders with their settings files,
the real reconciler and the real bootstrap. The CLI the git hooks start is a fixture script that writes
down what it was given; the session script loads the real spool module beside it. Only ROOT and expect
are shared. Every repository, folder, key and database is the fixture's own.
"""


def _v329_suite():
    import importlib.util
    import io
    import json
    import os
    from pathlib import Path
    import select
    import shutil
    import socket
    import subprocess
    import tempfile
    import time
    import traceback
    import types

    PRODUCTION = {
        'control_space_reconcile.py': ROOT / ".veldo" / "control_space_reconcile.py",
    }
    HOOK_SOURCE = ROOT / 'engine' / 'hooks'
    SESSION_SOURCE = ROOT / 'packs' / 'claude' / 'scripts' / 'space-session.py'
    rows = {}

    def check(row, message, good):
        rows.setdefault(row, []).append((message, bool(good)))

    def load(name, path):
        spec = importlib.util.spec_from_file_location('v329_' + name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    temp = Path(tempfile.mkdtemp(prefix='veldo-0329-')).resolve()
    conn = boot_conn = listener = None
    children = []
    try:
        mods = temp / '.veldo'
        shutil.copytree(ROOT / '.veldo', mods, ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copyfile(PRODUCTION['control_space_reconcile.py'], mods / 'control_space_reconcile.py')
        # Laid out as an engine is: the hooks beside .veldo, and the pack's script where the engine looks.
        shutil.copytree(HOOK_SOURCE, temp / 'hooks')
        (temp / 'packs' / 'claude' / 'scripts').mkdir(parents=True)
        shutil.copyfile(SESSION_SOURCE, temp / 'packs' / 'claude' / 'scripts' / 'space-session.py')
        R = load('reconcile', mods / 'control_space_reconcile.py')
        spool = load('spool', mods / 'control_space_spool.py')
        SP = spool._sibling('control_space')
        S = spool._sibling('control_store')
        CM = spool._sibling('control_membership')
        K = spool._sibling('control_space_kinds')
        CFG, YAML = load('config', mods / 'control_space_config.py'), load('yamlish', mods / 'yamlish.py')
        AC = CM.AC
        CM.attach(S)
        state, scratch, installation, home = (temp / name for name in ('state', 'scratch', 'installation', 'home'))
        for path in (state, scratch, installation, installation / 'keys', home, temp / 'bin'):
            path.mkdir(mode=0o700)
        # The CLI the git hooks start: it writes down its arguments and its input, and nothing else.
        seen = temp / 'cli-seen'
        cli = temp / 'bin' / 'veldo'
        cli.write_text('#!/bin/sh\n{ printf "%s " "$@"; echo; cat; echo END; } >>' + str(seen) + '\n')
        cli.chmod(0o755)
        own_seen = temp / 'own-seen'
        # TMPDIR names nothing: the hooks must work on a host whose temporary folder cannot be written.
        git_env = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'HOME': str(home), 'LC_ALL': 'C',
                   'TMPDIR': str(temp / 'no-such-temporary-folder'),
                   'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_NOSYSTEM': '1',
                   'GIT_AUTHOR_NAME': 'Fixture', 'GIT_AUTHOR_EMAIL': 'fixture@example.invalid',
                   'GIT_COMMITTER_NAME': 'Fixture', 'GIT_COMMITTER_EMAIL': 'fixture@example.invalid'}

        def git(where, *args):
            """Plain git, with the repository's own hooks in play: what a person at a terminal runs."""
            done = subprocess.run(['git', '-c', 'commit.gpgsign=false', '-c', 'advice.detachedHead=false',
                                   '-C', str(where), *args], env=git_env, capture_output=True, text=True, timeout=60)
            if done.returncode:
                raise RuntimeError('git ' + ' '.join(args) + ': ' + done.stderr)
            return done.stdout.strip()

        def told_to(where, key):
            """One value of a repository's own git configuration, or None when it has none."""
            try:
                return git(where, 'config', '--get', key)
            except RuntimeError:
                return None

        def repository(name):
            path = temp / name
            path.mkdir()
            git(path, 'init', '-q', '-b', 'main')
            (path / 'tracked').write_text('base\n')
            git(path, 'add', 'tracked')
            git(path, 'commit', '-q', '-m', 'base')
            (temp / (name + '-trees')).mkdir()
            return path

        bound, plain, custom, refuse, dormant = (repository(name) for name in
                                                 ('bound', 'plain', 'custom', 'refuse', 'dormant'))
        # A linked worktree made before any hook exists: it must use the hooks installed afterwards.
        git(bound, 'worktree', 'add', '-q', '-b', 'before', str(temp / 'bound-trees' / 'before'))
        # The owner's own hooks in the plain repository, both shell scripts, one that reads git's input.
        OWN = {'post-checkout': '#!/bin/sh\n# the owner wrote this hook\necho "own post-checkout $3" >>'
                                + str(own_seen) + '\nexit 0\n',
               'reference-transaction': '#!/bin/bash\nset -e\n# the owner wrote this hook too\n'
                                        'while read -r old new ref; do\n  echo "own ref $1 $ref" >>'
                                        + str(own_seen) + '\ndone\n'}
        for name, text in OWN.items():
            (plain / '.git' / 'hooks' / name).write_text(text)
            (plain / '.git' / 'hooks' / name).chmod(0o755)
        custom_hooks = temp / 'custom-hooks'
        custom_hooks.mkdir()
        git(custom, 'config', 'core.hooksPath', str(custom_hooks))
        # Hooks Veldo must not change: a program that is no shell script, a link, a file git does not run.
        PROGRAM = '#!/usr/bin/env python3\nprint("the owner wrote this program")\n'
        (refuse / '.git' / 'hooks' / 'post-checkout').write_text(PROGRAM)
        (refuse / '.git' / 'hooks' / 'post-checkout').chmod(0o755)
        elsewhere = temp / 'owner-hook-manager'
        elsewhere.write_text('#!/bin/sh\nexit 0\n')
        elsewhere.chmod(0o755)
        (refuse / '.git' / 'hooks' / 'reference-transaction').symlink_to(elsewhere)
        DORMANT = '#!/bin/sh\necho "the owner switched this hook off"\n'
        (dormant / '.git' / 'hooks' / 'post-checkout').write_text(DORMANT)
        (dormant / '.git' / 'hooks' / 'post-checkout').chmod(0o644)

        accounts = {name: temp / ('account-' + name) for name in 'abc'}
        for path in accounts.values():
            path.mkdir(mode=0o700)
        OWN_SETTINGS = {'model': 'the-owner-chose-this', 'permissions': {'allow': ['Bash(ls:*)']},
                        'hooks': {'PreToolUse': [{'matcher': 'Bash', 'hooks': [
                                      {'type': 'command', 'command': 'echo the owner guards this'}]}],
                                  'SessionStart': [{'hooks': [
                                      {'type': 'command', 'command': 'echo the owner greets the session'}]}]}}
        (accounts['b'] / 'settings.json').write_text(json.dumps(OWN_SETTINGS, indent=4))
        BROKEN = '{"hooks": {"SessionStart": [  // the owner is editing this\n'
        (accounts['c'] / 'settings.json').write_text(BROKEN)

        keys = {}
        for who in ('owner', SP.OBSERVER):
            key = installation / 'keys' / who
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key)],
                           check=True, capture_output=True, timeout=10)
            keys[who] = (key, Path(str(key) + '.pub').read_text().strip())

        def sign_as(who, data):
            return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(keys[who][0]), '-n',
                                   AC.SIGNATURE_NAMESPACE], input=data, capture_output=True,
                                  check=True, timeout=10).stdout.decode()

        conn = S.open_store(str(temp / 'control.sqlite3'))
        ids = {'domain_uuid': 'd329', 'repository_uuid': 'r329', 'store_uuid': 's329'}
        for index, who in enumerate(('owner', SP.OBSERVER)):
            params = {'principal': who, 'principal_type': 'person' if who == 'owner' else 'service',
                      'roles': ['membership_steward', 'project_owner'] if who == 'owner' else [],
                      'public_key': keys[who][1], 'independence_group': who,
                      'scope': '*' if who == 'owner' else [SP.SCOPE]}
            command = {'command_id': 'setup%d' % index, 'operation': 'enroll_principal', 'target': 'authority',
                       'parameters': params, 'artifact_digests': [], 'expected_versions': {}}
            now = CM.authority_state(S, conn)
            envelope = dict(ids, schema=AC.ENVELOPE_SCHEMA, command_id=command['command_id'], principal='owner',
                            request_revision=1, nonce='setup%d' % index, expires_at=1600,
                            membership_version=now['membership_version'], delegation_version=now['delegation_version'],
                            command_digest=AC.canonical_command_digest(command))
            cosigned = None if who == 'owner' else sign_as(who, AC.canonical_envelope_bytes(dict(envelope, principal=who)))
            CM.admit(S, conn, envelope, command, sign_as('owner', AC.canonical_envelope_bytes(envelope)),
                     ids, 1000, enrollee_signature=cosigned, journal_signer=('authority', lambda data: 'fixture'))
        plains = [{'repository': str(path), 'worktree_root': str(temp / (path.name + '-trees'))}
                  for path in (plain, custom, refuse, dormant)]
        config = {'present': True, 'enabled': True, 'engines': [], 'build_roots': [],
                  'scratch_roots': {'roots': [str(scratch)], 'session_pattern': 'sessions/{working_folder}/{session_id}'},
                  'plain_repositories': plains, 'client_accounts': [str(path) for path in accounts.values()],
                  'protect': [], 'pools': {'host': {'floor': 0, 'needs': {}}}}
        project = {'project': 'fixture-project', 'repository': str(bound), 'worktree_root': str(temp / 'bound-trees')}
        ledger = SP.Ledger(S, conn, 'authority', lambda data: 'fixture', config=config,
                           projects=[project], state_root=str(state), lifecycle=K.LIFECYCLE,
                           host=socket.gethostname(), device=lambda path: 'fixture-device')
        ledger.set_pool('host', 'filesystem', device='fixture-device')
        authority = spool.Local(ledger, CM)
        folder = spool.spool_folder(str(state))
        listener = spool.listen(folder)

        def install():
            return R.install(ledger, cli=str(cli), installation=str(installation),
                             hooks_source=str(HOOK_SOURCE), session_script=str(SESSION_SOURCE))

        def of(records, key, path):
            return next((one for one in records if one.get(key) == str(path)), {})

        def told():
            """What the hooks' CLI was given so far: one (arguments, input lines) for each start."""
            if not seen.exists():
                return []
            found = []
            for part in seen.read_text().split('END\n'):
                lines = part.splitlines()
                if lines:
                    found.append((lines[0], lines[1:]))
            return found

        def executable(path):
            return path.is_file() and not path.is_symlink() and os.access(path, os.X_OK)

        def marked(path):
            return [line for line in path.read_bytes().split(b'\n') if line.endswith(R.HOOK_MARK.encode())]

        records = install()

        # ---- AC1 -------------------------------------------------------------------------------
        row = 'ac1/bound-and-plain'
        for path in (bound, dormant):
            record, hooks = of(records, 'repository', path), path / '.git' / 'hooks'
            wanted = {'post-checkout': 'installed', 'reference-transaction': 'installed'} if path == bound \
                else {'post-checkout': 'refused:not_executable', 'reference-transaction': 'installed'}
            check(row, '%s: the record names the shared hooks folder and each hook: %s' % (path.name, record),
                  record.get('hooks_folder') == str(hooks) and record.get('hooks') == wanted)
        hooks = bound / '.git' / 'hooks'
        check(row, 'both hooks are executable files in the shared hooks folder, each with one marked line',
              all(executable(hooks / name) and executable(hooks / (R.HOOK_OURS + name))
                  and len(marked(hooks / name)) == 1
                  and (hooks / (R.HOOK_OURS + name)).read_bytes() == (HOOK_SOURCE / name).read_bytes()
                  for name in R.HOOKS))
        check(row, 'a linked worktree made before the install uses the same folder',
              os.path.realpath(os.path.join(str(temp / 'bound-trees' / 'before'),
                                            git(temp / 'bound-trees' / 'before', 'rev-parse', '--git-path', 'hooks')))
              == str(hooks))
        check(row, 'the repository is told the state root and the CLI',
              told_to(bound, 'veldo.space.stateroot') == str(state)
              and told_to(bound, 'veldo.space.cli') == str(cli)
              and told_to(bound, 'veldo.space.installation') == str(installation))
        tree = temp / 'bound-trees' / 'made-after'
        git(bound, 'worktree', 'add', '-q', '-b', 'after', str(tree))
        git(bound, 'commit', '-q', '--allow-empty', '-m', 'the trunk moves')
        said = told()
        check(row, 'git itself runs the installed hooks: a worktree add and a trunk commit each start the CLI: '
              + str(said),
              any(words.startswith('space record --state-root ' + str(state)) and '--worktree ' + str(tree) in words
                  for words, _lines in said)
              and any(words.startswith('space event --state-root ' + str(state))
                      and '--common-dir ' + str(bound / '.git') in words
                      and any(line.endswith(' refs/heads/main') for line in lines) for words, lines in said))

        row = 'ac1/configured-folder'
        record = of(records, 'repository', custom)
        check(row, 'the hooks go to the folder the repository configures: ' + str(record),
              record.get('hooks_folder') == str(custom_hooks) and record.get('ok') is True
              and all(executable(custom_hooks / name) and executable(custom_hooks / (R.HOOK_OURS + name))
                      for name in R.HOOKS))
        check(row, 'and not to the shared folder git does not read there',
              not any((custom / '.git' / 'hooks' / name).exists() for name in R.HOOKS))
        tree = temp / 'custom-trees' / 'one'
        git(custom, 'worktree', 'add', '-q', '-b', 'one', str(tree))
        check(row, 'git runs them from there, and the shared folder still holds none',
              not any((custom / '.git' / 'hooks' / name).exists() for name in R.HOOKS) and any(words.startswith('space record ') and '--worktree ' + str(tree) in words for words, _l in told()))

        row = 'ac1/keeps-own-lines'
        record, hooks = of(records, 'repository', plain), plain / '.git' / 'hooks'
        check(row, 'each existing hook is chained, and the record says so: ' + str(record),
              record.get('hooks') == {'post-checkout': 'chained', 'reference-transaction': 'chained'})
        for name, text in OWN.items():
            now = (hooks / name).read_text()
            kept = '\n'.join(line for line in now.split('\n') if not line.endswith(R.HOOK_MARK))
            check(row, name + ': every line the owner wrote is still there, in order, and one marked line was added: '
                  + repr(now),
                  kept == text and len(marked(hooks / name)) == 1 and now.split('\n')[0] == text.split('\n')[0]
                  and executable(hooks / name))
        tree = temp / 'plain-trees' / 'one'
        git(plain, 'worktree', 'add', '-q', '-b', 'one', str(tree))
        git(plain, 'commit', '-q', '--allow-empty', '-m', 'the trunk moves')
        own = own_seen.read_text().splitlines() if own_seen.exists() else []
        said = told()
        check(row, 'the owner\'s lines still run, with git\'s input whole: ' + str(own),
              'own post-checkout 1' in own and 'own ref committed refs/heads/main' in own
              and 'own ref prepared refs/heads/main' in own)
        check(row, 'nothing of the input copy is left in the hooks folder: ' + str(sorted(os.listdir(hooks))),
              not any(name.startswith('.veldo-in.') for name in os.listdir(hooks)))
        check(row, 'and Veldo\'s hook runs beside them with the same input',
              any(words.startswith('space record ') and '--worktree ' + str(tree) in words for words, _l in said)
              and any(words.startswith('space event ') and '--common-dir ' + str(plain / '.git') in words
                      and any(line.endswith(' refs/heads/main') for line in lines) for words, lines in said))
        before = {name: (hooks / name).read_bytes() for name in sorted(os.listdir(hooks))}
        again = install()
        check(row, 'a second install changes no byte and adds no second line: ' + str(of(again, 'repository', plain)),
              {name: (hooks / name).read_bytes() for name in sorted(os.listdir(hooks))} == before
              and of(again, 'repository', plain).get('hooks')
              == {'post-checkout': 'present', 'reference-transaction': 'present'})

        row = 'ac1/refused-and-said'
        record, hooks = of(again, 'repository', refuse), refuse / '.git' / 'hooks'
        check(row, 'a program and a link are refused by name, with why: ' + str(record),
              record.get('ok') is False and record.get('hooks') == {
                  'post-checkout': 'refused:not_a_shell_script', 'reference-transaction': 'refused:not_a_plain_file'})
        check(row, 'and are left as they were, with nothing of Veldo\'s beside them: ' + str(sorted(os.listdir(hooks))),
              (hooks / 'post-checkout').read_text() == PROGRAM
              and (hooks / 'reference-transaction').is_symlink()
              and os.readlink(hooks / 'reference-transaction') == str(elsewhere)
              and elsewhere.read_text() == '#!/bin/sh\nexit 0\n'
              and not any(name.startswith(R.HOOK_OURS) or name.startswith('.') for name in os.listdir(hooks)))
        hooks = dormant / '.git' / 'hooks'
        check(row, 'a hook git does not run is left switched off and unchanged',
              (hooks / 'post-checkout').read_text() == DORMANT and not os.access(hooks / 'post-checkout', os.X_OK)
              and of(again, 'repository', dormant).get('ok') is False)
        # An earlier copy of Veldo's own hook is replaced and kept; a file of the owner's under that name is not.
        ours = bound / '.git' / 'hooks' / (R.HOOK_OURS + 'post-checkout')
        ours.write_bytes(b'#!/bin/sh\n# Veldo space management, an earlier release\nexit 0\n')
        taken = custom_hooks / (R.HOOK_OURS + 'post-checkout')
        taken.write_bytes(b'#!/bin/sh\necho "the owner uses this name"\n')
        third = install()
        aside = [name for name in os.listdir(ours.parent) if name.startswith(ours.name + '.replaced-')]
        check(row, 'an earlier copy of Veldo\'s hook is replaced and kept beside it: ' + str(aside),
              ours.read_bytes() == (HOOK_SOURCE / 'post-checkout').read_bytes() and len(aside) == 1
              and (ours.parent / aside[0]).read_bytes().endswith(b'an earlier release\nexit 0\n'))
        check(row, 'a file of the owner\'s under Veldo\'s name is refused and kept: '
              + str(of(third, 'repository', custom)),
              taken.read_bytes() == b'#!/bin/sh\necho "the owner uses this name"\n'
              and of(third, 'repository', custom).get('hooks', {}).get('post-checkout') == 'refused:veldo_name_taken')
        taken.unlink(missing_ok=True)
        install()

        # ---- AC2 -------------------------------------------------------------------------------
        def ours_in(account, event):
            try:
                settings = json.loads((account / 'settings.json').read_text())
            except (OSError, ValueError):
                return []
            return [entry for _group, entry in R._session_entries(settings, event)]

        row = 'ac2/every-account'
        for name in 'ab':
            record = of(records, 'account', accounts[name])
            check(row, 'account %s: the record names the settings file and both hooks: %s' % (name, record),
                  record.get('ok') is True and record.get('settings') == str(accounts[name] / 'settings.json')
                  and record.get('hooks') == {'SessionStart': 'installed', 'SessionEnd': 'installed'})
            check(row, 'account %s: one entry for each hook, bounded, and the script beside the settings' % name,
                  all(len(ours_in(accounts[name], event)) == 1
                      and ours_in(accounts[name], event)[0].get('timeout') == 15
                      and ours_in(accounts[name], event)[0]['command'].startswith('exec ')
                      for event in R.SESSION_EVENTS)
                  and (accounts[name] / R.SESSION_SCRIPT).read_bytes() == SESSION_SOURCE.read_bytes())
        kept = json.loads((accounts['b'] / 'settings.json').read_text())
        for event in R.SESSION_EVENTS:
            rest = [group for group in kept.get('hooks', {}).get(event, [])
                    if not any(R.SESSION_SCRIPT in str(entry.get('command')) for entry in group['hooks'])]
            kept.get('hooks', {}).pop(event, None)
            if rest:
                kept['hooks'][event] = rest
        check(row, 'every key and hook the owner had in the second account is kept: ' + str(kept),
              kept == OWN_SETTINGS)
        record = of(records, 'account', accounts['c'])
        check(row, 'a settings file that cannot be read is refused and left byte for byte: ' + str(record),
              record.get('ok') is False and str(record.get('refused')).startswith('settings_unread')
              and (accounts['c'] / 'settings.json').read_text() == BROKEN
              and sorted(os.listdir(accounts['c'])) == ['settings.json'])
        check(row, 'a second install changed nothing in an account folder',
              all(of(again, 'account', accounts[name]).get('hooks')
                  == {'SessionStart': 'present', 'SessionEnd': 'present'} for name in 'ab'))

        def start_session(account, session, where):
            """What the client does at a session's start: run the account's own SessionStart hooks."""
            entries = ours_in(account, 'SessionStart')
            if not entries:
                return None
            process = subprocess.Popen(['/bin/sh', '-c', entries[0]['command']],
                                       env={'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'HOME': str(home),
                                            'PYTHONDONTWRITEBYTECODE': '1'},
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            children.append(process)
            process.stdin.write(json.dumps({'session_id': session, 'cwd': str(where)}).encode())
            process.stdin.close()
            began = time.monotonic()
            while process.poll() is None and time.monotonic() - began < 15:
                if select.select([listener], [], [], 0.02)[0]:
                    spool.serve_one(listener, authority)
            return process.poll()

        def items(session):
            return [record for record in ledger.items().values() if (record.get('owner') or {}).get('session') == session]

        row = 'ac2/session-under-second'
        for name, session in (('a', 'under-first'), ('b', 'under-second')):
            status = start_session(accounts[name], session, bound)
            found = items(session)
            check(row, 'a session started under account %s leaves its item: %s' % (name, (status, found)),
                  status == 0 and len(found) == 1 and found[0]['kind'] == 'scratch'
                  and found[0]['owner'] == {'scope': {'type': 'project', 'id': 'fixture-project'}, 'session': session}
                  and found[0]['process']['pid'] == os.getpid())

        # ---- AC3 -------------------------------------------------------------------------------
        def findings(why):
            result = R.Reconciler({'ledger': ledger}).run('cli')
            return result, [one for one in result['findings'] if one['why'] == why]

        row = 'ac3/missing-hook-reported'
        result, found = findings('hooks_missing')
        check(row, 'with the hooks in place only the refused ones are reported, with why: ' + str(found),
              result['ok'] and {one['repository']: one['missing'] for one in found} == {
                  str(refuse): {'post-checkout': 'no_veldo_line', 'reference-transaction': 'not_a_plain_file'},
                  str(dormant): {'post-checkout': 'not_executable'}})
        (bound / '.git' / 'hooks' / 'post-checkout').unlink(missing_ok=True)
        (plain / '.git' / 'hooks' / 'reference-transaction').unlink(missing_ok=True)
        (custom_hooks / (R.HOOK_OURS + 'post-checkout')).unlink(missing_ok=True)
        result, found = findings('hooks_missing')
        told_of = {one['repository']: one for one in found}
        check(row, 'a bound repository whose hook was deleted is reported, with the hook and its folder: '
              + str(told_of.get(str(bound))),
              result['ok'] and told_of.get(str(bound), {}).get('missing') == {'post-checkout': 'absent'}
              and told_of.get(str(bound), {}).get('hooks_folder') == str(bound / '.git' / 'hooks'))
        check(row, 'a plain repository whose hook was deleted is reported: ' + str(told_of.get(str(plain))),
              told_of.get(str(plain), {}).get('missing') == {'reference-transaction': 'absent'})
        check(row, 'a hook whose marked line starts nothing is reported: ' + str(told_of.get(str(custom))),
              told_of.get(str(custom), {}).get('missing') == {'post-checkout': 'veldo_hook_absent'}
              and told_of.get(str(custom), {}).get('hooks_folder') == str(custom_hooks))
        check(row, 'reporting is all reconcile did about it: nothing was put back',
              not (bound / '.git' / 'hooks' / 'post-checkout').exists())

        row = 'ac3/missing-session-reported'
        result, found = findings('session_hooks_missing')
        check(row, 'with the session hooks in place only the refused account is reported: ' + str(found),
              result['ok'] and [one['account'] for one in found] == [str(accounts['c'])]
              and str(found[0]['missing'][0]).startswith('settings_unread'))
        settings = json.loads((accounts['b'] / 'settings.json').read_text())
        settings.setdefault('hooks', {})['SessionEnd'] = []
        (accounts['b'] / 'settings.json').write_text(json.dumps(settings))
        (accounts['a'] / 'settings.json').unlink(missing_ok=True)
        result, found = findings('session_hooks_missing')
        told_of = {one['account']: one['missing'] for one in found}
        check(row, 'an account folder whose session hook was taken out is reported with the hook: ' + str(told_of),
              result['ok'] and told_of.get(str(accounts['b'])) == ['SessionEnd']
              and told_of.get(str(accounts['a'])) == ['settings_absent'])

        # ---- The service's start: binding a repository is what installs --------------------------
        row = 'wiring/bootstrap-installs'
        boot = temp / 'boot'
        boot.mkdir()
        newly, named = repository('boot/newly-bound'), repository('boot/named-plain')
        account = boot / 'account'
        account.mkdir()
        section = {'enabled': 'true', 'time_zone': 'UTC',
                   'pools': {'host': {'floor': 0, 'needs': {'build': 0, 'review': 0, 'gate': 0}}},
                   'engines': ['fixture'], 'scratch_roots': {'roots': [str(boot / 'scratch')],
                                                             'session_pattern': 'sessions/{working_folder}/{session_id}'},
                   'build_roots': [str(boot / 'build')],
                   'plain_repositories': [{'repository': str(named), 'worktree_root': str(boot / 'named-plain-trees')}],
                   'client_accounts': [str(account)],
                   'protect': {'paths': [], 'volumes': [], 'containers': [], 'images': [], 'networks': [],
                               'compose_projects': []}}
        (boot / 'installation').mkdir()
        (boot / 'installation' / 'installation.yaml').write_text(YAML.dump({
            'schema': 'veldo.installation/v1', 'owner': {'display_name': 'Fixture', 'role_id': 'owner'},
            'space': section}))
        (boot / 'state').mkdir()
        boot_conn = S.open_store(str(boot / 'state' / 'store.sqlite3'))
        logged = []
        service = types.SimpleNamespace(
            config={'installation': str(boot / 'installation'), 'state_root': str(boot / 'state'),
                    'store_path': str(boot / 'state' / 'store.sqlite3'), 'host_identity': 'fixture'},
            repositories={'repository': [str(newly)]}, conn=boot_conn, principal='authority',
            sign=lambda data: 'fixture', generation=1, domain='d329', _log=logged.append)
        space = R.bootstrap(service)
        done = {one.get('repository') or one.get('account'): one for one in getattr(service, 'space_hooks', [])}
        check(row, 'the start installs for the bound repository, the named plain repository and the named account: '
              + str(done),
              space is not None and set(done) == {str(newly), str(named), str(account)}
              and all(one.get('ok') is True for one in done.values())
              and all(executable(path / '.git' / 'hooks' / name) for path in (newly, named) for name in R.HOOKS)
              and all(ours_in(account, event) for event in R.SESSION_EVENTS))
        check(row, 'the hooks are told this installation\'s state root, and the keys of the mapping are unchanged',
              told_to(newly, 'veldo.space.stateroot') == str(boot / 'state')
              and told_to(newly, 'veldo.space.installation') == str(boot / 'installation')
              and sorted(space or {}) == ['free', 'keep', 'kinds', 'ledger', 'probe', 'remover'])
        check(row, 'each install is logged with the repository or account folder and the hooks folder used: '
              + str(logged),
              sorted((one['result'].get('repository') or one['result'].get('account'),
                      one['result'].get('hooks_folder') or one['result'].get('settings')) for one in logged
                     if one.get('operation') == 'hook_install')
              == sorted([(str(newly), str(newly / '.git' / 'hooks')), (str(named), str(named / '.git' / 'hooks')),
                         (str(account), str(account / 'settings.json'))]))
    except Exception:
        check('fixture/completed', traceback.format_exc(), False)
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
            child.wait(timeout=5)
        if listener is not None:
            listener.close()
        for one in (conn, boot_conn):
            if one is not None:
                one.close()
        shutil.rmtree(temp)
    for row, values in rows.items():
        failed = [message for message, good in values if not good]
        expect('space329/' + row + (': ' + failed[0] if failed else ''), bool(values) and not failed)


_v329_suite()
