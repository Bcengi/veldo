"""VELDO-0268: the push guard checks only pushes and merges that move a protected ref (main, master,
release branches and tags as the policy declares them in protected_refs) and never blocks a working
branch, while a protected destination keeps every check exactly as before.

Run: python3 scripts/selftest.py --suite 141_veldo_0268_protected_refs

Only shared ROOT and expect are consumed. Each row builds its own fixture repository in a temporary
directory: a working clone carrying this change's guard and policy_check (PRODUCTION) beside the
repository's own yamlish, git_process, verdict_corpus and reuse_evidence, a local bare remote, and,
for the pre-push rows, a git pre-push hook that calls the guard once per ref with VELDO_GUARD_REF and
VELDO_GUARD_COMMIT as core's hook does. The PreToolUse rows feed the guard the hook payload Claude
Code sends and, when the guard lets the command through, run the command, so "the remote has the
branch" is read from the bare remote. gh is a fixture script first on PATH. Real Git throughout.

The refusal rows (AC3) compare the guard's standard error, without its "VELDO guard: destination"
lines, byte for byte with the text the guard and policy_check printed before this change (the
literals below; proof/VELDO-0268/README.md records the run of the pre-change files that produced
them). The mutation rows apply each of the spec's registered mutations to a temporary copy and
require the targeted row to go red, so every falsifier is driven on every run.
"""


def _v268_suite():
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import subprocess
    import tempfile
    import time

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'veldo-guard.sh': ROOT / "scripts" / "veldo-guard.sh",
        'policy_check.py': ROOT / ".veldo" / "policy_check.py",
    }
    under_test = os.environ.get('VELDO_0268_UNDER_TEST')
    if under_test:
        # A diagnostic: the same rows over another pair of files (the pre-change pair, for the proof's
        # red-before run). Never set by the gate.
        PRODUCTION = {name: Path(under_test) / name for name in PRODUCTION}
    SIBLINGS = ('yamlish.py', 'git_process.py', 'verdict_corpus.py', 'reuse_evidence.py')
    ENGINE_REFS = ('refs/heads/main', 'refs/heads/master', 'refs/heads/release', 'refs/heads/release/*',
                   'refs/heads/release-*', 'refs/tags/*')
    started = time.monotonic()
    base = Path(tempfile.mkdtemp(prefix='v268-'))
    home = base / 'home'
    home.mkdir()
    fakebin = base / 'bin'
    fakebin.mkdir()
    gh = fakebin / 'gh'
    gh.write_text('#!/usr/bin/env bash\n'
                  '# fixture gh: "gh pr view ... --json baseRefName" answers $FIXTURE_GH_BASE, or fails\n'
                  'if [ "$1 $2" = "pr view" ] && [ -n "${FIXTURE_GH_BASE:-}" ]; then echo "$FIXTURE_GH_BASE"; exit 0; fi\n'
                  'exit 1\n')
    gh.chmod(0o755)
    ENV = {k: v for k, v in os.environ.items() if not k.startswith(('GIT_', 'VELDO_', 'CLAUDE_'))}
    ENV.update(HOME=str(home), XDG_CONFIG_HOME=str(home / '.config'), GIT_CONFIG_NOSYSTEM='1',
               GIT_AUTHOR_NAME='Fixture', GIT_AUTHOR_EMAIL='fixture@example.invalid',
               GIT_COMMITTER_NAME='Fixture', GIT_COMMITTER_EMAIL='fixture@example.invalid',
               PATH=str(fakebin) + os.pathsep + os.environ.get('PATH', ''))
    counter = [0]

    def git(cwd, *args, ok=True):
        r = subprocess.run(['git'] + list(args), cwd=str(cwd), env=ENV, capture_output=True, text=True)
        if ok and r.returncode != 0:
            raise RuntimeError('git %s: %s' % (' '.join(args), r.stderr.strip()[-300:]))
        return r

    def policy_text(refs=ENGINE_REFS, raw=None):
        text = 'schema: veldo.policy/v1\nversion: 1\nprotected_paths:\n  - {path: "secure/**", floor: high}\n'
        if raw is not None:
            return text + raw
        if refs is not None:
            text += 'protected_refs:\n' + ''.join('  - "%s"\n' % r for r in refs)
        return text

    def fixture(under, refs=ENGINE_REFS, raw=None, touch='app.txt', hook=False):
        """A working clone on main, one commit ahead of its bare remote's main (touching `touch`),
        with agent/claude/x at the same commit, a red gate stamp and no proof manifest."""
        counter[0] += 1
        root = base / ('f%03d' % counter[0])
        bare, work = root / 'remote.git', root / 'work'
        root.mkdir()
        git(root, 'init', '-q', '--bare', '-b', 'main', str(bare))
        git(root, 'init', '-q', '-b', 'main', str(work))
        (work / '.veldo').mkdir()
        (work / 'scripts').mkdir()
        for name in SIBLINGS:
            shutil.copyfile(ROOT / '.veldo' / name, work / '.veldo' / name)
        shutil.copyfile(Path(under['policy_check.py']), work / '.veldo' / 'policy_check.py')
        shutil.copyfile(Path(under['veldo-guard.sh']), work / 'scripts' / 'veldo-guard.sh')
        (work / '.veldo' / 'policy.yaml').write_text(policy_text(refs, raw))
        (work / '.gitignore').write_text('.veldo/last_verify\n.veldo/events.jsonl\nproof/\n')
        (work / 'README').write_text('fixture\n')
        git(work, 'add', '-A')
        git(work, 'commit', '-q', '-m', 'seed')
        git(work, 'remote', 'add', 'origin', str(bare))
        git(work, 'push', '-q', 'origin', 'main')
        path = work / touch
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('change\n')
        git(work, 'add', '-A')
        git(work, 'commit', '-q', '-m', 'change')
        git(work, 'branch', 'agent/claude/x')
        head = git(work, 'rev-parse', 'HEAD').stdout.strip()
        stamp(work, head, 'red')
        if hook:
            h = work / '.git' / 'hooks' / 'pre-push'
            h.write_text('#!/usr/bin/env bash\n'
                         '# fixture pre-push: the guard once per ref, as core\'s hook calls it\n'
                         'while read -r lref lsha rref rsha; do\n'
                         '  VELDO_GUARD_REF="$rref" VELDO_GUARD_COMMIT="$lsha" bash scripts/veldo-guard.sh </dev/null\n'
                         '  rc=$?\n'
                         '  echo "$rref $rc" >> .git/guard-rc\n'
                         '  [ "$rc" = 0 ] || exit "$rc"\n'
                         'done\n')
            h.chmod(0o755)
        return work, bare, head

    def stamp(work, head, status):
        (work / '.veldo' / 'last_verify').write_text(json.dumps(
            {'commit': head, 'status': status, 'reused': {'unit': 0, 'mutation': 0}, 'force_fresh': False}))

    def manifest(work, head):
        d = work / 'proof' / 'VELDO-9000'
        d.mkdir(parents=True, exist_ok=True)
        (d / 'manifest.json').write_text(json.dumps({'spec_id': 'VELDO-9000', 'commit': head}))

    def guard(work, command, **extra):
        cwd = extra.pop('VELDO_0268_CWD', str(work))  # the tool's cwd in the payload (default: the repository)
        env = dict(ENV, CLAUDE_PROJECT_DIR=str(work), **extra)
        payload = json.dumps({'tool_name': 'Bash', 'tool_input': {'command': command}, 'cwd': cwd})
        return subprocess.run(['bash', str(work / 'scripts' / 'veldo-guard.sh')], cwd=str(work), env=env,
                              input=payload, capture_output=True, text=True)

    def through_tool(work, command, **extra):
        """The guard as Claude Code calls it, then the command when the guard lets it through."""
        g = guard(work, command, **extra)
        ran = None
        if g.returncode == 0:
            ran = subprocess.run(['bash', '-c', command], cwd=str(work), env=dict(ENV, **extra),
                                 capture_output=True, text=True)
        return g, ran

    def has(bare, ref):
        return git(bare, 'rev-parse', '--verify', '--quiet', ref, ok=False).returncode == 0

    def checks_text(stderr):
        return ''.join(line for line in stderr.splitlines(True)
                       if not line.startswith('VELDO guard: destination '))

    def protected_lines(stderr):
        return [line for line in stderr.splitlines()
                if line.startswith('VELDO guard: destination ') and 'not protected' not in line]

    def load_check(work):
        counter[0] += 1
        spec = importlib.util.spec_from_file_location('v268_pc_%d' % counter[0], work / '.veldo' / 'policy_check.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def gate_text(head):
        return ('VELDO guard: blocked. The canonical gate is not green for HEAD (%s).\n'
                'Run ./scripts/verify.sh on the current state first. Proof is valid only for the state it ran against.\n'
                % head)

    def manifest_text(head):
        return ('VELDO guard: blocked. No proof manifest found for HEAD (%s).\n'
                'Produce proof/<spec-id>/manifest.json mapping every acceptance criterion to evidence (/veldo:proof).\n'
                % head)

    PATH_TEXT = ('VELDO policy: blocked. Protected path touched with no valid path-scoped approval.\n'
                 '  secure/key.txt  (protected by secure/**)\n'
                 '  Required: an approved, unexpired veldo.approval/v1 whose scope.commit is a\n'
                 '  commit in this push, whose scope.paths covers secure/key.txt, and whose approver\n'
                 '  is not the proof producer (no self-approval).\n')

    def debt_text(at, commit):
        return ('VELDO policy: blocked. An emergency backfill debt is open (emergency.push at %s, commit %s).\n'
                '  Land the backfill (spec + proof + review) or record an emergency.closed event; '
                "the setup's promise is that unclosed debt blocks the next ordinary merge.\n" % (at, commit[:12]))

    OBJECTION_TEXT = ('VELDO policy: blocked. A review objected and the objection is unresolved.\n'
                      '  VELDO-9000: proof/VELDO-9000/verdict.json\n'
                      '    the fix is wrong\n'
                      '  Resolve it the normal way: fix the work, commit, and let the re-review land\n'
                      '  a verdict on the newer commit. A review can object but never approve, so no\n'
                      '  pass verdict is required and none will clear this.\n'
                      '  To override, record an approval bound to a commit in this push, approved by\n'
                      '  someone who is not the proof producer.\n')

    def same(label, got, want):
        return got == want, '%s: got %r, want %r' % (label, got[-400:], want[-400:])

    # ---------------------------------------------------------------- AC1: the declared set
    def row_declared(under):
        work, _, _ = fixture(under)
        pc = load_check(work)
        names = ('refs/heads/main', 'refs/heads/release/1.2', 'refs/tags/v1', 'refs/heads/agent/claude/x',
                 'refs/heads/mainline')
        got = tuple(bool(pc.protected_ref(n)) for n in names)
        return got == (True, True, True, False, False), 'protected_ref over %s: %s' % (names, got)

    def row_union_shrink(under):
        work, _, _ = fixture(under)
        git(work, 'checkout', '-q', 'agent/claude/x')
        (work / '.veldo' / 'policy.yaml').write_text(policy_text(('refs/tags/*',)))
        pc = load_check(work)
        hit = pc.protected_ref('refs/heads/main')
        return bool(hit) and 'refs/heads/main:' in hit[1], 'working tree drops main, trunk lists it: %r' % (hit,)

    def row_no_key(under):
        work, _, _ = fixture(under, refs=None)
        pc = load_check(work)
        hit = pc.protected_ref('refs/heads/agent/claude/x')
        return bool(hit), 'no source declares protected_refs: %r' % (hit,)

    def row_installed(under):
        work, _, _ = fixture(under)
        inst = work.parent / 'installed'
        inst.mkdir()
        (inst / 'policy.yaml').write_text(policy_text(('refs/heads/production',)))
        pc = load_check(work)
        before = pc.protected_ref('refs/heads/production')
        pc.POLICY = inst / 'policy.yaml'
        after = pc.protected_ref('refs/heads/production')
        main = pc.protected_ref('refs/heads/main')
        return (not before and bool(after) and bool(main),
                'installation adds production: before %r, after %r, main %r' % (before, after, main))

    def row_unreadable(under):
        work, _, _ = fixture(under, raw='protected_refs: "refs/heads/main"\n')
        g = guard(work, 'git push origin agent/claude/x')
        want = 'VELDO guard: blocked. protected_refs in %s cannot be read' % (work.resolve() / '.veldo' / 'policy.yaml')
        return g.returncode == 2 and want in g.stderr, 'malformed protected_refs: exit %d, %r' % (g.returncode, g.stderr[-300:])

    # ---------------------------------------------------------------- AC2: working branches pass
    def row_branch_tool(under):
        work, bare, _ = fixture(under)
        g, ran = through_tool(work, 'git push origin agent/claude/x')
        ok = g.returncode == 0 and ran is not None and ran.returncode == 0 and has(bare, 'refs/heads/agent/claude/x')
        return ok, 'red stamp, no manifest, working branch: guard exit %d, %r' % (g.returncode, g.stderr[-300:])

    def row_branch_prepush(under):
        work, bare, _ = fixture(under, hook=True)
        r = git(work, 'push', 'origin', 'agent/claude/x', ok=False)
        rc = (work / '.git' / 'guard-rc').read_text() if (work / '.git' / 'guard-rc').exists() else ''
        ok = r.returncode == 0 and has(bare, 'refs/heads/agent/claude/x') and rc == 'refs/heads/agent/claude/x 0\n'
        return ok, 'pre-push, working branch: push exit %d, guard %r, %r' % (r.returncode, rc, r.stderr[-300:])

    def row_main_tool(under):
        work, bare, head = fixture(under)
        g, _ = through_tool(work, 'git push origin main')
        ok = g.returncode == 2 and checks_text(g.stderr) == gate_text(head)
        moved = git(bare, 'rev-parse', 'refs/heads/main').stdout.strip() == head
        return ok and not moved, 'main through the tool: exit %d, %r' % (g.returncode, g.stderr[-300:])

    def row_main_prepush(under):
        work, bare, head = fixture(under, hook=True)
        r = git(work, 'push', 'origin', 'main', ok=False)
        rc = (work / '.git' / 'guard-rc').read_text() if (work / '.git' / 'guard-rc').exists() else ''
        moved = git(bare, 'rev-parse', 'refs/heads/main').stdout.strip() == head
        ok = r.returncode != 0 and rc == 'refs/heads/main 2\n' and not moved and gate_text(head) in r.stderr
        return ok, 'main through pre-push: push exit %d, guard %r, %r' % (r.returncode, rc, r.stderr[-300:])

    def row_both(under):
        work, bare, head = fixture(under)
        g, _ = through_tool(work, 'git push origin agent/claude/x main')
        prot = protected_lines(g.stderr)
        ok = (g.returncode == 2 and len(prot) == 1 and 'refs/heads/main:' in prot[0]
              and 'destination refs/heads/agent/claude/x: not protected' in g.stderr
              and checks_text(g.stderr) == gate_text(head))
        return ok, 'both refs: exit %d, protected lines %r' % (g.returncode, prot)

    def row_head_colon_main(under):
        work, bare, head = fixture(under)
        git(work, 'checkout', '-q', 'agent/claude/x')
        g, _ = through_tool(work, 'git push origin HEAD:main')
        moved = git(bare, 'rev-parse', 'refs/heads/main').stdout.strip() == head
        return g.returncode == 2 and not moved, 'HEAD:main from a working branch: exit %d, %r' % (g.returncode, g.stderr[-300:])

    def row_unreproducible(under):
        work, _, _ = fixture(under)
        g, _ = through_tool(work, 'cd x && git push')
        return g.returncode == 2, '"cd x && git push": exit %d, %r' % (g.returncode, g.stderr[-300:])

    def row_dry_run_fails(under):
        work, _, _ = fixture(under)
        g, _ = through_tool(work, 'git push nosuchremote agent/claude/x')
        return g.returncode == 2, 'a dry run that fails: exit %d, %r' % (g.returncode, g.stderr[-300:])

    def row_pr_create(under):
        work, _, _ = fixture(under)
        g = guard(work, 'gh pr create --title t --body b')
        return g.returncode == 0, 'gh pr create: exit %d, %r' % (g.returncode, g.stderr[-300:])

    # ------------------------------------------------ fix round 1: quiet, global options, hooks
    def row_quiet_main(under):
        work, bare, head = fixture(under)
        seen = []
        for command in ('git push -q origin main', 'git push --quiet origin main', 'git push -fq origin main'):
            g = guard(work, command)
            seen.append((command, g.returncode, checks_text(g.stderr) == gate_text(head)))
        moved = git(bare, 'rev-parse', 'refs/heads/main').stdout.strip() == head
        ok = all(rc == 2 and text for _, rc, text in seen) and not moved
        return ok, 'quiet pushes of main: %r' % (seen,)

    def row_empty_answer(under):
        """A dry run that succeeds and names no destination: a pattern refspec matching no branch.
        The row holds only when the guard reports that exact reason and refuses on it, so a fixture
        that fails earlier (a dry run that errors or prints a line the guard cannot read) is red
        here rather than green for the wrong reason."""
        work, bare, head = fixture(under)
        g = guard(work, "git push origin 'refs/heads/nomatch/*:refs/heads/nomatch/*'")
        reason = [l for l in g.stderr.splitlines() if l.startswith('VELDO guard: destination unresolved:')]
        want = 'VELDO guard: destination unresolved: the dry run named no destination; treated as protected'
        ok = (g.returncode == 2 and len(reason) == 1 and reason[0].startswith(want)
              and checks_text(g.stderr) == gate_text(head)
              and git(bare, 'rev-parse', 'refs/heads/main').stdout.strip() != head)
        return ok, 'a dry run naming no destination: exit %d, reason %r' % (g.returncode, reason)

    def row_global_main(under):
        work, bare, head = fixture(under)
        seen = []
        for command in ('git -C %s push origin main' % work, 'git -c push.default=simple push origin main'):
            g = guard(work, command)
            seen.append((command, g.returncode, checks_text(g.stderr) == gate_text(head)))
        moved = git(bare, 'rev-parse', 'refs/heads/main').stdout.strip() == head
        ok = all(rc == 2 and text for _, rc, text in seen) and not moved
        return ok, 'global options before the subcommand, main: %r' % (seen,)

    def row_hooks_not_run(under):
        work, bare, _ = fixture(under)
        hooks = work.parent / 'hooks'
        hooks.mkdir()
        marker = work.parent / 'hook-ran'
        (hooks / 'pre-push').write_text('#!/usr/bin/env bash\ntouch "%s"\n' % marker)
        (hooks / 'pre-push').chmod(0o755)
        command = 'git -c core.hooksPath=%s push --verify origin agent/claude/x' % hooks
        g = guard(work, command)
        during = marker.exists()
        ran = subprocess.run(['bash', '-c', command], cwd=str(work), env=ENV, capture_output=True, text=True)
        ok = g.returncode == 0 and not during and ran.returncode == 0 and marker.exists()
        return ok, ('hooks re-enabled by the command: guard exit %d, hook ran in the dry run %s, '
                    'the real push ran it %s' % (g.returncode, during, marker.exists()))

    def row_branch_variants(under):
        work, bare, _ = fixture(under)
        seen = []
        for at, command in enumerate(('git push -q origin agent/claude/x:refs/heads/agent/claude/q',
                                      'git -C %s push origin agent/claude/x:refs/heads/agent/claude/c' % work,
                                      'git -c push.default=simple push origin agent/claude/x:refs/heads/agent/claude/k')):
            g, ran = through_tool(work, command)
            target = 'refs/heads/agent/claude/' + 'qck'[at]
            seen.append((command, g.returncode, ran is not None and ran.returncode == 0 and has(bare, target)))
        ok = all(rc == 0 and pushed for _, rc, pushed in seen)
        return ok, 'working branch pushes with quiet and global options: %r' % (seen,)

    # ------------------------- fix round 3: the guard runs no program the push chooses; aliases
    def program(work, name):
        """A program that must never run while the guard decides: it records that it ran, and fails."""
        path, mark = work.parent / name, work.parent / (name + '-ran')
        path.write_text('#!/bin/sh\ntouch "%s"\nexit 1\n' % mark)
        path.chmod(0o755)
        return path, mark

    def refused_unrun(work, bare, head, calls, marks, want):
        """Each (command, extra environment) exits 2 on the gate text with exactly one unresolved
        line containing `want`, no marker program ran, and the remote's main did not move."""
        seen, ok = [], True
        for command, extra in calls:
            g = guard(work, command, **extra)
            why = [l for l in g.stderr.splitlines() if l.startswith('VELDO guard: destination unresolved:')]
            ran = [m.name for m in marks if m.exists()]
            one = (g.returncode == 2 and not ran and len(why) == 1 and want in why[0]
                   and checks_text(g.stderr) == gate_text(head))
            ok = ok and one
            seen.append((command[:60], g.returncode, ran, why[0][36:120] if why else None))
        moved = git(bare, 'rev-parse', 'refs/heads/main').stdout.strip() == head
        return ok and not moved, 'main moved %s; %r' % (moved, seen)

    def row_program_options(under):
        work, bare, head = fixture(under)
        prog, mark = program(work, 'rp')
        calls = [('git push --receive-pack=%s origin main' % prog, {}),
                 ('git push --exec=%s origin agent/claude/x' % prog, {}),
                 ('git push --rec %s origin agent/claude/x' % prog, {})]
        return refused_unrun(work, bare, head, calls, [mark], 'an option the guard does not reproduce')

    def row_program_config_option(under):
        work, bare, head = fixture(under)
        prog, mark = program(work, 'cp')
        inc = work.parent / 'inc.cfg'
        inc.write_text('[remote "origin"]\n\treceivepack = %s\n' % prog)
        calls = [('git -c remote.origin.receivepack=%s push origin agent/claude/x' % prog, {}),
                 ('git -c core.sshCommand=%s push ssh://127.0.0.1:1/x main' % prog, {}),
                 ('git -c protocol.ext.allow=always push ext::%s agent/claude/x' % prog, {}),
                 ('git -c include.path=%s push origin agent/claude/x' % inc, {})]
        return refused_unrun(work, bare, head, calls, [mark], 'may name a program')

    def row_program_repo_config(under):
        work, bare, head = fixture(under)
        prog, mark = program(work, 'rc')
        git(work, 'config', 'remote.origin.receivepack', str(prog))
        calls = [('git push origin agent/claude/x', {}), ('git push origin main', {})]
        return refused_unrun(work, bare, head, calls, [mark], 'names a receive-pack program')

    def row_ssh_config(under):
        work, bare, head = fixture(under)
        prog, mark = program(work, 'sc')
        git(work, 'config', 'core.sshCommand', str(prog))
        git(work, 'remote', 'add', 's', 'ssh://127.0.0.1:1/x')
        calls = [('git push s agent/claude/x', {}), ('git push s main', {})]
        return refused_unrun(work, bare, head, calls, [mark], 'the dry run failed')

    def row_ssh_env(under):
        work, bare, head = fixture(under)
        prog, mark = program(work, 'se')
        git(work, 'remote', 'add', 's', 'ssh://127.0.0.1:1/x')
        calls = [('git push s agent/claude/x', {'GIT_SSH_COMMAND': str(prog)})]
        return refused_unrun(work, bare, head, calls, [mark], 'the dry run failed')

    def row_ssh_env_git_ssh(under):
        work, bare, head = fixture(under)
        prog, mark = program(work, 'gs')
        git(work, 'remote', 'add', 's', 'ssh://127.0.0.1:1/x')
        calls = [('git push s agent/claude/x', {'GIT_SSH': str(prog)})]
        return refused_unrun(work, bare, head, calls, [mark], 'the dry run failed')

    def row_ext_transport(under):
        work, bare, head = fixture(under)
        ext, ext_mark = program(work, 'ex')
        rem, rem_mark = program(work, 'er')
        rew, rew_mark = program(work, 'ew')
        helper, helper_mark = program(work, 'git-remote-foo')
        git(work, 'config', 'protocol.ext.allow', 'always')
        git(work, 'remote', 'add', 'e', 'ext::%s' % rem)
        git(work, 'config', 'url.ext::%s .pushInsteadOf' % rew, 'zz:')
        path = {'PATH': str(work.parent) + os.pathsep + ENV['PATH']}
        calls = [('git push ext::%s main' % ext, {}), ('git push e agent/claude/x', {}),
                 ('git push zz:q agent/claude/x', {}), ('git push foo::bar agent/claude/x', path)]
        return refused_unrun(work, bare, head, calls, [ext_mark, rem_mark, rew_mark, helper_mark],
                             'the dry run failed')

    def serve(bare=None, tls=False):
        """A fixture smart-http remote that answers 401 without the credential fixture:token and, with
        it, the receive-pack ref advertisement of `bare` (no bare: 401 always). Returns (server, base
        URL). The guard's dry run only reads the advertisement."""
        import base64
        import http.server
        import ssl
        import threading
        token = 'Basic ' + base64.b64encode(b'fixture:token').decode()

        class Remote(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if bare is None or self.headers.get('Authorization') != token:
                    self.send_response(401)
                    self.send_header('WWW-Authenticate', 'Basic realm="fixture"')
                    self.send_header('Content-Length', '0')
                    self.end_headers()
                    return
                if 'service=git-receive-pack' not in self.path:
                    self.send_response(404)
                    self.send_header('Content-Length', '0')
                    self.end_headers()
                    return
                adv = subprocess.run(['git', 'receive-pack', '--stateless-rpc', '--advertise-refs', str(bare)],
                                     env=ENV, capture_output=True).stdout
                head_line = b'# service=git-receive-pack\n'
                body = b'%04x' % (len(head_line) + 4) + head_line + b'0000' + adv
                self.send_response(200)
                self.send_header('Content-Type', 'application/x-git-receive-pack-advertisement')
                self.send_header('Cache-Control', 'no-cache')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                self.send_response(500)
                self.send_header('Content-Length', '0')
                self.end_headers()

            def log_message(self, *args):
                pass

        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Remote)
        scheme = 'http'
        if tls:
            keydir = Path(tempfile.mkdtemp(dir=str(base)))
            subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                            '-subj', '/CN=127.0.0.1', '-keyout', str(keydir / 'k.pem'), '-out', str(keydir / 'c.pem')],
                           env=ENV, capture_output=True, check=True)
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(str(keydir / 'c.pem'), str(keydir / 'k.pem'))
            server.socket = context.wrap_socket(server.socket, server_side=True)
            scheme = 'https'
        threading.Thread(target=server.serve_forever, daemon=True).start()
        return server, '%s://127.0.0.1:%d' % (scheme, server.server_port)

    def stop(server):
        server.shutdown()
        server.server_close()

    def row_credential(under):
        """A credential helper in the repository's own configuration is not run (owner decision
        Telegram 39895): unresolved, with askpass from the repository and the environment unrun."""
        work, bare, head = fixture(under)
        helper, helper_mark = program(work, 'ch')
        ask, ask_mark = program(work, 'ca')
        env_ask, env_ask_mark = program(work, 'ga')
        git(work, 'config', 'credential.helper', '!%s' % helper)
        git(work, 'config', 'core.askPass', str(ask))
        server, root = serve()
        try:
            url = root + '/r.git'
            calls = [('git push %s agent/claude/x' % url, {}),
                     ('git push %s agent/claude/x' % url, {'GIT_ASKPASS': str(env_ask)}),
                     ('git push %s main' % url, {})]
            return refused_unrun(work, bare, head, calls, [helper_mark, ask_mark, env_ask_mark],
                                 'names a credential helper outside the global and system configuration')
        finally:
            stop(server)

    def row_credential_url_scoped(under):
        """A URL-scoped credential.<url>.helper in the repository's configuration is not run."""
        work, bare, head = fixture(under)
        helper, helper_mark = program(work, 'cu')
        server, root = serve()
        try:
            git(work, 'config', 'credential.%s.helper' % root, '!%s' % helper)
            calls = [('git push %s/r.git agent/claude/x' % root, {})]
            return refused_unrun(work, bare, head, calls, [helper_mark],
                                 'names a credential helper outside the global and system configuration')
        finally:
            stop(server)

    def row_credential_command(under):
        """A credential helper on the command line is not run."""
        work, bare, head = fixture(under)
        helper, helper_mark = program(work, 'cc')
        server, root = serve()
        try:
            calls = [('git -c credential.helper=!%s push %s/r.git agent/claude/x' % (helper, root), {}),
                     ('git -c credential.%s.helper=!%s push %s/r.git agent/claude/x' % (root, helper, root), {})]
            return refused_unrun(work, bare, head, calls, [helper_mark], 'may name a program')
        finally:
            stop(server)

    def row_credential_included(under):
        """A helper in a file under the repository is not run, though the global configuration
        includes it (git reports the includer's scope), nor a global configuration file that itself
        lies under the repository."""
        work, bare, head = fixture(under)
        helper, helper_mark = program(work, 'ci')
        inside = work / '.git' / 'cred.cfg'
        inside.write_text('[credential]\n\thelper = !%s\n' % helper)
        outer = work.parent / 'global-inc.cfg'
        outer.write_text('[include]\n\tpath = %s\n' % inside)
        server, root = serve()
        try:
            calls = [('git push %s/r.git agent/claude/x' % root, {'GIT_CONFIG_GLOBAL': str(outer)}),
                     ('git push %s/r.git agent/claude/x' % root, {'GIT_CONFIG_GLOBAL': str(inside)})]
            return refused_unrun(work, bare, head, calls, [helper_mark],
                                 'names a credential helper outside the global and system configuration')
        finally:
            stop(server)

    def row_credential_global(under):
        """A gh-style helper in the global configuration (outside the repository) answers the https
        remote's credential request, so a working-branch push resolves and passes on a red stamp, and
        main to the same remote resolves as protected; askpass from the repository and the environment
        never runs."""
        work, bare, head = fixture(under)
        ask, ask_mark = program(work, 'ra')
        env_ask, env_ask_mark = program(work, 'ea')
        git(work, 'config', 'core.askPass', str(ask))
        gh_mark = work.parent / 'gh-helper-ran'
        gh_helper = work.parent / 'gh-helper'
        gh_helper.write_text('#!/bin/sh\ntouch "%s"\n'
                             'if [ "$1" = get ]; then echo username=fixture; echo password=token; fi\n' % gh_mark)
        gh_helper.chmod(0o755)
        server, root = serve(bare=bare, tls=True)
        try:
            glob = work.parent / 'global.cfg'
            glob.write_text('[credential "%s"]\n\thelper =\n\thelper = !%s\n[http]\n\tsslVerify = false\n'
                            % (root, gh_helper))
            extra = {'GIT_CONFIG_GLOBAL': str(glob), 'GIT_ASKPASS': str(env_ask)}
            g = guard(work, 'git push %s/r.git agent/claude/x' % root, **extra)
            branch = (g.returncode == 0 and 'destination refs/heads/agent/claude/x: not protected' in g.stderr
                      and 'destination unresolved' not in g.stderr)
            m = guard(work, 'git push %s/r.git main' % root, **extra)
            prot = protected_lines(m.stderr)
            main = (m.returncode == 2 and len(prot) == 1 and 'destination refs/heads/main:' in prot[0]
                    and checks_text(m.stderr) == gate_text(head))
            # A remote the global helper does not cover: git would fall back to askpass, which never runs.
            other, other_root = serve()
            try:
                n = guard(work, 'git push %s/r.git agent/claude/x' % other_root, **extra)
            finally:
                stop(other)
            uncovered = n.returncode == 2 and 'destination unresolved: the dry run failed' in n.stderr
            unrun = not ask_mark.exists() and not env_ask_mark.exists()
            moved = git(bare, 'rev-parse', 'refs/heads/main').stdout.strip() == head
            ok = branch and main and uncovered and gh_mark.exists() and unrun and not moved
            return ok, ('global helper over https: branch exit %d %r; main exit %d %r; uncovered remote exit %d; '
                        'helper ran %s; askpass unrun %s' % (g.returncode, g.stderr[-300:], m.returncode, prot,
                                                             n.returncode, gh_mark.exists(), unrun))
        finally:
            stop(server)

    def row_vcs(under):
        """remote.<name>.vcs names a remote helper program; it never runs."""
        work, bare, head = fixture(under)
        helper, helper_mark = program(work, 'git-remote-vv')
        git(work, 'config', 'remote.v.vcs', 'vv')
        git(work, 'config', 'remote.v.url', 'somewhere')
        path = {'PATH': str(work.parent) + os.pathsep + ENV['PATH']}
        calls = [('git push v agent/claude/x', path), ('git push v main', path)]
        return refused_unrun(work, bare, head, calls, [helper_mark], 'the dry run failed')

    def row_alias(under):
        work, bare, head = fixture(under)
        git(work, 'config', 'alias.pm', 'push origin main')
        git(work, 'config', 'alias.q', 'pm')
        git(work, 'config', 'alias.sp', '!git push origin main')
        git(work, 'config', 'alias.pb', 'push origin agent/claude/x:refs/heads/agent/claude/a')
        seen = []
        for command in ('git -c alias.p=push p origin main', 'git pm', 'git q', 'git sp', 'cd . && git pm'):
            g = guard(work, command)
            seen.append((command, g.returncode, checks_text(g.stderr) == gate_text(head)))
        g, ran = through_tool(work, 'git pb')
        branch = g.returncode == 0 and ran is not None and has(bare, 'refs/heads/agent/claude/a')
        moved = git(bare, 'rev-parse', 'refs/heads/main').stdout.strip() == head
        ok = all(rc == 2 and text for _, rc, text in seen) and branch and not moved
        return ok, 'aliases to push: %r; working-branch alias lands %s; main moved %s' % (seen, branch, moved)

    def row_alias_elsewhere(under):
        """The alias is looked up in the repository the command runs in, not the tool's cwd: from a cwd
        outside the repository (whose configuration has no alias p), each command naming the
        repository's alias p = push refuses on the gate text; a builtin after a cd still passes."""
        work, bare, head = fixture(under)
        git(work, 'config', 'alias.p', 'push')
        other = work.parent / 'elsewhere'
        other.mkdir()
        seen = []
        for command in ('cd %s && git p origin main' % work, 'true; git -C %s p origin main' % work,
                        'git -C %s p origin main' % work, 'GIT_DIR=%s/.git git p origin main' % work,
                        'git --git-dir=%s/.git p origin main' % work):
            g = guard(work, command, VELDO_0268_CWD=str(other))
            seen.append((command[-40:], g.returncode, checks_text(g.stderr) == gate_text(head)))
        builtin = guard(work, 'cd %s && git status' % work, VELDO_0268_CWD=str(other))
        moved = git(bare, 'rev-parse', 'refs/heads/main').stdout.strip() == head
        ok = all(rc == 2 and text for _, rc, text in seen) and builtin.returncode == 0 and not moved
        return ok, 'alias p in the repository, cwd outside it: %r; cd then git status exit %d' % (
            seen, builtin.returncode)

    # ------------------------- fix round 5: pushes that set an upstream; alias lookups that fail
    def row_set_upstream(under):
        """A working-branch push that sets an upstream (-u, the long option, -u origin HEAD, a plain
        push with push.autoSetupRemote configured or given with -c) passes on a red stamp and lands; the
        same -u to main still meets the gate."""
        work, bare, head = fixture(under)
        gcfg = work.parent / 'global.cfg'
        gcfg.write_text('[push]\n\tautoSetupRemote = true\n')
        seen = []
        for command, branch, target, extra in (
                ('git push -u origin agent/claude/x', None, 'x', {}),
                ('git push --set-upstream origin agent/claude/x:refs/heads/agent/claude/s', None, 's', {}),
                ('git push -u origin HEAD', 'agent/claude/h', 'h', {}),
                ('git push', 'agent/claude/p', 'p', {'GIT_CONFIG_GLOBAL': str(gcfg)}),
                ('git -c push.autoSetupRemote=true push', 'agent/claude/c', 'c', {})):
            if branch:
                git(work, 'checkout', '-q', '-b', branch)
            g, ran = through_tool(work, command, **extra)
            landed = ran is not None and ran.returncode == 0 and has(bare, 'refs/heads/agent/claude/' + target)
            seen.append((command, g.returncode, landed, 'unresolved' in g.stderr))
        git(work, 'checkout', '-q', 'main')
        main = guard(work, 'git push -u origin main')
        moved = git(bare, 'rev-parse', 'refs/heads/main').stdout.strip() == head
        ok = (all(rc == 0 and landed and not unres for _, rc, landed, unres in seen)
              and main.returncode == 2 and checks_text(main.stderr) == gate_text(head)
              and 'protected by' in main.stderr and not moved)
        return ok, 'pushes setting an upstream: %r; -u to main exit %d; main moved %s' % (
            seen, main.returncode, moved)

    def row_alias_unreadable(under):
        """An alias lookup that cannot run or read the configuration, or a -C value the shell expands,
        makes the subcommand unresolved, never "no alias": each refuses on the gate text; builtins with
        the same -C value pass."""
        work, bare, head = fixture(under)
        git(work, 'config', 'alias.pm', 'push origin main')
        git(work, 'config', 'alias.p', 'push')
        gcfg = work.parent / 'global.cfg'
        gcfg.write_text('[alias]\n\tgp = push origin main\n')
        other = work.parent / 'elsewhere'
        other.mkdir()
        (other / '$D').mkdir()  # the literal -C value exists where the guard runs, and has no alias
        missing = work.parent / 'missing'
        seen = []
        for command, cwd, extra in (
                ('git -C "$PWD" pm', work, {}),
                ('D=%s; git -C $D p origin main' % work, other, {}),
                ('for d in %s; do git -C $d p origin main; done' % work, other, {}),
                ('git -C "$PWD" gp', work, {'GIT_CONFIG_GLOBAL': str(gcfg)}),
                ('git -C %s pm' % missing, work, {}),
                ('true; git -C %s pm' % missing, work, {})):
            g = guard(work, command, VELDO_0268_CWD=str(cwd), **extra)
            seen.append((command[-36:], g.returncode, checks_text(g.stderr) == gate_text(head)))
        builtins = [guard(work, c).returncode for c in ('git -C "$PWD" status', 'git -C "$PWD" log -1')]
        moved = git(bare, 'rev-parse', 'refs/heads/main').stdout.strip() == head
        ok = all(rc == 2 and text for _, rc, text in seen) and builtins == [0, 0] and not moved
        return ok, 'alias lookups that fail or are expanded: %r; builtins %r; main moved %s' % (
            seen, builtins, moved)

    def row_alias_shell_c(under):
        """A simple command whose first word is not git has its text judged for aliases: sh -c and
        bash -c running an alias that pushes main refuse on the gate text; sh -c 'git status' passes."""
        work, bare, head = fixture(under)
        git(work, 'config', 'alias.pm', 'push origin main')
        git(work, 'config', 'alias.p', 'push')
        seen = []
        for command in ("sh -c 'git pm'", 'bash -c "git p origin main"'):
            g = guard(work, command)
            seen.append((command, g.returncode, checks_text(g.stderr) == gate_text(head)))
        plain = guard(work, "sh -c 'git status'")
        moved = git(bare, 'rev-parse', 'refs/heads/main').stdout.strip() == head
        ok = all(rc == 2 and text for _, rc, text in seen) and plain.returncode == 0 and not moved
        return ok, 'aliases under sh -c and bash -c: %r; sh -c git status exit %d' % (seen, plain.returncode)

    # ---------------------------------------------------------------- merges
    def row_merge(under):
        work, _, head = fixture(under)
        on_main = guard(work, 'git merge agent/claude/x')
        git(work, 'checkout', '-q', 'agent/claude/x')
        on_branch = guard(work, 'git merge main')
        ok = (on_main.returncode == 2 and checks_text(on_main.stderr) == gate_text(head)
              and on_branch.returncode == 0)
        return ok, 'merge on main exit %d, on a working branch exit %d' % (on_main.returncode, on_branch.returncode)

    def row_gh_base(under):
        work, _, head = fixture(under)
        into_main = guard(work, 'gh pr merge 7 --squash', FIXTURE_GH_BASE='main')
        into_branch = guard(work, 'gh pr merge 7 --squash', FIXTURE_GH_BASE='agent/claude/y')
        unknown = guard(work, 'gh pr merge 7 --squash')
        ok = (into_main.returncode == 2 and checks_text(into_main.stderr) == gate_text(head)
              and into_branch.returncode == 0 and unknown.returncode == 2)
        return ok, 'gh pr merge into main %d, into a branch %d, base unknown %d' % (
            into_main.returncode, into_branch.returncode, unknown.returncode)

    # ---------------------------------------------------------------- AC3: protected refusals unchanged
    def row_refuse_gate(under):
        work, _, head = fixture(under)
        g = guard(work, 'git push origin main')
        return same('red stamp', (str(g.returncode), checks_text(g.stderr)), ('2', gate_text(head)))

    def row_refuse_manifest(under):
        work, _, head = fixture(under)
        stamp(work, head, 'green')
        g = guard(work, 'git push origin main')
        return same('no manifest', (str(g.returncode), checks_text(g.stderr)), ('2', manifest_text(head)))

    def row_refuse_path(under):
        work, _, head = fixture(under, touch='secure/key.txt')
        stamp(work, head, 'green')
        manifest(work, head)
        g = guard(work, 'git push origin main')
        return same('protected path', (str(g.returncode), checks_text(g.stderr)), ('2', PATH_TEXT))

    def row_refuse_debt(under):
        work, _, head = fixture(under)
        stamp(work, head, 'green')
        manifest(work, head)
        at = '2026-11-06T00:00:00Z'
        (work / '.veldo' / 'events.jsonl').write_text(json.dumps(
            {'schema': 'veldo.event/v1', 'type': 'emergency.push', 'commit': head, 'at': at,
             'producer': 'veldo-guard'}) + '\n')
        g = guard(work, 'git push origin main')
        return same('emergency debt', (str(g.returncode), checks_text(g.stderr)), ('2', debt_text(at, head)))

    def row_refuse_objection(under):
        work, _, head = fixture(under)
        stamp(work, head, 'green')
        manifest(work, head)
        (work / 'proof' / 'VELDO-9000' / 'verdict.json').write_text(json.dumps(
            {'spec_id': 'VELDO-9000', 'commit': head, 'verdict': 'rework',
             'findings': {'blocking': ['the fix is wrong']}}))
        g = guard(work, 'git push origin main')
        return same('objection', (str(g.returncode), checks_text(g.stderr)), ('2', OBJECTION_TEXT))

    def row_refuse_tag(under):
        work, bare, head = fixture(under, touch='secure/key.txt')
        stamp(work, head, 'green')
        manifest(work, head)
        git(work, 'tag', 'v1')
        g, _ = through_tool(work, 'git push origin v1')
        ok = g.returncode == 2 and checks_text(g.stderr) == PATH_TEXT and not has(bare, 'refs/tags/v1')
        return ok, 'tag push touching a protected path: exit %d, %r' % (g.returncode, g.stderr[-300:])

    def row_refuse_lander(under):
        work, _, head = fixture(under, touch='secure/key.txt')
        inst = work.parent / 'installed' / '.veldo'
        inst.mkdir(parents=True)
        for name in SIBLINGS:
            shutil.copyfile(ROOT / '.veldo' / name, inst / name)
        shutil.copyfile(Path(under['policy_check.py']), inst / 'policy_check.py')
        (inst / 'policy.yaml').write_text(policy_text())
        trunk = git(work, 'rev-parse', 'origin/main').stdout.strip()
        r = subprocess.run(['python3', str(ROOT / '.veldo' / 'control_verification.py'), 'policy',
                            str(inst / 'policy_check.py'), str(work), trunk],
                           cwd=str(work), env=ENV, capture_output=True, text=True)
        return same('lander', (str(r.returncode), r.stdout), ('1', PATH_TEXT))

    # ---------------------------------------------------------------- AC4
    def row_copies(under):
        guards = [(ROOT / p).read_bytes() for p in ('scripts/veldo-guard.sh', 'engine/scripts/veldo-guard.sh',
                                                     'packs/claude/scripts/veldo-guard.sh')]
        checks = [(ROOT / p).read_bytes() for p in ('.veldo/policy_check.py', 'engine/.veldo/policy_check.py')]
        return len(set(guards)) == 1 and len(set(checks)) == 1, 'three guards and two policy_checks byte-identical'

    def row_doc(under):
        text = ' '.join((ROOT / 'engine' / 'AGENTS.md').read_text().split())
        need = ('the push guard protects the refs the policy names', 'Landing is where the gate and approvals bind',
                'Working branches push freely')
        missing = [n for n in need if n not in text]
        return not missing, 'engine/AGENTS.md protected refs paragraph, missing %r' % missing

    ROWS = {
        'refs/declared': row_declared, 'refs/union-shrink': row_union_shrink, 'refs/no-key': row_no_key,
        'refs/installed': row_installed, 'refs/unreadable': row_unreadable,
        'push/branch-tool': row_branch_tool, 'push/branch-prepush': row_branch_prepush,
        'push/main-tool': row_main_tool, 'push/main-prepush': row_main_prepush, 'push/both': row_both,
        'push/head-colon-main': row_head_colon_main, 'push/unreproducible': row_unreproducible,
        'push/dry-run-fails': row_dry_run_fails, 'push/pr-create': row_pr_create,
        'push/quiet-main': row_quiet_main, 'push/empty-answer': row_empty_answer,
        'push/global-options-main': row_global_main, 'push/hooks-not-run': row_hooks_not_run,
        'push/branch-variants': row_branch_variants,
        'push/program-options': row_program_options, 'push/program-config-option': row_program_config_option,
        'push/program-repo-config': row_program_repo_config, 'push/ssh-config': row_ssh_config,
        'push/ssh-env': row_ssh_env, 'push/ssh-env-git-ssh': row_ssh_env_git_ssh,
        'push/ext-transport': row_ext_transport, 'push/credential': row_credential, 'push/alias': row_alias,
        'push/credential-url-scoped': row_credential_url_scoped, 'push/credential-command': row_credential_command,
        'push/credential-included': row_credential_included, 'push/credential-global': row_credential_global,
        'push/vcs': row_vcs, 'push/alias-elsewhere': row_alias_elsewhere,
        'push/set-upstream': row_set_upstream, 'push/alias-unreadable': row_alias_unreadable,
        'push/alias-shell-c': row_alias_shell_c,
        'merge/checked-out': row_merge, 'merge/gh-base': row_gh_base,
        'refuse/gate': row_refuse_gate, 'refuse/manifest': row_refuse_manifest, 'refuse/path': row_refuse_path,
        'refuse/debt': row_refuse_debt, 'refuse/objection': row_refuse_objection, 'refuse/tag': row_refuse_tag,
        'refuse/lander': row_refuse_lander,
        'sync/copies': row_copies, 'doc/agents': row_doc,
    }

    # Fix round 1 anchors, shared with scripts/check_teeth_mutations.py's registration of the same defects.
    FORCED_LINE = 'FORCED = ["--no-quiet", "--dry-run", "--porcelain", "--no-verify"]\n'
    FORCED_LINE_DEFECT = 'FORCED = ["--dry-run", "--porcelain", "--no-verify"]  # defect: quiet is not overridden\n'
    EMPTY_CHECK = '    if not found:\n        return unresolved("the dry run named no destination")\n'
    EMPTY_CHECK_DEFECT = ('    if False:  # defect: a dry run naming no destination is allowed\n'
                          '        return unresolved("the dry run named no destination")\n')
    TRIGGER = "grep -qE '(git|gh pr (merge|create))'"
    TRIGGER_DEFECT = "grep -qE '(git (push|merge)|gh pr (merge|create))'"
    DRY_RUN_CALL = ('        r = subprocess.run(["git"] + kept + ["-c", "core.hooksPath=/dev/null", "push"]\n'
                    '                           + rest[:end] + FORCED + rest[end:],\n')
    DRY_RUN_CALL_DEFECT = ('        r = subprocess.run(["git", "-c", "core.hooksPath=/dev/null"] + kept\n'
                           '                           + ["push", "--dry-run", "--porcelain", "--no-verify"] + rest,\n')
    # Fix round 3 anchors, shared with scripts/check_teeth_mutations.py's registration of the same defects.
    PUSH_OPTION_CHECK = '            if name not in PUSH_LONG:\n'
    PUSH_OPTION_CHECK_DEFECT = '            if False:  # defect: every push option is reproduced\n'
    KEY_CHECK = '    if unsafe:\n'
    KEY_CHECK_DEFECT = '    if False:  # defect: every -c key is reproduced\n'
    RECEIVEPACK_CHECK = '    problem = configured_program(kept, cwd, env)\n'
    RECEIVEPACK_CHECK_DEFECT = "    problem = None  # defect: the configuration's receive-pack runs\n"
    SSH_PIN = 'PINNED = ["core.sshCommand=" + SSH,\n'
    SSH_PIN_DEFECT = 'PINNED = [  # defect: the ssh command is not pinned\n'
    ENV_FILTER = '           if not (k.startswith("GIT_") and k not in GIT_ENV_KEPT) and k != "SSH_ASKPASS"}\n'
    ENV_FILTER_DEFECT = '           if True}  # defect: the environment chooses programs\n'
    PROTOCOLS = '    env["GIT_ALLOW_PROTOCOL"] = "file:ssh:http:https"\n'
    PROTOCOLS_DEFECT = '    pass  # defect: every transport is allowed\n'
    ASKPASS_PIN = '          "core.askPass=",\n'
    ASKPASS_PIN_DEFECT = '          # defect: askpass is not pinned\n'
    # Fix round 4 anchors, shared with scripts/check_teeth_mutations.py's registration of the same defects.
    CREDENTIAL_CHECK = '    problem = credential_program(kept, cwd, env)\n'
    CREDENTIAL_CHECK_DEFECT = '    problem = None  # defect: any credential helper runs\n'
    CREDENTIAL_KEYS = '                                         r"^credential\\..*helper$"],\n'
    CREDENTIAL_KEYS_DEFECT = '                                         r"^credential\\.helper$"],  # defect: URL-scoped missed\n'
    CREDENTIAL_PATH = '                or any(real == d or real.startswith(d.rstrip("/") + "/") for d in repo)):\n'
    CREDENTIAL_PATH_DEFECT = '                or False):  # defect: a file under the repository counts as global\n'
    CREDENTIAL_GLOBAL_PIN_DEFECT = '          "credential.helper=",  # defect: the global helper is pinned off\n' + ASKPASS_PIN
    CREDENTIAL_SCOPE = '        if (scope not in ("global", "system") or not real\n'
    CREDENTIAL_SCOPE_DEFECT = '        if (scope not in ("system",) or not real  # defect: global is refused\n'
    ALIAS_C = '            value = None if sub in ("push", "merge") else alias_of(kept, sub, cwd)\n'
    ALIAS_C_DEFECT = '            value = None if sub in ("push", "merge") else alias_of([], sub, cwd)  # defect: cwd only\n'
    ALIAS_CD = '        if split is None or ELSEWHERE.search(command[:match.start()]):\n'
    ALIAS_CD_DEFECT = '        if split is None:  # defect: a cd before git is ignored\n'
    ALIAS_PREFIX = '    elsewhere = git_globals(words) is None or any("=" in w or w == "env" for w in prefix)\n'
    ALIAS_PREFIX_DEFECT = '    elsewhere = False  # defect: an assignment or option before the subcommand is ignored\n'
    ALIAS_EXPAND = '        value = None if sub in (None, "push", "merge") else alias_of(kept, sub, cwd)\n'
    ALIAS_EXPAND_DEFECT = '        value = None  # defect: aliases are not expanded\n'
    ALIAS_TEXT = ('        return unresolved("a git alias that may push or merge, in a command the guard cannot '
                  'reproduce")\n')
    ALIAS_TEXT_DEFECT = '        pass  # defect: an alias in a compound command is not judged\n'
    # Fix round 5 anchors, shared with scripts/check_teeth_mutations.py's registration of the same defects.
    UPSTREAM_LINE = ('        elif not (line.startswith("To ") or line == "Done" or not line.strip() '
                     'or UPSTREAM.fullmatch(line)):\n')
    UPSTREAM_LINE_DEFECT = ('        elif not (line.startswith("To ") or line == "Done" or not line.strip()):'
                            '  # defect: the upstream line is unread\n')
    LOOKUP_FAILS = '        raise AliasUnreadable(sub)\n'
    LOOKUP_FAILS_DEFECT = '        return None  # defect: a lookup that cannot run reads as no alias\n'
    EXPANDED_C = '            split = None  # a -C or -c value the shell expands: where git runs is not known\n'
    EXPANDED_C_DEFECT = '            pass  # defect: an expanded -C value is looked up as written\n'
    SHELL_C = ('            return unresolved("a git alias that may push or merge, in a command whose first word '
               'is not git")\n')
    SHELL_C_DEFECT = '            pass  # defect: a command whose first word is not git is not alias-checked\n'

    # The spec's registered mutations: (name, file, old, new, the row that must go red[, further
    # (old, new) replacements in the same file]).
    MUTATIONS = (
        ('ac1-union-reads-only-tree', 'policy_check.py',
         '    if trunk.returncode == 0 and trunk.stdout.strip():\n',
         '    if False:  # defect: the union reads only the working tree\n', 'refs/union-shrink'),
        ('ac1-missing-key-protects-nothing', 'policy_check.py',
         '        return (EVERY_REF, "no policy declares protected_refs")\n',
         '        return None  # defect: no protected_refs key means nothing is protected\n', 'refs/no-key'),
        ('ac2-destination-from-text', 'veldo-guard.sh',
         '    if sub == "push":\n        return dry_run(kept, rest, cwd)\n',
         '    if sub == "push":\n        return [("refs/heads/" + rest[-1].split(":")[0], None)]  # defect: read the text\n',
         'push/head-colon-main'),
        ('ac2-unresolved-unprotected', 'veldo-guard.sh',
         '            log("unresolved", "%s; treated as protected; %s" % (reason, CHECKS))\n'
         '            protected.append("unresolved")\n',
         '            log("unresolved", reason)  # defect: an unresolved destination is unprotected\n',
         'push/unreproducible'),
        ('ac3-tags-skip-approval', 'veldo-guard.sh',
         'if [ -f .veldo/policy_check.py ]; then\n',
         'if [ -f .veldo/policy_check.py ] && ! printf \'%s\\n\' "$JUDGED" | grep -q \'^refs/tags/\'; then\n',
         'refuse/tag'),
        # Fix round 1: a quiet push, global options before the subcommand, hooks re-enabled by the command.
        ('fix1-quiet-silences-answer', 'veldo-guard.sh', FORCED_LINE, FORCED_LINE_DEFECT, 'push/quiet-main',
         ((EMPTY_CHECK, EMPTY_CHECK_DEFECT),)),
        ('fix1-empty-answer-allowed', 'veldo-guard.sh', EMPTY_CHECK, EMPTY_CHECK_DEFECT, 'push/empty-answer'),
        ('fix1-trigger-misses-global-options', 'veldo-guard.sh', TRIGGER, TRIGGER_DEFECT,
         'push/global-options-main'),
        ('fix1-hooks-path-before-globals', 'veldo-guard.sh', DRY_RUN_CALL, DRY_RUN_CALL_DEFECT,
         'push/hooks-not-run'),
        ('fix1-quiet-not-overridden', 'veldo-guard.sh', FORCED_LINE, FORCED_LINE_DEFECT, 'push/branch-variants'),
        # Fix round 3: the guard's dry run runs no program the command, configuration or environment chooses.
        ('fix3-push-option-allowlist-off', 'veldo-guard.sh', PUSH_OPTION_CHECK, PUSH_OPTION_CHECK_DEFECT,
         'push/program-options'),
        ('fix3-config-key-allowlist-off', 'veldo-guard.sh', KEY_CHECK, KEY_CHECK_DEFECT, 'push/program-config-option'),
        ('fix3-configured-receivepack-runs', 'veldo-guard.sh', RECEIVEPACK_CHECK, RECEIVEPACK_CHECK_DEFECT,
         'push/program-repo-config'),
        ('fix3-ssh-command-not-pinned', 'veldo-guard.sh', SSH_PIN, SSH_PIN_DEFECT, 'push/ssh-config'),
        ('fix3-environment-chooses-programs', 'veldo-guard.sh', ENV_FILTER, ENV_FILTER_DEFECT, 'push/ssh-env'),
        ('fix3-git-ssh-reaches-dry-run', 'veldo-guard.sh', ENV_FILTER, ENV_FILTER_DEFECT, 'push/ssh-env-git-ssh',
         ((SSH_PIN, SSH_PIN_DEFECT),)),
        ('fix3-every-transport-allowed', 'veldo-guard.sh', PROTOCOLS, PROTOCOLS_DEFECT, 'push/ext-transport'),
        ('fix3-askpass-runs', 'veldo-guard.sh', ASKPASS_PIN, ASKPASS_PIN_DEFECT, 'push/credential-global'),
        ('fix3-alias-not-expanded', 'veldo-guard.sh', ALIAS_EXPAND, ALIAS_EXPAND_DEFECT, 'push/alias'),
        ('fix3-alias-in-text-ignored', 'veldo-guard.sh', ALIAS_TEXT, ALIAS_TEXT_DEFECT, 'push/alias'),
        # Fix round 4: credential helpers only from the global or system configuration; vcs helpers;
        # aliases looked up where the command runs.
        ('fix4-repository-helper-runs', 'veldo-guard.sh', CREDENTIAL_CHECK, CREDENTIAL_CHECK_DEFECT, 'push/credential'),
        ('fix4-url-scoped-helper-missed', 'veldo-guard.sh', CREDENTIAL_KEYS, CREDENTIAL_KEYS_DEFECT,
         'push/credential-url-scoped'),
        ('fix4-command-line-helper-runs', 'veldo-guard.sh', KEY_CHECK, KEY_CHECK_DEFECT, 'push/credential-command',
         ((CREDENTIAL_CHECK, CREDENTIAL_CHECK_DEFECT),)),
        ('fix4-included-helper-under-repository-runs', 'veldo-guard.sh', CREDENTIAL_PATH, CREDENTIAL_PATH_DEFECT,
         'push/credential-included'),
        ('fix4-global-helper-pinned-off', 'veldo-guard.sh', ASKPASS_PIN, CREDENTIAL_GLOBAL_PIN_DEFECT,
         'push/credential-global'),
        ('fix4-global-helper-refused', 'veldo-guard.sh', CREDENTIAL_SCOPE, CREDENTIAL_SCOPE_DEFECT,
         'push/credential-global'),
        ('fix4-vcs-helper-runs', 'veldo-guard.sh', PROTOCOLS, PROTOCOLS_DEFECT, 'push/vcs'),
        ('fix4-alias-ignores-dash-c', 'veldo-guard.sh', ALIAS_C, ALIAS_C_DEFECT, 'push/alias-elsewhere'),
        ('fix4-alias-ignores-cd', 'veldo-guard.sh', ALIAS_CD, ALIAS_CD_DEFECT, 'push/alias-elsewhere'),
        ('fix4-alias-ignores-prefix', 'veldo-guard.sh', ALIAS_PREFIX, ALIAS_PREFIX_DEFECT, 'push/alias-elsewhere'),
        # Fix round 5: the upstream line is read; a failed or expanded alias lookup is unresolved; sh -c.
        ('fix5-upstream-line-unread', 'veldo-guard.sh', UPSTREAM_LINE, UPSTREAM_LINE_DEFECT, 'push/set-upstream'),
        ('fix5-lookup-failure-is-no-alias', 'veldo-guard.sh', LOOKUP_FAILS, LOOKUP_FAILS_DEFECT,
         'push/alias-unreadable'),
        ('fix5-expanded-dash-c-looked-up', 'veldo-guard.sh', EXPANDED_C, EXPANDED_C_DEFECT, 'push/alias-unreadable'),
        ('fix5-shell-c-not-alias-checked', 'veldo-guard.sh', SHELL_C, SHELL_C_DEFECT, 'push/alias-shell-c'),
    )

    results = {}
    for name, fn in ROWS.items():
        try:
            results[name] = fn(PRODUCTION)
        except Exception as error:  # noqa: BLE001
            results[name] = (False, 'raised %s: %s' % (type(error).__name__, str(error)[:300]))
    for name, module, old, new, row, *also in MUTATIONS:
        label = 'mutation/' + name
        try:
            text = Path(PRODUCTION[module]).read_text()
            pairs = ((old, new),) + (also[0] if also else ())
            if any(text.count(o) != 1 for o, _ in pairs):
                results[label] = (False, 'anchor not found exactly once in %s' % module)
                continue
            for o, n in pairs:
                text = text.replace(o, n)
            mdir = base / ('mut-' + name)
            mdir.mkdir()
            mutated = {k: Path(v) for k, v in PRODUCTION.items()}
            (mdir / module).write_text(text)
            mutated[module] = mdir / module
            red, detail = ROWS[row](mutated)
            results[label] = (not red, 'row %s under the mutation: %s (%s)' % (row, 'red' if not red else 'green', detail))
        except Exception as error:  # noqa: BLE001
            results[label] = (False, 'raised %s: %s' % (type(error).__name__, str(error)[:300]))
    shutil.rmtree(base, ignore_errors=True)
    for name, (ok, detail) in results.items():
        if not ok or os.environ.get('VELDO_0268_DETAILS'):
            print('  VELDO-0268 %s %s: %s' % (name, 'observed' if ok else 'detail', detail))
        expect('VELDO-0268 ' + name + ('' if ok else ': ' + detail[:300]), ok)
    print('VELDO-0268 suite seconds: %.3f' % (time.monotonic() - started))


_v268_suite()
