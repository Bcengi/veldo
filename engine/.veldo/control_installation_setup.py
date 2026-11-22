"""Export already-live factory values as one initial/import installation commit."""
import importlib.util
import json
import os
from pathlib import Path


def organ(name):
    spec = importlib.util.spec_from_file_location('installation_setup_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


C = organ('control_installation_config')
WF = organ('control_workflow')
I = organ('installation')


def export(conn, settings, files=None):
    """Declared kinds from live records. Never export runs, pauses, conversations or occurrences."""
    files = dict(files or {})
    settings = json.loads(json.dumps(settings))
    for eid, kind, raw in conn.execute('SELECT id, kind, data FROM entities ORDER BY id'):
        data = json.loads(raw)
        if kind == WF.HEAD_KIND and not data.get('deleted'):
            row = WF._entity_row(conn, data['revision'])
            definition = row['data'].get('definition')
            if definition is None:
                content = WF._entity_row(conn, 'workflow-definition:' + row['data']['definition_digest'])
                definition = json.loads(content['data']['canonical'])
            path = 'workflows/%s.json' % data['workflow']
            encoded = WF.canonical(definition)
            if path in files and files[path] != encoded:
                raise C.Refused('installation_invalid:%s:$:import_collision' % path)
            files[path] = encoded
            files['workflows/%s.layout.json' % data['workflow']] = WF.canonical(row['data'].get('layout', {}))
        elif kind == 'project':
            name = data.get('name', eid.removeprefix('project:'))
            entry = {key: data[key] for key in ('account', 'landing_destination', 'remote', 'trunk',
                     'render_command', 'deploy_targets', 'spend_checklist', 'renumber_hook') if key in data}
            entry['repository'] = data.get('execution_repository', '')
            if not entry['repository']:
                entry.pop('repository')
            entry['workflows'] = {key: {field: binding[field] for field in ('workflow', 'version')}
                                  for key, binding in data.get('workflows', {}).items()}
            files['projects/%s.yaml' % name] = WF.canonical(entry)
        elif kind == 'agent_configuration_head':
            revision = WF._entity_row(conn, eid[:-5] + ':' + str(data['revision']))
            data = revision['data']
            definition = {key: data[key] for key in organ('control_agent_config').FIELDS if key in data}
            if definition:
                files['roles/%s.yaml' % definition['role']] = WF.canonical({'id': definition['role'],
                    'configuration': definition, 'capabilities': [tool['name'] for tool in definition['native_tools']]})
        elif kind == 'team' and data.get('team'):
            name = data['project']
            files['teams/%s.yaml' % name] = WF.canonical({'id': name, 'configuration': data['team']})
        elif kind == 'memory_store' and eid == 'memory:head':
            files['memory/manifest.yaml'] = WF.canonical({'manifest': organ('control_memory').manifest_of(data['definition'])})
        elif kind == 'account':
            settings.setdefault('accounts', {})[data['id']] = {
                key: data[key] for key in ('label', 'provider', 'profiles', 'concurrency') if key in data}
    files[I.SETTINGS_FILE] = WF.canonical(settings)
    return files


def create(store, conn, folder, *, settings, identity, domain, repository, signer, sign,
           secret_exists, observe=None):
    repo = I.Repository.create(folder, settings.get('git', {}).get('branch', 'main'))
    loader = C.Loader(store, conn, repo, domain=domain, workflow_repository=repository, signer=signer,
                      sign=sign, secret_exists=secret_exists, observe=observe, notify=observe)
    if loader.accepted_commit is not None:
        return {'outcome': 'already_done', 'commit': loader.accepted_commit, 'folder': repo.folder}
    try:
        parent = repo.head()
        files = repo.snapshot(parent)['files']
    except I.InstallationError:
        parent, files = None, repo.import_files()
    template = I._yamlish().read(Path(__file__).with_name('installation_template') / I.SETTINGS_FILE)
    settings = dict(template, **settings)
    files = export(conn, settings, files)
    _, problems = loader.validate(files)
    if problems:
        raise C.Refused(problems[0], codes=problems)
    commit = repo.commit(files, parent, identity, 'Import live installation configuration')
    repo.publish(commit, parent)
    result = loader.reconcile(bootstrap=True, made=True)
    if result['outcome'] != 'accepted':
        raise C.Refused(result['problems'][0], codes=result['problems'])
    if parent is None:
        repo.materialize_initial(files)
    return dict(result, folder=repo.folder)


def factory(store, conn, plan, ids, installed, identities, workspace_identity, *, remote=None, port=None,
            https_port=None, journal, observe=None, keystore=None):
    """Setup alone imports a token into the keystore. The loader only sees its reference."""
    if identities is None:
        git_identity = organ('control_git_identity')
        identities = git_identity.records(conn, ids['domain_uuid'])
        workspace_identity = git_identity.repository_record(conn, ids['domain_uuid'], ids['repository_uuid'])['identity']
    given = next(record for record in identities if record['id'] == workspace_identity)
    identity = {'name': given['author_name'], 'email': given['author_email']}
    config = json.loads(Path(installed['config']).read_text())
    folder = config['installation']
    ks = keystore or organ('control_credential_keystore').SecretService()
    token_name = ids['domain_uuid'] + '-bot'
    if not ks.contains(token_name):
        token = organ('control_channel_ingress').read_token(plan['token_file'])
        ks.set(token_name, token)
    approvers = [eid for eid, raw in conn.execute("SELECT id, data FROM entities WHERE kind='verification_key'")
                 if (value := json.loads(raw)).get('principal') == plan['owner']
                 and value.get('revoked_at') is None and value.get('retired_at') is None]
    settings = {'schema': I.SCHEMA, 'owner': {'display_name': identity['name'], 'role_id': 'owner'},
                'git_identities': {plan['owner']: identity}, 'approvers': sorted(approvers),
                'git': {'branch': 'main'}, 'channels': {'main': {'kind': 'telegram_chat', 'chat': str(plan['chat']),
                                                               'token': {'secret': token_name}}},
                'hosts': {'authority': config['host_identity']},
                'ports': {key: value for key, value in [('api', port), ('https', https_port)] if value is not None}}
    if remote is not None:
        settings['git']['remote'] = remote
    # Preserve additional previously declared installation kinds and settings at import.
    record = WF._entity_row(conn, 'installation:' + C.V.digest([ids['domain_uuid'], str(Path(folder).resolve())]))
    if record is not None:
        existing = record['data']['configuration'][I.SETTINGS_FILE]
    else:
        repository = I.Repository.create(folder)
        try:
            parent = repository.head()
        except I.InstallationError:
            parent = None
        files = repository.snapshot(parent)['files'] if parent else repository.import_files()
        existing = C.V.decode(files.get(I.SETTINGS_FILE, b'{}'))
    for field in ('channels', 'hosts', 'ports', 'git_identities'):
        settings[field] = dict(existing.get(field, {}), **settings[field])
    settings['git'] = dict(existing.get('git', {'branch': 'main'}))
    if remote is not None:
        settings['git']['remote'] = remote
    settings = dict(existing, **settings)
    result = create(store, conn, folder, settings=settings, identity=identity, domain=ids['domain_uuid'],
                  repository=ids['repository_uuid'], signer=journal[0], sign=journal[1],
                  secret_exists=ks.contains, observe=observe)
    directory = Path(installed['unit_path'] + '.d')
    directory.mkdir(mode=0o700, exist_ok=True)
    # systemd specifier expansion is disabled for the literal installation path.
    value = json.dumps(I.ENVIRONMENT + '=' + str(Path(folder).resolve()).replace('%', '%%'))
    (directory / 'installation.conf').write_text('[Service]\nEnvironment=' + value + '\n')
    os.chmod(directory / 'installation.conf', 0o600)
    config['installation_repository'] = result['commit']
    config['installation_branch'] = settings['git'].get('branch', 'main')
    Path(installed['config']).write_text(json.dumps(config, sort_keys=True) + '\n')
    return result
