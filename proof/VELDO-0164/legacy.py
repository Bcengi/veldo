"""Unmodified reader bodies from 294e1933, used as the AC3 comparison oracle.
The model body uses the current registration, including the newly published default team.
"""

def read_model(store, conn, name):
    """One read model from the authority's connection, in one read transaction at one watermark."""
    model = MODELS[name]
    kinds = [k.kind for k in model.kinds]
    items, problems, redacted = {k: [] for k in kinds}, [], []
    opened = not conn.in_transaction
    if opened:
        conn.execute('BEGIN')
    try:
        mark = watermark(conn)
        for row in conn.execute('SELECT id, kind, version, digest, data FROM entities WHERE kind IN (%s) '
                                'ORDER BY kind, id' % ','.join('?' * len(kinds)), kinds).fetchall():
            item, extra = _item(store, conn, row)
            if item is None:
                problems.append(extra)
                continue
            items[item['kind']].append(item)
            redacted.extend(extra)
    finally:
        if opened:
            conn.execute('COMMIT')
    answer = {'schema': SCHEMA, 'model': name, 'kinds': kinds, 'items': items, 'problems': problems,
              'redacted': redacted, 'watermark': mark, 'freshness': 'live',
              'gaps': [g._asdict() for g in GAPS if g.criterion == 'AC2' and _gap_of(g, name)]}
    if name == 'workers':
        answer['machines'] = machines(items['dispatch'])
    return answer

def workflow(self, principal, workflow, version=None):
    """VELDO-0132's stored canvas document of one revision (the head when `version` is None)."""
    def produce():
        if self.workflows is None:
            raise WF.Refused('unavailable_service:workflows', 'no workflow service on this authority')
        document = self.workflows.load(workflow, version)
        served, paths = MO.redact(document)
        return dict(served, redacted=paths, watermark=MO.watermark(self.conn), freshness='live')
    return self._answer(principal, produce)

def _feed(self, after, limit):
    self._authority()
    if self.publication is None:
        raise WF.Refused('unavailable_service:publication', 'no VELDO-0051 publication on this authority')
    # The publication's own public bounded readers: at most `limit` journal records after `after` with
    # the head, and the events it has published up to its stored watermark. Its refusals keep their names.
    rows, top = self.publication.journal(after, limit)
    head = top['seq']
    listed, published = self.publication.published(after, rows[-1][0] if rows else after)
    by_seq = {}
    for event in listed:
        by_seq.setdefault(event.get('journal_seq'), []).append(event['id'])
    out = []
    for seq, command, digest, changes, committed in rows:
        revocations = {}
        for eid, change in changes.items():
            data = (change or {}).get('data') or {}
            if change.get('kind') in (CR.KIND, 'membership') and data.get('revoked_at') is not None:
                revocations[eid] = {'kind': change['kind'], 'data': {'credential_id': data.get('credential_id'),
                                                                     'revoked_at': data['revoked_at']}}
        out.append({'seq': seq, 'command_id': command, 'record_digest': digest, 'committed_at': committed,
                    'entities': [{'id': eid, 'kind': (changes[eid] or {}).get('kind')} for eid in sorted(changes)],
                    'revocations': revocations, 'published': by_seq.get(seq, [])})
    return {'schema': 'veldo.api_events/v1', 'after': after, 'events': out,
            'watermark': {'seq': head, 'record_digest': top['record_digest']},
            'publication': {'watermark': published, 'head': head, 'pending_records': max(0, head - published),
                            'freshness': 'live' if published == head else 'stale'}}
