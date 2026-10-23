"""A new project from chat: the factory PM's one proposal and the owner's one answer (VELDO-0143 AC1).

WHAT THIS MODULE IS. The one reader and writer of a new-project decision (entity `new-project:<intake
proposal>` of kind `new_project`), and the one judge of whether such a decision is settled. Intake keeps a
message the factory PM routed as a new project in state NEW_PROJECT (VELDO-0152 AC3); the factory project's
next PM run reads it and returns one DOCUMENT naming only what needs judgment: the project's name, the
identity when the owner said one, the visibility when he said one, and the first objective. Everything else
the proposal binds is derived here, never chosen by the PM: the repository's uuid, the directory under the
identity's projects root, the remote under the identity's owner, whether the directory is already a Git
repository (then the adoption path of VELDO-0161, its scaffold commit laid before he is asked), the default
team's current revision (VELDO-0162 AC4), the default pipeline (the PM cycle's WORKFLOW, VELDO-0132), the
charter, the authority policy and the coordination budget.

ONE ANSWER. The proposal is settled by exactly one of three paths, and nothing is asked after it:

  own_message  the message that started it is the answer and nothing is presented: it is the factory
               owner's own authenticated message (his intake source), the PM named an identity, and the
               message names both the project and that identity, each as a whole word (nothing_asked).
  answer       otherwise the proposal is presented once to the factory owner as a VELDO-0068 request whose
               terms target TARGET (the project and the digest of the proposal) and whose brief is exactly
               brief(proposal); his approval settles it. When the PM named no identity, the proposal
               offers every configured identity in the same request and his approving answer names one of
               them, which resolves it (identity_named): an answer that answers a question offering exactly
               those identities.
  correction   his answer returns the proposal with his words (return_for_elaboration): the factory PM's
               next run reads the proposal and his words and returns the corrected document, which settles
               it with no second presentation. A corrected document that still names no identity fails the
               decision by name.

A reject settles nothing and the decision is `rejected`. An approval that names none of the identities the
proposal offered settles nothing either: the identity was asked and his answer did not say it, so the decision
is `failed` invalid_input:answer:identity and its report tells him why (VELDO-0143 F2).

A CORRECTION IS BOUND TO HIS WORDS (correction_problems). The PM reads his correction; it never chooses for him.
The corrected proposal settles only when each of its terms is the one he was shown or the one his correction
says: the project's name is the presented one or named in his words; the identity is the presented one or the
one configured identity his words name; the visibility is the one shown for that identity or the one visibility
his words name; and the mode is the one shown for that identity and name (an adoption is only ever an adoption
he was shown, its scaffold commit the one shown; a name or identity he was not shown is a creation). A word he
negates is not said (VELDO-0143 R3-2): an identity or visibility counts only where no negator (not, no, never,
nor, without, instead of, rather than, or a word ending n't) stands before it in its clause (the words since the
last , . ; : ! ? ( ) or line break, or the last but, and, so), and an identity or visibility he was shown that
his words negate does not stay. Anything else fails the decision by name, invalid_input:correction:<field>,
before anything is built or laid, and the one judge refuses it again (no_settled_decision:correction:<field>).

A NAME IS ONE PROJECT (VELDO-0143 F3). A project whose name is already a project's, or the name of another
new-project decision still live (presenting, presented, correcting or settled), compared without case as
GitHub compares names, is refused stale_subject:project_exists before he is asked and before anything is
created; the decision is `failed` with that reason and its report tells him. An activation that finds the
name taken meanwhile fails the decision `already_exists` rather than leaving it to be tried again.

NOTHING IS ASKED THAT CANNOT BE CARRIED OUT (VELDO-0143 F6). An installation with no provisioner configuration
(`provisioner`, the running service's provisioner_path) neither presents nor settles a proposal: the decision is
`failed` unavailable_service:provisioner and its report tells him why.

PRESENTED ONCE, EVEN ACROSS A CRASH (VELDO-0143 F4). The decision is written `presenting`, carrying the
proposal, the request's alias and its deadline, before anything is presented; the presentation follows, then
the decision is `presented`. A presentation interrupted by a crash or refused by the store is finished from the
record (resume, at the running service's next new-project pass) with the same proposal and the same commands,
which the store replays and the presenter does not send twice; nothing is built again.

THE SAME SETTLEMENT ACTIVATES (activate, VELDO-0143 AC3). Once the repository the decision names is
`active` (created and adopted, or adopted, and taken on by the running service), the decision is applied in
order, each step once: the project's activation (control_project.activate_decided, which refuses while the
repository is not active), its first team revision, which is the default team revision the proposal named
(first_team, VELDO-0162 AC4, after VELDO-0089's staffing checks), the message moved into the project as its
first objective proposal (control_intake_routes.resolve_new_project), that objective proposed by the
project's PM with the proposal's first objective as its outcome and accepted by the decision
(control_objective accept_decided); the decision is then `activated`, and VELDO-0128's report of it tells the
owner "<name> is ready; the first objective is next". A repository that ended `failed` activates nothing, the
decision is `failed`, and its report tells him why. settled() judges the decision from its evidence
(the intake source, the request, its settlement and effect, the brief), never from the record's state, and
refuses no_settled_decision:<why> by name. The repository provisioner, the adoption signer, the running
service's take-on and the project's activation all call it (repository_decision adapts it to the shape
control_repository.settled returns).

THE RECORD. states: presenting, presented, correcting, settled, rejected, failed, activated. Every write appends one
history entry and never changes an earlier one. Observations name the intake proposal, the decision, the
project, the identity and the request, never the message text, a token or a signature.

Standard library only; every organ is loaded as a sibling by path.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import time
import uuid


def organ(name):
    spec = importlib.util.spec_from_file_location('new_project_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GI = organ('control_git_identity')
AC = organ('authority_contract')

SCHEMA = 'veldo.new_project/v1'
DOCUMENT = 'veldo.new_project_document/v1'
DOCUMENT_FIELDS = ('schema', 'proposal_id', 'project', 'identity', 'visibility', 'objective', 'reason')
KIND = 'new_project'
ID_PREFIX = 'new-project:'
OPERATION = 'new_project_record'
WRITES = ('entities', 'journal', 'commands', 'nonces')
STATES = ('presenting', 'presented', 'correcting', 'settled', 'rejected', 'failed', 'activated')
TRANSITIONS = {None: ('presenting', 'settled', 'failed'), 'presenting': ('presented',),
               'presented': ('settled', 'correcting', 'rejected', 'failed'),
               'correcting': ('settled', 'failed'), 'settled': ('settled', 'failed', 'activated')}
# A new-project decision still live: its name is taken (A NAME IS ONE PROJECT).
LIVE = ('presenting', 'presented', 'correcting', 'settled')
PATHS = ('own_message', 'answer', 'correction')
# The VELDO-0068 request the owner answers when his message did not settle it.
TOUCHPOINT, TARGET = 'decision_disposition', 'new_project'
CHOICES = ['accept', 'return_for_elaboration', 'reject']
REQUEST_KIND, TERMS_KIND, SETTLEMENT_KIND, EFFECT_KIND = 'assignment', 'settlement_terms', 'request_settlement', 'settlement_effect'
SETTLED_STATE = 'SATISFIED'
EFFECTS = {'approve': 'decision_approved', 'return_for_elaboration': 'decision_returned'}
OWNER_ROLE = 'project_owner'
FACTORY_PROJECT = 'factory'
INTAKE_PROPOSAL, INTAKE_SOURCE, NEW_PROJECT_STATE = 'intake_proposal', 'intake_source', 'NEW_PROJECT'
# What every proposal binds, in the order a missing one is named.
PROPOSAL_FIELDS = ('project', 'repository', 'owner', 'identity', 'offered', 'directory', 'mode', 'remote', 'adoption',
                   'objective', 'charter', 'authority_policy', 'team', 'pipeline', 'coordination_budget', 'source')
# What the chosen identity decides: one offered entry each when the PM named none.
IDENTITY_FIELDS = ('identity', 'directory', 'mode', 'remote', 'adoption')
MODES = ('create', 'adopt')
VISIBILITIES = ('private', 'public')
# The defaults every new project starts with; the proposal names them, so his answer binds them.
AUTHORITY_POLICY = {'team_amendment': [OWNER_ROLE]}
COORDINATION_BUDGET = {'capacity': 4, 'invocations': 400, 'wall_seconds': 7 * 86400}
DEFAULT_BRANCH = 'main'
_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$')
_WORD_EDGE = r'[A-Za-z0-9_.-]'


class Refused(Exception):
    def __init__(self, code, detail=''):
        super().__init__('%s: %s' % (code, detail) if detail else code)
        self.code, self.detail = code, detail


def _is_str(value):
    return isinstance(value, str) and value.strip() != ''


def digest(value):
    return 'sha256:' + hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                                 ensure_ascii=True).encode()).hexdigest()


def decision_id(intake_proposal):
    return ID_PREFIX + str(intake_proposal)


def _row(conn, eid):
    if not _is_str(eid):
        return None
    row = conn.execute('SELECT kind, version, data FROM entities WHERE id=?', (eid,)).fetchone()
    return None if row is None else {'kind': row[0], 'version': row[1], 'data': json.loads(row[2])}


def read(conn, decision):
    found = _row(conn, decision)
    if found is None or found['kind'] != KIND:
        return None
    return dict(found['data'], version=found['version'])


def records(conn):
    return [dict(json.loads(data), version=version) for _eid, version, data in conn.execute(
        'SELECT id, version, data FROM entities WHERE kind=? ORDER BY id', (KIND,))]


# ---------------------------------------------------------------------------------------------
# What the factory PM returns
# ---------------------------------------------------------------------------------------------

def document_problems(document, proposal_id):
    """Why `document` is not the PM's new-project document for `proposal_id`, by name."""
    if not isinstance(document, dict) or set(document) != set(DOCUMENT_FIELDS) or document.get('schema') != DOCUMENT:
        return ['invalid_input:document']
    problems = []
    if document['proposal_id'] != proposal_id:
        problems.append('invalid_input:document:proposal_id')
    if (not _is_str(document['project']) or not _NAME.match(document['project'])
            or document['project'] == FACTORY_PROJECT):
        problems.append('invalid_input:document:project')
    if document['identity'] is not None and not GI.identifier(document['identity']):
        problems.append('invalid_input:document:identity')
    if document['visibility'] not in (None,) + VISIBILITIES:
        problems.append('invalid_input:document:visibility')
    for field in ('objective', 'reason'):
        if not _is_str(document[field]):
            problems.append('invalid_input:document:' + field)
    return problems


# ---------------------------------------------------------------------------------------------
# Words: what his message and his answer name
# ---------------------------------------------------------------------------------------------

def names(text, word):
    """Whether `text` names `word` as a whole word, ignoring case."""
    if not isinstance(text, str) or not _is_str(word):
        return False
    return re.search(r'(?<!%s)%s(?!%s)' % (_WORD_EDGE, re.escape(word), _WORD_EDGE), text, re.IGNORECASE) is not None


# VELDO-0143 R3-2: a negator, and where a clause begins, for what his words affirm.
_NEGATOR = re.compile(r"(?<![A-Za-z0-9_])(?:not|no|never|nor|without|instead\s+of|rather\s+than|[A-Za-z]+n['\u2019]t)"
                      r"(?![A-Za-z0-9_])", re.IGNORECASE)
_CLAUSE = re.compile(r"[,.;:!?()\n]|(?<![A-Za-z0-9_])(?:but|and|so)(?![A-Za-z0-9_])", re.IGNORECASE)


def mentions(text, word):
    """For each whole-word occurrence of `word` in `text` (ignoring case), whether his words affirm it: False where
    a negator stands before it in its clause ("not under bcengi", "don't make it public"), True otherwise."""
    if not isinstance(text, str) or not _is_str(word):
        return []
    found = []
    for match in re.finditer(r'(?<!%s)%s(?!%s)' % (_WORD_EDGE, re.escape(word), _WORD_EDGE), text, re.IGNORECASE):
        clause = max((c.end() for c in _CLAUSE.finditer(text, 0, match.start())), default=0)
        found.append(_NEGATOR.search(text, clause, match.start()) is None)
    return found


def affirmed(text, words):
    """Whether `text` names one of `words` and negates none of them."""
    seen = [flag for word in words for flag in mentions(text, word)]
    return bool(seen) and all(seen)


def negated(text, words):
    """Whether `text` negates one of `words` anywhere."""
    return any(not flag for word in words for flag in mentions(text, word))


def identity_words(record):
    return [w for w in (record.get('id'), record.get('label')) if _is_str(w)]


def identity_named(text, offered):
    """The one offered identity `text` names (by id or label), or None: an answer to a question that
    offered exactly these identities."""
    found = [entry['identity'] for entry in offered or []
             if any(names(text, word) for word in entry.get('words') or [entry['identity']])]
    return found[0] if len(set(found)) == 1 else None


def identities_named(text, records):
    """The ids of the configured identities (GI records) `text` names, by id or label, each as a whole word."""
    return sorted({r['id'] for r in records if any(names(text, word) for word in identity_words(r))})


def shown_entry(presented, identity):
    """What `presented` showed him for `identity`: the proposal itself when it named that identity, else the
    offered entry for it, else None (he was not shown it)."""
    if not isinstance(presented, dict):
        return None
    if presented.get('identity') is not None:
        return presented if presented['identity'] == identity else None
    return next((e for e in presented.get('offered') or [] if e.get('identity') == identity), None)


def correction_problems(presented, terms, rationale, records):
    """Why the corrected `terms` ({project, identity, visibility, mode, adoption}) are not bound to his words
    (A CORRECTION IS BOUND TO HIS WORDS), each invalid_input:correction:<field>. `records` are the configured
    identities."""
    problems = []
    same_name = terms.get('project') == presented.get('project')
    if not same_name and not names(rationale, terms.get('project')):
        problems.append('invalid_input:correction:project')
    identity = terms.get('identity')
    # A changed identity or visibility is said only where his words name exactly that one, never negated; one he
    # was shown and negates does not stay (R3-2).
    said = sorted({r['id'] for r in records if affirmed(rationale, identity_words(r))})
    words = next((identity_words(r) for r in records if r.get('id') == identity), [identity])
    if not (said == [identity] if identity != presented.get('identity') else not negated(rationale, words)):
        problems.append('invalid_input:correction:identity')
    shown = shown_entry(presented, identity)
    reference = (shown or presented).get('remote') or {}
    visibility = terms.get('visibility')
    named = [v for v in VISIBILITIES if affirmed(rationale, [v])]
    if not (named == [visibility] if visibility != reference.get('visibility')
            else not negated(rationale, [visibility])):
        problems.append('invalid_input:correction:visibility')
    expected = shown.get('mode') if shown is not None and same_name else 'create'
    if terms.get('mode') != expected or (expected == 'adopt' and 'adoption' in terms
                                          and terms['adoption'] != shown.get('adoption')):
        problems.append('invalid_input:correction:mode')
    return problems


def proposal_terms(proposal):
    """The terms correction_problems judges, of a resolved proposal."""
    return {'project': proposal.get('project'), 'identity': proposal.get('identity'),
            'visibility': (proposal.get('remote') or {}).get('visibility'), 'mode': proposal.get('mode'),
            'adoption': proposal.get('adoption')}


def name_taken(conn, name, decision=None):
    """Whether `name` is already a project's or another live new-project decision's (A NAME IS ONE PROJECT)."""
    if not isinstance(name, str):
        return False
    folded = name.casefold()
    for (raw,) in conn.execute("SELECT data FROM entities WHERE kind='project'"):
        if str(json.loads(raw).get('name', '')).casefold() == folded:
            return True
    return any(r['id'] != decision and r.get('state') in LIVE and str(r.get('project', '')).casefold() == folded
               for r in records(conn))


# ---------------------------------------------------------------------------------------------
# The proposal
# ---------------------------------------------------------------------------------------------

def remote_url(identity, name):
    """The one GitHub URL a repository of `identity` named `name` lives at, in the transport its push
    credential uses (VELDO-0153 checks it against the identity's owner)."""
    if (identity.get('push_credential') or {}).get('kind') == 'ssh':
        return 'ssh://git@github.com/%s/%s.git' % (identity['remote_owner'], name)
    return 'https://github.com/%s/%s.git' % (identity['remote_owner'], name)


def directory_state(path):
    """absent, empty, repository (a Git repository whose top level it is) or not_empty."""
    try:
        entries = os.listdir(path)
    except FileNotFoundError:
        return 'absent'
    except NotADirectoryError:
        return 'not_empty'
    if not entries:
        return 'empty'
    if os.path.isdir(os.path.join(path, '.git')):
        return 'repository'
    return 'not_empty'


def _origin(path):
    done = organ('git_process').run(['git', '-C', str(path), '-c', 'core.hooksPath=' + os.devnull, 'config', '--get',
                                     'remote.origin.url'], capture_output=True, text=True, timeout=30)
    return done.stdout.strip() if done.returncode == 0 and done.stdout.strip() else None


def offered_entry(conn, domain, identity, name, repository, owner, visibility, templates=None):
    """What choosing `identity` decides for a project named `name`: its directory, mode, remote and, for a
    directory that is already a Git repository, the VELDO-0161 adoption proposal (its scaffold commit laid
    now, so the answer names it)."""
    directory = os.path.join(identity['projects_root'], name)
    chosen = visibility or identity.get('default_visibility') or 'private'
    remote = {'name': name, 'owner': identity['remote_owner'], 'url': remote_url(identity, name), 'visibility': chosen}
    if directory_state(directory) != 'repository':
        return {'identity': identity['id'], 'directory': directory, 'mode': 'create', 'remote': remote, 'adoption': None}
    origin = _origin(directory)
    if origin is None:
        raise Refused('invalid_input:directory:no_remote', directory)
    provisioner = organ('control_repository_provisioner')
    try:
        adoption, _event = provisioner.prepare(conn, domain, path=directory, identity=identity['id'], remote=origin,
                                               name=name, owner=owner, repository=repository, templates=templates)
    except provisioner.Refused as error:
        raise Refused(error.code, directory) from None
    remote = dict(remote, url=adoption['remote'])
    return {'identity': identity['id'], 'directory': adoption['path'], 'mode': 'adopt', 'remote': remote,
            'adoption': adoption}


def default_team(conn):
    """{revision, digest} of the factory's default team at its current revision (VELDO-0162 AC4)."""
    TR = organ('control_team_routes')
    head = _row(conn, TR.HEAD)
    if head is None or head['kind'] != 'default_team_head':
        raise Refused('missing_evidence:default_team')
    saved = _row(conn, TR.default_id(head['data']['revision']))
    if saved is None or saved['kind'] != TR.KIND:
        raise Refused('missing_evidence:default_team')
    return {'revision': saved['data']['revision'], 'digest': saved['data']['digest']}


def default_pipeline():
    """The default pipeline every project's cycles run (control_workflow_cycle_pm.WORKFLOW)."""
    return dict(organ('control_workflow_cycle_pm').WORKFLOW)


def intake_source(conn, intake_proposal):
    """(key, source data, first writing command) of the one intake source whose recorded result is the
    inbox proposal `intake_proposal`: the message that started it. None when there is not exactly one."""
    proposal = _row(conn, intake_proposal)
    if proposal is None or proposal['kind'] != INTAKE_PROPOSAL:
        return None
    found = []
    for key in proposal['data'].get('sources') or []:
        row = _row(conn, key)
        data = row['data'] if row is not None and row['kind'] == INTAKE_SOURCE else {}
        if data.get('proposal_id') == intake_proposal and (data.get('result') or {}).get('outcome') == 'inbox':
            found.append((key, data))
    if len(found) != 1:
        return None
    key, data = found[0]
    written = organ('control_objective').first_writer(conn, key)
    return key, data, (written[1] if written else None)


def build(conn, domain, intake, document, *, repository, owner, templates=None, decision=None, shown=None):
    """The proposal for the inbox proposal `intake` (its record's data) from the PM's `document`. Raises
    Refused by name when the document is not one, names something that does not exist, or names a project
    that is taken (A NAME IS ONE PROJECT; `decision` is the one being built, never its own rival). `shown` is
    the proposal he was shown, for a correction: an adoption shown for the same identity and name is kept as
    shown, its scaffold commit not laid again."""
    problems = document_problems(document, intake.get('proposal_id'))
    if problems:
        raise Refused(problems[0], '; '.join(problems))
    if name_taken(conn, document['project'], decision):
        raise Refused('stale_subject:project_exists', document['project'])
    identities = {r['id']: r for r in GI.records(conn, domain)}
    if not identities:
        raise Refused('missing_authority:git_identities')
    if document['identity'] is not None and document['identity'] not in identities:
        raise Refused('invalid_input:document:identity', 'no configured identity is named so')
    found = intake_source(conn, intake['proposal_id'])
    if found is None:
        raise Refused('missing_evidence:intake_source', intake['proposal_id'])
    key, source, command = found
    name = document['project']
    chosen = [identities[document['identity']]] if document['identity'] else [identities[i] for i in sorted(identities)]
    def entry(record):
        kept = shown_entry(shown, record['id']) if shown and shown.get('project') == name else None
        if kept is not None and kept.get('mode') == 'adopt':
            visibility = document['visibility'] or record.get('default_visibility') or 'private'
            return dict({k: kept[k] for k in IDENTITY_FIELDS}, remote=dict(kept['remote'], visibility=visibility))
        return offered_entry(conn, domain, record, name, repository, owner, document['visibility'], templates)
    entries = [entry(record) for record in chosen]
    proposal = {'project': name, 'repository': repository, 'owner': owner, 'identity': None, 'offered': None,
                'directory': None, 'mode': None, 'remote': None, 'adoption': None, 'objective': document['objective'],
                'charter': {'purpose': document['objective']}, 'authority_policy': json.loads(json.dumps(AUTHORITY_POLICY)),
                'team': default_team(conn), 'pipeline': default_pipeline(),
                'coordination_budget': dict(COORDINATION_BUDGET),
                'source': {'proposal_id': intake['proposal_id'], 'intake_source': key, 'intake_command': command,
                           'principal': source.get('principal'), 'source_kind': source.get('source_kind'),
                           'source_id': source.get('source_ref')}}
    if document['identity']:
        proposal.update(entries[0])
    else:
        proposal['offered'] = [dict(entry, words=identity_words(identities[entry['identity']])) for entry in entries]
    return proposal


def resolve(proposal, identity):
    """The proposal with `identity`, one of those it offered, chosen."""
    entry = next((e for e in proposal.get('offered') or [] if e['identity'] == identity), None)
    if entry is None:
        raise Refused('invalid_input:identity', 'not one of the offered identities')
    resolved = dict(proposal, offered=None)
    resolved.update({k: entry[k] for k in IDENTITY_FIELDS})
    return resolved


def proposal_problems(proposal, resolved=True):
    """Why `proposal` is not a complete proposal (a resolved one names its identity), by name."""
    if not isinstance(proposal, dict) or set(proposal) != set(PROPOSAL_FIELDS):
        return ['invalid_input:proposal:fields']
    problems = []
    if not _is_str(proposal['project']) or not _NAME.match(proposal['project']) or proposal['project'] == FACTORY_PROJECT:
        problems.append('invalid_input:proposal:project')
    for field in ('repository', 'owner', 'objective'):
        if not _is_str(proposal[field]):
            problems.append('invalid_input:proposal:' + field)
    if resolved:
        if not _is_str(proposal['identity']) or proposal['offered'] is not None:
            problems.append('invalid_input:proposal:identity')
        if proposal['mode'] not in MODES or not isinstance(proposal['directory'], str) or not os.path.isabs(
                proposal['directory']):
            problems.append('invalid_input:proposal:directory')
        remote = proposal['remote'] if isinstance(proposal['remote'], dict) else {}
        if set(remote) != {'name', 'owner', 'url', 'visibility'} or remote.get('visibility') not in VISIBILITIES:
            problems.append('invalid_input:proposal:remote')
        if (proposal['mode'] == 'adopt') != isinstance(proposal['adoption'], dict):
            problems.append('invalid_input:proposal:adoption')
    return problems


def _shown(value):
    return value if isinstance(value, str) else json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(', ', ': '))


def brief(proposal):
    """Exactly what the owner is shown, in plain text: every value his answer binds, so an approval
    approves exactly what is created, adopted and activated."""
    p = proposal if isinstance(proposal, dict) else {}

    def where(entry):
        remote = entry.get('remote') or {}
        how = ('adopted as it is, its scaffold %s' % (
            'laid as commit %s, pushed on your answer' % entry['adoption']['scaffold_commit']
            if (entry.get('adoption') or {}).get('scaffold_commit') else 'already present')
            if entry.get('mode') == 'adopt' else 'created')
        return 'directory %s (%s), remote %s (%s, under %s)' % (
            entry.get('directory'), how, remote.get('url'), remote.get('visibility'), remote.get('owner'))
    lines = ['Start project %s.' % _shown(p.get('project'))]
    if p.get('identity'):
        lines += ['Identity: %s' % p['identity'], 'Where: %s' % where(p)]
    else:
        lines.append('Identity: not named; answer with the one to use: %s.'
                     % ', '.join(e.get('identity', '') for e in p.get('offered') or []))
        lines += ['  %s: %s' % (e.get('identity'), where(e)) for e in p.get('offered') or []]
    team, pipeline = p.get('team') or {}, p.get('pipeline') or {}
    lines += ['First objective: %s' % _shown(p.get('objective')),
              'Team: default team revision %s (%s)' % (team.get('revision'), team.get('digest')),
              'Pipeline: %s version %s (%s)' % (pipeline.get('id'), pipeline.get('version'), pipeline.get('digest')),
              'Coordination budget: %s' % _shown(p.get('coordination_budget')),
              'Authority policy: %s' % _shown(p.get('authority_policy')),
              'Owner: %s. Repository id: %s.' % (_shown(p.get('owner')), _shown(p.get('repository'))),
              'Approving creates or adopts exactly this repository, activates the project and accepts its first '
              'objective; answer with a correction instead to change any of it.']
    return '\n'.join(lines)


def target(proposal):
    """The settlement terms target of the request that presents `proposal`."""
    name = proposal.get('project') if isinstance(proposal, dict) else None
    return {'kind': TARGET, 'ref': 'project:' + str(name), 'digest': digest(proposal)}


# ---------------------------------------------------------------------------------------------
# Who may answer, and when nothing is asked
# ---------------------------------------------------------------------------------------------

def factory_owner(conn):
    project = _row(conn, 'project:' + FACTORY_PROJECT)
    if project is None or project['kind'] != 'project' or project['data'].get('state') != 'ACTIVE':
        return None
    return project['data'].get('owner')


def owner_problems(store, membership, conn, owner, now=None):
    state = membership.authority_state(store, conn)
    entry = AC.membership_entry(state['membership'], owner)
    active, why = AC.active_member(entry, time.time() if now is None else now)
    if not active:
        return ['not_owner:' + str(why)]
    if entry.get('principal_type') != 'person' or OWNER_ROLE not in (entry.get('roles') or []):
        return ['not_owner:role']
    return []


def nothing_asked(conn, intake, proposal, owner):
    """[] when the message that started it is the owner's answer and nothing is presented (ONE ANSWER),
    else every reason it is presented."""
    reasons = []
    found = intake_source(conn, (intake or {}).get('proposal_id'))
    source = found[1] if found else {}
    if not owner or source.get('principal') != owner or (intake or {}).get('principal') != owner:
        reasons.append('not_the_owners_message')
    text = (intake or {}).get('text')
    if not isinstance(proposal, dict) or not proposal.get('identity'):
        reasons.append('identity_not_named')
    else:
        identity = next((r for r in GI.records(conn, (intake or {}).get('domain')) if r['id'] == proposal['identity']), {})
        if not any(names(text, word) for word in identity_words(identity)):
            reasons.append('identity_not_in_message')
    if not isinstance(proposal, dict) or not names(text, proposal.get('project')):
        reasons.append('project_not_in_message')
    return reasons


# ---------------------------------------------------------------------------------------------
# The settled decision
# ---------------------------------------------------------------------------------------------

def _request(conn, rid):
    """(request data, request row, terms data, terms row, settlement data, effect data, versions), or Refused."""
    found = _row(conn, rid)
    data = found['data'] if found is not None and found['kind'] == REQUEST_KIND else None
    if not isinstance(data, dict) or type(data.get('request_version')) is not int:
        raise Refused('no_settled_decision:no_request', str(rid))
    subject = data.get('subject') if isinstance(data.get('subject'), dict) else {}
    terms_row = _row(conn, subject.get('ref'))
    terms = terms_row['data'] if terms_row is not None and terms_row['kind'] == TERMS_KIND else None
    if not isinstance(terms, dict) or digest(terms) != subject.get('digest'):
        raise Refused('no_settled_decision:no_terms', 'the request names no recorded settlement terms')
    reference = data.get('settlement') if isinstance(data.get('settlement'), dict) else {}
    settlement, effect = _row(conn, reference.get('settlement_id')), _row(conn, reference.get('effect_id'))
    if not (data.get('state') == SETTLED_STATE and reference.get('request_version') == data['request_version']
            and settlement is not None and settlement['kind'] == SETTLEMENT_KIND
            and effect is not None and effect['kind'] == EFFECT_KIND):
        raise Refused('no_settled_decision:not_settled', 'the request version is not settled')
    s, e = settlement['data'], effect['data']
    if (s.get('request_id') != rid or s.get('request_version') != data['request_version']
            or s.get('terms_id') != terms.get('terms_id') or s.get('terms_digest') != digest(terms)
            or e.get('settlement_id') != s.get('settlement_id') or e.get('target') != terms.get('target')):
        raise Refused('no_settled_decision:settlement', 'the settlement is not the answer to these terms')
    versions = {rid: found['version'], subject['ref']: terms_row['version'],
                reference['settlement_id']: settlement['version'], reference['effect_id']: effect['version']}
    return data, terms, s, e, reference, versions


def settled(store, membership, conn, decision, now=None):
    """The settled new-project decision `decision` (ONE ANSWER), judged from its evidence, or Refused
    no_settled_decision:<why>. Reads only. Returns {decision, path, proposal, owner, request,
    settlement_id, effect_id, source, versions}."""
    record = read(conn, decision)
    if record is None:
        raise Refused('no_settled_decision:no_decision', str(decision))
    intake = _row(conn, record.get('proposal_id'))
    idata = intake['data'] if intake is not None and intake['kind'] == INTAKE_PROPOSAL else {}
    route = idata.get('route') if isinstance(idata.get('route'), dict) else {}
    if (idata.get('project') != FACTORY_PROJECT or route.get('route') != 'new_project'
            or decision != decision_id(record.get('proposal_id'))):
        raise Refused('no_settled_decision:not_a_new_project', 'the factory PM did not route it as a new project')
    owner = factory_owner(conn)
    path, proposal = record.get('path'), record.get('proposal')
    if path not in PATHS:
        # Presented and not answered yet, answered with a correction the PM has not read yet, or rejected.
        raise Refused('no_settled_decision:%s' % {'presenting': 'not_answered', 'presented': 'not_answered',
                                                  'correcting': 'correcting', 'rejected': 'rejected'}.get(
                                                      record.get('state'), 'not_settled'),
                      str(decision))
    if proposal_problems(proposal):
        raise Refused('no_settled_decision:proposal', str(decision))
    if proposal['owner'] != owner or proposal['source'].get('proposal_id') != record['proposal_id']:
        raise Refused('no_settled_decision:not_owner', 'the proposal is not the factory owner\'s')
    found = intake_source(conn, record['proposal_id'])
    if found is None or proposal['source'].get('intake_source') != found[0]:
        raise Refused('no_settled_decision:intake_source', 'the proposal names another message')
    problems = owner_problems(store, membership, conn, owner, now)
    if problems:
        raise Refused('no_settled_decision:' + problems[0], 'the owner is not a current person holding project_owner')
    result = {'decision': decision, 'path': path, 'proposal': proposal, 'owner': owner, 'request': None,
              'settlement_id': decision, 'effect_id': None, 'presentation_id': None, 'source': proposal['source'],
              'versions': {decision: record['version'], record['proposal_id']: intake['version']}}
    if path == 'own_message':
        reasons = nothing_asked(conn, idata, proposal, owner)
        if reasons or record.get('request') is not None:
            raise Refused('no_settled_decision:asked:' + (reasons or ['presented'])[0], 'his message is not the answer')
        return result
    presented = record.get('presented')
    data, terms, s, e, reference, versions = _request(conn, record.get('request'))
    if (terms.get('touchpoint') != TOUCHPOINT or terms.get('target') != target(presented)
            or terms.get('proposal') != presented or proposal_problems(presented, resolved=False)):
        raise Refused('no_settled_decision:not_this_proposal', 'the request presents another proposal')
    if data.get('brief') != brief(presented):
        raise Refused('no_settled_decision:brief', 'the owner was shown something other than this proposal')
    if s.get('principals') != [owner] or data.get('owner') != owner:
        raise Refused('no_settled_decision:not_owner', 'the settled answer is not the factory owner\'s')
    ruling = s.get('ruling')
    if e.get('type') != EFFECTS.get(ruling):
        raise Refused('no_settled_decision:not_approved:%s' % ruling, 'the owner did not approve or correct it')
    named = presented['identity'] or identity_named(s.get('rationale'), presented.get('offered'))
    if path == 'answer':
        if ruling != 'approve' or e.get('proposal') != presented or named is None:
            raise Refused('no_settled_decision:answer', 'his answer does not settle this proposal')
        expected = presented if presented['identity'] else resolve(presented, named)
        if proposal != expected:
            raise Refused('no_settled_decision:proposal', 'the decision names other values than his answer')
    else:
        correction = record.get('correction') if isinstance(record.get('correction'), dict) else {}
        if ruling != 'return_for_elaboration':
            raise Refused('no_settled_decision:answer', 'only a returned proposal is corrected')
        if (not _is_str(correction.get('dispatch')) or correction.get('rationale') != s.get('rationale')
                or correction.get('digest') != digest(proposal)
                or document_problems(correction.get('document'), record['proposal_id'])
                or proposal['repository'] != presented['repository'] or proposal['source'] != presented['source']):
            raise Refused('no_settled_decision:correction', 'the decision is not the PM\'s reading of his correction')
        problems = correction_problems(presented, proposal_terms(proposal), s.get('rationale'),
                                       GI.records(conn, idata.get('domain')))
        if problems:
            raise Refused('no_settled_decision:' + problems[0].split(':', 1)[1], 'the correction is not his words')
    versions.update(result['versions'])
    return dict(result, request=record['request'], settlement_id=s.get('settlement_id'),
                effect_id=reference.get('effect_id'), presentation_id=s.get('presentation_id'), versions=versions)


def repository_decision(store, membership, conn, decision, now=None):
    """The settled decision in the shape control_repository.settled returns, naming the one repository the
    decision creates or adopts: for an adoption its VELDO-0161 proposal, for a creation the proposal of the
    repository the provisioner made, its base the initial commit its record names."""
    judged = settled(store, membership, conn, decision, now)
    p = judged['proposal']
    if p['mode'] == 'adopt':
        adoption = dict(p['adoption'])
    else:
        R = organ('control_repository')
        record = R.read(conn, p['repository']) or {}
        if record.get('origin') != 'created' or record.get('request') != decision:
            raise Refused('no_settled_decision:not_created', 'no repository was created for this decision')
        adoption = R.adoption_proposal(repository=p['repository'], name=p['remote']['name'], owner=p['owner'],
                                       identity=p['identity'], path=p['directory'], remote=p['remote']['url'],
                                       default_branch=DEFAULT_BRANCH, base_commit=record.get('base_commit'),
                                       scaffold_commit=None)
    return {'proposal': adoption, 'request': decision, 'request_version': 1, 'settlement_id': judged['settlement_id'],
            'effect_id': judged['effect_id'], 'presentation_id': judged['presentation_id'],
            'terms_id': None, 'versions': judged['versions'], 'new_project': judged}


def pending(conn):
    """What the factory PM still has to read, oldest first: each NEW_PROJECT inbox proposal with no decision
    yet (it prepares the proposal) and each decision being corrected (it reads his correction)."""
    out = []
    decided = {r['proposal_id']: r for r in records(conn)}
    for eid, version, raw in conn.execute('SELECT id, version, data FROM entities WHERE kind=? ORDER BY id',
                                          (INTAKE_PROPOSAL,)):
        data = json.loads(raw)
        if data.get('project') != FACTORY_PROJECT or data.get('state') != NEW_PROJECT_STATE:
            continue
        record = decided.get(eid)
        if record is None:
            out.append({'proposal_id': eid, 'version': version, 'decision': None, 'correction': None})
        elif record['state'] == 'correcting':
            out.append({'proposal_id': eid, 'version': version, 'decision': record['id'],
                        'decision_version': record['version'],
                        'correction': {'rationale': (record.get('correction') or {}).get('rationale'),
                                       'presented': record.get('presented')}})
    return out


# ---------------------------------------------------------------------------------------------
# The decisions, written
# ---------------------------------------------------------------------------------------------

class NewProjects:
    """The factory's new-project decisions on the service's connection. `inbox`, `settlement` and `presenter`
    are the VELDO-0064/0068/0065 services of this connection, `assignment` the control_assignment module;
    `requester` and `request_sign` sign the presented request (the factory PM's principal). The owner is told
    what became of a decision by its record: VELDO-0128's report projects it entering activated or failed
    (control_telegram_report project_ready) through the reporter's one rendered send. `provisioner` is the
    installation's provisioner configuration, or a callable answering it (None when there is none: NOTHING IS
    ASKED THAT CANNOT BE CARRIED OUT). `notify(state)` is called after every decision written, so the running
    service's new-project pass is made due by a decision the factory PM's run settled (VELDO-0143 F1)."""

    def __init__(self, store, membership, conn, ids, journal_signer, sign, *, inbox=None, settlement=None,
                 presenter=None, assignment=None, requester='pm', request_sign=None, templates=None,
                 generation=1, clock=time.time, provisioner=None, notify=None):
        self.store, self.membership, self.conn, self.ids = store, membership, conn, dict(ids)
        self.journal_signer, self.sign, self.generation, self.clock = journal_signer, sign, generation, clock
        self.inbox, self.settlement, self.presenter, self.assignment = inbox, settlement, presenter, assignment
        self.requester, self.request_sign, self.templates = requester, request_sign, templates
        self.provisioner, self.notify = provisioner, notify
        self.observations = []
        conn.command_registry[OPERATION] = {'transition': self._transition, 'writes': WRITES}

    @staticmethod
    def _transition(params, before):
        return {params['id']: {'kind': KIND, 'data': params['record']}}

    def _observe(self, operation, outcome, refusal=None, **fields):
        event = dict(kind='new_project', operation=operation, outcome=outcome, refusal=refusal, at=self.clock(),
                     domain_uuid=self.ids.get('domain_uuid'), **fields)
        self.observations.append(event)
        return event

    def write(self, decision, state, *, step, **fields):
        """Write the decision into `state` (TRANSITIONS), appending one history entry; Refused by name."""
        prior = read(self.conn, decision)
        current = None if prior is None else prior.get('state')
        if state not in TRANSITIONS.get(current, ()):
            raise Refused('invalid_transition:%s->%s' % (current, state), decision)
        at = self.clock()
        record = {k: v for k, v in (prior or {}).items() if k != 'version'}
        record.update(fields)
        record.update(schema=SCHEMA, id=decision, state=state, updated_at=at)
        entry = {'step': step, 'state': state, 'at': at}
        if fields.get('reason'):
            entry['reason'] = fields['reason']
        record['history'] = list(record.get('history') or []) + [entry]
        nonce = '%s:%d:%s' % (decision, len(record['history']), state)
        command = {'command_id': '%s:%s' % (OPERATION, nonce), 'principal': self.journal_signer, 'operation': OPERATION,
                   'parameters': {'id': decision, 'record': record},
                   'expected_versions': {decision: 0 if prior is None else prior['version']}, 'artifact_digests': [],
                   'nonce': nonce}
        self.store.execute(self.conn, command, self.journal_signer, self.sign, self.generation)
        if self.notify is not None:
            self.notify(state)
        return read(self.conn, decision)

    def provisioning(self):
        """The installation's provisioner configuration, or None."""
        return self.provisioner() if callable(self.provisioner) else self.provisioner

    def _fail(self, decision, step, reason, **fields):
        """The decision `failed` by name, its report telling him why; the message has its decision and is not
        read again."""
        self.write(decision, 'failed', step=step, reason=reason, **fields)

    def pending(self):
        return pending(self.conn)

    def propose(self, intake_proposal, document, *, dispatch):
        """The factory PM's document for a NEW_PROJECT inbox proposal: one proposal, settled by his message
        or presented once. Returns {ok, outcome (settled or presented), decision, ...} or {ok False, reason}."""
        decision = decision_id(intake_proposal)
        about = dict(proposal_id=intake_proposal, decision=decision, dispatch=dispatch)
        try:
            intake = _row(self.conn, intake_proposal)
            data = intake['data'] if intake is not None and intake['kind'] == INTAKE_PROPOSAL else {}
            if data.get('project') != FACTORY_PROJECT or data.get('state') != NEW_PROJECT_STATE:
                raise Refused('invalid_input:not_a_new_project', intake_proposal)
            if read(self.conn, decision) is not None:
                raise Refused('stale_version:already_proposed', decision)
            owner = factory_owner(self.conn)
            if owner is None:
                raise Refused('unsupported_configuration:factory_project')
            problems = document_problems(document, intake_proposal)
            if problems:
                raise Refused(problems[0], '; '.join(problems))
            terminal = None
            if not self.provisioning():
                terminal = 'unavailable_service:provisioner'
            elif name_taken(self.conn, document['project'], decision):
                terminal = 'stale_subject:project_exists'
            if terminal:
                self._fail(decision, 'proposal', terminal, proposal_id=intake_proposal, path=None, document=document,
                           dispatch=dispatch, presented=None, request=None, proposal=None, correction=None,
                           project=document['project'], repository=None)
                return dict(self._observe('propose', 'failed', terminal, project=document['project'], **about),
                            ok=False, reason=terminal)
            proposal = build(self.conn, self.ids['domain_uuid'], data, document, repository=str(uuid.uuid4()),
                             owner=owner, templates=self.templates, decision=decision)
            reasons = nothing_asked(self.conn, data, proposal, owner)
            if not reasons:
                self.write(decision, 'settled', step='own_message', proposal_id=intake_proposal, path='own_message',
                           document=document, dispatch=dispatch, presented=None, request=None, proposal=proposal,
                           correction=None, project=proposal['project'], repository=proposal['repository'], reason=None)
                return dict(self._observe('propose', 'settled', path='own_message', project=proposal['project'],
                                          identity=proposal['identity'], **about), ok=True)
            # Recorded before anything is presented, so a presentation a crash or the store interrupted is finished
            # from the record (resume), never built again.
            alias = 'new-project-' + hashlib.sha256(decision.encode()).hexdigest()[:24]
            deadline = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(self.clock() + 7 * 86400))
            self.write(decision, 'presenting', step='presenting', proposal_id=intake_proposal, path=None,
                       document=document, dispatch=dispatch, presented=proposal, request=None, proposal=None,
                       correction=None, project=proposal['project'], repository=proposal['repository'], reason=None,
                       presentation={'alias': alias, 'deadline': deadline})
            request = self._present(decision, proposal, owner, alias, deadline)
            self.write(decision, 'presented', step='presented', request=request)
        except (Refused, self.store.StoreRefused) as error:
            return dict(self._observe('propose', 'refused', error.code, **about), ok=False, reason=error.code)
        return dict(self._observe('propose', 'presented', asked=reasons, request=request, project=proposal['project'],
                                  identity=proposal['identity'], **about), ok=True)

    def _signed(self, **fields):
        command = dict(self.ids, principal=self.requester, **fields)
        return dict(command=command, signature=self.request_sign(self.store.canonical_bytes(command)))

    def _present(self, decision, proposal, owner, alias, deadline):
        """The one VELDO-0068 request that presents `proposal` to the owner: its terms, the inbox request,
        its framing and its presentation, under `alias` and `deadline` as the decision records them, so a retry
        carries the same commands (the store replays them; the presenter never sends a presentation twice).
        Returns the request id."""
        if None in (self.settlement, self.inbox, self.presenter, self.assignment, self.request_sign):
            raise Refused('unavailable_service:presentation')
        terms = self.settlement.terms(self._signed(operation='terms', terms=alias, command_id=alias + '-terms',
                                                   nonce=alias + '-terms', touchpoint=TOUCHPOINT,
                                                   target=target(proposal), proposal=proposal, required_roles=[],
                                                   quorum=None))
        if terms.get('outcome') != 'recorded':
            raise Refused('unavailable_service:terms', str(terms.get('reason')))
        self.inbox.apply(self._signed(operation='open', alias=alias, command_id=alias + '-open', nonce=alias + '-open',
                                      assignment=dict(kind='decision', owner=owner, scope=[FACTORY_PROJECT],
                                                      deadline=deadline, budget={'owner_minutes': 10},
                                                      brief=brief(proposal), choices=list(CHOICES),
                                                      subject=terms['subject'])))
        request = self.assignment.assignment_id(self.ids['repository_uuid'], alias)
        if self.inbox.read(request) is None:
            raise Refused('unavailable_service:request')
        self.presenter.frame(self._signed(operation='frame', alias=alias, request_version=1,
                                          risk_statement='Approving creates a repository under the identity shown and '
                                                         'activates the project; it is removed only by hand.',
                                          command_id=alias + '-frame', nonce=alias + '-frame'))
        self.presenter.present(request)
        return request

    def resume(self):
        """Each decision whose presentation did not finish (PRESENTED ONCE, EVEN ACROSS A CRASH): presented now
        from its record, then `presented`. Returns the observations made."""
        made = []
        for record in records(self.conn):
            if record['state'] != 'presenting':
                continue
            about = dict(decision=record['id'], proposal_id=record['proposal_id'])
            shown, presentation = record['presented'], record.get('presentation') or {}
            try:
                request = self._present(record['id'], shown, shown['owner'], presentation['alias'],
                                        presentation['deadline'])
                self.write(record['id'], 'presented', step='presented', request=request)
                made.append(self._observe('resume', 'presented', request=request, **about))
            except (Refused, self.store.StoreRefused) as error:
                made.append(self._observe('resume', 'refused', error.code, **about))
        return made

    def apply_settled(self):
        """Each presented decision whose request is settled: an approval naming the identity settles it, a
        return or an approval naming none hands his words to the factory PM, a reject ends it. No question is
        ever sent here. Returns the observations made."""
        made = []
        for record in records(self.conn):
            if record['state'] != 'presented':
                continue
            about = dict(decision=record['id'], proposal_id=record['proposal_id'], request=record['request'])
            row = _row(self.conn, record['request'])
            if row is None or row['data'].get('state') != SETTLED_STATE:
                continue
            reference = row['data'].get('settlement') or {}
            settled_row = _row(self.conn, reference.get('settlement_id'))
            if settled_row is None:
                continue
            s, presented = settled_row['data'], record['presented']
            ruling = s.get('ruling')
            try:
                if ruling == 'reject':
                    self.write(record['id'], 'rejected', step='answer', reason='rejected')
                    made.append(self._observe('answer', 'rejected', **about))
                    continue
                named = presented['identity'] or identity_named(s.get('rationale'), presented.get('offered'))
                if ruling == 'approve' and named is not None:
                    proposal = presented if presented['identity'] else resolve(presented, named)
                    self.write(record['id'], 'settled', step='answer', path='answer', proposal=proposal)
                    made.append(self._observe('answer', 'settled', path='answer', identity=named, **about))
                    continue
                if ruling == 'approve':
                    # The identity was asked and his approval did not say it: nothing is chosen for him.
                    self._fail(record['id'], 'answer', 'invalid_input:answer:identity')
                    made.append(self._observe('answer', 'failed', 'invalid_input:answer:identity', **about))
                    continue
                self.write(record['id'], 'correcting', step='answer',
                           correction={'rationale': s.get('rationale'), 'ruling': ruling, 'dispatch': None,
                                       'document': None, 'digest': None})
                made.append(self._observe('answer', 'correcting', ruling=ruling, **about))
            except (Refused, self.store.StoreRefused) as error:
                made.append(self._observe('answer', 'refused', error.code, **about))
        return made

    def correct(self, decision, document, *, dispatch):
        """The factory PM's reading of his correction: the corrected proposal settles the decision, with no
        second presentation; one that still names no identity fails it by name."""
        about = dict(decision=decision, dispatch=dispatch)
        record = read(self.conn, decision)
        try:
            if record is None or record['state'] != 'correcting':
                raise Refused('stale_version:not_correcting', decision)
            presented = record['presented']
            intake = _row(self.conn, record['proposal_id'])['data']
            problems = document_problems(document, record['proposal_id'])
            if problems:
                raise Refused(problems[0], '; '.join(problems))
            correction = dict(record['correction'], dispatch=dispatch, document=document)
            rationale = correction.get('rationale')
            configured = {r['id']: r for r in GI.records(self.conn, self.ids['domain_uuid'])}
            failure = None
            if document['identity'] is None:
                failure = 'invalid_input:identity'
            elif document['identity'] not in configured:
                raise Refused('invalid_input:document:identity', 'no configured identity is named so')
            else:
                # Judged before anything is built, so nothing is laid for terms he did not say or see.
                chosen = configured[document['identity']]
                directory = os.path.join(chosen['projects_root'], document['project'])
                terms = {'project': document['project'], 'identity': document['identity'],
                         'visibility': document['visibility'] or chosen.get('default_visibility') or 'private',
                         'mode': 'adopt' if directory_state(directory) == 'repository' else 'create'}
                problems = correction_problems(presented, terms, rationale, configured.values())
                if not problems and name_taken(self.conn, document['project'], decision):
                    problems = ['stale_subject:project_exists']
                failure = problems[0] if problems else None
            proposal = None
            if failure is None:
                proposal = build(self.conn, self.ids['domain_uuid'], intake, document,
                                 repository=presented['repository'], owner=presented['owner'],
                                 templates=self.templates, decision=decision, shown=presented)
                problems = correction_problems(presented, proposal_terms(proposal), rationale, configured.values())
                failure = problems[0] if problems else None
            if failure is not None:
                self._fail(decision, 'correction', failure, correction=correction, project=document['project'])
                return dict(self._observe('correct', 'failed', failure, **about), ok=False, reason=failure)
            correction['digest'] = digest(proposal)
            self.write(decision, 'settled', step='correction', path='correction', proposal=proposal,
                       project=proposal['project'], correction=correction)
        except (Refused, self.store.StoreRefused) as error:
            return dict(self._observe('correct', 'refused', error.code, **about), ok=False, reason=error.code)
        return dict(self._observe('correct', 'settled', path='correction', project=proposal['project'],
                                  identity=proposal['identity'], **about), ok=True)

    def settled_decisions(self):
        """The decisions settled and not yet activated or failed, oldest first."""
        return [r for r in records(self.conn) if r['state'] == 'settled']

    def finish(self, decision, *, activated, reason=None):
        """The decision activated (the project and its first objective) or failed by name; its report tells the
        owner which (project_ready). A failed repository is never reported ready."""
        record = read(self.conn, decision)
        name = (record.get('proposal') or {}).get('project')
        if activated:
            self.write(decision, 'activated', step='activated', reason=None)
        else:
            self.write(decision, 'failed', step='failed', reason=reason)
        self._observe('finish', 'activated' if activated else 'failed', reason, decision=decision, project=name)
        return read(self.conn, decision)


def metrics(conn, observations=()):
    """Decisions by state and by the path that settled them, and every refusal by its code."""
    every = records(conn)
    refused = {}
    for event in observations:
        if event.get('kind') == 'new_project' and event.get('outcome') == 'refused':
            refused[event.get('refusal')] = refused.get(event.get('refusal'), 0) + 1
    return {'by_state': {s: sum(1 for r in every if r['state'] == s) for s in STATES},
            'by_path': {p: sum(1 for r in every if r.get('path') == p) for p in PATHS},
            'asked': sum(1 for r in every if r.get('request')), 'refused_by_reason': refused}


# ---------------------------------------------------------------------------------------------
# The same settlement activates the project (VELDO-0143 AC3)
# ---------------------------------------------------------------------------------------------

def first_team(teams, decision, judged):
    """The project's first team revision: the default team revision the answered proposal named, after
    VELDO-0089's staffing checks (control_team Teams), accepted by the decision. A staffing problem refuses
    by name with VELDO-0089's owner request, and the project gets no team."""
    CT, TR = organ('control_team'), organ('control_team_routes')
    conn, proposal = teams.conn, judged['proposal']
    name, owner = proposal['project'], proposal['owner']
    tid = CT.team_id(name)
    if _row(conn, tid) is not None:
        return {'ok': True, 'reason': 'exists', 'team': CT.read(teams.store, conn, name)}
    saved = _row(conn, TR.default_id(proposal['team']['revision']))
    if (saved is None or saved['kind'] != TR.KIND or saved['data'].get('digest') != proposal['team']['digest']
            or saved['data'].get('revision') != proposal['team']['revision']):
        return {'ok': False, 'reason': 'stale_subject:default_team'}
    project = _row(conn, 'project:' + name)
    if project is None or project['data'].get('state') != 'ACTIVE':
        return {'ok': False, 'reason': 'project_not_active'}
    state = teams.membership.authority_state(teams.store, conn)
    pinned = [tid, 'project:' + name, TR.default_id(saved['data']['revision']), decision, owner,
              teams.membership.VERSIONS_ENTITY]
    cid = 'default-team-decision-' + hashlib.sha256(decision.encode()).hexdigest()[:32]
    params = dict(action='owner_save', team_id=tid, project=name, principal=owner, command_id=cid, at=teams.clock())
    try:
        teams._propose({'team': saved['data']['team']}, state, project['data'], None, params, pinned, teams.clock())
        params['acceptance'] = dict(request_id=judged['request'], settlement_id=judged['settlement_id'],
                                    effect_id=judged['effect_id'], principals=[owner], ruling='approve', decision=decision,
                                    default_team={'revision': saved['data']['revision'], 'digest': saved['data']['digest']})
        versions = {eid: state['entities'].get(eid, {}).get('version', 0) for eid in pinned}
        teams.store.execute(conn, dict(command_id=cid, principal=owner, operation=CT.OPERATION, parameters=params,
                                       expected_versions=versions, artifact_digests=[], nonce=cid),
                            teams.journal_signer, teams.sign, teams.authority_generation)
    except (CT.Refused, teams.store.StoreRefused) as error:
        return {'ok': False, 'reason': error.code, 'owner_request': getattr(error, 'owner_request', None)}
    return {'ok': True, 'reason': 'inherited', 'team': CT.read(teams.store, conn, name)}


def activate(decisions, decision, *, projects, teams, intake, objectives, pm, pm_sign, ids):
    """Apply the settled `decision` once its repository is active (THE SAME SETTLEMENT ACTIVATES). `ids` are
    the coordinates the objective commands carry (the new project's repository); `pm` and `pm_sign` the
    project manager the PM's commands are signed as. Returns {ok, step, reason, ...}; each step already done
    is kept."""
    OB = organ('control_objective')
    conn = decisions.conn
    if (read(conn, decision) or {}).get('state') == 'activated':
        return {'ok': True, 'step': 'activated', 'repeated': True}
    try:
        judged = settled(decisions.store, decisions.membership, conn, decision)
    except Refused as error:
        return {'ok': False, 'step': 'settlement', 'reason': error.code}
    proposal = judged['proposal']
    name, owner, pid = proposal['project'], proposal['owner'], proposal['source']['proposal_id']
    project = _row(conn, 'project:' + name)
    if project is None:
        done = projects.activate_decided(decision)
        if done.get('reason') == 'already_exists':
            decisions.finish(decision, activated=False, reason='already_exists')
            return {'ok': False, 'step': 'activation', 'reason': 'already_exists', 'failed': True}
        if not done.get('ok'):
            return {'ok': False, 'step': 'activation', 'reason': done.get('reason')}
    elif (project['data'].get('provenance') or {}).get('decision') != decision:
        # The name was taken meanwhile: the decision fails by name, never tried again (A NAME IS ONE PROJECT).
        decisions.finish(decision, activated=False, reason='already_exists')
        return {'ok': False, 'step': 'activation', 'reason': 'already_exists', 'failed': True}
    team = first_team(teams, decision, judged)
    if not team.get('ok'):
        return {'ok': False, 'step': 'team', 'reason': team.get('reason'), 'owner_request': team.get('owner_request')}
    target = pid + ':project'
    if _row(conn, target) is None:
        moved = intake.resolve_new_project(pid, project=name, decision=decision)
        if not moved.get('ok'):
            return {'ok': False, 'step': 'objective_proposal', 'reason': moved.get('reason')}
    oid = OB.objective_id(target)

    def signed(**body):
        command = dict(ids, principal=pm, **body)
        return {'command': command, 'signature': pm_sign(decisions.store.canonical_bytes(command))}
    current = OB.read(conn, oid)
    if current is None:
        made = objectives.apply(signed(operation='propose', command_id='objective-propose:' + oid,
                                       nonce='objective-propose:' + oid, proposal=target,
                                       outcome=proposal['objective'], scope=[name],
                                       authority={'acceptor': owner, 'assessor': owner},
                                       evidence_requirements=[{'id': 'gate', 'kind': 'gate_observation'}]))
        if not made.get('ok'):
            return {'ok': False, 'step': 'objective', 'reason': made.get('reason')}
        current = OB.read(conn, oid)
    if current['state'] == 'PROPOSED':
        accepted = objectives.apply(signed(operation='accept_decided', command_id='objective-decided:' + oid,
                                           nonce='objective-decided:' + oid, objective=oid,
                                           objective_version=current['version'], decision=decision,
                                           revision=current['revision'], bound_digest=current['bound_digest']))
        if not accepted.get('ok'):
            return {'ok': False, 'step': 'acceptance', 'reason': accepted.get('reason')}
    decisions.finish(decision, activated=True)
    return {'ok': True, 'step': 'activated', 'project': name, 'objective': oid}
