"""Mac half of the VELDO-0147 relay leg. Runs from the run's own export on the Mac.

The production receiver (control_worker.main) is what runs here: it reads the prepared binding and the
login and secrets frames from this SSH channel, mounts the login on a RAM disk, claims the dispatch from
the Linux authority through the signed relay, runs the pinned engine under the VELDO-0124 supervisor and
reports the result. This driver only prepares a candidate profile, skips the qualification stamp (as the
VELDO-0124 and VELDO-0125 native probes do; nothing here is a qualification), keeps the launchd resumer
uninstalled and writes down what the receiver did, in identifiers, modes and counts, never a value.

Subcommands: prepare ENGINE | configure | receive | summary ENGINE | fetch | clean
"""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import sys
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATE = ROOT / 'state'
HOME = Path(pwd.getpwuid(os.getuid()).pw_dir)
PAID = ('ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'CLAUDE_CODE_OAUTH_TOKEN', 'OPENAI_API_KEY',
        'CODEX_API_KEY', 'CLAUDE_CODE_USE_BEDROCK', 'CLAUDE_CODE_USE_VERTEX')
PROMPT = ('This is a qualification unit. Do exactly these steps and nothing else. '
          '1) Run this exact shell command: ls /nonexistent-veldo-0147; echo leg-done '
          '(it is expected to print an error to its error stream). '
          '2) Change the line "status: draft" to "status: edited" in notes.txt. '
          '3) Reply with the single word DONE.')
sys.path.insert(0, str(ROOT / 'proof/VELDO-0124'))


def native():
    spec = importlib.util.spec_from_file_location('native124', ROOT / 'proof/VELDO-0124/native_checks.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def engine_argv(engine):
    if engine == 'claude_code':
        entry = json.loads((ROOT / 'engine/runtime/claude-qualification.json').read_text())['versions']['2.1.317']
        settings = json.dumps(dict(disableAllHooks=True, disableBundledSkills=True,
                                   enabledPlugins={name: False for name in entry.get('engine_plugins', [])},
                                   skillOverrides={name: 'off' for name in entry.get('engine_skills', [])}),
                              sort_keys=True)
        return '2.1.317', [str(HOME / '.local/share/claude/versions/2.1.317'), '--print', '--output-format',
                           'stream-json', '--verbose', '--setting-sources=', '--strict-mcp-config',
                           '--disable-slash-commands', '--mcp-config', '{"mcpServers":{}}', '--settings', settings,
                           '--include-partial-messages', '--tools=Bash,Edit,Read', '--allowedTools=Bash,Edit,Read',
                           '--model', 'opus', PROMPT]
    record = json.loads((ROOT / 'engine/runtime/codex-qualification.json').read_text())
    options = list(record['flags']) + list(record['baseline']['options'])
    for name, value in sorted(record['baseline']['configuration'].items()):
        options += ['-c', '%s=%s' % (name, json.dumps(value))]
    return record['version'], [str(HOME / 'veldo-mac-runs/engines/codex-%s/codex' % record['version'])] + options + [
        '--skip-git-repo-check', '--sandbox', 'danger-full-access', PROMPT]


def keychain():
    out = subprocess.run(['/usr/bin/security', 'dump-keychain'], capture_output=True, text=True,
                         stdin=subprocess.DEVNULL).stdout
    names = sorted(line.split('=', 1)[1].strip() for line in out.splitlines()
                   if '"svce"' in line and ('Claude' in line or 'codex' in line.lower()))
    return dict(engine_items=len(names), digest=hashlib.sha256('\n'.join(names).encode()).hexdigest())


def ram_disks():
    listing = subprocess.run(['/sbin/mount'], capture_output=True, text=True).stdout
    return sum(1 for line in listing.splitlines() if '/veldo-login-' in line and '(hfs' in line)


def prepare(engine):
    N = native()
    P = N.P
    paths, profile, unused, fixture_facts, request = N.T.fixture(STATE)
    clone = paths['clone']
    (clone / 'notes.txt').write_text('title: mac leg unit\nstatus: draft\n')
    N.T.git('-C', str(clone), 'add', 'notes.txt')
    N.T.git('-C', str(clone), '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
            '-c', 'commit.gpgsign=false', 'commit', '-qm', 'unit')
    source = {kind: N.T.git('-C', str(clone), 'rev-parse', 'HEAD^{%s}' % kind) for kind in ('commit', 'tree')}
    version, argv = engine_argv(engine)
    profile.update(interpreter=N.PINNED, runtime_seconds=420, startup_seconds=30, stop_grace_seconds=2,
                   kill_grace_seconds=2, settle_seconds=5, home=str(HOME))
    profile['engines'][engine].update(argv=argv, version=version, binary_digest=P.file_digest(argv[0]))
    key = paths['authority'] / 'worker-signing'
    subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key)], check=True, capture_output=True)
    profile['signing_keys'] = [str(key)]
    host = N.M.Supervisor(profile, None)
    facts = host.os.facts()
    digest = request['contract']['capability']['configuration_digest']
    route = dict(host=facts['host'], principal='mac', platform='darwin', revision=1,
                 capabilities=['shell', 'macos', 'ios-build'], available=True,
                 engines={name: digest for name in P.ENGINES}, runtime_profile=P.digest(host.profile))
    route['qualification'] = dict(kind='native', reference='CANDIDATE PROBE ONLY, NOT A QUALIFICATION',
                                  profile_digest=P.digest({k: v for k, v in route.items() if k != 'available'}))
    (STATE / 'local.json').write_text(json.dumps(dict(profile=host.profile, key=str(key), source=str(clone),
                                                     engine=engine)))
    (STATE / 'local.json').chmod(0o600)
    (STATE / 'keychain-before.json').write_text(json.dumps(keychain()))
    print(json.dumps(dict(engine=engine, profile=route, source=source, facts=facts, binary_digest=profile['engines'][engine]['binary_digest'],
                          public_key=key.with_suffix('.pub').read_text().strip())))
    return 0


def configure():
    sent = json.loads(sys.stdin.read())
    local = json.loads((STATE / 'local.json').read_text())
    N = native()
    config = dict(profile=local['profile'], qualification=None, signing_key=local['key'], principal='mac',
                  workspace=sent['workspace'], binding=sent['binding'], source=local['source'],
                  ssh_argv=[N.PINNED, str(ROOT / '.veldo/control_relay.py'), sent['socket']],
                  runs=str(STATE / 'runs'), login='delivered',
                  accounts={'account': dict(id='account', provider=local['engine'], status='active')})
    (STATE / 'config.json').write_text(json.dumps(config))
    (STATE / 'config.json').chmod(0o600)
    print(json.dumps(dict(configured=True)))
    return 0


def receive():
    N = native()
    W = N.T.load('control_worker')
    real = W.organ
    seen = dict(order=[])

    def note():
        (STATE / 'delivery.json').write_text(json.dumps(seen, sort_keys=True))

    def organ(name):
        module = real(name)
        if name == 'project_runner_macos':
            # The one step skipped: the qualification stamp. Admission, containment and the run are production's.
            module.Supervisor.preflight = lambda self, request: (
                dict(probe=True, profile_digest=N.P.digest(self.profile)), self.admit(request))
        if name == 'project_runner_macos_login':
            class Watched(module.Delivery):
                def open(self):
                    path = super().open()
                    seen['order'].append('login_open')
                    seen.update(login=self.report['login'], ram_disks_open=ram_disks())
                    note()
                    return path

                def secrets(self):
                    super().secrets()
                    seen['order'].append('secrets_after_acceptance')
                    seen.update(secrets=self.report.get('secrets'))
                    note()

                def close(self):
                    result = super().close()
                    seen['order'].append('close')
                    seen.update(close=result, ram_disks_after=ram_disks(), base_absent=not self.base.exists())
                    note()
                    return result
            module.Delivery = Watched
        return module
    W.organ = organ
    W.install_resumer = lambda *arguments, **named: None  # no launch agent is left on this Mac by a probe
    production = W.receive_locked

    def observed(config, request, frames=None):
        try:
            return production(config, request, frames)
        except BaseException:
            import traceback
            (STATE / 'receive-error.txt').write_text(traceback.format_exc())
            raise
    W.receive_locked = observed
    W.main(str(STATE / 'config.json'))
    return 0


def run_directory():
    if not (STATE / 'runs').is_dir():
        return None
    found = [path for path in (STATE / 'runs').iterdir() if path.is_dir() and not path.name.startswith('.')]
    return found[0] if len(found) == 1 else None


def slot_directory():
    found = list((STATE / 'host').glob('org.veldo.worker.*'))
    return found[0] if len(found) == 1 else None


def summary(engine):
    out = dict(engine=engine, delivery=json.loads((STATE / 'delivery.json').read_text())
               if (STATE / 'delivery.json').exists() else None)
    if (STATE / 'receive-error.txt').exists():
        # The receiver's own failure, with this Mac's home and temp paths replaced.
        text = (STATE / 'receive-error.txt').read_text().replace(str(HOME), '<home>').replace(
            str(Path(os.confstr(65537)).resolve()), '<temp>').replace(os.confstr(65537), '<temp>/')
        out['receive_error'] = text[-1800:]
    slot, run = slot_directory(), run_directory()
    if slot is not None and (slot / 'request.json').exists():
        request = json.loads((slot / 'request.json').read_text())
        environment = request['environment']
        variable = 'CLAUDE_CONFIG_DIR' if engine == 'claude_code' else 'CODEX_HOME'
        temp = os.confstr(65537)
        out['readback'] = dict(
            names=sorted(environment), login_variable=variable,
            login_is_delivered_ram_disk=str(Path(environment.get(variable, '/')).resolve()).startswith(
                str(Path(temp).resolve() / 'veldo-login-')) and environment.get(variable, '').endswith('/profile'),
            other_login_variables=sorted(n for n in ('CLAUDE_CONFIG_DIR', 'CODEX_HOME') if n in environment and n != variable),
            paid_present=sorted(n for n in PAID if n in environment),
            policy_denies_keychain='com.apple.SecurityServer' in request['sandbox'],
            binary_digest=request['binary_digest'], argv_flags=[a for a in request['argv'][1:-1] if a.startswith('-')])
        out['slot'] = (json.loads((slot / 'slot.json').read_text()) or {}).get('state')
        out['engine_err_bytes'] = (slot / 'engine.err').stat().st_size if (slot / 'engine.err').exists() else None
    if run is not None:
        out['run_files'] = sorted(p.name for p in run.iterdir())
        evidence = run / 'result-evidence.json'
        if evidence.exists():
            kept = json.loads(evidence.read_text())
            out['observation'] = dict(state=kept['observation'].get('state'),
                                      termination=kept['observation'].get('termination'),
                                      cleanup=kept['observation'].get('cleanup'), usage=kept.get('usage'))
        archive = run / 'deliverables.tar'
        if archive.exists():
            with tarfile.open(archive) as tar:
                names = tar.getnames()
                if 'engine.out' in names:
                    data = tar.extractfile('engine.out').read()
                    out['engine_out'] = dict(lines=data.count(b'\n'), bytes=len(data),
                                             sha256=hashlib.sha256(data).hexdigest())
                if 'clone/notes.txt' in names:
                    out['file_edited'] = b'status: edited' in tar.extractfile('clone/notes.txt').read()
    before = json.loads((STATE / 'keychain-before.json').read_text())
    out.update(keychain_unchanged=keychain() == before, ram_disks_now=ram_disks(),
               login_bases_now=len(list(Path(os.confstr(65537)).glob('veldo-login-*'))))
    print(json.dumps(out, sort_keys=True))
    return 0


def fetch():
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w:gz') as archive:
        slot, run = slot_directory(), run_directory()
        for directory, names in ((slot, ('request.json', 'engine.out', 'engine.err', 'slot.json', 'go')),
                                 (run, ('result-evidence.json', 'run-context.json', 'result-request.json',
                                        'result-request.json.ack', 'delivery-complete.json'))):
            for name in names if directory is not None else ():
                if (directory / name).exists():
                    archive.add(directory / name, arcname=name)
        if run is not None and (run / 'deliverables.tar').exists():
            with tarfile.open(run / 'deliverables.tar') as tar:
                if 'engine.out' in tar.getnames():
                    data = tar.extractfile('engine.out').read()
                    member = tarfile.TarInfo('deliverables-engine.out')
                    member.size = len(data)
                    archive.addfile(member, io.BytesIO(data))
        for name in ('delivery.json', 'config.json'):
            if (STATE / name).exists():
                archive.add(STATE / name, arcname=name)
    sys.stdout.buffer.write(buffer.getvalue())
    return 0


def clean():
    slot = slot_directory()
    if slot is not None:
        subprocess.run(['/bin/launchctl', 'bootout', 'user/%d/%s' % (os.getuid(), slot.name)], capture_output=True)
    for base in Path(os.confstr(65537)).glob('veldo-login-*'):
        spec = importlib.util.spec_from_file_location('login', ROOT / '.veldo/project_runner_macos_login.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.close_profile(base)
    for temp in Path(os.confstr(65537)).glob('veldo-[0-9a-f]*'):
        shutil.rmtree(temp, ignore_errors=True)
    shutil.rmtree(ROOT, ignore_errors=True)
    print(json.dumps(dict(cleaned=not ROOT.exists(), ram_disks_now=ram_disks())))
    return 0


if __name__ == '__main__':
    command, arguments = sys.argv[1], sys.argv[2:]
    code = dict(prepare=prepare, configure=configure, receive=receive, summary=summary, fetch=fetch,
                clean=clean)[command](*arguments)
    sys.stdout.flush()
    sys.exit(code)
