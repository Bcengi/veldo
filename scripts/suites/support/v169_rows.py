"""VELDO-0169: a claim record in a state no command decides, written around execute.

Since VELDO-0169 the claim organ (control_claim) decides every entity of kind claim, and the store
refuses every other writer of one (control_store.declare_organ), the generic upsert_entity among
them. A suite that drives the claim organ or the claim client against a claim no transition makes
(an uncertain state, a heartbeat from the future or the distant past, a holder or generation set by
hand) plants that row the way 59_veldo_0037_aliases plants a revision no command could have
accepted: around execute, in its own write transaction, with the entity digest and the next version
the store itself computes, so every reader decodes it exactly as a committed row. It is a forged
row and is never journaled; the suites that plant one say so where they do.
"""
import json


def plant(store, conn, eid, kind, data):
    """Write entity `eid` of `kind` with `data` around execute, at its next version."""
    conn.execute('BEGIN IMMEDIATE')
    try:
        row = conn.execute('SELECT version FROM entities WHERE id=?', (eid,)).fetchone()
        version = (row[0] if row else 0) + 1
        digest = store.digest_of({'kind': kind, 'data': data, 'version': version})
        conn.execute('INSERT INTO entities (id, kind, version, digest, data) VALUES (?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET '
                     'kind=excluded.kind, version=excluded.version, digest=excluded.digest, data=excluded.data',
                     (eid, kind, version, digest, json.dumps(data, sort_keys=True)))
        conn.execute('COMMIT')
    except BaseException:
        if conn.in_transaction:
            conn.execute('ROLLBACK')
        raise
    return version
