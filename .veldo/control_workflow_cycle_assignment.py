"""Assignment reads for ordinary station eligibility (VELDO-0088).

Keep this seam free of command owners and workspace parsers: eligibility may
execute a parser only inside its held architecture snapshot. Read authority on
every decision; only the helper code is loaded once, never the accepted records.
"""
import json
import time


def assignments(conn, unit=None):
    """Every team assignment (of `unit` when named), on any connection."""
    rows = conn.execute('SELECT id, version, data FROM entities WHERE kind=? ORDER BY id', ('team_assignment',))
    found = [dict(json.loads(data), id=eid, version=version) for eid, version, data in rows]
    return [a for a in found if unit is None or a.get('unit') == unit]


def assigned(conn, unit):
    records = assignments(conn, unit)
    return max(records, key=lambda r: (r['at'], r['id'])) if records else None


def assignment_inputs(gate, unit, data):
    """Bind the assignment and its current authority to the ordinary station ticket."""
    assignment = assigned(gate.conn, unit)
    if not assignment:
        return {}
    identities = {'team_assignment': assignment['id'], 'assigned_team': 'team:' + data['project']}
    identities.update({'assigned_member/' + who: who
                       for who in [assignment['builder'], *assignment['reviewers']]})
    return {name: gate._entity(identity) for name, identity in identities.items()}


def assignment_problems(gate, unit, inputs, context, membership):
    assignment = gate._data(inputs.get('team_assignment')) or {}
    data = gate._data(inputs['unit'])
    team = gate._data(inputs.get('assigned_team')) or {}
    if (assignment.get('subject') != dict(unit=unit, revision=data.get('revision'),
                                         scope_digest=data.get('scope_digest'))
            or assignment.get('project') != data.get('project')
            or assignment.get('team', {}).get('revision') != team.get('revision')):
        return ['stale_subject:team_assignment']
    if (context or {}).get('holder') != assignment.get('builder'):
        return ['missing_authority:assigned_builder']
    reviewer = (context or {}).get('reviewer')
    if reviewer and (reviewer not in assignment['reviewers'] or reviewer == assignment['builder']):
        return ['reviewer_not_independent']
    for who in [assignment['builder'], *assignment['reviewers']]:
        member = gate._data(inputs.get('assigned_member/' + who))
        if (not member or not membership.AC.active_member(dict(member, principal=who), time.time())[0]
                or not membership.scope_covers(member.get('scope'), [data['project']])):
            return ['missing_authority:assigned_member']
    return []


