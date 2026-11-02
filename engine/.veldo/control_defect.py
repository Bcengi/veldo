"""Ordinary defect evidence, consumed by the normal backlog and grooming writers.

These are reports, not observations by a trusted reproduction service. Neither a
severity nor a reproduction assertion supplies admission, priority or review.
"""
import copy
import json

SCOPE_CHANGES = ('contract', 'criterion', 'public_behavior', 'interface', 'data_model',
                 'dependency_policy', 'protected_scope', 'release_policy', 'compatibility')


def origin(conn, proposal_id, objectives):
    """Follow only intake's recorded routing links back to its proposing source.

    Plain Telegram prose can first reach the factory inbox. The PM's existing
    project route retains the same sources and records both ends of that link.
    Return the records read so the backlog command pins them in its read set.
    """
    reads = []
    while isinstance(proposal_id, str) and proposal_id not in reads:
        reads.append(proposal_id)
        row = conn.execute('SELECT kind, data FROM entities WHERE id=?', (proposal_id,)).fetchone()
        if row is None or row[0] != 'intake_proposal':
            break
        proposal = json.loads(row[1])
        reads.extend(s for s in proposal.get('sources', []) if s not in reads)
        source = objectives.proposing_source(conn, proposal_id)
        if source is None and proposal.get('state') in ('ROUTED', 'RESOLVED'):
            candidates = []
            for key in proposal.get('sources', []):
                row = conn.execute('SELECT kind, data FROM entities WHERE id=?', (key,)).fetchone()
                data = json.loads(row[1]) if row and row[0] == 'intake_source' else {}
                if (data.get('proposal_id') == proposal_id and data.get('principal') == proposal.get('principal')
                        and data.get('result', {}).get('outcome') == 'inbox'):
                    candidates.append((key, data))
            source = candidates[0] if len(candidates) == 1 else None
        if source is not None:
            evidence = (source[1].get('command', {}).get('provenance') or {}).get('evidence_id')
            if evidence:
                reads.append(evidence)
            return source, reads
        parent = proposal.get('resolves')
        row = conn.execute('SELECT kind, data FROM entities WHERE id=?', (parent,)).fetchone() if isinstance(parent, str) else None
        previous = json.loads(row[1]) if row and row[0] == 'intake_proposal' else {}
        if (previous.get('resolved_to') != proposal_id or previous.get('sources') != proposal.get('sources')
                or previous.get('principal') != proposal.get('principal')):
            break
        proposal_id = parent
    return None, reads


def report(value, source, attribution):
    """Retain reported severity and evidence with the intake's own provenance.

    The PM interprets prose. This function never classifies a message by keywords.
    Missing severity stays unspecified; it is never inferred to be low severity.
    """
    value = {} if value is None else value
    if not isinstance(value, dict) or set(value) - {'severity', 'reproduction', 'scope_changes'}:
        raise ValueError('invalid_input:defect')
    severity = value.get('severity', 'unspecified')
    reproduction = value.get('reproduction', '')
    changes = value.get('scope_changes', [])
    if (not isinstance(severity, str) or not severity.strip()
            or not isinstance(reproduction, str)
            or not isinstance(changes, list)
            or any(not isinstance(c, str) or c not in SCOPE_CHANGES for c in changes)
            or len(set(changes)) != len(changes)):
        raise ValueError('invalid_input:defect')
    if source is None or attribution is None:
        raise ValueError('missing_evidence:defect_source')
    identity, data = source
    return {'severity': severity, 'reproduction': reproduction, 'scope_changes': list(changes),
            'source': {'id': identity, 'kind': data['source_kind'], 'ref': data['source_ref'],
                       'principal': data['principal'], 'text': data['text'],
                       'content_digest': data['content_digest'], 'attribution': copy.deepcopy(attribution)}}


def evidence(item):
    """The report is part of the exact material shown and bound at admission."""
    return copy.deepcopy((item.get('provenance') or {}).get('defect'))
