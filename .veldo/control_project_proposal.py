"""A new project from chat: the factory PM's one proposal and the owner's one answer (VELDO-0143 AC1).

WHAT THIS MODULE IS. The one reader and writer of a new-project decision (entity `new-project:<intake
proposal>` of kind `new_project`), and the one judge of whether such a decision is settled. Intake keeps a
message the factory PM routed as a new project in state NEW_PROJECT (VELDO-0152 AC3); the factory project's
next PM run reads it and returns one DOCUMENT naming only what needs judgment: the project's name, the
identity when the owner said one, the visibility when he said one, and the first objective. Everything else
the proposal binds is derived here, never chosen by the PM: the identities it offers (every configured one),
the repository's uuid, the directory under the
identity's projects root, the remote under the identity's owner, whether the directory is already a Git
repository (then the adoption path of VELDO-0161, its scaffold commit laid before he is asked), the default
team's current revision (VELDO-0162 AC4), the default pipeline (the PM cycle's WORKFLOW, VELDO-0132), the
charter, the authority policy and the coordination budget.

ONE ANSWER. The proposal is settled by exactly one of three paths, and nothing is asked after it:

  own_message  the message that started it is the answer and nothing is presented: it is the factory
               owner's own authenticated message (his intake source), the PM named an identity, the message
               names the project and that identity, each as a whole word, and no other identity, and it is
               plain ASCII with no negator, no word of visibility and no other word the rule has not read
               (PLAIN_WORDS, R8-3) anywhere; the repository is created
               private, never public and never an adoption, whatever the identity's default or the PM's
               document says (nothing_asked, VELDO-0143 R7-1). Any doubt presents it, so it costs him one
               choice; a repository that is not private always comes from a pick.
  answer       otherwise the proposal is presented once to the factory owner as a VELDO-0068 request whose
               terms target TARGET (the project and the digest of the proposal), whose brief is exactly
               brief(proposal) and whose choices are exactly choices(proposal); the choice he picks settles it.
  correction   his answer returns the proposal with his words (return_for_elaboration): the factory PM's
               next run reads the proposal and his words and returns the corrected document, which settles
               it with no second presentation.

THE IDENTITY AND THE VISIBILITY ARE CHOSEN, NEVER READ (VELDO-0143 round 7, owner decision Telegram 36174 and
36175). The proposal offers every configured identity, each with its directory, remote and mode, and its choices
(VELDO-0065's choices mechanism, a pick each) are: `accept`, which approves exactly the identity and visibility it
shows (offered only when it shows an identity), one pick `accept <identity> <visibility>` for every other pair of
an offered identity and a visibility, `return_for_elaboration` and `reject`. The decision binds the identity and
the visibility only from the choice he picked (answered): the values shown stay when he picks none of the
alternatives. His words, his reason and the PM's document never change either: no text is read for them. A
directory that is already a Git repository is adopted with its remote as it is on GitHub (AS_ON_REMOTE, R7-2):
nothing on the adoption path applies a visibility, so its entry is offered no visibility pick, only `accept
<identity> adopt`, a shape no creation pick folds into (R8-1), and the brief says so. A reject settles nothing and the decision is `rejected`.

A CORRECTION CHANGES ONLY THE NAME AND THE OBJECTIVE (correction_problems). The PM reads his correction; it never
chooses for him. The corrected document's objective is the PM's reading of his words. Its project name other than
the presented one is bound only where his words name it as a whole word and hold no negator anywhere (_NEGATOR).
Its identity and visibility must be null or the ones he was shown (a proposal that showed no identity cannot be
corrected: the identity is picked, never typed), and the mode is the one shown for that identity and name (an
adoption is only ever an adoption he was shown, its scaffold commit the one shown; a name he was not shown is a
creation). Anything else fails the decision by name, invalid_input:correction:<field>, before anything is built
or laid, his report tells him in plain words that it could not be set up and why, and the one judge refuses it
again (no_settled_decision:correction:<field>).

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
which the store replays and the presenter does not send twice; nothing is built again. A request the presenter
refuses for a reason no retry changes (NOT_PRESENTABLE, e.g. two choices that fold alike) fails the decision
invalid_input:<refusal>, so his report tells him, rather than leaving it presented to no one (R7-3); the decision
fails before the request is canceled, and a request a crash left open is canceled at the next pass (R8-2).

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
TRANSITIONS = {None: ('presenting', 'settled', 'failed'), 'presenting': ('presented', 'failed'),
               'presented': ('settled', 'correcting', 'rejected', 'failed'),
               'correcting': ('settled', 'failed'), 'settled': ('settled', 'failed', 'activated')}
# A new-project decision still live: its name is taken (A NAME IS ONE PROJECT).
LIVE = ('presenting', 'presented', 'correcting', 'settled')
PATHS = ('own_message', 'answer', 'correction')
# VELDO-0143 round 8 (R7-3): the presenter's refusals (control_channel_presentation compose) that the same request
# meets again on every retry; the decision fails invalid_input:<refusal>.
NOT_PRESENTABLE = ('ambiguous_choice', 'unmapped_choice', 'presentation_too_long')
# The VELDO-0068 request the owner answers when his message did not settle it.
TOUCHPOINT, TARGET = 'decision_disposition', 'new_project'
CHOICES = ['accept', 'return_for_elaboration', 'reject']
# The first word of a pick (control_channel_presentation.PICK_WORD): `accept <identity> <visibility>` approves with
# that identity and visibility (choices).
PICK = 'accept'
# VELDO-0143 round 9 (R8-1): the last word of an adoption's pick, `accept <identity> adopt`. Every pick folds
# (control_channel_presentation._fold) to its words, and a creation's last word is a visibility, so a pick ending in
# this word never folds like a creation's whatever the ids are; two picks fold alike only when their ids do, which
# control_git_identity.validate refuses.
ADOPT_WORD = 'adopt'
REQUEST_KIND, TERMS_KIND, SETTLEMENT_KIND, EFFECT_KIND = 'assignment', 'settlement_terms', 'request_settlement', 'settlement_effect'
SETTLED_STATE = 'SATISFIED'
EFFECTS = {'approve': 'decision_approved', 'return_for_elaboration': 'decision_returned'}
OWNER_ROLE = 'project_owner'
FACTORY_PROJECT = 'factory'
INTAKE_PROPOSAL, INTAKE_SOURCE, NEW_PROJECT_STATE = 'intake_proposal', 'intake_source', 'NEW_PROJECT'
# What every proposal binds, in the order a missing one is named.
PROPOSAL_FIELDS = ('project', 'repository', 'owner', 'identity', 'offered', 'directory', 'mode', 'remote', 'adoption',
                   'objective', 'charter', 'authority_policy', 'team', 'pipeline', 'coordination_budget', 'source')
# What the chosen identity decides: one offered entry for each configured identity.
IDENTITY_FIELDS = ('identity', 'directory', 'mode', 'remote', 'adoption')
MODES = ('create', 'adopt')
VISIBILITIES = ('private', 'public')
# VELDO-0143 round 8 (R7-2): an adoption keeps the existing remote's visibility, which nothing on the adoption path
# changes and nothing here reads, so its entry records this, is offered no visibility pick and is shown "as it is
# on GitHub"; a resolved adoption naming any other visibility is not a proposal (proposal_problems).
AS_ON_REMOTE = 'as_on_remote'
# The defaults every new project starts with; the proposal names them, so his answer binds them.
AUTHORITY_POLICY = {'team_amendment': [OWNER_ROLE]}
COORDINATION_BUDGET = {'capacity': 4, 'invocations': 400, 'wall_seconds': 7 * 86400}
DEFAULT_BRANCH = 'main'
_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$')
# A whole word's edges (VELDO-0143 R4-1), for a project's name his correction or his own message names and an identity
# his own message names (nothing_asked): a letter, digit or underscore continues a word, and so does a '.' or '-'
# joined to one ("shoal-two", "fjord.io"); a '.' or '-' with nothing after it ends the word.
_LEFT_EDGE = r'(?<![A-Za-z0-9_])(?<![A-Za-z0-9_][.-])'
_RIGHT_EDGE = r'(?![A-Za-z0-9_]|[.-][A-Za-z0-9_])'


class Refused(Exception):
    def __init__(self, code, detail=''):
        super().__init__('%s: %s' % (code, detail) if detail else code)
        self.code, self.detail = code, detail


class NotPresented(Refused):
    """The presenter refused the request for a reason no retry changes (NOT_PRESENTABLE): the decision fails by
    that name, so his report tells him, rather than staying presented to no one."""


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
    return re.search(_LEFT_EDGE + re.escape(word) + _RIGHT_EDGE, text, re.IGNORECASE) is not None


# VELDO-0143 round 6: whether a negator stands anywhere, failing closed. Since round 7 it guards only a changed
# project name and the message that is its own answer; no text is read for an identity or a visibility. A negator
# starts where no letter or digit stands before it and, but for the prefix "non", ends where none follows it, so a
# hyphen, an underscore, a period or a line break never joins it to another word.
_START, _END = r'(?<![^\W_])', r'(?![^\W_])'
_NEGATOR = re.compile(_START + r"(?:non|(?:not|no|nope|nah|nay|none|nor|neither|never|nothing|nobody|nowhere"
                      r"|without|cannot|avoid|avoiding|except|excepting|exclude|excluding|instead\s+of|rather\s+than"
                      r"|other\s+than|in\s+place\s+of|(?:anything|everything|all)\s+but|skip|drop|remove|refuse"
                      r"|reject|decline|against|wrong|stop|hate|dislike|mistake|forget|nein|nicht|kein|keine|pas"
                      r"|(?:do|does|did|is|are|was|were|wo|ca|could|would|should|must|might|has|have|had|need|sha|ai)nt"
                      r"|\w*n['\u2018\u2019`\u00b4]t|\u043d\u0435|\u043d\u0435\u0442|\u043d\u0438)"
                      + _END + r")", re.IGNORECASE)


def negates(text):
    """Whether a negator stands anywhere in `text`."""
    return isinstance(text, str) and _NEGATOR.search(text) is not None


# VELDO-0143 round 8 (R7-1): a word that could say what he wants of the visibility. His own message that holds one is
# presented, so the visibility is picked, never read from it. Each is read as a whole word between non-letters, so
# "opensource" or "publically" is not one; since round 9 (R8-3) a word the rule has not read (PLAIN_WORDS) presents
# his message, so no list of visibility words has to be complete.
_VISIBILITY_WORD = re.compile(r'(?<![^\W_])(?:private|privately|public|publicly|visib\w*|invisib\w*|hid\w*|secret\w*'
                              r'|open|opened|closed|internal)(?![^\W_])', re.IGNORECASE)


def says_visibility(text):
    """Whether a word that could name a visibility stands anywhere in `text`."""
    return isinstance(text, str) and _VISIBILITY_WORD.search(text) is not None


# VELDO-0143 round 9 (R8-3): the words his own message may hold and still settle unasked, besides the project's name
# and the identity's id or label: words that ask for a project and say nothing of what it should be. Any other word
# ("share it with everyone", "publish it", "make it opensource") might ask for something this rule cannot read, so
# his message is presented and he picks: failing closed.
PLAIN_WORDS = frozenset(('a', 'an', 'the', 'new', 'start', 'create', 'make', 'set', 'up', 'begin', 'please', 'project',
                         'repo', 'repository', 'called', 'named', 'name', 'under', 'with', 'using', 'as', 'for', 'my',
                         'me', 'it', 'identity', 'account'))


def unread_words(text, words):
    """The words of `text`, apart from each of `words` (as whole words, ignoring case), that are not PLAIN_WORDS."""
    if not isinstance(text, str):
        return []
    for word in sorted((w for w in words if _is_str(w)), key=len, reverse=True):
        text = re.sub(_LEFT_EDGE + re.escape(word) + _RIGHT_EDGE, ' ', text, flags=re.IGNORECASE)
    return [w for w in re.findall(r'[^\W_]+', text.casefold()) if w not in PLAIN_WORDS]


def identity_words(record):
    return [w for w in (record.get('id'), record.get('label')) if _is_str(w)]


def identities_named(text, records):
    """The ids of the configured identities (GI records) `text` names, by id or label, each as a whole word."""
    return sorted({r['id'] for r in records if any(names(text, word) for word in identity_words(r))})


def shown_entry(presented, identity):
    """What `presented` showed him for `identity`: its offered entry for it (the proposal itself once resolved),
    else None (he was not shown it)."""
    if not isinstance(presented, dict) or not _is_str(identity):
        return None
    if presented.get('offered') is None:
        return presented if presented.get('identity') == identity else None
    return next((e for e in presented['offered'] if isinstance(e, dict) and e.get('identity') == identity), None)


def visibility_of(entry):
    return ((entry or {}).get('remote') or {}).get('visibility')


# ---------------------------------------------------------------------------------------------
# The choices: the identity and the visibility are picked, never read (VELDO-0143 round 7)
# ---------------------------------------------------------------------------------------------

def picks(proposal):
    """{choice: (identity, visibility)} of every pick `proposal` offers (control_channel_presentation's pick kind,
    `accept <identity> <visibility>`): each offered identity with each visibility, but the pair it shows, which
    `accept` approves. An adoption keeps its remote's visibility (AS_ON_REMOTE), so it is offered as
    `accept <identity> adopt` (visibility None: the entry's), never with a visibility it cannot keep, and never in a
    shape a creation's pick folds into (R8-1)."""
    shown = proposal.get('identity') if isinstance(proposal, dict) else None
    shown_visibility = visibility_of(proposal) if shown else None
    found = {}
    for entry in (proposal.get('offered') if isinstance(proposal, dict) else None) or []:
        if entry.get('mode') == 'adopt':
            if entry.get('identity') != shown:
                found['%s %s %s' % (PICK, entry.get('identity'), ADOPT_WORD)] = (entry.get('identity'), None)
            continue
        for visibility in VISIBILITIES:
            if (entry.get('identity'), visibility) != (shown, shown_visibility):
                found['%s %s %s' % (PICK, entry.get('identity'), visibility)] = (entry.get('identity'), visibility)
    return found


def choices(proposal):
    """The choices the owner is offered for `proposal`, in order: accept when it shows an identity, every pick,
    return_for_elaboration and reject."""
    shown = isinstance(proposal, dict) and _is_str(proposal.get('identity'))
    return (['accept'] if shown else []) + list(picks(proposal)) + ['return_for_elaboration', 'reject']


def answered(presented, choice):
    """The resolved proposal his approving `choice` settles: `accept` what `presented` shows (only when it shows
    an identity), a pick the identity and visibility it names (an adoption's own, AS_ON_REMOTE); None for any other
    choice."""
    if choice == 'accept':
        return resolve(presented, presented['identity']) if _is_str(presented.get('identity')) else None
    pick = picks(presented).get(choice) if isinstance(choice, str) else None
    return None if pick is None else resolve(presented, *pick)


def correction_problems(presented, terms, rationale):
    """Why the corrected `terms` ({project, identity, visibility, mode, adoption}) are not what his correction may
    change (A CORRECTION CHANGES ONLY THE NAME AND THE OBJECTIVE), each invalid_input:correction:<field>."""
    problems = []
    negated = negates(rationale)
    same_name = terms.get('project') == presented.get('project')
    if not same_name and not (names(rationale, terms.get('project')) and not negated):
        problems.append('invalid_input:correction:project')
    shown = shown_entry(presented, presented.get('identity'))
    if shown is None or terms.get('identity') != presented.get('identity'):
        problems.append('invalid_input:correction:identity')
    if shown is None or terms.get('visibility') != visibility_of(shown):
        problems.append('invalid_input:correction:visibility')
    expected = shown.get('mode') if shown is not None and same_name else 'create'
    # A renamed adoption would be a creation whose visibility he never picked (R7-2): only a proposal decides the mode.
    renamed_adoption = shown is not None and not same_name and shown.get('mode') == 'adopt'
    if terms.get('mode') != expected or renamed_adoption or (expected == 'adopt' and 'adoption' in terms
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
        if chosen not in VISIBILITIES:
            raise Refused('invalid_input:visibility', 'a repository is created only as private or public')
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
    # The adoption path applies no visibility: the remote stays as it is on GitHub, and the entry says so (R7-2).
    remote = dict(remote, url=adoption['remote'], visibility=AS_ON_REMOTE)
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


def build(conn, domain, intake, document, *, repository, owner, templates=None, decision=None, shown=None,
          chosen=None):
    """The proposal for the inbox proposal `intake` (its record's data) from the PM's `document`: every
    configured identity offered, the one the document names shown. Raises Refused by name when the document
    is not one, names something that does not exist, or names a project that is taken (A NAME IS ONE PROJECT;
    `decision` is the one being built, never its own rival). `chosen` (identity, visibility), for a correction,
    builds the resolved proposal for that identity and visibility alone, whatever the document says. `shown`
    is the proposal he was shown, for a correction: an adoption shown for the same identity and name is kept
    as shown, its scaffold commit not laid again."""
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
    if chosen is not None and (chosen[0] not in identities or chosen[1] not in VISIBILITIES + (AS_ON_REMOTE,)):
        raise Refused('invalid_input:identity', 'not a configured identity and a visibility')
    found = intake_source(conn, intake['proposal_id'])
    if found is None:
        raise Refused('missing_evidence:intake_source', intake['proposal_id'])
    key, source, command = found
    name = document['project']
    records = [identities[chosen[0]]] if chosen else [identities[i] for i in sorted(identities)]
    visibility = chosen[1] if chosen else document['visibility']

    def entry(record):
        kept = shown_entry(shown, record['id']) if shown and shown.get('project') == name else None
        if kept is not None and kept.get('mode') == 'adopt':
            return dict({k: kept[k] for k in IDENTITY_FIELDS}, remote=dict(kept['remote'], visibility=AS_ON_REMOTE))
        return offered_entry(conn, domain, record, name, repository, owner, visibility, templates)
    entries = [entry(record) for record in records]
    proposal = {'project': name, 'repository': repository, 'owner': owner, 'identity': None, 'offered': None,
                'directory': None, 'mode': None, 'remote': None, 'adoption': None, 'objective': document['objective'],
                'charter': {'purpose': document['objective']}, 'authority_policy': json.loads(json.dumps(AUTHORITY_POLICY)),
                'team': default_team(conn), 'pipeline': default_pipeline(),
                'coordination_budget': dict(COORDINATION_BUDGET),
                'source': {'proposal_id': intake['proposal_id'], 'intake_source': key, 'intake_command': command,
                           'principal': source.get('principal'), 'source_kind': source.get('source_kind'),
                           'source_id': source.get('source_ref')}}
    if chosen:
        proposal.update(entries[0])
        return proposal
    proposal['offered'] = entries
    if document['identity']:
        proposal.update({k: v for k, v in next(e for e in entries if e['identity'] == document['identity']).items()
                         if k in IDENTITY_FIELDS})
    return proposal


def resolve(proposal, identity, visibility=None):
    """The proposal with `identity`, one of those it offered, chosen, and `visibility` when one is given (else
    the one shown for that identity)."""
    entry = next((e for e in proposal.get('offered') or [] if e['identity'] == identity), None)
    if entry is None:
        raise Refused('invalid_input:identity', 'not one of the offered identities')
    if visibility is not None and entry.get('mode') == 'adopt':
        raise Refused('invalid_input:visibility', 'an adoption keeps its remote\'s visibility')
    resolved = dict(proposal, offered=None)
    resolved.update({k: entry[k] for k in IDENTITY_FIELDS})
    if visibility is not None:
        resolved['remote'] = dict(entry['remote'], visibility=visibility)
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
        # A creation is private or public; an adoption's is its remote's, as it is (R7-2), never one it cannot keep.
        allowed = (AS_ON_REMOTE,) if proposal['mode'] == 'adopt' else VISIBILITIES
        if set(remote) != {'name', 'owner', 'url', 'visibility'} or remote.get('visibility') not in allowed:
            problems.append('invalid_input:proposal:remote')
        if (proposal['mode'] == 'adopt') != isinstance(proposal['adoption'], dict):
            problems.append('invalid_input:proposal:adoption')
    else:
        offered = proposal['offered'] if isinstance(proposal['offered'], list) else []
        ids = [e.get('identity') for e in offered if isinstance(e, dict)]
        if not offered or len(ids) != len(offered) or len(set(ids)) != len(ids) or not all(_is_str(i) for i in ids) \
                or (proposal['identity'] is not None and proposal['identity'] not in ids):
            problems.append('invalid_input:proposal:offered')
    return problems


def shown_visibility(visibility):
    """A visibility as the brief says it."""
    return 'visibility as it is on GitHub' if visibility == AS_ON_REMOTE else visibility


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
            entry.get('directory'), how, remote.get('url'), shown_visibility(remote.get('visibility')),
            remote.get('owner'))
    lines = ['Start project %s.' % _shown(p.get('project'))]
    offered = p.get('offered') if isinstance(p.get('offered'), list) else None
    if p.get('identity') and offered is None:
        lines += ['Identity: %s' % p['identity'], 'Where: %s' % where(p)]
    else:
        if p.get('identity'):
            lines.append('Identity: %s, %s. Answer accept to approve exactly that.'
                         % (p['identity'], shown_visibility((p.get('remote') or {}).get('visibility'))))
        else:
            lines.append('Identity: not named; pick one with a choice below.')
        lines.append('Each identity you can pick:')
        lines += ['  %s: %s' % (e.get('identity'), where(e)) for e in offered or []]
    team, pipeline = p.get('team') or {}, p.get('pipeline') or {}
    lines += ['First objective: %s' % _shown(p.get('objective')),
              'Team: default team revision %s (%s)' % (team.get('revision'), team.get('digest')),
              'Pipeline: %s version %s (%s)' % (pipeline.get('id'), pipeline.get('version'), pipeline.get('digest')),
              'Coordination budget: %s' % _shown(p.get('coordination_budget')),
              'Authority policy: %s' % _shown(p.get('authority_policy')),
              'Owner: %s. Repository id: %s.' % (_shown(p.get('owner')), _shown(p.get('repository'))),
              'Approving creates or adopts exactly this repository, activates the project and accepts its first '
              'objective.']
    if offered is not None:
        lines += ['To use another identity or visibility, answer with the choice that names both, '
                  '"%s <identity> <private or public>"; only a choice changes them, never your words. A directory '
                  'that is adopted keeps its repository as it is on GitHub, so its choice names the identity and adopt, '
                  '"%s <identity> %s". To change the name or the first objective, answer return_for_elaboration with '
                  'the change.' % (PICK, PICK, ADOPT_WORD)]
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
    # VELDO-0143 round 7: an identity read from his words binds only where nothing in them could mean otherwise;
    # any doubt presents it, and the identity is picked.
    if not isinstance(text, str) or not text.isascii():
        reasons.append('not_plain_text')
    if negates(text):
        reasons.append('negated')
    records = []
    if not isinstance(proposal, dict) or not proposal.get('identity'):
        reasons.append('identity_not_named')
    else:
        records = GI.records(conn, (intake or {}).get('domain'))
        said = identities_named(text, records)
        if proposal['identity'] not in said:
            reasons.append('identity_not_in_message')
        elif said != [proposal['identity']]:
            reasons.append('identity_not_alone')
    # VELDO-0143 round 8 (R7-1): unasked, a repository is only ever private. Neither the identity's default nor the
    # PM's document makes it public, and an adoption keeps a visibility no one here knows: a repository that is not
    # private always comes from a pick, and so does one his words say anything of.
    if not isinstance(proposal, dict) or visibility_of(proposal) != 'private':
        reasons.append('visibility_not_private')
    if says_visibility(text):
        reasons.append('visibility_in_message')
    # VELDO-0143 round 9 (R8-3): and only when every other word of it is one the rule has read.
    shown = next((r for r in records if r['id'] == proposal['identity']), {}) if records else {}
    if unread_words(text, [proposal.get('project') if isinstance(proposal, dict) else None] + identity_words(shown)):
        reasons.append('words_not_read')
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
    if data.get('choices') != choices(presented):
        raise Refused('no_settled_decision:choices', 'the owner was offered other choices than this proposal\'s')
    if s.get('principals') != [owner] or data.get('owner') != owner:
        raise Refused('no_settled_decision:not_owner', 'the settled answer is not the factory owner\'s')
    ruling = s.get('ruling')
    if e.get('type') != EFFECTS.get(ruling):
        raise Refused('no_settled_decision:not_approved:%s' % ruling, 'the owner did not approve or correct it')
    if path == 'answer':
        expected = answered(presented, s.get('choice')) if ruling == 'approve' else None
        if expected is None or e.get('proposal') != presented or e.get('choice') != s.get('choice'):
            raise Refused('no_settled_decision:answer', 'his answer does not settle this proposal')
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
        problems = correction_problems(presented, proposal_terms(proposal), s.get('rationale'))
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
                proposal = resolve(proposal, proposal['identity'])
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
            try:
                request = self._present(decision, proposal, owner, alias, deadline)
            except NotPresented as error:
                return dict(self._observe('propose', 'failed', error.code, project=proposal['project'], **about),
                            ok=False, reason=error.code)
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
        Returns the request id; raises NotPresented when the presenter refuses it for good (NOT_PRESENTABLE), the
        decision already failed by that name."""
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
                                                      brief=brief(proposal), choices=choices(proposal),
                                                      subject=terms['subject'])))
        request = self.assignment.assignment_id(self.ids['repository_uuid'], alias)
        if self.inbox.read(request) is None:
            raise Refused('unavailable_service:request')
        self.presenter.frame(self._signed(operation='frame', alias=alias, request_version=1,
                                          risk_statement='Approving creates a repository under the identity and with '
                                                         'the visibility you choose and activates the project; it is '
                                                         'removed only by hand.',
                                          command_id=alias + '-frame', nonce=alias + '-frame'))
        shown = self.presenter.present(request) or {}
        if shown.get('outcome') == 'refused' and shown.get('reason') in NOT_PRESENTABLE:
            # Nothing was presented. The decision fails by name before its request is canceled (R8-2), so no crash
            # leaves it presenting over a canceled request, which a resume would write presented to no one; a crash
            # before the cancel leaves a failed decision whose request resume cancels (_cancel_unpresented).
            self._fail(decision, 'presented', 'invalid_input:' + shown['reason'])
            self._cancel(alias)
            raise NotPresented('invalid_input:' + shown['reason'], request)
        return request

    def _cancel(self, alias):
        """Cancel the request under `alias` that he could never answer (the same signed command each time)."""
        self.inbox.apply(self._signed(operation='cancel', alias=alias, request_version=1, command_id=alias + '-cancel',
                                      nonce=alias + '-cancel'))

    def _cancel_unpresented(self, record):
        """The request of a decision failed as not presentable, canceled if it is still open. Returns whether it
        was canceled now."""
        alias = (record.get('presentation') or {}).get('alias')
        if record['state'] != 'failed' or not _is_str(alias) or record.get('reason') not in [
                'invalid_input:' + r for r in NOT_PRESENTABLE] or None in (self.inbox, self.assignment):
            return False
        request = self.assignment.assignment_id(self.ids['repository_uuid'], alias)
        state = ((self.inbox.read(request) or {}).get('data') or {}).get('state')
        if state is None or self.assignment.CATEGORIES.get(state) != 'pending':
            return False
        self._cancel(alias)
        return True

    def resume(self):
        """Each decision whose presentation did not finish (PRESENTED ONCE, EVEN ACROSS A CRASH): presented now
        from its record, then `presented`. Returns the observations made."""
        made = []
        for record in records(self.conn):
            about = dict(decision=record['id'], proposal_id=record['proposal_id'])
            try:
                if self._cancel_unpresented(record):
                    made.append(self._observe('resume', 'canceled', record.get('reason'), **about))
            except (Refused, self.store.StoreRefused) as error:
                made.append(self._observe('resume', 'refused', error.code, **about))
            if record['state'] != 'presenting':
                continue
            shown, presentation = record['presented'], record.get('presentation') or {}
            try:
                request = self._present(record['id'], shown, shown['owner'], presentation['alias'],
                                        presentation['deadline'])
                self.write(record['id'], 'presented', step='presented', request=request)
                made.append(self._observe('resume', 'presented', request=request, **about))
            except NotPresented as error:
                made.append(self._observe('resume', 'failed', error.code, **about))
            except (Refused, self.store.StoreRefused) as error:
                made.append(self._observe('resume', 'refused', error.code, **about))
        return made

    def apply_settled(self):
        """Each presented decision whose request is settled: the choice he picked settles it (accept as shown, a
        pick with the identity and visibility it names), a return hands his words to the factory PM, a reject ends
        it. No question is ever sent here. Returns the observations made."""
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
                if ruling == 'approve':
                    proposal = answered(presented, s.get('choice'))
                    if proposal is None:
                        # A choice this proposal never offered: nothing is chosen for him.
                        self._fail(record['id'], 'answer', 'invalid_input:answer:choice')
                        made.append(self._observe('answer', 'failed', 'invalid_input:answer:choice', **about))
                        continue
                    self.write(record['id'], 'settled', step='answer', path='answer', proposal=proposal)
                    made.append(self._observe('answer', 'settled', path='answer', identity=proposal['identity'],
                                              choice=s.get('choice'), **about))
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
        second presentation, when it changes only the name and the objective (A CORRECTION CHANGES ONLY THE NAME
        AND THE OBJECTIVE); anything else fails it by name."""
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
            if document['identity'] is not None and document['identity'] not in configured:
                raise Refused('invalid_input:document:identity', 'no configured identity is named so')
            # Judged before anything is built, so nothing is laid for terms he did not say or see. The identity
            # and the visibility are the ones he was shown; a document that sets others is refused by name.
            identity = document['identity'] or presented.get('identity')
            shown = shown_entry(presented, presented.get('identity'))
            terms = {'project': document['project'], 'identity': identity,
                     'visibility': document['visibility'] or visibility_of(shown), 'mode': 'create'}
            if identity in configured:
                directory = os.path.join(configured[identity]['projects_root'], document['project'])
                terms['mode'] = 'adopt' if directory_state(directory) == 'repository' else 'create'
            problems = correction_problems(presented, terms, rationale)
            if not problems and name_taken(self.conn, document['project'], decision):
                problems = ['stale_subject:project_exists']
            failure = problems[0] if problems else None
            proposal = None
            if failure is None:
                proposal = build(self.conn, self.ids['domain_uuid'], intake, document,
                                 repository=presented['repository'], owner=presented['owner'],
                                 templates=self.templates, decision=decision, shown=presented,
                                 chosen=(terms['identity'], terms['visibility']))
                problems = correction_problems(presented, proposal_terms(proposal), rationale)
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
