#!/usr/bin/env python3
"""What the installed Codex binary itself puts in front of the model under the baseline, VELDO-0156.

Runs only the binary's OFFLINE commands, with a scratch CODEX_HOME and HOME that hold no login and no
configuration file (the state `--ignore-user-config` gives the account profile's config.toml): `codex debug
prompt-input` renders the model-visible prompt input list as JSON, and `codex features list` prints the
feature table a launch would run with. Before anything runs, this process denies itself every TCP connect
(Landlock, inherited by the binary) and points every proxy variable at a dead loopback port, so nothing
reaches a host; no model runs, nothing logs in, no profile of the owner is read. Writes
proof/VELDO-0156/codex-rendered.json: for each planted item (the profile's AGENTS.md and
AGENTS.override.md, a skill in each place the binary reads skills from) whether its marker is in the
rendered prompt under each configuration, and whether the apps feature (the login's ChatGPT connectors)
is on.

    python3 -B proof/VELDO-0156/render_offline.py [--codex PATH]            # write
    python3 -B proof/VELDO-0156/render_offline.py --check [--codex PATH]    # compare, exit 1 on a change
"""
import argparse
import ctypes
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
OUT = HERE / 'codex-rendered.json'
sys.path.insert(0, str(HERE))
from extract_baseline import DEFAULT_CODEX, VERSION, _digest  # noqa: E402

MARKERS = {
    'profile_agents_md': 'V156-PROFILE-AGENTS-MARKER',
    'profile_agents_override_md': 'V156-PROFILE-OVERRIDE-MARKER',
    'clone_agents_md': 'V156-CLONE-AGENTS-MARKER',
    'skill_profile': 'v156-profile-skill',
    'skill_home_agents': 'v156-home-agents-skill',
    'skill_clone_agents': 'v156-clone-agents-skill',
    'skill_clone_codex': 'v156-clone-codex-skill',
    'skills_section': '<skills_instructions>',
}
# The configuration the baseline passes as overrides today, and each candidate switch tried against the
# profile's own instruction file (none of them is documented to turn it off; each is tried so the record
# shows what was ruled out).
BASE = ['-c', 'project_doc_max_bytes=0']
SKILLS_OFF = ['-c', 'skills.include_instructions=false']
INSTRUCTION_CANDIDATES = ['instructions=""', 'developer_instructions=""', 'include_environment_context=false',
                          'include_permissions_instructions=false', 'project_doc_fallback_filenames=[]']


def deny_network():
    """Landlock: this process and everything it starts may not connect over TCP (loopback included)."""
    libc = ctypes.CDLL(None, use_errno=True)
    create, restrict = 444, 446

    class Attr(ctypes.Structure):
        _fields_ = [('fs', ctypes.c_uint64), ('net', ctypes.c_uint64), ('scoped', ctypes.c_uint64)]
    abi = libc.syscall(ctypes.c_long(create), None, ctypes.c_size_t(0), ctypes.c_uint32(1))
    if abi < 4:
        raise SystemExit('landlock ABI %d < 4: refusing to run the binary without the network guard' % abi)
    attr = Attr(0, 1 << 1, 0)
    size = ctypes.sizeof(attr) if abi >= 6 else 16
    fd = libc.syscall(ctypes.c_long(create), ctypes.byref(attr), ctypes.c_size_t(size), ctypes.c_uint32(0))
    if fd < 0 or libc.prctl(38, 1, 0, 0, 0) != 0 or libc.syscall(ctypes.c_long(restrict), ctypes.c_int(fd),
                                                                  ctypes.c_uint32(0)) < 0:
        raise SystemExit('the network guard could not be installed')
    os.close(fd)


def plant(root, items):
    ch, home, repo = root / 'codex-home', root / 'home', root / 'clone'
    for directory in (ch, home, repo):
        directory.mkdir(parents=True)
    subprocess.run(['git', 'init', '-q', str(repo)], check=True, env={'PATH': '/usr/bin:/bin', 'HOME': str(home)})

    def skill(base, key):
        name = MARKERS[key]
        (base / name).mkdir(parents=True)
        (base / name / 'SKILL.md').write_text('---\nname: %s\ndescription: planted %s\n---\nbody\n' % (name, name))
    if 'profile_agents_md' in items:
        (ch / 'AGENTS.md').write_text(MARKERS['profile_agents_md'] + '\n')
    if 'profile_agents_override_md' in items:
        (ch / 'AGENTS.override.md').write_text(MARKERS['profile_agents_override_md'] + '\n')
    (repo / 'AGENTS.md').write_text(MARKERS['clone_agents_md'] + '\n')
    skill(ch / 'skills', 'skill_profile')
    skill(home / '.agents' / 'skills', 'skill_home_agents')
    skill(repo / '.agents' / 'skills', 'skill_clone_agents')
    skill(repo / '.codex' / 'skills', 'skill_clone_codex')
    return ch, home, repo


def environment(root, ch, home):
    dead = 'http://127.0.0.1:9'
    return {'PATH': '/usr/bin:/bin', 'HOME': str(home), 'CODEX_HOME': str(ch), 'TMPDIR': str(root),
            'LANG': 'C.UTF-8', 'HTTP_PROXY': dead, 'HTTPS_PROXY': dead, 'ALL_PROXY': dead, 'http_proxy': dead,
            'https_proxy': dead, 'NO_PROXY': ''}


def render(codex, items, extra):
    root = Path(tempfile.mkdtemp(prefix='v156-render-'))
    try:
        ch, home, repo = plant(root, items)
        done = subprocess.run([codex, 'debug', 'prompt-input', *BASE, *extra, 'hello'], cwd=repo,
                              env=environment(root, ch, home), capture_output=True, text=True, timeout=120)
        text = done.stdout
        bundled = sorted(p.name for p in (ch / 'skills' / '.system').glob('*') if p.is_dir())
        return {'overrides': BASE + list(extra), 'planted': sorted(items) + ['clone_agents_md', 'skills'],
                'exit': done.returncode, 'rendered': done.returncode == 0 and text.lstrip().startswith('['),
                'present': {key: marker in text for key, marker in sorted(MARKERS.items())},
                'bundled_installed': bundled,
                'bundled_rendered': sorted(name for name in bundled if ('name: %s' % name) in text or name in text)}
    finally:
        shutil.rmtree(root, ignore_errors=True)


def feature(codex, extra, name):
    root = Path(tempfile.mkdtemp(prefix='v156-features-'))
    try:
        ch, home = root / 'codex-home', root / 'home'
        ch.mkdir()
        home.mkdir()
        done = subprocess.run([codex, *extra, 'features', 'list'], env=environment(root, ch, home), cwd=root,
                              capture_output=True, text=True, timeout=60)
        for line in done.stdout.splitlines():
            parts = line.split()
            if parts and parts[0] == name:
                return {'arguments': list(extra), 'exit': done.returncode, 'stage': ' '.join(parts[1:-1]),
                        'enabled': parts[-1] == 'true'}
        return {'arguments': list(extra), 'exit': done.returncode, 'stage': None, 'enabled': None}
    finally:
        shutil.rmtree(root, ignore_errors=True)


def observe(codex):
    both = ('profile_agents_md', 'profile_agents_override_md')
    return {
        'binary': str(codex), 'version': VERSION, 'sha256': _digest(codex),
        'commands': ['codex debug prompt-input -c project_doc_max_bytes=0 [overrides] hello',
                     'codex [arguments] features list'],
        'profile_instructions': {
            'agents_md': render(codex, ('profile_agents_md',), SKILLS_OFF),
            'agents_override_md': render(codex, both, SKILLS_OFF),
            'candidates': {candidate: render(codex, ('profile_agents_md',), SKILLS_OFF + ['-c', candidate])['present']
                           ['profile_agents_md'] for candidate in INSTRUCTION_CANDIDATES}},
        'skills': {'without_switch': render(codex, (), []), 'with_switch': render(codex, (), SKILLS_OFF)},
        'apps': {'default': feature(codex, [], 'apps'), 'disabled': feature(codex, ['--disable', 'apps'], 'apps')},
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--codex', default=str(DEFAULT_CODEX))
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    deny_network()
    table = observe(args.codex)
    for section in ('profile_instructions', 'skills'):
        for key, value in table[section].items():
            if isinstance(value, dict) and 'rendered' in value and not value['rendered']:
                sys.stderr.write('the binary rendered no prompt for %s.%s (exit %s)\n' % (section, key, value['exit']))
                return 1
    text = json.dumps(table, indent=1, sort_keys=True).replace(str(args.codex), '<codex>') + '\n'
    if args.check:
        same = OUT.is_file() and OUT.read_text() == text
        print('codex-rendered.json %s' % ('matches the binary' if same else 'differs from the binary'))
        return 0 if same else 1
    OUT.write_text(text)
    print('wrote %s' % OUT)
    return 0


if __name__ == '__main__':
    sys.exit(main())
