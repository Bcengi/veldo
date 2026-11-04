"""A conversation turned into a new or existing project's work by the owner's typed command (VELDO-0180).

THE COMMAND (AC1). Only the conversation's owner turns it into project work, and only by his own typed command:
`conversations.make_project` in the API (the conversation, its current version, a project name, optionally the
objective in his words and a Git identity), or on Telegram, in reply to one of the conversation's messages,
`/project <name> [objective]` or his own words meaning it, which the factory PM reads from his message alone
(VELDO-0175 AC4's reading, command `project`, its name a whole word of his message). The project is named from that
command, never from anything a turn produced: the factory builds VELDO-0152 AC3's route document from the command
alone (`document`), marked with its conversation as its source, and intake's routing command carries it out. A name
that is one of the store's projects, by name or id, is the existing-project route (intake's scope and factory checks
refuse one outside his scope, unauthorized:project, or the factory, invalid_input:factory_project); any other name is
a new project of that name, which VELDO-0143's proposal settles from the command (nothing asked when it names the
identity, else his one answer). The objective is the text after the name, else the conversation's first message.
From anyone but the owner the command is refused missing_authority:conversation_owner, with no name
invalid_input:conversation_command:project_name, and each makes nothing. Nothing in a turn's reply, tool results or
protocol messages is ever read as a route, a name or a claim that a project was made: the follow-up pass reads only
the conversion proposals intake recorded from his commands.

THE INPUTS (AC2). At conversion the factory binds to the objective the conversation id, VELDO-0176 AC3's rendering of
every turn so far from their redacted execution records (never shortened: runs receive it as an input artifact file,
not as their prompt) and a snapshot of the conversation's workspace: its regular files, and for each attached
project clone its local commits as a Git bundle against the trunk commit the clone was taken at. Both are stored by
digest under the project's state (<state root>/projects/<name digest>/conversation-inputs). The project's PM runs
and the first build run of a unit under the objective receive both as input artifacts (`run_inputs`, the Runner's
preparation), checked against the bound digests by the receiver before launch (`launch_problem`, else
binding_mismatch:conversation_snapshot). The builder starts from trunk as always; the bundle is an input it may
apply, and the result reaches trunk only through the ordinary pipeline.

Observations name the conversation, the command and its route, the project route, the project, the proposal and the
objective, and the digests of the rendering and the snapshot; never their content.
"""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tarfile
import tempfile


def _organ(name):
    spec = importlib.util.spec_from_file_location('conversation_project_' + name,
                                                  Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


COMMAND = '/project'
KIND = 'project'
CONVERTING = 'CONVERTING'
DECIDED_BY = 'conversation_command'
SOURCE_OUTCOME = 'conversion'
OWNER_REFUSAL = 'missing_authority:conversation_owner'
NAME_REFUSAL = 'invalid_input:conversation_command:project_name'
SNAPSHOT_MISMATCH = 'binding_mismatch:conversation_snapshot'
ROUTES = ('new_project', 'existing_project')
HISTORY, SNAPSHOT = 'conversation_history', 'conversation_snapshot'
INPUTS = 'conversation-inputs'
# The objective states whose project runs still receive the conversation's inputs.
LIVE_OBJECTIVES = ('PROPOSED', 'ACCEPTED', 'ACTIVE')
REASON = 'The owner\'s typed command made this conversation a project\'s work.'


class Refused(Exception):
    def __init__(self, code, detail=''):
        super().__init__(code)
        self.code, self.detail = code, detail


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def parse(text):
    """(name, objective) of a typed `/project <name> [objective]`: the name exactly as typed (its first word after
    the command), the objective the rest, None when absent; None for any other text."""
    if not isinstance(text, str):
        return None
    words = text.strip().split(None, 1)
    if not words or words[0] != COMMAND:
        return None
    rest = words[1].strip() if len(words) > 1 else ''
    parts = rest.split(None, 1)
    name = parts[0] if parts else None
    objective = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
    return name, objective


def words_after(text, name):
    """His words after `name`, the name a whole word of `text` (VELDO-0143's word rule): (found, rest or None)."""
    import re
    NP = _organ('control_project_proposal')
    if not NP.names(text, name):
        return False, None
    match = re.search(NP._LEFT_EDGE + re.escape(name) + NP._RIGHT_EDGE, text, re.IGNORECASE)
    rest = text[match.end():].strip().lstrip(':,.-').strip()
    return True, rest or None


def project_names(conn):
    """{name or id: name} of every project the store records (its name and its id `project:<name>`)."""
    found = {}
    for (raw,) in conn.execute("SELECT data FROM entities WHERE kind='project'"):
        name = json.loads(raw).get('name')
        if _text(name):
            found[name] = name
            found['project:' + name] = name
    return found


def first_message(conn, identity):
    """The conversation's first message, his words as turn 1's intake source keeps them, or None."""
    CV = _organ('control_conversation')
    row = conn.execute('SELECT data FROM entities WHERE id=?', (CV.turn_id(identity, 1),)).fetchone()
    turn = json.loads(row[0]) if row else {}
    source = conn.execute('SELECT kind, data FROM entities WHERE id=?', (str(turn.get('intake_command')),)).fetchone()
    return json.loads(source[1]).get('text') if source and source[0] == 'intake_source' else None


def route_of(conn, name):
    """(route, project name): the existing-project route for a project the store records by name or id, else a new
    project of that name."""
    known = project_names(conn)
    if name in known:
        return 'existing_project', known[name]
    return 'new_project', name


def document(proposal_id, conversion):
    """VELDO-0152 AC3's route document the factory builds from the owner's command alone, marked with its
    conversation as its source."""
    doc = {'schema': 'veldo.intake_route/v1', 'proposal_id': proposal_id, 'route': conversion['route'],
           'reason': REASON, 'source': {'conversation': conversion['conversation'], 'command': conversion['command']}}
    if conversion['route'] == 'existing_project':
        doc['project'] = conversion['project']
    return doc


def new_project_document(proposal_id, conversion):
    """VELDO-0143's new-project document, built from the command alone (never by a PM run): its name, its identity
    when the command names one, no visibility, and the objective."""
    return {'schema': 'veldo.new_project_document/v1', 'proposal_id': proposal_id, 'project': conversion['project'],
            'identity': conversion.get('identity'), 'visibility': None, 'objective': conversion['objective'],
            'reason': REASON}


def conversion_of(data):
    """The conversion block of an intake proposal intake recorded from the owner's command, or None."""
    conversion = (data or {}).get('conversion') if isinstance(data, dict) else None
    decision = (data or {}).get('decision') if isinstance(data, dict) else None
    if (not isinstance(conversion, dict) or not isinstance(decision, dict)
            or decision.get('decided_by') != DECIDED_BY):
        return None
    return conversion


def conversion_source(conn, proposal_id):
    """(key, data) of the intake source of a conversion proposal (the owner's command) or of a proposal a conversion
    route moved into a project (it `resolves` the conversion proposal), or None."""
    row = conn.execute('SELECT kind, data FROM entities WHERE id=?', (str(proposal_id),)).fetchone()
    data = json.loads(row[1]) if row and row[0] == 'intake_proposal' else {}
    origin = data
    if conversion_of(data) is not None and data.get('resolves'):
        found = conn.execute('SELECT kind, data FROM entities WHERE id=?', (str(data['resolves']),)).fetchone()
        origin = json.loads(found[1]) if found and found[0] == 'intake_proposal' else {}
    conversion = conversion_of(origin)
    if conversion is None:
        return None
    key = conversion.get('command')
    found = conn.execute('SELECT kind, data FROM entities WHERE id=?', (str(key),)).fetchone()
    source = json.loads(found[1]) if found and found[0] == 'intake_source' else {}
    if source.get('proposal_id') != origin.get('proposal_id') or source.get('principal') != origin.get('principal'):
        return None
    return key, source


# -- the inputs (AC2) ---------------------------------------------------------------------------------------------

def _digest(data):
    return 'sha256:' + hashlib.sha256(data).hexdigest()


def file_digest(path):
    try:
        with open(path, 'rb') as handle:
            return _digest(handle.read())
    except OSError:
        return None


def inputs_directory(state_root, project):
    """Where a project's conversation inputs are stored: under the project's state, by its name's digest."""
    return os.path.join(os.path.abspath(str(state_root)), 'projects', hashlib.sha256(project.encode()).hexdigest(),
                        INPUTS)


def _store(directory, suffix, data):
    os.makedirs(directory, mode=0o700, exist_ok=True)
    digest = _digest(data)
    path = os.path.join(directory, digest.split(':', 1)[1] + suffix)
    if file_digest(path) != digest:
        handle, temporary = tempfile.mkstemp(dir=directory)
        with os.fdopen(handle, 'wb') as out:
            out.write(data)
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    return digest, path


def rendering(conn, records, identity):
    """VELDO-0176 AC3's rendering of every turn so far, from the redacted execution records, never shortened."""
    CV, ER = _organ('control_conversation'), _organ('control_execution_record')
    turns = CV.history(conn, records, identity, sys.maxsize, ER.read)
    return CV.render(turns, sys.maxsize)


def _tar_add(tar, name, data, mode=0o600):
    info = tarfile.TarInfo(name)
    info.size, info.mode, info.mtime, info.uid, info.gid = len(data), mode, 0, 0, 0
    tar.addfile(info, io.BytesIO(data))


def snapshot(record):
    """The conversation workspace's snapshot: its regular files (the attached clones aside), and for each attached
    clone its local commits as a Git bundle against the trunk commit it was taken at. (bytes, manifest)."""
    CV, GP = _organ('control_conversation'), _organ('git_process')
    workspace = CV.workspace_of(record)
    files, clones = [], []
    entries = []
    if workspace and os.path.isdir(workspace):
        for top, directories, names in os.walk(workspace):
            relative_top = os.path.relpath(top, workspace)
            if relative_top == '.':
                directories[:] = [d for d in directories if d != CV.PROJECTS]
            directories.sort()
            for name in sorted(names):
                path = os.path.join(top, name)
                if os.path.islink(path) or not os.path.isfile(path):
                    continue
                relative = os.path.normpath(os.path.join(relative_top, name))
                with open(path, 'rb') as handle:
                    data = handle.read()
                files.append({'path': relative, 'digest': _digest(data), 'size': len(data)})
                entries.append(('files/' + relative, data, 0o755 if os.access(path, os.X_OK) else 0o644))
    for number, attached in enumerate(record.get('attachments') or [], 1):
        clone, commit = attached.get('clone'), attached.get('commit')
        entry = {'project': attached.get('project'), 'clone': os.path.relpath(clone, workspace) if clone and workspace
                 else None, 'commit': commit, 'commits': 0, 'bundle': None}
        if clone and os.path.isdir(clone):
            count = GP.run(['git', '-C', clone, 'rev-list', '--count', '--all', '^' + commit], capture_output=True,
                           text=True)
            entry['commits'] = int(count.stdout.strip() or 0) if count.returncode == 0 else 0
            if entry['commits']:
                with tempfile.TemporaryDirectory() as scratch:
                    target = os.path.join(scratch, 'clone.bundle')
                    made = GP.run(['git', '-C', clone, 'bundle', 'create', target, '--all', '^' + commit],
                                  capture_output=True)
                    if made.returncode == 0:
                        data = Path(target).read_bytes()
                        name = 'bundles/%d-%s.bundle' % (number, attached.get('project'))
                        entry['bundle'] = {'path': name, 'digest': _digest(data)}
                        entries.append((name, data, 0o644))
        clones.append(entry)
    manifest = {'schema': 'veldo.conversation_snapshot/v1', 'conversation': record.get('id'), 'files': files,
                'clones': clones}
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w', format=tarfile.PAX_FORMAT) as tar:
        _tar_add(tar, 'snapshot.json', json.dumps(manifest, sort_keys=True, indent=1).encode())
        for name, data, mode in entries:
            _tar_add(tar, name, data, mode)
    return buffer.getvalue(), manifest


def bind(conn, records, state_root, record, project):
    """The conversation's inputs, stored by digest under the project's state: {conversation, rendering, snapshot}."""
    rendered = rendering(conn, records, record['id'])
    directory = inputs_directory(state_root, project)
    history_digest, history_path = _store(directory, '.history.txt', rendered['text'].encode())
    data, manifest = snapshot(record)
    snapshot_digest, snapshot_path = _store(directory, '.snapshot.tar', data)
    return {'conversation': record['id'], 'version': record.get('version'),
            'rendering': {'digest': history_digest, 'path': history_path, 'turns': rendered['turns'],
                          'characters': rendered['characters'], 'left_out': rendered['left_out']},
            'snapshot': {'digest': snapshot_digest, 'path': snapshot_path, 'files': len(manifest['files']),
                         'clones': [{k: c[k] for k in ('project', 'commit', 'commits')}
                                    for c in manifest['clones']]}}


def artifacts(objective_id, binding):
    """The two input artifacts a run receives for one objective's bound conversation inputs."""
    return [{'name': HISTORY, 'objective': objective_id, 'conversation': binding['conversation'],
             'path': binding['rendering']['path'], 'digest': binding['rendering']['digest']},
            {'name': SNAPSHOT, 'objective': objective_id, 'conversation': binding['conversation'],
             'path': binding['snapshot']['path'], 'digest': binding['snapshot']['digest']}]


def _objectives(conn):
    for eid, raw in conn.execute("SELECT id, data FROM entities WHERE kind='objective' ORDER BY id"):
        yield eid, json.loads(raw)


def run_inputs(conn, station, unit, project, attempt):
    """The input artifacts a project run receives (AC2): a PM (coordination) run of the project receives those of
    each live objective that binds a conversation's inputs; the first build run of a unit whose backlog item is under
    such an objective receives that objective's. [] for every other run."""
    if station == 'coordination':
        return [a for oid, data in _objectives(conn) if data.get('project') == project
                and data.get('state') in LIVE_OBJECTIVES and isinstance(data.get('conversation'), dict)
                for a in artifacts(oid, data['conversation'])]
    if station != 'build' or attempt != 1:
        return []
    row = conn.execute('SELECT kind, data FROM entities WHERE id=?', (str(unit),)).fetchone()
    held = json.loads(row[1]) if row and row[0] == 'execution_unit' else {}
    item = conn.execute('SELECT kind, data FROM entities WHERE id=?', (str(held.get('backlog_item_uuid')),)).fetchone()
    oid = json.loads(item[1]).get('objective_uuid') if item and item[0] == 'backlog_item' else None
    objective = conn.execute('SELECT kind, data FROM entities WHERE id=?', (str(oid),)).fetchone()
    data = json.loads(objective[1]) if objective and objective[0] == 'objective' else {}
    if data.get('project') != project or not isinstance(data.get('conversation'), dict):
        return []
    return artifacts(oid, data['conversation'])


def launch_problem(conn, contract):
    """Before launch: every input artifact the contract carries is the one its objective binds now, and its file has
    exactly that digest; else binding_mismatch:conversation_snapshot. None when it may launch."""
    payload = ((contract.get('input') or {}).get('payload')) or {}
    given = payload.get('input_artifacts') if isinstance(payload, dict) else None
    if not given:
        return None
    if not isinstance(given, list):
        return SNAPSHOT_MISMATCH
    for artifact in given:
        if not isinstance(artifact, dict):
            return SNAPSHOT_MISMATCH
        row = conn.execute('SELECT kind, data FROM entities WHERE id=?', (str(artifact.get('objective')),)).fetchone()
        data = json.loads(row[1]) if row and row[0] == 'objective' else {}
        binding = data.get('conversation') if isinstance(data.get('conversation'), dict) else {}
        bound = {HISTORY: binding.get('rendering'), SNAPSHOT: binding.get('snapshot')}.get(artifact.get('name')) or {}
        if (binding.get('conversation') != artifact.get('conversation') or bound.get('digest') != artifact.get('digest')
                or bound.get('path') != artifact.get('path')
                or file_digest(artifact.get('path')) != bound.get('digest')):
            return SNAPSHOT_MISMATCH
    return None


# -- the follow-up the factory's pass makes of a routed conversion -----------------------------------------------

def pending(conn):
    """What the factory still has to do for the owner's conversions, oldest first: a new-project conversion with no
    VELDO-0143 decision yet, and a conversion moved into an existing project whose objective is not proposed or not
    accepted yet."""
    NP, OB = _organ('control_project_proposal'), _organ('control_objective')
    out = []
    for eid, raw in conn.execute("SELECT id, data FROM entities WHERE kind='intake_proposal' ORDER BY id"):
        data = json.loads(raw)
        conversion = conversion_of(data)
        if conversion is None:
            continue
        if (data.get('project') == NP.FACTORY_PROJECT and data.get('state') == NP.NEW_PROJECT_STATE
                and NP.read(conn, NP.decision_id(eid)) is None):
            out.append({'kind': 'new_project', 'proposal_id': eid, 'conversion': conversion})
        elif data.get('proposal') == 'objective' and data.get('project') != NP.FACTORY_PROJECT \
                and data.get('resolves') and conversion.get('route') == 'existing_project':
            current = OB.read(conn, OB.objective_id(eid))
            if current is None or current.get('state') == 'PROPOSED':
                out.append({'kind': 'objective', 'proposal_id': eid, 'conversion': conversion,
                            'project': data['project']})
    return out


def unrouted(conn):
    """The conversion proposals intake recorded from his command whose route was not carried out yet (CONVERTING)."""
    return [eid for eid, raw in conn.execute("SELECT id, data FROM entities WHERE kind='intake_proposal' ORDER BY id")
            if (data := json.loads(raw)).get('state') == CONVERTING and conversion_of(data) is not None]


def follow_up(conn, *, new_projects=None, objectives=None, pm=None, pm_sign=None, ids=None, observe=None, intake=None):
    """Carry each pending conversion on from what intake recorded of his command, and nothing else: a recorded
    conversion whose route was not carried out (its routing command refused for a reason that may pass) routed again
    by intake; a new project's VELDO-0143 proposal from the command's own document; and an existing project's
    objective proposed by its PM and accepted by his command (VELDO-0150's own-message acceptance). Returns what was
    done."""
    OB = _organ('control_objective')
    done = []
    if intake is not None:
        for pid in unrouted(conn):
            result = intake._converted(pid, None)
            done.append({'kind': 'conversation_project', 'operation': 'follow_up', 'step': 'route', 'proposal_id': pid,
                         'outcome': result.get('outcome'), 'refusal': None, 'reason': result.get('reason')})
    for item in pending(conn):
        conversion, pid = item['conversion'], item['proposal_id']
        event = {'kind': 'conversation_project', 'operation': 'follow_up', 'step': item['kind'], 'proposal_id': pid,
                 'conversation': conversion.get('conversation'), 'command': conversion.get('command'),
                 'route': conversion.get('route'), 'project': conversion.get('project'),
                 'rendering_digest': (conversion.get('inputs') or {}).get('rendering', {}).get('digest'),
                 'snapshot_digest': (conversion.get('inputs') or {}).get('snapshot', {}).get('digest')}
        if item['kind'] == 'new_project':
            if new_projects is None:
                continue
            result = new_projects.propose(pid, new_project_document(pid, conversion), dispatch=conversion['command'])
            event.update(outcome=result.get('outcome') if result.get('ok') else 'refused',
                         refusal=None if result.get('ok') else result.get('reason'),
                         decision=result.get('decision'), asked=result.get('asked'))
        else:
            manager = pm(item['project']) if callable(pm) else pm
            coordinates = ids(item['project']) if callable(ids) else ids
            if objectives is None or manager is None or pm_sign is None or coordinates is None:
                continue
            oid = OB.objective_id(pid)

            def signed(**body):
                command = dict(coordinates, principal=manager, **body)
                return {'command': command, 'signature': pm_sign(objectives.store.canonical_bytes(command))}
            current = OB.read(conn, oid)
            result = {'ok': True}
            if current is None:
                result = objectives.apply(signed(operation='propose', command_id='objective-propose:' + oid,
                                                 nonce='objective-propose:' + oid, proposal=pid,
                                                 outcome=conversion['objective'], scope=[item['project']],
                                                 authority={'acceptor': conversion['owner'],
                                                            'assessor': conversion['owner']},
                                                 evidence_requirements=[{'id': 'gate', 'kind': 'gate_observation'}]))
                current = OB.read(conn, oid)
            if result.get('ok') and current is not None and current.get('state') == 'PROPOSED':
                written = OB.first_writer(conn, conversion['command'])
                result = objectives.apply(signed(operation='accept_message', command_id='objective-accept:' + oid,
                                                 nonce='objective-accept:' + oid, objective=oid,
                                                 objective_version=current['version'],
                                                 intake_command=written[1] if written else None,
                                                 revision=current['revision'], bound_digest=current['bound_digest']))
            event.update(outcome='accepted' if result.get('ok') else 'refused',
                         refusal=None if result.get('ok') else result.get('reason'), objective=oid)
        done.append(event)
        if observe is not None:
            observe(event)
    return done


def metrics(observations):
    """Conversions by project route and by command route, those that asked the owner one question, and conversion
    commands refused by reason."""
    routes, commands, asked, refused = {}, {}, 0, {}
    for e in observations:
        if e.get('kind') != 'conversation_project':
            continue
        if e.get('operation') == 'convert' and e.get('outcome') == 'converted':
            routes[e.get('route')] = routes.get(e.get('route'), 0) + 1
            commands[e.get('command_route')] = commands.get(e.get('command_route'), 0) + 1
        elif e.get('operation') == 'convert' and e.get('outcome') == 'refused':
            refused[e.get('reason')] = refused.get(e.get('reason'), 0) + 1
        elif e.get('operation') == 'follow_up' and e.get('step') == 'new_project' and e.get('outcome') == 'presented':
            asked += 1
    return {'routes': routes, 'command_routes': commands, 'asked_one_question': asked, 'refused': refused}
