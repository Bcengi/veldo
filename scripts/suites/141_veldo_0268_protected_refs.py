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
        env = dict(ENV, CLAUDE_PROJECT_DIR=str(work), **extra)
        payload = json.dumps({'tool_name': 'Bash', 'tool_input': {'command': command}, 'cwd': str(work)})
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
        'merge/checked-out': row_merge, 'merge/gh-base': row_gh_base,
        'refuse/gate': row_refuse_gate, 'refuse/manifest': row_refuse_manifest, 'refuse/path': row_refuse_path,
        'refuse/debt': row_refuse_debt, 'refuse/objection': row_refuse_objection, 'refuse/tag': row_refuse_tag,
        'refuse/lander': row_refuse_lander,
        'sync/copies': row_copies, 'doc/agents': row_doc,
    }

    # The spec's registered mutations: (name, file, old, new, the row that must go red).
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
    )

    results = {}
    for name, fn in ROWS.items():
        try:
            results[name] = fn(PRODUCTION)
        except Exception as error:  # noqa: BLE001
            results[name] = (False, 'raised %s: %s' % (type(error).__name__, str(error)[:300]))
    for name, module, old, new, row in MUTATIONS:
        label = 'mutation/' + name
        try:
            text = Path(PRODUCTION[module]).read_text()
            if text.count(old) != 1:
                results[label] = (False, 'anchor not found exactly once in %s' % module)
                continue
            mdir = base / ('mut-' + name)
            mdir.mkdir()
            mutated = {k: Path(v) for k, v in PRODUCTION.items()}
            (mdir / module).write_text(text.replace(old, new))
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
