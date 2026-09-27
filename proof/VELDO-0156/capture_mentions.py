#!/usr/bin/env python3
"""What the installed Codex binary itself sends the model when the prompt names a skill, VELDO-0156.

Runs the real `codex exec` of the pinned 0.154.0 binary against a model provider on loopback that this
process serves itself: it records each request body and answers 400, so the binary stops after its
retries and no model runs. A scratch CODEX_HOME and HOME hold no login and no configuration file (the state
`--ignore-user-config` gives the account profile's config.toml); nothing logs in, no profile of the owner
is read. Before anything runs, this process denies itself every TCP connect but the one loopback port
(Landlock, inherited by the binary) and points every proxy variable at a dead loopback port.

Each capture plants a skill in each place the binary reads skills from (the profile's skills/, with the
bundled set the binary installs into its .system, HOME/.agents/skills and the clone's .agents/skills and
.codex/skills) and, as controls, where it does not (the directory above the clone's root, a subdirectory
below the working directory, HOME/.codex/skills beside another CODEX_HOME, and a skill planted in .system
among the binary's own), names every one in the prompt, written as the receiver writes it (a JSON packet on
standard input), and records whether each skill's body is in any model request. Writes
proof/VELDO-0156/codex-mentions.json.

    python3 -B proof/VELDO-0156/capture_mentions.py [--codex PATH]            # write
    python3 -B proof/VELDO-0156/capture_mentions.py --check [--codex PATH]    # compare, exit 1 on a change
"""
import argparse
import ctypes
import http.server
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading

HERE = Path(__file__).resolve().parent
OUT = HERE / 'codex-mentions.json'
sys.path.insert(0, str(HERE))
from extract_baseline import DEFAULT_CODEX, VERSION, _digest  # noqa: E402

PORT = 18656
# Where each planted skill goes, relative to the scratch root: ch is CODEX_HOME, home is HOME, clone is the
# engine's working directory and its project root.
PLACES = {
    'skill_profile': 'ch/skills/v156m-profile-skill',
    'skill_home_agents': 'home/.agents/skills/v156m-home-skill',
    'skill_clone_agents': 'clone/.agents/skills/v156m-clone-skill',
    'skill_clone_codex': 'clone/.codex/skills/v156m-clone-codex-skill',
    'control_above_root': '.agents/skills/v156m-above-skill',
    'control_below_cwd': 'clone/sub/.agents/skills/v156m-below-skill',
    'control_home_codex': 'home/.codex/skills/v156m-home-codex-skill',
    'control_system_planted': 'ch/skills/.system/v156m-system-skill',
}
BUNDLED = 'imagegen'
# A line of the bundled imagegen SKILL.md body, the text the binary carries and installs into .system.
BUNDLED_MARKER = '# Image Generation Skill'
# The previous baseline (the review's), the shipped one, and each switch tried against the four places.
PREVIOUS = ['--ignore-user-config', '--ignore-rules', '--disable', 'apps', '-c', 'project_doc_max_bytes=0',
            '-c', 'forced_login_method="chatgpt"', '-c', 'cli_auth_credentials_store="file"',
            '-c', 'skills.include_instructions=false']
BUNDLED_OFF = ['-c', 'skills.bundled.enabled=false']
CANDIDATES = {
    'skills.enabled=false': ['-c', 'skills.enabled=false'],
    '--enable skip_host_skill_discovery': ['--enable', 'skip_host_skill_discovery'],
    '--disable mentions_v2': ['--disable', 'mentions_v2'],
    '--disable skill_search': ['--disable', 'skill_search'],
    'project_root_markers=[]': ['-c', 'project_root_markers=[]'],
    'the clone untrusted': ['-c', 'projects."{clone}".trust_level="untrusted"'],
}
# The one per-skill selector that works: a skills.config entry naming the skill's own file.
SELECTOR = ['-c', 'skills.config=[{path="{ch}/skills/v156m-profile-skill/SKILL.md", enabled=false}]']


def deny_network(port):
    """Landlock: this process and everything it starts may connect over TCP to `port` only."""
    libc = ctypes.CDLL(None, use_errno=True)
    create, add, restrict = 444, 445, 446

    class Attr(ctypes.Structure):
        _fields_ = [('fs', ctypes.c_uint64), ('net', ctypes.c_uint64), ('scoped', ctypes.c_uint64)]

    class Port(ctypes.Structure):
        _pack_ = 1
        _fields_ = [('allowed', ctypes.c_uint64), ('port', ctypes.c_uint64)]
    abi = libc.syscall(ctypes.c_long(create), None, ctypes.c_size_t(0), ctypes.c_uint32(1))
    if abi < 4:
        raise SystemExit('landlock ABI %d < 4: refusing to run the binary without the network guard' % abi)
    attr = Attr(0, 1 << 1, 0)
    size = ctypes.sizeof(attr) if abi >= 6 else 16
    fd = libc.syscall(ctypes.c_long(create), ctypes.byref(attr), ctypes.c_size_t(size), ctypes.c_uint32(0))
    rule = Port(1 << 1, port)
    if (fd < 0 or libc.syscall(ctypes.c_long(add), ctypes.c_int(fd), ctypes.c_int(2), ctypes.byref(rule),
                               ctypes.c_uint32(0)) != 0
            or libc.prctl(38, 1, 0, 0, 0) != 0
            or libc.syscall(ctypes.c_long(restrict), ctypes.c_int(fd), ctypes.c_uint32(0)) < 0):
        raise SystemExit('the network guard could not be installed')
    os.close(fd)


class Endpoint(http.server.BaseHTTPRequestHandler):
    """The loopback model provider: every request body kept, every request answered 400."""
    bodies = []

    def do_POST(self):
        Endpoint.bodies.append(self.rfile.read(int(self.headers.get('content-length') or 0)).decode('utf-8', 'replace'))
        self.send_response(400)
        self.send_header('content-type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"error":{"message":"v156 loopback","type":"invalid_request_error"}}')

    def do_GET(self):
        self.send_response(404)
        self.end_headers()

    def log_message(self, *args):
        pass


def skill(path, key):
    path.mkdir(parents=True, exist_ok=True)
    (path / 'SKILL.md').write_text('---\nname: %s\ndescription: planted %s\n---\nV156M-%s-BODY\n' % (path.name, key, key))


def capture(codex, extra, plant=True, preinstalled=False):
    root = Path(tempfile.mkdtemp(prefix='v156-mentions-'))
    try:
        ch, home, clone = root / 'ch', root / 'home', root / 'clone'
        for directory in (ch, home, clone):
            directory.mkdir()
        subprocess.run(['git', 'init', '-q', str(clone)], check=True, env={'PATH': '/usr/bin:/bin', 'HOME': str(home)})
        names = []
        for key, place in sorted(PLACES.items()) if plant else ():
            skill(root / place, key)
            names.append(Path(place).name)
        names.append(BUNDLED)
        packet = json.dumps({'payload': {'task': 'work the unit with ' + ' and '.join('$' + n for n in names)}})
        dead = 'http://127.0.0.1:9'
        env = {'PATH': '/usr/bin:/bin', 'HOME': str(home), 'CODEX_HOME': str(ch), 'TMPDIR': str(root), 'LANG': 'C.UTF-8',
               'HTTP_PROXY': dead, 'HTTPS_PROXY': dead, 'ALL_PROXY': dead, 'http_proxy': dead, 'https_proxy': dead,
               'NO_PROXY': '127.0.0.1', 'no_proxy': '127.0.0.1'}
        provider = ['-c', 'model_provider="v156m"', '-c', 'model="gpt-5"', '-c',
                    'model_providers.v156m={name="v156m", base_url="http://127.0.0.1:%d/v1", wire_api="responses"}' % PORT]
        extra = [a.replace('{ch}', str(ch)).replace('{clone}', str(clone)) for a in extra]
        if preinstalled:
            # A profile the binary already installed its bundled set into: one run without the switch first.
            subprocess.run([codex, 'exec', '--json', '-c', 'check_for_update_on_startup=false', *PREVIOUS, *provider,
                            '--skip-git-repo-check'], input='{}', cwd=clone, env=env, capture_output=True, text=True,
                           timeout=120)
        Endpoint.bodies = []
        done = subprocess.run([codex, 'exec', '--json', '-c', 'check_for_update_on_startup=false', *extra, *provider,
                               '--skip-git-repo-check'], input=packet, cwd=clone, env=env, capture_output=True,
                              text=True, timeout=120)
        text = '\n'.join(Endpoint.bodies)
        installed = ch / 'skills' / '.system' / BUNDLED / 'SKILL.md'
        present = {key: ('V156M-%s-BODY' % key) in text for key in sorted(PLACES)} if plant else {}
        present['bundled'] = BUNDLED_MARKER in text
        return {'arguments': [a.replace(str(root), '<root>') for a in extra], 'exit': done.returncode,
                'requested': bool(Endpoint.bodies), 'present': present,
                'skills_section': '<skills_instructions>' in text,
                'bundled_installed': installed.is_file() and BUNDLED_MARKER in installed.read_text()}
    finally:
        shutil.rmtree(root, ignore_errors=True)


def observe(codex):
    shipped = PREVIOUS + BUNDLED_OFF
    return {
        'binary': str(codex), 'version': VERSION, 'sha256': _digest(codex),
        'commands': ['codex exec --json -c check_for_update_on_startup=false [arguments] -c model_provider=<loopback> '
                     '--skip-git-repo-check < {"payload": {"task": "work the unit with $<each skill> and $imagegen"}}'],
        'places': PLACES,
        'previous_baseline': capture(codex, PREVIOUS),
        'baseline': capture(codex, shipped),
        'baseline_bundled_preinstalled': capture(codex, shipped, preinstalled=True),
        'candidates': {name: capture(codex, shipped + arguments)['present'] for name, arguments in sorted(CANDIDATES.items())},
        'selector': capture(codex, shipped + SELECTOR)['present'],
        'listing': {'baseline': capture(codex, shipped, plant=False),
                    'include_instructions_default': capture(codex, PREVIOUS[:-2] + BUNDLED_OFF, plant=False)},
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--codex', default=str(DEFAULT_CODEX))
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    if Path(args.codex).read_bytes().count(BUNDLED_MARKER.encode()) < 1:
        sys.stderr.write('moved: the bundled marker is not in the binary\n')
        return 1
    deny_network(PORT)
    server = http.server.HTTPServer(('127.0.0.1', PORT), Endpoint)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        table = observe(args.codex)
    finally:
        server.shutdown()
    for name in ('previous_baseline', 'baseline', 'baseline_bundled_preinstalled'):
        if not table[name]['requested']:
            sys.stderr.write('the binary sent no model request under %s (exit %s)\n' % (name, table[name]['exit']))
            return 1
    text = json.dumps(table, indent=1, sort_keys=True).replace(str(args.codex), '<codex>') + '\n'
    if args.check:
        same = OUT.is_file() and OUT.read_text() == text
        print('codex-mentions.json %s' % ('matches the binary' if same else 'differs from the binary'))
        return 0 if same else 1
    OUT.write_text(text)
    print('wrote %s' % OUT)
    return 0


if __name__ == '__main__':
    sys.exit(main())
