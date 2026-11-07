"""VELDO-0272: owner approval narrows to money, authentication and security, schema and irreversible
infrastructure; routine work lands on a green gate and a recorded independent review; the owner gets a daily
summary of what landed.

STAGED, NOT REGISTERED. This file belongs at scripts/suites/129_veldo_0272_approval_scope.py, but a suite file
there must also be enumerated in scripts/suites/manifest.json and requires.json (selftest refuses an
unenumerated file with SUITE_NOT_ENUMERATED), and both are outside VELDO-0272's footprint. It runs in the
shared namespace exactly as selftest runs a fragment (only ROOT and expect are consumed).

Each declared falsifier is a row that applies the mutation to a temporary copy (the policy rows, or a copy of
.veldo/ with one module changed), checks the unmutated baseline is green and the mutant red. Real Git
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
            'AC4 summary/file', 'AC4 summary/registry-identical', 'AC4 mutation/reviewer-dropped')
    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    GP = load('v272_git_process', ROOT / '.veldo' / 'git_process.py')
    Y = load('v272_yamlish', ROOT / '.veldo' / 'yamlish.py')
    POLICY_TEXT = (ROOT / '.veldo' / 'policy.yaml').read_text()

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

    def mutant_tree(base, name, module, old, new):
        """A copy of .veldo/*.py with one module changed; returns its .veldo directory, or None when the
        anchor is absent (a mutation that cannot apply is a red row, never a silent pass)."""
        tree = Path(base) / name / '.veldo'
        tree.mkdir(parents=True)
        for source in (ROOT / '.veldo').glob('*.py'):
            shutil.copyfile(source, tree / source.name)
        shutil.copyfile(ROOT / '.veldo' / 'policy.yaml', tree / 'policy.yaml')
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
    policy = Y.read(ROOT / '.veldo' / 'policy.yaml')

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
        P = load('v272_policy_check', ROOT / '.veldo' / 'policy_check.py')
        V = load('v272_validate', ROOT / '.veldo' / 'validate.py')

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

        # AC2: fixture specs after the start commit, and one committed before it.
        def flag_repo(where, Vmod):
            repo = new_repo(where, 'flags')
            write(repo, 'specs/VELDO-9101-old.md', spec_text('VELDO-9101', 'not_required', ['.veldo/policy_check.py']))
            first = commit(repo, 'old spec')
            write(repo, '.veldo/policy.yaml', re.sub(r'(approval_scope:\n  from_commit: )\S+', r'\g<1>' + first, POLICY_TEXT))
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
        P2 = load('v272_policy_check_roots', ROOT / '.veldo' / 'policy_check.py')
        P2.ROOT = ROOT

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

        # AC3: lowered flags and the review a not-required landing needs.
        def manifest(sid, producer='builder', checks=('unit',)):
            return {'schema': 'veldo.proof/v1', 'spec_id': sid, 'commit': 'f' * 40, 'producer': producer,
                    'criteria': [{'id': 'AC1', 'status': 'passed', 'evidence': [{'type': 'unit'}]}],
                    'checks': [{'name': c} for c in checks], 'rollback': 'revert'}

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

        def landing_case(where, Pmod, reviewer, stale=False):
            repo = new_repo(where, 'land-%s-%s' % (reviewer or 'none', stale))
            commit(repo, 'base')
            git(repo, 'update-ref', 'refs/remotes/origin/main', 'HEAD')
            sid = 'VELDO-9302'
            m = manifest(sid)
            write(repo, 'docs/guide.md', 'routine\n')
            write(repo, 'specs/VELDO-9302-docs.md', spec_text(sid, 'not_required', ['docs/**']))
            write(repo, 'proof/%s/manifest.json' % sid, json.dumps(m))
            change = commit(repo, 'docs change')
            if reviewer:
                digest = Pmod.proof_digest(manifest(sid, checks=('unit', 'older')) if stale else m)
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
                               'if producer is not None and (not v.get("reviewer") or v.get("reviewer") == producer):',
                               'if False:')
            check('AC3 mutation/reviewer-comparison-skipped', 'baseline green: the self-reviewed landing is refused',
                  r['self'][0] == 1)
            if tree is None:
                check('AC3 mutation/reviewer-comparison-skipped', 'the mutation anchor is present', False)
            else:
                PM = load('v272_policy_check_mut', tree / 'policy_check.py')
                code, out = landing_case(Path(mut) / 'x', PM, 'builder')
                check('AC3 mutation/reviewer-comparison-skipped', 'mutant red: the self-reviewed landing exits %d' % code, code != 1)

        EX = load('v272_executor', ROOT / '.veldo' / 'executor.py')
        hooks = EX.LiveLoop.__new__(EX.LiveLoop)
        ok_docs = hooks.merge_ready({'human_approval': 'not_required', 'footprint': ['docs/**']}, None, None)
        lied = hooks.merge_ready({'human_approval': 'not_required', 'footprint': ['.veldo/policy_check.py']}, None, None)
        check('AC3 executor/computed-flag', 'merge_ready: docs/** not_required is ready; a protected footprint declared '
              'not_required is not [%s]' % (lied,), ok_docs[0] is True and lied[0] is False and 'rule' in lied[1])

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
                write(repo, 'proof/%s/verdict.json' % sid, json.dumps(verdict(sid, c, reviewer, 'sha256:0')))
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

        LS = load('v272_landed', ROOT / '.veldo' / 'landed_summary.py')
        TR = load('v272_report', ROOT / '.veldo' / 'control_telegram_report.py')
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
