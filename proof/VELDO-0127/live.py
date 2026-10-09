#!/usr/bin/env python3
"""Lead-only subscription capture. This driver is never run by the implementer or suite.

Arguments name logged-in profile directories and pinned binaries. Login files are copied into
private temporary profiles under each login's runner lease and rotated credentials are written
back before the lease is released; one that cannot be is kept as a private recovery on persistent
storage and the run exits with the launcher's recovery status (VELDO-0211). Workers
run serially in the temporary factory, under its own transient Linux slice. Captures hold
capability names, credential-source identities and redacted execution-record evidence.
"""
import argparse
from contextlib import contextmanager
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
P = '-' * 2


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


LOGIN = load('live_borrowed_login', ROOT / 'scripts/agent_sandbox.py')


class Guard:
    """A process that holds the borrow's leases and scratch for as long as this one runs. If this
    one is killed outright, the guard stops the factory slice and only then settles the borrow
    itself (write-back, or a recovery), so no engine left running in the slice rotates the login
    after its lease is released and no rotation is left behind in the runtime directory."""

    def __init__(self):
        self.pid = self.write = None

    def start(self, borrow, command, env):
        read, write = os.pipe()
        pid = os.fork()
        if pid == 0:
            code = 1
            try:
                os.setsid()
                for number in LOGIN.STOP_SIGNALS:
                    signal.signal(number, signal.SIG_IGN)
                # Nothing else of this process stays open in the guard: a socket it held would never
                # reach end of file at the teardown.
                keep = {0, 1, 2, read, *borrow.descriptors}
                for name in os.listdir('/proc/self/fd'):
                    if int(name) not in keep:
                        try:
                            os.close(int(name))
                        except OSError:
                            pass
                code = 0
                if os.read(read, 1) != b'1':
                    try:
                        subprocess.run(command, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL)
                    except (OSError, subprocess.SubprocessError) as error:
                        print('live: the slice was not stopped: %s' % error, file=sys.stderr, flush=True)
                    try:
                        LOGIN.settle_borrow(borrow)
                    except LOGIN.CredentialRecovery as error:
                        print(LOGIN.recovery_message(error), file=sys.stderr, flush=True)
                        code = LOGIN.RECOVERY_EXIT
            finally:
                os._exit(code)
        os.close(read)
        self.pid, self.write = pid, write

    def release(self):
        """After this process settled the borrow itself: the guard ends without doing anything."""
        if self.pid is not None:
            os.write(self.write, b'1')
            os.close(self.write)
            os.waitpid(self.pid, 0)
            self.pid = None


class Borrowed:
    def __init__(self, stop, borrow, guard):
        self.stop, self.borrow, self._guard = stop, borrow, guard

    def guard(self, command, env):
        """Once the slice exists: `command` stops it should this process be killed outright."""
        self._guard.start(self.borrow, command, env)


@contextmanager
def borrowed_profiles(base, args, engines):
    """Hold each source login's lease (<login>/.runner-lease, the one the runners and the sandbox
    launcher take) through every capture, control and engine teardown, and write rotations back
    before releasing it. A borrow an earlier capture or launcher left unsettled is recovered first."""
    sources = []
    for engine in sorted(engines):
        name = '.credentials.json' if engine == 'claude' else 'auth.json'
        profile = base / (engine + '-login')
        profile.mkdir(mode=0o700)
        source = Path(args[engine + '_profile']).expanduser().resolve() / name
        if not source.is_file():
            raise ValueError('No file-backed subscription login in the supplied ' + engine + ' profile')
        sources.append((source, engine + '-login/' + name))
    args['claude_code_profile'] = str(base / 'claude-login')
    args['codex_profile'] = str(base / 'codex-login')
    LOGIN.recover_orphans()
    guard = Guard()
    with LOGIN.Stop() as stop:
        try:
            with LOGIN.borrowed_credentials(base, sources, base) as borrow:
                try:
                    yield Borrowed(stop, borrow, guard)
                finally:
                    stop.closing = True
        finally:
            guard.release()


SENSITIVE = re.compile(r'token|key|secret|authoriz|credential|bearer|cookie|password|[A-Za-z0-9+/=_-]{40,}', re.I)


def diagnose(path, label, work, record, page):
    """A failed run's receiver messages and record lines, with any sensitive-looking line dropped."""
    if not path:
        return
    # Codes and names only, never a value: the launch's own result and refusal, the record's state and
    # refusal, and each receiver message's event with its refusal code. These survive the filter below.
    record = record or {}
    codes = ['launch: result=%s refusal=%s owned=%s' % (getattr(work, 'result', None), getattr(work, 'refusal', None),
                                                        getattr(work, 'owned', None)),
             'record: state=%s refusal=%s reason=%s' % (record.get('state'), record.get('refusal'), record.get('reason'))]
    for message in getattr(work, 'messages', []) or []:
        if isinstance(message, dict):
            codes.append('event: %s refusal=%s keys=%s' % (message.get('event'), message.get('refusal'),
                                                           ','.join(sorted(message))))
    with open(path, 'a') as handle:
        handle.write('\n'.join(codes) + '\n')
    lines = ['== ' + label, 'record: ' + json.dumps({k: record.get(k) for k in sorted(record)
                                                    if k not in ('execution_record',)}, default=str)[:4000]]
    for message in getattr(work, 'messages', []) or []:
        lines.append('message: ' + json.dumps(message, default=str)[:2000])
    for row in (page or {}).get('lines', []):
        lines.append(row['stream'] + ': ' + row['payload'][:600])
    kept = [l for l in lines if not SENSITIVE.search(l)]
    with open(path, 'a') as handle:
        handle.write('\n'.join(kept) + '\n(dropped %d sensitive-looking lines)\n' % (len(lines) - len(kept)))


def codex_model(model, engine):
    modes = engine.MODEL_TOOL_MODES
    if model not in modes:
        raise SystemExit('A qualified codex-model is required: ' + model)
    return model


def capture(f, engine, mode, marker, evidence, diagnostics=None):
    role = engine + '-' + mode
    contract = f.prepare(engine, engine + '-' + mode + ('-planted' if marker else '-control'), {'role': role},
                         {'task': 'Reply with the word ready. Do not invoke any tools.'})
    work = f.launch(engine, contract)
    record = f.finish(engine, work)
    label = engine + ' ' + mode + (' planted' if marker else ' control')
    try:
        page = f.L.ER.read(f.state / 'records', work.dispatch_id, 0, 100000, record.get('execution_record'))
    except f.L.ER.Refused as error:
        diagnose(diagnostics, label + ' (no record: ' + str(error) + ')', work, record, None)
        raise
    if diagnostics and not f.D.completed(record):
        diagnose(diagnostics, label, work, record, page)
    revision = contract['capability']['configuration']['role_revision']
    baseline = next((e['baseline'] for e in work.messages if e.get('event') == 'baseline'), {})
    artifact = next((e['artifact'] for e in work.messages if e.get('event') == 'artifact'), {})
    document = json.loads(Path(artifact['path']).read_text()) if artifact.get('path') else {}
    events, debug, retained = [], [], []
    for row in page['lines']:
        retained.append(row['payload'])
        if row['stream'] == 'stderr':
            debug.append(row['payload'])
        if row['stream'] == 'engine':
            try:
                event = json.loads(row['payload'])
            except ValueError:
                continue
            events.append(event)
    init = next((e for e in events if e.get('type') == 'system' and e.get('subtype') == 'init'), {})
    # The engine's own built-in commands, as its initialize answer marks them (names only).
    answer = next((((e.get('response') or {}).get('response') or {}) for e in events if e.get('type') == 'control_response'
                   and isinstance(((e.get('response') or {}).get('response') or {}).get('commands'), list)), {})
    builtin = list(f.L.HANDOFF.builtin_commands(answer.get('commands')))
    init = {k: init[k] for k in ('tools', 'mcp_servers', 'slash_commands', 'skills', 'plugins', 'model') if k in init}
    options = baseline.get('options') or []
    disallowed = next((a.split('=', 1)[1].split(',') for a in options if a.startswith(P + 'disallowedTools=')), [])
    configuration = {}
    for index, option in enumerate(options):
        if option == '-c':
            def merge(target, source):
                for k, v in source.items():
                    if isinstance(v, dict): merge(target.setdefault(k, {}), v)
                    else: target[k] = v
            merge(configuration, tomllib.loads(options[index + 1]))
    # The engine's own MCP listing is retained in its launch evidence, before the prompt.
    listing = next((e['listing'] for e in work.messages if e.get('event') == 'capability_listing'), [])
    helper = f.L.HANDOFF
    expected = baseline.get('capabilities') or {}
    cred = next((e['credentials'] for e in work.messages if e.get('event') == 'credentials'), {})
    text = '\n'.join(retained)
    debug_text = '\n'.join(debug)
    # Only context counts survive from model messages; no answer or reasoning is retained.
    context_events = []
    for event in events:
        value = helper.context_size(event, revision['engine'])
        if value is None: continue
        if engine == 'claude':
            message = event.get('message') or (event.get('event') or {}).get('message', {})
            context_events.append({'type':'assistant', 'message':{'usage':message['usage']}})
        else:
            context_events.append({'type':'turn.completed', 'usage':event['usage']})
        break
    wire = None
    wire_tools = []
    if engine == 'codex':
        loopback = load('role_loopback', HERE / 'loopback.py')
        qualified = json.loads(f.codex_qualification.read_text())
        catalog = helper.codex_model(qualified, revision)
        wire = loopback.capture(document['executable']['path'], configuration, catalog=catalog)
        wire_tools = [evidence.wire_observation(r['body'], expected, helper) for r in wire['requests']]
    return {'mode':mode, 'marker':marker, 'completed':f.D.completed(record), 'revision':revision,
            'executable_digest':document.get('executable',{}).get('sha256'), 'init':init, 'expected':expected,
            'builtin_commands':builtin, 'probe':document.get('probe'),
            'disallowed':disallowed, 'configuration':configuration, 'listing':listing, 'wire_capture':wire, 'wire_tools':wire_tools,
            'model_catalog':catalog if engine == 'codex' else None,
            'first_turn_context':document.get('first_turn_context'), 'context_events':context_events,
            'credential_sources':cred.get('credentials'), 'record_commitment':record.get('execution_record'),
            'marker_present':'VELDO0127_UNLISTED_MARKER' in text,
            'debug_bytes':len(debug_text.encode()), 'debug_sha256':hashlib.sha256(debug_text.encode()).hexdigest(),
            'debug_marker_present':'VELDO0127_UNLISTED_MARKER' in debug_text,
            'debug_lines':[s for s in debug if 'CLAUDE.md' in s or 'instruction' in s.lower()][:30]}


def discovery_control(binary, profile, evidence):
    """Lead-only positive control: explicitly enable instruction discovery in a scratch project."""
    with tempfile.TemporaryDirectory(prefix='v127-debug-control-') as temp:
        root = Path(temp)
        (root / 'CLAUDE.md').write_text('VELDO0127_UNLISTED_MARKER ' * evidence.MARKER_REPETITIONS)
        debug = root / 'debug.log'
        env = {'PATH':'/usr/bin:/bin', 'HOME':temp, 'CLAUDE_CONFIG_DIR':str(profile),
               'DISABLE_AUTOUPDATER':'1', 'CLAUDE_CODE_DISABLE_AUTO_MEMORY':'1'}
        # This control runs outside the factory slice. Reap its entire process group on failure
        # or a handled stop before the borrowed profile can be written back.
        with subprocess.Popen([str(binary), '-p', 'Reply ready without tools.', P + 'verbose',
                               P + 'output-format', 'stream-json', P + 'debug-file', str(debug)],
                              cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True, start_new_session=True) as child:
            try:
                child.communicate(timeout=90)
            finally:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.wait()
            returncode = child.returncode
        text = debug.read_text() if debug.is_file() else ''
        lines = [line for line in text.splitlines() if 'CLAUDE.md' in line]
        return {'ran':True, 'returncode':returncode, 'debug_bytes':len(text.encode()),
                'debug_lines':lines, 'debug_sha256':hashlib.sha256(text.encode()).hexdigest(),
                'qualification':'debug-and-context' if lines else 'context-size-only'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ('claude', 'codex', 'claude-profile', 'codex-profile', 'claude-model', 'codex-model'):
        parser.add_argument(P + option, required=True)
    # Diagnosis only: one engine, one mode and one marker choice, printed, never written as a capture.
    parser.add_argument(P + 'only', help='engine (its whole capture, written) or engine:mode:control|planted (printed only)')
    # Judges a written capture again with the current evidence.py, without running any worker.
    parser.add_argument(P + 'rejudge', help='engine whose written capture is judged again')
    parser.add_argument(P + 'diagnostics', help='a file under /run/user/UID/ for redacted failed-run lines')
    args = vars(parser.parse_args())
    only = tuple(args.pop('only').split(':')) if args.get('only') else None
    rejudge = args.pop('rejudge')
    if rejudge:
        evidence = load('role_live_evidence', HERE / 'evidence.py')
        handoff = load('role_live_handoff', ROOT / '.veldo' / 'control_agent_config_handoff.py')
        path = HERE / (rejudge + '-live.json')
        result = json.loads(path.read_text())
        result['problems'] = evidence.problems(ROOT, rejudge, result, handoff)
        path.write_text(json.dumps(result, indent=1, sort_keys=True) + '\n')
        print(rejudge + ': ' + ('captured' if not result['problems'] else '; '.join(result['problems'])))
        return
    engines = ('claude', 'codex')
    if only is not None and len(only) == 1:
        engines, only = only, None
    if 'codex' in engines:
        codex_model(args['codex_model'], load('lead_codex', ROOT / '.veldo/control_engine_codex.py'))
    diagnostics = args.pop('diagnostics')
    if diagnostics and not diagnostics.startswith('/run/user/' + str(os.getuid()) + '/'):
        raise SystemExit('diagnostics must be under /run/user/' + str(os.getuid()))
    evidence = load('role_live_evidence', HERE / 'evidence.py')
    fixture = load('role_live_factory', HERE / 'factory.py')
    with tempfile.TemporaryDirectory(prefix='veldo0127-live-', dir='/run/user/' + str(os.getuid())) as temp:
        base = Path(temp)
        selected = (only[0],) if only else engines
        with borrowed_profiles(base, args, selected) as borrowed:
            f = fixture.factory(ROOT, base, {n:ROOT / '.veldo' / n for n in evidence.MODULES}, live=args)
            borrowed.guard(['systemctl', P + 'user', 'stop', f.slice_name], f.inherited)
            try:
                for engine in engines:
                    if only and only[0] != engine:
                        continue
                    for mode in ('always', 'deferred'):
                        definition = f.role(engine, engine + '-' + mode, mode == 'deferred')
                        if mode == 'deferred':
                            definition['instructions'].append({'source':'factory','path':'unassigned.md','load':'when assigned'})
                        f.save(definition)
                    result = {'schema':'veldo.role-live/v1', 'engine':engine, 'production':evidence.production(ROOT), 'runs':[]}
                    for mode in ('always', 'deferred'):
                        if only and only[1] != mode:
                            continue
                        if not only or only[2] == 'control':
                            result['runs'].append(capture(f, engine, mode, False, evidence, diagnostics))
                        if only and only[2] != 'planted':
                            continue
                        profile = base / (engine + '-login')
                        marker_paths = [f.src / 'CLAUDE.md', profile / 'CLAUDE.md']
                        if engine == 'codex':
                            marker_paths = [f.src / 'AGENTS.md']
                        for path in marker_paths:
                            path.write_text(('VELDO0127_UNLISTED_MARKER ' * evidence.MARKER_REPETITIONS) + '\n')
                        try:
                            result['runs'].append(capture(f, engine, mode, True, evidence, diagnostics))
                        finally:
                            for path in marker_paths: path.unlink()
                    if engine == 'claude' and not only:
                        result['debug_control'] = discovery_control(args['claude'], base / 'claude-login', evidence)
                    result['problems'] = evidence.problems(ROOT, engine, result, f.L.HANDOFF)
                    if only:
                        for run in result['runs']:
                            print(json.dumps({k: run[k] for k in ('mode', 'marker', 'completed', 'init', 'expected',
                                                                  'first_turn_context', 'listing', 'marker_present',
                                                                  'debug_marker_present', 'credential_sources')}))
                        print(engine + ' (diagnosis only, not written): ' + '; '.join(result['problems']))
                        continue
                    (HERE / (engine + '-live.json')).write_text(json.dumps(result, indent=1, sort_keys=True) + '\n')
                    print(engine + ': ' + ('captured' if not result['problems'] else '; '.join(result['problems'])))
            finally:
                borrowed.stop.closing = True
                try:
                    for connection in f.connections:
                        connection.close()
                finally:
                    # Wait for systemd's stop job, including its own kill timeout, before saving.
                    subprocess.run(['systemctl', P + 'user', 'stop', f.slice_name],
                                   env=f.inherited, capture_output=True, check=True)


if __name__ == '__main__':
    try:
        main()
    except LOGIN.CredentialRecovery as error:
        print(LOGIN.recovery_message(error), file=sys.stderr, flush=True)
        sys.exit(LOGIN.RECOVERY_EXIT)
