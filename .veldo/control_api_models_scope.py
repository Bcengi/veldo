"""Project resolution for the API's registered kinds (VELDO-0164).

Unknown or unresolved kinds are universal-only. References are read in the authority's
read transaction; journal changes use their committed data and the same reference rules.
No withheld identity is logged or returned, including in redaction and integrity problems.

VELDO-0178: a conversation has no project; its scope is its owner. A conversation's records (the conversation,
its turns, the messages sent in it, the answers kept under the owner's messages and a flag delivered to it) and the
dispatch of one of its turns are visible to the conversation's owner alone, whatever the reader's scope, the
universal one included; anyone else is withheld them as `conversation_owner`.
"""
import copy
import json


def field(data, path):
    for part in path.split('.'):
        data = data.get(part) if isinstance(data, dict) else None
    return data


# VELDO-0178: the kinds a conversation's records are kept as (control_conversation's KIND, TURN_KIND, SENT_KIND,
# ANSWER_KIND and FLAG_KIND), each naming its conversation; a conversation turn's dispatch names it as its unit.
CONVERSATION_KINDS = ('conversation', 'conversation_turn', 'conversation_message', 'conversation_answer',
                      'conversation_flag')
OWNER = 'conversation_owner'


def conversation_of(conn, kind, data):
    """The conversation a record belongs to, or None for a record of no conversation."""
    if not isinstance(data, dict):
        return None
    if kind == 'conversation':
        return data.get('id') if isinstance(data.get('id'), str) else ''
    if kind in CONVERSATION_KINDS:
        found = data.get('conversation')
        # A flag delivered to no conversation (undelivered) belongs to none; every other record names one.
        return found if isinstance(found, str) else (None if kind == 'conversation_flag' else '')
    if kind == 'dispatch_active' and isinstance(data.get('dispatch_id'), str):
        row = conn.execute('SELECT kind, data FROM entities WHERE id=?', ('dispatch:' + data['dispatch_id'],)).fetchone()
        return conversation_of(conn, row[0], json.loads(row[1])) if row and row[0] == 'dispatch' else None
    if kind == 'dispatch':
        contract = data.get('contract') if isinstance(data.get('contract'), dict) else {}
        if contract.get('subject_kind') == 'conversation':
            return contract.get('unit') if isinstance(contract.get('unit'), str) else ''
    return None


def conversation_owner(conn, identity):
    """The owner of a conversation, or None for an unknown one."""
    if not isinstance(identity, str) or not identity:
        return None
    row = conn.execute('SELECT kind, data FROM entities WHERE id=?', ('conversation:' + identity,)).fetchone()
    return json.loads(row[1]).get('owner') if row and row[0] == 'conversation' else None


class ReaderScope:
    def __init__(self, conn, membership, scope, rules, principal=None):
        self.conn, self.membership, self.scope, self.rules = conn, membership, scope, rules
        self.principal = principal
        self.withheld = {'out_of_scope': 0, 'no_project': 0, OWNER: 0}
        self.records = {'out_of_scope': 0, 'no_project': 0, OWNER: 0}

    @property
    def universal(self):
        return self.membership.scope_covers(self.scope, '*')

    def reference(self, identity, seen):
        if not isinstance(identity, str) or identity in seen:
            return None
        row = self.conn.execute('SELECT kind, data FROM entities WHERE id=?', (identity,)).fetchone()
        return self.projects(identity, row[0], json.loads(row[1]), seen | {identity}) if row else None

    def projects(self, identity, kind, data, seen=frozenset()):
        rule = self.rules.get(kind)
        if not rule:
            return None
        method = rule[0]
        if method == 'field':
            return field(data, rule[1])
        if method == 'reference':
            return self.reference(field(data, rule[1]), seen)
        if method == 'intake':
            # An inbox proposal may name the factory as its holding area, not a routed project.
            return None if data.get('proposal') == 'inbox' else data.get('project')
        if method == 'repository':
            repository = field(data, rule[1])
            projects = [json.loads(row[0]) for row in self.conn.execute(
                "SELECT data FROM entities WHERE kind='project'")]
            names = sorted({p['name'] for p in projects if repository
                            and p.get('execution_repository') == repository and p.get('name')})
            # A repository-wide record can contain every project in that repository.
            return names or None
        if method == 'request':
            scopes = []
            for rid, text in self.conn.execute("SELECT id, data FROM entities WHERE kind='assignment'"):
                request = json.loads(text)
                if field(request, 'subject.ref') == identity:
                    projects = self.projects(rid, 'assignment', request, seen | {identity})
                    if not projects:
                        return None
                    scopes.extend([projects] if isinstance(projects, str) else projects)
            return scopes or None
        if method == 'reservation':
            if data.get('type') == 'policy':
                if data.get('scope') == 'project':
                    return data.get('subject')
                if data.get('scope') == 'unit':
                    return self.reference(data.get('subject'), seen)
                return None
            return field(data, 'context.project')
        return None

    def project_data(self, kind, data):
        """Project metadata in a visible intake record follows the reader's scope too."""
        if self.universal or kind not in ('intake_proposal', 'intake_question'):
            return data
        served = copy.deepcopy(data)
        def covered(project):
            return isinstance(project, str) and self.membership.scope_covers(self.scope, project)
        # Shared ticket keys are prefixes, not project names. Keep a shared prefix only
        # when at least two visible projects share it, so it cannot disclose a hidden peer.
        prefixes = {}
        for project in field(data, 'context.projects') or []:
            if isinstance(project, dict) and covered(project.get('id')):
                for prefix in set(p.casefold() for p in project.get('ticket_key_prefixes', []) if isinstance(p, str)):
                    prefixes[prefix] = prefixes.get(prefix, 0) + 1
        def walk(value):
            if isinstance(value, dict):
                for key, item in list(value.items()):
                    if key == 'projects' and isinstance(item, list):
                        value[key] = [p for p in item if isinstance(p, dict) and covered(p.get('id'))]
                    elif key in ('candidates', 'hints') and isinstance(item, list):
                        value[key] = [p for p in item if covered(p)]
                    elif key == 'shared_ticket_keys' and isinstance(item, list):
                        value[key] = [p for p in item if isinstance(p, str) and prefixes.get(p.casefold(), 0) > 1]
                    elif key == 'project_versions' and isinstance(item, dict):
                        value[key] = {p:v for p,v in item.items() if p.startswith('project:')
                                      and covered(p[len('project:'):])}
                    else:
                        walk(item)
            elif isinstance(value, list):
                for item in value:
                    walk(item)
        walk(served)
        return served

    def owned(self, kind, data):
        """None for a record of no conversation, else whether the reader is its conversation's owner."""
        conversation = conversation_of(self.conn, kind, data)
        if conversation is None:
            return None
        if kind == 'conversation':
            owner = data.get('owner')
        else:
            owner = conversation_owner(self.conn, conversation)
        return isinstance(self.principal, str) and owner == self.principal

    def reason(self, identity, kind, data):
        owned = self.owned(kind, data)
        if owned is not None:
            return None if owned else OWNER
        if self.universal:
            return None
        if self.rules.get(kind) == ('shared',):
            return None
        projects = self.projects(identity, kind, data)
        if not projects:
            return 'no_project'
        return None if self.membership.scope_covers(self.scope, projects) else 'out_of_scope'

    def visible(self, identity, kind, data):
        reason = self.reason(identity, kind, data)
        if reason:
            self.withheld[reason] += 1
        return reason is None
