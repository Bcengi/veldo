"""THE ADMISSION REQUEST CONTRACT (VELDO-0079, PLAN-0019 W64, R09, R12): what grooming presents, what it
binds and when the owner's own message admits instead.

WHAT THIS MODULE IS. Pure functions over plain records, shared by the grooming service
(control_grooming.py, the one writer of admission requests) and the backlog service (control_backlog.py,
the one writer of backlog items), so the request is built, bound, shown and routed by one implementation.
It writes nothing; read_specifications is its one reader of files, the specification files of the
checkout both services are given, and requests and history its one reader of the store (read only), the
decision requests grooming opened, so both services judge an item's history the same way.

THE REQUEST. An admission request is the complete authorization material for one backlog item at one
decomposition revision (R09), in FIELDS order:

  class, lane         the item's work class and the lane admission_contract.CLASS_POLICY gives it
  outcome             the accepted objective's observable outcome, its accepted revision and bound digest
  scope, exclusions   the item's scope, and what the project manager states is left out of it
  priority            the proposed rank (DEFAULT_PRIORITY when none is proposed)
  ceiling             the coordination ceiling proposed for the work, each cap within the project's budget
  policy              the project's charter revision and digest and the digest of its authority policy
  specifications      each unit's primary specification and the digest of its file's bytes
  protected_paths     every path those specifications protect
  release_authority   the most any unit of the item may do: land its tested tree in the project's
                      execution repository (VELDO-0057); no other release action has an admitted adapter
  expiry              when the request lapses; no ruling on it is applied after that time
  evidence            the objective's evidence requirements and how the objective was accepted
  decomposition       the item's decomposition revision, digest and units
  alternatives        the alternatives the project manager considered
  questions           the questions the project manager asks the owner

Every field is rendered in `brief`, the exact text the owner is shown, and bound by `binding`: the
decomposition by its digest (which covers every unit entry), every other field by its value. The request
digest is the digest of the item, the request revision and that binding, so a revision with equal
content is a different request, and a settled ruling names it by `target` (kind, record, digest).

WHEN HIS MESSAGE ADMITS (`route`). The owner's own message that proposed the objective (VELDO-0150's
own_message acceptance) admits work under it at DEFAULT_PRIORITY with nothing presented when the request
asks for admission, raises no question and proposes the default priority, and its current revision was
written by the project's owner or its project manager, and nothing about the item was ever put to him.
Anything else is presented: an objective accepted by an answer, a question, another priority, another
author, a prioritization of units appended after admission (his message predates them), and an item any
of whose requests was opened to the owner (`presented`), since his answer or his pending decision governs
it from then on, whatever a later revision proposes. The reasons are named.

HISTORY (`history`). Every decision request grooming opens for an admission request has its own alias
(`alias`), so what the owner was asked, and what he ruled, is read from the store and not from the
current revision. A settled ruling other than an approval that is not yet applied to the item (`held`)
holds the item: no later revision is proposed or presented over it, so his reject or return is applied
as he gave it. A settled approval of an earlier revision authorizes nothing later (its digest binds it).

STALE BINDING (`live_problems`). A request revision binds what the store says now: the item's class,
scope and decomposition, the objective's accepted outcome and acceptance, the project's policy and
execution repository. A field that differs from the live records is named, so a ruling on an earlier
revision never applies to changed work. Standard library only.
"""
import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = 'veldo.admission_request/v1'
KIND = 'admission_request'
ID_PREFIX = 'admission-request:'
TARGET_KIND = 'admission_request'
FIELDS = ('class', 'lane', 'outcome', 'scope', 'exclusions', 'priority', 'ceiling', 'policy', 'specifications',
          'protected_paths', 'release_authority', 'expiry', 'evidence', 'decomposition', 'alternatives', 'questions')
# Where each field comes from: the store's records, the specification files, or the project manager.
STORE_FIELDS = ('class', 'lane', 'outcome', 'scope', 'policy', 'release_authority', 'evidence', 'decomposition')
WORKSPACE_FIELDS = ('specifications', 'protected_paths')
PROPOSED_FIELDS = ('exclusions', 'priority', 'ceiling', 'expiry', 'alternatives', 'questions')
# The priority vocabulary: rank 1 runs first. A project's work is admitted at DEFAULT_PRIORITY by the
# owner's own message; any other rank is his answer's to give.
PRIORITY_RANKS = (1, 2, 3, 4, 5)
DEFAULT_PRIORITY = {'rank': 3}
RELEASE_AUTHORITY = 'land'
EXPIRY_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
ADMISSION, PRIORITY = 'admission', 'priority'
OWN_MESSAGE = 'own_message'


def _organ(name):
    spec = importlib.util.spec_from_file_location('grooming_request_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


AD = _organ('admission_contract')
Y = _organ('yamlish')
AS = _organ('control_assignment')
PRESENTED = 'presented'
REQUEST_KIND = 'assignment'


def _is_str(v):
    return isinstance(v, str) and v.strip() != ''


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


def digest(value):
    return 'sha256:' + hashlib.sha256(_canonical(value)).hexdigest()


def request_id(item):
    """The one admission request record of backlog item `item`; its revisions are kept inside it."""
    return ID_PREFIX + hashlib.sha256(_canonical(['admission-request', item])).hexdigest()[:32]


def alias(rid, touchpoint, round_):
    """The inbox alias of the `round_`-th decision request grooming opens for `touchpoint` of admission
    request `rid`."""
    return 'groom-%s-%s-%d' % (rid[len(ID_PREFIX):][:24], touchpoint, round_)


def requests(conn, repository, rid, touchpoint):
    """[(alias, request id, assignment data)] of every request grooming opened for `touchpoint` of
    admission request `rid` in `repository`, in order, read on `conn`."""
    found, n = [], 1
    while True:
        name = alias(rid, touchpoint, n)
        aid = AS.assignment_id(repository, name)
        row = conn.execute('SELECT kind, data FROM entities WHERE id=?', (aid,)).fetchone()
        if row is None or row[0] != REQUEST_KIND:
            return found
        found.append((name, aid, json.loads(row[1])))
        n += 1


def history(conn, repository, rid, applied):
    """(opened, unapplied) of admission request `rid`: the id of every request grooming opened to the owner
    for it, and each settled ruling among them not in `applied` (the item's applied requests), as
    {'touchpoint', 'request', 'ruling'}."""
    opened, unapplied = [], []
    for touchpoint in (ADMISSION, PRIORITY):
        for _name, aid, data in requests(conn, repository, rid, touchpoint):
            opened.append(aid)
            reference = data.get('settlement') if isinstance(data.get('settlement'), dict) else {}
            if data.get('state') == 'SATISFIED' and _is_str(reference.get('ruling')) and aid not in (applied or []):
                unapplied.append({'touchpoint': touchpoint, 'request': aid, 'ruling': reference['ruling']})
    return opened, unapplied


def held(unapplied):
    """The settled rulings in `unapplied` that hold the item until they are applied: all but approvals."""
    return [u for u in unapplied if u['ruling'] != 'approve']


# Building the request.

def derived(item, objective, project):
    """The STORE_FIELDS of a request for `item`, from the item, its objective and its project as they are."""
    bound = objective.get('bound') or {}
    acceptance = objective.get('acceptance') if isinstance(objective.get('acceptance'), dict) else {}
    if acceptance.get('path') == OWN_MESSAGE:
        accepted = {'path': OWN_MESSAGE, 'intake_command': acceptance.get('intake_command'),
                    'source_kind': acceptance.get('source_kind'), 'source_id': acceptance.get('source_id')}
    else:
        accepted = {'path': 'answer', 'request_id': acceptance.get('request_id'),
                    'settlement_id': acceptance.get('settlement_id')}
    cls = item.get('work_class')
    return {
        'class': cls,
        'lane': (AD.CLASS_POLICY.get(cls) or {}).get('lane'),
        'outcome': {'objective': objective.get('uuid'), 'accepted_revision': objective.get('accepted_revision'),
                    'bound_digest': objective.get('bound_digest'), 'text': bound.get('outcome')},
        'scope': list(item.get('scope') or []),
        'policy': {'project': project.get('name'), 'charter_revision': project.get('charter_revision'),
                   'charter_digest': project.get('charter_digest'),
                   'authority_policy_digest': digest(project.get('authority_policy'))},
        'release_authority': {'maximum': RELEASE_AUTHORITY, 'repository': project.get('execution_repository')},
        'evidence': {'requirements': [dict(e) for e in bound.get('evidence_requirements') or [] if isinstance(e, dict)],
                     'acceptance': accepted},
        'decomposition': {'revision': item.get('decomposition_revision'), 'digest': item.get('decomposition_digest'),
                          'units': [{'unit': u.get('unit'), 'specification': u.get('specification'),
                                     'scope': list(u.get('scope') or [])} for u in item.get('decomposition') or []]},
    }


def specifications(item):
    """The distinct primary specifications of the item's decomposition, in order."""
    return list(dict.fromkeys(u.get('specification') for u in item.get('decomposition') or []))


def specified(item, found):
    """The WORKSPACE_FIELDS from `found`, {specification: {'digest', 'protected_paths'}} as read from the
    files. Returns (fields, problems): a specification with no readable file is named."""
    wanted = specifications(item)
    problems = ['missing_evidence:specification:%s' % s for s in wanted if not isinstance(found.get(s), dict)]
    specs = [{'id': s, 'digest': found[s]['digest']} for s in wanted if isinstance(found.get(s), dict)]
    paths = sorted({p for s in wanted if isinstance(found.get(s), dict) for p in found[s].get('protected_paths') or []})
    return {'specifications': specs, 'protected_paths': paths}, problems


def read_specifications(workspace, wanted):
    """{specification: {'digest', 'protected_paths'}} for each id in `wanted` whose file under
    `workspace`/specs is readable and names that id in its front matter. None or an absent file gives none."""
    found = {}
    if workspace is None:
        return found
    for spec in wanted:
        if not _is_str(spec) or '/' in spec or spec.startswith('.'):
            continue
        for path in sorted((Path(workspace) / 'specs').glob(spec + '-*.md')) + [Path(workspace) / 'specs' / (spec + '.md')]:
            try:
                data = path.read_bytes()
            except OSError:
                continue
            match = Y.front_matter_match(data.decode('utf-8', 'replace'))
            try:
                front = Y.parse(match.group(1)) if match else None
            except ValueError:
                front = None
            if isinstance(front, dict) and front.get('id') == spec:
                paths = front.get('protected_paths') if isinstance(front.get('protected_paths'), list) else []
                found[spec] = {'digest': 'sha256:' + hashlib.sha256(data).hexdigest(),
                               'protected_paths': [str(x) for x in paths]}
                break
    return found


def _strings(value):
    return isinstance(value, list) and all(_is_str(v) for v in value) and len(set(value)) == len(value)


def proposal_problems(proposal, project, now):
    """Why the project manager's proposal is not one this service records, by name."""
    if not isinstance(proposal, dict) or set(proposal) - set(PROPOSED_FIELDS):
        return ['invalid_input:proposal']
    problems = [f for f in ('ceiling', 'expiry') if f not in proposal]
    problems = ['missing_field:' + f for f in problems]
    for field in ('exclusions', 'alternatives'):
        if not _strings(proposal.get(field, [])):
            problems.append('invalid_input:' + field)
    questions = proposal.get('questions', [])
    if (not isinstance(questions, list) or not all(isinstance(q, dict) and set(q) == {'id', 'text'} and _is_str(q['id'])
                                                    and _is_str(q['text']) for q in questions)
            or len({q['id'] for q in questions}) != len(questions)):
        problems.append('invalid_input:questions')
    priority = proposal.get('priority', DEFAULT_PRIORITY)
    if not isinstance(priority, dict) or set(priority) != {'rank'} or priority.get('rank') not in PRIORITY_RANKS \
            or type(priority.get('rank')) is not int:
        problems.append('invalid_input:priority')
    budget = project.get('coordination_budget') if isinstance(project.get('coordination_budget'), dict) else {}
    ceiling = proposal.get('ceiling')
    if 'ceiling' in proposal:
        if not isinstance(ceiling, dict) or not ceiling or set(ceiling) - set(budget):
            problems.append('invalid_input:ceiling')
        else:
            for unit in sorted(ceiling):
                cap, value = budget.get(unit), ceiling[unit]
                if type(value) is not int or value <= 0:
                    problems.append('invalid_input:ceiling')
                elif not isinstance(cap, (int, float)) or value > cap:
                    problems.append('out_of_budget:' + unit)
    if 'expiry' in proposal:
        at = expiry_time(proposal.get('expiry'))
        if at is None:
            problems.append('invalid_input:expiry')
        elif at <= now:
            problems.append('stale_subject:expired')
    return problems


def expiry_time(value):
    try:
        return datetime.strptime(value, EXPIRY_FORMAT).replace(tzinfo=timezone.utc).timestamp()
    except (TypeError, ValueError):
        return None


def content(store_fields, workspace_fields, proposal):
    """The request's fields in FIELDS order."""
    proposed = {'exclusions': list(proposal.get('exclusions', [])), 'priority': dict(proposal.get('priority', DEFAULT_PRIORITY)),
                'ceiling': dict(proposal['ceiling']), 'expiry': proposal['expiry'],
                'alternatives': list(proposal.get('alternatives', [])),
                'questions': [dict(q) for q in proposal.get('questions', [])]}
    merged = dict(store_fields, **workspace_fields, **proposed)
    return {k: merged[k] for k in FIELDS}


# Binding and showing it.

def binding(fields):
    """What a request binds of its fields: every field by its value, the decomposition by its digest."""
    bound = {k: fields.get(k) for k in FIELDS}
    bound['decomposition'] = (fields.get('decomposition') or {}).get('digest')
    return bound


def request_digest(item, revision, fields):
    return digest({'item': item, 'revision': revision, 'binding': binding(fields)})


def target(record):
    """The settlement terms target a ruling on the request's current revision names."""
    return {'kind': TARGET_KIND, 'ref': record['uuid'], 'digest': record['digest']}


def _list(values):
    return '; '.join(values) if values else 'none'


def brief(record, touchpoint):
    """Exactly what the owner is shown for `touchpoint` (admission or priority) of the current revision."""
    c = record['content']
    ask = ('Admit backlog item %s' if touchpoint == ADMISSION else 'Prioritize backlog item %s') % record['item']
    evidence = c['evidence']
    accepted = evidence['acceptance']
    how = ('by your own message (intake command %s)' % accepted.get('intake_command') if accepted.get('path') == OWN_MESSAGE
           else 'by your answer (settlement %s)' % accepted.get('settlement_id'))
    lines = [
        '%s, admission request %s revision %d, in project %s.' % (ask, record['uuid'], record['revision'], record['project']),
        'Title: %s.' % record['title'],
        'Class: %s. Lane: %s.' % (c['class'], c['lane']),
        'Outcome: %s (objective %s, accepted revision %s).' % (c['outcome']['text'], c['outcome']['objective'],
                                                              c['outcome']['accepted_revision']),
        'Scope: %s. Exclusions: %s.' % (_list(c['scope']), _list(c['exclusions'])),
        'Priority: rank %d (the default is %d; 1 runs first).' % (c['priority']['rank'], DEFAULT_PRIORITY['rank']),
        'Ceiling: %s.' % ', '.join('%s=%s' % (k, c['ceiling'][k]) for k in sorted(c['ceiling'])),
        'Policy: charter revision %s (%s), authority policy %s.' % (c['policy']['charter_revision'],
                                                                    c['policy']['charter_digest'],
                                                                    c['policy']['authority_policy_digest']),
        'Specifications: %s.' % _list(['%s %s' % (s['id'], s['digest']) for s in c['specifications']]),
        'Protected paths: %s.' % _list(c['protected_paths']),
        'Release authority: at most %s in repository %s.' % (c['release_authority']['maximum'],
                                                             c['release_authority']['repository']),
        'Expires: %s.' % c['expiry'],
        'Evidence: %s; objective accepted %s.' % (_list(['%s (%s)' % (e['id'], e['kind']) for e in evidence['requirements']]),
                                                  how),
        'Decomposition: revision %s, digest %s, units %s.' % (
            c['decomposition']['revision'], c['decomposition']['digest'],
            _list(['%s (%s, scope %s)' % (u['unit'], u['specification'], ', '.join(u['scope']))
                   for u in c['decomposition']['units']])),
        'Alternatives: %s.' % _list(c['alternatives']),
        'Questions: %s.' % _list(['%s - %s' % (q['id'], q['text']) for q in c['questions']]),
        ('Admission and priority are separate decisions: admitting runs nothing until the work is prioritized.'
         if touchpoint == ADMISSION else
         'Admission and priority are separate decisions: approving makes the listed units executable at this rank.'),
    ]
    return '\n'.join(lines)


# What the store says now, and when his message admits.

def live_problems(fields, item, objective, project):
    """The STORE_FIELDS in which the request's binding differs from the live records, as
    stale_subject:<field>."""
    held, now = binding(fields), binding(dict(fields, **derived(item, objective, project)))
    return ['stale_subject:' + f for f in STORE_FIELDS if held[f] != now[f]]


def route(fields, touchpoints, objective, owner, managers, author, opened):
    """(path, reasons): OWN_MESSAGE when the owner's own message admits this revision at the default
    priority, else 'present' with every reason it is presented. `opened` is history's first answer: the
    requests grooming ever opened to the owner for this item."""
    reasons = []
    acceptance = objective.get('acceptance') if isinstance(objective.get('acceptance'), dict) else {}
    if acceptance.get('path') != OWN_MESSAGE or objective.get('accepted_revision') is None:
        reasons.append('objective_by_answer')
    if ADMISSION not in touchpoints:
        reasons.append('fresh_priority')
    if fields.get('questions'):
        reasons.append('question')
    if fields.get('priority') != DEFAULT_PRIORITY:
        reasons.append('priority')
    if author != owner and author not in managers:
        reasons.append('author')
    if opened:
        reasons.append(PRESENTED)
    return (OWN_MESSAGE if not reasons else 'present'), reasons
