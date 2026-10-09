"""The one fixture helper that configures a repository's Git identity before a suite binds it.

VELDO-0142: a repository record is bound only with its configured, immutable Git identity
(control_store.bind_repositories refuses missing_authority:repository_identity before writing).
Every suite, harness and helper that binds a repository, directly or through a service that does
(control_readset.attach_revisions, control_proof.ProofService, control_architecture's authority,
control_alias, dispatch's FloorAuthority), configures the identity on the same store first:

    GI = __import__('runpy').run_path(str(ROOT / 'scripts/suites/support/git_identity.py'))
    GI['bind_paths'](mods, conn, domain, {repository: str(path)})

`mods` is the directory of the installed engine copy the suite runs, so the identity is written
by that copy's control_git_identity.py (a registered mutation of it reaches the fixture too).
These fixtures choose their authors explicitly; production never reads Git to choose one. The
helper lives with the suites and is never installed.
"""
import importlib.util
from pathlib import Path
import sqlite3


def options(root, author=('Fixture Identity', 'fixture@example.invalid')):
    return dict(git_identities=[dict(id='fixture', label='Fixture', author_name=author[0], author_email=author[1],
                                    remote_host='github.com', remote_owner='fixture',
                                    api_token='keychain:fixture/api',
                                    push_credential=dict(kind='token', reference='keychain:fixture/api'),
                                    projects_root=str(Path(root).resolve()), default_visibility='private')],
                workspace_identity='fixture')


def bind(mods, conn, domain, repository, path, author=('Fixture Identity', 'fixture@example.invalid')):
    spec = importlib.util.spec_from_file_location('fixture_git_identity', Path(mods) / 'control_git_identity.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    conn = conn if conn is not None else sqlite3.connect(':memory:', isolation_level=None)
    module.configure(conn, domain, options(Path(mods).parent, author)['git_identities'],
                     {repository: dict(path=str(path), identity='fixture')})
    return conn


def bind_all(mods, conn):
    for domain, repository, path in conn.execute('SELECT domain_uuid, repository_uuid, path FROM repository_bindings').fetchall():
        bind(mods, conn, domain, repository, path)


def bind_paths(mods, conn, domain, repositories, author=('Fixture Identity', 'fixture@example.invalid')):
    for repository, path in repositories.items():
        bind(mods, conn, domain, repository, path, author)
