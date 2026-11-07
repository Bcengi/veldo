"""VELDO-0272: owner approval narrows to money, authentication and security, schema and irreversible
infrastructure; routine work lands on a green gate and a recorded independent review; the owner gets a daily
summary of what landed.

Only ROOT and expect are consumed. Each declared falsifier is registered twice: with the gate's mutation
driver (scripts/check_teeth_mutations.py, finding 272), which hands this suite a mutated copy of
.veldo/policy.yaml, policy_check.py or landed_summary.py through the three file names below, and as an in-suite
row that applies the mutation to a temporary copy and checks the baseline green and the mutant red. The
modules under test always run from a temporary .veldo tree (every .veldo/*.py and policy.yaml copied, the one
named file taken from its path below), so a mutant the driver supplies is the module the rows load. Real Git
throughout: scratch repositories with the real .veldo/policy.yaml, real commits, real policy_check.main().
"""


def _v272_suite():
    import contextlib
    import hashlib
    import importlib.util
    import io
    import json
    import os
    from pathlib import Path
    import re
    import shutil
    import tempfile
    import time

    started = time.monotonic()
    ROWS = ('AC1 policy/lists-match', 'AC1 policy/tiers-and-start', 'AC1 policy/engine-identical',
            'AC1 mutation/gate-legs-added-back', 'AC1 mutation/policy-check-removed',
            'AC1 push/test-machinery-no-approval', 'AC1 push/authorization-needs-approval',
            'AC2 flag/fixtures', 'AC2 flag/before-start-valid', 'AC2 mutation/reverse-direction-dropped',
            'AC3 lowered/flip', 'AC3 review/landing', 'AC3 mutation/reviewer-comparison-skipped',
            'AC3 executor/computed-flag',
            'AC3 lowered/rename', 'AC3 lowered/two-step', 'AC3 lowered/delete-re-add', 'AC3 lowered/merge',
            'AC3 review/producer-identity', 'AC3 review/per-spec',
            'AC4 summary/file', 'AC4 summary/registry-identical', 'AC4 mutation/reviewer-dropped',
            'AC4 summary/every-landing', 'AC4 summary/judged-fields')
    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @contextlib.contextmanager
    def section(prefix):
        """One acceptance criterion's rows: an exception reds that criterion's rows only."""
        try:
            yield
        except Exception as error:  # noqa: BLE001
            for row in ROWS:
                if row.startswith(prefix):
                    check(row, 'ran to its end (raised %s: %s)' % (type(error).__name__, str(error)[:300]), False)

    # The files the gate's mutation driver may replace (its anchors; written once each, in this form only).
    POLICY_FILE = ROOT / ".veldo" / "policy.yaml"
    PC_FILE = ROOT / ".veldo" / "policy_check.py"
    LS_FILE = ROOT / ".veldo" / "landed_summary.py"
    GP = load('v272_git_process', ROOT / '.veldo' / 'git_process.py')
    Y = load('v272_yamlish', ROOT / '.veldo' / 'yamlish.py')
    POLICY_TEXT = Path(POLICY_FILE).read_text()

    def git(root, *args, date=None):
        if date:
            # The Git boundary strips every GIT_ variable, so a dated fixture commit (the committer date
            # is the day a landing reached main) runs Git directly with its own clean environment.
            import subprocess
            env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
            env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date, GIT_CONFIG_GLOBAL=os.devnull,
                       GIT_CONFIG_NOSYSTEM='1', GIT_AUTHOR_NAME='fixture', GIT_AUTHOR_EMAIL='fixture@example.invalid',
                       GIT_COMMITTER_NAME='fixture', GIT_COMMITTER_EMAIL='fixture@example.invalid')
            r = subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True, env=env)
        else:
            r = GP.run(['git', '-C', str(root), *args], identity=('fixture', 'fixture@example.invalid'),
                       capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError('git %s: %s' % (' '.join(args), r.stderr.strip()[:300]))
        return r.stdout.strip()

    def write(root, rel, text):
        target = Path(root) / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def commit(root, message, date=None):
        git(root, 'add', '-A')
        git(root, 'commit', '-qm', message, date=date)
        return git(root, 'rev-parse', 'HEAD')

    def new_repo(base, name, policy=POLICY_TEXT):
        root = Path(base) / name
        root.mkdir(parents=True)
        git(root, 'init', '-q', '-b', 'main')
        git(root, 'config', 'commit.gpgsign', 'false')
        write(root, '.veldo/policy.yaml', policy)
        write(root, 'README.md', 'fixture\n')
        return root

    def module_tree(base, name, overlay):
        """A copy of .veldo/*.py and policy.yaml with `overlay` (file name: source path) laid over it; returns
        its .veldo directory. The modules under test load their siblings beside themselves and from their
        ROOT's .veldo, so they run from such a tree."""
        tree = Path(base) / name / '.veldo'
        tree.mkdir(parents=True)
        for source in (ROOT / '.veldo').glob('*.py'):
            shutil.copyfile(source, tree / source.name)
        shutil.copyfile(ROOT / '.veldo' / 'policy.yaml', tree / 'policy.yaml')
        for file_name, source in overlay.items():
            shutil.copyfile(source, tree / file_name)
        return tree

    def mutant_tree(base, name, module, old, new):
        """A copy of .veldo/*.py with one module changed; returns its .veldo directory, or None when the
        anchor is absent (a mutation that cannot apply is a red row, never a silent pass)."""
        tree = module_tree(base, name, {})
        text = (tree / module).read_text()
        if old not in text:
            return None
        (tree / module).write_text(text.replace(old, new, 1))
        return tree

    def spec_text(sid, approval, footprint=None, risk='standard', areas=None, title='fixture spec'):
        lines = ['---', 'schema: veldo.spec/v1', 'id: %s' % sid, 'title: %s' % title, 'status: ready',
                 'risk: %s' % risk, 'owner: fixture', 'human_approval: %s' % approval]
        if areas is not None:
            lines.append('risk_areas: [%s]' % ', '.join(areas))
        if footprint is not None:
            lines.append('footprint:')
            lines += ['  - "%s"' % f for f in footprint]
        lines += ['acceptance_criteria:', '  - id: AC1', '    text: fixture', '---', '', 'Body.', '']
        return '\n'.join(lines)

    def run_main(P, root):
        real = P.ROOT
        out = io.StringIO()
        try:
            P.ROOT = root
            with contextlib.redirect_stdout(out):
                code = P.main()
        finally:
            P.ROOT = real
        return code, out.getvalue()

    # ---------------------------------------------------------------- AC1
    spec_path = sorted((ROOT / 'specs').glob('VELDO-0272-*.md'))[0]
    stext = spec_path.read_text()

    def block(start, end):
        a = stext.index(start)
        return stext[a:stext.index(end, a)]

    PATH = re.compile(r'(?:engine/)?(?:\.veldo|scripts)/[A-Za-z0-9_./*-]*[A-Za-z0-9_*]')
    kept = set(PATH.findall(block('Protected paths kept', 'Protected paths removed')))
    removed = set(PATH.findall(block('Protected paths removed', 'Protected paths added')))
    added = set(PATH.findall(block('Protected paths added', 'Schema and irreversible')))
    expected = kept | added | {'engine/' + p for p in added}
    forbidden = removed | {'engine/' + p for p in removed}
    policy = Y.read(Path(POLICY_FILE))

    def lists_match(rows_):
        paths = [r.get('path') for r in rows_]
        return (sorted(paths) == sorted(expected) and len(paths) == len(set(paths))
                and all(r.get('floor') == 'high' for r in rows_) and not (set(paths) & forbidden))

    prot = policy.get('protected_paths') or []
    check('AC1 policy/lists-match', 'the Design section names %d kept, %d added (each with its engine copy), '
          '%d removed' % (len(kept), len(added), len(removed)), len(kept) == 11 and len(added) == 17 and len(removed) == 29)
    check('AC1 policy/lists-match', 'protected_paths is exactly kept and added, each floor high, none removed '
          '[extra %s, missing %s]' % (sorted({r['path'] for r in prot} - expected), sorted(expected - {r['path'] for r in prot})),
          lists_match(prot))
    tiers = policy.get('risk_tiers') or {}
    start = str((policy.get('approval_scope') or {}).get('from_commit', ''))
    check('AC1 policy/tiers-and-start', 'high no longer needs the owner, critical still does',
          str(tiers.get('high', {}).get('human_approval')) == 'false'
          and str(tiers.get('critical', {}).get('human_approval')) == 'true')
    resolved = GP.run(['git', '-C', str(ROOT), 'cat-file', '-e', start + '^{commit}'], capture_output=True)
    check('AC1 policy/tiers-and-start', 'approval_scope.from_commit is a full commit id of this repository [%s]' % start[:12],
          re.fullmatch(r'[0-9a-f]{40}', start) is not None and resolved.returncode == 0)
    check('AC1 policy/engine-identical', 'engine/.veldo/policy_check.py is byte-identical',
          (ROOT / '.veldo/policy_check.py').read_bytes() == (ROOT / 'engine/.veldo/policy_check.py').read_bytes())
    check('AC1 mutation/gate-legs-added-back', 'baseline green', lists_match(prot))
    check('AC1 mutation/gate-legs-added-back', 'mutant red: scripts/gate_legs.py added back',
          not lists_match(prot + [{'path': 'scripts/gate_legs.py', 'floor': 'high'}]))
    check('AC1 mutation/policy-check-removed', 'baseline green', lists_match(prot))
    check('AC1 mutation/policy-check-removed', 'mutant red: .veldo/policy_check.py removed',
          not lists_match([r for r in prot if r.get('path') != '.veldo/policy_check.py']))

    def exercise(base):
        pc_tree = module_tree(base, 'pc', {'policy_check.py': PC_FILE})
        P = load('v272_policy_check', pc_tree / 'policy_check.py')
        V = load('v272_validate', pc_tree / 'validate.py')

        with section('AC1 push'):
            # AC1 push rows: a test machinery path needs nothing; an authentication path needs the owner.
            for name, rel, want in (('legs', 'scripts/gate_legs.py', 0), ('auth', '.veldo/authorization.py', 1)):
                repo = new_repo(base, 'push-' + name)
                commit(repo, 'base')
                git(repo, 'update-ref', 'refs/remotes/origin/main', 'HEAD')
                write(repo, rel, '# changed\n')
                commit(repo, 'change ' + rel)
                code, out = run_main(P, repo)
                row = 'AC1 push/test-machinery-no-approval' if want == 0 else 'AC1 push/authorization-needs-approval'
                check(row, 'a commit touching only %s with no approval exits %d [%d: %s]' % (rel, want, code, out.strip()[:160]),
                      code == want and (want == 0 or rel in out))

        with section('AC2'):
            # AC2: fixture specs after the start commit, and one committed before it.
            def flag_repo(where, Vmod):
                repo = new_repo(where, 'flags')
                write(repo, 'specs/VELDO-9101-old.md', spec_text('VELDO-9101', 'not_required', ['.veldo/policy_check.py']))
                first = commit(repo, 'old spec')
                text = POLICY_TEXT if 'approval_scope:' in POLICY_TEXT else POLICY_TEXT + 'approval_scope:\n  from_commit: x\n'
                write(repo, '.veldo/policy.yaml', re.sub(r'(approval_scope:\n  from_commit: )\S+', r'\g<1>' + first, text))
                commit(repo, 'start line')
                fixtures = {
                    1: ('not_required', ['.veldo/policy_check.py'], 'standard', None),
                    2: ('not_required', ['scripts/**'], 'standard', None),
                    3: ('not_required', ['docs/**'], 'standard', ['money']),
                    4: ('required', ['docs/**'], 'standard', None),
                    5: ('not_required', ['docs/**'], 'standard', None),
                    6: ('not_required', None, 'standard', None),
                    7: ('required', ['docs/**'], 'critical', None),
                }
                results = {}
                for n, (flag, fp, risk, areas) in fixtures.items():
                    rel = 'specs/VELDO-92%02d-fixture.md' % n
                    write(repo, rel, spec_text('VELDO-92%02d' % n, flag, fp, risk, areas))
                    out = io.StringIO()
                    with contextlib.redirect_stdout(out):
                        errs = Vmod.check_approval_scope(repo / rel, Y.front_matter((repo / rel).read_text()), repo)
                    results[n] = (errs, out.getvalue())
                out = io.StringIO()
                old = repo / 'specs/VELDO-9101-old.md'
                with contextlib.redirect_stdout(out):
                    results['old'] = (Vmod.check_approval_scope(old, Y.front_matter(old.read_text()), repo), out.getvalue())
                return results

            under_scripts = [p for p in P.protected_patterns() if p.startswith('scripts/')]

            def fixture2_ok(res):
                errs, out = res[2]
                return errs > 0 and 'approval_flag_below_rule' in out and all(
                    'protected path %s ' % p in out for p in under_scripts) and bool(under_scripts)

            res = flag_repo(Path(base) / 'v', V)
            e = {n: res[n] for n in res}
            check('AC2 flag/fixtures', '(1) footprint .veldo/policy_check.py, not_required: refused naming it [%s]' % e[1][1].strip()[:200],
                  e[1][0] > 0 and 'approval_flag_below_rule' in e[1][1] and 'protected path .veldo/policy_check.py' in e[1][1])
            check('AC2 flag/fixtures', '(2) footprint scripts/**, not_required: refused naming every protected path under '
                  'scripts/ %s' % under_scripts, fixture2_ok(res))
            check('AC2 flag/fixtures', '(3) docs/**, risk_areas [money], not_required: refused naming money',
                  e[3][0] > 0 and 'risk area money' in e[3][1])
            check('AC2 flag/fixtures', '(4) docs/**, required: valid [%s]' % e[4][1].strip()[:120], e[4][0] == 0)
            check('AC2 flag/fixtures', '(5) docs/**, not_required: valid [%s]' % e[5][1].strip()[:120], e[5][0] == 0)
            check('AC2 flag/fixtures', '(6) no footprint, not_required: refused', e[6][0] > 0 and 'footprint absent' in e[6][1])
            check('AC2 flag/fixtures', '(7) critical, no risk_areas: refused', e[7][0] > 0 and 'critical_without_area' in e[7][1])
            check('AC2 flag/before-start-valid', 'the (1) shape committed before the start commit is valid [%s]' % res['old'][1].strip()[:120],
                  res['old'][0] == 0)
            with tempfile.TemporaryDirectory(prefix='v272-mut-', dir=base) as mut:
                tree = mutant_tree(mut, 'm', 'policy_check.py', 'return glob_covers(a, b) or glob_covers(b, a)',
                                   'return glob_covers(a, b)')
                check('AC2 mutation/reverse-direction-dropped', 'baseline green: (2) refused', fixture2_ok(res))
                if tree is None:
                    check('AC2 mutation/reverse-direction-dropped', 'the mutation anchor is present', False)
                else:
                    mres = flag_repo(Path(mut) / 'r', load('v272_validate_mut', tree / 'validate.py'))
                    check('AC2 mutation/reverse-direction-dropped', 'mutant red: (2) no longer refused [%s]' % mres[2][1].strip()[:120],
                          not fixture2_ok(mres))

        with section('AC3'):
            # AC3: lowered flags and the review a not-required landing needs.
            def manifest(sid, producer='builder', checks=('unit',)):
                m = {'schema': 'veldo.proof/v1', 'spec_id': sid, 'commit': 'f' * 40, 'producer': producer,
                     'criteria': [{'id': 'AC1', 'status': 'passed', 'evidence': [{'type': 'unit'}]}],
                     'checks': [{'name': c} for c in checks], 'rollback': 'revert'}
                if producer is None:
                    del m['producer']
                return m

            def verdict(sid, at, reviewer, digest):
                return {'schema': 'veldo.verdict/v1', 'spec_id': sid, 'commit': at, 'reviewer': reviewer,
                        'verdict': 'pass', 'criteria': [], 'findings': {'blocking': [], 'non_blocking': []},
                        'proof_digest': digest}

            def flip_case(where, approver):
                repo = new_repo(where, 'flip-%s' % (approver or 'none'))
                sid, rel = 'VELDO-9301', 'specs/VELDO-9301-flip.md'
                write(repo, rel, spec_text(sid, 'required', ['docs/**']))
                m = manifest(sid)
                write(repo, 'proof/%s/manifest.json' % sid, json.dumps(m))
                commit(repo, 'base')
                git(repo, 'update-ref', 'refs/remotes/origin/main', 'HEAD')
                write(repo, rel, spec_text(sid, 'not_required', ['docs/**']))
                flip = commit(repo, 'lower the flag')
                write(repo, 'proof/%s/verdict.json' % sid, json.dumps(verdict(sid, flip, 'reviewer', P.proof_digest(m))))
                if approver:
                    write(repo, 'proof/%s/approval-owner.json' % sid, json.dumps({
                        'schema': 'veldo.approval/v1', 'id': 'A-9301', 'decision': 'approved', 'approver': approver,
                        'scope': {'commit': flip, 'paths': [rel]}, 'recorded_at': '2026-11-07T00:00:00Z',
                        'expires_at': '2099-01-01T00:00:00Z'}))
                commit(repo, 'evidence')
                return run_main(P, repo)

            code, out = flip_case(Path(base) / 'f1', None)
            check('AC3 lowered/flip', 'required to not_required with no approval: exit 1 naming the spec file [%s]' % out.strip()[:160],
                  code == 1 and 'approval_flag_lowered' in out and 'specs/VELDO-9301-flip.md' in out)
            code, out = flip_case(Path(base) / 'f2', 'owner')
            check('AC3 lowered/flip', 'the same with an owner approval scoping it: exit 0 [%s]' % out.strip()[:160], code == 0)
            code, out = flip_case(Path(base) / 'f3', 'builder')
            check('AC3 lowered/flip', 'an approval whose approver is the producer: exit 1 [%s]' % out.strip()[:160],
                  code == 1 and 'approval_flag_lowered' in out)

            def landing_case(where, Pmod, reviewer, stale=False, producer='builder'):
                repo = new_repo(where, 'land-%s-%s' % ('x' if reviewer else 'none', stale))
                commit(repo, 'base')
                git(repo, 'update-ref', 'refs/remotes/origin/main', 'HEAD')
                sid = 'VELDO-9302'
                m = manifest(sid, producer=producer)
                write(repo, 'docs/guide.md', 'routine\n')
                write(repo, 'specs/VELDO-9302-docs.md', spec_text(sid, 'not_required', ['docs/**']))
                write(repo, 'proof/%s/manifest.json' % sid, json.dumps(m))
                change = commit(repo, 'docs change')
                if reviewer:
                    digest = Pmod.proof_digest(manifest(sid, producer=producer, checks=('unit', 'older')) if stale else m)
                    write(repo, 'proof/%s/verdict.json' % sid, json.dumps(verdict(sid, change, reviewer, digest)))
                    commit(repo, 'review')
                return run_main(Pmod, repo)

            def review_rows(where, Pmod):
                return {'none': landing_case(where / 'a', Pmod, None),
                        'self': landing_case(where / 'b', Pmod, 'builder'),
                        'other': landing_case(where / 'c', Pmod, 'reviewer'),
                        'stale': landing_case(where / 'd', Pmod, 'reviewer', stale=True)}

            r = review_rows(Path(base) / 'l', P)
            check('AC3 review/landing', 'docs only, not required, no verdict: exit 1 landing_without_review [%s]' % r['none'][1].strip()[:120],
                  r['none'][0] == 1 and 'landing_without_review' in r['none'][1])
            check('AC3 review/landing', 'a pass verdict whose reviewer is the producer: exit 1', r['self'][0] == 1
                  and 'landing_without_review' in r['self'][1])
            check('AC3 review/landing', 'a pass verdict from another reviewer bound to the commit and digest: exit 0 [%s]'
                  % r['other'][1].strip()[:160], r['other'][0] == 0)
            check('AC3 review/landing', 'the same verdict with a stale proof digest: exit 1', r['stale'][0] == 1)
            with tempfile.TemporaryDirectory(prefix='v272-mut-', dir=base) as mut:
                tree = mutant_tree(mut, 'm', 'policy_check.py',
                                   'if producer is not None and _self_review(v.get("reviewer"), producer):',
                                   'if False:')
                check('AC3 mutation/reviewer-comparison-skipped', 'baseline green: the self-reviewed landing is refused',
                      r['self'][0] == 1)
                if tree is None:
                    check('AC3 mutation/reviewer-comparison-skipped', 'the mutation anchor is present', False)
                else:
                    PM = load('v272_policy_check_mut', tree / 'policy_check.py')
                    code, out = landing_case(Path(mut) / 'x', PM, 'builder')
                    check('AC3 mutation/reviewer-comparison-skipped', 'mutant red: the self-reviewed landing exits %d' % code, code != 1)

            # F1: a lowering is judged by spec id, between the push base and HEAD and per commit against
            # every parent; an unreadable value counts as required. One row per evasion.
            def owner_approval(repo, sid, bound, paths=None, spec_id=None, name='approval-owner.json', approver='owner'):
                scope = {'commit': bound}
                if paths is not None:
                    scope['paths'] = paths
                if spec_id is not None:
                    scope['spec_id'] = spec_id
                write(repo, 'proof/%s/%s' % (sid, name), json.dumps({
                    'schema': 'veldo.approval/v1', 'id': 'A-%s' % sid, 'decision': 'approved', 'approver': approver,
                    'scope': scope, 'recorded_at': '2026-11-07T00:00:00Z', 'expires_at': '2099-01-01T00:00:00Z'}))

            def lowered(code, out):
                return code == 1 and 'approval_flag_lowered' in out

            def lower_base(where, name, sid, rel, base_text=None):
                repo = new_repo(where, name)
                write(repo, rel, base_text if base_text is not None else spec_text(sid, 'required', ['docs/**']))
                write(repo, 'proof/%s/manifest.json' % sid, json.dumps(manifest(sid)))
                commit(repo, 'base')
                git(repo, 'update-ref', 'refs/remotes/origin/main', 'HEAD')
                return repo

            BROKEN = 'no front matter here\n'

            def rename_case(where, Pmod, approved):
                sid, old, new = 'VELDO-9311', 'specs/VELDO-9311-before.md', 'specs/VELDO-9311-after.md'
                repo = lower_base(where, 'rename-%s' % approved, sid, old)
                git(repo, 'mv', old, new)
                write(repo, new, spec_text(sid, 'not_required', ['docs/**']))
                c = commit(repo, 'rename and lower')
                if approved:
                    owner_approval(repo, sid, c, paths=[old, new])
                    write(repo, 'proof/%s/verdict.json' % sid, json.dumps(verdict(sid, c, 'reviewer', Pmod.proof_digest(manifest(sid)))))
                    commit(repo, 'evidence')
                return run_main(Pmod, repo)

            def break_only_case(where, Pmod):
                sid, rel = 'VELDO-9312', 'specs/VELDO-9312-two.md'
                repo = lower_base(where, 'break', sid, rel)
                write(repo, rel, BROKEN)
                commit(repo, 'step one: the front matter breaks')
                return run_main(Pmod, repo)

            def base_unreadable_case(where, Pmod):
                sid, rel = 'VELDO-9313', 'specs/VELDO-9313-two.md'
                repo = lower_base(where, 'base-unreadable', sid, rel, base_text=BROKEN)
                write(repo, rel, spec_text(sid, 'not_required', ['docs/**']))
                commit(repo, 'step two: not_required over a base that cannot be read')
                return run_main(Pmod, repo)

            def two_step_case(where, Pmod):
                sid, rel = 'VELDO-9314', 'specs/VELDO-9314-two.md'
                repo = lower_base(where, 'two-step', sid, rel)
                write(repo, rel, BROKEN)
                commit(repo, 'step one')
                write(repo, rel, spec_text(sid, 'not_required', ['docs/**']))
                commit(repo, 'step two')
                return run_main(Pmod, repo)

            def delete_case(where, Pmod, readd):
                sid, rel = 'VELDO-9315', 'specs/VELDO-9315-gone.md'
                repo = lower_base(where, 'delete-%s' % readd, sid, rel)
                git(repo, 'rm', '-q', rel)
                commit(repo, 'delete the spec')
                if readd:
                    write(repo, 'specs/VELDO-9315-back.md', spec_text(sid, 'not_required', ['docs/**']))
                    commit(repo, 're-add it not required')
                return run_main(Pmod, repo)

            def merge_case(where, Pmod, preexisting):
                sid, rel = 'VELDO-9316', 'specs/VELDO-9316-merge.md'
                if preexisting:
                    repo = lower_base(where, 'merge-pre', sid, rel)
                else:
                    repo = new_repo(where, 'merge-new')
                    commit(repo, 'base')
                    git(repo, 'update-ref', 'refs/remotes/origin/main', 'HEAD')
                    write(repo, rel, spec_text(sid, 'required', ['docs/**']))
                    write(repo, 'proof/%s/manifest.json' % sid, json.dumps(manifest(sid)))
                    commit(repo, 'add the spec, required')
                git(repo, 'checkout', '-q', '-b', 'side')
                write(repo, 'docs/side.md', 'side\n')
                commit(repo, 'side work')
                git(repo, 'checkout', '-q', 'main')
                write(repo, 'docs/main.md', 'main\n')
                commit(repo, 'main work')
                git(repo, 'merge', '-q', '--no-ff', '--no-commit', 'side')
                write(repo, rel, spec_text(sid, 'not_required', ['docs/**']))
                commit(repo, 'merge side, lowering the flag in the merge itself')
                return run_main(Pmod, repo)

            def lowering_rows(where, Pmod):
                return {'rename': rename_case(where / 'r1', Pmod, False),
                        'rename-approved': rename_case(where / 'r2', Pmod, True),
                        'break': break_only_case(where / 't1', Pmod),
                        'base-unreadable': base_unreadable_case(where / 't2', Pmod),
                        'two-step': two_step_case(where / 't3', Pmod),
                        'delete': delete_case(where / 'd1', Pmod, False),
                        'delete-re-add': delete_case(where / 'd2', Pmod, True),
                        'merge-new': merge_case(where / 'm1', Pmod, False),
                        'merge-pre': merge_case(where / 'm2', Pmod, True)}

            lw = lowering_rows(Path(base) / 'lw', P)
            check('AC3 lowered/rename', 'rename and lower in one commit, no approval: exit 1 naming both files [%s]' % lw['rename'][1].strip()[:200],
                  lowered(*lw['rename']) and 'VELDO-9311-before.md' in lw['rename'][1] and 'VELDO-9311-after.md' in lw['rename'][1])
            check('AC3 lowered/rename', 'the same with an owner approval scoping both names and a review: exit 0 [%s]'
                  % lw['rename-approved'][1].strip()[:200], lw['rename-approved'][0] == 0)
            check('AC3 lowered/two-step', 'a push that only breaks a required spec\'s front matter: exit 1 [%s]' % lw['break'][1].strip()[:160],
                  lowered(*lw['break']))
            check('AC3 lowered/two-step', 'not_required over a push base whose value cannot be read: exit 1 [%s]'
                  % lw['base-unreadable'][1].strip()[:160], lowered(*lw['base-unreadable']))
            check('AC3 lowered/two-step', 'both steps in one push: exit 1', lowered(*lw['two-step']))
            check('AC3 lowered/delete-re-add', 'a push that deletes a required spec: exit 1 [%s]' % lw['delete'][1].strip()[:160],
                  lowered(*lw['delete']))
            check('AC3 lowered/delete-re-add', 'delete then re-add not_required under another name: exit 1',
                  lowered(*lw['delete-re-add']))
            check('AC3 lowered/merge', 'a merge commit lowering a spec added required in the range: exit 1 [%s]'
                  % lw['merge-new'][1].strip()[:160], lowered(*lw['merge-new']))
            check('AC3 lowered/merge', 'a merge commit lowering a spec required at the push base: exit 1',
                  lowered(*lw['merge-pre']))

            # F2: no producer recorded refuses every review; identities are compared normalized.
            ident = {'no-producer': landing_case(Path(base) / 'i1', P, 'reviewer', producer=None),
                     'dict-self': landing_case(Path(base) / 'i2', P, {'model': 'builder', 'context': 'fresh'}),
                     'case-self': landing_case(Path(base) / 'i3', P, '  BUILDER '),
                     'dict-other': landing_case(Path(base) / 'i4', P, {'model': 'other-model', 'context': 'fresh'})}
            check('AC3 review/producer-identity', 'a manifest with no producer: exit 1 landing_without_review [%s]'
                  % ident['no-producer'][1].strip()[:160], ident['no-producer'][0] == 1 and 'landing_without_review' in ident['no-producer'][1])
            check('AC3 review/producer-identity', 'a reviewer stored as a mapping naming the producer: exit 1',
                  ident['dict-self'][0] == 1 and 'landing_without_review' in ident['dict-self'][1])
            check('AC3 review/producer-identity', 'the producer in other case and spacing: exit 1',
                  ident['case-self'][0] == 1 and 'landing_without_review' in ident['case-self'][1])
            check('AC3 review/producer-identity', 'a mapping reviewer naming someone else: exit 0 [%s]' % ident['dict-other'][1].strip()[:160],
                  ident['dict-other'][0] == 0)

            # F5: the review is judged per spec, whatever else the push carries; a required spec needs the
            # owner approval and the review.
            def per_spec_case(where, Pmod, name, specs, protected=False):
                """specs: {sid: (flag, with_verdict, with_approval)} carried in one push."""
                repo = new_repo(where, 'per-' + name)
                commit(repo, 'base')
                git(repo, 'update-ref', 'refs/remotes/origin/main', 'HEAD')
                write(repo, 'docs/guide.md', 'routine\n')
                for sid, (flag, _v, _a) in specs.items():
                    write(repo, 'specs/%s-per.md' % sid, spec_text(sid, flag, ['docs/**']))
                    write(repo, 'proof/%s/manifest.json' % sid, json.dumps(manifest(sid)))
                if protected:
                    write(repo, '.veldo/authorization.py', '# changed\n')
                c = commit(repo, 'change')
                for sid, (_f, with_verdict, with_approval) in specs.items():
                    if with_verdict:
                        write(repo, 'proof/%s/verdict.json' % sid, json.dumps(verdict(sid, c, 'reviewer', Pmod.proof_digest(manifest(sid)))))
                    if with_approval:
                        owner_approval(repo, sid, c, spec_id=sid)
                if protected:
                    owner_approval(repo, 'VELDO-9399', c, paths=['.veldo/authorization.py'])
                commit(repo, 'evidence')
                return run_main(Pmod, repo)

            def per_spec_rows(where, Pmod):
                A, B = 'VELDO-9321', 'VELDO-9322'
                return {'with-required': per_spec_case(where, Pmod, 'a', {A: ('not_required', False, False), B: ('required', True, True)}),
                        'with-protected': per_spec_case(where, Pmod, 'b', {A: ('not_required', False, False)}, protected=True),
                        'required-no-review': per_spec_case(where, Pmod, 'c', {B: ('required', False, True)}),
                        'required-no-approval': per_spec_case(where, Pmod, 'd', {B: ('required', True, False)}),
                        'required-both': per_spec_case(where, Pmod, 'e', {B: ('required', True, True)}),
                        'all-complete': per_spec_case(where, Pmod, 'f', {A: ('not_required', True, False), B: ('required', True, True)})}

            ps = per_spec_rows(Path(base) / 'ps', P)
            check('AC3 review/per-spec', 'a not-required spec with no verdict beside a required spec: exit 1 naming it [%s]'
                  % ps['with-required'][1].strip()[:160],
                  ps['with-required'][0] == 1 and 'landing_without_review: VELDO-9321' in ps['with-required'][1])
            check('AC3 review/per-spec', 'a not-required spec with no verdict beside an approved protected path: exit 1 [%s]'
                  % ps['with-protected'][1].strip()[:160],
                  ps['with-protected'][0] == 1 and 'landing_without_review: VELDO-9321' in ps['with-protected'][1])
            check('AC3 review/per-spec', 'a required spec with the owner approval and no review: exit 1 [%s]'
                  % ps['required-no-review'][1].strip()[:160],
                  ps['required-no-review'][0] == 1 and 'landing_without_review: VELDO-9322' in ps['required-no-review'][1])
            check('AC3 review/per-spec', 'a required spec with a review and no owner approval: exit 1 [%s]'
                  % ps['required-no-approval'][1].strip()[:160],
                  ps['required-no-approval'][0] == 1 and 'owner approval missing: VELDO-9322' in ps['required-no-approval'][1])
            check('AC3 review/per-spec', 'a required spec with both: exit 0 [%s]' % ps['required-both'][1].strip()[:160],
                  ps['required-both'][0] == 0)
            check('AC3 review/per-spec', 'both specs complete in one push: exit 0 [%s]' % ps['all-complete'][1].strip()[:160],
                  ps['all-complete'][0] == 0)

            EX = load('v272_executor', ROOT / '.veldo' / 'executor.py')
            hooks = EX.LiveLoop.__new__(EX.LiveLoop)
            ok_docs = hooks.merge_ready({'human_approval': 'not_required', 'footprint': ['docs/**']}, None, None)
            lied = hooks.merge_ready({'human_approval': 'not_required', 'footprint': ['.veldo/policy_check.py']}, None, None)
            check('AC3 executor/computed-flag', 'merge_ready: docs/** not_required is ready; a protected footprint declared '
                  'not_required is not [%s]' % (lied,), ok_docs[0] is True and lied[0] is False and 'rule' in lied[1])

        with section('AC4'):
            # AC4: four landings over two days, the file, the registry text and the reviewer mutation.
            def summary_repo(where):
                repo = new_repo(where, 'landed')
                commit(repo, 'base', date='2026-11-05T09:00:00+00:00')
                events = []
                plan = (('VELDO-9401', 'required', 'owner', 'rev-a', '2026-11-06T10:00:00+00:00'),
                        ('VELDO-9402', 'not_required', None, 'rev-b', '2026-11-06T12:00:00+00:00'),
                        ('VELDO-9403', 'not_required', None, 'rev-c', '2026-11-06T15:00:00+00:00'),
                        ('VELDO-9404', 'not_required', None, 'rev-d', '2026-11-07T09:00:00+00:00'))
                landed = {}
                for sid, flag, approver, reviewer, date in plan:
                    write(repo, 'specs/%s-x.md' % sid, spec_text(sid, flag, ['docs/**'], title='Ticket %s title' % sid))
                    write(repo, 'docs/%s.md' % sid, 'x\n')
                    c = commit(repo, '%s: build' % sid, date=date)
                    events.append({'type': 'gate.passed', 'commit': c})
                    write(repo, '.veldo/events.jsonl', ''.join(json.dumps(ev) + '\n' for ev in events))
                    m = manifest(sid)
                    write(repo, 'proof/%s/manifest.json' % sid, json.dumps(m))
                    write(repo, 'proof/%s/verdict.json' % sid, json.dumps(verdict(sid, c, reviewer, PD(m))))
                    if approver:
                        write(repo, 'proof/%s/approval-owner.json' % sid, json.dumps({'decision': 'approved', 'approver': approver,
                                                                                    'scope': {'commit': c}}))
                    landed[sid] = commit(repo, '%s landing: evidence' % sid, date=date)
                return repo, landed

            def summary_rows(where, LSmod, TRmod):
                repo, landed = summary_repo(where)
                t1 = LSmod.write_day(repo, '2026-11-06')[0].read_text()
                t2 = LSmod.write_day(repo, '2026-11-07')[0].read_text()
                t0 = LSmod.write_day(repo, '2026-11-08')[0].read_text()
                shipped = [{'type': 'spec.shipped', 'spec': sid, 'commit': landed[sid]} for sid in ('VELDO-9401', 'VELDO-9402', 'VELDO-9403')]
                source = TRmod.Reporter.daily_source(None, '2026-11-06', shipped, repo)
                message, _reply = TRmod.Reporter.render(None, source, TRmod.TEXT.counters())
                return t1, t2, t0, message

            def file_ok(t1, t2, t0):
                lines1 = t1.splitlines()
                return (lines1[0] == 'Veldo landed on 2026-11-06: 3 (approval required 1, not required 2)'
                        and len(lines1) == 4
                        and [l.split()[1] for l in lines1[1:]] == ['VELDO-9401', 'VELDO-9402', 'VELDO-9403']
                        and all(('reviewer rev-%s' % k) in t1 for k in 'abc') and 'Ticket VELDO-9401 title' in t1
                        and 'approval required, approved by owner' in lines1[1] and 'approval not required' in lines1[2]
                        and all('gate green at ' in l for l in lines1[1:])
                        and len(t2.splitlines()) == 2 and 'VELDO-9404' in t2 and 'reviewer rev-d' in t2
                        and t0 == 'Veldo landed on 2026-11-08: nothing landed.')

            def registry_ok(t1, message):
                return message == t1 and 'reviewer rev-a' in message

            PD = P.proof_digest
            ls_tree = module_tree(base, 'ls', {'landed_summary.py': LS_FILE})
            LS = load('v272_landed', ls_tree / 'landed_summary.py')
            TR = load('v272_report', ls_tree / 'control_telegram_report.py')
            t1, t2, t0, message = summary_rows(Path(base) / 's', LS, TR)
            check('AC4 summary/file', 'day one lists exactly the three with their fields, day two one, an empty day one line '
                  '[%r]' % t1[:300], file_ok(t1, t2, t0))
            check('AC4 summary/registry-identical', 'the three as spec.shipped records through the report render: byte-identical',
                  registry_ok(t1, message))
            with tempfile.TemporaryDirectory(prefix='v272-mut-', dir=base) as mut:
                tree = mutant_tree(mut, 'm', 'landed_summary.py',
                                   '"- %s %s | gate %s | reviewer %s | approval %s"\n'
                                   '                     % (item["ticket"], item["title"], item["gate"], item["reviewer"], approval)',
                                   '"- %s %s | gate %s | approval %s"\n'
                                   '                     % (item["ticket"], item["title"], item["gate"], approval)')
                check('AC4 mutation/reviewer-dropped', 'baseline green: both rows', file_ok(t1, t2, t0) and registry_ok(t1, message))
                if tree is None:
                    check('AC4 mutation/reviewer-dropped', 'the mutation anchor is present', False)
                else:
                    m1, m2, m0, mmsg = summary_rows(Path(mut) / 'y', load('v272_landed_mut', tree / 'landed_summary.py'),
                                                    load('v272_report_mut', tree / 'control_telegram_report.py'))
                    check('AC4 mutation/reviewer-dropped', 'mutant red: the file row and the registry row both fail',
                          not file_ok(m1, m2, m0) and not registry_ok(m1, mmsg))

            # F3, F4: every first-parent landing of the day, credited only by a named id; the computed flag
            # and the reviewer of the verdict the push check accepts.
            def busy_repo(where):
                repo = new_repo(where, 'busy')
                commit(repo, 'base', date='2026-11-05T09:00:00+00:00')
                day = '2026-11-06T%02d:00:00+00:00'
                sid = 'VELDO-9411'
                m = manifest(sid)
                write(repo, 'specs/%s-x.md' % sid, spec_text(sid, 'not_required', ['docs/**'], title='Busy ticket'))
                write(repo, 'proof/%s/manifest.json' % sid, json.dumps(m))
                c = commit(repo, '%s: build' % sid, date=day % 9)
                write(repo, 'proof/%s/verdict-r1.json' % sid, json.dumps(verdict(sid, c, 'rev-x', PD(m))))
                write(repo, 'proof/%s/verdict-r2.json' % sid, json.dumps(verdict(sid, c, 'builder', PD(m))))
                commit(repo, '%s landing: evidence' % sid, date=day % 10)
                write(repo, '.veldo/secret_inventory.json', '{}\n')
                inventory = commit(repo, 'Secret inventory: distinct pattern lines', date=day % 11)
                git(repo, 'checkout', '-q', '-b', 'side')
                write(repo, 'src/side.txt', 'side\n')
                commit(repo, 'side work', date=day % 12)
                git(repo, 'checkout', '-q', 'main')
                git(repo, 'merge', '-q', '--no-ff', '-m', 'Merge agent/claude/veldo-0241 into landing-a', 'side', date=day % 13)
                merge = git(repo, 'rev-parse', 'HEAD')
                sid2 = 'VELDO-9412'
                m2 = manifest(sid2)
                write(repo, 'specs/%s-x.md' % sid2, spec_text(sid2, 'not_required', ['.veldo/authorization.py'], title='Footprint on auth'))
                write(repo, 'proof/%s/manifest.json' % sid2, json.dumps(m2))
                c2 = commit(repo, '%s: build' % sid2, date=day % 14)
                write(repo, 'proof/%s/verdict.json' % sid2, json.dumps(verdict(sid2, c2, 'rev-y', PD(m2))))
                commit(repo, '%s landing: evidence' % sid2, date=day % 15)
                return repo, inventory, merge

            def busy_text(where, LSmod):
                repo, inventory, merge = busy_repo(where)
                return LSmod.write_day(repo, '2026-11-06')[0].read_text(), inventory, merge

            def every_ok(text, inventory, merge):
                lines = text.splitlines()
                return (len(lines) == 5 and lines[0].startswith('Veldo landed on 2026-11-06: 4 ')
                        and lines[1].startswith('- VELDO-9411 ')
                        and lines[2].startswith('- %s Secret inventory: distinct pattern lines ' % inventory[:12])
                        and lines[3].startswith('- %s Merge agent/claude/veldo-0241 into landing-a ' % merge[:12])
                        and lines[4].startswith('- VELDO-9412 '))

            def judged_ok(text):
                lines = text.splitlines()
                return (len(lines) == 5 and lines[0].endswith('(approval required 2, not required 2)')
                        and 'reviewer rev-x |' in lines[1] and 'approval not required' in lines[1]
                        and 'reviewer none' in lines[2] and 'approval required' in lines[2]
                        and 'approval not required' in lines[3]
                        and 'reviewer rev-y |' in lines[4] and 'approval required' in lines[4])

            bt, inv, mg = busy_text(Path(base) / 'b', LS)
            check('AC4 summary/every-landing', 'a ticket, a commit naming no ticket, a merge and a ticket: four lines, the two '
                  'without a credited id under their subject [%r]' % bt[:400], every_ok(bt, inv, mg))
            check('AC4 summary/judged-fields', 'the computed flag (a not_required spec whose footprint meets a protected path '
                  'reads required, a protected path change reads required) and the reviewer of the accepted verdict, not '
                  'the self-review that sorts after it [%r]' % bt[:400], judged_ok(bt))

    try:
        with tempfile.TemporaryDirectory(prefix='v272-') as directory:
            exercise(Path(directory))
    except Exception as error:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        for row in ROWS:
            check(row, 'ran to its end (raised %s: %s)' % (type(error).__name__, str(error)[:300]), False)
    for name, observed in rows.items():
        ok = bool(observed) and all(one for _, one in observed)
        for label, one in observed:
            if not one or os.environ.get('VELDO_0272_DETAILS'):
                print('  VELDO-0272 %s %s: %s' % (name, 'detail' if not one else 'observed', label))
        failed = next((label for label, one in observed if not one), 'no check ran' if not observed else '')
        expect('VELDO-0272 ' + name + (': ' + failed if failed else ''), ok)
    print('VELDO-0272 suite seconds: %.3f' % (time.monotonic() - started))


_v272_suite()
