"""The hermetic fence's Git stand-in (support/identity_wire.py): no fixture Git reaches the network
or a real credential store.

    hermetic_git.py <fence directory> <git argument>...

The fence's `git` on PATH runs this for an identity invocation and for every invocation naming a
transport command; everything else goes straight to /usr/bin/git. For an identity invocation it
first does what the identity wire does (log it, run a suite's before-push program, replace each
registered URL by its local repository). Then, for a transport command, every repository the
command would contact is resolved the way Git resolves it (`ls-remote --get-url`, the remote's
pushurl values) and must be local: a path, a file URL, http on a loopback host, ssh only through a
command that is not the real ssh client, or an ext:: command. Anything else is refused before Git
runs, recorded in the fence's violation log and reported on standard error with exit status 97,
so the row that asked for it fails loudly. As a second wall Git runs with GIT_ALLOW_PROTOCOL naming
only the protocols judged local and with an unreachable HTTP proxy for every non-loopback host.

A credential helper read from the real user's global or system configuration (where a host's real
store, such as a `gh auth git-credential` helper, lives) is replaced, in place, by the fence's
guard helper, which records a violation if Git ever asks it for a credential. Helpers a fixture
configures are kept as they are.

The helper lives with the suites and is never installed.
"""
import json
import os
import subprocess
import sys
from urllib.parse import urlsplit

REAL_GIT = '/usr/bin/git'
LOOPBACK = ('127.0.0.1', 'localhost', '::1')
TRANSPORT = {'push', 'fetch', 'pull', 'ls-remote', 'clone', 'fetch-pack', 'send-pack', 'remote', 'archive'}
# Options of the transport commands that take their value as the next argument.
VALUED = {'-o', '--push-option', '--receive-pack', '--exec', '--upload-pack', '--depth', '--server-option',
          '--repo', '--shallow-since', '--shallow-exclude', '--negotiation-tip', '--filter', '-b', '--branch',
          '--origin', '-u', '--template', '--reference', '--reference-if-able', '--separate-git-dir',
          '-j', '--jobs', '--config', '--sort', '--bundle-uri'}
GLOBAL_VALUED = {'-C', '-c', '--git-dir', '--work-tree', '--namespace', '--config-env', '--exec-path'}

fence, args = sys.argv[1], sys.argv[2:]
conf = json.load(open(os.path.join(fence, 'fence.json')))


def violate(kind, detail):
    with open(conf['violations'], 'a') as log:
        log.write(json.dumps({'kind': kind, 'detail': detail, 'argv': args}) + '\n')
    sys.stderr.write('VELDO HERMETIC FENCE: refused (%s) %s\n' % (kind, detail))
    sys.exit(97)


# The identity wire's part: only an invocation carrying the identity transport's options.
if 'credential.interactive=false' in args and conf.get('map'):
    with open(conf['log'], 'a') as log:
        log.write(json.dumps(args) + '\n')
    remotes = json.load(open(conf['map']))
    if 'push' in args and os.path.exists(conf['hook']):
        tail = [a for a in args[args.index('push') + 1:] if not a.startswith('-')]
        lines = ''.join('%s %s %s %s\n' % (src, src, dst, '0' * 40)
                        for src, _, dst in (spec.partition(':') for spec in tail[1:]))
        subprocess.run(json.load(open(conf['hook'])), input=lines, text=True, check=True)
    args = [remotes.get(a, a) for a in args]

prefix, i = [], 0
while i < len(args):
    if args[i] in GLOBAL_VALUED:
        prefix += args[i:i + 2]
        i += 2
    elif args[i].startswith('-'):
        prefix.append(args[i])
        i += 1
    else:
        break
command, rest = (args[i], args[i + 1:]) if i < len(args) else ('', [])


def git_out(*more):
    done = subprocess.run([REAL_GIT, *prefix, *more], capture_output=True, text=True, errors='surrogateescape')
    return done.stdout if done.returncode == 0 else ''


def positionals(items):
    found, j = [], 0
    while j < len(items):
        if items[j] == '--':
            return found + items[j + 1:]
        if items[j] in VALUED:
            j += 2
            continue
        if not items[j].startswith('-'):
            found.append(items[j])
        j += 1
    return found


def remotes_of(names):
    configured = git_out('remote').split()
    return [n for n in names if n in configured] if names else configured


candidates = []
if command in TRANSPORT and not (command == 'ls-remote' and '--get-url' in rest):
    named = positionals(rest)
    if command == 'remote':
        sub = named[0] if named else ''
        if (sub == 'show' and '-n' not in rest) or sub in ('update', 'prune') or (sub == 'set-head' and ({'-a', '--auto'} & set(rest))):
            candidates = remotes_of(named[1:])
    elif command == 'archive':
        candidates = [a.split('=', 1)[1] for a in rest if a.startswith('--remote=')]
    elif command == 'clone':
        candidates = named[:1]
    else:
        candidates = named[:1] or remotes_of([])

urls = []
for candidate in candidates:
    resolved = git_out('ls-remote', '--get-url', '--', candidate).strip()
    urls.append(resolved or candidate)
    if command in ('push', 'send-pack'):
        urls += git_out('config', '--get-all', 'remote.%s.pushurl' % candidate).splitlines()

ssh_command = (git_out('config', '--get', 'core.sshCommand').strip() or os.environ.get('GIT_SSH_COMMAND')
               or os.environ.get('GIT_SSH') or 'ssh')
ssh_word = (ssh_command.split() or ['ssh'])[0]
real_ssh = os.path.basename(ssh_word.strip('\'"')) == 'ssh'
protocols = {'file', 'http'}


def judge(url):
    """The protocol a URL needs when it is local; None when it would leave the host."""
    if '::' in url and '://' not in url.split('::', 1)[0]:
        helper, address = url.split('::', 1)
        if helper == 'ext':
            return 'ext'
        inner = judge(address)
        return helper if inner else None
    if '://' in url:
        try:
            parts = urlsplit(url)
            host = parts.hostname or ''
        except ValueError:
            return None
        if parts.scheme == 'file':
            return 'file'
        if parts.scheme in ('http', 'https') and (host in LOOPBACK or host.startswith('127.')):
            return parts.scheme
        if parts.scheme in ('ssh', 'git+ssh', 'ssh+git') and not real_ssh:
            return 'ssh'
        return None
    head = url.split('/', 1)[0]
    if ':' in head and not url.startswith(('/', '.')):
        return None if real_ssh else 'ssh'
    return 'file'


for url in urls:
    needed = judge(url)
    if needed is None:
        violate('network', '%s would contact %s' % (command, url))
    protocols.add(needed)

env = dict(os.environ)
injected = []
if command in TRANSPORT:
    env.update(GIT_ALLOW_PROTOCOL=':'.join(sorted(protocols)), NO_PROXY=','.join(LOOPBACK),
               no_proxy=','.join(LOOPBACK), GIT_TERMINAL_PROMPT='0')
    injected += ['-c', 'http.proxy=http://127.0.0.1:9']
    # Credential helpers in the order Git reads them; a real store's entry becomes the guard's.
    listed = git_out('config', '--show-origin', '--null', '--get-regexp', r'^credential\..*helper$').split('\0')
    entries = [(listed[k], listed[k + 1]) for k in range(0, len(listed) - 1, 2)]
    if any(origin[len('file:'):] in conf['real_configs'] for origin, _ in entries if origin.startswith('file:')):
        injected += ['-c', 'credential.helper=']
        for origin, entry in entries:
            key, _, value = entry.partition('\n')
            real = origin.startswith('file:') and origin[len('file:'):] in conf['real_configs']
            injected += ['-c', key + '=' + ('!' + conf['guard'] if real and value else value)]
os.execve(REAL_GIT, ['git', *injected, *args], env)
