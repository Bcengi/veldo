"""The repository provisioner's creation steps (VELDO-0143 AC2): a new repository for a settled new-project
decision, made in order, each its own function, every one refused by name.

  directory  the proposal's directory under the identity's projects root: refused directory_not_empty when
             it exists and holds anything (one that is already a Git repository takes the adoption path,
             which the effect decides before this step); otherwise created, or kept when it exists empty.
  init       a Git repository there, on the default branch.
  scaffold   Veldo laid down with init_scaffold.scaffold.
  author     the identity's author configuration written into the repository (VELDO-0142).
  commit     the initial commit, authored and committed by the identity.
  remote     the remote created under the identity's owner through GitHub's REST interface with the
             identity's API token, standard library only: VELDO-0153's one owner check of the URL first
             (binding_mismatch:remote_owner before any network write), then the token from the keystore
             (token_unavailable), then a repository already there (remote_exists), then the creation at the
             chosen visibility, whose answer must name that owner, name and visibility (creation_refused).
  push       the initial commit pushed through git_process's `identity` profile (VELDO-0153) to the checked
             URL, leased on the branch being absent there, and read back (push_refused:remote).

STEPS names them in order; the effect (control_effect_executor_creation) records each on the repository
record and stops at the first refusal. Every local Git step runs under the isolated profile with no hook.
Observations and refusals carry the repository, the identity, the owner and the step, never the token.
"""
import importlib.util
import ipaddress
import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request


def organ(name):
    spec = importlib.util.spec_from_file_location('creation_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_git_process = organ('git_process')
R = organ('control_repository')
GI = R.GI
Refused = R.Refused
STEPS = ('directory', 'init', 'scaffold', 'author', 'commit', 'remote', 'push')
STEP_SECONDS = 60
GITHUB_API = 'https://api.github.com'
API_VERSION = '2022-11-28'
HTTP_SECONDS = 30
BRANCH = 'main'


def git(path, *args, check=True, **kwargs):
    done = _git_process.run(['git', '-C', str(path), '-c', 'core.hooksPath=' + os.devnull, *args], capture_output=True,
                  text=True, timeout=STEP_SECONDS, **kwargs)
    if check and done.returncode:
        raise Refused('invalid_input:git', '%s: %s' % (args[0], done.stderr.strip()[:200]))
    return done


# ---------------------------------------------------------------------------------------------
# The local steps
# ---------------------------------------------------------------------------------------------

def within(path, root):
    path, root = os.path.realpath(path), os.path.realpath(root)
    return path != root and path.startswith(root.rstrip(os.sep) + os.sep)


def directory(proposal, identity):
    """Create the directory, or keep it when it exists empty; refuse anything else by name."""
    path = proposal['directory']
    if not within(path, identity['projects_root']):
        raise Refused('invalid_input:directory:outside_projects_root', path)
    if os.path.islink(path):
        raise Refused('directory_not_empty:link', path)
    try:
        entries = os.listdir(path)
    except FileNotFoundError:
        entries = None
    except NotADirectoryError:
        raise Refused('directory_not_empty:not_a_directory', path) from None
    if entries:
        raise Refused('directory_not_empty', path)
    if entries is None:
        if not os.path.isdir(identity['projects_root']):
            raise Refused('invalid_input:directory:no_projects_root', identity['projects_root'])
        try:
            os.makedirs(path, mode=0o755)
        except OSError as error:
            raise Refused('invalid_input:directory:%s' % type(error).__name__, path) from None
    return {'path': os.path.realpath(path)}


def init(proposal, identity):
    done = _git_process.run(['git', '-c', 'core.hooksPath=' + os.devnull, 'init', '-q', '-b', BRANCH, proposal['directory']],
                  capture_output=True, text=True, timeout=STEP_SECONDS)
    if done.returncode:
        raise Refused('invalid_input:init', done.stderr.strip()[:200])
    return {'branch': BRANCH}


def scaffold(proposal, identity, templates=None):
    try:
        report = organ('init_scaffold').scaffold(proposal['directory'], templates=templates)
    except Exception as error:  # noqa: BLE001 - a scaffold that cannot be laid is a named refusal
        raise Refused('invalid_input:scaffold', type(error).__name__) from None
    return {'created': len(report.get('created') or [])}


def author(proposal, identity):
    name, email = GI.author(identity)
    git(proposal['directory'], 'config', 'user.name', name)
    git(proposal['directory'], 'config', 'user.email', email)
    return {'author': '%s <%s>' % (name, email)}


def commit(proposal, identity):
    path = proposal['directory']
    git(path, 'add', '-A')
    git(path, '-c', 'commit.gpgsign=false', 'commit', '-q', '--no-verify', '-m',
        'Start %s with the Veldo scaffold' % proposal['project'], identity=GI.author(identity))
    head = git(path, 'rev-parse', 'HEAD').stdout.strip()
    return {'base_commit': head}


# ---------------------------------------------------------------------------------------------
# The remote, through GitHub's REST interface
# ---------------------------------------------------------------------------------------------

def api_origin(value):
    """The REST origin the configuration names: GitHub's own, or http on a loopback address for a
    disposable stand-in (a suite's); anything else refuses by name."""
    value = value or GITHUB_API
    parts = urllib.parse.urlsplit(value)
    try:
        loopback = parts.hostname is not None and ipaddress.ip_address(parts.hostname).is_loopback
    except ValueError:
        loopback = parts.hostname == 'localhost'
    if (parts.scheme == 'https' and parts.hostname == 'api.github.com' or parts.scheme == 'http' and loopback) \
            and not parts.username and not parts.query and parts.path in ('', '/'):
        return value.rstrip('/')
    raise Refused('invalid_input:github_api', 'GitHub\'s REST origin or a loopback stand-in')


def token(identity):
    """The identity's API token from the keystore, as a secretref handle's value; refused by name."""
    try:
        return organ('secretref').resolve_for_runtime(
            identity['api_token'], organ('control_credential_keystore').SecretService()).reveal()
    except Exception as error:  # noqa: BLE001 - the reason is the keystore's code, never the value
        code = getattr(error, 'code', None)
        raise Refused('token_unavailable:%s' % (code.split(':', 1)[-1] if isinstance(code, str) else 'unresolved'))


class GitHub:
    """GitHub's REST interface with one identity's token. Never logs or returns the token."""

    def __init__(self, origin, value, timeout=HTTP_SECONDS):
        self.origin, self._token, self.timeout = api_origin(origin), value, timeout
        self.calls = []

    def call(self, method, path, body=None):
        request = urllib.request.Request(self.origin + path, method=method,
                                         data=None if body is None else json.dumps(body).encode(),
                                         headers={'Authorization': 'Bearer ' + self._token,
                                                  'Accept': 'application/vnd.github+json',
                                                  'X-GitHub-Api-Version': API_VERSION,
                                                  'User-Agent': 'veldo-repository-provisioner',
                                                  'Content-Type': 'application/json'})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect)
        try:
            with opener.open(request, timeout=self.timeout) as answer:
                status, raw = answer.status, answer.read()
        except urllib.error.HTTPError as error:
            status, raw = error.code, error.read()
        except (urllib.error.URLError, OSError, ValueError):
            self.calls.append({'method': method, 'path': path, 'status': None})
            raise Refused('creation_refused:unreachable', path) from None
        self.calls.append({'method': method, 'path': path, 'status': status})
        try:
            value = json.loads(raw) if raw else None
        except ValueError:
            value = None
        return status, value


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def remote(proposal, identity, *, origin=None, observe=None, repository=None, request=None, client=None):
    """Create the remote under the identity's owner (module docstring). Returns {url, owner, visibility,
    id} as GitHub answered them."""
    wanted = proposal['remote']
    transport = _git_process.identity_transport()
    try:
        checked = transport.check_remote(identity, wanted['url'], operation='creation', repository=repository,
                                         request=request, observe=observe)
    except transport.Refused as error:
        raise Refused(error.code) from None
    owner, name = checked['owner'], wanted['name']
    if checked['path'].rsplit('/', 1)[-1].removesuffix('.git') != name:
        raise Refused('invalid_input:remote_name', wanted['url'])
    github = client or GitHub(origin, token(identity))
    status, user = github.call('GET', '/user')
    if status != 200 or not isinstance(user, dict) or not isinstance(user.get('login'), str):
        raise Refused('creation_refused:user:http_%s' % status)
    status, _found = github.call('GET', '/repos/%s/%s' % (urllib.parse.quote(owner), urllib.parse.quote(name)))
    if status == 200:
        raise Refused('remote_exists', '%s/%s' % (owner, name))
    if status != 404:
        raise Refused('creation_refused:lookup:http_%s' % status)
    path = ('/user/repos' if user['login'].casefold() == owner.casefold()
            else '/orgs/%s/repos' % urllib.parse.quote(owner))
    private = wanted['visibility'] == 'private'
    status, made = github.call('POST', path, {'name': name, 'private': private, 'auto_init': False,
                                              'has_wiki': False})
    if status == 422:
        raise Refused('remote_exists', '%s/%s' % (owner, name))
    if status != 201 or not isinstance(made, dict):
        raise Refused('creation_refused:http_%s' % status)
    made_owner = (made.get('owner') or {}).get('login')
    if not isinstance(made_owner, str) or made_owner.casefold() != owner.casefold():
        raise Refused('binding_mismatch:remote_owner', 'GitHub created it under another owner')
    if made.get('name') != name or made.get('private') is not private:
        raise Refused('creation_refused:answer', 'GitHub created another repository than the one asked for')
    return {'url': wanted['url'], 'owner': made_owner, 'visibility': wanted['visibility'], 'id': made.get('id')}


def push(proposal, identity, base_commit):
    """Push the initial commit to the default branch of the checked remote URL through the identity profile,
    leased on the branch being absent there; read back. Returns the remote tip."""
    path, url = proposal['directory'], proposal['remote']['url']
    transport = _git_process.identity_transport()
    ref = 'refs/heads/' + BRANCH

    def run(*args):
        try:
            return _git_process.run(['git', '-C', path, *args], capture_output=True, text=True, timeout=STEP_SECONDS,
                          profile='identity', push_identity=identity, remote_url=url)
        except transport.Refused as error:
            raise Refused(error.code) from None
    pushed = run('push', '--porcelain', '--force-with-lease=%s:' % ref, url, '%s:%s' % (base_commit, ref))
    listed = run('ls-remote', url, ref)
    tip = listed.stdout.split('\t', 1)[0].strip() if not listed.returncode and listed.stdout.strip() else None
    if pushed.returncode or tip != base_commit:
        raise Refused('push_refused:remote', (pushed.stderr or '').strip()[:200])
    return {'tip': tip}

