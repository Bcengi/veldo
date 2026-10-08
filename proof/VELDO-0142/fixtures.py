"""Explicit identity records for older consumer suites, with no production fallback.

These fixtures choose their authors. Production never reads Git to choose an identity.
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
