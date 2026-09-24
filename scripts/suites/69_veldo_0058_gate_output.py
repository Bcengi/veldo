"""VELDO-0058: the canonical gate verifies a landing candidate from outside it. The stamp, the gate event
and the review-event reconciliation go to a trusted sink outside the candidate; GitLandOps.gate and
LiveLoop.gate each produce an external observation binding the exact candidate and the verification,
with the candidate unchanged after the run; the verifier and the policy that decide are the installed
ones, never the candidate's; and a valid candidate is published without its receipt in its own tree.

Only shared ROOT and expect are consumed. One temporary tree holds the installed .veldo copy the lander
and the executor load, with the production lander.py, executor.py and control_verification.py; the
fixture repository's canonical gate is the production scripts/verify.sh with a fixture catalog, so a
registered mutation of any of the four reaches every row. Real Git throughout: a scaffolded seed whose
gate stamp was committed by the ordinary landing step, a bare remote, the caller's clone the builds are
made in, and a work clone the executor's loop runs in. The fixture's one check is a real process that
fails a source not marked OK and, when a source asks, has a separate process change a tracked file, an
index entry or add an untracked file while the gate runs. This suite reads the candidates' state with
its own walk, never with control_verification's.
"""


def _v58_suite():
    import contextlib
    import hashlib
    import importlib.util
    import json
    import os
    from pathlib import Path
    import re
    import shutil
    import subprocess
    import sys
    import tempfile

    # Literal anchors: the registered mutation driver substitutes the production copy here.
    PRODUCTION = {
        'verify.sh': ROOT / "scripts" / "verify.sh",
        'lander.py': ROOT / ".veldo" / "lander.py",
        'executor.py': ROOT / ".veldo" / "executor.py",
        'control_verification.py': ROOT / ".veldo" / "control_verification.py",
        'policy_check.py': ROOT / ".veldo" / "policy_check.py",
    }

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def sha(body):
        return 'sha256:' + hashlib.sha256(body).hexdigest()

    emitted, raised, regions, observed = set(), [], [], {}

    def check(label, condition):
        emitted.add(label)
        expect('VELDO-0058 ' + label, bool(condition))

    @contextlib.contextmanager
    def region(*labels):
        regions.append(labels[0])
        try:
            yield
        except Exception as error:  # noqa: BLE001 - a raise reds its rows, never skips them
            raised.append((labels[0], repr(error)[:600]))
            for label in labels:
                if label not in emitted:
                    check(label, False)

    fast = '/dev/shm' if os.path.isdir('/dev/shm') and os.access('/dev/shm', os.W_OK) else None
    with tempfile.TemporaryDirectory(prefix='v58-', dir=fast) as directory:
        base = Path(directory)
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        shutil.copyfile(ROOT / '.veldo' / 'policy.yaml', mods / 'policy.yaml')
        for name, source in PRODUCTION.items():
            if name.endswith('.py'):
                shutil.copyfile(source, mods / name)
        GP = load('v58_git', mods / 'git_process.py')
        IS = load('v58_scaffold', mods / 'init_scaffold.py')
        LD = load('v58_lander', mods / 'lander.py')
        EX = load('v58_executor', mods / 'executor.py')
        OWNER = ('Owner', 'owner@example.invalid')
        BUILDER = ('Builder A', 'builder-a@example.invalid')
        LANDER = ('Lander', 'lander@example.invalid')
        clean = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        clean.update(PYTHONDONTWRITEBYTECODE='1', GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                     GIT_TERMINAL_PROMPT='0')

        def git(repo, *args, who=OWNER):
            r = GP.run(['git', '-C', str(repo), *args], capture_output=True, text=True, identity=who,
                       stdin=subprocess.DEVNULL, timeout=120)
            if r.returncode:
                raise RuntimeError('git %s: %s' % (' '.join(args[:3]), r.stderr.strip()[:300]))
            return r.stdout.strip()

        def blob(repo, commit, path):
            r = GP.run(['git', '-C', str(repo), 'cat-file', 'blob', '%s:%s' % (commit, path)], capture_output=True)
            return None if r.returncode else r.stdout

        def snapshot(root):
            """This suite's own reading of a work tree: HEAD, the index entries, and every file's bytes
            and mode outside .git, untracked and ignored included."""
            root = Path(root)
            files = {}
            for path in sorted(root.rglob('*')):
                rel = path.relative_to(root).as_posix()
                if rel == '.git' or rel.startswith('.git/'):
                    continue
                if path.is_symlink():
                    files[rel] = ('link', os.readlink(path))
                elif path.is_file():
                    files[rel] = ('file', path.stat().st_mode & 0o777, sha(path.read_bytes()))
                else:
                    files[rel] = ('dir',)
            return {'head': git(root, 'rev-parse', 'HEAD'), 'index': git(root, 'ls-files', '-s', '-v'),
                    'files': files}

        def inside(path, root):
            """This suite's own test: `path`, symlinks resolved, is `root` or below it."""
            path, root = os.path.realpath(str(path)), os.path.realpath(str(root))
            return path == root or path.startswith(root.rstrip(os.sep) + os.sep)

        def gate_text(text):
            """The production gate with this fixture's catalog: one required check, the rest not applicable."""
            def declare(match):
                if match.group(1) == 'unit':
                    return 'CHECK_unit="required:python3 -B check.py"'
                return 'CHECK_%s="na:fixture"' % match.group(1)
            return re.sub(r'(?m)^CHECK_([A-Za-z0-9_]+)=".*"$', declare, text)

        # The seed: scaffolded, its canonical gate the production script with the fixture catalog.
        seed = base / 'seed'
        seed.mkdir()
        GP.run(['git', 'init', '-q', '-b', 'main', str(seed)], check=True, capture_output=True)
        IS.scaffold(str(seed), templates=str(ROOT / 'engine'))
        # The trunk's policy module is the production one, so the installation a land lays down from the
        # trunk carries it (and a registered mutation of it).
        (seed / '.veldo' / 'policy_check.py').write_bytes(PRODUCTION['policy_check.py'].read_bytes())
        installed_gate = gate_text(PRODUCTION['verify.sh'].read_text())
        (seed / 'scripts' / 'verify.sh').write_text(installed_gate)
        (seed / '.gitignore').write_text('__pycache__/\n')
        (seed / 'check.py').write_text('\n'.join([
            'import pathlib, subprocess, sys',
            "texts = {p.name: p.read_text() for p in sorted(pathlib.Path('src').glob('*.py'))}",
            "actions = {'tracked': \"open('README.md', 'a').write('changed while the gate ran\\\\n')\",",
            "           'untracked': \"open('stray.out', 'w').write('output left by a check\\\\n')\",",
            "           'index': \"import subprocess; subprocess.run(['git', 'update-index', '--chmod=+x', 'README.md'], check=True)\"}",
            'for text in texts.values():',
            '    for mode, action in actions.items():',
            "        if 'MUTATE = %r' % mode in text:",
            "            subprocess.run([sys.executable, '-B', '-c', action], check=True)",
            "bad = [n for n, t in texts.items() if 'OK = True' not in t]",
            "print('red: %s' % bad if bad else 'green')",
            'sys.exit(1 if bad else 0)', '']))
        (seed / 'src').mkdir()
        (seed / 'src' / 'README').write_text('fixture sources\n')
        (seed / 'README.md').write_text('fixture\n')
        UNITS = ['VELDO-95%02d' % n for n in range(81, 92)]
        for sid in UNITS:
            (seed / 'specs' / ('%s-gate-output-fixture.md' % sid)).write_text('\n'.join([
                '---', 'schema: veldo.spec/v1', 'id: ' + sid, 'title: Gate output fixture unit', 'status: ready',
                'risk: standard', 'owner: dmitry', 'human_approval: not_required', 'lane: standalone',
                'protected_paths: []', 'acceptance_criteria:', '  - id: AC1', '    text: The unit check passes.',
                'required_evidence: [unit]', 'rollback: git revert', '---', '', '## Intent', '', 'Fixture.', '']))
        subprocess.run([sys.executable, '-B', 'scripts/update_index.py'], cwd=str(seed), check=True,
                       capture_output=True, timeout=60, env=clean)
        git(seed, 'add', '-A')
        git(seed, 'commit', '-q', '-m', 'Fixture repository')
        first = git(seed, 'rev-parse', 'HEAD')
        # The ordinary landing step, unchanged: the checkout's own gate, then its stamp committed.
        ordinary = subprocess.run(['bash', 'scripts/verify.sh'], cwd=str(seed), capture_output=True, text=True,
                                  stdin=subprocess.DEVNULL, env=clean, timeout=300)
        stamp_path, log_path = seed / '.veldo' / 'last_verify', seed / '.veldo' / 'events.jsonl'
        observed['ordinary'] = {
            'exit': ordinary.returncode, 'terminal': (ordinary.stdout.strip().splitlines() or [''])[-1],
            'stamp': json.loads(stamp_path.read_text()) if stamp_path.is_file() else None,
            'last_event': json.loads(log_path.read_text().splitlines()[-1]) if log_path.is_file() else None}
        git(seed, 'add', '--', '.veldo/last_verify', '.veldo/events.jsonl')
        git(seed, 'commit', '-q', '-m', 'Gate stamp for ' + first[:12])
        WATERMARK = git(seed, 'rev-parse', 'HEAD')
        remote = base / 'remote.git'
        GP.run(['git', 'clone', '-q', '--bare', str(seed), str(remote)], check=True, capture_output=True)
        caller = base / 'caller'
        GP.run(['git', 'clone', '-q', str(remote), str(caller)], check=True, capture_output=True)
        for repo in (caller, remote):
            git(repo, 'config', 'gc.auto', '0')
        gate_blob = blob(caller, WATERMARK, 'scripts/verify.sh')

        def build(unit, files, verdict=False, repo=caller):
            """A build branch from the trunk: the implementation commit, then the evidence commit whose
            proof names it (and a committed pass verdict when asked, which reconciliation projects)."""
            git(repo, 'checkout', '-q', '-B', 'build/' + unit, 'origin/main')
            for rel, text in files.items():
                (repo / rel).parent.mkdir(parents=True, exist_ok=True)
                (repo / rel).write_text(text)
            git(repo, 'add', '-A')
            git(repo, 'commit', '-q', '-m', 'Implement ' + unit, who=BUILDER)
            implementation = git(repo, 'rev-parse', 'HEAD')
            source = next(rel for rel in files if rel.startswith('src/'))
            manifest = {'schema': 'veldo.proof/v1', 'spec_id': unit, 'producer': 'builder-a', 'commit': implementation,
                        'criteria': [{'id': 'AC1', 'status': 'passed', 'evidence': [
                            {'type': 'unit', 'path': source, 'digest': sha((repo / source).read_bytes())}]}],
                        'checks': [{'name': 'unit', 'status': 'passed'}], 'rollback': 'git revert'}
            proof = repo / 'proof' / unit
            proof.mkdir(parents=True, exist_ok=True)
            if verdict:
                (proof / 'verdict-r1.json').write_text(json.dumps({
                    'schema': 'veldo.verdict/v1', 'spec_id': unit, 'commit': implementation,
                    'reviewer': {'model': 'fixture-reviewer', 'context': 'fresh'}, 'verdict': 'pass',
                    'reviewed_at': '2026-09-24T12:00:00Z', 'criteria': [{'id': 'AC1', 'assessment': 'satisfied'}],
                    'findings': {'blocking': [], 'non_blocking': []}}, indent=1) + '\n')
            (proof / 'manifest.json').write_text(json.dumps(manifest, indent=1, sort_keys=True) + '\n')
            git(repo, 'add', '--', 'proof/' + unit)
            git(repo, 'commit', '-q', '-m', 'Proof for ' + unit, who=BUILDER)
            return 'build/' + unit, implementation, git(repo, 'rev-parse', 'HEAD')

        def remote_tip():
            return git(remote, 'rev-parse', 'refs/heads/main')

        observations = base / 'observations'
        observations.mkdir()

        def land(branch, unit, between=None):
            """sync, reconcile, gate and finalize one unit through GitLandOps, recording the candidate's
            state (this suite's own reading) around the gate; `between` runs after the gate and before
            finalize, and may return False to finalize no further."""
            # The class is handed exactly the arguments its constructor takes (a pre-change lander has
            # no observations directory), so a red row is an assertion, never a TypeError.
            accepts = __import__('inspect').signature(LD.GitLandOps.__init__).parameters
            extra = {'observations': observations} if 'observations' in accepts else {}
            ops = LD.GitLandOps(caller, branch, trunk='main', remote='origin', push=True, identity=LANDER, **extra)
            out = {'trunk_before': remote_tip()}
            out['sync'] = ops.sync_main()
            out['reconcile'] = ops.reconcile(unit)
            record = ops.record() or {}
            workspace = record.get('workspace')
            out['before'] = snapshot(workspace)
            out['gate'] = ops.gate()
            out['after'] = snapshot(workspace)
            out['record'] = ops.record()
            out['finalize'] = []
            if out['gate'].get('ok'):
                if between is not None:
                    between(ops, out)
                out['finalize'].append(ops.finalize(unit))
            out['record'] = ops.record()
            out['trunk_after'] = remote_tip()
            reference = ((out['record'] or {}).get('gate') or {}).get('observation') or {}
            try:
                out['observation'] = json.loads(Path(reference['path']).read_text())
            except (KeyError, OSError, ValueError, TypeError):
                out['observation'] = {}
            out['workspace'] = workspace
            ops.discard()
            return out

        def refusal(result):
            return (result or {}).get('refusal')

        # A work clone for the executor's loop, its base the trunk.
        work = base / 'work'
        GP.run(['git', 'clone', '-q', str(remote), str(work)], check=True, capture_output=True)

        def live_gate(unit, files, verdict=False):
            """LiveLoop.gate over the work clone at a build of `unit`, resolved at the trunk first so the
            installed verifier is the base commit's."""
            git(work, 'checkout', '-q', '--detach', 'origin/main')
            live = EX.LiveLoop(root=str(work))
            live.resolve(unit)
            _branch, _implementation, evidence = build(unit, files, verdict=verdict, repo=work)
            before = snapshot(work)
            result = live.gate()
            return {'result': result, 'commit': evidence, 'base': getattr(live, 'base', None), 'before': before, 'after': snapshot(work),
                    'observation': result.get('observation') or {}}

        def reset_work():
            git(work, 'checkout', '-q', '-f', '--detach', 'origin/main')
            git(work, 'update-index', '--chmod=-x', 'README.md')
            git(work, 'checkout', '-q', '-f', '--', 'README.md')
            stray = work / 'stray.out'
            if stray.exists():
                stray.unlink()

        U = dict(zip(('review', 'live', 'red', 'tamper', 'during', 'stub_gate', 'stub_policy', 'valid',
                      'emptied_list', 'control_list', 'plain_list'), UNITS))

        # AC1: the stamp, the gate event and the review-event reconciliation go to the sink.
        with region('gate-output/review-write'):
            branch, _impl, evidence = build(U['review'], {'src/review.py': 'OK = True\n'}, verdict=True)
            valid = land(branch, U['review'])
            obs = valid['observation']
            commit = ((valid['record'] or {}).get('commit'))
            appended = (obs.get('outputs') or {}).get('appended') or []
            verdict_path = 'proof/%s/verdict-r1.json' % U['review']
            live = live_gate(U['live'], {'src/live.py': 'OK = True\n'}, verdict=True)
            reset_work()
            lobs = live['observation']
            lappended = (lobs.get('outputs') or {}).get('appended') or []
            red_branch, _impl, _evidence = build(U['red'], {'src/red.py': 'OK = False\n'})
            red = land(red_branch, U['red'])
            robs = red['observation']
            observed['review_write'] = {
                'valid': {k: valid[k] for k in ('gate', 'finalize', 'trunk_before', 'trunk_after')},
                'valid_unchanged': valid['before'] == valid['after'], 'appended': appended,
                'live': {'green': live['result'].get('green'), 'unchanged': live['before'] == live['after'],
                         'appended': lappended, 'refusals': lobs.get('refusals')},
                'red': {'gate': red['gate'], 'unchanged': red['before'] == red['after'],
                        'stamp': (robs.get('outputs') or {}).get('last_verify'),
                        'event': (robs.get('outputs') or {}).get('gate_event')}}
            check('gate-output/review-write',
                  valid['gate'].get('ok') is True and valid['before'] == valid['after']
                  and {'type': 'verdict.recorded', 'verdict_path': verdict_path} in
                  [{k: e.get(k) for k in ('type', 'verdict_path')} for e in appended]
                  and appended[-1:] == [{'type': 'gate.passed', 'commit': commit, 'producer': 'verify.sh'}]
                  and ((obs.get('outputs') or {}).get('last_verify') or {}).get('commit') == commit
                  and ((obs.get('outputs') or {}).get('last_verify') or {}).get('status') == 'green'
                  and blob(remote, commit, '.veldo/events.jsonl') == blob(remote, WATERMARK, '.veldo/events.jsonl')
                  and not inside((obs.get('outputs') or {}).get('sink', ''), valid['workspace'])
                  and valid['finalize'][-1].get('pushed') is True and valid['trunk_after'] == commit
                  and live['result'].get('green') is True and live['before'] == live['after']
                  and lobs.get('commit') == live['commit']
                  and any(e.get('type') == 'verdict.recorded' and e.get('verdict_path') == 'proof/%s/verdict-r1.json' % U['live']
                          for e in lappended)
                  and lappended[-1:] == [{'type': 'gate.passed', 'commit': live['commit'], 'producer': 'verify.sh'}]
                  and refusal(red['gate']) == 'missing_evidence:gate' and red['before'] == red['after']
                  and ((robs.get('outputs') or {}).get('last_verify') or {}).get('status') == 'red'
                  and ((robs.get('outputs') or {}).get('gate_event') or {}).get('type') == 'gate.failed'
                  and red['trunk_after'] == red['trunk_before'])

        # AC1: a sink that is absent, not a directory, unwritable, the candidate or inside it, or holding
        # a symlink where an output goes is refused before any check runs; a sink that refuses the final
        # write is RED; nothing is written to the candidate either way; the ordinary checkout is unchanged.
        with region('gate-output/sink-refusals'):
            probe = base / 'probe'
            GP.run(['git', 'clone', '-q', str(remote), str(probe)], check=True, capture_output=True)
            verifier = base / 'verifier' / 'scripts' / 'verify.sh'
            verifier.parent.mkdir(parents=True)
            verifier.write_bytes(gate_blob)

            def verify_at(sink, *extra):
                args = ['--candidate', str(probe)] + (['--sink', str(sink)] if sink is not None else []) + list(extra)
                before = snapshot(probe)
                run = subprocess.run(['bash', str(verifier)] + args, cwd=str(probe), capture_output=True, text=True,
                                     stdin=subprocess.DEVNULL, env=clean, timeout=300)
                lines = run.stdout.strip().splitlines()
                return {'exit': run.returncode, 'terminal': lines[-1] if lines else None,
                        'refused': any(line.startswith('== gate output: REFUSED') for line in lines),
                        'not_written': any(line.startswith('== gate output: NOT WRITTEN') for line in lines),
                        'checks_ran': '== unit' in lines, 'unchanged': before == snapshot(probe)}

            sinks = base / 'sinks'
            sinks.mkdir()
            (sinks / 'a-file').write_text('not a directory\n')
            (sinks / 'locked').mkdir(mode=0o500)
            os.symlink(str(probe / '.veldo'), str(sinks / 'into-candidate'))
            (sinks / 'planted').mkdir()
            os.symlink(str(probe / '.veldo' / 'events.jsonl'), str(sinks / 'planted' / 'events.jsonl'))
            (sinks / 'directory-log').mkdir()
            (sinks / 'directory-log' / 'events.jsonl').mkdir()
            cases = {'absent': verify_at(sinks / 'absent'), 'file': verify_at(sinks / 'a-file'),
                     'unwritable': verify_at(sinks / 'locked'), 'symlink-into': verify_at(sinks / 'into-candidate'),
                     'candidate': verify_at(probe), 'planted-link': verify_at(sinks / 'planted'),
                     'no-sink': verify_at(None)}
            (sinks / 'locked').chmod(0o700)
            final_write = verify_at(sinks / 'directory-log')
            head = git(probe, 'rev-parse', 'HEAD')
            refused_red = {name: c['exit'] == 1 and c['terminal'] == 'GATE: RED (%s)' % head and c['refused']
                           and not c['checks_ran'] and c['unchanged'] for name, c in cases.items()}
            written = sorted(p.name for p in (sinks / 'locked').iterdir()) + sorted(
                p.name for p in (sinks / 'planted').iterdir())
            ordinary_ok = observed['ordinary']
            observed['sink_refusals'] = {'cases': cases, 'final_write': final_write, 'refused_red': refused_red,
                                         'written': written, 'ordinary': ordinary_ok}
            check('gate-output/sink-refusals',
                  all(refused_red.values()) and len(refused_red) == 7 and written == ['events.jsonl']
                  and final_write['exit'] == 1 and final_write['terminal'] == 'GATE: RED (%s)' % head
                  and final_write['checks_ran'] and final_write['not_written'] and final_write['unchanged']
                  and ordinary_ok['exit'] == 0 and ordinary_ok['terminal'] == 'GATE: GREEN (%s)' % first
                  and (ordinary_ok['stamp'] or {}).get('commit') == first
                  and (ordinary_ok['stamp'] or {}).get('status') == 'green'
                  and (ordinary_ok['last_event'] or {}).get('type') == 'gate.passed'
                  and (ordinary_ok['last_event'] or {}).get('commit') == first)

        # AC2: the observation binds the exact candidate and the verification; any change to the candidate
        # during the run or after it, and any altered observation, refuses acceptance.
        with region('gate-output/post-run-mutation'):
            trunk_now = remote_tip()
            tampered = {}

            def tamper(ops, out):
                c = ops.candidate
                ws = Path(c['workspace'])
                reference = dict((c.get('gate') or {}).get('observation') or {})
                original = Path(reference['path']).read_bytes() if reference.get('path') else None

                def attempt(name, restore):
                    tampered[name] = ops.finalize(U['tamper'])
                    tampered[name + ':trunk'] = remote_tip()
                    restore()
                    c['state'] = 'verified'

                (ws / 'README.md').write_text('written after the final check\n')
                attempt('tracked', lambda: git(ws, 'checkout', '-q', '--', 'README.md'))
                git(ws, 'update-index', '--chmod=+x', 'README.md')
                attempt('index', lambda: git(ws, 'update-index', '--chmod=-x', 'README.md'))
                (ws / 'late.out').write_text('evidence written into the candidate\n')
                attempt('untracked', lambda: (ws / 'late.out').unlink())

                def rewrite(name, change):
                    if original is None:
                        tampered[name] = {'skipped': 'the gate wrote no external observation'}
                        return
                    body = json.loads(original)
                    change(body)
                    body['stdout_digest'] = sha(body['stdout'].encode('utf-8', 'surrogateescape'))
                    data = json.dumps(body, sort_keys=True, separators=(',', ':')).encode()
                    Path(reference['path']).write_bytes(data)
                    c['gate']['observation'] = dict(reference, digest=sha(data))

                    def restore():
                        Path(reference['path']).write_bytes(original)
                        c['gate']['observation'] = dict(reference)
                    attempt(name, restore)

                rewrite('no-terminal', lambda b: b.update(stdout='\n'.join(b['stdout'].splitlines()[:-1]) + '\n'))
                rewrite('check-result', lambda b: b.update(stdout=b['stdout'].replace('   unit: pass', '   unit: FAIL')))
                rewrite('identity', lambda b: b.update(commit='f' * 40, candidate=dict(b['candidate'], commit='f' * 40)))

            branch, _impl, _evidence = build(U['tamper'], {'src/tamper.py': 'OK = True\n'})
            landed = land(branch, U['tamper'], between=tamper)
            obs, commit = landed['observation'], (landed['record'] or {}).get('commit')
            during_branch, _impl, _evidence = build(U['during'], {'src/during.py': "OK = True\nMUTATE = 'index'\n"})
            during = land(during_branch, U['during'])
            live_runs = {}
            for mode in ('tracked', 'index', 'untracked'):
                run = live_gate(U['during'], {'src/during.py': "OK = True\nMUTATE = %r\n" % mode})
                live_runs[mode] = {'green': run['result'].get('green'),
                                   'refusals': run['observation'].get('refusals'),
                                   'changed': (run['observation'].get('post_run') or {}).get('changed')}
                reset_work()
            expected = {'tracked': 'stale_subject:candidate/changed_after_gate',
                        'index': 'stale_subject:candidate/changed_after_gate',
                        'untracked': 'stale_subject:candidate/changed_after_gate',
                        'no-terminal': 'missing_evidence:gate/terminal',
                        'check-result': 'missing_evidence:check_failed/unit',
                        'identity': 'stale_subject:observation/commit'}
            refused = {name: code in ((tampered.get(name) or {}).get('refusals') or [])
                       and tampered.get(name, {}).get('ok') is False and tampered.get(name + ':trunk') == trunk_now
                       for name, code in expected.items()}
            changed = {'tracked': 'README.md', 'index': ':index', 'untracked': 'stray.out'}
            during_refused = {mode: r['green'] is False and 'stale_subject:candidate/changed_during_gate' in (r['refusals'] or [])
                              and changed[mode] in (r['changed'] or []) for mode, r in live_runs.items()}
            required = [n for n, v in re.findall(r'(?m)^CHECK_([a-z_]+)="([^"]*)"$', installed_gate)
                        if v.startswith('required:')]
            bound = (obs.get('commit') == commit and (obs.get('candidate') or {}).get('commit') == commit
                     and (obs.get('candidate') or {}).get('tree') == git(remote, 'rev-parse', commit + '^{tree}')
                     and (obs.get('gate') or {}).get('digest') == sha(gate_blob)
                     and (obs.get('gate') or {}).get('installation') == 'commit:' + trunk_now
                     and (obs.get('command') or [None])[0] == 'bash'
                     and not inside((obs.get('command') or ['', ''])[1], landed['workspace'])
                     and (obs.get('command') or [])[2:] == ['--candidate', os.path.realpath(landed['workspace']),
                                                            '--sink', (obs.get('outputs') or {}).get('sink')]
                     and required == ['unit'] and (obs.get('catalog') or {}).get('required') == required
                     and (obs.get('catalog') or {}).get('results') == {'unit': 'pass'}
                     and '   unit: pass' in obs.get('stdout', '').splitlines()
                     and obs.get('stdout_digest') == sha(obs.get('stdout', '').encode())
                     and obs.get('terminal') == 'GATE: GREEN (%s)' % commit
                     and (obs.get('post_run') or {}).get('equal') is True and obs.get('green') is True
                     and obs.get('refusals') == [])
            final = (landed['finalize'] or [{}])[-1]
            observed['post_run'] = {'refused': refused, 'tampered': tampered, 'during_land': during['gate'],
                                    'live': live_runs, 'during_refused': during_refused, 'bound': bound,
                                    'final': final, 'trunk_after': landed['trunk_after']}
            check('gate-output/post-run-mutation',
                  bound and all(refused.values()) and len(refused) == 6 and all(during_refused.values())
                  and refusal(during['gate']) == 'stale_subject:candidate/changed_during_gate'
                  and during['trunk_after'] == during['trunk_before']
                  and final.get('pushed') is True and landed['trunk_after'] == commit)

        # AC3: the installed verifier and policy decide, never the candidate's success stubs; an observation
        # moved under the candidate or altered refuses; a valid candidate lands with no receipt in its tree.
        with region('gate-output/installed-policy'):
            trunk_now = remote_tip()
            stub_gate = '#!/usr/bin/env bash\necho "GATE: GREEN ($(git rev-parse HEAD))"\nexit 0\n'
            stub_policy = 'import sys\nprint("stub policy: accepted")\nsys.exit(0)\n'
            b1, _impl, _evidence = build(U['stub_gate'], {'src/stub_gate.py': 'OK = False\n',
                                                          'scripts/verify.sh': stub_gate,
                                                          '.veldo/policy_check.py': stub_policy})
            stubbed_gate = land(b1, U['stub_gate'])
            sobs = stubbed_gate['observation']
            b2, impl2, _evidence = build(U['stub_policy'], {'src/stub_policy.py': 'OK = True\n',
                                                            'auth/login.py': 'ALLOW = True\n',
                                                            '.veldo/policy_check.py': stub_policy})
            git(caller, 'checkout', '-q', 'build/' + U['stub_policy'])
            (caller / 'proof' / U['stub_policy'] / 'approval-dmitry.json').write_text(json.dumps({
                'schema': 'veldo.approval/v1', 'id': 'APPROVAL-9587-1', 'decision': 'rejected', 'approver': 'dmitry',
                'scope': {'spec_id': U['stub_policy'], 'commit': impl2, 'paths': ['auth/login.py']},
                'basis': 'The owner rejected this change.', 'recorded_at': '2026-09-24T12:00:00Z',
                'recorded_by': 'fixture', 'expires_at': '2026-12-31T00:00:00Z'}, indent=1) + '\n')
            git(caller, 'add', '-A')
            git(caller, 'commit', '-q', '-m', 'Rejected approval for ' + U['stub_policy'], who=BUILDER)
            stub_ran = subprocess.run([sys.executable, '-B', '.veldo/policy_check.py'], cwd=str(caller),
                                      capture_output=True, text=True, env=clean, timeout=60)
            stubbed_policy = land(b2, U['stub_policy'])
            moved = {}

            def move(ops, out):
                c = ops.candidate
                reference = dict((c.get('gate') or {}).get('observation') or {})
                if not reference.get('path'):
                    moved['skipped'] = 'the gate wrote no external observation'
                    return
                inner = Path(c['workspace']) / '.git' / 'observation.json'
                shutil.copyfile(reference['path'], inner)
                c['gate']['observation'] = dict(reference, path=str(inner))
                moved['inside'] = ops.finalize(U['valid'])
                c['state'], c['gate']['observation'] = 'verified', dict(reference)
                original = Path(reference['path']).read_bytes()
                Path(reference['path']).write_bytes(original.replace(b'"green":true', b'"green":true ', 1))
                moved['altered'] = ops.finalize(U['valid'])
                Path(reference['path']).write_bytes(original)
                c['state'] = 'verified'
                moved['trunk'] = remote_tip()

            b3, _impl, _evidence = build(U['valid'], {'src/valid.py': 'OK = True\n'})
            valid = land(b3, U['valid'], between=move)
            vcommit = (valid['record'] or {}).get('commit')
            changed_paths = git(remote, 'diff', '--name-only', trunk_now, vcommit).splitlines() if vcommit else []
            observed['installed_policy'] = {
                'stub_gate': {'gate': stubbed_gate['gate'], 'results': (sobs.get('catalog') or {}).get('results'),
                              'verifier': (sobs.get('gate') or {}).get('digest')},
                'stub_policy': {'gate': stubbed_policy['gate'], 'finalize': stubbed_policy['finalize'],
                                'stub_exit': stub_ran.returncode},
                'moved': moved, 'valid': valid['finalize'], 'changed_paths': changed_paths}
            policy_final = (stubbed_policy['finalize'] or [{}])[-1]
            check('gate-output/installed-policy',
                  refusal(stubbed_gate['gate']) == 'missing_evidence:gate'
                  and (sobs.get('catalog') or {}).get('results') == {'unit': 'FAIL'}
                  and (sobs.get('gate') or {}).get('digest') == sha(gate_blob)
                  and stubbed_gate['trunk_after'] == stubbed_gate['trunk_before'] == trunk_now
                  and stub_ran.returncode == 0 and stubbed_policy['gate'].get('ok') is True
                  and policy_final.get('ok') is False and policy_final.get('pushed') is not True
                  and 'missing_authority:repository_policy' in (policy_final.get('refusals') or [])
                  and 'Protected path touched' in str(policy_final.get('policy_check'))
                  and stubbed_policy['trunk_after'] == trunk_now
                  and 'invalid_input:observation/inside_candidate' in ((moved.get('inside') or {}).get('refusals') or [])
                  and 'binding_mismatch:observation/digest' in ((moved.get('altered') or {}).get('refusals') or [])
                  and moved.get('trunk') == trunk_now
                  and (valid['finalize'] or [{}])[-1].get('pushed') is True and valid['trunk_after'] == vcommit
                  and changed_paths and not {'.veldo/last_verify', '.veldo/events.jsonl'} & set(changed_paths)
                  and not any(p.startswith('proof/%s/' % U['valid']) and 'observation' in p for p in changed_paths))

        # AC3: the protected list the installed policy applies is the installation's policy.yaml, never the
        # candidate's. A candidate that empties protected_paths and adds a protected file is refused by the
        # trunk's list; the same change without the edit is refused too; an unprotected change lands.
        with region('gate-output/installed-policy-list'):
            trunk_list = remote_tip()
            YM = load('v58_yamlish', mods / 'yamlish.py')
            trunk_policy = blob(remote, trunk_list, '.veldo/policy.yaml').decode()
            emptied = re.sub(r'(?ms)^protected_paths:\n(?:(?:  .*|\s*)\n)*', 'protected_paths: []\n',
                             trunk_policy, count=1)
            lists = {'trunk': [r.get('path') for r in YM.parse(trunk_policy).get('protected_paths') or []],
                     'emptied': YM.parse(emptied).get('protected_paths')}
            b4, _impl, _evidence = build(U['emptied_list'], {'src/emptied_list.py': 'OK = True\n',
                                                             'auth/login.py': 'ALLOW = True\n',
                                                             '.veldo/policy.yaml': emptied})
            emptied_land = land(b4, U['emptied_list'])
            b5, _impl, _evidence = build(U['control_list'], {'src/control_list.py': 'OK = True\n',
                                                             'auth/login.py': 'ALLOW = True\n'})
            control_land = land(b5, U['control_list'])
            b6, _impl, _evidence = build(U['plain_list'], {'src/plain_list.py': 'OK = True\n'})
            plain_land = land(b6, U['plain_list'])
            pcommit = (plain_land['record'] or {}).get('commit')

            def refused_by_list(result):
                final = (result['finalize'] or [{}])[-1]
                return (result['gate'].get('ok') is True and final.get('ok') is False
                        and final.get('pushed') is not True
                        and 'missing_authority:repository_policy' in (final.get('refusals') or [])
                        and 'auth/login.py  (protected by auth/**)' in str(final.get('policy_check'))
                        and result['trunk_after'] == trunk_list)

            observed['installed_policy_list'] = {
                'lists': lists,
                'emptied': {'gate': emptied_land['gate'], 'finalize': emptied_land['finalize'],
                            'trunk_moved': emptied_land['trunk_after'] != trunk_list},
                'control': {'gate': control_land['gate'], 'finalize': control_land['finalize'],
                            'trunk_moved': control_land['trunk_after'] != trunk_list},
                'plain': {'gate': plain_land['gate'], 'finalize': plain_land['finalize'],
                          'trunk_after': plain_land['trunk_after'], 'commit': pcommit}}
            check('gate-output/installed-policy-list',
                  'auth/**' in lists['trunk'] and lists['emptied'] == []
                  and refused_by_list(emptied_land) and refused_by_list(control_land)
                  and (plain_land['finalize'] or [{}])[-1].get('pushed') is True
                  and pcommit and plain_land['trunk_after'] == pcommit)

        for first_label in regions:
            check('ran/' + first_label, first_label not in {label for label, _ in raised})
        observed['raised'] = raised
        globals()['_V58_OBSERVED'] = observed


_v58_started = __import__('time').monotonic()
_v58_suite()
_V58_SECONDS = __import__('time').monotonic() - _v58_started
