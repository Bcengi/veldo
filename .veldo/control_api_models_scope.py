"""Project resolution for the API's registered kinds (VELDO-0164).

Unknown or unresolved kinds are universal-only. References are read in the authority's
read transaction; journal changes use their committed data and the same reference rules.
No withheld identity is logged or returned, including in redaction and integrity problems.
"""
import copy
import json


def field(data, path):
    for part in path.split('.'):
        data = data.get(part) if isinstance(data, dict) else None
    return data


class ReaderScope:
    def __init__(self, conn, membership, scope, rules):
        self.conn, self.membership, self.scope, self.rules = conn, membership, scope, rules
        self.withheld = {'out_of_scope': 0, 'no_project': 0}
        self.records = {'out_of_scope': 0, 'no_project': 0}

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
        def walk(value):
            if isinstance(value, dict):
                for key, item in list(value.items()):
                    if key == 'projects' and isinstance(item, list):
                        value[key] = [p for p in item if isinstance(p, dict) and covered(p.get('id'))]
                    elif key in ('candidates', 'hints', 'shared_ticket_keys') and isinstance(item, list):
                        value[key] = [p for p in item if covered(p)]
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

    def reason(self, identity, kind, data):
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
